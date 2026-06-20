const LANGUAGE_STORAGE_KEY = "sdbr.language";
const SCHEDULE_VIEW_STORAGE_KEY = "sdbr.scheduleViews";

const I18N = {
  zh: {
    primaryNavigation: "主导航", planningContext: "计划上下文", toggleNavigation: "切换导航",
    productName: "需求驱动计划员工作台", navOverview: "计划总览", navData: "数据就绪",
    navRuns: "排程任务", navResults: "排程结果", navRelease: "释放管理", navBuffer: "缓冲执行",
    navExceptions: "异常中心", navAdmin: "管理后台", noUnreadExceptions: "无未读异常",
    apiConnected: "本地服务已连接", planningScope: "计划范围", defaultFactory: "默认工厂",
    masterDataVersionLabel: "主数据版本", snapshotLabel: "运行快照", systemHealthLabel: "系统健康",
    notSelected: "未选择", checking: "检查中", healthy: "健康", unavailable: "不可用",
    language: "语言", planner: "计划员", workspaceEyebrow: "计划员工作台",
    pageOverview: "计划总览", pageData: "数据就绪", pageRuns: "排程任务",
    pageResults: "排程结果", pageRelease: "释放管理", pageBuffer: "约束缓冲执行", pageExceptions: "异常中心", pageAdmin: "管理后台",
    descriptionOverview: "集中查看排程上下文、异常和下一步工作。",
    descriptionData: "检查主数据版本与运行状态快照。",
    descriptionRuns: "创建、跟踪和恢复排程任务。",
    descriptionResults: "检查排程结果、负荷、甘特图和诊断。",
    descriptionRelease: "依据绳长、物料、WIP 和缓冲管理工单释放。",
    descriptionBuffer: "按约束缓冲阶段和时间区域协同工单接收与开工。",
    descriptionExceptions: "集中处理失败、死信和执行偏差。",
    descriptionAdmin: "管理主数据、求解器、集成和权限配置。",
    frameworkReady: "页面框架已就绪", emptyTitle: "此功能将在对应验收单元中启用",
    emptyDescription: "当前阶段只建立应用导航、计划上下文和双语基础，不展示模拟生产数据。",
    overallReadiness: "总体就绪状态", loadingData: "正在读取数据状态", loadingDataDescription: "正在检查最新主数据版本与运行状态快照。",
    refresh: "刷新", selectPlanningInputs: "选作本次排程输入", readinessLoadFailed: "无法读取数据就绪状态",
    readinessRetryAdvice: "请检查服务状态后重试，当前页面不会清除已有选择。", masterData: "主数据",
    latestMasterDataVersion: "最新主数据版本", notAvailable: "无可用数据", version: "版本编号", source: "来源",
    createdBy: "创建人", capturedAt: "捕获时间", masterDataCounts: "主数据数量摘要", resources: "资源",
    constraints: "约束", routings: "工艺路线", orders: "工单", inventoryBuffers: "库存缓冲",
    materialRequirements: "物料需求", createNewVersion: "创建新版本", operationalState: "运行状态",
    latestOperationalSnapshot: "最新运行状态快照", snapshot: "快照编号", freshness: "新鲜度",
    operationalStateCounts: "运行状态数量摘要", inventory: "库存", materialAvailability: "物料可用量",
    inbound: "在途", wipScopes: "在制品（WIP）范围", resourceStatuses: "资源状态", dataQuality: "数据质量",
    readinessIssues: "数据问题", noIssues: "没有发现数据问题。", viewIssues: "查看问题", close: "关闭",
    errors: "阻塞问题", warnings: "警告",
    severityError: "错误", severityWarning: "警告", severityInformation: "提示",
    entityMasterDataVersion: "主数据版本", entityOperationalStateSnapshot: "运行状态快照", entityUnknown: "相关数据对象",
    location: "定位", field: "字段", technicalCode: "技术代码",
    statusEmpty: "尚无排程输入", statusBlocked: "数据未就绪", statusReady: "数据已就绪", statusReadyWithWarnings: "数据可用，但需关注",
    guidanceEmpty: "创建主数据版本和运行状态快照后才能开始排程。", guidanceBlocked: "请先解决阻塞问题，再选择本次排程输入。",
    guidanceReady: "最新版本与快照可以用于创建排程。", guidanceReadyWithWarnings: "当前数据可以用于排程，请同时关注警告项。",
    valid: "有效", invalid: "无效", fresh: "新鲜", stale: "已过期", future: "时间异常", notProvided: "未提供",
    issueCount: "个数据问题需要处理", inputsSelected: "已选择为本次排程输入",
    issue_MASTER_DATA_VERSION_MISSING: "尚未创建主数据版本。", issue_OPERATIONAL_STATE_SNAPSHOT_MISSING: "尚未创建运行状态快照。",
    issue_OPERATIONAL_STATE_SNAPSHOT_STALE: "最新运行状态快照已经过期。", issue_OPERATIONAL_STATE_SNAPSHOT_IN_FUTURE: "最新运行状态快照时间晚于当前时间。",
    issue_OPERATIONAL_SOURCE_NOT_PROVIDED: "运行状态快照未提供来源系统。", issue_RESOURCE_STATUS_NOT_CAPTURED: "当前快照尚未包含资源运行状态。",
    caseAcceptanceSummary: "测试案例验收摘要", testSystemCases: "测试系统案例", caseAcceptanceTitle: "案例验收总览",
    caseAcceptanceLoadFailed: "无法读取案例验收摘要", caseAcceptanceRetryAdvice: "请确认测试服务和测试库可用后重试。",
    totalCases: "案例总数", passedCases: "已通过", needsExecutionCases: "待执行", failedCases: "未通过",
    acceptancePassed: "通过", acceptanceNeedsExecution: "待执行", acceptanceFailed: "未通过",
    purpose: "验证目的", releaseReadyCount: "可释放数", blockingCodes: "阻塞代码", openScheduleResult: "打开排程结果",
    runMetrics: "排程任务状态摘要", allRuns: "全部任务", queued: "排队中", running: "运行中", completed: "已完成",
    deadLetter: "死信", pending: "待处理", failed: "失败", cancelled: "已取消", allStatuses: "全部状态",
    status: "状态", requester: "请求人", filterRequester: "筛选请求人", exceptionsOnly: "仅看异常",
    timeRange: "时间范围", allTime: "全部时间", last24Hours: "最近 24 小时", last7Days: "最近 7 天",
    last30Days: "最近 30 天", allSolvers: "全部求解器", startedAt: "开始时间",
    createPlanningRun: "创建排程", runsLoadFailed: "无法读取排程任务", runsRetryAdvice: "请重新加载后再操作。",
    runId: "Run ID", problem: "计划问题", solver: "求解器", requestedAt: "请求时间", duration: "耗时",
    attempts: "尝试", actions: "操作", noPlanningRuns: "尚无排程任务", noPlanningRunsDescription: "选择有效输入后创建第一项排程任务。",
    wizardTitle: "新建 Planning Run", wizardSteps: "创建排程步骤", selectInputs: "选择输入", setPolicy: "设置策略",
    reviewSubmit: "验证并提交", scheduleStart: "计划起点", selectInputsFirst: "请先在数据就绪中心选择有效输入。",
    timeBuffer: "时间缓冲（分钟）", timeLimit: "求解时间限制（秒）", maxAttempts: "最大尝试次数",
    retryDelay: "重试延迟（秒）", pausedUnavailable: "已暂停，暂不可用", enableSimio: "启用 Simio 验证",
    back: "上一步", next: "下一步", submitRun: "提交排程任务", available: "可用", unavailable: "不可用",
    enqueue: "入队", execute: "直接执行", cancel: "取消", recover: "人工恢复", openResults: "查看结果", view: "查看",
    seconds: "秒", notStarted: "未开始", frozenInputs: "冻结输入", solverParameters: "求解参数", workerLease: "Worker 与租约",
    timeline: "状态时间线", diagnostics: "求解诊断", auditEvents: "审计事件", noWorker: "尚未分配 Worker",
    dataUpdated: "数据已更新，请重新加载后再操作。", runCreated: "排程任务已创建", submissionFailed: "排程任务创建失败",
    confirmEnqueue: "确认将此排程任务加入队列？", confirmExecute: "确认立即调用 OR-Tools CP-SAT 执行此排程任务？",
    cancelReasonPrompt: "请输入取消原因。", recoverReasonPrompt: "请输入人工恢复原因。",
    actionFailed: "操作失败，请重新加载后重试。", solverUnavailable: "当前求解器不可用。",
    confirmAction: "确认操作", confirm: "确认", notifySuccess: "操作已完成", notifyError: "操作失败",
    resultContext: "排程结果上下文", planningRun: "排程任务", scheduleResultLoadFailed: "无法读取排程结果",
    scheduleResultRetryAdvice: "请选择已完成的排程任务后重试。", noCompletedSchedules: "尚无已完成的排程结果",
    completeRunFirst: "请先完成一项排程任务。", scheduleKpis: "排程结果指标", onTimeOrders: "准时工单",
    lateOrders: "延迟工单", overloadMinutes: "超载分钟", redBuffers: "红区缓冲", peakLoad: "峰值负荷",
    scheduleResultViews: "排程结果视图", ganttChart: "甘特图", resourceLoad: "资源负荷", orderDelivery: "订单交期",
    resource: "资源", workOrder: "工单", barType: "条带类型", bufferZone: "缓冲区", fromDate: "开始日期",
    toDate: "结束日期", zoom: "缩放", ganttLegend: "甘特图图例", processing: "加工",
    greenBuffer: "绿色时间缓冲", yellowBuffer: "黄色时间缓冲", redBuffer: "红色时间缓冲",
    maintenance: "维护", unavailableTime: "不可用时间",
    loadViews: "负荷视图", systemLoad: "系统负荷", singleResourceLoad: "单资源负荷", resourceType: "资源类型",
    owner: "负责人", category: "类别", date: "日期", loadMinutes: "负荷分钟", availableCapacity: "可用产能",
    utilization: "利用率", released: "已释放", unreleased: "未释放", remainingLoad: "剩余负荷",
    product: "产品", dueDate: "交期", plannedCompletion: "计划完工", delayMinutes: "延迟分钟",
    decisionSupport: "决策支持", scenarioComparison: "方案比较", baselineScenario: "基准方案",
    candidateScenario: "候选方案", compare: "比较", allResources: "全部资源", allOrders: "全部工单",
    allBarTypes: "全部条带", allZones: "全部缓冲区", allOptions: "全部", constraint: "约束资源",
    nonConstraint: "非约束资源", candidateConstraint: "候选约束", noGanttRows: "当前筛选条件下没有甘特任务。",
    noDiagnostics: "求解器未返回诊断信息。", onTime: "准时", late: "延迟", unscheduled: "未排程",
    generatedAt: "生成时间", recommended: "推荐", selectScenario: "采用并送审", selectionReasonPrompt: "请输入采用该方案的原因。",
    selectedForReview: "方案已选择并进入审核。", candidateReducesOverload: "候选方案降低了资源超载。",
    candidateReducesLateOrders: "候选方案减少了延迟工单。", candidateReducesRedBuffers: "候选方案减少了红区缓冲。",
    baselineBetterScore: "基准方案综合得分更优。", candidateBetterScore: "候选方案综合得分更优。",
    planGovernance: "计划治理", publicationGovernance: "计划发布治理", publicationLoadFailed: "无法读取计划发布状态",
    publicationRetryAdvice: "请刷新排程结果后重试。", publicationStatus: "发布状态", scheduleFingerprint: "计划指纹",
    allowedPublicationActions: "允许动作", publicationPackage: "发布包", packageId: "发布包编号", targetSystems: "目标系统",
    publishedBy: "发布人", publishedAt: "发布时间", solverStatus: "求解状态", publicationHistory: "发布历史",
    noPublicationHistory: "尚无发布历史。", supersedesRun: "替代计划", supersededByRun: "被替代方",
    reviewPlan: "提交复核", approvePlan: "批准计划", publishPlan: "发布计划", revokePublication: "撤销发布",
    publicationCommentPrompt: "请输入计划治理备注。", publicationActionCompleted: "计划发布状态已更新。",
    publicationActionDenied: "当前角色或状态不允许执行该计划治理动作。", statusDraft: "草案", statusReviewed: "已复核",
    statusApproved: "已批准", statusPublished: "已发布", statusPublicationRevoked: "已撤销", statusSuperseded: "已被替代",
    statusUnavailable: "不可用", actionReview: "提交复核", actionApprove: "批准计划", actionPublish: "发布计划", actionRevoke: "撤销发布",
    scheduledOrders: "已排程工单", search: "搜索", searchOrders: "搜索工单或产品", releaseStatus: "释放状态",
    groupBy: "分组", noGrouping: "不分组", routing: "工艺路线", savedView: "保存视图", defaultView: "默认视图",
    saveView: "保存当前视图", columns: "列", noneSelected: "未选择工单", lock: "锁定", unlock: "解锁",
    setPriority: "设置优先级", evaluateRelease: "进入释放评估", replan: "重新排程", selectAllOrders: "选择全部工单",
    orderDate: "订单日期", plannedRelease: "计划释放", finalDemandDate: "最终需求日期", promiseDate: "承诺日期",
    onTimeStatus: "准时状态", executionPriority: "执行优先级", orderFamily: "工单族", groupedResources: "分组资源",
    previousPage: "上一页", nextPage: "下一页", rowsPerPage: "每页", viewNamePrompt: "请输入视图名称。",
    priorityPrompt: "请输入优先级（1-999）。", selectedCount: "已选择 {count} 个工单", planCurrent: "当前计划",
    planStale: "已有更新计划", workOrderDetail: "工单详情", operations: "工序", auditHistory: "审计历史",
    releaseContext: "释放评估上下文", evaluatedAt: "评估时间", reevaluate: "重新评估", releaseLoadFailed: "无法读取释放评估",
    releaseRetryAdvice: "请检查已完成计划和运行状态快照。", noReleaseRuns: "没有可评估的已完成计划",
    totalOrders: "工单总数", readyToRelease: "可释放", blocked: "已阻塞", authorized: "已授权",
    penetration: "渗透率", ropeReleaseTime: "绳长释放时间", materialStatus: "物料状态", wipStatus: "WIP 状态",
    plannedStart: "计划开始", blockingReason: "阻塞原因", releaseGate: "释放门控", dispatchPackage: "调度包",
    authorizeRelease: "授权释放", viewDispatch: "查看调度包", viewReason: "查看原因", noBlockReason: "当前没有阻塞原因。",
    snapshotStatus: "快照状态", freshSnapshot: "运行状态快照新鲜", staleSnapshot: "运行状态快照已过期，禁止授权释放",
    futureSnapshot: "运行状态快照时间异常，禁止授权释放", clear: "通过", early: "未到时间", notReleased: "未释放",
    reason_ROPE_TIME_NOT_REACHED: "尚未到达绳长释放时间。", reason_MATERIAL_SHORTAGE: "可用物料不足。",
    reason_MATERIAL_INBOUND_PENDING: "物料仍在途中。", reason_WIP_LIMIT_EXCEEDED: "释放后将超过 WIP 上限。",
    reason_OPERATIONAL_SNAPSHOT_STALE: "运行状态快照已过期。", reason_OPERATIONAL_SNAPSHOT_FUTURE: "运行状态快照时间晚于评估时间。",
    authorizeImpact: "确认授权释放该工单？系统将记录门控快照并生成调度包。", releaseAuthorized: "工单已授权释放。",
    commandRecorded: "工单命令已记录。", pageOf: "第 {page} / {pages} 页",
    bufferContext: "约束缓冲上下文", bufferMatrix: "两阶段五区域缓冲矩阵", bufferLoadFailed: "无法读取缓冲执行看板",
    bufferRetryAdvice: "请选择包含已授权工单的已完成计划。", noBufferRuns: "没有可用的已完成计划", bufferOwner: "缓冲负责人",
    dailyLoad: "当日总负荷", lastScheduled: "最近排程时间", hours: "小时", yetToBeReceived: "待接收", received: "已接收",
    Early: "提前", Green: "绿区", Yellow: "黄区", Red: "红区", Late: "逾期", orderCount: "工单数", totalLoad: "总负荷",
    bufferOrderDetail: "缓冲工单详情", customer: "客户", currentReason: "当前原因", receiveStatus: "接收状态",
    executionTransaction: "执行事务", eventType: "事件类型", arrivedBuffer: "到达缓冲", startedOperation: "开始加工", eventAt: "事件时间",
    measureType: "记录方式", measureValue: "记录值", reasonCode: "原因码", selectReason: "请选择原因码", recordTransaction: "记录事务",
    reasonRequiredForLate: "Late 区事务必须选择标准原因码。", Quantity: "数量", CompletionPercent: "完成百分比", Hours: "工时",
    transactionRecorded: "执行事务已记录。", receiveOrStart: "接收 / 开工", reason_MATERIAL_SHORTAGE_CODE: "缺料",
    reason_EQUIPMENT_DOWN_CODE: "设备故障", reason_STAFF_ABSENCE_CODE: "人员缺勤", reason_QUALITY_REWORK_CODE: "质量返工",
    exceptionContext: "异常中心上下文", severity: "严重程度", exceptionLoadFailed: "无法读取异常中心", exceptionRetryAdvice: "请确认服务可用后重试。",
    totalExceptions: "异常总数", criticalExceptions: "严重", warningExceptions: "警告", openExceptions: "未处理", object: "对象", occurredAt: "发生时间",
    businessImpact: "业务影响", suggestedAction: "建议动作", exceptionDetail: "异常详情", allSeverities: "全部严重程度", allSources: "全部来源",
    Critical: "严重", Warning: "警告", Information: "提示", impact_ScheduleUnavailable: "排程结果不可用", impact_ConstraintMayStarve: "约束可能断料",
    impact_ExecutionThreatensSchedule: "执行偏差威胁计划", impact_ScheduleStabilityAtRisk: "计划稳定性存在风险",
    action_RecoverPlanningRun: "恢复排程任务", action_ReviewPlanningRunFailure: "复核失败任务", action_ExpediteConstraintBuffer: "催办约束缓冲",
    action_ReviewExecutionAlert: "处理执行预警", action_ReviewReplanRequest: "审核重排建议", viewDetail: "查看详情", relatedObjects: "关联对象", resolutionActions: "处理动作",
    auditTrail: "审计历史", noAuditTrail: "没有审计记录", type_PlanningRunDeadLetter: "排程死信", type_PlanningRunFailed: "排程失败", type_ConstraintBufferRisk: "约束缓冲风险",
    type_ExecutionAlert: "执行预警", type_ReplanSuggestion: "重排建议",
    administrationContext: "管理后台上下文", sensitiveSettingsReadOnly: "敏感连接参数当前只读。", administrationLoadFailed: "无法读取管理后台",
    administrationRetryAdvice: "请确认本地服务可用后重试。", adminMasterDataTitle: "主数据后台", importPreview: "导入预览",
    importPreviewDescription: "选择对象后先查看结构化预览和预校验结果，再生成主数据版本。", importFile: "导入文件", preValidate: "预校验",
    generateVersion: "生成版本", routingImport: "导入工艺路线", noImportSelected: "尚未选择导入对象", rawJsonHidden: "原始 JSON 默认隐藏，仅管理员调试模式可查看。",
    adminSystemTitle: "集成与求解器设置", policyConfiguration: "排程策略配置", calendar: "日历", calendarLayers: "资源日历四层",
    readOnly: "只读", objectCount: "当前数量", importEndpoint: "导入接口", reservedFields: "预留字段", structuredPreview: "结构化预览",
    preValidationRequired: "导入前预校验", versionAfterImport: "导入后生成版本", capabilityStatus: "能力状态", lastSync: "最近同步",
    workerQueue: "Worker 队列", stateStore: "状态存储", DayDefinition: "日定义", WeekDefinition: "周定义", TemporaryShiftOverride: "临时班次覆盖",
    ExclusionOrMaintenance: "排除/维护修改", RateInterpretation: "速率解释方式", Units: "单位", SchedulingWindow: "排程窗口",
    BufferBoundaries: "缓冲区边界比例", PiecesPerHour: "件/小时", HoursPerPiece: "小时/件", MinutesPerPiece: "分钟/件",
    BufferMinutes: "缓冲分钟", SetupMinutes: "换型分钟", DurationMinutes: "持续分钟", FixedOffsetMinutes: "固定偏移分钟",
    WindowStart: "窗口起点", PreferredCompletionTime: "首选完工时间", ShipmentCutoffRule: "发货截止规则", GreenRatio: "绿区比例",
    YellowRatio: "黄区比例", RedRatio: "红区比例", NotConfigured: "未配置", Paused: "已暂停", Available: "可用", Unavailable: "不可用",
    Idle: "空闲", Online: "在线", Healthy: "健康", Unhealthy: "异常"
  },
  en: {
    primaryNavigation: "Primary navigation", planningContext: "Planning context", toggleNavigation: "Toggle navigation",
    productName: "Demand-Driven Planner Workbench", navOverview: "Planning Overview", navData: "Data Readiness",
    navRuns: "Planning Runs", navResults: "Schedule Results", navRelease: "Release Management", navBuffer: "Buffer Execution",
    navExceptions: "Exceptions", navAdmin: "Administration", noUnreadExceptions: "No unread exceptions",
    apiConnected: "Local service connected", planningScope: "Planning scope", defaultFactory: "Default factory",
    masterDataVersionLabel: "Master data version", snapshotLabel: "Operational snapshot", systemHealthLabel: "System health",
    notSelected: "Not selected", checking: "Checking", healthy: "Healthy", unavailable: "Unavailable",
    language: "Language", planner: "Planner", workspaceEyebrow: "Planner Workbench",
    pageOverview: "Planning Overview", pageData: "Data Readiness", pageRuns: "Planning Runs",
    pageResults: "Schedule Results", pageRelease: "Release Management", pageBuffer: "Constraint Buffer Execution", pageExceptions: "Exceptions", pageAdmin: "Administration",
    descriptionOverview: "Review planning context, exceptions, and the next work to perform.",
    descriptionData: "Check master data versions and operational snapshots.",
    descriptionRuns: "Create, track, and recover planning runs.",
    descriptionResults: "Inspect schedules, load, Gantt views, and diagnostics.",
    descriptionRelease: "Control release using rope time, material, WIP, and buffers.",
    descriptionBuffer: "Coordinate order receipt and start by constraint-buffer stage and time zone.",
    descriptionExceptions: "Handle failures, dead letters, and execution variance.",
    descriptionAdmin: "Manage master data, solvers, integrations, and access.",
    frameworkReady: "Page framework ready", emptyTitle: "This capability will open in its acceptance unit",
    emptyDescription: "This phase establishes navigation, planning context, and bilingual foundations without fabricated production data.",
    overallReadiness: "Overall readiness", loadingData: "Loading data status", loadingDataDescription: "Checking the latest master data version and operational snapshot.",
    refresh: "Refresh", selectPlanningInputs: "Use as planning inputs", readinessLoadFailed: "Data readiness could not be loaded",
    readinessRetryAdvice: "Check the service and retry. Existing selections will not be cleared.", masterData: "Master data",
    latestMasterDataVersion: "Latest Master Data Version", notAvailable: "Not available", version: "Version", source: "Source",
    createdBy: "Created by", capturedAt: "Captured at", masterDataCounts: "Master data counts", resources: "Resources",
    constraints: "Constraints", routings: "Routings", orders: "Work orders", inventoryBuffers: "Inventory buffers",
    materialRequirements: "Material requirements", createNewVersion: "Create new version", operationalState: "Operational state",
    latestOperationalSnapshot: "Latest Operational State Snapshot", snapshot: "Snapshot", freshness: "Freshness",
    operationalStateCounts: "Operational state counts", inventory: "Inventory", materialAvailability: "Material availability",
    inbound: "Inbound", wipScopes: "WIP scopes", resourceStatuses: "Resource statuses", dataQuality: "Data quality",
    readinessIssues: "Data issues", noIssues: "No data issues found.", viewIssues: "View issues", close: "Close",
    errors: "Blocking issues", warnings: "Warnings",
    severityError: "Error", severityWarning: "Warning", severityInformation: "Information",
    entityMasterDataVersion: "Master data version", entityOperationalStateSnapshot: "Operational state snapshot", entityUnknown: "Related data object",
    location: "Location", field: "Field", technicalCode: "Technical code",
    statusEmpty: "No planning inputs", statusBlocked: "Data not ready", statusReady: "Data ready", statusReadyWithWarnings: "Data usable with warnings",
    guidanceEmpty: "Create a master data version and operational snapshot before planning.", guidanceBlocked: "Resolve blocking issues before selecting planning inputs.",
    guidanceReady: "The latest version and snapshot can be used for planning.", guidanceReadyWithWarnings: "The data can be used for planning; review the warnings as well.",
    valid: "Valid", invalid: "Invalid", fresh: "Fresh", stale: "Stale", future: "Time mismatch", notProvided: "Not provided",
    issueCount: "data issues require attention", inputsSelected: "Selected as planning inputs",
    issue_MASTER_DATA_VERSION_MISSING: "No master data version has been created.", issue_OPERATIONAL_STATE_SNAPSHOT_MISSING: "No operational state snapshot has been created.",
    issue_OPERATIONAL_STATE_SNAPSHOT_STALE: "The latest operational snapshot is stale.", issue_OPERATIONAL_STATE_SNAPSHOT_IN_FUTURE: "The latest operational snapshot is dated after the evaluation time.",
    issue_OPERATIONAL_SOURCE_NOT_PROVIDED: "The operational snapshot has no source system.", issue_RESOURCE_STATUS_NOT_CAPTURED: "The current snapshot does not include resource runtime status.",
    caseAcceptanceSummary: "Test case acceptance summary", testSystemCases: "Test system cases", caseAcceptanceTitle: "Case Acceptance Overview",
    caseAcceptanceLoadFailed: "Case acceptance summary could not be loaded", caseAcceptanceRetryAdvice: "Check that the test service and test database are available.",
    totalCases: "Total cases", passedCases: "Passed", needsExecutionCases: "Needs execution", failedCases: "Failed",
    acceptancePassed: "Passed", acceptanceNeedsExecution: "Needs execution", acceptanceFailed: "Failed",
    purpose: "Purpose", releaseReadyCount: "Ready releases", blockingCodes: "Blocking codes", openScheduleResult: "Open schedule result",
    runMetrics: "Planning run status summary", allRuns: "All runs", queued: "Queued", running: "Running", completed: "Completed",
    deadLetter: "Dead letter", pending: "Pending", failed: "Failed", cancelled: "Cancelled", allStatuses: "All statuses",
    status: "Status", requester: "Requester", filterRequester: "Filter requester", exceptionsOnly: "Exceptions only",
    timeRange: "Time range", allTime: "All time", last24Hours: "Last 24 hours", last7Days: "Last 7 days",
    last30Days: "Last 30 days", allSolvers: "All solvers", startedAt: "Started at",
    createPlanningRun: "Create planning run", runsLoadFailed: "Planning runs could not be loaded", runsRetryAdvice: "Reload before trying the operation again.",
    runId: "Run ID", problem: "Planning problem", solver: "Solver", requestedAt: "Requested at", duration: "Duration",
    attempts: "Attempts", actions: "Actions", noPlanningRuns: "No planning runs", noPlanningRunsDescription: "Select valid inputs and create the first planning run.",
    wizardTitle: "New Planning Run", wizardSteps: "Create planning run steps", selectInputs: "Select inputs", setPolicy: "Set policy",
    reviewSubmit: "Review and submit", scheduleStart: "Schedule start", selectInputsFirst: "Select valid inputs in Data Readiness first.",
    timeBuffer: "Time buffer (minutes)", timeLimit: "Solver time limit (seconds)", maxAttempts: "Maximum attempts",
    retryDelay: "Retry delay (seconds)", pausedUnavailable: "Paused and unavailable", enableSimio: "Enable Simio validation",
    back: "Back", next: "Next", submitRun: "Submit planning run", available: "Available", unavailable: "Unavailable",
    enqueue: "Enqueue", execute: "Execute now", cancel: "Cancel", recover: "Recover", openResults: "Open results", view: "View",
    seconds: "sec", notStarted: "Not started", frozenInputs: "Frozen inputs", solverParameters: "Solver parameters", workerLease: "Worker and lease",
    timeline: "Status timeline", diagnostics: "Solver diagnostics", auditEvents: "Audit events", noWorker: "No worker assigned",
    dataUpdated: "Data was updated. Reload before trying again.", runCreated: "Planning run created", submissionFailed: "Planning run creation failed",
    confirmEnqueue: "Enqueue this planning run?", confirmExecute: "Run this planning task with OR-Tools CP-SAT now?",
    cancelReasonPrompt: "Enter a cancellation reason.", recoverReasonPrompt: "Enter a recovery reason.",
    actionFailed: "The operation failed. Reload and try again.", solverUnavailable: "The selected solver is unavailable.",
    confirmAction: "Confirm action", confirm: "Confirm", notifySuccess: "Action completed", notifyError: "Action failed",
    resultContext: "Schedule result context", planningRun: "Planning run", scheduleResultLoadFailed: "Schedule result could not be loaded",
    scheduleResultRetryAdvice: "Select a completed planning run and retry.", noCompletedSchedules: "No completed schedule results",
    completeRunFirst: "Complete a planning run first.", scheduleKpis: "Schedule result metrics", onTimeOrders: "On-time orders",
    lateOrders: "Late orders", overloadMinutes: "Overload minutes", redBuffers: "Red buffers", peakLoad: "Peak load",
    scheduleResultViews: "Schedule result views", ganttChart: "Gantt chart", resourceLoad: "Resource load", orderDelivery: "Order delivery",
    resource: "Resource", workOrder: "Work order", barType: "Bar type", bufferZone: "Buffer zone", fromDate: "From date",
    toDate: "To date", zoom: "Zoom", ganttLegend: "Gantt legend", processing: "Processing",
    greenBuffer: "Green time buffer", yellowBuffer: "Yellow time buffer", redBuffer: "Red time buffer",
    maintenance: "Maintenance", unavailableTime: "Unavailable time",
    loadViews: "Load views", systemLoad: "System load", singleResourceLoad: "Single resource load", resourceType: "Resource type",
    owner: "Owner", category: "Category", date: "Date", loadMinutes: "Load minutes", availableCapacity: "Available capacity",
    utilization: "Utilization", released: "Released", unreleased: "Unreleased", remainingLoad: "Remaining load",
    product: "Product", dueDate: "Due date", plannedCompletion: "Planned completion", delayMinutes: "Delay minutes",
    decisionSupport: "Decision support", scenarioComparison: "Scenario comparison", baselineScenario: "Baseline",
    candidateScenario: "Candidate", compare: "Compare", allResources: "All resources", allOrders: "All orders",
    allBarTypes: "All bar types", allZones: "All zones", allOptions: "All", constraint: "Constraint",
    nonConstraint: "Non-constraint", candidateConstraint: "Candidate constraint", noGanttRows: "No Gantt tasks match the current filters.",
    noDiagnostics: "The solver returned no diagnostics.", onTime: "On time", late: "Late", unscheduled: "Unscheduled",
    generatedAt: "Generated at", recommended: "Recommended", selectScenario: "Select for review", selectionReasonPrompt: "Enter the reason for selecting this scenario.",
    selectedForReview: "Scenario selected for review.", candidateReducesOverload: "Candidate reduces resource overload.",
    candidateReducesLateOrders: "Candidate reduces late orders.", candidateReducesRedBuffers: "Candidate reduces red buffers.",
    baselineBetterScore: "Baseline has the better overall score.", candidateBetterScore: "Candidate has the better overall score.",
    planGovernance: "Plan governance", publicationGovernance: "Plan publication governance", publicationLoadFailed: "Plan publication status could not be loaded",
    publicationRetryAdvice: "Refresh the schedule result and retry.", publicationStatus: "Publication status", scheduleFingerprint: "Schedule fingerprint",
    allowedPublicationActions: "Allowed actions", publicationPackage: "Publication package", packageId: "Package ID", targetSystems: "Target systems",
    publishedBy: "Published by", publishedAt: "Published at", solverStatus: "Solver status", publicationHistory: "Publication history",
    noPublicationHistory: "No publication history yet.", supersedesRun: "Supersedes run", supersededByRun: "Superseded by",
    reviewPlan: "Submit for review", approvePlan: "Approve plan", publishPlan: "Publish plan", revokePublication: "Revoke publication",
    publicationCommentPrompt: "Enter a plan-governance comment.", publicationActionCompleted: "Plan publication status updated.",
    publicationActionDenied: "The current role or status does not allow this plan-governance action.", statusDraft: "Draft", statusReviewed: "Reviewed",
    statusApproved: "Approved", statusPublished: "Published", statusPublicationRevoked: "Revoked", statusSuperseded: "Superseded",
    statusUnavailable: "Unavailable", actionReview: "Submit for review", actionApprove: "Approve plan", actionPublish: "Publish plan", actionRevoke: "Revoke publication",
    scheduledOrders: "Scheduled orders", search: "Search", searchOrders: "Search order or product", releaseStatus: "Release status",
    groupBy: "Group by", noGrouping: "No grouping", routing: "Routing", savedView: "Saved view", defaultView: "Default view",
    saveView: "Save current view", columns: "Columns", noneSelected: "No orders selected", lock: "Lock", unlock: "Unlock",
    setPriority: "Set priority", evaluateRelease: "Evaluate release", replan: "Replan", selectAllOrders: "Select all orders",
    orderDate: "Order date", plannedRelease: "Planned release", finalDemandDate: "Final demand date", promiseDate: "Promise date",
    onTimeStatus: "On-time status", executionPriority: "Execution priority", orderFamily: "Order family", groupedResources: "Resource group",
    previousPage: "Previous", nextPage: "Next", rowsPerPage: "Rows per page", viewNamePrompt: "Enter a view name.",
    priorityPrompt: "Enter a priority from 1 to 999.", selectedCount: "{count} orders selected", planCurrent: "Current plan",
    planStale: "Newer plan available", workOrderDetail: "Work order detail", operations: "Operations", auditHistory: "Audit history",
    releaseContext: "Release evaluation context", evaluatedAt: "Evaluated at", reevaluate: "Re-evaluate", releaseLoadFailed: "Release evaluation could not be loaded",
    releaseRetryAdvice: "Check the completed plan and operational snapshot.", noReleaseRuns: "No completed plan is available for evaluation",
    totalOrders: "Total orders", readyToRelease: "Ready", blocked: "Blocked", authorized: "Authorized",
    penetration: "Penetration", ropeReleaseTime: "Rope release time", materialStatus: "Material status", wipStatus: "WIP status",
    plannedStart: "Planned start", blockingReason: "Blocking reason", releaseGate: "Release gate", dispatchPackage: "Dispatch package",
    authorizeRelease: "Authorize release", viewDispatch: "View dispatch", viewReason: "View reason", noBlockReason: "No blocking reasons.",
    snapshotStatus: "Snapshot status", freshSnapshot: "Operational snapshot is fresh", staleSnapshot: "Operational snapshot is stale; authorization is blocked",
    futureSnapshot: "Operational snapshot is from the future; authorization is blocked", clear: "Clear", early: "Early", notReleased: "Not released",
    reason_ROPE_TIME_NOT_REACHED: "Rope release time has not been reached.", reason_MATERIAL_SHORTAGE: "Available material is insufficient.",
    reason_MATERIAL_INBOUND_PENDING: "Required material is still inbound.", reason_WIP_LIMIT_EXCEEDED: "Release would exceed the WIP limit.",
    reason_OPERATIONAL_SNAPSHOT_STALE: "The operational snapshot is stale.", reason_OPERATIONAL_SNAPSHOT_FUTURE: "The operational snapshot is later than the evaluation time.",
    authorizeImpact: "Authorize this work order? The gate snapshot will be audited and a dispatch package generated.", releaseAuthorized: "Work order release authorized.",
    commandRecorded: "Work order command recorded.", pageOf: "Page {page} of {pages}",
    bufferContext: "Constraint buffer context", bufferMatrix: "Two-stage five-zone buffer matrix", bufferLoadFailed: "Buffer execution board could not be loaded",
    bufferRetryAdvice: "Select a completed plan containing authorized orders.", noBufferRuns: "No completed plan is available", bufferOwner: "Buffer owner",
    dailyLoad: "Daily load", lastScheduled: "Last scheduled", hours: "hours", yetToBeReceived: "Yet to be received", received: "Received",
    Early: "Early", Green: "Green", Yellow: "Yellow", Red: "Red", Late: "Late", orderCount: "Orders", totalLoad: "Total load",
    bufferOrderDetail: "Buffer order detail", customer: "Customer", currentReason: "Current reason", receiveStatus: "Receipt status",
    executionTransaction: "Execution transaction", eventType: "Event type", arrivedBuffer: "Arrived at buffer", startedOperation: "Started operation", eventAt: "Event time",
    measureType: "Measure type", measureValue: "Measure value", reasonCode: "Reason code", selectReason: "Select a reason code", recordTransaction: "Record transaction",
    reasonRequiredForLate: "Late-zone transactions require a standard reason code.", Quantity: "Quantity", CompletionPercent: "Completion percent", Hours: "Hours",
    transactionRecorded: "Execution transaction recorded.", receiveOrStart: "Receive / Start", reason_MATERIAL_SHORTAGE_CODE: "Material shortage",
    reason_EQUIPMENT_DOWN_CODE: "Equipment down", reason_STAFF_ABSENCE_CODE: "Staff absence", reason_QUALITY_REWORK_CODE: "Quality rework",
    exceptionContext: "Exception center context", severity: "Severity", exceptionLoadFailed: "Exception center could not be loaded", exceptionRetryAdvice: "Check the service and retry.",
    totalExceptions: "Total exceptions", criticalExceptions: "Critical", warningExceptions: "Warnings", openExceptions: "Open", object: "Object", occurredAt: "Occurred at",
    businessImpact: "Business impact", suggestedAction: "Suggested action", exceptionDetail: "Exception detail", allSeverities: "All severities", allSources: "All sources",
    Critical: "Critical", Warning: "Warning", Information: "Information", impact_ScheduleUnavailable: "Schedule output unavailable", impact_ConstraintMayStarve: "Constraint may starve",
    impact_ExecutionThreatensSchedule: "Execution variance threatens the schedule", impact_ScheduleStabilityAtRisk: "Schedule stability is at risk",
    action_RecoverPlanningRun: "Recover planning run", action_ReviewPlanningRunFailure: "Review failed run", action_ExpediteConstraintBuffer: "Expedite constraint buffer",
    action_ReviewExecutionAlert: "Handle execution alert", action_ReviewReplanRequest: "Review replan request", viewDetail: "View detail", relatedObjects: "Related objects", resolutionActions: "Resolution actions",
    auditTrail: "Audit trail", noAuditTrail: "No audit trail", type_PlanningRunDeadLetter: "Planning run dead letter", type_PlanningRunFailed: "Planning run failed", type_ConstraintBufferRisk: "Constraint buffer risk",
    type_ExecutionAlert: "Execution alert", type_ReplanSuggestion: "Replan suggestion",
    administrationContext: "Administration context", sensitiveSettingsReadOnly: "Sensitive connection parameters are read-only.", administrationLoadFailed: "Administration could not be loaded",
    administrationRetryAdvice: "Check the local service and retry.", adminMasterDataTitle: "Master Data Administration", importPreview: "Import preview",
    importPreviewDescription: "Select an object, review structured preview and pre-validation, then generate a master data version.", importFile: "Import file", preValidate: "Pre-validate",
    generateVersion: "Generate version", routingImport: "Import routings", noImportSelected: "No import object selected", rawJsonHidden: "Raw JSON is hidden by default and available only in administrator debug mode.",
    adminSystemTitle: "Integration and Solver Settings", policyConfiguration: "Scheduling policy configuration", calendar: "Calendar", calendarLayers: "Four resource-calendar layers",
    readOnly: "Read-only", objectCount: "Current count", importEndpoint: "Import endpoint", reservedFields: "Reserved fields", structuredPreview: "Structured preview",
    preValidationRequired: "Pre-validation before import", versionAfterImport: "Version after import", capabilityStatus: "Capability status", lastSync: "Last sync",
    workerQueue: "Worker queue", stateStore: "State store", DayDefinition: "Day definition", WeekDefinition: "Week definition", TemporaryShiftOverride: "Temporary shift override",
    ExclusionOrMaintenance: "Exclusion or maintenance change", RateInterpretation: "Rate interpretation", Units: "Units", SchedulingWindow: "Scheduling window",
    BufferBoundaries: "Buffer boundary ratios", PiecesPerHour: "Pieces/hour", HoursPerPiece: "Hours/piece", MinutesPerPiece: "Minutes/piece",
    BufferMinutes: "Buffer minutes", SetupMinutes: "Setup minutes", DurationMinutes: "Duration minutes", FixedOffsetMinutes: "Fixed offset minutes",
    WindowStart: "Window start", PreferredCompletionTime: "Preferred completion time", ShipmentCutoffRule: "Shipment cutoff rule", GreenRatio: "Green ratio",
    YellowRatio: "Yellow ratio", RedRatio: "Red ratio", NotConfigured: "Not configured", Paused: "Paused", Available: "Available", Unavailable: "Unavailable",
    Idle: "Idle", Online: "Online", Healthy: "Healthy", Unhealthy: "Unhealthy"
  }
};

