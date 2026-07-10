# S-DBR Native What-If Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a P2 S-DBR native execution-level what-if capability for order insertion, downtime, supply delay, and MTA red-zone replenishment shock, plus a Simio recommendation tooltip on the simulation tab.

**Architecture:** The first implementation stays inside the S-DBR execution read-model layer. It reuses frozen schedule output, CCR planned load, MTO/MTA buffer priority, DDMRP runtime lines, release gates, and resource calendar capacity; it does not create new DDAE protocol fields and does not run Simio as the primary decision engine. Simio remains optional high-fidelity validation and is surfaced as a business hint in the simulation results panel.

**Tech Stack:** Python 3.12, FastAPI, in-memory/SQLite `WorkbenchStateStore`, pytest, vanilla HTML/CSS/JavaScript planner workbench.

## Global Constraints

- SDBR remains a DDOM / S-DBR execution system only.
- Do not implement DDS&OP workflows, DDAE master-setting governance, Buffer Profile governance, or strategic what-if simulation.
- DDAE-origin time buffers, control points, DDMRP parameters, resource roles, and scheduling settings must be consumed according to contracts; do not silently extend their meaning.
- OR-Tools CP-SAT remains the active solver for actual planning runs; this P2 what-if is a read-model simulation, not a new solver path.
- Simio is optional post-schedule validation; do not make it a release/publication hard gate.
- `docs/backend-specification.md` and `docs/ui-specification.md` must be updated before or with implementation.
- Do not expose raw JSON master-data payloads in the normal planner workflow.
- Do not track `nofinish/`.

---

## File Structure

- Create `sdbr/sdbr_what_if.py`
  - Owns S-DBR native scenario modeling and impact calculation.
  - Exposes pure functions:
    - `build_sdbr_what_if_workspace(...) -> dict[str, object]`
    - `evaluate_sdbr_what_if_scenario(...) -> dict[str, object]`
  - No API, store mutation, or UI concerns.
- Modify `sdbr/api.py`
  - Adds read-only scenario workspace endpoint and stateless evaluation endpoint.
  - Does not persist what-if scenarios in P2 first pass.
- Modify `sdbr/schedule_result_view.py`
  - Reuses existing `SDBRMarketControl` and load inputs when building what-if workspace data.
  - Keeps existing schedule result workbench response stable.
- Modify `sdbr/web/planner-workbench.html`
  - Adds a compact what-if section under schedule results market-control area.
  - Adds Simio recommendation help tooltip in the simulation results tab.
- Modify `sdbr/web/planner-workbench.js`
  - Adds i18n text, form state, API calls, result rendering, and tooltip behavior.
- Modify `sdbr/web/planner-workbench.css`
  - Adds compact cards, impact badges, and tooltip styling.
- Modify `tests/test_sdbr_what_if.py`
  - Unit tests for pure S-DBR what-if logic.
- Modify `tests/test_api.py`
  - API and UI static tests.
- Modify `docs/backend-specification.md`
  - Adds `BE-SDBR-005` P2 execution what-if capability and change-log entry.
- Modify `docs/ui-specification.md`
  - Adds `UI-SCHEDULE-002` or P2 schedule-result what-if UI acceptance notes and change-log entry.

---

### Task 1: Specification First

**Files:**
- Modify: `docs/backend-specification.md`
- Modify: `docs/ui-specification.md`

**Interfaces:**
- Consumes: Existing `BE-SDBR-001` through `BE-SDBR-004`, `BE-SIM-*`, `UI-SCHEDULE-001`.
- Produces: New implementation target IDs used by tests and reports:
  - `BE-SDBR-005`: S-DBR native execution-level what-if.
  - `UI-SCHEDULE-002`: Schedule result what-if panel and Simio recommendation hint.

- [ ] **Step 1: Update backend capability table**

Add a row near S-DBR P1 market-control capabilities:

```markdown
| `BE-SDBR-005` | Native execution what-if | `[PARTIAL]` | `C` `sdbr/sdbr_what_if.py`; `A` `/planner/workbench/schedule-results/runs/{run_id}/what-if/workspace`, `/planner/workbench/schedule-results/runs/{run_id}/what-if/evaluate`; `T` `tests/test_sdbr_what_if.py`, `tests/test_api.py` | Evaluates execution-level shocks including MTO expedite/order insertion, downtime, supplier delay, and MTA red-zone replenishment pressure against frozen CCR load, buffer status, and release assumptions. Does not mutate schedule, does not run CP-SAT, does not add DDAE protocol fields, and does not claim formal customer promise. |
```

- [ ] **Step 2: Add backend acceptance note**

Add a dated section before backend changelog:

```markdown
### BE-SDBR-005 Native execution what-if 验收记录

- 日期：2026-07-09
- 范围：P2 第一版只做执行层 what-if read model，覆盖插单/加急、停机、供应延迟、MTA 红区补货冲击是否会把 CCR 负荷推入关注、接近上限或超载。
- 边界：不创建新 Planning Run；不修改冻结排程；不调用 CP-SAT；不新增 DDAE 协议；不将 Simio 作为主决策引擎。
- 业务输出：返回 CCR 负荷变化、保护能力状态、MTO 安全承诺影响、MTA/MTO 统一缓冲优先级变化、建议动作和是否建议用 Simio 高保真验证。
- 状态：`[PARTIAL]`，待实现和重复测试证据。
```

- [ ] **Step 3: Add backend changelog row**

Add the next changelog row:

```markdown
| 2.71 | 2026-07-09 | 启动 P2 S-DBR 原生 execution what-if 规格：插单、停机、供应延迟、MTA 红区补货冲击先由 S-DBR 快速评估 CCR 风险；Simio 作为复杂动态系统的可选高保真验证提示 |
```

- [ ] **Step 4: Add UI acceptance note**

