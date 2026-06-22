# SDBR / DDOM 后台能力规格与完成度台账

| 属性 | 内容 |
| --- | --- |
| 文档版本 | 2.8 |
| 日期 | 2026-06-20 |
| 文档状态 | 待用户审阅后成为后台开发基线 |
| 适用范围 | 完整产品蓝图，包括计划后台、求解器、集成、执行反馈、分析与运维能力 |
| UI 规格 | `docs/ui-specification.md` |
| 后台检查点 | `docs/backend-readiness-2026-06-19.md` |
| 产品参考 | 项目需求、Intuiflow 视频截图及 `interface/interface.md` |

## 1. 文档效力

本文件是后台需求、设计、开发、测试、审计和交接的能力台账。后续后台变更必须引用一个或多个 `BE-*` 规格编号。若新需求无法映射到现有编号，应先修改本文件，再修改代码。

本文件记录两类事实：

1. **目标能力**：完整产品最终需要具备什么。
2. **当前证据**：仓库中已经实现并验证了什么。

“目标存在”不表示“当前已经实现”；“存在接口骨架”也不表示“集成已经可用”。详细能力表是状态判断的唯一依据。

## 2. 状态与证据规则

### 2.1 状态定义

| 标识 | 中文状态 | 使用条件 |
| --- | --- | --- |
| `[VERIFIED]` | 已验证 | 实现存在，且自动化测试或明确运行检查已通过 |
| `[IMPLEMENTED]` | 已实现待验证 | 实现存在，但缺少当前可重复的验收证据 |
| `[PARTIAL]` | 部分实现 | 已有可用基础，但尚未满足完整产品要求 |
| `[NOT-STARTED]` | 未开始 | 尚无可用实现，或仅有需求描述 |
| `[PAUSED]` | 已暂停 | 产品路径保留，但依据项目决定暂不实施 |
| `[EXTERNAL]` | 外部系统边界 | 能力由 ERP、MES、SCADA、身份平台等外部系统负责；本系统只负责契约和集成 |

### 2.2 证据等级

| 标识 | 证据 |
| --- | --- |
| `C` | 代码实现或领域对象 |
| `A` | FastAPI 接口或进程入口 |
| `T` | 自动化测试 |
| `R` | 可重复运行、性能、恢复或人工验收记录 |
| `D` | 只有设计文档或接口占位，不构成实现完成证据 |

### 2.3 状态变更规则

1. `[VERIFIED]` 至少需要 `C/A + T/R` 两类证据。
2. `[PARTIAL]` 必须同时写清“已有能力”和“剩余缺口”。
3. `[PAUSED]` 恢复开发时先改为 `[NOT-STARTED]` 或 `[PARTIAL]`。
4. `[EXTERNAL]` 不得标记为本系统已完成；对应连接器应使用独立 `BE-INT-*` 条目跟踪。
5. 每次状态变更必须更新第 18 节变更记录，并给出测试或运行证据。
6. 测试失败时，不得继续保留受影响条目的 `[VERIFIED]` 状态。

## 3. 产品边界与总体流程

```text
ERP / 主数据源
  -> 主数据版本 + 运行状态快照
  -> Planning Run
  -> OR-Tools CP-SAT（当前活动求解器）
  -> 可选 Simio 验证
  -> 计划输出 / 方案比较 / 人工确认
  -> 绳长 + 物料 + WIP + 缓冲释放门控
  -> MES 执行
  -> 执行事件、偏差与异常
  -> 稳定性判断 / 重排请求 / BI 与流程挖掘
```

系统边界原则：

- ERP 负责订单、BOM、库存、采购在途和基础主数据的权威来源。
- 本系统负责冻结排程输入、有限产能排程、DBR 缓冲与释放决策。
- MES/SCADA 负责现场报工、设备状态和实际产量采集。
- 本系统接收执行事件并形成偏差、预警和重排建议，不替代完整 MES。
- Gurobi 与 OR-Tools 位于同一求解器抽象层；当前只允许 OR-Tools CP-SAT 执行新计划，Gurobi 保留历史结果读取路径但暂停新执行。
- Simio 是可选验证步骤；不验证时求解结果直接进入计划输出，验证时可接受、拒绝或调整计划。

## 4. 主数据与运行状态

| ID | 能力要求 | 状态 | 当前证据 | 缺口与完成条件 |
| --- | --- | --- | --- | --- |
| `BE-DATA-001` | 导入资源及日能力 | `[VERIFIED]` | `C` `sdbr/resource_import.py`; `A` `/resources/import`; `T` `tests/test_resource_import.py` | 已满足当前模型 |
| `BE-DATA-002` | 导入主/备用工艺路线和备用资源 | `[VERIFIED]` | `C` `sdbr/routing_import.py`; `A` `/routings/import`; `T` `tests/test_routing_import.py` | 已满足当前模型 |
| `BE-DATA-003` | 导入排程工单 | `[VERIFIED]` | `C` `sdbr/order_import.py`; `A` `/orders/import`; `T` `tests/test_order_import.py` | 后续由 ERP 连接器自动同步 |
| `BE-DATA-004` | 导入库存缓冲 | `[VERIFIED]` | `C` `sdbr/inventory_import.py`; `A` `/inventory-buffers/import`; `T` `tests/test_inventory_import.py` | 已满足当前模型 |
| `BE-DATA-005` | 导入已分配库存、在途数量与可用时间 | `[VERIFIED]` | `C` `sdbr/material_state.py`; `A` `/material-availability/import`; `T` `tests/test_material_state.py` | 物料批次、替代料和保质期尚属高级能力 |
| `BE-DATA-006` | 导入当前 WIP 与 WIP 上限 | `[VERIFIED]` | `C` `sdbr/material_state.py`; `A` `/wip-limits/import`; `T` `tests/test_material_state.py` | 已满足释放门控基础需求 |
| `BE-DATA-007` | 校验资源、约束、路线、工序、缓冲和物料需求 | `[VERIFIED]` | `C` `sdbr/master_data_validation.py`; `A` `/master-data/validate`; `T` `tests/test_master_data_validation.py` | 后续增加面向 UI 的问题分类与修复建议 |
| `BE-DATA-008` | 创建不可变、可追溯的 Master Data Version | `[VERIFIED]` | `A` `/master-data/versions`; `T` `tests/test_api.py`, `tests/test_backend_readiness.py` | 已满足当前审计需求 |
| `BE-DATA-009` | 创建运行状态快照并判断新鲜度 | `[VERIFIED]` | `C` `sdbr/operational_state.py`; `A` `/operational-state/snapshots`; `T` `tests/test_operational_state.py` | 后续增加资源实时状态字段 |
| `BE-DATA-010` | 柔性日历、班次、节假日和维护扣减 | `[PARTIAL]` | `C` `sdbr/calendar_import.py`, `sdbr/base_calendar.py`, `sdbr/calendar_overrides.py`, `sdbr/calendar_preview.py`, `sdbr/scheduling_solver.py`; `A` 主数据版本比较/发布/回滚、`/planner/workbench/admin/base-calendars`、`/planner/workbench/admin/resource-calendar-assignments`、`/planner/workbench/admin/calendar-overrides`、`/planner/workbench/calendar/preview`; `UI` 管理后台基础日历与临时覆盖配置入口，`UI-CALENDAR-001` 已定义独立日历页面；`T` `tests/test_calendar_import.py`, `tests/test_scheduling_solver.py`, `tests/test_api.py` | 已支持资源级日历、版本化日历输入、基础日历模板、多班次、节假日、资源日历分配、维护扣减、加班/临时覆盖、日历预览事项要素检查、受控主数据发布，以及基础日历和临时覆盖冻结到 Planning Run 并按“维护 > 节假日 > 临时覆盖 > 加班 > 基础班次”驱动 CP-SAT 能力桶；审批流、企业节假日自动同步、完整日历编辑器和节假日强制加班例外规则仍待后续确认 |
| `BE-DATA-011` | 丰富资源属性 | `[PARTIAL]` | `C` `Resource` 已有约束标识、能力、日历、资源数量、效率、类型、缓冲标识、负责人和分类；`T` `tests/test_api.py` | 班组人数、固定偏移和更细换型属性仍需独立业务规则 |
| `BE-DATA-012` | BOM、多级物料需求和替代料模型 | `[PARTIAL]` | `C` `sdbr/light_mrp.py`; `A` `/planner/workbench/light-mrp/evaluate`; `T` `tests/test_material_state.py`, `tests/test_api.py` | 第一版已确认由本系统执行轻量 MRP：按工单物料需求、库存缓冲、已分配库存、在途数量和物料检查窗口输出可用/在途覆盖/短缺/缺库存记录结论；完整 BOM 展开、多级 MRP、替代料、批次/效期分配和 ERP 库存账务仍未实现 |
| `BE-DATA-013` | 主数据版本差异、发布和回滚 | `[VERIFIED]` | `C/A` `/master-data/version-comparison`、`/master-data/versions/{id}/publish|retire|rollback`; `T` `tests/test_api.py` | 已满足后台治理闭环；真实 ERP 主数据发布回写由 `BE-INT-*` 跟踪 |
| `BE-DATA-014` | 版本化测试数据集、场景包与测试库重建 | `[VERIFIED]` | `C` `sdbr/test_data.py`, `sdbr/test_case_acceptance.py`; `D` `docs/cp-sat-business-case-acceptance.md`; `A` `/planner/workbench/test-data/cases`, `/planner/workbench/test-data/acceptance`, `/planner/workbench/test-data/acceptance/{case_id}/decision`, `/planner/workbench/test-data/acceptance/{case_id}/reset`, `/planner/workbench/test-data/acceptance/reset`; CLI `sdbr-reset-test-data --list-cases`; `T` `tests/test_test_data.py`, `tests/test_business_closure.py` | 已提供基准工厂、物料短缺、WIP 超限、CP-SAT 有限产能/备用资源/日历覆盖/效率/换型/不可行诊断案例、测试库重建、单案例/全案例复位、自动验收包、预期/实际差异、排程结果可打开性状态和人工确认/驳回记录；当前场景可驱动 Planning Run 执行、计划输出、释放门控、发布治理与 CP-SAT 业务行为验收 |

## 5. Planning Run 生命周期与任务执行

| ID | 能力要求 | 状态 | 当前证据 | 缺口与完成条件 |
| --- | --- | --- | --- | --- |
| `BE-RUN-001` | Planning Run 固定引用主数据版本和运行快照 | `[VERIFIED]` | `A` `/planning-runs`; `T` `tests/test_api.py`, `tests/test_backend_readiness.py`, `tests/test_business_closure.py` | 已满足 |
| `BE-RUN-002` | 创建、入队、领取、运行、完成、失败和取消生命周期 | `[VERIFIED]` | `C/A` `sdbr/api.py`; `T` `tests/test_api.py`, `tests/test_business_closure.py` | 已满足当前状态机 |
| `BE-RUN-003` | 独立 Worker 领取并执行任务 | `[VERIFIED]` | `C` `sdbr/planning_worker.py`; CLI `sdbr-planning-worker`; `T` `tests/test_planning_worker.py`, `tests/test_business_closure.py` | 生产环境服务安装脚本尚未提供 |
| `BE-RUN-004` | Worker 租约、续租、过期回收与令牌保护 | `[VERIFIED]` | `C/A` claim/renew/execute; `T` `tests/test_api.py`, `tests/test_backend_readiness.py` | 已满足当前部署模型 |
| `BE-RUN-005` | 重试、延迟重试、死信和人工恢复 | `[VERIFIED]` | `A` enqueue/recover; `T` `tests/test_api.py` | 已满足 |
| `BE-RUN-006` | 队列指标、分页查询和运行审计 | `[VERIFIED]` | `A` `/planning-runs`, `/metrics`, `/audit-events`; `T` `tests/test_api.py` | 后续提供 UI 聚合接口 |
| `BE-RUN-007` | 乐观并发和跨实例冲突检测 | `[VERIFIED]` | `C` `sdbr/state_store.py`; `A` `If-Match`; `T/R` `tests/test_backend_readiness.py` | 多节点生产部署应迁移至支持行级事务的数据库 |
| `BE-RUN-008` | 运行幂等键与重复请求去重 | `[PARTIAL]` | `C` 状态机和版本冲突可阻止部分重复写入 | 增加显式 idempotency key、请求摘要和重复响应语义 |
| `BE-RUN-009` | 计划确认、发布和撤销发布生命周期 | `[VERIFIED]` | `C` `sdbr/plan_publication.py`; `A` `/planning-runs/{run_id}/publication/*`; `T` `tests/test_business_closure.py` | 已实现 Draft/Reviewed/Approved/Published/Superseded/PublicationRevoked 状态、权限、审计和非法跳转保护 |

## 6. 求解器接口与排程模型

