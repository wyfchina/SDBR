"""BE-SDBR-010: MTO API payload and authorization contracts."""

from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor
from dataclasses import fields
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


def _decision_payload(
    evaluation: dict[str, object],
    *,
    decision_id: str = "DEC-TST-MTO-TASK19",
    decision: str = "Reject",
    reason: str = "Planner rejected the requested MTO commitment.",
    ccr_risk_acknowledged: bool = False,
    material_risk_acknowledged: bool = False,
) -> dict[str, object]:
    return {
        "DecisionID": decision_id,
        "Decision": decision,
        "DecidedBy": "client-spoofed-planner",
        "Reason": reason,
        "ExpectedEvaluationFingerprint": evaluation["EvaluationFingerprint"],
        "CcrRiskAcknowledged": ccr_risk_acknowledged,
        "MaterialRiskAcknowledged": material_risk_acknowledged,
    }


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


PUBLIC_STORE_FIELDS = tuple(
    item.name
    for item in fields(WorkbenchStateStore)
    if not item.name.startswith("_")
)
MTO_FIELDS = {
    "order_commitment_evaluations",
    "order_commitment_events",
    "revision",
}
PHASE0_FIELDS = {
    "planning_demand_commitments",
    "planning_reservation_batches",
    "ccr_capacity_reservations",
    "material_planning_allocations",
    "planning_reservation_events",
    "processed_planning_event_keys",
}
ALLOWED_STORE_CHANGES = {
    "intake": MTO_FIELDS,
    "reevaluate": MTO_FIELDS,
    "reject": MTO_FIELDS,
    "accept": MTO_FIELDS | PHASE0_FIELDS,
}


def _public_store_snapshot(store: WorkbenchStateStore):
    return {
        name: deepcopy(getattr(store, name))
        for name in PUBLIC_STORE_FIELDS
    }


def _assert_only_operation_fields_changed(
    *,
    before: dict[str, object],
    after: dict[str, object],
    operation: str,
) -> None:
    assert set(before) == set(PUBLIC_STORE_FIELDS) == set(after)
    allowed = ALLOWED_STORE_CHANGES[operation]
    for name in PUBLIC_STORE_FIELDS:
        if name not in allowed:
            assert after[name] == before[name], name


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

