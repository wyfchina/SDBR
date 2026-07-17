"""Acceptance evidence for BE-DDMRP-007 and BE-INT-008."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime
import json

import pytest

from sdbr.ddsop_contracts import DEFAULT_CONTRACT_ROOT, canonical_operating_model_fingerprint
from sdbr.ddsop_runtime_planning_input import (
    build_bounded_scheduling_input_from_package,
    correlate_runtime_package_feedback_delivery,
    ensure_package_can_create_planning_run,
    evaluate_ddmrp_runtime_signals_from_package,
    freeze_runtime_package_into_planning_run,
    process_runtime_planning_input_message,
    record_runtime_feedback_correlations,
    record_runtime_planning_input_processing_result,
)
from sdbr.environment_paths import resolve_ddae_interface_contract_root
from sdbr.state_store import WorkbenchStateStore


CONTRACT_ROOT = resolve_ddae_interface_contract_root()
RUNTIME_EXAMPLE = (
    CONTRACT_ROOT
    / "contracts"
    / "ddsop-runtime-planning-input-v1"
    / "examples"
    / "golden-runtime-planning-input.json"
)
RECEIVED_AT = datetime.fromisoformat("2026-06-30T09:05:00+08:00")


def test_runtime_planning_input_accepts_schema_and_semantic_positive_case() -> None:
    message = _runtime_message(status="AcceptedForBoundedPlanning")
    accepted_config = _accepted_configuration_for(message)

    result = process_runtime_planning_input_message(
        message,
        received_at=RECEIVED_AT,
        accepted_configurations={
            accepted_config["Payload"]["OperatingModelConfigurationID"]: accepted_config
        },
        contract_root=DEFAULT_CONTRACT_ROOT,
    )

    assert result.processing_status == "Accepted"
    assert result.errors == []
    assert result.package_record is not None
    assert result.package_record["UsableForPlanningRun"] is True
    assert result.package_record["OperatingModelConfigurationID"] == (
        message["Payload"]["FrozenDdsopConfiguration"]["OperatingModelConfigurationID"]
    )


def test_runtime_planning_input_rejects_duplicate_idempotency_key() -> None:
    message = _runtime_message(status="AcceptedForBoundedPlanning")

    result = process_runtime_planning_input_message(
        message,
        received_at=RECEIVED_AT,
        existing_idempotency_keys={message["IdempotencyKey"]},
        accepted_configurations={},
        contract_root=DEFAULT_CONTRACT_ROOT,
    )

    assert result.processing_status == "Duplicate"
    assert result.package_record is None
    assert result.inbound_message_record["ProcessingStatus"] == "Duplicate"


def test_runtime_planning_input_requires_resolved_approved_configuration() -> None:
    message = _runtime_message(status="AcceptedForBoundedPlanning")

    result = process_runtime_planning_input_message(
        message,
        received_at=RECEIVED_AT,
        accepted_configurations={},
        contract_root=DEFAULT_CONTRACT_ROOT,
    )

    assert result.processing_status == "Rejected"
    assert _codes(result.errors) == {"REFERENCE_NOT_FOUND"}


def test_runtime_planning_input_rejects_fingerprint_mismatch() -> None:
    message = _runtime_message(status="AcceptedForBoundedPlanning")
    accepted_config = _accepted_configuration_for(message)
    message["Payload"]["FrozenDdsopConfiguration"]["OperatingModelFingerprint"] = (
        "sha256:" + "0" * 64
    )

    result = process_runtime_planning_input_message(
        message,
        received_at=RECEIVED_AT,
        accepted_configurations={
            accepted_config["Payload"]["OperatingModelConfigurationID"]: accepted_config
        },
        contract_root=DEFAULT_CONTRACT_ROOT,
    )

    assert result.processing_status == "Rejected"
    assert "FINGERPRINT_MISMATCH" in _codes(result.errors)


def test_runtime_planning_input_rejects_missing_parameter_evidence() -> None:
    message = _runtime_message(status="AcceptedForBoundedPlanning")
    accepted_config = _accepted_configuration_for(message)
    refs = message["Payload"]["ParameterAuthorityEvidence"]["ParameterEvidenceRefs"]
    message["Payload"]["ParameterAuthorityEvidence"]["ParameterEvidenceRefs"] = [
        item for item in refs if item["FieldGroup"] != "ADU"
    ]

    result = process_runtime_planning_input_message(
        message,
        received_at=RECEIVED_AT,
        accepted_configurations={
            accepted_config["Payload"]["OperatingModelConfigurationID"]: accepted_config
        },
        contract_root=DEFAULT_CONTRACT_ROOT,
    )

    assert result.processing_status == "Rejected"
    assert "AUTHORITY_EVIDENCE_MISSING" in _codes(result.errors)


def test_runtime_planning_input_rejects_missing_runtime_row_traceability() -> None:
    message = _runtime_message(status="AcceptedForBoundedPlanning")
    accepted_config = _accepted_configuration_for(message)
    message["Payload"]["RuntimeEvidenceSnapshot"]["InventoryPositions"][0][
        "EvidenceRefs"
    ] = []

    result = process_runtime_planning_input_message(
        message,
        received_at=RECEIVED_AT,
        accepted_configurations={
            accepted_config["Payload"]["OperatingModelConfigurationID"]: accepted_config
        },
        contract_root=DEFAULT_CONTRACT_ROOT,
    )

    assert result.processing_status == "Rejected"
    assert _codes(result.errors) & {"RUNTIME_EVIDENCE_MISSING", "REQUIRED_FIELD_MISSING"}


def test_runtime_planning_input_rejects_missing_executable_row_traceability() -> None:
    message = _runtime_message(status="AcceptedForBoundedPlanning")
    accepted_config = _accepted_configuration_for(message)
    message["Payload"]["ExecutableSchedulingInputs"]["WorkOrders"][0][
        "EvidenceRefs"
    ] = []

    result = process_runtime_planning_input_message(
        message,
        received_at=RECEIVED_AT,
        accepted_configurations={
            accepted_config["Payload"]["OperatingModelConfigurationID"]: accepted_config
        },
        contract_root=DEFAULT_CONTRACT_ROOT,
    )

    assert result.processing_status == "Rejected"
    assert _codes(result.errors) & {
        "EXECUTABLE_SCHEDULING_INPUT_MISSING",
        "REQUIRED_FIELD_MISSING",
    }


def test_runtime_planning_input_rejects_invalid_numeric_values_by_schema() -> None:
    message = _runtime_message(status="AcceptedForBoundedPlanning")
    message["Payload"]["RuntimeEvidenceSnapshot"]["InventoryPositions"][0][
        "OnHandQty"
    ] = -1

    result = process_runtime_planning_input_message(
        message,
        received_at=RECEIVED_AT,
        accepted_configurations={},
        contract_root=DEFAULT_CONTRACT_ROOT,
    )

    assert result.processing_status == "Rejected"
    assert "INVALID_NUMERIC_VALUE" in _codes(result.errors)


def test_runtime_planning_input_rejects_ambiguous_spike_semantics() -> None:
    message = _runtime_message(status="AcceptedForBoundedPlanning")
    accepted_config = _accepted_configuration_for(message)
    demand = message["Payload"]["RuntimeEvidenceSnapshot"]["DemandSignals"][0]
    demand["DemandType"] = "SpikeCandidate"
    demand["SpikeQualificationStatus"] = "NotApplicable"
    demand["SpikeQualificationMode"] = "NotApplicable"
    demand["SpikeQualificationEvidenceID"] = None

    result = process_runtime_planning_input_message(
        message,
        received_at=RECEIVED_AT,
        accepted_configurations={
            accepted_config["Payload"]["OperatingModelConfigurationID"]: accepted_config
        },
        contract_root=DEFAULT_CONTRACT_ROOT,
    )

    assert result.processing_status == "Rejected"
    assert "SPIKE_QUALIFICATION_AMBIGUOUS" in _codes(result.errors)


def test_planning_run_gate_rejects_reviewed_package_and_freezes_accepted_package() -> None:
    reviewed_message = _runtime_message(status="Reviewed")
    reviewed_package = _accepted_result(reviewed_message).package_record
    assert reviewed_package is not None

    errors = ensure_package_can_create_planning_run(reviewed_package)
    assert errors[0]["Code"] == "INVALID_STATE_TRANSITION"

    accepted_message = _runtime_message(status="AcceptedForBoundedPlanning")
    package = _accepted_result(accepted_message).package_record
    assert package is not None
    frozen = freeze_runtime_package_into_planning_run(
        {
            "RunID": "TST-RUN-RPI-001",
            "ProblemID": "TST-PROBLEM-RPI-001",
            "Status": "Pending",
        },
        package,
    )

    assert frozen["RuntimePlanningInputPackageID"] == package["RuntimePlanningInputPackageID"]
    assert frozen["OperatingModelConfigurationID"] == package["OperatingModelConfigurationID"]
    assert frozen["ContractPath"] == "DDSOP-RUNTIME-PLANNING-INPUT-V1"
    assert frozen["LegacyPlanningRunPath"] is False


def test_ddmrp_runtime_adapter_consumes_frozen_parameters_and_runtime_evidence() -> None:
    message = _runtime_message(status="AcceptedForBoundedPlanning")
    accepted_config = _accepted_configuration_for(message)
    package = _accepted_result(message).package_record
    assert package is not None

    result = evaluate_ddmrp_runtime_signals_from_package(
        package,
        accepted_config,
        evaluated_at=datetime.fromisoformat("2026-06-30T09:00:00+08:00"),
    )

    assert result["RuntimePlanningInputPackageID"] == package["RuntimePlanningInputPackageID"]
    assert result["Summary"]["DecouplingPointCount"] == 1
    assert result["Summary"]["LineCount"] == 1
    assert "DDAE-governed DDMRP master settings" in result["Boundary"]


@pytest.mark.parametrize(
    ("quality_state", "available_qty"),
    [
        ("Unrestricted", 34),
        ("Inspection", 0),
        ("Blocked", 0),
        ("Released", 34),
    ],
)
def test_be_ddmrp_007_consumes_authority_available_qty_without_quality_reinterpretation(
    quality_state: str,
    available_qty: int,
) -> None:
    message = _runtime_message(status="AcceptedForBoundedPlanning")
    inventory = message["Payload"]["RuntimeEvidenceSnapshot"]["InventoryPositions"][0]
    inventory.update(
        {
            "OnHandQty": 42,
            "AllocatedQty": 8,
            "AvailableQty": available_qty,
            "QualityState": quality_state,
        }
    )
    accepted_config = _accepted_configuration_for(message)
    processed = process_runtime_planning_input_message(
        message,
        received_at=RECEIVED_AT,
        accepted_configurations={
            accepted_config["Payload"]["OperatingModelConfigurationID"]: accepted_config
        },
        contract_root=DEFAULT_CONTRACT_ROOT,
    )
    assert processed.processing_status == "Accepted"
    assert processed.package_record is not None

    result = evaluate_ddmrp_runtime_signals_from_package(
        processed.package_record,
        accepted_config,
        evaluated_at=datetime.fromisoformat("2026-06-30T09:00:00+08:00"),
    )
    line = result["Lines"][0]
    assert line["QualifiedOnHandQty"] == available_qty
    assert line["OnHandQty"] == available_qty
    assert line["PhysicalOnHandQty"] == 42
    assert line["AuthorityAllocatedQty"] == 8
    assert line["AuthorityAvailableQty"] == available_qty
    assert line["QualityState"] == quality_state
    assert line["Uom"] == inventory["UnitOfMeasure"]


def test_be_ddmrp_007_preserves_contract_demand_supply_ids_and_uom() -> None:
    message = _runtime_message(status="AcceptedForBoundedPlanning")
    runtime = message["Payload"]["RuntimeEvidenceSnapshot"]
    demand = runtime["DemandSignals"][0]
    supply = runtime["OpenSupplySignals"][0]
    demand["DueAt"] = "2026-06-30T17:00:00+08:00"
    accepted_config = _accepted_configuration_for(message)
    processed = process_runtime_planning_input_message(
        message,
        received_at=RECEIVED_AT,
        accepted_configurations={
            accepted_config["Payload"]["OperatingModelConfigurationID"]: accepted_config
        },
        contract_root=DEFAULT_CONTRACT_ROOT,
    )
    assert processed.processing_status == "Accepted"
    assert processed.package_record is not None

    result = evaluate_ddmrp_runtime_signals_from_package(
        processed.package_record,
        accepted_config,
        evaluated_at=datetime.fromisoformat("2026-06-30T09:00:00+08:00"),
    )
    line = result["Lines"][0]
    assert line["DemandComponents"][0]["DemandID"] == demand["DemandID"]
    assert line["DemandComponents"][0]["Uom"] == demand["UnitOfMeasure"]
    assert line["SupplyComponents"][0]["SupplyID"] == supply["SupplyID"]
    assert line["SupplyComponents"][0]["Uom"] == supply["UnitOfMeasure"]
    assert line["Uom"] == runtime["InventoryPositions"][0]["UnitOfMeasure"]
    assert "StandardTargetReceiptAt" not in line


def test_be_ddmrp_007_rejects_runtime_spike_without_accepted_threshold_authority() -> None:
    from sdbr.ddsop_runtime_planning_input import DdmrpRuntimeAuthorityError

    message = _runtime_message(status="AcceptedForBoundedPlanning")
    demand = message["Payload"]["RuntimeEvidenceSnapshot"]["DemandSignals"][0]
    demand.update(
        {
            "DemandType": "SpikeCandidate",
            "SpikeQualificationStatus": "RequiresSDBRQualification",
            "SpikeQualificationMode": "CalculatedBySDBR",
            "SpikeQualificationEvidenceID": None,
        }
    )
    accepted_config = _accepted_configuration_for(message)
    processed = process_runtime_planning_input_message(
        message,
        received_at=RECEIVED_AT,
        accepted_configurations={
            accepted_config["Payload"]["OperatingModelConfigurationID"]: accepted_config
        },
        contract_root=DEFAULT_CONTRACT_ROOT,
    )
    assert processed.processing_status == "Accepted"
    assert processed.package_record is not None

    with pytest.raises(DdmrpRuntimeAuthorityError) as error:
        evaluate_ddmrp_runtime_signals_from_package(
            processed.package_record,
            accepted_config,
            evaluated_at=datetime.fromisoformat("2026-06-30T09:00:00+08:00"),
        )

    assert error.value.code == "SPIKE_QUALIFICATION_INPUT_INSUFFICIENT"
    assert error.value.status == "DdmrpRuntimeAuthorityError"


def test_be_ddmrp_003_keeps_ddsop_qualified_spike_beyond_plain_dlt() -> None:
    message = _runtime_message(status="AcceptedForBoundedPlanning")
    demand = message["Payload"]["RuntimeEvidenceSnapshot"]["DemandSignals"][0]
    demand.update(
        {
            "DueAt": "2026-07-31T09:00:00+08:00",
            "DemandType": "SpikeCandidate",
            "SpikeQualificationStatus": "QualifiedByDDSOP",
            "SpikeQualificationMode": "ProvidedByDDSOP",
            "SpikeQualificationEvidenceID": "DDSOP-SPIKE-EVIDENCE-001",
        }
    )
    accepted_config = _accepted_configuration_for(message)
    processed = process_runtime_planning_input_message(
        message,
        received_at=RECEIVED_AT,
        accepted_configurations={
            accepted_config["Payload"]["OperatingModelConfigurationID"]: accepted_config
        },
        contract_root=DEFAULT_CONTRACT_ROOT,
    )
    assert processed.processing_status == "Accepted"
    assert processed.package_record is not None

    result = evaluate_ddmrp_runtime_signals_from_package(
        processed.package_record,
        accepted_config,
        evaluated_at=datetime.fromisoformat("2026-06-30T09:00:00+08:00"),
    )

    assert result["Lines"][0]["QualifiedDemandQty"] == demand["Quantity"]


@pytest.mark.parametrize("mismatch_source", ["buffer", "demand", "supply"])
def test_be_ddmrp_006_rejects_incompatible_item_location_uom(
    mismatch_source: str,
) -> None:
    from sdbr.ddsop_runtime_planning_input import DdmrpRuntimeAuthorityError

    message = _runtime_message(status="AcceptedForBoundedPlanning")
    accepted_config = _accepted_configuration_for(message)
    if mismatch_source == "buffer":
        accepted_config["Payload"]["DDMRPConfiguration"]["StockBufferProfiles"][0][
            "UnitOfMeasure"
        ] = "KG"
        accepted_config["Payload"]["Fingerprint"] = canonical_operating_model_fingerprint(
            accepted_config["Payload"]
        )
        message["Payload"]["FrozenDdsopConfiguration"]["OperatingModelFingerprint"] = (
            accepted_config["Payload"]["Fingerprint"]
        )
    elif mismatch_source == "demand":
        message["Payload"]["RuntimeEvidenceSnapshot"]["DemandSignals"][0][
            "UnitOfMeasure"
        ] = "KG"
    else:
        message["Payload"]["RuntimeEvidenceSnapshot"]["OpenSupplySignals"][0][
            "UnitOfMeasure"
        ] = "KG"

    processed = process_runtime_planning_input_message(
        message,
        received_at=RECEIVED_AT,
        accepted_configurations={
            accepted_config["Payload"]["OperatingModelConfigurationID"]: accepted_config
        },
        contract_root=DEFAULT_CONTRACT_ROOT,
    )
    assert processed.processing_status == "Accepted"
    assert processed.package_record is not None

    with pytest.raises(DdmrpRuntimeAuthorityError) as error:
        evaluate_ddmrp_runtime_signals_from_package(
            processed.package_record,
            accepted_config,
            evaluated_at=datetime.fromisoformat("2026-06-30T09:00:00+08:00"),
        )

    assert error.value.code == "REFERENCE_NOT_FOUND"
    assert "UnitOfMeasure" in str(error.value)


def test_bounded_scheduling_adapter_uses_explicit_executable_rows_only() -> None:
    message = _runtime_message(status="AcceptedForBoundedPlanning")
    package = _accepted_result(message).package_record
    assert package is not None

    bounded = build_bounded_scheduling_input_from_package(package)

    assert bounded["RuntimePlanningInputPackageID"] == package["RuntimePlanningInputPackageID"]
    assert bounded["WorkOrders"]
    assert bounded["Routings"]
    assert bounded["Operations"]
    assert bounded["ResourceCalendars"]
    assert "no missing routing" in bounded["Boundary"]


def test_bounded_scheduling_adapter_rejects_unresolved_resource_reference() -> None:
    message = _runtime_message(status="AcceptedForBoundedPlanning")
    package = _accepted_result(message).package_record
    assert package is not None
    package = deepcopy(package)
    package["Payload"]["ExecutableSchedulingInputs"]["Operations"][0][
        "ResourceID"
    ] = "MISSING_RESOURCE"

    with pytest.raises(ValueError):
        build_bounded_scheduling_input_from_package(package)


def test_delivery_ledger_correlation_links_runtime_package_to_feedback_messages() -> None:
    message = _runtime_message(status="AcceptedForBoundedPlanning")
    package = _accepted_result(message).package_record
    assert package is not None

    records = correlate_runtime_package_feedback_delivery(
        package,
        [
            {
                "MessageID": "SDBR-MSG-PLANNING-FEEDBACK-001",
                "IdempotencyKey": "SDBR:SDBR-MSG-PLANNING-FEEDBACK-001",
                "Payload": {"PlanningRunID": "TST-RUN-RPI-001"},
            },
            {
                "MessageID": "SDBR-MSG-VARIANCE-FEEDBACK-001",
                "IdempotencyKey": "SDBR:SDBR-MSG-VARIANCE-FEEDBACK-001",
                "Payload": {"PlanningRunID": "TST-RUN-RPI-001"},
            },
        ],
        delivered_at=RECEIVED_AT,
    )

    assert len(records) == 2
    assert {record["CorrelationStatus"] for record in records} == {"Linked"}
    assert records[0]["RuntimePlanningInputPackageID"] == package["RuntimePlanningInputPackageID"]
    assert records[0]["DeliveryLedgerCorrelationID"] == (
        package["DeliveryLedgerCorrelationID"]
    )


def test_runtime_package_and_feedback_correlation_are_recorded_in_store_ledgers() -> None:
    message = _runtime_message(status="AcceptedForBoundedPlanning")
    result = _accepted_result(message)
    package = result.package_record
    assert package is not None
    store = WorkbenchStateStore()

    record_runtime_planning_input_processing_result(store, result)
    correlations = correlate_runtime_package_feedback_delivery(
        package,
        [
            {
                "MessageID": "SDBR-MSG-PLANNING-FEEDBACK-LEDGER",
                "IdempotencyKey": "SDBR:SDBR-MSG-PLANNING-FEEDBACK-LEDGER",
                "Payload": {"PlanningRunID": "TST-RUN-RPI-LEDGER"},
            }
        ],
        delivered_at=RECEIVED_AT,
    )
    record_runtime_feedback_correlations(store, correlations)

    assert len(store.ddsop_runtime_planning_input_messages) == 1
    assert package["RuntimePlanningInputPackageID"] in (
        store.ddsop_runtime_planning_input_packages
    )
    assert store.ddsop_runtime_feedback_correlations[0]["CorrelationStatus"] == "Linked"


def _accepted_result(message: dict[str, object]):
    accepted_config = _accepted_configuration_for(message)
    return process_runtime_planning_input_message(
        message,
        received_at=RECEIVED_AT,
        accepted_configurations={
            accepted_config["Payload"]["OperatingModelConfigurationID"]: accepted_config
        },
        contract_root=DEFAULT_CONTRACT_ROOT,
    )


def _runtime_message(*, status: str) -> dict[str, object]:
    message = json.loads(RUNTIME_EXAMPLE.read_text(encoding="utf-8-sig"))
    message["Payload"]["PackageIdentity"]["PackageStatus"] = status
    _make_executable_rows_fully_explicit(message)
    accepted_config = _accepted_configuration_for(message, update_message=False)
    message["Payload"]["FrozenDdsopConfiguration"]["OperatingModelFingerprint"] = (
        accepted_config["Payload"]["Fingerprint"]
    )
    return message


def _make_executable_rows_fully_explicit(message: dict[str, object]) -> None:
    executable = message["Payload"]["ExecutableSchedulingInputs"]
    calendars = executable["ResourceCalendars"]
    calendar_by_resource = {row["ResourceID"]: row for row in calendars}
    template = calendars[0]
    for operation in executable["Operations"]:
        resource_id = operation["ResourceID"]
        if resource_id in calendar_by_resource:
            continue
        row = deepcopy(template)
        row["ResourceID"] = resource_id
        row["CalendarID"] = f"CAL-{resource_id}"
        row["EvidenceRefs"] = [
            {
                "EvidenceID": f"PUBLIC-DEMO-CALENDAR-{resource_id}",
                "SourceAuthority": "SDBR public demo positive fixture explicit calendar row",
                "SourceRecordID": f"CAL-{resource_id}",
                "SourceObservedAt": "2026-06-30T08:30:00+08:00",
            }
        ]
        calendars.append(row)


def _accepted_configuration_for(
    message: dict[str, object],
    *,
    update_message: bool = True,
) -> dict[str, object]:
    payload = message["Payload"]
    frozen = payload["FrozenDdsopConfiguration"]
    runtime = payload["RuntimeEvidenceSnapshot"]
    inventory = runtime["InventoryPositions"][0]
    item_id = inventory["ItemID"]
    location_id = inventory["LocationID"]
    configuration = {
        "OperatingModelConfigurationID": frozen["OperatingModelConfigurationID"],
        "ConfigurationVersion": frozen["ConfigurationVersion"],
        "Status": frozen["ConfigStatus"],
        "EffectiveFrom": frozen["EffectiveFrom"],
        "EffectiveTo": frozen["EffectiveTo"],
        "TimeZone": frozen["TimeZone"],
        "SchedulingConfiguration": {
            "SchedulingConfigurationID": frozen["SchedulingConfigurationID"],
            "ControlPoints": [
                {
                    "ControlPointID": "CP-PUBLIC-DEMO-QA",
                    "ResourceID": "QA-CONTROL-POINT",
                }
            ],
        },
        "DDMRPConfiguration": {
            "DDMRPConfigurationID": frozen["DDMRPConfigurationID"],
            "DecouplingPoints": [
                {
                    "ItemID": item_id,
                    "LocationID": location_id,
                    "BufferProfileID": "BP-PART-FPGA-SPACE",
                    "DLTMinutes": 5760,
                    "OrderMultipleQty": 1,
                    "MinimumOrderQty": 1,
                }
            ],
            "StockBufferProfiles": [
                {
                    "BufferProfileID": "BP-PART-FPGA-SPACE",
                    "TopOfRed": 20,
                    "TopOfYellow": 60,
                    "TopOfGreen": 100,
                    "UnitOfMeasure": inventory["UnitOfMeasure"],
                }
            ],
        },
    }
    configuration["Fingerprint"] = canonical_operating_model_fingerprint(configuration)
    if update_message:
        frozen["OperatingModelFingerprint"] = configuration["Fingerprint"]
    return {"Payload": configuration}


def _codes(errors: list[dict[str, object]]) -> set[str]:
    return {str(error["Code"]) for error in errors}
