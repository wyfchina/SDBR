from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import json

from jsonschema import Draft202012Validator

from sdbr.environment_paths import resolve_ddae_interface_contract_root
from sdbr.state_store import SQLiteWorkbenchStateStore
from sdbr.supplier_identity_source_contracts import (
    SupplierSourceReferenceResolver,
    ack_schema,
    process_supplier_identity_source_message,
)


CONTRACT_ROOT = resolve_ddae_interface_contract_root()
CONTRACT_DIR = CONTRACT_ROOT / "contracts" / "production-supplier-identity-source-v1"


def test_reviewed_supplier_source_example_is_accepted_but_not_active() -> None:
    message = _load_example("sup-microchip-part-fpga-space-reviewed.json")
    result = process_supplier_identity_source_message(
        message,
        received_at=_received_at(),
        reference_resolver=_resolver(),
    )

    assert result.ack["AckStatus"] == "Accepted"
    assert result.accepted_evidence is not None
    assert result.accepted_evidence["SupplierID"] == "SUP-MICROCHIP"
    assert result.accepted_evidence["ItemID"] == "PART-FPGA-SPACE"
    assert result.accepted_evidence["ActiveSourceUsable"] is False
    assert "NotProductionValidated" in result.accepted_evidence["NonClaims"]
    assert "NotBusinessGoldenLoopReady" in result.accepted_evidence["NonClaims"]


def test_ack_schema_accepts_contract_ack_example_and_generated_ack() -> None:
    ack = _load_example("ack-accepted-reviewed.json")
    Draft202012Validator(ack_schema()).validate(ack)
    message = _load_example("sup-microchip-part-fpga-space-reviewed.json")

    result = process_supplier_identity_source_message(
        message,
        received_at=_received_at(),
        reference_resolver=_resolver(),
    )

    Draft202012Validator(ack_schema()).validate(result.ack)
    assert result.ack["ConsumerSystem"] == "SDBR"


def test_reviewed_evidence_is_rejected_when_active_source_is_required() -> None:
    message = _load_example("sup-microchip-part-fpga-space-reviewed.json")

    result = process_supplier_identity_source_message(
        message,
        received_at=_received_at(),
        reference_resolver=_resolver(),
        require_active_source=True,
    )

    assert result.ack["AckStatus"] == "Rejected"
    assert result.ack["Errors"][0]["ErrorCode"] == "UNAPPROVED_SOURCE"
    assert result.accepted_evidence is None


def test_identical_replay_is_duplicate_safe() -> None:
    message = _load_example("sup-microchip-part-fpga-space-reviewed.json")
    first = process_supplier_identity_source_message(
        message,
        received_at=_received_at(),
        reference_resolver=_resolver(),
    )

    replay = process_supplier_identity_source_message(
        message,
        received_at=_received_at(),
        existing_ledger_records=[first.inbound_ledger_record],
        reference_resolver=_resolver(),
    )

    assert replay.ack["AckStatus"] == "Duplicate"
    assert replay.ack["Errors"] == []


def test_idempotency_conflict_is_dead_lettered() -> None:
    message = _load_example("sup-microchip-part-fpga-space-reviewed.json")
    first = process_supplier_identity_source_message(
        message,
        received_at=_received_at(),
        reference_resolver=_resolver(),
    )
    conflicting = deepcopy(message)
    conflicting["Payload"]["SupplierIdentity"]["SupplierName"] = "Changed Supplier"

    result = process_supplier_identity_source_message(
        conflicting,
        received_at=_received_at(),
        existing_ledger_records=[first.inbound_ledger_record],
        reference_resolver=_resolver(),
    )

    assert result.ack["AckStatus"] == "DeadLettered"
    assert result.ack["Errors"][0]["ErrorCode"] == "IDEMPOTENCY_CONFLICT"


def test_missing_source_authority_is_dead_lettered() -> None:
    message = _load_example("sup-microchip-part-fpga-space-reviewed.json")
    del message["Payload"]["SourceAuthority"]

    result = process_supplier_identity_source_message(
        message,
        received_at=_received_at(),
        reference_resolver=_resolver(),
    )

    assert result.ack["AckStatus"] == "DeadLettered"
    assert result.ack["Errors"][0]["ErrorCode"] == "MISSING_SOURCE_AUTHORITY"


