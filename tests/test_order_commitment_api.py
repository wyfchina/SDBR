"""BE-SDBR-010: MTO API payload and authorization contracts."""

from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import json
import sys

import pytest
from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient
from pydantic import ValidationError

from sdbr import api
from sdbr.operational_state import OperationalStateSnapshot
from sdbr.order_commitment_evaluation import (
    OrderCommitmentConflict,
    normalize_mto_order,
    rejected_evaluation_record,
)
from sdbr.order_commitment_view import DETAIL_FIELDS, ORDER_COMMITMENT_ROW_FIELDS
from sdbr.state_store import WorkbenchStateStore
from sdbr.test_data import seed_mto_order_commitment_fixture


MTO_FIXTURE_TIME = datetime(2026, 7, 12, 8, tzinfo=timezone.utc)


def _order_commitment_store(
    now: datetime = MTO_FIXTURE_TIME,
) -> tuple[WorkbenchStateStore, dict[str, object]]:
    store = WorkbenchStateStore()
    fixture = seed_mto_order_commitment_fixture(store, captured_at=now)
    return store, fixture


def _intake_payload() -> dict[str, object]:
    _, fixture = _order_commitment_store()
    return deepcopy(fixture["IntakePayloadTemplate"])


def _order_commitment_client(
    now: datetime = MTO_FIXTURE_TIME,
) -> tuple[TestClient, WorkbenchStateStore, dict[str, object]]:
    store, fixture = _order_commitment_store(now)
    return (
        TestClient(
            api.create_app(
                state_store=store,
                require_auth=True,
                utc_now=lambda: now,
            )
        ),
        store,
        fixture,
    )


def _planner_headers() -> dict[str, str]:
    return {"X-Actor-ID": "planner-task17", "X-Actor-Role": "Planner"}


def _auth_request(method: str, role: str) -> Request:
    return Request({
        "type": "http",
        "method": method,
        "path": "/planner/workbench/order-commitments/workbench",
        "headers": [
            (b"x-actor-id", b"actor-1"),
            (b"x-actor-role", role.encode("ascii")),
        ],
    })


def _order_commitment_resolver(
    store: WorkbenchStateStore,
):
    captured: dict[str, object] = {}
    previous_trace = sys.gettrace()

    def capture_create_app_locals(frame, event, argument):
        if event == "return" and frame.f_code is api.create_app.__code__:
            resolver = frame.f_locals.get(
                "_build_order_commitment_evaluation_from_state"
            )
            if resolver is not None:
                captured["resolver"] = resolver
        return capture_create_app_locals

    sys.settrace(capture_create_app_locals)
    try:
        api.create_app(state_store=store)
    finally:
        sys.settrace(previous_trace)

    resolver = captured.get("resolver")
    assert callable(resolver)
    return resolver


def _orchestration_input() -> tuple[WorkbenchStateStore, dict[str, object], object]:
    store, fixture = _order_commitment_store()
    return store, fixture, _order_commitment_resolver(store)


def _evaluate_order_commitment(
    resolver: object,
    fixture: dict[str, object],
    *,
    store: WorkbenchStateStore,
    requested_snapshot_id: str | None = None,
) -> dict[str, object] | JSONResponse:
    assert callable(resolver)
    return resolver(
        endpoint="/test/order-commitments",
        order=normalize_mto_order(fixture["IntakePayloadTemplate"]),
        evaluated_at=MTO_FIXTURE_TIME,
        check_material_availability=True,
        material_check_skip_reason=None,
        requested_operational_state_snapshot_id=requested_snapshot_id,
    )


def _error_data(result: dict[str, object] | JSONResponse) -> dict[str, object]:
    assert isinstance(result, JSONResponse)
    return json.loads(result.body)


def _evaluation_data(result: dict[str, object] | JSONResponse) -> dict[str, object]:
    assert isinstance(result, dict)
    return result


