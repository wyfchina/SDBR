from __future__ import annotations

from datetime import datetime

from sdbr.release_authorization import ReleaseAuthorization
from sdbr.shop_floor_execution import default_exception_codes


STAGES = ("YetToBeReceived", "Received")
ZONES = ("Early", "Green", "Yellow", "Red", "Late")
MEASURE_TYPES = ("Quantity", "CompletionPercent", "Hours")
REASON_REQUIRED_ZONES = ("Late",)


def build_buffer_execution_workbench(
    *,
    planning_run: dict[str, object],
    master_data_version: dict[str, object],
    authorizations: list[ReleaseAuthorization],
    execution_events: list[dict[str, object]],
    evaluated_at: datetime,
) -> dict[str, object]:
    rows = _active_rows(
        planning_run=planning_run,
        master_data_version=master_data_version,
        authorizations=authorizations,
        execution_events=execution_events,
        evaluated_at=evaluated_at,
    )
    resources = _dict_list(master_data_version.get("Resources"))
    constraint = next(
        (resource for resource in resources if resource.get("IsConstraint") is True),
        {},
    )
    matrix = []
    for stage in STAGES:
        cells = []
        for zone in ZONES:
            orders = [
                row for row in rows
                if row["Stage"] == stage and row["Zone"] == zone
            ]
            cells.append(
                {
                    "Zone": zone,
                    "OrderCount": len(orders),
                    "TotalLoadMinutes": sum(
                        int(order["LoadMinutes"]) for order in orders
                    ),
                    "Orders": orders,
                }
            )
        matrix.append({"Stage": stage, "Cells": cells})

    schedule = _dict(planning_run.get("Schedule"))
    return {
        "Context": {
            "RunID": planning_run.get("RunID"),
            "LocationID": constraint.get("LocationID"),
            "ConstraintResourceID": constraint.get("ResourceID"),
            "ConstraintResourceName": constraint.get("Name"),
            "BufferOwnerID": constraint.get("OwnerID"),
            "DailyLoadMinutes": sum(int(row["LoadMinutes"]) for row in rows),
            "LastScheduledAt": schedule.get("GeneratedAt"),
            "EvaluatedAt": evaluated_at.isoformat(),
        },
        "Rows": matrix,
        "TransactionPolicy": _transaction_policy(),
    }


def build_buffer_order_detail(
    *,
    planning_run: dict[str, object],
    master_data_version: dict[str, object],
    authorizations: list[ReleaseAuthorization],
    execution_events: list[dict[str, object]],
    order_id: str,
    evaluated_at: datetime,
) -> dict[str, object]:
    rows = _active_rows(
        planning_run=planning_run,
        master_data_version=master_data_version,
        authorizations=authorizations,
        execution_events=execution_events,
        evaluated_at=evaluated_at,
    )
    row = next((item for item in rows if item["OrderID"] == order_id), None)
    if row is None:
        raise KeyError(order_id)
    orders = {
        str(order.get("OrderID")): order
        for order in _dict_list(master_data_version.get("Orders"))
    }
    order = orders.get(order_id, {})
    return {
        "Order": {
            "OrderID": order_id,
            "ProductID": row["ProductID"],
            "CustomerID": order.get("CustomerID"),
            "PromiseDate": order.get("PromiseDate") or order.get("DueDate"),
            "Priority": row["Priority"],
            "Quantity": row["Quantity"],
            "LoadMinutes": row["LoadMinutes"],
        },
        "Execution": {
            "AuthorizationID": row["AuthorizationID"],
            "Stage": row["Stage"],
            "Zone": row["Zone"],
            "CurrentReasonCode": row["CurrentReasonCode"],
            "ScheduledStart": row["ScheduledStart"],
            "ScheduledEnd": row["ScheduledEnd"],
            "SuggestedReleaseAt": row["SuggestedReleaseAt"],
        },
        "TransactionPolicy": _transaction_policy(),
    }


