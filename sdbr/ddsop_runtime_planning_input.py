from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime
import json
from pathlib import Path
from typing import Any, Mapping

from jsonschema import Draft202012Validator

from sdbr.ddmrp import DecouplingPoint, DemandSignal, OpenSupply, evaluate_ddmrp_net_flow
from sdbr.ddsop_contracts import DEFAULT_CONTRACT_ROOT, canonical_operating_model_fingerprint
from sdbr.planner_view import InventoryBufferPolicy


RUNTIME_PLANNING_INPUT_CONTRACT_ID = "DDSOP-RUNTIME-PLANNING-INPUT-V1"
RUNTIME_PLANNING_INPUT_CONTRACT_VERSION = "0.1.0-draft"

DDMRP_REQUIRED_EVIDENCE = {
    "ADU",
    "DLT",
    "VariabilityFactor",
    "MOQ",
    "OrderCycle",
    "BufferZones",
    "DecouplingPoint",
    "BufferProfile",
    "UOM",
    "AdjustmentFactor",
}
BUFFER_ZONE_CALCULATION_INPUTS = {
    "ADU",
    "DLT",
    "VariabilityFactor",
    "MOQ",
    "OrderCycle",
}
SCHEDULING_REQUIRED_EVIDENCE = {
    "ControlPoint",
    "TimeBuffer",
    "ResourcePolicy",
    "CalendarPolicy",
    "ReleasePolicy",
}

REQUIRED_READ_ONLY_TOKENS = {
    "OPERATING_MODEL_CONFIGURATION_ID",
    "OPERATING_MODEL_FINGERPRINT",
    "SCHEDULING_CONFIGURATION_ID",
    "DDMRP_CONFIGURATION_ID",
    "DDSOP_DDMRP_MASTER_SETTINGS",
    "DDSOP_SCHEDULING_POLICY_SETTINGS",
    "DDMRP_BUFFER_TOPS",
    "DDMRP_DLT_MOQ_ORDER_CYCLE",
    "SCHEDULING_CONTROL_POINTS_TIME_BUFFERS",
}
REQUIRED_DERIVED_SIGNAL_TOKENS = {
    "NET_FLOW_POSITION",
    "BUFFER_STATUS",
    "QUALIFIED_SPIKE_DEMAND",
    "SCHEDULE_FEASIBILITY",
}
REQUIRED_FORBIDDEN_MUTATION_TOKENS = {
    "RECALCULATE_DDAE_BUFFER_TOPS",
    "MUTATE_DDAE_DLT_MOQ_ORDER_CYCLE",
    "MUTATE_DDAE_SCHEDULING_POLICY",
    "PROMOTE_RUNTIME_FEEDBACK_TO_APPROVED_MASTER_SETTING",
}


@dataclass(frozen=True)
class RuntimePlanningInputProcessingResult:
    processing_status: str
    package_record: dict[str, Any] | None
    inbound_message_record: dict[str, Any]
    errors: list[dict[str, Any]]


class DdmrpRuntimeAuthorityError(ValueError):
    status = "DdmrpRuntimeAuthorityError"

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def runtime_planning_input_schema(
    contract_root: Path | None = None,
) -> dict[str, Any]:
    root = contract_root or DEFAULT_CONTRACT_ROOT
    path = (
        root
        / "contracts"
        / "ddsop-runtime-planning-input-v1"
        / "schema"
        / "ddsop-runtime-planning-input-v1.schema.json"
    )
    return json.loads(path.read_text(encoding="utf-8-sig"))