class TestOrderCommitmentApiDecisionReplay:
    """BE-SDBR-010: revision-guarded decisions and immutable terminal replay."""

    @staticmethod
    def _open_evaluation(
        client: TestClient,
        fixture: dict[str, object],
    ) -> str:
        response = client.post(
            "/planner/workbench/order-commitments/intake",
            json=fixture["IntakePayloadTemplate"],
            headers=_planner_headers(),
        )
        assert response.status_code == 200
        return response.json()["Data"]["Evaluation"]["EvaluationID"]

    @staticmethod
    def _decision_headers(
        client: TestClient,
        *,
        actor_id: str = "planner-task17",
    ) -> dict[str, str]:
        revision = client.get(
            "/planner/workbench/order-commitments/workbench",
            headers=_planner_headers(),
        ).headers["X-Workbench-Revision"]
        return {
            "X-Actor-ID": actor_id,
            "X-Actor-Role": "Planner",
            "If-Match": revision,
        }

    def _rejected_fixture(self):
        client, store, fixture = _order_commitment_client()
        evaluation_id = self._open_evaluation(client, fixture)
        evaluation = store.order_commitment_evaluations[evaluation_id]
        return client, store, evaluation_id, _decision_payload(evaluation)

    def _accepted_fixture(self):
        client, store, fixture = _order_commitment_client()
        evaluation_id = self._open_evaluation(client, fixture)
        evaluation = store.order_commitment_evaluations[evaluation_id]
        assert "AcceptRequestedDate" in evaluation["Recommendation"]["AllowedActions"]
        payload = _decision_payload(
            evaluation,
            decision_id="DEC-TST-MTO-ACCEPTED-REPLAY",
            decision="AcceptRequestedDate",
            reason="Planner accepted the requested MTO commitment.",
            ccr_risk_acknowledged=True,
        )
        acceptance = client.post(
            f"/planner/workbench/order-commitments/{evaluation_id}/decision",
            json=payload,
            headers=self._decision_headers(client),
        )
        assert acceptance.status_code == 200
        demand = next(iter(store.planning_demand_commitments.values()))
        batch = next(iter(store.planning_reservation_batches.values()))
        capacity = next(iter(store.ccr_capacity_reservations.values()))
        material = next(iter(store.material_planning_allocations.values()))
        demand.update({"Status": "LinkedToFormalOrder", "RecordVersion": 2})
        for record in (batch, capacity):
            record.update({
                "Status": "ConvertedToScheduledOccupancy",
                "RecordVersion": 2,
                "PlanningRunID": "RUN-TST-MTO-1",
                "LastTransitionAt": "2026-07-20T12:00:00+00:00",
                "EventType": "PlanningRunCompleted",
            })
        material.update({
            "Status": "Externalized",
            "RecordVersion": 2,
            "ExternalAllocationRef": "ERP-ALLOC-TST-MTO-1",
            "MaterialSnapshotID": "OPS-AUTHORITY-TST-MTO-1",
        })
        return client, store, evaluation_id, payload

    def test_decision_requires_if_match_and_exact_evaluation_fingerprint(self):
        client, store, evaluation_id, payload = self._rejected_fixture()
        missing = client.post(
            f"/planner/workbench/order-commitments/{evaluation_id}/decision",
            json=payload,
            headers=_planner_headers(),
        )
        mismatched = client.post(
            f"/planner/workbench/order-commitments/{evaluation_id}/decision",
            json={**payload, "ExpectedEvaluationFingerprint": "0" * 64},
            headers=self._decision_headers(client),
        )

        assert missing.status_code == 428
        assert missing.json()["Data"]["Status"] == "OrderCommitmentPreconditionRequired"
        assert mismatched.status_code == 409
        assert mismatched.json()["Data"]["Status"] == (
            "OrderCommitmentEvaluationFingerprintMismatch"
        )
        assert store.order_commitment_evaluations[evaluation_id]["Status"] == "AwaitingPlannerDecision"

    def test_reject_records_server_actor_and_time_without_phase0_rows(self):
        client, store, evaluation_id, payload = self._rejected_fixture()
        before_phase0 = (
            deepcopy(store.planning_demand_commitments),
            deepcopy(store.planning_reservation_batches),
            deepcopy(store.ccr_capacity_reservations),
            deepcopy(store.material_planning_allocations),
            deepcopy(store.planning_reservation_events),
            deepcopy(store.processed_planning_event_keys),
        )

        response = client.post(
            f"/planner/workbench/order-commitments/{evaluation_id}/decision",
            json=payload,
            headers=self._decision_headers(client),
        )

        assert response.status_code == 200
        rejected = store.order_commitment_evaluations[evaluation_id]
        assert rejected["Status"] == "Rejected"
        assert rejected["Decision"]["DecidedBy"] == "planner-task17"
        assert rejected["Decision"]["DecidedAt"] == MTO_FIXTURE_TIME.isoformat()
        assert (
            store.planning_demand_commitments,
            store.planning_reservation_batches,
            store.ccr_capacity_reservations,
            store.material_planning_allocations,
            store.planning_reservation_events,
            store.processed_planning_event_keys,
        ) == before_phase0

    def test_exact_reject_replay_returns_same_record_without_duplicate_event(self):
        client, store, evaluation_id, payload = self._rejected_fixture()
        first = client.post(
            f"/planner/workbench/order-commitments/{evaluation_id}/decision",
            json=payload,
            headers=self._decision_headers(client),
        )
        event_count = len(store.order_commitment_events)
        second = client.post(
            f"/planner/workbench/order-commitments/{evaluation_id}/decision",
            json=payload,
            headers=self._decision_headers(client),
        )

        assert first.status_code == second.status_code == 200
        assert first.json()["Data"] == second.json()["Data"]
        assert len(store.order_commitment_events) == event_count

    def test_exact_accepted_replay_returns_same_verified_phase0_result(self):
        client, store, evaluation_id, payload = self._accepted_fixture()
        before = _public_store_snapshot(store)

        response = client.post(
            f"/planner/workbench/order-commitments/{evaluation_id}/decision",
            json=payload,
            headers=self._decision_headers(client),
        )

        assert response.status_code == 200
        data = response.json()["Data"]
        assert data["Status"] == "AcceptedPendingFormalSchedule"
        assert data["DemandCommitmentID"] == store.order_commitment_evaluations[
            evaluation_id
        ]["Decision"]["DemandCommitmentID"]
        assert data["ReservationBatchID"] == store.order_commitment_evaluations[
            evaluation_id
        ]["Decision"]["ReservationBatchID"]
        assert next(iter(store.planning_reservation_batches.values()))["Status"] == (
            "ConvertedToScheduledOccupancy"
        )
        assert next(iter(store.material_planning_allocations.values()))["Status"] == (
            "Externalized"
        )
        assert _public_store_snapshot(store) == before

    @pytest.mark.parametrize(
        "mutation",
        (
            "demand_quantity", "batch_confirmed_by", "capacity_reserved_minutes",
            "material_allocated_qty", "event_payload_fingerprint",
            "event_result_batch_id", "event_actor_id", "event_occurred_at",
            "event_demand_id", "batch_demand_id", "batch_capacity_id",
            "batch_material_id",
        ),
    )
    def test_exact_accepted_replay_rejects_one_field_phase0_corruption(self, mutation: str):
        client, store, evaluation_id, payload = self._accepted_fixture()
        demand = next(iter(store.planning_demand_commitments.values()))
        batch = next(iter(store.planning_reservation_batches.values()))
        capacity = next(iter(store.ccr_capacity_reservations.values()))
        material = next(iter(store.material_planning_allocations.values()))
        event = store.planning_reservation_events[0]
        if mutation == "demand_quantity": demand["Quantity"] = 999
        elif mutation == "batch_confirmed_by": batch["ConfirmedBy"] = "planner-corrupted"
        elif mutation == "capacity_reserved_minutes": capacity["ReservedMinutes"] = 999
        elif mutation == "material_allocated_qty": material["AllocatedQty"] = 999
        elif mutation == "event_payload_fingerprint": event["PayloadFingerprint"] = "corrupted"
        elif mutation == "event_result_batch_id": event["Result"]["ReservationBatchID"] = "PRB-corrupted"
        elif mutation == "event_actor_id": event["ActorID"] = "planner-corrupted"
        elif mutation == "event_occurred_at": event["OccurredAt"] = "2026-07-13T08:00:00+00:00"
        elif mutation == "event_demand_id": event["DemandCommitmentID"] = "DC-corrupted"
        elif mutation == "batch_demand_id": batch["DemandCommitmentID"] = "DC-corrupted"
        elif mutation == "batch_capacity_id": batch["CapacityReservationIDs"][0] = "CCR-corrupted"
        else: batch["MaterialAllocationIDs"][0] = "MAT-corrupted"
        before = _public_store_snapshot(store)

        response = client.post(
            f"/planner/workbench/order-commitments/{evaluation_id}/decision",
            json=payload,
            headers=self._decision_headers(client),
        )

        assert response.status_code == 409
        assert response.json()["Data"]["Status"] == (
            "OrderCommitmentDecisionReplayEvidenceMismatch"
        )
        assert _public_store_snapshot(store) == before

    @pytest.mark.parametrize(
        ("payload_change", "headers_change", "expected_status"),
        (
            ({"Decision": "AcceptRequestedDate"}, {}, "OrderCommitmentDecisionReplayConflict"),
            ({"ExpectedEvaluationFingerprint": "0" * 64}, {}, "OrderCommitmentEvaluationFingerprintMismatch"),
            ({}, {"X-Actor-ID": "planner-other"}, "OrderCommitmentDecisionReplayConflict"),
            ({"Reason": "A different trimmed rejection reason."}, {}, "OrderCommitmentDecisionReplayConflict"),
            ({"CcrRiskAcknowledged": True}, {}, "OrderCommitmentDecisionReplayConflict"),
            ({"MaterialRiskAcknowledged": True}, {}, "OrderCommitmentDecisionReplayConflict"),
        ),
    )
    def test_same_decision_id_one_field_at_a_time_change_conflicts(
        self,
        payload_change: dict[str, object],
        headers_change: dict[str, str],
        expected_status: str,
    ):
        client, _, evaluation_id, payload = self._rejected_fixture()
        first = client.post(
            f"/planner/workbench/order-commitments/{evaluation_id}/decision",
            json=payload,
            headers=self._decision_headers(client),
        )
        assert first.status_code == 200
        headers = self._decision_headers(client)
        headers.update(headers_change)

        response = client.post(
            f"/planner/workbench/order-commitments/{evaluation_id}/decision",
            json={**payload, **payload_change},
            headers=headers,
        )

        assert response.status_code == 409
        assert response.json()["Data"]["Status"] == expected_status

    def test_terminal_row_rejects_new_decision_id(self):
        client, _, evaluation_id, payload = self._rejected_fixture()
        first = client.post(
            f"/planner/workbench/order-commitments/{evaluation_id}/decision",
            json=payload,
            headers=self._decision_headers(client),
        )
        assert first.status_code == 200

        response = client.post(
            f"/planner/workbench/order-commitments/{evaluation_id}/decision",
            json={**payload, "DecisionID": "DEC-TST-MTO-NEW"},
            headers=self._decision_headers(client),
        )

        assert response.status_code == 409
        assert response.json()["Data"]["Status"] == "OrderCommitmentDecisionReplayConflict"

    def test_decision_event_and_record_share_one_server_time_and_actor(self):
        client, store, evaluation_id, payload = self._rejected_fixture()

        response = client.post(
            f"/planner/workbench/order-commitments/{evaluation_id}/decision",
            json=payload,
            headers=self._decision_headers(client),
        )

        assert response.status_code == 200
        decision = store.order_commitment_evaluations[evaluation_id]["Decision"]
        event = store.order_commitment_events[-1]
        assert decision["DecidedBy"] == event["ActorID"] == "planner-task17"
        assert decision["DecidedAt"] == event["OccurredAt"] == MTO_FIXTURE_TIME.isoformat()


