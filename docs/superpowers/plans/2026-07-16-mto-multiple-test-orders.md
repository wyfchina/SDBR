# MTO 多测试订单实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 通过现有 MTO 接收和评估 API 生成五类业务案例，并在 `runme.md` 中提供一条可重复执行、会自动校验结果的 PowerShell 命令。

**Architecture:** 不修改订单承诺算法或数据库种子函数。扩展现有浏览器测试数据脚本，使其先创建并验证五类业务评估，再创建接受、拒绝和过期决策等流程案例；Python API 测试独立验证同一组输入的业务结论，`runme.md` 说明运行与检查方法。

**Tech Stack:** Python 3、FastAPI TestClient、pytest、PowerShell 7、现有 SDBR Workbench API。

## Global Constraints

- 测试数据可以构造，但推荐、CCR 负荷、物料状态和安全承诺日期必须由正式评估逻辑计算。
- 80% 保护线是未取得 DDAE 批准保护线时的参考值；依赖该值的可行订单仍需计划员确认。
- 不修改 MTO 评估算法、DDAE 参数语义、生产接口或权威数据。
- 脚本不得直接写 SQLite，也不得写入预计算的评估结论。
- 后端验收引用 `BE-SDBR-010`；界面与运行说明引用 `UI-COMMIT-001`。
- 保留工作区已有 `runme.md` 改动，不覆盖用户或前序任务内容；忽略 `nofinish/`。

---

### Task 1: 用 API 测试锁定五类业务结论

**Files:**
- Modify: `tests/test_order_commitment_api.py`

**Interfaces:**
- Consumes: `seed_mto_order_commitment_fixture()` 返回的 `IntakePayloadTemplate`，以及现有 intake/reevaluate API。
- Produces: 一个场景矩阵测试，锁定五个订单 ID、容量状态、物料状态、保护线状态、推荐结论和关键负荷值。

- [ ] **Step 1: 写五类场景的行为测试**

在 `TestOrderCommitmentBrowserSequence` 前增加测试方法，先创建全部 intake，再对跳过物料案例重新评估：

```python
def test_business_scenarios_are_calculated_by_the_order_commitment_engine(self):
    client, _, fixture = _order_commitment_client()
    template = fixture["IntakePayloadTemplate"]
    cases = {
        "ON-TIME-REFERENCE": (1.0, 5.0, "OnTime", "Feasible", "PlannerConfirmationRequired"),
        "OVER-PROTECTION": (4.0, 20.0, "OnTime", "Feasible", "PlannerConfirmationRequired"),
        "LATER-SAFE-DATE": (6.0, 30.0, "LaterSafeDate", "Feasible", "PlannerConfirmationRequired"),
        "MATERIAL-SHORTAGE": (1.0, 120.0, "OnTime", "Shortage", "DoNotRecommendAccept"),
        "MATERIAL-SKIPPED": (1.0, 5.0, "OnTime", "SkippedPendingConfirmation", "PlannerConfirmationRequired"),
    }
```

对每个案例复制模板，设置 `OrderID = TST-MTO-SO-{suffix}`、`TraceID`、`Quantity`、物料 `RequiredQty` 和唯一 `RequirementLineID`。所有 intake 完成后，仅对 `MATERIAL-SKIPPED` 调用 reevaluate：

```python
{
    "RequestedBy": "planner-browser",
    "OperationalStateSnapshotID": None,
    "CheckMaterialAvailability": False,
    "MaterialCheckSkipReason": "Planner requested capacity-only MTO evaluation.",
}
```

从 `ShadowSchedule.SelectedAssessment.WindowAssessments`、`MaterialAssessment` 和 `Recommendation` 校验矩阵。`LATER-SAFE-DATE` 还必须断言安全承诺日期晚于请求承诺日期；`MATERIAL-SKIPPED` 必须断言 `CheckEnabled is False` 且 `SkipReason` 非空。前两个案例分别断言负荷为 `180 -> 240 (50%)` 和 `180 -> 420 (87.5%)`。

- [ ] **Step 2: 运行测试，确认现有算法是否满足设计**

Run:

```powershell
pytest tests/test_order_commitment_api.py -q -k "business_scenarios_are_calculated"
```

Expected: 若字段路径或案例参数与实际算法不一致则 FAIL；只允许修正测试读取路径或受控输入，不修改算法来迎合案例。

- [ ] **Step 3: 调整测试读取方式并再次运行**

使用现有 evaluation 字段名读取窗口：

```python
selected = evaluation["ShadowSchedule"]["SelectedAssessment"]
windows = selected["WindowAssessments"]
assert max(row["LoadBeforeMinutes"] for row in windows) == expected_before
```

再次运行同一命令，Expected: `1 passed`。

- [ ] **Step 4: 提交行为测试**

```powershell
git add tests/test_order_commitment_api.py
git commit -m "test: cover multiple MTO commitment scenarios"
```