class TestOrderCommitmentApiContracts:
    """BE-SDBR-010: strict MTO public payload and auth boundaries."""

    def test_intake_contract_accepts_explicit_snapshot_but_has_no_material_toggle(self):
        payload = _intake_payload()
        payload["OperationalStateSnapshotID"] = "TST-MTO-OPS-EXPLICIT"

        intake = api.MtoOrderCommitmentIntakePayload(**payload)

        assert intake.OperationalStateSnapshotID == "TST-MTO-OPS-EXPLICIT"
        assert "OperationalStateSnapshotID" not in api._mto_order_from_payload(intake)
        with pytest.raises(ValidationError, match="CheckMaterialAvailability"):
            api.MtoOrderCommitmentIntakePayload(
                **{**payload, "CheckMaterialAvailability": False}
            )

    def test_intake_contract_requires_aware_iso_timestamps_not_numeric_epochs(self):
        payload = _intake_payload()

        intake = api.MtoOrderCommitmentIntakePayload(**payload)

        assert intake.RequestedDueAt.tzinfo is not None
        assert intake.ReceivedAt.tzinfo is not None
        for timestamp_field in ("RequestedDueAt", "ReceivedAt"):
            for numeric_epoch in (0, 1.0):
                with pytest.raises(ValidationError, match=timestamp_field):
                    api.MtoOrderCommitmentIntakePayload(
                        **{**payload, timestamp_field: numeric_epoch}
                    )

    def test_reevaluation_contract_has_no_material_window_or_threshold_override(self):
        payload = {
            "RequestedBy": "planner-1",
            "OperationalStateSnapshotID": "TST-MTO-OPS-CURRENT",
        }

        reevaluation = api.MtoOrderCommitmentReevaluationPayload(**payload)

        assert reevaluation.CheckMaterialAvailability is True
        for prohibited_field in (
            "MaterialCheckWindowMinutes",
            "CcrProtectionThresholdMinutes",
        ):
            with pytest.raises(ValidationError, match=prohibited_field):
                api.MtoOrderCommitmentReevaluationPayload(
                    **{**payload, prohibited_field: 60}
                )

    def test_boolean_contract_requires_json_booleans_without_coercion(self):
        decision_payload = {
            "DecisionID": "DEC-TST-MTO-BOOLEAN",
            "Decision": "Reject",
            "DecidedBy": "planner-1",
            "Reason": "Planner decision under the MTO commitment policy.",
            "ExpectedEvaluationFingerprint": "f" * 64,
        }
        cases = (
            (
                api.MtoOrderCommitmentReevaluationPayload,
                {"RequestedBy": "planner-1"},
                "CheckMaterialAvailability",
            ),
            (
                api.MtoOrderCommitmentDecisionPayload,
                decision_payload,
                "CcrRiskAcknowledged",
            ),
            (
                api.MtoOrderCommitmentDecisionPayload,
                decision_payload,
                "MaterialRiskAcknowledged",
            ),
        )

        for model, payload, boolean_field in cases:
            accepted = model(**{**payload, boolean_field: False})
            assert getattr(accepted, boolean_field) is False

            for coercive_value in ("false", 0):
                with pytest.raises(ValidationError, match=boolean_field):
                    model(**{**payload, boolean_field: coercive_value})

    def test_decision_contract_accepts_all_four_acceptance_actions_and_reject(self):
        payload = {
            "DecisionID": "DEC-TST-MTO-1",
            "DecidedBy": "planner-1",
            "Reason": "Planner decision under the MTO commitment policy.",
            "ExpectedEvaluationFingerprint": "f" * 64,
        }
        decisions = (
            "AcceptRequestedDate",
            "ConditionallyAcceptRequestedDate",
            "AcceptRecommendedDate",
            "ConditionallyAcceptRecommendedDate",
            "Reject",
        )

        for decision in decisions:
            result = api.MtoOrderCommitmentDecisionPayload(
                **{**payload, "Decision": decision}
            )
            assert result.Decision == decision

    def test_mto_payloads_forbid_unknown_authority_and_window_fields(self):
        decision_payload = {
            "DecisionID": "DEC-TST-MTO-2",
            "Decision": "AcceptRequestedDate",
            "DecidedBy": "planner-1",
            "Reason": "Planner decision under the MTO commitment policy.",
            "ExpectedEvaluationFingerprint": "f" * 64,
        }
        cases = (
            (
                api.MtoOrderCommitmentIntakePayload,
                _intake_payload(),
                "ApprovedExternalAcceptance",
            ),
            (
                api.MtoOrderCommitmentReevaluationPayload,
                {"RequestedBy": "planner-1"},
                "MaterialAvailabilityWindowMinutes",
            ),
            (
                api.MtoOrderCommitmentDecisionPayload,
                decision_payload,
                "CreatePlanningRun",
            ),
            (
                api.MtoOrderCommitmentDecisionPayload,
                decision_payload,
                "DdaeConfiguration",
            ),
            (
                api.MtoOrderCommitmentIntakePayload,
                _intake_payload(),
                "RawOperationalStateSnapshot",
            ),
        )

        for model, payload, prohibited_field in cases:
            with pytest.raises(ValidationError, match=prohibited_field):
                model(**{**payload, prohibited_field: "not-authoritative"})

    def test_auth_helper_allows_all_roles_get_and_only_planner_admin_post(self):
        for role in ("Viewer", "Planner", "Worker", "Admin"):
            assert api._planning_run_authorization_error(
                _auth_request("GET", role)
            ) is None

        for role in ("Planner", "Admin"):
            assert api._planning_run_authorization_error(
                _auth_request("POST", role)
            ) is None
        for role in ("Viewer", "Worker"):
            error = api._planning_run_authorization_error(_auth_request("POST", role))
            assert error is not None
            assert error.status_code == 403

        client = TestClient(api.create_app(require_auth=True))
        assert client.get(
            "/planner/workbench/order-commitments/workbench"
        ).status_code == 401


