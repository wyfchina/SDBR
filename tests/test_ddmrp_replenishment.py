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


@pytest.mark.parametrize("non_finite", [float("nan"), float("inf"), float("-inf")])
def test_be_ddmrp_007_canonical_fingerprint_rejects_non_finite_numbers(
    non_finite: float,
) -> None:
    from sdbr.ddmrp_replenishment import (
        DdmrpReplenishmentConflict,
        canonical_fingerprint,
    )

    with pytest.raises(DdmrpReplenishmentConflict, match="non-canonical JSON"):
        canonical_fingerprint({"Quantity": non_finite})


@pytest.mark.parametrize("non_finite", [float("nan"), float("inf"), float("-inf")])
def test_be_ddmrp_007_relevant_ledger_identity_rejects_non_finite_numbers(
    non_finite: float,
) -> None:
    from sdbr.ddmrp_replenishment import (
        DdmrpReplenishmentConflict,
        build_relevant_planning_ledger_identity,
    )

    inputs = _ledger_inputs(quantity=5)
    inputs["planning_demand_commitments"]["DEMAND-1"]["Quantity"] = non_finite

    with pytest.raises(DdmrpReplenishmentConflict, match="non-canonical JSON"):
        build_relevant_planning_ledger_identity(**inputs)


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


def test_be_ddmrp_007_red_yellow_create_blocked_versions_green_above_remain_monitor_rows() -> None:
    write_set = _prepare_evaluation()

    assert len(write_set.evaluation_rows) == 4
    assert [row["PlanningStatus"] for row in write_set.evaluation_rows] == [
        "AboveGreen", "Green", "Red", "Yellow"
    ]
    assert len(write_set.chain_records) == 2
    assert len(write_set.recommendation_versions) == 2
    assert {row["PlanningStatus"] for row in write_set.recommendation_versions} == {
        "Red", "Yellow"
    }
    assert all(
        recommendation["AdviceType"] is None
        and recommendation["StandardTargetReceiptAt"] is None
        and recommendation["InitialStatus"] == "Blocked"
        and [gate["Code"] for gate in recommendation["GateCodes"]] == _gate_codes()
        for recommendation in write_set.recommendation_versions
    )
    monitor_rows = [
        row for row in write_set.evaluation_rows
        if row["PlanningStatus"] in {"Green", "AboveGreen"}
    ]
    assert all(
        row["SuggestedReplenishmentQty"] == 0
        and row["RecommendedAction"] == "Monitor"
        and row["RecommendationID"] is None
        for row in monitor_rows
    )


def test_be_ddmrp_007_reevaluation_reuses_logical_chain_and_increments_version() -> None:
    first = _prepare_evaluation(lines=[_runtime_line("ITEM-RED", "LOC", "Red", 70)])
    second = _prepare_evaluation(
        request_id="REQ-2",
        lines=[_runtime_line("ITEM-RED", "LOC", "Red", 60)],
        existing=_existing_from(first),
    )

    assert second.chain_records == ()
    assert second.request_result["CreatedLogicalReplenishmentIDs"] == []
    assert second.request_result["ReusedLogicalReplenishmentIDs"] == [
        first.chain_records[0]["LogicalReplenishmentID"]
    ]
    assert second.recommendation_versions[0]["RecommendationVersion"] == 2
    assert second.recommendation_versions[0]["LogicalReplenishmentID"] == (
        first.recommendation_versions[0]["LogicalReplenishmentID"]
    )


