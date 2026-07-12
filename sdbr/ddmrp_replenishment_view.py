from __future__ import annotations

from copy import deepcopy
from typing import Iterable, Mapping

from sdbr.ddmrp_replenishment import (
    CHAIN_ACTIVE_STATUSES,
    CHAIN_TERMINAL_STATUSES,
    DEMAND_COMPONENT_FIELDS,
    GATE_FIELDS,
    ISSUE_RECORD_FIELDS,
    SUPPLY_COMPONENT_FIELDS,
    DdmrpReplenishmentConflict,
    _validate_evaluation_row_contract,
    _validate_evaluation_run_contract,
    _validate_event_references,
    _validate_existing_chains,
    _validate_existing_recommendations,
)


WORKBENCH_FIELDS = (
    "Evaluation", "Summary", "Rows", "ActiveGraphs", "History", "Issues",
    "Boundary", "TechnicalDetails",
)
EVALUATION_VIEW_FIELDS = (
    "EvaluationID", "EvaluationAt", "RecordedAt", "RuntimePlanningInputPackageID",
    "RuntimePlanningInputPackageVersion", "OperatingModelConfigurationID",
    "DDMRPConfigurationID", "OperationalActionAllowed",
)
SUMMARY_VIEW_FIELDS = (
    "RedCount", "YellowCount", "GreenCount", "AboveGreenCount",
    "BlockedRecommendationCount", "PendingReviewCount",
    "AdjustmentRequiredCount", "ActiveGraphCount",
)
ROW_VIEW_FIELDS = (
    "RowKey", "ItemID", "LocationID", "Uom", "PlanningStatus", "ExecutionStatus",
    "BufferPercent", "QualifiedOnHandQty", "PhysicalOnHandQty",
    "AuthorityAllocatedQty", "AuthorityAvailableQty", "QualifiedOpenSupplyQty",
    "QualifiedDemandQty", "NetFlowPosition", "TopOfRed", "TopOfYellow",
    "TopOfGreen", "SuggestedReplenishmentQty", "StandardTargetReceiptAt",
    "TargetStatusCode", "RecommendedAction", "RecommendationID",
    "RecommendationVersion", "RecommendationStatus", "GateCodes",
    "DemandComponents", "SupplyComponents", "OperationalActionAllowed",
    "PendingReviewCount",
)
ACTIVE_GRAPH_VIEW_FIELDS = (
    "LogicalReplenishmentID", "RecommendationID", "RecommendationVersion",
    "ItemID", "LocationID", "Uom", "GraphStatus", "CandidateStatus",
    "PlannedSupplyQty", "PlanningRunID", "FormalOrderRef",
    "AdjustmentRequired", "LastEventAt",
)
ACTIVE_GRAPH_SOURCE_FIELDS = frozenset({
    "LogicalReplenishmentID", "RecommendationID", "ItemID", "LocationID",
    "Uom", "GraphStatus", "CandidateStatus", "PlannedSupplyQty",
    "PlanningRunID", "FormalOrderRef", "FormalSupplyID", "DemandCommitmentID",
    "ReservationBatchID", "PlannedManufacturingCandidateID", "RecordVersion",
})
_ACTIVE_GRAPH_REQUIRED_SOURCE_FIELDS = frozenset({
    "LogicalReplenishmentID", "RecommendationID", "ItemID", "LocationID",
})
_ACTIVE_GRAPH_TEXT_SOURCE_FIELDS = frozenset({
    "Uom", "GraphStatus", "CandidateStatus", "PlanningRunID", "FormalOrderRef",
    "FormalSupplyID", "DemandCommitmentID", "ReservationBatchID",
    "PlannedManufacturingCandidateID",
})
HISTORY_VIEW_FIELDS = (
    "LogicalReplenishmentID", "RecommendationID", "RecommendationVersion",
    "PredecessorRecommendationID", "SupersededByRecommendationID",
    "AdjustmentOfRecommendationID", "InitialStatus", "CurrentStatus",
    "SuggestedReplenishmentQty", "StandardTargetReceiptAt", "EvaluationID",
    "EvaluationAt", "LastEventAt", "Events",
)
HISTORY_EVENT_FIELDS = (
    "EventID", "EventType", "OccurredAt", "ActorID",
    "RelatedRecommendationID", "StatusBefore", "StatusAfter",
)
ISSUE_VIEW_FIELDS = (
    "Severity", "Code", "Message", "ItemID", "LocationID",
    "BlocksOperationalAction",
)
TECHNICAL_DETAILS_FIELDS = (
    "EvaluationID", "EvaluationFingerprint", "AuthoritySignatureFingerprint",
    "RelevantPlanningLedgerIdentity", "RelevantPlanningLedgerFingerprint",
    "RuntimeSnapshotID", "ParameterAuthorityFingerprint",
    "RecommendationFingerprints",
)
RECOMMENDATION_FINGERPRINT_FIELDS = (
    "RecommendationID", "RecommendationFingerprint",
)