---

### Task 2: 扩展 PowerShell 案例生成脚本

**Files:**
- Modify: `scripts/seed_mto_order_commitment_browser.ps1`
- Modify: `tests/test_order_commitment_api.py`

**Interfaces:**
- Consumes: Task 1 锁定的五类输入和预期结果；现有 reset/intake/reevaluate/decision API。
- Produces: 五个业务评估、独立流程案例，以及 `.tmp/mto-order-commitment-browser-fixture.json` 证据摘要。

- [ ] **Step 1: 增加脚本静态断言测试并验证失败**

```python
def test_browser_seed_script_declares_all_business_scenarios():
    script = Path("scripts/seed_mto_order_commitment_browser.ps1").read_text(encoding="utf-8")
    for scenario in (
        "ON-TIME-REFERENCE", "OVER-PROTECTION", "LATER-SAFE-DATE",
        "MATERIAL-SHORTAGE", "MATERIAL-SKIPPED",
    ):
        assert scenario in script
    assert "ExpectedRecommendation" in script
    assert "ExpectedCapacityStatus" in script
    assert "ExpectedMaterialStatus" in script
```

Run: `pytest tests/test_order_commitment_api.py -q -k "browser_seed_script_declares"`

Expected: FAIL，因为脚本尚未声明五个业务场景。

- [ ] **Step 2: 将业务场景矩阵加入脚本**

```powershell
$businessCases = @(
  @{ Suffix = "ON-TIME-REFERENCE"; Quantity = 1; RequiredQty = 5; ExpectedCapacityStatus = "OnTime"; ExpectedMaterialStatus = "Feasible"; ExpectedThresholdState = "ReferenceFallback"; ExpectedRecommendation = "PlannerConfirmationRequired" },
  @{ Suffix = "OVER-PROTECTION"; Quantity = 4; RequiredQty = 20; ExpectedCapacityStatus = "OnTime"; ExpectedMaterialStatus = "Feasible"; ExpectedThresholdState = "ReferenceFallback"; ExpectedRecommendation = "PlannerConfirmationRequired" },
  @{ Suffix = "LATER-SAFE-DATE"; Quantity = 6; RequiredQty = 30; ExpectedCapacityStatus = "LaterSafeDate"; ExpectedMaterialStatus = "Feasible"; ExpectedThresholdState = "ReferenceFallback"; ExpectedRecommendation = "PlannerConfirmationRequired" },
  @{ Suffix = "MATERIAL-SHORTAGE"; Quantity = 1; RequiredQty = 120; ExpectedCapacityStatus = "OnTime"; ExpectedMaterialStatus = "Shortage"; ExpectedThresholdState = "ReferenceFallback"; ExpectedRecommendation = "DoNotRecommendAccept" },
  @{ Suffix = "MATERIAL-SKIPPED"; Quantity = 1; RequiredQty = 5; ExpectedCapacityStatus = "OnTime"; ExpectedMaterialStatus = "SkippedPendingConfirmation"; ExpectedThresholdState = "ReferenceFallback"; ExpectedRecommendation = "PlannerConfirmationRequired"; SkipMaterial = $true }
)
```

扩展 `New-MtoEvaluation`，接收数量和物料需求。先完成全部 intake，再对 `SkipMaterial` 案例执行 reevaluate。

- [ ] **Step 3: 增加脚本结果提取和失败即停止机制**

```powershell
function Assert-Equal {
  param([string]$Label, [object]$Actual, [object]$Expected)
  if ($Actual -ne $Expected) {
    throw "$Label expected '$Expected' but got '$Actual'."
  }
}
```

对每个案例断言容量、物料、保护线和推荐结果；对前两个案例额外断言负荷前后值和百分比；对较晚日期案例比较两个 `PromiseAt`；对跳过物料案例断言 `CheckEnabled = false` 和非空 `SkipReason`。

- [ ] **Step 4: 保留但重新命名流程案例**

流程订单使用独立前缀：

```text
TST-MTO-SO-FLOW-ACCEPT
TST-MTO-SO-FLOW-REJECT
TST-MTO-SO-FLOW-STALE
```

接受和拒绝继续返回成功；过期指纹继续返回 HTTP 409。所有流程动作必须在五个业务案例断言完成后执行。

- [ ] **Step 5: 输出结构化证据摘要**

```powershell
$result = [ordered]@{
  BaselinePlanningRunID = $reset.Payload.Data.BaselinePlanningRunID
  BusinessScenarios = $businessEvidence
  LifecycleScenarios = $lifecycleEvidence
  PlanningRunID = $accepted.Payload.Data.Reservation.PlanningRunID
}
```

保留现有目录创建与 `ConvertTo-Json -Depth 30` 输出行为。

- [ ] **Step 6: 运行静态测试和脚本语法检查**

