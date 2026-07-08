# SDBR P1 Market Control Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build P1 S-DBR market-control capabilities: CCR planned load, MTO safe-date promise signals, MTA replenishment load visibility, unified buffer priority, and release-decision evidence without adding new DDAE protocol fields.

**Architecture:** Add one focused backend domain module for S-DBR market control, then wire it into existing schedule-result, release-management, dispatch, and UI read models. DDAE-owned parameters remain consumed from frozen configuration/runtime inputs; SDBR computes execution signals and feedback only.

**Tech Stack:** Python 3.11, FastAPI/Pydantic, OR-Tools CP-SAT existing path, plain HTML/CSS/JavaScript planner workbench, pytest.

## Global Constraints

- SDBR remains a DDOM / S-DBR execution system only: MRP/material feasibility, finite-capacity scheduling, release management, buffer execution, MES dispatch suggestions, execution feedback, variance capture, optional Simio validation.
- Do not implement DDS&OP workflows, scenario governance, master-setting approval, Buffer Profile governance, adjustment-factor approval, or strategic what-if simulation.
- DDAE-approved operating-model configuration must be received, validated, frozen, executed, and fed back; SDBR must not recalculate or govern DDAE-owned master parameters.
- Planning Run work must freeze `OperatingModelConfigurationID` and related configuration IDs already supported by `BE-RUN-010`.
- Time buffers, control points, DDMRP parameters, resource roles, and other DDAE-origin settings must be consumed according to the contract only; do not silently add DDAE fields.
- P1 first implementation must not require a new DDAE protocol. If structured CCR planned-load feedback is later required by DDAE, raise a Contract Agent change request after this internal read model is proven.
- OR-Tools CP-SAT remains the only active executable solver for new planning runs.
- Existing dirty worktree changes must not be reverted. Edit only files listed in the task being implemented.

---

## File Structure

- Create `sdbr/sdbr_market_control.py`: pure domain/read-model logic for CCR planned load, MTO safe date, MTA replenishment pressure, and unified buffer priority.
- Modify `sdbr/schedule_result_view.py`: include the new market-control package under existing `/planner/workbench/schedule-results/runs/{run_id}/workbench` without removing `SDBRFlowControl`.
- Modify `sdbr/work_order_release_view.py`: enrich release candidates with demand class and market-priority evidence; keep current gate rules intact.
- Modify `sdbr/dispatch_priority.py`: consume market-priority fields when present, while keeping release authorization and MES arrival gates as hard gates.
- Modify `sdbr/api.py`: add a small read-only endpoint only if schedule-result payload becomes too large; otherwise route through existing workbench endpoint.
- Modify `sdbr/web/planner-workbench.html`, `sdbr/web/planner-workbench.js`, `sdbr/web/planner-workbench.css`: show P1 market-control summary in business language.
- Modify `sdbr/test_data.py`: add a focused P1 fixture with MTO orders and one MTA replenishment order candidate; use existing resource/routing conventions.
- Create `tests/test_sdbr_market_control.py`: unit tests for new market-control functions.
- Modify `tests/test_api.py`: endpoint/read-model/UI static tests.
- Modify `tests/test_dispatch_priority.py`: verify unified priority still respects release and MES gates.
- Modify `docs/backend-specification.md`: add/advance BE capability records and changelog entry.
- Modify `docs/ui-specification.md`: add/advance UI records for schedule-result market-control visibility.

---

### Task 1: Specification And Boundary Update

**Files:**
- Modify: `docs/backend-specification.md`
- Modify: `docs/ui-specification.md`
- Test: `tests/test_api.py`

**Interfaces:**
- Consumes: existing spec sections for `BE-OUT-003`, `BE-UI-003`, `BE-DDMRP-006`, `BE-REL-011`, `BE-REL-012`, `BE-RUN-010`.
- Produces: explicit P1 acceptance language for later tasks.

- [ ] **Step 1: Add a backend spec test that fails until the spec records P1 scope**

Append this test to `tests/test_api.py` near the existing specification/static tests:

```python
def test_backend_spec_records_sdbr_p1_market_control_scope():
    spec = Path("docs/backend-specification.md").read_text(encoding="utf-8")
    assert "BE-SDBR-001" in spec
    assert "CCR planned load" in spec
    assert "MTO safe-date" in spec
    assert "MTA replenishment load" in spec
    assert "unified buffer priority" in spec
    assert "does not require a new DDAE protocol" in spec
```

- [ ] **Step 2: Run the targeted test and verify it fails**

Run: `pytest tests/test_api.py::test_backend_spec_records_sdbr_p1_market_control_scope -q`

Expected: FAIL because the new spec IDs and P1 wording are not present.

- [ ] **Step 3: Update backend specification**

In `docs/backend-specification.md`, add a new capability group after the DDMRP capability group:

```markdown
| `BE-SDBR-001` | CCR planned load read model | `[PARTIAL]` | `C` `sdbr/sdbr_market_control.py`; `A` `/planner/workbench/schedule-results/runs/{run_id}/workbench`; `T` `tests/test_sdbr_market_control.py`, `tests/test_api.py` | Combines MTO scheduled load and MTA replenishment load visibility for constraint/candidate-constraint resources. First implementation does not require a new DDAE protocol; it consumes frozen Planning Run configuration, executable schedule rows, and existing DDMRP runtime results. |
| `BE-SDBR-002` | MTO safe-date execution signal | `[PARTIAL]` | `C` `build_mto_safe_date_summary`; `T` `tests/test_sdbr_market_control.py` | Calculates execution-level promise signals from CCR load and frozen time-buffer policy. It does not let SDBR govern time-buffer master settings. |
| `BE-SDBR-003` | MTA replenishment load bridge | `[PARTIAL]` | `C` `build_mta_replenishment_load`; `T` `tests/test_sdbr_market_control.py` | Converts existing MTA replenishment orders and DDMRP replenishment suggestions into CCR load visibility where executable mapping exists; unmapped suggestions remain explicit issues rather than hidden load. |
| `BE-SDBR-004` | Unified MTO/MTA buffer priority | `[PARTIAL]` | `C` `build_unified_buffer_priority`; `A` release-management and dispatch read models; `T` `tests/test_sdbr_market_control.py`, `tests/test_dispatch_priority.py` | Uses MTO time-buffer and MTA stock-buffer status in a shared red/yellow/green priority scale while preserving release authorization and MES arrival gates. |
```

Add this changelog row:

```markdown
| 2.xx | 2026-07-09 | Start P1 S-DBR market-control scope: CCR planned load, MTO safe-date signal, MTA replenishment load visibility, and unified buffer priority. First round uses existing DDAE contracts and frozen runtime inputs; no new DDAE protocol is required. |
```

- [ ] **Step 4: Update UI specification**

In `docs/ui-specification.md`, add UI acceptance language under the schedule-results unit:

```markdown
- P1 S-DBR market-control panel shows CCR planned load, MTO safe-date signal, MTA replenishment load visibility, unified buffer priority, and the boundary "no new DDAE protocol required for this internal execution read model".
- The panel must not expose raw JSON, DDAE master-setting governance controls, or DDMRP parameter editors.
```

- [ ] **Step 5: Run the spec test again**

Run: `pytest tests/test_api.py::test_backend_spec_records_sdbr_p1_market_control_scope -q`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add docs/backend-specification.md docs/ui-specification.md tests/test_api.py
git commit -m "docs: define sdbr p1 market control scope"
```

---

### Task 2: Market-Control Domain Tests

**Files:**
- Create: `tests/test_sdbr_market_control.py`
- Create later: `sdbr/sdbr_market_control.py`

**Interfaces:**
- Consumes: no new production code yet.
- Produces expected interface:
  - `build_ccr_planned_load(*, gantt_rows: list[dict], resources: list[dict], orders: list[dict], ddmrp_lines: list[dict], horizon_start: datetime, horizon_days: int = 14, protective_capacity_target_percent: float = 80.0) -> dict`
  - `build_mto_safe_date_summary(*, ccr_planned_load: dict, time_buffer_minutes: int) -> dict`
  - `build_mta_replenishment_load(*, ddmrp_lines: list[dict], orders: list[dict]) -> dict`
  - `build_unified_buffer_priority(*, mto_candidates: list[dict], mta_lines: list[dict]) -> dict`

- [ ] **Step 1: Write the failing unit tests**

Create `tests/test_sdbr_market_control.py` with:

```python
from datetime import datetime, timezone

from sdbr.sdbr_market_control import (
    build_ccr_planned_load,
    build_mta_replenishment_load,
    build_mto_safe_date_summary,
    build_unified_buffer_priority,
)


def test_ccr_planned_load_splits_mto_and_mta_load():
    result = build_ccr_planned_load(
        gantt_rows=[
            {
                "ResourceID": "CCR-1",
                "Bars": [
                    {
                        "OrderID": "WO-MTO-1",
                        "OperationID": "DRUM",
                        "Start": "2026-07-10T08:00:00+00:00",
                        "End": "2026-07-10T10:00:00+00:00",
                        "DurationMinutes": 120,
                        "BarType": "Processing",
                    },
                    {
                        "OrderID": "WO-MTA-1",
                        "OperationID": "DRUM",
                        "Start": "2026-07-10T10:00:00+00:00",
                        "End": "2026-07-10T11:00:00+00:00",
                        "DurationMinutes": 60,
                        "BarType": "Processing",
                    },
                ],
            }
        ],
        resources=[
            {
                "ResourceID": "CCR-1",
                "Name": "Constraint",
                "IsConstraint": True,
                "DailyCapacityMinutes": {"2026-07-10": 240},
            }
        ],
        orders=[
            {"OrderID": "WO-MTO-1", "DemandClass": "MTO"},
            {"OrderID": "WO-MTA-1", "DemandClass": "MTA"},
        ],
        ddmrp_lines=[],
        horizon_start=datetime(2026, 7, 10, 0, 0, tzinfo=timezone.utc),
    )

    bucket = result["Buckets"][0]
    assert bucket["ResourceID"] == "CCR-1"
    assert bucket["MtoLoadMinutes"] == 120
    assert bucket["MtaLoadMinutes"] == 60
    assert bucket["TotalPlannedLoadMinutes"] == 180
    assert bucket["LoadPercent"] == 75.0
    assert result["Summary"]["Status"] == "Protected"


def test_ccr_planned_load_marks_near_limit_and_overload():
    result = build_ccr_planned_load(
        gantt_rows=[
            {
                "ResourceID": "CCR-1",
                "Bars": [
                    {
                        "OrderID": "WO-MTO-1",
                        "OperationID": "DRUM",
                        "Start": "2026-07-10T08:00:00+00:00",
                        "End": "2026-07-10T12:30:00+00:00",
                        "DurationMinutes": 270,
                        "BarType": "Processing",
                    }
                ],
            }
        ],
        resources=[
            {
                "ResourceID": "CCR-1",
                "Name": "Constraint",
                "IsConstraint": True,
                "DailyCapacityMinutes": {"2026-07-10": 240},
            }
        ],
        orders=[{"OrderID": "WO-MTO-1", "DemandClass": "MTO"}],
        ddmrp_lines=[],
        horizon_start=datetime(2026, 7, 10, 0, 0, tzinfo=timezone.utc),
    )

    assert result["Buckets"][0]["Status"] == "Overloaded"
    assert result["Summary"]["Status"] == "Overloaded"
    assert result["Summary"]["MaxLoadPercent"] == 112.5


def test_mto_safe_date_uses_first_protected_ccr_bucket_plus_half_buffer():
    planned_load = {
        "Buckets": [
            {
                "ResourceID": "CCR-1",
                "Date": "2026-07-10",
                "Status": "Overloaded",
                "LoadPercent": 112.5,
            },
            {
                "ResourceID": "CCR-1",
                "Date": "2026-07-11",
                "Status": "Protected",
                "LoadPercent": 70.0,
            },
        ]
    }

    summary = build_mto_safe_date_summary(
        ccr_planned_load=planned_load,
        time_buffer_minutes=480,
    )

    assert summary["Status"] == "Available"
    assert summary["EarliestSafeDate"] == "2026-07-11"
    assert summary["SafePromiseAt"] == "2026-07-11T04:00:00+00:00"
    assert summary["Rule"] == "FirstProtectedCcrBucketPlusHalfTimeBuffer"


def test_mta_replenishment_load_separates_mapped_and_unmapped_suggestions():
    result = build_mta_replenishment_load(
        ddmrp_lines=[
            {
                "ItemID": "FG-MTA",
                "LocationID": "MAIN",
                "PlanningStatus": "Red",
                "SuggestedReplenishmentQty": 20,
            },
            {
                "ItemID": "RM-UNMAPPED",
                "LocationID": "MAIN",
                "PlanningStatus": "Yellow",
                "SuggestedReplenishmentQty": 50,
            },
        ],
        orders=[
            {
                "OrderID": "WO-MTA-1",
                "ProductID": "FG-MTA",
                "DemandClass": "MTA",
                "Quantity": 20,
            }
        ],
    )

    assert result["MappedSuggestionCount"] == 1
    assert result["UnmappedSuggestionCount"] == 1
    assert result["Issues"][0]["Code"] == "MTA_REPLENISHMENT_EXECUTION_ORDER_MISSING"


def test_unified_buffer_priority_places_red_mto_and_mta_before_yellow():
    result = build_unified_buffer_priority(
        mto_candidates=[
            {
                "OrderID": "WO-MTO-YELLOW",
                "DemandClass": "MTO",
                "BufferZone": "Yellow",
                "BufferPenetrationPercent": 55,
                "SuggestedReleaseAt": "2026-07-10T08:00:00+00:00",
            }
        ],
        mta_lines=[
            {
                "ItemID": "FG-MTA",
                "LocationID": "MAIN",
                "PlanningStatus": "Red",
                "SuggestedReplenishmentQty": 20,
            }
        ],
    )

    rows = result["Rows"]
    assert rows[0]["DemandClass"] == "MTA"
    assert rows[0]["PriorityZone"] == "Red"
    assert rows[1]["DemandClass"] == "MTO"
    assert rows[1]["PriorityZone"] == "Yellow"
    assert result["Summary"]["RedCount"] == 1
