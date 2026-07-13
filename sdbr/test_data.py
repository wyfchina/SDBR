from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from datetime import date, datetime, time, timedelta, timezone
import json
from pathlib import Path
import shutil

from sdbr.inventory_import import InventoryBufferImportRow, import_inventory_buffers_from_rows
from sdbr.ddmrp_replenishment import (
    apply_staged_ddmrp_evaluation,
    build_read_only_authority_signature,
    build_relevant_planning_ledger_identity,
    prepare_ddmrp_evaluation,
    stage_ddmrp_evaluation,
)
from sdbr.ddsop_contracts import canonical_operating_model_fingerprint
from sdbr.master_data_validation import MaterialRequirement, validate_master_data
from sdbr.material_state import (
    MaterialAvailabilityImportRow,
    WipLimitImportRow,
    import_material_availability_from_rows,
    import_wip_limits_from_rows,
)
from sdbr.operational_state import create_operational_state_snapshot
from sdbr.order_import import OrderImportRow, import_orders_from_rows
from sdbr.plan_publication import schedule_fingerprint
from sdbr.planner_view import InventoryBufferPolicy
from sdbr.planner_workbench import Operation, Resource, Routing, SchedulingOrder, Shift, WorkCalendar
from sdbr.resource_import import ResourceCapacityImportRow, import_resources_from_capacity_rows
from sdbr.routing_import import RoutingImportRow, import_routings_from_operation_rows
from sdbr.runtime_environment import resolve_runtime_environment
from sdbr.state_store import SQLiteWorkbenchStateStore, WorkbenchStateStore


