"""Persistence evidence for BE-DDMRP-007 and existing state-store capabilities."""

from copy import deepcopy
from datetime import datetime, timezone
import json
import sqlite3

from fastapi.testclient import TestClient
import pytest

from sdbr.api import app, create_app
from sdbr.operational_state import create_operational_state_snapshot
from sdbr.planner_view import InventoryBufferPolicy
from sdbr.release_authorization import create_release_authorization
from sdbr.release_candidates import MaterialAvailability, WipLimit
from sdbr.replanning import create_replan_request
from sdbr.state_store import SQLiteWorkbenchStateStore, WorkbenchStateStore
from sdbr.state_store import StateStoreManagedRequestRejected


_DDMRP_LEDGER_VALUES = {
    "ddmrp_evaluation_runs": {
        "EVAL-1": {"EvaluationID": "EVAL-1", "EvaluationRequestID": "REQ-1"}
    },
    "ddmrp_evaluation_rows": {
        "ROW-1": {"EvaluationRowID": "ROW-1", "EvaluationID": "EVAL-1"}
    },
    "ddmrp_replenishment_chains": {
        "CHAIN-1": {"LogicalReplenishmentID": "CHAIN-1", "RecordVersion": 1}
    },
    "ddmrp_replenishment_recommendations": {
        "REC-1": {"RecommendationID": "REC-1", "EvaluationID": "EVAL-1"}
    },
    "ddmrp_replenishment_events": [
        {"EventID": "EVENT-1", "EvaluationID": "EVAL-1"}
    ],
    "ddmrp_active_replenishment_graphs": {
        "CHAIN-1": {
            "LogicalReplenishmentID": "CHAIN-1",
            "RecommendationID": "REC-1",
        }
    },
    "ddmrp_evaluation_request_results": {
        "REQ-1": {"EvaluationRequestID": "REQ-1", "EvaluationID": "EVAL-1"}
    },
}


def _seed_ddmrp_evaluation_ledgers(store: WorkbenchStateStore) -> None:
    for name, value in _DDMRP_LEDGER_VALUES.items():
        target = getattr(store, name)
        if isinstance(target, list):
            target.extend(deepcopy(value))
        else:
            target.update(deepcopy(value))


def _assert_ddmrp_evaluation_ledgers(store: WorkbenchStateStore) -> None:
    for name, value in _DDMRP_LEDGER_VALUES.items():
        assert getattr(store, name) == value


class _FailingMemoryWorkbenchStateStore(WorkbenchStateStore):
    fail_save = False

    def save(self):
        if self.fail_save:
            raise OSError("memory save failed")
        return super().save()


def test_default_service_uses_sqlite_state_store():
    assert isinstance(
        app.state.workbench_state_store,
        SQLiteWorkbenchStateStore,
    )


# BE-RUN-007 / BE-RUN-011
def test_atomic_update_captures_controlled_rejection_revision_inside_store_boundary(
    tmp_path,
):
    stores = (
        WorkbenchStateStore(),
        SQLiteWorkbenchStateStore(tmp_path / "controlled-rejection.db"),
    )
    for store in stores:
        store.audit_events.append({"Action": "InitialRevision"})
        store.save()
        rejection = StateStoreManagedRequestRejected(
            "Controlled request rejection."
        )

        def reject():
            raise rejection

        try:
            store.atomic_update(reject)
        except StateStoreManagedRequestRejected as error:
            assert error.current_revision == 1
        else:
            raise AssertionError("Controlled rejection was not propagated.")
        assert store.current_revision() == 1


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
    # Persistence evidence: BE-SDBR-007, BE-SDBR-008, BE-SDBR-009, BE-RUN-011.
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
    store.planning_demand_commitments["DC-1"] = {
        "DemandCommitmentID": "DC-1",
        "Status": "Active",
    }
    store.planning_reservation_batches["PRB-1"] = {
        "ReservationBatchID": "PRB-1",
        "Status": "ActivePlanReservation",
    }
    store.ccr_capacity_reservations["CCR-RES-1"] = {
        "CapacityReservationID": "CCR-RES-1",
        "ReservedMinutes": 60,
    }
    store.material_planning_allocations["MPA-1"] = {
        "MaterialAllocationID": "MPA-1",
        "AllocatedQty": 5,
    }
    store.planning_reservation_events.append({"EventID": "PRE-1"})
    store.processed_planning_event_keys.add("CONFIRM-1")

    store.save()
    restored = SQLiteWorkbenchStateStore(database_path)

    assert restored.execution_events == store.execution_events
    assert restored.replan_requests == store.replan_requests
    assert restored.replan_schedule_snapshots == store.replan_schedule_snapshots
    assert restored.release_authorizations == store.release_authorizations
    assert restored.operational_state_snapshots == store.operational_state_snapshots
    assert restored.release_decision_packages == store.release_decision_packages
    assert restored.planning_demand_commitments == store.planning_demand_commitments
    assert restored.planning_reservation_batches == store.planning_reservation_batches
    assert restored.ccr_capacity_reservations == store.ccr_capacity_reservations
    assert restored.material_planning_allocations == store.material_planning_allocations
    assert restored.planning_reservation_events == store.planning_reservation_events
    assert restored.processed_planning_event_keys == store.processed_planning_event_keys
    assert restored.health()["StateCounts"]["PlanningDemandCommitments"] == 1
    assert restored.health()["StateCounts"]["PlanningReservationBatches"] == 1
    assert restored.health()["StateCounts"]["CcrCapacityReservations"] == 1
    assert restored.health()["StateCounts"]["MaterialPlanningAllocations"] == 1
    assert restored.health()["StateCounts"]["PlanningReservationEvents"] == 1
    assert restored.health()["StateCounts"]["ProcessedPlanningEventKeys"] == 1


