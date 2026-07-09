# SDBR / DDOM 计划排程系统 UI 规格说明书

| 属性 | 内容 |
| --- | --- |
| 文档版本 | 5.29 |
| 日期 | 2026-07-09 |
| 状态 | UI 验收单元基线已完成；进入产品级 UI 审计与后续能力联动阶段 |
| 适用范围 | 计划员工作台及其直接支撑页面 |
| 后端基线 | `docs/backend-readiness-2026-06-19.md` |
| 产品参考 | 用户提供的 Intuiflow 产品视频及本项目业务需求 |

## 1. 文档效力与执行规则

本文件是后续 UI 设计、开发、测试和验收的基准规格。实现不得仅以临时对话或现有原型页面为依据。

### 1.1 规格编号

每个可交付项使用固定编号，例如 `UI-SHELL-001`。代码、测试、开发汇报和验收记录都应引用该编号。

### 1.2 状态定义

每项规格只能处于以下状态之一：

- `未开始`
- `开发中`
- `已实现待验证`
- `已验证待用户确认`
- `用户已确认`

### 1.3 逐项确认规则

1. 一次只推进当前已声明的规格项或同一验收单元中的紧密关联项。
2. 完成后必须说明对应规格编号、实现内容、测试结果和可查看地址。
3. 必须等待用户确认，方可将该项标记为 `用户已确认`。
4. 未确认项不得被后续改动默认为已接受。
5. 规格变更必须先修改本文件，并记录变更原因，再修改代码。

## 2. 产品目标

计划员工作台用于完成以下核心业务闭环：

```text
确认数据就绪
→ 创建 Planning Run
→ 选择求解与验证方式
→ 执行排程
→ 检查约束、负荷和交期
→ 处理异常或比较方案
→ 确认计划
→ 进入释放管理
```

UI 必须帮助计划员快速回答五个问题：

1. 本次排程使用的数据是否完整、新鲜、可追溯？
2. 哪些排程任务正在等待、执行、失败或需要人工处理？
3. 约束资源是否可执行，哪些订单威胁保护交期？
4. 哪些工单现在应该释放，哪些必须继续拦截？
5. 计划与实际发生偏差时，是监控、人工干预还是重新排程？

产品方向明确为 DDOM 运营执行工作台。UI 负责支持 DDOM 日常运行、排程、释放、缓冲执行、MES 派工建议、偏差反馈和可选 Simio 验证；DDS&OP / DDAE 只作为上游配置来源和下游反馈对象，不在本系统实现 DDS&OP 会议、情景评估、模型治理或重构审批界面。DDMRP 相关能力只作为 DDOM 运行链路消费已生效参数，不提供 DDMRP 参数配置、Buffer Profile 治理或调整因子审批页面。

来自 DDAE 的时间缓冲、控制点、DDMRP 参数、资源角色和主设置在 UI 中只能按契约显示来源、版本、冻结状态和执行反馈；不得在 SDBR 页面重新计算、审批或扩展这些主参数。若界面发现配置不足，应显示“需要契约变更/配置补充”的业务提示，而不是新增隐式字段或本地参数计算器。

## 3. 非目标与阶段边界

第一版 UI 不承担以下完整能力：

- 一线操作工完整 MES 终端
- SCADA 设备控制
- 完整 ERP 主数据维护替代品
- DDS&OP 战术协调、情景评估、模型治理或重构审批
- DDMRP 参数配置、Buffer Profile 治理或调整因子审批
- DDAE 已批准主设置的重新计算、审批或本地参数治理
- 深度 BI 自助报表设计器
- 完整流程挖掘建模器

第一版必须保留 OR-Tools 与 Simio 的正确产品路径和能力状态。能力未接通时应明确显示 `未配置` 或 `暂不可用`；已接通的能力必须标明作用边界，不能把 Simio 可选验证误导为排程求解器。

## 4. Intuiflow 对标原则

### 4.1 应吸收的产品特征

- 以计划员任务和异常为中心，而不是以数据库对象为中心。
- 使用缓冲颜色、约束负荷和优先级形成清晰的视觉决策信号。
- 支持从汇总状态下钻到订单、资源和异常原因。
- 计划结果、执行状态和业务动作处于同一工作上下文。
- 常用操作短路径完成，参数配置不占据日常主界面。

### 4.2 不应照搬的内容

- 不复制品牌、配色、图标或专有布局。
- 不把所有功能堆入一个无限向下滚动页面。
- 不在计划员首页展示原始 JSON、内部 API 载荷或调试输出。
- 不使用颜色作为唯一状态表达；必须同时提供文字或图标。
- 不把配置型主数据和每日排程操作混在同一表单。

### 4.3 截图对标结论

本节依据 `interface/` 中 16 张 Intuiflow 视频截图及 `interface/interface.md` 形成。

确认可借鉴的界面模式：

- 常驻左侧导航将 `Scheduling & Execution`、`Editors`、`Reports`、`Data` 与 `Settings` 分开。
- 首页同时呈现计划优先级、执行预警、准时性和 Buffer Board 摘要，但不承担明细编辑。
- Scheduler 是面向工单的高密度网格，支持保存视图、分组、批量动作和最近排程时间。
- System Load Graph 用于资源横向排名；Resource Load Graph 用于单资源逐日能力检查，两者不能合并成一张含义模糊的图。
- Buffer Board 使用 `Yet to be Received / Received` 两行和 `Early / Green / Yellow / Red / Late` 五列。
- 工单事务弹窗根据数量、百分比或工时记录进度；迟到事务必须选择原因码。
- 工单详情将工艺与工序、历史、路线、生产信息、销售信息和备注放在同一上下文中。
- 甘特图将 Processing 与 Green/Yellow/Red Time Buffer 作为不同条带显示，并支持悬浮详情。
- 资源日历采用 Day、Week、Shift Override、Exclusion/Modification 分层配置。
- 资源编辑器显式区分 Constraint、Buffered Resource 与普通 Resource。
- Process Mining 适合管理分析，不属于计划员每日创建排程的主路径。

本项目应采用这些业务表达模式，但重新设计视觉密度、交互一致性和移动适配，不复制原产品样式。

## 5. 用户角色与权限

| 角色 | 主要任务 | UI 权限 |
| --- | --- | --- |
| Viewer | 查看计划与指标 | 只读页面、筛选、下钻 |
| Planner | 创建排程、确认结果、处理释放 | 日常工作区全部业务操作 |
| Worker | 领取和执行后台任务 | 无人工业务页面，仅显示服务状态 |
| Admin | 主数据、接口、权限和恢复 | 后台管理及全部审计权限 |

第一版主要服务 `Planner`，同时提供 `Viewer` 只读行为和 `Admin` 后台入口。

## 6. 信息架构

### 6.1 一级导航

| 编号 | 中文 | 英文 | 用途 |
| --- | --- | --- | --- |
| NAV-01 | 计划总览 | Planning Overview | 今日异常、队列、约束和待办 |
| NAV-02 | 数据就绪 | Data Readiness | 主数据版本与运行快照健康度 |
| NAV-03 | 排程任务 | Planning Runs | 创建、入队、执行、恢复和审计 |
| NAV-04 | 排程结果 | Schedule Results | 甘特图、负荷、订单与诊断 |
| NAV-05 | 释放管理 | Release Management | 绳长、物料、WIP和缓冲门控 |
| NAV-06 | 异常中心 | Exceptions | 失败、死信、重排和稳定性 |
| NAV-07 | 日历配置 | Calendar Configuration | 基础日历、资源分配、临时覆盖和最终可用窗口预览 |
| NAV-08 | 管理后台 | Administration | 主数据、集成、求解器和权限 |

### 6.2 应用外壳

桌面端采用固定左侧导航、顶部上下文栏和主内容区。页面不得使用营销型首页。

顶部上下文栏持续显示：

- 当前工厂或计划范围
- 当前主数据版本
- 当前运行状态快照及新鲜度
- 当前语言
- 当前用户与角色
- 系统健康状态

## 7. 视觉与交互规范

### UI-SHELL-001 应用外壳

**状态：已验证待用户确认**

要求：

- 左侧导航支持展开与收起。
- 左侧导航项在桌面端 hover 或键盘 focus 时显示业务解释；解释复用页面标题区的双语说明文案。
- 当前页面、未读异常和死信数量清晰可见。
- 顶部上下文在页面切换时保持。
- 桌面宽度优先，最小支持 1280×720。
- 窄屏时左侧导航转为抽屉，关键表格允许横向滚动。
- 页面标题使用正常工作台尺度，不使用超大 Hero 文字。

验收：导航、上下文、语言切换、健康状态和导航业务解释均可操作；不存在重叠、裁切或布局跳动。

### UI-DS-001 设计语言

**状态：用户已确认**

- 主色使用克制的蓝色，业务正常状态使用青绿色。
- 缓冲状态使用红、黄、绿，同时显示文字标签。
- 橙色仅用于警告、重试、死信恢复等需要注意的动作。
- 灰色用于未配置、暂停或不可用能力。
- 卡片圆角不超过 8px，不使用卡片套卡片。
- 图标优先使用 Lucide 或项目统一图标库。
- 表格、筛选器和工具栏保持紧凑、可扫描。
- 禁止装饰性渐变、光晕球体和大面积单色背景。

## 8. 页面规格

### UI-OVERVIEW-001 计划总览

**状态：用户已确认**

页面区域：

- 待处理事项：数据过期、排程失败、死信、约束风险、释放阻塞。
- Planning Run 队列摘要：Queued、Running、Completed、DeadLetter。
- 约束资源未来四周负荷摘要。
- 红黄绿缓冲订单分布。
- 最近排程及最近人工操作。

主要动作：`创建排程`、`查看失败任务`、`进入释放管理`。

空状态：明确说明当前无任务，并提供创建排程入口；不得显示模拟业务数据冒充真实数据。

当前案例验收阶段，计划总览先承载 `测试案例验收` 摘要：

- 显示测试数据集、评估时间、通过/待执行/失败案例数。
- 每个案例显示案例名称、关联 Planning Run、排程状态、求解器状态、发布治理状态、释放可行数和阻塞原因代码。
- 支持从案例跳转到排程结果页查看具体计划。
- 未完成、死信或尚未执行的案例不得假装可打开排程结果，必须显示不可打开原因。
- 每个案例支持复位，全部案例支持一键复位，复位后回到可重新执行状态并清除人工确认/驳回影响。
- 明确这是测试系统案例验收视图，不得混入生产数据。

### UI-DATA-001 数据就绪中心

**状态：用户已确认**

页面显示：

- 最新主数据版本状态、来源、创建人和捕获时间。
- 资源、约束、工艺路线、订单、库存缓冲和物料需求数量摘要。
- 最新运行状态快照状态、新鲜度和来源。
- 库存、在途、WIP和资源状态的更新时间摘要。
- 数据问题按严重程度分组。

交互：

- `查看问题`打开结构化问题抽屉。
- `创建新版本`进入后台导入流程，不在日常页编辑原始 JSON。
- `生成运行快照`在测试/Mock 场景下基于最新运行状态快照生成一份当前时间的新快照，解决快照过期后无法继续验证释放和缓冲链路的问题；真实 ERP/MES 同步仍由外部接口能力跟踪。
- `选作本次排程输入`只允许选择有效版本和快照。

### UI-DDMRP-001 DDMRP 运行状态

**状态：已验证待用户确认**