class TestOrderCommitmentApiOrchestration:
    """BE-SDBR-006 through BE-SDBR-010: MTO resolver evidence boundaries."""

    def test_resolver_requires_completed_approved_or_published_baseline(self):
        store, fixture, resolver = _orchestration_input()
        run = store.planning_runs[fixture["BaselinePlanningRunID"]]
        run["Status"] = "Queued"

        not_completed = _error_data(_evaluate_order_commitment(
            resolver, fixture, store=store
        ))

        assert not_completed["StatusCode"] == 409
        assert not_completed["Data"]["Status"] == "PlanningRunNotCompleted"

        run["Status"] = "Completed"
        run["PublicationStatus"] = "Draft"
        not_published = _error_data(_evaluate_order_commitment(
            resolver, fixture, store=store
        ))

        assert not_published["StatusCode"] == 409
        assert (
            not_published["Data"]["Status"]
            == "PlanningRunNotApprovedOrPublished"
        )

    def test_resolver_requires_master_schedule_and_primary_route_references(self):
        store, fixture, resolver = _orchestration_input()
        run = store.planning_runs[fixture["BaselinePlanningRunID"]]
        run["Schedule"] = None

        missing_schedule = _error_data(_evaluate_order_commitment(
            resolver, fixture, store=store
        ))

        assert missing_schedule["Data"]["Status"] == "PlanningRunScheduleMissing"

        store, fixture, resolver = _orchestration_input()
        master = store.master_data_versions[fixture["MasterDataVersionID"]]
        master["Routings"] = []

        missing_primary_route = _evaluation_data(_evaluate_order_commitment(
            resolver, fixture, store=store
        ))

        assert missing_primary_route["ShadowSchedule"]["Status"] == "NotAssessable"
        assert missing_primary_route["ShadowSchedule"]["Issues"] == [{
            "Code": "ROUTING_NOT_PRIMARY_OR_AMBIGUOUS",
            "Message": "Exactly one matching primary route is required.",
        }]

    def test_resolver_selects_latest_current_snapshot_by_default(self):
        store, fixture, resolver = _orchestration_input()
        baseline_snapshot = store.operational_state_snapshots[
            fixture["OperationalStateSnapshotID"]
        ]
        latest_snapshot = OperationalStateSnapshot(
            snapshot_id="TST-MTO-OPS-LATEST",
            captured_at=MTO_FIXTURE_TIME - timedelta(minutes=1),
            inventory_buffers=baseline_snapshot.inventory_buffers,
            material_availability=baseline_snapshot.material_availability,
            wip_limits=baseline_snapshot.wip_limits,
        )
        store.operational_state_snapshots[latest_snapshot.snapshot_id] = latest_snapshot

        evaluation = _evaluation_data(_evaluate_order_commitment(
            resolver, fixture, store=store
        ))

        assert evaluation["MaterialAssessment"]["SnapshotSelectionMode"] == (
            "LatestCurrent"
        )
        assert evaluation["MaterialAssessment"]["OperationalStateSnapshotID"] == (
            latest_snapshot.snapshot_id
        )

    def test_resolver_preserves_explicit_stale_and_future_as_insufficient_evidence(self):
        store, fixture, resolver = _orchestration_input()
        baseline_snapshot = store.operational_state_snapshots[
            fixture["OperationalStateSnapshotID"]
        ]
        for snapshot_id, captured_at, freshness in (
            ("TST-MTO-OPS-STALE", MTO_FIXTURE_TIME - timedelta(minutes=61), "Stale"),
            ("TST-MTO-OPS-FUTURE", MTO_FIXTURE_TIME + timedelta(minutes=1), "Future"),
        ):
            store.operational_state_snapshots[snapshot_id] = OperationalStateSnapshot(
                snapshot_id=snapshot_id,
                captured_at=captured_at,
                inventory_buffers=baseline_snapshot.inventory_buffers,
                material_availability=baseline_snapshot.material_availability,
                wip_limits=baseline_snapshot.wip_limits,
            )

            evaluation = _evaluation_data(_evaluate_order_commitment(
                resolver,
                fixture,
                store=store,
                requested_snapshot_id=snapshot_id,
            ))

            assert evaluation["MaterialAssessment"]["SnapshotSelectionMode"] == "Explicit"
            assert evaluation["MaterialAssessment"]["OperationalStateSnapshotID"] == snapshot_id
            assert evaluation["MaterialAssessment"]["Status"] == "EvidenceInsufficient"
            assert evaluation["MaterialAssessment"]["Issues"] == [{
                "Code": "OPERATIONAL_STATE_EVIDENCE_NOT_FRESH",
                "FreshnessStatus": freshness,
            }]

    def test_resolver_freezes_all_configuration_release_route_calendar_references(self):
        store, fixture, resolver = _orchestration_input()
        run = store.planning_runs[fixture["BaselinePlanningRunID"]]
        run.update({
            "OperatingModelConfigurationID": "OMC-MTO-1",
            "OperatingModelFingerprint": "a" * 64,
            "SchedulingConfigurationID": "SCH-MTO-1",
            "DDMRPConfigurationID": "DDMRP-MTO-1",
        })

        evaluation = _evaluation_data(_evaluate_order_commitment(
            resolver, fixture, store=store
        ))
        basis = evaluation["Basis"]

        assert basis["BaselinePlanningRunID"] == fixture["BaselinePlanningRunID"]
        assert basis["MasterDataVersionID"] == fixture["MasterDataVersionID"]
        assert basis["OperatingModelConfigurationID"] == "OMC-MTO-1"
        assert basis["OperatingModelFingerprint"] == "a" * 64
        assert basis["SchedulingConfigurationID"] == "SCH-MTO-1"
        assert basis["DDMRPConfigurationID"] == "DDMRP-MTO-1"
        assert basis["ReleasePolicyVersionID"] == "TST-MTO-RELEASE-POLICY-1"
        assert basis["RoutingFingerprint"]
        assert basis["CalendarFingerprint"]
        assert basis["FrozenReleasePolicyFingerprint"] == api.canonical_fingerprint(
            api.release_policy_evidence(run["FrozenReleasePolicy"])
        )

    def test_resolver_uses_only_reference_protection_policy(self):
        store, fixture, resolver = _orchestration_input()
        run = store.planning_runs[fixture["BaselinePlanningRunID"]]
        run["CcrProtectionThresholdPercent"] = 55

        evaluation = _evaluation_data(_evaluate_order_commitment(
            resolver, fixture, store=store
        ))

        assert evaluation["ProtectionPolicy"] == {
            "TargetPercent": 80.0,
            "Source": "ReferenceFallback",
            "Approved": False,
            "ConfigurationID": None,
        }

    def test_resolver_fingerprints_only_exact_relevant_capacity_and_material_rows(self):
        store, fixture, resolver = _orchestration_input()
        baseline = _evaluation_data(_evaluate_order_commitment(
            resolver, fixture, store=store
        ))
        store.ccr_capacity_reservations["IRRELEVANT-CAPACITY"] = {
            "ResourceID": "TST-MTO-NOT-A-CCR",
            "WindowStartAt": "not-a-time",
            "WindowEndAt": "still-not-a-time",
        }
        store.material_planning_allocations["IRRELEVANT-MATERIAL"] = {
            "ItemID": "TST-MTO-NOT-A-MATERIAL",
            "LocationID": "TST-MTO-NOT-A-LOCATION",
        }

        replay = _evaluation_data(_evaluate_order_commitment(
            resolver, fixture, store=store
        ))

        assert replay["EvaluationFingerprint"] == baseline["EvaluationFingerprint"]
        assert replay["Basis"]["RelevantCapacityLedger"] == []
        assert replay["Basis"]["RelevantMaterialLedger"] == []

    def test_resolver_rejects_missing_calendar_timezone_conservatively(self):
        store, fixture, resolver = _orchestration_input()
        master = store.master_data_versions[fixture["MasterDataVersionID"]]
        master["CalendarTimezone"] = ""

        evaluation = _evaluation_data(_evaluate_order_commitment(
            resolver, fixture, store=store
        ))

        assert evaluation["ShadowSchedule"]["Status"] == "NotAssessable"
        assert evaluation["ShadowSchedule"]["Issues"] == [{
            "Code": "CALENDAR_TIMEZONE_REQUIRED",
            "Message": "A calendar timezone is required for MTO shadow capacity.",
        }]