const ROUTES = {
  overview: ["pageOverview", "descriptionOverview"],
  "data-readiness": ["pageData", "descriptionData"],
  "planning-runs": ["pageRuns", "descriptionRuns"],
  "schedule-results": ["pageResults", "descriptionResults"],
  "release-management": ["pageRelease", "descriptionRelease"],
  "buffer-board": ["pageBuffer", "descriptionBuffer"],
  exceptions: ["pageExceptions", "descriptionExceptions"],
  administration: ["pageAdmin", "descriptionAdmin"]
};

let currentLanguage = "zh";
let caseAcceptanceData = null;
let dataReadiness = null;
let planningRunWorkbench = null;
let planningRunWizardStep = 1;
let scheduleResultData = null;
let scheduleResultRuns = [];
let selectedScheduleRunID = null;
let planPublicationData = null;
let activeScheduleTab = "gantt";
let scheduledOrdersData = null;
let scheduledOrdersPage = 1;
let scheduledOrdersSort = { key: "PlannedStartAt", direction: "asc" };
let selectedScheduledOrderIDs = new Set();
let visibleScheduledOrderColumns = new Set(["OrderID", "ProductID", "PlannedReleaseAt", "PromiseDate", "OnTimeStatus", "ReleaseStatus", "ExecutionPriority", "RoutingID", "ResourceIDs"]);
let releaseManagementData = null;
let selectedReleaseRunID = null;
let bufferBoardData = null;
let selectedBufferRunID = null;
let selectedBufferOrder = null;
let exceptionCenterData = null;
let administrationData = null;

