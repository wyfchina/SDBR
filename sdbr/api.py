from __future__ import annotations

from copy import deepcopy
from datetime import date, datetime, time, timedelta, timezone
from hashlib import sha256
from hmac import compare_digest
from pathlib import Path
from secrets import token_urlsafe
from threading import Lock, RLock
from time import monotonic
from typing import Callable, Literal, Mapping
from zoneinfo import ZoneInfo

import anyio
from fastapi import FastAPI, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

from sdbr.api_payload import get_planner_workbench_demo_payload
from sdbr.adventureworks_product_demo_profile import (
    build_adventureworks_product_demo_profile_status,
)
from sdbr.adventureworks_scheduling_adapter import (
    build_adventureworks_scheduling_adapter_status,
)
from sdbr.administration_view import build_administration_workbench
from sdbr.base_calendar import (
    apply_base_calendar_assignments,
    base_calendar_driver_status,
    resource_calendar_assignment_driver_status,
)
from sdbr.calendar_import import (
    CalendarImportRow,
    attach_work_calendars_to_resources,
    import_work_calendars_from_rows,
)
from sdbr.calendar_overrides import (
    apply_calendar_overrides,
    calendar_override_driver_status,
)
from sdbr.calendar_preview import build_calendar_preview
from sdbr.ccr_shadow_scheduler import (
    SHADOW_ALGORITHM,
    evaluate_ccr_shadow_schedule,
)
from sdbr.data_readiness import build_data_readiness
from sdbr.dispatch_priority import (
    build_mes_dispatch_priority_queue,
    build_mes_dispatch_suggestion_package,
)
from sdbr.ddom_operational_metrics import build_ddom_operational_metrics
from sdbr.ddmrp import (
    DecouplingPoint,
    DemandSignal,
    OpenSupply,
    evaluate_ddmrp_net_flow,
)
from sdbr.ddsop_contracts import (
    build_planning_run_feedback_message,
    build_variance_analysis_feedback_message,
    process_ddsop_config_message,
    validate_required_master_data_references,
)
from sdbr.ddsop_delivery import deliver_ddsop_feedback_message
from sdbr.buffer_execution_view import (
    build_buffer_execution_workbench,
    build_buffer_order_detail,
)
from sdbr.exception_center_view import (
    build_exception_center_workbench,
    build_exception_detail,
)
from sdbr.inventory_import import InventoryBufferImportRow, import_inventory_buffers_from_rows
from sdbr.integration_contracts import (
    find_integration_contract,
    integration_adapter_status_payload,
    integration_contracts_payload,
    integration_dead_letters,
    integration_message_record,
    replay_integration_message,
    validate_integration_message,
)
from sdbr.master_data_validation import (
    MasterDataValidationResult,
    MaterialRequirement,
    validate_master_data,
)
from sdbr.material_state import (
    MaterialAvailabilityImportRow,
    WipLimitImportRow,
    import_material_availability_from_rows,
    import_wip_limits_from_rows,
)
from sdbr.light_mrp import evaluate_light_mrp
from sdbr.order_import import OrderImportRow, import_orders_from_rows
from sdbr.operational_state import (
    OperationalStateSnapshot,
    create_operational_state_snapshot,
    evaluate_operational_state_freshness,
)
from sdbr.order_commitment_evaluation import (
    ACCEPTANCE_DECISIONS,
    OrderCommitmentConflict,
    OrderCommitmentSnapshotNotFound,
    REFERENCE_CCR_PROTECTION_POLICY,
    _parse_aware,
    accepted_evaluation_record,
    build_order_commitment_basis,
    candidate_demand_commitment_id,
    canonical_decision_fingerprint,
    canonical_fingerprint,
    canonical_json,
    canonical_order_commitment_decision_facts,
    create_order_commitment_evaluation,
    evaluate_mto_material_availability,
    exact_order_commitment_intake_replay,
    normalize_mto_order,
    prepare_mto_acceptance,
    register_order_commitment_evaluation,
    rejected_evaluation_record,
    select_order_commitment_operational_snapshot,
    supersede_open_order_commitment_evaluations,
)
from sdbr.order_commitment_view import (
    SAFE_AUDIT_DETAIL_FIELDS,
    build_order_commitment_detail,
    build_order_commitment_workbench,
)
from sdbr.plan_publication import (
    build_plan_publication_view,
    mark_superseded,
    publication_state,
    schedule_fingerprint as planning_schedule_fingerprint,
    transition_publication_state,
)
from sdbr.planning_reservations import (
    ReservationConflict,
    ReservationLegacyMigrationRequired,
    apply_reservation_write_set,
)
from sdbr.public_demo_golden_loop import (
    get_public_demo_golden_loop_status,
    run_public_demo_golden_loop,
)
from sdbr.planner_view import (
    InventoryBufferPolicy,
    build_planner_workbench_view,
    planner_workbench_view_to_dict,
)
from sdbr.planning_run_view import (
    build_planning_run_detail,
    build_planning_run_workbench,
)
from sdbr.planning_run_reservation_bridge import (
    GRAPH_FORMAT,
    LEGACY_GRAPH_FORMAT,
    ReservationBatchReferenceError,
    ReservationGraphDriftError,
    ReservationGraphMigrationRequiredError,
    ScheduledOccupancyEvidenceError,
    freeze_planning_reservations,
    transition_planning_reservations_for_run,
)
from sdbr.planning_commitments import DEMAND_SOURCE_TYPES
from sdbr.schedule_result_view import (
    build_schedule_result_workbench,
    compare_schedule_results,
)
from sdbr.schedule_output_governance import (
    audit_context_for_order,
    build_schedule_output_governance,
    build_schedule_output_package,
    output_context_for_order,
    release_context_for_order,
)
from sdbr.sdbr_what_if import (
    build_sdbr_what_if_workspace,
    evaluate_sdbr_what_if_scenario,
)
from sdbr.work_order_release_view import (
    build_release_management_workbench,
    build_scheduled_work_order_detail,
    build_scheduled_work_order_workbench,
)
from sdbr.planner_workbench import (
    MaintenanceWindow,
    Operation,
    ReleaseDecision,
    Resource,
    Routing,
    SchedulingOrder,
    Shift,
    WorkCalendar,
    evaluate_release_decision,
)
from sdbr.resource_import import ResourceCapacityImportRow, import_resources_from_capacity_rows
from sdbr.release_stability import (
    ReleaseStabilityInput,
    ReleaseStabilityPolicy,
    ReleaseStabilityResult,
    evaluate_release_stability,
)
from sdbr.release_decision_package import build_release_decision_package
from sdbr.release_candidates import (
    MaterialAvailability,
    WipLimit,
    release_candidate_rows_from_schedule,
)
from sdbr.release_policy import release_policy_evidence, release_policy_settings
from sdbr.release_authorization import (
    ReleaseAuthorization,
    build_dispatch_package,
    build_release_stability_report,
    create_release_authorization,
)
from sdbr.replanning import (
    ReplanRequest,
    create_replan_request,
    decide_replan_request,
    finish_replan_execution,
    start_replan_execution,
)
from sdbr.routing_import import RoutingImportRow, import_routings_from_operation_rows
from sdbr.runtime_environment import (
    RuntimeEnvironment,
    resolve_runtime_environment,
)
from sdbr.schedule_output import (
    scheduled_order_rows_from_schedule,
    scheduled_work_order_rows_from_schedule,
)
from sdbr.scheduling_solver import (
    ACTIVE_SOLVER_BACKEND_ID,
    BUILT_IN_OBJECTIVE_STRATEGY_IDS,
    FixedOperationAssignment,
    PAUSED_SOLVER_BACKEND_IDS,
    SchedulingObjective,
    SolverDiagnostic,
    SetupTransition,
    SimioValidationAdapter,
    build_scheduling_problem,
    build_capacity_buckets_from_resources,
    create_solver_engine,
)
from sdbr.simio_validation import (
    SimioValidationError,
    create_simio_validation_run,
    default_simio_template_registry,
    resolve_simio_template,
    summarize_simio_validation,
)
from sdbr.scenario_comparison import compare_scenarios
from sdbr.shop_floor_execution import (
    ExecutionEvent,
    build_authorized_execution_alerts,
    build_authorized_execution_status,
    build_execution_variance_stability,
    build_schedule_execution_variance,
    default_exception_codes,
    summarize_execution_events,
    validate_execution_event,
)
from sdbr.state_store import (
    SQLiteWorkbenchStateStore,
    StateStoreManagedRequestRejected,
    StateStoreRevisionConflict,
    WorkbenchStateStore,
)
from sdbr.test_data import (
    reset_test_case_state,
    seed_baseline_test_data,
    seed_mto_order_commitment_fixture,
    test_case_catalog_payload,
)
from sdbr.test_case_acceptance import (
    DEFAULT_CASE_EVALUATED_AT,
    build_test_case_acceptance_workbench,
    create_test_case_acceptance_decision,
)


_DIRECT_EXECUTION_CLAIM_GRACE_SECONDS = 60


class ResourcePayload(BaseModel):
    ResourceID: str
    Name: str
    IsConstraint: bool
    DailyCapacityMinutes: dict[str, int]
    Calendar: CalendarPayload | None = None
    CapacityUnits: int = Field(default=1, ge=1)
    EfficiencyPercent: int = Field(default=100, ge=1)
    ResourceType: str | None = None
    IsBuffered: bool = False
    OwnerID: str | None = None
    Category: str | None = None


class ShiftPayload(BaseModel):
    Name: str
    Start: time
    End: time


class MaintenanceWindowPayload(BaseModel):
    Start: datetime
    End: datetime


class CalendarPayload(BaseModel):
    CalendarID: str
    WorkingWeekdays: list[int]
    Shifts: list[ShiftPayload]
    MaintenanceWindows: list[MaintenanceWindowPayload] = []
    Holidays: list[date] = []


class OperationPayload(BaseModel):
    OperationID: str
    ResourceID: str
    DurationMinutes: int
    Sequence: int
    AlternateResourceIDs: list[str] = []
    SetupFamily: str | None = None
    EarliestStartAt: datetime | None = None
    LatestEndAt: datetime | None = None


class SetupTransitionPayload(BaseModel):
    ResourceID: str
    FromFamily: str
    ToFamily: str
    SetupMinutes: int = Field(ge=0)


class RoutingPayload(BaseModel):
    ProductID: str
    Operations: list[OperationPayload]
    RoutingID: str = "PRIMARY"
    IsPrimary: bool = True


class MtoMaterialRequirementPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    RequirementLineID: str
    ItemID: str
    LocationID: str
    RequiredQty: float = Field(gt=0)
    Uom: str = "EA"


class MtoOrderCommitmentIntakePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    SourceSystem: str = "MockERP"
    SourceObjectType: str = "CustomerOrder"
    OrderID: str
    OrderVersion: str
    DemandLineID: str = "1"
    ProductID: str
    LocationID: str
    Quantity: float = Field(gt=0)
    Uom: str = "EA"
    RequestedDueAt: AwareDatetime
    BusinessPriority: int = Field(default=100, ge=1, le=999)
    ReceivedAt: AwareDatetime
    TraceID: str
    BaselinePlanningRunID: str
    RoutingID: str = "PRIMARY"
    OperationalStateSnapshotID: str | None = None
    MaterialRequirements: list[MtoMaterialRequirementPayload] = Field(
        default_factory=list
    )


class MtoOrderCommitmentReevaluationPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    RequestedBy: str
    BaselinePlanningRunID: str | None = None
    OperationalStateSnapshotID: str | None = None
    CheckMaterialAvailability: bool = True
    MaterialCheckSkipReason: str | None = None


class MtoOrderCommitmentDecisionPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    DecisionID: str
    Decision: Literal[
        "AcceptRequestedDate",
        "ConditionallyAcceptRequestedDate",
        "AcceptRecommendedDate",
        "ConditionallyAcceptRecommendedDate",
        "Reject",
    ]
    DecidedBy: str
    Reason: str
    ExpectedEvaluationFingerprint: str
    CcrRiskAcknowledged: bool = False
    MaterialRiskAcknowledged: bool = False


def _mto_order_from_payload(
    payload: MtoOrderCommitmentIntakePayload,
) -> dict[str, object]:
    return {
        "SourceSystem": payload.SourceSystem,
        "SourceObjectType": payload.SourceObjectType,
        "OrderID": payload.OrderID,
        "OrderVersion": payload.OrderVersion,
        "DemandLineID": payload.DemandLineID,
        "ProductID": payload.ProductID,
        "LocationID": payload.LocationID,
        "Quantity": payload.Quantity,
        "Uom": payload.Uom,
        "RequestedDueAt": payload.RequestedDueAt,
        "BusinessPriority": payload.BusinessPriority,
        "ReceivedAt": payload.ReceivedAt,
        "TraceID": payload.TraceID,
        "BaselinePlanningRunID": payload.BaselinePlanningRunID,
        "RoutingID": payload.RoutingID,
        "MaterialRequirements": [
            row.model_dump() for row in payload.MaterialRequirements
        ],
    }


class OrderPayload(BaseModel):
    OrderID: str
    ProductID: str
    Quantity: float
    DueDate: datetime
    TargetStartDate: date


class SimioValidationRunPayload(BaseModel):
    RunID: str
    RunnerMode: Literal["auto", "mock", "local"] = "auto"
    TemplateID: str | None = None
    RequestedBy: str = "planner-1"
    RequestedAt: datetime | None = None


class InventoryBufferPayload(BaseModel):
    ItemID: str
    LocationID: str
    OnHandQty: float
    RedZoneQty: float
    YellowZoneQty: float
    GreenZoneQty: float


class MaterialRequirementPayload(BaseModel):
    OrderID: str
    ItemID: str
    LocationID: str
    RequiredQty: float


class MaterialRequirementImportRowPayload(BaseModel):
    OrderID: str
    ItemID: str
    LocationID: str
    RequiredQty: float


class DdmrpDecouplingPointPayload(BaseModel):
    ItemID: str
    LocationID: str
    BufferProfileID: str
    DLTMinutes: int = Field(ge=0)
    OrderMultipleQty: float = Field(default=0.0, ge=0)
    MinimumOrderQty: float = Field(default=0.0, ge=0)
    Status: Literal["Draft", "Active", "Retired"] = "Active"


class DdmrpDemandSignalPayload(BaseModel):
    ItemID: str
    LocationID: str
    DemandQty: float = Field(ge=0)
    DemandDueAt: datetime
    DemandType: str = "CustomerOrder"
    IsQualifiedSpike: bool = False


class DdmrpOpenSupplyPayload(BaseModel):
    ItemID: str
    LocationID: str
    SupplyQty: float = Field(ge=0)
    ExpectedAt: datetime | None = None
    Status: str = "Open"


class DdmrpDecouplingPointImportPayload(BaseModel):
    Rows: list[DdmrpDecouplingPointPayload]


class DdmrpDemandSignalImportPayload(BaseModel):
    Rows: list[DdmrpDemandSignalPayload]


class DdmrpOpenSupplyImportPayload(BaseModel):
    Rows: list[DdmrpOpenSupplyPayload]


class DdmrpNetFlowEvaluationPayload(BaseModel):
    EvaluatedAt: datetime
    DecouplingPoints: list[DdmrpDecouplingPointPayload]
    StockBuffers: list[InventoryBufferPayload]
    DemandSignals: list[DdmrpDemandSignalPayload] = []
    OpenSupply: list[DdmrpOpenSupplyPayload] = []


class PlannerWorkbenchCalculatePayload(BaseModel):
    ProblemID: str
    ScheduleStartAt: datetime
    SourceRunID: str | None = None
    Resources: list[ResourcePayload]
    Routings: list[RoutingPayload]
    Orders: list[OrderPayload]
    SolverBackendID: str = "baseline-finite"
    TimeBufferMinutes: int = 0
    FreezeWindowMinutes: int = Field(default=0, ge=0)
    ObjectiveStrategyID: str = "v1_delivery_flow_bottleneck"
    GeneratedAt: datetime | None = None
    InventoryBuffers: list[InventoryBufferPayload] = []
    MaterialRequirements: list[MaterialRequirementPayload] = []
    SetupTransitions: list[SetupTransitionPayload] = []
    CalendarTimezone: str | None = None


class ReleaseStabilityPolicyPayload(BaseModel):
    ToleranceMinutes: int = 30
    ReplanThresholdMinutes: int = 120
    ConsecutiveBlockedThreshold: int = 3
    ReplanCooldownMinutes: int = 60


class PlannerWorkbenchReleasePayload(PlannerWorkbenchCalculatePayload):
    OrderID: str
    RequestedReleaseAt: datetime
    PreviousConsecutiveBlockedCount: int = 0
    LastReplanAt: datetime | None = None
    StabilityPolicy: ReleaseStabilityPolicyPayload = ReleaseStabilityPolicyPayload()


class PlannerWorkbenchScenarioComparePayload(BaseModel):
    Baseline: PlannerWorkbenchCalculatePayload
    Candidate: PlannerWorkbenchCalculatePayload


class ResourceCapacityImportRowPayload(BaseModel):
    ResourceID: str
    Name: str
    IsConstraint: bool
    CapacityDate: date
    CapacityMinutes: int


class CalendarImportRowPayload(BaseModel):
    ResourceID: str
    CalendarID: str
    WorkingWeekdays: list[int]
    ShiftName: str | None = None
    ShiftStart: time | None = None
    ShiftEnd: time | None = None
    Holiday: date | None = None
    MaintenanceStart: datetime | None = None
    MaintenanceEnd: datetime | None = None


class ResourceImportPayload(BaseModel):
    Rows: list[ResourceCapacityImportRowPayload]
    CalendarRows: list[CalendarImportRowPayload] = []
    CalendarTimezone: str | None = None


class InventoryBufferImportRowPayload(BaseModel):
    ItemID: str
    LocationID: str
    OnHandQty: float
    RedZoneQty: float
    YellowZoneQty: float
    GreenZoneQty: float


class InventoryBufferImportPayload(BaseModel):
    Resources: list[ResourcePayload]
    Rows: list[InventoryBufferImportRowPayload]
    CalendarTimezone: str | None = None


class RoutingImportRowPayload(BaseModel):
    ProductID: str
    RoutingID: str
    IsPrimary: bool
    OperationID: str
    ResourceID: str
    DurationMinutes: int
    Sequence: int
    AlternateResourceIDs: list[str] = []


class RoutingImportPayload(BaseModel):
    Resources: list[ResourcePayload]
    Rows: list[RoutingImportRowPayload]
    CalendarTimezone: str | None = None


class OrderImportRowPayload(BaseModel):
    OrderID: str
    ProductID: str
    Quantity: float
    DueDate: datetime
    TargetStartDate: date


class OrderImportPayload(BaseModel):
    Resources: list[ResourcePayload]
    Routings: list[RoutingPayload]
    Rows: list[OrderImportRowPayload]
    CalendarTimezone: str | None = None


class MasterDataImportPayload(BaseModel):
    ResourceRows: list[ResourceCapacityImportRowPayload]
    CalendarRows: list[CalendarImportRowPayload] = []
    RoutingRows: list[RoutingImportRowPayload]
    OrderRows: list[OrderImportRowPayload]
    InventoryBufferRows: list[InventoryBufferImportRowPayload] = []
    MaterialRequirementRows: list[MaterialRequirementImportRowPayload] = []
    DdmrpDecouplingPointRows: list[DdmrpDecouplingPointPayload] = []
    DdmrpDemandSignalRows: list[DdmrpDemandSignalPayload] = []
    DdmrpOpenSupplyRows: list[DdmrpOpenSupplyPayload] = []
    CalendarTimezone: str | None = None


class MasterDataVersionPayload(MasterDataImportPayload):
    VersionID: str
    CapturedAt: datetime
    SourceSystem: str = "ManualImport"
    CreatedBy: str


class MasterDataVersionTransitionPayload(BaseModel):
    ActorID: str
    OccurredAt: datetime
    Reason: str | None = None


class DbrReleasePolicyPayload(BaseModel):
    VersionID: str
    CreatedAt: datetime
    CreatedBy: str
    ScopeID: str = "global"
    RopeBufferMinutes: int = Field(default=120, ge=0)
    GreenZoneRatio: float = Field(default=0.33, ge=0)
    YellowZoneRatio: float = Field(default=0.34, ge=0)
    RedZoneRatio: float = Field(default=0.33, ge=0)
    MaxWipCount: int | None = Field(default=None, ge=0)
    MaterialLookaheadMinutes: int = Field(default=0, ge=0)
    MaterialCheckWindowMinutes: int | None = Field(default=None, ge=0)
    StabilityToleranceMinutes: int = Field(default=30, ge=0)
    StabilityReplanThresholdMinutes: int = Field(default=120, ge=0)
    ConsecutiveBlockedThreshold: int = Field(default=3, ge=1)
    ReplanCooldownMinutes: int = Field(default=60, ge=0)
    Status: Literal["Draft", "Active", "Retired"] = "Draft"


class CalendarOverridePayload(BaseModel):
    OverrideID: str
    CalendarID: str
    ResourceID: str | None = None
    OverrideType: Literal[
        "TemporaryShiftOverride",
        "ExclusionOrMaintenance",
        "Overtime",
    ]
    EffectiveStartAt: datetime
    EffectiveEndAt: datetime
    CapacityDeltaMinutes: int = 0
    ShiftName: str | None = None
    Reason: str | None = None
    CreatedAt: datetime
    CreatedBy: str
    Status: Literal["Draft", "Active", "Retired"] = "Draft"


class BaseCalendarPayload(BaseModel):
    CalendarID: str
    DisplayName: str | None = None
    WorkingWeekdays: list[int]
    Shifts: list[ShiftPayload]
    MaintenanceWindows: list[MaintenanceWindowPayload] = []
    Holidays: list[date] = []
    Timezone: str = "UTC"
    CreatedAt: datetime
    CreatedBy: str
    Status: Literal["Draft", "Active", "Retired"] = "Draft"


class ResourceCalendarAssignmentPayload(BaseModel):
    AssignmentID: str
    ResourceID: str
    CalendarID: str
    CreatedAt: datetime
    CreatedBy: str
    Status: Literal["Draft", "Active", "Retired"] = "Draft"


class SchedulingStrategyPayload(BaseModel):
    StrategyID: str
    DisplayName: str
    CreatedAt: datetime
    CreatedBy: str
    TardinessWeight: int = Field(default=100, ge=0)
    MakespanWeight: int = Field(default=1, ge=0)
    AlternateResourcePenaltyWeight: int = Field(default=10, ge=0)
    Description: str | None = None
    Status: Literal["Draft", "Active", "Retired"] = "Draft"


class PlanningRunPayload(BaseModel):
    RunID: str
    ProblemID: str
    MasterDataVersionID: str
    OperationalStateSnapshotID: str
    OperatingModelConfigurationID: str | None = None
    SourceRunID: str | None = None
    ReleasePolicyVersionID: str | None = None
    ScheduleStartAt: datetime
    TimeBufferMinutes: int = Field(default=0, ge=0)
    FreezeWindowMinutes: int = Field(default=0, ge=0)
    ObjectiveStrategyID: str = "v1_delivery_flow_bottleneck"
    SetupTransitions: list[SetupTransitionPayload] = []
    SolverBackendID: Literal["ortools", "gurobi"] = "ortools"
    TimeLimitSeconds: int = Field(default=300, ge=1, le=3600)
    MaxAttempts: int = Field(default=3, ge=1, le=10)
    RetryDelaySeconds: int = Field(default=60, ge=0, le=3600)
    PlanningReservationBatchIDs: list[object] = Field(default_factory=list)
    RequestedBy: str
    RequestedAt: datetime


class PlanningRunExecutionPayload(BaseModel):
    ExecutedBy: str
    StartedAt: AwareDatetime
    CompletedAt: AwareDatetime | None = None
    TimeLimitSeconds: int = Field(default=300, ge=1, le=3600)
    LeaseToken: str | None = None


class SdbrWhatIfScenarioPayload(BaseModel):
    ScenarioType: Literal[
        "MTO_EXPEDITE",
        "RESOURCE_DOWNTIME",
        "SUPPLY_DELAY",
        "MTA_RED_REPLENISHMENT_SHOCK",
    ] = "MTO_EXPEDITE"
    ResourceID: str
    BucketDate: str
    AdditionalLoadMinutes: int = Field(default=0, ge=0)
    DowntimeMinutes: int = Field(default=0, ge=0)
    CandidateID: str | None = None
    CandidateItemID: str | None = None
    CandidateLocationID: str | None = None
    ProjectedLoadMinutes: int = Field(default=0, ge=0)
    SuggestedShockQty: float = Field(default=0, ge=0)
    DemandClass: str | None = None
    Reason: str | None = None
    UseSimioRecommended: bool = False


class DdsopFeedbackDeliveryPayload(BaseModel):
    TargetEndpoint: str
    DeliveredBy: str = "sdbr-contract-fixture"
    DeliveredAt: datetime | None = None
    TimeoutSeconds: int = Field(default=10, ge=1, le=60)


class PlanningRunEnqueuePayload(BaseModel):
    EnqueuedBy: str
    EnqueuedAt: datetime
    MaxAttempts: int = Field(default=3, ge=1, le=10)
    RetryDelaySeconds: int = Field(default=60, ge=0, le=3600)


class PlanningRunClaimPayload(BaseModel):
    WorkerID: str
    ClaimedAt: AwareDatetime
    LeaseSeconds: int = Field(default=300, ge=10, le=3600)


class PlanningRunLeaseRenewalPayload(BaseModel):
    WorkerID: str
    LeaseToken: str
    RenewedAt: AwareDatetime
    LeaseSeconds: int = Field(default=300, ge=10, le=3600)


class PlanningRunProcessQueuedPayload(BaseModel):
    WorkerID: str = "interactive-worker"
    ProcessedAt: AwareDatetime
    LeaseSeconds: int = Field(default=300, ge=10, le=3600)
    TimeLimitSeconds: int = Field(default=300, ge=1, le=3600)


class PlanningRunCancellationPayload(BaseModel):
    CancelledBy: str
    CancelledAt: datetime
    Reason: str


class PlanningRunRecoveryPayload(BaseModel):
    RecoveredBy: str
    RecoveredAt: datetime
    Reason: str
    ResetAttempts: bool = True


class ScheduleScenarioSelectionPayload(BaseModel):
    BaselineRunID: str
    CandidateRunID: str
    SelectedRunID: str
    SelectedBy: str
    SelectedAt: datetime
    Reason: str


class PlanPublicationTransitionPayload(BaseModel):
    ActorID: str
    OccurredAt: datetime
    Comment: str | None = None
    TargetSystems: list[str] = ["InternalPlanning"]


class ScheduledWorkOrderCommandPayload(BaseModel):
    Command: Literal["Lock", "Unlock", "SetPriority"]
    OrderIDs: list[str] = Field(min_length=1)
    ActorID: str
    OccurredAt: datetime
    Priority: int | None = Field(default=None, ge=1, le=999)


class PlanningRunReleaseAuthorizationPayload(BaseModel):
    ReleasedBy: str
    ReleasedAt: datetime
    OperationalStateMaxAgeMinutes: int = Field(default=60, gt=0)
    UseLatestOperationalState: bool = False
    OperationalStateSnapshotID: str | None = None


class PlannerWorkbenchImportCalculatePayload(MasterDataImportPayload):
    ProblemID: str
    ScheduleStartAt: datetime
    SolverBackendID: str = "baseline-finite"
    TimeBufferMinutes: int = 0
    GeneratedAt: datetime | None = None


class PlannerWorkbenchImportReleasePayload(PlannerWorkbenchImportCalculatePayload):
    OrderID: str
    RequestedReleaseAt: datetime


class ExecutionEventPayload(BaseModel):
    OrderID: str
    EventType: str
    EventAt: datetime
    TargetStartAt: datetime
    ExceptionCode: str | None = None
    AuthorizationID: str | None = None
    OperationID: str | None = None
    ResourceID: str | None = None
    DispatchConflictResult: str | None = None


class BufferTransactionPayload(BaseModel):
    EventType: Literal["ArrivedBuffer", "StartedOperation"]
    EventAt: datetime
    ActorID: str
    MeasureType: Literal["Quantity", "CompletionPercent", "Hours"]
    MeasureValue: float = Field(gt=0)
    ExceptionCode: str | None = None


class ReplanRequestDecisionPayload(BaseModel):
    Decision: Literal["Approve", "Reject"]
    DecidedBy: str
    DecidedAt: datetime
    Comment: str | None = None


class WipLimitPayload(BaseModel):
    ScopeID: str
    CurrentWipCount: int
    MaxWipCount: int
    OrderWipIncrement: int = 1


class MaterialAvailabilityPayload(BaseModel):
    ItemID: str
    LocationID: str
    AllocatedQty: float = 0.0
    InboundQty: float = 0.0
    InboundAvailableAt: datetime | None = None


class MaterialAvailabilityImportPayload(BaseModel):
    Rows: list[MaterialAvailabilityPayload]


class WipLimitImportPayload(BaseModel):
    Rows: list[WipLimitPayload]


class OperationalStateSnapshotPayload(BaseModel):
    SnapshotID: str
    CapturedAt: datetime
    InventoryBuffers: list[InventoryBufferPayload] = []
    MaterialAvailability: list[MaterialAvailabilityPayload] = []
    WipLimits: list[WipLimitPayload] = []


class MockOperationalStateRefreshPayload(BaseModel):
    EvaluatedAt: datetime
    SnapshotID: str | None = None
    SourceSnapshotID: str | None = None
    ActorID: str = "planner"


class ReleaseCandidatePayload(BaseModel):
    EvaluatedAt: datetime
    ReleasePolicyVersionID: str | None = None
    OperationalStateSnapshotID: str | None = None
    InventoryBuffers: list[InventoryBufferPayload] = []
    MaterialRequirements: list[MaterialRequirementPayload] = []
    WipLimits: list[WipLimitPayload] = []
    MaterialAvailability: list[MaterialAvailabilityPayload] = []


class LightMrpEvaluationPayload(BaseModel):
    EvaluatedAt: datetime
    MaterialCheckWindowMinutes: int = Field(default=0, ge=0)
    InventoryBuffers: list[InventoryBufferPayload] = []
    MaterialRequirements: list[MaterialRequirementPayload] = []
    MaterialAvailability: list[MaterialAvailabilityPayload] = []


class ReleaseAuthorizationPayload(ReleaseCandidatePayload):
    OrderID: str
    ReleasedBy: str
    ReleasedAt: datetime
    OperationalStateMaxAgeMinutes: int = Field(default=60, gt=0)
    DecisionPackageID: str | None = None


class ReleaseDecisionPackagePayload(BaseModel):
    EvaluatedAt: datetime
    OperationalStateSnapshotID: str
    MaterialRequirements: list[MaterialRequirementPayload] = []


class ExecutionVarianceReplanPayload(BaseModel):
    DetectedAt: datetime
    RequestedBy: str
    ToleranceMinutes: int = 30
    ReplanThresholdMinutes: int = 120
    ReplanCooldownMinutes: int = 60
    LastReplanAt: datetime | None = None


class IntegrationMessagePayload(BaseModel):
    ContractID: str
    MessageID: str | None = None
    MessageType: str | None = None
    SourceSystem: str | None = None
    OccurredAt: datetime | None = None
    Payload: dict[str, object] | None = None


class IntegrationReplayPayload(BaseModel):
    ActorID: str
    ReplayedAt: datetime


class TestCaseAcceptanceDecisionPayload(BaseModel):
    Decision: Literal["Confirm", "Reject"]
    ActorID: str
    DecidedAt: datetime
    Comment: str | None = None


def _client_revision_from_if_match(value: str | None) -> int | None:
    if value is None:
        return None
    stripped = value.strip().strip('"')
    if stripped == "":
        return None
    return int(stripped)


def _revision_conflict_response(
    *,
    endpoint: str,
    expected_revision: int,
    current_revision: int,
    message: str,
) -> JSONResponse:
    return JSONResponse(
        status_code=409,
        headers={"X-Workbench-Revision": str(current_revision)},
        content={
            "Endpoint": endpoint,
            "StatusCode": 409,
            "Data": {
                "Status": "StateStoreRevisionConflict",
                "ExpectedRevision": expected_revision,
                "CurrentRevision": current_revision,
                "Message": message,
            },
        },
    )


def _planning_run_authorization_error(request: Request) -> JSONResponse | None:
    actor_id = request.headers.get("x-actor-id")
    actor_role = request.headers.get("x-actor-role")
    if not actor_id or not actor_role:
        return JSONResponse(
            status_code=401,
            content={
                "Endpoint": request.url.path,
                "StatusCode": 401,
                "Data": {
                    "Status": "AuthenticationRequired",
                    "Message": "X-Actor-ID and X-Actor-Role headers are required.",
                },
            },
        )
    path = request.url.path
    if request.method == "GET":
        allowed_roles = (
            {"Planner", "Admin"}
            if path.endswith("/audit-events")
            else {"Viewer", "Planner", "Worker", "Admin"}
        )
    elif path.endswith("/jobs/claim-next") or path.endswith("/renew-lease"):
        allowed_roles = {"Worker", "Admin"}
    elif path.endswith("/execute"):
        allowed_roles = {"Planner", "Worker", "Admin"}
    else:
        allowed_roles = {"Planner", "Admin"}
    if actor_role not in allowed_roles:
        return JSONResponse(
            status_code=403,
            content={
                "Endpoint": path,
                "StatusCode": 403,
                "Data": {
                    "Status": "PermissionDenied",
                    "ActorID": actor_id,
                    "ActorRole": actor_role,
                    "Message": "Actor role is not permitted for this operation.",
                },
            },
        )
    request.state.actor_id = actor_id
    request.state.actor_role = actor_role
    return None


def _planning_run_public_record(
    planning_run: dict[str, object],
) -> dict[str, object]:
    public_record = dict(planning_run)
    public_record.pop("LeaseToken", None)
    public_record.pop("LeaseTokenHash", None)
    public_record.pop("ExecutionTokenHash", None)
    return public_record


def _operating_model_configuration_summary(
    configuration: dict[str, object],
) -> dict[str, object]:
    return {
        "OperatingModelConfigurationID": configuration.get(
            "OperatingModelConfigurationID"
        ),
        "ConfigurationVersion": configuration.get("ConfigurationVersion"),
        "Status": configuration.get("Status"),
        "ProcessingStatus": configuration.get("ProcessingStatus"),
        "UsableForPlanningRun": configuration.get("UsableForPlanningRun", False),
        "Fingerprint": configuration.get("Fingerprint"),
        "SchedulingConfigurationID": configuration.get("SchedulingConfigurationID"),
        "DDMRPConfigurationID": configuration.get("DDMRPConfigurationID"),
        "EffectiveFrom": configuration.get("EffectiveFrom"),
        "EffectiveTo": configuration.get("EffectiveTo"),
        "PendingReferences": configuration.get("PendingReferences", []),
        "ReceivedAt": configuration.get("ReceivedAt"),
    }


def _lease_token_hash(lease_token: str) -> str:
    return sha256(lease_token.encode("utf-8")).hexdigest()


class _StoreManagedRequestRejected(StateStoreManagedRequestRejected):
    def __init__(self, response: JSONResponse) -> None:
        super().__init__("Store-managed request was rejected.")
        self.response = response


def _effective_actor_id(request: Request, fallback: str) -> str:
    return str(getattr(request.state, "actor_id", fallback))


def _worker_identity_mismatch_response(
    *,
    request: Request,
    claimed_worker_id: str,
    endpoint: str,
) -> JSONResponse | None:
    actor_role = getattr(request.state, "actor_role", None)
    actor_id = getattr(request.state, "actor_id", None)
    if actor_role != "Worker" or actor_id == claimed_worker_id:
        return None
    return JSONResponse(
        status_code=403,
        content={
            "Endpoint": endpoint,
            "StatusCode": 403,
            "Data": {
                "Status": "ActorIdentityMismatch",
                "ActorID": actor_id,
                "ClaimedWorkerID": claimed_worker_id,
                "Message": "Authenticated worker cannot act as another worker.",
            },
        },
    )


def _append_planning_run_audit_event(
    *,
    audit_events: list[dict[str, object]],
    run_id: str,
    action: str,
    actor_id: str,
    occurred_at: datetime,
    details: dict[str, object] | None = None,
) -> None:
    audit_events.append(
        {
            "EventID": f"AUD-{len(audit_events) + 1:08d}",
            "RunID": run_id,
            "Action": action,
            "ActorID": actor_id,
            "OccurredAt": occurred_at.isoformat(),
            "Details": details or {},
        }
    )


def _latest_completed_run_id(
    planning_runs: dict[str, dict[str, object]],
) -> str | None:
    completed = [
        run
        for run in planning_runs.values()
        if run.get("Status") == "Completed" and isinstance(run.get("Schedule"), dict)
    ]
    if not completed:
        return None
    completed.sort(
        key=lambda run: str(
            run.get("CompletedAt")
            or (
                run.get("Schedule", {}).get("GeneratedAt")
                if isinstance(run.get("Schedule"), dict)
                else None
            )
            or run.get("RequestedAt")
            or ""
        ),
        reverse=True,
    )
    return str(completed[0].get("RunID"))


def _enrich_test_case_openability(cases: list[dict[str, object]]) -> None:
    for case in cases:
        actual = case.get("Actual") if isinstance(case.get("Actual"), dict) else {}
        status = actual.get("PlanningRunStatus") if isinstance(actual, dict) else None
        can_open = bool(status == "Completed" and actual.get("GeneratedAt") is not None)
        reason = None
        if not can_open:
            if status == "DeadLetter":
                reason = "PLANNING_RUN_DEAD_LETTER"
            elif status is None:
                reason = "PLANNING_RUN_NOT_EXECUTED"
            else:
                reason = "PLANNING_RUN_NOT_COMPLETED"
        case["ScheduleResultOpenable"] = can_open
        case["ScheduleResultUnavailableReason"] = reason


def create_app(
    state_store: WorkbenchStateStore | None = None,
    *,
    require_auth: bool = False,
    runtime_environment: RuntimeEnvironment | None = None,
    utc_now: Callable[[], datetime] | None = None,
) -> FastAPI:
    app = FastAPI(title="SDBR Planner Workbench")
    app.mount(
        "/planner/assets",
        StaticFiles(directory=Path(__file__).with_name("web")),
        name="planner-assets",
    )
    app.state.require_auth = require_auth
    active_environment = runtime_environment or resolve_runtime_environment()
    app.state.runtime_environment = active_environment
    server_utc_clock = utc_now or (lambda: datetime.now(timezone.utc))

    def server_utc_now() -> datetime:
        observed_at = server_utc_clock()
        if not isinstance(observed_at, datetime):
            raise TypeError("Server UTC clock must return a datetime.")
        if observed_at.tzinfo is None or observed_at.utcoffset() is None:
            raise ValueError("Server UTC clock must return a timezone-aware datetime.")
        return observed_at.astimezone(timezone.utc)

    active_store = state_store or WorkbenchStateStore()
    app.state.workbench_state_store = active_store
    execution_events = active_store.execution_events
    replan_requests = active_store.replan_requests
    replan_schedule_snapshots = active_store.replan_schedule_snapshots
    release_authorizations = active_store.release_authorizations
    operational_state_snapshots = active_store.operational_state_snapshots
    release_decision_packages = active_store.release_decision_packages
    dbr_release_policies = active_store.dbr_release_policies
    base_calendars = active_store.base_calendars
    resource_calendar_assignments = active_store.resource_calendar_assignments
    calendar_overrides = active_store.calendar_overrides
    scheduling_strategy_versions = active_store.scheduling_strategy_versions
    ddsop_config_inbound_messages = active_store.ddsop_config_inbound_messages
    operating_model_configurations = active_store.operating_model_configurations
    ddsop_feedback_outbound_messages = active_store.ddsop_feedback_outbound_messages
    integration_messages = active_store.integration_messages
    test_case_acceptance_decisions = active_store.test_case_acceptance_decisions
    simio_validation_runs = active_store.simio_validation_runs
    simio_template_registry = active_store.simio_template_registry
    ddmrp_decoupling_points = active_store.ddmrp_decoupling_points
    ddmrp_demand_signals = active_store.ddmrp_demand_signals
    ddmrp_open_supply = active_store.ddmrp_open_supply
    master_data_versions = active_store.master_data_versions
    planning_runs = active_store.planning_runs
    planning_demand_commitments = active_store.planning_demand_commitments
    planning_reservation_batches = active_store.planning_reservation_batches
    ccr_capacity_reservations = active_store.ccr_capacity_reservations
    material_planning_allocations = active_store.material_planning_allocations
    planning_reservation_events = active_store.planning_reservation_events
    processed_planning_event_keys = active_store.processed_planning_event_keys
    audit_events = active_store.audit_events
    order_commitment_evaluations = active_store.order_commitment_evaluations
    order_commitment_events = active_store.order_commitment_events
    if not simio_template_registry:
        simio_template_registry.update(default_simio_template_registry())
        active_store.active_simio_template_id = next(iter(simio_template_registry))
    claim_lock = Lock()
    reservation_graph_lock = RLock()
    reservation_workbench_fields = (
        "ReservationBatchID",
        "DemandCommitmentID",
        "DemandClass",
        "Status",
        "ConfirmationID",
        "ConfirmedBy",
        "ConfirmedAt",
        "CapacityReservationIDs",
        "MaterialAllocationIDs",
        "PlanningRunID",
        "LastTransitionAt",
        "EventType",
    )

    @app.middleware("http")
    async def persist_successful_writes(request, call_next):
        async def call_next_after_downstream_completion():
            response = None
            downstream_error: BaseException | None = None
            with anyio.CancelScope(shield=True):
                try:
                    response = await call_next(request)
                except BaseException as error:
                    downstream_error = error
            await anyio.lowlevel.checkpoint_if_cancelled()
            if downstream_error is not None:
                raise downstream_error
            if response is None:
                raise RuntimeError("Downstream request returned no response.")
            return response

        if require_auth and request.url.path.startswith(
            (
                "/planner/workbench/planning-runs",
                "/planner/workbench/planning-reservations",
                "/planner/workbench/order-commitments",
            )
        ):
            auth_error = _planning_run_authorization_error(request)
            if auth_error is not None:
                return auth_error
        is_write = request.method in {"POST", "PUT", "PATCH", "DELETE"}
        if not is_write:
            async with active_store.state_admission():
                response = await call_next_after_downstream_completion()
                response_revision = active_store.current_revision()
            response.headers["X-Workbench-Revision"] = str(response_revision)
            response.headers["X-SDBR-Environment"] = active_environment.environment_id
            return response

        store_managed_execution = request.url.path.startswith(
            "/planner/workbench/planning-runs/"
        ) and request.url.path.endswith(
            ("/execute", "/process-queued", "/renew-lease")
        )
        if store_managed_execution:
            response = await call_next_after_downstream_completion()
            response_revision = getattr(
                request.state,
                "store_managed_revision",
                None,
            )
            if not isinstance(response_revision, int):
                response_revision = active_store.current_revision()
            response.headers["X-Workbench-Revision"] = str(response_revision)
            response.headers["X-SDBR-Environment"] = active_environment.environment_id
            return response

        async with active_store.state_admission():
            expected_revision = _client_revision_from_if_match(
                request.headers.get("if-match")
            )
            if (
                expected_revision is not None
                and expected_revision != active_store.current_revision()
            ):
                return _revision_conflict_response(
                    endpoint=request.url.path,
                    expected_revision=expected_revision,
                    current_revision=active_store.current_revision(),
                    message="Workbench state changed; reload the latest state before retrying.",
                )
            persistence_snapshot = active_store.snapshot_state()
            try:
                response = await call_next_after_downstream_completion()
                if response.status_code < 400 or getattr(
                    request.state, "persist_workbench_write", False
                ):
                    try:
                        active_store.save()
                    except StateStoreRevisionConflict as error:
                        active_store.reload()
                        return _revision_conflict_response(
                            endpoint=request.url.path,
                            expected_revision=error.expected_revision,
                            current_revision=error.current_revision,
                            message="Workbench state changed; reload completed and the request can be retried.",
                        )
                else:
                    active_store.restore_state(persistence_snapshot)
            except BaseException:
                active_store.restore_state(persistence_snapshot)
                raise
            response.headers["X-Workbench-Revision"] = str(
                active_store.current_revision()
            )
            response.headers["X-SDBR-Environment"] = active_environment.environment_id
            return response

    def resolve_release_operational_state(
        payload: ReleaseCandidatePayload,
    ) -> tuple[
        list[InventoryBufferPolicy],
        list[MaterialAvailability],
        list[WipLimit],
        OperationalStateSnapshot | None,
    ]:
        if payload.OperationalStateSnapshotID is None:
            return (
                _inventory_buffers_from_payload(payload.InventoryBuffers),
                _material_availability_from_payload(payload.MaterialAvailability),
                _wip_limits_from_payload(payload.WipLimits),
                None,
            )
        snapshot = operational_state_snapshots.get(payload.OperationalStateSnapshotID)
        if snapshot is None:
            raise KeyError(payload.OperationalStateSnapshotID)
        return (
            snapshot.inventory_buffers,
            snapshot.material_availability,
            snapshot.wip_limits,
            snapshot,
        )

    def _order_commitment_error(
        *,
        endpoint: str,
        status_code: int,
        status: str,
        message: str,
        details: Mapping[str, object] | None = None,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status_code,
            content={
                "Endpoint": endpoint,
                "StatusCode": status_code,
                "Data": {
                    "Status": status,
                    "Message": message,
                    **deepcopy(dict(details or {})),
                },
            },
        )

    def _not_assessable_shadow(
        *,
        order: Mapping[str, object],
        evaluated_at: datetime,
        code: str,
        message: str,
    ) -> dict[str, object]:
        return {
            "Algorithm": deepcopy(SHADOW_ALGORITHM),
            "Status": "NotAssessable",
            "CapacityAssessmentCutoffAt": (
                evaluated_at.astimezone(timezone.utc).isoformat()
            ),
            "RequestedDueAt": order["RequestedDueAt"],
            "LatestCcrCompletionAt": None,
            "RequestedDateAssessment": {"Feasible": False},
            "EarliestSafeAssessment": None,
            "SelectedAssessment": None,
            "RelevantCapacityWindowKeys": [],
            "Issues": [{"Code": code, "Message": message}],
            "Summary": {
                "CcrOperationCount": 0,
                "SelectedWindowCount": 0,
                "MaximumLoadAfterPercent": None,
            },
        }

    def _prefilter_mto_capacity_rows(
        *,
        rows: list[dict[str, object]],
        allowed_keys: set[tuple[str, str, str]],
    ) -> list[dict[str, object]]:
        return [
            deepcopy(row)
            for row in rows
            if (
                str(row.get("ResourceID") or ""),
                str(row.get("WindowStartAt") or ""),
                str(row.get("WindowEndAt") or ""),
            ) in allowed_keys
        ]

    def _prefilter_mto_material_rows(
        *,
        rows: list[dict[str, object]],
        allowed_keys: set[tuple[str, str]],
    ) -> list[dict[str, object]]:
        return [
            deepcopy(row)
            for row in rows
            if (
                str(row.get("ItemID") or ""),
                str(row.get("LocationID") or ""),
            ) in allowed_keys
        ]

    def _build_order_commitment_evaluation_from_state(
        *,
        endpoint: str,
        order: Mapping[str, object],
        evaluated_at: datetime,
        check_material_availability: bool,
        material_check_skip_reason: str | None,
        requested_operational_state_snapshot_id: str | None,
    ) -> dict[str, object] | JSONResponse:
        evaluated_at = _parse_aware(evaluated_at)
        run = planning_runs.get(str(order["BaselinePlanningRunID"]))
        if run is None:
            return _order_commitment_error(
                endpoint=endpoint,
                status_code=404,
                status="PlanningRunNotFound",
                message="Baseline Planning Run was not found.",
            )
        if run.get("Status") != "Completed":
            return _order_commitment_error(
                endpoint=endpoint,
                status_code=409,
                status="PlanningRunNotCompleted",
                message="Baseline Planning Run must be completed.",
            )
        if publication_state(run) not in {"Approved", "Published"}:
            return _order_commitment_error(
                endpoint=endpoint,
                status_code=409,
                status="PlanningRunNotApprovedOrPublished",
                message="Baseline plan must be approved or published.",
            )
        schedule = run.get("Schedule")
        if not isinstance(schedule, dict):
            return _order_commitment_error(
                endpoint=endpoint,
                status_code=409,
                status="PlanningRunScheduleMissing",
                message="Baseline schedule evidence is missing.",
            )
        master = master_data_versions.get(str(run.get("MasterDataVersionID")))
        if not isinstance(master, dict):
            return _order_commitment_error(
                endpoint=endpoint,
                status_code=404,
                status="MasterDataVersionNotFound",
                message="Baseline master-data version was not found.",
            )

        orchestration_issue: tuple[str, str] | None = None
        resources: list[Resource] = []
        routings: list[Routing] = []
        routing: Routing | None = None
        setup_transitions: list[SetupTransition] = []
        capacity_buckets = []
        timezone_name = master.get("CalendarTimezone")
        if not isinstance(timezone_name, str) or not timezone_name.strip():
            orchestration_issue = (
                "CALENDAR_TIMEZONE_REQUIRED",
                "A calendar timezone is required for MTO shadow capacity.",
            )
        try:
            resource_rows = master.get("Resources")
            routing_rows = master.get("Routings")
            if not isinstance(resource_rows, list) or not isinstance(
                routing_rows, list
            ):
                raise ValueError("Master resource/routing rows must be lists.")
            resources = _resources_from_payload([
                ResourcePayload(**row) for row in resource_rows
            ])
            resources = apply_base_calendar_assignments(
                resources=resources,
                calendars=run.get("FrozenBaseCalendars") or [],
                assignments=(
                    run.get("FrozenResourceCalendarAssignments") or []
                ),
            ).resources
            resources = apply_calendar_overrides(
                resources=resources,
                overrides=run.get("FrozenCalendarOverrides") or [],
            ).resources
            routings = _routings_from_payload([
                RoutingPayload(**row) for row in routing_rows
            ])
            setup_rows = run.get("SetupTransitions") or []
            if not isinstance(setup_rows, list):
                raise ValueError("SetupTransitions must be a list.")
            setup_transitions = _setup_transitions_from_payload([
                SetupTransitionPayload(**row) for row in setup_rows
            ])
        except (KeyError, TypeError, ValueError) as error:
            orchestration_issue = (
                "MASTER_ROUTE_CALENDAR_EVIDENCE_INVALID",
                str(error),
            )

        if orchestration_issue is None:
            routing_matches = [
                row
                for row in routings
                if row.product_id == order["ProductID"]
                and row.routing_id == order["RoutingID"]
                and row.is_primary is True
            ]
            if len(routing_matches) != 1:
                orchestration_issue = (
                    "ROUTING_NOT_PRIMARY_OR_AMBIGUOUS",
                    "Exactly one matching primary route is required.",
                )
            else:
                routing = routing_matches[0]

        resources_by_id = {row.resource_id: row for row in resources}
        if orchestration_issue is None and routing is not None:
            missing_resource_ids = sorted({
                operation.resource_id
                for operation in routing.operations
                if operation.resource_id not in resources_by_id
            })
            if missing_resource_ids:
                orchestration_issue = (
                    "ROUTE_RESOURCE_NOT_FOUND",
                    "Route references missing resources: "
                    + ", ".join(missing_resource_ids),
                )

        ccr_resource_ids: set[str] = set()
        if orchestration_issue is None and routing is not None:
            ccr_resource_ids = {
                operation.resource_id
                for operation in routing.operations
                if resources_by_id[operation.resource_id].is_constraint
            }
            if not ccr_resource_ids:
                orchestration_issue = (
                    "CCR_OPERATION_NOT_FOUND",
                    "The primary route has no CCR operation.",
                )

        if orchestration_issue is None:
            try:
                capacity_buckets = build_capacity_buckets_from_resources(
                    resources,
                    tzinfo=ZoneInfo(str(timezone_name)),
                )
            except (KeyError, TypeError, ValueError) as error:
                orchestration_issue = (
                    "CALENDAR_CAPACITY_EVIDENCE_INVALID",
                    str(error),
                )

        frozen_release_policy = _release_policy_for_evaluation(
            planning_run=run,
            requested_policy_id=None,
            dbr_release_policies=dbr_release_policies,
        )
        material_window = release_policy_settings(
            frozen_release_policy
        ).material_lookahead_minutes
        material_input_keys = {
            (str(row["ItemID"]), str(row["LocationID"]))
            for row in order["MaterialRequirements"]
        }
        capacity_input_keys = {
            (
                bucket.resource_id,
                bucket.bucket_start.astimezone(timezone.utc).isoformat(),
                bucket.bucket_end.astimezone(timezone.utc).isoformat(),
            )
            for bucket in capacity_buckets
            if bucket.resource_id in ccr_resource_ids
        }
        relevant_capacity_rows = _prefilter_mto_capacity_rows(
            rows=list(ccr_capacity_reservations.values()),
            allowed_keys=capacity_input_keys,
        )
        relevant_material_rows = _prefilter_mto_material_rows(
            rows=list(material_planning_allocations.values()),
            allowed_keys=material_input_keys,
        )
        raw_gantt_rows = schedule.get("GanttRows", [])
        if not isinstance(raw_gantt_rows, list):
            orchestration_issue = (
                "SCHEDULE_GANTT_EVIDENCE_INVALID",
                "Schedule GanttRows must be a list.",
            )
            raw_gantt_rows = []
        relevant_gantt_rows = [
            deepcopy(row)
            for row in raw_gantt_rows
            if isinstance(row, Mapping)
            and str(row.get("ResourceID") or "") in ccr_resource_ids
        ]

        try:
            selection = select_order_commitment_operational_snapshot(
                snapshots=operational_state_snapshots,
                evaluated_at=evaluated_at,
                requested_snapshot_id=(
                    requested_operational_state_snapshot_id
                ),
            )
        except OrderCommitmentSnapshotNotFound as error:
            return _order_commitment_error(
                endpoint=endpoint,
                status_code=404,
                status=error.status,
                message=str(error),
                details={"OperationalStateSnapshotID": error.snapshot_id},
            )

        shadow = (
            _not_assessable_shadow(
                order=order,
                evaluated_at=evaluated_at,
                code=orchestration_issue[0],
                message=orchestration_issue[1],
            )
            if orchestration_issue is not None
            else evaluate_ccr_shadow_schedule(
                order_id=str(order["PlanningOrderID"]),
                quantity=float(order["Quantity"]),
                routing=routing,
                resources=resources,
                capacity_buckets=capacity_buckets,
                setup_transitions=setup_transitions,
                gantt_rows=relevant_gantt_rows,
                active_capacity_reservations=relevant_capacity_rows,
                requested_due_at=_parse_aware(order["RequestedDueAt"]),
                evaluated_at=evaluated_at,
                downstream_protection_minutes=int(
                    run.get("TimeBufferMinutes", 0)
                ),
                protection_threshold_percent=80.0,
            )
        )
        try:
            material = evaluate_mto_material_availability(
                order=order,
                snapshot_selection=selection,
                active_material_allocations=relevant_material_rows,
                current_demand_commitment_id=(
                    candidate_demand_commitment_id(order)
                ),
                evaluated_at=evaluated_at,
                material_check_window_minutes=material_window,
                check_material_availability=check_material_availability,
                skip_reason=material_check_skip_reason,
            )
        except OrderCommitmentConflict as error:
            return _order_commitment_error(
                endpoint=endpoint,
                status_code=409,
                status=error.status,
                message=str(error),
            )

        route_projection = (
            None
            if routing is None
            else {
                "ProductID": routing.product_id,
                "RoutingID": routing.routing_id,
                "IsPrimary": routing.is_primary,
                "Operations": [
                    {
                        "OperationID": row.operation_id,
                        "ResourceID": row.resource_id,
                        "DurationMinutes": row.duration_minutes,
                        "Sequence": row.sequence,
                        "AlternateResourceIDs": sorted(
                            row.alternate_resource_ids or []
                        ),
                        "SetupFamily": row.setup_family,
                    }
                    for row in sorted(
                        routing.operations, key=lambda item: item.sequence
                    )
                ],
            }
        )
        calendar_projection = {
            "CalendarTimezone": timezone_name,
            "CapacityBuckets": [
                {
                    "ResourceID": row.resource_id,
                    "WindowStartAt": row.bucket_start.astimezone(
                        timezone.utc
                    ).isoformat(),
                    "WindowEndAt": row.bucket_end.astimezone(
                        timezone.utc
                    ).isoformat(),
                    "CapacityMinutes": row.capacity_minutes,
                }
                for row in sorted(
                    capacity_buckets,
                    key=lambda item: (
                        item.resource_id,
                        item.bucket_start,
                        item.bucket_end,
                    ),
                )
            ],
            "FrozenBaseCalendars": deepcopy(
                run.get("FrozenBaseCalendars") or []
            ),
            "FrozenResourceCalendarAssignments": deepcopy(
                run.get("FrozenResourceCalendarAssignments") or []
            ),
            "FrozenCalendarOverrides": deepcopy(
                run.get("FrozenCalendarOverrides") or []
            ),
        }
        selected_snapshot = selection["OperationalStateSnapshot"]
        inventory_rows = (
            list(selected_snapshot.inventory_buffers)
            if isinstance(selected_snapshot, OperationalStateSnapshot)
            else []
        )
        availability_rows = (
            list(selected_snapshot.material_availability)
            if isinstance(selected_snapshot, OperationalStateSnapshot)
            else []
        )
        material_cutoff_value = material["MaterialEligibilityCutoffAt"]
        try:
            basis = build_order_commitment_basis(
                baseline_planning_run_id=str(run["RunID"]),
                baseline_operational_state_snapshot_id=(
                    str(run["OperationalStateSnapshotID"])
                    if run.get("OperationalStateSnapshotID") is not None
                    else None
                ),
                baseline_schedule_fingerprint=(
                    planning_schedule_fingerprint(run)
                    or canonical_fingerprint(schedule)
                ),
                master_data_version_id=str(master["VersionID"]),
                operating_model_configuration_id=run.get(
                    "OperatingModelConfigurationID"
                ),
                operating_model_fingerprint=run.get(
                    "OperatingModelFingerprint"
                ),
                scheduling_configuration_id=run.get(
                    "SchedulingConfigurationID"
                ),
                ddmrp_configuration_id=run.get("DDMRPConfigurationID"),
                release_policy_version_id=run.get("ReleasePolicyVersionID"),
                frozen_release_policy_fingerprint=canonical_fingerprint(
                    release_policy_evidence(frozen_release_policy)
                ),
                routing_fingerprint=canonical_fingerprint(route_projection),
                calendar_fingerprint=canonical_fingerprint(
                    calendar_projection
                ),
                time_buffer_minutes=int(run.get("TimeBufferMinutes", 0)),
                material_check_window_minutes=material_window,
                capacity_assessment_cutoff_at=_parse_aware(
                    shadow["CapacityAssessmentCutoffAt"]
                ),
                material_eligibility_cutoff_at=(
                    _parse_aware(material_cutoff_value)
                    if material_cutoff_value is not None
                    else None
                ),
                check_material_availability=check_material_availability,
                material_skip_reason=material_check_skip_reason,
                snapshot_selection=selection,
                relevant_capacity_window_keys=[
                    tuple(row) for row in shadow["RelevantCapacityWindowKeys"]
                ],
                capacity_ledger_rows=relevant_capacity_rows,
                relevant_material_keys=sorted(material_input_keys),
                inventory_buffer_rows=inventory_rows,
                material_availability_rows=availability_rows,
                material_ledger_rows=relevant_material_rows,
            )
            return create_order_commitment_evaluation(
                order=order,
                shadow_schedule=shadow,
                material_assessment=material,
                basis=basis,
                protection_policy=REFERENCE_CCR_PROTECTION_POLICY,
                evaluated_at=evaluated_at,
            )
        except OrderCommitmentConflict as error:
            return _order_commitment_error(
                endpoint=endpoint,
                status_code=409,
                status=error.status,
                message=str(error),
            )

    @app.get("/planner/workbench/demo")
    def planner_workbench_demo(solver_backend_id: str = "baseline-finite") -> dict[str, object]:
        return get_planner_workbench_demo_payload(solver_backend_id=solver_backend_id)

    @app.post("/planner/workbench/calculate")
    def planner_workbench_calculate(payload: PlannerWorkbenchCalculatePayload):
        objective = _objective_for_strategy_id(
            strategy_id=payload.ObjectiveStrategyID,
            scheduling_strategy_versions=scheduling_strategy_versions,
        )
        if objective is None:
            return _objective_strategy_not_found_response(
                endpoint="/planner/workbench/calculate",
                strategy_id=payload.ObjectiveStrategyID,
            )
        validation = _validate_master_data_payload(payload)
        if not validation.is_valid:
            return JSONResponse(
                status_code=409,
                content={
                    "Endpoint": "/planner/workbench/calculate",
                    "StatusCode": 409,
                    "Data": {
                        "Validation": _master_data_validation_to_dict(validation),
                    },
                },
            )
        data = _calculate_workbench_data(payload, validation, objective=objective)
        return {
            "Endpoint": "/planner/workbench/calculate",
            "StatusCode": 200,
            "Data": data,
        }

    @app.post("/planner/workbench/master-data/validate")
    def planner_workbench_master_data_validate(
        payload: PlannerWorkbenchCalculatePayload,
    ) -> dict[str, object]:
        validation = _validate_master_data_payload(payload)
        return {
            "Endpoint": "/planner/workbench/master-data/validate",
            "StatusCode": 200,
            "Data": _master_data_validation_to_dict(validation),
        }

    @app.post("/planner/workbench/resources/import")
    def planner_workbench_resources_import(payload: ResourceImportPayload) -> dict[str, object]:
        resources = _resources_from_import_payload(payload)
        validation = validate_master_data(
            resources=resources,
            routings=[],
            orders=[],
            inventory_buffers=[],
            material_requirements=[],
            calendar_timezone=payload.CalendarTimezone,
        )
        return {
            "Endpoint": "/planner/workbench/resources/import",
            "StatusCode": 200,
            "Data": {
                "Resources": _resources_to_payload_dict(resources),
                "Validation": _master_data_validation_to_dict(validation),
            },
        }

    @app.post("/planner/workbench/inventory-buffers/import")
    def planner_workbench_inventory_buffers_import(
        payload: InventoryBufferImportPayload,
    ) -> dict[str, object]:
        inventory_buffers = import_inventory_buffers_from_rows(
            _inventory_buffer_import_rows_from_payload(payload.Rows)
        )
        validation = validate_master_data(
            resources=_resources_from_payload(payload.Resources),
            routings=[],
            orders=[],
            inventory_buffers=inventory_buffers,
            material_requirements=[],
            calendar_timezone=payload.CalendarTimezone,
        )
        return {
            "Endpoint": "/planner/workbench/inventory-buffers/import",
            "StatusCode": 200,
            "Data": {
                "InventoryBuffers": _inventory_buffers_to_payload_dict(inventory_buffers),
                "Validation": _master_data_validation_to_dict(validation),
            },
        }

    @app.post("/planner/workbench/material-availability/import")
    def planner_workbench_material_availability_import(
        payload: MaterialAvailabilityImportPayload,
    ):
        endpoint = "/planner/workbench/material-availability/import"
        try:
            material_availability = import_material_availability_from_rows(
                _material_availability_import_rows_from_payload(payload.Rows)
            )
        except ValueError as error:
            return JSONResponse(
                status_code=409,
                content={
                    "Endpoint": endpoint,
                    "StatusCode": 409,
                    "Data": {
                        "Status": "MaterialAvailabilityInvalid",
                        "Message": str(error),
                    },
                },
            )
        return {
            "Endpoint": endpoint,
            "StatusCode": 200,
            "Data": {
                "MaterialAvailability": _material_availability_to_payload_dict(
                    material_availability
                ),
            },
        }

    @app.post("/planner/workbench/light-mrp/evaluate")
    def planner_workbench_light_mrp_evaluate(
        payload: LightMrpEvaluationPayload,
    ) -> dict[str, object]:
        return {
            "Endpoint": "/planner/workbench/light-mrp/evaluate",
            "StatusCode": 200,
            "Data": evaluate_light_mrp(
                material_requirements=_material_requirements_from_payload(
                    payload.MaterialRequirements
                ),
                inventory_buffers=_inventory_buffers_from_payload(
                    payload.InventoryBuffers
                ),
                material_availability=_material_availability_from_payload(
                    payload.MaterialAvailability
                ),
                evaluated_at=payload.EvaluatedAt,
                material_check_window_minutes=payload.MaterialCheckWindowMinutes,
            ),
        }

    @app.post("/planner/workbench/ddmrp/decoupling-points/import")
    def planner_workbench_ddmrp_decoupling_points_import(
        payload: DdmrpDecouplingPointImportPayload,
    ) -> dict[str, object]:
        rows = _ddmrp_decoupling_points_to_payload_dict(
            _ddmrp_decoupling_points_from_payload(payload.Rows)
        )
        ddmrp_decoupling_points.clear()
        ddmrp_decoupling_points.extend(rows)
        return {
            "Endpoint": "/planner/workbench/ddmrp/decoupling-points/import",
            "StatusCode": 200,
            "Data": {"DecouplingPoints": rows},
        }

    @app.post("/planner/workbench/ddmrp/demand-signals/import")
    def planner_workbench_ddmrp_demand_signals_import(
        payload: DdmrpDemandSignalImportPayload,
    ) -> dict[str, object]:
        rows = _ddmrp_demand_signals_to_payload_dict(
            _ddmrp_demand_signals_from_payload(payload.Rows)
        )
        ddmrp_demand_signals.clear()
        ddmrp_demand_signals.extend(rows)
        return {
            "Endpoint": "/planner/workbench/ddmrp/demand-signals/import",
            "StatusCode": 200,
            "Data": {"DemandSignals": rows},
        }

    @app.post("/planner/workbench/ddmrp/open-supply/import")
    def planner_workbench_ddmrp_open_supply_import(
        payload: DdmrpOpenSupplyImportPayload,
    ) -> dict[str, object]:
        rows = _ddmrp_open_supply_to_payload_dict(
            _ddmrp_open_supply_from_payload(payload.Rows)
        )
        ddmrp_open_supply.clear()
        ddmrp_open_supply.extend(rows)
        return {
            "Endpoint": "/planner/workbench/ddmrp/open-supply/import",
            "StatusCode": 200,
            "Data": {"OpenSupply": rows},
        }

    @app.post("/planner/workbench/ddmrp/net-flow/evaluate")
    def planner_workbench_ddmrp_net_flow_evaluate(
        payload: DdmrpNetFlowEvaluationPayload,
    ):
        endpoint = "/planner/workbench/ddmrp/net-flow/evaluate"
        try:
            data = evaluate_ddmrp_net_flow(
                decoupling_points=_ddmrp_decoupling_points_from_payload(
                    payload.DecouplingPoints
                ),
                stock_buffers=_inventory_buffers_from_payload(payload.StockBuffers),
                demand_signals=_ddmrp_demand_signals_from_payload(
                    payload.DemandSignals
                ),
                open_supply=_ddmrp_open_supply_from_payload(payload.OpenSupply),
                evaluated_at=payload.EvaluatedAt,
            )
        except ValueError as error:
            return JSONResponse(
                status_code=409,
                content={
                    "Endpoint": endpoint,
                    "StatusCode": 409,
                    "Data": {"Status": "DdmrpNetFlowInvalid", "Message": str(error)},
                },
            )
        return {"Endpoint": endpoint, "StatusCode": 200, "Data": data}

    @app.get("/planner/workbench/ddmrp/status")
    def planner_workbench_ddmrp_status(
        evaluated_at: datetime | None = Query(default=None, alias="EvaluatedAt"),
    ):
        endpoint = "/planner/workbench/ddmrp/status"
        effective_evaluated_at = evaluated_at or datetime.now(timezone.utc)
        master_data = _latest_ddmrp_master_data_version(master_data_versions)
        if master_data is not None:
            points_payload = master_data.get("DdmrpDecouplingPoints", [])
            demand_payload = master_data.get("DdmrpDemandSignals", [])
            supply_payload = master_data.get("DdmrpOpenSupply", [])
            stock_payload = master_data.get("InventoryBuffers", [])
            source = {
                "SourceType": "MasterDataVersion",
                "VersionID": master_data.get("VersionID"),
                "CapturedAt": master_data.get("CapturedAt"),
            }
        else:
            points_payload = ddmrp_decoupling_points
            demand_payload = ddmrp_demand_signals
            supply_payload = ddmrp_open_supply
            stock_payload = []
            source = {"SourceType": "ImportedRuntimeLedger", "VersionID": None}
        try:
            data = evaluate_ddmrp_net_flow(
                decoupling_points=_ddmrp_decoupling_points_from_dicts(points_payload),
                stock_buffers=_inventory_buffers_from_dicts(stock_payload),
                demand_signals=_ddmrp_demand_signals_from_dicts(demand_payload),
                open_supply=_ddmrp_open_supply_from_dicts(supply_payload),
                evaluated_at=effective_evaluated_at,
            )
        except ValueError as error:
            return JSONResponse(
                status_code=409,
                content={
                    "Endpoint": endpoint,
                    "StatusCode": 409,
                    "Data": {"Status": "DdmrpStatusInvalid", "Message": str(error)},
                },
            )
        data["Source"] = source
        return {"Endpoint": endpoint, "StatusCode": 200, "Data": data}

    @app.post("/planner/workbench/wip-limits/import")
    def planner_workbench_wip_limits_import(payload: WipLimitImportPayload):
        endpoint = "/planner/workbench/wip-limits/import"
        try:
            wip_limits = import_wip_limits_from_rows(
                _wip_limit_import_rows_from_payload(payload.Rows)
            )
        except ValueError as error:
            return JSONResponse(
                status_code=409,
                content={
                    "Endpoint": endpoint,
                    "StatusCode": 409,
                    "Data": {
                        "Status": "WipLimitsInvalid",
                        "Message": str(error),
                    },
                },
            )
        return {
            "Endpoint": endpoint,
            "StatusCode": 200,
            "Data": {
                "WipLimits": _wip_limits_to_payload_dict(wip_limits),
            },
        }

    @app.post("/planner/workbench/operational-state/snapshots")
    def planner_workbench_operational_state_snapshot(
        payload: OperationalStateSnapshotPayload,
    ):
        endpoint = "/planner/workbench/operational-state/snapshots"
        if payload.SnapshotID in operational_state_snapshots:
            return JSONResponse(
                status_code=409,
                content={
                    "Endpoint": endpoint,
                    "StatusCode": 409,
                    "Data": {
                        "SnapshotID": payload.SnapshotID,
                        "Status": "OperationalStateSnapshotConflict",
                        "Message": f"Operational state snapshot {payload.SnapshotID} already exists.",
                    },
                },
            )
        try:
            snapshot = create_operational_state_snapshot(
                snapshot_id=payload.SnapshotID,
                captured_at=payload.CapturedAt,
                inventory_buffers=_inventory_buffers_from_payload(
                    payload.InventoryBuffers
                ),
                material_availability=import_material_availability_from_rows(
                    _material_availability_import_rows_from_payload(
                        payload.MaterialAvailability
                    )
                ),
                wip_limits=import_wip_limits_from_rows(
                    _wip_limit_import_rows_from_payload(payload.WipLimits)
                ),
            )
        except ValueError as error:
            return JSONResponse(
                status_code=409,
                content={
                    "Endpoint": endpoint,
                    "StatusCode": 409,
                    "Data": {
                        "SnapshotID": payload.SnapshotID,
                        "Status": "OperationalStateSnapshotInvalid",
                        "Message": str(error),
                    },
                },
            )
        operational_state_snapshots[snapshot.snapshot_id] = snapshot
        return {
            "Endpoint": endpoint,
            "StatusCode": 200,
            "Data": {
                "Snapshot": _operational_state_snapshot_to_dict(snapshot),
            },
        }

    @app.get("/planner/workbench/operational-state/snapshots/{snapshot_id}")
    def planner_workbench_operational_state_snapshot_get(snapshot_id: str):
        endpoint = f"/planner/workbench/operational-state/snapshots/{snapshot_id}"
        snapshot = operational_state_snapshots.get(snapshot_id)
        if snapshot is None:
            return JSONResponse(
                status_code=404,
                content={
                    "Endpoint": endpoint,
                    "StatusCode": 404,
                    "Data": {
                        "SnapshotID": snapshot_id,
                        "Status": "OperationalStateSnapshotNotFound",
                        "Message": f"Operational state snapshot {snapshot_id} was not found.",
                    },
                },
            )
        return {
            "Endpoint": endpoint,
            "StatusCode": 200,
            "Data": {
                "Snapshot": _operational_state_snapshot_to_dict(snapshot),
            },
        }

    @app.get("/planner/workbench/state-store/health")
    def planner_workbench_state_store_health() -> dict[str, object]:
        return {
            "Endpoint": "/planner/workbench/state-store/health",
            "StatusCode": 200,
            "Data": {
                **active_store.health(),
                "Environment": active_environment.to_dict(),
            },
        }

    @app.get("/planner/workbench/environment")
    def planner_workbench_environment() -> dict[str, object]:
        return {
            "Endpoint": "/planner/workbench/environment",
            "StatusCode": 200,
            "Data": active_environment.to_dict(),
        }

    @app.post("/planner/workbench/ddsop/config-inbound")
    def planner_workbench_ddsop_config_inbound(payload: dict[str, object]):
        endpoint = "/planner/workbench/ddsop/config-inbound"
        duplicate_record = next(
            (
                record
                for record in ddsop_config_inbound_messages
                if record.get("IdempotencyKey") == payload.get("IdempotencyKey")
            ),
            None,
        )
        result = process_ddsop_config_message(
            payload,
            received_at=datetime.now(timezone.utc),
            duplicate_record=duplicate_record,
            release_policy_ids=set(dbr_release_policies.keys()),
            calendar_ids=set(base_calendars.keys()),
            scheduling_strategy_ids=set(scheduling_strategy_versions.keys()),
            planning_priority_policy_ids={
                "DDMRP-PRIORITY-RED-YELLOW-GREEN-001"
            },
            scheduling_priority_classes={"Standard"},
        )
        ddsop_config_inbound_messages.append(result.inbound_message_record)
        if result.configuration_record is not None:
            operating_model_configurations[
                str(result.configuration_record["OperatingModelConfigurationID"])
            ] = result.configuration_record
        return {
            "Endpoint": endpoint,
            "StatusCode": 200,
            "Data": {"Ack": result.ack},
        }

    @app.get("/planner/workbench/ddsop/configurations")
    def planner_workbench_ddsop_configurations() -> dict[str, object]:
        return {
            "Endpoint": "/planner/workbench/ddsop/configurations",
            "StatusCode": 200,
            "Data": {
                "Configurations": [
                    _operating_model_configuration_summary(record)
                    for record in operating_model_configurations.values()
                ],
                "InboundMessageCount": len(ddsop_config_inbound_messages),
            },
        }

    @app.get("/planner/workbench/ddsop/feedback/planning-runs/{run_id}")
    def planner_workbench_ddsop_planning_run_feedback(run_id: str):
        endpoint = f"/planner/workbench/ddsop/feedback/planning-runs/{run_id}"
        planning_run = planning_runs.get(run_id)
        if planning_run is None:
            return _planning_run_not_found(endpoint=endpoint, run_id=run_id)
        try:
            message = build_planning_run_feedback_message(
                planning_run,
                generated_at=datetime.now(timezone.utc),
                release_authorizations=release_authorizations,
            )
        except ValueError as error:
            return JSONResponse(
                status_code=409,
                content={
                    "Endpoint": endpoint,
                    "StatusCode": 409,
                    "Data": {
                        "RunID": run_id,
                        "Status": "OperatingModelConfigurationNotFrozen",
                        "Message": str(error),
                    },
                },
            )
        return {
            "Endpoint": endpoint,
            "StatusCode": 200,
            "Data": {"Message": message},
        }

    @app.get("/planner/workbench/ddsop/feedback/variance-analysis/{run_id}")
    def planner_workbench_ddsop_variance_feedback(run_id: str):
        endpoint = f"/planner/workbench/ddsop/feedback/variance-analysis/{run_id}"
        planning_run = planning_runs.get(run_id)
        if planning_run is None:
            return _planning_run_not_found(endpoint=endpoint, run_id=run_id)
        try:
            message = build_variance_analysis_feedback_message(
                planning_run,
                generated_at=datetime.now(timezone.utc),
            )
        except ValueError as error:
            return JSONResponse(
                status_code=409,
                content={
                    "Endpoint": endpoint,
                    "StatusCode": 409,
                    "Data": {
                        "RunID": run_id,
                        "Status": "OperatingModelConfigurationNotFrozen",
                        "Message": str(error),
                    },
                },
            )
        return {
            "Endpoint": endpoint,
            "StatusCode": 200,
            "Data": {"Message": message},
        }

    @app.post("/planner/workbench/ddsop/feedback/runs/{run_id}/deliver")
    def planner_workbench_ddsop_feedback_deliver(
        run_id: str,
        payload: DdsopFeedbackDeliveryPayload,
    ):
        endpoint = f"/planner/workbench/ddsop/feedback/runs/{run_id}/deliver"
        planning_run = planning_runs.get(run_id)
        if planning_run is None:
            return _planning_run_not_found(endpoint=endpoint, run_id=run_id)
        delivered_at = payload.DeliveredAt or datetime.now(timezone.utc)
        try:
            messages = [
                build_planning_run_feedback_message(
                    planning_run,
                    generated_at=delivered_at,
                    release_authorizations=release_authorizations,
                ),
                build_variance_analysis_feedback_message(
                    planning_run,
                    generated_at=delivered_at,
                ),
            ]
        except ValueError as error:
            return JSONResponse(
                status_code=409,
                content={
                    "Endpoint": endpoint,
                    "StatusCode": 409,
                    "Data": {
                        "RunID": run_id,
                        "Status": "OperatingModelConfigurationNotFrozen",
                        "Message": str(error),
                    },
                },
            )
        delivery_records = [
            deliver_ddsop_feedback_message(
                message,
                target_endpoint=payload.TargetEndpoint,
                attempted_at=delivered_at,
                timeout_seconds=payload.TimeoutSeconds,
            )
            | {"DeliveredBy": payload.DeliveredBy}
            for message in messages
        ]
        ddsop_feedback_outbound_messages.extend(delivery_records)
        return {
            "Endpoint": endpoint,
            "StatusCode": 200,
            "Data": {
                "RunID": run_id,
                "TargetEndpoint": payload.TargetEndpoint,
                "DeliveryRecords": delivery_records,
            },
        }

    @app.get("/planner/workbench/ddsop/feedback/delivery-ledger")
    def planner_workbench_ddsop_feedback_delivery_ledger() -> dict[str, object]:
        return {
            "Endpoint": "/planner/workbench/ddsop/feedback/delivery-ledger",
            "StatusCode": 200,
            "Data": {
                "DeliveryRecords": ddsop_feedback_outbound_messages,
                "RecordCount": len(ddsop_feedback_outbound_messages),
            },
        }

    @app.get("/planner/workbench/public-demo/golden-loop")
    def planner_workbench_public_demo_golden_loop() -> dict[str, object]:
        return {
            "Endpoint": "/planner/workbench/public-demo/golden-loop",
            "StatusCode": 200,
            "Data": get_public_demo_golden_loop_status(),
        }

    @app.post("/planner/workbench/public-demo/golden-loop/run")
    def planner_workbench_public_demo_golden_loop_run() -> dict[str, object]:
        result = run_public_demo_golden_loop()
        return {
            "Endpoint": "/planner/workbench/public-demo/golden-loop/run",
            "StatusCode": 200,
            "Data": result,
        }

    @app.get("/planner/workbench/public-demo/adventureworks-scheduling-adapter")
    def planner_workbench_public_demo_adventureworks_adapter() -> dict[str, object]:
        return {
            "Endpoint": "/planner/workbench/public-demo/adventureworks-scheduling-adapter",
            "StatusCode": 200,
            "Data": build_adventureworks_scheduling_adapter_status(),
        }

    @app.post("/planner/workbench/public-demo/adventureworks-scheduling-adapter/run")
    def planner_workbench_public_demo_adventureworks_adapter_run() -> dict[str, object]:
        return {
            "Endpoint": "/planner/workbench/public-demo/adventureworks-scheduling-adapter/run",
            "StatusCode": 200,
            "Data": build_adventureworks_scheduling_adapter_status(write_artifacts=True),
        }

    @app.get("/planner/workbench/public-demo/adventureworks-product-demo-profile")
    def planner_workbench_public_demo_adventureworks_product_profile() -> dict[str, object]:
        return {
            "Endpoint": "/planner/workbench/public-demo/adventureworks-product-demo-profile",
            "StatusCode": 200,
            "Data": build_adventureworks_product_demo_profile_status(),
        }

    @app.get("/planner/workbench/test-data/cases")
    def planner_workbench_test_data_cases() -> dict[str, object]:
        return {
            "Endpoint": "/planner/workbench/test-data/cases",
            "StatusCode": 200,
            "Data": {
                **test_case_catalog_payload(),
                "Environment": active_environment.to_dict(),
            },
        }

    @app.get("/planner/workbench/test-data/acceptance")
    def planner_workbench_test_data_acceptance(
        evaluated_at: datetime = DEFAULT_CASE_EVALUATED_AT,
    ) -> dict[str, object]:
        workbench = build_test_case_acceptance_workbench(
            planning_runs=planning_runs,
            master_data_versions=master_data_versions,
            operational_state_snapshots=operational_state_snapshots,
            release_authorizations=release_authorizations,
            acceptance_decisions=test_case_acceptance_decisions,
            evaluated_at=evaluated_at,
        )
        _enrich_test_case_openability(workbench["Cases"])
        return {
            "Endpoint": "/planner/workbench/test-data/acceptance",
            "StatusCode": 200,
            "Data": {
                **workbench,
                "Environment": active_environment.to_dict(),
            },
        }

    @app.post("/planner/workbench/test-data/acceptance/reset")
    def planner_workbench_test_data_acceptance_reset_all() -> dict[str, object]:
        summary = seed_baseline_test_data(active_store)
        return {
            "Endpoint": "/planner/workbench/test-data/acceptance/reset",
            "StatusCode": 200,
            "Data": {
                "Status": "Reset",
                "Scope": "AllCases",
                "Summary": summary.to_dict(),
            },
        }

    @app.post("/planner/workbench/test-data/order-commitment/reset")
    def planner_workbench_order_commitment_test_data_reset():
        endpoint = "/planner/workbench/test-data/order-commitment/reset"
        if active_environment.is_production:
            return JSONResponse(
                status_code=409,
                content={
                    "Endpoint": endpoint,
                    "StatusCode": 409,
                    "Data": {"Status": "TestDataResetNotAllowed"},
                },
            )
        seed_baseline_test_data(active_store)
        fixture = seed_mto_order_commitment_fixture(
            active_store,
            captured_at=server_utc_now(),
        )
        return {
            "Endpoint": endpoint,
            "StatusCode": 200,
            "Data": {"Status": "Reset", **fixture},
        }

    @app.post("/planner/workbench/test-data/acceptance/{case_id}/reset")
    def planner_workbench_test_data_acceptance_reset_case(case_id: str):
        endpoint = f"/planner/workbench/test-data/acceptance/{case_id}/reset"
        try:
            result = reset_test_case_state(active_store, case_id=case_id)
        except KeyError:
            return JSONResponse(
                status_code=404,
                content={
                    "Endpoint": endpoint,
                    "StatusCode": 404,
                    "Data": {
                        "CaseID": case_id,
                        "Status": "TestCaseNotFound",
                        "Message": f"Test case {case_id} was not found.",
                    },
                },
            )
        return {
            "Endpoint": endpoint,
            "StatusCode": 200,
            "Data": result,
        }

    @app.get("/planner/workbench/test-data/acceptance/decisions")
    def planner_workbench_test_data_acceptance_decisions() -> dict[str, object]:
        return {
            "Endpoint": "/planner/workbench/test-data/acceptance/decisions",
            "StatusCode": 200,
            "Data": {
                "Count": len(test_case_acceptance_decisions),
                "Decisions": sorted(
                    test_case_acceptance_decisions,
                    key=lambda item: str(item.get("DecidedAt", "")),
                    reverse=True,
                ),
            },
        }

    @app.post("/planner/workbench/test-data/acceptance/{case_id}/decision")
    def planner_workbench_test_data_acceptance_decision_create(
        case_id: str,
        payload: TestCaseAcceptanceDecisionPayload,
        evaluated_at: datetime = DEFAULT_CASE_EVALUATED_AT,
    ):
        endpoint = f"/planner/workbench/test-data/acceptance/{case_id}/decision"
        workbench = build_test_case_acceptance_workbench(
            planning_runs=planning_runs,
            master_data_versions=master_data_versions,
            operational_state_snapshots=operational_state_snapshots,
            release_authorizations=release_authorizations,
            acceptance_decisions=test_case_acceptance_decisions,
            evaluated_at=evaluated_at,
        )
        case = next(
            (item for item in workbench["Cases"] if item["CaseID"] == case_id),
            None,
        )
        if case is None:
            return JSONResponse(
                status_code=404,
                content={
                    "Endpoint": endpoint,
                    "StatusCode": 404,
                    "Data": {
                        "CaseID": case_id,
                        "Status": "TestCaseNotFound",
                        "Message": f"Test case {case_id} was not found.",
                    },
                },
            )
        if payload.Decision == "Confirm" and case["AcceptanceStatus"] != "Passed":
            return JSONResponse(
                status_code=409,
                content={
                    "Endpoint": endpoint,
                    "StatusCode": 409,
                    "Data": {
                        "CaseID": case_id,
                        "Status": "TestCaseNotPassed",
                        "AcceptanceStatus": case["AcceptanceStatus"],
                        "FailureReasons": case.get("FailureReasons", []),
                        "Message": "Only passed test cases can be confirmed.",
                    },
                },
            )
        decision = create_test_case_acceptance_decision(
            case=case,
            decision=payload.Decision,
            actor_id=payload.ActorID,
            decided_at=payload.DecidedAt,
            comment=payload.Comment,
            existing_decisions=test_case_acceptance_decisions,
        )
        test_case_acceptance_decisions.append(decision)
        _append_planning_run_audit_event(
            audit_events=audit_events,
            run_id=case_id,
            action="TestCaseAcceptanceDecision",
            actor_id=payload.ActorID,
            occurred_at=payload.DecidedAt,
            details={
                "Decision": payload.Decision,
                "AcceptancePackageID": decision["AcceptancePackageID"],
                "AcceptanceStatusAtDecision": decision["AcceptanceStatusAtDecision"],
            },
        )
        return {
            "Endpoint": endpoint,
            "StatusCode": 200,
            "Data": {"Decision": decision},
        }

    @app.get("/planner/workbench/administration/workbench")
    def planner_workbench_administration_workbench() -> dict[str, object]:
        availability = create_solver_engine(ACTIVE_SOLVER_BACKEND_ID).is_available()
        return {
            "Endpoint": "/planner/workbench/administration/workbench",
            "StatusCode": 200,
            "Data": build_administration_workbench(
                master_data_versions=master_data_versions.values(),
                planning_runs=planning_runs.values(),
                dbr_release_policies=dbr_release_policies.values(),
                base_calendars=base_calendars.values(),
                resource_calendar_assignments=_resource_calendar_assignments_with_driver_status(
                    assignments=resource_calendar_assignments.values(),
                    calendars=base_calendars.values(),
                    master_data_versions=master_data_versions.values(),
                    planning_runs=planning_runs.values(),
                ),
                calendar_overrides=_calendar_overrides_with_driver_status(
                    overrides=calendar_overrides.values(),
                    master_data_versions=master_data_versions.values(),
                    planning_runs=planning_runs.values(),
                ),
                scheduling_strategies=scheduling_strategy_versions.values(),
                integration_contracts=integration_contracts_payload()["Contracts"],
                integration_messages=integration_messages,
                state_store_health=active_store.health(),
                ortools_available=availability.available,
            ),
        }

    @app.post("/planner/workbench/admin/base-calendars")
    def planner_workbench_base_calendar_create(payload: BaseCalendarPayload):
        endpoint = "/planner/workbench/admin/base-calendars"
        if payload.CalendarID in base_calendars:
            return JSONResponse(
                status_code=409,
                content={
                    "Endpoint": endpoint,
                    "StatusCode": 409,
                    "Data": {
                        "CalendarID": payload.CalendarID,
                        "Status": "BaseCalendarConflict",
                        "Message": f"Base calendar {payload.CalendarID} already exists.",
                    },
                },
            )
        invalid_shift = next(
            (shift for shift in payload.Shifts if shift.End <= shift.Start),
            None,
        )
        if invalid_shift is not None:
            return JSONResponse(
                status_code=422,
                content={
                    "Endpoint": endpoint,
                    "StatusCode": 422,
                    "Data": {
                        "CalendarID": payload.CalendarID,
                        "Status": "BaseCalendarInvalid",
                        "Message": "Shift End must be later than Start.",
                    },
                },
            )
        invalid_window = next(
            (
                window
                for window in payload.MaintenanceWindows
                if window.End <= window.Start
            ),
            None,
        )
        if invalid_window is not None:
            return JSONResponse(
                status_code=422,
                content={
                    "Endpoint": endpoint,
                    "StatusCode": 422,
                    "Data": {
                        "CalendarID": payload.CalendarID,
                        "Status": "BaseCalendarInvalid",
                        "Message": "Maintenance window End must be later than Start.",
                    },
                },
            )
        calendar = _base_calendar_from_payload(payload)
        base_calendars[payload.CalendarID] = calendar
        _append_planning_run_audit_event(
            audit_events=audit_events,
            run_id=payload.CalendarID,
            action="BaseCalendarCreated",
            actor_id=payload.CreatedBy,
            occurred_at=payload.CreatedAt,
            details={
                "CalendarID": payload.CalendarID,
                "Status": payload.Status,
                "ShiftCount": len(payload.Shifts),
            },
        )
        enriched = _base_calendars_with_driver_status(
            calendars=[calendar],
            assignments=resource_calendar_assignments.values(),
            planning_runs=planning_runs.values(),
        )[0]
        return {"Endpoint": endpoint, "StatusCode": 200, "Data": {"Calendar": enriched}}

    @app.get("/planner/workbench/admin/base-calendars")
    def planner_workbench_base_calendar_list() -> dict[str, object]:
        calendars = sorted(
            _base_calendars_with_driver_status(
                calendars=base_calendars.values(),
                assignments=resource_calendar_assignments.values(),
                planning_runs=planning_runs.values(),
            ),
            key=lambda item: str(item.get("CreatedAt", "")),
            reverse=True,
        )
        return {
            "Endpoint": "/planner/workbench/admin/base-calendars",
            "StatusCode": 200,
            "Data": {
                "CalendarCount": len(calendars),
                "ActiveCalendarCount": sum(
                    1 for item in calendars if item.get("Status") == "Active"
                ),
                "Calendars": calendars,
            },
        }

    @app.get("/planner/workbench/admin/base-calendars/{calendar_id}")
    def planner_workbench_base_calendar_get(calendar_id: str):
        endpoint = f"/planner/workbench/admin/base-calendars/{calendar_id}"
        calendar = base_calendars.get(calendar_id)
        if calendar is None:
            return JSONResponse(
                status_code=404,
                content={
                    "Endpoint": endpoint,
                    "StatusCode": 404,
                    "Data": {
                        "CalendarID": calendar_id,
                        "Status": "BaseCalendarNotFound",
                        "Message": f"Base calendar {calendar_id} was not found.",
                    },
                },
            )
        enriched = _base_calendars_with_driver_status(
            calendars=[calendar],
            assignments=resource_calendar_assignments.values(),
            planning_runs=planning_runs.values(),
        )[0]
        return {"Endpoint": endpoint, "StatusCode": 200, "Data": {"Calendar": enriched}}

    @app.post("/planner/workbench/admin/resource-calendar-assignments")
    def planner_workbench_resource_calendar_assignment_create(
        payload: ResourceCalendarAssignmentPayload,
    ):
        endpoint = "/planner/workbench/admin/resource-calendar-assignments"
        if payload.AssignmentID in resource_calendar_assignments:
            return JSONResponse(
                status_code=409,
                content={
                    "Endpoint": endpoint,
                    "StatusCode": 409,
                    "Data": {
                        "AssignmentID": payload.AssignmentID,
                        "Status": "ResourceCalendarAssignmentConflict",
                        "Message": (
                            f"Resource calendar assignment {payload.AssignmentID} already exists."
                        ),
                    },
                },
            )
        if payload.CalendarID not in base_calendars:
            return JSONResponse(
                status_code=404,
                content={
                    "Endpoint": endpoint,
                    "StatusCode": 404,
                    "Data": {
                        "CalendarID": payload.CalendarID,
                        "Status": "BaseCalendarNotFound",
                        "Message": f"Base calendar {payload.CalendarID} was not found.",
                    },
                },
            )
        assignment = _resource_calendar_assignment_from_payload(payload)
        if assignment["Status"] == "Active":
            _retire_other_active_resource_calendar_assignments(
                assignments=resource_calendar_assignments,
                active_assignment_id=payload.AssignmentID,
                resource_id=payload.ResourceID,
            )
        resource_calendar_assignments[payload.AssignmentID] = assignment
        _append_planning_run_audit_event(
            audit_events=audit_events,
            run_id=payload.AssignmentID,
            action="ResourceCalendarAssignmentCreated",
            actor_id=payload.CreatedBy,
            occurred_at=payload.CreatedAt,
            details={
                "ResourceID": payload.ResourceID,
                "CalendarID": payload.CalendarID,
                "Status": payload.Status,
            },
        )
        enriched = _resource_calendar_assignments_with_driver_status(
            assignments=[assignment],
            calendars=base_calendars.values(),
            master_data_versions=master_data_versions.values(),
            planning_runs=planning_runs.values(),
        )[0]
        return {"Endpoint": endpoint, "StatusCode": 200, "Data": {"Assignment": enriched}}

    @app.get("/planner/workbench/admin/resource-calendar-assignments")
    def planner_workbench_resource_calendar_assignment_list() -> dict[str, object]:
        assignments = sorted(
            _resource_calendar_assignments_with_driver_status(
                assignments=resource_calendar_assignments.values(),
                calendars=base_calendars.values(),
                master_data_versions=master_data_versions.values(),
                planning_runs=planning_runs.values(),
            ),
            key=lambda item: str(item.get("CreatedAt", "")),
            reverse=True,
        )
        return {
            "Endpoint": "/planner/workbench/admin/resource-calendar-assignments",
            "StatusCode": 200,
            "Data": {
                "AssignmentCount": len(assignments),
                "ActiveAssignmentCount": sum(
                    1 for item in assignments if item.get("Status") == "Active"
                ),
                "Assignments": assignments,
            },
        }

    @app.post("/planner/workbench/admin/calendar-overrides")
    def planner_workbench_calendar_override_create(payload: CalendarOverridePayload):
        endpoint = "/planner/workbench/admin/calendar-overrides"
        if payload.OverrideID in calendar_overrides:
            return JSONResponse(
                status_code=409,
                content={
                    "Endpoint": endpoint,
                    "StatusCode": 409,
                    "Data": {
                        "OverrideID": payload.OverrideID,
                        "Status": "CalendarOverrideConflict",
                        "Message": (
                            f"Calendar override {payload.OverrideID} already exists."
                        ),
                    },
                },
            )
        if payload.EffectiveEndAt <= payload.EffectiveStartAt:
            return JSONResponse(
                status_code=422,
                content={
                    "Endpoint": endpoint,
                    "StatusCode": 422,
                    "Data": {
                        "OverrideID": payload.OverrideID,
                        "Status": "CalendarOverrideInvalid",
                        "Message": "EffectiveEndAt must be later than EffectiveStartAt.",
                    },
                },
            )
        override = _calendar_override_from_payload(payload)
        calendar_overrides[payload.OverrideID] = override
        _append_planning_run_audit_event(
            audit_events=audit_events,
            run_id=payload.OverrideID,
            action="CalendarOverrideCreated",
            actor_id=payload.CreatedBy,
            occurred_at=payload.CreatedAt,
            details={
                "CalendarID": payload.CalendarID,
                "ResourceID": payload.ResourceID,
                "OverrideType": payload.OverrideType,
                "Status": payload.Status,
            },
        )
        return {
            "Endpoint": endpoint,
            "StatusCode": 200,
            "Data": {"Override": override},
        }

    @app.get("/planner/workbench/admin/calendar-overrides")
    def planner_workbench_calendar_override_list() -> dict[str, object]:
        overrides = sorted(
            _calendar_overrides_with_driver_status(
                overrides=calendar_overrides.values(),
                master_data_versions=master_data_versions.values(),
                planning_runs=planning_runs.values(),
            ),
            key=lambda item: str(item.get("EffectiveStartAt", "")),
            reverse=True,
        )
        return {
            "Endpoint": "/planner/workbench/admin/calendar-overrides",
            "StatusCode": 200,
            "Data": {
                "OverrideCount": len(overrides),
                "ActiveOverrideCount": sum(
                    1 for item in overrides if item.get("Status") == "Active"
                ),
                "ConflictCheckStatus": "NotEnforced",
                "Overrides": overrides,
            },
        }

    @app.get("/planner/workbench/admin/calendar-overrides/{override_id}")
    def planner_workbench_calendar_override_get(override_id: str):
        endpoint = f"/planner/workbench/admin/calendar-overrides/{override_id}"
        override = calendar_overrides.get(override_id)
        if override is None:
            return JSONResponse(
                status_code=404,
                content={
                    "Endpoint": endpoint,
                    "StatusCode": 404,
                    "Data": {
                        "OverrideID": override_id,
                        "Status": "CalendarOverrideNotFound",
                        "Message": f"Calendar override {override_id} was not found.",
                    },
                },
            )
        enriched = _calendar_overrides_with_driver_status(
            overrides=[override],
            master_data_versions=master_data_versions.values(),
            planning_runs=planning_runs.values(),
        )[0]
        return {"Endpoint": endpoint, "StatusCode": 200, "Data": {"Override": enriched}}

    @app.get("/planner/workbench/calendar/resources")
    def planner_workbench_calendar_resources(
        MasterDataVersionID: str | None = None,
    ) -> dict[str, object]:
        version = _calendar_preview_master_data_version(
            master_data_versions=master_data_versions,
            version_id=MasterDataVersionID,
        )
        resources = _resources_from_payload(
            [ResourcePayload(**item) for item in version.get("Resources", [])]
        ) if version else []
        rows = _resources_to_payload_dict(resources)
        return {
            "Endpoint": "/planner/workbench/calendar/resources",
            "StatusCode": 200,
            "Data": {
                "ResourceCount": len(rows),
                "Resources": rows,
            },
        }

    @app.get("/planner/workbench/calendar/preview")
    def planner_workbench_calendar_preview(
        StartDate: date,
        EndDate: date,
        ResourceID: str | None = None,
        MasterDataVersionID: str | None = None,
        Timezone: str = "UTC",
    ):
        endpoint = "/planner/workbench/calendar/preview"
        if EndDate < StartDate:
            return JSONResponse(
                status_code=422,
                content={
                    "Endpoint": endpoint,
                    "StatusCode": 422,
                    "Data": {
                        "Status": "CalendarPreviewInvalidRange",
                        "Message": "EndDate must be on or after StartDate.",
                    },
                },
            )
        try:
            tzinfo = ZoneInfo(Timezone)
        except Exception:
            return JSONResponse(
                status_code=422,
                content={
                    "Endpoint": endpoint,
                    "StatusCode": 422,
                    "Data": {
                        "Status": "CalendarPreviewInvalidTimezone",
                        "Message": f"Timezone {Timezone} is not valid.",
                    },
                },
            )
        version = _calendar_preview_master_data_version(
            master_data_versions=master_data_versions,
            version_id=MasterDataVersionID,
        )
        if version is None:
            return _planning_run_reference_error(
                endpoint=endpoint,
                entity_id=MasterDataVersionID or "latest",
                status="MasterDataVersionNotFound",
                message="No master data version with resources was found for calendar preview.",
            )
        resources = _resources_from_payload(
            [
                ResourcePayload(**item)
                for item in version.get("Resources", [])
                if isinstance(item, dict)
            ]
        )
        if ResourceID is not None and all(
            resource.resource_id != ResourceID for resource in resources
        ):
            return _planning_run_reference_error(
                endpoint=endpoint,
                entity_id=ResourceID,
                status="ResourceNotFound",
                message=f"Resource {ResourceID} was not found in master data version {version.get('VersionID')}.",
            )
        return {
            "Endpoint": endpoint,
            "StatusCode": 200,
            "Data": build_calendar_preview(
                resources=resources,
                base_calendars=list(base_calendars.values()),
                resource_calendar_assignments=list(
                    resource_calendar_assignments.values()
                ),
                calendar_overrides=list(calendar_overrides.values()),
                start_date=StartDate,
                end_date=EndDate,
                tzinfo=tzinfo,
                resource_id=ResourceID,
            )
            | {"MasterDataVersionID": version.get("VersionID")},
        }

    @app.post("/planner/workbench/admin/scheduling-strategies")
    def planner_workbench_scheduling_strategy_create(
        payload: SchedulingStrategyPayload,
    ):
        endpoint = "/planner/workbench/admin/scheduling-strategies"
        if payload.StrategyID in scheduling_strategy_versions:
            return JSONResponse(
                status_code=409,
                content={
                    "Endpoint": endpoint,
                    "StatusCode": 409,
                    "Data": {
                        "StrategyID": payload.StrategyID,
                        "Status": "SchedulingStrategyConflict",
                        "Message": (
                            f"Scheduling strategy {payload.StrategyID} already exists."
                        ),
                    },
                },
            )
        strategy = _scheduling_strategy_from_payload(payload)
        if strategy["Status"] == "Active":
            _retire_other_active_scheduling_strategies(
                scheduling_strategy_versions=scheduling_strategy_versions,
                active_strategy_id=payload.StrategyID,
            )
        scheduling_strategy_versions[payload.StrategyID] = strategy
        _append_planning_run_audit_event(
            audit_events=audit_events,
            run_id=payload.StrategyID,
            action="SchedulingStrategyCreated",
            actor_id=payload.CreatedBy,
            occurred_at=payload.CreatedAt,
            details={
                "StrategyID": payload.StrategyID,
                "Status": payload.Status,
                "ObjectiveWeights": strategy["ObjectiveWeights"],
            },
        )
        return {
            "Endpoint": endpoint,
            "StatusCode": 200,
            "Data": {"Strategy": strategy},
        }

    @app.get("/planner/workbench/admin/scheduling-strategies")
    def planner_workbench_scheduling_strategy_list() -> dict[str, object]:
        strategies = sorted(
            scheduling_strategy_versions.values(),
            key=lambda item: str(item.get("CreatedAt", "")),
            reverse=True,
        )
        active = next(
            (item for item in strategies if item.get("Status") == "Active"),
            None,
        )
        return {
            "Endpoint": "/planner/workbench/admin/scheduling-strategies",
            "StatusCode": 200,
            "Data": {
                "StrategyCount": len(strategies),
                "ActiveStrategyID": active.get("StrategyID") if active else None,
                "BuiltInStrategyIDs": [
                    "v1_delivery_flow_bottleneck",
                    "balanced",
                    "delivery_first",
                    "flow_first",
                    "bottleneck_protect",
                ],
                "CustomWeightPersistenceStatus": "Available",
                "Strategies": strategies,
            },
        }

    @app.get("/planner/workbench/admin/scheduling-strategies/{strategy_id}")
    def planner_workbench_scheduling_strategy_get(strategy_id: str):
        endpoint = f"/planner/workbench/admin/scheduling-strategies/{strategy_id}"
        strategy = scheduling_strategy_versions.get(strategy_id)
        if strategy is None:
            return JSONResponse(
                status_code=404,
                content={
                    "Endpoint": endpoint,
                    "StatusCode": 404,
                    "Data": {
                        "StrategyID": strategy_id,
                        "Status": "SchedulingStrategyNotFound",
                        "Message": f"Scheduling strategy {strategy_id} was not found.",
                    },
                },
            )
        return {"Endpoint": endpoint, "StatusCode": 200, "Data": {"Strategy": strategy}}

    @app.get("/planner/workbench/admin/cp-sat/assumptions")
    def planner_workbench_cp_sat_assumptions() -> dict[str, object]:
        endpoint = "/planner/workbench/admin/cp-sat/assumptions"
        return {
            "Endpoint": endpoint,
            "StatusCode": 200,
            "Data": _cp_sat_assumptions_payload(
                scheduling_strategy_versions=scheduling_strategy_versions,
                dbr_release_policies=dbr_release_policies,
            ),
        }

    @app.get("/planner/workbench/integrations/contracts")
    def planner_workbench_integration_contracts() -> dict[str, object]:
        return {
            "Endpoint": "/planner/workbench/integrations/contracts",
            "StatusCode": 200,
            "Data": integration_contracts_payload(),
        }

    @app.get("/planner/workbench/integrations/mock-api/status")
    def planner_workbench_integration_mock_api_status() -> dict[str, object]:
        return {
            "Endpoint": "/planner/workbench/integrations/mock-api/status",
            "StatusCode": 200,
            "Data": integration_adapter_status_payload(),
        }

    @app.get("/planner/workbench/integrations/contracts/{contract_id}")
    def planner_workbench_integration_contract_get(contract_id: str):
        endpoint = f"/planner/workbench/integrations/contracts/{contract_id}"
        contract = find_integration_contract(contract_id)
        if contract is None:
            return JSONResponse(
                status_code=404,
                content={
                    "Endpoint": endpoint,
                    "StatusCode": 404,
                    "Data": {
                        "ContractID": contract_id,
                        "Status": "IntegrationContractNotFound",
                        "Message": f"Integration contract {contract_id} was not found.",
                    },
                },
            )
        return {
            "Endpoint": endpoint,
            "StatusCode": 200,
            "Data": {"Contract": contract.to_dict()},
        }

    @app.post("/planner/workbench/integrations/messages")
    def planner_workbench_integration_message_create(
        payload: IntegrationMessagePayload,
        request: Request,
    ):
        endpoint = "/planner/workbench/integrations/messages"
        contract = find_integration_contract(payload.ContractID)
        if contract is None:
            return JSONResponse(
                status_code=404,
                content={
                    "Endpoint": endpoint,
                    "StatusCode": 404,
                    "Data": {
                        "ContractID": payload.ContractID,
                        "Status": "IntegrationContractNotFound",
                        "Message": f"Integration contract {payload.ContractID} was not found.",
                    },
                },
            )
        received_at = datetime.now(timezone.utc)
        message = payload.model_dump(mode="json", exclude={"ContractID"})
        validation = validate_integration_message(
            contract=contract,
            message=message,
            existing_messages=integration_messages,
            received_at=received_at,
        )
        message_recorded = validation["Status"] in {"Accepted", "Rejected"}
        if message_recorded:
            integration_messages.append(
                integration_message_record(
                    contract=contract,
                    message=message,
                    validation=validation,
                )
            )
        status_code = 200 if validation["Accepted"] else 409
        body = {
            "Endpoint": endpoint,
            "StatusCode": status_code,
            "Data": validation,
        }
        if status_code != 200:
            if message_recorded:
                request.state.persist_workbench_write = True
            return JSONResponse(status_code=status_code, content=body)
        return body

    @app.get("/planner/workbench/integrations/messages/dead-letter")
    def planner_workbench_integration_dead_letters() -> dict[str, object]:
        rows = integration_dead_letters(integration_messages)
        return {
            "Endpoint": "/planner/workbench/integrations/messages/dead-letter",
            "StatusCode": 200,
            "Data": {
                "Count": len(rows),
                "Messages": rows,
            },
        }

    @app.post("/planner/workbench/integrations/messages/{message_id}/replay")
    def planner_workbench_integration_message_replay(
        message_id: str,
        payload: IntegrationReplayPayload,
    ):
        endpoint = f"/planner/workbench/integrations/messages/{message_id}/replay"
        replayed = replay_integration_message(
            message_id=message_id,
            messages=integration_messages,
            replayed_at=payload.ReplayedAt,
            actor_id=payload.ActorID,
        )
        if replayed is None:
            return JSONResponse(
                status_code=404,
                content={
                    "Endpoint": endpoint,
                    "StatusCode": 404,
                    "Data": {
                        "MessageID": message_id,
                        "Status": "IntegrationMessageNotFound",
                        "Message": f"Integration message {message_id} was not found.",
                    },
                },
            )
        return {
            "Endpoint": endpoint,
            "StatusCode": 200,
            "Data": {"Message": replayed},
        }

    @app.get("/planner/workbench/data-readiness")
    def planner_workbench_data_readiness(
        evaluated_at: datetime | None = Query(default=None, alias="EvaluatedAt"),
        max_snapshot_age_minutes: int = Query(
            default=60,
            alias="MaxSnapshotAgeMinutes",
            gt=0,
            le=10080,
        ),
    ) -> dict[str, object]:
        effective_evaluated_at = evaluated_at or datetime.now(timezone.utc)
        return {
            "Endpoint": "/planner/workbench/data-readiness",
            "StatusCode": 200,
            "Data": build_data_readiness(
                master_data_versions=master_data_versions.values(),
                operational_state_snapshots=operational_state_snapshots.values(),
                evaluated_at=effective_evaluated_at,
                max_snapshot_age_minutes=max_snapshot_age_minutes,
            ),
        }

    @app.post("/planner/workbench/routings/import")
    def planner_workbench_routings_import(payload: RoutingImportPayload) -> dict[str, object]:
        routings = import_routings_from_operation_rows(_routing_import_rows_from_payload(payload.Rows))
        validation = validate_master_data(
            resources=_resources_from_payload(payload.Resources),
            routings=routings,
            orders=[],
            inventory_buffers=[],
            material_requirements=[],
            calendar_timezone=payload.CalendarTimezone,
        )
        return {
            "Endpoint": "/planner/workbench/routings/import",
            "StatusCode": 200,
            "Data": {
                "Routings": _routings_to_payload_dict(routings),
                "Validation": _master_data_validation_to_dict(validation),
            },
        }

    @app.post("/planner/workbench/orders/import")
    def planner_workbench_orders_import(payload: OrderImportPayload) -> dict[str, object]:
        orders = import_orders_from_rows(_order_import_rows_from_payload(payload.Rows))
        validation = validate_master_data(
            resources=_resources_from_payload(payload.Resources),
            routings=_routings_from_payload(payload.Routings),
            orders=orders,
            inventory_buffers=[],
            material_requirements=[],
            calendar_timezone=payload.CalendarTimezone,
        )
        return {
            "Endpoint": "/planner/workbench/orders/import",
            "StatusCode": 200,
            "Data": {
                "Orders": _orders_to_payload_dict(orders),
                "Validation": _master_data_validation_to_dict(validation),
            },
        }

    @app.post("/planner/workbench/master-data/versions")
    def planner_workbench_master_data_version_create(payload: MasterDataVersionPayload):
        endpoint = "/planner/workbench/master-data/versions"
        if payload.VersionID in master_data_versions:
            return JSONResponse(
                status_code=409,
                content={
                    "Endpoint": endpoint,
                    "StatusCode": 409,
                    "Data": {
                        "VersionID": payload.VersionID,
                        "Status": "MasterDataVersionConflict",
                        "Message": f"Master data version {payload.VersionID} already exists.",
                    },
                },
            )
        version = _master_data_version_from_payload(payload)
        master_data_versions[payload.VersionID] = version
        return {
            "Endpoint": endpoint,
            "StatusCode": 200,
            "Data": {
                "Version": version,
            },
        }

    @app.get("/planner/workbench/master-data/versions/{version_id}")
    def planner_workbench_master_data_version_get(version_id: str):
        endpoint = f"/planner/workbench/master-data/versions/{version_id}"
        version = master_data_versions.get(version_id)
        if version is None:
            return JSONResponse(
                status_code=404,
                content={
                    "Endpoint": endpoint,
                    "StatusCode": 404,
                    "Data": {
                        "VersionID": version_id,
                        "Status": "MasterDataVersionNotFound",
                        "Message": f"Master data version {version_id} was not found.",
                    },
                },
            )
        return {
            "Endpoint": endpoint,
            "StatusCode": 200,
            "Data": {
                "Version": version,
            },
        }

    @app.get("/planner/workbench/master-data/version-comparison")
    def planner_workbench_master_data_version_compare(
        baseline_version_id: str,
        candidate_version_id: str,
    ):
        endpoint = "/planner/workbench/master-data/version-comparison"
        baseline = master_data_versions.get(baseline_version_id)
        candidate = master_data_versions.get(candidate_version_id)
        if baseline is None:
            return _planning_run_reference_error(
                endpoint=endpoint,
                entity_id=baseline_version_id,
                status="MasterDataVersionNotFound",
                message=f"Master data version {baseline_version_id} was not found.",
            )
        if candidate is None:
            return _planning_run_reference_error(
                endpoint=endpoint,
                entity_id=candidate_version_id,
                status="MasterDataVersionNotFound",
                message=f"Master data version {candidate_version_id} was not found.",
            )
        return {
            "Endpoint": endpoint,
            "StatusCode": 200,
            "Data": _master_data_version_diff(
                baseline=baseline,
                candidate=candidate,
            ),
        }

    @app.post("/planner/workbench/master-data/versions/{version_id}/publish")
    def planner_workbench_master_data_version_publish(
        version_id: str,
        payload: MasterDataVersionTransitionPayload,
        request: Request,
    ):
        endpoint = f"/planner/workbench/master-data/versions/{version_id}/publish"
        version = master_data_versions.get(version_id)
        if version is None:
            return _planning_run_reference_error(
                endpoint=endpoint,
                entity_id=version_id,
                status="MasterDataVersionNotFound",
                message=f"Master data version {version_id} was not found.",
            )
        if version.get("Status") != "Valid":
            return JSONResponse(
                status_code=409,
                content={
                    "Endpoint": endpoint,
                    "StatusCode": 409,
                    "Data": {
                        "VersionID": version_id,
                        "Status": "MasterDataVersionInvalid",
                        "Message": "Only valid master data versions can be published.",
                    },
                },
            )
        for other_id, other in master_data_versions.items():
            if other_id != version_id and other.get("PublicationStatus") == "Published":
                other["PublicationStatus"] = "Inactive"
                other["InactivatedByVersionID"] = version_id
        updated = dict(version)
        updated.update(
            {
                "PublicationStatus": "Published",
                "PublishedBy": _effective_actor_id(request, payload.ActorID),
                "PublishedAt": payload.OccurredAt.isoformat(),
                "PublicationReason": payload.Reason,
            }
        )
        master_data_versions[version_id] = updated
        _append_planning_run_audit_event(
            audit_events=audit_events,
            run_id=version_id,
            action="MasterDataVersionPublished",
            actor_id=_effective_actor_id(request, payload.ActorID),
            occurred_at=payload.OccurredAt,
            details={"Reason": payload.Reason},
        )
        return {"Endpoint": endpoint, "StatusCode": 200, "Data": {"Version": updated}}

    @app.post("/planner/workbench/master-data/versions/{version_id}/retire")
    def planner_workbench_master_data_version_retire(
        version_id: str,
        payload: MasterDataVersionTransitionPayload,
        request: Request,
    ):
        endpoint = f"/planner/workbench/master-data/versions/{version_id}/retire"
        version = master_data_versions.get(version_id)
        if version is None:
            return _planning_run_reference_error(
                endpoint=endpoint,
                entity_id=version_id,
                status="MasterDataVersionNotFound",
                message=f"Master data version {version_id} was not found.",
            )
        updated = dict(version)
        updated.update(
            {
                "PublicationStatus": "Retired",
                "RetiredBy": _effective_actor_id(request, payload.ActorID),
                "RetiredAt": payload.OccurredAt.isoformat(),
                "RetirementReason": payload.Reason,
            }
        )
        master_data_versions[version_id] = updated
        _append_planning_run_audit_event(
            audit_events=audit_events,
            run_id=version_id,
            action="MasterDataVersionRetired",
            actor_id=_effective_actor_id(request, payload.ActorID),
            occurred_at=payload.OccurredAt,
            details={"Reason": payload.Reason},
        )
        return {"Endpoint": endpoint, "StatusCode": 200, "Data": {"Version": updated}}

    @app.post("/planner/workbench/master-data/versions/{version_id}/rollback")
    def planner_workbench_master_data_version_rollback(
        version_id: str,
        payload: MasterDataVersionTransitionPayload,
        request: Request,
    ):
        endpoint = f"/planner/workbench/master-data/versions/{version_id}/rollback"
        version = master_data_versions.get(version_id)
        if version is None:
            return _planning_run_reference_error(
                endpoint=endpoint,
                entity_id=version_id,
                status="MasterDataVersionNotFound",
                message=f"Master data version {version_id} was not found.",
            )
        updated = dict(version)
        updated.update(
            {
                "PublicationStatus": "Published",
                "RolledBackBy": _effective_actor_id(request, payload.ActorID),
                "RolledBackAt": payload.OccurredAt.isoformat(),
                "RollbackReason": payload.Reason,
            }
        )
        for other_id, other in master_data_versions.items():
            if other_id != version_id and other.get("PublicationStatus") == "Published":
                other["PublicationStatus"] = "Inactive"
                other["InactivatedByVersionID"] = version_id
        master_data_versions[version_id] = updated
        _append_planning_run_audit_event(
            audit_events=audit_events,
            run_id=version_id,
            action="MasterDataVersionRollbackPublished",
            actor_id=_effective_actor_id(request, payload.ActorID),
            occurred_at=payload.OccurredAt,
            details={"Reason": payload.Reason},
        )
        return {"Endpoint": endpoint, "StatusCode": 200, "Data": {"Version": updated}}

    @app.post("/planner/workbench/dbr/release-policies")
    def planner_workbench_dbr_release_policy_create(
        payload: DbrReleasePolicyPayload,
    ):
        endpoint = "/planner/workbench/dbr/release-policies"
        if payload.VersionID in dbr_release_policies:
            return JSONResponse(
                status_code=409,
                content={
                    "Endpoint": endpoint,
                    "StatusCode": 409,
                    "Data": {
                        "VersionID": payload.VersionID,
                        "Status": "DbrReleasePolicyConflict",
                        "Message": f"DBR release policy {payload.VersionID} already exists.",
                    },
                },
            )
        policy = _dbr_release_policy_from_payload(payload)
        if policy["Status"] == "Active":
            _retire_other_active_policies(
                dbr_release_policies=dbr_release_policies,
                active_version_id=payload.VersionID,
            )
        dbr_release_policies[payload.VersionID] = policy
        return {
            "Endpoint": endpoint,
            "StatusCode": 200,
            "Data": {"Policy": policy},
        }

    @app.get("/planner/workbench/dbr/release-policies")
    def planner_workbench_dbr_release_policy_list() -> dict[str, object]:
        policies = sorted(
            dbr_release_policies.values(),
            key=lambda item: str(item.get("CreatedAt", "")),
            reverse=True,
        )
        active = next(
            (policy for policy in policies if policy.get("Status") == "Active"),
            None,
        )
        return {
            "Endpoint": "/planner/workbench/dbr/release-policies",
            "StatusCode": 200,
            "Data": {
                "PolicyCount": len(policies),
                "ActivePolicyVersionID": (
                    active.get("VersionID") if active is not None else None
                ),
                "Policies": policies,
                "ConfigurableParameters": [
                    "RopeBufferMinutes",
                    "TimeBufferRatios",
                    "MaxWipCount",
                    "MaterialLookaheadMinutes",
                    "StabilityPolicy",
                ],
            },
        }

    @app.get("/planner/workbench/dbr/release-policies/{version_id}")
    def planner_workbench_dbr_release_policy_get(version_id: str):
        endpoint = f"/planner/workbench/dbr/release-policies/{version_id}"
        policy = dbr_release_policies.get(version_id)
        if policy is None:
            return JSONResponse(
                status_code=404,
                content={
                    "Endpoint": endpoint,
                    "StatusCode": 404,
                    "Data": {
                        "VersionID": version_id,
                        "Status": "DbrReleasePolicyNotFound",
                        "Message": f"DBR release policy {version_id} was not found.",
                    },
                },
            )
        return {"Endpoint": endpoint, "StatusCode": 200, "Data": {"Policy": policy}}

    @app.post("/planner/workbench/planning-runs")
    def planner_workbench_planning_run_create(
        payload: PlanningRunPayload,
        request: Request,
    ):
        endpoint = "/planner/workbench/planning-runs"
        if payload.SolverBackendID in PAUSED_SOLVER_BACKEND_IDS:
            return JSONResponse(
                status_code=409,
                content={
                    "Endpoint": endpoint,
                    "StatusCode": 409,
                    "Data": {
                        "RunID": payload.RunID,
                        "SolverBackendID": payload.SolverBackendID,
                        "Status": "SolverBackendPaused",
                        "Message": (
                            f"Solver backend {payload.SolverBackendID} is paused for new planning runs."
                        ),
                    },
                },
            )
        if payload.RunID in planning_runs:
            return JSONResponse(
                status_code=409,
                content={
                    "Endpoint": endpoint,
                    "StatusCode": 409,
                    "Data": {
                        "RunID": payload.RunID,
                        "Status": "PlanningRunConflict",
                        "Message": f"Planning run {payload.RunID} already exists.",
                    },
                },
            )
        master_data_version = master_data_versions.get(payload.MasterDataVersionID)
        if master_data_version is None:
            return _planning_run_reference_error(
                endpoint=endpoint,
                entity_id=payload.MasterDataVersionID,
                status="MasterDataVersionNotFound",
                message=(
                    f"Master data version {payload.MasterDataVersionID} was not found."
                ),
            )
        if master_data_version["Status"] != "Valid":
            return JSONResponse(
                status_code=409,
                content={
                    "Endpoint": endpoint,
                    "StatusCode": 409,
                    "Data": {
                        "MasterDataVersionID": payload.MasterDataVersionID,
                        "Status": "MasterDataVersionInvalid",
                        "Validation": master_data_version["Validation"],
                        "Message": (
                            f"Master data version {payload.MasterDataVersionID} "
                            "cannot be scheduled because it is invalid."
                        ),
                    },
                },
            )
        operational_snapshot = operational_state_snapshots.get(
            payload.OperationalStateSnapshotID
        )
        if operational_snapshot is None:
            return _planning_run_reference_error(
                endpoint=endpoint,
                entity_id=payload.OperationalStateSnapshotID,
                status="OperationalStateSnapshotNotFound",
                message=(
                    "Operational state snapshot "
                    f"{payload.OperationalStateSnapshotID} was not found."
                ),
            )
        if payload.SourceRunID is not None:
            source_run = planning_runs.get(payload.SourceRunID)
            if source_run is None:
                return _planning_run_reference_error(
                    endpoint=endpoint,
                    entity_id=payload.SourceRunID,
                    status="SourcePlanningRunNotFound",
                    message=f"Source planning run {payload.SourceRunID} was not found.",
                )
            if source_run.get("Status") != "Completed":
                return JSONResponse(
                    status_code=409,
                    content={
                        "Endpoint": endpoint,
                        "StatusCode": 409,
                        "Data": {
                            "SourceRunID": payload.SourceRunID,
                            "Status": "SourcePlanningRunNotCompleted",
                            "Message": "Source planning run must be completed before it can seed a new run.",
                        },
                    },
                )
        operating_model_configuration_record = None
        if payload.OperatingModelConfigurationID is not None:
            operating_model_configuration_record = operating_model_configurations.get(
                payload.OperatingModelConfigurationID
            )
            if operating_model_configuration_record is None:
                return _planning_run_reference_error(
                    endpoint=endpoint,
                    entity_id=payload.OperatingModelConfigurationID,
                    status="OperatingModelConfigurationNotFound",
                    message=(
                        "Operating model configuration "
                        f"{payload.OperatingModelConfigurationID} was not found."
                    ),
                )
            if operating_model_configuration_record.get("Status") not in {
                "Approved",
                "Active",
            } or not operating_model_configuration_record.get(
                "UsableForPlanningRun",
                False,
            ):
                return JSONResponse(
                    status_code=409,
                    content={
                        "Endpoint": endpoint,
                        "StatusCode": 409,
                        "Data": {
                            "OperatingModelConfigurationID": payload.OperatingModelConfigurationID,
                            "Status": "OperatingModelConfigurationNotUsable",
                            "ConfigurationStatus": operating_model_configuration_record.get(
                                "Status"
                            ),
                            "ProcessingStatus": operating_model_configuration_record.get(
                                "ProcessingStatus"
                            ),
                            "PendingReferences": operating_model_configuration_record.get(
                                "PendingReferences",
                                [],
                            ),
                            "Message": (
                                "Only Approved or Active DDAE configurations with resolved references "
                                "can be frozen into a Planning Run."
                            ),
                        },
                    },
                )
            reference_errors = validate_required_master_data_references(
                operating_model_configuration_record,
                master_data_version,
            )
            if reference_errors:
                return JSONResponse(
                    status_code=409,
                    content={
                        "Endpoint": endpoint,
                        "StatusCode": 409,
                        "Data": {
                            "OperatingModelConfigurationID": payload.OperatingModelConfigurationID,
                            "MasterDataVersionID": payload.MasterDataVersionID,
                            "Status": "REFERENCE_NOT_FOUND",
                            "Errors": reference_errors,
                            "Message": (
                                "DDAE Operating Model Configuration contains references "
                                "that cannot be resolved in the selected Master Data Version."
                            ),
                        },
                    },
                )
        scheduling_strategy = _scheduling_strategy_snapshot_for_id(
            strategy_id=payload.ObjectiveStrategyID,
            scheduling_strategy_versions=scheduling_strategy_versions,
        )
        if scheduling_strategy is None:
            return _objective_strategy_not_found_response(
                endpoint=endpoint,
                strategy_id=payload.ObjectiveStrategyID,
            )
        release_policy = None
        if payload.ReleasePolicyVersionID is not None:
            release_policy = dbr_release_policies.get(payload.ReleasePolicyVersionID)
            if release_policy is None:
                return JSONResponse(
                    status_code=404,
                    content={
                        "Endpoint": endpoint,
                        "StatusCode": 404,
                        "Data": {
                            "VersionID": payload.ReleasePolicyVersionID,
                            "Status": "DbrReleasePolicyNotFound",
                            "Message": f"DBR release policy {payload.ReleasePolicyVersionID} was not found.",
                        },
                    },
                )
        with reservation_graph_lock:
            for batch_id in payload.PlanningReservationBatchIDs:
                if not isinstance(batch_id, str) or not batch_id.strip():
                    return JSONResponse(
                        status_code=409,
                        content={
                            "Endpoint": endpoint,
                            "StatusCode": 409,
                            "Data": {
                                "Status": "PlanningReservationBatchInvalid",
                                "Message": (
                                    "Planning reservation batch graph is incomplete or "
                                    "inconsistent."
                                ),
                            },
                        },
                    )
                batch = planning_reservation_batches.get(batch_id)
                if batch is None:
                    return JSONResponse(
                        status_code=404,
                        content={
                            "Endpoint": endpoint,
                            "StatusCode": 404,
                            "Data": {
                                "ReservationBatchID": batch_id,
                                "Status": "PlanningReservationBatchNotFound",
                                "Message": "Requested planning reservation batch was not found.",
                            },
                        },
                    )
                if not isinstance(batch, dict) or not isinstance(
                    batch.get("Status"), str
                ):
                    return JSONResponse(
                        status_code=409,
                        content={
                            "Endpoint": endpoint,
                            "StatusCode": 409,
                            "Data": {
                                "ReservationBatchID": batch_id,
                                "Status": "PlanningReservationBatchInvalid",
                                "Message": (
                                    "Planning reservation batch graph is incomplete or "
                                    "inconsistent."
                                ),
                            },
                        },
                    )
                if batch.get("Status") not in {
                    "ActivePlanReservation",
                    "LinkedToFormalOrder",
                }:
                    return JSONResponse(
                        status_code=409,
                        content={
                            "Endpoint": endpoint,
                            "StatusCode": 409,
                            "Data": {
                                "ReservationBatchID": batch_id,
                                "Status": "PlanningReservationBatchNotEligible",
                                "Message": (
                                    "Requested planning reservation batch is not eligible "
                                    "for a planning run."
                                ),
                            },
                        },
                    )
            try:
                frozen_planning_reservations = freeze_planning_reservations(
                    batch_ids=payload.PlanningReservationBatchIDs,
                    demand_commitments=planning_demand_commitments,
                    batches=planning_reservation_batches,
                    capacity_reservations=ccr_capacity_reservations,
                    material_allocations=material_planning_allocations,
                )
            except ReservationBatchReferenceError:
                return JSONResponse(
                    status_code=409,
                    content={
                        "Endpoint": endpoint,
                        "StatusCode": 409,
                        "Data": {
                            "Status": "PlanningReservationBatchInvalid",
                            "Message": (
                                "Planning reservation batch graph is incomplete or inconsistent."
                            ),
                        },
                    },
                )
        planning_run = _pending_planning_run(
            payload=payload,
            master_data_version=master_data_version,
            operational_snapshot=operational_snapshot,
            release_policy=release_policy,
            scheduling_strategy=scheduling_strategy,
            operating_model_configuration=operating_model_configuration_record,
            frozen_base_calendars=_active_base_calendars(base_calendars.values()),
            frozen_resource_calendar_assignments=_active_resource_calendar_assignments(
                resource_calendar_assignments.values()
            ),
            frozen_calendar_overrides=_active_calendar_overrides(
                calendar_overrides.values()
            ),
            frozen_planning_reservations=frozen_planning_reservations,
        )
        planning_runs[payload.RunID] = planning_run
        _append_planning_run_audit_event(
            audit_events=audit_events,
            run_id=payload.RunID,
            action="PlanningRunCreated",
            actor_id=_effective_actor_id(request, payload.RequestedBy),
            occurred_at=payload.RequestedAt,
        )
        return {
            "Endpoint": endpoint,
            "StatusCode": 200,
            "Data": {
                "PlanningRun": _planning_run_public_record(planning_run),
            },
        }

    @app.post("/planner/workbench/planning-runs/{run_id}/enqueue")
    def planner_workbench_planning_run_enqueue(
        run_id: str,
        payload: PlanningRunEnqueuePayload,
        request: Request,
    ):
        endpoint = f"/planner/workbench/planning-runs/{run_id}/enqueue"
        planning_run = planning_runs.get(run_id)
        if planning_run is None:
            return _planning_run_not_found(endpoint=endpoint, run_id=run_id)
        if planning_run.get("SolverBackendID") in PAUSED_SOLVER_BACKEND_IDS:
            return JSONResponse(
                status_code=409,
                content={
                    "Endpoint": endpoint,
                    "StatusCode": 409,
                    "Data": {
                        "RunID": run_id,
                        "SolverBackendID": planning_run.get("SolverBackendID"),
                        "Status": "SolverBackendPaused",
                        "Message": "Paused solver runs must be copied to a new CP-SAT planning run.",
                    },
                },
            )
        if planning_run["Status"] != "Pending":
            return _planning_run_transition_conflict(
                endpoint=endpoint,
                planning_run=planning_run,
                message=f"Planning run {run_id} is not pending and cannot be enqueued.",
            )
        queued_run = dict(planning_run)
        queued_run.update(
            {
                "Status": "Queued",
                "EnqueuedBy": payload.EnqueuedBy,
                "EnqueuedAt": payload.EnqueuedAt.isoformat(),
                "AttemptCount": 0,
                "MaxAttempts": payload.MaxAttempts,
                "RetryDelaySeconds": payload.RetryDelaySeconds,
                "NextAttemptAt": payload.EnqueuedAt.isoformat(),
            }
        )
        queued_run["StatusHistory"] = [
            *planning_run["StatusHistory"],
            {
                "Status": "Queued",
                "ChangedAt": payload.EnqueuedAt.isoformat(),
                "ChangedBy": payload.EnqueuedBy,
            },
        ]
        planning_runs[run_id] = queued_run
        _append_planning_run_audit_event(
            audit_events=audit_events,
            run_id=run_id,
            action="PlanningRunEnqueued",
            actor_id=_effective_actor_id(request, payload.EnqueuedBy),
            occurred_at=payload.EnqueuedAt,
            details={
                "MaxAttempts": payload.MaxAttempts,
                "RetryDelaySeconds": payload.RetryDelaySeconds,
            },
        )
        return {
            "Endpoint": endpoint,
            "StatusCode": 200,
            "Data": {"PlanningRun": _planning_run_public_record(queued_run)},
        }

    @app.post("/planner/workbench/planning-runs/jobs/claim-next")
    def planner_workbench_planning_run_claim_next(
        payload: PlanningRunClaimPayload,
        request: Request,
    ):
        endpoint = "/planner/workbench/planning-runs/jobs/claim-next"
        with claim_lock:
            identity_error = _worker_identity_mismatch_response(
                request=request,
                claimed_worker_id=payload.WorkerID,
                endpoint=endpoint,
            )
            if identity_error is not None:
                return identity_error
            claim_observed_at = server_utc_now()
            candidates = [
                planning_run
                for planning_run in planning_runs.values()
                if planning_run.get("SolverBackendID") == ACTIVE_SOLVER_BACKEND_ID
                and (
                    (
                        planning_run["Status"] == "Queued"
                        and _planning_run_ready_for_claim(
                            planning_run, claim_observed_at
                        )
                    )
                    or _planning_run_lease_expired(
                        planning_run, claim_observed_at
                    )
                )
            ]
            if not candidates:
                return {
                    "Endpoint": endpoint,
                    "StatusCode": 200,
                    "Data": {"PlanningRun": None},
                }
            planning_run = min(
                candidates,
                key=lambda item: str(
                    item.get("EnqueuedAt") or item["RequestedAt"]
                ),
            )
            recovered = planning_run["Status"] == "Running"
            lease_token = token_urlsafe(24)
            claimed_run = dict(planning_run)
            claimed_run.pop("LeaseToken", None)
            if recovered:
                claimed_run.pop("ExecutionTokenHash", None)
                claimed_run.pop("ExecutionClaimedAt", None)
                claimed_run.pop("ExecutionClaimedBy", None)
                claimed_run.pop("ExecutionClaimExpiresAt", None)
                claimed_run["ExecutionClaimInvalidatedAt"] = (
                    claim_observed_at.isoformat()
                )
                claimed_run["ExecutionClaimInvalidationReason"] = (
                    "ExpiredLeaseRecovery"
                )
            claimed_run.update(
                {
                    "Status": "Running",
                    "WorkerID": payload.WorkerID,
                    "LeaseTokenHash": _lease_token_hash(lease_token),
                    "LeaseClaimedAt": payload.ClaimedAt.isoformat(),
                    "LeaseExpiresAt": (
                        claim_observed_at
                        + timedelta(seconds=payload.LeaseSeconds)
                    ).isoformat(),
                    "LeaseSeconds": payload.LeaseSeconds,
                    "AttemptCount": int(
                        planning_run.get("AttemptCount", 0)
                    )
                    + 1,
                    "RecoveredFromExpiredLease": recovered,
                }
            )
            claimed_run["StatusHistory"] = [
                *planning_run["StatusHistory"],
                {
                    "Status": "Running",
                    "ChangedAt": payload.ClaimedAt.isoformat(),
                    "ChangedBy": payload.WorkerID,
                    "Reason": (
                        "ExpiredLeaseRecovery" if recovered else "WorkerClaim"
                    ),
                },
            ]
            planning_runs[str(planning_run["RunID"])] = claimed_run
            _append_planning_run_audit_event(
                audit_events=audit_events,
                run_id=str(planning_run["RunID"]),
                action=(
                    "PlanningRunLeaseRecovered"
                    if recovered
                    else "PlanningRunClaimed"
                ),
                actor_id=_effective_actor_id(request, payload.WorkerID),
                occurred_at=payload.ClaimedAt,
                details={"AttemptCount": claimed_run["AttemptCount"]},
            )
            claimed_response = _planning_run_public_record(claimed_run)
            claimed_response["LeaseToken"] = lease_token
            return {
                "Endpoint": endpoint,
                "StatusCode": 200,
                "Data": {"PlanningRun": claimed_response},
            }

    @app.post("/planner/workbench/planning-runs/{run_id}/execute")
    def planner_workbench_planning_run_execute(
        run_id: str,
        payload: PlanningRunExecutionPayload,
        request: Request,
    ):
        endpoint = f"/planner/workbench/planning-runs/{run_id}/execute"
        identity_error = _worker_identity_mismatch_response(
            request=request,
            claimed_worker_id=payload.ExecutedBy,
            endpoint=endpoint,
        )
        if identity_error is not None:
            return identity_error
        expected_revision = (
            None
            if getattr(request.state, "skip_execution_if_match", False)
            else _client_revision_from_if_match(request.headers.get("if-match"))
        )
        execution_token_hash = _lease_token_hash(token_urlsafe(24))

        def persist_execution_claim() -> dict[str, object]:
            claim_observed_at = server_utc_now()
            planning_run = planning_runs.get(run_id)
            if planning_run is None:
                raise _StoreManagedRequestRejected(
                    _planning_run_not_found(endpoint=endpoint, run_id=run_id)
                )
            if planning_run.get("SolverBackendID") in PAUSED_SOLVER_BACKEND_IDS:
                raise _StoreManagedRequestRejected(
                    JSONResponse(
                        status_code=409,
                        content={
                            "Endpoint": endpoint,
                            "StatusCode": 409,
                            "Data": {
                                "RunID": run_id,
                                "SolverBackendID": planning_run.get(
                                    "SolverBackendID"
                                ),
                                "Status": "SolverBackendPaused",
                                "Message": (
                                    "Paused solver runs must be copied to a new "
                                    "CP-SAT planning run."
                                ),
                            },
                        },
                    )
                )
            direct_execution = planning_run.get("Status") == "Pending"
            worker_execution = planning_run.get("Status") == "Running"
            if not direct_execution and not worker_execution:
                raise _StoreManagedRequestRejected(
                    _planning_run_transition_conflict(
                        endpoint=endpoint,
                        planning_run=planning_run,
                        message=(
                            f"Planning run {run_id} is not pending and cannot be "
                            "executed."
                        ),
                    )
                )
            if planning_run.get("ExecutionTokenHash"):
                raise _StoreManagedRequestRejected(
                    JSONResponse(
                        status_code=409,
                        content={
                            "Endpoint": endpoint,
                            "StatusCode": 409,
                            "Data": {
                                "RunID": run_id,
                                "Status": "PlanningRunExecutionAlreadyClaimed",
                                "ExecutionVersion": planning_run.get(
                                    "ExecutionVersion"
                                ),
                                "Message": (
                                    "Planning run already has a persisted execution "
                                    "owner."
                                ),
                            },
                        },
                    )
                )
            if worker_execution:
                lease_error = _planning_run_execution_lease_error(
                    planning_run=planning_run,
                    executed_by=payload.ExecutedBy,
                    lease_token=payload.LeaseToken,
                    observed_at=claim_observed_at,
                )
                if lease_error is not None:
                    raise _StoreManagedRequestRejected(
                        JSONResponse(
                            status_code=409,
                            content={
                                "Endpoint": endpoint,
                                "StatusCode": 409,
                                "Data": {"RunID": run_id, **lease_error},
                            },
                        )
                    )

            execution_version = int(planning_run.get("ExecutionVersion", 0)) + 1
            execution_claim_expires_at = (
                str(planning_run["LeaseExpiresAt"])
                if worker_execution
                else (
                    claim_observed_at
                    + timedelta(
                        seconds=(
                            payload.TimeLimitSeconds
                            + _DIRECT_EXECUTION_CLAIM_GRACE_SECONDS
                        )
                    )
                ).isoformat()
            )
            claimed_execution_run = deepcopy(planning_run)
            claimed_execution_run.update(
                {
                    "Status": "Running",
                    "ExecutionVersion": execution_version,
                    "ExecutionTokenHash": execution_token_hash,
                    "ExecutionClaimedAt": payload.StartedAt.isoformat(),
                    "ExecutionClaimedBy": payload.ExecutedBy,
                    "ExecutionClaimExpiresAt": execution_claim_expires_at,
                }
            )
            claimed_status_history = list(planning_run["StatusHistory"])
            if direct_execution:
                claimed_status_history.append(
                    {
                        "Status": "Running",
                        "ChangedAt": payload.StartedAt.isoformat(),
                        "ChangedBy": payload.ExecutedBy,
                        "Reason": "DirectExecution",
                    }
                )
            claimed_execution_run["StatusHistory"] = claimed_status_history
            planning_runs[run_id] = claimed_execution_run
            return {
                "PlanningRun": deepcopy(claimed_execution_run),
                "MasterDataVersion": deepcopy(
                    master_data_versions[
                        str(claimed_execution_run["MasterDataVersionID"])
                    ]
                ),
                "OperationalSnapshot": deepcopy(
                    operational_state_snapshots[
                        str(claimed_execution_run["OperationalStateSnapshotID"])
                    ]
                ),
                "SchedulingStrategyVersions": deepcopy(
                    scheduling_strategy_versions
                ),
                "DirectExecution": direct_execution,
                "WorkerExecution": worker_execution,
                "ExecutionVersion": execution_version,
                "LeaseOwnerWorkerID": planning_run.get("WorkerID"),
                "LeaseOwnerTokenHash": planning_run.get("LeaseTokenHash"),
            }

        try:
            claim, claim_outcome = active_store.atomic_update(
                persist_execution_claim,
                expected_revision=expected_revision,
            )
            request.state.store_managed_revision = claim_outcome.revision
        except _StoreManagedRequestRejected as error:
            request.state.store_managed_revision = error.current_revision
            return error.response
        except StateStoreRevisionConflict as error:
            request.state.store_managed_revision = error.current_revision
            return _revision_conflict_response(
                endpoint=endpoint,
                expected_revision=error.expected_revision,
                current_revision=error.current_revision,
                message=(
                    "Workbench state changed before the execution claim was "
                    "persisted."
                ),
            )

        planning_run = claim["PlanningRun"]
        master_data_version = claim["MasterDataVersion"]
        operational_snapshot = claim["OperationalSnapshot"]
        execution_request = _planning_run_payload_from_record(planning_run)
        solve_started_at = monotonic()
        try:
            solver_result = _execute_planning_run(
                payload=execution_request,
                master_data_version=master_data_version,
                operational_snapshot=operational_snapshot,
                solver_time_limit_seconds=payload.TimeLimitSeconds,
                scheduling_strategy_versions=claim["SchedulingStrategyVersions"],
                frozen_scheduling_strategy=planning_run.get("FrozenSchedulingStrategy"),
                frozen_base_calendars=(
                    planning_run.get("FrozenBaseCalendars")
                    if isinstance(planning_run.get("FrozenBaseCalendars"), list)
                    else []
                ),
                frozen_resource_calendar_assignments=(
                    planning_run.get("FrozenResourceCalendarAssignments")
                    if isinstance(
                        planning_run.get("FrozenResourceCalendarAssignments"), list
                    )
                    else []
                ),
                frozen_calendar_overrides=(
                    planning_run.get("FrozenCalendarOverrides")
                    if isinstance(planning_run.get("FrozenCalendarOverrides"), list)
                    else []
                ),
                release_policy=(
                    planning_run.get("FrozenReleasePolicy")
                    if isinstance(planning_run.get("FrozenReleasePolicy"), dict)
                    else None
                ),
            )
        except Exception as error:
            solver_result = {
                "Status": "Failed",
                "SolverStatus": "Error",
                "SolverMessage": str(error),
                "Schedule": None,
            }
        observed_completed_at = payload.StartedAt + timedelta(
            seconds=max(0.0, monotonic() - solve_started_at)
        )
        completed_at = max(
            observed_completed_at,
            payload.CompletedAt or observed_completed_at,
        )

        def persist_execution_finalization() -> dict[str, object]:
            finalization_observed_at = server_utc_now()
            live_execution_run = planning_runs.get(run_id)
            ownership_matches = (
                live_execution_run is not None
                and live_execution_run.get("Status") == "Running"
                and live_execution_run.get("ExecutionVersion")
                == claim["ExecutionVersion"]
                and live_execution_run.get("ExecutionClaimedBy")
                == payload.ExecutedBy
                and compare_digest(
                    str(live_execution_run.get("ExecutionTokenHash") or ""),
                    execution_token_hash,
                )
            )
            if ownership_matches and claim["WorkerExecution"]:
                ownership_matches = (
                    live_execution_run.get("WorkerID")
                    == claim["LeaseOwnerWorkerID"]
                    and compare_digest(
                        str(live_execution_run.get("LeaseTokenHash") or ""),
                        str(claim["LeaseOwnerTokenHash"] or ""),
                    )
                )
            if not ownership_matches:
                raise _StoreManagedRequestRejected(
                    JSONResponse(
                        status_code=409,
                        content={
                            "Endpoint": endpoint,
                            "StatusCode": 409,
                            "Data": {
                                "RunID": run_id,
                                "Status": "PlanningRunExecutionOwnershipLost",
                                "ExecutionVersion": claim["ExecutionVersion"],
                                "Message": (
                                    "Planning run execution or lease ownership changed "
                                    "before finalization."
                                ),
                            },
                        },
                    )
                )
            expiry_error = _planning_run_execution_claim_expiry_error(
                planning_run=live_execution_run,
                observed_at=finalization_observed_at,
                worker_execution=bool(claim["WorkerExecution"]),
            )
            if expiry_error is not None:
                raise _StoreManagedRequestRejected(
                    JSONResponse(
                        status_code=409,
                        content={
                            "Endpoint": endpoint,
                            "StatusCode": 409,
                            "Data": {"RunID": run_id, **expiry_error},
                        },
                    )
                )

            completed_run = {**deepcopy(live_execution_run), **deepcopy(solver_result)}
            status_history = list(live_execution_run["StatusHistory"])
            completed_run.update(
                {
                    "StartedAt": payload.StartedAt.isoformat(),
                    "CompletedAt": completed_at.isoformat(),
                    "ExecutedBy": payload.ExecutedBy,
                    "TimeLimitSeconds": payload.TimeLimitSeconds,
                }
            )
            if (
                completed_run["Status"] == "Completed"
                and completed_run.get("PublicationStatus") is None
            ):
                completed_run["PublicationStatus"] = "Draft"
            if claim["WorkerExecution"] and completed_run["Status"] == "Failed":
                completed_run = _apply_planning_run_failure_policy(
                    planning_run=completed_run,
                    failed_at=finalization_observed_at,
                )
            reservation_fields_present = (
                "PlanningReservationBatchIDs" in completed_run
                or "FrozenPlanningReservations" in completed_run
            )
            selected_value = completed_run.get("PlanningReservationBatchIDs", [])
            selected_run_batch_ids = (
                list(selected_value) if isinstance(selected_value, list) else []
            )
            frozen_planning_reservations = completed_run.get(
                "FrozenPlanningReservations"
            )
            frozen_transition_graph = (
                frozen_planning_reservations
                if isinstance(frozen_planning_reservations, Mapping)
                else {}
            )
            frozen_batch_ids_value = frozen_transition_graph.get(
                "ReservationBatchIDs"
            )
            frozen_batch_ids = (
                list(frozen_batch_ids_value)
                if isinstance(frozen_batch_ids_value, list)
                else list(selected_run_batch_ids)
            )
            reservation_audit_details: dict[str, object] = {}
            reservation_error: dict[str, object] | None = None
            transitioned = None
            reservation_transition_attempted = (
                reservation_fields_present
                and completed_run["Status"]
                in {"Completed", "Failed", "DeadLetter"}
            )
            if not isinstance(selected_value, list):
                reservation_error = {
                    "Status": "PlanningReservationGraphDrift",
                    "ReservationBatchIDs": [],
                    "Message": (
                        "Planning Run selected reservation batch IDs must be a list."
                    ),
                }
                completed_run.update(
                    {
                        "Status": "Failed",
                        "SolverStatus": "Error",
                        "SolverMessage": reservation_error["Message"],
                        "PublicationStatus": None,
                        "PlanningError": deepcopy(reservation_error),
                    }
                )
            elif reservation_transition_attempted:
                try:
                    transitioned = transition_planning_reservations_for_run(
                        run_id=run_id,
                        run_status=str(completed_run["Status"]),
                        occurred_at=completed_at,
                        batch_ids=selected_run_batch_ids,
                        frozen_reservations=frozen_transition_graph,
                        schedule=(
                            completed_run.get("Schedule")
                            if isinstance(completed_run.get("Schedule"), dict)
                            else None
                        ),
                        demand_commitments=planning_demand_commitments,
                        batches=planning_reservation_batches,
                        capacity_reservations=ccr_capacity_reservations,
                        material_allocations=material_planning_allocations,
                    )
                except ScheduledOccupancyEvidenceError as error:
                    reservation_error = {
                        "Status": "PlanningReservationScheduledOccupancyIncomplete",
                        "CapacityReservationIDs": list(
                            error.capacity_reservation_ids
                        ),
                        "Reasons": error.reasons,
                        "Message": str(error),
                    }
                    completed_run.update(
                        {
                            "Status": "Failed",
                            "SolverStatus": "Error",
                            "SolverMessage": str(error),
                            "PublicationStatus": None,
                            "PlanningError": deepcopy(reservation_error),
                        }
                    )
                    try:
                        transitioned = transition_planning_reservations_for_run(
                            run_id=run_id,
                            run_status="Failed",
                            occurred_at=completed_at,
                            batch_ids=selected_run_batch_ids,
                            frozen_reservations=frozen_transition_graph,
                            demand_commitments=planning_demand_commitments,
                            batches=planning_reservation_batches,
                            capacity_reservations=ccr_capacity_reservations,
                            material_allocations=material_planning_allocations,
                        )
                    except ReservationBatchReferenceError as drift_error:
                        reservation_error = {
                            "Status": "PlanningReservationGraphDrift",
                            "ReservationBatchIDs": list(frozen_batch_ids),
                            "Message": str(drift_error),
                        }
                        completed_run["SolverMessage"] = str(drift_error)
                        completed_run["PlanningError"] = deepcopy(
                            reservation_error
                        )
                except ReservationGraphMigrationRequiredError as error:
                    persisted_legacy_graph = deepcopy(
                        dict(frozen_transition_graph)
                    )
                    persisted_legacy_graph.setdefault(
                        "GraphFormat", LEGACY_GRAPH_FORMAT
                    )
                    completed_run["FrozenPlanningReservations"] = (
                        persisted_legacy_graph
                    )
                    reservation_error = {
                        "Status": error.status,
                        "ReservationBatchIDs": list(frozen_batch_ids),
                        "GraphFormat": persisted_legacy_graph.get("GraphFormat"),
                        "RequiredGraphFormat": GRAPH_FORMAT,
                        "Message": str(error),
                    }
                    completed_run.update(
                        {
                            "Status": "Failed",
                            "SolverStatus": "Error",
                            "SolverMessage": str(error),
                            "PublicationStatus": None,
                            "PlanningError": deepcopy(reservation_error),
                        }
                    )
                except (
                    ReservationGraphDriftError,
                    ReservationBatchReferenceError,
                ) as error:
                    reservation_error = {
                        "Status": "PlanningReservationGraphDrift",
                        "ReservationBatchIDs": list(frozen_batch_ids),
                        "Message": str(error),
                    }
                    completed_run.update(
                        {
                            "Status": "Failed",
                            "SolverStatus": "Error",
                            "SolverMessage": str(error),
                            "PublicationStatus": None,
                            "PlanningError": deepcopy(reservation_error),
                        }
                    )
                if transitioned is not None:
                    planning_reservation_batches.clear()
                    planning_reservation_batches.update(transitioned["Batches"])
                    ccr_capacity_reservations.clear()
                    ccr_capacity_reservations.update(
                        transitioned["CapacityReservations"]
                    )
                    material_planning_allocations.clear()
                    material_planning_allocations.update(
                        transitioned["MaterialAllocations"]
                    )
            if reservation_transition_attempted:
                if reservation_error is not None:
                    detail_name = (
                        "PlanningReservationsHeldForError"
                        if transitioned is not None
                        else "PlanningReservationsPreservedForGraphDrift"
                    )
                else:
                    detail_name = (
                        "PlanningReservationsConverted"
                        if completed_run["Status"] == "Completed"
                        else "PlanningReservationsHeldForError"
                    )
                reservation_audit_details[detail_name] = list(frozen_batch_ids)
            status_history.append(
                {
                    "Status": completed_run["Status"],
                    "ChangedAt": completed_at.isoformat(),
                    "ChangedBy": payload.ExecutedBy,
                    "Reason": completed_run.get("DeadLetterReason")
                    or (
                        completed_run.get("PlanningError", {}).get("Status")
                        if isinstance(completed_run.get("PlanningError"), dict)
                        else None
                    )
                    or (
                        "RetryScheduled"
                        if completed_run["Status"] == "Queued"
                        else "ExecutionFinished"
                    ),
                }
            )
            completed_run["StatusHistory"] = status_history
            completed_run.pop("ExecutionTokenHash", None)
            completed_run.pop("ExecutionClaimExpiresAt", None)
            completed_run["CompletedExecutionVersion"] = claim["ExecutionVersion"]
            planning_runs[run_id] = completed_run
            _append_planning_run_audit_event(
                audit_events=audit_events,
                run_id=run_id,
                action="PlanningRunExecuted",
                actor_id=_effective_actor_id(request, payload.ExecutedBy),
                occurred_at=completed_at,
                details={
                    "Status": completed_run["Status"],
                    "SolverStatus": completed_run.get("SolverStatus"),
                    "AttemptCount": completed_run.get("AttemptCount", 0),
                    **(
                        {"PlanningError": deepcopy(reservation_error)}
                        if reservation_error is not None
                        else {}
                    ),
                    **reservation_audit_details,
                },
            )
            return {
                "PlanningRun": deepcopy(completed_run),
                "ReservationError": deepcopy(reservation_error),
            }

        def persist_direct_finalization_error(
            finalization_error: Exception,
        ) -> dict[str, object]:
            live_execution_run = planning_runs.get(run_id)
            ownership_matches = (
                live_execution_run is not None
                and live_execution_run.get("Status") == "Running"
                and live_execution_run.get("ExecutionVersion")
                == claim["ExecutionVersion"]
                and live_execution_run.get("ExecutionClaimedBy")
                == payload.ExecutedBy
                and compare_digest(
                    str(live_execution_run.get("ExecutionTokenHash") or ""),
                    execution_token_hash,
                )
            )
            if not ownership_matches:
                raise RuntimeError(
                    "Direct execution ownership changed before finalization error "
                    "compensation."
                )
            failed_run = deepcopy(live_execution_run)
            failed_run.update(
                {
                    "Status": "Failed",
                    "SolverStatus": "Error",
                    "SolverMessage": (
                        "Planning run finalization failed: "
                        f"{finalization_error}"
                    ),
                    "PlanningError": {
                        "Status": "PlanningRunFinalizationError",
                        "Message": str(finalization_error),
                    },
                    "StartedAt": payload.StartedAt.isoformat(),
                    "CompletedAt": completed_at.isoformat(),
                    "ExecutedBy": payload.ExecutedBy,
                    "TimeLimitSeconds": payload.TimeLimitSeconds,
                    "ExecutionClaimInvalidatedAt": completed_at.isoformat(),
                    "ExecutionClaimInvalidationReason": "FinalizationError",
                }
            )
            failed_run.pop("ExecutionTokenHash", None)
            failed_run.pop("ExecutionClaimExpiresAt", None)
            failed_run["StatusHistory"] = [
                *live_execution_run["StatusHistory"],
                {
                    "Status": "Failed",
                    "ChangedAt": completed_at.isoformat(),
                    "ChangedBy": payload.ExecutedBy,
                    "Reason": "FinalizationError",
                },
            ]
            planning_runs[run_id] = failed_run
            _append_planning_run_audit_event(
                audit_events=audit_events,
                run_id=run_id,
                action="PlanningRunFinalizationFailed",
                actor_id=_effective_actor_id(request, payload.ExecutedBy),
                occurred_at=completed_at,
                details={
                    "ExecutionVersion": claim["ExecutionVersion"],
                    "Message": str(finalization_error),
                },
            )
            return deepcopy(failed_run)

        try:
            finalization, finalization_outcome = active_store.atomic_update(
                persist_execution_finalization
            )
            request.state.store_managed_revision = finalization_outcome.revision
        except _StoreManagedRequestRejected as error:
            request.state.store_managed_revision = error.current_revision
            return error.response
        except StateStoreRevisionConflict as error:
            request.state.store_managed_revision = error.current_revision
            return _revision_conflict_response(
                endpoint=endpoint,
                expected_revision=error.expected_revision,
                current_revision=error.current_revision,
                message=(
                    "Workbench state changed before execution finalization; the "
                    "persisted execution owner was not overwritten."
                ),
            )
        except Exception as error:
            if claim["DirectExecution"]:
                _, compensation_outcome = active_store.atomic_update(
                    lambda: persist_direct_finalization_error(error)
                )
                request.state.store_managed_revision = compensation_outcome.revision
            raise

        completed_run = finalization["PlanningRun"]
        reservation_error = finalization["ReservationError"]
        if reservation_error is not None:
            return JSONResponse(
                status_code=409,
                content={
                    "Endpoint": endpoint,
                    "StatusCode": 409,
                    "Data": {
                        **reservation_error,
                        "PlanningRun": _planning_run_public_record(
                            completed_run
                        ),
                    },
                },
            )
        return {
            "Endpoint": endpoint,
            "StatusCode": 200,
            "Data": {"PlanningRun": _planning_run_public_record(completed_run)},
        }

    @app.post("/planner/workbench/planning-runs/{run_id}/process-queued")
    def planner_workbench_planning_run_process_queued(
        run_id: str,
        payload: PlanningRunProcessQueuedPayload,
        request: Request,
    ):
        endpoint = f"/planner/workbench/planning-runs/{run_id}/process-queued"
        identity_error = _worker_identity_mismatch_response(
            request=request,
            claimed_worker_id=payload.WorkerID,
            endpoint=endpoint,
        )
        if identity_error is not None:
            return identity_error
        lease_token = token_urlsafe(24)

        def persist_interactive_worker_claim() -> None:
            claim_observed_at = server_utc_now()
            planning_run = planning_runs.get(run_id)
            if planning_run is None:
                raise _StoreManagedRequestRejected(
                    _planning_run_not_found(endpoint=endpoint, run_id=run_id)
                )
            if planning_run.get("SolverBackendID") in PAUSED_SOLVER_BACKEND_IDS:
                raise _StoreManagedRequestRejected(
                    JSONResponse(
                        status_code=409,
                        content={
                            "Endpoint": endpoint,
                            "StatusCode": 409,
                            "Data": {
                                "RunID": run_id,
                                "SolverBackendID": planning_run.get(
                                    "SolverBackendID"
                                ),
                                "Status": "SolverBackendPaused",
                                "Message": (
                                    "Paused solver runs must be copied to a new "
                                    "CP-SAT planning run."
                                ),
                            },
                        },
                    )
                )
            if planning_run.get("Status") != "Queued":
                raise _StoreManagedRequestRejected(
                    _planning_run_transition_conflict(
                        endpoint=endpoint,
                        planning_run=planning_run,
                        message=(
                            f"Planning run {run_id} is not queued and cannot be "
                            "processed by the interactive worker."
                        ),
                    )
                )
            if not _planning_run_ready_for_claim(
                planning_run, claim_observed_at
            ):
                raise _StoreManagedRequestRejected(
                    JSONResponse(
                        status_code=409,
                        content={
                            "Endpoint": endpoint,
                            "StatusCode": 409,
                            "Data": {
                                "RunID": run_id,
                                "Status": "PlanningRunNotReadyForClaim",
                                "NextAttemptAt": planning_run.get("NextAttemptAt"),
                            },
                        },
                    )
                )
            claimed_run = dict(planning_run)
            claimed_run.pop("LeaseToken", None)
            claimed_run.update(
                {
                    "Status": "Running",
                    "WorkerID": payload.WorkerID,
                    "LeaseTokenHash": _lease_token_hash(lease_token),
                    "LeaseClaimedAt": payload.ProcessedAt.isoformat(),
                    "LeaseExpiresAt": (
                        claim_observed_at
                        + timedelta(seconds=payload.LeaseSeconds)
                    ).isoformat(),
                    "LeaseSeconds": payload.LeaseSeconds,
                    "AttemptCount": int(planning_run.get("AttemptCount", 0)) + 1,
                    "RecoveredFromExpiredLease": False,
                }
            )
            claimed_run["StatusHistory"] = [
                *planning_run["StatusHistory"],
                {
                    "Status": "Running",
                    "ChangedAt": payload.ProcessedAt.isoformat(),
                    "ChangedBy": payload.WorkerID,
                    "Reason": "InteractiveWorkerClaim",
                },
            ]
            planning_runs[run_id] = claimed_run
            _append_planning_run_audit_event(
                audit_events=audit_events,
                run_id=run_id,
                action="PlanningRunClaimed",
                actor_id=_effective_actor_id(request, payload.WorkerID),
                occurred_at=payload.ProcessedAt,
                details={
                    "AttemptCount": claimed_run["AttemptCount"],
                    "Mode": "InteractiveWorker",
                },
            )

        try:
            _, claim_outcome = active_store.atomic_update(
                persist_interactive_worker_claim,
                expected_revision=_client_revision_from_if_match(
                    request.headers.get("if-match")
                )
            )
            request.state.store_managed_revision = claim_outcome.revision
        except _StoreManagedRequestRejected as error:
            request.state.store_managed_revision = error.current_revision
            return error.response
        except StateStoreRevisionConflict as error:
            request.state.store_managed_revision = error.current_revision
            return _revision_conflict_response(
                endpoint=endpoint,
                expected_revision=error.expected_revision,
                current_revision=error.current_revision,
                message="Workbench state changed before the worker claim persisted.",
            )
        request.state.skip_execution_if_match = True
        execution_response = planner_workbench_planning_run_execute(
            run_id,
            PlanningRunExecutionPayload(
                ExecutedBy=payload.WorkerID,
                StartedAt=payload.ProcessedAt,
                TimeLimitSeconds=payload.TimeLimitSeconds,
                LeaseToken=lease_token,
            ),
            request,
        )
        if isinstance(execution_response, JSONResponse):
            return execution_response
        execution_response["Endpoint"] = endpoint
        execution_response["Data"]["WorkerLifecycle"] = {
            "WorkerID": payload.WorkerID,
            "ClaimedAt": payload.ProcessedAt.isoformat(),
            "ExecutionMode": "InteractiveWorker",
        }
        return execution_response

    @app.post("/planner/workbench/planning-runs/{run_id}/renew-lease")
    def planner_workbench_planning_run_renew_lease(
        run_id: str,
        payload: PlanningRunLeaseRenewalPayload,
        request: Request,
    ):
        endpoint = f"/planner/workbench/planning-runs/{run_id}/renew-lease"
        identity_error = _worker_identity_mismatch_response(
            request=request,
            claimed_worker_id=payload.WorkerID,
            endpoint=endpoint,
        )
        if identity_error is not None:
            return identity_error

        def persist_lease_renewal() -> dict[str, object]:
            renewal_observed_at = server_utc_now()
            planning_run = planning_runs.get(run_id)
            if planning_run is None:
                raise _StoreManagedRequestRejected(
                    _planning_run_not_found(endpoint=endpoint, run_id=run_id)
                )
            if planning_run["Status"] != "Running":
                raise _StoreManagedRequestRejected(
                    _planning_run_transition_conflict(
                        endpoint=endpoint,
                        planning_run=planning_run,
                        message=(
                            f"Planning run {run_id} is not running and cannot renew "
                            "a lease."
                        ),
                    )
                )
            lease_error = _planning_run_execution_lease_error(
                planning_run=planning_run,
                executed_by=payload.WorkerID,
                lease_token=payload.LeaseToken,
                observed_at=renewal_observed_at,
            )
            if lease_error is not None:
                raise _StoreManagedRequestRejected(
                    JSONResponse(
                        status_code=409,
                        content={
                            "Endpoint": endpoint,
                            "StatusCode": 409,
                            "Data": {"RunID": run_id, **lease_error},
                        },
                    )
                )
            renewed_run = dict(planning_run)
            renewed_expires_at = (
                renewal_observed_at + timedelta(seconds=payload.LeaseSeconds)
            ).isoformat()
            renewed_run.update(
                {
                    "LastHeartbeatAt": payload.RenewedAt.isoformat(),
                    "LeaseExpiresAt": renewed_expires_at,
                    "LeaseSeconds": payload.LeaseSeconds,
                    "LeaseRenewalCount": int(
                        planning_run.get("LeaseRenewalCount", 0)
                    )
                    + 1,
                }
            )
            if renewed_run.get("ExecutionTokenHash"):
                renewed_run["ExecutionClaimExpiresAt"] = renewed_expires_at
            planning_runs[run_id] = renewed_run
            _append_planning_run_audit_event(
                audit_events=audit_events,
                run_id=run_id,
                action="PlanningRunLeaseRenewed",
                actor_id=_effective_actor_id(request, payload.WorkerID),
                occurred_at=payload.RenewedAt,
                details={"LeaseRenewalCount": renewed_run["LeaseRenewalCount"]},
            )
            return deepcopy(renewed_run)

        try:
            renewed_run, renewal_outcome = active_store.atomic_update(
                persist_lease_renewal,
                expected_revision=_client_revision_from_if_match(
                    request.headers.get("if-match")
                ),
            )
            request.state.store_managed_revision = renewal_outcome.revision
        except _StoreManagedRequestRejected as error:
            request.state.store_managed_revision = error.current_revision
            return error.response
        except StateStoreRevisionConflict as error:
            request.state.store_managed_revision = error.current_revision
            return _revision_conflict_response(
                endpoint=endpoint,
                expected_revision=error.expected_revision,
                current_revision=error.current_revision,
                message="Workbench state changed before lease renewal persisted.",
            )
        return {
            "Endpoint": endpoint,
            "StatusCode": 200,
            "Data": {"PlanningRun": _planning_run_public_record(renewed_run)},
        }

    @app.post("/planner/workbench/planning-runs/{run_id}/cancel")
    def planner_workbench_planning_run_cancel(
        run_id: str,
        payload: PlanningRunCancellationPayload,
        request: Request,
    ):
        endpoint = f"/planner/workbench/planning-runs/{run_id}/cancel"
        planning_run = planning_runs.get(run_id)
        if planning_run is None:
            return _planning_run_not_found(endpoint=endpoint, run_id=run_id)
        if planning_run["Status"] != "Pending":
            return _planning_run_transition_conflict(
                endpoint=endpoint,
                planning_run=planning_run,
                message=f"Planning run {run_id} is not pending and cannot be cancelled.",
            )
        cancelled_run = dict(planning_run)
        cancelled_run.update(
            {
                "Status": "Cancelled",
                "CancelledBy": payload.CancelledBy,
                "CancelledAt": payload.CancelledAt.isoformat(),
                "CancellationReason": payload.Reason,
                "SolverStatus": "Cancelled",
                "SolverMessage": payload.Reason,
            }
        )
        cancelled_run["StatusHistory"] = [
            *planning_run["StatusHistory"],
            {
                "Status": "Cancelled",
                "ChangedAt": payload.CancelledAt.isoformat(),
                "ChangedBy": payload.CancelledBy,
            },
        ]
        planning_runs[run_id] = cancelled_run
        _append_planning_run_audit_event(
            audit_events=audit_events,
            run_id=run_id,
            action="PlanningRunCancelled",
            actor_id=_effective_actor_id(request, payload.CancelledBy),
            occurred_at=payload.CancelledAt,
            details={"Reason": payload.Reason},
        )
        return {
            "Endpoint": endpoint,
            "StatusCode": 200,
            "Data": {"PlanningRun": _planning_run_public_record(cancelled_run)},
        }

    @app.post("/planner/workbench/planning-runs/{run_id}/recover")
    def planner_workbench_planning_run_recover(
        run_id: str,
        payload: PlanningRunRecoveryPayload,
        request: Request,
    ):
        endpoint = f"/planner/workbench/planning-runs/{run_id}/recover"
        planning_run = planning_runs.get(run_id)
        if planning_run is None:
            return _planning_run_not_found(endpoint=endpoint, run_id=run_id)
        recovery_source_status = str(planning_run["Status"])
        if recovery_source_status not in {"DeadLetter", "Failed"}:
            return _planning_run_transition_conflict(
                endpoint=endpoint,
                planning_run=planning_run,
                message=(
                    f"Planning run {run_id} is neither failed nor dead-lettered "
                    "and cannot be recovered."
                ),
            )
        recovered_run = dict(planning_run)
        previous_failure = {
            "Status": recovery_source_status,
            "FailedAt": planning_run.get("CompletedAt"),
            "Reason": planning_run.get("DeadLetterReason")
            or planning_run.get("SolverMessage"),
            "AttemptCount": planning_run.get("AttemptCount"),
            "LastFailure": planning_run.get("LastFailure"),
            "PlanningError": deepcopy(planning_run.get("PlanningError")),
        }
        recovered_run.update(
            {
                "Status": "Queued",
                "AttemptCount": (
                    0
                    if payload.ResetAttempts
                    else int(planning_run.get("AttemptCount", 0))
                ),
                "NextAttemptAt": payload.RecoveredAt.isoformat(),
                "RecoveredBy": payload.RecoveredBy,
                "RecoveredAt": payload.RecoveredAt.isoformat(),
                "RecoveryReason": payload.Reason,
                "DeadLetterAt": None,
                "DeadLetterReason": None,
                "SolverStatus": "Pending",
                "SolverMessage": (
                    f"{recovery_source_status} planning run recovered for retry."
                ),
                "PreviousFailure": previous_failure,
                "PlanningError": None,
            }
        )
        for ownership_field in (
            "ExecutionTokenHash",
            "ExecutionClaimExpiresAt",
            "LeaseTokenHash",
            "LeaseExpiresAt",
        ):
            recovered_run.pop(ownership_field, None)
        if recovery_source_status == "DeadLetter":
            recovered_run["PreviousDeadLetter"] = {
                "DeadLetterAt": planning_run.get("DeadLetterAt"),
                "Reason": planning_run.get("DeadLetterReason"),
                "AttemptCount": planning_run.get("AttemptCount"),
                "LastFailure": planning_run.get("LastFailure"),
            }
        recovered_run["StatusHistory"] = [
            *planning_run["StatusHistory"],
            {
                "Status": "Queued",
                "ChangedAt": payload.RecoveredAt.isoformat(),
                "ChangedBy": payload.RecoveredBy,
                "Reason": f"{recovery_source_status}Recovery",
            },
        ]
        planning_runs[run_id] = recovered_run
        _append_planning_run_audit_event(
            audit_events=audit_events,
            run_id=run_id,
            action=(
                "PlanningRunDeadLetterRecovered"
                if recovery_source_status == "DeadLetter"
                else "PlanningRunFailedRecovered"
            ),
            actor_id=_effective_actor_id(request, payload.RecoveredBy),
            occurred_at=payload.RecoveredAt,
            details={
                "Reason": payload.Reason,
                "ResetAttempts": payload.ResetAttempts,
                "RecoveredFromStatus": recovery_source_status,
            },
        )
        return {
            "Endpoint": endpoint,
            "StatusCode": 200,
            "Data": {"PlanningRun": _planning_run_public_record(recovered_run)},
        }

    @app.get("/planner/workbench/planning-runs")
    def planner_workbench_planning_run_list(
        status: str | None = None,
        worker_id: str | None = None,
        limit: int = Query(default=50, ge=1, le=200),
        offset: int = Query(default=0, ge=0),
    ):
        endpoint = "/planner/workbench/planning-runs"
        matched = [
            planning_run
            for planning_run in planning_runs.values()
            if (status is None or planning_run["Status"] == status)
            and (worker_id is None or planning_run.get("WorkerID") == worker_id)
        ]
        matched.sort(
            key=lambda item: (str(item["RequestedAt"]), str(item["RunID"])),
            reverse=True,
        )
        page = matched[offset : offset + limit]
        return {
            "Endpoint": endpoint,
            "StatusCode": 200,
            "Data": {
                "Total": len(matched),
                "Count": len(page),
                "Offset": offset,
                "Limit": limit,
                "PlanningRuns": [
                    _planning_run_public_record(planning_run)
                    for planning_run in page
                ],
            },
        }

    @app.get("/planner/workbench/planning-runs/audit-events")
    def planner_workbench_planning_run_audit_events(
        run_id: str | None = None,
        action: str | None = None,
        limit: int = Query(default=100, ge=1, le=500),
        offset: int = Query(default=0, ge=0),
    ):
        endpoint = "/planner/workbench/planning-runs/audit-events"
        matched = [
            event
            for event in audit_events
            if (run_id is None or event["RunID"] == run_id)
            and (action is None or event["Action"] == action)
        ]
        page = matched[offset : offset + limit]
        return {
            "Endpoint": endpoint,
            "StatusCode": 200,
            "Data": {
                "Total": len(matched),
                "Count": len(page),
                "Offset": offset,
                "Limit": limit,
                "AuditEvents": page,
            },
        }

    @app.get("/planner/workbench/planning-runs/metrics")
    def planner_workbench_planning_run_metrics(
        observed_at: datetime | None = None,
    ):
        endpoint = "/planner/workbench/planning-runs/metrics"
        effective_observed_at = observed_at or datetime.now(timezone.utc)
        status_names = [
            "Pending",
            "Queued",
            "Running",
            "Completed",
            "Failed",
            "Cancelled",
            "DeadLetter",
        ]
        by_status = {
            status_name: sum(
                1
                for planning_run in planning_runs.values()
                if planning_run["Status"] == status_name
            )
            for status_name in status_names
        }
        queued_runs = [
            planning_run
            for planning_run in planning_runs.values()
            if planning_run["Status"] == "Queued"
        ]
        return {
            "Endpoint": endpoint,
            "StatusCode": 200,
            "Data": {
                "ObservedAt": effective_observed_at.isoformat(),
                "Total": len(planning_runs),
                "ByStatus": by_status,
                "QueuedReadyCount": sum(
                    1
                    for planning_run in queued_runs
                    if _planning_run_ready_for_claim(
                        planning_run, effective_observed_at
                    )
                ),
                "QueuedDelayedCount": sum(
                    1
                    for planning_run in queued_runs
                    if not _planning_run_ready_for_claim(
                        planning_run, effective_observed_at
                    )
                ),
                "RunningExpiredLeaseCount": sum(
                    1
                    for planning_run in planning_runs.values()
                    if _planning_run_lease_expired(
                        planning_run, effective_observed_at
                    )
                ),
                "DeadLetterCount": by_status["DeadLetter"],
                "RetryScheduledCount": sum(
                    1
                    for planning_run in queued_runs
                    if int(planning_run.get("AttemptCount", 0)) > 0
                ),
                "TotalAttempts": sum(
                    int(planning_run.get("AttemptCount", 0))
                    for planning_run in planning_runs.values()
                ),
            },
        }

    @app.get("/planner/workbench/planning-runs/workbench")
    def planner_workbench_planning_runs_workbench() -> dict[str, object]:
        availability = create_solver_engine(ACTIVE_SOLVER_BACKEND_ID).is_available()
        return {
            "Endpoint": "/planner/workbench/planning-runs/workbench",
            "StatusCode": 200,
            "Data": build_planning_run_workbench(
                planning_runs=list(planning_runs.values()),
                ortools_available=availability.available,
            ),
        }

    @app.get("/planner/workbench/planning-reservations/workbench")
    def planning_reservation_workbench():
        with reservation_graph_lock:
            rows: list[dict[str, object]] = []
            for batch in planning_reservation_batches.values():
                row = {
                    field: deepcopy(batch[field])
                    for field in reservation_workbench_fields
                    if field in batch
                }
                commitment = planning_demand_commitments.get(
                    str(row.get("DemandCommitmentID"))
                )
                if commitment is not None:
                    if not row.get("DemandClass"):
                        row["DemandClass"] = deepcopy(
                            commitment.get("DemandClass")
                        )
                    demand_source_type = commitment.get("DemandSourceType")
                    if demand_source_type in DEMAND_SOURCE_TYPES:
                        row["DemandSourceType"] = demand_source_type
                rows.append(row)
            rows.sort(
                key=lambda item: (
                    str(item.get("Status")),
                    str(item.get("ReservationBatchID")),
                )
            )
            summary = {
                "BatchCount": len(rows),
                "ActiveCount": sum(
                    1
                    for row in rows
                    if row.get("Status") == "ActivePlanReservation"
                ),
                "MTOCount": sum(
                    1 for row in rows if row.get("DemandClass") == "MTO"
                ),
                "MTACount": sum(
                    1 for row in rows if row.get("DemandClass") == "MTA"
                ),
                "DemandSourceTypeCounts": {
                    source_type: sum(
                        1
                        for row in rows
                        if row.get("DemandSourceType") == source_type
                    )
                    for source_type in sorted(DEMAND_SOURCE_TYPES)
                },
            }
            snapshot = {
                "Summary": summary,
                "Rows": rows,
                "Boundary": (
                    "Shared planning reservations only; not ERP/WMS inventory authority."
                ),
            }
        return {
            "Endpoint": "/planner/workbench/planning-reservations/workbench",
            "StatusCode": 200,
            "Data": snapshot,
        }

    @app.get("/planner/workbench/planning-runs/{run_id}/workbench")
    def planner_workbench_planning_run_workbench_detail(run_id: str):
        endpoint = f"/planner/workbench/planning-runs/{run_id}/workbench"
        planning_run = planning_runs.get(run_id)
        if planning_run is None:
            return _planning_run_not_found(endpoint=endpoint, run_id=run_id)
        return {
            "Endpoint": endpoint,
            "StatusCode": 200,
            "Data": build_planning_run_detail(
                planning_run=planning_run,
                audit_events=[
                    event for event in audit_events if event["RunID"] == run_id
                ],
            ),
        }

    @app.get(
        "/planner/workbench/schedule-results/runs/{run_id}/workbench"
    )
    def planner_workbench_schedule_result(run_id: str):
        endpoint = (
            f"/planner/workbench/schedule-results/runs/{run_id}/workbench"
        )
        planning_run = planning_runs.get(run_id)
        if planning_run is None:
            return _planning_run_not_found(endpoint=endpoint, run_id=run_id)
        if planning_run.get("Status") != "Completed" or not isinstance(
            planning_run.get("Schedule"), dict
        ):
            return JSONResponse(
                status_code=409,
                content={
                    "Endpoint": endpoint,
                    "StatusCode": 409,
                    "Data": {
                        "RunID": run_id,
                        "Status": "ScheduleResultUnavailable",
                        "CurrentStatus": planning_run.get("Status"),
                        "Message": "The planning run has no completed schedule result.",
                    },
                },
            )
        master_data_version = master_data_versions.get(
            str(planning_run.get("MasterDataVersionID")), {}
        )
        released_order_ids = {
            item.order_id
            for item in release_authorizations
            if item.status == "Authorized"
        }
        return {
            "Endpoint": endpoint,
            "StatusCode": 200,
            "Data": build_schedule_result_workbench(
                planning_run=planning_run,
                master_data_version=master_data_version,
                released_order_ids=released_order_ids,
            ),
        }

    @app.get(
        "/planner/workbench/schedule-results/runs/{run_id}/what-if/workspace"
    )
    def planner_workbench_schedule_result_what_if_workspace(run_id: str):
        endpoint = (
            f"/planner/workbench/schedule-results/runs/{run_id}/what-if/workspace"
        )
        planning_run = planning_runs.get(run_id)
        if planning_run is None:
            return _planning_run_not_found(endpoint=endpoint, run_id=run_id)
        if planning_run.get("Status") != "Completed" or not isinstance(
            planning_run.get("Schedule"), dict
        ):
            return JSONResponse(
                status_code=409,
                content={
                    "Endpoint": endpoint,
                    "StatusCode": 409,
                    "Data": {
                        "RunID": run_id,
                        "Status": "ScheduleResultUnavailable",
                        "CurrentStatus": planning_run.get("Status"),
                        "Message": "The planning run has no completed schedule result.",
                    },
                },
            )
        master_data_version_id = str(planning_run.get("MasterDataVersionID") or "")
        master_data_version = master_data_versions.get(master_data_version_id)
        if not isinstance(master_data_version, dict):
            return JSONResponse(
                status_code=409,
                content={
                    "Endpoint": endpoint,
                    "StatusCode": 409,
                    "Data": {
                        "RunID": run_id,
                        "Status": "SourceMasterDataUnavailable",
                        "MasterDataVersionID": master_data_version_id,
                        "Message": (
                            "The completed schedule references a master data "
                            "version that is not available for what-if evaluation."
                        ),
                    },
                },
            )
        schedule_workbench = build_schedule_result_workbench(
            planning_run=planning_run,
            master_data_version=master_data_version,
            released_order_ids={
                item.order_id
                for item in release_authorizations
                if item.status == "Authorized"
            },
        )
        return {
            "Endpoint": endpoint,
            "StatusCode": 200,
            "Data": build_sdbr_what_if_workspace(
                ccr_planned_load=schedule_workbench.get("SDBRMarketControl", {}).get(
                    "CCRPlannedLoad", {}
                ),
                ddmrp_lines=[
                    item
                    for item in (
                        master_data_version.get("DdmrpRuntimeLines")
                        or master_data_version.get("DdmrpNetFlowLines")
                        or []
                    )
                    if isinstance(item, dict)
                ],
            ),
        }

    @app.post(
        "/planner/workbench/schedule-results/runs/{run_id}/what-if/evaluate"
    )
    def planner_workbench_schedule_result_what_if_evaluate(
        run_id: str,
        payload: SdbrWhatIfScenarioPayload,
    ):
        endpoint = (
            f"/planner/workbench/schedule-results/runs/{run_id}/what-if/evaluate"
        )
        planning_run = planning_runs.get(run_id)
        if planning_run is None:
            return _planning_run_not_found(endpoint=endpoint, run_id=run_id)
        if planning_run.get("Status") != "Completed" or not isinstance(
            planning_run.get("Schedule"), dict
        ):
            return JSONResponse(
                status_code=409,
                content={
                    "Endpoint": endpoint,
                    "StatusCode": 409,
                    "Data": {
                        "RunID": run_id,
                        "Status": "ScheduleResultUnavailable",
                        "CurrentStatus": planning_run.get("Status"),
                        "Message": "The planning run has no completed schedule result.",
                    },
                },
            )
        master_data_version_id = str(planning_run.get("MasterDataVersionID") or "")
        master_data_version = master_data_versions.get(master_data_version_id)
        if not isinstance(master_data_version, dict):
            return JSONResponse(
                status_code=409,
                content={
                    "Endpoint": endpoint,
                    "StatusCode": 409,
                    "Data": {
                        "RunID": run_id,
                        "Status": "SourceMasterDataUnavailable",
                        "MasterDataVersionID": master_data_version_id,
                        "Message": (
                            "The completed schedule references a master data "
                            "version that is not available for what-if evaluation."
                        ),
                    },
                },
            )
        schedule_workbench = build_schedule_result_workbench(
            planning_run=planning_run,
            master_data_version=master_data_version,
            released_order_ids={
                item.order_id
                for item in release_authorizations
                if item.status == "Authorized"
            },
        )
        return {
            "Endpoint": endpoint,
            "StatusCode": 200,
            "Data": evaluate_sdbr_what_if_scenario(
                ccr_planned_load=schedule_workbench.get("SDBRMarketControl", {}).get(
                    "CCRPlannedLoad", {}
                ),
                scenario=payload.model_dump(mode="json"),
            ),
        }

    @app.get(
        "/planner/workbench/schedule-results/runs/{run_id}/governance"
    )
    def planner_workbench_schedule_output_governance(run_id: str):
        endpoint = (
            f"/planner/workbench/schedule-results/runs/{run_id}/governance"
        )
        planning_run = planning_runs.get(run_id)
        if planning_run is None:
            return _planning_run_not_found(endpoint=endpoint, run_id=run_id)
        return {
            "Endpoint": endpoint,
            "StatusCode": 200,
            "Data": build_schedule_output_governance(
                planning_run=planning_run,
                master_data_version=master_data_versions.get(
                    str(planning_run.get("MasterDataVersionID"))
                ),
                operational_state_snapshot=operational_state_snapshots.get(
                    str(planning_run.get("OperationalStateSnapshotID"))
                ),
                release_authorizations=release_authorizations,
                audit_events=[
                    event for event in audit_events if event["RunID"] == run_id
                ],
                simio_validation_runs=simio_validation_runs,
                superseded_by_run_id=_superseded_by_run_id(
                    run_id=run_id,
                    planning_runs=planning_runs,
                ),
            ),
        }

    @app.get(
        "/planner/workbench/schedule-results/runs/{run_id}/output-package"
    )
    def planner_workbench_schedule_output_package(run_id: str):
        endpoint = (
            f"/planner/workbench/schedule-results/runs/{run_id}/output-package"
        )
        planning_run = planning_runs.get(run_id)
        if planning_run is None:
            return _planning_run_not_found(endpoint=endpoint, run_id=run_id)
        package = build_schedule_output_package(
            planning_run=planning_run,
            master_data_version=master_data_versions.get(
                str(planning_run.get("MasterDataVersionID"))
            ),
            operational_state_snapshot=operational_state_snapshots.get(
                str(planning_run.get("OperationalStateSnapshotID"))
            ),
            release_authorizations=release_authorizations,
            audit_events=[
                event for event in audit_events if event["RunID"] == run_id
            ],
            simio_validation_runs=simio_validation_runs,
            superseded_by_run_id=_superseded_by_run_id(
                run_id=run_id,
                planning_runs=planning_runs,
            ),
        )
        if package.get("Status") == "OutputPackageUnavailable":
            return JSONResponse(
                status_code=409,
                content={
                    "Endpoint": endpoint,
                    "StatusCode": 409,
                    "Data": {
                        **package,
                        "Message": "Output package requires a completed, internally consistent schedule.",
                    },
                },
            )
        return {
            "Endpoint": endpoint,
            "StatusCode": 200,
            "Data": package,
        }

    @app.get("/planner/workbench/schedule-results/compare")
    def planner_workbench_schedule_result_compare(
        baseline_run_id: str,
        candidate_run_id: str,
    ):
        endpoint = "/planner/workbench/schedule-results/compare"
        result_views = []
        for run_id in (baseline_run_id, candidate_run_id):
            planning_run = planning_runs.get(run_id)
            if planning_run is None:
                return _planning_run_not_found(
                    endpoint=endpoint, run_id=run_id
                )
            if planning_run.get("Status") != "Completed" or not isinstance(
                planning_run.get("Schedule"), dict
            ):
                return JSONResponse(
                    status_code=409,
                    content={
                        "Endpoint": endpoint,
                        "StatusCode": 409,
                        "Data": {
                            "RunID": run_id,
                            "Status": "ScheduleResultUnavailable",
                            "Message": "Both scenarios must have completed schedule results.",
                        },
                    },
                )
            result_views.append(
                build_schedule_result_workbench(
                    planning_run=planning_run,
                    master_data_version=master_data_versions.get(
                        str(planning_run.get("MasterDataVersionID")), {}
                    ),
                )
            )
        return {
            "Endpoint": endpoint,
            "StatusCode": 200,
            "Data": compare_schedule_results(
                baseline=result_views[0], candidate=result_views[1]
            ),
        }

    @app.post("/planner/workbench/schedule-results/select")
    def planner_workbench_schedule_result_select(
        payload: ScheduleScenarioSelectionPayload,
        request: Request,
    ):
        endpoint = "/planner/workbench/schedule-results/select"
        compared_ids = {payload.BaselineRunID, payload.CandidateRunID}
        if payload.SelectedRunID not in compared_ids:
            return JSONResponse(
                status_code=409,
                content={
                    "Endpoint": endpoint,
                    "StatusCode": 409,
                    "Data": {
                        "Status": "ScenarioSelectionConflict",
                        "Message": "Selected run must be one of the compared scenarios.",
                    },
                },
            )
        for run_id in compared_ids:
            planning_run = planning_runs.get(run_id)
            if planning_run is None:
                return _planning_run_not_found(
                    endpoint=endpoint, run_id=run_id
                )
            if planning_run.get("Status") != "Completed":
                return JSONResponse(
                    status_code=409,
                    content={
                        "Endpoint": endpoint,
                        "StatusCode": 409,
                        "Data": {
                            "RunID": run_id,
                            "Status": "ScheduleResultUnavailable",
                            "Message": "Only completed schedule results can be selected.",
                        },
                    },
                )
        _append_planning_run_audit_event(
            audit_events=audit_events,
            run_id=payload.SelectedRunID,
            action="ScheduleScenarioSelected",
            actor_id=_effective_actor_id(request, payload.SelectedBy),
            occurred_at=payload.SelectedAt,
            details={
                "BaselineRunID": payload.BaselineRunID,
                "CandidateRunID": payload.CandidateRunID,
                "SelectedRunID": payload.SelectedRunID,
                "Reason": payload.Reason,
                "SelectionStatus": "SelectedForReview",
            },
        )
        return {
            "Endpoint": endpoint,
            "StatusCode": 200,
            "Data": {
                "Status": "SelectedForReview",
                "SelectedRunID": payload.SelectedRunID,
                "MessageCode": "SCHEDULE_SCENARIO_SELECTED_FOR_REVIEW",
            },
        }

    @app.get(
        "/planner/workbench/schedule-results/runs/{run_id}/work-orders/workbench"
    )
    def planner_workbench_scheduled_work_orders(run_id: str):
        endpoint = (
            f"/planner/workbench/schedule-results/runs/{run_id}"
            "/work-orders/workbench"
        )
        planning_run = planning_runs.get(run_id)
        if planning_run is None:
            return _planning_run_not_found(endpoint=endpoint, run_id=run_id)
        if planning_run.get("Status") != "Completed" or not isinstance(
            planning_run.get("Schedule"), dict
        ):
            return JSONResponse(
                status_code=409,
                content={
                    "Endpoint": endpoint,
                    "StatusCode": 409,
                    "Data": {
                        "RunID": run_id,
                        "Status": "ScheduledWorkOrdersUnavailable",
                        "Message": "Scheduled work orders require a completed planning run.",
                    },
                },
            )
        workbench = build_scheduled_work_order_workbench(
            planning_run=planning_run,
            master_data_version=master_data_versions.get(
                str(planning_run.get("MasterDataVersionID")), {}
            ),
            audit_events=[
                event for event in audit_events if event["RunID"] == run_id
            ],
            authorizations=release_authorizations,
        )
        generated_at = str(workbench["ViewMetadata"].get("GeneratedAt") or "")
        workbench["ViewMetadata"]["IsStale"] = any(
            other.get("Status") == "Completed"
            and str(
                _dict_schedule(other).get("GeneratedAt")
                or other.get("CompletedAt")
                or ""
            )
            > generated_at
            for other_id, other in planning_runs.items()
            if other_id != run_id
        )
        return {
            "Endpoint": endpoint,
            "StatusCode": 200,
            "Data": workbench,
        }

    @app.get(
        "/planner/workbench/schedule-results/runs/{run_id}"
        "/work-orders/{order_id}/workbench"
    )
    def planner_workbench_scheduled_work_order_detail(
        run_id: str, order_id: str
    ):
        endpoint = (
            f"/planner/workbench/schedule-results/runs/{run_id}"
            f"/work-orders/{order_id}/workbench"
        )
        planning_run = planning_runs.get(run_id)
        if planning_run is None:
            return _planning_run_not_found(endpoint=endpoint, run_id=run_id)
        run_audit = [
            event for event in audit_events if event["RunID"] == run_id
        ]
        master_data_version = master_data_versions.get(
            str(planning_run.get("MasterDataVersionID")), {}
        )
        workbench = build_scheduled_work_order_workbench(
            planning_run=planning_run,
            master_data_version=master_data_version,
            audit_events=run_audit,
            authorizations=release_authorizations,
        )
        detail = build_scheduled_work_order_detail(
            order_id=order_id,
            workbench=workbench,
            planning_run=planning_run,
            master_data_version=master_data_version,
            audit_events=run_audit,
            authorizations=release_authorizations,
        )
        if detail is None:
            return JSONResponse(
                status_code=404,
                content={
                    "Endpoint": endpoint,
                    "StatusCode": 404,
                    "Data": {
                        "RunID": run_id,
                        "OrderID": order_id,
                        "Status": "ScheduledWorkOrderNotFound",
                    },
                },
            )
        detail["OutputContext"] = output_context_for_order(
            planning_run=planning_run,
            superseded_by_run_id=_superseded_by_run_id(
                run_id=run_id,
                planning_runs=planning_runs,
            ),
        )
        existing_release_context = detail.get("ReleaseContext")
        detail["ReleaseContext"] = {
            **(
                existing_release_context
                if isinstance(existing_release_context, dict)
                else {}
            ),
            **release_context_for_order(
                order_id=order_id,
                planning_run=planning_run,
                authorizations=release_authorizations,
            ),
        }
        detail["AuditContext"] = audit_context_for_order(
            order_id=order_id,
            audit_events=run_audit,
        )
        return {"Endpoint": endpoint, "StatusCode": 200, "Data": detail}

    @app.post(
        "/planner/workbench/schedule-results/runs/{run_id}/work-orders/commands"
    )
    def planner_workbench_scheduled_work_order_command(
        run_id: str,
        payload: ScheduledWorkOrderCommandPayload,
        request: Request,
    ):
        endpoint = (
            f"/planner/workbench/schedule-results/runs/{run_id}"
            "/work-orders/commands"
        )
        planning_run = planning_runs.get(run_id)
        if planning_run is None:
            return _planning_run_not_found(endpoint=endpoint, run_id=run_id)
        known_order_ids = {
            str(item.get("OrderID"))
            for item in scheduled_order_rows_from_schedule(
                _dict_schedule(planning_run)
            )
        }
        unknown = [item for item in payload.OrderIDs if item not in known_order_ids]
        if unknown:
            return JSONResponse(
                status_code=404,
                content={
                    "Endpoint": endpoint,
                    "StatusCode": 404,
                    "Data": {
                        "Status": "ScheduledWorkOrderNotFound",
                        "OrderIDs": unknown,
                    },
                },
            )
        if payload.Command == "SetPriority" and payload.Priority is None:
            return JSONResponse(
                status_code=422,
                content={
                    "Endpoint": endpoint,
                    "StatusCode": 422,
                    "Data": {"Status": "PriorityRequired"},
                },
            )
        action = {
            "Lock": "ScheduledWorkOrdersLocked",
            "Unlock": "ScheduledWorkOrdersUnlocked",
            "SetPriority": "ScheduledWorkOrdersPrioritySet",
        }[payload.Command]
        details: dict[str, object] = {"OrderIDs": payload.OrderIDs}
        if payload.Priority is not None:
            details["Priority"] = payload.Priority
        _append_planning_run_audit_event(
            audit_events=audit_events,
            run_id=run_id,
            action=action,
            actor_id=_effective_actor_id(request, payload.ActorID),
            occurred_at=payload.OccurredAt,
            details=details,
        )
        return {
            "Endpoint": endpoint,
            "StatusCode": 200,
            "Data": {
                "RunID": run_id,
                "Status": "CommandRecorded",
                "Action": action,
                "OrderIDs": payload.OrderIDs,
            },
        }

    @app.get(
        "/planner/workbench/release-management/runs/{run_id}/workbench"
    )
    def planner_workbench_release_management(
        run_id: str,
        evaluated_at: datetime,
        operational_state_max_age_minutes: int = Query(default=60, gt=0),
        use_latest_operational_state: bool = Query(default=False),
        operational_state_snapshot_id: str | None = Query(default=None),
    ):
        endpoint = (
            f"/planner/workbench/release-management/runs/{run_id}/workbench"
        )
        planning_run = planning_runs.get(run_id)
        if planning_run is None:
            return _planning_run_not_found(endpoint=endpoint, run_id=run_id)
        if planning_run.get("Status") != "Completed" or not isinstance(
            planning_run.get("Schedule"), dict
        ):
            return JSONResponse(
                status_code=409,
                content={
                    "Endpoint": endpoint,
                    "StatusCode": 409,
                    "Data": {
                        "RunID": run_id,
                        "Status": "ReleaseCandidatesUnavailable",
                    },
                },
            )
        snapshot = _operational_state_snapshot_for_release_evaluation(
            planning_run=planning_run,
            operational_state_snapshots=operational_state_snapshots,
            evaluated_at=evaluated_at,
            use_latest_operational_state=use_latest_operational_state,
            requested_snapshot_id=operational_state_snapshot_id,
        )
        if snapshot is None:
            return JSONResponse(
                status_code=404,
                content={
                    "Endpoint": endpoint,
                    "StatusCode": 404,
                    "Data": {
                        "Status": "OperationalStateSnapshotNotFound",
                        "SnapshotID": planning_run.get(
                            "OperationalStateSnapshotID"
                        ),
                    },
                },
            )
        freshness = evaluate_operational_state_freshness(
            snapshot=snapshot,
            evaluated_at=evaluated_at,
            max_age_minutes=operational_state_max_age_minutes,
        )
        master_data = master_data_versions.get(
            str(planning_run.get("MasterDataVersionID")), {}
        )
        material_requirements = _material_requirements_from_payload(
            [
                MaterialRequirementPayload(**item)
                for item in master_data.get("MaterialRequirements", [])
                if isinstance(item, dict)
            ]
        )
        return {
            "Endpoint": endpoint,
            "StatusCode": 200,
            "Data": build_release_management_workbench(
                planning_run=planning_run,
                evaluated_at=evaluated_at,
                inventory_buffers=snapshot.inventory_buffers,
                material_requirements=material_requirements,
                wip_limits=snapshot.wip_limits,
                material_availability=snapshot.material_availability,
                operational_state_status=freshness.status,
                operational_state_captured_at=snapshot.captured_at,
                authorizations=release_authorizations,
                operational_state_snapshot_id=snapshot.snapshot_id,
                release_policy=_release_policy_for_evaluation(
                    planning_run=planning_run,
                    requested_policy_id=None,
                    dbr_release_policies=dbr_release_policies,
                ),
            ),
        }

    @app.post(
        "/planner/workbench/release-management/runs/{run_id}"
        "/mock-operational-state-refresh"
    )
    def planner_workbench_release_management_mock_refresh(
        run_id: str,
        payload: MockOperationalStateRefreshPayload,
        request: Request,
    ):
        endpoint = (
            f"/planner/workbench/release-management/runs/{run_id}"
            "/mock-operational-state-refresh"
        )
        planning_run = planning_runs.get(run_id)
        if planning_run is None:
            return _planning_run_not_found(endpoint=endpoint, run_id=run_id)
        if planning_run.get("Status") != "Completed" or not isinstance(
            planning_run.get("Schedule"), dict
        ):
            return JSONResponse(
                status_code=409,
                content={
                    "Endpoint": endpoint,
                    "StatusCode": 409,
                    "Data": {
                        "RunID": run_id,
                        "Status": "ReleaseCandidatesUnavailable",
                    },
                },
            )
        source_snapshot = _operational_state_snapshot_for_release_evaluation(
            planning_run=planning_run,
            operational_state_snapshots=operational_state_snapshots,
            evaluated_at=payload.EvaluatedAt,
            use_latest_operational_state=True,
            requested_snapshot_id=payload.SourceSnapshotID,
        )
        if source_snapshot is None:
            return JSONResponse(
                status_code=404,
                content={
                    "Endpoint": endpoint,
                    "StatusCode": 404,
                    "Data": {"Status": "OperationalStateSnapshotNotFound"},
                },
            )
        snapshot_id = payload.SnapshotID or _next_mock_operational_snapshot_id(
            operational_state_snapshots=operational_state_snapshots,
            evaluated_at=payload.EvaluatedAt,
        )
        if snapshot_id in operational_state_snapshots:
            return JSONResponse(
                status_code=409,
                content={
                    "Endpoint": endpoint,
                    "StatusCode": 409,
                    "Data": {
                        "SnapshotID": snapshot_id,
                        "Status": "OperationalStateSnapshotConflict",
                    },
                },
            )
        refreshed_snapshot = create_operational_state_snapshot(
            snapshot_id=snapshot_id,
            captured_at=payload.EvaluatedAt,
            inventory_buffers=list(source_snapshot.inventory_buffers),
            material_availability=list(source_snapshot.material_availability),
            wip_limits=list(source_snapshot.wip_limits),
        )
        operational_state_snapshots[refreshed_snapshot.snapshot_id] = (
            refreshed_snapshot
        )
        _append_planning_run_audit_event(
            audit_events=audit_events,
            run_id=run_id,
            action="OperationalStateSnapshotMockRefreshed",
            actor_id=_effective_actor_id(request, payload.ActorID),
            occurred_at=payload.EvaluatedAt,
            details={
                "SourceSnapshotID": source_snapshot.snapshot_id,
                "SnapshotID": refreshed_snapshot.snapshot_id,
                "Usage": "ReleaseGateReevaluation",
            },
        )
        return {
            "Endpoint": endpoint,
            "StatusCode": 200,
            "Data": {
                "SourceSnapshotID": source_snapshot.snapshot_id,
                "Snapshot": _operational_state_snapshot_to_dict(
                    refreshed_snapshot
                ),
                "RecommendedNextAction": "ReevaluateReleaseGate",
            },
        }

    @app.post(
        "/planner/workbench/release-management/runs/{run_id}"
        "/orders/{order_id}/authorize"
    )
    def planner_workbench_release_management_authorize(
        run_id: str,
        order_id: str,
        payload: PlanningRunReleaseAuthorizationPayload,
        request: Request,
    ):
        endpoint = (
            f"/planner/workbench/release-management/runs/{run_id}"
            f"/orders/{order_id}/authorize"
        )
        planning_run = planning_runs.get(run_id)
        if planning_run is None:
            return _planning_run_not_found(endpoint=endpoint, run_id=run_id)
        snapshot = _operational_state_snapshot_for_release_evaluation(
            planning_run=planning_run,
            operational_state_snapshots=operational_state_snapshots,
            evaluated_at=payload.ReleasedAt,
            use_latest_operational_state=payload.UseLatestOperationalState,
            requested_snapshot_id=payload.OperationalStateSnapshotID,
        )
        if snapshot is None:
            return JSONResponse(
                status_code=404,
                content={
                    "Endpoint": endpoint,
                    "StatusCode": 404,
                    "Data": {"Status": "OperationalStateSnapshotNotFound"},
                },
            )
        freshness = evaluate_operational_state_freshness(
            snapshot=snapshot,
            evaluated_at=payload.ReleasedAt,
            max_age_minutes=payload.OperationalStateMaxAgeMinutes,
        )
        master_data = master_data_versions.get(
            str(planning_run.get("MasterDataVersionID")), {}
        )
        release_policy = _release_policy_for_evaluation(
            planning_run=planning_run,
            requested_policy_id=None,
            dbr_release_policies=dbr_release_policies,
        )
        workbench = build_release_management_workbench(
            planning_run=planning_run,
            evaluated_at=payload.ReleasedAt,
            inventory_buffers=snapshot.inventory_buffers,
            material_requirements=_material_requirements_from_payload(
                [
                    MaterialRequirementPayload(**item)
                    for item in master_data.get("MaterialRequirements", [])
                    if isinstance(item, dict)
                ]
            ),
            wip_limits=snapshot.wip_limits,
            material_availability=snapshot.material_availability,
            operational_state_status=freshness.status,
            operational_state_captured_at=snapshot.captured_at,
            authorizations=release_authorizations,
            operational_state_snapshot_id=snapshot.snapshot_id,
            release_policy=release_policy,
        )
        candidate = next(
            (
                item
                for item in workbench["Candidates"]
                if item["OrderID"] == order_id
            ),
            None,
        )
        if candidate is None:
            return JSONResponse(
                status_code=404,
                content={
                    "Endpoint": endpoint,
                    "StatusCode": 404,
                    "Data": {"Status": "ReleaseCandidateNotFound"},
                },
            )
        if not candidate["CanAuthorize"]:
            return JSONResponse(
                status_code=409,
                content={
                    "Endpoint": endpoint,
                    "StatusCode": 409,
                    "Data": {
                        "Status": "ReleaseGateBlocked",
                        "OrderID": order_id,
                        "BlockingReasons": candidate["BlockingReasons"],
                        "RecommendedAction": candidate["RecommendedAction"],
                    },
                },
            )
        authorization = create_release_authorization(
            request_id=run_id,
            candidate=candidate,
            released_by=payload.ReleasedBy,
            released_at=payload.ReleasedAt,
            operational_state_snapshot_id=snapshot.snapshot_id,
            operational_state_captured_at=snapshot.captured_at,
            release_policy_version_id=(
                str(release_policy.get("VersionID")) if release_policy else None
            ),
            release_policy_evidence=release_policy_evidence(release_policy),
        )
        release_authorizations.append(authorization)
        _append_planning_run_audit_event(
            audit_events=audit_events,
            run_id=run_id,
            action="WorkOrderReleaseAuthorized",
            actor_id=_effective_actor_id(request, payload.ReleasedBy),
            occurred_at=payload.ReleasedAt,
            details={
                "OrderIDs": [order_id],
                "AuthorizationID": authorization.authorization_id,
                "OperationalStateSnapshotID": snapshot.snapshot_id,
                "ReleasePolicyVersionID": (
                    str(release_policy.get("VersionID")) if release_policy else None
                ),
            },
        )
        return {
            "Endpoint": endpoint,
            "StatusCode": 200,
            "Data": {
                "Authorization": _release_authorization_to_dict(authorization)
            },
        }

    @app.get("/planner/workbench/buffer-board/runs/{run_id}/workbench")
    def planner_workbench_buffer_board(run_id: str, evaluated_at: datetime):
        endpoint = f"/planner/workbench/buffer-board/runs/{run_id}/workbench"
        planning_run = planning_runs.get(run_id)
        if planning_run is None:
            return _planning_run_not_found(endpoint=endpoint, run_id=run_id)
        if planning_run.get("Status") != "Completed" or not isinstance(
            planning_run.get("Schedule"), dict
        ):
            return JSONResponse(
                status_code=409,
                content={
                    "Endpoint": endpoint,
                    "StatusCode": 409,
                    "Data": {"Status": "BufferBoardUnavailable", "RunID": run_id},
                },
            )
        master_data = master_data_versions.get(
            str(planning_run.get("MasterDataVersionID")), {}
        )
        return {
            "Endpoint": endpoint,
            "StatusCode": 200,
            "Data": build_buffer_execution_workbench(
                planning_run=planning_run,
                master_data_version=master_data,
                authorizations=release_authorizations,
                execution_events=execution_events,
                evaluated_at=evaluated_at,
            ),
        }

    @app.get(
        "/planner/workbench/buffer-board/runs/{run_id}"
        "/orders/{order_id}/workbench"
    )
    def planner_workbench_buffer_order_detail(
        run_id: str,
        order_id: str,
        evaluated_at: datetime,
    ):
        endpoint = (
            f"/planner/workbench/buffer-board/runs/{run_id}"
            f"/orders/{order_id}/workbench"
        )
        planning_run = planning_runs.get(run_id)
        if planning_run is None:
            return _planning_run_not_found(endpoint=endpoint, run_id=run_id)
        master_data = master_data_versions.get(
            str(planning_run.get("MasterDataVersionID")), {}
        )
        try:
            detail = build_buffer_order_detail(
                planning_run=planning_run,
                master_data_version=master_data,
                authorizations=release_authorizations,
                execution_events=execution_events,
                order_id=order_id,
                evaluated_at=evaluated_at,
            )
        except KeyError:
            return JSONResponse(
                status_code=404,
                content={
                    "Endpoint": endpoint,
                    "StatusCode": 404,
                    "Data": {
                        "Status": "BufferOrderNotFound",
                        "RunID": run_id,
                        "OrderID": order_id,
                    },
                },
            )
        return {"Endpoint": endpoint, "StatusCode": 200, "Data": detail}

    @app.post(
        "/planner/workbench/buffer-board/runs/{run_id}"
        "/orders/{order_id}/transactions"
    )
    def planner_workbench_buffer_transaction(
        run_id: str,
        order_id: str,
        payload: BufferTransactionPayload,
        request: Request,
    ):
        endpoint = (
            f"/planner/workbench/buffer-board/runs/{run_id}"
            f"/orders/{order_id}/transactions"
        )
        planning_run = planning_runs.get(run_id)
        if planning_run is None:
            return _planning_run_not_found(endpoint=endpoint, run_id=run_id)
        master_data = master_data_versions.get(
            str(planning_run.get("MasterDataVersionID")), {}
        )
        try:
            detail = build_buffer_order_detail(
                planning_run=planning_run,
                master_data_version=master_data,
                authorizations=release_authorizations,
                execution_events=execution_events,
                order_id=order_id,
                evaluated_at=payload.EventAt,
            )
        except KeyError:
            return JSONResponse(
                status_code=404,
                content={
                    "Endpoint": endpoint,
                    "StatusCode": 404,
                    "Data": {"Status": "BufferOrderNotFound", "OrderID": order_id},
                },
            )
        execution = detail["Execution"]
        if (
            execution["Zone"]
            in detail["TransactionPolicy"]["ReasonRequiredZones"]
            and not payload.ExceptionCode
        ):
            return JSONResponse(
                status_code=409,
                content={
                    "Endpoint": endpoint,
                    "StatusCode": 409,
                    "Data": {
                        "Status": "ReasonCodeRequired",
                        "OrderID": order_id,
                        "AuthorizationID": execution["AuthorizationID"],
                        "Zone": execution["Zone"],
                    },
                },
            )
        if payload.MeasureType == "CompletionPercent" and payload.MeasureValue > 100:
            return JSONResponse(
                status_code=409,
                content={
                    "Endpoint": endpoint,
                    "StatusCode": 409,
                    "Data": {
                        "Status": "TransactionMeasureInvalid",
                        "MeasureType": payload.MeasureType,
                    },
                },
            )
        target_start = datetime.fromisoformat(str(execution["ScheduledStart"]))
        validation = validate_execution_event(
            ExecutionEvent(
                order_id=order_id,
                event_type=payload.EventType,
                event_at=payload.EventAt,
                target_start_at=target_start,
                exception_code=payload.ExceptionCode,
            )
        )
        if not validation.accepted:
            return JSONResponse(
                status_code=409,
                content={
                    "Endpoint": endpoint,
                    "StatusCode": 409,
                    "Data": {
                        "Status": validation.status,
                        "Message": validation.message,
                        "RequiresExceptionCode": validation.requires_exception_code,
                    },
                },
            )
        event_record = {
            "AuthorizationID": execution["AuthorizationID"],
            "OrderID": order_id,
            "EventType": payload.EventType,
            "EventAt": payload.EventAt.isoformat(),
            "TargetStartAt": target_start.isoformat(),
            "ActorID": _effective_actor_id(request, payload.ActorID),
            "MeasureType": payload.MeasureType,
            "MeasureValue": payload.MeasureValue,
            "ExceptionCode": payload.ExceptionCode,
            "Status": validation.status,
            "RequiresReview": validation.requires_review,
        }
        execution_events.append(event_record)
        return {
            "Endpoint": endpoint,
            "StatusCode": 200,
            "Data": {"Status": validation.status, "Event": event_record},
        }

    @app.get("/planner/workbench/exceptions/workbench")
    def planner_workbench_exception_center(evaluated_at: datetime):
        endpoint = "/planner/workbench/exceptions/workbench"
        return {
            "Endpoint": endpoint,
            "StatusCode": 200,
            "Data": build_exception_center_workbench(
                planning_runs=list(planning_runs.values()),
                audit_events=audit_events,
                replan_requests=replan_requests,
                release_authorizations=release_authorizations,
                execution_events=execution_events,
                evaluated_at=evaluated_at,
            ),
        }

    @app.get("/planner/workbench/exceptions/{exception_id}/workbench")
    def planner_workbench_exception_detail(exception_id: str, evaluated_at: datetime):
        endpoint = f"/planner/workbench/exceptions/{exception_id}/workbench"
        try:
            detail = build_exception_detail(
                exception_id=exception_id,
                planning_runs=list(planning_runs.values()),
                audit_events=audit_events,
                replan_requests=replan_requests,
                release_authorizations=release_authorizations,
                execution_events=execution_events,
                evaluated_at=evaluated_at,
            )
        except KeyError:
            return JSONResponse(
                status_code=404,
                content={
                    "Endpoint": endpoint,
                    "StatusCode": 404,
                    "Data": {
                        "Status": "ExceptionNotFound",
                        "ExceptionID": exception_id,
                    },
                },
            )
        return {"Endpoint": endpoint, "StatusCode": 200, "Data": detail}

    @app.get("/planner/workbench/planning-runs/{run_id}")
    def planner_workbench_planning_run_get(run_id: str):
        endpoint = f"/planner/workbench/planning-runs/{run_id}"
        planning_run = planning_runs.get(run_id)
        if planning_run is None:
            return _planning_run_not_found(endpoint=endpoint, run_id=run_id)
        return {
            "Endpoint": endpoint,
            "StatusCode": 200,
            "Data": {
                "PlanningRun": _planning_run_public_record(planning_run),
            },
        }

    @app.get("/planner/workbench/planning-runs/{run_id}/publication")
    def planner_workbench_planning_run_publication_get(run_id: str):
        endpoint = f"/planner/workbench/planning-runs/{run_id}/publication"
        planning_run = planning_runs.get(run_id)
        if planning_run is None:
            return _planning_run_not_found(endpoint=endpoint, run_id=run_id)
        superseded_by_run_id = next(
            (
                str(other.get("RunID"))
                for other in planning_runs.values()
                if other.get("SupersedesRunID") == run_id
            ),
            None,
        )
        return {
            "Endpoint": endpoint,
            "StatusCode": 200,
            "Data": build_plan_publication_view(
                planning_run=planning_run,
                superseded_by_run_id=superseded_by_run_id,
            ),
        }

    @app.post("/planner/workbench/planning-runs/{run_id}/publication/review")
    def planner_workbench_planning_run_publication_review(
        run_id: str,
        payload: PlanPublicationTransitionPayload,
        request: Request,
    ):
        return _planning_run_publication_transition_response(
            endpoint=f"/planner/workbench/planning-runs/{run_id}/publication/review",
            run_id=run_id,
            action="Review",
            payload=payload,
            request=request,
            planning_runs=planning_runs,
            audit_events=audit_events,
        )

    @app.post("/planner/workbench/planning-runs/{run_id}/publication/approve")
    def planner_workbench_planning_run_publication_approve(
        run_id: str,
        payload: PlanPublicationTransitionPayload,
        request: Request,
    ):
        return _planning_run_publication_transition_response(
            endpoint=f"/planner/workbench/planning-runs/{run_id}/publication/approve",
            run_id=run_id,
            action="Approve",
            payload=payload,
            request=request,
            planning_runs=planning_runs,
            audit_events=audit_events,
        )

    @app.post("/planner/workbench/planning-runs/{run_id}/publication/publish")
    def planner_workbench_planning_run_publication_publish(
        run_id: str,
        payload: PlanPublicationTransitionPayload,
        request: Request,
    ):
        return _planning_run_publication_transition_response(
            endpoint=f"/planner/workbench/planning-runs/{run_id}/publication/publish",
            run_id=run_id,
            action="Publish",
            payload=payload,
            request=request,
            planning_runs=planning_runs,
            audit_events=audit_events,
        )

    @app.post("/planner/workbench/planning-runs/{run_id}/publication/revoke")
    def planner_workbench_planning_run_publication_revoke(
        run_id: str,
        payload: PlanPublicationTransitionPayload,
        request: Request,
    ):
        return _planning_run_publication_transition_response(
            endpoint=f"/planner/workbench/planning-runs/{run_id}/publication/revoke",
            run_id=run_id,
            action="Revoke",
            payload=payload,
            request=request,
            planning_runs=planning_runs,
            audit_events=audit_events,
        )

    @app.post("/planner/workbench/master-data/import")
    def planner_workbench_master_data_import(
        payload: MasterDataImportPayload,
    ) -> dict[str, object]:
        resources, routings, orders, inventory_buffers = _entities_from_master_data_import_payload(
            payload
        )
        validation = validate_master_data(
            resources=resources,
            routings=routings,
            orders=orders,
            inventory_buffers=inventory_buffers,
            material_requirements=_material_requirements_from_import_payload(payload),
            calendar_timezone=payload.CalendarTimezone,
        )
        return {
            "Endpoint": "/planner/workbench/master-data/import",
            "StatusCode": 200,
            "Data": {
                "Resources": _resources_to_payload_dict(resources),
                "Routings": _routings_to_payload_dict(routings),
                "Orders": _orders_to_payload_dict(orders),
                "InventoryBuffers": _inventory_buffers_to_payload_dict(inventory_buffers),
                "MaterialRequirements": _material_requirements_to_payload_dict(
                    _material_requirements_from_import_payload(payload)
                ),
                "Validation": _master_data_validation_to_dict(validation),
            },
        }

    @app.post("/planner/workbench/master-data/import/calculate")
    def planner_workbench_master_data_import_calculate(
        payload: PlannerWorkbenchImportCalculatePayload,
    ):
        resources, routings, orders, inventory_buffers = _entities_from_master_data_import_payload(
            payload
        )
        validation = validate_master_data(
            resources=resources,
            routings=routings,
            orders=orders,
            inventory_buffers=inventory_buffers,
            material_requirements=_material_requirements_from_import_payload(payload),
            calendar_timezone=payload.CalendarTimezone,
        )
        if not validation.is_valid:
            return JSONResponse(
                status_code=409,
                content={
                    "Endpoint": "/planner/workbench/master-data/import/calculate",
                    "StatusCode": 409,
                    "Data": {
                        "Validation": _master_data_validation_to_dict(validation),
                    },
                },
            )
        data = _calculate_workbench_data_from_entities(
            problem_id=payload.ProblemID,
            schedule_start_at=payload.ScheduleStartAt,
            resources=resources,
            routings=routings,
            orders=orders,
            inventory_buffers=inventory_buffers,
            validation=validation,
            time_buffer_minutes=payload.TimeBufferMinutes,
            calendar_timezone=payload.CalendarTimezone,
            solver_backend_id=payload.SolverBackendID,
            generated_at=payload.GeneratedAt,
        )
        return {
            "Endpoint": "/planner/workbench/master-data/import/calculate",
            "StatusCode": 200,
            "Data": data,
        }

    @app.post("/planner/workbench/master-data/import/release")
    def planner_workbench_master_data_import_release(
        payload: PlannerWorkbenchImportReleasePayload,
    ):
        resources, routings, orders, inventory_buffers = _entities_from_master_data_import_payload(
            payload
        )
        validation = validate_master_data(
            resources=resources,
            routings=routings,
            orders=orders,
            inventory_buffers=inventory_buffers,
            material_requirements=_material_requirements_from_import_payload(payload),
            calendar_timezone=payload.CalendarTimezone,
        )
        if not validation.is_valid:
            return JSONResponse(
                status_code=409,
                content={
                    "Endpoint": "/planner/workbench/master-data/import/release",
                    "StatusCode": 409,
                    "Data": {
                        "Validation": _master_data_validation_to_dict(validation),
                    },
                },
            )
        workbench_view = build_planner_workbench_view(
            problem_id=payload.ProblemID,
            orders=orders,
            resources=resources,
            routings=routings,
            schedule_start_at=payload.ScheduleStartAt,
            time_buffer_minutes=payload.TimeBufferMinutes,
            calendar_tzinfo=ZoneInfo(payload.CalendarTimezone) if payload.CalendarTimezone else None,
            solver_backend_id=payload.SolverBackendID,
            generated_at=payload.GeneratedAt,
            inventory_buffers=inventory_buffers,
        )
        recommendations = {
            item.order_id: item.suggested_release_date
            for item in workbench_view.release_recommendations
        }
        if payload.OrderID not in recommendations:
            body = {
                "Endpoint": "/planner/workbench/master-data/import/release",
                "StatusCode": 404,
                "Data": {
                    "OrderID": payload.OrderID,
                    "Allowed": False,
                    "Status": "ReleaseOrderNotFound",
                    "Message": f"No release recommendation exists for order {payload.OrderID}.",
                },
            }
            return JSONResponse(status_code=404, content=body)
        body, status_code = _release_decision_response_body(
            endpoint="/planner/workbench/master-data/import/release",
            order_id=payload.OrderID,
            requested_release_at=payload.RequestedReleaseAt,
            suggested_release_at=recommendations[payload.OrderID],
            inventory_buffers=inventory_buffers,
            material_requirements=_material_requirements_from_import_payload(payload),
        )
        if status_code != 200:
            return JSONResponse(status_code=status_code, content=body)
        return body

    @app.post("/planner/workbench/scenarios/compare")
    def planner_workbench_scenarios_compare(
        payload: PlannerWorkbenchScenarioComparePayload,
    ):
        baseline_validation = _validate_master_data_payload(payload.Baseline)
        candidate_validation = _validate_master_data_payload(payload.Candidate)
        if not baseline_validation.is_valid or not candidate_validation.is_valid:
            invalid_scenario = _invalid_scenario_label(
                baseline_validation=baseline_validation,
                candidate_validation=candidate_validation,
            )
            return JSONResponse(
                status_code=409,
                content={
                    "Endpoint": "/planner/workbench/scenarios/compare",
                    "StatusCode": 409,
                    "Data": {
                        "InvalidScenario": invalid_scenario,
                        "Message": f"{invalid_scenario} scenario failed master data validation.",
                        "BaselineValidation": _master_data_validation_to_dict(
                            baseline_validation
                        ),
                        "CandidateValidation": _master_data_validation_to_dict(
                            candidate_validation
                        ),
                    },
                },
            )
        baseline_objective = _objective_for_strategy_id(
            strategy_id=payload.Baseline.ObjectiveStrategyID,
            scheduling_strategy_versions=scheduling_strategy_versions,
        )
        if baseline_objective is None:
            return _objective_strategy_not_found_response(
                endpoint="/planner/workbench/scenarios/compare",
                strategy_id=payload.Baseline.ObjectiveStrategyID,
            )
        candidate_objective = _objective_for_strategy_id(
            strategy_id=payload.Candidate.ObjectiveStrategyID,
            scheduling_strategy_versions=scheduling_strategy_versions,
        )
        if candidate_objective is None:
            return _objective_strategy_not_found_response(
                endpoint="/planner/workbench/scenarios/compare",
                strategy_id=payload.Candidate.ObjectiveStrategyID,
            )
        baseline_view = _calculate_workbench_data(
            payload.Baseline,
            baseline_validation,
            objective=baseline_objective,
        )
        candidate_view = _calculate_workbench_data(
            payload.Candidate,
            candidate_validation,
            objective=candidate_objective,
        )
        return {
            "Endpoint": "/planner/workbench/scenarios/compare",
            "StatusCode": 200,
            "Data": compare_scenarios(
                baseline_payload=baseline_view,
                candidate_payload=candidate_view,
            ),
        }

    @app.post("/planner/workbench/simio/export")
    def planner_workbench_simio_export(payload: PlannerWorkbenchCalculatePayload) -> dict[str, object]:
        problem = build_scheduling_problem(
            problem_id=payload.ProblemID,
            orders=_orders_from_payload(payload.Orders),
            routings=_routings_from_payload(payload.Routings),
        )
        return {
            "Endpoint": "/planner/workbench/simio/export",
            "StatusCode": 200,
            "Data": SimioValidationAdapter().export_problem(problem),
        }

    @app.get("/planner/workbench/simio/templates")
    def planner_workbench_simio_templates() -> dict[str, object]:
        endpoint = "/planner/workbench/simio/templates"
        active_template_id = active_store.active_simio_template_id
        templates = list(simio_template_registry.values())
        active_template: dict[str, object] | None = None
        try:
            active_template = resolve_simio_template(
                template_registry=simio_template_registry,
                active_template_id=active_template_id,
            )
            status = "Ready"
            message = "Simio validation template is configured."
        except SimioValidationError as error:
            status = error.status
            message = error.message
        return {
            "Endpoint": endpoint,
            "StatusCode": 200,
            "Data": {
                "Status": status,
                "Message": message,
                "ActiveTemplateID": active_template_id,
                "ActiveTemplate": active_template,
                "Templates": templates,
                "TemplateCount": len(templates),
                "TemplatePolicy": {
                    "DefaultDirectory": "model/templates/simio",
                    "RuntimeRule": (
                        "Copy the active template to a derived package for each "
                        "validation run; do not mutate the source template."
                    ),
                    "TimeUnitRule": (
                        "APS minutes must be written to Simio time fields with "
                        "explicit Minutes units."
                    ),
                },
            },
        }

    @app.post("/planner/workbench/simio/validation-runs")
    def planner_workbench_simio_validation_run_create(
        payload: SimioValidationRunPayload,
    ):
        endpoint = "/planner/workbench/simio/validation-runs"
        planning_run = planning_runs.get(payload.RunID)
        if planning_run is None:
            return _planning_run_not_found(endpoint=endpoint, run_id=payload.RunID)
        output_package = build_schedule_output_package(
            planning_run=planning_run,
            master_data_version=master_data_versions.get(
                str(planning_run.get("MasterDataVersionID"))
            ),
            operational_state_snapshot=operational_state_snapshots.get(
                str(planning_run.get("OperationalStateSnapshotID"))
            ),
            release_authorizations=release_authorizations,
            audit_events=[
                event for event in audit_events if event["RunID"] == payload.RunID
            ],
            simio_validation_runs=simio_validation_runs,
            superseded_by_run_id=_superseded_by_run_id(
                run_id=payload.RunID,
                planning_runs=planning_runs,
            ),
        )
        if output_package.get("Status") == "OutputPackageUnavailable":
            return JSONResponse(
                status_code=409,
                content={
                    "Endpoint": endpoint,
                    "StatusCode": 409,
                    "Data": {
                        "RunID": payload.RunID,
                        "Status": "SimioValidationUnavailable",
                        "Message": (
                            "Simio validation requires a completed, internally "
                            "consistent schedule output package."
                        ),
                        "Completeness": output_package.get("Completeness"),
                    },
                },
            )
        try:
            validation_run = create_simio_validation_run(
                planning_run=planning_run,
                output_package=output_package,
                runner_mode=payload.RunnerMode,
                requested_by=payload.RequestedBy,
                requested_at=payload.RequestedAt,
                template_registry=simio_template_registry,
                active_template_id=active_store.active_simio_template_id,
                template_id=payload.TemplateID,
            )
        except SimioValidationError as error:
            return JSONResponse(
                status_code=409,
                content={
                    "Endpoint": endpoint,
                    "StatusCode": 409,
                    "Data": {
                        "RunID": payload.RunID,
                        "Status": error.status,
                        "Message": error.message,
                    },
                },
            )
        simio_validation_runs[str(validation_run["ValidationRunID"])] = validation_run
        _append_planning_run_audit_event(
            audit_events=audit_events,
            run_id=payload.RunID,
            action="SimioValidationRunCreated",
            actor_id=payload.RequestedBy,
            occurred_at=payload.RequestedAt or datetime.now(timezone.utc),
            details={
                "ValidationRunID": validation_run["ValidationRunID"],
                "RunnerMode": payload.RunnerMode,
                "TemplateID": validation_run["Package"].get("TemplateID"),
                "TemplateVersion": validation_run["Package"].get("TemplateVersion"),
                "Status": validation_run["Status"],
                "PackageID": validation_run["Package"]["PackageID"],
            },
        )
        return {
            "Endpoint": endpoint,
            "StatusCode": 200,
            "Data": validation_run,
        }

    @app.get("/planner/workbench/simio/validation-runs/{validation_run_id}")
    def planner_workbench_simio_validation_run_get(validation_run_id: str):
        endpoint = f"/planner/workbench/simio/validation-runs/{validation_run_id}"
        validation_run = simio_validation_runs.get(validation_run_id)
        if validation_run is None:
            return JSONResponse(
                status_code=404,
                content={
                    "Endpoint": endpoint,
                    "StatusCode": 404,
                    "Data": {
                        "ValidationRunID": validation_run_id,
                        "Status": "SimioValidationRunNotFound",
                        "Message": (
                            f"Simio validation run {validation_run_id} was not found."
                        ),
                    },
                },
            )
        return {
            "Endpoint": endpoint,
            "StatusCode": 200,
            "Data": validation_run,
        }

    @app.get(
        "/planner/workbench/schedule-results/runs/{run_id}/simio-validation"
    )
    def planner_workbench_schedule_result_simio_validation(run_id: str):
        endpoint = f"/planner/workbench/schedule-results/runs/{run_id}/simio-validation"
        planning_run = planning_runs.get(run_id)
        if planning_run is None:
            return _planning_run_not_found(endpoint=endpoint, run_id=run_id)
        return {
            "Endpoint": endpoint,
            "StatusCode": 200,
            "Data": summarize_simio_validation(
                simio_validation_runs=simio_validation_runs,
                run_id=run_id,
            ),
        }

    @app.post("/planner/workbench/release")
    def planner_workbench_release(
        payload: PlannerWorkbenchReleasePayload,
        request: Request,
    ):
        validation = _validate_master_data_payload(payload)
        if not validation.is_valid:
            return JSONResponse(
                status_code=409,
                content={
                    "Endpoint": "/planner/workbench/release",
                    "StatusCode": 409,
                    "Data": {
                        "Validation": _master_data_validation_to_dict(validation),
                    },
                },
            )
        workbench_view = build_planner_workbench_view(
            problem_id=payload.ProblemID,
            orders=_orders_from_payload(payload.Orders),
            resources=_resources_from_payload(payload.Resources),
            routings=_routings_from_payload(payload.Routings),
            schedule_start_at=payload.ScheduleStartAt,
            time_buffer_minutes=payload.TimeBufferMinutes,
            calendar_tzinfo=ZoneInfo(payload.CalendarTimezone) if payload.CalendarTimezone else None,
            solver_backend_id=payload.SolverBackendID,
            generated_at=payload.GeneratedAt,
            inventory_buffers=_inventory_buffers_from_payload(payload.InventoryBuffers),
        )
        recommendations = {
            item.order_id: item.suggested_release_date
            for item in workbench_view.release_recommendations
        }
        if payload.OrderID not in recommendations:
            body = {
                "Endpoint": "/planner/workbench/release",
                "StatusCode": 404,
                "Data": {
                    "OrderID": payload.OrderID,
                    "Allowed": False,
                    "Status": "ReleaseOrderNotFound",
                    "Message": f"No release recommendation exists for order {payload.OrderID}.",
                },
            }
            return JSONResponse(status_code=404, content=body)
        decision = evaluate_release_decision(
            order_id=payload.OrderID,
            requested_release_at=payload.RequestedReleaseAt,
            suggested_release_at=recommendations[payload.OrderID],
        )
        inventory_buffers = _inventory_buffers_from_payload(payload.InventoryBuffers)
        material_requirements = _material_requirements_from_payload(payload.MaterialRequirements)
        body, status_code = _release_decision_body(
            endpoint="/planner/workbench/release",
            decision=decision,
            inventory_buffers=inventory_buffers,
            material_requirements=material_requirements,
        )
        gate_allowed = bool(body["Data"]["Allowed"])
        consecutive_blocked_count = (
            0
            if gate_allowed
            else payload.PreviousConsecutiveBlockedCount + 1
        )
        stability = evaluate_release_stability(
            ReleaseStabilityInput(
                order_id=payload.OrderID,
                planned_release_at=recommendations[payload.OrderID],
                evaluated_release_at=payload.RequestedReleaseAt,
                gate_allowed=gate_allowed,
                consecutive_blocked_count=consecutive_blocked_count,
                last_replan_at=payload.LastReplanAt,
            ),
            policy=ReleaseStabilityPolicy(
                tolerance_minutes=payload.StabilityPolicy.ToleranceMinutes,
                replan_threshold_minutes=(
                    payload.StabilityPolicy.ReplanThresholdMinutes
                ),
                consecutive_blocked_threshold=(
                    payload.StabilityPolicy.ConsecutiveBlockedThreshold
                ),
                replan_cooldown_minutes=(
                    payload.StabilityPolicy.ReplanCooldownMinutes
                ),
            ),
        )
        body["Data"]["Stability"] = _release_stability_to_dict(
            stability,
            consecutive_blocked_count=consecutive_blocked_count,
        )
        replan_request = create_replan_request(
            problem_id=payload.ProblemID,
            order_id=payload.OrderID,
            planned_release_at=recommendations[payload.OrderID],
            detected_at=payload.RequestedReleaseAt,
            reason_code=stability.reason_code,
            deviation_minutes=stability.deviation_minutes,
            consecutive_blocked_count=consecutive_blocked_count,
            replan_required=stability.replan_required,
        )
        replan_request_created = False
        if replan_request is not None:
            existing_request = next(
                (
                    item
                    for item in replan_requests
                    if item.request_id == replan_request.request_id
                ),
                None,
            )
            if existing_request is None:
                replan_requests.append(replan_request)
                replan_request_created = True
            else:
                replan_request = existing_request
        body["Data"]["ReplanRequest"] = (
            _replan_request_to_dict(replan_request)
            if replan_request is not None
            else None
        )
        if status_code != 200:
            if replan_request_created:
                request.state.persist_workbench_write = True
            return JSONResponse(status_code=status_code, content=body)
        return body

    @app.get("/planner/workbench/replan-requests")
    def planner_workbench_replan_requests() -> dict[str, object]:
        return {
            "Endpoint": "/planner/workbench/replan-requests",
            "StatusCode": 200,
            "Data": {
                "Count": len(replan_requests),
                "Requests": [
                    _replan_request_to_dict(item)
                    for item in replan_requests
                ],
            },
        }

    @app.post("/planner/workbench/replan-requests/{request_id}/decision")
    def planner_workbench_replan_request_decision(
        request_id: str,
        payload: ReplanRequestDecisionPayload,
    ):
        request_index = next(
            (
                index
                for index, item in enumerate(replan_requests)
                if item.request_id == request_id
            ),
            None,
        )
        endpoint = f"/planner/workbench/replan-requests/{request_id}/decision"
        if request_index is None:
            return JSONResponse(
                status_code=404,
                content={
                    "Endpoint": endpoint,
                    "StatusCode": 404,
                    "Data": {
                        "RequestID": request_id,
                        "Status": "ReplanRequestNotFound",
                        "Message": f"Replan request {request_id} was not found.",
                    },
                },
            )
        try:
            updated_request = decide_replan_request(
                replan_requests[request_index],
                decision=payload.Decision,
                decided_by=payload.DecidedBy,
                decided_at=payload.DecidedAt,
                comment=payload.Comment,
            )
        except ValueError as error:
            return JSONResponse(
                status_code=409,
                content={
                    "Endpoint": endpoint,
                    "StatusCode": 409,
                    "Data": {
                        "RequestID": request_id,
                        "Status": "ReplanDecisionConflict",
                        "Message": str(error),
                    },
                },
            )
        replan_requests[request_index] = updated_request
        return {
            "Endpoint": endpoint,
            "StatusCode": 200,
            "Data": {
                "Request": _replan_request_to_dict(updated_request),
            },
        }

    @app.post("/planner/workbench/replan-requests/{request_id}/execute")
    def planner_workbench_replan_request_execute(
        request_id: str,
        payload: PlannerWorkbenchCalculatePayload,
    ):
        request_index = next(
            (
                index
                for index, item in enumerate(replan_requests)
                if item.request_id == request_id
            ),
            None,
        )
        endpoint = f"/planner/workbench/replan-requests/{request_id}/execute"
        if request_index is None:
            return JSONResponse(
                status_code=404,
                content={
                    "Endpoint": endpoint,
                    "StatusCode": 404,
                    "Data": {
                        "RequestID": request_id,
                        "Status": "ReplanRequestNotFound",
                        "Message": f"Replan request {request_id} was not found.",
                    },
                },
            )

        current_request = replan_requests[request_index]
        try:
            running_request = start_replan_execution(
                current_request,
                started_at=datetime.now(timezone.utc),
                solver_backend_id=payload.SolverBackendID,
            )
        except ValueError as error:
            return JSONResponse(
                status_code=409,
                content={
                    "Endpoint": endpoint,
                    "StatusCode": 409,
                    "Data": {
                        "RequestID": request_id,
                        "Status": "ReplanExecutionConflict",
                        "Message": str(error),
                    },
                },
            )
        if payload.ProblemID != current_request.problem_id:
            return JSONResponse(
                status_code=409,
                content={
                    "Endpoint": endpoint,
                    "StatusCode": 409,
                    "Data": {
                        "RequestID": request_id,
                        "Status": "ReplanProblemMismatch",
                        "Message": (
                            f"Snapshot problem {payload.ProblemID} does not match "
                            f"request problem {current_request.problem_id}."
                        ),
                    },
                },
            )
        if payload.SolverBackendID != ACTIVE_SOLVER_BACKEND_ID:
            return JSONResponse(
                status_code=409,
                content={
                    "Endpoint": endpoint,
                    "StatusCode": 409,
                    "Data": {
                        "RequestID": request_id,
                        "Status": "ReplanBackendRejected",
                        "Message": "Approved replans must use the active OR-Tools CP-SAT backend.",
                    },
                },
            )
        validation = _validate_master_data_payload(payload)
        if not validation.is_valid:
            return JSONResponse(
                status_code=409,
                content={
                    "Endpoint": endpoint,
                    "StatusCode": 409,
                    "Data": {
                        "RequestID": request_id,
                        "Status": "ReplanMasterDataInvalid",
                        "Validation": _master_data_validation_to_dict(validation),
                    },
                },
            )
        if payload.SourceRunID is not None and _source_run_for_replan(
            problem_id=current_request.problem_id,
            source_run_id=payload.SourceRunID,
            planning_runs=planning_runs,
        ) is None:
            return JSONResponse(
                status_code=409,
                content={
                    "Endpoint": endpoint,
                    "StatusCode": 409,
                    "Data": {
                        "RequestID": request_id,
                        "SourceRunID": payload.SourceRunID,
                        "Status": "ReplanSourceRunUnavailable",
                        "Message": "Source run must be a completed schedule for the same problem.",
                    },
                },
            )
        replan_requests[request_index] = running_request
        fixed_assignments = _fixed_assignments_for_replan(
            problem_id=current_request.problem_id,
            source_run_id=payload.SourceRunID,
            schedule_start_at=payload.ScheduleStartAt,
            freeze_window_minutes=payload.FreezeWindowMinutes,
            planning_runs=planning_runs,
            audit_events=audit_events,
        )
        objective = _objective_for_strategy_id(
            strategy_id=payload.ObjectiveStrategyID,
            scheduling_strategy_versions=scheduling_strategy_versions,
        )
        if objective is None:
            return _objective_strategy_not_found_response(
                endpoint=endpoint,
                strategy_id=payload.ObjectiveStrategyID,
            )
        source_run = _source_run_for_replan(
            problem_id=current_request.problem_id,
            source_run_id=payload.SourceRunID,
            planning_runs=planning_runs,
        )
        schedule = _calculate_workbench_data(
            payload,
            validation,
            fixed_assignments=fixed_assignments,
            objective=objective,
        )
        if source_run is not None:
            schedule["SourceRunID"] = source_run.get("RunID")
            schedule["ReplanTrace"] = {
                "SourceRunID": source_run.get("RunID"),
                "FreezeWindowMinutes": payload.FreezeWindowMinutes,
                "LockedOrderIDs": sorted(
                    _locked_order_ids_for_run(
                        run_id=str(source_run.get("RunID")),
                        audit_events=audit_events,
                    )
                ),
                "FixedAssignmentCount": len(fixed_assignments),
            }
            schedule["ReplanDiff"] = _schedule_operation_diff(
                source_schedule=_dict_schedule(source_run),
                candidate_schedule=schedule,
                fixed_assignments=fixed_assignments,
            )
        finished_request = finish_replan_execution(
            running_request,
            completed_at=datetime.now(timezone.utc),
            solver_status=str(schedule["SolverStatus"]),
            solver_message=str(schedule["SolverMessage"]),
        )
        replan_requests[request_index] = finished_request
        if finished_request.status == "Completed":
            replan_schedule_snapshots[request_id] = schedule
        else:
            replan_schedule_snapshots.pop(request_id, None)
        return {
            "Endpoint": endpoint,
            "StatusCode": 200,
            "Data": {
                "Request": _replan_request_to_dict(finished_request),
                "Schedule": schedule,
            },
        }

    @app.get("/planner/workbench/replan-requests/{request_id}/scheduled-work-orders")
    def planner_workbench_replan_scheduled_work_orders(request_id: str):
        endpoint = f"/planner/workbench/replan-requests/{request_id}/scheduled-work-orders"
        request = next(
            (item for item in replan_requests if item.request_id == request_id),
            None,
        )
        if request is None:
            return JSONResponse(
                status_code=404,
                content={
                    "Endpoint": endpoint,
                    "StatusCode": 404,
                    "Data": {
                        "RequestID": request_id,
                        "Status": "ReplanRequestNotFound",
                        "Message": f"Replan request {request_id} was not found.",
                    },
                },
            )
        schedule = replan_schedule_snapshots.get(request_id)
        if request.status != "Completed" or schedule is None:
            return JSONResponse(
                status_code=409,
                content={
                    "Endpoint": endpoint,
                    "StatusCode": 409,
                    "Data": {
                        "RequestID": request_id,
                        "Status": "ScheduledWorkOrdersUnavailable",
                        "Message": "Scheduled work orders are available only after a completed replan execution.",
                    },
                },
            )
        return {
            "Endpoint": endpoint,
            "StatusCode": 200,
            "Data": {
                "RequestID": request_id,
                "SolverStatus": request.solver_status,
                "Operations": scheduled_work_order_rows_from_schedule(schedule),
            },
        }

    @app.get("/planner/workbench/replan-requests/{request_id}/scheduled-orders")
    def planner_workbench_replan_scheduled_orders(request_id: str):
        endpoint = f"/planner/workbench/replan-requests/{request_id}/scheduled-orders"
        request = next(
            (item for item in replan_requests if item.request_id == request_id),
            None,
        )
        if request is None:
            return JSONResponse(
                status_code=404,
                content={
                    "Endpoint": endpoint,
                    "StatusCode": 404,
                    "Data": {
                        "RequestID": request_id,
                        "Status": "ReplanRequestNotFound",
                        "Message": f"Replan request {request_id} was not found.",
                    },
                },
            )
        schedule = replan_schedule_snapshots.get(request_id)
        if request.status != "Completed" or schedule is None:
            return JSONResponse(
                status_code=409,
                content={
                    "Endpoint": endpoint,
                    "StatusCode": 409,
                    "Data": {
                        "RequestID": request_id,
                        "Status": "ScheduledOrdersUnavailable",
                        "Message": "Scheduled orders are available only after a completed replan execution.",
                    },
                },
            )
        return {
            "Endpoint": endpoint,
            "StatusCode": 200,
            "Data": {
                "RequestID": request_id,
                "SolverStatus": request.solver_status,
                "Orders": scheduled_order_rows_from_schedule(schedule),
            },
        }

    @app.post("/planner/workbench/replan-requests/{request_id}/release-candidates")
    def planner_workbench_replan_release_candidates(
        request_id: str,
        payload: ReleaseCandidatePayload,
    ):
        endpoint = f"/planner/workbench/replan-requests/{request_id}/release-candidates"
        request = next(
            (item for item in replan_requests if item.request_id == request_id),
            None,
        )
        if request is None:
            return JSONResponse(
                status_code=404,
                content={
                    "Endpoint": endpoint,
                    "StatusCode": 404,
                    "Data": {
                        "RequestID": request_id,
                        "Status": "ReplanRequestNotFound",
                        "Message": f"Replan request {request_id} was not found.",
                    },
                },
            )
        schedule = replan_schedule_snapshots.get(request_id)
        if request.status != "Completed" or schedule is None:
            return JSONResponse(
                status_code=409,
                content={
                    "Endpoint": endpoint,
                    "StatusCode": 409,
                    "Data": {
                        "RequestID": request_id,
                        "Status": "ReleaseCandidatesUnavailable",
                        "Message": "Release candidates are available only after a completed replan execution.",
                    },
                },
            )
        try:
            (
                inventory_buffers,
                material_availability,
                wip_limits,
                operational_snapshot,
            ) = resolve_release_operational_state(payload)
        except KeyError:
            return JSONResponse(
                status_code=404,
                content={
                    "Endpoint": endpoint,
                    "StatusCode": 404,
                    "Data": {
                        "SnapshotID": payload.OperationalStateSnapshotID,
                        "Status": "OperationalStateSnapshotNotFound",
                        "Message": (
                            f"Operational state snapshot "
                            f"{payload.OperationalStateSnapshotID} was not found."
                        ),
                    },
                },
            )
        return {
            "Endpoint": endpoint,
            "StatusCode": 200,
            "Data": {
                "RequestID": request_id,
                "SolverStatus": request.solver_status,
                "OperationalStateSnapshotID": (
                    operational_snapshot.snapshot_id
                    if operational_snapshot is not None
                    else None
                ),
                "OperationalStateCapturedAt": (
                    operational_snapshot.captured_at.isoformat()
                    if operational_snapshot is not None
                    else None
                ),
                "ReleasePolicyVersionID": payload.ReleasePolicyVersionID,
                "ReleasePolicySnapshot": (
                    dbr_release_policies.get(payload.ReleasePolicyVersionID)
                    if payload.ReleasePolicyVersionID is not None
                    else None
                ),
                "Candidates": release_candidate_rows_from_schedule(
                    schedule=schedule,
                    evaluated_at=payload.EvaluatedAt,
                    inventory_buffers=inventory_buffers,
                    material_requirements=_material_requirements_from_payload(
                        payload.MaterialRequirements
                    ),
                    wip_limits=wip_limits,
                    material_availability=material_availability,
                    release_policy=(
                        dbr_release_policies.get(payload.ReleasePolicyVersionID)
                        if payload.ReleasePolicyVersionID is not None
                        else None
                    ),
                ),
            },
        }

    @app.post("/planner/workbench/replan-requests/{request_id}/release-authorizations")
    def planner_workbench_replan_release_authorization(
        request_id: str,
        payload: ReleaseAuthorizationPayload,
    ):
        endpoint = f"/planner/workbench/replan-requests/{request_id}/release-authorizations"
        request = next(
            (item for item in replan_requests if item.request_id == request_id),
            None,
        )
        if request is None:
            return JSONResponse(
                status_code=404,
                content={
                    "Endpoint": endpoint,
                    "StatusCode": 404,
                    "Data": {
                        "RequestID": request_id,
                        "Status": "ReplanRequestNotFound",
                        "Message": f"Replan request {request_id} was not found.",
                    },
                },
            )
        schedule = replan_schedule_snapshots.get(request_id)
        if request.status != "Completed" or schedule is None:
            return JSONResponse(
                status_code=409,
                content={
                    "Endpoint": endpoint,
                    "StatusCode": 409,
                    "Data": {
                        "RequestID": request_id,
                        "Status": "ReleaseAuthorizationUnavailable",
                        "Message": "Release authorization is available only after a completed replan execution.",
                    },
                },
            )
        decision_package = None
        if payload.DecisionPackageID is not None:
            decision_package = release_decision_packages.get(payload.DecisionPackageID)
            if decision_package is None:
                return JSONResponse(
                    status_code=404,
                    content={
                        "Endpoint": endpoint,
                        "StatusCode": 404,
                        "Data": {
                            "DecisionPackageID": payload.DecisionPackageID,
                            "Status": "ReleaseDecisionPackageNotFound",
                            "Message": (
                                f"Release decision package "
                                f"{payload.DecisionPackageID} was not found."
                            ),
                        },
                    },
                )
            if decision_package["RequestID"] != request_id:
                return JSONResponse(
                    status_code=409,
                    content={
                        "Endpoint": endpoint,
                        "StatusCode": 409,
                        "Data": {
                            "DecisionPackageID": payload.DecisionPackageID,
                            "Status": "ReleaseDecisionPackageRequestMismatch",
                            "Message": "Decision package belongs to another replan request.",
                        },
                    },
                )
            operational_state_snapshot = operational_state_snapshots.get(
                str(decision_package["OperationalStateSnapshotID"])
            )
            candidates = list(decision_package["Candidates"])
            freshness_evaluated_at = payload.ReleasedAt
        else:
            try:
                (
                    inventory_buffers,
                    material_availability,
                    wip_limits,
                    operational_state_snapshot,
                ) = resolve_release_operational_state(payload)
            except KeyError:
                return JSONResponse(
                    status_code=404,
                    content={
                        "Endpoint": endpoint,
                        "StatusCode": 404,
                        "Data": {
                            "SnapshotID": payload.OperationalStateSnapshotID,
                            "Status": "OperationalStateSnapshotNotFound",
                            "Message": (
                                f"Operational state snapshot "
                                f"{payload.OperationalStateSnapshotID} was not found."
                            ),
                        },
                    },
                )
            candidates = release_candidate_rows_from_schedule(
                schedule=schedule,
                evaluated_at=payload.EvaluatedAt,
                inventory_buffers=inventory_buffers,
                material_requirements=_material_requirements_from_payload(
                    payload.MaterialRequirements
                ),
                wip_limits=wip_limits,
                material_availability=material_availability,
                release_policy=(
                    dbr_release_policies.get(payload.ReleasePolicyVersionID)
                    if payload.ReleasePolicyVersionID is not None
                    else None
                ),
            )
            freshness_evaluated_at = payload.EvaluatedAt
        if operational_state_snapshot is not None:
            freshness = evaluate_operational_state_freshness(
                snapshot=operational_state_snapshot,
                evaluated_at=freshness_evaluated_at,
                max_age_minutes=payload.OperationalStateMaxAgeMinutes,
            )
            if not freshness.acceptable:
                status = (
                    "OperationalStateSnapshotStale"
                    if freshness.status == "Stale"
                    else "OperationalStateSnapshotFromFuture"
                )
                return JSONResponse(
                    status_code=409,
                    content={
                        "Endpoint": endpoint,
                        "StatusCode": 409,
                        "Data": {
                            "SnapshotID": operational_state_snapshot.snapshot_id,
                            "Status": status,
                            "AgeMinutes": freshness.age_minutes,
                            "MaxAgeMinutes": freshness.max_age_minutes,
                            "Message": "Operational state snapshot is outside the authorization freshness window.",
                        },
                    },
                )
        candidate = next(
            (item for item in candidates if item["OrderID"] == payload.OrderID),
            None,
        )
        if candidate is None:
            return JSONResponse(
                status_code=404,
                content={
                    "Endpoint": endpoint,
                    "StatusCode": 404,
                    "Data": {
                        "RequestID": request_id,
                        "OrderID": payload.OrderID,
                        "Status": "ReleaseCandidateNotFound",
                        "Message": f"Release candidate for order {payload.OrderID} was not found.",
                    },
                },
            )
        release_policy = (
            dbr_release_policies.get(payload.ReleasePolicyVersionID)
            if payload.ReleasePolicyVersionID is not None
            else None
        )
        try:
            authorization = create_release_authorization(
                request_id=request_id,
                candidate=candidate,
                released_by=payload.ReleasedBy,
                released_at=payload.ReleasedAt,
                operational_state_snapshot_id=(
                    operational_state_snapshot.snapshot_id
                    if operational_state_snapshot is not None
                    else None
                ),
                operational_state_captured_at=(
                    operational_state_snapshot.captured_at
                    if operational_state_snapshot is not None
                    else None
                ),
                decision_package_id=payload.DecisionPackageID,
                release_policy_version_id=(
                    str(release_policy.get("VersionID")) if release_policy else None
                ),
                release_policy_evidence=release_policy_evidence(release_policy),
            )
        except ValueError as error:
            return JSONResponse(
                status_code=409,
                content={
                    "Endpoint": endpoint,
                    "StatusCode": 409,
                    "Data": {
                        "RequestID": request_id,
                        "OrderID": payload.OrderID,
                        "Status": "ReleaseAuthorizationRejected",
                        "Message": str(error),
                        "Candidate": candidate,
                    },
                },
            )
        existing_authorization = next(
            (
                item
                for item in release_authorizations
                if item.authorization_id == authorization.authorization_id
            ),
            None,
        )
        if existing_authorization is None:
            release_authorizations.append(authorization)
        else:
            existing_evidence = _release_authorization_evidence_to_dict(
                existing_authorization
            )
            requested_evidence = _release_authorization_evidence_to_dict(
                authorization
            )
            if existing_evidence != requested_evidence:
                return JSONResponse(
                    status_code=409,
                    content={
                        "Endpoint": endpoint,
                        "StatusCode": 409,
                        "Data": {
                            "AuthorizationID": authorization.authorization_id,
                            "RequestID": request_id,
                            "OrderID": payload.OrderID,
                            "Status": "ReleaseAuthorizationEvidenceConflict",
                            "Message": "The release event already exists with different decision evidence.",
                            "ExistingEvidence": existing_evidence,
                            "RequestedEvidence": requested_evidence,
                        },
                    },
                )
            authorization = existing_authorization
        return {
            "Endpoint": endpoint,
            "StatusCode": 200,
            "Data": {
                "Authorization": _release_authorization_to_dict(authorization),
            },
        }

    @app.post(
        "/planner/workbench/replan-requests/{request_id}/release-decision-packages"
    )
    def planner_workbench_release_decision_package(
        request_id: str,
        payload: ReleaseDecisionPackagePayload,
    ):
        endpoint = (
            f"/planner/workbench/replan-requests/{request_id}"
            "/release-decision-packages"
        )
        request = next(
            (item for item in replan_requests if item.request_id == request_id),
            None,
        )
        if request is None:
            return JSONResponse(
                status_code=404,
                content={
                    "Endpoint": endpoint,
                    "StatusCode": 404,
                    "Data": {
                        "RequestID": request_id,
                        "Status": "ReplanRequestNotFound",
                        "Message": f"Replan request {request_id} was not found.",
                    },
                },
            )
        schedule = replan_schedule_snapshots.get(request_id)
        if request.status != "Completed" or schedule is None:
            return JSONResponse(
                status_code=409,
                content={
                    "Endpoint": endpoint,
                    "StatusCode": 409,
                    "Data": {
                        "RequestID": request_id,
                        "Status": "ReleaseDecisionPackageUnavailable",
                        "Message": "A completed replan schedule is required.",
                    },
                },
            )
        operational_snapshot = operational_state_snapshots.get(
            payload.OperationalStateSnapshotID
        )
        if operational_snapshot is None:
            return JSONResponse(
                status_code=404,
                content={
                    "Endpoint": endpoint,
                    "StatusCode": 404,
                    "Data": {
                        "SnapshotID": payload.OperationalStateSnapshotID,
                        "Status": "OperationalStateSnapshotNotFound",
                        "Message": (
                            f"Operational state snapshot "
                            f"{payload.OperationalStateSnapshotID} was not found."
                        ),
                    },
                },
            )
        material_requirements = _material_requirements_from_payload(
            payload.MaterialRequirements
        )
        candidates = release_candidate_rows_from_schedule(
            schedule=schedule,
            evaluated_at=payload.EvaluatedAt,
            inventory_buffers=operational_snapshot.inventory_buffers,
            material_requirements=material_requirements,
            wip_limits=operational_snapshot.wip_limits,
            material_availability=operational_snapshot.material_availability,
        )
        decision_package = build_release_decision_package(
            request_id=request_id,
            problem_id=request.problem_id,
            solver_backend_id=str(request.solver_backend_id),
            solver_status=request.solver_status,
            schedule=schedule,
            operational_state_snapshot_id=operational_snapshot.snapshot_id,
            operational_state_captured_at=operational_snapshot.captured_at.isoformat(),
            evaluated_at=payload.EvaluatedAt.isoformat(),
            material_requirements=_material_requirements_to_payload_dict(
                material_requirements
            ),
            candidates=candidates,
        )
        package_id = str(decision_package["DecisionPackageID"])
        release_decision_packages.setdefault(package_id, decision_package)
        return {
            "Endpoint": endpoint,
            "StatusCode": 200,
            "Data": {"DecisionPackage": release_decision_packages[package_id]},
        }

    @app.get("/planner/workbench/release-decision-packages/{package_id}")
    def planner_workbench_release_decision_package_by_id(package_id: str):
        endpoint = f"/planner/workbench/release-decision-packages/{package_id}"
        decision_package = release_decision_packages.get(package_id)
        if decision_package is None:
            return JSONResponse(
                status_code=404,
                content={
                    "Endpoint": endpoint,
                    "StatusCode": 404,
                    "Data": {
                        "DecisionPackageID": package_id,
                        "Status": "ReleaseDecisionPackageNotFound",
                        "Message": f"Release decision package {package_id} was not found.",
                    },
                },
            )
        return {
            "Endpoint": endpoint,
            "StatusCode": 200,
            "Data": {"DecisionPackage": decision_package},
        }

    @app.get(
        "/planner/workbench/release-decision-packages/{package_id}/authorizations"
    )
    def planner_workbench_release_decision_package_authorizations(package_id: str):
        endpoint = (
            f"/planner/workbench/release-decision-packages/{package_id}"
            "/authorizations"
        )
        if package_id not in release_decision_packages:
            return JSONResponse(
                status_code=404,
                content={
                    "Endpoint": endpoint,
                    "StatusCode": 404,
                    "Data": {
                        "DecisionPackageID": package_id,
                        "Status": "ReleaseDecisionPackageNotFound",
                        "Message": f"Release decision package {package_id} was not found.",
                    },
                },
            )
        linked_authorizations = sorted(
            (
                item
                for item in release_authorizations
                if item.decision_package_id == package_id
            ),
            key=lambda item: (item.released_at, item.authorization_id),
        )
        return {
            "Endpoint": endpoint,
            "StatusCode": 200,
            "Data": {
                "DecisionPackageID": package_id,
                "AuthorizationStatus": (
                    "Authorized" if linked_authorizations else "NotAuthorized"
                ),
                "AuthorizationCount": len(linked_authorizations),
                "Authorizations": [
                    _release_authorization_to_dict(item)
                    for item in linked_authorizations
                ],
            },
        }

    @app.get(
        "/planner/workbench/release-decision-packages/{package_id}/execution-trace"
    )
    def planner_workbench_release_decision_package_execution_trace(package_id: str):
        endpoint = (
            f"/planner/workbench/release-decision-packages/{package_id}"
            "/execution-trace"
        )
        if package_id not in release_decision_packages:
            return JSONResponse(
                status_code=404,
                content={
                    "Endpoint": endpoint,
                    "StatusCode": 404,
                    "Data": {
                        "DecisionPackageID": package_id,
                        "Status": "ReleaseDecisionPackageNotFound",
                        "Message": f"Release decision package {package_id} was not found.",
                    },
                },
            )
        linked_authorizations = [
            item
            for item in release_authorizations
            if item.decision_package_id == package_id
        ]
        authorization_ids = {
            item.authorization_id for item in linked_authorizations
        }
        linked_events = [
            event
            for event in execution_events
            if event.get("AuthorizationID") in authorization_ids
        ]
        rows = build_authorized_execution_status(
            [build_dispatch_package(item) for item in linked_authorizations],
            linked_events,
        )
        for row in rows:
            authorization_id = row["AuthorizationID"]
            row["Events"] = sorted(
                (
                    event
                    for event in linked_events
                    if event.get("AuthorizationID") == authorization_id
                ),
                key=lambda event: str(event.get("EventAt", "")),
            )
        return {
            "Endpoint": endpoint,
            "StatusCode": 200,
            "Data": {
                "DecisionPackageID": package_id,
                "OverallExecutionStatus": _overall_execution_status(rows),
                "AuthorizationCount": len(linked_authorizations),
                "Rows": rows,
            },
        }

    @app.get(
        "/planner/workbench/release-decision-packages/{package_id}/execution-variance"
    )
    def planner_workbench_release_decision_package_execution_variance(package_id: str):
        endpoint = (
            f"/planner/workbench/release-decision-packages/{package_id}"
            "/execution-variance"
        )
        if package_id not in release_decision_packages:
            return JSONResponse(
                status_code=404,
                content={
                    "Endpoint": endpoint,
                    "StatusCode": 404,
                    "Data": {
                        "DecisionPackageID": package_id,
                        "Status": "ReleaseDecisionPackageNotFound",
                        "Message": f"Release decision package {package_id} was not found.",
                    },
                },
            )
        linked_authorizations = [
            item
            for item in release_authorizations
            if item.decision_package_id == package_id
        ]
        authorization_ids = {
            item.authorization_id for item in linked_authorizations
        }
        linked_events = [
            event
            for event in execution_events
            if event.get("AuthorizationID") in authorization_ids
        ]
        variance = build_schedule_execution_variance(
            [build_dispatch_package(item) for item in linked_authorizations],
            linked_events,
        )
        return {
            "Endpoint": endpoint,
            "StatusCode": 200,
            "Data": {
                "DecisionPackageID": package_id,
                **variance,
            },
        }

    @app.get(
        "/planner/workbench/release-decision-packages/{package_id}/execution-stability"
    )
    def planner_workbench_release_decision_package_execution_stability(
        package_id: str,
        ToleranceMinutes: int = 30,
        ReplanThresholdMinutes: int = 120,
        ReplanCooldownMinutes: int = 60,
        LastReplanAt: datetime | None = None,
    ):
        endpoint = (
            f"/planner/workbench/release-decision-packages/{package_id}"
            "/execution-stability"
        )
        if package_id not in release_decision_packages:
            return JSONResponse(
                status_code=404,
                content={
                    "Endpoint": endpoint,
                    "StatusCode": 404,
                    "Data": {
                        "DecisionPackageID": package_id,
                        "Status": "ReleaseDecisionPackageNotFound",
                        "Message": f"Release decision package {package_id} was not found.",
                    },
                },
            )
        linked_authorizations = [
            item
            for item in release_authorizations
            if item.decision_package_id == package_id
        ]
        authorization_ids = {
            item.authorization_id for item in linked_authorizations
        }
        linked_events = [
            event
            for event in execution_events
            if event.get("AuthorizationID") in authorization_ids
        ]
        variance = build_schedule_execution_variance(
            [build_dispatch_package(item) for item in linked_authorizations],
            linked_events,
        )
        try:
            policy = ReleaseStabilityPolicy(
                tolerance_minutes=ToleranceMinutes,
                replan_threshold_minutes=ReplanThresholdMinutes,
                replan_cooldown_minutes=ReplanCooldownMinutes,
            )
            stability = build_execution_variance_stability(
                list(variance["Rows"]),
                policy=policy,
                last_replan_at=LastReplanAt,
            )
        except ValueError as error:
            return JSONResponse(
                status_code=422,
                content={
                    "Endpoint": endpoint,
                    "StatusCode": 422,
                    "Data": {
                        "DecisionPackageID": package_id,
                        "Status": "ExecutionStabilityPolicyInvalid",
                        "Message": str(error),
                    },
                },
            )
        return {
            "Endpoint": endpoint,
            "StatusCode": 200,
            "Data": {
                "DecisionPackageID": package_id,
                "Policy": {
                    "ToleranceMinutes": ToleranceMinutes,
                    "ReplanThresholdMinutes": ReplanThresholdMinutes,
                    "ReplanCooldownMinutes": ReplanCooldownMinutes,
                    "LastReplanAt": (
                        LastReplanAt.isoformat()
                        if LastReplanAt is not None
                        else None
                    ),
                },
                **stability,
            },
        }

    @app.post(
        "/planner/workbench/release-decision-packages/{package_id}"
        "/execution-replan-requests"
    )
    def planner_workbench_execution_variance_replan_requests(
        package_id: str,
        payload: ExecutionVarianceReplanPayload,
    ):
        endpoint = (
            f"/planner/workbench/release-decision-packages/{package_id}"
            "/execution-replan-requests"
        )
        decision_package = release_decision_packages.get(package_id)
        if decision_package is None:
            return JSONResponse(
                status_code=404,
                content={
                    "Endpoint": endpoint,
                    "StatusCode": 404,
                    "Data": {
                        "DecisionPackageID": package_id,
                        "Status": "ReleaseDecisionPackageNotFound",
                        "Message": f"Release decision package {package_id} was not found.",
                    },
                },
            )
        linked_authorizations = [
            item
            for item in release_authorizations
            if item.decision_package_id == package_id
        ]
        authorization_ids = {
            item.authorization_id for item in linked_authorizations
        }
        linked_events = [
            event
            for event in execution_events
            if event.get("AuthorizationID") in authorization_ids
        ]
        variance = build_schedule_execution_variance(
            [build_dispatch_package(item) for item in linked_authorizations],
            linked_events,
        )
        try:
            stability = build_execution_variance_stability(
                list(variance["Rows"]),
                policy=ReleaseStabilityPolicy(
                    tolerance_minutes=payload.ToleranceMinutes,
                    replan_threshold_minutes=payload.ReplanThresholdMinutes,
                    replan_cooldown_minutes=payload.ReplanCooldownMinutes,
                ),
                last_replan_at=payload.LastReplanAt,
            )
        except ValueError as error:
            return JSONResponse(
                status_code=422,
                content={
                    "Endpoint": endpoint,
                    "StatusCode": 422,
                    "Data": {
                        "DecisionPackageID": package_id,
                        "Status": "ExecutionStabilityPolicyInvalid",
                        "Message": str(error),
                    },
                },
            )
        variance_by_authorization = {
            str(row["AuthorizationID"]): row for row in variance["Rows"]
        }
        queued_requests = []
        for row in stability["Rows"]:
            if row["ReplanRequired"] is not True:
                continue
            variance_row = variance_by_authorization[str(row["AuthorizationID"])]
            planned_at_key = (
                "PlannedCompletionAt"
                if row["DeviationBasis"] == "Completion"
                else "PlannedStartAt"
            )
            planned_at = datetime.fromisoformat(str(variance_row[planned_at_key]))
            replan_request = create_replan_request(
                problem_id=str(decision_package["ProblemID"]),
                order_id=str(row["OrderID"]),
                planned_release_at=planned_at,
                detected_at=payload.DetectedAt,
                reason_code=str(row["ReasonCode"]),
                deviation_minutes=int(row["DeviationMinutes"]),
                consecutive_blocked_count=0,
                replan_required=True,
                source="ExecutionVariance",
                source_reference_id=package_id,
                requested_by=payload.RequestedBy,
            )
            if replan_request is None:
                continue
            existing_request = next(
                (
                    item
                    for item in replan_requests
                    if item.request_id == replan_request.request_id
                ),
                None,
            )
            if existing_request is None:
                replan_requests.append(replan_request)
            else:
                replan_request = existing_request
            queued_requests.append(replan_request)
        if not queued_requests:
            return JSONResponse(
                status_code=409,
                content={
                    "Endpoint": endpoint,
                    "StatusCode": 409,
                    "Data": {
                        "DecisionPackageID": package_id,
                        "Status": "ExecutionReplanNotRequired",
                        "Message": "Execution variance does not currently require replanning.",
                    },
                },
            )
        return {
            "Endpoint": endpoint,
            "StatusCode": 200,
            "Data": {
                "DecisionPackageID": package_id,
                "Count": len(queued_requests),
                "Requests": [
                    _replan_request_to_dict(item) for item in queued_requests
                ],
            },
        }

    @app.get(
        "/planner/workbench/release-decision-packages/{package_id}/replan-requests"
    )
    def planner_workbench_release_decision_package_replan_requests(package_id: str):
        endpoint = (
            f"/planner/workbench/release-decision-packages/{package_id}"
            "/replan-requests"
        )
        if package_id not in release_decision_packages:
            return JSONResponse(
                status_code=404,
                content={
                    "Endpoint": endpoint,
                    "StatusCode": 404,
                    "Data": {
                        "DecisionPackageID": package_id,
                        "Status": "ReleaseDecisionPackageNotFound",
                        "Message": f"Release decision package {package_id} was not found.",
                    },
                },
            )
        linked_requests = sorted(
            (
                item
                for item in replan_requests
                if item.source == "ExecutionVariance"
                and item.source_reference_id == package_id
            ),
            key=lambda item: (item.detected_at, item.request_id),
        )
        statuses = {item.status for item in linked_requests}
        if not statuses:
            feedback_status = "NoReplanRequest"
        elif len(statuses) == 1:
            feedback_status = next(iter(statuses))
        else:
            feedback_status = "Mixed"
        return {
            "Endpoint": endpoint,
            "StatusCode": 200,
            "Data": {
                "DecisionPackageID": package_id,
                "FeedbackStatus": feedback_status,
                "Count": len(linked_requests),
                "Requests": [
                    _replan_request_to_dict(item) for item in linked_requests
                ],
            },
        }

    @app.get("/planner/workbench/release-authorizations")
    def planner_workbench_release_authorizations() -> dict[str, object]:
        return {
            "Endpoint": "/planner/workbench/release-authorizations",
            "StatusCode": 200,
            "Data": {
                "Count": len(release_authorizations),
                "Authorizations": [
                    _release_authorization_to_dict(item)
                    for item in release_authorizations
                ],
            },
        }

    @app.get("/planner/workbench/release-authorizations/stability-report")
    def planner_workbench_release_authorization_stability_report() -> dict[str, object]:
        return {
            "Endpoint": "/planner/workbench/release-authorizations/stability-report",
            "StatusCode": 200,
            "Data": {
                "Rows": build_release_stability_report(release_authorizations),
            },
        }

    def _mes_dispatch_priority_payload(
        *,
        endpoint: str,
        run_id: str,
        evaluated_at: datetime,
        operational_state_max_age_minutes: int,
        use_latest_operational_state: bool,
        operational_state_snapshot_id: str | None,
    ) -> dict[str, object] | JSONResponse:
        planning_run = planning_runs.get(run_id)
        if planning_run is None:
            return _planning_run_not_found(endpoint=endpoint, run_id=run_id)
        if planning_run.get("Status") != "Completed" or not isinstance(
            planning_run.get("Schedule"), dict
        ):
            return JSONResponse(
                status_code=409,
                content={
                    "Endpoint": endpoint,
                    "StatusCode": 409,
                    "Data": {"Status": "DispatchPriorityUnavailable", "RunID": run_id},
                },
            )
        snapshot = _operational_state_snapshot_for_release_evaluation(
            planning_run=planning_run,
            operational_state_snapshots=operational_state_snapshots,
            evaluated_at=evaluated_at,
            use_latest_operational_state=use_latest_operational_state,
            requested_snapshot_id=operational_state_snapshot_id,
        )
        if snapshot is None:
            return JSONResponse(
                status_code=404,
                content={
                    "Endpoint": endpoint,
                    "StatusCode": 404,
                    "Data": {"Status": "OperationalStateSnapshotNotFound"},
                },
            )
        freshness = evaluate_operational_state_freshness(
            snapshot=snapshot,
            evaluated_at=evaluated_at,
            max_age_minutes=operational_state_max_age_minutes,
        )
        master_data = master_data_versions.get(
            str(planning_run.get("MasterDataVersionID")), {}
        )
        release_policy = _release_policy_for_evaluation(
            planning_run=planning_run,
            requested_policy_id=None,
            dbr_release_policies=dbr_release_policies,
        )
        release_workbench = build_release_management_workbench(
            planning_run=planning_run,
            evaluated_at=evaluated_at,
            inventory_buffers=snapshot.inventory_buffers,
            material_requirements=_material_requirements_from_payload(
                [
                    MaterialRequirementPayload(**item)
                    for item in master_data.get("MaterialRequirements", [])
                    if isinstance(item, dict)
                ]
            ),
            wip_limits=snapshot.wip_limits,
            material_availability=snapshot.material_availability,
            operational_state_status=freshness.status,
            operational_state_captured_at=snapshot.captured_at,
            authorizations=release_authorizations,
            operational_state_snapshot_id=snapshot.snapshot_id,
            release_policy=release_policy,
        )
        return build_mes_dispatch_priority_queue(
            planning_run=planning_run,
            master_data_version=master_data,
            release_workbench=release_workbench,
            authorizations=release_authorizations,
            execution_events=execution_events,
            evaluated_at=evaluated_at,
        )

    @app.get("/planner/workbench/dispatch-priority/runs/{run_id}/workbench")
    def planner_workbench_dispatch_priority(
        run_id: str,
        evaluated_at: datetime,
        operational_state_max_age_minutes: int = Query(default=60, gt=0),
        use_latest_operational_state: bool = True,
        operational_state_snapshot_id: str | None = None,
    ):
        endpoint = f"/planner/workbench/dispatch-priority/runs/{run_id}/workbench"
        payload = _mes_dispatch_priority_payload(
            endpoint=endpoint,
            run_id=run_id,
            evaluated_at=evaluated_at,
            operational_state_max_age_minutes=operational_state_max_age_minutes,
            use_latest_operational_state=use_latest_operational_state,
            operational_state_snapshot_id=operational_state_snapshot_id,
        )
        if isinstance(payload, JSONResponse):
            return payload
        return {
            "Endpoint": endpoint,
            "StatusCode": 200,
            "Data": payload,
        }

    @app.get("/planner/workbench/mes/dispatch-suggestions/runs/{run_id}")
    def planner_workbench_mes_dispatch_suggestions(
        run_id: str,
        evaluated_at: datetime,
        operational_state_max_age_minutes: int = Query(default=60, gt=0),
        use_latest_operational_state: bool = True,
        operational_state_snapshot_id: str | None = None,
    ):
        endpoint = f"/planner/workbench/mes/dispatch-suggestions/runs/{run_id}"
        payload = _mes_dispatch_priority_payload(
            endpoint=endpoint,
            run_id=run_id,
            evaluated_at=evaluated_at,
            operational_state_max_age_minutes=operational_state_max_age_minutes,
            use_latest_operational_state=use_latest_operational_state,
            operational_state_snapshot_id=operational_state_snapshot_id,
        )
        if isinstance(payload, JSONResponse):
            return payload
        planning_run = planning_runs[str(run_id)]
        package = build_mes_dispatch_suggestion_package(
            dispatch_workbench=payload,
            schedule_fingerprint=str(planning_run.get("ScheduleFingerprint") or ""),
            generated_at=evaluated_at,
        )
        return {
            "Endpoint": endpoint,
            "StatusCode": 200,
            "Data": {"DispatchSuggestionPackage": package},
        }

    @app.post("/planner/workbench/mes/dispatch-suggestions/runs/{run_id}/issue")
    def planner_workbench_mes_dispatch_suggestions_issue(
        run_id: str,
        evaluated_at: datetime,
        issued_by: str = "planner-1",
        operational_state_max_age_minutes: int = Query(default=60, gt=0),
        use_latest_operational_state: bool = True,
        operational_state_snapshot_id: str | None = None,
    ):
        endpoint = f"/planner/workbench/mes/dispatch-suggestions/runs/{run_id}/issue"
        payload = _mes_dispatch_priority_payload(
            endpoint=endpoint,
            run_id=run_id,
            evaluated_at=evaluated_at,
            operational_state_max_age_minutes=operational_state_max_age_minutes,
            use_latest_operational_state=use_latest_operational_state,
            operational_state_snapshot_id=operational_state_snapshot_id,
        )
        if isinstance(payload, JSONResponse):
            return payload
        planning_run = planning_runs[str(run_id)]
        package = build_mes_dispatch_suggestion_package(
            dispatch_workbench=payload,
            schedule_fingerprint=str(planning_run.get("ScheduleFingerprint") or ""),
            generated_at=evaluated_at,
        )
        contract = find_integration_contract("MES-OUTBOUND-V1")
        assert contract is not None
        message = {
            "MessageID": package["PackageID"],
            "MessageType": "DispatchQueueIssued",
            "SourceSystem": "SDBR",
            "OccurredAt": evaluated_at.isoformat(),
            "Payload": {
                "IssuedBy": issued_by,
                "DispatchSuggestionPackage": package,
            },
        }
        validation = validate_integration_message(
            contract=contract,
            message=message,
            existing_messages=integration_messages,
            received_at=datetime.now(timezone.utc),
        )
        if validation["Status"] in {"Accepted", "Rejected"}:
            integration_messages.append(
                integration_message_record(
                    contract=contract,
                    message=message,
                    validation=validation,
                )
            )
        return {
            "Endpoint": endpoint,
            "StatusCode": 200,
            "Data": {
                "Status": "MockDispatchSuggestionIssued",
                "DispatchSuggestionPackage": package,
                "IntegrationMessage": validation,
            },
        }

    @app.get("/planner/workbench/ddom/operational-metrics")
    def planner_workbench_ddom_operational_metrics(
        evaluated_at: datetime,
        run_id: str | None = None,
        operational_state_max_age_minutes: int = Query(default=60, gt=0),
        use_latest_operational_state: bool = True,
        operational_state_snapshot_id: str | None = None,
    ):
        endpoint = "/planner/workbench/ddom/operational-metrics"
        selected_run_id = run_id or _latest_completed_run_id(planning_runs)
        if selected_run_id is None:
            return JSONResponse(
                status_code=404,
                content={
                    "Endpoint": endpoint,
                    "StatusCode": 404,
                    "Data": {"Status": "CompletedPlanningRunNotFound"},
                },
            )
        planning_run = planning_runs.get(selected_run_id)
        if planning_run is None:
            return _planning_run_not_found(endpoint=endpoint, run_id=selected_run_id)
        if planning_run.get("Status") != "Completed" or not isinstance(
            planning_run.get("Schedule"), dict
        ):
            return JSONResponse(
                status_code=409,
                content={
                    "Endpoint": endpoint,
                    "StatusCode": 409,
                    "Data": {
                        "RunID": selected_run_id,
                        "Status": "OperationalMetricsUnavailable",
                    },
                },
            )
        master_data = master_data_versions.get(
            str(planning_run.get("MasterDataVersionID")), {}
        )
        buffer_workbench = build_buffer_execution_workbench(
            planning_run=planning_run,
            master_data_version=master_data,
            authorizations=release_authorizations,
            execution_events=execution_events,
            evaluated_at=evaluated_at,
        )
        release_workbench: dict[str, object] = {
            "Summary": {
                "TotalCount": 0,
                "ReadyCount": 0,
                "BlockedCount": 0,
                "AuthorizedCount": sum(
                    1
                    for authorization in release_authorizations
                    if authorization.request_id == selected_run_id
                    and authorization.status == "Authorized"
                ),
            },
            "Candidates": [],
            "OperationalStateStatus": "Unavailable",
        }
        dispatch_workbench: dict[str, object] = {
            "Summary": {
                "ResourceCount": 0,
                "DispatchableOperationCount": 0,
                "CandidateWarningCount": 0,
                "QueueJumpSuggestionCount": 0,
                "PlannerConfirmationCount": 0,
                "ReplanSuggestionCount": 0,
            },
            "Resources": [],
        }
        snapshot = _operational_state_snapshot_for_release_evaluation(
            planning_run=planning_run,
            operational_state_snapshots=operational_state_snapshots,
            evaluated_at=evaluated_at,
            use_latest_operational_state=use_latest_operational_state,
            requested_snapshot_id=operational_state_snapshot_id,
        )
        if snapshot is not None:
            freshness = evaluate_operational_state_freshness(
                snapshot=snapshot,
                evaluated_at=evaluated_at,
                max_age_minutes=operational_state_max_age_minutes,
            )
            release_policy = _release_policy_for_evaluation(
                planning_run=planning_run,
                requested_policy_id=None,
                dbr_release_policies=dbr_release_policies,
            )
            release_workbench = build_release_management_workbench(
                planning_run=planning_run,
                evaluated_at=evaluated_at,
                inventory_buffers=snapshot.inventory_buffers,
                material_requirements=_material_requirements_from_payload(
                    [
                        MaterialRequirementPayload(**item)
                        for item in master_data.get("MaterialRequirements", [])
                        if isinstance(item, dict)
                    ]
                ),
                wip_limits=snapshot.wip_limits,
                material_availability=snapshot.material_availability,
                operational_state_status=freshness.status,
                operational_state_captured_at=snapshot.captured_at,
                authorizations=release_authorizations,
                operational_state_snapshot_id=snapshot.snapshot_id,
                release_policy=release_policy,
            )
            dispatch_payload = _mes_dispatch_priority_payload(
                endpoint=endpoint,
                run_id=selected_run_id,
                evaluated_at=evaluated_at,
                operational_state_max_age_minutes=operational_state_max_age_minutes,
                use_latest_operational_state=use_latest_operational_state,
                operational_state_snapshot_id=operational_state_snapshot_id,
            )
            if not isinstance(dispatch_payload, JSONResponse):
                dispatch_workbench = dispatch_payload
        return {
            "Endpoint": endpoint,
            "StatusCode": 200,
            "Data": build_ddom_operational_metrics(
                planning_run=planning_run,
                master_data_version=master_data,
                release_workbench=release_workbench,
                buffer_workbench=buffer_workbench,
                dispatch_workbench=dispatch_workbench,
                authorizations=release_authorizations,
                execution_events=execution_events,
                evaluated_at=evaluated_at,
            ),
        }

    @app.get("/planner/workbench/release-authorizations/{authorization_id}/dispatch-package")
    def planner_workbench_release_authorization_dispatch_package(authorization_id: str):
        endpoint = (
            f"/planner/workbench/release-authorizations/{authorization_id}"
            "/dispatch-package"
        )
        authorization = next(
            (
                item
                for item in release_authorizations
                if item.authorization_id == authorization_id
            ),
            None,
        )
        if authorization is None:
            return JSONResponse(
                status_code=404,
                content={
                    "Endpoint": endpoint,
                    "StatusCode": 404,
                    "Data": {
                        "AuthorizationID": authorization_id,
                        "Status": "ReleaseAuthorizationNotFound",
                        "Message": f"Release authorization {authorization_id} was not found.",
                    },
                },
            )
        return {
            "Endpoint": endpoint,
            "StatusCode": 200,
            "Data": {
                "DispatchPackage": build_dispatch_package(authorization),
            },
        }

    @app.post("/shop-floor/execution/event")
    def shop_floor_execution_event(payload: ExecutionEventPayload):
        if payload.AuthorizationID is not None:
            authorization = next(
                (
                    item
                    for item in release_authorizations
                    if item.authorization_id == payload.AuthorizationID
                ),
                None,
            )
            if authorization is None:
                return JSONResponse(
                    status_code=404,
                    content={
                        "Endpoint": "/shop-floor/execution/event",
                        "StatusCode": 404,
                        "Data": {
                            "Accepted": False,
                            "Status": "ExecutionAuthorizationNotFound",
                            "Message": (
                                f"Release authorization {payload.AuthorizationID} "
                                "was not found."
                            ),
                            "RequiresExceptionCode": False,
                            "RequiresReview": False,
                        },
                    },
                )
            if authorization.order_id != payload.OrderID:
                return JSONResponse(
                    status_code=409,
                    content={
                        "Endpoint": "/shop-floor/execution/event",
                        "StatusCode": 409,
                        "Data": {
                            "Accepted": False,
                            "Status": "ExecutionAuthorizationMismatch",
                            "Message": (
                                f"Authorization {payload.AuthorizationID} belongs "
                                f"to order {authorization.order_id}."
                            ),
                            "RequiresExceptionCode": False,
                            "RequiresReview": False,
                        },
                    },
                )
        result = validate_execution_event(
            ExecutionEvent(
                order_id=payload.OrderID,
                event_type=payload.EventType,
                event_at=payload.EventAt,
                target_start_at=payload.TargetStartAt,
                exception_code=payload.ExceptionCode,
            )
        )
        status_code = 200 if result.accepted else 409
        if result.accepted:
            event_record = {
                "OrderID": payload.OrderID,
                "EventType": payload.EventType,
                "EventAt": payload.EventAt.isoformat(),
                "TargetStartAt": payload.TargetStartAt.isoformat(),
                "ExceptionCode": payload.ExceptionCode,
                "Status": result.status,
                "RequiresReview": result.requires_review,
            }
            if payload.AuthorizationID is not None:
                event_record["AuthorizationID"] = payload.AuthorizationID
            if payload.OperationID is not None:
                event_record["OperationID"] = payload.OperationID
            if payload.ResourceID is not None:
                event_record["ResourceID"] = payload.ResourceID
            if payload.DispatchConflictResult is not None:
                event_record["DispatchConflictResult"] = (
                    payload.DispatchConflictResult
                )
            execution_events.append(event_record)
        body = {
            "Endpoint": "/shop-floor/execution/event",
            "StatusCode": status_code,
            "Data": {
                "Accepted": result.accepted,
                "Status": result.status,
                "Message": result.message,
                "RequiresExceptionCode": result.requires_exception_code,
                "RequiresReview": result.requires_review,
            },
        }
        if status_code != 200:
            return JSONResponse(status_code=status_code, content=body)
        return body

    @app.get("/shop-floor/execution/events")
    def shop_floor_execution_events() -> dict[str, object]:
        return {
            "Endpoint": "/shop-floor/execution/events",
            "StatusCode": 200,
            "Data": {
                "Events": execution_events,
                "Summary": _execution_event_summary(execution_events),
            },
        }

    @app.get("/shop-floor/execution/authorized-status")
    def shop_floor_execution_authorized_status() -> dict[str, object]:
        dispatch_packages = [
            build_dispatch_package(authorization)
            for authorization in release_authorizations
        ]
        return {
            "Endpoint": "/shop-floor/execution/authorized-status",
            "StatusCode": 200,
            "Data": {
                "Rows": build_authorized_execution_status(
                    dispatch_packages,
                    execution_events,
                ),
            },
        }

    @app.get("/shop-floor/execution/authorized-alerts")
    def shop_floor_execution_authorized_alerts(EvaluatedAt: datetime) -> dict[str, object]:
        dispatch_packages = [
            build_dispatch_package(authorization)
            for authorization in release_authorizations
        ]
        return {
            "Endpoint": "/shop-floor/execution/authorized-alerts",
            "StatusCode": 200,
            "Data": {
                "EvaluatedAt": EvaluatedAt.isoformat(),
                "Alerts": build_authorized_execution_alerts(
                    dispatch_packages=dispatch_packages,
                    events=execution_events,
                    evaluated_at=EvaluatedAt,
                ),
            },
        }

    @app.get("/shop-floor/execution/exception-codes")
    def shop_floor_exception_codes() -> dict[str, object]:
        return {
            "Endpoint": "/shop-floor/execution/exception-codes",
            "StatusCode": 200,
            "Data": [
                {
                    "Code": definition.code,
                    "DisplayName": definition.display_name,
                    "Category": definition.category,
                }
                for definition in default_exception_codes().values()
            ],
        }

    @app.get("/planner/workbench", response_class=HTMLResponse)
    def planner_workbench_page() -> str:
        return _planner_shell_html()

    return app


_runtime_environment = resolve_runtime_environment()
app = create_app(
    state_store=SQLiteWorkbenchStateStore(_runtime_environment.database_path),
    runtime_environment=_runtime_environment,
)


def _resources_from_payload(resources: list[ResourcePayload]) -> list[Resource]:
    return [
        Resource(
            resource_id=item.ResourceID,
            name=item.Name,
            is_constraint=item.IsConstraint,
            daily_capacity_minutes={
                date.fromisoformat(bucket_date): minutes
                for bucket_date, minutes in item.DailyCapacityMinutes.items()
            },
            calendar=_calendar_from_payload(item.Calendar),
            capacity_units=item.CapacityUnits,
            efficiency_percent=item.EfficiencyPercent,
            resource_type=item.ResourceType,
            is_buffered=item.IsBuffered,
            owner_id=item.OwnerID,
            category=item.Category,
        )
        for item in resources
    ]


def _resource_capacity_import_rows_from_payload(
    rows: list[ResourceCapacityImportRowPayload],
) -> list[ResourceCapacityImportRow]:
    return [
        ResourceCapacityImportRow(
            resource_id=row.ResourceID,
            name=row.Name,
            is_constraint=row.IsConstraint,
            capacity_date=row.CapacityDate,
            capacity_minutes=row.CapacityMinutes,
        )
        for row in rows
    ]


def _calendar_import_rows_from_payload(
    rows: list[CalendarImportRowPayload],
) -> list[CalendarImportRow]:
    return [
        CalendarImportRow(
            resource_id=row.ResourceID,
            calendar_id=row.CalendarID,
            working_weekdays=row.WorkingWeekdays,
            shift_name=row.ShiftName,
            shift_start=row.ShiftStart,
            shift_end=row.ShiftEnd,
            holiday=row.Holiday,
            maintenance_start=row.MaintenanceStart,
            maintenance_end=row.MaintenanceEnd,
        )
        for row in rows
    ]


def _resources_from_import_payload(payload: ResourceImportPayload) -> list[Resource]:
    resources = import_resources_from_capacity_rows(
        _resource_capacity_import_rows_from_payload(payload.Rows)
    )
    if not payload.CalendarRows:
        return resources
    return attach_work_calendars_to_resources(
        resources,
        import_work_calendars_from_rows(_calendar_import_rows_from_payload(payload.CalendarRows)),
    )


def _resources_to_payload_dict(resources: list[Resource]) -> list[dict[str, object]]:
    payloads: list[dict[str, object]] = []
    for resource in resources:
        payload: dict[str, object] = {
            "ResourceID": resource.resource_id,
            "Name": resource.name,
            "IsConstraint": resource.is_constraint,
            "DailyCapacityMinutes": {
                bucket_date.isoformat(): minutes
                for bucket_date, minutes in resource.daily_capacity_minutes.items()
            },
        }
        if resource.capacity_units != 1:
            payload["CapacityUnits"] = resource.capacity_units
        if resource.efficiency_percent != 100:
            payload["EfficiencyPercent"] = resource.efficiency_percent
        if resource.resource_type is not None:
            payload["ResourceType"] = resource.resource_type
        if resource.is_buffered:
            payload["IsBuffered"] = resource.is_buffered
        if resource.owner_id is not None:
            payload["OwnerID"] = resource.owner_id
        if resource.category is not None:
            payload["Category"] = resource.category
        if resource.calendar is not None:
            payload["Calendar"] = _calendar_to_payload_dict(resource.calendar)
        payloads.append(payload)
    return payloads


def _calendar_to_payload_dict(calendar: WorkCalendar) -> dict[str, object]:
    return {
        "CalendarID": calendar.calendar_id,
        "WorkingWeekdays": sorted(calendar.working_weekdays),
        "Shifts": [
            {
                "Name": shift.name,
                "Start": shift.start.isoformat(),
                "End": shift.end.isoformat(),
            }
            for shift in calendar.shifts
        ],
        "MaintenanceWindows": [
            {
                "Start": maintenance.start.isoformat(),
                "End": maintenance.end.isoformat(),
            }
            for maintenance in calendar.maintenance_windows
        ],
        "Holidays": [
            holiday.isoformat()
            for holiday in sorted(calendar.holidays or set())
        ],
    }


def _calendar_from_payload(calendar: CalendarPayload | None) -> WorkCalendar | None:
    if calendar is None:
        return None
    return WorkCalendar(
        calendar_id=calendar.CalendarID,
        working_weekdays=set(calendar.WorkingWeekdays),
        shifts=[
            Shift(
                name=shift.Name,
                start=shift.Start,
                end=shift.End,
            )
            for shift in calendar.Shifts
        ],
        maintenance_windows=[
            MaintenanceWindow(
                start=window.Start,
                end=window.End,
            )
            for window in calendar.MaintenanceWindows
        ],
        holidays=set(calendar.Holidays),
    )


def _routings_from_payload(routings: list[RoutingPayload]) -> list[Routing]:
    return [
        Routing(
            product_id=item.ProductID,
            routing_id=item.RoutingID,
            is_primary=item.IsPrimary,
            operations=[
                Operation(
                    operation_id=operation.OperationID,
                    resource_id=operation.ResourceID,
                    duration_minutes=operation.DurationMinutes,
                    sequence=operation.Sequence,
                    alternate_resource_ids=operation.AlternateResourceIDs,
                    setup_family=operation.SetupFamily or item.ProductID,
                    earliest_start_at=operation.EarliestStartAt,
                    latest_end_at=operation.LatestEndAt,
                )
                for operation in item.Operations
            ],
        )
        for item in routings
    ]


def _routing_import_rows_from_payload(
    rows: list[RoutingImportRowPayload],
) -> list[RoutingImportRow]:
    return [
        RoutingImportRow(
            product_id=row.ProductID,
            routing_id=row.RoutingID,
            is_primary=row.IsPrimary,
            operation_id=row.OperationID,
            resource_id=row.ResourceID,
            duration_minutes=row.DurationMinutes,
            sequence=row.Sequence,
            alternate_resource_ids=row.AlternateResourceIDs,
        )
        for row in rows
    ]


def _routings_to_payload_dict(routings: list[Routing]) -> list[dict[str, object]]:
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
                    **(
                        {"SetupFamily": operation.setup_family}
                        if operation.setup_family is not None
                        else {}
                    ),
                    **(
                        {"EarliestStartAt": operation.earliest_start_at.isoformat()}
                        if operation.earliest_start_at is not None
                        else {}
                    ),
                    **(
                        {"LatestEndAt": operation.latest_end_at.isoformat()}
                        if operation.latest_end_at is not None
                        else {}
                    ),
                }
                for operation in routing.operations
            ],
        }
        for routing in routings
    ]


def _orders_from_payload(orders: list[OrderPayload]) -> list[SchedulingOrder]:
    return [
        SchedulingOrder(
            order_id=item.OrderID,
            product_id=item.ProductID,
            quantity=item.Quantity,
            due_date=item.DueDate,
            target_start_date=item.TargetStartDate,
        )
        for item in orders
    ]


def _order_import_rows_from_payload(
    rows: list[OrderImportRowPayload],
) -> list[OrderImportRow]:
    return [
        OrderImportRow(
            order_id=row.OrderID,
            product_id=row.ProductID,
            quantity=row.Quantity,
            due_date=row.DueDate,
            target_start_date=row.TargetStartDate,
        )
        for row in rows
    ]


def _orders_to_payload_dict(orders: list[SchedulingOrder]) -> list[dict[str, object]]:
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


def _setup_transitions_from_payload(
    transitions: list[SetupTransitionPayload],
) -> list[SetupTransition]:
    return [
        SetupTransition(
            resource_id=item.ResourceID,
            from_family=item.FromFamily,
            to_family=item.ToFamily,
            setup_minutes=item.SetupMinutes,
        )
        for item in transitions
    ]


def _setup_transitions_to_payload_dict(
    transitions: list[SetupTransition],
) -> list[dict[str, object]]:
    return [
        {
            "ResourceID": transition.resource_id,
            "FromFamily": transition.from_family,
            "ToFamily": transition.to_family,
            "SetupMinutes": transition.setup_minutes,
        }
        for transition in transitions
    ]


def _inventory_buffers_from_payload(
    inventory_buffers: list[InventoryBufferPayload],
) -> list[InventoryBufferPolicy]:
    return [
        InventoryBufferPolicy(
            item_id=item.ItemID,
            location_id=item.LocationID,
            on_hand_qty=item.OnHandQty,
            red_zone_qty=item.RedZoneQty,
            yellow_zone_qty=item.YellowZoneQty,
            green_zone_qty=item.GreenZoneQty,
        )
        for item in inventory_buffers
    ]


def _inventory_buffer_import_rows_from_payload(
    rows: list[InventoryBufferImportRowPayload],
) -> list[InventoryBufferImportRow]:
    return [
        InventoryBufferImportRow(
            item_id=row.ItemID,
            location_id=row.LocationID,
            on_hand_qty=row.OnHandQty,
            red_zone_qty=row.RedZoneQty,
            yellow_zone_qty=row.YellowZoneQty,
            green_zone_qty=row.GreenZoneQty,
        )
        for row in rows
    ]


def _inventory_buffers_from_dicts(rows: object) -> list[InventoryBufferPolicy]:
    if not isinstance(rows, list):
        return []
    return [
        InventoryBufferPolicy(
            item_id=str(row["ItemID"]),
            location_id=str(row["LocationID"]),
            on_hand_qty=float(row["OnHandQty"]),
            red_zone_qty=float(row["RedZoneQty"]),
            yellow_zone_qty=float(row["YellowZoneQty"]),
            green_zone_qty=float(row["GreenZoneQty"]),
        )
        for row in rows
        if isinstance(row, dict)
    ]


def _material_requirements_from_payload(
    rows: list[MaterialRequirementPayload],
) -> list[MaterialRequirement]:
    return [
        MaterialRequirement(
            order_id=row.OrderID,
            item_id=row.ItemID,
            location_id=row.LocationID,
            required_qty=row.RequiredQty,
        )
        for row in rows
    ]


def _ddmrp_decoupling_points_from_payload(
    rows: list[DdmrpDecouplingPointPayload],
) -> list[DecouplingPoint]:
    return [
        DecouplingPoint(
            item_id=row.ItemID,
            location_id=row.LocationID,
            buffer_profile_id=row.BufferProfileID,
            dlt_minutes=row.DLTMinutes,
            order_multiple_qty=row.OrderMultipleQty,
            minimum_order_qty=row.MinimumOrderQty,
            status=row.Status,
        )
        for row in rows
    ]


def _ddmrp_demand_signals_from_payload(
    rows: list[DdmrpDemandSignalPayload],
) -> list[DemandSignal]:
    return [
        DemandSignal(
            item_id=row.ItemID,
            location_id=row.LocationID,
            demand_qty=row.DemandQty,
            demand_due_at=row.DemandDueAt,
            demand_type=row.DemandType,
            is_qualified_spike=row.IsQualifiedSpike,
        )
        for row in rows
    ]


def _ddmrp_open_supply_from_payload(
    rows: list[DdmrpOpenSupplyPayload],
) -> list[OpenSupply]:
    return [
        OpenSupply(
            item_id=row.ItemID,
            location_id=row.LocationID,
            supply_qty=row.SupplyQty,
            expected_at=row.ExpectedAt,
            status=row.Status,
        )
        for row in rows
    ]


def _ddmrp_decoupling_points_from_dicts(rows: object) -> list[DecouplingPoint]:
    if not isinstance(rows, list):
        return []
    return [
        DecouplingPoint(
            item_id=str(row["ItemID"]),
            location_id=str(row["LocationID"]),
            buffer_profile_id=str(row["BufferProfileID"]),
            dlt_minutes=int(row["DLTMinutes"]),
            order_multiple_qty=float(row.get("OrderMultipleQty", 0.0)),
            minimum_order_qty=float(row.get("MinimumOrderQty", 0.0)),
            status=str(row.get("Status", "Active")),
        )
        for row in rows
        if isinstance(row, dict)
    ]


def _ddmrp_demand_signals_from_dicts(rows: object) -> list[DemandSignal]:
    if not isinstance(rows, list):
        return []
    return [
        DemandSignal(
            item_id=str(row["ItemID"]),
            location_id=str(row["LocationID"]),
            demand_qty=float(row["DemandQty"]),
            demand_due_at=_datetime_from_value(row["DemandDueAt"]),
            demand_type=str(row.get("DemandType", "CustomerOrder")),
            is_qualified_spike=bool(row.get("IsQualifiedSpike", False)),
        )
        for row in rows
        if isinstance(row, dict)
    ]


def _ddmrp_open_supply_from_dicts(rows: object) -> list[OpenSupply]:
    if not isinstance(rows, list):
        return []
    return [
        OpenSupply(
            item_id=str(row["ItemID"]),
            location_id=str(row["LocationID"]),
            supply_qty=float(row["SupplyQty"]),
            expected_at=(
                _datetime_from_value(row["ExpectedAt"])
                if row.get("ExpectedAt") is not None
                else None
            ),
            status=str(row.get("Status", "Open")),
        )
        for row in rows
        if isinstance(row, dict)
    ]


def _ddmrp_decoupling_points_to_payload_dict(
    rows: list[DecouplingPoint],
) -> list[dict[str, object]]:
    return [row.to_dict() for row in rows]


def _ddmrp_demand_signals_to_payload_dict(
    rows: list[DemandSignal],
) -> list[dict[str, object]]:
    return [row.to_dict() for row in rows]


def _ddmrp_open_supply_to_payload_dict(
    rows: list[OpenSupply],
) -> list[dict[str, object]]:
    return [row.to_dict() for row in rows]


def _datetime_from_value(value: object) -> datetime:
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value))


def _wip_limits_from_payload(rows: list[WipLimitPayload]) -> list[WipLimit]:
    return [
        WipLimit(
            scope_id=row.ScopeID,
            current_wip_count=row.CurrentWipCount,
            max_wip_count=row.MaxWipCount,
            order_wip_increment=row.OrderWipIncrement,
        )
        for row in rows
    ]


def _wip_limit_import_rows_from_payload(rows: list[WipLimitPayload]) -> list[WipLimitImportRow]:
    return [
        WipLimitImportRow(
            scope_id=row.ScopeID,
            current_wip_count=row.CurrentWipCount,
            max_wip_count=row.MaxWipCount,
            order_wip_increment=row.OrderWipIncrement,
        )
        for row in rows
    ]


def _wip_limits_to_payload_dict(wip_limits: list[WipLimit]) -> list[dict[str, object]]:
    return [
        {
            "ScopeID": item.scope_id,
            "CurrentWipCount": item.current_wip_count,
            "MaxWipCount": item.max_wip_count,
            "OrderWipIncrement": item.order_wip_increment,
        }
        for item in wip_limits
    ]


def _material_availability_from_payload(
    rows: list[MaterialAvailabilityPayload],
) -> list[MaterialAvailability]:
    return [
        MaterialAvailability(
            item_id=row.ItemID,
            location_id=row.LocationID,
            allocated_qty=row.AllocatedQty,
            inbound_qty=row.InboundQty,
            inbound_available_at=row.InboundAvailableAt,
        )
        for row in rows
    ]


def _material_availability_import_rows_from_payload(
    rows: list[MaterialAvailabilityPayload],
) -> list[MaterialAvailabilityImportRow]:
    return [
        MaterialAvailabilityImportRow(
            item_id=row.ItemID,
            location_id=row.LocationID,
            allocated_qty=row.AllocatedQty,
            inbound_qty=row.InboundQty,
            inbound_available_at=row.InboundAvailableAt,
        )
        for row in rows
    ]


def _material_availability_to_payload_dict(
    material_availability: list[MaterialAvailability],
) -> list[dict[str, object]]:
    return [
        {
            "ItemID": item.item_id,
            "LocationID": item.location_id,
            "AllocatedQty": item.allocated_qty,
            "InboundQty": item.inbound_qty,
            "InboundAvailableAt": (
                item.inbound_available_at.isoformat()
                if item.inbound_available_at is not None
                else None
            ),
        }
        for item in material_availability
    ]


def _operational_state_snapshot_to_dict(
    snapshot: OperationalStateSnapshot,
) -> dict[str, object]:
    return {
        "SnapshotID": snapshot.snapshot_id,
        "CapturedAt": snapshot.captured_at.isoformat(),
        "InventoryBuffers": _inventory_buffers_to_payload_dict(
            snapshot.inventory_buffers
        ),
        "MaterialAvailability": _material_availability_to_payload_dict(
            snapshot.material_availability
        ),
        "WipLimits": _wip_limits_to_payload_dict(snapshot.wip_limits),
    }


def _material_requirements_from_import_payload(
    payload: MasterDataImportPayload,
) -> list[MaterialRequirement]:
    return [
        MaterialRequirement(
            order_id=row.OrderID,
            item_id=row.ItemID,
            location_id=row.LocationID,
            required_qty=row.RequiredQty,
        )
        for row in payload.MaterialRequirementRows
    ]


def _material_requirements_to_payload_dict(
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


def _inventory_buffers_to_payload_dict(
    inventory_buffers: list[InventoryBufferPolicy],
) -> list[dict[str, object]]:
    return [
        {
            "ItemID": item.item_id,
            "LocationID": item.location_id,
            "OnHandQty": item.on_hand_qty,
            "RedZoneQty": item.red_zone_qty,
            "YellowZoneQty": item.yellow_zone_qty,
            "GreenZoneQty": item.green_zone_qty,
        }
        for item in inventory_buffers
    ]


def _release_decision_response_body(
    *,
    endpoint: str,
    order_id: str,
    requested_release_at: datetime,
    suggested_release_at: datetime,
    inventory_buffers: list[InventoryBufferPolicy],
    material_requirements: list[MaterialRequirement],
) -> tuple[dict[str, object], int]:
    decision = evaluate_release_decision(
        order_id=order_id,
        requested_release_at=requested_release_at,
        suggested_release_at=suggested_release_at,
    )
    return _release_decision_body(
        endpoint=endpoint,
        decision=decision,
        inventory_buffers=inventory_buffers,
        material_requirements=material_requirements,
    )


def _release_stability_to_dict(
    result: ReleaseStabilityResult,
    *,
    consecutive_blocked_count: int,
) -> dict[str, object]:
    return {
        "DeviationMinutes": result.deviation_minutes,
        "AbsoluteDeviationMinutes": result.absolute_deviation_minutes,
        "TimingStatus": result.timing_status,
        "Severity": result.severity,
        "Action": result.action,
        "ReplanRequired": result.replan_required,
        "ReasonCode": result.reason_code,
        "ConsecutiveBlockedCount": consecutive_blocked_count,
    }


def _replan_request_to_dict(request: ReplanRequest) -> dict[str, object]:
    return {
        "RequestID": request.request_id,
        "ProblemID": request.problem_id,
        "OrderID": request.order_id,
        "PlannedReleaseAt": request.planned_release_at.isoformat(),
        "DetectedAt": request.detected_at.isoformat(),
        "ReasonCode": request.reason_code,
        "DeviationMinutes": request.deviation_minutes,
        "ConsecutiveBlockedCount": request.consecutive_blocked_count,
        "Source": request.source,
        "SourceReferenceID": request.source_reference_id,
        "RequestedBy": request.requested_by,
        "Status": request.status,
        "DecidedBy": request.decided_by,
        "DecidedAt": (
            request.decided_at.isoformat()
            if request.decided_at is not None
            else None
        ),
        "DecisionComment": request.decision_comment,
        "ExecutionStartedAt": (
            request.execution_started_at.isoformat()
            if request.execution_started_at is not None
            else None
        ),
        "ExecutionCompletedAt": (
            request.execution_completed_at.isoformat()
            if request.execution_completed_at is not None
            else None
        ),
        "SolverBackendID": request.solver_backend_id,
        "SolverStatus": request.solver_status,
        "SolverMessage": request.solver_message,
    }


def _release_authorization_to_dict(
    authorization: ReleaseAuthorization,
) -> dict[str, object]:
    result = {
        "AuthorizationID": authorization.authorization_id,
        "RequestID": authorization.request_id,
        "OrderID": authorization.order_id,
        "ReleasedBy": authorization.released_by,
        "ReleasedAt": authorization.released_at.isoformat(),
        "ScheduledStart": authorization.scheduled_start,
        "ScheduledEnd": authorization.scheduled_end,
        "SuggestedReleaseAt": authorization.suggested_release_at,
        "Status": authorization.status,
    }
    if authorization.operational_state_snapshot_id is not None:
        result["OperationalStateSnapshotID"] = (
            authorization.operational_state_snapshot_id
        )
        result["OperationalStateCapturedAt"] = (
            authorization.operational_state_captured_at
        )
    if authorization.decision_package_id is not None:
        result["DecisionPackageID"] = authorization.decision_package_id
    if authorization.release_policy_version_id is not None:
        result["ReleasePolicyVersionID"] = authorization.release_policy_version_id
    if authorization.release_policy_evidence is not None:
        result["ReleasePolicyEvidence"] = authorization.release_policy_evidence
    return result


def _dict_schedule(planning_run: dict[str, object]) -> dict[str, object]:
    schedule = planning_run.get("Schedule")
    return schedule if isinstance(schedule, dict) else {}


def _superseded_by_run_id(
    *,
    run_id: str,
    planning_runs: dict[str, dict[str, object]],
) -> str | None:
    return next(
        (
            str(other.get("RunID"))
            for other in planning_runs.values()
            if other.get("SupersedesRunID") == run_id
        ),
        None,
    )


def _release_authorization_evidence_to_dict(
    authorization: ReleaseAuthorization,
) -> dict[str, object]:
    return {
        "DecisionPackageID": authorization.decision_package_id,
        "OperationalStateSnapshotID": authorization.operational_state_snapshot_id,
        "OperationalStateCapturedAt": authorization.operational_state_captured_at,
        "ReleasePolicyVersionID": authorization.release_policy_version_id,
        "ReleasePolicyEvidence": authorization.release_policy_evidence,
    }


def _overall_execution_status(rows: list[dict[str, object]]) -> str:
    if not rows:
        return "NotAuthorized"
    if any(row.get("RequiresReview") is True for row in rows):
        return "ReviewRequired"
    statuses = {str(row["ExecutionStatus"]) for row in rows}
    if statuses == {"Shipped"}:
        return "Shipped"
    if statuses <= {"Completed", "Shipped"}:
        return "Completed"
    if statuses == {"Authorized"}:
        return "Authorized"
    if statuses & {"ArrivedBuffer", "InProcess", "InExecution"}:
        return "InProcess"
    return "InExecution"


def _release_decision_body(
    *,
    endpoint: str,
    decision: ReleaseDecision,
    inventory_buffers: list[InventoryBufferPolicy],
    material_requirements: list[MaterialRequirement],
) -> tuple[dict[str, object], int]:
    inventory_risks = _inventory_release_risks(
        order_id=decision.order_id,
        inventory_buffers=inventory_buffers,
        material_requirements=material_requirements,
    )
    if decision.allowed and inventory_risks:
        return (
            {
                "Endpoint": endpoint,
                "StatusCode": 409,
                "Data": {
                    "OrderID": decision.order_id,
                    "Allowed": False,
                    "Status": "ReleaseBlockedByInventoryBuffer",
                    "Message": "Hold release until required material buffers recover above red zone.",
                    "RequestedReleaseAt": decision.requested_release_at.isoformat(),
                    "SuggestedReleaseAt": decision.suggested_release_at.isoformat(),
                    "MinutesEarly": decision.minutes_early,
                    "InventoryRisks": inventory_risks,
                },
            },
            409,
        )
    status_code = 200 if decision.allowed else 409
    return (
        {
            "Endpoint": endpoint,
            "StatusCode": status_code,
            "Data": {
                "OrderID": decision.order_id,
                "Allowed": decision.allowed,
                "Status": decision.status,
                "Message": decision.message,
                "RequestedReleaseAt": decision.requested_release_at.isoformat(),
                "SuggestedReleaseAt": decision.suggested_release_at.isoformat(),
                "MinutesEarly": decision.minutes_early,
                "InventoryRisks": inventory_risks,
            },
        },
        status_code,
    )


def _inventory_release_risks(
    *,
    order_id: str,
    inventory_buffers: list[InventoryBufferPolicy],
    material_requirements: list[MaterialRequirement],
) -> list[dict[str, object]]:
    buffers_by_key = {
        (buffer.item_id, buffer.location_id): buffer
        for buffer in inventory_buffers
    }
    risks: list[dict[str, object]] = []
    for requirement in material_requirements:
        if requirement.order_id != order_id:
            continue
        buffer = buffers_by_key.get((requirement.item_id, requirement.location_id))
        if buffer is None:
            continue
        projected_on_hand = buffer.on_hand_qty - requirement.required_qty
        if projected_on_hand < buffer.red_zone_qty:
            risks.append(
                {
                    "OrderID": requirement.order_id,
                    "ItemID": requirement.item_id,
                    "LocationID": requirement.location_id,
                    "RequiredQty": requirement.required_qty,
                    "OnHandQty": buffer.on_hand_qty,
                    "ProjectedOnHandQty": projected_on_hand,
                    "RedZoneQty": buffer.red_zone_qty,
                    "Message": (
                        f"Releasing order {requirement.order_id} would project "
                        f"{requirement.item_id} at {requirement.location_id} "
                        "below the red zone."
                    ),
                }
            )
    return risks


def _entities_from_master_data_import_payload(
    payload: MasterDataImportPayload,
) -> tuple[
    list[Resource],
    list[Routing],
    list[SchedulingOrder],
    list[InventoryBufferPolicy],
]:
    resources = _resources_from_import_payload(
        ResourceImportPayload(
            Rows=payload.ResourceRows,
            CalendarRows=payload.CalendarRows,
            CalendarTimezone=payload.CalendarTimezone,
        )
    )
    routings = import_routings_from_operation_rows(
        _routing_import_rows_from_payload(payload.RoutingRows)
    )
    orders = import_orders_from_rows(_order_import_rows_from_payload(payload.OrderRows))
    inventory_buffers = import_inventory_buffers_from_rows(
        _inventory_buffer_import_rows_from_payload(payload.InventoryBufferRows)
    )
    return resources, routings, orders, inventory_buffers


def _master_data_version_from_payload(
    payload: MasterDataVersionPayload,
) -> dict[str, object]:
    resources, routings, orders, inventory_buffers = _entities_from_master_data_import_payload(
        payload
    )
    material_requirements = _material_requirements_from_import_payload(payload)
    validation = validate_master_data(
        resources=resources,
        routings=routings,
        orders=orders,
        inventory_buffers=inventory_buffers,
        material_requirements=material_requirements,
        calendar_timezone=payload.CalendarTimezone,
    )
    return {
        "VersionID": payload.VersionID,
        "CapturedAt": payload.CapturedAt.isoformat(),
        "SourceSystem": payload.SourceSystem,
        "CreatedBy": payload.CreatedBy,
        "CalendarTimezone": payload.CalendarTimezone,
        "Status": "Valid" if validation.is_valid else "Invalid",
        "PublicationStatus": "Draft",
        "Summary": validation.summary,
        "Resources": _resources_to_payload_dict(resources),
        "Routings": _routings_to_payload_dict(routings),
        "Orders": _orders_to_payload_dict(orders),
        "InventoryBuffers": _inventory_buffers_to_payload_dict(inventory_buffers),
        "MaterialRequirements": _material_requirements_to_payload_dict(
            material_requirements
        ),
        "DdmrpDecouplingPoints": _ddmrp_decoupling_points_to_payload_dict(
            _ddmrp_decoupling_points_from_payload(payload.DdmrpDecouplingPointRows)
        ),
        "DdmrpDemandSignals": _ddmrp_demand_signals_to_payload_dict(
            _ddmrp_demand_signals_from_payload(payload.DdmrpDemandSignalRows)
        ),
        "DdmrpOpenSupply": _ddmrp_open_supply_to_payload_dict(
            _ddmrp_open_supply_from_payload(payload.DdmrpOpenSupplyRows)
        ),
        "Validation": _master_data_validation_to_dict(validation),
    }


def _planning_run_reference_error(
    *,
    endpoint: str,
    entity_id: str,
    status: str,
    message: str,
) -> JSONResponse:
    return JSONResponse(
        status_code=404,
        content={
            "Endpoint": endpoint,
            "StatusCode": 404,
            "Data": {
                "EntityID": entity_id,
                "Status": status,
                "Message": message,
            },
        },
    )


def _planning_run_not_found(*, endpoint: str, run_id: str) -> JSONResponse:
    return JSONResponse(
        status_code=404,
        content={
            "Endpoint": endpoint,
            "StatusCode": 404,
            "Data": {
                "RunID": run_id,
                "Status": "PlanningRunNotFound",
                "Message": f"Planning run {run_id} was not found.",
            },
        },
    )


def _planning_run_publication_transition_response(
    *,
    endpoint: str,
    run_id: str,
    action: str,
    payload: PlanPublicationTransitionPayload,
    request: Request,
    planning_runs: dict[str, dict[str, object]],
    audit_events: list[dict[str, object]],
):
    planning_run = planning_runs.get(run_id)
    if planning_run is None:
        return _planning_run_not_found(endpoint=endpoint, run_id=run_id)
    if action in {"Publish", "Revoke"}:
        actor_role = getattr(request.state, "actor_role", None)
        if actor_role is not None and actor_role != "Admin":
            return JSONResponse(
                status_code=403,
                content={
                    "Endpoint": endpoint,
                    "StatusCode": 403,
                    "Data": {
                        "Status": "PermissionDenied",
                        "ActorID": payload.ActorID,
                        "ActorRole": actor_role,
                        "Message": (
                            "Only Admin actors can publish or revoke plans."
                        ),
                    },
                },
            )
    try:
        updated = transition_publication_state(
            planning_run=planning_run,
            action=action,
            actor_id=_effective_actor_id(request, payload.ActorID),
            occurred_at=payload.OccurredAt,
            comment=payload.Comment,
            target_systems=payload.TargetSystems,
        )
    except ValueError as error:
        return JSONResponse(
            status_code=409,
            content={
                "Endpoint": endpoint,
                "StatusCode": 409,
                "Data": {
                    "RunID": run_id,
                    "Status": "PublicationTransitionConflict",
                    "CurrentPublicationStatus": publication_state(planning_run),
                    "Message": str(error),
                },
            },
        )

    if action == "Publish":
        for other_id, other in list(planning_runs.items()):
            if (
                other_id != run_id
                and other.get("ProblemID") == planning_run.get("ProblemID")
                and publication_state(other) == "Published"
            ):
                superseded = mark_superseded(
                    planning_run=other,
                    superseded_by_run_id=run_id,
                    actor_id=_effective_actor_id(request, payload.ActorID),
                    occurred_at=payload.OccurredAt,
                )
                planning_runs[other_id] = superseded
                _append_planning_run_audit_event(
                    audit_events=audit_events,
                    run_id=other_id,
                    action="PlanPublicationSuperseded",
                    actor_id=_effective_actor_id(request, payload.ActorID),
                    occurred_at=payload.OccurredAt,
                    details={"SupersededByRunID": run_id},
                )
        updated["SupersedesRunID"] = next(
            (
                other_id
                for other_id, other in planning_runs.items()
                if other_id != run_id
                and other.get("ProblemID") == planning_run.get("ProblemID")
                and other.get("SupersededByRunID") == run_id
            ),
            None,
        )
    planning_runs[run_id] = updated
    _append_planning_run_audit_event(
        audit_events=audit_events,
        run_id=run_id,
        action=f"PlanPublication{action}",
        actor_id=_effective_actor_id(request, payload.ActorID),
        occurred_at=payload.OccurredAt,
        details={
            "PublicationStatus": updated.get("PublicationStatus"),
            "Comment": payload.Comment,
            "PackageID": (
                updated.get("PublicationPackage", {}).get("PackageID")
                if isinstance(updated.get("PublicationPackage"), dict)
                else None
            ),
        },
    )
    return {
        "Endpoint": endpoint,
        "StatusCode": 200,
        "Data": build_plan_publication_view(planning_run=updated),
    }


def _planning_run_transition_conflict(
    *,
    endpoint: str,
    planning_run: dict[str, object],
    message: str,
) -> JSONResponse:
    return JSONResponse(
        status_code=409,
        content={
            "Endpoint": endpoint,
            "StatusCode": 409,
            "Data": {
                "RunID": planning_run["RunID"],
                "Status": "PlanningRunNotPending",
                "CurrentStatus": planning_run["Status"],
                "Message": message,
            },
        },
    )


def _planning_run_lease_expired(
    planning_run: dict[str, object],
    observed_at: datetime,
) -> bool:
    if planning_run["Status"] != "Running":
        return False
    normalized_observed_at = _aware_planning_run_datetime(observed_at)
    if normalized_observed_at is None:
        return False
    has_worker_lease = any(
        planning_run.get(field)
        for field in ("WorkerID", "LeaseTokenHash", "LeaseExpiresAt")
    )
    if has_worker_lease:
        lease_expires_at = _aware_planning_run_datetime(
            planning_run.get("LeaseExpiresAt")
        )
        return (
            lease_expires_at is None
            or lease_expires_at <= normalized_observed_at
        )
    if planning_run.get("ExecutionTokenHash"):
        execution_expires_at = _aware_planning_run_datetime(
            planning_run.get("ExecutionClaimExpiresAt")
        )
        return (
            execution_expires_at is None
            or execution_expires_at <= normalized_observed_at
        )
    return False


def _planning_run_ready_for_claim(
    planning_run: dict[str, object],
    observed_at: datetime,
) -> bool:
    next_attempt_at = planning_run.get("NextAttemptAt")
    if not isinstance(next_attempt_at, str):
        return True
    normalized_next_attempt_at = _aware_planning_run_datetime(next_attempt_at)
    normalized_observed_at = _aware_planning_run_datetime(observed_at)
    return (
        normalized_next_attempt_at is None
        or normalized_observed_at is not None
        and normalized_next_attempt_at <= normalized_observed_at
    )


def _aware_planning_run_datetime(value: object) -> datetime | None:
    try:
        parsed = (
            value
            if isinstance(value, datetime)
            else datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        )
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return None
    return parsed


def _apply_planning_run_failure_policy(
    *,
    planning_run: dict[str, object],
    failed_at: datetime,
) -> dict[str, object]:
    updated_run = dict(planning_run)
    solver_status = str(planning_run.get("SolverStatus", "Error"))
    attempt_count = int(planning_run.get("AttemptCount", 1))
    max_attempts = int(planning_run.get("MaxAttempts", 1))
    retry_delay_seconds = int(planning_run.get("RetryDelaySeconds", 0))
    updated_run["LastFailure"] = {
        "FailedAt": failed_at.isoformat(),
        "AttemptNumber": attempt_count,
        "SolverStatus": solver_status,
        "SolverMessage": planning_run.get("SolverMessage"),
    }
    retryable = solver_status in {"Error", "Unavailable", "TimeLimit"}
    if retryable and attempt_count < max_attempts:
        updated_run.update(
            {
                "Status": "Queued",
                "NextAttemptAt": (
                    failed_at + timedelta(seconds=retry_delay_seconds)
                ).isoformat(),
                "LeaseTokenHash": None,
                "LeaseClaimedAt": None,
                "LeaseExpiresAt": None,
                "ExecutionClaimExpiresAt": None,
            }
        )
        return updated_run
    updated_run.update(
        {
            "Status": "DeadLetter",
            "DeadLetterAt": failed_at.isoformat(),
            "DeadLetterReason": (
                "MaxAttemptsExceeded"
                if retryable
                else "NonRetryableSolverStatus"
            ),
            "LeaseTokenHash": None,
            "LeaseExpiresAt": None,
            "ExecutionClaimExpiresAt": None,
        }
    )
    return updated_run


def _planning_run_execution_lease_error(
    *,
    planning_run: dict[str, object],
    executed_by: str,
    lease_token: str | None,
    observed_at: datetime,
) -> dict[str, object] | None:
    stored_hash = planning_run.get("LeaseTokenHash")
    if stored_hash is None and isinstance(planning_run.get("LeaseToken"), str):
        stored_hash = _lease_token_hash(str(planning_run["LeaseToken"]))
    supplied_hash = _lease_token_hash(lease_token) if lease_token else ""
    if planning_run.get("WorkerID") != executed_by or not (
        isinstance(stored_hash, str) and compare_digest(stored_hash, supplied_hash)
    ):
        return {
            "Status": "PlanningRunLeaseMismatch",
            "CurrentStatus": planning_run["Status"],
            "Message": "Worker identity or lease token does not own this planning run.",
        }
    lease_expires_at = _aware_planning_run_datetime(
        planning_run.get("LeaseExpiresAt")
    )
    if lease_expires_at is None or lease_expires_at <= observed_at:
        return {
            "Status": "PlanningRunLeaseExpired",
            "CurrentStatus": planning_run["Status"],
            "LeaseExpiresAt": planning_run.get("LeaseExpiresAt"),
            "Message": "Planning run lease expired before execution started.",
        }
    return None


def _planning_run_execution_claim_expiry_error(
    *,
    planning_run: Mapping[str, object],
    observed_at: datetime,
    worker_execution: bool,
) -> dict[str, object] | None:
    execution_expires_at = _aware_planning_run_datetime(
        planning_run.get("ExecutionClaimExpiresAt")
    )
    if worker_execution:
        lease_expires_at = _aware_planning_run_datetime(
            planning_run.get("LeaseExpiresAt")
        )
        if (
            lease_expires_at is None
            or execution_expires_at is None
            or lease_expires_at <= observed_at
            or execution_expires_at <= observed_at
        ):
            return {
                "Status": "PlanningRunLeaseExpired",
                "CurrentStatus": planning_run["Status"],
                "LeaseExpiresAt": planning_run.get("LeaseExpiresAt"),
                "ExecutionClaimExpiresAt": planning_run.get(
                    "ExecutionClaimExpiresAt"
                ),
                "Message": (
                    "Planning run lease expired before execution finalization."
                ),
            }
        return None
    if execution_expires_at is None or execution_expires_at <= observed_at:
        return {
            "Status": "PlanningRunExecutionClaimExpired",
            "CurrentStatus": planning_run["Status"],
            "ExecutionClaimExpiresAt": planning_run.get(
                "ExecutionClaimExpiresAt"
            ),
            "Message": (
                "Direct execution claim expired before execution finalization."
            ),
        }
    return None


def _pending_planning_run(
    *,
    payload: PlanningRunPayload,
    master_data_version: dict[str, object],
    operational_snapshot: OperationalStateSnapshot,
    release_policy: dict[str, object] | None = None,
    scheduling_strategy: dict[str, object] | None = None,
    operating_model_configuration: dict[str, object] | None = None,
    frozen_base_calendars: list[dict[str, object]] | None = None,
    frozen_resource_calendar_assignments: list[dict[str, object]] | None = None,
    frozen_calendar_overrides: list[dict[str, object]] | None = None,
    frozen_planning_reservations: dict[str, object] | None = None,
) -> dict[str, object]:
    return {
        "RunID": payload.RunID,
        "ProblemID": payload.ProblemID,
        "Status": "Pending",
        "MasterDataVersionID": payload.MasterDataVersionID,
        "MasterDataCapturedAt": master_data_version["CapturedAt"],
        "OperationalStateSnapshotID": payload.OperationalStateSnapshotID,
        "OperationalStateCapturedAt": operational_snapshot.captured_at.isoformat(),
        "ContractPath": (
            "DDSOP-CONFIG-INBOUND-V1"
            if operating_model_configuration
            else "LegacyNonDdsopConfigInboundV1"
        ),
        "LegacyPlanningRunPath": operating_model_configuration is None,
        "OperatingModelConfigurationID": (
            operating_model_configuration.get("OperatingModelConfigurationID")
            if operating_model_configuration
            else payload.OperatingModelConfigurationID
        ),
        "OperatingModelFingerprint": (
            operating_model_configuration.get("Fingerprint")
            if operating_model_configuration
            else None
        ),
        "SchedulingConfigurationID": (
            operating_model_configuration.get("SchedulingConfigurationID")
            if operating_model_configuration
            else None
        ),
        "DDMRPConfigurationID": (
            operating_model_configuration.get("DDMRPConfigurationID")
            if operating_model_configuration
            else None
        ),
        "FrozenOperatingModelConfiguration": (
            dict(operating_model_configuration.get("Payload", {}))
            if operating_model_configuration
            else None
        ),
        "OperatingModelConfigurationVersion": (
            operating_model_configuration.get("ConfigurationVersion")
            if operating_model_configuration
            else None
        ),
        "SourceRunID": payload.SourceRunID,
        "ReleasePolicyVersionID": payload.ReleasePolicyVersionID,
        "FrozenReleasePolicy": dict(release_policy) if release_policy else None,
        "PlanningReservationBatchIDs": list(payload.PlanningReservationBatchIDs),
        "FrozenPlanningReservations": deepcopy(
            frozen_planning_reservations
            if frozen_planning_reservations is not None
            else freeze_planning_reservations(
                batch_ids=[],
                demand_commitments={},
                batches={},
                capacity_reservations={},
                material_allocations={},
            )
        ),
        "FrozenBaseCalendars": [
            dict(item) for item in (frozen_base_calendars or [])
        ],
        "FrozenResourceCalendarAssignments": [
            dict(item) for item in (frozen_resource_calendar_assignments or [])
        ],
        "FrozenCalendarOverrides": [
            dict(item) for item in (frozen_calendar_overrides or [])
        ],
        "ScheduleStartAt": payload.ScheduleStartAt.isoformat(),
        "TimeBufferMinutes": payload.TimeBufferMinutes,
        "FreezeWindowMinutes": payload.FreezeWindowMinutes,
        "ObjectiveStrategyID": payload.ObjectiveStrategyID,
        "FrozenSchedulingStrategy": (
            dict(scheduling_strategy) if scheduling_strategy else None
        ),
        "SetupTransitions": _setup_transitions_to_payload_dict(
            _setup_transitions_from_payload(payload.SetupTransitions)
        ),
        "SolverBackendID": payload.SolverBackendID,
        "TimeLimitSeconds": payload.TimeLimitSeconds,
        "MaxAttempts": payload.MaxAttempts,
        "RetryDelaySeconds": payload.RetryDelaySeconds,
        "SolverStatus": "Pending",
        "SolverMessage": "Planning run is awaiting execution.",
        "RequestedBy": payload.RequestedBy,
        "RequestedAt": payload.RequestedAt.isoformat(),
        "StartedAt": None,
        "CompletedAt": None,
        "ExecutedBy": None,
        "Schedule": None,
        "StatusHistory": [
            {
                "Status": "Pending",
                "ChangedAt": payload.RequestedAt.isoformat(),
                "ChangedBy": payload.RequestedBy,
            }
        ],
    }


def _planning_run_payload_from_record(
    planning_run: dict[str, object],
) -> PlanningRunPayload:
    return PlanningRunPayload(
        RunID=planning_run["RunID"],
        ProblemID=planning_run["ProblemID"],
        MasterDataVersionID=planning_run["MasterDataVersionID"],
        OperationalStateSnapshotID=planning_run["OperationalStateSnapshotID"],
        OperatingModelConfigurationID=planning_run.get(
            "OperatingModelConfigurationID"
        ),
        SourceRunID=planning_run.get("SourceRunID"),
        ReleasePolicyVersionID=planning_run.get("ReleasePolicyVersionID"),
        ScheduleStartAt=planning_run["ScheduleStartAt"],
        TimeBufferMinutes=planning_run["TimeBufferMinutes"],
        FreezeWindowMinutes=planning_run.get("FreezeWindowMinutes", 0),
        ObjectiveStrategyID=planning_run.get(
            "ObjectiveStrategyID", "v1_delivery_flow_bottleneck"
        ),
        SetupTransitions=[
            SetupTransitionPayload(**item)
            for item in planning_run.get("SetupTransitions", [])
        ],
        SolverBackendID=planning_run["SolverBackendID"],
        TimeLimitSeconds=planning_run.get("TimeLimitSeconds", 300),
        MaxAttempts=planning_run.get("MaxAttempts", 3),
        RetryDelaySeconds=planning_run.get("RetryDelaySeconds", 60),
        PlanningReservationBatchIDs=planning_run.get(
            "PlanningReservationBatchIDs", []
        ),
        RequestedBy=planning_run["RequestedBy"],
        RequestedAt=planning_run["RequestedAt"],
    )


def _execute_planning_run(
    *,
    payload: PlanningRunPayload,
    master_data_version: dict[str, object],
    operational_snapshot: OperationalStateSnapshot,
    solver_time_limit_seconds: float | None = None,
    scheduling_strategy_versions: dict[str, dict[str, object]] | None = None,
    frozen_scheduling_strategy: object | None = None,
    frozen_base_calendars: list[dict[str, object]] | None = None,
    frozen_resource_calendar_assignments: list[dict[str, object]] | None = None,
    frozen_calendar_overrides: list[dict[str, object]] | None = None,
    release_policy: dict[str, object] | None = None,
) -> dict[str, object]:
    objective = _objective_for_strategy_id(
        strategy_id=payload.ObjectiveStrategyID,
        scheduling_strategy_versions=scheduling_strategy_versions or {},
        frozen_scheduling_strategy=(
            frozen_scheduling_strategy
            if isinstance(frozen_scheduling_strategy, dict)
            else None
        ),
    )
    if objective is None:
        raise ValueError(
            f"Scheduling objective strategy {payload.ObjectiveStrategyID} was not found."
        )
    resources = _resources_from_payload(
        [ResourcePayload(**item) for item in master_data_version["Resources"]]
    )
    base_calendar_application = apply_base_calendar_assignments(
        resources=resources,
        calendars=frozen_base_calendars or [],
        assignments=frozen_resource_calendar_assignments or [],
    )
    resources = base_calendar_application.resources
    calendar_application = apply_calendar_overrides(
        resources=resources,
        overrides=frozen_calendar_overrides or [],
    )
    resources = calendar_application.resources
    routings = _routings_from_payload(
        [RoutingPayload(**item) for item in master_data_version["Routings"]]
    )
    orders = _orders_from_payload(
        [OrderPayload(**item) for item in master_data_version["Orders"]]
    )
    master_inventory_buffers = _inventory_buffers_from_payload(
        [
            InventoryBufferPayload(**item)
            for item in master_data_version["InventoryBuffers"]
        ]
    )
    material_requirements = [
        MaterialRequirement(
            order_id=str(item["OrderID"]),
            item_id=str(item["ItemID"]),
            location_id=str(item["LocationID"]),
            required_qty=float(item["RequiredQty"]),
        )
        for item in master_data_version["MaterialRequirements"]
    ]
    validation = validate_master_data(
        resources=resources,
        routings=routings,
        orders=orders,
        inventory_buffers=master_inventory_buffers,
        material_requirements=material_requirements,
        calendar_timezone=master_data_version["CalendarTimezone"],
    )
    schedule = _calculate_workbench_data_from_entities(
        problem_id=payload.ProblemID,
        schedule_start_at=payload.ScheduleStartAt,
        resources=resources,
        routings=routings,
        orders=orders,
        inventory_buffers=operational_snapshot.inventory_buffers,
        validation=validation,
        time_buffer_minutes=payload.TimeBufferMinutes,
        calendar_timezone=master_data_version["CalendarTimezone"],
        solver_backend_id=payload.SolverBackendID,
        generated_at=payload.RequestedAt,
        solver_time_limit_seconds=solver_time_limit_seconds,
        setup_transitions=_setup_transitions_from_payload(payload.SetupTransitions),
        objective=objective,
        align_release_to_schedule=True,
        release_policy=release_policy,
    )
    schedule.setdefault("SolverDiagnostics", []).extend(
        _solver_diagnostics_to_payload_dict(
            [
                *base_calendar_application.diagnostics,
                *calendar_application.diagnostics,
            ]
        )
    )
    schedule["BaseCalendarSummary"] = {
        "FrozenCalendarCount": len(frozen_base_calendars or []),
        "FrozenAssignmentCount": len(frozen_resource_calendar_assignments or []),
        "AppliedAssignmentCount": len(
            base_calendar_application.applied_assignments
        ),
        "AppliedAssignments": base_calendar_application.applied_assignments,
    }
    schedule["CalendarOverrideSummary"] = {
        "FrozenOverrideCount": len(frozen_calendar_overrides or []),
        "AppliedOverrideCount": len(calendar_application.applied_overrides),
        "AppliedOverrides": calendar_application.applied_overrides,
    }
    schedule["CalendarSummary"] = {
        **schedule["BaseCalendarSummary"],
        **schedule["CalendarOverrideSummary"],
    }
    schedule["ProblemID"] = payload.ProblemID
    solver_status = str(schedule["SolverStatus"])
    return {
        "RunID": payload.RunID,
        "ProblemID": payload.ProblemID,
        "Status": (
            "Completed"
            if solver_status in {"Optimal", "Feasible"}
            else "Failed"
        ),
        "MasterDataVersionID": payload.MasterDataVersionID,
        "MasterDataCapturedAt": master_data_version["CapturedAt"],
        "OperationalStateSnapshotID": payload.OperationalStateSnapshotID,
        "OperationalStateCapturedAt": operational_snapshot.captured_at.isoformat(),
        "SourceRunID": payload.SourceRunID,
        "ReleasePolicyVersionID": payload.ReleasePolicyVersionID,
        "FrozenBaseCalendars": [
            dict(item) for item in (frozen_base_calendars or [])
        ],
        "FrozenResourceCalendarAssignments": [
            dict(item) for item in (frozen_resource_calendar_assignments or [])
        ],
        "BaseCalendarSummary": schedule["BaseCalendarSummary"],
        "FrozenCalendarOverrides": [
            dict(item) for item in (frozen_calendar_overrides or [])
        ],
        "CalendarOverrideSummary": schedule["CalendarOverrideSummary"],
        "ScheduleStartAt": payload.ScheduleStartAt.isoformat(),
        "TimeBufferMinutes": payload.TimeBufferMinutes,
        "FreezeWindowMinutes": payload.FreezeWindowMinutes,
        "ObjectiveStrategyID": payload.ObjectiveStrategyID,
        "SetupTransitions": _setup_transitions_to_payload_dict(
            _setup_transitions_from_payload(payload.SetupTransitions)
        ),
        "SolverBackendID": payload.SolverBackendID,
        "SolverStatus": solver_status,
        "SolverMessage": schedule["SolverMessage"],
        "RequestedBy": payload.RequestedBy,
        "RequestedAt": payload.RequestedAt.isoformat(),
        "Schedule": schedule,
    }


def _validate_master_data_payload(
    payload: PlannerWorkbenchCalculatePayload,
) -> MasterDataValidationResult:
    return validate_master_data(
        resources=_resources_from_payload(payload.Resources),
        routings=_routings_from_payload(payload.Routings),
        orders=_orders_from_payload(payload.Orders),
        inventory_buffers=_inventory_buffers_from_payload(payload.InventoryBuffers),
        material_requirements=_material_requirements_from_payload(payload.MaterialRequirements),
        calendar_timezone=payload.CalendarTimezone,
    )


def _calculate_workbench_data(
    payload: PlannerWorkbenchCalculatePayload,
    validation: MasterDataValidationResult,
    fixed_assignments: list[FixedOperationAssignment] | None = None,
    objective: SchedulingObjective | None = None,
) -> dict[str, object]:
    data = _calculate_workbench_data_from_entities(
        problem_id=payload.ProblemID,
        schedule_start_at=payload.ScheduleStartAt,
        resources=_resources_from_payload(payload.Resources),
        routings=_routings_from_payload(payload.Routings),
        orders=_orders_from_payload(payload.Orders),
        inventory_buffers=_inventory_buffers_from_payload(payload.InventoryBuffers),
        validation=validation,
        time_buffer_minutes=payload.TimeBufferMinutes,
        calendar_timezone=payload.CalendarTimezone,
        solver_backend_id=payload.SolverBackendID,
        generated_at=payload.GeneratedAt,
        fixed_assignments=fixed_assignments,
        setup_transitions=_setup_transitions_from_payload(payload.SetupTransitions),
        objective=objective or SchedulingObjective(strategy_id=payload.ObjectiveStrategyID),
    )
    data["ObjectiveStrategyID"] = payload.ObjectiveStrategyID
    data["ObjectiveWeights"] = _objective_to_payload_dict(
        objective or SchedulingObjective(strategy_id=payload.ObjectiveStrategyID)
    )
    if payload.SetupTransitions:
        data["SetupTransitions"] = _setup_transitions_to_payload_dict(
            _setup_transitions_from_payload(payload.SetupTransitions)
        )
    if fixed_assignments:
        data["FixedAssignments"] = [
            _fixed_assignment_to_dict(assignment)
            for assignment in fixed_assignments
        ]
    return data


def _fixed_assignments_for_replan(
    *,
    problem_id: str,
    source_run_id: str | None = None,
    schedule_start_at: datetime,
    freeze_window_minutes: int,
    planning_runs: dict[str, dict[str, object]],
    audit_events: list[dict[str, object]],
) -> list[FixedOperationAssignment]:
    source_run = _source_run_for_replan(
        problem_id=problem_id,
        source_run_id=source_run_id,
        planning_runs=planning_runs,
    )
    if source_run is None:
        return []
    locked_order_ids = _locked_order_ids_for_run(
        run_id=str(source_run["RunID"]),
        audit_events=audit_events,
    )
    freeze_until = schedule_start_at + timedelta(minutes=freeze_window_minutes)
    if not locked_order_ids and freeze_window_minutes <= 0:
        return []

    assignments = []
    for row in scheduled_work_order_rows_from_schedule(_dict_schedule(source_run)):
        start_at = _parse_iso_datetime(row.get("Start"))
        locked = str(row.get("OrderID")) in locked_order_ids
        frozen = (
            freeze_window_minutes > 0
            and start_at is not None
            and start_at <= freeze_until
        )
        if not locked and not frozen:
            continue
        operation_id = row.get("OperationID")
        resource_id = row.get("ResourceID")
        if operation_id is None or resource_id is None or start_at is None:
            continue
        assignments.append(
            FixedOperationAssignment(
                operation_id=str(operation_id),
                resource_id=str(resource_id),
                start_at=start_at,
            )
        )
    return assignments


def _source_run_for_replan(
    *,
    problem_id: str,
    source_run_id: str | None,
    planning_runs: dict[str, dict[str, object]],
) -> dict[str, object] | None:
    if source_run_id is not None:
        source_run = planning_runs.get(source_run_id)
        if (
            source_run is not None
            and source_run.get("ProblemID") == problem_id
            and source_run.get("Status") == "Completed"
            and _dict_schedule(source_run)
        ):
            return source_run
        return None
    return _latest_completed_planning_run_for_problem(
        problem_id=problem_id,
        planning_runs=planning_runs,
    )


def _latest_completed_planning_run_for_problem(
    *,
    problem_id: str,
    planning_runs: dict[str, dict[str, object]],
) -> dict[str, object] | None:
    completed = [
        planning_run
        for planning_run in planning_runs.values()
        if planning_run.get("ProblemID") == problem_id
        and planning_run.get("Status") == "Completed"
        and _dict_schedule(planning_run)
    ]
    if not completed:
        return None
    return max(completed, key=_planning_run_schedule_timestamp)


def _planning_run_schedule_timestamp(planning_run: dict[str, object]) -> str:
    schedule = _dict_schedule(planning_run)
    return str(
        schedule.get("GeneratedAt")
        or planning_run.get("CompletedAt")
        or planning_run.get("RequestedAt")
        or ""
    )


def _locked_order_ids_for_run(
    *, run_id: str, audit_events: list[dict[str, object]]
) -> set[str]:
    locked: set[str] = set()
    for event in sorted(audit_events, key=lambda item: str(item.get("OccurredAt", ""))):
        if event.get("RunID") != run_id:
            continue
        details = event.get("Details")
        if not isinstance(details, dict):
            continue
        order_ids = {str(order_id) for order_id in details.get("OrderIDs", [])}
        if event.get("Action") == "ScheduledWorkOrdersLocked":
            locked.update(order_ids)
        elif event.get("Action") == "ScheduledWorkOrdersUnlocked":
            locked.difference_update(order_ids)
    return locked


def _fixed_assignment_to_dict(
    assignment: FixedOperationAssignment,
) -> dict[str, object]:
    return {
        "OperationID": assignment.operation_id,
        "ResourceID": assignment.resource_id,
        "StartAt": assignment.start_at.isoformat(),
    }


def _schedule_operation_diff(
    *,
    source_schedule: dict[str, object],
    candidate_schedule: dict[str, object],
    fixed_assignments: list[FixedOperationAssignment],
) -> dict[str, object]:
    source = _scheduled_operations_by_key(source_schedule)
    candidate = _scheduled_operations_by_key(candidate_schedule)
    fixed_keys = {assignment.operation_id for assignment in fixed_assignments}
    rows = []
    for key in sorted(set(source) | set(candidate)):
        before = source.get(key)
        after = candidate.get(key)
        if before is None:
            change_type = "Added"
        elif after is None:
            change_type = "Removed"
        else:
            start_delta = _minutes_between(before.get("Start"), after.get("Start"))
            end_delta = _minutes_between(before.get("End"), after.get("End"))
            resource_changed = before.get("ResourceID") != after.get("ResourceID")
            if start_delta == 0 and end_delta == 0 and not resource_changed:
                change_type = "Unchanged"
            elif resource_changed:
                change_type = "ResourceChanged"
            elif start_delta is not None and start_delta < 0:
                change_type = "Advanced"
            elif start_delta is not None and start_delta > 0:
                change_type = "Delayed"
            else:
                change_type = "Changed"
        rows.append(
            {
                "OperationID": key,
                "OrderID": (after or before or {}).get("OrderID"),
                "ChangeType": change_type,
                "Before": before,
                "After": after,
                "StartDeltaMinutes": (
                    _minutes_between(before.get("Start"), after.get("Start"))
                    if before and after
                    else None
                ),
                "EndDeltaMinutes": (
                    _minutes_between(before.get("End"), after.get("End"))
                    if before and after
                    else None
                ),
                "ResourceChanged": (
                    before.get("ResourceID") != after.get("ResourceID")
                    if before and after
                    else False
                ),
                "FixedByLockOrFreeze": key in fixed_keys,
            }
        )
    return {
        "Summary": {
            "AddedCount": sum(1 for row in rows if row["ChangeType"] == "Added"),
            "RemovedCount": sum(1 for row in rows if row["ChangeType"] == "Removed"),
            "AdvancedCount": sum(1 for row in rows if row["ChangeType"] == "Advanced"),
            "DelayedCount": sum(1 for row in rows if row["ChangeType"] == "Delayed"),
            "ResourceChangedCount": sum(
                1 for row in rows if row["ResourceChanged"] is True
            ),
            "FixedByLockOrFreezeCount": sum(
                1 for row in rows if row["FixedByLockOrFreeze"] is True
            ),
        },
        "Operations": rows,
    }


def _scheduled_operations_by_key(
    schedule: dict[str, object],
) -> dict[str, dict[str, object]]:
    result = {}
    for row in scheduled_work_order_rows_from_schedule(schedule):
        key = str(row.get("OperationID"))
        result[key] = {
            "OrderID": row.get("OrderID"),
            "OperationID": row.get("OperationID"),
            "ResourceID": row.get("ResourceID"),
            "Start": row.get("Start"),
            "End": row.get("End"),
            "DurationMinutes": row.get("DurationMinutes"),
        }
    return result


def _minutes_between(before: object, after: object) -> int | None:
    before_dt = _parse_iso_datetime(before)
    after_dt = _parse_iso_datetime(after)
    if before_dt is None or after_dt is None:
        return None
    return int((after_dt - before_dt).total_seconds() / 60)


def _release_policy_for_evaluation(
    *,
    planning_run: dict[str, object],
    requested_policy_id: str | None,
    dbr_release_policies: dict[str, dict[str, object]],
) -> dict[str, object] | None:
    if requested_policy_id is not None:
        return dbr_release_policies.get(requested_policy_id)
    frozen = planning_run.get("FrozenReleasePolicy")
    if isinstance(frozen, dict):
        return frozen
    version_id = planning_run.get("ReleasePolicyVersionID")
    if isinstance(version_id, str):
        return dbr_release_policies.get(version_id)
    return None


def _operational_state_snapshot_for_release_evaluation(
    *,
    planning_run: dict[str, object],
    operational_state_snapshots: dict[str, OperationalStateSnapshot],
    evaluated_at: datetime,
    use_latest_operational_state: bool,
    requested_snapshot_id: str | None,
) -> OperationalStateSnapshot | None:
    if requested_snapshot_id is not None:
        return operational_state_snapshots.get(requested_snapshot_id)
    if use_latest_operational_state:
        eligible_snapshots = [
            snapshot
            for snapshot in operational_state_snapshots.values()
            if snapshot.captured_at <= evaluated_at
        ]
        if eligible_snapshots:
            return max(
                eligible_snapshots,
                key=lambda snapshot: snapshot.captured_at,
            )
    return operational_state_snapshots.get(
        str(planning_run.get("OperationalStateSnapshotID"))
    )


def _next_mock_operational_snapshot_id(
    *,
    operational_state_snapshots: dict[str, OperationalStateSnapshot],
    evaluated_at: datetime,
) -> str:
    stem = (
        "TST-OPS-LATEST-REEVALUATION-"
        f"{evaluated_at.strftime('%Y%m%d%H%M%S')}"
    )
    if stem not in operational_state_snapshots:
        return stem
    index = 2
    while f"{stem}-{index}" in operational_state_snapshots:
        index += 1
    return f"{stem}-{index}"


def _dbr_release_policy_from_payload(
    payload: DbrReleasePolicyPayload,
) -> dict[str, object]:
    return {
        "VersionID": payload.VersionID,
        "CreatedAt": payload.CreatedAt.isoformat(),
        "CreatedBy": payload.CreatedBy,
        "ScopeID": payload.ScopeID,
        "RopeBufferMinutes": payload.RopeBufferMinutes,
        "TimeBufferRatios": {
            "Green": payload.GreenZoneRatio,
            "Yellow": payload.YellowZoneRatio,
            "Red": payload.RedZoneRatio,
        },
        "MaxWipCount": payload.MaxWipCount,
        "MaterialLookaheadMinutes": (
            payload.MaterialCheckWindowMinutes
            if payload.MaterialCheckWindowMinutes is not None
            else payload.MaterialLookaheadMinutes
        ),
        "MaterialCheckWindowMinutes": (
            payload.MaterialCheckWindowMinutes
            if payload.MaterialCheckWindowMinutes is not None
            else payload.MaterialLookaheadMinutes
        ),
        "StabilityPolicy": {
            "ToleranceMinutes": payload.StabilityToleranceMinutes,
            "ReplanThresholdMinutes": payload.StabilityReplanThresholdMinutes,
            "ConsecutiveBlockedThreshold": payload.ConsecutiveBlockedThreshold,
            "ReplanCooldownMinutes": payload.ReplanCooldownMinutes,
        },
        "Status": payload.Status,
    }


def _retire_other_active_policies(
    *,
    dbr_release_policies: dict[str, dict[str, object]],
    active_version_id: str,
) -> None:
    for version_id, policy in dbr_release_policies.items():
        if version_id != active_version_id and policy.get("Status") == "Active":
            policy["Status"] = "Retired"
            policy["RetiredByPolicyVersionID"] = active_version_id


def _active_calendar_overrides(
    overrides: object,
) -> list[dict[str, object]]:
    return [
        dict(item)
        for item in overrides
        if isinstance(item, dict) and item.get("Status") == "Active"
    ]


def _active_base_calendars(
    calendars: object,
) -> list[dict[str, object]]:
    return [
        dict(item)
        for item in calendars
        if isinstance(item, dict) and item.get("Status") == "Active"
    ]


def _active_resource_calendar_assignments(
    assignments: object,
) -> list[dict[str, object]]:
    return [
        dict(item)
        for item in assignments
        if isinstance(item, dict) and item.get("Status") == "Active"
    ]


def _base_calendars_with_driver_status(
    *,
    calendars: object,
    assignments: object,
    planning_runs: object,
) -> list[dict[str, object]]:
    applied_calendar_ids = _applied_base_calendar_ids(planning_runs)
    assignment_list = [item for item in assignments if isinstance(item, dict)]
    enriched: list[dict[str, object]] = []
    for calendar in calendars:
        if not isinstance(calendar, dict):
            continue
        item = dict(calendar)
        item["SolverDriverStatus"] = base_calendar_driver_status(
            calendar=item,
            assignments=assignment_list,
            applied_calendar_ids=applied_calendar_ids,
        )
        enriched.append(item)
    return enriched


def _resource_calendar_assignments_with_driver_status(
    *,
    assignments: object,
    calendars: object,
    master_data_versions: object,
    planning_runs: object,
) -> list[dict[str, object]]:
    resources = _latest_master_data_resources(master_data_versions)
    calendar_list = [item for item in calendars if isinstance(item, dict)]
    applied_assignment_ids = _applied_resource_calendar_assignment_ids(planning_runs)
    enriched: list[dict[str, object]] = []
    for assignment in assignments:
        if not isinstance(assignment, dict):
            continue
        item = dict(assignment)
        item["SolverDriverStatus"] = resource_calendar_assignment_driver_status(
            assignment=item,
            resources=resources,
            calendars=calendar_list,
            applied_assignment_ids=applied_assignment_ids,
        )
        enriched.append(item)
    return enriched


def _calendar_overrides_with_driver_status(
    *,
    overrides: object,
    master_data_versions: object,
    planning_runs: object,
) -> list[dict[str, object]]:
    resources = _latest_master_data_resources(master_data_versions)
    applied_ids = _applied_calendar_override_ids(planning_runs)
    enriched: list[dict[str, object]] = []
    for override in overrides:
        if not isinstance(override, dict):
            continue
        item = dict(override)
        item["SolverDriverStatus"] = calendar_override_driver_status(
            override=item,
            resources=resources,
            applied_override_ids=applied_ids,
        )
        enriched.append(item)
    return enriched


def _applied_base_calendar_ids(planning_runs: object) -> set[str]:
    result: set[str] = set()
    for run in planning_runs:
        if not isinstance(run, dict):
            continue
        summary = run.get("BaseCalendarSummary")
        if not isinstance(summary, dict):
            schedule = run.get("Schedule")
            summary = schedule.get("BaseCalendarSummary") if isinstance(schedule, dict) else None
        if not isinstance(summary, dict):
            continue
        for item in summary.get("AppliedAssignments", []):
            if isinstance(item, dict) and item.get("CalendarID") is not None:
                result.add(str(item["CalendarID"]))
    return result


def _applied_resource_calendar_assignment_ids(planning_runs: object) -> set[str]:
    result: set[str] = set()
    for run in planning_runs:
        if not isinstance(run, dict):
            continue
        summary = run.get("BaseCalendarSummary")
        if not isinstance(summary, dict):
            schedule = run.get("Schedule")
            summary = schedule.get("BaseCalendarSummary") if isinstance(schedule, dict) else None
        if not isinstance(summary, dict):
            continue
        for item in summary.get("AppliedAssignments", []):
            if isinstance(item, dict) and item.get("AssignmentID") is not None:
                result.add(str(item["AssignmentID"]))
    return result


def _latest_master_data_resources(master_data_versions: object) -> list[Resource]:
    versions = [
        version
        for version in master_data_versions
        if isinstance(version, dict) and isinstance(version.get("Resources"), list)
    ]
    if not versions:
        return []
    latest = max(versions, key=lambda item: str(item.get("CapturedAt", "")))
    try:
        return _resources_from_payload(
            [
                ResourcePayload(**item)
                for item in latest.get("Resources", [])
                if isinstance(item, dict)
            ]
        )
    except Exception:
        return []


def _latest_ddmrp_master_data_version(
    master_data_versions: dict[str, dict[str, object]],
) -> dict[str, object] | None:
    versions = [
        version
        for version in master_data_versions.values()
        if isinstance(version, dict)
        and (
            isinstance(version.get("DdmrpDecouplingPoints"), list)
            or isinstance(version.get("InventoryBuffers"), list)
        )
    ]
    if not versions:
        return None
    return max(versions, key=lambda item: str(item.get("CapturedAt", "")))


def _calendar_preview_master_data_version(
    *,
    master_data_versions: dict[str, dict[str, object]],
    version_id: str | None,
) -> dict[str, object] | None:
    if version_id is not None:
        version = master_data_versions.get(version_id)
        return version if isinstance(version, dict) else None
    versions = [
        version
        for version in master_data_versions.values()
        if isinstance(version, dict) and isinstance(version.get("Resources"), list)
    ]
    if not versions:
        return None
    return max(versions, key=lambda item: str(item.get("CapturedAt", "")))


def _applied_calendar_override_ids(planning_runs: object) -> set[str]:
    result: set[str] = set()
    for run in planning_runs:
        if not isinstance(run, dict):
            continue
        summary = run.get("CalendarOverrideSummary")
        if not isinstance(summary, dict):
            schedule = run.get("Schedule")
            summary = schedule.get("CalendarOverrideSummary") if isinstance(schedule, dict) else None
        if not isinstance(summary, dict):
            continue
        for item in summary.get("AppliedOverrides", []):
            if isinstance(item, dict) and item.get("OverrideID") is not None:
                result.add(str(item["OverrideID"]))
    return result


def _solver_diagnostics_to_payload_dict(
    diagnostics: list[SolverDiagnostic],
) -> list[dict[str, object]]:
    return [
        {
            "Severity": diagnostic.severity,
            "Code": diagnostic.code,
            "Message": diagnostic.message,
            "EntityID": diagnostic.entity_id,
        }
        for diagnostic in diagnostics
    ]


def _base_calendar_from_payload(payload: BaseCalendarPayload) -> dict[str, object]:
    return {
        "CalendarID": payload.CalendarID,
        "DisplayName": payload.DisplayName,
        "WorkingWeekdays": list(payload.WorkingWeekdays),
        "Shifts": [
            {
                "Name": shift.Name,
                "Start": shift.Start.isoformat(),
                "End": shift.End.isoformat(),
            }
            for shift in payload.Shifts
        ],
        "MaintenanceWindows": [
            {
                "Start": window.Start.isoformat(),
                "End": window.End.isoformat(),
            }
            for window in payload.MaintenanceWindows
        ],
        "Holidays": [item.isoformat() for item in payload.Holidays],
        "Timezone": payload.Timezone,
        "CreatedAt": payload.CreatedAt.isoformat(),
        "CreatedBy": payload.CreatedBy,
        "Status": payload.Status,
        "SolverDriverStatus": "NotAssigned",
    }


def _resource_calendar_assignment_from_payload(
    payload: ResourceCalendarAssignmentPayload,
) -> dict[str, object]:
    return {
        "AssignmentID": payload.AssignmentID,
        "ResourceID": payload.ResourceID,
        "CalendarID": payload.CalendarID,
        "CreatedAt": payload.CreatedAt.isoformat(),
        "CreatedBy": payload.CreatedBy,
        "Status": payload.Status,
        "SolverDriverStatus": "NotApplied",
    }


def _retire_other_active_resource_calendar_assignments(
    *,
    assignments: dict[str, dict[str, object]],
    active_assignment_id: str,
    resource_id: str,
) -> None:
    for assignment_id, assignment in assignments.items():
        if (
            assignment_id != active_assignment_id
            and assignment.get("ResourceID") == resource_id
            and assignment.get("Status") == "Active"
        ):
            assignment["Status"] = "Retired"
            assignment["RetiredByAssignmentID"] = active_assignment_id


def _calendar_override_from_payload(
    payload: CalendarOverridePayload,
) -> dict[str, object]:
    return {
        "OverrideID": payload.OverrideID,
        "CalendarID": payload.CalendarID,
        "ResourceID": payload.ResourceID,
        "OverrideType": payload.OverrideType,
        "EffectiveStartAt": payload.EffectiveStartAt.isoformat(),
        "EffectiveEndAt": payload.EffectiveEndAt.isoformat(),
        "CapacityDeltaMinutes": payload.CapacityDeltaMinutes,
        "ShiftName": payload.ShiftName,
        "Reason": payload.Reason,
        "CreatedAt": payload.CreatedAt.isoformat(),
        "CreatedBy": payload.CreatedBy,
        "Status": payload.Status,
        "SolverDriverStatus": "NotApplied",
    }


def _scheduling_strategy_from_payload(
    payload: SchedulingStrategyPayload,
) -> dict[str, object]:
    return {
        "StrategyID": payload.StrategyID,
        "DisplayName": payload.DisplayName,
        "CreatedAt": payload.CreatedAt.isoformat(),
        "CreatedBy": payload.CreatedBy,
        "Description": payload.Description,
        "ObjectiveWeights": {
            "TardinessWeight": payload.TardinessWeight,
            "MakespanWeight": payload.MakespanWeight,
            "AlternateResourcePenaltyWeight": (
                payload.AlternateResourcePenaltyWeight
            ),
        },
        "Status": payload.Status,
        "SolverDriverStatus": "AppliedWhenSelected",
    }


def _objective_for_strategy_id(
    *,
    strategy_id: str,
    scheduling_strategy_versions: dict[str, dict[str, object]],
    frozen_scheduling_strategy: dict[str, object] | None = None,
) -> SchedulingObjective | None:
    if strategy_id in BUILT_IN_OBJECTIVE_STRATEGY_IDS:
        return SchedulingObjective(strategy_id=strategy_id)
    strategy = (
        frozen_scheduling_strategy
        if frozen_scheduling_strategy is not None
        else scheduling_strategy_versions.get(strategy_id)
    )
    if strategy is None:
        return None
    weights = strategy.get("ObjectiveWeights")
    if not isinstance(weights, dict):
        return None
    return SchedulingObjective(
        strategy_id=strategy_id,
        tardiness_weight=float(weights.get("TardinessWeight", 1.0)),
        makespan_weight=float(weights.get("MakespanWeight", 0.001)),
        alternate_resource_weight=float(
            weights.get("AlternateResourcePenaltyWeight", 0.01)
        ),
    )


def _scheduling_strategy_snapshot_for_id(
    *,
    strategy_id: str,
    scheduling_strategy_versions: dict[str, dict[str, object]],
) -> dict[str, object] | None:
    if strategy_id in BUILT_IN_OBJECTIVE_STRATEGY_IDS:
        return {
            "StrategyID": strategy_id,
            "Source": "BuiltIn",
            "ObjectiveWeights": _objective_to_payload_dict(
                SchedulingObjective(strategy_id=strategy_id)
            ),
            "Status": "Active",
        }
    strategy = scheduling_strategy_versions.get(strategy_id)
    return dict(strategy) if strategy is not None else None


def _objective_to_payload_dict(objective: SchedulingObjective) -> dict[str, object]:
    return {
        "StrategyID": objective.strategy_id,
        "TardinessWeight": objective.tardiness_weight,
        "MakespanWeight": objective.makespan_weight,
        "AlternateResourcePenaltyWeight": objective.alternate_resource_weight,
    }


def _objective_strategy_not_found_response(
    *,
    endpoint: str,
    strategy_id: str,
) -> JSONResponse:
    return JSONResponse(
        status_code=404,
        content={
            "Endpoint": endpoint,
            "StatusCode": 404,
            "Data": {
                "StrategyID": strategy_id,
                "Status": "SchedulingStrategyNotFound",
                "Message": (
                    f"Scheduling strategy {strategy_id} was not found. "
                    "Use a built-in strategy or create it in the strategy catalog."
                ),
            },
        },
    )


def _cp_sat_assumptions_payload(
    *,
    scheduling_strategy_versions: dict[str, dict[str, object]],
    dbr_release_policies: dict[str, dict[str, object]],
) -> dict[str, object]:
    active_strategy = next(
        (
            strategy
            for strategy in scheduling_strategy_versions.values()
            if strategy.get("Status") == "Active"
        ),
        None,
    )
    active_release_policy = next(
        (
            policy
            for policy in dbr_release_policies.values()
            if policy.get("Status") == "Active"
        ),
        None,
    )
    return {
        "SolverBackendID": ACTIVE_SOLVER_BACKEND_ID,
        "PausedSolverBackendIDs": sorted(PAUSED_SOLVER_BACKEND_IDS),
        "ModelingAssumptions": [
            {
                "AssumptionID": "TIME_INTEGER_MINUTES",
                "Description": "Scheduling time is represented as integer minutes.",
                "DescriptionZh": "排程时间按整数分钟表示，不使用秒级或小数分钟。",
                "Status": "Active",
            },
            {
                "AssumptionID": "PARALLEL_RESOURCE_POOL",
                "Description": "CapacityUnits model a homogeneous resource pool.",
                "DescriptionZh": "CapacityUnits 表示同质资源池的并行能力，不追踪池内具体机台。",
                "Status": "Active",
            },
            {
                "AssumptionID": "FINITE_CONSTRAINT_RESOURCES",
                "Description": "Constraint resources are finite; non-constraints keep infinite-capacity semantics.",
                "DescriptionZh": "约束资源按有限产能排程，非约束资源保持无限产能语义。",
                "Status": "Active",
            },
            {
                "AssumptionID": "NO_FULL_MRP_IN_SOLVER",
                "Description": "Material, inbound supply and WIP are evaluated by release gating, not as CP-SAT hard constraints.",
                "DescriptionZh": "物料、在途和 WIP 由释放门控判断，不作为当前 CP-SAT 硬约束。",
                "Status": "Active",
            },
            {
                "AssumptionID": "SINGLE_UNIT_SETUP_ONLY",
                "Description": "Sequence-dependent setup is active only on finite single-unit resources.",
                "DescriptionZh": "顺序相关换型仅在单台有限资源上启用，多机台换型待后续建模。",
                "Status": "Active",
            },
        ],
        "TunableParameters": [
            {
                "ParameterID": "TimeLimitSeconds",
                "Layer": "CP-SAT",
                "DriverStatus": "Applied",
                "Description": "Passed to CP-SAT max_time_in_seconds.",
                "DescriptionZh": "传入 CP-SAT 的最大求解时间。",
            },
            {
                "ParameterID": "ObjectiveStrategyID",
                "Layer": "CP-SAT",
                "DriverStatus": "Applied",
                "Description": "Selects a built-in strategy or a custom strategy catalog entry.",
                "DescriptionZh": "选择内置目标策略或后台自定义策略。",
            },
            {
                "ParameterID": "ObjectiveWeights",
                "Layer": "CP-SAT",
                "DriverStatus": "Applied",
                "Description": "Custom tardiness, makespan and alternate-resource weights drive the weighted objective.",
                "DescriptionZh": "自定义迟期、完工跨度和备用资源权重会驱动加权目标。",
            },
            {
                "ParameterID": "TimeBufferMinutes",
                "Layer": "PlanningInput",
                "DriverStatus": "PartiallyApplied",
                "Description": "Used for protected due date semantics; not a complete DBR hard-constraint model.",
                "DescriptionZh": "用于保护交期语义，但不是完整 DBR 硬约束模型。",
            },
            {
                "ParameterID": "ReleasePolicy",
                "Layer": "ReleaseGate",
                "DriverStatus": "PartiallyApplied",
                "Description": "Frozen for release evaluation and traceability; not fully back-propagated into CP-SAT.",
                "DescriptionZh": "用于释放评估和追溯，尚未完整反向驱动 CP-SAT。",
            },
        ],
        "BuiltInObjectiveStrategies": sorted(BUILT_IN_OBJECTIVE_STRATEGY_IDS),
        "CustomStrategyCount": len(scheduling_strategy_versions),
        "ActiveCustomStrategyID": (
            active_strategy.get("StrategyID") if active_strategy else None
        ),
        "ActiveReleasePolicyVersionID": (
            active_release_policy.get("VersionID")
            if active_release_policy
            else None
        ),
        "DeferredRules": [
            "Batching",
            "MergeSplit",
            "MultiMachineSetup",
            "BomMrp",
            "CrewSize",
            "SimioFeedback",
        ],
    }


def _retire_other_active_scheduling_strategies(
    *,
    scheduling_strategy_versions: dict[str, dict[str, object]],
    active_strategy_id: str,
) -> None:
    for strategy_id, strategy in scheduling_strategy_versions.items():
        if strategy_id != active_strategy_id and strategy.get("Status") == "Active":
            strategy["Status"] = "Retired"
            strategy["RetiredByStrategyID"] = active_strategy_id


def _master_data_version_diff(
    *,
    baseline: dict[str, object],
    candidate: dict[str, object],
) -> dict[str, object]:
    object_keys = [
        "Resources",
        "Routings",
        "Orders",
        "InventoryBuffers",
        "MaterialRequirements",
    ]
    rows = []
    for key in object_keys:
        baseline_ids = _object_identity_set(key, baseline.get(key))
        candidate_ids = _object_identity_set(key, candidate.get(key))
        rows.append(
            {
                "ObjectKey": key,
                "BaselineCount": len(baseline_ids),
                "CandidateCount": len(candidate_ids),
                "AddedIDs": sorted(candidate_ids - baseline_ids),
                "RemovedIDs": sorted(baseline_ids - candidate_ids),
                "CommonCount": len(baseline_ids & candidate_ids),
            }
        )
    return {
        "BaselineVersionID": baseline.get("VersionID"),
        "CandidateVersionID": candidate.get("VersionID"),
        "Rows": rows,
        "Summary": {
            "AddedObjectCount": sum(len(row["AddedIDs"]) for row in rows),
            "RemovedObjectCount": sum(len(row["RemovedIDs"]) for row in rows),
            "ChangedObjectGroups": [
                row["ObjectKey"]
                for row in rows
                if row["AddedIDs"] or row["RemovedIDs"]
            ],
        },
    }


def _object_identity_set(object_key: str, value: object) -> set[str]:
    identities = set()
    for item in value if isinstance(value, list) else []:
        if not isinstance(item, dict):
            continue
        if object_key == "Resources":
            identities.add(str(item.get("ResourceID")))
        elif object_key == "Routings":
            identities.add(f"{item.get('ProductID')}:{item.get('RoutingID')}")
        elif object_key == "Orders":
            identities.add(str(item.get("OrderID")))
        elif object_key == "InventoryBuffers":
            identities.add(f"{item.get('ItemID')}:{item.get('LocationID')}")
        elif object_key == "MaterialRequirements":
            identities.add(
                f"{item.get('OrderID')}:{item.get('ItemID')}:{item.get('LocationID')}"
            )
    return {identity for identity in identities if identity != "None"}


def _parse_iso_datetime(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _calculate_workbench_data_from_entities(
    *,
    problem_id: str,
    schedule_start_at: datetime,
    resources: list[Resource],
    routings: list[Routing],
    orders: list[SchedulingOrder],
    inventory_buffers: list[InventoryBufferPolicy],
    validation: MasterDataValidationResult,
    time_buffer_minutes: int = 0,
    calendar_timezone: str | None = None,
    solver_backend_id: str = "baseline-finite",
    generated_at: datetime | None = None,
    solver_time_limit_seconds: float | None = None,
    fixed_assignments: list[FixedOperationAssignment] | None = None,
    setup_transitions: list[SetupTransition] | None = None,
    objective: SchedulingObjective | None = None,
    align_release_to_schedule: bool = False,
    release_policy: dict[str, object] | None = None,
) -> dict[str, object]:
    view = build_planner_workbench_view(
        problem_id=problem_id,
        orders=orders,
        resources=resources,
        routings=routings,
        schedule_start_at=schedule_start_at,
        time_buffer_minutes=time_buffer_minutes,
        calendar_tzinfo=ZoneInfo(calendar_timezone) if calendar_timezone else None,
        solver_backend_id=solver_backend_id,
        generated_at=generated_at,
        inventory_buffers=inventory_buffers,
        solver_time_limit_seconds=solver_time_limit_seconds,
        fixed_assignments=fixed_assignments,
        setup_transitions=setup_transitions,
        objective=objective,
        align_release_to_schedule=align_release_to_schedule,
        release_policy=release_policy,
    )
    data = planner_workbench_view_to_dict(view)
    data["Validation"] = _master_data_validation_to_dict(validation)
    data["ObjectiveWeights"] = _objective_to_payload_dict(objective or SchedulingObjective())
    return data


def _invalid_scenario_label(
    baseline_validation: MasterDataValidationResult,
    candidate_validation: MasterDataValidationResult,
) -> str:
    if not baseline_validation.is_valid and not candidate_validation.is_valid:
        return "Both"
    if not baseline_validation.is_valid:
        return "Baseline"
    return "Candidate"


def _master_data_validation_to_dict(
    validation: MasterDataValidationResult,
) -> dict[str, object]:
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


def _execution_event_summary(events: list[dict[str, object]]) -> dict[str, object]:
    return summarize_execution_events(events)


def _planner_shell_html() -> str:
    return Path(__file__).with_name("web").joinpath("planner-workbench.html").read_text(
        encoding="utf-8"
    )


def _planner_workbench_html() -> str:
    return """<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Planner Workbench</title>
  <style>
    :root { color-scheme: light; font-family: Arial, sans-serif; }
    body { margin: 0; background: #f6f7f9; color: #172033; }
    header { padding: 20px 28px; background: #ffffff; border-bottom: 1px solid #d9dee7; }
    h1 { margin: 0; font-size: 24px; }
    .toolbar { margin-top: 12px; display: flex; gap: 10px; align-items: center; }
    select, button, textarea { border: 1px solid #b9c1d0; border-radius: 6px; padding: 7px 9px; background: #fff; }
    input { border: 1px solid #b9c1d0; border-radius: 6px; padding: 7px 9px; background: #fff; }
    button { background: #1f5fd1; color: #fff; border-color: #1f5fd1; cursor: pointer; }
    button.secondary { background: #ffffff; color: #1f5fd1; }
    textarea { width: 100%; min-height: 260px; box-sizing: border-box; font-family: Consolas, monospace; font-size: 12px; line-height: 1.4; }
    pre { margin: 0; padding: 10px; background: #f1f4f8; border-radius: 6px; overflow: auto; max-height: 220px; }
    .error { color: #b42318; min-height: 18px; }
    main { padding: 20px 28px; display: grid; gap: 18px; }
    .metrics { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 12px; }
    .metric, section { background: #ffffff; border: 1px solid #d9dee7; border-radius: 8px; padding: 14px; }
    .label { color: #5c667a; font-size: 12px; text-transform: uppercase; }
    .value { font-size: 24px; font-weight: 700; margin-top: 4px; }
    .grid { display: grid; gap: 8px; }
    .form-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(210px, 1fr)); gap: 10px; align-items: end; }
    .field { display: grid; gap: 4px; }
    .row { display: grid; grid-template-columns: 140px 1fr; gap: 8px; align-items: center; }
    .cells { display: flex; gap: 6px; }
    .cell { min-width: 84px; padding: 8px; border-radius: 6px; background: #e8f1ff; font-size: 12px; }
    .cell.over { background: #ffd9d9; }
    .buffer-item { padding: 10px; border-radius: 6px; border-left: 5px solid #8da2c0; background: #f5f7fb; }
    .buffer-red { border-left-color: #d92d20; background: #fff1f0; }
    .buffer-yellow { border-left-color: #d18b00; background: #fff8e1; }
    .buffer-green { border-left-color: #1f8f4d; background: #eefaf2; }
    .bar-line { position: relative; height: 30px; background: #eef1f5; border-radius: 6px; overflow: hidden; }
    .bar { position: absolute; top: 5px; height: 20px; background: #246bfe; border-radius: 5px; color: #fff; font-size: 11px; padding-left: 6px; white-space: nowrap; }
  </style>
</head>
<body>
  <header>
    <h1 data-i18n="appTitle">需求驱动计划员工作台</h1>
    <div class="toolbar">
      <label class="label" for="language-select" data-i18n="language">语言</label>
      <select id="language-select">
        <option value="zh">中文</option>
        <option value="en">English</option>
      </select>
      <label class="label" for="solver-select" data-i18n="solver">求解器</label>
      <select id="solver-select">
        <option value="baseline-finite">Baseline finite</option>
        <option value="ortools">OR-Tools</option>
        <option value="gurobi">Gurobi</option>
      </select>
      <button id="calculate-button" type="button" data-i18n="calculate">计算</button>
      <button id="compare-scenarios-button" class="secondary" type="button" data-i18n="compareCandidate">比较候选方案</button>
      <button id="simio-export-button" class="secondary" type="button" data-i18n="simioExport">Simio 导出</button>
    </div>
    <div class="label" id="solver-status" data-i18n="loadingSolver">正在加载求解器状态</div>
    <div class="error" id="workbench-error"></div>
  </header>
  <main>
    <section>
      <h2 data-i18n="masterDataRequest">主数据请求</h2>
      <button id="validate-master-data-button" class="secondary" type="button" data-i18n="validateMasterData">校验主数据</button>
      <textarea id="master-data-input"></textarea>
      <div id="master-data-health-summary" class="metrics"></div>
      <div id="master-data-issues" class="grid"></div>
      <pre id="master-data-validation" data-i18n="noMasterDataValidation">尚未运行主数据校验。</pre>
    </section>
    <div class="metrics">
      <div class="metric"><div class="label" data-i18n="orders">订单</div><div class="value" id="order-count">0</div></div>
      <div class="metric"><div class="label" data-i18n="constraintOverloads">约束超载</div><div class="value" id="overload-count">0</div></div>
      <div class="metric"><div class="label" data-i18n="redBuffer">红色缓冲</div><div class="value" id="buffer-red-count">0</div></div>
      <div class="metric"><div class="label" data-i18n="yellowBuffer">黄色缓冲</div><div class="value" id="buffer-yellow-count">0</div></div>
      <div class="metric"><div class="label" data-i18n="greenBuffer">绿色缓冲</div><div class="value" id="buffer-green-count">0</div></div>
      <div class="metric"><div class="label" data-i18n="bufferAlert">缓冲预警</div><div class="value" id="buffer-alert-status">无</div></div>
      <div class="metric"><div class="label" data-i18n="generated">生成时间</div><div class="value" id="generated-at">-</div></div>
    </div>
    <section>
      <h2 data-i18n="systemLoadGraph">系统负载图</h2>
      <div id="load-graph" class="grid"></div>
    </section>
    <section>
      <h2 data-i18n="ganttChart">甘特图</h2>
      <div id="gantt-chart" class="grid"></div>
    </section>
    <section>
      <h2 data-i18n="releaseBoard">释放看板</h2>
      <div id="release-board" class="grid"></div>
    </section>
    <section>
      <h2 data-i18n="scenarioComparison">方案对比</h2>
      <div class="toolbar">
        <button id="copy-baseline-to-candidate-button" class="secondary" type="button" data-i18n="copyBaselineToCandidate">复制基准到候选</button>
      </div>
      <label class="field"><span class="label" data-i18n="candidateScenario">候选方案</span><textarea id="candidate-master-data-input"></textarea></label>
      <div id="scenario-comparison-output" class="grid" data-i18n="noScenarioComparison">尚未运行方案对比。</div>
    </section>
    <section>
      <h2 data-i18n="releaseGate">释放门</h2>
      <div class="form-grid">
        <label class="field"><span class="label" data-i18n="order">订单</span><input id="release-order-id" value="WO-1001"></label>
        <label class="field"><span class="label" data-i18n="requestedRelease">请求释放时间</span><input id="release-requested-at" value="2026-06-20T05:00:00+00:00"></label>
        <button id="release-gate-button" type="button" data-i18n="checkRelease">检查释放</button>
      </div>
      <div id="release-gate-decision" class="grid"></div>
      <pre id="release-gate-output" data-i18n="noReleaseChecked">尚未检查释放。</pre>
    </section>
    <section>
      <h2 data-i18n="bufferBoard">缓冲看板</h2>
      <div id="buffer-board" class="grid"></div>
    </section>
    <section>
      <h2 data-i18n="inventoryBufferBoard">库存缓冲看板</h2>
      <div id="inventory-buffer-board" class="grid"></div>
    </section>
    <section>
      <h2 data-i18n="capacityBufferBoard">产能缓冲看板</h2>
      <div id="capacity-buffer-board" class="grid"></div>
    </section>
    <section>
      <h2 data-i18n="executionPriority">执行优先级</h2>
      <div id="execution-priority" class="grid"></div>
    </section>
    <section>
      <h2 data-i18n="constraintCandidates">候选约束</h2>
      <div id="bottleneck-candidates" class="grid"></div>
    </section>
    <section>
      <h2 data-i18n="shopFloorExecution">车间执行</h2>
      <div class="form-grid">
        <label class="field"><span class="label" data-i18n="order">订单</span><input id="execution-order-id" value="WO-1001"></label>
        <label class="field"><span class="label" data-i18n="event">事件</span><select id="execution-event-type"><option value="ArrivedBuffer" data-i18n="arrivedBuffer">到达缓冲</option><option value="StartedOperation" data-i18n="startedOperation">开始加工</option><option value="CompletedOperation" data-i18n="completedOperation">完成工序</option><option value="Shipped" data-i18n="shipped">已发货</option></select></label>
        <label class="field"><span class="label" data-i18n="eventAt">事件时间</span><input id="execution-event-at" value="2026-06-16T09:00:00+00:00"></label>
        <label class="field"><span class="label" data-i18n="targetStart">目标开始</span><input id="execution-target-start-at" value="2026-06-16T08:00:00+00:00"></label>
        <label class="field"><span class="label" data-i18n="standardExceptionCode">标准异常代码</span><select id="execution-exception-code-select"></select></label>
        <label class="field"><span class="label" data-i18n="exceptionCode">异常代码</span><input id="execution-exception-code" data-i18n-placeholder="requiredWhenLate" placeholder="迟到时必填"></label>
        <button id="record-execution-button" type="button" data-i18n="recordEvent">记录事件</button>
      </div>
      <pre id="execution-event-result" data-i18n="noExecutionEventRecorded">尚未记录执行事件。</pre>
      <div id="execution-event-summary" class="grid"></div>
      <div id="exception-code-catalog" class="grid"></div>
      <div id="process-transitions" class="grid"></div>
      <div id="execution-event-history" class="grid"></div>
    </section>
    <section>
      <h2 data-i18n="alternateRouteSuggestions">备用工艺路线建议</h2>
      <div id="alternate-routes" class="grid"></div>
    </section>
    <section>
      <h2 data-i18n="simioExportPreview">Simio 导出预览</h2>
      <pre id="simio-export-output" data-i18n="noExportGenerated">尚未生成导出。</pre>
    </section>
  </main>
  <script>
    const I18N = {
      zh: {
        appTitle: '需求驱动计划员工作台',
        language: '语言',
        solver: '求解器',
        calculate: '计算',
        compareCandidate: '比较候选方案',
        simioExport: 'Simio 导出',
        loadingSolver: '正在加载求解器状态',
        masterDataRequest: '主数据请求',
        validateMasterData: '校验主数据',
        noMasterDataValidation: '尚未运行主数据校验。',
        masterDataValid: '主数据有效',
        masterDataInvalid: '主数据存在问题',
        resources: '资源',
        constraints: '约束',
        calendars: '日历',
        routings: '路线',
        inventoryBuffers: '库存缓冲',
        noMasterDataIssues: '未发现主数据问题。',
        orders: '订单',
        constraintOverloads: '约束超载',
        redBuffer: '红色缓冲',
        yellowBuffer: '黄色缓冲',
        greenBuffer: '绿色缓冲',
        bufferAlert: '缓冲预警',
        generated: '生成时间',
        systemLoadGraph: '系统负载图',
        ganttChart: '甘特图',
        releaseBoard: '释放看板',
        scenarioComparison: '方案对比',
        candidateScenario: '候选方案',
        copyBaselineToCandidate: '复制基准到候选',
        noScenarioComparison: '尚未运行方案对比。',
        releaseGate: '释放门',
        order: '订单',
        requestedRelease: '请求释放时间',
        checkRelease: '检查释放',
        noReleaseChecked: '尚未检查释放。',
        releaseAllowed: '允许释放',
        releaseBlocked: '禁止过早释放',
        releaseOrderNotFound: '未找到释放订单',
        suggestedRelease: '建议释放时间',
        minutesEarly: '提前分钟',
        requestedAt: '请求时间',
        bufferBoard: '缓冲看板',
        inventoryBufferBoard: '库存缓冲看板',
        capacityBufferBoard: '产能缓冲看板',
        executionPriority: '执行优先级',
        constraintCandidates: '候选约束',
        shopFloorExecution: '车间执行',
        event: '事件',
        arrivedBuffer: '到达缓冲',
        startedOperation: '开始加工',
        completedOperation: '完成工序',
        shipped: '已发货',
        eventAt: '事件时间',
        targetStart: '目标开始',
        standardExceptionCode: '标准异常代码',
        chooseExceptionCode: '选择异常代码',
        exceptionCode: '异常代码',
        requiredWhenLate: '迟到时必填',
        recordEvent: '记录事件',
        noExecutionEventRecorded: '尚未记录执行事件。',
        alternateRouteSuggestions: '备用工艺路线建议',
        simioExportPreview: 'Simio 导出预览',
        noExportGenerated: '尚未生成导出。',
        critical: '严重',
        none: '无',
        release: '释放',
        target: '目标',
        onHand: '现有量',
        redYellowGreen: '红/黄/绿',
        penetration: '渗透率',
        noReleaseRecommendations: '无释放建议。',
        noBufferSignals: '无缓冲信号。',
        noInventoryBuffers: '未配置库存缓冲。',
        noCapacityBuffers: '无非约束产能缓冲。',
        capacity: '产能',
        required: '需求',
        sprintCapacity: '冲刺产能',
        healthy: '健康',
        watch: '关注',
        overloaded: '超载',
        noExecutionPriorities: '无执行优先级。',
        bottleneckRecommendation: '评审为新的约束候选',
        overloadedBuckets: '超载周期',
        maxLoad: '最大负载',
        overload: '超载',
        min: '分钟',
        noBottleneckCandidates: '无持续性非约束超载。',
        noAlternateRouteSuggestions: '无备用路线建议。',
        recommendedScenario: '推荐方案',
        scenarioOrderCount: '订单数',
        scenarioConstraintOverloads: '约束超载数',
        scenarioTotalOverloadMinutes: '总超载分钟',
        scenarioRedBufferCount: '红色缓冲数',
        criticalAlert: '关键预警',
        totalOverloadDelta: '总超载差值',
        redBufferDelta: '红缓冲差值',
        decisionReasons: '决策原因',
        noDecisionReasons: '没有返回决策原因。',
        invalidScenario: '无效方案',
        message: '消息',
        baselineValidation: '基准方案校验',
        candidateValidation: '候选方案校验',
        valid: '有效',
        invalid: '无效',
        masterDataValidationFailed: '主数据校验失败。',
        totalEvents: '事件总数',
        requiresReview: '需复核',
        reworkLoops: '返工环路',
        lateArrivalSummary: '迟到摘要',
        late: '迟到',
        average: '平均',
        max: '最大',
        exceptionCategories: '异常类别',
        topExceptionCategories: 'Top 异常类别',
        exceptionCodes: '异常代码',
        count: '次数',
        review: '复核',
        reworkLoop: '返工环路',
        noProcessTransitions: '未发现流程流转。',
        noExecutionEvents: '无执行事件记录。',
        materialShortage: '物料短缺',
        equipmentDown: '设备故障',
        staffAbsence: '人员缺勤',
        qualityRework: '质量返工',
        categorySupply: '供应',
        categoryEquipment: '设备',
        categoryLabor: '人员',
        categoryQuality: '质量',
        status: '状态',
        noAction: '无建议'
      },
      en: {
        appTitle: 'Demand-Driven Planner Workbench',
        language: 'Language',
        solver: 'Solver',
        calculate: 'Calculate',
        compareCandidate: 'Compare candidate',
        simioExport: 'Simio export',
        loadingSolver: 'Loading solver status',
        masterDataRequest: 'Master data request',
        validateMasterData: 'Validate master data',
        noMasterDataValidation: 'No master data validation has run.',
        masterDataValid: 'Master data valid',
        masterDataInvalid: 'Master data has issues',
        resources: 'Resources',
        constraints: 'Constraints',
        calendars: 'Calendars',
        routings: 'Routings',
        inventoryBuffers: 'Inventory buffers',
        noMasterDataIssues: 'No master data issues found.',
        orders: 'Orders',
        constraintOverloads: 'Constraint overloads',
        redBuffer: 'Red buffer',
        yellowBuffer: 'Yellow buffer',
        greenBuffer: 'Green buffer',
        bufferAlert: 'Buffer alert',
        generated: 'Generated',
        systemLoadGraph: 'System load graph',
        ganttChart: 'Gantt chart',
        releaseBoard: 'Release board',
        scenarioComparison: 'Scenario comparison',
        candidateScenario: 'Candidate scenario',
        copyBaselineToCandidate: 'Copy baseline to candidate',
        noScenarioComparison: 'No scenario comparison has run.',
        releaseGate: 'Release gate',
        order: 'Order',
        requestedRelease: 'Requested release',
        checkRelease: 'Check release',
        noReleaseChecked: 'No release check has run.',
        releaseAllowed: 'Release allowed',
        releaseBlocked: 'Early release blocked',
        releaseOrderNotFound: 'Release order not found',
        suggestedRelease: 'Suggested release',
        minutesEarly: 'Minutes early',
        requestedAt: 'Requested at',
        bufferBoard: 'Buffer board',
        inventoryBufferBoard: 'Inventory buffer board',
        capacityBufferBoard: 'Capacity buffer board',
        executionPriority: 'Execution priority',
        constraintCandidates: 'Constraint candidates',
        shopFloorExecution: 'Shop floor execution',
        event: 'Event',
        arrivedBuffer: 'Arrived buffer',
        startedOperation: 'Started operation',
        completedOperation: 'Completed operation',
        shipped: 'Shipped',
        eventAt: 'Event at',
        targetStart: 'Target start',
        standardExceptionCode: 'Standard exception code',
        chooseExceptionCode: 'Choose exception code',
        exceptionCode: 'Exception code',
        requiredWhenLate: 'Required when late',
        recordEvent: 'Record event',
        noExecutionEventRecorded: 'No execution event recorded.',
        alternateRouteSuggestions: 'Alternate route suggestions',
        simioExportPreview: 'Simio export preview',
        noExportGenerated: 'No export generated.',
        critical: 'Critical',
        none: 'None',
        release: 'release',
        target: 'target',
        onHand: 'on hand',
        redYellowGreen: 'red/yellow/green',
        penetration: 'penetration',
        noReleaseRecommendations: 'No release recommendations.',
        noBufferSignals: 'No buffer signals.',
        noInventoryBuffers: 'No inventory buffers configured.',
        noCapacityBuffers: 'No non-constraint capacity buffers.',
        capacity: 'capacity',
        required: 'required',
        sprintCapacity: 'sprint capacity',
        healthy: 'Healthy',
        watch: 'Watch',
        overloaded: 'Overloaded',
        noExecutionPriorities: 'No execution priorities.',
        bottleneckRecommendation: 'Review as new constraint candidate',
        overloadedBuckets: 'overloaded buckets',
        maxLoad: 'max load',
        overload: 'overload',
        min: 'min',
        noBottleneckCandidates: 'No sustained non-constraint overloads.',
        noAlternateRouteSuggestions: 'No alternate route suggestions.',
        recommendedScenario: 'Recommended scenario',
        scenarioOrderCount: 'Order count',
        scenarioConstraintOverloads: 'Constraint overloads',
        scenarioTotalOverloadMinutes: 'Total overload minutes',
        scenarioRedBufferCount: 'Red buffer count',
        criticalAlert: 'Critical alert',
        totalOverloadDelta: 'Total overload delta',
        redBufferDelta: 'Red buffer delta',
        decisionReasons: 'Decision reasons',
        noDecisionReasons: 'No decision reasons returned.',
        invalidScenario: 'Invalid scenario',
        message: 'Message',
        baselineValidation: 'Baseline validation',
        candidateValidation: 'Candidate validation',
        valid: 'valid',
        invalid: 'invalid',
        masterDataValidationFailed: 'Master data validation failed.',
        totalEvents: 'Total events',
        requiresReview: 'Requires review',
        reworkLoops: 'Rework loops',
        lateArrivalSummary: 'Late arrival summary',
        late: 'late',
        average: 'average',
        max: 'max',
        exceptionCategories: 'Exception categories',
        topExceptionCategories: 'Top exception categories',
        exceptionCodes: 'Exception codes',
        count: 'count',
        review: 'review',
        reworkLoop: 'rework loop',
        noProcessTransitions: 'No process transitions discovered.',
        noExecutionEvents: 'No execution events recorded.',
        materialShortage: 'Material shortage',
        equipmentDown: 'Equipment down',
        staffAbsence: 'Staff absence',
        qualityRework: 'Quality rework',
        categorySupply: 'Supply',
        categoryEquipment: 'Equipment',
        categoryLabor: 'Labor',
        categoryQuality: 'Quality',
        status: 'Status',
        noAction: 'No recommendation'
      }
    };

    let currentLanguage = 'zh';

    function t(key) {
      return (I18N[currentLanguage] && I18N[currentLanguage][key]) || I18N.en[key] || key;
    }

    function applyLanguage() {
      currentLanguage = document.getElementById('language-select').value;
      document.documentElement.lang = currentLanguage === 'zh' ? 'zh-CN' : 'en';
      document.title = t('appTitle');
      document.querySelectorAll('[data-i18n]').forEach(element => {
        element.textContent = t(element.dataset.i18n);
      });
      document.querySelectorAll('[data-i18n-placeholder]').forEach(element => {
        element.placeholder = t(element.dataset.i18nPlaceholder);
      });
    }

    function zoneLabel(zone) {
      const key = { Red: 'redBuffer', Yellow: 'yellowBuffer', Green: 'greenBuffer' }[zone];
      return key ? t(key) : zone;
    }

    function eventLabel(value) {
      const key = {
        ArrivedBuffer: 'arrivedBuffer',
        StartedOperation: 'startedOperation',
        CompletedOperation: 'completedOperation',
        Shipped: 'shipped'
      }[value];
      return key ? t(key) : value;
    }

    function exceptionCategoryLabel(value) {
      const key = {
        Supply: 'categorySupply',
        Equipment: 'categoryEquipment',
        Labor: 'categoryLabor',
        Quality: 'categoryQuality'
      }[value];
      return key ? t(key) : value;
    }

    function localizedScenarioName(value) {
      const scenarioMap = {
        Baseline: { zh: '基准方案', en: 'Baseline' },
        Candidate: { zh: '候选方案', en: 'Candidate' }
      };
      return scenarioMap[value] ? scenarioMap[value][currentLanguage] : value;
    }

    function localizedAction(value) {
      const actionMap = {
        'Expedite to constraint': { zh: '加急送达约束资源', en: 'Expedite to constraint' },
        'Release now': { zh: '立即释放', en: 'Release now' },
        'Hold release': { zh: '暂缓释放', en: 'Hold release' },
        'Red buffer penetration': { zh: '红色缓冲渗透', en: 'Red buffer penetration' },
        'Inside release window': { zh: '已进入释放窗口', en: 'Inside release window' },
        'Not ready for release': { zh: '尚未到释放时间', en: 'Not ready for release' },
        'Expedite replenishment': { zh: '加急补货', en: 'Expedite replenishment' },
        'Release replenishment order': { zh: '释放补货订单', en: 'Release replenishment order' },
        'Maintain buffer': { zh: '维持缓冲', en: 'Maintain buffer' },
        'Review as new constraint candidate': { zh: '评审为新的约束候选', en: 'Review as new constraint candidate' },
        'Reclassify or offload work': { zh: '重新定义约束或转移负荷', en: 'Reclassify or offload work' },
        'Reserve sprint capacity': { zh: '预留冲刺产能', en: 'Reserve sprint capacity' },
        'Protect sprint capacity': { zh: '保护冲刺产能', en: 'Protect sprint capacity' }
      };
      return actionMap[value] ? actionMap[value][currentLanguage] : (value || t('noAction'));
    }

    function capacityStatusLabel(value) {
      const key = {
        Healthy: 'healthy',
        Watch: 'watch',
        Overloaded: 'overloaded'
      }[value];
      return key ? t(key) : value;
    }

    function releaseStatusLabel(value) {
      const key = {
        ReleaseAllowed: 'releaseAllowed',
        ReleaseBlocked: 'releaseBlocked',
        ReleaseOrderNotFound: 'releaseOrderNotFound'
      }[value];
      return key ? t(key) : value;
    }

    function localizedDecisionReason(reason) {
      if (currentLanguage !== 'zh') {
        return reason;
      }
      let match = reason.match(/^Candidate reduces total overload by (\\d+) minutes\\.$/);
      if (match) {
        return `候选方案减少总超载 ${match[1]} 分钟。`;
      }
      match = reason.match(/^Baseline has (\\d+) fewer overload minutes than Candidate\\.$/);
      if (match) {
        return `基准方案比候选方案少 ${match[1]} 分钟超载。`;
      }
      match = reason.match(/^Candidate reduces red buffer count by (\\d+)\\.$/);
      if (match) {
        return `候选方案减少红色缓冲 ${match[1]} 项。`;
      }
      match = reason.match(/^Baseline has (\\d+) fewer red buffer items than Candidate\\.$/);
      if (match) {
        return `基准方案比候选方案少 ${match[1]} 个红色缓冲项。`;
      }
      if (reason === 'Candidate clears a critical buffer alert.') {
        return '候选方案清除了严重缓冲预警。';
      }
      match = reason.match(/^(Baseline|Candidate) has the better overall scenario score\\.$/);
      if (match) {
        return `${localizedScenarioName(match[1])} 的综合方案评分更优。`;
      }
      return reason;
    }

    const DEFAULT_MASTER_DATA = {
      ProblemID: 'DEMO-PLAN',
      ScheduleStartAt: '2026-06-16T08:00:00+00:00',
      SolverBackendID: 'baseline-finite',
      CalendarTimezone: 'UTC',
      TimeBufferMinutes: 240,
      Resources: [
        {
          ResourceID: 'WC-DRUM',
          Name: 'Constraint Cutter',
          IsConstraint: true,
          DailyCapacityMinutes: { '2026-06-16': 480 },
          Calendar: {
            CalendarID: 'CAL-DRUM-DAY',
            WorkingWeekdays: [0, 1, 2, 3, 4],
            Holidays: [],
            Shifts: [
              { Name: 'Day', Start: '08:00', End: '16:00' }
            ],
            MaintenanceWindows: []
          }
        },
        {
          ResourceID: 'WC-ASM',
          Name: 'Assembly Cell',
          IsConstraint: false,
          DailyCapacityMinutes: { '2026-06-16': 960 }
        }
      ],
      Routings: [
        {
          ProductID: 'FG-A',
          RoutingID: 'PRIMARY',
          IsPrimary: true,
          Operations: [
            { OperationID: 'CUT', ResourceID: 'WC-DRUM', DurationMinutes: 120, Sequence: 1 },
            { OperationID: 'ASM', ResourceID: 'WC-ASM', DurationMinutes: 80, Sequence: 2 }
          ]
        }
      ],
      Orders: [
        {
          OrderID: 'WO-1001',
          ProductID: 'FG-A',
          Quantity: 2,
          DueDate: '2026-06-20T08:00:00+00:00',
          TargetStartDate: '2026-06-16'
        }
      ],
      InventoryBuffers: [
        {
          ItemID: 'RM-STEEL',
          LocationID: 'SUPPLIER-DECOUPLING',
          OnHandQty: 35,
          RedZoneQty: 50,
          YellowZoneQty: 120,
          GreenZoneQty: 200
        }
      ]
    };

    const DEMO_ENDPOINT = '/planner/workbench/demo?solver_backend_id=';
    const EXCEPTION_CODE_CATALOG = [
      { Code: 'MATERIAL_SHORTAGE', DisplayNameKey: 'materialShortage', CategoryKey: 'categorySupply' },
      { Code: 'EQUIPMENT_DOWN', DisplayNameKey: 'equipmentDown', CategoryKey: 'categoryEquipment' },
      { Code: 'STAFF_ABSENCE', DisplayNameKey: 'staffAbsence', CategoryKey: 'categoryLabor' },
      { Code: 'QUALITY_REWORK', DisplayNameKey: 'qualityRework', CategoryKey: 'categoryQuality' }
    ];
    let exceptionCodeCatalog = EXCEPTION_CODE_CATALOG;

    function readMasterData() {
      const payload = JSON.parse(document.getElementById('master-data-input').value);
      payload.SolverBackendID = document.getElementById('solver-select').value;
      return payload;
    }

    function populateExceptionCodeSelect() {
      const select = document.getElementById('execution-exception-code-select');
      const selectedValue = select.value;
      select.innerHTML = `<option value="">${t('chooseExceptionCode')}</option>` + exceptionCodeCatalog
        .map(item => `<option value="${item.Code}">${item.Code} - ${exceptionDisplayName(item)}</option>`)
        .join('');
      select.value = selectedValue;
    }

    function exceptionDisplayName(item) {
      return item.DisplayNameKey ? t(item.DisplayNameKey) : item.DisplayName;
    }

    function exceptionCategoryName(item) {
      return item.CategoryKey ? t(item.CategoryKey) : item.Category;
    }

    function exceptionDisplayNameKey(code) {
      return {
        MATERIAL_SHORTAGE: 'materialShortage',
        EQUIPMENT_DOWN: 'equipmentDown',
        STAFF_ABSENCE: 'staffAbsence',
        QUALITY_REWORK: 'qualityRework'
      }[code];
    }

    function exceptionCategoryKey(category) {
      return {
        Supply: 'categorySupply',
        Equipment: 'categoryEquipment',
        Labor: 'categoryLabor',
        Quality: 'categoryQuality'
      }[category];
    }

    async function loadExceptionCodeCatalog() {
      try {
        const response = await fetch('/shop-floor/execution/exception-codes');
        const payload = await response.json();
        if (response.ok && Array.isArray(payload.Data)) {
          exceptionCodeCatalog = payload.Data.map(item => ({
            Code: item.Code,
            DisplayName: item.DisplayName,
            Category: item.Category,
            DisplayNameKey: exceptionDisplayNameKey(item.Code),
            CategoryKey: exceptionCategoryKey(item.Category)
          }));
          populateExceptionCodeSelect();
        }
      } catch (error) {
        exceptionCodeCatalog = EXCEPTION_CODE_CATALOG;
        populateExceptionCodeSelect();
      }
    }

    function readCandidateScenario() {
      const payload = JSON.parse(document.getElementById('candidate-master-data-input').value);
      payload.SolverBackendID = document.getElementById('solver-select').value;
      return payload;
    }

    function syncCandidateScenarioFromBaseline() {
      const baseline = readMasterData();
      const candidate = buildCandidateScenario(baseline);
      document.getElementById('candidate-master-data-input').value = JSON.stringify(candidate, null, 2);
    }

    function renderWorkbench(data) {
      document.getElementById('solver-status').textContent = `${data.SolverBackendID}: ${data.SolverStatus}`;
      document.getElementById('order-count').textContent = data.OrderCount;
      document.getElementById('overload-count').textContent = data.ConstraintOverloadCount;
      document.getElementById('buffer-red-count').textContent = data.BufferSummary.RedCount;
      document.getElementById('buffer-yellow-count').textContent = data.BufferSummary.YellowCount;
      document.getElementById('buffer-green-count').textContent = data.BufferSummary.GreenCount;
      document.getElementById('buffer-alert-status').textContent = data.BufferSummary.HasCriticalAlert ? t('critical') : (data.BufferSummary.HighestSeverity === 'None' ? t('none') : data.BufferSummary.HighestSeverity);
      document.getElementById('generated-at').textContent = data.GeneratedAt || '-';
      document.getElementById('load-graph').innerHTML = data.LoadGraphRows.map(row => `
        <div class="row"><strong>${row.ResourceID}</strong><div class="cells">
          ${row.Cells.map(cell => `<div class="cell ${cell.OverloadMinutes > 0 ? 'over' : ''}">${cell.Date}<br>${cell.LoadPercent}%</div>`).join('')}
        </div></div>`).join('');
      document.getElementById('gantt-chart').innerHTML = data.GanttRows.map(row => `
        <div class="row"><strong>${row.ResourceID}</strong><div class="bar-line">
          ${row.Bars.map((bar, index) => `<div class="bar" style="left:${index * 28}%; width:${Math.max(12, bar.DurationMinutes / 8)}%">${bar.OrderID}</div>`).join('')}
        </div></div>`).join('');
      document.getElementById('release-board').innerHTML = data.ReleaseRecommendations.length
        ? data.ReleaseRecommendations.map(item => `<div>${item.OrderID}: ${t('release')} ${item.SuggestedReleaseDate}</div>`).join('')
        : `<div>${t('noReleaseRecommendations')}</div>`;
      document.getElementById('buffer-board').innerHTML = data.BufferBoard.length
        ? data.BufferBoard.map(item => `<div class="buffer-item buffer-${item.Zone.toLowerCase()}"><strong>${zoneLabel(item.Zone)}</strong> ${item.OrderID}<br>${t('release')} ${item.SuggestedReleaseDate}<br>${t('target')} ${item.TargetStartDate}</div>`).join('')
        : `<div>${t('noBufferSignals')}</div>`;
      document.getElementById('inventory-buffer-board').innerHTML = data.InventoryBufferBoard.length
        ? data.InventoryBufferBoard.map(item => `<div class="buffer-item buffer-${item.Zone.toLowerCase()}"><strong>${zoneLabel(item.Zone)}</strong> ${item.ItemID}<br>${item.LocationID}<br>${t('onHand')} ${item.OnHandQty}<br>${t('redYellowGreen')} ${item.RedZoneQty}/${item.YellowZoneQty}/${item.GreenZoneQty}<br>${t('penetration')} ${item.PenetrationPercent}%<br>${localizedAction(item.RecommendedAction)}</div>`).join('')
        : `<div>${t('noInventoryBuffers')}</div>`;
      renderCapacityBufferBoard(data.CapacityBufferBoard || []);
      document.getElementById('execution-priority').innerHTML = data.ExecutionPriorityQueue.length
        ? data.ExecutionPriorityQueue.map(item => `<div class="buffer-item buffer-${item.Zone.toLowerCase()}"><strong>#${item.Rank}</strong> ${item.OrderID} (${zoneLabel(item.Zone)})<br>${localizedAction(item.RecommendedAction)}<br>${localizedAction(item.PriorityReason)}<br>${t('release')} ${item.SuggestedReleaseDate}</div>`).join('')
        : `<div>${t('noExecutionPriorities')}</div>`;
      const bottleneckRecommendation = t('bottleneckRecommendation');
      document.getElementById('bottleneck-candidates').innerHTML = data.BottleneckCandidates.length
        ? data.BottleneckCandidates.map(item => `<div class="buffer-item buffer-yellow"><strong>${item.ResourceID}</strong> ${item.ResourceName}<br>${localizedAction(item.Recommendation || bottleneckRecommendation)}<br>${t('overloadedBuckets')} ${item.OverloadedBucketCount}<br>${t('maxLoad')} ${item.MaxLoadPercent}%<br>${t('overload')} ${item.TotalOverloadMinutes} ${t('min')}</div>`).join('')
        : `<div>${t('noBottleneckCandidates')}</div>`;
      document.getElementById('alternate-routes').innerHTML = data.AlternateRouteSuggestions.length
        ? data.AlternateRouteSuggestions.map(item => `<div>${item.OrderID}: ${item.CurrentRoutingID} -> ${item.AlternateRoutingID}</div>`).join('')
        : `<div>${t('noAlternateRouteSuggestions')}</div>`;
      if (data.Validation) {
        renderMasterDataValidation(data.Validation);
      }
    }

    function renderMasterDataValidation(validation) {
      document.getElementById('master-data-validation').textContent = JSON.stringify(validation, null, 2);
      const summary = validation.Summary || {};
      const summaryItems = [
        [validation.IsValid ? t('masterDataValid') : t('masterDataInvalid'), validation.Issues ? validation.Issues.length : 0],
        [t('resources'), summary.ResourceCount || 0],
        [t('constraints'), summary.ConstraintResourceCount || 0],
        [t('calendars'), summary.CalendarResourceCount || 0],
        [t('routings'), summary.RoutingCount || 0],
        [t('orders'), summary.OrderCount || 0],
        [t('inventoryBuffers'), summary.InventoryBufferCount || 0]
      ];
      document.getElementById('master-data-health-summary').innerHTML = summaryItems
        .map(([label, value]) => `<div class="metric"><div class="label">${label}</div><div class="value">${value}</div></div>`)
        .join('');
      document.getElementById('master-data-issues').innerHTML = validation.Issues && validation.Issues.length
        ? validation.Issues.map(issue => `<div class="buffer-item buffer-red"><strong>${issue.Code}</strong> ${issue.Severity}<br>${issue.Message}<br>${issue.Field}</div>`).join('')
        : `<div class="buffer-item buffer-green">${t('noMasterDataIssues')}</div>`;
    }

    function renderCapacityBufferBoard(items) {
      document.getElementById('capacity-buffer-board').innerHTML = items.length
        ? items.map(item => {
          const statusClass = item.Status === 'Overloaded' ? 'buffer-red' : (item.Status === 'Watch' ? 'buffer-yellow' : 'buffer-green');
          return `<div class="buffer-item ${statusClass}"><strong>${item.ResourceID}</strong> ${item.ResourceName}<br>${t('status')}: ${capacityStatusLabel(item.Status)}<br>${t('capacity')} ${item.CapacityMinutes} ${t('min')} / ${t('required')} ${item.RequiredMinutes} ${t('min')}<br>${t('sprintCapacity')} ${item.SprintCapacityMinutes} ${t('min')}<br>${t('overload')} ${item.OverloadMinutes} ${t('min')} (${item.LoadPercent}%)<br>${localizedAction(item.Recommendation)}</div>`;
        }).join('')
        : `<div>${t('noCapacityBuffers')}</div>`;
    }

    function renderReleaseGateDecision(payload) {
      const data = payload.Data || {};
      if (data.Validation) {
        document.getElementById('release-gate-decision').innerHTML = `<div class="buffer-item buffer-red">${t('masterDataValidationFailed')}</div>`;
        return;
      }
      const statusClass = data.Allowed ? 'buffer-green' : 'buffer-red';
      const details = [
        `${t('order')}: ${data.OrderID || '-'}`,
        `${t('requestedAt')}: ${data.RequestedReleaseAt || '-'}`,
        `${t('suggestedRelease')}: ${data.SuggestedReleaseAt || '-'}`,
        `${t('minutesEarly')}: ${data.MinutesEarly || 0}`,
        data.Message || ''
      ].filter(Boolean).join('<br>');
      document.getElementById('release-gate-decision').innerHTML = `
        <div class="buffer-item ${statusClass}"><strong>${releaseStatusLabel(data.Status)}</strong><br>${details}</div>`;
    }

    async function calculateWorkbench() {
      document.getElementById('workbench-error').textContent = '';
      try {
        const response = await fetch('/planner/workbench/calculate', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(readMasterData())
        });
        const payload = await response.json();
        if (!response.ok) {
          if (payload.Data && payload.Data.Validation) {
            renderMasterDataValidation(payload.Data.Validation);
            throw new Error(t('masterDataValidationFailed'));
          }
          throw new Error(JSON.stringify(payload));
        }
        renderWorkbench(payload.Data);
      } catch (error) {
        document.getElementById('workbench-error').textContent = error.message;
      }
    }

    async function validateMasterData() {
      document.getElementById('workbench-error').textContent = '';
      try {
        const response = await fetch('/planner/workbench/master-data/validate', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(readMasterData())
        });
        const payload = await response.json();
        if (!response.ok) {
          throw new Error(JSON.stringify(payload));
        }
        renderMasterDataValidation(payload.Data);
      } catch (error) {
        document.getElementById('workbench-error').textContent = error.message;
      }
    }

    async function exportSimio() {
      document.getElementById('workbench-error').textContent = '';
      try {
        const response = await fetch('/planner/workbench/simio/export', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(readMasterData())
        });
        const payload = await response.json();
        if (!response.ok) {
          throw new Error(JSON.stringify(payload));
        }
        document.getElementById('simio-export-output').textContent = JSON.stringify(payload.Data, null, 2);
      } catch (error) {
        document.getElementById('workbench-error').textContent = error.message;
      }
    }

    function buildCandidateScenario(baseline) {
      const candidate = JSON.parse(JSON.stringify(baseline));
      if (candidate.Orders && candidate.Orders.length > 1) {
        const secondOrder = candidate.Orders[1];
        const nextDate = new Date(`${secondOrder.TargetStartDate}T00:00:00Z`);
        nextDate.setUTCDate(nextDate.getUTCDate() + 1);
        secondOrder.TargetStartDate = nextDate.toISOString().slice(0, 10);
      }
      return candidate;
    }

    function renderScenarioSummaryCard(label, summary) {
      return `<div class="buffer-item"><strong>${label}</strong><br>
        ${t('scenarioOrderCount')}: ${summary.OrderCount}<br>
        ${t('scenarioConstraintOverloads')}: ${summary.ConstraintOverloadCount}<br>
        ${t('scenarioTotalOverloadMinutes')}: ${summary.TotalOverloadMinutes} ${t('min')}<br>
        ${t('scenarioRedBufferCount')}: ${summary.RedBufferCount}<br>
        ${t('criticalAlert')}: ${summary.HasCriticalAlert ? t('critical') : t('none')}</div>`;
    }

    function renderScenarioComparison(data) {
      const delta = data.Delta;
      const reasons = data.DecisionReasons.length
        ? data.DecisionReasons.map(reason => `<div>${localizedDecisionReason(reason)}</div>`).join('')
        : `<div>${t('noDecisionReasons')}</div>`;
      document.getElementById('scenario-comparison-output').innerHTML = `
        ${renderScenarioSummaryCard(localizedScenarioName('Baseline'), data.Baseline)}
        ${renderScenarioSummaryCard(localizedScenarioName('Candidate'), data.Candidate)}
        <div class="buffer-item buffer-green"><strong>${t('recommendedScenario')}</strong><br>${localizedScenarioName(data.RecommendedScenario)}</div>
        <div class="buffer-item"><strong>${t('totalOverloadDelta')}</strong><br>${delta.TotalOverloadMinutes} ${t('min')}</div>
        <div class="buffer-item"><strong>${t('redBufferDelta')}</strong><br>${delta.RedBufferCount}</div>
        <div class="buffer-item"><strong>${t('decisionReasons')}</strong><br>${reasons}</div>`;
    }

    function renderScenarioComparisonError(data) {
      const baselineStatus = data.BaselineValidation && data.BaselineValidation.IsValid ? t('valid') : t('invalid');
      const candidateStatus = data.CandidateValidation && data.CandidateValidation.IsValid ? t('valid') : t('invalid');
      document.getElementById('scenario-comparison-output').innerHTML = `
        <div class="buffer-item buffer-red"><strong>${t('invalidScenario')}</strong><br>${data.InvalidScenario}</div>
        <div class="buffer-item"><strong>${t('message')}</strong><br>${data.Message}</div>
        <div class="buffer-item"><strong>${t('baselineValidation')}</strong><br>${baselineStatus}</div>
        <div class="buffer-item"><strong>${t('candidateValidation')}</strong><br>${candidateStatus}</div>`;
    }

    async function compareScenarios() {
      document.getElementById('workbench-error').textContent = '';
      try {
        const baseline = readMasterData();
        const candidate = readCandidateScenario();
        const response = await fetch('/planner/workbench/scenarios/compare', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ Baseline: baseline, Candidate: candidate })
        });
        const payload = await response.json();
        if (!response.ok) {
          if (payload.Data && payload.Data.InvalidScenario) {
            renderScenarioComparisonError(payload.Data);
            throw new Error(payload.Data.Message);
          }
          throw new Error(JSON.stringify(payload));
        }
        renderScenarioComparison(payload.Data);
      } catch (error) {
        document.getElementById('workbench-error').textContent = error.message;
      }
    }

    async function checkReleaseGate() {
      document.getElementById('workbench-error').textContent = '';
      try {
        const request = readMasterData();
        request.OrderID = document.getElementById('release-order-id').value;
        request.RequestedReleaseAt = document.getElementById('release-requested-at').value;
        const response = await fetch('/planner/workbench/release', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(request)
        });
        const payload = await response.json();
        renderReleaseGateDecision(payload);
        document.getElementById('release-gate-output').textContent = JSON.stringify(payload, null, 2);
      } catch (error) {
        document.getElementById('workbench-error').textContent = error.message;
      }
    }

    async function recordExecutionEvent() {
      const request = {
        OrderID: document.getElementById('execution-order-id').value,
        EventType: document.getElementById('execution-event-type').value,
        EventAt: document.getElementById('execution-event-at').value,
        TargetStartAt: document.getElementById('execution-target-start-at').value,
        ExceptionCode: document.getElementById('execution-exception-code').value || null
      };
      const response = await fetch('/shop-floor/execution/event', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(request)
      });
      const payload = await response.json();
      document.getElementById('execution-event-result').textContent = JSON.stringify(payload, null, 2);
      await loadExecutionEvents();
    }

    async function loadExecutionEvents() {
      const response = await fetch('/shop-floor/execution/events');
      const payload = await response.json();
      const summary = payload.Data.Summary;
      const exceptionCounts = Object.entries(summary.ExceptionCodeCounts)
        .map(([code, count]) => `${code}: ${count}`)
        .join(', ') || t('none');
      const exceptionCategoryCounts = Object.entries(summary.ExceptionCategoryCounts)
        .map(([category, count]) => `${exceptionCategoryLabel(category)}: ${count}`)
        .join(', ') || t('none');
      const topExceptionCategories = summary.TopExceptionCategories.length
        ? summary.TopExceptionCategories.map(item => `${item.Rank}. ${exceptionCategoryLabel(item.Category)}: ${item.Count} (${item.Percent}%) - ${localizedAction(item.RecommendedAction)}`).join('<br>')
        : t('none');
      const lateArrival = summary.LateArrivalSummary;
      document.getElementById('execution-event-summary').innerHTML = `
        <div class="buffer-item"><strong>${t('totalEvents')}</strong>: ${summary.TotalEvents}<br>
        <strong>${t('requiresReview')}</strong>: ${summary.RequiresReviewCount}<br>
        <strong>${t('reworkLoops')}</strong>: ${summary.ReworkLoopCount}<br>
        <strong>${t('lateArrivalSummary')}</strong>: ${lateArrival.LateArrivalCount} ${t('late')}, ${t('average')} ${lateArrival.AverageLateMinutes} ${t('min')}, ${t('max')} ${lateArrival.MaxLateMinutes} ${t('min')}<br>
        <strong>${t('exceptionCategories')}</strong>: ${exceptionCategoryCounts}<br>
        <strong>${t('topExceptionCategories')}</strong>:<br>${topExceptionCategories}<br>
        <strong>${t('exceptionCodes')}</strong>: ${exceptionCounts}</div>`;
      document.getElementById('exception-code-catalog').innerHTML = exceptionCodeCatalog
        .map(item => `<div class="buffer-item"><strong>${item.Code}</strong><br>${exceptionDisplayName(item)}<br>${exceptionCategoryName(item)}</div>`)
        .join('');
      document.getElementById('process-transitions').innerHTML = summary.ProcessTransitions.length
        ? summary.ProcessTransitions.map(item => `<div class="buffer-item ${item.IsReworkLoop ? 'buffer-red' : ''}"><strong>${eventLabel(item.From)}</strong> -> <strong>${eventLabel(item.To)}</strong><br>${t('count')} ${item.Count}<br>${t('average')} ${item.AverageElapsedMinutes} ${t('min')}<br>${t('review')} ${item.RequiresReviewCount}${item.IsReworkLoop ? `<br>${t('reworkLoop')}` : ''}</div>`).join('')
        : `<div>${t('noProcessTransitions')}</div>`;
      document.getElementById('execution-event-history').innerHTML = payload.Data.Events.length
        ? payload.Data.Events.map(item => `<div class="buffer-item"><strong>${item.OrderID}</strong> ${eventLabel(item.EventType)}<br>${t('status')}: ${item.Status}<br>${item.EventAt}${item.ExceptionCode ? `<br>${item.ExceptionCode}` : ''}</div>`).join('')
        : `<div>${t('noExecutionEvents')}</div>`;
    }

    document.getElementById('master-data-input').value = JSON.stringify(DEFAULT_MASTER_DATA, null, 2);
    syncCandidateScenarioFromBaseline();
    document.getElementById('solver-select').addEventListener('change', calculateWorkbench);
    document.getElementById('validate-master-data-button').addEventListener('click', validateMasterData);
    document.getElementById('calculate-button').addEventListener('click', calculateWorkbench);
    document.getElementById('copy-baseline-to-candidate-button').addEventListener('click', syncCandidateScenarioFromBaseline);
    document.getElementById('compare-scenarios-button').addEventListener('click', compareScenarios);
    document.getElementById('simio-export-button').addEventListener('click', exportSimio);
    document.getElementById('release-gate-button').addEventListener('click', checkReleaseGate);
    document.getElementById('record-execution-button').addEventListener('click', recordExecutionEvent);
    document.getElementById('execution-exception-code-select').addEventListener('change', event => {
      document.getElementById('execution-exception-code').value = event.target.value;
    });
    document.getElementById('language-select').addEventListener('change', () => {
      applyLanguage();
      populateExceptionCodeSelect();
      calculateWorkbench();
      loadExecutionEvents();
    });
    applyLanguage();
    populateExceptionCodeSelect();
    loadExceptionCodeCatalog().then(loadExecutionEvents);
    calculateWorkbench();
  </script>
</body>
</html>"""
