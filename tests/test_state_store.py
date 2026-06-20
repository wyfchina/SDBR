from datetime import datetime, timezone

from fastapi.testclient import TestClient

from sdbr.api import app, create_app
from sdbr.operational_state import create_operational_state_snapshot
from sdbr.planner_view import InventoryBufferPolicy
from sdbr.release_authorization import create_release_authorization
from sdbr.release_candidates import MaterialAvailability, WipLimit
from sdbr.replanning import create_replan_request
from sdbr.state_store import SQLiteWorkbenchStateStore, WorkbenchStateStore


def test_default_service_uses_sqlite_state_store():
    assert isinstance(
        app.state.workbench_state_store,
        SQLiteWorkbenchStateStore,
    )


def test_shared_state_store_survives_application_recreation():
    store = WorkbenchStateStore()
    first_client = TestClient(create_app(state_store=store))
    create_response = first_client.post(
        "/planner/workbench/operational-state/snapshots",
        json={
            "SnapshotID": "OPS-PERSISTENCE-BOUNDARY",
            "CapturedAt": "2026-06-20T06:00:00+00:00",
        },
    )
    assert create_response.status_code == 200

    recreated_client = TestClient(create_app(state_store=store))
    response = recreated_client.get(
        "/planner/workbench/operational-state/snapshots/OPS-PERSISTENCE-BOUNDARY"
    )

    assert response.status_code == 200
    assert response.json()["Data"]["Snapshot"]["SnapshotID"] == (
        "OPS-PERSISTENCE-BOUNDARY"
    )


def test_sqlite_state_store_round_trips_all_state_collections(tmp_path):
    database_path = tmp_path / "workbench.db"
    store = SQLiteWorkbenchStateStore(database_path)
    captured_at = datetime(2026, 6, 20, 6, tzinfo=timezone.utc)
    store.execution_events.append(
        {
            "AuthorizationID": "REL-1",
            "OrderID": "WO-1",
            "EventType": "StartedOperation",
            "EventAt": "2026-06-20T06:05:00+00:00",
        }
    )
    replan_request = create_replan_request(
        problem_id="PLAN-1",
        order_id="WO-1",
        planned_release_at=captured_at,
        detected_at=datetime(2026, 6, 20, 8, tzinfo=timezone.utc),
        reason_code="DeviationAtReplanThreshold",
        deviation_minutes=120,
        consecutive_blocked_count=0,
        replan_required=True,
        source="ExecutionVariance",
        source_reference_id="RDP-1",
        requested_by="planner-1",
    )
    assert replan_request is not None
    store.replan_requests.append(replan_request)
    store.replan_schedule_snapshots[replan_request.request_id] = {
        "SolverStatus": "Optimal",
        "GeneratedAt": "2026-06-20T08:00:00+00:00",
    }
    authorization = create_release_authorization(
        request_id=replan_request.request_id,
        candidate={
            "OrderID": "WO-1",
            "RecommendedAction": "ReadyForRelease",
        },
        released_by="planner-1",
        released_at=datetime(2026, 6, 20, 6, 5, tzinfo=timezone.utc),
        decision_package_id="RDP-1",
    )
    store.release_authorizations.append(authorization)
    snapshot = create_operational_state_snapshot(
        snapshot_id="OPS-1",
        captured_at=captured_at,
        inventory_buffers=[
            InventoryBufferPolicy(
                item_id="RM-1",
                location_id="MAIN",
                on_hand_qty=80,
                red_zone_qty=50,
                yellow_zone_qty=120,
                green_zone_qty=200,
            )
        ],
        material_availability=[
            MaterialAvailability(
                item_id="RM-1",
                location_id="MAIN",
                allocated_qty=10,
                inbound_qty=20,
                inbound_available_at=datetime(
                    2026, 6, 20, 7, tzinfo=timezone.utc
                ),
            )
        ],
        wip_limits=[WipLimit("DRUM", 1, 5)],
    )
    store.operational_state_snapshots[snapshot.snapshot_id] = snapshot
    store.release_decision_packages["RDP-1"] = {
        "DecisionPackageID": "RDP-1",
        "RequestID": replan_request.request_id,
    }

    store.save()
    restored = SQLiteWorkbenchStateStore(database_path)

    assert restored.execution_events == store.execution_events
    assert restored.replan_requests == store.replan_requests
    assert restored.replan_schedule_snapshots == store.replan_schedule_snapshots
    assert restored.release_authorizations == store.release_authorizations
    assert restored.operational_state_snapshots == store.operational_state_snapshots
    assert restored.release_decision_packages == store.release_decision_packages


def test_sqlite_state_store_is_committed_after_successful_api_write(tmp_path):
    database_path = tmp_path / "workbench.db"
    client = TestClient(
        create_app(state_store=SQLiteWorkbenchStateStore(database_path))
    )
    response = client.post(
        "/planner/workbench/operational-state/snapshots",
        json={
            "SnapshotID": "OPS-SQLITE",
            "CapturedAt": "2026-06-20T06:00:00+00:00",
        },
    )
    assert response.status_code == 200

    restored_client = TestClient(
        create_app(state_store=SQLiteWorkbenchStateStore(database_path))
    )
    restored = restored_client.get(
        "/planner/workbench/operational-state/snapshots/OPS-SQLITE"
    )

    assert restored.status_code == 200


