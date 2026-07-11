from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass, field, fields
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import sqlite3
from threading import Lock, RLock
from typing import Callable, TypeVar

from sdbr.operational_state import (
    OperationalStateSnapshot,
    create_operational_state_snapshot,
)
from sdbr.planner_view import InventoryBufferPolicy
from sdbr.release_authorization import ReleaseAuthorization
from sdbr.release_candidates import MaterialAvailability, WipLimit
from sdbr.replanning import ReplanRequest


class StateStoreRevisionConflict(RuntimeError):
    def __init__(self, *, expected_revision: int, current_revision: int) -> None:
        super().__init__("Workbench state was changed by another writer.")
        self.expected_revision = expected_revision
        self.current_revision = current_revision


class StateStoreManagedRequestRejected(RuntimeError):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self._current_revision: int | None = None

    @property
    def current_revision(self) -> int:
        if self._current_revision is None:
            raise RuntimeError(
                "Controlled rejection left the state store without a revision."
            )
        return self._current_revision

    def capture_current_revision(self, current_revision: int) -> None:
        if self._current_revision is not None:
            raise RuntimeError("Controlled rejection revision was already captured.")
        self._current_revision = current_revision


@dataclass(frozen=True, slots=True)
class StateStoreSaveOutcome:
    committed: bool
    revision: int
    backup_succeeded: bool | None
    maintenance_error: str | None = None


MutationResult = TypeVar("MutationResult")


@dataclass(slots=True)
class WorkbenchStateStore:
    execution_events: list[dict[str, object]] = field(default_factory=list)
    replan_requests: list[ReplanRequest] = field(default_factory=list)
    replan_schedule_snapshots: dict[str, dict[str, object]] = field(
        default_factory=dict
    )
    release_authorizations: list[ReleaseAuthorization] = field(default_factory=list)
    operational_state_snapshots: dict[str, OperationalStateSnapshot] = field(
        default_factory=dict
    )
    release_decision_packages: dict[str, dict[str, object]] = field(
        default_factory=dict
    )
    dbr_release_policies: dict[str, dict[str, object]] = field(default_factory=dict)
    base_calendars: dict[str, dict[str, object]] = field(default_factory=dict)
    resource_calendar_assignments: dict[str, dict[str, object]] = field(default_factory=dict)
    calendar_overrides: dict[str, dict[str, object]] = field(default_factory=dict)
    scheduling_strategy_versions: dict[str, dict[str, object]] = field(default_factory=dict)
    ddsop_config_inbound_messages: list[dict[str, object]] = field(default_factory=list)
    operating_model_configurations: dict[str, dict[str, object]] = field(default_factory=dict)
    ddsop_feedback_outbound_messages: list[dict[str, object]] = field(default_factory=list)
    ddsop_runtime_planning_input_messages: list[dict[str, object]] = field(default_factory=list)
    ddsop_runtime_planning_input_packages: dict[str, dict[str, object]] = field(default_factory=dict)
    ddsop_runtime_feedback_correlations: list[dict[str, object]] = field(default_factory=list)
    supplier_identity_source_inbound_messages: list[dict[str, object]] = field(default_factory=list)
    production_inventory_quality_inbound_messages: list[dict[str, object]] = field(default_factory=list)
    execution_object_evidence_inbound_messages: list[dict[str, object]] = field(default_factory=list)
    integration_messages: list[dict[str, object]] = field(default_factory=list)
    test_case_acceptance_decisions: list[dict[str, object]] = field(default_factory=list)
    simio_validation_runs: dict[str, dict[str, object]] = field(default_factory=dict)
    simio_template_registry: dict[str, dict[str, object]] = field(default_factory=dict)
    active_simio_template_id: str | None = None
    ddmrp_decoupling_points: list[dict[str, object]] = field(default_factory=list)
    ddmrp_demand_signals: list[dict[str, object]] = field(default_factory=list)
    ddmrp_open_supply: list[dict[str, object]] = field(default_factory=list)
    master_data_versions: dict[str, dict[str, object]] = field(default_factory=dict)
    planning_runs: dict[str, dict[str, object]] = field(default_factory=dict)
    planning_demand_commitments: dict[str, dict[str, object]] = field(
        default_factory=dict
    )
    planning_reservation_batches: dict[str, dict[str, object]] = field(
        default_factory=dict
    )
    ccr_capacity_reservations: dict[str, dict[str, object]] = field(
        default_factory=dict
    )
    material_planning_allocations: dict[str, dict[str, object]] = field(
        default_factory=dict
    )
    planning_reservation_events: list[dict[str, object]] = field(default_factory=list)
    processed_planning_event_keys: set[str] = field(default_factory=set)
    audit_events: list[dict[str, object]] = field(default_factory=list)
    revision: int = 0
    _request_write_lock: Lock = field(
        default_factory=Lock,
        init=False,
        repr=False,
        compare=False,
    )

    def save(self) -> StateStoreSaveOutcome:
        self.revision += 1
        return StateStoreSaveOutcome(
            committed=True,
            revision=self.revision,
            backup_succeeded=None,
        )

    def health(self) -> dict[str, object]:
        return {
            "Backend": "Memory",
            "Status": "Healthy",
            "SchemaVersion": None,
            "Revision": self.current_revision(),
            "RecoveryStatus": "NotApplicable",
            "LastSavedAt": None,
            "StateCounts": _state_counts(self),
        }

    def reload(self) -> None:
        return None

    def current_revision(self) -> int:
        return self.revision

    @property
    def request_write_lock(self) -> Lock:
        return self._request_write_lock

    @property
    def state_lock(self) -> Lock:
        return self._request_write_lock

    def snapshot_state(self) -> dict[str, object]:
        return _snapshot_complete_state(self)

    def restore_state(self, snapshot: dict[str, object]) -> None:
        _restore_complete_state(self, snapshot)

    def atomic_update(
        self,
        mutation: Callable[[], MutationResult],
        *,
        expected_revision: int | None = None,
    ) -> tuple[MutationResult, StateStoreSaveOutcome]:
        with self._request_write_lock:
            current_revision = self.current_revision()
            if (
                expected_revision is not None
                and expected_revision != current_revision
            ):
                raise StateStoreRevisionConflict(
                    expected_revision=expected_revision,
                    current_revision=current_revision,
                )
            snapshot = self.snapshot_state()
            try:
                result = mutation()
                outcome = self.save()
            except Exception as error:
                if isinstance(error, StateStoreManagedRequestRejected):
                    error.capture_current_revision(current_revision)
                self.restore_state(snapshot)
                raise
            return result, outcome