def process_runtime_planning_input_message(
    message: Mapping[str, Any],
    *,
    received_at: datetime,
    existing_idempotency_keys: set[str] | None = None,
    accepted_configurations: Mapping[str, Mapping[str, Any]] | None = None,
    contract_root: Path | None = None,
) -> RuntimePlanningInputProcessingResult:
    normalized = deepcopy(dict(message))
    idempotency_key = str(normalized.get("IdempotencyKey", ""))
    message_id = str(normalized.get("MessageID", ""))
    if idempotency_key and idempotency_key in (existing_idempotency_keys or set()):
        record = {
            "Message": normalized,
            "ReceivedAt": received_at.isoformat(),
            "ProcessingStatus": "Duplicate",
            "IdempotencyKey": idempotency_key,
            "Errors": [],
        }
        return RuntimePlanningInputProcessingResult(
            processing_status="Duplicate",
            package_record=None,
            inbound_message_record=record,
            errors=[],
        )

    errors: list[dict[str, Any]] = []
    schema_errors = sorted(
        Draft202012Validator(
            runtime_planning_input_schema(contract_root)
        ).iter_errors(normalized),
        key=lambda item: list(item.path),
    )
    if schema_errors:
        errors.extend(_schema_error(error) for error in schema_errors)
        return _result(
            status="Rejected",
            message=normalized,
            received_at=received_at,
            errors=_dedupe_errors(errors),
            package_record=None,
        )

    payload = dict(normalized["Payload"])
    package_identity = dict(payload["PackageIdentity"])
    frozen = dict(payload["FrozenDdsopConfiguration"])
    _append_semantic_errors(payload, errors)
    _append_configuration_reference_errors(
        frozen,
        errors,
        accepted_configurations=accepted_configurations or {},
    )

    status = "Accepted" if not errors else "Rejected"
    package_record: dict[str, Any] | None = None
    if not errors:
        package_record = {
            "RuntimePlanningInputPackageID": package_identity[
                "RuntimePlanningInputPackageID"
            ],
            "PackageVersion": package_identity["PackageVersion"],
            "PackageStatus": package_identity["PackageStatus"],
            "ExecutionMode": package_identity["ExecutionMode"],
            "MappingConfidence": package_identity["MappingConfidence"],
            "ScenarioLabel": package_identity["ScenarioLabel"],
            "MessageID": message_id,
            "IdempotencyKey": idempotency_key,
            "ReceivedAt": received_at.isoformat(),
            "ProcessingStatus": status,
            "UsableForPlanningRun": (
                package_identity["PackageStatus"] == "AcceptedForBoundedPlanning"
            ),
            "OperatingModelConfigurationID": frozen[
                "OperatingModelConfigurationID"
            ],
            "OperatingModelFingerprint": frozen["OperatingModelFingerprint"],
            "SchedulingConfigurationID": frozen["SchedulingConfigurationID"],
            "DDMRPConfigurationID": frozen["DDMRPConfigurationID"],
            "DeliveryLedgerCorrelationID": payload["OutputExpectations"][
                "DeliveryLedgerCorrelationID"
            ],
            "Payload": payload,
        }
    return _result(
        status=status,
        message=normalized,
        received_at=received_at,
        errors=_dedupe_errors(errors),
        package_record=package_record,
    )


def ensure_package_can_create_planning_run(
    package_record: Mapping[str, Any],
) -> list[dict[str, Any]]:
    if package_record.get("PackageStatus") != "AcceptedForBoundedPlanning":
        return [
            _error(
                "INVALID_STATE_TRANSITION",
                "Only AcceptedForBoundedPlanning runtime packages may create new Planning Runs.",
                "Payload.PackageIdentity.PackageStatus",
            )
        ]
    if not package_record.get("UsableForPlanningRun"):
        return [
            _error(
                "INVALID_STATE_TRANSITION",
                "Runtime package is not marked usable for Planning Run creation.",
                "UsableForPlanningRun",
            )
        ]
    return []


def freeze_runtime_package_into_planning_run(
    planning_run: Mapping[str, Any],
    package_record: Mapping[str, Any],
) -> dict[str, Any]:
    errors = ensure_package_can_create_planning_run(package_record)
    if errors:
        raise ValueError(errors[0]["Message"])
    result = deepcopy(dict(planning_run))
    result.update(
        {
            "RuntimePlanningInputPackageID": package_record[
                "RuntimePlanningInputPackageID"
            ],
            "RuntimePlanningInputPackageVersion": package_record["PackageVersion"],
            "RuntimePlanningInputPackageStatus": package_record["PackageStatus"],
            "RuntimePlanningInputPackageIdempotencyKey": package_record[
                "IdempotencyKey"
            ],
            "RuntimePlanningInputPackageMessageID": package_record["MessageID"],
            "RuntimePackageDeliveryLedgerCorrelationID": package_record[
                "DeliveryLedgerCorrelationID"
            ],
            "OperatingModelConfigurationID": package_record[
                "OperatingModelConfigurationID"
            ],
            "OperatingModelFingerprint": package_record[
                "OperatingModelFingerprint"
            ],
            "SchedulingConfigurationID": package_record["SchedulingConfigurationID"],
            "DDMRPConfigurationID": package_record["DDMRPConfigurationID"],
            "ContractPath": "DDSOP-RUNTIME-PLANNING-INPUT-V1",
            "LegacyPlanningRunPath": False,
        }
    )
    return result