def test_sqlite_state_store_reports_health_and_recovers_corrupt_database(tmp_path):
    database_path = tmp_path / "workbench.db"
    store = SQLiteWorkbenchStateStore(database_path)
    snapshot = create_operational_state_snapshot(
        snapshot_id="OPS-RECOVERY",
        captured_at=datetime(2026, 6, 20, 6, tzinfo=timezone.utc),
        inventory_buffers=[],
        material_availability=[],
        wip_limits=[],
    )
    store.operational_state_snapshots[snapshot.snapshot_id] = snapshot
    store.save()

    health = store.health()
    assert health["Backend"] == "SQLite"
    assert health["Status"] == "Healthy"
    assert health["SchemaVersion"] == 1
    assert health["StateCounts"]["OperationalStateSnapshots"] == 1
    assert health["LastSavedAt"] is not None
    assert store.backup_path.exists()

    database_path.write_bytes(b"not-a-sqlite-database")
    restored = SQLiteWorkbenchStateStore(database_path)

    assert "OPS-RECOVERY" in restored.operational_state_snapshots
    assert restored.health()["RecoveryStatus"] == "RecoveredFromBackup"


def test_state_store_health_endpoint_exposes_backend_status(tmp_path):
    client = TestClient(
        create_app(
            state_store=SQLiteWorkbenchStateStore(tmp_path / "workbench.db")
        )
    )

    response = client.get("/planner/workbench/state-store/health")

    assert response.status_code == 200
    data = response.json()["Data"]
    assert data["Backend"] == "SQLite"
    assert data["Status"] == "Healthy"
    assert data["SchemaVersion"] == 1


def test_sqlite_state_store_rejects_stale_writer_and_succeeds_after_retry(tmp_path):
    database_path = tmp_path / "workbench.db"
    first_store = SQLiteWorkbenchStateStore(database_path)
    stale_store = SQLiteWorkbenchStateStore(database_path)
    first_client = TestClient(create_app(state_store=first_store))
    stale_client = TestClient(create_app(state_store=stale_store))
    first_response = first_client.post(
        "/planner/workbench/operational-state/snapshots",
        json={
            "SnapshotID": "OPS-WRITER-A",
            "CapturedAt": "2026-06-20T06:00:00+00:00",
        },
    )
    assert first_response.status_code == 200
    second_payload = {
        "SnapshotID": "OPS-WRITER-B",
        "CapturedAt": "2026-06-20T06:05:00+00:00",
    }

    conflict = stale_client.post(
        "/planner/workbench/operational-state/snapshots",
        json=second_payload,
    )

    assert conflict.status_code == 409
    conflict_data = conflict.json()["Data"]
    assert conflict_data["Status"] == "StateStoreRevisionConflict"
    assert conflict_data["ExpectedRevision"] == 0
    assert conflict_data["CurrentRevision"] == 1

    retry = stale_client.post(
        "/planner/workbench/operational-state/snapshots",
        json=second_payload,
    )
    assert retry.status_code == 200
    restored_client = TestClient(
        create_app(state_store=SQLiteWorkbenchStateStore(database_path))
    )
    assert restored_client.get(
        "/planner/workbench/operational-state/snapshots/OPS-WRITER-A"
    ).status_code == 200
    assert restored_client.get(
        "/planner/workbench/operational-state/snapshots/OPS-WRITER-B"
    ).status_code == 200


def test_api_exposes_revision_header_and_rejects_stale_client_revision():
    client = TestClient(create_app(state_store=WorkbenchStateStore()))

    initial = client.get("/planner/workbench/state-store/health")
    assert initial.status_code == 200
    assert initial.headers["X-Workbench-Revision"] == "0"

    first_write = client.post(
        "/planner/workbench/operational-state/snapshots",
        headers={"If-Match": "0"},
        json={
            "SnapshotID": "OPS-CLIENT-A",
            "CapturedAt": "2026-06-20T06:00:00+00:00",
        },
    )
    assert first_write.status_code == 200
    assert first_write.headers["X-Workbench-Revision"] == "1"

    stale_write = client.post(
        "/planner/workbench/operational-state/snapshots",
        headers={"If-Match": "0"},
        json={
            "SnapshotID": "OPS-CLIENT-B",
            "CapturedAt": "2026-06-20T06:05:00+00:00",
        },
    )
    assert stale_write.status_code == 409
    assert stale_write.headers["X-Workbench-Revision"] == "1"
    stale_data = stale_write.json()["Data"]
    assert stale_data["Status"] == "StateStoreRevisionConflict"
    assert stale_data["ExpectedRevision"] == 0
    assert stale_data["CurrentRevision"] == 1

    assert client.get(
        "/planner/workbench/operational-state/snapshots/OPS-CLIENT-B"
    ).status_code == 404

    retry = client.post(
        "/planner/workbench/operational-state/snapshots",
        headers={"If-Match": "1"},
        json={
            "SnapshotID": "OPS-CLIENT-B",
            "CapturedAt": "2026-06-20T06:05:00+00:00",
        },
    )
    assert retry.status_code == 200
    assert retry.headers["X-Workbench-Revision"] == "2"
