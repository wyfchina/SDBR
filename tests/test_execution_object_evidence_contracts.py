from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path

from jsonschema import Draft202012Validator

from sdbr.execution_object_evidence_contracts import (
    ExecutionObjectReferenceResolver,
    ack_schema,
    default_reviewed_fixture_resolver,
    evidence_schema,
    process_execution_object_evidence_message,
)
from sdbr.state_store import SQLiteWorkbenchStateStore


CONTRACT_ROOT = Path(r"D:\Documents\DDAE_INTERFACE_CONTRACT")
CONTRACT_DIR = CONTRACT_ROOT / "contracts" / "sdbr-execution-object-evidence-v1"


def test_reviewed_execution_object_example_is_accepted_as_controlled_context_only() -> None:
    message = _load_example("sub-avionics-compute-part-fpga-space-reviewed.json")

    result = process_execution_object_evidence_message(
        message,
        received_at=_received_at(),
        reference_resolver=default_reviewed_fixture_resolver(),
    )

    assert result.ack["AckStatus"] == "Accepted"
    assert result.ack["ErrorCode"] is None
    assert result.accepted_evidence is not None
    assert result.accepted_evidence["WorkOrderID"] == "WO-SUB-AVIONICS-COMPUTE-001"
    assert result.accepted_evidence["RoutingID"] == "SDBR-ROUTE-SUB-AVIONICS-COMPUTE-001"
    assert result.accepted_evidence["MaterialIssueCount"] == 0
    assert result.accepted_evidence["MaterialConsumptionCount"] == 0
    assert result.accepted_evidence["SourceAuthoritativeUsable"] is False
    assert "Not ProductionValidated" in result.accepted_evidence["NonClaims"]
    assert "Not Business Golden Loop readiness" in result.accepted_evidence["NonClaims"]


def test_schema_accepts_evidence_and_ack_examples_and_generated_ack() -> None:
    message = _load_example("sub-avionics-compute-part-fpga-space-reviewed.json")
    Draft202012Validator(evidence_schema()).validate(message)
    for filename in (
        "ack-accepted-reviewed.json",
        "rejected-ddae-routing-as-executable.json",
        "deadletter-idempotency-conflict.json",
    ):
        Draft202012Validator(ack_schema()).validate(_load_example(filename))

    result = process_execution_object_evidence_message(
        message,
        received_at=_received_at(),
        reference_resolver=default_reviewed_fixture_resolver(),
    )

    Draft202012Validator(ack_schema()).validate(result.ack)
    assert result.ack["ConsumerSystem"] == "DDAE"


def test_identical_replay_is_duplicate_safe() -> None:
    message = _load_example("sub-avionics-compute-part-fpga-space-reviewed.json")
    first = process_execution_object_evidence_message(
        message,
        received_at=_received_at(),
        reference_resolver=default_reviewed_fixture_resolver(),
    )

    replay = process_execution_object_evidence_message(
        message,
        received_at=_received_at(),
        existing_ledger_records=[first.inbound_ledger_record],
        reference_resolver=default_reviewed_fixture_resolver(),
    )

    assert replay.ack["AckStatus"] == "Duplicate"
    assert replay.ack["ErrorCode"] is None


def test_idempotency_conflict_is_dead_lettered() -> None:
    message = _load_example("sub-avionics-compute-part-fpga-space-reviewed.json")
    first = process_execution_object_evidence_message(
        message,
        received_at=_received_at(),
        reference_resolver=default_reviewed_fixture_resolver(),
    )
    conflicting = deepcopy(message)
    conflicting["Payload"]["WorkOrder"]["RemainingQty"] = 0

    result = process_execution_object_evidence_message(
        conflicting,
        received_at=_received_at(),
        existing_ledger_records=[first.inbound_ledger_record],
        reference_resolver=default_reviewed_fixture_resolver(),
    )

    assert result.ack["AckStatus"] == "DeadLettered"
    assert result.ack["ErrorCode"] == "IDEMPOTENCY_CONFLICT"