def buffer_zone(
    *,
    suggested_release_at: str | None,
    scheduled_start: str | None,
    evaluated_at: datetime,
) -> str:
    release_at = _parse_datetime(suggested_release_at)
    start_at = _parse_datetime(scheduled_start)
    if release_at is None or start_at is None or start_at <= release_at:
        return "Late" if start_at is not None and evaluated_at > start_at else "Red"
    if evaluated_at < release_at:
        return "Early"
    penetration = (evaluated_at - release_at) / (start_at - release_at) * 100
    if penetration <= 33:
        return "Green"
    if penetration <= 66:
        return "Yellow"
    if penetration <= 100:
        return "Red"
    return "Late"


def _active_rows(
    *,
    planning_run: dict[str, object],
    master_data_version: dict[str, object],
    authorizations: list[ReleaseAuthorization],
    execution_events: list[dict[str, object]],
    evaluated_at: datetime,
) -> list[dict[str, object]]:
    run_id = str(planning_run.get("RunID"))
    orders = {
        str(order.get("OrderID")): order
        for order in _dict_list(master_data_version.get("Orders"))
    }
    schedule = _dict(planning_run.get("Schedule"))
    scheduled_orders = _scheduled_orders(schedule)
    priorities = {
        str(item.get("OrderID")): item.get("Rank")
        for item in _dict_list(schedule.get("ExecutionPriorityQueue"))
    }
    rows = []
    for authorization in authorizations:
        if authorization.request_id != run_id or authorization.status != "Authorized":
            continue
        order_events = sorted(
            (
                event for event in execution_events
                if event.get("AuthorizationID") == authorization.authorization_id
                or (
                    event.get("AuthorizationID") is None
                    and event.get("OrderID") == authorization.order_id
                )
            ),
            key=lambda event: str(event.get("EventAt") or ""),
        )
        last_event = order_events[-1] if order_events else None
        if last_event and last_event.get("EventType") in {"CompletedOperation", "Shipped"}:
            continue
        order = orders.get(authorization.order_id, {})
        schedule_row = scheduled_orders.get(authorization.order_id, {})
        stage = (
            "Received"
            if any(
                event.get("EventType") in {"ArrivedBuffer", "StartedOperation"}
                for event in order_events
            )
            else "YetToBeReceived"
        )
        rows.append(
            {
                "AuthorizationID": authorization.authorization_id,
                "OrderID": authorization.order_id,
                "ProductID": order.get("ProductID"),
                "Quantity": order.get("Quantity"),
                "LoadMinutes": int(schedule_row.get("TotalDurationMinutes") or 0),
                "Priority": priorities.get(authorization.order_id),
                "Stage": stage,
                "Zone": buffer_zone(
                    suggested_release_at=authorization.suggested_release_at,
                    scheduled_start=authorization.scheduled_start,
                    evaluated_at=evaluated_at,
                ),
                "CurrentReasonCode": (
                    last_event.get("ExceptionCode") if last_event else None
                ),
                "ScheduledStart": authorization.scheduled_start,
                "ScheduledEnd": authorization.scheduled_end,
                "SuggestedReleaseAt": authorization.suggested_release_at,
            }
        )
    return sorted(rows, key=lambda row: (int(row["Priority"] or 999), str(row["OrderID"])))


def _scheduled_orders(schedule: dict[str, object]) -> dict[str, dict[str, object]]:
    result: dict[str, dict[str, object]] = {}
    for gantt_row in _dict_list(schedule.get("GanttRows")):
        for bar in _dict_list(gantt_row.get("Bars")):
            order_id = str(bar.get("OrderID"))
            row = result.setdefault(order_id, {"TotalDurationMinutes": 0})
            row["TotalDurationMinutes"] = int(row["TotalDurationMinutes"]) + int(
                bar.get("DurationMinutes") or 0
            )
    return result


def _transaction_policy() -> dict[str, object]:
    return {
        "MeasureTypes": list(MEASURE_TYPES),
        "ReasonRequiredZones": list(REASON_REQUIRED_ZONES),
        "ExceptionCodes": [
            {
                "Code": definition.code,
                "DisplayName": definition.display_name,
                "Category": definition.category,
            }
            for definition in default_exception_codes().values()
        ],
    }


def _dict(value: object) -> dict[str, object]:
    return value if isinstance(value, dict) else {}


def _dict_list(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))