def record_runtime_planning_input_processing_result(
    store: Any,
    result: RuntimePlanningInputProcessingResult,
) -> None:
    store.ddsop_runtime_planning_input_messages.append(result.inbound_message_record)
    if result.package_record is not None:
        package_id = str(result.package_record["RuntimePlanningInputPackageID"])
        store.ddsop_runtime_planning_input_packages[package_id] = result.package_record


def record_runtime_feedback_correlations(
    store: Any,
    correlation_records: list[Mapping[str, Any]],
) -> None:
    store.ddsop_runtime_feedback_correlations.extend(
        deepcopy(dict(record)) for record in correlation_records
    )


def evaluate_ddmrp_runtime_signals_from_package(
    package_record: Mapping[str, Any],
    operating_model_configuration: Mapping[str, Any],
    *,
    evaluated_at: datetime,
) -> dict[str, Any]:
    payload = _payload(package_record)
    ddmrp_config = _operating_payload(operating_model_configuration)[
        "DDMRPConfiguration"
    ]
    runtime = payload["RuntimeEvidenceSnapshot"]
    if any(
        item.get("SpikeQualificationStatus") == "RequiresSDBRQualification"
        and item.get("SpikeQualificationMode") == "CalculatedBySDBR"
        for item in runtime.get("DemandSignals", [])
    ):
        raise DdmrpRuntimeAuthorityError(
            "SPIKE_QUALIFICATION_INPUT_INSUFFICIENT",
            "Accepted spike threshold authority is required for SDBR qualification.",
        )
    buffer_by_id = {
        str(item["BufferProfileID"]): item
        for item in ddmrp_config.get("StockBufferProfiles", [])
    }
    inventory_by_key = {
        (str(item["ItemID"]), str(item["LocationID"])): item
        for item in runtime.get("InventoryPositions", [])
    }
    _validate_ddmrp_runtime_uom_references(
        ddmrp_config=ddmrp_config,
        runtime=runtime,
        buffer_by_id=buffer_by_id,
        inventory_by_key=inventory_by_key,
    )
    decoupling_points: list[DecouplingPoint] = []
    buffers: list[InventoryBufferPolicy] = []
    for point in ddmrp_config.get("DecouplingPoints", []):
        key = (str(point["ItemID"]), str(point["LocationID"]))
        profile = buffer_by_id.get(str(point["BufferProfileID"]))
        inventory = inventory_by_key.get(key)
        if profile is None or inventory is None:
            continue
        top_red = float(profile["TopOfRed"])
        top_yellow = float(profile["TopOfYellow"])
        top_green = float(profile["TopOfGreen"])
        authority_available_qty = float(inventory["AvailableQty"])
        decoupling_points.append(
            DecouplingPoint(
                item_id=key[0],
                location_id=key[1],
                buffer_profile_id=str(point["BufferProfileID"]),
                dlt_minutes=int(point["DLTMinutes"]),
                order_multiple_qty=float(point.get("OrderMultipleQty", 0.0)),
                minimum_order_qty=float(point.get("MinimumOrderQty", 0.0)),
                status="Active",
            )
        )
        buffers.append(
            InventoryBufferPolicy(
                item_id=key[0],
                location_id=key[1],
                on_hand_qty=authority_available_qty,
                red_zone_qty=top_red,
                yellow_zone_qty=top_yellow - top_red,
                green_zone_qty=top_green - top_yellow,
            )
        )
    demand_signals = [
        DemandSignal(
            item_id=str(item["ItemID"]),
            location_id=str(item["LocationID"]),
            demand_qty=float(item["Quantity"]),
            demand_due_at=datetime.fromisoformat(str(item["DueAt"])),
            demand_type=str(item["DemandType"]),
            is_qualified_spike=(
                item.get("SpikeQualificationStatus") == "QualifiedByDDSOP"
            ),
            demand_id=str(item["DemandID"]),
            uom=str(item["UnitOfMeasure"]),
        )
        for item in runtime.get("DemandSignals", [])
    ]
    open_supply = [
        OpenSupply(
            item_id=str(item["ItemID"]),
            location_id=str(item["LocationID"]),
            supply_qty=float(item["Quantity"]),
            expected_at=datetime.fromisoformat(str(item["ExpectedAt"])),
            status=str(item["SupplyStatus"]),
            supply_id=str(item["SupplyID"]),
            uom=str(item["UnitOfMeasure"]),
        )
        for item in runtime.get("OpenSupplySignals", [])
    ]
    result = evaluate_ddmrp_net_flow(
        decoupling_points=decoupling_points,
        stock_buffers=buffers,
        demand_signals=demand_signals,
        open_supply=open_supply,
        evaluated_at=evaluated_at,
    )
    for line in result["Lines"]:
        inventory = inventory_by_key[(str(line["ItemID"]), str(line["LocationID"]))]
        line.update(
            {
                "PhysicalOnHandQty": float(inventory["OnHandQty"]),
                "AuthorityAllocatedQty": float(inventory["AllocatedQty"]),
                "AuthorityAvailableQty": float(inventory["AvailableQty"]),
                "QualityState": str(inventory["QualityState"]),
                "Uom": str(inventory["UnitOfMeasure"]),
            }
        )
    result["RuntimePlanningInputPackageID"] = package_record[
        "RuntimePlanningInputPackageID"
    ]
    result["Boundary"] = (
        "SDBR runtime signal calculation only; DDAE-governed DDMRP master "
        "settings are consumed as frozen read-only inputs."
    )
    return result


