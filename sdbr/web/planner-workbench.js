const LANGUAGE_STORAGE_KEY = "sdbr.language";
const SCHEDULE_VIEW_STORAGE_KEY = "sdbr.scheduleViews";

const I18N = {
  zh: {
    primaryNavigation: "主导航", planningContext: "计划上下文", toggleNavigation: "切换导航",
    productName: "需求驱动计划员工作台", navOverview: "计划总览", navOperationalMetrics: "运营指标", navData: "数据就绪", navMaterials: "物料计划",
    navRuns: "排程任务", navResults: "排程结果", navRelease: "释放管理", navBuffer: "缓冲执行", navDispatch: "派工建议",
    navPublicDemo: "公开演示闭环", navExceptions: "异常中心", navCalendar: "日历配置", navAdmin: "管理后台", noUnreadExceptions: "无未读异常",
    apiConnected: "本地服务已连接", planningScope: "计划范围", defaultFactory: "默认工厂",
    masterDataVersionLabel: "主数据版本", snapshotLabel: "运行快照", systemHealthLabel: "系统健康",
    notSelected: "未选择", checking: "检查中", healthy: "健康", unavailable: "不可用",
    language: "语言", planner: "计划员", workspaceEyebrow: "计划员工作台",
    pageOverview: "计划总览", pageOperationalMetrics: "运营指标", pageData: "数据就绪", pageMaterials: "物料计划", pageRuns: "排程任务",
    pageResults: "排程结果", pageRelease: "释放管理", pageBuffer: "约束缓冲执行", pageDispatch: "派工建议", pagePublicDemo: "公开演示闭环", pageExceptions: "异常中心", pageCalendar: "日历配置", pageAdmin: "管理后台",
    descriptionOverview: "集中查看排程范围、异常和下一步工作。",
    descriptionOperationalMetrics: "按可靠性、稳定性和流速检查 DDOM 日常运行表现。",
    descriptionData: "检查主数据版本与运行状态快照。",
    descriptionMaterials: "按 DDMRP 缓冲状态处理物料净流和补货建议。",
    descriptionRuns: "创建、跟踪和恢复排程任务。",
    descriptionResults: "检查排程结果、负荷、甘特图和诊断。",
    descriptionRelease: "依据绳长、物料、WIP 和缓冲管理工单释放。",
    descriptionBuffer: "按约束缓冲阶段和时间区域协同工单接收与开工。",
    descriptionDispatch: "按缓冲颜色、渗透率和现场状态生成资源级派工建议。",
    descriptionPublicDemo: "使用 PUBLIC-DEMO-GOLDEN-DATA-V1 文件包演示 DDAE 配置接收、SDBR 运行和反馈交接。",
    descriptionExceptions: "集中处理失败、死信和执行偏差。",
    descriptionCalendar: "检查日历事项、冲突优先级和 CP-SAT 最终可用窗口。",
    descriptionAdmin: "管理主数据、求解器、集成和权限配置。",
    frameworkReady: "页面框架已就绪", emptyTitle: "此功能将在对应验收单元中启用",
    emptyDescription: "当前阶段只建立应用导航、计划输入和双语基础，不展示模拟生产数据。",
    overallReadiness: "总体就绪状态", loadingData: "正在读取数据状态", loadingDataDescription: "正在检查最新主数据版本与运行状态快照。",
    refresh: "刷新", generateOperationalSnapshot: "生成运行快照", selectPlanningInputs: "选作本次排程输入", readinessLoadFailed: "无法读取数据就绪状态",
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
    yes: "是", no: "否", noNeedReschedule: "暂不需要重排", needReschedule: "需要重排",
    issueCount: "个数据问题需要处理", inputsSelected: "已选择为本次排程输入",
    operationalSnapshotGenerated: "运行快照已生成。",
    operationalSnapshotGenerateFailed: "运行快照生成失败。",
    operationalSnapshotMissing: "没有可复制的运行状态快照。",
    publicDemoContext: "公开演示闭环", publicDemoSummary: "公开演示闭环摘要", runPublicDemo: "运行演示闭环",
    publicDemoOnly: "仅公开演示", controlledDemo: "受控契约演示", packageValidation: "数据包校验",
    frozenPackage: "冻结数据包", handoffValidation: "交接校验", ddaeHandoff: "DDAE 到 SDBR",
    contractValidation: "契约校验", validationResults: "校验结果", feedbackHandoff: "反馈交接",
    adapterValidation: "Adapter 校验", adventureWorksAdapter: "AdventureWorks 排程 Adapter",
    adapterMode: "Adapter 模式", generatedRows: "生成行数", explicitCalendars: "显式资源日历",
    formalSolverGate: "正式求解入口", generatedPackage: "生成包路径",
    materialFeasibleClaim: "物料可行性生产声明",
    productDemoMode: "产品演示模式", productDemoProfile: "AdventureWorks 产品演示 Profile",
    activeProfile: "活动 Profile", demoAuthority: "演示权威数据", authorityRows: "权威行数",
    sourceClassCoverage: "来源类型覆盖", panelPolicy: "页面策略", productDemoPanels: "产品演示页面",
    placeholderPanels: "占位页面", sampleModePanels: "样例模式页面", validationDeadLetters: "校验死信",
    setupOmission: "换型规则边界", materialOmission: "物料可行性边界",
    sdbrFeedbackFiles: "SDBR 到 DDAE", boundary: "边界", nonClaims: "非声明",
    publicDemoLoadFailed: "无法读取公开演示闭环", publicDemoRetryAdvice: "请确认 frozen package 与 handoff 文件可用后重试。",
    publicDemoRunCompleted: "公开演示反馈文件已生成。", publicDemoRunNotReady: "公开演示尚未就绪，请检查 DDAE handoff payload。",
    sdbrMarketControlKicker: "S-DBR 运行控制", sdbrMarketControlTitle: "市场承诺与约束保护",
    ccrPlannedLoad: "约束计划负荷", mtoSafeDate: "MTO 安全承诺", mtaReplenishmentLoad: "MTA 补货负荷", unifiedBufferPriority: "统一缓冲优先级",
    marketControlBoundary: "本区使用已冻结配置、排程结果和 DDMRP 运行输入，不新增 DDAE 主参数协议。",
    marketLoadStatus_Overloaded: "超出保护能力", marketLoadStatus_NearLimit: "接近上限", marketLoadStatus_Watch: "需要关注", marketLoadStatus_Protected: "受保护",
    marketLoadDetail: "关键资源合计 {total} 分钟（{hours} 小时）· MTO {mto} 分钟 · MTA {mta} 分钟 · 最高负荷 {max}%（按有效产能窗口计算）",
    marketSafeDateUnavailable: "需要产能评审", marketSafeDateExpired: "已过期：{date}", marketMtaMapped: "{count} 条已映射", marketMtaUnmapped: "{count} 条补货建议缺少执行映射",
    marketPriorityCount: "{count} 条", marketPriorityDetail: "红区 {red} · 黄区 {yellow} · 绿区 {green}",
    marketControlDetails: "查看约束负荷和优先级明细",
    marketNoPriorityRows: "暂无统一缓冲优先级明细",
    marketNoLoadBuckets: "暂无约束负荷明细",
    marketLoadBucketTitle: "约束负荷",
    marketPriorityRowsTitle: "优先级来源",
    marketDemandClassMTO: "MTO 工单",
    marketDemandClassMTA: "MTA 补货",
    marketPrioritySource_MTAStockBuffer: "库存缓冲",
    marketPrioritySource_MTOTimeBuffer: "时间缓冲",
    marketPriorityItem: "物料 {item} · 地点 {location} · 映射工单 {order}",
    marketPriorityOrder: "工单 {order}",
    bufferDailyLoadScope: "工单全流程剩余负荷，不等同于约束资源负荷",
    sdbrWhatIfKicker: "S-DBR 执行级 What-if",
    sdbrWhatIfTitle: "冲击会不会打爆约束",
    scenarioType: "场景类型",
    scenarioMtoExpedite: "插单 / 加急",
    scenarioResourceDowntime: "停机冲击",
    scenarioSupplyDelay: "供应延迟",
    scenarioMtaRedShock: "MTA 红区补货冲击",
    mtaRedCandidate: "MTA 红区候选",
    noMtaRedCandidates: "当前没有可评估的 MTA 红区补货候选。",
    mtaCandidateSummary: "候选 {candidate} · 物料 {item} · 地点 {location} · 建议数量 {qty} · 预计约束负荷 {minutes} 分钟",
    additionalLoadMinutes: "新增 / 挤压负荷分钟",
    downtimeMinutes: "停机分钟",
    runSdbrWhatIf: "评估冲击",
    sdbrWhatIfBoundary: "只评估执行层冲击，不修改冻结排程。",
    whatIfBeforeAfter: "负荷变化",
    whatIfRecommendation: "建议动作",
    whatIfSimioHint: "是否建议 Simio 复核",
    whatIfDecision_AbsorbWithExistingPlan: "按现有计划吸收",
    whatIfDecision_AbsorbWithBufferAndProtectiveCapacity: "用缓冲和保护产能吸收",
    whatIfDecision_ReviewBeforeRelease: "释放前人工复核",
    whatIfDecision_ProtectCcrAndReviewReplan: "保护约束并复核是否重排",
    whatIfDecision_ReviewRequired: "需要人工评审",
    effectiveCapacity: "有效产能",
    loadChange: "负荷变化",
    loadPercentChange: "负荷率变化",
    beforeAfterStatus: "状态变化",
    whenUseSimio: "什么时候建议用 Simio？",
    simioRecommendationTitle: "建议使用 Simio 高保真验证的情形",
    simioUseCaseCcrGroup: "CCR 不是单一资源，而是一组设备/人员/夹具组合。",
    simioUseCaseDisruption: "停机、返工、检测失败对结果影响很大。",
    simioUseCaseReentrant: "同一个订单多次访问同一资源。",
    simioUseCaseBranching: "Routing 分支多，路径选择复杂。",
    simioUseCaseQueueDrivers: "搬运、等待、批处理、换型占比很高。",
    simioUseCaseQueueStory: "需要展示为什么排队爆了的动态过程。",
    simioUseCaseStableModel: "已经有稳定 Simio 模型和数据维护机制。",
    businessUserView: "业务用户视图", sdbrExecutionDemo: "SDBR 执行演示",
    sdbrExecutionDemoIntro: "这部分用业务语言说明：SDBR 如何接收 DDAE 的受控演示交接，校验其可信性，转换为有界演示排程输入，并把结果反馈给 DDAE 复核。",
    demoConfidenceMeaning: "演示口径说明",
    productDemoOnlyExplanation: "ProductDemoOnly = AdventureWorks 产品演示档案，包含明确补全的 DemoAuthority。",
    publicDemoOnlyExplanation: "PublicDemoOnly = 底层公开数据包和受控 fixture adapter 的证据口径。",
    ddmrpRuntime: "DDMRP 运行", ddmrpRuntimeStatus: "DDMRP 运行状态", ddmrpRuntimeSummary: "DDMRP 运行状态摘要",
    decouplingPoints: "解耦点", redZone: "红区", yellowZone: "黄区", greenZone: "绿区", aboveGreenZone: "高于绿区",
    replenishmentSuggestions: "补货建议", missingData: "缺失数据", viewDdmrpDetails: "解耦点明细",
    item: "物料", onHand: "在手量", netFlowPosition: "净流位置", planningBufferZone: "计划缓冲区",
    executionBufferZone: "在手执行区", suggestedReplenishmentQty: "建议补货量",
    ddmrpReady: "DDMRP 运行数据可用", ddmrpMissingData: "DDMRP 输入存在缺失", ddmrpNoData: "尚无 DDMRP 解耦点数据。",
    action_Replenish: "建议补货", action_Monitor: "保持观察",
    zone_Red: "红区：需要行动", zone_Yellow: "黄区：需要关注", zone_Green: "绿区：正常", zone_AboveGreen: "高于绿区：暂不补货",
    materialPlanningSummary: "物料计划摘要", criticalPriority: "紧急", attentionPriority: "关注", normalPriority: "正常",
    materialPlanningWorkbench: "物料计划工作台", searchItemOrLocation: "搜索物料或地点", sortBy: "排序",
    planningPriority: "计划优先级", bufferPercent: "缓冲百分比", openSupply: "在途供应", qualifiedDemand: "合格需求",
    materialPlanningLoadFailed: "无法读取物料计划工作台", materialPlanningRetryAdvice: "请确认 DDMRP 运行数据可用后重试。",
    materialPlanningNoRows: "没有符合条件的物料计划记录", materialPlanningNoRowsAdvice: "请调整筛选条件或检查 DDMRP 输入数据。",
    materialDetail: "物料详情", selectMaterialForDetails: "选择一条物料查看详情",
    materialDetailAdvice: "详情显示当前快照的缓冲边界、需求/供应构成和趋势占位。",
    topOfRed: "红区顶部", topOfYellow: "黄区顶部", topOfGreen: "绿区顶部",
    supplyDemandComponents: "需求与供应构成", trendPlaceholder: "趋势分析",
    trendPlaceholderMessage: "第一版显示当前快照；历史缓冲、在手和净流趋势将在后续版本补充。",
    demandComponentsCount: "合格需求 {count} 条", supplyComponentsCount: "有效在途 {count} 条",
    operationalMetricsContext: "运营指标范围", operationalMetricsOverview: "运营指标总览",
    operationalMetricsLoadFailed: "无法读取运营指标", operationalMetricsRetryAdvice: "请确认已存在完成的排程任务和本地服务可用后重试。",
    ddomMetricSet: "DDOM 流动指标", overallScore: "综合得分", varianceFeedback: "偏差反馈",
    feedbackForDDSOP: "给上层战术协同的运行表现反馈", metricAppliesTo: "适用范围", metricDoesNotApplyTo: "不适用范围",
    dataCoverageIssues: "数据覆盖缺口", noDataCoverageIssues: "当前指标没有明显数据覆盖缺口。",
    recommendedActions: "建议动作", metricQuestion: "核心问题", metricFocus: "关注重点",
    metricCoverage: "数据覆盖", metricStatusGreen: "绿色：按模型运行", metricStatusYellow: "黄色：需要关注", metricStatusRed: "红色：需要干预", metricStatusUnavailable: "数据不足",
    coverage_Available: "数据可用", coverage_NoActiveBufferOrders: "暂无活动缓冲工单", coverage_NoReleaseCandidates: "暂无释放候选",
    coverage_NoScheduledOrders: "暂无计划工单", coverage_NoExecutionEvents: "暂无执行事件", coverage_NoArrivalEvents: "暂无到达事件", coverage_NoDispatchableOperations: "暂无可派工工序",
    issue_MASTER_DATA_VERSION_MISSING: "尚未创建主数据版本。", issue_OPERATIONAL_STATE_SNAPSHOT_MISSING: "尚未创建运行状态快照。",
    issue_OPERATIONAL_STATE_SNAPSHOT_STALE: "最新运行状态快照已经过期。", issue_OPERATIONAL_STATE_SNAPSHOT_IN_FUTURE: "最新运行状态快照时间晚于当前时间。",
    issue_OPERATIONAL_SOURCE_NOT_PROVIDED: "运行状态快照未提供来源系统。", issue_RESOURCE_STATUS_NOT_CAPTURED: "当前快照尚未包含资源运行状态。",
    caseAcceptanceSummary: "测试案例验收摘要", testSystemCases: "测试系统案例", caseAcceptanceTitle: "案例验收总览",
    caseGroup: "案例分组", caseType: "案例类型", expectedAssertions: "期望断言", passedAssertions: "通过断言", failureReasons: "差异原因",
    CPSATBusinessCases: "CP-SAT业务案例", BusinessClosure: "业务闭环案例",
    caseAcceptanceLoadFailed: "无法读取案例验收摘要", caseAcceptanceRetryAdvice: "请确认测试服务和测试库可用后重试。",
    totalCases: "案例总数", passedCases: "已通过", needsExecutionCases: "待执行", failedCases: "未通过",
    acceptancePassed: "通过", acceptanceNeedsExecution: "待执行", acceptanceFailed: "未通过",
    purpose: "验证目的", releaseReadyCount: "可释放数", blockingCodes: "阻塞代码", openScheduleResult: "打开排程结果",
    scheduleNotCompleted: "排程未完成", executeCaseFirst: "需要先执行并完成该案例的 Planning Run，才能打开排程结果。",
    resetCase: "复位案例", resetAllCases: "复位全部案例", caseResetCompleted: "案例已复位。", caseResetFailed: "案例复位失败。",
    PLANNING_RUN_NOT_COMPLETED: "Planning Run 尚未完成。", PLANNING_RUN_DEAD_LETTER: "Planning Run 已进入死信，不能打开排程结果。",
    PLANNING_RUN_NOT_EXECUTED: "Planning Run 尚未执行。",
    runMetrics: "排程任务状态摘要", allRuns: "全部任务", queued: "排队中", running: "运行中", completed: "已完成",
    deadLetter: "死信", pending: "待计算", failed: "失败", cancelled: "已取消", allStatuses: "全部状态",
    status: "状态", requester: "请求人", filterRequester: "筛选请求人", exceptionsOnly: "仅看异常",
    timeRange: "时间范围", allTime: "全部时间", last24Hours: "最近 24 小时", last7Days: "最近 7 天",
    last30Days: "最近 30 天", allSolvers: "全部求解器", startedAt: "开始时间",
    createPlanningRun: "创建排程", runsLoadFailed: "无法读取排程任务", runsRetryAdvice: "请重新加载后再操作。",
    runId: "Run ID", problem: "计划场景", solver: "求解器", requestedAt: "请求时间", duration: "耗时",
    attempts: "尝试", actions: "操作", noPlanningRuns: "尚无排程任务", noPlanningRunsDescription: "选择有效输入后创建第一项排程任务。",
    wizardTitle: "新建 Planning Run", wizardSteps: "创建排程步骤", selectInputs: "选择输入", setPolicy: "设置策略",
    reviewSubmit: "验证并提交", scheduleStart: "计划起点", selectInputsFirst: "请先在数据就绪中心选择有效输入。",
    timeBufferProfile: "时间缓冲参数", timeBufferCalculator: "时间缓冲计算器",
    timeBufferFormula: "时间缓冲 = OLT × (1 + 变异与弹性综合系数)",
    operatingLeadTime: "运营提前期 OLT（分钟）", variabilityProfile: "上游波动程度",
    variabilityLow: "低", variabilityMedium: "中", variabilityHigh: "高",
    variabilityHelp: "上游波动来自设备故障、来料准时率、返工和废品率。波动越高，约束前需要留出的时间保护越大。",
    capacityFlexProfile: "产能弹性", capacityFlexHigh: "高弹性", capacityFlexMedium: "中弹性", capacityFlexLow: "低弹性",
    capacityFlexHelp: "产能弹性表示上游非约束资源的保护性产能和追赶能力。弹性越高，异常后越容易追回进度，时间缓冲可相对较小。",
    timeBufferMultiplier: "推荐倍数", recommendedTimeBuffer: "推荐时间缓冲", useRecommendedBuffer: "采用推荐值",
    timeBufferRecommendationApplied: "已采用推荐时间缓冲。",
    timeBuffer: "时间缓冲（分钟）", timeLimit: "求解时间限制（秒）", maxAttempts: "最大尝试次数",
    retryDelay: "重试延迟（秒）", pausedUnavailable: "已暂停，暂不可用", enableSimio: "启用 Simio 验证",
    back: "上一步", next: "下一步", submitRun: "提交排程任务", available: "可用", unavailable: "不可用",
    enqueue: "入队", execute: "直接执行", processQueue: "处理队列", cancel: "取消", recover: "人工恢复", openResults: "查看结果", view: "查看",
    seconds: "秒", notStarted: "未开始", frozenInputs: "冻结输入", solverParameters: "求解参数", workerLease: "Worker 与租约",
    timeline: "状态时间线", diagnostics: "求解诊断", auditEvents: "审计事件", noWorker: "尚未分配 Worker",
    businessDiagnosis: "业务判断", technicalDetails: "技术详情",
    diag_ORTOOLS_TIME_LIMIT_CONFIGURED: "排程计算已设置时间上限，超过上限会返回当前可行结果或超时诊断。",
    diag_ORTOOLS_CP_SAT_MODEL: "本次排程已考虑可选资源、工序顺序、有限产能、换型、并行资源、时间窗口和能力日历。",
    diag_ORTOOLS_OBJECTIVE_STRATEGY: "本次排程采用平衡策略，在交期、流动时间和瓶颈保护之间折中。",
    diag_ORTOOLS_SETUP_TRANSITIONS_ENABLED: "本次排程已考虑产品族切换带来的换型时间。",
    diag_ORTOOLS_RESOURCE_EFFICIENCY_ENABLED: "本次排程已考虑资源效率对加工时长的影响。",
    diag_ORTOOLS_OPERATION_TIME_WINDOWS_ENABLED: "本次排程已考虑工序最早开始和最晚完成窗口。",
    diag_ORTOOLS_CAPACITY_BUCKETS_ENABLED: "本次排程已考虑日历和能力桶限制。",
    diag_ORTOOLS_CUSTOM_OBJECTIVE_WEIGHTS_ENABLED: "本次排程使用了自定义目标权重。",
    dataUpdated: "数据已更新，请重新加载后再操作。", runCreated: "排程任务已创建", submissionFailed: "排程任务创建失败",
    confirmEnqueue: "确认将此排程任务加入队列？", confirmExecute: "确认立即调用 OR-Tools CP-SAT 执行此排程任务？",
    confirmProcessQueue: "确认由交互式 Worker 领取并计算此排程任务？", queueProcessed: "队列任务已处理。",
    replanCreatedQueued: "重排任务已创建并入队，请在排程任务中处理队列。",
    confirmReplan: "确认基于当前计划创建新版重排任务并入队？",
    cancelReasonPrompt: "请输入取消原因。", recoverReasonPrompt: "请输入人工恢复原因。",
    actionFailed: "操作失败，请重新加载后重试。", solverUnavailable: "当前求解器不可用。",
    confirmAction: "确认操作", confirm: "确认", notifySuccess: "操作已完成", notifyError: "操作失败",
    resultContext: "排程结果范围", planningRun: "排程任务", scheduleResultLoadFailed: "无法读取排程结果",
    scheduleResultRetryAdvice: "请选择已完成的排程任务后重试。", noCompletedSchedules: "尚无已完成的排程结果",
    completeRunFirst: "请先完成一项排程任务。", scheduleKpis: "排程结果指标", onTimeOrders: "按计划准时工单",
    lateOrders: "按计划延迟工单", overloadMinutes: "超载分钟", redBuffers: "红区缓冲", peakLoad: "峰值负荷",
    scheduleResultViews: "排程结果视图", ganttChart: "甘特图", resourceLoad: "资源负荷", orderDelivery: "订单交期",
    ganttMode: "甘特图模式", resourceOccupationView: "资源占用图", workOrderFlowView: "工单流程图",
    resource: "资源", workOrder: "工单", barType: "条带类型", bufferZone: "缓冲区", fromDate: "开始日期",
    toDate: "结束日期", zoom: "缩放", ganttLegend: "甘特图图例", processing: "加工",
    greenBuffer: "绿色时间缓冲", yellowBuffer: "黄色时间缓冲", redBuffer: "红色时间缓冲",
    maintenance: "维护", unavailableTime: "不可用时间",
    loadViews: "负荷视图", systemLoad: "系统负荷", singleResourceLoad: "单资源负荷", resourceType: "资源类型",
    owner: "负责人", category: "类别", date: "日期", loadMinutes: "负荷分钟", availableCapacity: "可用产能",
    utilization: "利用率", released: "已释放", unreleased: "未释放", remainingLoad: "剩余负荷",
    sdbrFlowControl: "S-DBR 运行控制", plannedLoadAndProtectiveCapacity: "计划负荷与保护产能",
    plannedLoad: "计划负荷", safeDate: "安全日期", releaseDiscipline: "释放纪律", stabilityGuidance: "稳定性建议",
    protectiveCapacity: "保护产能", earliestSafeDate: "最早安全日期", monitorOnly: "仅监控，不作为硬约束",
    flowStatus_Protected: "保护正常", flowStatus_NearLimit: "接近上限", flowStatus_Overloaded: "负荷超限",
    flowStatus_Available: "可作为初步窗口", flowStatus_NeedsCapacityReview: "需要产能协调",
    flowAction_OperateByBufferPriority: "按缓冲优先级运行",
    flowAction_ReviewBeforeInsertOrder: "插单前人工复核",
    flowAction_CoordinateBeforeReleaseOrPromise: "释放或承诺前先协调产能",
    flowAction_NoHardConstraintNeeded: "无需转为硬约束",
    flowAction_MonitorBeforeInsertOrder: "插单前关注",
    flowAction_ProtectiveCapacityReview: "复核保护产能",
    flowAction_EscalateCapacityOrReplanReview: "协调产能，必要时评审重排",
    flowAction_AbsorbWithBufferAndProtectiveCapacity: "先用缓冲和保护产能吸收",
    flowAction_OnlyWhenBufferOrLoadThresholdIsBreached: "仅在缓冲或负荷达到阈值时重排",
    protectiveStatus_Healthy: "保护正常", protectiveStatus_Watch: "关注", protectiveStatus_AtRisk: "风险", protectiveStatus_CandidateConstraint: "候选约束",
    product: "产品", dueDate: "交期", plannedCompletion: "计划完工", delayMinutes: "延迟分钟",
    decisionSupport: "决策支持", scenarioComparison: "方案比较", baselineScenario: "基准方案",
    candidateScenario: "候选方案", compare: "比较", allResources: "全部资源", allOrders: "全部工单",
    allBarTypes: "全部条带", allZones: "全部缓冲区", allOptions: "全部", constraint: "约束资源",
    nonConstraint: "非约束资源", candidateConstraint: "候选约束", noGanttRows: "当前筛选条件下没有甘特任务。",
    noDiagnostics: "求解器未返回诊断信息。", onTime: "准时", late: "延迟", unscheduled: "未排程", code: "技术码", message: "消息",
    generatedAt: "生成时间", recommended: "推荐", selectScenario: "采用并送审", selectionReasonPrompt: "请输入采用该方案的原因。",
    selectedForReview: "方案已选择并进入审核。", candidateReducesOverload: "候选方案降低了资源超载。",
    candidateReducesLateOrders: "候选方案减少了延迟工单。", candidateReducesRedBuffers: "候选方案减少了红区缓冲。",
    baselineBetterScore: "基准方案综合得分更优。", candidateBetterScore: "候选方案综合得分更优。",
    planGovernance: "计划治理", publicationGovernance: "计划发布治理", publicationLoadFailed: "无法读取计划发布状态",
    publicationRetryAdvice: "请刷新排程结果后重试。", publicationStatus: "发布状态", scheduleFingerprint: "计划指纹",
    allowedPublicationActions: "允许动作", publicationPackage: "发布包", packageId: "发布包编号", targetSystems: "目标系统",
    publishedBy: "发布人", publishedAt: "发布时间", solverStatus: "求解状态", publicationHistory: "发布历史",
    outputGovernance: "计划输出", outputAvailability: "输出可用性", outputPackage: "计划输出包", outputPackageId: "输出包编号",
    completenessStatus: "输出检查", passedChecks: "通过检查", failedChecks: "未通过检查", releaseGovernance: "释放准备",
    recommendationCount: "释放建议数", unauthorizedCount: "未授权数", auditGovernance: "操作记录", auditEventCount: "记录数",
    scenarioSelectionCount: "方案选择数", workOrderCommandCount: "工单命令数", publicationActionCount: "发布动作数",
    simulationResults: "仿真结果", simioValidation: "Simio 验证", simioValidationStatus: "验证状态", simioRunner: "运行器", simioPackage: "验证包",
    simioModelPath: "模型路径", simioResultModelPath: "结果模型", simioIssues: "问题数", simioKpis: "验证指标",
    simioFeasibility: "可行性结论", simioThroughput: "吞吐", simioQueueMetrics: "队列指标", simioWipMetrics: "WIP 指标",
    simioResourceUtilization: "资源利用率", simioResultCoverage: "结果解析覆盖", simioRunnerMode: "运行模式",
    simioTemplateRegistry: "Simio 仿真模板", simioTemplate: "仿真模板", activeSimioTemplate: "当前活动模板",
    templateId: "模板编号", templateName: "模板名称", templateVersion: "模板版本", templatePath: "模板路径",
    templateSourceType: "模板来源类型", timeUnitPolicy: "时间单位规则", desktopValidationStatus: "Desktop 校验状态",
    templateStatus: "模板状态", configuredTemplates: "已登记模板", templatePolicy: "模板使用规则",
    defaultTemplateDirectory: "默认模板目录", runtimeRule: "运行规则", timeUnitRule: "时间单位规则",
    templateReady: "模板已配置，仿真验证将复制该模板并生成运行模型。",
    templateNeedsAttention: "模板配置需要检查。", pendingManualCheck: "待人工 Desktop 校验",
    simioRunnerAuto: "自动", simioRunnerMock: "Mock", simioRunnerLocal: "本机 Headless", runSimioValidation: "运行仿真验证",
    simioOptionalValidation: "计划完成后可在仿真结果页运行", simioValidationRequested: "Simio 仿真验证已完成。",
    noSimulationResult: "尚未请求 Simio 仿真验证。", busyMinutes: "忙碌分钟", starvedMinutes: "饥饿分钟", evidence: "数据来源",
    actualStart: "实际开始", actualEnd: "实际结束", queueWaitMinutes: "队列等待", wipAfterStart: "开工后 WIP",
    wipAfterEnd: "完工后 WIP", eventStatus: "事件状态", durationMinutes: "加工/停留时间",
    simioOrderFilter: "工单筛选", simioOrderFilterPlaceholder: "搜索工单",
    simioQueueWaitFilter: "等待时间", allSimulationEvents: "全部事件", allWaitTimes: "全部等待",
    waitGreaterThanZero: "等待 > 0 分钟", waitGreaterThan30: "等待 > 30 分钟", waitGreaterThan60: "等待 > 60 分钟",
    simulationRowsRange: "显示 {start}-{end} / 共 {total} 条", noSimulationRows: "没有符合条件的工单仿真记录",
    parsedSources: "已用数据", unavailableSources: "未取得数据",
    simioSourceParsedFromSDBROutputRows: "来自工单输出记录", simioSourceParsedFromPostRunLogs: "来自 Simio 运行日志",
    simioSourceParsedFromInteractiveStatistics: "来自 Simio 交互统计", simioSourceParsed: "已完整解析",
    simioSourcePartialResultParsed: "已解析部分仿真结果", simioSourceUnavailable: "暂不可用",
    simioPartialWithAvailableMetrics: "已解析部分仿真结果，可查看下方已回传指标。",
    businessDecision: "业务判断", publicationDecision: "发布进度", outputDecision: "输出准备", releaseDecision: "释放准备",
    simulationDecision: "仿真验证", auditDecision: "操作留痕", technicalDetails: "技术详情", showDetails: "展开", hideDetails: "收起",
    planCanPublish: "计划可进入发布流程", planNeedsReview: "计划需先复核或批准", outputReadyForReview: "计划输出已齐套", outputNeedsAttention: "计划输出需检查",
    releaseReadySummary: "已有释放建议，可进入释放评估", releaseNoRecommendation: "暂无释放建议", simulationPassedSummary: "仿真验证通过，可作为复核证据",
    simulationWarningSummary: "仿真可运行，但存在提示项", simulationNotRunSummary: "尚未运行仿真验证", auditReadySummary: "关键操作已留痕",
    simioIssue_SIMIO_RESULT_LOG_MISSING: "未取得完整统计文件，已用其他结果数据补充。",
    simioIssue_SIMIO_UNFINISHED_ORDERS: "仿真显示存在未完成工单。",
    simioIssue_SIMIO_BINARY_LOGS_PARTIAL: "部分仿真日志只能解析到关键指标。",
    simioIssue_SIMIO_RESULT_PARTIAL: "仿真完成，但部分明细未能解析。",
    simioEvent_OperationStarted: "工序开始", simioEvent_OperationCompleted: "工序完成", simioEvent_OrderStarted: "工单开始", simioEvent_OrderCompleted: "工单完成",
    externalDelivery: "外部投递", notSent: "未发送", packageReady: "输出包可用", packageUnavailable: "输出包不可用",
    externalDeliveryOwnedByIntegrations: "ERP/MES 下发由外部接口模块负责，本版本只生成内部输出包。",
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
    releaseContext: "释放评估", evaluatedAt: "评估时间", reevaluate: "重新评估",
    releaseSnapshotRefreshed: "Mock 运行快照已刷新，释放门控已重新评估。", releaseLoadFailed: "无法读取释放评估",
    releaseRetryAdvice: "请检查已完成计划和运行状态快照。", noReleaseRuns: "没有可评估的已完成计划",
    totalOrders: "工单总数", readyToRelease: "可释放", blocked: "已阻塞", authorized: "已授权",
    penetration: "渗透率", ropeReleaseTime: "绳长释放时间", materialStatus: "物料状态", wipStatus: "WIP 状态",
    plannedStart: "计划开始", blockingReason: "阻塞原因", releaseGate: "释放门控", dispatchPackage: "调度包",
    authorizeRelease: "授权释放", viewDispatch: "查看调度包", viewReason: "查看原因", noBlockReason: "当前没有阻塞原因。",
    snapshotStatus: "快照状态", freshSnapshot: "运行状态快照新鲜", staleSnapshot: "运行状态快照已过期，禁止授权释放",
    futureSnapshot: "运行状态快照时间异常，禁止授权释放", clear: "通过", early: "未到时间", notReleased: "未释放",
    snapshotRefreshAdvice: "请同步或生成新的资源/物料/WIP 快照后重新评估；仅快照过期不要求重新排程。",
    releasePolicyVersion: "释放策略版本", policyEvidence: "策略证据", reasonDetails: "触发参数", stabilityDecision: "稳定性判断",
    ropeBufferMinutes: "策略绳长分钟", materialCheckWindowMinutes: "物料检查窗口分钟", materialLookaheadMinutes: "物料检查窗口分钟",
    maxWipCount: "策略 WIP 上限", policyMaxWipCount: "策略 WIP 上限", snapshotMaxWipCount: "快照 WIP 上限",
    effectiveMaxWipCount: "实际采用 WIP 上限", actualWipCount: "当前 WIP", projectedWipCount: "释放后 WIP",
    minutesUntilRelease: "距离可释放分钟", toleranceMinutes: "稳定性容忍分钟", replanThresholdMinutes: "重排阈值分钟",
    consecutiveBlockedThreshold: "连续阻塞阈值", replanCooldownMinutes: "重排冷却分钟", action: "动作",
    deviationMinutes: "偏差分钟", absoluteDeviationMinutes: "绝对偏差分钟", reasonCodeLabel: "业务原因", riskCount: "风险数",
    recommendedAction: "建议动作", requiresReschedule: "是否需要重排",
    reason_ROPE_TIME_NOT_REACHED: "尚未到达绳长释放时间。", reason_MATERIAL_SHORTAGE: "可用物料不足。",
    reason_MATERIAL_INBOUND_PENDING: "物料仍在途中。", reason_WIP_LIMIT_EXCEEDED: "释放后 WIP 将超过上限，暂不进入正式派工队列。",
    reason_OPERATIONAL_SNAPSHOT_STALE: "运行状态快照已过期。", reason_OPERATIONAL_SNAPSHOT_FUTURE: "运行状态快照时间晚于评估时间。",
    action_RefreshOperationalSnapshotAndReevaluate: "同步/生成新运行快照后重新评估释放",
    action_CorrectEvaluationTimeOrSnapshot: "修正评估时间或选择正确快照",
    action_ReadyForRelease: "可以授权释放",
    action_HoldForWip: "暂缓释放，等待 WIP 降低",
    action_WaitForInbound: "等待在途物料到达",
    action_ExpediteMaterial: "催办物料或调整供应",
    action_Monitor: "继续监控",
    action_Review: "需要计划员复核",
    action_Replan: "建议发起重排",
    reason_DeviationAtReplanThreshold: "偏差已达到重排阈值",
    reason_WithinTolerance: "偏差仍在容忍范围内",
    reason_ConsecutiveGateBlocks: "连续阻塞次数达到阈值",
    reason_ReplanCooldownActive: "重排冷却期内，先复核再决定",
    authorizeImpact: "确认授权释放该工单？系统将记录门控快照并生成调度包。", releaseAuthorized: "工单已授权释放。",
    commandRecorded: "工单命令已记录。", pageOf: "第 {page} / {pages} 页",
    bufferContext: "约束缓冲", bufferMatrix: "两阶段五区域缓冲矩阵", bufferLoadFailed: "无法读取缓冲执行看板",
    bufferRetryAdvice: "请选择包含已授权工单的已完成计划。", noBufferRuns: "没有可用的已完成计划", bufferOwner: "缓冲负责人",
    dailyLoad: "当日总负荷", lastScheduled: "最近排程时间", hours: "小时", yetToBeReceived: "待接收", received: "已接收",
    Early: "提前", Green: "绿区", Yellow: "黄区", Red: "红区", Late: "逾期", orderCount: "工单数", totalLoad: "总负荷",
    mesDispatch: "MES 派工", mesDispatchQueue: "MES 派工队列", mesDispatchBoundary: "此处只展示内部派工队列，不执行真实 MES 投递。",
    dispatchContext: "派工建议", dispatchLoadFailed: "无法读取派工建议", dispatchRetryAdvice: "请选择包含已完成计划和释放数据的排程任务。", noDispatchRuns: "没有可用的已完成计划",
    dispatchableOperations: "可正式派工工序", candidateWarnings: "候选/预警", queueJumpSuggestions: "插队建议", plannerConfirmations: "需调度员确认",
    replanSuggestions: "重排建议", dispatchRank: "派工顺序", planSequence: "计划顺序", conflictResult: "冲突结果",
    plannerConfirmation: "调度员确认", mesDispatchUnavailable: "MES 派工队列暂不可用", noDispatchRows: "当前没有可正式派工工序。",
    noDispatchWarnings: "当前没有候选/预警。", Dispatchable: "可派工", CandidateOnly: "候选/预警", FollowPlan: "按计划执行",
    SuggestQueueJump: "建议插队", NeedsReplan: "需要重排", Clear: "通过", ReleaseNotAuthorized: "未授权释放",
    LatestOperationalStateBlocked: "最新门控阻塞", LatestOperationalStateNotReady: "最新状态未就绪",
    ArrivalNotConfirmed: "缺少到达确认", DispatchRejected: "MES 已拒绝", ExceptionReported: "现场异常",
    NotArrived: "未到达", MissingArrivalConfirmation: "缺少到达确认", Arrived: "已到达", Processing: "加工中", Completed: "已完成",
    currentExecution: "现场状态", arrivalStatus: "到达状态", recommendation: "建议", recommendationReason: "建议原因",
    issueDispatchSuggestions: "生成 MES 派工建议包", dispatchSuggestionNotIssued: "尚未生成派工建议包。",
    dispatchSuggestionIssued: "MES 派工建议包已生成", packageId: "包编号", mockDeliveryStatus: "Mock 投递状态",
    MockDispatchSuggestionIssued: "Mock 派工建议已生成", Accepted: "已接收", Duplicate: "重复消息",
    Hold: "暂不派工", QueueJump: "建议插队", ReviewAndReplan: "复核并考虑重排",
    required: "需要", ConstraintResourceSetupOrIdleRisk: "约束资源可能增加换型或产生空闲风险",
    RedZoneCanOverrideSetupLossOnlyAfterPlannerConfirmation: "红区可压倒换型损失，但需要调度员确认",
    bufferOrderDetail: "缓冲工单详情", customer: "客户", currentReason: "当前原因", receiveStatus: "接收状态",
    executionTransaction: "执行事务", eventType: "事件类型", arrivedBuffer: "到达缓冲", startedOperation: "开始加工", eventAt: "事件时间",
    measureType: "记录方式", measureValue: "记录值", reasonCode: "原因码", selectReason: "请选择原因码", recordTransaction: "记录事务",
    reasonRequiredForLate: "Late 区事务必须选择标准原因码。", Quantity: "数量", CompletionPercent: "完成百分比", Hours: "工时",
    transactionRecorded: "执行事务已记录。", receiveOrStart: "接收 / 开工", reason_MATERIAL_SHORTAGE_CODE: "缺料",
    reason_EQUIPMENT_DOWN_CODE: "设备故障", reason_STAFF_ABSENCE_CODE: "人员缺勤", reason_QUALITY_REWORK_CODE: "质量返工",
    exceptionContext: "异常中心", severity: "严重程度", exceptionLoadFailed: "无法读取异常中心", exceptionRetryAdvice: "请确认服务可用后重试。",
    totalExceptions: "异常总数", criticalExceptions: "严重", warningExceptions: "警告", openExceptions: "未处理", object: "对象", occurredAt: "发生时间",
    businessImpact: "业务影响", suggestedAction: "建议动作", exceptionDetail: "异常详情", allSeverities: "全部严重程度", allSources: "全部来源",
    Critical: "严重", Warning: "警告", Information: "提示", impact_ScheduleUnavailable: "排程结果不可用", impact_ConstraintMayStarve: "约束可能断料",
    impact_ExecutionThreatensSchedule: "执行偏差威胁计划", impact_ScheduleStabilityAtRisk: "计划稳定性存在风险",
    action_RecoverPlanningRun: "恢复排程任务", action_ReviewPlanningRunFailure: "复核失败任务", action_ExpediteConstraintBuffer: "催办约束缓冲",
    action_ReviewExecutionAlert: "处理执行预警", action_ReviewReplanRequest: "审核重排建议", viewDetail: "查看详情", relatedObjects: "关联对象", resolutionActions: "处理动作",
    auditTrail: "审计历史", noAuditTrail: "没有审计记录", type_PlanningRunDeadLetter: "排程死信", type_PlanningRunFailed: "排程失败", type_ConstraintBufferRisk: "约束缓冲风险",
    type_ExecutionAlert: "执行预警", type_ReplanSuggestion: "重排建议",
    calendarContext: "日历配置", calendarPreviewLoadFailed: "无法读取日历预览", calendarPreviewRetryAdvice: "请确认已有主数据版本和资源日历配置后重试。",
    calendarElements: "日历事项", calendarRequiredElements: "事项要素检查", cpSatCapacityWindows: "CP-SAT 能力窗口", finalCapacityWindows: "最终可用窗口",
    sourceRules: "来源规则", appliedCalendarElements: "已识别日历规则", cpSatNeedReason: "CP-SAT 需求原因", missingImpactDomain: "缺失影响域",
    previewMode: "预览模式", finalWindowCount: "最终窗口数", missingDailyCapacityDates: "缺失日能力日期", noCalendarWindows: "当前范围没有最终可用窗口。",
    noCalendarElements: "当前资源没有识别到日历规则。", elementType: "事项类型", sourceId: "来源编号", start: "开始", end: "结束",
    calendarOperation: "日历操作", calendarWorkbenchTitle: "资源级日历配置", patternBased: "模式驱动",
    calendarWorkbenchDescription: "参考工作周 + 日模式结构：管理员维护基础日历，计划员维护临时覆盖；新建 Planning Run 时冻结生效配置。",
    workSchedules: "工作周 / 基础日历", dayPatterns: "日模式 / 班次时段", calendarExceptions: "节假日与维护",
    holidayDate: "节假日日期", maintenanceStart: "维护开始", maintenanceEnd: "维护结束", saveWorkSchedule: "保存工作周",
    weekdayMonday: "周一", weekdayTuesday: "周二", weekdayWednesday: "周三", weekdayThursday: "周四",
    weekdayFriday: "周五", weekdaySaturday: "周六", weekdaySunday: "周日",
    resourceCalendarAssignment: "资源日历分配", workPeriodExceptions: "加班 / 临时覆盖 / 停机", calendarRules: "固定规则",
    calendarPriorityRule: "维护 > 节假日 > 临时覆盖 > 加班 > 基础班次", timezone: "时区",
    timezoneRule: "第一版按日历时区生成能力窗口，中国现场默认 Asia/Shanghai。", crossShiftRule: "跨班次加工规则",
    crossShiftRuleDescription: "当前要求工序完整落入单个能力窗口，连续跨班次加工后续确认。",
    noCalendarConfigRows: "尚无配置记录。", adminCalendarMoved: "日历配置已移到独立页面；管理后台只保留能力摘要和当前配置清单。",
    openCalendarConfiguration: "打开日历配置", baseCalendarSummary: "基础日历摘要", calendarOverrideSummary: "日历临时覆盖摘要",
    administrationContext: "管理后台", sensitiveSettingsReadOnly: "敏感连接参数当前只读。", administrationLoadFailed: "无法读取管理后台",
    administrationRetryAdvice: "请确认本地服务可用后重试。", adminMasterDataTitle: "主数据后台", importPreview: "导入预览",
    importPreviewDescription: "选择对象后先查看结构化预览和预校验结果，再生成主数据版本。", importFile: "导入文件", preValidate: "预校验",
    generateVersion: "生成版本", routingImport: "导入工艺路线", noImportSelected: "尚未选择导入对象", rawJsonHidden: "原始 JSON 默认隐藏，仅管理员调试模式可查看。",
    adminSystemTitle: "集成与求解器设置", policyConfiguration: "排程策略配置", cpSatAssumptions: "CP-SAT 建模假设",
    tunableParameters: "可调参数", deferredRules: "延后规则", driverStatus: "驱动状态", calendar: "日历", calendarLayers: "资源日历四层",
    readOnly: "只读", partialEditable: "部分可配置", objectCount: "当前数量", importEndpoint: "导入接口", reservedFields: "预留字段", structuredPreview: "结构化预览",
    preValidationRequired: "导入前预校验", versionAfterImport: "导入后生成版本", capabilityStatus: "能力状态", lastSync: "最近同步",
    workerQueue: "Worker 队列", stateStore: "状态存储", DayDefinition: "日定义", WeekDefinition: "周定义", TemporaryShiftOverride: "临时班次覆盖",
    ExclusionOrMaintenance: "排除/维护修改", Overtime: "加班", calendarOverrides: "临时覆盖", calendarOverrideConfig: "日历临时覆盖配置",
    baseCalendars: "基础日历", baseCalendarConfig: "基础日历配置", displayName: "显示名称", workingWeekdays: "工作日",
    shiftStart: "班次开始", shiftEnd: "班次结束", createBaseCalendar: "创建基础日历", baseCalendarCreated: "基础日历已创建。",
    baseCalendarFailed: "基础日历创建失败。", baseCalendarBoundary: "Active 基础日历和资源分配会冻结到新建 Planning Run，并驱动 CP-SAT 能力桶；复杂冲突审批后续补齐。",
    assignmentId: "分配编号", assignCalendar: "分配日历", calendarAssignment: "日历分配", calendarAssignmentCreated: "资源日历分配已创建。",
    calendarAssignmentFailed: "资源日历分配创建失败。", noBaseCalendars: "尚无基础日历。", noCalendarAssignments: "尚无资源日历分配。",
    overrideId: "覆盖编号", calendarId: "日历编号", overrideType: "覆盖类型", effectiveStart: "生效开始", effectiveEnd: "生效结束",
    capacityDelta: "产能增减分钟", shiftName: "班次名称", reason: "原因", createOverride: "创建覆盖", calendarOverride: "日历覆盖",
    noCalendarOverrides: "尚无临时日历覆盖。", calendarOverrideCreated: "日历覆盖已创建。", calendarOverrideFailed: "日历覆盖创建失败。",
    calendarOverrideBoundary: "生效的临时覆盖会驱动新建 Planning Run；维护 > 节假日 > 临时覆盖 > 加班 > 基础班次，审批流暂不做。",
    calendarScope: "日历范围", ResourceOnly: "仅资源级", conflictPriority: "冲突优先级", ApprovalFlowStatus: "审批流",
    StatusOnly: "仅状态字段", Maintenance: "维护", Holiday: "节假日", BaseShift: "基础班次", Draft: "草案", Active: "生效", Retired: "停用",
    Ready: "已就绪", SimioXmlProjectExport: "Simio XML 项目导出",
    RateInterpretation: "速率解释方式", Units: "单位", SchedulingWindow: "排程窗口",
    BufferBoundaries: "缓冲区边界比例", PiecesPerHour: "件/小时", HoursPerPiece: "小时/件", MinutesPerPiece: "分钟/件",
    BufferMinutes: "缓冲分钟", SetupMinutes: "换型分钟", DurationMinutes: "持续分钟", FixedOffsetMinutes: "固定偏移分钟",
    WindowStart: "窗口起点", PreferredCompletionTime: "首选完工时间", ShipmentCutoffRule: "发货截止规则", GreenRatio: "绿区比例",
    YellowRatio: "黄区比例", RedRatio: "红区比例", NotConfigured: "未配置", Paused: "已暂停", Available: "可用", Unavailable: "不可用",
    Applied: "已应用", PartiallyApplied: "部分应用",
    Idle: "空闲", Online: "在线", Healthy: "健康", Unhealthy: "异常",
    navOrderCommitments: "订单承诺", pageOrderCommitments: "订单承诺", descriptionOrderCommitments: "查看 MTO 自动评估、证据和计划员待决定事项。",
    orderCommitmentSummary: "订单承诺摘要", awaitingDecision: "待决定", confirmationRequired: "需确认", materialPending: "物料待确认", acceptedPendingSchedule: "已接受，待正式排程",
    searchOrderOrProduct: "搜索订单或产品", allStatuses: "全部状态", order: "订单", product: "产品", requestedDueAt: "请求交期", earliestSafePromise: "建议安全日期",
    ccrLoadBeforeAfter: "CCR 负荷前后", protectionThresholdSource: "保护线来源", materialStatus: "物料状态", recommendation: "建议", reservationStatus: "预留状态", exceptionStatus: "异常状态",
    actions: "操作", viewDetails: "查看详情", orderCommitmentEvaluation: "订单承诺评估", orderCommitmentLoadFailed: "无法读取订单承诺评估", orderCommitmentRetryAdvice: "请确认服务可用后重试。", orderCommitmentDetailLoading: "正在读取订单承诺评估详情。", orderCommitmentDetailLoadFailed: "无法读取订单承诺评估详情。",
    materialSkipReasonRequired: "关闭物料检查时，请填写业务原因。", orderCommitmentRevisionConflict: "工作台状态已更新，已刷新当前评估；请复核后再操作。", orderCommitmentReevaluationFailed: "无法重新评估当前订单承诺。", orderCommitmentNotReevaluatable: "当前评估已结束或已被替代，不能重新评估。", orderCommitmentNotFound: "未找到订单承诺评估，请刷新后重试。",
    requiredDecisionEvidenceMissing: "请填写决定原因并完成当前操作要求的风险确认。", orderCommitmentEvidenceChanged: "决定依据已变化，已刷新当前评估；请重新选择操作。", orderCommitmentReplayConflict: "该决定与已记录的结果不一致，已刷新当前评估；不会自动重试。", orderCommitmentDecisionFailed: "无法记录当前订单承诺决定。请复核后重试。", orderCommitmentDecisionRecorded: "订单承诺决定已记录：",
    noOrderCommitments: "当前没有订单承诺评估。", orderDetails: "订单信息", capacityEvidence: "产能证据", materialEvidence: "物料证据", decision: "计划员决定", reservation: "计划预留",
    auditHistory: "审计记录", technicalDetails: "技术追溯", selectedPromise: "选定承诺日期", earliestSafeAssessment: "最早安全日期", requestedDateAssessment: "请求日期评估",
    loadBefore: "评估前负荷", loadAfter: "评估后负荷", loadPercent: "负荷率", protectionThreshold: "保护线", thresholdState: "保护线状态", materialCheck: "物料检查",
    materialFreshness: "物料证据新鲜度", materialLines: "物料需求行", acceptedPromise: "接受的承诺日期", decidedBy: "决定人", decidedAt: "决定时间", decisionReason: "决定原因", ccrRiskAcknowledged: "CCR 风险已确认", materialRiskAcknowledged: "物料风险已确认", supersededByEvaluation: "替代评估",
    reservationBatch: "预留批次", demandCommitment: "需求承诺", boundary: "业务边界", recommendationOnly: "仅提供建议，最终决定由计划员作出。",
    externalOrderAcceptance: "外部订单接受", planningRunCreation: "创建 Planning Run", productionMutation: "生产权威变更", unknownStatus: "未知状态",
    RecommendAccept: "建议接受", PlannerConfirmationRequired: "需计划员确认", CapacityAcceptableMaterialPending: "产能可接受，物料待确认", MaterialEvidenceRequired: "待物料确认",
    RecommendLaterPromise: "建议调整交期", DoNotRecommendAccept: "暂不建议接受", Feasible: "物料可行", SkippedPendingConfirmation: "物料待确认（已跳过检查）",
    EvidenceInsufficient: "物料证据不足", Shortage: "物料短缺", OnTime: "可按请求日期完成", LaterSafeDate: "需采用后续安全日期", NotAssessable: "暂不可评估",
    Fresh: "新鲜", Stale: "已过期", Future: "时间异常", Missing: "缺失", Protected: "保护范围内", Watch: "需要关注", NearLimit: "接近上限", Overloaded: "超载",
    ApprovedWithin: "批准保护线内", ApprovedExceeded: "超过批准保护线", Covered: "已覆盖", PlannedAllocationPrepared: "计划分配已准备", PendingConfirmation: "待确认",
    AwaitingPlannerDecision: "待计划员决定", AcceptedPendingFormalSchedule: "已接受，待正式排程", Rejected: "已拒绝", Superseded: "已由新评估替代",
    NotReserved: "尚未预留", ActivePlanReservation: "计划预留有效", LinkedToFormalOrder: "已关联正式订单", ConvertedToScheduledOccupancy: "已转正式排程占用",
    HeldForPlanningError: "排程异常待处理", AdjustmentRequired: "需要调整", Released: "已释放", Cancelled: "已取消", ReservationEvidenceMissing: "预留证据缺失",
    None: "无异常", AssessmentBlocked: "评估受阻", MaterialEvidenceBlocked: "物料证据受阻", PlanningErrorPending: "排程异常待处理",
    ReferenceFallback: "80% 默认参考，需确认", ApprovedOperatingModel: "批准的运行模型保护线", AcceptRequestedDate: "接受请求日期",
    ConditionallyAcceptRequestedDate: "条件接受请求日期", AcceptRecommendedDate: "接受建议日期", ConditionallyAcceptRecommendedDate: "条件接受建议日期",
    Reevaluate: "重新评估", Reject: "拒绝", OrderCommitmentEvaluated: "已评估", OrderCommitmentReevaluated: "已重新评估",
    OrderCommitmentEvaluationSuperseded: "评估已替代", OrderCommitmentAccepted: "已接受", OrderCommitmentRejected: "已拒绝",
    LatestCurrent: "最新当前快照", Explicit: "显式快照", OnHand: "在手", OnHandAndInbound: "在手与在途", NotPerformed: "未执行"
  },
  en: {
    primaryNavigation: "Primary navigation", planningContext: "Planning context", toggleNavigation: "Toggle navigation",
    productName: "Demand-Driven Planner Workbench", navOverview: "Planning Overview", navOperationalMetrics: "Operational Metrics", navData: "Data Readiness", navMaterials: "Materials Planning",
    navRuns: "Planning Runs", navResults: "Schedule Results", navRelease: "Release Management", navBuffer: "Buffer Execution", navDispatch: "Dispatch Suggestions",
    navPublicDemo: "Public Demo Loop", navExceptions: "Exceptions", navCalendar: "Calendar Configuration", navAdmin: "Administration", noUnreadExceptions: "No unread exceptions",
    apiConnected: "Local service connected", planningScope: "Planning scope", defaultFactory: "Default factory",
    masterDataVersionLabel: "Master data version", snapshotLabel: "Operational snapshot", systemHealthLabel: "System health",
    notSelected: "Not selected", checking: "Checking", healthy: "Healthy", unavailable: "Unavailable",
    language: "Language", planner: "Planner", workspaceEyebrow: "Planner Workbench",
    pageOverview: "Planning Overview", pageOperationalMetrics: "Operational Metrics", pageData: "Data Readiness", pageMaterials: "Materials Planning", pageRuns: "Planning Runs",
    pageResults: "Schedule Results", pageRelease: "Release Management", pageBuffer: "Constraint Buffer Execution", pageDispatch: "Dispatch Suggestions", pagePublicDemo: "Public Demo Loop", pageExceptions: "Exceptions", pageCalendar: "Calendar Configuration", pageAdmin: "Administration",
    descriptionOverview: "Review planning context, exceptions, and the next work to perform.",
    descriptionOperationalMetrics: "Review DDOM daily performance by reliability, stability, and flow velocity.",
    descriptionData: "Check master data versions and operational snapshots.",
    descriptionMaterials: "Review DDMRP net flow and replenishment suggestions by buffer priority.",
    descriptionRuns: "Create, track, and recover planning runs.",
    descriptionResults: "Inspect schedules, load, Gantt views, and diagnostics.",
    descriptionRelease: "Control release using rope time, material, WIP, and buffers.",
    descriptionBuffer: "Coordinate order receipt and start by constraint-buffer stage and time zone.",
    descriptionDispatch: "Generate resource-level dispatch suggestions by buffer color, penetration, and shop-floor state.",
    descriptionPublicDemo: "Demonstrate DDAE config intake, SDBR demo run, and feedback handoff using the PUBLIC-DEMO-GOLDEN-DATA-V1 file package.",
    descriptionExceptions: "Handle failures, dead letters, and execution variance.",
    descriptionCalendar: "Review calendar elements, conflict priority, and final CP-SAT availability windows.",
    descriptionAdmin: "Manage master data, solvers, integrations, and access.",
    frameworkReady: "Page framework ready", emptyTitle: "This capability will open in its acceptance unit",
    emptyDescription: "This phase establishes navigation, planning context, and bilingual foundations without fabricated production data.",
    overallReadiness: "Overall readiness", loadingData: "Loading data status", loadingDataDescription: "Checking the latest master data version and operational snapshot.",
    refresh: "Refresh", generateOperationalSnapshot: "Generate operational snapshot", selectPlanningInputs: "Use as planning inputs", readinessLoadFailed: "Data readiness could not be loaded",
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
    yes: "Yes", no: "No", noNeedReschedule: "No reschedule needed", needReschedule: "Reschedule needed",
    issueCount: "data issues require attention", inputsSelected: "Selected as planning inputs",
    operationalSnapshotGenerated: "Operational snapshot generated.",
    operationalSnapshotGenerateFailed: "Operational snapshot generation failed.",
    operationalSnapshotMissing: "No operational snapshot is available to copy.",
    publicDemoContext: "Public demo loop", publicDemoSummary: "Public demo loop summary", runPublicDemo: "Run demo loop",
    publicDemoOnly: "Public demo only", controlledDemo: "Controlled contract demo", packageValidation: "Package validation",
    frozenPackage: "Frozen package", handoffValidation: "Handoff validation", ddaeHandoff: "DDAE to SDBR",
    contractValidation: "Contract validation", validationResults: "Validation results", feedbackHandoff: "Feedback handoff",
    adapterValidation: "Adapter validation", adventureWorksAdapter: "AdventureWorks scheduling adapter",
    adapterMode: "Adapter mode", generatedRows: "Generated rows", explicitCalendars: "Explicit resource calendars",
    formalSolverGate: "Formal solver gate", generatedPackage: "Generated package path",
    materialFeasibleClaim: "Material-feasible production claim",
    productDemoMode: "Product demo mode", productDemoProfile: "AdventureWorks ProductDemo profile",
    activeProfile: "Active profile", demoAuthority: "DemoAuthority data", authorityRows: "Authority rows",
    sourceClassCoverage: "Source class coverage", panelPolicy: "Panel policy", productDemoPanels: "Product demo panels",
    placeholderPanels: "Placeholder panels", sampleModePanels: "SampleMode panels", validationDeadLetters: "Validation dead letters",
    setupOmission: "Setup boundary", materialOmission: "Material feasibility boundary",
    sdbrFeedbackFiles: "SDBR to DDAE", boundary: "Boundary", nonClaims: "Non-claims",
    publicDemoLoadFailed: "Public demo loop could not be loaded", publicDemoRetryAdvice: "Check that the frozen package and handoff files are available, then retry.",
    publicDemoRunCompleted: "Public demo feedback files generated.", publicDemoRunNotReady: "Public demo is not ready. Check the DDAE handoff payload.",
    sdbrMarketControlKicker: "S-DBR flow control", sdbrMarketControlTitle: "Market promise and constraint protection",
    ccrPlannedLoad: "Constraint planned load", mtoSafeDate: "MTO safe promise", mtaReplenishmentLoad: "MTA replenishment load", unifiedBufferPriority: "Unified buffer priority",
    marketControlBoundary: "This panel consumes frozen configuration, schedule output, and DDMRP runtime input. It does not add DDAE-governed master parameters.",
    marketLoadStatus_Overloaded: "Beyond protective capacity", marketLoadStatus_NearLimit: "Near limit", marketLoadStatus_Watch: "Needs attention", marketLoadStatus_Protected: "Protected",
    marketLoadDetail: "CCR total {total} min ({hours} h) · MTO {mto} min · MTA {mta} min · peak load {max}% by effective capacity window",
    marketSafeDateUnavailable: "Capacity review needed", marketSafeDateExpired: "Expired: {date}", marketMtaMapped: "{count} mapped", marketMtaUnmapped: "{count} replenishment suggestions need execution mapping",
    marketPriorityCount: "{count} rows", marketPriorityDetail: "Red {red} · Yellow {yellow} · Green {green}",
    marketControlDetails: "View load and priority details",
    marketNoPriorityRows: "No unified buffer priority detail",
    marketNoLoadBuckets: "No constraint load detail",
    marketLoadBucketTitle: "Constraint load",
    marketPriorityRowsTitle: "Priority source",
    marketDemandClassMTO: "MTO order",
    marketDemandClassMTA: "MTA replenishment",
    marketPrioritySource_MTAStockBuffer: "Stock buffer",
    marketPrioritySource_MTOTimeBuffer: "Time buffer",
    marketPriorityItem: "Item {item} · location {location} · mapped order {order}",
    marketPriorityOrder: "Order {order}",
    bufferDailyLoadScope: "Remaining full-route order load, not the same as constraint-resource load",
    sdbrWhatIfKicker: "S-DBR execution what-if",
    sdbrWhatIfTitle: "Will the shock break the constraint?",
    scenarioType: "Scenario type",
    scenarioMtoExpedite: "Order insertion / expedite",
    scenarioResourceDowntime: "Downtime shock",
    scenarioSupplyDelay: "Supply delay",
    scenarioMtaRedShock: "MTA red replenishment shock",
    mtaRedCandidate: "MTA red candidate",
    noMtaRedCandidates: "No MTA red replenishment candidate is available for evaluation.",
    mtaCandidateSummary: "Candidate {candidate} · item {item} · location {location} · suggested qty {qty} · projected constraint load {minutes} min",
    additionalLoadMinutes: "Added / compressed load minutes",
    downtimeMinutes: "Downtime minutes",
    runSdbrWhatIf: "Evaluate shock",
    sdbrWhatIfBoundary: "Execution-layer impact only; the frozen schedule is not changed.",
    whatIfBeforeAfter: "Load change",
    whatIfRecommendation: "Recommended action",
    whatIfSimioHint: "Simio review suggested",
    whatIfDecision_AbsorbWithExistingPlan: "Absorb with current plan",
    whatIfDecision_AbsorbWithBufferAndProtectiveCapacity: "Absorb with buffer and protective capacity",
    whatIfDecision_ReviewBeforeRelease: "Review before release",
    whatIfDecision_ProtectCcrAndReviewReplan: "Protect CCR and review replan",
    whatIfDecision_ReviewRequired: "Manual review required",
    effectiveCapacity: "Effective capacity",
    loadChange: "Load change",
    loadPercentChange: "Load percent change",
    beforeAfterStatus: "Status change",
    whenUseSimio: "When should Simio be used?",
    simioRecommendationTitle: "When high-fidelity Simio validation is recommended",
    simioUseCaseCcrGroup: "The CCR is a group of machines, people, fixtures, or handling capacity.",
    simioUseCaseDisruption: "Downtime, rework, or inspection failure materially changes the result.",
    simioUseCaseReentrant: "The same order visits the same resource more than once.",
    simioUseCaseBranching: "Routing has many branches and path choices.",
    simioUseCaseQueueDrivers: "Handling, waiting, batching, or changeover dominates the flow time.",
    simioUseCaseQueueStory: "The team needs to see why queues exploded over time.",
    simioUseCaseStableModel: "A stable Simio model and data-maintenance process already exists.",
    businessUserView: "Business user view", sdbrExecutionDemo: "SDBR execution demo",
    sdbrExecutionDemoIntro: "This section explains in business language how SDBR receives the controlled DDAE handoff, validates whether it is trustworthy, converts it into bounded demo scheduling input, and sends feedback to DDAE for review.",
    demoConfidenceMeaning: "Demo confidence wording",
    productDemoOnlyExplanation: "ProductDemoOnly = the AdventureWorks product-demo profile, including explicitly completed DemoAuthority evidence.",
    publicDemoOnlyExplanation: "PublicDemoOnly = the evidence level for the underlying public data package and controlled fixture adapter.",
    ddmrpRuntime: "DDMRP runtime", ddmrpRuntimeStatus: "DDMRP runtime status", ddmrpRuntimeSummary: "DDMRP runtime summary",
    decouplingPoints: "Decoupling points", redZone: "Red", yellowZone: "Yellow", greenZone: "Green", aboveGreenZone: "Above green",
    replenishmentSuggestions: "Replenishment suggestions", missingData: "Missing data", viewDdmrpDetails: "Decoupling point details",
    item: "Item", onHand: "On hand", netFlowPosition: "Net flow position", planningBufferZone: "Planning buffer zone",
    executionBufferZone: "On-hand execution zone", suggestedReplenishmentQty: "Suggested replenishment qty",
    ddmrpReady: "DDMRP runtime data is available", ddmrpMissingData: "DDMRP inputs have missing data", ddmrpNoData: "No DDMRP decoupling points are available.",
    action_Replenish: "Replenish", action_Monitor: "Monitor",
    zone_Red: "Red: action required", zone_Yellow: "Yellow: watch", zone_Green: "Green: normal", zone_AboveGreen: "Above green: no replenishment",
    materialPlanningSummary: "Materials planning summary", criticalPriority: "Critical", attentionPriority: "Attention", normalPriority: "Normal",
    materialPlanningWorkbench: "Materials planning workbench", searchItemOrLocation: "Search item or location", sortBy: "Sort by",
    planningPriority: "Planning priority", bufferPercent: "% of buffer", openSupply: "Open supply", qualifiedDemand: "Qualified demand",
    materialPlanningLoadFailed: "Materials planning workbench could not be loaded", materialPlanningRetryAdvice: "Check that DDMRP runtime data is available and retry.",
    materialPlanningNoRows: "No material planning rows match the filters", materialPlanningNoRowsAdvice: "Adjust filters or check DDMRP input data.",
    materialDetail: "Material detail", selectMaterialForDetails: "Select a material to view details",
    materialDetailAdvice: "Details show the current snapshot boundaries, demand/supply components, and a trend placeholder.",
    topOfRed: "Top of red", topOfYellow: "Top of yellow", topOfGreen: "Top of green",
    supplyDemandComponents: "Demand and supply components", trendPlaceholder: "Trend analysis",
    trendPlaceholderMessage: "V1 shows the current snapshot. Historical buffer, on-hand, and net-flow trends will be added later.",
    demandComponentsCount: "{count} qualified demand rows", supplyComponentsCount: "{count} effective open supply rows",
    operationalMetricsContext: "Operational metrics scope", operationalMetricsOverview: "Operational metrics overview",
    operationalMetricsLoadFailed: "Operational metrics could not be loaded", operationalMetricsRetryAdvice: "Check that a completed planning run and the local service are available, then retry.",
    ddomMetricSet: "DDOM flow metrics", overallScore: "Overall score", varianceFeedback: "Variance feedback",
    feedbackForDDSOP: "Operating performance feedback for DDS&OP", metricAppliesTo: "Applies to", metricDoesNotApplyTo: "Does not apply to",
    dataCoverageIssues: "Data coverage gaps", noDataCoverageIssues: "No obvious data coverage gaps.",
    recommendedActions: "Recommended actions", metricQuestion: "Core question", metricFocus: "Focus",
    metricCoverage: "Data coverage", metricStatusGreen: "Green: running to model", metricStatusYellow: "Yellow: needs attention", metricStatusRed: "Red: intervention needed", metricStatusUnavailable: "Insufficient data",
    coverage_Available: "Available", coverage_NoActiveBufferOrders: "No active buffer orders", coverage_NoReleaseCandidates: "No release candidates",
    coverage_NoScheduledOrders: "No scheduled orders", coverage_NoExecutionEvents: "No execution events", coverage_NoArrivalEvents: "No arrival events", coverage_NoDispatchableOperations: "No dispatchable operations",
    issue_MASTER_DATA_VERSION_MISSING: "No master data version has been created.", issue_OPERATIONAL_STATE_SNAPSHOT_MISSING: "No operational state snapshot has been created.",
    issue_OPERATIONAL_STATE_SNAPSHOT_STALE: "The latest operational snapshot is stale.", issue_OPERATIONAL_STATE_SNAPSHOT_IN_FUTURE: "The latest operational snapshot is dated after the evaluation time.",
    issue_OPERATIONAL_SOURCE_NOT_PROVIDED: "The operational snapshot has no source system.", issue_RESOURCE_STATUS_NOT_CAPTURED: "The current snapshot does not include resource runtime status.",
    caseAcceptanceSummary: "Test case acceptance summary", testSystemCases: "Test system cases", caseAcceptanceTitle: "Case Acceptance Overview",
    caseGroup: "Case group", caseType: "Case type", expectedAssertions: "Expected assertions", passedAssertions: "Passed assertions", failureReasons: "Difference reasons",
    CPSATBusinessCases: "CP-SAT business cases", BusinessClosure: "Business closure cases",
    caseAcceptanceLoadFailed: "Case acceptance summary could not be loaded", caseAcceptanceRetryAdvice: "Check that the test service and test database are available.",
    totalCases: "Total cases", passedCases: "Passed", needsExecutionCases: "Needs execution", failedCases: "Failed",
    acceptancePassed: "Passed", acceptanceNeedsExecution: "Needs execution", acceptanceFailed: "Failed",
    purpose: "Purpose", releaseReadyCount: "Ready releases", blockingCodes: "Blocking codes", openScheduleResult: "Open schedule result",
    scheduleNotCompleted: "Schedule not completed", executeCaseFirst: "Execute and complete this case's Planning Run before opening the schedule result.",
    resetCase: "Reset case", resetAllCases: "Reset all cases", caseResetCompleted: "Case reset completed.", caseResetFailed: "Case reset failed.",
    PLANNING_RUN_NOT_COMPLETED: "Planning Run is not completed.", PLANNING_RUN_DEAD_LETTER: "Planning Run is dead-lettered and has no schedule result.",
    PLANNING_RUN_NOT_EXECUTED: "Planning Run has not been executed.",
    runMetrics: "Planning run status summary", allRuns: "All runs", queued: "Queued", running: "Running", completed: "Completed",
    deadLetter: "Dead letter", pending: "Pending", failed: "Failed", cancelled: "Cancelled", allStatuses: "All statuses",
    status: "Status", requester: "Requester", filterRequester: "Filter requester", exceptionsOnly: "Exceptions only",
    timeRange: "Time range", allTime: "All time", last24Hours: "Last 24 hours", last7Days: "Last 7 days",
    last30Days: "Last 30 days", allSolvers: "All solvers", startedAt: "Started at",
    createPlanningRun: "Create planning run", runsLoadFailed: "Planning runs could not be loaded", runsRetryAdvice: "Reload before trying the operation again.",
    runId: "Run ID", problem: "Planning scenario", solver: "Solver", requestedAt: "Requested at", duration: "Duration",
    attempts: "Attempts", actions: "Actions", noPlanningRuns: "No planning runs", noPlanningRunsDescription: "Select valid inputs and create the first planning run.",
    wizardTitle: "New Planning Run", wizardSteps: "Create planning run steps", selectInputs: "Select inputs", setPolicy: "Set policy",
    reviewSubmit: "Review and submit", scheduleStart: "Schedule start", selectInputsFirst: "Select valid inputs in Data Readiness first.",
    timeBufferProfile: "Time buffer parameters", timeBufferCalculator: "Time buffer calculator",
    timeBufferFormula: "Time buffer = OLT × (1 + variability and flex coefficient)",
    operatingLeadTime: "Operating Lead Time OLT (minutes)", variabilityProfile: "Upstream variability",
    variabilityLow: "Low", variabilityMedium: "Medium", variabilityHigh: "High",
    variabilityHelp: "Upstream variability reflects equipment downtime, supplier punctuality, rework, and scrap. Higher variability needs more time protection before the constraint.",
    capacityFlexProfile: "Capacity flex", capacityFlexHigh: "High flex", capacityFlexMedium: "Medium flex", capacityFlexLow: "Low flex",
    capacityFlexHelp: "Capacity flex reflects protective capacity and catch-up ability in upstream non-constraints. Higher flex can support a smaller time buffer.",
    timeBufferMultiplier: "Recommended multiplier", recommendedTimeBuffer: "Recommended time buffer", useRecommendedBuffer: "Use recommendation",
    timeBufferRecommendationApplied: "Recommended time buffer applied.",
    timeBuffer: "Time buffer (minutes)", timeLimit: "Solver time limit (seconds)", maxAttempts: "Maximum attempts",
    retryDelay: "Retry delay (seconds)", pausedUnavailable: "Paused and unavailable", enableSimio: "Enable Simio validation",
    back: "Back", next: "Next", submitRun: "Submit planning run", available: "Available", unavailable: "Unavailable",
    enqueue: "Enqueue", execute: "Execute now", processQueue: "Process queue", cancel: "Cancel", recover: "Recover", openResults: "Open results", view: "View",
    seconds: "sec", notStarted: "Not started", frozenInputs: "Frozen inputs", solverParameters: "Solver parameters", workerLease: "Worker and lease",
    timeline: "Status timeline", diagnostics: "Solver diagnostics", auditEvents: "Audit events", noWorker: "No worker assigned",
    businessDiagnosis: "Business diagnosis", technicalDetails: "Technical details",
    diag_ORTOOLS_TIME_LIMIT_CONFIGURED: "The planning calculation has a time limit; it will return the best available result or a timeout diagnosis.",
    diag_ORTOOLS_CP_SAT_MODEL: "This schedule considered optional resources, operation sequence, finite capacity, setup, parallel resources, time windows, and calendar capacity.",
    diag_ORTOOLS_OBJECTIVE_STRATEGY: "This schedule used a balanced strategy across delivery, flow time, and bottleneck protection.",
    diag_ORTOOLS_SETUP_TRANSITIONS_ENABLED: "This schedule considered setup time between product families.",
    diag_ORTOOLS_RESOURCE_EFFICIENCY_ENABLED: "This schedule considered resource efficiency when calculating operation duration.",
    diag_ORTOOLS_OPERATION_TIME_WINDOWS_ENABLED: "This schedule considered earliest-start and latest-finish windows.",
    diag_ORTOOLS_CAPACITY_BUCKETS_ENABLED: "This schedule considered calendar and capacity-bucket limits.",
    diag_ORTOOLS_CUSTOM_OBJECTIVE_WEIGHTS_ENABLED: "This schedule used custom objective weights.",
    dataUpdated: "Data was updated. Reload before trying again.", runCreated: "Planning run created", submissionFailed: "Planning run creation failed",
    confirmEnqueue: "Enqueue this planning run?", confirmExecute: "Run this planning task with OR-Tools CP-SAT now?",
    confirmProcessQueue: "Let the interactive worker claim and calculate this planning run?", queueProcessed: "Queued planning run processed.",
    replanCreatedQueued: "Replan run created and queued. Process it in Planning Runs.",
    confirmReplan: "Create and enqueue a new replan run from the current schedule?",
    cancelReasonPrompt: "Enter a cancellation reason.", recoverReasonPrompt: "Enter a recovery reason.",
    actionFailed: "The operation failed. Reload and try again.", solverUnavailable: "The selected solver is unavailable.",
    confirmAction: "Confirm action", confirm: "Confirm", notifySuccess: "Action completed", notifyError: "Action failed",
    resultContext: "Schedule result scope", planningRun: "Planning run", scheduleResultLoadFailed: "Schedule result could not be loaded",
    scheduleResultRetryAdvice: "Select a completed planning run and retry.", noCompletedSchedules: "No completed schedule results",
    completeRunFirst: "Complete a planning run first.", scheduleKpis: "Schedule result metrics", onTimeOrders: "Plan on-time orders",
    lateOrders: "Plan late orders", overloadMinutes: "Overload minutes", redBuffers: "Red buffers", peakLoad: "Peak load",
    scheduleResultViews: "Schedule result views", ganttChart: "Gantt chart", resourceLoad: "Resource load", orderDelivery: "Order delivery",
    ganttMode: "Gantt mode", resourceOccupationView: "Resource occupation", workOrderFlowView: "Work-order flow",
    resource: "Resource", workOrder: "Work order", barType: "Bar type", bufferZone: "Buffer zone", fromDate: "From date",
    toDate: "To date", zoom: "Zoom", ganttLegend: "Gantt legend", processing: "Processing",
    greenBuffer: "Green time buffer", yellowBuffer: "Yellow time buffer", redBuffer: "Red time buffer",
    maintenance: "Maintenance", unavailableTime: "Unavailable time",
    loadViews: "Load views", systemLoad: "System load", singleResourceLoad: "Single resource load", resourceType: "Resource type",
    owner: "Owner", category: "Category", date: "Date", loadMinutes: "Load minutes", availableCapacity: "Available capacity",
    utilization: "Utilization", released: "Released", unreleased: "Unreleased", remainingLoad: "Remaining load",
    sdbrFlowControl: "S-DBR flow control", plannedLoadAndProtectiveCapacity: "Planned load and protective capacity",
    plannedLoad: "Planned load", safeDate: "Safe date", releaseDiscipline: "Release discipline", stabilityGuidance: "Stability guidance",
    protectiveCapacity: "Protective capacity", earliestSafeDate: "Earliest safe date", monitorOnly: "Monitor only, not a hard constraint",
    flowStatus_Protected: "Protected", flowStatus_NearLimit: "Near limit", flowStatus_Overloaded: "Overloaded",
    flowStatus_Available: "Available as an initial window", flowStatus_NeedsCapacityReview: "Needs capacity review",
    flowAction_OperateByBufferPriority: "Operate by buffer priority",
    flowAction_ReviewBeforeInsertOrder: "Review before inserting orders",
    flowAction_CoordinateBeforeReleaseOrPromise: "Coordinate capacity before release or promise",
    flowAction_NoHardConstraintNeeded: "No hard constraint needed",
    flowAction_MonitorBeforeInsertOrder: "Monitor before inserting orders",
    flowAction_ProtectiveCapacityReview: "Review protective capacity",
    flowAction_EscalateCapacityOrReplanReview: "Coordinate capacity; review replan only if needed",
    flowAction_AbsorbWithBufferAndProtectiveCapacity: "Absorb with buffers and protective capacity first",
    flowAction_OnlyWhenBufferOrLoadThresholdIsBreached: "Replan only when buffer or load thresholds are breached",
    protectiveStatus_Healthy: "Protected", protectiveStatus_Watch: "Watch", protectiveStatus_AtRisk: "At risk", protectiveStatus_CandidateConstraint: "Candidate constraint",
    product: "Product", dueDate: "Due date", plannedCompletion: "Planned completion", delayMinutes: "Delay minutes",
    decisionSupport: "Decision support", scenarioComparison: "Scenario comparison", baselineScenario: "Baseline",
    candidateScenario: "Candidate", compare: "Compare", allResources: "All resources", allOrders: "All orders",
    allBarTypes: "All bar types", allZones: "All zones", allOptions: "All", constraint: "Constraint",
    nonConstraint: "Non-constraint", candidateConstraint: "Candidate constraint", noGanttRows: "No Gantt tasks match the current filters.",
    noDiagnostics: "The solver returned no diagnostics.", onTime: "On time", late: "Late", unscheduled: "Unscheduled", code: "Technical code", message: "Message",
    generatedAt: "Generated at", recommended: "Recommended", selectScenario: "Select for review", selectionReasonPrompt: "Enter the reason for selecting this scenario.",
    selectedForReview: "Scenario selected for review.", candidateReducesOverload: "Candidate reduces resource overload.",
    candidateReducesLateOrders: "Candidate reduces late orders.", candidateReducesRedBuffers: "Candidate reduces red buffers.",
    baselineBetterScore: "Baseline has the better overall score.", candidateBetterScore: "Candidate has the better overall score.",
    planGovernance: "Plan governance", publicationGovernance: "Plan publication governance", publicationLoadFailed: "Plan publication status could not be loaded",
    publicationRetryAdvice: "Refresh the schedule result and retry.", publicationStatus: "Publication status", scheduleFingerprint: "Schedule fingerprint",
    allowedPublicationActions: "Allowed actions", publicationPackage: "Publication package", packageId: "Package ID", targetSystems: "Target systems",
    publishedBy: "Published by", publishedAt: "Published at", solverStatus: "Solver status", publicationHistory: "Publication history",
    outputGovernance: "Plan output", outputAvailability: "Output availability", outputPackage: "Plan output package", outputPackageId: "Output package ID",
    completenessStatus: "Output checks", passedChecks: "Passed checks", failedChecks: "Failed checks", releaseGovernance: "Release readiness",
    recommendationCount: "Release recommendations", unauthorizedCount: "Unauthorized", auditGovernance: "Action history", auditEventCount: "Records",
    scenarioSelectionCount: "Scenario selections", workOrderCommandCount: "Work-order commands", publicationActionCount: "Publication actions",
    simulationResults: "Simulation results", simioValidation: "Simio validation", simioValidationStatus: "Validation status", simioRunner: "Runner", simioPackage: "Validation package",
    simioModelPath: "Model path", simioResultModelPath: "Result model", simioIssues: "Issues", simioKpis: "Validation KPIs",
    simioFeasibility: "Feasibility", simioThroughput: "Throughput", simioQueueMetrics: "Queue metrics", simioWipMetrics: "WIP metrics",
    simioResourceUtilization: "Resource utilization", simioResultCoverage: "Result coverage", simioRunnerMode: "Runner mode",
    simioTemplateRegistry: "Simio simulation templates", simioTemplate: "Simulation template", activeSimioTemplate: "Active template",
    templateId: "Template ID", templateName: "Template name", templateVersion: "Template version", templatePath: "Template path",
    templateSourceType: "Template source type", timeUnitPolicy: "Time unit rule", desktopValidationStatus: "Desktop validation status",
    templateStatus: "Template status", configuredTemplates: "Registered templates", templatePolicy: "Template usage rule",
    defaultTemplateDirectory: "Default template directory", runtimeRule: "Runtime rule", timeUnitRule: "Time unit rule",
    templateReady: "Template configured. Simulation validation will copy it into a derived run model.",
    templateNeedsAttention: "Template configuration needs review.", pendingManualCheck: "Pending manual Desktop check",
    simioRunnerAuto: "Auto", simioRunnerMock: "Mock", simioRunnerLocal: "Local headless", runSimioValidation: "Run simulation validation",
    simioOptionalValidation: "Available after the plan is completed on the simulation results tab.", simioValidationRequested: "Simio simulation validation completed.",
    noSimulationResult: "Simio simulation validation has not been requested.", busyMinutes: "Busy minutes", starvedMinutes: "Starved minutes", evidence: "Data source",
    actualStart: "Actual start", actualEnd: "Actual end", queueWaitMinutes: "Queue wait", wipAfterStart: "WIP after start",
    wipAfterEnd: "WIP after end", eventStatus: "Event status", durationMinutes: "Processing / dwell time",
    simioOrderFilter: "Work-order filter", simioOrderFilterPlaceholder: "Search work order",
    simioQueueWaitFilter: "Wait time", allSimulationEvents: "All events", allWaitTimes: "All wait times",
    waitGreaterThanZero: "Wait > 0 minutes", waitGreaterThan30: "Wait > 30 minutes", waitGreaterThan60: "Wait > 60 minutes",
    simulationRowsRange: "Showing {start}-{end} / {total} rows", noSimulationRows: "No simulation work-order records match the filters",
    parsedSources: "Data used", unavailableSources: "Data not available",
    simioSourceParsedFromSDBROutputRows: "From work-order output rows", simioSourceParsedFromPostRunLogs: "From Simio run logs",
    simioSourceParsedFromInteractiveStatistics: "From Simio interactive statistics", simioSourceParsed: "Fully parsed",
    simioSourcePartialResultParsed: "Partial simulation result parsed", simioSourceUnavailable: "Unavailable",
    simioPartialWithAvailableMetrics: "Partial simulation result parsed; available returned metrics are shown below.",
    businessDecision: "Business decision", publicationDecision: "Publication progress", outputDecision: "Output readiness", releaseDecision: "Release readiness",
    simulationDecision: "Simulation validation", auditDecision: "Action history", technicalDetails: "Technical details", showDetails: "Expand", hideDetails: "Collapse",
    planCanPublish: "Plan can continue through publication", planNeedsReview: "Plan needs review or approval first", outputReadyForReview: "Plan output is complete", outputNeedsAttention: "Plan output needs attention",
    releaseReadySummary: "Release recommendations are available", releaseNoRecommendation: "No release recommendations yet", simulationPassedSummary: "Simulation passed and can support review",
    simulationWarningSummary: "Simulation ran with warnings", simulationNotRunSummary: "Simulation has not been run", auditReadySummary: "Key actions are recorded",
    simioIssue_SIMIO_RESULT_LOG_MISSING: "Full statistics file was not produced; other result data is being used.",
    simioIssue_SIMIO_UNFINISHED_ORDERS: "Simulation shows one or more unfinished orders.",
    simioIssue_SIMIO_BINARY_LOGS_PARTIAL: "Some simulation logs only returned key metrics.",
    simioIssue_SIMIO_RESULT_PARTIAL: "Simulation completed, but some details could not be parsed.",
    simioEvent_OperationStarted: "Operation started", simioEvent_OperationCompleted: "Operation completed", simioEvent_OrderStarted: "Order started", simioEvent_OrderCompleted: "Order completed",
    externalDelivery: "External delivery", notSent: "Not sent", packageReady: "Output package available", packageUnavailable: "Output package unavailable",
    externalDeliveryOwnedByIntegrations: "ERP/MES delivery is owned by the external integration module. This version only creates an internal output package.",
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
    releaseContext: "Release evaluation", evaluatedAt: "Evaluated at", reevaluate: "Re-evaluate",
    releaseSnapshotRefreshed: "Mock operational snapshot refreshed and release gate re-evaluated.", releaseLoadFailed: "Release evaluation could not be loaded",
    releaseRetryAdvice: "Check the completed plan and operational snapshot.", noReleaseRuns: "No completed plan is available for evaluation",
    totalOrders: "Total orders", readyToRelease: "Ready", blocked: "Blocked", authorized: "Authorized",
    penetration: "Penetration", ropeReleaseTime: "Rope release time", materialStatus: "Material status", wipStatus: "WIP status",
    plannedStart: "Planned start", blockingReason: "Blocking reason", releaseGate: "Release gate", dispatchPackage: "Dispatch package",
    authorizeRelease: "Authorize release", viewDispatch: "View dispatch", viewReason: "View reason", noBlockReason: "No blocking reasons.",
    snapshotStatus: "Snapshot status", freshSnapshot: "Operational snapshot is fresh", staleSnapshot: "Operational snapshot is stale; authorization is blocked",
    futureSnapshot: "Operational snapshot is from the future; authorization is blocked", clear: "Clear", early: "Early", notReleased: "Not released",
    snapshotRefreshAdvice: "Sync or create a fresh resource/material/WIP snapshot, then re-evaluate release. A stale snapshot alone does not require rescheduling.",
    releasePolicyVersion: "Release policy version", policyEvidence: "Policy evidence", reasonDetails: "Trigger parameters", stabilityDecision: "Stability decision",
    ropeBufferMinutes: "Policy rope minutes", materialCheckWindowMinutes: "Material check window minutes", materialLookaheadMinutes: "Material check window minutes",
    maxWipCount: "Policy WIP limit", policyMaxWipCount: "Policy WIP limit", snapshotMaxWipCount: "Snapshot WIP limit",
    effectiveMaxWipCount: "Effective WIP limit", actualWipCount: "Current WIP", projectedWipCount: "Projected WIP",
    minutesUntilRelease: "Minutes until release", toleranceMinutes: "Stability tolerance minutes", replanThresholdMinutes: "Replan threshold minutes",
    consecutiveBlockedThreshold: "Consecutive block threshold", replanCooldownMinutes: "Replan cooldown minutes", action: "Action",
    deviationMinutes: "Deviation minutes", absoluteDeviationMinutes: "Absolute deviation minutes", reasonCodeLabel: "Business reason", riskCount: "Risk count",
    recommendedAction: "Recommended action", requiresReschedule: "Requires reschedule",
    reason_ROPE_TIME_NOT_REACHED: "Rope release time has not been reached.", reason_MATERIAL_SHORTAGE: "Available material is insufficient.",
    reason_MATERIAL_INBOUND_PENDING: "Required material is still inbound.", reason_WIP_LIMIT_EXCEEDED: "Projected WIP would exceed the limit; keep as a warning, not a formal dispatch.",
    reason_OPERATIONAL_SNAPSHOT_STALE: "The operational snapshot is stale.", reason_OPERATIONAL_SNAPSHOT_FUTURE: "The operational snapshot is later than the evaluation time.",
    action_RefreshOperationalSnapshotAndReevaluate: "Sync/create a fresh operational snapshot and re-evaluate release",
    action_CorrectEvaluationTimeOrSnapshot: "Correct the evaluation time or selected snapshot",
    action_ReadyForRelease: "Ready for release",
    action_HoldForWip: "Hold until WIP decreases",
    action_WaitForInbound: "Wait for inbound material",
    action_ExpediteMaterial: "Expedite material or adjust supply",
    action_Monitor: "Monitor",
    action_Review: "Planner review required",
    action_Replan: "Replan recommended",
    reason_DeviationAtReplanThreshold: "Deviation reached the replan threshold",
    reason_WithinTolerance: "Deviation remains within tolerance",
    reason_ConsecutiveGateBlocks: "Consecutive gate blocks reached the threshold",
    reason_ReplanCooldownActive: "Replan cooldown is active; review before deciding",
    authorizeImpact: "Authorize this work order? The gate snapshot will be audited and a dispatch package generated.", releaseAuthorized: "Work order release authorized.",
    commandRecorded: "Work order command recorded.", pageOf: "Page {page} of {pages}",
    bufferContext: "Constraint buffer", bufferMatrix: "Two-stage five-zone buffer matrix", bufferLoadFailed: "Buffer execution board could not be loaded",
    bufferRetryAdvice: "Select a completed plan containing authorized orders.", noBufferRuns: "No completed plan is available", bufferOwner: "Buffer owner",
    dailyLoad: "Daily load", lastScheduled: "Last scheduled", hours: "hours", yetToBeReceived: "Yet to be received", received: "Received",
    Early: "Early", Green: "Green", Yellow: "Yellow", Red: "Red", Late: "Late", orderCount: "Orders", totalLoad: "Total load",
    mesDispatch: "MES dispatch", mesDispatchQueue: "MES dispatch queue", mesDispatchBoundary: "This area shows the internal dispatch queue only; it does not send to MES.",
    dispatchContext: "Dispatch suggestions", dispatchLoadFailed: "Dispatch suggestions could not be loaded", dispatchRetryAdvice: "Select a completed planning run with release data.", noDispatchRuns: "No completed planning run is available",
    dispatchableOperations: "Dispatchable operations", candidateWarnings: "Candidates / warnings", queueJumpSuggestions: "Queue-jump suggestions", plannerConfirmations: "Planner confirmations",
    replanSuggestions: "Replan suggestions", dispatchRank: "Dispatch rank", planSequence: "Plan sequence", conflictResult: "Conflict result",
    plannerConfirmation: "Planner confirmation", mesDispatchUnavailable: "MES dispatch queue unavailable", noDispatchRows: "No dispatchable operations.",
    noDispatchWarnings: "No candidates or warnings.", Dispatchable: "Dispatchable", CandidateOnly: "Candidate / warning", FollowPlan: "Follow plan",
    SuggestQueueJump: "Suggest queue jump", NeedsReplan: "Needs replan", Clear: "Clear", ReleaseNotAuthorized: "Release not authorized",
    LatestOperationalStateBlocked: "Latest gate blocked", LatestOperationalStateNotReady: "Latest state not ready",
    ArrivalNotConfirmed: "Arrival not confirmed", DispatchRejected: "MES rejected", ExceptionReported: "Shop-floor exception",
    NotArrived: "Not arrived", MissingArrivalConfirmation: "Arrival not confirmed", Arrived: "Arrived", Processing: "Processing", Completed: "Completed",
    currentExecution: "Shop-floor status", arrivalStatus: "Arrival status", recommendation: "Recommendation", recommendationReason: "Reason",
    issueDispatchSuggestions: "Generate MES dispatch package", dispatchSuggestionNotIssued: "No dispatch suggestion package generated yet.",
    dispatchSuggestionIssued: "MES dispatch suggestion package generated", packageId: "Package ID", mockDeliveryStatus: "Mock delivery status",
    MockDispatchSuggestionIssued: "Mock dispatch suggestion generated", Accepted: "Accepted", Duplicate: "Duplicate",
    Hold: "Hold", QueueJump: "Queue jump", ReviewAndReplan: "Review and replan",
    required: "Required", ConstraintResourceSetupOrIdleRisk: "Constraint resource may incur setup or idle risk",
    RedZoneCanOverrideSetupLossOnlyAfterPlannerConfirmation: "Red zone may override setup loss only after planner confirmation",
    bufferOrderDetail: "Buffer order detail", customer: "Customer", currentReason: "Current reason", receiveStatus: "Receipt status",
    executionTransaction: "Execution transaction", eventType: "Event type", arrivedBuffer: "Arrived at buffer", startedOperation: "Started operation", eventAt: "Event time",
    measureType: "Measure type", measureValue: "Measure value", reasonCode: "Reason code", selectReason: "Select a reason code", recordTransaction: "Record transaction",
    reasonRequiredForLate: "Late-zone transactions require a standard reason code.", Quantity: "Quantity", CompletionPercent: "Completion percent", Hours: "Hours",
    transactionRecorded: "Execution transaction recorded.", receiveOrStart: "Receive / Start", reason_MATERIAL_SHORTAGE_CODE: "Material shortage",
    reason_EQUIPMENT_DOWN_CODE: "Equipment down", reason_STAFF_ABSENCE_CODE: "Staff absence", reason_QUALITY_REWORK_CODE: "Quality rework",
    exceptionContext: "Exception center", severity: "Severity", exceptionLoadFailed: "Exception center could not be loaded", exceptionRetryAdvice: "Check the service and retry.",
    totalExceptions: "Total exceptions", criticalExceptions: "Critical", warningExceptions: "Warnings", openExceptions: "Open", object: "Object", occurredAt: "Occurred at",
    businessImpact: "Business impact", suggestedAction: "Suggested action", exceptionDetail: "Exception detail", allSeverities: "All severities", allSources: "All sources",
    Critical: "Critical", Warning: "Warning", Information: "Information", impact_ScheduleUnavailable: "Schedule output unavailable", impact_ConstraintMayStarve: "Constraint may starve",
    impact_ExecutionThreatensSchedule: "Execution variance threatens the schedule", impact_ScheduleStabilityAtRisk: "Schedule stability is at risk",
    action_RecoverPlanningRun: "Recover planning run", action_ReviewPlanningRunFailure: "Review failed run", action_ExpediteConstraintBuffer: "Expedite constraint buffer",
    action_ReviewExecutionAlert: "Handle execution alert", action_ReviewReplanRequest: "Review replan request", viewDetail: "View detail", relatedObjects: "Related objects", resolutionActions: "Resolution actions",
    auditTrail: "Audit trail", noAuditTrail: "No audit trail", type_PlanningRunDeadLetter: "Planning run dead letter", type_PlanningRunFailed: "Planning run failed", type_ConstraintBufferRisk: "Constraint buffer risk",
    type_ExecutionAlert: "Execution alert", type_ReplanSuggestion: "Replan suggestion",
    calendarContext: "Calendar configuration", calendarPreviewLoadFailed: "Calendar preview could not be loaded", calendarPreviewRetryAdvice: "Check that master data and resource calendars are available, then retry.",
    calendarElements: "Calendar elements", calendarRequiredElements: "Required element check", cpSatCapacityWindows: "CP-SAT capacity windows", finalCapacityWindows: "Final availability windows",
    sourceRules: "Source rules", appliedCalendarElements: "Recognized calendar rules", cpSatNeedReason: "Why CP-SAT needs it", missingImpactDomain: "Impact if missing",
    previewMode: "Preview mode", finalWindowCount: "Final windows", missingDailyCapacityDates: "Missing daily capacity dates", noCalendarWindows: "No final availability windows in this range.",
    noCalendarElements: "No calendar rules were recognized for this resource.", elementType: "Element type", sourceId: "Source ID", start: "Start", end: "End",
    calendarOperation: "Calendar operations", calendarWorkbenchTitle: "Resource-level calendar configuration", patternBased: "Pattern based",
    calendarWorkbenchDescription: "Uses a work-week plus day-pattern structure: administrators maintain base calendars, planners maintain temporary overrides, and active settings are frozen into new Planning Runs.",
    workSchedules: "Work schedules / Base calendar", dayPatterns: "Day patterns / Work periods", calendarExceptions: "Holidays and maintenance",
    holidayDate: "Holiday date", maintenanceStart: "Maintenance start", maintenanceEnd: "Maintenance end", saveWorkSchedule: "Save work schedule",
    weekdayMonday: "Monday", weekdayTuesday: "Tuesday", weekdayWednesday: "Wednesday", weekdayThursday: "Thursday",
    weekdayFriday: "Friday", weekdaySaturday: "Saturday", weekdaySunday: "Sunday",
    resourceCalendarAssignment: "Resource calendar assignment", workPeriodExceptions: "Overtime / Temporary overrides / Downtime", calendarRules: "Fixed rules",
    calendarPriorityRule: "Maintenance > holiday > temporary override > overtime > base shift", timezone: "Timezone",
    timezoneRule: "Version 1 generates capacity windows in the calendar timezone; Asia/Shanghai is the China-site default.", crossShiftRule: "Cross-shift processing rule",
    crossShiftRuleDescription: "Operations must currently fit inside one availability window; continuous cross-shift processing needs later confirmation.",
    noCalendarConfigRows: "No configuration records yet.", adminCalendarMoved: "Calendar configuration has moved to the dedicated page; administration keeps only capability summaries and current records.",
    openCalendarConfiguration: "Open calendar configuration", baseCalendarSummary: "Base calendar summary", calendarOverrideSummary: "Temporary override summary",
    administrationContext: "Administration", sensitiveSettingsReadOnly: "Sensitive connection parameters are read-only.", administrationLoadFailed: "Administration could not be loaded",
    administrationRetryAdvice: "Check the local service and retry.", adminMasterDataTitle: "Master Data Administration", importPreview: "Import preview",
    importPreviewDescription: "Select an object, review structured preview and pre-validation, then generate a master data version.", importFile: "Import file", preValidate: "Pre-validate",
    generateVersion: "Generate version", routingImport: "Import routings", noImportSelected: "No import object selected", rawJsonHidden: "Raw JSON is hidden by default and available only in administrator debug mode.",
    adminSystemTitle: "Integration and Solver Settings", policyConfiguration: "Scheduling policy configuration", cpSatAssumptions: "CP-SAT Modeling Assumptions",
    tunableParameters: "Tunable parameters", deferredRules: "Deferred rules", driverStatus: "Driver status", calendar: "Calendar", calendarLayers: "Four resource-calendar layers",
    readOnly: "Read-only", partialEditable: "Partially configurable", objectCount: "Current count", importEndpoint: "Import endpoint", reservedFields: "Reserved fields", structuredPreview: "Structured preview",
    preValidationRequired: "Pre-validation before import", versionAfterImport: "Version after import", capabilityStatus: "Capability status", lastSync: "Last sync",
    workerQueue: "Worker queue", stateStore: "State store", DayDefinition: "Day definition", WeekDefinition: "Week definition", TemporaryShiftOverride: "Temporary shift override",
    ExclusionOrMaintenance: "Exclusion or maintenance change", Overtime: "Overtime", calendarOverrides: "Temporary overrides", calendarOverrideConfig: "Calendar temporary override configuration",
    baseCalendars: "Base calendars", baseCalendarConfig: "Base calendar configuration", displayName: "Display name", workingWeekdays: "Working weekdays",
    shiftStart: "Shift start", shiftEnd: "Shift end", createBaseCalendar: "Create base calendar", baseCalendarCreated: "Base calendar created.",
    baseCalendarFailed: "Base calendar creation failed.", baseCalendarBoundary: "Active base calendars and resource assignments are frozen into new Planning Runs and drive CP-SAT capacity buckets; complex conflict approval remains later.",
    assignmentId: "Assignment ID", assignCalendar: "Assign calendar", calendarAssignment: "Calendar assignment", calendarAssignmentCreated: "Resource calendar assignment created.",
    calendarAssignmentFailed: "Resource calendar assignment creation failed.", noBaseCalendars: "No base calendars.", noCalendarAssignments: "No resource calendar assignments.",
    overrideId: "Override ID", calendarId: "Calendar ID", overrideType: "Override type", effectiveStart: "Effective start", effectiveEnd: "Effective end",
    capacityDelta: "Capacity delta minutes", shiftName: "Shift name", reason: "Reason", createOverride: "Create override", calendarOverride: "Calendar override",
    noCalendarOverrides: "No temporary calendar overrides.", calendarOverrideCreated: "Calendar override created.", calendarOverrideFailed: "Calendar override creation failed.",
    calendarOverrideBoundary: "Active temporary overrides drive new Planning Runs; maintenance > holiday > temporary override > overtime > base shift. Approval flow is status-only for now.",
    calendarScope: "Calendar scope", ResourceOnly: "Resource only", conflictPriority: "Conflict priority", ApprovalFlowStatus: "Approval flow",
    StatusOnly: "Status fields only", Maintenance: "Maintenance", Holiday: "Holiday", BaseShift: "Base shift", Draft: "Draft", Active: "Active", Retired: "Retired",
    Ready: "Ready", SimioXmlProjectExport: "Simio XML project export",
    RateInterpretation: "Rate interpretation", Units: "Units", SchedulingWindow: "Scheduling window",
    BufferBoundaries: "Buffer boundary ratios", PiecesPerHour: "Pieces/hour", HoursPerPiece: "Hours/piece", MinutesPerPiece: "Minutes/piece",
    BufferMinutes: "Buffer minutes", SetupMinutes: "Setup minutes", DurationMinutes: "Duration minutes", FixedOffsetMinutes: "Fixed offset minutes",
    WindowStart: "Window start", PreferredCompletionTime: "Preferred completion time", ShipmentCutoffRule: "Shipment cutoff rule", GreenRatio: "Green ratio",
    YellowRatio: "Yellow ratio", RedRatio: "Red ratio", NotConfigured: "Not configured", Paused: "Paused", Available: "Available", Unavailable: "Unavailable",
    Applied: "Applied", PartiallyApplied: "Partially applied",
    Idle: "Idle", Online: "Online", Healthy: "Healthy", Unhealthy: "Unhealthy",
    navOrderCommitments: "Order Commitments", pageOrderCommitments: "Order Commitments", descriptionOrderCommitments: "Review MTO evaluations, evidence, and planner decisions awaiting action.",
    orderCommitmentSummary: "Order commitment summary", awaitingDecision: "Awaiting decision", confirmationRequired: "Confirmation required", materialPending: "Material pending", acceptedPendingSchedule: "Accepted, pending formal schedule",
    searchOrderOrProduct: "Search order or product", allStatuses: "All statuses", order: "Order", product: "Product", requestedDueAt: "Requested due", earliestSafePromise: "Earliest safe promise",
    ccrLoadBeforeAfter: "CCR load before / after", protectionThresholdSource: "Protection threshold source", materialStatus: "Material status", recommendation: "Recommendation", reservationStatus: "Reservation status", exceptionStatus: "Exception status",
    actions: "Actions", viewDetails: "View details", orderCommitmentEvaluation: "Order commitment evaluation", orderCommitmentLoadFailed: "Order commitment evaluations could not be loaded", orderCommitmentRetryAdvice: "Check the service and retry.", orderCommitmentDetailLoading: "Loading order commitment evaluation details.", orderCommitmentDetailLoadFailed: "Order commitment evaluation details could not be loaded.",
    materialSkipReasonRequired: "Provide a business reason when material checking is turned off.", orderCommitmentRevisionConflict: "Workbench state changed. The current evaluation was refreshed; review it before acting again.", orderCommitmentReevaluationFailed: "This order commitment could not be re-evaluated.", orderCommitmentNotReevaluatable: "This evaluation is closed or superseded and cannot be re-evaluated.", orderCommitmentNotFound: "The order commitment evaluation was not found. Refresh and try again.",
    requiredDecisionEvidenceMissing: "Provide a decision reason and complete the risk acknowledgements required for this action.", orderCommitmentEvidenceChanged: "Decision evidence changed. The current evaluation was refreshed; choose the action again.", orderCommitmentReplayConflict: "This decision conflicts with the recorded result. The evaluation was refreshed and was not retried.", orderCommitmentDecisionFailed: "This order commitment decision could not be recorded. Review it and try again.", orderCommitmentDecisionRecorded: "Order commitment decision recorded:",
    noOrderCommitments: "No order commitment evaluations are available.", orderDetails: "Order details", capacityEvidence: "Capacity evidence", materialEvidence: "Material evidence", decision: "Planner decision", reservation: "Planning reservation",
    auditHistory: "Audit history", technicalDetails: "Technical trace", selectedPromise: "Selected promise", earliestSafeAssessment: "Earliest safe assessment", requestedDateAssessment: "Requested-date assessment",
    loadBefore: "Load before", loadAfter: "Load after", loadPercent: "Load percent", protectionThreshold: "Protection threshold", thresholdState: "Threshold state", materialCheck: "Material check",
    materialFreshness: "Material evidence freshness", materialLines: "Material requirement lines", acceptedPromise: "Accepted promise", decidedBy: "Decided by", decidedAt: "Decided at", decisionReason: "Decision reason", ccrRiskAcknowledged: "CCR risk acknowledged", materialRiskAcknowledged: "Material risk acknowledged", supersededByEvaluation: "Superseding evaluation",
    reservationBatch: "Reservation batch", demandCommitment: "Demand commitment", boundary: "Business boundary", recommendationOnly: "Recommendation only; the planner makes the final decision.",
    externalOrderAcceptance: "External order acceptance", planningRunCreation: "Planning Run creation", productionMutation: "Production authority mutation", unknownStatus: "Unknown status",
    RecommendAccept: "Recommend accept", PlannerConfirmationRequired: "Planner confirmation required", CapacityAcceptableMaterialPending: "Capacity acceptable, material pending", MaterialEvidenceRequired: "Material evidence required",
    RecommendLaterPromise: "Recommend later promise", DoNotRecommendAccept: "Do not recommend acceptance", Feasible: "Material feasible", SkippedPendingConfirmation: "Material pending (check skipped)",
    EvidenceInsufficient: "Material evidence insufficient", Shortage: "Material shortage", OnTime: "On time", LaterSafeDate: "Later safe date", NotAssessable: "Not assessable",
    Fresh: "Fresh", Stale: "Stale", Future: "Future", Missing: "Missing", Protected: "Protected", Watch: "Watch", NearLimit: "Near limit", Overloaded: "Overloaded",
    ApprovedWithin: "Within approved threshold", ApprovedExceeded: "Approved threshold exceeded", Covered: "Covered", PlannedAllocationPrepared: "Planned allocation prepared", PendingConfirmation: "Pending confirmation",
    AwaitingPlannerDecision: "Awaiting planner decision", AcceptedPendingFormalSchedule: "Accepted, pending formal schedule", Rejected: "Rejected", Superseded: "Superseded by newer evaluation",
    NotReserved: "Not reserved", ActivePlanReservation: "Active plan reservation", LinkedToFormalOrder: "Linked to formal order", ConvertedToScheduledOccupancy: "Converted to scheduled occupancy",
    HeldForPlanningError: "Held for planning error", AdjustmentRequired: "Adjustment required", Released: "Released", Cancelled: "Cancelled", ReservationEvidenceMissing: "Reservation evidence missing",
    None: "No exception", AssessmentBlocked: "Assessment blocked", MaterialEvidenceBlocked: "Material evidence blocked", PlanningErrorPending: "Planning error pending",
    ReferenceFallback: "80% reference fallback; confirmation required", ApprovedOperatingModel: "Approved operating-model threshold", AcceptRequestedDate: "Accept requested date",
    ConditionallyAcceptRequestedDate: "Conditionally accept requested date", AcceptRecommendedDate: "Accept recommended date", ConditionallyAcceptRecommendedDate: "Conditionally accept recommended date",
    Reevaluate: "Re-evaluate", Reject: "Reject", OrderCommitmentEvaluated: "Commitment evaluated", OrderCommitmentReevaluated: "Commitment re-evaluated",
    OrderCommitmentEvaluationSuperseded: "Evaluation superseded", OrderCommitmentAccepted: "Commitment accepted", OrderCommitmentRejected: "Commitment rejected",
    LatestCurrent: "Latest current snapshot", Explicit: "Explicit snapshot", OnHand: "On hand", OnHandAndInbound: "On hand and inbound", NotPerformed: "Not performed"
  }
};