| ID | 能力要求 | 状态 | 当前证据 | 缺口与完成条件 |
| --- | --- | --- | --- | --- |
| `BE-SOLVER-001` | 统一求解器协议、可用性、输入、结果和诊断 | `[VERIFIED]` | `C` `SchedulingSolver`, `SchedulingProblem`, `SchedulingResult`; `T` `tests/test_scheduling_solver.py` | 已满足扩展基础 |
| `BE-SOLVER-002` | Gurobi 实际建模和求解 | `[PAUSED]` | `C` `GurobiEngine`, `_solve_fixed_resource_gurobi`; `T/R` 既有 Gurobi 小模型测试 | 保留历史结果读取和兼容代码；禁止创建或执行新的 Gurobi 计划，许可证不再作为当前产品运行条件 |
| `BE-SOLVER-003` | 约束资源有限产能 | `[VERIFIED]` | `C` 容量桶和有限资源约束; `T` `tests/test_scheduling_solver.py` | 已满足当前粒度 |
| `BE-SOLVER-004` | 非约束资源按无限产能并保留冲刺能力 | `[VERIFIED]` | `C` `enforce_finite_capacity_on_constraints_only`; `T` `tests/test_scheduling_solver.py` | 后续使冲刺能力比例可配置 |
| `BE-SOLVER-005` | 工序优先关系和最小间隔 | `[VERIFIED]` | `C` `PrecedenceConstraint`; `T` `tests/test_scheduling_solver.py` | 已满足基础路线 |
| `BE-SOLVER-006` | 备用资源选择和惩罚权重 | `[VERIFIED]` | `C` assignment binary variables and objective; `T` `tests/test_scheduling_solver.py` | 已满足当前模型 |
| `BE-SOLVER-007` | 交期、保护交期、最早释放和优先级输入 | `[PARTIAL]` | `C` `SchedulingOrderInput` 已包含字段，目标包含迟期和完工期；`T` `tests/test_api.py` 策略绳长驱动 Planning Run 建议释放时间 | 统一定义保护交期与时间缓冲的目标函数、硬约束和软惩罚语义 |
| `BE-SOLVER-008` | 求解时间限制和结构化诊断 | `[VERIFIED]` | `C` `solver_time_limit_seconds`, `SolverDiagnostic`; `T` `tests/test_scheduling_solver.py` | 后续增加 MIP gap、节点数和中断原因 |
| `BE-SOLVER-009` | OR-Tools CP-SAT 活动求解器 | `[VERIFIED]` | `C` `sdbr/cp_sat_solver.py`, `OrToolsEngine`; `T` `tests/test_scheduling_solver.py`, `tests/test_api.py`, `tests/test_business_closure.py`; `R` 三组持久化测试场景与六组 `TST-CP-*` 业务案例 | 已实现有限产能、优先关系、备用资源、能力桶、保护交期目标、时间限制和结构化诊断，并成为唯一活动求解器 |
| `BE-SOLVER-010` | 顺序相关换型与产品族切换 | `[PARTIAL]` | `C` `SetupTransition`、CP-SAT 单机有限资源换型顺序约束；`T` `tests/test_scheduling_solver.py`, `tests/test_business_closure.py` | 已实现单机有限资源换型矩阵和非对称换型排序，并通过 `TST-CP-SETUP-SEQUENCE` 业务案例验证换型间隔；多并行资源换型、清洗规则和机台级族切换仍未实现 |
| `BE-SOLVER-011` | 资源数量、效率、班组人数和固定偏移约束 | `[PARTIAL]` | `C` `capacity_units`、`efficiency_percent`、工序时间窗、临时日历覆盖能力桶；`T` `tests/test_scheduling_solver.py`, `tests/test_api.py`, `tests/test_business_closure.py` | 已实现资源并行数量、效率修正、工序 earliest/latest 时间窗和 Active 日历覆盖驱动 CP-SAT，并通过 `TST-CP-CALENDAR-OVERTIME`、`TST-CP-RESOURCE-EFFICIENCY` 和 `TST-CP-INFEASIBLE-WINDOW` 验证；班组人数和固定偏移仍需独立业务规则 |
| `BE-SOLVER-012` | 工单锁定、冻结区和人工固定安排 | `[PARTIAL]` | `C` `FixedOperationAssignment`、CP-SAT 固定开始/固定资源硬约束、显式 `SourceRunID`、重排来源追踪和工序差异摘要；`T` `tests/test_scheduling_solver.py`、`tests/test_api.py` | 已完成工序级固定开始/资源、锁定工单、冻结窗口、Planning Run 显式源计划选择和重排差异输出；锁定范围细分到工序/资源/订单的交互策略仍需 UI/业务规则确认 |
| `BE-SOLVER-013` | 批次、合批、拆批和订单分组 | `[NOT-STARTED]` | `D` `administration_view.py` 已暴露批次字段和策略分组占位 | 暂不硬编码；需先定义合批粒度、拆批条件、批量容量和订单混批限制 |
| `BE-SOLVER-014` | 多目标策略和配置化权重 | `[PARTIAL]` | `C` `strategy_id`、`ObjectiveStrategyID`、内置策略权重、版本化策略台账、自定义权重驱动 CP-SAT；`A` `/planner/workbench/admin/scheduling-strategies`, `/planner/workbench/admin/cp-sat/assumptions`; `T` `tests/test_scheduling_solver.py`, `tests/test_api.py`, `tests/test_business_closure.py` | 第一版默认策略为 `v1_delivery_flow_bottleneck`：交期优先、流动时间第二、瓶颈/备用资源保护第三；已实现内置策略、自定义策略权重持久化、自定义策略驱动 CP-SAT、算法假设/可调参数说明接口，并在 `TST-CP-*` 业务案例中输出可解释断言；策略仿真解释和 UI 调参仍需后续完成 |
| `BE-SOLVER-015` | 大规模性能基线与许可证容量治理 | `[NOT-STARTED]` | `D` 已记录 `CORES=256` 议题 | 与 OR-Tools/Simio 阶段共同建立规模矩阵、硬件/许可检查和降级策略 |

### 6.1 当前 CP-SAT 建模假设

以下假设是当前通用排程基线，用户已于 2026-06-20 认可。它们不代表所有工厂的最终业务规则；未来面向具体业务时，应通过案例逐项确认并定制，不在当前阶段提前硬编码。

1. 排程时间采用整数分钟精度。
2. 并行资源按同质容量池建模，不区分池内具体机台。
3. 工序必须完整落在一个能力桶内，当前不跨班次连续加工。
4. 约束资源采用有限产能；非约束资源默认采用无限产能并保留冲刺能力语义。
5. 资源效率通过 `ceil(标准工时 * 100 / 效率百分比)` 修正工序时长。
6. 时间缓冲当前主要通过保护交期参与迟期目标，不等同于完整 DBR 数学模型。
7. 物料齐套、在途、轻量 MRP、WIP 和绳长释放继续由释放门控/物料评估层判断，不作为当前 CP-SAT 硬约束。
8. 第一版默认优化偏好为交期优先、流动时间第二、瓶颈/备用资源保护第三；策略权重仍需按具体业务验证。
9. 单机有限资源支持顺序相关换型；多并行资源的机台级换型等待具体业务规则。
10. 完整 BOM 展开、多级 MRP、替代料、批次、合批、拆批、班组人数及 Simio 反馈不属于当前通用模型。

### 6.2 当前可调参数边界

当前阶段允许配置并可追溯的 CP-SAT 参数如下。未列入的参数不得在 UI 或 API 中暗示为已支持。

| 参数类别 | API 字段/对象 | 当前作用 | 边界 |
| --- | --- | --- | --- |
| 求解器选择 | `SolverBackendID` | 新任务只允许 `ortools` | Gurobi 暂停，Simio 不参与求解 |
| 求解时间限制 | `TimeLimitSeconds` / `solver_time_limit_seconds` | 传入 CP-SAT `max_time_in_seconds` | 不保证最优，只保证状态结构化 |
| 目标策略 | `ObjectiveStrategyID` | 选择内置策略或后台自定义策略 | 自定义策略需先在策略台账创建 |
| 目标权重 | `/admin/scheduling-strategies` 的 `TardinessWeight`、`MakespanWeight`、`AlternateResourcePenaltyWeight` | 直接形成 CP-SAT 加权目标 | 权重解释需通过业务案例校准 |
| 时间缓冲 | `TimeBufferMinutes`、释放策略时间缓冲比例 | 当前用于保护交期/释放门控语义 | 不作为完整 DBR 数学硬约束 |
| 资源效率/并行数 | `EfficiencyPercent`、`CapacityUnits` | 修正工时和并行容量 | 多机台顺序换型仍未支持 |
| 工序时间窗 | `EarliestStartAt`、`LatestEndAt` | CP-SAT 硬约束 | 业务含义由上游或人工配置给出 |
| 换型矩阵 | `SetupTransitions` | 单机有限资源顺序换型硬约束 | 多并行资源换型后续建模 |
| 释放策略 | `/dbr/release-policies` | 冻结并驱动建议释放时间、释放门控、缓冲颜色、WIP 采用上限、物料检查窗口和稳定性动作 | 不反向作为 CP-SAT 物料/WIP 硬约束；批次/MRP 仍待业务规则 |

## 7. DBR 缓冲、释放与稳定性

| ID | 能力要求 | 状态 | 当前证据 | 缺口与完成条件 |
| --- | --- | --- | --- | --- |
| `BE-REL-001` | 计算绳长和建议释放时间 | `[VERIFIED]` | `C` `calculate_suggested_release_date`, `release_candidates.py`; `T` `tests/test_planner_workbench.py`, `tests/test_release_candidates.py` | 已满足基础 DBR |
| `BE-REL-002` | 物料可用性和在途到达门控 | `[VERIFIED]` | `C` `release_candidates.py`; `T` `tests/test_release_candidates.py` | 高级替代料和批次分配未纳入 |
| `BE-REL-003` | WIP 上限门控 | `[VERIFIED]` | `C` `WipLimit`; `T` `tests/test_release_candidates.py` | 已满足基础需求 |
| `BE-REL-004` | 合并绳长、物料、WIP 和库存风险形成候选 | `[VERIFIED]` | `C/A` release candidate endpoints; `T` `tests/test_api.py`, `tests/test_release_candidates.py`, `tests/test_business_closure.py` | 已满足；测试数据验证释放门控消费 Completed Planning Run 的冻结排程结果 |
| `BE-REL-005` | 授权、派发包和结构化阻塞原因 | `[VERIFIED]` | `C` `release_authorization.py`; `A` release authorization endpoints; `T` `tests/test_release_authorization.py`, `tests/test_business_closure.py` | 已满足当前接口边界；物料短缺与 WIP 超限输出结构化阻塞原因 |
| `BE-REL-006` | 决策包、执行追踪和偏差分析 | `[VERIFIED]` | `C` `release_decision_package.py`, `shop_floor_execution.py`; `A` package trace/variance endpoints; `T` `tests/test_api.py` | 已满足基础闭环 |
| `BE-REL-007` | 稳定性策略抑制频繁放行/重排波动 | `[VERIFIED]` | `C` `release_stability.py`, `release_policy.py`; `T` `tests/test_release_stability.py`, `tests/test_api.py` | 已由版本化释放策略驱动释放管理稳定性动作；后续按业务案例校准阈值 |
| `BE-REL-008` | 偏差触发重排请求并支持人工决策 | `[VERIFIED]` | `C` `replanning.py`; `A` replan endpoints; `T` `tests/test_replanning.py`, `tests/test_api.py` | 已满足 |
| `BE-REL-009` | 时间缓冲红黄绿计算 | `[VERIFIED]` | `C` `planner_view.py`, `work_order_release_view.py`; `T` `tests/test_planner_view.py`, `tests/test_api.py` | Planning Run 释放管理已按冻结释放策略比例计算红黄绿；Buffer Board 更复杂优先级仍由 BE-REL-011 跟踪 |
| `BE-REL-010` | 两阶段五区域 Buffer Board 聚合 | `[VERIFIED]` | `C` `sdbr/buffer_execution_view.py`; `A` Buffer Board workbench/detail endpoints; `T` `tests/test_api.py` | 已按 Planning Run 聚合授权、冻结计划和执行事件；更复杂的优先级由 BE-REL-011 承担 |
| `BE-REL-011` | 配置化执行优先级矩阵 | `[PARTIAL]` | `C` `sdbr/dispatch_priority.py`; `A` `/planner/workbench/dispatch-priority/runs/{run_id}/workbench`; `T` `tests/test_dispatch_priority.py`, `tests/test_api.py` | 第一版 MES 派工优先级已按“已授权释放、红黄绿、渗透率、约束资源计划开始、客户交期”输出资源/工作中心 + 工序级队列；MTS、Min-Max、MTO 独立策略及 Stockout/Critical/OTOG 等权重仍后续配置化 |
| `BE-REL-012` | 版本化 DBR 与释放策略中心 | `[VERIFIED]` | `C/A` `/dbr/release-policies` 列表/创建/查询、Planning Run 冻结 `ReleasePolicyVersionID` 和策略快照、释放推荐/门控/授权证据消费策略、管理后台配置摘要；`T` `tests/test_api.py` | 已实现绳长、缓冲比例、策略 WIP 上限、物料检查窗口和稳定性阈值驱动当前释放算法；后续只做业务校准、编辑 UI 和审批流程 |