def _validate_ddmrp_runtime_uom_references(
    *,
    ddmrp_config: Mapping[str, Any],
    runtime: Mapping[str, Any],
    buffer_by_id: Mapping[str, Mapping[str, Any]],
    inventory_by_key: Mapping[tuple[str, str], Mapping[str, Any]],
) -> None:
    expected_uom_by_key: dict[tuple[str, str], str] = {}
    for point in ddmrp_config.get("DecouplingPoints", []):
        key = (str(point["ItemID"]), str(point["LocationID"]))
        inventory = inventory_by_key.get(key)
        profile = buffer_by_id.get(str(point["BufferProfileID"]))
        if inventory is None or profile is None:
            continue
        inventory_uom = str(inventory["UnitOfMeasure"])
        profile_uom = str(profile["UnitOfMeasure"])
        if profile_uom != inventory_uom:
            _raise_uom_reference_error(
                key=key,
                expected_uom=inventory_uom,
                actual_uom=profile_uom,
                source="StockBufferProfile",
            )
        expected_uom_by_key[key] = inventory_uom

    for collection_name in ("DemandSignals", "OpenSupplySignals"):
        for row in runtime.get(collection_name, []):
            key = (str(row["ItemID"]), str(row["LocationID"]))
            expected_uom = expected_uom_by_key.get(key)
            if expected_uom is None:
                continue
            actual_uom = str(row["UnitOfMeasure"])
            if actual_uom != expected_uom:
                _raise_uom_reference_error(
                    key=key,
                    expected_uom=expected_uom,
                    actual_uom=actual_uom,
                    source=collection_name,
                )


def _raise_uom_reference_error(
    *,
    key: tuple[str, str],
    expected_uom: str,
    actual_uom: str,
    source: str,
) -> None:
    raise DdmrpRuntimeAuthorityError(
        "REFERENCE_NOT_FOUND",
        (
            f"UnitOfMeasure reference mismatch for {key[0]}/{key[1]}: "
            f"inventory uses {expected_uom}, but {source} uses {actual_uom}."
        ),
    )


def build_bounded_scheduling_input_from_package(
    package_record: Mapping[str, Any],
) -> dict[str, Any]:
    payload = _payload(package_record)
    executable = payload.get("ExecutableSchedulingInputs")
    if not isinstance(executable, Mapping):
        raise ValueError("ExecutableSchedulingInputs is required for bounded scheduling.")
    errors = _executable_cross_reference_errors(executable)
    if errors:
        raise ValueError(errors[0]["Message"])
    return {
        "RuntimePlanningInputPackageID": package_record[
            "RuntimePlanningInputPackageID"
        ],
        "MasterDataVersionID": executable["MasterDataVersionID"],
        "WorkOrders": deepcopy(executable.get("WorkOrders", [])),
        "Routings": deepcopy(executable.get("Routings", [])),
        "Operations": deepcopy(executable.get("Operations", [])),
        "ResourceCalendars": deepcopy(executable.get("ResourceCalendars", [])),
        "MaterialConstraints": deepcopy(executable.get("MaterialConstraints", [])),
        "SetupChangeoverRules": deepcopy(executable.get("SetupChangeoverRules", [])),
        "Boundary": (
            "Bounded scheduling adapter input only; no missing routing, resource, "
            "operation, or calendar placeholders are created."
        ),
    }