class TestOrderCommitmentApiStaleness:
    """BE-SDBR-008 through BE-SDBR-010: acceptance uses exact current facts."""

    @staticmethod
    def _fixture(
        *,
        explicit_snapshot: bool = True,
    ) -> tuple[
        TestClient,
        WorkbenchStateStore,
        dict[str, object],
        list[datetime],
        str,
    ]:
        clock = [MTO_FIXTURE_TIME]
        store, fixture = _order_commitment_store(clock[0])
        client = TestClient(api.create_app(
            state_store=store,
            require_auth=True,
            utc_now=lambda: clock[0],
        ))
        payload = deepcopy(fixture["IntakePayloadTemplate"])
        if not explicit_snapshot:
            payload["OperationalStateSnapshotID"] = None
        intake = client.post(
            "/planner/workbench/order-commitments/intake",
            json=payload,
            headers=_planner_headers(),
        )
        assert intake.status_code == 200
        return (
            client,
            store,
            fixture,
            clock,
            intake.json()["Data"]["Evaluation"]["EvaluationID"],
        )

    @staticmethod
    def _decision_headers(client: TestClient) -> dict[str, str]:
        return TestOrderCommitmentApiDecisionReplay._decision_headers(client)

    @staticmethod
    def _acceptance_payload(evaluation: dict[str, object]) -> dict[str, object]:
        return _decision_payload(
            evaluation,
            decision_id="DEC-TST-MTO-STALE",
            decision="AcceptRequestedDate",
            reason="Planner requests an MTO acceptance after current-state checks.",
            ccr_risk_acknowledged=True,
        )

    @staticmethod
    def _capacity_request(evaluation: dict[str, object]) -> dict[str, object]:
        request = evaluation["DecisionFacts"]["CapacityReservationRequests"][0]
        assert request["ResourceID"] == "TST-MTO-CCR-1"
        assert "08:00" in str(request["WindowStartAt"])
        assert "16:00" in str(request["WindowEndAt"])
        return request

    @staticmethod
    def _capacity_reservation(
        request: dict[str, object],
        capacity_reservation_id: str,
        **overrides: object,
    ) -> dict[str, object]:
        return {
            **request,
            "CapacityReservationID": capacity_reservation_id,
            "ReservationBatchID": "PRB-TST-MTO-OTHER",
            "DemandCommitmentID": "DC-TST-MTO-OTHER",
            "DemandClass": "MTO",
            "Status": "ActivePlanReservation",
            "RecordVersion": 1,
            **overrides,
        }

    @staticmethod
    def _material_allocation(
        material_allocation_id: str,
        **overrides: object,
    ) -> dict[str, object]:
        return {
            "MaterialAllocationID": material_allocation_id,
            "ReservationBatchID": "PRB-TST-MTO-OTHER",
            "DemandCommitmentID": "DC-TST-MTO-OTHER",
            "DemandClass": "MTO",
            "ItemID": "TST-MTO-RM-1",
            "LocationID": "TST-MAIN",
            "AllocatedQty": 5.0,
            "MaterialSnapshotID": "TST-MTO-OPS-CURRENT",
            "Status": "ActivePlanReservation",
            "RecordVersion": 1,
            **overrides,
        }

    def _assert_stale(
        self,
        *,
        client: TestClient,
        store: WorkbenchStateStore,
        evaluation_id: str,
    ) -> None:
        evaluation = deepcopy(store.order_commitment_evaluations[evaluation_id])
        payload = self._acceptance_payload(evaluation)
        before = _public_store_snapshot(store)
        for _ in range(2):
            response = client.post(
                f"/planner/workbench/order-commitments/{evaluation_id}/decision",
                json=payload,
                headers=self._decision_headers(client),
            )
            assert response.status_code == 409
            assert response.json()["Data"]["Status"] == (
                "OrderCommitmentEvaluationStale"
            )
            assert _public_store_snapshot(store) == before

    def _assert_currently_eligible(
        self,
        *,
        client: TestClient,
        store: WorkbenchStateStore,
        evaluation_id: str,
    ) -> None:
        snapshot = store.snapshot_state()
        response = client.post(
            f"/planner/workbench/order-commitments/{evaluation_id}/decision",
            json=self._acceptance_payload(
                store.order_commitment_evaluations[evaluation_id]
            ),
            headers=self._decision_headers(client),
        )
        assert response.status_code == 200
        assert response.json()["Data"]["Status"] == (
            "AcceptedPendingFormalSchedule"
        )
        store.restore_state(snapshot)

    def _rechecked_without_material(
        self,
        *,
        client: TestClient,
        store: WorkbenchStateStore,
        evaluation_id: str,
    ) -> str:
        response = client.post(
            f"/planner/workbench/order-commitments/{evaluation_id}/reevaluate",
            json={
                "RequestedBy": "planner-staleness",
                "CheckMaterialAvailability": False,
                "MaterialCheckSkipReason": "Capacity-only staleness test.",
            },
            headers=_planner_headers(),
        )
        assert response.status_code == 200
        rechecked_id = response.json()["Data"]["Evaluation"]["EvaluationID"]
        assert store.order_commitment_evaluations[rechecked_id]["MaterialAssessment"][
            "CheckEnabled"
        ] is False
        return rechecked_id

    def test_exact_assessed_0800_1600_capacity_change_marks_evaluation_stale(self):
        client, store, _, _, evaluation_id = self._fixture()
        request = self._capacity_request(
            store.order_commitment_evaluations[evaluation_id]
        )
        store.ccr_capacity_reservations["CCR-TST-MTO-STALE"] = (
            self._capacity_reservation(request, "CCR-TST-MTO-STALE")
        )

        self._assert_stale(
            client=client, store=store, evaluation_id=evaluation_id
        )

    def test_same_resource_different_window_does_not_mark_evaluation_stale(self):
        client, store, fixture, _, evaluation_id = self._fixture()
        request = self._capacity_request(
            store.order_commitment_evaluations[evaluation_id]
        )
        _, start, end = fixture["CapacityWindowKeys"][1]
        store.ccr_capacity_reservations["CCR-TST-MTO-OTHER-WINDOW"] = (
            self._capacity_reservation(
                request,
                "CCR-TST-MTO-OTHER-WINDOW",
                WindowStartAt=start,
                WindowEndAt=end,
                LatestAllowedCompletionAt=end,
            )
        )
        store.save()

        self._assert_currently_eligible(
            client=client, store=store, evaluation_id=evaluation_id
        )

    def test_unrelated_resource_change_does_not_mark_evaluation_stale(self):
        client, store, _, _, evaluation_id = self._fixture()
        store.ccr_capacity_reservations["CCR-TST-MTO-UNRELATED"] = {
            "CapacityReservationID": "CCR-TST-MTO-UNRELATED",
            "ResourceID": "TST-MTO-NOT-A-CCR",
            "WindowStartAt": "not-a-time",
            "WindowEndAt": "still-not-a-time",
        }
        store.save()

        self._assert_currently_eligible(
            client=client, store=store, evaluation_id=evaluation_id
        )

    def test_relevant_requirement_item_location_change_marks_stale(self):
        client, store, _, _, evaluation_id = self._fixture()
        store.material_planning_allocations["MPA-TST-MTO-STALE"] = (
            self._material_allocation("MPA-TST-MTO-STALE")
        )

        self._assert_stale(
            client=client, store=store, evaluation_id=evaluation_id
        )

    def test_unrelated_item_location_change_remains_eligible_after_revision_refresh(self):
        client, store, _, _, evaluation_id = self._fixture()
        store.material_planning_allocations["MPA-TST-MTO-UNRELATED"] = {
            "MaterialAllocationID": "MPA-TST-MTO-UNRELATED",
            "ItemID": "TST-MTO-NOT-A-MATERIAL",
            "LocationID": "TST-MTO-NOT-A-LOCATION",
        }
        store.save()

        self._assert_currently_eligible(
            client=client, store=store, evaluation_id=evaluation_id
        )

    def test_new_latest_snapshot_marks_latest_mode_evaluation_stale(self):
        client, store, fixture, _, evaluation_id = self._fixture(
            explicit_snapshot=False
        )
        selected = store.operational_state_snapshots[
            fixture["OperationalStateSnapshotID"]
        ]
        store.operational_state_snapshots["TST-MTO-OPS-LATEST"] = (
            OperationalStateSnapshot(
                snapshot_id="TST-MTO-OPS-LATEST",
                captured_at=selected.captured_at + timedelta(minutes=1),
                inventory_buffers=deepcopy(selected.inventory_buffers),
                material_availability=deepcopy(selected.material_availability),
                wip_limits=deepcopy(selected.wip_limits),
            )
        )

        self._assert_stale(
            client=client, store=store, evaluation_id=evaluation_id
        )

    def test_explicit_snapshot_remains_selected_until_its_freshness_changes(self):
        client, store, fixture, clock, evaluation_id = self._fixture()
        selected = store.operational_state_snapshots[
            fixture["OperationalStateSnapshotID"]
        ]
        store.operational_state_snapshots["TST-MTO-OPS-LATEST"] = (
            OperationalStateSnapshot(
                snapshot_id="TST-MTO-OPS-LATEST",
                captured_at=selected.captured_at + timedelta(minutes=1),
                inventory_buffers=deepcopy(selected.inventory_buffers),
                material_availability=deepcopy(selected.material_availability),
                wip_limits=deepcopy(selected.wip_limits),
            )
        )
        self._assert_currently_eligible(
            client=client, store=store, evaluation_id=evaluation_id
        )

        clock[0] = selected.captured_at + timedelta(minutes=61)
        self._assert_stale(
            client=client, store=store, evaluation_id=evaluation_id
        )

    def test_fresh_to_stale_time_boundary_blocks_acceptance(self):
        client, store, fixture, clock, evaluation_id = self._fixture()
        selected = store.operational_state_snapshots[
            fixture["OperationalStateSnapshotID"]
        ]
        clock[0] = selected.captured_at + timedelta(minutes=60)
        self._assert_currently_eligible(
            client=client, store=store, evaluation_id=evaluation_id
        )

        clock[0] = selected.captured_at + timedelta(minutes=61)
        self._assert_stale(
            client=client, store=store, evaluation_id=evaluation_id
        )

    def test_time_advance_inside_selected_window_changes_current_capacity_facts(self):
        client, store, _, clock, evaluation_id = self._fixture()
        evaluation_id = self._rechecked_without_material(
            client=client, store=store, evaluation_id=evaluation_id
        )
        clock[0] = MTO_FIXTURE_TIME + timedelta(days=2, hours=1)

        self._assert_stale(
            client=client, store=store, evaluation_id=evaluation_id
        )

    def test_later_safe_window_and_promise_change_without_ledger_mutation_marks_stale(self):
        client, store, _, clock, evaluation_id = self._fixture()
        request = self._capacity_request(
            store.order_commitment_evaluations[evaluation_id]
        )
        store.ccr_capacity_reservations["CCR-TST-MTO-LATER"] = (
            self._capacity_reservation(
                request,
                "CCR-TST-MTO-LATER",
                ReservedMinutes=300.0,
            )
        )
        evaluation_id = self._rechecked_without_material(
            client=client, store=store, evaluation_id=evaluation_id
        )
        evaluation = store.order_commitment_evaluations[evaluation_id]
        assert evaluation["DecisionFacts"]["CapacityStatus"] == "LaterSafeDate"
        clock[0] = MTO_FIXTURE_TIME + timedelta(days=3, hours=1)

        self._assert_stale(
            client=client, store=store, evaluation_id=evaluation_id
        )

    def test_inbound_eligibility_cutoff_crossing_inside_fresh_snapshot_marks_stale(self):
        client, store, fixture, clock, evaluation_id = self._fixture()
        snapshot_id = fixture["OperationalStateSnapshotID"]
        selected = store.operational_state_snapshots[snapshot_id]
        availability = selected.material_availability[0]
        store.operational_state_snapshots[snapshot_id] = OperationalStateSnapshot(
            snapshot_id=snapshot_id,
            captured_at=selected.captured_at,
            inventory_buffers=deepcopy(selected.inventory_buffers),
            material_availability=[
                availability.__class__(
                    item_id=availability.item_id,
                    location_id=availability.location_id,
                    allocated_qty=availability.allocated_qty,
                    inbound_qty=5.0,
                    inbound_available_at=MTO_FIXTURE_TIME + timedelta(
                        days=1, minutes=10
                    ),
                )
            ],
            wip_limits=deepcopy(selected.wip_limits),
        )
        # Re-evaluate against the inbound cutoff without advancing freshness.
        source = store.order_commitment_evaluations[evaluation_id]
        reevaluation = client.post(
            f"/planner/workbench/order-commitments/{evaluation_id}/reevaluate",
            json={
                "RequestedBy": "planner-staleness",
                "OperationalStateSnapshotID": snapshot_id,
            },
            headers=_planner_headers(),
        )
        assert reevaluation.status_code == 200
        evaluation_id = reevaluation.json()["Data"]["Evaluation"]["EvaluationID"]
        assert source["EvaluationID"] != evaluation_id
        clock[0] = MTO_FIXTURE_TIME + timedelta(minutes=11)

        self._assert_stale(
            client=client, store=store, evaluation_id=evaluation_id
        )

    def test_unchanged_canonical_decision_facts_allow_acceptance_despite_later_observation(self):
        client, store, _, clock, evaluation_id = self._fixture()
        clock[0] = MTO_FIXTURE_TIME + timedelta(minutes=1)

        self._assert_currently_eligible(
            client=client, store=store, evaluation_id=evaluation_id
        )


