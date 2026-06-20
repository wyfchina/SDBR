from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
import json
from pathlib import Path
import shutil

from sdbr.inventory_import import InventoryBufferImportRow, import_inventory_buffers_from_rows
from sdbr.master_data_validation import MaterialRequirement, validate_master_data
from sdbr.material_state import (
    MaterialAvailabilityImportRow,
    WipLimitImportRow,
    import_material_availability_from_rows,
    import_wip_limits_from_rows,
)
from sdbr.operational_state import create_operational_state_snapshot
from sdbr.order_import import OrderImportRow, import_orders_from_rows
from sdbr.planner_workbench import Resource, Routing, SchedulingOrder
from sdbr.resource_import import ResourceCapacityImportRow, import_resources_from_capacity_rows
from sdbr.routing_import import RoutingImportRow, import_routings_from_operation_rows
from sdbr.runtime_environment import resolve_runtime_environment
from sdbr.state_store import SQLiteWorkbenchStateStore, WorkbenchStateStore


BASELINE_MASTER_DATA_VERSION_ID = "TST-MDV-BASELINE-20260619"
BASELINE_OPERATIONAL_STATE_ID = "TST-OPS-BASELINE-20260619"
MATERIAL_SHORTAGE_OPERATIONAL_STATE_ID = "TST-OPS-MATERIAL-SHORTAGE-20260619"
WIP_LIMIT_OPERATIONAL_STATE_ID = "TST-OPS-WIP-LIMIT-20260619"


@dataclass(frozen=True, slots=True)
class TestDataResetSummary:
    environment_id: str
    database_path: str
    archived_database_path: str | None
    master_data_version_id: str
    operational_state_snapshot_ids: list[str]
    planning_run_ids: list[str]
    resource_count: int
    routing_count: int
    order_count: int

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class TestCaseSpec:
    case_id: str
    name_zh: str
    name_en: str
    planning_run_id: str
    master_data_version_id: str
    operational_state_snapshot_id: str
    purpose_zh: str
    expected_solver_backend_id: str
    expected_planning_run_status: str
    expected_solver_statuses: list[str]
    expected_release_ready_min: int
    expected_blocking_codes: list[str]
    expected_publication_status: str
    input_summary_zh: str
    expected_schedule_zh: str
    expected_release_zh: str
    expected_publication_zh: str
    covered_spec_ids: list[str]

    def to_dict(self) -> dict[str, object]:
        return {
            "CaseID": self.case_id,
            "NameZh": self.name_zh,
            "NameEn": self.name_en,
            "PlanningRunID": self.planning_run_id,
            "MasterDataVersionID": self.master_data_version_id,
            "OperationalStateSnapshotID": self.operational_state_snapshot_id,
            "PurposeZh": self.purpose_zh,
            "ExpectedSolverBackendID": self.expected_solver_backend_id,
            "ExpectedPlanningRunStatus": self.expected_planning_run_status,
            "ExpectedSolverStatuses": self.expected_solver_statuses,
            "ExpectedReleaseReadyMin": self.expected_release_ready_min,
            "ExpectedBlockingCodes": self.expected_blocking_codes,
            "ExpectedPublicationStatus": self.expected_publication_status,
            "InputSummaryZh": self.input_summary_zh,
            "ExpectedScheduleZh": self.expected_schedule_zh,
            "ExpectedReleaseZh": self.expected_release_zh,
            "ExpectedPublicationZh": self.expected_publication_zh,
            "CoveredSpecIDs": self.covered_spec_ids,
        }


