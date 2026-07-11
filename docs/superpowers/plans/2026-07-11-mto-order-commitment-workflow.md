# MTO Order Commitment Workflow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver an automatic CCR-first MTO order-commitment evaluation that gives a recommendation, leaves the final decision to a planner, and activates the existing shared demand/capacity/material ledgers only after an explicit option-2 decision.

**Architecture:** Keep the shadow scheduler, material assessment, recommendation/identity logic, and sanitized projections pure. FastAPI resolves a completed Approved/Published baseline, server-selected current operational evidence, and exact relevant Phase 0 rows, then persists immutable evaluations and revision-guarded decisions through the existing `WorkbenchStateStore` boundary. Acceptance ends at `AcceptedPendingFormalSchedule` and never creates a Planning Run or mutates DDAE, master data, ERP/WMS, MES, supplier-authority, or production-authority state.

**Tech Stack:** Python 3.11+, FastAPI, Pydantic `AwareDatetime`, existing scheduling and Phase 0 dataclasses, `WorkbenchStateStore` / `SQLiteWorkbenchStateStore`, pytest, vanilla HTML/CSS/JavaScript, PowerShell.

## Global Constraints

- Cite `BE-SDBR-006` through `BE-SDBR-010` and `BE-RUN-011` in backend tests; cite `UI-COMMIT-001` in UI tests and evidence.
- The first specification commit uses backend version `2.80` and UI version `5.35`. Current histories end at `2.79` and `5.34`; preserve those rows. Advance the stale document headers (`2.67` and `5.29`) instead of treating them as ledger tips.
- Recommendation only: intake and re-evaluation never accept an order, create a `DemandCommitment`, reserve capacity/material, create a Planning Run, or emit an external message.
- Planner decides. Material checking defaults on; a planner may disable it only through authenticated re-evaluation with a trimmed non-empty reason.
- Option 2 is fixed: acceptance writes shared Phase 0 objects and ends at `AcceptedPendingFormalSchedule`. It does not create or modify a Planning Run.
- No code or payload may govern or mutate DDAE parameters, extend a DDAE contract, append an order to a master-data version, acknowledge an external order, change ERP/WMS stock, or issue MES output.
- Use only OR-Tools CP-SAT for later formal runs. The shadow evaluator is deterministic window logic and does not invoke CP-SAT, Gurobi, or Simio.
- The API adapter uses only `REFERENCE_CCR_PROTECTION_POLICY` (80.0%, `ReferenceFallback`, `Approved=false`). Approved-policy behavior is pure-domain compatibility coverage, not a hidden DDAE field.
- A reference fallback always sets `RequiresCcrAcknowledgement=true`. Any selected candidate over an approved threshold also sets it, including later-safe candidates.
- Stale, future, missing, or malformed material evidence never produces `Feasible` or allocation requests. Skipped checking is not material feasibility.
- Resolve material lookahead only from the baseline run's frozen release policy through `release_policy_settings(frozen_release_policy).material_lookahead_minutes`. No MTO client or JavaScript payload may provide a material-window value.
- Preserve all history. Re-evaluation may supersede only an undecided row; accepted and rejected rows are immutable except exact decision replay.
- Normal planner projections expose no raw order, basis, master-data, snapshot, event-detail, or reservation JSON. Fingerprints and trace IDs stay in collapsed technical details.
- Do not modify `D:\Documents\DDAE_INTERFACE_CONTRACT`, `sdbr/ddsop_contracts.py`, or `nofinish/`.
- UI acceptance unit 13 stops at `已验证待用户确认` until explicit user confirmation.

---

## Exact Domain Contract

### Solver-Parity Capacity Semantics

Use these equations in `sdbr/ccr_shadow_scheduler.py`.

1. Mirror the formal duration pipeline exactly:

~~~python
base_duration = int(operation.duration_minutes * quantity)
effective_duration = max(
    1,
    ceil(base_duration * 100 / max(1, resource.efficiency_percent)),
)
~~~

2. `CapacityBucket.capacity_minutes` is already the formal aggregate duration limit. Never multiply it by `Resource.capacity_units`. `capacity_units` is used only for temporal overlap:

~~~python
aggregate_remaining = (
    bucket.capacity_minutes
    - scheduled_minutes_in_full_bucket
    - active_reserved_minutes_for_exact_bucket
    - candidate_minutes_already_assigned_to_bucket
)
usable_end = min(bucket.bucket_end, operation_deadline)
usable_span_minutes = floor_minutes(usable_end - bucket.bucket_start)
temporal_capacity = usable_span_minutes * resource.capacity_units
temporal_remaining = (
    temporal_capacity
    - scheduled_overlap_minutes_before_usable_end
    - active_reserved_minutes_for_exact_bucket
    - candidate_minutes_assigned_before_usable_end
)
fits = effective_duration <= min(aggregate_remaining, temporal_remaining)
~~~

All exact-window reservations are charged to the usable subwindow because Phase 0 deliberately does not lock an intra-window position. Full-bucket scheduled overlap protects the formal aggregate constraint; deadline-truncated overlap protects the temporal constraint.

3. Only `Processing` bars contribute scheduled load. Malformed/duplicate schedule or reservation evidence returns `NotAssessable`, never an undercount.

4. Active rows are exactly statuses in `ACTIVE_PLANNING_STATUSES` and match the triple `(ResourceID, WindowStartAt, WindowEndAt)`. Group/allocate windows per primary CCR resource; never pool resources.

5. Every selected row satisfies:

~~~python
latest_allowed = min(window_end, operation_deadline)
assert window_start < latest_allowed <= window_end
~~~

Equality with `WindowEndAt` is valid and must pass `prepare_reservation_confirmation`. A window that merely starts before the deadline is insufficient.

6. Threshold percent is `LoadAfterMinutes / bucket.capacity_minutes * 100`. Physical/date feasibility and protection risk remain separate.

### Freshness Policy

Ground MTO freshness in `evaluate_operational_state_freshness`:

~~~python
ORDER_COMMITMENT_OPERATIONAL_STATE_MAX_AGE_MINUTES = 60
age_minutes = (evaluated_at - snapshot.captured_at).total_seconds() / 60
status = "Future" if age_minutes < 0 else "Stale" if age_minutes > 60 else "Fresh"
acceptable = status == "Fresh"
~~~

- With no explicit snapshot ID, select the greatest `(captured_at, snapshot_id)` among snapshots with `captured_at <= evaluated_at`. Do not fall back to the baseline run's frozen snapshot.
- With an explicit SDBR snapshot ID, resolve that exact row. Unknown ID returns `404 OperationalStateSnapshotNotFound` before registration.
- Exactly 60 minutes is `Fresh`; older is `Stale`; any explicitly selected future snapshot is `Future`.
- `Stale`, `Future`, or no current snapshot yields `EvidenceInsufficient`, zero `AllocationRequests`, and no acceptance action.
- Persist selected ID, captured time, status, age at evaluation, max age, and `ValidThroughAt = CapturedAt + 60 minutes`.
- Snapshot identity, captured/valid-through times, freshness status, and max age are identity facts. Age-at-evaluation is observation metadata: store it in `Basis` and `MaterialAssessment` but exclude it, with `EvaluatedAt`, from identity fingerprints. Crossing from `Fresh` to `Stale` changes identity.
- Persist `CapacityAssessmentCutoffAt=EvaluatedAt` and, only when material checking is enabled, `MaterialEligibilityCutoffAt=EvaluatedAt + MaterialCheckWindowMinutes`. Both are canonical UTC ISO strings and are evaluation-identity facts. They are never inferred again from `CreatedAt` or client data.
- Exact intake replay is resolved by `OrderContentFingerprint` before a new clock observation is evaluated. Intentional re-evaluation observes new cutoffs and therefore produces either an exact duplicate for identical cutoffs/content or a deterministic new `EvaluationID`; it must never produce a same-ID/different-content conflict.

### Total Recommendation and Decision Matrix

Threshold state is `ApprovedWithin`, `ApprovedExceeded`, or `ReferenceFallback`. `RequiresCcrAcknowledgement` is true for every `ApprovedExceeded` and `ReferenceFallback` row. `RequiresMaterialAcknowledgement` is true for every `SkippedPendingConfirmation` row.

| Capacity | Material | ApprovedWithin | ApprovedExceeded / ReferenceFallback | Allowed actions |
| --- | --- | --- | --- | --- |
| `NotAssessable` | any | `DoNotRecommendAccept` | `DoNotRecommendAccept` | `Reevaluate`, `Reject` |
| `OnTime` | `Feasible` | `RecommendAccept` | `PlannerConfirmationRequired` | `AcceptRequestedDate`, `Reevaluate`, `Reject` |
| `OnTime` | `SkippedPendingConfirmation` | `CapacityAcceptableMaterialPending` | `PlannerConfirmationRequired` | `ConditionallyAcceptRequestedDate`, `Reevaluate`, `Reject` |
| `OnTime` | `EvidenceInsufficient` | `MaterialEvidenceRequired` | `MaterialEvidenceRequired` | `Reevaluate`, `Reject` |
| `OnTime` | `Shortage` | `DoNotRecommendAccept` | `DoNotRecommendAccept` | `Reevaluate`, `Reject` |
| `LaterSafeDate` | `Feasible` | `RecommendLaterPromise` | `PlannerConfirmationRequired` | `AcceptRecommendedDate`, `Reevaluate`, `Reject` |
| `LaterSafeDate` | `SkippedPendingConfirmation` | `RecommendLaterPromise` | `PlannerConfirmationRequired` | `ConditionallyAcceptRecommendedDate`, `Reevaluate`, `Reject` |
| `LaterSafeDate` | `EvidenceInsufficient` | `MaterialEvidenceRequired` | `MaterialEvidenceRequired` | `Reevaluate`, `Reject` |
| `LaterSafeDate` | `Shortage` | `DoNotRecommendAccept` | `DoNotRecommendAccept` | `Reevaluate`, `Reject` |

Exact acceptance contexts:

~~~python
ACCEPTANCE_ACTION_CONTEXT = {
    "AcceptRequestedDate": ("OnTime", "Feasible", "RequestedDateAssessment"),
    "ConditionallyAcceptRequestedDate": (
        "OnTime", "SkippedPendingConfirmation", "RequestedDateAssessment"
    ),
    "AcceptRecommendedDate": (
        "LaterSafeDate", "Feasible", "EarliestSafeAssessment"
    ),
    "ConditionallyAcceptRecommendedDate": (
        "LaterSafeDate", "SkippedPendingConfirmation", "EarliestSafeAssessment"
    ),
}
~~~

`Reject` is allowed for every `AwaitingPlannerDecision` row. Evidence-insufficient, shortage, and not-assessable rows have no acceptance action. Terminal rows expose `AllowedActions=[]`.

Action acknowledgement requirements are derived, never copied blindly from the evaluation-level warning flags:

~~~python
def action_acknowledgement_requirements(
    *,
    action: str,
    requires_ccr_acknowledgement: bool,
    requires_material_acknowledgement: bool,
) -> dict[str, bool]:
    is_acceptance = action in ACCEPTANCE_DECISIONS
    return {
        "RequiresCcrAcknowledgement": (
            is_acceptance and requires_ccr_acknowledgement
        ),
        "RequiresMaterialAcknowledgement": (
            is_acceptance and requires_material_acknowledgement
        ),
    }
~~~

Consequently `Reject` and `Reevaluate` always expose both requirements as `false`. The UI dialog reads the selected action's requirements, not the row-level warning flags. The backend accepts `Reject` with both acknowledgement booleans false even for a reference-fallback or skipped-material evaluation.

### Evaluation and Decision Identity

Keep three different canonical projections. They have deliberately different jobs:

1. `AuditBasis` preserves the complete frozen baseline/configuration/route/calendar, selected snapshot, exact relevant capacity rows, and exact relevant material rows, even when material checking is skipped.
2. `DecisionStalenessBasis` contains only facts capable of changing the decision under the selected policy. It always includes schedule/configuration/route/calendar/capacity facts. It includes snapshot/material facts only when `CheckMaterialAvailability=true`.
3. `DecisionFacts` contains the actual current decision outputs and is compared field-for-field immediately before an acceptance mutation.

Canonical evaluation identity:

~~~python
evaluation_identity = {
    "OrderContentFingerprint": order["OrderContentFingerprint"],
    "AuditBasisFingerprint": basis["AuditBasisFingerprint"],
    "DecisionStalenessBasisFingerprint": basis[
        "DecisionStalenessBasisFingerprint"
    ],
    "CapacityAssessmentCutoffAt": basis["CapacityAssessmentCutoffAt"],
    "MaterialEligibilityCutoffAt": basis[
        "MaterialEligibilityCutoffAt"
    ],
    "MaterialPolicy": {
        "CheckEnabled": material["CheckEnabled"],
        "SkipReason": material.get("SkipReason"),
        "MaterialCheckWindowMinutes": material["MaterialCheckWindowMinutes"],
        "SnapshotSelectionMode": material["SnapshotSelectionMode"],
        "RequestedOperationalStateSnapshotID": material.get(
            "RequestedOperationalStateSnapshotID"
        ),
    },
    "ProtectionPolicy": normalized_protection_policy,
    "ShadowAlgorithm": {
        "Mode": "CCRFirstShadowScheduleV1",
        "Version": 1,
        "CapacitySemantics": "FormalBucketAggregateDeadlineTruncatedV1",
    },
}
~~~

`AuditBasisFingerprint` includes baseline schedule fingerprint; master version; `OperatingModelConfigurationID`, `OperatingModelFingerprint`, `SchedulingConfigurationID`, `DDMRPConfigurationID`; `ReleasePolicyVersionID` and frozen-policy fingerprint; route/calendar fingerprints; both cutoff facts; selected snapshot identity/freshness; exact CCR resource/window keys considered; matching active capacity rows; requirement item/location snapshot projections; and matching active material rows. It excludes unrelated rows and observation-only age.

`DecisionStalenessBasisFingerprint` excludes `EvaluatedAt`, age observations, and both cutoff timestamps. It includes the same capacity/configuration facts as the audit basis. When material checking is disabled it contains only `MaterialPolicy={"CheckEnabled": false, "SkipReason": <trimmed reason>, "MaterialCheckWindowMinutes": <frozen value>}` and excludes selected snapshot identity/freshness, inventory/material availability projections, and material allocation ledger rows. This separation prevents an unrelated inventory snapshot from staling a capacity-only decision while retaining that snapshot in immutable audit evidence.

Before strict ledger validation, prefilter capacity rows to exact `(ResourceID, WindowStartAt, WindowEndAt)` keys available to this order's primary CCR route and prefilter material rows to exact requirement `(ItemID, LocationID)` keys. Malformed matching rows fail closed; malformed unrelated rows are ignored by this decision path and are covered by explicit tests. This plan does not introduce a global corruption gate.

### Canonical Current Decision Facts

`create_order_commitment_evaluation` persists the following projection and its `canonical_fingerprint`. `_current_order_commitment_is_stale` compares the freshly rebuilt projection with the persisted projection before `prepare_mto_acceptance` is called:

~~~python
CAPACITY_DECISION_WINDOW_FIELDS = (
    "RouteSequence",
    "OperationID",
    "ResourceID",
    "WindowStartAt",
    "WindowEndAt",
    "UsableWindowStartAt",
    "UsableWindowEndAt",
    "LatestAllowedCompletionAt",
    "CapacityMinutes",
    "UsableTemporalCapacityMinutes",
    "ScheduledLoadMinutes",
    "ScheduledLoadBeforeDeadlineMinutes",
    "ExistingReservationMinutes",
    "CandidateLoadMinutes",
    "LoadBeforeMinutes",
    "LoadAfterMinutes",
    "LoadAfterPercent",
    "AggregateRemainingMinutes",
    "TemporalRemainingMinutes",
    "LoadStatus",
    "ThresholdExceeded",
)

CAPACITY_DECISION_REQUEST_FIELDS = (
    "ReservationLineID",
    "OrderID",
    "OperationID",
    "ResourceID",
    "WindowStartAt",
    "WindowEndAt",
    "ReservedMinutes",
    "LatestAllowedCompletionAt",
)

MATERIAL_DECISION_REQUEST_FIELDS = (
    "RequirementLineID",
    "ItemID",
    "LocationID",
    "Uom",
    "AllocatedQty",
    "SupplySourceType",
    "MaterialSnapshotID",
)

def canonical_order_commitment_decision_facts(
    evaluation: Mapping[str, object],
) -> dict[str, object]:
    shadow = dict(evaluation["ShadowSchedule"])
    material = dict(evaluation["MaterialAssessment"])
    recommendation = dict(evaluation["Recommendation"])
    candidate_key = {
        "OnTime": "RequestedDateAssessment",
        "LaterSafeDate": "EarliestSafeAssessment",
    }.get(str(shadow["Status"]))
    candidate = (
        dict(shadow[candidate_key])
        if candidate_key is not None
        and isinstance(shadow.get(candidate_key), Mapping)
        else {}
    )
    actions = list(recommendation["AllowedActions"])
    return {
        "CapacityStatus": shadow["Status"],
        "SelectedCandidateKey": candidate_key,
        "SelectedPromiseAt": candidate.get("PromiseAt"),
        "CapacityWindowAssessments": sorted(
            [
                {
                    field: row.get(field)
                    for field in CAPACITY_DECISION_WINDOW_FIELDS
                }
                for row in candidate.get("WindowAssessments", [])
            ],
            key=lambda row: (
                int(row["RouteSequence"]),
                str(row["OperationID"]),
                str(row["WindowStartAt"]),
            ),
        ),
        "CapacityReservationRequests": sorted(
            [
                {
                    field: row.get(field)
                    for field in CAPACITY_DECISION_REQUEST_FIELDS
                }
                for row in candidate.get("ReservationRequests", [])
            ],
            key=lambda row: str(row["ReservationLineID"]),
        ),
        "MaterialStatus": material["Status"],
        "MaterialAllocationRequests": sorted(
            [
                {
                    field: row.get(field)
                    for field in MATERIAL_DECISION_REQUEST_FIELDS
                }
                for row in material.get("AllocationRequests", [])
            ],
            key=lambda row: str(row["RequirementLineID"]),
        ),
        "Recommendation": recommendation["Decision"],
        "ThresholdState": recommendation["ThresholdState"],
        "AllowedActions": actions,
        "ActionAcknowledgementRequirements": {
            action: action_acknowledgement_requirements(
                action=action,
                requires_ccr_acknowledgement=bool(
                    recommendation["RequiresCcrAcknowledgement"]
                ),
                requires_material_acknowledgement=bool(
                    recommendation["RequiresMaterialAcknowledgement"]
                ),
            )
            for action in actions
        },
    }
~~~

The mapping/list casts above are valid Python and require `Mapping` from `collections.abc`. No observational field is silently omitted: a selected-window time advance, selected later-safe window/promise change, reservation deadline/load change, inbound eligibility change, recommendation change, or acknowledgement change produces different `DecisionFacts`.

Canonical decision fingerprint:

~~~python
decision_identity = {
    "DecisionID": decision_id.strip(),
    "EvaluationID": evaluation["EvaluationID"],
    "EvaluationFingerprint": evaluation["EvaluationFingerprint"],
    "Decision": decision,
    "ActorID": effective_actor_id.strip(),
    "Reason": reason.strip(),
    "CcrRiskAcknowledged": bool(ccr_risk_acknowledged),
    "MaterialRiskAcknowledged": bool(material_risk_acknowledged),
}
~~~

Exclude `DecidedAt`. Capture `decision_at = server_utc_now()` and `actor_id = _effective_actor_id(request, payload.DecidedBy)` once and pass those same values to every write/event builder.

### Intake Version and Terminal Rules

- `OrderVersionRank` is the tuple `(_parse_aware(ReceivedAt), OrderVersion)`; it is persisted as canonical ISO text plus `OrderVersion` and compared lexicographically. Tests use `ReceivedAt` one minute later for version 2. `_parse_aware` is the only datetime parse helper in `order_commitment_evaluation.py`; no `parse_aware` alias is introduced.
- Exact `OrderContentFingerprint` replay returns the existing row, including a terminal/superseded row, with `RegistrationStatus="Duplicate"` and no mutation/event/clock-derived evaluation.
- The same `OrderKey` (same version) with different content returns `409 OrderVersionContentConflict`.
- A lower version rank than the greatest persisted rank for the logical order returns `409 OrderVersionSuperseded` and cannot displace the newer row.
- A new higher-ranked intake atomically marks every prior `AwaitingPlannerDecision` row with the same `LogicalOrderKey` as `Superseded`, persists its supersession events, then inserts the candidate and event before the response is projected. Superseded rows expose `AllowedActions=[]` and reject decisions with `409 OrderCommitmentEvaluationNotDecisionEligible`.
- A prior `Rejected` row is immutable but does not block a higher-ranked version. A prior `AcceptedPendingFormalSchedule` row returns `409 AcceptedOrderVersionChangeRequiresExplicitAmendment`; cancellation/amendment is outside this plan. A prior `Superseded` row is immutable and does not block a still-higher-ranked version.
- Intake executes under the existing store admission/save boundary. Two concurrent v1/v2 requests leave exactly one open row, the greatest rank; the lower row is either superseded or rejected as old depending on lock order. No partial event/evaluation state is observable.

### Sanitized Read Contract

Each workbench row has exactly:

~~~python
ORDER_COMMITMENT_ROW_FIELDS = (
    "EvaluationID", "OrderID", "DemandLineID", "ProductID", "Quantity", "Uom",
    "BusinessPriority", "RequestedDueAt", "EarliestSafePromiseAt",
    "SelectedPromiseAt", "CcrResourceIDs", "CcrWindowCount",
    "LoadBeforeMinutes", "LoadAfterMinutes", "LoadAfterPercent",
    "ProtectionThresholdPercent", "ProtectionThresholdSource",
    "ProtectionThresholdApproved", "MaterialStatus",
    "MaterialEvidenceFreshnessStatus", "Recommendation", "AllowedActions",
    "RequiresCcrAcknowledgement", "RequiresMaterialAcknowledgement", "Status",
    "ReservationBatchID", "ReservationStatus", "ExceptionStatus", "EvaluatedAt",
    "ExternalOrderAcceptance", "PlanningRunCreation", "ProductionMutation",
)
~~~

`ReservationStatus` is `NotReserved`, a linked Phase 0 batch status, or `ReservationEvidenceMissing`. `ExceptionStatus` is `None`, `AssessmentBlocked`, `MaterialEvidenceBlocked`, `ReservationEvidenceMissing`, or `PlanningErrorPending`.

The detail `Recommendation` object has exactly:

~~~python
RECOMMENDATION_VIEW_FIELDS = (
    "Decision",
    "AllowedActions",
    "ThresholdState",
    "RequiresPlannerDecision",
    "RequiresCcrAcknowledgement",
    "RequiresMaterialAcknowledgement",
    "ActionAcknowledgementRequirements",
)
~~~

`ActionAcknowledgementRequirements` is keyed only by the projected `AllowedActions`; every value has exactly `RequiresCcrAcknowledgement` and `RequiresMaterialAcknowledgement`. Terminal details have an empty action list and empty requirements object.

Audit projections expose:

~~~python
AUDIT_FIELDS = (
    "EventID", "EventType", "OccurredAt", "ActorID",
    "DecisionID", "ReservationBatchID", "Details",
)
SAFE_AUDIT_DETAIL_FIELDS = frozenset({
    "FromStatus", "ToStatus", "Recommendation", "DecisionCode",
    "SupersededByEvaluationID", "AcceptedPromiseAt",
    "CcrRiskAcknowledged", "MaterialRiskAcknowledged",
    "MaterialCheckEnabled", "MaterialEvidenceFreshnessStatus",
})
~~~

Do not project event trace/causation/correlation IDs, source payloads, `Basis`, raw orders, master/snapshot rows, or unknown `Details`. Safe trace/fingerprint values belong only in collapsed `TechnicalDetails`.

---

## File Map

- Create `sdbr/ccr_shadow_scheduler.py`: pure CCR route/window and safe-promise evaluation.
- Create `sdbr/order_commitment_evaluation.py`: canonical order, snapshot/material gate, matrix, identity, registration, decision fingerprint, Phase 0 preparation.
- Create `sdbr/order_commitment_view.py`: exact sanitized list/detail projections.
- Create `tests/test_ccr_shadow_scheduler.py`, `tests/test_order_commitment_evaluation.py`, `tests/test_order_commitment_view.py`, and `tests/test_order_commitment_api.py`.
- Create `scripts/seed_mto_order_commitment_browser.ps1`: API-only repeatable browser state.
- Modify `sdbr/sdbr_market_control.py` at `_load_status` / `build_ccr_planned_load`.
- Modify `sdbr/state_store.py` at `WorkbenchStateStore`, `_state_payloads`, `_apply_payloads`, `_clear`, and `_state_counts`.
- Modify `sdbr/api.py` at payload models near `OrderPayload`, `create_app` aliases/auth middleware, `planning_reservation_workbench`, and endpoint registration before `planner_workbench_page`.
- Modify `sdbr/test_data.py` at constants and a new MTO fixture function.
- Modify `sdbr/web/planner-workbench.html`, `planner-workbench.js`, and `planner-workbench.css` at the symbols named in UI tasks.
- Modify `tests/test_sdbr_market_control.py`, `tests/test_state_store.py`, `tests/test_test_data.py`, `tests/test_planning_run_reservation_bridge.py`, and existing shell assertions in `tests/test_api.py`.
- Modify `docs/backend-specification.md` and `docs/ui-specification.md` before implementation and later only with observed evidence.

---

### Task 1: Specification Start at Backend 2.80 and UI 5.35

**Files and anchors**
- Modify `docs/backend-specification.md:3-8` header, `:143-151` after `BE-SDBR-009`, `:988-1010` acceptance records, and `:1010-1020` change-log head.
- Modify `docs/ui-specification.md:3-8` header, `:131` section 6.1, `:253` after `UI-DDMRP-002`, `:792` section 11, `:879` section 16, `:898` section 17, and `:1109-1117` change-log head.

**Produces:** `BE-SDBR-010` and `UI-COMMIT-001` in `[NOT-STARTED]` / `未开始`.

- [ ] **Step 1: Write the backend capability, policy, and start record**

Set header version/date to `2.80` / `2026-07-11`. Insert:

~~~markdown
| `BE-SDBR-010` | Automatic MTO order commitment evaluation and planner decision | `[NOT-STARTED]` | `D` `docs/superpowers/specs/2026-07-10-sdbr-order-commitment-evaluation-design.md`; planned `C` `sdbr/ccr_shadow_scheduler.py`, `sdbr/order_commitment_evaluation.py`, `sdbr/order_commitment_view.py`; planned `A` `/planner/workbench/order-commitments/*`; planned `T` `tests/test_ccr_shadow_scheduler.py`, `tests/test_order_commitment_evaluation.py`, `tests/test_order_commitment_api.py` | Intake performs recommendation-only CCR shadow assessment using formal bucket semantics and exact active reservations. Current operational evidence is server-selected with a fixed 60-minute maximum age; stale/future evidence cannot be feasible. Identity freezes schedule/config/release/snapshot/relevant-ledger evidence. Only a planner decision may create shared Phase 0 rows, ending at `AcceptedPendingFormalSchedule`; no Planning Run or external-authority mutation is automatic. |
~~~

Add before section 18:

~~~markdown
### BE-SDBR-010 MTO 订单承诺评估启动记录

- 日期：2026-07-11
- 状态：`[NOT-STARTED]`。
- 建议边界：系统只产生建议，计划员保留最终决定权；接收与重新评估不产生需求承诺或预留。
- 容量口径：`CapacityBucket.capacity_minutes` 保持正式求解器总分钟语义，不乘 `capacity_units`；交期落在窗口内时只使用截止时间前子窗口，并满足 `WindowStartAt < LatestAllowedCompletionAt <= WindowEndAt`。
- 物料与新鲜度：检查默认开启；最大年龄固定 60 分钟；默认选择不晚于服务端评估时间的最新快照，显式引用按 ID 解析；`Stale`、`Future` 或缺失证据返回 `EvidenceInsufficient` 且无分配请求。
- 确认：矩阵包含请求日期/建议日期与物料跳过组合；参考保护线及批准保护线超限均要求 CCR 确认，跳过物料均要求物料确认。
- 身份：评估依据冻结 baseline schedule、Operating Model、Scheduling、DDMRP、release policy、route/calendar、当前快照及精确相关容量/物料投影；决定指纹不含服务端观察时间。
- 结束状态：`AcceptedPendingFormalSchedule`；Planning Run 必须由后续显式操作通过 `PlanningReservationBatchIDs` 选择预留。
- 权威边界：不修改 DDAE、主数据版本、外部订单、ERP/WMS、MES、供应商或生产权威台账。
~~~

Prepend:

~~~markdown
| 2.80 | 2026-07-11 | 启动 `BE-SDBR-010` MTO 订单承诺：固化正式求解器一致的 CCR 影子容量、60 分钟运行快照新鲜度、完整建议/决定矩阵、配置与相关状态身份、option-2 共享预留和无外部权威修改边界 |
~~~

- [ ] **Step 2: Write the UI capability, IA, API map, and acceptance unit**

Set UI header to `5.35` / `2026-07-11`. Replace section 6.1 with the live route sequence:

~~~markdown
| NAV-01 | 计划总览 | Planning Overview | 今日异常、队列、约束和待办 |
| NAV-02 | 运营指标 | Operational Metrics | DDOM 运行指标 |
| NAV-03 | 数据就绪 | Data Readiness | 主数据版本与运行快照健康度 |
| NAV-04 | 物料计划 | Materials Planning | DDMRP 运行 read model |
| NAV-05 | 订单承诺 | Order Commitments | MTO 自动评估与计划员决定 |
| NAV-06 | 排程任务 | Planning Runs | 创建、入队、执行、恢复和审计 |
| NAV-07 | 排程结果 | Schedule Results | 甘特图、负荷、订单与诊断 |
| NAV-08 | 释放管理 | Release Management | 绳长、物料、WIP 和缓冲门控 |
| NAV-09 | 缓冲执行 | Buffer Execution | 缓冲状态与执行反馈 |
| NAV-10 | 派工建议 | Dispatch Suggestions | MES 建议和证据 |
| NAV-11 | 异常中心 | Exceptions | 失败、死信、重排和稳定性 |
| NAV-12 | 日历配置 | Calendar Configuration | 日历与有效能力窗口 |
| NAV-13 | 管理后台 | Administration | 主数据、集成、求解器和权限 |
| NAV-D1 | 公开演示闭环 | Public Demo | 演示数据与验收路径 |
~~~

Insert `UI-COMMIT-001` with `状态：未开始`. Copy the exact row fields from “Sanitized Read Contract” into the spec and require `ReservationStatus`, `ExceptionStatus`, lifecycle-derived `AllowedActions`, the safe audit whitelist, no raw JSON, no material-window client field, bilingual labels, stale conflict handling, and option-2 terminal wording.

Add section 11 rows:

~~~markdown
| 订单承诺接收 | `POST /planner/workbench/order-commitments/intake` |
| 订单承诺列表/详情 | `GET /planner/workbench/order-commitments/workbench`、`GET /planner/workbench/order-commitments/{evaluation_id}` |
| 订单承诺重新评估 | `POST /planner/workbench/order-commitments/{evaluation_id}/reevaluate` |
| 订单承诺计划员决定 | `POST /planner/workbench/order-commitments/{evaluation_id}/decision` |
~~~

Append:

~~~markdown
| 13 | MTO 订单承诺评估 | UI-COMMIT-001 | 是 |
~~~

Add record `17.13` with status `未开始`, then prepend:

~~~markdown
| 5.35 | 2026-07-11 | 启动 `UI-COMMIT-001` 独立 MTO 订单承诺工作台：精确列表/详情字段、预留与异常状态、AllowedActions 门控、安全审计、当前快照重新评估和 option-2 决定；不发送物料窗口、不创建 Planning Run、不修改外部权威 |
~~~

- [ ] **Step 3: Verify and commit**

~~~powershell
rg -n "文档版本 \| 2\.80|BE-SDBR-010|60 分钟|AcceptedPendingFormalSchedule|^\| 2\.80 " docs/backend-specification.md
rg -n "文档版本 \| 5\.35|UI-COMMIT-001|NAV-05|订单承诺接收|^\| 13 \||^\| 5\.35 " docs/ui-specification.md
git diff --check
git add -- docs/backend-specification.md docs/ui-specification.md
git commit -m "docs: specify revised MTO commitment workflow"
~~~

Expected: one `2.80` and one `5.35` row, no duplicate historical version, both new IDs not started, and a clean diff check.

---

### Task 2: Shared CCR Load Classifier

**Files and anchors**
- Modify `sdbr/sdbr_market_control.py` at `_load_status` and `build_ccr_planned_load`.
- Modify `tests/test_sdbr_market_control.py` after existing planned-load coverage.

**IDs:** `BE-SDBR-001`, `BE-SDBR-010`.

- [ ] **Step 1: Add the exact failing test**

Add class `TestSharedCcrLoadClassifier` with method `test_classifier_preserves_existing_threshold_boundaries`, asserting 80.0 → `Protected`, 80.01 → `Watch`, 95.0 → `NearLimit`, and 100.01 → `Overloaded` for target 80.0.

~~~powershell
pytest tests/test_sdbr_market_control.py::TestSharedCcrLoadClassifier::test_classifier_preserves_existing_threshold_boundaries -q --basetemp .tmp/pytest-mto-classifier-red -p no:cacheprovider
~~~

Expected: FAIL because `classify_ccr_load` is not public.

- [ ] **Step 2: Promote the existing logic**

~~~python
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
~~~

Replace only the private call in `build_ccr_planned_load`; preserve constants, totals, and response fields.

- [ ] **Step 3: Verify and commit**

~~~powershell
pytest tests/test_sdbr_market_control.py::TestSharedCcrLoadClassifier --collect-only -q
pytest tests/test_sdbr_market_control.py -q --basetemp .tmp/pytest-mto-market-green -p no:cacheprovider
git add -- sdbr/sdbr_market_control.py tests/test_sdbr_market_control.py
git commit -m "refactor: share CCR load classification"
~~~

Expected: one class test collects and the full file passes.

---

### Task 3: Shadow Input and Route Extraction in Three Small Slices

**Files and anchors**
- Create `sdbr/ccr_shadow_scheduler.py`.
- Create `tests/test_ccr_shadow_scheduler.py`.

**IDs:** `BE-SDBR-008`, `BE-SDBR-010`.

**Produces:** only validation and route-extraction helpers. The public evaluator is introduced with a complete body in Task 5; no temporary evaluator or route stub is committed here.

- [ ] **Step 1 (RED, 2-5 min): add exact validation tests**

~~~python
# tests/test_ccr_shadow_scheduler.py
from datetime import datetime, timezone

import pytest

from sdbr.ccr_shadow_scheduler import _validate_shadow_request


UTC = timezone.utc


class TestCcrShadowInputContract:
    @pytest.mark.parametrize(
        ("overrides", "message"),
        [
            ({"order_id": " "}, "order_id"),
            ({"quantity": True}, "quantity"),
            ({"quantity": float("inf")}, "quantity"),
            ({"requested_due_at": datetime(2026, 7, 20, 8)}, "timezone-aware"),
            ({"evaluated_at": datetime(2026, 7, 11, 8)}, "timezone-aware"),
            ({"downstream_protection_minutes": -1}, "non-negative"),
            ({"protection_threshold_percent": 0.0}, "threshold"),
            ({"protection_threshold_percent": 100.1}, "threshold"),
        ],
    )
    def test_rejects_invalid_public_inputs(self, overrides, message):
        values = {
            "order_id": "SO-1:10",
            "quantity": 1.0,
            "requested_due_at": datetime(2026, 7, 20, 18, tzinfo=UTC),
            "evaluated_at": datetime(2026, 7, 11, 8, tzinfo=UTC),
            "downstream_protection_minutes": 60,
            "protection_threshold_percent": 80.0,
        }
        values.update(overrides)
        with pytest.raises(ValueError, match=message):
            _validate_shadow_request(**values)
~~~

Run:

~~~powershell
pytest tests/test_ccr_shadow_scheduler.py::TestCcrShadowInputContract::test_rejects_invalid_public_inputs -q --basetemp .tmp/pytest-mto-shadow-input-red -p no:cacheprovider
~~~

Expected: FAIL because `sdbr.ccr_shadow_scheduler` does not exist.

- [ ] **Step 2 (GREEN, 2-5 min): create exact imports, constants, and validation helpers**

~~~python
# sdbr/ccr_shadow_scheduler.py
from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from math import ceil, floor, isfinite
from numbers import Real

from sdbr.planner_workbench import Operation, Resource, Routing
from sdbr.planning_reservation_view import ACTIVE_PLANNING_STATUSES
from sdbr.scheduling_solver import CapacityBucket, SetupTransition
from sdbr.sdbr_market_control import classify_ccr_load


SHADOW_ALGORITHM = {
    "Mode": "CCRFirstShadowScheduleV1",
    "Version": 1,
    "CapacitySemantics": "FormalBucketAggregateDeadlineTruncatedV1",
}


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Shadow schedule datetimes must be timezone-aware.")
    return value.astimezone(timezone.utc)


def _utc_iso(value: datetime) -> str:
    return _utc(value).isoformat()


def _positive_real(value: object, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ValueError(f"Shadow schedule {field} must be finite and positive.")
    normalized = float(value)
    if not isfinite(normalized) or normalized <= 0:
        raise ValueError(f"Shadow schedule {field} must be finite and positive.")
    return normalized


def _validate_shadow_request(
    *,
    order_id: str,
    quantity: object,
    requested_due_at: datetime,
    evaluated_at: datetime,
    downstream_protection_minutes: int,
    protection_threshold_percent: float,
) -> None:
    if not isinstance(order_id, str) or not order_id.strip():
        raise ValueError("Shadow schedule order_id must be non-empty.")
    _positive_real(quantity, "quantity")
    _utc(requested_due_at)
    _utc(evaluated_at)
    if (
        isinstance(downstream_protection_minutes, bool)
        or not isinstance(downstream_protection_minutes, int)
        or downstream_protection_minutes < 0
    ):
        raise ValueError("Shadow schedule protection must be non-negative.")
    threshold = _positive_real(
        protection_threshold_percent,
        "protection threshold",
    )
    if threshold > 100:
        raise ValueError("Shadow schedule threshold must be in (0, 100].")


def _issue(code: str, *entity_ids: str) -> dict[str, object]:
    return {"Code": code, "EntityIDs": list(entity_ids)}
~~~

Run the exact red selector again; expect PASS. Commit only this slice:

~~~powershell
git add -- sdbr/ccr_shadow_scheduler.py tests/test_ccr_shadow_scheduler.py
git commit -m "feat: validate MTO shadow inputs"
~~~

- [ ] **Step 3 (RED, 2-5 min): append exact route/setup tests**

~~~python
# append inside TestCcrShadowInputContract
    def test_route_order_repeated_ccr_and_formal_duration(self):
        resource = Resource(
            "CCR-1", "CCR", True, {}, capacity_units=1,
            efficiency_percent=80,
        )
        routing = Routing(
            product_id="FG-1",
            operations=[
                Operation("CCR-B", "CCR-1", 7, 30),
                Operation("NCR", "NCR-1", 5, 20),
                Operation("CCR-A", "CCR-1", 11, 10),
            ],
        )
        non_constraint = Resource("NCR-1", "NCR", False, {})

        all_operations, ccr_operations, issues = _extract_route_operations(
            order_id="SO-1:10",
            quantity=1.5,
            routing=routing,
            resources=[resource, non_constraint],
            setup_transitions=[],
        )

        assert issues == []
        assert [row["SourceOperationID"] for row in all_operations] == [
            "CCR-A", "NCR", "CCR-B"
        ]
        assert [row["OperationID"] for row in ccr_operations] == [
            "SO-1:10:CCR-A", "SO-1:10:CCR-B"
        ]
        assert ccr_operations[0]["DurationMinutes"] == 20

    def test_to_family_setup_and_missing_route_resource_or_ccr_fail_closed(self):
        ccr = Resource("CCR-1", "CCR", True, {}, efficiency_percent=100)
        routing = Routing(
            product_id="FG-1",
            operations=[Operation("CUT", "CCR-1", 10, 10, setup_family="F2")],
        )
        transition = SetupTransition("CCR-1", "F1", "F2", 15)

        _, _, setup_issues = _extract_route_operations(
            order_id="SO-1:10",
            quantity=1.0,
            routing=routing,
            resources=[ccr],
            setup_transitions=[transition],
        )
        assert [row["Code"] for row in setup_issues] == [
            "CCR_SETUP_LOAD_REQUIRES_REVIEW"
        ]

        for broken_routing, resources, code in [
            (None, [ccr], "ROUTING_NOT_FOUND"),
            (routing, [], "RESOURCE_NOT_FOUND"),
            (
                Routing("FG-1", [Operation("PACK", "NCR-1", 10, 10)]),
                [Resource("NCR-1", "NCR", False, {})],
                "CCR_OPERATION_NOT_FOUND",
            ),
        ]:
            _, _, issues = _extract_route_operations(
                order_id="SO-1:10",
                quantity=1.0,
                routing=broken_routing,
                resources=resources,
                setup_transitions=[],
            )
            assert [row["Code"] for row in issues] == [code]
~~~

Add these imports to the test file's existing import block:

~~~python
from sdbr.ccr_shadow_scheduler import (
    _extract_route_operations,
    _validate_shadow_request,
)
from sdbr.planner_workbench import Operation, Resource, Routing
from sdbr.scheduling_solver import SetupTransition
~~~

Run:

~~~powershell
pytest tests/test_ccr_shadow_scheduler.py::TestCcrShadowInputContract::test_route_order_repeated_ccr_and_formal_duration tests/test_ccr_shadow_scheduler.py::TestCcrShadowInputContract::test_to_family_setup_and_missing_route_resource_or_ccr_fail_closed -q --basetemp .tmp/pytest-mto-shadow-route-red -p no:cacheprovider
~~~

Expected: FAIL because `_extract_route_operations` is absent.

- [ ] **Step 4 (GREEN, 2-5 min): append the complete route extractor**

~~~python
def _unique_resources(resources: list[Resource]) -> dict[str, Resource]:
    result: dict[str, Resource] = {}
    for resource in resources:
        resource_id = resource.resource_id.strip()
        if not resource_id or resource_id in result:
            raise ValueError("Shadow resources require unique non-empty IDs.")
        if resource.capacity_units <= 0 or resource.efficiency_percent <= 0:
            raise ValueError("Shadow resource capacity and efficiency must be positive.")
        result[resource_id] = resource
    return result


def _extract_route_operations(
    *,
    order_id: str,
    quantity: float,
    routing: Routing | None,
    resources: list[Resource],
    setup_transitions: list[SetupTransition],
) -> tuple[list[dict[str, object]], list[dict[str, object]], list[dict[str, object]]]:
    if routing is None:
        return [], [], [_issue("ROUTING_NOT_FOUND")]
    resources_by_id = _unique_resources(resources)
    ordered = sorted(routing.operations, key=lambda row: row.sequence)
    operation_ids = [row.operation_id.strip() for row in ordered]
    sequences = [row.sequence for row in ordered]
    if (
        any(not item for item in operation_ids)
        or len(operation_ids) != len(set(operation_ids))
        or len(sequences) != len(set(sequences))
    ):
        raise ValueError("Route operations require unique IDs and sequences.")
    all_operations: list[dict[str, object]] = []
    ccr_operations: list[dict[str, object]] = []
    for operation in ordered:
        resource = resources_by_id.get(operation.resource_id)
        if resource is None:
            return [], [], [_issue("RESOURCE_NOT_FOUND", operation.operation_id)]
        base_duration = int(
            _positive_real(operation.duration_minutes, "duration")
            * _positive_real(quantity, "quantity")
        )
        effective_duration = max(
            1,
            ceil(base_duration * 100 / resource.efficiency_percent),
        )
        record = {
            "RouteSequence": operation.sequence,
            "OperationID": f"{order_id.strip()}:{operation.operation_id.strip()}",
            "SourceOperationID": operation.operation_id.strip(),
            "ResourceID": resource.resource_id,
            "DurationMinutes": effective_duration,
            "AlternateResourceIDs": sorted(operation.alternate_resource_ids or []),
            "IsPrimaryCcr": resource.is_constraint,
        }
        all_operations.append(record)
        if not resource.is_constraint:
            continue
        target_family = operation.setup_family or routing.product_id
        unresolved_setup = any(
            transition.resource_id == resource.resource_id
            and transition.to_family == target_family
            and transition.setup_minutes > 0
            for transition in setup_transitions
        )
        if unresolved_setup:
            return [], [], [
                _issue(
                    "CCR_SETUP_LOAD_REQUIRES_REVIEW",
                    operation.operation_id,
                    resource.resource_id,
                )
            ]
        ccr_operations.append(record)
    if not ccr_operations:
        return all_operations, [], [_issue("CCR_OPERATION_NOT_FOUND")]
    return all_operations, ccr_operations, []
~~~

Run the two red selectors, then the complete class with `--collect-only` and normally. Expect three test methods and all parameter cases to pass. Commit:

~~~powershell
git add -- sdbr/ccr_shadow_scheduler.py tests/test_ccr_shadow_scheduler.py
git commit -m "feat: extract MTO CCR route operations"
~~~

---

### Task 4: Solver-Parity Window Accounting in Three Review Gates

**Files and anchors**
- Modify `sdbr/ccr_shadow_scheduler.py` after `_extract_route_operations`.
- Modify `tests/test_ccr_shadow_scheduler.py` after `TestCcrShadowInputContract`.

**IDs:** `BE-SDBR-008`, `BE-SDBR-010`.

- [ ] **Step 1 (RED): append exact aggregate/deadline tests**

~~~python
class TestCcrShadowCapacityParity:
    @staticmethod
    def _state(*, units=1, capacity=480, scheduled=(), reserved=0):
        return {
            "ResourceID": "CCR-1",
            "WindowStart": datetime(2026, 7, 20, 8, tzinfo=UTC),
            "WindowEnd": datetime(2026, 7, 20, 16, tzinfo=UTC),
            "CapacityMinutes": capacity,
            "CapacityUnits": units,
            "ProcessingIntervals": list(scheduled),
            "ScheduledFullMinutes": sum(
                int((end - start).total_seconds() // 60)
                for start, end in scheduled
            ),
            "ExistingReservationMinutes": reserved,
            "CandidateAssignments": [],
        }

    def test_capacity_units_never_multiply_formal_bucket_total(self):
        state = self._state(units=2, reserved=450)
        metrics = _window_metrics(
            state,
            usable_start=state["WindowStart"],
            deadline=state["WindowEnd"],
            candidate_minutes=60,
        )
        assert metrics["AggregateRemainingMinutes"] == 30
        assert metrics["Fits"] is False

    def test_deadline_truncates_temporal_but_not_aggregate_load(self):
        start = datetime(2026, 7, 20, 8, tzinfo=UTC)
        state = self._state(
            scheduled=[(start, start + timedelta(minutes=180))]
        )
        metrics = _window_metrics(
            state,
            usable_start=start,
            deadline=datetime(2026, 7, 20, 12, tzinfo=UTC),
            candidate_minutes=120,
        )
        assert metrics["UsableTemporalCapacityMinutes"] == 240
        assert metrics["TemporalRemainingMinutes"] == 60
        assert metrics["Fits"] is False

        after_deadline = self._state(
            scheduled=[
                (
                    datetime(2026, 7, 20, 13, tzinfo=UTC),
                    datetime(2026, 7, 20, 16, tzinfo=UTC),
                )
            ]
        )
        aggregate = _window_metrics(
            after_deadline,
            usable_start=start,
            deadline=datetime(2026, 7, 20, 12, tzinfo=UTC),
            candidate_minutes=360,
        )
        assert aggregate["ScheduledLoadBeforeDeadlineMinutes"] == 0
        assert aggregate["AggregateRemainingMinutes"] == 300
        assert aggregate["Fits"] is False
~~~

Extend the test imports with `timedelta` and `_window_metrics`. Run both exact nodes; expect FAIL because `_window_metrics` is absent.

- [ ] **Step 2 (GREEN): append complete overlap and metric helpers**

~~~python
def _floor_minutes(value: timedelta) -> int:
    return floor(value.total_seconds() / 60)


def _overlap_minutes(
    intervals: list[tuple[datetime, datetime]],
    start: datetime,
    end: datetime,
) -> int:
    return sum(
        max(0, _floor_minutes(min(item_end, end) - max(item_start, start)))
        for item_start, item_end in intervals
    )


def _window_metrics(
    state: Mapping[str, object],
    *,
    usable_start: datetime,
    deadline: datetime,
    candidate_minutes: int,
) -> dict[str, object]:
    window_start = state["WindowStart"]
    window_end = state["WindowEnd"]
    assert isinstance(window_start, datetime)
    assert isinstance(window_end, datetime)
    usable_start = max(window_start, usable_start)
    usable_end = min(window_end, deadline)
    if usable_end <= usable_start:
        return {"Fits": False, "Reason": "NO_USABLE_WINDOW"}
    assignments = list(state["CandidateAssignments"])
    candidate_full = sum(int(row["Minutes"]) for row in assignments)
    candidate_before_deadline = sum(
        int(row["Minutes"])
        for row in assignments
        if row["LatestAllowedCompletionAt"] <= usable_end
    )
    scheduled_full = int(state["ScheduledFullMinutes"])
    existing = int(state["ExistingReservationMinutes"])
    aggregate_before = scheduled_full + existing + candidate_full
    intervals = list(state["ProcessingIntervals"])
    scheduled_usable = _overlap_minutes(intervals, usable_start, usable_end)
    temporal_before = scheduled_usable + existing + candidate_before_deadline
    capacity_minutes = int(state["CapacityMinutes"])
    temporal_capacity = (
        _floor_minutes(usable_end - usable_start)
        * int(state["CapacityUnits"])
    )
    aggregate_remaining = capacity_minutes - aggregate_before
    temporal_remaining = temporal_capacity - temporal_before
    load_after = aggregate_before + candidate_minutes
    load_percent = round(load_after / capacity_minutes * 100, 2)
    return {
        "Fits": candidate_minutes <= min(
            aggregate_remaining,
            temporal_remaining,
        ),
        "WindowStartAt": _utc_iso(window_start),
        "WindowEndAt": _utc_iso(window_end),
        "UsableWindowStartAt": _utc_iso(usable_start),
        "UsableWindowEndAt": _utc_iso(usable_end),
        "LatestAllowedCompletionAt": _utc_iso(usable_end),
        "CapacityMinutes": capacity_minutes,
        "UsableTemporalCapacityMinutes": temporal_capacity,
        "ScheduledLoadMinutes": scheduled_full,
        "ScheduledLoadBeforeDeadlineMinutes": scheduled_usable,
        "ExistingReservationMinutes": existing,
        "CandidateLoadMinutes": candidate_minutes,
        "LoadBeforeMinutes": aggregate_before,
        "LoadAfterMinutes": load_after,
        "LoadAfterPercent": load_percent,
        "AggregateRemainingMinutes": aggregate_remaining,
        "TemporalRemainingMinutes": temporal_remaining,
    }


def _commit_candidate(
    state: dict[str, object],
    *,
    minutes: int,
    latest_allowed_completion_at: datetime,
) -> None:
    assignments = list(state["CandidateAssignments"])
    assignments.append(
        {
            "Minutes": minutes,
            "LatestAllowedCompletionAt": latest_allowed_completion_at,
        }
    )
    state["CandidateAssignments"] = assignments
~~~

Run the two nodes and commit this isolated parity slice.

~~~powershell
git add -- sdbr/ccr_shadow_scheduler.py tests/test_ccr_shadow_scheduler.py
git commit -m "feat: enforce formal shadow bucket limits"
~~~

- [ ] **Step 3 (RED): append exact state-scope and Phase 0 request tests**

~~~python
    def test_repeated_visits_share_only_their_exact_resource_window(self):
        state = self._state()
        _commit_candidate(
            state,
            minutes=300,
            latest_allowed_completion_at=state["WindowEnd"],
        )
        second = _window_metrics(
            state,
            usable_start=state["WindowStart"],
            deadline=state["WindowEnd"],
            candidate_minutes=200,
        )
        assert second["AggregateRemainingMinutes"] == 180
        assert second["Fits"] is False

    def test_end_equal_deadline_is_accepted_by_phase0(self):
        operation = {
            "OperationID": "SO-1:10:CUT",
            "ResourceID": "CCR-1",
            "DurationMinutes": 60,
        }
        state = self._state()
        request = _reservation_request(
            order_id="SO-1:10",
            operation=operation,
            state=state,
            operation_deadline=state["WindowEnd"],
        )
        demand = create_demand_commitment(
            demand_source_type="MTOCustomerOrder",
            source_system="MockERP",
            source_object_type="CustomerOrder",
            source_object_id="SO-1",
            source_object_version="1",
            demand_line_id="10",
            item_or_product_id="FG-1",
            location_id="MAIN",
            quantity=1.0,
            uom="EA",
            required_at=state["WindowEnd"],
            demand_class="MTO",
            trace_id="TRACE-1",
        )
        write_set = prepare_reservation_confirmation(
            demand_commitment=demand,
            existing_commitments={},
            confirmation_id="DEC-1",
            confirmed_by="planner-1",
            confirmed_at=datetime(2026, 7, 11, 8, tzinfo=UTC),
            capacity_requests=[request],
            material_requests=[],
        )
        assert request["LatestAllowedCompletionAt"] == request["WindowEndAt"]
        assert len(write_set.capacity_reservations) == 1
~~~

Add exact imports for `_commit_candidate`, `_reservation_request`, `create_demand_commitment`, and `prepare_reservation_confirmation`. Run both nodes; expect only the request test to fail because `_reservation_request` is absent.

- [ ] **Step 4 (GREEN): append the complete request builder**

~~~python
def _reservation_request(
    *,
    order_id: str,
    operation: Mapping[str, object],
    state: Mapping[str, object],
    operation_deadline: datetime,
) -> dict[str, object]:
    window_start = state["WindowStart"]
    window_end = state["WindowEnd"]
    assert isinstance(window_start, datetime)
    assert isinstance(window_end, datetime)
    latest = min(window_end, operation_deadline)
    if not window_start < latest <= window_end:
        raise ValueError("Reservation deadline must be inside its exact window.")
    return {
        "ReservationLineID": (
            f"{operation['OperationID']}:{_utc_iso(window_start)}"
        ),
        "OrderID": order_id,
        "OperationID": operation["OperationID"],
        "ResourceID": operation["ResourceID"],
        "WindowStartAt": _utc_iso(window_start),
        "WindowEndAt": _utc_iso(window_end),
        "ReservedMinutes": int(operation["DurationMinutes"]),
        "LatestAllowedCompletionAt": _utc_iso(latest),
    }
~~~

Run the two nodes, then `tests/test_planning_reservations.py`; commit:

~~~powershell
git add -- sdbr/ccr_shadow_scheduler.py tests/test_ccr_shadow_scheduler.py
git commit -m "feat: emit Phase 0 ready shadow requests"
~~~

- [ ] **Step 5 (RED/GREEN): normalize only exact route-window evidence**

Append tests that build CCR-A/CCR-B 08:00-16:00 buckets, a different CCR-B window, and a malformed unrelated resource row. Assert `_build_window_states` charges only the exact active CCR-B triple, ignores inactive/different/unrelated rows, rejects a malformed matching row, and rejects duplicate buckets/bars/reservation IDs. Use this complete implementation:

~~~python
def _parse_aware(value: object, field: str) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as error:
            raise ValueError(f"{field} must be an aware ISO datetime.") from error
    else:
        raise ValueError(f"{field} must be an aware ISO datetime.")
    return _utc(parsed)


def _build_window_states(
    *,
    resources: list[Resource],
    capacity_buckets: list[CapacityBucket],
    ccr_resource_ids: set[str],
    gantt_rows: list[dict[str, object]],
    active_capacity_reservations: list[dict[str, object]],
) -> dict[tuple[str, datetime, datetime], dict[str, object]]:
    resources_by_id = _unique_resources(resources)
    states: dict[tuple[str, datetime, datetime], dict[str, object]] = {}
    for bucket in capacity_buckets:
        if bucket.resource_id not in ccr_resource_ids:
            continue
        start = _utc(bucket.bucket_start)
        end = _utc(bucket.bucket_end)
        key = (bucket.resource_id, start, end)
        resource = resources_by_id.get(bucket.resource_id)
        if (
            resource is None
            or end <= start
            or bucket.capacity_minutes <= 0
            or key in states
        ):
            raise ValueError("CCR capacity buckets are malformed or duplicated.")
        states[key] = {
            "ResourceID": bucket.resource_id,
            "WindowStart": start,
            "WindowEnd": end,
            "CapacityMinutes": bucket.capacity_minutes,
            "CapacityUnits": resource.capacity_units,
            "ProcessingIntervals": [],
            "ScheduledFullMinutes": 0,
            "ExistingReservationMinutes": 0,
            "CandidateAssignments": [],
        }
    seen_bars: set[tuple[object, ...]] = set()
    for resource_row in gantt_rows:
        resource_id = str(resource_row.get("ResourceID") or "")
        if resource_id not in ccr_resource_ids:
            continue
        bars = resource_row.get("Bars")
        if not isinstance(bars, list):
            raise ValueError("Relevant Gantt row Bars must be a list.")
        for bar in bars:
            if not isinstance(bar, Mapping):
                raise ValueError("Relevant Gantt bars must be objects.")
            if bar.get("BarType") not in {None, "Processing"}:
                continue
            start = _parse_aware(bar.get("Start"), "Gantt Start")
            end = _parse_aware(bar.get("End"), "Gantt End")
            identity = (
                resource_id,
                bar.get("OrderID"),
                bar.get("OperationID"),
                start,
                end,
            )
            if end <= start or identity in seen_bars:
                raise ValueError("Relevant processing bars are malformed or duplicated.")
            seen_bars.add(identity)
            for key, state in states.items():
                if key[0] != resource_id or end <= key[1] or start >= key[2]:
                    continue
                state["ProcessingIntervals"].append((start, end))
                state["ScheduledFullMinutes"] += _overlap_minutes(
                    [(start, end)], key[1], key[2]
                )
    seen_reservations: set[str] = set()
    for row in active_capacity_reservations:
        if row.get("Status") not in ACTIVE_PLANNING_STATUSES:
            continue
        resource_id = str(row.get("ResourceID") or "")
        start = _parse_aware(row.get("WindowStartAt"), "WindowStartAt")
        end = _parse_aware(row.get("WindowEndAt"), "WindowEndAt")
        key = (resource_id, start, end)
        if key not in states:
            continue
        reservation_id = str(row.get("CapacityReservationID") or "").strip()
        latest = _parse_aware(
            row.get("LatestAllowedCompletionAt"),
            "LatestAllowedCompletionAt",
        )
        minutes = _positive_real(row.get("ReservedMinutes"), "reserved minutes")
        if (
            not reservation_id
            or reservation_id in seen_reservations
            or not start < latest <= end
        ):
            raise ValueError("Relevant capacity reservations are malformed or duplicated.")
        seen_reservations.add(reservation_id)
        states[key]["ExistingReservationMinutes"] += int(minutes)
    return states
~~~

The API prefilter in Task 16 ensures a malformed unrelated row never reaches `_parse_aware`; this helper still performs a second exact-key check. Run the new exact nodes and commit as a separate review gate:

~~~powershell
git add -- sdbr/ccr_shadow_scheduler.py tests/test_ccr_shadow_scheduler.py
git commit -m "feat: scope MTO capacity evidence to exact windows"
~~~

---

### Task 5: Requested-Date and Earliest-Safe Selection

**Files and anchors**
- Modify `sdbr/ccr_shadow_scheduler.py`; add `_route_deadlines`, `_requested_candidate`, `_forward_window_metrics`, `_earliest_safe_candidate`, and `_result`.
- Modify `tests/test_ccr_shadow_scheduler.py` after parity tests.

**IDs:** `BE-SDBR-010`.

- [ ] **Step 1A (requested-date RED): write the three requested-pass tests**

Add `TestCcrShadowPromiseSelection`:

- `test_requested_candidate_walks_route_backward_and_returns_on_time`;
- `test_late_requested_candidate_returns_earliest_safe_promise`;
- `test_low_load_only_after_deadline_never_makes_request_on_time`;
- `test_multi_ccr_route_uses_per_operation_deadlines_and_route_order`;
- `test_no_later_window_returns_not_assessable_without_reservation_requests`;
- `test_selected_evidence_lists_exact_relevant_capacity_window_keys`.

Add this exact cutoff regression to the same class and import
`_requested_candidate`. It proves both cutoff rules during the initial
evaluation: a window ending exactly at the cutoff is excluded, and only the
unelapsed part of an active window contributes temporal capacity.

~~~python
    def test_initial_requested_pass_cannot_use_elapsed_shift_minutes(self):
        start = datetime(2026, 7, 20, 8, tzinfo=UTC)
        cutoff = datetime(2026, 7, 20, 12, tzinfo=UTC)
        end = datetime(2026, 7, 20, 16, tzinfo=UTC)

        def state(window_start, window_end, capacity):
            return {
                "ResourceID": "CCR-1",
                "WindowStart": window_start,
                "WindowEnd": window_end,
                "CapacityMinutes": capacity,
                "CapacityUnits": 1,
                "ProcessingIntervals": [],
                "ScheduledFullMinutes": 0,
                "ExistingReservationMinutes": 0,
                "CandidateAssignments": [],
            }

        operation = {
            "RouteSequence": 10,
            "OperationID": "SO-1:10:CUT",
            "SourceOperationID": "CUT",
            "ResourceID": "CCR-1",
            "DurationMinutes": 300,
        }
        result = _requested_candidate(
            order_id="SO-1:10",
            requested_due_at=end,
            capacity_assessment_cutoff_at=cutoff,
            ccr_operations=[operation],
            deadlines={"CUT": end},
            source_states={
                ("CCR-1", start, cutoff): state(start, cutoff, 240),
                ("CCR-1", start, end): state(start, end, 480),
            },
            protection_threshold_percent=80.0,
        )

        assert result["Feasible"] is False
        assert result["ReservationRequests"] == []
        assert result["ConsideredWindowKeys"] == [
            ("CCR-1", start.isoformat(), end.isoformat())
        ]
~~~

~~~powershell
pytest tests/test_ccr_shadow_scheduler.py::TestCcrShadowPromiseSelection::test_requested_candidate_walks_route_backward_and_returns_on_time tests/test_ccr_shadow_scheduler.py::TestCcrShadowPromiseSelection::test_low_load_only_after_deadline_never_makes_request_on_time tests/test_ccr_shadow_scheduler.py::TestCcrShadowPromiseSelection::test_initial_requested_pass_cannot_use_elapsed_shift_minutes --collect-only -q
pytest tests/test_ccr_shadow_scheduler.py::TestCcrShadowPromiseSelection::test_requested_candidate_walks_route_backward_and_returns_on_time tests/test_ccr_shadow_scheduler.py::TestCcrShadowPromiseSelection::test_low_load_only_after_deadline_never_makes_request_on_time tests/test_ccr_shadow_scheduler.py::TestCcrShadowPromiseSelection::test_initial_requested_pass_cannot_use_elapsed_shift_minutes -q --basetemp .tmp/pytest-mto-shadow-requested-red -p no:cacheprovider
~~~

Expected: exactly three items collect and fail because the requested pass is
absent or does not accept `capacity_assessment_cutoff_at`.

- [ ] **Step 1B (requested-date implement): add deadlines and the requested pass**

~~~python
def _route_deadlines(
    *,
    all_route_operations: list[dict[str, object]],
    requested_due_at: datetime,
    downstream_protection_minutes: int,
) -> dict[str, datetime]:
    cursor = requested_due_at - timedelta(
        minutes=downstream_protection_minutes
    )
    deadlines: dict[str, datetime] = {}
    for operation in reversed(all_route_operations):
        source_id = str(operation["SourceOperationID"])
        deadlines[source_id] = cursor
        cursor -= timedelta(minutes=int(operation["DurationMinutes"]))
    return deadlines
~~~

Requested pass:

~~~python
def _requested_candidate(
    *,
    order_id: str,
    requested_due_at: datetime,
    capacity_assessment_cutoff_at: datetime,
    ccr_operations: list[dict[str, object]],
    deadlines: Mapping[str, datetime],
    source_states: Mapping[
        tuple[str, datetime, datetime], dict[str, object]
    ],
    protection_threshold_percent: float,
) -> dict[str, object]:
    states = deepcopy(dict(source_states))
    assessments: list[dict[str, object]] = []
    requests: list[dict[str, object]] = []
    considered: set[tuple[str, str, str]] = set()
    cutoff = _utc(capacity_assessment_cutoff_at)
    for operation in reversed(ccr_operations):
        resource_id = str(operation["ResourceID"])
        deadline = deadlines[str(operation["SourceOperationID"])]
        fitting: list[tuple[dict[str, object], dict[str, object]]] = []
        for key, state in states.items():
            if (
                key[0] != resource_id
                or key[2] <= cutoff
                or key[1] >= deadline
            ):
                continue
            considered.add((key[0], _utc_iso(key[1]), _utc_iso(key[2])))
            metrics = _window_metrics(
                state,
                usable_start=max(key[1], cutoff),
                deadline=deadline,
                candidate_minutes=int(operation["DurationMinutes"]),
            )
            if metrics["Fits"]:
                fitting.append((state, metrics))
        selected = max(
            fitting,
            key=lambda item: (
                item[0]["WindowStart"], item[0]["WindowEnd"]
            ),
            default=None,
        )
        if selected is None:
            return {
                "Feasible": False,
                "PromiseAt": _utc_iso(requested_due_at),
                "WindowAssessments": [],
                "ReservationRequests": [],
                "ConsideredWindowKeys": sorted(considered),
            }
        state, metrics = selected
        latest = _parse_aware(
            metrics["LatestAllowedCompletionAt"],
            "LatestAllowedCompletionAt",
        )
        _commit_candidate(
            state,
            minutes=int(operation["DurationMinutes"]),
            latest_allowed_completion_at=latest,
        )
        assessments.append(
            {
                **metrics,
                "RouteSequence": operation["RouteSequence"],
                "OperationID": operation["OperationID"],
                "ResourceID": resource_id,
                "LoadStatus": classify_ccr_load(
                    load_percent=float(metrics["LoadAfterPercent"]),
                    protective_capacity_target_percent=(
                        protection_threshold_percent
                    ),
                ),
                "ThresholdExceeded": (
                    float(metrics["LoadAfterPercent"])
                    > protection_threshold_percent
                ),
            }
        )
        requests.append(
            _reservation_request(
                order_id=order_id,
                operation=operation,
                state=state,
                operation_deadline=deadline,
            )
        )
    return {
        "Feasible": True,
        "PromiseAt": _utc_iso(requested_due_at),
        "WindowAssessments": sorted(
            assessments, key=lambda row: int(row["RouteSequence"])
        ),
        "ReservationRequests": sorted(
            requests,
            key=lambda row: str(row["OperationID"]),
        ),
        "ConsideredWindowKeys": sorted(considered),
    }
~~~

Forward safe pass:

~~~python
def _earliest_safe_candidate(
    *,
    order_id: str,
    all_route_operations: list[dict[str, object]],
    source_states: Mapping[
        tuple[str, datetime, datetime], dict[str, object]
    ],
    capacity_assessment_cutoff_at: datetime,
    downstream_protection_minutes: int,
    protection_threshold_percent: float,
) -> dict[str, object] | None:
    states = deepcopy(dict(source_states))
    cursor = capacity_assessment_cutoff_at
    assessments: list[dict[str, object]] = []
    requests: list[dict[str, object]] = []
    considered: set[tuple[str, str, str]] = set()
    for operation in sorted(
        all_route_operations,
        key=lambda row: int(row["RouteSequence"]),
    ):
        duration = int(operation["DurationMinutes"])
        if not bool(operation["IsPrimaryCcr"]):
            cursor += timedelta(minutes=duration)
            continue
        resource_id = str(operation["ResourceID"])
        fitting: list[tuple[dict[str, object], dict[str, object]]] = []
        for key, state in states.items():
            if key[0] != resource_id or key[2] <= cursor:
                continue
            considered.add((key[0], _utc_iso(key[1]), _utc_iso(key[2])))
            metrics = _window_metrics(
                state,
                usable_start=cursor,
                deadline=key[2],
                candidate_minutes=duration,
            )
            if metrics["Fits"]:
                fitting.append((state, metrics))
        selected = min(
            fitting,
            key=lambda item: (
                item[0]["WindowEnd"], item[0]["WindowStart"]
            ),
            default=None,
        )
        if selected is None:
            return None
        state, metrics = selected
        completion_at = state["WindowEnd"]
        assert isinstance(completion_at, datetime)
        _commit_candidate(
            state,
            minutes=duration,
            latest_allowed_completion_at=completion_at,
        )
        assessments.append(
            {
                **metrics,
                "RouteSequence": operation["RouteSequence"],
                "OperationID": operation["OperationID"],
                "ResourceID": resource_id,
                "LoadStatus": classify_ccr_load(
                    load_percent=float(metrics["LoadAfterPercent"]),
                    protective_capacity_target_percent=(
                        protection_threshold_percent
                    ),
                ),
                "ThresholdExceeded": (
                    float(metrics["LoadAfterPercent"])
                    > protection_threshold_percent
                ),
            }
        )
        requests.append(
            _reservation_request(
                order_id=order_id,
                operation=operation,
                state=state,
                operation_deadline=completion_at,
            )
        )
        cursor = completion_at
    return {
        "Feasible": True,
        "PromiseAt": _utc_iso(
            cursor + timedelta(minutes=downstream_protection_minutes)
        ),
        "WindowAssessments": assessments,
        "ReservationRequests": requests,
        "ConsideredWindowKeys": sorted(considered),
    }
~~~

Add the public evaluator with this complete body; it is the first task that exports the public symbol:

~~~python
def _not_assessable_result(
    *,
    requested_due_at: datetime,
    capacity_assessment_cutoff_at: datetime,
    issues: list[dict[str, object]],
) -> dict[str, object]:
    return {
        "Algorithm": deepcopy(SHADOW_ALGORITHM),
        "Status": "NotAssessable",
        "CapacityAssessmentCutoffAt": _utc_iso(
            capacity_assessment_cutoff_at
        ),
        "RequestedDueAt": _utc_iso(requested_due_at),
        "LatestCcrCompletionAt": None,
        "RequestedDateAssessment": {"Feasible": False},
        "EarliestSafeAssessment": None,
        "SelectedAssessment": None,
        "RelevantCapacityWindowKeys": [],
        "Issues": deepcopy(issues),
        "Summary": {
            "CcrOperationCount": 0,
            "SelectedWindowCount": 0,
            "MaximumLoadAfterPercent": None,
        },
    }


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
    _validate_shadow_request(
        order_id=order_id,
        quantity=quantity,
        requested_due_at=requested_due_at,
        evaluated_at=evaluated_at,
        downstream_protection_minutes=downstream_protection_minutes,
        protection_threshold_percent=protection_threshold_percent,
    )
    requested_due_at = _utc(requested_due_at)
    cutoff = _utc(evaluated_at)
    all_operations, ccr_operations, issues = _extract_route_operations(
        order_id=order_id,
        quantity=quantity,
        routing=routing,
        resources=resources,
        setup_transitions=setup_transitions,
    )
    if issues:
        return _not_assessable_result(
            requested_due_at=requested_due_at,
            capacity_assessment_cutoff_at=cutoff,
            issues=issues,
        )
    try:
        states = _build_window_states(
            resources=resources,
            capacity_buckets=capacity_buckets,
            ccr_resource_ids={
                str(row["ResourceID"]) for row in ccr_operations
            },
            gantt_rows=gantt_rows,
            active_capacity_reservations=active_capacity_reservations,
        )
    except ValueError as error:
        return _not_assessable_result(
            requested_due_at=requested_due_at,
            capacity_assessment_cutoff_at=cutoff,
            issues=[_issue("CAPACITY_EVIDENCE_INVALID", str(error))],
        )
    deadlines = _route_deadlines(
        all_route_operations=all_operations,
        requested_due_at=requested_due_at,
        downstream_protection_minutes=downstream_protection_minutes,
    )
    requested = _requested_candidate(
        order_id=order_id,
        requested_due_at=requested_due_at,
        capacity_assessment_cutoff_at=cutoff,
        ccr_operations=ccr_operations,
        deadlines=deadlines,
        source_states=states,
        protection_threshold_percent=protection_threshold_percent,
    )
    earliest_safe = None
    status = "OnTime"
    selected = requested
    if not bool(requested["Feasible"]):
        earliest_safe = _earliest_safe_candidate(
            order_id=order_id,
            all_route_operations=all_operations,
            source_states=states,
            capacity_assessment_cutoff_at=cutoff,
            downstream_protection_minutes=downstream_protection_minutes,
            protection_threshold_percent=protection_threshold_percent,
        )
        if earliest_safe is None:
            return _not_assessable_result(
                requested_due_at=requested_due_at,
                capacity_assessment_cutoff_at=cutoff,
                issues=[_issue("NO_SAFE_CCR_WINDOW")],
            )
        status = "LaterSafeDate"
        selected = earliest_safe
    considered = {
        tuple(row)
        for assessment in (requested, earliest_safe)
        if isinstance(assessment, Mapping)
        for row in assessment.get("ConsideredWindowKeys", [])
    }
    window_rows = list(selected["WindowAssessments"])
    return {
        "Algorithm": deepcopy(SHADOW_ALGORITHM),
        "Status": status,
        "CapacityAssessmentCutoffAt": _utc_iso(cutoff),
        "RequestedDueAt": _utc_iso(requested_due_at),
        "LatestCcrCompletionAt": _utc_iso(
            requested_due_at
            - timedelta(minutes=downstream_protection_minutes)
        ),
        "RequestedDateAssessment": requested,
        "EarliestSafeAssessment": earliest_safe,
        "SelectedAssessment": selected,
        "RelevantCapacityWindowKeys": sorted(considered),
        "Issues": [],
        "Summary": {
            "CcrOperationCount": len(ccr_operations),
            "SelectedWindowCount": len(
                selected["ReservationRequests"]
            ),
            "MaximumLoadAfterPercent": max(
                (
                    float(row["LoadAfterPercent"])
                    for row in window_rows
                ),
                default=None,
            ),
        },
    }
~~~

No later candidate returns `NotAssessable`, issue `NO_SAFE_CCR_WINDOW`, and no selected/reservation rows. Apply the bodies above only in the slice that names them; do not paste all three production blocks before the first RED run.

- [ ] **Step 1C (requested-date GREEN/commit): verify exactly three items**

~~~powershell
pytest tests/test_ccr_shadow_scheduler.py::TestCcrShadowPromiseSelection::test_requested_candidate_walks_route_backward_and_returns_on_time tests/test_ccr_shadow_scheduler.py::TestCcrShadowPromiseSelection::test_low_load_only_after_deadline_never_makes_request_on_time tests/test_ccr_shadow_scheduler.py::TestCcrShadowPromiseSelection::test_initial_requested_pass_cannot_use_elapsed_shift_minutes -q --basetemp .tmp/pytest-mto-shadow-requested-green -p no:cacheprovider
python -m compileall -q sdbr
git add -- sdbr/ccr_shadow_scheduler.py tests/test_ccr_shadow_scheduler.py
git commit -m "feat: honor the MTO capacity cutoff"
~~~

Expected: exactly three items pass.

- [ ] **Step 2A (earliest-safe RED): add and run the three forward-pass items**

~~~powershell
pytest tests/test_ccr_shadow_scheduler.py::TestCcrShadowPromiseSelection::test_late_requested_candidate_returns_earliest_safe_promise tests/test_ccr_shadow_scheduler.py::TestCcrShadowPromiseSelection::test_multi_ccr_route_uses_per_operation_deadlines_and_route_order tests/test_ccr_shadow_scheduler.py::TestCcrShadowPromiseSelection::test_no_later_window_returns_not_assessable_without_reservation_requests --collect-only -q
pytest tests/test_ccr_shadow_scheduler.py::TestCcrShadowPromiseSelection::test_late_requested_candidate_returns_earliest_safe_promise tests/test_ccr_shadow_scheduler.py::TestCcrShadowPromiseSelection::test_multi_ccr_route_uses_per_operation_deadlines_and_route_order tests/test_ccr_shadow_scheduler.py::TestCcrShadowPromiseSelection::test_no_later_window_returns_not_assessable_without_reservation_requests -q --basetemp .tmp/pytest-mto-shadow-forward-red -p no:cacheprovider
~~~

Expected: exactly three items collect and fail because
`_earliest_safe_candidate` and the no-safe result path are absent.

- [ ] **Step 2B (earliest-safe implement): add `_earliest_safe_candidate` and `_not_assessable_result` from the complete blocks above**

- [ ] **Step 2C (earliest-safe GREEN/commit): verify exactly three items**

~~~powershell
pytest tests/test_ccr_shadow_scheduler.py::TestCcrShadowPromiseSelection::test_late_requested_candidate_returns_earliest_safe_promise tests/test_ccr_shadow_scheduler.py::TestCcrShadowPromiseSelection::test_multi_ccr_route_uses_per_operation_deadlines_and_route_order tests/test_ccr_shadow_scheduler.py::TestCcrShadowPromiseSelection::test_no_later_window_returns_not_assessable_without_reservation_requests -q --basetemp .tmp/pytest-mto-shadow-forward-green -p no:cacheprovider
python -m compileall -q sdbr
git add -- sdbr/ccr_shadow_scheduler.py tests/test_ccr_shadow_scheduler.py
git commit -m "feat: select the earliest safe MTO promise"
~~~

Expected: exactly three items pass.

- [ ] **Step 3A (public evaluator RED): add the exact-window evidence item**

~~~powershell
pytest tests/test_ccr_shadow_scheduler.py::TestCcrShadowPromiseSelection::test_selected_evidence_lists_exact_relevant_capacity_window_keys --collect-only -q
pytest tests/test_ccr_shadow_scheduler.py::TestCcrShadowPromiseSelection::test_selected_evidence_lists_exact_relevant_capacity_window_keys -q --basetemp .tmp/pytest-mto-shadow-public-red -p no:cacheprovider
~~~

Expected: exactly one item collects and fails because
`evaluate_ccr_shadow_schedule` is absent.

- [ ] **Step 3B (public evaluator implement): add `evaluate_ccr_shadow_schedule` from the complete block above**

- [ ] **Step 3C (public evaluator GREEN/commit): verify one item, then all seven class items**

~~~powershell
pytest tests/test_ccr_shadow_scheduler.py::TestCcrShadowPromiseSelection::test_selected_evidence_lists_exact_relevant_capacity_window_keys -q --basetemp .tmp/pytest-mto-shadow-public-green -p no:cacheprovider
pytest tests/test_ccr_shadow_scheduler.py::TestCcrShadowPromiseSelection --collect-only -q
pytest tests/test_ccr_shadow_scheduler.py -q --basetemp .tmp/pytest-mto-shadow-complete -p no:cacheprovider
python -m compileall -q sdbr
git add -- sdbr/ccr_shadow_scheduler.py tests/test_ccr_shadow_scheduler.py
git commit -m "feat: expose the MTO shadow evaluation"
~~~

Expected: the focused item passes, exactly seven class items collect, and the complete scheduler file passes.

---

### Task 6: Canonical MTO Order and Protection Policy

**Files and anchors**
- Create `sdbr/order_commitment_evaluation.py`.
- Create `tests/test_order_commitment_evaluation.py`.

**IDs:** `BE-SDBR-006`, `BE-SDBR-010`.

**Produces**

~~~python
from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
from math import isfinite
from numbers import Real
from typing import Literal

from sdbr.operational_state import (
    OperationalStateSnapshot,
    evaluate_operational_state_freshness,
)
from sdbr.planner_view import InventoryBufferPolicy
from sdbr.planning_commitments import (
    create_demand_commitment,
    normalize_demand_commitment,
)
from sdbr.planning_reservation_view import (
    ACTIVE_PLANNING_STATUSES,
    planning_allocated_qty_for_other_demands,
)
from sdbr.planning_reservations import (
    PlanningReservationWriteSet,
    prepare_reservation_confirmation,
)
from sdbr.release_candidates import MaterialAvailability


class OrderCommitmentConflict(ValueError):
    status = "OrderCommitmentConflict"

class OrderCommitmentStale(OrderCommitmentConflict):
    status = "OrderCommitmentEvaluationStale"

class OrderCommitmentSnapshotNotFound(OrderCommitmentConflict):
    status = "OperationalStateSnapshotNotFound"

    def __init__(self, snapshot_id: str) -> None:
        self.snapshot_id = snapshot_id
        super().__init__(
            f"Operational state snapshot was not found: {snapshot_id}."
        )

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

def require_aware(value: datetime, field: str) -> datetime:
    if not isinstance(value, datetime):
        raise OrderCommitmentConflict(f"{field} must be a datetime.")
    if value.tzinfo is None or value.utcoffset() is None:
        raise OrderCommitmentConflict(f"{field} must be timezone-aware.")
    return value


def _utc(value: datetime) -> datetime:
    require_aware(value, "Datetime")
    return value.astimezone(timezone.utc)


def _parse_aware(value: object) -> datetime:
    if isinstance(value, datetime):
        return _utc(value)
    try:
        return _utc(datetime.fromisoformat(str(value).replace("Z", "+00:00")))
    except (TypeError, ValueError) as error:
        raise OrderCommitmentConflict("Datetime must be timezone-aware.") from error


def _utc_iso(value: datetime) -> str:
    return _utc(value).isoformat()


def canonical_json(value: object) -> str:
    return json.dumps(
        value,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    )


def canonical_fingerprint(value: object) -> str:
    return f"sha256:{sha256(canonical_json(value).encode('utf-8')).hexdigest()}"
~~~

- [ ] **Step 1: Write order/policy tests**

Add `TestMtoOrderAndProtectionPolicy`:

- `test_normalize_mto_order_derives_stable_versioned_and_logical_identity`;
- `test_order_fingerprint_covers_sorted_material_requirements_but_not_evaluation_time`;
- `test_order_rejects_blank_identity_naive_times_duplicate_requirements_and_nonfinite_quantity`;
- `test_reference_policy_is_exactly_unapproved_80_percent`;
- `test_approved_policy_requires_configuration_and_reference_policy_rejects_configuration`.

~~~powershell
pytest tests/test_order_commitment_evaluation.py::TestMtoOrderAndProtectionPolicy -q --basetemp .tmp/pytest-mto-order-red -p no:cacheprovider
~~~

Expected: import fails because the module is absent.

- [ ] **Step 2: Implement canonical content**

Canonical order fields:

~~~python
ORDER_CONTENT_FIELDS = (
    "SourceSystem", "SourceObjectType", "OrderID", "OrderVersion",
    "DemandLineID", "ProductID", "LocationID", "Quantity", "Uom",
    "RequestedDueAt", "BusinessPriority", "ReceivedAt", "TraceID",
    "BaselinePlanningRunID", "RoutingID", "MaterialRequirements",
)

def _positive_number(value: object, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise OrderCommitmentConflict(f"{field} must be finite and positive.")
    normalized = float(value)
    if not isfinite(normalized) or normalized <= 0:
        raise OrderCommitmentConflict(f"{field} must be finite and positive.")
    return normalized


def _required_text(record: Mapping[str, object], field: str) -> str:
    value = record.get(field)
    if not isinstance(value, str) or not value.strip():
        raise OrderCommitmentConflict(f"{field} is required.")
    return value.strip()
~~~

Normalize with this complete function; it also persists the intake version rank used by Task 17:

~~~python
def normalize_mto_order(record: Mapping[str, object]) -> dict[str, object]:
    text_fields = (
        "SourceSystem", "SourceObjectType", "OrderID", "OrderVersion",
        "DemandLineID", "ProductID", "LocationID", "Uom", "TraceID",
        "BaselinePlanningRunID", "RoutingID",
    )
    order = {field: _required_text(record, field) for field in text_fields}
    order["Quantity"] = _positive_number(record.get("Quantity"), "Quantity")
    order["RequestedDueAt"] = _parse_aware(
        record.get("RequestedDueAt")
    ).isoformat()
    received_at = _parse_aware(record.get("ReceivedAt"))
    order["ReceivedAt"] = received_at.isoformat()
    priority = record.get("BusinessPriority")
    if isinstance(priority, bool) or not isinstance(priority, int) or not 1 <= priority <= 999:
        raise OrderCommitmentConflict("BusinessPriority must be in 1..999.")
    order["BusinessPriority"] = priority
    raw_requirements = record.get("MaterialRequirements")
    if not isinstance(raw_requirements, list):
        raise OrderCommitmentConflict("MaterialRequirements must be a list.")
    requirements: list[dict[str, object]] = []
    identities: set[tuple[str, str, str]] = set()
    for raw in raw_requirements:
        if not isinstance(raw, Mapping):
            raise OrderCommitmentConflict("Material requirement must be an object.")
        requirement = {
            "RequirementLineID": _required_text(raw, "RequirementLineID"),
            "ItemID": _required_text(raw, "ItemID"),
            "LocationID": _required_text(raw, "LocationID"),
            "RequiredQty": _positive_number(raw.get("RequiredQty"), "RequiredQty"),
            "Uom": _required_text(raw, "Uom"),
        }
        identity = (
            str(requirement["ItemID"]),
            str(requirement["LocationID"]),
            str(requirement["RequirementLineID"]),
        )
        if identity in identities:
            raise OrderCommitmentConflict("Material requirement identity is duplicated.")
        identities.add(identity)
        requirements.append(requirement)
    order["MaterialRequirements"] = sorted(
        requirements,
        key=lambda row: str(row["RequirementLineID"]),
    )
    identity = {
        "SourceSystem": order["SourceSystem"],
        "SourceObjectType": order["SourceObjectType"],
        "OrderID": order["OrderID"],
        "OrderVersion": order["OrderVersion"],
        "DemandLineID": order["DemandLineID"],
        "ProductID": order["ProductID"],
        "LocationID": order["LocationID"],
    }
    order["OrderKey"] = canonical_json(identity)
    order["LogicalOrderKey"] = canonical_json(
        {key: value for key, value in identity.items() if key != "OrderVersion"}
    )
    order["OrderVersionRank"] = [
        order["ReceivedAt"], order["OrderVersion"]
    ]
    order["PlanningOrderID"] = f"{order['OrderID']}:{order['DemandLineID']}"
    order["OrderContentFingerprint"] = canonical_fingerprint(
        {field: order[field] for field in ORDER_CONTENT_FIELDS}
    )
    return order


def candidate_demand_commitment_id(order: Mapping[str, object]) -> str:
    return str(create_demand_commitment(
        demand_source_type="MTOCustomerOrder",
        source_system=str(order["SourceSystem"]),
        source_object_type=str(order["SourceObjectType"]),
        source_object_id=str(order["OrderID"]),
        source_object_version=str(order["OrderVersion"]),
        demand_line_id=str(order["DemandLineID"]),
        item_or_product_id=str(order["ProductID"]),
        location_id=str(order["LocationID"]),
        quantity=float(order["Quantity"]),
        uom=str(order["Uom"]),
        required_at=_parse_aware(order["RequestedDueAt"]),
        demand_class="MTO",
        trace_id=str(order["TraceID"]),
    )["DemandCommitmentID"])
~~~

`candidate_demand_commitment_id` calls `create_demand_commitment` using requested due time and returns its canonical `DemandCommitmentID`; do not recreate Phase 0 identity logic.

Normalize policy with this complete function:

~~~python
def normalized_policy_dict(
    policy: CcrProtectionPolicy,
) -> dict[str, object]:
    target = _positive_number(policy.target_percent, "TargetPercent")
    configuration_id = (
        policy.configuration_id.strip()
        if isinstance(policy.configuration_id, str)
        and policy.configuration_id.strip()
        else None
    )
    if policy.source == "ApprovedOperatingModel":
        if not policy.approved or configuration_id is None or target > 100:
            raise OrderCommitmentConflict("Approved policy is inconsistent.")
    elif policy.source == "ReferenceFallback":
        if policy.approved or configuration_id is not None or target != 80.0:
            raise OrderCommitmentConflict("Reference policy must be unapproved 80%.")
    else:
        raise OrderCommitmentConflict("Protection policy source is unsupported.")
    return {
        "TargetPercent": target,
        "Source": policy.source,
        "Approved": policy.approved,
        "ConfigurationID": configuration_id,
    }
~~~

- [ ] **Step 3: Verify and commit**

~~~powershell
pytest tests/test_order_commitment_evaluation.py::TestMtoOrderAndProtectionPolicy --collect-only -q
pytest tests/test_order_commitment_evaluation.py::TestMtoOrderAndProtectionPolicy tests/test_planning_commitments.py -q --basetemp .tmp/pytest-mto-order-green -p no:cacheprovider
git add -- sdbr/order_commitment_evaluation.py tests/test_order_commitment_evaluation.py
git commit -m "feat: define canonical MTO commitment identity"
~~~

Expected: five class tests and Phase 0 identity regressions pass.

---

### Task 7: Current Operational Snapshot Selection and Freshness

**Files and anchors**
- Modify `sdbr/order_commitment_evaluation.py` after policy definitions.
- Modify `tests/test_order_commitment_evaluation.py` after order tests.

**IDs:** `BE-SDBR-010`.

**Consumes:** `OperationalStateSnapshot`, `evaluate_operational_state_freshness`.

**Produces**

~~~python
ORDER_COMMITMENT_OPERATIONAL_STATE_MAX_AGE_MINUTES = 60

def select_order_commitment_operational_snapshot(
    *,
    snapshots: Mapping[str, OperationalStateSnapshot],
    evaluated_at: datetime,
    requested_snapshot_id: str | None,
) -> dict[str, object]:
~~~

- [ ] **Step 1: Write freshness tests**

Add `TestOrderCommitmentSnapshotFreshness`:

- `test_default_selection_uses_latest_nonfuture_snapshot_with_id_tiebreak`;
- `test_explicit_fresh_snapshot_is_selected_exactly`;
- `test_snapshot_at_sixty_minutes_is_fresh`;
- `test_snapshot_older_than_sixty_minutes_is_stale`;
- `test_explicit_future_snapshot_is_future_and_unacceptable`;
- `test_no_nonfuture_snapshot_returns_no_current_snapshot`;
- `test_unknown_explicit_snapshot_raises_snapshot_not_found`.

~~~powershell
pytest tests/test_order_commitment_evaluation.py::TestOrderCommitmentSnapshotFreshness -q --basetemp .tmp/pytest-mto-freshness-red -p no:cacheprovider
~~~

Expected: seven failures because selection is absent.

- [ ] **Step 2: Implement deterministic selection**

~~~python
def select_order_commitment_operational_snapshot(
    *,
    snapshots: Mapping[str, OperationalStateSnapshot],
    evaluated_at: datetime,
    requested_snapshot_id: str | None,
) -> dict[str, object]:
    evaluated_at = _utc(require_aware(evaluated_at, "evaluated_at"))
    requested = (
        requested_snapshot_id.strip()
        if isinstance(requested_snapshot_id, str)
        and requested_snapshot_id.strip()
        else None
    )
    mode = "Explicit" if requested is not None else "LatestCurrent"
    if requested is not None:
        snapshot = snapshots.get(requested)
        if snapshot is None:
            raise OrderCommitmentSnapshotNotFound(requested)
    else:
        eligible = [
            row for row in snapshots.values()
            if row.captured_at <= evaluated_at
        ]
        snapshot = max(
            eligible,
            key=lambda row: (row.captured_at, row.snapshot_id),
            default=None,
        )
    if snapshot is None:
        return {
            "SnapshotSelectionMode": mode,
            "RequestedOperationalStateSnapshotID": requested,
            "OperationalStateSnapshot": None,
            "OperationalStateSnapshotID": None,
            "OperationalStateCapturedAt": None,
            "OperationalStateFreshnessStatus": "Missing",
            "OperationalStateAgeMinutes": None,
            "OperationalStateMaxAgeMinutes": 60,
            "OperationalStateValidThroughAt": None,
            "Acceptable": False,
        }
    freshness = evaluate_operational_state_freshness(
        snapshot=snapshot,
        evaluated_at=evaluated_at,
        max_age_minutes=60,
    )
    return {
        "SnapshotSelectionMode": mode,
        "RequestedOperationalStateSnapshotID": requested,
        "OperationalStateSnapshot": snapshot,
        "OperationalStateSnapshotID": snapshot.snapshot_id,
        "OperationalStateCapturedAt": snapshot.captured_at.isoformat(),
        "OperationalStateFreshnessStatus": freshness.status,
        "OperationalStateAgeMinutes": freshness.age_minutes,
        "OperationalStateMaxAgeMinutes": freshness.max_age_minutes,
        "OperationalStateValidThroughAt": (
            snapshot.captured_at + timedelta(minutes=60)
        ).isoformat(),
        "Acceptable": freshness.acceptable,
    }
~~~

`OrderCommitmentSnapshotNotFound` was defined in Task 6, carries status `OperationalStateSnapshotNotFound`, and retains the missing ID in `snapshot_id`. Do not choose a future row in latest mode.

- [ ] **Step 3: Verify and commit**

~~~powershell
pytest tests/test_order_commitment_evaluation.py::TestOrderCommitmentSnapshotFreshness --collect-only -q
pytest tests/test_order_commitment_evaluation.py::TestOrderCommitmentSnapshotFreshness tests/test_operational_state.py -q --basetemp .tmp/pytest-mto-freshness-green -p no:cacheprovider
git add -- sdbr/order_commitment_evaluation.py tests/test_order_commitment_evaluation.py
git commit -m "feat: gate MTO evidence by current snapshot"
~~~

Expected: seven class tests and existing freshness tests pass.

---

### Task 8: Default-On Material Feasibility

**Files and anchors**
- Modify `sdbr/order_commitment_evaluation.py`; add `evaluate_mto_material_availability`.
- Modify `tests/test_order_commitment_evaluation.py` after freshness tests.

**IDs:** `BE-SDBR-009`, `BE-SDBR-010`.

**Produces**

~~~python
def evaluate_mto_material_availability(
    *,
    order: Mapping[str, object],
    snapshot_selection: Mapping[str, object],
    active_material_allocations: list[dict[str, object]],
    current_demand_commitment_id: str,
    evaluated_at: datetime,
    material_check_window_minutes: int,
    check_material_availability: bool = True,
    skip_reason: str | None = None,
) -> dict[str, object]:
~~~

`evaluated_at` is the single server observation passed by orchestration. The function canonicalizes it once as `MaterialEligibilityCutoffAt = evaluated_at + material_check_window_minutes` when checking is enabled and stores `None` when checking is disabled.

- [ ] **Step 1: Write material tests**

Add `TestOrderCommitmentMaterialFeasibility`:

- `test_check_defaults_on_and_uses_uncommitted_shared_availability`;
- `test_skip_requires_reason_records_pending_requirements_and_zero_allocations`;
- `test_stale_snapshot_returns_evidence_insufficient_and_zero_allocations`;
- `test_future_snapshot_returns_evidence_insufficient_and_zero_allocations`;
- `test_missing_snapshot_or_required_item_row_is_evidence_insufficient`;
- `test_inbound_counts_only_when_aware_and_inside_frozen_material_window`;
- `test_shortage_is_all_or_nothing_and_returns_no_allocation_requests`;
- `test_current_demand_allocation_is_not_subtracted_twice`;
- `test_same_item_location_lines_use_cumulative_candidate_balance`;
- `test_same_item_location_coverage_is_independent_of_input_line_order`;
- `test_feasible_same_item_location_allocations_sum_to_accepted_total`;
- `test_malformed_unrelated_material_allocation_is_ignored_but_matching_malformed_row_is_insufficient`.

Install this exact helper and the three new cumulative-accounting tests in the
class. The existing shortage test uses the same helper with quantities `3`
and `3` and asserts `AllocationRequests == []`.

~~~python
    @staticmethod
    def _same_key_material_result(requirements, *, on_hand=5.0):
        observed_at = datetime(2026, 7, 11, 8, tzinfo=UTC)
        snapshot = OperationalStateSnapshot(
            snapshot_id="OPS-1",
            captured_at=observed_at,
            inventory_buffers=[
                InventoryBufferPolicy(
                    "RM-1", "MAIN", on_hand, 0.0, 0.0, 0.0
                )
            ],
            material_availability=[
                MaterialAvailability("RM-1", "MAIN")
            ],
            wip_limits=[],
        )
        selection = select_order_commitment_operational_snapshot(
            snapshots={snapshot.snapshot_id: snapshot},
            evaluated_at=observed_at,
            requested_snapshot_id=snapshot.snapshot_id,
        )
        return evaluate_mto_material_availability(
            order={"MaterialRequirements": deepcopy(requirements)},
            snapshot_selection=selection,
            active_material_allocations=[],
            current_demand_commitment_id="DC-CURRENT",
            evaluated_at=observed_at,
            material_check_window_minutes=0,
        )

    def test_same_item_location_lines_use_cumulative_candidate_balance(self):
        requirements = [
            {"RequirementLineID": "L1", "ItemID": "RM-1",
             "LocationID": "MAIN", "RequiredQty": 3.0, "Uom": "EA"},
            {"RequirementLineID": "L2", "ItemID": "RM-1",
             "LocationID": "MAIN", "RequiredQty": 3.0, "Uom": "EA"},
        ]
        result = self._same_key_material_result(requirements)
        assert result["Status"] == "Shortage"
        assert [row["CoverageStatus"] for row in result["Lines"]] == [
            "Covered", "Shortage"
        ]
        assert [
            row["UncommittedAvailabilityQty"] for row in result["Lines"]
        ] == [5.0, 2.0]
        assert result["AllocationRequests"] == []

    def test_same_item_location_coverage_is_independent_of_input_line_order(self):
        requirements = [
            {"RequirementLineID": "L2", "ItemID": "RM-1",
             "LocationID": "MAIN", "RequiredQty": 3.0, "Uom": "EA"},
            {"RequirementLineID": "L1", "ItemID": "RM-1",
             "LocationID": "MAIN", "RequiredQty": 3.0, "Uom": "EA"},
        ]
        forward = self._same_key_material_result(requirements)
        reverse = self._same_key_material_result(list(reversed(requirements)))
        assert forward == reverse

    def test_feasible_same_item_location_allocations_sum_to_accepted_total(self):
        requirements = [
            {"RequirementLineID": "L2", "ItemID": "RM-1",
             "LocationID": "MAIN", "RequiredQty": 2.0, "Uom": "EA"},
            {"RequirementLineID": "L1", "ItemID": "RM-1",
             "LocationID": "MAIN", "RequiredQty": 2.0, "Uom": "EA"},
        ]
        result = self._same_key_material_result(requirements)
        assert result["Status"] == "Feasible"
        assert [
            row["RequirementLineID"]
            for row in result["AllocationRequests"]
        ] == ["L1", "L2"]
        assert sum(
            row["AllocatedQty"] for row in result["AllocationRequests"]
        ) == 4.0
~~~

Extend the test imports with `deepcopy`, `OperationalStateSnapshot`,
`InventoryBufferPolicy`, and `MaterialAvailability`; all four symbols are
available before this task from the Task 6 production imports or their live
modules.

~~~powershell
pytest tests/test_order_commitment_evaluation.py::TestOrderCommitmentMaterialFeasibility -q --basetemp .tmp/pytest-mto-material-red -p no:cacheprovider
~~~

Expected: twelve collected items fail because material evaluation is absent.

- [ ] **Step 2: Implement all branches**

Add this complete local result builder before the public function; no undefined `evidence_insufficient` symbol is used:

~~~python
def _material_evidence_insufficient(
    *,
    evidence: Mapping[str, object],
    order: Mapping[str, object],
    code: str,
    details: Mapping[str, object] | None = None,
) -> dict[str, object]:
    return {
        **deepcopy(dict(evidence)),
        "Status": "EvidenceInsufficient",
        "Lines": [],
        "AllocationRequests": [],
        "PendingRequirements": deepcopy(order["MaterialRequirements"]),
        "Issues": [{"Code": code, **deepcopy(dict(details or {}))}],
    }
~~~

Start the public function body exactly with:

~~~python
selection = snapshot_selection
normalized_skip_reason = (
    skip_reason.strip()
    if isinstance(skip_reason, str) and skip_reason.strip()
    else None
)
if material_check_window_minutes < 0:
    raise OrderCommitmentConflict("Material check window cannot be negative.")
material_cutoff = (
    _utc(evaluated_at)
    + timedelta(minutes=material_check_window_minutes)
    if check_material_availability
    else None
)
evidence = {
    "CheckEnabled": bool(check_material_availability),
    "SkipReason": normalized_skip_reason,
    "MaterialCheckWindowMinutes": material_check_window_minutes,
    "MaterialEligibilityCutoffAt": (
        material_cutoff.isoformat() if material_cutoff is not None else None
    ),
    "SnapshotSelectionMode": selection["SnapshotSelectionMode"],
    "RequestedOperationalStateSnapshotID": selection[
        "RequestedOperationalStateSnapshotID"
    ],
    "OperationalStateSnapshotID": selection[
        "OperationalStateSnapshotID"
    ],
    "OperationalStateCapturedAt": selection[
        "OperationalStateCapturedAt"
    ],
    "OperationalStateFreshnessStatus": selection[
        "OperationalStateFreshnessStatus"
    ],
    "OperationalStateAgeMinutes": selection[
        "OperationalStateAgeMinutes"
    ],
    "OperationalStateMaxAgeMinutes": 60,
    "OperationalStateValidThroughAt": selection[
        "OperationalStateValidThroughAt"
    ],
    "ReleaseGateStillRequired": True,
}
~~~

Exact branch order:

~~~python
if not check_material_availability:
    if not normalized_skip_reason:
        raise OrderCommitmentConflict("Material check skip reason is required.")
    return {
        **evidence,
        "Status": "SkippedPendingConfirmation",
        "Lines": [],
        "AllocationRequests": [],
        "PendingRequirements": deepcopy(order["MaterialRequirements"]),
    }
if not selection["Acceptable"]:
    return _material_evidence_insufficient(
        evidence=evidence,
        order=order,
        code="OPERATIONAL_STATE_EVIDENCE_NOT_FRESH",
        details={
            "FreshnessStatus": selection[
                "OperationalStateFreshnessStatus"
            ]
        },
    )
if not order["MaterialRequirements"]:
    return _material_evidence_insufficient(
        evidence=evidence,
        order=order,
        code="MATERIAL_REQUIREMENTS_MISSING",
    )
~~~

Continue the same function with this exact relevant-row prefilter and loop. It intentionally filters before calling the live globally validating allocation helper:

~~~python
snapshot = selection["OperationalStateSnapshot"]
if snapshot is None or material_cutoff is None:
    return _material_evidence_insufficient(
        evidence=evidence,
        order=order,
        code="OPERATIONAL_STATE_EVIDENCE_MISSING",
    )
requirements = sorted(
    deepcopy(order["MaterialRequirements"]),
    key=lambda row: (
        str(row["ItemID"]),
        str(row["LocationID"]),
        str(row["RequirementLineID"]),
    ),
)
relevant_keys = {
    (str(row["ItemID"]), str(row["LocationID"]))
    for row in requirements
}
relevant_allocations = [
    deepcopy(row)
    for row in active_material_allocations
    if (
        str(row.get("ItemID") or ""),
        str(row.get("LocationID") or ""),
    ) in relevant_keys
]
buffers = {
    (row.item_id, row.location_id): row
    for row in snapshot.inventory_buffers
    if (row.item_id, row.location_id) in relevant_keys
}
availability_rows = {
    (row.item_id, row.location_id): row
    for row in snapshot.material_availability
    if (row.item_id, row.location_id) in relevant_keys
}
if set(buffers) != relevant_keys or set(availability_rows) != relevant_keys:
    return _material_evidence_insufficient(
        evidence=evidence,
        order=order,
        code="REQUIRED_MATERIAL_EVIDENCE_MISSING",
    )
lines: list[dict[str, object]] = []
allocation_requests: list[dict[str, object]] = []
try:
    supply_by_key: dict[
        tuple[str, str], dict[str, float | str]
    ] = {}
    for key in sorted(relevant_keys):
        buffer = buffers[key]
        availability = availability_rows[key]
        inbound_at = availability.inbound_available_at
        if inbound_at is not None:
            inbound_at = _utc(inbound_at)
        eligible_inbound = (
            float(availability.inbound_qty)
            if inbound_at is not None and inbound_at <= material_cutoff
            else 0.0
        )
        other_planning = planning_allocated_qty_for_other_demands(
            allocations=relevant_allocations,
            item_id=key[0],
            location_id=key[1],
            current_demand_commitment_id=current_demand_commitment_id,
        )
        qualified = float(buffer.on_hand_qty) + eligible_inbound
        uncommitted = max(
            qualified
            - float(availability.allocated_qty)
            - other_planning,
            0.0,
        )
        supply_by_key[key] = {
            "OnHandQty": float(buffer.on_hand_qty),
            "EligibleInboundQty": eligible_inbound,
            "AuthorityAllocatedQty": float(availability.allocated_qty),
            "OtherPlanningAllocatedQty": other_planning,
            "QualifiedSupplyQty": qualified,
            "UncommittedAvailabilityQty": uncommitted,
            "SupplySourceType": (
                "OnHandAndInbound" if eligible_inbound > 0 else "OnHand"
            ),
        }

    remaining_by_key = {
        key: float(row["UncommittedAvailabilityQty"])
        for key, row in supply_by_key.items()
    }
    for requirement in requirements:
        key = (
            str(requirement["ItemID"]),
            str(requirement["LocationID"]),
        )
        supply = supply_by_key[key]
        required = float(requirement["RequiredQty"])
        available_before_line = remaining_by_key[key]
        covered = available_before_line >= required
        if covered:
            remaining_by_key[key] = available_before_line - required
        lines.append(
            {
                "RequirementLineID": requirement["RequirementLineID"],
                "ItemID": key[0],
                "LocationID": key[1],
                "Uom": requirement["Uom"],
                "RequiredQty": required,
                "OnHandQty": supply["OnHandQty"],
                "EligibleInboundQty": supply["EligibleInboundQty"],
                "AuthorityAllocatedQty": supply[
                    "AuthorityAllocatedQty"
                ],
                "OtherPlanningAllocatedQty": supply[
                    "OtherPlanningAllocatedQty"
                ],
                "QualifiedSupplyQty": supply["QualifiedSupplyQty"],
                "UncommittedAvailabilityQty": available_before_line,
                "CoverageStatus": "Covered" if covered else "Shortage",
            }
        )
        if covered:
            allocation_requests.append(
                {
                    "RequirementLineID": requirement[
                        "RequirementLineID"
                    ],
                    "ItemID": key[0],
                    "LocationID": key[1],
                    "Uom": requirement["Uom"],
                    "AllocatedQty": required,
                    "SupplySourceType": supply["SupplySourceType"],
                    "MaterialSnapshotID": selection[
                        "OperationalStateSnapshotID"
                    ],
                }
            )
except (TypeError, ValueError, OverflowError) as error:
    return _material_evidence_insufficient(
        evidence=evidence,
        order=order,
        code="MATERIAL_EVIDENCE_INVALID",
        details={"Message": str(error)},
    )
if any(row["CoverageStatus"] == "Shortage" for row in lines):
    return {
        **evidence,
        "Status": "Shortage",
        "Lines": lines,
        "AllocationRequests": [],
        "PendingRequirements": deepcopy(requirements),
        "Issues": [],
    }
return {
    **evidence,
    "Status": "Feasible",
    "Lines": lines,
    "AllocationRequests": allocation_requests,
    "PendingRequirements": [],
    "Issues": [],
}
~~~

The material opt-out decision-basis test belongs to Task 10, where that basis
is created. Keep only the malformed relevant/unrelated allocation test in this
task.

- [ ] **Step 3A (freshness/skip RED): run the four branch items**

~~~powershell
pytest tests/test_order_commitment_evaluation.py::TestOrderCommitmentMaterialFeasibility::test_skip_requires_reason_records_pending_requirements_and_zero_allocations tests/test_order_commitment_evaluation.py::TestOrderCommitmentMaterialFeasibility::test_stale_snapshot_returns_evidence_insufficient_and_zero_allocations tests/test_order_commitment_evaluation.py::TestOrderCommitmentMaterialFeasibility::test_future_snapshot_returns_evidence_insufficient_and_zero_allocations tests/test_order_commitment_evaluation.py::TestOrderCommitmentMaterialFeasibility::test_missing_snapshot_or_required_item_row_is_evidence_insufficient --collect-only -q
pytest tests/test_order_commitment_evaluation.py::TestOrderCommitmentMaterialFeasibility::test_skip_requires_reason_records_pending_requirements_and_zero_allocations tests/test_order_commitment_evaluation.py::TestOrderCommitmentMaterialFeasibility::test_stale_snapshot_returns_evidence_insufficient_and_zero_allocations tests/test_order_commitment_evaluation.py::TestOrderCommitmentMaterialFeasibility::test_future_snapshot_returns_evidence_insufficient_and_zero_allocations tests/test_order_commitment_evaluation.py::TestOrderCommitmentMaterialFeasibility::test_missing_snapshot_or_required_item_row_is_evidence_insufficient -q --basetemp .tmp/pytest-mto-material-branches-red -p no:cacheprovider
~~~

Expected: exactly four items collect and fail.

- [ ] **Step 3B (freshness/skip implement): add `_material_evidence_insufficient`, the evidence header, and the three early branches shown above**

- [ ] **Step 3C (freshness/skip GREEN/commit): verify four items**

~~~powershell
pytest tests/test_order_commitment_evaluation.py::TestOrderCommitmentMaterialFeasibility::test_skip_requires_reason_records_pending_requirements_and_zero_allocations tests/test_order_commitment_evaluation.py::TestOrderCommitmentMaterialFeasibility::test_stale_snapshot_returns_evidence_insufficient_and_zero_allocations tests/test_order_commitment_evaluation.py::TestOrderCommitmentMaterialFeasibility::test_future_snapshot_returns_evidence_insufficient_and_zero_allocations tests/test_order_commitment_evaluation.py::TestOrderCommitmentMaterialFeasibility::test_missing_snapshot_or_required_item_row_is_evidence_insufficient -q --basetemp .tmp/pytest-mto-material-branches-green -p no:cacheprovider
git add -- sdbr/order_commitment_evaluation.py tests/test_order_commitment_evaluation.py
git commit -m "feat: gate MTO material evidence freshness"
~~~

Expected: exactly four items pass.

- [ ] **Step 4A (candidate-balance RED): run the seven accounting items**

~~~powershell
pytest tests/test_order_commitment_evaluation.py::TestOrderCommitmentMaterialFeasibility::test_check_defaults_on_and_uses_uncommitted_shared_availability tests/test_order_commitment_evaluation.py::TestOrderCommitmentMaterialFeasibility::test_inbound_counts_only_when_aware_and_inside_frozen_material_window tests/test_order_commitment_evaluation.py::TestOrderCommitmentMaterialFeasibility::test_shortage_is_all_or_nothing_and_returns_no_allocation_requests tests/test_order_commitment_evaluation.py::TestOrderCommitmentMaterialFeasibility::test_current_demand_allocation_is_not_subtracted_twice tests/test_order_commitment_evaluation.py::TestOrderCommitmentMaterialFeasibility::test_same_item_location_lines_use_cumulative_candidate_balance tests/test_order_commitment_evaluation.py::TestOrderCommitmentMaterialFeasibility::test_same_item_location_coverage_is_independent_of_input_line_order tests/test_order_commitment_evaluation.py::TestOrderCommitmentMaterialFeasibility::test_feasible_same_item_location_allocations_sum_to_accepted_total --collect-only -q
pytest tests/test_order_commitment_evaluation.py::TestOrderCommitmentMaterialFeasibility::test_check_defaults_on_and_uses_uncommitted_shared_availability tests/test_order_commitment_evaluation.py::TestOrderCommitmentMaterialFeasibility::test_inbound_counts_only_when_aware_and_inside_frozen_material_window tests/test_order_commitment_evaluation.py::TestOrderCommitmentMaterialFeasibility::test_shortage_is_all_or_nothing_and_returns_no_allocation_requests tests/test_order_commitment_evaluation.py::TestOrderCommitmentMaterialFeasibility::test_current_demand_allocation_is_not_subtracted_twice tests/test_order_commitment_evaluation.py::TestOrderCommitmentMaterialFeasibility::test_same_item_location_lines_use_cumulative_candidate_balance tests/test_order_commitment_evaluation.py::TestOrderCommitmentMaterialFeasibility::test_same_item_location_coverage_is_independent_of_input_line_order tests/test_order_commitment_evaluation.py::TestOrderCommitmentMaterialFeasibility::test_feasible_same_item_location_allocations_sum_to_accepted_total -q --basetemp .tmp/pytest-mto-material-balance-red -p no:cacheprovider
~~~

Expected: exactly seven items collect and fail. In particular, the pre-fix
implementation reports both `3`-unit lines covered against `5` units.

- [ ] **Step 4B (candidate-balance implement): add the exact prefilter, one-per-key supply calculation, deterministic line loop, and all-or-nothing return shown above**

- [ ] **Step 4C (candidate-balance GREEN/commit): verify seven items and shared allocation regressions**

~~~powershell
pytest tests/test_order_commitment_evaluation.py::TestOrderCommitmentMaterialFeasibility::test_check_defaults_on_and_uses_uncommitted_shared_availability tests/test_order_commitment_evaluation.py::TestOrderCommitmentMaterialFeasibility::test_inbound_counts_only_when_aware_and_inside_frozen_material_window tests/test_order_commitment_evaluation.py::TestOrderCommitmentMaterialFeasibility::test_shortage_is_all_or_nothing_and_returns_no_allocation_requests tests/test_order_commitment_evaluation.py::TestOrderCommitmentMaterialFeasibility::test_current_demand_allocation_is_not_subtracted_twice tests/test_order_commitment_evaluation.py::TestOrderCommitmentMaterialFeasibility::test_same_item_location_lines_use_cumulative_candidate_balance tests/test_order_commitment_evaluation.py::TestOrderCommitmentMaterialFeasibility::test_same_item_location_coverage_is_independent_of_input_line_order tests/test_order_commitment_evaluation.py::TestOrderCommitmentMaterialFeasibility::test_feasible_same_item_location_allocations_sum_to_accepted_total tests/test_planning_reservation_view.py -q --basetemp .tmp/pytest-mto-material-balance-green -p no:cacheprovider
git add -- sdbr/order_commitment_evaluation.py tests/test_order_commitment_evaluation.py
git commit -m "fix: consume MTO material balance cumulatively"
~~~

Expected: exactly seven focused items and the shared-allocation regressions pass.

- [ ] **Step 5A (exact-prefilter RED): run the one malformed-row item**

~~~powershell
pytest tests/test_order_commitment_evaluation.py::TestOrderCommitmentMaterialFeasibility::test_malformed_unrelated_material_allocation_is_ignored_but_matching_malformed_row_is_insufficient --collect-only -q
pytest tests/test_order_commitment_evaluation.py::TestOrderCommitmentMaterialFeasibility::test_malformed_unrelated_material_allocation_is_ignored_but_matching_malformed_row_is_insufficient -q --basetemp .tmp/pytest-mto-material-prefilter-red -p no:cacheprovider
~~~

Expected: exactly one item collects and fails before the exact prefilter is in
the public function.

- [ ] **Step 5B (exact-prefilter implement): keep the shown tolerant key filter before `planning_allocated_qty_for_other_demands`; matching malformed rows are caught and returned as `MATERIAL_EVIDENCE_INVALID`**

- [ ] **Step 5C (exact-prefilter GREEN/commit): verify one item and all twelve class items**

~~~powershell
pytest tests/test_order_commitment_evaluation.py::TestOrderCommitmentMaterialFeasibility::test_malformed_unrelated_material_allocation_is_ignored_but_matching_malformed_row_is_insufficient -q --basetemp .tmp/pytest-mto-material-prefilter-green -p no:cacheprovider
pytest tests/test_order_commitment_evaluation.py::TestOrderCommitmentMaterialFeasibility --collect-only -q
pytest tests/test_order_commitment_evaluation.py::TestOrderCommitmentMaterialFeasibility -q --basetemp .tmp/pytest-mto-material-complete -p no:cacheprovider
git add -- sdbr/order_commitment_evaluation.py tests/test_order_commitment_evaluation.py
git commit -m "feat: scope MTO material evidence exactly"
~~~

Expected: the focused item passes and exactly twelve class items collect and pass.

---

### Task 9: Total Recommendation Matrix

**Files and anchors**
- Modify `sdbr/order_commitment_evaluation.py`; add constants and `build_order_commitment_recommendation`.
- Modify `tests/test_order_commitment_evaluation.py` after material tests.

**IDs:** `BE-SDBR-010`.

**Produces**

~~~python
ACCEPTANCE_DECISIONS = frozenset({
    "AcceptRequestedDate",
    "ConditionallyAcceptRequestedDate",
    "AcceptRecommendedDate",
    "ConditionallyAcceptRecommendedDate",
})

ACCEPTANCE_ACTION_CONTEXT = {
    "AcceptRequestedDate": (
        "OnTime", "Feasible", "RequestedDateAssessment"
    ),
    "ConditionallyAcceptRequestedDate": (
        "OnTime",
        "SkippedPendingConfirmation",
        "RequestedDateAssessment",
    ),
    "AcceptRecommendedDate": (
        "LaterSafeDate", "Feasible", "EarliestSafeAssessment"
    ),
    "ConditionallyAcceptRecommendedDate": (
        "LaterSafeDate",
        "SkippedPendingConfirmation",
        "EarliestSafeAssessment",
    ),
}


def action_acknowledgement_requirements(
    *,
    action: str,
    requires_ccr_acknowledgement: bool,
    requires_material_acknowledgement: bool,
) -> dict[str, bool]:
    is_acceptance = action in ACCEPTANCE_DECISIONS
    return {
        "RequiresCcrAcknowledgement": (
            is_acceptance and requires_ccr_acknowledgement
        ),
        "RequiresMaterialAcknowledgement": (
            is_acceptance and requires_material_acknowledgement
        ),
    }

def build_order_commitment_recommendation(
    *,
    shadow_schedule: Mapping[str, object],
    material_assessment: Mapping[str, object],
    protection_policy: CcrProtectionPolicy,
) -> dict[str, object]:
~~~

- [ ] **Step 1: Write a parameterized exhaustive matrix**

Add `TestOrderCommitmentRecommendationMatrix` with a 27-row parameter table covering 3 capacity states × 4 material states where applicable × all 3 threshold states. Name explicit focused methods:

- `test_later_safe_skipped_material_allows_conditional_recommended_date`;
- `test_later_safe_reference_fallback_requires_ccr_acknowledgement`;
- `test_later_safe_approved_threshold_exceeded_requires_ccr_acknowledgement`;
- `test_later_safe_insufficient_material_has_no_acceptance_action`;
- `test_every_reference_fallback_sets_ccr_acknowledgement`;
- `test_every_skipped_material_row_sets_material_acknowledgement`.

The parameterized test asserts recommendation code, exact ordered actions, and both acknowledgement booleans for every table row.

~~~powershell
pytest tests/test_order_commitment_evaluation.py::TestOrderCommitmentRecommendationMatrix -q --basetemp .tmp/pytest-mto-matrix-red -p no:cacheprovider
~~~

Expected: failures because the matrix function and fourth acceptance action are absent.

- [ ] **Step 2: Implement the total branch table**

~~~python
capacity = shadow_schedule["Status"]
material = material_assessment["Status"]
selected = shadow_schedule.get("SelectedAssessment") or {}
threshold_state = (
    "ReferenceFallback"
    if protection_policy.source == "ReferenceFallback"
    else "ApprovedExceeded"
    if bool(selected.get("ThresholdExceeded"))
    else "ApprovedWithin"
)
requires_ccr = threshold_state in {
    "ReferenceFallback", "ApprovedExceeded"
}
requires_material = material == "SkippedPendingConfirmation"

if capacity == "NotAssessable":
    decision, actions = "DoNotRecommendAccept", ["Reevaluate", "Reject"]
elif material == "EvidenceInsufficient":
    decision, actions = "MaterialEvidenceRequired", ["Reevaluate", "Reject"]
elif material == "Shortage":
    decision, actions = "DoNotRecommendAccept", ["Reevaluate", "Reject"]
elif capacity == "OnTime" and material == "Feasible":
    decision = (
        "RecommendAccept"
        if threshold_state == "ApprovedWithin"
        else "PlannerConfirmationRequired"
    )
    actions = ["AcceptRequestedDate", "Reevaluate", "Reject"]
elif capacity == "OnTime" and material == "SkippedPendingConfirmation":
    decision = (
        "CapacityAcceptableMaterialPending"
        if threshold_state == "ApprovedWithin"
        else "PlannerConfirmationRequired"
    )
    actions = [
        "ConditionallyAcceptRequestedDate", "Reevaluate", "Reject"
    ]
elif capacity == "LaterSafeDate" and material == "Feasible":
    decision = (
        "RecommendLaterPromise"
        if threshold_state == "ApprovedWithin"
        else "PlannerConfirmationRequired"
    )
    actions = ["AcceptRecommendedDate", "Reevaluate", "Reject"]
elif (
    capacity == "LaterSafeDate"
    and material == "SkippedPendingConfirmation"
):
    decision = (
        "RecommendLaterPromise"
        if threshold_state == "ApprovedWithin"
        else "PlannerConfirmationRequired"
    )
    actions = [
        "ConditionallyAcceptRecommendedDate", "Reevaluate", "Reject"
    ]
else:
    raise OrderCommitmentConflict(
        f"Unsupported recommendation state: {capacity}/{material}."
    )
return {
    "Decision": decision,
    "AllowedActions": actions,
    "ThresholdState": threshold_state,
    "RequiresPlannerDecision": True,
    "RequiresCcrAcknowledgement": requires_ccr,
    "RequiresMaterialAcknowledgement": requires_material,
    "ActionAcknowledgementRequirements": {
        action: action_acknowledgement_requirements(
            action=action,
            requires_ccr_acknowledgement=requires_ccr,
            requires_material_acknowledgement=requires_material,
        )
        for action in actions
    },
}
~~~

- [ ] **Step 3: Verify and commit**

~~~powershell
pytest tests/test_order_commitment_evaluation.py::TestOrderCommitmentRecommendationMatrix --collect-only -q
pytest tests/test_order_commitment_evaluation.py::TestOrderCommitmentRecommendationMatrix -q --basetemp .tmp/pytest-mto-matrix-green -p no:cacheprovider
git add -- sdbr/order_commitment_evaluation.py tests/test_order_commitment_evaluation.py
git commit -m "feat: complete MTO recommendation matrix"
~~~

Expected: all matrix cases and six named edge tests pass.

---

### Task 10: Relevant-State Basis, Evaluation Identity, and Supersession

**Files and anchors**
- Modify `sdbr/order_commitment_evaluation.py`; add basis/evaluation/registration functions.
- Modify `tests/test_order_commitment_evaluation.py` after matrix tests.

**IDs:** `BE-SDBR-006`, `BE-SDBR-010`.

**Produces**

~~~python
def build_order_commitment_basis(
    *,
    baseline_planning_run_id: str,
    baseline_operational_state_snapshot_id: str | None,
    baseline_schedule_fingerprint: str,
    master_data_version_id: str,
    operating_model_configuration_id: str | None,
    operating_model_fingerprint: str | None,
    scheduling_configuration_id: str | None,
    ddmrp_configuration_id: str | None,
    release_policy_version_id: str | None,
    frozen_release_policy_fingerprint: str,
    routing_fingerprint: str,
    calendar_fingerprint: str,
    time_buffer_minutes: int,
    material_check_window_minutes: int,
    capacity_assessment_cutoff_at: datetime,
    material_eligibility_cutoff_at: datetime | None,
    check_material_availability: bool,
    material_skip_reason: str | None,
    snapshot_selection: Mapping[str, object],
    relevant_capacity_window_keys: list[tuple[str, str, str]],
    capacity_ledger_rows: list[dict[str, object]],
    relevant_material_keys: list[tuple[str, str]],
    inventory_buffer_rows: list[InventoryBufferPolicy],
    material_availability_rows: list[MaterialAvailability],
    material_ledger_rows: list[dict[str, object]],
) -> dict[str, object]:

def create_order_commitment_evaluation(
    *,
    order: Mapping[str, object],
    shadow_schedule: Mapping[str, object],
    material_assessment: Mapping[str, object],
    basis: Mapping[str, object],
    protection_policy: CcrProtectionPolicy,
    evaluated_at: datetime,
) -> dict[str, object]:

def register_order_commitment_evaluation(
    evaluations: Mapping[str, dict[str, object]],
    candidate: dict[str, object],
) -> tuple[Literal["Created", "Duplicate"], dict[str, object]]:

def supersede_open_order_commitment_evaluations(
    *,
    evaluations: Mapping[str, dict[str, object]],
    candidate: dict[str, object],
    superseded_at: datetime,
) -> dict[str, dict[str, object]]:
~~~

Before either basis/evaluation function, install the canonical decision-fact
symbols from the global contract in `order_commitment_evaluation.py`; the
global section is a contract, while this is the production installation:

~~~python
CAPACITY_DECISION_WINDOW_FIELDS = (
    "RouteSequence", "OperationID", "ResourceID", "WindowStartAt",
    "WindowEndAt", "UsableWindowStartAt", "UsableWindowEndAt",
    "LatestAllowedCompletionAt", "CapacityMinutes",
    "UsableTemporalCapacityMinutes", "ScheduledLoadMinutes",
    "ScheduledLoadBeforeDeadlineMinutes", "ExistingReservationMinutes",
    "CandidateLoadMinutes", "LoadBeforeMinutes", "LoadAfterMinutes",
    "LoadAfterPercent", "AggregateRemainingMinutes",
    "TemporalRemainingMinutes", "LoadStatus", "ThresholdExceeded",
)
CAPACITY_DECISION_REQUEST_FIELDS = (
    "ReservationLineID", "OrderID", "OperationID", "ResourceID",
    "WindowStartAt", "WindowEndAt", "ReservedMinutes",
    "LatestAllowedCompletionAt",
)
MATERIAL_DECISION_REQUEST_FIELDS = (
    "RequirementLineID", "ItemID", "LocationID", "Uom",
    "AllocatedQty", "SupplySourceType", "MaterialSnapshotID",
)


def canonical_order_commitment_decision_facts(
    evaluation: Mapping[str, object],
) -> dict[str, object]:
    shadow = dict(evaluation["ShadowSchedule"])
    material = dict(evaluation["MaterialAssessment"])
    recommendation = dict(evaluation["Recommendation"])
    candidate_key = {
        "OnTime": "RequestedDateAssessment",
        "LaterSafeDate": "EarliestSafeAssessment",
    }.get(str(shadow["Status"]))
    candidate = (
        dict(shadow[candidate_key])
        if candidate_key is not None
        and isinstance(shadow.get(candidate_key), Mapping)
        else {}
    )
    actions = list(recommendation["AllowedActions"])
    return {
        "CapacityStatus": shadow["Status"],
        "SelectedCandidateKey": candidate_key,
        "SelectedPromiseAt": candidate.get("PromiseAt"),
        "CapacityWindowAssessments": sorted(
            [
                {
                    field: row.get(field)
                    for field in CAPACITY_DECISION_WINDOW_FIELDS
                }
                for row in candidate.get("WindowAssessments", [])
            ],
            key=lambda row: (
                int(row["RouteSequence"]),
                str(row["OperationID"]),
                str(row["WindowStartAt"]),
            ),
        ),
        "CapacityReservationRequests": sorted(
            [
                {
                    field: row.get(field)
                    for field in CAPACITY_DECISION_REQUEST_FIELDS
                }
                for row in candidate.get("ReservationRequests", [])
            ],
            key=lambda row: str(row["ReservationLineID"]),
        ),
        "MaterialStatus": material["Status"],
        "MaterialAllocationRequests": sorted(
            [
                {
                    field: row.get(field)
                    for field in MATERIAL_DECISION_REQUEST_FIELDS
                }
                for row in material.get("AllocationRequests", [])
            ],
            key=lambda row: str(row["RequirementLineID"]),
        ),
        "Recommendation": recommendation["Decision"],
        "ThresholdState": recommendation["ThresholdState"],
        "AllowedActions": actions,
        "ActionAcknowledgementRequirements": {
            action: action_acknowledgement_requirements(
                action=action,
                requires_ccr_acknowledgement=bool(
                    recommendation["RequiresCcrAcknowledgement"]
                ),
                requires_material_acknowledgement=bool(
                    recommendation["RequiresMaterialAcknowledgement"]
                ),
            )
            for action in actions
        },
    }
~~~

- [ ] **Step 1: Write identity/relevant-state tests**

Add `TestOrderCommitmentEvaluationIdentity`:

- `test_exact_replay_returns_existing_evaluation`;
- `test_protection_policy_change_creates_new_evaluation`;
- `test_each_frozen_configuration_reference_changes_identity`;
- `test_shadow_algorithm_capacity_semantics_changes_identity`;
- `test_relevant_capacity_change_in_exact_assessed_window_changes_basis`;
- `test_unrelated_capacity_resource_or_window_does_not_change_basis`;
- `test_relevant_material_item_location_change_changes_basis`;
- `test_unrelated_material_item_location_does_not_change_basis`;
- `test_fresh_age_observation_change_keeps_identity_but_fresh_to_stale_changes_it`;
- `test_capacity_cutoff_change_creates_deterministic_new_identity_not_content_conflict`;
- `test_material_cutoff_crossing_inbound_creates_deterministic_new_identity`;
- `test_skipped_material_decision_basis_excludes_snapshot_and_material_rows`;
- `test_malformed_unrelated_rows_are_ignored_after_exact_prefilter`;
- `test_only_open_same_logical_order_is_superseded`;
- `test_accepted_or_rejected_evidence_cannot_be_superseded`.

~~~powershell
pytest tests/test_order_commitment_evaluation.py::TestOrderCommitmentEvaluationIdentity -q --basetemp .tmp/pytest-mto-identity-red -p no:cacheprovider
~~~

Expected: the named tests fail because basis and registration functions are absent.

- [ ] **Step 2: Build only exact relevant projections**

Install the complete projection prelude and function body. Tolerant raw-key
comparison happens before strict parsing, so malformed unrelated rows are
ignored while malformed matching rows fail closed.

~~~python
CAPACITY_BASIS_FIELDS = (
    "CapacityReservationID", "ReservationBatchID", "DemandCommitmentID",
    "DemandClass", "ResourceID", "WindowStartAt", "WindowEndAt",
    "ReservedMinutes", "LatestAllowedCompletionAt", "Status",
    "RecordVersion",
)
MATERIAL_BASIS_FIELDS = (
    "MaterialAllocationID", "ReservationBatchID", "DemandCommitmentID",
    "DemandClass", "ItemID", "LocationID", "AllocatedQty",
    "MaterialSnapshotID", "Status", "RecordVersion",
)


def _basis_nonnegative(value: object, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise OrderCommitmentConflict(f"{field} must be finite and non-negative.")
    normalized = float(value)
    if not isfinite(normalized) or normalized < 0:
        raise OrderCommitmentConflict(f"{field} must be finite and non-negative.")
    return normalized


def _basis_record_version(value: object, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise OrderCommitmentConflict(f"{field} must be a positive integer.")
    return value


def build_order_commitment_basis(
    *,
    baseline_planning_run_id: str,
    baseline_operational_state_snapshot_id: str | None,
    baseline_schedule_fingerprint: str,
    master_data_version_id: str,
    operating_model_configuration_id: str | None,
    operating_model_fingerprint: str | None,
    scheduling_configuration_id: str | None,
    ddmrp_configuration_id: str | None,
    release_policy_version_id: str | None,
    frozen_release_policy_fingerprint: str,
    routing_fingerprint: str,
    calendar_fingerprint: str,
    time_buffer_minutes: int,
    material_check_window_minutes: int,
    capacity_assessment_cutoff_at: datetime,
    material_eligibility_cutoff_at: datetime | None,
    check_material_availability: bool,
    material_skip_reason: str | None,
    snapshot_selection: Mapping[str, object],
    relevant_capacity_window_keys: list[tuple[str, str, str]],
    capacity_ledger_rows: list[dict[str, object]],
    relevant_material_keys: list[tuple[str, str]],
    inventory_buffer_rows: list[InventoryBufferPolicy],
    material_availability_rows: list[MaterialAvailability],
    material_ledger_rows: list[dict[str, object]],
) -> dict[str, object]:
    selection = snapshot_selection
    capacity_keys = sorted({
        (
            str(resource_id),
            _parse_aware(start).isoformat(),
            _parse_aware(end).isoformat(),
        )
        for resource_id, start, end in relevant_capacity_window_keys
    })
    material_keys = sorted({
        (str(item_id), str(location_id))
        for item_id, location_id in relevant_material_keys
    })
    capacity_key_set = set(capacity_keys)
    material_key_set = set(material_keys)

    capacity_projection: list[dict[str, object]] = []
    seen_capacity_ids: set[str] = set()
    for raw in capacity_ledger_rows:
        if raw.get("Status") not in ACTIVE_PLANNING_STATUSES:
            continue
        raw_key = (
            str(raw.get("ResourceID") or ""),
            str(raw.get("WindowStartAt") or ""),
            str(raw.get("WindowEndAt") or ""),
        )
        if raw_key not in capacity_key_set:
            continue
        capacity_id = _required_text(raw, "CapacityReservationID")
        if capacity_id in seen_capacity_ids:
            raise OrderCommitmentConflict(
                "Relevant capacity reservation ID is duplicated."
            )
        start = _parse_aware(raw["WindowStartAt"])
        end = _parse_aware(raw["WindowEndAt"])
        latest = _parse_aware(raw["LatestAllowedCompletionAt"])
        if end <= start or not start < latest <= end:
            raise OrderCommitmentConflict(
                "Relevant capacity reservation window is invalid."
            )
        projected = {
            field: deepcopy(raw.get(field))
            for field in CAPACITY_BASIS_FIELDS
        }
        projected.update({
            "CapacityReservationID": capacity_id,
            "ReservationBatchID": _required_text(raw, "ReservationBatchID"),
            "DemandCommitmentID": _required_text(raw, "DemandCommitmentID"),
            "DemandClass": _required_text(raw, "DemandClass"),
            "ResourceID": raw_key[0],
            "WindowStartAt": start.isoformat(),
            "WindowEndAt": end.isoformat(),
            "ReservedMinutes": _positive_number(
                raw.get("ReservedMinutes"), "ReservedMinutes"
            ),
            "LatestAllowedCompletionAt": latest.isoformat(),
            "Status": _required_text(raw, "Status"),
            "RecordVersion": _basis_record_version(
                raw.get("RecordVersion"), "Capacity RecordVersion"
            ),
        })
        seen_capacity_ids.add(capacity_id)
        capacity_projection.append(projected)
    capacity_projection.sort(
        key=lambda row: str(row["CapacityReservationID"])
    )

    inventory_projection: list[dict[str, object]] = []
    seen_inventory_keys: set[tuple[str, str]] = set()
    for row in inventory_buffer_rows:
        key = (row.item_id, row.location_id)
        if key not in material_key_set:
            continue
        if key in seen_inventory_keys:
            raise OrderCommitmentConflict(
                "Relevant inventory-buffer evidence is duplicated."
            )
        seen_inventory_keys.add(key)
        inventory_projection.append({
            "ItemID": row.item_id,
            "LocationID": row.location_id,
            "OnHandQty": _basis_nonnegative(row.on_hand_qty, "OnHandQty"),
            "RedZoneQty": _basis_nonnegative(row.red_zone_qty, "RedZoneQty"),
            "YellowZoneQty": _basis_nonnegative(
                row.yellow_zone_qty, "YellowZoneQty"
            ),
            "GreenZoneQty": _basis_nonnegative(
                row.green_zone_qty, "GreenZoneQty"
            ),
        })
    inventory_projection.sort(
        key=lambda row: (str(row["ItemID"]), str(row["LocationID"]))
    )

    availability_projection: list[dict[str, object]] = []
    seen_availability_keys: set[tuple[str, str]] = set()
    for row in material_availability_rows:
        key = (row.item_id, row.location_id)
        if key not in material_key_set:
            continue
        if key in seen_availability_keys:
            raise OrderCommitmentConflict(
                "Relevant material-availability evidence is duplicated."
            )
        seen_availability_keys.add(key)
        availability_projection.append({
            "ItemID": row.item_id,
            "LocationID": row.location_id,
            "AllocatedQty": _basis_nonnegative(
                row.allocated_qty, "Authority AllocatedQty"
            ),
            "InboundQty": _basis_nonnegative(row.inbound_qty, "InboundQty"),
            "InboundAvailableAt": (
                _utc(row.inbound_available_at).isoformat()
                if row.inbound_available_at is not None
                else None
            ),
        })
    availability_projection.sort(
        key=lambda row: (str(row["ItemID"]), str(row["LocationID"]))
    )

    material_projection: list[dict[str, object]] = []
    seen_material_ids: set[str] = set()
    for raw in material_ledger_rows:
        if raw.get("Status") not in ACTIVE_PLANNING_STATUSES:
            continue
        raw_key = (
            str(raw.get("ItemID") or ""),
            str(raw.get("LocationID") or ""),
        )
        if raw_key not in material_key_set:
            continue
        allocation_id = _required_text(raw, "MaterialAllocationID")
        if allocation_id in seen_material_ids:
            raise OrderCommitmentConflict(
                "Relevant material allocation ID is duplicated."
            )
        projected = {
            field: deepcopy(raw.get(field))
            for field in MATERIAL_BASIS_FIELDS
        }
        projected.update({
            "MaterialAllocationID": allocation_id,
            "ReservationBatchID": _required_text(raw, "ReservationBatchID"),
            "DemandCommitmentID": _required_text(raw, "DemandCommitmentID"),
            "DemandClass": _required_text(raw, "DemandClass"),
            "ItemID": raw_key[0],
            "LocationID": raw_key[1],
            "AllocatedQty": _basis_nonnegative(
                raw.get("AllocatedQty"), "AllocatedQty"
            ),
            "MaterialSnapshotID": _required_text(
                raw, "MaterialSnapshotID"
            ),
            "Status": _required_text(raw, "Status"),
            "RecordVersion": _basis_record_version(
                raw.get("RecordVersion"), "Material RecordVersion"
            ),
        })
        seen_material_ids.add(allocation_id)
        material_projection.append(projected)
    material_projection.sort(
        key=lambda row: str(row["MaterialAllocationID"])
    )
~~~

Continue inside the same `build_order_commitment_basis` function with this
indented tail:

~~~python
    audit_basis = {
        "BaselinePlanningRunID": baseline_planning_run_id,
        "BaselineOperationalStateSnapshotID": (
            baseline_operational_state_snapshot_id
        ),
        "BaselineScheduleFingerprint": baseline_schedule_fingerprint,
        "MasterDataVersionID": master_data_version_id,
        "OperatingModelConfigurationID": operating_model_configuration_id,
        "OperatingModelFingerprint": operating_model_fingerprint,
        "SchedulingConfigurationID": scheduling_configuration_id,
        "DDMRPConfigurationID": ddmrp_configuration_id,
        "ReleasePolicyVersionID": release_policy_version_id,
        "FrozenReleasePolicyFingerprint": frozen_release_policy_fingerprint,
        "RoutingFingerprint": routing_fingerprint,
        "CalendarFingerprint": calendar_fingerprint,
        "TimeBufferMinutes": time_buffer_minutes,
        "MaterialCheckWindowMinutes": material_check_window_minutes,
        "CapacityAssessmentCutoffAt": _utc_iso(
            capacity_assessment_cutoff_at
        ),
        "MaterialEligibilityCutoffAt": (
            _utc_iso(material_eligibility_cutoff_at)
            if material_eligibility_cutoff_at is not None
            else None
        ),
        "SelectedOperationalStateSnapshotID": selection[
            "OperationalStateSnapshotID"
        ],
        "SelectedOperationalStateCapturedAt": selection[
            "OperationalStateCapturedAt"
        ],
        "OperationalStateFreshnessStatus": selection[
            "OperationalStateFreshnessStatus"
        ],
        "OperationalStateAgeMinutes": selection[
            "OperationalStateAgeMinutes"
        ],
        "OperationalStateMaxAgeMinutes": 60,
        "OperationalStateValidThroughAt": selection[
            "OperationalStateValidThroughAt"
        ],
        "RelevantCapacityWindowKeys": capacity_keys,
        "RelevantCapacityLedger": capacity_projection,
        "RelevantMaterialKeys": material_keys,
        "RelevantInventoryBuffers": inventory_projection,
        "RelevantMaterialAvailability": availability_projection,
        "RelevantMaterialLedger": material_projection,
    }
    audit_fingerprint_projection = deepcopy(audit_basis)
    audit_fingerprint_projection.pop("OperationalStateAgeMinutes", None)
    capacity_decision_basis = {
        key: deepcopy(audit_basis[key])
        for key in (
            "BaselinePlanningRunID",
            "BaselineScheduleFingerprint",
            "MasterDataVersionID",
            "OperatingModelConfigurationID",
            "OperatingModelFingerprint",
            "SchedulingConfigurationID",
            "DDMRPConfigurationID",
            "ReleasePolicyVersionID",
            "FrozenReleasePolicyFingerprint",
            "RoutingFingerprint",
            "CalendarFingerprint",
            "TimeBufferMinutes",
            "RelevantCapacityWindowKeys",
            "RelevantCapacityLedger",
        )
    }
    decision_staleness_basis = {
        **capacity_decision_basis,
        "MaterialPolicy": {
            "CheckEnabled": bool(check_material_availability),
            "SkipReason": material_skip_reason,
            "MaterialCheckWindowMinutes": material_check_window_minutes,
        },
    }
    if check_material_availability:
        decision_staleness_basis.update(
            {
                "SelectedOperationalStateSnapshotID": audit_basis[
                    "SelectedOperationalStateSnapshotID"
                ],
                "SelectedOperationalStateCapturedAt": audit_basis[
                    "SelectedOperationalStateCapturedAt"
                ],
                "OperationalStateFreshnessStatus": audit_basis[
                    "OperationalStateFreshnessStatus"
                ],
                "OperationalStateValidThroughAt": audit_basis[
                    "OperationalStateValidThroughAt"
                ],
                "RelevantMaterialKeys": material_keys,
                "RelevantInventoryBuffers": inventory_projection,
                "RelevantMaterialAvailability": availability_projection,
                "RelevantMaterialLedger": material_projection,
            }
        )
    return {
        **audit_basis,
        "AuditBasisFingerprint": canonical_fingerprint(
            audit_fingerprint_projection
        ),
        "DecisionStalenessBasis": decision_staleness_basis,
        "DecisionStalenessBasisFingerprint": canonical_fingerprint(
            decision_staleness_basis
        ),
    }
~~~

- [ ] **Step 3: Build complete evaluation identity**

~~~python
def create_order_commitment_evaluation(
    *,
    order: Mapping[str, object],
    shadow_schedule: Mapping[str, object],
    material_assessment: Mapping[str, object],
    basis: Mapping[str, object],
    protection_policy: CcrProtectionPolicy,
    evaluated_at: datetime,
) -> dict[str, object]:
    evaluated_at = _utc(require_aware(evaluated_at, "evaluated_at"))
    policy = normalized_policy_dict(protection_policy)
    identity = {
        "OrderContentFingerprint": order["OrderContentFingerprint"],
        "AuditBasisFingerprint": basis["AuditBasisFingerprint"],
        "DecisionStalenessBasisFingerprint": basis[
            "DecisionStalenessBasisFingerprint"
        ],
        "CapacityAssessmentCutoffAt": basis[
            "CapacityAssessmentCutoffAt"
        ],
        "MaterialEligibilityCutoffAt": basis[
            "MaterialEligibilityCutoffAt"
        ],
        "MaterialPolicy": {
            "CheckEnabled": material_assessment["CheckEnabled"],
            "SkipReason": material_assessment.get("SkipReason"),
            "MaterialCheckWindowMinutes": material_assessment[
                "MaterialCheckWindowMinutes"
            ],
            "SnapshotSelectionMode": material_assessment[
                "SnapshotSelectionMode"
            ],
            "RequestedOperationalStateSnapshotID": material_assessment.get(
                "RequestedOperationalStateSnapshotID"
            ),
        },
        "ProtectionPolicy": policy,
        "ShadowAlgorithm": deepcopy(shadow_schedule["Algorithm"]),
    }
    evaluation_id = (
        "OCE-"
        + sha256(canonical_json(identity).encode("utf-8")).hexdigest()[:20]
    )
    immutable = {
        "EvaluationID": evaluation_id,
        "Order": deepcopy(order),
        "LogicalOrderKey": order["LogicalOrderKey"],
        "OrderContentFingerprint": order["OrderContentFingerprint"],
        "Basis": deepcopy(basis),
        "AuditBasisFingerprint": basis["AuditBasisFingerprint"],
        "DecisionStalenessBasisFingerprint": basis[
            "DecisionStalenessBasisFingerprint"
        ],
        "ProtectionPolicy": policy,
        "ShadowSchedule": deepcopy(shadow_schedule),
        "MaterialAssessment": deepcopy(material_assessment),
        "Recommendation": build_order_commitment_recommendation(
            shadow_schedule=shadow_schedule,
            material_assessment=material_assessment,
            protection_policy=protection_policy,
        ),
    }
    immutable["DecisionFacts"] = canonical_order_commitment_decision_facts(
        immutable
    )
    immutable["DecisionFactsFingerprint"] = canonical_fingerprint(
        immutable["DecisionFacts"]
    )
    fingerprint_projection = deepcopy(immutable)
    fingerprint_projection["Basis"].pop(
        "OperationalStateAgeMinutes", None
    )
    fingerprint_projection["MaterialAssessment"].pop(
        "OperationalStateAgeMinutes", None
    )
    evaluation_fingerprint = canonical_fingerprint(fingerprint_projection)
    return {
        **immutable,
        "EvaluationFingerprint": evaluation_fingerprint,
        "EvaluatedAt": _utc_iso(evaluated_at),
        "CreatedAt": _utc_iso(evaluated_at),
        "Status": "AwaitingPlannerDecision",
        "RecordVersion": 1,
    }


def register_order_commitment_evaluation(
    evaluations: Mapping[str, dict[str, object]],
    candidate: dict[str, object],
) -> tuple[Literal["Created", "Duplicate"], dict[str, object]]:
    evaluation_id = _required_text(candidate, "EvaluationID")
    fingerprint = _required_text(candidate, "EvaluationFingerprint")
    existing = evaluations.get(evaluation_id)
    if existing is None:
        return "Created", deepcopy(candidate)
    if existing.get("EvaluationFingerprint") == fingerprint:
        return "Duplicate", deepcopy(existing)
    raise OrderCommitmentConflict(
        "Evaluation ID already exists with different canonical content."
    )
~~~

Registration now has a complete body and returns the persisted deep copy only
when ID and evaluation fingerprint match; otherwise same-ID content raises
conflict. Supersession updates only `AwaitingPlannerDecision` rows with the
same logical key; accepted/rejected conflicts are explicit.

Use these complete intake helpers; they make terminal behavior and version ordering explicit before the API mutates anything:

~~~python
def exact_order_commitment_intake_replay(
    *,
    evaluations: Mapping[str, dict[str, object]],
    order: Mapping[str, object],
) -> dict[str, object] | None:
    logical_rows = [
        row for row in evaluations.values()
        if row.get("LogicalOrderKey") == order["LogicalOrderKey"]
    ]
    exact = next(
        (
            row for row in logical_rows
            if row.get("OrderContentFingerprint")
            == order["OrderContentFingerprint"]
        ),
        None,
    )
    if exact is not None:
        return deepcopy(exact)
    if any(row.get("Order", {}).get("OrderKey") == order["OrderKey"] for row in logical_rows):
        raise OrderCommitmentConflict("OrderVersionContentConflict")
    if any(row.get("Status") == "AcceptedPendingFormalSchedule" for row in logical_rows):
        raise OrderCommitmentConflict(
            "AcceptedOrderVersionChangeRequiresExplicitAmendment"
        )
    if logical_rows:
        greatest_rank = max(
            tuple(row["Order"]["OrderVersionRank"])
            for row in logical_rows
        )
        if tuple(order["OrderVersionRank"]) < greatest_rank:
            raise OrderCommitmentConflict("OrderVersionSuperseded")
    return None


def supersede_open_order_commitment_evaluations(
    *,
    evaluations: Mapping[str, dict[str, object]],
    candidate: Mapping[str, object],
    superseded_at: datetime,
) -> dict[str, dict[str, object]]:
    updates: dict[str, dict[str, object]] = {}
    for evaluation_id, row in evaluations.items():
        if (
            row.get("LogicalOrderKey") != candidate["LogicalOrderKey"]
            or row.get("Status") != "AwaitingPlannerDecision"
            or evaluation_id == candidate["EvaluationID"]
        ):
            continue
        updated = deepcopy(row)
        updated["Status"] = "Superseded"
        updated["SupersededAt"] = _utc_iso(superseded_at)
        updated["SupersededByEvaluationID"] = candidate["EvaluationID"]
        updated["RecordVersion"] = int(row["RecordVersion"]) + 1
        updates[evaluation_id] = updated
    return updates
~~~

- [ ] **Step 4A (exact projections RED): run the six projection/relevance items**

~~~powershell
pytest tests/test_order_commitment_evaluation.py::TestOrderCommitmentEvaluationIdentity::test_relevant_capacity_change_in_exact_assessed_window_changes_basis tests/test_order_commitment_evaluation.py::TestOrderCommitmentEvaluationIdentity::test_unrelated_capacity_resource_or_window_does_not_change_basis tests/test_order_commitment_evaluation.py::TestOrderCommitmentEvaluationIdentity::test_relevant_material_item_location_change_changes_basis tests/test_order_commitment_evaluation.py::TestOrderCommitmentEvaluationIdentity::test_unrelated_material_item_location_does_not_change_basis tests/test_order_commitment_evaluation.py::TestOrderCommitmentEvaluationIdentity::test_skipped_material_decision_basis_excludes_snapshot_and_material_rows tests/test_order_commitment_evaluation.py::TestOrderCommitmentEvaluationIdentity::test_malformed_unrelated_rows_are_ignored_after_exact_prefilter --collect-only -q
pytest tests/test_order_commitment_evaluation.py::TestOrderCommitmentEvaluationIdentity::test_relevant_capacity_change_in_exact_assessed_window_changes_basis tests/test_order_commitment_evaluation.py::TestOrderCommitmentEvaluationIdentity::test_unrelated_capacity_resource_or_window_does_not_change_basis tests/test_order_commitment_evaluation.py::TestOrderCommitmentEvaluationIdentity::test_relevant_material_item_location_change_changes_basis tests/test_order_commitment_evaluation.py::TestOrderCommitmentEvaluationIdentity::test_unrelated_material_item_location_does_not_change_basis tests/test_order_commitment_evaluation.py::TestOrderCommitmentEvaluationIdentity::test_skipped_material_decision_basis_excludes_snapshot_and_material_rows tests/test_order_commitment_evaluation.py::TestOrderCommitmentEvaluationIdentity::test_malformed_unrelated_rows_are_ignored_after_exact_prefilter -q --basetemp .tmp/pytest-mto-basis-red -p no:cacheprovider
~~~

Expected: exactly six items collect and fail.

- [ ] **Step 4B (exact projections implement): install the complete `build_order_commitment_basis` projection prelude and tail above**

- [ ] **Step 4C (exact projections GREEN/commit): verify six items**

~~~powershell
pytest tests/test_order_commitment_evaluation.py::TestOrderCommitmentEvaluationIdentity::test_relevant_capacity_change_in_exact_assessed_window_changes_basis tests/test_order_commitment_evaluation.py::TestOrderCommitmentEvaluationIdentity::test_unrelated_capacity_resource_or_window_does_not_change_basis tests/test_order_commitment_evaluation.py::TestOrderCommitmentEvaluationIdentity::test_relevant_material_item_location_change_changes_basis tests/test_order_commitment_evaluation.py::TestOrderCommitmentEvaluationIdentity::test_unrelated_material_item_location_does_not_change_basis tests/test_order_commitment_evaluation.py::TestOrderCommitmentEvaluationIdentity::test_skipped_material_decision_basis_excludes_snapshot_and_material_rows tests/test_order_commitment_evaluation.py::TestOrderCommitmentEvaluationIdentity::test_malformed_unrelated_rows_are_ignored_after_exact_prefilter -q --basetemp .tmp/pytest-mto-basis-green -p no:cacheprovider
git add -- sdbr/order_commitment_evaluation.py tests/test_order_commitment_evaluation.py
git commit -m "feat: freeze exact MTO decision evidence"
~~~

Expected: exactly six items pass.

- [ ] **Step 5A (identity/registration RED): run the seven identity items**

~~~powershell
pytest tests/test_order_commitment_evaluation.py::TestOrderCommitmentEvaluationIdentity::test_exact_replay_returns_existing_evaluation tests/test_order_commitment_evaluation.py::TestOrderCommitmentEvaluationIdentity::test_protection_policy_change_creates_new_evaluation tests/test_order_commitment_evaluation.py::TestOrderCommitmentEvaluationIdentity::test_each_frozen_configuration_reference_changes_identity tests/test_order_commitment_evaluation.py::TestOrderCommitmentEvaluationIdentity::test_shadow_algorithm_capacity_semantics_changes_identity tests/test_order_commitment_evaluation.py::TestOrderCommitmentEvaluationIdentity::test_fresh_age_observation_change_keeps_identity_but_fresh_to_stale_changes_it tests/test_order_commitment_evaluation.py::TestOrderCommitmentEvaluationIdentity::test_capacity_cutoff_change_creates_deterministic_new_identity_not_content_conflict tests/test_order_commitment_evaluation.py::TestOrderCommitmentEvaluationIdentity::test_material_cutoff_crossing_inbound_creates_deterministic_new_identity --collect-only -q
pytest tests/test_order_commitment_evaluation.py::TestOrderCommitmentEvaluationIdentity::test_exact_replay_returns_existing_evaluation tests/test_order_commitment_evaluation.py::TestOrderCommitmentEvaluationIdentity::test_protection_policy_change_creates_new_evaluation tests/test_order_commitment_evaluation.py::TestOrderCommitmentEvaluationIdentity::test_each_frozen_configuration_reference_changes_identity tests/test_order_commitment_evaluation.py::TestOrderCommitmentEvaluationIdentity::test_shadow_algorithm_capacity_semantics_changes_identity tests/test_order_commitment_evaluation.py::TestOrderCommitmentEvaluationIdentity::test_fresh_age_observation_change_keeps_identity_but_fresh_to_stale_changes_it tests/test_order_commitment_evaluation.py::TestOrderCommitmentEvaluationIdentity::test_capacity_cutoff_change_creates_deterministic_new_identity_not_content_conflict tests/test_order_commitment_evaluation.py::TestOrderCommitmentEvaluationIdentity::test_material_cutoff_crossing_inbound_creates_deterministic_new_identity -q --basetemp .tmp/pytest-mto-identity-red -p no:cacheprovider
~~~

Expected: exactly seven items collect and fail.

- [ ] **Step 5B (identity/registration implement): install the decision-fact constants/function, complete evaluation builder, and complete registration function above**

- [ ] **Step 5C (identity/registration GREEN/commit): verify seven items**

~~~powershell
pytest tests/test_order_commitment_evaluation.py::TestOrderCommitmentEvaluationIdentity::test_exact_replay_returns_existing_evaluation tests/test_order_commitment_evaluation.py::TestOrderCommitmentEvaluationIdentity::test_protection_policy_change_creates_new_evaluation tests/test_order_commitment_evaluation.py::TestOrderCommitmentEvaluationIdentity::test_each_frozen_configuration_reference_changes_identity tests/test_order_commitment_evaluation.py::TestOrderCommitmentEvaluationIdentity::test_shadow_algorithm_capacity_semantics_changes_identity tests/test_order_commitment_evaluation.py::TestOrderCommitmentEvaluationIdentity::test_fresh_age_observation_change_keeps_identity_but_fresh_to_stale_changes_it tests/test_order_commitment_evaluation.py::TestOrderCommitmentEvaluationIdentity::test_capacity_cutoff_change_creates_deterministic_new_identity_not_content_conflict tests/test_order_commitment_evaluation.py::TestOrderCommitmentEvaluationIdentity::test_material_cutoff_crossing_inbound_creates_deterministic_new_identity -q --basetemp .tmp/pytest-mto-identity-green -p no:cacheprovider
git add -- sdbr/order_commitment_evaluation.py tests/test_order_commitment_evaluation.py
git commit -m "feat: register canonical MTO evaluations"
~~~

Expected: exactly seven items pass.

- [ ] **Step 6A (supersession RED): run the two lifecycle items**

~~~powershell
pytest tests/test_order_commitment_evaluation.py::TestOrderCommitmentEvaluationIdentity::test_only_open_same_logical_order_is_superseded tests/test_order_commitment_evaluation.py::TestOrderCommitmentEvaluationIdentity::test_accepted_or_rejected_evidence_cannot_be_superseded --collect-only -q
pytest tests/test_order_commitment_evaluation.py::TestOrderCommitmentEvaluationIdentity::test_only_open_same_logical_order_is_superseded tests/test_order_commitment_evaluation.py::TestOrderCommitmentEvaluationIdentity::test_accepted_or_rejected_evidence_cannot_be_superseded -q --basetemp .tmp/pytest-mto-supersession-red -p no:cacheprovider
~~~

Expected: exactly two items collect and fail.

- [ ] **Step 6B (supersession implement): install `exact_order_commitment_intake_replay` and `supersede_open_order_commitment_evaluations` above**

- [ ] **Step 6C (supersession GREEN/commit): verify two items, then all fifteen class items**

~~~powershell
pytest tests/test_order_commitment_evaluation.py::TestOrderCommitmentEvaluationIdentity::test_only_open_same_logical_order_is_superseded tests/test_order_commitment_evaluation.py::TestOrderCommitmentEvaluationIdentity::test_accepted_or_rejected_evidence_cannot_be_superseded -q --basetemp .tmp/pytest-mto-supersession-green -p no:cacheprovider
pytest tests/test_order_commitment_evaluation.py::TestOrderCommitmentEvaluationIdentity --collect-only -q
pytest tests/test_order_commitment_evaluation.py::TestOrderCommitmentEvaluationIdentity -q --basetemp .tmp/pytest-mto-identity-complete -p no:cacheprovider
git add -- sdbr/order_commitment_evaluation.py tests/test_order_commitment_evaluation.py
git commit -m "feat: supersede only open MTO evaluations"
~~~

Expected: the focused items pass and exactly fifteen class items collect and pass.

---

### Task 11: Decision Fingerprint and Phase 0 Acceptance Preparation

**Files and anchors**
- Modify `sdbr/order_commitment_evaluation.py`; add decision and record builders.
- Modify `tests/test_order_commitment_evaluation.py` after identity tests.

**IDs:** `BE-SDBR-006` through `BE-SDBR-010`.

**Produces**

~~~python
def canonical_decision_fingerprint(
    *,
    evaluation: Mapping[str, object],
    decision_id: str,
    decision: str,
    actor_id: str,
    reason: str,
    ccr_risk_acknowledged: bool,
    material_risk_acknowledged: bool,
) -> str:

def prepare_mto_acceptance(
    *,
    evaluation: Mapping[str, object],
    existing_commitments: Mapping[str, dict[str, object]],
    decision_id: str,
    decision: str,
    decided_by: str,
    decided_at: datetime,
    reason: str,
    ccr_risk_acknowledged: bool,
    material_risk_acknowledged: bool,
) -> PlanningReservationWriteSet:

def accepted_evaluation_record(
    *,
    evaluation: Mapping[str, object],
    write_set: PlanningReservationWriteSet,
    decision_id: str,
    decision: str,
    decided_by: str,
    decided_at: datetime,
    reason: str,
    ccr_risk_acknowledged: bool,
    material_risk_acknowledged: bool,
) -> dict[str, object]:

def rejected_evaluation_record(
    *,
    evaluation: Mapping[str, object],
    decision_id: str,
    decision: str,
    decided_by: str,
    decided_at: datetime,
    reason: str,
    ccr_risk_acknowledged: bool,
    material_risk_acknowledged: bool,
) -> dict[str, object]:
~~~

- [ ] **Step 1: Write action, acknowledgement, and fingerprint tests**

Add `TestOrderCommitmentAcceptancePreparation`:

- `test_requested_feasible_builds_canonical_mto_demand_and_material_rows`;
- `test_requested_skipped_builds_pending_material_and_zero_allocations`;
- `test_later_feasible_uses_recommended_promise`;
- `test_later_skipped_uses_conditional_recommended_action_and_zero_allocations`;
- `test_all_reference_and_exceeded_selected_candidates_require_ccr_ack`;
- `test_all_skipped_acceptance_actions_require_material_ack`;
- `test_reject_never_requires_ccr_or_material_acknowledgement`;
- `test_insufficient_shortage_and_not_assessable_reject_acceptance`;
- `test_expired_latest_completion_rejects_acceptance`;
- `test_decision_fingerprint_excludes_decided_at_and_covers_every_canonical_field`;
- `test_acceptance_uses_normalize_demand_commitment_and_preserves_mto_context`.

~~~powershell
pytest tests/test_order_commitment_evaluation.py::TestOrderCommitmentAcceptancePreparation -q --basetemp .tmp/pytest-mto-acceptance-prep-red -p no:cacheprovider
~~~

Expected: eleven items fail because acceptance functions are absent.

- [ ] **Step 2: Install complete validation, fingerprint, and acceptance preparation**

~~~python
def _decision_text(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise OrderCommitmentConflict(f"{field} is required.")
    return value.strip()


def canonical_decision_fingerprint(
    *,
    evaluation: Mapping[str, object],
    decision_id: str,
    decision: str,
    actor_id: str,
    reason: str,
    ccr_risk_acknowledged: bool,
    material_risk_acknowledged: bool,
) -> str:
    identity = {
        "DecisionID": _decision_text(decision_id, "DecisionID"),
        "EvaluationID": evaluation["EvaluationID"],
        "EvaluationFingerprint": evaluation["EvaluationFingerprint"],
        "Decision": _decision_text(decision, "Decision"),
        "ActorID": _decision_text(actor_id, "ActorID"),
        "Reason": _decision_text(reason, "Reason"),
        "CcrRiskAcknowledged": bool(ccr_risk_acknowledged),
        "MaterialRiskAcknowledged": bool(
            material_risk_acknowledged
        ),
    }
    return canonical_fingerprint(identity)


def prepare_mto_acceptance(
    *,
    evaluation: Mapping[str, object],
    existing_commitments: Mapping[str, dict[str, object]],
    decision_id: str,
    decision: str,
    decided_by: str,
    decided_at: datetime,
    reason: str,
    ccr_risk_acknowledged: bool,
    material_risk_acknowledged: bool,
) -> PlanningReservationWriteSet:
    normalized_decision_id = _decision_text(decision_id, "DecisionID")
    normalized_actor = _decision_text(decided_by, "DecidedBy")
    _decision_text(reason, "Reason")
    decided_at = _utc(require_aware(decided_at, "DecidedAt"))
    if evaluation["Status"] != "AwaitingPlannerDecision":
        raise OrderCommitmentConflict("Evaluation is not decision-eligible.")
    context = ACCEPTANCE_ACTION_CONTEXT.get(decision)
    if (
        context is None
        or decision not in evaluation["Recommendation"]["AllowedActions"]
    ):
        raise OrderCommitmentConflict("Decision is not allowed.")
    capacity_status, material_status, candidate_key = context
    if evaluation["ShadowSchedule"]["Status"] != capacity_status:
        raise OrderCommitmentConflict(
            "Decision capacity context does not match."
        )
    if evaluation["MaterialAssessment"]["Status"] != material_status:
        raise OrderCommitmentConflict(
            "Decision material context does not match."
        )
    requirements = action_acknowledgement_requirements(
        action=decision,
        requires_ccr_acknowledgement=bool(
            evaluation["Recommendation"]["RequiresCcrAcknowledgement"]
        ),
        requires_material_acknowledgement=bool(
            evaluation["Recommendation"][
                "RequiresMaterialAcknowledgement"
            ]
        ),
    )
    if (
        requirements["RequiresCcrAcknowledgement"]
        and not ccr_risk_acknowledged
    ):
        raise OrderCommitmentConflict(
            "CCR risk acknowledgement is required."
        )
    if (
        requirements["RequiresMaterialAcknowledgement"]
        and not material_risk_acknowledged
    ):
        raise OrderCommitmentConflict(
            "Material risk acknowledgement is required."
        )
    candidate = evaluation["ShadowSchedule"].get(candidate_key)
    if not isinstance(candidate, Mapping):
        raise OrderCommitmentConflict(
            "Selected capacity assessment is missing."
        )
    accepted_promise_at = _parse_aware(candidate["PromiseAt"])
    for row in candidate.get("ReservationRequests", []):
        if _parse_aware(row["LatestAllowedCompletionAt"]) <= decided_at:
            raise OrderCommitmentConflict(
                "Selected reservation window has expired."
            )

    order = evaluation["Order"]
    demand = create_demand_commitment(
        demand_source_type="MTOCustomerOrder",
        source_system=order["SourceSystem"],
        source_object_type=order["SourceObjectType"],
        source_object_id=order["OrderID"],
        source_object_version=order["OrderVersion"],
        demand_line_id=order["DemandLineID"],
        item_or_product_id=order["ProductID"],
        location_id=order["LocationID"],
        quantity=order["Quantity"],
        uom=order["Uom"],
        required_at=accepted_promise_at,
        demand_class="MTO",
        trace_id=order["TraceID"],
    )
    demand.update({
        "OrderCommitmentEvaluationID": evaluation["EvaluationID"],
        "BaselinePlanningRunID": evaluation["Basis"][
            "BaselinePlanningRunID"
        ],
        "OperatingModelConfigurationID": evaluation["Basis"][
            "OperatingModelConfigurationID"
        ],
        "OperatingModelFingerprint": evaluation["Basis"][
            "OperatingModelFingerprint"
        ],
        "SchedulingConfigurationID": evaluation["Basis"][
            "SchedulingConfigurationID"
        ],
        "DDMRPConfigurationID": evaluation["Basis"][
            "DDMRPConfigurationID"
        ],
        "ReleasePolicyVersionID": evaluation["Basis"][
            "ReleasePolicyVersionID"
        ],
        "RoutingID": order["RoutingID"],
        "BusinessPriority": order["BusinessPriority"],
        "AcceptedPromiseAt": accepted_promise_at.isoformat(),
        "MaterialCommitmentStatus": (
            "PlannedAllocationPrepared"
            if material_status == "Feasible"
            else "PendingConfirmation"
        ),
        "PendingMaterialRequirements": (
            []
            if material_status == "Feasible"
            else deepcopy(
                evaluation["MaterialAssessment"]["PendingRequirements"]
            )
        ),
        "ExternalOrderAcceptance": "NotPerformed",
        "PlanningRunCreation": "NotPerformed",
        "ProductionMutation": "NotPerformed",
    })
    demand = normalize_demand_commitment(demand)
    material_requests = (
        evaluation["MaterialAssessment"]["AllocationRequests"]
        if material_status == "Feasible"
        else []
    )
    return prepare_reservation_confirmation(
        demand_commitment=demand,
        existing_commitments=existing_commitments,
        confirmation_id=normalized_decision_id,
        confirmed_by=normalized_actor,
        confirmed_at=decided_at,
        capacity_requests=candidate.get("ReservationRequests", []),
        material_requests=material_requests,
    )
~~~

- [ ] **Step 3: Install complete immutable accepted/rejected record builders**

~~~python
def _decision_evidence(
    *,
    evaluation: Mapping[str, object],
    decision_id: str,
    decision: str,
    decided_by: str,
    decided_at: datetime,
    reason: str,
    ccr_risk_acknowledged: bool,
    material_risk_acknowledged: bool,
) -> dict[str, object]:
    normalized_decision_id = _decision_text(decision_id, "DecisionID")
    normalized_actor = _decision_text(decided_by, "DecidedBy")
    normalized_reason = _decision_text(reason, "Reason")
    decided_at = _utc(require_aware(decided_at, "DecidedAt"))
    return {
        "DecisionID": normalized_decision_id,
        "DecisionFingerprint": canonical_decision_fingerprint(
            evaluation=evaluation,
            decision_id=normalized_decision_id,
            decision=decision,
            actor_id=normalized_actor,
            reason=normalized_reason,
            ccr_risk_acknowledged=ccr_risk_acknowledged,
            material_risk_acknowledged=material_risk_acknowledged,
        ),
        "Decision": decision,
        "DecidedBy": normalized_actor,
        "DecidedAt": decided_at.isoformat(),
        "Reason": normalized_reason,
        "CcrRiskAcknowledged": bool(ccr_risk_acknowledged),
        "MaterialRiskAcknowledged": bool(
            material_risk_acknowledged
        ),
    }


def accepted_evaluation_record(
    *,
    evaluation: Mapping[str, object],
    write_set: PlanningReservationWriteSet,
    decision_id: str,
    decision: str,
    decided_by: str,
    decided_at: datetime,
    reason: str,
    ccr_risk_acknowledged: bool,
    material_risk_acknowledged: bool,
) -> dict[str, object]:
    if evaluation["Status"] != "AwaitingPlannerDecision":
        raise OrderCommitmentConflict("Evaluation is not decision-eligible.")
    if decision not in ACCEPTANCE_ACTION_CONTEXT:
        raise OrderCommitmentConflict("Decision is not an acceptance action.")
    updated = deepcopy(dict(evaluation))
    evidence = _decision_evidence(
        evaluation=evaluation,
        decision_id=decision_id,
        decision=decision,
        decided_by=decided_by,
        decided_at=decided_at,
        reason=reason,
        ccr_risk_acknowledged=ccr_risk_acknowledged,
        material_risk_acknowledged=material_risk_acknowledged,
    )
    evidence.update({
        "AcceptedPromiseAt": write_set.demand_commitment[
            "AcceptedPromiseAt"
        ],
        "DemandCommitmentID": write_set.demand_commitment[
            "DemandCommitmentID"
        ],
        "ReservationBatchID": write_set.batch["ReservationBatchID"],
        "ExternalOrderAcceptance": "NotPerformed",
        "PlanningRunCreation": "NotPerformed",
        "ProductionMutation": "NotPerformed",
    })
    updated["Decision"] = evidence
    updated["Status"] = "AcceptedPendingFormalSchedule"
    updated["RecordVersion"] = int(evaluation["RecordVersion"]) + 1
    return updated


def rejected_evaluation_record(
    *,
    evaluation: Mapping[str, object],
    decision_id: str,
    decision: str,
    decided_by: str,
    decided_at: datetime,
    reason: str,
    ccr_risk_acknowledged: bool,
    material_risk_acknowledged: bool,
) -> dict[str, object]:
    if (
        evaluation["Status"] != "AwaitingPlannerDecision"
        or decision != "Reject"
        or decision not in evaluation["Recommendation"]["AllowedActions"]
    ):
        raise OrderCommitmentConflict("Rejection is not allowed.")
    updated = deepcopy(dict(evaluation))
    updated["Decision"] = _decision_evidence(
        evaluation=evaluation,
        decision_id=decision_id,
        decision=decision,
        decided_by=decided_by,
        decided_at=decided_at,
        reason=reason,
        ccr_risk_acknowledged=ccr_risk_acknowledged,
        material_risk_acknowledged=material_risk_acknowledged,
    )
    updated["Status"] = "Rejected"
    updated["RecordVersion"] = int(evaluation["RecordVersion"]) + 1
    return updated
~~~

- [ ] **Step 4A (acceptance contexts RED): run the four candidate/action items**

~~~powershell
pytest tests/test_order_commitment_evaluation.py::TestOrderCommitmentAcceptancePreparation::test_requested_feasible_builds_canonical_mto_demand_and_material_rows tests/test_order_commitment_evaluation.py::TestOrderCommitmentAcceptancePreparation::test_requested_skipped_builds_pending_material_and_zero_allocations tests/test_order_commitment_evaluation.py::TestOrderCommitmentAcceptancePreparation::test_later_feasible_uses_recommended_promise tests/test_order_commitment_evaluation.py::TestOrderCommitmentAcceptancePreparation::test_later_skipped_uses_conditional_recommended_action_and_zero_allocations --collect-only -q
pytest tests/test_order_commitment_evaluation.py::TestOrderCommitmentAcceptancePreparation::test_requested_feasible_builds_canonical_mto_demand_and_material_rows tests/test_order_commitment_evaluation.py::TestOrderCommitmentAcceptancePreparation::test_requested_skipped_builds_pending_material_and_zero_allocations tests/test_order_commitment_evaluation.py::TestOrderCommitmentAcceptancePreparation::test_later_feasible_uses_recommended_promise tests/test_order_commitment_evaluation.py::TestOrderCommitmentAcceptancePreparation::test_later_skipped_uses_conditional_recommended_action_and_zero_allocations -q --basetemp .tmp/pytest-mto-prep-context-red -p no:cacheprovider
~~~

Expected: exactly four items collect and fail.

- [ ] **Step 4B (acceptance contexts implement): install `prepare_mto_acceptance` and its validation helpers above**

- [ ] **Step 4C (acceptance contexts GREEN/commit): verify four items**

~~~powershell
pytest tests/test_order_commitment_evaluation.py::TestOrderCommitmentAcceptancePreparation::test_requested_feasible_builds_canonical_mto_demand_and_material_rows tests/test_order_commitment_evaluation.py::TestOrderCommitmentAcceptancePreparation::test_requested_skipped_builds_pending_material_and_zero_allocations tests/test_order_commitment_evaluation.py::TestOrderCommitmentAcceptancePreparation::test_later_feasible_uses_recommended_promise tests/test_order_commitment_evaluation.py::TestOrderCommitmentAcceptancePreparation::test_later_skipped_uses_conditional_recommended_action_and_zero_allocations -q --basetemp .tmp/pytest-mto-prep-context-green -p no:cacheprovider
git add -- sdbr/order_commitment_evaluation.py tests/test_order_commitment_evaluation.py
git commit -m "feat: prepare MTO acceptance contexts"
~~~

Expected: exactly four items pass.

- [ ] **Step 5A (acknowledgement/guard RED): run the five guard items**

~~~powershell
pytest tests/test_order_commitment_evaluation.py::TestOrderCommitmentAcceptancePreparation::test_all_reference_and_exceeded_selected_candidates_require_ccr_ack tests/test_order_commitment_evaluation.py::TestOrderCommitmentAcceptancePreparation::test_all_skipped_acceptance_actions_require_material_ack tests/test_order_commitment_evaluation.py::TestOrderCommitmentAcceptancePreparation::test_reject_never_requires_ccr_or_material_acknowledgement tests/test_order_commitment_evaluation.py::TestOrderCommitmentAcceptancePreparation::test_insufficient_shortage_and_not_assessable_reject_acceptance tests/test_order_commitment_evaluation.py::TestOrderCommitmentAcceptancePreparation::test_expired_latest_completion_rejects_acceptance --collect-only -q
pytest tests/test_order_commitment_evaluation.py::TestOrderCommitmentAcceptancePreparation::test_all_reference_and_exceeded_selected_candidates_require_ccr_ack tests/test_order_commitment_evaluation.py::TestOrderCommitmentAcceptancePreparation::test_all_skipped_acceptance_actions_require_material_ack tests/test_order_commitment_evaluation.py::TestOrderCommitmentAcceptancePreparation::test_reject_never_requires_ccr_or_material_acknowledgement tests/test_order_commitment_evaluation.py::TestOrderCommitmentAcceptancePreparation::test_insufficient_shortage_and_not_assessable_reject_acceptance tests/test_order_commitment_evaluation.py::TestOrderCommitmentAcceptancePreparation::test_expired_latest_completion_rejects_acceptance -q --basetemp .tmp/pytest-mto-prep-guards-red -p no:cacheprovider
~~~

Expected: exactly five items collect and fail on missing action-specific guards.

- [ ] **Step 5B (acknowledgement/guard implement): wire `action_acknowledgement_requirements`, allowed-action checks, and `_parse_aware` expiry checks exactly as shown**

- [ ] **Step 5C (acknowledgement/guard GREEN/commit): verify five items**

~~~powershell
pytest tests/test_order_commitment_evaluation.py::TestOrderCommitmentAcceptancePreparation::test_all_reference_and_exceeded_selected_candidates_require_ccr_ack tests/test_order_commitment_evaluation.py::TestOrderCommitmentAcceptancePreparation::test_all_skipped_acceptance_actions_require_material_ack tests/test_order_commitment_evaluation.py::TestOrderCommitmentAcceptancePreparation::test_reject_never_requires_ccr_or_material_acknowledgement tests/test_order_commitment_evaluation.py::TestOrderCommitmentAcceptancePreparation::test_insufficient_shortage_and_not_assessable_reject_acceptance tests/test_order_commitment_evaluation.py::TestOrderCommitmentAcceptancePreparation::test_expired_latest_completion_rejects_acceptance -q --basetemp .tmp/pytest-mto-prep-guards-green -p no:cacheprovider
git add -- sdbr/order_commitment_evaluation.py tests/test_order_commitment_evaluation.py
git commit -m "feat: enforce MTO decision acknowledgements"
~~~

Expected: exactly five items pass.

- [ ] **Step 6A (fingerprint/records RED): run the two canonical-record items**

~~~powershell
pytest tests/test_order_commitment_evaluation.py::TestOrderCommitmentAcceptancePreparation::test_decision_fingerprint_excludes_decided_at_and_covers_every_canonical_field tests/test_order_commitment_evaluation.py::TestOrderCommitmentAcceptancePreparation::test_acceptance_uses_normalize_demand_commitment_and_preserves_mto_context --collect-only -q
pytest tests/test_order_commitment_evaluation.py::TestOrderCommitmentAcceptancePreparation::test_decision_fingerprint_excludes_decided_at_and_covers_every_canonical_field tests/test_order_commitment_evaluation.py::TestOrderCommitmentAcceptancePreparation::test_acceptance_uses_normalize_demand_commitment_and_preserves_mto_context -q --basetemp .tmp/pytest-mto-prep-record-red -p no:cacheprovider
~~~

Expected: exactly two items collect and fail.

- [ ] **Step 6B (fingerprint/records implement): install `canonical_decision_fingerprint`, `_decision_evidence`, and both terminal record builders above**

- [ ] **Step 6C (fingerprint/records GREEN/commit): verify two items, all eleven class items, and Phase 0 regressions**

~~~powershell
pytest tests/test_order_commitment_evaluation.py::TestOrderCommitmentAcceptancePreparation::test_decision_fingerprint_excludes_decided_at_and_covers_every_canonical_field tests/test_order_commitment_evaluation.py::TestOrderCommitmentAcceptancePreparation::test_acceptance_uses_normalize_demand_commitment_and_preserves_mto_context -q --basetemp .tmp/pytest-mto-prep-record-green -p no:cacheprovider
pytest tests/test_order_commitment_evaluation.py::TestOrderCommitmentAcceptancePreparation --collect-only -q
pytest tests/test_order_commitment_evaluation.py tests/test_planning_commitments.py tests/test_planning_reservations.py tests/test_planning_reservation_view.py -q --basetemp .tmp/pytest-mto-domain-green -p no:cacheprovider
git add -- sdbr/order_commitment_evaluation.py tests/test_order_commitment_evaluation.py
git commit -m "feat: persist canonical MTO decision evidence"
~~~

Expected: the focused items pass, exactly eleven class items collect, and all shared-ledger regressions pass.

---

### Task 12: Persist Evaluation and Event Evidence

**Files and anchors**
- Modify `sdbr/state_store.py:60-125` `WorkbenchStateStore`.
- Modify `sdbr/state_store.py:347` `_state_payloads`.
- Modify `sdbr/state_store.py:500-630` `_apply_payloads`.
- Modify `sdbr/state_store.py:640-680` `_clear`.
- Modify `sdbr/state_store.py:730-790` `_state_counts`.
- Modify `tests/test_state_store.py` after existing SQLite/rollback coverage.

**IDs:** `BE-SDBR-010`.

**Produces**

~~~python
order_commitment_evaluations: dict[str, dict[str, object]]
order_commitment_events: list[dict[str, object]]
~~~

- [ ] **Step 1: Write standalone persistence tests**

Add `TestOrderCommitmentStatePersistence`:

- `test_order_commitment_collections_round_trip_through_sqlite`;
- `test_order_commitment_collections_appear_in_health_and_clear`;
- `test_order_commitment_collections_restore_content_and_aliases_after_atomic_rollback`.

The rollback test captures `id(store.order_commitment_evaluations)` and `id(store.order_commitment_events)`, mutates both inside `atomic_update`, raises `RuntimeError`, then asserts both IDs and deep content match the pre-state.

~~~powershell
pytest tests/test_state_store.py::TestOrderCommitmentStatePersistence -q --basetemp .tmp/pytest-mto-store-red -p no:cacheprovider
~~~

Expected: three failures because fields are absent.

- [ ] **Step 2: Add both fields through every existing state boundary**

Add adjacent to Phase 0 fields:

~~~python
order_commitment_evaluations: dict[str, dict[str, object]] = field(
    default_factory=dict
)
order_commitment_events: list[dict[str, object]] = field(
    default_factory=list
)
~~~

Add payload keys with those exact snake-case names. Restore with `self.order_commitment_evaluations.update(deepcopy(payloads.get("order_commitment_evaluations", {})))` and `self.order_commitment_events.extend(deepcopy(payloads.get("order_commitment_events", [])))`; clear both; report counts `OrderCommitmentEvaluations` and `OrderCommitmentEvents`.

Do not change schema version. The SQLite store is a keyed JSON bag and already defaults missing keys. Do not add custom rollback logic: existing complete-state snapshot/restore handles public dataclass fields and alias preservation.

- [ ] **Step 3: Verify and commit**

~~~powershell
pytest tests/test_state_store.py::TestOrderCommitmentStatePersistence --collect-only -q
pytest tests/test_state_store.py -q --basetemp .tmp/pytest-mto-store-green -p no:cacheprovider
git add -- sdbr/state_store.py tests/test_state_store.py
git commit -m "feat: persist MTO evaluation evidence"
~~~

Expected: three class tests and the full state-store suite pass.

---

### Task 13: Exact Sanitized Workbench and Detail Projections

**Files and anchors**
- Create `sdbr/order_commitment_view.py`.
- Create `tests/test_order_commitment_view.py`.

**IDs:** `BE-SDBR-010`, `UI-COMMIT-001`.

**Produces**

~~~python
def build_order_commitment_workbench(
    *,
    evaluations: list[dict[str, object]],
    demand_commitments: Mapping[str, dict[str, object]],
    reservation_batches: Mapping[str, dict[str, object]],
) -> dict[str, object]:

def build_order_commitment_detail(
    *,
    evaluation: dict[str, object],
    events: list[dict[str, object]],
    demand_commitment: dict[str, object] | None,
    reservation_batch: dict[str, object] | None,
) -> dict[str, object]:
~~~

- [ ] **Step 1: Write exact field/sanitization tests**

Add `TestOrderCommitmentViewContract`:

- `test_workbench_row_has_exact_field_set_and_exception_reservation_status`;
- `test_terminal_rows_have_empty_allowed_actions`;
- `test_held_batch_maps_to_planning_error_pending`;
- `test_missing_accepted_batch_maps_to_reservation_evidence_missing`;
- `test_detail_has_exact_top_level_and_whitelisted_capacity_material_fields`;
- `test_audit_history_drops_unknown_details_trace_and_raw_payloads`;
- `test_fingerprints_exist_only_in_collapsed_technical_details`;
- `test_raw_basis_order_master_and_snapshot_payloads_never_appear`;
- `test_workbench_sort_and_summary_are_deterministic`.

~~~powershell
pytest tests/test_order_commitment_view.py::TestOrderCommitmentViewContract -q --basetemp .tmp/pytest-mto-view-red -p no:cacheprovider
~~~

Expected: import fails because the module is absent.

- [ ] **Step 2: Implement exact row derivation**

Summary:

~~~python
{
    "EvaluationCount": len(rows),
    "AwaitingDecisionCount": count_status("AwaitingPlannerDecision"),
    "ConfirmationRequiredCount": count_recommendation(
        "PlannerConfirmationRequired"
    ),
    "MaterialPendingCount": count_material({
        "SkippedPendingConfirmation", "EvidenceInsufficient", "Shortage"
    }),
    "AcceptedPendingScheduleCount": count_status(
        "AcceptedPendingFormalSchedule"
    ),
    "RejectedCount": count_status("Rejected"),
    "ExceptionCount": count_exception_not_none(),
}
~~~

Resolve linked demand/batch from decision IDs first, then matching `OrderCommitmentEvaluationID`. Derive:

~~~python
reservation_status = (
    "NotReserved"
    if evaluation["Status"] != "AcceptedPendingFormalSchedule"
    and reservation_batch is None
    else "ReservationEvidenceMissing"
    if evaluation["Status"] == "AcceptedPendingFormalSchedule"
    and reservation_batch is None
    else str(reservation_batch["Status"])
)
exception_status = (
    "PlanningErrorPending"
    if reservation_status == "HeldForPlanningError"
    else "ReservationEvidenceMissing"
    if reservation_status == "ReservationEvidenceMissing"
    else "AssessmentBlocked"
    if shadow["Status"] == "NotAssessable" or shadow["Issues"]
    else "MaterialEvidenceBlocked"
    if material["Status"] == "EvidenceInsufficient"
    else "None"
)
allowed_actions = (
    deepcopy(recommendation["AllowedActions"])
    if evaluation["Status"] == "AwaitingPlannerDecision"
    else []
)
~~~

Return exactly `ORDER_COMMITMENT_ROW_FIELDS`. Sort by descending aware `EvaluatedAt`, then `OrderID`, then `EvaluationID`.

- [ ] **Step 3: Implement exact detail projection**

Top level:

~~~python
DETAIL_FIELDS = (
    "EvaluationID", "Status", "EvaluatedAt", "RecordVersion", "Order",
    "CapacityEvidence", "MaterialEvidence", "Recommendation",
    "EvidenceReferences", "Decision", "Reservation", "AuditHistory",
    "TechnicalDetails", "Boundary",
)
~~~

Whitelists:

~~~python
ORDER_FIELDS = (
    "OrderID", "DemandLineID", "ProductID", "LocationID", "Quantity",
    "Uom", "RequestedDueAt", "BusinessPriority", "RoutingID",
)
CAPACITY_WINDOW_FIELDS = (
    "ResourceID", "OperationID", "WindowStartAt", "WindowEndAt",
    "UsableWindowEndAt", "LatestAllowedCompletionAt", "CapacityMinutes",
    "UsableTemporalCapacityMinutes", "ScheduledLoadMinutes",
    "ScheduledLoadBeforeDeadlineMinutes", "ExistingReservationMinutes",
    "CandidateLoadMinutes", "LoadBeforeMinutes", "LoadAfterMinutes",
    "LoadAfterPercent", "LoadStatus", "ThresholdExceeded",
    "PhysicalCapacityExceeded", "AlternateResourceIDs",
)
MATERIAL_LINE_FIELDS = (
    "RequirementLineID", "ItemID", "LocationID", "Uom", "RequiredQty",
    "OnHandQty", "EligibleInboundQty", "AuthorityAllocatedQty",
    "OtherPlanningAllocatedQty", "QualifiedSupplyQty",
    "UncommittedAvailabilityQty", "CoverageStatus",
)
~~~

`EvidenceReferences` includes baseline run/master/config/release IDs and selected snapshot ID/captured/status/age/max. `Decision` includes only decision code, actor/time/reason, acknowledgements, promise, demand and batch IDs. `TechnicalDetails` includes fingerprints, trace ID, and correlation IDs but no raw objects.

Audit rows are projected through `AUDIT_FIELDS`; project `Details` by `SAFE_AUDIT_DETAIL_FIELDS` intersection. Boundary is always:

~~~python
{
    "RecommendationOnly": True,
    "ExternalOrderAcceptance": "NotPerformed",
    "PlanningRunCreation": "NotPerformed",
    "ProductionMutation": "NotPerformed",
    "ReleaseMaterialGateStillRequired": True,
}
~~~

- [ ] **Step 4: Verify and commit**

~~~powershell
pytest tests/test_order_commitment_view.py::TestOrderCommitmentViewContract --collect-only -q
pytest tests/test_order_commitment_view.py -q --basetemp .tmp/pytest-mto-view-green -p no:cacheprovider
git add -- sdbr/order_commitment_view.py tests/test_order_commitment_view.py
git commit -m "feat: project safe MTO commitment views"
~~~

Expected: nine named tests pass.

---

### Task 14: Reproducible Test-Environment MTO Baseline Seed

**Files and anchors**
- Modify `sdbr/test_data.py:20-35` constants and after `seed_baseline_test_data`.
- Modify `sdbr/api.py` after `planner_workbench_test_data_acceptance_reset_all`.
- Modify `tests/test_test_data.py` after existing reset endpoint tests.

**IDs:** `BE-DATA-014`, `BE-SDBR-010`.

**Produces**

~~~python
MTO_COMMITMENT_MASTER_DATA_VERSION_ID = "TST-MTO-MDV-COMMITMENT"
MTO_COMMITMENT_OPERATIONAL_STATE_ID = "TST-MTO-OPS-CURRENT"
MTO_COMMITMENT_BASELINE_RUN_ID = "TST-MTO-RUN-BASELINE"

def seed_mto_order_commitment_fixture(
    store: WorkbenchStateStore,
    *,
    captured_at: datetime,
) -> dict[str, object]:
~~~

- [ ] **Step 1: Write seed and endpoint tests**

Add `TestOrderCommitmentBrowserSeed`:

- `test_seed_builds_valid_master_fresh_snapshot_and_published_completed_baseline`;
- `test_seed_returns_exact_api_intake_template_and_window_ids`;
- `test_test_environment_reset_endpoint_uses_server_time_and_is_repeatable`;
- `test_production_environment_rejects_order_commitment_fixture_reset`.

~~~powershell
pytest tests/test_test_data.py::TestOrderCommitmentBrowserSeed -q --basetemp .tmp/pytest-mto-seed-red -p no:cacheprovider
~~~

Expected: four failures because fixture seed is absent.

- [ ] **Step 2: Install the complete repeatable fixture persistence body**

Extend `sdbr/test_data.py` imports with:

~~~python
from sdbr.plan_publication import schedule_fingerprint
from sdbr.planner_view import InventoryBufferPolicy
~~~

Then install this complete function. It clears only the MTO/Phase 0 runtime
collections owned by this test fixture, persists the master/snapshot/run, and
returns every identifier consumed by the API and browser tests.

~~~python
def seed_mto_order_commitment_fixture(
    store: WorkbenchStateStore,
    *,
    captured_at: datetime,
) -> dict[str, object]:
    if captured_at.tzinfo is None or captured_at.utcoffset() is None:
        raise ValueError("MTO fixture time must be timezone-aware.")
    captured_at = captured_at.astimezone(timezone.utc)
    due_date = captured_at.date() + timedelta(days=2)
    next_date = captured_at.date() + timedelta(days=3)
    due_start = datetime.combine(
        due_date, time(8, 0), tzinfo=timezone.utc
    )
    due_end = datetime.combine(
        due_date, time(16, 0), tzinfo=timezone.utc
    )
    next_start = datetime.combine(
        next_date, time(8, 0), tzinfo=timezone.utc
    )
    next_end = datetime.combine(
        next_date, time(16, 0), tzinfo=timezone.utc
    )

    store.order_commitment_evaluations.clear()
    store.order_commitment_events.clear()
    store.planning_demand_commitments.clear()
    store.planning_reservation_batches.clear()
    store.ccr_capacity_reservations.clear()
    store.material_planning_allocations.clear()
    store.planning_reservation_events.clear()
    store.processed_planning_event_keys.clear()

    day_calendar = WorkCalendar(
        calendar_id="TST-MTO-CAL-DAY",
        working_weekdays=set(range(7)),
        shifts=[Shift("Day", time(8, 0), time(16, 0))],
        maintenance_windows=[],
        holidays=set(),
    )
    resources = [
        Resource(
            "TST-MTO-CCR-1",
            "MTO Constraint",
            True,
            {due_date: 480, next_date: 480},
            calendar=day_calendar,
            capacity_units=1,
            efficiency_percent=100,
        ),
        Resource(
            "TST-MTO-NCR-1",
            "MTO Pack",
            False,
            {due_date: 480, next_date: 480},
            calendar=day_calendar,
        ),
    ]
    routing = Routing(
        product_id="TST-MTO-FG-1",
        routing_id="PRIMARY",
        is_primary=True,
        operations=[
            Operation("CCR-CUT", "TST-MTO-CCR-1", 60, 10),
            Operation("PACK", "TST-MTO-NCR-1", 30, 20),
        ],
    )
    inventory_buffers = [
        InventoryBufferPolicy(
            "TST-MTO-RM-1", "TST-MAIN", 100.0, 20.0, 40.0, 80.0
        )
    ]
    validation = validate_master_data(
        resources=resources,
        routings=[routing],
        orders=[],
        inventory_buffers=inventory_buffers,
        material_requirements=[],
        calendar_timezone="UTC",
    )
    if not validation.is_valid:
        raise ValueError("MTO fixture master data must validate.")
    store.master_data_versions[MTO_COMMITMENT_MASTER_DATA_VERSION_ID] = {
        "VersionID": MTO_COMMITMENT_MASTER_DATA_VERSION_ID,
        "CapturedAt": captured_at.isoformat(),
        "SourceSystem": "SDBR-TestData",
        "CreatedBy": "sdbr-test-data",
        "CalendarTimezone": "UTC",
        "Status": "Valid",
        "Resources": _resources_to_dict(resources),
        "Routings": _routings_to_dict([routing]),
        "Orders": [],
        "InventoryBuffers": _inventory_buffers_to_dict(
            inventory_buffers
        ),
        "MaterialRequirements": [],
        "Validation": _validation_to_dict(validation),
    }

    snapshot = create_operational_state_snapshot(
        snapshot_id=MTO_COMMITMENT_OPERATIONAL_STATE_ID,
        captured_at=captured_at - timedelta(minutes=5),
        inventory_buffers=inventory_buffers,
        material_availability=import_material_availability_from_rows([
            MaterialAvailabilityImportRow(
                "TST-MTO-RM-1", "TST-MAIN", 0.0, 0.0, None
            )
        ]),
        wip_limits=[],
    )
    store.operational_state_snapshots[snapshot.snapshot_id] = snapshot

    schedule = {
        "GeneratedAt": captured_at.isoformat(),
        "GanttRows": [
            {
                "ResourceID": "TST-MTO-CCR-1",
                "Bars": [
                    {
                        "OrderID": "TST-MTO-BASELOAD",
                        "OperationID": "TST-MTO-BASELOAD:CCR-CUT",
                        "BarType": "Processing",
                        "Start": due_start.isoformat(),
                        "End": (
                            due_start + timedelta(minutes=180)
                        ).isoformat(),
                        "DurationMinutes": 180,
                    }
                ],
            }
        ],
        "Orders": [],
        "Diagnostics": [],
    }
    frozen_release_policy = {
        "VersionID": "TST-MTO-RELEASE-POLICY-1",
        "RopeBufferMinutes": 60,
        "MaterialCheckWindowMinutes": 1440,
    }
    run = {
        "RunID": MTO_COMMITMENT_BASELINE_RUN_ID,
        "ProblemID": "TST-MTO-PROBLEM-BASELINE",
        "Status": "Completed",
        "PublicationStatus": "Published",
        "MasterDataVersionID": MTO_COMMITMENT_MASTER_DATA_VERSION_ID,
        "OperationalStateSnapshotID": snapshot.snapshot_id,
        "OperatingModelConfigurationID": None,
        "OperatingModelFingerprint": None,
        "SchedulingConfigurationID": None,
        "DDMRPConfigurationID": None,
        "ReleasePolicyVersionID": frozen_release_policy["VersionID"],
        "FrozenReleasePolicy": frozen_release_policy,
        "FrozenBaseCalendars": [],
        "FrozenResourceCalendarAssignments": [],
        "FrozenCalendarOverrides": [],
        "SetupTransitions": [],
        "TimeBufferMinutes": 60,
        "RequestedBy": "sdbr-test-data",
        "RequestedAt": captured_at.isoformat(),
        "StartedAt": captured_at.isoformat(),
        "CompletedAt": captured_at.isoformat(),
        "Schedule": schedule,
        "PublicationHistory": [],
    }
    run["ScheduleFingerprint"] = schedule_fingerprint(run)
    store.planning_runs[MTO_COMMITMENT_BASELINE_RUN_ID] = run

    return {
        "MasterDataVersionID": MTO_COMMITMENT_MASTER_DATA_VERSION_ID,
        "OperationalStateSnapshotID": snapshot.snapshot_id,
        "BaselinePlanningRunID": MTO_COMMITMENT_BASELINE_RUN_ID,
        "CapacityWindowKeys": [
            (
                "TST-MTO-CCR-1",
                due_start.isoformat(),
                due_end.isoformat(),
            ),
            (
                "TST-MTO-CCR-1",
                next_start.isoformat(),
                next_end.isoformat(),
            ),
        ],
        "IntakePayloadTemplate": {
            "SourceSystem": "MockERP",
            "SourceObjectType": "CustomerOrder",
            "OrderID": "TST-MTO-SO-ORDINARY",
            "OrderVersion": "1",
            "DemandLineID": "10",
            "ProductID": "TST-MTO-FG-1",
            "LocationID": "TST-MAIN",
            "Quantity": 1.0,
            "Uom": "EA",
            "RequestedDueAt": datetime.combine(
                due_date, time(18, 0), tzinfo=timezone.utc
            ).isoformat(),
            "BusinessPriority": 100,
            "ReceivedAt": captured_at.isoformat(),
            "TraceID": "TRACE-TST-MTO-ORDINARY",
            "BaselinePlanningRunID": MTO_COMMITMENT_BASELINE_RUN_ID,
            "RoutingID": "PRIMARY",
            "OperationalStateSnapshotID": snapshot.snapshot_id,
            "MaterialRequirements": [
                {
                    "RequirementLineID": (
                        "TST-MTO-SO-ORDINARY:10:TST-MTO-RM-1"
                    ),
                    "ItemID": "TST-MTO-RM-1",
                    "LocationID": "TST-MAIN",
                    "RequiredQty": 5.0,
                    "Uom": "EA",
                }
            ],
        },
    }
~~~

- [ ] **Step 3: Add a test-only public reset endpoint**

Extend the existing `sdbr.test_data` import in `sdbr/api.py` with
`seed_mto_order_commitment_fixture` before adding the route:

~~~python
from sdbr.test_data import (
    reset_test_case_state,
    seed_baseline_test_data,
    seed_mto_order_commitment_fixture,
    test_case_catalog_payload,
)
~~~

~~~python
@app.post("/planner/workbench/test-data/order-commitment/reset")
def planner_workbench_order_commitment_test_data_reset():
    endpoint = "/planner/workbench/test-data/order-commitment/reset"
    if active_environment.is_production:
        return JSONResponse(
            status_code=409,
            content={
                "Endpoint": endpoint,
                "StatusCode": 409,
                "Data": {"Status": "TestDataResetNotAllowed"},
            },
        )
    seed_baseline_test_data(active_store)
    fixture = seed_mto_order_commitment_fixture(
        active_store,
        captured_at=server_utc_now(),
    )
    return {
        "Endpoint": endpoint,
        "StatusCode": 200,
        "Data": {"Status": "Reset", **fixture},
    }
~~~

This is the only browser prerequisite seeder; it writes the actual uvicorn SQLite store through a public test endpoint, never a test-only in-memory helper.

- [ ] **Step 4: Verify and commit**

~~~powershell
pytest tests/test_test_data.py::TestOrderCommitmentBrowserSeed --collect-only -q
pytest tests/test_test_data.py -q --basetemp .tmp/pytest-mto-seed-green -p no:cacheprovider
git add -- sdbr/test_data.py sdbr/api.py tests/test_test_data.py
git commit -m "test: seed MTO browser acceptance state"
~~~

Expected: four class tests and all test-data regressions pass.

---

### Task 15: MTO API Payloads, Auth Scope, and Test Fixture

**Files and anchors**
- Modify `sdbr/api.py:305` near `OrderPayload`.
- Modify `sdbr/api.py:1084-1190` `create_app` aliases and auth path tuple.
- Create `tests/test_order_commitment_api.py`.

**IDs:** `BE-SDBR-010`.

- [ ] **Step 1: Write API contract/auth tests**

In `tests/test_order_commitment_api.py`, create `_order_commitment_store(now)` using `seed_mto_order_commitment_fixture` with fixed UTC time, plus `_intake_payload` from its returned template. Add `TestOrderCommitmentApiContracts`:

- `test_intake_contract_accepts_explicit_snapshot_but_has_no_material_toggle`;
- `test_reevaluation_contract_has_no_material_window_or_threshold_override`;
- `test_decision_contract_accepts_all_four_acceptance_actions_and_reject`;
- `test_mto_payloads_forbid_unknown_authority_and_window_fields`;
- `test_auth_helper_allows_all_roles_get_and_only_planner_admin_post`.

Build auth requests exactly:

~~~python
def _auth_request(method: str, role: str) -> Request:
    return Request({
        "type": "http",
        "method": method,
        "path": "/planner/workbench/order-commitments/workbench",
        "headers": [
            (b"x-actor-id", b"actor-1"),
            (b"x-actor-role", role.encode("ascii")),
        ],
    })
~~~

Call `_planning_run_authorization_error` directly for GET/POST role assertions; later endpoint tests prove middleware coverage.

~~~powershell
pytest tests/test_order_commitment_api.py::TestOrderCommitmentApiContracts -q --basetemp .tmp/pytest-mto-api-contract-red -p no:cacheprovider
~~~

Expected: five failures because the MTO models and protected-path registration are absent.

- [ ] **Step 2: Add exact Pydantic models**

Extend the live import to `from pydantic import AwareDatetime, BaseModel, ConfigDict, Field`, then add:

~~~python
class MtoMaterialRequirementPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    RequirementLineID: str
    ItemID: str
    LocationID: str
    RequiredQty: float = Field(gt=0)
    Uom: str = "EA"

class MtoOrderCommitmentIntakePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
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
    OperationalStateSnapshotID: str | None = None
    MaterialRequirements: list[MtoMaterialRequirementPayload] = Field(
        default_factory=list
    )

class MtoOrderCommitmentReevaluationPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    RequestedBy: str
    BaselinePlanningRunID: str | None = None
    OperationalStateSnapshotID: str | None = None
    CheckMaterialAvailability: bool = True
    MaterialCheckSkipReason: str | None = None

class MtoOrderCommitmentDecisionPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    DecisionID: str
    Decision: Literal[
        "AcceptRequestedDate",
        "ConditionallyAcceptRequestedDate",
        "AcceptRecommendedDate",
        "ConditionallyAcceptRecommendedDate",
        "Reject",
    ]
    DecidedBy: str
    Reason: str
    ExpectedEvaluationFingerprint: str
    CcrRiskAcknowledged: bool = False
    MaterialRiskAcknowledged: bool = False


def _mto_order_from_payload(
    payload: MtoOrderCommitmentIntakePayload,
) -> dict[str, object]:
    return {
        "SourceSystem": payload.SourceSystem,
        "SourceObjectType": payload.SourceObjectType,
        "OrderID": payload.OrderID,
        "OrderVersion": payload.OrderVersion,
        "DemandLineID": payload.DemandLineID,
        "ProductID": payload.ProductID,
        "LocationID": payload.LocationID,
        "Quantity": payload.Quantity,
        "Uom": payload.Uom,
        "RequestedDueAt": payload.RequestedDueAt,
        "BusinessPriority": payload.BusinessPriority,
        "ReceivedAt": payload.ReceivedAt,
        "TraceID": payload.TraceID,
        "BaselinePlanningRunID": payload.BaselinePlanningRunID,
        "RoutingID": payload.RoutingID,
        "MaterialRequirements": [
            row.model_dump() for row in payload.MaterialRequirements
        ],
    }
~~~

Intake has no material opt-out. None of the three models accepts protection threshold, approved flag, material-window minutes, external acceptance, Planning Run creation, production mutation, DDAE configuration payload, or raw master/snapshot content.

- [ ] **Step 3: Alias state and extend existing role middleware**

Inside `create_app`:

~~~python
order_commitment_evaluations = (
    active_store.order_commitment_evaluations
)
order_commitment_events = active_store.order_commitment_events
~~~

Add `/planner/workbench/order-commitments` to the same protected-path tuple as planning runs/reservations. Existing `_planning_run_authorization_error` gives Viewer/Planner/Worker/Admin GET and Planner/Admin non-GET. Tasks 17-21 add each real route once; Task 15 adds no interim endpoint.

- [ ] **Step 4: Verify and commit**

~~~powershell
pytest tests/test_order_commitment_api.py::TestOrderCommitmentApiContracts --collect-only -q
pytest tests/test_order_commitment_api.py::TestOrderCommitmentApiContracts -q --basetemp .tmp/pytest-mto-api-contract-green -p no:cacheprovider
git add -- sdbr/api.py tests/test_order_commitment_api.py
git commit -m "feat: define MTO commitment API contracts"
~~~

Expected: five tests pass; unknown fields return 422.

---

### Task 16: State-to-Evaluation Orchestration

**Files and anchors**
- Modify `sdbr/api.py` inside `create_app` before route declarations; add `_build_order_commitment_evaluation_from_state`.
- Modify `tests/test_order_commitment_api.py` after contract tests.

**IDs:** `BE-SDBR-006` through `BE-SDBR-010`.

Extend existing `sdbr/api.py` imports exactly with:

~~~python
from sdbr.ccr_shadow_scheduler import (
    SHADOW_ALGORITHM,
    evaluate_ccr_shadow_schedule,
)
from sdbr.order_commitment_evaluation import (
    ACCEPTANCE_DECISIONS,
    OrderCommitmentConflict,
    OrderCommitmentSnapshotNotFound,
    REFERENCE_CCR_PROTECTION_POLICY,
    _parse_aware,
    accepted_evaluation_record,
    build_order_commitment_basis,
    candidate_demand_commitment_id,
    canonical_decision_fingerprint,
    canonical_fingerprint,
    canonical_json,
    canonical_order_commitment_decision_facts,
    create_order_commitment_evaluation,
    evaluate_mto_material_availability,
    exact_order_commitment_intake_replay,
    normalize_mto_order,
    prepare_mto_acceptance,
    register_order_commitment_evaluation,
    rejected_evaluation_record,
    select_order_commitment_operational_snapshot,
    supersede_open_order_commitment_evaluations,
)
from sdbr.order_commitment_view import (
    SAFE_AUDIT_DETAIL_FIELDS,
    build_order_commitment_detail,
    build_order_commitment_workbench,
)
from sdbr.planning_reservations import (
    ReservationConflict,
    ReservationLegacyMigrationRequired,
    apply_reservation_write_set,
    assert_reservation_write_set_replay_matches,
)
from sdbr.plan_publication import (
    publication_state,
    schedule_fingerprint as planning_schedule_fingerprint,
)
from sdbr.release_policy import release_policy_evidence, release_policy_settings
from sdbr.scheduling_solver import build_capacity_buckets_from_resources
~~~

These are the complete MTO imports for Tasks 16-21. Do not add a second,
partial import block in a later route task. Existing `api.py` imports already
provide `deepcopy`, `datetime`, `sha256`, `timezone`, `Mapping`, `ZoneInfo`,
`JSONResponse`, `Request`, payload rehydrators, calendar applicators, and the
live store aliases.

**Produces**

~~~python
def _order_commitment_error(
    *,
    endpoint: str,
    status_code: int,
    status: str,
    message: str,
    details: Mapping[str, object] | None = None,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "Endpoint": endpoint,
            "StatusCode": status_code,
            "Data": {
                "Status": status,
                "Message": message,
                **deepcopy(dict(details or {})),
            },
        },
    )

def _not_assessable_shadow(
    *,
    order: Mapping[str, object],
    evaluated_at: datetime,
    code: str,
    message: str,
) -> dict[str, object]:
    return {
        "Algorithm": deepcopy(SHADOW_ALGORITHM),
        "Status": "NotAssessable",
        "CapacityAssessmentCutoffAt": (
            evaluated_at.astimezone(timezone.utc).isoformat()
        ),
        "RequestedDueAt": order["RequestedDueAt"],
        "LatestCcrCompletionAt": None,
        "RequestedDateAssessment": {"Feasible": False},
        "EarliestSafeAssessment": None,
        "SelectedAssessment": None,
        "RelevantCapacityWindowKeys": [],
        "Issues": [{"Code": code, "Message": message}],
        "Summary": {
            "CcrOperationCount": 0,
            "SelectedWindowCount": 0,
            "MaximumLoadAfterPercent": None,
        },
    }

def _build_order_commitment_evaluation_from_state(
    *,
    endpoint: str,
    order: Mapping[str, object],
    evaluated_at: datetime,
    check_material_availability: bool,
    material_check_skip_reason: str | None,
    requested_operational_state_snapshot_id: str | None,
) -> dict[str, object] | JSONResponse:
~~~

- [ ] **Step 1: Write resolver tests**

Add `TestOrderCommitmentApiOrchestration`:

- `test_resolver_requires_completed_approved_or_published_baseline`;
- `test_resolver_requires_master_schedule_and_primary_route_references`;
- `test_resolver_selects_latest_current_snapshot_by_default`;
- `test_resolver_preserves_explicit_stale_and_future_as_insufficient_evidence`;
- `test_resolver_freezes_all_configuration_release_route_calendar_references`;
- `test_resolver_uses_only_reference_protection_policy`;
- `test_resolver_fingerprints_only_exact_relevant_capacity_and_material_rows`;
- `test_resolver_rejects_missing_calendar_timezone_conservatively`.

~~~powershell
pytest tests/test_order_commitment_api.py::TestOrderCommitmentApiOrchestration -q --basetemp .tmp/pytest-mto-orchestration-red -p no:cacheprovider
~~~

Expected: eight failures because resolver is absent.

- [ ] **Step 2: Add the exact tolerant ledger prefilters**

They use only tolerant key reads; strict validation remains in the domain
functions:

~~~python
def _prefilter_mto_capacity_rows(
    *,
    rows: list[dict[str, object]],
    allowed_keys: set[tuple[str, str, str]],
) -> list[dict[str, object]]:
    return [
        deepcopy(row)
        for row in rows
        if (
            str(row.get("ResourceID") or ""),
            str(row.get("WindowStartAt") or ""),
            str(row.get("WindowEndAt") or ""),
        ) in allowed_keys
    ]


def _prefilter_mto_material_rows(
    *,
    rows: list[dict[str, object]],
    allowed_keys: set[tuple[str, str]],
) -> list[dict[str, object]]:
    return [
        deepcopy(row)
        for row in rows
        if (
            str(row.get("ItemID") or ""),
            str(row.get("LocationID") or ""),
        ) in allowed_keys
    ]
~~~

- [ ] **Step 3: Install the complete state-to-evaluation resolver**

This is the entire body, including every return and fail-closed route/resource
branch. `_parse_aware` is the only parse name. In particular, it never reads
`routing.operations` until a unique route exists and never indexes a resource
dictionary before checking missing IDs.

~~~python
def _build_order_commitment_evaluation_from_state(
    *,
    endpoint: str,
    order: Mapping[str, object],
    evaluated_at: datetime,
    check_material_availability: bool,
    material_check_skip_reason: str | None,
    requested_operational_state_snapshot_id: str | None,
) -> dict[str, object] | JSONResponse:
    evaluated_at = _parse_aware(evaluated_at)
    run = planning_runs.get(str(order["BaselinePlanningRunID"]))
    if run is None:
        return _order_commitment_error(
            endpoint=endpoint,
            status_code=404,
            status="PlanningRunNotFound",
            message="Baseline Planning Run was not found.",
        )
    if run.get("Status") != "Completed":
        return _order_commitment_error(
            endpoint=endpoint,
            status_code=409,
            status="PlanningRunNotCompleted",
            message="Baseline Planning Run must be completed.",
        )
    if publication_state(run) not in {"Approved", "Published"}:
        return _order_commitment_error(
            endpoint=endpoint,
            status_code=409,
            status="PlanningRunNotApprovedOrPublished",
            message="Baseline plan must be approved or published.",
        )
    schedule = run.get("Schedule")
    if not isinstance(schedule, dict):
        return _order_commitment_error(
            endpoint=endpoint,
            status_code=409,
            status="PlanningRunScheduleMissing",
            message="Baseline schedule evidence is missing.",
        )
    master = master_data_versions.get(str(run.get("MasterDataVersionID")))
    if not isinstance(master, dict):
        return _order_commitment_error(
            endpoint=endpoint,
            status_code=404,
            status="MasterDataVersionNotFound",
            message="Baseline master-data version was not found.",
        )

    orchestration_issue: tuple[str, str] | None = None
    resources: list[Resource] = []
    routings: list[Routing] = []
    routing: Routing | None = None
    setup_transitions: list[SetupTransition] = []
    capacity_buckets = []
    timezone_name = master.get("CalendarTimezone")
    if not isinstance(timezone_name, str) or not timezone_name.strip():
        orchestration_issue = (
            "CALENDAR_TIMEZONE_REQUIRED",
            "A calendar timezone is required for MTO shadow capacity.",
        )
    try:
        resource_rows = master.get("Resources")
        routing_rows = master.get("Routings")
        if not isinstance(resource_rows, list) or not isinstance(
            routing_rows, list
        ):
            raise ValueError("Master resource/routing rows must be lists.")
        resources = _resources_from_payload([
            ResourcePayload(**row) for row in resource_rows
        ])
        resources = apply_base_calendar_assignments(
            resources=resources,
            calendars=run.get("FrozenBaseCalendars") or [],
            assignments=(
                run.get("FrozenResourceCalendarAssignments") or []
            ),
        ).resources
        resources = apply_calendar_overrides(
            resources=resources,
            overrides=run.get("FrozenCalendarOverrides") or [],
        ).resources
        routings = _routings_from_payload([
            RoutingPayload(**row) for row in routing_rows
        ])
        setup_rows = run.get("SetupTransitions") or []
        if not isinstance(setup_rows, list):
            raise ValueError("SetupTransitions must be a list.")
        setup_transitions = _setup_transitions_from_payload([
            SetupTransitionPayload(**row) for row in setup_rows
        ])
    except (KeyError, TypeError, ValueError) as error:
        orchestration_issue = (
            "MASTER_ROUTE_CALENDAR_EVIDENCE_INVALID",
            str(error),
        )

    if orchestration_issue is None:
        routing_matches = [
            row
            for row in routings
            if row.product_id == order["ProductID"]
            and row.routing_id == order["RoutingID"]
            and row.is_primary is True
        ]
        if len(routing_matches) != 1:
            orchestration_issue = (
                "ROUTING_NOT_PRIMARY_OR_AMBIGUOUS",
                "Exactly one matching primary route is required.",
            )
        else:
            routing = routing_matches[0]

    resources_by_id = {row.resource_id: row for row in resources}
    if orchestration_issue is None and routing is not None:
        missing_resource_ids = sorted({
            operation.resource_id
            for operation in routing.operations
            if operation.resource_id not in resources_by_id
        })
        if missing_resource_ids:
            orchestration_issue = (
                "ROUTE_RESOURCE_NOT_FOUND",
                "Route references missing resources: "
                + ", ".join(missing_resource_ids),
            )

    ccr_resource_ids: set[str] = set()
    if orchestration_issue is None and routing is not None:
        ccr_resource_ids = {
            operation.resource_id
            for operation in routing.operations
            if resources_by_id[operation.resource_id].is_constraint
        }
        if not ccr_resource_ids:
            orchestration_issue = (
                "CCR_OPERATION_NOT_FOUND",
                "The primary route has no CCR operation.",
            )

    if orchestration_issue is None:
        try:
            capacity_buckets = build_capacity_buckets_from_resources(
                resources,
                tzinfo=ZoneInfo(str(timezone_name)),
            )
        except (KeyError, TypeError, ValueError) as error:
            orchestration_issue = (
                "CALENDAR_CAPACITY_EVIDENCE_INVALID",
                str(error),
            )

    frozen_release_policy = _release_policy_for_evaluation(
        planning_run=run,
        requested_policy_id=None,
        dbr_release_policies=dbr_release_policies,
    )
    material_window = release_policy_settings(
        frozen_release_policy
    ).material_lookahead_minutes
    material_input_keys = {
        (str(row["ItemID"]), str(row["LocationID"]))
        for row in order["MaterialRequirements"]
    }
    capacity_input_keys = {
        (
            bucket.resource_id,
            bucket.bucket_start.astimezone(timezone.utc).isoformat(),
            bucket.bucket_end.astimezone(timezone.utc).isoformat(),
        )
        for bucket in capacity_buckets
        if bucket.resource_id in ccr_resource_ids
    }
    relevant_capacity_rows = _prefilter_mto_capacity_rows(
        rows=list(ccr_capacity_reservations.values()),
        allowed_keys=capacity_input_keys,
    )
    relevant_material_rows = _prefilter_mto_material_rows(
        rows=list(material_planning_allocations.values()),
        allowed_keys=material_input_keys,
    )
    raw_gantt_rows = schedule.get("GanttRows", [])
    if not isinstance(raw_gantt_rows, list):
        orchestration_issue = (
            "SCHEDULE_GANTT_EVIDENCE_INVALID",
            "Schedule GanttRows must be a list.",
        )
        raw_gantt_rows = []
    relevant_gantt_rows = [
        deepcopy(row)
        for row in raw_gantt_rows
        if isinstance(row, Mapping)
        and str(row.get("ResourceID") or "") in ccr_resource_ids
    ]

    try:
        selection = select_order_commitment_operational_snapshot(
            snapshots=operational_state_snapshots,
            evaluated_at=evaluated_at,
            requested_snapshot_id=(
                requested_operational_state_snapshot_id
            ),
        )
    except OrderCommitmentSnapshotNotFound as error:
        return _order_commitment_error(
            endpoint=endpoint,
            status_code=404,
            status=error.status,
            message=str(error),
            details={"OperationalStateSnapshotID": error.snapshot_id},
        )

    shadow = (
        _not_assessable_shadow(
            order=order,
            evaluated_at=evaluated_at,
            code=orchestration_issue[0],
            message=orchestration_issue[1],
        )
        if orchestration_issue is not None
        else evaluate_ccr_shadow_schedule(
            order_id=str(order["PlanningOrderID"]),
            quantity=float(order["Quantity"]),
            routing=routing,
            resources=resources,
            capacity_buckets=capacity_buckets,
            setup_transitions=setup_transitions,
            gantt_rows=relevant_gantt_rows,
            active_capacity_reservations=relevant_capacity_rows,
            requested_due_at=_parse_aware(order["RequestedDueAt"]),
            evaluated_at=evaluated_at,
            downstream_protection_minutes=int(
                run.get("TimeBufferMinutes", 0)
            ),
            protection_threshold_percent=80.0,
        )
    )
    try:
        material = evaluate_mto_material_availability(
            order=order,
            snapshot_selection=selection,
            active_material_allocations=relevant_material_rows,
            current_demand_commitment_id=(
                candidate_demand_commitment_id(order)
            ),
            evaluated_at=evaluated_at,
            material_check_window_minutes=material_window,
            check_material_availability=check_material_availability,
            skip_reason=material_check_skip_reason,
        )
    except OrderCommitmentConflict as error:
        return _order_commitment_error(
            endpoint=endpoint,
            status_code=409,
            status=error.status,
            message=str(error),
        )

    route_projection = (
        None
        if routing is None
        else {
            "ProductID": routing.product_id,
            "RoutingID": routing.routing_id,
            "IsPrimary": routing.is_primary,
            "Operations": [
                {
                    "OperationID": row.operation_id,
                    "ResourceID": row.resource_id,
                    "DurationMinutes": row.duration_minutes,
                    "Sequence": row.sequence,
                    "AlternateResourceIDs": sorted(
                        row.alternate_resource_ids or []
                    ),
                    "SetupFamily": row.setup_family,
                }
                for row in sorted(
                    routing.operations, key=lambda item: item.sequence
                )
            ],
        }
    )
    calendar_projection = {
        "CalendarTimezone": timezone_name,
        "CapacityBuckets": [
            {
                "ResourceID": row.resource_id,
                "WindowStartAt": row.bucket_start.astimezone(
                    timezone.utc
                ).isoformat(),
                "WindowEndAt": row.bucket_end.astimezone(
                    timezone.utc
                ).isoformat(),
                "CapacityMinutes": row.capacity_minutes,
            }
            for row in sorted(
                capacity_buckets,
                key=lambda item: (
                    item.resource_id,
                    item.bucket_start,
                    item.bucket_end,
                ),
            )
        ],
        "FrozenBaseCalendars": deepcopy(
            run.get("FrozenBaseCalendars") or []
        ),
        "FrozenResourceCalendarAssignments": deepcopy(
            run.get("FrozenResourceCalendarAssignments") or []
        ),
        "FrozenCalendarOverrides": deepcopy(
            run.get("FrozenCalendarOverrides") or []
        ),
    }
    selected_snapshot = selection["OperationalStateSnapshot"]
    inventory_rows = (
        list(selected_snapshot.inventory_buffers)
        if isinstance(selected_snapshot, OperationalStateSnapshot)
        else []
    )
    availability_rows = (
        list(selected_snapshot.material_availability)
        if isinstance(selected_snapshot, OperationalStateSnapshot)
        else []
    )
    material_cutoff_value = material["MaterialEligibilityCutoffAt"]
    try:
        basis = build_order_commitment_basis(
            baseline_planning_run_id=str(run["RunID"]),
            baseline_operational_state_snapshot_id=(
                str(run["OperationalStateSnapshotID"])
                if run.get("OperationalStateSnapshotID") is not None
                else None
            ),
            baseline_schedule_fingerprint=(
                planning_schedule_fingerprint(run)
                or canonical_fingerprint(schedule)
            ),
            master_data_version_id=str(master["VersionID"]),
            operating_model_configuration_id=run.get(
                "OperatingModelConfigurationID"
            ),
            operating_model_fingerprint=run.get(
                "OperatingModelFingerprint"
            ),
            scheduling_configuration_id=run.get(
                "SchedulingConfigurationID"
            ),
            ddmrp_configuration_id=run.get("DDMRPConfigurationID"),
            release_policy_version_id=run.get("ReleasePolicyVersionID"),
            frozen_release_policy_fingerprint=canonical_fingerprint(
                release_policy_evidence(frozen_release_policy)
            ),
            routing_fingerprint=canonical_fingerprint(route_projection),
            calendar_fingerprint=canonical_fingerprint(
                calendar_projection
            ),
            time_buffer_minutes=int(run.get("TimeBufferMinutes", 0)),
            material_check_window_minutes=material_window,
            capacity_assessment_cutoff_at=_parse_aware(
                shadow["CapacityAssessmentCutoffAt"]
            ),
            material_eligibility_cutoff_at=(
                _parse_aware(material_cutoff_value)
                if material_cutoff_value is not None
                else None
            ),
            check_material_availability=check_material_availability,
            material_skip_reason=material_check_skip_reason,
            snapshot_selection=selection,
            relevant_capacity_window_keys=[
                tuple(row) for row in shadow["RelevantCapacityWindowKeys"]
            ],
            capacity_ledger_rows=relevant_capacity_rows,
            relevant_material_keys=sorted(material_input_keys),
            inventory_buffer_rows=inventory_rows,
            material_availability_rows=availability_rows,
            material_ledger_rows=relevant_material_rows,
        )
        return create_order_commitment_evaluation(
            order=order,
            shadow_schedule=shadow,
            material_assessment=material,
            basis=basis,
            protection_policy=REFERENCE_CCR_PROTECTION_POLICY,
            evaluated_at=evaluated_at,
        )
    except OrderCommitmentConflict as error:
        return _order_commitment_error(
            endpoint=endpoint,
            status_code=409,
            status=error.status,
            message=str(error),
        )
~~~

- [ ] **Step 4: Verify and commit**

~~~powershell
pytest tests/test_order_commitment_api.py::TestOrderCommitmentApiOrchestration --collect-only -q
pytest tests/test_order_commitment_api.py::TestOrderCommitmentApiOrchestration -q --basetemp .tmp/pytest-mto-orchestration-green -p no:cacheprovider
git add -- sdbr/api.py tests/test_order_commitment_api.py
git commit -m "feat: orchestrate MTO commitment evidence"
~~~

Expected: eight resolver tests pass.

---

### Task 17: Idempotent Intake and Sanitized Reads

**Files and anchors**
- Modify `sdbr/api.py` inside `create_app`; add the intake/read routes once (Task 15 created no route or stub).
- Modify `tests/test_order_commitment_api.py` after orchestration tests.

**IDs:** `BE-SDBR-010`.

- [ ] **Step 1: Write intake/read tests**

Add `TestOrderCommitmentApiIntakeAndReads`:

- `test_intake_automatically_evaluates_with_material_check_enabled`;
- `test_duplicate_intake_returns_same_evaluation_and_one_event`;
- `test_intake_with_stale_evidence_has_no_acceptance_action`;
- `test_intake_malformed_route_persists_do_not_recommend_with_issue`;
- `test_workbench_and_detail_return_exact_sanitized_contract_and_revision`;
- `test_unknown_detail_returns_order_commitment_not_found`;
- `test_intake_creates_no_phase0_or_planning_run_objects`.
- `test_v1_to_v2_intake_atomically_supersedes_v1_and_old_row_has_no_actions`;
- `test_decision_against_superseded_v1_is_rejected`;
- `test_concurrent_v1_v2_intake_leaves_only_greatest_rank_open`;
- `test_new_version_after_rejected_is_allowed_but_after_accepted_requires_amendment`.

~~~powershell
pytest tests/test_order_commitment_api.py::TestOrderCommitmentApiIntakeAndReads -q --basetemp .tmp/pytest-mto-intake-red -p no:cacheprovider
~~~

Expected: the named tests fail because real routes are absent.

- [ ] **Step 2: Add stable safe event append**

Use one sanitizer and one boundary helper for every response:

~~~python
def _order_commitment_row(
    evaluation: Mapping[str, object],
) -> dict[str, object]:
    workbench = build_order_commitment_workbench(
        evaluations=[deepcopy(dict(evaluation))],
        demand_commitments=planning_demand_commitments,
        reservation_batches=planning_reservation_batches,
    )
    return deepcopy(workbench["Rows"][0])

def _order_commitment_boundary() -> dict[str, object]:
    return {
        "RecommendationOnly": True,
        "ExternalOrderAcceptance": "NotPerformed",
        "PlanningRunCreation": "NotPerformed",
        "ProductionMutation": "NotPerformed",
        "ReleaseMaterialGateStillRequired": True,
    }
~~~

~~~python
def _append_order_commitment_event(
    *,
    evaluation,
    event_type,
    actor_id,
    occurred_at,
    decision_id=None,
    reservation_batch_id=None,
    causation_id,
    details,
):
    safe_details = {
        key: deepcopy(value)
        for key, value in details.items()
        if key in INTERNAL_ORDER_COMMITMENT_EVENT_DETAIL_FIELDS
    }
    identity = {
        "EvaluationID": evaluation["EvaluationID"],
        "EventType": event_type,
        "DecisionID": decision_id,
        "ReservationBatchID": reservation_batch_id,
        "CausationID": causation_id,
    }
    event = {
        "EventID": "OCEV-" + sha256(
            canonical_json(identity).encode("utf-8")
        ).hexdigest()[:20],
        "EventType": event_type,
        "EvaluationID": evaluation["EvaluationID"],
        "OccurredAt": occurred_at.isoformat(),
        "ActorID": actor_id,
        "TraceID": evaluation["Order"]["TraceID"],
        "CausationID": causation_id,
        "CorrelationID": evaluation["Order"]["LogicalOrderKey"],
        "DecisionID": decision_id,
        "ReservationBatchID": reservation_batch_id,
        "Details": safe_details,
    }
    existing = next(
        (
            row for row in order_commitment_events
            if row.get("EventID") == event["EventID"]
        ),
        None,
    )
    if existing is None:
        order_commitment_events.append(event)
    elif canonical_fingerprint(existing) != canonical_fingerprint(event):
        raise OrderCommitmentConflict(
            "Order commitment event identity/content conflict."
        )
    return event
~~~

Allowed internal detail fields are exactly the `SAFE_AUDIT_DETAIL_FIELDS` set; event metadata remains internal and is sanitized by Task 13.

- [ ] **Step 3: Implement intake**

~~~python
@app.post("/planner/workbench/order-commitments/intake")
def planner_workbench_order_commitment_intake(
    payload: MtoOrderCommitmentIntakePayload,
    request: Request,
):
    endpoint = "/planner/workbench/order-commitments/intake"
    order = normalize_mto_order(_mto_order_from_payload(payload))
    try:
        replay = exact_order_commitment_intake_replay(
            evaluations=order_commitment_evaluations,
            order=order,
        )
    except OrderCommitmentConflict as error:
        return _order_commitment_error(
            endpoint=endpoint,
            status_code=409,
            status=str(error),
            message=str(error),
        )
    if replay is not None:
        return {
            "Endpoint": endpoint,
            "StatusCode": 200,
            "Data": {
                "RegistrationStatus": "Duplicate",
                "Evaluation": _order_commitment_row(replay),
                "Boundary": _order_commitment_boundary(),
            },
        }
    evaluated_at = server_utc_now()
    actor_id = _effective_actor_id(request, order["SourceSystem"])
    candidate = _build_order_commitment_evaluation_from_state(
        endpoint=endpoint,
        order=order,
        evaluated_at=evaluated_at,
        check_material_availability=True,
        material_check_skip_reason=None,
        requested_operational_state_snapshot_id=(
            payload.OperationalStateSnapshotID
        ),
    )
    if isinstance(candidate, JSONResponse):
        return candidate
    registration, persisted = register_order_commitment_evaluation(
        order_commitment_evaluations, candidate
    )
    if registration == "Created":
        superseded = supersede_open_order_commitment_evaluations(
            evaluations=order_commitment_evaluations,
            candidate=persisted,
            superseded_at=evaluated_at,
        )
        for superseded_id, superseded_row in superseded.items():
            order_commitment_evaluations[superseded_id] = deepcopy(
                superseded_row
            )
            _append_order_commitment_event(
                evaluation=superseded_row,
                event_type="OrderCommitmentEvaluationSuperseded",
                actor_id=actor_id,
                occurred_at=evaluated_at,
                causation_id=persisted["EvaluationID"],
                details={
                    "FromStatus": "AwaitingPlannerDecision",
                    "ToStatus": "Superseded",
                    "SupersededByEvaluationID": persisted[
                        "EvaluationID"
                    ],
                },
            )
        order_commitment_evaluations[persisted["EvaluationID"]] = deepcopy(
            persisted
        )
        _append_order_commitment_event(
            evaluation=persisted,
            event_type="OrderCommitmentEvaluated",
            actor_id=actor_id,
            occurred_at=evaluated_at,
            causation_id=persisted["Order"]["OrderKey"],
            details={
                "ToStatus": "AwaitingPlannerDecision",
                "Recommendation": persisted["Recommendation"]["Decision"],
                "MaterialCheckEnabled": True,
                "MaterialEvidenceFreshnessStatus": persisted[
                    "MaterialAssessment"
                ]["OperationalStateFreshnessStatus"],
            },
        )
    return {
        "Endpoint": endpoint,
        "StatusCode": 200,
        "Data": {
            "RegistrationStatus": registration,
            "Evaluation": _order_commitment_row(persisted),
            "Boundary": _order_commitment_boundary(),
        },
    }
~~~

Do not call `server_utc_now()` twice. Duplicate registration writes nothing and appends no event.

- [ ] **Step 4: Implement GET endpoints**

Workbench passes copied evaluations/demands/batches to `build_order_commitment_workbench`. Detail resolves decision-linked demand/batch and matching events, then calls `build_order_commitment_detail`. Return `404 OrderCommitmentEvaluationNotFound` for an unknown ID. Existing middleware captures body and `X-Workbench-Revision` under one state admission; add no extra lock.

- [ ] **Step 5: Verify and commit in two slices**

Slice A is exact replay plus sanitized reads. Slice B is v1-to-v2 supersession, terminal behavior, old-decision rejection, and concurrency. Each slice has its own RED command, focused green command, and commit; do not combine all intake/read behavior behind one import failure.

~~~powershell
pytest tests/test_order_commitment_api.py::TestOrderCommitmentApiIntakeAndReads --collect-only -q
pytest tests/test_order_commitment_api.py::TestOrderCommitmentApiIntakeAndReads tests/test_order_commitment_view.py -q --basetemp .tmp/pytest-mto-intake-green -p no:cacheprovider
git add -- sdbr/api.py tests/test_order_commitment_api.py
git commit -m "feat: add recommendation-only MTO intake"
~~~

Expected: seven API tests and view tests pass.

---

### Task 18: Audited Re-evaluation with Current Evidence

**Files and anchors**
- Modify `sdbr/api.py` inside `create_app`; add the re-evaluation route once (there is no interim stub).
- Modify `tests/test_order_commitment_api.py` after intake/read tests.

**IDs:** `BE-SDBR-010`.

- [ ] **Step 1: Write re-evaluation tests**

Add `TestOrderCommitmentApiReevaluation`:

- `test_reevaluation_defaults_material_check_on_and_selects_new_latest_snapshot`;
- `test_explicit_stale_or_future_snapshot_persists_insufficient_evidence`;
- `test_material_opt_out_requires_reason_and_has_no_allocations`;
- `test_reevaluation_payload_cannot_override_material_window`;
- `test_new_evaluation_supersedes_only_open_source_and_preserves_events`;
- `test_unchanged_replay_returns_duplicate_without_second_event`;
- `test_terminal_or_superseded_source_has_no_reevaluation`;
- `test_reevaluation_creates_no_phase0_or_planning_run_objects`.

~~~powershell
pytest tests/test_order_commitment_api.py::TestOrderCommitmentApiReevaluation -q --basetemp .tmp/pytest-mto-reevaluation-red -p no:cacheprovider
~~~

Expected: eight failures because route is absent.

- [ ] **Step 2: Implement exact re-evaluation transaction**

The following block is the body of this exact route; indent it one level beneath the signature so `evaluation_id`, `payload`, `request`, and `endpoint` are bound:

~~~python
@app.post(
    "/planner/workbench/order-commitments/{evaluation_id}/reevaluate"
)
def planner_workbench_order_commitment_reevaluate(
    evaluation_id: str,
    payload: MtoOrderCommitmentReevaluationPayload,
    request: Request,
):
    endpoint = (
        "/planner/workbench/order-commitments/"
        f"{evaluation_id}/reevaluate"
    )
    # Insert the exact body immediately below at this indentation.
~~~

~~~python
source = order_commitment_evaluations.get(evaluation_id)
if source is None:
    return _order_commitment_error(
        endpoint=endpoint, status_code=404,
        status="OrderCommitmentEvaluationNotFound",
        message="Order commitment evaluation was not found.",
    )
if source["Status"] != "AwaitingPlannerDecision":
    return _order_commitment_error(
        endpoint=endpoint, status_code=409,
        status="OrderCommitmentEvaluationNotReevaluatable",
        message="Only an open evaluation may be re-evaluated.",
    )
observed_at = server_utc_now()
actor_id = _effective_actor_id(request, payload.RequestedBy)
order = deepcopy(source["Order"])
if payload.BaselinePlanningRunID is not None:
    order["BaselinePlanningRunID"] = (
        payload.BaselinePlanningRunID.strip()
    )
order = normalize_mto_order(order)
candidate = _build_order_commitment_evaluation_from_state(
    endpoint=endpoint,
    order=order,
    evaluated_at=observed_at,
    check_material_availability=payload.CheckMaterialAvailability,
    material_check_skip_reason=payload.MaterialCheckSkipReason,
    requested_operational_state_snapshot_id=(
        payload.OperationalStateSnapshotID
    ),
)
if isinstance(candidate, JSONResponse):
    return candidate
registration, persisted = register_order_commitment_evaluation(
    order_commitment_evaluations, candidate
)
if registration == "Duplicate":
    return {
        "Endpoint": endpoint,
        "StatusCode": 200,
        "Data": {
            "RegistrationStatus": "Duplicate",
            "Evaluation": _order_commitment_row(persisted),
            "Boundary": _order_commitment_boundary(),
        },
    }
updates = supersede_open_order_commitment_evaluations(
    evaluations=order_commitment_evaluations,
    candidate=persisted,
    superseded_at=observed_at,
)
for updated_id, updated_row in updates.items():
    order_commitment_evaluations[updated_id] = deepcopy(updated_row)
    _append_order_commitment_event(
        evaluation=updated_row,
        event_type="OrderCommitmentEvaluationSuperseded",
        actor_id=actor_id,
        occurred_at=observed_at,
        causation_id=persisted["EvaluationID"],
        details={
            "FromStatus": "AwaitingPlannerDecision",
            "ToStatus": "Superseded",
            "SupersededByEvaluationID": persisted["EvaluationID"],
        },
    )
order_commitment_evaluations[persisted["EvaluationID"]] = deepcopy(
    persisted
)
_append_order_commitment_event(
    evaluation=persisted,
    event_type="OrderCommitmentReevaluated",
    actor_id=actor_id,
    occurred_at=observed_at,
    causation_id=source["EvaluationID"],
    details={
        "ToStatus": "AwaitingPlannerDecision",
        "Recommendation": persisted["Recommendation"]["Decision"],
        "MaterialCheckEnabled": persisted["MaterialAssessment"][
            "CheckEnabled"
        ],
        "MaterialEvidenceFreshnessStatus": persisted[
            "MaterialAssessment"
        ]["OperationalStateFreshnessStatus"],
    },
)
~~~

Both events use `observed_at` and `actor_id` captured once. Event details are limited to from/to status, superseding ID, recommendation, material-check enabled, and freshness status. There is no material-window request field; `_build_order_commitment_evaluation_from_state` resolves it from the selected baseline's frozen policy.

- [ ] **Step 3: Verify and commit**

~~~powershell
pytest tests/test_order_commitment_api.py::TestOrderCommitmentApiReevaluation --collect-only -q
pytest tests/test_order_commitment_api.py::TestOrderCommitmentApiReevaluation -q --basetemp .tmp/pytest-mto-reevaluation-green -p no:cacheprovider
git add -- sdbr/api.py tests/test_order_commitment_api.py
git commit -m "feat: re-evaluate MTO commitment evidence"
~~~

Expected: eight tests pass.

---

### Task 19: Decision Preconditions, Rejection, and Exact Replay

**Files and anchors**
- Modify `sdbr/planning_reservations.py`; expose the existing idempotent replay
  verifier without widening its lifecycle-field allowlist.
- Modify `sdbr/api.py` inside `create_app`; begin real decision route.
- Modify `tests/test_planning_reservations.py` after the existing replay tests.
- Modify `tests/test_order_commitment_api.py` after re-evaluation tests.

**IDs:** `BE-SDBR-010`.

- [ ] **Step 1: Write precondition/replay tests**

Add `TestOrderCommitmentApiDecisionReplay`:

- `test_decision_requires_if_match_and_exact_evaluation_fingerprint`;
- `test_reject_records_server_actor_and_time_without_phase0_rows`;
- `test_exact_reject_replay_returns_same_record_without_duplicate_event`;
- `test_exact_accepted_replay_returns_same_verified_phase0_result`;
- `test_exact_accepted_replay_rejects_one_field_phase0_corruption`;
- `test_same_decision_id_one_field_at_a_time_change_conflicts`;
- `test_terminal_row_rejects_new_decision_id`;
- `test_decision_event_and_record_share_one_server_time_and_actor`.

Parameterize the one-field test over decision code, expected fingerprint, effective actor header, trimmed reason, CCR acknowledgement, and material acknowledgement.

Parameterize `test_exact_accepted_replay_rejects_one_field_phase0_corruption`
over these independent mutations, restoring a fresh accepted fixture for every
case: demand `Quantity`; batch `ConfirmedBy`; capacity `ReservedMinutes`;
material `AllocatedQty`; planning-reservation event `PayloadFingerprint`;
planning-reservation event `Result.ReservationBatchID`; event `ActorID`; event
`OccurredAt`; event `DemandCommitmentID`; batch `DemandCommitmentID`; one batch
`CapacityReservationIDs` entry; and one batch `MaterialAllocationIDs` entry.
Assert `409
OrderCommitmentDecisionReplayEvidenceMismatch`, the complete public store equals
its pre-request deep copy, and no event or processed key is added. The normal
exact replay test must also advance demand/batch/capacity/material through the
documented Planning Run lifecycle and prove replay still succeeds; no status,
version, Planning Run provenance, or material-authority handoff exception may be
defined in the API.

~~~powershell
pytest tests/test_order_commitment_api.py::TestOrderCommitmentApiDecisionReplay -q --basetemp .tmp/pytest-mto-decision-replay-red -p no:cacheprovider
~~~

Expected: eight logical tests fail because decision route and shared replay
entry point are incomplete.

- [ ] **Step 2: Enforce preconditions and one captured decision observation**

~~~python
if request.headers.get("if-match") is None:
    return JSONResponse(
        status_code=428,
        content={
            "Endpoint": endpoint,
            "StatusCode": 428,
            "Data": {
                "Status": "OrderCommitmentPreconditionRequired"
            },
        },
    )
evaluation = order_commitment_evaluations.get(evaluation_id)
if evaluation is None:
    return _order_commitment_error(
        endpoint=endpoint, status_code=404,
        status="OrderCommitmentEvaluationNotFound",
        message="Order commitment evaluation was not found.",
    )
if payload.ExpectedEvaluationFingerprint != evaluation[
    "EvaluationFingerprint"
]:
    return _order_commitment_error(
        endpoint=endpoint, status_code=409,
        status="OrderCommitmentEvaluationFingerprintMismatch",
        message="Expected evaluation fingerprint does not match.",
    )
decision_at = server_utc_now()
actor_id = _effective_actor_id(request, payload.DecidedBy)
incoming_fingerprint = canonical_decision_fingerprint(
    evaluation=evaluation,
    decision_id=payload.DecisionID,
    decision=payload.Decision,
    actor_id=actor_id,
    reason=payload.Reason,
    ccr_risk_acknowledged=payload.CcrRiskAcknowledged,
    material_risk_acknowledged=payload.MaterialRiskAcknowledged,
)
~~~

Existing middleware handles numeric revision mismatch before route code. Do not reread/retry.

- [ ] **Step 3: Expose the Phase 0 verifier and implement exact terminal replay and rejection**

In `planning_reservations.py`, rename
`_assert_idempotent_replay_matches` to
`assert_reservation_write_set_replay_matches`, add
`processed_event_keys: MutableSet[str]` to its parameters, and move the
processed-key membership check into that function before its existing unique
event lookup. Keep `_REPLAY_TRANSITION_FIELDS`, all allowed status sets, the
newer-`RecordVersion` requirement, and the narrowly defined material-authority
handoff exactly as implemented. Keep the existing canonical demand
normalization, immutable-content comparisons, child lookup, event
`PayloadFingerprint`, and event `Result` checks unchanged, and additionally
require the one persisted event to equal the canonical write-set event in every
field. Events have no mutable replay fields; this comparison therefore verifies
event ID/type, demand/batch linkage, actor/time/trace provenance, idempotency
key, payload fingerprint, and result together. Change
`apply_reservation_write_set` to call this public verifier for the processed-key
branch. Add one direct Phase 0 test proving the public verifier accepts a deep
copy of a valid evolved ledger and does not mutate any supplied collection.

For terminal status:

~~~python
if evaluation["Status"] == "Superseded":
    return _order_commitment_error(
        endpoint=endpoint,
        status_code=409,
        status="OrderCommitmentEvaluationNotDecisionEligible",
        message="Superseded evaluation cannot receive a decision.",
    )
persisted_decision = evaluation.get("Decision")
if not isinstance(persisted_decision, dict):
    return _order_commitment_error(
        endpoint=endpoint, status_code=409,
        status="OrderCommitmentDecisionEvidenceMissing",
        message="Persisted decision evidence is missing.",
    )
if persisted_decision["DecisionFingerprint"] != incoming_fingerprint:
    return _order_commitment_error(
        endpoint=endpoint, status_code=409,
        status="OrderCommitmentDecisionReplayConflict",
        message="Decision replay content differs from persisted content.",
    )
if evaluation["Status"] == "AcceptedPendingFormalSchedule":
    original = deepcopy(evaluation)
    original["Status"] = "AwaitingPlannerDecision"
    original["RecordVersion"] = int(evaluation["RecordVersion"]) - 1
    original.pop("Decision", None)
    try:
        original_write_set = prepare_mto_acceptance(
            evaluation=original,
            existing_commitments={},
            decision_id=str(persisted_decision["DecisionID"]),
            decision=str(persisted_decision["Decision"]),
            decided_by=str(persisted_decision["DecidedBy"]),
            decided_at=_parse_aware(persisted_decision["DecidedAt"]),
            reason=str(persisted_decision["Reason"]),
            ccr_risk_acknowledged=bool(
                persisted_decision["CcrRiskAcknowledged"]
            ),
            material_risk_acknowledged=bool(
                persisted_decision["MaterialRiskAcknowledged"]
            ),
        )
        assert_reservation_write_set_replay_matches(
            write_set=original_write_set,
            commitments=deepcopy(planning_demand_commitments),
            batches=deepcopy(planning_reservation_batches),
            capacity_reservations=deepcopy(ccr_capacity_reservations),
            material_allocations=deepcopy(material_planning_allocations),
            events=deepcopy(planning_reservation_events),
            processed_event_keys=deepcopy(
                processed_planning_event_keys
            ),
        )
    except ReservationConflict:
        return _order_commitment_error(
            endpoint=endpoint, status_code=409,
            status="OrderCommitmentDecisionReplayEvidenceMismatch",
            message=(
                "Persisted acceptance does not match its canonical "
                "Phase 0 write set."
            ),
        )
return {
    "Endpoint": endpoint,
    "StatusCode": 200,
    "Data": {
        "Evaluation": _order_commitment_row(evaluation),
        "Status": evaluation["Status"],
        "DemandCommitmentID": persisted_decision.get(
            "DemandCommitmentID"
        ),
        "ReservationBatchID": persisted_decision.get(
            "ReservationBatchID"
        ),
        "ExternalOrderAcceptance": "NotPerformed",
        "PlanningRunCreation": "NotPerformed",
        "ProductionMutation": "NotPerformed",
    },
}
~~~

For new `Reject`:

~~~python
updated = rejected_evaluation_record(
    evaluation=evaluation,
    decision_id=payload.DecisionID,
    decision="Reject",
    decided_by=actor_id,
    decided_at=decision_at,
    reason=payload.Reason,
    ccr_risk_acknowledged=payload.CcrRiskAcknowledged,
    material_risk_acknowledged=payload.MaterialRiskAcknowledged,
)
order_commitment_evaluations[evaluation_id] = updated
_append_order_commitment_event(
    evaluation=updated,
    event_type="OrderCommitmentRejected",
    actor_id=actor_id,
    occurred_at=decision_at,
    decision_id=payload.DecisionID.strip(),
    causation_id=payload.DecisionID.strip(),
    details={
        "FromStatus": "AwaitingPlannerDecision",
        "ToStatus": "Rejected",
        "DecisionCode": "Reject",
        "CcrRiskAcknowledged": payload.CcrRiskAcknowledged,
        "MaterialRiskAcknowledged": payload.MaterialRiskAcknowledged,
    },
)
~~~

Rejection creates no shared demand/reservation or external state.

- [ ] **Step 4: Verify and commit**

~~~powershell
pytest tests/test_order_commitment_api.py::TestOrderCommitmentApiDecisionReplay --collect-only -q
pytest tests/test_planning_reservations.py tests/test_order_commitment_api.py::TestOrderCommitmentApiDecisionReplay -q --basetemp .tmp/pytest-mto-decision-replay-green -p no:cacheprovider
git add -- sdbr/planning_reservations.py sdbr/api.py tests/test_planning_reservations.py tests/test_order_commitment_api.py
git commit -m "feat: record replay-safe MTO decisions"
~~~

Expected: exact replay is stable across only the Phase 0 verifier's documented
monotonic lifecycle changes; every one-field content, provenance, event, result,
or ID-linkage corruption returns 409 without mutating state.

---

### Task 20: Relevant-State Staleness Gate

**Files and anchors**
- Modify `sdbr/api.py` in the acceptance branch of the decision route.
- Modify `tests/test_order_commitment_api.py` after replay tests.

**IDs:** `BE-SDBR-008` through `BE-SDBR-010`.

- [ ] **Step 1: Write exact relevant/unrelated change tests**

Add `TestOrderCommitmentApiStaleness`:

- `test_exact_assessed_0800_1600_capacity_change_marks_evaluation_stale`;
- `test_same_resource_different_window_does_not_mark_evaluation_stale`;
- `test_unrelated_resource_change_does_not_mark_evaluation_stale`;
- `test_relevant_requirement_item_location_change_marks_stale`;
- `test_unrelated_item_location_change_remains_eligible_after_revision_refresh`;
- `test_new_latest_snapshot_marks_latest-mode_evaluation_stale`;
- `test_explicit_snapshot_remains_selected_until_its_freshness_changes`;
- `test_fresh_to_stale_time_boundary_blocks_acceptance`.
- `test_time_advance_inside_selected_window_changes_current_capacity_facts`;
- `test_later_safe_window_and_promise_change_without_ledger_mutation_marks_stale`;
- `test_inbound_eligibility_cutoff_crossing_inside_fresh_snapshot_marks_stale`;
- `test_unchanged_canonical_decision_facts_allow_acceptance_despite_later_observation`.

For every capacity mutation, first read `evaluation["DecisionFacts"]["CapacityReservationRequests"][0]` and copy its exact `ResourceID`, `WindowStartAt`, and `WindowEndAt`; assert those values are `TST-MTO-CCR-1`, `08:00`, and `16:00` in the seeded fixture before mutating. For unrelated tests, mutate/save store, fetch the current revision, and submit that current revision. This isolates business staleness from global revision staleness.

~~~powershell
pytest tests/test_order_commitment_api.py::TestOrderCommitmentApiStaleness -q --basetemp .tmp/pytest-mto-stale-red -p no:cacheprovider
~~~

Expected: the named tests fail because acceptance does not compare current decision facts.

- [ ] **Step 2: Rebuild the exact persisted policy before any mutation**

~~~python
material = evaluation["MaterialAssessment"]
requested_snapshot_id = (
    material.get("RequestedOperationalStateSnapshotID")
    if material["SnapshotSelectionMode"] == "Explicit"
    else None
)
current = _build_order_commitment_evaluation_from_state(
    endpoint=endpoint,
    order=evaluation["Order"],
    evaluated_at=decision_at,
    check_material_availability=material["CheckEnabled"],
    material_check_skip_reason=material.get("SkipReason"),
    requested_operational_state_snapshot_id=requested_snapshot_id,
)
if isinstance(current, JSONResponse):
    return current
current_facts = canonical_order_commitment_decision_facts(current)
persisted_facts = evaluation["DecisionFacts"]
stale = any((
    current["DecisionStalenessBasisFingerprint"]
    != evaluation["DecisionStalenessBasisFingerprint"],
    current_facts != persisted_facts,
    canonical_fingerprint(current_facts)
    != evaluation["DecisionFactsFingerprint"],
    current["OrderContentFingerprint"] != evaluation[
        "OrderContentFingerprint"
    ],
    current["ProtectionPolicy"] != evaluation["ProtectionPolicy"],
    current["ShadowSchedule"]["Algorithm"] != evaluation[
        "ShadowSchedule"
    ]["Algorithm"],
    current["MaterialAssessment"]["CheckEnabled"] != material[
        "CheckEnabled"
    ],
    current["MaterialAssessment"].get("SkipReason") != material.get(
        "SkipReason"
    ),
))
if stale:
    return JSONResponse(
        status_code=409,
        content={
            "Endpoint": endpoint,
            "StatusCode": 409,
            "Data": {
                "Status": "OrderCommitmentEvaluationStale",
                "EvaluationID": evaluation_id,
                "Message": (
                    "Relevant capacity, material, schedule, calendar, "
                    "configuration, release, or snapshot evidence changed."
                ),
            },
        },
    )
~~~

Do not compare `EvaluationID`, `AuditBasisFingerprint`, or the new cutoff timestamps directly: time is allowed to advance when canonical decision facts remain identical. Do not modify the old row on a stale request. Middleware rollback preserves all state. Only explicit re-evaluation creates/supersedes evidence.

- [ ] **Step 3: Verify and commit in two slices**

Slice A covers stable/relevant evidence fingerprints. Slice B covers the four time-dependent canonical-fact tests. Each gets a focused RED/GREEN/commit cycle before the complete class run.

~~~powershell
pytest tests/test_order_commitment_api.py::TestOrderCommitmentApiStaleness --collect-only -q
pytest tests/test_order_commitment_api.py::TestOrderCommitmentApiStaleness -q --basetemp .tmp/pytest-mto-stale-green -p no:cacheprovider
git add -- sdbr/api.py tests/test_order_commitment_api.py
git commit -m "feat: reject stale MTO commitment decisions"
~~~

Expected: only exact relevant state invalidates an evaluation.

---

### Task 21: Atomic Option-2 Acceptance and Deep Authority Boundaries

**Files and anchors**
- Modify `sdbr/api.py` in the acceptance branch and `planning_reservation_workbench`.
- Modify `tests/test_order_commitment_api.py` after staleness tests.

**IDs:** `BE-SDBR-006` through `BE-SDBR-010`.

- [ ] **Step 1: Write atomicity, concurrency, and authority tests**

Add this exact test helper:

~~~python
from dataclasses import fields


PUBLIC_STORE_FIELDS = tuple(
    item.name
    for item in fields(WorkbenchStateStore)
    if not item.name.startswith("_")
)
MTO_FIELDS = {
    "order_commitment_evaluations",
    "order_commitment_events",
    "revision",
}
PHASE0_FIELDS = {
    "planning_demand_commitments",
    "planning_reservation_batches",
    "ccr_capacity_reservations",
    "material_planning_allocations",
    "planning_reservation_events",
    "processed_planning_event_keys",
}
ALLOWED_STORE_CHANGES = {
    "intake": MTO_FIELDS,
    "reevaluate": MTO_FIELDS,
    "reject": MTO_FIELDS,
    "accept": MTO_FIELDS | PHASE0_FIELDS,
}


def _public_store_snapshot(store: WorkbenchStateStore):
    return {
        name: deepcopy(getattr(store, name))
        for name in PUBLIC_STORE_FIELDS
    }


def _assert_only_operation_fields_changed(
    *,
    before: dict[str, object],
    after: dict[str, object],
    operation: str,
) -> None:
    assert set(before) == set(PUBLIC_STORE_FIELDS) == set(after)
    allowed = ALLOWED_STORE_CHANGES[operation]
    for name in PUBLIC_STORE_FIELDS:
        if name not in allowed:
            assert after[name] == before[name], name
~~~

Add `TestOrderCommitmentApiAcceptance`:

- `test_acceptance_atomically_creates_only_mto_phase0_rows`;
- `test_conditional_recommended_date_creates_pending_material_and_zero_allocations`;
- `test_decision_record_phase0_event_and_mto_event_share_server_actor_and_time`;
- `test_acceptance_response_is_accepted_pending_formal_schedule_and_not_performed_boundaries`;
- `test_acceptance_creates_no_planning_run_and_does_not_change_existing_publication`;
- `test_intake_reevaluation_rejection_and_acceptance_deep_preserve_authority_state`;
- `test_two_clients_one_revision_yield_one_success_one_revision_conflict`;
- `test_forced_save_failure_restores_all_mto_phase0_event_key_and_revision_state`;
- `test_phase0_shared_read_row_exposes_only_evaluation_promise_and_material_status`;
- `test_viewer_worker_forbidden_and_planner_admin_allowed_to_accept`.

The deep test snapshots before each of the four operations and calls `_assert_only_operation_fields_changed`. Because it derives from every public `WorkbenchStateStore` dataclass field, it covers current operational snapshots, release policies, calendars/assignments/overrides, scheduling strategies, all DDMRP inputs, Simio state, test-case state, external-authority ledgers, and future public fields automatically. A newly added field fails the equality assertion until its operation-specific authority is explicitly reviewed.

~~~powershell
pytest tests/test_order_commitment_api.py::TestOrderCommitmentApiAcceptance -q --basetemp .tmp/pytest-mto-acceptance-api-red -p no:cacheprovider
~~~

Expected: ten failures because acceptance write is absent.

- [ ] **Step 2: Apply one write set with one actor/time**

~~~python
write_set = prepare_mto_acceptance(
    evaluation=evaluation,
    existing_commitments=planning_demand_commitments,
    decision_id=payload.DecisionID,
    decision=payload.Decision,
    decided_by=actor_id,
    decided_at=decision_at,
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
    decided_by=actor_id,
    decided_at=decision_at,
    reason=payload.Reason,
    ccr_risk_acknowledged=payload.CcrRiskAcknowledged,
    material_risk_acknowledged=payload.MaterialRiskAcknowledged,
)
order_commitment_evaluations[evaluation_id] = updated
_append_order_commitment_event(
    evaluation=updated,
    event_type="OrderCommitmentAccepted",
    actor_id=actor_id,
    occurred_at=decision_at,
    decision_id=payload.DecisionID.strip(),
    reservation_batch_id=write_set.batch["ReservationBatchID"],
    causation_id=payload.DecisionID.strip(),
    details={
        "FromStatus": "AwaitingPlannerDecision",
        "ToStatus": "AcceptedPendingFormalSchedule",
        "DecisionCode": payload.Decision,
        "AcceptedPromiseAt": updated["Decision"]["AcceptedPromiseAt"],
        "CcrRiskAcknowledged": payload.CcrRiskAcknowledged,
        "MaterialRiskAcknowledged": payload.MaterialRiskAcknowledged,
    },
)
~~~

Map domain errors by `.status` to 409. Do not add nested `atomic_update`; `persist_successful_writes` already holds the state admission, snapshots complete state, saves once, and restores on error.

Return:

~~~python
{
    "Endpoint": endpoint,
    "StatusCode": 200,
    "Data": {
        "Evaluation": _order_commitment_row(updated),
        "DemandCommitmentID": write_set.demand_commitment[
            "DemandCommitmentID"
        ],
        "ReservationBatchID": write_set.batch["ReservationBatchID"],
        "CapacityReservationIDs": list(
            write_set.batch["CapacityReservationIDs"]
        ),
        "MaterialAllocationIDs": list(
            write_set.batch["MaterialAllocationIDs"]
        ),
        "Status": "AcceptedPendingFormalSchedule",
        "ExternalOrderAcceptance": "NotPerformed",
        "PlanningRunCreation": "NotPerformed",
        "ProductionMutation": "NotPerformed",
    },
}
~~~

- [ ] **Step 3: Extend only the shared sanitized reservation row**

At `planning_reservation_workbench`, when a batch resolves its demand, add:

~~~python
{
    "OrderCommitmentEvaluationID": demand.get(
        "OrderCommitmentEvaluationID"
    ),
    "AcceptedPromiseAt": demand.get("AcceptedPromiseAt"),
    "MaterialCommitmentStatus": demand.get(
        "MaterialCommitmentStatus"
    ),
}
~~~

Do not expose pending requirements, order payload, basis, or fingerprints.

- [ ] **Step 4: Verify focused transaction and full API regressions**

~~~powershell
pytest tests/test_order_commitment_api.py::TestOrderCommitmentApiAcceptance --collect-only -q
pytest tests/test_order_commitment_api.py tests/test_planning_commitments.py tests/test_planning_reservations.py tests/test_planning_reservation_view.py tests/test_state_store.py -q --basetemp .tmp/pytest-mto-acceptance-api-green -p no:cacheprovider
pytest tests/test_api.py -q --basetemp .tmp/pytest-mto-existing-api-regression -p no:cacheprovider
~~~

Expected: ten class tests and both regression commands pass.

- [ ] **Step 5: Commit**

~~~powershell
git add -- sdbr/api.py tests/test_order_commitment_api.py
git commit -m "feat: activate MTO reservations on planner decision"
~~~

---

### Task 22: Real MTO Acceptance-to-Planning-Run Bridge Compatibility

**Files and anchors**
- Modify `tests/test_planning_run_reservation_bridge.py` after existing completed/failed transition tests.
- No production code change.

**IDs:** `BE-SDBR-006` through `BE-SDBR-010`, `BE-RUN-011`.

- [ ] **Step 1: Write a test starting from the real MTO write set**

Add `TestMtoAcceptancePlanningRunBridge` with:

- `test_explicit_planning_run_selection_freezes_and_converts_mto_acceptance`;
- `test_explicit_planning_run_failure_preserves_mto_reservation_as_held`.

Fixture flow:

~~~python
evaluation = {
    "EvaluationID": "OCE-MTO-BRIDGE",
    "EvaluationFingerprint": "sha256:mto-bridge",
    "Status": "AwaitingPlannerDecision",
    "Order": {
        "SourceSystem": "MockERP",
        "SourceObjectType": "CustomerOrder",
        "OrderID": "SO-BRIDGE",
        "OrderVersion": "1",
        "DemandLineID": "10",
        "PlanningOrderID": "SO-BRIDGE:10",
        "ProductID": "FG-1",
        "LocationID": "MAIN",
        "Quantity": 1.0,
        "Uom": "EA",
        "RequestedDueAt": "2026-07-20T18:00:00+00:00",
        "BusinessPriority": 10,
        "RoutingID": "PRIMARY",
        "TraceID": "TRACE-SO-BRIDGE-10",
    },
    "Basis": {
        "BaselinePlanningRunID": "RUN-BASELINE",
        "OperatingModelConfigurationID": None,
        "OperatingModelFingerprint": None,
        "SchedulingConfigurationID": None,
        "DDMRPConfigurationID": None,
        "ReleasePolicyVersionID": "RELEASE-BRIDGE",
    },
    "ShadowSchedule": {
        "Status": "OnTime",
        "RequestedDateAssessment": {
            "Feasible": True,
            "PromiseAt": "2026-07-20T18:00:00+00:00",
            "ReservationRequests": [{
                "ReservationLineID": (
                    "SO-BRIDGE:10:CCR-CUT:"
                    "2026-07-20T08:00:00+00:00"
                ),
                "OrderID": "SO-BRIDGE:10",
                "OperationID": "SO-BRIDGE:10:CCR-CUT",
                "ResourceID": "CCR-1",
                "WindowStartAt": "2026-07-20T08:00:00+00:00",
                "WindowEndAt": "2026-07-20T16:00:00+00:00",
                "ReservedMinutes": 60,
                "LatestAllowedCompletionAt": (
                    "2026-07-20T16:00:00+00:00"
                ),
            }],
        },
    },
    "MaterialAssessment": {
        "Status": "Feasible",
        "AllocationRequests": [{
            "RequirementLineID": "SO-BRIDGE:10:RM-1",
            "ItemID": "RM-1",
            "LocationID": "MAIN",
            "Uom": "EA",
            "AllocatedQty": 5.0,
            "SupplySourceType": "OnHand",
            "MaterialSnapshotID": "OPS-BRIDGE",
        }],
        "PendingRequirements": [],
    },
    "Recommendation": {
        "AllowedActions": [
            "AcceptRequestedDate", "Reevaluate", "Reject"
        ],
        "RequiresCcrAcknowledgement": False,
        "RequiresMaterialAcknowledgement": False,
    },
}
write_set = prepare_mto_acceptance(
    evaluation=evaluation,
    existing_commitments={},
    decision_id="DEC-MTO-BRIDGE",
    decision="AcceptRequestedDate",
    decided_by="planner-bridge",
    decided_at=datetime(2026, 7, 11, 8, tzinfo=UTC),
    reason="Bridge compatibility acceptance.",
    ccr_risk_acknowledged=False,
    material_risk_acknowledged=False,
)
commitments = {}
batches = {}
capacities = {}
materials = {}
events = []
processed_keys = set()
planning_runs = {}
apply_reservation_write_set(
    write_set=write_set,
    commitments=commitments,
    batches=batches,
    capacity_reservations=capacities,
    material_allocations=materials,
    events=events,
    processed_event_keys=processed_keys,
)
assert planning_runs == {}
planning_run = {
    "RunID": "RUN-MTO-BRIDGE",
    "PlanningReservationBatchIDs": [
        write_set.batch["ReservationBatchID"]
    ],
}
frozen = freeze_planning_reservations(
    batch_ids=planning_run["PlanningReservationBatchIDs"],
    demand_commitments=commitments,
    batches=batches,
    capacity_reservations=capacities,
    material_allocations=materials,
)
expected_context = {
    "OrderCommitmentEvaluationID": "OCE-MTO-BRIDGE",
    "BaselinePlanningRunID": "RUN-BASELINE",
    "OperatingModelConfigurationID": None,
    "OperatingModelFingerprint": None,
    "SchedulingConfigurationID": None,
    "DDMRPConfigurationID": None,
    "ReleasePolicyVersionID": "RELEASE-BRIDGE",
    "RoutingID": "PRIMARY",
    "BusinessPriority": 10,
    "AcceptedPromiseAt": "2026-07-20T18:00:00+00:00",
    "MaterialCommitmentStatus": "PlannedAllocationPrepared",
    "PendingMaterialRequirements": [],
    "ExternalOrderAcceptance": "NotPerformed",
    "PlanningRunCreation": "NotPerformed",
    "ProductionMutation": "NotPerformed",
}
frozen_demand = frozen["DemandCommitments"][0]
assert {
    key: frozen_demand.get(key) for key in expected_context
} == expected_context
~~~

Completed schedule evidence is:

~~~python
{
    "GanttRows": [{
        "ResourceID": "CCR-1",
        "Bars": [{
            "OrderID": "SO-BRIDGE:10",
            "OperationID": "SO-BRIDGE:10:CCR-CUT",
            "Start": "2026-07-20T08:00:00+00:00",
            "End": "2026-07-20T09:00:00+00:00",
            "DurationMinutes": 60,
        }],
    }],
}
~~~

Call `transition_planning_reservations_for_run` with explicit batch IDs, frozen graph, and schedule; assert batch/capacity become `ConvertedToScheduledOccupancy`, material remains active, and correlations match. In a separate deep-copied graph call status `Failed` with no schedule; assert batch/capacity/material are `HeldForPlanningError`.

After both `Completed` and `Failed` transition calls, assert the original `commitments[write_set.demand_commitment["DemandCommitmentID"]]` still has every `expected_context` field/value and the returned transition contains no replacement demand projection. This proves the normalizer, freeze graph, and both lifecycle paths preserve the full new MTO context. Also assert acceptance itself created no `planning_run`; the test's local `planning_run` dict is the first and only explicit Planning Run bridge action.

~~~powershell
pytest tests/test_planning_run_reservation_bridge.py::TestMtoAcceptancePlanningRunBridge -q --basetemp .tmp/pytest-mto-bridge-red -p no:cacheprovider
~~~

Expected: both compatibility tests PASS against the already implemented MTO domain and Phase 0 bridge. If either fails, correct the earlier MTO correlation/write-set implementation before committing this test; do not add automatic Planning Run creation.

- [ ] **Step 2: Run the real compatibility test and bridge regressions**

~~~powershell
pytest tests/test_planning_run_reservation_bridge.py::TestMtoAcceptancePlanningRunBridge --collect-only -q
pytest tests/test_planning_run_reservation_bridge.py -q --basetemp .tmp/pytest-mto-bridge-green -p no:cacheprovider
~~~

Expected: two class tests and the entire bridge file pass. No application edit is needed.

- [ ] **Step 3: Commit**

~~~powershell
git add -- tests/test_planning_run_reservation_bridge.py
git commit -m "test: prove MTO Planning Run bridge compatibility"
~~~

---

### Task 23: Backend Verification and Evidence at Version 2.81

**Files and anchors**
- Modify `docs/backend-specification.md` at `BE-SDBR-010`, its acceptance record, header, and change-log head.

**IDs:** all backend IDs in this plan.

- [ ] **Step 1: Run syntax and exact focused collection**

~~~powershell
python -m compileall -q sdbr
pytest tests/test_ccr_shadow_scheduler.py tests/test_order_commitment_evaluation.py tests/test_order_commitment_view.py tests/test_order_commitment_api.py tests/test_planning_run_reservation_bridge.py tests/test_state_store.py tests/test_sdbr_market_control.py --collect-only -q
pytest tests/test_ccr_shadow_scheduler.py tests/test_order_commitment_evaluation.py tests/test_order_commitment_view.py tests/test_order_commitment_api.py tests/test_planning_run_reservation_bridge.py tests/test_state_store.py tests/test_sdbr_market_control.py -q --basetemp .tmp/pytest-mto-backend-focused -p no:cacheprovider
~~~

Expected: compile exits 0; collection names every class in Tasks 2-22; focused tests pass.

- [ ] **Step 2: Run preserved business paths**

~~~powershell
pytest tests/test_scheduling_solver.py tests/test_schedule_output.py tests/test_release_candidates.py tests/test_release_authorization.py tests/test_material_state.py tests/test_sdbr_market_control.py tests/test_sdbr_what_if.py tests/test_planning_reservations.py tests/test_planning_reservation_view.py tests/test_planning_run_reservation_bridge.py tests/test_api.py -q --basetemp .tmp/pytest-mto-preserved-paths -p no:cacheprovider
~~~

Expected: all pass; only the repository's known Starlette/httpx warning is acceptable if still emitted.

- [ ] **Step 3: Verify scope and forbidden mutations**

~~~powershell
rg -n "BE-SDBR-010|BE-RUN-011|UI-COMMIT-001" tests sdbr docs/backend-specification.md docs/ui-specification.md
rg -n "ExternalOrderAcceptance|PlanningRunCreation|ProductionMutation|ReferenceFallback|ORDER_COMMITMENT_OPERATIONAL_STATE_MAX_AGE_MINUTES" sdbr tests
rg -n "MaterialCheckWindowMinutes" sdbr/web/planner-workbench.js
git diff --check
git status --short
~~~

Expected: first two scans find required citations/boundaries; the JavaScript material-window scan has no MTO request occurrence; no changed path is under the prohibited directories; diff check is clean.

- [ ] **Step 4: Record only observed evidence**

Advance backend header to `2.81`, set `BE-SDBR-010` to `[PARTIAL]`, replace planned evidence with exact implemented paths/endpoints/tests, and append a `2.81` row. In the acceptance record, copy the exact commands and terminal summaries actually observed; do not predeclare counts.

Keep `[PARTIAL]` because approved CCR threshold intake, external formal-order authority, explicit later Planning Run, and ERP/MES authority remain outside this implementation.

- [ ] **Step 5: Commit**

~~~powershell
git add -- docs/backend-specification.md
git commit -m "docs: record MTO commitment backend evidence"
~~~

---

### Task 24: UI Specification Development State and Semantic Shell

**Files and anchors**
- Modify `docs/ui-specification.md` at `UI-COMMIT-001` and record 17.13.
- Modify `sdbr/web/planner-workbench.html:20-62` nav, after `material-planning-view`, and near existing drawers/dialogs.
- Modify `tests/test_api.py:5653` `test_planner_workbench_page_returns_semantic_application_shell`; add a focused MTO shell test nearby.

**IDs:** `UI-COMMIT-001`, `BE-SDBR-010`.

- [ ] **Step 1: Move only unit 13 to development**

Change `UI-COMMIT-001` and record 17.13 from `未开始` to `开发中`. Do not change any other UI status.

- [ ] **Step 2: Replace the brittle nav count with exact sequence assertions**

Add `import re` and update the existing shell test:

~~~python
routes = re.findall(
    r'<a class="nav-item"[^>]+data-route="([^"]+)"[^>]+data-nav-help>',
    html,
)
indices = re.findall(
    r'<span class="nav-index" aria-hidden="true">([^<]+)</span>',
    html,
)
assert routes == [
    "overview", "operational-metrics", "data-readiness",
    "material-planning", "order-commitments", "planning-runs",
    "schedule-results", "release-management", "buffer-board",
    "dispatch-suggestions", "exceptions", "calendar",
    "administration", "public-demo",
]
assert indices == [
    "01", "02", "03", "04", "05", "06", "07",
    "08", "09", "10", "11", "12", "13", "D1",
]
assert routes.count("order-commitments") == 1
assert len(routes) == len(set(routes))
~~~

Add `TestOrderCommitmentUiShell.test_shell_has_independent_view_exact_columns_drawer_and_dialog` asserting IDs and all table headers, including `ReservationStatus` and `ExceptionStatus`.

~~~powershell
pytest tests/test_api.py::test_planner_workbench_page_returns_semantic_application_shell tests/test_api.py::TestOrderCommitmentUiShell::test_shell_has_independent_view_exact_columns_drawer_and_dialog -q --basetemp .tmp/pytest-mto-ui-shell-red -p no:cacheprovider
~~~

Expected: failures because route and view are absent.

- [ ] **Step 3: Add the exact route and workbench markup**

Insert after material planning and renumber later numeric indices; preserve `D1`:

~~~html
<a class="nav-item" href="#order-commitments"
   data-route="order-commitments" data-nav-help>
  <span class="nav-index" aria-hidden="true">05</span>
  <span data-i18n="navOrderCommitments">订单承诺</span>
</a>
~~~

Add:

~~~html
<div id="order-commitments-view" class="order-commitments-view" hidden>
  <section class="order-commitment-summary"
           aria-label="订单承诺摘要"
           data-i18n-aria-label="orderCommitmentSummary">
    <div><span data-i18n="awaitingDecision">待决定</span>
      <strong data-order-commitment-summary="AwaitingDecisionCount">0</strong></div>
    <div><span data-i18n="confirmationRequired">需确认</span>
      <strong data-order-commitment-summary="ConfirmationRequiredCount">0</strong></div>
    <div><span data-i18n="materialPending">物料待确认</span>
      <strong data-order-commitment-summary="MaterialPendingCount">0</strong></div>
    <div><span data-i18n="acceptedPendingSchedule">已接受，待正式排程</span>
      <strong data-order-commitment-summary="AcceptedPendingScheduleCount">0</strong></div>
  </section>
  <div id="order-commitment-error" class="persistent-error"
       role="alert" hidden></div>
  <section id="order-commitment-content"
           class="order-commitment-workbench" hidden>
    <div class="compact-toolbar">
      <label><span data-i18n="searchOrderOrProduct">搜索订单或产品</span>
        <input id="order-commitment-search" type="search"></label>
      <label><span data-i18n="status">状态</span>
        <select id="order-commitment-status-filter">
          <option value="" data-i18n="allStatuses">全部状态</option>
        </select></label>
      <button id="refresh-order-commitments" class="button secondary"
              type="button" data-i18n="refresh">刷新</button>
    </div>
    <div class="table-scroll">
      <table id="order-commitment-table" class="data-table">
        <thead><tr>
          <th data-i18n="order">订单</th>
          <th data-i18n="product">产品</th>
          <th data-i18n="requestedDueAt">请求交期</th>
          <th data-i18n="earliestSafePromise">建议安全日期</th>
          <th data-i18n="ccrLoadBeforeAfter">CCR 负荷前后</th>
          <th data-i18n="protectionThresholdSource">保护线来源</th>
          <th data-i18n="materialStatus">物料状态</th>
          <th data-i18n="recommendation">建议</th>
          <th data-i18n="reservationStatus">预留状态</th>
          <th data-i18n="exceptionStatus">异常状态</th>
          <th data-i18n="actions">操作</th>
        </tr></thead>
        <tbody id="order-commitment-table-body"></tbody>
      </table>
    </div>
  </section>
  <div id="order-commitment-empty" class="table-empty" hidden></div>
</div>
~~~

- [ ] **Step 4: Add detail and decision containers**

Add one `aside#order-commitment-detail` with:

~~~html
<div class="drawer-heading">
  <div><span class="panel-kicker"
             data-i18n="orderCommitmentEvaluation">订单承诺评估</span>
    <h2 id="order-commitment-detail-title">-</h2></div>
  <button id="close-order-commitment-detail" class="icon-button"
          type="button" data-i18n-aria-label="close">&#10005;</button>
</div>
<div id="order-commitment-detail-content"
     class="run-detail-content"></div>
<form id="order-commitment-reevaluation-form"
      class="order-commitment-reevaluation" hidden>
  <label class="capability-toggle">
    <input id="order-commitment-material-check" type="checkbox" checked>
    <span data-i18n="checkMaterialAvailability">检查物料计划可用性</span>
  </label>
  <label id="order-commitment-material-skip-field" hidden>
    <span data-i18n="materialSkipReason">跳过原因</span>
    <textarea id="order-commitment-material-skip-reason" rows="3"></textarea>
  </label>
  <p data-i18n="orderCommitmentMaterialGateReminder">
    释放阶段仍执行物料硬门控
  </p>
  <button id="reevaluate-order-commitment" class="button secondary"
          type="submit" data-i18n="reevaluate">重新评估</button>
</form>
<div id="order-commitment-actions" class="wizard-actions"></div>
~~~

Add:

~~~html
<dialog id="order-commitment-decision-dialog"
        class="run-wizard compact-dialog"
        aria-labelledby="order-commitment-decision-title">
  <form id="order-commitment-decision-form" method="dialog">
    <div class="drawer-heading">
      <div><span class="panel-kicker"
                 data-i18n="plannerDecision">计划员决定</span>
        <h2 id="order-commitment-decision-title">-</h2></div>
    </div>
    <div id="order-commitment-decision-summary"
         class="order-commitment-decision-grid"></div>
    <label id="order-commitment-ccr-ack-field" hidden>
      <input id="order-commitment-ccr-ack" type="checkbox">
      <span data-i18n="acknowledgeCcrRisk">
        我已复核 CCR 保护负荷风险
      </span>
    </label>
    <label id="order-commitment-material-ack-field" hidden>
      <input id="order-commitment-material-ack" type="checkbox">
      <span data-i18n="acknowledgeMaterialPending">
        我确认物料仍待处理，且释放阶段继续硬门控
      </span>
    </label>
    <label><span data-i18n="decisionReason">决定原因</span>
      <textarea id="order-commitment-decision-reason"
                rows="3" required></textarea>
    </label>
    <div id="order-commitment-decision-error"
         class="persistent-error" role="alert" hidden></div>
    <p class="inline-note"
       data-i18n="orderCommitmentExternalBoundary">
      不会自动接受外部订单，也不会创建 Planning Run 或修改 ERP/MES
    </p>
    <div class="wizard-actions">
      <button id="cancel-order-commitment-decision"
              class="button secondary" type="button"
              data-i18n="cancel">取消</button>
      <button id="submit-order-commitment-decision"
              class="button primary" type="submit"
              data-i18n="confirm">确认</button>
    </div>
  </form>
</dialog>
~~~

Increment HTML asset query versions to `v=20260711-mto-order-commitment`.

- [ ] **Step 5: Verify and commit**

~~~powershell
pytest tests/test_api.py::test_planner_workbench_page_returns_semantic_application_shell tests/test_api.py::TestOrderCommitmentUiShell --collect-only -q
pytest tests/test_api.py::test_planner_workbench_page_returns_semantic_application_shell tests/test_api.py::TestOrderCommitmentUiShell -q --basetemp .tmp/pytest-mto-ui-shell-green -p no:cacheprovider
git add -- docs/ui-specification.md sdbr/web/planner-workbench.html tests/test_api.py
git commit -m "feat: add MTO commitment workbench shell"
~~~

Expected: exact route/index sequence and shell tests pass.

---

### Task 25: Bilingual Read Flow, Exact Rows, and Safe Details

**Files and anchors**
- Modify `sdbr/web/planner-workbench.js:1-850` translations, `:859` `ROUTES`, `:900` state, `:979` `renderRoute`, and before `DOMContentLoaded`.
- Modify `sdbr/web/planner-workbench.css` near existing data-table/drawer responsive rules.
- Modify `tests/test_api.py` after `TestOrderCommitmentUiShell`.
- Modify `tests/test_order_commitment_api.py` with a UI response-contract test.

**IDs:** `UI-COMMIT-001`, `BE-SDBR-010`.

- [ ] **Step 1: Write read-flow and translation tests**

Add `TestOrderCommitmentUiReadFlow`:

- `test_script_uses_workbench_detail_endpoints_and_revision_header`;
- `test_every_backend_enum_has_exact_chinese_and_english_label`;
- `test_render_uses_reservation_exception_and_allowed_actions_fields`;
- `test_detail_renderer_has_no_json_stringify_or_raw_payload_path`.

In `tests/test_order_commitment_api.py`, add
`TestOrderCommitmentUiContract.test_api_ui_contract_contains_every_field_consumed_by_javascript`.
Create one evaluation through intake, read workbench/detail, and assert
`set(row) == set(ORDER_COMMITMENT_ROW_FIELDS)`,
`set(detail) == set(DETAIL_FIELDS)`, and that every nested field read by
the JavaScript whitelists is present.

~~~powershell
pytest tests/test_api.py::TestOrderCommitmentUiReadFlow tests/test_order_commitment_api.py::TestOrderCommitmentUiContract -q --basetemp .tmp/pytest-mto-ui-read-red -p no:cacheprovider
~~~

Expected: read-flow tests fail because JS/CSS are absent.

- [ ] **Step 2: Add exact bilingual enum labels**

Both language maps must cover this table; fallback renders localized `unknownStatus`, never the raw enum:

| Enum | Chinese | English |
| --- | --- | --- |
| `RecommendAccept` | 建议接受 | Recommend accept |
| `PlannerConfirmationRequired` | 需计划员确认 | Planner confirmation required |
| `CapacityAcceptableMaterialPending` | 产能可接受，物料待确认 | Capacity acceptable, material pending |
| `MaterialEvidenceRequired` | 待物料确认 | Material evidence required |
| `RecommendLaterPromise` | 建议调整交期 | Recommend later promise |
| `DoNotRecommendAccept` | 暂不建议接受 | Do not recommend acceptance |
| `Feasible` | 物料可行 | Material feasible |
| `SkippedPendingConfirmation` | 物料待确认（已跳过检查） | Material pending (check skipped) |
| `EvidenceInsufficient` | 物料证据不足 | Material evidence insufficient |
| `Shortage` | 物料短缺 | Material shortage |
| `OnTime` | 可按请求日期完成 | On time |
| `LaterSafeDate` | 需采用后续安全日期 | Later safe date |
| `NotAssessable` | 暂不可评估 | Not assessable |
| `Fresh` | 新鲜 | Fresh |
| `Stale` | 已过期 | Stale |
| `Future` | 时间异常 | Future |
| `Missing` | 缺失 | Missing |
| `Protected` | 保护范围内 | Protected |
| `Watch` | 需要关注 | Watch |
| `NearLimit` | 接近上限 | Near limit |
| `Overloaded` | 超载 | Overloaded |
| `ApprovedWithin` | 批准保护线内 | Within approved threshold |
| `ApprovedExceeded` | 超过批准保护线 | Approved threshold exceeded |
| `Covered` | 已覆盖 | Covered |
| `PlannedAllocationPrepared` | 计划分配已准备 | Planned allocation prepared |
| `PendingConfirmation` | 待确认 | Pending confirmation |
| `AwaitingPlannerDecision` | 待计划员决定 | Awaiting planner decision |
| `AcceptedPendingFormalSchedule` | 已接受，待正式排程 | Accepted, pending formal schedule |
| `Rejected` | 已拒绝 | Rejected |
| `Superseded` | 已由新评估替代 | Superseded by newer evaluation |
| `NotReserved` | 尚未预留 | Not reserved |
| `ActivePlanReservation` | 计划预留有效 | Active plan reservation |
| `LinkedToFormalOrder` | 已关联正式订单 | Linked to formal order |
| `ConvertedToScheduledOccupancy` | 已转正式排程占用 | Converted to scheduled occupancy |
| `HeldForPlanningError` | 排程异常待处理 | Held for planning error |
| `AdjustmentRequired` | 需要调整 | Adjustment required |
| `Released` | 已释放 | Released |
| `Cancelled` | 已取消 | Cancelled |
| `ReservationEvidenceMissing` | 预留证据缺失 | Reservation evidence missing |
| `None` | 无异常 | No exception |
| `AssessmentBlocked` | 评估受阻 | Assessment blocked |
| `MaterialEvidenceBlocked` | 物料证据受阻 | Material evidence blocked |
| `PlanningErrorPending` | 排程异常待处理 | Planning error pending |
| `ReferenceFallback` | 80% 默认参考，需确认 | 80% reference fallback; confirmation required |
| `ApprovedOperatingModel` | 批准的运行模型保护线 | Approved operating-model threshold |
| `AcceptRequestedDate` | 接受请求日期 | Accept requested date |
| `ConditionallyAcceptRequestedDate` | 条件接受请求日期 | Conditionally accept requested date |
| `AcceptRecommendedDate` | 接受建议日期 | Accept recommended date |
| `ConditionallyAcceptRecommendedDate` | 条件接受建议日期 | Conditionally accept recommended date |
| `Reevaluate` | 重新评估 | Re-evaluate |
| `Reject` | 拒绝 | Reject |
| `OrderCommitmentEvaluated` | 已评估 | Commitment evaluated |
| `OrderCommitmentReevaluated` | 已重新评估 | Commitment re-evaluated |
| `OrderCommitmentEvaluationSuperseded` | 评估已替代 | Evaluation superseded |
| `OrderCommitmentAccepted` | 已接受 | Commitment accepted |
| `OrderCommitmentRejected` | 已拒绝 | Commitment rejected |
| `LatestCurrent` | 最新当前快照 | Latest current snapshot |
| `Explicit` | 显式快照 | Explicit snapshot |
| `OnHand` | 在手 | On hand |
| `OnHandAndInbound` | 在手与在途 | On hand and inbound |
| `NotPerformed` | 未执行 | Not performed |

- [ ] **Step 3: Add route/state/load/render**

~~~javascript
ROUTES["order-commitments"] = [
  "pageOrderCommitments", "descriptionOrderCommitments"
];
let orderCommitmentData = null;
let orderCommitmentRevision = null;
let selectedOrderCommitment = null;
let selectedOrderCommitmentAction = null;

async function loadOrderCommitments() {
  const response = await fetch(
    "/planner/workbench/order-commitments/workbench",
    { headers: { Accept: "application/json" } }
  );
  orderCommitmentRevision = response.headers.get(
    "X-Workbench-Revision"
  );
  if (!response.ok) throw new Error("order-commitment-load-failed");
  orderCommitmentData = (await response.json()).Data;
  renderOrderCommitments();
}

async function openOrderCommitmentDetail(evaluationId) {
  const response = await fetch(
    "/planner/workbench/order-commitments/"
      + encodeURIComponent(evaluationId),
    { headers: { Accept: "application/json" } }
  );
  orderCommitmentRevision = response.headers.get(
    "X-Workbench-Revision"
  ) || orderCommitmentRevision;
  if (!response.ok) throw new Error("order-commitment-detail-failed");
  selectedOrderCommitment = (await response.json()).Data;
  renderOrderCommitmentDetail();
  openSideDrawer("order-commitment-detail");
}
~~~

`renderRoute` shows/loads this independent view. `renderOrderCommitments` filters order/product/status and renders every exact row column, including reservation and exception status plus a `ViewDetails` button. Use `textContent`/existing `textCell`, never `innerHTML` with server values.

`renderOrderCommitmentDetail` creates business sections from whitelisted `Order`, `CapacityEvidence`, `MaterialEvidence`, `Recommendation`, `Decision`, `Reservation`, and `AuditHistory`, and a collapsed `<details class="technical-detail">` from `TechnicalDetails`. Do not call `JSON.stringify` on detail or any subsection.

- [ ] **Step 4: Add restrained responsive styles**

~~~css
.order-commitment-summary {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
}
.order-commitment-workbench .table-scroll {
  max-width: 100%;
  overflow-x: auto;
}
.order-commitment-decision-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}
@media (max-width: 900px) {
  .order-commitment-summary,
  .order-commitment-decision-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .order-commitment-workbench .compact-toolbar {
    grid-template-columns: minmax(0, 1fr);
  }
  #order-commitment-decision-dialog {
    width: min(calc(100% - 24px), 640px);
  }
}
~~~

Use existing variables/radius. Add no gradients, blobs, negative letter spacing, nested cards, or page-level horizontal overflow.

- [ ] **Step 5: Verify and commit**

~~~powershell
node --check sdbr/web/planner-workbench.js
pytest tests/test_api.py::TestOrderCommitmentUiReadFlow tests/test_order_commitment_api.py::TestOrderCommitmentUiContract --collect-only -q
pytest tests/test_api.py::TestOrderCommitmentUiReadFlow tests/test_order_commitment_api.py::TestOrderCommitmentUiContract -q --basetemp .tmp/pytest-mto-ui-read-green -p no:cacheprovider
git add -- sdbr/web/planner-workbench.js sdbr/web/planner-workbench.css tests/test_api.py tests/test_order_commitment_api.py
git commit -m "feat: render MTO commitment evidence"
~~~

Expected: JS syntax and five read-flow/contract tests pass.

---

### Task 26: Re-evaluation Controls and Terminal Action Gating

**Files and anchors**
- Modify `sdbr/web/planner-workbench.js` at detail rendering and `DOMContentLoaded`.
- Modify `tests/test_api.py` after UI read-flow tests.
- Modify `tests/test_order_commitment_view.py` terminal-action coverage.

**IDs:** `UI-COMMIT-001`, `BE-SDBR-010`.

- [ ] **Step 1: Write action-gating and request-shape tests**

Add `TestOrderCommitmentUiReevaluation`:

- `test_reevaluation_form_is_driven_only_by_allowed_actions`;
- `test_terminal_detail_has_no_reevaluation_or_decision_controls`;
- `test_material_toggle_requires_reason_when_disabled`;
- `test_reevaluation_request_contains_no_material_window`;
- `test_success_refreshes_revision_list_and_new_detail`.

Static assertions require the script to read `selectedOrderCommitment.Recommendation.AllowedActions`, and assert `MaterialCheckWindowMinutes` and `MaterialLookaheadMinutes` are absent from the MTO request builder.

~~~powershell
pytest tests/test_api.py::TestOrderCommitmentUiReevaluation tests/test_order_commitment_view.py::TestOrderCommitmentViewContract::test_terminal_rows_have_empty_allowed_actions -q --basetemp .tmp/pytest-mto-ui-reeval-red -p no:cacheprovider
~~~

Expected: UI tests fail because handlers/gates are absent.

- [ ] **Step 2: Render controls from `AllowedActions` only**

~~~javascript
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
    button.className = action === "Reject"
      ? "button danger" : "button primary";
    button.textContent = enumLabel("action", action);
    button.addEventListener("click", () => {
      openOrderCommitmentDecision(action);
    });
    actions.append(button);
  });
}
~~~

Because terminal backend details return `AllowedActions=[]`, accepted, rejected, and superseded details are read-only. Exact replay remains an API behavior and is never shown as an active UI action.

- [ ] **Step 3: Implement material toggle and exact re-evaluation body**

~~~javascript
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
    showOrderCommitmentError(
      translate("materialSkipReasonRequired")
    );
    return;
  }
  const response = await fetch(
    "/planner/workbench/order-commitments/"
      + encodeURIComponent(selectedOrderCommitment.EvaluationID)
      + "/reevaluate",
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
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
  if (!response.ok) {
    showOrderCommitmentError(await responseErrorMessage(response));
    return;
  }
  const newId = (await response.json()).Data.Evaluation.EvaluationID;
  await loadOrderCommitments();
  await openOrderCommitmentDetail(newId);
}
~~~

No baseline or material-window override is sent; the source baseline and frozen release policy remain server-owned.

- [ ] **Step 4: Bind, verify, and commit**

Bind toggle `change`, form `submit`, drawer close, search/filter/refresh, route load, and language re-render in `DOMContentLoaded`.

~~~powershell
node --check sdbr/web/planner-workbench.js
pytest tests/test_api.py::TestOrderCommitmentUiReevaluation tests/test_order_commitment_view.py::TestOrderCommitmentViewContract::test_terminal_rows_have_empty_allowed_actions --collect-only -q
pytest tests/test_api.py::TestOrderCommitmentUiReevaluation tests/test_order_commitment_view.py::TestOrderCommitmentViewContract::test_terminal_rows_have_empty_allowed_actions -q --basetemp .tmp/pytest-mto-ui-reeval-green -p no:cacheprovider
git add -- sdbr/web/planner-workbench.js tests/test_api.py
git commit -m "feat: gate MTO reevaluation actions"
~~~

Expected: five UI tests and terminal view test pass.

---

### Task 27: Revision-Guarded Decision Dialog

**Files and anchors**
- Modify `sdbr/web/planner-workbench.js` at decision dialog functions and `DOMContentLoaded`.
- Modify `tests/test_api.py` after re-evaluation UI tests.

**IDs:** `UI-COMMIT-001`, `BE-SDBR-010`.

- [ ] **Step 1: Write decision-flow tests**

Add `TestOrderCommitmentUiDecisionFlow`:

- `test_dialog_shows_ccr_ack_for_reference_and_exceeded_candidates`;
- `test_dialog_shows_material_ack_for_both_conditional_actions`;
- `test_reject_hides_and_does_not_require_both_risk_acknowledgements`;
- `test_dialog_requires_reason_and_visible_acknowledgements`;
- `test_decision_sends_if_match_fingerprint_and_all_canonical_fields`;
- `test_conflict_refreshes_without_automatic_decision_retry`;
- `test_success_renders_accepted_pending_formal_schedule_boundaries`.

~~~powershell
pytest tests/test_api.py::TestOrderCommitmentUiDecisionFlow -q --basetemp .tmp/pytest-mto-ui-decision-red -p no:cacheprovider
~~~

Expected: six failures because decision functions are absent.

- [ ] **Step 2: Open the dialog from the selected action**

~~~javascript
function openOrderCommitmentDecision(action) {
  if (!orderCommitmentAllowedActions().has(action)) return;
  selectedOrderCommitmentAction = action;
  const recommendation = selectedOrderCommitment.Recommendation;
  const requirements =
    recommendation.ActionAcknowledgementRequirements?.[action] || {
      RequiresCcrAcknowledgement: false,
      RequiresMaterialAcknowledgement: false
    };
  document.getElementById(
    "order-commitment-ccr-ack-field"
  ).hidden = !requirements.RequiresCcrAcknowledgement;
  document.getElementById(
    "order-commitment-material-ack-field"
  ).hidden = !requirements.RequiresMaterialAcknowledgement;
  document.getElementById("order-commitment-ccr-ack").checked = false;
  document.getElementById(
    "order-commitment-material-ack"
  ).checked = false;
  document.getElementById(
    "order-commitment-decision-reason"
  ).value = "";
  renderOrderCommitmentDecisionSummary(
    selectedOrderCommitment, action
  );
  document.getElementById(
    "order-commitment-decision-dialog"
  ).showModal();
}
~~~

Summary shows action, requested/selected promise, CCR load/threshold source, material status, and three `NotPerformed` boundaries.

- [ ] **Step 3: Submit exact canonical decision and handle conflicts**

~~~javascript
async function submitOrderCommitmentDecision(event) {
  event.preventDefault();
  const detail = selectedOrderCommitment;
  const action = selectedOrderCommitmentAction;
  if (!detail || !orderCommitmentAllowedActions().has(action)) return;
  const reason = document.getElementById(
    "order-commitment-decision-reason"
  ).value.trim();
  const ccrRequired = !document.getElementById(
    "order-commitment-ccr-ack-field"
  ).hidden;
  const materialRequired = !document.getElementById(
    "order-commitment-material-ack-field"
  ).hidden;
  const ccrAck = document.getElementById(
    "order-commitment-ccr-ack"
  ).checked;
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
  const decisionId = [
    "DEC", detail.EvaluationID, detail.RecordVersion, action
  ].join("-");
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
  if (!response.ok && [
    "StateStoreRevisionConflict",
    "OrderCommitmentEvaluationStale"
  ].includes(status)) {
    showOrderCommitmentDecisionError(
      translate("orderCommitmentEvidenceChanged")
    );
    await loadOrderCommitments();
    await openOrderCommitmentDetail(detail.EvaluationID);
    selectedOrderCommitmentAction = null;
    document.getElementById(
      "submit-order-commitment-decision"
    ).disabled = true;
    return;
  }
  if (!response.ok) {
    showOrderCommitmentDecisionError(
      payload?.Data?.Message || translate("requestFailed")
    );
    return;
  }
  document.getElementById(
    "order-commitment-decision-dialog"
  ).close();
  selectedOrderCommitmentAction = null;
  await loadOrderCommitments();
  await openOrderCommitmentDetail(detail.EvaluationID);
}
~~~

There is exactly one fetch whose path ends in `/decision` in this function and no retry loop/call. Conflict refresh requires a new planner choice.

- [ ] **Step 4: Bind, verify, and commit**

~~~powershell
node --check sdbr/web/planner-workbench.js
pytest tests/test_api.py::TestOrderCommitmentUiDecisionFlow --collect-only -q
pytest tests/test_api.py::TestOrderCommitmentUiDecisionFlow -q --basetemp .tmp/pytest-mto-ui-decision-green -p no:cacheprovider
git add -- sdbr/web/planner-workbench.js tests/test_api.py
git commit -m "feat: confirm option2 MTO decisions"
~~~

Expected: six decision-flow tests pass.

---

### Task 28: Reproducible API Seed, Browser Acceptance, and UI Evidence

**Files and anchors**
- Create `scripts/seed_mto_order_commitment_browser.ps1`.
- Modify `tests/test_order_commitment_api.py` after acceptance tests.
- Modify `docs/ui-specification.md` at `UI-COMMIT-001`, record 17.13, header, and change-log head.

**IDs:** `UI-COMMIT-001`, `BE-SDBR-010`.

- [ ] **Step 1: Write an in-process acceptance-sequence test**

Add `TestOrderCommitmentBrowserSequence.test_public_sequence_creates_ordinary_skipped_accepted_and_stale_states`. It calls only public endpoints:

1. test-data MTO reset;
2. five distinct intakes (`ORDINARY`, `SKIP`, `STALE`, `ACCEPT`, `REJECT`);
3. re-evaluate `SKIP` with material disabled/reason;
4. accept `ACCEPT` with current revision and CCR acknowledgement;
5. submit `STALE` with the refreshed global revision and its old fingerprint;
6. reject `REJECT` with both risk acknowledgements false;
7. assert ordinary awaiting, skipped material pending, accepted pending formal schedule with batch, rejected terminal with `AllowedActions=[]`, and stale 409 whose request can be repeated without ledger mutation.

Also assert no automatic Planning Run beyond the seeded baseline and deep authority snapshot unchanged after steps 2-5.

~~~powershell
pytest tests/test_order_commitment_api.py::TestOrderCommitmentBrowserSequence -q --basetemp .tmp/pytest-mto-browser-sequence-red -p no:cacheprovider
~~~

Expected: the sequence test fails until the repeatable script/response assumptions are aligned.

- [ ] **Step 2: Create the complete API-only PowerShell seeder**

Create:

~~~powershell
param(
  [string]$BaseUrl = "http://127.0.0.1:8765",
  [string]$OutputPath = ".tmp/mto-order-commitment-browser-fixture.json"
)

$ErrorActionPreference = "Stop"

function Invoke-SdbrJson {
  param(
    [string]$Method,
    [string]$Path,
    [object]$Body = $null,
    [hashtable]$Headers = @{}
  )
  $arguments = @{
    Uri = "$BaseUrl$Path"
    Method = $Method
    Headers = $Headers
    SkipHttpErrorCheck = $true
  }
  if ($null -ne $Body) {
    $arguments.ContentType = "application/json"
    $arguments.Body = $Body | ConvertTo-Json -Depth 30
  }
  $response = Invoke-WebRequest @arguments
  $payload = $response.Content | ConvertFrom-Json
  return [pscustomobject]@{
    StatusCode = [int]$response.StatusCode
    Revision = [string]$response.Headers["X-Workbench-Revision"]
    Payload = $payload
  }
}

function Copy-JsonObject {
  param([object]$Value)
  return $Value | ConvertTo-Json -Depth 30 | ConvertFrom-Json
}

$reset = Invoke-SdbrJson `
  -Method "POST" `
  -Path "/planner/workbench/test-data/order-commitment/reset"
if ($reset.StatusCode -ne 200) {
  throw "MTO fixture reset failed: $($reset.StatusCode)"
}
$template = $reset.Payload.Data.IntakePayloadTemplate

function New-MtoEvaluation {
  param([string]$Suffix)
  $body = Copy-JsonObject $template
  $body.OrderID = "TST-MTO-SO-$Suffix"
  $body.TraceID = "TRACE-TST-MTO-$Suffix"
  $body.MaterialRequirements[0].RequirementLineID = (
    "{0}:10:TST-MTO-RM-1" -f $body.OrderID
  )
  $response = Invoke-SdbrJson `
    -Method "POST" `
    -Path "/planner/workbench/order-commitments/intake" `
    -Body $body
  if ($response.StatusCode -ne 200) {
    throw "MTO intake $Suffix failed: $($response.StatusCode)"
  }
  return $response
}

$ordinary = New-MtoEvaluation "ORDINARY"
$skipSource = New-MtoEvaluation "SKIP"
$stale = New-MtoEvaluation "STALE"
$acceptSource = New-MtoEvaluation "ACCEPT"
$rejectSource = New-MtoEvaluation "REJECT"

$skipSourceId = $skipSource.Payload.Data.Evaluation.EvaluationID
$skipped = Invoke-SdbrJson `
  -Method "POST" `
  -Path (
    "/planner/workbench/order-commitments/{0}/reevaluate" -f
    $skipSourceId
  ) `
  -Body @{
    RequestedBy = "planner-browser"
    OperationalStateSnapshotID = $null
    CheckMaterialAvailability = $false
    MaterialCheckSkipReason = "Browser capacity-only acceptance evidence."
  }
if ($skipped.StatusCode -ne 200) {
  throw "MTO skipped-material re-evaluation failed."
}

$acceptId = $acceptSource.Payload.Data.Evaluation.EvaluationID
$acceptDetail = Invoke-SdbrJson `
  -Method "GET" `
  -Path (
    "/planner/workbench/order-commitments/{0}" -f $acceptId
  )
$accepted = Invoke-SdbrJson `
  -Method "POST" `
  -Path (
    "/planner/workbench/order-commitments/{0}/decision" -f $acceptId
  ) `
  -Headers @{ "If-Match" = $acceptDetail.Revision } `
  -Body @{
    DecisionID = "DEC-TST-MTO-BROWSER-ACCEPT"
    Decision = "AcceptRequestedDate"
    DecidedBy = "planner-browser"
    Reason = "Browser acceptance evidence."
    ExpectedEvaluationFingerprint = (
      $acceptDetail.Payload.Data.TechnicalDetails.EvaluationFingerprint
    )
    CcrRiskAcknowledged = $true
    MaterialRiskAcknowledged = $false
  }
if ($accepted.StatusCode -ne 200) {
  throw "MTO acceptance failed."
}

$rejectId = $rejectSource.Payload.Data.Evaluation.EvaluationID
$rejectDetail = Invoke-SdbrJson `
  -Method "GET" `
  -Path ("/planner/workbench/order-commitments/{0}" -f $rejectId)
$rejected = Invoke-SdbrJson `
  -Method "POST" `
  -Path (
    "/planner/workbench/order-commitments/{0}/decision" -f $rejectId
  ) `
  -Headers @{ "If-Match" = $rejectDetail.Revision } `
  -Body @{
    DecisionID = "DEC-TST-MTO-BROWSER-REJECT"
    Decision = "Reject"
    DecidedBy = "planner-browser"
    Reason = "Browser rejected-terminal evidence."
    ExpectedEvaluationFingerprint = (
      $rejectDetail.Payload.Data.TechnicalDetails.EvaluationFingerprint
    )
    CcrRiskAcknowledged = $false
    MaterialRiskAcknowledged = $false
  }
if ($rejected.StatusCode -ne 200) {
  throw "MTO rejection failed."
}

$staleId = $stale.Payload.Data.Evaluation.EvaluationID
$staleDetail = Invoke-SdbrJson `
  -Method "GET" `
  -Path (
    "/planner/workbench/order-commitments/{0}" -f $staleId
  )
$staleDecision = Invoke-SdbrJson `
  -Method "POST" `
  -Path (
    "/planner/workbench/order-commitments/{0}/decision" -f $staleId
  ) `
  -Headers @{ "If-Match" = $staleDetail.Revision } `
  -Body @{
    DecisionID = "DEC-TST-MTO-BROWSER-STALE"
    Decision = "AcceptRequestedDate"
    DecidedBy = "planner-browser"
    Reason = "Must be rejected as stale."
    ExpectedEvaluationFingerprint = (
      $staleDetail.Payload.Data.TechnicalDetails.EvaluationFingerprint
    )
    CcrRiskAcknowledged = $true
    MaterialRiskAcknowledged = $false
  }
if (
  $staleDecision.StatusCode -ne 409 -or
  $staleDecision.Payload.Data.Status -ne "OrderCommitmentEvaluationStale"
) {
  throw "MTO stale-decision fixture did not produce the expected 409."
}

$result = [ordered]@{
  BaselinePlanningRunID = $reset.Payload.Data.BaselinePlanningRunID
  OperationalStateSnapshotID = (
    $reset.Payload.Data.OperationalStateSnapshotID
  )
  OrdinaryEvaluationID = (
    $ordinary.Payload.Data.Evaluation.EvaluationID
  )
  SkippedEvaluationID = (
    $skipped.Payload.Data.Evaluation.EvaluationID
  )
  AcceptedEvaluationID = $acceptId
  AcceptedReservationBatchID = (
    $accepted.Payload.Data.ReservationBatchID
  )
  RejectedEvaluationID = $rejectId
  StaleEvaluationID = $staleId
  StaleDecisionStatus = $staleDecision.Payload.Data.Status
  FinalRevision = $staleDecision.Revision
}
$directory = Split-Path -Parent $OutputPath
if ($directory) {
  New-Item -ItemType Directory -Path $directory -Force | Out-Null
}
$result | ConvertTo-Json -Depth 10 |
  Set-Content -LiteralPath $OutputPath -Encoding utf8
$result
~~~

This script never imports a test helper or writes SQLite directly.

- [ ] **Step 3: Verify script assumptions in pytest**

~~~powershell
pytest tests/test_order_commitment_api.py::TestOrderCommitmentBrowserSequence --collect-only -q
pytest tests/test_order_commitment_api.py::TestOrderCommitmentBrowserSequence -q --basetemp .tmp/pytest-mto-browser-sequence-green -p no:cacheprovider
~~~

Expected: one sequence test passes with the four visible states and stale 409.

- [ ] **Step 4: Run automated UI and full regressions**

~~~powershell
node --check sdbr/web/planner-workbench.js
python -m compileall -q sdbr
pytest tests/test_api.py::TestOrderCommitmentUiShell tests/test_api.py::TestOrderCommitmentUiReadFlow tests/test_api.py::TestOrderCommitmentUiReevaluation tests/test_api.py::TestOrderCommitmentUiDecisionFlow tests/test_order_commitment_api.py::TestOrderCommitmentUiContract tests/test_order_commitment_api.py::TestOrderCommitmentBrowserSequence -q --basetemp .tmp/pytest-mto-ui-focused -p no:cacheprovider
pytest -q --basetemp .tmp/pytest-full-mto-order-commitment -p no:cacheprovider
git diff --check
~~~

Expected: syntax, focused, full, and diff checks pass. Record actual counts only after observing output.

- [ ] **Step 5: Run the actual PowerShell syntax/API smoke against a real SQLite-backed server**

First parse the real script, not a reconstructed sequence:

~~~powershell
$tokens = $null
$errors = $null
[void][System.Management.Automation.Language.Parser]::ParseFile(
  (Resolve-Path "scripts/seed_mto_order_commitment_browser.ps1"),
  [ref]$tokens,
  [ref]$errors
)
if ($errors.Count -ne 0) { $errors | Format-List; exit 1 }
~~~

In terminal 1:

~~~powershell
New-Item -ItemType Directory -Path ".tmp" -Force | Out-Null
if (Get-NetTCPConnection -LocalPort 8765 -State Listen -ErrorAction SilentlyContinue) {
  throw "Port 8765 is already in use; choose one unused port and pass it to both commands."
}
$env:SDBR_ENVIRONMENT = "test"
$env:SDBR_WORKBENCH_DB_PATH = (
  Join-Path (Resolve-Path ".tmp") "mto-order-commitment-browser.db"
)
python -m uvicorn sdbr.api:app --host 127.0.0.1 --port 8765
~~~

Expected: uvicorn reports `http://127.0.0.1:8765`.

In terminal 2:

~~~powershell
pwsh -File scripts/seed_mto_order_commitment_browser.ps1 `
  -BaseUrl "http://127.0.0.1:8765" `
  -OutputPath ".tmp/mto-order-commitment-browser-fixture.json"
Get-Content -LiteralPath ".tmp/mto-order-commitment-browser-fixture.json"
~~~

Expected fixed source IDs:

- baseline `TST-MTO-RUN-BASELINE`;
- snapshot `TST-MTO-OPS-CURRENT`;
- one ordinary, skipped, accepted, rejected, and stale evaluation ID;
- one accepted reservation batch ID;
- `StaleDecisionStatus = OrderCommitmentEvaluationStale`;
- a numeric final revision.

- [ ] **Step 6: Perform browser-control acceptance**

Load the `browser:control-in-app-browser` skill, then open:

`http://127.0.0.1:8765/planner/workbench#order-commitments`

Verify and capture:

1. Desktop 1280×720: exact nav, four summaries, 11 table columns, ordinary/skipped/accepted/stale-related evidence, drawer, no overlap/clipping. Save `.tmp/mto-order-commitment-desktop.png`.
2. Mobile 390×844: nav drawer, summary, scroll-contained table, detail, re-evaluation controls, and decision dialog remain inside viewport; `document.documentElement.scrollWidth === document.documentElement.clientWidth`. Save `.tmp/mto-order-commitment-mobile.png`.
3. Chinese/English switching translates every recommendation/material/lifecycle/reservation/exception/action label while IDs remain unchanged.
4. Keyboard focus opens route, detail, and dialog; labels/checkboxes have visible focus.
5. Reference threshold warning is visible. Material opt-out blocks blank reason. CCR/material acknowledgements block submission when required.
6. Terminal accepted/rejected/superseded rows have no active controls. Accepted text is `已接受，待正式排程`; boundaries still say no external order, Planning Run, or ERP/MES mutation.
7. A stale decision displays the localized stale message and is not retried.
8. Browser console has no uncaught error.

Stop terminal 1 with Ctrl+C after screenshots/checks; do not leave the server running.

- [ ] **Step 7: Record UI evidence at 5.36 and stop at confirmation gate**

Advance UI header to `5.36`. Change only `UI-COMMIT-001` and record 17.13 from `开发中` to `已验证待用户确认`. Append a 5.36 change row and record exact automated commands/results, URL, desktop/mobile screenshots, bilingual/keyboard/stale/action observations, and unchanged authority boundaries. Do not write `用户已确认`.

- [ ] **Step 8: Commit and request unit-13 confirmation**

~~~powershell
git add -- scripts/seed_mto_order_commitment_browser.ps1 tests/test_order_commitment_api.py docs/ui-specification.md sdbr/web/planner-workbench.html sdbr/web/planner-workbench.js sdbr/web/planner-workbench.css tests/test_api.py
git commit -m "docs: record MTO commitment UI evidence"
~~~

Report commits, observed tests, URL, and `UI-COMMIT-001`. Stop. Do not begin MTA, external-order integration, automatic Planning Run creation, DDAE changes, or another UI unit.

---

## Final Verification Matrix

| Review / requirement | Closing task(s) | Exact evidence |
| --- | --- | --- |
| C1 complete implementation instructions | Tasks 2-28 | Each code-changing task has executable snippets, exact imports/symbol anchors, selectors, and reviewer-sized commits |
| Round-2 C2 current decision facts before acceptance | Tasks 10, 20 | exact capacity candidate/promise/request/deadline/load, material status/request, recommendation, and action-ack facts; selected-window, later-safe, and inbound-cutoff tests |
| Round-2 C3 normal-intake supersession | Tasks 10, 17, 19 | v1-to-v2 atomic supersession, terminal policy, old-decision rejection, and concurrent intake tests |
| C2 no double multiplication; deadline truncation; exact inequality; per-resource windows | Tasks 3-5 | `TestCcrShadowCapacityParity`, `TestCcrShadowPromiseSelection`, Phase 0 regression |
| C3 total matrix including later-safe + skipped and all CCR acknowledgements | Tasks 9, 11, 27 | exhaustive matrix plus conditional recommended action/domain/UI tests |
| C4 exact current snapshot freshness | Tasks 1, 7, 8, 16, 18, 20 | 60-minute boundary, latest/explicit/stale/future/re-evaluation tests |
| C5 exact selectors and bite-sized TDD | Every task | explicit `path::TestClass`/node commands and one reviewable commit per slice |
| C6 reproducible server/browser state | Tasks 14, 28 | public test reset, API-only PowerShell script, SQLite uvicorn, fixed output file/screenshots |
| I1 backend 2.80 and UI 5.35 next | Task 1 | ledger/header scans preserving 2.74-2.79 and 5.34 |
| I2 complete policy/config/algorithm/cutoff identity | Tasks 6, 10, 16 | policy/config and canonical capacity/material cutoff identity tests; never same-ID/content conflict |
| I3 audit vs decision relevance and exact prefilter | Tasks 8, 10, 16, 20 | skipped-material decision basis excludes snapshot/material facts; malformed unrelated rows are prefiltered; exact 08:00-16:00 stale row |
| I4 one server time/actor and canonical decision fingerprint | Tasks 11, 19, 21 | one-field replay conflicts and shared time/actor assertions |
| I5 real MTO Planning Run bridge | Task 22 | real `prepare_mto_acceptance` write set, explicit `PlanningReservationBatchIDs`, completed/failed transitions |
| I6 deep no-external-authority mutation | Tasks 17-21, 28 | every public `WorkbenchStateStore` dataclass field is snapshotted; operation-specific MTO/Phase 0/revision allowlists only |
| I7 complete UI spec/row contract | Tasks 1, 13, 24-25 | section 6.1/11 updates; exact row keys including reservation/exception |
| I8 terminal gating and safe audit | Tasks 13, 26-27 | terminal `AllowedActions=[]`, audit whitelist, no raw payload tests |
| Round-2 I5 action-specific acknowledgements and complete enums | Tasks 9, 13, 25, 27 | Reject requirements are both false; every backend-producible capacity/freshness/load/threshold/coverage/batch/audit/action value has both labels |
| Round-2 M1/M2/M3 practical acceptance evidence | Tasks 14, 22, 28 | rejected terminal seed plus actual PowerShell parse/API smoke; full MTO bridge context; explicit 08:00-16:00 calendar and returned-triple mutation |
| M1 unused normalizer | Task 11 | acceptance explicitly calls `normalize_demand_commitment` |
| M2 exact edit anchors | Every task | file line/symbol anchors in every Files block |
| M3 brittle nav count | Task 24 | exact ordered route/index set and unique route assertion |
| Recommendation only; planner final | Tasks 17-21 | intake no-write tests; authenticated decision endpoint |
| Material default on; planner may disable | Tasks 8, 15, 18, 26 | default, reason, pending/no-allocation, UI request tests |
| AcceptedPendingFormalSchedule; no automatic run | Tasks 11, 21-22, 27-28 | terminal response and explicit-only bridge |
| No DDAE/ERP/MES/master authority mutation | Tasks 1, 21, 23, 28 | deep guards, scans, UI boundary |

## Final Execution Checklist

- [ ] Backend specification starts at 2.80 and later evidence uses 2.81; UI starts at 5.35 and later evidence uses 5.36.
- [ ] `CapacityBucket.capacity_minutes` is never multiplied by `capacity_units`.
- [ ] Both full-bucket aggregate and deadline-truncated temporal limits are enforced.
- [ ] Every Phase 0 row satisfies `WindowStartAt < LatestAllowedCompletionAt <= WindowEndAt`.
- [ ] Matrix covers all capacity/material/threshold states and four acceptance actions.
- [ ] Current snapshot selection, explicit selection, exactly-60, stale, future, and no-current cases are tested.
- [ ] Audit basis retains complete evidence; decision-staleness basis excludes skipped-material snapshot/material facts and unrelated malformed rows.
- [ ] Evaluation identity contains canonical capacity/material cutoffs; time-dependent re-evaluation is duplicate-or-new, never same-ID/different-content.
- [ ] Acceptance compares canonical current decision facts before every mutation.
- [ ] Newer normal intake atomically supersedes prior open logical-order evaluations; terminal and concurrent behavior is tested.
- [ ] Decision fingerprint covers exact canonical fields, excludes server observation time, and replays exactly.
- [ ] Intake, re-evaluation, rejection, and acceptance deep-preserve every external-authority collection.
- [ ] Acceptance creates only shared Phase 0 rows and `AcceptedPendingFormalSchedule`.
- [ ] A real MTO write set freezes/converts/holds through an explicitly selected Planning Run batch.
- [ ] Workbench rows include `ReservationStatus`, `ExceptionStatus`, and lifecycle-safe `AllowedActions`.
- [ ] Audit/detail projection is whitelisted; no raw JSON or client material window exists.
- [ ] API-only browser seed produces ordinary/skipped/accepted/rejected/stale states in the actual SQLite server and the real PowerShell script passes parse/API smoke.
- [ ] Automated/full/browser checks pass and UI stops at `已验证待用户确认`.
- [ ] DDAE contract files, `nofinish/`, and application authority boundaries remain untouched.

## Execution Handoff

Use `superpowers:subagent-driven-development` for one fresh implementer and review gate per task, or `superpowers:executing-plans` for checkpointed inline execution. In either mode, commit each numbered task separately and stop after Task 28 for explicit UI acceptance-unit confirmation.