BASELINE_MASTER_DATA_VERSION_ID = "TST-MDV-BASELINE-20260619"
BASELINE_OPERATIONAL_STATE_ID = "TST-OPS-BASELINE-20260619"
MATERIAL_SHORTAGE_OPERATIONAL_STATE_ID = "TST-OPS-MATERIAL-SHORTAGE-20260619"
WIP_LIMIT_OPERATIONAL_STATE_ID = "TST-OPS-WIP-LIMIT-20260619"
DDMRP_NET_FLOW_MASTER_DATA_VERSION_ID = "TST-DDMRP-MDV-NET-FLOW-20260625"
P1_MARKET_CONTROL_MASTER_DATA_VERSION_ID = "TST-P1-MDV-MARKET-CONTROL-20260709"
P1_MARKET_CONTROL_RUN_ID = "TST-P1-RUN-MARKET-CONTROL-20260709"
MTO_COMMITMENT_MASTER_DATA_VERSION_ID = "TST-MTO-MDV-COMMITMENT"
MTO_COMMITMENT_OPERATIONAL_STATE_ID = "TST-MTO-OPS-CURRENT"
MTO_COMMITMENT_BASELINE_RUN_ID = "TST-MTO-RUN-BASELINE"
DDMRP_READ_ONLY_REPLENISHMENT_CASE_ID = "TST-DDMRP-REPLENISHMENT-READONLY-20260711"
DDMRP_READ_ONLY_REPLENISHMENT_EVALUATED_AT = datetime(
    2026, 7, 11, 1, tzinfo=timezone.utc
)
DDMRP_READ_ONLY_REPLENISHMENT_ROWS = (
    ("TST-DDMRP-RO-ABOVE-GREEN-1", "AboveGreen", 150.0, 0.0),
    ("TST-DDMRP-RO-ABOVE-GREEN-2", "AboveGreen", 165.0, 0.0),
    ("TST-DDMRP-RO-ABOVE-GREEN-3", "AboveGreen", 180.0, 0.0),
    ("TST-DDMRP-RO-GREEN-1", "Green", 75.0, 0.0),
    ("TST-DDMRP-RO-GREEN-2", "Green", 82.0, 0.0),
    ("TST-DDMRP-RO-GREEN-3", "Green", 95.0, 0.0),
    ("TST-DDMRP-RO-RED-1", "Red", 10.0, 90.0),
    ("TST-DDMRP-RO-RED-2", "Red", 14.0, 86.0),
    ("TST-DDMRP-RO-RED-3", "Red", 18.0, 82.0),
    ("TST-DDMRP-RO-YELLOW-1", "Yellow", 35.0, 65.0),
    ("TST-DDMRP-RO-YELLOW-2", "Yellow", 42.0, 58.0),
    ("TST-DDMRP-RO-YELLOW-3", "Yellow", 49.0, 51.0),
)
DDMRP_READ_ONLY_REPLENISHMENT_ITEM_IDS = tuple(
    row[0] for row in DDMRP_READ_ONLY_REPLENISHMENT_ROWS
)


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
    case_group: str
    case_type: str
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
    expected_schedule_assertions: list[str]
    expected_diagnostic_codes: list[str]
    input_summary_zh: str
    expected_schedule_zh: str
    expected_release_zh: str
    expected_publication_zh: str
    covered_spec_ids: list[str]

    def to_dict(self) -> dict[str, object]:
        return {
            "CaseID": self.case_id,
            "CaseGroup": self.case_group,
            "CaseType": self.case_type,
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
            "ExpectedScheduleAssertions": self.expected_schedule_assertions,
            "ExpectedDiagnosticCodes": self.expected_diagnostic_codes,
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
            case_group="BusinessClosure",
            case_type="EndToEnd",
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
            expected_schedule_assertions=[],
            expected_diagnostic_codes=["ORTOOLS_CP_SAT_MODEL"],
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
            case_group="BusinessClosure",
            case_type="ReleaseGate",
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
            expected_schedule_assertions=[],
            expected_diagnostic_codes=["ORTOOLS_CP_SAT_MODEL"],
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
            case_group="BusinessClosure",
            case_type="ReleaseGate",
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
            expected_schedule_assertions=[],
            expected_diagnostic_codes=["ORTOOLS_CP_SAT_MODEL"],
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
        TestCaseSpec(
            case_id="TST-P1-MARKET-CONTROL",
            case_group="SDBRMarketControlCases",
            case_type="MarketControl",
            name_zh="S-DBR 市场承诺与约束保护",
            name_en="S-DBR market promise and constraint protection",
            planning_run_id=P1_MARKET_CONTROL_RUN_ID,
            master_data_version_id=P1_MARKET_CONTROL_MASTER_DATA_VERSION_ID,
            operational_state_snapshot_id=BASELINE_OPERATIONAL_STATE_ID,
            purpose_zh="验证同一排程结果能同时显示 MTO 约束负荷、MTA 补货负荷、安全承诺信号和统一缓冲优先级。",
            expected_solver_backend_id="ortools",
            expected_planning_run_status="Completed",
            expected_solver_statuses=["Optimal", "Feasible"],
            expected_release_ready_min=0,
            expected_blocking_codes=[],
            expected_publication_status="Draft",
            expected_schedule_assertions=["ALL_ORDERS_SCHEDULED"],
            expected_diagnostic_codes=["ORTOOLS_CP_SAT_MODEL"],
            input_summary_zh="使用 3 张 P1 测试工单，其中 2 张为 MTO，1 张为 MTA 补货；MTA 补货建议已映射到可执行工单。",
            expected_schedule_zh="CP-SAT 应完成有限能力排程，约束资源上同时形成 MTO 和 MTA 计划负荷。",
            expected_release_zh="本案例聚焦 S-DBR 运行控制信号，释放候选数量不作为验收重点。",
            expected_publication_zh="排程完成后形成草案计划。",
            covered_spec_ids=[
                "BE-SDBR-001",
                "BE-SDBR-002",
                "BE-SDBR-003",
                "BE-SDBR-004",
                "BE-UI-003",
            ],
        ),
        TestCaseSpec(
            case_id="TST-CP-FINITE-RESOURCE",
            case_group="CPSATBusinessCases",
            case_type="FiniteCapacity",
            name_zh="CP-SAT 约束资源有限产能",
            name_en="CP-SAT finite constraint capacity",
            planning_run_id="TST-CP-RUN-FINITE-001",
            master_data_version_id="TST-CP-MDV-FINITE-20260621",
            operational_state_snapshot_id=BASELINE_OPERATIONAL_STATE_ID,
            purpose_zh="验证同一约束资源上的工序不会重叠，业务含义是瓶颈设备一次只能加工一张工单。",
            expected_solver_backend_id="ortools",
            expected_planning_run_status="Completed",
            expected_solver_statuses=["Optimal", "Feasible"],
            expected_release_ready_min=0,
            expected_blocking_codes=[],
            expected_publication_status="Draft",
            expected_schedule_assertions=["FINITE_RESOURCE_NO_OVERLAP", "ALL_ORDERS_SCHEDULED"],
            expected_diagnostic_codes=["ORTOOLS_CP_SAT_MODEL"],
            input_summary_zh="两张工单共用同一台约束资源，每张加工 120 分钟，无备用资源。",
            expected_schedule_zh="两张工单应前后排产，不允许在同一时段占用同一约束资源。",
            expected_release_zh="本案例聚焦排程，不要求释放候选数量。",
            expected_publication_zh="排程完成后形成草案计划。",
            covered_spec_ids=["BE-DATA-014", "BE-SOLVER-009"],
        ),
        TestCaseSpec(
            case_id="TST-CP-ALTERNATE-RESOURCE",
            case_group="CPSATBusinessCases",
            case_type="AlternateResource",
            name_zh="CP-SAT 备用资源选择",
            name_en="CP-SAT alternate resource choice",
            planning_run_id="TST-CP-RUN-ALTERNATE-001",
            master_data_version_id="TST-CP-MDV-ALTERNATE-20260621",
            operational_state_snapshot_id=BASELINE_OPERATIONAL_STATE_ID,
            purpose_zh="验证主资源拥堵时，CP-SAT 可以把工序分配到备用资源以缩短整体完工。",
            expected_solver_backend_id="ortools",
            expected_planning_run_status="Completed",
            expected_solver_statuses=["Optimal", "Feasible"],
            expected_release_ready_min=0,
            expected_blocking_codes=[],
            expected_publication_status="Draft",
            expected_schedule_assertions=["ALTERNATE_RESOURCE_USED"],
            expected_diagnostic_codes=["ORTOOLS_CP_SAT_MODEL"],
            input_summary_zh="两张工单的主资源相同，其中一张允许使用备用资源。",
            expected_schedule_zh="至少一项工序应使用备用资源；若主资源等待代价更高，备用资源是合理选择。",
            expected_release_zh="本案例聚焦排程，不要求释放候选数量。",
            expected_publication_zh="排程完成后形成草案计划。",
            covered_spec_ids=["BE-DATA-014", "BE-SOLVER-009"],
        ),
        TestCaseSpec(
            case_id="TST-CP-CALENDAR-OVERTIME",
            case_group="CPSATBusinessCases",
            case_type="CalendarOverride",
            name_zh="CP-SAT 日历维护与加班",
            name_en="CP-SAT calendar maintenance and overtime",
            planning_run_id="TST-CP-RUN-CALENDAR-001",
            master_data_version_id="TST-CP-MDV-CALENDAR-20260621",
            operational_state_snapshot_id=BASELINE_OPERATIONAL_STATE_ID,
            purpose_zh="验证 Active 临时日历覆盖会被冻结到 Planning Run，并真正改变 CP-SAT 可用产能窗口。",
            expected_solver_backend_id="ortools",
            expected_planning_run_status="Completed",
            expected_solver_statuses=["Optimal", "Feasible"],
            expected_release_ready_min=0,
            expected_blocking_codes=[],
            expected_publication_status="Draft",
            expected_schedule_assertions=["CALENDAR_OVERRIDE_APPLIED", "MAINTENANCE_WINDOW_AVOIDED", "OVERTIME_WINDOW_USED"],
            expected_diagnostic_codes=["CALENDAR_OVERRIDES_APPLIED", "ORTOOLS_CP_SAT_MODEL"],
            input_summary_zh="同一资源白天维护不可用，晚上有加班窗口；工序只能排进可用窗口。",
            expected_schedule_zh="工序不能落入维护窗口，且应使用加班窗口完成排产。",
            expected_release_zh="本案例聚焦排程，不要求释放候选数量。",
            expected_publication_zh="排程完成后形成草案计划。",
            covered_spec_ids=["BE-DATA-014", "BE-DATA-010", "BE-SOLVER-011"],
        ),
        TestCaseSpec(
            case_id="TST-CP-RESOURCE-EFFICIENCY",
            case_group="CPSATBusinessCases",
            case_type="ResourceEfficiency",
            name_zh="CP-SAT 资源效率修正",
            name_en="CP-SAT resource efficiency adjustment",
            planning_run_id="TST-CP-RUN-EFFICIENCY-001",
            master_data_version_id="TST-CP-MDV-EFFICIENCY-20260621",
            operational_state_snapshot_id=BASELINE_OPERATIONAL_STATE_ID,
            purpose_zh="验证资源效率会改变实际排程时长，业务含义是低效率设备需要占用更长时间。",
            expected_solver_backend_id="ortools",
            expected_planning_run_status="Completed",
            expected_solver_statuses=["Optimal", "Feasible"],
            expected_release_ready_min=0,
            expected_blocking_codes=[],
            expected_publication_status="Draft",
            expected_schedule_assertions=["EFFICIENCY_DURATION_APPLIED"],
            expected_diagnostic_codes=["ORTOOLS_RESOURCE_EFFICIENCY_ENABLED", "ORTOOLS_CP_SAT_MODEL"],
            input_summary_zh="同一 60 分钟标准工序分配到效率 50% 的资源。",
            expected_schedule_zh="计划占用时长应变为 120 分钟，而不是仍按标准 60 分钟。",
            expected_release_zh="本案例聚焦排程，不要求释放候选数量。",
            expected_publication_zh="排程完成后形成草案计划。",
            covered_spec_ids=["BE-DATA-014", "BE-SOLVER-011"],
        ),
        TestCaseSpec(
            case_id="TST-CP-SETUP-SEQUENCE",
            case_group="CPSATBusinessCases",
            case_type="SetupTransition",
            name_zh="CP-SAT 顺序相关换型",
            name_en="CP-SAT sequence dependent setup",
            planning_run_id="TST-CP-RUN-SETUP-001",
            master_data_version_id="TST-CP-MDV-SETUP-20260621",
            operational_state_snapshot_id=BASELINE_OPERATIONAL_STATE_ID,
            purpose_zh="验证不同产品族在同一有限资源上切换时，需要加入换型间隔。",
            expected_solver_backend_id="ortools",
            expected_planning_run_status="Completed",
            expected_solver_statuses=["Optimal", "Feasible"],
            expected_release_ready_min=0,
            expected_blocking_codes=[],
            expected_publication_status="Draft",
            expected_schedule_assertions=["SETUP_LAG_APPLIED"],
            expected_diagnostic_codes=["ORTOOLS_SETUP_TRANSITIONS_ENABLED", "ORTOOLS_CP_SAT_MODEL"],
            input_summary_zh="两张不同产品族工单共用同一有限资源，并配置 A 到 B 的 45 分钟换型。",
            expected_schedule_zh="两张不同产品族工单之间必须至少保留 45 分钟换型间隔，不依赖具体先后顺序。",
            expected_release_zh="本案例聚焦排程，不要求释放候选数量。",
            expected_publication_zh="排程完成后形成草案计划。",
            covered_spec_ids=["BE-DATA-014", "BE-SOLVER-010"],
        ),
        TestCaseSpec(
            case_id="TST-CP-INFEASIBLE-WINDOW",
            case_group="CPSATBusinessCases",
            case_type="InfeasibleDiagnostic",
            name_zh="CP-SAT 时间窗不可行诊断",
            name_en="CP-SAT infeasible time window diagnostic",
            planning_run_id="TST-CP-RUN-INFEASIBLE-001",
            master_data_version_id="TST-CP-MDV-INFEASIBLE-20260621",
            operational_state_snapshot_id=BASELINE_OPERATIONAL_STATE_ID,
            purpose_zh="验证时间窗过窄时系统返回结构化不可行诊断，而不是输出看似可执行的错误计划。",
            expected_solver_backend_id="ortools",
            expected_planning_run_status="DeadLetter",
            expected_solver_statuses=["Infeasible"],
            expected_release_ready_min=0,
            expected_blocking_codes=[],
            expected_publication_status="Unavailable",
            expected_schedule_assertions=["INFEASIBLE_DIAGNOSTIC_REPORTED"],
            expected_diagnostic_codes=["ORTOOLS_INFEASIBLE"],
            input_summary_zh="一项 120 分钟工序被限制在 60 分钟时间窗内完成。",
            expected_schedule_zh="Planning Run 应失败，SolverStatus 为 Infeasible，并返回 ORTOOLS_INFEASIBLE。",
            expected_release_zh="不可行计划不进入释放候选。",
            expected_publication_zh="不可行计划无发布资格，发布视图显示不可用且无允许动作。",
            covered_spec_ids=["BE-DATA-014", "BE-SOLVER-009", "BE-SOLVER-011"],
        ),
    ]


