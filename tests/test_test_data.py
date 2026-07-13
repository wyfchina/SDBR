from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from sdbr.api import create_app
from sdbr.runtime_environment import resolve_runtime_environment
from sdbr.state_store import SQLiteWorkbenchStateStore, WorkbenchStateStore
from sdbr.test_data import (
    BASELINE_MASTER_DATA_VERSION_ID,
    BASELINE_OPERATIONAL_STATE_ID,
    DDMRP_NET_FLOW_MASTER_DATA_VERSION_ID,
    MATERIAL_SHORTAGE_OPERATIONAL_STATE_ID,
    P1_MARKET_CONTROL_MASTER_DATA_VERSION_ID,
    P1_MARKET_CONTROL_RUN_ID,
    WIP_LIMIT_OPERATIONAL_STATE_ID,
    main,
    reset_test_database,
    seed_baseline_test_data,
    test_case_catalog_payload as build_test_case_catalog_payload,
)


# BE-DDMRP-007 / UI-DDMRP-003
def test_be_ddmrp_007_seeded_read_only_replenishment_workbench_is_reproducible(
    tmp_path,
):
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

    catalog_response = client.get("/planner/workbench/test-data/cases")

    assert catalog_response.status_code == 200
    catalog = catalog_response.json()["Data"]
    seeded_cases = [
        case
        for case in catalog["DdmrpRuntimeCases"]
        if case["CaseID"] == "TST-DDMRP-REPLENISHMENT-READONLY-20260711"
    ]
    assert len(seeded_cases) == 1
    seeded_case = seeded_cases[0]
    assert seeded_case["CaseGroup"] == "DDMRPRuntimeCases"
    assert seeded_case["ExpectedSummary"] == {
        "RedCount": 3,
        "YellowCount": 3,
        "GreenCount": 3,
        "AboveGreenCount": 3,
        "BlockedRecommendationCount": 6,
        "PendingReviewCount": 0,
        "AdjustmentRequiredCount": 0,
        "ActiveGraphCount": 0,
    }
    assert seeded_case["CoveredSpecIDs"] == ["BE-DDMRP-007", "UI-DDMRP-003"]

    workbench_response = client.get("/planner/workbench/ddmrp/workbench")

    assert workbench_response.status_code == 200
    workbench = workbench_response.json()["Data"]
    assert workbench["Evaluation"]["EvaluationAt"] == "2026-07-11T01:00:00+00:00"
    assert workbench["Summary"] == seeded_case["ExpectedSummary"]
    assert len(workbench["Rows"]) == 12
    assert {
        status: sum(1 for row in workbench["Rows"] if row["PlanningStatus"] == status)
        for status in ("Red", "Yellow", "Green", "AboveGreen")
    } == {"Red": 3, "Yellow": 3, "Green": 3, "AboveGreen": 3}
    expected_authority_on_hand = {
        "TST-DDMRP-RO-ABOVE-GREEN-1": 150.0,
        "TST-DDMRP-RO-ABOVE-GREEN-2": 165.0,
        "TST-DDMRP-RO-ABOVE-GREEN-3": 180.0,
        "TST-DDMRP-RO-GREEN-1": 75.0,
        "TST-DDMRP-RO-GREEN-2": 82.0,
        "TST-DDMRP-RO-GREEN-3": 95.0,
        "TST-DDMRP-RO-RED-1": 10.0,
        "TST-DDMRP-RO-RED-2": 14.0,
        "TST-DDMRP-RO-RED-3": 18.0,
        "TST-DDMRP-RO-YELLOW-1": 35.0,
        "TST-DDMRP-RO-YELLOW-2": 42.0,
        "TST-DDMRP-RO-YELLOW-3": 49.0,
    }
    assert {
        row["ItemID"]: row["QualifiedOnHandQty"] for row in workbench["Rows"]
    } == expected_authority_on_hand
    assert {
        row["ItemID"]: row["AuthorityAvailableQty"] for row in workbench["Rows"]
    } == expected_authority_on_hand
    assert all(
        row["StandardTargetReceiptAt"] is None
        and [gate["Code"] for gate in row["GateCodes"]]
        == [
            "DLT_TARGET_SEMANTICS_INSUFFICIENT",
            "OPERATIONAL_AUTHORITY_NOT_ACCEPTED",
            "PLANNING_ADVICE_CONTRACT_NOT_ACCEPTED",
            "PLAN_BOM_FEASIBILITY_CONTRACT_NOT_ACCEPTED",
        ]
        and row["OperationalActionAllowed"] is False
        and row["PendingReviewCount"] == 0
        for row in workbench["Rows"]
    )
    assert all(
        row["RecommendationStatus"] == "Blocked"
        for row in workbench["Rows"]
        if row["PlanningStatus"] in {"Red", "Yellow"}
    )
    assert all(
        row["RecommendationStatus"] is None
        for row in workbench["Rows"]
        if row["PlanningStatus"] in {"Green", "AboveGreen"}
    )
    assert all(
        row["SuggestedReplenishmentQty"] == 0
        and row["RecommendedAction"] == "Monitor"
        for row in workbench["Rows"]
        if row["PlanningStatus"] in {"Green", "AboveGreen"}
    )
    assert workbench["ActiveGraphs"] == []
    assert all("OperationalControl" not in row for row in workbench["Rows"])


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
    assert DDMRP_NET_FLOW_MASTER_DATA_VERSION_ID in store.master_data_versions
    assert P1_MARKET_CONTROL_MASTER_DATA_VERSION_ID in store.master_data_versions
    assert P1_MARKET_CONTROL_RUN_ID in store.planning_runs
    assert {
        "TST-RUN-BASELINE-001",
        "TST-RUN-MATERIAL-SHORTAGE-001",
        "TST-RUN-WIP-LIMIT-001",
        "TST-CP-RUN-FINITE-001",
        "TST-CP-RUN-INFEASIBLE-001",
    } <= set(store.planning_runs)
    assert all(
        run["SolverBackendID"] == "ortools"
        for run in store.planning_runs.values()
    )
    assert all(
        order["OrderID"].startswith("TST-")
        for order in store.master_data_versions[BASELINE_MASTER_DATA_VERSION_ID]["Orders"]
    )
    p1_version = store.master_data_versions[P1_MARKET_CONTROL_MASTER_DATA_VERSION_ID]
    p1_demand_classes = {row["OrderID"]: row.get("DemandClass") for row in p1_version["Orders"]}
    assert "MTO" in p1_demand_classes.values()
    assert "MTA" in p1_demand_classes.values()
    assert any(row.get("DemandClass") == "MTA" for row in p1_version["Orders"])
    ddmrp_version = store.master_data_versions[DDMRP_NET_FLOW_MASTER_DATA_VERSION_ID]
    assert len(ddmrp_version["DdmrpDecouplingPoints"]) == 12
    assert {
        row["PlanningStatus"] for row in ddmrp_version["DdmrpDecouplingPoints"]
    } == {"Red", "Yellow", "Green", "AboveGreen"}


