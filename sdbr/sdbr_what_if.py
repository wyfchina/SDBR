from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


PROTECTIVE_CAPACITY_TARGET_PERCENT = 80.0
NEAR_LIMIT_PERCENT = 90.0
OVERLOADED_PERCENT = 100.0

SCENARIO_TYPES = [
    "MTO_EXPEDITE",
    "RESOURCE_DOWNTIME",
    "SUPPLY_DELAY",
    "MTA_RED_REPLENISHMENT_SHOCK",
]
UNSUPPORTED_SCENARIO_TYPE = "UNSUPPORTED_SCENARIO_TYPE"


def evaluate_sdbr_what_if_scenario(
    *,
    ccr_planned_load: dict[str, object],
    scenario: dict[str, object],
    evaluated_at: datetime | None = None,
) -> dict[str, object]:
    scenario_type = _scenario_type(scenario)
    if scenario_type == UNSUPPORTED_SCENARIO_TYPE:
        return _review_required_result(
            scenario=scenario,
            evaluated_at=evaluated_at,
            reason_code=UNSUPPORTED_SCENARIO_TYPE,
            business_meaning="不支持的执行层 what-if 场景类型，不能用于 CCR 负荷评估。",
        )
    if scenario_type == "MTA_RED_REPLENISHMENT_SHOCK":
        if not _text(scenario.get("CandidateID")):
            return _review_required_result(
                scenario=scenario,
                evaluated_at=evaluated_at,
                reason_code="MTA_RED_CANDIDATE_REQUIRED",
                business_meaning="请选择一个 MTA 红区补货候选，再评估其对约束资源的冲击。",
            )
        if _scenario_additional_load_minutes(scenario) <= 0:
            return _review_required_result(
                scenario=scenario,
                evaluated_at=evaluated_at,
                reason_code="MTA_RED_SHOCK_LOAD_REQUIRED",
                business_meaning="该 MTA 红区候选缺少可执行负荷分钟，不能判断是否会打爆约束。",
            )

    bucket = _find_bucket(
        ccr_planned_load=ccr_planned_load,
        resource_id=str(scenario.get("ResourceID") or ""),
        bucket_date=str(scenario.get("BucketDate") or ""),
    )
    if bucket is None:
        return _review_required_result(
            scenario=scenario,
            evaluated_at=evaluated_at,
            reason_code="CCR_BUCKET_NOT_FOUND",
            business_meaning="找不到对应的约束资源负荷窗口，不能评估本次执行层冲击。",
        )

    capacity = _non_negative_number(bucket.get("CapacityMinutes"))
    downtime_minutes = _scenario_downtime_minutes(scenario)
    effective_capacity = max(capacity - downtime_minutes, 0.0)
    before_load = _non_negative_number(bucket.get("TotalPlannedLoadMinutes"))
    additional_load = _scenario_additional_load_minutes(scenario)
    after_load = before_load + additional_load
    before_percent = _percent(before_load, capacity)
    after_percent = _percent(after_load, effective_capacity)
    before_status = str(bucket.get("Status") or _status(before_percent))
    after_status = _status(after_percent)

    impact = {
        "ResourceID": bucket.get("ResourceID"),
        "ResourceName": bucket.get("ResourceName"),
        "BucketDate": bucket.get("Date"),
        "CapacityMinutes": _clean_number(capacity),
        "EffectiveCapacityMinutes": _clean_number(effective_capacity),
        "BeforeLoadMinutes": _clean_number(before_load),
        "AdditionalLoadMinutes": _clean_number(additional_load),
        "DowntimeMinutes": _clean_number(downtime_minutes),
        "AfterLoadMinutes": _clean_number(after_load),
        "BeforeLoadPercent": before_percent,
        "AfterLoadPercent": after_percent,
        "BeforeStatus": before_status,
        "AfterStatus": after_status,
    }
    if scenario_type == "MTA_RED_REPLENISHMENT_SHOCK":
        impact["Candidate"] = _scenario_candidate_context(scenario)

    return {
        "Mode": "SDBRNativeWhatIfV1",
        "SpecID": "BE-SDBR-005",
        "ScenarioType": scenario_type,
        "EvaluatedAt": _evaluated_at_text(evaluated_at),
        "Impact": impact,
        "Recommendation": _recommendation(after_status),
        "SimioRecommendation": simio_recommendation_hint(scenario=scenario),
        "Boundary": (
            "S-DBR native execution what-if for BE-SDBR-005; does not mutate the "
            "frozen schedule, does not run CP-SAT, and does not add DDAE protocol fields."
        ),
    }