class SQLiteWorkbenchStateStore(WorkbenchStateStore):
    SCHEMA_VERSION = 1

    def __init__(self, database_path: str | Path) -> None:
        super().__init__()
        self.database_path = Path(database_path)
        self.backup_path = self.database_path.with_suffix(
            self.database_path.suffix + ".bak"
        )
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = RLock()
        self._last_saved_at: str | None = None
        self._last_backup_error: str | None = None
        self._recovery_status = "Normal"
        self._revision = 0
        try:
            self._initialize()
            self._load()
        except sqlite3.DatabaseError:
            if not self.backup_path.exists():
                raise
            shutil.copy2(self.backup_path, self.database_path)
            self._clear()
            self._initialize()
            self._load()
            self._recovery_status = "RecoveredFromBackup"

    def save(self) -> StateStoreSaveOutcome:
        saved_at = datetime.now(timezone.utc).isoformat()
        with self._lock:
            connection = sqlite3.connect(self.database_path)
            try:
                connection.execute("BEGIN IMMEDIATE")
                current_revision = self._database_revision(connection)
                if current_revision != self._revision:
                    raise StateStoreRevisionConflict(
                        expected_revision=self._revision,
                        current_revision=current_revision,
                    )
                next_revision = current_revision + 1
                self._write_connection_state(
                    connection,
                    saved_at=saved_at,
                    next_revision=next_revision,
                )
                connection.commit()
            except Exception:
                connection.rollback()
                raise
            finally:
                connection.close()
        return self._committed_outcome(
            saved_at=saved_at,
            next_revision=next_revision,
        )

    def atomic_update(
        self,
        mutation: Callable[[], MutationResult],
        *,
        expected_revision: int | None = None,
    ) -> tuple[MutationResult, StateStoreSaveOutcome]:
        with self._request_write_lock:
            pre_transaction_snapshot = self.snapshot_state()
            authoritative_snapshot: dict[str, object] | None = None
            saved_at = datetime.now(timezone.utc).isoformat()
            with self._lock:
                connection = sqlite3.connect(self.database_path)
                try:
                    connection.execute("BEGIN IMMEDIATE")
                    payloads, metadata = self._read_connection_state(connection)
                    self._replace_loaded_state(payloads, metadata)
                    authoritative_snapshot = self.snapshot_state()
                    current_revision = self._revision
                    if (
                        expected_revision is not None
                        and expected_revision != current_revision
                    ):
                        raise StateStoreRevisionConflict(
                            expected_revision=expected_revision,
                            current_revision=current_revision,
                        )
                    result = mutation()
                    next_revision = current_revision + 1
                    self._write_connection_state(
                        connection,
                        saved_at=saved_at,
                        next_revision=next_revision,
                    )
                    connection.commit()
                except Exception as error:
                    if isinstance(error, StateStoreManagedRequestRejected):
                        error.capture_current_revision(current_revision)
                    connection.rollback()
                    self.restore_state(
                        authoritative_snapshot or pre_transaction_snapshot
                    )
                    raise
                finally:
                    connection.close()
            outcome = self._committed_outcome(
                saved_at=saved_at,
                next_revision=next_revision,
            )
            return result, outcome

    def health(self) -> dict[str, object]:
        with self._lock, sqlite3.connect(self.database_path) as connection:
            quick_check = connection.execute("PRAGMA quick_check").fetchone()
        database_healthy = quick_check is not None and quick_check[0] == "ok"
        if not database_healthy:
            status = "Unhealthy"
        elif self._last_backup_error is not None:
            status = "Degraded"
        else:
            status = "Healthy"
        return {
            "Backend": "SQLite",
            "Status": status,
            "SchemaVersion": self.SCHEMA_VERSION,
            "Revision": self._revision,
            "RecoveryStatus": self._recovery_status,
            "DatabasePath": str(self.database_path.resolve()),
            "BackupPath": str(self.backup_path.resolve()),
            "LastSavedAt": self._last_saved_at,
            "LastBackupError": self._last_backup_error,
            "StateCounts": _state_counts(self),
        }

    def current_revision(self) -> int:
        return self._revision

    def _database_revision(self, connection: sqlite3.Connection) -> int:
        row = connection.execute(
            """
            SELECT metadata_value FROM workbench_metadata
            WHERE metadata_key = 'state_revision'
            """
        ).fetchone()
        return int(row[0]) if row is not None else 0

    def _state_payloads(self) -> dict[str, object]:
        return {
            "execution_events": self.execution_events,
            "replan_requests": [asdict(item) for item in self.replan_requests],
            "replan_schedule_snapshots": self.replan_schedule_snapshots,
            "release_authorizations": [
                asdict(item) for item in self.release_authorizations
            ],
            "operational_state_snapshots": [
                asdict(item) for item in self.operational_state_snapshots.values()
            ],
            "release_decision_packages": self.release_decision_packages,
            "dbr_release_policies": self.dbr_release_policies,
            "base_calendars": self.base_calendars,
            "resource_calendar_assignments": self.resource_calendar_assignments,
            "calendar_overrides": self.calendar_overrides,
            "scheduling_strategy_versions": self.scheduling_strategy_versions,
            "ddsop_config_inbound_messages": self.ddsop_config_inbound_messages,
            "operating_model_configurations": self.operating_model_configurations,
            "ddsop_feedback_outbound_messages": self.ddsop_feedback_outbound_messages,
            "ddsop_runtime_planning_input_messages": self.ddsop_runtime_planning_input_messages,
            "ddsop_runtime_planning_input_packages": self.ddsop_runtime_planning_input_packages,
            "ddsop_runtime_feedback_correlations": self.ddsop_runtime_feedback_correlations,
            "supplier_identity_source_inbound_messages": self.supplier_identity_source_inbound_messages,
            "production_inventory_quality_inbound_messages": self.production_inventory_quality_inbound_messages,
            "execution_object_evidence_inbound_messages": self.execution_object_evidence_inbound_messages,
            "integration_messages": self.integration_messages,
            "test_case_acceptance_decisions": self.test_case_acceptance_decisions,
            "simio_validation_runs": self.simio_validation_runs,
            "simio_template_registry": self.simio_template_registry,
            "active_simio_template_id": self.active_simio_template_id,
            "ddmrp_decoupling_points": self.ddmrp_decoupling_points,
            "ddmrp_demand_signals": self.ddmrp_demand_signals,
            "ddmrp_open_supply": self.ddmrp_open_supply,
            "master_data_versions": self.master_data_versions,
            "planning_runs": self.planning_runs,
            "planning_demand_commitments": self.planning_demand_commitments,
            "planning_reservation_batches": self.planning_reservation_batches,
            "ccr_capacity_reservations": self.ccr_capacity_reservations,
            "material_planning_allocations": self.material_planning_allocations,
            "planning_reservation_events": self.planning_reservation_events,
            "processed_planning_event_keys": sorted(
                self.processed_planning_event_keys
            ),
            "audit_events": self.audit_events,
        }

    def _write_connection_state(
        self,
        connection: sqlite3.Connection,
        *,
        saved_at: str,
        next_revision: int,
    ) -> None:
        connection.executemany(
            """
            INSERT INTO workbench_state (state_key, payload)
            VALUES (?, ?)
            ON CONFLICT(state_key) DO UPDATE SET payload = excluded.payload
            """,
            [
                (
                    state_key,
                    json.dumps(
                        _jsonable(payload),
                        ensure_ascii=True,
                        sort_keys=True,
                        separators=(",", ":"),
                    ),
                )
                for state_key, payload in self._state_payloads().items()
            ],
        )
        connection.executemany(
            """
            INSERT INTO workbench_metadata (metadata_key, metadata_value)
            VALUES (?, ?)
            ON CONFLICT(metadata_key) DO UPDATE
            SET metadata_value = excluded.metadata_value
            """,
            (
                ("last_saved_at", saved_at),
                ("state_revision", str(next_revision)),
            ),
        )

    def _read_connection_state(
        self,
        connection: sqlite3.Connection,
    ) -> tuple[dict[str, object], dict[str, str]]:
        rows = dict(connection.execute("SELECT state_key, payload FROM workbench_state"))
        metadata = dict(
            connection.execute(
                "SELECT metadata_key, metadata_value FROM workbench_metadata"
            )
        )
        return (
            {state_key: json.loads(payload) for state_key, payload in rows.items()},
            metadata,
        )

    def _replace_loaded_state(
        self,
        payloads: dict[str, object],
        metadata: dict[str, str],
    ) -> None:
        schema_version = int(metadata.get("schema_version", "0"))
        if schema_version != self.SCHEMA_VERSION:
            raise ValueError(
                f"Unsupported workbench schema version: {schema_version}."
            )
        self._clear()
        self._last_saved_at = metadata.get("last_saved_at")
        self._revision = int(metadata.get("state_revision", "0"))
        self._apply_payloads(payloads)

    def _committed_outcome(
        self,
        *,
        saved_at: str,
        next_revision: int,
    ) -> StateStoreSaveOutcome:
        self._last_saved_at = saved_at
        self._revision = next_revision
        try:
            self._create_backup()
        except Exception as error:
            self._last_backup_error = f"{type(error).__name__}: {error}"
            self._recovery_status = "BackupFailed"
            return StateStoreSaveOutcome(
                committed=True,
                revision=next_revision,
                backup_succeeded=False,
                maintenance_error=self._last_backup_error,
            )
        self._last_backup_error = None
        if self._recovery_status == "BackupFailed":
            self._recovery_status = "Normal"
        return StateStoreSaveOutcome(
            committed=True,
            revision=next_revision,
            backup_succeeded=True,
        )

    def _initialize(self) -> None:
        with sqlite3.connect(self.database_path) as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS workbench_state (
                    state_key TEXT PRIMARY KEY,
                    payload TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS workbench_metadata (
                    metadata_key TEXT PRIMARY KEY,
                    metadata_value TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                INSERT INTO workbench_metadata (metadata_key, metadata_value)
                VALUES ('schema_version', ?)
                ON CONFLICT(metadata_key) DO NOTHING
                """,
                (str(self.SCHEMA_VERSION),),
            )
            connection.execute(
                """
                INSERT INTO workbench_metadata (metadata_key, metadata_value)
                VALUES ('state_revision', '0')
                ON CONFLICT(metadata_key) DO NOTHING
                """
            )

    def _load(self) -> None:
        with self._lock, sqlite3.connect(self.database_path) as connection:
            payloads, metadata = self._read_connection_state(connection)
        self._replace_loaded_state(payloads, metadata)

    def _apply_payloads(self, payloads: dict[str, object]) -> None:
        if not payloads:
            return
        self.execution_events.extend(payloads.get("execution_events", []))
        self.replan_requests.extend(
            _replan_request_from_dict(item)
            for item in payloads.get("replan_requests", [])
        )
        self.replan_schedule_snapshots.update(
            payloads.get("replan_schedule_snapshots", {})
        )
        self.release_authorizations.extend(
            _release_authorization_from_dict(item)
            for item in payloads.get("release_authorizations", [])
        )
        self.operational_state_snapshots.update(
            (
                snapshot.snapshot_id,
                snapshot,
            )
            for snapshot in (
                _operational_state_snapshot_from_dict(item)
                for item in payloads.get("operational_state_snapshots", [])
            )
        )
        self.release_decision_packages.update(
            payloads.get("release_decision_packages", {})
        )
        self.dbr_release_policies.update(payloads.get("dbr_release_policies", {}))
        self.base_calendars.update(payloads.get("base_calendars", {}))
        self.resource_calendar_assignments.update(
            payloads.get("resource_calendar_assignments", {})
        )
        self.calendar_overrides.update(payloads.get("calendar_overrides", {}))
        self.scheduling_strategy_versions.update(
            payloads.get("scheduling_strategy_versions", {})
        )
        self.ddsop_config_inbound_messages.extend(
            payloads.get("ddsop_config_inbound_messages", [])
        )
        self.operating_model_configurations.update(
            payloads.get("operating_model_configurations", {})
        )
        self.ddsop_feedback_outbound_messages.extend(
            payloads.get("ddsop_feedback_outbound_messages", [])
        )
        self.ddsop_runtime_planning_input_messages.extend(
            payloads.get("ddsop_runtime_planning_input_messages", [])
        )
        self.ddsop_runtime_planning_input_packages.update(
            payloads.get("ddsop_runtime_planning_input_packages", {})
        )
        self.ddsop_runtime_feedback_correlations.extend(
            payloads.get("ddsop_runtime_feedback_correlations", [])
        )
        self.supplier_identity_source_inbound_messages.extend(
            payloads.get("supplier_identity_source_inbound_messages", [])
        )
        self.production_inventory_quality_inbound_messages.extend(
            payloads.get("production_inventory_quality_inbound_messages", [])
        )
        self.execution_object_evidence_inbound_messages.extend(
            payloads.get("execution_object_evidence_inbound_messages", [])
        )
        self.integration_messages.extend(payloads.get("integration_messages", []))
        self.test_case_acceptance_decisions.extend(
            payloads.get("test_case_acceptance_decisions", [])
        )
        self.simio_validation_runs.update(payloads.get("simio_validation_runs", {}))
        self.simio_template_registry.update(
            payloads.get("simio_template_registry", {})
        )
        self.active_simio_template_id = payloads.get("active_simio_template_id")
        self.ddmrp_decoupling_points.extend(
            payloads.get("ddmrp_decoupling_points", [])
        )
        self.ddmrp_demand_signals.extend(payloads.get("ddmrp_demand_signals", []))
        self.ddmrp_open_supply.extend(payloads.get("ddmrp_open_supply", []))
        self.master_data_versions.update(payloads.get("master_data_versions", {}))
        self.planning_runs.update(payloads.get("planning_runs", {}))
        self.planning_demand_commitments.update(
            payloads.get("planning_demand_commitments", {})
        )
        self.planning_reservation_batches.update(
            payloads.get("planning_reservation_batches", {})
        )
        self.ccr_capacity_reservations.update(
            payloads.get("ccr_capacity_reservations", {})
        )
        self.material_planning_allocations.update(
            payloads.get("material_planning_allocations", {})
        )
        self.planning_reservation_events.extend(
            payloads.get("planning_reservation_events", [])
        )
        self.processed_planning_event_keys.update(
            payloads.get("processed_planning_event_keys", [])
        )
        self.audit_events.extend(payloads.get("audit_events", []))

    def _create_backup(self) -> None:
        with self._lock, sqlite3.connect(self.database_path) as source:
            with sqlite3.connect(self.backup_path) as destination:
                source.backup(destination)

    def reload(self) -> None:
        with self._lock:
            self._load()

    def _clear(self) -> None:
        self.execution_events.clear()
        self.replan_requests.clear()
        self.replan_schedule_snapshots.clear()
        self.release_authorizations.clear()
        self.operational_state_snapshots.clear()
        self.release_decision_packages.clear()
        self.dbr_release_policies.clear()
        self.base_calendars.clear()
        self.resource_calendar_assignments.clear()
        self.calendar_overrides.clear()
        self.scheduling_strategy_versions.clear()
        self.ddsop_config_inbound_messages.clear()
        self.operating_model_configurations.clear()
        self.ddsop_feedback_outbound_messages.clear()
        self.ddsop_runtime_planning_input_messages.clear()
        self.ddsop_runtime_planning_input_packages.clear()
        self.ddsop_runtime_feedback_correlations.clear()
        self.supplier_identity_source_inbound_messages.clear()
        self.production_inventory_quality_inbound_messages.clear()
        self.execution_object_evidence_inbound_messages.clear()
        self.integration_messages.clear()
        self.test_case_acceptance_decisions.clear()
        self.simio_validation_runs.clear()
        self.simio_template_registry.clear()
        self.active_simio_template_id = None
        self.ddmrp_decoupling_points.clear()
        self.ddmrp_demand_signals.clear()
        self.ddmrp_open_supply.clear()
        self.master_data_versions.clear()
        self.planning_runs.clear()
        self.planning_demand_commitments.clear()
        self.planning_reservation_batches.clear()
        self.ccr_capacity_reservations.clear()
        self.material_planning_allocations.clear()
        self.planning_reservation_events.clear()
        self.processed_planning_event_keys.clear()
        self.audit_events.clear()


_SQLITE_SNAPSHOT_METADATA_FIELDS = (
    "_revision",
    "_last_saved_at",
    "_last_backup_error",
    "_recovery_status",
)


def _snapshot_complete_state(store: WorkbenchStateStore) -> dict[str, object]:
    state = {
        item.name: deepcopy(getattr(store, item.name))
        for item in fields(WorkbenchStateStore)
        if not item.name.startswith("_")
    }
    metadata = {
        name: deepcopy(getattr(store, name))
        for name in _SQLITE_SNAPSHOT_METADATA_FIELDS
        if hasattr(store, name)
    }
    return {"State": state, "Metadata": metadata}


def _restore_complete_state(
    store: WorkbenchStateStore,
    snapshot: dict[str, object],
) -> None:
    state = snapshot.get("State")
    metadata = snapshot.get("Metadata")
    if not isinstance(state, dict) or not isinstance(metadata, dict):
        raise TypeError("Workbench state snapshot is invalid.")
    for name, saved in state.items():
        current = getattr(store, name)
        if isinstance(current, dict) and isinstance(saved, dict):
            current.clear()
            current.update(deepcopy(saved))
        elif isinstance(current, list) and isinstance(saved, list):
            current.clear()
            current.extend(deepcopy(saved))
        elif isinstance(current, set) and isinstance(saved, set):
            current.clear()
            current.update(deepcopy(saved))
        else:
            setattr(store, name, deepcopy(saved))
    for name, saved in metadata.items():
        setattr(store, name, deepcopy(saved))


def _jsonable(value: object) -> object:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return value


def _state_counts(store: WorkbenchStateStore) -> dict[str, int]:
    return {
        "ExecutionEvents": len(store.execution_events),
        "ReplanRequests": len(store.replan_requests),
        "ReplanScheduleSnapshots": len(store.replan_schedule_snapshots),
        "ReleaseAuthorizations": len(store.release_authorizations),
        "OperationalStateSnapshots": len(store.operational_state_snapshots),
        "ReleaseDecisionPackages": len(store.release_decision_packages),
        "DbrReleasePolicies": len(store.dbr_release_policies),
        "BaseCalendars": len(store.base_calendars),
        "ResourceCalendarAssignments": len(store.resource_calendar_assignments),
        "CalendarOverrides": len(store.calendar_overrides),
        "SchedulingStrategyVersions": len(store.scheduling_strategy_versions),
        "DdsopConfigInboundMessages": len(store.ddsop_config_inbound_messages),
        "OperatingModelConfigurations": len(store.operating_model_configurations),
        "DdsopFeedbackOutboundMessages": len(store.ddsop_feedback_outbound_messages),
        "DdsopRuntimePlanningInputMessages": len(
            store.ddsop_runtime_planning_input_messages
        ),
        "DdsopRuntimePlanningInputPackages": len(
            store.ddsop_runtime_planning_input_packages
        ),
        "DdsopRuntimeFeedbackCorrelations": len(
            store.ddsop_runtime_feedback_correlations
        ),
        "SupplierIdentitySourceInboundMessages": len(
            store.supplier_identity_source_inbound_messages
        ),
        "ProductionInventoryQualityInboundMessages": len(
            store.production_inventory_quality_inbound_messages
        ),
        "ExecutionObjectEvidenceInboundMessages": len(
            store.execution_object_evidence_inbound_messages
        ),
        "IntegrationMessages": len(store.integration_messages),
        "TestCaseAcceptanceDecisions": len(store.test_case_acceptance_decisions),
        "SimioValidationRuns": len(store.simio_validation_runs),
        "SimioTemplateRegistry": len(store.simio_template_registry),
        "DdmrpDecouplingPoints": len(store.ddmrp_decoupling_points),
        "DdmrpDemandSignals": len(store.ddmrp_demand_signals),
        "DdmrpOpenSupply": len(store.ddmrp_open_supply),
        "MasterDataVersions": len(store.master_data_versions),
        "PlanningRuns": len(store.planning_runs),
        "PlanningDemandCommitments": len(store.planning_demand_commitments),
        "PlanningReservationBatches": len(store.planning_reservation_batches),
        "CcrCapacityReservations": len(store.ccr_capacity_reservations),
        "MaterialPlanningAllocations": len(store.material_planning_allocations),
        "PlanningReservationEvents": len(store.planning_reservation_events),
        "ProcessedPlanningEventKeys": len(store.processed_planning_event_keys),
        "AuditEvents": len(store.audit_events),
    }


def _replan_request_from_dict(value: dict[str, object]) -> ReplanRequest:
    data = dict(value)
    for key in (
        "planned_release_at",
        "detected_at",
        "decided_at",
        "execution_started_at",
        "execution_completed_at",
    ):
        if data.get(key) is not None:
            data[key] = datetime.fromisoformat(str(data[key]))
    return ReplanRequest(**data)


def _release_authorization_from_dict(
    value: dict[str, object],
) -> ReleaseAuthorization:
    data = dict(value)
    data["released_at"] = datetime.fromisoformat(str(data["released_at"]))
    return ReleaseAuthorization(**data)


def _operational_state_snapshot_from_dict(
    value: dict[str, object],
) -> OperationalStateSnapshot:
    material_availability = []
    for item in value.get("material_availability", []):
        data = dict(item)
        if data.get("inbound_available_at") is not None:
            data["inbound_available_at"] = datetime.fromisoformat(
                str(data["inbound_available_at"])
            )
        material_availability.append(MaterialAvailability(**data))
    return create_operational_state_snapshot(
        snapshot_id=str(value["snapshot_id"]),
        captured_at=datetime.fromisoformat(str(value["captured_at"])),
        inventory_buffers=[
            InventoryBufferPolicy(**item)
            for item in value.get("inventory_buffers", [])
        ],
        material_availability=material_availability,
        wip_limits=[WipLimit(**item) for item in value.get("wip_limits", [])],
    )
