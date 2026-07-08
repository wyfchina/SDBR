from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
from typing import Any, Iterable, Mapping

from jsonschema import Draft202012Validator


PROFILE_ID = "ADVENTUREWORKS_PRODUCT_DEMO_V1"
CONTRACT_ID = "ADVENTUREWORKS-PRODUCT-DEMO-V1"
EXPECTED_BASE_PACKAGE_ID = "PUBLIC-DEMO-GOLDEN-DATA-V1"
EXPECTED_BASE_PACKAGE_CHECKSUM = (
    "20ddd29cb082ba833ff617013257a7270c49b0a6eb1da8b97f5a7240ac900772"
)
PROFILE_MANIFEST_EXAMPLE = "adventureworks-product-demo-v1-profile-manifest.example.json"
DEMO_AUTHORITY_EXAMPLE = "demo-authority-extension.example.json"
PRODUCT = "SDBR"
ALLOWED_DEFAULT_PANEL_HANDLING = {"Placeholder", "SampleModeOnly"}
REQUIRED_NON_CLAIMS = {
    "NoProductionValidated",
    "NoBusinessGoldenLoopReadiness",
    "NoProductionAuthority",
    "NoProductionMaterialFeasibility",
    "NoProductionRoutingAuthority",
    "NoProductionCalendarAuthority",
    "NoAutomaticDDAEMasterSettingMutation",
    "NoSDBRExecutableConsumptionOfNetworkCandidates",
    "NoFormalProductionCpSatEntry",
}
REQUIRED_SDBR_AUTHORITY_GROUPS = {
    "Calendars": "DEMO_AUTHORITY_FILE_MISSING",
    "CapacityWindows": "DEMO_AUTHORITY_FILE_MISSING",
    "ExecutableRoutingRows": "DEMO_AUTHORITY_FILE_MISSING",
    "OperationDurations": "DEMO_AUTHORITY_FILE_MISSING",
    "WorkOrderReleaseCandidates": "DEMO_AUTHORITY_FILE_MISSING",
    "SchedulingObjectivePolicies": "DEMO_AUTHORITY_FILE_MISSING",
    "DispatchHorizons": "DEMO_AUTHORITY_FILE_MISSING",
}


@dataclass(frozen=True)
class ProfileAssetPaths:
    contract_dir: Path
    profile_schema: Path
    demo_authority_schema: Path
    profile_manifest: Path
    demo_authority: Path


def default_contract_root() -> Path:
    return Path(
        os.environ.get(
            "DDAE_INTERFACE_CONTRACT_ROOT",
            r"D:\Documents\DDAE_INTERFACE_CONTRACT",
        )
    )


def adventureworks_product_demo_contract_dir(contract_root: Path | None = None) -> Path:
    root = contract_root or default_contract_root()
    return root / "contracts" / "adventureworks-product-demo-v1"


def build_adventureworks_product_demo_profile_status(
    *,
    contract_root: Path | None = None,
) -> dict[str, Any]:
    paths = _asset_paths(contract_root)
    dead_letters: list[dict[str, Any]] = []
    manifest: dict[str, Any] = {}
    authority: dict[str, Any] = {}

    try:
        profile_schema = _read_json(paths.profile_schema)
        demo_authority_schema = _read_json(paths.demo_authority_schema)
        manifest = _read_json(paths.profile_manifest)
        authority = _read_json(paths.demo_authority)
    except (OSError, json.JSONDecodeError) as error:
        dead_letters.append(
            _dead_letter(
                code="DEMO_AUTHORITY_FILE_MISSING",
                message=str(error),
                evidence_ref=str(paths.contract_dir),
            )
        )
        return _status_payload(
            paths=paths,
            manifest=manifest,
            authority=authority,
            dead_letters=dead_letters,
        )

    dead_letters.extend(
        _schema_dead_letters(
            validator=Draft202012Validator(profile_schema),
            instance=manifest,
            code="PROFILE_SCHEMA_INVALID",
            evidence_ref=str(paths.profile_manifest),
        )
    )
    dead_letters.extend(
        _schema_dead_letters(
            validator=Draft202012Validator(demo_authority_schema),
            instance=authority,
            code="DEMO_AUTHORITY_SCHEMA_INVALID",
            evidence_ref=str(paths.demo_authority),
        )
    )
    dead_letters.extend(_semantic_dead_letters(manifest=manifest, authority=authority))
    return _status_payload(
        paths=paths,
        manifest=manifest,
        authority=authority,
        dead_letters=dead_letters,
    )


