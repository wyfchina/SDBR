from __future__ import annotations


def summarize_scenario(view_payload: dict[str, object]) -> dict[str, object]:
    load_rows = view_payload.get("LoadGraphRows", [])
    total_overload_minutes = 0
    if isinstance(load_rows, list):
        for row in load_rows:
            if not isinstance(row, dict):
                continue
            cells = row.get("Cells", [])
            if not isinstance(cells, list):
                continue
            total_overload_minutes += sum(
                int(cell.get("OverloadMinutes", 0))
                for cell in cells
                if isinstance(cell, dict)
            )

    buffer_summary = view_payload.get("BufferSummary", {})
    red_buffer_count = 0
    has_critical_alert = False
    if isinstance(buffer_summary, dict):
        red_buffer_count = int(buffer_summary.get("RedCount", 0))
        has_critical_alert = bool(buffer_summary.get("HasCriticalAlert", False))

    return {
        "OrderCount": int(view_payload.get("OrderCount", 0)),
        "ConstraintOverloadCount": int(view_payload.get("ConstraintOverloadCount", 0)),
        "TotalOverloadMinutes": total_overload_minutes,
        "RedBufferCount": red_buffer_count,
        "HasCriticalAlert": has_critical_alert,
    }


def compare_scenarios(
    baseline_payload: dict[str, object],
    candidate_payload: dict[str, object],
) -> dict[str, object]:
    baseline = summarize_scenario(baseline_payload)
    candidate = summarize_scenario(candidate_payload)
    delta = {
        "ConstraintOverloadCount": int(candidate["ConstraintOverloadCount"])
        - int(baseline["ConstraintOverloadCount"]),
        "TotalOverloadMinutes": int(candidate["TotalOverloadMinutes"])
        - int(baseline["TotalOverloadMinutes"]),
        "RedBufferCount": int(candidate["RedBufferCount"]) - int(baseline["RedBufferCount"]),
        "CriticalAlertImproved": bool(baseline["HasCriticalAlert"])
        and not bool(candidate["HasCriticalAlert"]),
    }
    recommended = "Candidate" if _scenario_score(candidate) < _scenario_score(baseline) else "Baseline"
    return {
        "Baseline": baseline,
        "Candidate": candidate,
        "Delta": delta,
        "RecommendedScenario": recommended,
        "DecisionReasons": _decision_reasons(delta=delta, recommended=recommended),
    }


def _decision_reasons(delta: dict[str, object], recommended: str) -> list[str]:
    reasons = []
    total_overload_delta = int(delta["TotalOverloadMinutes"])
    red_buffer_delta = int(delta["RedBufferCount"])
    if total_overload_delta < 0:
        reasons.append(
            f"Candidate reduces total overload by {abs(total_overload_delta)} minutes."
        )
    elif total_overload_delta > 0:
        reasons.append(
            f"Baseline has {total_overload_delta} fewer overload minutes than Candidate."
        )

    if red_buffer_delta < 0:
        reasons.append(f"Candidate reduces red buffer count by {abs(red_buffer_delta)}.")
    elif red_buffer_delta > 0:
        reasons.append(f"Baseline has {red_buffer_delta} fewer red buffer items than Candidate.")

    if bool(delta["CriticalAlertImproved"]):
        reasons.append("Candidate clears a critical buffer alert.")

    if not reasons:
        reasons.append(f"{recommended} has the better overall scenario score.")
    return reasons


def _scenario_score(summary: dict[str, object]) -> tuple[int, int, int]:
    return (
        int(summary["TotalOverloadMinutes"]),
        int(summary["RedBufferCount"]),
        1 if summary["HasCriticalAlert"] else 0,
    )
