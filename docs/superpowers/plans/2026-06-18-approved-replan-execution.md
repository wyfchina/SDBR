# Approved Replan Execution Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Execute approved replan requests against a fresh snapshot using Gurobi and record the outcome.

**Architecture:** Extend the immutable request with execution audit fields and pure start/finish transitions. Add a synchronous API adapter that validates request state and snapshot identity, runs the existing calculation path with Gurobi, and replaces the queue record with its final state.

**Tech Stack:** Python dataclasses, FastAPI, Gurobi adapter, pytest

---

### Task 1: Execution state machine

**Files:**
- Modify: `sdbr/replanning.py`
- Modify: `tests/test_replanning.py`

- [ ] **Step 1: Write failing transition tests**

Test starting an approved request, successful finish for `Optimal`, failed finish
for `Infeasible`, start rejection for non-approved requests, and finish rejection
for non-running requests.

- [ ] **Step 2: Run tests and verify missing functions fail**

Run: `python -m pytest tests/test_replanning.py -q`

- [ ] **Step 3: Implement execution fields and pure transitions**

Add start/completion timestamps, backend, solver status, and solver message.
Implement `start_replan_execution` and `finish_replan_execution` with strict
state checks and `Optimal/Feasible` success mapping.

- [ ] **Step 4: Verify domain tests pass**

Run: `python -m pytest tests/test_replanning.py -q`

### Task 2: Gurobi execution endpoint

**Files:**
- Modify: `sdbr/api.py`
- Modify: `tests/test_api.py`

- [ ] **Step 1: Write failing endpoint tests**

Cover non-approved rejection, problem mismatch, non-Gurobi backend rejection,
and approved execution using the real configured Gurobi adapter. Accept
`Completed` when solver status is `Optimal/Feasible`; otherwise require `Failed`.

- [ ] **Step 2: Verify endpoint tests fail**

Run: `python -m pytest tests/test_api.py -k "replan_execution" -q`

- [ ] **Step 3: Implement synchronous execution and serialization**

Validate request and snapshot before changing state. Set `Running`, calculate
through `_calculate_workbench_data`, finish from `SolverStatus` and
`SolverMessage`, replace the queue item, and return request plus schedule.

- [ ] **Step 4: Run targeted, API, and full tests**

Run: `python -m pytest tests/test_api.py -k "replan_execution" -q`

Run: `python -m pytest tests/test_api.py -q`

Run: `python -m pytest -q`

### Task 3: Runtime verification

**Files:**
- No source changes.

- [ ] **Step 1: Restart Uvicorn and verify workbench HTTP 200**

- [ ] **Step 2: Trigger, approve, and execute through HTTP; verify final solver and request statuses**