BOUNDARY = (
    "Read-only SDBR planning evaluation; no ERP order, inventory authority, "
    "or operational reservation write."
)
_PLANNING_STATUS_RANK = {"Red": 0, "Yellow": 1, "Green": 2, "AboveGreen": 3}


def build_ddmrp_replenishment_workbench(
    *,
    evaluation_runs: Mapping[str, Mapping[str, object]],
    evaluation_rows: Mapping[str, Mapping[str, object]],
    chains: Mapping[str, Mapping[str, object]],
    recommendations: Mapping[str, Mapping[str, object]],
    events: tuple[Mapping[str, object], ...],
    active_replenishment_graphs: Mapping[str, Mapping[str, object]],
) -> dict[str, object]:
    if not evaluation_runs:
        if any((evaluation_rows, chains, recommendations, events, active_replenishment_graphs)):
            raise DdmrpReplenishmentConflict(
                "DDMRP workbench child ledger exists without an evaluation."
            )
        return _empty_workbench()

    run_rows = _validated_runs(evaluation_runs)
    event_rows = tuple(deepcopy(tuple(events)))
    chain_rows, chain_statuses = _validate_existing_chains(
        chains, event_rows, active_replenishment_graphs
    )
    recommendation_rows, recommendation_statuses = _validate_existing_recommendations(
        recommendations, event_rows, chain_rows
    )
    _validate_event_references(
        event_rows,
        chain_rows,
        recommendation_rows,
        active_replenishment_graphs,
    )
    row_rows = _validated_rows(
        evaluation_rows=evaluation_rows,
        evaluation_runs=run_rows,
        recommendations=recommendation_rows,
    )
    _validate_graph_links(
        active_replenishment_graphs,
        chain_rows,
        chain_statuses,
        recommendation_rows,
    )
    _validate_provenance_links(
        run_rows,
        row_rows,
        chain_rows,
        recommendation_rows,
        event_rows,
    )
    _validate_single_current_version(recommendation_rows, recommendation_statuses)

    latest = max(
        run_rows.values(),
        key=lambda run: (
            str(run["EvaluationAt"]), str(run["RecordedAt"]), str(run["EvaluationID"])
        ),
    )
    latest_id = str(latest["EvaluationID"])
    latest_rows = [
        row for row in row_rows.values() if row["EvaluationID"] == latest_id
    ]
    _validate_latest_gates(latest, latest_rows)

    visible_chain_ids = {
        str(recommendation_rows[str(row["RecommendationID"])]["LogicalReplenishmentID"])
        for row in latest_rows
        if row["RecommendationID"] is not None
    }
    visible_chain_ids.update(str(key) for key in active_replenishment_graphs)
    visible_chain_ids.update(
        logical_id for logical_id, status in chain_statuses.items()
        if status in CHAIN_ACTIVE_STATUSES
    )
    visible_recommendations = [
        recommendation for recommendation in recommendation_rows.values()
        if recommendation["LogicalReplenishmentID"] in visible_chain_ids
    ]

    projected_rows = [
        _project_row(row, recommendation_rows, recommendation_statuses)
        for row in latest_rows
    ]
    projected_rows.sort(key=lambda row: (
        _PLANNING_STATUS_RANK.get(str(row["PlanningStatus"]), 99),
        _nullable_number_sort(row["BufferPercent"]),
        str(row["ItemID"]),
        str(row["LocationID"]),
    ))
    projected_graphs = [
        _project_active_graph(
            graph,
            chain_statuses=chain_statuses,
            recommendations=recommendation_rows,
            recommendation_statuses=recommendation_statuses,
            events=event_rows,
        )
        for graph in active_replenishment_graphs.values()
    ]
    projected_graphs.sort(key=lambda graph: (
        str(graph["ItemID"]), str(graph["LocationID"]),
        str(graph["LogicalReplenishmentID"]),
    ))
    projected_history = [
        _project_history(
            recommendation,
            recommendation_statuses=recommendation_statuses,
            evaluation_runs=run_rows,
            events=event_rows,
        )
        for recommendation in visible_recommendations
    ]
    projected_history.sort(key=lambda history: (
        str(recommendation_rows[str(history["RecommendationID"])]["ItemID"]),
        str(recommendation_rows[str(history["RecommendationID"])]["LocationID"]),
        int(history["RecommendationVersion"]),
        str(history["RecommendationID"]),
    ))
    projected_issues = [_project(issue, ISSUE_VIEW_FIELDS) for issue in latest["Issues"]]
    projected_issues.sort(key=lambda issue: (
        str(issue["Severity"]), str(issue["Code"]),
        str(issue["ItemID"] or ""), str(issue["LocationID"] or ""),
    ))

    summary = _summary(projected_rows, projected_graphs, projected_history)
    signature = latest["AuthoritySignature"]
    technical = {
        "EvaluationID": latest["EvaluationID"],
        "EvaluationFingerprint": latest["EvaluationFingerprint"],
        "AuthoritySignatureFingerprint": latest["AuthoritySignatureFingerprint"],
        "RelevantPlanningLedgerIdentity": latest["RelevantPlanningLedgerIdentity"],
        "RelevantPlanningLedgerFingerprint": latest["RelevantPlanningLedgerFingerprint"],
        "RuntimeSnapshotID": latest["RuntimeSnapshotID"],
        "ParameterAuthorityFingerprint": signature["parameter_authority_fingerprint"],
        "RecommendationFingerprints": [
            _project(recommendation, RECOMMENDATION_FINGERPRINT_FIELDS)
            for recommendation in sorted(
                visible_recommendations,
                key=lambda row: str(row["RecommendationID"]),
            )
        ],
    }
    result = {
        "Evaluation": _project(latest, EVALUATION_VIEW_FIELDS),
        "Summary": summary,
        "Rows": projected_rows,
        "ActiveGraphs": projected_graphs,
        "History": projected_history,
        "Issues": projected_issues,
        "Boundary": BOUNDARY,
        "TechnicalDetails": technical,
    }
    return deepcopy(result)


