"""Exact, sanitized read projections for MTO order commitment evidence."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from typing import Mapping


ORDER_COMMITMENT_ROW_FIELDS = (
    "EvaluationID", "OrderID", "DemandLineID", "ProductID", "Quantity", "Uom",
    "BusinessPriority", "RequestedDueAt", "EarliestSafePromiseAt",
    "SelectedPromiseAt", "CcrResourceIDs", "CcrWindowCount",
    "LoadBeforeMinutes", "LoadAfterMinutes", "LoadAfterPercent",
    "ProtectionThresholdPercent", "ProtectionThresholdSource",
    "ProtectionThresholdApproved", "MaterialStatus",
    "MaterialEvidenceFreshnessStatus", "Recommendation", "AllowedActions",
    "RequiresCcrAcknowledgement", "RequiresMaterialAcknowledgement", "Status",
    "ReservationBatchID", "ReservationStatus", "ExceptionStatus", "EvaluatedAt",
    "ExternalOrderAcceptance", "PlanningRunCreation", "ProductionMutation",
)

DETAIL_FIELDS = (
    "EvaluationID", "Status", "EvaluatedAt", "RecordVersion", "Order",
    "CapacityEvidence", "MaterialEvidence", "Recommendation",
    "EvidenceReferences", "Decision", "Reservation", "AuditHistory",
    "TechnicalDetails", "Boundary",
)

ORDER_FIELDS = (
    "OrderID", "DemandLineID", "ProductID", "LocationID", "Quantity",
    "Uom", "RequestedDueAt", "BusinessPriority", "RoutingID",
)

CAPACITY_WINDOW_FIELDS = (
    "ResourceID", "OperationID", "WindowStartAt", "WindowEndAt",
    "UsableWindowEndAt", "LatestAllowedCompletionAt", "CapacityMinutes",
    "UsableTemporalCapacityMinutes", "ScheduledLoadMinutes",
    "ScheduledLoadBeforeDeadlineMinutes", "ExistingReservationMinutes",
    "CandidateLoadMinutes", "LoadBeforeMinutes", "LoadAfterMinutes",
    "LoadAfterPercent", "LoadStatus", "ThresholdExceeded",
    "PhysicalCapacityExceeded", "AlternateResourceIDs",
)

MATERIAL_LINE_FIELDS = (
    "RequirementLineID", "ItemID", "LocationID", "Uom", "RequiredQty",
    "OnHandQty", "EligibleInboundQty", "AuthorityAllocatedQty",
    "OtherPlanningAllocatedQty", "QualifiedSupplyQty",
    "UncommittedAvailabilityQty", "CoverageStatus",
)

RECOMMENDATION_VIEW_FIELDS = (
    "Decision",
    "AllowedActions",
    "ThresholdState",
    "RequiresPlannerDecision",
    "RequiresCcrAcknowledgement",
    "RequiresMaterialAcknowledgement",
    "ActionAcknowledgementRequirements",
)

ORDER_COMMITMENT_ACTIONS = frozenset({
    "AcceptRequestedDate",
    "ConditionallyAcceptRequestedDate",
    "AcceptRecommendedDate",
    "ConditionallyAcceptRecommendedDate",
    "Reevaluate",
    "Reject",
})

ACTION_ACKNOWLEDGEMENT_REQUIREMENT_FIELDS = (
    "RequiresCcrAcknowledgement",
    "RequiresMaterialAcknowledgement",
)

AUDIT_FIELDS = (
    "EventID", "EventType", "OccurredAt", "ActorID",
    "DecisionID", "ReservationBatchID", "Details",
)

SAFE_AUDIT_DETAIL_FIELDS = frozenset({
    "FromStatus", "ToStatus", "Recommendation", "DecisionCode",
    "SupersededByEvaluationID", "AcceptedPromiseAt",
    "CcrRiskAcknowledged", "MaterialRiskAcknowledged",
    "MaterialCheckEnabled", "MaterialEvidenceFreshnessStatus",
})

_CANDIDATE_FIELDS = ("PromiseAt", "WindowAssessments")
_CAPACITY_EVIDENCE_FIELDS = (
    "Status", "RequestedDateAssessment", "EarliestSafeAssessment",
    "SelectedAssessment",
)
_MATERIAL_EVIDENCE_FIELDS = (
    "Status", "CheckEnabled", "SkipReason", "MaterialCheckWindowMinutes",
    "MaterialEligibilityCutoffAt", "OperationalStateSnapshotID",
    "OperationalStateCapturedAt", "OperationalStateFreshnessStatus",
    "OperationalStateAgeMinutes", "OperationalStateMaxAgeMinutes", "Lines",
)
_EVIDENCE_REFERENCE_FIELDS = (
    "BaselinePlanningRunID", "BaselineOperationalStateSnapshotID",
    "MasterDataVersionID", "OperatingModelConfigurationID",
    "SchedulingConfigurationID", "DDMRPConfigurationID",
    "ReleasePolicyVersionID", "SelectedOperationalStateSnapshotID",
    "SelectedOperationalStateCapturedAt", "OperationalStateFreshnessStatus",
    "OperationalStateAgeMinutes", "OperationalStateMaxAgeMinutes",
)
_DECISION_FIELDS = (
    "DecisionID", "Decision", "DecidedBy", "DecidedAt", "Reason",
    "CcrRiskAcknowledged", "MaterialRiskAcknowledged", "AcceptedPromiseAt",
    "DemandCommitmentID", "ReservationBatchID",
)
_RESERVATION_FIELDS = ("DemandCommitmentID", "ReservationBatchID", "Status")
_TECHNICAL_DETAIL_FIELDS = (
    "EvaluationFingerprint", "OrderContentFingerprint", "AuditBasisFingerprint",
    "DecisionStalenessBasisFingerprint", "DecisionFactsFingerprint", "TraceID",
    "CorrelationID",
)

_BOUNDARY = {
    "RecommendationOnly": True,
    "ExternalOrderAcceptance": "NotPerformed",
    "PlanningRunCreation": "NotPerformed",
    "ProductionMutation": "NotPerformed",
    "ReleaseMaterialGateStillRequired": True,
}


def _mapping(value: object) -> Mapping[str, object]:
    return value if isinstance(value, Mapping) else {}


def _list_of_mappings(value: object) -> list[Mapping[str, object]]:
    return [item for item in value if isinstance(item, Mapping)] if isinstance(value, list) else []


def _project(record: Mapping[str, object], fields: tuple[str, ...]) -> dict[str, object]:
    return {field: deepcopy(record.get(field)) for field in fields}


def _project_candidate(value: object) -> dict[str, object] | None:
    candidate = _mapping(value)
    if not candidate:
        return None
    return {
        "PromiseAt": deepcopy(candidate.get("PromiseAt")),
        "WindowAssessments": [
            _project_capacity_window(window)
            for window in _list_of_mappings(candidate.get("WindowAssessments"))
        ],
    }


def _project_capacity_window(window: Mapping[str, object]) -> dict[str, object]:
    projected = _project(window, CAPACITY_WINDOW_FIELDS)
    alternate_resource_ids = window.get("AlternateResourceIDs")
    projected["AlternateResourceIDs"] = [
        deepcopy(resource_id)
        for resource_id in alternate_resource_ids
        if isinstance(resource_id, str)
    ] if isinstance(alternate_resource_ids, list) else []
    return projected


def _project_capacity_evidence(shadow: Mapping[str, object]) -> dict[str, object]:
    return {
        "Status": deepcopy(shadow.get("Status")),
        "RequestedDateAssessment": _project_candidate(
            shadow.get("RequestedDateAssessment")
        ),
        "EarliestSafeAssessment": _project_candidate(
            shadow.get("EarliestSafeAssessment")
        ),
        "SelectedAssessment": _project_candidate(shadow.get("SelectedAssessment")),
    }


def _project_material_evidence(material: Mapping[str, object]) -> dict[str, object]:
    result = _project(material, _MATERIAL_EVIDENCE_FIELDS[:-1])
    result["Lines"] = [
        _project(line, MATERIAL_LINE_FIELDS)
        for line in _list_of_mappings(material.get("Lines"))
    ]
    return result


def _project_recommendation(
    recommendation: Mapping[str, object],
    *,
    terminal: bool,
) -> dict[str, object]:
    source_actions = recommendation.get("AllowedActions")
    if (
        not isinstance(source_actions, list)
        or any(
            not isinstance(action, str) or action not in ORDER_COMMITMENT_ACTIONS
            for action in source_actions
        )
        or len(source_actions) != len(set(source_actions))
    ):
        raise ValueError("AllowedActions must contain only supported action strings.")

    requirements = recommendation.get("ActionAcknowledgementRequirements")
    if not isinstance(requirements, Mapping):
        raise ValueError("ActionAcknowledgementRequirements must be a mapping.")
    if any(
        isinstance(action, str)
        and action in ORDER_COMMITMENT_ACTIONS
        and action not in source_actions
        for action in requirements
    ):
        raise ValueError(
            "ActionAcknowledgementRequirements cannot introduce unsupported actions."
        )

    projected_requirements = {}
    for action in source_actions:
        requirement = requirements.get(action)
        if (
            not isinstance(requirement, Mapping)
            or any(
                not isinstance(requirement.get(field), bool)
                for field in ACTION_ACKNOWLEDGEMENT_REQUIREMENT_FIELDS
            )
        ):
            raise ValueError(
                "Action acknowledgement requirements must contain exactly two boolean flags."
            )
        projected_requirements[action] = {
            field: requirement[field]
            for field in ACTION_ACKNOWLEDGEMENT_REQUIREMENT_FIELDS
        }

    allowed_actions = [] if terminal else deepcopy(source_actions)
    return {
        "Decision": deepcopy(recommendation.get("Decision")),
        "AllowedActions": allowed_actions,
        "ThresholdState": deepcopy(recommendation.get("ThresholdState")),
        "RequiresPlannerDecision": deepcopy(
            recommendation.get("RequiresPlannerDecision")
        ),
        "RequiresCcrAcknowledgement": deepcopy(
            recommendation.get("RequiresCcrAcknowledgement")
        ),
        "RequiresMaterialAcknowledgement": deepcopy(
            recommendation.get("RequiresMaterialAcknowledgement")
        ),
        "ActionAcknowledgementRequirements": (
            {} if terminal else projected_requirements
        ),
    }


def _decision(evaluation: Mapping[str, object]) -> Mapping[str, object]:
    return _mapping(evaluation.get("Decision"))


def _matching_record(
    records: Mapping[str, dict[str, object]],
    *,
    evaluation_id: object,
    requested_id: object,
) -> Mapping[str, object] | None:
    if isinstance(requested_id, str) and isinstance(records.get(requested_id), Mapping):
        return records[requested_id]
    for key in sorted(records):
        record = records[key]
        if record.get("OrderCommitmentEvaluationID") == evaluation_id:
            return record
    return None


def _linked_records(
    *,
    evaluation: Mapping[str, object],
    demand_commitments: Mapping[str, dict[str, object]],
    reservation_batches: Mapping[str, dict[str, object]],
) -> tuple[Mapping[str, object] | None, Mapping[str, object] | None]:
    decision = _decision(evaluation)
    demand = _matching_record(
        demand_commitments,
        evaluation_id=evaluation.get("EvaluationID"),
        requested_id=decision.get("DemandCommitmentID"),
    )
    batch = _matching_record(
        reservation_batches,
        evaluation_id=evaluation.get("EvaluationID"),
        requested_id=decision.get("ReservationBatchID"),
    )
    return demand, batch


def _selected_candidate(shadow: Mapping[str, object]) -> Mapping[str, object]:
    selected = _mapping(shadow.get("SelectedAssessment"))
    if selected:
        return selected
    candidate_key = {
        "OnTime": "RequestedDateAssessment",
        "LaterSafeDate": "EarliestSafeAssessment",
    }.get(str(shadow.get("Status")))
    return _mapping(shadow.get(candidate_key)) if candidate_key else {}


def _reservation_status(
    evaluation: Mapping[str, object],
    batch: Mapping[str, object] | None,
) -> str:
    if batch is not None:
        return str(batch.get("Status"))
    if evaluation.get("Status") == "AcceptedPendingFormalSchedule":
        return "ReservationEvidenceMissing"
    return "NotReserved"


def _exception_status(
    *,
    reservation_status: str,
    shadow: Mapping[str, object],
    material: Mapping[str, object],
) -> str:
    if reservation_status == "HeldForPlanningError":
        return "PlanningErrorPending"
    if reservation_status == "ReservationEvidenceMissing":
        return "ReservationEvidenceMissing"
    if shadow.get("Status") == "NotAssessable" or shadow.get("Issues"):
        return "AssessmentBlocked"
    if material.get("Status") == "EvidenceInsufficient":
        return "MaterialEvidenceBlocked"
    return "None"


def _order_commitment_row(
    evaluation: Mapping[str, object],
    *,
    batch: Mapping[str, object] | None,
) -> dict[str, object]:
    order = _mapping(evaluation.get("Order"))
    shadow = _mapping(evaluation.get("ShadowSchedule"))
    material = _mapping(evaluation.get("MaterialAssessment"))
    policy = _mapping(evaluation.get("ProtectionPolicy"))
    recommendation = _mapping(evaluation.get("Recommendation"))
    decision = _decision(evaluation)
    selected = _selected_candidate(shadow)
    windows = _list_of_mappings(selected.get("WindowAssessments"))
    reservation_status = _reservation_status(evaluation, batch)
    terminal = evaluation.get("Status") != "AwaitingPlannerDecision"
    return {
        "EvaluationID": deepcopy(evaluation.get("EvaluationID")),
        "OrderID": deepcopy(order.get("OrderID")),
        "DemandLineID": deepcopy(order.get("DemandLineID")),
        "ProductID": deepcopy(order.get("ProductID")),
        "Quantity": deepcopy(order.get("Quantity")),
        "Uom": deepcopy(order.get("Uom")),
        "BusinessPriority": deepcopy(order.get("BusinessPriority")),
        "RequestedDueAt": deepcopy(order.get("RequestedDueAt")),
        "EarliestSafePromiseAt": deepcopy(
            _mapping(shadow.get("EarliestSafeAssessment")).get("PromiseAt")
        ),
        "SelectedPromiseAt": deepcopy(selected.get("PromiseAt")),
        "CcrResourceIDs": sorted({
            resource_id
            for row in windows
            if isinstance((resource_id := row.get("ResourceID")), str)
        }),
        "CcrWindowCount": len(windows),
        "LoadBeforeMinutes": deepcopy(
            max((row.get("LoadBeforeMinutes") for row in windows), default=None)
        ),
        "LoadAfterMinutes": deepcopy(
            max((row.get("LoadAfterMinutes") for row in windows), default=None)
        ),
        "LoadAfterPercent": deepcopy(
            max((row.get("LoadAfterPercent") for row in windows), default=None)
        ),
        "ProtectionThresholdPercent": deepcopy(policy.get("TargetPercent")),
        "ProtectionThresholdSource": deepcopy(policy.get("Source")),
        "ProtectionThresholdApproved": deepcopy(policy.get("Approved")),
        "MaterialStatus": deepcopy(material.get("Status")),
        "MaterialEvidenceFreshnessStatus": deepcopy(
            material.get("OperationalStateFreshnessStatus")
        ),
        "Recommendation": deepcopy(recommendation.get("Decision")),
        "AllowedActions": _project_recommendation(
            recommendation, terminal=terminal
        )["AllowedActions"],
        "RequiresCcrAcknowledgement": deepcopy(
            recommendation.get("RequiresCcrAcknowledgement")
        ),
        "RequiresMaterialAcknowledgement": deepcopy(
            recommendation.get("RequiresMaterialAcknowledgement")
        ),
        "Status": deepcopy(evaluation.get("Status")),
        "ReservationBatchID": deepcopy(
            decision.get("ReservationBatchID")
            if decision.get("ReservationBatchID") is not None
            else batch.get("ReservationBatchID") if batch is not None else None
        ),
        "ReservationStatus": reservation_status,
        "ExceptionStatus": _exception_status(
            reservation_status=reservation_status, shadow=shadow, material=material
        ),
        "EvaluatedAt": deepcopy(evaluation.get("EvaluatedAt")),
        "ExternalOrderAcceptance": deepcopy(
            decision.get("ExternalOrderAcceptance", "NotPerformed")
        ),
        "PlanningRunCreation": deepcopy(
            decision.get("PlanningRunCreation", "NotPerformed")
        ),
        "ProductionMutation": deepcopy(decision.get("ProductionMutation", "NotPerformed")),
    }


def _aware_timestamp(value: object) -> datetime:
    if not isinstance(value, str):
        raise ValueError("EvaluatedAt must be an ISO-8601 aware timestamp.")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("EvaluatedAt must be an ISO-8601 aware timestamp.")
    return parsed


def build_order_commitment_workbench(
    *,
    evaluations: list[dict[str, object]],
    demand_commitments: Mapping[str, dict[str, object]],
    reservation_batches: Mapping[str, dict[str, object]],
) -> dict[str, object]:
    rows = []
    for evaluation in evaluations:
        _, batch = _linked_records(
            evaluation=evaluation,
            demand_commitments=demand_commitments,
            reservation_batches=reservation_batches,
        )
        rows.append(_order_commitment_row(evaluation, batch=batch))
    rows.sort(key=lambda row: (str(row["OrderID"]), str(row["EvaluationID"])))
    rows.sort(key=lambda row: _aware_timestamp(row["EvaluatedAt"]), reverse=True)
    summary = {
        "EvaluationCount": len(rows),
        "AwaitingDecisionCount": sum(
            row["Status"] == "AwaitingPlannerDecision" for row in rows
        ),
        "ConfirmationRequiredCount": sum(
            row["Recommendation"] == "PlannerConfirmationRequired" for row in rows
        ),
        "MaterialPendingCount": sum(
            row["MaterialStatus"]
            in {"SkippedPendingConfirmation", "EvidenceInsufficient", "Shortage"}
            for row in rows
        ),
        "AcceptedPendingScheduleCount": sum(
            row["Status"] == "AcceptedPendingFormalSchedule" for row in rows
        ),
        "RejectedCount": sum(row["Status"] == "Rejected" for row in rows),
        "ExceptionCount": sum(row["ExceptionStatus"] != "None" for row in rows),
    }
    return {"Summary": summary, "Rows": rows}


def _project_audit_history(events: list[dict[str, object]]) -> list[dict[str, object]]:
    projected = []
    for event in events:
        details = _mapping(event.get("Details"))
        projected.append({
            "EventID": deepcopy(event.get("EventID")),
            "EventType": deepcopy(event.get("EventType")),
            "OccurredAt": deepcopy(event.get("OccurredAt")),
            "ActorID": deepcopy(event.get("ActorID")),
            "DecisionID": deepcopy(event.get("DecisionID")),
            "ReservationBatchID": deepcopy(event.get("ReservationBatchID")),
            "Details": {
                field: deepcopy(details[field])
                for field in sorted(SAFE_AUDIT_DETAIL_FIELDS)
                if field in details
            },
        })
    projected.sort(key=lambda event: (str(event["OccurredAt"]), str(event["EventID"])))
    return projected


def build_order_commitment_detail(
    *,
    evaluation: dict[str, object],
    events: list[dict[str, object]],
    demand_commitment: dict[str, object] | None,
    reservation_batch: dict[str, object] | None,
) -> dict[str, object]:
    shadow = _mapping(evaluation.get("ShadowSchedule"))
    material = _mapping(evaluation.get("MaterialAssessment"))
    basis = _mapping(evaluation.get("Basis"))
    decision = _decision(evaluation)
    batch = _mapping(reservation_batch)
    demand = _mapping(demand_commitment)
    technical = _project(evaluation, _TECHNICAL_DETAIL_FIELDS)
    technical["DecisionFingerprint"] = deepcopy(decision.get("DecisionFingerprint"))
    return {
        "EvaluationID": deepcopy(evaluation.get("EvaluationID")),
        "Status": deepcopy(evaluation.get("Status")),
        "EvaluatedAt": deepcopy(evaluation.get("EvaluatedAt")),
        "RecordVersion": deepcopy(evaluation.get("RecordVersion")),
        "Order": _project(_mapping(evaluation.get("Order")), ORDER_FIELDS),
        "CapacityEvidence": _project_capacity_evidence(shadow),
        "MaterialEvidence": _project_material_evidence(material),
        "Recommendation": _project_recommendation(
            _mapping(evaluation.get("Recommendation")),
            terminal=evaluation.get("Status") != "AwaitingPlannerDecision",
        ),
        "EvidenceReferences": _project(basis, _EVIDENCE_REFERENCE_FIELDS),
        "Decision": _project(decision, _DECISION_FIELDS),
        "Reservation": {
            "DemandCommitmentID": deepcopy(
                decision.get("DemandCommitmentID", demand.get("DemandCommitmentID"))
            ),
            "ReservationBatchID": deepcopy(
                decision.get("ReservationBatchID", batch.get("ReservationBatchID"))
            ),
            "Status": deepcopy(batch.get("Status")),
        },
        "AuditHistory": _project_audit_history(events),
        "TechnicalDetails": technical,
        "Boundary": deepcopy(_BOUNDARY),
    }