function translate(key) {
  return I18N[currentLanguage][key] || I18N.en[key] || key;
}

function translateWith(key, values) {
  return Object.entries(values).reduce((text, [name, value]) => text.replace(`{${name}}`, String(value)), translate(key));
}

function storedLanguage() {
  try {
    const value = localStorage.getItem(LANGUAGE_STORAGE_KEY);
    return value === "en" ? "en" : "zh";
  } catch (_error) {
    return "zh";
  }
}

function persistLanguage(language) {
  try {
    localStorage.setItem(LANGUAGE_STORAGE_KEY, language);
  } catch (_error) {
    // The workbench still functions when storage is unavailable.
  }
}

function applyLanguage(language) {
  currentLanguage = language === "en" ? "en" : "zh";
  document.documentElement.lang = currentLanguage === "zh" ? "zh-CN" : "en";
  document.querySelectorAll("[data-i18n]").forEach((element) => {
    element.textContent = translate(element.dataset.i18n);
  });
  document.querySelectorAll("[data-i18n-aria-label]").forEach((element) => {
    element.setAttribute("aria-label", translate(element.dataset.i18nAriaLabel));
  });
  document.querySelectorAll("[data-i18n-title]").forEach((element) => {
    element.setAttribute("title", translate(element.dataset.i18nTitle));
  });
  document.getElementById("language-select").value = currentLanguage;
  renderRoute();
}

function currentRoute() {
  const route = window.location.hash.replace(/^#/, "");
  return Object.hasOwn(ROUTES, route) ? route : "overview";
}

function renderRoute(focusWorkspace = false) {
  const route = currentRoute();
  const [titleKey, descriptionKey] = ROUTES[route];
  document.getElementById("page-title").textContent = translate(titleKey);
  document.getElementById("page-description").textContent = translate(descriptionKey);
  document.querySelectorAll("[data-route]").forEach((link) => {
    const active = link.dataset.route === route;
    link.classList.toggle("is-active", active);
    if (active) link.setAttribute("aria-current", "page");
    else link.removeAttribute("aria-current");
  });
  const isDataReadiness = route === "data-readiness";
  const isOverview = route === "overview";
  const isPlanningRuns = route === "planning-runs";
  const isScheduleResults = route === "schedule-results";
  const isReleaseManagement = route === "release-management";
  const isBufferBoard = route === "buffer-board";
  const isExceptions = route === "exceptions";
  const isAdministration = route === "administration";
  document.getElementById("generic-workspace").hidden = isOverview || isDataReadiness || isPlanningRuns || isScheduleResults || isReleaseManagement || isBufferBoard || isExceptions || isAdministration;
  document.getElementById("overview-view").hidden = !isOverview;
  document.getElementById("data-readiness-view").hidden = !isDataReadiness;
  document.getElementById("planning-runs-view").hidden = !isPlanningRuns;
  document.getElementById("schedule-results-view").hidden = !isScheduleResults;
  document.getElementById("release-management-view").hidden = !isReleaseManagement;
  document.getElementById("buffer-board-view").hidden = !isBufferBoard;
  document.getElementById("exceptions-view").hidden = !isExceptions;
  document.getElementById("administration-view").hidden = !isAdministration;
  if (isOverview) loadCaseAcceptance();
  if (isDataReadiness) loadDataReadiness();
  if (isPlanningRuns) loadPlanningRuns();
  if (isScheduleResults) loadScheduleResultRuns();
  if (isReleaseManagement) loadReleaseManagementRuns();
  if (isBufferBoard) loadBufferBoardRuns();
  if (isExceptions) loadExceptionCenter();
  if (isAdministration) loadAdministration();
  closeMobileNavigation();
  if (focusWorkspace) {
    document.getElementById("workspace").focus({ preventScroll: true });
  }
}

function setText(id, value) {
  document.getElementById(id).textContent = value ?? "-";
}

function displayValue(value) {
  return value === null || value === undefined || value === "" ? translate("notProvided") : String(value);
}

function formatDate(value) {
  if (!value) return "-";
  return new Intl.DateTimeFormat(currentLanguage === "zh" ? "zh-CN" : "en-US", {
    dateStyle: "medium", timeStyle: "short"
  }).format(new Date(value));
}

function setStatusChip(element, text, state) {
  element.textContent = text;
  element.className = `status-chip ${state}`;
  element.dataset.qualityComponent = "status-chip";
}

function showNotification(message, tone = "success") {
  const region = document.getElementById("notification-region");
  const item = document.createElement("div");
  item.className = `notification-item ${tone}`;
  item.textContent = message || translate(tone === "error" ? "notifyError" : "notifySuccess");
  region.append(item);
  if (tone !== "error") {
    window.setTimeout(() => item.remove(), 3600);
  }
}

function confirmAction({ message, context = "" }) {
  return new Promise((resolve) => {
    const dialog = document.getElementById("action-confirm-dialog");
    setText("confirm-action-impact", message);
    setText("confirm-action-context", context);
    const accept = document.getElementById("confirm-action-accept");
    const cancel = document.getElementById("confirm-action-cancel");
    const cleanup = (result) => {
      accept.removeEventListener("click", onAccept);
      cancel.removeEventListener("click", onCancel);
      dialog.removeEventListener("close", onClose);
      if (dialog.open) dialog.close();
      resolve(result);
    };
    const onAccept = () => cleanup(true);
    const onCancel = () => cleanup(false);
    const onClose = () => cleanup(false);
    accept.addEventListener("click", onAccept);
    cancel.addEventListener("click", onCancel);
    dialog.addEventListener("close", onClose);
    dialog.showModal();
  });
}

function renderSummary(containerId, summary) {
  document.querySelectorAll(`#${containerId} [data-metric]`).forEach((element) => {
    const value = summary ? summary[element.dataset.metric] : null;
    element.textContent = value === null || value === undefined ? "-" : String(value);
  });
}

async function loadCaseAcceptance() {
  try {
    const response = await fetch("/planner/workbench/test-data/acceptance", { headers: { Accept: "application/json" } });
    if (!response.ok) throw new Error(String(response.status));
    caseAcceptanceData = (await response.json()).Data;
    renderCaseAcceptance();
    document.getElementById("case-acceptance-error").hidden = true;
    document.getElementById("case-acceptance-content").hidden = false;
  } catch (_error) {
    document.getElementById("case-acceptance-error").hidden = false;
    document.getElementById("case-acceptance-content").hidden = true;
  }
}

function acceptanceStatusLabel(status) {
  return translate({
    Passed: "acceptancePassed", NeedsExecution: "acceptanceNeedsExecution", Failed: "acceptanceFailed"
  }[status] || "notAvailable");
}

function acceptanceStatusClass(status) {
  if (status === "Passed") return "is-valid";
  if (status === "NeedsExecution") return "is-warning";
  return "is-invalid";
}

function renderCaseAcceptance() {
  if (!caseAcceptanceData) return;
  setText("case-acceptance-evaluated-at", `${translate("evaluatedAt")}: ${formatDate(caseAcceptanceData.EvaluatedAt)}`);
  document.querySelectorAll("[data-case-summary]").forEach((element) => {
    const key = element.dataset.caseSummary;
    element.textContent = caseAcceptanceData.Summary?.[key] ?? 0;
  });
  const container = document.getElementById("case-acceptance-cards");
  container.replaceChildren();
  (caseAcceptanceData.Cases || []).forEach((caseItem) => {
    const card = document.createElement("section");
    card.className = "case-card";
    const heading = document.createElement("div");
    heading.className = "panel-heading";
    const titleWrap = document.createElement("div");
    const kicker = document.createElement("span");
    kicker.className = "panel-kicker";
    kicker.textContent = caseItem.CaseID;
    const title = document.createElement("h2");
    title.textContent = currentLanguage === "zh" ? caseItem.NameZh : caseItem.NameEn;
    titleWrap.append(kicker, title);
    const chip = document.createElement("span");
    setStatusChip(chip, acceptanceStatusLabel(caseItem.AcceptanceStatus), acceptanceStatusClass(caseItem.AcceptanceStatus));
    heading.append(titleWrap, chip);
    const purpose = document.createElement("p");
    purpose.textContent = currentLanguage === "zh" ? caseItem.PurposeZh : caseItem.NameEn;
    const actual = caseItem.Actual || {};
    const release = actual.Release || {};
    const releaseSummary = release.Summary || {};
    const meta = document.createElement("div");
    meta.className = "case-card-meta";
    [
      ["planningRun", caseItem.PlanningRunID],
      ["status", statusLabel(actual.PlanningRunStatus)],
      ["solver", `${displayValue(actual.SolverBackendID)} / ${displayValue(actual.SolverStatus)}`],
      ["publicationStatus", publicationStatusLabel(actual.PublicationStatus)],
      ["releaseReadyCount", releaseSummary.ReadyCount ?? "-"],
      ["blockingCodes", (release.BlockingCodes || []).join(", ") || translate("clear")]
    ].forEach(([labelKey, value]) => {
      const item = document.createElement("div");
      const label = document.createElement("span");
      label.textContent = translate(labelKey);
      const strong = document.createElement("strong");
      strong.textContent = value ?? "-";
      item.append(label, strong);
      meta.append(item);
    });
    const actions = document.createElement("div");
    actions.className = "case-card-actions";
    const open = document.createElement("button");
    open.type = "button";
    open.className = "button secondary";
    open.textContent = translate("openScheduleResult");
    open.disabled = actual.PlanningRunStatus !== "Completed";
    open.addEventListener("click", () => {
      selectedScheduleRunID = caseItem.PlanningRunID;
      window.location.hash = "schedule-results";
    });
    actions.append(open);
    card.append(heading, purpose, meta, actions);
    container.append(card);
  });
}

function readinessStatusCopy(status) {
  return {
    Empty: ["statusEmpty", "guidanceEmpty", "is-blocked"],
    Blocked: ["statusBlocked", "guidanceBlocked", "is-blocked"],
    Ready: ["statusReady", "guidanceReady", ""],
    ReadyWithWarnings: ["statusReadyWithWarnings", "guidanceReadyWithWarnings", "is-warning"]
  }[status] || ["statusBlocked", "guidanceBlocked", "is-blocked"];
}

function renderDataReadiness(payload) {
  dataReadiness = payload;
  const [statusKey, guidanceKey, bannerState] = readinessStatusCopy(payload.OverallStatus);
  const banner = document.getElementById("readiness-banner");
  banner.className = `readiness-banner ${bannerState}`.trim();
  setText("readiness-overall-status", translate(statusKey));
  setText("readiness-guidance", translate(guidanceKey));

  const version = payload.LatestMasterDataVersion;
  setText("master-data-id", version?.VersionID || "-");
  setText("master-data-source", displayValue(version?.SourceSystem));
  setText("master-data-created-by", displayValue(version?.CreatedBy));
  setText("master-data-captured-at", formatDate(version?.CapturedAt));
  setStatusChip(
    document.getElementById("master-data-status"),
    version ? translate(version.Status === "Valid" ? "valid" : "invalid") : translate("notAvailable"),
    version ? (version.Status === "Valid" ? "is-valid" : "is-invalid") : "neutral"
  );
  renderSummary("master-data-summary", version?.Summary);

  const snapshot = payload.LatestOperationalStateSnapshot;
  setText("operational-state-id", snapshot?.SnapshotID || "-");
  setText("operational-state-source", displayValue(snapshot?.SourceSystem));
  setText("operational-state-captured-at", formatDate(snapshot?.CapturedAt));
  const freshness = snapshot?.Freshness?.Status;
  const freshnessKey = { Fresh: "fresh", Stale: "stale", Future: "future" }[freshness];
  setText("operational-state-freshness", freshnessKey ? translate(freshnessKey) : "-");
  setStatusChip(
    document.getElementById("operational-state-status"),
    freshnessKey ? translate(freshnessKey) : translate("notAvailable"),
    freshness === "Fresh" ? "is-valid" : (snapshot ? "is-invalid" : "neutral")
  );
  renderSummary("operational-state-summary", snapshot?.Summary);
  renderReadinessIssues(payload.Issues || []);
  document.getElementById("select-planning-inputs").disabled = !payload.CanCreatePlanningRun;
  document.getElementById("readiness-error").hidden = true;
}

function issueMessage(issue) {
  const localized = translate(`issue_${issue.Code}`);
  return localized.startsWith("issue_") ? issue.Message : localized;
}

function localizedSeverity(value) {
  return translate({ Error: "severityError", Warning: "severityWarning" }[value] || "severityInformation");
}

function localizedEntityType(value) {
  return translate({
    MasterDataVersion: "entityMasterDataVersion",
    OperationalStateSnapshot: "entityOperationalStateSnapshot"
  }[value] || "entityUnknown");
}

function renderReadinessIssues(issues) {
  const container = document.getElementById("readiness-issues");
  container.replaceChildren();
  [{ severity: "Error", label: "errors" }, { severity: "Warning", label: "warnings" }].forEach((group) => {
    const groupedIssues = issues.filter((issue) => issue.Severity === group.severity);
    if (!groupedIssues.length) return;
    const section = document.createElement("section");
    section.className = "readiness-issue-group";
    const heading = document.createElement("h3");
    heading.textContent = `${translate(group.label)} (${groupedIssues.length})`;
    section.append(heading);
    groupedIssues.forEach((issue) => {
      const item = document.createElement("article");
      item.className = `issue-item ${issue.Severity === "Error" ? "is-error" : ""}`.trim();
      const title = document.createElement("strong");
      title.textContent = `${localizedSeverity(issue.Severity)} · ${localizedEntityType(issue.EntityType)}`;
      const message = document.createElement("p");
      message.textContent = issueMessage(issue);
      const meta = document.createElement("div");
      meta.className = "issue-meta";
      const location = document.createElement("span");
      location.textContent = `${translate("location")}: ${localizedEntityType(issue.EntityType)}${issue.EntityID ? ` / ${issue.EntityID}` : ""}`;
      meta.append(location);
      if (issue.Field) {
        const field = document.createElement("span");
        field.textContent = `${translate("field")}: ${issue.Field}`;
        meta.append(field);
      }
      const technicalCode = document.createElement("span");
      technicalCode.textContent = `${translate("technicalCode")}: ${issue.Code}`;
      meta.append(technicalCode);
      item.append(title, message, meta);
      section.append(item);
    });
    container.append(section);
  });
  setText("issues-summary", issues.length ? `${issues.length} ${translate("issueCount")}` : translate("noIssues"));
  document.getElementById("view-readiness-issues").disabled = issues.length === 0;
}

async function loadDataReadiness() {
  const banner = document.getElementById("readiness-banner");
  banner.className = "readiness-banner is-loading";
  try {
    const response = await fetch("/planner/workbench/data-readiness", { headers: { Accept: "application/json" } });
    if (!response.ok) throw new Error(String(response.status));
    const payload = await response.json();
    renderDataReadiness(payload.Data);
  } catch (_error) {
    banner.className = "readiness-banner is-blocked";
    document.getElementById("readiness-error").hidden = false;
  }
}

function openIssuesDrawer() {
  const drawer = document.getElementById("issues-drawer");
  drawer.hidden = false;
  drawer.classList.add("is-open");
  drawer.setAttribute("aria-hidden", "false");
  document.getElementById("drawer-backdrop").hidden = false;
  document.getElementById("close-issues-drawer").focus();
}

function closeIssuesDrawer() {
  const drawer = document.getElementById("issues-drawer");
  drawer.classList.remove("is-open");
  drawer.setAttribute("aria-hidden", "true");
  drawer.hidden = true;
  document.getElementById("drawer-backdrop").hidden = true;
}

function selectPlanningInputs() {
  if (!dataReadiness?.CanCreatePlanningRun) return;
  setText("master-data-version", dataReadiness.Selection.MasterDataVersionID);
  setText("snapshot-freshness", dataReadiness.Selection.OperationalStateSnapshotID);
  setText("route-status", translate("inputsSelected"));
}

function statusLabel(status) {
  return translate({
    Pending: "pending", Queued: "queued", Running: "running", Completed: "completed",
    Failed: "failed", DeadLetter: "deadLetter", Cancelled: "cancelled"
  }[status] || "status");
}

function statusClass(status) {
  if (status === "Completed") return "is-success";
  if (status === "Running") return "is-running";
  if (status === "Queued" || status === "Pending") return "is-warning";
  if (["Failed", "DeadLetter", "Cancelled"].includes(status)) return "is-error";
  return "";
}

function actionLabel(action) {
  return translate({
    Enqueue: "enqueue", Execute: "execute", Cancel: "cancel", Recover: "recover", OpenResults: "openResults"
  }[action] || "view");
}

function renderPlanningRunMetrics(data) {
  document.querySelectorAll("[data-run-metric]").forEach((element) => {
    const key = element.dataset.runMetric;
    element.textContent = key === "Total" ? data.Total : (data.ByStatus[key] || 0);
  });
}

function filteredPlanningRuns() {
  if (!planningRunWorkbench) return [];
  const status = document.getElementById("planning-run-status-filter").value;
  const requester = document.getElementById("planning-run-requester-filter").value.trim().toLowerCase();
  const solver = document.getElementById("planning-run-solver-filter").value;
  const timeHours = Number(document.getElementById("planning-run-time-filter").value || 0);
  const cutoff = timeHours ? Date.now() - (timeHours * 60 * 60 * 1000) : null;
  const exceptionsOnly = document.getElementById("planning-run-exception-filter").checked;
  return planningRunWorkbench.Rows.filter((run) => {
    if (status && run.Status !== status) return false;
    if (requester && !String(run.RequestedBy || "").toLowerCase().includes(requester)) return false;
    if (solver && run.SolverBackendID !== solver) return false;
    if (cutoff && new Date(run.RequestedAt).getTime() < cutoff) return false;
    if (exceptionsOnly && !["Failed", "DeadLetter", "Cancelled"].includes(run.Status)) return false;
    return true;
  });
}

function renderPlanningRuns() {
  const body = document.getElementById("planning-run-table-body");
  const rows = filteredPlanningRuns();
  body.replaceChildren();
  rows.forEach((run) => {
    const row = document.createElement("tr");
    const runCell = document.createElement("td");
    const runLink = document.createElement("button");
    runLink.type = "button";
    runLink.className = "run-link";
    runLink.textContent = run.RunID;
    runLink.addEventListener("click", () => openPlanningRunDetail(run.RunID));
    runCell.append(runLink);
    const status = document.createElement("span");
    status.className = `status-pill ${statusClass(run.Status)}`.trim();
    status.textContent = statusLabel(run.Status);
    const actionCell = document.createElement("td");
    actionCell.className = "run-actions";
    const viewButton = document.createElement("button");
    viewButton.type = "button";
    viewButton.className = "run-action";
    viewButton.textContent = translate("view");
    viewButton.addEventListener("click", () => openPlanningRunDetail(run.RunID));
    actionCell.append(viewButton);
    run.AllowedActions.forEach((action) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "run-action";
      button.textContent = actionLabel(action);
      button.addEventListener("click", () => performRunAction(run, action));
      actionCell.append(button);
    });
    [
      runCell, textCell(run.ProblemID), nodeCell(status), textCell(run.MasterDataVersionID),
      textCell(run.OperationalStateSnapshotID), textCell(run.SolverBackendID),
      textCell(run.RequestedBy), textCell(formatDate(run.StartedAt)),
      textCell(run.DurationSeconds === null ? "-" : `${run.DurationSeconds} ${translate("seconds")}`),
      textCell(`${run.AttemptCount}/${run.MaxAttempts || "-"}`), actionCell
    ].forEach((cell) => row.append(cell));
    body.append(row);
  });
  document.getElementById("planning-runs-empty").hidden = rows.length !== 0;
}