def _validated_runs(
    evaluation_runs: Mapping[str, Mapping[str, object]],
) -> dict[str, dict[str, object]]:
    result: dict[str, dict[str, object]] = {}
    for key, source in evaluation_runs.items():
        if not isinstance(source, Mapping):
            raise DdmrpReplenishmentConflict("DDMRP evaluation must be a mapping.")
        run = deepcopy(dict(source))
        _validate_evaluation_run_contract(run)
        evaluation_id = str(run["EvaluationID"])
        if key != evaluation_id or evaluation_id in result:
            raise DdmrpReplenishmentConflict("DDMRP evaluation mapping identity mismatch.")
        result[evaluation_id] = run
    return result


def _validated_rows(
    *,
    evaluation_rows: Mapping[str, Mapping[str, object]],
    evaluation_runs: Mapping[str, Mapping[str, object]],
    recommendations: Mapping[str, Mapping[str, object]],
) -> dict[str, dict[str, object]]:
    result: dict[str, dict[str, object]] = {}
    scopes: set[tuple[str, str, str]] = set()
    for key, source in evaluation_rows.items():
        if not isinstance(source, Mapping):
            raise DdmrpReplenishmentConflict("DDMRP evaluation row must be a mapping.")
        row = deepcopy(dict(source))
        _validate_evaluation_row_contract(row)
        row_id = str(row["EvaluationRowID"])
        evaluation_id = str(row["EvaluationID"])
        scope = (evaluation_id, str(row["ItemID"]), str(row["LocationID"]))
        if key != row_id or row_id in result or scope in scopes:
            raise DdmrpReplenishmentConflict("DDMRP evaluation row identity is duplicated.")
        if evaluation_id not in evaluation_runs:
            raise DdmrpReplenishmentConflict("DDMRP evaluation row run is missing.")
        if row["EvaluationAt"] != evaluation_runs[evaluation_id]["EvaluationAt"]:
            raise DdmrpReplenishmentConflict("DDMRP evaluation row time differs from its run.")
        recommendation_id = row["RecommendationID"]
        if recommendation_id is not None:
            recommendation = recommendations.get(str(recommendation_id))
            if recommendation is None or recommendation["EvaluationRowID"] != row_id:
                raise DdmrpReplenishmentConflict(
                    "DDMRP evaluation row recommendation is orphaned."
                )
        scopes.add(scope)
        result[row_id] = row
    return result


