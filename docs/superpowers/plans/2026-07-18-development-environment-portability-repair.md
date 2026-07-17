# SDBR Development Environment Portability Repair Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restore a portable Windows development environment in which SDBR imports normally, contract-dependent tests use the configured DDAE repository, documented commands run, and the complete regression suite passes.

**Architecture:** Normalize the migrated package directory to Git's canonical lowercase spelling, then centralize contract and public-demo path resolution in one small Python module. Repository consumers and tests use that resolver, while user-level environment settings provide the new machine path without committing it as a product default. Machine tooling and documentation are repaired separately from backend behavior.

**Tech Stack:** Python 3.12, pathlib, pytest, FastAPI/Uvicorn, Windows PowerShell 5.1, PowerShell 7, winget, Git.

## Global Constraints

- Preserve SDBR as a DDOM / S-DBR execution system; do not add DDS&OP/DDAE governance.
- Applicable backend capability references are `BE-RUN-010` and `BE-INT-008`; their statuses remain unchanged.
- Do not change contract schemas, fields, payloads, or files under `DDAE_INTERFACE_CONTRACT`.
- Resolve the new contract location through `DDAE_INTERFACE_CONTRACT_ROOT`; keep `D:\Documents\DDAE_INTERFACE_CONTRACT` only as the legacy fallback.
- Do not create a `D:` directory junction and do not persist `PYTHONCASEOK`.
- Keep `docs/SDBR-development-handoff-latest.md` untracked unless the user separately authorizes adding it.
- Preserve unrelated user changes and the untracked `nofinish/` directory.
- Use a new `--basetemp` name for every Windows pytest run.

---

### Task 1: Normalize the migrated package directory and local temp root

**Files:**
- Filesystem rename only: `SDBR/` to `sdbr/`
- Create ignored directory: `.tmp/`

**Interfaces:**
- Consumes: Git's canonical tracked package spelling `sdbr/`.
- Produces: a case-correct importable package directory and an existing parent for documented pytest basetemp paths.

- [ ] **Step 1: Reproduce the lowercase import failure without a workaround**

Run with `PYTHONCASEOK` removed from the current process:

```powershell
Remove-Item Env:PYTHONCASEOK -ErrorAction SilentlyContinue
python -c "import importlib.util; print(importlib.util.find_spec('sdbr'))"
```

Expected before repair: `None`.

- [ ] **Step 2: Perform a two-step case-only rename**

```powershell
$actualPackage = Get-ChildItem -LiteralPath . -Directory |
  Where-Object { $_.Name -ceq 'SDBR' } |
  Select-Object -First 1
if ($actualPackage) {
  Rename-Item -LiteralPath $actualPackage.FullName -NewName '__sdbr_casefix__'
  Rename-Item -LiteralPath '.\__sdbr_casefix__' -NewName 'sdbr'
}
```

Expected: `python` sees the package as `sdbr`, while Git reports no content rename.

- [ ] **Step 3: Create the ignored temp parent**

```powershell
New-Item -ItemType Directory -Force .tmp | Out-Null
```

Expected: `Test-Path .tmp` returns `True`, and `.tmp/` remains ignored by Git.

- [ ] **Step 4: Verify import and worktree state**

```powershell
Remove-Item Env:PYTHONCASEOK -ErrorAction SilentlyContinue
python -c "import importlib.util, sdbr; print(importlib.util.find_spec('sdbr')); print(sdbr.__file__)"
git status --short
```

Expected: a non-null module spec, a path ending in `sdbr\__init__.py`, and no tracked change caused by the case repair.

### Task 2: Add the portable path resolver with TDD

**Files:**
- Create: `tests/test_environment_paths.py`
- Create: `sdbr/environment_paths.py`

**Interfaces:**
- Produces: `LEGACY_DDAE_INTERFACE_CONTRACT_ROOT: Path`.
- Produces: `resolve_ddae_interface_contract_root(environ: Mapping[str, str] | None = None) -> Path`.
- Produces: `resolve_public_demo_package_root(environ: Mapping[str, str] | None = None) -> Path`.

- [ ] **Step 1: Write the failing resolver tests**

Create `tests/test_environment_paths.py`:

```python
from pathlib import Path

from sdbr.environment_paths import (
    LEGACY_DDAE_INTERFACE_CONTRACT_ROOT,
    resolve_ddae_interface_contract_root,
    resolve_public_demo_package_root,
)


def test_be_run_010_be_int_008_contract_root_uses_environment_override() -> None:
    configured = Path(r"C:\portable\DDAE_INTERFACE_CONTRACT")

    assert resolve_ddae_interface_contract_root(
        {"DDAE_INTERFACE_CONTRACT_ROOT": str(configured)}
    ) == configured


def test_be_run_010_be_int_008_contract_root_keeps_legacy_fallback() -> None:
    assert (
        resolve_ddae_interface_contract_root({})
        == LEGACY_DDAE_INTERFACE_CONTRACT_ROOT
    )


def test_be_int_008_public_demo_root_derives_from_contract_root() -> None:
    contract_root = Path(r"C:\portable\DDAE_INTERFACE_CONTRACT")

    assert resolve_public_demo_package_root(
        {"DDAE_INTERFACE_CONTRACT_ROOT": str(contract_root)}
    ) == contract_root / "data" / "public-demo-golden-data-v1"


def test_be_int_008_public_demo_explicit_override_wins() -> None:
    explicit = Path(r"C:\fixtures\public-demo")

    assert resolve_public_demo_package_root(
        {
            "DDAE_INTERFACE_CONTRACT_ROOT": r"C:\portable\DDAE_INTERFACE_CONTRACT",
            "SDBR_PUBLIC_DEMO_PACKAGE_ROOT": str(explicit),
        }
    ) == explicit
```

- [ ] **Step 2: Run the new tests and verify RED**

```powershell
python -m pytest tests\test_environment_paths.py -q `
  --basetemp .tmp\pytest-environment-paths-red-20260718 `
  -p no:cacheprovider
```

Expected: collection error `ModuleNotFoundError: No module named 'sdbr.environment_paths'`.

- [ ] **Step 3: Implement the minimal resolver**

Create `sdbr/environment_paths.py`:

```python
from __future__ import annotations

from collections.abc import Mapping
import os
from pathlib import Path


LEGACY_DDAE_INTERFACE_CONTRACT_ROOT = Path(
    r"D:\Documents\DDAE_INTERFACE_CONTRACT"
)


def resolve_ddae_interface_contract_root(
    environ: Mapping[str, str] | None = None,
) -> Path:
    values = os.environ if environ is None else environ
    configured = values.get("DDAE_INTERFACE_CONTRACT_ROOT")
    if configured:
        return Path(configured)
    return LEGACY_DDAE_INTERFACE_CONTRACT_ROOT


def resolve_public_demo_package_root(
    environ: Mapping[str, str] | None = None,
) -> Path:
    values = os.environ if environ is None else environ
    configured = values.get("SDBR_PUBLIC_DEMO_PACKAGE_ROOT")
    if configured:
        return Path(configured)
    return (
        resolve_ddae_interface_contract_root(values)
        / "data"
        / "public-demo-golden-data-v1"
    )
```

- [ ] **Step 4: Run the resolver tests and verify GREEN**

```powershell
python -m pytest tests\test_environment_paths.py -q `
  --basetemp .tmp\pytest-environment-paths-green-20260718 `
  -p no:cacheprovider
```

Expected: `4 passed`.

- [ ] **Step 5: Commit the tested resolver**

```powershell
git add sdbr/environment_paths.py tests/test_environment_paths.py
git diff --cached --check
git commit -m "test: define portable DDAE environment paths"
```

### Task 3: Migrate runtime consumers and contract tests

**Files:**
- Modify: `sdbr/ddsop_contracts.py:18-23`
- Modify: `sdbr/execution_object_evidence_contracts.py:18-23`
- Modify: `sdbr/production_inventory_quality_contracts.py:18-23`
- Modify: `sdbr/supplier_identity_source_contracts.py:18-23`
- Modify: `sdbr/adventureworks_product_demo_profile.py:53-59`
- Modify: `sdbr/adventureworks_scheduling_adapter.py:58-64`
- Modify: `sdbr/public_demo_golden_loop.py:37-43`
- Modify: `tests/test_adventureworks_product_demo_profile.py:15`
- Modify: `tests/test_adventureworks_scheduling_adapter.py:24`
- Modify: `tests/test_ddsop_contracts.py:27`
- Modify: `tests/test_ddsop_runtime_planning_input.py:26`
- Modify: `tests/test_execution_object_evidence_contracts.py:20`
- Modify: `tests/test_production_inventory_quality_contracts.py:18`
- Modify: `tests/test_supplier_identity_source_contracts.py:18`

