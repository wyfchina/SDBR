from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from sdbr.adventureworks_scheduling_adapter import (
    ADVENTUREWORKS_ADAPTER_PROFILE_ID,
    CAPACITY_UNIT_NORMALIZATION_RULE_ID,
    MATERIAL_CONSTRAINTS_MODE,
    RESOURCE_IDS,
    SETUP_CHANGEOVER_MODE,
    AdventureWorksAdapterError,
    build_adventureworks_runtime_planning_input_message,
    build_adventureworks_scheduling_adapter_status,
)
from sdbr.api import create_app
from sdbr.ddsop_contracts import DEFAULT_CONTRACT_ROOT
from sdbr.ddsop_runtime_planning_input import process_runtime_planning_input_message


CONTRACT_ROOT = Path(r"D:\Documents\DDAE_INTERFACE_CONTRACT")
PACKAGE_ROOT = CONTRACT_ROOT / "data" / "public-demo-golden-data-v1"


def test_adventureworks_adapter_generates_valid_runtime_package() -> None:
    message, accepted_configuration, summary = (
        build_adventureworks_runtime_planning_input_message(
            package_root=PACKAGE_ROOT,
            contract_root=DEFAULT_CONTRACT_ROOT,
        )
    )

    executable = message["Payload"]["ExecutableSchedulingInputs"]
    assert executable["AdapterProfileID"] == ADVENTUREWORKS_ADAPTER_PROFILE_ID
    assert executable["CapacityUnitNormalizationRuleID"] == (
        CAPACITY_UNIT_NORMALIZATION_RULE_ID
    )
    assert executable["MaterialConstraintsMode"] == MATERIAL_CONSTRAINTS_MODE
    assert executable["MaterialConstraints"] == []
    assert executable["SetupChangeoverMode"] == SETUP_CHANGEOVER_MODE
    assert {row["ResourceID"] for row in executable["ResourceCalendars"]} == set(
        RESOURCE_IDS
    )
    assert summary["RoutingPathCoverage"]["SelectedFixtureWorkOrderCount"] == 7
    assert summary["StorageOnlyLocationGuard"]["StorageOnlyLocationsPromoted"] == []

    result = process_runtime_planning_input_message(
        message,
        received_at=_received_at(),
        accepted_configurations={
            accepted_configuration["Payload"]["OperatingModelConfigurationID"]: (
                accepted_configuration
            )
        },
        contract_root=DEFAULT_CONTRACT_ROOT,
    )

    assert result.processing_status == "Accepted"
    assert result.errors == []
    assert result.package_record is not None
    assert result.package_record["UsableForPlanningRun"] is True


def test_adventureworks_adapter_writes_artifacts_without_sql_runtime(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("SDBR_ADVENTUREWORKS_ADAPTER_OUTPUT_DIR", str(tmp_path))

    status = build_adventureworks_scheduling_adapter_status(
        package_root=PACKAGE_ROOT,
        contract_root=DEFAULT_CONTRACT_ROOT,
        write_artifacts=True,
    )

    assert status["Status"] == "Accepted"
    assert status["BoundedFixtureScheduling"]["Status"] == "ValidatedInputOnly"
    assert status["FormalSolverGate"]["CP-SAT/OR-Tools"] == "Gated"
    assert status["MaterialConstraints"]["Mode"] == MATERIAL_CONSTRAINTS_MODE
    assert status["MaterialConstraints"]["MaterialFeasibleProductionClaim"] is False
    package_path = Path(status["GeneratedPackagePath"])
    assert package_path.exists()
    payload = json.loads(package_path.read_text(encoding="utf-8"))
    assert payload["Payload"]["PackageIdentity"]["MappingConfidence"] == "PublicDemoOnly"
    assert payload["Payload"]["ExecutableSchedulingInputs"]["MaterialConstraintsMode"] == (
        MATERIAL_CONSTRAINTS_MODE
    )
    assert payload["Payload"]["ExecutableSchedulingInputs"]["MaterialConstraints"] == []
    assert payload["Payload"]["ExecutableSchedulingInputs"]["ResourceCalendars"]


def test_adventureworks_adapter_rejects_operation_without_positive_duration(monkeypatch) -> None:
    def broken_json(path: Path):
        data = _real_json(path)
        if path.name == "routings.json":
            for row in data:
                row["ActualResourceHrs"] = 0
                row["ScheduledStartDate"] = "2026-07-01T08:00:00"
                row["ScheduledEndDate"] = "2026-07-01T08:00:00"
        return data

    monkeypatch.setattr("sdbr.adventureworks_scheduling_adapter._read_json", broken_json)

    with pytest.raises(AdventureWorksAdapterError) as error:
        build_adventureworks_runtime_planning_input_message(
            package_root=PACKAGE_ROOT,
            contract_root=DEFAULT_CONTRACT_ROOT,
            max_work_orders=1,
        )

    assert error.value.code == "INVALID_NUMERIC_VALUE"


def test_public_demo_api_exposes_adventureworks_adapter_status(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("SDBR_ADVENTUREWORKS_ADAPTER_OUTPUT_DIR", str(tmp_path))
    client = TestClient(create_app())

    response = client.get("/planner/workbench/public-demo/adventureworks-scheduling-adapter")
    assert response.status_code == 200
    data = response.json()["Data"]
    assert data["Status"] == "Accepted"
    assert data["Declarations"]["MaterialConstraintsMode"] == MATERIAL_CONSTRAINTS_MODE
    assert data["MaterialConstraints"]["MaterialFeasibleProductionClaim"] is False

    run_response = client.post(
        "/planner/workbench/public-demo/adventureworks-scheduling-adapter/run"
    )
    assert run_response.status_code == 200
    run_data = run_response.json()["Data"]
    assert Path(run_data["GeneratedPackagePath"]).exists()


def test_public_demo_business_user_view_is_bottom_section() -> None:
    html = Path("sdbr/web/planner-workbench.html").read_text(encoding="utf-8")
    script = Path("sdbr/web/planner-workbench.js").read_text(encoding="utf-8")

    assert 'data-i18n="businessUserView"' in html
    assert "public-demo-business-steps" in html
    assert html.index("public-demo-nonclaims-title") < html.index(
        "public-demo-business-title"
    )
    assert html.count('data-route="public-demo"') == 1
    assert html.index('data-route="administration"') < html.index(
        'data-route="public-demo"'
    )
    nav_end = html.index("</nav>")
    assert html.rfind('data-route="public-demo"', 0, nav_end) > html.rfind(
        'data-route="administration"', 0, nav_end
    )
    assert "renderPublicDemoBusinessView(data)" in script
    assert "renderPublicDemoProductProfile(data.ProductDemoMode" in script
    assert "MaterialConstraintsMode" in script
    assert "MaterialFeasibleProductionClaim" in script


def _real_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _received_at():
    from datetime import datetime

    return datetime.fromisoformat("2026-06-30T18:45:00+08:00")