def test_ddae_routing_semantics_are_rejected_as_executable_routing() -> None:
    message = _load_example("sub-avionics-compute-part-fpga-space-reviewed.json")
    message["Payload"]["Routing"]["RoutingAuthority"] = "DDAE_PRIMARY_ROUTING"

    result = process_execution_object_evidence_message(
        message,
        received_at=_received_at(),
        reference_resolver=default_reviewed_fixture_resolver(),
    )

    assert result.ack["AckStatus"] == "Rejected"
    assert result.ack["ErrorCode"] == "UNKNOWN_ROUTING"


def test_missing_work_order_id_is_rejected_with_specific_error_code() -> None:
    message = _load_example("sub-avionics-compute-part-fpga-space-reviewed.json")
    message["Payload"]["WorkOrder"].pop("WorkOrderID")

    result = process_execution_object_evidence_message(
        message,
        received_at=_received_at(),
        reference_resolver=default_reviewed_fixture_resolver(),
    )

    assert result.ack["AckStatus"] == "Rejected"
    assert result.ack["ErrorCode"] == "MISSING_WORK_ORDER"


def test_unknown_work_order_is_dead_lettered() -> None:
    message = _load_example("sub-avionics-compute-part-fpga-space-reviewed.json")

    result = process_execution_object_evidence_message(
        message,
        received_at=_received_at(),
        reference_resolver=ExecutionObjectReferenceResolver(
            work_order_ids={"OTHER-WO"},
            routing_ids={"SDBR-ROUTE-SUB-AVIONICS-COMPUTE-001"},
            operation_ids={"OP-INSTALL-FPGA-SPACE-001"},
            resource_ids={"RES-AVIONICS-BENCH-001"},
            work_center_ids={"WC-AVIONICS-ASSEMBLY"},
            product_ids={"SUB-AVIONICS-COMPUTE"},
            item_ids={"SUB-AVIONICS-COMPUTE", "PART-FPGA-SPACE"},
            location_ids={"ASSY-LINE-AVIONICS", "WH-ELEC-QA"},
            uoms={"EA"},
        ),
    )

    assert result.ack["AckStatus"] == "DeadLettered"
    assert result.ack["ErrorCode"] == "UNKNOWN_WORK_ORDER"


def test_missing_planning_run_id_is_rejected_with_specific_error_code() -> None:
    message = _load_example("sub-avionics-compute-part-fpga-space-reviewed.json")
    message["Payload"]["PlanningContext"].pop("PlanningRunID")

    result = process_execution_object_evidence_message(
        message,
        received_at=_received_at(),
        reference_resolver=default_reviewed_fixture_resolver(),
    )

    assert result.ack["AckStatus"] == "Rejected"
    assert result.ack["ErrorCode"] == "MISSING_PLANNING_RUN"


def test_missing_frozen_config_is_dead_lettered() -> None:
    message = _load_example("sub-avionics-compute-part-fpga-space-reviewed.json")
    message["Payload"]["PlanningContext"]["SchedulingConfigurationID"] = "SCH-OTHER"

    result = process_execution_object_evidence_message(
        message,
        received_at=_received_at(),
        reference_resolver=default_reviewed_fixture_resolver(),
    )

    assert result.ack["AckStatus"] == "DeadLettered"
    assert result.ack["ErrorCode"] == "FROZEN_CONFIG_MISMATCH"


def test_operation_sequence_mismatch_is_rejected() -> None:
    message = _load_example("sub-avionics-compute-part-fpga-space-reviewed.json")
    message["Payload"]["Operations"][0]["OperationSequence"] = 20

    result = process_execution_object_evidence_message(
        message,
        received_at=_received_at(),
        reference_resolver=default_reviewed_fixture_resolver(),
    )

    assert result.ack["AckStatus"] == "Rejected"
    assert result.ack["ErrorCode"] == "OPERATION_SEQUENCE_INVALID"