def test_case_catalog() -> list[TestCaseSpec]:
    return [
        TestCaseSpec(
            case_id="TST-CASE-BASELINE",
            name_zh="基准排程与释放",
            name_en="Baseline schedule and release",
            planning_run_id="TST-RUN-BASELINE-001",
            master_data_version_id=BASELINE_MASTER_DATA_VERSION_ID,
            operational_state_snapshot_id=BASELINE_OPERATIONAL_STATE_ID,
            purpose_zh="验证 CP-SAT 能完成基准有限产能排程，并形成可释放候选。",
            expected_solver_backend_id="ortools",
            expected_planning_run_status="Completed",
            expected_solver_statuses=["Optimal", "Feasible"],
            expected_release_ready_min=1,
            expected_blocking_codes=[],
            expected_publication_status="Draft",
            input_summary_zh="使用基准主数据、基准库存/在途/WIP 快照和 12 张测试工单。",
            expected_schedule_zh="CP-SAT 应生成 Completed 计划，约束资源工序不重叠，12 张工单均有计划开始和完工时间。",
            expected_release_zh="至少存在一个可释放候选；可释放工单无结构化阻塞原因。",
            expected_publication_zh="排程完成后默认形成草案计划，尚未复核、批准或发布。",
            covered_spec_ids=[
                "BE-DATA-014",
                "BE-SOLVER-009",
                "BE-OUT-001",
                "BE-REL-004",
                "BE-RUN-009",
            ],
        ),
        TestCaseSpec(
            case_id="TST-CASE-MATERIAL-SHORTAGE",
            name_zh="物料短缺门控",
            name_en="Material shortage release gate",
            planning_run_id="TST-RUN-MATERIAL-SHORTAGE-001",
            master_data_version_id=BASELINE_MASTER_DATA_VERSION_ID,
            operational_state_snapshot_id=MATERIAL_SHORTAGE_OPERATIONAL_STATE_ID,
            purpose_zh="验证排程可完成，但释放门控因可用库存不足或在途未到而拦截。",
            expected_solver_backend_id="ortools",
            expected_planning_run_status="Completed",
            expected_solver_statuses=["Optimal", "Feasible"],
            expected_release_ready_min=0,
            expected_blocking_codes=["MATERIAL_SHORTAGE"],
            expected_publication_status="Draft",
            input_summary_zh="使用相同排程主数据，但运行状态快照将关键物料可用量推迟到未来到达。",
            expected_schedule_zh="有限产能排程仍应完成，物料短缺不作为当前 CP-SAT 硬约束。",
            expected_release_zh="所有候选被物料短缺或在途未到阻塞，并返回 MATERIAL_SHORTAGE。",
            expected_publication_zh="排程完成后仍是草案；释放阻塞不自动撤销排程结果。",
            covered_spec_ids=[
                "BE-DATA-014",
                "BE-SOLVER-009",
                "BE-REL-004",
                "BE-REL-005",
                "BE-UI-004",
            ],
        ),
        TestCaseSpec(
            case_id="TST-CASE-WIP-LIMIT",
            name_zh="WIP 上限门控",
            name_en="WIP limit release gate",
            planning_run_id="TST-RUN-WIP-LIMIT-001",
            master_data_version_id=BASELINE_MASTER_DATA_VERSION_ID,
            operational_state_snapshot_id=WIP_LIMIT_OPERATIONAL_STATE_ID,
            purpose_zh="验证排程可完成，但释放门控因在制品达到上限而拦截。",
            expected_solver_backend_id="ortools",
            expected_planning_run_status="Completed",
            expected_solver_statuses=["Optimal", "Feasible"],
            expected_release_ready_min=0,
            expected_blocking_codes=["WIP_LIMIT_EXCEEDED"],
            expected_publication_status="Draft",
            input_summary_zh="使用相同排程主数据，但运行状态快照将 WIP 设置到上限。",
            expected_schedule_zh="有限产能排程仍应完成，WIP 限制由释放门控判断。",
            expected_release_zh="所有候选因 WIP 达到上限被阻塞，并返回 WIP_LIMIT_EXCEEDED。",
            expected_publication_zh="排程完成后仍是草案；WIP 阻塞进入释放管理而不是改变求解器状态。",
            covered_spec_ids=[
                "BE-DATA-014",
                "BE-SOLVER-009",
                "BE-REL-004",
                "BE-REL-005",
                "BE-UI-004",
            ],
        ),
    ]


def test_case_catalog_payload() -> dict[str, object]:
    return {
        "DatasetID": "TST-DATASET-BASELINE-20260619",
        "MasterDataVersionID": BASELINE_MASTER_DATA_VERSION_ID,
        "CaseCount": len(test_case_catalog()),
        "Cases": [case.to_dict() for case in test_case_catalog()],
    }