页面位置：数据就绪中心。

页面显示：

- 解耦点数量、红/黄/绿/高于绿区数量。
- 需要补货的解耦点数量。
- DDMRP 输入缺失或无法计算的数量。
- 可展开的解耦点明细：物料、地点、在手量、净流位置、计划缓冲区、在手执行区、建议补货量和建议动作。

交互边界：

- 只读查看 DDMRP 运行结果，不提供 Buffer Profile、DLT、调整因子、解耦点设计或 DDMRP 参数配置入口。
- 技术字段可以在接口中保留，但业务界面应优先显示“需要补货、关注、正常、高于绿区”等计划员可理解表达。
- DDMRP 结果作为 DDOM 运行和释放解释依据，不在当前 UI 中直接变成 CP-SAT 硬约束配置。

### UI-DDMRP-002 DDMRP 物料计划工作台

**状态：已验证待用户确认**

页面位置：独立导航页 `物料计划 / Materials Planning`。

页面显示：

- 物料、地点、计划优先级、缓冲区、缓冲百分比、在手库存、在途供应、合格需求、净流位置、建议补货量和推荐动作。
- 红/黄/绿/高于绿区颜色和业务标签。
- 红区、黄区显示补货建议；绿区、高于绿区显示保持观察或暂不补货。
- 点击物料查看当前快照详情，包括缓冲上下限、需求/供应构成和趋势占位。

交互边界：

- 支持搜索物料/地点、按缓冲区筛选、按优先级/缓冲百分比/建议补货量排序。
- 第一版只读展示补货建议，不提供批量批准、ERP 订单生成或外部投递。
- 不提供 Buffer Profile、DLT、调整因子、解耦点设计或 DDMRP 参数配置入口。
- 所有补货与不补货判断以 `docs/ddom-ddmrp-runtime-principles.md` 为准，尤其是绿区和高于绿区不补货。

### UI-DDOM-001 DDOM 运营指标与偏差反馈

**状态：已验证待用户确认**

页面位置：独立导航页 `运营指标 / Operational Metrics`。

页面显示：

- 按 `可靠性 / 稳定性 / 速度/流速` 三类展示 DDOM 运营指标。
- 每类显示业务问题、颜色状态、综合得分和四个最小指标。
- 每个指标显示业务名称、定义、数值、红黄绿状态、数据覆盖说明和建议动作。
- 页面明确该指标体系用于 DDOM 日常运行反馈，不用于 DDS&OP 模型配置、财务成本归因或 MES 秒级控制。
- 偏差反馈区显示建议动作和数据覆盖缺口，便于后续 DDS&OP 复盘消费。
- 中文界面不得直接展示后端英文枚举、适用范围或不适用范围；应转换为计划业务语言。

交互边界：

- 支持选择已完成 Planning Run 和评估时间。
- 技术证据和原始来源可以在接口中保留，主界面只显示业务语言。
- 第一版不做历史趋势、管理层大屏、DDS&OP 出站接口或指标阈值配置。

### UI-RUN-001 Planning Run 列表

**状态：用户已确认**

列：Run ID、计划场景、状态、主数据版本、运行快照、求解器、请求人、开始时间、耗时、尝试次数。

筛选：状态、时间、请求人、求解器、仅看异常。

状态动作：

| 状态 | 允许动作 |
| --- | --- |
| Pending | 入队、直接执行、取消 |
| Queued | 查看等待原因 |
| Running | 查看 Worker、租约和求解进度 |
| Completed | 打开排程结果 |
| Failed | 查看诊断 |
| DeadLetter | 查看失败记录、人工恢复 |
| Cancelled | 查看审计 |

### UI-RUN-002 创建排程向导

**状态：用户已确认**

采用三步流程：

1. `选择输入`：主数据版本、运行状态快照、计划起点。
2. `设置策略`：时间缓冲、求解器、TimeLimit、重试策略。
3. `验证并提交`：显示输入摘要、风险和不可用能力。

时间缓冲设置：

- 页面提供时间缓冲计算器，输入 `运营提前期 OLT`、`上游波动程度`和`产能弹性`。
- 推荐值按 `时间缓冲 = OLT × (1 + 变异与弹性综合系数)` 计算，并限制在 `0.5 × OLT` 至 `2.5 × OLT` 的产品默认边界内。
- 经验分布遵循低波动/高弹性约 `0.5~1.0 × OLT`，中波动/中弹性约 `1.0~1.5 × OLT`，高波动/低弹性约 `1.5~2.5 × OLT`。
- `上游波动程度`和`产能弹性`必须提供悬浮解释，说明设备故障、来料准时率、返工/废品、保护性产能和追赶能力如何影响时间缓冲。
- 计划员可采用推荐值，也可手工覆盖最终 `TimeBufferMinutes`；提交给 CP-SAT 和释放策略冻结链路的仍是最终分钟值。

求解与验证路径：

- 求解器选择显示 `OR-Tools CP-SAT` 与 `Gurobi` 为同级产品路径。
- `OR-Tools CP-SAT` 是当前唯一可用并默认选中的求解器。
- `Gurobi` 保留历史产品路径，但显示 `已暂停 / Paused`，不可用于提交新计划。
- `启用 Simio 验证`为独立开关，不属于求解器选择。
- 未启用 Simio：求解器结果直接进入排程输出。
- 当前 Simio 状态为计划完成后的可选仿真验证能力；创建排程时不参与 CP-SAT 求解，排程完成后在仿真结果页发起验证。

### UI-SIM-001 仿真结果输出页

**状态：已验证待用户确认**

排程结果页必须提供独立的 `仿真结果 / Simulation Results` 页签，用于查看 Simio 对已完成计划的验证证据。

页面显示：

- 验证状态、Runner 模式、验证包、模型路径和结果模型路径。
- 可行性结论：可行、可行但有警告、不可行或结果不可用。
- 吞吐、队列、WIP、资源利用率和结果解析覆盖摘要。
- 资源利用率明细：资源、利用率、忙碌时间、饥饿时间和证据来源。
- 计划偏差明细：工单、实际开始、实际结束、队列等待、WIP 快照和事件状态。
- 问题清单：不可解析日志、未完成订单、模型/结果缺口等结构化原因。
- 面向计划员的主视图不得直接显示 `ParsedFromSDBROutputRows`、`ParsedFromPostRunLogs`、`PartialResultParsed` 等技术状态；必须转为“来自工单输出记录”“来自 Simio 运行日志”“已解析部分仿真结果”等业务语言。
- 输出治理、释放原因和仿真结果中的原因码、布尔值和英文说明必须优先显示业务含义；技术码只作为次要审计信息展示。
- 计划偏差/工单仿真明细不得一次性平铺所有记录；必须提供工单号搜索、事件状态筛选、队列等待筛选、`10 / 25 / 50` 每页选择、上一页/下一页和当前范围提示。
- 工单仿真明细必须支持按工单、实际开始、实际结束、队列等待、加工/停留时间、WIP 开始/结束和事件状态排序；加工/停留时间可由前端用实际结束减实际开始派生。
- 资源利用率必须按风险阈值突出显示：`>80% 且 <=90%` 黄色，`>90% 且 <100%` 红色，`>=100%` 黑色白字；`<=80%`、空值或不可解析值保持普通样式。

操作：

- 可选择 `auto / mock / local` Runner 模式并发起一次 Simio 验证。
- 可刷新当前 Run 的最新验证结果。

边界：

- Simio 验证是计划复核证据，不是排程求解器。
- 本阶段不启用 Simio Portal、Server Connector、Experiment 批量配置或发布硬门控。
- 是否要求 “Simio 必须通过才能发布” 留待后续策略确认。

### UI-CALENDAR-001 日历配置独立页面

**状态：已验证待用户确认**

日历配置必须从管理后台拆分为独立页面，因为它直接决定 CP-SAT 看到的资源能力窗口。

第一阶段页面关注“事项要素是否齐全”“核心配置是否可操作”和“最终可用窗口是否可解释”，不做复杂审批流。

页面区域：

- 基础日历模板：多班次、工作日、节假日、维护窗口、状态。
- 资源日历分配：资源与 Active 基础日历的绑定关系。
- 临时覆盖：临时班次、加班、维护/不可用。
- 冲突优先级：维护 > 节假日 > 临时覆盖 > 加班 > 基础班次。
- 最终可用窗口预览：按资源和日期范围展示 CP-SAT 实际消费的能力窗口。
- 事项要素检查：显示事项、CP-SAT 需要原因、缺失影响域。
- Planning Run 影响：说明 Active 日历与覆盖会在新建 Planning Run 时冻结。

日历预览阶段重点事项：

| 事项 | CP-SAT 需求原因 | 缺失影响域 |
| --- | --- | --- |
| 资源日历分配 | 确定每个资源使用哪个日历生成能力桶 | 资源可能回退到日能力总量，排程与现场班次不一致 |
| 基础班次开始/结束 | 决定资源在一天内哪些时间可加工 | 工序可能排到非工作时间，或产能被低估 |
| 工作日规则 | 判断日历是否在某天生效 | 周末或非工作日可能被错误排产 |
| 节假日 | 扣除整天不可用时间 | 计划可能排到停工日，或节假日加班规则不清 |
| 维护/停机窗口 | 切掉所有低优先级可用窗口 | 工序可能排到设备维护期间 |
| 加班窗口 | 增加额外能力桶 | 紧急订单可能被误判不可行或延后 |
| 临时班次覆盖 | 体现计划员短期排班调整 | 重排结果无法反映临时排班变化 |
| 冲突优先级 | 多规则重叠时唯一确定最终窗口 | 同一时间可能同时被解释为可用和不可用 |
| 时区 | 保证日期、班次、交期一致 | 跨天、跨班次和节假日判断偏移 |
| 跨班次加工规则 | 决定长工序是否可跨窗口 | 当前 CP-SAT 要求工序完整落入一个能力桶，规则缺失会影响可行性 |

后台依赖：

- `GET /planner/workbench/calendar/preview`
- 返回 `RequiredElements`、`ConflictPriority`、`Resources[].Elements`、`Resources[].FinalCapacityWindows`、`MissingDailyCapacityDates`。
- `POST /planner/workbench/admin/base-calendars`
- `POST /planner/workbench/admin/resource-calendar-assignments`
- `POST /planner/workbench/admin/calendar-overrides`

验收：

- 页面提供资源级日历的核心操作入口：工作周/基础日历、日模式/班次时段、资源日历分配、节假日、维护、加班、临时班次覆盖。
- 系统自动生成日历编号、分配编号和覆盖编号；资源与日历使用下拉选择；工作日使用周一到周日复选框。
- 管理后台不再提供日历编辑表单或日历摘要区；日历配置统一进入独立 `日历配置 / Calendar Configuration` 页面。
- 用户选择资源和日期范围后，能看到基础班次、节假日、维护、加班、临时覆盖和最终 CP-SAT 能力窗口。
- 缺少日能力日期、资源日历分配或时区问题必须可见，不得只显示空白。
- 页面不得暗示已支持审批流、节假日强制加班例外或跨班次连续加工。

验证记录：

