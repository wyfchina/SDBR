from __future__ import annotations

from copy import deepcopy

from sdbr.order_commitment_view import (
    AUDIT_FIELDS,
    CAPACITY_WINDOW_FIELDS,
    DETAIL_FIELDS,
    MATERIAL_LINE_FIELDS,
    ORDER_COMMITMENT_ROW_FIELDS,
    SAFE_AUDIT_DETAIL_FIELDS,
    build_order_commitment_detail,
    build_order_commitment_workbench,
)


class TestOrderCommitmentViewContract:
    """BE-SDBR-010, UI-COMMIT-001: exact, safe MTO read projections."""

    def _evaluation(
        self,
        *,
        evaluation_id: str = "OCE-1",
        order_id: str = "SO-100",
        evaluated_at: str = "2026-07-12T08:00:00+00:00",
        status: str = "AwaitingPlannerDecision",
    ) -> dict[str, object]:
        window = {
            "ResourceID": "CCR-1",
            "OperationID": "OP-10",
            "WindowStartAt": "2026-07-12T08:00:00+00:00",
            "WindowEndAt": "2026-07-12T10:00:00+00:00",
            "UsableWindowEndAt": "2026-07-12T09:00:00+00:00",
            "LatestAllowedCompletionAt": "2026-07-12T09:00:00+00:00",
            "CapacityMinutes": 120.0,
            "UsableTemporalCapacityMinutes": 60.0,
            "ScheduledLoadMinutes": 15.0,
            "ScheduledLoadBeforeDeadlineMinutes": 15.0,
            "ExistingReservationMinutes": 5.0,
            "CandidateLoadMinutes": 10.0,
            "LoadBeforeMinutes": 20.0,
            "LoadAfterMinutes": 30.0,
            "LoadAfterPercent": 25.0,
            "LoadStatus": "WithinCapacity",
            "ThresholdExceeded": False,
            "PhysicalCapacityExceeded": False,
            "AlternateResourceIDs": ["CCR-2", {"must": "not leak"}],
            "AuthorityCapacityPayload": {"must": "not leak"},
        }
        assessment = {
            "PromiseAt": "2026-07-12T09:00:00+00:00",
            "WindowAssessments": [window],
            "ReservationRequests": [{"Raw": "request"}],
            "RawCandidatePayload": {"must": "not leak"},
        }
        return {
            "EvaluationID": evaluation_id,
            "Status": status,
            "EvaluatedAt": evaluated_at,
            "RecordVersion": 1,
            "EvaluationFingerprint": "sha256:evaluation",
            "OrderContentFingerprint": "sha256:order",
            "AuditBasisFingerprint": "sha256:basis",
            "DecisionFactsFingerprint": "sha256:decision-facts",
            "Order": {
                "OrderID": order_id,
                "DemandLineID": "10",
                "ProductID": "FG-1",
                "LocationID": "MAIN",
                "Quantity": 5.0,
                "Uom": "EA",
                "RequestedDueAt": "2026-07-12T09:00:00+00:00",
                "BusinessPriority": 100,
                "RoutingID": "R-1",
                "RawOrderPayload": {"authority": "hidden"},
            },
            "ShadowSchedule": {
                "Status": "OnTime",
                "RequestedDateAssessment": assessment,
                "EarliestSafeAssessment": {
                    **deepcopy(assessment),
                    "PromiseAt": "2026-07-12T10:00:00+00:00",
                },
                "SelectedAssessment": assessment,
                "Issues": [],
                "RawShadowPayload": {"authority": "hidden"},
            },
            "MaterialAssessment": {
                "Status": "Feasible",
                "CheckEnabled": True,
                "SkipReason": None,
                "MaterialCheckWindowMinutes": 60,
                "MaterialEligibilityCutoffAt": "2026-07-12T09:00:00+00:00",
                "OperationalStateSnapshotID": "OPS-1",
                "OperationalStateCapturedAt": "2026-07-12T07:55:00+00:00",
                "OperationalStateFreshnessStatus": "Fresh",
                "OperationalStateAgeMinutes": 5,
                "OperationalStateMaxAgeMinutes": 60,
                "Lines": [{
                    "RequirementLineID": "20",
                    "ItemID": "RM-1",
                    "LocationID": "MAIN",
                    "Uom": "EA",
                    "RequiredQty": 5.0,
                    "OnHandQty": 8.0,
                    "EligibleInboundQty": 2.0,
                    "AuthorityAllocatedQty": 1.0,
                    "OtherPlanningAllocatedQty": 1.0,
                    "QualifiedSupplyQty": 9.0,
                    "UncommittedAvailabilityQty": 8.0,
                    "CoverageStatus": "Covered",
                    "RawInventoryAuthorityPayload": {"must": "not leak"},
                }],
                "PendingRequirements": [{"Raw": "requirement"}],
                "Issues": [{"Raw": "issue"}],
                "RawSnapshotPayload": {"must": "not leak"},
            },
            "ProtectionPolicy": {
                "ThresholdPercent": 75.0,
                "Source": "ApprovedOperatingModel",
                "Approved": True,
                "RawPolicyPayload": {"must": "not leak"},
            },
            "Recommendation": {
                "Decision": "AcceptRequestedDate",
                "AllowedActions": ["AcceptRequestedDate", "Reject"],
                "ThresholdState": "ApprovedWithin",
                "RequiresPlannerDecision": True,
                "RequiresCcrAcknowledgement": False,
                "RequiresMaterialAcknowledgement": False,
                "ActionAcknowledgementRequirements": {
                    "AcceptRequestedDate": {
                        "RequiresCcrAcknowledgement": False,
                        "RequiresMaterialAcknowledgement": False,
                        "Raw": "hidden",
                    },
                    "Reject": {
                        "RequiresCcrAcknowledgement": False,
                        "RequiresMaterialAcknowledgement": False,
                    },
                    "UnknownAction": {"Raw": "hidden"},
                },
                "RawRecommendationPayload": {"must": "not leak"},
            },
            "Basis": {
                "BaselinePlanningRunID": "RUN-1",
                "MasterDataVersionID": "MDV-1",
                "OperatingModelConfigurationID": "OMC-1",
                "SchedulingConfigurationID": "SC-1",
                "DDMRPConfigurationID": "DDMRP-1",
                "ReleasePolicyVersionID": "RP-1",
                "SelectedOperationalStateSnapshotID": "OPS-1",
                "SelectedOperationalStateCapturedAt": "2026-07-12T07:55:00+00:00",
                "OperationalStateFreshnessStatus": "Fresh",
                "OperationalStateAgeMinutes": 5,
                "OperationalStateMaxAgeMinutes": 60,
                "RawMasterData": {"must": "not leak"},
                "RelevantMaterialAvailability": [{"Raw": "authority"}],
            },
            "TraceID": "TRACE-1",
            "CorrelationID": "CORR-1",
            "RawEvaluationPayload": {"must": "not leak"},
        }

    def _accepted_evaluation(self) -> dict[str, object]:
        evaluation = self._evaluation(status="AcceptedPendingFormalSchedule")
        evaluation["Decision"] = {
            "DecisionID": "DEC-1",
            "DecisionFingerprint": "sha256:decision",
            "Decision": "AcceptRequestedDate",
            "DecidedBy": "planner-1",
            "DecidedAt": "2026-07-12T08:05:00+00:00",
            "Reason": "Confirmed against frozen evidence.",
            "CcrRiskAcknowledged": False,
            "MaterialRiskAcknowledged": False,
            "AcceptedPromiseAt": "2026-07-12T09:00:00+00:00",
            "DemandCommitmentID": "DC-1",
            "ReservationBatchID": "RB-1",
            "ExternalOrderAcceptance": "NotPerformed",
            "PlanningRunCreation": "NotPerformed",
            "ProductionMutation": "NotPerformed",
            "RawDecisionPayload": {"must": "not leak"},
        }
        return evaluation

    def _batch(self, *, status: str = "ActivePlanReservation") -> dict[str, object]:
        return {
            "ReservationBatchID": "RB-1",
            "DemandCommitmentID": "DC-1",
            "OrderCommitmentEvaluationID": "OCE-1",
            "Status": status,
            "ConfirmationID": "DEC-1",
            "RawReservationPayload": {"must": "not leak"},
        }

    def test_workbench_row_has_exact_field_set_and_exception_reservation_status(self):
        result = build_order_commitment_workbench(
            evaluations=[self._evaluation()],
            demand_commitments={},
            reservation_batches={},
        )

        row = result["Rows"][0]
        assert set(row) == set(ORDER_COMMITMENT_ROW_FIELDS)
        assert row["ReservationStatus"] == "NotReserved"
        assert row["ExceptionStatus"] == "None"

    def test_terminal_rows_have_empty_allowed_actions(self):
        result = build_order_commitment_workbench(
            evaluations=[self._accepted_evaluation()],
            demand_commitments={},
            reservation_batches={"RB-1": self._batch()},
        )

        assert result["Rows"][0]["AllowedActions"] == []

    def test_held_batch_maps_to_planning_error_pending(self):
        result = build_order_commitment_workbench(
            evaluations=[self._accepted_evaluation()],
            demand_commitments={},
            reservation_batches={"RB-1": self._batch(status="HeldForPlanningError")},
        )

        row = result["Rows"][0]
        assert row["ReservationStatus"] == "HeldForPlanningError"
        assert row["ExceptionStatus"] == "PlanningErrorPending"

    def test_missing_accepted_batch_maps_to_reservation_evidence_missing(self):
        result = build_order_commitment_workbench(
            evaluations=[self._accepted_evaluation()],
            demand_commitments={},
            reservation_batches={},
        )

        row = result["Rows"][0]
        assert row["ReservationStatus"] == "ReservationEvidenceMissing"
        assert row["ExceptionStatus"] == "ReservationEvidenceMissing"

    def test_detail_has_exact_top_level_and_whitelisted_capacity_material_fields(self):
        detail = build_order_commitment_detail(
            evaluation=self._evaluation(),
            events=[],
            demand_commitment=None,
            reservation_batch=None,
        )

        assert set(detail) == set(DETAIL_FIELDS)
        window = detail["CapacityEvidence"]["SelectedAssessment"]["WindowAssessments"][0]
        assert set(window) == set(CAPACITY_WINDOW_FIELDS)
        material = detail["MaterialEvidence"]["Lines"][0]
        assert set(material) == set(MATERIAL_LINE_FIELDS)
        assert window["AlternateResourceIDs"] == ["CCR-2"]

    def test_audit_history_drops_unknown_details_trace_and_raw_payloads(self):
        event = {
            "EventID": "OCEVT-1",
            "EventType": "DecisionRecorded",
            "OccurredAt": "2026-07-12T08:05:00+00:00",
            "ActorID": "planner-1",
            "DecisionID": "DEC-1",
            "ReservationBatchID": "RB-1",
            "TraceID": "TRACE-EVENT",
            "CausationID": "CAUSE-1",
            "RawSourcePayload": {"must": "not leak"},
            "Details": {
                "DecisionCode": "AcceptRequestedDate",
                "Unknown": "hidden",
                "RawPayload": {"must": "not leak"},
            },
        }
        detail = build_order_commitment_detail(
            evaluation=self._accepted_evaluation(),
            events=[event],
            demand_commitment=None,
            reservation_batch=self._batch(),
        )

        audit = detail["AuditHistory"][0]
        assert set(audit) == set(AUDIT_FIELDS)
        assert set(audit["Details"]) <= SAFE_AUDIT_DETAIL_FIELDS
        assert audit["Details"] == {"DecisionCode": "AcceptRequestedDate"}
        assert "TRACE-EVENT" not in repr(detail["AuditHistory"])
        assert "must" not in repr(detail["AuditHistory"])

    def test_fingerprints_exist_only_in_collapsed_technical_details(self):
        detail = build_order_commitment_detail(
            evaluation=self._accepted_evaluation(),
            events=[],
            demand_commitment=None,
            reservation_batch=self._batch(),
        )

        rendered = repr({key: value for key, value in detail.items() if key != "TechnicalDetails"})
        assert "sha256:" not in rendered
        assert detail["TechnicalDetails"]["EvaluationFingerprint"] == "sha256:evaluation"
        assert detail["TechnicalDetails"]["DecisionFingerprint"] == "sha256:decision"

    def test_raw_basis_order_master_and_snapshot_payloads_never_appear(self):
        detail = build_order_commitment_detail(
            evaluation=self._evaluation(),
            events=[],
            demand_commitment=None,
            reservation_batch=None,
        )

        assert "must" not in repr(detail)
        assert "RawMasterData" not in repr(detail)
        assert "RawOrderPayload" not in repr(detail)
        assert "RawSnapshotPayload" not in repr(detail)

    def test_workbench_sort_and_summary_are_deterministic(self):
        first = self._evaluation(evaluation_id="OCE-B", order_id="SO-200")
        second = self._evaluation(evaluation_id="OCE-A", order_id="SO-100")
        second["Recommendation"] = {
            **second["Recommendation"],
            "Decision": "PlannerConfirmationRequired",
        }
        third = self._evaluation(
            evaluation_id="OCE-C",
            order_id="SO-300",
            evaluated_at="2026-07-12T09:00:00+00:00",
            status="Rejected",
        )
        third["MaterialAssessment"] = {
            **third["MaterialAssessment"],
            "Status": "Shortage",
        }
        original_evaluations = deepcopy([first, third, second])

        result = build_order_commitment_workbench(
            evaluations=[first, third, second],
            demand_commitments={},
            reservation_batches={},
        )

        assert [row["EvaluationID"] for row in result["Rows"]] == [
            "OCE-C", "OCE-A", "OCE-B",
        ]
        assert result["Summary"] == {
            "EvaluationCount": 3,
            "AwaitingDecisionCount": 2,
            "ConfirmationRequiredCount": 1,
            "MaterialPendingCount": 1,
            "AcceptedPendingScheduleCount": 0,
            "RejectedCount": 1,
            "ExceptionCount": 0,
        }
        assert [first, third, second] == original_evaluations
