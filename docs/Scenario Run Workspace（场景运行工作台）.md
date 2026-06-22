下面是 **Scenario Run Workspace（场景运行工作台）** 的核心用例设计。它的定位不是“看报表”，而是让 DDS&OP 计划员在会议中快速回答：

```text
如果我们调整补货规则、提前建库或增加产能，未来缓冲、库存、产能和供应需求会怎样变化？
```

**核心用例 1：Baseline vs Scenario 对比**

工作过程：

1. 用户进入 Scenario Run Workspace。
2. 系统自动加载当前 Baseline Plan。
3. 用户选择计划范围，例如未来 12 周、26 周或 52 周。
4. 用户创建一个 Scenario。
5. 用户修改场景参数。
6. 点击“运行场景”。
7. 系统同时展示 Baseline 和 Scenario。
8. 用户查看差异，判断是否采纳。

输入：

```text
计划范围：12 / 26 / 52 周
SKU 或产品族范围
当前库存
当前 Net Flow
ADU / DLT / MOQ / Order Cycle
未来需求
当前资源能力
当前供应商来源
```

输出：

```text
Baseline 计划结果
Scenario 计划结果
差异指标 Delta
缓冲水位变化
补货订单变化
RCCP 负载变化
供应商需求变化
平均库存变化
缺货风险变化
计算 trace
```

**核心用例 2：Pre-build Campaign 提前建库**

工作过程：

1. 系统显示未来某几周需求峰值或产能超载。
2. 用户选择一个 SKU 或产品族。
3. 用户设置提前建库数量和 build week。
4. 系统把未来峰值压力前移到淡季。
5. 用户比较建库前后库存、产能和供应需求。

输入：

```text
目标 SKU / 产品族
Pre-build 数量
Build week
目标需求峰值周
当前库存与缓冲参数
```

输出：

```text
提前释放的补货 / 工单
峰值周负载下降量
建库周负载增加量
平均库存增加量
营运资金影响
缺货风险变化
```

目的：

```text
削峰填谷，用库存换取未来交付稳定性。
```

**核心用例 3：产能调整场景**

工作过程：

1. 系统在 RCCP 中标识某资源未来超载。
2. 用户选择资源，例如 Line 1、High Speed、瓶颈工序。
3. 用户设置某几周产能乘数，例如 1.2、1.5。
4. 系统重新计算资源负载率。
5. 用户查看平均负载、峰值负载、超载周是否下降。

输入：

```text
资源名称
调整起止周
产能调整倍数
当前 routing
预计补货订单
当前资源能力
```

输出：

```text
调整后可用产能
调整后负载率
平均负载变化
峰值负载变化
超载周数量变化
剩余能力缺口
```

目的：

```text
判断加班、增班或外协是否足以消除瓶颈。
```

**核心用例 4：MOQ / 订货周期调整**

工作过程：

1. 用户发现某 SKU 订单过于频繁，或库存水位波动过大。
2. 用户修改 MOQ、Order Multiple、Order Cycle。
3. 系统重新生成补货订单。
4. 用户查看订单数量、订单频率、平均库存和缺货风险。

输入：

```text
SKU
MOQ
Order Multiple
Order Cycle
固定订货日规则
ADU / DLT / 缓冲区参数
```

输出：

```text
补货订单数量变化
订单生成周变化
平均订单量变化
平均库存变化
Net Flow 稳定性变化
缺货风险变化
```

目的：

```text
在订单效率、库存资金和服务水平之间找平衡。
```

**核心用例 5：异常 SKU 驱动场景分析**

工作过程：

1. 系统展示异常 SKU 列表。
2. 用户按 shortage days、service level、net flow、spike、lead time 等筛选。
3. 用户点击一个异常 SKU。
4. 系统展示该 SKU 的历史表现、未来缓冲趋势、补货订单和资源影响。
5. 用户直接基于该 SKU 创建 Scenario。

输入：

```text
SKU 异常指标
历史消耗
未来需求
缓冲水位
库存与开放供应
资源 routing
供应商来源
```

输出：

```text
异常原因提示
SKU 缓冲趋势
建议可测试动作
场景运行结果
是否改善异常
```

目的：

```text
从问题出发，而不是从空白参数表出发。
```

**核心用例 6：Constrained vs Unconstrained 对比**

工作过程：

1. 系统先计算不受约束计划。
2. 系统再根据资源能力、供应能力或资金限制计算受约束计划。
3. 用户比较两者差异。
4. 系统显示哪些 SKU、产品族或资源导致业务计划无法达成。

输入：

```text
需求计划
SKU 缓冲参数
资源能力
供应商能力
库存资金限制
服务目标
```

输出：

```text
Unconstrained supply
Constrained supply
Unconstrained inventory
Constrained inventory
缺口数量
缺口金额
受影响 SKU / 产品族
瓶颈资源
建议动作
```

目的：

```text
让管理层看到约束对业务计划的真实影响。
```

**推荐页面工作流**

```text
1. 选择范围
   产品族 / SKU / 供应商 / 资源 / 计划周期

2. 查看 Baseline
   当前缓冲、补货、RCCP、供应需求

3. 识别异常
   缺货、超载、库存过高、订单频繁、供应风险

4. 配置 Scenario
   Pre-build、产能调整、MOQ、订货周期、需求事件

5. 运行 Scenario
   调用 DemandDrivenPlanningEngine

6. 对比结果
   Baseline vs Scenario vs Delta

7. 查看 Trace
   输入参数如何转成补货订单、负载和供应需求

8. 保存 / 导出 / 提交
   保存场景、导出结果、提交管理评审
```

**标准输入结构**

```text
ScenarioInput
- scenarioName
- horizonWeeks
- selectedSkus
- selectedProductFamilies
- demandOverrides
- prebuildCampaigns
- capacityAdjustments
- moqOverrides
- orderCycleOverrides
- supplierConstraints
- financialAssumptions
```

**标准输出结构**

```text
ScenarioRunResult
- baselinePlan
- scenarioPlan
- deltaSummary
- bufferTrendComparison
- replenishmentOrderComparison
- rccpComparison
- projectedSupplyComparison
- financialImpact
- risks
- recommendations
- calculationTrace
```

**最重要的输出指标**

```text
服务风险：缺货天数、红区穿透、Net Flow 稳定性
库存影响：平均库存、库存金额、营运资金变化
产能影响：平均负载、峰值负载、超载周数量
供应影响：供应商周度需求、供应缺口、物料族风险
决策影响：推荐动作、收益、代价、是否建议采纳
```

一句话总结：

**Scenario Run Workspace 的本质是 DDS&OP 的会议沙盘：用 SKU 级推演做真实计算，用产品族/资源/供应商汇总做管理决策。**