- 2026-06-22：新增独立导航 `日历配置 / Calendar Configuration`，页面可调用 `GET /planner/workbench/calendar/preview` 展示事项要素、最终能力窗口、规则来源和缺失日能力日期；补充类似 Simio 的“工作周 + 日模式”轻量操作区，可创建基础日历、资源绑定和临时覆盖。
- 2026-06-22：修正日历页产品化细节：降低表单内容字号、加重标题层级、自动生成编号、资源/日历改为下拉选择、工作日改为复选框；管理后台取消日历编辑表单和日历摘要区。
- 2026-06-22：排程结果甘特区增加双视图：`资源占用图`按资源展示加工、维护和不可用条带，用于确认日历维护/加班窗口是否影响资源能力；`工单流程图`按工单展示工序流转，用于确认订单经过哪些资源和时间段。
- 自动化证据：`python -m compileall -q sdbr`；`pytest tests/test_api.py -q -k "calendar_preview or ui_calendar or semantic_application_shell or admin_001_002" --basetemp .tmp/pytest-calendar-page -p no:cacheprovider`，4 passed。
- 用户确认：待确认。

### UI-RUN-003 Planning Run 详情

**状态：用户已确认**

详情页包含：

- 状态时间线
- 冻结输入引用
- 求解参数
- Worker 与租约摘要，不显示租约令牌或哈希
- 求解状态和结构化诊断
- 重试、死信和人工恢复历史
- 审计事件

并发冲突：收到 `409` 时显示“数据已更新”，提供 `重新加载`，不得静默覆盖。

### UI-SCHEDULE-001 排程结果工作区

**状态：用户已确认**

采用同一上下文内的标签视图：

- `甘特图`
- `资源负荷`
- `订单交期`
- `求解诊断`

甘特图要求：

- 资源或工作中心为纵轴，时间为横轴。
- 区分约束资源、非约束资源、维护时间和不可用时间。
- Processing 工序条与 Green、Yellow、Red Time Buffer 条必须视觉分离。
- 工序条显示订单、工序、开始结束、资源和缓冲状态。
- 悬浮详情至少包含条带类型、任务、开始、结束、订单号和资源。
- 支持缩放、时间范围和订单/资源筛选。
- 缩放必须包含分钟级查看档位；放大后时间轴刻度显示到小时/分钟，便于检查短工序、相邻工序和疑似资源重叠。
- 支持按资源、工单、持续时间类型、生产线和自定义业务字段筛选。
- 第一版仅查看，不提供未经后端约束校验的自由拖拽保存。

资源负荷要求：

- 数量和产能来自 API，不得写死。
- `系统负荷`视图按选定日期范围横向比较全部资源负荷百分比，支持按资源类型、位置、负责人和类别筛选。
- `资源负荷`视图按日显示单一资源的可用产能线、负荷柱、已释放/未释放构成和数值明细表。
- 同时显示负荷小时、可用产能、利用率、已释放、未释放和剩余负荷。
- `系统负荷`视图必须显示 S-DBR 运行控制摘要，包括计划负荷、安全日期、释放纪律、稳定性建议和非约束资源保护产能状态。
- P1 S-DBR market-control panel shows CCR planned load, MTO safe-date signal, MTA replenishment load visibility, unified buffer priority, and the boundary "no new DDAE protocol required for this internal execution read model".
- The P1 market-control panel must not expose raw JSON, DDAE master-setting governance controls, or DDMRP parameter editors.
- 非约束资源的保护产能状态为监控信号，不得在界面暗示已自动变成 CP-SAT 硬约束。
- 约束资源以可用产能为刚性边界；非约束资源允许显示超过 100% 的峰值和风险提示。
- 持续超载资源标为候选约束，但不自动修改主数据。

求解诊断要求：

- 主视图必须使用业务语言解释求解情况，例如“排程计算已设置时间上限”“模型已考虑备用资源、工序顺序、有限资源、换型、并行数量、时间窗和能力桶”等。
- `ORTOOLS_*`、求解器英文原文、策略 ID 等技术信息默认折叠在“技术详情”内，供审计和调试使用，不作为计划员主反馈。
- 诊断不应暗示业务异常；只有不可行、超时、缺数据或违反约束时才给出需要处理的业务动作。

验证记录：

- 2026-07-02：甘特图缩放从 100%/150%/200% 扩展为 100%/150%/200%/400%/800%/分钟级，放大后刻度按范围自适应到小时/分钟，支持检查短工序与相邻任务。自动化证据：`pytest tests/test_api.py -q -k "schedule_result_workspace" --basetemp .tmp/pytest-gantt-minute-zoom -p no:cacheprovider`。
- 2026-07-03：资源负荷页新增 S-DBR 运行控制摘要，展示计划负荷、安全日期、释放纪律、稳定性建议和非约束资源保护产能；明确非约束资源仅监控，不作为硬约束。自动化证据：`pytest tests/test_api.py -q -k "schedule_result_workspace" --basetemp .tmp/pytest-sdbr-flow-control -p no:cacheprovider`。
- 2026-06-25：`求解诊断`主视图改为业务摘要，`ORTOOLS_TIME_LIMIT_CONFIGURED`、`ORTOOLS_CP_SAT_MODEL`、`ORTOOLS_OBJECTIVE_STRATEGY` 等技术码默认折叠到“技术详情”。自动化证据：`python -m compileall -q sdbr`；`node --check sdbr/web/planner-workbench.js`；`pytest tests/test_api.py -q -k "semantic_application_shell or schedule_result or buffer_board or dispatch_priority" --basetemp .tmp/pytest-dispatch-diagnostics-ui-2 -p no:cacheprovider`，8 passed；`pytest -q --basetemp .tmp/pytest-full-dispatch-diagnostics-ui-2 -p no:cacheprovider`，363 passed，1 warning。

### UI-SCHEDULE-003 已排程工单网格

**状态：用户已确认**

该页面与 `UI-RUN-001 Planning Run 列表`严格区分：Planning Run 列表管理计算任务，本页面管理某次排程输出中的生产工单。

核心列：

- 工单号、物料、订单日期
- 计划释放日期
- 最终需求日期
- 承诺日期
- 准时状态和提前/延迟天数
- 释放状态、执行优先级
- 路线、工单族、分组资源

交互要求：

- 支持筛选、排序、分页、列显示和按列分组。
- 支持保存个人视图，不同视图保留筛选、列和分组状态。
- 支持批量锁定/解锁、设置优先级和进入释放评估。
- `重新排程`必须创建或触发受审计的 Planning Run，不允许只在前端改变顺序。
- `释放`不得绕过 `UI-RELEASE-001` 的物料、WIP和绳长门控。
- 显示本计划最近生成时间和数据是否过期。

### UI-SCHEDULE-002 方案比较

**状态：用户已确认**

- 基准方案与候选方案并列比较。
- 指标至少包括交期、约束负荷、总延迟、换用备用资源次数和缓冲风险。
- 不显示候选方案原始 JSON。
- 采用候选方案必须产生审计事件。

### UI-PLANPUB-001 计划发布治理

**状态：用户已确认**

计划发布治理嵌入 `排程结果` 页面，不新建孤立发布页。计划员在同一上下文中完成结果检查、复核、批准、发布状态查看和发布包追溯。

页面显示：

- 发布生命周期状态：草案、已复核、已批准、已发布、已撤销、已被替代、不可用。
- 允许动作：提交复核、批准计划、发布计划、撤销发布。
- 发布包摘要：发布包编号、计划指纹、目标系统、发布人、发布时间、订单数量、求解器状态。
- 发布历史：动作、前后状态、操作人、时间和备注。
- 替代关系：被哪次计划替代或替代了哪次计划。
- 输出治理摘要：输出可用性、内部输出包编号、完整性检查、释放建议/授权摘要、审计摘要、主数据版本和运行快照。

交互要求：

- 状态不得直接显示内部英文枚举；中文界面必须使用中文业务状态，英文界面使用业务英文标签。
- `发布计划`和`撤销发布`属于 Admin 权限动作；普通计划员界面可看到禁用或后端拒绝后的明确原因。
- 所有动作必须调用 `/planner/workbench/planning-runs/{run_id}/publication/*` 后端 API，不得只在前端改状态。
- 动作完成后必须重新读取发布状态，保持排程结果、发布包和审计历史一致。
- 输出治理摘要必须调用后台 governance/output-package read model，不得直接展示原始排程 JSON。
- 真实 ERP/MES 回写仍属于 `BE-INT-*`，本 UI 只显示内部发布包和目标系统占位。

### UI-RELEASE-001 释放管理工作区

**状态：用户已确认**

列表按执行优先级展示：

- 缓冲颜色与渗透率
- 绳长释放时间
- 物料齐套状态
- WIP 门控状态
- 计划开始时间
- 当前阻塞原因

主要动作：查看原因、重新评估、授权释放、查看调度包。

不得因排程已完成就默认释放工单。释放动作必须经过独立门控结果。

重新评估的业务语义：对同一个已完成 Planning Run 读取新的运行状态快照，重新判断物料、在途、WIP 和快照新鲜度；该动作不得重新求解排程，也不得要求重新建立任务包。授权释放时必须记录实际采用的运行状态快照。

**2026-06-22 补充说明：**如果释放管理显示“运行状态快照已过期”，页面必须提示“同步或生成新的资源/物料/WIP 快照后重新评估”；不得把该状态表达成“需要重新排程”。重排只在新鲜快照重新评估后，由稳定性阈值或人工决策触发。

**2026-06-22 Mock 闭环补充：**第一版采用 Mock API 时，“重新评估”按钮必须先调用 Mock 运行状态快照刷新接口，生成评估时点的新鲜资源/物料/WIP 快照，再重新读取释放门控；否则后续授权释放和约束缓冲执行页面无法验收。

**2026-06-21 补充验证：**“重新评估”按钮改为使用最新运行状态快照，普通切换计划仍默认显示冻结快照；若旧快照过期但最新快照新鲜，同一 Planning Run 可重新得到可释放结果，并在授权中记录最新快照 ID。自动化验证：`pytest -q --basetemp .tmp/pytest-full-release-reevaluate-final -p no:cacheprovider`，312 passed，1 warning。

**2026-06-21 补充验证：**释放管理顶部显示当前冻结释放策略版本；阻塞原因抽屉显示策略证据、触发参数和稳定性判断，包括策略绳长分钟、物料检查窗口、策略 WIP 上限、稳定性容忍与重排阈值；授权后的调度包保留释放策略版本。自动化验证：`pytest -q --basetemp .tmp/pytest-full-release-policy-final -p no:cacheprovider`，311 passed，1 warning。该补充属于现有 `UI-RELEASE-001` 的 read model 可见性增强，不新增大 UI 流程。

### UI-BUFFER-001 约束缓冲执行看板

**状态：用户已确认**

**2026-06-20 补充验证：**已修正排程结果中的建议释放时间，使其优先按 CP-SAT 计划首工序开始时间倒推时间缓冲；新增 `tests/test_business_closure.py::test_test_data_drives_release_authorization_and_buffer_execution_with_fresh_snapshot`，在 UI 默认 60 分钟快照新鲜度规则下验证“释放授权 -> 待接收 -> 已接收”的端到端业务分支。

**2026-06-25 体验边界修正：**缓冲执行页只展示约束缓冲矩阵、到达/未到达、红黄绿时间区域和工单缓冲状态；MES 派工建议队列迁移到独立 `派工建议 / Dispatch Suggestions` 页面，避免缓冲执行与派工排序混在同一业务页面。

顶部上下文：位置、约束资源、缓冲负责人、当日总负荷、最近排程时间。

主体采用固定二维矩阵：

