"""BE-SDBR-010: MTO API payload and authorization contracts."""

from copy import deepcopy
from datetime import datetime, timezone

import pytest
from fastapi import Request
from fastapi.testclient import TestClient
from pydantic import ValidationError

from sdbr import api
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
