from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
from typing import Any, Mapping

from sdbr.adventureworks_scheduling_adapter import (
    build_adventureworks_scheduling_adapter_status,
)
from sdbr.ddsop_contracts import (
    build_planning_run_feedback_message,
    build_variance_analysis_feedback_message,
    process_ddsop_config_message,
)


EXPECTED_PACKAGE_CHECKSUM = (
    "20ddd29cb082ba833ff617013257a7270c49b0a6eb1da8b97f5a7240ac900772"
)
PACKAGE_ID = "PUBLIC-DEMO-GOLDEN-DATA-V1"
DEMO_LABELS = [
    "DemoFixture",
    "ReviewedEvidence",
    "Controlled Contract Golden Loop Demo",
    "MappingConfidence = PublicDemoOnly",
]
REVIEWED_CANDIDATES = ("PART-FPGA-SPACE", "WH-ELEC-QA", "EA")


def public_demo_package_root() -> Path:
    return Path(
        os.environ.get(
            "SDBR_PUBLIC_DEMO_PACKAGE_ROOT",
            r"D:\Documents\DDAE_INTERFACE_CONTRACT\data\public-demo-golden-data-v1",
        )
    )


def expected_package_checksum() -> str:
    return os.environ.get(
        "SDBR_PUBLIC_DEMO_PACKAGE_CHECKSUM", EXPECTED_PACKAGE_CHECKSUM
    )


def handoff_input_path(package_root: Path | None = None) -> Path:
    root = package_root or public_demo_package_root()
    return root / "handoff" / "ddae-to-sdbr" / "ddsop-config-inbound-v1-payload.json"


def handoff_output_dir(package_root: Path | None = None) -> Path:
    root = package_root or public_demo_package_root()
    return root / "handoff" / "sdbr-to-ddae"


def planning_feedback_path(package_root: Path | None = None) -> Path:
    return handoff_output_dir(package_root) / "planning-run-feedback.json"


def variance_feedback_path(package_root: Path | None = None) -> Path:
    return handoff_output_dir(package_root) / "variance-analysis-feedback.json"


def validation_summary_path(package_root: Path | None = None) -> Path:
    return handoff_output_dir(package_root) / "validation-summary.json"


def get_public_demo_golden_loop_status() -> dict[str, Any]:
    root = public_demo_package_root()
    package = _package_status(root)
    handoff = _handoff_status(root)
    payload = handoff.get("Payload") if handoff.get("Status") == "Loaded" else None
    validation = (
        _validate_payload(payload, received_at=datetime.now(timezone.utc))
        if isinstance(payload, Mapping)
        else _not_ready_validation(handoff)
    )
    outputs = _output_status(root)
    return {
        "DemoName": "PUBLIC-DEMO-GOLDEN-DATA-V1 Controlled Contract Golden Loop Demo",
        "Labels": DEMO_LABELS,
        "MappingConfidence": "PublicDemoOnly",
        "Package": package,
        "HandoffInput": _without_payload(handoff),
        "Validation": validation,
        "AdventureWorksSchedulingAdapter": (
            build_adventureworks_scheduling_adapter_status(write_artifacts=False)
        ),
        "HandoffOutputs": outputs,
        "NonClaims": _non_claims(),
    }