def _asset_paths(contract_root: Path | None) -> ProfileAssetPaths:
    contract_dir = adventureworks_product_demo_contract_dir(contract_root)
    return ProfileAssetPaths(
        contract_dir=contract_dir,
        profile_schema=contract_dir
        / "schema"
        / "adventureworks-product-demo-v1-profile.schema.json",
        demo_authority_schema=contract_dir
        / "schema"
        / "demo-authority-extension.schema.json",
        profile_manifest=contract_dir / "examples" / PROFILE_MANIFEST_EXAMPLE,
        demo_authority=contract_dir / "examples" / DEMO_AUTHORITY_EXAMPLE,
    )


def _status_payload(
    *,
    paths: ProfileAssetPaths,
    manifest: Mapping[str, Any],
    authority: Mapping[str, Any],
    dead_letters: list[dict[str, Any]],
) -> dict[str, Any]:
    sdbr_authority = (
        authority.get("SDBRSchedulingAuthority")
        if isinstance(authority.get("SDBRSchedulingAuthority"), Mapping)
        else {}
    )
    panel_policy = _panel_policy(manifest)
    validation_status = "AcceptedForProductDemo" if not dead_letters else "Rejected"
    return {
        "ProfileID": manifest.get("ProfileID", PROFILE_ID),
        "Mode": manifest.get("Mode"),
        "ProductStatus": manifest.get("ProductStatus"),
        "ProfileStatus": manifest.get("ProfileStatus"),
        "ScenarioLabel": manifest.get("ScenarioLabel"),
        "MappingConfidence": manifest.get("MappingConfidence"),
        "ManifestID": manifest.get("ManifestID"),
        "ManifestVersion": manifest.get("ManifestVersion"),
        "Fingerprint": manifest.get("Fingerprint"),
        "ContractDir": str(paths.contract_dir),
        "ManifestPath": str(paths.profile_manifest),
        "DemoAuthorityPath": str(paths.demo_authority),
        "BasePackageReference": manifest.get("BasePackageReference", {}),
        "DemoAuthority": {
            "DemoAuthorityPackageID": authority.get("DemoAuthorityPackageID"),
            "DemoAuthorityVersion": authority.get("DemoAuthorityVersion"),
            "DemoAuthorityStatus": authority.get("DemoAuthorityStatus"),
            "SchemaRef": (manifest.get("DemoAuthorityExtension") or {}).get(
                "DemoAuthoritySchemaRef"
            ),
            "SDBRSchedulingAuthority": _sdbr_authority_summary(sdbr_authority),
        },
        "PanelPolicy": panel_policy,
        "SourceClassCoverage": _source_class_coverage(authority),
        "EvidenceSamples": _evidence_samples(authority),
        "Validation": {
            "OverallStatus": validation_status,
            "ProfileSchemaValidation": "Passed"
            if not any(item["Code"] == "PROFILE_SCHEMA_INVALID" for item in dead_letters)
            else "Failed",
            "DemoAuthorityValidation": "Passed"
            if not any(
                item["Code"]
                in {
                    "DEMO_AUTHORITY_FILE_MISSING",
                    "DEMO_AUTHORITY_SCHEMA_INVALID",
                    "SOURCE_CLASS_MISSING",
                    "FIELD_OWNER_AMBIGUOUS",
                    "UNKNOWN_SOURCE_CLASS",
                }
                for item in dead_letters
            )
            else "Failed",
            "PanelPolicyValidation": "Passed"
            if not any(item["Code"] == "PANEL_MODE_CONFLICT" for item in dead_letters)
            else "Failed",
            "BoundaryValidation": "Passed"
            if not any(
                item["Code"]
                in {
                    "FORBIDDEN_PRODUCTION_CLAIM",
                    "EXECUTABLE_AUTHORITY_OVERREACH",
                    "SAMPLE_MIXING_DETECTED",
                    "BASE_PACKAGE_CHECKSUM_MISMATCH",
                }
                for item in dead_letters
            )
            else "Failed",
            "DeadLetters": dead_letters,
        },
        "BoundaryGuards": {
            "NoSampleFallback": True,
            "NetworkCandidatesExecutable": False,
            "MaterialFeasibleProductionClaim": False,
            "FormalCpSatOrToolsEntry": "Gated",
            "ExistingFeedbackUse": "DDAEGovernanceReviewContextOnly",
        },
        "NonClaims": list(manifest.get("NonClaims") or []),
    }