function textCell(value) {
  const cell = document.createElement("td");
  cell.textContent = value ?? "-";
  return cell;
}

function nodeCell(node) {
  const cell = document.createElement("td");
  cell.append(node);
  return cell;
}

async function loadPlanningRuns() {
  try {
    const response = await fetch("/planner/workbench/planning-runs/workbench", { headers: { Accept: "application/json" } });
    if (!response.ok) throw new Error(String(response.status));
    planningRunWorkbench = (await response.json()).Data;
    renderPlanningRunMetrics(planningRunWorkbench);
    renderPlanningRuns();
    document.getElementById("planning-runs-error").hidden = true;
  } catch (_error) {
    document.getElementById("planning-runs-error").hidden = false;
  }
}

async function openPlanningRunWizard() {
  if (!dataReadiness) await loadDataReadiness();
  const dialog = document.getElementById("planning-run-wizard");
  const now = new Date();
  document.getElementById("wizard-run-id").value = `RUN-${now.toISOString().replace(/\D/g, "").slice(0, 14)}`;
  document.getElementById("wizard-problem-id").value = `PLAN-${now.toISOString().slice(0, 10)}`;
  document.getElementById("wizard-master-data-version").value = dataReadiness?.Selection?.MasterDataVersionID || "";
  document.getElementById("wizard-operational-snapshot").value = dataReadiness?.Selection?.OperationalStateSnapshotID || "";
  document.getElementById("wizard-schedule-start").value = new Date(now.getTime() + 3600000).toISOString().slice(0, 16);
  document.getElementById("wizard-input-warning").hidden = Boolean(dataReadiness?.CanCreatePlanningRun);
  document.getElementById("wizard-submit-error").hidden = true;
  const ortools = planningRunWorkbench?.Capabilities?.Solvers?.find((item) => item.BackendID === "ortools");
  document.getElementById("solver-ortools").disabled = !ortools?.Available;
  document.getElementById("solver-ortools-status").textContent = translate(ortools?.Available ? "available" : "unavailable");
  setWizardStep(1);
  dialog.showModal();
}

function setWizardStep(step) {
  planningRunWizardStep = step;
  document.querySelectorAll("[data-wizard-step]").forEach((section) => { section.hidden = Number(section.dataset.wizardStep) !== step; });
  document.querySelectorAll("[data-wizard-indicator]").forEach((item) => item.classList.toggle("is-active", Number(item.dataset.wizardIndicator) === step));
  document.getElementById("wizard-back").disabled = step === 1;
  document.getElementById("wizard-next").hidden = step === 3;
  document.getElementById("wizard-submit").hidden = step !== 3;
  document.getElementById("wizard-next").disabled = step === 1 && !dataReadiness?.CanCreatePlanningRun;
  document.getElementById("wizard-submit").disabled = !dataReadiness?.CanCreatePlanningRun
    || document.getElementById("solver-ortools").disabled;
  if (step === 3) renderWizardReview();
}

function renderWizardReview() {
  const review = document.getElementById("wizard-review");
  review.replaceChildren();
  [
    ["runId", "wizard-run-id"], ["problem", "wizard-problem-id"], ["masterDataVersionLabel", "wizard-master-data-version"],
    ["snapshotLabel", "wizard-operational-snapshot"], ["scheduleStart", "wizard-schedule-start"],
    ["timeBuffer", "wizard-time-buffer"], ["timeLimit", "wizard-time-limit"], ["maxAttempts", "wizard-max-attempts"],
    ["retryDelay", "wizard-retry-delay"]
  ].forEach(([labelKey, inputId]) => {
    const row = document.createElement("div");
    row.className = "review-row";
    const label = document.createElement("span");
    label.textContent = translate(labelKey);
    const value = document.createElement("strong");
    value.textContent = document.getElementById(inputId).value || "-";
    row.append(label, value);
    review.append(row);
  });
}

async function submitPlanningRun(event) {
  event.preventDefault();
  const error = document.getElementById("wizard-submit-error");
  const payload = {
    RunID: document.getElementById("wizard-run-id").value,
    ProblemID: document.getElementById("wizard-problem-id").value,
    MasterDataVersionID: document.getElementById("wizard-master-data-version").value,
    OperationalStateSnapshotID: document.getElementById("wizard-operational-snapshot").value,
    ScheduleStartAt: new Date(document.getElementById("wizard-schedule-start").value).toISOString(),
    TimeBufferMinutes: Number(document.getElementById("wizard-time-buffer").value),
    SolverBackendID: "ortools",
    TimeLimitSeconds: Number(document.getElementById("wizard-time-limit").value),
    MaxAttempts: Number(document.getElementById("wizard-max-attempts").value),
    RetryDelaySeconds: Number(document.getElementById("wizard-retry-delay").value),
    RequestedBy: "planner",
    RequestedAt: new Date().toISOString()
  };
  try {
    const response = await fetch("/planner/workbench/planning-runs", {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload)
    });
    if (!response.ok) {
      const result = await response.json();
      throw new Error(response.status === 409 ? translate("dataUpdated") : (result.Data?.Message || translate("submissionFailed")));
    }
    document.getElementById("planning-run-wizard").close();
    setText("route-status", translate("runCreated"));
    await loadPlanningRuns();
  } catch (caught) {
    error.hidden = false;
    error.textContent = caught.message;
  }
}

async function openPlanningRunDetail(runId) {
  const response = await fetch(`/planner/workbench/planning-runs/${encodeURIComponent(runId)}/workbench`);
  if (!response.ok) return;
  renderPlanningRunDetail((await response.json()).Data);
  const drawer = document.getElementById("planning-run-detail");
  drawer.hidden = false;
  drawer.classList.add("is-open");
  drawer.setAttribute("aria-hidden", "false");
  document.getElementById("drawer-backdrop").hidden = false;
}

function renderPlanningRunDetail(detail) {
  setText("run-detail-title", detail.RunID);
  const content = document.getElementById("planning-run-detail-content");
  content.replaceChildren();
  content.append(detailSection("frozenInputs", [
    ["masterDataVersionLabel", detail.FrozenInputs.MasterDataVersionID],
    ["snapshotLabel", detail.FrozenInputs.OperationalStateSnapshotID],
    ["scheduleStart", formatDate(detail.ScheduleStartAt)],
    ["status", statusLabel(detail.Status)]
  ]));
  content.append(detailSection("solverParameters", [
    ["solver", detail.SolverBackendID], ["timeBuffer", detail.TimeBufferMinutes],
    ["timeLimit", detail.TimeLimitSeconds || "-"], ["attempts", `${detail.AttemptCount}/${detail.MaxAttempts || "-"}`]
  ]));
  content.append(detailSection("workerLease", detail.Worker ? [
    ["requester", detail.Worker.WorkerID], ["requestedAt", formatDate(detail.Worker.LeaseClaimedAt)],
    ["duration", formatDate(detail.Worker.LeaseExpiresAt)], ["attempts", detail.Worker.LeaseRenewalCount]
  ] : [["workerLease", translate("noWorker")]]));
  content.append(listSection("timeline", detail.Timeline, (item) => `${statusLabel(item.Status)} · ${formatDate(item.ChangedAt)} · ${item.ChangedBy}`));
  content.append(listSection("diagnostics", detail.Diagnostics, (item) => `${item.Code}: ${item.Message}`));
  content.append(listSection("auditEvents", detail.AuditEvents, (item) => `${item.Action} · ${item.ActorID} · ${formatDate(item.OccurredAt)}`));
}

function detailSection(titleKey, rows) {
  const section = document.createElement("section");
  section.className = "detail-section";
  const title = document.createElement("h3");
  title.textContent = translate(titleKey);
  const grid = document.createElement("div");
  grid.className = "detail-grid";
  rows.forEach(([labelKey, value]) => {
    const cell = document.createElement("div");
    cell.className = "detail-cell";
    const label = document.createElement("span");
    label.textContent = translate(labelKey);
    const strong = document.createElement("strong");
    strong.textContent = value ?? "-";
    cell.append(label, strong);
    grid.append(cell);
  });
  section.append(title, grid);
  return section;
}

function listSection(titleKey, items, formatter) {
  const section = document.createElement("section");
  section.className = "detail-section";
  const title = document.createElement("h3");
  title.textContent = translate(titleKey);
  const list = document.createElement("div");
  list.className = "timeline-list";
  (items || []).forEach((item) => {
    const row = document.createElement("div");
    row.className = "timeline-item";
    const text = document.createElement("strong");
    text.textContent = formatter(item);
    row.append(text);
    list.append(row);
  });
  section.append(title, list);
  return section;
}

function closePlanningRunDetail() {
  const drawer = document.getElementById("planning-run-detail");
  drawer.classList.remove("is-open");
  drawer.setAttribute("aria-hidden", "true");
  drawer.hidden = true;
  document.getElementById("drawer-backdrop").hidden = true;
}

async function performRunAction(run, action) {
  if (action === "OpenResults") {
    selectedScheduleRunID = run.RunID;
    window.location.hash = "schedule-results";
    return;
  }
  const now = new Date().toISOString();
  let endpoint = null;
  let payload = null;
  if (action === "Enqueue") {
    if (!(await confirmAction({ message: translate("confirmEnqueue"), context: `${translate("runId")}: ${run.RunID}` }))) return;
    endpoint = `/planner/workbench/planning-runs/${encodeURIComponent(run.RunID)}/enqueue`;
    payload = {
      EnqueuedBy: "planner", EnqueuedAt: now, MaxAttempts: run.MaxAttempts || 3,
      RetryDelaySeconds: run.RetryDelaySeconds ?? 60
    };
  } else if (action === "Execute") {
    if (!(await confirmAction({ message: translate("confirmExecute"), context: `${translate("runId")}: ${run.RunID}` }))) return;
    endpoint = `/planner/workbench/planning-runs/${encodeURIComponent(run.RunID)}/execute`;
    payload = { ExecutedBy: "planner", StartedAt: now, TimeLimitSeconds: run.TimeLimitSeconds || 300 };
  } else if (action === "Cancel") {
    const reason = window.prompt(translate("cancelReasonPrompt"), "");
    if (reason === null) return;
    endpoint = `/planner/workbench/planning-runs/${encodeURIComponent(run.RunID)}/cancel`;
    payload = { CancelledBy: "planner", CancelledAt: now, Reason: reason.trim() || translate("cancel") };
  } else if (action === "Recover") {
    const reason = window.prompt(translate("recoverReasonPrompt"), "");
    if (reason === null) return;
    endpoint = `/planner/workbench/planning-runs/${encodeURIComponent(run.RunID)}/recover`;
    payload = { RecoveredBy: "planner", RecoveredAt: now, Reason: reason.trim() || translate("recover"), ResetAttempts: true };
  }
  if (!endpoint) { await openPlanningRunDetail(run.RunID); return; }
  const response = await fetch(endpoint, {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload)
  });
  if (!response.ok) {
    const result = await response.json();
    setText("route-status", response.status === 409 ? translate("dataUpdated") : (result.Data?.Message || translate("actionFailed")));
    showNotification(response.status === 409 ? translate("dataUpdated") : translate("notifyError"), "error");
    return;
  }
  showNotification(translate("notifySuccess"), "success");
  await loadPlanningRuns();
}