def test_p1_market_control_case_contains_mto_and_mta_orders():
    store = WorkbenchStateStore()
    seed_baseline_test_data(store)

    mdv = store.master_data_versions[P1_MARKET_CONTROL_MASTER_DATA_VERSION_ID]
    demand_classes = {row["OrderID"]: row.get("DemandClass") for row in mdv["Orders"]}

    assert P1_MARKET_CONTROL_RUN_ID in store.planning_runs
    assert "MTO" in demand_classes.values()
    assert "MTA" in demand_classes.values()
    assert any(row.get("DemandClass") == "MTA" for row in mdv["Orders"])
    assert mdv["DdmrpRuntimeLines"][0]["ItemID"] == "TST-FG-C"


def test_test_case_catalog_documents_business_acceptance_cases():
    # BE-DATA-014 / BE-SOLVER-009 / BE-REL-004
    payload = build_test_case_catalog_payload()

    assert payload["DatasetID"] == "TST-DATASET-BASELINE-20260619"
    assert payload["CaseCount"] == 10
    assert payload["DdmrpRuntimeCases"][0]["MasterDataVersionID"] == (
        DDMRP_NET_FLOW_MASTER_DATA_VERSION_ID
    )
    assert payload["DdmrpRuntimeCases"][0]["ExpectedSummary"] == {
        "RedCount": 3,
        "YellowCount": 3,
        "GreenCount": 3,
        "AboveGreenCount": 3,
        "ReplenishmentSuggestionCount": 6,
    }
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
    assert cases["TST-CP-FINITE-RESOURCE"]["CaseGroup"] == "CPSATBusinessCases"
    assert cases["TST-CP-FINITE-RESOURCE"]["ExpectedScheduleAssertions"] == [
        "FINITE_RESOURCE_NO_OVERLAP",
        "ALL_ORDERS_SCHEDULED",
    ]
    assert cases["TST-CP-INFEASIBLE-WINDOW"]["ExpectedPlanningRunStatus"] == "DeadLetter"
    assert cases["TST-CP-INFEASIBLE-WINDOW"]["ExpectedDiagnosticCodes"] == [
        "ORTOOLS_INFEASIBLE"
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


class TestOrderCommitmentBrowserSeed:
    """BE-DATA-014 / BE-SDBR-010: controlled MTO browser fixture."""

    def test_seed_builds_valid_master_fresh_snapshot_and_published_completed_baseline(
        self,
    ):
        from sdbr import test_data

        store = WorkbenchStateStore()
        captured_at = datetime(2026, 7, 12, 8, tzinfo=timezone.utc)

        fixture = test_data.seed_mto_order_commitment_fixture(
            store,
            captured_at=captured_at,
        )

        master_data = store.master_data_versions[
            fixture["MasterDataVersionID"]
        ]
        snapshot = store.operational_state_snapshots[
            fixture["OperationalStateSnapshotID"]
        ]
        baseline = store.planning_runs[fixture["BaselinePlanningRunID"]]
        assert master_data["VersionID"] == "TST-MTO-MDV-COMMITMENT"
        assert master_data["Status"] == "Valid"
        assert master_data["Validation"]["IsValid"] is True
        assert snapshot.snapshot_id == "TST-MTO-OPS-CURRENT"
        assert snapshot.captured_at == captured_at - timedelta(minutes=5)
        assert baseline["RunID"] == "TST-MTO-RUN-BASELINE"
        assert baseline["Status"] == "Completed"
        assert baseline["PublicationStatus"] == "Published"
        assert baseline["ScheduleFingerprint"]

    def test_seed_returns_exact_api_intake_template_and_window_ids(self):
        from sdbr import test_data

        store = WorkbenchStateStore()
        captured_at = datetime(2026, 7, 12, 8, tzinfo=timezone.utc)

        fixture = test_data.seed_mto_order_commitment_fixture(
            store,
            captured_at=captured_at,
        )

        assert fixture["MasterDataVersionID"] == "TST-MTO-MDV-COMMITMENT"
        assert fixture["OperationalStateSnapshotID"] == "TST-MTO-OPS-CURRENT"
        assert fixture["BaselinePlanningRunID"] == "TST-MTO-RUN-BASELINE"
        assert fixture["CapacityWindowKeys"] == [
            (
                "TST-MTO-CCR-1",
                "2026-07-14T08:00:00+00:00",
                "2026-07-14T16:00:00+00:00",
            ),
            (
                "TST-MTO-CCR-1",
                "2026-07-15T08:00:00+00:00",
                "2026-07-15T16:00:00+00:00",
            ),
        ]
        assert fixture["IntakePayloadTemplate"] == {
            "SourceSystem": "MockERP",
            "SourceObjectType": "CustomerOrder",
            "OrderID": "TST-MTO-SO-ORDINARY",
            "OrderVersion": "1",
            "DemandLineID": "10",
            "ProductID": "TST-MTO-FG-1",
            "LocationID": "TST-MAIN",
            "Quantity": 1.0,
            "Uom": "EA",
            "RequestedDueAt": "2026-07-14T18:00:00+00:00",
            "BusinessPriority": 100,
            "ReceivedAt": "2026-07-12T08:00:00+00:00",
            "TraceID": "TRACE-TST-MTO-ORDINARY",
            "BaselinePlanningRunID": "TST-MTO-RUN-BASELINE",
            "RoutingID": "PRIMARY",
            "OperationalStateSnapshotID": "TST-MTO-OPS-CURRENT",
            "MaterialRequirements": [
                {
                    "RequirementLineID": "TST-MTO-SO-ORDINARY:10:TST-MTO-RM-1",
                    "ItemID": "TST-MTO-RM-1",
                    "LocationID": "TST-MAIN",
                    "RequiredQty": 5.0,
                    "Uom": "EA",
                }
            ],
        }

    def test_test_environment_reset_endpoint_uses_server_time_and_is_repeatable(
        self,
    ):
        server_time = datetime(2026, 7, 12, 8, tzinfo=timezone.utc)
        store = WorkbenchStateStore()
        client = TestClient(create_app(state_store=store, utc_now=lambda: server_time))

        first = client.post("/planner/workbench/test-data/order-commitment/reset")
        assert first.status_code == 200
        first_data = first.json()["Data"]
        assert first_data["Status"] == "Reset"
        assert first_data["IntakePayloadTemplate"]["ReceivedAt"] == (
            server_time.isoformat()
        )
        assert store.operational_state_snapshots[
            "TST-MTO-OPS-CURRENT"
        ].captured_at == server_time - timedelta(minutes=5)

        store.order_commitment_evaluations["TST-MTO-EVAL-STALE"] = {}
        second = client.post("/planner/workbench/test-data/order-commitment/reset")
        assert second.status_code == 200
        assert second.json()["Data"] == first_data
        assert store.order_commitment_evaluations == {}

    def test_production_environment_rejects_order_commitment_fixture_reset(self, tmp_path):
        runtime_environment = resolve_runtime_environment(
            environment_id="production",
            database_path=tmp_path / "production.db",
        )
        client = TestClient(
            create_app(
                state_store=WorkbenchStateStore(),
                runtime_environment=runtime_environment,
            )
        )

        response = client.post("/planner/workbench/test-data/order-commitment/reset")

        assert response.status_code == 409
        assert response.json() == {
            "Endpoint": "/planner/workbench/test-data/order-commitment/reset",
            "StatusCode": 409,
            "Data": {"Status": "TestDataResetNotAllowed"},
        }


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
    assert data["LatestMasterDataVersion"]["VersionID"] == DDMRP_NET_FLOW_MASTER_DATA_VERSION_ID
    assert data["Selection"]["MasterDataVersionID"] == DDMRP_NET_FLOW_MASTER_DATA_VERSION_ID
    assert data["Selection"]["OperationalStateSnapshotID"] in {
        BASELINE_OPERATIONAL_STATE_ID,
        MATERIAL_SHORTAGE_OPERATIONAL_STATE_ID,
        WIP_LIMIT_OPERATIONAL_STATE_ID,
    }
    assert data["CanCreatePlanningRun"] is True


def test_seeded_test_database_feeds_ddmrp_runtime_status(tmp_path):
    # BE-DDMRP-001 / BE-DDMRP-006 / UI-DDMRP-001
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
        "/planner/workbench/ddmrp/status",
        params={"EvaluatedAt": "2026-06-25T08:00:00+00:00"},
    )

    assert response.status_code == 200
    data = response.json()["Data"]
    assert data["Source"]["VersionID"] == DDMRP_NET_FLOW_MASTER_DATA_VERSION_ID
    assert data["Summary"] == {
        "DecouplingPointCount": 12,
        "LineCount": 12,
        "RedCount": 3,
        "YellowCount": 3,
        "GreenCount": 3,
        "AboveGreenCount": 3,
        "ReplenishmentSuggestionCount": 6,
        "MissingDataCount": 0,
        "ReadyForRuntime": True,
    }
    lines = {line["ItemID"]: line for line in data["Lines"]}
    assert lines["TST-DDMRP-RED"]["PlanningStatus"] == "Red"
    assert lines["TST-DDMRP-YELLOW"]["PlanningStatus"] == "Yellow"
    assert lines["TST-DDMRP-GREEN"]["PlanningStatus"] == "Green"
    assert lines["TST-DDMRP-GREEN"]["SuggestedReplenishmentQty"] == 0
    assert lines["TST-DDMRP-ABOVE"]["PlanningStatus"] == "AboveGreen"


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
    assert data["CaseCount"] == 10
    assert data["DdmrpRuntimeCases"][0]["CaseGroup"] == "DDMRPRuntimeCases"
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
    assert data["Summary"]["NeedsExecutionCount"] == 10
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
