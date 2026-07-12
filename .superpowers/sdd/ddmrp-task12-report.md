# DDMRP Task 12 Verification Report

Date: 2026-07-12

## Scope And Status

- Executed only Task 12 from `docs/superpowers/plans/2026-07-11-ddmrp-runtime-replenishment-closure.md` in `D:\Documents\SDBR\.worktrees\ddmrp-replenishment`.
- Status: `BLOCKED`.
- No Activation A1-A8 work was started. No Buy/Make confirmation, candidate, reservation, allocation, external-order, or target-date behavior was added.
- `docs/backend-specification.md` and `docs/ui-specification.md` remain unchanged. Task 12 permits `BE-DDMRP-007` `[VERIFIED]` and `UI-DDMRP-003` `已验证待用户确认` only after its required browser matrix. That matrix could not start, so advancing either status or adding its planned changelog evidence would be fabricated.
- `BE-DDMRP-008`, `BE-DDMRP-009`, and `UI-DDMRP-004` remain unstarted, and `CONTRACT-GATE-DDMRP-ACTIVATION-001` remains closed.

## Automated Verification

| Command | Result |
| --- | --- |
| `python -m compileall -q sdbr` | Exit 0. |
| `node --check sdbr/web/planner-workbench.js` | Not runnable: `node` is not recognized on `PATH`. |
| Exact focused command with `--basetemp .tmp/pytest-ddmrp-readonly-focused` | Exit 1: inherited basetemp could not be removed (`WinError 5`); 362 passed, 35 setup errors, 36 warnings. The ignored directory was not modified. |
| Focused retry with fresh ignored basetemp | Exit 0: 397 passed, 1 existing `StarletteDeprecationWarning`, 76.99s. |
| Full retry with fresh ignored basetemp | Exit 0: 847 passed, 1 existing `StarletteDeprecationWarning`, 95.73s. |
| `git diff --check` before report creation | Exit 0. |

The failed exact focused run is an environment/temporary-directory residual, not a test assertion failure. A fresh-basetemp five-case fixture probe passed before the full focused retry.

## Browser Matrix Attempt

The requested deterministic DB was successfully rebuilt through the project-module fallback because the planned console entrypoint is unavailable:

```text
sdbr-reset-test-data --database-path ...
# failed: command not recognized on PATH

python -m sdbr.test_data --database-path .tmp/ddmrp-ui-acceptance/workbench-state.db
# exit 0; environment_id: test
```

The planned factory target is not importable in this environment:

```text
python -c "import tests; print(tests.__file__); from tests.ddmrp_browser_acceptance_app import create_runtime_app"
# tests.__file__: E:\\Program Files\\Python\\Python312\\Lib\\site-packages\\tests\\__init__.py
# ModuleNotFoundError: No module named 'tests.ddmrp_browser_acceptance_app'

python -m uvicorn tests.ddmrp_browser_acceptance_app:create_runtime_app --factory --host 127.0.0.1 --port 8011
# ERROR: Error loading ASGI app. Could not import module "tests.ddmrp_browser_acceptance_app".
```

The exact bounded Task 12 `Start-Process` lifecycle then exited with `DDMRP acceptance server exited during startup.` Port `8011` was free before the attempt and independently confirmed free afterward. The unrelated running `pytest` process observed after cleanup used `.tmp/pytest-mto-task13-full`; it did not own port `8011` and was not terminated.

No browser page was opened. The following required artifacts do not exist and must not be treated as evidence:

```text
.tmp/ddmrp-ui-acceptance/browser-report.md
.tmp/ddmrp-ui-acceptance/seeded-1280x720.png
.tmp/ddmrp-ui-acceptance/seeded-1920x1080.png
.tmp/ddmrp-ui-acceptance/seeded-390x844.png
.tmp/ddmrp-ui-acceptance/empty-1280x720.png
.tmp/ddmrp-ui-acceptance/error-1280x720.png
.tmp/ddmrp-ui-acceptance/403-1280x720.png
.tmp/ddmrp-ui-acceptance/409-1280x720.png
```

## Exact Blockers

1. `tests.ddmrp_browser_acceptance_app:create_runtime_app` resolves `tests` to a site-packages package because the repository `tests/` directory is not importable as that package. The acceptance server cannot start, so the catalog/workbench endpoint checks and all five visual modes cannot be executed.
2. `node` is unavailable on `PATH`, so the required `node --check` command cannot run.
3. The prescribed focused `--basetemp` path is not removable by the current test process (`WinError 5`). Fresh ignored basetemps allow the suites to complete, but do not make the exact command pass.
4. The `sdbr-reset-test-data` console entrypoint is unavailable on `PATH`; `python -m sdbr.test_data` is a successful project-module fallback, not a substitute for a registered console-script installation.

Resolving item 1 requires an explicitly approved follow-up to make the Task 11 factory import path runtime-importable. No such scope change was made here.

## Completion Evidence After 5d664c2 (2026-07-12)

- `5d664c2` made the required `tests.ddmrp_browser_acceptance_app:create_runtime_app` target importable. The package marker exposed one pre-existing test-only sibling import; changing `tests/test_ddmrp_replenishment_view.py` to import `tests.test_ddmrp_replenishment` restored collection without changing production behavior.
- Fresh verification used writable basetemps outside the inherited locked `.tmp` path: `python -m compileall -q sdbr` and local `node.exe --check sdbr/web/planner-workbench.js` exited 0; the exact Task 12 focused selection passed 398 tests and the full suite passed 848 tests. Each suite emitted one existing `StarletteDeprecationWarning`.
- The deterministic acceptance database was rebuilt through `python -m sdbr.test_data --database-path .tmp/ddmrp-ui-acceptance/workbench-state.db`. The bounded fixture lifecycle started on port 8011, passed its health check, found exactly one `TST-DDMRP-REPLENISHMENT-READONLY-20260711` catalog case, and verified the exact seeded summary and four-row set.
- Browser evidence completed for seeded 1280x720, 1920x1080, and 390x844 plus empty/error/403/409 at 1280x720. Explicit HTTP observations were seeded 200, empty 200, error 500, 403 403, and 409 409. The report and seven fixed screenshot paths exist under `.tmp/ddmrp-ui-acceptance/`.
- The server was stopped and port 8011 was independently confirmed free. `BE-DDMRP-007` is now `[VERIFIED]`; `UI-DDMRP-003` is `已验证待用户确认`. `BE-DDMRP-008`, `BE-DDMRP-009`, `UI-DDMRP-004`, Activation A1-A8, and `CONTRACT-GATE-DDMRP-ACTIVATION-001` remain unchanged and closed. No user confirmation was recorded.