class TestOrderCommitmentApiIntakeAndReads:
    """BE-SDBR-010: idempotent MTO intake and sanitized read boundaries."""

    def test_intake_automatically_evaluates_with_material_check_enabled(self):
        client, store, fixture = _order_commitment_client()

        response = client.post(
            "/planner/workbench/order-commitments/intake",
            json=fixture["IntakePayloadTemplate"],
            headers=_planner_headers(),
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["Data"]["RegistrationStatus"] == "Created"
        evaluation_id = payload["Data"]["Evaluation"]["EvaluationID"]
        assert store.order_commitment_evaluations[evaluation_id][
            "MaterialAssessment"
        ]["CheckEnabled"] is True
        assert store.order_commitment_events[0]["ActorID"] == "planner-task17"
        assert payload["Data"]["Boundary"] == {
            "RecommendationOnly": True,
            "ExternalOrderAcceptance": "NotPerformed",
            "PlanningRunCreation": "NotPerformed",
            "ProductionMutation": "NotPerformed",
            "ReleaseMaterialGateStillRequired": True,
        }

    def test_duplicate_intake_returns_same_evaluation_and_one_event(self):
        client, store, fixture = _order_commitment_client()

        first = client.post(
            "/planner/workbench/order-commitments/intake",
            json=fixture["IntakePayloadTemplate"],
            headers=_planner_headers(),
        )
        revision_after_first = first.headers["X-Workbench-Revision"]
        duplicate = client.post(
            "/planner/workbench/order-commitments/intake",
            json=fixture["IntakePayloadTemplate"],
            headers=_planner_headers(),
        )

        assert duplicate.status_code == 200
        assert duplicate.json()["Data"]["RegistrationStatus"] == "Duplicate"
        assert duplicate.json()["Data"]["Evaluation"]["EvaluationID"] == (
            first.json()["Data"]["Evaluation"]["EvaluationID"]
        )
        assert len(store.order_commitment_evaluations) == 1
        assert len(store.order_commitment_events) == 1
        assert duplicate.headers["X-Workbench-Revision"] == revision_after_first

    def test_intake_with_stale_evidence_has_no_acceptance_action(self):
        client, store, fixture = _order_commitment_client()
        current = store.operational_state_snapshots[
            fixture["OperationalStateSnapshotID"]
        ]
        stale_id = "TST-MTO-OPS-STALE-INTAKE"
        store.operational_state_snapshots[stale_id] = OperationalStateSnapshot(
            snapshot_id=stale_id,
            captured_at=MTO_FIXTURE_TIME - timedelta(minutes=61),
            inventory_buffers=current.inventory_buffers,
            material_availability=current.material_availability,
            wip_limits=current.wip_limits,
        )
        payload = deepcopy(fixture["IntakePayloadTemplate"])
        payload["OperationalStateSnapshotID"] = stale_id

        response = client.post(
            "/planner/workbench/order-commitments/intake",
            json=payload,
            headers=_planner_headers(),
        )

        assert response.status_code == 200
        row = response.json()["Data"]["Evaluation"]
        assert row["MaterialStatus"] == "EvidenceInsufficient"
        assert not any(action.startswith("Accept") for action in row["AllowedActions"])

    def test_intake_malformed_route_persists_do_not_recommend_with_issue(self):
        client, store, fixture = _order_commitment_client()
        master = store.master_data_versions[fixture["MasterDataVersionID"]]
        master["Routings"] = []

        response = client.post(
            "/planner/workbench/order-commitments/intake",
            json=fixture["IntakePayloadTemplate"],
            headers=_planner_headers(),
        )

        assert response.status_code == 200
        row = response.json()["Data"]["Evaluation"]
        assert row["Recommendation"] == "DoNotRecommendAccept"
        evaluation = store.order_commitment_evaluations[row["EvaluationID"]]
        assert evaluation["ShadowSchedule"]["Issues"] == [{
            "Code": "ROUTING_NOT_PRIMARY_OR_AMBIGUOUS",
            "Message": "Exactly one matching primary route is required.",
        }]

    def test_workbench_and_detail_return_exact_sanitized_contract_and_revision(self):
        client, _, fixture = _order_commitment_client()
        intake = client.post(
            "/planner/workbench/order-commitments/intake",
            json=fixture["IntakePayloadTemplate"],
            headers=_planner_headers(),
        )
        evaluation_id = intake.json()["Data"]["Evaluation"]["EvaluationID"]

        workbench = client.get(
            "/planner/workbench/order-commitments/workbench",
            headers=_planner_headers(),
        )
        detail = client.get(
            f"/planner/workbench/order-commitments/{evaluation_id}",
            headers=_planner_headers(),
        )

        assert workbench.status_code == 200
        assert detail.status_code == 200
        assert set(workbench.json()["Data"]["Rows"][0]) == set(
            ORDER_COMMITMENT_ROW_FIELDS
        )
        assert set(detail.json()["Data"]) == set(DETAIL_FIELDS)
        assert "OrderContentFingerprint" not in detail.json()["Data"]["Order"]
        assert workbench.headers["X-Workbench-Revision"] == detail.headers[
            "X-Workbench-Revision"
        ]

    def test_unknown_detail_returns_order_commitment_not_found(self):
        client, _, _ = _order_commitment_client()

        response = client.get(
            "/planner/workbench/order-commitments/OCE-NOT-FOUND",
            headers=_planner_headers(),
        )

        assert response.status_code == 404
        assert response.json()["Data"]["Status"] == (
            "OrderCommitmentEvaluationNotFound"
        )

    def test_intake_creates_no_phase0_or_planning_run_objects(self):
        client, store, fixture = _order_commitment_client()
        before = {
            "PlanningRuns": deepcopy(store.planning_runs),
            "PlanningDemandCommitments": deepcopy(store.planning_demand_commitments),
            "PlanningReservationBatches": deepcopy(store.planning_reservation_batches),
            "CcrCapacityReservations": deepcopy(store.ccr_capacity_reservations),
            "MaterialPlanningAllocations": deepcopy(store.material_planning_allocations),
            "PlanningReservationEvents": deepcopy(store.planning_reservation_events),
        }

        response = client.post(
            "/planner/workbench/order-commitments/intake",
            json=fixture["IntakePayloadTemplate"],
            headers=_planner_headers(),
        )

        assert response.status_code == 200
        assert store.planning_runs == before["PlanningRuns"]
        assert store.planning_demand_commitments == before["PlanningDemandCommitments"]
        assert store.planning_reservation_batches == before[
            "PlanningReservationBatches"
        ]
        assert store.ccr_capacity_reservations == before["CcrCapacityReservations"]
        assert store.material_planning_allocations == before[
            "MaterialPlanningAllocations"
        ]
        assert store.planning_reservation_events == before[
            "PlanningReservationEvents"
        ]

    def test_v1_to_v2_intake_atomically_supersedes_v1_and_old_row_has_no_actions(self):
        client, store, fixture = _order_commitment_client()
        v1 = client.post(
            "/planner/workbench/order-commitments/intake",
            json=fixture["IntakePayloadTemplate"],
            headers=_planner_headers(),
        )
        v2_payload = deepcopy(fixture["IntakePayloadTemplate"])
        v2_payload["OrderVersion"] = "2"

        v2 = client.post(
            "/planner/workbench/order-commitments/intake",
            json=v2_payload,
            headers=_planner_headers(),
        )
        v1_id = v1.json()["Data"]["Evaluation"]["EvaluationID"]
        v2_id = v2.json()["Data"]["Evaluation"]["EvaluationID"]
        workbench = client.get(
            "/planner/workbench/order-commitments/workbench",
            headers=_planner_headers(),
        )
        rows = {row["EvaluationID"]: row for row in workbench.json()["Data"]["Rows"]}

        assert v2.status_code == 200
        assert store.order_commitment_evaluations[v1_id]["Status"] == "Superseded"
        assert store.order_commitment_evaluations[v1_id]["SupersededByEvaluationID"] == v2_id
        assert rows[v1_id]["AllowedActions"] == []
        assert rows[v2_id]["Status"] == "AwaitingPlannerDecision"
        assert [
            event["EventType"] for event in store.order_commitment_events
        ] == [
            "OrderCommitmentEvaluated",
            "OrderCommitmentEvaluationSuperseded",
            "OrderCommitmentEvaluated",
        ]

    def test_decision_against_superseded_v1_is_rejected(self):
        client, store, fixture = _order_commitment_client()
        v1 = client.post(
            "/planner/workbench/order-commitments/intake",
            json=fixture["IntakePayloadTemplate"],
            headers=_planner_headers(),
        )
        v2_payload = deepcopy(fixture["IntakePayloadTemplate"])
        v2_payload["OrderVersion"] = "2"
        client.post(
            "/planner/workbench/order-commitments/intake",
            json=v2_payload,
            headers=_planner_headers(),
        )
        v1_evaluation = store.order_commitment_evaluations[
            v1.json()["Data"]["Evaluation"]["EvaluationID"]
        ]

        with pytest.raises(OrderCommitmentConflict, match="Rejection is not allowed"):
            rejected_evaluation_record(
                evaluation=v1_evaluation,
                decision_id="DEC-TST-MTO-SUPERSEDED",
                decision="Reject",
                decided_by="planner-task17",
                decided_at=MTO_FIXTURE_TIME,
                reason="Newer order version supersedes this evaluation.",
                ccr_risk_acknowledged=False,
                material_risk_acknowledged=False,
            )

    def test_concurrent_v1_v2_intake_leaves_only_greatest_rank_open(self):
        client, store, fixture = _order_commitment_client()
        v1_payload = deepcopy(fixture["IntakePayloadTemplate"])
        v2_payload = deepcopy(fixture["IntakePayloadTemplate"])
        v2_payload["OrderVersion"] = "2"

        with ThreadPoolExecutor(max_workers=2) as executor:
            responses = list(executor.map(
                lambda payload: client.post(
                    "/planner/workbench/order-commitments/intake",
                    json=payload,
                    headers=_planner_headers(),
                ),
                (v1_payload, v2_payload),
            ))

        assert all(response.status_code in {200, 409} for response in responses)
        open_rows = [
            row
            for row in store.order_commitment_evaluations.values()
            if row["Status"] == "AwaitingPlannerDecision"
        ]
        assert len(open_rows) == 1
        assert open_rows[0]["Order"]["OrderVersion"] == "2"
        assert all(
            row["Order"]["OrderVersion"] == "2" or row["Status"] == "Superseded"
            for row in store.order_commitment_evaluations.values()
        )

    def test_new_version_after_rejected_is_allowed_but_after_accepted_requires_amendment(self):
        client, store, fixture = _order_commitment_client()
        v1 = client.post(
            "/planner/workbench/order-commitments/intake",
            json=fixture["IntakePayloadTemplate"],
            headers=_planner_headers(),
        )
        v1_id = v1.json()["Data"]["Evaluation"]["EvaluationID"]
        store.order_commitment_evaluations[v1_id] = rejected_evaluation_record(
            evaluation=store.order_commitment_evaluations[v1_id],
            decision_id="DEC-TST-MTO-REJECTED-V1",
            decision="Reject",
            decided_by="planner-task17",
            decided_at=MTO_FIXTURE_TIME,
            reason="Rejected version may be replaced by a newer version.",
            ccr_risk_acknowledged=False,
            material_risk_acknowledged=False,
        )
        v2_payload = deepcopy(fixture["IntakePayloadTemplate"])
        v2_payload["OrderVersion"] = "2"

        v2 = client.post(
            "/planner/workbench/order-commitments/intake",
            json=v2_payload,
            headers=_planner_headers(),
        )
        v2_id = v2.json()["Data"]["Evaluation"]["EvaluationID"]
        store.order_commitment_evaluations[v2_id]["Status"] = (
            "AcceptedPendingFormalSchedule"
        )
        v3_payload = deepcopy(fixture["IntakePayloadTemplate"])
        v3_payload["OrderVersion"] = "3"

        v3 = client.post(
            "/planner/workbench/order-commitments/intake",
            json=v3_payload,
            headers=_planner_headers(),
        )

        assert v2.status_code == 200
        assert v3.status_code == 409
        assert v3.json()["Data"]["Status"] == (
            "AcceptedOrderVersionChangeRequiresExplicitAmendment"
        )


class TestOrderCommitmentApiReevaluation:
    """BE-SDBR-010: immutable, current-evidence MTO re-evaluation."""

    @staticmethod
    def _intake_open_evaluation(
        client: TestClient,
        fixture: dict[str, object],
    ) -> str:
        intake = client.post(
            "/planner/workbench/order-commitments/intake",
            json=fixture["IntakePayloadTemplate"],
            headers=_planner_headers(),
        )
        assert intake.status_code == 200
        return intake.json()["Data"]["Evaluation"]["EvaluationID"]

    def test_reevaluation_defaults_material_check_on_and_selects_new_latest_snapshot(self):
        client, store, fixture = _order_commitment_client()
        source_id = self._intake_open_evaluation(client, fixture)
        current = store.operational_state_snapshots[
            fixture["OperationalStateSnapshotID"]
        ]
        latest_id = "TST-MTO-OPS-LATEST-REEVALUATION"
        store.operational_state_snapshots[latest_id] = OperationalStateSnapshot(
            snapshot_id=latest_id,
            captured_at=MTO_FIXTURE_TIME,
            inventory_buffers=current.inventory_buffers,
            material_availability=current.material_availability,
            wip_limits=current.wip_limits,
        )

        response = client.post(
            f"/planner/workbench/order-commitments/{source_id}/reevaluate",
            json={"RequestedBy": "planner-re-evaluation"},
            headers=_planner_headers(),
        )

        assert response.status_code == 200
        reevaluated_id = response.json()["Data"]["Evaluation"]["EvaluationID"]
        reevaluated = store.order_commitment_evaluations[reevaluated_id]
        assert reevaluated["MaterialAssessment"]["CheckEnabled"] is True
        assert reevaluated["MaterialAssessment"]["OperationalStateSnapshotID"] == latest_id

    @pytest.mark.parametrize(
        ("snapshot_id", "captured_at", "freshness"),
        (
            ("TST-MTO-OPS-STALE-REEVALUATION", MTO_FIXTURE_TIME - timedelta(minutes=61), "Stale"),
            ("TST-MTO-OPS-FUTURE-REEVALUATION", MTO_FIXTURE_TIME + timedelta(minutes=1), "Future"),
        ),
    )
    def test_explicit_stale_or_future_snapshot_persists_insufficient_evidence(
        self,
        snapshot_id: str,
        captured_at: datetime,
        freshness: str,
    ):
        client, store, fixture = _order_commitment_client()
        source_id = self._intake_open_evaluation(client, fixture)
        current = store.operational_state_snapshots[
            fixture["OperationalStateSnapshotID"]
        ]
        store.operational_state_snapshots[snapshot_id] = OperationalStateSnapshot(
            snapshot_id=snapshot_id,
            captured_at=captured_at,
            inventory_buffers=current.inventory_buffers,
            material_availability=current.material_availability,
            wip_limits=current.wip_limits,
        )

        response = client.post(
            f"/planner/workbench/order-commitments/{source_id}/reevaluate",
            json={
                "RequestedBy": "planner-re-evaluation",
                "OperationalStateSnapshotID": snapshot_id,
            },
            headers=_planner_headers(),
        )

        assert response.status_code == 200
        reevaluated_id = response.json()["Data"]["Evaluation"]["EvaluationID"]
        material = store.order_commitment_evaluations[reevaluated_id][
            "MaterialAssessment"
        ]
        assert material["OperationalStateFreshnessStatus"] == freshness
        assert material["Status"] == "EvidenceInsufficient"
        assert material["AllocationRequests"] == []

    def test_material_opt_out_requires_reason_and_has_no_allocations(self):
        client, store, fixture = _order_commitment_client()
        source_id = self._intake_open_evaluation(client, fixture)

        invalid = client.post(
            f"/planner/workbench/order-commitments/{source_id}/reevaluate",
            json={
                "RequestedBy": "planner-re-evaluation",
                "CheckMaterialAvailability": False,
                "MaterialCheckSkipReason": "   ",
            },
            headers=_planner_headers(),
        )
        valid = client.post(
            f"/planner/workbench/order-commitments/{source_id}/reevaluate",
            json={
                "RequestedBy": "planner-re-evaluation",
                "CheckMaterialAvailability": False,
                "MaterialCheckSkipReason": "Capacity-only commitment review.",
            },
            headers=_planner_headers(),
        )

        assert invalid.status_code == 409
        assert valid.status_code == 200
        reevaluated_id = valid.json()["Data"]["Evaluation"]["EvaluationID"]
        material = store.order_commitment_evaluations[reevaluated_id][
            "MaterialAssessment"
        ]
        assert material["CheckEnabled"] is False
        assert material["AllocationRequests"] == []

    def test_reevaluation_payload_cannot_override_material_window(self):
        client, _, fixture = _order_commitment_client()
        source_id = self._intake_open_evaluation(client, fixture)

        response = client.post(
            f"/planner/workbench/order-commitments/{source_id}/reevaluate",
            json={
                "RequestedBy": "planner-re-evaluation",
                "MaterialAvailabilityWindowMinutes": 999,
            },
            headers=_planner_headers(),
        )

        assert response.status_code == 422
        assert "MaterialAvailabilityWindowMinutes" in response.text

    def test_new_evaluation_supersedes_only_open_source_and_preserves_events(self):
        client, store, fixture = _order_commitment_client()
        source_id = self._intake_open_evaluation(client, fixture)
        current = store.operational_state_snapshots[
            fixture["OperationalStateSnapshotID"]
        ]
        store.operational_state_snapshots["TST-MTO-OPS-NEW-EVIDENCE"] = (
            OperationalStateSnapshot(
                snapshot_id="TST-MTO-OPS-NEW-EVIDENCE",
                captured_at=MTO_FIXTURE_TIME,
                inventory_buffers=current.inventory_buffers,
                material_availability=current.material_availability,
                wip_limits=current.wip_limits,
            )
        )

        response = client.post(
            f"/planner/workbench/order-commitments/{source_id}/reevaluate",
            json={"RequestedBy": "planner-re-evaluation"},
            headers=_planner_headers(),
        )

        assert response.status_code == 200
        reevaluated_id = response.json()["Data"]["Evaluation"]["EvaluationID"]
        assert store.order_commitment_evaluations[source_id]["Status"] == "Superseded"
        assert store.order_commitment_evaluations[source_id][
            "SupersededByEvaluationID"
        ] == reevaluated_id
        assert [event["EventType"] for event in store.order_commitment_events] == [
            "OrderCommitmentEvaluated",
            "OrderCommitmentEvaluationSuperseded",
            "OrderCommitmentReevaluated",
        ]
        superseded_event, reevaluated_event = store.order_commitment_events[-2:]
        assert superseded_event["ActorID"] == reevaluated_event["ActorID"] == "planner-task17"
        assert superseded_event["OccurredAt"] == reevaluated_event["OccurredAt"]
        assert reevaluated_event["CausationID"] == source_id

    def test_unchanged_replay_returns_duplicate_without_second_event(self):
        client, store, fixture = _order_commitment_client()
        source_id = self._intake_open_evaluation(client, fixture)
        before_revision = client.get(
            "/planner/workbench/order-commitments/workbench",
            headers=_planner_headers(),
        ).headers["X-Workbench-Revision"]

        first = client.post(
            f"/planner/workbench/order-commitments/{source_id}/reevaluate",
            json={
                "RequestedBy": "planner-re-evaluation",
                "OperationalStateSnapshotID": fixture[
                    "OperationalStateSnapshotID"
                ],
            },
            headers=_planner_headers(),
        )
        second = client.post(
            f"/planner/workbench/order-commitments/{source_id}/reevaluate",
            json={
                "RequestedBy": "planner-re-evaluation",
                "OperationalStateSnapshotID": fixture[
                    "OperationalStateSnapshotID"
                ],
            },
            headers=_planner_headers(),
        )

        assert first.status_code == 200
        assert second.status_code == 200
        assert first.json()["Data"]["RegistrationStatus"] == "Duplicate"
        assert second.json()["Data"]["RegistrationStatus"] == "Duplicate"
        assert first.headers["X-Workbench-Revision"] == before_revision
        assert second.headers["X-Workbench-Revision"] == before_revision
        assert len(store.order_commitment_events) == 1

    @pytest.mark.parametrize(
        "status", ("AcceptedPendingFormalSchedule", "Rejected", "Superseded")
    )
    def test_terminal_or_superseded_source_has_no_reevaluation(self, status: str):
        client, store, fixture = _order_commitment_client()
        source_id = self._intake_open_evaluation(client, fixture)
        store.order_commitment_evaluations[source_id]["Status"] = status

        response = client.post(
            f"/planner/workbench/order-commitments/{source_id}/reevaluate",
            json={"RequestedBy": "planner-re-evaluation"},
            headers=_planner_headers(),
        )

        assert response.status_code == 409
        assert response.json()["Data"]["Status"] == "OrderCommitmentEvaluationNotReevaluatable"

    def test_reevaluation_creates_no_phase0_or_planning_run_objects(self):
        client, store, fixture = _order_commitment_client()
        source_id = self._intake_open_evaluation(client, fixture)
        before = {
            "PlanningRuns": deepcopy(store.planning_runs),
            "PlanningDemandCommitments": deepcopy(store.planning_demand_commitments),
            "PlanningReservationBatches": deepcopy(store.planning_reservation_batches),
            "CcrCapacityReservations": deepcopy(store.ccr_capacity_reservations),
            "MaterialPlanningAllocations": deepcopy(store.material_planning_allocations),
            "PlanningReservationEvents": deepcopy(store.planning_reservation_events),
        }

        response = client.post(
            f"/planner/workbench/order-commitments/{source_id}/reevaluate",
            json={"RequestedBy": "planner-re-evaluation"},
            headers=_planner_headers(),
        )

        assert response.status_code == 200
        assert store.planning_runs == before["PlanningRuns"]
        assert store.planning_demand_commitments == before["PlanningDemandCommitments"]
        assert store.planning_reservation_batches == before[
            "PlanningReservationBatches"
        ]
        assert store.ccr_capacity_reservations == before["CcrCapacityReservations"]
        assert store.material_planning_allocations == before[
            "MaterialPlanningAllocations"
        ]
        assert store.planning_reservation_events == before[
            "PlanningReservationEvents"
        ]
