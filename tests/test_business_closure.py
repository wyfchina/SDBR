from datetime import datetime, timedelta

from fastapi.testclient import TestClient

from sdbr.api import create_app
from sdbr.operational_state import create_operational_state_snapshot
from sdbr.state_store import WorkbenchStateStore
from sdbr.test_data import (
    BASELINE_MASTER_DATA_VERSION_ID,
    BASELINE_OPERATIONAL_STATE_ID,
    MATERIAL_SHORTAGE_OPERATIONAL_STATE_ID,
    WIP_LIMIT_OPERATIONAL_STATE_ID,
    seed_baseline_test_data,
)


def test_test_data_drives_planning_run_output_and_release_management():
    store = WorkbenchStateStore()
    seed_baseline_test_data(store)
    client = TestClient(create_app(state_store=store))

    created = client.post(
        "/planner/workbench/planning-runs",
        json={
            "RunID": "TST-RUN-E2E-CREATED",
            "ProblemID": "TST-PROBLEM-E2E",
            "MasterDataVersionID": BASELINE_MASTER_DATA_VERSION_ID,
            "OperationalStateSnapshotID": BASELINE_OPERATIONAL_STATE_ID,
            "ScheduleStartAt": "2026-06-22T08:00:00+00:00",
            "TimeBufferMinutes": 480,
            "SolverBackendID": "ortools",
            "RequestedBy": "planner-e2e",
            "RequestedAt": "2026-06-19T08:00:00+00:00",
        },
    )
    assert created.status_code == 200
    assert created.json()["Data"]["PlanningRun"]["Status"] == "Pending"

    run = _enqueue_claim_and_execute(client, "TST-RUN-E2E-CREATED")
    assert run["Status"] == "Completed"
    assert run["SolverStatus"] == "Optimal"
    assert run["PublicationStatus"] == "Draft"
    assert run["Schedule"]["ProblemID"] == "TST-PROBLEM-E2E"

    schedule_result = client.get(
        "/planner/workbench/schedule-results/runs/TST-RUN-E2E-CREATED/workbench"
    )
    assert schedule_result.status_code == 200
    schedule_data = schedule_result.json()["Data"]
    assert schedule_data["Context"]["RunID"] == "TST-RUN-E2E-CREATED"
    assert schedule_data["KPIs"]["OrderCount"] == 12
    assert schedule_data["Gantt"]["Rows"]
    assert schedule_data["SystemLoad"]["Rows"]

    work_orders = client.get(
        "/planner/workbench/schedule-results/runs/"
        "TST-RUN-E2E-CREATED/work-orders/workbench"
    )
    assert work_orders.status_code == 200
    rows = work_orders.json()["Data"]["Rows"]
    assert len(rows) == 12
    first = rows[0]
    assert first["OrderID"].startswith("TST-WO-")
    assert first["PlannedStartAt"] is not None
    assert first["PlannedCompletionAt"] is not None
    assert first["ResourceIDs"]

    release = client.get(
        "/planner/workbench/release-management/runs/"
        "TST-RUN-E2E-CREATED/workbench",
        params={
            "evaluated_at": "2026-07-02T12:00:00+00:00",
            "operational_state_max_age_minutes": 30000,
        },
    )
    assert release.status_code == 200
    release_data = release.json()["Data"]
    assert release_data["Summary"]["TotalCount"] == 12
    assert release_data["Summary"]["ReadyCount"] > 0
    ready = next(item for item in release_data["Candidates"] if item["CanAuthorize"])
    assert ready["RecommendedAction"] == "ReadyForRelease"
    assert ready["BlockingReasons"] == []