def correlate_runtime_package_feedback_delivery(
    package_record: Mapping[str, Any],
    feedback_messages: list[Mapping[str, Any]],
    *,
    delivered_at: datetime,
) -> list[dict[str, Any]]:
    payload = _payload(package_record)
    expectations = payload["OutputExpectations"]
    records: list[dict[str, Any]] = []
    for message in feedback_messages:
        records.append(
            {
                "RuntimePlanningInputPackageID": package_record[
                    "RuntimePlanningInputPackageID"
                ],
                "DeliveryLedgerCorrelationID": expectations[
                    "DeliveryLedgerCorrelationID"
                ],
                "FeedbackCorrelationMode": expectations["FeedbackCorrelationMode"],
                "FeedbackContractID": expectations["FeedbackContractID"],
                "MessageID": message.get("MessageID"),
                "IdempotencyKey": message.get("IdempotencyKey"),
                "MessageType": message.get("MessageType"),
                "PlanningRunID": (message.get("Payload") or {}).get("PlanningRunID"),
                "DeliveredAt": delivered_at.isoformat(),
                "CorrelationStatus": "Linked",
            }
        )
    return records


def _result(
    *,
    status: str,
    message: Mapping[str, Any],
    received_at: datetime,
    errors: list[dict[str, Any]],
    package_record: dict[str, Any] | None,
) -> RuntimePlanningInputProcessingResult:
    inbound = {
        "Message": deepcopy(dict(message)),
        "ReceivedAt": received_at.isoformat(),
        "ProcessingStatus": status,
        "IdempotencyKey": message.get("IdempotencyKey"),
        "RuntimePlanningInputPackageID": (
            (message.get("Payload") or {})
            .get("PackageIdentity", {})
            .get("RuntimePlanningInputPackageID")
            if isinstance(message.get("Payload"), Mapping)
            else None
        ),
        "Errors": errors,
    }
    return RuntimePlanningInputProcessingResult(
        processing_status=status,
        package_record=package_record,
        inbound_message_record=inbound,
        errors=errors,
    )


def _append_semantic_errors(payload: Mapping[str, Any], errors: list[dict[str, Any]]) -> None:
    identity = dict(payload["PackageIdentity"])
    evidence = dict(payload["ParameterAuthorityEvidence"])
    runtime = payload.get("RuntimeEvidenceSnapshot")
    executable = payload.get("ExecutableSchedulingInputs")
    rules = dict(payload["ConsumerRules"])
    expectations = dict(payload["OutputExpectations"])

    if identity["ScenarioLabel"] in {"DemoFixture", "ControlledContractGoldenLoopDemo"}:
        if identity["MappingConfidence"] not in {"PublicDemoOnly", "ReviewedEvidence"}:
            errors.append(
                _error(
                    "CONFIDENCE_LABEL_CONFLICT",
                    "Demo labels cannot be paired with production mapping confidence.",
                    "Payload.PackageIdentity.MappingConfidence",
                )
            )
    if identity["ScenarioLabel"] == "ProductionCandidate":
        if identity["MappingConfidence"] not in {"ProductionCandidate", "ProductionAccepted"}:
            errors.append(
                _error(
                    "CONFIDENCE_LABEL_CONFLICT",
                    "ProductionCandidate label requires production candidate or accepted mapping confidence.",
                    "Payload.PackageIdentity.MappingConfidence",
                )
            )
    _append_evidence_coverage_errors(identity["ExecutionMode"], evidence, errors)
    _append_consumer_rule_errors(rules, errors)
    _append_runtime_evidence_errors(identity["ExecutionMode"], runtime, errors)
    _append_executable_input_errors(identity["ExecutionMode"], executable, errors)
    if expectations.get("FeedbackContractID") != "DDSOP-FEEDBACK-OUTBOUND-V1":
        errors.append(
            _error(
                "ENUM_VALUE_INVALID",
                "Output expectations must target DDSOP-FEEDBACK-OUTBOUND-V1.",
                "Payload.OutputExpectations.FeedbackContractID",
            )
        )
    if expectations.get("RuntimePlanningInputPackageID") != identity.get(
        "RuntimePlanningInputPackageID"
    ):
        errors.append(
            _error(
                "FEEDBACK_CORRELATION_MISSING",
                "OutputExpectations RuntimePlanningInputPackageID must match PackageIdentity.",
                "Payload.OutputExpectations.RuntimePlanningInputPackageID",
            )
        )
    if expectations.get("FeedbackCorrelationMode") != "DeliveryLedger":
        errors.append(
            _error(
                "FEEDBACK_CORRELATION_MISSING",
                "FeedbackCorrelationMode must be DeliveryLedger.",
                "Payload.OutputExpectations.FeedbackCorrelationMode",
            )
        )


