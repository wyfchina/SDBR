from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
import sqlite3
import xml.etree.ElementTree as ET

from fastapi.testclient import TestClient

from sdbr.api import create_app
from sdbr.operational_state import create_operational_state_snapshot
from sdbr.schedule_output_governance import build_schedule_output_package
from sdbr.simio_validation import (
    TABLE_MANUFACTURING_ORDERS,
    TABLE_MANUFACTURING_ORDERS_OUTPUT,
    TABLE_RESOURCES,
    TABLE_ROUTINGS,
    _metrics_from_interactive_statistics,
    _parse_simio_result_package,
    build_simio_validation_package,
    ensure_rlm_running,
    run_simio_validation_package,
)
from sdbr.state_store import WorkbenchStateStore


def test_simio_validation_package_writes_spfx_tables(tmp_path):
    store = _simio_test_store()
    planning_run = store.planning_runs["RUN-SIMIO"]
    output_package = _output_package(store)

    package = build_simio_validation_package(
        planning_run=planning_run,
        output_package=output_package,
        output_root=tmp_path,
        generated_at=datetime(2026, 6, 23, 8, tzinfo=timezone.utc),
    )

    assert package["PackageID"].startswith("SIMIO-PKG-RUN-SIMIO-")
    assert package["TemplateSourcePath"].endswith(
        "model\\templates\\simio\\SDBR_Example_Base.xml"
    ) or package["TemplateSourcePath"].endswith(
        "model/templates/simio/SDBR_Example_Base.xml"
    )
    assert package["TemplateID"] == "INLINE-TEMPLATE"
    assert package["TemplateFrozenSnapshot"]["TimeUnitPolicy"] == (
        "APS minutes are written as explicit Simio Minutes."
    )
    assert package["TemplateSourceType"] == "SimioXmlProjectExport"
    assert package["TemplateConversion"]["Status"] == "ConvertedFromXmlExport"
    model_path = Path(str(package["ModelPath"]))
    assert model_path.exists()
    with ZipFile(model_path, "r") as archive:
        names = {name.replace("\\", "/") for name in archive.namelist()}
        assert {
            "Project.xml",
            TABLE_RESOURCES,
            TABLE_ROUTINGS,
            TABLE_MANUFACTURING_ORDERS,
        } <= names
        resources = _rows(archive.read(TABLE_RESOURCES).decode("utf-8"))
        routing_xml = archive.read(TABLE_ROUTINGS).decode("utf-8")
        routings = _rows(routing_xml)
        routing_root = ET.fromstring(routing_xml)
        orders = _rows(archive.read(TABLE_MANUFACTURING_ORDERS).decode("utf-8"))
        model_payloads = b"".join(
            archive.read(name)
            for name in archive.namelist()
            if name.replace("\\", "/").startswith(("Models/Model/", "Models/SchedServer/"))
            and name.endswith(".xml")
        )

    assert {
        "TST_WC_PREP",
        "TST_WC_DRUM",
        "TST_WC_ALT_DRUM",
        "TST_WC_PAINT",
        "TST_WC_ASSY",
        "TST_WC_PACK",
    } <= {row["ResourceName"] for row in resources}
    assert all("-" not in row["ResourceName"] for row in resources)
    assert all(row["WorkSchedule"] == "5DayWeek" for row in resources)
    assert [row["Sequence"] for row in routings] == [
        "TST_WC_DRUM",
        "TST_WC_PACK",
        "TST_SINK",
    ]
    assert [
        prop.attrib.get("Units")
        for prop in routing_root.findall(".//Property")
        if prop.attrib.get("Name") == "ProcessTime"
    ] == ["Minutes", "Minutes", "Minutes"]
    assert [
        (prop.text, prop.attrib.get("Units"))
        for prop in routing_root.findall(".//Property")
        if prop.attrib.get("Name") == "SetupTime"
    ] == [("0", "Minutes"), ("0", "Minutes"), ("0", "Minutes")]
    assert (
        b'<Property Name="TaskProcessingTime" Units="Hours">.1</Property>'
        not in model_payloads
    )
    assert b'<DefaultTupleEntry Name="TaskProcessingTime" Value=".1" />' not in model_payloads
    assert b'<Property Name="TaskProcessingTime" Units="Minutes">0</Property>' in model_payloads
    assert orders[0]["OrderId"] == "TST-WO-100"
    assert orders[0]["MaterialName"] == "TST-FG-A"


