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
- Simio must retain the product path defined by `UI-RUN-002`; the current implemented scope is optional post-schedule validation through Mock Runner or local Headless Runner. Simio Portal, Server Connector, Experiment automation, and any publication hard gate remain deferred until explicitly implemented.

## Product scope

- Maintain SDBR as a DDOM / S-DBR execution system only. Its responsibility is MRP/material feasibility, finite-capacity scheduling, release management, buffer execution, MES dispatch suggestions, execution feedback, variance capture, and optional Simio validation.
- Do not implement DDS&OP workflows in this repository unless explicitly requested. DDS&OP / DDAE owns model governance and configuration decisions, including scenario governance, master-setting approval, Buffer Profile governance, adjustment-factor approval, and strategic what-if simulation.
- DDAE-approved operating-model configuration must flow through this lifecycle: receive, validate, freeze, execute, and feed back. Do not recalculate or govern DDAE-owned master parameters in SDBR pages.
- Planning Run work must freeze the `OperatingModelConfigurationID` used for that run so results can always be traced back to the DDS&OP/DDAE configuration version in force at scheduling time.
- Time buffers, control points, DDMRP parameters, resource roles, and other DDAE-origin settings must be consumed according to the contract only. Do not silently extend their meaning or add implicit fields in SDBR.
- Feedback from SDBR to DDAE must include configuration version, run version, timestamp, data source, exception reason, and a traceable ID.
- Existing ERP/MES mock interfaces may remain inside SDBR, but DDAE connectivity must be governed separately by the Contract Agent and the contracts under `D:\Documents\DDAE_INTERFACE_CONTRACT`.
- If the execution layer discovers that a DDAE contract is insufficient, submit a contract change request. Do not first implement hidden SDBR-only fields or UI-side parameter workarounds.
- DDMRP capability belongs inside the DDOM runtime path, but do not build DDMRP parameter configuration, Buffer Profile governance, adjustment-factor approval, or DDS&OP scenario-governance UI here. Those settings are external inputs until a later explicit scope change.

## Simio integration work

- Record every Simio model generation or mutation process in a durable repository document so the workflow can later be promoted into a Codex Skill.
- Before guessing Simio API, XML, server connector, or headless execution behavior, inspect `model/` first. Official Simio PDFs are local-only reference files and are intentionally ignored by Git; when present locally, prefer `model/Simio API Reference Guide.pdf`, then `model/Simio Reference Guide.pdf` and `model/Simio Server Connector Reference.pdf`.
- Treat existing Simio `.spfx` / XML prototypes under `model/` as local source-of-truth examples for object names, table shapes, and supported scheduling constructs.