def test_be_ddmrp_007_recommendation_predecessor_and_supersession_links_are_bidirectional() -> None:
    first = _prepare_evaluation(lines=[_runtime_line("ITEM-RED", "LOC", "Red", 70)])
    second = _prepare_evaluation(
        request_id="REQ-2",
        lines=[_runtime_line("ITEM-RED", "LOC", "Yellow", 50)],
        existing=_existing_from(first),
    )
    predecessor = first.recommendation_versions[0]
    successor = second.recommendation_versions[0]
    superseded = next(
        event for event in second.events if event["EventType"] == "RecommendationSuperseded"
    )

    assert successor["PredecessorRecommendationID"] == predecessor["RecommendationID"]
    assert superseded["AggregateID"] == predecessor["RecommendationID"]
    assert superseded["RelatedRecommendationID"] == successor["RecommendationID"]
    assert superseded["EventPayload"] == {
        "SupersededByRecommendationID": successor["RecommendationID"],
        "SupersedingEvaluationID": successor["EvaluationID"],
    }


def test_be_ddmrp_007_active_confirmed_graph_creates_adjustment_required_not_second_actionable_version() -> None:
    first = _prepare_evaluation(lines=[_runtime_line("ITEM-RED", "LOC", "Red", 70)])
    existing = _existing_from(first)
    recommendation = first.recommendation_versions[0]
    chain = first.chain_records[0]
    existing["events"] += _confirmation_events(recommendation, chain)
    existing["active_graphs"] = {
        chain["LogicalReplenishmentID"]: _active_graph(chain, recommendation)
    }
    second = _prepare_evaluation(
        request_id="REQ-2",
        lines=[_runtime_line("ITEM-RED", "LOC", "Red", 90)],
        existing=existing,
    )

    adjustment = second.recommendation_versions[0]
    assert adjustment["InitialStatus"] == "AdjustmentRequired"
    assert adjustment["AdjustmentOfRecommendationID"] == recommendation["RecommendationID"]
    assert adjustment["PredecessorRecommendationID"] == recommendation["RecommendationID"]
    assert not any(
        event["EventType"] in {"RecommendationPendingReview", "RecommendationConfirmed"}
        for event in second.events
    )


def test_be_ddmrp_007_terminal_chain_starts_next_cycle_with_new_logical_identity() -> None:
    first = _prepare_evaluation(lines=[_runtime_line("ITEM-RED", "LOC", "Red", 70)])
    existing = _existing_from(first)
    chain = first.chain_records[0]
    existing["events"] += (
        _event(
            "ReplenishmentChainReleased", "ReplenishmentChain", chain["LogicalReplenishmentID"],
            2, "Open", "Released", {"DecisionID": "DEC-1", "Reason": "Closed cycle"},
            chain["OpenedByEvaluationID"], chain["LogicalReplenishmentID"], None,
        ),
    )
    second = _prepare_evaluation(
        request_id="REQ-2",
        lines=[_runtime_line("ITEM-RED", "LOC", "Red", 70)],
        existing=existing,
    )

    assert second.chain_records[0]["CycleNumber"] == 2
    assert second.chain_records[0]["LogicalReplenishmentID"] != chain["LogicalReplenishmentID"]
    assert second.recommendation_versions[0]["RecommendationVersion"] == 1


def test_be_ddmrp_007_same_authority_inputs_produce_deterministic_ids_and_fingerprint() -> None:
    first = _prepare_evaluation()
    second = _prepare_evaluation()

    assert first == second
    assert first.payload_fingerprint == second.payload_fingerprint
    assert first.request_result["EvaluationPayloadFingerprint"] == first.payload_fingerprint
    assert first.evaluation_run["EvaluationAt"] == EVALUATED_AT.isoformat()
    assert all(
        row["EvaluationAt"] == EVALUATED_AT.isoformat()
        for row in first.evaluation_rows
    )