def test_test_data_drives_release_authorization_and_buffer_execution_with_fresh_snapshot():
    # BE-DATA-014 / BE-REL-010 / BE-EXEC-004
    store = WorkbenchStateStore()
    seed_baseline_test_data(store)
    client = TestClient(create_app(state_store=store))

    run = _enqueue_claim_and_execute(client, "TST-RUN-BASELINE-001")
    first_release = min(
        run["Schedule"]["ReleaseRecommendations"],
        key=lambda item: item["SuggestedReleaseDate"],
    )
    evaluated_at = datetime.fromisoformat(first_release["SuggestedReleaseDate"])
    baseline_snapshot = store.operational_state_snapshots[BASELINE_OPERATIONAL_STATE_ID]
    store.operational_state_snapshots[BASELINE_OPERATIONAL_STATE_ID] = (
        create_operational_state_snapshot(
            snapshot_id=baseline_snapshot.snapshot_id,
            captured_at=evaluated_at,
            inventory_buffers=baseline_snapshot.inventory_buffers,
            material_availability=baseline_snapshot.material_availability,
            wip_limits=baseline_snapshot.wip_limits,
        )
    )

    release = client.get(
        "/planner/workbench/release-management/runs/"
        "TST-RUN-BASELINE-001/workbench",
        params={"evaluated_at": evaluated_at.isoformat()},
    )

    assert release.status_code == 200
    release_data = release.json()["Data"]
    assert release_data["OperationalStateStatus"] == "Fresh"
    ready = next(item for item in release_data["Candidates"] if item["CanAuthorize"])
    assert ready["OrderID"] == first_release["OrderID"]
    assert ready["SuggestedReleaseAt"] == first_release["SuggestedReleaseDate"]
    assert ready["SuggestedReleaseAt"] < ready["ScheduledStart"]

    authorization = client.post(
        "/planner/workbench/release-management/runs/"
        f"TST-RUN-BASELINE-001/orders/{ready['OrderID']}/authorize",
        json={
            "ReleasedBy": "planner-e2e",
            "ReleasedAt": evaluated_at.isoformat(),
            "OperationalStateMaxAgeMinutes": 60,
        },
    )
    assert authorization.status_code == 200
    authorization_id = authorization.json()["Data"]["Authorization"]["AuthorizationID"]

    board_before = client.get(
        "/planner/workbench/buffer-board/runs/TST-RUN-BASELINE-001/workbench",
        params={"evaluated_at": evaluated_at.isoformat()},
    ).json()["Data"]
    assert _buffer_order_count(board_before, "YetToBeReceived") == 1
    assert _buffer_order_count(board_before, "Received") == 0

    arrived_at = evaluated_at + timedelta(minutes=10)
    transaction = client.post(
        "/planner/workbench/buffer-board/runs/"
        f"TST-RUN-BASELINE-001/orders/{ready['OrderID']}/transactions",
        json={
            "EventType": "ArrivedBuffer",
            "EventAt": arrived_at.isoformat(),
            "ActorID": "operator-e2e",
            "MeasureType": "Quantity",
            "MeasureValue": 1,
        },
    )
    assert transaction.status_code == 200
    event = transaction.json()["Data"]["Event"]
    assert event["AuthorizationID"] == authorization_id
    assert event["Status"] == "Accepted"

    board_after = client.get(
        "/planner/workbench/buffer-board/runs/TST-RUN-BASELINE-001/workbench",
        params={"evaluated_at": arrived_at.isoformat()},
    ).json()["Data"]
    assert _buffer_order_count(board_after, "YetToBeReceived") == 0
    assert _buffer_order_count(board_after, "Received") == 1