def test_sqlite_state_store_clear_empties_shared_planning_reservation_collections(
    tmp_path,
):
    # Clear-state evidence: BE-SDBR-007, BE-SDBR-008, BE-SDBR-009, BE-RUN-011.
    store = SQLiteWorkbenchStateStore(tmp_path / "workbench.db")
    store.planning_demand_commitments["DC-1"] = {"DemandCommitmentID": "DC-1"}
    store.planning_reservation_batches["PRB-1"] = {"ReservationBatchID": "PRB-1"}
    store.ccr_capacity_reservations["CCR-RES-1"] = {
        "CapacityReservationID": "CCR-RES-1"
    }
    store.material_planning_allocations["MPA-1"] = {"MaterialAllocationID": "MPA-1"}
    store.planning_reservation_events.append({"EventID": "PRE-1"})
    store.processed_planning_event_keys.add("CONFIRM-1")

    store._clear()

    assert store.planning_demand_commitments == {}
    assert store.planning_reservation_batches == {}
    assert store.ccr_capacity_reservations == {}
    assert store.material_planning_allocations == {}
    assert store.planning_reservation_events == []
    assert store.processed_planning_event_keys == set()


class TestOrderCommitmentStatePersistence:
    # Persistence evidence: BE-SDBR-010.
    def test_order_commitment_collections_round_trip_through_sqlite(self, tmp_path):
        database_path = tmp_path / "workbench.db"
        store = SQLiteWorkbenchStateStore(database_path)
        store.order_commitment_evaluations["MTO-EVAL-1"] = {
            "EvaluationID": "MTO-EVAL-1",
            "Recommendation": "AcceptRequestedDate",
            "DecisionEvidence": {"MaterialCheck": "Available"},
        }
        store.order_commitment_events.append(
            {
                "EventID": "MTO-EVENT-1",
                "EvaluationID": "MTO-EVAL-1",
                "EventType": "Evaluated",
            }
        )

        store.save()
        restored = SQLiteWorkbenchStateStore(database_path)

        assert restored.order_commitment_evaluations == (
            store.order_commitment_evaluations
        )
        assert restored.order_commitment_events == store.order_commitment_events

    def test_order_commitment_collections_appear_in_health_and_clear(self, tmp_path):
        store = SQLiteWorkbenchStateStore(tmp_path / "workbench.db")
        store.order_commitment_evaluations["MTO-EVAL-1"] = {
            "EvaluationID": "MTO-EVAL-1"
        }
        store.order_commitment_events.append({"EventID": "MTO-EVENT-1"})

        assert store.health()["StateCounts"]["OrderCommitmentEvaluations"] == 1
        assert store.health()["StateCounts"]["OrderCommitmentEvents"] == 1

        store._clear()

        assert store.order_commitment_evaluations == {}
        assert store.order_commitment_events == []

    def test_order_commitment_collections_restore_content_and_aliases_after_atomic_rollback(
        self,
        tmp_path,
    ):
        store = SQLiteWorkbenchStateStore(tmp_path / "workbench.db")
        store.order_commitment_evaluations["MTO-EVAL-1"] = {
            "EvaluationID": "MTO-EVAL-1",
            "Recommendation": "AcceptRequestedDate",
        }
        store.order_commitment_events.append(
            {"EventID": "MTO-EVENT-1", "EvaluationID": "MTO-EVAL-1"}
        )
        store.save()
        evaluation_alias = id(store.order_commitment_evaluations)
        event_alias = id(store.order_commitment_events)
        expected_evaluations = {
            "MTO-EVAL-1": {
                "EvaluationID": "MTO-EVAL-1",
                "Recommendation": "AcceptRequestedDate",
            }
        }
        expected_events = [
            {"EventID": "MTO-EVENT-1", "EvaluationID": "MTO-EVAL-1"}
        ]

        def mutate():
            store.order_commitment_evaluations["MTO-EVAL-2"] = {
                "EvaluationID": "MTO-EVAL-2"
            }
            store.order_commitment_events.append({"EventID": "MTO-EVENT-2"})
            raise RuntimeError("Rollback MTO evidence mutation.")

        try:
            store.atomic_update(mutate)
        except RuntimeError as error:
            assert str(error) == "Rollback MTO evidence mutation."
        else:
            raise AssertionError("Atomic update did not roll back MTO evidence.")

        assert id(store.order_commitment_evaluations) == evaluation_alias
        assert id(store.order_commitment_events) == event_alias
        assert store.order_commitment_evaluations == expected_evaluations
        assert store.order_commitment_events == expected_events


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


