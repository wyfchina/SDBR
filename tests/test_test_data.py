from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from sdbr.api import create_app
from sdbr.runtime_environment import resolve_runtime_environment
from sdbr.state_store import SQLiteWorkbenchStateStore, WorkbenchStateStore
from sdbr.test_data import (
    BASELINE_MASTER_DATA_VERSION_ID,
    BASELINE_OPERATIONAL_STATE_ID,
    MATERIAL_SHORTAGE_OPERATIONAL_STATE_ID,
    WIP_LIMIT_OPERATIONAL_STATE_ID,
    main,
    reset_test_database,
    seed_baseline_test_data,
    test_case_catalog_payload as build_test_case_catalog_payload,
)


def test_seed_baseline_test_data_builds_business_readable_state():
    store = WorkbenchStateStore()

    summary = seed_baseline_test_data(store)

    assert summary.master_data_version_id == BASELINE_MASTER_DATA_VERSION_ID
    assert summary.resource_count == 6
    assert summary.routing_count == 4
    assert summary.order_count == 12
    assert BASELINE_OPERATIONAL_STATE_ID in store.operational_state_snapshots
    assert MATERIAL_SHORTAGE_OPERATIONAL_STATE_ID in store.operational_state_snapshots
    assert WIP_LIMIT_OPERATIONAL_STATE_ID in store.operational_state_snapshots
    assert sorted(store.planning_runs) == [
        "TST-RUN-BASELINE-001",
        "TST-RUN-MATERIAL-SHORTAGE-001",
        "TST-RUN-WIP-LIMIT-001",
    ]
    assert all(
        run["SolverBackendID"] == "ortools"
        for run in store.planning_runs.values()
    )
    assert all(
        order["OrderID"].startswith("TST-")
        for order in store.master_data_versions[BASELINE_MASTER_DATA_VERSION_ID]["Orders"]
    )


def test_test_case_catalog_documents_business_acceptance_cases():
    # BE-DATA-014 / BE-SOLVER-009 / BE-REL-004
    payload = build_test_case_catalog_payload()

    assert payload["DatasetID"] == "TST-DATASET-BASELINE-20260619"
    assert payload["CaseCount"] == 3
    cases = {case["CaseID"]: case for case in payload["Cases"]}
    assert cases["TST-CASE-BASELINE"]["PlanningRunID"] == "TST-RUN-BASELINE-001"
    assert cases["TST-CASE-BASELINE"]["InputSummaryZh"].startswith("使用基准主数据")
    assert "12 张工单" in cases["TST-CASE-BASELINE"]["ExpectedScheduleZh"]
    assert cases["TST-CASE-BASELINE"]["ExpectedReleaseReadyMin"] == 1
    assert cases["TST-CASE-BASELINE"]["ExpectedPublicationStatus"] == "Draft"
    assert cases["TST-CASE-MATERIAL-SHORTAGE"]["ExpectedBlockingCodes"] == [
        "MATERIAL_SHORTAGE"
    ]
    assert cases["TST-CASE-WIP-LIMIT"]["ExpectedBlockingCodes"] == [
        "WIP_LIMIT_EXCEEDED"
    ]
    assert all(
        case["ExpectedSolverBackendID"] == "ortools"
        for case in payload["Cases"]
    )


def test_reset_test_database_archives_existing_database_and_seeds_new_state(tmp_path):
    database_path = tmp_path / "workbench-state.db"
    database_path.write_bytes(b"old database")

    summary = reset_test_database(
        database_path=database_path,
        archived_at=datetime(2026, 6, 19, 8, tzinfo=timezone.utc),
    )

    assert summary.environment_id == "test"
    assert summary.database_path == str(database_path.resolve())
    assert summary.archived_database_path is not None
    assert summary.archived_database_path.endswith(
        "archive\\workbench-state-20260619T080000Z.db"
    )
    assert database_path.exists()

    store = SQLiteWorkbenchStateStore(database_path)
    assert BASELINE_MASTER_DATA_VERSION_ID in store.master_data_versions
    assert BASELINE_OPERATIONAL_STATE_ID in store.operational_state_snapshots
    assert "TST-RUN-BASELINE-001" in store.planning_runs


def test_reset_test_database_refuses_production_environment(tmp_path):
    with pytest.raises(ValueError, match="production environment"):
        reset_test_database(
            environment_id="production",
            database_path=tmp_path / "production.db",
        )


