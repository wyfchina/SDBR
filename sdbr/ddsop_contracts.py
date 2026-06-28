from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Mapping

from jsonschema import Draft202012Validator


CONFIG_CONTRACT_ID = "DDSOP-CONFIG-INBOUND-V1"
FEEDBACK_CONTRACT_ID = "DDSOP-FEEDBACK-OUTBOUND-V1"
CONTRACT_VERSION = "1.0.0"
DEFAULT_CONTRACT_ROOT = Path(
    os.environ.get(
        "DDAE_INTERFACE_CONTRACT_ROOT",
        r"D:\Documents\DDAE_INTERFACE_CONTRACT",
    )
)


@dataclass(frozen=True)
class DdsopConfigProcessingResult:
    ack: dict[str, Any]
    configuration_record: dict[str, Any] | None
    inbound_message_record: dict[str, Any]


def contract_root() -> Path:
    return DEFAULT_CONTRACT_ROOT


def _schema_path(*parts: str) -> Path:
    return contract_root().joinpath("contracts", *parts)


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def config_schema() -> dict[str, Any]:
    return _load_json(
        _schema_path(
            "ddsop-config-inbound-v1",
            "schema",
            "ddsop-config-inbound-v1.schema.json",
        )
    )


def config_ack_schema() -> dict[str, Any]:
    return _load_json(
        _schema_path(
            "ddsop-config-inbound-v1",
            "schema",
            "ddsop-config-inbound-v1-ack.schema.json",
        )
    )


def feedback_schema() -> dict[str, Any]:
    return _load_json(
        _schema_path(
            "ddsop-feedback-outbound-v1",
            "schema",
            "ddsop-feedback-outbound-v1.schema.json",
        )
    )


def feedback_ack_schema() -> dict[str, Any]:
    return _load_json(
        _schema_path(
            "ddsop-feedback-outbound-v1",
            "schema",
            "ddsop-feedback-outbound-v1-ack.schema.json",
        )
    )