## 8. 计划输出、负载与方案比较

| ID | 能力要求 | 状态 | 当前证据 | 缺口与完成条件 |
| --- | --- | --- | --- | --- |
| `BE-OUT-001` | 输出工序级和工单级计划 | `[VERIFIED]` | `C` `sdbr/schedule_output.py`; `A` scheduled work-order/order endpoints; `T` `tests/test_schedule_output.py`, `tests/test_business_closure.py` | 已满足基础结果输出 |
| `BE-OUT-002` | 资源甘特数据 | `[PARTIAL]` | `C` `sdbr/gantt_view.py`, `sdbr/schedule_result_view.py`; `T` `tests/test_gantt_view.py`, `tests/test_business_closure.py`, `tests/test_api.py` | 已由测试 Planning Run 验证甘特 read model，并按冻结释放策略绳长展示时间缓冲长度；前端排程结果页补充 `资源占用图` 与 `工单流程图` 双视图，支持按资源确认维护/不可用窗口、按工单确认工序流转；更完整计划/实际对比仍待 MES 执行数据 |
| `BE-OUT-003` | 系统级负载图 | `[PARTIAL]` | `C` `LoadGraphRow`, `planner_view.py`, `schedule_result_view.py`; `T` `tests/test_planner_view.py`, `tests/test_business_closure.py`, `tests/test_api.py` | 已由测试 Planning Run 验证负载 read model；本阶段补内部输出包资源负荷摘要；跨资源排名、可配置时间范围和负责人/类型/分类筛选仍后续完善 |
| `BE-OUT-004` | 单资源逐日负载图 | `[PARTIAL]` | `C` 已有日能力、需求和超载单元格 | 增加 Available/Released/Unreleased/Completed/Remaining 分层 |
| `BE-OUT-005` | 非约束资源瓶颈候选识别 | `[VERIFIED]` | `C` `build_bottleneck_candidates`; `T` `tests/test_planner_view.py` | 后续阈值配置化 |
| `BE-OUT-006` | 产能缓冲和库存缓冲看板 | `[VERIFIED]` | `C` `build_capacity_buffer_board`, `build_inventory_buffer_board`; `T` `tests/test_planner_view.py` | UI 聚合仍需完善 |
| `BE-OUT-007` | 排程方案比较与推荐 | `[VERIFIED]` | `C` `sdbr/scenario_comparison.py`; `A` `/scenarios/compare`; `T` `tests/test_api.py` | 后续支持持久化方案集和人工选择理由 |
| `BE-OUT-008` | 已排程工单统一查询与批量命令 | `[VERIFIED]` | `C` `sdbr/work_order_release_view.py`; `A` Planning Run work-order workbench/commands；`T` `tests/test_api.py`, `tests/test_business_closure.py` | 已提供统一工单 read model，以及锁定/解锁/优先级审计命令；本阶段补输出治理上下文；释放强制进入 BE-UI-004 |
| `BE-OUT-009` | 工单详情聚合 | `[VERIFIED]` | `C/A` 已组合工序、交期、路线、释放、计划、生产/销售、备注、UDF 和审计上下文；`T` `tests/test_api.py` | 已满足当前计划员详情审计需求；本阶段补 OutputContext、ReleaseContext 和 AuditContext；更深 ERP/MES 字段由集成阶段补充 |
| `BE-OUT-010` | 计划发布文件/API 契约 | `[VERIFIED]` | `C` `sdbr/plan_publication.py`; `A` `/planning-runs/{run_id}/publication`; `T` `tests/test_business_closure.py` | 已定义内部版本化计划发布包、状态查询、发布、撤销、替代和审计；本阶段补内部输出治理包和稳定读取契约；真实 ERP/MES 回写仍由 `BE-INT-*` 跟踪 |

## 9. 执行反馈与异常

| ID | 能力要求 | 状态 | 当前证据 | 缺口与完成条件 |
| --- | --- | --- | --- | --- |
| `BE-EXEC-001` | 接收现场执行事件 | `[VERIFIED]` | `C` `shop_floor_execution.py`; `A` `/shop-floor/execution/event`; `T` `tests/test_shop_floor_execution.py` | 当前是集成契约，不是完整 MES 终端 |
| `BE-EXEC-002` | 到达缓冲、开始、完成和状态汇总 | `[VERIFIED]` | `C/A` execution status endpoints; `T` `tests/test_shop_floor_execution.py`, `tests/test_api.py` | 已满足基础反馈 |
| `BE-EXEC-003` | 迟到事件强制异常原因码 | `[VERIFIED]` | `C` `validate_execution_event`, default exception catalog; `T` `tests/test_shop_floor_execution.py` | 原因码目录和必填区域需配置化 |
| `BE-EXEC-004` | 按数量、百分比、工时和最后一批报工 | `[PARTIAL]` | `C/A` Buffer Board 事务支持 Quantity、CompletionPercent、Hours 并记录 Actor/原因码；`T` `tests/test_api.py` | 最后一批语义、MES 对账和幂等接入契约仍未实现；完整报工优先由 MES 承担 |
| `BE-EXEC-005` | 计划与实际偏差、授权预警 | `[VERIFIED]` | `C` variance/stability/alerts builders; `A` authorized alerts; `T` `tests/test_shop_floor_execution.py` | 已满足基础闭环 |
| `BE-EXEC-006` | 完整操作员终端、扫码和设备采集 | `[EXTERNAL]` | MES/SCADA 责任 | 本系统只维护事件契约、幂等和确认回执 |

## 10. ERP、MES 与外部集成

| ID | 能力要求 | 状态 | 当前证据 | 缺口与完成条件 |
| --- | --- | --- | --- | --- |
| `BE-INT-001` | ERP 入站连接器 | `[PARTIAL]` | `C` `sdbr/integration_contracts.py`; `A` `/planner/workbench/integrations/contracts`, `/planner/workbench/integrations/mock-api/status`, `/planner/workbench/integrations/messages`; `T` `tests/test_integration_contracts.py` | 第一版采用 Mock API 作为活动适配器；已定义 ERP 入站契约、字段校验、幂等键、确认、死信和重放测试桩；未来通过可替换 Adapter 接入直连 ERP 或 UNS Topic；真实 ERP 增量同步、映射适配、重试调度和对账仍未实现 |
| `BE-INT-002` | ERP 出站计划与释放回写 | `[PARTIAL]` | `C` `sdbr/integration_contracts.py`; `A` `/planner/workbench/integrations/contracts`, `/planner/workbench/integrations/mock-api/status`, `/planner/workbench/integrations/messages`; `T` `tests/test_integration_contracts.py` | 第一版采用 Mock API，不真实回写 ERP；已定义确认计划、建议释放、实际释放和异常状态的出站契约及确认/重放边界；未来通过可替换 Adapter 接入直连 ERP 或 UNS Topic；真实 ERP 回写连接器、投递队列和回执对账仍未实现 |
| `BE-INT-003` | ERP 业务所有权 | `[EXTERNAL]` | ERP 是权威来源 | 本系统不替代 ERP 主数据、采购和库存账务 |
| `BE-INT-004` | MES 入站执行事件连接器 | `[PARTIAL]` | `C/A` 通用执行事件接口、`sdbr/integration_contracts.py` MES 入站契约和消息测试桩；`T` `tests/test_integration_contracts.py`, `tests/test_shop_floor_execution.py` | 第一版采用 Mock API 接收测试/验收事件；已补幂等键、来源系统、字段校验、死信、重放契约，以及 DispatchAccepted、StartedOperation、CompletedOperation、DispatchRejected、ExceptionReported 第一版回执类型；真实 MES 适配、重放执行和对账仍未实现 |
| `BE-INT-005` | MES 出站派工与释放接口 | `[PARTIAL]` | `C/A` dispatch package、`sdbr/dispatch_priority.py`、`sdbr/integration_contracts.py` MES 出站契约；`A` `/planner/workbench/dispatch-priority/runs/{run_id}/workbench`, `/planner/workbench/integrations/mock-api/status`; `T` `tests/test_integration_contracts.py`, `tests/test_release_authorization.py`, `tests/test_dispatch_priority.py`, `tests/test_api.py` | 第一版只生成 MES 派工建议，不真实下发 MES；已定义版本化派工/释放消息、资源/工作中心 + 工序级派工队列、确认回执、撤销和重发边界；真实 MES 投递、确认回执和重发队列仍未实现 |
| `BE-INT-006` | MES/SCADA 业务所有权 | `[EXTERNAL]` | MES/SCADA 负责现场采集和控制 | 本系统消费状态，不直接控制设备 |
| `BE-INT-007` | 通用集成监控 | `[PARTIAL]` | `C/A` 集成消息台账、死信查询和重放请求接口；`T` `tests/test_integration_contracts.py` | 已提供契约层错误队列和人工重放占位；连接状态、延迟、最后成功时间、自动重试和外部系统健康检查仍未实现 |

### 10.1 可替换集成架构原则

后续 ERP/MES 集成不得把 SDBR 核心业务绑定到某一种外部技术路线。SDBR 核心只处理统一业务消息（Canonical Message），外部系统接入必须通过可替换 Adapter 完成。

目标架构：

```text
SDBR Core Planning / Release / Dispatch
  -> Integration Port
  -> Adapter
     -> Direct ERP/MES API 或数据库/文件
     -> UNS MQTT Topic
     -> Mock/Test Adapter
```

Canonical Message 必须包含：

- `MessageID`
- `MessageType`
- `SchemaVersion`
- `SourceSystem`
- `BusinessID`
- `Revision`
- `OccurredAt`
- `IdempotencyKey`
- `Payload`

第一版消息类型至少覆盖：

- ERP 入站：`WorkOrderImported`、`RoutingImported`、`ResourceImported`、`MaterialRequirementImported`、`InventorySnapshotImported`
- ERP 出站：`SchedulePublished`、`ReleaseAuthorized`、`PlanningExceptionReported`
- MES 出站：`DispatchQueueIssued`、`ReleaseInstructionIssued`、`DispatchRevoked`
- MES 入站：`DispatchAccepted`、`StartedOperation`、`CompletedOperation`、`DispatchRejected`、`ExceptionReported`

Adapter 策略：

- `DirectAdapter`：用于未来直连 ERP/MES REST、数据库中间表、文件或消息队列。
- `UnsMqttAdapter`：用于未来接入 EMQX/UNS，Topic 由工厂、车间、产线、工作中心和事件类型组成。
- `MockAdapter`：用于测试数据、案例验收和离线演示。

UNS Topic 命名建议：

```text
SDBR/{Plant}/{Area}/{Line}/{WorkCenter}/Dispatch/QueueIssued
SDBR/{Plant}/{Area}/{Line}/{WorkCenter}/Dispatch/ReleaseAuthorized
SDBR/{Plant}/{Area}/{Line}/{WorkCenter}/Schedule/Published
source/erp/{Plant}/Orders/WorkOrderImported
source/erp/{Plant}/Materials/InventorySnapshot
source/mes/{Plant}/{Area}/{Line}/{WorkCenter}/Execution/StartedOperation
source/mes/{Plant}/{Area}/{Line}/{WorkCenter}/Execution/CompletedOperation
source/mes/{Plant}/{Area}/{Line}/{WorkCenter}/Execution/ExceptionReported
```

设计约束：

- SDBR 核心业务模块不得直接调用 ERP/MES/EMQX/Node-RED/IoTDB SDK。
- Direct 与 UNS 只允许出现在 Adapter 层。
- 消息台账、幂等、确认回执、死信、人工重放和审计必须在 Integration Port 层统一处理。
- Adapter 切换不得改变 Planning Run、释放门控、派工优先级和发布治理的核心业务代码。

## 11. Simio 验证

| ID | 能力要求 | 状态 | 当前证据 | 缺口与完成条件 |
| --- | --- | --- | --- | --- |
| `BE-SIM-001` | 导出求解问题或计划到 Simio 契约 | `[PAUSED]` | `D` `SimioValidationAdapter` 和 `/simio/export` 仅提供基础导出 | 项目恢复后冻结交换模型并完成契约测试 |
| `BE-SIM-002` | 提交仿真任务并跟踪生命周期 | `[PAUSED]` | 无 | 定义提交、运行、超时、取消和失败恢复 |
| `BE-SIM-003` | 接收验证结果、风险与调整建议 | `[PAUSED]` | 无 | 定义可行性、吞吐、队列、在制品和瓶颈反馈 |
| `BE-SIM-004` | 可选验证路径 | `[PARTIAL]` | `D` 产品路径和适配器边界已定义 | 实现“直接输出”和“经 Simio 验证后输出”的统一 Planning Run 状态流 |

## 12. BI 与流程挖掘