def test_release_management_blocks_material_shortage_and_wip_limit_from_schedules():
    store = WorkbenchStateStore()
    seed_baseline_test_data(store)
    client = TestClient(create_app(state_store=store))

    material_run = _enqueue_claim_and_execute(
        client, "TST-RUN-MATERIAL-SHORTAGE-001"
    )
    wip_run = _enqueue_claim_and_execute(client, "TST-RUN-WIP-LIMIT-001")
    assert material_run["Status"] == "Completed"
    assert wip_run["Status"] == "Completed"

    material_release = client.get(
        "/planner/workbench/release-management/runs/"
        "TST-RUN-MATERIAL-SHORTAGE-001/workbench",
        params={
            "evaluated_at": "2026-07-02T12:00:00+00:00",
            "operational_state_max_age_minutes": 30000,
        },
    )
    assert material_release.status_code == 200
    material_candidates = material_release.json()["Data"]["Candidates"]
    assert material_candidates
    assert any(
        reason["Code"] == "MATERIAL_SHORTAGE"
        for candidate in material_candidates
        for reason in candidate["BlockingReasons"]
    )
    assert all(not candidate["CanAuthorize"] for candidate in material_candidates)

    wip_release = client.get(
        "/planner/workbench/release-management/runs/"
        "TST-RUN-WIP-LIMIT-001/workbench",
        params={
            "evaluated_at": "2026-07-02T12:00:00+00:00",
            "operational_state_max_age_minutes": 30000,
        },
    )
    assert wip_release.status_code == 200
    wip_candidates = wip_release.json()["Data"]["Candidates"]
    assert wip_candidates
    assert any(
        reason["Code"] == "WIP_LIMIT_EXCEEDED"
        for candidate in wip_candidates
        for reason in candidate["BlockingReasons"]
    )
    assert all(not candidate["CanAuthorize"] for candidate in wip_candidates)


def test_test_case_acceptance_summarizes_completed_business_cases():
    # BE-DATA-014 / BE-SOLVER-009 / BE-REL-004 / BE-RUN-009
    store = WorkbenchStateStore()
    seed_baseline_test_data(store)
    client = TestClient(create_app(state_store=store))

    for run_id in [
        "TST-RUN-BASELINE-001",
        "TST-RUN-MATERIAL-SHORTAGE-001",
        "TST-RUN-WIP-LIMIT-001",
    ]:
        _enqueue_claim_and_execute(client, run_id)

    response = client.get("/planner/workbench/test-data/acceptance")

    assert response.status_code == 200
    data = response.json()["Data"]
    assert data["AcceptancePackageID"] == "TST-ACP-BASELINE-20260619"
    assert data["EnvironmentBoundary"] == "TestOnly"
    assert data["ExecutionPlan"]["StepCount"] == 4
    assert data["Summary"]["PassedCount"] == 3
    assert data["Summary"]["PendingHumanDecisionCount"] == 3
    cases = {case["CaseID"]: case for case in data["Cases"]}
    assert cases["TST-CASE-BASELINE"]["Expected"]["ReleaseReadyMin"] == 1
    assert all(
        check["Passed"]
        for check in cases["TST-CASE-BASELINE"]["ActualVsExpected"]
    )
    assert cases["TST-CASE-BASELINE"]["Actual"]["Release"]["Summary"]["ReadyCount"] > 0
    assert "MATERIAL_SHORTAGE" in cases["TST-CASE-MATERIAL-SHORTAGE"]["Actual"]["Release"]["BlockingCodes"]
    assert "WIP_LIMIT_EXCEEDED" in cases["TST-CASE-WIP-LIMIT"]["Actual"]["Release"]["BlockingCodes"]
    assert {
        cases["TST-CASE-BASELINE"]["Actual"]["PublicationStatus"],
        cases["TST-CASE-MATERIAL-SHORTAGE"]["Actual"]["PublicationStatus"],
        cases["TST-CASE-WIP-LIMIT"]["Actual"]["PublicationStatus"],
    } == {"Draft"}


