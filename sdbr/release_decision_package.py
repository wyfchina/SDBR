from __future__ import annotations

from hashlib import sha256
import json


def build_release_decision_package(
    *,
    request_id: str,
    problem_id: str,
    solver_backend_id: str,
    solver_status: str | None,
    schedule: dict[str, object],
    operational_state_snapshot_id: str,
    operational_state_captured_at: str,
    evaluated_at: str,
    material_requirements: list[dict[str, object]],
    candidates: list[dict[str, object]],
) -> dict[str, object]:
    schedule_snapshot_id = _content_id("SCH", schedule)
    decision_basis = {
        "RequestID": request_id,
        "ScheduleSnapshotID": schedule_snapshot_id,
        "OperationalStateSnapshotID": operational_state_snapshot_id,
        "EvaluatedAt": evaluated_at,
        "MaterialRequirements": material_requirements,
        "Candidates": candidates,
    }
    return {
        "DecisionPackageID": _content_id("RDP", decision_basis),
        "RequestID": request_id,
        "ProblemID": problem_id,
        "SolverBackendID": solver_backend_id,
        "SolverStatus": solver_status,
        "ScheduleSnapshotID": schedule_snapshot_id,
        "OperationalStateSnapshotID": operational_state_snapshot_id,
        "OperationalStateCapturedAt": operational_state_captured_at,
        "EvaluatedAt": evaluated_at,
        "MaterialRequirements": material_requirements,
        "Candidates": candidates,
    }


def _content_id(prefix: str, value: object) -> str:
    canonical = json.dumps(
        value,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return f"{prefix}-{sha256(canonical.encode('utf-8')).hexdigest()[:16]}"