def test_sqlite_save_exposes_committed_boundary_when_backup_maintenance_fails(
    tmp_path,
    monkeypatch,
):
    database_path = tmp_path / "backup-boundary.db"
    store = SQLiteWorkbenchStateStore(database_path)
    store.planning_runs["RUN-BACKUP-BOUNDARY"] = {
        "RunID": "RUN-BACKUP-BOUNDARY",
        "Status": "Pending",
    }

    def fail_backup() -> None:
        raise OSError("backup target unavailable")

    monkeypatch.setattr(store, "_create_backup", fail_backup)

    outcome = store.save()

    assert outcome.committed is True
    assert outcome.revision == 1
    assert outcome.backup_succeeded is False
    assert "backup target unavailable" in str(outcome.maintenance_error)
    assert store.current_revision() == 1
    assert store.health()["Status"] == "Degraded"
    assert store.health()["RecoveryStatus"] == "BackupFailed"
    restored = SQLiteWorkbenchStateStore(database_path)
    assert restored.planning_runs["RUN-BACKUP-BOUNDARY"]["Status"] == "Pending"
    assert restored.current_revision() == 1


def test_api_reports_success_and_keeps_committed_state_when_sqlite_backup_fails(
    tmp_path,
    monkeypatch,
):
    database_path = tmp_path / "backup-api-boundary.db"
    store = SQLiteWorkbenchStateStore(database_path)

    def fail_backup() -> None:
        raise OSError("backup target unavailable")

    monkeypatch.setattr(store, "_create_backup", fail_backup)
    client = TestClient(
        create_app(state_store=store),
        raise_server_exceptions=False,
    )

    response = client.post(
        "/planner/workbench/operational-state/snapshots",
        json={
            "SnapshotID": "OPS-BACKUP-FAILURE",
            "CapturedAt": "2026-06-20T06:00:00+00:00",
        },
    )

    assert response.status_code == 200
    assert response.headers["X-Workbench-Revision"] == "1"
    assert "OPS-BACKUP-FAILURE" in store.operational_state_snapshots
    restored = SQLiteWorkbenchStateStore(database_path)
    assert "OPS-BACKUP-FAILURE" in restored.operational_state_snapshots


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