def test_test_case_acceptance_records_human_confirmation_and_audit():
    # BE-DATA-014 / BE-OPS-002
    store = WorkbenchStateStore()
    seed_baseline_test_data(store)
    client = TestClient(create_app(state_store=store))
    for run_id in [
        "TST-RUN-BASELINE-001",
        "TST-RUN-MATERIAL-SHORTAGE-001",
        "TST-RUN-WIP-LIMIT-001",
    ]:
        _enqueue_claim_and_execute(client, run_id)

    response = client.post(
        "/planner/workbench/test-data/acceptance/TST-CASE-BASELINE/decision",
        json={
            "Decision": "Confirm",
            "ActorID": "planner-acceptance",
            "DecidedAt": "2026-06-20T10:00:00+00:00",
            "Comment": "基准案例符合业务预期。",
        },
    )

    assert response.status_code == 200
    decision = response.json()["Data"]["Decision"]
    assert decision["DecisionID"] == "TST-ACD-000001"
    assert decision["AcceptanceStatusAtDecision"] == "Passed"
    assert decision["ActualSnapshot"]["PlanningRunStatus"] == "Completed"

    decisions = client.get("/planner/workbench/test-data/acceptance/decisions")
    assert decisions.status_code == 200
    assert decisions.json()["Data"]["Count"] == 1

    workbench = client.get("/planner/workbench/test-data/acceptance").json()["Data"]
    cases = {case["CaseID"]: case for case in workbench["Cases"]}
    assert workbench["Summary"]["ConfirmedCount"] == 1
    assert workbench["Summary"]["PendingHumanDecisionCount"] == 2
    assert cases["TST-CASE-BASELINE"]["LatestDecision"]["Decision"] == "Confirm"

    audit = client.get(
        "/planner/workbench/planning-runs/audit-events",
        params={"run_id": "TST-CASE-BASELINE"},
    )
    assert audit.status_code == 200
    assert audit.json()["Data"]["AuditEvents"][0]["Action"] == "TestCaseAcceptanceDecision"


def test_test_case_acceptance_rejects_confirmation_before_case_passes():
    # BE-DATA-014
    store = WorkbenchStateStore()
    seed_baseline_test_data(store)
    client = TestClient(create_app(state_store=store))

    response = client.post(
        "/planner/workbench/test-data/acceptance/TST-CASE-BASELINE/decision",
        json={
            "Decision": "Confirm",
            "ActorID": "planner-acceptance",
            "DecidedAt": "2026-06-20T10:05:00+00:00",
        },
    )

    assert response.status_code == 409
    data = response.json()["Data"]
    assert data["Status"] == "TestCaseNotPassed"
    assert data["AcceptanceStatus"] == "NeedsExecution"