```

- [ ] **Step 2: Run the tests and verify the import failure**

Run: `pytest tests/test_sdbr_market_control.py -q`

Expected: FAIL with `ModuleNotFoundError: No module named 'sdbr.sdbr_market_control'`.

- [ ] **Step 3: Commit the failing tests if working TDD branch policy allows red commits; otherwise keep unstaged until Task 3**

Preferred for this repository: do not commit red tests alone. Continue to Task 3 and commit with implementation.

---

### Task 3: Market-Control Domain Implementation

**Files:**
- Create: `sdbr/sdbr_market_control.py`
- Test: `tests/test_sdbr_market_control.py`

**Interfaces:**
- Consumes: plain dict rows from existing schedule, DDMRP, master data read models.
- Produces: `CCRPlannedLoad`, `MTOSafeDate`, `MTAReplenishmentLoad`, `UnifiedBufferPriority` dictionaries for Task 4 and Task 5.

- [ ] **Step 1: Implement the module**

Create `sdbr/sdbr_market_control.py`:

```python
from __future__ import annotations

from datetime import datetime, time, timedelta


PROTECTIVE_CAPACITY_TARGET_PERCENT = 80.0
PLANNED_LOAD_WARNING_PERCENT = 90.0
ZONE_RANK = {"Late": 0, "Red": 1, "Yellow": 2, "Green": 3, "AboveGreen": 4, "Early": 5}


def build_ccr_planned_load(
    *,
    gantt_rows: list[dict[str, object]],
    resources: list[dict[str, object]],
    orders: list[dict[str, object]],
    ddmrp_lines: list[dict[str, object]],
    horizon_start: datetime,
    horizon_days: int = 14,
    protective_capacity_target_percent: float = PROTECTIVE_CAPACITY_TARGET_PERCENT,
) -> dict[str, object]:
    resources_by_id = {str(item.get("ResourceID")): item for item in resources}
    orders_by_id = {str(item.get("OrderID")): item for item in orders}
    horizon_dates = {
        (horizon_start.date() + timedelta(days=offset)).isoformat()
        for offset in range(max(horizon_days, 1))
    }
    buckets: dict[tuple[str, str], dict[str, object]] = {}
    for resource in resources:
        resource_id = str(resource.get("ResourceID"))
        if not _is_controlled_resource(resource):
            continue
        for bucket_date, capacity in _daily_capacity(resource).items():
            if bucket_date not in horizon_dates:
                continue
            buckets[(resource_id, bucket_date)] = {
                "ResourceID": resource_id,
                "ResourceName": resource.get("Name") or resource.get("ResourceName") or resource_id,
                "Date": bucket_date,
                "CapacityMinutes": int(capacity),
                "MtoLoadMinutes": 0,
                "MtaLoadMinutes": 0,
                "TotalPlannedLoadMinutes": 0,
                "LoadPercent": 0.0,
                "Status": "Protected",
                "DemandBreakdown": [],
            }
    for row in gantt_rows:
        resource_id = str(row.get("ResourceID"))
        if resource_id not in resources_by_id or not _is_controlled_resource(resources_by_id[resource_id]):
            continue
        for bar in _dict_list(row.get("Bars")):
            if bar.get("BarType") not in {None, "Processing"}:
                continue
            start = _parse_datetime(bar.get("Start"))
            if start is None:
                continue
            bucket_date = start.date().isoformat()
            bucket = buckets.get((resource_id, bucket_date))
            if bucket is None:
                continue
            order_id = str(bar.get("OrderID"))
            demand_class = _demand_class(orders_by_id.get(order_id, {}))
            duration = int(bar.get("DurationMinutes", 0) or 0)
            if demand_class == "MTA":
                bucket["MtaLoadMinutes"] = int(bucket["MtaLoadMinutes"]) + duration
            else:
                bucket["MtoLoadMinutes"] = int(bucket["MtoLoadMinutes"]) + duration
            bucket["DemandBreakdown"].append(
                {
                    "OrderID": order_id,
                    "OperationID": bar.get("OperationID"),
                    "DemandClass": demand_class,
                    "DurationMinutes": duration,
                }
            )
    rows = []
    for bucket in buckets.values():
        total = int(bucket["MtoLoadMinutes"]) + int(bucket["MtaLoadMinutes"])
        capacity = int(bucket["CapacityMinutes"])
        load_percent = round(total / capacity * 100, 2) if capacity > 0 else 0.0
        bucket["TotalPlannedLoadMinutes"] = total
        bucket["LoadPercent"] = load_percent
        bucket["Status"] = _load_status(
            load_percent,
            protective_capacity_target_percent=protective_capacity_target_percent,
        )
        rows.append(bucket)
    rows.sort(key=lambda item: (str(item["Date"]), str(item["ResourceID"])))
    mapped_mta = build_mta_replenishment_load(ddmrp_lines=ddmrp_lines, orders=orders)
    max_load = max((float(item["LoadPercent"]) for item in rows), default=0.0)
    return {
        "Mode": "SDBRCCRPlannedLoadV1",
        "Boundary": "Consumes frozen schedule and externally configured runtime inputs; no new DDAE protocol is required for P1 internal read model.",
        "Policy": {
            "ProtectiveCapacityTargetPercent": protective_capacity_target_percent,
            "WarningPercent": PLANNED_LOAD_WARNING_PERCENT,
        },
        "Summary": {
            "Status": _summary_status(rows),
            "BucketCount": len(rows),
            "ConstraintResourceCount": len({item["ResourceID"] for item in rows}),
            "MtoLoadMinutes": sum(int(item["MtoLoadMinutes"]) for item in rows),
            "MtaLoadMinutes": sum(int(item["MtaLoadMinutes"]) for item in rows),
            "MaxLoadPercent": round(max_load, 2),
            "MappedMtaSuggestionCount": mapped_mta["MappedSuggestionCount"],
            "UnmappedMtaSuggestionCount": mapped_mta["UnmappedSuggestionCount"],
        },
        "Buckets": rows,
        "MTAReplenishmentLoad": mapped_mta,
    }


