from __future__ import annotations

import argparse
import json
import signal
from dataclasses import dataclass
from datetime import datetime, timezone
from threading import Event, Thread
from typing import Callable, Protocol
from urllib.error import HTTPError
from urllib.request import Request, urlopen


class PlanningRunClient(Protocol):
    def claim_next(self, **payload) -> dict[str, object] | None: ...

    def renew_lease(self, **payload) -> dict[str, object] | None: ...

    def execute(self, **payload) -> dict[str, object]: ...


@dataclass(frozen=True, slots=True)
class PlanningRunWorkerConfig:
    worker_id: str
    lease_seconds: int = 360
    time_limit_seconds: int = 300
    heartbeat_seconds: int = 60
    poll_seconds: float = 5.0

    def __post_init__(self) -> None:
        if self.heartbeat_seconds <= 0:
            raise ValueError("heartbeat_seconds must be positive")
        if self.lease_seconds <= self.heartbeat_seconds:
            raise ValueError("lease_seconds must be greater than heartbeat_seconds")
        if self.time_limit_seconds <= 0:
            raise ValueError("time_limit_seconds must be positive")
        if self.poll_seconds <= 0:
            raise ValueError("poll_seconds must be positive")


class HttpPlanningRunClient:
    def __init__(
        self,
        base_url: str,
        *,
        actor_id: str | None = None,
        actor_role: str = "Worker",
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.actor_id = actor_id
        self.actor_role = actor_role

    def claim_next(
        self,
        *,
        worker_id: str,
        claimed_at: datetime,
        lease_seconds: int,
    ) -> dict[str, object] | None:
        return self._post(
            "/planner/workbench/planning-runs/jobs/claim-next",
            {
                "WorkerID": worker_id,
                "ClaimedAt": claimed_at.isoformat(),
                "LeaseSeconds": lease_seconds,
            },
        )

    def renew_lease(
        self,
        *,
        run_id: str,
        worker_id: str,
        lease_token: str,
        renewed_at: datetime,
        lease_seconds: int,
    ) -> dict[str, object] | None:
        return self._post(
            f"/planner/workbench/planning-runs/{run_id}/renew-lease",
            {
                "WorkerID": worker_id,
                "LeaseToken": lease_token,
                "RenewedAt": renewed_at.isoformat(),
                "LeaseSeconds": lease_seconds,
            },
        )

    def execute(
        self,
        *,
        run_id: str,
        executed_by: str,
        started_at: datetime,
        time_limit_seconds: int,
        lease_token: str,
    ) -> dict[str, object]:
        result = self._post(
            f"/planner/workbench/planning-runs/{run_id}/execute",
            {
                "ExecutedBy": executed_by,
                "StartedAt": started_at.isoformat(),
                "TimeLimitSeconds": time_limit_seconds,
                "LeaseToken": lease_token,
            },
            timeout_seconds=time_limit_seconds + 30,
        )
        if result is None:
            raise RuntimeError("Planning run execution returned no result.")
        return result

    def _post(
        self,
        path: str,
        payload: dict[str, object],
        timeout_seconds: float = 30,
    ) -> dict[str, object] | None:
        headers = {"Content-Type": "application/json"}
        if self.actor_id:
            headers.update(
                {
                    "X-Actor-ID": self.actor_id,
                    "X-Actor-Role": self.actor_role,
                }
            )
        request = Request(
            f"{self.base_url}{path}",
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        try:
            with urlopen(request, timeout=timeout_seconds) as response:
                body = json.loads(response.read().decode("utf-8"))
        except HTTPError as error:
            detail = error.read().decode("utf-8")
            raise RuntimeError(
                f"Planning worker request failed with HTTP {error.code}: {detail}"
            ) from error
        return body["Data"]["PlanningRun"]


class PlanningRunWorker:
    def __init__(
        self,
        *,
        client: PlanningRunClient,
        config: PlanningRunWorkerConfig,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        self.client = client
        self.config = config
        self.now = now or (lambda: datetime.now(timezone.utc))

    def run_once(self) -> bool:
        planning_run = self.client.claim_next(
            worker_id=self.config.worker_id,
            claimed_at=self.now(),
            lease_seconds=self.config.lease_seconds,
        )
        if planning_run is None:
            return False
        run_id = str(planning_run["RunID"])
        lease_token = str(planning_run["LeaseToken"])
        heartbeat_stop = Event()
        heartbeat = Thread(
            target=self._renew_lease_until_stopped,
            args=(run_id, lease_token, heartbeat_stop),
            daemon=True,
        )
        heartbeat.start()
        try:
            self.client.execute(
                run_id=run_id,
                executed_by=self.config.worker_id,
                started_at=self.now(),
                time_limit_seconds=self.config.time_limit_seconds,
                lease_token=lease_token,
            )
        finally:
            heartbeat_stop.set()
            heartbeat.join(timeout=self.config.heartbeat_seconds + 1)
        return True

    def run_forever(self, *, stop_event: Event) -> None:
        while not stop_event.is_set():
            processed = self.run_once()
            if not processed:
                stop_event.wait(self.config.poll_seconds)

    def _renew_lease_until_stopped(
        self,
        run_id: str,
        lease_token: str,
        stop_event: Event,
    ) -> None:
        while not stop_event.wait(self.config.heartbeat_seconds):
            self.client.renew_lease(
                run_id=run_id,
                worker_id=self.config.worker_id,
                lease_token=lease_token,
                renewed_at=self.now(),
                lease_seconds=self.config.lease_seconds,
            )


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the SDBR planning worker.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8765")
    parser.add_argument("--worker-id", required=True)
    parser.add_argument("--lease-seconds", type=int, default=360)
    parser.add_argument("--time-limit-seconds", type=int, default=300)
    parser.add_argument("--heartbeat-seconds", type=int, default=60)
    parser.add_argument("--poll-seconds", type=float, default=5.0)
    args = parser.parse_args()
    stop_event = Event()

    def request_stop(_signum, _frame) -> None:
        stop_event.set()

    signal.signal(signal.SIGINT, request_stop)
    signal.signal(signal.SIGTERM, request_stop)
    worker = PlanningRunWorker(
        client=HttpPlanningRunClient(
            args.base_url,
            actor_id=args.worker_id,
            actor_role="Worker",
        ),
        config=PlanningRunWorkerConfig(
            worker_id=args.worker_id,
            lease_seconds=args.lease_seconds,
            time_limit_seconds=args.time_limit_seconds,
            heartbeat_seconds=args.heartbeat_seconds,
            poll_seconds=args.poll_seconds,
        ),
    )
    worker.run_forever(stop_event=stop_event)


if __name__ == "__main__":
    main()
