# MTO/MTA 共享计划预留基础层设计

## 1. 目的

本设计协调以下两份已确认设计的共同基础：

- `2026-07-10-sdbr-order-commitment-evaluation-design.md`；
- `2026-07-10-ddmrp-runtime-replenishment-closure-design.md`。

两项能力分别服务 MTO 新订单承诺和 MTA/DDMRP 补货运行，但都会创建 CCR 计划级容量预留、物料计划分配，并最终被正式 Planning Run 或 ERP 正式订单消费。如果分别实现，各自维护一套台账，会造成 CCR 负荷、物料需求和库存占用重复计算。

因此实施顺序固定为：先建立共享计划预留基础层，再分别实现 MTO 与 MTA 的只读评估，随后接入两类计划员确认事务，最后完成 Planning Run、Mock ERP 和统一缓冲优先级闭环。

本设计不改变两份上层设计已经确认的业务规则，也不新增 DDAE 主参数。

## 2. 产品与权威边界

共享基础层属于 DDOM / S-DBR 执行层，负责：

- 统一需求身份和来源分类；
- 统一 CCR 计划级容量预留；
- 统一物料计划分配；
- 防止重复承诺和重复计入负荷；
- 将计划预留安全转为正式订单或正式排程占用；
- 保留版本、幂等、事件和审计证据。

它不负责：

- DDAE/DDS&OP 参数、保护线、缓冲档案或资源角色治理；
- ERP/WMS 库存账、正式订单和正式库存分配；
- QMS 质量状态变更；
- 自动接受新订单或自动确认补货建议；
- 自动重排正式计划。

## 3. 核心不变量

1. 同一个业务需求在系统内只有一个稳定的需求身份。
2. 同一需求版本不能重复建立相同 CCR 预留或物料计划分配。
3. MTO 和 MTA 使用同一套 CCR Planned Load 口径。
4. 计划级预留转为正式排程后，不再作为计划预留重复计入负荷。
5. 计划级物料分配被 ERP/WMS 正式分配接管后，不再作为 SDBR 额外扣减重复计算。
6. 一次计划员确认产生的候选、容量预留和物料分配必须全部成功或全部失败。
7. 已确认事实不得被重评估静默覆盖，只能通过新版本、调整、释放或转正事件改变状态。
8. DDMRP 净流需求与物料计划分配是两个不同概念：需求只计一次，分配只防止其他需求重复使用供应。
9. 服务重启、worker 重试、消息重放和重复点击不能产生重复业务对象。
10. 任一投影都必须能够追溯到配置、快照、需求、评估、计划员和事件来源。

## 4. 统一需求身份

### 4.1 Demand Commitment

共享基础层建立 `DemandCommitment`，表示一个需要保护市场承诺或库存补货目标的执行级需求。

建议字段：

- `DemandCommitmentID`；
- `DemandSourceType`；
- `SourceSystem`；
- `SourceObjectType`；
- `SourceObjectID`；
- `SourceObjectVersion`；
- `DemandLineID`；
- `ProductID` 或 `ItemID`；
- `LocationID`；
- `Quantity` 和 `Uom`；
- `RequiredAt`；
- `DemandClass`；
- `ConfigurationReferences`；
- `SnapshotReferences`；
- `TraceID`；
- `Status`。

### 4.2 DemandSourceType

首轮只允许以下来源：

- `MTOCustomerOrder`：真实新订单或正式客户需求；
- `MTAReplenishment`：DDMRP 解耦点补货建议；
- `DependentDemand`：Make BOM 影子展开产生的下级需求；
- `ExternalFormalOrder`：ERP 回传的正式订单需求；
- `Adjustment`：对已确认需求的受控调整。

来源类型必须显示在业务 read model 中，不能只用颜色隐藏 MTO 与 MTA 差异。

### 4.3 去重键

需求业务键采用：

```text
SourceSystem
+ SourceObjectType
+ SourceObjectID
+ SourceObjectVersion
+ DemandLineID
+ ItemOrProductID
+ LocationID
```

相同业务键和相同内容返回已有记录。相同业务键但内容不同必须拒绝并要求新版本，不允许覆盖。

新版本可以生成新的需求记录，但在其确认批次生效前，必须先把旧版本转为 `AdjustmentRequired`、`Released` 或 `Superseded`。同一业务需求不能有两个可同时消耗能力或物料的活动版本。

## 5. 计划确认批次