def _append_configuration_reference_errors(
    frozen: Mapping[str, Any],
    errors: list[dict[str, Any]],
    *,
    accepted_configurations: Mapping[str, Mapping[str, Any]],
) -> None:
    if frozen.get("SourceConfigurationContractID") != "DDSOP-CONFIG-INBOUND-V1":
        errors.append(
            _error(
                "REFERENCE_NOT_FOUND",
                "Frozen configuration must reference DDSOP-CONFIG-INBOUND-V1.",
                "Payload.FrozenDdsopConfiguration.SourceConfigurationContractID",
            )
        )
    if frozen.get("ConfigStatus") not in {"Approved", "Active"}:
        errors.append(
            _error(
                "CONFIGURATION_NOT_APPROVED",
                "Frozen DDSOP configuration must be Approved or Active.",
                "Payload.FrozenDdsopConfiguration.ConfigStatus",
            )
        )
    config_id = str(frozen.get("OperatingModelConfigurationID"))
    accepted = accepted_configurations.get(config_id)
    if accepted is None:
        errors.append(
            _reference_error(
                "OperatingModelConfigurationID",
                config_id,
                "Payload.FrozenDdsopConfiguration.OperatingModelConfigurationID",
            )
        )
        return
    accepted_payload = _operating_payload(accepted)
    accepted_status = accepted_payload.get("Status") or accepted_payload.get("ConfigStatus")
    if accepted_status not in {"Approved", "Active"}:
        errors.append(
            _error(
                "CONFIGURATION_NOT_APPROVED",
                "Referenced DDSOP configuration is not Approved or Active in SDBR.",
                "AcceptedConfigurations.Status",
            )
        )
    expected = canonical_operating_model_fingerprint(accepted_payload)
    if frozen.get("OperatingModelFingerprint") != expected:
        errors.append(
            _error(
                "FINGERPRINT_MISMATCH",
                "Frozen configuration fingerprint does not match accepted DDSOP configuration.",
                "Payload.FrozenDdsopConfiguration.OperatingModelFingerprint",
            )
        )
    scheduling_id = _configuration_section_id(
        accepted_payload,
        section="SchedulingConfiguration",
        direct_field="SchedulingConfigurationID",
    )
    if scheduling_id and scheduling_id != frozen.get("SchedulingConfigurationID"):
        errors.append(
            _reference_error(
                "SchedulingConfigurationID",
                str(frozen.get("SchedulingConfigurationID")),
                "Payload.FrozenDdsopConfiguration.SchedulingConfigurationID",
            )
        )
    ddmrp_id = _configuration_section_id(
        accepted_payload,
        section="DDMRPConfiguration",
        direct_field="DDMRPConfigurationID",
    )
    if ddmrp_id and ddmrp_id != frozen.get("DDMRPConfigurationID"):
        errors.append(
            _reference_error(
                "DDMRPConfigurationID",
                str(frozen.get("DDMRPConfigurationID")),
                "Payload.FrozenDdsopConfiguration.DDMRPConfigurationID",
            )
        )


def _append_evidence_coverage_errors(
    execution_mode: str,
    evidence: Mapping[str, Any],
    errors: list[dict[str, Any]],
) -> None:
    refs = [
        item
        for item in evidence.get("ParameterEvidenceRefs", [])
        if isinstance(item, Mapping)
    ]
    applicable_groups = {
        str(item.get("FieldGroup"))
        for item in refs
        if item.get("Applicability") == "Applicable"
    }
    all_groups = {str(item.get("FieldGroup")) for item in refs}
    not_applicable_without_reason = [
        item.get("FieldGroup")
        for item in refs
        if item.get("Applicability") == "NotApplicable"
        and not item.get("NotApplicableReason")
    ]
    for field_group in not_applicable_without_reason:
        errors.append(
            _error(
                "AUTHORITY_EVIDENCE_MISSING",
                f"{field_group} evidence marked NotApplicable must include a reason.",
                "Payload.ParameterAuthorityEvidence.ParameterEvidenceRefs.NotApplicableReason",
            )
        )
    required: set[str] = set()
    if execution_mode in {"DDMRPExecution", "DDMRPAndBoundedScheduling"}:
        required |= DDMRP_REQUIRED_EVIDENCE
    if execution_mode in {"BoundedProductionScheduling", "DDMRPAndBoundedScheduling"}:
        required |= SCHEDULING_REQUIRED_EVIDENCE
    missing = sorted(required - all_groups)
    for field_group in missing:
        errors.append(
            _error(
                "AUTHORITY_EVIDENCE_MISSING",
                f"Missing required parameter evidence for {field_group}.",
                "Payload.ParameterAuthorityEvidence.ParameterEvidenceRefs",
            )
        )
    buffer_refs = [
        item
        for item in refs
        if item.get("FieldGroup") == "BufferZones"
        and item.get("CalculationStatus") == "Calculated"
    ]
    if buffer_refs:
        for field_group in sorted(BUFFER_ZONE_CALCULATION_INPUTS - all_groups):
            errors.append(
                _error(
                    "AUTHORITY_EVIDENCE_MISSING",
                    f"Calculated BufferZones requires {field_group} evidence.",
                    "Payload.ParameterAuthorityEvidence.ParameterEvidenceRefs",
                )
            )
    if evidence.get("ApprovedAt") and evidence.get("EffectivePolicyID") is None:
        errors.append(
            _error(
                "AUTHORITY_EVIDENCE_MISSING",
                "EffectivePolicyID is required for approved parameter evidence.",
                "Payload.ParameterAuthorityEvidence.EffectivePolicyID",
            )
        )