def _validate_graph_links(
    active_graphs: Mapping[str, Mapping[str, object]],
    chains: Mapping[str, Mapping[str, object]],
    chain_statuses: Mapping[str, str],
    recommendations: Mapping[str, Mapping[str, object]],
) -> None:
    for logical_id, graph in active_graphs.items():
        _validate_active_graph_source(graph)
        recommendation_id = str(graph.get("RecommendationID") or "")
        recommendation = recommendations.get(recommendation_id)
        chain = chains.get(logical_id)
        if recommendation is None or chain is None:
            raise DdmrpReplenishmentConflict("Active graph reference is orphaned.")
        if (
            recommendation["LogicalReplenishmentID"] != logical_id
            or graph.get("ItemID") != chain["ItemID"]
            or graph.get("LocationID") != chain["LocationID"]
            or chain_statuses[logical_id] in CHAIN_TERMINAL_STATUSES
        ):
            raise DdmrpReplenishmentConflict("Active graph scope differs from its chain.")


def _validate_active_graph_source(graph: Mapping[str, object]) -> None:
    source_fields = set(graph)
    if source_fields - ACTIVE_GRAPH_SOURCE_FIELDS:
        raise DdmrpReplenishmentConflict("Active graph source fields differ.")
    if _ACTIVE_GRAPH_REQUIRED_SOURCE_FIELDS - source_fields:
        raise DdmrpReplenishmentConflict("Active graph source fields are missing.")
    if any(
        not isinstance(graph[field], str) or not graph[field]
        for field in _ACTIVE_GRAPH_REQUIRED_SOURCE_FIELDS
    ):
        raise DdmrpReplenishmentConflict("Active graph identity fields must be text.")
    for field in _ACTIVE_GRAPH_TEXT_SOURCE_FIELDS & source_fields:
        value = graph[field]
        if value is not None and not isinstance(value, str):
            raise DdmrpReplenishmentConflict("Active graph display fields must be text.")
    if "PlannedSupplyQty" in graph and (
        isinstance(graph["PlannedSupplyQty"], bool)
        or not isinstance(graph["PlannedSupplyQty"], (int, float))
    ):
        raise DdmrpReplenishmentConflict("Active graph planned supply must be numeric.")
    if "RecordVersion" in graph and (
        isinstance(graph["RecordVersion"], bool)
        or not isinstance(graph["RecordVersion"], int)
        or graph["RecordVersion"] <= 0
    ):
        raise DdmrpReplenishmentConflict("Active graph record version must be positive.")