| ID | 能力要求 | 状态 | 当前证据 | 缺口与完成条件 |
| --- | --- | --- | --- | --- |
| `BE-BI-001` | 计划总览聚合 API | `[NOT-STARTED]` | 数据散布于队列、负载、缓冲、异常接口 | 提供队列、准时率、约束风险、缓冲摘要和最近操作 read model |
| `BE-BI-002` | 交期、吞吐、WIP、缓冲和稳定性指标 | `[PARTIAL]` | 已有局部摘要、偏差和稳定性数据 | 定义指标口径、时间维度和历史存储 |
| `BE-BI-003` | 流程转移与返工统计 | `[PARTIAL]` | `C` `_process_transitions` 和返工识别 | 将私有统计提升为稳定分析契约并补充过滤维度 |
| `BE-BI-004` | 完整流程拓扑挖掘 | `[NOT-STARTED]` | 无图模型和历史事件仓库 | 输出节点、边、频次、耗时、返工环及筛选 API；可由外部 BI 展示 |
| `BE-BI-005` | 自助 BI 报表设计器 | `[EXTERNAL]` | Power BI 等外部工具责任 | 本系统提供受治理的数据集和嵌入入口 |

## 13. 安全、审计、持久化与运维

| ID | 能力要求 | 状态 | 当前证据 | 缺口与完成条件 |
| --- | --- | --- | --- | --- |
| `BE-OPS-001` | Viewer/Planner/Worker/Admin RBAC | `[VERIFIED]` | `C/A` FastAPI 授权; `T` `tests/test_api.py` | 当前本地环境可关闭鉴权 |
| `BE-OPS-002` | 业务操作审计 | `[VERIFIED]` | `C/A` audit events; `T/R` `tests/test_api.py`, `tests/test_backend_readiness.py` | 扩展到配置、发布、人工调整和集成重放 |
| `BE-OPS-003` | SQLite 持久化、备份与损坏恢复 | `[VERIFIED]` | `C` `SQLiteWorkbenchStateStore`; `T/R` `tests/test_state_store.py`, `tests/test_backend_readiness.py` | 当前适合单服务开发部署 |
| `BE-OPS-004` | 生产级关系数据库与迁移 | `[NOT-STARTED]` | 无 | 多节点部署前迁移到支持事务和行级锁的数据库，并建立 schema migration |
| `BE-OPS-005` | 身份提供商、登录和令牌生命周期 | `[NOT-STARTED]` | 仅有请求头角色校验基础 | 接入企业 IdP/OIDC，完成登录、会话、登出和服务账户 |
| `BE-OPS-006` | 健康检查和状态存储检查 | `[PARTIAL]` | `A` `/state-store/health`; `T` `tests/test_state_store.py` | 增加求解器、Worker、数据库、ERP、MES、Simio 分项 readiness/liveness |
| `BE-OPS-007` | 结构化日志、指标和追踪 | `[NOT-STARTED]` | 无统一可观测性管线 | 增加 correlation ID、结构化日志、Prometheus 指标和分布式追踪 |
| `BE-OPS-008` | Worker 服务化、部署和滚动升级 | `[PARTIAL]` | 独立 Worker 进程已实现 | 增加 Windows 服务/容器部署、优雅停机、容量配置和运行手册 |
| `BE-OPS-009` | API 版本化和兼容策略 | `[NOT-STARTED]` | 当前端点未使用显式 `/v1` | 发布外部集成前定义版本、弃用和兼容测试 |
| `BE-OPS-010` | 性能与容量基线 | `[PARTIAL]` | `R` 1,000 Planning Runs 查询基线见后台检查点 | 增加求解规模、并发 Worker、数据库、集成吞吐和长时间稳定性测试 |
| `BE-OPS-011` | 测试/生产运行环境隔离 | `[VERIFIED]` | `C` `sdbr/runtime_environment.py`; `A` `/planner/workbench/environment`; `T` `tests/test_runtime_environment.py`, `tests/test_test_data.py` | 已隔离测试/生产 SQLite 路径，API 返回环境元数据并拒绝生产环境测试数据重建；生产级数据库仍由 `BE-OPS-004` 跟踪 |

## 14. UI 支撑 API

| ID | 能力要求 | 状态 | 当前证据 | 缺口与完成条件 |
| --- | --- | --- | --- | --- |
| `BE-UI-001` | 数据就绪聚合接口 | `[VERIFIED]` | `C` `sdbr/data_readiness.py`; `A` `GET /planner/workbench/data-readiness`; `T` `tests/test_api.py` | 已输出安全摘要、数量、新鲜度、结构化问题和排程输入可用性，不返回原始主数据数组 |
| `BE-UI-002` | Planning Run 工作台接口 | `[VERIFIED]` | `C` `sdbr/planning_run_view.py`; `A` Planning Run 工作台列表/详情与生命周期接口；`T` `tests/test_api.py` | 已提供安全列表/详情 read model、允许动作、能力状态和冻结策略参数 |
| `BE-UI-003` | 排程结果聚合接口 | `[VERIFIED]` | `C` `sdbr/schedule_result_view.py`; `A` `/schedule-results/runs/{run_id}/workbench`, `/compare`, `/select`; `T` `tests/test_api.py` | 已按 Planning Run 返回安全 KPI、诊断、甘特、系统/单资源负荷、风险和筛选元数据，并支持方案比较与审计选择 |
| `BE-UI-004` | 释放管理聚合接口 | `[VERIFIED]` | `C` `sdbr/work_order_release_view.py`; `A` Planning Run release-management workbench/authorize 支持冻结快照与最新运行快照重新评估；`T` `tests/test_api.py`, `tests/test_business_closure.py` | 已桥接冻结计划、主数据和运行快照，输出优先级、动态缓冲渗透、结构化阻塞原因、允许动作及调度包引用；同一已完成计划可用最新运行状态快照重新评估释放门控，不要求重新建 Planning Run |
| `BE-UI-005` | 异常中心聚合接口 | `[VERIFIED]` | `C` `sdbr/exception_center_view.py`; `A` exception center workbench/detail endpoints; `T` `tests/test_api.py` | 已统一 Planning Run 失败/DeadLetter、约束缓冲风险、执行预警和重排建议；后续可继续丰富释放阻塞处置动作和关闭工作流 |
| `BE-UI-006` | 管理配置 API | `[PARTIAL]` | `C/A` `/planner/workbench/administration/workbench` 输出主数据对象、日历配置摘要、释放策略配置、求解器策略、集成契约、Worker/SQLite 状态，并聚合日历覆盖、自定义排程策略和释放策略驱动状态；`T` `tests/test_api.py` | 已提供安全管理工作台、半配置化入口摘要、日历覆盖 API、策略权重 API 和释放策略驱动状态；敏感连接参数编辑、配置审批、配置编辑 UI 和真实外部系统健康配置后续实现 |
| `BE-UI-007` | 保存视图、筛选和用户偏好 | `[NOT-STARTED]` | 无 | 保存列、排序、分组、筛选、语言和页面偏好 |
| `BE-UI-008` | 双语消息码和字段词典 | `[NOT-STARTED]` | API 多为英文文本 | 返回稳定 message code，由 UI 负责中英文展示，保留技术详情 |

## 15. 开发优先级与实施阶段

### 15.1 UI 外壳可立即开始

`UI-SHELL-001`、`UI-DS-001` 和 `UI-I18N-001` 不依赖新增排程能力，可以按 UI Spec 开发。

### 15.2 对应页面开发前必须补齐

| 优先级 | 后台规格 | 原因 |
| --- | --- | --- |
| P0 | `BE-UI-001` 至 `BE-UI-005` | 避免 UI 直接拼接内部对象或展示原始 JSON |
| P0 | `BE-DATA-011`, `BE-REL-010`, `BE-REL-011`, `BE-REL-012` | 资源、缓冲板和优先级是核心业务表达 |
| P0 | `BE-OUT-002` 至 `BE-OUT-004`, `BE-OUT-008`, `BE-OUT-009` | 支撑甘特、负载、工单网格和详情页 |
| P1 | `BE-DATA-010`, `BE-SOLVER-010` 至 `BE-SOLVER-014` | 提升高级排程可执行性和人工控制 |
| P1 | `BE-RUN-009`, `BE-OUT-010` | 建立确认、发布和撤销的正式业务闭环 |
| P1 | `BE-OPS-005` 至 `BE-OPS-009` | 上线前安全、运维和接口治理 |
| P2 | `BE-INT-*`, `BE-BI-*` | ERP/MES 接入和管理分析阶段 |
| 当前迁移 | `BE-SOLVER-009` | CP-SAT 成为唯一活动求解器并完成 Gurobi 约束等价迁移 |
| 暂停 | `BE-SOLVER-002`, `BE-SIM-*` | Gurobi 暂停新执行；Simio 按项目决定延后 |

### 15.3 推荐开发顺序

1. UI 应用外壳。
2. 后台策略配置模型与管理 API。
3. 数据就绪和 Planning Run 聚合 API。
4. 丰富资源、日历和缓冲板模型。
5. 计划工单、详情、负载和甘特聚合 API。
6. 完成 CP-SAT 等价迁移后，继续计划锁定、换型、冻结区和高级 CP-SAT 约束。
7. 计划确认、发布及 ERP/MES 契约。
8. 可观测性、生产数据库、身份与部署。
9. BI、流程挖掘和 Simio 后续阶段；Gurobi 保留为暂停兼容路径。

## 16. 审计与验收模板

每项能力完成后按以下格式记录：

```markdown
### BE-{DOMAIN}-{NNN} 验收记录

- 状态变更：`[PARTIAL]` -> `[VERIFIED]`
- 日期：YYYY-MM-DD
- 实现证据：`path/to/module.py`、`METHOD /api/path`
- 测试证据：`pytest tests/test_module.py -q`，N passed
- 业务验收：输入、动作、预期结果
- 已知限制：无，或列出仍保留的边界
- 用户确认：待确认 / 已确认（YYYY-MM-DD）
```

后台功能开发完成但尚未取得用户确认时，可以标记 `[VERIFIED]`，但验收记录中的“用户确认”必须保留为“待确认”。技术验证与产品验收不可混为一项。

### BE-REL-010 / BE-EXEC-004 验收记录

- 状态变更：`BE-REL-010 [PARTIAL]` -> `[VERIFIED]`；`BE-EXEC-004 [NOT-STARTED]` -> `[PARTIAL]`
- 日期：2026-06-19
- 实现证据：`sdbr/buffer_execution_view.py`、`GET /planner/workbench/buffer-board/runs/{run_id}/workbench`、工单详情与事务端点
- 测试证据：`pytest -q`，243 passed
- 业务验收：已授权工单按两阶段五区域聚合；到达事件切换接收阶段；Late 区事务缺少标准原因码时拒绝
- 已知限制：最后一批、MES 对账、扫码和设备采集不在当前实现范围
- 用户确认：待确认

### BE-UI-005 验收记录

- 状态变更：`[PARTIAL]` -> `[VERIFIED]`
- 日期：2026-06-19
- 实现证据：`sdbr/exception_center_view.py`、`GET /planner/workbench/exceptions/workbench`、`GET /planner/workbench/exceptions/{exception_id}/workbench`
- 测试证据：`pytest -q`，246 passed
- 业务验收：统一异常清单包含严重程度、状态、对象、发生时间、原因代码、业务影响、建议动作、负责人和审计历史；详情返回关联对象和处理动作
- 已知限制：异常关闭、分派、SLA 和完整处置工作流尚未实现
- 用户确认：待确认

### BE-UI-006 验收记录

- 状态变更：`[NOT-STARTED]` -> `[PARTIAL]`
- 日期：2026-06-19
- 实现证据：`sdbr/administration_view.py`、`GET /planner/workbench/administration/workbench`
- 测试证据：`pytest -q`，248 passed
- 业务验收：只读管理后台 read model 包含主数据对象定义、导入入口、预校验/版本生成语义、资源扩展字段、日历四层、Gurobi/OR-Tools/Simio、ERP/MES、Worker 队列和 SQLite 健康状态
- 已知限制：敏感连接参数编辑、配置持久化、真实 ERP/MES/Simio 连接监控和配置变更审计仍未实现
- 用户确认：待确认

### BE-DATA-014 / BE-RUN-001 至 BE-RUN-003 验收记录

- 状态变更：保持 `[VERIFIED]`，补充测试数据驱动闭环证据
- 日期：2026-06-19
- 实现证据：`sdbr/test_data.py`、`GET /planner/workbench/test-data/cases`、`sdbr-reset-test-data --list-cases`、`POST /planner/workbench/planning-runs`、enqueue、claim-next、execute
- 测试证据：`pytest tests/test_test_data.py tests/test_business_closure.py -q`，11 passed；`pytest -q`，271 passed，2 warnings
- 业务验收：基准测试数据可创建 Planning Run，固定引用主数据版本与运行状态快照，完成入队、Worker 领取、OR-Tools CP-SAT 执行并进入 Completed/Draft；案例台账明确基准、物料短缺和 WIP 超限的预期阻塞代码
- 已知限制：测试数据规模仍是基准工厂，不构成大规模性能基线
- 用户确认：待确认

