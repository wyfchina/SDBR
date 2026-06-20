# Release Deviation Stability Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a configurable business policy that monitors rope-release deviation and suppresses unnecessary Gurobi replanning.

**Architecture:** Create a focused `release_stability` module containing immutable input, policy, and result types plus a pure evaluation function. Keep the planner workbench and Gurobi adapter unchanged in this increment so the policy can be tested independently before API integration.

**Tech Stack:** Python dataclasses, datetime, pytest

---

### Task 1: Core deviation classification

**Files:**
- Create: `sdbr/release_stability.py`
- Create: `tests/test_release_stability.py`

- [ ] **Step 1: Write failing tests for tolerance and review classifications**

```python
def test_release_deviation_inside_tolerance_is_monitored():
    result = evaluate_release_stability(
        ReleaseStabilityInput(
            order_id="WO-1",
            planned_release_at=utc(8, 0),
            evaluated_release_at=utc(8, 20),
            gate_allowed=True,
        )
    )
    assert result.deviation_minutes == 20
    assert result.action == "Monitor"
    assert result.replan_required is False


def test_release_deviation_above_tolerance_requires_review():
    result = evaluate_release_stability(
        ReleaseStabilityInput(
            order_id="WO-1",
            planned_release_at=utc(8, 0),
            evaluated_release_at=utc(9, 0),
            gate_allowed=True,
        )
    )
    assert result.timing_status == "Late"
    assert result.action == "Review"
```

- [ ] **Step 2: Run the tests and verify missing-module failure**

Run: `python -m pytest tests/test_release_stability.py -q`

Expected: FAIL because `sdbr.release_stability` does not exist.

- [ ] **Step 3: Implement immutable contracts and pure classification**

Create `ReleaseStabilityPolicy`, `ReleaseStabilityInput`, and
`ReleaseStabilityResult` dataclasses. Implement signed minute deviation,
`Early`/`OnTime`/`Late` timing status, and `Monitor`/`Review` actions using the
policy tolerance.

- [ ] **Step 4: Run targeted tests**

Run: `python -m pytest tests/test_release_stability.py -q`

Expected: PASS.

### Task 2: Stable replan trigger

**Files:**
- Modify: `sdbr/release_stability.py`
- Modify: `tests/test_release_stability.py`

- [ ] **Step 1: Write failing tests for large delays, repeated blocking, and cooldown**

Test that a delay at the replan threshold returns `Replan`, that three
consecutive blocked gate checks return `Replan`, and that a recent prior replan
converts the action to `Review` with reason `ReplanCooldownActive`.

- [ ] **Step 2: Run tests and verify assertion failures**

Run: `python -m pytest tests/test_release_stability.py -q`

Expected: FAIL because replan and cooldown behavior are absent.

- [ ] **Step 3: Implement trigger and cooldown ordering**

Evaluate threshold and repeated blocking first. If either trigger is active,
check the elapsed minutes since `last_replan_at`; suppress replanning until the
configured cooldown has elapsed.

- [ ] **Step 4: Run targeted tests**

Run: `python -m pytest tests/test_release_stability.py -q`

Expected: PASS.

### Task 3: Policy validation and regression verification

**Files:**
- Modify: `sdbr/release_stability.py`
- Modify: `tests/test_release_stability.py`

- [ ] **Step 1: Write failing validation tests**

Cover negative tolerance, replan threshold below tolerance, blocked threshold
below one, negative blocked count, and mixed timezone awareness.

- [ ] **Step 2: Run tests and verify expected failures**

Run: `python -m pytest tests/test_release_stability.py -q`

Expected: FAIL because invalid inputs are accepted.

- [ ] **Step 3: Implement validation with stable `ValueError` messages**

Validate policy values in `ReleaseStabilityPolicy.__post_init__`, input counters
in `ReleaseStabilityInput.__post_init__`, and datetime compatibility before
subtracting timestamps.

- [ ] **Step 4: Run targeted and full test suites**

Run: `python -m pytest tests/test_release_stability.py -q`

Expected: PASS.

Run: `python -m pytest -q`

Expected: all tests PASS; the existing pytest cache permission warning may remain.
