from datetime import datetime, timezone

from sdbr.sdbr_what_if import (
    build_sdbr_what_if_workspace,
    evaluate_sdbr_what_if_scenario,
    simio_recommendation_hint,
)


def _ccr_load():
    return {
        "Summary": {
            "Status": "Protected",
            "ProtectiveCapacityTargetPercent": 80.0,
            "SpecID": "BE-SDBR-005",
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
            "SpecID": "BE-SDBR-005",
        },
        evaluated_at=datetime(2026, 7, 9, 8, 0, tzinfo=timezone.utc),
    )

    assert result["ScenarioType"] == "MTO_EXPEDITE"
    assert result["Impact"]["BeforeLoadPercent"] == 62.5
    assert result["Impact"]["AfterLoadPercent"] == 87.5
    assert result["Impact"]["AfterStatus"] == "Watch"
    assert result["Recommendation"]["Decision"] == "AbsorbWithBufferAndProtectiveCapacity"
    assert result["Recommendation"]["RequiresFormalReplan"] is False


def test_downtime_at_full_effective_capacity_marks_near_limit_boundary():
    result = evaluate_sdbr_what_if_scenario(
        ccr_planned_load=_ccr_load(),
        scenario={
            "ScenarioType": "RESOURCE_DOWNTIME",
            "ResourceID": "CCR-1",
            "BucketDate": "2026-07-10",
            "DowntimeMinutes": 180,
            "Reason": "停机后剩余负荷挤压",
            "SpecID": "BE-SDBR-005",
        },
        evaluated_at=datetime(2026, 7, 9, 8, 0, tzinfo=timezone.utc),
    )

    assert result["Impact"]["CapacityMinutes"] == 480
    assert result["Impact"]["EffectiveCapacityMinutes"] == 300
    assert result["Impact"]["AfterLoadPercent"] == 100.0
    assert result["Impact"]["AfterStatus"] == "NearLimit"


def test_downtime_with_added_recovery_load_marks_overloaded_and_recommends_simio():
    result = evaluate_sdbr_what_if_scenario(
        ccr_planned_load=_ccr_load(),
        scenario={
            "ScenarioType": "RESOURCE_DOWNTIME",
            "ResourceID": "CCR-1",
            "BucketDate": "2026-07-10",
            "DowntimeMinutes": 180,
            "AdditionalLoadMinutes": 30,
            "Reason": "停机与恢复负荷挤压",
            "SpecID": "BE-SDBR-005",
        },
        evaluated_at=datetime(2026, 7, 9, 8, 0, tzinfo=timezone.utc),
    )

    assert result["Impact"]["AfterLoadPercent"] == 110.0
    assert result["Impact"]["AfterStatus"] == "Overloaded"
    assert result["Recommendation"]["RequiresFormalReplan"] is True
    assert result["SimioRecommendation"]["Recommended"] is True


def test_full_day_outage_with_existing_load_marks_overloaded():
    result = evaluate_sdbr_what_if_scenario(
        ccr_planned_load=_ccr_load(),
        scenario={
            "ScenarioType": "RESOURCE_DOWNTIME",
            "ResourceID": "CCR-1",
            "BucketDate": "2026-07-10",
            "DowntimeMinutes": 480,
            "Reason": "全天停机",
            "SpecID": "BE-SDBR-005",
        },
        evaluated_at=datetime(2026, 7, 9, 8, 0, tzinfo=timezone.utc),
    )

    assert result["Impact"]["EffectiveCapacityMinutes"] == 0
    assert result["Impact"]["AfterLoadPercent"] == 999.99
    assert result["Impact"]["AfterStatus"] == "Overloaded"
    assert result["Recommendation"]["Decision"] == "ProtectCcrAndReviewReplan"


def test_missing_ccr_bucket_returns_review_required_without_exception():
    result = evaluate_sdbr_what_if_scenario(
        ccr_planned_load=_ccr_load(),
        scenario={
            "ScenarioType": "SUPPLY_DELAY",
            "ResourceID": "CCR-MISSING",
            "BucketDate": "2026-07-10",
            "AdditionalLoadMinutes": 10,
            "SpecID": "BE-SDBR-005",
        },
    )

    assert result["Impact"] is None
    assert result["Recommendation"]["Decision"] == "ReviewRequired"
    assert result["Recommendation"]["ReasonCode"] == "CCR_BUCKET_NOT_FOUND"


def test_unsupported_scenario_type_returns_review_required_without_evaluation():
    result = evaluate_sdbr_what_if_scenario(
        ccr_planned_load=_ccr_load(),
        scenario={
            "ScenarioType": "UNSUPPORTED",
            "ResourceID": "CCR-1",
            "BucketDate": "2026-07-10",
            "AdditionalLoadMinutes": 10,
            "SpecID": "BE-SDBR-005",
        },
    )

    assert result["ScenarioType"] == "UNSUPPORTED_SCENARIO_TYPE"
    assert result["Impact"] is None
    assert result["Recommendation"]["Decision"] == "ReviewRequired"
    assert result["Recommendation"]["ReasonCode"] == "UNSUPPORTED_SCENARIO_TYPE"


