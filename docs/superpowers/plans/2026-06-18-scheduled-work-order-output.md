# Scheduled Work Order Output Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Provide completed replan schedules as flat scheduled work order operation rows.

**Architecture:** Add a pure schedule output mapper that flattens schedule `GanttRows`. Store completed execution schedule snapshots in the API adapter and expose a read endpoint that returns flat rows only for completed requests.

**Tech Stack:** Python, FastAPI, pytest

---

### Task 1: Schedule output mapper

**Files:**
- Create: `sdbr/schedule_output.py`
- Create: `tests/test_schedule_output.py`

- [ ] **Step 1: Write failing mapper tests**

Test that rows are flattened from two resources and sorted by start time,
resource, and operation.

- [ ] **Step 2: Run tests and verify missing module failure**

Run: `python -m pytest tests/test_schedule_output.py -q`

- [ ] **Step 3: Implement `scheduled_work_order_rows_from_schedule`**

Read `GanttRows[*].Bars[*]`, attach resource ID, preserve ISO timestamps, and
sort rows deterministically.

- [ ] **Step 4: Verify mapper tests pass**

Run: `python -m pytest tests/test_schedule_output.py -q`

### Task 2: API snapshot and output endpoint

**Files:**
- Modify: `sdbr/api.py`
- Modify: `tests/test_api.py`

- [ ] **Step 1: Write failing API tests**

Execute an approved request and fetch scheduled work orders. Add tests for an
unknown request and for a pending request with no completed schedule output.

- [ ] **Step 2: Run tests and verify failures**

Run: `python -m pytest tests/test_api.py -k "scheduled_work_orders" -q`

- [ ] **Step 3: Store completed snapshots and implement GET endpoint**

Add `replan_schedule_snapshots` inside `create_app`. Save the schedule only when
the final request status is `Completed`. Return flattened operations through the
new endpoint.

- [ ] **Step 4: Run targeted, API, and full tests**

Run: `python -m pytest tests/test_api.py -k "scheduled_work_orders" -q`

Run: `python -m pytest tests/test_api.py -q`

Run: `python -m pytest -q`

### Task 3: Runtime verification

**Files:**
- No source changes.

- [ ] **Step 1: Restart Uvicorn**

- [ ] **Step 2: Trigger, approve, execute, and fetch scheduled work orders through HTTP**