function replaceSelectOptions(select, options, { allKey = null, valueKey = null, labelKey = null } = {}) {
  const previous = select.value;
  select.replaceChildren();
  if (allKey) {
    const all = document.createElement("option");
    all.value = "";
    all.textContent = translate(allKey);
    select.append(all);
  }
  options.forEach((item) => {
    const option = document.createElement("option");
    if (typeof item === "object") {
      option.value = String(item[valueKey]);
      option.textContent = String(item[labelKey] || item[valueKey]);
    } else {
      option.value = String(item);
      option.textContent = String(item);
    }
    select.append(option);
  });
  if ([...select.options].some((option) => option.value === previous)) select.value = previous;
}

async function loadScheduleResultRuns() {
  try {
    const response = await fetch("/planner/workbench/planning-runs/workbench", { headers: { Accept: "application/json" } });
    if (!response.ok) throw new Error(String(response.status));
    const workbench = (await response.json()).Data;
    scheduleResultRuns = workbench.Rows.filter((run) => run.Status === "Completed");
    const runSelect = document.getElementById("schedule-result-run-select");
    replaceSelectOptions(runSelect, scheduleResultRuns, { valueKey: "RunID", labelKey: "RunID" });
    replaceSelectOptions(document.getElementById("baseline-run-select"), scheduleResultRuns, { valueKey: "RunID", labelKey: "RunID" });
    replaceSelectOptions(document.getElementById("candidate-run-select"), scheduleResultRuns, { valueKey: "RunID", labelKey: "RunID" });
    if (!scheduleResultRuns.length) {
      document.getElementById("schedule-result-empty").hidden = false;
      document.getElementById("schedule-result-content").hidden = true;
      document.getElementById("schedule-result-error").hidden = true;
      return;
    }
    const validSelected = scheduleResultRuns.some((run) => run.RunID === selectedScheduleRunID);
    selectedScheduleRunID = validSelected ? selectedScheduleRunID : scheduleResultRuns[0].RunID;
    runSelect.value = selectedScheduleRunID;
    const baseline = document.getElementById("baseline-run-select");
    const candidate = document.getElementById("candidate-run-select");
    baseline.value = scheduleResultRuns[0].RunID;
    candidate.value = scheduleResultRuns[Math.min(1, scheduleResultRuns.length - 1)].RunID;
    document.getElementById("schedule-result-empty").hidden = true;
    await loadScheduleResult(selectedScheduleRunID);
  } catch (_error) {
    document.getElementById("schedule-result-error").hidden = false;
    document.getElementById("schedule-result-content").hidden = true;
  }
}

async function loadScheduleResult(runId) {
  if (!runId) return;
  try {
    const response = await fetch(`/planner/workbench/schedule-results/runs/${encodeURIComponent(runId)}/workbench`);
    if (!response.ok) throw new Error(String(response.status));
    scheduleResultData = (await response.json()).Data;
    selectedScheduleRunID = runId;
    renderScheduleResult();
    await loadScheduledOrders(runId);
    await loadPlanPublication(runId);
    document.getElementById("schedule-result-error").hidden = true;
    document.getElementById("schedule-result-content").hidden = false;
  } catch (_error) {
    document.getElementById("schedule-result-error").hidden = false;
    document.getElementById("schedule-result-content").hidden = true;
  }
}

function renderScheduleResult() {
  if (!scheduleResultData) return;
  const context = scheduleResultData.Context;
  const contextElement = document.getElementById("schedule-result-context");
  contextElement.replaceChildren();
  [["problem", context.ProblemID], ["solver", context.SolverBackendID], ["generatedAt", formatDate(context.GeneratedAt)]].forEach(([key, value]) => {
    const span = document.createElement("span");
    const label = document.createElement("span");
    label.textContent = `${translate(key)}: `;
    const strong = document.createElement("strong");
    strong.textContent = value ?? "-";
    span.append(label, strong);
    contextElement.append(span);
  });
  document.querySelectorAll("[data-schedule-kpi]").forEach((element) => {
    const key = element.dataset.scheduleKpi;
    const value = scheduleResultData.KPIs[key] ?? 0;
    element.textContent = key === "MaxLoadPercent" ? `${value}%` : String(value);
  });
  prepareScheduleFilters();
  renderGanttBoard();
  renderSystemLoad();
  renderResourceLoad();
  renderOrderDelivery();
  renderScheduleDiagnostics();
  setScheduleTab(activeScheduleTab);
}

function prepareScheduleFilters() {
  const options = scheduleResultData.FilterOptions;
  replaceSelectOptions(document.getElementById("gantt-resource-filter"), options.Resources, { allKey: "allResources", valueKey: "ResourceID", labelKey: "ResourceName" });
  replaceSelectOptions(document.getElementById("gantt-order-filter"), options.Orders, { allKey: "allOrders" });
  replaceSelectOptions(document.getElementById("gantt-type-filter"), options.BarTypes, { allKey: "allBarTypes" });
  replaceSelectOptions(document.getElementById("gantt-zone-filter"), options.BufferZones, { allKey: "allZones" });
  replaceSelectOptions(document.getElementById("load-type-filter"), options.ResourceTypes, { allKey: "allOptions" });
  replaceSelectOptions(document.getElementById("load-location-filter"), options.Locations, { allKey: "allOptions" });
  replaceSelectOptions(document.getElementById("load-owner-filter"), options.Owners, { allKey: "allOptions" });
  replaceSelectOptions(document.getElementById("load-category-filter"), options.Categories, { allKey: "allOptions" });
  replaceSelectOptions(document.getElementById("resource-load-select"), options.Resources, { valueKey: "ResourceID", labelKey: "ResourceName" });
  const range = scheduleResultData.Gantt.Range;
  if (range.Start && !document.getElementById("gantt-from-date").value) document.getElementById("gantt-from-date").value = range.Start.slice(0, 10);
  if (range.End && !document.getElementById("gantt-to-date").value) document.getElementById("gantt-to-date").value = range.End.slice(0, 10);
}

function setScheduleTab(tabName) {
  activeScheduleTab = tabName;
  document.querySelectorAll("[data-schedule-tab]").forEach((button) => {
    const active = button.dataset.scheduleTab === tabName;
    button.classList.toggle("is-active", active);
    button.setAttribute("aria-selected", String(active));
  });
  document.querySelectorAll("[data-schedule-panel]").forEach((panel) => { panel.hidden = panel.dataset.schedulePanel !== tabName; });
}

function ganttBarTypeLabel(bar) {
  if (bar.BarType === "Processing") return translate("processing");
  if (bar.BarType === "Maintenance") return translate("maintenance");
  if (bar.BarType === "Unavailable") return translate("unavailableTime");
  return translate(`${String(bar.BufferZone || "Green").toLowerCase()}Buffer`);
}

function renderGanttBoard() {
  const board = document.getElementById("gantt-board");
  board.replaceChildren();
  const resourceFilter = document.getElementById("gantt-resource-filter").value;
  const orderFilter = document.getElementById("gantt-order-filter").value;
  const typeFilter = document.getElementById("gantt-type-filter").value;
  const zoneFilter = document.getElementById("gantt-zone-filter").value;
  const fromValue = document.getElementById("gantt-from-date").value;
  const toValue = document.getElementById("gantt-to-date").value;
  const from = fromValue ? new Date(`${fromValue}T00:00:00`) : new Date(scheduleResultData.Gantt.Range.Start);
  const to = toValue ? new Date(`${toValue}T23:59:59`) : new Date(scheduleResultData.Gantt.Range.End);
  const rangeMs = Math.max(to.getTime() - from.getTime(), 1);
  board.style.setProperty("--gantt-zoom", document.getElementById("gantt-zoom").value);
  const axis = document.createElement("div");
  axis.className = "gantt-axis";
  const axisLabel = document.createElement("div");
  axisLabel.className = "gantt-axis-label";
  axisLabel.textContent = translate("resource");
  const axisTrack = document.createElement("div");
  axisTrack.className = "gantt-axis-track";
  for (let index = 0; index <= 4; index += 1) {
    const tick = document.createElement("span");
    tick.className = "gantt-tick";
    tick.style.setProperty("--tick-position", `${index * 25}%`);
    tick.textContent = new Intl.DateTimeFormat(currentLanguage === "zh" ? "zh-CN" : "en-US", { month: "short", day: "numeric" }).format(new Date(from.getTime() + rangeMs * index / 4));
    axisTrack.append(tick);
  }
  axis.append(axisLabel, axisTrack);
  board.append(axis);
  let visibleRows = 0;
  scheduleResultData.Gantt.Rows.forEach((rowData) => {
    if (resourceFilter && rowData.ResourceID !== resourceFilter) return;
    const bars = rowData.Bars.filter((bar) => {
      if (orderFilter && bar.OrderID !== orderFilter) return false;
      if (typeFilter && bar.BarType !== typeFilter) return false;
      if (zoneFilter && bar.BufferZone !== zoneFilter) return false;
      return new Date(bar.End) >= from && new Date(bar.Start) <= to;
    });
    if (!bars.length) return;
    visibleRows += 1;
    const row = document.createElement("div");
    row.className = `gantt-row${rowData.IsConstraint ? " is-constraint" : ""}`;
    const label = document.createElement("div");
    label.className = "gantt-resource-label";
    label.textContent = `${rowData.ResourceName}${rowData.IsConstraint ? ` · ${translate("constraint")}` : ""}`;
    const track = document.createElement("div");
    track.className = "gantt-track";
    bars.forEach((bar) => {
      const start = Math.max(new Date(bar.Start).getTime(), from.getTime());
      const end = Math.min(new Date(bar.End).getTime(), to.getTime());
      const element = document.createElement("div");
      element.className = bar.BarType === "TimeBuffer"
        ? `gantt-bar buffer ${bar.BufferZone || "Green"}`
        : `gantt-bar ${String(bar.BarType).toLowerCase()}`;
      element.style.setProperty("--bar-left", `${Math.max((start - from.getTime()) / rangeMs * 100, 0)}%`);
      element.style.setProperty("--bar-width", `${Math.max((end - start) / rangeMs * 100, 0.35)}%`);
      element.textContent = bar.BarType === "Processing"
        ? `${bar.OrderID} · ${bar.OperationID}`
        : (bar.BarType === "TimeBuffer" ? bar.OrderID : ganttBarTypeLabel(bar));
      element.title = `${ganttBarTypeLabel(bar)}\n${translate("workOrder")}: ${bar.OrderID || "-"}\n${translate("resource")}: ${rowData.ResourceName}\n${translate("startedAt")}: ${formatDate(bar.Start)}\n${translate("plannedCompletion")}: ${formatDate(bar.End)}`;
      track.append(element);
    });
    row.append(label, track);
    board.append(row);
  });
  if (!visibleRows) {
    const empty = document.createElement("div");
    empty.className = "table-empty";
    empty.textContent = translate("noGanttRows");
    board.append(empty);
  }
}

function filteredSystemLoadRows() {
  const filters = [
    ["load-type-filter", "ResourceType"], ["load-location-filter", "LocationID"],
    ["load-owner-filter", "OwnerID"], ["load-category-filter", "Category"]
  ];
  return scheduleResultData.SystemLoad.Rows.filter((row) => filters.every(([id, key]) => !document.getElementById(id).value || String(row[key] ?? "") === document.getElementById(id).value));
}

function renderSystemLoad() {
  if (!scheduleResultData) return;
  const chart = document.getElementById("system-load-chart");
  chart.replaceChildren();
  filteredSystemLoadRows().forEach((row) => {
    const item = document.createElement("div");
    item.className = "load-row";
    const label = document.createElement("div");
    label.className = "load-row-label";
    const strong = document.createElement("strong");
    strong.textContent = row.ResourceName;
    const detail = document.createElement("span");
    detail.textContent = `${row.RequiredMinutes} / ${row.CapacityMinutes} min${row.IsCandidateConstraint ? ` · ${translate("candidateConstraint")}` : ""}`;
    label.append(strong, detail);
    const track = document.createElement("div");
    track.className = "load-track";
    const bar = document.createElement("div");
    bar.className = `load-bar${row.LoadPercent > 100 ? " overload" : ""}`;
    bar.style.setProperty("--load-width", `${Math.min(row.LoadPercent / 1.5, 100)}%`);
    track.append(bar);
    const value = document.createElement("div");
    value.className = "load-value";
    value.textContent = `${row.LoadPercent}%`;
    item.append(label, track, value);
    chart.append(item);
  });
}

function setLoadView(viewName) {
  document.querySelectorAll("[data-load-view]").forEach((button) => button.classList.toggle("is-active", button.dataset.loadView === viewName));
  document.getElementById("system-load-view").hidden = viewName !== "system";
  document.getElementById("resource-load-view").hidden = viewName !== "resource";
}

function renderResourceLoad() {
  if (!scheduleResultData) return;
  const resourceId = document.getElementById("resource-load-select").value;
  const rows = scheduleResultData.ResourceLoad.Rows.filter((row) => row.ResourceID === resourceId);
  const chart = document.getElementById("resource-load-chart");
  const table = document.getElementById("resource-load-table-body");
  chart.replaceChildren();
  table.replaceChildren();
  rows.forEach((row) => {
    const item = document.createElement("div");
    item.className = "load-row";
    const label = document.createElement("div");
    label.className = "load-row-label";
    label.textContent = row.Date;
    const track = document.createElement("div");
    track.className = "load-track";
    const bar = document.createElement("div");
    bar.className = `load-bar${row.LoadPercent > 100 ? " overload" : ""}`;
    bar.style.setProperty("--load-width", `${Math.min(row.LoadPercent / 1.5, 100)}%`);
    track.append(bar);
    const value = document.createElement("div");
    value.className = "load-value";
    value.textContent = `${row.LoadPercent}%`;
    item.append(label, track, value);
    chart.append(item);
    const tableRow = document.createElement("tr");
    [row.Date, row.RequiredMinutes, row.CapacityMinutes, `${row.LoadPercent}%`, row.ReleasedMinutes, row.UnreleasedMinutes, row.RemainingMinutes].forEach((cellValue) => tableRow.append(textCell(cellValue)));
    table.append(tableRow);
  });
}

function deliveryStatusLabel(status) {
  return translate({ OnTime: "onTime", Late: "late", Unscheduled: "unscheduled" }[status] || "notProvided");
}

function renderOrderDelivery() {
  const body = document.getElementById("order-delivery-table-body");
  body.replaceChildren();
  scheduleResultData.OrderDelivery.forEach((order) => {
    const row = document.createElement("tr");
    [order.OrderID, order.ProductID, formatDate(order.DueDate), formatDate(order.PlannedCompletionAt), deliveryStatusLabel(order.Status), order.DelayMinutes ?? "-"].forEach((value) => row.append(textCell(value)));
    body.append(row);
  });
}

function renderScheduleDiagnostics() {
  const container = document.getElementById("schedule-diagnostics");
  container.replaceChildren();
  if (!scheduleResultData.Diagnostics.length) {
    const empty = document.createElement("div");
    empty.className = "table-empty";
    empty.textContent = translate("noDiagnostics");
    container.append(empty);
    return;
  }
  scheduleResultData.Diagnostics.forEach((diagnostic) => {
    const item = document.createElement("div");
    item.className = `diagnostic-item${diagnostic.Severity === "Error" ? " is-error" : ""}`;
    const strong = document.createElement("strong");
    strong.textContent = diagnostic.Code;
    const detail = document.createElement("span");
    detail.textContent = diagnostic.Message;
    item.append(strong, detail);
    container.append(item);
  });
}

async function loadPlanPublication(runId) {
  planPublicationData = null;
  document.getElementById("publication-error").hidden = true;
  try {
    const response = await fetch(`/planner/workbench/planning-runs/${encodeURIComponent(runId)}/publication`, { headers: { Accept: "application/json" } });
    if (!response.ok) throw new Error(String(response.status));
    planPublicationData = (await response.json()).Data;
    renderPlanPublication();
  } catch (_error) {
    document.getElementById("publication-error").hidden = false;
    renderPlanPublication();
  }
}

function publicationStatusLabel(status) {
  return translate({
    Draft: "statusDraft", Reviewed: "statusReviewed", Approved: "statusApproved",
    Published: "statusPublished", PublicationRevoked: "statusPublicationRevoked",
    Superseded: "statusSuperseded", Unavailable: "statusUnavailable"
  }[status] || "statusUnavailable");
}

function publicationStatusClass(status) {
  if (status === "Published") return "is-valid";
  if (status === "Approved" || status === "Reviewed" || status === "Draft") return "is-warning";
  if (status === "PublicationRevoked" || status === "Superseded") return "neutral";
  return "is-unavailable";
}

function publicationActionLabel(action) {
  return translate({
    Review: "actionReview", Approve: "actionApprove", Publish: "actionPublish", Revoke: "actionRevoke"
  }[action] || "view");
}

function publicationActionEndpoint(action) {
  return {
    Review: "review", Approve: "approve", Publish: "publish", Revoke: "revoke"
  }[action];
}

