"""Acceptance evidence for BE-DDMRP-007 and UI-DDMRP-003."""

from __future__ import annotations

from copy import deepcopy

import pytest

from test_ddmrp_replenishment import (
    EVALUATED_AT,
    _active_graph,
    _confirmation_events,
    _evaluation_inputs,
    _existing_from,
    _ledger_identity,
    _operating_model_configuration,
    _package_record,
    _prepare_evaluation,
    _runtime_line,
)


BOUNDARY = (
    "Read-only SDBR planning evaluation; no ERP order, inventory authority, "
    "or operational reservation write."
)


def test_be_ddmrp_007_view_returns_latest_rows_plus_older_active_or_adjustment_chains() -> None:
    first = _prepare_evaluation(
        lines=[_runtime_line("ITEM-RED", "LOC", "Red", 70)]
    )
    recommendation = first.recommendation_versions[0]
    chain = first.chain_records[0]
    existing = _existing_from(first)
    existing["events"] = _events_with_run_provenance(
        (*existing["events"], *_confirmation_events(recommendation, chain)),
        first.evaluation_run,
    )
    existing["active_graphs"] = {
        chain["LogicalReplenishmentID"]: _active_graph(chain, recommendation)
    }
    second = _prepare_distinct_evaluation(
        request_id="REQ-2",
        lines=[_runtime_line("ITEM-RED", "LOC", "Yellow", 55)],
        existing=existing,
    )
    ledgers = _ledgers(first, second, existing=existing)

    result = _build(**ledgers)

    assert result["Evaluation"]["EvaluationID"] == second.evaluation_run["EvaluationID"]
    assert [(row["ItemID"], row["PlanningStatus"]) for row in result["Rows"]] == [
        ("ITEM-RED", "Yellow")
    ]
    assert [row["RecommendationVersion"] for row in result["History"]] == [1, 2]
    assert result["History"][0]["CurrentStatus"] == "Superseded"
    assert result["History"][1]["CurrentStatus"] == "AdjustmentRequired"
    assert result["ActiveGraphs"][0]["RecommendationID"] == recommendation[
        "RecommendationID"
    ]
    assert result["ActiveGraphs"][0]["AdjustmentRequired"] is True
    assert result["Summary"]["ActiveGraphCount"] == 1
    assert result["Summary"]["AdjustmentRequiredCount"] == 1


def test_be_ddmrp_007_view_exposes_null_target_and_business_gate_codes() -> None:
    write_set = _prepare_evaluation(
        lines=[_runtime_line("ITEM-RED", "LOC", "Red", 70)]
    )

    result = _build(**_ledgers(write_set))

    row = result["Rows"][0]
    assert row["StandardTargetReceiptAt"] is None
    assert row["TargetStatusCode"] == "DLT_TARGET_SEMANTICS_INSUFFICIENT"
    assert [gate["Code"] for gate in row["GateCodes"]] == [
        issue["Code"] for issue in result["Issues"]
    ]
    assert all(issue["Severity"] == "Blocking" for issue in result["Issues"])
    assert result["Evaluation"]["OperationalActionAllowed"] is False
    assert row["OperationalActionAllowed"] is False


def test_be_ddmrp_007_view_never_exposes_frozen_payload_or_evidence_rows() -> None:
    write_set = _prepare_evaluation()

    result = _build(**_ledgers(write_set))
    keys = _nested_keys(result)
    rendered = repr(result)

    assert "Payload" not in keys
    assert "EventPayload" not in keys
    assert "AuthoritySignature" not in keys
    assert "EvaluationRequestID" not in keys
    assert "RecordedBy" not in keys
    assert "ParameterAuthorityEvidence" not in rendered
    assert "ApprovalEvidenceID" not in rendered
    assert "DemandCommitmentID" not in rendered
    assert "CapacityReservationID" not in rendered
    assert "MaterialAllocationID" not in rendered
    assert "DecisionID" not in rendered
    assert result["Boundary"] == BOUNDARY


