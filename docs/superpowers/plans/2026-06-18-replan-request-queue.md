# Replan Request Queue Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn release stability replan recommendations into deduplicated pending review requests that can be queried through the API.

**Architecture:** Add a storage-independent domain module that creates deterministic replan requests. Use a small in-memory list inside `create_app` as the current repository adapter and expose it through the existing release response and a read-only queue endpoint.

**Tech Stack:** Python dataclasses, hashlib, FastAPI, pytest

---

### Task 1: Replan request domain model

**Files:**
- Create: `sdbr/replanning.py`
- Create: `tests/test_replanning.py`

- [ ] **Step 1: Write failing domain tests**

Test that `create_replan_request` produces a `PendingReview` request with a
stable ID when `replan_required=True`, produces the same ID for identical
inputs, and returns `None` when replanning is not required.

- [ ] **Step 2: Verify the missing-module failure**

Run: `python -m pytest tests/test_replanning.py -q`

Expected: FAIL because `sdbr.replanning` does not exist.

- [ ] **Step 3: Implement the immutable model and deterministic factory**

Use SHA-256 over problem ID, order ID, planned release ISO timestamp, and reason
code; expose the first 16 hexadecimal characters with prefix `RPL-`.

- [ ] **Step 4: Verify domain tests pass**

Run: `python -m pytest tests/test_replanning.py -q`

Expected: PASS.

### Task 2: API queue integration

**Files:**
- Modify: `sdbr/api.py`
- Modify: `tests/test_api.py`

- [ ] **Step 1: Write failing API tests**

Test that a third blocked release returns `Data.ReplanRequest`, the queue GET
endpoint contains that request, a repeated identical release does not duplicate
it, and an allowed release returns `ReplanRequest: null`.

- [ ] **Step 2: Verify the new assertions fail**

Run: `python -m pytest tests/test_api.py -k "replan_request" -q`

Expected: FAIL because the request and endpoint are absent.

- [ ] **Step 3: Implement queue creation, serialization, and GET endpoint**

Create requests only for `ReplanRequired`; append only when the deterministic
ID is not already present. Return the request in the release response and all
requests from `GET /planner/workbench/replan-requests`.

- [ ] **Step 4: Run targeted, API, and full tests**

Run: `python -m pytest tests/test_api.py -k "replan_request" -q`

Run: `python -m pytest tests/test_api.py -q`

Run: `python -m pytest -q`

Expected: all tests PASS with only known environment warnings.

### Task 3: Runtime verification

**Files:**
- No source changes.

- [ ] **Step 1: Restart Uvicorn and verify workbench HTTP 200**

- [ ] **Step 2: Submit a replan-triggering release twice and verify the queue contains one request**