def seed_baseline_test_data(store: WorkbenchStateStore) -> TestDataResetSummary:
    _clear_store(store)
    captured_at = datetime(2026, 6, 19, 8, tzinfo=timezone.utc)
    resources = _baseline_resources()
    routings = _baseline_routings()
    orders = _baseline_orders()
    inventory_buffers = _baseline_inventory_buffers()
    material_requirements = _baseline_material_requirements(orders)
    validation = validate_master_data(
        resources=resources,
        routings=routings,
        orders=orders,
        inventory_buffers=inventory_buffers,
        material_requirements=material_requirements,
        calendar_timezone=None,
    )
    store.master_data_versions[BASELINE_MASTER_DATA_VERSION_ID] = {
        "VersionID": BASELINE_MASTER_DATA_VERSION_ID,
        "CapturedAt": captured_at.isoformat(),
        "SourceSystem": "SDBR-TestData",
        "CreatedBy": "sdbr-test-data",
        "CalendarTimezone": None,
        "Status": "Valid" if validation.is_valid else "Invalid",
        "Resources": _resources_to_dict(resources),
        "Routings": _routings_to_dict(routings),
        "Orders": _orders_to_dict(orders),
        "InventoryBuffers": _inventory_buffers_to_dict(inventory_buffers),
        "MaterialRequirements": _material_requirements_to_dict(material_requirements),
        "Validation": _validation_to_dict(validation),
    }

    snapshots = [
        create_operational_state_snapshot(
            snapshot_id=BASELINE_OPERATIONAL_STATE_ID,
            captured_at=captured_at,
            inventory_buffers=inventory_buffers,
            material_availability=import_material_availability_from_rows(
                [
                    MaterialAvailabilityImportRow("TST-RM-STEEL", "TST-MAIN", 20, 180, None),
                    MaterialAvailabilityImportRow("TST-RM-ELEC", "TST-MAIN", 10, 80, None),
                    MaterialAvailabilityImportRow("TST-RM-PACK", "TST-MAIN", 30, 50, None),
                ]
            ),
            wip_limits=import_wip_limits_from_rows(
                [
                    WipLimitImportRow("TST-WC-DRUM", 2, 5),
                    WipLimitImportRow("TST-WC-PAINT", 1, 6),
                    WipLimitImportRow("TST-SYSTEM", 8, 18),
                ]
            ),
        ),
        create_operational_state_snapshot(
            snapshot_id=MATERIAL_SHORTAGE_OPERATIONAL_STATE_ID,
            captured_at=captured_at,
            inventory_buffers=inventory_buffers,
            material_availability=import_material_availability_from_rows(
                [
                    MaterialAvailabilityImportRow("TST-RM-STEEL", "TST-MAIN", 250, 20, datetime(2026, 6, 30, 8, tzinfo=timezone.utc)),
                    MaterialAvailabilityImportRow("TST-RM-ELEC", "TST-MAIN", 120, 10, datetime(2026, 6, 30, 8, tzinfo=timezone.utc)),
                    MaterialAvailabilityImportRow("TST-RM-PACK", "TST-MAIN", 360, 10, None),
                ]
            ),
            wip_limits=import_wip_limits_from_rows(
                [
                    WipLimitImportRow("TST-WC-DRUM", 2, 5),
                    WipLimitImportRow("TST-WC-PAINT", 1, 6),
                    WipLimitImportRow("TST-SYSTEM", 8, 18),
                ]
            ),
        ),
        create_operational_state_snapshot(
            snapshot_id=WIP_LIMIT_OPERATIONAL_STATE_ID,
            captured_at=captured_at,
            inventory_buffers=inventory_buffers,
            material_availability=import_material_availability_from_rows(
                [
                    MaterialAvailabilityImportRow("TST-RM-STEEL", "TST-MAIN", 20, 180, None),
                    MaterialAvailabilityImportRow("TST-RM-ELEC", "TST-MAIN", 10, 80, None),
                    MaterialAvailabilityImportRow("TST-RM-PACK", "TST-MAIN", 30, 50, None),
                ]
            ),
            wip_limits=import_wip_limits_from_rows(
                [
                    WipLimitImportRow("TST-WC-DRUM", 5, 5),
                    WipLimitImportRow("TST-WC-PAINT", 6, 6),
                    WipLimitImportRow("TST-SYSTEM", 18, 18),
                ]
            ),
        ),
    ]
    for snapshot in snapshots:
        store.operational_state_snapshots[snapshot.snapshot_id] = snapshot

    planning_run_ids = [
        "TST-RUN-BASELINE-001",
        "TST-RUN-MATERIAL-SHORTAGE-001",
        "TST-RUN-WIP-LIMIT-001",
    ]
    snapshot_ids = [
        BASELINE_OPERATIONAL_STATE_ID,
        MATERIAL_SHORTAGE_OPERATIONAL_STATE_ID,
        WIP_LIMIT_OPERATIONAL_STATE_ID,
    ]
    for run_id, snapshot_id in zip(planning_run_ids, snapshot_ids, strict=True):
        store.planning_runs[run_id] = _pending_run_record(
            run_id=run_id,
            snapshot_id=snapshot_id,
            requested_at=captured_at,
        )

    store.audit_events.append(
        {
            "EventID": "AUD-TST-00000001",
            "RunID": "TST-DATASET",
            "Action": "TestDataSeeded",
            "ActorID": "sdbr-test-data",
            "OccurredAt": captured_at.isoformat(),
            "Details": {
                "SpecIDs": ["BE-DATA-014", "BE-OPS-011"],
                "MasterDataVersionID": BASELINE_MASTER_DATA_VERSION_ID,
                "OperationalStateSnapshotIDs": snapshot_ids,
            },
        }
    )
    return TestDataResetSummary(
        environment_id="test",
        database_path="",
        archived_database_path=None,
        master_data_version_id=BASELINE_MASTER_DATA_VERSION_ID,
        operational_state_snapshot_ids=snapshot_ids,
        planning_run_ids=planning_run_ids,
        resource_count=len(resources),
        routing_count=len(routings),
        order_count=len(orders),
    )