function renderPlanPublication() {
  const statusChip = document.getElementById("publication-status-chip");
  const summary = document.getElementById("publication-summary");
  const actions = document.getElementById("publication-actions");
  const packageElement = document.getElementById("publication-package");
  const historyElement = document.getElementById("publication-history");
  summary.replaceChildren();
  actions.replaceChildren();
  packageElement.replaceChildren();
  historyElement.replaceChildren();
  if (!planPublicationData) {
    setStatusChip(statusChip, publicationStatusLabel("Unavailable"), "is-unavailable");
    return;
  }

  const status = planPublicationData.PublicationStatus || "Unavailable";
  setStatusChip(statusChip, publicationStatusLabel(status), publicationStatusClass(status));
  summary.append(detailSection("publicationStatus", [
    ["planningRun", planPublicationData.RunID],
    ["problem", planPublicationData.ProblemID],
    ["publicationStatus", publicationStatusLabel(status)],
    ["scheduleFingerprint", planPublicationData.ScheduleFingerprint ? `${planPublicationData.ScheduleFingerprint.slice(0, 16)}...` : "-"],
    ["supersedesRun", displayValue(planPublicationData.SupersedesRunID)],
    ["supersededByRun", displayValue(planPublicationData.SupersededByRunID)]
  ]));

  const actionTitle = document.createElement("h3");
  actionTitle.textContent = translate("allowedPublicationActions");
  actions.append(actionTitle);
  const allowed = planPublicationData.AllowedActions || [];
  if (!allowed.length) {
    const empty = document.createElement("p");
    empty.className = "inline-note";
    empty.textContent = translate("notAvailable");
    actions.append(empty);
  }
  allowed.forEach((action) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = action === "Publish" ? "button primary" : "button secondary";
    button.textContent = publicationActionLabel(action);
    button.addEventListener("click", () => executePublicationAction(action));
    actions.append(button);
  });

  const packageData = planPublicationData.PublicationPackage;
  if (packageData) {
    const summaryData = packageData.Summary || {};
    packageElement.append(detailSection("publicationPackage", [
      ["packageId", packageData.PackageID],
      ["targetSystems", (packageData.TargetSystems || []).join(", ")],
      ["publishedBy", packageData.PublishedBy],
      ["publishedAt", formatDate(packageData.PublishedAt)],
      ["orders", displayValue(summaryData.OrderCount)],
      ["solverStatus", displayValue(summaryData.SolverStatus)]
    ]));
  } else {
    packageElement.append(detailSection("publicationPackage", [["publicationPackage", translate("notAvailable")]]));
  }

  const history = planPublicationData.PublicationHistory || [];
  if (history.length) {
    historyElement.append(listSection("publicationHistory", history, (item) => `${publicationActionLabel(item.Action)} · ${publicationStatusLabel(item.FromStatus)} → ${publicationStatusLabel(item.ToStatus)} · ${displayValue(item.ActorID)} · ${formatDate(item.OccurredAt)}${item.Comment ? ` · ${item.Comment}` : ""}`));
  } else {
    historyElement.append(detailSection("publicationHistory", [["publicationHistory", translate("noPublicationHistory")]]));
  }
}

async function executePublicationAction(action) {
  const endpointAction = publicationActionEndpoint(action);
  if (!selectedScheduleRunID || !endpointAction) return;
  const comment = window.prompt(translate("publicationCommentPrompt"), "");
  if (comment === null) return;
  const response = await fetch(`/planner/workbench/planning-runs/${encodeURIComponent(selectedScheduleRunID)}/publication/${endpointAction}`, {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-Workbench-Actor-Role": action === "Publish" || action === "Revoke" ? "Admin" : "Planner" },
    body: JSON.stringify({
      ActorID: action === "Publish" || action === "Revoke" ? "admin" : "planner",
      OccurredAt: new Date().toISOString(),
      Comment: comment.trim() || null,
      TargetSystems: ["InternalPlanning"]
    })
  });
  if (!response.ok) {
    showNotification(response.status === 403 || response.status === 409 ? translate("publicationActionDenied") : translate("notifyError"), "error");
    await loadPlanPublication(selectedScheduleRunID);
    return;
  }
  planPublicationData = (await response.json()).Data;
  renderPlanPublication();
  showNotification(translate("publicationActionCompleted"), "success");
}

async function compareSelectedScenarios() {
  const baselineRunID = document.getElementById("baseline-run-select").value;
  const candidateRunID = document.getElementById("candidate-run-select").value;
  if (!baselineRunID || !candidateRunID || baselineRunID === candidateRunID) return;
  const query = new URLSearchParams({ baseline_run_id: baselineRunID, candidate_run_id: candidateRunID });
  const response = await fetch(`/planner/workbench/schedule-results/compare?${query}`);
  if (!response.ok) return;
  renderScenarioComparison((await response.json()).Data);
}

function renderScenarioComparison(comparison) {
  const container = document.getElementById("scenario-comparison-result");
  container.hidden = false;
  container.replaceChildren();
  const grid = document.createElement("div");
  grid.className = "comparison-grid";
  [comparison.Baseline, comparison.Candidate].forEach((scenario, index) => {
    const column = document.createElement("section");
    column.className = `comparison-column${scenario.RunID === comparison.RecommendedRunID ? " is-recommended" : ""}`;
    const title = document.createElement("h3");
    title.textContent = `${index === 0 ? translate("baselineScenario") : translate("candidateScenario")}: ${scenario.RunID}${scenario.RunID === comparison.RecommendedRunID ? ` · ${translate("recommended")}` : ""}`;
    const metrics = document.createElement("div");
    metrics.className = "comparison-metrics";
    [["onTimeOrders", "OnTimeOrderCount"], ["lateOrders", "LateOrderCount"], ["overloadMinutes", "TotalOverloadMinutes"], ["redBuffers", "RedBufferCount"]].forEach(([labelKey, metricKey]) => {
      const item = document.createElement("div");
      const label = document.createElement("span");
      label.textContent = translate(labelKey);
      const strong = document.createElement("strong");
      strong.textContent = scenario.KPIs[metricKey] ?? 0;
      item.append(label, strong);
      metrics.append(item);
    });
    column.append(title, metrics);
    grid.append(column);
  });
  const decision = document.createElement("div");
  decision.className = "comparison-decision";
  const reasons = document.createElement("span");
  reasons.textContent = comparison.DecisionCodes.map((code) => translate({ CANDIDATE_REDUCES_OVERLOAD: "candidateReducesOverload", CANDIDATE_REDUCES_LATE_ORDERS: "candidateReducesLateOrders", CANDIDATE_REDUCES_RED_BUFFERS: "candidateReducesRedBuffers", BASELINE_BETTER_SCORE: "baselineBetterScore", CANDIDATE_BETTER_SCORE: "candidateBetterScore" }[code] || code)).join(" ");
  const select = document.createElement("button");
  select.type = "button";
  select.className = "button primary";
  select.textContent = translate("selectScenario");
  select.addEventListener("click", () => selectScenarioForReview(comparison));
  decision.append(reasons, select);
  container.append(grid, decision);
}

async function selectScenarioForReview(comparison) {
  const reason = window.prompt(translate("selectionReasonPrompt"), "");
  if (reason === null) return;
  const response = await fetch("/planner/workbench/schedule-results/select", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      BaselineRunID: comparison.Baseline.RunID, CandidateRunID: comparison.Candidate.RunID,
      SelectedRunID: comparison.RecommendedRunID, SelectedBy: "planner",
      SelectedAt: new Date().toISOString(), Reason: reason.trim() || translate("recommended")
    })
  });
  if (response.ok) setText("route-status", translate("selectedForReview"));
}

const SCHEDULED_ORDER_COLUMNS = [
  ["OrderID", "workOrder"], ["ProductID", "product"], ["OrderDate", "orderDate"],
  ["PlannedReleaseAt", "plannedRelease"], ["FinalDemandDate", "finalDemandDate"],
  ["PromiseDate", "promiseDate"], ["OnTimeStatus", "onTimeStatus"],
  ["ReleaseStatus", "releaseStatus"], ["ExecutionPriority", "executionPriority"],
  ["RoutingID", "routing"], ["OrderFamily", "orderFamily"], ["ResourceIDs", "groupedResources"]
];

async function loadScheduledOrders(runId) {
  try {
    const response = await fetch(`/planner/workbench/schedule-results/runs/${encodeURIComponent(runId)}/work-orders/workbench`);
    if (!response.ok) throw new Error(String(response.status));
    scheduledOrdersData = (await response.json()).Data;
    selectedScheduledOrderIDs.clear();
    scheduledOrdersPage = 1;
    prepareScheduledOrderControls();
    renderScheduledOrders();
  } catch (_error) {
    scheduledOrdersData = null;
  }
}

function prepareScheduledOrderControls() {
  const options = scheduledOrdersData.FilterOptions;
  replaceSelectOptions(document.getElementById("scheduled-order-release-filter"), options.ReleaseStatuses, { allKey: "allOptions" });
  replaceSelectOptions(document.getElementById("scheduled-order-buffer-filter"), options.BufferZones, { allKey: "allZones" });
  const picker = document.getElementById("scheduled-order-columns");
  picker.replaceChildren();
  SCHEDULED_ORDER_COLUMNS.forEach(([key, labelKey]) => {
    const label = document.createElement("label");
    const input = document.createElement("input");
    input.type = "checkbox";
    input.checked = visibleScheduledOrderColumns.has(key);
    input.addEventListener("change", () => {
      if (input.checked) visibleScheduledOrderColumns.add(key);
      else visibleScheduledOrderColumns.delete(key);
      renderScheduledOrders();
    });
    const span = document.createElement("span");
    span.textContent = translate(labelKey);
    label.append(input, span);
    picker.append(label);
  });
  loadSavedScheduleViews();
}

function scheduledOrderFilteredRows() {
  const search = document.getElementById("scheduled-order-search").value.trim().toLowerCase();
  const releaseStatus = document.getElementById("scheduled-order-release-filter").value;
  const bufferZone = document.getElementById("scheduled-order-buffer-filter").value;
  const rows = scheduledOrdersData.Rows.filter((row) => {
    if (search && !`${row.OrderID} ${row.ProductID || ""}`.toLowerCase().includes(search)) return false;
    if (releaseStatus && row.ReleaseStatus !== releaseStatus) return false;
    if (bufferZone && row.BufferZone !== bufferZone) return false;
    return true;
  });
  const { key, direction } = scheduledOrdersSort;
  rows.sort((left, right) => {
    const a = left[key] ?? "";
    const b = right[key] ?? "";
    const comparison = typeof a === "number" && typeof b === "number" ? a - b : String(a).localeCompare(String(b));
    return direction === "asc" ? comparison : -comparison;
  });
  return rows;
}

function scheduledOrderDisplayValue(row, key) {
  if (["OrderDate", "PlannedReleaseAt", "FinalDemandDate", "PromiseDate"].includes(key)) return formatDate(row[key]);
  if (key === "ResourceIDs") return (row.ResourceIDs || []).join(", ") || "-";
  if (key === "OnTimeStatus") return deliveryStatusLabel(row.OnTimeStatus);
  if (key === "ReleaseStatus") return row.ReleaseStatus === "Authorized" ? translate("authorized") : translate("notReleased");
  return row[key] ?? "-";
}

function renderScheduledOrders() {
  if (!scheduledOrdersData) return;
  const body = document.getElementById("scheduled-orders-table-body");
  body.replaceChildren();
  setText("scheduled-orders-generated-at", `${translate("generatedAt")}: ${formatDate(scheduledOrdersData.ViewMetadata.GeneratedAt)}`);
  const freshness = document.getElementById("scheduled-orders-freshness");
  setStatusChip(freshness, translate(scheduledOrdersData.ViewMetadata.IsStale ? "planStale" : "planCurrent"), scheduledOrdersData.ViewMetadata.IsStale ? "is-warning" : "is-valid");
  document.querySelectorAll("#scheduled-orders-table [data-column]").forEach((cell) => { cell.hidden = !visibleScheduledOrderColumns.has(cell.dataset.column); });
  const allRows = scheduledOrderFilteredRows();
  const pageSize = Number(document.getElementById("scheduled-orders-page-size").value);
  const pages = Math.max(Math.ceil(allRows.length / pageSize), 1);
  scheduledOrdersPage = Math.min(scheduledOrdersPage, pages);
  const pageRows = allRows.slice((scheduledOrdersPage - 1) * pageSize, scheduledOrdersPage * pageSize);
  const groupKey = document.getElementById("scheduled-order-group").value;
  let previousGroup = Symbol("none");
  pageRows.forEach((rowData) => {
    const groupValue = groupKey ? rowData[groupKey] ?? translate("notProvided") : null;
    if (groupKey && groupValue !== previousGroup) {
      previousGroup = groupValue;
      const groupRow = document.createElement("tr");
      groupRow.className = "group-row";
      const groupCell = document.createElement("td");
      groupCell.colSpan = 14;
      groupCell.textContent = `${translate({ ReleaseStatus: "releaseStatus", BufferZone: "bufferZone", RoutingID: "routing" }[groupKey])}: ${groupValue}`;
      groupRow.append(groupCell);
      body.append(groupRow);
    }
    const row = document.createElement("tr");
    const selectionCell = document.createElement("td");
    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.checked = selectedScheduledOrderIDs.has(rowData.OrderID);
    checkbox.addEventListener("change", () => {
      if (checkbox.checked) selectedScheduledOrderIDs.add(rowData.OrderID);
      else selectedScheduledOrderIDs.delete(rowData.OrderID);
      updateScheduledOrderSelection();
    });
    selectionCell.append(checkbox);
    row.append(selectionCell);
    SCHEDULED_ORDER_COLUMNS.forEach(([key]) => {
      const cell = document.createElement("td");
      cell.dataset.column = key;
      cell.hidden = !visibleScheduledOrderColumns.has(key);
      if (key === "OrderID") {
        const button = document.createElement("button");
        button.type = "button";
        button.className = "run-link";
        button.textContent = rowData.OrderID;
        button.addEventListener("click", () => openScheduledOrderDetail(rowData.OrderID));
        cell.append(button);
        if (rowData.IsLocked) {
          const locked = document.createElement("span");
          locked.className = "lock-indicator";
          locked.textContent = translate("lock");
          cell.append(locked);
        }
      } else cell.textContent = scheduledOrderDisplayValue(rowData, key);
      row.append(cell);
    });
    const actions = document.createElement("td");
    const view = document.createElement("button");
    view.type = "button";
    view.className = "run-action";
    view.textContent = translate("view");
    view.addEventListener("click", () => openScheduledOrderDetail(rowData.OrderID));
    actions.append(view);
    row.append(actions);
    body.append(row);
  });
  setText("scheduled-orders-page-info", translateWith("pageOf", { page: scheduledOrdersPage, pages }));
  document.getElementById("scheduled-orders-previous").disabled = scheduledOrdersPage <= 1;
  document.getElementById("scheduled-orders-next").disabled = scheduledOrdersPage >= pages;
  document.getElementById("select-all-scheduled-orders").checked = pageRows.length > 0 && pageRows.every((row) => selectedScheduledOrderIDs.has(row.OrderID));
  updateScheduledOrderSelection();
}

function updateScheduledOrderSelection() {
  const count = selectedScheduledOrderIDs.size;
  setText("scheduled-order-selection-count", count ? translateWith("selectedCount", { count }) : translate("noneSelected"));
  ["lock-scheduled-orders", "unlock-scheduled-orders", "priority-scheduled-orders", "evaluate-scheduled-orders-release"].forEach((id) => { document.getElementById(id).disabled = count === 0; });
}

async function executeScheduledOrderCommand(command) {
  if (!selectedScheduledOrderIDs.size) return;
  let priority = null;
  if (command === "SetPriority") {
    const value = window.prompt(translate("priorityPrompt"), "1");
    if (value === null) return;
    priority = Number(value);
    if (!Number.isInteger(priority) || priority < 1 || priority > 999) return;
  }
  const response = await fetch(`/planner/workbench/schedule-results/runs/${encodeURIComponent(selectedScheduleRunID)}/work-orders/commands`, {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ Command: command, OrderIDs: [...selectedScheduledOrderIDs], ActorID: "planner", OccurredAt: new Date().toISOString(), Priority: priority })
  });
  if (response.ok) {
    setText("route-status", translate("commandRecorded"));
    await loadScheduledOrders(selectedScheduleRunID);
  }
}

async function openScheduledOrderDetail(orderId) {
  const response = await fetch(`/planner/workbench/schedule-results/runs/${encodeURIComponent(selectedScheduleRunID)}/work-orders/${encodeURIComponent(orderId)}/workbench`);
  if (!response.ok) return;
  const detail = (await response.json()).Data;
  setText("scheduled-order-detail-title", orderId);
  const content = document.getElementById("scheduled-order-detail-content");
  content.replaceChildren();
  content.append(detailSection("workOrderDetail", [
    ["product", detail.Order.ProductID], ["routing", detail.Order.RoutingID],
    ["plannedRelease", formatDate(detail.Order.PlannedReleaseAt)], ["promiseDate", formatDate(detail.Order.PromiseDate)],
    ["releaseStatus", scheduledOrderDisplayValue(detail.Order, "ReleaseStatus")], ["executionPriority", detail.Order.ExecutionPriority]
  ]));
  content.append(listSection("operations", detail.Operations, (item) => `${item.OperationID} · ${item.ResourceID} · ${formatDate(item.Start)} - ${formatDate(item.End)}`));
  content.append(listSection("auditHistory", detail.AuditEvents, (item) => `${item.Action} · ${item.ActorID} · ${formatDate(item.OccurredAt)}`));
  openSideDrawer("scheduled-order-detail");
}

function scheduleViews() {
  try { return JSON.parse(localStorage.getItem(SCHEDULE_VIEW_STORAGE_KEY) || "{}"); } catch (_error) { return {}; }
}

function loadSavedScheduleViews() {
  const select = document.getElementById("scheduled-order-saved-view");
  const previous = select.value;
  const views = scheduleViews();
  select.replaceChildren();
  const defaultOption = document.createElement("option");
  defaultOption.value = "";
  defaultOption.textContent = translate("defaultView");
  select.append(defaultOption);
  Object.keys(views).sort().forEach((name) => {
    const option = document.createElement("option");
    option.value = name;
    option.textContent = name;
    select.append(option);
  });
  if (views[previous]) select.value = previous;
}

function saveScheduledOrderView() {
  const name = window.prompt(translate("viewNamePrompt"), "");
  if (!name?.trim()) return;
  const views = scheduleViews();
  views[name.trim()] = {
    releaseStatus: document.getElementById("scheduled-order-release-filter").value,
    bufferZone: document.getElementById("scheduled-order-buffer-filter").value,
    group: document.getElementById("scheduled-order-group").value,
    pageSize: document.getElementById("scheduled-orders-page-size").value,
    columns: [...visibleScheduledOrderColumns]
  };
  localStorage.setItem(SCHEDULE_VIEW_STORAGE_KEY, JSON.stringify(views));
  loadSavedScheduleViews();
  document.getElementById("scheduled-order-saved-view").value = name.trim();
}

function applyScheduledOrderView(name) {
  const view = scheduleViews()[name];
  if (!view) return;
  document.getElementById("scheduled-order-release-filter").value = view.releaseStatus || "";
  document.getElementById("scheduled-order-buffer-filter").value = view.bufferZone || "";
  document.getElementById("scheduled-order-group").value = view.group || "";
  document.getElementById("scheduled-orders-page-size").value = view.pageSize || "10";
  visibleScheduledOrderColumns = new Set(view.columns || visibleScheduledOrderColumns);
  scheduledOrdersPage = 1;
  prepareScheduledOrderControls();
  document.getElementById("scheduled-order-saved-view").value = name;
  renderScheduledOrders();
}