def test_case_catalog_payload() -> dict[str, object]:
    return {
        "DatasetID": "TST-DATASET-BASELINE-20260619",
        "MasterDataVersionID": BASELINE_MASTER_DATA_VERSION_ID,
        "CaseCount": len(test_case_catalog()),
        "DdmrpRuntimeCases": [
            {
                "CaseID": "TST-DDMRP-NET-FLOW",
                "CaseGroup": "DDMRPRuntimeCases",
                "NameZh": "DDMRP 净流与库存缓冲",
                "MasterDataVersionID": DDMRP_NET_FLOW_MASTER_DATA_VERSION_ID,
                "PurposeZh": "展示同一时间点下红区、黄区、绿区和高于绿区四类解耦点的净流位置、在手执行状态和补货建议。",
                "ExpectedSummary": {
                    "RedCount": 3,
                    "YellowCount": 3,
                    "GreenCount": 3,
                    "AboveGreenCount": 3,
                    "ReplenishmentSuggestionCount": 6,
                },
                "CoveredSpecIDs": [
                    "BE-DDMRP-001",
                    "BE-DDMRP-002",
                    "BE-DDMRP-003",
                    "BE-DDMRP-004",
                    "BE-DDMRP-005",
                    "BE-DDMRP-006",
                    "UI-DDMRP-001",
                ],
            },
            {
                "CaseID": DDMRP_READ_ONLY_REPLENISHMENT_CASE_ID,
                "CaseGroup": "DDMRPRuntimeCases",
                "NameZh": "DDMRP 只读补货受控夹具",
                "MasterDataVersionID": None,
                "PurposeZh": "验证受控测试夹具可重复展示受门控的只读补货评估，且不授权任何操作写入。",
                "TestFixtureOnly": True,
                "ExpectedSummary": {
                    "RedCount": 3,
                    "YellowCount": 3,
                    "GreenCount": 3,
                    "AboveGreenCount": 3,
                    "BlockedRecommendationCount": 6,
                    "PendingReviewCount": 0,
                    "AdjustmentRequiredCount": 0,
                    "ActiveGraphCount": 0,
                },
                "CoveredSpecIDs": ["BE-DDMRP-007", "UI-DDMRP-003"],
            },
        ],
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
                    WipLimitImportRow("TST_WC_DRUM", 2, 5),
                    WipLimitImportRow("TST_WC_PAINT", 1, 6),
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
                    WipLimitImportRow("TST_WC_DRUM", 2, 5),
                    WipLimitImportRow("TST_WC_PAINT", 1, 6),
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
                    WipLimitImportRow("TST_WC_DRUM", 5, 5),
                    WipLimitImportRow("TST_WC_PAINT", 6, 6),
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
    _seed_cp_sat_business_cases(store=store, captured_at=captured_at)
    _seed_p1_market_control_case(
        store=store,
        captured_at=captured_at + timedelta(days=5),
    )
    _seed_ddmrp_net_flow_case(store=store, captured_at=captured_at + timedelta(days=6))
    _seed_ddmrp_read_only_replenishment_case(store=store)

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


def seed_mto_order_commitment_fixture(
    store: WorkbenchStateStore,
    *,
    captured_at: datetime,
) -> dict[str, object]:
    if captured_at.tzinfo is None or captured_at.utcoffset() is None:
        raise ValueError("MTO fixture time must be timezone-aware.")
    captured_at = captured_at.astimezone(timezone.utc)
    due_date = captured_at.date() + timedelta(days=2)
    next_date = captured_at.date() + timedelta(days=3)
    due_start = datetime.combine(
        due_date, time(8, 0), tzinfo=timezone.utc
    )
    due_end = datetime.combine(
        due_date, time(16, 0), tzinfo=timezone.utc
    )
    next_start = datetime.combine(
        next_date, time(8, 0), tzinfo=timezone.utc
    )
    next_end = datetime.combine(
        next_date, time(16, 0), tzinfo=timezone.utc
    )

    store.order_commitment_evaluations.clear()
    store.order_commitment_events.clear()
    store.planning_demand_commitments.clear()
    store.planning_reservation_batches.clear()
    store.ccr_capacity_reservations.clear()
    store.material_planning_allocations.clear()
    store.planning_reservation_events.clear()
    store.processed_planning_event_keys.clear()

    day_calendar = WorkCalendar(
        calendar_id="TST-MTO-CAL-DAY",
        working_weekdays=set(range(7)),
        shifts=[Shift("Day", time(8, 0), time(16, 0))],
        maintenance_windows=[],
        holidays=set(),
    )
    resources = [
        Resource(
            "TST-MTO-CCR-1",
            "MTO Constraint",
            True,
            {due_date: 480, next_date: 480},
            calendar=day_calendar,
            capacity_units=1,
            efficiency_percent=100,
        ),
        Resource(
            "TST-MTO-NCR-1",
            "MTO Pack",
            False,
            {due_date: 480, next_date: 480},
            calendar=day_calendar,
        ),
    ]
    routing = Routing(
        product_id="TST-MTO-FG-1",
        routing_id="PRIMARY",
        is_primary=True,
        operations=[
            Operation("CCR-CUT", "TST-MTO-CCR-1", 60, 10),
            Operation("PACK", "TST-MTO-NCR-1", 30, 20),
        ],
    )
    inventory_buffers = [
        InventoryBufferPolicy(
            "TST-MTO-RM-1", "TST-MAIN", 100.0, 20.0, 40.0, 80.0
        )
    ]
    validation = validate_master_data(
        resources=resources,
        routings=[routing],
        orders=[],
        inventory_buffers=inventory_buffers,
        material_requirements=[],
        calendar_timezone="UTC",
    )
    if not validation.is_valid:
        raise ValueError("MTO fixture master data must validate.")
    store.master_data_versions[MTO_COMMITMENT_MASTER_DATA_VERSION_ID] = {
        "VersionID": MTO_COMMITMENT_MASTER_DATA_VERSION_ID,
        "CapturedAt": captured_at.isoformat(),
        "SourceSystem": "SDBR-TestData",
        "CreatedBy": "sdbr-test-data",
        "CalendarTimezone": "UTC",
        "Status": "Valid",
        "Resources": _resources_to_dict(resources),
        "Routings": _routings_to_dict([routing]),
        "Orders": [],
        "InventoryBuffers": _inventory_buffers_to_dict(
            inventory_buffers
        ),
        "MaterialRequirements": [],
        "Validation": _validation_to_dict(validation),
    }

    snapshot = create_operational_state_snapshot(
        snapshot_id=MTO_COMMITMENT_OPERATIONAL_STATE_ID,
        captured_at=captured_at - timedelta(minutes=5),
        inventory_buffers=inventory_buffers,
        material_availability=import_material_availability_from_rows([
            MaterialAvailabilityImportRow(
                "TST-MTO-RM-1", "TST-MAIN", 0.0, 0.0, None
            )
        ]),
        wip_limits=[],
    )
    store.operational_state_snapshots[snapshot.snapshot_id] = snapshot

    schedule = {
        "GeneratedAt": captured_at.isoformat(),
        "GanttRows": [
            {
                "ResourceID": "TST-MTO-CCR-1",
                "Bars": [
                    {
                        "OrderID": "TST-MTO-BASELOAD",
                        "OperationID": "TST-MTO-BASELOAD:CCR-CUT",
                        "BarType": "Processing",
                        "Start": due_start.isoformat(),
                        "End": (
                            due_start + timedelta(minutes=180)
                        ).isoformat(),
                        "DurationMinutes": 180,
                    }
                ],
            }
        ],
        "Orders": [],
        "Diagnostics": [],
    }
    frozen_release_policy = {
        "VersionID": "TST-MTO-RELEASE-POLICY-1",
        "RopeBufferMinutes": 60,
        "MaterialCheckWindowMinutes": 1440,
    }
    run = {
        "RunID": MTO_COMMITMENT_BASELINE_RUN_ID,
        "ProblemID": "TST-MTO-PROBLEM-BASELINE",
        "Status": "Completed",
        "PublicationStatus": "Published",
        "MasterDataVersionID": MTO_COMMITMENT_MASTER_DATA_VERSION_ID,
        "OperationalStateSnapshotID": snapshot.snapshot_id,
        "OperatingModelConfigurationID": None,
        "OperatingModelFingerprint": None,
        "SchedulingConfigurationID": None,
        "DDMRPConfigurationID": None,
        "ReleasePolicyVersionID": frozen_release_policy["VersionID"],
        "FrozenReleasePolicy": frozen_release_policy,
        "FrozenBaseCalendars": [],
        "FrozenResourceCalendarAssignments": [],
        "FrozenCalendarOverrides": [],
        "SetupTransitions": [],
        "TimeBufferMinutes": 60,
        "RequestedBy": "sdbr-test-data",
        "RequestedAt": captured_at.isoformat(),
        "StartedAt": captured_at.isoformat(),
        "CompletedAt": captured_at.isoformat(),
        "Schedule": schedule,
        "PublicationHistory": [],
    }
    run["ScheduleFingerprint"] = schedule_fingerprint(run)
    store.planning_runs[MTO_COMMITMENT_BASELINE_RUN_ID] = run

    return {
        "MasterDataVersionID": MTO_COMMITMENT_MASTER_DATA_VERSION_ID,
        "OperationalStateSnapshotID": snapshot.snapshot_id,
        "BaselinePlanningRunID": MTO_COMMITMENT_BASELINE_RUN_ID,
        "CapacityWindowKeys": [
            (
                "TST-MTO-CCR-1",
                due_start.isoformat(),
                due_end.isoformat(),
            ),
            (
                "TST-MTO-CCR-1",
                next_start.isoformat(),
                next_end.isoformat(),
            ),
        ],
        "IntakePayloadTemplate": {
            "SourceSystem": "MockERP",
            "SourceObjectType": "CustomerOrder",
            "OrderID": "TST-MTO-SO-ORDINARY",
            "OrderVersion": "1",
            "DemandLineID": "10",
            "ProductID": "TST-MTO-FG-1",
            "LocationID": "TST-MAIN",
            "Quantity": 1.0,
            "Uom": "EA",
            "RequestedDueAt": datetime.combine(
                due_date, time(18, 0), tzinfo=timezone.utc
            ).isoformat(),
            "BusinessPriority": 100,
            "ReceivedAt": captured_at.isoformat(),
            "TraceID": "TRACE-TST-MTO-ORDINARY",
            "BaselinePlanningRunID": MTO_COMMITMENT_BASELINE_RUN_ID,
            "RoutingID": "PRIMARY",
            "OperationalStateSnapshotID": snapshot.snapshot_id,
            "MaterialRequirements": [
                {
                    "RequirementLineID": (
                        "TST-MTO-SO-ORDINARY:10:TST-MTO-RM-1"
                    ),
                    "ItemID": "TST-MTO-RM-1",
                    "LocationID": "TST-MAIN",
                    "RequiredQty": 5.0,
                    "Uom": "EA",
                }
            ],
        },
    }


def reset_test_case_state(
    store: WorkbenchStateStore,
    *,
    case_id: str,
    reset_at: datetime | None = None,
) -> dict[str, object]:
    case = next((item for item in test_case_catalog() if item.case_id == case_id), None)
    if case is None:
        raise KeyError(case_id)
    effective_reset_at = reset_at or datetime(2026, 6, 19, 8, tzinfo=timezone.utc)
    if case.case_id == "TST-P1-MARKET-CONTROL":
        _seed_p1_market_control_case(store=store, captured_at=effective_reset_at)
    elif case.case_id.startswith("TST-CP-"):
        _reset_cp_sat_case(store=store, case=case, captured_at=effective_reset_at)
    else:
        _reset_business_closure_case(store=store, case=case, captured_at=effective_reset_at)
    _remove_case_runtime_state(store=store, case=case)
    store.audit_events.append(
        {
            "EventID": f"AUD-{case.case_id}-RESET-{effective_reset_at.strftime('%Y%m%d%H%M%S')}",
            "RunID": case.planning_run_id,
            "Action": "TestCaseReset",
            "ActorID": "sdbr-test-data",
            "OccurredAt": effective_reset_at.isoformat(),
            "Details": {
                "CaseID": case.case_id,
                "PlanningRunID": case.planning_run_id,
                "SpecIDs": ["BE-DATA-014"],
            },
        }
    )
    return {
        "CaseID": case.case_id,
        "PlanningRunID": case.planning_run_id,
        "Status": "Reset",
        "ResetAt": effective_reset_at.isoformat(),
    }


def _reset_business_closure_case(
    *,
    store: WorkbenchStateStore,
    case: TestCaseSpec,
    captured_at: datetime,
) -> None:
    if BASELINE_MASTER_DATA_VERSION_ID not in store.master_data_versions:
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
    store.planning_runs[case.planning_run_id] = _pending_run_record(
        run_id=case.planning_run_id,
        snapshot_id=case.operational_state_snapshot_id,
        requested_at=captured_at,
        master_data_version_id=case.master_data_version_id,
    )


def _reset_cp_sat_case(
    *,
    store: WorkbenchStateStore,
    case: TestCaseSpec,
    captured_at: datetime,
) -> None:
    builder_by_case_id = {
        "TST-CP-FINITE-RESOURCE": _cp_finite_case,
        "TST-CP-ALTERNATE-RESOURCE": _cp_alternate_case,
        "TST-CP-CALENDAR-OVERTIME": _cp_calendar_case,
        "TST-CP-RESOURCE-EFFICIENCY": _cp_efficiency_case,
        "TST-CP-SETUP-SEQUENCE": _cp_setup_case,
        "TST-CP-INFEASIBLE-WINDOW": _cp_infeasible_case,
    }
    builder = builder_by_case_id.get(case.case_id)
    if builder is None:
        raise KeyError(case.case_id)
    version_id, run_id, resources, routings, orders, run_options = builder(captured_at)
    inventory_buffers = _baseline_inventory_buffers()
    validation = validate_master_data(
        resources=resources,
        routings=routings,
        orders=orders,
        inventory_buffers=inventory_buffers,
        material_requirements=[],
        calendar_timezone=None,
    )
    store.master_data_versions[version_id] = {
        "VersionID": version_id,
        "CapturedAt": captured_at.isoformat(),
        "SourceSystem": "SDBR-CP-SAT-TestData",
        "CreatedBy": "sdbr-test-data",
        "CalendarTimezone": run_options.get("CalendarTimezone"),
        "Status": "Valid" if validation.is_valid else "Invalid",
        "Resources": _resources_to_dict(resources),
        "Routings": _routings_to_dict(routings),
        "Orders": _orders_to_dict(orders),
        "InventoryBuffers": _inventory_buffers_to_dict(inventory_buffers),
        "MaterialRequirements": [],
        "Validation": _validation_to_dict(validation),
    }
    store.planning_runs[run_id] = _pending_run_record(
        run_id=run_id,
        snapshot_id=case.operational_state_snapshot_id,
        requested_at=captured_at,
        master_data_version_id=version_id,
        problem_id=str(run_options.get("ProblemID", run_id.replace("RUN", "PROBLEM"))),
        time_buffer_minutes=int(run_options.get("TimeBufferMinutes", 0)),
        objective_strategy_id=str(run_options.get("ObjectiveStrategyID", "balanced")),
        setup_transitions=list(run_options.get("SetupTransitions", [])),
        frozen_calendar_overrides=list(run_options.get("FrozenCalendarOverrides", [])),
    )
    for override in run_options.get("FrozenCalendarOverrides", []):
        store.calendar_overrides[str(override["OverrideID"])] = dict(override)


def _seed_p1_market_control_case(
    *,
    store: WorkbenchStateStore,
    captured_at: datetime,
) -> None:
    resources = _baseline_resources()
    routings = _p1_market_control_routings()
    orders = _baseline_orders()[:3]
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
    order_rows = _orders_to_dict(orders)
    for row in order_rows:
        row["DemandClass"] = "MTA" if row["OrderID"] == "TST-WO-0003" else "MTO"
        if row["DemandClass"] == "MTA":
            row["OrderType"] = "StockReplenishment"
    store.master_data_versions[P1_MARKET_CONTROL_MASTER_DATA_VERSION_ID] = {
        "VersionID": P1_MARKET_CONTROL_MASTER_DATA_VERSION_ID,
        "CapturedAt": captured_at.isoformat(),
        "SourceSystem": "SDBR-P1-TestData",
        "CreatedBy": "sdbr-test-data",
        "CalendarTimezone": None,
        "Status": "Valid" if validation.is_valid else "Invalid",
        "Resources": _resources_to_dict(resources),
        "Routings": _routings_to_dict(routings),
        "Orders": order_rows,
        "InventoryBuffers": _inventory_buffers_to_dict(inventory_buffers),
        "MaterialRequirements": _material_requirements_to_dict(material_requirements),
        "DdmrpRuntimeLines": [
            {
                "ItemID": "TST-FG-C",
                "LocationID": "TST-MAIN",
                "PlanningStatus": "Red",
                "SuggestedReplenishmentQty": 1,
                "NetFlowPosition": 40,
                "TopOfGreen": 100,
                "RecommendedAction": "Replenish",
                "BusinessMeaning": "P1 测试补货建议已映射到 TST-WO-0003。",
            }
        ],
        "Validation": _validation_to_dict(validation),
    }
    store.planning_runs[P1_MARKET_CONTROL_RUN_ID] = _pending_run_record(
        run_id=P1_MARKET_CONTROL_RUN_ID,
        snapshot_id=BASELINE_OPERATIONAL_STATE_ID,
        requested_at=captured_at,
        master_data_version_id=P1_MARKET_CONTROL_MASTER_DATA_VERSION_ID,
        problem_id="TST-P1-PROBLEM-MARKET-CONTROL",
        time_buffer_minutes=480,
    )
    store.audit_events.append(
        {
            "EventID": "AUD-TST-P1-MARKET-CONTROL-SEED",
            "RunID": P1_MARKET_CONTROL_RUN_ID,
            "Action": "P1MarketControlCaseSeeded",
            "ActorID": "sdbr-test-data",
            "OccurredAt": captured_at.isoformat(),
            "Details": {
                "SpecIDs": [
                    "BE-SDBR-001",
                    "BE-SDBR-002",
                    "BE-SDBR-003",
                    "BE-SDBR-004",
                ],
                "MasterDataVersionID": P1_MARKET_CONTROL_MASTER_DATA_VERSION_ID,
                "DemandClasses": ["MTO", "MTA"],
            },
        }
    )


def _p1_market_control_routings() -> list[Routing]:
    routings = []
    for routing in _baseline_routings():
        if not routing.is_primary:
            continue
        routings.append(
            Routing(
                product_id=routing.product_id,
                routing_id=routing.routing_id,
                is_primary=routing.is_primary,
                operations=[
                    Operation(
                        operation_id=operation.operation_id,
                        resource_id=operation.resource_id,
                        duration_minutes=operation.duration_minutes,
                        sequence=operation.sequence,
                        alternate_resource_ids=[],
                        setup_family=operation.setup_family,
                        earliest_start_at=operation.earliest_start_at,
                        latest_end_at=operation.latest_end_at,
                    )
                    for operation in routing.operations
                ],
            )
        )
    return routings


def _seed_ddmrp_net_flow_case(
    *,
    store: WorkbenchStateStore,
    captured_at: datetime,
) -> None:
    resources = _baseline_resources()
    routings = _baseline_routings()
    orders = _baseline_orders()
    ddmrp_case_rows = (
        ("TST-DDMRP-RED", "Red", 40, "BP-HIGH-VARIABILITY", 40),
        ("TST-DDMRP-RED-2", "Red", 20, "BP-HIGH-VARIABILITY", 40),
        ("TST-DDMRP-RED-3", "Red", 30, "BP-HIGH-VARIABILITY", 40),
        ("TST-DDMRP-YELLOW", "Yellow", 80, "BP-MEDIUM-VARIABILITY", 30),
        ("TST-DDMRP-YELLOW-2", "Yellow", 70, "BP-MEDIUM-VARIABILITY", 30),
        ("TST-DDMRP-YELLOW-3", "Yellow", 90, "BP-MEDIUM-VARIABILITY", 30),
        ("TST-DDMRP-GREEN", "Green", 140, "BP-LOW-VARIABILITY", 20),
        ("TST-DDMRP-GREEN-2", "Green", 130, "BP-LOW-VARIABILITY", 20),
        ("TST-DDMRP-GREEN-3", "Green", 150, "BP-LOW-VARIABILITY", 20),
        ("TST-DDMRP-ABOVE", "AboveGreen", 230, "BP-STABLE", 20),
        ("TST-DDMRP-ABOVE-2", "AboveGreen", 220, "BP-STABLE", 20),
        ("TST-DDMRP-ABOVE-3", "AboveGreen", 260, "BP-STABLE", 20),
    )
    inventory_buffers = import_inventory_buffers_from_rows(
        [
            InventoryBufferImportRow(item_id, "TST-MAIN", on_hand, 50, 50, 100)
            for item_id, _, on_hand, _, _ in ddmrp_case_rows
        ]
    )
    validation = validate_master_data(
        resources=resources,
        routings=routings,
        orders=orders,
        inventory_buffers=inventory_buffers,
        material_requirements=[],
        calendar_timezone=None,
    )
    store.master_data_versions[DDMRP_NET_FLOW_MASTER_DATA_VERSION_ID] = {
        "VersionID": DDMRP_NET_FLOW_MASTER_DATA_VERSION_ID,
        "CapturedAt": captured_at.isoformat(),
        "SourceSystem": "SDBR-DDMRP-TestData",
        "CreatedBy": "sdbr-test-data",
        "CalendarTimezone": None,
        "Status": "Valid" if validation.is_valid else "Invalid",
        "Resources": _resources_to_dict(resources),
        "Routings": _routings_to_dict(routings),
        "Orders": _orders_to_dict(orders),
        "InventoryBuffers": _inventory_buffers_to_dict(inventory_buffers),
        "MaterialRequirements": [],
        "DdmrpDecouplingPoints": [
            {
                "ItemID": item_id,
                "LocationID": "TST-MAIN",
                "BufferProfileID": buffer_profile_id,
                "DLTMinutes": 1440,
                "OrderMultipleQty": 10,
                "MinimumOrderQty": minimum_order_qty,
                "Status": "Active",
                "PlanningStatus": planning_status,
            }
            for (
                item_id,
                planning_status,
                _,
                buffer_profile_id,
                minimum_order_qty,
            ) in ddmrp_case_rows
        ],
        "DdmrpDemandSignals": [
            {
                "ItemID": "TST-DDMRP-RED",
                "LocationID": "TST-MAIN",
                "DemandQty": 30,
                "DemandDueAt": datetime(2026, 6, 25, 12, tzinfo=timezone.utc).isoformat(),
                "DemandType": "CustomerOrder",
                "IsQualifiedSpike": False,
            },
            {
                "ItemID": "TST-DDMRP-YELLOW",
                "LocationID": "TST-MAIN",
                "DemandQty": 10,
                "DemandDueAt": datetime(2026, 6, 25, 12, tzinfo=timezone.utc).isoformat(),
                "DemandType": "CustomerOrder",
                "IsQualifiedSpike": False,
            },
            {
                "ItemID": "TST-DDMRP-GREEN",
                "LocationID": "TST-MAIN",
                "DemandQty": 10,
                "DemandDueAt": datetime(2026, 6, 25, 12, tzinfo=timezone.utc).isoformat(),
                "DemandType": "CustomerOrder",
                "IsQualifiedSpike": False,
            },
        ],
        "DdmrpOpenSupply": [
            {
                "ItemID": "TST-DDMRP-RED",
                "LocationID": "TST-MAIN",
                "SupplyQty": 10,
                "ExpectedAt": datetime(2026, 6, 25, 16, tzinfo=timezone.utc).isoformat(),
                "Status": "Open",
            }
        ],
        "Validation": _validation_to_dict(validation),
    }
    store.audit_events.append(
        {
            "EventID": "AUD-TST-DDMRP-NET-FLOW-SEED",
            "RunID": "TST-DDMRP-NET-FLOW",
            "Action": "DdmrpRuntimeCaseSeeded",
            "ActorID": "sdbr-test-data",
            "OccurredAt": captured_at.isoformat(),
            "Details": {
                "SpecIDs": ["BE-DDMRP-001", "BE-DDMRP-006", "UI-DDMRP-001"],
                "MasterDataVersionID": DDMRP_NET_FLOW_MASTER_DATA_VERSION_ID,
                "ExpectedZones": ["Red", "Yellow", "Green", "AboveGreen"],
            },
        }
    )


def _seed_ddmrp_read_only_replenishment_case(*, store: WorkbenchStateStore) -> None:
    evaluated_at = DDMRP_READ_ONLY_REPLENISHMENT_EVALUATED_AT
    operating_model_configuration = {
        "OperatingModelConfigurationID": "TST-DDMRP-RO-OMC-20260711",
        "Status": "Approved",
        "DDMRPConfiguration": {
            "DDMRPConfigurationID": "TST-DDMRP-RO-CONFIG-20260711",
        },
    }
    operating_model_configuration["Fingerprint"] = canonical_operating_model_fingerprint(
        operating_model_configuration
    )
    package_record = {
        "RuntimePlanningInputPackageID": "TST-DDMRP-RO-RPI-20260711",
        "PackageVersion": "1.0.0",
        "PackageStatus": "Reviewed",
        "OperatingModelConfigurationID": operating_model_configuration[
            "OperatingModelConfigurationID"
        ],
        "OperatingModelFingerprint": operating_model_configuration["Fingerprint"],
        "DDMRPConfigurationID": operating_model_configuration["DDMRPConfiguration"][
            "DDMRPConfigurationID"
        ],
        "Payload": {
            "PackageIdentity": {
                "RuntimePlanningInputPackageID": "TST-DDMRP-RO-RPI-20260711",
                "PackageVersion": "1.0.0",
                "PackageStatus": "Reviewed",
                "ScenarioLabel": "DemoFixture",
                "MappingConfidence": "PublicDemoOnly",
            },
            "FrozenDdsopConfiguration": {
                "OperatingModelConfigurationID": operating_model_configuration[
                    "OperatingModelConfigurationID"
                ],
                "OperatingModelFingerprint": operating_model_configuration[
                    "Fingerprint"
                ],
                "DDMRPConfigurationID": operating_model_configuration[
                    "DDMRPConfiguration"
                ]["DDMRPConfigurationID"],
            },
            "ParameterAuthorityEvidence": {
                "ApprovalEvidenceID": "TST-DDMRP-RO-TEST-FIXTURE-ONLY",
                "ParameterEvidenceRefs": [
                    {
                        "FieldGroup": field_group,
                        "EvidenceID": f"TST-DDMRP-RO-{field_group}",
                        "ProductionAuthorityStatus": "PublicDemoOnly",
                        "Applicability": "Applicable",
                    }
                    for field_group in ("ADU", "DLT", "BufferZones", "BufferProfile")
                ],
            },
            "RuntimeEvidenceSnapshot": {
                "OperationalStateSnapshotID": "TST-DDMRP-RO-SNAPSHOT-20260711",
                "SnapshotAt": evaluated_at.isoformat(),
                "InventoryPositions": [
                    {
                        "ItemID": item_id,
                        "LocationID": "TST-MAIN",
                        "AvailableQty": quantity,
                    }
                    for item_id, _, quantity, _ in (
                        DDMRP_READ_ONLY_REPLENISHMENT_ROWS
                    )
                ],
                "DemandSignals": [],
                "OpenSupplySignals": [],
            },
        },
    }
    ledger_identity = build_relevant_planning_ledger_identity(
        scope_item_locations=[
            (item_id, "TST-MAIN")
            for item_id in DDMRP_READ_ONLY_REPLENISHMENT_ITEM_IDS
        ],
        planning_demand_commitments=store.planning_demand_commitments,
        planning_reservation_batches=store.planning_reservation_batches,
        ccr_capacity_reservations=store.ccr_capacity_reservations,
        material_planning_allocations=store.material_planning_allocations,
        active_replenishment_graphs=store.ddmrp_active_replenishment_graphs,
    )
    signature, gates = build_read_only_authority_signature(
        package_record=package_record,
        operating_model_configuration={"Payload": operating_model_configuration},
        relevant_planning_ledger=ledger_identity,
        evaluated_at=evaluated_at,
    )
    write_set = prepare_ddmrp_evaluation(
        evaluation_request_id=DDMRP_READ_ONLY_REPLENISHMENT_CASE_ID,
        recorded_at=evaluated_at,
        actor_id="sdbr-test-data",
        runtime_result={
            "EvaluationMode": "DDMRPNetFlowV1",
            "Boundary": "read-only",
            "EvaluatedAt": evaluated_at.isoformat(),
            "Summary": {},
            "Lines": [
                _ddmrp_read_only_replenishment_runtime_line(
                    item_id=item_id,
                    planning_status=planning_status,
                    net_flow_position=net_flow_position,
                    suggested_replenishment_qty=suggested_replenishment_qty,
                )
                for (
                    item_id,
                    planning_status,
                    net_flow_position,
                    suggested_replenishment_qty,
                ) in DDMRP_READ_ONLY_REPLENISHMENT_ROWS
            ],
            "Issues": [],
        },
        authority_signature=signature,
        gates=gates,
        existing_chains=store.ddmrp_replenishment_chains,
        existing_recommendations=store.ddmrp_replenishment_recommendations,
        existing_events=tuple(store.ddmrp_replenishment_events),
        active_replenishment_graphs=store.ddmrp_active_replenishment_graphs,
    )
    staged = stage_ddmrp_evaluation(
        write_set=write_set,
        evaluation_runs=store.ddmrp_evaluation_runs,
        evaluation_rows=store.ddmrp_evaluation_rows,
        chains=store.ddmrp_replenishment_chains,
        recommendations=store.ddmrp_replenishment_recommendations,
        events=store.ddmrp_replenishment_events,
        request_results=store.ddmrp_evaluation_request_results,
    )
    apply_staged_ddmrp_evaluation(
        staged=staged,
        evaluation_runs=store.ddmrp_evaluation_runs,
        evaluation_rows=store.ddmrp_evaluation_rows,
        chains=store.ddmrp_replenishment_chains,
        recommendations=store.ddmrp_replenishment_recommendations,
        events=store.ddmrp_replenishment_events,
        request_results=store.ddmrp_evaluation_request_results,
    )


def _ddmrp_read_only_replenishment_runtime_line(
    *,
    item_id: str,
    planning_status: str,
    net_flow_position: float,
    suggested_replenishment_qty: float,
) -> dict[str, object]:
    return {
        "ItemID": item_id,
        "LocationID": "TST-MAIN",
        "BufferProfileID": "TST-DDMRP-RO-BUFFER-PROFILE",
        "DLTMinutes": 1440,
        "OnHandQty": net_flow_position,
        "QualifiedOnHandQty": net_flow_position,
        "QualifiedOpenSupplyQty": 0.0,
        "QualifiedDemandQty": 0.0,
        "NetFlowPosition": net_flow_position,
        "TopOfRed": 20.0,
        "TopOfYellow": 50.0,
        "TopOfGreen": 100.0,
        "PlanningStatus": planning_status,
        "ExecutionStatus": planning_status,
        "SuggestedReplenishmentQty": suggested_replenishment_qty,
        "RecommendedAction": (
            "Replenish" if suggested_replenishment_qty else "Monitor"
        ),
        "DemandComponents": [],
        "SupplyComponents": [],
        "PhysicalOnHandQty": net_flow_position,
        "AuthorityAllocatedQty": 0.0,
        "AuthorityAvailableQty": net_flow_position,
        "QualityState": "Unrestricted",
        "Uom": "EA",
    }


def _remove_case_runtime_state(
    *,
    store: WorkbenchStateStore,
    case: TestCaseSpec,
) -> None:
    run_id = case.planning_run_id
    version = store.master_data_versions.get(case.master_data_version_id, {})
    order_ids = {
        str(item.get("OrderID"))
        for item in version.get("Orders", [])
        if isinstance(item, dict) and item.get("OrderID") is not None
    }
    store.test_case_acceptance_decisions[:] = [
        item for item in store.test_case_acceptance_decisions
        if item.get("CaseID") != case.case_id
    ]
    store.release_authorizations[:] = [
        item for item in store.release_authorizations
        if item.request_id != run_id and item.order_id not in order_ids
    ]
    store.execution_events[:] = [
        item for item in store.execution_events
        if getattr(item, "run_id", None) != run_id
        and getattr(item, "order_id", None) not in order_ids
    ]
    store.release_decision_packages[:] = [
        item for item in store.release_decision_packages
        if item.get("RunID") != run_id
    ]
    store.replan_requests[:] = [
        item for item in store.replan_requests
        if getattr(item, "order_id", None) not in order_ids
    ]
    store.replan_schedule_snapshots[:] = [
        item for item in store.replan_schedule_snapshots
        if item.get("RunID") != run_id and item.get("SourceRunID") != run_id
    ]
    store.audit_events[:] = [
        item for item in store.audit_events
        if item.get("RunID") not in {run_id, case.case_id}
    ]


def _seed_cp_sat_business_cases(
    *,
    store: WorkbenchStateStore,
    captured_at: datetime,
) -> None:
    case_builders = [
        _cp_finite_case,
        _cp_alternate_case,
        _cp_calendar_case,
        _cp_efficiency_case,
        _cp_setup_case,
        _cp_infeasible_case,
    ]
    for builder in case_builders:
        version_id, run_id, resources, routings, orders, run_options = builder(captured_at)
        inventory_buffers = _baseline_inventory_buffers()
        material_requirements: list[MaterialRequirement] = []
        validation = validate_master_data(
            resources=resources,
            routings=routings,
            orders=orders,
            inventory_buffers=inventory_buffers,
            material_requirements=material_requirements,
            calendar_timezone=None,
        )
        store.master_data_versions[version_id] = {
            "VersionID": version_id,
            "CapturedAt": captured_at.isoformat(),
            "SourceSystem": "SDBR-CP-SAT-TestData",
            "CreatedBy": "sdbr-test-data",
            "CalendarTimezone": run_options.get("CalendarTimezone"),
            "Status": "Valid" if validation.is_valid else "Invalid",
            "Resources": _resources_to_dict(resources),
            "Routings": _routings_to_dict(routings),
            "Orders": _orders_to_dict(orders),
            "InventoryBuffers": _inventory_buffers_to_dict(inventory_buffers),
            "MaterialRequirements": [],
            "Validation": _validation_to_dict(validation),
        }
        store.planning_runs[run_id] = _pending_run_record(
            run_id=run_id,
            snapshot_id=BASELINE_OPERATIONAL_STATE_ID,
            requested_at=captured_at,
            master_data_version_id=version_id,
            problem_id=str(run_options.get("ProblemID", run_id.replace("RUN", "PROBLEM"))),
            time_buffer_minutes=int(run_options.get("TimeBufferMinutes", 0)),
            objective_strategy_id=str(run_options.get("ObjectiveStrategyID", "balanced")),
            setup_transitions=list(run_options.get("SetupTransitions", [])),
            frozen_calendar_overrides=list(
                run_options.get("FrozenCalendarOverrides", [])
            ),
        )
        for override in run_options.get("FrozenCalendarOverrides", []):
            store.calendar_overrides[str(override["OverrideID"])] = dict(override)


def _cp_finite_case(captured_at: datetime):
    resource = Resource("TST-CP-DRUM", "CP案例-单台约束资源", True, {date(2026, 6, 22): 480})
    routing = Routing(
        "TST-CP-FG-FIN",
        [Operation("CUT", "TST-CP-DRUM", 120, 10)],
    )
    orders = [
        SchedulingOrder("TST-CP-WO-FIN-1", routing.product_id, 1, datetime(2026, 6, 22, 17, tzinfo=timezone.utc), date(2026, 6, 22)),
        SchedulingOrder("TST-CP-WO-FIN-2", routing.product_id, 1, datetime(2026, 6, 22, 17, tzinfo=timezone.utc), date(2026, 6, 22)),
    ]
    return "TST-CP-MDV-FINITE-20260621", "TST-CP-RUN-FINITE-001", [resource], [routing], orders, {}


def _cp_alternate_case(captured_at: datetime):
    resources = [
        Resource("TST-CP-PRIMARY", "CP案例-主资源", True, {date(2026, 6, 22): 480}),
        Resource("TST-CP-ALT", "CP案例-备用资源", True, {date(2026, 6, 22): 480}),
    ]
    routing = Routing(
        "TST-CP-FG-ALT",
        [Operation("CUT", "TST-CP-PRIMARY", 120, 10, ["TST-CP-ALT"])],
    )
    orders = [
        SchedulingOrder("TST-CP-WO-ALT-1", routing.product_id, 1, datetime(2026, 6, 22, 13, tzinfo=timezone.utc), date(2026, 6, 22)),
        SchedulingOrder("TST-CP-WO-ALT-2", routing.product_id, 1, datetime(2026, 6, 22, 13, tzinfo=timezone.utc), date(2026, 6, 22)),
    ]
    return "TST-CP-MDV-ALTERNATE-20260621", "TST-CP-RUN-ALTERNATE-001", resources, [routing], orders, {
        "ObjectiveStrategyID": "flow_first"
    }


def _cp_calendar_case(captured_at: datetime):
    resource = Resource(
        "TST-CP-CAL",
        "CP案例-日历资源",
        True,
        {date(2026, 6, 22): 240},
        calendar=WorkCalendar(
            "TST-CP-CAL-CALENDAR",
            {0},
            [Shift("早班", time(8), time(12))],
            [],
        ),
    )
    routing = Routing(
        "TST-CP-FG-CAL",
        [Operation("HEAT", "TST-CP-CAL", 90, 10)],
    )
    orders = [
        SchedulingOrder("TST-CP-WO-CAL-1", routing.product_id, 1, datetime(2026, 6, 22, 23, tzinfo=timezone.utc), date(2026, 6, 22)),
    ]
    overrides = [
        {
            "OverrideID": "TST-CP-CAL-MAINT-001",
            "CalendarID": "TST-CP-CAL-CALENDAR",
            "ResourceID": "TST-CP-CAL",
            "OverrideType": "ExclusionOrMaintenance",
            "EffectiveStartAt": "2026-06-22T08:00:00+00:00",
            "EffectiveEndAt": "2026-06-22T12:00:00+00:00",
            "CapacityDeltaMinutes": 0,
            "ShiftName": "维护",
            "Reason": "业务案例：白天维护不可排产",
            "CreatedAt": captured_at.isoformat(),
            "CreatedBy": "sdbr-test-data",
            "Status": "Active",
        },
        {
            "OverrideID": "TST-CP-CAL-OT-001",
            "CalendarID": "TST-CP-CAL-CALENDAR",
            "ResourceID": "TST-CP-CAL",
            "OverrideType": "Overtime",
            "EffectiveStartAt": "2026-06-22T18:00:00+00:00",
            "EffectiveEndAt": "2026-06-22T20:00:00+00:00",
            "CapacityDeltaMinutes": 120,
            "ShiftName": "加班",
            "Reason": "业务案例：晚间加班可排产",
            "CreatedAt": captured_at.isoformat(),
            "CreatedBy": "sdbr-test-data",
            "Status": "Active",
        },
    ]
    return "TST-CP-MDV-CALENDAR-20260621", "TST-CP-RUN-CALENDAR-001", [resource], [routing], orders, {
        "FrozenCalendarOverrides": overrides,
        "CalendarTimezone": "UTC",
    }


def _cp_efficiency_case(captured_at: datetime):
    resource = Resource(
        "TST-CP-SLOW",
        "CP案例-低效率资源",
        True,
        {date(2026, 6, 22): 480},
        efficiency_percent=50,
    )
    routing = Routing(
        "TST-CP-FG-EFF",
        [Operation("PROCESS", "TST-CP-SLOW", 60, 10)],
    )
    orders = [
        SchedulingOrder("TST-CP-WO-EFF-1", routing.product_id, 1, datetime(2026, 6, 22, 17, tzinfo=timezone.utc), date(2026, 6, 22)),
    ]
    return "TST-CP-MDV-EFFICIENCY-20260621", "TST-CP-RUN-EFFICIENCY-001", [resource], [routing], orders, {}


def _cp_setup_case(captured_at: datetime):
    resource = Resource("TST-CP-SETUP", "CP案例-换型资源", True, {date(2026, 6, 22): 480})
    routings = [
        Routing("TST-CP-FG-A", [Operation("CUT", "TST-CP-SETUP", 60, 10, setup_family="FAM-A")]),
        Routing("TST-CP-FG-B", [Operation("CUT", "TST-CP-SETUP", 60, 10, setup_family="FAM-B")]),
    ]
    orders = [
        SchedulingOrder("TST-CP-WO-SET-A", "TST-CP-FG-A", 1, datetime(2026, 6, 22, 13, tzinfo=timezone.utc), date(2026, 6, 22)),
        SchedulingOrder("TST-CP-WO-SET-B", "TST-CP-FG-B", 1, datetime(2026, 6, 22, 14, tzinfo=timezone.utc), date(2026, 6, 22)),
    ]
    return "TST-CP-MDV-SETUP-20260621", "TST-CP-RUN-SETUP-001", [resource], routings, orders, {
            "SetupTransitions": [
                {
                    "ResourceID": "TST-CP-SETUP",
                    "FromFamily": "FAM-A",
                    "ToFamily": "FAM-B",
                    "SetupMinutes": 45,
                },
                {
                    "ResourceID": "TST-CP-SETUP",
                    "FromFamily": "FAM-B",
                    "ToFamily": "FAM-A",
                    "SetupMinutes": 45,
                },
            ]
    }


def _cp_infeasible_case(captured_at: datetime):
    start = datetime(2026, 6, 22, 8, tzinfo=timezone.utc)
    resource = Resource("TST-CP-TIGHT", "CP案例-时间窗资源", True, {date(2026, 6, 22): 480})
    routing = Routing(
        "TST-CP-FG-INF",
        [
            Operation(
                "CUT",
                "TST-CP-TIGHT",
                120,
                10,
                earliest_start_at=start,
                latest_end_at=start + timedelta(minutes=60),
            )
        ],
    )
    orders = [
        SchedulingOrder("TST-CP-WO-INF-1", routing.product_id, 1, datetime(2026, 6, 22, 17, tzinfo=timezone.utc), date(2026, 6, 22)),
    ]
    return "TST-CP-MDV-INFEASIBLE-20260621", "TST-CP-RUN-INFEASIBLE-001", [resource], [routing], orders, {}


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
        ("TST_WC_PREP", "测试-备料工作中心", False, 540),
        ("TST_WC_DRUM", "测试-约束机加工", True, 420),
        ("TST_WC_ALT_DRUM", "测试-备用机加工", False, 360),
        ("TST_WC_PAINT", "测试-表面处理", False, 480),
        ("TST_WC_ASSY", "测试-总装", False, 600),
        ("TST_WC_PACK", "测试-包装", False, 480),
    ]
    rows = [
        ResourceCapacityImportRow(resource_id, name, is_constraint, workday, capacity)
        for resource_id, name, is_constraint, capacity in resource_specs
        for workday in workdays
    ]
    return import_resources_from_capacity_rows(rows)