def reset_test_database(
    *,
    database_path: str | Path | None = None,
    environment_id: str = "test",
    archived_at: datetime | None = None,
) -> TestDataResetSummary:
    runtime_environment = resolve_runtime_environment(
        environment_id=environment_id,
        database_path=database_path,
    )
    if runtime_environment.is_production:
        raise ValueError("Test data reset is not allowed for the production environment.")

    effective_archived_at = archived_at or datetime.now(timezone.utc)
    archived_database_path = _archive_existing_database(
        runtime_environment.database_path,
        archived_at=effective_archived_at,
    )
    store = SQLiteWorkbenchStateStore(runtime_environment.database_path)
    summary = seed_baseline_test_data(store)
    store.save()
    return TestDataResetSummary(
        environment_id=runtime_environment.environment_id,
        database_path=str(runtime_environment.database_path.resolve()),
        archived_database_path=(
            str(archived_database_path.resolve()) if archived_database_path is not None else None
        ),
        master_data_version_id=summary.master_data_version_id,
        operational_state_snapshot_ids=summary.operational_state_snapshot_ids,
        planning_run_ids=summary.planning_run_ids,
        resource_count=summary.resource_count,
        routing_count=summary.routing_count,
        order_count=summary.order_count,
    )


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Rebuild the SDBR test database.")
    parser.add_argument("--database-path", default=None)
    parser.add_argument(
        "--list-cases",
        action="store_true",
        help="Print the versioned test case catalog without rebuilding the database.",
    )
    args = parser.parse_args(argv)
    if args.list_cases:
        print(json.dumps(test_case_catalog_payload(), ensure_ascii=False, indent=2))
        return
    summary = reset_test_database(database_path=args.database_path)
    for key, value in summary.to_dict().items():
        print(f"{key}: {value}")