function toLocalDateTimeInput(value) {
  const local = new Date(value.getTime() - value.getTimezoneOffset() * 60000);
  return local.toISOString().slice(0, 16);
}

async function loadReleaseManagementRuns() {
  try {
    const response = await fetch("/planner/workbench/planning-runs/workbench");
    if (!response.ok) throw new Error(String(response.status));
    const runs = (await response.json()).Data.Rows.filter((run) => run.Status === "Completed");
    const select = document.getElementById("release-run-select");
    replaceSelectOptions(select, runs, { valueKey: "RunID", labelKey: "RunID" });
    if (!runs.length) {
      document.getElementById("release-management-empty").hidden = false;
      document.getElementById("release-management-content").hidden = true;
      return;
    }
    const preferred = selectedReleaseRunID || selectedScheduleRunID;
    selectedReleaseRunID = runs.some((run) => run.RunID === preferred) ? preferred : runs[0].RunID;
    select.value = selectedReleaseRunID;
    if (!document.getElementById("release-evaluated-at").value) document.getElementById("release-evaluated-at").value = toLocalDateTimeInput(new Date());
    document.getElementById("release-management-empty").hidden = true;
    await loadReleaseManagement();
  } catch (_error) {
    document.getElementById("release-management-error").hidden = false;
  }
}

async function loadReleaseManagement() {
  const runId = document.getElementById("release-run-select").value;
  const evaluatedValue = document.getElementById("release-evaluated-at").value;
  if (!runId || !evaluatedValue) return;
  selectedReleaseRunID = runId;
  try {
    const query = new URLSearchParams({ evaluated_at: new Date(evaluatedValue).toISOString(), operational_state_max_age_minutes: "60" });
    const response = await fetch(`/planner/workbench/release-management/runs/${encodeURIComponent(runId)}/workbench?${query}`);
    if (!response.ok) throw new Error(String(response.status));
    releaseManagementData = (await response.json()).Data;
    renderReleaseManagement();
    document.getElementById("release-management-content").hidden = false;
    document.getElementById("release-management-error").hidden = true;
  } catch (_error) {
    document.getElementById("release-management-content").hidden = true;
    document.getElementById("release-management-error").hidden = false;
  }
}

function gateStatusLabel(value) {
  return translate({ Clear: "clear", Ready: "clear", Early: "early", Blocked: "blocked", PendingInbound: "inbound" }[value] || value);
}

function renderReleaseManagement() {
  document.querySelectorAll("[data-release-summary]").forEach((element) => { element.textContent = releaseManagementData.Summary[element.dataset.releaseSummary] ?? 0; });
  const snapshot = document.getElementById("release-snapshot-status");
  snapshot.textContent = `${translate("snapshotStatus")}: ${translate({ Fresh: "freshSnapshot", Stale: "staleSnapshot", Future: "futureSnapshot" }[releaseManagementData.OperationalStateStatus])} · ${releaseManagementData.OperationalStateSnapshotID} · ${formatDate(releaseManagementData.OperationalStateCapturedAt)}`;
  const body = document.getElementById("release-candidate-table-body");
  body.replaceChildren();
  releaseManagementData.Candidates.forEach((candidate) => {
    const row = document.createElement("tr");
    row.append(textCell(candidate.ExecutionPriority), textCell(candidate.OrderID));
    const zoneCell = document.createElement("td");
    const zone = document.createElement("span");
    zone.className = `buffer-chip ${candidate.BufferZone}`;
    zone.textContent = candidate.BufferZone;
    zoneCell.append(zone);
    row.append(zoneCell, textCell(`${candidate.BufferPenetrationPercent}%`), textCell(formatDate(candidate.SuggestedReleaseAt)));
    [candidate.MaterialStatus, candidate.WipStatus].forEach((status) => {
      const cell = document.createElement("td");
      const label = document.createElement("span");
      label.className = `gate-status ${status === "Clear" ? "is-clear" : "is-blocked"}`;
      label.textContent = gateStatusLabel(status);
      cell.append(label);
      row.append(cell);
    });
    row.append(textCell(formatDate(candidate.ScheduledStart)));
    const reasonCell = document.createElement("td");
    const reasonButton = document.createElement("button");
    reasonButton.type = "button";
    reasonButton.className = "run-action";
    reasonButton.textContent = candidate.BlockingReasons.length ? `${candidate.BlockingReasons.length} · ${translate("viewReason")}` : translate("noBlockReason");
    reasonButton.addEventListener("click", () => openReleaseReasons(candidate));
    reasonCell.append(reasonButton);
    const actions = document.createElement("td");
    actions.className = "release-actions";
    const authorize = document.createElement("button");
    authorize.type = "button";
    authorize.textContent = translate("authorizeRelease");
    authorize.disabled = !candidate.CanAuthorize;
    authorize.addEventListener("click", () => authorizeReleaseCandidate(candidate));
    actions.append(authorize);
    if (candidate.AuthorizationID) {
      const dispatch = document.createElement("button");
      dispatch.type = "button";
      dispatch.textContent = translate("viewDispatch");
      dispatch.addEventListener("click", () => openDispatchPackage(candidate.AuthorizationID));
      actions.append(dispatch);
    }
    row.append(reasonCell, actions);
    body.append(row);
  });
}

function openReleaseReasons(candidate) {
  const content = document.getElementById("release-reason-content");
  content.replaceChildren();
  if (!candidate.BlockingReasons.length) {
    const empty = document.createElement("div");
    empty.className = "table-empty";
    empty.textContent = translate("noBlockReason");
    content.append(empty);
  } else {
    candidate.BlockingReasons.forEach((reason) => {
      const item = document.createElement("section");
      item.className = "detail-section";
      const title = document.createElement("h3");
      title.textContent = translate(`reason_${reason.Code}`);
      const code = document.createElement("span");
      code.className = "issue-meta";
      code.textContent = reason.Code;
      item.append(title, code);
      content.append(item);
    });
  }
  openSideDrawer("release-reason-detail");
}

async function authorizeReleaseCandidate(candidate) {
  if (!candidate.CanAuthorize || !(await confirmAction({ message: translate("authorizeImpact"), context: `${translate("workOrder")}: ${candidate.OrderID}` }))) return;
  const response = await fetch(`/planner/workbench/release-management/runs/${encodeURIComponent(selectedReleaseRunID)}/orders/${encodeURIComponent(candidate.OrderID)}/authorize`, {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ReleasedBy: "planner", ReleasedAt: new Date(document.getElementById("release-evaluated-at").value).toISOString(), OperationalStateMaxAgeMinutes: 60 })
  });
  if (response.ok) {
    setText("route-status", translate("releaseAuthorized"));
    showNotification(translate("releaseAuthorized"), "success");
    await loadReleaseManagement();
  } else {
    document.getElementById("release-management-error").hidden = false;
    showNotification(translate("notifyError"), "error");
  }
}

async function openDispatchPackage(authorizationId) {
  const response = await fetch(`/planner/workbench/release-authorizations/${encodeURIComponent(authorizationId)}/dispatch-package`);
  if (!response.ok) return;
  const packageData = (await response.json()).Data.DispatchPackage;
  setText("dispatch-package-title", authorizationId);
  const content = document.getElementById("dispatch-package-content");
  content.replaceChildren();
  content.append(detailSection("dispatchPackage", [
    ["workOrder", packageData.OrderID], ["releaseStatus", packageData.DispatchStatus],
    ["plannedStart", formatDate(packageData.ScheduledStart)], ["plannedCompletion", formatDate(packageData.ScheduledEnd)],
    ["snapshotLabel", packageData.OperationalStateSnapshotID]
  ]));
  openSideDrawer("dispatch-package-detail");
}

async function loadBufferBoardRuns() {
  try {
    const response = await fetch("/planner/workbench/planning-runs/workbench");
    if (!response.ok) throw new Error(String(response.status));
    const runs = (await response.json()).Data.Rows.filter((run) => run.Status === "Completed");
    const select = document.getElementById("buffer-run-select");
    replaceSelectOptions(select, runs, { valueKey: "RunID", labelKey: "RunID" });
    if (!runs.length) {
      document.getElementById("buffer-board-empty").hidden = false;
      document.getElementById("buffer-board-content").hidden = true;
      return;
    }
    const preferred = selectedBufferRunID || selectedReleaseRunID || selectedScheduleRunID;
    selectedBufferRunID = runs.some((run) => run.RunID === preferred) ? preferred : runs[0].RunID;
    select.value = selectedBufferRunID;
    if (!document.getElementById("buffer-evaluated-at").value) document.getElementById("buffer-evaluated-at").value = toLocalDateTimeInput(new Date());
    document.getElementById("buffer-board-empty").hidden = true;
    await loadBufferBoard();
  } catch (_error) {
    document.getElementById("buffer-board-error").hidden = false;
  }
}

async function loadBufferBoard() {
  const runId = document.getElementById("buffer-run-select").value;
  const evaluatedValue = document.getElementById("buffer-evaluated-at").value;
  if (!runId || !evaluatedValue) return;
  selectedBufferRunID = runId;
  try {
    const query = new URLSearchParams({ evaluated_at: new Date(evaluatedValue).toISOString() });
    const response = await fetch(`/planner/workbench/buffer-board/runs/${encodeURIComponent(runId)}/workbench?${query}`);
    if (!response.ok) throw new Error(String(response.status));
    bufferBoardData = (await response.json()).Data;
    renderBufferBoard();
    document.getElementById("buffer-board-content").hidden = false;
    document.getElementById("buffer-board-error").hidden = true;
  } catch (_error) {
    document.getElementById("buffer-board-content").hidden = true;
    document.getElementById("buffer-board-error").hidden = false;
  }
}

function renderBufferBoard() {
  const context = bufferBoardData.Context;
  const summary = document.getElementById("buffer-context-summary");
  summary.replaceChildren();
  [
    ["location", context.LocationID], ["constraint", `${context.ConstraintResourceName || "-"} · ${context.ConstraintResourceID || "-"}`],
    ["bufferOwner", context.BufferOwnerID], ["dailyLoad", `${(context.DailyLoadMinutes / 60).toFixed(1)} ${translate("hours")}`],
    ["lastScheduled", formatDate(context.LastScheduledAt)]
  ].forEach(([labelKey, value]) => summary.append(detailMetric(labelKey, value)));

  const matrix = document.getElementById("buffer-board-matrix");
  matrix.replaceChildren();
  const corner = document.createElement("div");
  corner.className = "buffer-matrix-corner";
  corner.textContent = translate("receiveStatus");
  matrix.append(corner);
  ["Early", "Green", "Yellow", "Red", "Late"].forEach((zone) => {
    const header = document.createElement("div");
    header.className = `buffer-zone-header zone-${zone}`;
    header.textContent = translate(zone);
    matrix.append(header);
  });
  bufferBoardData.Rows.forEach((row) => {
    const stage = document.createElement("div");
    stage.className = "buffer-stage-header";
    stage.textContent = translate(row.Stage === "Received" ? "received" : "yetToBeReceived");
    matrix.append(stage);
    row.Cells.forEach((cell) => matrix.append(bufferMatrixCell(cell)));
  });
}

function detailMetric(labelKey, value) {
  const metric = document.createElement("div");
  const label = document.createElement("span");
  label.textContent = translate(labelKey);
  const strong = document.createElement("strong");
  strong.textContent = displayValue(value);
  metric.append(label, strong);
  return metric;
}

function bufferMatrixCell(cell) {
  const element = document.createElement("section");
  element.className = `buffer-matrix-cell zone-${cell.Zone}`;
  const summary = document.createElement("div");
  summary.className = "buffer-cell-summary";
  summary.textContent = `${translate("orderCount")} ${cell.OrderCount} · ${translate("totalLoad")} ${(cell.TotalLoadMinutes / 60).toFixed(1)} ${translate("hours")}`;
  element.append(summary);
  cell.Orders.forEach((order) => {
    const card = document.createElement("button");
    card.type = "button";
    card.className = "buffer-order-card";
    const title = document.createElement("strong");
    title.textContent = order.OrderID;
    const product = document.createElement("span");
    product.textContent = displayValue(order.ProductID);
    const measure = document.createElement("small");
    measure.textContent = `${translate("Quantity")}: ${displayValue(order.Quantity)} · ${(order.LoadMinutes / 60).toFixed(1)} ${translate("hours")}`;
    card.append(title, product, measure);
    card.addEventListener("click", () => openBufferOrderDetail(order.OrderID));
    element.append(card);
  });
  return element;
}

async function openBufferOrderDetail(orderId) {
  const evaluatedAt = new Date(document.getElementById("buffer-evaluated-at").value).toISOString();
  const query = new URLSearchParams({ evaluated_at: evaluatedAt });
  const response = await fetch(`/planner/workbench/buffer-board/runs/${encodeURIComponent(selectedBufferRunID)}/orders/${encodeURIComponent(orderId)}/workbench?${query}`);
  if (!response.ok) return;
  selectedBufferOrder = (await response.json()).Data;
  setText("buffer-order-detail-title", orderId);
  const content = document.getElementById("buffer-order-detail-content");
  content.replaceChildren();
  content.append(
    detailSection("bufferOrderDetail", [
      ["product", selectedBufferOrder.Order.ProductID], ["customer", selectedBufferOrder.Order.CustomerID],
      ["promiseDate", formatDate(selectedBufferOrder.Order.PromiseDate)], ["executionPriority", selectedBufferOrder.Order.Priority],
      ["receiveStatus", translate(selectedBufferOrder.Execution.Stage === "Received" ? "received" : "yetToBeReceived")],
      ["bufferZone", translate(selectedBufferOrder.Execution.Zone)], ["currentReason", selectedBufferOrder.Execution.CurrentReasonCode ? reasonCodeLabel(selectedBufferOrder.Execution.CurrentReasonCode) : translate("notProvided")]
    ])
  );
  const action = document.createElement("button");
  action.type = "button";
  action.className = "button primary";
  action.textContent = translate("receiveOrStart");
  action.addEventListener("click", openBufferTransactionDialog);
  content.append(action);
  openSideDrawer("buffer-order-detail");
}

function reasonCodeLabel(code) {
  return translate(`reason_${code}_CODE`);
}

function openBufferTransactionDialog() {
  const policy = selectedBufferOrder.TransactionPolicy;
  const measure = document.getElementById("buffer-transaction-measure");
  measure.replaceChildren(...policy.MeasureTypes.map((type) => new Option(translate(type), type)));
  const reason = document.getElementById("buffer-transaction-reason");
  reason.replaceChildren(new Option(translate("selectReason"), ""), ...policy.ExceptionCodes.map((item) => new Option(reasonCodeLabel(item.Code), item.Code)));
  document.getElementById("buffer-transaction-at").value = toLocalDateTimeInput(new Date());
  document.getElementById("buffer-transaction-value").value = "";
  const required = policy.ReasonRequiredZones.includes(selectedBufferOrder.Execution.Zone);
  reason.required = required;
  document.getElementById("buffer-transaction-guidance").hidden = !required;
  setText("buffer-transaction-title", selectedBufferOrder.Order.OrderID);
  document.getElementById("buffer-transaction-dialog").showModal();
}

async function submitBufferTransaction(event) {
  event.preventDefault();
  const payload = {
    EventType: document.getElementById("buffer-transaction-event").value,
    EventAt: new Date(document.getElementById("buffer-transaction-at").value).toISOString(),
    ActorID: "operator",
    MeasureType: document.getElementById("buffer-transaction-measure").value,
    MeasureValue: Number(document.getElementById("buffer-transaction-value").value),
    ExceptionCode: document.getElementById("buffer-transaction-reason").value || null
  };
  const response = await fetch(`/planner/workbench/buffer-board/runs/${encodeURIComponent(selectedBufferRunID)}/orders/${encodeURIComponent(selectedBufferOrder.Order.OrderID)}/transactions`, {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload)
  });
  if (!response.ok) {
    const result = await response.json();
    document.getElementById("buffer-transaction-guidance").textContent = result.Data?.Status === "ReasonCodeRequired" ? translate("reasonRequiredForLate") : translate("actionFailed");
    document.getElementById("buffer-transaction-guidance").hidden = false;
    return;
  }
  document.getElementById("buffer-transaction-dialog").close();
  closeSideDrawer("buffer-order-detail");
  setText("route-status", translate("transactionRecorded"));
  await loadBufferBoard();
}

async function loadExceptionCenter() {
  if (!document.getElementById("exception-evaluated-at").value) document.getElementById("exception-evaluated-at").value = toLocalDateTimeInput(new Date());
  const evaluatedAt = new Date(document.getElementById("exception-evaluated-at").value).toISOString();
  try {
    const query = new URLSearchParams({ evaluated_at: evaluatedAt });
    const response = await fetch(`/planner/workbench/exceptions/workbench?${query}`);
    if (!response.ok) throw new Error(String(response.status));
    exceptionCenterData = (await response.json()).Data;
    prepareExceptionFilters();
    renderExceptionCenter();
    document.getElementById("exception-center-content").hidden = false;
    document.getElementById("exception-center-error").hidden = true;
  } catch (_error) {
    document.getElementById("exception-center-content").hidden = true;
    document.getElementById("exception-center-error").hidden = false;
  }
}

function prepareExceptionFilters() {
  const severity = document.getElementById("exception-severity-filter");
  const severityValue = severity.value;
  severity.replaceChildren(new Option(translate("allSeverities"), ""), ...exceptionCenterData.FilterOptions.Severities.map((item) => new Option(translate(item), item)));
  severity.value = [...severity.options].some((option) => option.value === severityValue) ? severityValue : "";
  const source = document.getElementById("exception-source-filter");
  const sourceValue = source.value;
  source.replaceChildren(new Option(translate("allSources"), ""), ...exceptionCenterData.FilterOptions.Sources.map((item) => new Option(item, item)));
  source.value = [...source.options].some((option) => option.value === sourceValue) ? sourceValue : "";
}

function exceptionRows() {
  const severity = document.getElementById("exception-severity-filter").value;
  const source = document.getElementById("exception-source-filter").value;
  return (exceptionCenterData?.Rows || []).filter((row) => (!severity || row.Severity === severity) && (!source || row.Source === source));
}