const ROUTES = {
  overview: ["pageOverview", "descriptionOverview"],
  "operational-metrics": ["pageOperationalMetrics", "descriptionOperationalMetrics"],
  "data-readiness": ["pageData", "descriptionData"],
  "material-planning": ["pageMaterials", "descriptionMaterials"],
  "order-commitments": ["pageOrderCommitments", "descriptionOrderCommitments"],
  "planning-runs": ["pageRuns", "descriptionRuns"],
  "schedule-results": ["pageResults", "descriptionResults"],
  "release-management": ["pageRelease", "descriptionRelease"],
  "buffer-board": ["pageBuffer", "descriptionBuffer"],
  "dispatch-suggestions": ["pageDispatch", "descriptionDispatch"],
  "public-demo": ["pagePublicDemo", "descriptionPublicDemo"],
  exceptions: ["pageExceptions", "descriptionExceptions"],
  calendar: ["pageCalendar", "descriptionCalendar"],
  administration: ["pageAdmin", "descriptionAdmin"]
};

let currentLanguage = "zh";
let caseAcceptanceData = null;
let operationalMetricsData = null;
let selectedOperationalMetricsRunID = null;
let dataReadiness = null;
let materialPlanningData = null;
let materialPlanningSortKey = "PriorityRank";
let selectedMaterialPlanningKey = null;
let orderCommitmentData = null;
let orderCommitmentRevision = null;
let selectedOrderCommitment = null;
let selectedOrderCommitmentAction = null;
let planningRunWorkbench = null;
let planningRunWizardStep = 1;
let scheduleResultData = null;
let scheduleResultRuns = [];
let selectedScheduleRunID = null;
let planPublicationData = null;
let scheduleOutputGovernanceData = null;
let scheduleOutputPackageData = null;
let sdbrWhatIfWorkspace = null;
let sdbrWhatIfResult = null;
let activeScheduleTab = "gantt";
let activeGanttMode = "resource";
let scheduledOrdersData = null;
let scheduledOrdersPage = 1;
let scheduledOrdersSort = { key: "PlannedStartAt", direction: "asc" };
let simioAdherencePage = 1;
let simioAdherenceSort = { key: "ActualStartTime", direction: "asc" };
let selectedScheduledOrderIDs = new Set();
let visibleScheduledOrderColumns = new Set(["OrderID", "ProductID", "PlannedReleaseAt", "PromiseDate", "OnTimeStatus", "ReleaseStatus", "ExecutionPriority", "RoutingID", "ResourceIDs"]);
let releaseManagementData = null;
let selectedReleaseRunID = null;
let releaseManagementUsesLatestOperationalState = false;
let bufferBoardData = null;
let dispatchPriorityData = null;
let mesDispatchIssueData = null;
let publicDemoData = null;
let selectedBufferRunID = null;
let selectedDispatchRunID = null;
let selectedBufferOrder = null;
let exceptionCenterData = null;
let calendarPreviewData = null;
let administrationData = null;
let baseCalendarsData = [];
let resourceCalendarAssignmentsData = [];
let calendarOverridesData = [];
let calendarResourcesData = [];