Add a schedule-result UI acceptance section:

```markdown
### P2 S-DBR 执行级 What-if UI 验收记录

- 范围：排程结果页提供只读/轻编辑 what-if 面板，支持选择插单、停机、供应延迟和 MTA 红区补货冲击，并展示 CCR 风险、缓冲影响、建议动作和 Simio 推荐验证提示。
- 边界：不暴露 DDAE 参数配置，不生成正式 Planning Run，不把 Simio 作为默认主引擎。
- Simio 提示：仿真结果页提供“什么时候建议使用 Simio”的悬浮说明，覆盖多 CCR 组合、停机/返工/检测失败、多次访问同资源、复杂 routing 分支、搬运/等待/批处理/换型占比高、需要展示动态排队爆发过程、已有稳定 Simio 模型和数据维护机制等条件。
- 状态：待实现。
```

- [ ] **Step 5: Run no-op documentation check**

Run: `rg -n "BE-SDBR-005|UI.*What-if|Simio 提示" docs`

Expected: New spec rows and acceptance notes are visible.

---

### Task 2: Pure What-If Engine

**Files:**
- Create: `sdbr/sdbr_what_if.py`
- Test: `tests/test_sdbr_what_if.py`

**Interfaces:**
- Consumes:
  - `build_ccr_planned_load(...)` output shape from `sdbr/sdbr_market_control.py`
  - DDMRP runtime lines from master data version
  - Scenario payload dictionaries from API/UI
- Produces:
  - `build_sdbr_what_if_workspace(...) -> dict[str, object]`
  - `evaluate_sdbr_what_if_scenario(...) -> dict[str, object]`

- [ ] **Step 1: Write failing test for expedite/order insertion impact**

Create `tests/test_sdbr_what_if.py`:

```python
from datetime import datetime, timezone

from sdbr.sdbr_what_if import evaluate_sdbr_what_if_scenario


def _ccr_load():
    return {
        "Summary": {
            "Status": "Protected",
            "ProtectiveCapacityTargetPercent": 80.0,
        },
        "Buckets": [
            {
                "ResourceID": "CCR-1",
                "ResourceName": "测试-约束机加工",
                "Date": "2026-07-10",
                "CapacityMinutes": 480,
                "MtoLoadMinutes": 300,
                "MtaLoadMinutes": 0,
                "TotalPlannedLoadMinutes": 300,
                "LoadPercent": 62.5,
                "Status": "Protected",
                "DemandBreakdown": [],
            }
        ],
    }


def test_expedite_order_shock_marks_ccr_watch_when_protective_capacity_is_consumed():
    result = evaluate_sdbr_what_if_scenario(
        ccr_planned_load=_ccr_load(),
        scenario={
            "ScenarioType": "MTO_EXPEDITE",
            "ResourceID": "CCR-1",
            "BucketDate": "2026-07-10",
            "AdditionalLoadMinutes": 120,
            "DemandClass": "MTO",
            "Reason": "客户插单",
        },
        evaluated_at=datetime(2026, 7, 9, 8, 0, tzinfo=timezone.utc),
    )

    assert result["ScenarioType"] == "MTO_EXPEDITE"
    assert result["Impact"]["BeforeLoadPercent"] == 62.5
    assert result["Impact"]["AfterLoadPercent"] == 87.5
    assert result["Impact"]["AfterStatus"] == "Watch"
    assert result["Recommendation"]["Decision"] == "AbsorbWithBufferAndProtectiveCapacity"
    assert result["Recommendation"]["RequiresFormalReplan"] is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_sdbr_what_if.py::test_expedite_order_shock_marks_ccr_watch_when_protective_capacity_is_consumed -q`

Expected: FAIL with `ModuleNotFoundError: No module named 'sdbr.sdbr_what_if'`.

- [ ] **Step 3: Implement minimal what-if engine**

Create `sdbr/sdbr_what_if.py`:

```python
from __future__ import annotations

from datetime import datetime
from typing import Any


PROTECTIVE_CAPACITY_TARGET_PERCENT = 80.0
NEAR_LIMIT_PERCENT = 90.0


def evaluate_sdbr_what_if_scenario(
    *,
    ccr_planned_load: dict[str, object],
    scenario: dict[str, object],
    evaluated_at: datetime | None = None,
) -> dict[str, object]:
    bucket = _find_bucket(
        ccr_planned_load=ccr_planned_load,
        resource_id=str(scenario.get("ResourceID") or ""),
        bucket_date=str(scenario.get("BucketDate") or ""),
    )
    additional = max(int(scenario.get("AdditionalLoadMinutes") or 0), 0)
    if not bucket:
        return _blocked_result(
            scenario=scenario,
            code="CCR_BUCKET_NOT_FOUND",
            message="找不到对应的约束资源负荷窗口，不能评估本次冲击。",
        )

    before_minutes = int(bucket.get("TotalPlannedLoadMinutes") or 0)
    capacity = int(bucket.get("CapacityMinutes") or 0)
    after_minutes = before_minutes + additional
    before_percent = _percent(before_minutes, capacity)
    after_percent = _percent(after_minutes, capacity)
    before_status = str(bucket.get("Status") or _status(before_percent))
    after_status = _status(after_percent)
    return {
        "Mode": "SDBRNativeWhatIfV1",
        "ScenarioType": str(scenario.get("ScenarioType") or "MTO_EXPEDITE"),
        "EvaluatedAt": evaluated_at.isoformat() if evaluated_at else None,
        "Impact": {
            "ResourceID": bucket.get("ResourceID"),
            "ResourceName": bucket.get("ResourceName"),
            "BucketDate": bucket.get("Date"),
            "CapacityMinutes": capacity,
            "BeforeLoadMinutes": before_minutes,
            "AdditionalLoadMinutes": additional,
            "AfterLoadMinutes": after_minutes,
            "BeforeLoadPercent": before_percent,
            "AfterLoadPercent": after_percent,
            "BeforeStatus": before_status,
            "AfterStatus": after_status,
        },
        "Recommendation": _recommendation(after_status),
        "SimioRecommendation": simio_recommendation_hint(scenario=scenario),
        "Boundary": (
            "S-DBR native execution what-if; does not mutate the frozen schedule, "
            "does not run CP-SAT, and does not claim production validation."
        ),
    }


def build_sdbr_what_if_workspace(
    *,
    ccr_planned_load: dict[str, object],
    ddmrp_lines: list[dict[str, object]],
) -> dict[str, object]:
    return {
        "Mode": "SDBRNativeWhatIfWorkspaceV1",
        "ScenarioTypes": [
            "MTO_EXPEDITE",
            "RESOURCE_DOWNTIME",
            "SUPPLY_DELAY",
            "MTA_RED_REPLENISHMENT_SHOCK",
        ],
        "CcrBuckets": [
            {
                "ResourceID": item.get("ResourceID"),
                "ResourceName": item.get("ResourceName"),
                "Date": item.get("Date"),
                "CapacityMinutes": item.get("CapacityMinutes"),
                "TotalPlannedLoadMinutes": item.get("TotalPlannedLoadMinutes"),
                "LoadPercent": item.get("LoadPercent"),
                "Status": item.get("Status"),
            }
            for item in _dict_list(ccr_planned_load.get("Buckets"))
        ],
        "MtaRedCandidates": [
            item
            for item in ddmrp_lines
            if str(item.get("PlanningStatus") or "").lower() == "red"
        ],
        "Boundary": (
            "Workspace data for execution-level S-DBR what-if only; no DDAE "
            "parameter governance or production promise claim."
        ),
    }


def simio_recommendation_hint(*, scenario: dict[str, object] | None = None) -> dict[str, object]:
    conditions = [
        "CCR 不是单一资源，而是一组设备、人员、夹具或搬运能力组合。",
        "停机、返工、检测失败对结果影响很大。",
        "同一个订单会多次访问同一资源。",
        "Routing 分支多，路径选择复杂。",
        "搬运、等待、批处理或换型占比很高。",
        "需要展示为什么排队爆发的动态过程。",
        "已经有稳定的 Simio 模型和数据维护机制。",
    ]
    scenario = scenario or {}
    suggested = bool(scenario.get("UseSimioRecommended")) or str(
        scenario.get("ScenarioType") or ""
    ) in {"RESOURCE_DOWNTIME", "SUPPLY_DELAY"}
    return {
        "Recommended": suggested,
        "Title": "建议使用 Simio 高保真验证的情形",
        "Conditions": conditions,
        "BusinessMeaning": (
            "S-DBR what-if 先快速判断 CCR 是否被打爆；当现场动态、排队、返工、"
            "分支路径或多资源耦合很强时，再用 Simio 解释过程和验证可执行性。"
        ),
    }


def _find_bucket(
    *,
    ccr_planned_load: dict[str, object],
    resource_id: str,
    bucket_date: str,
) -> dict[str, object] | None:
    for item in _dict_list(ccr_planned_load.get("Buckets")):
        if str(item.get("ResourceID")) == resource_id and str(item.get("Date")) == bucket_date:
            return item
    return None


def _blocked_result(*, scenario: dict[str, object], code: str, message: str) -> dict[str, object]:
    return {
        "Mode": "SDBRNativeWhatIfV1",
        "ScenarioType": str(scenario.get("ScenarioType") or "UNKNOWN"),
        "Impact": None,
        "Recommendation": {
            "Decision": "ReviewRequired",
            "RequiresFormalReplan": False,
            "ReasonCode": code,
            "BusinessMeaning": message,
        },
        "SimioRecommendation": simio_recommendation_hint(scenario=scenario),
    }


def _recommendation(status: str) -> dict[str, object]:
    if status == "Overloaded":
        return {
            "Decision": "ProtectCcrAndReviewReplan",
            "RequiresFormalReplan": True,
            "BusinessMeaning": "冲击后约束资源超载，需要先保护 CCR，并由计划员复核是否重排。",
        }
    if status == "NearLimit":
        return {
            "Decision": "ReviewBeforeRelease",
            "RequiresFormalReplan": False,
            "BusinessMeaning": "冲击后接近能力上限，应暂停自动释放并人工复核。",
        }
    if status == "Watch":
        return {
            "Decision": "AbsorbWithBufferAndProtectiveCapacity",
            "RequiresFormalReplan": False,
            "BusinessMeaning": "冲击消耗保护产能，但未打爆 CCR，优先用缓冲、加班或优先级吸收。",
        }
    return {
        "Decision": "AbsorbWithExistingPlan",
        "RequiresFormalReplan": False,
        "BusinessMeaning": "冲击仍在保护能力范围内，可按现有计划吸收并继续观察。",
    }


def _status(load_percent: float) -> str:
    if load_percent > 100:
        return "Overloaded"
    if load_percent > NEAR_LIMIT_PERCENT:
        return "NearLimit"
    if load_percent > PROTECTIVE_CAPACITY_TARGET_PERCENT:
        return "Watch"
    return "Protected"


def _percent(minutes: int, capacity: int) -> float:
    return round(minutes / capacity * 100, 2) if capacity > 0 else 0.0


def _dict_list(value: Any) -> list[dict[str, object]]:
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_sdbr_what_if.py::test_expedite_order_shock_marks_ccr_watch_when_protective_capacity_is_consumed -q`

Expected: PASS.

- [ ] **Step 5: Add downtime and overload tests**

Append to `tests/test_sdbr_what_if.py`:

```python
def test_downtime_reduces_effective_capacity_and_marks_overload():
    load = _ccr_load()
    load["Buckets"][0]["CapacityMinutes"] = 360

    result = evaluate_sdbr_what_if_scenario(
        ccr_planned_load=load,
        scenario={
            "ScenarioType": "RESOURCE_DOWNTIME",
            "ResourceID": "CCR-1",
            "BucketDate": "2026-07-10",
            "AdditionalLoadMinutes": 90,
            "Reason": "停机后剩余负荷挤压",
            "UseSimioRecommended": True,
        },
        evaluated_at=datetime(2026, 7, 9, 8, 0, tzinfo=timezone.utc),
    )

    assert result["Impact"]["AfterLoadPercent"] == 108.33
    assert result["Impact"]["AfterStatus"] == "Overloaded"
    assert result["Recommendation"]["RequiresFormalReplan"] is True
    assert result["SimioRecommendation"]["Recommended"] is True
```

- [ ] **Step 6: Run full what-if unit tests**

Run: `pytest tests/test_sdbr_what_if.py -q --basetemp .tmp/pytest-sdbr-what-if -p no:cacheprovider`

Expected: all tests pass.

---

### Task 3: API Endpoints

**Files:**
- Modify: `sdbr/api.py`
- Test: `tests/test_api.py`

**Interfaces:**
- Consumes:
  - `build_schedule_result_workbench(...)`
  - `build_sdbr_what_if_workspace(...)`
  - `evaluate_sdbr_what_if_scenario(...)`
- Produces:
  - `GET /planner/workbench/schedule-results/runs/{run_id}/what-if/workspace`
  - `POST /planner/workbench/schedule-results/runs/{run_id}/what-if/evaluate`

- [ ] **Step 1: Write failing API test**

Append near schedule-result tests in `tests/test_api.py`:

```python
def test_schedule_result_what_if_workspace_and_evaluate_api():
    client = TestClient(create_app(state_store=_schedule_result_test_store()))

    workspace = client.get(
        "/planner/workbench/schedule-results/runs/RUN-RESULT/what-if/workspace"
    )

    assert workspace.status_code == 200
    data = workspace.json()["Data"]
    assert data["Mode"] == "SDBRNativeWhatIfWorkspaceV1"
    assert "MTO_EXPEDITE" in data["ScenarioTypes"]
    assert data["Boundary"].startswith("Workspace data")

    evaluate = client.post(
        "/planner/workbench/schedule-results/runs/RUN-RESULT/what-if/evaluate",
        json={
            "ScenarioType": "MTO_EXPEDITE",
            "ResourceID": "WC-DRUM",
            "BucketDate": "2026-06-19",
            "AdditionalLoadMinutes": 60,
            "DemandClass": "MTO",
        },
    )

    assert evaluate.status_code == 200
    result = evaluate.json()["Data"]
    assert result["Mode"] == "SDBRNativeWhatIfV1"
    assert result["Impact"]["AdditionalLoadMinutes"] == 60
    assert result["SimioRecommendation"]["Title"] == "建议使用 Simio 高保真验证的情形"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_api.py::test_schedule_result_what_if_workspace_and_evaluate_api -q`

Expected: FAIL with 404 for missing endpoints.

- [ ] **Step 3: Add API payload model**

In `sdbr/api.py`, near existing Pydantic request models, add:

```python
class SdbrWhatIfScenarioPayload(BaseModel):
    ScenarioType: str = "MTO_EXPEDITE"
    ResourceID: str
    BucketDate: str
    AdditionalLoadMinutes: int = 0
    DemandClass: str | None = None
    Reason: str | None = None
    UseSimioRecommended: bool | None = None
```

- [ ] **Step 4: Add imports**

In `sdbr/api.py`, add:

```python
from sdbr.sdbr_what_if import (
    build_sdbr_what_if_workspace,
    evaluate_sdbr_what_if_scenario,
)
```

- [ ] **Step 5: Add workspace endpoint**

Near schedule-results workbench routes in `sdbr/api.py`, add:

```python
    @app.get("/planner/workbench/schedule-results/runs/{run_id}/what-if/workspace")
    def planner_workbench_schedule_result_what_if_workspace(run_id: str):
        endpoint = f"/planner/workbench/schedule-results/runs/{run_id}/what-if/workspace"
        planning_run = planning_runs.get(run_id)
        if not planning_run or planning_run.get("Status") != "Completed":
            return _error(
                endpoint,
                status="SDBRWhatIfUnavailable",
                message="S-DBR what-if requires a completed planning run.",
                status_code=400,
            )
        master_data_version = master_data_versions.get(
            str(planning_run.get("MasterDataVersionID"))
        ) or {}
        workbench = build_schedule_result_workbench(
            planning_run=planning_run,
            master_data_version=master_data_version,
            released_order_ids={
                str(item.get("OrderID"))
                for item in release_authorizations.values()
                if item.get("RunID") == run_id
            },
        )
        market = workbench.get("SDBRMarketControl") or {}
        data = build_sdbr_what_if_workspace(
            ccr_planned_load=market.get("CCRPlannedLoad") or {},
            ddmrp_lines=_dict_list(master_data_version.get("DdmrpRuntimeLines")),
        )
        return _ok(endpoint, data)
```

- [ ] **Step 6: Add evaluate endpoint**

In the same route area, add:

```python
    @app.post("/planner/workbench/schedule-results/runs/{run_id}/what-if/evaluate")
    def planner_workbench_schedule_result_what_if_evaluate(
        run_id: str,
        payload: SdbrWhatIfScenarioPayload,
    ):
        endpoint = f"/planner/workbench/schedule-results/runs/{run_id}/what-if/evaluate"
        planning_run = planning_runs.get(run_id)
        if not planning_run or planning_run.get("Status") != "Completed":
            return _error(
                endpoint,
                status="SDBRWhatIfUnavailable",
                message="S-DBR what-if requires a completed planning run.",
                status_code=400,
            )
        master_data_version = master_data_versions.get(
            str(planning_run.get("MasterDataVersionID"))
        ) or {}
        workbench = build_schedule_result_workbench(
            planning_run=planning_run,
            master_data_version=master_data_version,
            released_order_ids={
                str(item.get("OrderID"))
                for item in release_authorizations.values()
                if item.get("RunID") == run_id
            },
        )
        market = workbench.get("SDBRMarketControl") or {}
        result = evaluate_sdbr_what_if_scenario(
            ccr_planned_load=market.get("CCRPlannedLoad") or {},
            scenario=payload.model_dump(),
            evaluated_at=datetime.now(timezone.utc),
        )
        return _ok(endpoint, result)
```

- [ ] **Step 7: Run API test**

Run: `pytest tests/test_api.py::test_schedule_result_what_if_workspace_and_evaluate_api -q --basetemp .tmp/pytest-sdbr-what-if-api -p no:cacheprovider`

Expected: PASS.

---

### Task 4: UI Panel for Native What-If

**Files:**
- Modify: `sdbr/web/planner-workbench.html`
- Modify: `sdbr/web/planner-workbench.js`
- Modify: `sdbr/web/planner-workbench.css`
- Test: `tests/test_api.py`

**Interfaces:**
- Consumes:
  - `GET /planner/workbench/schedule-results/runs/{run_id}/what-if/workspace`
  - `POST /planner/workbench/schedule-results/runs/{run_id}/what-if/evaluate`
- Produces:
  - Compact schedule result what-if panel for business user review.

- [ ] **Step 1: Write failing UI static test**

Append assertions to schedule-result UI test or create a new test:

```python
def test_schedule_results_page_exposes_sdbr_native_what_if_panel():
    html = Path("sdbr/web/planner-workbench.html").read_text(encoding="utf-8")
    script = Path("sdbr/web/planner-workbench.js").read_text(encoding="utf-8")
    css = Path("sdbr/web/planner-workbench.css").read_text(encoding="utf-8")

    assert 'id="sdbr-what-if-panel"' in html
    assert 'id="sdbr-what-if-scenario-type"' in html
    assert 'id="run-sdbr-what-if"' in html
    assert "/what-if/workspace" in script
    assert "/what-if/evaluate" in script
    assert "renderSdbrWhatIfWorkspace" in script
    assert ".sdbr-what-if-panel" in css
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_api.py::test_schedule_results_page_exposes_sdbr_native_what_if_panel -q`

Expected: FAIL because the panel is not present.

- [ ] **Step 3: Add HTML panel**

In `sdbr/web/planner-workbench.html`, under the market-control panel and before publication governance, add:

```html
<section id="sdbr-what-if-panel" class="sdbr-what-if-panel" hidden>
  <div class="panel-heading">
    <div>
      <span class="panel-kicker" data-i18n="sdbrWhatIfKicker">S-DBR 执行级 What-if</span>
      <h2 data-i18n="sdbrWhatIfTitle">冲击会不会打爆约束</h2>
    </div>
  </div>
  <div class="what-if-grid">
    <label><span data-i18n="scenarioType">场景类型</span><select id="sdbr-what-if-scenario-type">
      <option value="MTO_EXPEDITE" data-i18n="scenarioMtoExpedite">插单 / 加急</option>
      <option value="RESOURCE_DOWNTIME" data-i18n="scenarioResourceDowntime">停机冲击</option>
      <option value="SUPPLY_DELAY" data-i18n="scenarioSupplyDelay">供应延迟</option>
      <option value="MTA_RED_REPLENISHMENT_SHOCK" data-i18n="scenarioMtaRedShock">MTA 红区补货冲击</option>
    </select></label>
    <label><span data-i18n="resource">资源</span><select id="sdbr-what-if-resource"></select></label>
    <label><span data-i18n="date">日期</span><select id="sdbr-what-if-date"></select></label>
    <label><span data-i18n="additionalLoadMinutes">新增/挤压负荷分钟</span><input id="sdbr-what-if-load-minutes" type="number" min="0" value="60"></label>
  </div>
  <div class="what-if-actions">
    <button id="run-sdbr-what-if" class="button secondary" type="button" data-i18n="runSdbrWhatIf">评估冲击</button>
    <p class="inline-note" data-i18n="sdbrWhatIfBoundary">只评估执行层冲击，不修改冻结排程。</p>
  </div>
  <div id="sdbr-what-if-result" class="what-if-result"></div>
</section>
```

- [ ] **Step 4: Add i18n keys**

In `sdbr/web/planner-workbench.js`, add Chinese keys:

```javascript
sdbrWhatIfKicker: "S-DBR 执行级 What-if",
sdbrWhatIfTitle: "冲击会不会打爆约束",
scenarioType: "场景类型",
scenarioMtoExpedite: "插单 / 加急",
scenarioResourceDowntime: "停机冲击",
scenarioSupplyDelay: "供应延迟",
scenarioMtaRedShock: "MTA 红区补货冲击",
additionalLoadMinutes: "新增/挤压负荷分钟",
runSdbrWhatIf: "评估冲击",
sdbrWhatIfBoundary: "只评估执行层冲击，不修改冻结排程。",
whatIfBeforeAfter: "负荷变化",
whatIfRecommendation: "建议动作",
whatIfSimioHint: "是否建议 Simio 复核",
```

Add English keys:

```javascript
sdbrWhatIfKicker: "S-DBR execution what-if",
sdbrWhatIfTitle: "Will the shock break the constraint?",
scenarioType: "Scenario type",
scenarioMtoExpedite: "Order insertion / expedite",
scenarioResourceDowntime: "Downtime shock",
scenarioSupplyDelay: "Supply delay",
scenarioMtaRedShock: "MTA red replenishment shock",
additionalLoadMinutes: "Added / compressed load minutes",
runSdbrWhatIf: "Evaluate shock",
sdbrWhatIfBoundary: "Execution-layer impact only; the frozen schedule is not changed.",
whatIfBeforeAfter: "Load change",
whatIfRecommendation: "Recommended action",
whatIfSimioHint: "Simio review suggested",
```