| 流转阶段 | Early | Green | Yellow | Red | Late |
| --- | --- | --- | --- | --- | --- |
| 待接收 Yet to be Received | 工单 | 工单 | 工单 | 工单 | 工单 |
| 已接收 Received | 工单 | 工单 | 工单 | 工单 | 工单 |

要求：

- 每列显示工单数量和总负荷工时。
- 工单项至少显示工单号、物料、数量或工时。
- 点击工单打开详情，不依赖只能鼠标触发的悬浮交互。
- 详情显示客户、承诺日期、优先级、接收状态和当前原因。
- Late 区及按策略要求的缓冲区执行接收/开工事务时，必须选择标准原因码。
- 支持按数量、完成百分比或工时记录事务，但具体可用方式由后台配置决定。
- MES 派工队列不在缓冲执行页展示；独立派工建议页调用内部 read model，不执行真实 MES 投递。
- 业务边界：缓冲执行关注“工单是否已被释放、是否到达约束缓冲、处于哪个时间缓冲区域”；它不是资源前的实时排序页面。

验证记录：

- 2026-06-25：缓冲执行页与派工建议页完成 UI 边界拆分，缓冲页只进入 `loadBufferBoardRuns()` / 缓冲矩阵链路；MES 派工建议控件迁移到独立 `dispatch-suggestions` 路由。自动化证据：`python -m compileall -q sdbr`；`node --check sdbr/web/planner-workbench.js`；`pytest tests/test_api.py -q -k "semantic_application_shell or schedule_result or buffer_board or dispatch_priority" --basetemp .tmp/pytest-dispatch-diagnostics-ui-2 -p no:cacheprovider`，8 passed；`pytest -q --basetemp .tmp/pytest-full-dispatch-diagnostics-ui-2 -p no:cacheprovider`，363 passed，1 warning。

### UI-DISPATCH-001 派工建议工作台

**状态：已验证待用户确认**

页面位置：独立导航页 `派工建议 / Dispatch Suggestions`。

业务定义：

- 派工建议的对象是“资源/工作中心前等待加工的工序队列”，通常表现为某个工单的某道工序，不等同于释放整个工单。
- 如果资源前没有排队，MES 可以按本地规则直接开工，并通过执行事件回传 SDBR。
- 如果资源前出现排队，或存在红区/高渗透、约束资源冲突、插队风险、异常延误，MES 可请求 SDBR 返回排序建议。

页面显示：

- 按资源/工作中心折叠展示正式派工队列与候选/预警。
- 显示缓冲颜色、渗透率、计划顺序、派工顺序、冲突结果、现场到达状态、释放状态、建议动作和是否需要调度员确认。
- 显示派工建议包生成按钮、包编号和 Mock 投递状态。

交互边界：

- 只生成内部 Mock 派工建议包，不真实下发 MES。
- 未释放或最新门控阻塞的工单显示为候选/预警，不得混入正式队列。
- 后续真实 MES Direct Adapter 或 UNS Topic 必须消费同一派工建议语义。
- 本看板属于现场执行协同边界；完整操作工终端仍不在第一版范围内。
- SDBR 派工建议依赖最新执行事件和运行状态快照，不要求系统持续掌握工厂每一秒状态；触发重排或释放复核时必须使用足够新鲜的现场快照。

验证记录：

- 2026-06-25：新增独立导航 `派工建议 / Dispatch Suggestions`，页面可选择已完成计划和评估时间，调用派工优先级 read model，按资源/工作中心展示正式队列、候选预警和 Mock 派工建议包生成入口。自动化证据同 `UI-BUFFER-001` 2026-06-25 记录，状态保持“已验证待用户确认”。
- 2026-06-26：补充 MES 与 SDBR 的时序边界：缓冲执行负责工单释放/到达/缓冲状态，派工建议负责资源前工序队列排序；无排队时 MES 可直接开工，有排队或风险时再请求 SDBR 排序。
- 2026-06-26：派工建议页按 `缓冲执行` 页面版式收紧面板标题、说明文字、按钮、统计栏和资源折叠行字号；`MES 派工队列` 降为面板内标题层级，不再形成独立页面主标题视觉焦点。

### UI-DEMO-001 公开演示闭环页面

**状态：已验证待用户确认**

页面位置：独立导航页 `公开演示闭环 / Public Demo Loop`。

业务定义：

- 页面用于 `PUBLIC-DEMO-GOLDEN-DATA-V1 Controlled Contract Golden Loop Demo`，只演示文件化契约交接，不代表生产验证或 Business Golden Loop readiness。
- 页面读取 DDAE handoff payload，显示 schema、状态/审批、fingerprint、crosswalk 文件和 reviewed candidate mapping 校验。
- 页面使用 `DemoFixture`、`ReviewedEvidence`、`Controlled Contract Golden Loop Demo`、`MappingConfidence = PublicDemoOnly` 标签，不得显示生产权威或生产验证结论。

页面显示：

- 冻结数据包状态、checksum、canonical file 数量和 crosswalk 文件状态。
- DDAE 到 SDBR handoff 的 MessageID、IdempotencyKey 和读取状态。
- 契约 ACK、fingerprint、reviewed candidate mapping 命中情况。
- SDBR 到 DDAE feedback handoff 文件的存在性和大小。
- 非声明列表：不声明 `ProductionValidated`、不声明 Business Golden Loop readiness、不声明 production authority。

交互边界：

- `运行演示闭环`只在 handoff payload 通过当前契约校验时生成 demo fixture feedback 文件。
- 若 payload 不符合契约 schema，页面必须显示阻塞原因，不能绕过契约生成 feedback。
- 不重新抽取 AdventureWorks，不自动创建 SDBR 生产主数据，不修改契约仓库 schema/examples/tests/changelog。

验证记录：

- 2026-06-29：新增 `public-demo` 路由、页面卡片和 FastAPI read/run 接口；`python -m compileall -q sdbr` 通过，bundled Node `--check sdbr\web\planner-workbench.js` 通过，FastAPI TestClient 返回 `200 Blocked` / `200 ValidationBlocked`。当前 DDAE handoff payload 因 `Payload.ChangeReason.ReasonCode=CONTROLLED_CONTRACT_DEMO` 不在契约 schema 枚举内被拒绝，页面显示阻塞且不写 feedback。
- 2026-06-30：新增 AdventureWorks 排程 Adapter 只读校验区，展示 `ADVENTUREWORKS-BOUNDED-SCHEDULING-ADAPTER-PROFILE-V1`、`BoundedAdapterFixtureSchedulingMode`、7 个 SDBR-owned AW 资源日历映射、生成工单/工序行数和正式求解入口 gate；按 Contract Agent correction gate 补充 `MaterialConstraintsMode = OmittedForPublicDemo` 与“物料可行性生产声明：否”，避免把公开演示上下文误读为生产物料可行性证明。
- 2026-07-01：按 `PUBLIC_DEMO_BUSINESS_USER_DEMO_V1_IMPLEMENTATION_NEXT_ACTIONS_20260701.md` 在公开演示闭环内容区最下方新增业务用户演示视图；该视图位于冻结数据包、DDAE 到 SDBR、校验结果、AdventureWorks Adapter、SDBR 到 DDAE 和非声明区域之后，不新增左侧导航、不重排既有技术区；内容用业务语言说明 SDBR 收到什么、校验什么、转换什么、不声明什么、反馈什么，并保留 `OmittedForPublicDemo`、`PublicDemoOnly`、正式求解入口 gated 等边界。
- 2026-07-01：按 Contract Agent 导航顺序要求，将左侧导航中的 `公开演示闭环 / Public Demo Loop` 移到导航列表最下面；页面内部技术区和底部业务用户演示视图顺序不变。
- 2026-07-01：按 `ADVENTUREWORKS_PRODUCT_DEMO_V1_SCOPED_IMPLEMENTATION_DISPATCH_NEXT_ACTIONS_20260701.md` 在公开演示闭环技术区新增 `AdventureWorks 产品演示 Profile` 卡片，展示 ProductDemoMode profile、DemoAuthority 状态、SDBR authority 行数、source-class coverage、PanelPolicy、setup/material omission blocking rule 和 validation dead-letter 数；该卡片位于契约校验之后、AdventureWorks Adapter 之前，底部业务用户演示视图仍保持页面内容区最下方；页面继续保留 `ProductDemoOnly` / `PublicDemoOnly` 分层口径，不声明生产物料可行性、ProductionValidated 或 Business Golden Loop readiness。

### UI-EXCEPTION-001 异常与死信中心

**状态：用户已确认**

统一展示：

- Planning Run 失败和 DeadLetter
- 物料不足
- WIP 超限
- 未到绳长时间
- 主数据缺失
- 约束缓冲风险
- 执行偏差与重排建议

每项异常必须包含：严重程度、对象、发生时间、原因代码、业务影响、建议动作和审计历史。

人工恢复必须填写原因，并显示是否重置尝试次数。

### UI-ADMIN-001 主数据后台

**状态：基础管理后台用户已确认；日历配置已迁移到独立页面**

**当前实现边界：**用户确认的是管理后台基线。日历配置不再放在管理后台；基础日历、资源分配、临时覆盖、事项预览和最终能力窗口统一迁移到独立 `日历配置` 页面。管理后台保留主数据、集成、求解器与策略类管理信息，不重复提供日历设置入口，避免用户在两个位置维护同一类配置。

后台按对象分区：资源、日历、工艺路线、订单、库存缓冲、物料需求。

- 支持文件导入和结构化预览。
- 工艺路线必须提供导入入口。
- 导入前预校验，导入后生成版本。
- 错误按行、字段和严重程度展示。
- 原始 JSON 仅允许在管理员调试模式查看，默认隐藏。
- 资源类型明确区分 `Constraint`、`Buffered Resource`和普通`Resource`。
- 资源字段至少预留缓冲时间、资源数量、换型时间、固定偏移、班组人数、效率和负责人。
- 资源日历分为日定义、周定义、临时班次覆盖和排除/修改四层。
- 临时班次覆盖和维护排除必须显示生效日期范围，不允许只修改一个不可追溯的总工时数字。

### UI-ADMIN-002 集成与求解器设置

**状态：用户已确认**

页面显示：

- ERP、MES 连接状态和最近同步时间。
- 集成模式显示 Direct Adapter、UNS MQTT Adapter、Mock API Adapter 的启用状态、最近消息时间、死信数量和重放入口；第一版活动方式为 Mock API，Direct 与 UNS 仅作为后续可替换路径展示。该显示对应后台 `BE-INT-*` 的 Canonical Message + Integration Port + 可替换 Adapter 架构。
- MES 第一版只显示派工建议队列，不显示为真实下发、已投递或已连接 MES。
- OR-Tools CP-SAT、Gurobi 能力状态；CP-SAT 显示可用，Gurobi 显示已暂停。
- Simio 验证接口状态；当前显示为可用的可选仿真验证能力，不参与求解器选择。
- Worker 在线状态、心跳和队列指标。
- SQLite 健康、备份和恢复状态。

该页面只显示系统能力，不允许普通计划员修改敏感连接参数。

排程策略配置至少分组显示：

- 速率解释方式：件/小时、小时/件、分钟/件。
- 缓冲、换型、持续时间和固定偏移的单位。
- 排程窗口、首选完工/发货时间和截止规则。
- 缓冲区边界比例。
- 哪些缓冲区事务必须填写原因码。
- 执行优先级规则，区分缓冲件、Min/Max件和非缓冲件。

