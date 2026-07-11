# MTO Order Commitment Workflow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an automatic CCR-first MTO order commitment assessment that returns a recommendation, lets a planner make the explicit decision, and atomically activates the existing shared demand, CCR capacity reservation, and material planning allocation ledgers without accepting an external order or mutating production systems.

**Architecture:** A canonical Mock API intake immediately creates an immutable, idempotent shadow assessment against one completed and Approved/Published baseline Planning Run, its frozen master/calendar/configuration references, active shared reservations, and one operational-state snapshot. Pure domain modules own the window-level CCR shadow scheduler, material feasibility, recommendation, confirmation guards, and sanitized read models; FastAPI only resolves repository state and applies the existing Phase 0 reservation write set under the current revision-controlled state boundary. The approved option-2 planner flow ends at `AcceptedPendingFormalSchedule`: it never creates a Planning Run, changes a master-data version, accepts the customer order in an external system, or writes ERP/MES production state.

**Tech Stack:** Python 3.11+, FastAPI, Pydantic `AwareDatetime`, existing dataclass scheduling models, `WorkbenchStateStore` / `SQLiteWorkbenchStateStore`, pytest, vanilla HTML/CSS/JavaScript planner workbench.

## Global Constraints

- Cite `BE-SDBR-006` through `BE-SDBR-010`, `BE-RUN-011`, and `UI-COMMIT-001` in changed tests and acceptance evidence.
- Update `docs/backend-specification.md` and `docs/ui-specification.md` before implementation code; do not mark either new item verified until repeatable evidence exists.
- SDBR remains a DDOM / S-DBR execution system. Do not add DDS&OP workflows, DDAE parameter governance, Buffer Profile governance, or strategic scenario governance.
- Do not modify `D:\Documents\DDAE_INTERFACE_CONTRACT`, `sdbr/ddsop_contracts.py`, or any DDAE schema. The current MTO adapter must return the explicit `80.0%` reference policy with `Source="ReferenceFallback"` and `Approved=false`; it must never reinterpret an uncontracted field as an approved CCR threshold.
- A reference threshold can never produce the ordinary `RecommendAccept` result. It always sets `RequiresCcrAcknowledgement=true`, even when projected load is at or below 80%.
- Order intake performs the assessment automatically. Intake and re-evaluation create no `DemandCommitment`, reservation batch, capacity reservation, material allocation, Planning Run, integration message, or external order.
- Every acceptance is a planner action. On-time capacity above an approved threshold requires an explicit CCR-risk acknowledgement and non-empty reason.
- Material checking defaults to enabled. Disabling it requires a non-empty reason, produces no `MaterialPlanningAllocation`, records pending material requirements, and does not weaken the existing release-stage material hard gate.
- Material evidence that is missing, stale, or insufficient cannot be accepted as material-feasible.
- The approved option-2 workflow is: automatic assessment -> planner detail review -> optional audited re-evaluation -> explicit confirmation dialog -> revision-guarded decision -> atomic shared reservation activation -> `AcceptedPendingFormalSchedule`.
- Acceptance does not create or modify a Planning Run. A later, explicit Planning Run may select the resulting `ReservationBatchID` through the existing `PlanningRunPayload.PlanningReservationBatchIDs` interface and `BE-RUN-011` bridge.
- Acceptance does not append the MTO order to a master-data version. Formal scheduling still requires a valid planning input containing the order and an explicit selected reservation batch.
- No endpoint may claim external customer-order acceptance, production ERP/WMS allocation, MES dispatch, or formal schedule publication.
- Keep OR-Tools CP-SAT as the only executable solver for formal Planning Runs. The CCR-first assessment is a deterministic window-level shadow calculation and does not call CP-SAT, Gurobi, or Simio.
- First-scope shadow scheduling uses one published primary route, each operation's primary resource, non-split operations, and date/shift windows. Alternate resources may only make the conservative result better; they are shown as unused options. A relevant nonzero sequence-dependent setup rule that cannot be tied to an exact predecessor must return structured `CCR_SETUP_LOAD_REQUIRES_REVIEW` and cannot produce an acceptance action.
- Preserve all history. Re-evaluation creates a new immutable evaluation and supersedes only an undecided prior evaluation; accepted or rejected evidence is not overwritten.
- Do not expose raw master-data, operational-state, DDAE, evaluation, or reservation JSON in the planner workflow. Technical IDs and fingerprints belong in collapsed technical details.
- Do not touch `nofinish/`.

---

## Option-2 Workflow Contract

1. `POST /planner/workbench/order-commitments/intake` receives a canonical MTO line plus a completed, Approved/Published `BaselinePlanningRunID` and immediately evaluates it.
2. The persisted evaluation contains the order content fingerprint, relevant-state basis fingerprint, CCR window evidence, material evidence, recommendation, threshold source, and allowed planner actions.
3. `GET /planner/workbench/order-commitments/workbench` and `GET /planner/workbench/order-commitments/{evaluation_id}` return sanitized list/detail projections and the current `X-Workbench-Revision`.
4. A planner may call `POST /planner/workbench/order-commitments/{evaluation_id}/reevaluate` to refresh evidence or opt out of material checking with a reason. This creates a new evaluation ID and retains the old evidence.
5. A planner calls `POST /planner/workbench/order-commitments/{evaluation_id}/decision` with `If-Match`, the evaluation fingerprint, a stable `DecisionID`, a permitted decision code, a reason, and any required acknowledgements.
6. Acceptance builds one canonical `MTOCustomerOrder` demand and invokes `prepare_reservation_confirmation` plus `apply_reservation_write_set`. The evaluation decision, demand, batch, CCR rows, optional material rows, and audit events persist together or all roll back.
7. The response and UI display `AcceptedPendingFormalSchedule`, the accepted promise, and reservation batch identity. They explicitly display `ExternalOrderAcceptance="NotPerformed"` and `ProductionMutation="NotPerformed"`.
8. Rejection records the planner decision and creates no shared demand or reservation objects.

---

## File Structure

- Create `sdbr/ccr_shadow_scheduler.py`
  - Pure date/shift-capacity-window scheduler for primary-route CCR operations.
  - Counts completed-schedule processing load plus active Phase 0 capacity reservations.
  - Produces requested-date and earliest-safe candidates without changing the schedule.
- Create `sdbr/order_commitment_evaluation.py`
  - Canonical MTO input, fingerprints, material feasibility, recommendation, evaluation registration, supersession, planner-decision guards, and Phase 0 confirmation preparation.
- Create `sdbr/order_commitment_view.py`
  - Sanitized list and detail projections for the planner workbench.
- Modify `sdbr/sdbr_market_control.py`
  - Promote the existing CCR load-status classifier to the shared public `classify_ccr_load` interface used by market control and shadow scheduling.
- Modify `sdbr/state_store.py`
  - Persist `order_commitment_evaluations` and `order_commitment_events`; include them in restore, clear, health counts, rollback snapshots, and SQLite round trips.
- Modify `sdbr/api.py`
  - Add Pydantic payloads, reference resolution, automatic intake/re-evaluation, read endpoints, revision-guarded planner decision, auth coverage, and atomic calls into Phase 0.
- Modify `sdbr/web/planner-workbench.html`
  - Add the independent Order Commitments navigation route, dense workbench table, detail drawer, material re-evaluation controls, and option-2 confirmation dialog.
- Modify `sdbr/web/planner-workbench.js`
  - Add bilingual copy, route/load/render state, `X-Workbench-Revision` capture, `If-Match` decisions, acknowledgement validation, and refresh behavior.
- Modify `sdbr/web/planner-workbench.css`
  - Add restrained table/detail/dialog layouts and desktop/narrow-screen rules.
- Create `tests/test_ccr_shadow_scheduler.py`
  - CCR sequence, repeated visits, threshold, physical capacity, later safe promise, calendars, and malformed-input tests.
- Create `tests/test_order_commitment_evaluation.py`
  - Material default/opt-out, recommendation matrix, fingerprints, idempotency, supersession, decision guards, and Phase 0 write-set tests.
- Create `tests/test_order_commitment_view.py`
  - Sanitization, summary, source/status, audit, and technical-details tests.
- Modify `tests/test_state_store.py`
  - SQLite round-trip, clear, health count, and rollback coverage for the two new collections.
- Modify `tests/test_sdbr_market_control.py`
  - Shared classifier regression and unchanged planned-load behavior.
- Modify `tests/test_api.py`
  - End-to-end API, auth, revision, concurrency, rollback, no-external-mutation, and static UI acceptance tests.
- Modify `docs/backend-specification.md`
  - Add `BE-SDBR-010`, acceptance evidence, remaining boundaries, and dated change-log entries.
- Modify `docs/ui-specification.md`
  - Add `UI-COMMIT-001`, acceptance unit 13, option-2 interaction details, status/evidence, and dated change-log entries.

The implementation must reuse these existing interfaces without creating parallel ledgers:

```python
create_demand_commitment -> dict[str, object]
prepare_reservation_confirmation -> PlanningReservationWriteSet
apply_reservation_write_set -> None
reservation_load_by_bucket -> dict[tuple[str, str], dict[str, object]]
planning_allocated_qty_for_other_demands -> float
freeze_planning_reservations -> dict[str, object]
```

---

### Task 1: Specification First

**Files:**
- Modify: `docs/backend-specification.md`
- Modify: `docs/ui-specification.md`

**Interfaces:**
- Consumes: current `BE-SDBR-001` through `BE-SDBR-009`, `BE-RUN-011`, UI status definitions in section 1, and the implementation-order gate in UI section 16.
- Produces: `BE-SDBR-010` and `UI-COMMIT-001`, which every new backend/UI test must cite.

- [ ] **Step 1: Add the backend capability before writing code**

Update the backend document header to version `2.74` and date `2026-07-11`; leave its document-status wording unchanged.

Add this row immediately after `BE-SDBR-009`:

```markdown
| `BE-SDBR-010` | Automatic MTO order commitment evaluation and planner decision | `[NOT-STARTED]` | `D` `docs/superpowers/specs/2026-07-10-sdbr-order-commitment-evaluation-design.md`; planned `C` `sdbr/ccr_shadow_scheduler.py`, `sdbr/order_commitment_evaluation.py`; planned `A` `/planner/workbench/order-commitments/*`; planned `T` `tests/test_ccr_shadow_scheduler.py`, `tests/test_order_commitment_evaluation.py`, `tests/test_api.py` | Canonical new-order intake must automatically perform a CCR-first shadow assessment against completed schedule load plus active shared reservations, default to material checking, return recommendation only, and require an explicit planner decision. Approved-threshold exceedance and the 80% reference fallback require acknowledgement. Acceptance must reuse `BE-SDBR-006` through `BE-SDBR-009`, end at `AcceptedPendingFormalSchedule`, and must not accept an external order, create a Planning Run, or mutate ERP/MES. |
```

Do not change `BE-SDBR-006` through `BE-SDBR-009` or `BE-RUN-011` to `[VERIFIED]`. They remain `[PARTIAL]` because MTA workflow, formal-order authority, and complete external closure remain outside this task.

- [ ] **Step 2: Add the backend start record and change log**

Add before section 18:

```markdown
### BE-SDBR-010 MTO 订单承诺评估启动记录

- 日期：2026-07-11
- 范围：真实 MTO 新订单进入自动 CCR-first 影子评估；系统只返回建议，计划员通过独立工作台决定接受建议日期、条件接受或拒绝。
- 保护线：当前 DDAE 契约不扩展字段；第一轮 API 只使用明确标记的 `80.0% ReferenceFallback`，因此不得返回普通“建议接受”，接受前必须确认风险。
- 物料：默认检查共享未承诺可用量；计划员关闭检查时必须填写原因，只登记待确认物料需求，不创建已分配声明，且不绕过释放阶段物料硬门控。
- 确认：复用共享 `DemandCommitment`、`PlanningReservationBatch`、`CCRCapacityReservation` 和 `MaterialPlanningAllocation`；结束状态为 `AcceptedPendingFormalSchedule`。
- 边界：不自动接受外部客户订单，不创建 Planning Run，不修改主数据版本，不写 ERP/WMS/MES，不新增 DDAE 契约字段。
- 状态：`[NOT-STARTED]`，待实现与重复测试证据。
```

Add the next backend change-log row:

```markdown
| 2.74 | 2026-07-11 | 启动 `BE-SDBR-010` MTO 订单承诺工作流：新订单自动进行 CCR-first 影子评估，默认检查物料，计划员按 option-2 显式确认后写入共享预留；不扩展 DDAE 契约、不自动接受外部订单、不修改 ERP/MES |
```

- [ ] **Step 3: Add the independent UI specification**

Update the UI document header to version `5.35` and date `2026-07-11`; do not rewrite the statuses of existing acceptance units.

Insert this page specification after `UI-DDMRP-002` and before the Planning Run pages:

```markdown
### UI-COMMIT-001 MTO 订单承诺评估工作台

**状态：未开始**

- 独立一级导航为“订单承诺 / Order Commitments”，不放入创建排程向导，也不替代排程结果 What-if。
- 默认列表显示订单、产品、请求交期、建议安全日期、CCR、负荷前后、保护线来源、物料状态、建议、预留状态和异常状态。
- 详情显示路线/CCR 负荷依据、日期或班次候选、物料证据、配置/日历/快照引用和审计历史；技术 ID 与 fingerprint 只放在折叠技术详情中。
- “检查物料计划可用性”默认开启。关闭时必须填写原因，并持续显示“物料待确认”和“释放阶段仍执行物料硬门控”。
- option-2 接受流程固定为：查看建议 -> 选择允许动作 -> 打开影响明确的确认对话框 -> 完成 CCR/物料风险确认 -> 提交 revision-guarded 决定 -> 显示“已接受，待正式排程”。
- 普通建议、保护线超限、80%参考保护线、跳过物料、物料证据不足和建议调整交期必须使用不同文字状态；颜色不能是唯一表达。
- 保护线超限或参考保护线必须勾选风险确认并填写原因；跳过物料的条件接受必须再次确认物料仍待处理。
- 接受或拒绝都必须由计划员触发。页面不得显示或暗示外部订单已接受、Planning Run 已创建、ERP/WMS 已分配或 MES 已下发。
- `409 StateStoreRevisionConflict` 或 `OrderCommitmentEvaluationStale` 显示“数据已更新，需要重新评估”，不得静默重试或覆盖。
- 列表/详情必须有加载、空、错误和窄屏状态；正常工作流不得显示原始 JSON。
```

- [ ] **Step 4: Add UI acceptance unit 13 and change log**

Append this row to section 16:

```markdown
| 13 | MTO 订单承诺评估 | UI-COMMIT-001 | 是 |
```

Add before UI section 18:

```markdown
### 17.13 第十三验收单元记录

- 规格：`UI-COMMIT-001`
- 后台依赖：`BE-SDBR-006` 至 `BE-SDBR-010`、`BE-RUN-011`
- 日期：2026-07-11
- 范围：独立订单承诺工作台、自动评估结果、默认物料检查、带原因的物料跳过、option-2 计划员确认和共享预留状态。
- 边界：不创建 Planning Run，不自动接受外部订单，不修改 ERP/WMS/MES，不新增 DDAE 字段，不显示原始 JSON。
- 状态：未开始。
```

Add the next UI change-log row:

```markdown
| 5.35 | 2026-07-11 | 启动 `UI-COMMIT-001` 独立 MTO 订单承诺评估工作台：自动 CCR-first 建议、默认物料检查、带原因的物料跳过、option-2 计划员确认和共享预留状态；不自动接受外部订单或修改生产系统 |
```

- [ ] **Step 5: Verify IDs, statuses, and boundaries**

Run:

```powershell
rg -n "BE-SDBR-010|UI-COMMIT-001|17\.13|2\.74|5\.35|AcceptedPendingFormalSchedule|ReferenceFallback" docs/backend-specification.md docs/ui-specification.md
```

Expected: both IDs, both `[NOT-STARTED]` / `未开始` states, both change-log rows, the acceptance unit, and all scope boundaries are present.

- [ ] **Step 6: Commit specification targets**

```powershell
git add -- docs/backend-specification.md docs/ui-specification.md
git commit -m "docs: specify MTO order commitment workflow"
```

---

### Task 2: CCR-First Shadow Scheduler

**Files:**
- Create: `sdbr/ccr_shadow_scheduler.py`
- Create: `tests/test_ccr_shadow_scheduler.py`
- Modify: `sdbr/sdbr_market_control.py`
- Modify: `tests/test_sdbr_market_control.py`

**Interfaces:**
- Consumes:
  - `Routing`, `Resource`, and `Operation` from `sdbr.planner_workbench`.
  - `CapacityBucket` and `SetupTransition` from `sdbr.scheduling_solver`.
  - completed schedule `GanttRows` with processing `Start`, `End`, `OrderID`, and `OperationID`.
  - active Phase 0 capacity rows with exact `WindowStartAt`, `WindowEndAt`, `ReservedMinutes`, `ResourceID`, and active status.
- Produces:
  - `classify_ccr_load(*, load_percent: float, protective_capacity_target_percent: float) -> str` in `sdbr.sdbr_market_control`.
  - `evaluate_ccr_shadow_schedule(*, order_id: str, quantity: float, routing: Routing | None, resources: list[Resource], capacity_buckets: list[CapacityBucket], setup_transitions: list[SetupTransition], gantt_rows: list[dict[str, object]], active_capacity_reservations: list[dict[str, object]], requested_due_at: datetime, evaluated_at: datetime, downstream_protection_minutes: int, protection_threshold_percent: float) -> dict[str, object]`.
  - Output keys `Mode`, `Status`, `RequestedDueAt`, `LatestCcrCompletionAt`, `RequestedDateAssessment`, `EarliestSafeAssessment`, `SelectedAssessment`, `Issues`, and `Summary`.
  - Each selected assessment produces Phase 0-ready `ReservationRequests` with exact `ReservationLineID`, `OrderID`, `OperationID`, `ResourceID`, `WindowStartAt`, `WindowEndAt`, `ReservedMinutes`, and `LatestAllowedCompletionAt`.

- [ ] **Step 1: Write failing shared-classifier tests**

Add to `tests/test_sdbr_market_control.py`:

```python
# BE-SDBR-001 / BE-SDBR-010
from sdbr.sdbr_market_control import classify_ccr_load


def test_classify_ccr_load_uses_the_existing_market_control_thresholds():
    assert classify_ccr_load(
        load_percent=80.0,
        protective_capacity_target_percent=80.0,
    ) == "Protected"
    assert classify_ccr_load(
        load_percent=80.01,
        protective_capacity_target_percent=80.0,
    ) == "Watch"
    assert classify_ccr_load(
        load_percent=95.0,
        protective_capacity_target_percent=80.0,
    ) == "NearLimit"
    assert classify_ccr_load(
        load_percent=100.01,
        protective_capacity_target_percent=80.0,
    ) == "Overloaded"
```

Run:

```powershell
pytest tests/test_sdbr_market_control.py -q -k "classify_ccr_load" --basetemp .tmp/pytest-mto-load-classifier-red -p no:cacheprovider
```

Expected: FAIL because `classify_ccr_load` is not public yet.

- [ ] **Step 2: Promote one load classifier without changing P1 behavior**

In `sdbr/sdbr_market_control.py`, replace the private `_load_status` call and definition with:

```python
def classify_ccr_load(
    *,
    load_percent: float,
    protective_capacity_target_percent: float,
) -> str:
    if load_percent > 100:
        return "Overloaded"
    if load_percent > PLANNED_LOAD_WARNING_PERCENT:
        return "NearLimit"
    if load_percent > protective_capacity_target_percent:
        return "Watch"
    return "Protected"
```

Call it from `build_ccr_planned_load` with keyword arguments. Do not alter `PROTECTIVE_CAPACITY_TARGET_PERCENT`, `PLANNED_LOAD_WARNING_PERCENT`, bucket totals, or P1 response fields.

- [ ] **Step 3: Write failing shadow-schedule tests**

Create `tests/test_ccr_shadow_scheduler.py` with deterministic aware datetimes and these helpers/tests:

```python
"""Acceptance evidence for BE-SDBR-010."""

from datetime import datetime, timezone

import pytest

from sdbr.ccr_shadow_scheduler import evaluate_ccr_shadow_schedule
from sdbr.planner_workbench import Operation, Resource, Routing
from sdbr.scheduling_solver import CapacityBucket, SetupTransition


UTC = timezone.utc


def _resource(*, capacity_units: int = 1, efficiency_percent: int = 100) -> Resource:
    return Resource(
        resource_id="CCR-1",
        name="Constraint",
        is_constraint=True,
        daily_capacity_minutes={},
        capacity_units=capacity_units,
        efficiency_percent=efficiency_percent,
    )


def _routing(*, repeated_visit: bool = False) -> Routing:
    operations = [
        Operation("PREP", "NCR-1", 20, 10),
        Operation("CCR-CUT", "CCR-1", 60, 20, setup_family="FG-1"),
        Operation("PACK", "NCR-2", 30, 30),
    ]
    if repeated_visit:
        operations.insert(2, Operation("CCR-INSPECT", "CCR-1", 30, 25))
    return Routing(product_id="FG-1", routing_id="PRIMARY", operations=operations)


def _bucket(day: int, *, capacity: int = 480) -> CapacityBucket:
    return CapacityBucket(
        resource_id="CCR-1",
        bucket_start=datetime(2026, 7, day, 8, tzinfo=UTC),
        bucket_end=datetime(2026, 7, day, 16, tzinfo=UTC),
        capacity_minutes=capacity,
    )


def _evaluate(**overrides: object) -> dict[str, object]:
    arguments: dict[str, object] = {
        "order_id": "SO-100:10",
        "quantity": 1.0,
        "routing": _routing(),
        "resources": [_resource(), Resource("NCR-1", "Prep", False, {}), Resource("NCR-2", "Pack", False, {})],
        "capacity_buckets": [_bucket(20), _bucket(21)],
        "setup_transitions": [],
        "gantt_rows": [],
        "active_capacity_reservations": [],
        "requested_due_at": datetime(2026, 7, 20, 18, tzinfo=UTC),
        "evaluated_at": datetime(2026, 7, 20, 7, tzinfo=UTC),
        "downstream_protection_minutes": 60,
        "protection_threshold_percent": 80.0,
    }
    arguments.update(overrides)
    return evaluate_ccr_shadow_schedule(**arguments)  # type: ignore[arg-type]


def test_on_time_window_returns_phase0_ready_reservation_request():
    result = _evaluate()

    assert result["Status"] == "OnTime"
    selected = result["SelectedAssessment"]
    assert selected["PromiseAt"] == "2026-07-20T18:00:00+00:00"
    assert selected["ThresholdExceeded"] is False
    assert selected["ReservationRequests"] == [{
        "ReservationLineID": "SO-100:10:CCR-CUT:2026-07-20T08:00:00+00:00",
        "OrderID": "SO-100:10",
        "OperationID": "SO-100:10:CCR-CUT",
        "ResourceID": "CCR-1",
        "WindowStartAt": "2026-07-20T08:00:00+00:00",
        "WindowEndAt": "2026-07-20T16:00:00+00:00",
        "ReservedMinutes": 60,
        "LatestAllowedCompletionAt": "2026-07-20T16:00:00+00:00",
    }]


def test_on_time_physical_fit_above_protection_threshold_requires_review():
    result = _evaluate(
        gantt_rows=[{
            "ResourceID": "CCR-1",
            "Bars": [{
                "BarType": "Processing",
                "OrderID": "WO-EXISTING",
                "OperationID": "WO-EXISTING:CCR",
                "Start": "2026-07-20T08:00:00+00:00",
                "End": "2026-07-20T14:30:00+00:00",
            }],
        }],
    )

    selected = result["SelectedAssessment"]
    assert result["Status"] == "OnTime"
    assert selected["LoadBeforeMinutes"] == 390
    assert selected["LoadAfterMinutes"] == 450
    assert selected["LoadAfterPercent"] == 93.75
    assert selected["ThresholdExceeded"] is True
    assert selected["PhysicalCapacityExceeded"] is False


def test_request_that_misses_deadline_returns_later_safe_promise():
    result = _evaluate(
        gantt_rows=[{
            "ResourceID": "CCR-1",
            "Bars": [{
                "BarType": "Processing",
                "OrderID": "WO-FULL",
                "OperationID": "WO-FULL:CCR",
                "Start": "2026-07-20T08:00:00+00:00",
                "End": "2026-07-20T16:00:00+00:00",
            }],
        }],
    )

    assert result["Status"] == "LaterSafeDate"
    assert result["RequestedDateAssessment"]["Feasible"] is False
    assert result["EarliestSafeAssessment"]["Feasible"] is True
    assert result["EarliestSafeAssessment"]["PromiseAt"] > "2026-07-20T18:00:00+00:00"
    assert result["SelectedAssessment"] == result["EarliestSafeAssessment"]


def test_repeated_ccr_visits_keep_distinct_operation_correlations():
    result = _evaluate(routing=_routing(repeated_visit=True))

    requests = result["SelectedAssessment"]["ReservationRequests"]
    assert [row["OperationID"] for row in requests] == [
        "SO-100:10:CCR-CUT",
        "SO-100:10:CCR-INSPECT",
    ]
    assert sum(row["ReservedMinutes"] for row in requests) == 90


def test_shadow_load_counts_active_reservations_but_not_converted_rows():
    active = {
        "CapacityReservationID": "CCR-ACTIVE",
        "ResourceID": "CCR-1",
        "WindowStartAt": "2026-07-20T08:00:00+00:00",
        "WindowEndAt": "2026-07-20T16:00:00+00:00",
        "ReservedMinutes": 300,
        "DemandClass": "MTA",
        "Status": "ActivePlanReservation",
    }
    converted = {**active, "CapacityReservationID": "CCR-CONVERTED", "ReservedMinutes": 100, "Status": "ConvertedToScheduledOccupancy"}

    result = _evaluate(active_capacity_reservations=[active, converted])

    selected = result["SelectedAssessment"]
    assert selected["ExistingReservationMinutes"] == 300
    assert selected["LoadAfterMinutes"] == 360


def test_low_load_in_a_window_after_the_deadline_does_not_make_request_on_time():
    result = _evaluate(
        capacity_buckets=[_bucket(21)],
        requested_due_at=datetime(2026, 7, 20, 12, tzinfo=UTC),
    )

    assert result["Status"] == "LaterSafeDate"


def test_unresolved_sequence_setup_rule_blocks_acceptance_instead_of_undercounting():
    result = _evaluate(
        setup_transitions=[SetupTransition("CCR-1", "FAMILY-A", "FG-1", 30)],
    )

    assert result["Status"] == "NotAssessable"
    assert "CCR_SETUP_LOAD_REQUIRES_REVIEW" in [row["Code"] for row in result["Issues"]]


@pytest.mark.parametrize("field", ["requested_due_at", "evaluated_at"])
def test_shadow_schedule_rejects_naive_decision_times(field: str):
    with pytest.raises(ValueError, match="timezone-aware"):
        _evaluate(**{field: datetime(2026, 7, 20, 8)})
```

Run:

```powershell
pytest tests/test_ccr_shadow_scheduler.py -q --basetemp .tmp/pytest-ccr-shadow-red -p no:cacheprovider
```

Expected: FAIL because `sdbr.ccr_shadow_scheduler` does not exist.

- [ ] **Step 4: Implement the window-level algorithm**

Create `sdbr/ccr_shadow_scheduler.py` with this public shape and exact rules:

```python
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from math import ceil, isfinite
from numbers import Real

from sdbr.planner_workbench import Resource, Routing
from sdbr.planning_reservation_view import ACTIVE_PLANNING_STATUSES
from sdbr.scheduling_solver import CapacityBucket, SetupTransition
from sdbr.sdbr_market_control import classify_ccr_load


SHADOW_MODE = "CCRFirstShadowScheduleV1"


def evaluate_ccr_shadow_schedule(
    *,
    order_id: str,
    quantity: float,
    routing: Routing | None,
    resources: list[Resource],
    capacity_buckets: list[CapacityBucket],
    setup_transitions: list[SetupTransition],
    gantt_rows: list[dict[str, object]],
    active_capacity_reservations: list[dict[str, object]],
    requested_due_at: datetime,
    evaluated_at: datetime,
    downstream_protection_minutes: int,
    protection_threshold_percent: float,
) -> dict[str, object]:
    """Evaluate one MTO line without creating a formal schedule or reservation."""
    _validate_request(
        order_id=order_id,
        quantity=quantity,
        requested_due_at=requested_due_at,
        evaluated_at=evaluated_at,
        downstream_protection_minutes=downstream_protection_minutes,
        protection_threshold_percent=protection_threshold_percent,
    )
    ccr_operations, operation_issues = _ccr_operations(
        order_id=order_id,
        quantity=quantity,
        routing=routing,
        resources=resources,
        setup_transitions=setup_transitions,
    )
    window_states, window_issues = _capacity_window_states(
        resources=resources,
        capacity_buckets=capacity_buckets,
        gantt_rows=gantt_rows,
        active_capacity_reservations=active_capacity_reservations,
    )
    issues = [*operation_issues, *window_issues]
    if issues:
        return _not_assessable_result(
            requested_due_at=requested_due_at,
            issues=issues,
            protection_threshold_percent=protection_threshold_percent,
        )
    requested = _backward_requested_date_candidate(
        order_id=order_id,
        operations=ccr_operations,
        windows=window_states,
        requested_due_at=requested_due_at,
        evaluated_at=evaluated_at,
        downstream_protection_minutes=downstream_protection_minutes,
        protection_threshold_percent=protection_threshold_percent,
    )
    earliest_safe = None
    if not requested["Feasible"]:
        earliest_safe = _forward_earliest_safe_candidate(
            order_id=order_id,
            operations=ccr_operations,
            windows=window_states,
            evaluated_at=evaluated_at,
            downstream_protection_minutes=downstream_protection_minutes,
            protection_threshold_percent=protection_threshold_percent,
        )
    return _shadow_result(
        requested_due_at=requested_due_at,
        requested=requested,
        earliest_safe=earliest_safe,
        protection_threshold_percent=protection_threshold_percent,
    )
```

Implement the body and private helpers with these non-negotiable rules:

1. Reject blank `order_id`, non-finite/non-positive `quantity`, naive decision times, negative protection minutes, and thresholds outside `(0, 100]`.
2. Normalize all datetime comparisons to UTC while preserving ISO offsets in returned window references.
3. Select CCR operations by resolving each operation's primary `resource_id` to `Resource.is_constraint=True`. Preserve alternate resource IDs as display-only conservative context. If a relevant nonzero `SetupTransition` targets the CCR operation's setup family but the exact predecessor family cannot be proven from schedule evidence, return `CCR_SETUP_LOAD_REQUIRES_REVIEW` and `NotAssessable` rather than omitting setup minutes. A missing route, missing resource, no CCR operation, duplicate operation identity, malformed capacity window, or malformed active reservation also produces `Status="NotAssessable"`; it never becomes a feasible empty schedule.
4. Effective operation load is `ceil(operation.duration_minutes * quantity * 100 / resource.efficiency_percent)`. Bucket physical capacity is `bucket.capacity_minutes * resource.capacity_units`.
5. Scheduled load is the overlap in minutes of `Processing` bars with each exact capacity window. Count active Phase 0 rows only when status is in `ACTIVE_PLANNING_STATUSES` and `(ResourceID, WindowStartAt, WindowEndAt)` exactly matches the window. Reject ambiguous duplicate IDs or malformed rows instead of undercounting.
6. Derive the last CCR deadline as `requested_due_at - downstream_protection_minutes`. Walk the route backward so downstream non-CCR durations and later CCR visits constrain earlier CCR deadlines.
7. The requested-date candidate allocates each CCR operation in reverse sequence into the latest single window that starts before its operation deadline and has sufficient physical capacity. Do not split one operation over windows. Update candidate load after every selected operation so repeated visits cannot reuse the same free minutes.
8. If the requested-date candidate fails, run a forward earliest-safe pass from `evaluated_at`, respecting route sequence and non-CCR durations. `PromiseAt` is the final route estimate plus downstream protection. The selected candidate is requested-date when on time, otherwise earliest-safe.
9. Every selected window reports `CapacityMinutes`, `ScheduledLoadMinutes`, `ExistingReservationMinutes`, `CandidateLoadMinutes`, `LoadBeforeMinutes`, `LoadAfterMinutes`, rounded percentages, `LoadStatus`, `ThresholdExceeded`, and `PhysicalCapacityExceeded`.
10. A candidate is feasible only when every CCR operation fits at or below physical capacity. Crossing the protection threshold changes risk and recommendation inputs but does not by itself make the date infeasible.
11. Sort returned reservation requests by route sequence. Use `OperationID=f"{order_id}:{operation.operation_id}"` and `ReservationLineID=f"{operation_id}:{window_start.isoformat()}"`; set `LatestAllowedCompletionAt` to an aware instant strictly inside the selected window and no later than the operation deadline.
12. Return only copied/derived business evidence. Do not mutate routing, resources, Gantt rows, capacity buckets, or reservation rows.

Implement every named private helper in the same module according to the twelve rules above; the committed module must contain no stubbed helper or `NotImplementedError`.

- [ ] **Step 5: Run scheduler and P1 regressions**

Run:

```powershell
pytest tests/test_ccr_shadow_scheduler.py tests/test_sdbr_market_control.py tests/test_planning_reservation_view.py -q --basetemp .tmp/pytest-ccr-shadow-green -p no:cacheprovider
```

Expected: PASS. Existing P1 load totals and Phase 0 active/converted filtering remain unchanged.

- [ ] **Step 6: Commit the scheduler slice**

```powershell
git add -- sdbr/ccr_shadow_scheduler.py sdbr/sdbr_market_control.py tests/test_ccr_shadow_scheduler.py tests/test_sdbr_market_control.py
git commit -m "feat: add CCR-first MTO shadow scheduler"
```

---

### Task 3: MTO Evaluation, Material Gate, and Planner-Decision Domain

**Files:**
- Create: `sdbr/order_commitment_evaluation.py`
- Create: `tests/test_order_commitment_evaluation.py`

**Interfaces:**
- Consumes:
  - `create_demand_commitment` and `normalize_demand_commitment` from `sdbr.planning_commitments`.
  - `prepare_reservation_confirmation` and `PlanningReservationWriteSet` from `sdbr.planning_reservations`.
  - `planning_allocated_qty_for_other_demands` from `sdbr.planning_reservation_view`.
  - `InventoryBufferPolicy`, `MaterialAvailability`, and the Task 2 shadow-schedule output.
- Produces:
  - `CcrProtectionPolicy(target_percent: float, source: Literal["ApprovedOperatingModel", "ReferenceFallback"], approved: bool, configuration_id: str | None = None)`.
  - `REFERENCE_CCR_PROTECTION_POLICY` with `80.0`, `ReferenceFallback`, and `approved=False`.
  - `normalize_mto_order(record: Mapping[str, object]) -> dict[str, object]`.
  - `candidate_demand_commitment_id(order: Mapping[str, object]) -> str`.
  - `evaluate_mto_material_availability(*, order: Mapping[str, object], inventory_buffers: list[InventoryBufferPolicy], material_availability: list[MaterialAvailability], active_material_allocations: list[dict[str, object]], current_demand_commitment_id: str, snapshot_id: str, evaluated_at: datetime, material_check_window_minutes: int, check_material_availability: bool, skip_reason: str | None) -> dict[str, object]`.
  - `build_order_commitment_basis(*, baseline_planning_run_id: str, baseline_schedule_fingerprint: str, master_data_version_id: str, routing_fingerprint: str, operational_state_snapshot_id: str, operational_state_captured_at: datetime, capacity_ledger_rows: list[dict[str, object]], material_ledger_rows: list[dict[str, object]], calendar_fingerprint: str, time_buffer_minutes: int) -> dict[str, object]`.
  - `create_order_commitment_evaluation(*, order: Mapping[str, object], shadow_schedule: Mapping[str, object], material_assessment: Mapping[str, object], basis: Mapping[str, object], protection_policy: CcrProtectionPolicy, evaluated_at: datetime) -> dict[str, object]`.
  - `register_order_commitment_evaluation(evaluations: Mapping[str, dict[str, object]], candidate: dict[str, object]) -> tuple[Literal["Created", "Duplicate"], dict[str, object]]`.
  - `supersede_open_order_commitment_evaluations(*, evaluations: Mapping[str, dict[str, object]], candidate: dict[str, object], superseded_at: datetime) -> dict[str, dict[str, object]]`.
  - `prepare_mto_acceptance(*, evaluation: Mapping[str, object], existing_commitments: Mapping[str, dict[str, object]], decision_id: str, decision: str, decided_by: str, decided_at: datetime, reason: str, ccr_risk_acknowledged: bool, material_risk_acknowledged: bool) -> PlanningReservationWriteSet`.
  - `accepted_evaluation_record(*, evaluation: Mapping[str, object], write_set: PlanningReservationWriteSet, decision_id: str, decision: str, decided_by: str, decided_at: datetime, reason: str, ccr_risk_acknowledged: bool, material_risk_acknowledged: bool) -> dict[str, object]`.
  - `rejected_evaluation_record(*, evaluation: Mapping[str, object], decision_id: str, decided_by: str, decided_at: datetime, reason: str) -> dict[str, object]`.

- [ ] **Step 1: Write failing material and recommendation tests**

Create `tests/test_order_commitment_evaluation.py` with an approved-policy fixture, a reference-policy fixture, one on-time shadow result, one later-safe result, inventory/availability rows, and active allocations. Include these core tests:

```python
"""Acceptance evidence for BE-SDBR-006 through BE-SDBR-010."""

from datetime import datetime, timezone

import pytest

from sdbr.order_commitment_evaluation import (
    CcrProtectionPolicy,
    OrderCommitmentConflict,
    REFERENCE_CCR_PROTECTION_POLICY,
    accepted_evaluation_record,
    create_order_commitment_evaluation,
    evaluate_mto_material_availability,
    normalize_mto_order,
    prepare_mto_acceptance,
    register_order_commitment_evaluation,
)
from sdbr.planner_view import InventoryBufferPolicy
from sdbr.release_candidates import MaterialAvailability


UTC = timezone.utc
APPROVED_POLICY = CcrProtectionPolicy(
    target_percent=80.0,
    source="ApprovedOperatingModel",
    approved=True,
    configuration_id="OMC-APPROVED",
)


def _order() -> dict[str, object]:
    return normalize_mto_order({
        "SourceSystem": "MockERP",
        "SourceObjectType": "CustomerOrder",
        "OrderID": "SO-100",
        "OrderVersion": "1",
        "DemandLineID": "10",
        "ProductID": "FG-1",
        "LocationID": "MAIN",
        "Quantity": 2.0,
        "Uom": "EA",
        "RequestedDueAt": "2026-07-20T18:00:00+00:00",
        "BusinessPriority": 10,
        "ReceivedAt": "2026-07-11T08:00:00+00:00",
        "TraceID": "TRACE-SO-100-10",
        "BaselinePlanningRunID": "RUN-BASELINE",
        "RoutingID": "PRIMARY",
        "MaterialRequirements": [{
            "RequirementLineID": "SO-100:10:RM-1",
            "ItemID": "RM-1",
            "LocationID": "MAIN",
            "RequiredQty": 5.0,
            "Uom": "EA",
        }],
    })


def _shadow(*, load_after_percent: float = 70.0, status: str = "OnTime") -> dict[str, object]:
    selected = {
        "Feasible": True,
        "PromiseAt": "2026-07-20T18:00:00+00:00" if status == "OnTime" else "2026-07-21T18:00:00+00:00",
        "LoadBeforeMinutes": 240,
        "LoadAfterMinutes": 300,
        "LoadAfterPercent": load_after_percent,
        "ThresholdExceeded": load_after_percent > 80.0,
        "PhysicalCapacityExceeded": False,
        "ReservationRequests": [{
            "ReservationLineID": "SO-100:10:CCR-CUT:2026-07-20T08:00:00+00:00",
            "OrderID": "SO-100:10",
            "OperationID": "SO-100:10:CCR-CUT",
            "ResourceID": "CCR-1",
            "WindowStartAt": "2026-07-20T08:00:00+00:00",
            "WindowEndAt": "2026-07-20T16:00:00+00:00",
            "ReservedMinutes": 60,
            "LatestAllowedCompletionAt": "2026-07-20T16:00:00+00:00",
        }],
    }
    return {
        "Mode": "CCRFirstShadowScheduleV1",
        "Status": status,
        "RequestedDateAssessment": selected if status == "OnTime" else {"Feasible": False},
        "EarliestSafeAssessment": selected if status != "OnTime" else None,
        "SelectedAssessment": selected,
        "Issues": [],
    }


def _basis() -> dict[str, object]:
    return {
        "BaselinePlanningRunID": "RUN-BASELINE",
        "BaselineScheduleFingerprint": "sha256:schedule",
        "MasterDataVersionID": "MDV-1",
        "RoutingFingerprint": "sha256:routing",
        "OperationalStateSnapshotID": "OPS-1",
        "OperationalStateCapturedAt": "2026-07-11T07:30:00+00:00",
        "CapacityLedgerFingerprint": "sha256:capacity",
        "MaterialLedgerFingerprint": "sha256:material",
        "CalendarFingerprint": "sha256:calendar",
        "TimeBufferMinutes": 60,
    }


def test_material_check_defaults_to_shared_uncommitted_availability():
    material = evaluate_mto_material_availability(
        order=_order(),
        inventory_buffers=[InventoryBufferPolicy("RM-1", "MAIN", 10, 2, 4, 8)],
        material_availability=[MaterialAvailability("RM-1", "MAIN", allocated_qty=1)],
        active_material_allocations=[{
            "MaterialAllocationID": "MPA-OTHER",
            "DemandCommitmentID": "DC-OTHER",
            "ItemID": "RM-1",
            "LocationID": "MAIN",
            "AllocatedQty": 3,
            "Status": "ActivePlanReservation",
        }],
        current_demand_commitment_id="DC-CANDIDATE",
        snapshot_id="OPS-1",
        evaluated_at=datetime(2026, 7, 11, 8, tzinfo=UTC),
        material_check_window_minutes=0,
        check_material_availability=True,
        skip_reason=None,
    )

    assert material["Status"] == "Feasible"
    assert material["CheckEnabled"] is True
    assert material["Lines"][0]["UncommittedAvailabilityQty"] == 6.0
    assert material["AllocationRequests"][0]["AllocatedQty"] == 5.0


def test_material_opt_out_requires_reason_and_never_creates_allocations():
    with pytest.raises(OrderCommitmentConflict, match="skip reason"):
        evaluate_mto_material_availability(
            order=_order(), inventory_buffers=[], material_availability=[],
            active_material_allocations=[], current_demand_commitment_id="DC-1",
            snapshot_id="OPS-1", evaluated_at=datetime(2026, 7, 11, 8, tzinfo=UTC),
            material_check_window_minutes=0, check_material_availability=False,
            skip_reason="",
        )

    material = evaluate_mto_material_availability(
        order=_order(), inventory_buffers=[], material_availability=[],
        active_material_allocations=[], current_demand_commitment_id="DC-1",
        snapshot_id="OPS-1", evaluated_at=datetime(2026, 7, 11, 8, tzinfo=UTC),
        material_check_window_minutes=0, check_material_availability=False,
        skip_reason="Customer asked for a capacity-only decision.",
    )

    assert material["Status"] == "SkippedPendingConfirmation"
    assert material["AllocationRequests"] == []
    assert material["PendingRequirements"] == _order()["MaterialRequirements"]
    assert material["ReleaseGateStillRequired"] is True


def test_reference_threshold_never_returns_ordinary_recommend_accept():
    material = {"Status": "Feasible", "CheckEnabled": True, "AllocationRequests": [], "PendingRequirements": []}

    evaluation = create_order_commitment_evaluation(
        order=_order(), shadow_schedule=_shadow(load_after_percent=70.0),
        material_assessment=material, basis=_basis(),
        protection_policy=REFERENCE_CCR_PROTECTION_POLICY,
        evaluated_at=datetime(2026, 7, 11, 8, tzinfo=UTC),
    )

    assert evaluation["Recommendation"]["Decision"] == "PlannerConfirmationRequired"
    assert evaluation["Recommendation"]["RequiresCcrAcknowledgement"] is True
    assert evaluation["ProtectionPolicy"] == {
        "TargetPercent": 80.0,
        "Source": "ReferenceFallback",
        "Approved": False,
        "ConfigurationID": None,
    }


def test_approved_threshold_under_line_can_recommend_accept_but_does_not_accept():
    evaluation = create_order_commitment_evaluation(
        order=_order(), shadow_schedule=_shadow(load_after_percent=70.0),
        material_assessment={"Status": "Feasible", "CheckEnabled": True, "AllocationRequests": [], "PendingRequirements": []},
        basis=_basis(), protection_policy=APPROVED_POLICY,
        evaluated_at=datetime(2026, 7, 11, 8, tzinfo=UTC),
    )

    assert evaluation["Recommendation"]["Decision"] == "RecommendAccept"
    assert evaluation["Status"] == "AwaitingPlannerDecision"
    assert "Decision" not in evaluation


def test_approved_threshold_exceedance_requires_explicit_acknowledgement():
    evaluation = create_order_commitment_evaluation(
        order=_order(), shadow_schedule=_shadow(load_after_percent=90.0),
        material_assessment={"Status": "Feasible", "CheckEnabled": True, "AllocationRequests": [], "PendingRequirements": []},
        basis=_basis(), protection_policy=APPROVED_POLICY,
        evaluated_at=datetime(2026, 7, 11, 8, tzinfo=UTC),
    )

    assert evaluation["Recommendation"]["Decision"] == "PlannerConfirmationRequired"
    assert evaluation["Recommendation"]["RequiresCcrAcknowledgement"] is True
    with pytest.raises(OrderCommitmentConflict, match="CCR risk acknowledgement"):
        prepare_mto_acceptance(
            evaluation=evaluation, existing_commitments={}, decision_id="DEC-1",
            decision="AcceptRequestedDate", decided_by="planner-1",
            decided_at=datetime(2026, 7, 11, 8, 5, tzinfo=UTC), reason="Reviewed",
            ccr_risk_acknowledged=False, material_risk_acknowledged=False,
        )


def test_intake_registration_is_idempotent_for_same_content_and_basis():
    evaluation = create_order_commitment_evaluation(
        order=_order(), shadow_schedule=_shadow(),
        material_assessment={"Status": "Feasible", "CheckEnabled": True, "AllocationRequests": [], "PendingRequirements": []},
        basis=_basis(), protection_policy=APPROVED_POLICY,
        evaluated_at=datetime(2026, 7, 11, 8, tzinfo=UTC),
    )

    status, created = register_order_commitment_evaluation({}, evaluation)
    replay_status, replay = register_order_commitment_evaluation(
        {str(created["EvaluationID"]): created}, evaluation
    )

    assert status == "Created"
    assert replay_status == "Duplicate"
    assert replay == created
```

Also include exact tests named:

```python
def test_missing_material_evidence_allows_only_reevaluate_or_reject():
    evaluation = create_order_commitment_evaluation(
        order=_order(), shadow_schedule=_shadow(),
        material_assessment={
            "Status": "EvidenceInsufficient", "CheckEnabled": True,
            "AllocationRequests": [], "PendingRequirements": [],
        },
        basis=_basis(), protection_policy=APPROVED_POLICY,
        evaluated_at=datetime(2026, 7, 11, 8, tzinfo=UTC),
    )

    assert evaluation["Recommendation"]["Decision"] == "MaterialEvidenceRequired"
    assert evaluation["Recommendation"]["AllowedActions"] == ["Reevaluate", "Reject"]

def test_later_safe_candidate_allows_accept_recommended_date_only():
    evaluation = create_order_commitment_evaluation(
        order=_order(), shadow_schedule=_shadow(status="LaterSafeDate"),
        material_assessment={
            "Status": "Feasible", "CheckEnabled": True,
            "AllocationRequests": [], "PendingRequirements": [],
        },
        basis=_basis(), protection_policy=APPROVED_POLICY,
        evaluated_at=datetime(2026, 7, 11, 8, tzinfo=UTC),
    )

    assert evaluation["Recommendation"]["Decision"] == "RecommendLaterPromise"
    assert "AcceptRecommendedDate" in evaluation["Recommendation"]["AllowedActions"]
    assert "AcceptRequestedDate" not in evaluation["Recommendation"]["AllowedActions"]

def test_prepare_mto_acceptance_builds_canonical_mto_demand_and_phase0_rows():
    evaluation = create_order_commitment_evaluation(
        order=_order(), shadow_schedule=_shadow(),
        material_assessment={
            "Status": "Feasible", "CheckEnabled": True,
            "AllocationRequests": [{
                "RequirementLineID": "SO-100:10:RM-1", "ItemID": "RM-1",
                "LocationID": "MAIN", "Uom": "EA", "AllocatedQty": 5.0,
                "SupplySourceType": "OnHand", "MaterialSnapshotID": "OPS-1",
            }],
            "PendingRequirements": [],
        },
        basis=_basis(), protection_policy=APPROVED_POLICY,
        evaluated_at=datetime(2026, 7, 11, 8, tzinfo=UTC),
    )

    write_set = prepare_mto_acceptance(
        evaluation=evaluation, existing_commitments={}, decision_id="DEC-ACCEPT-1",
        decision="AcceptRequestedDate", decided_by="planner-1",
        decided_at=datetime(2026, 7, 11, 8, 5, tzinfo=UTC),
        reason="Reviewed and accepted.", ccr_risk_acknowledged=False,
        material_risk_acknowledged=False,
    )

    assert write_set.demand_commitment["DemandSourceType"] == "MTOCustomerOrder"
    assert write_set.demand_commitment["RequiredAt"] == "2026-07-20T18:00:00+00:00"
    assert write_set.demand_commitment["OrderCommitmentEvaluationID"] == evaluation["EvaluationID"]
    assert len(write_set.capacity_reservations) == 1
    assert len(write_set.material_allocations) == 1

def test_conditional_acceptance_records_pending_material_and_zero_allocations():
    evaluation = create_order_commitment_evaluation(
        order=_order(), shadow_schedule=_shadow(),
        material_assessment={
            "Status": "SkippedPendingConfirmation", "CheckEnabled": False,
            "SkipReason": "Capacity-only decision.", "AllocationRequests": [],
            "PendingRequirements": _order()["MaterialRequirements"],
        },
        basis=_basis(), protection_policy=APPROVED_POLICY,
        evaluated_at=datetime(2026, 7, 11, 8, tzinfo=UTC),
    )

    write_set = prepare_mto_acceptance(
        evaluation=evaluation, existing_commitments={}, decision_id="DEC-CONDITIONAL-1",
        decision="ConditionallyAcceptRequestedDate", decided_by="planner-1",
        decided_at=datetime(2026, 7, 11, 8, 5, tzinfo=UTC),
        reason="Capacity accepted; material remains pending.",
        ccr_risk_acknowledged=False, material_risk_acknowledged=True,
    )

    assert write_set.demand_commitment["MaterialCommitmentStatus"] == "PendingConfirmation"
    assert write_set.demand_commitment["PendingMaterialRequirements"]
    assert write_set.material_allocations == ()

def test_accepted_or_rejected_evaluation_cannot_be_silently_superseded():
    evaluation = create_order_commitment_evaluation(
        order=_order(), shadow_schedule=_shadow(),
        material_assessment={
            "Status": "Feasible", "CheckEnabled": True,
            "AllocationRequests": [], "PendingRequirements": [],
        },
        basis=_basis(), protection_policy=APPROVED_POLICY,
        evaluated_at=datetime(2026, 7, 11, 8, tzinfo=UTC),
    )
    accepted = {**evaluation, "Status": "AcceptedPendingFormalSchedule"}

    with pytest.raises(OrderCommitmentConflict, match="cannot be superseded"):
        supersede_open_order_commitment_evaluations(
            evaluations={str(accepted["EvaluationID"]): accepted},
            candidate={**evaluation, "EvaluationID": "OCE-NEW"},
            superseded_at=datetime(2026, 7, 11, 8, 10, tzinfo=UTC),
        )
```

Import `supersede_open_order_commitment_evaluations` in the test module with the other Task 3 functions.

Run:

```powershell
pytest tests/test_order_commitment_evaluation.py -q --basetemp .tmp/pytest-mto-evaluation-red -p no:cacheprovider
```

Expected: FAIL because `sdbr.order_commitment_evaluation` does not exist.

- [ ] **Step 2: Implement canonical order and protection-policy types**

Create the module with these public definitions:

```python
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
from math import isfinite
from numbers import Real
from typing import Literal, Mapping

from sdbr.planner_view import InventoryBufferPolicy
from sdbr.planning_commitments import create_demand_commitment
from sdbr.planning_reservation_view import planning_allocated_qty_for_other_demands
from sdbr.planning_reservations import PlanningReservationWriteSet, prepare_reservation_confirmation
from sdbr.release_candidates import MaterialAvailability


class OrderCommitmentConflict(ValueError):
    status = "OrderCommitmentConflict"


class OrderCommitmentStale(OrderCommitmentConflict):
    status = "OrderCommitmentEvaluationStale"


@dataclass(frozen=True, slots=True)
class CcrProtectionPolicy:
    target_percent: float
    source: Literal["ApprovedOperatingModel", "ReferenceFallback"]
    approved: bool
    configuration_id: str | None = None


REFERENCE_CCR_PROTECTION_POLICY = CcrProtectionPolicy(
    target_percent=80.0,
    source="ReferenceFallback",
    approved=False,
)


ACCEPTANCE_DECISIONS = frozenset({
    "AcceptRequestedDate",
    "AcceptRecommendedDate",
    "ConditionallyAcceptRequestedDate",
})
```

`normalize_mto_order` must validate non-empty identity fields, allowed MTO demand class, finite positive quantity/requirements, unique requirement line IDs, aware request/receipt times, and a valid primary-route reference. It returns canonical UTC timestamps plus:

```python
{
    "OrderKey": "<canonical JSON identity>",
    "LogicalOrderKey": "<same identity without OrderVersion>",
    "OrderContentFingerprint": "sha256:<digest>",
    "PlanningOrderID": "<OrderID>:<DemandLineID>",
}
```

Do not include baseline load, material mode, or evaluation time in `OrderContentFingerprint`; those belong to the evaluation basis/policy fingerprint.

- [ ] **Step 3: Implement material feasibility and immutable fingerprints**

`evaluate_mto_material_availability` must:

1. Default to `check_material_availability=True` at the API boundary.
2. Return `SkippedPendingConfirmation` only with a trimmed reason, zero allocation requests, copied pending requirements, and `ReleaseGateStillRequired=true`.
3. Return `EvidenceInsufficient` when checking is enabled but requirements are empty, inventory balance is missing, snapshot identity is missing, an inbound timestamp is naive, or numeric evidence is malformed.
4. For each requirement, calculate:

```text
QualifiedSupplyQty = OnHandQty + eligible inbound within the material window
UncommittedAvailabilityQty = QualifiedSupplyQty
  - authority AllocatedQty
  - active SDBR planning allocations for other DemandCommitmentIDs
```

5. Never subtract allocations belonging to `current_demand_commitment_id`.
6. Return `Feasible` only when every line covers `RequiredQty`; otherwise return `Shortage` and no allocation requests.
7. Build one Phase 0 material request per feasible requirement with `RequirementLineID`, `ItemID`, `LocationID`, `Uom`, `AllocatedQty=RequiredQty`, `SupplySourceType` (`OnHand` or `OnHandAndInbound`), and `MaterialSnapshotID`.

Use one canonical helper:

```python
def canonical_fingerprint(value: object) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return f"sha256:{sha256(encoded).hexdigest()}"
```

`build_order_commitment_basis` must copy and fingerprint only these relevant facts: baseline run ID and schedule fingerprint; master version ID; route fingerprint; operational snapshot ID/captured time; active capacity reservation IDs, statuses, record versions, windows, and minutes; active material allocation IDs, statuses, record versions, item/location, and quantity; frozen calendar fingerprint; and time-buffer minutes. It must not use the global state-store revision as a business fingerprint.

- [ ] **Step 4: Implement the recommendation matrix and immutable evaluation**

`create_order_commitment_evaluation` must derive a stable ID from the order, basis, and material-policy content:

```python
evaluation_identity = {
    "OrderContentFingerprint": order["OrderContentFingerprint"],
    "BasisFingerprint": canonical_fingerprint(basis),
    "MaterialPolicy": {
        "CheckEnabled": material_assessment["CheckEnabled"],
        "SkipReason": material_assessment.get("SkipReason"),
        "MaterialCheckWindowMinutes": material_assessment["MaterialCheckWindowMinutes"],
    },
}
evaluation_id = f"OCE-{sha256(canonical_fingerprint(evaluation_identity).encode('utf-8')).hexdigest()[:20]}"
```

Return `EvaluationFingerprint` over the immutable evaluation content, excluding lifecycle `Status`, `RecordVersion`, `Decision`, and first-observation timestamps `EvaluatedAt` / `CreatedAt`. This lets a duplicate message observed later return the original evidence instead of conflicting on wall-clock time. Apply this exact recommendation order:

| Capacity | Material | Threshold | Decision | Allowed acceptance |
|---|---|---|---|---|
| Not assessable | any | any | `DoNotRecommendAccept` | none |
| Later safe date | feasible | any | `RecommendLaterPromise` | `AcceptRecommendedDate` |
| On time | insufficient/shortage | any | `MaterialEvidenceRequired` | none |
| On time | skipped | any | `CapacityAcceptableMaterialPending` unless CCR acknowledgement is also required | `ConditionallyAcceptRequestedDate` |
| On time | feasible | approved and within threshold | `RecommendAccept` | `AcceptRequestedDate` |
| On time | feasible/skipped | approved but exceeded | `PlannerConfirmationRequired` | corresponding requested-date action with CCR acknowledgement |
| On time | feasible/skipped | reference fallback | `PlannerConfirmationRequired` | corresponding requested-date action with CCR acknowledgement |

Every recommendation sets `RequiresPlannerDecision=true`. No evaluation function accepts an order.

- [ ] **Step 5: Implement registration, supersession, and Phase 0 acceptance preparation**

`register_order_commitment_evaluation` must return the persisted row for an exact duplicate ID/content and reject ID/content conflicts. `supersede_open_order_commitment_evaluations` may supersede only `AwaitingPlannerDecision` rows sharing `LogicalOrderKey`; it returns copied updates with `Status="Superseded"`, incremented `RecordVersion`, `SupersededByEvaluationID`, and `SupersededAt`. It must reject superseding `AcceptedPendingFormalSchedule` or `Rejected` rows.

`prepare_mto_acceptance` must:

1. Require `Status="AwaitingPlannerDecision"`, an allowed action, a non-empty decision ID/actor/reason, an aware decision time, and all recommendation acknowledgements.
2. Use requested due for `AcceptRequestedDate` / `ConditionallyAcceptRequestedDate`; use `EarliestSafeAssessment.PromiseAt` for `AcceptRecommendedDate`.
3. Reject expired windows where `LatestAllowedCompletionAt <= decided_at`.
4. Build a canonical `MTOCustomerOrder` demand through `create_demand_commitment` and then add only explicit SDBR execution context:

```python
demand.update({
    "OrderCommitmentEvaluationID": evaluation["EvaluationID"],
    "BaselinePlanningRunID": evaluation["Basis"]["BaselinePlanningRunID"],
    "RoutingID": evaluation["Order"]["RoutingID"],
    "BusinessPriority": evaluation["Order"]["BusinessPriority"],
    "AcceptedPromiseAt": accepted_promise_at,
    "MaterialCommitmentStatus": (
        "PlannedAllocationPrepared"
        if evaluation["MaterialAssessment"]["Status"] == "Feasible"
        else "PendingConfirmation"
    ),
    "PendingMaterialRequirements": deepcopy(
        evaluation["MaterialAssessment"].get("PendingRequirements", [])
    ),
    "ExternalOrderAcceptance": "NotPerformed",
    "ProductionMutation": "NotPerformed",
})
```

5. Call the existing `prepare_reservation_confirmation` with `confirmation_id=decision_id`, the selected shadow candidate's capacity requests, and material allocation requests only when material status is `Feasible`.
6. Do not mutate evaluation or store collections. Return the `PlanningReservationWriteSet` for the API transaction.

`accepted_evaluation_record` and `rejected_evaluation_record` must return copied records with incremented `RecordVersion`, stable decision fingerprint, actor/time/reason, and status. Acceptance also records `DemandCommitmentID`, `ReservationBatchID`, accepted promise, `ExternalOrderAcceptance="NotPerformed"`, and `ProductionMutation="NotPerformed"`.

- [ ] **Step 6: Run pure-domain and shared-ledger regressions**

Run:

```powershell
pytest tests/test_order_commitment_evaluation.py tests/test_planning_commitments.py tests/test_planning_reservations.py tests/test_planning_reservation_view.py -q --basetemp .tmp/pytest-mto-evaluation-green -p no:cacheprovider
```

Expected: PASS. Existing demand normalization, replay, predecessor, and one-batch-per-demand guards remain green.

- [ ] **Step 7: Commit the evaluation slice**

```powershell
git add -- sdbr/order_commitment_evaluation.py tests/test_order_commitment_evaluation.py
git commit -m "feat: add MTO commitment evaluation domain"
```

---

### Task 4: Persistent Evidence and Sanitized Read Models

**Files:**
- Modify: `sdbr/state_store.py`
- Create: `sdbr/order_commitment_view.py`
- Modify: `tests/test_state_store.py`
- Create: `tests/test_order_commitment_view.py`

**Interfaces:**
- Produces state collections:
  - `order_commitment_evaluations: dict[str, dict[str, object]]`
  - `order_commitment_events: list[dict[str, object]]`
- Produces read models:
  - `build_order_commitment_workbench(*, evaluations: list[dict[str, object]], demand_commitments: Mapping[str, dict[str, object]], reservation_batches: Mapping[str, dict[str, object]]) -> dict[str, object]`
  - `build_order_commitment_detail(*, evaluation: dict[str, object], events: list[dict[str, object]], demand_commitment: dict[str, object] | None, reservation_batch: dict[str, object] | None) -> dict[str, object]`
- Main rows never expose `OrderContentFingerprint`, `BasisFingerprint`, raw `Basis`, or source payloads. Detail exposes safe references and a collapsed `TechnicalDetails` object.

- [ ] **Step 1: Write failing state-store tests**

Extend the existing full SQLite round-trip test in `tests/test_state_store.py`:

```python
# BE-SDBR-010
store.order_commitment_evaluations["OCE-1"] = {
    "EvaluationID": "OCE-1",
    "Status": "AwaitingPlannerDecision",
}
store.order_commitment_events.append({
    "EventID": "OCE-EVENT-1",
    "EvaluationID": "OCE-1",
    "EventType": "OrderCommitmentEvaluated",
})

# After reload:
assert restored.order_commitment_evaluations == store.order_commitment_evaluations
assert restored.order_commitment_events == store.order_commitment_events
assert restored.health()["StateCounts"]["OrderCommitmentEvaluations"] == 1
assert restored.health()["StateCounts"]["OrderCommitmentEvents"] == 1
```

Extend the clear test to assert both collections empty. Add a rollback test that mutates both collections inside `atomic_update`, raises `RuntimeError`, and asserts object identity plus content are restored.

Run:

```powershell
pytest tests/test_state_store.py -q -k "order_commitment" --basetemp .tmp/pytest-mto-state-red -p no:cacheprovider
```

Expected: FAIL because the fields do not exist.

- [ ] **Step 2: Persist both collections through every store boundary**

Add the two dataclass fields adjacent to the Phase 0 planning collections. Add both keys to `_state_payloads`, `_apply_payloads`, `_clear`, and `_state_counts`. Do not increment `SCHEMA_VERSION`: the SQLite store is a keyed JSON state bag and missing keys already load as empty collections.

Do not add custom snapshot code. `_snapshot_complete_state` already walks all public dataclass fields, and `_restore_complete_state` preserves existing container aliases by clearing/updating lists and dictionaries.

- [ ] **Step 3: Write failing read-model tests**

Create `tests/test_order_commitment_view.py`:

```python
"""Acceptance evidence for BE-SDBR-010 and UI-COMMIT-001."""

from sdbr.order_commitment_view import (
    build_order_commitment_detail,
    build_order_commitment_workbench,
)


def _evaluation() -> dict[str, object]:
    return {
        "EvaluationID": "OCE-1",
        "EvaluationFingerprint": "sha256:evaluation",
        "OrderContentFingerprint": "sha256:order",
        "BasisFingerprint": "sha256:basis",
        "LogicalOrderKey": "logical-order",
        "Status": "AwaitingPlannerDecision",
        "EvaluatedAt": "2026-07-11T08:00:00+00:00",
        "Order": {
            "OrderID": "SO-100", "DemandLineID": "10", "ProductID": "FG-1",
            "Quantity": 2, "Uom": "EA", "RequestedDueAt": "2026-07-20T18:00:00+00:00",
            "BusinessPriority": 10, "RoutingID": "PRIMARY", "TraceID": "TRACE-1",
        },
        "Basis": {
            "BaselinePlanningRunID": "RUN-1", "MasterDataVersionID": "MDV-1",
            "OperationalStateSnapshotID": "OPS-1", "CalendarFingerprint": "sha256:calendar",
        },
        "ProtectionPolicy": {"TargetPercent": 80.0, "Source": "ReferenceFallback", "Approved": False, "ConfigurationID": None},
        "ShadowSchedule": {
            "Status": "OnTime",
            "SelectedAssessment": {
                "PromiseAt": "2026-07-20T18:00:00+00:00",
                "LoadBeforeMinutes": 240, "LoadAfterMinutes": 300,
                "LoadAfterPercent": 62.5, "ThresholdExceeded": False,
                "ReservationRequests": [{"ResourceID": "CCR-1", "WindowStartAt": "2026-07-20T08:00:00+00:00"}],
            },
            "Issues": [],
        },
        "MaterialAssessment": {"Status": "Feasible", "CheckEnabled": True, "Lines": []},
        "Recommendation": {
            "Decision": "PlannerConfirmationRequired",
            "AllowedActions": ["AcceptRequestedDate", "Reject", "Reevaluate"],
            "RequiresCcrAcknowledgement": True,
            "RequiresMaterialAcknowledgement": False,
        },
    }


def test_workbench_is_business_facing_and_omits_raw_fingerprints():
    result = build_order_commitment_workbench(
        evaluations=[_evaluation()], demand_commitments={}, reservation_batches={}
    )

    assert result["Summary"]["AwaitingDecisionCount"] == 1
    row = result["Rows"][0]
    assert row["OrderID"] == "SO-100"
    assert row["Recommendation"] == "PlannerConfirmationRequired"
    assert row["ProtectionThresholdSource"] == "ReferenceFallback"
    assert "Basis" not in row
    assert "BasisFingerprint" not in row
    assert "OrderContentFingerprint" not in row


def test_detail_keeps_technical_ids_collapsed_and_includes_audit():
    result = build_order_commitment_detail(
        evaluation=_evaluation(),
        events=[{"EventID": "EV-1", "EvaluationID": "OCE-1", "EventType": "OrderCommitmentEvaluated"}],
        demand_commitment=None,
        reservation_batch=None,
    )

    assert result["Order"]["OrderID"] == "SO-100"
    assert result["CapacityEvidence"]["Status"] == "OnTime"
    assert result["Boundary"]["ExternalOrderAcceptance"] == "NotPerformed"
    assert result["Boundary"]["ProductionMutation"] == "NotPerformed"
    assert result["TechnicalDetails"]["EvaluationFingerprint"] == "sha256:evaluation"
    assert result["AuditHistory"][0]["EventType"] == "OrderCommitmentEvaluated"
```

Run:

```powershell
pytest tests/test_order_commitment_view.py -q --basetemp .tmp/pytest-mto-view-red -p no:cacheprovider
```

Expected: FAIL because the read-model module does not exist.

- [ ] **Step 4: Implement deterministic list/detail projections**

The workbench summary must include:

```python
{
    "EvaluationCount": int,
    "AwaitingDecisionCount": int,
    "ConfirmationRequiredCount": int,
    "MaterialPendingCount": int,
    "AcceptedPendingScheduleCount": int,
    "RejectedCount": int,
}
```

Each row must include only:

```python
{
    "EvaluationID", "OrderID", "DemandLineID", "ProductID", "Quantity", "Uom",
    "RequestedDueAt", "EarliestSafePromiseAt", "CcrResourceIDs",
    "LoadBeforeMinutes", "LoadAfterMinutes", "LoadAfterPercent",
    "ProtectionThresholdPercent", "ProtectionThresholdSource",
    "MaterialStatus", "Recommendation", "AllowedActions", "Status",
    "ReservationBatchID", "EvaluatedAt", "ExternalOrderAcceptance",
    "PlanningRunCreation", "ProductionMutation",
}
```

Resolve `ReservationBatchID` from the accepted evaluation decision first, then from a matching demand commitment if needed. Sort newest `EvaluatedAt` first, then `OrderID`, then `EvaluationID`.

Default `ExternalOrderAcceptance`, `PlanningRunCreation`, and `ProductionMutation` to `NotPerformed` for undecided/rejected rows as well as accepted rows.

The detail projection must use this exact top-level shape:

```python
{
    "EvaluationID": str,
    "Status": str,
    "EvaluatedAt": str,
    "RecordVersion": int,
    "Order": dict[str, object],
    "CapacityEvidence": dict[str, object],
    "MaterialEvidence": dict[str, object],
    "Recommendation": dict[str, object],
    "EvidenceReferences": dict[str, object],
    "Decision": dict[str, object] | None,
    "Reservation": dict[str, object] | None,
    "AuditHistory": list[dict[str, object]],
    "TechnicalDetails": dict[str, object],
    "Boundary": dict[str, object],
}
```

Copy selected capacity evidence, material lines, recommendation, safe configuration/snapshot references, decision/reservation summary, and audit history; place fingerprints only under `TechnicalDetails`. `Boundary` is always:

```python
{
    "RecommendationOnly": True,
    "ExternalOrderAcceptance": "NotPerformed",
    "PlanningRunCreation": "NotPerformed",
    "ProductionMutation": "NotPerformed",
    "ReleaseMaterialGateStillRequired": True,
}
```

- [ ] **Step 5: Run persistence and view tests**

Run:

```powershell
pytest tests/test_state_store.py tests/test_order_commitment_view.py -q --basetemp .tmp/pytest-mto-state-view-green -p no:cacheprovider
```

Expected: PASS, including SQLite restart and rollback evidence.

- [ ] **Step 6: Commit persistent evidence and read models**

```powershell
git add -- sdbr/state_store.py sdbr/order_commitment_view.py tests/test_state_store.py tests/test_order_commitment_view.py
git commit -m "feat: persist MTO commitment evidence"
```

---

### Task 5: Automatic Intake, Re-Evaluation, and Read APIs

**Files:**
- Modify: `sdbr/api.py`
- Modify: `tests/test_api.py`

**Interfaces:**
- Produces Pydantic payloads:
  - `MtoMaterialRequirementPayload`
  - `MtoOrderCommitmentIntakePayload`
  - `MtoOrderCommitmentReevaluationPayload`
- Produces endpoints:
  - `POST /planner/workbench/order-commitments/intake`
  - `POST /planner/workbench/order-commitments/{evaluation_id}/reevaluate`
  - `GET /planner/workbench/order-commitments/workbench`
  - `GET /planner/workbench/order-commitments/{evaluation_id}`
- Intake and re-evaluation use `REFERENCE_CCR_PROTECTION_POLICY` only. No API field lets a caller supply, approve, or override the threshold.
- Every GET returns the store revision in the existing `X-Workbench-Revision` header.

- [ ] **Step 1: Write the failing automatic-intake API fixture and tests**

Add imports for the new domain/view modules and `build_capacity_buckets_from_resources`. Add a dedicated `_order_commitment_test_store()` helper in `tests/test_api.py`; do not overload `_schedule_result_test_store()` because its route is intentionally empty and its historical solver is Gurobi.

The helper must create:

```python
def _order_commitment_test_store() -> WorkbenchStateStore:
    store = WorkbenchStateStore()
    store.master_data_versions["MDV-MTO"] = {
        "VersionID": "MDV-MTO",
        "CapturedAt": "2026-07-11T07:00:00+00:00",
        "SourceSystem": "SDBR-Test",
        "Status": "Valid",
        "CalendarTimezone": "UTC",
        "Resources": [
            {
                "ResourceID": "CCR-1", "Name": "Constraint", "IsConstraint": True,
                "DailyCapacityMinutes": {"2026-07-20": 480, "2026-07-21": 480},
                "CapacityUnits": 1, "EfficiencyPercent": 100,
            },
            {
                "ResourceID": "NCR-1", "Name": "Pack", "IsConstraint": False,
                "DailyCapacityMinutes": {"2026-07-20": 480, "2026-07-21": 480},
                "CapacityUnits": 1, "EfficiencyPercent": 100,
            },
        ],
        "Routings": [{
            "ProductID": "FG-1", "RoutingID": "PRIMARY", "IsPrimary": True,
            "Operations": [
                {"OperationID": "CCR-CUT", "ResourceID": "CCR-1", "DurationMinutes": 60, "Sequence": 10, "AlternateResourceIDs": []},
                {"OperationID": "PACK", "ResourceID": "NCR-1", "DurationMinutes": 30, "Sequence": 20, "AlternateResourceIDs": []},
            ],
        }],
        "Orders": [{
            "OrderID": "WO-EXISTING", "ProductID": "FG-1", "Quantity": 1,
            "DueDate": "2026-07-20T18:00:00+00:00", "TargetStartDate": "2026-07-20",
        }],
        "InventoryBuffers": [],
        "MaterialRequirements": [],
        "Validation": {"IsValid": True},
    }
    store.operational_state_snapshots["OPS-MTO"] = create_operational_state_snapshot(
        snapshot_id="OPS-MTO",
        captured_at=datetime(2026, 7, 11, 7, 30, tzinfo=timezone.utc),
        inventory_buffers=[InventoryBufferPolicy("RM-1", "MAIN", 20, 2, 4, 8)],
        material_availability=[MaterialAvailability("RM-1", "MAIN", allocated_qty=0)],
        wip_limits=[],
    )
    store.planning_runs["RUN-MTO-BASELINE"] = {
        "RunID": "RUN-MTO-BASELINE", "Status": "Completed", "PublicationStatus": "Published",
        "MasterDataVersionID": "MDV-MTO", "OperationalStateSnapshotID": "OPS-MTO",
        "ScheduleStartAt": "2026-07-20T00:00:00+00:00", "TimeBufferMinutes": 60,
        "FrozenBaseCalendars": [], "FrozenResourceCalendarAssignments": [],
        "FrozenCalendarOverrides": [], "FrozenOperatingModelConfiguration": None,
        "OperatingModelConfigurationID": None,
        "Schedule": {
            "GeneratedAt": "2026-07-11T07:45:00+00:00",
            "GanttRows": [{
                "ResourceID": "CCR-1",
                "Bars": [{
                    "BarType": "Processing", "OrderID": "WO-EXISTING",
                    "OperationID": "WO-EXISTING:CCR-CUT",
                    "Start": "2026-07-20T08:00:00+00:00",
                    "End": "2026-07-20T11:00:00+00:00",
                }],
            }],
        },
    }
    return store


def _mto_intake_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "SourceSystem": "MockERP", "SourceObjectType": "CustomerOrder",
        "OrderID": "SO-100", "OrderVersion": "1", "DemandLineID": "10",
        "ProductID": "FG-1", "LocationID": "MAIN", "Quantity": 1,
        "Uom": "EA", "RequestedDueAt": "2026-07-20T18:00:00+00:00",
        "BusinessPriority": 10, "ReceivedAt": "2026-07-11T08:00:00+00:00",
        "TraceID": "TRACE-SO-100-10", "BaselinePlanningRunID": "RUN-MTO-BASELINE",
        "RoutingID": "PRIMARY",
        "MaterialRequirements": [{
            "RequirementLineID": "SO-100:10:RM-1", "ItemID": "RM-1",
            "LocationID": "MAIN", "RequiredQty": 5, "Uom": "EA",
        }],
    }
    payload.update(overrides)
    return payload
```

Add these tests with `utc_now=lambda: datetime(2026, 7, 11, 8, tzinfo=timezone.utc)`:

```python
# BE-SDBR-006 through BE-SDBR-010
def test_order_intake_automatically_evaluates_but_creates_no_commitment_or_reservation():
    store = _order_commitment_test_store()
    client = TestClient(create_app(state_store=store, utc_now=lambda: datetime(2026, 7, 11, 8, tzinfo=timezone.utc)))

    response = client.post("/planner/workbench/order-commitments/intake", json=_mto_intake_payload())

    assert response.status_code == 200
    data = response.json()["Data"]
    assert data["RegistrationStatus"] == "Created"
    assert data["Evaluation"]["Status"] == "AwaitingPlannerDecision"
    assert data["Evaluation"]["Recommendation"] == "PlannerConfirmationRequired"
    assert data["Evaluation"]["ProtectionThresholdSource"] == "ReferenceFallback"
    assert store.planning_demand_commitments == {}
    assert store.planning_reservation_batches == {}
    assert store.ccr_capacity_reservations == {}
    assert store.material_planning_allocations == {}
    assert store.planning_runs.keys() == {"RUN-MTO-BASELINE"}
    assert store.integration_messages == []


def test_order_intake_defaults_material_check_to_enabled():
    client = TestClient(create_app(state_store=_order_commitment_test_store(), utc_now=lambda: datetime(2026, 7, 11, 8, tzinfo=timezone.utc)))

    response = client.post("/planner/workbench/order-commitments/intake", json=_mto_intake_payload())

    detail_id = response.json()["Data"]["Evaluation"]["EvaluationID"]
    detail = client.get(f"/planner/workbench/order-commitments/{detail_id}").json()["Data"]
    assert detail["MaterialEvidence"]["CheckEnabled"] is True
    assert detail["MaterialEvidence"]["Status"] == "Feasible"


def test_duplicate_order_message_returns_same_evaluation_and_one_event():
    store = _order_commitment_test_store()
    client = TestClient(create_app(state_store=store, utc_now=lambda: datetime(2026, 7, 11, 8, tzinfo=timezone.utc)))

    first = client.post("/planner/workbench/order-commitments/intake", json=_mto_intake_payload())
    second = client.post("/planner/workbench/order-commitments/intake", json=_mto_intake_payload())

    assert second.json()["Data"]["RegistrationStatus"] == "Duplicate"
    assert second.json()["Data"]["Evaluation"]["EvaluationID"] == first.json()["Data"]["Evaluation"]["EvaluationID"]
    assert len(store.order_commitment_evaluations) == 1
    assert len(store.order_commitment_events) == 1


def test_order_commitment_workbench_and_detail_are_sanitized():
    store = _order_commitment_test_store()
    client = TestClient(create_app(state_store=store, utc_now=lambda: datetime(2026, 7, 11, 8, tzinfo=timezone.utc)))
    intake = client.post("/planner/workbench/order-commitments/intake", json=_mto_intake_payload())
    evaluation_id = intake.json()["Data"]["Evaluation"]["EvaluationID"]

    workbench = client.get("/planner/workbench/order-commitments/workbench")
    detail = client.get(f"/planner/workbench/order-commitments/{evaluation_id}")

    assert workbench.status_code == detail.status_code == 200
    assert "X-Workbench-Revision" in workbench.headers
    assert "Basis" not in workbench.json()["Data"]["Rows"][0]
    assert detail.json()["Data"]["TechnicalDetails"]["EvaluationFingerprint"]
    assert "RawPayload" not in detail.text


def test_material_opt_out_reevaluation_requires_reason_and_supersedes_open_evidence():
    store = _order_commitment_test_store()
    client = TestClient(create_app(state_store=store, utc_now=lambda: datetime(2026, 7, 11, 8, 5, tzinfo=timezone.utc)))
    intake = client.post("/planner/workbench/order-commitments/intake", json=_mto_intake_payload())
    evaluation_id = intake.json()["Data"]["Evaluation"]["EvaluationID"]

    missing_reason = client.post(
        f"/planner/workbench/order-commitments/{evaluation_id}/reevaluate",
        json={"RequestedBy": "planner-1", "CheckMaterialAvailability": False, "MaterialCheckSkipReason": ""},
    )
    assert missing_reason.status_code == 409

    response = client.post(
        f"/planner/workbench/order-commitments/{evaluation_id}/reevaluate",
        json={
            "RequestedBy": "planner-1", "CheckMaterialAvailability": False,
            "MaterialCheckSkipReason": "Capacity-only customer discussion.",
        },
    )

    assert response.status_code == 200
    new_id = response.json()["Data"]["Evaluation"]["EvaluationID"]
    assert new_id != evaluation_id
    assert store.order_commitment_evaluations[evaluation_id]["Status"] == "Superseded"
    assert response.json()["Data"]["Evaluation"]["MaterialStatus"] == "SkippedPendingConfirmation"
```

Also test 404/409 for missing, non-completed, or Draft baseline run, missing master version, missing operational snapshot, and unknown evaluation detail. Test malformed route/resource/calendar as a persisted `DoNotRecommendAccept` evaluation with structured issues, not a 500.

Run:

```powershell
pytest tests/test_api.py -q -k "order_commitment and not decision" --basetemp .tmp/pytest-mto-intake-api-red -p no:cacheprovider
```

Expected: FAIL because payloads, state aliases, helpers, and endpoints do not exist.

- [ ] **Step 2: Add exact Pydantic request contracts**

Add near `OrderPayload`:

```python
class MtoMaterialRequirementPayload(BaseModel):
    RequirementLineID: str
    ItemID: str
    LocationID: str
    RequiredQty: float = Field(gt=0)
    Uom: str = "EA"


class MtoOrderCommitmentIntakePayload(BaseModel):
    SourceSystem: str = "MockERP"
    SourceObjectType: str = "CustomerOrder"
    OrderID: str
    OrderVersion: str
    DemandLineID: str = "1"
    ProductID: str
    LocationID: str
    Quantity: float = Field(gt=0)
    Uom: str = "EA"
    RequestedDueAt: AwareDatetime
    BusinessPriority: int = Field(default=100, ge=1, le=999)
    ReceivedAt: AwareDatetime
    TraceID: str
    BaselinePlanningRunID: str
    RoutingID: str = "PRIMARY"
    MaterialRequirements: list[MtoMaterialRequirementPayload] = Field(default_factory=list)


class MtoOrderCommitmentReevaluationPayload(BaseModel):
    RequestedBy: str
    BaselinePlanningRunID: str | None = None
    CheckMaterialAvailability: bool = True
    MaterialCheckSkipReason: str | None = None
```

Use server-owned `server_utc_now()` for evaluation/event time. Automatic intake always calls material evaluation with `check_material_availability=True`; only the authenticated planner/admin re-evaluation endpoint may turn it off. Resolve `MaterialCheckWindowMinutes` from the baseline run's frozen release policy (`MaterialCheckWindowMinutes`, then `MaterialLookaheadMinutes`, then `0`) rather than accepting a UI/API override. Do not accept a threshold, approved flag, configuration payload, external acceptance flag, or production mutation flag from clients.

- [ ] **Step 3: Wire state, auth, and one orchestration helper**

Inside `create_app`, alias the two Task 4 collections. Extend the `require_auth` protected-path tuple with `/planner/workbench/order-commitments`; existing role behavior then allows Viewer/Planner/Worker/Admin GET and only Planner/Admin POST.

Add `_build_order_commitment_evaluation_from_state` as a nested helper so it can safely use store aliases and the existing API conversion functions. It must:

1. Resolve a baseline run with `Status="Completed"` and `PublicationStatus` in `{"Approved", "Published"}`, a valid master version, and an operational snapshot or return the repository's standard 404/409 response shape.
2. Rehydrate `Resource` and `Routing` from the frozen master version.
3. Apply the baseline run's `FrozenBaseCalendars`, `FrozenResourceCalendarAssignments`, and `FrozenCalendarOverrides` through existing calendar helpers.
4. Select the exact primary route matching `ProductID` and `RoutingID`. First scope rejects a non-primary route as structured `ROUTING_NOT_PRIMARY`; it does not alter routing governance or solver routing semantics.
5. Build aware capacity buckets using the master `CalendarTimezone`; when the version has only date buckets and no timezone, use the order's request timezone and record that source in basis evidence.
6. Parse the baseline run's frozen `SetupTransitions` through the existing payload converter and pass them, completed `Schedule.GanttRows`, and copied active shared capacity rows to Task 2. A relevant unresolved setup rule remains a structured no-accept recommendation.
7. Derive the prospective MTO `DemandCommitmentID` through a Task 3 `candidate_demand_commitment_id(order)` helper, then call material evaluation so self-allocation exclusion is stable on replay.
8. Build relevant-state fingerprints from sorted immutable projections. Do not fingerprint the complete store, raw master payload, or unrelated audit/events.
9. Always inject `REFERENCE_CCR_PROTECTION_POLICY`. Do not inspect an uncontracted DDAE field.
10. Return the immutable evaluation plus a sanitized error response only for missing top-level repository references.

- [ ] **Step 4: Implement idempotent intake and audited re-evaluation**

For intake:

```python
@app.post("/planner/workbench/order-commitments/intake")
def planner_workbench_order_commitment_intake(
    payload: MtoOrderCommitmentIntakePayload,
    request: Request,
):
    endpoint = "/planner/workbench/order-commitments/intake"
    evaluation_or_response = _build_order_commitment_evaluation_from_state(
        order=_mto_order_from_payload(payload),
        evaluated_at=server_utc_now(),
        check_material_availability=True,
        material_check_skip_reason=None,
        material_check_window_minutes=_material_check_window_minutes_for_run(
            payload.BaselinePlanningRunID
        ),
    )
    if isinstance(evaluation_or_response, JSONResponse):
        return evaluation_or_response
    registration, evaluation = register_order_commitment_evaluation(
        order_commitment_evaluations,
        evaluation_or_response,
    )
    if registration == "Created":
        order_commitment_evaluations[str(evaluation["EvaluationID"])] = deepcopy(evaluation)
        _append_order_commitment_event(
            events=order_commitment_events,
            evaluation=evaluation,
            event_type="OrderCommitmentEvaluated",
            actor_id=_effective_actor_id(request, str(evaluation["Order"]["SourceSystem"])),
            occurred_at=server_utc_now(),
        )
    return {
        "Endpoint": endpoint,
        "StatusCode": 200,
        "Data": {
            "RegistrationStatus": registration,
            "Evaluation": _order_commitment_row(evaluation),
            "Boundary": _order_commitment_boundary(),
        },
    }
```

The final implementation may call the Task 4 view function instead of a private `_order_commitment_row`, but must use one sanitizer only.

Re-evaluation copies the canonical order from the source evaluation, optionally replaces `BaselinePlanningRunID`, resolves the material window from that baseline run, applies the planner's material-check toggle/reason, recomputes against current relevant state, registers the new evaluation, supersedes only prior open evidence, writes `OrderCommitmentReevaluated` and `OrderCommitmentEvaluationSuperseded` events, and returns the new sanitized row. If relevant state and policy are unchanged, it returns `Duplicate` without a second event.

Stable event IDs must be derived from evaluation ID, event type, and decision/superseding identity. Duplicate intake/re-evaluation must not append duplicate events. Every event uses this envelope and omits raw payloads:

```python
{
    "EventID": str,
    "EventType": str,
    "EvaluationID": str,
    "OccurredAt": str,
    "ActorID": str,
    "TraceID": str,
    "CausationID": str,
    "CorrelationID": str,
    "DecisionID": str | None,
    "ReservationBatchID": str | None,
    "Details": dict[str, object],
}
```

`Details` may contain status transitions, recommendation code, superseding evaluation ID, and non-sensitive reservation IDs. It must not contain `Basis`, master data, operational-state rows, or a source order payload.

- [ ] **Step 5: Implement sanitized GET endpoints**

The workbench GET passes copied store values to `build_order_commitment_workbench`. Detail resolves any decision-linked demand/batch, filters events by `EvaluationID`, and calls `build_order_commitment_detail`. Missing evaluation returns `404 OrderCommitmentEvaluationNotFound`.

Keep store locking consistent with existing GET middleware. Do not add a second lock around the two collections; `state_admission` already captures body and revision in one boundary.

- [ ] **Step 6: Run API, persistence, and domain tests**

Run:

```powershell
pytest tests/test_api.py tests/test_order_commitment_evaluation.py tests/test_order_commitment_view.py tests/test_state_store.py -q -k "order_commitment" --basetemp .tmp/pytest-mto-intake-api-green -p no:cacheprovider
```

Expected: PASS. Intake creates one evaluation and event only; all shared planning and external integration collections remain unchanged.

- [ ] **Step 7: Commit automatic intake and read APIs**

```powershell
git add -- sdbr/api.py tests/test_api.py
git commit -m "feat: add automatic MTO commitment intake"
```

---

### Task 6: Revision-Guarded Option-2 Planner Decision

**Files:**
- Modify: `sdbr/api.py`
- Modify: `tests/test_api.py`

**Interfaces:**
- Produces `MtoOrderCommitmentDecisionPayload`.
- Produces `POST /planner/workbench/order-commitments/{evaluation_id}/decision`.
- Consumes the exact `EvaluationFingerprint`, `If-Match` state revision, Task 3 `prepare_mto_acceptance`, and Phase 0 `apply_reservation_write_set`.
- Acceptance output is `AcceptedPendingFormalSchedule`; rejection output is `Rejected`.

- [ ] **Step 1: Write failing decision, stale-state, and no-mutation tests**

Add:

```python
def _decision_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "DecisionID": "DEC-SO-100-10-1",
        "Decision": "AcceptRequestedDate",
        "DecidedBy": "planner-1",
        "Reason": "Reviewed capacity and customer priority.",
        "ExpectedEvaluationFingerprint": "",
        "CcrRiskAcknowledged": True,
        "MaterialRiskAcknowledged": False,
    }
    payload.update(overrides)
    return payload


def _intake_for_decision(client: TestClient) -> tuple[str, str, str]:
    response = client.post("/planner/workbench/order-commitments/intake", json=_mto_intake_payload())
    row = response.json()["Data"]["Evaluation"]
    detail = client.get(f"/planner/workbench/order-commitments/{row['EvaluationID']}")
    return row["EvaluationID"], detail.json()["Data"]["TechnicalDetails"]["EvaluationFingerprint"], detail.headers["X-Workbench-Revision"]


def test_option2_acceptance_atomically_creates_shared_mto_reservations_only():
    store = _order_commitment_test_store()
    client = TestClient(create_app(state_store=store, utc_now=lambda: datetime(2026, 7, 11, 8, 5, tzinfo=timezone.utc)))
    evaluation_id, fingerprint, revision = _intake_for_decision(client)

    response = client.post(
        f"/planner/workbench/order-commitments/{evaluation_id}/decision",
        headers={"If-Match": revision},
        json=_decision_payload(ExpectedEvaluationFingerprint=fingerprint),
    )

    assert response.status_code == 200
    data = response.json()["Data"]
    assert data["Evaluation"]["Status"] == "AcceptedPendingFormalSchedule"
    assert data["Evaluation"]["ExternalOrderAcceptance"] == "NotPerformed"
    assert data["Evaluation"]["ProductionMutation"] == "NotPerformed"
    assert len(store.planning_demand_commitments) == 1
    assert len(store.planning_reservation_batches) == 1
    assert len(store.ccr_capacity_reservations) == 1
    assert len(store.material_planning_allocations) == 1
    assert store.planning_runs.keys() == {"RUN-MTO-BASELINE"}
    assert store.integration_messages == []
    assert store.ddsop_feedback_outbound_messages == []


def test_reference_or_exceeded_threshold_cannot_accept_without_ccr_acknowledgement():
    store = _order_commitment_test_store()
    client = TestClient(create_app(state_store=store, utc_now=lambda: datetime(2026, 7, 11, 8, 5, tzinfo=timezone.utc)))
    evaluation_id, fingerprint, revision = _intake_for_decision(client)

    response = client.post(
        f"/planner/workbench/order-commitments/{evaluation_id}/decision",
        headers={"If-Match": revision},
        json=_decision_payload(ExpectedEvaluationFingerprint=fingerprint, CcrRiskAcknowledged=False),
    )

    assert response.status_code == 409
    assert response.json()["Data"]["Status"] == "OrderCommitmentConflict"
    assert store.planning_demand_commitments == {}
    assert store.planning_reservation_batches == {}


def test_conditional_acceptance_keeps_material_pending_and_creates_no_allocation():
    store = _order_commitment_test_store()
    client = TestClient(create_app(state_store=store, utc_now=lambda: datetime(2026, 7, 11, 8, 5, tzinfo=timezone.utc)))
    initial = client.post("/planner/workbench/order-commitments/intake", json=_mto_intake_payload())
    source_id = initial.json()["Data"]["Evaluation"]["EvaluationID"]
    reevaluated = client.post(
        f"/planner/workbench/order-commitments/{source_id}/reevaluate",
        json={
            "RequestedBy": "planner-1", "CheckMaterialAvailability": False,
            "MaterialCheckSkipReason": "Capacity-only decision.",
        },
    )
    evaluation_id = reevaluated.json()["Data"]["Evaluation"]["EvaluationID"]
    detail = client.get(f"/planner/workbench/order-commitments/{evaluation_id}")

    response = client.post(
        f"/planner/workbench/order-commitments/{evaluation_id}/decision",
        headers={"If-Match": detail.headers["X-Workbench-Revision"]},
        json=_decision_payload(
            Decision="ConditionallyAcceptRequestedDate",
            ExpectedEvaluationFingerprint=detail.json()["Data"]["TechnicalDetails"]["EvaluationFingerprint"],
            MaterialRiskAcknowledged=True,
        ),
    )

    assert response.status_code == 200
    demand = next(iter(store.planning_demand_commitments.values()))
    assert demand["MaterialCommitmentStatus"] == "PendingConfirmation"
    assert demand["PendingMaterialRequirements"]
    assert store.material_planning_allocations == {}


def test_decision_requires_if_match_and_exact_evaluation_fingerprint():
    store = _order_commitment_test_store()
    client = TestClient(create_app(state_store=store, utc_now=lambda: datetime(2026, 7, 11, 8, 5, tzinfo=timezone.utc)))
    evaluation_id, fingerprint, revision = _intake_for_decision(client)

    no_precondition = client.post(
        f"/planner/workbench/order-commitments/{evaluation_id}/decision",
        json=_decision_payload(ExpectedEvaluationFingerprint=fingerprint),
    )
    wrong_fingerprint = client.post(
        f"/planner/workbench/order-commitments/{evaluation_id}/decision",
        headers={"If-Match": revision},
        json=_decision_payload(ExpectedEvaluationFingerprint="sha256:wrong"),
    )

    assert no_precondition.status_code == 428
    assert wrong_fingerprint.status_code == 409
    assert store.planning_demand_commitments == {}


def test_relevant_capacity_change_marks_evaluation_stale_before_confirmation():
    store = _order_commitment_test_store()
    client = TestClient(create_app(state_store=store, utc_now=lambda: datetime(2026, 7, 11, 8, 5, tzinfo=timezone.utc)))
    evaluation_id, fingerprint, _revision = _intake_for_decision(client)
    store.ccr_capacity_reservations["CCR-COMPETING"] = {
        "CapacityReservationID": "CCR-COMPETING", "ReservationBatchID": "PRB-OTHER",
        "DemandCommitmentID": "DC-OTHER", "DemandClass": "MTA", "ResourceID": "CCR-1",
        "WindowStartAt": "2026-07-20T00:00:00+00:00", "WindowEndAt": "2026-07-21T00:00:00+00:00",
        "ReservedMinutes": 120, "Status": "ActivePlanReservation", "RecordVersion": 1,
    }
    store.save()

    response = client.post(
        f"/planner/workbench/order-commitments/{evaluation_id}/decision",
        headers={"If-Match": str(store.current_revision())},
        json=_decision_payload(ExpectedEvaluationFingerprint=fingerprint),
    )

    assert response.status_code == 409
    assert response.json()["Data"]["Status"] == "OrderCommitmentEvaluationStale"
    assert store.planning_reservation_batches == {}


def test_reject_records_decision_without_shared_reservations():
    store = _order_commitment_test_store()
    client = TestClient(create_app(state_store=store, utc_now=lambda: datetime(2026, 7, 11, 8, 5, tzinfo=timezone.utc)))
    evaluation_id, fingerprint, revision = _intake_for_decision(client)

    response = client.post(
        f"/planner/workbench/order-commitments/{evaluation_id}/decision",
        headers={"If-Match": revision},
        json=_decision_payload(Decision="Reject", ExpectedEvaluationFingerprint=fingerprint, CcrRiskAcknowledged=False),
    )

    assert response.status_code == 200
    assert response.json()["Data"]["Evaluation"]["Status"] == "Rejected"
    assert store.planning_demand_commitments == {}
    assert store.planning_reservation_batches == {}
```

Add exact tests for:

- idempotent replay of the same `DecisionID` and payload returns the same batch without duplicate events;
- same `DecisionID` with changed action/reason/fingerprint returns 409;
- two clients using one revision to accept competing evaluations produce one 200 and one `StateStoreRevisionConflict` 409;
- a forced `save()` failure restores evaluation, demand, batch, capacity, material, events, processed keys, and revision;
- accepted/rejected/superseded evaluation cannot be decided again except exact accepted-decision replay;
- `MaterialEvidenceRequired` and `DoNotRecommendAccept` reject all acceptance action codes;
- `AcceptRecommendedDate` uses the later safe promise and matching reservation rows;
- auth mode allows Viewer GET, forbids Viewer/Worker decision, and allows Planner/Admin decision.

Run:

```powershell
pytest tests/test_api.py -q -k "order_commitment and (decision or concurrent or rollback or auth)" --basetemp .tmp/pytest-mto-decision-red -p no:cacheprovider
```

Expected: FAIL because the decision payload/endpoint does not exist.

- [ ] **Step 2: Add the decision payload and precondition contract**

```python
class MtoOrderCommitmentDecisionPayload(BaseModel):
    DecisionID: str
    Decision: Literal[
        "AcceptRequestedDate",
        "AcceptRecommendedDate",
        "ConditionallyAcceptRequestedDate",
        "Reject",
    ]
    DecidedBy: str
    Reason: str
    ExpectedEvaluationFingerprint: str
    CcrRiskAcknowledged: bool = False
    MaterialRiskAcknowledged: bool = False
```

The endpoint must return `428 OrderCommitmentPreconditionRequired` when `If-Match` is absent. Let existing middleware reject a stale numeric revision before endpoint code runs. Do not silently reread/retry a failed planner decision.

- [ ] **Step 3: Recompute relevant evidence before any mutation**

For acceptance actions, rebuild the candidate evaluation from the persisted order and its exact material policy against current relevant state. Compare its `BasisFingerprint` and capacity/material policy to the persisted evaluation. If any relevant fact changed, return:

```python
JSONResponse(
    status_code=409,
    content={
        "Endpoint": endpoint,
        "StatusCode": 409,
        "Data": {
            "Status": "OrderCommitmentEvaluationStale",
            "EvaluationID": evaluation_id,
            "Message": "Capacity, material, schedule, calendar, or reference evidence changed; re-evaluate before deciding.",
        },
    },
)
```

Do not mark the old row stale in this failing request; a 409 write is rolled back by middleware. The next explicit re-evaluation preserves history and supersedes it.

- [ ] **Step 4: Implement rejection and exact replay before new acceptance**

If status is `Rejected`, return the existing result only when the persisted decision fingerprint equals the incoming decision fingerprint. If status is `AcceptedPendingFormalSchedule`, return the existing decision/batch only on the same exact decision fingerprint and a verifiable persisted Phase 0 result; otherwise return 409. This preserves Phase 0's lifetime one-batch-per-demand rule.

For a new `Reject`, call `rejected_evaluation_record`, replace only the evaluation row, append one stable `OrderCommitmentRejected` event, and return sanitized detail. Create no shared planning objects.

- [ ] **Step 5: Apply option-2 acceptance inside the existing write boundary**

For a new acceptance:

```python
write_set = prepare_mto_acceptance(
    evaluation=evaluation,
    existing_commitments=planning_demand_commitments,
    decision_id=payload.DecisionID,
    decision=payload.Decision,
    decided_by=_effective_actor_id(request, payload.DecidedBy),
    decided_at=server_utc_now(),
    reason=payload.Reason,
    ccr_risk_acknowledged=payload.CcrRiskAcknowledged,
    material_risk_acknowledged=payload.MaterialRiskAcknowledged,
)
apply_reservation_write_set(
    write_set=write_set,
    commitments=planning_demand_commitments,
    batches=planning_reservation_batches,
    capacity_reservations=ccr_capacity_reservations,
    material_allocations=material_planning_allocations,
    events=planning_reservation_events,
    processed_event_keys=processed_planning_event_keys,
)
updated = accepted_evaluation_record(
    evaluation=evaluation,
    write_set=write_set,
    decision_id=payload.DecisionID,
    decision=payload.Decision,
    decided_by=_effective_actor_id(request, payload.DecidedBy),
    decided_at=server_utc_now(),
    reason=payload.Reason,
    ccr_risk_acknowledged=payload.CcrRiskAcknowledged,
    material_risk_acknowledged=payload.MaterialRiskAcknowledged,
)
order_commitment_evaluations[evaluation_id] = updated
```

Append `OrderCommitmentAccepted` after the shared write-set call. If any domain error occurs, map its `.status` to a structured 409. Existing middleware's complete snapshot/restore and SQLite save transaction guarantee all-or-nothing persistence; do not add a nested `atomic_update` while `state_admission` holds the store lock.

Return:

```python
{
    "Endpoint": endpoint,
    "StatusCode": 200,
    "Data": {
        "Evaluation": sanitized_row,
        "DemandCommitmentID": write_set.demand_commitment["DemandCommitmentID"],
        "ReservationBatchID": write_set.batch["ReservationBatchID"],
        "CapacityReservationIDs": list(write_set.batch["CapacityReservationIDs"]),
        "MaterialAllocationIDs": list(write_set.batch["MaterialAllocationIDs"]),
        "Status": "AcceptedPendingFormalSchedule",
        "ExternalOrderAcceptance": "NotPerformed",
        "PlanningRunCreation": "NotPerformed",
        "ProductionMutation": "NotPerformed",
    },
}
```

- [ ] **Step 6: Expose MTO linkage in the existing shared reservation read model**

When `planning_reservation_workbench()` enriches a batch from its demand commitment, add sanitized `OrderCommitmentEvaluationID`, `AcceptedPromiseAt`, and `MaterialCommitmentStatus`. Do not add `PendingMaterialRequirements`, fingerprints, or raw order content to the shared list row.

- [ ] **Step 7: Run the complete API transaction slice**

Run:

```powershell
pytest tests/test_api.py tests/test_order_commitment_evaluation.py tests/test_order_commitment_view.py tests/test_planning_commitments.py tests/test_planning_reservations.py tests/test_planning_reservation_view.py tests/test_state_store.py -q -k "order_commitment or planning_reservation" --basetemp .tmp/pytest-mto-decision-green -p no:cacheprovider
```

Expected: PASS. Acceptance is atomic and internal; no test observes a new Planning Run, master-data mutation, integration message, DDAE feedback, ERP/WMS allocation claim, or MES output.

- [ ] **Step 8: Commit the planner-decision transaction**

```powershell
git add -- sdbr/api.py tests/test_api.py
git commit -m "feat: activate MTO reservations on planner decision"
```

---

### Task 7: Backend Integration Verification and Evidence

**Files:**
- Modify: `docs/backend-specification.md`

**Interfaces:**
- Verifies the complete `BE-SDBR-006` through `BE-SDBR-010` path and preserved `BE-RUN-011` bridge.
- Does not implement UI in this task.

- [ ] **Step 1: Run compile and focused backend suites**

Run:

```powershell
python -m compileall -q sdbr
pytest tests/test_ccr_shadow_scheduler.py tests/test_order_commitment_evaluation.py tests/test_order_commitment_view.py tests/test_planning_commitments.py tests/test_planning_reservations.py tests/test_planning_reservation_view.py tests/test_planning_run_reservation_bridge.py tests/test_state_store.py tests/test_sdbr_market_control.py tests/test_api.py -q -k "order_commitment or ccr_shadow or planning_commitment or planning_reservation or ccr_planned_load" --basetemp .tmp/pytest-mto-order-commitment-backend -p no:cacheprovider
```

Expected: compile exits 0 with no output; focused tests pass. The only acceptable warning is the repository's existing Starlette `TestClient` / `httpx` deprecation warning, if still present.

- [ ] **Step 2: Run preserved business-path regressions**

Run:

```powershell
pytest tests/test_scheduling_solver.py tests/test_schedule_output.py tests/test_release_candidates.py tests/test_release_authorization.py tests/test_material_state.py tests/test_sdbr_market_control.py tests/test_sdbr_what_if.py tests/test_planning_run_reservation_bridge.py tests/test_api.py -q --basetemp .tmp/pytest-mto-preserved-business-paths -p no:cacheprovider
```

Expected: PASS. Light-MRP material coverage remains in `tests/test_material_state.py` and `tests/test_api.py`; this repository does not have a separate `tests/test_light_mrp.py` file.

- [ ] **Step 3: Verify scope and citation hygiene**

Run:

```powershell
rg -n "BE-SDBR-010|UI-COMMIT-001" tests sdbr docs/backend-specification.md docs/ui-specification.md
rg -n "ExternalOrderAcceptance|PlanningRunCreation|ProductionMutation|ReferenceFallback" sdbr tests
git diff --check
git status --short
```

Expected:

- new backend tests cite `BE-SDBR-010` and shared-ledger IDs where applicable;
- no changed path is under `nofinish/` or `DDAE_INTERFACE_CONTRACT`;
- no changed code adds a DDAE threshold field or external-order mutation;
- `git diff --check` exits 0;
- only intended MTO workflow files are modified.

- [ ] **Step 4: Update backend status and repeatable evidence**

Change `BE-SDBR-010` from `[NOT-STARTED]` to `[PARTIAL]` and replace planned evidence with exact implemented files/endpoints/tests. Keep `[PARTIAL]` because the current adapter has only the reference threshold, external order authority is absent, formal Planning Run creation is explicit and separate, and production ERP/MES mutation is out of scope.

Update the dated acceptance record with:

- exact compile command and exit result;
- exact focused and preserved-suite commands with observed pass/deselect/warning counts and elapsed time;
- implemented endpoint list;
- explicit proof that intake produced no demand/reservation and acceptance produced no Planning Run/integration message;
- remaining `ReferenceFallback`, external authority, and formal scheduling boundaries.

Do not invent counts before the commands run.

- [ ] **Step 5: Commit backend evidence**

```powershell
git add -- docs/backend-specification.md
git commit -m "docs: record MTO commitment backend evidence"
```

---

### Task 8: UI-COMMIT-001 Order Commitment Workbench and Confirmation Gate

**Files:**
- Modify: `sdbr/web/planner-workbench.html`
- Modify: `sdbr/web/planner-workbench.js`
- Modify: `sdbr/web/planner-workbench.css`
- Modify: `tests/test_api.py`
- Modify: `docs/ui-specification.md`

**Interfaces:**
- Consumes Task 5/6 list, detail, re-evaluation, and decision endpoints.
- Captures `X-Workbench-Revision` from GET/detail and sends it as `If-Match` on decision.
- Produces hash route `#order-commitments`, independent view `order-commitments-view`, detail drawer `order-commitment-detail`, and dialog `order-commitment-decision-dialog`.
- This task is UI acceptance unit 13. After verification and the evidence commit, stop and request user confirmation; do not mark `用户已确认` without the user's response.

- [ ] **Step 1: Change UI status to development before UI code**

In `docs/ui-specification.md`, change only `UI-COMMIT-001` and the 17.13 record from `未开始` to `开发中`. Do not change any unrelated pending UI item.

- [ ] **Step 2: Write failing static UI acceptance tests**

Add to `tests/test_api.py`:

```python
# UI-COMMIT-001 / BE-SDBR-010
def test_planner_workbench_page_exposes_order_commitment_option2_workflow():
    client = TestClient(create_app())

    html = client.get("/planner/workbench").text
    script = client.get("/planner/assets/planner-workbench.js").text
    css = client.get("/planner/assets/planner-workbench.css").text

    assert 'data-route="order-commitments"' in html
    assert 'id="order-commitments-view"' in html
    assert 'id="order-commitment-table-body"' in html
    assert 'id="order-commitment-empty"' in html
    assert 'id="order-commitment-detail"' in html
    assert 'id="order-commitment-material-check"' in html
    assert 'id="order-commitment-material-skip-reason"' in html
    assert 'id="order-commitment-decision-dialog"' in html
    assert 'id="order-commitment-ccr-ack"' in html
    assert 'id="order-commitment-material-ack"' in html
    assert 'id="order-commitment-decision-reason"' in html
    assert "/planner/workbench/order-commitments/workbench" in script
    assert "/reevaluate`" in script
    assert "/decision`" in script
    assert '"If-Match": orderCommitmentRevision' in script
    assert "AcceptedPendingFormalSchedule" in script
    assert 'orderCommitmentMaterialGateReminder: "释放阶段仍执行物料硬门控"' in script
    assert 'orderCommitmentExternalBoundary: "不会自动接受外部订单，也不会创建 Planning Run 或修改 ERP/MES"' in script
    assert "JSON.stringify(detail" not in script
    assert ".order-commitment-workbench" in css
    assert ".order-commitment-decision-grid" in css


def test_semantic_shell_includes_order_commitment_route_and_updated_nav_count():
    html = TestClient(create_app()).get("/planner/workbench").text

    assert 'data-route="order-commitments"' in html
    assert html.count("data-nav-help") == 14
```

Add an API-driven UI contract test that creates an evaluation, reads workbench/detail, conditionally accepts it, and asserts every field referenced by JavaScript exists. This prevents a static-only UI from drifting from the backend response.

Run:

```powershell
pytest tests/test_api.py -q -k "order_commitment_option2 or semantic_shell_includes_order_commitment or order_commitment_ui_contract" --basetemp .tmp/pytest-mto-ui-red -p no:cacheprovider
```

Expected: FAIL because route/view/drawer/dialog/scripts/styles do not exist.

- [ ] **Step 3: Add the independent navigation route and dense workbench markup**

Insert the navigation item after Materials Planning and renumber subsequent numeric visual indices by one; keep `D1` unchanged:

```html
<a class="nav-item" href="#order-commitments" data-route="order-commitments" data-nav-help>
  <span class="nav-index" aria-hidden="true">05</span>
  <span data-i18n="navOrderCommitments">订单承诺</span>
</a>
```

Insert the view between material planning and Planning Runs:

```html
<div id="order-commitments-view" class="order-commitments-view" hidden>
  <section class="order-commitment-summary" aria-label="订单承诺摘要" data-i18n-aria-label="orderCommitmentSummary">
    <div><span data-i18n="awaitingDecision">待决定</span><strong data-order-commitment-summary="AwaitingDecisionCount">0</strong></div>
    <div><span data-i18n="confirmationRequired">需确认</span><strong data-order-commitment-summary="ConfirmationRequiredCount">0</strong></div>
    <div><span data-i18n="materialPending">物料待确认</span><strong data-order-commitment-summary="MaterialPendingCount">0</strong></div>
    <div><span data-i18n="acceptedPendingSchedule">已接受，待正式排程</span><strong data-order-commitment-summary="AcceptedPendingScheduleCount">0</strong></div>
  </section>
  <div id="order-commitment-error" class="persistent-error" role="alert" hidden>
    <strong data-i18n="orderCommitmentLoadFailed">无法读取订单承诺评估</strong>
    <span data-i18n="orderCommitmentRetryAdvice">请刷新最新评估证据后重试。</span>
  </div>
  <section id="order-commitment-content" class="order-commitment-workbench" hidden>
    <div class="compact-toolbar">
      <label><span data-i18n="searchOrderOrProduct">搜索订单或产品</span><input id="order-commitment-search" type="search"></label>
      <label><span data-i18n="status">状态</span><select id="order-commitment-status-filter"><option value="" data-i18n="allStatuses">全部状态</option></select></label>
      <button id="refresh-order-commitments" class="button secondary" type="button" data-i18n="refresh">刷新</button>
    </div>
    <div class="table-scroll">
      <table id="order-commitment-table" class="data-table">
        <thead><tr>
          <th data-i18n="order">订单</th><th data-i18n="product">产品</th>
          <th data-i18n="requestedDueAt">请求交期</th><th data-i18n="earliestSafePromise">建议安全日期</th>
          <th data-i18n="ccrLoadBeforeAfter">CCR 负荷前后</th><th data-i18n="protectionThresholdSource">保护线来源</th>
          <th data-i18n="materialStatus">物料状态</th><th data-i18n="recommendation">建议</th>
          <th data-i18n="reservationStatus">预留状态</th><th data-i18n="actions">操作</th>
        </tr></thead>
        <tbody id="order-commitment-table-body"></tbody>
      </table>
    </div>
  </section>
  <div id="order-commitment-empty" class="table-empty" hidden>
    <strong data-i18n="noOrderCommitments">尚无订单承诺评估</strong>
    <span data-i18n="orderCommitmentIntakeHint">新订单通过 Mock API 进入后会自动评估。</span>
  </div>
</div>
```

Do not add an order-entry form to this UI scope. New orders enter through the canonical Mock API; the page is the planner's assessment and decision workbench.

- [ ] **Step 4: Add detail, material re-evaluation, and option-2 decision markup**

Add one standard side drawer:

```html
<aside id="order-commitment-detail" class="issues-drawer run-detail" aria-labelledby="order-commitment-detail-title" aria-hidden="true" hidden>
  <div class="drawer-heading">
    <div><span class="panel-kicker" data-i18n="orderCommitmentEvaluation">订单承诺评估</span><h2 id="order-commitment-detail-title">-</h2></div>
    <button id="close-order-commitment-detail" class="icon-button" type="button" aria-label="关闭" data-i18n-aria-label="close">&#10005;</button>
  </div>
  <div id="order-commitment-detail-content" class="run-detail-content"></div>
  <form id="order-commitment-reevaluation-form" class="order-commitment-reevaluation">
    <label class="capability-toggle"><input id="order-commitment-material-check" type="checkbox" checked><span data-i18n="checkMaterialAvailability">检查物料计划可用性</span></label>
    <label id="order-commitment-material-skip-field" hidden><span data-i18n="materialSkipReason">跳过原因</span><textarea id="order-commitment-material-skip-reason" rows="3"></textarea></label>
    <p data-i18n="orderCommitmentMaterialGateReminder">释放阶段仍执行物料硬门控</p>
    <button id="reevaluate-order-commitment" class="button secondary" type="submit" data-i18n="reevaluate">重新评估</button>
  </form>
  <div id="order-commitment-actions" class="wizard-actions"></div>
</aside>
```

Add a dedicated dialog rather than reusing the generic yes/no dialog because acknowledgements are conditional and auditable:

```html
<dialog id="order-commitment-decision-dialog" class="run-wizard compact-dialog" aria-labelledby="order-commitment-decision-title">
  <form id="order-commitment-decision-form" method="dialog">
    <div class="drawer-heading"><div><span class="panel-kicker" data-i18n="plannerDecision">计划员决定</span><h2 id="order-commitment-decision-title">-</h2></div></div>
    <div id="order-commitment-decision-summary" class="order-commitment-decision-grid"></div>
    <label id="order-commitment-ccr-ack-field" hidden><input id="order-commitment-ccr-ack" type="checkbox"><span data-i18n="acknowledgeCcrRisk">我已复核 CCR 保护负荷风险</span></label>
    <label id="order-commitment-material-ack-field" hidden><input id="order-commitment-material-ack" type="checkbox"><span data-i18n="acknowledgeMaterialPending">我确认物料仍待处理，且释放阶段继续硬门控</span></label>
    <label><span data-i18n="decisionReason">决定原因</span><textarea id="order-commitment-decision-reason" rows="3" required></textarea></label>
    <p class="inline-note" data-i18n="orderCommitmentExternalBoundary">不会自动接受外部订单，也不会创建 Planning Run 或修改 ERP/MES</p>
    <div class="wizard-actions">
      <button id="cancel-order-commitment-decision" class="button secondary" type="button" data-i18n="cancel">取消</button>
      <button id="submit-order-commitment-decision" class="button primary" type="submit" data-i18n="confirm">确认</button>
    </div>
  </form>
</dialog>
```

Increment the planner-workbench asset query version to `v=20260711-mto-order-commitment`.

- [ ] **Step 5: Add route, translations, state, and rendering**

Add both Chinese and English keys for every new `data-i18n` value plus all backend statuses/decisions. At minimum include:

```javascript
navOrderCommitments: "订单承诺",
pageOrderCommitments: "订单承诺评估",
descriptionOrderCommitments: "自动评估新订单的 CCR 与物料影响，由计划员决定是否接受。",
orderCommitmentMaterialGateReminder: "释放阶段仍执行物料硬门控",
orderCommitmentExternalBoundary: "不会自动接受外部订单，也不会创建 Planning Run 或修改 ERP/MES",
recommendation_RecommendAccept: "建议接受",
recommendation_PlannerConfirmationRequired: "需计划员确认",
recommendation_CapacityAcceptableMaterialPending: "产能可接受，物料待确认",
recommendation_MaterialEvidenceRequired: "待物料确认",
recommendation_RecommendLaterPromise: "建议调整交期",
recommendation_DoNotRecommendAccept: "暂不建议接受",
thresholdSource_ApprovedOperatingModel: "批准的运行模型保护线",
thresholdSource_ReferenceFallback: "80% 默认参考，需确认",
status_AcceptedPendingFormalSchedule: "已接受，待正式排程",
status_AwaitingPlannerDecision: "待计划员决定",
status_Superseded: "已由新评估替代",
```

Add corresponding English strings. Add the route:

```javascript
"order-commitments": ["pageOrderCommitments", "descriptionOrderCommitments"],
```

Add state:

```javascript
let orderCommitmentData = null;
let orderCommitmentRevision = null;
let selectedOrderCommitment = null;
let selectedOrderCommitmentAction = null;
```

Update `renderRoute` to hide/show/load `order-commitments-view`. Add `order-commitments` to navigation help automatically through `ROUTES`.

Implement:

```javascript
async function loadOrderCommitments() {
  const response = await fetch("/planner/workbench/order-commitments/workbench", { headers: { Accept: "application/json" } });
  orderCommitmentRevision = response.headers.get("X-Workbench-Revision");
  if (!response.ok) throw new Error("Order commitment workbench unavailable");
  orderCommitmentData = (await response.json()).Data;
  renderOrderCommitments();
}

async function openOrderCommitmentDetail(evaluationId) {
  const response = await fetch(`/planner/workbench/order-commitments/${encodeURIComponent(evaluationId)}`);
  orderCommitmentRevision = response.headers.get("X-Workbench-Revision") || orderCommitmentRevision;
  if (!response.ok) throw new Error("Order commitment detail unavailable");
  selectedOrderCommitment = (await response.json()).Data;
  renderOrderCommitmentDetail();
  openSideDrawer("order-commitment-detail");
}
```

`renderOrderCommitments` must filter by order/product/status, use text plus status classes, render an explicit `ViewDetails` button, and show a real empty state. `renderOrderCommitmentDetail` must render business sections for capacity, material, recommendation, accepted reservation, audit, and a collapsed `<details class="technical-detail">`; it must never call `JSON.stringify` on the detail.

- [ ] **Step 6: Implement re-evaluation and revision-guarded decision UI**

Material toggle behavior:

```javascript
function updateOrderCommitmentMaterialSkipField() {
  const enabled = document.getElementById("order-commitment-material-check").checked;
  document.getElementById("order-commitment-material-skip-field").hidden = enabled;
  document.getElementById("order-commitment-material-skip-reason").required = !enabled;
}
```

Re-evaluation sends the selected evaluation's baseline run, current toggle, reason, and window. If material checking is off and reason is blank, show an inline/error notification and do not call the API. On success, close/reopen the new detail and refresh the list; capture the new response revision.

Decision submission must use:

```javascript
const response = await fetch(
  `/planner/workbench/order-commitments/${encodeURIComponent(selectedOrderCommitment.EvaluationID)}/decision`,
  {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "If-Match": orderCommitmentRevision
    },
    body: JSON.stringify({
      DecisionID: `DEC-${selectedOrderCommitment.EvaluationID}-${selectedOrderCommitmentAction}`,
      Decision: selectedOrderCommitmentAction,
      DecidedBy: "planner-1",
      Reason: document.getElementById("order-commitment-decision-reason").value.trim(),
      ExpectedEvaluationFingerprint: selectedOrderCommitment.TechnicalDetails.EvaluationFingerprint,
      CcrRiskAcknowledged: document.getElementById("order-commitment-ccr-ack").checked,
      MaterialRiskAcknowledged: document.getElementById("order-commitment-material-ack").checked
    })
  }
);
```

Before fetch, require a reason and any visible acknowledgement. On `409 StateStoreRevisionConflict` or `OrderCommitmentEvaluationStale`, keep the dialog state, show the localized stale message, refresh list/detail, and require the planner to choose again. Never auto-retry a decision. On success, close the dialog, refresh, and show `AcceptedPendingFormalSchedule` or `Rejected`.

Bind all new controls in `DOMContentLoaded`, include `order-commitment-detail` in the drawer close list, and re-render the current workbench/detail on language change.

- [ ] **Step 7: Add restrained responsive styles**

Add selectors for `.order-commitments-view`, `.order-commitment-summary`, `.order-commitment-workbench`, `.order-commitment-reevaluation`, `.order-commitment-decision-grid`, and compact status/action rows. Follow existing variables and radius limits. Do not add gradients, decorative blobs, nested cards, negative letter spacing, or a new one-hue palette.

Required layout behavior:

- desktop summary uses four stable columns and the table scrolls inside its container;
- drawer controls never overlap the fixed header;
- labels wrap before controls shrink;
- at `max-width: 900px`, summary becomes two columns, toolbar becomes one column, dialog width is `min(100% - 24px, 640px)`, and no page-level horizontal overflow appears;
- status colors always include visible text.

- [ ] **Step 8: Run static, syntax, focused, and full automated verification**

Run:

```powershell
node --check sdbr/web/planner-workbench.js
python -m compileall -q sdbr
pytest tests/test_ccr_shadow_scheduler.py tests/test_order_commitment_evaluation.py tests/test_order_commitment_view.py tests/test_state_store.py tests/test_sdbr_market_control.py tests/test_api.py -q -k "order_commitment or ccr_shadow" --basetemp .tmp/pytest-mto-ui-focused -p no:cacheprovider
pytest -q --basetemp .tmp/pytest-full-mto-order-commitment -p no:cacheprovider
git diff --check
```

Expected: JavaScript/Python checks exit 0, focused and full suites pass, and diff check is clean. Record actual counts and the existing warning accurately.

- [ ] **Step 9: Perform browser verification on test state**

Use the browser-control skill. Start a test-only server on an unused port (8765 unless occupied):

```powershell
$env:SDBR_ENVIRONMENT = "test"
python -m uvicorn sdbr.api:app --host 127.0.0.1 --port 8765
```

Open `http://127.0.0.1:8765/planner/workbench#order-commitments`. Verify:

1. 1280x720: navigation, title, summary, table, empty/error states, and drawer do not overlap or clip.
2. 390x844: navigation drawer, summary, table container, detail, material controls, and decision dialog stay within viewport; page `scrollWidth` equals client width.
3. Chinese/English switching updates route, table, statuses, acknowledgements, boundary copy, and detail labels while IDs remain unchanged.
4. Keyboard focus can open the route and detail actions; dialog labels/checkboxes have visible focus.
5. With an API-created evaluation, ordinary list/detail works, reference-threshold warning is visible, material opt-out requires reason, required acknowledgements block submit, and stale 409 is shown rather than retried.
6. Accepted result reads “已接受，待正式排程” and still states that no external order, Planning Run, or ERP/MES mutation occurred.
7. Browser console has no uncaught errors.

Capture desktop and narrow screenshots in `.tmp/` for local evidence only; do not commit them unless the user separately requests durable visual artifacts. Stop the server after checks.

- [ ] **Step 10: Update UI evidence and hold for user confirmation**

Change `UI-COMMIT-001` and record 17.13 from `开发中` to `已验证待用户确认`. Add:

- exact focused/full test commands and observed counts;
- `node --check` and compile results;
- desktop/narrow viewport results;
- bilingual, keyboard, stale-state, material-toggle, and option-2 decision observations;
- the local URL used;
- unchanged boundary: no DDAE contract expansion, external acceptance, Planning Run creation, or production ERP/MES mutation.

Do not write `用户已确认`.

- [ ] **Step 11: Commit the UI acceptance unit and evidence**

```powershell
git add -- sdbr/web/planner-workbench.html sdbr/web/planner-workbench.js sdbr/web/planner-workbench.css tests/test_api.py docs/ui-specification.md
git commit -m "feat: add MTO order commitment workbench"
```

- [ ] **Step 12: Stop at the repository confirmation gate**

Report `UI-COMMIT-001`, commits, test evidence, and the view URL. Ask the user to confirm acceptance unit 13. Do not begin MTA workflow, external-order integration, formal-order scheduling injection, or any subsequent UI acceptance unit until the user responds.

---

## Requirement Coverage Map

| Approved requirement | Implementation task | Repeatable evidence |
|---|---|---|
| New order triggers assessment automatically | Task 5 intake endpoint | `test_order_intake_automatically_evaluates_but_creates_no_commitment_or_reservation` |
| System recommends; planner decides | Tasks 3, 5, 6 | recommendation matrix, no-write intake assertions, option-2 decision endpoint |
| On-time but protected-load threshold exceeded requires confirmation | Tasks 2, 3, 6, 8 | threshold test, acknowledgement rejection test, UI checkbox test |
| Current missing DDAE threshold uses marked 80% reference only | Tasks 1, 3, 5, 7 | pure reference-policy test, API fallback assertion, scope scan |
| Material check is default | Tasks 3 and 5 | default material API/domain tests |
| Planner may opt out with reason | Tasks 3, 5, 6, 8 | re-evaluation reason test, conditional acceptance test, UI required field |
| Material opt-out cannot claim feasibility or bypass release | Tasks 3, 6, 7, 8 | zero-allocation/pending-requirement assertions and preserved release regressions |
| Accepted option-2 action creates shared CCR reservation | Task 6 | atomic acceptance API test and Phase 0 suites |
| Material pass creates shared planning allocation | Tasks 3 and 6 | Phase 0 write-set and API allocation assertions |
| Stale evaluation cannot confirm | Task 6 | relevant-ledger drift and `If-Match` tests |
| Concurrent confirmations cannot double promise | Task 6 | one-success/one-revision-conflict concurrency test |
| Duplicate messages/clicks are idempotent | Tasks 3, 5, 6 | duplicate intake and exact decision replay tests |
| Planning success converts; failure preserves reservation | Task 7 | existing `tests/test_planning_run_reservation_bridge.py` in focused regression |
| No DDAE contract expansion | Tasks 1, 5, 7 | reference-only adapter plus changed-path/content scans |
| No automatic external acceptance | Tasks 5, 6, 8 | store assertions and explicit `NotPerformed` response/UI boundary |
| No production ERP/MES mutation | Tasks 5, 6, 7, 8 | integration collections unchanged, full regression, boundary copy |
| Independent planner workbench and user confirmation gate | Task 8 | static/UI contract tests, browser checks, `已验证待用户确认` stop |

## Final Execution Checklist

- [ ] Specification rows and change logs were committed before code.
- [ ] Intake is automatic and idempotent but recommendation-only.
- [ ] Approved-threshold exceedance and all reference-fallback results require planner CCR acknowledgement.
- [ ] Material check defaults on; skip requires reason and produces zero material allocations.
- [ ] Material shortage/evidence gaps cannot be accepted as feasible.
- [ ] Acceptance uses the existing canonical demand and Phase 0 reservation functions.
- [ ] Capacity/material/evaluation/decision writes are atomic across save failures and revision conflicts.
- [ ] Competing confirmations cannot both consume one revision/capacity view.
- [ ] Intake and acceptance create no external acceptance, production integration message, master-data mutation, or automatic Planning Run.
- [ ] Accepted result is `AcceptedPendingFormalSchedule` with a traceable batch ID.
- [ ] Existing Planning Run bridge, P1 market control, What-if, release material gate, and full suite remain green.
- [ ] UI exposes no raw JSON and passes desktop/narrow/bilingual/keyboard/stale-state checks.
- [ ] UI status stops at `已验证待用户确认` until explicit user confirmation.
- [ ] `nofinish/` and DDAE contract files remain untouched.

## Execution Handoff

Use `superpowers:subagent-driven-development` for task-by-task implementation with review after each commit, or `superpowers:executing-plans` for checkpointed inline execution. Because Task 8 is a repository-mandated UI acceptance gate, either execution mode must stop after Task 8 and wait for explicit user confirmation.
