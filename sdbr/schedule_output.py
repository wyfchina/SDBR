from __future__ import annotations


def scheduled_work_order_rows_from_schedule(
    schedule: dict[str, object],
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for gantt_row in schedule.get("GanttRows", []):
        if not isinstance(gantt_row, dict):
            continue
        resource_id = gantt_row.get("ResourceID")
        for bar in gantt_row.get("Bars", []):
            if not isinstance(bar, dict):
                continue
            rows.append(
                {
                    "OrderID": bar.get("OrderID"),
                    "OperationID": bar.get("OperationID"),
                    "ResourceID": resource_id,
                    "Start": bar.get("Start"),
                    "End": bar.get("End"),
                    "DurationMinutes": bar.get("DurationMinutes"),
                }
            )
    return sorted(
        rows,
        key=lambda item: (
            str(item.get("Start", "")),
            str(item.get("ResourceID", "")),
            str(item.get("OperationID", "")),
        ),
    )


def scheduled_order_rows_from_schedule(
    schedule: dict[str, object],
) -> list[dict[str, object]]:
    operations = scheduled_work_order_rows_from_schedule(schedule)
    operations_by_order: dict[str, list[dict[str, object]]] = {}
    for operation in operations:
        order_id = operation.get("OrderID")
        if order_id is None:
            continue
        operations_by_order.setdefault(str(order_id), []).append(operation)

    rows = []
    for order_id, order_operations in operations_by_order.items():
        ordered_operations = sorted(
            order_operations,
            key=lambda item: (
                str(item.get("Start", "")),
                str(item.get("End", "")),
                str(item.get("OperationID", "")),
            ),
        )
        first_operation = ordered_operations[0]
        last_operation = max(
            ordered_operations,
            key=lambda item: (
                str(item.get("End", "")),
                str(item.get("Start", "")),
                str(item.get("OperationID", "")),
            ),
        )
        resource_ids = []
        for operation in ordered_operations:
            resource_id = operation.get("ResourceID")
            if resource_id is not None and resource_id not in resource_ids:
                resource_ids.append(resource_id)
        rows.append(
            {
                "OrderID": order_id,
                "ScheduledStart": first_operation.get("Start"),
                "ScheduledEnd": last_operation.get("End"),
                "FirstOperationID": first_operation.get("OperationID"),
                "FirstResourceID": first_operation.get("ResourceID"),
                "LastOperationID": last_operation.get("OperationID"),
                "LastResourceID": last_operation.get("ResourceID"),
                "OperationCount": len(ordered_operations),
                "TotalDurationMinutes": sum(
                    int(operation.get("DurationMinutes") or 0)
                    for operation in ordered_operations
                ),
                "ResourceIDs": resource_ids,
            }
        )

    return sorted(
        rows,
        key=lambda item: (
            str(item.get("ScheduledStart", "")),
            str(item.get("OrderID", "")),
        ),
    )
