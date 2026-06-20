# Replan Request Decision Design

## Goal

Allow a planner to approve or reject a pending replan request with an auditable
decision before any Gurobi orchestration is allowed.

## State Machine

Only `PendingReview` requests can be decided. `Approve` transitions to
`Approved`; `Reject` transitions to `Rejected`. A second decision on the same
request is rejected as a conflict. Rejection requires a non-empty comment;
approval comments are optional.

The immutable request records `DecidedBy`, `DecidedAt`, and `DecisionComment`.
Creation leaves these values empty.

## API

`POST /planner/workbench/replan-requests/{request_id}/decision` accepts
`Decision`, `DecidedBy`, `DecidedAt`, and optional `Comment`.

- Unknown request ID returns `404`.
- Unsupported decision values fail request validation with `422`.
- Missing rejection comment or an already decided request returns `409`.
- A successful transition returns the complete updated request.

The existing queue endpoint returns the decision metadata. No solver is called
by this endpoint.

## Testing

Unit tests cover approve, reject, rejection-comment enforcement, and repeated
decision protection. API tests cover successful approval, unknown IDs, and
conflict responses while retaining existing queue behavior.