def _validate_provenance_links(
    runs: Mapping[str, Mapping[str, object]],
    rows: Mapping[str, Mapping[str, object]],
    chains: Mapping[str, Mapping[str, object]],
    recommendations: Mapping[str, Mapping[str, object]],
    events: Iterable[Mapping[str, object]],
) -> None:
    for chain in chains.values():
        opening_run = runs.get(str(chain["OpenedByEvaluationID"]))
        chain_recommendations = sorted(
            (
                recommendation for recommendation in recommendations.values()
                if recommendation["LogicalReplenishmentID"]
                == chain["LogicalReplenishmentID"]
            ),
            key=lambda recommendation: int(recommendation["RecommendationVersion"]),
        )
        if opening_run is None:
            raise DdmrpReplenishmentConflict("DDMRP chain opening evaluation is missing.")
        if (
            not chain_recommendations
            or chain_recommendations[0]["RecommendationVersion"] != 1
            or chain_recommendations[0]["EvaluationID"]
            != chain["OpenedByEvaluationID"]
            or chain["OpenedAt"] != opening_run["EvaluationAt"]
        ):
            raise DdmrpReplenishmentConflict(
                "DDMRP created chain membership differs from its evaluation."
            )
    for recommendation in recommendations.values():
        evaluation_id = str(recommendation["EvaluationID"])
        row_id = str(recommendation["EvaluationRowID"])
        run = runs.get(evaluation_id)
        row = rows.get(row_id)
        if run is None or row is None:
            raise DdmrpReplenishmentConflict("DDMRP recommendation evaluation is orphaned.")
        if (
            row["RecommendationID"] != recommendation["RecommendationID"]
            or row["EvaluationID"] != evaluation_id
            or any(
                row[field] != recommendation[field]
                for field in (
                    "ItemID", "LocationID", "Uom", "PlanningStatus",
                    "ExecutionStatus", "SuggestedReplenishmentQty",
                    "StandardTargetReceiptAt", "GateCodes",
                )
            )
            or recommendation["AuthoritySignatureFingerprint"]
            != run["AuthoritySignatureFingerprint"]
            or recommendation["RelevantPlanningLedgerIdentity"]
            != run["RelevantPlanningLedgerIdentity"]
            or recommendation["RelevantPlanningLedgerFingerprint"]
            != run["RelevantPlanningLedgerFingerprint"]
        ):
            raise DdmrpReplenishmentConflict("DDMRP recommendation provenance differs.")
    rows_by_run: dict[str, list[Mapping[str, object]]] = {
        evaluation_id: [] for evaluation_id in runs
    }
    for row in rows.values():
        evaluation_id = str(row["EvaluationID"])
        run = runs[evaluation_id]
        expected_gates = sorted(
            (
                {
                    "Code": issue["Code"],
                    "Message": issue["Message"],
                    "BlocksOperationalAction": issue["BlocksOperationalAction"],
                }
                for issue in run["Issues"]
            ),
            key=lambda gate: str(gate["Code"]),
        )
        if (
            row["AuthoritySignatureFingerprint"]
            != run["AuthoritySignatureFingerprint"]
            or row["OperationalActionAllowed"] != run["OperationalActionAllowed"]
            or row["GateCodes"] != expected_gates
        ):
            raise DdmrpReplenishmentConflict("DDMRP evaluation row provenance differs.")
        rows_by_run[evaluation_id].append(row)
    for evaluation_id, run in runs.items():
        run_rows = rows_by_run[evaluation_id]
        run_recommendations = [
            recommendation for recommendation in recommendations.values()
            if recommendation["EvaluationID"] == evaluation_id
        ]
        expected_summary = {
            "RedCount": sum(row["PlanningStatus"] == "Red" for row in run_rows),
            "YellowCount": sum(row["PlanningStatus"] == "Yellow" for row in run_rows),
            "GreenCount": sum(row["PlanningStatus"] == "Green" for row in run_rows),
            "AboveGreenCount": sum(
                row["PlanningStatus"] == "AboveGreen" for row in run_rows
            ),
            "BlockedRecommendationCount": sum(
                recommendation["InitialStatus"] == "Blocked"
                for recommendation in run_recommendations
            ),
            "AdjustmentRequiredCount": sum(
                recommendation["InitialStatus"] == "AdjustmentRequired"
                for recommendation in run_recommendations
            ),
            "IssueCount": len(run["Issues"]),
        }
        if dict(run["Summary"]) != expected_summary:
            raise DdmrpReplenishmentConflict("DDMRP evaluation summary differs.")
    for event in events:
        evaluation_id = str(event["EvaluationID"])
        logical_id = str(event["LogicalReplenishmentID"])
        run = runs.get(evaluation_id)
        if run is None:
            raise DdmrpReplenishmentConflict("DDMRP event evaluation is orphaned.")
        if any((
            event["CausationID"] != run["EvaluationRequestID"],
            event["CorrelationID"] != evaluation_id,
            event["IdempotencyKey"] != event["EventID"],
            event["TraceID"] != logical_id,
            event["OccurredAt"] != run["RecordedAt"],
            event["ActorID"] != run["RecordedBy"],
        )):
            raise DdmrpReplenishmentConflict(
                "DDMRP event back-reference or provenance differs."
            )
        if event["EventType"] == "ReplenishmentChainOpened":
            chain = chains[logical_id]
            if any((
                chain["OpenedByEvaluationID"] != evaluation_id,
                chain["OpenedAt"] != run["EvaluationAt"],
            )):
                raise DdmrpReplenishmentConflict(
                    "DDMRP chain creation event provenance differs."
                )
        if event["EventType"] == "RecommendationVersionCreated":
            recommendation = recommendations[str(event["RecommendationID"])]
            if any((
                recommendation["EvaluationID"] != evaluation_id,
                recommendation["CreatedAt"] != run["RecordedAt"],
                recommendation["CreatedBy"] != run["RecordedBy"],
            )):
                raise DdmrpReplenishmentConflict(
                    "DDMRP recommendation creation event provenance differs."
                )
        if event["EventType"] == "RecommendationSuperseded":
            successor = recommendations[str(event["RelatedRecommendationID"])]
            if successor["EvaluationID"] != evaluation_id:
                raise DdmrpReplenishmentConflict(
                    "DDMRP recommendation supersession event provenance differs."
                )