### 5.1 Planning Reservation Batch

每次计划员接受 MTO 订单或确认 MTA Make 建议时，建立一个 `PlanningReservationBatch`，作为原子事务和审计边界。

批次至少关联：

- 一个 `DemandCommitment`；
- 一个 MTO 接单结果或 MTA 补货建议；
- 零至多个 CCR 容量预留；
- 零至多个物料计划分配；
- MTA Make 场景下的计划制造候选；
- 评估、预览、配置、BOM、日历和运行快照版本；
- 计划员、确认时间和审计原因。

批次状态：

```text
PendingConfirmation
  -> ActivePlanReservation
  -> LinkedToFormalOrder
  -> ConvertedToScheduledOccupancy
```

旁路状态：

- `HeldForPlanningError`；
- `AdjustmentRequired`；
- `Released`；
- `Cancelled`；
- `Rejected`。

MTO 接单与 MTA Make 确认可使用不同前置校验，但写入共享台账时必须遵守相同原子性和幂等规则。

## 6. CCR 计划级容量预留

### 6.1 记录粒度

`CCRCapacityReservation` 采用资源、日期/班次或有效产能窗口的分钟级负荷预留，不锁定班次内精确工序顺序。

至少记录：

- `CapacityReservationID`；
- `ReservationBatchID`；
- `DemandCommitmentID`；
- `DemandClass`；
- `ResourceID`；
- `WindowStartAt`、`WindowEndAt`；
- `ReservedMinutes`；
- `LatestAllowedCompletionAt`；
- `PlanningRunID` 或正式订单引用；
- 配置、日历、评估和 trace 引用；
- 状态和版本。

多 CCR 或同一需求多次访问 CCR 时生成多条明细，但均属于同一确认批次。

### 6.2 CCR Planned Load 唯一口径

每个资源窗口的计划负荷为：

```text
ScheduledProcessingLoad
+ ActivePlanReservationLoad
+ LinkedFormalOrderReservationLoadNotYetScheduled
```

不得计入：

- 已转为正式排程工序的预留；
- 已释放、取消或拒绝的预留；
- 仅用于 What-if 且未被计划员确认的影子负荷；
- DDMRP 尚未确认的 MTA 补货建议。

正式 Planning Run 成功后，相关预留原子转为 `ConvertedToScheduledOccupancy`，同一负荷只由正式工序贡献。Planning Run 失败时保持预留并进入 `HeldForPlanningError`，不得静默释放。

### 6.3 并发保护

确认前必须使用最新状态存储 revision 和负荷版本复查目标窗口。两个请求同时争用同一保护能力时，只允许一个事务成功；另一个返回“负荷已变化，需要重新评估”。现有 `StateStoreRevisionConflict` 作为并发失败信号，不得被转换为普通成功或静默重试。

## 7. 物料计划分配

### 7.1 目的

`MaterialPlanningAllocation` 防止尚未被 ERP/WMS 正式分配接管的库存或供应被多个计划候选重复承诺。它不是库存账，也不是物料需求本身。

至少记录：

- `MaterialPlanningAllocationID`；
- `ReservationBatchID`；
- `DemandCommitmentID`；
- `RequirementLineID`；
- `ItemID`、`LocationID`、`Uom`；
- `AllocatedQty`；
- `SupplySourceType` 和可选供应引用；
- `MaterialSnapshotID`；
- `ExternalAllocationRef`；
- 状态和版本。

### 7.2 需求与分配不得重复扣减

DDMRP 净流评估中：

- 业务需求通过 `DemandCommitment` 或合格需求信号进入 `QualifiedDemandQty`，只计一次；
- 与该需求关联的计划分配不能再次作为第二条需求扣减净流位置；
- 计划分配的作用是让其他候选在物料可行性检查中看不到已承诺供应。

其他候选的可用性检查采用：

```text
UncommittedAvailability
= QualifiedPhysicalOrInboundSupply
- AuthorityAllocationsNotRepresentedAsCurrentCandidateSupply
- ActiveSDBRPlanningAllocationsForOtherDemandCommitments
```

计算必须按 `DemandCommitmentID` 排除当前需求自身的分配，避免自我重复扣减。

### 7.3 外部权威接管

当 ERP/WMS 返回正式分配引用且新的权威快照已经包含该分配时，SDBR 计划分配转为 `Externalized`。后续可用性计算只读取权威分配，不再额外扣减 SDBR 计划分配。