**Interfaces:**
- Consumes: both resolver functions from Task 2.
- Preserves: existing module-level `DEFAULT_CONTRACT_ROOT` values and existing public wrapper function names used by callers.
- Produces: test fixtures and runtime defaults that agree on the configured contract root.

- [ ] **Step 1: Verify the existing hardcoded test-path failure**

```powershell
$env:DDAE_INTERFACE_CONTRACT_ROOT = `
  (Resolve-Path (Join-Path $HOME 'Documents\DDAE_INTERFACE_CONTRACT')).Path
python -m pytest `
  tests\test_adventureworks_product_demo_profile.py `
  tests\test_adventureworks_scheduling_adapter.py `
  tests\test_ddsop_contracts.py `
  tests\test_ddsop_runtime_planning_input.py `
  tests\test_execution_object_evidence_contracts.py `
  tests\test_production_inventory_quality_contracts.py `
  tests\test_supplier_identity_source_contracts.py `
  -q --tb=line `
  --basetemp .tmp\pytest-contract-paths-red-20260718 `
  -p no:cacheprovider
```

Expected before migration: failures reference `D:\Documents\DDAE_INTERFACE_CONTRACT`.

- [ ] **Step 2: Replace duplicated runtime contract-root defaults**

In each of these four modules:

- `sdbr/ddsop_contracts.py`
- `sdbr/execution_object_evidence_contracts.py`
- `sdbr/production_inventory_quality_contracts.py`
- `sdbr/supplier_identity_source_contracts.py`

import and assign the shared resolver:

```python
from sdbr.environment_paths import resolve_ddae_interface_contract_root


DEFAULT_CONTRACT_ROOT = resolve_ddae_interface_contract_root()
```

Remove the replaced local `Path(os.environ.get(...))` block. Remove `os` only
when the module has no other `os` usage; retain `Path` when used elsewhere.

- [ ] **Step 3: Preserve product-demo wrapper APIs while using the resolver**

In `sdbr/adventureworks_product_demo_profile.py`:

```python
from sdbr.environment_paths import resolve_ddae_interface_contract_root


def default_contract_root() -> Path:
    return resolve_ddae_interface_contract_root()
```

In `sdbr/adventureworks_scheduling_adapter.py`:

```python
from sdbr.environment_paths import resolve_public_demo_package_root


def adventureworks_public_demo_package_root() -> Path:
    return resolve_public_demo_package_root()
```

In `sdbr/public_demo_golden_loop.py`:

```python
from sdbr.environment_paths import resolve_public_demo_package_root


def public_demo_package_root() -> Path:
    return resolve_public_demo_package_root()
```

Keep `os` imports in files that still read other environment variables.

- [ ] **Step 4: Replace the seven hardcoded test roots**

In every listed contract-dependent test module, add:

```python
from sdbr.environment_paths import resolve_ddae_interface_contract_root
```

Replace the hardcoded assignment with:

```python
CONTRACT_ROOT = resolve_ddae_interface_contract_root()
```

Keep `Path` imports wherever the test module uses `Path` for temporary files or
type annotations.

- [ ] **Step 5: Run focused resolver and contract tests**

```powershell
$env:DDAE_INTERFACE_CONTRACT_ROOT = `
  (Resolve-Path (Join-Path $HOME 'Documents\DDAE_INTERFACE_CONTRACT')).Path
python -m pytest `
  tests\test_environment_paths.py `
  tests\test_adventureworks_product_demo_profile.py `
  tests\test_adventureworks_scheduling_adapter.py `
  tests\test_ddsop_contracts.py `
  tests\test_ddsop_runtime_planning_input.py `
  tests\test_execution_object_evidence_contracts.py `
  tests\test_production_inventory_quality_contracts.py `
  tests\test_supplier_identity_source_contracts.py `
  -q --tb=line `
  --basetemp .tmp\pytest-contract-paths-green-20260718 `
  -p no:cacheprovider