def build_sdbr_what_if_workspace(
    *,
    ccr_planned_load: dict[str, object],
    ddmrp_lines: list[dict[str, object]],
) -> dict[str, object]:
    return {
        "Mode": "SDBRNativeWhatIfWorkspaceV1",
        "SpecID": "BE-SDBR-005",
        "ScenarioTypes": list(SCENARIO_TYPES),
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
            _mta_red_candidate(item)
            for item in ddmrp_lines
            if str(item.get("PlanningStatus") or "").strip().lower() == "red"
        ],
        "Boundary": (
            "Workspace data for BE-SDBR-005 execution-level S-DBR what-if only; "
            "no DDAE parameter governance, production promise, or schedule mutation."
        ),
    }


def simio_recommendation_hint(
    *,
    scenario: dict[str, object] | None = None,
) -> dict[str, object]:
    scenario = scenario or {}
    scenario_type = _scenario_type(scenario)
    recommended = scenario_type in {"RESOURCE_DOWNTIME", "SUPPLY_DELAY"} or any(
        bool(scenario.get(flag))
        for flag in (
            "UseSimioRecommended",
            "HasCcrGroup",
            "HasDowntimeReworkOrInspectionFailure",
            "HasReentrantRouting",
            "HasRoutingBranches",
            "HasHighQueueDrivers",
            "NeedsDynamicQueueExplanation",
            "HasStableSimioModelDataMaintenance",
        )
    )

    return {
        "Recommended": recommended,
        "Title": "建议使用 Simio 高保真验证的情形",
        "Conditions": [
            "CCR 不是单一资源，而是一组设备/人员/夹具或搬运能力组合。",
            "停机、返工、检测失败对结果影响很大。",
            "同一个订单会多次访问同一资源。",
            "Routing 分支多，路径选择复杂。",
            "搬运、等待、批处理、换型占比很高。",
            "需要展示排队爆发的动态过程。",
            "已经有稳定 Simio 模型和数据维护机制。",
        ],
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


def _review_required_result(
    *,
    scenario: dict[str, object],
    evaluated_at: datetime | None,
    reason_code: str,
    business_meaning: str,
) -> dict[str, object]:
    return {
        "Mode": "SDBRNativeWhatIfV1",
        "SpecID": "BE-SDBR-005",
        "ScenarioType": _scenario_type(scenario),
        "EvaluatedAt": _evaluated_at_text(evaluated_at),
        "Impact": None,
        "Recommendation": {
            "Decision": "ReviewRequired",
            "RequiresFormalReplan": False,
            "ReasonCode": reason_code,
            "BusinessMeaning": business_meaning,
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
            "BusinessMeaning": "冲击消耗保护产能，但未打爆 CCR，优先用缓冲和保护产能吸收。",
        }
    return {
        "Decision": "AbsorbWithExistingPlan",
        "RequiresFormalReplan": False,
        "BusinessMeaning": "冲击仍在保护能力范围内，可按现有计划吸收并继续观察。",
    }


def _status(load_percent: float) -> str:
    if load_percent > OVERLOADED_PERCENT:
        return "Overloaded"
    if load_percent > NEAR_LIMIT_PERCENT:
        return "NearLimit"
    if load_percent > PROTECTIVE_CAPACITY_TARGET_PERCENT:
        return "Watch"
    return "Protected"


def _percent(load_minutes: float, capacity_minutes: float) -> float:
    if capacity_minutes <= 0:
        return 999.99 if load_minutes > 0 else 0.0
    return round(load_minutes / capacity_minutes * 100.0, 2)


def _scenario_type(scenario: dict[str, object]) -> str:
    scenario_type = str(scenario.get("ScenarioType") or "MTO_EXPEDITE")
    return scenario_type if scenario_type in SCENARIO_TYPES else UNSUPPORTED_SCENARIO_TYPE


def _mta_red_candidate(item: dict[str, object]) -> dict[str, object]:
    item_id = _text(item.get("ItemID") or item.get("PartID"))
    location_id = _text(item.get("LocationID"))
    candidate_id = _text(item.get("CandidateID")) or _candidate_id(item_id, location_id)
    suggested_qty = _clean_number(
        _non_negative_number(
            item.get("SuggestedShockQty")
            or item.get("SuggestedReplenishmentQty")
            or item.get("RecommendedOrderQty")
            or item.get("ReplenishmentQty")
        )
    )
    projected_load = _clean_number(
        _non_negative_number(
            item.get("ProjectedLoadMinutes")
            or item.get("MappedLoadMinutes")
            or item.get("LoadMinutes")
        )
    )
    return {
        "CandidateID": candidate_id,
        "ItemID": item_id or None,
        "LocationID": location_id or None,
        "Zone": "Red",
        "SuggestedShockQty": suggested_qty,
        "ProjectedLoadMinutes": projected_load,
        "MappedOrderID": item.get("MappedOrderID") or item.get("MappedWorkOrderID"),
        "BusinessMeaning": (
            "MTA 红区补货候选，仅用于评估补货负荷是否冲击约束资源；"
            "不代表已生成补货工单或正式物料可行性声明。"
        ),
    }


def _scenario_additional_load_minutes(scenario: dict[str, object]) -> float:
    if _scenario_type(scenario) == "MTA_RED_REPLENISHMENT_SHOCK":
        return _non_negative_number(
            scenario.get("AdditionalLoadMinutes")
            or scenario.get("ProjectedLoadMinutes")
            or scenario.get("CandidateProjectedLoadMinutes")
        )
    return _non_negative_number(
        scenario.get("AdditionalLoadMinutes")
        or scenario.get("AddedLoadMinutes")
        or scenario.get("CompressedLoadMinutes")
    )


def _scenario_downtime_minutes(scenario: dict[str, object]) -> float:
    if _scenario_type(scenario) != "RESOURCE_DOWNTIME":
        return 0.0
    return _non_negative_number(
        scenario.get("DowntimeMinutes")
        or scenario.get("UnavailableCapacityMinutes")
        or scenario.get("LostCapacityMinutes")
    )


def _non_negative_number(value: object) -> float:
    try:
        return max(float(value or 0), 0.0)
    except (TypeError, ValueError):
        return 0.0


def _clean_number(value: float) -> int | float:
    return int(value) if value.is_integer() else round(value, 2)


def _scenario_candidate_context(scenario: dict[str, object]) -> dict[str, object]:
    return {
        "CandidateID": _text(scenario.get("CandidateID")) or None,
        "ItemID": _text(scenario.get("CandidateItemID") or scenario.get("ItemID")) or None,
        "LocationID": _text(scenario.get("CandidateLocationID") or scenario.get("LocationID"))
        or None,
        "SuggestedShockQty": _clean_number(
            _non_negative_number(scenario.get("SuggestedShockQty"))
        ),
        "ProjectedLoadMinutes": _clean_number(
            _scenario_additional_load_minutes(scenario)
        ),
    }


def _candidate_id(item_id: str, location_id: str) -> str:
    parts = [part for part in (item_id, location_id) if part]
    return "MTA-RED-" + "-".join(parts or ["UNKNOWN"])


def _text(value: object) -> str:
    return str(value or "").strip()


def _evaluated_at_text(evaluated_at: datetime | None) -> str:
    value = evaluated_at or datetime.now(timezone.utc)
    return value.isoformat()


def _dict_list(value: Any) -> list[dict[str, object]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]