### BE-OUT-001 / BE-OUT-002 / BE-OUT-003 / BE-OUT-008 验收记录

- 状态变更：保持既有状态，补充测试数据驱动计划输出证据
- 日期：2026-06-19
- 实现证据：`sdbr/schedule_result_view.py`、`sdbr/schedule_output.py`、Schedule Result 与 Work Order workbench API
- 测试证据：`pytest tests/test_business_closure.py -q`，4 passed；`pytest -q`，261 passed
- 业务验收：Completed Planning Run 的 Schedule 可被排程结果、甘特、系统负载和已排程工单 read model 消费，工单计划返回订单、资源、计划开始与完成时间
- 已知限制：高级甘特字段、冻结区、换型和计划/实际对比仍按原条目保持未完成或部分实现
- 用户确认：待确认

### BE-REL-004 / BE-REL-005 / BE-UI-004 验收记录

- 状态变更：保持 `[VERIFIED]`，补充释放门控与排程结果对齐证据
- 日期：2026-06-19
- 实现证据：`sdbr/work_order_release_view.py`、`sdbr/release_candidates.py`、Release Management workbench API
- 测试证据：`pytest tests/test_business_closure.py -q`，4 passed；`pytest -q`，261 passed
- 业务验收：释放管理消费 Completed Planning Run 的冻结排程结果；基准场景存在可授权候选；物料短缺场景输出 `MATERIAL_SHORTAGE`；WIP 超限场景输出 `WIP_LIMIT_EXCEEDED`
- 已知限制：策略阈值配置中心仍由 `BE-REL-012` 跟踪
- 用户确认：待确认

### BE-RUN-009 / BE-OUT-010 验收记录

- 状态变更：`[NOT-STARTED]` -> `[VERIFIED]`
- 日期：2026-06-19
- 实现证据：`sdbr/plan_publication.py`、`GET /planner/workbench/planning-runs/{run_id}/publication`、review/approve/publish/revoke API
- 测试证据：`pytest tests/test_business_closure.py -q`，4 passed；`pytest -q`，261 passed
- 业务验收：计划发布生命周期支持 Draft、Reviewed、Approved、Published、Superseded、PublicationRevoked；非法跳转被拒绝；发布生成带 Schedule fingerprint 的内部发布包；新发布计划会替代同一 ProblemID 下旧 Published 计划；发布和撤销写入审计；Planner 不能发布或撤销
- 已知限制：真实 ERP/MES 回写、确认回执、重发和对账仍由 `BE-INT-*` 跟踪
- 用户确认：待确认

### BE-OUT-002 / BE-OUT-003 / BE-OUT-008 / BE-OUT-009 / BE-OUT-010 输出治理验收记录

- 状态变更：`BE-OUT-008`、`BE-OUT-009`、`BE-OUT-010` 保持 `[VERIFIED]`；`BE-OUT-002`、`BE-OUT-003` 保持 `[PARTIAL]` 并补充内部输出包证据
- 日期：2026-06-21
- 实现证据：`sdbr/schedule_output_governance.py` 新增输出治理 read model 和内部计划输出包；`sdbr/api.py` 新增 `GET /planner/workbench/schedule-results/runs/{run_id}/governance`、`GET /planner/workbench/schedule-results/runs/{run_id}/output-package`，并扩展工单详情 `OutputContext`、`ReleaseContext`、`AuditContext`
- 测试证据：`python -m compileall -q sdbr`；`pytest tests/test_api.py -q -k "schedule_result or output_governance or publication" --basetemp .tmp/pytest-output-governance -p no:cacheprovider`，5 passed；`pytest tests/test_api.py -q -k "be_out_010 or be_out_008_009 or schedule_result_workspace" --basetemp .tmp/pytest-output-governance-detail -p no:cacheprovider`，4 passed
- 业务验收：Completed Run 可返回治理摘要、完整性检查、发布状态、输出包摘要、释放授权摘要和审计摘要；内部输出包包含工单级计划、工序级计划、资源负荷摘要、甘特摘要、释放建议、冻结策略/主数据/快照上下文和诊断摘要；未完成或缺少运行快照的计划不能生成可交付输出包；工单详情可追溯到输出包、计划指纹、发布状态、释放建议/授权和相关审计动作
- 已知限制：真实 ERP/MES 投递、回执、重放、对账和外部系统错误处理仍由 `BE-INT-*` 跟踪；甘特与负荷在本阶段只进入内部输出包摘要，计划/实际对比仍等待 MES 执行数据
- 用户确认：待确认

### BE-SOLVER-002 / BE-SOLVER-009 验收记录

- 状态变更：`BE-SOLVER-002 [VERIFIED] -> [PAUSED]`；`BE-SOLVER-009 [PAUSED] -> [PARTIAL] -> [VERIFIED]`
- 日期：2026-06-19
- 实现证据：`sdbr/cp_sat_solver.py`、`sdbr/scheduling_solver.py`、Planning Run和重排活动引擎策略、求解器能力 read model
- 测试证据：`pytest -q`，267 passed；Python compileall和前端脚本语法检查通过
- 业务验收：三组隔离 SQLite 场景均由 OR-Tools CP-SAT 完成并返回 Optimal；每组输出12个工单、6条甘特资源行和6条负载行；基准场景8个可释放，短缺与WIP场景分别返回 `MATERIAL_SHORTAGE` 和 `WIP_LIMIT_EXCEEDED`
- 暂停验收：新 Gurobi Planning Run 返回409和 `SolverBackendPaused`；Worker不领取历史Queued Gurobi任务；历史结果保留真实求解器标识和读取路径
- 已知限制：`release_not_before`、顺序相关换型、冻结区、批次和完整多目标策略仍按 `BE-SOLVER-007`、`BE-SOLVER-010` 至 `BE-SOLVER-014` 跟踪
- 用户确认：待确认

### BE-SOLVER-012 验收记录

- 状态变更：`[NOT-STARTED]` -> `[PARTIAL]`
- 日期：2026-06-20
- 实现证据：`sdbr/scheduling_solver.py` 增加 `FixedOperationAssignment` 和排程问题固定安排输入；`sdbr/cp_sat_solver.py` 增加 CP-SAT 固定开始时间、固定资源选择和结构化输入诊断
- 测试证据：`pytest tests/test_scheduling_solver.py -q`，30 passed；`pytest tests/test_api.py -q -k "replan_execution_preserves_operations_inside_freeze_window or replan_execution_preserves_locked_orders or replan_execution_runs_cp_sat"`，3 passed；`pytest -q`，279 passed，2 warnings
- 业务验收：工序级人工固定安排会作为硬约束进入 CP-SAT；固定到备用资源时不会被目标函数挪回主资源；两个固定工序抢占同一有限资源时返回 `Infeasible`；非候选资源、重复固定和早于计划起点的固定输入返回结构化错误；重排执行会读取同一 `ProblemID` 下最近 Completed 计划的锁定工单审计事件，并将其已排工序作为 `FixedAssignments` 带入 CP-SAT；当重排 payload 设置 `FreezeWindowMinutes` 时，上一版计划中落入重排起点加冻结窗口的工序也会被自动固定
- 已知限制：锁定范围细分、跨源计划显式选择、新建 Planning Run 的锁定来源选择仍未完成；当前重排保留策略默认使用同一 `ProblemID` 最近 Completed 计划
- 用户确认：待确认

### BE-SOLVER-010 / BE-SOLVER-011 / BE-SOLVER-014 验收记录

- 状态变更：保持 `[PARTIAL]`，补充 CP-SAT 高级排程 P1 闭环证据
- 日期：2026-06-20
- 实现证据：`sdbr/scheduling_solver.py` 增加 `SetupTransition`、资源并行数量、效率、工序时间窗和策略 ID；`sdbr/cp_sat_solver.py` 增加顺序相关换型、累计并行产能、效率时长、时间窗和内置目标策略；`sdbr/api.py` 增加高级排程 payload 与 Planning Run 冻结字段
- 测试证据：`python -m compileall -q sdbr`；`pytest tests/test_scheduling_solver.py -q`，37 passed；`pytest tests/test_api.py -q -k "advanced_cp_sat_fields or planning_run_lifecycle"`，2 passed；`pytest -q`，287 passed，2 warnings
- 业务验收：单机有限资源支持非对称换型矩阵并影响排序；同族或无矩阵不增加换型；资源 `CapacityUnits > 1` 允许同资源并行加工；`EfficiencyPercent` 会修正有效加工时长；工序 `EarliestStartAt/LatestEndAt` 作为硬时间窗进入 CP-SAT；calculate API 和 Planning Run 可冻结 `ObjectiveStrategyID` 与 `SetupTransitions`，并返回高级能力诊断
- 已知限制：多并行资源暂不支持顺序相关换型；班组人数、固定偏移、版本化策略中心、策略配置持久化和方案解释仍未完成；批次/合批/拆批继续由 `BE-SOLVER-013` 跟踪
- 用户确认：待确认

### BE-SOLVER-013 占位验收记录

- 状态变更：保持 `[NOT-STARTED]`，补充设计占位证据
- 日期：2026-06-20
- 实现证据：`sdbr/administration_view.py` 在只读管理模型中暴露 `BatchFamily`、`MergeRule`、`SplitPolicy`、`BatchID`、`MinimumSplitQuantity`、`MaximumBatchQuantity` 和 `MixedOrderAllowed` 等未来字段/策略分组
- 测试证据：`python -m compileall -q sdbr`；`pytest tests/test_api.py -q -k "administration_workbench"`，1 passed；`pytest -q`，287 passed，2 warnings
- 业务验收：批次、合批、拆批和订单分组未进入 CP-SAT；当前只为后续 UI/需求讨论提供字段台账，避免把规则硬编码进求解器
- 已知限制：必须先明确合批粒度、拆批条件、批量容量、混批限制、批次物料可用性和订单承诺拆分规则，才能开始实现
- 用户确认：待确认

### BE-SOLVER-012 / BE-REL-012 / BE-DATA-010 / BE-DATA-011 / BE-DATA-013 / BE-OUT-009 验收记录

- 状态变更：`BE-DATA-013`、`BE-OUT-009` 推进到 `[VERIFIED]`；`BE-SOLVER-012`、`BE-REL-012`、`BE-DATA-010`、`BE-DATA-011` 保持 `[PARTIAL]` 并补充闭环证据
- 日期：2026-06-20
- 实现证据：`sdbr/api.py` 增加 `SourceRunID`、`ReleasePolicyVersionID`、DBR 释放策略版本、主数据版本比较/发布/停用/回滚、重排来源追踪和差异摘要；`sdbr/state_store.py` 持久化 DBR 策略；`sdbr/work_order_release_view.py` 扩展工单详情和释放策略快照；`sdbr/planning_run_view.py` 暴露冻结源计划与策略
- 测试证据：`pytest tests/test_api.py -q -k "be_solver_012 or be_rel_012 or be_data_010_011_013 or planning_run_lifecycle or scheduled_work_order_detail"`，5 passed；`pytest tests/test_state_store.py -q`，8 passed；`python -m compileall -q sdbr`；`pytest -q`，291 passed，2 warnings
- 业务验收：Planning Run 可显式引用已完成源计划并冻结 DBR 策略版本；重排执行返回 `ReplanTrace` 与工序级 `ReplanDiff`；释放管理返回冻结策略快照；主数据版本可比较、发布、停用和回滚；工单详情聚合计划、生产、销售、释放、备注、UDF 和审计上下文
- 已知限制：DBR 策略参数当前完成版本化与追溯，尚未全部驱动释放算法；锁定范围细分、临时加班/停工对象 API、班组人数、固定偏移仍需业务规则或 UI 交互边界明确
- 用户确认：待确认

### BE-INT-001 / BE-INT-002 / BE-INT-004 / BE-INT-005 / BE-INT-007 / BE-DATA-014 / BE-REL-012 / BE-UI-006 验收记录

- 状态变更：`BE-INT-001`、`BE-INT-002`、`BE-INT-007` 从 `[NOT-STARTED]` 推进到 `[PARTIAL]`；`BE-INT-004`、`BE-INT-005`、`BE-DATA-014`、`BE-REL-012`、`BE-UI-006` 保持原状态并补充契约、案例与配置证据
- 日期：2026-06-20
- 实现证据：`sdbr/integration_contracts.py` 定义 ERP 入站、ERP 出站、MES 入站、MES 出站契约；`sdbr/api.py` 新增集成契约列表、消息测试桩、死信和重放接口；`sdbr/state_store.py` 持久化集成消息台账；`sdbr/administration_view.py` 输出日历、释放策略、求解策略和集成契约配置摘要；`sdbr/test_data.py` 扩展案例卡输入与预期说明
- 测试证据：`python -m compileall -q sdbr`；`pytest tests/test_integration_contracts.py tests/test_state_store.py -q --basetemp .tmp/pytest-contracts-2 -p no:cacheprovider`，13 passed；`pytest tests/test_test_data.py tests/test_business_closure.py -q --basetemp .tmp/pytest-cases`，13 passed；`pytest tests/test_api.py -q -k "administration_workbench or release_policy_list or be_solver_012" --basetemp .tmp/pytest-config-2 -p no:cacheprovider`，4 passed；`pytest -q --basetemp .tmp/pytest-full-20260620-2 -p no:cacheprovider`，297 passed，1 warning
- 业务验收：当前完成的是接口契约、字段校验、幂等、确认、死信、重放和人工案例验收支撑，不连接真实 ERP/MES；配置后台显示可追溯配置入口，但敏感连接编辑、临时加班/停工独立 API 和真实配置审批仍未实现
- 已知限制：BOM/MRP、批次、合批、拆批、多机台换型、ERP/MES 真实连接、自动重试调度、对账和外部系统健康检查仍需后续业务规则或集成边界明确
- 用户确认：待确认