def run_public_demo_golden_loop() -> dict[str, Any]:
    root = public_demo_package_root()
    status = get_public_demo_golden_loop_status()
    handoff_payload_status = _handoff_status(root)
    payload = handoff_payload_status.get("Payload")
    if not isinstance(payload, Mapping):
        return {
            **status,
            "RunStatus": "NotReady",
            "RunMessage": "DDAE handoff payload is not available yet.",
        }

    validation = _validate_payload(payload, received_at=datetime.now(timezone.utc))
    if validation["OverallStatus"] != "AcceptedForDemo":
        return {
            **status,
            "Validation": validation,
            "RunStatus": "ValidationBlocked",
            "RunMessage": "DDAE handoff payload is not usable for the controlled demo.",
        }

    generated_at = datetime.now(timezone.utc)
    planning_run = _demo_planning_run(payload, generated_at=generated_at)
    planning_feedback = build_planning_run_feedback_message(
        planning_run,
        generated_at=generated_at,
        release_authorizations=[],
        target_system="DDAE",
    )
    variance_feedback = build_variance_analysis_feedback_message(
        planning_run,
        generated_at=generated_at,
        target_system="DDAE",
    )
    validation_summary = {
        "PackageID": PACKAGE_ID,
        "PackageChecksum": expected_package_checksum(),
        "DemoRunID": planning_run["RunID"],
        "RunStatus": "Completed",
        "ValidationStatus": validation["OverallStatus"],
        "Labels": DEMO_LABELS,
        "MappingConfidence": "PublicDemoOnly",
        "FrozenConfiguration": {
            "OperatingModelConfigurationID": planning_run[
                "OperatingModelConfigurationID"
            ],
            "OperatingModelFingerprint": planning_run["OperatingModelFingerprint"],
            "SchedulingConfigurationID": planning_run["SchedulingConfigurationID"],
            "DDMRPConfigurationID": planning_run["DDMRPConfigurationID"],
        },
        "FeedbackMessages": [
            planning_feedback["MessageID"],
            variance_feedback["MessageID"],
        ],
        "NonClaims": _non_claims(),
        "GeneratedAt": generated_at.isoformat(),
    }
    adventureworks_adapter = build_adventureworks_scheduling_adapter_status(
        write_artifacts=True
    )

    out_dir = handoff_output_dir(root)
    out_dir.mkdir(parents=True, exist_ok=True)
    _write_json(planning_feedback_path(root), planning_feedback)
    _write_json(variance_feedback_path(root), variance_feedback)
    _write_json(validation_summary_path(root), validation_summary)

    return {
        **get_public_demo_golden_loop_status(),
        "RunStatus": "Completed",
        "RunMessage": "Controlled demo feedback handoff files were generated.",
        "DemoPlanningRun": planning_run,
        "GeneratedPayloads": {
            "PlanningRunFeedback": planning_feedback,
            "VarianceAnalysisFeedback": variance_feedback,
            "ValidationSummary": validation_summary,
            "AdventureWorksSchedulingAdapter": adventureworks_adapter,
        },
    }


def _package_status(root: Path) -> dict[str, Any]:
    manifest_path = root / "manifest.json"
    if not manifest_path.exists():
        return {
            "PackageRoot": str(root),
            "Status": "Missing",
            "Message": "Frozen public demo package manifest was not found.",
        }
    try:
        manifest = _read_json(manifest_path)
    except (OSError, json.JSONDecodeError) as error:
        return {
            "PackageRoot": str(root),
            "Status": "Invalid",
            "Message": str(error),
        }
    files = sorted((manifest.get("FileRoleMap") or {}).keys())
    missing_files = [name for name in files if not (root / name).exists()]
    package_checksum = str(manifest.get("PackageChecksum", ""))
    checksum_ok = package_checksum == expected_package_checksum()
    return {
        "PackageRoot": str(root),
        "Status": "Ready" if checksum_ok and not missing_files else "NeedsAttention",
        "PackageID": manifest.get("PackageID"),
        "PackageVersion": manifest.get("PackageVersion"),
        "PackageRole": manifest.get("PackageRole"),
        "PackageChecksum": package_checksum,
        "ExpectedPackageChecksum": expected_package_checksum(),
        "ChecksumMatches": checksum_ok,
        "CanonicalFileCount": len(files),
        "MissingFiles": missing_files,
        "RowCountsByFile": manifest.get("RowCountsByFile", {}),
        "CrosswalkFilePresent": (root / "crosswalk.json").exists(),
        "NonClaims": manifest.get("NonClaims", []),
    }


def _handoff_status(root: Path) -> dict[str, Any]:
    path = handoff_input_path(root)
    if not path.exists():
        return {
            "Path": str(path),
            "Status": "Missing",
            "Message": "Waiting for DDAE to write DDSOP-CONFIG-INBOUND-V1 payload.",
        }
    try:
        payload = _read_json(path)
    except (OSError, json.JSONDecodeError) as error:
        return {
            "Path": str(path),
            "Status": "Invalid",
            "Message": str(error),
        }
    return {
        "Path": str(path),
        "Status": "Loaded",
        "MessageID": payload.get("MessageID"),
        "IdempotencyKey": payload.get("IdempotencyKey"),
        "Payload": payload,
    }


