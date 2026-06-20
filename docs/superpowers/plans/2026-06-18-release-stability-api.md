# Release Stability API Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Return release stability decisions from the existing planner release endpoint while preserving old requests and status codes.

**Architecture:** Extend the release payload with optional history and policy fields. Evaluate stability only after rope and inventory checks produce the final gate result, then serialize it under `Data.Stability` without process-local persistence.

**Tech Stack:** Python, FastAPI, Pydantic, pytest

---

### Task 1: Default stability response

**Files:**
- Modify: `tests/test_api.py`
- Modify: `sdbr/api.py`

- [ ] **Step 1: Write a failing API test**

Extend the release-at-rope-date test to assert that an unchanged request returns
`Stability.Action == "Monitor"`, `ReplanRequired is False`, and
`ConsecutiveBlockedCount == 0`.

- [ ] **Step 2: Verify the test fails**

Run: `python -m pytest tests/test_api.py::test_planner_workbench_release_endpoint_allows_release_at_rope_date -q`

Expected: FAIL because `Data.Stability` is absent.

- [ ] **Step 3: Add optional payload fields and response serialization**

Add `PreviousConsecutiveBlockedCount`, `LastReplanAt`, and nested
`StabilityPolicy` defaults. Import `ReleaseStabilityInput`,
`ReleaseStabilityPolicy`, and `evaluate_release_stability`; evaluate using the
final gate result and serialize all result fields.

- [ ] **Step 4: Verify the targeted test passes**

Run: `python -m pytest tests/test_api.py::test_planner_workbench_release_endpoint_allows_release_at_rope_date -q`

Expected: PASS.

### Task 2: Blocking history and cooldown

**Files:**
- Modify: `tests/test_api.py`
- Modify: `sdbr/api.py`

- [ ] **Step 1: Write failing API tests**

Add tests proving that an inventory-blocked request with
`PreviousConsecutiveBlockedCount=2` triggers `Replan`, an allowed request resets
the count from two to zero, and `LastReplanAt` suppresses another replan during
the cooldown.

- [ ] **Step 2: Verify the tests fail for missing transition behavior**

Run: `python -m pytest tests/test_api.py -k "release_endpoint and stability" -q`

Expected: FAIL on the new stability assertions.

- [ ] **Step 3: Implement final-gate state transition**

Compute the final allowed value after inventory risks. Increment the previous
blocked count when false and reset it when true. Pass the resulting count and
the configured policy to `evaluate_release_stability`.

- [ ] **Step 4: Run API and full regression suites**

Run: `python -m pytest tests/test_api.py -q`

Expected: PASS.

Run: `python -m pytest -q`

Expected: all tests PASS with only the known environment warnings.

### Task 3: Runtime verification

**Files:**
- No source changes.

- [ ] **Step 1: Restart the service**

Restart Uvicorn on `127.0.0.1:8765` using the existing project command.

- [ ] **Step 2: Verify the workbench**

Request `http://127.0.0.1:8765/planner/workbench` and expect HTTP `200`.