### BE-INT-* 可替换接口架构记录

- 状态变更：`BE-INT-001`、`BE-INT-002`、`BE-INT-004`、`BE-INT-005`、`BE-INT-007` 保持 `[PARTIAL]`，补充未来直连 ERP/MES 与 UNS 两种技术路线的统一架构约束
- 日期：2026-06-21
- 设计证据：第 10.1 节新增 Canonical Message、Integration Port、Direct Adapter、UNS MQTT Adapter、Mock Adapter、幂等键、死信、重放和 Topic 命名原则
- 业务验收：SDBR 核心排程、释放、派工和发布治理不得直接依赖 ERP/MES/EMQX/Node-RED/IoTDB SDK；未来如选择直连系统，只替换 Direct Adapter；如选择 UNS，只替换 UnsMqttAdapter；核心业务消息、审计、幂等和重放语义保持一致
- 已知限制：当前仍是架构规格，不包含真实 ERP/MES 连接器、MQTT 客户端、Topic 订阅发布实现、外部认证和生产级健康监控
- 用户确认：待确认

### BE-REL-011 / BE-INT-004 / BE-INT-005 MES 派工优先级输出验收记录

- 状态变更：`BE-REL-011`、`BE-INT-004`、`BE-INT-005` 保持 `[PARTIAL]`，补充第一版 MES 派工优先级队列和回执契约证据
- 日期：2026-06-21
- 实现证据：`sdbr/dispatch_priority.py` 新增资源/工作中心 + 工序级派工队列；`GET /planner/workbench/dispatch-priority/runs/{run_id}/workbench` 输出队列、候选预警、冲突结果、调度员确认提示和重排建议；`sdbr/api.py` 在派工前使用最新运行状态重新调用释放门控；`sdbr/integration_contracts.py` 补充 DispatchQueueIssued、DispatchAccepted、StartedOperation、CompletedOperation、DispatchRejected、ExceptionReported 消息类型
- 测试证据：`pytest tests/test_dispatch_priority.py -q --basetemp .tmp/pytest-dispatch-priority -p no:cacheprovider`，3 passed；`pytest tests/test_api.py -q -k "dispatch_priority or integration_contract" --basetemp .tmp/pytest-dispatch-api -p no:cacheprovider`，1 passed；`pytest tests/test_dispatch_priority.py tests/test_integration_contracts.py tests/test_shop_floor_execution.py -q --basetemp .tmp/pytest-dispatch-contracts -p no:cacheprovider`，18 passed；`pytest tests/test_api.py -q -k "dispatch_priority or release_authorization or buffer_board or shop_floor" --basetemp .tmp/pytest-dispatch-related-api -p no:cacheprovider`，23 passed
- 业务验收：正式派工只包含已授权且最新物料/WIP/快照门控仍通过的工序；未释放或最新门控阻塞的工单只进入候选/预警；同一资源内按红黄绿、渗透率、计划开始和客户交期排序；允许红区插队；约束资源插队时输出 `RequiresPlannerConfirmation`；连续插队超过 2 次后输出 `NeedsReplan`，但不自动重排
- 已知限制：真实 MES 投递、外部确认对账、UNS Topic 发布、直连 Adapter、投递重试队列和 UI 独立派工页面仍未实现；当前端点是内部稳定 read model/API 契约
- 用户确认：待确认

### BE-DATA-014 案例验收体系验收记录

- 状态变更：保持 `[VERIFIED]`，补充案例验收包、预期/实际差异、人工确认/驳回和持久化证据
- 日期：2026-06-20
- 实现证据：`sdbr/test_case_acceptance.py` 输出 `AcceptancePackageID`、执行计划、案例预期、实际对照、失败原因、最新人工决策和决策记录；`sdbr/api.py` 新增 `/planner/workbench/test-data/acceptance/{case_id}/decision` 与 `/planner/workbench/test-data/acceptance/decisions`；`sdbr/state_store.py` 持久化 `test_case_acceptance_decisions`
- 测试证据：`python -m compileall -q sdbr`；`pytest tests/test_business_closure.py -q --basetemp .tmp/pytest-acceptance-business -p no:cacheprovider`，7 passed；`pytest tests/test_test_data.py -q --basetemp .tmp/pytest-acceptance-data -p no:cacheprovider`，9 passed；`pytest -q --basetemp .tmp/pytest-full-acceptance-20260620 -p no:cacheprovider`，300 passed，1 warning
- 补充证据：2026-06-22 新增 `/planner/workbench/test-data/acceptance/{case_id}/reset` 与 `/planner/workbench/test-data/acceptance/reset`；验收包新增 `ScheduleResultOpenable` 与 `ScheduleResultUnavailableReason`；`python -m compileall -q sdbr`；`pytest tests/test_business_closure.py tests/test_api.py -q -k "openable_schedule_results or acceptance_reset or reset_all or case_acceptance_overview or admin_001_002 or cp_sat_business_cases or schedule_result_workspace or ui_calendar" --basetemp .tmp/pytest-case-reset -p no:cacheprovider`，9 passed
- 业务验收：案例体系可展示测试数据输入、排程预期、释放预期、发布预期、自动判定结果和逐项差异；通过案例可由人工确认，未执行或未通过案例不能被确认；确认/驳回记录可审计并可跨 SQLite 重载保留；每个案例可复位到可重新执行状态，全部案例可一键复位
- 已知限制：当前案例仍限于基准、物料短缺、WIP 超限和六组 `TST-CP-*` 标准场景；真实业务案例、行业模板和更复杂人工确认工作流仍需后续扩展
- 用户确认：待确认

### BE-DATA-014 / BE-SOLVER-009 至 BE-SOLVER-011 / BE-SOLVER-014 CP-SAT 业务案例验收记录

- 状态变更：`BE-DATA-014`、`BE-SOLVER-009` 保持 `[VERIFIED]`；`BE-SOLVER-010`、`BE-SOLVER-011`、`BE-SOLVER-014` 保持 `[PARTIAL]` 并补充可人工验收的业务案例证据
- 日期：2026-06-21
- 实现证据：`sdbr/test_data.py` 新增六组 `TST-CP-*` Planning Run、独立 Master Data Version 和案例目录字段；`sdbr/test_case_acceptance.py` 增加期望诊断与业务断言判定；`docs/cp-sat-business-case-acceptance.md` 说明有限产能、备用资源、日历覆盖、资源效率、顺序相关换型和不可行诊断案例；`sdbr/web/planner-workbench.js` 在案例卡显示案例分组、类型、期望断言、通过断言和差异原因
- 测试证据：`python -m compileall -q sdbr`；`pytest tests/test_test_data.py -q --basetemp .tmp/pytest-cp-cases-data -p no:cacheprovider`，9 passed；`pytest tests/test_business_closure.py -q --basetemp .tmp/pytest-cp-cases-business -p no:cacheprovider`，9 passed；`pytest tests/test_api.py -q -k "case_acceptance_overview" --basetemp .tmp/pytest-cp-cases-ui -p no:cacheprovider`，1 passed；`pytest -q --basetemp .tmp/pytest-full-cp-business-cases -p no:cacheprovider`，316 passed，1 warning
- 业务验收：六组 `TST-CP-*` 案例可端到端执行，并通过 `GET /planner/workbench/test-data/acceptance` 输出“期望断言 / 通过断言 / 差异原因”；Completed 案例必须标记为可打开排程结果，不可行案例以 `DeadLetter` + `ORTOOLS_INFEASIBLE` 作为正确结果，不伪装成可执行计划，并返回不可打开原因
- 已知限制：案例只验证当前通用 CP-SAT 假设，不覆盖 BOM/MRP、批次/合批/拆批、多并行资源机台级换型、ERP/MES/Simio 真实集成，也不要求多个等价最优解的具体顺序完全固定
- 用户确认：待确认

### BE-DATA-010 / BE-SOLVER-014 / BE-REL-012 / BE-UI-006 配置后台验收记录

- 状态变更：保持 `[PARTIAL]`，补充日历与策略配置后台证据
- 日期：2026-06-20
- 实现证据：`sdbr/api.py` 新增 `/planner/workbench/admin/calendar-overrides` 和 `/planner/workbench/admin/scheduling-strategies` 创建/列表/查询接口；`sdbr/state_store.py` 持久化日历覆盖与自定义排程策略；`sdbr/administration_view.py` 在管理后台聚合日历覆盖、释放策略和策略权重状态；`sdbr/web/planner-workbench.js` 与 `sdbr/web/planner-workbench.html` 将“计划问题 / Planning problem”修正为“计划场景 / Planning scenario”
- 测试证据：`python -m compileall -q sdbr`；`pytest tests/test_api.py -q -k "calendar_override or scheduling_strategy or administration_workbench or admin_001_002" --basetemp .tmp/pytest-calendar-strategy-target -p no:cacheprovider`，4 passed；`pytest -q --basetemp .tmp/pytest-full-calendar-strategy-20260620 -p no:cacheprovider`，302 passed，1 warning
- 业务验收：计划员/管理员可把临时班次、停机/维护、加班作为版本化配置台账保存和查询；可把多目标权重作为自定义排程策略保存并设置单一活动策略；管理后台可查看配置数量、活动项、状态计数和边界说明
- 已知限制：临时日历覆盖已可驱动新建 Planning Run 的 CP-SAT 能力桶；覆盖冲突、基础日历模板编辑、配置审批、UI 编辑和敏感外部连接参数编辑仍需后续业务规则；自定义策略权重驱动 CP-SAT 的业务效果需通过案例验收校准
- 用户确认：待确认

### BE-SOLVER-014 CP-SAT 假设与可调参数验收记录

- 状态变更：保持 `[PARTIAL]`，补充自定义策略权重驱动 CP-SAT 与假设说明接口证据
- 日期：2026-06-20
- 实现证据：`sdbr/api.py` 新增 `GET /planner/workbench/admin/cp-sat/assumptions`；`/planner/workbench/admin/scheduling-strategies` 创建的自定义权重可被 calculate、方案比较、重排和 Planning Run 执行路径消费；Planning Run 创建时冻结 `FrozenSchedulingStrategy`；排程输出返回 `ObjectiveWeights`；`sdbr/cp_sat_solver.py` 对自定义策略输出 `ORTOOLS_CUSTOM_OBJECTIVE_WEIGHTS_ENABLED` 诊断
- 测试证据：`python -m compileall -q sdbr`；`pytest tests/test_api.py -q -k "cp_sat_assumptions or custom_objective_strategy or freezes_custom_objective_strategy or advanced_cp_sat_fields or scheduling_strategy" --basetemp .tmp/pytest-cp-sat-params-target -p no:cacheprovider`，5 passed；`pytest -q --basetemp .tmp/pytest-full-cp-sat-params-20260620 -p no:cacheprovider`，305 passed，1 warning
- 业务验收：后台可查询 CP-SAT 当前建模假设、可调参数、暂停求解器、延后规则和活动策略；自定义策略权重会实际进入 CP-SAT 加权目标；找不到策略 ID 时返回结构化 `SchedulingStrategyNotFound`；Planning Run 冻结策略后，后续策略变更不会改变该 Run 的求解权重
- 已知限制：权重数值的业务含义仍需通过真实案例校准；策略仿真解释、UI 调参、批次/MRP/多机台换型/Simio 反馈仍不在当前实现范围
- 用户确认：待确认

### BE-REL-012 / BE-SOLVER-007 / BE-OUT-002 / BE-UI-006 释放策略驱动算法验收记录