function renderExceptionCenter() {
  document.querySelectorAll("[data-exception-summary]").forEach((element) => { element.textContent = exceptionCenterData.Summary[element.dataset.exceptionSummary] ?? 0; });
  const body = document.getElementById("exception-center-table-body");
  body.replaceChildren();
  const rows = exceptionRows();
  if (!rows.length) {
    const row = document.createElement("tr");
    const cell = document.createElement("td");
    cell.colSpan = 8;
    cell.className = "empty-cell";
    cell.textContent = translate("noIssues");
    row.append(cell);
    body.append(row);
    return;
  }
  rows.forEach((exception) => {
    const row = document.createElement("tr");
    const severity = document.createElement("td");
    const chip = document.createElement("span");
    chip.className = `severity-chip ${exception.Severity}`;
    chip.textContent = translate(exception.Severity);
    severity.append(chip);
    row.append(severity);
    row.append(textCell(`${translate(`type_${exception.ExceptionType}`)} · ${exception.ObjectType} ${exception.ObjectID}`));
    row.append(textCell(formatDate(exception.OccurredAt)));
    row.append(textCell(exception.ReasonCode));
    row.append(textCell(translate(`impact_${exception.BusinessImpactCode}`)));
    row.append(textCell(translate(`action_${exception.SuggestedActionCode}`)));
    row.append(textCell(exception.OwnerID));
    const actions = document.createElement("td");
    const button = document.createElement("button");
    button.type = "button";
    button.className = "run-action";
    button.textContent = translate("viewDetail");
    button.addEventListener("click", () => openExceptionDetail(exception.ExceptionID));
    actions.append(button);
    row.append(actions);
    body.append(row);
  });
}

async function openExceptionDetail(exceptionId) {
  const evaluatedAt = new Date(document.getElementById("exception-evaluated-at").value).toISOString();
  const query = new URLSearchParams({ evaluated_at: evaluatedAt });
  const response = await fetch(`/planner/workbench/exceptions/${encodeURIComponent(exceptionId)}/workbench?${query}`);
  if (!response.ok) return;
  const detail = (await response.json()).Data;
  setText("exception-detail-title", detail.Exception.ObjectID);
  const content = document.getElementById("exception-detail-content");
  content.replaceChildren();
  content.append(detailSection("exceptionDetail", [
    ["severity", translate(detail.Exception.Severity)], ["object", `${detail.Exception.ObjectType} ${detail.Exception.ObjectID}`],
    ["occurredAt", formatDate(detail.Exception.OccurredAt)], ["reasonCode", detail.Exception.ReasonCode],
    ["businessImpact", translate(`impact_${detail.Exception.BusinessImpactCode}`)], ["suggestedAction", translate(`action_${detail.Exception.SuggestedActionCode}`)],
    ["owner", detail.Exception.OwnerID], ["source", detail.Exception.Source]
  ]));
  content.append(detailSection("relatedObjects", detail.RelatedObjects.map((item) => [item.Relationship, `${item.ObjectType} ${item.ObjectID}`])));
  content.append(detailSection("resolutionActions", detail.ResolutionActions.map((item) => ["suggestedAction", translate(`action_${item.ActionCode}`)])));
  if (detail.Exception.AuditTrail.length) {
    content.append(detailSection("auditTrail", detail.Exception.AuditTrail.map((item) => [item.Action, `${formatDate(item.OccurredAt)} · ${displayValue(item.ActorID)}`])));
  } else {
    content.append(detailSection("auditTrail", [["auditTrail", translate("noAuditTrail")]]));
  }
  openSideDrawer("exception-detail");
}

async function loadAdministration() {
  try {
    const response = await fetch("/planner/workbench/administration/workbench", { headers: { Accept: "application/json" } });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const payload = await response.json();
    administrationData = payload.Data;
    renderAdministration();
    document.getElementById("administration-error").hidden = true;
    document.getElementById("administration-content").hidden = false;
  } catch (_error) {
    document.getElementById("administration-error").hidden = false;
    document.getElementById("administration-content").hidden = true;
  }
}

function renderAdministration() {
  if (!administrationData) return;
  setText("admin-mode-chip", translate("readOnly"));
  renderAdminObjects(administrationData.MasterDataObjects || []);
  renderAdminCapabilities(administrationData);
  renderAdminPolicyGroups(administrationData.PolicyGroups || []);
  renderAdminCalendarLayers(administrationData.CalendarLayers || []);
}

function renderAdminObjects(objects) {
  const container = document.getElementById("admin-master-data-objects");
  container.replaceChildren();
  objects.forEach((item) => {
    const card = document.createElement("button");
    card.type = "button";
    card.className = "admin-object-card";
    const title = document.createElement("strong");
    title.textContent = translate(item.LabelKey) || item.ObjectKey;
    const count = document.createElement("span");
    count.textContent = `${translate("objectCount")}: ${item.CurrentCount}`;
    const endpoint = document.createElement("small");
    endpoint.textContent = `${translate("importEndpoint")}: ${item.ImportEndpoint}`;
    const fields = document.createElement("p");
    fields.textContent = `${translate("reservedFields")}: ${(item.ReservedFields || []).join(", ")}`;
    const flags = document.createElement("div");
    flags.className = "admin-card-flags";
    [translate("structuredPreview"), translate("preValidationRequired"), translate("versionAfterImport")].forEach((label) => {
      const chip = document.createElement("span");
      chip.className = "status-chip neutral";
      chip.textContent = label;
      flags.append(chip);
    });
    card.append(title, count, endpoint, fields, flags);
    card.addEventListener("click", () => selectAdminImportObject(item));
    container.append(card);
  });
}

function selectAdminImportObject(item) {
  const preview = document.getElementById("admin-preview-table");
  preview.className = "admin-selected-preview";
  preview.replaceChildren(detailSection(item.LabelKey, [
    ["importEndpoint", item.ImportEndpoint],
    ["reservedFields", (item.ReservedFields || []).join(", ")],
    ["preValidationRequired", translate("preValidationRequired")],
    ["versionAfterImport", translate("versionAfterImport")]
  ]));
  document.getElementById("admin-validate-import").disabled = false;
}

function renderAdminCapabilities(data) {
  const container = document.getElementById("admin-system-capabilities");
  container.replaceChildren();
  const rows = [
    ...(data.Solvers || []).map((item) => ({ name: item.DisplayName, status: item.Status, detail: translate("solver") })),
    ...(data.Integrations || []).map((item) => ({ name: item.DisplayName, status: item.Status, detail: `${translate("lastSync")}: ${displayValue(item.LastSyncAt)}` })),
    { name: translate("workerQueue"), status: data.WorkerQueue?.Status, detail: `${translate("queued")}: ${data.WorkerQueue?.QueuedCount || 0} · ${translate("running")}: ${data.WorkerQueue?.RunningCount || 0}` },
    { name: translate("stateStore"), status: data.StateStore?.Status, detail: `${data.StateStore?.Backend || "-"} · Rev ${data.StateStore?.Revision ?? "-"}` }
  ];
  rows.forEach((row) => {
    const card = document.createElement("div");
    card.className = "capability-card";
    const title = document.createElement("strong");
    title.textContent = row.name;
    const status = document.createElement("span");
    status.className = `status-chip ${row.status === "Available" || row.status === "Healthy" || row.status === "Online" ? "is-valid" : "neutral"}`;
    status.textContent = translate(row.status) || row.status || "-";
    const detail = document.createElement("small");
    detail.textContent = row.detail;
    card.append(title, status, detail);
    container.append(card);
  });
}

function renderAdminPolicyGroups(groups) {
  const container = document.getElementById("admin-policy-groups");
  container.replaceChildren();
  groups.forEach((group) => {
    const row = document.createElement("div");
    row.className = "policy-group";
    const title = document.createElement("strong");
    title.textContent = translate(group.GroupKey);
    const values = document.createElement("span");
    values.textContent = (group.Options || []).map((option) => translate(option)).join(" / ");
    row.append(title, values);
    container.append(row);
  });
}

function renderAdminCalendarLayers(layers) {
  const container = document.getElementById("admin-calendar-layers");
  container.replaceChildren();
  layers.forEach((layer, index) => {
    const item = document.createElement("div");
    item.className = "calendar-layer";
    const order = document.createElement("span");
    order.textContent = String(index + 1).padStart(2, "0");
    const label = document.createElement("strong");
    label.textContent = translate(layer);
    item.append(order, label);
    container.append(item);
  });
}

function openSideDrawer(id) {
  const drawer = document.getElementById(id);
  drawer.hidden = false;
  drawer.classList.add("is-open");
  drawer.setAttribute("aria-hidden", "false");
  document.getElementById("drawer-backdrop").hidden = false;
}

function closeSideDrawer(id) {
  const drawer = document.getElementById(id);
  drawer.classList.remove("is-open");
  drawer.hidden = true;
  drawer.setAttribute("aria-hidden", "true");
  const anyOpen = [...document.querySelectorAll(".issues-drawer")].some((item) => !item.hidden);
  document.getElementById("drawer-backdrop").hidden = !anyOpen;
}

function isNarrowScreen() {
  return window.matchMedia("(max-width: 900px)").matches;
}

function toggleNavigation() {
  const shell = document.querySelector(".app-shell");
  const navigation = document.getElementById("primary-navigation");
  const backdrop = document.getElementById("navigation-backdrop");
  const button = document.getElementById("navigation-toggle");
  if (isNarrowScreen()) {
    const open = navigation.classList.toggle("is-open");
    backdrop.hidden = !open;
    button.setAttribute("aria-expanded", String(open));
    return;
  }
  shell.classList.toggle("nav-collapsed");
  button.setAttribute("aria-expanded", String(!shell.classList.contains("nav-collapsed")));
}

function closeMobileNavigation() {
  const navigation = document.getElementById("primary-navigation");
  navigation.classList.remove("is-open");
  document.getElementById("navigation-backdrop").hidden = true;
  document.getElementById("navigation-toggle").setAttribute("aria-expanded", "false");
}

async function loadSystemHealth() {
  const element = document.getElementById("system-health");
  try {
    const response = await fetch("/planner/workbench/state-store/health", { headers: { Accept: "application/json" } });
    if (!response.ok) throw new Error(String(response.status));
    await response.json();
    element.dataset.i18n = "healthy";
    element.textContent = translate("healthy");
    element.classList.remove("is-loading", "is-error");
  } catch (_error) {
    element.dataset.i18n = "unavailable";
    element.textContent = translate("unavailable");
    element.classList.remove("is-loading");
    element.classList.add("is-error");
  }
}

function formatContextDate(value) {
  return new Intl.DateTimeFormat(currentLanguage === "zh" ? "zh-CN" : "en-US", {
    dateStyle: "medium", timeStyle: "short"
  }).format(value);
}

document.addEventListener("DOMContentLoaded", () => {
  const languageSelect = document.getElementById("language-select");
  const language = storedLanguage();
  applyLanguage(language);
  languageSelect.addEventListener("change", () => {
    persistLanguage(languageSelect.value);
    applyLanguage(languageSelect.value);
  });
  document.getElementById("navigation-toggle").addEventListener("click", toggleNavigation);
  document.getElementById("navigation-backdrop").addEventListener("click", closeMobileNavigation);
  document.getElementById("refresh-case-acceptance").addEventListener("click", loadCaseAcceptance);
  document.getElementById("refresh-data-readiness").addEventListener("click", loadDataReadiness);
  document.getElementById("view-readiness-issues").addEventListener("click", openIssuesDrawer);
  document.getElementById("close-issues-drawer").addEventListener("click", closeIssuesDrawer);
  document.getElementById("drawer-backdrop").addEventListener("click", () => {
    closeIssuesDrawer();
    ["planning-run-detail", "scheduled-order-detail", "release-reason-detail", "dispatch-package-detail", "buffer-order-detail", "exception-detail"].forEach((id) => closeSideDrawer(id));
  });
  document.getElementById("select-planning-inputs").addEventListener("click", selectPlanningInputs);
  document.getElementById("create-master-data-version").addEventListener("click", () => { window.location.hash = "administration"; });
  document.getElementById("refresh-planning-runs").addEventListener("click", loadPlanningRuns);
  document.getElementById("planning-run-status-filter").addEventListener("change", renderPlanningRuns);
  document.getElementById("planning-run-time-filter").addEventListener("change", renderPlanningRuns);
  document.getElementById("planning-run-solver-filter").addEventListener("change", renderPlanningRuns);
  document.getElementById("planning-run-requester-filter").addEventListener("input", renderPlanningRuns);
  document.getElementById("planning-run-exception-filter").addEventListener("change", renderPlanningRuns);
  document.getElementById("create-planning-run").addEventListener("click", openPlanningRunWizard);
  document.getElementById("close-planning-run-wizard").addEventListener("click", () => document.getElementById("planning-run-wizard").close());
  document.getElementById("wizard-back").addEventListener("click", () => setWizardStep(Math.max(1, planningRunWizardStep - 1)));
  document.getElementById("wizard-next").addEventListener("click", () => setWizardStep(Math.min(3, planningRunWizardStep + 1)));
  document.getElementById("planning-run-form").addEventListener("submit", submitPlanningRun);
  document.getElementById("close-planning-run-detail").addEventListener("click", closePlanningRunDetail);
  document.getElementById("schedule-result-run-select").addEventListener("change", (event) => loadScheduleResult(event.target.value));
  document.getElementById("refresh-schedule-result").addEventListener("click", () => loadScheduleResult(selectedScheduleRunID));
  document.querySelectorAll("[data-schedule-tab]").forEach((button) => button.addEventListener("click", () => setScheduleTab(button.dataset.scheduleTab)));
  ["gantt-resource-filter", "gantt-order-filter", "gantt-type-filter", "gantt-zone-filter", "gantt-from-date", "gantt-to-date", "gantt-zoom"].forEach((id) => document.getElementById(id).addEventListener("change", renderGanttBoard));
  document.querySelectorAll("[data-load-view]").forEach((button) => button.addEventListener("click", () => setLoadView(button.dataset.loadView)));
  ["load-type-filter", "load-location-filter", "load-owner-filter", "load-category-filter"].forEach((id) => document.getElementById(id).addEventListener("change", renderSystemLoad));
  document.getElementById("resource-load-select").addEventListener("change", renderResourceLoad);
  document.getElementById("compare-scenarios").addEventListener("click", compareSelectedScenarios);
  document.getElementById("scheduled-order-search").addEventListener("input", () => { scheduledOrdersPage = 1; renderScheduledOrders(); });
  ["scheduled-order-release-filter", "scheduled-order-buffer-filter", "scheduled-order-group", "scheduled-orders-page-size"].forEach((id) => document.getElementById(id).addEventListener("change", () => { scheduledOrdersPage = 1; renderScheduledOrders(); }));
  document.querySelectorAll("[data-order-sort]").forEach((button) => button.addEventListener("click", () => {
    const key = button.dataset.orderSort;
    scheduledOrdersSort = { key, direction: scheduledOrdersSort.key === key && scheduledOrdersSort.direction === "asc" ? "desc" : "asc" };
    renderScheduledOrders();
  }));
  document.getElementById("scheduled-orders-previous").addEventListener("click", () => { scheduledOrdersPage -= 1; renderScheduledOrders(); });
  document.getElementById("scheduled-orders-next").addEventListener("click", () => { scheduledOrdersPage += 1; renderScheduledOrders(); });
  document.getElementById("select-all-scheduled-orders").addEventListener("change", (event) => {
    scheduledOrderFilteredRows().forEach((row) => { if (event.target.checked) selectedScheduledOrderIDs.add(row.OrderID); else selectedScheduledOrderIDs.delete(row.OrderID); });
    renderScheduledOrders();
  });
  document.getElementById("lock-scheduled-orders").addEventListener("click", () => executeScheduledOrderCommand("Lock"));
  document.getElementById("unlock-scheduled-orders").addEventListener("click", () => executeScheduledOrderCommand("Unlock"));
  document.getElementById("priority-scheduled-orders").addEventListener("click", () => executeScheduledOrderCommand("SetPriority"));
  document.getElementById("evaluate-scheduled-orders-release").addEventListener("click", () => { selectedReleaseRunID = selectedScheduleRunID; window.location.hash = "release-management"; });
  document.getElementById("replan-scheduled-orders").addEventListener("click", () => { window.location.hash = "planning-runs"; });
  document.getElementById("save-scheduled-order-view").addEventListener("click", saveScheduledOrderView);
  document.getElementById("scheduled-order-saved-view").addEventListener("change", (event) => applyScheduledOrderView(event.target.value));
  document.getElementById("close-scheduled-order-detail").addEventListener("click", () => closeSideDrawer("scheduled-order-detail"));
  document.getElementById("close-release-reason-detail").addEventListener("click", () => closeSideDrawer("release-reason-detail"));
  document.getElementById("close-dispatch-package-detail").addEventListener("click", () => closeSideDrawer("dispatch-package-detail"));
  document.getElementById("release-run-select").addEventListener("change", loadReleaseManagement);
  document.getElementById("refresh-release-management").addEventListener("click", loadReleaseManagement);
  document.getElementById("buffer-run-select").addEventListener("change", loadBufferBoard);
  document.getElementById("refresh-buffer-board").addEventListener("click", loadBufferBoard);
  document.getElementById("close-buffer-order-detail").addEventListener("click", () => closeSideDrawer("buffer-order-detail"));
  document.getElementById("close-buffer-transaction-dialog").addEventListener("click", () => document.getElementById("buffer-transaction-dialog").close());
  document.getElementById("cancel-buffer-transaction").addEventListener("click", () => document.getElementById("buffer-transaction-dialog").close());
  document.getElementById("buffer-transaction-form").addEventListener("submit", submitBufferTransaction);
  document.getElementById("refresh-exception-center").addEventListener("click", loadExceptionCenter);
  document.getElementById("exception-severity-filter").addEventListener("change", renderExceptionCenter);
  document.getElementById("exception-source-filter").addEventListener("change", renderExceptionCenter);
  document.getElementById("close-exception-detail").addEventListener("click", () => closeSideDrawer("exception-detail"));
  document.getElementById("refresh-administration").addEventListener("click", loadAdministration);
  document.getElementById("admin-routings-import").addEventListener("click", () => {
    const routingObject = (administrationData?.MasterDataObjects || []).find((item) => item.ObjectKey === "Routings");
    if (routingObject) selectAdminImportObject(routingObject);
  });
  window.addEventListener("hashchange", () => renderRoute(true));
  window.addEventListener("resize", () => { if (!isNarrowScreen()) closeMobileNavigation(); });
  loadSystemHealth();
});