def test_mock_simio_runner_returns_completed_result(tmp_path):
    store = _simio_test_store()
    package = build_simio_validation_package(
        planning_run=store.planning_runs["RUN-SIMIO"],
        output_package=_output_package(store),
        output_root=tmp_path,
    )

    result = run_simio_validation_package(package=package, runner_mode="mock")

    assert result["Status"] == "Completed"
    assert result["RunnerBackend"] == "mock"
    assert result["FeasibilityConclusion"] == "Feasible"
    assert result["Kpis"]["OrderCount"] == 1
    assert result["Throughput"]["CompletedOrderCount"] == 1
    assert result["QueueMetrics"]["Status"] == "NotSimulated"
    assert result["Issues"] == []


def test_simio_result_parser_returns_partial_coverage_for_binary_logs(tmp_path):
    store = _simio_test_store()
    package = build_simio_validation_package(
        planning_run=store.planning_runs["RUN-SIMIO"],
        output_package=_output_package(store),
        output_root=tmp_path,
    )
    model_path = Path(str(package["ModelPath"]))

    result = _parse_simio_result_package(
        package=package,
        result_model_path=model_path,
        helper_result={"Status": "Completed"},
        issues=[],
    )

    assert result["FeasibilityConclusion"] == "Infeasible"
    assert result["Throughput"]["Status"] == "Parsed"
    assert result["Throughput"]["OutputSource"] == (
        "Results/Model/TableStates.sqlite:InteractiveValues"
    )
    assert (
        "Results/Model/TableStates.sqlite:InteractiveValues"
        in result["ResultCoverage"]["ParsedSources"]
    )
    assert result["ResultCoverage"]["Status"] == "PartialResultParsed"
    assert result["ResourceUtilization"]["Status"] == "PartialResultParsed"
    assert any(
        issue["Code"] == "SIMIO_UNFINISHED_ORDERS" for issue in result["Issues"]
    )


def test_simio_result_parser_reads_plan_values_from_headless_run(tmp_path):
    store = _simio_test_store()
    package = build_simio_validation_package(
        planning_run=store.planning_runs["RUN-SIMIO"],
        output_package=_output_package(store),
        output_root=tmp_path,
    )
    result_model_path = _result_package_with_plan_values(
        source_path=Path(str(package["ModelPath"])),
        output_path=tmp_path / "result-with-plan-values.spfx",
    )

    result = _parse_simio_result_package(
        package=package,
        result_model_path=result_model_path,
        helper_result={"Status": "Completed"},
        issues=[],
    )

    assert result["FeasibilityConclusion"] == "FeasibleWithWarnings"
    assert result["Throughput"]["Status"] == "Parsed"
    assert result["Throughput"]["OutputSource"] == (
        "Results/Model/TableStates.sqlite:PlanValues"
    )
    assert result["Throughput"]["CompletedOrderCount"] == 1
    assert result["Throughput"]["UnfinishedOrderCount"] == 0
    rows = result["ScheduleAdherence"]["Rows"]
    assert rows[0]["OrderID"] == "TST-WO-100"
    assert rows[0]["RoutingKey"] == "TST-FG-A-10"
    assert rows[1]["RoutingKey"] == "TST-FG-A-20"
    assert rows[0]["ScheduledResource"] == "TST_WC_DRUM"
    assert rows[0]["ActualStartTime"] == "2019-12-02 10:05:00"
    assert rows[1]["EventStatus"] == "OrderCompleted"
    assert result["QueueMetrics"]["Status"] == "ParsedFromSDBROutputRows"
    assert result["QueueMetrics"]["Resources"][0]["AverageWaitMinutes"] == 5
    assert result["WipMetrics"]["Status"] == "ParsedFromSDBROutputRows"
    assert result["WipMetrics"]["SystemMaxWip"] == 1