def build_mto_safe_date_summary(
    *,
    ccr_planned_load: dict[str, object],
    time_buffer_minutes: int,
) -> dict[str, object]:
    buckets = _dict_list(ccr_planned_load.get("Buckets"))
    protected = [
        bucket
        for bucket in buckets
        if bucket.get("Status") == "Protected"
    ]
    if not protected:
        return {
            "Status": "NeedsCapacityReview",
            "EarliestSafeDate": None,
            "SafePromiseAt": None,
            "Rule": "FirstProtectedCcrBucketPlusHalfTimeBuffer",
            "BusinessMeaning": "当前可见范围内没有低于保护负荷阈值的控制点能力窗口，接单前需要人工产能评审。",
        }
    first = min(protected, key=lambda item: (str(item.get("Date")), str(item.get("ResourceID"))))
    safe_date = str(first["Date"])
    half_buffer = max(int(time_buffer_minutes / 2), 0)
    safe_promise_at = datetime.combine(
        datetime.fromisoformat(safe_date).date(),
        time.min,
        tzinfo=_first_tzinfo_from_buckets(buckets),
    ) + timedelta(minutes=half_buffer)
    return {
        "Status": "Available",
        "EarliestSafeDate": safe_date,
        "SafePromiseAt": safe_promise_at.isoformat(),
        "Rule": "FirstProtectedCcrBucketPlusHalfTimeBuffer",
        "BusinessMeaning": "以第一个受保护控制点负荷窗口加半个时间缓冲作为执行层安全承诺信号。",
    }


def build_mta_replenishment_load(
    *,
    ddmrp_lines: list[dict[str, object]],
    orders: list[dict[str, object]],
) -> dict[str, object]:
    mta_orders_by_product = {
        str(order.get("ProductID")): order
        for order in orders
        if _demand_class(order) == "MTA"
    }
    mapped = []
    issues = []
    for line in ddmrp_lines:
        suggested_qty = float(line.get("SuggestedReplenishmentQty") or 0)
        if suggested_qty <= 0:
            continue
        item_id = str(line.get("ItemID"))
        order = mta_orders_by_product.get(item_id)
        if order is None:
            issues.append(
                {
                    "Code": "MTA_REPLENISHMENT_EXECUTION_ORDER_MISSING",
                    "Severity": "Warning",
                    "ItemID": item_id,
                    "LocationID": line.get("LocationID"),
                    "BusinessMeaning": "该 DDMRP 补货建议没有对应的执行级补货工单，因此不隐式写入 CCR 负荷。",
                }
            )
            continue
        mapped.append(
            {
                "ItemID": item_id,
                "LocationID": line.get("LocationID"),
                "OrderID": order.get("OrderID"),
                "SuggestedReplenishmentQty": suggested_qty,
                "PlanningStatus": line.get("PlanningStatus"),
            }
        )
    return {
        "Mode": "MTAReplenishmentLoadBridgeV1",
        "MappedSuggestionCount": len(mapped),
        "UnmappedSuggestionCount": len(issues),
        "MappedSuggestions": mapped,
        "Issues": issues,
    }


def build_unified_buffer_priority(
    *,
    mto_candidates: list[dict[str, object]],
    mta_lines: list[dict[str, object]],
) -> dict[str, object]:
    rows = []
    for candidate in mto_candidates:
        zone = str(candidate.get("BufferZone") or "Green")
        rows.append(
            {
                "DemandClass": "MTO",
                "BusinessObjectID": candidate.get("OrderID"),
                "PriorityZone": zone,
                "PenetrationPercent": float(candidate.get("BufferPenetrationPercent") or 0),
                "SuggestedReleaseAt": candidate.get("SuggestedReleaseAt"),
                "RecommendedAction": candidate.get("RecommendedAction"),
            }
        )
    for line in mta_lines:
        if float(line.get("SuggestedReplenishmentQty") or 0) <= 0:
            continue
        zone = str(line.get("PlanningStatus") or "Green")
        rows.append(
            {
                "DemandClass": "MTA",
                "BusinessObjectID": f"{line.get('ItemID')}@{line.get('LocationID')}",
                "ItemID": line.get("ItemID"),
                "LocationID": line.get("LocationID"),
                "PriorityZone": zone,
                "PenetrationPercent": _mta_penetration(line),
                "SuggestedReplenishmentQty": line.get("SuggestedReplenishmentQty"),
                "RecommendedAction": line.get("RecommendedAction") or "Replenish",
            }
        )
    rows.sort(
        key=lambda item: (
            ZONE_RANK.get(str(item.get("PriorityZone")), 9),
            -float(item.get("PenetrationPercent") or 0),
            str(item.get("SuggestedReleaseAt") or ""),
            str(item.get("BusinessObjectID") or ""),
        )
    )
    for index, row in enumerate(rows, start=1):
        row["PriorityRank"] = index
    return {
        "Mode": "UnifiedMtoMtaBufferPriorityV1",
        "Summary": {
            "TotalCount": len(rows),
            "RedCount": sum(1 for item in rows if item["PriorityZone"] == "Red"),
            "YellowCount": sum(1 for item in rows if item["PriorityZone"] == "Yellow"),
            "GreenCount": sum(1 for item in rows if item["PriorityZone"] == "Green"),
        },
        "Rows": rows,
    }


def _is_controlled_resource(resource: dict[str, object]) -> bool:
    return bool(resource.get("IsConstraint")) or bool(resource.get("IsCandidateConstraint"))


def _daily_capacity(resource: dict[str, object]) -> dict[str, int]:
    raw = resource.get("DailyCapacityMinutes")
    if isinstance(raw, dict):
        return {str(day): int(minutes or 0) for day, minutes in raw.items()}
    calendar = resource.get("Calendar")
    if isinstance(calendar, dict):
        return {}
    return {}


def _demand_class(order: dict[str, object]) -> str:
    raw = (
        order.get("DemandClass")
        or order.get("DemandType")
        or order.get("OrderType")
        or order.get("PlanningMode")
    )
    if str(raw).upper() in {"MTA", "MAKE_TO_AVAILABILITY", "STOCK_REPLENISHMENT", "REPLENISHMENT"}:
        return "MTA"
    return "MTO"


def _load_status(
    load_percent: float,
    *,
    protective_capacity_target_percent: float,
) -> str:
    if load_percent > 100:
        return "Overloaded"
    if load_percent > PLANNED_LOAD_WARNING_PERCENT:
        return "NearLimit"
    if load_percent > protective_capacity_target_percent:
        return "Watch"
    return "Protected"


def _summary_status(rows: list[dict[str, object]]) -> str:
    statuses = {str(item.get("Status")) for item in rows}
    if "Overloaded" in statuses:
        return "Overloaded"
    if "NearLimit" in statuses:
        return "NearLimit"
    if "Watch" in statuses:
        return "Watch"
    return "Protected"


def _parse_datetime(value: object) -> datetime | None:
    if isinstance(value, datetime):
        return value
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _first_tzinfo_from_buckets(buckets: list[dict[str, object]]):
    for bucket in buckets:
        for item in _dict_list(bucket.get("DemandBreakdown")):
            value = _parse_datetime(item.get("Start"))
            if value is not None:
                return value.tzinfo
    return datetime.now().astimezone().tzinfo


