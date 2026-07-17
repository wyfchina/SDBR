from __future__ import annotations

import json
from pathlib import Path
import shutil

from fastapi.testclient import TestClient

from sdbr.adventureworks_product_demo_profile import (
    build_adventureworks_product_demo_profile_status,
)
from sdbr.api import create_app
from sdbr.environment_paths import resolve_ddae_interface_contract_root


CONTRACT_ROOT = resolve_ddae_interface_contract_root()
CONTRACT_DIR = CONTRACT_ROOT / "contracts" / "adventureworks-product-demo-v1"


def test_product_demo_profile_accepts_reviewed_manifest_and_demo_authority() -> None:
    status = build_adventureworks_product_demo_profile_status(
        contract_root=CONTRACT_ROOT
    )

    assert status["Validation"]["OverallStatus"] == "AcceptedForProductDemo"
    assert status["ProfileID"] == "ADVENTUREWORKS_PRODUCT_DEMO_V1"
    assert status["Mode"] == "ProductDemoMode"
    assert status["MappingConfidence"] == "ProductDemoOnly"
    assert status["BoundaryGuards"]["MaterialFeasibleProductionClaim"] is False
    assert status["BoundaryGuards"]["NetworkCandidatesExecutable"] is False

    authority = status["DemoAuthority"]["SDBRSchedulingAuthority"]
    assert authority["RowCounts"]["Calendars"] > 0
    assert authority["RowCounts"]["CapacityWindows"] > 0
    assert authority["RowCounts"]["ExecutableRoutingRows"] > 0
    assert authority["RowCounts"]["OperationDurations"] > 0
    assert authority["RowCounts"]["WorkOrderReleaseCandidates"] > 0
    assert authority["MaterialFeasibilityOmission"]["OmissionMode"] == (
        "OmittedForPublicDemo"
    )
    assert authority["SetupChangeoverOmission"]["OmissionMode"] == (
        "NoSetupRulesApplied"
    )

    panel_policy = status["PanelPolicy"]
    assert "public-demo-loop" in panel_policy["ProductDemoModePanels"]
    assert "planning-overview" in panel_policy["PlaceholderPanels"]
    assert "administration" in panel_policy["SampleModeOnlyPanels"]
    assert status["Validation"]["DeadLetters"] == []


def test_product_demo_profile_rejects_missing_sdbr_authority(tmp_path) -> None:
    copied_root = _copy_contract_tree(tmp_path)
    authority_path = (
        copied_root
        / "contracts"
        / "adventureworks-product-demo-v1"
        / "examples"
        / "demo-authority-extension.example.json"
    )
    authority = json.loads(authority_path.read_text(encoding="utf-8"))
    authority["SDBRSchedulingAuthority"]["Calendars"] = []
    authority_path.write_text(json.dumps(authority, indent=2), encoding="utf-8")

    status = build_adventureworks_product_demo_profile_status(
        contract_root=copied_root
    )

    assert status["Validation"]["OverallStatus"] == "Rejected"
    assert any(
        item["Code"] == "DEMO_AUTHORITY_FILE_MISSING"
        and "Calendars" in item["EvidenceRef"]
        for item in status["Validation"]["DeadLetters"]
    )


def test_product_demo_profile_rejects_network_executable_overreach(tmp_path) -> None:
    copied_root = _copy_contract_tree(tmp_path)
    authority_path = (
        copied_root
        / "contracts"
        / "adventureworks-product-demo-v1"
        / "examples"
        / "demo-authority-extension.example.json"
    )
    authority = json.loads(authority_path.read_text(encoding="utf-8"))
    authority["SDBRSchedulingAuthority"]["ExecutableRoutingRows"][0][
        "Owner"
    ] = "NetworkStructureScoring"
    authority_path.write_text(json.dumps(authority, indent=2), encoding="utf-8")

    status = build_adventureworks_product_demo_profile_status(
        contract_root=copied_root
    )

    assert status["Validation"]["OverallStatus"] == "Rejected"
    assert any(
        item["Code"] == "EXECUTABLE_AUTHORITY_OVERREACH"
        for item in status["Validation"]["DeadLetters"]
    )


def test_product_demo_profile_api_and_public_demo_read_model() -> None:
    client = TestClient(create_app())

    profile_response = client.get(
        "/planner/workbench/public-demo/adventureworks-product-demo-profile"
    )
    assert profile_response.status_code == 200
    profile = profile_response.json()["Data"]
    assert profile["Validation"]["OverallStatus"] == "AcceptedForProductDemo"
    assert profile["MappingConfidence"] == "ProductDemoOnly"

    public_demo_response = client.get("/planner/workbench/public-demo/golden-loop")
    assert public_demo_response.status_code == 200
    public_demo = public_demo_response.json()["Data"]
    assert public_demo["ProductDemoMode"]["ProfileID"] == (
        "ADVENTUREWORKS_PRODUCT_DEMO_V1"
    )
    assert public_demo["ProductDemoMode"]["MappingConfidence"] == "ProductDemoOnly"
    assert any(
        "Network Structure Scoring" in item for item in public_demo["NonClaims"]
    )


def test_public_demo_page_contains_product_demo_profile_panel() -> None:
    html = Path("sdbr/web/planner-workbench.html").read_text(encoding="utf-8")
    script = Path("sdbr/web/planner-workbench.js").read_text(encoding="utf-8")
    css = Path("sdbr/web/planner-workbench.css").read_text(encoding="utf-8")

    assert "public-demo-product-profile" in html
    assert ".public-demo-view[hidden] { display: none; }" in css
    assert "public-demo-confidence-title" in html
    assert "productDemoOnlyExplanation" in html
    assert "ProductDemoOnly = the AdventureWorks product-demo profile" in script
    assert "PublicDemoOnly = the evidence level for the underlying public data package" in script
    assert "renderPublicDemoProductProfile(data.ProductDemoMode" in script
    assert html.index("public-demo-validation-title") < html.index(
        "public-demo-product-profile-title"
    )
    assert html.index("public-demo-product-profile-title") < html.index(
        "public-demo-adapter-title"
    )
    assert html.index("public-demo-nonclaims-title") < html.index(
        "public-demo-business-title"
    )


def _copy_contract_tree(tmp_path: Path) -> Path:
    target_root = tmp_path / "contract-root"
    target_dir = target_root / "contracts" / "adventureworks-product-demo-v1"
    shutil.copytree(CONTRACT_DIR, target_dir)
    return target_root