def test_interactive_statistics_rows_drive_resource_wip_and_queue_metrics():
    rows = [
        _stat_row(
            "DefaultEntity",
            "[Population]",
            "Throughput",
            "Total",
            "NumberCreated",
            4,
        ),
        _stat_row(
            "DefaultEntity",
            "[Population]",
            "Throughput",
            "Total",
            "NumberDestroyed",
            3,
        ),
        _stat_row(
            "DefaultEntity",
            "[Population]",
            "Content",
            "Average",
            "NumberInSystem",
            2.5,
        ),
        _stat_row(
            "DefaultEntity",
            "[Population]",
            "Content",
            "Maximum",
            "NumberInSystem",
            5,
        ),
        _stat_row(
            "TST_WC_DRUM",
            "Processing",
            "Content",
            "Average",
            "NumberInStation",
            1.2,
        ),
        _stat_row(
            "TST_WC_DRUM",
            "Processing",
            "Content",
            "Maximum",
            "NumberInStation",
            2,
        ),
        _stat_row(
            "TST_WC_DRUM",
            "Processing",
            "HoldingTime",
            "Average",
            "TimeInStation",
            0.25,
        ),
        _stat_row(
            "TST_WC_DRUM",
            "Processing",
            "Throughput",
            "Total",
            "NumberEntered",
            4,
        ),
        _stat_row(
            "TST_WC_DRUM",
            "Processing",
            "Throughput",
            "Total",
            "NumberExited",
            3,
        ),
        _stat_row(
            "TST_WC_DRUM",
            "[Resource]",
            "ResourceState",
            "Percent",
            "TimeProcessing",
            50,
        ),
        _stat_row(
            "TST_WC_DRUM",
            "[Resource]",
            "ResourceState",
            "Total",
            "TimeProcessing",
            0.5,
        ),
        _stat_row(
            "TST_WC_DRUM",
            "[Resource]",
            "ResourceState",
            "Total",
            "TimeStarved",
            0.1,
        ),
    ]

    metrics = _metrics_from_interactive_statistics(
        rows=rows,
        resource_ids=["TST_WC_DRUM"],
    )

    assert metrics["ResultCoverageStatus"] == "Parsed"
    assert metrics["Throughput"]["SimioEntityCreated"] == 4
    assert metrics["Throughput"]["SimioEntityDestroyed"] == 3
    assert metrics["WipMetrics"]["Status"] == "ParsedFromInteractiveStatistics"
    assert metrics["WipMetrics"]["SystemAverageWip"] == 2.5
    assert metrics["WipMetrics"]["SystemMaxWip"] == 5
    queue = metrics["QueueMetrics"]["Resources"][0]
    assert queue["AverageStationContent"] == 1.2
    assert queue["MaxStationContent"] == 2
    assert queue["AverageTimeInStationMinutes"] == 15
    utilization = metrics["ResourceUtilization"]["Resources"][0]
    assert utilization["UtilizationPercent"] == 50
    assert utilization["BusyMinutes"] == 30
    assert utilization["StarvedMinutes"] == 6


def test_rlm_detection_reports_already_running_without_start(monkeypatch):
    monkeypatch.setattr("sdbr.simio_validation.os.name", "nt")
    monkeypatch.setattr("sdbr.simio_validation._windows_process_running", lambda _: True)

    status = ensure_rlm_running(rlm_path=Path("missing-rlm.exe"))

    assert status["Status"] == "AlreadyRunning"


def test_simio_validation_api_creates_run_and_updates_governance():
    store = _simio_test_store()
    client = TestClient(create_app(state_store=store))

    templates = client.get("/planner/workbench/simio/templates")
    assert templates.status_code == 200
    assert templates.json()["Data"]["ActiveTemplateID"] == "SDBR-SIMIO-DBR-V1"

    response = client.post(
        "/planner/workbench/simio/validation-runs",
        json={
            "RunID": "RUN-SIMIO",
            "RunnerMode": "mock",
            "TemplateID": "SDBR-SIMIO-DBR-V1",
            "RequestedBy": "planner-1",
            "RequestedAt": "2026-06-23T08:00:00+00:00",
        },
    )

    assert response.status_code == 200
    validation = response.json()["Data"]
    assert validation["Status"] == "Completed"
    assert validation["Package"]["Tables"]["ManufacturingOrders"]["RowCount"] == 1
    assert validation["Package"]["TemplateID"] == "SDBR-SIMIO-DBR-V1"
    assert validation["Package"]["TemplateVersion"] == "2026.06.24"
    assert validation["Result"]["RunnerBackend"] == "mock"
    assert validation["ValidationRunID"] in store.simio_validation_runs
    assert store.audit_events[-1]["Action"] == "SimioValidationRunCreated"

    fetched = client.get(
        f"/planner/workbench/simio/validation-runs/{validation['ValidationRunID']}"
    )
    assert fetched.status_code == 200

    summary = client.get(
        "/planner/workbench/schedule-results/runs/RUN-SIMIO/simio-validation"
    )
    assert summary.status_code == 200
    assert summary.json()["Data"]["Status"] == "Completed"
    assert summary.json()["Data"]["PackageID"] == validation["Package"]["PackageID"]
    assert summary.json()["Data"]["TemplateID"] == "SDBR-SIMIO-DBR-V1"

    governance = client.get(
        "/planner/workbench/schedule-results/runs/RUN-SIMIO/governance"
    )
    assert governance.status_code == 200
    assert governance.json()["Data"]["SimioValidation"]["Status"] == "Completed"