def test_plan_publication_lifecycle_records_package_audit_and_rbac():
    store = WorkbenchStateStore()
    seed_baseline_test_data(store)
    client = TestClient(create_app(state_store=store, require_auth=True))
    planner_headers = {"X-Actor-ID": "planner-1", "X-Actor-Role": "Planner"}
    admin_headers = {"X-Actor-ID": "admin-1", "X-Actor-Role": "Admin"}

    _enqueue_claim_and_execute_with_auth(
        client,
        "TST-RUN-BASELINE-001",
        planner_headers=planner_headers,
    )

    initial = client.get(
        "/planner/workbench/planning-runs/TST-RUN-BASELINE-001/publication",
        headers={"X-Actor-ID": "viewer-1", "X-Actor-Role": "Viewer"},
    )
    assert initial.status_code == 200
    assert initial.json()["Data"]["PublicationStatus"] == "Draft"
    assert initial.json()["Data"]["AllowedActions"] == ["Review"]

    illegal_approve = client.post(
        "/planner/workbench/planning-runs/TST-RUN-BASELINE-001/publication/approve",
        headers=planner_headers,
        json={
            "ActorID": "planner-1",
            "OccurredAt": "2026-06-19T09:00:00+00:00",
        },
    )
    assert illegal_approve.status_code == 409
    assert illegal_approve.json()["Data"]["Status"] == "PublicationTransitionConflict"

    reviewed = client.post(
        "/planner/workbench/planning-runs/TST-RUN-BASELINE-001/publication/review",
        headers=planner_headers,
        json={
            "ActorID": "planner-1",
            "OccurredAt": "2026-06-19T09:01:00+00:00",
            "Comment": "Baseline schedule reviewed.",
        },
    )
    assert reviewed.status_code == 200
    assert reviewed.json()["Data"]["PublicationStatus"] == "Reviewed"

    approved = client.post(
        "/planner/workbench/planning-runs/TST-RUN-BASELINE-001/publication/approve",
        headers=planner_headers,
        json={
            "ActorID": "planner-1",
            "OccurredAt": "2026-06-19T09:02:00+00:00",
        },
    )
    assert approved.status_code == 200
    assert approved.json()["Data"]["PublicationStatus"] == "Approved"

    planner_publish = client.post(
        "/planner/workbench/planning-runs/TST-RUN-BASELINE-001/publication/publish",
        headers=planner_headers,
        json={
            "ActorID": "planner-1",
            "OccurredAt": "2026-06-19T09:03:00+00:00",
        },
    )
    assert planner_publish.status_code == 403
    assert planner_publish.json()["Data"]["Status"] == "PermissionDenied"

    published = client.post(
        "/planner/workbench/planning-runs/TST-RUN-BASELINE-001/publication/publish",
        headers=admin_headers,
        json={
            "ActorID": "admin-1",
            "OccurredAt": "2026-06-19T09:04:00+00:00",
            "TargetSystems": ["InternalPlanning", "MES-Contract"],
        },
    )
    assert published.status_code == 200
    published_data = published.json()["Data"]
    assert published_data["PublicationStatus"] == "Published"
    package = published_data["PublicationPackage"]
    assert package["RunID"] == "TST-RUN-BASELINE-001"
    assert package["ScheduleFingerprint"] == published_data["ScheduleFingerprint"]
    assert package["TargetSystems"] == ["InternalPlanning", "MES-Contract"]

    revoked = client.post(
        "/planner/workbench/planning-runs/TST-RUN-BASELINE-001/publication/revoke",
        headers=admin_headers,
        json={
            "ActorID": "admin-1",
            "OccurredAt": "2026-06-19T09:05:00+00:00",
            "Comment": "Hold for demand review.",
        },
    )
    assert revoked.status_code == 200
    assert revoked.json()["Data"]["PublicationStatus"] == "PublicationRevoked"

    audit = client.get(
        "/planner/workbench/planning-runs/audit-events",
        headers=planner_headers,
        params={"run_id": "TST-RUN-BASELINE-001"},
    )
    actions = [item["Action"] for item in audit.json()["Data"]["AuditEvents"]]
    assert "PlanPublicationReview" in actions
    assert "PlanPublicationApprove" in actions
    assert "PlanPublicationPublish" in actions
    assert "PlanPublicationRevoke" in actions


def test_publishing_new_plan_supersedes_prior_published_plan_for_same_problem():
    store = WorkbenchStateStore()
    seed_baseline_test_data(store)
    client = TestClient(create_app(state_store=store))

    _enqueue_claim_and_execute(client, "TST-RUN-BASELINE-001")
    first_published = _review_approve_publish(client, "TST-RUN-BASELINE-001")
    assert first_published["PublicationStatus"] == "Published"

    client.post(
        "/planner/workbench/planning-runs",
        json={
            "RunID": "TST-RUN-BASELINE-002",
            "ProblemID": "TST-PROBLEM-BASELINE",
            "MasterDataVersionID": BASELINE_MASTER_DATA_VERSION_ID,
            "OperationalStateSnapshotID": BASELINE_OPERATIONAL_STATE_ID,
            "ScheduleStartAt": "2026-06-22T08:00:00+00:00",
            "TimeBufferMinutes": 480,
            "SolverBackendID": "ortools",
            "RequestedBy": "planner-e2e",
            "RequestedAt": "2026-06-19T08:10:00+00:00",
        },
    )
    _enqueue_claim_and_execute(client, "TST-RUN-BASELINE-002")
    second_published = _review_approve_publish(client, "TST-RUN-BASELINE-002")
    assert second_published["PublicationStatus"] == "Published"
    assert second_published["SupersedesRunID"] == "TST-RUN-BASELINE-001"

    first = client.get(
        "/planner/workbench/planning-runs/TST-RUN-BASELINE-001/publication"
    )
    assert first.status_code == 200
    assert first.json()["Data"]["PublicationStatus"] == "Superseded"
    assert first.json()["Data"]["SupersededByRunID"] == "TST-RUN-BASELINE-002"


