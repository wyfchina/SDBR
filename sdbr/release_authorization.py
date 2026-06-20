from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256

from sdbr.release_stability import (
    ReleaseStabilityInput,
    ReleaseStabilityPolicy,
    evaluate_release_stability,
)


@dataclass(frozen=True, slots=True)
class ReleaseAuthorization:
    authorization_id: str
    request_id: str
    order_id: str
    released_by: str
    released_at: datetime
    scheduled_start: str | None
    scheduled_end: str | None
    suggested_release_at: str | None
    status: str
    operational_state_snapshot_id: str | None = None
    operational_state_captured_at: str | None = None
    decision_package_id: str | None = None


def create_release_authorization(
    *,
    request_id: str,
    candidate: dict[str, object],
    released_by: str,
    released_at: datetime,
    operational_state_snapshot_id: str | None = None,
    operational_state_captured_at: datetime | None = None,
    decision_package_id: str | None = None,
) -> ReleaseAuthorization:
    if candidate.get("RecommendedAction") != "ReadyForRelease":
        raise ValueError("Only ReadyForRelease candidates can be authorized")
    order_id = str(candidate["OrderID"])
    identity = "|".join((request_id, order_id, released_at.isoformat()))
    return ReleaseAuthorization(
        authorization_id=f"REL-{sha256(identity.encode('utf-8')).hexdigest()[:16]}",
        request_id=request_id,
        order_id=order_id,
        released_by=released_by,
        released_at=released_at,
        scheduled_start=_optional_str(candidate.get("ScheduledStart")),
        scheduled_end=_optional_str(candidate.get("ScheduledEnd")),
        suggested_release_at=_optional_str(candidate.get("SuggestedReleaseAt")),
        status="Authorized",
        operational_state_snapshot_id=operational_state_snapshot_id,
        operational_state_captured_at=(
            operational_state_captured_at.isoformat()
            if operational_state_captured_at is not None
            else None
        ),
        decision_package_id=decision_package_id,
    )


def build_dispatch_package(
    authorization: ReleaseAuthorization,
) -> dict[str, object]:
    package = {
        "AuthorizationID": authorization.authorization_id,
        "RequestID": authorization.request_id,
        "OrderID": authorization.order_id,
        "DispatchStatus": "ReadyToIssue",
        "ReleasedBy": authorization.released_by,
        "ReleasedAt": authorization.released_at.isoformat(),
        "ScheduledStart": authorization.scheduled_start,
        "ScheduledEnd": authorization.scheduled_end,
        "SuggestedReleaseAt": authorization.suggested_release_at,
    }
    if authorization.operational_state_snapshot_id is not None:
        package["OperationalStateSnapshotID"] = (
            authorization.operational_state_snapshot_id
        )
        package["OperationalStateCapturedAt"] = (
            authorization.operational_state_captured_at
        )
    if authorization.decision_package_id is not None:
        package["DecisionPackageID"] = authorization.decision_package_id
    return package


def build_release_stability_report(
    authorizations: list[ReleaseAuthorization],
    policy: ReleaseStabilityPolicy | None = None,
) -> list[dict[str, object]]:
    rows = []
    for authorization in authorizations:
        if authorization.suggested_release_at is None:
            rows.append(
                {
                    "AuthorizationID": authorization.authorization_id,
                    "RequestID": authorization.request_id,
                    "OrderID": authorization.order_id,
                    "SuggestedReleaseAt": None,
                    "ReleasedAt": authorization.released_at.isoformat(),
                    "DeviationMinutes": None,
                    "AbsoluteDeviationMinutes": None,
                    "TimingStatus": "Unknown",
                    "Severity": "Warning",
                    "Action": "Review",
                    "ReplanRequired": False,
                    "ReasonCode": "MissingSuggestedReleaseAt",
                }
            )
            continue
        suggested_release_at = datetime.fromisoformat(authorization.suggested_release_at)
        result = evaluate_release_stability(
            ReleaseStabilityInput(
                order_id=authorization.order_id,
                planned_release_at=suggested_release_at,
                evaluated_release_at=authorization.released_at,
                gate_allowed=True,
            ),
            policy=policy,
        )
        rows.append(
            {
                "AuthorizationID": authorization.authorization_id,
                "RequestID": authorization.request_id,
                "OrderID": authorization.order_id,
                "SuggestedReleaseAt": authorization.suggested_release_at,
                "ReleasedAt": authorization.released_at.isoformat(),
                "DeviationMinutes": result.deviation_minutes,
                "AbsoluteDeviationMinutes": result.absolute_deviation_minutes,
                "TimingStatus": result.timing_status,
                "Severity": result.severity,
                "Action": result.action,
                "ReplanRequired": result.replan_required,
                "ReasonCode": result.reason_code,
            }
        )
    return sorted(
        rows,
        key=lambda item: (
            _release_stability_action_rank(str(item["Action"])),
            -int(item["AbsoluteDeviationMinutes"] or 0),
            str(item["AuthorizationID"]),
        ),
    )


def _optional_str(value: object) -> str | None:
    if value is None:
        return None
    return str(value)


def _release_stability_action_rank(action: str) -> int:
    return {
        "Replan": 0,
        "Review": 1,
        "Monitor": 2,
    }.get(action, 3)