def test_material_requirement_is_not_issue_or_consumption_proof() -> None:
    message = _load_example("sub-avionics-compute-part-fpga-space-reviewed.json")

    result = process_execution_object_evidence_message(
        message,
        received_at=_received_at(),
        reference_resolver=default_reviewed_fixture_resolver(),
    )

    assert result.ack["AckStatus"] == "Accepted"
    assert result.accepted_evidence is not None
    assert result.accepted_evidence["MaterialRequirementIDs"] == [
        "MR-SUB-AVIONICS-COMPUTE-PART-FPGA-SPACE-001"
    ]
    assert result.accepted_evidence["MaterialIssueCount"] == 0
    assert result.accepted_evidence["MaterialConsumptionCount"] == 0


def test_material_issue_without_inventory_quality_dependency_is_rejected() -> None:
    message = _load_example("sub-avionics-compute-part-fpga-space-reviewed.json")
    message["Payload"]["MaterialIssues"].append(_material_issue())

    result = process_execution_object_evidence_message(
        message,
        received_at=_received_at(),
        reference_resolver=default_reviewed_fixture_resolver(),
    )

    assert result.ack["AckStatus"] == "Rejected"
    assert result.ack["ErrorCode"] == "MISSING_INVENTORY_QUALITY_EVIDENCE"


def test_material_consumption_without_inventory_quality_dependency_is_rejected() -> None:
    message = _load_example("sub-avionics-compute-part-fpga-space-reviewed.json")
    message["Payload"]["MaterialConsumptions"].append(_material_consumption())

    result = process_execution_object_evidence_message(
        message,
        received_at=_received_at(),
        reference_resolver=default_reviewed_fixture_resolver(),
    )

    assert result.ack["AckStatus"] == "Rejected"
    assert result.ack["ErrorCode"] == "MISSING_INVENTORY_QUALITY_EVIDENCE"


def test_late_captured_completion_without_reconciliation_is_rejected() -> None:
    message = _load_example("sub-avionics-compute-part-fpga-space-reviewed.json")
    message["Payload"]["WorkOrder"]["WorkOrderStatus"] = "Completed"
    message["Payload"]["WorkOrder"]["CompletedQty"] = 1
    message["Payload"]["WorkOrder"]["RemainingQty"] = 0

    result = process_execution_object_evidence_message(
        message,
        received_at=_received_at(),
        reference_resolver=default_reviewed_fixture_resolver(),
    )

    assert result.ack["AckStatus"] == "Rejected"
    assert result.ack["ErrorCode"] == "EVENT_ORDER_INVALID"


def test_late_captured_completion_with_reconciliation_is_accepted() -> None:
    message = _load_example("sub-avionics-compute-part-fpga-space-reviewed.json")
    message["Payload"]["WorkOrder"].update(
        {
            "WorkOrderStatus": "Completed",
            "CompletedQty": 1,
            "RemainingQty": 0,
            "EventCaptureMode": "LateCaptured",
            "LateCaptureReason": "Paper traveler reconciled after execution.",
            "ReconciliationReferenceID": "RECON-WO-SUB-AVIONICS-COMPUTE-001",
            "ObservedAt": "2026-07-16T18:00:00+08:00",
            "RecordedAt": "2026-07-16T19:00:00+08:00",
        }
    )

    result = process_execution_object_evidence_message(
        message,
        received_at=_received_at(),
        reference_resolver=default_reviewed_fixture_resolver(),
    )

    assert result.ack["AckStatus"] == "Accepted"


def test_production_validated_reserved_is_rejected() -> None:
    message = _load_example("sub-avionics-compute-part-fpga-space-reviewed.json")
    message["Payload"]["EvidenceConfidence"] = "ProductionValidatedReserved"

    result = process_execution_object_evidence_message(
        message,
        received_at=_received_at(),
        reference_resolver=default_reviewed_fixture_resolver(),
    )

    assert result.ack["AckStatus"] == "Rejected"
    assert result.ack["ErrorCode"] == "CONTRACT_SCOPE_VIOLATION"