def _append_consumer_rule_errors(
    rules: Mapping[str, Any],
    errors: list[dict[str, Any]],
) -> None:
    checks = [
        (
            REQUIRED_READ_ONLY_TOKENS,
            set(rules.get("ReadOnlyFrozenInputs", [])),
            "Payload.ConsumerRules.ReadOnlyFrozenInputs",
        ),
        (
            REQUIRED_DERIVED_SIGNAL_TOKENS,
            set(rules.get("SDBRDerivedRuntimeSignals", [])),
            "Payload.ConsumerRules.SDBRDerivedRuntimeSignals",
        ),
        (
            REQUIRED_FORBIDDEN_MUTATION_TOKENS,
            set(rules.get("ForbiddenMutations", [])),
            "Payload.ConsumerRules.ForbiddenMutations",
        ),
    ]
    for required, actual, field in checks:
        for token in sorted(required - actual):
            errors.append(
                _error(
                    "OWNERSHIP_VIOLATION",
                    f"Missing canonical consumer rule token {token}.",
                    field,
                )
            )


def _append_runtime_evidence_errors(
    execution_mode: str,
    runtime: Any,
    errors: list[dict[str, Any]],
) -> None:
    if execution_mode not in {"DDMRPExecution", "DDMRPAndBoundedScheduling"}:
        return
    if not isinstance(runtime, Mapping):
        errors.append(
            _error(
                "RUNTIME_EVIDENCE_MISSING",
                "RuntimeEvidenceSnapshot is required for DDMRP execution.",
                "Payload.RuntimeEvidenceSnapshot",
            )
        )
        return
    for collection_name in ("InventoryPositions", "DemandSignals", "OpenSupplySignals"):
        for index, item in enumerate(runtime.get(collection_name, [])):
            if not isinstance(item, Mapping) or not item.get("EvidenceRefs"):
                errors.append(
                    _error(
                        "RUNTIME_EVIDENCE_MISSING",
                        f"{collection_name} row is missing EvidenceRefs.",
                        f"Payload.RuntimeEvidenceSnapshot.{collection_name}[{index}].EvidenceRefs",
                    )
                )
    for index, item in enumerate(runtime.get("DemandSignals", [])):
        if not isinstance(item, Mapping):
            continue
        if item.get("DemandType") == "SpikeCandidate":
            status = item.get("SpikeQualificationStatus")
            mode = item.get("SpikeQualificationMode")
            valid = (
                status == "QualifiedByDDSOP"
                and mode == "ProvidedByDDSOP"
                and item.get("SpikeQualificationEvidenceID")
            ) or (status == "RequiresSDBRQualification" and mode == "CalculatedBySDBR")
            if not valid:
                errors.append(
                    _error(
                        "SPIKE_QUALIFICATION_AMBIGUOUS",
                        "SpikeCandidate demand must be qualified by DDSOP or explicitly require SDBR qualification.",
                        f"Payload.RuntimeEvidenceSnapshot.DemandSignals[{index}]",
                    )
                )