def test_be_ddmrp_007_logical_identity_uses_canonical_json_for_adversarial_identifiers() -> None:
    import json

    from sdbr.ddmrp_replenishment import canonical_stable_id

    identities = [
        {"ItemID": "A|B", "LocationID": "C", "CycleNumber": 1},
        {"ItemID": "A", "LocationID": "B|C", "CycleNumber": 1},
        {"ItemID": '{"x":1}', "LocationID": "[x]", "CycleNumber": 2},
    ]
    canonical = [json.dumps(value, sort_keys=True, separators=(",", ":")) for value in identities]
    ids = [canonical_stable_id("DRL", value) for value in identities]
    row_keys = [
        json.dumps(
            {"ItemID": value["ItemID"], "LocationID": value["LocationID"]},
            sort_keys=True,
            separators=(",", ":"),
        )
        for value in identities
    ]

    assert len(set(canonical)) == len(identities)
    assert len(set(row_keys)) == len(identities)
    assert len(set(ids)) == len(identities)


def test_be_ddmrp_007_immutable_record_field_sets_and_nested_fingerprints_are_exact() -> None:
    from sdbr.ddmrp_replenishment import (
        DEMAND_COMPONENT_FIELDS, EVALUATION_ROW_FIELDS, EVALUATION_RUN_FIELDS,
        EVALUATION_SUMMARY_FIELDS, GATE_FIELDS, ISSUE_RECORD_FIELDS,
        RECOMMENDATION_FIELDS, REPLENISHMENT_CHAIN_FIELDS, REQUEST_RESULT_FIELDS,
        RESPONSE_DATA_FIELDS, SUPPLY_COMPONENT_FIELDS, canonical_fingerprint,
    )

    write_set = _prepare_evaluation(lines=[_runtime_line("ITEM-RED", "LOC", "Red", 70)])
    run = write_set.evaluation_run
    row = write_set.evaluation_rows[0]
    chain = write_set.chain_records[0]
    recommendation = write_set.recommendation_versions[0]
    result = write_set.request_result
    assert set(run) == set(EVALUATION_RUN_FIELDS)
    assert set(run["Summary"]) == set(EVALUATION_SUMMARY_FIELDS)
    assert all(set(issue) == set(ISSUE_RECORD_FIELDS) for issue in run["Issues"])
    assert set(row) == set(EVALUATION_ROW_FIELDS)
    assert set(row["DemandComponents"][0]) == set(DEMAND_COMPONENT_FIELDS)
    assert set(row["SupplyComponents"][0]) == set(SUPPLY_COMPONENT_FIELDS)
    assert set(row["GateCodes"][0]) == set(GATE_FIELDS)
    assert set(chain) == set(REPLENISHMENT_CHAIN_FIELDS)
    assert set(recommendation) == set(RECOMMENDATION_FIELDS)
    assert set(result) == set(REQUEST_RESULT_FIELDS)
    assert set(result["ResponseData"]) == set(RESPONSE_DATA_FIELDS)
    forbidden = {
        "Payload", "CandidateID", "ReservationBatchID", "CapacityReservationIDs",
        "MaterialAllocationIDs",
    }
    assert all(
        not (forbidden & set(record))
        for record in (run, row, chain, recommendation, result)
    )
    for record, fingerprint in (
        (run, "EvaluationFingerprint"), (row, "EvaluationRowFingerprint"),
        (chain, "ChainFingerprint"), (recommendation, "RecommendationFingerprint"),
        (result, "RequestResultFingerprint"),
    ):
        assert record[fingerprint] == canonical_fingerprint(
            {key: value for key, value in record.items() if key != fingerprint}
        )


def test_be_ddmrp_007_event_types_payloads_creation_versions_and_folds_are_exact() -> None:
    from sdbr.ddmrp_replenishment import (
        EVENT_FIELDS, EVENT_PAYLOAD_FIELDS_BY_TYPE, canonical_fingerprint,
        fold_chain_status, fold_recommendation_status,
    )

    write_set = _prepare_evaluation(lines=[_runtime_line("ITEM-RED", "LOC", "Red", 70)])
    chain = write_set.chain_records[0]
    recommendation = write_set.recommendation_versions[0]
    for event in write_set.events:
        assert set(event) == set(EVENT_FIELDS)
        assert set(event["EventPayload"]) == set(
            EVENT_PAYLOAD_FIELDS_BY_TYPE[event["EventType"]]
        )
        assert event["PayloadFingerprint"] == canonical_fingerprint(event["EventPayload"])
        assert event["AggregateVersion"] == 1
    assert fold_chain_status(chain, write_set.events) == "Open"
    assert fold_recommendation_status(recommendation, write_set.events) == "Blocked"


