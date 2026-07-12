"""BE-SDBR-010: MTO API payload and authorization contracts."""

from copy import deepcopy
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
from sdbr.order_commitment_evaluation import normalize_mto_order
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
