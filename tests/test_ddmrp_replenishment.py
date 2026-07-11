"""Acceptance evidence for BE-DDMRP-007; activation-only cases also trace BE-DDMRP-008 and BE-DDMRP-009."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict
from datetime import datetime, timezone

import pytest

from sdbr.ddsop_contracts import canonical_operating_model_fingerprint


EVALUATED_AT = datetime(2026, 6, 30, 1, 0, tzinfo=timezone.utc)
SIGNATURE_KEYS = {
    "runtime_package_id",
    "runtime_package_version",
    "runtime_package_fingerprint",
    "runtime_snapshot_id",
    "runtime_snapshot_at",
    "operating_model_configuration_id",
    "operating_model_fingerprint",
    "ddmrp_configuration_id",
    "target_time_semantics_id",
    "target_policy_id",
    "target_policy_version",
    "target_policy_fingerprint",
    "target_calendar_id",
    "target_calendar_version",
    "target_calendar_fingerprint",
    "planning_advice_package_id",
    "planning_advice_package_fingerprint",
    "plan_bom_package_id",
    "plan_bom_package_fingerprint",
    "material_authority_snapshot_id",
    "material_authority_snapshot_fingerprint",
    "capacity_calendar_snapshot_id",
    "capacity_calendar_snapshot_fingerprint",
    "local_planning_ledger_schema_version",
    "local_planning_ledger_identity",
    "local_planning_ledger_fingerprint",
    "scenario_label",
    "mapping_confidence",
    "parameter_authority_fingerprint",
    "signature_fingerprint",
}


def test_be_ddmrp_007_signature_freezes_runtime_config_and_all_current_authority_slots() -> None:
    from sdbr.ddmrp_replenishment import build_read_only_authority_signature

    package = _package_record(production_accepted=True)
    configuration = _operating_model_configuration(package)
    ledger = _ledger_identity()

    signature, gates = build_read_only_authority_signature(
        package_record=package,
        operating_model_configuration=configuration,
        relevant_planning_ledger=ledger,
        evaluated_at=EVALUATED_AT,
    )

    frozen = asdict(signature)
    assert set(frozen) == SIGNATURE_KEYS
    assert frozen["runtime_package_id"] == "RPI-TEST-001"
    assert frozen["runtime_package_version"] == "1.0.0"
    assert frozen["runtime_snapshot_id"] == "OPS-TEST-001"
    assert frozen["runtime_snapshot_at"] == "2026-06-30T01:00:00+00:00"
    assert frozen["operating_model_configuration_id"] == "OMC-TEST-001"
    assert frozen["operating_model_fingerprint"] == configuration["Payload"]["Fingerprint"]
    assert frozen["ddmrp_configuration_id"] == "DDMRP-TEST-001"
    assert frozen["local_planning_ledger_schema_version"] == ledger.schema_version
    assert frozen["local_planning_ledger_identity"] == ledger.identity
    assert frozen["local_planning_ledger_fingerprint"] == ledger.fingerprint
    assert frozen["parameter_authority_fingerprint"].startswith("sha256:")
    assert frozen["signature_fingerprint"].startswith("sha256:")
    for field in (
        "target_time_semantics_id",
        "target_policy_id",
        "target_policy_version",
        "target_policy_fingerprint",
        "target_calendar_id",
        "target_calendar_version",
        "target_calendar_fingerprint",
        "planning_advice_package_id",
        "planning_advice_package_fingerprint",
        "plan_bom_package_id",
        "plan_bom_package_fingerprint",
        "material_authority_snapshot_id",
        "material_authority_snapshot_fingerprint",
        "capacity_calendar_snapshot_id",
        "capacity_calendar_snapshot_fingerprint",
    ):
        assert frozen[field] is None
    assert [gate.code for gate in gates] == sorted(
        {
            "DLT_TARGET_SEMANTICS_INSUFFICIENT",
            "PLANNING_ADVICE_CONTRACT_NOT_ACCEPTED",
            "PLAN_BOM_FEASIBILITY_CONTRACT_NOT_ACCEPTED",
        }
    )


def test_be_ddmrp_007_public_demo_signature_is_read_only() -> None:
    from sdbr.ddmrp_replenishment import build_read_only_authority_signature

    package = _package_record(production_accepted=False)
    signature, gates = build_read_only_authority_signature(
        package_record=package,
        operating_model_configuration=_operating_model_configuration(package),
        relevant_planning_ledger=_ledger_identity(),
        evaluated_at=EVALUATED_AT,
    )

    assert signature.mapping_confidence == "PublicDemoOnly"
    assert [gate.code for gate in gates] == sorted(
        {
            "DLT_TARGET_SEMANTICS_INSUFFICIENT",
            "OPERATIONAL_AUTHORITY_NOT_ACCEPTED",
            "PLANNING_ADVICE_CONTRACT_NOT_ACCEPTED",
            "PLAN_BOM_FEASIBILITY_CONTRACT_NOT_ACCEPTED",
        }
    )
    assert all(gate.blocks_operational_action for gate in gates)


def test_be_ddmrp_007_missing_target_semantics_returns_named_gate_and_null_target() -> None:
    from sdbr.ddmrp_replenishment import build_read_only_authority_signature

    package = _package_record(production_accepted=True)
    signature, gates = build_read_only_authority_signature(
        package_record=package,
        operating_model_configuration=_operating_model_configuration(package),
        relevant_planning_ledger=_ledger_identity(),
        evaluated_at=EVALUATED_AT,
    )

    assert signature.target_time_semantics_id is None
    assert signature.target_policy_id is None
    assert signature.target_calendar_id is None
    assert "DLT_TARGET_SEMANTICS_INSUFFICIENT" in {gate.code for gate in gates}
    assert "StandardTargetReceiptAt" not in asdict(signature)


def test_be_ddmrp_007_signature_fingerprint_changes_for_runtime_or_relevant_ledger_drift() -> None:
    from sdbr.ddmrp_replenishment import build_read_only_authority_signature

    package = _package_record(production_accepted=True)
    configuration = _operating_model_configuration(package)
    first_ledger = _ledger_identity(quantity=5)
    second_ledger = _ledger_identity(quantity=6)
    first, _ = build_read_only_authority_signature(
        package_record=package,
        operating_model_configuration=configuration,
        relevant_planning_ledger=first_ledger,
        evaluated_at=EVALUATED_AT,
    )
    changed_runtime = deepcopy(package)
    changed_runtime["Payload"]["RuntimeEvidenceSnapshot"]["InventoryPositions"][0][
        "AvailableQty"
    ] = 41
    second, _ = build_read_only_authority_signature(
        package_record=changed_runtime,
        operating_model_configuration=configuration,
        relevant_planning_ledger=first_ledger,
        evaluated_at=EVALUATED_AT,
    )
    third, _ = build_read_only_authority_signature(
        package_record=package,
        operating_model_configuration=configuration,
        relevant_planning_ledger=second_ledger,
        evaluated_at=EVALUATED_AT,
    )

    assert first.signature_fingerprint != second.signature_fingerprint
    assert first.runtime_package_fingerprint != second.runtime_package_fingerprint
    assert first.signature_fingerprint != third.signature_fingerprint
    assert first.local_planning_ledger_identity != third.local_planning_ledger_identity


def test_be_ddmrp_007_rejects_runtime_configuration_reference_mismatch() -> None:
    from sdbr.ddmrp_replenishment import (
        DdmrpReplenishmentConflict,
        build_read_only_authority_signature,
    )

    package = _package_record(production_accepted=True)
    configuration = _operating_model_configuration(package)
    configuration["Payload"]["DDMRPConfiguration"]["DDMRPConfigurationID"] = "OTHER"
    configuration["Payload"]["Fingerprint"] = canonical_operating_model_fingerprint(
        configuration["Payload"]
    )

    with pytest.raises(DdmrpReplenishmentConflict):
        build_read_only_authority_signature(
            package_record=package,
            operating_model_configuration=configuration,
            relevant_planning_ledger=_ledger_identity(),
            evaluated_at=EVALUATED_AT,
        )


def test_be_ddmrp_007_relevant_ledger_identity_ignores_global_revision_and_unrelated_facts() -> None:
    from sdbr.ddmrp_replenishment import build_relevant_planning_ledger_identity

    inputs = _ledger_inputs(quantity=5)
    first = build_relevant_planning_ledger_identity(**inputs)
    changed = deepcopy(inputs)
    changed["planning_demand_commitments"]["DEMAND-OUTSIDE"] = _demand_row(
        demand_id="DEMAND-OUTSIDE", item_id="OTHER", location_id="OTHER", quantity=99
    )
    changed["planning_demand_commitments"]["DEMAND-1"]["AuditOnlyNote"] = "ignored"
    changed["planning_reservation_batches"]["BATCH-OUTSIDE"] = _batch_row(
        batch_id="BATCH-OUTSIDE", demand_id="DEMAND-OUTSIDE"
    )
    second = build_relevant_planning_ledger_identity(**changed)
    quantity_changed = build_relevant_planning_ledger_identity(**_ledger_inputs(quantity=6))

    assert first == second
    assert first != quantity_changed
    assert first.identity != quantity_changed.identity
    assert first.fingerprint != quantity_changed.fingerprint


def test_be_ddmrp_007_signature_uses_canonical_snapshot_datetime_not_raw_package_text() -> None:
    from sdbr.ddmrp_replenishment import (
        DdmrpReplenishmentConflict,
        build_read_only_authority_signature,
    )

    first_package = _package_record(production_accepted=True)
    configuration = _operating_model_configuration(first_package)
    second_package = deepcopy(first_package)
    first_package["Payload"]["RuntimeEvidenceSnapshot"]["SnapshotAt"] = "2026-06-30T01:00:00Z"
    second_package["Payload"]["RuntimeEvidenceSnapshot"]["SnapshotAt"] = (
        "2026-06-30T09:00:00+08:00"
    )
    first, _ = build_read_only_authority_signature(
        package_record=first_package,
        operating_model_configuration=configuration,
        relevant_planning_ledger=_ledger_identity(),
        evaluated_at=EVALUATED_AT,
    )
    second, _ = build_read_only_authority_signature(
        package_record=second_package,
        operating_model_configuration=configuration,
        relevant_planning_ledger=_ledger_identity(),
        evaluated_at=EVALUATED_AT,
    )

    assert first.runtime_snapshot_at == second.runtime_snapshot_at
    assert first.signature_fingerprint == second.signature_fingerprint
    with pytest.raises(DdmrpReplenishmentConflict):
        build_read_only_authority_signature(
            package_record=first_package,
            operating_model_configuration=configuration,
            relevant_planning_ledger=_ledger_identity(),
            evaluated_at=datetime(2026, 6, 30, 1, 0),
        )


def _ledger_identity(*, quantity: int = 5):
    from sdbr.ddmrp_replenishment import build_relevant_planning_ledger_identity

    return build_relevant_planning_ledger_identity(**_ledger_inputs(quantity=quantity))


def _ledger_inputs(*, quantity: int) -> dict[str, object]:
    return {
        "scope_item_locations": [("ITEM-1", "LOC-1")],
        "planning_demand_commitments": {
            "DEMAND-1": _demand_row(quantity=quantity),
        },
        "planning_reservation_batches": {"BATCH-1": _batch_row()},
        "ccr_capacity_reservations": {"CAP-1": _capacity_row()},
        "material_planning_allocations": {"MAT-1": _material_row()},
        "active_replenishment_graphs": {"GRAPH-1": _graph_row()},
    }


def _demand_row(
    *,
    demand_id: str = "DEMAND-1",
    item_id: str = "ITEM-1",
    location_id: str = "LOC-1",
    quantity: int = 5,
) -> dict[str, object]:
    return {
        "DemandCommitmentID": demand_id,
        "DemandSourceType": "MTAReplenishment",
        "SourceSystem": "SDBR",
        "SourceObjectType": "LogicalReplenishment",
        "SourceObjectID": "LR-1",
        "SourceObjectVersion": 1,
        "DemandLineID": "LINE-1",
        "ItemOrProductID": item_id,
        "LocationID": location_id,
        "Quantity": quantity,
        "Uom": "EA",
        "RequiredAt": "2026-07-01T00:00:00+00:00",
        "DemandClass": "MTA",
        "Status": "Active",
        "RecordVersion": 1,
        "ContentFingerprint": "sha256:demand",
    }


def _batch_row(
    *, batch_id: str = "BATCH-1", demand_id: str = "DEMAND-1"
) -> dict[str, object]:
    return {
        "ReservationBatchID": batch_id,
        "DemandCommitmentID": demand_id,
        "DemandClass": "MTA",
        "Status": "ActivePlanReservation",
        "CapacityReservationIDs": ["CAP-1"],
        "MaterialAllocationIDs": ["MAT-1"],
        "PlanningRunID": None,
        "RecordVersion": 1,
        "LastTransitionAt": "2026-06-30T01:00:00+00:00",
        "EventType": "ReservationBatchCreated",
    }


def _capacity_row() -> dict[str, object]:
    return {
        "CapacityReservationID": "CAP-1",
        "ReservationBatchID": "BATCH-1",
        "DemandCommitmentID": "DEMAND-1",
        "DemandClass": "MTA",
        "ResourceID": "CCR-1",
        "WindowStartAt": "2026-07-01T00:00:00+00:00",
        "WindowEndAt": "2026-07-01T01:00:00+00:00",
        "ReservedMinutes": 60,
        "LatestAllowedCompletionAt": "2026-07-02T00:00:00+00:00",
        "Status": "ActivePlanReservation",
        "PlanningRunID": None,
        "RecordVersion": 1,
        "LastTransitionAt": "2026-06-30T01:00:00+00:00",
        "EventType": "CapacityReservationCreated",
    }


def _material_row() -> dict[str, object]:
    return {
        "MaterialAllocationID": "MAT-1",
        "ReservationBatchID": "BATCH-1",
        "DemandCommitmentID": "DEMAND-1",
        "RequirementLineID": "REQ-1",
        "ItemID": "COMP-1",
        "LocationID": "LOC-1",
        "Uom": "EA",
        "AllocatedQty": 5,
        "SupplySourceType": "Inventory",
        "SupplyID": "SUPPLY-1",
        "MaterialSnapshotID": "MAT-SNAPSHOT-1",
        "ExternalAllocationRef": None,
        "Status": "ActivePlanReservation",
        "RecordVersion": 1,
        "LastTransitionAt": "2026-06-30T01:00:00+00:00",
        "EventType": "MaterialAllocationCreated",
    }


def _graph_row() -> dict[str, object]:
    return {
        "LogicalReplenishmentID": "GRAPH-1",
        "RecommendationID": "REC-1",
        "ItemID": "ITEM-1",
        "LocationID": "LOC-1",
        "Uom": "EA",
        "GraphStatus": "ActivePlanReservation",
        "DemandCommitmentID": "DEMAND-1",
        "ReservationBatchID": "BATCH-1",
        "PlannedManufacturingCandidateID": None,
        "FormalSupplyID": None,
        "RecordVersion": 1,
    }


def _package_record(*, production_accepted: bool) -> dict[str, object]:
    confidence = "ProductionAccepted" if production_accepted else "PublicDemoOnly"
    authority = "Accepted" if production_accepted else "PublicDemoOnly"
    scenario = "ProductionCandidate" if production_accepted else "ControlledContractGoldenLoopDemo"
    return {
        "RuntimePlanningInputPackageID": "RPI-TEST-001",
        "PackageVersion": "1.0.0",
        "PackageStatus": "AcceptedForBoundedPlanning" if production_accepted else "Reviewed",
        "OperatingModelConfigurationID": "OMC-TEST-001",
        "OperatingModelFingerprint": "pending",
        "DDMRPConfigurationID": "DDMRP-TEST-001",
        "Payload": {
            "PackageIdentity": {
                "RuntimePlanningInputPackageID": "RPI-TEST-001",
                "PackageVersion": "1.0.0",
                "PackageStatus": "AcceptedForBoundedPlanning" if production_accepted else "Reviewed",
                "ScenarioLabel": scenario,
                "MappingConfidence": confidence,
            },
            "FrozenDdsopConfiguration": {
                "OperatingModelConfigurationID": "OMC-TEST-001",
                "OperatingModelFingerprint": "pending",
                "DDMRPConfigurationID": "DDMRP-TEST-001",
            },
            "ParameterAuthorityEvidence": {
                "ApprovalEvidenceID": "APPROVAL-1",
                "ParameterEvidenceRefs": [
                    {
                        "FieldGroup": field_group,
                        "EvidenceID": f"EVIDENCE-{field_group}",
                        "ProductionAuthorityStatus": authority,
                        "Applicability": "Applicable",
                    }
                    for field_group in ("ADU", "DLT", "BufferZones", "BufferProfile")
                ],
            },
            "RuntimeEvidenceSnapshot": {
                "OperationalStateSnapshotID": "OPS-TEST-001",
                "SnapshotAt": "2026-06-30T09:00:00+08:00",
                "InventoryPositions": [
                    {
                        "ItemID": "ITEM-1",
                        "LocationID": "LOC-1",
                        "AvailableQty": 40,
                    }
                ],
                "DemandSignals": [],
                "OpenSupplySignals": [],
            },
        },
    }


def _operating_model_configuration(package: dict[str, object]) -> dict[str, object]:
    payload = {
        "OperatingModelConfigurationID": "OMC-TEST-001",
        "Status": "Approved",
        "DDMRPConfiguration": {"DDMRPConfigurationID": "DDMRP-TEST-001"},
    }
    payload["Fingerprint"] = canonical_operating_model_fingerprint(payload)
    package["OperatingModelFingerprint"] = payload["Fingerprint"]
    package["Payload"]["FrozenDdsopConfiguration"]["OperatingModelFingerprint"] = payload[
        "Fingerprint"
    ]
    return {"Payload": payload}