def test_be_ddmrp_007_event_fold_rejects_gaps_duplicates_illegal_creation_and_status_transitions() -> None:
    from sdbr.ddmrp_replenishment import (
        DdmrpReplenishmentConflict, fold_chain_status, fold_recommendation_status,
    )

    write_set = _prepare_evaluation(lines=[_runtime_line("ITEM-RED", "LOC", "Red", 70)])
    chain = write_set.chain_records[0]
    recommendation = write_set.recommendation_versions[0]
    chain_event, recommendation_event = write_set.events
    gap = replace_event(chain_event, AggregateVersion=2)
    duplicate = (chain_event, replace_event(chain_event, EventType="ReplenishmentChainCancelled"))
    illegal_creation = replace_event(chain_event, EventType="ReplenishmentChainCompleted")
    illegal_transition = (
        recommendation_event,
        _event(
            "RecommendationIssued", "Recommendation", recommendation["RecommendationID"],
            2, "Blocked", "Issued", {"OutputRequestID": "OUT-1"},
            recommendation["EvaluationID"], recommendation["LogicalReplenishmentID"],
            recommendation["RecommendationID"],
        ),
    )
    with pytest.raises(DdmrpReplenishmentConflict):
        fold_chain_status(chain, (gap,))
    with pytest.raises(DdmrpReplenishmentConflict):
        fold_chain_status(chain, duplicate)
    with pytest.raises(DdmrpReplenishmentConflict):
        fold_chain_status(chain, (illegal_creation,))
    with pytest.raises(DdmrpReplenishmentConflict):
        fold_recommendation_status(recommendation, illegal_transition)


def test_be_ddmrp_007_issue_records_persist_full_gate_context() -> None:
    from sdbr.ddmrp_replenishment import canonical_fingerprint

    write_set = _prepare_evaluation(lines=[_runtime_line("ITEM-RED", "LOC", "Red", 70)])
    issues = write_set.evaluation_run["Issues"]
    assert [issue["Code"] for issue in issues] == _gate_codes()
    for issue in issues:
        gate = next(gate for gate in _evaluation_inputs()[1] if gate.code == issue["Code"])
        assert issue["Severity"] == "Blocking"
        assert issue["Message"] == gate.message
        assert issue["ItemID"] is None and issue["LocationID"] is None
        assert issue["BlocksOperationalAction"] is True
        assert issue["IssueFingerprint"] == canonical_fingerprint(
            {key: value for key, value in issue.items() if key != "IssueFingerprint"}
        )


def test_be_ddmrp_007_supply_components_use_only_authoritative_contract_fields() -> None:
    from sdbr.ddmrp_replenishment import DdmrpReplenishmentConflict, SUPPLY_COMPONENT_FIELDS

    line = _runtime_line("ITEM-RED", "LOC", "Red", 70)
    write_set = _prepare_evaluation(lines=[line])
    assert set(write_set.evaluation_rows[0]["SupplyComponents"][0]) == set(
        SUPPLY_COMPONENT_FIELDS
    )
    invalid = deepcopy(line)
    invalid["SupplyComponents"][0]["SourceType"] = "PurchaseOrder"
    with pytest.raises(DdmrpReplenishmentConflict, match="extra"):
        _prepare_evaluation(lines=[invalid])