def test_workspace_lists_supported_scenarios_and_red_replenishment_candidates():
    workspace = build_sdbr_what_if_workspace(
        ccr_planned_load=_ccr_load(),
        ddmrp_lines=[
            {
                "PartID": "P-RED",
                "ItemID": "ITEM-RED",
                "LocationID": "MAIN",
                "PlanningStatus": "red",
                "NetFlowPosition": 10,
                "TopOfRed": 20,
                "TopOfYellow": 60,
                "TopOfGreen": 100,
                "SuggestedReplenishmentQty": 90,
                "ProjectedLoadMinutes": 75,
                "RecommendedAction": "建议补货",
                "RawPayload": {"do_not_expose": True},
            },
            {"PartID": "P-GREEN", "PlanningStatus": "green"},
        ],
    )

    assert workspace["SpecID"] == "BE-SDBR-005"
    assert workspace["ScenarioTypes"] == [
        "MTO_EXPEDITE",
        "RESOURCE_DOWNTIME",
        "SUPPLY_DELAY",
        "MTA_RED_REPLENISHMENT_SHOCK",
    ]
    assert workspace["MtaRedCandidates"] == [
        {
            "CandidateID": "MTA-RED-ITEM-RED-MAIN",
            "ItemID": "ITEM-RED",
            "LocationID": "MAIN",
            "Zone": "Red",
            "SuggestedShockQty": 90,
            "ProjectedLoadMinutes": 75,
            "MappedOrderID": None,
            "BusinessMeaning": (
                "MTA 红区补货候选，仅用于评估补货负荷是否冲击约束资源；"
                "不代表已生成补货工单或正式物料可行性声明。"
            ),
        }
    ]
    assert "RawPayload" not in workspace["MtaRedCandidates"][0]
    assert "TopOfRed" not in workspace["MtaRedCandidates"][0]
    assert "TopOfYellow" not in workspace["MtaRedCandidates"][0]
    assert "TopOfGreen" not in workspace["MtaRedCandidates"][0]


def test_mta_red_shock_requires_candidate_and_uses_projected_load():
    missing_candidate = evaluate_sdbr_what_if_scenario(
        ccr_planned_load=_ccr_load(),
        scenario={
            "ScenarioType": "MTA_RED_REPLENISHMENT_SHOCK",
            "ResourceID": "CCR-1",
            "BucketDate": "2026-07-10",
            "AdditionalLoadMinutes": 60,
            "SpecID": "BE-SDBR-005",
        },
    )

    assert missing_candidate["Impact"] is None
    assert missing_candidate["Recommendation"]["ReasonCode"] == "MTA_RED_CANDIDATE_REQUIRED"

    result = evaluate_sdbr_what_if_scenario(
        ccr_planned_load=_ccr_load(),
        scenario={
            "ScenarioType": "MTA_RED_REPLENISHMENT_SHOCK",
            "ResourceID": "CCR-1",
            "BucketDate": "2026-07-10",
            "CandidateID": "MTA-RED-ITEM-RED-MAIN",
            "CandidateItemID": "ITEM-RED",
            "CandidateLocationID": "MAIN",
            "ProjectedLoadMinutes": 75,
            "SuggestedShockQty": 90,
            "SpecID": "BE-SDBR-005",
        },
    )

    assert result["Impact"]["AdditionalLoadMinutes"] == 75
    assert result["Impact"]["Candidate"]["CandidateID"] == "MTA-RED-ITEM-RED-MAIN"
    assert result["Impact"]["Candidate"]["SuggestedShockQty"] == 90


def test_simio_recommendation_hint_includes_chinese_business_conditions():
    hint = simio_recommendation_hint(
        scenario={
            "ScenarioType": "SUPPLY_DELAY",
            "HasRoutingBranches": True,
            "SpecID": "BE-SDBR-005",
        }
    )

    assert hint["Recommended"] is True
    assert "设备/人员/夹具" in " ".join(hint["Conditions"])
    assert "停机、返工、检测失败" in " ".join(hint["Conditions"])
    assert "同一个订单会多次访问同一资源" in " ".join(hint["Conditions"])
    assert "Routing 分支多" in " ".join(hint["Conditions"])
    assert "搬运、等待、批处理、换型" in " ".join(hint["Conditions"])
    assert "排队爆发的动态过程" in " ".join(hint["Conditions"])
    assert "稳定 Simio 模型和数据维护机制" in " ".join(hint["Conditions"])