const TIME_BUFFER_MULTIPLIERS = {
  Low: { High: 0.75, Medium: 1.0, Low: 1.25 },
  Medium: { High: 1.0, Medium: 1.25, Low: 1.5 },
  High: { High: 1.5, Medium: 2.0, Low: 2.5 }
};

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
  document.querySelectorAll("[data-i18n-placeholder]").forEach((element) => {
    element.setAttribute("placeholder", translate(element.dataset.i18nPlaceholder));
  });
  document.getElementById("language-select").value = currentLanguage;
  renderRoute();
  refreshNavigationHelp();
  refreshDdmrpDetailsAction();
  renderMaterialPlanningTable();
  renderOperationalMetrics();
  if (selectedOrderCommitment) renderOrderCommitmentDetail();
  const decisionDialog = document.getElementById("order-commitment-decision-dialog");
  if (decisionDialog?.open && selectedOrderCommitmentAction) {
    setText(
      "order-commitment-decision-title",
      orderCommitmentLabel(selectedOrderCommitmentAction)
    );
    renderOrderCommitmentDecisionSummary(
      selectedOrderCommitment,
      selectedOrderCommitmentAction
    );
  }
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
  const isOperationalMetrics = route === "operational-metrics";
  const isDataReadiness = route === "data-readiness";
  const isMaterialPlanning = route === "material-planning";
  const isOrderCommitments = route === "order-commitments";
  const isOverview = route === "overview";
  const isPlanningRuns = route === "planning-runs";
  const isScheduleResults = route === "schedule-results";
  const isReleaseManagement = route === "release-management";
  const isBufferBoard = route === "buffer-board";
  const isDispatchSuggestions = route === "dispatch-suggestions";
  const isPublicDemo = route === "public-demo";
  const isExceptions = route === "exceptions";
  const isCalendar = route === "calendar";
  const isAdministration = route === "administration";
  document.getElementById("generic-workspace").hidden = isOverview || isOperationalMetrics || isDataReadiness || isMaterialPlanning || isOrderCommitments || isPlanningRuns || isScheduleResults || isReleaseManagement || isBufferBoard || isDispatchSuggestions || isPublicDemo || isExceptions || isCalendar || isAdministration;
  document.getElementById("overview-view").hidden = !isOverview;
  document.getElementById("operational-metrics-view").hidden = !isOperationalMetrics;
  document.getElementById("data-readiness-view").hidden = !isDataReadiness;
  document.getElementById("material-planning-view").hidden = !isMaterialPlanning;
  document.getElementById("order-commitments-view").hidden = !isOrderCommitments;
  document.getElementById("planning-runs-view").hidden = !isPlanningRuns;
  document.getElementById("schedule-results-view").hidden = !isScheduleResults;
  document.getElementById("release-management-view").hidden = !isReleaseManagement;
  document.getElementById("buffer-board-view").hidden = !isBufferBoard;
  document.getElementById("dispatch-suggestions-view").hidden = !isDispatchSuggestions;
  document.getElementById("public-demo-view").hidden = !isPublicDemo;
  document.getElementById("exceptions-view").hidden = !isExceptions;
  document.getElementById("calendar-view").hidden = !isCalendar;
  document.getElementById("administration-view").hidden = !isAdministration;
  if (isOverview) loadCaseAcceptance();
  if (isOperationalMetrics) loadOperationalMetricsRuns();
  if (isDataReadiness) loadDataReadiness();
  if (isMaterialPlanning) loadMaterialPlanning();
  if (isOrderCommitments) loadOrderCommitments();
  if (isPlanningRuns) loadPlanningRuns();
  if (isScheduleResults) loadScheduleResultRuns();
  if (isReleaseManagement) loadReleaseManagementRuns();
  if (isBufferBoard) loadBufferBoardRuns();
  if (isDispatchSuggestions) loadDispatchSuggestionRuns();
  if (isPublicDemo) loadPublicDemoGoldenLoop();
  if (isExceptions) loadExceptionCenter();
  if (isCalendar) loadCalendarWorkspace();
  if (isAdministration) loadAdministration();
  closeMobileNavigation();
  if (focusWorkspace) {
    document.getElementById("workspace").focus({ preventScroll: true });
  }
}