- 状态变更：`BE-REL-012` 推进到 `[VERIFIED]`；`BE-SOLVER-007`、`BE-OUT-002`、`BE-UI-006` 保持 `[PARTIAL]` 并补充释放策略驱动证据
- 日期：2026-06-21
- 实现证据：`sdbr/release_policy.py` 统一释放策略参数；Planning Run 执行冻结策略并用 `RopeBufferMinutes` 生成建议释放时间；`sdbr/work_order_release_view.py` 用冻结策略比例计算红黄绿、用策略 WIP 上限和物料检查窗口生成阻塞原因、用稳定性阈值输出 Monitor/Review/Replan；`sdbr/release_authorization.py` 和 `sdbr/api.py` 在授权与调度包中保留策略版本和策略证据；`sdbr/web/planner-workbench.js` 在释放管理中展示策略版本、触发参数和稳定性判断
- 测试证据：`python -m compileall -q sdbr`；`pytest tests/test_api.py -q -k "be_rel_012 or planning_run_release_workbench_authorizes_only_ready_order or release_candidates_mark_late_inbound_material" --basetemp .tmp/pytest-release-policy -p no:cacheprovider`，9 passed；修复兼容性后执行 `pytest tests/test_release_candidates.py tests/test_api.py -q -k "release_candidates_return_completed_replan_release_readiness or builds_release_candidates_from_schedule_and_material_state or blocks_release_candidate_when_wip_limit_would_be_exceeded or be_rel_012" --basetemp .tmp/pytest-release-policy-fixes -p no:cacheprovider`，10 passed；`pytest -q --basetemp .tmp/pytest-full-release-policy-final -p no:cacheprovider`，311 passed，1 warning
- 业务验收：同一排程结果可因冻结策略不同而改变建议释放时间、缓冲颜色、WIP 阻塞、在途物料可用判断和稳定性动作；历史 Planning Run 使用冻结策略快照，后续策略变更不改变已完成计划
- 已知限制：释放策略仍不作为 CP-SAT 的物料/WIP 硬约束；批次、BOM/MRP、多机台换型、ERP/MES 回写和完整策略编辑审批 UI 仍待业务规则或集成边界明确
- 用户确认：待确认

### BE-UI-004 / UI-RELEASE-001 释放门控重新评估验收记录

- 状态变更：保持 `[VERIFIED]`，补充“同一计划使用最新运行快照重新评估释放门控”的业务证据
- 日期：2026-06-21
- 实现证据：`GET /planner/workbench/release-management/runs/{run_id}/workbench` 增加 `use_latest_operational_state` 和 `operational_state_snapshot_id` 查询参数；`POST /planner/workbench/release-management/runs/{run_id}/orders/{order_id}/authorize` 增加 `UseLatestOperationalState` 和 `OperationalStateSnapshotID`；`sdbr/work_order_release_view.py` 返回实际采用的快照 ID；`sdbr/web/planner-workbench.js` 的“重新评估”使用最新运行快照，授权保留当前评估快照
- 测试证据：`python -m compileall -q sdbr`；`pytest tests/test_api.py -q -k "release_management_can_reevaluate_same_run_with_latest_snapshot or planning_run_release_workbench_authorizes_only_ready_order or be_rel_012" --basetemp .tmp/pytest-release-reevaluate -p no:cacheprovider`，9 passed；`pytest tests/test_api.py -q -k "data_readiness_endpoint_returns_latest_safe_summaries or release_management_can_reevaluate_same_run_with_latest_snapshot" --basetemp .tmp/pytest-release-reevaluate-fixes -p no:cacheprovider`，2 passed；`pytest -q --basetemp .tmp/pytest-full-release-reevaluate-final -p no:cacheprovider`，312 passed，1 warning
- 业务验收：如果原 Planning Run 的冻结快照过期，计划员可在不重建任务包、不重新排程的情况下使用最新运行状态快照重新评估物料、在途、WIP 和快照新鲜度；授权释放记录实际使用的新快照
- 2026-06-22 业务边界补充：运行快照过期只阻止授权释放，并返回 `RecommendedAction=RefreshOperationalSnapshotAndReevaluate`、`RequiresReschedule=false`；它不是重排触发条件。只有使用新鲜快照重新评估后仍出现计划偏差、连续阻塞或超过稳定性阈值，才进入 `BE-REL-008` 重排决策。
- 2026-06-22 Mock 闭环补充：新增 `POST /planner/workbench/release-management/runs/{run_id}/mock-operational-state-refresh`，在测试/Mock API 模式下基于现有快照生成评估时点的新运行快照，随后同一 Planning Run 可重新评估释放门控并继续授权/缓冲页验证。
- 已知限制：当前“最新快照”按捕获时间不晚于评估时间的最大值选择；未来可按工厂、产线、资源范围筛选最新快照

### BE-RUN-004 / BE-RUN-006 Planning Run 队列处理补充验收记录

- 状态变更：保持 `[VERIFIED]`，补充“进入队列后可由交互式 Worker 显式领取并执行”的产品闭环证据
- 日期：2026-06-22
- 实现证据：`POST /planner/workbench/planning-runs/{run_id}/process-queued` 将指定 `Queued` 任务推进为 `Running`，校验租约后调用 CP-SAT 执行，最终写回 `Completed`、`Failed`、重试 `Queued` 或 `DeadLetter`；Planning Run 列表对 `Queued` 暴露 `ProcessQueue` 动作
- 测试证据：`pytest tests/test_api.py -q -k "mock_refresh_creates_fresh_snapshot or queued_planning_run_can_be_processed_by_interactive_worker or release_management_can_reevaluate_same_run_with_latest_snapshot" --basetemp .tmp/pytest-release-queue-flow -p no:cacheprovider`，3 passed
- 业务验收：第一版不要求常驻后台 Worker；计划员可通过“处理队列”模拟 Worker 领取、计算、完成和通知，后续可替换为自动 Worker 服务。

### BE-DATA-010 / BE-SOLVER-011 / BE-UI-006 临时日历覆盖驱动排程验收记录

- 状态变更：保持 `[PARTIAL]`，补充 Active 临时覆盖冻结到 Planning Run 并驱动 CP-SAT 的证据
- 日期：2026-06-21
- 实现证据：`sdbr/calendar_overrides.py` 将 Active 覆盖应用到资源日历；Planning Run 创建时冻结 `FrozenCalendarOverrides`；执行时只消费冻结覆盖；`ExclusionOrMaintenance` 扣减维护窗口，`Overtime` 和 `TemporaryShiftOverride` 新增一次性能力窗口；排程结果返回 `CalendarOverrideSummary` 与 `CALENDAR_OVERRIDES_APPLIED` / `CALENDAR_OVERRIDE_NOT_APPLIED` 诊断；管理后台返回动态 `SolverDriverStatus`
- 测试证据：`python -m compileall -q sdbr`；`pytest tests/test_scheduling_solver.py tests/test_api.py -q -k "calendar_override or calendar_overrides_freeze_and_drive_planning_run or resource_calendar_capacity" --basetemp .tmp/pytest-calendar-overrides -p no:cacheprovider`，5 passed；`pytest tests/test_api.py -q -k "calendar_overrides_freeze_and_drive_planning_run" --basetemp .tmp/pytest-calendar-overrides-api -p no:cacheprovider`，1 passed；`pytest -q --basetemp .tmp/pytest-full-calendar-overrides -p no:cacheprovider`，315 passed，1 warning
- 业务验收：计划员可在管理后台创建 Active 临时覆盖，新建 Planning Run 会冻结该覆盖并让 CP-SAT 避开维护窗口或使用加班/临时班次窗口；历史 Run 不受后续覆盖变化影响
- 已知限制：基础日历模板、资源日历分配、覆盖冲突自动解决和审批流仍未实现；`TemporaryShiftOverride` 当前按新增窗口处理，不替换原班次

### BE-DATA-010 / BE-SOLVER-011 / BE-UI-006 基础日历配置验收记录

- 状态变更：保持 `[PARTIAL]`，补充基础日历模板和资源日历分配可配置、可冻结、可驱动 CP-SAT 的证据
- 日期：2026-06-21
- 实现证据：`sdbr/base_calendar.py` 新增基础日历模板应用；`sdbr/api.py` 新增 `/planner/workbench/admin/base-calendars` 与 `/planner/workbench/admin/resource-calendar-assignments` 创建/列表/详情接口；Planning Run 创建时冻结 `FrozenBaseCalendars` 与 `FrozenResourceCalendarAssignments`；执行时先应用基础日历，再应用临时覆盖；`sdbr/administration_view.py` 和管理后台 UI 展示基础日历、资源分配和 driver status
- 测试证据：`python -m compileall -q sdbr`；`pytest tests/test_api.py -q -k "base_calendar or calendar_override_configuration" --basetemp .tmp/pytest-base-calendar -p no:cacheprovider`，3 passed；`pytest tests/test_api.py -q -k "administration_workbench or admin_001_002 or base_calendar or calendar_override_configuration" --basetemp .tmp/pytest-base-calendar-admin -p no:cacheprovider`，5 passed；2026-06-21 补充 `pytest tests/test_scheduling_solver.py -q -k "calendar_override or resource_calendar_conflict_priority" --basetemp .tmp/pytest-calendar-priority-solver -p no:cacheprovider`，3 passed；`pytest tests/test_api.py -q -k "base_calendar or calendar_override_configuration or administration_workbench" --basetemp .tmp/pytest-calendar-priority-api -p no:cacheprovider`，4 passed
- 业务验收：基础日历可定义工作日、多班次、节假日和维护窗口；资源日历分配可将活动日历模板绑定到资源，并保证同一资源只有一个 Active 分配；新建 Planning Run 冻结当时的活动基础日历与资源分配，后续配置变更不影响历史 Run；CP-SAT 按冻结基础日历能力桶排程，测试中资源从 10:00 班次开始排产，切换到 06:00 班次后新 Run 使用新分配；加班和临时覆盖窗口遇到维护会被切段，遇到节假日会被扣除
- 已知限制：审批流、企业节假日自动同步、跨工厂日历继承、节假日强制加班例外规则和 UI 复杂班次编辑器仍未完成；当前 UI 只提供单班次快速创建入口，完整模板编辑仍可通过 API 扩展
- 用户确认：待确认

### BE-DATA-010 / UI-CALENDAR-001 日历预览验收记录

- 状态变更：`BE-DATA-010` 保持 `[PARTIAL]`，补充独立日历页面规格、预览 read model 和前端页面；`UI-CALENDAR-001` 推进到已验证待用户确认
- 日期：2026-06-22
- 实现证据：`docs/ui-specification.md` 新增 `日历配置 / Calendar Configuration` 一级导航和 `UI-CALENDAR-001`；`sdbr/calendar_preview.py` 新增日历事项要素表、冲突优先级、资源级最终能力窗口预览；`GET /planner/workbench/calendar/preview` 返回 `RequiredElements`、`Resources[].Elements`、`Resources[].FinalCapacityWindows`、`MissingDailyCapacityDates`；`GET /planner/workbench/calendar/resources` 返回最新主数据资源供下拉选择；`sdbr/web/planner-workbench.html`、`sdbr/web/planner-workbench.js`、`sdbr/web/planner-workbench.css` 新增独立日历配置页面、双语文案、资源/日期筛选、事项要素、最终窗口和规则来源展示，并复用 `/planner/workbench/admin/base-calendars`、`/planner/workbench/admin/resource-calendar-assignments`、`/planner/workbench/admin/calendar-overrides` 提供工作周/日模式、资源绑定、节假日、维护、加班和临时覆盖的操作入口；管理后台取消日历编辑表单和日历摘要区
- 测试证据：`python -m compileall -q sdbr`；`pytest tests/test_api.py -q -k "calendar_preview or ui_calendar or semantic_application_shell or admin_001_002" --basetemp .tmp/pytest-calendar-page -p no:cacheprovider`，4 passed
- 业务验收：预览阶段重点检查事项是否齐全，包括资源日历分配、基础班次、工作日、节假日、维护、加班、临时覆盖、冲突优先级、时区和跨班次加工规则；最终能力窗口与 CP-SAT 能力桶语义一致
- 已知限制：本阶段完成独立页面的预览、要素检查和核心配置操作，不实现审批流、节假日强制加班例外、跨班次连续加工、复杂表格编辑器和企业节假日同步

### BE-DATA-012 / BE-INT-* / BE-SOLVER-014 第一版交付边界验收记录

- 状态变更：`BE-DATA-012` 从 `[NOT-STARTED]` 推进到 `[PARTIAL]`；`BE-INT-001`、`BE-INT-002`、`BE-INT-004`、`BE-INT-005` 保持 `[PARTIAL]` 并明确第一版采用 Mock API；`BE-SOLVER-014` 保持 `[PARTIAL]` 并明确第一版默认目标策略
- 日期：2026-06-21
- 实现证据：`sdbr/light_mrp.py` 新增轻量 MRP 评估；`POST /planner/workbench/light-mrp/evaluate` 输出工单物料可用、在途覆盖、短缺和缺库存记录；`sdbr/integration_contracts.py` 新增 `MockApiFirstVersion` 与可替换 Adapter 状态；`GET /planner/workbench/integrations/mock-api/status` 返回 Mock API、Direct ERP/MES、UNS MQTT 三种路径状态；`sdbr/scheduling_solver.py` 与 `sdbr/cp_sat_solver.py` 新增第一版默认策略 `v1_delivery_flow_bottleneck`
- 测试证据：`pytest tests/test_material_state.py tests/test_integration_contracts.py tests/test_api.py -q -k "light_mrp or integration_contract or mock_api or administration_workbench" --basetemp .tmp/pytest-v1-boundary-target -p no:cacheprovider`，9 passed；`pytest tests/test_material_state.py tests/test_integration_contracts.py tests/test_api.py tests/test_scheduling_solver.py tests/test_dispatch_priority.py -q -k "light_mrp or integration_contract or mock_api or administration_workbench or objective or dispatch_priority" --basetemp .tmp/pytest-v1-boundary-expanded -p no:cacheprovider`，15 passed；`pytest -q --basetemp .tmp/pytest-full-v1-boundary-final -p no:cacheprovider`，328 passed，1 warning
- 业务验收：第一版外部接口采用 Mock API；MES 只生成资源/工作中心 + 工序级派工建议，不真实下发；本系统做轻量 MRP，但不替代 ERP 库存账务；默认排程偏好为交期优先、流动时间第二、瓶颈/备用资源保护第三
- 已知限制：完整 BOM 展开、多级净需求、替代料、批次/效期分配、真实 ERP/MES/UNS Adapter、自动投递、回执对账和生产级重试调度仍未实现