- [ ] **Step 5: Add JS workspace loader**

In `sdbr/web/planner-workbench.js`, add global state near other schedule globals:

```javascript
let sdbrWhatIfWorkspace = null;
let sdbrWhatIfResult = null;
```

Add:

```javascript
async function loadSdbrWhatIfWorkspace(runId) {
  const panel = document.getElementById("sdbr-what-if-panel");
  if (!panel || !runId) return;
  try {
    const response = await fetch(`/planner/workbench/schedule-results/runs/${encodeURIComponent(runId)}/what-if/workspace`, {
      headers: { Accept: "application/json" }
    });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const payload = await response.json();
    sdbrWhatIfWorkspace = payload.Data;
    renderSdbrWhatIfWorkspace();
  } catch (error) {
    sdbrWhatIfWorkspace = null;
    panel.hidden = true;
  }
}

function renderSdbrWhatIfWorkspace() {
  const panel = document.getElementById("sdbr-what-if-panel");
  if (!panel || !sdbrWhatIfWorkspace) return;
  panel.hidden = false;
  const resourceSelect = document.getElementById("sdbr-what-if-resource");
  const dateSelect = document.getElementById("sdbr-what-if-date");
  const buckets = sdbrWhatIfWorkspace.CcrBuckets || [];
  replaceSelectOptions(resourceSelect, [...new Map(buckets.map((item) => [
    item.ResourceID,
    { ResourceID: item.ResourceID, Label: `${item.ResourceName || item.ResourceID} · ${item.ResourceID}` }
  ])).values()], { valueKey: "ResourceID", labelKey: "Label" });
  replaceSelectOptions(dateSelect, [...new Set(buckets.map((item) => item.Date))].filter(Boolean));
}
```

- [ ] **Step 6: Add JS evaluator**

Add:

```javascript
async function runSdbrWhatIf() {
  if (!selectedScheduleRunID) return;
  const button = document.getElementById("run-sdbr-what-if");
  button.disabled = true;
  try {
    const response = await fetch(`/planner/workbench/schedule-results/runs/${encodeURIComponent(selectedScheduleRunID)}/what-if/evaluate`, {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify({
        ScenarioType: document.getElementById("sdbr-what-if-scenario-type").value,
        ResourceID: document.getElementById("sdbr-what-if-resource").value,
        BucketDate: document.getElementById("sdbr-what-if-date").value,
        AdditionalLoadMinutes: Number(document.getElementById("sdbr-what-if-load-minutes").value || 0)
      })
    });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const payload = await response.json();
    sdbrWhatIfResult = payload.Data;
    renderSdbrWhatIfResult();
  } catch (error) {
    showNotification(error.message, "error");
  } finally {
    button.disabled = false;
  }
}

function renderSdbrWhatIfResult() {
  const container = document.getElementById("sdbr-what-if-result");
  if (!container) return;
  container.replaceChildren();
  const result = sdbrWhatIfResult;
  if (!result?.Impact) return;
  container.append(
    detailSection("whatIfBeforeAfter", [
      ["resource", `${result.Impact.ResourceName || "-"} · ${result.Impact.ResourceID || "-"}`],
      ["totalLoad", `${formatNumber(result.Impact.BeforeLoadMinutes)} -> ${formatNumber(result.Impact.AfterLoadMinutes)} min`],
      ["peakLoad", `${formatNumber(result.Impact.BeforeLoadPercent)}% -> ${formatNumber(result.Impact.AfterLoadPercent)}%`],
      ["status", `${displayValue(result.Impact.BeforeStatus)} -> ${displayValue(result.Impact.AfterStatus)}`]
    ]),
    detailSection("whatIfRecommendation", [
      ["recommendedAction", displayValue(result.Recommendation?.BusinessMeaning)],
      ["requiresReschedule", result.Recommendation?.RequiresFormalReplan ? translate("yes") : translate("no")]
    ]),
    detailSection("whatIfSimioHint", [
      ["status", result.SimioRecommendation?.Recommended ? translate("yes") : translate("no")],
      ["businessDiagnosis", displayValue(result.SimioRecommendation?.BusinessMeaning)]
    ])
  );
}
```

- [ ] **Step 7: Wire loader and events**

In the schedule-result load flow after `renderSdbrMarketControl(scheduleResultData);`, add:

```javascript
loadSdbrWhatIfWorkspace(selectedScheduleRunID);
```

In startup listeners, add:

```javascript
document.getElementById("run-sdbr-what-if").addEventListener("click", runSdbrWhatIf);
```

- [ ] **Step 8: Add CSS**

In `sdbr/web/planner-workbench.css`, add:

```css
.sdbr-what-if-panel {
  margin-top: 16px;
}

.what-if-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(180px, 1fr));
  gap: 12px;
}

.what-if-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 12px;
}

.what-if-result {
  display: grid;
  grid-template-columns: repeat(3, minmax(220px, 1fr));
  gap: 12px;
  margin-top: 12px;
}

@media (max-width: 900px) {
  .what-if-grid,
  .what-if-result {
    grid-template-columns: 1fr;
  }
}
```

- [ ] **Step 9: Run UI static test**

Run: `pytest tests/test_api.py::test_schedule_results_page_exposes_sdbr_native_what_if_panel -q --basetemp .tmp/pytest-sdbr-what-if-ui -p no:cacheprovider`

Expected: PASS.

---

### Task 5: Simio Recommendation Tooltip on Simulation Tab

