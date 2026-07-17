from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
from typing import Any, Mapping

from sdbr.ddsop_contracts import (
    DEFAULT_CONTRACT_ROOT,
    canonical_operating_model_fingerprint,
)
from sdbr.ddsop_runtime_planning_input import (
    build_bounded_scheduling_input_from_package,
    process_runtime_planning_input_message,
)
from sdbr.environment_paths import resolve_public_demo_package_root


ADVENTUREWORKS_ADAPTER_PROFILE_ID = (
    "ADVENTUREWORKS-BOUNDED-SCHEDULING-ADAPTER-PROFILE-V1"
)
CAPACITY_UNIT_NORMALIZATION_RULE_ID = (
    "AW-CAPACITY-UNIT-FIXTURE-ONE-UNIT-PER-RESOURCE-WINDOW"
)
MATERIAL_CONSTRAINTS_MODE = "OmittedForPublicDemo"
SETUP_CHANGEOVER_MODE = "NoSetupRulesApplied"
RUNTIME_PACKAGE_ID = "RPI-AW-SCHED-SDBR-BOUNDED-FIXTURE-001"
RESOURCE_IDS = (
    "AW-RES-10",
    "AW-RES-20",
    "AW-RES-30",
    "AW-RES-40",
    "AW-RES-45",
    "AW-RES-50",
    "AW-RES-60",
)


class AdventureWorksAdapterError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def adventureworks_adapter_output_dir() -> Path:
    return Path(
        os.environ.get(
            "SDBR_ADVENTUREWORKS_ADAPTER_OUTPUT_DIR",
            str(Path(__file__).resolve().parents[1] / "data" / "public-demo-adventureworks-adapter"),
        )
    )


def adventureworks_public_demo_package_root() -> Path:
    return resolve_public_demo_package_root()


def build_adventureworks_scheduling_adapter_status(
    *,
    package_root: Path | None = None,
    contract_root: Path | None = None,
    write_artifacts: bool = False,
    output_dir: Path | None = None,
    max_work_orders: int = 7,
) -> dict[str, Any]:
    root = package_root or adventureworks_public_demo_package_root()
    try:
        message, accepted_configuration, adapter_summary = (
            build_adventureworks_runtime_planning_input_message(
                package_root=root,
                contract_root=contract_root,
                max_work_orders=max_work_orders,
            )
        )
        processing = process_runtime_planning_input_message(
            message,
            received_at=_aware_now(),
            accepted_configurations={
                accepted_configuration["Payload"]["OperatingModelConfigurationID"]: (
                    accepted_configuration
                )
            },
            contract_root=contract_root or DEFAULT_CONTRACT_ROOT,
        )
        validation_status = (
            "Accepted"
            if processing.processing_status == "Accepted"
            and processing.package_record is not None
            else "Rejected"
        )
        bounded_summary = (
            _bounded_fixture_scheduling_summary(processing.package_record)
            if processing.package_record is not None
            else {
                "Mode": "BoundedAdapterFixtureSchedulingMode",
                "Status": "NotRun",
                "Reason": "Runtime package validation failed.",
            }
        )
        artifacts = (
            _write_adapter_artifacts(
                output_dir or adventureworks_adapter_output_dir(),
                message=message,
                validation_summary={
                    "AdapterProfileID": ADVENTUREWORKS_ADAPTER_PROFILE_ID,
                    "RuntimePlanningInputPackageID": RUNTIME_PACKAGE_ID,
                    "ValidationStatus": validation_status,
                    "ProcessingStatus": processing.processing_status,
                    "Errors": processing.errors,
                    "AdapterSummary": adapter_summary,
                    "BoundedFixtureScheduling": bounded_summary,
                    "NonClaims": _non_claims(),
                },
                bounded_summary=bounded_summary,
            )
            if write_artifacts
            else {}
        )
        return {
            "AdapterProfileID": ADVENTUREWORKS_ADAPTER_PROFILE_ID,
            "Mode": "BoundedAdapterFixtureSchedulingMode",
            "PackageRoot": str(root),
            "Status": validation_status,
            "ProcessingStatus": processing.processing_status,
            "RuntimePlanningInputPackageID": RUNTIME_PACKAGE_ID,
            "GeneratedPackagePath": artifacts.get("RuntimePackagePath"),
            "ValidationSummaryPath": artifacts.get("ValidationSummaryPath"),
            "BoundedSchedulingSummaryPath": artifacts.get("BoundedSchedulingSummaryPath"),
            "Declarations": {
                "CapacityUnitNormalizationRuleID": CAPACITY_UNIT_NORMALIZATION_RULE_ID,
                "MaterialConstraintsMode": MATERIAL_CONSTRAINTS_MODE,
                "SetupChangeoverMode": SETUP_CHANGEOVER_MODE,
                "MappingConfidence": "PublicDemoOnly",
                "ScenarioLabel": "ControlledContractGoldenLoopDemo",
            },
            "CalendarMappings": adapter_summary["CalendarMappings"],
            "RoutingPathCoverage": adapter_summary["RoutingPathCoverage"],
            "OperationResourceCoverage": adapter_summary["OperationResourceCoverage"],
            "DurationNormalization": adapter_summary["DurationNormalization"],
            "CapacityUnitNormalization": adapter_summary["CapacityUnitNormalization"],
            "MaterialConstraints": adapter_summary["MaterialConstraints"],
            "SetupChangeover": adapter_summary["SetupChangeover"],
            "StorageOnlyLocationGuard": adapter_summary["StorageOnlyLocationGuard"],
            "ValidationErrors": processing.errors,
            "BoundedFixtureScheduling": bounded_summary,
            "FormalSolverGate": {
                "CP-SAT/OR-Tools": "Gated",
                "Reason": (
                    "Public demo rows remain bounded fixture adapter inputs until a "
                    "later gate accepts formal executable scheduling entry."
                ),
            },
            "NonClaims": _non_claims(),
        }
    except AdventureWorksAdapterError as error:
        return {
            "AdapterProfileID": ADVENTUREWORKS_ADAPTER_PROFILE_ID,
            "Mode": "BoundedAdapterFixtureSchedulingMode",
            "PackageRoot": str(root),
            "Status": "Rejected",
            "ProcessingStatus": "AdapterRejected",
            "ValidationErrors": [{"Code": error.code, "Message": error.message}],
            "FormalSolverGate": {"CP-SAT/OR-Tools": "Gated"},
            "NonClaims": _non_claims(),
        }


