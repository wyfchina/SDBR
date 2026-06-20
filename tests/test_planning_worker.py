from datetime import datetime, timezone
from threading import Event

import json

from sdbr.planning_worker import (
    HttpPlanningRunClient,
    PlanningRunWorker,
    PlanningRunWorkerConfig,
)


class FakePlanningRunClient:
    def __init__(self) -> None:
        self.claim_calls = []
        self.execute_calls = []

    def claim_next(self, **payload):
        self.claim_calls.append(payload)
        return {
            "RunID": "RUN-1",
            "LeaseToken": "lease-1",
            "WorkerID": payload["worker_id"],
        }

    def renew_lease(self, **payload):
        return None

    def execute(self, **payload):
        self.execute_calls.append(payload)
        return {"RunID": payload["run_id"], "Status": "Completed"}


def test_worker_run_once_claims_and_executes_owned_planning_run():
    client = FakePlanningRunClient()
    worker = PlanningRunWorker(
        client=client,
        config=PlanningRunWorkerConfig(
            worker_id="worker-1",
            lease_seconds=360,
            time_limit_seconds=300,
            heartbeat_seconds=60,
        ),
        now=lambda: datetime(2026, 6, 16, 8, 0, tzinfo=timezone.utc),
    )

    processed = worker.run_once()

    assert processed is True
    assert client.claim_calls[0]["worker_id"] == "worker-1"
    assert client.execute_calls == [
        {
            "run_id": "RUN-1",
            "executed_by": "worker-1",
            "started_at": datetime(2026, 6, 16, 8, 0, tzinfo=timezone.utc),
            "time_limit_seconds": 300,
            "lease_token": "lease-1",
        }
    ]


def test_worker_honors_stop_signal_before_claiming_more_work():
    client = FakePlanningRunClient()
    stop_event = Event()
    stop_event.set()
    worker = PlanningRunWorker(
        client=client,
        config=PlanningRunWorkerConfig(worker_id="worker-1"),
    )

    worker.run_forever(stop_event=stop_event)

    assert client.claim_calls == []


def test_http_worker_execution_timeout_exceeds_solver_time_limit(monkeypatch):
    observed = {}

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def read(self):
            return json.dumps(
                {"Data": {"PlanningRun": {"RunID": "RUN-1"}}}
            ).encode("utf-8")

    def fake_urlopen(request, timeout):
        observed["timeout"] = timeout
        observed["actor_id"] = request.get_header("X-actor-id")
        observed["actor_role"] = request.get_header("X-actor-role")
        return FakeResponse()

    monkeypatch.setattr("sdbr.planning_worker.urlopen", fake_urlopen)
    client = HttpPlanningRunClient(
        "http://127.0.0.1:8765",
        actor_id="worker-1",
        actor_role="Worker",
    )

    client.execute(
        run_id="RUN-1",
        executed_by="worker-1",
        started_at=datetime(2026, 6, 16, 8, 0, tzinfo=timezone.utc),
        time_limit_seconds=300,
        lease_token="lease-1",
    )

    assert observed["timeout"] == 330
    assert observed["actor_id"] == "worker-1"
    assert observed["actor_role"] == "Worker"