def _archive_existing_database(
    database_path: Path,
    *,
    archived_at: datetime,
) -> Path | None:
    if not database_path.exists():
        return None
    archive_directory = database_path.parent / "archive"
    archive_directory.mkdir(parents=True, exist_ok=True)
    timestamp = archived_at.strftime("%Y%m%dT%H%M%SZ")
    archived_database_path = archive_directory / f"{database_path.stem}-{timestamp}{database_path.suffix}"
    shutil.copy2(database_path, archived_database_path)
    database_path.unlink()
    backup_path = database_path.with_suffix(database_path.suffix + ".bak")
    if backup_path.exists():
        shutil.copy2(
            backup_path,
            archive_directory / f"{backup_path.stem}-{timestamp}{backup_path.suffix}",
        )
        backup_path.unlink()
    return archived_database_path


def _baseline_resources() -> list[Resource]:
    workdays = [
        date(2026, 6, 22),
        date(2026, 6, 23),
        date(2026, 6, 24),
        date(2026, 6, 25),
        date(2026, 6, 26),
        date(2026, 6, 29),
        date(2026, 6, 30),
        date(2026, 7, 1),
        date(2026, 7, 2),
        date(2026, 7, 3),
    ]
    resource_specs = [
        ("TST-WC-PREP", "测试-备料工作中心", False, 540),
        ("TST-WC-DRUM", "测试-约束机加工", True, 420),
        ("TST-WC-ALT-DRUM", "测试-备用机加工", False, 360),
        ("TST-WC-PAINT", "测试-表面处理", False, 480),
        ("TST-WC-ASSY", "测试-总装", False, 600),
        ("TST-WC-PACK", "测试-包装", False, 480),
    ]
    rows = [
        ResourceCapacityImportRow(resource_id, name, is_constraint, workday, capacity)
        for resource_id, name, is_constraint, capacity in resource_specs
        for workday in workdays
    ]
    return import_resources_from_capacity_rows(rows)


def _baseline_routings() -> list[Routing]:
    rows = [
        RoutingImportRow("TST-FG-A", "PRIMARY", True, "PREP", "TST-WC-PREP", 35, 10),
        RoutingImportRow("TST-FG-A", "PRIMARY", True, "DRUM", "TST-WC-DRUM", 95, 20, ["TST-WC-ALT-DRUM"]),
        RoutingImportRow("TST-FG-A", "PRIMARY", True, "ASSY", "TST-WC-ASSY", 60, 30),
        RoutingImportRow("TST-FG-A", "PRIMARY", True, "PACK", "TST-WC-PACK", 25, 40),
        RoutingImportRow("TST-FG-B", "PRIMARY", True, "PREP", "TST-WC-PREP", 25, 10),
        RoutingImportRow("TST-FG-B", "PRIMARY", True, "DRUM", "TST-WC-DRUM", 120, 20, ["TST-WC-ALT-DRUM"]),
        RoutingImportRow("TST-FG-B", "PRIMARY", True, "PAINT", "TST-WC-PAINT", 70, 30),
        RoutingImportRow("TST-FG-B", "PRIMARY", True, "PACK", "TST-WC-PACK", 30, 40),
        RoutingImportRow("TST-FG-C", "PRIMARY", True, "PREP", "TST-WC-PREP", 45, 10),
        RoutingImportRow("TST-FG-C", "PRIMARY", True, "DRUM", "TST-WC-DRUM", 80, 20, ["TST-WC-ALT-DRUM"]),
        RoutingImportRow("TST-FG-C", "PRIMARY", True, "ASSY", "TST-WC-ASSY", 90, 30),
        RoutingImportRow("TST-FG-C", "PRIMARY", True, "PACK", "TST-WC-PACK", 35, 40),
        RoutingImportRow("TST-FG-B", "ALT-PAINT-LATE", False, "PREP", "TST-WC-PREP", 25, 10),
        RoutingImportRow("TST-FG-B", "ALT-PAINT-LATE", False, "DRUM", "TST-WC-ALT-DRUM", 145, 20),
        RoutingImportRow("TST-FG-B", "ALT-PAINT-LATE", False, "PAINT", "TST-WC-PAINT", 65, 30),
        RoutingImportRow("TST-FG-B", "ALT-PAINT-LATE", False, "PACK", "TST-WC-PACK", 30, 40),
    ]
    return import_routings_from_operation_rows(rows)