如果只有正式订单引用但权威快照尚未同步，计划分配保持 `LinkedToFormalOrder` 并继续保护供应，直到权威快照完成接管。

## 8. MTO 与 MTA 的共同和差异

### 8.1 共同部分

- 共享需求身份；
- 共享容量和物料台账；
- 共享快照、版本和过期确认门控；
- 共享事务、幂等、审计和事件关联；
- 共享 Planning Run 转正逻辑；
- 共享 CCR Planned Load 投影；
- 统一缓冲优先级中保留来源分类。

### 8.2 MTO 特有部分

- 从客户请求交期和路线进行影子排程；
- 返回接单建议和最早安全日期；
- 计划员接受订单后建立预留；
- 跳过物料检查时只登记待确认需求，不创建已通过物料声明；
- 正式 Planning Run 失败后保留承诺和预留。

### 8.3 MTA 特有部分

- 从 DDMRP Red/Yellow 净流结果生成补货建议；
- Green/AboveGreen 不产生补货量；
- Make 确认前执行 BOM、下级物料和 CCR 预览；
- Make 确认后建立计划制造候选和预留；
- Buy/Transfer 不建立制造 CCR 预留，只进入外部建议治理；
- 下级物料不足时计划制造候选不可释放。

## 9. Planning Run 转正桥接

Planning Run 创建和执行时必须识别仍有效的计划确认批次：

1. 冻结相关 `DemandCommitmentID`、`ReservationBatchID`、容量预留和物料分配版本；
2. 排程时把容量预留作为承诺边界，而不是再额外增加一份重复工序负荷；
3. 排程成功后，将实际工序与预留关联并把预留转为 `ConvertedToScheduledOccupancy`；
4. 物料计划分配继续有效，直到 ERP/WMS 权威分配接管或需求取消；
5. 排程失败时，将批次标为 `HeldForPlanningError`，保留预留并生成异常；
6. 取消或调整必须通过受控事件释放或替代原批次。

Planning Run 不得根据缺失引用创建占位路由、资源、日历、物料或地点。

## 10. 事件、幂等与投影

### 10.1 事件信封

共享事件至少包含：

- `EventID`；
- `EventType`；
- `OccurredAt`；
- `SourceSystem`；
- `CausationID`；
- `CorrelationID`；
- `IdempotencyKey`；
- `DemandCommitmentID`；
- `ReservationBatchID`；
- `TraceID`；
- 版本和业务 payload。

### 10.2 事件循环保护

- 接单确认或补货确认产生需求/预留事件，但不得再次创建同一需求；
- DDMRP 重评估可读取预留变化，却不能把同一预留重新解释为一条新需求；
- Planning Run 转正事件只改变预留状态，不再次增加 Planned Load；
- ERP/WMS 回执根据外部引用和幂等键更新同一对象，不创建重复对象；
- 已处理事件 ID 和幂等键必须持久化。

### 10.3 业务投影

共享基础层提供：

- CCR Planned Load 投影；
- 未转正容量预留投影；
- 物料未外部化计划分配投影；
- 需求承诺与来源投影；
- Planning Run 转正和异常投影；
- MTO/MTA 统一优先级所需的来源和状态字段。

## 11. 当前代码落点

当前仓库使用 `WorkbenchStateStore` / `SQLiteWorkbenchStateStore` 保存整体 JSON 状态，并以 revision 防止并发覆盖。首轮不引入新的 ORM 或独立数据库。

共享基础层建议采用以下模块边界：

- `sdbr/planning_commitments.py`：需求身份、状态和去重；
- `sdbr/planning_reservations.py`：确认批次、CCR 预留、物料计划分配和事务规则；
- `sdbr/planning_reservation_view.py`：Planned Load、未转正预留和物料分配 read model；
- `sdbr/planning_run_reservation_bridge.py`：Planning Run 冻结、转正和异常；
- `sdbr/state_store.py`：新增持久化集合和状态计数；
- `sdbr/api.py`：后续只做编排与端点绑定，不承载领域规则。

建议新增状态集合：

- `planning_demand_commitments`；
- `planning_reservation_batches`；
- `ccr_capacity_reservations`；
- `material_planning_allocations`；
- `planning_reservation_events`；
- `processed_planning_event_keys`。