def _schema_dead_letters(
    *,
    validator: Draft202012Validator,
    instance: Mapping[str, Any],
    code: str,
    evidence_ref: str,
) -> list[dict[str, Any]]:
    return [
        _dead_letter(
            code=code,
            message=error.message,
            evidence_ref=f"{evidence_ref}#{'/'.join(str(part) for part in error.path)}",
        )
        for error in sorted(validator.iter_errors(instance), key=str)
    ]


def _semantic_dead_letters(
    *,
    manifest: Mapping[str, Any],
    authority: Mapping[str, Any],
) -> list[dict[str, Any]]:
    dead_letters: list[dict[str, Any]] = []
    base = manifest.get("BasePackageReference") or {}
    if base.get("BasePackageID") != EXPECTED_BASE_PACKAGE_ID or base.get(
        "BasePackageChecksum"
    ) != EXPECTED_BASE_PACKAGE_CHECKSUM:
        dead_letters.append(
            _dead_letter(
                code="BASE_PACKAGE_CHECKSUM_MISMATCH",
                message="Product demo profile does not reference the frozen public demo package checksum.",
                evidence_ref="BasePackageReference",
            )
        )
    if manifest.get("ProductStatus") == "ProductionValidated":
        dead_letters.append(
            _dead_letter(
                code="FORBIDDEN_PRODUCTION_CLAIM",
                message="ProductDemoMode profile must not claim ProductionValidated.",
                evidence_ref="ProductStatus",
            )
        )
    if manifest.get("MappingConfidence") != "ProductDemoOnly":
        dead_letters.append(
            _dead_letter(
                code="PROFILE_SCHEMA_INVALID",
                message="AdventureWorks ProductDemo profile must remain ProductDemoOnly.",
                evidence_ref="MappingConfidence",
            )
        )

    sdbr_authority = (
        authority.get("SDBRSchedulingAuthority")
        if isinstance(authority.get("SDBRSchedulingAuthority"), Mapping)
        else {}
    )
    for group_name, code in REQUIRED_SDBR_AUTHORITY_GROUPS.items():
        rows = sdbr_authority.get(group_name)
        if not isinstance(rows, list) or not rows:
            dead_letters.append(
                _dead_letter(
                    code=code,
                    message=f"SDBR DemoAuthority group {group_name} is required for ProductDemoReady.",
                    evidence_ref=f"SDBRSchedulingAuthority.{group_name}",
                )
            )
    dead_letters.extend(_authority_row_dead_letters(authority))
    dead_letters.extend(_omission_dead_letters(sdbr_authority))
    dead_letters.extend(_panel_policy_dead_letters(manifest))
    dead_letters.extend(_non_claim_dead_letters(manifest))
    dead_letters.extend(_network_overreach_dead_letters(sdbr_authority))
    return dead_letters


def _authority_row_dead_letters(authority: Mapping[str, Any]) -> list[dict[str, Any]]:
    dead_letters: list[dict[str, Any]] = []
    for path, row in _walk_authority_rows(authority):
        source_class = row.get("SourceClass")
        owner = row.get("Owner")
        evidence_ref = row.get("EvidenceRef")
        if not source_class or not evidence_ref:
            dead_letters.append(
                _dead_letter(
                    code="SOURCE_CLASS_MISSING",
                    message=f"Authority row {path} lacks SourceClass or EvidenceRef.",
                    evidence_ref=path,
                )
            )
        elif source_class not in {
            "ExtractedFromAdventureWorks",
            "DerivedFromAdventureWorks",
            "DemoAuthority",
            "ContractFixture",
            "Missing",
        }:
            dead_letters.append(
                _dead_letter(
                    code="UNKNOWN_SOURCE_CLASS",
                    message=f"Authority row {path} uses unknown source class {source_class}.",
                    evidence_ref=path,
                )
            )
        if owner not in {
            "ContractAgent",
            "DDAE",
            "SDBR",
            "NetworkStructureScoring",
        }:
            dead_letters.append(
                _dead_letter(
                    code="FIELD_OWNER_AMBIGUOUS",
                    message=f"Authority row {path} lacks a recognized owner.",
                    evidence_ref=path,
                )
            )
    return dead_letters