def _baseline_orders() -> list[SchedulingOrder]:
    rows = [
        OrderImportRow("TST-WO-0001", "TST-FG-A", 1, datetime(2026, 6, 26, 17, tzinfo=timezone.utc), date(2026, 6, 22)),
        OrderImportRow("TST-WO-0002", "TST-FG-B", 1, datetime(2026, 6, 26, 17, tzinfo=timezone.utc), date(2026, 6, 22)),
        OrderImportRow("TST-WO-0003", "TST-FG-C", 1, datetime(2026, 6, 29, 17, tzinfo=timezone.utc), date(2026, 6, 23)),
        OrderImportRow("TST-WO-0004", "TST-FG-A", 2, datetime(2026, 6, 30, 17, tzinfo=timezone.utc), date(2026, 6, 23)),
        OrderImportRow("TST-WO-0005", "TST-FG-B", 1, datetime(2026, 7, 1, 17, tzinfo=timezone.utc), date(2026, 6, 24)),
        OrderImportRow("TST-WO-0006", "TST-FG-C", 2, datetime(2026, 7, 1, 17, tzinfo=timezone.utc), date(2026, 6, 24)),
        OrderImportRow("TST-WO-0007", "TST-FG-A", 1, datetime(2026, 7, 2, 17, tzinfo=timezone.utc), date(2026, 6, 25)),
        OrderImportRow("TST-WO-0008", "TST-FG-B", 2, datetime(2026, 7, 2, 17, tzinfo=timezone.utc), date(2026, 6, 25)),
        OrderImportRow("TST-WO-0009", "TST-FG-C", 1, datetime(2026, 7, 3, 17, tzinfo=timezone.utc), date(2026, 6, 26)),
        OrderImportRow("TST-WO-0010", "TST-FG-A", 1, datetime(2026, 7, 3, 17, tzinfo=timezone.utc), date(2026, 6, 26)),
        OrderImportRow("TST-WO-0011", "TST-FG-B", 1, datetime(2026, 7, 6, 17, tzinfo=timezone.utc), date(2026, 6, 29)),
        OrderImportRow("TST-WO-0012", "TST-FG-C", 1, datetime(2026, 7, 6, 17, tzinfo=timezone.utc), date(2026, 6, 29)),
    ]
    return import_orders_from_rows(rows)


def _baseline_inventory_buffers():
    return import_inventory_buffers_from_rows(
        [
            InventoryBufferImportRow("TST-RM-STEEL", "TST-MAIN", 260, 80, 180, 320),
            InventoryBufferImportRow("TST-RM-ELEC", "TST-MAIN", 130, 40, 90, 180),
            InventoryBufferImportRow("TST-RM-PACK", "TST-MAIN", 420, 120, 240, 500),
        ]
    )


def _baseline_material_requirements(
    orders: list[SchedulingOrder],
) -> list[MaterialRequirement]:
    requirements = []
    for order in orders:
        requirements.append(
            MaterialRequirement(
                order.order_id,
                "TST-RM-STEEL",
                "TST-MAIN",
                10 * order.quantity,
            )
        )
        if order.product_id in {"TST-FG-B", "TST-FG-C"}:
            requirements.append(
                MaterialRequirement(
                    order.order_id,
                    "TST-RM-ELEC",
                    "TST-MAIN",
                    4 * order.quantity,
                )
            )
        requirements.append(
            MaterialRequirement(
                order.order_id,
                "TST-RM-PACK",
                "TST-MAIN",
                3 * order.quantity,
            )
        )
    return requirements