def test_seeded_test_database_feeds_data_readiness_endpoint(tmp_path):
    database_path = tmp_path / "workbench-state.db"
    reset_test_database(database_path=database_path)
    runtime_environment = resolve_runtime_environment(
        environment_id="test",
        database_path=database_path,
    )
    client = TestClient(
        create_app(
            state_store=SQLiteWorkbenchStateStore(database_path),
            runtime_environment=runtime_environment,
        )
    )

    response = client.get(
        "/planner/workbench/data-readiness",
        params={"EvaluatedAt": "2026-06-19T08:10:00+00:00"},
    )

    assert response.status_code == 200
    data = response.json()["Data"]
    assert data["LatestMasterDataVersion"]["VersionID"] == BASELINE_MASTER_DATA_VERSION_ID
    assert data["Selection"]["MasterDataVersionID"] == BASELINE_MASTER_DATA_VERSION_ID
    assert data["Selection"]["OperationalStateSnapshotID"] in {
        BASELINE_OPERATIONAL_STATE_ID,
        MATERIAL_SHORTAGE_OPERATIONAL_STATE_ID,
        WIP_LIMIT_OPERATIONAL_STATE_ID,
    }
    assert data["CanCreatePlanningRun"] is True


def test_test_case_catalog_endpoint_exposes_environment_metadata(tmp_path):
    runtime_environment = resolve_runtime_environment(
        environment_id="test",
        database_path=tmp_path / "workbench-state.db",
    )
    client = TestClient(
        create_app(
            state_store=SQLiteWorkbenchStateStore(runtime_environment.database_path),
            runtime_environment=runtime_environment,
        )
    )

    response = client.get("/planner/workbench/test-data/cases")

    assert response.status_code == 200
    data = response.json()["Data"]
    assert data["CaseCount"] == 3
    assert data["Environment"]["EnvironmentID"] == "test"
    assert data["Cases"][0]["CoveredSpecIDs"]


def test_test_case_acceptance_endpoint_marks_pending_cases_as_needing_execution():
    store = WorkbenchStateStore()
    seed_baseline_test_data(store)
    client = TestClient(create_app(state_store=store))

    response = client.get("/planner/workbench/test-data/acceptance")

    assert response.status_code == 200
    data = response.json()["Data"]
    assert data["AcceptancePackageID"] == "TST-ACP-BASELINE-20260619"
    assert data["Summary"]["PendingHumanDecisionCount"] == 0
    assert data["Summary"]["NeedsExecutionCount"] == 3
    assert {case["AcceptanceStatus"] for case in data["Cases"]} == {
        "NeedsExecution"
    }
    assert all(case["ActualVsExpected"] for case in data["Cases"])


def test_test_case_acceptance_decisions_persist_in_sqlite_store(tmp_path):
    database_path = tmp_path / "workbench-state.db"
    store = SQLiteWorkbenchStateStore(database_path)
    seed_baseline_test_data(store)
    store.save()
    client = TestClient(create_app(state_store=store))
    for run_id in [
        "TST-RUN-BASELINE-001",
        "TST-RUN-MATERIAL-SHORTAGE-001",
        "TST-RUN-WIP-LIMIT-001",
    ]:
        assert client.post(
            f"/planner/workbench/planning-runs/{run_id}/enqueue",
            json={
                "EnqueuedBy": "planner-test",
                "EnqueuedAt": "2026-06-19T08:01:00+00:00",
            },
        ).status_code == 200
        claim = client.post(
            "/planner/workbench/planning-runs/jobs/claim-next",
            json={
                "WorkerID": "worker-test",
                "ClaimedAt": "2026-06-19T08:02:00+00:00",
                "LeaseSeconds": 600,
            },
        )
        assert claim.status_code == 200
        assert client.post(
            f"/planner/workbench/planning-runs/{run_id}/execute",
            json={
                "ExecutedBy": "worker-test",
                "StartedAt": "2026-06-19T08:03:00+00:00",
                "CompletedAt": "2026-06-19T08:04:00+00:00",
                "TimeLimitSeconds": 30,
                "LeaseToken": claim.json()["Data"]["PlanningRun"]["LeaseToken"],
            },
        ).status_code == 200
    assert client.post(
        "/planner/workbench/test-data/acceptance/TST-CASE-BASELINE/decision",
        json={
            "Decision": "Confirm",
            "ActorID": "planner-test",
            "DecidedAt": "2026-06-20T10:15:00+00:00",
        },
    ).status_code == 200

    reloaded = TestClient(create_app(state_store=SQLiteWorkbenchStateStore(database_path)))
    response = reloaded.get("/planner/workbench/test-data/acceptance")

    assert response.status_code == 200
    data = response.json()["Data"]
    assert data["Summary"]["ConfirmedCount"] == 1
    cases = {case["CaseID"]: case for case in data["Cases"]}
    assert cases["TST-CASE-BASELINE"]["LatestDecision"]["ActorID"] == "planner-test"


def test_test_data_cli_lists_cases_without_rebuild(capsys):
    main(["--list-cases"])

    output = capsys.readouterr().out
    assert "TST-DATASET-BASELINE-20260619" in output
    assert "TST-CASE-MATERIAL-SHORTAGE" in output