class TestOrderCommitmentApiAcceptance:
    """BE-SDBR-006 through BE-SDBR-010: atomic Phase 0 acceptance."""

    @staticmethod
    def _open_evaluation(
        *,
        actor_id: str = "planner-task21",
    ) -> tuple[TestClient, WorkbenchStateStore, dict[str, object], str]:
        store, fixture = _order_commitment_store()
        client = TestClient(api.create_app(
            state_store=store,
            require_auth=True,
            utc_now=lambda: MTO_FIXTURE_TIME,
        ))
        intake = client.post(
            "/planner/workbench/order-commitments/intake",
            json=fixture["IntakePayloadTemplate"],
            headers={"X-Actor-ID": actor_id, "X-Actor-Role": "Planner"},
        )
        assert intake.status_code == 200
        return (
            client,
            store,
            fixture,
            intake.json()["Data"]["Evaluation"]["EvaluationID"],
        )

    @staticmethod
    def _headers(
        client: TestClient,
        *,
        actor_id: str = "planner-task21",
        actor_role: str = "Planner",
        revision: str | None = None,
    ) -> dict[str, str]:
        if revision is None:
            revision = client.get(
                "/planner/workbench/order-commitments/workbench",
                headers={
                    "X-Actor-ID": actor_id,
                    "X-Actor-Role": actor_role,
                },
            ).headers["X-Workbench-Revision"]
        return {
            "X-Actor-ID": actor_id,
            "X-Actor-Role": actor_role,
            "If-Match": revision,
        }

    @staticmethod
    def _acceptance_payload(
        evaluation: dict[str, object],
        *,
        decision_id: str = "DEC-TST-MTO-TASK21",
    ) -> dict[str, object]:
        return _decision_payload(
            evaluation,
            decision_id=decision_id,
            decision="AcceptRequestedDate",
            reason="Planner accepted the requested MTO commitment.",
            ccr_risk_acknowledged=True,
        )

    def _conditional_recommended_fixture(
        self,
    ) -> tuple[TestClient, WorkbenchStateStore, str, dict[str, object]]:
        client, store, _, source_id = self._open_evaluation()
        source = store.order_commitment_evaluations[source_id]
        request = deepcopy(
            source["DecisionFacts"]["CapacityReservationRequests"][0]
        )
        request.update({
            "CapacityReservationID": "CCR-TST-MTO-TASK21-EXISTING",
            "ReservationBatchID": "PRB-TST-MTO-TASK21-EXISTING",
            "DemandCommitmentID": "DC-TST-MTO-TASK21-EXISTING",
            "DemandClass": "MTO",
            "Status": "ActivePlanReservation",
            "RecordVersion": 1,
            "ReservedMinutes": 300.0,
        })
        store.ccr_capacity_reservations[
            "CCR-TST-MTO-TASK21-EXISTING"
        ] = request
        reevaluation = client.post(
            f"/planner/workbench/order-commitments/{source_id}/reevaluate",
            json={
                "RequestedBy": "planner-task21",
                "CheckMaterialAvailability": False,
                "MaterialCheckSkipReason": (
                    "Planner requested capacity-only conditional acceptance."
                ),
            },
            headers=_planner_headers(),
        )
        assert reevaluation.status_code == 200
        evaluation_id = reevaluation.json()["Data"]["Evaluation"]["EvaluationID"]
        evaluation = store.order_commitment_evaluations[evaluation_id]
        assert evaluation["Recommendation"]["AllowedActions"] == [
            "ConditionallyAcceptRecommendedDate",
            "Reevaluate",
            "Reject",
        ]
        payload = _decision_payload(
            evaluation,
            decision_id="DEC-TST-MTO-TASK21-CONDITIONAL",
            decision="ConditionallyAcceptRecommendedDate",
            reason="Planner accepted the later promise pending material confirmation.",
            ccr_risk_acknowledged=True,
            material_risk_acknowledged=True,
        )
        return client, store, evaluation_id, payload

    def _accepted_replay_fixture(
        self,
    ) -> tuple[TestClient, WorkbenchStateStore, str, dict[str, object]]:
        client, store, _, evaluation_id = self._open_evaluation()
        payload = self._acceptance_payload(
            store.order_commitment_evaluations[evaluation_id]
        )
        response = client.post(
            f"/planner/workbench/order-commitments/{evaluation_id}/decision",
            json=payload,
            headers=self._headers(client),
        )
        assert response.status_code == 200
        return client, store, evaluation_id, payload

    def _assert_replay_evidence_mismatch(
        self,
        *,
        client: TestClient,
        store: WorkbenchStateStore,
        evaluation_id: str,
        payload: dict[str, object],
    ) -> None:
        before = _public_store_snapshot(store)
        revision = store.revision

        response = client.post(
            f"/planner/workbench/order-commitments/{evaluation_id}/decision",
            json=payload,
            headers=self._headers(client),
        )

        assert response.status_code == 409
        assert response.json()["Data"]["Status"] == (
            "OrderCommitmentDecisionReplayEvidenceMismatch"
        )
        assert store.revision == revision
        assert _public_store_snapshot(store) == before

    @pytest.mark.parametrize(
        ("field", "drifted_value"),
        (
            ("DecisionID", "DEC-TST-MTO-DRIFTED"),
            ("DecisionFingerprint", "sha256:" + "0" * 64),
            ("Decision", "AcceptRecommendedDate"),
            ("DecidedBy", "planner-drifted"),
            ("DecidedAt", "2026-07-12T09:00:00+00:00"),
            ("Reason", "A different persisted acceptance reason."),
            ("CcrRiskAcknowledged", False),
            ("MaterialRiskAcknowledged", True),
            ("AcceptedPromiseAt", "2026-07-19T08:00:00+00:00"),
            ("DemandCommitmentID", "DC-TST-MTO-DRIFTED"),
            ("ReservationBatchID", "PRB-TST-MTO-DRIFTED"),
            ("ExternalOrderAcceptance", "Performed"),
            ("PlanningRunCreation", "Performed"),
            ("ProductionMutation", "Performed"),
        ),
    )
    def test_accepted_replay_rejects_each_drifted_persisted_decision_field(
        self,
        field: str,
        drifted_value: object,
    ):
        client, store, evaluation_id, payload = self._accepted_replay_fixture()
        store.order_commitment_evaluations[evaluation_id]["Decision"][field] = (
            drifted_value
        )

        self._assert_replay_evidence_mismatch(
            client=client,
            store=store,
            evaluation_id=evaluation_id,
            payload=payload,
        )

    @pytest.mark.parametrize(
        ("field", "drifted_value"),
        (
            ("EventID", "OCEV-TST-MTO-DRIFTED"),
            ("EventType", "OrderCommitmentRejected"),
            ("EvaluationID", "OCE-TST-MTO-DRIFTED"),
            ("OccurredAt", "2026-07-12T09:00:00+00:00"),
            ("ActorID", "planner-drifted"),
            ("TraceID", "TRACE-TST-MTO-DRIFTED"),
            ("CausationID", "DEC-TST-MTO-DRIFTED"),
            ("CorrelationID", "MTO-TST-DRIFTED"),
            ("DecisionID", "DEC-TST-MTO-DRIFTED"),
            ("ReservationBatchID", "PRB-TST-MTO-DRIFTED"),
        ),
    )
    def test_accepted_replay_rejects_each_drifted_mto_event_field(
        self,
        field: str,
        drifted_value: object,
    ):
        client, store, evaluation_id, payload = self._accepted_replay_fixture()
        event = next(
            row
            for row in store.order_commitment_events
            if row["EventType"] == "OrderCommitmentAccepted"
        )
        event[field] = drifted_value

        self._assert_replay_evidence_mismatch(
            client=client,
            store=store,
            evaluation_id=evaluation_id,
            payload=payload,
        )

    @pytest.mark.parametrize(
        ("field", "drifted_value"),
        (
            ("FromStatus", "Superseded"),
            ("ToStatus", "Rejected"),
            ("DecisionCode", "AcceptRecommendedDate"),
            ("AcceptedPromiseAt", "2026-07-19T08:00:00+00:00"),
            ("CcrRiskAcknowledged", False),
            ("MaterialRiskAcknowledged", True),
        ),
    )
    def test_accepted_replay_rejects_each_drifted_mto_event_detail(
        self,
        field: str,
        drifted_value: object,
    ):
        client, store, evaluation_id, payload = self._accepted_replay_fixture()
        event = next(
            row
            for row in store.order_commitment_events
            if row["EventType"] == "OrderCommitmentAccepted"
        )
        event["Details"][field] = drifted_value

        self._assert_replay_evidence_mismatch(
            client=client,
            store=store,
            evaluation_id=evaluation_id,
            payload=payload,
        )

    @pytest.mark.parametrize("event_mutation", ("missing", "duplicate"))
    def test_accepted_replay_requires_one_unique_canonical_mto_event(
        self,
        event_mutation: str,
    ):
        client, store, evaluation_id, payload = self._accepted_replay_fixture()
        event_index = next(
            index
            for index, row in enumerate(store.order_commitment_events)
            if row["EventType"] == "OrderCommitmentAccepted"
        )
        if event_mutation == "missing":
            store.order_commitment_events.pop(event_index)
        else:
            store.order_commitment_events.append(
                deepcopy(store.order_commitment_events[event_index])
            )

        self._assert_replay_evidence_mismatch(
            client=client,
            store=store,
            evaluation_id=evaluation_id,
            payload=payload,
        )

    @pytest.mark.parametrize(
        ("collection_name", "identity_field", "orphan_id"),
        (
            (
                "ccr_capacity_reservations",
                "CapacityReservationID",
                "CCR-TST-MTO-ORPHAN",
            ),
            (
                "material_planning_allocations",
                "MaterialAllocationID",
                "MAT-TST-MTO-ORPHAN",
            ),
        ),
    )
    def test_accepted_replay_rejects_orphan_phase0_child(
        self,
        collection_name: str,
        identity_field: str,
        orphan_id: str,
    ):
        client, store, evaluation_id, payload = self._accepted_replay_fixture()
        collection = getattr(store, collection_name)
        orphan = deepcopy(next(iter(collection.values())))
        orphan[identity_field] = orphan_id
        collection[orphan_id] = orphan

        self._assert_replay_evidence_mismatch(
            client=client,
            store=store,
            evaluation_id=evaluation_id,
            payload=payload,
        )

    @pytest.mark.parametrize(
        "mutation",
        (
            "missing_key",
            "invalid_timestamp",
            "naive_timestamp",
            "non_string_identity",
            "invalid_acknowledgement_type",
        ),
    )
    def test_accepted_replay_maps_malformed_persisted_decision_to_domain_conflict(
        self,
        mutation: str,
    ):
        client, store, evaluation_id, payload = self._accepted_replay_fixture()
        decision = store.order_commitment_evaluations[evaluation_id]["Decision"]
        if mutation == "missing_key":
            decision.pop("Reason")
        elif mutation == "invalid_timestamp":
            decision["DecidedAt"] = "not-a-timestamp"
        elif mutation == "naive_timestamp":
            decision["DecidedAt"] = "2026-07-12T08:00:00"
        elif mutation == "non_string_identity":
            decision["DecisionID"] = 42
        else:
            decision["CcrRiskAcknowledged"] = "true"

        self._assert_replay_evidence_mismatch(
            client=client,
            store=store,
            evaluation_id=evaluation_id,
            payload=payload,
        )

    def test_acceptance_atomically_creates_only_mto_phase0_rows(self):
        client, store, _, evaluation_id = self._open_evaluation()
        evaluation = store.order_commitment_evaluations[evaluation_id]
        before = _public_store_snapshot(store)

        response = client.post(
            f"/planner/workbench/order-commitments/{evaluation_id}/decision",
            json=self._acceptance_payload(evaluation),
            headers=self._headers(client),
        )

        assert response.status_code == 200
        _assert_only_operation_fields_changed(
            before=before,
            after=_public_store_snapshot(store),
            operation="accept",
        )
        data = response.json()["Data"]
        assert len(store.planning_demand_commitments) == 1
        assert len(store.planning_reservation_batches) == 1
        assert len(store.ccr_capacity_reservations) == 1
        assert len(store.material_planning_allocations) == 1
        assert len(store.planning_reservation_events) == 1
        assert len(store.processed_planning_event_keys) == 1
        assert data["DemandCommitmentID"] in store.planning_demand_commitments
        assert data["ReservationBatchID"] in store.planning_reservation_batches
        assert data["CapacityReservationIDs"] == list(
            store.ccr_capacity_reservations
        )
        assert data["MaterialAllocationIDs"] == list(
            store.material_planning_allocations
        )

    def test_conditional_recommended_date_creates_pending_material_and_zero_allocations(self):
        client, store, evaluation_id, payload = (
            self._conditional_recommended_fixture()
        )
        evaluation = store.order_commitment_evaluations[evaluation_id]

        response = client.post(
            f"/planner/workbench/order-commitments/{evaluation_id}/decision",
            json=payload,
            headers=self._headers(client),
        )

        assert response.status_code == 200
        data = response.json()["Data"]
        demand = store.planning_demand_commitments[data["DemandCommitmentID"]]
        assert demand["AcceptedPromiseAt"] == evaluation["ShadowSchedule"][
            "EarliestSafeAssessment"
        ]["PromiseAt"]
        assert demand["MaterialCommitmentStatus"] == "PendingConfirmation"
        assert demand["PendingMaterialRequirements"] == evaluation[
            "MaterialAssessment"
        ]["PendingRequirements"]
        assert data["MaterialAllocationIDs"] == []
        assert store.material_planning_allocations == {}

    def test_decision_record_phase0_event_and_mto_event_share_server_actor_and_time(self):
        client, store, _, evaluation_id = self._open_evaluation()
        evaluation = store.order_commitment_evaluations[evaluation_id]

        response = client.post(
            f"/planner/workbench/order-commitments/{evaluation_id}/decision",
            json=self._acceptance_payload(evaluation),
            headers=self._headers(client),
        )

        assert response.status_code == 200
        decision = store.order_commitment_evaluations[evaluation_id]["Decision"]
        batch = next(iter(store.planning_reservation_batches.values()))
        phase0_event = store.planning_reservation_events[-1]
        mto_event = store.order_commitment_events[-1]
        assert (
            decision["DecidedBy"]
            == batch["ConfirmedBy"]
            == phase0_event["ActorID"]
            == mto_event["ActorID"]
            == "planner-task21"
        )
        assert (
            decision["DecidedAt"]
            == batch["ConfirmedAt"]
            == phase0_event["OccurredAt"]
            == mto_event["OccurredAt"]
            == MTO_FIXTURE_TIME.isoformat()
        )

    def test_acceptance_response_is_accepted_pending_formal_schedule_and_not_performed_boundaries(self):
        client, store, _, evaluation_id = self._open_evaluation()
        payload = self._acceptance_payload(
            store.order_commitment_evaluations[evaluation_id]
        )

        first = client.post(
            f"/planner/workbench/order-commitments/{evaluation_id}/decision",
            json=payload,
            headers=self._headers(client),
        )
        after_first = _public_store_snapshot(store)
        first_revision = first.headers["X-Workbench-Revision"]
        replay = client.post(
            f"/planner/workbench/order-commitments/{evaluation_id}/decision",
            json=payload,
            headers=self._headers(client),
        )

        assert first.status_code == replay.status_code == 200
        data = first.json()["Data"]
        assert data["Status"] == "AcceptedPendingFormalSchedule"
        assert data["Evaluation"]["Status"] == "AcceptedPendingFormalSchedule"
        assert data["ExternalOrderAcceptance"] == "NotPerformed"
        assert data["PlanningRunCreation"] == "NotPerformed"
        assert data["ProductionMutation"] == "NotPerformed"
        assert replay.json()["Data"] == data
        assert replay.headers["X-Workbench-Revision"] == first_revision
        assert _public_store_snapshot(store) == after_first

    def test_acceptance_creates_no_planning_run_and_does_not_change_existing_publication(self):
        client, store, fixture, evaluation_id = self._open_evaluation()
        before_runs = deepcopy(store.planning_runs)
        before_publication = deepcopy(
            store.planning_runs[fixture["BaselinePlanningRunID"]][
                "PublicationHistory"
            ]
        )

        response = client.post(
            f"/planner/workbench/order-commitments/{evaluation_id}/decision",
            json=self._acceptance_payload(
                store.order_commitment_evaluations[evaluation_id]
            ),
            headers=self._headers(client),
        )

        assert response.status_code == 200
        assert store.planning_runs == before_runs
        assert store.planning_runs[fixture["BaselinePlanningRunID"]][
            "PublicationHistory"
        ] == before_publication

    def test_intake_reevaluation_rejection_and_acceptance_deep_preserve_authority_state(self):
        store, fixture = _order_commitment_store()
        client = TestClient(api.create_app(
            state_store=store,
            require_auth=True,
            utc_now=lambda: MTO_FIXTURE_TIME,
        ))
        before = _public_store_snapshot(store)
        intake = client.post(
            "/planner/workbench/order-commitments/intake",
            json=fixture["IntakePayloadTemplate"],
            headers=_planner_headers(),
        )
        assert intake.status_code == 200
        _assert_only_operation_fields_changed(
            before=before,
            after=_public_store_snapshot(store),
            operation="intake",
        )

        evaluation_id = intake.json()["Data"]["Evaluation"]["EvaluationID"]
        before = _public_store_snapshot(store)
        reevaluation = client.post(
            f"/planner/workbench/order-commitments/{evaluation_id}/reevaluate",
            json={"RequestedBy": "planner-task21"},
            headers=_planner_headers(),
        )
        assert reevaluation.status_code == 200
        _assert_only_operation_fields_changed(
            before=before,
            after=_public_store_snapshot(store),
            operation="reevaluate",
        )

        reject_client, reject_store, _, reject_id = self._open_evaluation()
        before = _public_store_snapshot(reject_store)
        rejection = reject_client.post(
            f"/planner/workbench/order-commitments/{reject_id}/decision",
            json=_decision_payload(
                reject_store.order_commitment_evaluations[reject_id]
            ),
            headers=self._headers(reject_client),
        )
        assert rejection.status_code == 200
        _assert_only_operation_fields_changed(
            before=before,
            after=_public_store_snapshot(reject_store),
            operation="reject",
        )

        accept_client, accept_store, _, accept_id = self._open_evaluation()
        before = _public_store_snapshot(accept_store)
        acceptance = accept_client.post(
            f"/planner/workbench/order-commitments/{accept_id}/decision",
            json=self._acceptance_payload(
                accept_store.order_commitment_evaluations[accept_id]
            ),
            headers=self._headers(accept_client),
        )
        assert acceptance.status_code == 200
        _assert_only_operation_fields_changed(
            before=before,
            after=_public_store_snapshot(accept_store),
            operation="accept",
        )

    def test_two_clients_one_revision_yield_one_success_one_revision_conflict(self):
        store, fixture = _order_commitment_store()
        app = api.create_app(
            state_store=store,
            require_auth=True,
            utc_now=lambda: MTO_FIXTURE_TIME,
        )
        with TestClient(app) as first_client, TestClient(app) as second_client:
            intake = first_client.post(
                "/planner/workbench/order-commitments/intake",
                json=fixture["IntakePayloadTemplate"],
                headers=_planner_headers(),
            )
            evaluation_id = intake.json()["Data"]["Evaluation"]["EvaluationID"]
            payload = self._acceptance_payload(
                store.order_commitment_evaluations[evaluation_id]
            )
            revision = first_client.get(
                "/planner/workbench/order-commitments/workbench",
                headers=_planner_headers(),
            ).headers["X-Workbench-Revision"]
            headers = self._headers(first_client, revision=revision)

            with ThreadPoolExecutor(max_workers=2) as executor:
                responses = list(executor.map(
                    lambda client: client.post(
                        f"/planner/workbench/order-commitments/{evaluation_id}/decision",
                        json=payload,
                        headers=headers,
                    ),
                    (first_client, second_client),
                ))

        assert sorted(response.status_code for response in responses) == [200, 409]
        conflict = next(response for response in responses if response.status_code == 409)
        assert conflict.json()["Data"]["Status"] == "StateStoreRevisionConflict"
        assert store.revision == int(revision) + 1
        assert store.order_commitment_evaluations[evaluation_id]["Status"] == (
            "AcceptedPendingFormalSchedule"
        )
        assert len(store.planning_reservation_batches) == 1
        assert sum(
            event["EventType"] == "OrderCommitmentAccepted"
            for event in store.order_commitment_events
        ) == 1

    def test_forced_save_failure_restores_all_mto_phase0_event_key_and_revision_state(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ):
        client, store, _, evaluation_id = self._open_evaluation()
        before = _public_store_snapshot(store)

        def fail_save(_store: WorkbenchStateStore):
            raise RuntimeError("forced Task 21 save failure")

        monkeypatch.setattr(WorkbenchStateStore, "save", fail_save)

        with pytest.raises(RuntimeError, match="forced Task 21 save failure"):
            client.post(
                f"/planner/workbench/order-commitments/{evaluation_id}/decision",
                json=self._acceptance_payload(
                    store.order_commitment_evaluations[evaluation_id]
                ),
                headers=self._headers(client),
            )

        assert _public_store_snapshot(store) == before

    def test_phase0_shared_read_row_exposes_only_evaluation_promise_and_material_status(self):
        client, store, _, evaluation_id = self._open_evaluation()
        acceptance = client.post(
            f"/planner/workbench/order-commitments/{evaluation_id}/decision",
            json=self._acceptance_payload(
                store.order_commitment_evaluations[evaluation_id]
            ),
            headers=self._headers(client),
        )
        assert acceptance.status_code == 200

        response = client.get(
            "/planner/workbench/planning-reservations/workbench",
            headers=_planner_headers(),
        )

        assert response.status_code == 200
        row = response.json()["Data"]["Rows"][0]
        demand = next(iter(store.planning_demand_commitments.values()))
        shared_base_fields = {
            "ReservationBatchID",
            "DemandCommitmentID",
            "DemandClass",
            "Status",
            "ConfirmationID",
            "ConfirmedBy",
            "ConfirmedAt",
            "CapacityReservationIDs",
            "MaterialAllocationIDs",
            "PlanningRunID",
            "LastTransitionAt",
            "EventType",
            "DemandSourceType",
        }
        mto_context_fields = {
            "OrderCommitmentEvaluationID",
            "AcceptedPromiseAt",
            "MaterialCommitmentStatus",
        }
        assert set(row) - shared_base_fields == mto_context_fields
        assert row["OrderCommitmentEvaluationID"] == evaluation_id
        assert row["AcceptedPromiseAt"] == demand["AcceptedPromiseAt"]
        assert row["MaterialCommitmentStatus"] == "PlannedAllocationPrepared"
        assert not {
            "PendingMaterialRequirements",
            "Order",
            "Basis",
            "DecisionFacts",
            "EvaluationFingerprint",
        } & set(row)

    def test_viewer_worker_forbidden_and_planner_admin_allowed_to_accept(self):
        for role in ("Viewer", "Worker"):
            client, store, _, evaluation_id = self._open_evaluation()
            before = _public_store_snapshot(store)
            response = client.post(
                f"/planner/workbench/order-commitments/{evaluation_id}/decision",
                json=self._acceptance_payload(
                    store.order_commitment_evaluations[evaluation_id]
                ),
                headers=self._headers(
                    client,
                    actor_id=f"task21-{role.lower()}",
                    actor_role=role,
                ),
            )
            assert response.status_code == 403
            assert _public_store_snapshot(store) == before

        for role in ("Planner", "Admin"):
            client, store, _, evaluation_id = self._open_evaluation()
            actor_id = f"task21-{role.lower()}"
            response = client.post(
                f"/planner/workbench/order-commitments/{evaluation_id}/decision",
                json=self._acceptance_payload(
                    store.order_commitment_evaluations[evaluation_id]
                ),
                headers=self._headers(
                    client,
                    actor_id=actor_id,
                    actor_role=role,
                ),
            )
            assert response.status_code == 200
            assert store.order_commitment_evaluations[evaluation_id]["Decision"][
                "DecidedBy"
            ] == actor_id
