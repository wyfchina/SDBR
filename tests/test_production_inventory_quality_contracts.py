from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import json

from jsonschema import Draft202012Validator

from sdbr.production_inventory_quality_contracts import (
    InventoryQualityReferenceResolver,
    ack_schema,
    process_inventory_quality_evidence_message,
)
from sdbr.environment_paths import resolve_ddae_interface_contract_root
from sdbr.state_store import SQLiteWorkbenchStateStore


CONTRACT_ROOT = resolve_ddae_interface_contract_root()
CONTRACT_DIR = CONTRACT_ROOT / "contracts" / "production-inventory-quality-evidence-v1"


def test_reviewed_inventory_quality_example_is_accepted_but_not_source_authoritative() -> None:
    message = _load_example("part-fpga-space-reviewed-inventory-quality.json")

    result = process_inventory_quality_evidence_message(
        message,
        received_at=_received_at(),
        reference_resolver=_resolver(),
    )

    assert result.ack["AckStatus"] == "Accepted"
    assert result.accepted_evidence is not None
    assert result.accepted_evidence["ItemID"] == "PART-FPGA-SPACE"
    assert result.accepted_evidence["LocationID"] == "WH-ELEC-QA"
    assert result.accepted_evidence["SourceAuthoritativeUsable"] is False
    assert "NotProductionValidated" in result.accepted_evidence["NonClaims"]
    assert "NotBusinessGoldenLoopReady" in result.accepted_evidence["NonClaims"]


def test_ack_schema_accepts_contract_ack_example_and_generated_ack() -> None:
    ack = _load_example("ack-accepted-reviewed.json")
    Draft202012Validator(ack_schema()).validate(ack)
    message = _load_example("part-fpga-space-reviewed-inventory-quality.json")

    result = process_inventory_quality_evidence_message(
        message,
        received_at=_received_at(),
        reference_resolver=_resolver(),
    )

    Draft202012Validator(ack_schema()).validate(result.ack)
    assert result.ack["ConsumerSystem"] == "SDBR"


def test_reviewed_evidence_is_rejected_when_source_authoritative_required() -> None:
    message = _load_example("part-fpga-space-reviewed-inventory-quality.json")

    result = process_inventory_quality_evidence_message(
        message,
        received_at=_received_at(),
        reference_resolver=_resolver(),
        require_source_authoritative=True,
    )

    assert result.ack["AckStatus"] == "Rejected"
    assert result.ack["Errors"][0]["ErrorCode"] == "CONTRACT_SCOPE_VIOLATION"
    assert result.accepted_evidence is None


def test_identical_replay_is_duplicate_safe() -> None:
    message = _load_example("part-fpga-space-reviewed-inventory-quality.json")
    first = process_inventory_quality_evidence_message(
        message,
        received_at=_received_at(),
        reference_resolver=_resolver(),
    )

    replay = process_inventory_quality_evidence_message(
        message,
        received_at=_received_at(),
        existing_ledger_records=[first.inbound_ledger_record],
        reference_resolver=_resolver(),
    )

    assert replay.ack["AckStatus"] == "Duplicate"
    assert replay.ack["Errors"] == []


def test_idempotency_conflict_is_dead_lettered() -> None:
    message = _load_example("part-fpga-space-reviewed-inventory-quality.json")
    first = process_inventory_quality_evidence_message(
        message,
        received_at=_received_at(),
        reference_resolver=_resolver(),
    )
    conflicting = deepcopy(message)
    conflicting["Payload"]["InventorySnapshot"]["AvailableQty"] = 121

    result = process_inventory_quality_evidence_message(
        conflicting,
        received_at=_received_at(),
        existing_ledger_records=[first.inbound_ledger_record],
        reference_resolver=_resolver(),
    )

    assert result.ack["AckStatus"] == "DeadLettered"
    assert result.ack["Errors"][0]["ErrorCode"] == "IDEMPOTENCY_CONFLICT"


