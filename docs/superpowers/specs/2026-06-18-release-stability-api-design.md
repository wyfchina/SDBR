# Release Stability API Integration Design

## Goal

Expose the existing release stability policy through the planner release gate
without changing the current release status codes or storing process-local
state.

## Request

`POST /planner/workbench/release` accepts three optional additions:

- `PreviousConsecutiveBlockedCount`, default `0`.
- `LastReplanAt`, default `null`.
- `StabilityPolicy`, containing configurable tolerance, replan threshold,
  consecutive blocked threshold, and cooldown values with current business
  defaults.

The previous blocked count represents completed evaluations before the current
request. A blocked current decision increments it; an allowed decision resets it
to zero.

## Response

Successful and blocked release decisions include `Data.Stability` with signed
and absolute deviation, timing status, severity, action, replan flag, reason
code, and the updated consecutive blocked count. The final gate result includes
both rope timing and inventory buffer checks before stability is evaluated.

Unknown orders and invalid master data keep their existing response contracts
because no valid release decision exists to evaluate.

## State Boundary

The endpoint is a stateless transition. The caller persists the returned
blocked count and records `LastReplanAt` only after a replan actually occurs.
This avoids inconsistent state across API processes and leaves a clean path to
an execution event store later.

## Testing

API tests cover backward-compatible defaults, repeated inventory blocking that
triggers replan, allowed release resetting the count, and cooldown suppression.
The complete test suite remains the regression gate.