def _enqueue_claim_and_execute(client: TestClient, run_id: str) -> dict[str, object]:
    assert client.post(
        f"/planner/workbench/planning-runs/{run_id}/enqueue",
        json={
            "EnqueuedBy": "planner-e2e",
            "EnqueuedAt": "2026-06-19T08:01:00+00:00",
        },
    ).status_code == 200
    claim = client.post(
        "/planner/workbench/planning-runs/jobs/claim-next",
        json={
            "WorkerID": "worker-e2e",
            "ClaimedAt": "2026-06-19T08:02:00+00:00",
            "LeaseSeconds": 600,
        },
    )
    assert claim.status_code == 200
    claimed = claim.json()["Data"]["PlanningRun"]
    assert claimed["RunID"] == run_id
    execute = client.post(
        f"/planner/workbench/planning-runs/{run_id}/execute",
        json={
            "ExecutedBy": "worker-e2e",
            "StartedAt": "2026-06-19T08:03:00+00:00",
            "CompletedAt": "2026-06-19T08:04:00+00:00",
            "TimeLimitSeconds": 30,
            "LeaseToken": claimed["LeaseToken"],
        },
    )
    assert execute.status_code == 200
    return execute.json()["Data"]["PlanningRun"]


def _enqueue_claim_and_execute_with_auth(
    client: TestClient,
    run_id: str,
    *,
    planner_headers: dict[str, str],
) -> dict[str, object]:
    assert client.post(
        f"/planner/workbench/planning-runs/{run_id}/enqueue",
        headers=planner_headers,
        json={
            "EnqueuedBy": "planner-1",
            "EnqueuedAt": "2026-06-19T08:01:00+00:00",
        },
    ).status_code == 200
    worker_headers = {"X-Actor-ID": "worker-1", "X-Actor-Role": "Worker"}
    claim = client.post(
        "/planner/workbench/planning-runs/jobs/claim-next",
        headers=worker_headers,
        json={
            "WorkerID": "worker-1",
            "ClaimedAt": "2026-06-19T08:02:00+00:00",
            "LeaseSeconds": 600,
        },
    )
    assert claim.status_code == 200
    claimed = claim.json()["Data"]["PlanningRun"]
    execute = client.post(
        f"/planner/workbench/planning-runs/{run_id}/execute",
        headers=worker_headers,
        json={
            "ExecutedBy": "worker-1",
            "StartedAt": "2026-06-19T08:03:00+00:00",
            "CompletedAt": "2026-06-19T08:04:00+00:00",
            "TimeLimitSeconds": 30,
            "LeaseToken": claimed["LeaseToken"],
        },
    )
    assert execute.status_code == 200
    return execute.json()["Data"]["PlanningRun"]


def _review_approve_publish(client: TestClient, run_id: str) -> dict[str, object]:
    for action, minute in [("review", "01"), ("approve", "02"), ("publish", "03")]:
        response = client.post(
            f"/planner/workbench/planning-runs/{run_id}/publication/{action}",
            json={
                "ActorID": "planner-e2e" if action != "publish" else "admin-e2e",
                "OccurredAt": f"2026-06-19T09:{minute}:00+00:00",
            },
        )
        assert response.status_code == 200
        data = response.json()["Data"]
    return data


def _buffer_order_count(board: dict[str, object], stage: str) -> int:
    row = next(item for item in board["Rows"] if item["Stage"] == stage)
    return sum(cell["OrderCount"] for cell in row["Cells"])