def build_adventureworks_runtime_planning_input_message(
    *,
    package_root: Path | None = None,
    contract_root: Path | None = None,
    max_work_orders: int = 7,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    root = package_root or adventureworks_public_demo_package_root()
    profile = _adapter_profile(contract_root)
    _assert_profile_boundary(profile)
    work_orders = _read_json(root / "work-orders.json")
    routings = _read_json(root / "routings.json")
    capacities = _read_json(root / "capacities.json")
    locations = _read_json(root / "locations.json")
    if not isinstance(work_orders, list) or not isinstance(routings, list):
        raise AdventureWorksAdapterError(
            "PACKAGE_FILE_INVALID",
            "AdventureWorks work-orders.json and routings.json must be arrays.",
        )

    selected = _select_work_orders_for_profile(profile, work_orders, routings, max_work_orders)
    executable, adapter_summary = _build_executable_scheduling_inputs(
        profile=profile,
        selected=selected,
        capacities=capacities if isinstance(capacities, list) else [],
        locations=locations if isinstance(locations, list) else [],
    )
    accepted_configuration = _accepted_demo_configuration()
    frozen = _frozen_configuration_from(accepted_configuration)
    payload = {
        "PackageIdentity": {
            "RuntimePlanningInputPackageID": RUNTIME_PACKAGE_ID,
            "PackageVersion": "0.1.0-sdbr-adventureworks-fixture",
            "PackageStatus": "AcceptedForBoundedPlanning",
            "ExecutionMode": "BoundedProductionScheduling",
            "MappingConfidence": "PublicDemoOnly",
            "ScenarioLabel": "ControlledContractGoldenLoopDemo",
        },
        "FrozenDdsopConfiguration": frozen,
        "ParameterAuthorityEvidence": _parameter_authority_evidence(),
        "ExecutableSchedulingInputs": executable,
        "ConsumerRules": _consumer_rules(),
        "OutputExpectations": _output_expectations(),
    }
    message = {
        "ContractID": "DDSOP-RUNTIME-PLANNING-INPUT-V1",
        "ContractVersion": "0.1.0-draft",
        "MessageID": "SDBR-MSG-AW-SCHED-RPI-001",
        "MessageType": "RuntimePlanningInputPackagePublished",
        "SourceSystem": "SDBR",
        "TargetSystem": ["SDBR"],
        "IdempotencyKey": "SDBR:SDBR-MSG-AW-SCHED-RPI-001",
        "OccurredAt": "2026-06-30T18:30:00+08:00",
        "Payload": payload,
    }
    return message, accepted_configuration, adapter_summary


def _adapter_profile(contract_root: Path | None) -> dict[str, Any]:
    root = contract_root or DEFAULT_CONTRACT_ROOT
    path = (
        root
        / "contracts"
        / "ddsop-runtime-planning-input-v1"
        / "examples"
        / "adventureworks-bounded-scheduling-adapter-profile.json"
    )
    return _read_json(path)


def _assert_profile_boundary(profile: Mapping[str, Any]) -> None:
    if profile.get("ProfileID") != ADVENTUREWORKS_ADAPTER_PROFILE_ID:
        raise AdventureWorksAdapterError(
            "ADAPTER_PROFILE_MISMATCH",
            "AdventureWorks adapter profile ID does not match the reviewed profile.",
        )
    if profile.get("MappingConfidence") != "PublicDemoOnly":
        raise AdventureWorksAdapterError(
            "CONFIDENCE_LABEL_CONFLICT",
            "AdventureWorks adapter profile must remain PublicDemoOnly.",
        )
    if (profile.get("CalendarAuthority") or {}).get("Owner") != "SDBR":
        raise AdventureWorksAdapterError(
            "OWNERSHIP_VIOLATION",
            "AdventureWorks adapter profile must leave executable calendars under SDBR ownership.",
        )


def _select_work_orders_for_profile(
    profile: Mapping[str, Any],
    work_orders: list[Mapping[str, Any]],
    routings: list[Mapping[str, Any]],
    max_work_orders: int,
) -> list[dict[str, Any]]:
    order_by_id = {int(item["WorkOrderID"]): item for item in work_orders}
    routing_by_order: dict[int, list[Mapping[str, Any]]] = defaultdict(list)
    for row in routings:
        routing_by_order[int(row["WorkOrderID"])].append(row)

    selected: list[dict[str, Any]] = []
    used_orders: set[int] = set()
    for signature in profile.get("RoutingPathSignatures", []):
        target_pairs = [
            (int(item["SourceOperationSequence"]), int(item["SourceLocationID"]))
            for item in signature.get("Operations", [])
        ]
        match_id = None
        for work_order_id, rows in routing_by_order.items():
            if work_order_id in used_orders or work_order_id not in order_by_id:
                continue
            pairs = [
                (int(row["SourceOperationSequence"]), int(row["SourceLocationID"]))
                for row in sorted(rows, key=lambda item: int(item["SourceOperationSequence"]))
            ]
            if pairs == target_pairs:
                match_id = work_order_id
                break
        if match_id is None:
            raise AdventureWorksAdapterError(
                "REFERENCE_NOT_FOUND",
                f"No work order matches routing path signature {signature.get('RoutingPathSignatureID')}.",
            )
        used_orders.add(match_id)
        selected.append(
            {
                "Signature": signature,
                "WorkOrder": order_by_id[match_id],
                "RoutingRows": sorted(
                    routing_by_order[match_id],
                    key=lambda item: int(item["SourceOperationSequence"]),
                ),
            }
        )
        if len(selected) >= max_work_orders:
            break
    return selected


def _build_executable_scheduling_inputs(
    *,
    profile: Mapping[str, Any],
    selected: list[Mapping[str, Any]],
    capacities: list[Mapping[str, Any]],
    locations: list[Mapping[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any]]:
    resource_by_location = {
        int(item["SourceLocationID"]): str(item["ResourceID"])
        for item in profile.get("OperationResources", [])
    }
    allowed_locations = set(resource_by_location)
    capacity_by_location = {
        int(item["SourceLocationID"]): item for item in capacities if item.get("SourceLocationID") is not None
    }
    location_role_by_id = {
        int(item["SourceLocationID"]): str(item.get("LocationProxyRole", ""))
        for item in locations
        if item.get("SourceLocationID") is not None
    }
    work_orders: list[dict[str, Any]] = []
    routings: list[dict[str, Any]] = []
    operations: list[dict[str, Any]] = []
    duration_sources = {"ActualResourceHrs": 0, "ScheduledDateDelta": 0}
    demo_start = datetime(2026, 7, 1, 8, 0, tzinfo=timezone(timedelta(hours=8)))
    for index, item in enumerate(selected, start=1):
        source_order = item["WorkOrder"]
        signature = item["Signature"]
        source_order_id = int(source_order["WorkOrderID"])
        product_id = f"AW-PRODUCT-{source_order['SourceProductID']}"
        routing_id = f"{signature['RoutingPathSignatureID']}-WO-{source_order_id}"
        operation_ids: list[str] = []
        work_order_id = f"AW-WO-{source_order_id}"
        work_orders.append(
            {
                "WorkOrderID": work_order_id,
                "ProductID": product_id,
                "RoutingID": routing_id,
                "Quantity": float(source_order["OrderQty"]),
                "UnitOfMeasure": "EA",
                "EarliestReleaseAt": _iso(demo_start + timedelta(days=index - 1)),
                "DueAt": _iso(demo_start + timedelta(days=index + 5)),
                "Priority": index,
                "EvidenceRefs": [
                    _evidence(
                        evidence_id=str(source_order["DemoWorkOrderID"]),
                        source_record_id=_source_record_id(source_order),
                    )
                ],
            }
        )
        for row in item["RoutingRows"]:
            location_id = int(row["SourceLocationID"])
            if location_id not in allowed_locations:
                raise AdventureWorksAdapterError(
                    "STORAGE_ONLY_LOCATION_NOT_EXECUTABLE",
                    f"Location {location_id} is not an accepted executable operation resource.",
                )
            operation_id = (
                f"AW-OP-{source_order_id}-"
                f"{int(row['SourceOperationSequence']):03d}-{location_id}"
            )
            duration, source = _normalized_duration_minutes(row)
            duration_sources[source] += 1
            operation_ids.append(operation_id)
            operations.append(
                {
                    "OperationID": operation_id,
                    "Sequence": int(row["SourceOperationSequence"]),
                    "ResourceID": resource_by_location[location_id],
                    "AlternateResourceIDs": [],
                    "DurationMinutes": duration,
                    "EvidenceRefs": [
                        _evidence(
                            evidence_id=str(row["DemoRoutingOperationID"]),
                            source_record_id=(
                                f"{_source_record_id(row)};"
                                f"DurationRule={source}"
                            ),
                        )
                    ],
                }
            )
        routings.append(
            {
                "RoutingID": routing_id,
                "ProductID": product_id,
                "OperationIDs": operation_ids,
                "EvidenceRefs": [
                    _evidence(
                        evidence_id=str(signature["RoutingPathSignatureID"]),
                        source_record_id=(
                            "RoutingPathSignature="
                            + "-".join(
                                str(op["SourceLocationID"])
                                for op in signature.get("Operations", [])
                            )
                        ),
                    )
                ],
            }
        )

    resource_calendars = [
        _resource_calendar(
            source_location_id=location_id,
            resource_id=resource_by_location[location_id],
            capacity=capacity_by_location.get(location_id, {}),
        )
        for location_id in sorted(allowed_locations)
    ]
    executable = {
        "MasterDataVersionID": "AW-SCHED-PUBLIC-DEMO-MD-SDBR-0.1",
        "AdapterProfileID": ADVENTUREWORKS_ADAPTER_PROFILE_ID,
        "CapacityUnitNormalizationRuleID": CAPACITY_UNIT_NORMALIZATION_RULE_ID,
        "MaterialConstraintsMode": MATERIAL_CONSTRAINTS_MODE,
        "SetupChangeoverMode": SETUP_CHANGEOVER_MODE,
        "WorkOrders": work_orders,
        "Routings": routings,
        "Operations": operations,
        "ResourceCalendars": resource_calendars,
        "MaterialConstraints": [],
        "SetupChangeoverRules": [
            _evidence(
                evidence_id="AW-NO-SETUP-RULES-APPLIED",
                source_authority="SDBR public demo fixture policy",
                source_record_id="SetupChangeoverMode=NoSetupRulesApplied",
            )
        ],
    }
    summary = {
        "RoutingPathCoverage": {
            "RecognizedPathCount": len(profile.get("RoutingPathSignatures", [])),
            "SelectedFixtureWorkOrderCount": len(work_orders),
            "SelectedRoutingIDs": [row["RoutingID"] for row in routings],
        },
        "OperationResourceCoverage": {
            "RequiredResourceIDs": list(RESOURCE_IDS),
            "GeneratedOperationCount": len(operations),
            "OperationResourceIDs": sorted(
                {str(row["ResourceID"]) for row in operations}
            ),
        },
        "CalendarMappings": [
            {
                "ResourceID": row["ResourceID"],
                "CalendarID": row["CalendarID"],
                "CapacityWindowCount": len(row["CapacityWindows"]),
                "Authority": "SDBR",
                "MappingStatus": "Explicit",
            }
            for row in resource_calendars
        ],
        "DurationNormalization": {
            "Rule": "Prefer ActualResourceHrs * 60; fallback to ScheduledEndDate - ScheduledStartDate.",
            "ActualResourceHrsRows": duration_sources["ActualResourceHrs"],
            "ScheduledDateDeltaRows": duration_sources["ScheduledDateDelta"],
            "RejectedNonPositiveRows": 0,
        },
        "CapacityUnitNormalization": {
            "RuleID": CAPACITY_UNIT_NORMALIZATION_RULE_ID,
            "CapacityUnits": 1,
            "AvailabilityUse": "Audit evidence only; not production capacity authority.",
        },
        "MaterialConstraints": {
            "Mode": MATERIAL_CONSTRAINTS_MODE,
            "MaterialFeasibleProductionClaim": False,
        },
        "SetupChangeover": {
            "Mode": SETUP_CHANGEOVER_MODE,
            "SilentInferenceAllowed": False,
        },
        "StorageOnlyLocationGuard": {
            "AllowedExecutableLocationIDs": sorted(allowed_locations),
            "StorageOnlyLocationsPromoted": [],
            "Status": "Passed",
            "ObservedLocationRoles": {
                str(location_id): location_role_by_id.get(location_id)
                for location_id in sorted(allowed_locations)
            },
        },
    }
    return executable, summary


def _resource_calendar(
    *,
    source_location_id: int,
    resource_id: str,
    capacity: Mapping[str, Any],
) -> dict[str, Any]:
    start = datetime(2026, 7, 1, 8, 0, tzinfo=timezone(timedelta(hours=8)))
    end = datetime(2026, 7, 8, 17, 0, tzinfo=timezone(timedelta(hours=8)))
    return {
        "ResourceID": resource_id,
        "CalendarID": f"AW-CAL-RES-{source_location_id}-SDBR-DEMO-8X5",
        "CapacityWindows": [
            {
                "StartAt": _iso(start),
                "EndAt": _iso(end),
                "CapacityUnits": 1,
            }
        ],
        "EvidenceRefs": [
            _evidence(
                evidence_id=str(
                    capacity.get("DemoCapacityID")
                    or f"AW-CAPACITY-{source_location_id}"
                ),
                source_authority=(
                    "SDBR public demo calendar fixture; AdventureWorks "
                    "Availability retained as public-demo proxy evidence only"
                ),
                source_record_id=(
                    _source_record_id(capacity)
                    or f"Production.Location;LocationID={source_location_id};WorkingWindow=DEMO-8x5"
                ),
            )
        ],
    }


def _normalized_duration_minutes(row: Mapping[str, Any]) -> tuple[int, str]:
    actual_hours = _to_float(row.get("ActualResourceHrs"))
    if actual_hours and actual_hours > 0:
        return max(1, round(actual_hours * 60)), "ActualResourceHrs"
    start = _parse_source_datetime(row.get("ScheduledStartDate"))
    end = _parse_source_datetime(row.get("ScheduledEndDate"))
    if start is not None and end is not None and end > start:
        minutes = int((end - start).total_seconds() // 60)
        if minutes > 0:
            return minutes, "ScheduledDateDelta"
    raise AdventureWorksAdapterError(
        "INVALID_NUMERIC_VALUE",
        f"Routing operation {row.get('DemoRoutingOperationID')} has no positive duration.",
    )


def _accepted_demo_configuration() -> dict[str, Any]:
    payload = {
        "OperatingModelConfigurationID": "DDSOP-OMC-AW-SCHED-PUBLIC-DEMO-V1",
        "ConfigurationVersion": "1.0.0",
        "Status": "Approved",
        "EffectiveFrom": "2026-06-30T00:00:00+08:00",
        "EffectiveTo": None,
        "TimeZone": "Asia/Shanghai",
        "SchedulingConfiguration": {
            "SchedulingConfigurationID": "DDSOP-SCHED-AW-PUBLIC-DEMO-V1",
            "AdapterProfileID": ADVENTUREWORKS_ADAPTER_PROFILE_ID,
            "ControlPoints": [
                {"ControlPointID": "AW-CP-FINAL-ASSEMBLY", "ResourceID": "AW-RES-60"}
            ],
            "ReleasePolicy": "PublicDemoOnly fixture release policy",
            "PriorityPolicy": "PublicDemoOnly fixture priority policy",
        },
        "DDMRPConfiguration": {
            "DDMRPConfigurationID": "DDSOP-DDMRP-AW-PUBLIC-DEMO-V1",
            "DecouplingPoints": [],
            "StockBufferProfiles": [],
        },
    }
    payload["Fingerprint"] = canonical_operating_model_fingerprint(payload)
    return {"Payload": payload}


def _frozen_configuration_from(record: Mapping[str, Any]) -> dict[str, Any]:
    payload = record["Payload"]
    return {
        "OperatingModelConfigurationID": payload["OperatingModelConfigurationID"],
        "OperatingModelFingerprint": payload["Fingerprint"],
        "ConfigurationVersion": payload["ConfigurationVersion"],
        "SourceConfigurationContractID": "DDSOP-CONFIG-INBOUND-V1",
        "ConfigStatus": payload["Status"],
        "EffectiveFrom": payload["EffectiveFrom"],
        "EffectiveTo": payload["EffectiveTo"],
        "TimeZone": payload["TimeZone"],
        "SchedulingConfigurationID": payload["SchedulingConfiguration"][
            "SchedulingConfigurationID"
        ],
        "DDMRPConfigurationID": payload["DDMRPConfiguration"]["DDMRPConfigurationID"],
    }


def _parameter_authority_evidence() -> dict[str, Any]:
    refs = []
    for field_group, source_authority, status in [
        ("ControlPoint", "DDAE public demo scheduling governance", "ManualGoverned"),
        ("TimeBuffer", "DDAE public demo scheduling governance", "ManualGoverned"),
        ("ResourcePolicy", "DDAE public demo scheduling governance", "ManualGoverned"),
        ("CalendarPolicy", "SDBR public demo calendar fixture authority", "FixtureSeeded"),
        ("ReleasePolicy", "DDAE public demo scheduling governance", "ManualGoverned"),
    ]:
        refs.append(
            {
                "FieldGroup": field_group,
                "EvidenceID": f"AW-SCHED-{field_group.upper()}-PUBLIC-DEMO",
                "SourceAuthority": source_authority,
                "CalculationStatus": status,
                "ProductionAuthorityStatus": "PublicDemoOnly",
                "Applicability": "Applicable",
                "NotApplicableReason": None,
            }
        )
    return {
        "DDMRPFormulaVersionID": "DDMRP-NOT-USED-BOUNDED-SCHED-PUBLIC-DEMO",
        "SchedulingRuleVersionID": "SCHED-RULE-AW-BOUNDED-SCHED-SDBR-0.1",
        "ApprovalEvidenceID": "APPROVAL-AW-SCHED-SDBR-FIXTURE-20260630",
        "ApprovedBy": "SDBR Agent scoped implementation",
        "ApprovedAt": "2026-06-30T18:20:00+08:00",
        "EffectivePolicyID": "EFFECTIVITY-AW-SCHED-SDBR-PUBLIC-DEMO-20260630",
        "ParameterEvidenceRefs": refs,
    }


def _consumer_rules() -> dict[str, list[str]]:
    return {
        "ReadOnlyFrozenInputs": [
            "OPERATING_MODEL_CONFIGURATION_ID",
            "OPERATING_MODEL_FINGERPRINT",
            "SCHEDULING_CONFIGURATION_ID",
            "DDMRP_CONFIGURATION_ID",
            "DDSOP_DDMRP_MASTER_SETTINGS",
            "DDSOP_SCHEDULING_POLICY_SETTINGS",
            "DDMRP_BUFFER_TOPS",
            "DDMRP_DLT_MOQ_ORDER_CYCLE",
            "SCHEDULING_CONTROL_POINTS_TIME_BUFFERS",
        ],
        "SDBRDerivedRuntimeSignals": [
            "NET_FLOW_POSITION",
            "BUFFER_STATUS",
            "QUALIFIED_SPIKE_DEMAND",
            "MATERIAL_AVAILABILITY_STATUS",
            "RELEASE_AUTHORIZATION_STATE",
            "SCHEDULE_FEASIBILITY",
            "INFEASIBILITY_CAUSES",
            "DISPATCH_RECOMMENDATION",
        ],
        "ForbiddenMutations": [
            "MUTATE_OPERATING_MODEL_CONFIGURATION_ID",
            "MUTATE_OPERATING_MODEL_FINGERPRINT",
            "RECALCULATE_DDAE_BUFFER_TOPS",
            "MUTATE_DDAE_DLT_MOQ_ORDER_CYCLE",
            "MUTATE_DDAE_SCHEDULING_POLICY",
            "PROMOTE_RUNTIME_FEEDBACK_TO_APPROVED_MASTER_SETTING",
        ],
    }


def _output_expectations() -> dict[str, Any]:
    return {
        "FeedbackContractID": "DDSOP-FEEDBACK-OUTBOUND-V1",
        "PlanningRunFeedbackRequired": True,
        "VarianceAnalysisFeedbackRequired": True,
        "RuntimePlanningInputPackageID": RUNTIME_PACKAGE_ID,
        "FeedbackCorrelationMode": "DeliveryLedger",
        "DeliveryLedgerCorrelationID": "LEDGER-CORR-AW-SCHED-SDBR-RPI-001",
        "ReplayPolicy": "Same IdempotencyKey returns Duplicate; corrected package requires new MessageID.",
        "DeadLetterPolicy": "Schema, authority, resource-calendar, duration, material-mode, setup-mode, or ownership failure must be rejected without bypass.",
    }


def _bounded_fixture_scheduling_summary(
    package_record: Mapping[str, Any] | None,
) -> dict[str, Any]:
    if package_record is None:
        return {"Mode": "BoundedAdapterFixtureSchedulingMode", "Status": "NotRun"}
    bounded = build_bounded_scheduling_input_from_package(package_record)
    return {
        "Mode": "BoundedAdapterFixtureSchedulingMode",
        "Status": "ValidatedInputOnly",
        "RuntimePlanningInputPackageID": bounded["RuntimePlanningInputPackageID"],
        "WorkOrderCount": len(bounded["WorkOrders"]),
        "RoutingCount": len(bounded["Routings"]),
        "OperationCount": len(bounded["Operations"]),
        "ResourceCalendarCount": len(bounded["ResourceCalendars"]),
        "FormalSolverEntry": "Gated",
        "Message": (
            "Generated rows are validated as bounded fixture scheduling input; "
            "formal CP-SAT / OR-Tools production entry remains disabled."
        ),
    }


def _write_adapter_artifacts(
    output_dir: Path,
    *,
    message: Mapping[str, Any],
    validation_summary: Mapping[str, Any],
    bounded_summary: Mapping[str, Any],
) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    package_path = output_dir / "adventureworks-bounded-scheduling-runtime-package.json"
    validation_path = output_dir / "adventureworks-bounded-scheduling-validation-summary.json"
    bounded_path = output_dir / "adventureworks-bounded-scheduling-summary.json"
    _write_json(package_path, message)
    _write_json(validation_path, validation_summary)
    _write_json(bounded_path, bounded_summary)
    return {
        "RuntimePackagePath": str(package_path),
        "ValidationSummaryPath": str(validation_path),
        "BoundedSchedulingSummaryPath": str(bounded_path),
    }


def _evidence(
    *,
    evidence_id: str,
    source_record_id: str,
    source_authority: str = "AdventureWorks public demo fixture",
) -> dict[str, str]:
    return {
        "EvidenceID": evidence_id,
        "SourceAuthority": source_authority,
        "SourceRecordID": source_record_id,
        "SourceObservedAt": "2026-06-30T18:30:00+08:00",
    }


def _source_record_id(row: Mapping[str, Any]) -> str:
    identity = row.get("SourceRowIdentity")
    if isinstance(identity, Mapping):
        table = identity.get("SourceTable")
        key = identity.get("SourceKey")
        if table and key:
            return f"{table};{key}"
    return str(row.get("SourceRecordID") or "")


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _parse_source_datetime(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value))
    except ValueError:
        return None


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _iso(value: datetime) -> str:
    return value.isoformat()


def _aware_now() -> datetime:
    return datetime.now(timezone.utc)


def _non_claims() -> list[str]:
    return [
        "Not ProductionValidated",
        "Not Business Golden Loop readiness",
        "Not production authority",
        "BoundedAdapterFixtureSchedulingMode only",
        "Formal CP-SAT / OR-Tools production entry remains gated",
        "SQL Server / SQL Express is not a runtime dependency",
    ]