def _mta_penetration(line: dict[str, object]) -> float:
    top_of_green = float(line.get("TopOfGreen") or 0)
    net_flow = float(line.get("NetFlowPosition") or 0)
    if top_of_green <= 0:
        return 0.0
    return round(max(0.0, min(100.0, (top_of_green - net_flow) / top_of_green * 100)), 2)


def _dict_list(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]
```

- [ ] **Step 2: Run unit tests**

Run: `pytest tests/test_sdbr_market_control.py -q`

Expected: PASS.

- [ ] **Step 3: Fix timezone helper if needed**

If `test_mto_safe_date_uses_first_protected_ccr_bucket_plus_half_buffer` returns local timezone instead of UTC, replace `_first_tzinfo_from_buckets` with:

```python
from datetime import timezone


def _first_tzinfo_from_buckets(buckets: list[dict[str, object]]):
    return timezone.utc
```

Run: `pytest tests/test_sdbr_market_control.py -q`

Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add sdbr/sdbr_market_control.py tests/test_sdbr_market_control.py
git commit -m "feat: add sdbr market control read model"
```

---

### Task 4: Schedule Result Integration

**Files:**
- Modify: `sdbr/schedule_result_view.py`
- Modify: `tests/test_api.py`

**Interfaces:**
- Consumes: `build_ccr_planned_load`, `build_mto_safe_date_summary`, `build_unified_buffer_priority`.
- Produces: `ScheduleResultWorkbench["SDBRMarketControl"]`.

- [ ] **Step 1: Add failing API test**

Append to `tests/test_api.py` near the schedule-results tests:

```python
def test_schedule_results_returns_p1_market_control_summary():
    client = _client_with_test_data()

    response = client.get("/planner/workbench/schedule-results/runs/RUN-RESULT/workbench")

    assert response.status_code == 200
    data = response.json()["Data"]
    market = data["SDBRMarketControl"]
    assert market["CCRPlannedLoad"]["Mode"] == "SDBRCCRPlannedLoadV1"
    assert "MtoLoadMinutes" in market["CCRPlannedLoad"]["Summary"]
    assert "MtaLoadMinutes" in market["CCRPlannedLoad"]["Summary"]
    assert market["MTOSafeDate"]["Rule"] == "FirstProtectedCcrBucketPlusHalfTimeBuffer"
    assert market["UnifiedBufferPriority"]["Mode"] == "UnifiedMtoMtaBufferPriorityV1"
    assert market["Boundary"]["RequiresNewDdaeProtocol"] is False
```

- [ ] **Step 2: Run the test and verify failure**

Run: `pytest tests/test_api.py::test_schedule_results_returns_p1_market_control_summary -q`

Expected: FAIL because `SDBRMarketControl` is missing.

- [ ] **Step 3: Import the market-control builders**

At the top of `sdbr/schedule_result_view.py`, add:

```python
from sdbr.sdbr_market_control import (
    build_ccr_planned_load,
    build_mto_safe_date_summary,
    build_unified_buffer_priority,
)
```

- [ ] **Step 4: Build and attach market control**

Inside `build_schedule_result_workbench`, after `system_load, resource_load = _build_load_views(...)`, add:

```python
    ddmrp_lines = _dict_list(master_data_version.get("DdmrpRuntimeLines"))
    ccr_planned_load = build_ccr_planned_load(
        gantt_rows=_dict_list(gantt.get("Rows")),
        resources=_dict_list(master_data_version.get("Resources")),
        orders=_dict_list(master_data_version.get("Orders")),
        ddmrp_lines=ddmrp_lines,
        horizon_start=_parse_datetime(gantt["Range"].get("Start"))
        or _parse_datetime(schedule.get("GeneratedAt"))
        or datetime.now().astimezone(),
    )
    mto_safe_date = build_mto_safe_date_summary(
        ccr_planned_load=ccr_planned_load,
        time_buffer_minutes=effective_rope_buffer_minutes(
            release_policy=(
                planning_run.get("FrozenReleasePolicy")
                if isinstance(planning_run.get("FrozenReleasePolicy"), dict)
                else None
            ),
            fallback_time_buffer_minutes=int(planning_run.get("TimeBufferMinutes", 0)),
        ),
    )
    unified_priority = build_unified_buffer_priority(
        mto_candidates=_dict_list(schedule.get("BufferBoard")),
        mta_lines=ddmrp_lines,
    )
```

Then add this key to the returned dict:

```python
        "SDBRMarketControl": {
            "Boundary": {
                "RequiresNewDdaeProtocol": False,
                "BusinessMeaning": "P1 first round consumes existing frozen configuration, schedule output and DDMRP runtime data; it does not add DDAE-owned master parameters.",
            },
            "CCRPlannedLoad": ccr_planned_load,
            "MTOSafeDate": mto_safe_date,
            "UnifiedBufferPriority": unified_priority,
        },
```

- [ ] **Step 5: Run targeted API test**

Run: `pytest tests/test_api.py::test_schedule_results_returns_p1_market_control_summary -q`

Expected: PASS.

- [ ] **Step 6: Run existing schedule-result tests**

Run: `pytest tests/test_api.py -q -k "schedule_result or SDBRFlowControl" --basetemp .tmp/pytest-p1-schedule -p no:cacheprovider`

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add sdbr/schedule_result_view.py tests/test_api.py
git commit -m "feat: expose sdbr p1 market control on schedule results"
```

---

### Task 5: Release And Dispatch Priority Integration

**Files:**
- Modify: `sdbr/work_order_release_view.py`
- Modify: `sdbr/dispatch_priority.py`
- Modify: `tests/test_dispatch_priority.py`
- Modify: `tests/test_api.py`

**Interfaces:**
- Consumes: release candidates with existing `BufferZone`, `BufferPenetrationPercent`, and optional master order `DemandClass`.
- Produces: `DemandClass`, `MarketPriorityRank`, `MarketPriorityReason`, and consistent sorting fields.

- [ ] **Step 1: Add failing release-management API test**

Append to `tests/test_api.py` near release-management tests:

```python
def test_release_management_candidates_include_market_priority_evidence():
    client = _client_with_test_data()

    response = client.get("/planner/workbench/release-management/runs/RUN-RESULT/workbench")

    assert response.status_code == 200
    candidates = response.json()["Data"]["Candidates"]
    assert candidates
    assert "DemandClass" in candidates[0]
    assert "MarketPriorityRank" in candidates[0]
    assert "MarketPriorityReason" in candidates[0]