def test_missing_inventory_authority_for_snapshot_is_rejected() -> None:
    message = _load_example("part-fpga-space-reviewed-inventory-quality.json")
    message["Payload"]["InventoryAuthority"] = None

    result = process_inventory_quality_evidence_message(
        message,
        received_at=_received_at(),
        reference_resolver=_resolver(),
    )

    assert result.ack["AckStatus"] == "Rejected"
    assert result.ack["Errors"][0]["ErrorCode"] == "MISSING_INVENTORY_AUTHORITY"


def test_missing_quality_authority_for_release_is_rejected() -> None:
    message = _load_example("part-fpga-space-reviewed-inventory-quality.json")
    message["Payload"]["QualityAuthority"] = None

    result = process_inventory_quality_evidence_message(
        message,
        received_at=_received_at(),
        reference_resolver=_resolver(),
    )

    assert result.ack["AckStatus"] == "Rejected"
    assert result.ack["Errors"][0]["ErrorCode"] == "MISSING_QUALITY_AUTHORITY"


def test_unknown_item_reference_is_dead_lettered() -> None:
    message = _load_example("part-fpga-space-reviewed-inventory-quality.json")

    result = process_inventory_quality_evidence_message(
        message,
        received_at=_received_at(),
        reference_resolver=InventoryQualityReferenceResolver(
            item_ids={"OTHER-ITEM"},
            location_ids={"WH-ELEC-QA", "WH-IQC"},
            program_ids={"SAT-BUS-001"},
            uoms={"EA"},
            inventory_authority_ids={"ContractAgentAcceptedSource"},
            quality_authority_ids={"ContractAgentAcceptedSource"},
            snapshot_ids={"SDBR-FPGA-MATERIAL-AVAILABILITY-SNAPSHOT-20260627-001"},
            quality_release_ids={"CTRL-QA-RELEASE-FPGA-20260712-001"},
        ),
    )

    assert result.ack["AckStatus"] == "DeadLettered"
    assert result.ack["Errors"][0]["ErrorCode"] == "UNKNOWN_ITEM"


def test_unsupported_uom_is_rejected() -> None:
    message = _load_example("part-fpga-space-reviewed-inventory-quality.json")

    result = process_inventory_quality_evidence_message(
        message,
        received_at=_received_at(),
        reference_resolver=InventoryQualityReferenceResolver(
            item_ids={"PART-FPGA-SPACE"},
            location_ids={"WH-ELEC-QA", "WH-IQC"},
            program_ids={"SAT-BUS-001"},
            uoms={"KG"},
            inventory_authority_ids={"ContractAgentAcceptedSource"},
            quality_authority_ids={"ContractAgentAcceptedSource"},
            snapshot_ids={"SDBR-FPGA-MATERIAL-AVAILABILITY-SNAPSHOT-20260627-001"},
            quality_release_ids={"CTRL-QA-RELEASE-FPGA-20260712-001"},
        ),
    )

    assert result.ack["AckStatus"] == "Rejected"
    assert result.ack["Errors"][0]["ErrorCode"] == "UNSUPPORTED_UOM"


def test_timezone_free_timestamp_is_rejected() -> None:
    message = _load_example("part-fpga-space-reviewed-inventory-quality.json")
    message["Payload"]["InventorySnapshot"]["SnapshotTimestamp"] = "2026-06-27T20:00:00"

    result = process_inventory_quality_evidence_message(
        message,
        received_at=_received_at(),
        reference_resolver=_resolver(),
    )

    assert result.ack["AckStatus"] == "Rejected"
    assert result.ack["Errors"][0]["ErrorCode"] == "INVALID_TIMESTAMP"


def test_invalid_quantity_is_rejected() -> None:
    message = _load_example("part-fpga-space-reviewed-inventory-quality.json")
    message["Payload"]["InventorySnapshot"]["AvailableAfterAllocationQty"] = 130

    result = process_inventory_quality_evidence_message(
        message,
        received_at=_received_at(),
        reference_resolver=_resolver(),
    )

    assert result.ack["AckStatus"] == "Rejected"
    assert result.ack["Errors"][0]["ErrorCode"] == "INVALID_QUANTITY"


