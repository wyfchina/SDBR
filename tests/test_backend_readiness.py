from concurrent.futures import ThreadPoolExecutor
from time import perf_counter, sleep

from fastapi.testclient import TestClient

from sdbr.api import create_app
from sdbr.state_store import SQLiteWorkbenchStateStore, WorkbenchStateStore


def _queued_run(run_id: str) -> dict[str, object]:
    return {
        "RunID": run_id,
        "ProblemID": f"PLAN-{run_id}",
        "Status": "Queued",
        "RequestedAt": "2026-06-19T08:00:00+00:00",
        "EnqueuedAt": "2026-06-19T08:01:00+00:00",
        "NextAttemptAt": "2026-06-19T08:01:00+00:00",
        "AttemptCount": 0,
        "MaxAttempts": 3,
        "RetryDelaySeconds": 60,
        "SolverBackendID": "ortools",
        "StatusHistory": [],
    }


def test_two_api_instances_allow_only_one_worker_to_persist_claim(
    tmp_path,
    monkeypatch,
):
    database_path = tmp_path / "workbench.db"
    seed_store = SQLiteWorkbenchStateStore(database_path)
    seed_store.planning_runs["RUN-CROSS-PROCESS"] = _queued_run(
        "RUN-CROSS-PROCESS"
    )
    seed_store.save()
    first_client = TestClient(
        create_app(state_store=SQLiteWorkbenchStateStore(database_path))
    )
    second_client = TestClient(
        create_app(state_store=SQLiteWorkbenchStateStore(database_path))
    )

    def slow_token(_length):
        sleep(0.2)
        return "lease-cross-instance"

    monkeypatch.setattr("sdbr.api.token_urlsafe", slow_token)

    def claim(client_and_worker):
        client, worker_id = client_and_worker
        return client.post(
            "/planner/workbench/planning-runs/jobs/claim-next",
            json={
                "WorkerID": worker_id,
                "ClaimedAt": "2026-06-19T08:02:00+00:00",
                "LeaseSeconds": 120,
            },
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        responses = list(
            executor.map(
                claim,
                [(first_client, "worker-a"), (second_client, "worker-b")],
            )
        )

    assert sorted(response.status_code for response in responses) == [200, 409]
    conflict = next(response for response in responses if response.status_code == 409)
    assert conflict.json()["Data"]["Status"] == "StateStoreRevisionConflict"
    restored = SQLiteWorkbenchStateStore(database_path)
    assert restored.planning_runs["RUN-CROSS-PROCESS"]["Status"] == "Running"
    assert sum(
        event["Action"] == "PlanningRunClaimed"
        for event in restored.audit_events
    ) == 1


def test_planning_run_list_and_metrics_meet_backend_performance_baseline():
    store = WorkbenchStateStore()
    for index in range(1000):
        status = "Queued" if index % 2 == 0 else "Completed"
        planning_run = _queued_run(f"RUN-{index:04d}")
        planning_run["Status"] = status
        planning_run["AttemptCount"] = index % 3
        store.planning_runs[str(planning_run["RunID"])] = planning_run
    client = TestClient(create_app(state_store=store))

    started_at = perf_counter()
    list_response = client.get(
        "/planner/workbench/planning-runs",
        params={"status": "Queued", "limit": 200},
    )
    metrics_response = client.get(
        "/planner/workbench/planning-runs/metrics",
        params={"observed_at": "2026-06-19T09:00:00+00:00"},
    )
    elapsed_seconds = perf_counter() - started_at

    assert list_response.status_code == 200
    assert list_response.json()["Data"]["Total"] == 500
    assert list_response.json()["Data"]["Count"] == 200
    assert metrics_response.status_code == 200
    assert metrics_response.json()["Data"]["Total"] == 1000
    assert elapsed_seconds < 2.0


def test_backup_recovery_restores_planning_runs_and_audit_events(tmp_path):
    database_path = tmp_path / "workbench.db"
    store = SQLiteWorkbenchStateStore(database_path)
    store.planning_runs["RUN-RECOVERY"] = _queued_run("RUN-RECOVERY")
    store.audit_events.append(
        {
            "EventID": "AUD-00000001",
            "RunID": "RUN-RECOVERY",
            "Action": "PlanningRunEnqueued",
            "ActorID": "planner-1",
            "OccurredAt": "2026-06-19T08:01:00+00:00",
            "Details": {},
        }
    )
    store.save()
    database_path.write_bytes(b"not-a-sqlite-database")

    restored = SQLiteWorkbenchStateStore(database_path)

    assert restored.health()["RecoveryStatus"] == "RecoveredFromBackup"
    assert restored.planning_runs["RUN-RECOVERY"]["Status"] == "Queued"
    assert restored.audit_events[0]["Action"] == "PlanningRunEnqueued"
