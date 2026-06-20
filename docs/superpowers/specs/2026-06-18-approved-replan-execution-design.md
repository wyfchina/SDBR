# Approved Replan Execution Design

## Goal

Execute an approved replan request with Gurobi using a fresh planning snapshot
and record the solver outcome on the request.

## State Machine

Only `Approved` requests can start. Starting transitions the request to
`Running` and records execution start time plus backend ID. Finishing transitions
to `Completed` for `Optimal` or `Feasible`; every other solver status transitions
to `Failed`. Completion records time, solver status, and solver message.

## API

`POST /planner/workbench/replan-requests/{request_id}/execute` accepts the normal
planner calculation payload as the current data snapshot.

- Unknown request returns `404`.
- A request not in `Approved` returns `409`.
- Snapshot `ProblemID` mismatch returns `409`.
- A backend other than `gurobi` returns `409`.
- Invalid master data returns `409` without changing request status.
- Valid execution returns `200` with the updated request and schedule data,
  including failed solver outcomes for auditability.

Execution is synchronous in the current adapter. The domain state transitions
do not depend on synchronous execution and can later be reused by a worker.

## Testing

Unit tests cover start, successful completion, failed completion, and invalid
state transitions. API tests cover authorization/state checks, backend and
problem validation, and real Gurobi execution with an availability-tolerant
assertion.