def test_simio_validation_api_rejects_unknown_template():
    store = _simio_test_store()
    client = TestClient(create_app(state_store=store))

    response = client.post(
        "/planner/workbench/simio/validation-runs",
        json={
            "RunID": "RUN-SIMIO",
            "RunnerMode": "mock",
            "TemplateID": "UNKNOWN-TEMPLATE",
        },
    )

    assert response.status_code == 409
    assert response.json()["Data"]["Status"] == "SimioTemplateNotRegistered"


def test_simio_validation_api_rejects_incomplete_run():
    store = _simio_test_store()
    store.planning_runs["RUN-SIMIO"]["Status"] = "Running"
    client = TestClient(create_app(state_store=store))

    response = client.post(
        "/planner/workbench/simio/validation-runs",
        json={"RunID": "RUN-SIMIO", "RunnerMode": "mock"},
    )

    assert response.status_code == 409
    assert response.json()["Data"]["Status"] == "SimioValidationUnavailable"


def _output_package(store: WorkbenchStateStore) -> dict[str, object]:
    return build_schedule_output_package(
        planning_run=store.planning_runs["RUN-SIMIO"],
        master_data_version=store.master_data_versions["MDV-SIMIO"],
        operational_state_snapshot=store.operational_state_snapshots["OPS-SIMIO"],
        release_authorizations=[],
        audit_events=[],
    )


def _simio_test_store() -> WorkbenchStateStore:
    store = WorkbenchStateStore()
    store.master_data_versions["MDV-SIMIO"] = {
        "VersionID": "MDV-SIMIO",
        "Resources": [
            {
                "ResourceID": "TST_WC_DRUM",
                "Name": "Drum",
                "IsConstraint": True,
                "DailyCapacityMinutes": {"2026-06-23": 480},
            },
            {
                "ResourceID": "TST_WC_PACK",
                "Name": "Pack",
                "IsConstraint": False,
                "DailyCapacityMinutes": {"2026-06-23": 480},
            },
        ],
        "Orders": [
            {
                "OrderID": "TST-WO-100",
                "ProductID": "TST-FG-A",
                "Quantity": 1,
                "DueDate": "2026-06-24T08:00:00+00:00",
                "TargetStartDate": "2026-06-23",
            }
        ],
    }
    store.operational_state_snapshots["OPS-SIMIO"] = create_operational_state_snapshot(
        snapshot_id="OPS-SIMIO",
        captured_at=datetime(2026, 6, 23, 7, tzinfo=timezone.utc),
        inventory_buffers=[],
        material_availability=[],
        wip_limits=[],
    )
    store.planning_runs["RUN-SIMIO"] = {
        "RunID": "RUN-SIMIO",
        "ProblemID": "PLAN-SIMIO",
        "Status": "Completed",
        "MasterDataVersionID": "MDV-SIMIO",
        "OperationalStateSnapshotID": "OPS-SIMIO",
        "SolverBackendID": "ortools",
        "SolverStatus": "Optimal",
        "Schedule": {
            "OrderCount": 1,
            "GeneratedAt": "2026-06-23T07:30:00+00:00",
            "GanttRows": [
                {
                    "ResourceID": "TST_WC_DRUM",
                    "ResourceName": "Drum",
                    "IsConstraint": True,
                    "Bars": [
                        {
                            "OrderID": "TST-WO-100",
                            "OperationID": "OP-DRUM",
                            "Start": "2026-06-23T08:00:00+00:00",
                            "End": "2026-06-23T09:00:00+00:00",
                            "DurationMinutes": 60,
                        }
                    ],
                },
                {
                    "ResourceID": "TST_WC_PACK",
                    "ResourceName": "Pack",
                    "IsConstraint": False,
                    "Bars": [
                        {
                            "OrderID": "TST-WO-100",
                            "OperationID": "OP-PACK",
                            "Start": "2026-06-23T09:00:00+00:00",
                            "End": "2026-06-23T09:30:00+00:00",
                            "DurationMinutes": 30,
                        }
                    ],
                },
            ],
            "ReleaseRecommendations": [
                {
                    "OrderID": "TST-WO-100",
                    "SuggestedReleaseDate": "2026-06-23T06:00:00+00:00",
                }
            ],
            "LoadGraphRows": [],
        },
    }
    return store