function navigationHelpContent(route) {
  const routeConfig = ROUTES[route];
  if (!routeConfig) return null;
  const [titleKey, descriptionKey] = routeConfig;
  return {
    title: translate(titleKey),
    description: translate(descriptionKey)
  };
}

function positionNavigationHelp(link) {
  const tooltip = document.getElementById("nav-business-tooltip");
  if (!tooltip || tooltip.hidden) return;
  const navigation = document.getElementById("primary-navigation");
  const navRect = navigation.getBoundingClientRect();
  const linkRect = link.getBoundingClientRect();
  const spacing = 12;
  const viewportPadding = 12;
  const maxLeft = Math.max(viewportPadding, window.innerWidth - tooltip.offsetWidth - viewportPadding);
  const left = Math.min(navRect.right + spacing, maxLeft);
  const top = Math.min(
    Math.max(viewportPadding, linkRect.top + (linkRect.height / 2) - (tooltip.offsetHeight / 2)),
    Math.max(viewportPadding, window.innerHeight - tooltip.offsetHeight - viewportPadding)
  );
  tooltip.style.left = `${left}px`;
  tooltip.style.top = `${top}px`;
}

function showNavigationHelp(link) {
  if (isNarrowScreen()) return;
  const content = navigationHelpContent(link.dataset.route);
  if (!content) return;
  const tooltip = document.getElementById("nav-business-tooltip");
  document.getElementById("nav-business-tooltip-title").textContent = content.title;
  document.getElementById("nav-business-tooltip-description").textContent = content.description;
  tooltip.dataset.route = link.dataset.route;
  tooltip.hidden = false;
  tooltip.setAttribute("aria-hidden", "false");
  document.querySelectorAll("[data-nav-help]").forEach((item) => item.removeAttribute("aria-describedby"));
  link.setAttribute("aria-describedby", "nav-business-tooltip");
  window.requestAnimationFrame(() => positionNavigationHelp(link));
}

function hideNavigationHelp() {
  const tooltip = document.getElementById("nav-business-tooltip");
  if (!tooltip) return;
  tooltip.hidden = true;
  tooltip.setAttribute("aria-hidden", "true");
  tooltip.removeAttribute("data-route");
  document.querySelectorAll("[data-nav-help]").forEach((item) => item.removeAttribute("aria-describedby"));
}

function refreshNavigationHelp() {
  const tooltip = document.getElementById("nav-business-tooltip");
  if (!tooltip || tooltip.hidden) return;
  const route = tooltip.dataset.route;
  const link = document.querySelector(`[data-nav-help][data-route="${route}"]`);
  if (!link) {
    hideNavigationHelp();
    return;
  }
  showNavigationHelp(link);
}

function setText(id, value) {
  document.getElementById(id).textContent = value ?? "-";
}

function displayValue(value) {
  return value === null || value === undefined || value === "" ? translate("notProvided") : String(value);
}

function businessValue(value) {
  if (typeof value === "boolean") return translate(value ? "yes" : "no");
  if (["Pending", "Queued", "Running", "Completed", "Failed", "DeadLetter", "Cancelled"].includes(String(value))) {
    return statusLabel(String(value));
  }
  if (value === "Test planning run is awaiting execution.") {
    return currentLanguage === "zh" ? "排程任务正在等待执行。" : value;
  }
  const translated = translate(`reason_${value}`);
  if (!String(translated).startsWith("reason_")) return translated;
  const action = translate(`action_${value}`);
  if (!String(action).startsWith("action_")) return action;
  return simioBusinessStatusLabel(value);
}

function businessBoolean(key, value) {
  if (key === "requiresReschedule") return translate(value ? "needReschedule" : "noNeedReschedule");
  return businessValue(value);
}

function externalDeliveryReason(value) {
  return value === "External ERP/MES delivery is owned by BE-INT-* integrations."
    ? translate("externalDeliveryOwnedByIntegrations")
    : displayValue(value);
}

function simioSourceLabel(value) {
  const key = {
    ParsedFromSDBROutputRows: "simioSourceParsedFromSDBROutputRows",
    ParsedFromPostRunLogs: "simioSourceParsedFromPostRunLogs",
    ParsedFromInteractiveStatistics: "simioSourceParsedFromInteractiveStatistics",
    Parsed: "simioSourceParsed",
    PartialResultParsed: "simioSourcePartialResultParsed",
    Unavailable: "simioSourceUnavailable"
  }[value];
  return key ? translate(key) : simioBusinessStatusLabel(value);
}

function simioEventStatusLabel(value) {
  const translated = translate(`simioEvent_${value}`);
  return !String(translated).startsWith("simioEvent_") ? translated : businessValue(value);
}

function simioIssueBusinessLabel(issue) {
  const translated = translate(`simioIssue_${issue?.Code}`);
  if (!String(translated).startsWith("simioIssue_")) return translated;
  return businessValue(issue?.Message || issue?.Code || "simioIssues");
}

function simioIssueSeverityClass(issue) {
  return issue?.Severity === "Error" ? " is-error" : "";
}

function simioDataSourceLabel(value) {
  if (value === "Results/Model/Interactive_Results.stats") {
    return currentLanguage === "zh" ? "完整统计文件" : "Full statistics file";
  }
  return simioSourceLabel(value);
}

function compactFingerprint(value) {
  return value ? `${String(value).slice(0, 16)}...` : "-";
}

function formatNumber(value, maximumFractionDigits = 2) {
  if (value === null || value === undefined || value === "") return "-";
  const number = Number(value);
  if (!Number.isFinite(number)) return String(value);
  return new Intl.NumberFormat(currentLanguage === "zh" ? "zh-CN" : "en-US", {
    maximumFractionDigits
  }).format(number);
}

function toNumericValue(value) {
  if (value === null || value === undefined || value === "") return null;
  const number = Number(value);
  return Number.isFinite(number) ? number : null;
}

function minutesBetween(startValue, endValue) {
  if (!startValue || !endValue) return null;
  const start = new Date(startValue).getTime();
  const end = new Date(endValue).getTime();
  if (!Number.isFinite(start) || !Number.isFinite(end)) return null;
  return Math.max(0, Math.round((end - start) / 60000));
}

function simioAdherenceDuration(row) {
  return minutesBetween(row?.ActualStartTime, row?.ActualEndTime);
}

function simioUtilizationRiskClass(value) {
  const percent = toNumericValue(value);
  if (percent === null) return "";
  if (percent >= 100) return "utilization-risk-full";
  if (percent > 90) return "utilization-risk-critical";
  if (percent > 80) return "utilization-risk-warning";
  return "";
}

function formatSimioThroughput(throughput) {
  if (!throughput) return null;
  const completed = formatNumber(throughput.CompletedOrderCount);
  const planned = formatNumber(throughput.PlannedOrderCount);
  const unfinished = formatNumber(throughput.UnfinishedOrderCount);
  const created = throughput.SimioEntityCreated === undefined ? null : formatNumber(throughput.SimioEntityCreated);
  const destroyed = throughput.SimioEntityDestroyed === undefined ? null : formatNumber(throughput.SimioEntityDestroyed);
  const parts = [
    currentLanguage === "zh" ? `完成 ${completed} / 计划 ${planned}` : `Completed ${completed} / planned ${planned}`,
    currentLanguage === "zh" ? `未完成 ${unfinished}` : `unfinished ${unfinished}`
  ];
  if (created !== null || destroyed !== null) {
    parts.push(currentLanguage === "zh" ? `实体 ${created ?? "-"} / 销毁 ${destroyed ?? "-"}` : `entities ${created ?? "-"} / destroyed ${destroyed ?? "-"}`);
  }
  return parts.join(" · ");
}

function formatSimioWip(metrics) {
  if (!metrics) return null;
  const avg = formatNumber(metrics.SystemAverageWip);
  const max = formatNumber(metrics.SystemMaxWip);
  return currentLanguage === "zh"
    ? `${simioSourceLabel(metrics.Status)}，平均 ${avg}，最大 ${max}`
    : `${simioSourceLabel(metrics.Status)}, avg ${avg}, max ${max}`;
}

function formatSimioQueue(metrics) {
  if (!metrics) return null;
  const first = (metrics.Resources || [])[0] || {};
  if (first.AverageWaitMinutes !== undefined || first.MaxWaitMinutes !== undefined) {
    return currentLanguage === "zh"
      ? `${simioSourceLabel(metrics.Status)}，平均/最大等待 ${formatNumber(first.AverageWaitMinutes)}/${formatNumber(first.MaxWaitMinutes)} 分钟`
      : `${simioSourceLabel(metrics.Status)}, avg/max wait ${formatNumber(first.AverageWaitMinutes)}/${formatNumber(first.MaxWaitMinutes)} min`;
  }
  return currentLanguage === "zh"
    ? `${simioSourceLabel(metrics.Status)}，平均/最大队列 ${formatNumber(first.AverageStationContent)}/${formatNumber(first.MaxStationContent)}`
    : `${simioSourceLabel(metrics.Status)}, avg/max queue ${formatNumber(first.AverageStationContent)}/${formatNumber(first.MaxStationContent)}`;
}

function formatSimioUtilization(metrics) {
  if (!metrics) return null;
  const resources = metrics.Resources || [];
  const busyRows = resources.filter((item) => Number(item.BusyMinutes || 0) > 0).length;
  const total = resources.length;
  return currentLanguage === "zh"
    ? `${simioSourceLabel(metrics.Status)}，${busyRows}/${total} 个资源有加工记录`
    : `${simioSourceLabel(metrics.Status)}, ${busyRows}/${total} resources have processing records`;
}

function formatDate(value) {
  if (!value) return "-";
  return new Intl.DateTimeFormat(currentLanguage === "zh" ? "zh-CN" : "en-US", {
    dateStyle: "medium", timeStyle: "short"
  }).format(new Date(value));
}

function operationalMetricStatusLabel(status) {
  return translate({
    Green: "metricStatusGreen",
    Yellow: "metricStatusYellow",
    Red: "metricStatusRed",
    Unavailable: "metricStatusUnavailable"
  }[status] || "metricStatusUnavailable");
}

function operationalMetricStatusClass(status) {
  return {
    Green: "is-green",
    Yellow: "is-yellow",
    Red: "is-red",
    Unavailable: "is-unavailable"
  }[status] || "is-unavailable";
}

function dataCoverageLabel(value) {
  return translate(`coverage_${value || "Available"}`);
}

function operationalApplicabilityLabel(value) {
  const zh = {
    "DDOM daily operations": "DDOM 日常运营执行",
    "Release gating and buffer execution": "释放门控与缓冲执行",
    "MES dispatch suggestion review": "MES 派工建议复核",
    "Execution variance feedback to DDS&OP": "给 DDS&OP 的执行偏差反馈",
    "Financial cost attribution": "财务成本归因",
    "DDS&OP model configuration or scenario governance": "DDS&OP 模型配置或情景治理",
    "MES second-by-second machine control": "MES 秒级设备控制",
    "Long-term capacity investment decisions": "长期产能投资决策"
  };
  const en = {
    "DDOM daily operations": "DDOM daily operations",
    "Release gating and buffer execution": "Release gating and buffer execution",
    "MES dispatch suggestion review": "MES dispatch suggestion review",
    "Execution variance feedback to DDS&OP": "Execution variance feedback to DDS&OP",
    "Financial cost attribution": "Financial cost attribution",
    "DDS&OP model configuration or scenario governance": "DDS&OP model configuration or scenario governance",
    "MES second-by-second machine control": "MES second-by-second machine control",
    "Long-term capacity investment decisions": "Long-term capacity investment decisions"
  };
  return (currentLanguage === "zh" ? zh : en)[value] || value || "-";
}

function metricDisplayValue(metric) {
  if (metric.Value === null || metric.Value === undefined) return "-";
  if (metric.Unit === "Percent") return `${formatNumber(metric.Value)}%`;
  if (metric.Unit === "Minutes") return `${formatNumber(metric.Value)}m`;
  return formatNumber(metric.Value);
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
    const passedAssertions = (actual.ScheduleAssertions || [])
      .filter((item) => item.Passed)
      .map((item) => item.AssertionID);
    [
      ["caseGroup", translate(caseItem.CaseGroup) || displayValue(caseItem.CaseGroup)],
      ["caseType", caseItem.CaseType],
      ["planningRun", caseItem.PlanningRunID],
      ["status", statusLabel(actual.PlanningRunStatus)],
      ["solver", `${displayValue(actual.SolverBackendID)} / ${displayValue(actual.SolverStatus)}`],
      ["publicationStatus", publicationStatusLabel(actual.PublicationStatus)],
      ["releaseReadyCount", releaseSummary.ReadyCount ?? "-"],
      ["blockingCodes", (release.BlockingCodes || []).join(", ") || translate("clear")],
      ["expectedAssertions", (caseItem.ExpectedScheduleAssertions || []).join(", ") || translate("notAvailable")],
      ["passedAssertions", passedAssertions.join(", ") || translate("notAvailable")],
      ["failureReasons", (caseItem.FailureReasons || []).join(", ") || translate("clear")]
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
    const openable = caseItem.ScheduleResultOpenable === true;
    open.textContent = openable ? translate("openScheduleResult") : translate("scheduleNotCompleted");
    open.disabled = !openable;
    if (open.disabled) open.title = translate(caseItem.ScheduleResultUnavailableReason) || translate("executeCaseFirst");
    open.addEventListener("click", () => {
      selectedScheduleRunID = caseItem.PlanningRunID;
      window.location.hash = "schedule-results";
    });
    const reset = document.createElement("button");
    reset.type = "button";
    reset.className = "button secondary";
    reset.textContent = translate("resetCase");
    reset.addEventListener("click", () => resetAcceptanceCase(caseItem.CaseID));
    actions.append(open, reset);
    card.append(heading, purpose, meta, actions);
    container.append(card);
  });
}

async function resetAcceptanceCase(caseId) {
  const response = await fetch(`/planner/workbench/test-data/acceptance/${encodeURIComponent(caseId)}/reset`, { method: "POST" });
  if (!response.ok) {
    showNotification(translate("caseResetFailed"), "error");
    return;
  }
  showNotification(translate("caseResetCompleted"), "success");
  await loadCaseAcceptance();
}

async function resetAllAcceptanceCases() {
  const response = await fetch("/planner/workbench/test-data/acceptance/reset", { method: "POST" });
  if (!response.ok) {
    showNotification(translate("caseResetFailed"), "error");
    return;
  }
  showNotification(translate("caseResetCompleted"), "success");
  await loadCaseAcceptance();
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
  document.getElementById("generate-operational-snapshot").disabled = !snapshot?.SnapshotID;
  document.getElementById("readiness-error").hidden = true;
}

function ddmrpZoneLabel(value) {
  const translated = translate(`zone_${value}`);
  return String(translated).startsWith("zone_") ? displayValue(value) : translated;
}

function ddmrpActionLabel(value) {
  const translated = translate(`action_${value}`);
  return String(translated).startsWith("action_") ? displayValue(value) : translated;
}

function renderDdmrpStatus(payload) {
  const summary = payload?.Summary || {};
  document.querySelectorAll("#ddmrp-status-summary [data-ddmrp-summary]").forEach((element) => {
    const value = summary[element.dataset.ddmrpSummary];
    element.textContent = value === null || value === undefined ? "-" : String(value);
  });
  const missingCount = Number(summary.MissingDataCount || 0);
  const lineCount = Number(summary.LineCount || 0);
  setStatusChip(
    document.getElementById("ddmrp-status-chip"),
    lineCount ? translate(missingCount ? "ddmrpMissingData" : "ddmrpReady") : translate("notAvailable"),
    lineCount ? (missingCount ? "is-warning" : "is-valid") : "neutral"
  );
  const body = document.getElementById("ddmrp-status-table-body");
  body.replaceChildren();
  (payload?.Lines || []).forEach((line) => {
    const row = document.createElement("tr");
    [
      line.ItemID,
      line.LocationID,
      formatNumber(line.OnHandQty),
      formatNumber(line.NetFlowPosition),
      ddmrpZoneLabel(line.PlanningStatus),
      ddmrpZoneLabel(line.ExecutionStatus),
      formatNumber(line.SuggestedReplenishmentQty),
      ddmrpActionLabel(line.RecommendedAction)
    ].forEach((value) => {
      const cell = document.createElement("td");
      cell.textContent = value;
      row.append(cell);
    });
    body.append(row);
  });
  if (!body.children.length) {
    const row = document.createElement("tr");
    const cell = document.createElement("td");
    cell.colSpan = 8;
    cell.textContent = translate("ddmrpNoData");
    row.append(cell);
    body.append(row);
  }
  const source = payload?.Source?.VersionID ? `${translate("version")}: ${payload.Source.VersionID}` : "";
  setText("ddmrp-status-message", source);
}

function ddmrpZoneRank(value) {
  return { Red: 1, Yellow: 2, Green: 3, AboveGreen: 4 }[value] || 9;
}

function ddmrpPriorityLabel(value) {
  return {
    Red: translate("criticalPriority"),
    Yellow: translate("attentionPriority"),
    Green: translate("normalPriority"),
    AboveGreen: translate("aboveGreenZone")
  }[value] || displayValue(value);
}

function ddmrpZoneClass(value) {
  return {
    Red: "is-red",
    Yellow: "is-yellow",
    Green: "is-green",
    AboveGreen: "is-above-green"
  }[value] || "";
}

function materialPlanningRows() {
  return (materialPlanningData?.Lines || []).map((line) => {
    const topOfGreen = Number(line.TopOfGreen || 0);
    const netFlow = Number(line.NetFlowPosition || 0);
    const bufferPercent = topOfGreen > 0 ? (netFlow / topOfGreen) * 100 : null;
    return {
      ...line,
      BufferPercent: bufferPercent,
      BufferPercentText: bufferPercent === null ? "-" : `${formatNumber(bufferPercent)}%`,
      PriorityRank: ddmrpZoneRank(line.PlanningStatus),
      RowKey: `${line.ItemID}@@${line.LocationID}`
    };
  });
}

function filteredMaterialPlanningRows() {
  const query = document.getElementById("material-planning-search")?.value.trim().toLowerCase() || "";
  const zone = document.getElementById("material-planning-zone-filter")?.value || "All";
  const rows = materialPlanningRows().filter((row) => {
    const matchesQuery = !query || `${row.ItemID} ${row.LocationID}`.toLowerCase().includes(query);
    const matchesZone = zone === "All" || row.PlanningStatus === zone;
    return matchesQuery && matchesZone;
  });
  rows.sort((left, right) => {
    const key = materialPlanningSortKey;
    const leftValue = Number(left[key]);
    const rightValue = Number(right[key]);
    if (Number.isFinite(leftValue) && Number.isFinite(rightValue) && leftValue !== rightValue) {
      return leftValue - rightValue;
    }
    if (left.PriorityRank !== right.PriorityRank) return left.PriorityRank - right.PriorityRank;
    const leftPercent = Number(left.BufferPercent);
    const rightPercent = Number(right.BufferPercent);
    if (Number.isFinite(leftPercent) && Number.isFinite(rightPercent) && leftPercent !== rightPercent) {
      return leftPercent - rightPercent;
    }
    return String(left.ItemID).localeCompare(String(right.ItemID));
  });
  if (materialPlanningSortKey === "SuggestedReplenishmentQty") rows.reverse();
  return rows;
}

function renderMaterialPlanningSummary(summary = {}) {
  document.querySelectorAll("[data-material-summary]").forEach((element) => {
    const value = summary[element.dataset.materialSummary];
    element.textContent = value === null || value === undefined ? "-" : String(value);
  });
}

function renderMaterialPlanningTable() {
  const body = document.getElementById("material-planning-table-body");
  if (!body) return;
  const rows = filteredMaterialPlanningRows();
  body.replaceChildren();
  rows.forEach((rowData) => {
    const row = document.createElement("tr");
    const itemButton = document.createElement("button");
    itemButton.type = "button";
    itemButton.className = "run-link";
    itemButton.textContent = rowData.ItemID;
    itemButton.addEventListener("click", () => selectMaterialPlanningRow(rowData.RowKey));

    const priority = document.createElement("span");
    priority.className = `material-priority ${ddmrpZoneClass(rowData.PlanningStatus)}`;
    priority.textContent = ddmrpPriorityLabel(rowData.PlanningStatus);

    const action = document.createElement("span");
    action.className = `material-action ${rowData.RecommendedAction === "Replenish" ? "is-replenish" : ""}`;
    action.textContent = ddmrpActionLabel(rowData.RecommendedAction);

    [
      nodeCell(itemButton),
      textCell(rowData.LocationID),
      nodeCell(priority),
      textCell(ddmrpZoneLabel(rowData.PlanningStatus)),
      textCell(rowData.BufferPercentText),
      textCell(formatNumber(rowData.OnHandQty)),
      textCell(formatNumber(rowData.QualifiedOpenSupplyQty)),
      textCell(formatNumber(rowData.QualifiedDemandQty)),
      textCell(formatNumber(rowData.NetFlowPosition)),
      textCell(formatNumber(rowData.SuggestedReplenishmentQty)),
      nodeCell(action)
    ].forEach((cell) => row.append(cell));
    body.append(row);
  });
  document.getElementById("material-planning-empty").hidden = rows.length !== 0;
  if (selectedMaterialPlanningKey && !materialPlanningRows().some((row) => row.RowKey === selectedMaterialPlanningKey)) {
    selectedMaterialPlanningKey = null;
  }
  renderMaterialPlanningDetail();
}

function renderMaterialPlanningDetail() {
  const rows = materialPlanningRows();
  const selected = rows.find((row) => row.RowKey === selectedMaterialPlanningKey);
  document.getElementById("material-detail-empty").hidden = Boolean(selected);
  document.getElementById("material-detail-content").hidden = !selected;
  setText("material-detail-heading", selected ? `${selected.ItemID} · ${selected.LocationID}` : translate("selectMaterialForDetails"));
  setStatusChip(
    document.getElementById("material-detail-status"),
    selected ? ddmrpPriorityLabel(selected.PlanningStatus) : translate("notSelected"),
    selected ? (selected.PlanningStatus === "Red" ? "is-invalid" : selected.PlanningStatus === "Yellow" ? "is-warning" : "is-valid") : "neutral"
  );
  if (!selected) return;
  document.querySelectorAll("[data-material-detail]").forEach((element) => {
    const key = element.dataset.materialDetail;
    element.textContent = key === "BufferPercentText" ? selected.BufferPercentText : formatNumber(selected[key]);
  });
  const demandCount = selected.DemandComponents?.length || 0;
  const supplyCount = selected.SupplyComponents?.length || 0;
  setText(
    "material-detail-components",
    `${translateWith("demandComponentsCount", { count: demandCount })} · ${translateWith("supplyComponentsCount", { count: supplyCount })}`
  );
}

function selectMaterialPlanningRow(rowKey) {
  selectedMaterialPlanningKey = rowKey;
  renderMaterialPlanningDetail();
  document.getElementById("material-planning-detail").scrollIntoView({ block: "nearest", behavior: "smooth" });
}

function renderMaterialPlanning(payload) {
  materialPlanningData = payload || null;
  renderMaterialPlanningSummary(payload?.Summary || {});
  const source = payload?.Source?.VersionID ? `${translate("version")}: ${payload.Source.VersionID}` : "";
  setText("material-planning-source", source);
  document.getElementById("material-planning-error").hidden = true;
  renderMaterialPlanningTable();
}

async function loadMaterialPlanning() {
  try {
    const response = await fetch("/planner/workbench/ddmrp/status", { headers: { Accept: "application/json" } });
    if (!response.ok) throw new Error(String(response.status));
    renderMaterialPlanning((await response.json()).Data);
  } catch (_error) {
    materialPlanningData = null;
    renderMaterialPlanningSummary({});
    setText("material-planning-source", "");
    document.getElementById("material-planning-table-body").replaceChildren();
    document.getElementById("material-planning-empty").hidden = false;
    document.getElementById("material-planning-error").hidden = false;
    selectedMaterialPlanningKey = null;
    renderMaterialPlanningDetail();
  }
}

function refreshDdmrpDetailsAction() {
  const details = document.getElementById("ddmrp-details");
  const action = document.querySelector("[data-ddmrp-details-action]");
  if (!details || !action) return;
  action.textContent = translate(details.open ? "hideDetails" : "showDetails");
}

async function loadDdmrpStatus() {
  try {
    const response = await fetch("/planner/workbench/ddmrp/status", { headers: { Accept: "application/json" } });
    if (!response.ok) throw new Error(String(response.status));
    renderDdmrpStatus((await response.json()).Data);
  } catch (_error) {
    renderDdmrpStatus(null);
  }
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
    await loadDdmrpStatus();
  } catch (_error) {
    banner.className = "readiness-banner is-blocked";
    document.getElementById("generate-operational-snapshot").disabled = true;
    document.getElementById("readiness-error").hidden = false;
  }
}