def _omission_dead_letters(sdbr_authority: Mapping[str, Any]) -> list[dict[str, Any]]:
    omitted = sdbr_authority.get("OmittedGroups") or []
    by_name = {
        str(row.get("GroupName")): row for row in omitted if isinstance(row, Mapping)
    }
    dead_letters: list[dict[str, Any]] = []
    setup = by_name.get("SetupChangeoverRules")
    if not setup or setup.get("OmissionMode") != "NoSetupRulesApplied" or not setup.get(
        "BlockingRule"
    ):
        dead_letters.append(
            _dead_letter(
                code="SOURCE_CLASS_MISSING",
                message="Setup/changeover omission must block setup optimization.",
                evidence_ref="SDBRSchedulingAuthority.OmittedGroups.SetupChangeoverRules",
            )
        )
    material = by_name.get("MaterialFeasibilityStatus")
    if (
        not material
        or material.get("OmissionMode") != "OmittedForPublicDemo"
        or not material.get("BlockingRule")
    ):
        dead_letters.append(
            _dead_letter(
                code="FORBIDDEN_PRODUCTION_CLAIM",
                message="Material feasibility omission must block material-feasible production claims.",
                evidence_ref="SDBRSchedulingAuthority.OmittedGroups.MaterialFeasibilityStatus",
            )
        )
    return dead_letters


def _panel_policy_dead_letters(manifest: Mapping[str, Any]) -> list[dict[str, Any]]:
    dead_letters: list[dict[str, Any]] = []
    defaults = manifest.get("PanelPolicyDefault") or {}
    sdbr_default = defaults.get(PRODUCT)
    if sdbr_default not in ALLOWED_DEFAULT_PANEL_HANDLING:
        dead_letters.append(
            _dead_letter(
                code="PANEL_MODE_CONFLICT",
                message="SDBR omitted panels must default to Placeholder or SampleModeOnly.",
                evidence_ref="PanelPolicyDefault.SDBR",
            )
        )
    sdbr_panels = [
        row
        for row in manifest.get("PanelPolicy", [])
        if isinstance(row, Mapping) and row.get("Product") == PRODUCT
    ]
    if not any(row.get("PanelID") == "public-demo-loop" for row in sdbr_panels):
        dead_letters.append(
            _dead_letter(
                code="PANEL_MODE_CONFLICT",
                message="SDBR public demo loop panel must be explicitly adapted for ProductDemoMode.",
                evidence_ref="PanelPolicy.SDBR.public-demo-loop",
            )
        )
    return dead_letters


def _non_claim_dead_letters(manifest: Mapping[str, Any]) -> list[dict[str, Any]]:
    non_claims = set(manifest.get("NonClaims") or [])
    missing = sorted(REQUIRED_NON_CLAIMS - non_claims)
    if not missing:
        return []
    return [
        _dead_letter(
            code="FORBIDDEN_PRODUCTION_CLAIM",
            message=f"Missing required non-claim: {claim}.",
            evidence_ref="NonClaims",
        )
        for claim in missing
    ]


def _network_overreach_dead_letters(
    sdbr_authority: Mapping[str, Any],
) -> list[dict[str, Any]]:
    executable_groups = [
        "Calendars",
        "CapacityWindows",
        "ExecutableRoutingRows",
        "OperationDurations",
        "WorkOrderReleaseCandidates",
        "SchedulingObjectivePolicies",
        "DispatchHorizons",
    ]
    dead_letters: list[dict[str, Any]] = []
    for group_name in executable_groups:
        for index, row in enumerate(sdbr_authority.get(group_name) or []):
            if not isinstance(row, Mapping):
                continue
            if row.get("Owner") == "NetworkStructureScoring":
                dead_letters.append(
                    _dead_letter(
                        code="EXECUTABLE_AUTHORITY_OVERREACH",
                        message=f"SDBR executable group {group_name} must not use Network candidates as executable authority.",
                        evidence_ref=f"SDBRSchedulingAuthority.{group_name}[{index}]",
                    )
                )
    return dead_letters