def _validate_single_current_version(
    recommendations: Mapping[str, Mapping[str, object]],
    statuses: Mapping[str, str],
) -> None:
    by_chain: dict[str, list[str]] = {}
    for recommendation_id, recommendation in recommendations.items():
        if statuses[recommendation_id] != "Superseded":
            by_chain.setdefault(str(recommendation["LogicalReplenishmentID"]), []).append(
                recommendation_id
            )
    if any(len(current_ids) > 1 for current_ids in by_chain.values()):
        raise DdmrpReplenishmentConflict(
            "Multiple current DDMRP recommendation versions exist."
        )


def _validate_latest_gates(
    evaluation: Mapping[str, object],
    rows: Iterable[Mapping[str, object]],
) -> None:
    issues = evaluation["Issues"]
    for issue in issues:
        if set(issue) != set(ISSUE_RECORD_FIELDS):
            raise DdmrpReplenishmentConflict("DDMRP issue fields differ.")
    for row in rows:
        for gate in row["GateCodes"]:
            applicable = [
                issue for issue in issues
                if issue["Code"] == gate["Code"]
                and (
                    (issue["ItemID"] is None and issue["LocationID"] is None)
                    or (
                        issue["ItemID"] == row["ItemID"]
                        and issue["LocationID"] == row["LocationID"]
                    )
                )
            ]
            if len(applicable) != 1 or any((
                applicable[0]["Message"] != gate["Message"],
                applicable[0]["BlocksOperationalAction"]
                != gate["BlocksOperationalAction"],
            )):
                raise DdmrpReplenishmentConflict(
                    "DDMRP row gate does not resolve to one immutable issue."
                )