def test_be_ddmrp_007_view_rejects_duplicate_chain_or_orphan_recommendation() -> None:
    from sdbr.ddmrp_replenishment import (
        DdmrpReplenishmentConflict,
        canonical_fingerprint,
    )

    write_set = _prepare_evaluation(
        lines=[_runtime_line("ITEM-RED", "LOC", "Red", 70)]
    )
    ledgers = _ledgers(write_set)
    chain = next(iter(ledgers["chains"].values()))
    ledgers["chains"]["DUPLICATE-MAPPING-KEY"] = deepcopy(chain)

    with pytest.raises(DdmrpReplenishmentConflict):
        _build(**ledgers)

    orphaned = _ledgers(write_set)
    orphaned["chains"].clear()
    with pytest.raises(DdmrpReplenishmentConflict):
        _build(**orphaned)

    divergent = _ledgers(write_set)
    row = next(iter(divergent["evaluation_rows"].values()))
    row["SuggestedReplenishmentQty"] = 999
    row["EvaluationRowFingerprint"] = canonical_fingerprint({
        key: value for key, value in row.items()
        if key != "EvaluationRowFingerprint"
    })
    with pytest.raises(DdmrpReplenishmentConflict):
        _build(**divergent)


def test_be_ddmrp_007_view_is_deterministic_and_deep_copied() -> None:
    write_set = _prepare_evaluation()
    ledgers = _ledgers(write_set)

    first = _build(**ledgers)
    second = _build(**ledgers)
    assert first == second

    first["Rows"][0]["DemandComponents"][0]["DemandQty"] = -999
    first["Issues"][0]["Message"] = "changed"
    assert _build(**ledgers) == second
    assert next(iter(ledgers["evaluation_rows"].values()))["DemandComponents"][0][
        "DemandQty"
    ] != -999


def test_be_ddmrp_007_view_empty_state_shape_is_stable() -> None:
    from sdbr.ddmrp_replenishment_view import (
        SUMMARY_VIEW_FIELDS,
        TECHNICAL_DETAILS_FIELDS,
        WORKBENCH_FIELDS,
    )

    result = _build(
        evaluation_runs={},
        evaluation_rows={},
        chains={},
        recommendations={},
        events=(),
        active_replenishment_graphs={},
    )

    assert tuple(result) == WORKBENCH_FIELDS
    assert result["Evaluation"] is None
    assert tuple(result["Summary"]) == SUMMARY_VIEW_FIELDS
    assert set(result["Summary"].values()) == {0}
    assert result["Rows"] == []
    assert result["ActiveGraphs"] == []
    assert result["History"] == []
    assert result["Issues"] == []
    assert result["Boundary"] == BOUNDARY
    assert tuple(result["TechnicalDetails"]) == TECHNICAL_DETAILS_FIELDS
    assert all(value in (None, []) for value in result["TechnicalDetails"].values())