```powershell
pytest tests/test_order_commitment_api.py -q -k "browser_seed_script_declares"
[scriptblock]::Create((Get-Content scripts/seed_mto_order_commitment_browser.ps1 -Raw)) | Out-Null
```

Expected: pytest PASS；PowerShell 不抛出解析异常。

- [ ] **Step 7: 提交脚本和脚本测试**

```powershell
git add scripts/seed_mto_order_commitment_browser.ps1 tests/test_order_commitment_api.py
git commit -m "test: seed distinct MTO business examples"
```

---

### Task 3: 在 runme.md 中加入执行和检查说明

**Files:**
- Modify: `runme.md`
- Modify: `tests/test_order_commitment_api.py`

**Interfaces:**
- Consumes: Task 2 的脚本路径、默认服务 URL、输出路径和五类案例结果。
- Produces: 用户可直接执行的 MTO 测试数据生成说明。

- [ ] **Step 1: 增加运行说明文本检查**

```python
def test_runbook_documents_multiple_mto_business_examples():
    runbook = Path("runme.md").read_text(encoding="utf-8")
    assert "seed_mto_order_commitment_browser.ps1" in runbook
    for scenario in (
        "TST-MTO-SO-ON-TIME-REFERENCE", "TST-MTO-SO-OVER-PROTECTION",
        "TST-MTO-SO-LATER-SAFE-DATE", "TST-MTO-SO-MATERIAL-SHORTAGE",
        "TST-MTO-SO-MATERIAL-SKIPPED",
    ):
        assert scenario in runbook
```

Run: `pytest tests/test_order_commitment_api.py -q -k "runbook_documents_multiple_mto"`

Expected: FAIL，因为当前运行说明没有五个案例 ID。

- [ ] **Step 2: 在 runme.md 增加 MTO 多案例章节**

```powershell
Set-Location D:\Documents\SDBR
pwsh -File .\scripts\seed_mto_order_commitment_browser.ps1 `
  -BaseUrl http://127.0.0.1:8765 `
  -OutputPath .tmp\mto-order-commitment-browser-fixture.json
```

说明页面 `http://127.0.0.1:8765/planner/workbench#order-commitment`，列出五个案例的订单 ID、输入差异和预期业务结论，并提示命令会清除现有 MTO 测试评估及预留状态。

- [ ] **Step 3: 运行说明测试并提交**

Run: `pytest tests/test_order_commitment_api.py -q -k "runbook_documents_multiple_mto"`

Expected: `1 passed`。

```powershell
git add runme.md tests/test_order_commitment_api.py
git commit -m "docs: add MTO scenario seed instructions"
```

---

### Task 4: 完整回归和真实 API 验证

**Files:**
- Verify: `scripts/seed_mto_order_commitment_browser.ps1`
- Verify: `.tmp/mto-order-commitment-browser-fixture.json`
- Verify: `runme.md`

**Interfaces:**
- Consumes: 正在运行的本地 Workbench 服务。
- Produces: 可供页面检查的五个 MTO 业务案例和流程案例。

- [ ] **Step 1: 运行 MTO 定向测试**

```powershell
pytest tests/test_order_commitment_api.py tests/test_order_commitment_evaluation.py tests/test_order_commitment_view.py -q --basetemp .tmp/pytest-mto-scenarios -p no:cacheprovider
```

Expected: 全部 PASS。

- [ ] **Step 2: 运行编译和相关 API 回归**

```powershell
python -m compileall -q sdbr
pytest tests/test_api.py -q -k "order_commitment or planning_run_center" --basetemp .tmp/pytest-mto-api -p no:cacheprovider
```

Expected: 编译退出码为 0；相关 API 测试全部 PASS。

- [ ] **Step 3: 对本地服务运行真实脚本**

```powershell
pwsh -File .\scripts\seed_mto_order_commitment_browser.ps1 `
  -BaseUrl http://127.0.0.1:8765 `
  -OutputPath .tmp\mto-order-commitment-browser-fixture.json
```

Expected: 退出码为 0；JSON 中 `BusinessScenarios` 有 5 条，包含对应推荐、负荷和物料状态；`LifecycleScenarios` 记录接受、拒绝和过期结果。

- [ ] **Step 4: 检查页面 read model**

```powershell
Invoke-RestMethod http://127.0.0.1:8765/planner/workbench/order-commitments/workbench `
  -Headers @{ "X-Actor-ID" = "planner-runbook"; "X-Actor-Role" = "Planner" }
```

Expected: Rows 中包含五个 `TST-MTO-SO-*` 业务案例；页面 `#order-commitment` 可搜索这些订单号。

- [ ] **Step 5: 检查最终差异**

```powershell
git diff --check
git status --short
```

Expected: 无空白错误；`nofinish/` 未被暂存；只存在本计划相关改动或用户此前已有的明确改动。