```

Expected: all selected tests pass with no reference to the old `D:` path.

- [ ] **Step 6: Commit the consumer migration**

```powershell
git add sdbr tests
git diff --cached --check
git commit -m "fix: resolve DDAE assets from portable environment paths"
```

### Task 4: Repair user-level Windows tooling and environment

**Files:**
- Create ignored local directory if absent: `.tmp/`
- Modify current Windows user environment: `DDAE_INTERFACE_CONTRACT_ROOT`, `Path`
- Install application: Microsoft PowerShell 7

**Interfaces:**
- Consumes: verified contract repository under `$HOME\Documents` and Python's `sysconfig` Scripts path.
- Produces: persistent user environment inherited by future terminals.

- [ ] **Step 1: Capture current values and persist the verified contract root**

```powershell
$previousContractRoot = [Environment]::GetEnvironmentVariable(
  'DDAE_INTERFACE_CONTRACT_ROOT', 'User'
)
$previousUserPath = [Environment]::GetEnvironmentVariable('Path', 'User')
$contractRoot = (
  Resolve-Path (Join-Path $HOME 'Documents\DDAE_INTERFACE_CONTRACT')
).Path
Write-Host "Previous contract root: $previousContractRoot"
Write-Host "Previous user PATH: $previousUserPath"
[Environment]::SetEnvironmentVariable(
  'DDAE_INTERFACE_CONTRACT_ROOT', $contractRoot, 'User'
)
$env:DDAE_INTERFACE_CONTRACT_ROOT = $contractRoot
```

Expected: the user-level and current-process values equal the verified `C:`
contract repository.

- [ ] **Step 2: Add Python Scripts to user PATH exactly once**

```powershell
$pythonScripts = python -c "import sysconfig; print(sysconfig.get_path('scripts'))"
$userPath = [Environment]::GetEnvironmentVariable('Path', 'User')
$pathEntries = @($userPath -split ';' | Where-Object { $_ })
if ($pathEntries -notcontains $pythonScripts) {
  $newUserPath = (($pathEntries + $pythonScripts) -join ';') + ';'
  [Environment]::SetEnvironmentVariable('Path', $newUserPath, 'User')
}
if (($env:Path -split ';') -notcontains $pythonScripts) {
  $env:Path = "$pythonScripts;$env:Path"
}
pytest --version
```

Expected: pytest reports version `9.0.2`, and the persistent user PATH contains
the Scripts directory once.

- [ ] **Step 3: Ensure no persistent case workaround exists**

```powershell
[Environment]::SetEnvironmentVariable('PYTHONCASEOK', $null, 'User')
Remove-Item Env:PYTHONCASEOK -ErrorAction SilentlyContinue
python -c "import sdbr; print(sdbr.__file__)"
```

Expected: the lowercase import succeeds without `PYTHONCASEOK`.

- [ ] **Step 4: Install PowerShell 7**

```powershell
winget install --id Microsoft.PowerShell --exact --source winget `
  --accept-source-agreements --accept-package-agreements --silent
```

Expected: winget installs Microsoft PowerShell 7 or reports that the matching
installed package is already current.

- [ ] **Step 5: Verify PowerShell 7 and the persistent environment**

```powershell
$pwsh = 'C:\Program Files\PowerShell\7\pwsh.exe'
& $pwsh --version
& $pwsh -NoProfile -Command `
  '[Environment]::GetEnvironmentVariable("DDAE_INTERFACE_CONTRACT_ROOT", "User")'
[Environment]::GetEnvironmentVariable('Path', 'User') -split ';' |
  Where-Object { $_ -eq $pythonScripts }
```

Expected: `PowerShell 7.x`, the new contract root, and exactly one matching
Python Scripts PATH entry.

### Task 5: Update portable operating instructions

**Files:**
- Modify: `AGENTS.md:36`
- Modify: `runme.md:1-100` and repeated startup snippets
- Modify but do not stage: `docs/SDBR-development-handoff-latest.md`

**Interfaces:**
- Consumes: the resolver and user-level environment rules from Tasks 2-4.
- Produces: commands that work on the new device and explain the legacy fallback.

- [ ] **Step 1: Update the repository working agreement path rule**

Replace the fixed-path sentence in `AGENTS.md` with:

```markdown
- Existing ERP/MES mock interfaces may remain inside SDBR, but DDAE connectivity must be governed separately by the Contract Agent and the contracts under `DDAE_INTERFACE_CONTRACT_ROOT`; the legacy fallback is `D:\Documents\DDAE_INTERFACE_CONTRACT`.
```

- [ ] **Step 2: Add a portable bootstrap block to `runme.md`**

Add before installation and verification commands:

```powershell
$SDBR_ROOT = (Resolve-Path (Join-Path $HOME 'Documents\SDBR')).Path
$DDAE_CONTRACT_ROOT = (
  Resolve-Path (Join-Path $HOME 'Documents\DDAE_INTERFACE_CONTRACT')
).Path
Set-Location $SDBR_ROOT
$env:DDAE_INTERFACE_CONTRACT_ROOT = $DDAE_CONTRACT_ROOT
New-Item -ItemType Directory -Force .tmp | Out-Null
```

State that the environment variable selects the contract repository and the
historical `D:` value is only a compatibility fallback. Replace active
`pytest ...` examples with `python -m pytest ...` so they do not depend on a
console-script PATH refresh. Replace active fixed SDBR root assignments with:

```powershell
$SDBR_ROOT = (Resolve-Path (Join-Path $HOME 'Documents\SDBR')).Path
```

- [ ] **Step 3: Update the local latest handoff without tracking it**

Use the same `$HOME\Documents` root derivation, set
`DDAE_INTERFACE_CONTRACT_ROOT`, and create `.tmp` in startup and verification
blocks. Record the 2026-07-18 migration repair and retain the rule that contract
contents remain authoritative outside SDBR.

- [ ] **Step 4: Verify documentation and stage tracked files only**

```powershell
rg -n 'D:\\Documents\\SDBR|pytest -q|D:\\Documents\\DDAE_INTERFACE_CONTRACT' `
  AGENTS.md runme.md docs\SDBR-development-handoff-latest.md
git add AGENTS.md runme.md
git diff --cached --check
git diff --cached --name-only
```

