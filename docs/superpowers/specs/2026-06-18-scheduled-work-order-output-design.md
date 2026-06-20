# Scheduled Work Order Output Design

## Goal

Expose completed Gurobi replan results as flat scheduled operation rows for
downstream validation, release gating, and execution handoff.

## Output Contract

Each row contains `OrderID`, `OperationID`, `ResourceID`, `Start`, `End`, and
`DurationMinutes`. Rows are sorted by start time, resource, and operation.

The rows are derived from the schedule `GanttRows`, but the output is a business
handoff format rather than a UI-specific Gantt structure.

## API

The replan execution endpoint stores a schedule snapshot only when the request
finishes as `Completed`. Failed executions remain auditable through the request
and schedule response but do not publish work order output.

`GET /planner/workbench/replan-requests/{request_id}/scheduled-work-orders`
returns the flat rows for a completed request.

- Unknown request returns `404`.
- A request without completed schedule output returns `409`.
- Completed output returns `200` with request ID, solver status, and operations.

## Testing

Unit tests cover flattening and sorting. API tests cover successful output after
execution, unknown IDs, and unavailable output before completion.