def _output_status(root: Path) -> dict[str, Any]:
    outputs = {}
    for label, path in {
        "PlanningRunFeedback": planning_feedback_path(root),
        "VarianceAnalysisFeedback": variance_feedback_path(root),
        "ValidationSummary": validation_summary_path(root),
    }.items():
        outputs[label] = {
            "Path": str(path),
            "Exists": path.exists(),
            "SizeBytes": path.stat().st_size if path.exists() else 0,
        }
    return outputs


def _validate_payload(
    payload: Mapping[str, Any] | None,
    *,
    received_at: datetime,
) -> dict[str, Any]:
    if payload is None:
        return _not_ready_validation({"Status": "Missing"})
    refs = _known_references_from_payload(payload)
    result = process_ddsop_config_message(
        payload,
        received_at=received_at,
        release_policy_ids=refs["ReleasePolicyIDs"],
        calendar_ids=refs["CalendarIDs"],
        scheduling_strategy_ids=refs["SchedulingStrategyIDs"],
        planning_priority_policy_ids=refs["PlanningPriorityPolicyIDs"],
        scheduling_priority_classes=refs["SchedulingPriorityClasses"],
    )
    ack = result.ack
    mapping_hits = _mapping_hits(payload)
    crosswalk_status = _crosswalk_status(public_demo_package_root())
    usable = bool(ack.get("UsableForPlanningRun"))
    accepted = str(ack.get("ProcessingStatus")) == "Accepted"
    all_mapping_hits = all(item["Hit"] for item in mapping_hits)
    overall = (
        "AcceptedForDemo"
        if usable and accepted and all_mapping_hits
        else "Blocked"
    )
    return {
        "OverallStatus": overall,
        "ConfigAck": ack,
        "SchemaValidation": "Passed" if ack.get("ProcessingStatus") != "Rejected" else "Failed",
        "StatusApprovalValidation": (
            "Passed" if usable and accepted else "Failed"
        ),
        "FingerprintValidation": "Passed"
        if ack.get("Fingerprint") == payload.get("Payload", {}).get("Fingerprint")
        else "Failed",
        "CrosswalkValidation": crosswalk_status,
        "ReviewedCandidateMappingHits": mapping_hits,
        "ConfigurationRecord": result.configuration_record,
    }


def _not_ready_validation(handoff: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "OverallStatus": "WaitingForDdaePayload",
        "SchemaValidation": "NotRun",
        "StatusApprovalValidation": "NotRun",
        "FingerprintValidation": "NotRun",
        "CrosswalkValidation": {
            "Status": "NotRun",
            "Message": f"Handoff status: {handoff.get('Status', 'Missing')}",
        },
        "ReviewedCandidateMappingHits": [
            {"CandidateID": candidate, "Hit": False, "Source": "NotRun"}
            for candidate in REVIEWED_CANDIDATES
        ],
        "ConfigAck": None,
    }


def _known_references_from_payload(payload: Mapping[str, Any]) -> dict[str, set[str]]:
    body = payload.get("Payload") if isinstance(payload.get("Payload"), Mapping) else {}
    scheduling = (
        body.get("SchedulingConfiguration")
        if isinstance(body.get("SchedulingConfiguration"), Mapping)
        else {}
    )
    ddmrp = (
        body.get("DDMRPConfiguration")
        if isinstance(body.get("DDMRPConfiguration"), Mapping)
        else {}
    )
    return {
        "ReleasePolicyIDs": {
            str(scheduling.get("ReleasePolicyVersionID"))
        }
        if scheduling.get("ReleasePolicyVersionID")
        else set(),
        "CalendarIDs": {
            str(resource.get("CalendarID"))
            for resource in scheduling.get("ResourceSettings", [])
            if isinstance(resource, Mapping) and resource.get("CalendarID")
        },
        "SchedulingStrategyIDs": {
            str(scheduling.get("SchedulingStrategyID"))
        }
        if scheduling.get("SchedulingStrategyID")
        else set(),
        "PlanningPriorityPolicyIDs": {
            str(ddmrp.get("PlanningPriorityPolicyID"))
        }
        if ddmrp.get("PlanningPriorityPolicyID")
        else set(),
        "SchedulingPriorityClasses": {
            str(part.get("SchedulingPriorityClass"))
            for part in scheduling.get("PartSchedulingSettings", [])
            if isinstance(part, Mapping) and part.get("SchedulingPriorityClass")
        },
    }