**Files:**
- Modify: `sdbr/web/planner-workbench.html`
- Modify: `sdbr/web/planner-workbench.js`
- Modify: `sdbr/web/planner-workbench.css`
- Test: `tests/test_api.py`

**Interfaces:**
- Consumes: No backend data required for first pass.
- Produces: Hover/focus tooltip in simulation results tab explaining when Simio is the better tool.

- [ ] **Step 1: Write failing UI test**

Add:

```python
def test_simulation_results_panel_exposes_simio_usage_recommendation_tooltip():
    html = Path("sdbr/web/planner-workbench.html").read_text(encoding="utf-8")
    script = Path("sdbr/web/planner-workbench.js").read_text(encoding="utf-8")
    css = Path("sdbr/web/planner-workbench.css").read_text(encoding="utf-8")

    assert 'id="simio-recommendation-help"' in html
    assert "simioRecommendationTitle" in script
    assert "CCR 不是单一资源" in script
    assert ".simio-recommendation-tooltip" in css
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_api.py::test_simulation_results_panel_exposes_simio_usage_recommendation_tooltip -q`

Expected: FAIL because tooltip is not present.

- [ ] **Step 3: Add HTML tooltip trigger**

In `sdbr/web/planner-workbench.html`, inside `schedule-panel-simulation` before the runner toolbar, add:

```html
<div class="simio-recommendation-help">
  <button id="simio-recommendation-help" class="link-button" type="button" aria-describedby="simio-recommendation-tooltip" data-i18n="whenUseSimio">什么时候建议用 Simio？</button>
  <div id="simio-recommendation-tooltip" class="simio-recommendation-tooltip" role="tooltip">
    <strong data-i18n="simioRecommendationTitle">建议使用 Simio 高保真验证的情形</strong>
    <ul>
      <li data-i18n="simioUseCaseCcrGroup">CCR 不是单一资源，而是一组设备/人员/夹具组合。</li>
      <li data-i18n="simioUseCaseDisruption">停机、返工、检测失败对结果影响很大。</li>
      <li data-i18n="simioUseCaseReentrant">同一个订单多次访问同一资源。</li>
      <li data-i18n="simioUseCaseBranching">Routing 分支多，路径选择复杂。</li>
      <li data-i18n="simioUseCaseQueueDrivers">搬运、等待、批处理、换型占比很高。</li>
      <li data-i18n="simioUseCaseQueueStory">需要展示为什么排队爆了的动态过程。</li>
      <li data-i18n="simioUseCaseStableModel">已经有稳定 Simio 模型和数据维护机制。</li>
    </ul>
  </div>
</div>
```

- [ ] **Step 4: Add i18n keys**

Add Chinese keys:

```javascript
whenUseSimio: "什么时候建议用 Simio？",
simioRecommendationTitle: "建议使用 Simio 高保真验证的情形",
simioUseCaseCcrGroup: "CCR 不是单一资源，而是一组设备/人员/夹具组合。",
simioUseCaseDisruption: "停机、返工、检测失败对结果影响很大。",
simioUseCaseReentrant: "同一个订单多次访问同一资源。",
simioUseCaseBranching: "Routing 分支多，路径选择复杂。",
simioUseCaseQueueDrivers: "搬运、等待、批处理、换型占比很高。",
simioUseCaseQueueStory: "需要展示为什么排队爆了的动态过程。",
simioUseCaseStableModel: "已经有稳定 Simio 模型和数据维护机制。",
```

Add English keys:

```javascript
whenUseSimio: "When should Simio be used?",
simioRecommendationTitle: "When high-fidelity Simio validation is recommended",
simioUseCaseCcrGroup: "The CCR is a group of machines, people, fixtures, or handling capacity.",
simioUseCaseDisruption: "Downtime, rework, or inspection failure materially changes the result.",
simioUseCaseReentrant: "The same order visits the same resource more than once.",
simioUseCaseBranching: "Routing has many branches and path choices.",
simioUseCaseQueueDrivers: "Handling, waiting, batching, or changeover dominates the flow time.",
simioUseCaseQueueStory: "The team needs to see why queues exploded over time.",
simioUseCaseStableModel: "A stable Simio model and data-maintenance process already exists.",
```

- [ ] **Step 5: Add CSS tooltip behavior**

Add:

```css
.simio-recommendation-help {
  position: relative;
  margin-bottom: 12px;
}

.simio-recommendation-tooltip {
  display: none;
  position: absolute;
  z-index: 30;
  max-width: 520px;
  padding: 12px 14px;
  border: 1px solid #c7d7ea;
  border-radius: 8px;
  background: #fff;
  box-shadow: 0 12px 30px rgba(16, 32, 56, 0.14);
}

.simio-recommendation-help:hover .simio-recommendation-tooltip,
.simio-recommendation-help:focus-within .simio-recommendation-tooltip {
  display: block;
}
```

- [ ] **Step 6: Run UI tooltip test**

Run: `pytest tests/test_api.py::test_simulation_results_panel_exposes_simio_usage_recommendation_tooltip -q --basetemp .tmp/pytest-simio-hint-ui -p no:cacheprovider`

Expected: PASS.

---

### Task 6: Read Model Polish and Business Language

**Files:**
- Modify: `sdbr/web/planner-workbench.js`
- Test: `tests/test_api.py`

**Interfaces:**
- Consumes:
  - What-if result `Recommendation.Decision` values.
- Produces:
  - Chinese business labels for what-if decisions.

- [ ] **Step 1: Write failing static assertion**

Add to UI test:

```python
assert 'whatIfDecision_AbsorbWithBufferAndProtectiveCapacity: "用缓冲和保护产能吸收"' in script
assert 'whatIfDecision_ProtectCcrAndReviewReplan: "保护约束并复核是否重排"' in script
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_api.py::test_schedule_results_page_exposes_sdbr_native_what_if_panel -q`