async function generateOperationalSnapshotFromLatest() {
  const sourceSnapshotID = dataReadiness?.LatestOperationalStateSnapshot?.SnapshotID;
  if (!sourceSnapshotID) {
    showNotification(translate("operationalSnapshotMissing"), "error");
    return;
  }
  const button = document.getElementById("generate-operational-snapshot");
  button.disabled = true;
  try {
    const sourceResponse = await fetch(`/planner/workbench/operational-state/snapshots/${encodeURIComponent(sourceSnapshotID)}`, { headers: { Accept: "application/json" } });
    if (!sourceResponse.ok) throw new Error(String(sourceResponse.status));
    const source = (await sourceResponse.json()).Data.Snapshot || {};
    const now = new Date();
    const snapshotID = `OPS-MOCK-${now.toISOString().replace(/\D/g, "").slice(0, 14)}`;
    const createResponse = await fetch("/planner/workbench/operational-state/snapshots", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        SnapshotID: snapshotID,
        CapturedAt: now.toISOString(),
        InventoryBuffers: source.InventoryBuffers || [],
        MaterialAvailability: source.MaterialAvailability || [],
        WipLimits: source.WipLimits || []
      })
    });
    if (!createResponse.ok) throw new Error(String(createResponse.status));
    showNotification(translate("operationalSnapshotGenerated"), "success");
    await loadDataReadiness();
  } catch (_error) {
    showNotification(translate("operationalSnapshotGenerateFailed"), "error");
  } finally {
    button.disabled = !dataReadiness?.LatestOperationalStateSnapshot?.SnapshotID;
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
    Enqueue: "enqueue", Execute: "execute", ProcessQueue: "processQueue", Cancel: "cancel", Recover: "recover", OpenResults: "openResults"
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

function selectedOptionText(inputId) {
  const element = document.getElementById(inputId);
  return element?.selectedOptions?.[0]?.textContent || element?.value || "-";
}

function timeBufferRecommendation() {
  const olt = Math.max(0, Number(document.getElementById("wizard-olt-minutes").value || 0));
  const variability = document.getElementById("wizard-variability-profile").value;
  const flex = document.getElementById("wizard-capacity-flex-profile").value;
  const multiplier = TIME_BUFFER_MULTIPLIERS[variability]?.[flex] ?? 1.25;
  return { multiplier, minutes: Math.round(olt * multiplier) };
}

function renderTimeBufferRecommendation() {
  const { multiplier, minutes } = timeBufferRecommendation();
  document.getElementById("wizard-time-buffer-multiplier").value = `${formatNumber(multiplier)}×`;
  document.getElementById("wizard-time-buffer-recommendation").textContent = currentLanguage === "zh"
    ? `${formatNumber(minutes)} 分钟`
    : `${formatNumber(minutes)} min`;
}

function applyTimeBufferRecommendation() {
  document.getElementById("wizard-time-buffer").value = timeBufferRecommendation().minutes;
  showNotification(translate("timeBufferRecommendationApplied"), "success");
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
  document.getElementById("wizard-olt-minutes").value = document.getElementById("wizard-time-buffer").value || "120";
  renderTimeBufferRecommendation();
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
    ["operatingLeadTime", "wizard-olt-minutes"], ["variabilityProfile", "wizard-variability-profile"],
    ["capacityFlexProfile", "wizard-capacity-flex-profile"], ["timeBufferMultiplier", "wizard-time-buffer-multiplier"],
    ["timeBuffer", "wizard-time-buffer"], ["timeLimit", "wizard-time-limit"], ["maxAttempts", "wizard-max-attempts"],
    ["retryDelay", "wizard-retry-delay"]
  ].forEach(([labelKey, inputId]) => {
    const row = document.createElement("div");
    row.className = "review-row";
    const label = document.createElement("span");
    label.textContent = translate(labelKey);
    const value = document.createElement("strong");
    const input = document.getElementById(inputId);
    value.textContent = input?.tagName === "SELECT" ? selectedOptionText(inputId) : (input?.value || "-");
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
  content.append(listSection("diagnostics", detail.Diagnostics, (item) => `${businessValue(item.Code)}：${businessValue(item.Message)}`));
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

function collapsibleDetailSection(titleKey, rows, { open = false } = {}) {
  const details = document.createElement("details");
  details.className = "collapsible-detail";
  details.open = open;
  const summary = document.createElement("summary");
  const title = document.createElement("span");
  title.textContent = translate(titleKey);
  const action = document.createElement("small");
  action.className = "collapsible-action";
  action.textContent = translate(open ? "hideDetails" : "showDetails");
  summary.append(title, action);
  const content = detailSection(titleKey, rows);
  content.querySelector("h3")?.remove();
  details.append(summary, content);
  details.addEventListener("toggle", () => {
    action.textContent = translate(details.open ? "hideDetails" : "showDetails");
  });
  return details;
}

function businessDecisionCard(titleKey, value, detailRows = [], { tone = "neutral" } = {}) {
  const card = document.createElement("article");
  card.className = `business-decision-card tone-${tone}`;
  const title = document.createElement("span");
  title.textContent = translate(titleKey);
  const strong = document.createElement("strong");
  strong.textContent = value ?? "-";
  card.append(title, strong);
  if (detailRows.length) {
    card.append(collapsibleDetailSection("technicalDetails", detailRows));
  }
  return card;
}

function detailRowsFromObject(source) {
  return Object.entries(source || {})
    .filter(([, value]) => value !== undefined && value !== null && value !== "")
    .map(([key, value]) => [lowerFirst(key), detailDisplayValue(value, lowerFirst(key))]);
}

function detailDisplayValue(value, key = "") {
  if (Array.isArray(value)) return `${value.length} · ${translate("riskCount")}`;
  if (typeof value === "boolean") return businessBoolean(key, value);
  if (typeof value === "object" && value !== null) {
    return Object.entries(value)
      .filter(([, nested]) => nested !== undefined && nested !== null && nested !== "")
      .map(([nestedKey, nested]) => `${translate(lowerFirst(nestedKey))}: ${detailDisplayValue(nested, lowerFirst(nestedKey))}`)
      .join(" · ");
  }
  return businessValue(value);
}

function lowerFirst(value) {
  return String(value).replace(/^[A-Z]/, (letter) => letter.toLowerCase());
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
  } else if (action === "ProcessQueue") {
    if (!(await confirmAction({ message: translate("confirmProcessQueue"), context: `${translate("runId")}: ${run.RunID}` }))) return;
    endpoint = `/planner/workbench/planning-runs/${encodeURIComponent(run.RunID)}/process-queued`;
    payload = { WorkerID: "interactive-worker", ProcessedAt: now, TimeLimitSeconds: run.TimeLimitSeconds || 300 };
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
  showNotification(translate(action === "ProcessQueue" ? "queueProcessed" : "notifySuccess"), "success");
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

async function loadOperationalMetricsRuns() {
  try {
    const response = await fetch("/planner/workbench/planning-runs/workbench", { headers: { Accept: "application/json" } });
    if (!response.ok) throw new Error(String(response.status));
    const workbench = (await response.json()).Data;
    const runs = workbench.Rows.filter((run) => run.Status === "Completed");
    const select = document.getElementById("operational-metrics-run-select");
    replaceSelectOptions(select, runs, { valueKey: "RunID", labelKey: "RunID" });
    if (!runs.length) throw new Error("No completed planning runs");
    const preferred = selectedOperationalMetricsRunID || selectedDispatchRunID || selectedBufferRunID || selectedReleaseRunID || selectedScheduleRunID;
    selectedOperationalMetricsRunID = runs.some((run) => run.RunID === preferred) ? preferred : runs[0].RunID;
    select.value = selectedOperationalMetricsRunID;
    if (!document.getElementById("operational-metrics-evaluated-at").value) {
      document.getElementById("operational-metrics-evaluated-at").value = toLocalDateTimeInput(new Date());
    }
    await loadOperationalMetrics();
  } catch (_error) {
    document.getElementById("operational-metrics-error").hidden = false;
    document.getElementById("operational-metrics-content").hidden = true;
  }
}

async function loadOperationalMetrics() {
  const runId = document.getElementById("operational-metrics-run-select").value;
  if (!runId) return;
  selectedOperationalMetricsRunID = runId;
  const evaluatedAt = document.getElementById("operational-metrics-evaluated-at").value;
  const query = new URLSearchParams({
    run_id: runId,
    evaluated_at: new Date(evaluatedAt || Date.now()).toISOString(),
    use_latest_operational_state: "true"
  });
  try {
    const response = await fetch(`/planner/workbench/ddom/operational-metrics?${query}`, { headers: { Accept: "application/json" } });
    if (!response.ok) throw new Error(String(response.status));
    operationalMetricsData = (await response.json()).Data;
    renderOperationalMetrics();
    document.getElementById("operational-metrics-error").hidden = true;
    document.getElementById("operational-metrics-content").hidden = false;
  } catch (_error) {
    document.getElementById("operational-metrics-error").hidden = false;
    document.getElementById("operational-metrics-content").hidden = true;
  }
}

function renderOperationalMetrics() {
  if (!operationalMetricsData) return;
  setText("operational-metrics-status", operationalMetricStatusLabel(operationalMetricsData.OverallStatus));
  document.getElementById("operational-metrics-status").className = `metric-status-text ${operationalMetricStatusClass(operationalMetricsData.OverallStatus)}`;
  setText("operational-metrics-score", operationalMetricsData.OverallScore === null || operationalMetricsData.OverallScore === undefined ? "-" : formatNumber(operationalMetricsData.OverallScore));
  const applies = (operationalMetricsData.Applicability?.AppliesTo || []).map(operationalApplicabilityLabel).join(" · ");
  const notApplies = (operationalMetricsData.Applicability?.DoesNotApplyTo || []).map(operationalApplicabilityLabel).join(" · ");
  setText("operational-metrics-scope", `${translate("metricAppliesTo")}: ${applies || "-"} / ${translate("metricDoesNotApplyTo")}: ${notApplies || "-"}`);
  const categories = document.getElementById("operational-metrics-categories");
  categories.replaceChildren();
  (operationalMetricsData.Categories || []).forEach((category) => {
    const card = document.createElement("section");
    card.className = `operational-category-card ${operationalMetricStatusClass(category.Status)}`;
    const heading = document.createElement("div");
    heading.className = "operational-category-heading";
    const title = document.createElement("h2");
    title.textContent = category.NameZh || category.NameEn || category.CategoryID;
    const chip = document.createElement("span");
    chip.className = `status-chip ${operationalMetricStatusClass(category.Status)}`;
    chip.textContent = operationalMetricStatusLabel(category.Status);
    const question = document.createElement("p");
    question.textContent = `${translate("metricQuestion")}: ${category.QuestionZh || "-"} · ${translate("metricFocus")}: ${category.FocusZh || "-"}`;
    heading.append(title, chip, question);
    const list = document.createElement("div");
    list.className = "operational-metric-list";
    (category.Metrics || []).forEach((metric) => list.append(operationalMetricRow(metric)));
    card.append(heading, list);
    categories.append(card);
  });
  renderOperationalFeedback();
}

function operationalMetricRow(metric) {
  const row = document.createElement("article");
  row.className = `operational-metric-row ${operationalMetricStatusClass(metric.Status)}`;
  const main = document.createElement("div");
  const name = document.createElement("strong");
  name.textContent = metric.NameZh || metric.MetricID;
  const definition = document.createElement("p");
  definition.textContent = metric.DefinitionZh || "-";
  main.append(name, definition);
  const value = document.createElement("div");
  value.className = "operational-metric-value";
  const number = document.createElement("strong");
  number.textContent = metricDisplayValue(metric);
  const coverage = document.createElement("span");
  coverage.textContent = `${translate("metricCoverage")}: ${dataCoverageLabel(metric.DataCoverage)}`;
  value.append(number, coverage);
  row.append(main, value);
  return row;
}

function operationalMetricDisplayName(metricId) {
  for (const category of operationalMetricsData?.Categories || []) {
    const metric = (category.Metrics || []).find((item) => item.MetricID === metricId);
    if (metric) return metric.NameZh || metric.NameEn || metric.MetricID;
  }
  return metricId || "-";
}

function renderOperationalFeedback() {
  const container = document.getElementById("operational-feedback-list");
  container.replaceChildren();
  const feedback = operationalMetricsData?.VarianceFeedback || {};
  const actions = feedback.RecommendedActions || [];
  const issues = feedback.DataCoverageIssues || [];
  container.append(detailSection("recommendedActions", actions.map((item) => [operationalMetricDisplayName(item.MetricID), item.ActionZh || "-"])));
  container.append(detailSection("dataCoverageIssues", issues.length
    ? issues.map((item) => [operationalMetricDisplayName(item.MetricID), item.MessageZh || dataCoverageLabel(item.Coverage)])
    : [["status", translate("noDataCoverageIssues")]]));
}

async function loadScheduleResult(runId) {
  if (!runId) return;
  try {
    const response = await fetch(`/planner/workbench/schedule-results/runs/${encodeURIComponent(runId)}/workbench`);
    if (!response.ok) throw new Error(String(response.status));
    scheduleResultData = (await response.json()).Data;
    selectedScheduleRunID = runId;
    simioAdherencePage = 1;
    renderScheduleResult();
    await loadScheduledOrders(runId);
    await loadPlanPublication(runId);
    await loadScheduleOutputGovernance(runId);
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
  renderSdbrMarketControl(scheduleResultData);
  loadSdbrWhatIfWorkspace(selectedScheduleRunID);
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

function setGanttMode(modeName) {
  activeGanttMode = modeName === "order" ? "order" : "resource";
  document.querySelectorAll("[data-gantt-mode]").forEach((button) => {
    const active = button.dataset.ganttMode === activeGanttMode;
    button.classList.toggle("is-active", active);
    button.setAttribute("aria-selected", String(active));
  });
  renderGanttBoard();
}

function ganttBarTypeLabel(bar) {
  if (bar.BarType === "Processing") return translate("processing");
  if (bar.BarType === "Maintenance") return translate("maintenance");
  if (bar.BarType === "Unavailable") return translate("unavailableTime");
  return translate(`${String(bar.BufferZone || "Green").toLowerCase()}Buffer`);
}

function ganttTickIntervalMinutes(rangeMs, zoomValue) {
  const rangeMinutes = rangeMs / 60000;
  const targetTicks = zoomValue >= 16 ? 120 : zoomValue >= 8 ? 72 : zoomValue >= 4 ? 48 : 4;
  const intervals = zoomValue >= 8
    ? [5, 15, 30, 60, 120, 240, 480, 720, 1440, 2880, 10080]
    : [360, 720, 1440, 2880, 10080];
  return intervals.find((minutes) => rangeMinutes / minutes <= targetTicks) || intervals[intervals.length - 1];
}

function renderGanttTicks(axisTrack, from, rangeMs, zoomValue) {
  const intervalMinutes = ganttTickIntervalMinutes(rangeMs, zoomValue);
  const intervalMs = intervalMinutes * 60000;
  const formatterOptions = intervalMinutes < 1440
    ? { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" }
    : { month: "short", day: "numeric" };
  const formatter = new Intl.DateTimeFormat(currentLanguage === "zh" ? "zh-CN" : "en-US", formatterOptions);
  for (let offset = 0, index = 0; offset <= rangeMs + 1 && index < 240; offset += intervalMs, index += 1) {
    const tick = document.createElement("span");
    tick.className = "gantt-tick";
    tick.style.setProperty("--tick-position", `${Math.min(offset / rangeMs * 100, 100)}%`);
    tick.textContent = formatter.format(new Date(from.getTime() + offset));
    axisTrack.append(tick);
  }
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
  const zoomValue = Number(document.getElementById("gantt-zoom").value) || 1;
  board.style.setProperty("--gantt-zoom", String(zoomValue));
  const axis = document.createElement("div");
  axis.className = "gantt-axis";
  const axisLabel = document.createElement("div");
  axisLabel.className = "gantt-axis-label";
  axisLabel.textContent = activeGanttMode === "order" ? translate("workOrder") : translate("resource");
  const axisTrack = document.createElement("div");
  axisTrack.className = "gantt-axis-track";
  renderGanttTicks(axisTrack, from, rangeMs, zoomValue);
  axis.append(axisLabel, axisTrack);
  board.append(axis);
  const sourceRows = activeGanttMode === "order"
    ? ganttRowsByOrder(scheduleResultData.Gantt.Rows)
    : scheduleResultData.Gantt.Rows;
  let visibleRows = 0;
  sourceRows.forEach((rowData) => {
    if (resourceFilter && activeGanttMode !== "order" && rowData.ResourceID !== resourceFilter) return;
    const bars = rowData.Bars.filter((bar) => {
      if (resourceFilter && activeGanttMode === "order" && bar.ResourceID !== resourceFilter) return false;
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
    label.textContent = activeGanttMode === "order"
      ? rowData.OrderID
      : `${rowData.ResourceName}${rowData.IsConstraint ? ` · ${translate("constraint")}` : ""}`;
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
      element.title = `${ganttBarTypeLabel(bar)}\n${translate("workOrder")}: ${bar.OrderID || "-"}\n${translate("resource")}: ${bar.ResourceName || rowData.ResourceName}\n${translate("startedAt")}: ${formatDate(bar.Start)}\n${translate("plannedCompletion")}: ${formatDate(bar.End)}`;
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

function ganttRowsByOrder(resourceRows) {
  const byOrder = new Map();
  resourceRows.forEach((resourceRow) => {
    (resourceRow.Bars || []).forEach((bar) => {
      if (!bar.OrderID || bar.BarType !== "Processing") return;
      const existing = byOrder.get(bar.OrderID) || {
        OrderID: bar.OrderID,
        ResourceID: "",
        ResourceName: bar.OrderID,
        IsConstraint: false,
        Bars: []
      };
      existing.Bars.push({
        ...bar,
        ResourceID: resourceRow.ResourceID,
        ResourceName: resourceRow.ResourceName
      });
      byOrder.set(bar.OrderID, existing);
    });
  });
  return [...byOrder.values()]
    .map((row) => ({
      ...row,
      Bars: row.Bars.sort((left, right) => new Date(left.Start) - new Date(right.Start))
    }))
    .sort((left, right) => {
      const leftStart = left.Bars[0]?.Start || "";
      const rightStart = right.Bars[0]?.Start || "";
      return new Date(leftStart) - new Date(rightStart);
    });
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
  renderSdbrFlowControl();
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

function renderSdbrMarketControl(data) {
  const panel = document.getElementById("sdbr-market-control-panel");
  if (!panel) return;
  const market = data?.SDBRMarketControl;
  if (!market) {
    panel.hidden = true;
    return;
  }
  panel.hidden = false;
  const loadSummary = market.CCRPlannedLoad?.Summary || {};
  const safeDate = market.MTOSafeDate || {};
  const mta = market.MTAReplenishmentLoad || market.CCRPlannedLoad?.MTAReplenishmentLoad || {};
  const prioritySummary = market.UnifiedBufferPriority?.Summary || {};
  const totalLoadMinutes = Number(loadSummary.MtoLoadMinutes || 0) + Number(loadSummary.MtaLoadMinutes || 0);
  setText("market-control-load-status", marketLoadStatusLabel(loadSummary.Status));
  setText("market-control-load-detail", translateWith("marketLoadDetail", {
    total: formatNumber(totalLoadMinutes),
    hours: formatNumber(totalLoadMinutes / 60, 1),
    mto: formatNumber(loadSummary.MtoLoadMinutes || 0),
    mta: formatNumber(loadSummary.MtaLoadMinutes || 0),
    max: formatNumber(loadSummary.MaxLoadPercent || 0)
  }));
  const safeDateText = safeDate.Status === "Expired"
    ? translateWith("marketSafeDateExpired", { date: safeDate.EarliestSafeDate || "-" })
    : (safeDate.EarliestSafeDate || translate("marketSafeDateUnavailable"));
  setText("market-control-safe-date", safeDateText);
  setText("market-control-safe-date-detail", safeDate.BusinessMeaning || "-");
  setText("market-control-mta-load", translateWith("marketMtaMapped", { count: formatNumber(mta.MappedSuggestionCount || 0) }));
  setText("market-control-mta-detail", translateWith("marketMtaUnmapped", { count: formatNumber(mta.UnmappedSuggestionCount || 0) }));
  setText("market-control-priority-count", translateWith("marketPriorityCount", { count: formatNumber(prioritySummary.TotalCount || 0) }));
  setText("market-control-priority-detail", translateWith("marketPriorityDetail", {
    red: formatNumber(prioritySummary.RedCount || 0),
    yellow: formatNumber(prioritySummary.YellowCount || 0),
    green: formatNumber(prioritySummary.GreenCount || 0)
  }));
  renderMarketControlDetails(market);
}

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
    sdbrWhatIfResult = null;
    renderSdbrWhatIfWorkspace();
    renderSdbrWhatIfResult();
  } catch (_error) {
    sdbrWhatIfWorkspace = null;
    sdbrWhatIfResult = null;
    panel.hidden = true;
  }
}

function renderSdbrWhatIfWorkspace() {
  const panel = document.getElementById("sdbr-what-if-panel");
  if (!panel || !sdbrWhatIfWorkspace) return;
  const buckets = Array.isArray(sdbrWhatIfWorkspace.CcrBuckets) ? sdbrWhatIfWorkspace.CcrBuckets : [];
  if (!buckets.length) {
    panel.hidden = true;
    return;
  }
  panel.hidden = false;
  const resourceSelect = document.getElementById("sdbr-what-if-resource");
  const dateSelect = document.getElementById("sdbr-what-if-date");
  const existingResource = resourceSelect.value;
  const existingDate = dateSelect.value;
  const resourceOptions = [...new Map(buckets.map((item) => [
    item.ResourceID,
    { ResourceID: item.ResourceID, Label: `${item.ResourceName || item.ResourceID} · ${item.ResourceID}` }
  ])).values()].filter((item) => item.ResourceID);
  replaceSelectOptions(resourceSelect, resourceOptions, { valueKey: "ResourceID", labelKey: "Label" });
  if (existingResource && resourceOptions.some((item) => item.ResourceID === existingResource)) resourceSelect.value = existingResource;
  const visibleDates = [...new Set(buckets
    .filter((item) => !resourceSelect.value || item.ResourceID === resourceSelect.value)
    .map((item) => item.Date)
    .filter(Boolean))];
  replaceSelectOptions(dateSelect, visibleDates);
  if (existingDate && visibleDates.includes(existingDate)) dateSelect.value = existingDate;
  const candidateSelect = document.getElementById("sdbr-what-if-mta-candidate");
  if (candidateSelect) {
    const candidates = Array.isArray(sdbrWhatIfWorkspace.MtaRedCandidates) ? sdbrWhatIfWorkspace.MtaRedCandidates : [];
    const candidateOptions = candidates.map((item) => ({
      CandidateID: item.CandidateID,
      Label: `${item.ItemID || "-"} · ${item.LocationID || "-"} · ${formatNumber(item.ProjectedLoadMinutes || 0)} min`
    })).filter((item) => item.CandidateID);
    replaceSelectOptions(candidateSelect, candidateOptions, { valueKey: "CandidateID", labelKey: "Label" });
  }
  updateSdbrWhatIfMtaCandidateDisplay(true);
}

function selectedSdbrWhatIfMtaCandidate() {
  const candidateSelect = document.getElementById("sdbr-what-if-mta-candidate");
  const candidateID = candidateSelect?.value;
  const candidates = Array.isArray(sdbrWhatIfWorkspace?.MtaRedCandidates) ? sdbrWhatIfWorkspace.MtaRedCandidates : [];
  return candidates.find((item) => item.CandidateID === candidateID) || null;
}

function updateSdbrWhatIfMtaCandidateDisplay(applyLoadDefault = false) {
  const scenarioType = document.getElementById("sdbr-what-if-scenario-type")?.value;
  const wrap = document.getElementById("sdbr-what-if-mta-candidate-wrap");
  const summary = document.getElementById("sdbr-what-if-mta-candidate-summary");
  const loadInput = document.getElementById("sdbr-what-if-load-minutes");
  const isMta = scenarioType === "MTA_RED_REPLENISHMENT_SHOCK";
  if (wrap) wrap.hidden = !isMta;
  if (!summary) return;
  if (!isMta) {
    summary.hidden = true;
    summary.textContent = "";
    return;
  }
  const candidate = selectedSdbrWhatIfMtaCandidate();
  if (!candidate) {
    summary.hidden = false;
    summary.textContent = translate("noMtaRedCandidates");
    return;
  }
  if (applyLoadDefault && loadInput && Number(candidate.ProjectedLoadMinutes || 0) > 0) {
    loadInput.value = String(candidate.ProjectedLoadMinutes);
  }
  summary.hidden = false;
  summary.textContent = translateWith("mtaCandidateSummary", {
    candidate: candidate.CandidateID || "-",
    item: candidate.ItemID || "-",
    location: candidate.LocationID || "-",
    qty: formatNumber(candidate.SuggestedShockQty || 0),
    minutes: formatNumber(candidate.ProjectedLoadMinutes || 0)
  });
}

async function runSdbrWhatIf() {
  if (!selectedScheduleRunID) return;
  const button = document.getElementById("run-sdbr-what-if");
  if (!button) return;
  button.disabled = true;
  try {
    const selectedCandidate = selectedSdbrWhatIfMtaCandidate();
    const response = await fetch(`/planner/workbench/schedule-results/runs/${encodeURIComponent(selectedScheduleRunID)}/what-if/evaluate`, {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify({
        ScenarioType: document.getElementById("sdbr-what-if-scenario-type").value,
        ResourceID: document.getElementById("sdbr-what-if-resource").value,
        BucketDate: document.getElementById("sdbr-what-if-date").value,
        AdditionalLoadMinutes: Number(document.getElementById("sdbr-what-if-load-minutes").value || 0),
        DowntimeMinutes: Number(document.getElementById("sdbr-what-if-downtime-minutes").value || 0),
        CandidateID: selectedCandidate?.CandidateID || null,
        CandidateItemID: selectedCandidate?.ItemID || null,
        CandidateLocationID: selectedCandidate?.LocationID || null,
        ProjectedLoadMinutes: Number(selectedCandidate?.ProjectedLoadMinutes || 0),
        SuggestedShockQty: Number(selectedCandidate?.SuggestedShockQty || 0)
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

function whatIfDecisionLabel(value) {
  const key = `whatIfDecision_${value || "ReviewRequired"}`;
  const translated = translate(key);
  return translated === key ? displayValue(value) : translated;
}

function renderSdbrWhatIfResult() {
  const container = document.getElementById("sdbr-what-if-result");
  if (!container) return;
  container.replaceChildren();
  const result = sdbrWhatIfResult;
  if (!result) return;
  const impact = result.Impact || {};
  const recommendation = result.Recommendation || {};
  const simio = result.SimioRecommendation || {};
  const sections = [];
  if (result.Impact) {
    const beforeAfterRows = [
      ["resource", `${impact.ResourceName || "-"} · ${impact.ResourceID || "-"}`],
      ["effectiveCapacity", `${formatNumber(impact.CapacityMinutes || 0)} -> ${formatNumber(impact.EffectiveCapacityMinutes || 0)} min`],
      ["loadChange", `${formatNumber(impact.BeforeLoadMinutes || 0)} -> ${formatNumber(impact.AfterLoadMinutes || 0)} min`],
      ["loadPercentChange", `${formatNumber(impact.BeforeLoadPercent || 0)}% -> ${formatNumber(impact.AfterLoadPercent || 0)}%`],
      ["beforeAfterStatus", `${marketLoadStatusLabel(impact.BeforeStatus)} -> ${marketLoadStatusLabel(impact.AfterStatus)}`]
    ];
    if (impact.Candidate?.CandidateID) {
      beforeAfterRows.push(["mtaRedCandidate", `${impact.Candidate.CandidateID} · ${impact.Candidate.ItemID || "-"} · ${impact.Candidate.LocationID || "-"}`]);
    }
    sections.push(detailSection("whatIfBeforeAfter", beforeAfterRows));
  } else {
    sections.push(detailSection("whatIfBeforeAfter", [
      ["status", whatIfDecisionLabel(recommendation.Decision)],
      ["reason", displayValue(recommendation.ReasonCode || recommendation.BusinessMeaning)]
    ]));
  }
  sections.push(
    detailSection("whatIfRecommendation", [
      ["recommendedAction", `${whatIfDecisionLabel(recommendation.Decision)} · ${displayValue(recommendation.BusinessMeaning)}`],
      ["requiresReschedule", recommendation.RequiresFormalReplan ? translate("yes") : translate("no")]
    ]),
    detailSection("whatIfSimioHint", [
      ["status", simio.Recommended ? translate("yes") : translate("no")],
      ["businessDiagnosis", displayValue(simio.BusinessMeaning)]
    ])
  );
  container.append(...sections);
}

function marketLoadStatusLabel(status) {
  const key = `marketLoadStatus_${status || "Protected"}`;
  const translated = translate(key);
  return translated === key ? displayValue(status) : translated;
}

function bufferZoneLabel(zone) {
  const key = String(zone || "Green");
  const translated = translate(key);
  return translated === key ? displayValue(zone) : translated;
}

function renderMarketControlDetails(market) {
  const container = document.getElementById("market-control-details-list");
  if (!container) return;
  container.replaceChildren();

  const loadSection = document.createElement("section");
  const loadTitle = document.createElement("h3");
  loadTitle.textContent = translate("marketLoadBucketTitle");
  loadSection.append(loadTitle);
  const buckets = Array.isArray(market.CCRPlannedLoad?.Buckets) ? market.CCRPlannedLoad.Buckets : [];
  if (buckets.length) {
    const list = document.createElement("div");
    list.className = "market-detail-list";
    buckets
      .filter((bucket) => Number(bucket.TotalPlannedLoadMinutes || 0) > 0)
      .forEach((bucket) => {
        const row = document.createElement("div");
        row.className = "market-detail-row";
        const title = document.createElement("strong");
        title.textContent = `${bucket.ResourceName || bucket.ResourceID || "-"} · ${bucket.Date || "-"}`;
        const detail = document.createElement("span");
        detail.textContent = `${formatNumber(bucket.TotalPlannedLoadMinutes || 0)} 分钟 / ${formatNumber((bucket.TotalPlannedLoadMinutes || 0) / 60, 1)} 小时 · ${translate("marketDemandClassMTO")} ${formatNumber(bucket.MtoLoadMinutes || 0)} 分钟 · ${translate("marketDemandClassMTA")} ${formatNumber(bucket.MtaLoadMinutes || 0)} 分钟 · ${formatNumber(bucket.LoadPercent || 0)}%`;
        row.append(title, detail);
        list.append(row);
      });
    loadSection.append(list.childElementCount ? list : emptyMarketDetail("marketNoLoadBuckets"));
  } else {
    loadSection.append(emptyMarketDetail("marketNoLoadBuckets"));
  }

  const prioritySection = document.createElement("section");
  const priorityTitle = document.createElement("h3");
  priorityTitle.textContent = translate("marketPriorityRowsTitle");
  prioritySection.append(priorityTitle);
  const rows = Array.isArray(market.UnifiedBufferPriority?.Rows) ? market.UnifiedBufferPriority.Rows : [];
  if (rows.length) {
    const list = document.createElement("div");
    list.className = "market-detail-list";
    rows.forEach((item) => {
      const row = document.createElement("div");
      row.className = `market-detail-row zone-${item.PriorityZone || "Green"}`;
      const demandClass = item.DemandClass === "MTA" ? translate("marketDemandClassMTA") : translate("marketDemandClassMTO");
      const sourceKey = `marketPrioritySource_${item.Source || ""}`;
      const source = translate(sourceKey) === sourceKey ? displayValue(item.Source) : translate(sourceKey);
      const title = document.createElement("strong");
      title.textContent = `${bufferZoneLabel(item.PriorityZone)} · ${demandClass} · ${source}`;
      const detail = document.createElement("span");
      detail.textContent = item.DemandClass === "MTA"
        ? translateWith("marketPriorityItem", {
            item: item.ItemID || "-",
            location: item.LocationID || "-",
            order: item.OrderID || "-"
          })
        : translateWith("marketPriorityOrder", { order: item.OrderID || "-" });
      const action = document.createElement("small");
      action.textContent = item.RecommendedAction || "-";
      row.append(title, detail, action);
      list.append(row);
    });
    prioritySection.append(list);
  } else {
    prioritySection.append(emptyMarketDetail("marketNoPriorityRows"));
  }

  container.append(loadSection, prioritySection);
}

function emptyMarketDetail(messageKey) {
  const item = document.createElement("p");
  item.className = "muted";
  item.textContent = translate(messageKey);
  return item;
}

function renderSdbrFlowControl() {
  const summary = document.getElementById("sdbr-flow-control-summary");
  const list = document.getElementById("protective-capacity-list");
  summary.replaceChildren();
  list.replaceChildren();
  const control = scheduleResultData?.SDBRFlowControl || {};
  const plannedLoad = control.PlannedLoad || {};
  const safeDate = control.SafeDate || {};
  const release = control.ReleaseDiscipline || {};
  const stability = control.StabilityGuidance || {};
  [
    ["plannedLoad", flowStatusLabel(plannedLoad.Status), flowActionLabel(plannedLoad.RecommendedAction), `${plannedLoad.MaxLoadResourceID || "-"} · ${plannedLoad.MaxLoadPercent || 0}%`],
    ["safeDate", flowStatusLabel(safeDate.Status), safeDate.EarliestSafeDate || "-", safeDate.BusinessMeaning || "-"],
    ["releaseDiscipline", translate("monitorOnly"), release.EarliestSuggestedReleaseAt ? formatDate(release.EarliestSuggestedReleaseAt) : "-", release.BusinessMeaning || "-"],
    ["stabilityGuidance", flowActionLabel(stability.DefaultAction), flowActionLabel(stability.ReplanTrigger), stability.BusinessMeaning || "-"]
  ].forEach(([labelKey, value, subValue, note]) => {
    const card = document.createElement("article");
    card.className = "flow-control-card";
    const label = document.createElement("span");
    label.textContent = translate(labelKey);
    const strong = document.createElement("strong");
    strong.textContent = value;
    const small = document.createElement("small");
    small.textContent = subValue;
    const paragraph = document.createElement("p");
    paragraph.textContent = note;
    card.append(label, strong, small, paragraph);
    summary.append(card);
  });
  (control.ProtectiveCapacity?.Rows || []).forEach((row) => {
    const item = document.createElement("div");
    item.className = `protective-capacity-row ${protectiveStatusClass(row.Status)}`;
    const name = document.createElement("strong");
    name.textContent = row.ResourceName || row.ResourceID || "-";
    const status = document.createElement("span");
    status.textContent = `${protectiveStatusLabel(row.Status)} · ${row.LoadPercent}%`;
    const action = document.createElement("small");
    action.textContent = flowActionLabel(row.RecommendedAction);
    item.append(name, status, action);
    list.append(item);
  });
  if (!(control.ProtectiveCapacity?.Rows || []).length) {
    const empty = document.createElement("p");
    empty.className = "inline-note";
    empty.textContent = translate("notAvailable");
    list.append(empty);
  }
}

function flowStatusLabel(status) {
  const key = `flowStatus_${status}`;
  const translated = translate(key);
  return translated === key ? displayValue(status) : translated;
}

function flowActionLabel(action) {
  const key = `flowAction_${action}`;
  const translated = translate(key);
  return translated === key ? displayValue(action) : translated;
}

function protectiveStatusLabel(status) {
  const key = `protectiveStatus_${status}`;
  const translated = translate(key);
  return translated === key ? displayValue(status) : translated;
}

function protectiveStatusClass(status) {
  if (status === "CandidateConstraint") return "is-critical";
  if (status === "AtRisk") return "is-warning";
  if (status === "Watch") return "is-watch";
  return "is-healthy";
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
    strong.textContent = translate("businessDiagnosis");
    const detail = document.createElement("span");
    detail.textContent = solverDiagnosticBusinessText(diagnostic);
    const technical = document.createElement("details");
    technical.className = "technical-detail";
    const summary = document.createElement("summary");
    summary.textContent = translate("technicalDetails");
    const code = document.createElement("code");
    code.textContent = diagnostic.Code;
    const message = document.createElement("span");
    message.textContent = diagnostic.Message;
    technical.append(summary, code, message);
    item.append(strong, detail, technical);
    container.append(item);
  });
}

function solverDiagnosticBusinessText(diagnostic) {
  const translated = translate(`diag_${diagnostic?.Code}`);
  if (!String(translated).startsWith("diag_")) return translated;
  return businessValue(diagnostic?.Message || diagnostic?.Code);
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

async function loadScheduleOutputGovernance(runId) {
  scheduleOutputGovernanceData = null;
  scheduleOutputPackageData = null;
  try {
    const governanceResponse = await fetch(`/planner/workbench/schedule-results/runs/${encodeURIComponent(runId)}/governance`, { headers: { Accept: "application/json" } });
    if (!governanceResponse.ok) throw new Error(String(governanceResponse.status));
    scheduleOutputGovernanceData = (await governanceResponse.json()).Data;
    const packageResponse = await fetch(`/planner/workbench/schedule-results/runs/${encodeURIComponent(runId)}/output-package`, { headers: { Accept: "application/json" } });
    if (packageResponse.ok) {
      scheduleOutputPackageData = (await packageResponse.json()).Data;
    }
  } catch (_error) {
    scheduleOutputGovernanceData = null;
    scheduleOutputPackageData = null;
  }
  renderScheduleOutputGovernance();
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
  renderScheduleOutputGovernance();
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

function renderScheduleOutputGovernance() {
  const container = document.getElementById("output-governance-summary");
  if (!container) return;
  container.replaceChildren();
  if (!scheduleOutputGovernanceData) {
    renderSimulationResults();
    return;
  }
  const completeness = scheduleOutputGovernanceData.Completeness || {};
  const checks = completeness.Checks || [];
  const passedCount = checks.filter((item) => item.Passed).length;
  const failedCodes = completeness.FailureCodes || [];
  const release = scheduleOutputGovernanceData.Release || {};
  const audit = scheduleOutputGovernanceData.Audit || {};
  const frozen = scheduleOutputGovernanceData.FrozenInputs || {};
  const simio = scheduleOutputGovernanceData.SimioValidation || {};
  const packageId = scheduleOutputPackageData?.PackageID || scheduleOutputGovernanceData.OutputPackageID;
  const publicationStatus = planPublicationData?.Status;
  const publicationReady = ["Reviewed", "Approved", "Published"].includes(publicationStatus);
  const outputAvailable = scheduleOutputGovernanceData.OutputAvailability === "Available";
  const hasReleaseRecommendations = Number(release.RecommendationCount || 0) > 0;
  const simioStatus = simio.Status || "NotRequested";
  const simioFeasible = ["Feasible", "FeasibleWithWarnings"].includes(simio.FeasibilityConclusion);
  const simioTone = simio.FeasibilityConclusion === "Feasible" ? "good" : (simio.Status === "NotRequested" ? "neutral" : "warn");
  container.classList.add("governance-decision-grid");
  container.append(
    businessDecisionCard(
      "publicationDecision",
      publicationReady ? translate("planCanPublish") : translate("planNeedsReview"),
      [["publicationStatus", publicationStatus ? publicationStatusLabel(publicationStatus) : "-"]],
      { tone: publicationReady ? "good" : "warn" }
    ),
    businessDecisionCard(
      "outputDecision",
      outputAvailable && !failedCodes.length ? translate("outputReadyForReview") : translate("outputNeedsAttention"),
      [
        ["outputAvailability", translate(outputAvailable ? "packageReady" : "packageUnavailable")],
        ["passedChecks", `${passedCount} / ${checks.length}`],
        ["failedChecks", failedCodes.length ? failedCodes.map(businessValue).join(", ") : translate("noIssues")],
        ["outputPackageId", displayValue(packageId)],
        ["scheduleFingerprint", compactFingerprint(scheduleOutputGovernanceData.ScheduleFingerprint)]
      ],
      { tone: outputAvailable && !failedCodes.length ? "good" : "warn" }
    ),
    businessDecisionCard(
      "releaseDecision",
      hasReleaseRecommendations ? translate("releaseReadySummary") : translate("releaseNoRecommendation"),
      [
        ["recommendationCount", displayValue(release.RecommendationCount)],
        ["authorized", displayValue(release.AuthorizedCount)],
        ["unauthorizedCount", displayValue(release.UnauthorizedCount)]
      ],
      { tone: hasReleaseRecommendations ? "good" : "neutral" }
    ),
    businessDecisionCard(
      "simulationDecision",
      simioStatus === "NotRequested"
        ? translate("simulationNotRunSummary")
        : (simio.FeasibilityConclusion === "Feasible" ? translate("simulationPassedSummary") : translate("simulationWarningSummary")),
      [
        ["simioValidationStatus", simioBusinessStatusLabel(simio.Status)],
        ["simioFeasibility", simioBusinessStatusLabel(simio.FeasibilityConclusion)],
        ["simioTemplate", displayValue([simio.TemplateID, simio.TemplateVersion].filter(Boolean).join(" · "))],
        ["simioIssues", displayValue(simio.IssueCount)],
        ["simioThroughput", displayValue(formatSimioThroughput(simio.Throughput))],
        ["simioQueueMetrics", displayValue(formatSimioQueue(simio.QueueMetrics))],
        ["simioWipMetrics", displayValue(formatSimioWip(simio.WipMetrics))],
        ["simioResourceUtilization", displayValue(formatSimioUtilization(simio.ResourceUtilization))]
      ],
      { tone: simioFeasible ? simioTone : (simioStatus === "NotRequested" ? "neutral" : "warn") }
    ),
    businessDecisionCard(
      "auditDecision",
      translate("auditReadySummary"),
      [
        ["auditEventCount", displayValue(audit.AuditEventCount)],
        ["scenarioSelectionCount", displayValue(audit.ScenarioSelectionCount)],
        ["workOrderCommandCount", displayValue(audit.WorkOrderCommandCount)],
        ["publicationActionCount", displayValue(audit.PublicationActionCount)]
      ],
      { tone: "neutral" }
    )
  );
  container.append(collapsibleDetailSection("technicalDetails", [
    ["masterDataVersionLabel", displayValue(frozen.MasterDataVersionID)],
    ["snapshotLabel", displayValue(frozen.OperationalStateSnapshotID)],
    ["releasePolicyVersion", displayValue(frozen.ReleasePolicyVersionID)],
    ["simioRunner", displayValue(simio.RunnerBackend || simio.RunnerMode)],
    ["simioPackage", displayValue(simio.PackageID)],
    ["templatePath", displayValue(simio.TemplateFrozenSnapshot?.TemplatePath || simio.TemplateSourcePath)],
    ["templateSourceType", displayValue(simio.TemplateFrozenSnapshot?.TemplateSourceType)],
    ["timeUnitPolicy", displayValue(simio.TemplateFrozenSnapshot?.TimeUnitPolicy)],
    ["desktopValidationStatus", simioTemplateStatusLabel(simio.TemplateFrozenSnapshot?.DesktopValidationStatus)],
    ["simioResultCoverage", simioSourceLabel(simio.ResultCoverage?.Status)],
    ["parsedSources", displayValue((simio.ResultCoverage?.ParsedSources || []).map(simioDataSourceLabel).join(", "))],
    ["unavailableSources", displayValue((simio.ResultCoverage?.UnavailableSources || []).map(simioDataSourceLabel).join(", "))],
    ["simioModelPath", displayValue(simio.ModelPath)],
    ["simioResultModelPath", displayValue(simio.ResultModelPath)]
  ]));
  if (scheduleOutputPackageData) {
    container.append(collapsibleDetailSection("externalDelivery", [
      ["externalDelivery", translate("notSent")],
      ["reason", externalDeliveryReason(scheduleOutputPackageData.ExternalDelivery?.Reason)]
    ]));
  }
  renderSimulationResults();
}

function simioBusinessStatusLabel(value) {
  const zh = {
    NotRequested: "未请求", Completed: "已完成", Failed: "失败", Running: "验证中",
    Feasible: "可行", FeasibleWithWarnings: "可行但有警告", Infeasible: "不可行",
    ResultUnavailable: "结果不可用", PartialResultParsed: "已解析部分仿真结果", Parsed: "已完整解析",
    ParsedFromPostRunLogs: "来自 Simio 运行日志", ParsedFromSDBROutputRows: "来自工单输出记录",
    Mocked: "Mock 验证", NotSimulated: "未仿真", Unavailable: "不可用",
    Warning: "提示", Error: "错误", Information: "信息"
  };
  const en = {
    NotRequested: "Not requested", Completed: "Completed", Failed: "Failed", Running: "Running",
    Feasible: "Feasible", FeasibleWithWarnings: "Feasible with warnings", Infeasible: "Infeasible",
    ResultUnavailable: "Result unavailable", PartialResultParsed: "Partial simulation result parsed", Parsed: "Fully parsed",
    ParsedFromPostRunLogs: "From Simio run logs", ParsedFromSDBROutputRows: "From work-order output rows",
    Mocked: "Mocked", NotSimulated: "Not simulated", Unavailable: "Unavailable",
    Warning: "Warning", Error: "Error", Information: "Information"
  };
  return (currentLanguage === "zh" ? zh : en)[value] || displayValue(value);
}

function simioAdherenceMinuteLabel(value) {
  const number = toNumericValue(value);
  if (number === null) return "-";
  return currentLanguage === "zh" ? `${formatNumber(number)} 分钟` : `${formatNumber(number)} min`;
}

function simioAdherenceSortValue(row, key) {
  if (key === "DurationMinutes") return simioAdherenceDuration(row);
  if (key === "ActualStartTime" || key === "ActualEndTime") {
    const value = row?.[key];
    if (!value) return null;
    const time = new Date(value).getTime();
    return Number.isFinite(time) ? time : null;
  }
  if (key === "QueueWaitMinutes" || key === "WipAfterStart" || key === "WipAfterEnd") {
    return toNumericValue(row?.[key]);
  }
  if (key === "EventStatus") {
    return simioEventStatusLabel(row?.EventStatus).toLowerCase();
  }
  return String(row?.[key] ?? "").toLowerCase();
}

function compareSimioAdherenceRows(left, right) {
  const direction = simioAdherenceSort.direction === "desc" ? -1 : 1;
  const leftValue = simioAdherenceSortValue(left, simioAdherenceSort.key);
  const rightValue = simioAdherenceSortValue(right, simioAdherenceSort.key);
  if (leftValue === null && rightValue === null) return 0;
  if (leftValue === null) return 1;
  if (rightValue === null) return -1;
  if (leftValue < rightValue) return -1 * direction;
  if (leftValue > rightValue) return 1 * direction;
  return 0;
}

function filteredSimioAdherenceRows(rows) {
  const search = (document.getElementById("simio-adherence-search")?.value || "").trim().toLowerCase();
  const eventStatus = document.getElementById("simio-adherence-event-filter")?.value || "";
  const waitFilter = document.getElementById("simio-adherence-wait-filter")?.value || "";
  return rows.filter((row) => {
    if (search && !String(row.OrderID || "").toLowerCase().includes(search)) return false;
    if (eventStatus && row.EventStatus !== eventStatus) return false;
    const wait = toNumericValue(row.QueueWaitMinutes);
    if (waitFilter === "gt0" && !(wait !== null && wait > 0)) return false;
    if (waitFilter === "gt30" && !(wait !== null && wait > 30)) return false;
    if (waitFilter === "gt60" && !(wait !== null && wait > 60)) return false;
    return true;
  });
}

function renderSimioAdherenceRows(simio) {
  const body = document.getElementById("simio-adherence-body");
  const pageSummary = document.getElementById("simio-adherence-page-summary");
  const previous = document.getElementById("simio-adherence-previous");
  const next = document.getElementById("simio-adherence-next");
  const pageSize = Number(document.getElementById("simio-adherence-page-size")?.value || 10);
  if (!body) return;
  body.replaceChildren();
  const rows = simio?.ScheduleAdherence?.Rows || [];
  const filteredRows = filteredSimioAdherenceRows(rows).sort(compareSimioAdherenceRows);
  const pages = Math.max(1, Math.ceil(filteredRows.length / pageSize));
  simioAdherencePage = Math.min(Math.max(1, simioAdherencePage), pages);
  const startIndex = filteredRows.length ? (simioAdherencePage - 1) * pageSize : 0;
  const pageRows = filteredRows.slice(startIndex, startIndex + pageSize);
  if (!pageRows.length) {
    const row = document.createElement("tr");
    const cell = document.createElement("td");
    cell.colSpan = 8;
    cell.className = "table-empty";
    cell.textContent = rows.length ? translate("noSimulationRows") : displayValue(simio?.ScheduleAdherence?.Message || translate("noSimulationRows"));
    row.append(cell);
    body.append(row);
  } else {
    pageRows.forEach((item) => {
      const row = document.createElement("tr");
      [
        item.OrderID,
        item.ActualStartTime,
        item.ActualEndTime,
        simioAdherenceMinuteLabel(item.QueueWaitMinutes),
        simioAdherenceMinuteLabel(simioAdherenceDuration(item)),
        item.WipAfterStart,
        item.WipAfterEnd,
        simioEventStatusLabel(item.EventStatus)
      ].forEach((value) => {
        const cell = document.createElement("td");
        cell.textContent = displayValue(value);
        row.append(cell);
      });
      body.append(row);
    });
  }
  if (pageSummary) {
    const start = filteredRows.length ? startIndex + 1 : 0;
    const end = filteredRows.length ? Math.min(startIndex + pageSize, filteredRows.length) : 0;
    pageSummary.textContent = translateWith("simulationRowsRange", { start, end, total: filteredRows.length });
  }
  if (previous) previous.disabled = simioAdherencePage <= 1;
  if (next) next.disabled = simioAdherencePage >= pages;
}

function renderSimulationResults() {
  const summary = document.getElementById("simio-result-summary");
  const utilizationBody = document.getElementById("simio-resource-utilization-body");
  const adherenceBody = document.getElementById("simio-adherence-body");
  const issuesContainer = document.getElementById("simio-result-issues");
  if (!summary || !utilizationBody || !adherenceBody || !issuesContainer) return;
  summary.replaceChildren();
  utilizationBody.replaceChildren();
  adherenceBody.replaceChildren();
  issuesContainer.replaceChildren();
  const simio = scheduleOutputGovernanceData?.SimioValidation || {};
  if (!scheduleOutputGovernanceData || !simio.Status || simio.Status === "NotRequested") {
    summary.append(detailSection("simioValidation", [
      ["simioValidationStatus", translate("noSimulationResult")]
    ]));
    renderSimioAdherenceRows({ ScheduleAdherence: { Rows: [], Message: translate("noSimulationResult") } });
    return;
  }
  const coverage = simio.ResultCoverage || {};
  summary.append(detailSection("simioValidation", [
    ["simioValidationStatus", simioBusinessStatusLabel(simio.Status)],
    ["simioFeasibility", simioBusinessStatusLabel(simio.FeasibilityConclusion)],
    ["simioTemplate", displayValue([simio.TemplateID, simio.TemplateVersion].filter(Boolean).join(" · "))],
    ["simioThroughput", displayValue(formatSimioThroughput(simio.Throughput))],
    ["simioQueueMetrics", displayValue(formatSimioQueue(simio.QueueMetrics))],
    ["simioWipMetrics", displayValue(formatSimioWip(simio.WipMetrics))],
    ["simioResultCoverage", simioBusinessStatusLabel(coverage.Status)]
  ]));
  summary.append(collapsibleDetailSection("technicalDetails", [
    ["simioRunner", displayValue(simio.RunnerBackend || simio.RunnerMode)],
    ["simioPackage", displayValue(simio.PackageID)],
    ["templatePath", displayValue(simio.TemplateFrozenSnapshot?.TemplatePath || simio.TemplateSourcePath)],
    ["templateSourceType", displayValue(simio.TemplateFrozenSnapshot?.TemplateSourceType)],
    ["timeUnitPolicy", displayValue(simio.TemplateFrozenSnapshot?.TimeUnitPolicy)],
    ["desktopValidationStatus", simioTemplateStatusLabel(simio.TemplateFrozenSnapshot?.DesktopValidationStatus)],
    ["parsedSources", displayValue((coverage.ParsedSources || []).map(simioDataSourceLabel).join(", "))],
    ["unavailableSources", displayValue((coverage.UnavailableSources || []).map(simioDataSourceLabel).join(", "))],
    ["simioModelPath", displayValue(simio.ModelPath)],
    ["simioResultModelPath", displayValue(simio.ResultModelPath)]
  ]));

  const utilizationRows = simio.ResourceUtilization?.Resources || [];
  if (!utilizationRows.length) {
    const row = document.createElement("tr");
    const cell = document.createElement("td");
    cell.colSpan = 5;
    cell.className = "table-empty";
    cell.textContent = translate("notAvailable");
    row.append(cell);
    utilizationBody.append(row);
  } else {
    utilizationRows.forEach((item) => {
      const row = document.createElement("tr");
      const riskClass = simioUtilizationRiskClass(item.UtilizationPercent);
      [
        item.ResourceID,
        item.UtilizationPercent === null || item.UtilizationPercent === undefined ? "-" : `${formatNumber(item.UtilizationPercent)}%`,
        item.BusyMinutes,
        item.StarvedMinutes,
        item.MetricBasis ? simioDataSourceLabel(item.MetricBasis) : ((item.SourceLogs || []).map(simioDataSourceLabel).join(", ") || simioSourceLabel(simio.ResourceUtilization?.Status))
      ].forEach((value, index) => {
        const cell = document.createElement("td");
        if (index === 1 && riskClass) {
          cell.classList.add("utilization-cell", riskClass);
        }
        cell.textContent = displayValue(value);
        row.append(cell);
      });
      utilizationBody.append(row);
    });
  }

  renderSimioAdherenceRows(simio);

  const issues = simio.Issues || [];
  if (!issues.length) {
    const item = document.createElement("div");
    item.className = "diagnostic-item";
    item.textContent = translate("noIssues");
    issuesContainer.append(item);
  } else {
    issues.forEach((issue) => {
      const item = document.createElement("div");
      item.className = `diagnostic-item${simioIssueSeverityClass(issue)}`;
      const strong = document.createElement("strong");
      strong.textContent = simioIssueBusinessLabel(issue);
      const detail = document.createElement("span");
      detail.textContent = simioBusinessStatusLabel(issue.Severity) || displayValue(issue.Severity);
      item.append(strong, detail, collapsibleDetailSection("technicalDetails", [
        ["code", displayValue(issue.Code)],
        ["message", displayValue(issue.Message)],
        ["severity", displayValue(issue.Severity)]
      ]));
      issuesContainer.append(item);
    });
  }
}

async function runSimioValidation() {
  if (!selectedScheduleRunID) return;
  const button = document.getElementById("run-simio-validation");
  button.disabled = true;
  try {
    const response = await fetch("/planner/workbench/simio/validation-runs", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        RunID: selectedScheduleRunID,
        RunnerMode: document.getElementById("simio-runner-mode").value,
        RequestedBy: "planner",
        RequestedAt: new Date().toISOString()
      })
    });
    if (!response.ok) throw new Error(String(response.status));
    showNotification(translate("simioValidationRequested"), "success");
    await loadScheduleOutputGovernance(selectedScheduleRunID);
  } catch (_error) {
    showNotification(translate("notifyError"), "error");
  } finally {
    button.disabled = false;
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

async function createReplanRunFromCurrentSchedule() {
  if (!selectedScheduleRunID || !scheduleResultData?.Context) return;
  if (!(await confirmAction({ message: translate("confirmReplan"), context: `${translate("planningRun")}: ${selectedScheduleRunID}` }))) return;
  const context = scheduleResultData.Context;
  const now = new Date();
  const runId = `RPL-RUN-${now.toISOString().replace(/\D/g, "").slice(0, 14)}`;
  const payload = {
    RunID: runId,
    ProblemID: context.ProblemID,
    MasterDataVersionID: context.MasterDataVersionID,
    OperationalStateSnapshotID: context.OperationalStateSnapshotID,
    SourceRunID: selectedScheduleRunID,
    ReleasePolicyVersionID: context.ReleasePolicyVersionID || null,
    ScheduleStartAt: now.toISOString(),
    TimeBufferMinutes: 0,
    FreezeWindowMinutes: 0,
    ObjectiveStrategyID: "v1_delivery_flow_bottleneck",
    SolverBackendID: "ortools",
    TimeLimitSeconds: 300,
    MaxAttempts: 3,
    RetryDelaySeconds: 60,
    RequestedBy: "planner",
    RequestedAt: now.toISOString()
  };
  const createResponse = await fetch("/planner/workbench/planning-runs", {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload)
  });
  if (!createResponse.ok) {
    showNotification(translate("notifyError"), "error");
    return;
  }
  const enqueueResponse = await fetch(`/planner/workbench/planning-runs/${encodeURIComponent(runId)}/enqueue`, {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ EnqueuedBy: "planner", EnqueuedAt: new Date().toISOString(), MaxAttempts: 3, RetryDelaySeconds: 60 })
  });
  if (!enqueueResponse.ok) {
    showNotification(translate("notifyError"), "error");
    return;
  }
  showNotification(translate("replanCreatedQueued"), "success");
  setText("route-status", translate("replanCreatedQueued"));
  window.location.hash = "planning-runs";
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
    const query = new URLSearchParams({
      evaluated_at: new Date(evaluatedValue).toISOString(),
      operational_state_max_age_minutes: "60"
    });
    if (releaseManagementUsesLatestOperationalState) query.set("use_latest_operational_state", "true");
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

async function reevaluateReleaseManagementWithLatestState() {
  const runId = document.getElementById("release-run-select").value;
  const evaluatedValue = document.getElementById("release-evaluated-at").value;
  if (!runId || !evaluatedValue) return;
  try {
    const response = await fetch(`/planner/workbench/release-management/runs/${encodeURIComponent(runId)}/mock-operational-state-refresh`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        EvaluatedAt: new Date(evaluatedValue).toISOString(),
        SourceSnapshotID: releaseManagementData?.OperationalStateSnapshotID,
        ActorID: "planner"
      })
    });
    if (!response.ok && response.status !== 409) throw new Error(String(response.status));
  } catch (_error) {
    showNotification(translate("notifyError"), "error");
  }
  releaseManagementUsesLatestOperationalState = true;
  await loadReleaseManagement();
  showNotification(translate("releaseSnapshotRefreshed"), "success");
}

function gateStatusLabel(value) {
  return translate({ Clear: "clear", Ready: "clear", Early: "early", Blocked: "blocked", PendingInbound: "inbound" }[value] || value);
}

function renderReleaseManagement() {
  document.querySelectorAll("[data-release-summary]").forEach((element) => { element.textContent = releaseManagementData.Summary[element.dataset.releaseSummary] ?? 0; });
  const snapshot = document.getElementById("release-snapshot-status");
  const policyVersion = releaseManagementData.ReleasePolicyVersionID || releaseManagementData.PolicyEvidence?.VersionID || "-";
  const snapshotMessage = `${translate("snapshotStatus")}: ${translate({ Fresh: "freshSnapshot", Stale: "staleSnapshot", Future: "futureSnapshot" }[releaseManagementData.OperationalStateStatus])} · ${releaseManagementData.OperationalStateSnapshotID} · ${formatDate(releaseManagementData.OperationalStateCapturedAt)} · ${translate("releasePolicyVersion")}: ${policyVersion}`;
  snapshot.textContent = releaseManagementData.OperationalStateStatus === "Stale"
    ? `${snapshotMessage} · ${translate("snapshotRefreshAdvice")}`
    : snapshotMessage;
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
  const evidence = candidate.PolicyEvidence || releaseManagementData.PolicyEvidence || {};
  content.append(detailSection("policyEvidence", detailRowsFromObject({
    releasePolicyVersion: evidence.VersionID,
    ropeBufferMinutes: evidence.RopeBufferMinutes,
    materialCheckWindowMinutes: evidence.MaterialCheckWindowMinutes ?? evidence.MaterialLookaheadMinutes,
    maxWipCount: evidence.MaxWipCount,
    toleranceMinutes: evidence.StabilityPolicy?.ToleranceMinutes,
    replanThresholdMinutes: evidence.StabilityPolicy?.ReplanThresholdMinutes,
    consecutiveBlockedThreshold: evidence.StabilityPolicy?.ConsecutiveBlockedThreshold,
    replanCooldownMinutes: evidence.StabilityPolicy?.ReplanCooldownMinutes
  })));
  if (candidate.Stability) {
    content.append(detailSection("stabilityDecision", detailRowsFromObject({
      action: candidate.Stability.Action,
      deviationMinutes: candidate.Stability.DeviationMinutes,
      absoluteDeviationMinutes: candidate.Stability.AbsoluteDeviationMinutes,
      reasonCodeLabel: candidate.Stability.ReasonCode
    })));
  }
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
      code.textContent = `${translate("technicalCode")}: ${reason.Code}`;
      item.append(title, code);
      const reasonDetails = { ...(reason.Details || {}) };
      if (reasonDetails.RecommendedAction) {
        reasonDetails.RecommendedAction = translate(`action_${reasonDetails.RecommendedAction}`);
      }
      const details = detailSection("reasonDetails", detailRowsFromObject(reasonDetails));
      item.append(details);
      content.append(item);
    });
  }
  openSideDrawer("release-reason-detail");
}

async function authorizeReleaseCandidate(candidate) {
  if (!candidate.CanAuthorize || !(await confirmAction({ message: translate("authorizeImpact"), context: `${translate("workOrder")}: ${candidate.OrderID}` }))) return;
  const response = await fetch(`/planner/workbench/release-management/runs/${encodeURIComponent(selectedReleaseRunID)}/orders/${encodeURIComponent(candidate.OrderID)}/authorize`, {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      ReleasedBy: "planner",
      ReleasedAt: new Date(document.getElementById("release-evaluated-at").value).toISOString(),
      OperationalStateMaxAgeMinutes: 60,
      UseLatestOperationalState: releaseManagementUsesLatestOperationalState,
      OperationalStateSnapshotID: releaseManagementData?.OperationalStateSnapshotID
    })
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
    ["snapshotLabel", packageData.OperationalStateSnapshotID], ["releasePolicyVersion", packageData.ReleasePolicyVersionID]
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
    ["bufferOwner", context.BufferOwnerID], ["dailyLoad", `${(context.DailyLoadMinutes / 60).toFixed(1)} ${translate("hours")} · ${translate("bufferDailyLoadScope")}`],
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

async function loadMesDispatchPriority(runId, evaluatedValue) {
  try {
    const query = new URLSearchParams({ evaluated_at: new Date(evaluatedValue).toISOString() });
    const response = await fetch(`/planner/workbench/dispatch-priority/runs/${encodeURIComponent(runId)}/workbench?${query}`);
    if (!response.ok) throw new Error(String(response.status));
    dispatchPriorityData = (await response.json()).Data;
  } catch (_error) {
    dispatchPriorityData = null;
  }
  renderMesDispatchPriority();
}

async function loadDispatchSuggestionRuns() {
  try {
    const response = await fetch("/planner/workbench/planning-runs/workbench");
    if (!response.ok) throw new Error(String(response.status));
    const runs = (await response.json()).Data.Rows.filter((run) => run.Status === "Completed");
    const select = document.getElementById("dispatch-run-select");
    replaceSelectOptions(select, runs, { valueKey: "RunID", labelKey: "RunID" });
    if (!runs.length) {
      document.getElementById("dispatch-suggestions-empty").hidden = false;
      document.getElementById("dispatch-suggestions-content").hidden = true;
      return;
    }
    const preferred = selectedDispatchRunID || selectedBufferRunID || selectedReleaseRunID || selectedScheduleRunID;
    selectedDispatchRunID = runs.some((run) => run.RunID === preferred) ? preferred : runs[0].RunID;
    select.value = selectedDispatchRunID;
    if (!document.getElementById("dispatch-evaluated-at").value) document.getElementById("dispatch-evaluated-at").value = toLocalDateTimeInput(new Date());
    document.getElementById("dispatch-suggestions-empty").hidden = true;
    await loadDispatchSuggestions();
  } catch (_error) {
    document.getElementById("dispatch-suggestions-error").hidden = false;
  }
}

async function loadDispatchSuggestions() {
  const runId = document.getElementById("dispatch-run-select").value;
  const evaluatedValue = document.getElementById("dispatch-evaluated-at").value;
  if (!runId || !evaluatedValue) return;
  selectedDispatchRunID = runId;
  try {
    await loadMesDispatchPriority(runId, evaluatedValue);
    document.getElementById("dispatch-suggestions-content").hidden = false;
    document.getElementById("dispatch-suggestions-error").hidden = true;
  } catch (_error) {
    document.getElementById("dispatch-suggestions-content").hidden = true;
    document.getElementById("dispatch-suggestions-error").hidden = false;
  }
}

function renderMesDispatchPriority() {
  const summary = document.getElementById("mes-dispatch-summary");
  const resources = document.getElementById("mes-dispatch-resources");
  const chip = document.getElementById("mes-dispatch-policy-chip");
  const issueStatus = document.getElementById("mes-dispatch-issue-status");
  summary.replaceChildren();
  resources.replaceChildren();
  renderMesDispatchIssueStatus(issueStatus);
  if (!dispatchPriorityData) {
    chip.className = "status-chip neutral";
    chip.textContent = translate("mesDispatchUnavailable");
    resources.append(emptyDispatchMessage("mesDispatchUnavailable"));
    return;
  }
  chip.className = "status-chip is-valid";
  chip.textContent = `${translate("snapshotLabel")}: ${displayValue(dispatchPriorityData.OperationalStateSnapshotID)}`;
  [
    ["resource", dispatchPriorityData.Summary.ResourceCount],
    ["dispatchableOperations", dispatchPriorityData.Summary.DispatchableOperationCount],
    ["candidateWarnings", dispatchPriorityData.Summary.CandidateWarningCount],
    ["queueJumpSuggestions", dispatchPriorityData.Summary.QueueJumpSuggestionCount],
    ["plannerConfirmations", dispatchPriorityData.Summary.PlannerConfirmationCount],
    ["replanSuggestions", dispatchPriorityData.Summary.ReplanSuggestionCount]
  ].forEach(([labelKey, value]) => summary.append(detailMetric(labelKey, value)));
  (dispatchPriorityData.Resources || []).forEach((resource) => {
    const section = document.createElement("details");
    section.className = "dispatch-resource-card collapsible-resource";
    const heading = document.createElement("summary");
    heading.className = "dispatch-resource-heading";
    const title = document.createElement("strong");
    title.textContent = `${resource.ResourceName || resource.ResourceID} · ${resource.WorkCenterID}`;
    const counts = document.createElement("span");
    counts.className = "status-chip neutral";
    counts.textContent = `${translate("dispatchableOperations")} ${resource.QueueCount} · ${translate("candidateWarnings")} ${resource.CandidateWarningCount}`;
    const action = document.createElement("small");
    action.className = "collapsible-action";
    action.textContent = translate("showDetails");
    heading.append(title, counts, action);
    section.append(heading);
    section.addEventListener("toggle", () => {
      action.textContent = translate(section.open ? "hideDetails" : "showDetails");
    });
    section.append(dispatchQueueGroup("dispatchableOperations", resource.Queue || [], false));
    section.append(dispatchQueueGroup("candidateWarnings", resource.CandidateWarnings || [], true));
    resources.append(section);
  });
}

function renderMesDispatchIssueStatus(container) {
  if (!container) return;
  if (!mesDispatchIssueData) {
    container.className = "inline-note";
    container.textContent = translate("dispatchSuggestionNotIssued");
    return;
  }
  const packageId = mesDispatchIssueData.DispatchSuggestionPackage?.PackageID;
  const status = mesDispatchIssueData.IntegrationMessage?.Status || mesDispatchIssueData.Status;
  container.className = "inline-note";
  container.textContent = `${translate("dispatchSuggestionIssued")} · ${translate("packageId")}: ${displayValue(packageId)} · ${translate("mockDeliveryStatus")}: ${translate(status) || displayValue(status)}`;
}

function dispatchQueueGroup(titleKey, rows, isWarning) {
  const group = document.createElement("div");
  group.className = "dispatch-queue-group";
  const title = document.createElement("h3");
  title.textContent = translate(titleKey);
  group.append(title);
  if (!rows.length) {
    group.append(emptyDispatchMessage(isWarning ? "noDispatchWarnings" : "noDispatchRows"));
    return group;
  }
  rows.forEach((row) => group.append(dispatchOperationCard(row, isWarning)));
  return group;
}

function dispatchOperationCard(row, isWarning) {
  const card = document.createElement("article");
  card.className = `dispatch-operation-card zone-${row.BufferZone || "Early"}${isWarning ? " is-warning" : ""}`;
  const title = document.createElement("div");
  title.className = "dispatch-operation-title";
  const order = document.createElement("strong");
  order.textContent = `${row.OrderID} · ${row.OperationID}`;
  const status = document.createElement("span");
  status.className = `status-chip ${row.DispatchEligibility === "Dispatchable" ? "is-valid" : "neutral"}`;
  status.textContent = translate(row.DispatchEligibility) || row.DispatchEligibility;
  title.append(order, status);
  const details = document.createElement("div");
  details.className = "dispatch-operation-details";
  [
    ["dispatchRank", row.DispatchRank || "-"],
    ["planSequence", row.PlanSequence],
    ["bufferZone", translate(row.BufferZone)],
    ["penetration", `${Number(row.BufferPenetrationPercent || 0).toFixed(1)}%`],
    ["plannedStart", formatDate(row.ScheduledStart)],
    ["conflictResult", row.ConflictResultLabelZh || translate(row.ConflictResult)],
    ["releaseGate", translate(row.LatestGateStatus) || row.LatestGateStatus],
    ["arrivalStatus", translate(row.ArrivalStatus) || row.ArrivalStatus],
    ["currentExecution", translate(row.ExecutionStatus) || row.ExecutionStatus],
    ["recommendation", translate(row.DispatchRecommendation) || row.DispatchRecommendation],
    ["plannerConfirmation", row.RequiresPlannerConfirmation ? translate("required") : translate("notProvided")]
  ].forEach(([labelKey, value]) => details.append(detailMetric(labelKey, value)));
  card.append(title, details);
  if (row.RecommendationReason) {
    const reason = document.createElement("p");
    reason.className = isWarning ? "inline-warning" : "inline-note";
    reason.textContent = `${translate("recommendationReason")}: ${row.RecommendationReason}`;
    card.append(reason);
  }
  if ((row.PlannerConfirmationReasons || []).length) {
    const note = document.createElement("p");
    note.className = "inline-warning";
    note.textContent = row.PlannerConfirmationReasons.map((reason) => translate(reason) || reason).join(" / ");
    card.append(note);
  }
  if ((row.LatestGateBlockingReasons || []).length) {
    const note = document.createElement("p");
    note.className = "inline-warning";
    note.textContent = row.LatestGateBlockingReasons.map(formatDispatchGateReason).join(" / ");
    card.append(note);
  }
  return card;
}

function formatDispatchGateReason(reason) {
  const code = reason?.Code;
  const base = translate(`reason_${code}`) || displayValue(code);
  if (code === "WIP_LIMIT_EXCEEDED") {
    const risks = Array.isArray(reason?.Details?.Risks) ? reason.Details.Risks : [];
    const evidence = risks.map(formatDispatchWipRisk).filter(Boolean).join("；");
    return evidence ? `${base} ${evidence}` : base;
  }
  if (String(code || "").startsWith("OPERATIONAL_SNAPSHOT_")) {
    return `${base} ${translate("snapshotRefreshAdvice")}`;
  }
  return base;
}

function formatDispatchWipRisk(risk) {
  if (!risk) return "";
  const scope = risk.ScopeID || risk.ResourceID || risk.ItemID || "-";
  const effectiveLimit = risk.EffectiveMaxWipCount ?? risk.MaxWipCount;
  return `${scope}: ${translate("actualWipCount")} ${displayValue(risk.CurrentWipCount)}, ${translate("projectedWipCount")} ${displayValue(risk.ProjectedWipCount)}, ${translate("effectiveMaxWipCount")} ${displayValue(effectiveLimit)}`;
}

async function issueMesDispatchSuggestions() {
  const runId = document.getElementById("dispatch-run-select").value;
  const evaluatedValue = document.getElementById("dispatch-evaluated-at").value;
  const button = document.getElementById("issue-mes-dispatch-suggestions");
  if (!runId || !evaluatedValue || !button) return;
  button.disabled = true;
  try {
    const query = new URLSearchParams({
      evaluated_at: new Date(evaluatedValue).toISOString(),
      issued_by: "planner-1"
    });
    const response = await fetch(`/planner/workbench/mes/dispatch-suggestions/runs/${encodeURIComponent(runId)}/issue?${query}`, { method: "POST" });
    if (!response.ok) throw new Error(String(response.status));
    mesDispatchIssueData = (await response.json()).Data;
    showNotification(translate("dispatchSuggestionIssued"), "success");
  } catch (_error) {
    showNotification(translate("actionFailed"), "error");
  } finally {
    button.disabled = false;
    renderMesDispatchPriority();
  }
}

function emptyDispatchMessage(key) {
  const empty = document.createElement("div");
  empty.className = "table-empty";
  empty.textContent = translate(key);
  return empty;
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

async function loadPublicDemoGoldenLoop() {
  try {
    const response = await fetch("/planner/workbench/public-demo/golden-loop", { headers: { Accept: "application/json" } });
    if (!response.ok) throw new Error(String(response.status));
    publicDemoData = (await response.json()).Data;
    document.getElementById("public-demo-error").hidden = true;
    document.getElementById("public-demo-content").hidden = false;
    renderPublicDemoGoldenLoop();
  } catch (_error) {
    publicDemoData = null;
    document.getElementById("public-demo-error").hidden = false;
    document.getElementById("public-demo-content").hidden = true;
  }
}

async function runPublicDemoGoldenLoop() {
  const button = document.getElementById("run-public-demo");
  if (!button) return;
  button.disabled = true;
  try {
    const response = await fetch("/planner/workbench/public-demo/golden-loop/run", { method: "POST", headers: { Accept: "application/json" } });
    if (!response.ok) throw new Error(String(response.status));
    publicDemoData = (await response.json()).Data;
    renderPublicDemoGoldenLoop();
    showNotification(
      publicDemoData.RunStatus === "Completed" ? translate("publicDemoRunCompleted") : translate("publicDemoRunNotReady"),
      publicDemoData.RunStatus === "Completed" ? "success" : "error"
    );
  } catch (_error) {
    showNotification(translate("actionFailed"), "error");
  } finally {
    button.disabled = false;
  }
}

function renderPublicDemoGoldenLoop() {
  const data = publicDemoData || {};
  const chip = document.getElementById("public-demo-chip");
  const validationStatus = data.Validation?.OverallStatus || data.RunStatus || "NotRun";
  chip.className = `status-chip ${validationStatus === "AcceptedForDemo" || data.RunStatus === "Completed" ? "is-valid" : "neutral"}`;
  chip.textContent = displayValue(validationStatus);
  setText("public-demo-labels", (data.Labels || []).join(" · "));
  const summary = document.getElementById("public-demo-summary");
  summary.replaceChildren(
    detailMetric("packageValidation", data.Package?.Status),
    detailMetric("handoffValidation", data.HandoffInput?.Status),
    detailMetric("productDemoMode", data.ProductDemoMode?.Validation?.OverallStatus),
    detailMetric("contractValidation", validationStatus),
    detailMetric("feedbackHandoff", data.RunStatus || outputCompletionLabel(data.HandoffOutputs))
  );
  renderPublicDemoPackage(data.Package || {});
  renderPublicDemoHandoff(data.HandoffInput || {});
  renderPublicDemoValidation(data.Validation || {});
  renderPublicDemoProductProfile(data.ProductDemoMode || {});
  renderPublicDemoAdapter(data.AdventureWorksSchedulingAdapter || {});
  renderPublicDemoOutputs(data.HandoffOutputs || {});
  const nonClaims = document.getElementById("public-demo-nonclaims");
  nonClaims.replaceChildren(...(data.NonClaims || []).map((claim) => {
    const item = document.createElement("li");
    item.textContent = claim;
    return item;
  }));
  renderPublicDemoBusinessView(data);
}

function renderPublicDemoPackage(packageData) {
  renderKeyValueList("public-demo-package", [
    ["PackageID", packageData.PackageID],
    ["Status", packageData.Status],
    ["PackageChecksum", compactFingerprint(packageData.PackageChecksum)],
    ["ExpectedPackageChecksum", compactFingerprint(packageData.ExpectedPackageChecksum)],
    ["ChecksumMatches", businessValue(packageData.ChecksumMatches)],
    ["CanonicalFileCount", packageData.CanonicalFileCount],
    ["CrosswalkFilePresent", businessValue(packageData.CrosswalkFilePresent)]
  ]);
}

function renderPublicDemoHandoff(handoff) {
  renderKeyValueList("public-demo-handoff", [
    ["Status", handoff.Status],
    ["MessageID", handoff.MessageID],
    ["IdempotencyKey", handoff.IdempotencyKey],
    ["Path", handoff.Path]
  ]);
}

function renderPublicDemoValidation(validation) {
  const rows = [
    ["OverallStatus", validation.OverallStatus],
    ["SchemaValidation", validation.SchemaValidation],
    ["StatusApprovalValidation", validation.StatusApprovalValidation],
    ["FingerprintValidation", validation.FingerprintValidation],
    ["CrosswalkValidation", validation.CrosswalkValidation?.Status],
    ["ConfigAck", validation.ConfigAck?.ProcessingStatus]
  ];
  const container = document.getElementById("public-demo-validation");
  container.replaceChildren();
  rows.forEach(([key, value]) => container.append(keyValueCard(key, value)));
  (validation.ReviewedCandidateMappingHits || []).forEach((hit) => {
    container.append(keyValueCard(hit.CandidateID, `${hit.Hit ? translate("yes") : translate("no")} · ${hit.MappingConfidence || "-"}`));
  });
}

function renderPublicDemoAdapter(adapter) {
  const declarations = adapter.Declarations || {};
  const material = adapter.MaterialConstraints || {};
  const routing = adapter.RoutingPathCoverage || {};
  const resources = adapter.OperationResourceCoverage || {};
  const bounded = adapter.BoundedFixtureScheduling || {};
  const calendarCount = (adapter.CalendarMappings || []).filter((row) => row.MappingStatus === "Explicit").length;
  renderKeyValueList("public-demo-adapter", [
    ["Status", adapter.Status],
    [translate("adapterMode"), adapter.Mode],
    ["AdapterProfileID", adapter.AdapterProfileID],
    ["CapacityUnitNormalizationRuleID", declarations.CapacityUnitNormalizationRuleID],
    ["MaterialConstraintsMode", declarations.MaterialConstraintsMode],
    [translate("materialFeasibleClaim"), businessValue(material.MaterialFeasibleProductionClaim === true)],
    ["SetupChangeoverMode", declarations.SetupChangeoverMode],
    [translate("explicitCalendars"), `${calendarCount} / ${(adapter.CalendarMappings || []).length}`],
    [translate("generatedRows"), `${routing.SelectedFixtureWorkOrderCount || 0} ${translate("orders")} · ${resources.GeneratedOperationCount || 0} ${translate("operations")}`],
    [translate("formalSolverGate"), adapter.FormalSolverGate?.["CP-SAT/OR-Tools"]],
    [translate("generatedPackage"), adapter.GeneratedPackagePath || "-"],
    ["BoundedFixtureScheduling", bounded.Status]
  ]);
}

function renderPublicDemoProductProfile(profile) {
  const authority = profile.DemoAuthority || {};
  const sdbrAuthority = authority.SDBRSchedulingAuthority || {};
  const rowCounts = sdbrAuthority.RowCounts || {};
  const panelPolicy = profile.PanelPolicy || {};
  const setupOmission = sdbrAuthority.SetupChangeoverOmission || {};
  const materialOmission = sdbrAuthority.MaterialFeasibilityOmission || {};
  const validation = profile.Validation || {};
  renderKeyValueList("public-demo-product-profile", [
    [translate("activeProfile"), `${displayValue(profile.ProfileID)} · ${displayValue(profile.Mode)}`],
    [translate("productDemoMode"), `${displayValue(profile.ProductStatus)} · ${displayValue(profile.MappingConfidence)}`],
    [translate("demoAuthority"), `${displayValue(authority.DemoAuthorityPackageID)} · ${displayValue(authority.DemoAuthorityStatus)}`],
    [translate("authorityRows"), formatAuthorityRowCounts(rowCounts)],
    [translate("sourceClassCoverage"), formatSourceClassCoverage(profile.SourceClassCoverage || {})],
    [translate("panelPolicy"), `${translate("productDemoPanels")} ${countList(panelPolicy.ProductDemoModePanels)} · ${translate("placeholderPanels")} ${countList(panelPolicy.PlaceholderPanels)} · ${translate("sampleModePanels")} ${countList(panelPolicy.SampleModeOnlyPanels)}`],
    [translate("setupOmission"), setupOmission.BlockingRule || "-"],
    [translate("materialOmission"), materialOmission.BlockingRule || "-"],
    [translate("validationDeadLetters"), `${(validation.DeadLetters || []).length} · ${displayValue(validation.OverallStatus)}`]
  ]);
}

function renderPublicDemoOutputs(outputs) {
  const rows = Object.entries(outputs).map(([name, value]) => [
    name,
    `${value.Exists ? translate("yes") : translate("no")} · ${value.SizeBytes || 0} B`
  ]);
  renderKeyValueList("public-demo-outputs", rows);
}

function formatAuthorityRowCounts(rowCounts) {
  const keys = ["Calendars", "CapacityWindows", "ExecutableRoutingRows", "OperationDurations", "WorkOrderReleaseCandidates", "SchedulingObjectivePolicies", "DispatchHorizons"];
  return keys.map((key) => `${key} ${rowCounts[key] || 0}`).join(" · ");
}

function formatSourceClassCoverage(coverage) {
  const entries = Object.entries(coverage || {});
  if (!entries.length) return "-";
  return entries.map(([key, value]) => `${key} ${value}`).join(" · ");
}

function countList(values) {
  return Array.isArray(values) ? values.length : 0;
}

function renderKeyValueList(elementId, rows) {
  const container = document.getElementById(elementId);
  container.replaceChildren(...rows.map(([key, value]) => keyValueCard(key, value)));
}

function keyValueCard(label, value) {
  const card = document.createElement("div");
  card.className = "policy-group-item";
  const title = document.createElement("strong");
  title.textContent = label;
  const text = document.createElement("span");
  text.textContent = displayValue(value);
  card.append(title, text);
  return card;
}

function outputCompletionLabel(outputs) {
  const values = Object.values(outputs || {});
  return values.length && values.every((item) => item.Exists) ? "Completed" : "NotGenerated";
}

function renderPublicDemoBusinessView(data) {
  const adapter = data.AdventureWorksSchedulingAdapter || {};
  const declarations = adapter.Declarations || {};
  const material = adapter.MaterialConstraints || {};
  const routing = adapter.RoutingPathCoverage || {};
  const resources = adapter.OperationResourceCoverage || {};
  const validation = data.Validation || {};
  const outputs = data.HandoffOutputs || {};
  const calendarCount = (adapter.CalendarMappings || []).filter((row) => row.MappingStatus === "Explicit").length;
  const outputNames = Object.entries(outputs)
    .filter(([, value]) => value?.Exists)
    .map(([name]) => name);
  const steps = currentLanguage === "zh"
    ? [
        {
          title: "1. SDBR 收到了什么",
          body: `SDBR 收到 DDAE 的配置/运行交接和公开演示数据包，用于判断这次受控演示能否进入 SDBR 执行侧校验。数据包状态：${displayValue(data.Package?.Status)}；交接状态：${displayValue(data.HandoffInput?.Status)}。`,
          trace: `追溯：${displayValue(data.Package?.PackageID)} · ${displayValue(data.HandoffInput?.MessageID)}`
        },
        {
          title: "2. SDBR 校验了什么",
          body: `SDBR 检查 schema、审批状态、指纹、crosswalk 和配置 ACK，用业务话说就是确认“这份交接是否可信、是否可用于本次演示”。当前校验结果：${displayValue(validation.OverallStatus)}。`,
          trace: `Schema ${displayValue(validation.SchemaValidation)} · Fingerprint ${displayValue(validation.FingerprintValidation)} · Crosswalk ${displayValue(validation.CrosswalkValidation?.Status)}`
        },
        {
          title: "3. SDBR 为演示转换了什么",
          body: `SDBR 使用 AdventureWorks Adapter 把公开演示数据转换为有界演示排程输入：${routing.SelectedFixtureWorkOrderCount || 0} 个代表性演示工单、${resources.GeneratedOperationCount || 0} 道工序、${calendarCount} 个 SDBR 自有资源日历。`,
          trace: `模式：${displayValue(adapter.Mode)} · Adapter：${displayValue(adapter.AdapterProfileID)}`
        },
        {
          title: "4. SDBR 没有声明什么",
          body: `本演示不声明物料可行性生产排程，不声明完整生产 routing 权威，也不打开正式 CP-SAT / OR-Tools 生产入口。物料可行性生产声明：${businessValue(material.MaterialFeasibleProductionClaim === true)}。`,
          trace: `MaterialConstraintsMode=${displayValue(declarations.MaterialConstraintsMode)} · MaterialConstraints=[] · Formal solver=${displayValue(adapter.FormalSolverGate?.["CP-SAT/OR-Tools"])}`
        },
        {
          title: "5. SDBR 回传了什么",
          body: `SDBR 回传 PlanningRunFeedback、VarianceAnalysisFeedback 和 ValidationSummary，供 DDAE 做治理复核。这些反馈不会自动修改 DDAE 已批准主设置。`,
          trace: `已生成：${outputNames.length ? outputNames.join(" · ") : "尚未生成反馈文件"}`
        }
      ]
    : [
        {
          title: "1. What SDBR received",
          body: `SDBR receives the DDAE configuration/runtime handoff and the public demo package to decide whether this controlled demo can enter execution-side validation. Package status: ${displayValue(data.Package?.Status)}; handoff status: ${displayValue(data.HandoffInput?.Status)}.`,
          trace: `Traceability: ${displayValue(data.Package?.PackageID)} · ${displayValue(data.HandoffInput?.MessageID)}`
        },
        {
          title: "2. What SDBR validated",
          body: `SDBR checks schema, approval status, fingerprint, crosswalk, and config ACK. In business terms, this answers whether the handoff is trustworthy and usable for this demo. Current validation result: ${displayValue(validation.OverallStatus)}.`,
          trace: `Schema ${displayValue(validation.SchemaValidation)} · Fingerprint ${displayValue(validation.FingerprintValidation)} · Crosswalk ${displayValue(validation.CrosswalkValidation?.Status)}`
        },
        {
          title: "3. What SDBR converted for the demo",
          body: `SDBR uses the AdventureWorks adapter to convert the public demo data into bounded demo scheduling input: ${routing.SelectedFixtureWorkOrderCount || 0} representative demo work orders, ${resources.GeneratedOperationCount || 0} operations, and ${calendarCount} SDBR-owned resource calendars.`,
          trace: `Mode: ${displayValue(adapter.Mode)} · Adapter: ${displayValue(adapter.AdapterProfileID)}`
        },
        {
          title: "4. What SDBR does not claim",
          body: `This demo does not claim material-feasible production scheduling, full production routing authority, or formal CP-SAT / OR-Tools production entry. Material-feasible production claim: ${businessValue(material.MaterialFeasibleProductionClaim === true)}.`,
          trace: `MaterialConstraintsMode=${displayValue(declarations.MaterialConstraintsMode)} · MaterialConstraints=[] · Formal solver=${displayValue(adapter.FormalSolverGate?.["CP-SAT/OR-Tools"])}`
        },
        {
          title: "5. What SDBR sent back",
          body: `SDBR sends PlanningRunFeedback, VarianceAnalysisFeedback, and ValidationSummary back to DDAE for governance review. These feedback records do not automatically mutate approved DDAE master settings.`,
          trace: `Generated: ${outputNames.length ? outputNames.join(" · ") : "No feedback files generated yet"}`
        }
      ];
  const list = document.getElementById("public-demo-business-steps");
  list.replaceChildren(...steps.map((step) => {
    const item = document.createElement("li");
    const title = document.createElement("strong");
    title.textContent = step.title;
    const body = document.createElement("p");
    body.textContent = step.body;
    const trace = document.createElement("small");
    trace.textContent = step.trace;
    item.append(title, body, trace);
    return item;
  }));
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

async function loadCalendarPreview() {
  const resourceId = document.getElementById("calendar-preview-resource").value.trim();
  const startDate = document.getElementById("calendar-preview-start").value;
  const endDate = document.getElementById("calendar-preview-end").value;
  try {
    const query = new URLSearchParams({ StartDate: startDate, EndDate: endDate, Timezone: "UTC" });
    if (resourceId) query.set("ResourceID", resourceId);
    const response = await fetch(`/planner/workbench/calendar/preview?${query}`, { headers: { Accept: "application/json" } });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    calendarPreviewData = (await response.json()).Data;
    renderCalendarPreview();
    document.getElementById("calendar-preview-error").hidden = true;
    document.getElementById("calendar-preview-content").hidden = false;
  } catch (_error) {
    calendarPreviewData = null;
    document.getElementById("calendar-preview-error").hidden = false;
    document.getElementById("calendar-preview-content").hidden = true;
    setText("calendar-preview-chip", translate("unavailable"));
  }
}

async function loadCalendarWorkspace() {
  await loadCalendarConfiguration();
  await loadCalendarPreview();
}

async function loadCalendarConfiguration() {
  const [resourcesResponse, baseCalendarsResponse, calendarAssignmentsResponse, calendarOverridesResponse] = await Promise.all([
    fetch("/planner/workbench/calendar/resources", { headers: { Accept: "application/json" } }),
    fetch("/planner/workbench/admin/base-calendars", { headers: { Accept: "application/json" } }),
    fetch("/planner/workbench/admin/resource-calendar-assignments", { headers: { Accept: "application/json" } }),
    fetch("/planner/workbench/admin/calendar-overrides", { headers: { Accept: "application/json" } })
  ]);
  if (!resourcesResponse.ok) throw new Error(`HTTP ${resourcesResponse.status}`);
  if (!baseCalendarsResponse.ok) throw new Error(`HTTP ${baseCalendarsResponse.status}`);
  if (!calendarAssignmentsResponse.ok) throw new Error(`HTTP ${calendarAssignmentsResponse.status}`);
  if (!calendarOverridesResponse.ok) throw new Error(`HTTP ${calendarOverridesResponse.status}`);
  const resourcesPayload = await resourcesResponse.json();
  const baseCalendarsPayload = await baseCalendarsResponse.json();
  const calendarAssignmentsPayload = await calendarAssignmentsResponse.json();
  const calendarOverridesPayload = await calendarOverridesResponse.json();
  calendarResourcesData = resourcesPayload.Data?.Resources || [];
  baseCalendarsData = baseCalendarsPayload.Data?.Calendars || [];
  resourceCalendarAssignmentsData = calendarAssignmentsPayload.Data?.Assignments || [];
  calendarOverridesData = calendarOverridesPayload.Data?.Overrides || [];
  renderCalendarConfiguration();
}

function renderCalendarConfiguration() {
  updateCalendarGeneratedIds();
  renderCalendarSelects();
  renderCalendarMiniList("calendar-page-base-calendars", baseCalendarsData, (item) => [
    item.CalendarID,
    item.DisplayName || translate("notProvided"),
    `${translate("status")}: ${translate(item.Status) || item.Status}`,
    `${translate("timezone")}: ${item.Timezone || translate("notProvided")}`,
    `${translate("workingWeekdays")}: ${(item.WorkingWeekdays || []).join(", ")}`,
    `${translate("shiftName")}: ${(item.Shifts || []).map((shift) => `${shift.Name} ${shift.Start}-${shift.End}`).join(" / ") || "-"}`
  ]);
  renderCalendarMiniList("calendar-page-assignments", resourceCalendarAssignmentsData, (item) => [
    item.AssignmentID,
    `${translate("resource")}: ${item.ResourceID}`,
    `${translate("calendarId")}: ${item.CalendarID}`,
    `${translate("status")}: ${translate(item.Status) || item.Status}`
  ]);
  renderCalendarMiniList("calendar-page-overrides", calendarOverridesData, (item) => [
    item.OverrideID,
    `${translate("overrideType")}: ${translate(item.OverrideType) || item.OverrideType}`,
    `${translate("resource")}: ${item.ResourceID || translate("notProvided")}`,
    `${formatDate(item.EffectiveStartAt)} - ${formatDate(item.EffectiveEndAt)}`
  ]);
}

function updateCalendarGeneratedIds(force = false) {
  const stamp = new Date().toISOString().replace(/[-:.TZ]/g, "").slice(0, 17);
  const idFields = [
    ["calendar-page-base-calendar-id", `CAL-${stamp}`],
    ["calendar-page-assignment-id", `CAL-ASG-${stamp}`],
    ["calendar-page-override-id", `CAL-OVR-${stamp}`]
  ];
  idFields.forEach(([id, value]) => {
    const input = document.getElementById(id);
    if (input && (force || !input.value)) input.value = value;
  });
}

function renderCalendarSelects() {
  const resources = calendarResourcesData.map((item) => ({
    ResourceID: item.ResourceID,
    ResourceName: item.ResourceName || item.ResourceID
  }));
  const calendars = baseCalendarsData.map((item) => ({
    CalendarID: item.CalendarID,
    DisplayName: item.DisplayName || item.CalendarID
  }));
  replaceSelectOptions(document.getElementById("calendar-preview-resource"), resources, { valueKey: "ResourceID", labelKey: "ResourceName" });
  replaceSelectOptions(document.getElementById("calendar-page-assignment-resource-id"), resources, { valueKey: "ResourceID", labelKey: "ResourceName" });
  replaceSelectOptions(document.getElementById("calendar-page-override-resource-id"), resources, { allKey: "notSelected", valueKey: "ResourceID", labelKey: "ResourceName" });
  replaceSelectOptions(document.getElementById("calendar-page-assignment-calendar-id"), calendars, { valueKey: "CalendarID", labelKey: "DisplayName" });
  replaceSelectOptions(document.getElementById("calendar-page-override-calendar-id"), calendars, { valueKey: "CalendarID", labelKey: "DisplayName" });
}

function renderCalendarMiniList(containerId, rows, rowTextFactory) {
  const container = document.getElementById(containerId);
  container.replaceChildren();
  if (!rows.length) {
    const empty = document.createElement("p");
    empty.className = "inline-note";
    empty.textContent = translate("noCalendarConfigRows");
    container.append(empty);
    return;
  }
  rows.forEach((item) => {
    const row = document.createElement("div");
    row.className = "calendar-mini-row";
    rowTextFactory(item).forEach((text, index) => {
      const value = document.createElement(index === 0 ? "strong" : "span");
      value.textContent = displayValue(text);
      row.append(value);
    });
    container.append(row);
  });
}

function renderCalendarPreview() {
  if (!calendarPreviewData) return;
  setText("calendar-preview-chip", `${calendarPreviewData.MasterDataVersionID || "-"} · ${calendarPreviewData.Timezone || "UTC"}`);
  renderCalendarRequiredElements();
  renderCalendarSummary();
  renderCalendarFinalWindows();
  renderCalendarSourceElements();
}

function renderCalendarRequiredElements() {
  const container = document.getElementById("calendar-required-elements");
  container.replaceChildren();
  (calendarPreviewData.RequiredElements || []).forEach((item) => {
    const card = document.createElement("article");
    card.className = "calendar-element-card";
    const title = document.createElement("h3");
    title.textContent = item.Element || item.ElementID;
    const reason = document.createElement("p");
    reason.innerHTML = `<strong>${translate("cpSatNeedReason")}:</strong> ${displayValue(item.CpSatNeedReason)}`;
    const impact = document.createElement("p");
    impact.innerHTML = `<strong>${translate("missingImpactDomain")}:</strong> ${displayValue(item.MissingImpactDomain)}`;
    card.append(title, reason, impact);
    container.append(card);
  });
}

function renderCalendarSummary() {
  const container = document.getElementById("calendar-preview-summary");
  container.replaceChildren();
  const summary = calendarPreviewData.Summary || {};
  [
    ["resources", summary.ResourceCount],
    ["baseCalendars", summary.ActiveBaseCalendarCount],
    ["calendarAssignment", summary.ActiveAssignmentCount],
    ["calendarOverrides", summary.ActiveOverrideCount],
    ["finalWindowCount", summary.FinalWindowCount],
    ["missingDailyCapacityDates", summary.MissingDailyCapacityDateCount]
  ].forEach(([labelKey, value]) => {
    const item = document.createElement("div");
    item.innerHTML = `<span>${translate(labelKey)}</span><strong>${displayValue(value)}</strong>`;
    container.append(item);
  });
}

function renderCalendarFinalWindows() {
  const container = document.getElementById("calendar-final-windows");
  container.replaceChildren();
  const rows = (calendarPreviewData.Resources || []).flatMap((resource) =>
    (resource.FinalCapacityWindows || []).map((window) => ({ ...window, ResourceID: resource.ResourceID }))
  );
  if (!rows.length) {
    const empty = document.createElement("div");
    empty.className = "table-empty";
    empty.textContent = translate("noCalendarWindows");
    container.append(empty);
    return;
  }
  rows.forEach((window) => {
    const card = document.createElement("article");
    card.className = "calendar-window-card";
    card.append(detailSection("finalCapacityWindows", [
      ["resource", window.ResourceID],
      ["start", formatDate(window.Start)],
      ["end", formatDate(window.End)],
      ["availableCapacity", `${window.CapacityMinutes} ${translate("minutes")}`]
    ]));
    container.append(card);
  });
}

function renderCalendarSourceElements() {
  const container = document.getElementById("calendar-source-elements");
  container.replaceChildren();
  const resources = calendarPreviewData.Resources || [];
  if (!resources.length) {
    const empty = document.createElement("div");
    empty.className = "table-empty";
    empty.textContent = translate("noCalendarElements");
    container.append(empty);
    return;
  }
  resources.forEach((resource) => {
    const card = document.createElement("article");
    card.className = "calendar-source-card";
    const heading = document.createElement("div");
    heading.className = "calendar-override-heading";
    heading.innerHTML = `<strong>${resource.ResourceID}</strong><span class="status-chip neutral">${displayValue(resource.CalendarID)}</span>`;
    const missingNote = document.createElement("p");
    missingNote.className = "inline-note";
    missingNote.textContent = resource.MissingDailyCapacityDates?.length
      ? `${translate("missingDailyCapacityDates")}: ${resource.MissingDailyCapacityDates.join(", ")}`
      : `${translate("missingDailyCapacityDates")}: 0`;
    card.append(heading, missingNote);
    (resource.Elements || []).forEach((item) => {
      const row = document.createElement("div");
      row.className = "calendar-source-row";
      row.append(detailSection("appliedCalendarElements", [
        ["elementType", translate(String(item.ElementType || ""))],
        ["sourceId", item.SourceID || item.CalendarID || "-"],
        ["status", translate(String(item.Status || (item.Applied ? "Applied" : "NotApplied")))],
        ["start", item.Start ? formatDate(item.Start) : displayValue(item.Date || item.ShiftName)],
        ["end", item.End ? formatDate(item.End) : displayValue(item.CapacityMinutes || item.CapacityDeltaMinutes)]
      ]));
      card.append(row);
    });
    if (!(resource.Elements || []).length) {
      const empty = document.createElement("p");
      empty.className = "inline-note";
      empty.textContent = translate("noCalendarElements");
      card.append(empty);
    }
    container.append(card);
  });
}

async function loadAdministration() {
  try {
    const [administrationResponse, cpSatResponse, baseCalendarsResponse, calendarAssignmentsResponse, calendarOverridesResponse, simioTemplatesResponse] = await Promise.all([
      fetch("/planner/workbench/administration/workbench", { headers: { Accept: "application/json" } }),
      fetch("/planner/workbench/admin/cp-sat/assumptions", { headers: { Accept: "application/json" } }),
      fetch("/planner/workbench/admin/base-calendars", { headers: { Accept: "application/json" } }),
      fetch("/planner/workbench/admin/resource-calendar-assignments", { headers: { Accept: "application/json" } }),
      fetch("/planner/workbench/admin/calendar-overrides", { headers: { Accept: "application/json" } }),
      fetch("/planner/workbench/simio/templates", { headers: { Accept: "application/json" } })
    ]);
    if (!administrationResponse.ok) throw new Error(`HTTP ${administrationResponse.status}`);
    if (!cpSatResponse.ok) throw new Error(`HTTP ${cpSatResponse.status}`);
    if (!baseCalendarsResponse.ok) throw new Error(`HTTP ${baseCalendarsResponse.status}`);
    if (!calendarAssignmentsResponse.ok) throw new Error(`HTTP ${calendarAssignmentsResponse.status}`);
    if (!calendarOverridesResponse.ok) throw new Error(`HTTP ${calendarOverridesResponse.status}`);
    if (!simioTemplatesResponse.ok) throw new Error(`HTTP ${simioTemplatesResponse.status}`);
    const administrationPayload = await administrationResponse.json();
    const cpSatPayload = await cpSatResponse.json();
    const baseCalendarsPayload = await baseCalendarsResponse.json();
    const calendarAssignmentsPayload = await calendarAssignmentsResponse.json();
    const calendarOverridesPayload = await calendarOverridesResponse.json();
    const simioTemplatesPayload = await simioTemplatesResponse.json();
    administrationData = { ...administrationPayload.Data, CpSatAssumptions: cpSatPayload.Data, SimioTemplates: simioTemplatesPayload.Data };
    baseCalendarsData = baseCalendarsPayload.Data?.Calendars || [];
    resourceCalendarAssignmentsData = calendarAssignmentsPayload.Data?.Assignments || [];
    calendarOverridesData = calendarOverridesPayload.Data?.Overrides || [];
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
  setText("admin-mode-chip", translate("partialEditable"));
  renderAdminObjects(administrationData.MasterDataObjects || []);
  renderAdminCapabilities(administrationData);
  renderAdminSimioTemplates(administrationData.SimioTemplates);
  renderAdminCpSatAssumptions(administrationData.CpSatAssumptions);
  renderAdminPolicyGroups(administrationData.PolicyGroups || []);
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

function simioTemplateStatusLabel(value) {
  if (value === "PendingManualCheck") return translate("pendingManualCheck");
  return translate(value) || displayValue(value);
}

function renderAdminSimioTemplates(data) {
  const container = document.getElementById("admin-simio-templates");
  if (!container) return;
  container.replaceChildren();
  if (!data) {
    container.append(detailSection("simioTemplateRegistry", [["statusUnavailable", translate("notAvailable")]]));
    return;
  }
  const active = data.ActiveTemplate || {};
  const status = data.Status || "Unavailable";
  const templateCount = data.TemplateCount ?? (data.Templates || []).length;
  const rows = [
    ["templateStatus", simioTemplateStatusLabel(status)],
    ["activeSimioTemplate", displayValue(active.TemplateID)],
    ["templateVersion", displayValue(active.TemplateVersion)],
    ["timeUnitPolicy", displayValue(active.TimeUnitPolicy)],
    ["desktopValidationStatus", simioTemplateStatusLabel(active.DesktopValidationStatus)],
    ["configuredTemplates", templateCount]
  ];
  const section = detailSection("simioTemplateRegistry", rows);
  const message = document.createElement("p");
  message.className = status === "Ready" ? "inline-note" : "inline-warning";
  message.textContent = status === "Ready" ? translate("templateReady") : translate("templateNeedsAttention");
  section.append(message);
  section.append(collapsibleDetailSection("technicalDetails", [
    ["templateName", displayValue(active.TemplateName)],
    ["templatePath", displayValue(active.TemplatePath)],
    ["templateSourceType", displayValue(active.TemplateSourceType)],
    ["defaultTemplateDirectory", displayValue(data.TemplatePolicy?.DefaultDirectory)],
    ["runtimeRule", displayValue(data.TemplatePolicy?.RuntimeRule)],
    ["timeUnitRule", displayValue(data.TemplatePolicy?.TimeUnitRule)]
  ]));
  container.append(section);
}

function renderAdminCpSatAssumptions(data) {
  const container = document.getElementById("admin-cp-sat-assumptions");
  container.replaceChildren();
  if (!data) {
    container.append(detailSection("cpSatAssumptions", [["statusUnavailable", translate("notAvailable")]]));
    return;
  }
  const assumptions = (data.ModelingAssumptions || [])
    .map((item) => `${item.AssumptionID}: ${currentLanguage === "zh" && item.DescriptionZh ? item.DescriptionZh : item.Description}`)
    .join("\n");
  const parameters = (data.TunableParameters || [])
    .map((item) => `${item.ParameterID} · ${translate("driverStatus")}: ${translate(item.DriverStatus) || item.DriverStatus}`)
    .join("\n");
  const deferred = (data.DeferredRules || []).join(" / ");
  [
    ["cpSatAssumptions", assumptions],
    ["tunableParameters", parameters],
    ["deferredRules", deferred]
  ].forEach(([key, value]) => {
    const row = document.createElement("div");
    row.className = "policy-group";
    const title = document.createElement("strong");
    title.textContent = translate(key);
    const values = document.createElement("span");
    values.textContent = value || "-";
    row.append(title, values);
    container.append(row);
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
  const config = administrationData?.CalendarConfiguration || {};
  const ruleRows = [
    ["calendarScope", translate(config.CalendarScope || "ResourceOnly")],
    ["conflictPriority", (config.ConflictPriority || []).map((item) => translate(item) || item).join(" > ")],
    ["ApprovalFlowStatus", translate(config.ApprovalFlowStatus || "StatusOnly")]
  ];
  ruleRows.forEach(([labelKey, value]) => {
    const item = document.createElement("div");
    item.className = "calendar-layer";
    const label = document.createElement("strong");
    label.textContent = translate(labelKey);
    const detail = document.createElement("span");
    detail.textContent = value || "-";
    item.append(label, detail);
    container.append(item);
  });
}

function renderBaseCalendars() {
  const container = document.getElementById("admin-base-calendars");
  container.replaceChildren();
  if (!baseCalendarsData.length) {
    const empty = document.createElement("div");
    empty.className = "table-empty";
    empty.textContent = translate("noBaseCalendars");
    container.append(empty);
    return;
  }
  baseCalendarsData.forEach((item) => {
    const card = document.createElement("section");
    card.className = "calendar-override-card";
    const heading = document.createElement("div");
    heading.className = "calendar-override-heading";
    const title = document.createElement("strong");
    title.textContent = `${item.CalendarID}${item.DisplayName ? ` · ${item.DisplayName}` : ""}`;
    const status = document.createElement("span");
    status.className = `status-chip ${item.Status === "Active" ? "is-valid" : "neutral"}`;
    status.textContent = `${translate(item.Status) || item.Status} · ${translate(item.SolverDriverStatus) || item.SolverDriverStatus}`;
    heading.append(title, status);
    card.append(heading, detailSection("baseCalendars", [
      ["workingWeekdays", (item.WorkingWeekdays || []).join(", ")],
      ["shiftName", (item.Shifts || []).map((shift) => `${shift.Name} ${shift.Start}-${shift.End}`).join(" / ") || "-"],
      ["maintenance", (item.MaintenanceWindows || []).length],
      ["createdBy", item.CreatedBy || translate("notProvided")]
    ]));
    container.append(card);
  });
}

function renderResourceCalendarAssignments() {
  const container = document.getElementById("admin-resource-calendar-assignments");
  container.replaceChildren();
  if (!resourceCalendarAssignmentsData.length) {
    const empty = document.createElement("div");
    empty.className = "table-empty";
    empty.textContent = translate("noCalendarAssignments");
    container.append(empty);
    return;
  }
  resourceCalendarAssignmentsData.forEach((item) => {
    const card = document.createElement("section");
    card.className = "calendar-override-card";
    const heading = document.createElement("div");
    heading.className = "calendar-override-heading";
    const title = document.createElement("strong");
    title.textContent = item.AssignmentID;
    const status = document.createElement("span");
    status.className = `status-chip ${item.Status === "Active" ? "is-valid" : "neutral"}`;
    status.textContent = `${translate(item.Status) || item.Status} · ${translate(item.SolverDriverStatus) || item.SolverDriverStatus}`;
    heading.append(title, status);
    card.append(heading, detailSection("calendarAssignment", [
      ["resource", item.ResourceID],
      ["calendarId", item.CalendarID],
      ["createdBy", item.CreatedBy || translate("notProvided")]
    ]));
    container.append(card);
  });
}

function renderCalendarOverrides() {
  const container = document.getElementById("admin-calendar-overrides");
  container.replaceChildren();
  if (!calendarOverridesData.length) {
    const empty = document.createElement("div");
    empty.className = "table-empty";
    empty.textContent = translate("noCalendarOverrides");
    container.append(empty);
    return;
  }
  calendarOverridesData.forEach((item) => {
    const card = document.createElement("section");
    card.className = "calendar-override-card";
    const heading = document.createElement("div");
    heading.className = "calendar-override-heading";
    const title = document.createElement("strong");
    title.textContent = item.OverrideID;
    const status = document.createElement("span");
    status.className = `status-chip ${item.Status === "Active" ? "is-valid" : "neutral"}`;
    status.textContent = translate(item.Status) || item.Status;
    heading.append(title, status);
    card.append(heading, detailSection("calendarOverride", [
      ["calendarId", item.CalendarID],
      ["resource", item.ResourceID || translate("notProvided")],
      ["overrideType", translate(item.OverrideType)],
      ["effectiveStart", formatDate(item.EffectiveStartAt)],
      ["effectiveEnd", formatDate(item.EffectiveEndAt)],
      ["capacityDelta", item.CapacityDeltaMinutes],
      ["reason", item.Reason || translate("notProvided")]
    ]));
    container.append(card);
  });
}

function weekdaysFromInput(id) {
  return document.getElementById(id).value
    .split(",")
    .map((item) => Number(item.trim()))
    .filter((item) => Number.isInteger(item) && item >= 0 && item <= 6);
}

function weekdaysFromCalendarCheckboxes() {
  return [...document.querySelectorAll("[data-calendar-weekday]:checked")]
    .map((item) => Number(item.value))
    .filter((item) => Number.isInteger(item) && item >= 0 && item <= 6);
}

function shiftPayloadFromInputs(nameId, startId, endId) {
  const name = document.getElementById(nameId).value.trim();
  const start = document.getElementById(startId).value;
  const end = document.getElementById(endId).value;
  if (!start || !end) return null;
  return { Name: name || "Shift", Start: `${start}:00`, End: `${end}:00` };
}

function localInputValueToIso(id) {
  const value = document.getElementById(id).value;
  return value ? new Date(value).toISOString() : null;
}

async function submitCalendarPageBaseCalendar(event) {
  event.preventDefault();
  const shifts = [
    shiftPayloadFromInputs("calendar-page-shift1-name", "calendar-page-shift1-start", "calendar-page-shift1-end"),
    shiftPayloadFromInputs("calendar-page-shift2-name", "calendar-page-shift2-start", "calendar-page-shift2-end")
  ].filter(Boolean);
  const maintenanceStart = localInputValueToIso("calendar-page-maintenance-start");
  const maintenanceEnd = localInputValueToIso("calendar-page-maintenance-end");
  const holidayDate = document.getElementById("calendar-page-holiday-date").value;
  const payload = {
    CalendarID: document.getElementById("calendar-page-base-calendar-id").value.trim(),
    DisplayName: document.getElementById("calendar-page-base-calendar-name").value.trim() || null,
    WorkingWeekdays: weekdaysFromCalendarCheckboxes(),
    Shifts: shifts,
    MaintenanceWindows: maintenanceStart && maintenanceEnd ? [{ Start: maintenanceStart, End: maintenanceEnd }] : [],
    Holidays: holidayDate ? [holidayDate] : [],
    Timezone: document.getElementById("calendar-page-base-timezone").value.trim() || "Asia/Shanghai",
    CreatedAt: new Date().toISOString(),
    CreatedBy: "planner",
    Status: document.getElementById("calendar-page-base-status").value
  };
  const response = await fetch("/planner/workbench/admin/base-calendars", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });
  if (!response.ok) {
    showNotification(translate("baseCalendarFailed"), "error");
    return;
  }
  showNotification(translate("baseCalendarCreated"), "success");
  updateCalendarGeneratedIds(true);
  await loadCalendarWorkspace();
}

async function submitCalendarPageAssignment(event) {
  event.preventDefault();
  const payload = {
    AssignmentID: document.getElementById("calendar-page-assignment-id").value.trim(),
    ResourceID: document.getElementById("calendar-page-assignment-resource-id").value.trim(),
    CalendarID: document.getElementById("calendar-page-assignment-calendar-id").value.trim(),
    CreatedAt: new Date().toISOString(),
    CreatedBy: "planner",
    Status: document.getElementById("calendar-page-assignment-status").value
  };
  const response = await fetch("/planner/workbench/admin/resource-calendar-assignments", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });
  if (!response.ok) {
    showNotification(translate("calendarAssignmentFailed"), "error");
    return;
  }
  showNotification(translate("calendarAssignmentCreated"), "success");
  document.getElementById("calendar-preview-resource").value = payload.ResourceID;
  updateCalendarGeneratedIds(true);
  await loadCalendarWorkspace();
}

async function submitBaseCalendar(event) {
  event.preventDefault();
  const payload = {
    CalendarID: document.getElementById("base-calendar-id").value.trim(),
    DisplayName: document.getElementById("base-calendar-name").value.trim() || null,
    WorkingWeekdays: weekdaysFromInput("base-calendar-weekdays"),
    Shifts: [{
      Name: document.getElementById("base-calendar-shift-name").value.trim() || "Day",
      Start: `${document.getElementById("base-calendar-shift-start").value}:00`,
      End: `${document.getElementById("base-calendar-shift-end").value}:00`
    }],
    MaintenanceWindows: [],
    Holidays: [],
    Timezone: "Asia/Shanghai",
    CreatedAt: new Date().toISOString(),
    CreatedBy: "planner",
    Status: "Active"
  };
  const response = await fetch("/planner/workbench/admin/base-calendars", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });
  if (!response.ok) {
    showNotification(translate("baseCalendarFailed"), "error");
    return;
  }
  showNotification(translate("baseCalendarCreated"), "success");
  await loadAdministration();
}

async function submitResourceCalendarAssignment(event) {
  event.preventDefault();
  const payload = {
    AssignmentID: document.getElementById("calendar-assignment-id").value.trim(),
    ResourceID: document.getElementById("calendar-assignment-resource-id").value.trim(),
    CalendarID: document.getElementById("calendar-assignment-calendar-id").value.trim(),
    CreatedAt: new Date().toISOString(),
    CreatedBy: "planner",
    Status: "Active"
  };
  const response = await fetch("/planner/workbench/admin/resource-calendar-assignments", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });
  if (!response.ok) {
    showNotification(translate("calendarAssignmentFailed"), "error");
    return;
  }
  showNotification(translate("calendarAssignmentCreated"), "success");
  await loadAdministration();
}

function localInputToIso(id) {
  const value = document.getElementById(id).value;
  return value ? new Date(value).toISOString() : null;
}

async function submitCalendarPageOverride(event) {
  event.preventDefault();
  const payload = {
    OverrideID: document.getElementById("calendar-page-override-id").value.trim(),
    CalendarID: document.getElementById("calendar-page-override-calendar-id").value.trim(),
    ResourceID: document.getElementById("calendar-page-override-resource-id").value.trim() || null,
    OverrideType: document.getElementById("calendar-page-override-type").value,
    EffectiveStartAt: localInputValueToIso("calendar-page-override-start"),
    EffectiveEndAt: localInputValueToIso("calendar-page-override-end"),
    CapacityDeltaMinutes: Number(document.getElementById("calendar-page-override-capacity").value || 0),
    ShiftName: null,
    Reason: document.getElementById("calendar-page-override-reason").value.trim() || null,
    CreatedAt: new Date().toISOString(),
    CreatedBy: "planner",
    Status: "Active"
  };
  const response = await fetch("/planner/workbench/admin/calendar-overrides", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });
  if (!response.ok) {
    showNotification(translate("calendarOverrideFailed"), "error");
    return;
  }
  showNotification(translate("calendarOverrideCreated"), "success");
  if (payload.ResourceID) document.getElementById("calendar-preview-resource").value = payload.ResourceID;
  updateCalendarGeneratedIds(true);
  await loadCalendarWorkspace();
}

async function submitCalendarOverride(event) {
  event.preventDefault();
  const payload = {
    OverrideID: document.getElementById("calendar-override-id").value.trim(),
    CalendarID: document.getElementById("calendar-id").value.trim(),
    ResourceID: document.getElementById("calendar-resource-id").value.trim() || null,
    OverrideType: document.getElementById("calendar-override-type").value,
    EffectiveStartAt: localInputToIso("calendar-effective-start"),
    EffectiveEndAt: localInputToIso("calendar-effective-end"),
    CapacityDeltaMinutes: Number(document.getElementById("calendar-capacity-delta").value || 0),
    ShiftName: document.getElementById("calendar-shift-name").value.trim() || null,
    Reason: document.getElementById("calendar-reason").value.trim() || null,
    CreatedAt: new Date().toISOString(),
    CreatedBy: "planner",
    Status: "Active"
  };
  const response = await fetch("/planner/workbench/admin/calendar-overrides", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });
  if (!response.ok) {
    showNotification(translate("calendarOverrideFailed"), "error");
    return;
  }
  showNotification(translate("calendarOverrideCreated"), "success");
  await loadAdministration();
}

function orderCommitmentLabel(value) {
  if (value === null || value === undefined || value === "") {
    return translate("notProvided");
  }
  return Object.hasOwn(I18N[currentLanguage], String(value))
    ? I18N[currentLanguage][String(value)]
    : translate("unknownStatus");
}

function orderCommitmentLoadLabel(before, after, percent) {
  const beforeText = before === null || before === undefined ? "-" : `${formatNumber(before)} min`;
  const afterText = after === null || after === undefined ? "-" : `${formatNumber(after)} min`;
  const percentText = percent === null || percent === undefined ? "-" : `${formatNumber(percent)}%`;
  return `${beforeText} / ${afterText} (${percentText})`;
}

function orderCommitmentRows() {
  return Array.isArray(orderCommitmentData?.Rows) ? orderCommitmentData.Rows : [];
}

function renderOrderCommitmentSummary(summary) {
  [
    "AwaitingDecisionCount", "ConfirmationRequiredCount", "MaterialPendingCount",
    "AcceptedPendingScheduleCount"
  ].forEach((key) => {
    const element = document.querySelector(`[data-order-commitment-summary="${key}"]`);
    if (element) element.textContent = formatNumber(summary?.[key] || 0);
  });
}

function populateOrderCommitmentStatusFilter(rows) {
  const filter = document.getElementById("order-commitment-status-filter");
  const selectedValue = filter.value;
  const statuses = [...new Set(rows.map((row) => row.Status).filter(Boolean))].sort();
  filter.replaceChildren();
  const allOption = document.createElement("option");
  allOption.value = "";
  allOption.textContent = translate("allStatuses");
  filter.append(allOption);
  statuses.forEach((status) => {
    const option = document.createElement("option");
    option.value = status;
    option.textContent = orderCommitmentLabel(status);
    filter.append(option);
  });
  filter.value = statuses.includes(selectedValue) ? selectedValue : "";
}

function renderOrderCommitments() {
  const content = document.getElementById("order-commitment-content");
  const empty = document.getElementById("order-commitment-empty");
  const body = document.getElementById("order-commitment-table-body");
  const rows = orderCommitmentRows();
  renderOrderCommitmentSummary(orderCommitmentData?.Summary);
  populateOrderCommitmentStatusFilter(rows);

  const query = document.getElementById("order-commitment-search").value.trim().toLocaleLowerCase();
  const status = document.getElementById("order-commitment-status-filter").value;
  const visibleRows = rows.filter((row) => {
    const matchesQuery = !query || [row.OrderID, row.ProductID]
      .some((value) => String(value || "").toLocaleLowerCase().includes(query));
    return matchesQuery && (!status || row.Status === status);
  });

  body.replaceChildren();
  visibleRows.forEach((row) => {
    const tableRow = document.createElement("tr");
    const actionCell = document.createElement("td");
    actionCell.className = "run-actions";
    actionCell.classList.toggle("has-planner-action", Array.isArray(row.AllowedActions) && row.AllowedActions.length > 0);
    const viewButton = document.createElement("button");
    viewButton.type = "button";
    viewButton.className = "run-action";
    viewButton.textContent = translate("viewDetails");
    viewButton.addEventListener("click", () => openOrderCommitmentDetail(row.EvaluationID));
    actionCell.append(viewButton);
    [
      textCell(row.OrderID), textCell(row.ProductID), textCell(formatDate(row.RequestedDueAt)),
      textCell(formatDate(row.EarliestSafePromiseAt)),
      textCell(orderCommitmentLoadLabel(row.LoadBeforeMinutes, row.LoadAfterMinutes, row.LoadAfterPercent)),
      textCell(orderCommitmentLabel(row.ProtectionThresholdSource)),
      textCell(orderCommitmentLabel(row.MaterialStatus)), textCell(orderCommitmentLabel(row.Recommendation)),
      textCell(orderCommitmentLabel(row.ReservationStatus)), textCell(orderCommitmentLabel(row.ExceptionStatus)), actionCell
    ].forEach((cell) => tableRow.append(cell));
    body.append(tableRow);
  });
  content.hidden = false;
  empty.hidden = visibleRows.length !== 0;
  empty.textContent = rows.length === 0 ? translate("noOrderCommitments") : translate("notAvailable");
}

async function loadOrderCommitments() {
  const error = document.getElementById("order-commitment-error");
  const content = document.getElementById("order-commitment-content");
  const empty = document.getElementById("order-commitment-empty");
  if (!orderCommitmentData) {
    content.hidden = true;
    empty.hidden = false;
    empty.textContent = translate("loadingData");
  }
  try {
    const response = await fetch("/planner/workbench/order-commitments/workbench", {
      headers: { Accept: "application/json" }
    });
    orderCommitmentRevision = response.headers.get("X-Workbench-Revision");
    if (!response.ok) throw new Error("order-commitment-load-failed");
    orderCommitmentData = (await response.json()).Data;
    error.hidden = true;
    renderOrderCommitments();
  } catch (_error) {
    content.hidden = true;
    empty.hidden = true;
    error.textContent = `${translate("orderCommitmentLoadFailed")} ${translate("orderCommitmentRetryAdvice")}`;
    error.hidden = false;
  }
}

function orderCommitmentAssessmentRows(assessment) {
  if (!assessment) return [["status", translate("notAvailable")]];
  const windows = Array.isArray(assessment.WindowAssessments) ? assessment.WindowAssessments : [];
  return [
    ["selectedPromise", formatDate(assessment.PromiseAt)],
    ["ccrPlannedLoad", windows.map((window) => window.ResourceID).filter(Boolean).join(", ") || translate("notAvailable")],
    ["loadAfter", windows.map((window) => orderCommitmentLoadLabel(
      window.LoadBeforeMinutes, window.LoadAfterMinutes, window.LoadAfterPercent
    )).join("; ") || translate("notAvailable")]
  ];
}

function orderCommitmentAuditFactText(details) {
  const factValues = {
    FromStatus: orderCommitmentLabel(details.FromStatus),
    ToStatus: orderCommitmentLabel(details.ToStatus),
    Recommendation: orderCommitmentLabel(details.Recommendation),
    DecisionCode: orderCommitmentLabel(details.DecisionCode),
    SupersededByEvaluationID: displayValue(details.SupersededByEvaluationID),
    AcceptedPromiseAt: formatDate(details.AcceptedPromiseAt),
    CcrRiskAcknowledged: businessValue(details.CcrRiskAcknowledged),
    MaterialRiskAcknowledged: businessValue(details.MaterialRiskAcknowledged),
    MaterialCheckEnabled: businessValue(details.MaterialCheckEnabled),
    MaterialEvidenceFreshnessStatus: orderCommitmentLabel(details.MaterialEvidenceFreshnessStatus)
  };
  const factLabels = {
    SupersededByEvaluationID: "supersededByEvaluation",
    AcceptedPromiseAt: "acceptedPromise",
    CcrRiskAcknowledged: "ccrRiskAcknowledged",
    MaterialRiskAcknowledged: "materialRiskAcknowledged",
    MaterialCheckEnabled: "materialCheck",
    MaterialEvidenceFreshnessStatus: "materialFreshness"
  };
  return Object.entries(factValues)
    .filter(([key]) => details[key] !== null && details[key] !== undefined && details[key] !== "")
    .map(([key, value]) => factLabels[key] ? `${translate(factLabels[key])}: ${value}` : value);
}

function orderCommitmentAuditText(event) {
  const facts = orderCommitmentAuditFactText(event.Details || {});
  const eventType = orderCommitmentLabel(event.EventType);
  return [eventType, formatDate(event.OccurredAt), event.ActorID, ...facts]
    .filter(Boolean).join(" · ");
}

function showOrderCommitmentError(message) {
  const error = document.getElementById("order-commitment-error");
  error.textContent = message;
  error.hidden = false;
  showNotification(message, "error");
}

function orderCommitmentAllowedActions() {
  return new Set(
    selectedOrderCommitment?.Recommendation?.AllowedActions || []
  );
}

function renderOrderCommitmentActions() {
  const allowed = orderCommitmentAllowedActions();
  const reevaluationForm = document.getElementById(
    "order-commitment-reevaluation-form"
  );
  reevaluationForm.hidden = !allowed.has("Reevaluate");
  const actions = document.getElementById("order-commitment-actions");
  actions.replaceChildren();
  [
    "AcceptRequestedDate",
    "ConditionallyAcceptRequestedDate",
    "AcceptRecommendedDate",
    "ConditionallyAcceptRecommendedDate",
    "Reject"
  ].filter((action) => allowed.has(action)).forEach((action) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = action === "Reject" ? "button danger" : "button primary";
    button.textContent = orderCommitmentLabel(action);
    button.addEventListener("click", () => {
      openOrderCommitmentDecision(action);
    });
    actions.append(button);
  });
}

function updateOrderCommitmentMaterialSkipField() {
  const enabled = document.getElementById(
    "order-commitment-material-check"
  ).checked;
  const field = document.getElementById(
    "order-commitment-material-skip-field"
  );
  const reason = document.getElementById(
    "order-commitment-material-skip-reason"
  );
  field.hidden = enabled;
  reason.required = !enabled;
}

function orderCommitmentReevaluationErrorMessage(status) {
  if (status === "StateStoreRevisionConflict") {
    return translate("orderCommitmentRevisionConflict");
  }
  if (status === "OrderCommitmentEvaluationNotReevaluatable") {
    return translate("orderCommitmentNotReevaluatable");
  }
  if (status === "OrderCommitmentEvaluationNotFound") {
    return translate("orderCommitmentNotFound");
  }
  return translate("orderCommitmentReevaluationFailed");
}

async function reevaluateOrderCommitment(event) {
  event.preventDefault();
  if (!orderCommitmentAllowedActions().has("Reevaluate")) return;
  const enabled = document.getElementById(
    "order-commitment-material-check"
  ).checked;
  const reason = document.getElementById(
    "order-commitment-material-skip-reason"
  ).value.trim();
  if (!enabled && !reason) {
    showOrderCommitmentError(translate("materialSkipReasonRequired"));
    return;
  }
  const evaluationId = selectedOrderCommitment.EvaluationID;
  const response = await fetch(
    "/planner/workbench/order-commitments/"
      + encodeURIComponent(evaluationId) + "/reevaluate",
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "If-Match": orderCommitmentRevision
      },
      body: JSON.stringify({
        RequestedBy: "planner-1",
        OperationalStateSnapshotID: null,
        CheckMaterialAvailability: enabled,
        MaterialCheckSkipReason: enabled ? null : reason
      })
    }
  );
  orderCommitmentRevision = response.headers.get(
    "X-Workbench-Revision"
  ) || orderCommitmentRevision;
  const payload = await response.json();
  if (!response.ok) {
    const status = payload?.Data?.Status;
    if (status === "StateStoreRevisionConflict") {
      await loadOrderCommitments();
      await openOrderCommitmentDetail(evaluationId);
      showOrderCommitmentError(
        orderCommitmentReevaluationErrorMessage(status)
      );
      return;
    }
    showOrderCommitmentError(orderCommitmentReevaluationErrorMessage(status));
    return;
  }
  const newId = payload.Data.Evaluation.EvaluationID;
  await loadOrderCommitments();
  await openOrderCommitmentDetail(newId);
}

function orderCommitmentDecisionRequirements(action) {
  const requirements = selectedOrderCommitment?.Recommendation
    ?.ActionAcknowledgementRequirements?.[action];
  if (
    !requirements
    || typeof requirements.RequiresCcrAcknowledgement !== "boolean"
    || typeof requirements.RequiresMaterialAcknowledgement !== "boolean"
  ) {
    return null;
  }
  return requirements;
}

function renderOrderCommitmentDecisionSummary(detail, action) {
  const summary = document.getElementById("order-commitment-decision-summary");
  const row = orderCommitmentData?.Rows?.find(
    (candidate) => candidate.EvaluationID === detail.EvaluationID
  );
  const selectedAssessment = detail.CapacityEvidence?.SelectedAssessment;
  const windows = selectedAssessment?.WindowAssessments || [];
  const ccrLoad = windows.map((window) => orderCommitmentLoadLabel(
    window.LoadBeforeMinutes,
    window.LoadAfterMinutes,
    window.LoadAfterPercent
  )).join("; ") || translate("notAvailable");
  summary.replaceChildren();
  summary.append(detailSection("decision", [
    ["decision", orderCommitmentLabel(action)],
    ["requestedDueAt", formatDate(detail.Order?.RequestedDueAt)],
    ["selectedPromise", formatDate(selectedAssessment?.PromiseAt)],
    ["ccrLoadBeforeAfter", ccrLoad],
    ["protectionThresholdSource", orderCommitmentLabel(
      row?.ProtectionThresholdSource
    )],
    ["thresholdState", orderCommitmentLabel(
      detail.Recommendation?.ThresholdState
    )],
    ["materialStatus", orderCommitmentLabel(detail.MaterialEvidence?.Status)],
    ["externalOrderAcceptance", orderCommitmentLabel(
      detail.Boundary?.ExternalOrderAcceptance
    )],
    ["planningRunCreation", orderCommitmentLabel(
      detail.Boundary?.PlanningRunCreation
    )],
    ["productionMutation", orderCommitmentLabel(
      detail.Boundary?.ProductionMutation
    )]
  ]));
}

function updateOrderCommitmentDecisionValidity() {
  const reasonControl = document.getElementById(
    "order-commitment-decision-reason"
  );
  const ccrField = document.getElementById("order-commitment-ccr-ack-field");
  const materialField = document.getElementById(
    "order-commitment-material-ack-field"
  );
  const ccrControl = document.getElementById("order-commitment-ccr-ack");
  const materialControl = document.getElementById(
    "order-commitment-material-ack"
  );
  const reason = reasonControl.value.trim();
  const ccrRequired = !ccrField.hidden;
  const materialRequired = !materialField.hidden;
  const ccrAck = ccrControl.checked;
  const materialAck = materialControl.checked;
  const valid = Boolean(
    reason
    && (!ccrRequired || ccrAck)
    && (!materialRequired || materialAck)
  );
  const submit = document.getElementById("submit-order-commitment-decision");
  submit.disabled = !valid;
  return valid;
}

function showOrderCommitmentDecisionError(message) {
  const error = document.getElementById("order-commitment-decision-error");
  error.textContent = message;
  error.hidden = false;
  showNotification(message, "error");
}

function clearOrderCommitmentDecision() {
  selectedOrderCommitmentAction = null;
  const form = document.getElementById("order-commitment-decision-form");
  form.reset();
  document.getElementById("order-commitment-decision-error").hidden = true;
  document.getElementById("order-commitment-ccr-ack-field").hidden = true;
  document.getElementById("order-commitment-material-ack-field").hidden = true;
  document.getElementById("order-commitment-ccr-ack").required = false;
  document.getElementById("order-commitment-material-ack").required = false;
  document.getElementById("submit-order-commitment-decision").disabled = true;
}

function closeOrderCommitmentDecision() {
  const dialog = document.getElementById("order-commitment-decision-dialog");
  if (dialog.open) dialog.close();
  clearOrderCommitmentDecision();
}

function openOrderCommitmentDecision(action) {
  if (
    !selectedOrderCommitment
    || selectedOrderCommitment?.Status !== "AwaitingPlannerDecision"
    || !orderCommitmentAllowedActions().has(action)
  ) {
    return;
  }
  const requirements = orderCommitmentDecisionRequirements(action);
  if (!requirements) return;
  selectedOrderCommitmentAction = action;
  const ccrField = document.getElementById("order-commitment-ccr-ack-field");
  const materialField = document.getElementById(
    "order-commitment-material-ack-field"
  );
  const ccrAck = document.getElementById("order-commitment-ccr-ack");
  const materialAck = document.getElementById("order-commitment-material-ack");
  const reason = document.getElementById("order-commitment-decision-reason");
  ccrField.hidden = !requirements.RequiresCcrAcknowledgement;
  materialField.hidden = !requirements.RequiresMaterialAcknowledgement;
  ccrAck.required = requirements.RequiresCcrAcknowledgement;
  materialAck.required = requirements.RequiresMaterialAcknowledgement;
  ccrAck.checked = false;
  materialAck.checked = false;
  reason.value = "";
  document.getElementById("order-commitment-decision-error").hidden = true;
  setText("order-commitment-decision-title", orderCommitmentLabel(action));
  renderOrderCommitmentDecisionSummary(selectedOrderCommitment, action);
  updateOrderCommitmentDecisionValidity();
  document.getElementById("order-commitment-decision-dialog").showModal();
  const firstRequiredControl = requirements.RequiresCcrAcknowledgement
    ? ccrAck
    : requirements.RequiresMaterialAcknowledgement ? materialAck : reason;
  firstRequiredControl.focus();
}

function orderCommitmentDecisionErrorMessage(status) {
  if ([
    "OrderCommitmentDecisionReplayConflict",
    "OrderCommitmentDecisionReplayEvidenceMismatch"
  ].includes(status)) {
    return translate("orderCommitmentReplayConflict");
  }
  if ([
    "StateStoreRevisionConflict",
    "OrderCommitmentEvaluationStale",
    "OrderCommitmentEvaluationFingerprintMismatch",
    "OrderCommitmentEvaluationNotDecisionEligible"
  ].includes(status)) {
    return translate("orderCommitmentEvidenceChanged");
  }
  return translate("orderCommitmentDecisionFailed");
}

async function submitOrderCommitmentDecision(event) {
  event.preventDefault();
  const detail = selectedOrderCommitment;
  const action = selectedOrderCommitmentAction;
  if (
    !detail
    || detail.Status !== "AwaitingPlannerDecision"
    || !orderCommitmentAllowedActions().has(action)
  ) {
    return;
  }
  const reason = document.getElementById(
    "order-commitment-decision-reason"
  ).value.trim();
  const ccrRequired = !document.getElementById(
    "order-commitment-ccr-ack-field"
  ).hidden;
  const materialRequired = !document.getElementById(
    "order-commitment-material-ack-field"
  ).hidden;
  const ccrAck = document.getElementById("order-commitment-ccr-ack").checked;
  const materialAck = document.getElementById(
    "order-commitment-material-ack"
  ).checked;
  if (!reason || (ccrRequired && !ccrAck)
      || (materialRequired && !materialAck)) {
    showOrderCommitmentDecisionError(
      translate("requiredDecisionEvidenceMissing")
    );
    return;
  }
  const decisionId = ["DEC", detail.EvaluationID, detail.RecordVersion, action].join("-");
  const submitButton = document.getElementById(
    "submit-order-commitment-decision"
  );
  submitButton.disabled = true;
  try {
    const response = await fetch(
      "/planner/workbench/order-commitments/"
        + encodeURIComponent(detail.EvaluationID) + "/decision",
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "If-Match": orderCommitmentRevision
        },
        body: JSON.stringify({
          DecisionID: decisionId,
          Decision: action,
          DecidedBy: "planner-1",
          Reason: reason,
          ExpectedEvaluationFingerprint:
            detail.TechnicalDetails.EvaluationFingerprint,
          CcrRiskAcknowledged: ccrAck,
          MaterialRiskAcknowledged: materialAck
        })
      }
    );
    orderCommitmentRevision = response.headers.get(
      "X-Workbench-Revision"
    ) || orderCommitmentRevision;
    const payload = await response.json();
    const status = payload?.Data?.Status;
    const refreshOnlyStatuses = [
      "StateStoreRevisionConflict",
      "OrderCommitmentEvaluationStale",
      "OrderCommitmentEvaluationFingerprintMismatch",
      "OrderCommitmentEvaluationNotDecisionEligible",
      "OrderCommitmentDecisionReplayConflict",
      "OrderCommitmentDecisionReplayEvidenceMismatch"
    ];
    if (!response.ok && refreshOnlyStatuses.includes(status)) {
      const message = orderCommitmentDecisionErrorMessage(status);
      await loadOrderCommitments();
      await openOrderCommitmentDetail(detail.EvaluationID);
      selectedOrderCommitmentAction = null;
      submitButton.disabled = true;
      showOrderCommitmentDecisionError(message);
      return;
    }
    if (!response.ok) {
      showOrderCommitmentDecisionError(
        orderCommitmentDecisionErrorMessage(status)
      );
      updateOrderCommitmentDecisionValidity();
      return;
    }
    const successMessage = `${translate("orderCommitmentDecisionRecorded")} ${
      orderCommitmentLabel(status)
    }`;
    closeOrderCommitmentDecision();
    await loadOrderCommitments();
    await openOrderCommitmentDetail(detail.EvaluationID);
    showNotification(successMessage, "success");
  } catch (_error) {
    showOrderCommitmentDecisionError(
      translate("orderCommitmentDecisionFailed")
    );
    updateOrderCommitmentDecisionValidity();
  }
}

function renderOrderCommitmentDetail() {
  const detail = selectedOrderCommitment;
  if (!detail) return;
  setText("order-commitment-detail-title", detail.Order?.OrderID || detail.EvaluationID);
  const content = document.getElementById("order-commitment-detail-content");
  content.replaceChildren();
  content.append(detailSection("orderDetails", [
    ["order", detail.Order?.OrderID], ["product", detail.Order?.ProductID],
    ["quantity", detail.Order?.Quantity === null || detail.Order?.Quantity === undefined ? "-" : `${formatNumber(detail.Order.Quantity)} ${detail.Order.Uom || ""}`.trim()],
    ["requestedDueAt", formatDate(detail.Order?.RequestedDueAt)], ["businessPriority", detail.Order?.BusinessPriority]
  ]));
  content.append(detailSection("capacityEvidence", [
    ["status", orderCommitmentLabel(detail.CapacityEvidence?.Status)],
    ["requestedDateAssessment", formatDate(detail.CapacityEvidence?.RequestedDateAssessment?.PromiseAt)],
    ["earliestSafeAssessment", formatDate(detail.CapacityEvidence?.EarliestSafeAssessment?.PromiseAt)],
    ...orderCommitmentAssessmentRows(detail.CapacityEvidence?.SelectedAssessment)
  ]));
  const materialLines = Array.isArray(detail.MaterialEvidence?.Lines) ? detail.MaterialEvidence.Lines : [];
  content.append(detailSection("materialEvidence", [
    ["status", orderCommitmentLabel(detail.MaterialEvidence?.Status)],
    ["materialCheck", businessValue(detail.MaterialEvidence?.CheckEnabled)],
    ["materialFreshness", orderCommitmentLabel(detail.MaterialEvidence?.OperationalStateFreshnessStatus)],
    ["materialLines", formatNumber(materialLines.length)]
  ]));
  content.append(detailSection("recommendation", [
    ["recommendation", orderCommitmentLabel(detail.Recommendation?.Decision)],
    ["thresholdState", orderCommitmentLabel(detail.Recommendation?.ThresholdState)],
    ["confirmationRequired", businessValue(detail.Recommendation?.RequiresPlannerDecision)],
    ["materialPending", businessValue(detail.Recommendation?.RequiresMaterialAcknowledgement)]
  ]));
  content.append(detailSection("decision", [
    ["decision", orderCommitmentLabel(detail.Decision?.Decision)], ["decidedBy", detail.Decision?.DecidedBy],
    ["decidedAt", formatDate(detail.Decision?.DecidedAt)], ["decisionReason", detail.Decision?.Reason],
    ["acceptedPromise", formatDate(detail.Decision?.AcceptedPromiseAt)]
  ]));
  content.append(detailSection("reservation", [
    ["demandCommitment", detail.Reservation?.DemandCommitmentID], ["reservationBatch", detail.Reservation?.ReservationBatchID],
    ["status", orderCommitmentLabel(detail.Reservation?.Status)]
  ]));
  content.append(listSection("auditHistory", detail.AuditHistory, orderCommitmentAuditText));
  content.append(detailSection("boundary", [
    ["recommendationOnly", businessValue(detail.Boundary?.RecommendationOnly)],
    ["externalOrderAcceptance", orderCommitmentLabel(detail.Boundary?.ExternalOrderAcceptance)],
    ["planningRunCreation", orderCommitmentLabel(detail.Boundary?.PlanningRunCreation)],
    ["productionMutation", orderCommitmentLabel(detail.Boundary?.ProductionMutation)]
  ]));
  const technical = document.createElement("details");
  technical.className = "technical-detail";
  const summary = document.createElement("summary");
  summary.textContent = translate("technicalDetails");
  const technicalRows = [
    ["evaluationFingerprint", detail.TechnicalDetails?.EvaluationFingerprint],
    ["decisionFingerprint", detail.TechnicalDetails?.DecisionFingerprint],
    ["traceId", detail.TechnicalDetails?.TraceID]
  ].filter(([, value]) => value);
  technical.append(summary, detailSection("technicalDetails", technicalRows));
  content.append(technical);
  renderOrderCommitmentActions();
  updateOrderCommitmentMaterialSkipField();
}

function renderOrderCommitmentDetailState(message, { retry } = {}) {
  const content = document.getElementById("order-commitment-detail-content");
  content.replaceChildren();
  const state = document.createElement("p");
  state.className = "order-commitment-detail-state";
  state.textContent = message;
  state.setAttribute("role", retry ? "alert" : "status");
  content.append(state);
  if (retry) {
    const retryButton = document.createElement("button");
    retryButton.type = "button";
    retryButton.className = "button secondary";
    retryButton.textContent = translate("refresh");
    retryButton.addEventListener("click", retry);
    content.append(retryButton);
  }
  document.getElementById("order-commitment-reevaluation-form").hidden = true;
  document.getElementById("order-commitment-actions").replaceChildren();
}

async function openOrderCommitmentDetail(evaluationId) {
  openSideDrawer("order-commitment-detail");
  selectedOrderCommitment = null;
  setText("order-commitment-detail-title", evaluationId);
  renderOrderCommitmentDetailState(translate("orderCommitmentDetailLoading"));
  try {
    const response = await fetch(
      "/planner/workbench/order-commitments/" + encodeURIComponent(evaluationId),
      { headers: { Accept: "application/json" } }
    );
    orderCommitmentRevision = response.headers.get("X-Workbench-Revision") || orderCommitmentRevision;
    if (!response.ok) throw new Error("order-commitment-detail-failed");
    selectedOrderCommitment = (await response.json()).Data;
    renderOrderCommitmentDetail();
  } catch (_error) {
    renderOrderCommitmentDetailState(
      `${translate("orderCommitmentDetailLoadFailed")} ${translate("orderCommitmentRetryAdvice")}`,
      { retry: () => openOrderCommitmentDetail(evaluationId) }
    );
  }
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
  hideNavigationHelp();
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
  hideNavigationHelp();
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
  document.querySelectorAll("[data-nav-help]").forEach((link) => {
    link.addEventListener("mouseenter", () => showNavigationHelp(link));
    link.addEventListener("focus", () => showNavigationHelp(link));
    link.addEventListener("mouseleave", hideNavigationHelp);
    link.addEventListener("blur", hideNavigationHelp);
  });
  window.addEventListener("resize", refreshNavigationHelp);
  document.getElementById("navigation-toggle").addEventListener("click", toggleNavigation);
  document.getElementById("navigation-backdrop").addEventListener("click", closeMobileNavigation);
  document.getElementById("refresh-case-acceptance").addEventListener("click", loadCaseAcceptance);
  document.getElementById("reset-all-cases").addEventListener("click", resetAllAcceptanceCases);
  document.getElementById("refresh-data-readiness").addEventListener("click", loadDataReadiness);
  document.getElementById("ddmrp-details").addEventListener("toggle", refreshDdmrpDetailsAction);
  document.getElementById("refresh-material-planning").addEventListener("click", loadMaterialPlanning);
  document.getElementById("material-planning-search").addEventListener("input", renderMaterialPlanningTable);
  document.getElementById("material-planning-zone-filter").addEventListener("change", renderMaterialPlanningTable);
  document.getElementById("material-planning-sort").addEventListener("change", (event) => {
    materialPlanningSortKey = event.target.value;
    renderMaterialPlanningTable();
  });
  document.getElementById("refresh-order-commitments").addEventListener("click", loadOrderCommitments);
  document.getElementById("order-commitment-search").addEventListener("input", renderOrderCommitments);
  document.getElementById("order-commitment-status-filter").addEventListener("change", renderOrderCommitments);
  document.getElementById("order-commitment-material-check").addEventListener("change", updateOrderCommitmentMaterialSkipField);
  document.getElementById("order-commitment-reevaluation-form").addEventListener("submit", reevaluateOrderCommitment);
  document.getElementById("order-commitment-decision-form").addEventListener("submit", submitOrderCommitmentDecision);
  document.getElementById("cancel-order-commitment-decision").addEventListener("click", closeOrderCommitmentDecision);
  document.getElementById("order-commitment-decision-dialog").addEventListener("cancel", closeOrderCommitmentDecision);
  [
    "order-commitment-decision-reason",
    "order-commitment-ccr-ack",
    "order-commitment-material-ack"
  ].forEach((id) => document.getElementById(id).addEventListener("input", updateOrderCommitmentDecisionValidity));
  document.getElementById("close-order-commitment-detail").addEventListener("click", () => closeSideDrawer("order-commitment-detail"));
  document.getElementById("operational-metrics-run-select").addEventListener("change", loadOperationalMetrics);
  document.getElementById("operational-metrics-evaluated-at").addEventListener("change", loadOperationalMetrics);
  document.getElementById("refresh-operational-metrics").addEventListener("click", loadOperationalMetrics);
  document.getElementById("generate-operational-snapshot").addEventListener("click", generateOperationalSnapshotFromLatest);
  document.getElementById("view-readiness-issues").addEventListener("click", openIssuesDrawer);
  document.getElementById("close-issues-drawer").addEventListener("click", closeIssuesDrawer);
  document.getElementById("drawer-backdrop").addEventListener("click", () => {
    closeIssuesDrawer();
    ["order-commitment-detail", "planning-run-detail", "scheduled-order-detail", "release-reason-detail", "dispatch-package-detail", "buffer-order-detail", "exception-detail"].forEach((id) => closeSideDrawer(id));
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
  ["wizard-olt-minutes", "wizard-variability-profile", "wizard-capacity-flex-profile"].forEach((id) => {
    document.getElementById(id).addEventListener("input", renderTimeBufferRecommendation);
    document.getElementById(id).addEventListener("change", renderTimeBufferRecommendation);
  });
  document.getElementById("apply-time-buffer-recommendation").addEventListener("click", applyTimeBufferRecommendation);
  document.getElementById("planning-run-form").addEventListener("submit", submitPlanningRun);
  document.getElementById("close-planning-run-detail").addEventListener("click", closePlanningRunDetail);
  document.getElementById("schedule-result-run-select").addEventListener("change", (event) => loadScheduleResult(event.target.value));
  document.getElementById("refresh-schedule-result").addEventListener("click", () => loadScheduleResult(selectedScheduleRunID));
  document.querySelectorAll("[data-schedule-tab]").forEach((button) => button.addEventListener("click", () => setScheduleTab(button.dataset.scheduleTab)));
  document.getElementById("sdbr-what-if-resource").addEventListener("change", renderSdbrWhatIfWorkspace);
  document.getElementById("sdbr-what-if-scenario-type").addEventListener("change", () => updateSdbrWhatIfMtaCandidateDisplay(true));
  document.getElementById("sdbr-what-if-mta-candidate").addEventListener("change", () => updateSdbrWhatIfMtaCandidateDisplay(true));
  document.getElementById("run-sdbr-what-if").addEventListener("click", runSdbrWhatIf);
  document.getElementById("run-simio-validation").addEventListener("click", runSimioValidation);
  document.getElementById("refresh-simio-validation").addEventListener("click", () => loadScheduleOutputGovernance(selectedScheduleRunID));
  document.getElementById("simio-adherence-search").addEventListener("input", () => { simioAdherencePage = 1; renderSimulationResults(); });
  ["simio-adherence-event-filter", "simio-adherence-wait-filter", "simio-adherence-page-size"].forEach((id) => {
    document.getElementById(id).addEventListener("change", () => { simioAdherencePage = 1; renderSimulationResults(); });
  });
  document.querySelectorAll("[data-simio-sort]").forEach((button) => button.addEventListener("click", () => {
    const key = button.dataset.simioSort;
    simioAdherenceSort = {
      key,
      direction: simioAdherenceSort.key === key && simioAdherenceSort.direction === "asc" ? "desc" : "asc"
    };
    simioAdherencePage = 1;
    renderSimulationResults();
  }));
  document.getElementById("simio-adherence-previous").addEventListener("click", () => { simioAdherencePage -= 1; renderSimulationResults(); });
  document.getElementById("simio-adherence-next").addEventListener("click", () => { simioAdherencePage += 1; renderSimulationResults(); });
  document.querySelectorAll("[data-gantt-mode]").forEach((button) => button.addEventListener("click", () => setGanttMode(button.dataset.ganttMode)));
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
  document.getElementById("replan-scheduled-orders").addEventListener("click", createReplanRunFromCurrentSchedule);
  document.getElementById("save-scheduled-order-view").addEventListener("click", saveScheduledOrderView);
  document.getElementById("scheduled-order-saved-view").addEventListener("change", (event) => applyScheduledOrderView(event.target.value));
  document.getElementById("close-scheduled-order-detail").addEventListener("click", () => closeSideDrawer("scheduled-order-detail"));
  document.getElementById("close-release-reason-detail").addEventListener("click", () => closeSideDrawer("release-reason-detail"));
  document.getElementById("close-dispatch-package-detail").addEventListener("click", () => closeSideDrawer("dispatch-package-detail"));
  document.getElementById("release-run-select").addEventListener("change", () => {
    releaseManagementUsesLatestOperationalState = false;
    loadReleaseManagement();
  });
  document.getElementById("refresh-release-management").addEventListener("click", reevaluateReleaseManagementWithLatestState);
  document.getElementById("buffer-run-select").addEventListener("change", loadBufferBoard);
  document.getElementById("refresh-buffer-board").addEventListener("click", loadBufferBoard);
  document.getElementById("dispatch-run-select").addEventListener("change", loadDispatchSuggestions);
  document.getElementById("dispatch-evaluated-at").addEventListener("change", loadDispatchSuggestions);
  document.getElementById("refresh-dispatch-suggestions").addEventListener("click", loadDispatchSuggestions);
  document.getElementById("issue-mes-dispatch-suggestions").addEventListener("click", issueMesDispatchSuggestions);
  document.getElementById("refresh-public-demo").addEventListener("click", loadPublicDemoGoldenLoop);
  document.getElementById("run-public-demo").addEventListener("click", runPublicDemoGoldenLoop);
  document.getElementById("close-buffer-order-detail").addEventListener("click", () => closeSideDrawer("buffer-order-detail"));
  document.getElementById("close-buffer-transaction-dialog").addEventListener("click", () => document.getElementById("buffer-transaction-dialog").close());
  document.getElementById("cancel-buffer-transaction").addEventListener("click", () => document.getElementById("buffer-transaction-dialog").close());
  document.getElementById("buffer-transaction-form").addEventListener("submit", submitBufferTransaction);
  document.getElementById("refresh-exception-center").addEventListener("click", loadExceptionCenter);
  document.getElementById("exception-severity-filter").addEventListener("change", renderExceptionCenter);
  document.getElementById("exception-source-filter").addEventListener("change", renderExceptionCenter);
  document.getElementById("close-exception-detail").addEventListener("click", () => closeSideDrawer("exception-detail"));
  document.getElementById("refresh-calendar-preview").addEventListener("click", loadCalendarPreview);
  document.getElementById("calendar-preview-resource").addEventListener("change", loadCalendarPreview);
  document.getElementById("calendar-preview-start").addEventListener("change", loadCalendarPreview);
  document.getElementById("calendar-preview-end").addEventListener("change", loadCalendarPreview);
  document.getElementById("calendar-base-calendar-form").addEventListener("submit", submitCalendarPageBaseCalendar);
  document.getElementById("calendar-assignment-form").addEventListener("submit", submitCalendarPageAssignment);
  document.getElementById("calendar-override-form").addEventListener("submit", submitCalendarPageOverride);
  document.getElementById("refresh-administration").addEventListener("click", loadAdministration);
  document.getElementById("admin-base-calendar-form")?.addEventListener("submit", submitBaseCalendar);
  document.getElementById("admin-resource-calendar-assignment-form")?.addEventListener("submit", submitResourceCalendarAssignment);
  document.getElementById("admin-calendar-override-form")?.addEventListener("submit", submitCalendarOverride);
  document.getElementById("admin-routings-import").addEventListener("click", () => {
    const routingObject = (administrationData?.MasterDataObjects || []).find((item) => item.ObjectKey === "Routings");
    if (routingObject) selectAdminImportObject(routingObject);
  });
  window.addEventListener("hashchange", () => renderRoute(true));
  window.addEventListener("resize", () => { if (!isNarrowScreen()) closeMobileNavigation(); });
  loadSystemHealth();
});