这些参数属于 Admin 配置，不应出现在计划员每次创建排程的主表单中；创建向导只显示允许覆盖的少数策略。

## 9. 通用组件规格

### UI-COMP-001 状态标签

所有状态使用统一组件，包含颜色、图标和双语文字。禁止不同页面为同一状态使用不同颜色。

### UI-COMP-002 数据表格

必须支持：加载态、空态、错误态、分页、排序、筛选、列宽稳定和键盘焦点。

### UI-COMP-003 详情抽屉

用于快速查看订单、资源、诊断和异常，不应替代需要持续工作的完整页面。

### UI-COMP-004 确认对话框

取消、人工恢复、授权释放和采用候选方案必须显示影响范围，禁止使用模糊的“确定吗”。

### UI-COMP-005 通知

- 成功操作使用短暂通知。
- 需要人工处理的错误不得只用短暂通知，必须在页面保留。
- 后端错误消息应转换为业务语言，同时保留可展开的技术诊断。

## 10. 双语规范

### UI-I18N-001 中英文切换

**状态：用户已确认**

- 所有导航、按钮、状态、错误和表头都必须双语覆盖。
- 用户选择保存在本地，并在刷新后保持。
- 日期、数字和时区按语言格式化，但业务时间值不得改变。
- 中文为默认语言，英文术语遵循本规格中的英文名称。
- 不允许页面出现未翻译的键名或内部枚举值。
- 业务对象名称、字段标签和状态文字必须完整翻译，不得在中文词条中混用英文业务名称。
- 对象 ID、字段路径、审计代码、求解器品牌和行业通用缩写保持原值；中文界面必须使用中文标签说明其含义，例如“运行状态快照编号：OPS-RUNTIME-REVISION-1”。
- 自动化验收必须断言关键中文词条不含英文业务名称；浏览器验收必须分别检查中英文页面，且语言切换不得改变对象 ID。

## 11. API 映射

| UI 功能 | 主要 API |
| --- | --- |
| 数据版本 | `POST/GET /planner/workbench/master-data/versions` |
| 运行快照 | `POST/GET /planner/workbench/operational-state/snapshots` |
| 排程任务列表 | `GET /planner/workbench/planning-runs` |
| 创建排程 | `POST /planner/workbench/planning-runs` |
| 入队 | `POST /planner/workbench/planning-runs/{run_id}/enqueue` |
| 执行 | `POST /planner/workbench/planning-runs/{run_id}/execute` |
| 取消 | `POST /planner/workbench/planning-runs/{run_id}/cancel` |
| 死信恢复 | `POST /planner/workbench/planning-runs/{run_id}/recover` |
| 队列指标 | `GET /planner/workbench/planning-runs/metrics` |
| 审计 | `GET /planner/workbench/planning-runs/audit-events` |
| 场景比较 | `POST /planner/workbench/scenarios/compare` |
| 释放评估 | `POST /planner/workbench/release` |
| 重排请求 | `/planner/workbench/replan-requests...` |
| 释放授权 | `/planner/workbench/release-authorizations...` |
| 状态存储健康 | `GET /planner/workbench/state-store/health` |

UI 不得直接构造或修改 SQLite 数据。

## 12. 加载、错误和并发状态

### UI-STATE-001 加载状态

- 首屏使用稳定骨架或区域加载指示，不导致布局跳动。
- 长时间排程显示任务状态，不在浏览器中无限等待一个同步动画。

### UI-STATE-002 空状态

- 空状态说明缺少什么以及下一步动作。
- 不使用虚构订单填充生产页面。

### UI-STATE-003 错误状态

- `400/422`：输入或字段问题。
- `401`：需要身份认证。
- `403`：权限不足。
- `404`：对象不存在或已被移除。
- `409 StateStoreRevisionConflict`：重新加载后再操作。
- `409 PlanningRun...`：显示当前状态及允许动作。
- `5xx`：保留请求上下文并允许重试，不清空用户输入。

### UI-STATE-004 数据新鲜度

运行快照必须显示捕获时间和新鲜度。过期数据创建排程时必须警告，严重过期时按后端规则禁止提交。

## 13. 安全和审计

- UI 根据角色隐藏或禁用操作，但后端仍是最终权限边界。
- 所有写请求读取并更新 `X-Workbench-Revision`。
- 关键写操作发送 `If-Match`。
- UI 不显示或保存 Worker 租约令牌。
- 创建、执行、取消、恢复、授权释放和采用方案均可追溯。
- 管理页面不得在前端日志输出连接密钥或敏感配置。

## 14. 可访问性与可用性

- 所有图标按钮提供工具提示和可访问名称。
- 所有表单控件有可见标签。
- 键盘可以到达主要导航、筛选和业务动作。
- 焦点状态清晰。
- 正文和状态文字满足常规对比度要求。
- 红黄绿状态同时使用文字或图标，兼容色觉差异。

## 15. 测试与验收

每个页面至少验证：

- 中文与英文
- 1280×720 和 1920×1080
- 窄屏抽屉导航
- 加载、空数据、成功、权限不足、服务错误和 409 冲突
- 表格分页与筛选
- 不出现重叠、裁切、不可读文字或无响应按钮
- API 请求与本规格映射一致

关键流程使用浏览器端到端测试：

1. 选择有效数据并创建 Planning Run。
2. 入队并观察状态变化。
3. 查看完成结果和诊断。
4. 模拟失败、重试、DeadLetter和人工恢复。
5. 进入释放管理并查看门控原因。
6. 切换语言并保持业务上下文。

## 16. 实施顺序与确认门

| 顺序 | 验收单元 | 包含规格 | 完成后必须获得用户确认 |
| --- | --- | --- | --- |
| 1 | 应用外壳 | UI-SHELL-001、UI-DS-001、UI-I18N-001 | 是 |
| 2 | 数据就绪 | UI-DATA-001、UI-DDMRP-001 | 是 |
| 3 | Planning Run 中心 | UI-RUN-001、UI-RUN-002、UI-RUN-003 | 是 |
| 4 | 排程结果 | UI-SCHEDULE-001、UI-SCHEDULE-002 | 是 |
| 5 | 排程工单与释放 | UI-SCHEDULE-003、UI-RELEASE-001 | 是 |
| 6 | 缓冲执行看板 | UI-BUFFER-001 | 是 |
| 7 | 异常中心 | UI-EXCEPTION-001 | 是 |
| 8 | 管理后台 | UI-ADMIN-001、UI-ADMIN-002 | 是 |
| 9 | 通用质量 | UI-COMP-001 至 UI-COMP-005、UI-STATE-001 至 UI-STATE-004 | 是 |
| 10 | 活动求解器切换 | UI-RUN-002、UI-ADMIN-002 | 是 |
| 11 | 计划发布治理 | UI-PLANPUB-001 | 是 |
| 12 | 测试案例验收总览 | UI-OVERVIEW-001 | 是 |

任何验收单元未确认前，原则上不进入下一单元的正式开发；若用户明确要求继续，未确认单元状态保持 `已验证待用户确认`，不得写成 `用户已确认`。

## 17. 第一验收单元的预期成果

用户确认本规格后，首先实施：

- 新应用外壳与左侧导航
- 顶部计划上下文
- 中文/英文切换
- 系统健康状态
- 当前页面路由和空内容框架
- 桌面及窄屏布局验证

第一单元不修改 Gurobi、Planning Run、释放逻辑和数据库结构。

### 17.1 第一验收单元记录

- 规格：`UI-SHELL-001`、`UI-DS-001`、`UI-I18N-001`
- 状态：已验证待用户确认（原第一验收单元已确认；2026-06-24 导航业务解释增强待确认）
- 实现：`sdbr/web/planner-workbench.html`、`planner-workbench.css`、`planner-workbench.js`
- 后端接入：保留 `/planner/workbench` 地址，系统健康读取 `/planner/workbench/state-store/health`
- 自动化验证：2026-06-19 执行 `pytest -q`，`223 passed, 2 warnings`
- 浏览器验证：1280x720 桌面布局、390x844 窄屏抽屉、中英文切换及刷新保持、Hash 路由、系统健康状态、无横向溢出
- 2026-06-24 增强：左侧导航项支持桌面 hover 与键盘 focus 自动弹出业务解释，说明复用页面标题区双语文案；移动端抽屉不强制显示悬浮说明，避免遮挡触摸导航。
- 用户确认：已确认（2026-06-19）
- 本次增强用户确认：待确认

### 17.2 第二验收单元记录

- 规格：`UI-DATA-001`、`UI-DDMRP-001`、`UI-DDMRP-002`
- 后台依赖：`BE-UI-001`、`BE-DDMRP-001` 至 `BE-DDMRP-006`
- 状态：`UI-DATA-001` 用户已确认；`UI-DDMRP-001`、`UI-DDMRP-002` 已验证待用户确认
- 实现：数据就绪聚合 API、最新主数据与运行快照摘要、真实空/阻塞状态、按严重度分组的问题抽屉、排程输入选择门控
- 安全边界：日常页面不返回或显示资源、路线、订单等原始 JSON 数组
- 自动化验证：2026-06-19 执行 `pytest -q`，`227 passed, 2 warnings`
- 浏览器验证：真实持久化数据、阻塞状态、未来快照预警、问题抽屉开关、创建版本导航、禁用无效输入选择、无页面内容重叠
- 双语修正：问题严重度、对象类型、定位、技术代码及主数据/运行快照业务名称全部随语言切换；对象 ID、字段路径和审计代码保留原值
- 本地化回归：中文显示“最新主数据版本”“最新运行状态快照”“快照编号”和“在制品（WIP）范围”；中英文切换前后 `OPS-RUNTIME-REVISION-1` 保持不变
- DDMRP 增强：2026-06-25 数据就绪中心新增只读 `DDMRP 运行状态`，展示解耦点、红黄绿/高于绿区数量、补货建议、缺失数据和可展开明细；无 DDMRP 参数配置、Buffer Profile 治理或调整因子审批入口；测试数据新增 `TST-DDMRP-MDV-NET-FLOW-20260625`，可直观看到红/黄/绿/高于绿区各 1 个、补货建议 2 个；自动化验证 `pytest tests/test_ddmrp.py tests/test_material_state.py tests/test_api.py -q -k "ddmrp or light_mrp or data_readiness_workspace" --basetemp .tmp/pytest-ddmrp-focused-2 -p no:cacheprovider`，10 passed；`pytest tests/test_ddmrp.py tests/test_test_data.py tests/test_api.py -q -k "ddmrp or test_case_catalog or seeded_test_database or data_readiness_workspace" --basetemp .tmp/pytest-ddmrp-demo-case -p no:cacheprovider`，12 passed；全量 `pytest -q --basetemp .tmp/pytest-full-ddmrp -p no:cacheprovider`，359 passed，1 warning
- DDMRP 体验修正：2026-06-25 将解耦点明细折叠控件调整为与仿真输出一致的“展开/收起”动作；版本编号来源提示降级为辅助字号，避免在数据就绪页形成错误视觉焦点。
- DDMRP 工作台：2026-06-25 新增独立 `物料计划 / Materials Planning` 导航页，复用 `/planner/workbench/ddmrp/status` 展示物料-地点净流工作台、搜索、缓冲区筛选、优先级/缓冲百分比/建议补货量排序和只读详情；红/黄区显示建议补货，绿区和高于绿区不显示补货动作；趋势图保留后续占位，不提供 DDMRP 参数配置或外部订单生成。
- 用户确认：已确认（2026-06-19）
- DDMRP 新增项用户确认：待确认