def test_governance_auto_update_attempt_is_rejected() -> None:
    message = _load_example("sub-avionics-compute-part-fpga-space-reviewed.json")
    message["Payload"]["DDAEGovernanceBoundary"]["AllowsAutomaticMasterSettingUpdate"] = True

    result = process_execution_object_evidence_message(
        message,
        received_at=_received_at(),
        reference_resolver=default_reviewed_fixture_resolver(),
    )

    assert result.ack["AckStatus"] == "Rejected"
    assert result.ack["ErrorCode"] == "GOVERNANCE_AUTO_UPDATE_FORBIDDEN"


def test_state_store_persists_execution_object_evidence_inbound_ledger(tmp_path) -> None:
    database_path = tmp_path / "workbench.sqlite"
    store = SQLiteWorkbenchStateStore(database_path)
    message = _load_example("sub-avionics-compute-part-fpga-space-reviewed.json")
    result = process_execution_object_evidence_message(
        message,
        received_at=_received_at(),
        reference_resolver=default_reviewed_fixture_resolver(),
    )
    store.execution_object_evidence_inbound_messages.append(result.inbound_ledger_record)
    store.save()

    reloaded = SQLiteWorkbenchStateStore(database_path)

    assert len(reloaded.execution_object_evidence_inbound_messages) == 1
    assert (
        reloaded.execution_object_evidence_inbound_messages[0]["AckStatus"]
        == "Accepted"
    )


def _load_example(filename: str) -> dict[str, object]:
    return json.loads(
        (CONTRACT_DIR / "examples" / filename).read_text(encoding="utf-8-sig")
    )


def _received_at() -> datetime:
    return datetime(2026, 6, 28, 13, 30, tzinfo=timezone.utc)


def _material_issue() -> dict[str, object]:
    return {
        "IssueEventID": "ISSUE-PART-FPGA-SPACE-001",
        "IssueState": "Issued",
        "ConsumedItemID": "PART-FPGA-SPACE",
        "IssueLocationID": "WH-ELEC-QA",
        "LotID": None,
        "SerialID": None,
        "BatchID": None,
        "IssuedQty": 1,
        "QuantityUOM": "EA",
        "UOMAuthority": "SDBR-MASTER-DATA",
        "IssuedAt": "2026-07-15T08:00:00+08:00",
        "IssueSourceSystem": "SDBR-REVIEWED-FIXTURE",
        "IssueDocumentID": "ISSUE-DOC-001",
        "InventoryQualityEvidencePackageID": None,
        "InventoryQualityEvidenceVersion": None,
        "IssueAuthorityReferenceID": None,
        "ReversesIssueEventID": None,
    }


def _material_consumption() -> dict[str, object]:
    return {
        "ConsumptionEventID": "CONS-PART-FPGA-SPACE-001",
        "ConsumptionState": "Consumed",
        "ConsumedByOperationID": "OP-INSTALL-FPGA-SPACE-001",
        "ConsumedItemID": "PART-FPGA-SPACE",
        "ConsumedLocationID": "WH-ELEC-QA",
        "ConsumedQty": 1,
        "ScrapQty": 0,
        "RejectQty": 0,
        "RemainingQty": 0,
        "QuantityUOM": "EA",
        "UOMAuthority": "SDBR-MASTER-DATA",
        "ConsumedAt": "2026-07-15T12:00:00+08:00",
        "ConsumptionSourceSystem": "SDBR-REVIEWED-FIXTURE",
        "ConsumptionMethod": "ReviewedFixtureOnly",
        "InventoryQualityEvidencePackageID": None,
        "InventoryQualityEvidenceVersion": None,
        "ConsumptionAuthorityReferenceID": None,
        "ReversesConsumptionEventID": None,
    }