def _project_row(
    row: Mapping[str, object],
    recommendations: Mapping[str, Mapping[str, object]],
    recommendation_statuses: Mapping[str, str],
) -> dict[str, object]:
    recommendation_id = row["RecommendationID"]
    recommendation = (
        recommendations[str(recommendation_id)] if recommendation_id is not None else None
    )
    top_of_green = row["TopOfGreen"]
    buffer_percent = (
        (row["NetFlowPosition"] / top_of_green) * 100
        if isinstance(top_of_green, (int, float)) and top_of_green > 0
        else None
    )
    values = {
        **row,
        "BufferPercent": buffer_percent,
        "RecommendationVersion": (
            recommendation["RecommendationVersion"] if recommendation else None
        ),
        "RecommendationStatus": (
            recommendation_statuses[str(recommendation_id)] if recommendation else None
        ),
        "PendingReviewCount": int(
            recommendation is not None
            and recommendation_statuses[str(recommendation_id)] == "PendingReview"
        ),
        "DemandComponents": [
            _project(component, DEMAND_COMPONENT_FIELDS)
            for component in row["DemandComponents"]
        ],
        "SupplyComponents": [
            _project(component, SUPPLY_COMPONENT_FIELDS)
            for component in row["SupplyComponents"]
        ],
        "GateCodes": [_project(gate, GATE_FIELDS) for gate in row["GateCodes"]],
    }
    return _project(values, ROW_VIEW_FIELDS)


def _project_active_graph(
    graph: Mapping[str, object],
    *,
    chain_statuses: Mapping[str, str],
    recommendations: Mapping[str, Mapping[str, object]],
    recommendation_statuses: Mapping[str, str],
    events: Iterable[Mapping[str, object]],
) -> dict[str, object]:
    logical_id = str(graph["LogicalReplenishmentID"])
    recommendation = recommendations[str(graph["RecommendationID"])]
    current_statuses = [
        recommendation_statuses[recommendation_id]
        for recommendation_id, source in recommendations.items()
        if source["LogicalReplenishmentID"] == logical_id
        and recommendation_statuses[recommendation_id] != "Superseded"
    ]
    values = {
        "LogicalReplenishmentID": logical_id,
        "RecommendationID": graph["RecommendationID"],
        "RecommendationVersion": recommendation["RecommendationVersion"],
        "ItemID": graph["ItemID"],
        "LocationID": graph["LocationID"],
        "Uom": graph.get("Uom", recommendation["Uom"]),
        "GraphStatus": graph.get("GraphStatus"),
        "CandidateStatus": graph.get("CandidateStatus"),
        "PlannedSupplyQty": graph.get(
            "PlannedSupplyQty", recommendation["SuggestedReplenishmentQty"]
        ),
        "PlanningRunID": graph.get("PlanningRunID"),
        "FormalOrderRef": graph.get("FormalOrderRef", graph.get("FormalSupplyID")),
        "AdjustmentRequired": (
            chain_statuses[logical_id] == "AdjustmentRequired"
            or "AdjustmentRequired" in current_statuses
        ),
        "LastEventAt": _last_event_at(events, logical_id=logical_id),
    }
    return _project(values, ACTIVE_GRAPH_VIEW_FIELDS)