```

- [ ] **Step 2: Add failing dispatch test**

Append to `tests/test_dispatch_priority.py`:

```python
def test_dispatch_priority_preserves_market_priority_fields():
    queue = build_mes_dispatch_priority_queue(
        planning_run=_planning_run(),
        master_data_version=_master_data(),
        release_workbench={
            "OperationalStateSnapshotID": "OPS-LATEST",
            "Candidates": [
                {
                    **_candidate("WO-A", "Red", 95),
                    "DemandClass": "MTO",
                    "MarketPriorityRank": 1,
                    "MarketPriorityReason": "红区 MTO 工单，优先保护市场承诺",
                }
            ],
        },
        authorizations=[_authorization("AUTH-A", "WO-A")],
        execution_events=[_event("ArrivedBuffer", "WO-A", "OP-A")],
        evaluated_at=datetime(2026, 6, 16, 9, tzinfo=timezone.utc),
    )

    row = queue["Resources"][0]["Queue"][0]
    assert row["DemandClass"] == "MTO"
    assert row["MarketPriorityRank"] == 1
    assert row["MarketPriorityReason"] == "红区 MTO 工单，优先保护市场承诺"
```

- [ ] **Step 3: Run both tests and verify failure**

Run: `pytest tests/test_api.py::test_release_management_candidates_include_market_priority_evidence tests/test_dispatch_priority.py::test_dispatch_priority_preserves_market_priority_fields -q`

Expected: FAIL because the fields are missing.

- [ ] **Step 4: Enrich release candidates in `sdbr/work_order_release_view.py`**

Inside `build_release_management_workbench`, before the `for candidate in candidates:` loop, add:

```python
    schedule_orders = {
        str(item.get("OrderID")): item
        for item in _dict_list(_dict(planning_run.get("Schedule")).get("ScheduledOrders"))
    }
```

Inside the loop, before `enriched.append`, add:

```python
        demand_class = str(
            schedule_orders.get(order_id, {}).get("DemandClass")
            or candidate.get("DemandClass")
            or "MTO"
        )
        market_reason = _market_priority_reason(
            demand_class=demand_class,
            zone=zone,
            penetration=penetration,
        )
```

Add these fields in the appended dict:

```python
                "DemandClass": demand_class,
                "MarketPriorityReason": market_reason,
```

After ranking `ExecutionPriority`, also set:

```python
        item["MarketPriorityRank"] = rank
```

Add helper:

```python
def _market_priority_reason(*, demand_class: str, zone: str, penetration: float) -> str:
    class_label = "MTA补货" if demand_class == "MTA" else "MTO工单"
    if zone in {"Late", "Red"}:
        return f"{zone} 区 {class_label}，渗透率 {penetration:.2f}%，优先保护市场承诺"
    if zone == "Yellow":
        return f"黄区 {class_label}，进入释放关注窗口"
    return f"绿区 {class_label}，保持观察"
```

- [ ] **Step 5: Preserve fields in `sdbr/dispatch_priority.py`**

In the row dict built inside `build_mes_dispatch_priority_queue`, add:

```python
                "DemandClass": candidate.get("DemandClass") or "MTO",
                "MarketPriorityRank": candidate.get("MarketPriorityRank"),
                "MarketPriorityReason": candidate.get("MarketPriorityReason"),
```

In `_suggestion_row`, add:

```python
        "DemandClass": row.get("DemandClass"),
        "MarketPriorityRank": row.get("MarketPriorityRank"),
        "MarketPriorityReason": row.get("MarketPriorityReason"),
```

- [ ] **Step 6: Run targeted tests**

Run: `pytest tests/test_api.py::test_release_management_candidates_include_market_priority_evidence tests/test_dispatch_priority.py::test_dispatch_priority_preserves_market_priority_fields -q`

Expected: PASS.

- [ ] **Step 7: Run release/dispatch regression**

Run: `pytest tests/test_dispatch_priority.py tests/test_release_candidates.py tests/test_release_authorization.py -q`

Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add sdbr/work_order_release_view.py sdbr/dispatch_priority.py tests/test_api.py tests/test_dispatch_priority.py
git commit -m "feat: propagate unified market priority to release and dispatch"
```

---

### Task 6: P1 Fixture And Acceptance Case

**Files:**
- Modify: `sdbr/test_data.py`
- Modify: `tests/test_test_data.py`
- Modify: `tests/test_api.py`

**Interfaces:**
- Consumes: baseline resource/routing/order conventions.
- Produces: a stable `TST-P1-MARKET-CONTROL` case that shows MTO/MTA load and unified priority without production claims.

- [ ] **Step 1: Add failing fixture test**

Append to `tests/test_test_data.py`:

```python
def test_p1_market_control_case_contains_mto_and_mta_orders():
    store = WorkbenchStateStore()
    seed_test_data(store)
    mdv = store.master_data_versions["TST-P1-MDV-MARKET-CONTROL-20260709"]
    demand_classes = {row["OrderID"]: row.get("DemandClass") for row in mdv["Orders"]}
    assert "MTO" in demand_classes.values()
    assert "MTA" in demand_classes.values()
    assert any(row.get("DemandClass") == "MTA" for row in mdv["Orders"])
```

- [ ] **Step 2: Run the test and verify failure**

Run: `pytest tests/test_test_data.py::test_p1_market_control_case_contains_mto_and_mta_orders -q`

Expected: FAIL because the fixture does not exist.

- [ ] **Step 3: Add P1 fixture IDs**

In `sdbr/test_data.py`, add constants near the other test IDs:

```python
P1_MARKET_CONTROL_MASTER_DATA_VERSION_ID = "TST-P1-MDV-MARKET-CONTROL-20260709"
P1_MARKET_CONTROL_RUN_ID = "TST-P1-RUN-MARKET-CONTROL-20260709"
```

- [ ] **Step 4: Add P1 master data seed**

Add a function:

```python
def _seed_p1_market_control_case(store: WorkbenchStateStore) -> None:
    resources = _baseline_resources()
    routings = _baseline_routings()
    orders = _baseline_orders()
    order_rows = _orders_to_dict(orders)
    order_rows[0]["DemandClass"] = "MTO"
    order_rows[1]["DemandClass"] = "MTO"
    order_rows[2]["DemandClass"] = "MTA"
    order_rows[2]["OrderType"] = "StockReplenishment"
    inventory_buffers = _baseline_inventory_buffers()
    store.master_data_versions[P1_MARKET_CONTROL_MASTER_DATA_VERSION_ID] = {
        "VersionID": P1_MARKET_CONTROL_MASTER_DATA_VERSION_ID,
        "Status": "Published",
        "SourceSystem": "SDBR-P1-TestData",
        "ImportedAt": datetime(2026, 7, 9, 8, tzinfo=timezone.utc).isoformat(),
        "Orders": order_rows,
        "Resources": _resources_to_dict(resources),
        "Routings": _routings_to_dict(routings),
        "InventoryBuffers": _inventory_buffers_to_dict(inventory_buffers),
        "MaterialRequirements": [
            item.to_dict() for item in _baseline_material_requirements(orders)
        ],
        "DdmrpRuntimeLines": [
            {
                "ItemID": "TST-FG-C",
                "LocationID": "TST-MAIN",
                "PlanningStatus": "Red",
                "SuggestedReplenishmentQty": 1,
                "NetFlowPosition": 40,
                "TopOfGreen": 100,
                "RecommendedAction": "Replenish",
            }
        ],
    }
    store.planning_runs[P1_MARKET_CONTROL_RUN_ID] = _pending_run_record(
        run_id=P1_MARKET_CONTROL_RUN_ID,
        snapshot_id="TST-OPS-BASELINE-20260619",
        requested_at=datetime(2026, 7, 9, 8, tzinfo=timezone.utc),
        master_data_version_id=P1_MARKET_CONTROL_MASTER_DATA_VERSION_ID,
        problem_id="TST-P1-PROBLEM-MARKET-CONTROL",
        time_buffer_minutes=480,
    )
```