Expected: active instructions use portable roots; staged names are only
`AGENTS.md` and `runme.md`. Historical or explicitly labeled legacy fallback
mentions may remain.

- [ ] **Step 5: Commit tracked documentation**

```powershell
git commit -m "docs: make Windows development setup portable"
```

### Task 6: Run final acceptance and record exact evidence

**Files:**
- Modify: `docs/SDBR-development-handoff-latest.md` with final local evidence only
- Do not add contract files, `.tmp/`, or `nofinish/`

**Interfaces:**
- Consumes: all repaired repository and machine settings.
- Produces: fresh evidence supporting the environment-ready conclusion.

- [ ] **Step 1: Verify tooling and dependencies**

```powershell
Remove-Item Env:PYTHONCASEOK -ErrorAction SilentlyContinue
python --version
python -m pip check
pytest --version
pwsh --version
python -c "import sdbr; print(sdbr.__file__)"
```

Expected: Python 3.12, no broken requirements, pytest 9.0.2, PowerShell 7,
and a lowercase `sdbr` import.

- [ ] **Step 2: Compile the backend**

```powershell
python -m compileall -q sdbr
```

Expected: exit code 0 with no output.

- [ ] **Step 3: Run the MTO acceptance suite**

```powershell
python -m pytest `
  tests\test_order_commitment_api.py `
  tests\test_order_commitment_evaluation.py `
  tests\test_order_commitment_view.py `
  -q --basetemp .tmp\pytest-environment-repair-mto-20260718 `
  -p no:cacheprovider
```

Expected: `291 passed`.

- [ ] **Step 4: Run the complete regression suite**

```powershell
python -m pytest -q `
  --basetemp .tmp\pytest-environment-repair-full-20260718 `
  -p no:cacheprovider
```

Expected: all tests pass, including the four new path tests, with no old
contract-path failure.

- [ ] **Step 5: Verify actual HTTP startup**

Start the service in a managed terminal session:

```powershell
$env:SDBR_ENVIRONMENT = 'test'
$env:SDBR_WORKBENCH_DB_PATH = Join-Path $env:TEMP `
  'sdbr-environment-repair-20260718.db'
python -m uvicorn sdbr.api:app --host 127.0.0.1 --port 8765
```

From a second command, request:

```powershell
$response = Invoke-WebRequest -UseBasicParsing `
  -Uri 'http://127.0.0.1:8765/planner/workbench' `
  -TimeoutSec 10
$response.StatusCode
```

Expected: `200`. Stop Uvicorn and confirm port 8765 has no listener.

- [ ] **Step 6: Perform final repository hygiene review**

```powershell
git diff --check
git status --short
git rev-list --left-right --count origin/master...HEAD
```

Expected: no whitespace errors; no staged files; only the intentionally
untracked latest handoff and `nofinish/` remain; local commits are reported
accurately relative to `origin/master`.

- [ ] **Step 7: Record final local evidence**

Append the exact tool versions, test counts, service HTTP result, contract-root
location, and remaining untracked-file status to
`docs/SDBR-development-handoff-latest.md`. Keep the file untracked and report
that explicitly in the handoff.
