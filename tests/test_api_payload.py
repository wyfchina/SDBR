from datetime import datetime, timezone

from sdbr.api_payload import get_planner_workbench_demo_payload


def test_planner_workbench_demo_payload_wraps_serializable_workbench_view():
    payload = get_planner_workbench_demo_payload(
        generated_at=datetime(2026, 6, 15, 12, tzinfo=timezone.utc),
    )

    assert payload["Endpoint"] == "/planner/workbench/demo"
    assert payload["StatusCode"] == 200
    assert payload["Data"]["GeneratedAt"] == "2026-06-15T12:00:00+00:00"
    assert payload["Data"]["SolverBackendID"] == "baseline-finite"
    assert payload["Data"]["SolverStatus"] == "Feasible"
    assert payload["Data"]["OrderCount"] == 2
    assert payload["Data"]["LoadGraphRows"]
    assert payload["Data"]["GanttRows"]


def test_planner_workbench_demo_payload_can_report_cp_sat_solver_status():
    payload = get_planner_workbench_demo_payload(
        generated_at=datetime(2026, 6, 15, 12, tzinfo=timezone.utc),
        solver_backend_id="ortools",
    )

    assert payload["Data"]["SolverBackendID"] == "ortools"
    assert payload["Data"]["SolverStatus"] in {"Optimal", "Feasible"}
    assert payload["Data"]["GanttRows"]
    assert payload["Data"]["LoadGraphRows"]