Call `_seed_p1_market_control_case(store)` inside `seed_test_data` after baseline data is seeded.

- [ ] **Step 5: Run fixture test**

Run: `pytest tests/test_test_data.py::test_p1_market_control_case_contains_mto_and_mta_orders -q`

Expected: PASS.

- [ ] **Step 6: Add API acceptance test that executes P1 run and checks market control**

Append to `tests/test_api.py`:

```python
def test_p1_market_control_case_executes_and_returns_mto_mta_load():
    client = _client_with_test_data()

    execute = client.post(
        "/planner/workbench/planning-runs/TST-P1-RUN-MARKET-CONTROL-20260709/execute",
        json={"ExecutedBy": "pytest"},
    )
    assert execute.status_code == 200

    response = client.get(
        "/planner/workbench/schedule-results/runs/TST-P1-RUN-MARKET-CONTROL-20260709/workbench"
    )
    assert response.status_code == 200
    market = response.json()["Data"]["SDBRMarketControl"]
    assert market["CCRPlannedLoad"]["Summary"]["MtoLoadMinutes"] > 0
    assert market["CCRPlannedLoad"]["Summary"]["MtaLoadMinutes"] > 0
    assert market["CCRPlannedLoad"]["Summary"]["MappedMtaSuggestionCount"] >= 1
```

- [ ] **Step 7: Run targeted P1 case test**

Run: `pytest tests/test_api.py::test_p1_market_control_case_executes_and_returns_mto_mta_load -q`

Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add sdbr/test_data.py tests/test_test_data.py tests/test_api.py
git commit -m "test: add p1 market control acceptance case"
```

---

### Task 7: UI Business Panel

**Files:**
- Modify: `sdbr/web/planner-workbench.html`
- Modify: `sdbr/web/planner-workbench.js`
- Modify: `sdbr/web/planner-workbench.css`
- Modify: `tests/test_api.py`

**Interfaces:**
- Consumes: `SDBRMarketControl` from schedule-result workbench.
- Produces: business-friendly read-only P1 panel in schedule results.

- [ ] **Step 1: Add failing static UI test**

Append to `tests/test_api.py` near UI schedule-result tests:

```python
def test_schedule_results_page_exposes_p1_market_control_panel():
    html = Path("sdbr/web/planner-workbench.html").read_text(encoding="utf-8")
    script = Path("sdbr/web/planner-workbench.js").read_text(encoding="utf-8")
    css = Path("sdbr/web/planner-workbench.css").read_text(encoding="utf-8")

    assert 'id="sdbr-market-control-panel"' in html
    assert "renderSdbrMarketControl" in script
    assert "CCR planned load" not in html
    assert ".market-control-grid" in css
```

- [ ] **Step 2: Run and verify failure**

Run: `pytest tests/test_api.py::test_schedule_results_page_exposes_p1_market_control_panel -q`

Expected: FAIL because panel elements are missing.

- [ ] **Step 3: Add HTML panel**

In `sdbr/web/planner-workbench.html`, inside the schedule results view after the KPI area and before detailed tabs, add:

```html
<section id="sdbr-market-control-panel" class="panel market-control-panel" hidden>
  <div class="panel-heading">
    <div>
      <span class="panel-kicker" data-i18n="sdbrMarketControlKicker">S-DBR 运行控制</span>
      <h2 data-i18n="sdbrMarketControlTitle">市场承诺与约束保护</h2>
    </div>
  </div>
  <div class="market-control-grid">
    <article>
      <span data-i18n="ccrPlannedLoad">约束计划负荷</span>
      <strong id="market-control-load-status">-</strong>
      <p id="market-control-load-detail" class="muted">-</p>
    </article>
    <article>
      <span data-i18n="mtoSafeDate">MTO安全承诺</span>
      <strong id="market-control-safe-date">-</strong>
      <p id="market-control-safe-date-detail" class="muted">-</p>
    </article>
    <article>
      <span data-i18n="mtaReplenishmentLoad">MTA补货负荷</span>
      <strong id="market-control-mta-load">-</strong>
      <p id="market-control-mta-detail" class="muted">-</p>
    </article>
    <article>
      <span data-i18n="unifiedBufferPriority">统一缓冲优先级</span>
      <strong id="market-control-priority-count">-</strong>
      <p id="market-control-priority-detail" class="muted">-</p>
    </article>
  </div>
  <p class="boundary-note" data-i18n="marketControlBoundary">
    本区使用已冻结配置、排程结果和 DDMRP 运行输入，不新增 DDAE 主参数协议。
  </p>
</section>
```

- [ ] **Step 4: Add translations**

In `sdbr/web/planner-workbench.js`, add translation keys in both Chinese and English dictionaries:

```javascript
sdbrMarketControlKicker: "S-DBR 运行控制",
sdbrMarketControlTitle: "市场承诺与约束保护",
ccrPlannedLoad: "约束计划负荷",
mtoSafeDate: "MTO安全承诺",
mtaReplenishmentLoad: "MTA补货负荷",
unifiedBufferPriority: "统一缓冲优先级",
marketControlBoundary: "本区使用已冻结配置、排程结果和 DDMRP 运行输入，不新增 DDAE 主参数协议。",
```

English:

```javascript
sdbrMarketControlKicker: "S-DBR flow control",
sdbrMarketControlTitle: "Market promise and constraint protection",
ccrPlannedLoad: "Constraint planned load",
mtoSafeDate: "MTO safe promise",
mtaReplenishmentLoad: "MTA replenishment load",
unifiedBufferPriority: "Unified buffer priority",
marketControlBoundary: "This panel consumes frozen configuration, schedule output, and DDMRP runtime input. It does not add DDAE-governed master parameters.",
```

- [ ] **Step 5: Add render function**

In `sdbr/web/planner-workbench.js`, add:

```javascript
function renderSdbrMarketControl(data) {
  const panel = document.getElementById("sdbr-market-control-panel");
  if (!panel) return;
  const market = data && data.SDBRMarketControl;
  if (!market) {
    panel.hidden = true;
    return;
  }
  panel.hidden = false;
  const load = market.CCRPlannedLoad || {};
  const loadSummary = load.Summary || {};
  const safeDate = market.MTOSafeDate || {};
  const priority = market.UnifiedBufferPriority || {};
  const prioritySummary = priority.Summary || {};
  const mta = (load.MTAReplenishmentLoad || {});
  setText("market-control-load-status", businessLoadStatus(loadSummary.Status));
  setText(
    "market-control-load-detail",
    `MTO ${loadSummary.MtoLoadMinutes || 0} 分钟 · MTA ${loadSummary.MtaLoadMinutes || 0} 分钟 · 最高负荷 ${formatPercent(loadSummary.MaxLoadPercent || 0)}`
  );
  setText("market-control-safe-date", safeDate.EarliestSafeDate || "需要产能评审");
  setText("market-control-safe-date-detail", safeDate.BusinessMeaning || "");
  setText("market-control-mta-load", `${mta.MappedSuggestionCount || 0} 条已映射`);
  setText(
    "market-control-mta-detail",
    `${mta.UnmappedSuggestionCount || 0} 条补货建议缺少执行映射`
  );
  setText("market-control-priority-count", `${prioritySummary.TotalCount || 0} 条`);
  setText(
    "market-control-priority-detail",
    `红区 ${prioritySummary.RedCount || 0} · 黄区 ${prioritySummary.YellowCount || 0} · 绿区 ${prioritySummary.GreenCount || 0}`
  );
}