Expected: FAIL because decision translations are missing.

- [ ] **Step 3: Add decision labels**

Add Chinese keys:

```javascript
whatIfDecision_AbsorbWithExistingPlan: "按现有计划吸收",
whatIfDecision_AbsorbWithBufferAndProtectiveCapacity: "用缓冲和保护产能吸收",
whatIfDecision_ReviewBeforeRelease: "释放前人工复核",
whatIfDecision_ProtectCcrAndReviewReplan: "保护约束并复核是否重排",
whatIfDecision_ReviewRequired: "需要人工评审",
```

Add English keys:

```javascript
whatIfDecision_AbsorbWithExistingPlan: "Absorb with current plan",
whatIfDecision_AbsorbWithBufferAndProtectiveCapacity: "Absorb with buffer and protective capacity",
whatIfDecision_ReviewBeforeRelease: "Review before release",
whatIfDecision_ProtectCcrAndReviewReplan: "Protect CCR and review replan",
whatIfDecision_ReviewRequired: "Manual review required",
```

- [ ] **Step 4: Add helper**

Add:

```javascript
function whatIfDecisionLabel(value) {
  const key = `whatIfDecision_${value || "ReviewRequired"}`;
  const translated = translate(key);
  return translated === key ? displayValue(value) : translated;
}
```

Use it in `renderSdbrWhatIfResult()`:

```javascript
["recommendedAction", `${whatIfDecisionLabel(result.Recommendation?.Decision)} · ${displayValue(result.Recommendation?.BusinessMeaning)}`],
```

- [ ] **Step 5: Run test**

Run: `pytest tests/test_api.py::test_schedule_results_page_exposes_sdbr_native_what_if_panel -q --basetemp .tmp/pytest-what-if-labels -p no:cacheprovider`

Expected: PASS.

---

### Task 7: End-to-End Verification and Documentation Evidence

**Files:**
- Modify: `docs/backend-specification.md`
- Modify: `docs/ui-specification.md`
- Test: no new test files

**Interfaces:**
- Consumes: All prior task outputs.
- Produces: Verified status notes, not `用户已确认`.

- [ ] **Step 1: Update backend acceptance evidence**

In `BE-SDBR-005 Native execution what-if 验收记录`, update implementation/test evidence:

```markdown
- 实现证据：`sdbr/sdbr_what_if.py` 以 CCR planned load、DDMRP runtime lines 和 scenario payload 生成执行层 what-if；`sdbr/api.py` 提供 workspace/evaluate read API；排程结果页面消费该 read model。
- 测试证据：`pytest tests/test_sdbr_what_if.py -q --basetemp .tmp/pytest-sdbr-what-if -p no:cacheprovider`；`pytest tests/test_api.py -q -k "what_if or simio_usage_recommendation" --basetemp .tmp/pytest-sdbr-what-if-api-ui -p no:cacheprovider`。
```

- [ ] **Step 2: Update UI acceptance evidence**

In UI P2 what-if section, update:

```markdown
- 自动化验证：`pytest tests/test_api.py -q -k "what_if or simio_usage_recommendation" --basetemp .tmp/pytest-sdbr-what-if-api-ui -p no:cacheprovider`; `node --check sdbr/web/planner-workbench.js`。
- 状态：已验证待用户确认。
```

- [ ] **Step 3: Run focused test suite**

Run:

```bash
pytest tests/test_sdbr_what_if.py -q --basetemp .tmp/pytest-sdbr-what-if -p no:cacheprovider
pytest tests/test_api.py -q -k "what_if or simio_usage_recommendation or schedule_results_page_exposes_p1_market_control_panel" --basetemp .tmp/pytest-sdbr-what-if-api-ui -p no:cacheprovider
python -m compileall -q sdbr
C:\Users\wyfch\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe --check sdbr\web\planner-workbench.js
```

Expected:
- `tests/test_sdbr_what_if.py`: PASS
- selected API/UI tests: PASS
- compileall: no output
- node check: no output

- [ ] **Step 4: Optional browser check**

If service is running at `http://127.0.0.1:8765/planner/workbench`, open:

```text
http://127.0.0.1:8765/planner/workbench#schedule-results
```

Manual expected:
- Schedule Results page still shows market-control panel.
- New S-DBR what-if panel appears below market-control and above publication governance.
- Simulation tab shows "什么时候建议用 Simio？" tooltip.
- Tooltip content lists CCR group, downtime/rework/inspection, repeated resource visits, routing branches, handling/waiting/batch/changeover, queue explosion story, and stable Simio model/data maintenance.

- [ ] **Step 5: Commit**

```bash
git add sdbr/sdbr_what_if.py sdbr/api.py sdbr/web/planner-workbench.html sdbr/web/planner-workbench.js sdbr/web/planner-workbench.css tests/test_sdbr_what_if.py tests/test_api.py docs/backend-specification.md docs/ui-specification.md
git commit -m "feat: add native S-DBR execution what-if"
```

---

## Self-Review

**Spec coverage**
- Native S-DBR what-if: Task 2 and Task 3.
- UI what-if panel: Task 4.
- Simio recommendation tooltip: Task 5.
- Business wording: Task 6.
- Specification and verification evidence: Task 1 and Task 7.

**Known boundaries deliberately excluded**
- No persisted what-if scenario history in P2 first pass.
- No CP-SAT re-solve from what-if.
- No Simio automatic execution from what-if.
- No DDAE protocol additions.
- No ProductionValidated or Business Golden Loop readiness claim.

**Type consistency**
- `build_sdbr_what_if_workspace(...)` and `evaluate_sdbr_what_if_scenario(...)` are introduced in Task 2 and consumed by Task 3.
- UI consumes `Mode`, `CcrBuckets`, `Impact`, `Recommendation`, and `SimioRecommendation` exactly as produced by Task 2.