def _panel_policy(manifest: Mapping[str, Any]) -> dict[str, Any]:
    sdbr_rows = [
        dict(row)
        for row in manifest.get("PanelPolicy", [])
        if isinstance(row, Mapping) and row.get("Product") == PRODUCT
    ]
    return {
        "DefaultForSDBR": (manifest.get("PanelPolicyDefault") or {}).get(PRODUCT),
        "ProductDemoModePanels": [
            row["PanelID"]
            for row in sdbr_rows
            if row.get("ProductModeHandling") == "ProductDemoMode"
        ],
        "PlaceholderPanels": [
            row["PanelID"]
            for row in sdbr_rows
            if row.get("ProductModeHandling") == "Placeholder"
        ],
        "SampleModeOnlyPanels": [
            row["PanelID"]
            for row in sdbr_rows
            if row.get("ProductModeHandling") == "SampleModeOnly"
        ],
        "Rows": sdbr_rows,
    }


def _sdbr_authority_summary(sdbr_authority: Mapping[str, Any]) -> dict[str, Any]:
    groups = {
        "Calendars": sdbr_authority.get("Calendars") or [],
        "CapacityWindows": sdbr_authority.get("CapacityWindows") or [],
        "ExecutableRoutingRows": sdbr_authority.get("ExecutableRoutingRows") or [],
        "OperationDurations": sdbr_authority.get("OperationDurations") or [],
        "WorkOrderReleaseCandidates": sdbr_authority.get("WorkOrderReleaseCandidates")
        or [],
        "SchedulingObjectivePolicies": sdbr_authority.get(
            "SchedulingObjectivePolicies"
        )
        or [],
        "DispatchHorizons": sdbr_authority.get("DispatchHorizons") or [],
        "SetupChangeoverRules": sdbr_authority.get("SetupChangeoverRules") or [],
        "MaterialFeasibilityStatus": sdbr_authority.get("MaterialFeasibilityStatus")
        or [],
        "OmittedGroups": sdbr_authority.get("OmittedGroups") or [],
    }
    return {
        "RowCounts": {key: len(value) for key, value in groups.items()},
        "RepresentativeRows": {
            key: _sample_rows(value, 2)
            for key, value in groups.items()
            if key not in {"SetupChangeoverRules", "MaterialFeasibilityStatus"}
        },
        "SetupChangeoverOmission": _omission_for(
            groups["OmittedGroups"],
            "SetupChangeoverRules",
        ),
        "MaterialFeasibilityOmission": _omission_for(
            groups["OmittedGroups"],
            "MaterialFeasibilityStatus",
        ),
    }


def _source_class_coverage(authority: Mapping[str, Any]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for _path, row in _walk_authority_rows(authority):
        source_class = str(row.get("SourceClass", "Missing"))
        counts[source_class] = counts.get(source_class, 0) + 1
    return counts


def _evidence_samples(authority: Mapping[str, Any]) -> list[dict[str, Any]]:
    samples = []
    for path, row in _walk_authority_rows(authority):
        samples.append(
            {
                "Path": path,
                "SourceClass": row.get("SourceClass"),
                "EvidenceRef": row.get("EvidenceRef"),
                "Owner": row.get("Owner"),
            }
        )
        if len(samples) >= 8:
            break
    return samples


def _walk_authority_rows(
    value: Any,
    path: str = "DemoAuthority",
) -> Iterable[tuple[str, Mapping[str, Any]]]:
    if isinstance(value, Mapping):
        if {"SourceClass", "EvidenceRef", "Owner"}.intersection(value.keys()):
            yield path, value
        for key, child in value.items():
            yield from _walk_authority_rows(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _walk_authority_rows(child, f"{path}[{index}]")


def _omission_for(rows: list[Any], group_name: str) -> dict[str, Any] | None:
    for row in rows:
        if isinstance(row, Mapping) and row.get("GroupName") == group_name:
            return dict(row)
    return None


def _sample_rows(rows: list[Any], limit: int) -> list[Any]:
    return [dict(row) if isinstance(row, Mapping) else row for row in rows[:limit]]


def _dead_letter(code: str, message: str, evidence_ref: str) -> dict[str, Any]:
    return {
        "ManifestID": None,
        "ProfileID": PROFILE_ID,
        "ErrorCode": code,
        "Code": code,
        "ErrorMessage": message,
        "Message": message,
        "DetectedBy": "SDBR",
        "DetectedAt": None,
        "EvidenceRef": evidence_ref,
        "ReplayAllowed": True,
    }


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))