### 17.3 第三验收单元记录

- 规格：`UI-RUN-001`、`UI-RUN-002`、`UI-RUN-003`
- 后台依赖：`BE-UI-002`
- 状态：用户已确认
- 实现：Planning Run 指标与列表、状态/时间/请求人/求解器/异常筛选、三步创建向导、详情抽屉和生命周期动作
- 策略一致性：创建时冻结 TimeLimit、最大尝试次数与重试延迟；直接执行和入队使用该 Planning Run 的冻结参数
- 历史验收时的集成边界：当时 Gurobi 可用；OR-Tools 与 Simio 按产品路径展示但保持暂停；当前状态以第十验收单元为准
- 安全边界：详情仅显示 Worker 与租约摘要，不返回租约令牌或哈希
- 自动化验证：2026-06-19 执行 `pytest -q`，`231 passed, 2 warnings`；前端脚本通过 Node.js 语法检查
- 历史运行时验证：服务返回 200；OpenAPI 默认策略为 TimeLimit 300 秒、最大尝试 3 次、重试延迟 60 秒；当时工作台能力接口报告 Gurobi 可用、OR-Tools/Simio 暂停
- 浏览器验证：原标签页停留在服务短暂重启产生的浏览器错误页，自动接管重载被安全策略阻止；服务已恢复，待用户手动刷新并进行产品确认
- 用户确认：已确认（2026-06-19）

### 17.4 第四验收单元记录

- 规格：`UI-SCHEDULE-001`、`UI-SCHEDULE-002`
- 后台依赖：`BE-UI-003`、`BE-OUT-001` 至 `BE-OUT-007`
- 状态：用户已确认
- 实现：按 Planning Run 读取结果 KPI、四标签结果工作区、可筛选缩放甘特、系统/单资源负荷、订单交期、求解诊断和方案比较
- 甘特表达：区分加工、绿/黄/红时间缓冲、维护和不可用时间；第一版只读，不提供自由拖拽保存
- 负荷表达：数量和产能来自 API；显示产能边界、已释放/未释放、剩余负荷、超载和候选约束提示
- 方案治理：按 Run ID 比较基准/候选方案，推荐结果使用稳定决策代码；采用方案写入 `ScheduleScenarioSelected` 审计并进入审核，不直接发布
- 安全边界：页面不返回或展示原始 `Schedule` JSON；隔离验收服务不写入正式 SQLite 数据
- 自动化验证：2026-06-19 执行 `pytest -q`，`235 passed, 2 warnings`；Python 编译和前端脚本语法检查通过
- 浏览器验证：真实空状态；隔离完成态样本的 KPI、三类业务条带及维护条带、系统负荷、逐日负荷、方案推荐、中英文切换；1280×720 桌面无溢出，390×844 窄屏修正后页面宽度与客户端宽度均为 375px
- 用户确认：已确认（2026-06-19）

### P1 S-DBR 市场控制 UI 验收记录

- 规格：`UI-SCHEDULE-001`
- 后台依赖：`BE-SDBR-001` 至 `BE-SDBR-004`
- 日期：2026-07-09
- 范围：排程结果页新增“市场承诺与约束保护”只读面板，展示约束计划负荷、MTO 安全承诺、MTA 补货负荷和统一缓冲优先级。
- 边界：UI 不提供 DDAE 主参数编辑、DDMRP 参数配置、Buffer Profile 治理、原始 JSON 展示或正式承诺交期声明。
- 自动化验证：`pytest tests/test_api.py::test_schedule_results_page_exposes_p1_market_control_panel -q --basetemp .tmp/pytest-p1-ui-green -p no:cacheprovider`；`node --check sdbr/web/planner-workbench.js`。
- 状态：已验证待用户确认。

### 17.5 第五验收单元记录

- 规格：`UI-SCHEDULE-003`、`UI-RELEASE-001`
- 后台依赖：`BE-OUT-008`、`BE-OUT-009`、`BE-UI-004`、`BE-REL-001` 至 `BE-REL-007`
- 状态：用户已确认
- 已排程工单：按 Planning Run 返回工单、交期、路线、资源、释放、执行优先级和锁定状态；支持筛选、排序、分页、分组、列选择和本地保存视图
- 受审计操作：批量锁定、解锁和优先级命令写入 Planning Run 审计；重新排程返回 Planning Run 中心，不在前端改序
- 释放门控：复用现有绳长、物料、在途和 WIP 逻辑；动态输出缓冲渗透、执行优先级、结构化阻塞原因和 `CanAuthorize`
- 授权边界：仅 `ReadyForRelease` 且运行状态快照新鲜的工单可授权；授权记录冻结快照来源并生成可查看的调度包
- 安全边界：排程完成不等于释放；已排程工单页不提供绕过门控的直接释放动作
- 自动化验证：2026-06-19 执行 `pytest -q`，`239 passed, 2 warnings`；前端脚本语法检查通过
- 运行时验证：服务返回 200，新工单/释放 OpenAPI 路径可用；当前正式数据无已完成任务时保持真实空状态
- 浏览器验证：服务重启后当前标签页被浏览器安全策略阻止自动接管；未绕过限制，待用户刷新后进行产品确认
- 用户确认：已确认（2026-06-19）

### 17.6 第六验收单元记录

- 规格：`UI-BUFFER-001`
- 后台依赖：`BE-REL-010`、`BE-EXEC-001` 至 `BE-EXEC-004`
- 状态：用户已确认
- 看板聚合：按 Planning Run 组合已授权工单、冻结计划、约束资源和执行事件，固定输出 Yet to be Received/Received 两阶段与 Early/Green/Yellow/Red/Late 五区域
- 业务摘要：顶部显示位置、约束资源、缓冲负责人、当日总负荷和最近排程时间；每个矩阵单元显示工单数、总工时与工单卡片
- 事务边界：详情显示客户、承诺日期、优先级、接收状态和当前原因；支持后台配置的数量、完成百分比和工时记录方式，Late 区接收/开工强制标准原因码
- MES 边界：页面只提供计划与现场协同事务，不承担扫码、设备采集或完整操作员终端职责
- 派工边界调整：2026-06-25 MES 派工队列迁移到独立 `UI-DISPATCH-001` 页面；缓冲执行页只保留两阶段五区域缓冲矩阵和工单缓冲状态。
- 自动化验证：2026-06-19 执行 `pytest -q`，`243 passed, 2 warnings`；Python 编译和前端脚本语法检查通过
- 运行时验证：服务返回 200，OpenAPI 包含缓冲看板、工单详情和事务路由；正式数据无已完成计划时保持真实空状态
- 浏览器验证：中文与英文标题、说明、导航和空状态正确切换；当前 599px 窄窗口下页面宽度与内容宽度均为 599px，无整页横向溢出；控制台无错误
- 用户确认：已确认（2026-06-19）

### 17.6A 派工建议验收单元记录

- 规格：`UI-DISPATCH-001`
- 后台依赖：`BE-REL-011`、`BE-INT-005`
- 状态：已验证待用户确认
- 实现：独立派工建议页按资源/工作中心折叠展示正式队列、候选/预警、插队冲突、现场状态、释放状态、调度员确认提示和 Mock 派工建议包生成。
- 安全边界：第一版只生成内部 Mock 派工建议，不真实下发 MES；未来 Direct Adapter 或 UNS 适配器必须复用同一派工建议语义。
- 用户确认：待确认

### 17.7 第七验收单元记录

- 规格：`UI-EXCEPTION-001`
- 后台依赖：`BE-UI-005`、`BE-REL-008`、`BE-EXEC-005`
- 状态：用户已确认
- 聚合范围：统一展示 Planning Run 失败与 DeadLetter、约束缓冲风险、执行预警和重排建议；释放阻塞类数据通过同一异常模型预留来源与动作代码
- 业务字段：每项异常包含严重程度、对象、发生时间、原因代码、业务影响、建议动作、负责人和审计历史
- 交互边界：支持按严重程度和来源筛选，点击详情查看关联对象、处理动作和审计历史；不显示原始后端对象或 JSON
- 自动化验证：2026-06-19 执行 `pytest -q`，`246 passed, 2 warnings`；Python 编译和前端脚本语法检查通过
- 运行时验证：服务返回 200，OpenAPI 包含异常中心聚合与详情路由；正式数据当前显示真实异常/空状态
- 浏览器验证：异常中心中文与英文标题、导航和表头正确切换；1280px 页面无整页横向溢出；控制台无错误
- 用户确认：已确认（2026-06-19）

### 17.8 第八验收单元记录

- 规格：`UI-ADMIN-001`、`UI-ADMIN-002`
- 后台依赖：`BE-UI-006`、`BE-DATA-010`、`BE-DATA-011`、`BE-INT-007`、`BE-OPS-006`
- 状态：用户已确认
- 范围：主数据后台按对象分区，提供导入预览入口、预校验结果、版本生成入口、资源扩展字段和日历四层展示；系统设置展示 ERP/MES、Gurobi/OR-Tools、Simio、Worker 队列和 SQLite 健康状态
- 历史验收时的边界：默认不显示原始 JSON，不允许普通计划员修改敏感连接参数；当时 OR-Tools 和 Simio 保留产品路径但显示暂停/不可用；当前求解器状态以第十验收单元为准
- 自动化验证：2026-06-19 执行 `pytest -q`，`248 passed, 2 warnings`；Python 编译和前端脚本语法检查通过
- 运行时验证：服务返回 200，OpenAPI/HTTP 包含管理后台聚合路由；`/planner/workbench/administration/workbench` 返回安全只读 read model
- 浏览器验证：中文与英文后台标题、工艺路线导入入口、系统设置标题和原始 JSON 调试提示正确切换；1280px 页面无整页横向溢出；控制台无错误
- 用户确认：已确认（2026-06-19）

### 17.9 第九验收单元记录

- 规格：`UI-COMP-001` 至 `UI-COMP-005`、`UI-STATE-001` 至 `UI-STATE-004`
- 状态：用户已确认
- 范围：统一状态标签、数据表格、详情抽屉、确认对话框、通知、加载态、空态、错误态和数据新鲜度表达
- 边界：本单元不新增业务能力，只做跨页面质量一致性、可访问性和回归检查
- 自动化验证：2026-06-19 执行 `pytest -q`，`249 passed, 2 warnings`；Python 编译和前端脚本语法检查通过
- 运行时验证：服务返回 200，前端资产返回 200；统一通知区、确认对话框和质量组件标记可被页面读取
- 浏览器验证：计划任务页面中文显示正常，统一状态标签、表格、加载/空/错误状态、通知区和确认对话框均存在；1280px 页面无整页横向溢出；页面控制台无错误
- 用户确认：已确认（2026-06-19）

### 17.10 第十验收单元记录