function businessLoadStatus(status) {
  if (status === "Overloaded") return "超出保护能力";
  if (status === "NearLimit") return "接近上限";
  if (status === "Watch") return "需要关注";
  return "受保护";
}
```

Call `renderSdbrMarketControl(data);` in the schedule-result render path immediately after KPI rendering.

- [ ] **Step 6: Add CSS**

In `sdbr/web/planner-workbench.css`, add:

```css
.market-control-panel {
  margin-top: 16px;
}

.market-control-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  border: 1px solid var(--border-color);
  border-radius: 8px;
  overflow: hidden;
}

.market-control-grid article {
  padding: 14px 16px;
  border-right: 1px solid var(--border-color);
  min-width: 0;
}

.market-control-grid article:last-child {
  border-right: 0;
}

.market-control-grid span {
  display: block;
  color: var(--muted-text);
  font-size: 13px;
  margin-bottom: 6px;
}

.market-control-grid strong {
  display: block;
  color: var(--text-color);
  font-size: 22px;
  line-height: 1.25;
}

.market-control-grid p {
  margin: 6px 0 0;
  font-size: 13px;
}

@media (max-width: 900px) {
  .market-control-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 560px) {
  .market-control-grid {
    grid-template-columns: 1fr;
  }

  .market-control-grid article {
    border-right: 0;
    border-bottom: 1px solid var(--border-color);
  }
}
```

- [ ] **Step 7: Run static UI test**

Run: `pytest tests/test_api.py::test_schedule_results_page_exposes_p1_market_control_panel -q`

Expected: PASS.

- [ ] **Step 8: Run syntax check**

Run: `node --check sdbr/web/planner-workbench.js`

Expected: exit code 0.

- [ ] **Step 9: Commit**

```bash
git add sdbr/web/planner-workbench.html sdbr/web/planner-workbench.js sdbr/web/planner-workbench.css tests/test_api.py
git commit -m "feat: show sdbr p1 market control panel"
```

---

### Task 8: Final Verification And Acceptance Notes

**Files:**
- Modify: `docs/backend-specification.md`
- Modify: `docs/ui-specification.md`

**Interfaces:**
- Consumes: all previous task outputs.
- Produces: repeatable acceptance evidence and known boundaries.

- [ ] **Step 1: Add final backend acceptance note**

In `docs/backend-specification.md`, add an acceptance record:

```markdown
### BE-SDBR-001 至 BE-SDBR-004 P1 市场控制验收记录

- 日期：2026-07-09
- 状态变更：`BE-SDBR-001` 至 `BE-SDBR-004` 保持 `[PARTIAL]`，完成第一轮内部执行 read model 和 UI 证据。
- 实现证据：`sdbr/sdbr_market_control.py` 生成 CCR planned load、MTO safe-date signal、MTA replenishment load bridge 和 unified buffer priority；`sdbr/schedule_result_view.py` 在排程结果 read model 中返回 `SDBRMarketControl`；释放和派工 read model 保留 release/MES gates 并补充市场优先级证据。
- 测试证据：`tests/test_sdbr_market_control.py`、`tests/test_api.py`、`tests/test_dispatch_priority.py`。
- 边界：本轮不新增 DDAE 协议；不配置或审批 DDAE 主参数；不声明正式承诺交期；MTA 补货建议缺少执行工单映射时只输出 issue，不隐式写入 CCR 负荷。
```

- [ ] **Step 2: Add final UI acceptance note**

In `docs/ui-specification.md`, add:

```markdown
### P1 S-DBR 市场控制 UI 验收记录

- 日期：2026-07-09
- 排程结果页展示“市场承诺与约束保护”只读面板，包含约束计划负荷、MTO 安全承诺、MTA 补货负荷和统一缓冲优先级。
- UI 不提供 DDAE 主参数编辑、DDMRP 参数配置或 Buffer Profile 治理入口。
- 状态：已验证待用户确认。
```

- [ ] **Step 3: Run targeted verification**

Run:

```bash
python -m compileall -q sdbr
pytest tests/test_sdbr_market_control.py tests/test_dispatch_priority.py -q
pytest tests/test_api.py -q -k "sdbr_p1 or market_control or schedule_results_returns_p1 or release_management_candidates_include_market_priority or schedule_results_page_exposes_p1" --basetemp .tmp/pytest-p1-market-control -p no:cacheprovider
node --check sdbr/web/planner-workbench.js
```

Expected: all commands exit 0.

- [ ] **Step 4: Run full regression if time allows**

Run:

```bash
pytest -q --basetemp .tmp/pytest-full-p1-market-control -p no:cacheprovider
```

Expected: PASS. If unrelated dirty-worktree tests fail, record exact failures in the final report and do not change unrelated files.

- [ ] **Step 5: Commit**

```bash
git add docs/backend-specification.md docs/ui-specification.md
git commit -m "docs: record sdbr p1 market control acceptance"
```

---

## Self-Review

**Spec coverage:** The plan covers CCR planned load, MTO safe-date signal, MTA replenishment load visibility, unified buffer priority, release/dispatch propagation, UI visibility, and explicit DDAE boundary.

**Placeholder scan:** The plan avoids unresolved placeholder markers, hidden future fields, and "add tests later" phrasing. Every task contains exact files, commands, and expected outcomes.

**Type consistency:** The new module consistently produces dictionaries consumed by schedule-result, release-management, dispatch, and UI. Function names match across tasks: `build_ccr_planned_load`, `build_mto_safe_date_summary`, `build_mta_replenishment_load`, and `build_unified_buffer_priority`.

**Known implementation caution:** Task 4 must pass actual `gantt["Rows"]`, not raw schedule `GanttRows`, because `schedule_result_view._build_gantt` enriches bars with `BarType` and time-buffer/maintenance bars. Task 6 may require adding `ScheduledOrders` to the schedule output or using `master_data_version["Orders"]` directly if the existing schedule does not contain order demand classes.
