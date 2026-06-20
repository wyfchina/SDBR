from __future__ import annotations

from datetime import datetime
from typing import Iterable

from sdbr.operational_state import (
    OperationalStateSnapshot,
    evaluate_operational_state_freshness,
)


def build_data_readiness(
    *,
    master_data_versions: Iterable[dict[str, object]],
    operational_state_snapshots: Iterable[OperationalStateSnapshot],
    evaluated_at: datetime,
    max_snapshot_age_minutes: int,
) -> dict[str, object]:
    latest_version = _latest_master_data_version(master_data_versions)
    latest_snapshot = _latest_operational_snapshot(operational_state_snapshots)
    issues: list[dict[str, object]] = []

    version_summary = None
    master_data_ready = False
    if latest_version is None:
        issues.append(
            _issue(
                severity="Error",
                code="MASTER_DATA_VERSION_MISSING",
                message="No master data version is available.",
                entity_type="MasterDataVersion",
            )
        )
    else:
        version_summary = _master_data_summary(latest_version)
        master_data_ready = latest_version.get("Status") == "Valid"
        for validation_issue in latest_version.get("Validation", {}).get("Issues", []):
            issues.append(
                {
                    "Severity": validation_issue.get("Severity", "Error"),
                    "Code": validation_issue.get("Code", "MASTER_DATA_INVALID"),
                    "Message": validation_issue.get("Message", "Master data is invalid."),
                    "EntityType": "MasterDataVersion",
                    "EntityID": latest_version.get("VersionID"),
                    "Field": validation_issue.get("Field"),
                }
            )

    snapshot_summary = None
    operational_state_ready = False
    if latest_snapshot is None:
        issues.append(
            _issue(
                severity="Error",
                code="OPERATIONAL_STATE_SNAPSHOT_MISSING",
                message="No operational state snapshot is available.",
                entity_type="OperationalStateSnapshot",
            )
        )
    else:
        freshness = evaluate_operational_state_freshness(
            snapshot=latest_snapshot,
            evaluated_at=evaluated_at,
            max_age_minutes=max_snapshot_age_minutes,
        )
        operational_state_ready = freshness.acceptable
        snapshot_summary = {
            "SnapshotID": latest_snapshot.snapshot_id,
            "CapturedAt": latest_snapshot.captured_at.isoformat(),
            "SourceSystem": None,
            "CreatedBy": None,
            "Freshness": {
                "Status": freshness.status,
                "AgeMinutes": round(freshness.age_minutes, 2),
                "MaxAgeMinutes": freshness.max_age_minutes,
                "Acceptable": freshness.acceptable,
            },
            "Summary": {
                "InventoryBufferCount": len(latest_snapshot.inventory_buffers),
                "MaterialAvailabilityCount": len(latest_snapshot.material_availability),
                "InboundItemCount": sum(
                    1
                    for item in latest_snapshot.material_availability
                    if item.inbound_qty > 0
                ),
                "WipScopeCount": len(latest_snapshot.wip_limits),
                "ResourceStatusCount": None,
            },
        }
        if freshness.status == "Stale":
            issues.append(
                _issue(
                    severity="Error",
                    code="OPERATIONAL_STATE_SNAPSHOT_STALE",
                    message="The latest operational state snapshot is stale.",
                    entity_type="OperationalStateSnapshot",
                    entity_id=latest_snapshot.snapshot_id,
                )
            )
        elif freshness.status == "Future":
            issues.append(
                _issue(
                    severity="Error",
                    code="OPERATIONAL_STATE_SNAPSHOT_IN_FUTURE",
                    message="The latest operational state snapshot is dated in the future.",
                    entity_type="OperationalStateSnapshot",
                    entity_id=latest_snapshot.snapshot_id,
                )
            )
        issues.extend(
            [
                _issue(
                    severity="Warning",
                    code="OPERATIONAL_SOURCE_NOT_PROVIDED",
                    message="The operational state source system was not provided.",
                    entity_type="OperationalStateSnapshot",
                    entity_id=latest_snapshot.snapshot_id,
                ),
                _issue(
                    severity="Warning",
                    code="RESOURCE_STATUS_NOT_CAPTURED",
                    message="Resource runtime status is not captured in the current snapshot contract.",
                    entity_type="OperationalStateSnapshot",
                    entity_id=latest_snapshot.snapshot_id,
                ),
            ]
        )

    can_create_run = master_data_ready and operational_state_ready
    if latest_version is None and latest_snapshot is None:
        overall_status = "Empty"
    elif not can_create_run:
        overall_status = "Blocked"
    elif issues:
        overall_status = "ReadyWithWarnings"
    else:
        overall_status = "Ready"

    return {
        "EvaluatedAt": evaluated_at.isoformat(),
        "OverallStatus": overall_status,
        "CanCreatePlanningRun": can_create_run,
        "LatestMasterDataVersion": version_summary,
        "LatestOperationalStateSnapshot": snapshot_summary,
        "Issues": issues,
        "Selection": {
            "MasterDataVersionID": (
                latest_version.get("VersionID") if master_data_ready else None
            ),
            "OperationalStateSnapshotID": (
                latest_snapshot.snapshot_id if operational_state_ready else None
            ),
        },
    }


def _latest_master_data_version(
    versions: Iterable[dict[str, object]],
) -> dict[str, object] | None:
    candidates = list(versions)
    if not candidates:
        return None
    return max(
        candidates,
        key=lambda item: (
            _parse_datetime(str(item.get("CapturedAt", ""))),
            str(item.get("VersionID", "")),
        ),
    )


def _latest_operational_snapshot(
    snapshots: Iterable[OperationalStateSnapshot],
) -> OperationalStateSnapshot | None:
    candidates = list(snapshots)
    if not candidates:
        return None
    return max(candidates, key=lambda item: (item.captured_at, item.snapshot_id))


def _master_data_summary(version: dict[str, object]) -> dict[str, object]:
    validation = version.get("Validation", {})
    return {
        "VersionID": version.get("VersionID"),
        "CapturedAt": version.get("CapturedAt"),
        "SourceSystem": version.get("SourceSystem"),
        "CreatedBy": version.get("CreatedBy"),
        "Status": version.get("Status"),
        "Summary": validation.get("Summary", {}),
    }


def _issue(
    *,
    severity: str,
    code: str,
    message: str,
    entity_type: str,
    entity_id: str | None = None,
) -> dict[str, object]:
    return {
        "Severity": severity,
        "Code": code,
        "Message": message,
        "EntityType": entity_type,
        "EntityID": entity_id,
        "Field": None,
    }


def _parse_datetime(value: str) -> datetime:
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return datetime.min