def test_be_ddmrp_007_view_nested_projection_allowlists_are_exact() -> None:
    from sdbr.ddmrp_replenishment import (
        DEMAND_COMPONENT_FIELDS,
        GATE_FIELDS,
        SUPPLY_COMPONENT_FIELDS,
    )
    from sdbr.ddmrp_replenishment_view import (
        ACTIVE_GRAPH_VIEW_FIELDS,
        EVALUATION_VIEW_FIELDS,
        HISTORY_EVENT_FIELDS,
        HISTORY_VIEW_FIELDS,
        ISSUE_VIEW_FIELDS,
        RECOMMENDATION_FINGERPRINT_FIELDS,
        ROW_VIEW_FIELDS,
        SUMMARY_VIEW_FIELDS,
        TECHNICAL_DETAILS_FIELDS,
        WORKBENCH_FIELDS,
    )

    first = _prepare_evaluation(
        lines=[_runtime_line("ITEM-RED", "LOC", "Red", 70)]
    )
    recommendation = first.recommendation_versions[0]
    chain = first.chain_records[0]
    existing = _existing_from(first)
    existing["events"] = _events_with_run_provenance(
        (*existing["events"], *_confirmation_events(recommendation, chain)),
        first.evaluation_run,
    )
    existing["active_graphs"] = {
        chain["LogicalReplenishmentID"]: _active_graph(chain, recommendation)
    }
    result = _build(**_ledgers(first, existing=existing))

    assert tuple(result) == WORKBENCH_FIELDS
    assert tuple(result["Evaluation"]) == EVALUATION_VIEW_FIELDS
    assert tuple(result["Summary"]) == SUMMARY_VIEW_FIELDS
    assert tuple(result["Rows"][0]) == ROW_VIEW_FIELDS
    assert tuple(result["Rows"][0]["DemandComponents"][0]) == DEMAND_COMPONENT_FIELDS
    assert tuple(result["Rows"][0]["SupplyComponents"][0]) == SUPPLY_COMPONENT_FIELDS
    assert tuple(result["Rows"][0]["GateCodes"][0]) == GATE_FIELDS
    assert tuple(result["ActiveGraphs"][0]) == ACTIVE_GRAPH_VIEW_FIELDS
    assert tuple(result["History"][0]) == HISTORY_VIEW_FIELDS
    assert tuple(result["History"][0]["Events"][0]) == HISTORY_EVENT_FIELDS
    assert tuple(result["Issues"][0]) == ISSUE_VIEW_FIELDS
    assert tuple(result["TechnicalDetails"]) == TECHNICAL_DETAILS_FIELDS
    assert tuple(result["TechnicalDetails"]["RecommendationFingerprints"][0]) == (
        RECOMMENDATION_FINGERPRINT_FIELDS
    )


@pytest.mark.parametrize(
    "field",
    (
        "Uom",
        "GraphStatus",
        "CandidateStatus",
        "PlannedSupplyQty",
        "PlanningRunID",
        "FormalOrderRef",
        "FormalSupplyID",
    ),
)
def test_be_ddmrp_007_view_rejects_nested_active_graph_display_values(
    field: str,
) -> None:
    """BE-DDMRP-007: graph display leaves cannot carry raw evidence payloads."""
    write_set = _prepare_evaluation(
        lines=[_runtime_line("ITEM-RED", "LOC", "Red", 70)]
    )
    recommendation = write_set.recommendation_versions[0]
    chain = write_set.chain_records[0]
    ledgers = _ledgers(write_set)
    graph = _active_graph(chain, recommendation)
    graph.update({
        "CandidateStatus": "Planned",
        "PlannedSupplyQty": 70.0,
        "PlanningRunID": "PLAN-1",
    })
    if field != "FormalSupplyID":
        graph["FormalOrderRef"] = "ORDER-1"
    graph[field] = {"Payload": {"InventoryPositions": [{"secret": "raw"}]}}
    ledgers["active_replenishment_graphs"] = {
        chain["LogicalReplenishmentID"]: graph
    }

    from sdbr.ddmrp_replenishment import DdmrpReplenishmentConflict

    with pytest.raises(DdmrpReplenishmentConflict):
        _build(**ledgers)


def test_be_ddmrp_007_view_rejects_unallowlisted_active_graph_source_field() -> None:
    """BE-DDMRP-007: active graphs have an exact safe source contract."""
    write_set = _prepare_evaluation(
        lines=[_runtime_line("ITEM-RED", "LOC", "Red", 70)]
    )
    recommendation = write_set.recommendation_versions[0]
    chain = write_set.chain_records[0]
    ledgers = _ledgers(write_set)
    graph = _active_graph(chain, recommendation)
    graph["Payload"] = {"InventoryPositions": [{"secret": "raw"}]}
    ledgers["active_replenishment_graphs"] = {
        chain["LogicalReplenishmentID"]: graph
    }

    from sdbr.ddmrp_replenishment import DdmrpReplenishmentConflict

    with pytest.raises(DdmrpReplenishmentConflict):
        _build(**ledgers)