def _baseline_routings() -> list[Routing]:
    rows = [
        RoutingImportRow("TST-FG-A", "PRIMARY", True, "PREP", "TST_WC_PREP", 35, 10),
        RoutingImportRow("TST-FG-A", "PRIMARY", True, "DRUM", "TST_WC_DRUM", 95, 20, ["TST_WC_ALT_DRUM"]),
        RoutingImportRow("TST-FG-A", "PRIMARY", True, "ASSY", "TST_WC_ASSY", 60, 30),
        RoutingImportRow("TST-FG-A", "PRIMARY", True, "PACK", "TST_WC_PACK", 25, 40),
        RoutingImportRow("TST-FG-B", "PRIMARY", True, "PREP", "TST_WC_PREP", 25, 10),
        RoutingImportRow("TST-FG-B", "PRIMARY", True, "DRUM", "TST_WC_DRUM", 120, 20, ["TST_WC_ALT_DRUM"]),
        RoutingImportRow("TST-FG-B", "PRIMARY", True, "PAINT", "TST_WC_PAINT", 70, 30),
        RoutingImportRow("TST-FG-B", "PRIMARY", True, "PACK", "TST_WC_PACK", 30, 40),
        RoutingImportRow("TST-FG-C", "PRIMARY", True, "PREP", "TST_WC_PREP", 45, 10),
        RoutingImportRow("TST-FG-C", "PRIMARY", True, "DRUM", "TST_WC_DRUM", 80, 20, ["TST_WC_ALT_DRUM"]),
        RoutingImportRow("TST-FG-C", "PRIMARY", True, "ASSY", "TST_WC_ASSY", 90, 30),
        RoutingImportRow("TST-FG-C", "PRIMARY", True, "PACK", "TST_WC_PACK", 35, 40),
        RoutingImportRow("TST-FG-B", "ALT-PAINT-LATE", False, "PREP", "TST_WC_PREP", 25, 10),
        RoutingImportRow("TST-FG-B", "ALT-PAINT-LATE", False, "DRUM", "TST_WC_ALT_DRUM", 145, 20),
        RoutingImportRow("TST-FG-B", "ALT-PAINT-LATE", False, "PAINT", "TST_WC_PAINT", 65, 30),
        RoutingImportRow("TST-FG-B", "ALT-PAINT-LATE", False, "PACK", "TST_WC_PACK", 30, 40),
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
    master_data_version_id: str = BASELINE_MASTER_DATA_VERSION_ID,
    problem_id: str = "TST-PROBLEM-BASELINE",
    time_buffer_minutes: int = 480,
    objective_strategy_id: str = "balanced",
    setup_transitions: list[dict[str, object]] | None = None,
    frozen_calendar_overrides: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    return {
        "RunID": run_id,
        "ProblemID": problem_id,
        "Status": "Pending",
        "MasterDataVersionID": master_data_version_id,
        "MasterDataCapturedAt": requested_at.isoformat(),
        "OperationalStateSnapshotID": snapshot_id,
        "OperationalStateCapturedAt": requested_at.isoformat(),
        "SourceRunID": None,
        "ReleasePolicyVersionID": None,
        "FrozenReleasePolicy": None,
        "FrozenCalendarOverrides": [dict(item) for item in (frozen_calendar_overrides or [])],
        "ScheduleStartAt": datetime(2026, 6, 22, 8, tzinfo=timezone.utc).isoformat(),
        "TimeBufferMinutes": time_buffer_minutes,
        "FreezeWindowMinutes": 0,
        "ObjectiveStrategyID": objective_strategy_id,
        "FrozenSchedulingStrategy": None,
        "SetupTransitions": [dict(item) for item in (setup_transitions or [])],
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
    collection_names = (
        "execution_events",
        "replan_requests",
        "replan_schedule_snapshots",
        "release_authorizations",
        "operational_state_snapshots",
        "release_decision_packages",
        "dbr_release_policies",
        "calendar_overrides",
        "scheduling_strategy_versions",
        "integration_messages",
        "test_case_acceptance_decisions",
        "ddmrp_decoupling_points",
        "ddmrp_demand_signals",
        "ddmrp_open_supply",
        "ddmrp_evaluation_runs",
        "ddmrp_evaluation_rows",
        "ddmrp_replenishment_chains",
        "ddmrp_replenishment_recommendations",
        "ddmrp_replenishment_events",
        "ddmrp_active_replenishment_graphs",
        "ddmrp_evaluation_request_results",
        "master_data_versions",
        "planning_runs",
        "planning_demand_commitments",
        "planning_reservation_batches",
        "ccr_capacity_reservations",
        "material_planning_allocations",
        "order_commitment_evaluations",
        "order_commitment_events",
        "planning_reservation_events",
        "processed_planning_event_keys",
        "audit_events",
    )
    snapshot = store.snapshot_state()
    try:
        for name in collection_names:
            getattr(store, name).clear()
    except BaseException:
        store.restore_state(snapshot)
        raise


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
            "CapacityUnits": resource.capacity_units,
            "EfficiencyPercent": resource.efficiency_percent,
            "ResourceType": resource.resource_type,
            "IsBuffered": resource.is_buffered,
            "OwnerID": resource.owner_id,
            "Category": resource.category,
            "Calendar": (
                {
                    "CalendarID": resource.calendar.calendar_id,
                    "WorkingWeekdays": sorted(resource.calendar.working_weekdays),
                    "Shifts": [
                        {
                            "Name": shift.name,
                            "Start": shift.start.isoformat(),
                            "End": shift.end.isoformat(),
                        }
                        for shift in resource.calendar.shifts
                    ],
                    "MaintenanceWindows": [
                        {
                            "Start": window.start.isoformat(),
                            "End": window.end.isoformat(),
                        }
                        for window in resource.calendar.maintenance_windows
                    ],
                    "Holidays": [
                        holiday.isoformat()
                        for holiday in sorted(resource.calendar.holidays or set())
                    ],
                }
                if resource.calendar is not None
                else None
            ),
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
                    "SetupFamily": operation.setup_family,
                    "EarliestStartAt": (
                        operation.earliest_start_at.isoformat()
                        if operation.earliest_start_at is not None
                        else None
                    ),
                    "LatestEndAt": (
                        operation.latest_end_at.isoformat()
                        if operation.latest_end_at is not None
                        else None
                    ),
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
