# P1 MTO + DDMRP Integration Conflict Report

Date: 2026-07-12
Branch: `codex/p1-mto-ddmrp-integration`
Merge inputs: `codex/mto-order-commitment` and `codex/ddmrp-replenishment`
Specifications: `BE-SDBR-010`, `BE-DDMRP-007`, `UI-COMMIT-001`, `UI-DDMRP-003`, `UI-DDMRP-004`

## Conflict Decisions

### `docs/backend-specification.md`

- Retained both capability rows, detailed evidence, statuses, deferred boundaries, and change-log descriptions.
- Kept MTO history at versions 2.80 through 2.82 and rebased the parallel DDMRP entries to 2.83 and 2.84 so the merged ledger has unique, monotonic version identifiers.
- Set the merged document header to version 2.84 dated 2026-07-12.
- Preserved `BE-SDBR-010` as `[PARTIAL]`, `BE-DDMRP-007` as `[VERIFIED]`, and the DDMRP activation gate as closed.

### `docs/ui-specification.md`

- Retained the full MTO commitment workbench specification and both DDMRP acceptance-unit specifications.
- Assigned acceptance order 13 to `UI-COMMIT-001`, 14 to `UI-DDMRP-003`, and 15 to `UI-DDMRP-004`; updated the `UI-DDMRP-004` prerequisite to reference unit 14.
- Kept MTO history at versions 5.35 and 5.36 and rebased the parallel DDMRP entries to 5.37 and 5.38. The merged header and specification test now use version 5.38.
- Preserved both implemented UI units as `已验证待用户确认`; `UI-DDMRP-004` remains `未开始`. No unit was changed to `用户已确认`.

### `sdbr/api.py`

- Retained the union of Pydantic imports required by the MTO typed payloads and DDMRP validation adapters.
- Retained both protected route prefixes: `/planner/workbench/order-commitments` and `/planner/workbench/ddmrp`.
- Unified persistence decisions so either branch's exact-replay marker (`skip_workbench_persistence` or `skip_workbench_save`) prevents a redundant save, while existing controlled-error writes can still request persistence with `persist_workbench_write`.
- Found and fixed an automatic-merge issue outside the conflict markers: both feature modules exported `canonical_fingerprint`. DDMRP now uses `ddmrp_canonical_fingerprint`, while the MTO function remains available as the existing public `sdbr.api.canonical_fingerprint` symbol.
- Retained both sets of endpoint models, state collections, handlers, and read-model builders.

### `sdbr/test_data.py`

- Retained all MTO fixture identifiers and the complete `seed_mto_order_commitment_fixture` helper.
- Retained all DDMRP read-only replenishment identifiers, runtime-line builder, and `_seed_ddmrp_read_only_replenishment_case` helper.
- The DDMRP baseline seed still invokes its read-only replenishment helper, while the MTO browser fixture remains an explicit reusable helper for its acceptance setup.

## Integration-Only Fixes

- Updated the MTO UI specification test from branch-local version 5.36 to merged version 5.38.
- Restored the existing `sdbr.api.canonical_fingerprint` compatibility surface after the initial explicit-alias change exposed a focused-test failure.
- No feature behavior, authority boundary, solver policy, or deferred activation scope was expanded.

## Verification

- `python -m compileall -q sdbr tests`: exit 0.
- Local Node runtime `--check sdbr/web/planner-workbench.js`: exit 0.
- Initial combined focused run: 827 passed, 2 failed, 41 setup errors, 1 warning. The two failures identified the API compatibility symbol and merged spec-version assertion above. All setup errors shared one environmental cause: the repository-local `.tmp` basetemp disappeared during the run.
- Minimal post-fix replay of the two failures: 2 passed, 1 warning.
- Final combined MTO + DDMRP focused suite with a fresh basetemp under the system temporary directory: 870 passed, 1 warning in 109.73s.
- Final full repository suite with a separate fresh system basetemp: 1223 passed, 1 warning in 159.09s.
- The only warning is the pre-existing FastAPI/Starlette `TestClient` deprecation warning for the installed `httpx` integration.
- No application or acceptance service was started.

## Remaining Risks

- Repository-local `.tmp` is not a reliable pytest basetemp in this environment; repeatable integration runs should continue to use a fresh system-temporary path.
- The existing Starlette/httpx deprecation warning remains unresolved and is unrelated to this merge.
- `BE-SDBR-010` remains partial, `UI-COMMIT-001` and `UI-DDMRP-003` still require explicit user confirmation, and DDMRP Buy/Make activation remains deferred behind its contract gate.
