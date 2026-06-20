# Replan Request Decision Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an auditable approve/reject state machine for pending replan requests without invoking the solver.

**Architecture:** Keep transition rules in the immutable `replanning` domain module using dataclass replacement. Add one constrained decision command endpoint that replaces the matching request in the current queue adapter and maps domain conflicts to HTTP responses.

**Tech Stack:** Python dataclasses, FastAPI, Pydantic, pytest

---

### Task 1: Domain decision state machine

**Files:**
- Modify: `sdbr/replanning.py`
- Modify: `tests/test_replanning.py`

- [ ] **Step 1: Write failing tests for approve and reject transitions**

Assert that approval returns `Approved` with actor and timestamp, rejection
returns `Rejected` with its required comment, rejection without a comment raises
`ValueError`, and deciding a non-pending request raises `ValueError`.

- [ ] **Step 2: Verify tests fail because the transition is absent**

Run: `python -m pytest tests/test_replanning.py -q`

- [ ] **Step 3: Add nullable audit fields and implement `decide_replan_request`**

Use `dataclasses.replace`; accept only `Approve` and `Reject`, require a trimmed
comment for rejection, and reject requests whose status is not `PendingReview`.

- [ ] **Step 4: Verify domain tests pass**

Run: `python -m pytest tests/test_replanning.py -q`

### Task 2: Decision API

**Files:**
- Modify: `sdbr/api.py`
- Modify: `tests/test_api.py`

- [ ] **Step 1: Write failing endpoint tests**

Create a queued request through the release endpoint, approve it, and verify the
queue record changes. Add tests for unknown IDs, rejection without comment, and
a repeated decision conflict.

- [ ] **Step 2: Verify the new endpoint tests fail**

Run: `python -m pytest tests/test_api.py -k "replan_request_decision" -q`

- [ ] **Step 3: Implement payload, endpoint, serialization, and error mapping**

Use a `Literal["Approve", "Reject"]` payload decision. Replace the queue item
on success; return `404` for missing ID and `409` for domain transition errors.

- [ ] **Step 4: Run targeted, API, and full tests**

Run: `python -m pytest tests/test_api.py -k "replan_request_decision" -q`

Run: `python -m pytest tests/test_api.py -q`

Run: `python -m pytest -q`

### Task 3: Runtime verification

**Files:**
- No source changes.

- [ ] **Step 1: Restart Uvicorn and verify workbench HTTP 200**

- [ ] **Step 2: Trigger and approve a request through HTTP; verify queue status is `Approved`**
