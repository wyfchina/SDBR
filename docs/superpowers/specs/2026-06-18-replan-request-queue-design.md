# Replan Request Queue Design

## Goal

Convert a release stability `Replan` recommendation into an auditable pending
request without invoking Gurobi automatically.

## Domain Model

A replan request contains a deterministic request ID, problem ID, order ID,
planned release time, detection time, reason code, deviation minutes,
consecutive blocked count, source, and status. New requests start as
`PendingReview` and use `ReleaseStability` as their source.

The deterministic identity is based on problem ID, order ID, planned release
time, and reason code. Repeated evaluations of the same active plan therefore
produce the same identity.

## Queue Behavior

The release endpoint creates a request only when `ReplanRequired` is true. If an
open request with the same identity already exists, the endpoint reuses it
instead of appending a duplicate. The release response includes the request.

`GET /planner/workbench/replan-requests` returns current requests. The initial
API adapter stores them in application memory, matching the existing execution
event adapter. Domain creation and identity logic remain storage-independent so
a database repository can replace the adapter later.

## Boundary

This increment does not approve requests, call Gurobi, or mark a replan as
completed. Those actions require an explicit orchestration transition in a
later increment.

## Testing

Unit tests cover deterministic request creation and ignoring non-replan
stability results. API tests cover request creation, deduplication, list access,
and the absence of requests for `Monitor` and `Review` results.