def canonical_operating_model_fingerprint(
    operating_model_configuration: Mapping[str, Any],
) -> str:
    canonical = deepcopy(dict(operating_model_configuration))
    canonical.pop("Fingerprint", None)
    encoded = json.dumps(
        canonical,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def process_ddsop_config_message(
    message: Mapping[str, Any],
    *,
    received_at: datetime,
    duplicate_record: Mapping[str, Any] | None = None,
    release_policy_ids: set[str] | None = None,
    calendar_ids: set[str] | None = None,
    scheduling_strategy_ids: set[str] | None = None,
    planning_priority_policy_ids: set[str] | None = None,
    scheduling_priority_classes: set[str] | None = None,
) -> DdsopConfigProcessingResult:
    normalized = deepcopy(dict(message))
    idempotency_key = str(normalized.get("IdempotencyKey", ""))
    message_id = str(normalized.get("MessageID", ""))
    if duplicate_record is not None:
        existing_configuration = duplicate_record.get("AcceptedConfigurationID")
        existing_fingerprint = duplicate_record.get("Fingerprint")
        ack = _ack(
            original_message_id=message_id,
            idempotency_key=idempotency_key,
            processing_status="Duplicate",
            received_at=received_at,
            usable_for_planning_run=bool(
                duplicate_record.get("UsableForPlanningRun", False)
            ),
            accepted_configuration_id=(
                str(existing_configuration)
                if existing_configuration is not None
                else None
            ),
            fingerprint=(
                str(existing_fingerprint) if existing_fingerprint is not None else None
            ),
            errors=[],
        )
        return DdsopConfigProcessingResult(
            ack=ack,
            configuration_record=None,
            inbound_message_record={
                "Message": normalized,
                "Ack": ack,
                "ReceivedAt": received_at.isoformat(),
                "ProcessingStatus": "Duplicate",
                "IdempotencyKey": idempotency_key,
            },
        )

    schema_errors = sorted(
        Draft202012Validator(config_schema()).iter_errors(normalized),
        key=lambda item: list(item.path),
    )
    if schema_errors:
        errors = [_schema_error_to_contract_error(error) for error in schema_errors]
        primary_errors = _dedupe_errors(errors)
        ack = _ack(
            original_message_id=message_id,
            idempotency_key=idempotency_key,
            processing_status="Rejected",
            received_at=received_at,
            usable_for_planning_run=False,
            accepted_configuration_id=None,
            fingerprint=None,
            errors=primary_errors,
        )
        return DdsopConfigProcessingResult(
            ack=ack,
            configuration_record=None,
            inbound_message_record={
                "Message": normalized,
                "Ack": ack,
                "ReceivedAt": received_at.isoformat(),
                "ProcessingStatus": "Rejected",
                "IdempotencyKey": idempotency_key,
            },
        )

    payload = deepcopy(dict(normalized["Payload"]))
    fingerprint = canonical_operating_model_fingerprint(payload)
    errors: list[dict[str, Any]] = []
    if payload.get("Fingerprint") != fingerprint:
        errors.append(
            _error(
                code="FINGERPRINT_MISMATCH",
                message="Payload fingerprint does not match the contract canonical SHA-256 value.",
                field_path="Payload.Fingerprint",
            )
        )
    if payload.get("Status") not in {"Approved", "Active"}:
        errors.append(
            _error(
                code="CONFIGURATION_NOT_APPROVED",
                message="Only Approved or Active operating model configurations can be used by SDBR.",
                field_path="Payload.Status",
            )
        )
    _append_business_invariant_errors(payload, errors)
    if errors:
        ack = _ack(
            original_message_id=message_id,
            idempotency_key=idempotency_key,
            processing_status="Rejected",
            received_at=received_at,
            usable_for_planning_run=False,
            accepted_configuration_id=None,
            fingerprint=fingerprint,
            errors=errors,
        )
        return DdsopConfigProcessingResult(
            ack=ack,
            configuration_record=None,
            inbound_message_record={
                "Message": normalized,
                "Ack": ack,
                "ReceivedAt": received_at.isoformat(),
                "ProcessingStatus": "Rejected",
                "IdempotencyKey": idempotency_key,
                "Fingerprint": fingerprint,
            },
        )

    pending_references = _pending_references(
        payload,
        release_policy_ids=release_policy_ids or set(),
        calendar_ids=calendar_ids or set(),
        scheduling_strategy_ids=scheduling_strategy_ids or set(),
        planning_priority_policy_ids=planning_priority_policy_ids or set(),
        scheduling_priority_classes=scheduling_priority_classes or set(),
    )
    processing_status = "AcceptedPendingReferences" if pending_references else "Accepted"
    usable = processing_status == "Accepted"
    scheduling_configuration = dict(payload["SchedulingConfiguration"])
    ddmrp_configuration = dict(payload["DDMRPConfiguration"])
    configuration_id = str(payload["OperatingModelConfigurationID"])
    configuration_record = {
        "OperatingModelConfigurationID": configuration_id,
        "ConfigurationVersion": payload["ConfigurationVersion"],
        "SchemaVersion": payload["SchemaVersion"],
        "Status": payload["Status"],
        "EffectiveFrom": payload["EffectiveFrom"],
        "EffectiveTo": payload.get("EffectiveTo"),
        "Fingerprint": fingerprint,
        "SchedulingConfigurationID": scheduling_configuration[
            "SchedulingConfigurationID"
        ],
        "DDMRPConfigurationID": ddmrp_configuration["DDMRPConfigurationID"],
        "ProcessingStatus": processing_status,
        "UsableForPlanningRun": usable,
        "PendingReferences": pending_references,
        "Payload": payload,
        "SourceMessageID": message_id,
        "IdempotencyKey": idempotency_key,
        "ReceivedAt": received_at.isoformat(),
    }
    ack = _ack(
        original_message_id=message_id,
        idempotency_key=idempotency_key,
        processing_status=processing_status,
        received_at=received_at,
        usable_for_planning_run=usable,
        accepted_configuration_id=configuration_id,
        fingerprint=fingerprint,
        errors=[],
        pending_references=pending_references,
    )
    return DdsopConfigProcessingResult(
        ack=ack,
        configuration_record=configuration_record,
        inbound_message_record={
            "Message": normalized,
            "Ack": ack,
            "ReceivedAt": received_at.isoformat(),
            "ProcessingStatus": processing_status,
            "IdempotencyKey": idempotency_key,
            "AcceptedConfigurationID": configuration_id,
            "Fingerprint": fingerprint,
            "UsableForPlanningRun": usable,
            "PendingReferences": pending_references,
        },
    )


def validate_feedback_message(message: Mapping[str, Any]) -> None:
    Draft202012Validator(feedback_schema()).validate(dict(message))


def validate_required_master_data_references(
    operating_model_configuration: Mapping[str, Any],
    master_data_version: Mapping[str, Any],
) -> list[dict[str, Any]]:
    payload = (
        operating_model_configuration.get("Payload")
        if "Payload" in operating_model_configuration
        else operating_model_configuration
    )
    if not isinstance(payload, Mapping):
        return [
            {
                "Code": "REFERENCE_NOT_FOUND",
                "Message": "Operating model configuration payload is not available.",
                "Field": "Payload",
                "ReferenceType": "OperatingModelConfiguration",
                "ReferenceID": str(
                    operating_model_configuration.get(
                        "OperatingModelConfigurationID", "unknown"
                    )
                ),
            }
        ]
    resources = [
        item
        for item in master_data_version.get("Resources", [])
        if isinstance(item, Mapping)
    ]
    routings = [
        item
        for item in master_data_version.get("Routings", [])
        if isinstance(item, Mapping)
    ]
    orders = [
        item for item in master_data_version.get("Orders", []) if isinstance(item, Mapping)
    ]
    inventory_buffers = [
        item
        for item in master_data_version.get("InventoryBuffers", [])
        if isinstance(item, Mapping)
    ]
    material_requirements = [
        item
        for item in master_data_version.get("MaterialRequirements", [])
        if isinstance(item, Mapping)
    ]
    resource_ids = {str(item.get("ResourceID")) for item in resources}
    product_ids = {
        str(item.get("ProductID"))
        for item in [*routings, *orders]
        if item.get("ProductID") is not None
    }
    routing_pairs = {
        (str(item.get("ProductID")), str(item.get("RoutingID")))
        for item in routings
        if item.get("ProductID") is not None and item.get("RoutingID") is not None
    }
    item_ids = {
        str(item.get("ItemID"))
        for item in [*inventory_buffers, *material_requirements]
        if item.get("ItemID") is not None
    }
    location_ids = {
        str(item.get("LocationID"))
        for item in [*inventory_buffers, *material_requirements]
        if item.get("LocationID") is not None
    }
    item_location_pairs = {
        (str(item.get("ItemID")), str(item.get("LocationID")))
        for item in [*inventory_buffers, *material_requirements]
        if item.get("ItemID") is not None and item.get("LocationID") is not None
    }
    errors: list[dict[str, Any]] = []
    scheduling = dict(payload.get("SchedulingConfiguration", {}))
    for control_point in scheduling.get("ControlPoints", []):
        if isinstance(control_point, Mapping):
            _require_reference(
                errors,
                reference_type="ResourceID",
                reference_id=control_point.get("ResourceID"),
                known_ids=resource_ids,
                field="Payload.SchedulingConfiguration.ControlPoints.ResourceID",
            )
    for resource_setting in scheduling.get("ResourceSettings", []):
        if isinstance(resource_setting, Mapping):
            _require_reference(
                errors,
                reference_type="ResourceID",
                reference_id=resource_setting.get("ResourceID"),
                known_ids=resource_ids,
                field="Payload.SchedulingConfiguration.ResourceSettings.ResourceID",
            )
    for assignment in scheduling.get("TimeBufferAssignments", []):
        if isinstance(assignment, Mapping):
            _require_reference(
                errors,
                reference_type="ProductID",
                reference_id=assignment.get("ProductID"),
                known_ids=product_ids,
                field="Payload.SchedulingConfiguration.TimeBufferAssignments.ProductID",
            )
    for part_setting in scheduling.get("PartSchedulingSettings", []):
        if not isinstance(part_setting, Mapping):
            continue
        product_id = part_setting.get("ProductID")
        routing_id = part_setting.get("PrimaryRoutingID")
        _require_reference(
            errors,
            reference_type="ProductID",
            reference_id=product_id,
            known_ids=product_ids,
            field="Payload.SchedulingConfiguration.PartSchedulingSettings.ProductID",
        )
        if product_id is not None and routing_id is not None:
            if (str(product_id), str(routing_id)) not in routing_pairs:
                errors.append(
                    _reference_error(
                        reference_type="PrimaryRoutingID",
                        reference_id=str(routing_id),
                        field="Payload.SchedulingConfiguration.PartSchedulingSettings.PrimaryRoutingID",
                        message=(
                            "PrimaryRoutingID must exist in the selected MasterDataVersionID "
                            "for the same ProductID."
                        ),
                        evidence={"ProductID": str(product_id)},
                    )
                )
        for alternate_resource_id in part_setting.get("AllowedAlternateResources", []):
            _require_reference(
                errors,
                reference_type="ResourceID",
                reference_id=alternate_resource_id,
                known_ids=resource_ids,
                field="Payload.SchedulingConfiguration.PartSchedulingSettings.AllowedAlternateResources",
            )
    ddmrp = dict(payload.get("DDMRPConfiguration", {}))
    for point in ddmrp.get("DecouplingPoints", []):
        if isinstance(point, Mapping):
            _require_item_location(
                errors,
                item_id=point.get("ItemID"),
                location_id=point.get("LocationID"),
                item_ids=item_ids,
                location_ids=location_ids,
                item_location_pairs=item_location_pairs,
                field="Payload.DDMRPConfiguration.DecouplingPoints",
            )
    for assignment in ddmrp.get("PartProfileAssignments", []):
        if isinstance(assignment, Mapping):
            _require_item_location(
                errors,
                item_id=assignment.get("ItemID"),
                location_id=assignment.get("LocationID"),
                item_ids=item_ids,
                location_ids=location_ids,
                item_location_pairs=item_location_pairs,
                field="Payload.DDMRPConfiguration.PartProfileAssignments",
            )
    for adjustment in ddmrp.get("AdjustmentFactors", []):
        if isinstance(adjustment, Mapping):
            _require_item_location(
                errors,
                item_id=adjustment.get("ItemID"),
                location_id=adjustment.get("LocationID"),
                item_ids=item_ids,
                location_ids=location_ids,
                item_location_pairs=item_location_pairs,
                field="Payload.DDMRPConfiguration.AdjustmentFactors",
            )
    return errors


def build_planning_run_feedback_message(
    planning_run: Mapping[str, Any],
    *,
    generated_at: datetime,
    release_authorizations: list[Any] | None = None,
    target_system: str = "DDAE",
) -> dict[str, Any]:
    payload = _planning_run_feedback_payload(
        planning_run,
        release_authorizations=release_authorizations or [],
    )
    message = {
        "ContractID": FEEDBACK_CONTRACT_ID,
        "ContractVersion": CONTRACT_VERSION,
        "MessageID": f"SDBR-MSG-PLANNING-RUN-FEEDBACK-{planning_run['RunID']}",
        "MessageType": "PlanningRunFeedbackPublished",
        "SourceSystem": "SDBR",
        "TargetSystem": target_system,
        "IdempotencyKey": f"SDBR:PlanningRunFeedback:{planning_run['RunID']}",
        "OccurredAt": generated_at.isoformat(),
        "Payload": payload,
    }
    validate_feedback_message(message)
    return message


def build_variance_analysis_feedback_message(
    planning_run: Mapping[str, Any],
    *,
    generated_at: datetime,
    target_system: str = "DDAE",
) -> dict[str, Any]:
    payload = _variance_feedback_payload(planning_run, generated_at=generated_at)
    message = {
        "ContractID": FEEDBACK_CONTRACT_ID,
        "ContractVersion": CONTRACT_VERSION,
        "MessageID": f"SDBR-MSG-VARIANCE-FEEDBACK-{planning_run['RunID']}",
        "MessageType": "VarianceAnalysisFeedbackPublished",
        "SourceSystem": "SDBR",
        "TargetSystem": target_system,
        "IdempotencyKey": f"SDBR:VarianceAnalysisFeedback:{planning_run['RunID']}",
        "OccurredAt": generated_at.isoformat(),
        "Payload": payload,
    }
    validate_feedback_message(message)
    return message


def _ack(
    *,
    original_message_id: str,
    idempotency_key: str,
    processing_status: str,
    received_at: datetime,
    usable_for_planning_run: bool,
    accepted_configuration_id: str | None,
    fingerprint: str | None,
    errors: list[dict[str, Any]],
    pending_references: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    ack: dict[str, Any] = {
        "ContractID": CONFIG_CONTRACT_ID,
        "ContractVersion": CONTRACT_VERSION,
        "OriginalMessageID": original_message_id,
        "IdempotencyKey": idempotency_key,
        "ProcessingStatus": processing_status,
        "ReceivedAt": received_at.isoformat(),
        "AcceptedConfigurationID": accepted_configuration_id,
        "Fingerprint": fingerprint,
        "UsableForPlanningRun": usable_for_planning_run,
        "Errors": errors,
    }
    if pending_references:
        ack["PendingReferences"] = pending_references
    Draft202012Validator(config_ack_schema()).validate(ack)
    return ack


def _error(*, code: str, message: str, field_path: str) -> dict[str, Any]:
    return {
        "Code": code,
        "Message": message,
        "Field": field_path,
    }


def _schema_error_to_contract_error(error) -> dict[str, Any]:
    field_path = ".".join(str(item) for item in error.absolute_path)
    if error.validator == "required" and "Approval" in str(error.message):
        return _error(
            code="APPROVAL_REQUIRED",
            message=error.message,
            field_path=field_path or "Payload.Approval",
        )
    if error.validator in {"enum", "const"}:
        code = "ENUM_VALUE_INVALID"
    else:
        code = "REQUIRED_FIELD_MISSING" if error.validator == "required" else "REQUIRED_FIELD_MISSING"
    return _error(code=code, message=error.message, field_path=field_path or "$")


def _dedupe_errors(errors: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[str, str]] = set()
    deduped: list[dict[str, Any]] = []
    for error in errors:
        key = (str(error["Code"]), str(error.get("FieldPath", "")))
        if key not in seen:
            seen.add(key)
            deduped.append(error)
    return deduped


def _append_business_invariant_errors(
    payload: Mapping[str, Any],
    errors: list[dict[str, Any]],
) -> None:
    effective_from = payload.get("EffectiveFrom")
    effective_to = payload.get("EffectiveTo")
    if effective_from is not None and effective_to is not None:
        try:
            if datetime.fromisoformat(str(effective_to)) <= datetime.fromisoformat(
                str(effective_from)
            ):
                errors.append(
                    _error(
                        code="EFFECTIVE_WINDOW_INVALID",
                        message="EffectiveTo must be greater than EffectiveFrom.",
                        field_path="Payload.EffectiveTo",
                    )
                )
        except ValueError:
            errors.append(
                _error(
                    code="EFFECTIVE_WINDOW_INVALID",
                    message="EffectiveFrom or EffectiveTo is not a valid date-time.",
                    field_path="Payload.EffectiveTo",
                )
            )
    scheduling = dict(payload.get("SchedulingConfiguration", {}))
    profile_ids = {
        str(profile.get("ProfileID"))
        for profile in scheduling.get("TimeBufferProfiles", [])
    }
    control_point_ids = {
        str(point.get("ControlPointID"))
        for point in scheduling.get("ControlPoints", [])
    }
    for profile in scheduling.get("TimeBufferProfiles", []):
        total = (
            float(profile.get("GreenRatio", 0))
            + float(profile.get("YellowRatio", 0))
            + float(profile.get("RedRatio", 0))
        )
        if abs(total - 1.0) > 0.000001:
            errors.append(
                _error(
                    code="BUFFER_RATIO_INVALID",
                    message="Time buffer zone ratios must sum to 1.0.",
                    field_path=(
                        "Payload.SchedulingConfiguration.TimeBufferProfiles"
                    ),
                )
            )
    for assignment in scheduling.get("TimeBufferAssignments", []):
        if str(assignment.get("ProfileID")) not in profile_ids:
            errors.append(
                _error(
                    code="REFERENCE_NOT_FOUND",
                    message="TimeBufferAssignment ProfileID does not exist in TimeBufferProfiles.",
                    field_path="Payload.SchedulingConfiguration.TimeBufferAssignments.ProfileID",
                )
            )
        if str(assignment.get("ControlPointID")) not in control_point_ids:
            errors.append(
                _error(
                    code="REFERENCE_NOT_FOUND",
                    message="TimeBufferAssignment ControlPointID does not exist in ControlPoints.",
                    field_path="Payload.SchedulingConfiguration.TimeBufferAssignments.ControlPointID",
                )
            )
    ddmrp = dict(payload.get("DDMRPConfiguration", {}))
    stock_profiles = {
        str(profile.get("BufferProfileID")): profile
        for profile in ddmrp.get("StockBufferProfiles", [])
    }
    for profile in stock_profiles.values():
        top_red = float(profile.get("TopOfRed", 0))
        top_yellow = float(profile.get("TopOfYellow", 0))
        top_green = float(profile.get("TopOfGreen", 0))
        if not top_red <= top_yellow <= top_green:
            errors.append(
                _error(
                    code="BUFFER_ZONE_ORDER_INVALID",
                    message="Stock buffer zones must satisfy TopOfRed <= TopOfYellow <= TopOfGreen.",
                    field_path="Payload.DDMRPConfiguration.StockBufferProfiles",
                )
            )
    for point in ddmrp.get("DecouplingPoints", []):
        if str(point.get("BufferProfileID")) not in stock_profiles:
            errors.append(
                _error(
                    code="REFERENCE_NOT_FOUND",
                    message="DecouplingPoint BufferProfileID does not exist in StockBufferProfiles.",
                    field_path="Payload.DDMRPConfiguration.DecouplingPoints.BufferProfileID",
                )
            )
    for assignment in ddmrp.get("PartProfileAssignments", []):
        if str(assignment.get("BufferProfileID")) not in stock_profiles:
            errors.append(
                _error(
                    code="REFERENCE_NOT_FOUND",
                    message="PartProfileAssignment BufferProfileID does not exist in StockBufferProfiles.",
                    field_path="Payload.DDMRPConfiguration.PartProfileAssignments.BufferProfileID",
                )
            )


def _pending_references(
    payload: Mapping[str, Any],
    *,
    release_policy_ids: set[str],
    calendar_ids: set[str],
    scheduling_strategy_ids: set[str],
    planning_priority_policy_ids: set[str],
    scheduling_priority_classes: set[str],
) -> list[dict[str, Any]]:
    pending: list[dict[str, Any]] = []
    scheduling = dict(payload["SchedulingConfiguration"])
    _add_pending_reference(
        pending,
        reference_type="SchedulingStrategy",
        reference_id=scheduling.get("SchedulingStrategyID"),
        known_ids=scheduling_strategy_ids,
        field_path="Payload.SchedulingConfiguration.SchedulingStrategyID",
    )
    _add_pending_reference(
        pending,
        reference_type="ReleasePolicy",
        reference_id=scheduling.get("ReleasePolicyVersionID"),
        known_ids=release_policy_ids,
        field_path="Payload.SchedulingConfiguration.ReleasePolicyVersionID",
    )
    for resource in scheduling.get("ResourceSettings", []):
        _add_pending_reference(
            pending,
            reference_type="Calendar",
            reference_id=resource.get("CalendarID"),
            known_ids=calendar_ids,
            field_path="Payload.SchedulingConfiguration.ResourceSettings.CalendarID",
        )
    for part in scheduling.get("PartSchedulingSettings", []):
        _add_pending_reference(
            pending,
            reference_type="SchedulingPriorityClass",
            reference_id=part.get("SchedulingPriorityClass"),
            known_ids=scheduling_priority_classes,
            field_path="Payload.SchedulingConfiguration.PartSchedulingSettings.SchedulingPriorityClass",
        )
    ddmrp = dict(payload["DDMRPConfiguration"])
    _add_pending_reference(
        pending,
        reference_type="PlanningPriorityPolicy",
        reference_id=ddmrp.get("PlanningPriorityPolicyID"),
        known_ids=planning_priority_policy_ids,
        field_path="Payload.DDMRPConfiguration.PlanningPriorityPolicyID",
    )
    return pending


def _add_pending_reference(
    pending: list[dict[str, Any]],
    *,
    reference_type: str,
    reference_id: Any,
    known_ids: set[str],
    field_path: str,
) -> None:
    if reference_id is None:
        return
    if str(reference_id) not in known_ids:
        pending.append(
            {
                "ReferenceType": reference_type,
                "ReferenceID": str(reference_id),
                "Field": field_path,
            }
        )


def _require_reference(
    errors: list[dict[str, Any]],
    *,
    reference_type: str,
    reference_id: Any,
    known_ids: set[str],
    field: str,
) -> None:
    if reference_id is None:
        return
    if str(reference_id) not in known_ids:
        errors.append(
            _reference_error(
                reference_type=reference_type,
                reference_id=str(reference_id),
                field=field,
                message=(
                    f"{reference_type} must exist in the selected MasterDataVersionID."
                ),
            )
        )


def _require_item_location(
    errors: list[dict[str, Any]],
    *,
    item_id: Any,
    location_id: Any,
    item_ids: set[str],
    location_ids: set[str],
    item_location_pairs: set[tuple[str, str]],
    field: str,
) -> None:
    if item_id is not None and str(item_id) not in item_ids:
        errors.append(
            _reference_error(
                reference_type="ItemID",
                reference_id=str(item_id),
                field=f"{field}.ItemID",
                message="ItemID must exist in the selected MasterDataVersionID.",
            )
        )
    if location_id is not None and str(location_id) not in location_ids:
        errors.append(
            _reference_error(
                reference_type="LocationID",
                reference_id=str(location_id),
                field=f"{field}.LocationID",
                message="LocationID must exist in the selected MasterDataVersionID.",
            )
        )
    if (
        item_id is not None
        and location_id is not None
        and str(item_id) in item_ids
        and str(location_id) in location_ids
        and (str(item_id), str(location_id)) not in item_location_pairs
    ):
        errors.append(
            _reference_error(
                reference_type="ItemLocationID",
                reference_id=f"{item_id}@{location_id}",
                field=field,
                message=(
                    "ItemID and LocationID must exist as the same item-location pair "
                    "in the selected MasterDataVersionID."
                ),
            )
        )


def _reference_error(
    *,
    reference_type: str,
    reference_id: str,
    field: str,
    message: str,
    evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    error: dict[str, Any] = {
        "Code": "REFERENCE_NOT_FOUND",
        "Message": message,
        "Field": field,
        "ReferenceType": reference_type,
        "ReferenceID": reference_id,
    }
    if evidence:
        error["Evidence"] = evidence
    return error


def _planning_run_feedback_payload(
    planning_run: Mapping[str, Any],
    *,
    release_authorizations: list[Any],
) -> dict[str, Any]:
    _require_operating_model_freeze(planning_run)
    release_summary = _release_summary(
        planning_run, release_authorizations=release_authorizations
    )
    buffer_summary = _buffer_summary(planning_run)
    data_issues = _data_coverage_issues(planning_run)
    return {
        "FeedbackType": "PlanningRunFeedback",
        "PlanningRunID": str(planning_run["RunID"]),
        "OperatingModelConfigurationID": str(
            planning_run["OperatingModelConfigurationID"]
        ),
        "OperatingModelFingerprint": str(planning_run["OperatingModelFingerprint"]),
        "MasterDataVersionID": str(planning_run["MasterDataVersionID"]),
        "OperationalStateSnapshotID": str(planning_run["OperationalStateSnapshotID"]),
        "RunStatus": _feedback_run_status(str(planning_run.get("Status", "Queued"))),
        "RunStartedAt": planning_run.get("StartedAt"),
        "RunCompletedAt": planning_run.get("CompletedAt"),
        "SolverStatus": _feedback_solver_status(planning_run.get("SolverStatus")),
        "ScheduleFingerprint": planning_run.get("ScheduleFingerprint"),
        "ReleaseSummary": release_summary,
        "BufferSummary": buffer_summary,
        "DispatchSummary": _dispatch_summary(planning_run),
        "OperationalMetrics": {
            "MetricSetID": "DDOM-FLOW-METRICS-V1",
            "OverallStatus": "Yellow" if data_issues else "Green",
            "OverallScore": 80.0 if data_issues else 100.0,
        },
        "DataCoverageIssues": data_issues,
    }


def _variance_feedback_payload(
    planning_run: Mapping[str, Any],
    *,
    generated_at: datetime,
) -> dict[str, Any]:
    _require_operating_model_freeze(planning_run)
    data_issues = _data_coverage_issues(planning_run)
    status = "Yellow" if data_issues else "Green"
    metric_categories = [
        _metric_category(
            category_id="Reliability",
            name="Operational reliability",
            status=status,
            metric_id="ScheduledReleaseRate",
            metric_name="Scheduled release readiness",
            value=_safe_ratio(
                _release_summary(planning_run, release_authorizations=[])[
                    "ReadyCount"
                ],
                _release_summary(planning_run, release_authorizations=[])[
                    "CandidateCount"
                ],
            ),
            unit="Percent",
            coverage="Partial" if data_issues else "Available",
        ),
        _metric_category(
            category_id="Stability",
            name="Operational stability",
            status=status,
            metric_id="RedBufferShare",
            metric_name="Red and late buffer share",
            value=_safe_ratio(
                _buffer_summary(planning_run)["Red"]
                + _buffer_summary(planning_run)["Late"],
                _buffer_summary(planning_run)["Total"],
            ),
            unit="Percent",
            coverage="Partial" if data_issues else "Available",
        ),
        _metric_category(
            category_id="Speed",
            name="Operational speed",
            status=status,
            metric_id="DispatchableOperationCount",
            metric_name="Dispatchable operation count",
            value=float(_dispatch_summary(planning_run)["DispatchableOperationCount"]),
            unit="Count",
            coverage="Partial" if data_issues else "Available",
        ),
    ]
    return {
        "FeedbackType": "VarianceAnalysisFeedback",
        "FeedbackPackageID": f"VAR-{planning_run['RunID']}",
        "PlanningRunID": str(planning_run["RunID"]),
        "OperatingModelConfigurationID": str(
            planning_run["OperatingModelConfigurationID"]
        ),
        "OperatingModelFingerprint": str(planning_run["OperatingModelFingerprint"]),
        "MasterDataVersionID": str(planning_run["MasterDataVersionID"]),
        "OperationalStateSnapshotID": str(planning_run["OperationalStateSnapshotID"]),
        "FeedbackGeneratedAt": generated_at.isoformat(),
        "MetricSetID": "DDOM-FLOW-METRICS-V1",
        "OverallStatus": status,
        "ReliabilityStatus": status,
        "StabilityStatus": status,
        "SpeedStatus": status,
        "MetricCategories": metric_categories,
        "RecommendedDDSOPReviewTopics": [],
        "DataCoverageIssues": data_issues,
    }


def _metric_category(
    *,
    category_id: str,
    name: str,
    status: str,
    metric_id: str,
    metric_name: str,
    value: float | None,
    unit: str,
    coverage: str,
) -> dict[str, Any]:
    return {
        "CategoryID": category_id,
        "Name": name,
        "Status": status,
        "Score": value,
        "Metrics": [
            {
                "MetricID": metric_id,
                "Name": metric_name,
                "Value": value,
                "Unit": unit,
                "Status": status,
                "DataCoverage": coverage,
            }
        ],
    }


def _require_operating_model_freeze(planning_run: Mapping[str, Any]) -> None:
    for key in (
        "OperatingModelConfigurationID",
        "OperatingModelFingerprint",
        "SchedulingConfigurationID",
        "DDMRPConfigurationID",
    ):
        if not planning_run.get(key):
            raise ValueError(f"Planning run is missing frozen {key}.")


def _release_summary(
    planning_run: Mapping[str, Any],
    *,
    release_authorizations: list[Any],
) -> dict[str, int]:
    recommendations = _release_recommendations(planning_run)
    ready = 0
    blocked = 0
    for item in recommendations:
        blocked_reasons = item.get("BlockedReasons") or item.get("BlockingReasons")
        if blocked_reasons:
            blocked += 1
        else:
            ready += 1
    authorized = sum(
        1
        for authorization in release_authorizations
        if getattr(authorization, "run_id", None) == planning_run.get("RunID")
        or (
            isinstance(authorization, Mapping)
            and authorization.get("RunID") == planning_run.get("RunID")
        )
    )
    return {
        "CandidateCount": len(recommendations),
        "ReadyCount": ready,
        "AuthorizedCount": authorized,
        "BlockedCount": blocked,
    }


def _buffer_summary(planning_run: Mapping[str, Any]) -> dict[str, int]:
    summary = {"Total": 0, "Green": 0, "Yellow": 0, "Red": 0, "Late": 0}
    for item in _release_recommendations(planning_run):
        zone = str(
            item.get("BufferZone")
            or item.get("Zone")
            or item.get("BufferStatus")
            or ""
        )
        normalized = zone.capitalize()
        if normalized in summary and normalized != "Total":
            summary[normalized] += 1
        summary["Total"] += 1
    return summary


def _dispatch_summary(planning_run: Mapping[str, Any]) -> dict[str, int]:
    dispatch = planning_run.get("DispatchSummary")
    if isinstance(dispatch, Mapping):
        return {
            "DispatchableOperationCount": int(
                dispatch.get("DispatchableOperationCount", 0)
            ),
            "ReplanSuggestionCount": int(dispatch.get("ReplanSuggestionCount", 0)),
            "QueueJumpSuggestionCount": int(
                dispatch.get("QueueJumpSuggestionCount", 0)
            ),
        }
    return {
        "DispatchableOperationCount": 0,
        "ReplanSuggestionCount": 0,
        "QueueJumpSuggestionCount": 0,
    }


def _release_recommendations(planning_run: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    schedule = planning_run.get("Schedule")
    if not isinstance(schedule, Mapping):
        return []
    recommendations = schedule.get("ReleaseRecommendations")
    if isinstance(recommendations, list):
        return [item for item in recommendations if isinstance(item, Mapping)]
    work_orders = schedule.get("WorkOrders")
    if isinstance(work_orders, list):
        return [item for item in work_orders if isinstance(item, Mapping)]
    return []


def _data_coverage_issues(planning_run: Mapping[str, Any]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    if not isinstance(planning_run.get("Schedule"), Mapping):
        issues.append(
            {
                "Code": "SCHEDULE_UNAVAILABLE",
                "Message": "Planning run has no schedule output.",
                "Severity": "Warning",
            }
        )
    if not planning_run.get("ScheduleFingerprint"):
        issues.append(
            {
                "Code": "SCHEDULE_FINGERPRINT_UNAVAILABLE",
                "Message": "Schedule fingerprint is not available in the current run record.",
                "Severity": "Info",
            }
        )
    return issues


def _feedback_run_status(status: str) -> str:
    mapping = {
        "Pending": "Queued",
        "Queued": "Queued",
        "Running": "Running",
        "Completed": "Completed",
        "Failed": "Failed",
        "Canceled": "Canceled",
        "Cancelled": "Canceled",
        "DeadLettered": "DeadLettered",
        "DeadLetter": "DeadLettered",
    }
    return mapping.get(status, "Failed")


def _feedback_solver_status(status: Any) -> str:
    mapping = {
        None: "NotRun",
        "Optimal": "Optimal",
        "Feasible": "Feasible",
        "Infeasible": "Infeasible",
        "Error": "Failed",
        "Failed": "Failed",
        "Unavailable": "Failed",
    }
    return mapping.get(status, "Failed")


def _safe_ratio(numerator: int, denominator: int) -> float | None:
    if denominator <= 0:
        return None
    return round((numerator / denominator) * 100.0, 2)