def _project_history(
    recommendation: Mapping[str, object],
    *,
    recommendation_statuses: Mapping[str, str],
    evaluation_runs: Mapping[str, Mapping[str, object]],
    events: Iterable[Mapping[str, object]],
) -> dict[str, object]:
    recommendation_id = str(recommendation["RecommendationID"])
    selected_events = sorted(
        (
            event for event in events
            if event["AggregateType"] == "Recommendation"
            and event["AggregateID"] == recommendation_id
        ),
        key=lambda event: (int(event["AggregateVersion"]), str(event["EventID"])),
    )
    superseded_by = next((
        event["RelatedRecommendationID"] for event in selected_events
        if event["EventType"] == "RecommendationSuperseded"
    ), None)
    evaluation = evaluation_runs[str(recommendation["EvaluationID"])]
    values = {
        "LogicalReplenishmentID": recommendation["LogicalReplenishmentID"],
        "RecommendationID": recommendation_id,
        "RecommendationVersion": recommendation["RecommendationVersion"],
        "PredecessorRecommendationID": recommendation["PredecessorRecommendationID"],
        "SupersededByRecommendationID": superseded_by,
        "AdjustmentOfRecommendationID": recommendation["AdjustmentOfRecommendationID"],
        "InitialStatus": recommendation["InitialStatus"],
        "CurrentStatus": recommendation_statuses[recommendation_id],
        "SuggestedReplenishmentQty": recommendation["SuggestedReplenishmentQty"],
        "StandardTargetReceiptAt": recommendation["StandardTargetReceiptAt"],
        "EvaluationID": recommendation["EvaluationID"],
        "EvaluationAt": evaluation["EvaluationAt"],
        "LastEventAt": _last_event_at(selected_events),
        "Events": [_project(event, HISTORY_EVENT_FIELDS) for event in selected_events],
    }
    return _project(values, HISTORY_VIEW_FIELDS)


def _summary(
    rows: Iterable[Mapping[str, object]],
    active_graphs: Iterable[Mapping[str, object]],
    history: Iterable[Mapping[str, object]],
) -> dict[str, int]:
    row_list = list(rows)
    graph_list = list(active_graphs)
    statuses = [row["CurrentStatus"] for row in history]
    return {
        "RedCount": sum(row["PlanningStatus"] == "Red" for row in row_list),
        "YellowCount": sum(row["PlanningStatus"] == "Yellow" for row in row_list),
        "GreenCount": sum(row["PlanningStatus"] == "Green" for row in row_list),
        "AboveGreenCount": sum(
            row["PlanningStatus"] == "AboveGreen" for row in row_list
        ),
        "BlockedRecommendationCount": statuses.count("Blocked"),
        "PendingReviewCount": statuses.count("PendingReview"),
        "AdjustmentRequiredCount": statuses.count("AdjustmentRequired"),
        "ActiveGraphCount": len(graph_list),
    }


def _empty_workbench() -> dict[str, object]:
    return {
        "Evaluation": None,
        "Summary": {field: 0 for field in SUMMARY_VIEW_FIELDS},
        "Rows": [],
        "ActiveGraphs": [],
        "History": [],
        "Issues": [],
        "Boundary": BOUNDARY,
        "TechnicalDetails": {
            field: [] if field == "RecommendationFingerprints" else None
            for field in TECHNICAL_DETAILS_FIELDS
        },
    }


def _project(value: Mapping[str, object], fields: tuple[str, ...]) -> dict[str, object]:
    return {field: deepcopy(value[field]) for field in fields}


def _last_event_at(
    events: Iterable[Mapping[str, object]], *, logical_id: str | None = None
) -> object:
    selected = [
        event["OccurredAt"] for event in events
        if logical_id is None or event["LogicalReplenishmentID"] == logical_id
    ]
    return max(selected, default=None)


def _nullable_number_sort(value: object) -> tuple[bool, float]:
    if isinstance(value, (int, float)):
        return (False, float(value))
    return (True, 0.0)