def _pending_run_record(
    *,
    run_id: str,
    snapshot_id: str,
    requested_at: datetime,
) -> dict[str, object]:
    return {
        "RunID": run_id,
        "ProblemID": "TST-PROBLEM-BASELINE",
        "Status": "Pending",
        "MasterDataVersionID": BASELINE_MASTER_DATA_VERSION_ID,
        "MasterDataCapturedAt": requested_at.isoformat(),
        "OperationalStateSnapshotID": snapshot_id,
        "OperationalStateCapturedAt": requested_at.isoformat(),
        "ScheduleStartAt": datetime(2026, 6, 22, 8, tzinfo=timezone.utc).isoformat(),
        "TimeBufferMinutes": 480,
        "SolverBackendID": "ortools",
        "TimeLimitSeconds": 300,
        "MaxAttempts": 3,
        "RetryDelaySeconds": 60,
        "SolverStatus": "Pending",
        "SolverMessage": "Test planning run is awaiting execution.",
        "RequestedBy": "sdbr-test-data",
        "RequestedAt": requested_at.isoformat(),
        "StartedAt": None,
        "CompletedAt": None,
        "ExecutedBy": None,
        "Schedule": None,
        "StatusHistory": [
            {
                "Status": "Pending",
                "ChangedAt": requested_at.isoformat(),
                "ChangedBy": "sdbr-test-data",
            }
        ],
    }


def _clear_store(store: WorkbenchStateStore) -> None:
    store.execution_events.clear()
    store.replan_requests.clear()
    store.replan_schedule_snapshots.clear()
    store.release_authorizations.clear()
    store.operational_state_snapshots.clear()
    store.release_decision_packages.clear()
    store.dbr_release_policies.clear()
    store.calendar_overrides.clear()
    store.scheduling_strategy_versions.clear()
    store.integration_messages.clear()
    store.test_case_acceptance_decisions.clear()
    store.master_data_versions.clear()
    store.planning_runs.clear()
    store.audit_events.clear()


def _resources_to_dict(resources: list[Resource]) -> list[dict[str, object]]:
    return [
        {
            "ResourceID": resource.resource_id,
            "Name": resource.name,
            "IsConstraint": resource.is_constraint,
            "DailyCapacityMinutes": {
                capacity_date.isoformat(): minutes
                for capacity_date, minutes in resource.daily_capacity_minutes.items()
            },
        }
        for resource in resources
    ]


def _routings_to_dict(routings: list[Routing]) -> list[dict[str, object]]:
    return [
        {
            "ProductID": routing.product_id,
            "RoutingID": routing.routing_id,
            "IsPrimary": routing.is_primary,
            "Operations": [
                {
                    "OperationID": operation.operation_id,
                    "ResourceID": operation.resource_id,
                    "DurationMinutes": operation.duration_minutes,
                    "Sequence": operation.sequence,
                    "AlternateResourceIDs": operation.alternate_resource_ids or [],
                }
                for operation in routing.operations
            ],
        }
        for routing in routings
    ]


def _orders_to_dict(orders: list[SchedulingOrder]) -> list[dict[str, object]]:
    return [
        {
            "OrderID": order.order_id,
            "ProductID": order.product_id,
            "Quantity": order.quantity,
            "DueDate": order.due_date.isoformat(),
            "TargetStartDate": order.target_start_date.isoformat(),
        }
        for order in orders
    ]


def _inventory_buffers_to_dict(inventory_buffers) -> list[dict[str, object]]:
    return [
        {
            "ItemID": buffer.item_id,
            "LocationID": buffer.location_id,
            "OnHandQty": buffer.on_hand_qty,
            "RedZoneQty": buffer.red_zone_qty,
            "YellowZoneQty": buffer.yellow_zone_qty,
            "GreenZoneQty": buffer.green_zone_qty,
        }
        for buffer in inventory_buffers
    ]


def _material_requirements_to_dict(
    material_requirements: list[MaterialRequirement],
) -> list[dict[str, object]]:
    return [
        {
            "OrderID": requirement.order_id,
            "ItemID": requirement.item_id,
            "LocationID": requirement.location_id,
            "RequiredQty": requirement.required_qty,
        }
        for requirement in material_requirements
    ]


def _validation_to_dict(validation) -> dict[str, object]:
    return {
        "IsValid": validation.is_valid,
        "Summary": validation.summary,
        "Issues": [
            {
                "Severity": issue.severity,
                "Code": issue.code,
                "Message": issue.message,
                "Field": issue.field,
            }
            for issue in validation.issues
        ],
    }


if __name__ == "__main__":
    main()