## 17. 当前验证基线

截至 2026-06-21：

- 已验证核心：主数据导入与校验、冻结版本与快照、Planning Run 生命周期、既有 Gurobi 基础有限排程、释放门控、授权与稳定性、执行偏差、重排、SQLite 持久化、RBAC、审计和并发冲突控制。
- 主要部分实现：资源与日历配置、时间缓冲进入优化模型、Buffer Board、执行优先级、负载/甘特、UI 聚合 API、MES 事件集成、生产运维、CP-SAT 换型/并行资源/效率/时间窗/策略。
- 主要未开始：合批拆批、ERP/MES 真实连接器、生产数据库、企业身份、完整可观测性和流程拓扑挖掘。
- 当前开发：OR-Tools CP-SAT 已成为唯一活动求解器；高级排程 P1 闭环已部分完成，剩余为多机台换型、班组人数、固定偏移、版本化策略中心和批次规则。
- 已暂停：Gurobi 新计划执行、Simio 实际仿真验证。
- 外部边界：ERP 账务与主数据所有权、MES/SCADA 现场操作与设备控制、BI 报表设计器。
- 完整自动化测试：2026-06-21 最近执行 `pytest -q --basetemp .tmp/pytest-full-v1-boundary-final -p no:cacheprovider`，结果为 `328 passed, 1 warning`。警告来自 Starlette TestClient/httpx 弃用提示，不影响测试通过。
- 测试/生产隔离基线：新增 `BE-OPS-011` 环境元数据与独立 SQLite 路径，新增 `BE-DATA-014` 基准工厂、场景包和测试库重建。
- 释放/缓冲测试证据（`BE-DATA-014` / `BE-REL-010` / `BE-EXEC-004`）：已新增时间一致且快照新鲜的端到端案例；默认 60 分钟运行快照新鲜度下可完成释放授权、进入 Buffer Board，并通过执行事务从“待接收”移动到“已接收”。
- 已知日历缺口（`BE-DATA-010` / `BE-UI-006`）：管理 read model 已展示日历四层结构，基础日历模板、资源分配和临时覆盖均可配置；Active 基础日历/分配/临时覆盖已可冻结并驱动新建 Planning Run 的 CP-SAT 能力桶；维护、节假日、临时覆盖、加班和基础班次优先级已进入能力桶计算；审批流、企业节假日同步、节假日强制加班例外和完整 UI 日历编辑器尚未完成。
- 第一版交付边界（`BE-INT-*` / `BE-DATA-012` / `BE-SOLVER-014`）：外部接口采用 Mock API；MES 第一版只生成派工建议，不真实下发；本系统执行轻量 MRP；默认排程偏好为交期优先、流动时间第二、瓶颈/备用资源保护第三；真实 ERP/MES/UNS、完整多级 MRP 和高级批次规则暂不纳入第一版交付。
- 性能与恢复基线记录于 `docs/backend-readiness-2026-06-19.md`；任何状态更新应重新运行相关测试。

## 18. 变更记录

| 版本 | 日期 | 变更 |
| --- | --- | --- |
| 1.0 | 2026-06-19 | 建立完整产品蓝图、能力状态、实现证据、缺口、优先级与审计规则 |
| 1.1 | 2026-06-19 | 完成 BE-UI-001 数据就绪聚合接口并记录 227 项测试基线 |
| 1.2 | 2026-06-19 | 完成 BE-UI-002 Planning Run 工作台 read model、能力状态与冻结策略参数，记录 231 项测试基线 |
| 1.3 | 2026-06-19 | 完成 BE-UI-003 排程结果聚合、方案比较与审计选择接口，记录 235 项测试基线 |
| 1.4 | 2026-06-19 | 完成 BE-OUT-008 与 BE-UI-004：Planning Run 工单 read model、审计命令、释放门控、授权及调度包，记录 239 项测试基线 |
| 1.5 | 2026-06-19 | 明确 BE-REL-010 以 Planning Run、释放授权、冻结计划和执行事件形成两阶段五区域 Buffer Board，启动 UI-BUFFER-001 后台支撑开发 |
| 1.6 | 2026-06-19 | 完成 BE-REL-010 两阶段五区域 Buffer Board；BE-EXEC-004 增加数量、百分比和工时事务契约，记录 243 项测试基线 |
| 1.7 | 2026-06-19 | 明确 BE-UI-005 异常中心聚合接口范围，启动 UI-EXCEPTION-001 后台支撑开发 |
| 1.8 | 2026-06-19 | 完成 BE-UI-005 异常中心聚合与详情接口，记录 246 项测试基线 |
| 1.9 | 2026-06-19 | 明确 BE-UI-006 先提供只读管理后台聚合能力，启动 UI-ADMIN-001/UI-ADMIN-002 后台支撑开发 |
| 2.0 | 2026-06-19 | 完成 BE-UI-006 只读管理后台聚合接口并记录 248 项测试基线，完整配置管理仍保持部分实现 |
| 2.17 | 2026-06-20 | 补充日历覆盖与排程策略后台配置 API，管理后台聚合配置状态，并统一“计划场景”术语 |
| 2.18 | 2026-06-20 | 补充 CP-SAT 建模假设与可调参数接口，自定义目标权重实际驱动 CP-SAT，并记录 305 项测试基线 |
| 2.19 | 2026-06-20 | 记录缓冲执行端到端测试分支不可达及日历只读/部分实现缺口；BE-DATA-014、BE-REL-010、BE-EXEC-004 和 BE-DATA-010 状态不变 |
| 2.20 | 2026-06-20 | 修正建议释放时间优先对齐排程首工序开始时间，补齐释放授权到 Buffer Board 执行事务端到端测试；管理后台新增临时日历覆盖配置入口，BE-DATA-010 仍保持部分完成 |
| 2.21 | 2026-06-21 | 完成释放策略中心驱动当前算法：绳长、缓冲比例、WIP 上限、物料检查窗口和稳定性阈值进入 Planning Run、释放门控、授权证据和 UI read model；BE-REL-012 推进到 VERIFIED |
| 2.22 | 2026-06-21 | 释放管理支持同一已完成计划使用最新运行快照重新评估门控并授权，无需重建任务包或重新排程；记录 312 项测试基线 |
| 2.23 | 2026-06-21 | 临时日历覆盖冻结到 Planning Run 并驱动 CP-SAT 能力桶；基础日历模板编辑与冲突审批仍保持后续边界 |
| 2.24 | 2026-06-21 | 新增六组 `TST-CP-*` CP-SAT 业务案例、人工验收手册、案例断言和总览展示字段，用于按业务直觉验收有限产能、备用资源、日历覆盖、效率、换型和不可行诊断 |
| 2.25 | 2026-06-21 | 新增排程输出治理 read model、内部计划输出包和工单详情治理上下文；真实 ERP/MES 投递仍归 `BE-INT-*` |
| 2.26 | 2026-06-21 | 新增基础日历模板与资源日历分配配置 API，冻结到 Planning Run 并驱动 CP-SAT 能力桶；复杂冲突审批仍保持后续边界 |
| 2.27 | 2026-06-21 | 明确 ERP/MES 集成采用 Canonical Message + Integration Port + 可替换 Adapter 架构，同时支持直连 ERP/MES 与未来 UNS MQTT 路线 |
| 2.28 | 2026-06-21 | 基础日历补齐资源级冲突优先级：维护 > 节假日 > 临时覆盖 > 加班 > 基础班次；加班和临时覆盖遇维护切段、遇节假日扣除 |
| 2.29 | 2026-06-21 | 新增 MES 派工优先级输出：资源/工作中心 + 工序级队列，授权释放硬门槛，最新物料/WIP 再检查，插队/确认/重排建议 |
| 2.30 | 2026-06-21 | 固化第一版交付边界：Mock API 为活动集成方式、MES 仅派工建议、轻量 MRP 第一版、默认目标策略为交期优先/流动时间/瓶颈保护 |
| 2.31 | 2026-06-22 | 新增日历配置独立页面、日历预览 read model、前端预览区和轻量配置操作区，输出事项要素、冲突优先级、最终 CP-SAT 能力窗口和缺失日能力日期；资源/日历改为选择式输入，管理后台取消日历编辑表单和日历摘要区 |
| 2.32 | 2026-06-22 | 案例验收新增排程结果可打开性状态、不可打开原因、单案例复位和全部案例复位，确保 `TST-CP-*` 案例可重复验收 |
| 2.33 | 2026-06-22 | 明确运行快照过期只触发“刷新快照并重新评估释放”，不触发重新排程；阻塞原因增加推荐动作和 `RequiresReschedule=false` 证据 |
| 2.34 | 2026-06-22 | 补齐 Mock 运行快照刷新和 Planning Run 交互式队列处理：释放门控可生成新鲜测试快照后继续授权，Queued 任务可显式领取、计算并完成 |
| 2.1 | 2026-06-19 | 新增 BE-DATA-014 与 BE-OPS-011，用于测试/生产隔离、基准测试数据集、场景包和测试库重建能力 |
| 2.2 | 2026-06-19 | 完成 BE-OPS-011 测试/生产环境隔离与 BE-DATA-014 测试数据重建工具，记录 257 项测试基线 |
| 2.3 | 2026-06-19 | 明确后台业务闭环 1-4 验收边界：测试数据驱动 Planning Run、计划输出、释放门控对齐及计划确认/发布生命周期 |
| 2.4 | 2026-06-19 | 完成后台业务闭环 1-4：测试数据驱动 Planning Run、排程结果进入计划输出、释放门控对齐、计划确认/发布生命周期，记录 261 项测试基线 |
| 2.5 | 2026-06-19 | 调整 BE-SOLVER-002/009 能力边界：启动 CP-SAT 等价迁移并设为唯一活动求解器，Gurobi 暂停新执行但保留历史兼容路径 |
| 2.6 | 2026-06-19 | 完成 BE-SOLVER-009 CP-SAT 等价迁移、活动引擎切换和三场景运行验收，记录267项测试基线；BE-SOLVER-002保持暂停兼容路径 |
| 2.7 | 2026-06-19 | 扩展 BE-DATA-014：新增测试案例台账、只读案例接口和 CLI 列表能力，用于后续按案例验收 CP-SAT、释放门控和计划发布治理 |
| 2.8 | 2026-06-20 | 推进 BE-SOLVER-012：CP-SAT 增加工序级固定开始/固定资源硬约束和结构化诊断，记录 277 项测试基线 |
| 2.9 | 2026-06-20 | 扩展 BE-SOLVER-012：重排执行继承上一版 Completed 计划中已锁定工单并转为 CP-SAT 固定安排，记录 278 项测试基线 |
| 2.10 | 2026-06-20 | 扩展 BE-SOLVER-012：重排执行支持 `FreezeWindowMinutes` 冻结窗口，自动固定上一版计划中窗口内工序，记录 279 项测试基线 |
| 2.11 | 2026-06-20 | 推进 BE-SOLVER-010/011/014：CP-SAT 增加顺序相关换型、并行资源、效率、时间窗和内置目标策略，记录 287 项测试基线 |
| 2.12 | 2026-06-20 | 明确 BE-SOLVER-013 批次/合批/拆批不硬编码，仅在管理 read model 暴露未来字段和策略分组，占位仍保持 NOT-STARTED |
| 2.13 | 2026-06-20 | 推进后续 1-4：显式源计划与重排差异、版本化 DBR 策略、主数据比较/发布/回滚、工单详情治理聚合；批次/BOM/集成继续等待规则明确 |
| 2.14 | 2026-06-20 | 记录用户认可的当前 CP-SAT 通用建模假设及未来按具体业务定制边界；同步修正 AGENTS.md 中活动求解器状态冲突 |
| 2.15 | 2026-06-20 | 定义 ERP/MES 入站/出站契约与消息测试桩，扩展案例验收卡和管理后台日历/释放策略/集成契约配置摘要；真实连接器仍保持未实现 |
| 2.16 | 2026-06-20 | 完成案例验收体系：新增验收包、预期/实际差异、人工确认/驳回记录、审计和 SQLite 持久化，记录 300 项测试基线 |