def test_be_ddmrp_007_sqlite_round_trip_clear_health_and_complete_rollback(
    tmp_path,
    monkeypatch,
):
    memory_store = _FailingMemoryWorkbenchStateStore()
    _seed_ddmrp_evaluation_ledgers(memory_store)
    memory_store.save()
    memory_snapshot = memory_store.snapshot_state()

    def clear_memory_ledgers() -> None:
        for name in _DDMRP_LEDGER_VALUES:
            getattr(memory_store, name).clear()

    memory_store.fail_save = True
    with pytest.raises(OSError, match="memory save failed"):
        memory_store.atomic_update(clear_memory_ledgers)

    _assert_ddmrp_evaluation_ledgers(memory_store)
    assert memory_store.current_revision() == 1
    memory_store.restore_state(memory_snapshot)
    _assert_ddmrp_evaluation_ledgers(memory_store)

    database_path = tmp_path / "ddmrp-evaluation-ledgers.db"
    sqlite_store = SQLiteWorkbenchStateStore(database_path)
    _seed_ddmrp_evaluation_ledgers(sqlite_store)
    sqlite_store.save()

    restarted = SQLiteWorkbenchStateStore(database_path)
    _assert_ddmrp_evaluation_ledgers(restarted)
    assert restarted.current_revision() == 1
    assert restarted.health()["SchemaVersion"] == 1
    assert restarted.health()["StateCounts"] == {
        **{
            key: value
            for key, value in restarted.health()["StateCounts"].items()
            if not key.startswith("DdmrpEvaluation")
            and not key.startswith("DdmrpReplenishment")
            and key != "DdmrpActiveReplenishmentGraphs"
        },
        "DdmrpEvaluationRuns": 1,
        "DdmrpEvaluationRows": 1,
        "DdmrpReplenishmentChains": 1,
        "DdmrpReplenishmentRecommendations": 1,
        "DdmrpReplenishmentEvents": 1,
        "DdmrpActiveReplenishmentGraphs": 1,
        "DdmrpEvaluationRequestResults": 1,
    }

    sqlite_snapshot = restarted.snapshot_state()
    restarted._clear()
    for name in _DDMRP_LEDGER_VALUES:
        assert not getattr(restarted, name)
    restarted.restore_state(sqlite_snapshot)
    _assert_ddmrp_evaluation_ledgers(restarted)

    def clear_sqlite_ledgers() -> None:
        for name in _DDMRP_LEDGER_VALUES:
            getattr(restarted, name).clear()

    def fail_write(*args, **kwargs) -> None:
        raise OSError("sqlite save failed")

    monkeypatch.setattr(restarted, "_write_connection_state", fail_write)
    with pytest.raises(OSError, match="sqlite save failed"):
        restarted.atomic_update(clear_sqlite_ledgers)

    _assert_ddmrp_evaluation_ledgers(restarted)
    assert restarted.current_revision() == 1
    _assert_ddmrp_evaluation_ledgers(SQLiteWorkbenchStateStore(database_path))

    with sqlite3.connect(database_path) as connection:
        connection.executemany(
            "DELETE FROM workbench_state WHERE state_key = ?",
            ((name,) for name in _DDMRP_LEDGER_VALUES),
        )
    backward_compatible = SQLiteWorkbenchStateStore(database_path)
    for name in _DDMRP_LEDGER_VALUES:
        assert not getattr(backward_compatible, name)

    malformed_path = tmp_path / "malformed-ddmrp-request-result.db"
    malformed = SQLiteWorkbenchStateStore(malformed_path)
    malformed._initialize()
    with sqlite3.connect(malformed_path) as connection:
        connection.execute(
            """
            INSERT INTO workbench_state (state_key, payload)
            VALUES (?, ?)
            ON CONFLICT(state_key) DO UPDATE SET payload = excluded.payload
            """,
            (
                "ddmrp_evaluation_request_results",
                json.dumps(
                    {
                        "REQ-KEY": {
                            "EvaluationRequestID": "REQ-DIFFERENT",
                            "EvaluationID": "EVAL-1",
                        }
                    }
                ),
            ),
        )
    with pytest.raises(ValueError, match="EvaluationRequestID"):
        SQLiteWorkbenchStateStore(malformed_path)


def test_be_ddmrp_007_memory_complete_state_snapshot_restore():
    store = WorkbenchStateStore()
    _seed_ddmrp_evaluation_ledgers(store)
    store.revision = 4
    snapshot = store.snapshot_state()

    for name in _DDMRP_LEDGER_VALUES:
        getattr(store, name).clear()
    store.revision = 9
    store.restore_state(snapshot)

    _assert_ddmrp_evaluation_ledgers(store)
    assert store.current_revision() == 4
