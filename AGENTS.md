# Repository Working Agreement

## Backend development

- `docs/backend-specification.md` is the authoritative backend capability specification and completion ledger.
- Every backend change must cite the applicable `BE-*` specification IDs in tests, development reports, or acceptance records.
- Update the specification before implementation when a requested behavior changes a capability boundary or acceptance condition.
- Use only the status definitions in section 2 of the backend specification. Do not mark a capability as `[VERIFIED]` without implementation plus repeatable test or runtime evidence.
- Record partial capabilities explicitly; an interface skeleton, external-system responsibility, or paused integration must not be reported as complete.
- Add a dated entry to the backend specification change log whenever capability scope or status changes.

## UI development

- `docs/ui-specification.md` is the authoritative UI development specification.
- Every UI change must cite the applicable `UI-*` specification IDs.
- Implement UI acceptance units in the order defined by section 16 of the spec.
- After an acceptance unit is implemented and verified, stop and request user confirmation.
- Do not mark a specification item as `用户已确认` until the user explicitly confirms it.
- Change the specification first when requested behavior conflicts with the current spec.
- Do not expose raw JSON master-data payloads in the normal planner workflow.

## Deferred integrations

- OR-Tools CP-SAT is the currently active and only executable solver implementation for new planning runs.
- Gurobi must retain historical-result compatibility, but new Gurobi planning runs are paused and must be shown as unavailable for execution.
- Simio must retain the product path defined by `UI-RUN-002`, but must be shown as unavailable until its backend integration is implemented.