SQLite 存储仍使用单次 `BEGIN IMMEDIATE`、revision 检查和整体状态保存，保证同一次确认批次原子持久化。确认服务必须采用 copy-on-write 或显式回滚；如果 `save()` 因 `StateStoreRevisionConflict` 或其他异常失败，进程内 Store 也不能残留候选、容量或物料的部分变更。未来只有在性能证据表明整体状态存储不足时，才迁移为独立关系表。

## 12. 规格与契约门控

实施前必须：

1. 在 `docs/backend-specification.md` 增加共享需求承诺、CCR 预留、物料计划分配和 Planning Run 转正的 `BE-*` 验收项；
2. 明确现有 `BE-SDBR-*`、`BE-DDMRP-*`、`BE-RUN-*` 如何消费共享台账；
3. 在 `docs/ui-specification.md` 仅记录后续两个工作台的共享状态显示，不为基础层增加独立业务页面；
4. 核对 DDAE 是否提供正式 CCR 保护线；缺失时只能使用明确标记的参考试算；
5. 核对 ERP/WMS Mock 契约是否支持正式订单和分配接管 ACK；缺失时提交 Contract Agent 变更请求；
6. 不在 SDBR 中增加隐式 DDAE 或 ERP 字段。

## 13. 实施顺序

### 阶段 0：共享基础层

1. 规格更新和共享术语固定；
2. 需求身份与去重；
3. 确认批次、CCR 预留和物料计划分配；
4. State Store 持久化和 revision 并发测试；
5. Planned Load 和物料可用性共享投影；
6. Planning Run 转正、失败保留和释放规则；
7. 事件幂等和审计。

### 阶段 1：可并行的只读评估

- MTO：订单影子排程、接单建议和安全日期；
- MTA：版本化 DDMRP 评估、补货建议和运行工作台。

两条线在此阶段不得直接写入自有预留台账。

### 阶段 2：计划员确认事务

- MTO 接受订单调用共享确认服务；
- MTA Make 确认调用共享确认服务；
- Buy/Transfer 仅进入外部建议治理；
- 集成测试证明并发确认不会重复承诺。

### 阶段 3：正式闭环

- Planning Run 消费与转正；
- Mock ERP 正式订单/分配 ACK；
- 执行事件和 DDMRP 局部重评估；
- MTO/MTA 统一缓冲优先级。

## 14. 验收测试

1. 相同需求业务键和内容重复提交时返回同一需求，不新增记录。
2. 相同需求业务键但内容变化时要求新版本。
3. MTO 和 MTA 对同一 CCR 窗口的预留进入同一 Planned Load。
4. 未确认影子负荷不进入 Planned Load。
5. 正式排程转正后，原容量预留不重复计入负荷。
6. Planning Run 失败后预留保持有效并标记异常。
7. 两个并发确认争用同一能力时只有一个成功。
8. 确认批次中候选、容量和物料任一失败时全部回滚。
9. 同一需求在 DDMRP 净流中只计一次，计划分配不造成第二次需求扣减。
10. 其他候选的物料可用性排除已分配供应。
11. 当前候选的可用性检查排除自身分配，避免自我重复扣减。
12. ERP/WMS 正式分配被权威快照接管后，SDBR 分配不再重复扣减。
13. 重复确认、worker 重试和事件重放不产生重复预留。
14. MTO 接受事件不会通过 DDMRP 重评估再次创建同一需求。
15. MTA Make 确认后生成的预留明确标记 MTA 来源。
16. 统一优先级投影能区分 MTO、MTA 和 DependentDemand。
17. 状态存储重启后恢复全部共享台账和幂等记录。
18. revision 冲突不会留下部分确认结果。
19. 新需求版本生效前，旧活动版本必须被调整、释放或替代，不能同时占用资源。
20. 缺少 DDAE 或 ERP 契约字段时返回结构化门控，不创建默认值。
21. 现有排程、释放、DDMRP、P1 市场控制和 What-if 测试不回归。

## 15. 非目标

- 不在共享基础层实现 MTO 影子排程算法；
- 不在共享基础层实现 DDMRP 净流、BOM 展开或补货量算法；
- 不建立独立 UI 页面；
- 不自动确认订单或补货建议；
- 不修改 DDAE 主设置；
- 不修改 ERP/WMS 库存账；
- 不替代正式 Planning Run；
- 不引入新的生产权威声明；
- 不实现替代料、批次、效期、合批或复杂拆批；
- 不在阶段 0 接入 Simio。