def _prepare_evaluation(
    *,
    request_id: str = "REQ-1",
    lines: list[dict[str, object]] | None = None,
    existing: dict[str, object] | None = None,
):
    from sdbr.ddmrp_replenishment import prepare_ddmrp_evaluation

    signature, gates, runtime_result = _evaluation_inputs(lines=lines)
    existing = existing or {}
    return prepare_ddmrp_evaluation(
        evaluation_request_id=request_id,
        recorded_at=EVALUATED_AT,
        actor_id="planner-1",
        runtime_result=runtime_result,
        authority_signature=signature,
        gates=gates,
        existing_chains=existing.get("chains", {}),
        existing_recommendations=existing.get("recommendations", {}),
        existing_events=existing.get("events", ()),
        active_replenishment_graphs=existing.get("active_graphs", {}),
    )


def _evaluation_inputs(*, lines: list[dict[str, object]] | None = None):
    from sdbr.ddmrp_replenishment import build_read_only_authority_signature

    package = _package_record(production_accepted=False)
    signature, gates = build_read_only_authority_signature(
        package_record=package,
        operating_model_configuration=_operating_model_configuration(package),
        relevant_planning_ledger=_ledger_identity(),
        evaluated_at=EVALUATED_AT,
    )
    rows = lines or [
        _runtime_line("ITEM-ABOVE", "LOC", "AboveGreen", 0),
        _runtime_line("ITEM-GREEN", "LOC", "Green", 0),
        _runtime_line("ITEM-RED", "LOC", "Red", 70),
        _runtime_line("ITEM-YELLOW", "LOC", "Yellow", 40),
    ]
    return signature, gates, {
        "EvaluationMode": "DDMRPNetFlowV1",
        "Boundary": "read-only",
        "EvaluatedAt": EVALUATED_AT.isoformat(),
        "Summary": {},
        "Lines": rows,
        "Issues": [],
    }


def _runtime_line(
    item_id: str, location_id: str, status: str, suggested_qty: float
) -> dict[str, object]:
    return {
        "ItemID": item_id, "LocationID": location_id, "BufferProfileID": "BP-1",
        "DLTMinutes": 1440, "OnHandQty": 10.0, "QualifiedOnHandQty": 10.0,
        "QualifiedOpenSupplyQty": 5.0, "QualifiedDemandQty": 15.0,
        "NetFlowPosition": 0.0, "TopOfRed": 20.0, "TopOfYellow": 50.0,
        "TopOfGreen": 100.0, "PlanningStatus": status, "ExecutionStatus": "Red",
        "SuggestedReplenishmentQty": suggested_qty,
        "RecommendedAction": "Replenish" if suggested_qty else "Monitor",
        "DemandComponents": [{
            "DemandID": f"D-{item_id}", "DemandType": "CustomerOrder",
            "DemandQty": 15.0, "DemandDueAt": EVALUATED_AT.isoformat(),
            "IsQualifiedSpike": False, "Uom": "EA",
        }],
        "SupplyComponents": [{
            "SupplyID": f"S-{item_id}", "SupplyQty": 5.0,
            "ExpectedAt": EVALUATED_AT.isoformat(), "Status": "Open", "Uom": "EA",
        }],
        "PhysicalOnHandQty": 12.0, "AuthorityAllocatedQty": 2.0,
        "AuthorityAvailableQty": 10.0, "QualityState": "Unrestricted", "Uom": "EA",
    }


def _existing_from(write_set) -> dict[str, object]:
    return {
        "chains": {row["LogicalReplenishmentID"]: deepcopy(row) for row in write_set.chain_records},
        "recommendations": {
            row["RecommendationID"]: deepcopy(row) for row in write_set.recommendation_versions
        },
        "events": tuple(deepcopy(write_set.events)),
        "active_graphs": {},
    }


def _gate_codes() -> list[str]:
    return [
        "DLT_TARGET_SEMANTICS_INSUFFICIENT",
        "OPERATIONAL_AUTHORITY_NOT_ACCEPTED",
        "PLANNING_ADVICE_CONTRACT_NOT_ACCEPTED",
        "PLAN_BOM_FEASIBILITY_CONTRACT_NOT_ACCEPTED",
    ]