def test_unknown_supplier_reference_is_dead_lettered() -> None:
    message = _load_example("sup-microchip-part-fpga-space-reviewed.json")

    result = process_supplier_identity_source_message(
        message,
        received_at=_received_at(),
        reference_resolver=SupplierSourceReferenceResolver(
            supplier_ids={"OTHER-SUPPLIER"},
            item_ids={"PART-FPGA-SPACE"},
            location_ids={"WH-ELEC-QA"},
            program_ids={"SAT-BUS-001"},
            supplier_source_relation_ids={"PSISR-SUP-MICROCHIP-PART-FPGA-SPACE-001"},
            uoms={"EA"},
            source_authority_ids={"ContractAgentAcceptedSource"},
        ),
    )

    assert result.ack["AckStatus"] == "DeadLettered"
    assert result.ack["Errors"][0]["ErrorCode"] == "UNKNOWN_SUPPLIER"


def test_governance_auto_update_attempt_is_rejected() -> None:
    message = _load_example("sup-microchip-part-fpga-space-reviewed.json")
    message["Payload"]["DDAEGovernanceBoundary"][
        "AllowsAutomaticMasterSettingUpdate"
    ] = True

    result = process_supplier_identity_source_message(
        message,
        received_at=_received_at(),
        reference_resolver=_resolver(),
    )

    assert result.ack["AckStatus"] == "Rejected"
    assert result.ack["Errors"][0]["ErrorCode"] == "GOVERNANCE_AUTO_UPDATE_FORBIDDEN"


def test_contradictory_source_terms_are_rejected() -> None:
    message = _load_example("sup-microchip-part-fpga-space-reviewed.json")
    message["Payload"]["SourceTerms"]["TermsAreProductionAuthoritative"] = True
    message["Payload"]["SourceTerms"]["DDAEPlanningAssumptionOnly"] = True

    result = process_supplier_identity_source_message(
        message,
        received_at=_received_at(),
        reference_resolver=_resolver(),
    )

    assert result.ack["AckStatus"] == "Rejected"
    assert result.ack["Errors"][0]["ErrorCode"] == "CONTRACT_SCOPE_VIOLATION"


def test_production_validated_reserved_is_not_active_v1_claim() -> None:
    message = _load_example("sup-microchip-part-fpga-space-reviewed.json")
    message["Payload"]["EvidenceConfidence"] = "ProductionValidatedReserved"

    result = process_supplier_identity_source_message(
        message,
        received_at=_received_at(),
        reference_resolver=_resolver(),
    )

    assert result.ack["AckStatus"] == "Rejected"
    assert result.ack["Errors"][0]["ErrorCode"] == "CONTRACT_SCOPE_VIOLATION"


def test_invalid_effective_window_is_rejected() -> None:
    message = _load_example("sup-microchip-part-fpga-space-reviewed.json")
    message["Payload"]["SupplierSourceRelation"]["EffectiveTo"] = (
        "2026-06-27T00:00:00+08:00"
    )

    result = process_supplier_identity_source_message(
        message,
        received_at=_received_at(),
        reference_resolver=_resolver(),
    )

    assert result.ack["AckStatus"] == "Rejected"
    assert result.ack["Errors"][0]["ErrorCode"] == "INVALID_EFFECTIVE_WINDOW"


def test_state_store_persists_supplier_identity_source_inbound_ledger(tmp_path) -> None:
    database_path = tmp_path / "workbench.sqlite"
    store = SQLiteWorkbenchStateStore(database_path)
    message = _load_example("sup-microchip-part-fpga-space-reviewed.json")
    result = process_supplier_identity_source_message(
        message,
        received_at=_received_at(),
        reference_resolver=_resolver(),
    )
    store.supplier_identity_source_inbound_messages.append(
        result.inbound_ledger_record
    )
    store.save()

    reloaded = SQLiteWorkbenchStateStore(database_path)

    assert len(reloaded.supplier_identity_source_inbound_messages) == 1
    assert (
        reloaded.supplier_identity_source_inbound_messages[0]["AckStatus"]
        == "Accepted"
    )


def _load_example(filename: str) -> dict[str, object]:
    return json.loads(
        (CONTRACT_DIR / "examples" / filename).read_text(encoding="utf-8-sig")
    )


def _received_at() -> datetime:
    return datetime(2026, 6, 28, 10, 50, tzinfo=timezone.utc)


def _resolver() -> SupplierSourceReferenceResolver:
    return SupplierSourceReferenceResolver(
        supplier_ids={"SUP-MICROCHIP"},
        item_ids={"PART-FPGA-SPACE"},
        location_ids={"WH-ELEC-QA"},
        program_ids={"SAT-BUS-001"},
        supplier_source_relation_ids={"PSISR-SUP-MICROCHIP-PART-FPGA-SPACE-001"},
        uoms={"EA"},
        source_authority_ids={"ContractAgentAcceptedSource"},
    )