def _append_executable_input_errors(
    execution_mode: str,
    executable: Any,
    errors: list[dict[str, Any]],
) -> None:
    if execution_mode not in {"BoundedProductionScheduling", "DDMRPAndBoundedScheduling"}:
        return
    if not isinstance(executable, Mapping):
        errors.append(
            _error(
                "EXECUTABLE_SCHEDULING_INPUT_MISSING",
                "ExecutableSchedulingInputs is required for bounded scheduling.",
                "Payload.ExecutableSchedulingInputs",
            )
        )
        return
    for collection_name in ("WorkOrders", "Routings", "Operations", "ResourceCalendars"):
        for index, item in enumerate(executable.get(collection_name, [])):
            if not isinstance(item, Mapping) or not item.get("EvidenceRefs"):
                errors.append(
                    _error(
                        "EXECUTABLE_SCHEDULING_INPUT_MISSING",
                        f"{collection_name} row is missing EvidenceRefs.",
                        f"Payload.ExecutableSchedulingInputs.{collection_name}[{index}].EvidenceRefs",
                    )
                )
    errors.extend(_executable_cross_reference_errors(executable))


def _executable_cross_reference_errors(
    executable: Mapping[str, Any],
) -> list[dict[str, Any]]:
    errors: list[dict[str, Any]] = []
    routing_ids = {str(item.get("RoutingID")) for item in executable.get("Routings", [])}
    operation_ids = {
        str(item.get("OperationID")) for item in executable.get("Operations", [])
    }
    calendar_resource_ids = {
        str(item.get("ResourceID")) for item in executable.get("ResourceCalendars", [])
    }
    for order in executable.get("WorkOrders", []):
        if str(order.get("RoutingID")) not in routing_ids:
            errors.append(
                _reference_error(
                    "RoutingID",
                    str(order.get("RoutingID")),
                    "Payload.ExecutableSchedulingInputs.WorkOrders.RoutingID",
                )
            )
    for routing in executable.get("Routings", []):
        for operation_id in routing.get("OperationIDs", []):
            if str(operation_id) not in operation_ids:
                errors.append(
                    _reference_error(
                        "OperationID",
                        str(operation_id),
                        "Payload.ExecutableSchedulingInputs.Routings.OperationIDs",
                    )
                )
    for operation in executable.get("Operations", []):
        resource_ids = [operation.get("ResourceID"), *operation.get("AlternateResourceIDs", [])]
        for resource_id in resource_ids:
            if str(resource_id) not in calendar_resource_ids:
                errors.append(
                    _reference_error(
                        "ResourceID",
                        str(resource_id),
                        "Payload.ExecutableSchedulingInputs.Operations.ResourceID",
                    )
                )
    return errors


def _schema_error(error) -> dict[str, Any]:
    field_path = ".".join(str(item) for item in error.absolute_path) or "$"
    if error.validator in {"enum", "const"}:
        code = "ENUM_VALUE_INVALID"
    elif error.validator in {"minimum", "exclusiveMinimum"}:
        code = "INVALID_NUMERIC_VALUE"
    else:
        code = "REQUIRED_FIELD_MISSING"
    return _error(code, error.message, field_path)


def _error(code: str, message: str, field: str) -> dict[str, Any]:
    return {"Code": code, "Message": message, "Field": field}


def _reference_error(reference_type: str, reference_id: str, field: str) -> dict[str, Any]:
    result = _error(
        "REFERENCE_NOT_FOUND",
        f"{reference_type} {reference_id} cannot be resolved in runtime planning input package.",
        field,
    )
    result["ReferenceType"] = reference_type
    result["ReferenceID"] = reference_id
    return result


def _dedupe_errors(errors: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[str, str, str]] = set()
    result: list[dict[str, Any]] = []
    for error in errors:
        key = (str(error.get("Code")), str(error.get("Field")), str(error.get("Message")))
        if key not in seen:
            seen.add(key)
            result.append(error)
    return result


def _configuration_section_id(
    configuration: Mapping[str, Any],
    *,
    section: str,
    direct_field: str,
) -> str | None:
    if configuration.get(direct_field):
        return str(configuration[direct_field])
    section_value = configuration.get(section)
    if isinstance(section_value, Mapping) and section_value.get(direct_field):
        return str(section_value[direct_field])
    return None


def _payload(package_record: Mapping[str, Any]) -> Mapping[str, Any]:
    payload = package_record.get("Payload")
    if not isinstance(payload, Mapping):
        raise ValueError("Runtime planning input package payload is unavailable.")
    return payload


def _operating_payload(configuration: Mapping[str, Any]) -> Mapping[str, Any]:
    payload = configuration.get("Payload") if "Payload" in configuration else configuration
    if not isinstance(payload, Mapping):
        raise ValueError("Operating model configuration payload is unavailable.")
    return payload