- 规格：`UI-RUN-002`、`UI-ADMIN-002`
- 状态：用户已确认
- 变更原因：产品活动求解器由 Gurobi 切换为 OR-Tools CP-SAT
- 验收范围：创建向导默认选择且仅允许 CP-SAT；Gurobi 同级显示但为“已暂停”；Simio 作为计划完成后的可选验证能力显示；历史计划保持真实求解器名称
- 自动化验证：2026-06-19执行 `pytest -q`，267 passed，2 warnings；前端脚本语法检查通过
- 运行时验证：Planning Run和管理后台能力接口报告 OR-Tools CP-SAT可用且可选择、Gurobi为Paused且不可选择；历史结果保留真实求解器标识
- 2026-06-20 补强：管理后台读取 `GET /planner/workbench/admin/cp-sat/assumptions`，展示 CP-SAT 建模假设、可调参数、暂停求解器和延后规则，避免把未实现的 MRP/批次/Simio 反馈误导为已启用；前端脚本增加版本参数以避免旧浏览器缓存；自动化验证 `pytest tests/test_api.py -q -k "semantic_application_shell or admin_001_002 or plan_publication_governance or case_acceptance_overview or cp_sat_assumptions" --basetemp .tmp/pytest-ui-pending-confirmation-regression -p no:cacheprovider`，5 passed；全量验证 `pytest -q --basetemp .tmp/pytest-full-ui-pending-confirmation-20260620-final2 -p no:cacheprovider`，305 passed，1 warning
- 浏览器验证：2026-06-20 使用测试库三组 `TST-RUN-*` 已完成计划验证；创建向导显示 CP-SAT 默认可用、Gurobi 禁用、Simio 禁用；管理后台中英文显示 CP-SAT 可用、Gurobi 暂停、Simio 暂不可用，并展示 CP-SAT 建模假设/可调参数/延后规则；390px 窄屏无横向溢出
- 2026-06-23 更新：Simio Local Headless / Mock 验证 API 已接入，管理后台和 Planning Run 能力接口将 Simio 显示为可用的可选验证能力；创建向导不再显示“已暂停”，排程结果页新增 `仿真结果 / Simulation Results` 页签，可发起验证并展示可行性、吞吐、队列、WIP、资源利用率、计划偏差和问题清单。
- 2026-06-24 更新：管理后台新增 `Simio 仿真模板 / Simio simulation templates` 只读区域，读取 `/planner/workbench/simio/templates`，展示活动模板、模板版本、时间单位规则、Desktop 校验状态和技术详情折叠区。
- 用户确认：已确认（2026-06-20）

### 17.11 第十一验收单元记录

- 规格：`UI-PLANPUB-001`
- 后台依赖：`BE-RUN-009`、`BE-OUT-010`、`BE-OPS-002`
- 状态：用户已确认
- 范围：在排程结果页面内嵌计划发布治理区，显示发布状态、允许动作、发布包摘要、发布历史和替代关系
- 边界：只调用内部发布生命周期 API；真实 ERP/MES 回写仍由 `BE-INT-*` 跟踪
- 自动化验证：2026-06-20 执行 `python -m compileall -q sdbr`；`pytest tests/test_api.py -q -k "semantic_application_shell or admin_001_002 or plan_publication_governance or case_acceptance_overview or cp_sat_assumptions" --basetemp .tmp/pytest-ui-pending-confirmation-regression -p no:cacheprovider`，5 passed；`pytest -q --basetemp .tmp/pytest-full-ui-pending-confirmation-20260620-final2 -p no:cacheprovider`，305 passed，1 warning
- 浏览器验证：2026-06-20 在 `#schedule-results` 验证排程结果内嵌治理区存在；中文显示“计划发布治理”“草案”“提交复核”，英文显示 “Plan publication governance”“Draft”“Submit for review”；发布包与发布历史区域存在；桌面和 390px 窄屏无横向溢出
- 补充验证：2026-06-21 排程结果页同一治理区新增“输出治理”摘要，展示输出可用性、输出包编号、计划指纹、主数据版本、运行快照、释放建议/授权摘要、审计摘要和外部投递占位；页面调用 `/planner/workbench/schedule-results/runs/{run_id}/governance` 与 `/planner/workbench/schedule-results/runs/{run_id}/output-package`，不返回或展示原始大 JSON；自动化验证 `pytest tests/test_api.py -q -k "be_out_010 or be_out_008_009 or schedule_result_workspace" --basetemp .tmp/pytest-output-governance-detail -p no:cacheprovider`，4 passed
- 体验收口：2026-06-24 将计划治理区从接口字段堆叠调整为业务决策路径：发布进度、输出准备、释放准备、仿真验证、操作留痕；技术码、模型路径、解析来源和外部投递原因默认折叠到“技术详情”；仿真事件状态和问题说明改为业务化中文。验证：`python -m compileall -q sdbr`、`node --check sdbr/web/planner-workbench.js`、`pytest tests/test_api.py -q -k "schedule_result_workspace or buffer or simio or semantic_application_shell" --basetemp .tmp/pytest-ui-business-friendly -p no:cacheprovider` 11 passed、`pytest -q --basetemp .tmp/pytest-full-ui-business-friendly -p no:cacheprovider` 348 passed，1 warning
- 2026-06-24 补充：仿真结果摘要增加“仿真模板”，显示本次验证冻结的 `TemplateID / TemplateVersion`；模板路径、来源类型、时间单位规则和 Desktop 校验状态保留在可展开的技术详情中。
- 用户确认：已确认（2026-06-20）

### 17.12 第十二验收单元记录

- 规格：`UI-OVERVIEW-001`
- 后台依赖：`BE-DATA-014`、`BE-SOLVER-009`、`BE-REL-004`、`BE-RUN-009`
- 状态：用户已确认
- 范围：计划总览显示测试案例验收摘要和 CP-SAT 业务案例分组，作为后续按案例判断产品行为是否符合预期的入口
- 边界：当前只显示测试系统案例验收，不替代生产 BI 总览；生产级总览仍等待 `BE-BI-*`
- 自动化验证：2026-06-20 执行 `python -m compileall -q sdbr`；`pytest tests/test_api.py -q -k "semantic_application_shell or admin_001_002 or plan_publication_governance or case_acceptance_overview or cp_sat_assumptions" --basetemp .tmp/pytest-ui-pending-confirmation-regression -p no:cacheprovider`，5 passed；`pytest -q --basetemp .tmp/pytest-full-ui-pending-confirmation-20260620-final2 -p no:cacheprovider`，305 passed，1 warning
- 浏览器验证：2026-06-20 重建测试库并执行三组 `TST-RUN-*` 后，计划总览显示案例总数 3、已通过 3、待执行 0、未通过 0；案例卡显示 Planning Run、状态、求解器、发布状态、可释放数和阻塞代码；中英文切换正常；390px 窄屏无横向溢出
- 补充验证：2026-06-21 新增六组 `TST-CP-*` CP-SAT 业务案例；案例卡显示案例分组、类型、期望断言、通过断言和差异原因；定向验证 `pytest tests/test_test_data.py -q --basetemp .tmp/pytest-cp-cases-data -p no:cacheprovider`，9 passed；`pytest tests/test_business_closure.py -q --basetemp .tmp/pytest-cp-cases-business -p no:cacheprovider`，9 passed；`pytest tests/test_api.py -q -k "case_acceptance_overview" --basetemp .tmp/pytest-cp-cases-ui -p no:cacheprovider`，1 passed；全量 `pytest -q --basetemp .tmp/pytest-full-cp-business-cases -p no:cacheprovider`，316 passed，1 warning
- 补充验证：2026-06-22 案例卡新增 `ScheduleResultOpenable` 与不可打开原因展示，未完成案例显示“排程未完成”；新增单案例复位和全部案例复位入口；覆盖三组业务闭环案例和六组 `TST-CP-*` 案例，验证 Completed 案例均可打开排程结果、不可行案例返回明确不可打开原因；定向验证 `pytest tests/test_business_closure.py tests/test_api.py -q -k "openable_schedule_results or acceptance_reset or reset_all or case_acceptance_overview or admin_001_002 or cp_sat_business_cases or schedule_result_workspace or ui_calendar" --basetemp .tmp/pytest-case-reset -p no:cacheprovider`，9 passed
- 用户确认：已确认（2026-06-20）

## 18. 变更记录

