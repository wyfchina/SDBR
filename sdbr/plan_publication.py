from __future__ import annotations

from datetime import datetime
from hashlib import sha256
import json


TERMINAL_PUBLICATION_STATES = {"Superseded", "PublicationRevoked"}


def build_plan_publication_view(
    *,
    planning_run: dict[str, object],
    superseded_by_run_id: str | None = None,
) -> dict[str, object]:
    state = publication_state(planning_run)
    return {
        "RunID": planning_run.get("RunID"),
        "ProblemID": planning_run.get("ProblemID"),
        "PublicationStatus": state,
        "AllowedActions": allowed_publication_actions(planning_run),
        "ScheduleFingerprint": schedule_fingerprint(planning_run),
        "PublicationPackage": planning_run.get("PublicationPackage"),
        "PublicationHistory": planning_run.get("PublicationHistory", []),
        "SupersedesRunID": planning_run.get("SupersedesRunID"),
        "SupersededByRunID": planning_run.get("SupersededByRunID")
        or superseded_by_run_id,
    }


def publication_state(planning_run: dict[str, object]) -> str:
    explicit_state = planning_run.get("PublicationStatus")
    if isinstance(explicit_state, str):
        return explicit_state
    if planning_run.get("Status") == "Completed" and isinstance(
        planning_run.get("Schedule"), dict
    ):
        return "Draft"
    return "Unavailable"


def allowed_publication_actions(planning_run: dict[str, object]) -> list[str]:
    if planning_run.get("Status") != "Completed" or not isinstance(
        planning_run.get("Schedule"), dict
    ):
        return []
    state = publication_state(planning_run)
    return {
        "Draft": ["Review"],
        "Reviewed": ["Approve"],
        "Approved": ["Publish"],
        "Published": ["Revoke"],
    }.get(state, [])


def schedule_fingerprint(planning_run: dict[str, object]) -> str | None:
    schedule = planning_run.get("Schedule")
    if not isinstance(schedule, dict):
        return None
    payload = json.dumps(
        schedule,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    )
    return sha256(payload.encode("utf-8")).hexdigest()


def transition_publication_state(
    *,
    planning_run: dict[str, object],
    action: str,
    actor_id: str,
    occurred_at: datetime,
    comment: str | None = None,
    target_systems: list[str] | None = None,
) -> dict[str, object]:
    current_state = publication_state(planning_run)
    next_state_by_action = {
        "Review": ("Draft", "Reviewed"),
        "Approve": ("Reviewed", "Approved"),
        "Publish": ("Approved", "Published"),
        "Revoke": ("Published", "PublicationRevoked"),
    }
    if action not in next_state_by_action:
        raise ValueError(f"Unsupported publication action: {action}.")
    expected_state, next_state = next_state_by_action[action]
    if current_state != expected_state:
        raise ValueError(
            f"Publication action {action} requires {expected_state}; "
            f"current state is {current_state}."
        )

    updated = dict(planning_run)
    updated["PublicationStatus"] = next_state
    event = {
        "Action": action,
        "FromStatus": current_state,
        "ToStatus": next_state,
        "ActorID": actor_id,
        "OccurredAt": occurred_at.isoformat(),
        "Comment": comment,
    }
    history = list(updated.get("PublicationHistory", []))
    history.append(event)
    updated["PublicationHistory"] = history
    if next_state == "Published":
        updated["PublicationPackage"] = build_publication_package(
            planning_run=updated,
            published_by=actor_id,
            published_at=occurred_at,
            target_systems=target_systems or ["InternalPlanning"],
        )
    if next_state == "PublicationRevoked":
        package = updated.get("PublicationPackage")
        if isinstance(package, dict):
            updated["PublicationPackage"] = {
                **package,
                "RevokedBy": actor_id,
                "RevokedAt": occurred_at.isoformat(),
                "RevocationComment": comment,
            }
    return updated


def mark_superseded(
    *,
    planning_run: dict[str, object],
    superseded_by_run_id: str,
    actor_id: str,
    occurred_at: datetime,
) -> dict[str, object]:
    updated = dict(planning_run)
    updated["PublicationStatus"] = "Superseded"
    updated["SupersededByRunID"] = superseded_by_run_id
    history = list(updated.get("PublicationHistory", []))
    history.append(
        {
            "Action": "Supersede",
            "FromStatus": "Published",
            "ToStatus": "Superseded",
            "ActorID": actor_id,
            "OccurredAt": occurred_at.isoformat(),
            "Comment": f"Superseded by planning run {superseded_by_run_id}.",
        }
    )
    updated["PublicationHistory"] = history
    return updated


def build_publication_package(
    *,
    planning_run: dict[str, object],
    published_by: str,
    published_at: datetime,
    target_systems: list[str],
) -> dict[str, object]:
    schedule = planning_run.get("Schedule")
    schedule_dict = schedule if isinstance(schedule, dict) else {}
    fingerprint = schedule_fingerprint(planning_run) or ""
    return {
        "PackageID": f"PUB-{planning_run.get('RunID')}-{fingerprint[:12]}",
        "RunID": planning_run.get("RunID"),
        "ProblemID": planning_run.get("ProblemID"),
        "MasterDataVersionID": planning_run.get("MasterDataVersionID"),
        "OperationalStateSnapshotID": planning_run.get(
            "OperationalStateSnapshotID"
        ),
        "ScheduleFingerprint": fingerprint,
        "PublishedBy": published_by,
        "PublishedAt": published_at.isoformat(),
        "TargetSystems": target_systems,
        "Summary": {
            "OrderCount": schedule_dict.get("OrderCount"),
            "SolverStatus": planning_run.get("SolverStatus"),
            "SolverBackendID": planning_run.get("SolverBackendID"),
            "GeneratedAt": schedule_dict.get("GeneratedAt")
            or planning_run.get("CompletedAt"),
        },
    }