def test_production_validated_reserved_is_rejected() -> None:
    message = _load_example("part-fpga-space-reviewed-inventory-quality.json")
    message["Payload"]["EvidenceConfidence"] = "ProductionValidatedReserved"

    result = process_inventory_quality_evidence_message(
        message,
        received_at=_received_at(),
        reference_resolver=_resolver(),
    )

    assert result.ack["AckStatus"] == "Rejected"
    assert result.ack["Errors"][0]["ErrorCode"] == "CONTRACT_SCOPE_VIOLATION"


def test_reversal_without_original_movement_is_dead_lettered() -> None:
    message = _load_example("part-fpga-space-reviewed-inventory-quality.json")
    movement = message["Payload"]["StockMovements"][0]
    movement["MovementType"] = "Reversal"
    movement["MovementState"] = "Reversed"
    movement["ReversesMovementID"] = None

    result = process_inventory_quality_evidence_message(
        message,
        received_at=_received_at(),
        reference_resolver=_resolver(),
    )

    assert result.ack["AckStatus"] == "DeadLettered"
    assert result.ack["Errors"][0]["ErrorCode"] == "MOVEMENT_REVERSAL_TARGET_NOT_FOUND"


def test_supersession_without_target_is_dead_lettered() -> None:
    message = _load_example("part-fpga-space-reviewed-inventory-quality.json")
    message["Payload"]["Supersession"]["CorrectionReason"] = "Corrected quantity."

    result = process_inventory_quality_evidence_message(
        message,
        received_at=_received_at(),
        reference_resolver=_resolver(),
    )

    assert result.ack["AckStatus"] == "DeadLettered"
    assert result.ack["Errors"][0]["ErrorCode"] == "SUPERSESSION_TARGET_NOT_FOUND"


def test_state_store_persists_inventory_quality_inbound_ledger(tmp_path) -> None:
    database_path = tmp_path / "workbench.sqlite"
    store = SQLiteWorkbenchStateStore(database_path)
    message = _load_example("part-fpga-space-reviewed-inventory-quality.json")
    result = process_inventory_quality_evidence_message(
        message,
        received_at=_received_at(),
        reference_resolver=_resolver(),
    )
    store.production_inventory_quality_inbound_messages.append(
        result.inbound_ledger_record
    )
    store.save()

    reloaded = SQLiteWorkbenchStateStore(database_path)

    assert len(reloaded.production_inventory_quality_inbound_messages) == 1
    assert (
        reloaded.production_inventory_quality_inbound_messages[0]["AckStatus"]
        == "Accepted"
    )


def _load_example(filename: str) -> dict[str, object]:
    return json.loads(
        (CONTRACT_DIR / "examples" / filename).read_text(encoding="utf-8-sig")
    )


def _received_at() -> datetime:
    return datetime(2026, 6, 28, 12, 50, tzinfo=timezone.utc)


def _resolver() -> InventoryQualityReferenceResolver:
    return InventoryQualityReferenceResolver(
        item_ids={"PART-FPGA-SPACE"},
        location_ids={"WH-ELEC-QA", "WH-IQC"},
        program_ids={"SAT-BUS-001"},
        uoms={"EA"},
        inventory_authority_ids={"ContractAgentAcceptedSource"},
        quality_authority_ids={"ContractAgentAcceptedSource"},
        snapshot_ids={"SDBR-FPGA-MATERIAL-AVAILABILITY-SNAPSHOT-20260627-001"},
        movement_ids={"PIQE-MOVE-PART-FPGA-SPACE-QA-RELEASE-20260712-001"},
        quality_release_ids={"CTRL-QA-RELEASE-FPGA-20260712-001"},
    )