def _event(
    event_type: str, aggregate_type: str, aggregate_id: str, version: int,
    status_before: str | None, status_after: str, payload: dict[str, object],
    evaluation_id: str, logical_id: str, recommendation_id: str | None,
    *, related_id: str | None = None,
) -> dict[str, object]:
    from sdbr.ddmrp_replenishment import canonical_fingerprint, canonical_stable_id

    return {
        "EventID": canonical_stable_id("DRE", {
            "AggregateType": aggregate_type, "AggregateID": aggregate_id,
            "AggregateVersion": version, "EventType": event_type,
        }),
        "EventType": event_type, "AggregateType": aggregate_type,
        "AggregateID": aggregate_id, "AggregateVersion": version,
        "EvaluationID": evaluation_id, "LogicalReplenishmentID": logical_id,
        "RecommendationID": recommendation_id, "RelatedRecommendationID": related_id,
        "StatusBefore": status_before, "StatusAfter": status_after,
        "OccurredAt": EVALUATED_AT.isoformat(), "ActorID": "planner-1",
        "CausationID": "REQ-LIFECYCLE", "CorrelationID": evaluation_id,
        "IdempotencyKey": f"IDEM-{event_type}-{version}", "TraceID": logical_id,
        "EventPayload": deepcopy(payload), "PayloadFingerprint": canonical_fingerprint(payload),
    }


def replace_event(event: dict[str, object], **changes: object) -> dict[str, object]:
    from sdbr.ddmrp_replenishment import canonical_fingerprint, canonical_stable_id

    changed = deepcopy(event)
    changed.update(changes)
    changed["EventID"] = canonical_stable_id("DRE", {
        "AggregateType": changed["AggregateType"], "AggregateID": changed["AggregateID"],
        "AggregateVersion": changed["AggregateVersion"], "EventType": changed["EventType"],
    })
    payload = changed["EventPayload"]
    changed["PayloadFingerprint"] = canonical_fingerprint(payload)
    return changed


def _confirmation_events(recommendation, chain) -> tuple[dict[str, object], ...]:
    logical_id = chain["LogicalReplenishmentID"]
    recommendation_id = recommendation["RecommendationID"]
    evaluation_id = recommendation["EvaluationID"]
    return (
        _event(
            "RecommendationPendingReview", "Recommendation", recommendation_id, 2,
            "Blocked", "PendingReview", {
                "AdviceType": "Buy",
                "AuthoritySignatureFingerprint": recommendation["AuthoritySignatureFingerprint"],
            }, evaluation_id, logical_id, recommendation_id,
        ),
        _event(
            "RecommendationConfirmed", "Recommendation", recommendation_id, 3,
            "PendingReview", "Confirmed", {
                "DecisionID": "DEC-1", "AdviceType": "Buy", "Reason": "Approved",
            }, evaluation_id, logical_id, recommendation_id,
        ),
        _event(
            "ReplenishmentChainActivated", "ReplenishmentChain", logical_id, 2,
            "Open", "ActiveGraph", {
                "DecisionID": "DEC-1", "AdviceType": "Buy", "ActiveGraphID": logical_id,
            }, evaluation_id, logical_id, recommendation_id,
        ),
    )


def _active_graph(chain, recommendation) -> dict[str, object]:
    return {
        "LogicalReplenishmentID": chain["LogicalReplenishmentID"],
        "RecommendationID": recommendation["RecommendationID"],
        "ItemID": chain["ItemID"], "LocationID": chain["LocationID"], "Uom": "EA",
        "GraphStatus": "ActivePlanReservation", "DemandCommitmentID": "D-1",
        "ReservationBatchID": "B-1", "PlannedManufacturingCandidateID": None,
        "FormalSupplyID": None, "RecordVersion": 1,
    }


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