| 版本 | 日期 | 变更 |
| --- | --- | --- |
| 5.29 | 2026-07-09 | 完成 P1 S-DBR 市场控制 UI 第一轮验证：排程结果页新增只读“市场承诺与约束保护”面板，展示约束计划负荷、MTO 安全承诺、MTA 补货负荷和统一缓冲优先级；状态为已验证待用户确认 |
| 5.28 | 2026-07-09 | 启动 P1 S-DBR 市场控制面板规格：排程结果页后续只读展示 CCR planned load、MTO safe-date、MTA replenishment load 和 unified buffer priority；第一轮为内部执行 read model，不新增 DDAE 协议、不暴露主参数治理或 DDMRP 参数编辑 |
| 5.27 | 2026-07-03 | `UI-SCHEDULE-001` 资源负荷页新增 S-DBR 运行控制摘要：计划负荷、安全日期、释放纪律、稳定性建议和非约束资源保护产能状态；明确非约束资源仅作为监控/候选约束信号，不作为自动硬约束 |
| 5.26 | 2026-07-01 | 将 `公开演示闭环 / Public Demo Loop` 左侧导航项移动到导航列表最下面；不改变公开演示页面内部技术区和底部业务用户演示视图顺序 |
| 5.25 | 2026-07-01 | `UI-DEMO-001` 在公开演示闭环页最下方新增业务用户演示视图，面向业务用户解释 SDBR 的执行/校验/adapter/反馈角色；不新增导航、不改变现有技术区顺序，不声明生产验证或 Business Golden Loop readiness |
| 5.24 | 2026-06-30 | 公开演示闭环页新增 AdventureWorks 排程 Adapter 校验区：显示 adapter profile、bounded fixture 模式、AW-RES 显式资源日历映射、生成行数、formal solver gate，并明确 `MaterialConstraintsMode=OmittedForPublicDemo` 且无物料可行性生产声明 |
| 5.23 | 2026-06-29 | 新增 `UI-DEMO-001`：独立 `公开演示闭环 / Public Demo Loop` 页面，读取 PUBLIC-DEMO-GOLDEN-DATA-V1 frozen package 与 DDAE handoff payload，展示契约校验、reviewed candidate mapping 命中和 SDBR feedback handoff 状态；明确仅为 DemoFixture / ReviewedEvidence / PublicDemoOnly，不声明生产验证 |
| 5.22 | 2026-06-26 | 固化 DDAE / DDS&OP UI 边界：SDBR 页面只展示 DDAE 主设置的来源、版本、冻结状态和执行反馈，不重新计算或审批时间缓冲、控制点、DDMRP 参数、资源角色等主参数；配置不足时提示契约变更或配置补充，不新增隐式 UI 字段 |
| 5.21 | 2026-06-26 | 统一 `UI-CALENDAR-001` 与 `UI-ADMIN-001/002` 字体层级：日历配置与管理后台的标题、卡片、表单、说明文字和列表行收敛到工作台页面的紧凑字号与密度 |
| 5.20 | 2026-06-26 | 收口 `UI-DDOM-001` 中文展示：运营指标页将后端适用范围、不适用范围等英文规范值转换为中文业务表达，避免计划员界面出现英文说明 |
| 5.19 | 2026-06-26 | 新增 `UI-DDOM-001`：独立 `运营指标 / Operational Metrics` 页面，按可靠性、稳定性、速度/流速展示 DDOM 运营指标、偏差反馈建议和数据覆盖缺口；不实现 DDS&OP 配置、历史趋势或财务 KPI |
| 5.18 | 2026-06-26 | 收紧 `UI-DISPATCH-001` 派工建议页字体和卡片密度，使其与缓冲执行页的标题层级、统计栏和资源折叠行保持一致 |
| 5.17 | 2026-06-25 | 将 MES 派工建议从缓冲执行页迁移到独立 `UI-DISPATCH-001` 派工建议页；缓冲执行页只保留约束缓冲矩阵和工单缓冲状态；求解诊断主视图改为业务摘要，技术码默认收起 |
| 5.16 | 2026-06-25 | 新增 `UI-DDMRP-002`：独立 DDMRP 物料计划工作台，按物料-地点展示净流、缓冲百分比、红黄绿优先级、在手/在途/合格需求和只读补货建议；不提供 DDMRP 参数配置或外部订单生成 |
| 5.15 | 2026-06-25 | 新增 DDMRP 运行展示测试数据 `TST-DDMRP-MDV-NET-FLOW-20260625`，数据就绪页可直观看到红/黄/绿/高于绿区解耦点和红/黄区补货建议 |
| 5.14 | 2026-06-25 | 收口 `UI-DDMRP-001` 明细展示：解耦点明细使用“展开/收起”动作替代浏览器默认小三角；DDMRP 版本来源提示降级为辅助文字层级 |
| 5.13 | 2026-06-25 | 新增 `UI-DDMRP-001`：数据就绪中心只读展示 DDMRP 运行状态、解耦点缓冲颜色和补货建议；不提供 DDMRP 参数配置、Buffer Profile 治理或调整因子审批入口 |
| 5.12 | 2026-06-25 | 明确 UI 产品方向为 DDOM 运营执行工作台；DDS&OP 只作为配置来源和反馈对象，不做 DDS&OP 工作流界面；DDMRP 只作为运行链路能力消费已生效参数，不做参数配置、Buffer Profile 治理或调整因子审批 |
| 5.11 | 2026-06-25 | 仿真结果页工单明细改为前端分页、筛选和排序；资源利用率按 80%、90%、100% 阈值显示黄色、红色、黑色风险提示；本轮不改 Simio 解析结构和后端 API |
| 5.10 | 2026-06-24 | 缓冲执行页补充 MES 派工建议包生成、Mock 投递状态、现场到达状态和建议原因展示，作为未来 Direct MES Adapter / UNS Topic 的 UI 验收入口 |
| 5.9 | 2026-06-24 | 排程结果计划治理区调整为业务决策路径展示：发布、输出、释放、仿真、审计按计划流转组织；“上下文”类标题改为业务名称；Simio 技术码、解析来源、模型路径等默认折叠到技术详情；仿真事件状态中文化；缓冲执行 MES 资源队列改为按设备折叠/展开 |
| 5.10 | 2026-06-24 | Simio 模板注册机制在界面体现：管理后台新增“Simio 仿真模板”只读卡片，展示活动模板、版本、时间单位规则和 Desktop 校验状态；排程结果的仿真结果页显示本次验证模板，模型路径和技术字段继续折叠在技术详情 |
| 1.0 | 2026-06-19 | 建立 UI 开发基线规格 |
| 1.1 | 2026-06-19 | 根据 Intuiflow 视频截图补充工单网格、双层负荷视图、缓冲执行看板、甘特缓冲条和后台配置规则 |
| 1.2 | 2026-06-19 | 完成并验证第一验收单元：应用外壳、设计语言和中英文切换 |
| 1.3 | 2026-06-19 | 用户确认第一验收单元，启动 UI-DATA-001 数据就绪中心 |
| 1.4 | 2026-06-19 | 完成并验证第二验收单元 UI-DATA-001 |
| 1.5 | 2026-06-19 | 修正数据问题定位中的未翻译严重度和对象类型枚举 |
| 1.6 | 2026-06-19 | 用户确认第二验收单元，启动 Planning Run 中心 |
| 1.7 | 2026-06-19 | 完成并验证第三验收单元 Planning Run 中心，补齐策略冻结、筛选和生命周期动作 |
| 1.8 | 2026-06-19 | 明确业务词条与技术标识的双语边界，修正数据就绪中心混合语言规则 |
| 1.9 | 2026-06-19 | 用户确认第三验收单元，启动排程结果与方案比较工作区 |
| 2.0 | 2026-06-19 | 完成并验证第四验收单元：排程结果、甘特、负荷、交期、诊断与方案比较 |
| 2.1 | 2026-06-19 | 用户确认第四验收单元，启动已排程工单与释放管理工作区 |
| 2.2 | 2026-06-19 | 完成并验证第五验收单元：已排程工单、审计命令、释放门控、授权和调度包 |
| 2.3 | 2026-06-19 | 用户确认第五验收单元，启动第六验收单元 UI-BUFFER-001 约束缓冲执行看板 |
| 2.4 | 2026-06-19 | 完成并验证第六验收单元：两阶段五区域缓冲看板、工单详情及带原因码的执行事务 |
| 2.5 | 2026-06-19 | 用户确认第六验收单元，启动第七验收单元 UI-EXCEPTION-001 异常与死信中心 |
| 2.6 | 2026-06-19 | 完成并验证第七验收单元：异常中心聚合、筛选、详情、审计历史和双语展示 |
| 2.7 | 2026-06-19 | 用户确认第七验收单元，启动第八验收单元：管理后台 |
| 2.8 | 2026-06-19 | 完成并验证第八验收单元：主数据后台、管理配置聚合、求解器/集成状态和双语展示 |
| 2.9 | 2026-06-19 | 用户确认第八验收单元，启动第九验收单元：通用组件与通用状态质量 |
| 3.2 | 2026-06-19 | 根据求解器决策新增第十验收单元：OR-Tools CP-SAT 成为唯一活动求解器，Gurobi 切换为暂停状态 |
| 3.3 | 2026-06-19 | 完成第十验收单元自动化与运行态验证，状态推进为已验证待用户确认 |
| 3.4 | 2026-06-19 | 根据用户要求在第十单元未确认但继续推进的情况下新增第十一验收单元：排程结果内嵌计划发布治理 |
| 3.5 | 2026-06-19 | 完成第十一验收单元自动化验证：计划发布治理区嵌入排程结果，调用内部发布生命周期 API 并提供双语业务状态 |
| 3.6 | 2026-06-19 | 启动第十二验收单元：测试案例验收总览，用于按案例检查 CP-SAT、释放门控和计划发布治理 |
| 3.7 | 2026-06-19 | 完成第十二验收单元自动化验证：计划总览显示测试案例验收摘要、案例卡片和排程结果跳转入口 |
| 3.8 | 2026-06-20 | 将 Planning Run 列表和创建向导中的“计划问题 / Planning problem”统一调整为“计划场景 / Planning scenario” |
| 3.9 | 2026-06-20 | 第十验收单元补强：管理后台展示 CP-SAT 建模假设、可调参数和延后规则 |
| 4.0 | 2026-06-20 | 处理 UI 第十、十一、十二待确认项：完成测试数据执行、浏览器中英文/窄屏验证、脚本缓存破坏和最终 305 项测试基线 |
| 4.1 | 2026-06-23 | Simio 状态从暂停调整为可选验证可用；排程结果页新增仿真结果页签，支持发起验证并展示可行性、吞吐、队列/WIP、资源利用率、计划偏差和问题清单 |
| 4.2 | 2026-06-24 | 左侧导航增加业务解释悬浮提示：桌面 hover 与键盘 focus 触发，复用现有双语页面说明文案，移动端抽屉不强制显示 |
| 4.1 | 2026-06-20 | 记录 UI-BUFFER-001 测试分支不可达和 UI-ADMIN-001 日历仅只读展示的已知缺口，避免将已完成页面误报为完整业务配置能力 |
| 4.2 | 2026-06-20 | 补齐 UI-BUFFER-001 释放授权到缓冲执行端到端证据；UI-ADMIN-001 新增临时日历覆盖配置入口，基础日历编辑仍保持未完成边界 |
| 4.3 | 2026-06-20 | 用户确认第十、十一、十二验收单元：活动求解器切换、排程结果内嵌计划发布治理、测试案例验收总览 |
| 4.4 | 2026-06-21 | 释放管理补充冻结释放策略版本、策略证据、阻塞触发参数、稳定性判断和调度包策略版本展示 |
| 4.5 | 2026-06-21 | 释放管理“重新评估”改为读取最新运行状态快照，同一计划可刷新门控判断并授权，不要求重建任务包 |
| 4.6 | 2026-06-21 | 管理后台日历说明更新：Active 临时覆盖可驱动新建 Planning Run，基础日历模板与冲突审批仍后续实现 |
| 4.7 | 2026-06-21 | 临时日历覆盖驱动排程通过自动化验证：冻结到 Planning Run、影响 CP-SAT 能力桶和甘特维护条带；全量 315 passed |
| 4.8 | 2026-06-21 | 测试案例验收总览扩展 CP-SAT 业务案例分组，案例卡显示类型、期望断言、通过断言和差异原因 |
| 4.9 | 2026-06-24 | 数据就绪页新增 Mock 运行快照生成入口；创建排程向导新增 OLT、波动程度和产能弹性驱动的时间缓冲计算器 |
| 4.9 | 2026-06-21 | 排程结果页计划治理区补充输出治理摘要：输出包、完整性、释放、审计和外部投递占位均来自后台 read model |
| 5.0 | 2026-06-21 | 管理后台新增基础日历模板和资源日历分配快速配置入口，Active 配置会冻结到 Planning Run 并驱动 CP-SAT |
| 5.1 | 2026-06-21 | 管理后台集成设置补充可替换 Adapter 展示要求，未来同时支持直连 ERP/MES 与 UNS MQTT 路线 |
| 5.2 | 2026-06-21 | 基础日历管理明确资源级范围、管理员/计划员分工、草案/生效/停用状态和冲突优先级展示 |
| 5.3 | 2026-06-21 | 缓冲执行页增加 MES 派工队列验收入口，按资源/工作中心展示正式队列、候选预警、插队冲突和调度员确认提示 |
| 5.4 | 2026-06-21 | 第一版交付边界同步：管理后台显示 Mock API 为活动集成方式，MES 为派工建议模式；Direct ERP/MES 与 UNS 路径后续替换，不在第一版真实连接 |
| 5.5 | 2026-06-22 | 案例验收总览新增排程结果可打开性、不可打开原因、单案例复位和全部复位；管理后台移除日历区块，日历配置统一进入独立页面 |
| 5.6 | 2026-06-22 | 释放管理在运行快照过期时提示同步/生成新快照后重新评估，避免将数据新鲜度问题误表达为重新排程 |
| 5.7 | 2026-06-22 | 释放管理“重新评估”在 Mock 模式下生成新鲜运行快照；排程结果“重新排程”创建源计划重排任务并入队；Planning Run 列表对 Queued 暴露“处理队列”动作 |
| 5.8 | 2026-06-24 | 数据就绪补 Mock 运行快照生成；创建排程向导补时间缓冲计算器和波动/弹性悬浮解释；Simio、释放原因和输出治理增加业务友好反馈格式化 |
| 3.0 | 2026-06-19 | 完成并验证第九验收单元：统一状态标签、表格、详情、确认、通知、加载/空/错和数据新鲜度质量护栏 |
| 3.1 | 2026-06-19 | 用户确认第九验收单元，完成 UI 验收单元基线；将计划总览列入后续产品总览阶段 |