@pytest.mark.parametrize(
    ("field", "forged_value"),
    (
        ("ActorID", "forged-operator"),
        ("OccurredAt", "2026-07-12T01:00:00+00:00"),
    ),
)
def test_be_ddmrp_007_view_rejects_forged_history_actor_or_time_provenance(
    field: str,
    forged_value: str,
) -> None:
    """BE-DDMRP-007: history event actor/time must match its immutable run."""
    write_set = _prepare_evaluation(
        lines=[_runtime_line("ITEM-RED", "LOC", "Red", 70)]
    )
    ledgers = _ledgers(write_set)
    event = next(
        event for event in ledgers["events"]
        if event["EventType"] == "RecommendationVersionCreated"
    )
    event[field] = forged_value

    from sdbr.ddmrp_replenishment import DdmrpReplenishmentConflict

    with pytest.raises(DdmrpReplenishmentConflict):
        _build(**ledgers)


def _build(**ledgers):
    from sdbr.ddmrp_replenishment_view import build_ddmrp_replenishment_workbench

    return build_ddmrp_replenishment_workbench(**ledgers)


def _prepare_distinct_evaluation(*, request_id, lines, existing):
    from sdbr.ddmrp_replenishment import (
        build_read_only_authority_signature,
        prepare_ddmrp_evaluation,
    )

    package = _package_record(production_accepted=False)
    signature, gates = build_read_only_authority_signature(
        package_record=package,
        operating_model_configuration=_operating_model_configuration(package),
        relevant_planning_ledger=_ledger_identity(quantity=6),
        evaluated_at=EVALUATED_AT,
    )
    _, _, runtime_result = _evaluation_inputs(lines=lines)
    return prepare_ddmrp_evaluation(
        evaluation_request_id=request_id,
        recorded_at=EVALUATED_AT,
        actor_id="planner-1",
        runtime_result=runtime_result,
        authority_signature=signature,
        gates=gates,
        existing_chains=existing["chains"],
        existing_recommendations=existing["recommendations"],
        existing_events=existing["events"],
        active_replenishment_graphs=existing["active_graphs"],
    )


def _ledgers(*write_sets, existing=None):
    evaluation_runs = {}
    evaluation_rows = {}
    chains = deepcopy((existing or {}).get("chains", {}))
    recommendations = deepcopy((existing or {}).get("recommendations", {}))
    events = list(deepcopy((existing or {}).get("events", ())))
    active_graphs = deepcopy((existing or {}).get("active_graphs", {}))
    seen_events = {event["EventID"] for event in events}
    for write_set in write_sets:
        evaluation_runs[write_set.evaluation_run["EvaluationID"]] = deepcopy(
            write_set.evaluation_run
        )
        evaluation_rows.update({
            row["EvaluationRowID"]: deepcopy(row)
            for row in write_set.evaluation_rows
        })
        chains.update({
            row["LogicalReplenishmentID"]: deepcopy(row)
            for row in write_set.chain_records
        })
        recommendations.update({
            row["RecommendationID"]: deepcopy(row)
            for row in write_set.recommendation_versions
        })
        for event in write_set.events:
            if event["EventID"] not in seen_events:
                events.append(deepcopy(event))
                seen_events.add(event["EventID"])
    return {
        "evaluation_runs": evaluation_runs,
        "evaluation_rows": evaluation_rows,
        "chains": chains,
        "recommendations": recommendations,
        "events": tuple(events),
        "active_replenishment_graphs": active_graphs,
    }


def _events_with_run_provenance(events, run):
    return tuple({
        **deepcopy(event),
        "CausationID": run["EvaluationRequestID"],
        "CorrelationID": run["EvaluationID"],
        "IdempotencyKey": event["EventID"],
        "TraceID": event["LogicalReplenishmentID"],
        "OccurredAt": run["RecordedAt"],
        "ActorID": run["RecordedBy"],
    } for event in events)


def _nested_keys(value):
    if isinstance(value, dict):
        return set(value).union(*(_nested_keys(item) for item in value.values()), set())
    if isinstance(value, list):
        return set().union(*(_nested_keys(item) for item in value), set())
    return set()
