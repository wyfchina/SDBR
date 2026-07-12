# DDMRP Task 11 Browser Acceptance Fixture Report

Date: 2026-07-12

## Scope

- Implemented only Task 11 from `docs/superpowers/plans/2026-07-11-ddmrp-runtime-replenishment-closure.md`.
- Acceptance evidence: `BE-DDMRP-007` and `UI-DDMRP-003`.
- Added an executable, test-only FastAPI wrapper and its two planned test nodes.
- Did not run Task 12's browser process, screenshots, browser acceptance/spec finalization, or modify either specification.

## Delivered Fixture Boundary

- `tests/ddmrp_browser_acceptance_app.py` wraps `create_app(state_store=...)` only; `sdbr/api.py` is unchanged and the production application returns `404` for `PUT /__ddmrp_acceptance__/mode/seeded`.
- The only accepted modes are `seeded`, `empty`, `error`, `403`, and `409`. Invalid modes return the fixed `422` detail.
- Seeded traffic delegates to the real SQLite-backed workbench. Empty returns the exact eight-key safe projection from `build_ddmrp_replenishment_workbench(...)`. Error modes return fixed wrapper shapes with the required status and message.
- Every workbench GET response has `X-Workbench-Revision`; switching a mode or rejecting an invalid mode does not mutate any workbench ledger.
- `create_runtime_app()` refuses non-test environments and requires `SDBR_WORKBENCH_DB_PATH`, then opens `SQLiteWorkbenchStateStore` at that exact path.

## TDD Evidence

RED, before creating the test-only acceptance module:

```text
pytest @tests -q --basetemp .tmp/pytest-ddmrp-browser-fixture-red -p no:cacheprovider
6 failed, 1 warning
```

The five parameterized mode cases and the production-isolation case each failed for the expected missing `ddmrp_browser_acceptance_app` module.

GREEN, with the identical selection:

```text
pytest @tests -q --basetemp .tmp/pytest-ddmrp-browser-fixture-green -p no:cacheprovider
6 passed, 1 warning
```

The test loader uses an explicit file path because this repository deliberately has no `tests/__init__.py`, and an unrelated site-packages `tests` package would otherwise shadow the local fixture. The fixture remains test-only and is not packaged under `sdbr`.

## Related Verification And Review

```text
pytest tests/test_ddmrp_browser_acceptance_app.py tests/test_test_data.py -q --basetemp .tmp/pytest-ddmrp-browser-related -p no:cacheprovider
18 passed, 1 warning

pytest tests/test_api.py -q -k "ui_ddmrp_003 or be_ddmrp_007_workbench" --basetemp .tmp/pytest-ddmrp-browser-api-related -p no:cacheprovider
2 passed, 261 deselected, 1 warning

python -m compileall -q tests/ddmrp_browser_acceptance_app.py tests/test_ddmrp_browser_acceptance_app.py
exit 0

git diff --check
exit 0
```

Self-review confirmed the production package has no acceptance-fixture reference, the production route stays absent, safe response keys are exact, and the fixture has no write path to the state store.

## Concern

The pytest runs retain the existing FastAPI/Starlette `TestClient` `httpx` deprecation warning. Task 12 browser execution and specification finalization remain intentionally unstarted.