def _rows(fragment_text: str) -> list[dict[str, str]]:
    root = ET.fromstring(fragment_text)
    rows = []
    for row in root.findall("./Row"):
        values = {}
        for prop in row.findall("./Properties/Property"):
            values[str(prop.attrib["Name"])] = prop.text or ""
        rows.append(values)
    return rows


def _result_package_with_plan_values(*, source_path: Path, output_path: Path) -> Path:
    sqlite_path = output_path.with_suffix(".sqlite")
    connection = sqlite3.connect(sqlite_path)
    try:
        connection.execute(
            """
            CREATE TABLE Table_ManufacturingOrdersOutput_States_PlanValues (
                __RowIndex INTEGER,
                OrderId INTEGER,
                RoutingKey INTEGER,
                ScheduledResource TEXT,
                ScheduledStartTime TEXT,
                ScheduledEndTime TEXT,
                ScheduledQuantity REAL,
                ActualStartTime TEXT,
                ActualEndTime TEXT,
                QueueEnteredTime TEXT,
                QueueWaitMinutes REAL,
                WipAfterStart REAL,
                WipAfterEnd REAL,
                EventStatus TEXT
            )
            """
        )
        connection.executemany(
            """
            INSERT INTO Table_ManufacturingOrdersOutput_States_PlanValues
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    0,
                    0,
                    0,
                    "TST_WC_DRUM",
                    "2019-12-02 10:00:00",
                    "2019-12-02 11:00:00",
                    1.0,
                    "2019-12-02 10:05:00",
                    "2019-12-02 11:02:00",
                    "2019-12-02 10:00:00",
                    5,
                    1,
                    1,
                    "OperationCompleted",
                ),
                (
                    1,
                    0,
                    1,
                    "TST_WC_PACK",
                    "2019-12-02 11:00:00",
                    "2019-12-02 11:30:00",
                    1.0,
                    "2019-12-02 11:03:00",
                    "2019-12-02 11:32:00",
                    "2019-12-02 11:00:00",
                    3,
                    1,
                    0,
                    "OrderCompleted",
                ),
            ],
        )
        connection.execute(
            """
            CREATE TABLE Table_ManufacturingOrdersOutput_States_InteractiveValues (
                __RowIndex INTEGER,
                OrderId INTEGER,
                RoutingKey INTEGER,
                ScheduledResource TEXT,
                ScheduledStartTime TEXT,
                ScheduledEndTime TEXT,
                ScheduledQuantity REAL
            )
            """
        )
        connection.commit()
    finally:
        connection.close()

    with ZipFile(source_path, "r") as source:
        with ZipFile(output_path, "w", compression=ZIP_DEFLATED) as target:
            for info in source.infolist():
                if info.filename.replace("\\", "/") == "Results/Model/TableStates.sqlite":
                    target.writestr("Results/Model/TableStates.sqlite", sqlite_path.read_bytes())
                else:
                    target.writestr(info, source.read(info.filename))
    return output_path


def _stat_row(
    object_name: str,
    data_source: str,
    category: str,
    statistic_type: str,
    data_item: str,
    value: float,
) -> dict[str, object]:
    return {
        "ObjectName": object_name,
        "DataSource": data_source,
        "StatisticCategory": category,
        "StatisticType": statistic_type,
        "DataItem": data_item,
        "Value": value,
        "Average": value,
        "Minimum": value,
        "Maximum": value,
    }
