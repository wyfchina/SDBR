# SDBR Development Environment Portability Repair Design

**Date:** 2026-07-17  
**Status:** Approved for implementation by the user  
**Applicable backend capabilities:** `BE-RUN-010`, `BE-INT-008`

## 1. Purpose

Repair the SDBR development environment after moving the repository and its
DDAE contract repository to a new Windows device. The repaired environment
must support the documented development, test, and startup commands without
depending on a temporary import workaround or a fixed drive letter.

This work changes development-path resolution and local tooling only. It does
not change any DDAE contract field, SDBR capability boundary, solver behavior,
or backend specification status.

## 2. Confirmed Problems

1. The tracked Python package path is `sdbr/`, but the migrated filesystem
   preserved the directory as `SDBR/`. Python therefore cannot resolve
   `import sdbr` unless the temporary `PYTHONCASEOK=1` workaround is used.
2. The DDAE contract repository now exists at
   `C:\Users\吴一帆\Documents\DDAE_INTERFACE_CONTRACT`, while seven test
   modules and several public-demo defaults still use
   `D:\Documents\DDAE_INTERFACE_CONTRACT` directly.
3. The runtime supports `DDAE_INTERFACE_CONTRACT_ROOT`, but the tests do not
   consistently use the same resolver. Public-demo package defaults also do
   not derive from the configured contract root.
4. `.tmp/` is intentionally ignored and was not recreated during migration,
   so documented relative `--basetemp .tmp\...` commands fail.
5. Python's `Scripts` directory is absent from the user `PATH`; the installed
   `pytest.exe` therefore cannot be called as `pytest`.
6. PowerShell 7 is not installed, so documented `pwsh` commands are unavailable.

## 3. Selected Approach

Use a portable repository repair plus explicit local-machine bootstrap. Do not
create a `D:` directory junction and do not retain `PYTHONCASEOK` as a normal
development setting.

### 3.1 Normalize the package directory

Perform a two-step case-only rename from the migrated `SDBR/` package directory
to `sdbr/`. Git already tracks the lowercase path, so this restores the
filesystem to the repository's canonical spelling without changing package
contents.

Acceptance evidence is a fresh Python process in which
`importlib.util.find_spec("sdbr")` and `import sdbr` succeed with
`PYTHONCASEOK` unset.

### 3.2 Centralize portable contract paths

Add a small `sdbr/environment_paths.py` module with two responsibilities:

- resolve the DDAE contract root from `DDAE_INTERFACE_CONTRACT_ROOT`, falling
  back to the historical `D:\Documents\DDAE_INTERFACE_CONTRACT` only when the
  environment variable is absent;
- resolve the public-demo package root from `SDBR_PUBLIC_DEMO_PACKAGE_ROOT`, or
  derive it as `<resolved contract root>/data/public-demo-golden-data-v1` when
  no explicit public-demo override exists.

Existing DDAE/runtime modules and the affected tests will consume these
resolvers instead of embedding new machine-specific paths. The historical
fallback remains for compatibility; the new `C:` location is supplied through
the environment, not committed as a product default.

The resolver must not search arbitrary directories, reconstruct contract
payloads, create placeholders, or alter contract data. Missing paths continue
to fail visibly in the consuming capability.

### 3.3 Bootstrap the current Windows user environment

Persist the following user-level settings:

- `DDAE_INTERFACE_CONTRACT_ROOT` set to the verified new contract repository;
- Python 3.12's `Scripts` directory appended to the user `PATH` exactly once.

Create the ignored local `.tmp/` directory. Install Microsoft PowerShell 7
through `winget`, then verify `pwsh` in a fresh process. These operations affect
the current development machine, not repository product behavior.

No persistent `PYTHONCASEOK` variable may be created.

### 3.4 Update durable operating instructions

Update `AGENTS.md`, `runme.md`, and the latest handoff document so future
commands use `DDAE_INTERFACE_CONTRACT_ROOT`, create `.tmp/` before relative
pytest basetemp paths, and describe the current portable contract-path rule.
Historical evidence paths in older specifications and reports remain unchanged.

The latest handoff file is currently untracked. It may be updated as local
handoff evidence, but it must not be silently added to a commit unless the user
explicitly requests that repository-history change.

## 4. Testing Strategy

Use test-driven development for the path resolver:

1. Add tests proving environment-variable precedence, the legacy fallback, the
   public-demo derivation rule, and explicit public-demo override precedence.
2. Run the tests before implementation and confirm they fail because the new
   resolver does not exist.
3. Add the minimal resolver implementation and migrate consumers.
4. Re-run focused contract and public-demo tests with
   `DDAE_INTERFACE_CONTRACT_ROOT` set to the new repository.

Final verification must include:

- standard lowercase `sdbr` import with no case workaround;
- `python -m compileall -q sdbr`;
- the documented MTO suite, expected to retain `291 passed`;
- the full pytest suite with a fresh `.tmp` basetemp and no contract-path
  failures;
- Uvicorn startup and an HTTP 200 response from `/planner/workbench`;
- `pytest --version`, `pwsh --version`, and `pip check`;
- Git diff and status review confirming that unrelated user files were not
  changed or staged.

## 5. Failure Handling and Rollback

- If PowerShell installation fails, repository repair and Python verification
  continue; the tool installation remains an explicit unresolved machine item.
- If a configured contract root does not contain the required accepted
  contract assets, stop and report the missing asset. Do not copy or synthesize
  contract files inside SDBR.
- User-level `PATH` and `DDAE_INTERFACE_CONTRACT_ROOT` changes must preserve the
  previous values so they can be restored if validation fails.
- The package-directory rename can be reversed with the same two-step case-only
  operation if Python import validation unexpectedly regresses.

## 6. Non-Goals

- No DDS&OP/DDAE governance or contract schema changes.
- No change to `BE-RUN-010` or `BE-INT-008` capability status.
- No `D:` junction, copied contract repository, or hidden SDBR-only fields.
- No solver, scheduling, release, DDMRP, UI workflow, or production-authority
  behavior change.