def _mapping_hits(payload: Mapping[str, Any]) -> list[dict[str, Any]]:
    payload_text = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    hits = []
    for candidate in REVIEWED_CANDIDATES:
        hits.append(
            {
                "CandidateID": candidate,
                "Hit": candidate in payload_text,
                "Source": "DDSOP-CONFIG-INBOUND-V1 payload",
                "MappingConfidence": "PublicDemoOnly",
            }
        )
    return hits


def _crosswalk_status(root: Path) -> dict[str, Any]:
    crosswalk = root / "crosswalk.json"
    manifest = _read_json(root / "manifest.json") if (root / "manifest.json").exists() else {}
    expected = (manifest.get("ChecksumsByFile") or {}).get("crosswalk.json")
    actual = _file_sha256(crosswalk) if crosswalk.exists() else None
    return {
        "Status": "Passed" if actual and expected == actual else "Failed",
        "Path": str(crosswalk),
        "Exists": crosswalk.exists(),
        "ChecksumMatches": bool(actual and expected == actual),
        "MappingConfidenceRequired": "PublicDemoOnly",
    }


def _demo_planning_run(
    payload: Mapping[str, Any],
    *,
    generated_at: datetime,
) -> dict[str, Any]:
    body = payload["Payload"]
    scheduling = body["SchedulingConfiguration"]
    ddmrp = body["DDMRPConfiguration"]
    run_id = "PUBLIC-DEMO-SDBR-RUN-" + _short_hash(
        str(payload.get("MessageID", "")) + expected_package_checksum()
    )
    schedule = {
        "WorkOrders": [
            {
                "OrderID": "DEMO-WO-PART-FPGA-SPACE-001",
                "ProductID": "PART-FPGA-SPACE",
                "ResourceID": "WH-ELEC-QA",
                "LocationID": "WH-ELEC-QA",
                "PlannedStartAt": "2026-07-01T08:00:00+08:00",
                "PlannedEndAt": "2026-07-01T12:00:00+08:00",
                "BufferZone": "Yellow",
                "BlockedReasons": [],
            }
        ],
        "ReleaseRecommendations": [
            {
                "WorkOrderID": "DEMO-WO-PART-FPGA-SPACE-001",
                "ItemID": "PART-FPGA-SPACE",
                "LocationID": "WH-ELEC-QA",
                "BufferZone": "Yellow",
                "SuggestedReleaseAt": "2026-06-30T08:00:00+08:00",
                "BlockedReasons": [],
                "RecommendationSource": "DemoFixtureReviewedEvidence",
            }
        ],
        "DemoFixture": True,
        "ReviewedEvidence": True,
    }
    fingerprint = "sha256:" + sha256(
        json.dumps(schedule, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()
    return {
        "RunID": run_id,
        "Status": "Completed",
        "SolverBackendID": "DemoFixture",
        "SolverStatus": "Feasible",
        "StartedAt": generated_at.isoformat(),
        "CompletedAt": generated_at.isoformat(),
        "OperatingModelConfigurationID": body["OperatingModelConfigurationID"],
        "OperatingModelFingerprint": body["Fingerprint"],
        "SchedulingConfigurationID": scheduling["SchedulingConfigurationID"],
        "DDMRPConfigurationID": ddmrp["DDMRPConfigurationID"],
        "MasterDataVersionID": PACKAGE_ID,
        "OperationalStateSnapshotID": "PUBLIC-DEMO-GOLDEN-DATA-V1-SNAPSHOT",
        "ScheduleFingerprint": fingerprint,
        "Schedule": schedule,
        "DispatchSummary": {
            "DispatchableOperationCount": 1,
            "ReplanSuggestionCount": 0,
            "QueueJumpSuggestionCount": 0,
        },
        "Labels": DEMO_LABELS,
        "MappingConfidence": "PublicDemoOnly",
        "NonClaims": _non_claims(),
    }


def _without_payload(status: Mapping[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in status.items() if key != "Payload"}


def _non_claims() -> list[str]:
    return [
        "Not ProductionValidated",
        "Not Business Golden Loop readiness",
        "Not production authority",
        "No automatic SDBR production master-data creation",
        "SQL Server / SQL Express is not a demo runtime dependency",
    ]


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _file_sha256(path: Path) -> str | None:
    if not path.exists():
        return None
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _short_hash(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()[:12].upper()
