from __future__ import annotations

import base64
from datetime import datetime, timezone, timedelta
from pathlib import Path
import os
import sqlite3
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from zipfile import ZipFile, ZIP_DEFLATED


DEFAULT_SIMIO_TEMPLATE_ID = "SDBR-SIMIO-DBR-V1"
DEFAULT_SIMIO_TEMPLATE_VERSION = "2026.06.24"
SIMIO_TEMPLATE_PATH = Path("model/templates/simio/SDBR_Example_Base.xml")
SIMIO_LEGACY_TEMPLATE_PATH = Path("model/Simple_DBR_XML/SDBR_Example.xml")
SIMIO_OUTPUT_ROOT = Path(".tmp/simio-validation")
SIMIO_HELPER_COMPILE_SCRIPT = Path("tools/simio_headless_helper/compile.ps1")
SIMIO_HELPER_DLL_PATH = Path(".tmp/simio-headless-helper/SimioHeadlessHelper.dll")
SIMIO_HELPER_TEMP_DIR = Path(".tmp/simio-temp")
SIMIO_RLM_PATH = Path(r"D:\Program Files\Simio LLC\RLM\rlm.exe")
SIMIO_API_DLL_PATH = Path(r"D:\Program Files\Simio LLC\Simio\SimioAPI.dll")

TABLE_RESOURCES = "Models/Model/TableData/Resources.xml"
TABLE_ROUTINGS = "Models/Model/TableData/Routings.xml"
TABLE_MANUFACTURING_ORDERS = "Models/Model/TableData/ManufacturingOrders.xml"
TABLE_MANUFACTURING_ORDERS_OUTPUT = (
    "Models/Model/TableData/ManufacturingOrdersOutput.xml"
)
TABLE_SDBR_RUN_SUMMARY = "Models/Model/TableData/SDBRRunSummary.xml"
SIMIO_MINUTE_FIELDS = {"ProcessTime", "SetupTime"}
SIMIO_ZERO_AUXILIARY_TASK_REPLACEMENTS = (
    (
        b'<Property Name="TaskProcessingTime" Units="Hours">.1</Property>',
        b'<Property Name="TaskProcessingTime" Units="Minutes">0</Property>',
    ),
    (
        b'<DefaultTupleEntry Name="TaskProcessingTime" Value=".1" />',
        b'<DefaultTupleEntry Name="TaskProcessingTime" Value="0" />',
    ),
    (
        b'<DefaultTupleEntry Name="TaskProcessingTime.Units" Value="Hours" />',
        b'<DefaultTupleEntry Name="TaskProcessingTime.Units" Value="Minutes" />',
    ),
)
SDBR_PROCESS_PATHS = (
    "Models/Model/Processes/SDBR_MfgStart.xml",
    "Models/Model/Processes/SDBR_OperationStart.xml",
    "Models/Model/Processes/SDBR_OperationEnd.xml",
    "Models/Model/Processes/SDBR_MfgEnd.xml",
    "Models/Model/Processes/SDBR_RunEndSummary.xml",
)
RESULT_LOG_PATHS = (
    "Results/Model/Interactive_Results.stats",
    "Results/Model/ResourceUsage.log",
    "Results/Model/ResourceState.log",
    "Results/Model/ResourceCapacity.log",
    "Results/Model/Task.log",
    "Results/Model/TaskState.log",
)
TABLE_STATES_SQLITE = "Results/Model/TableStates.sqlite"
SIMIO_STATS_SOURCE = "Results/Model/Interactive_Results.stats"


class SimioValidationError(Exception):
    def __init__(self, *, status: str, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.message = message


def default_simio_template_registry() -> dict[str, dict[str, object]]:
    return {
        DEFAULT_SIMIO_TEMPLATE_ID: {
            "TemplateID": DEFAULT_SIMIO_TEMPLATE_ID,
            "TemplateName": "SDBR Example Base",
            "TemplateVersion": DEFAULT_SIMIO_TEMPLATE_VERSION,
            "TemplatePath": str(SIMIO_TEMPLATE_PATH),
            "TemplateSourceType": _template_source_type(SIMIO_TEMPLATE_PATH),
            "RuntimeFormat": "SimioXmlProjectExport",
            "Status": "Active",
            "IsDefault": True,
            "ModelName": "Model",
            "TimeUnitPolicy": "APS minutes are written as explicit Simio Minutes.",
            "DesktopValidationStatus": "PendingManualCheck",
            "Notes": (
                "Product-managed Simio validation template. Copy this template "
                "to a derived package for every validation run."
            ),
        }
    }


def resolve_simio_template(
    *,
    template_registry: dict[str, dict[str, object]] | None = None,
    active_template_id: str | None = None,
    requested_template_id: str | None = None,
) -> dict[str, object]:
    registry = default_simio_template_registry()
    registry.update(template_registry or {})
    template_id = requested_template_id or active_template_id
    if not template_id:
        template_id = next(
            (
                str(item.get("TemplateID"))
                for item in registry.values()
                if item.get("IsDefault") and item.get("Status") == "Active"
            ),
            DEFAULT_SIMIO_TEMPLATE_ID,
        )
    template = registry.get(str(template_id))
    if template is None:
        raise SimioValidationError(
            status="SimioTemplateNotRegistered",
            message=f"Simio template is not registered: {template_id}.",
        )
    if template.get("Status") != "Active":
        raise SimioValidationError(
            status="SimioTemplateInactive",
            message=f"Simio template is not active: {template_id}.",
        )
    path = Path(str(template.get("TemplatePath") or ""))
    if not path.exists():
        raise SimioValidationError(
            status="SimioTemplateMissing",
            message=f"Simio template was not found: {path}.",
        )
    return {
        **template,
        "TemplateID": str(template.get("TemplateID") or template_id),
        "TemplateVersion": str(template.get("TemplateVersion") or "Unversioned"),
        "TemplatePath": str(path),
        "TemplateSourceType": str(
            template.get("TemplateSourceType") or _template_source_type(path)
        ),
    }


def _template_record_from_path(template_path: Path) -> dict[str, object]:
    return {
        "TemplateID": "INLINE-TEMPLATE",
        "TemplateName": template_path.stem,
        "TemplateVersion": "Unversioned",
        "TemplatePath": str(template_path),
        "TemplateSourceType": _template_source_type(template_path),
        "RuntimeFormat": _template_source_type(template_path),
        "Status": "Active",
        "IsDefault": False,
        "TimeUnitPolicy": "APS minutes are written as explicit Simio Minutes.",
        "DesktopValidationStatus": "Unknown",
    }


def build_simio_validation_package(
    *,
    planning_run: dict[str, object],
    output_package: dict[str, object],
    template_path: Path = SIMIO_TEMPLATE_PATH,
    template_record: dict[str, object] | None = None,
    output_root: Path = SIMIO_OUTPUT_ROOT,
    generated_at: datetime | None = None,
) -> dict[str, object]:
    if planning_run.get("Status") != "Completed" or not isinstance(
        planning_run.get("Schedule"), dict
    ):
        raise SimioValidationError(
            status="SimioValidationUnavailable",
            message="Simio validation requires a Completed Planning Run with a schedule.",
        )
    template = template_record or _template_record_from_path(template_path)
    template_path = Path(str(template.get("TemplatePath") or template_path))
    if not template_path.exists():
        raise SimioValidationError(
            status="SimioTemplateMissing",
            message=f"Simio template was not found: {template_path}.",
        )
    if output_package.get("Status") == "OutputPackageUnavailable":
        raise SimioValidationError(
            status="SimioOutputPackageUnavailable",
            message="Simio validation requires an available internal output package.",
        )

    generated = generated_at or datetime.now(timezone.utc)
    run_id = str(planning_run.get("RunID"))
    fingerprint = str(output_package.get("ScheduleFingerprint") or "")
    package_id = f"SIMIO-PKG-{run_id}-{fingerprint[:12] or 'NOFINGERPRINT'}"
    package_dir = output_root / run_id
    package_dir.mkdir(parents=True, exist_ok=True)
    model_path = package_dir / f"SDBR_Example_{run_id}.spfx"

    time_mapping = _simio_time_mapping(
        output_package=output_package,
        template_path=template_path,
    )
    resources = _resource_rows(
        output_package=output_package,
        template_path=template_path,
    )
    routings = _routing_rows(output_package=output_package)
    orders = _manufacturing_order_rows(
        output_package=output_package,
        time_mapping=time_mapping,
    )
    conversion = _write_simio_package_tables(
        template_path=template_path,
        output_path=model_path,
        resources=resources,
        routings=routings,
        orders=orders,
    )
    issues = _package_issues(
        resources=resources,
        routings=routings,
        orders=orders,
        model_path=model_path,
    )
    return {
        "PackageID": package_id,
        "PackageType": "SimioValidationPackage",
        "RunID": run_id,
        "ProblemID": planning_run.get("ProblemID"),
        "ScheduleFingerprint": output_package.get("ScheduleFingerprint"),
        "GeneratedAt": generated.isoformat(),
        "TemplateID": template.get("TemplateID"),
        "TemplateName": template.get("TemplateName"),
        "TemplateVersion": template.get("TemplateVersion"),
        "TemplatePath": str(template_path),
        "TemplateSourcePath": str(template_path),
        "TemplateSourceType": template.get("TemplateSourceType")
        or _template_source_type(template_path),
        "TemplateFrozenSnapshot": {
            "TemplateID": template.get("TemplateID"),
            "TemplateName": template.get("TemplateName"),
            "TemplateVersion": template.get("TemplateVersion"),
            "TemplatePath": str(template_path),
            "TemplateSourceType": template.get("TemplateSourceType")
            or _template_source_type(template_path),
            "RuntimeFormat": template.get("RuntimeFormat"),
            "ModelName": template.get("ModelName"),
            "TimeUnitPolicy": template.get("TimeUnitPolicy"),
            "DesktopValidationStatus": template.get("DesktopValidationStatus"),
        },
        "TemplateConversion": conversion,
        "TimeMapping": time_mapping,
        "ModelPath": str(model_path),
        "ResultModelPath": str(package_dir / f"SDBR_Example_{run_id}_result.spfx"),
        "Tables": {
            "Resources": {"Path": TABLE_RESOURCES, "RowCount": len(resources)},
            "Routings": {"Path": TABLE_ROUTINGS, "RowCount": len(routings)},
            "ManufacturingOrders": {
                "Path": TABLE_MANUFACTURING_ORDERS,
                "RowCount": len(orders),
            },
            "ManufacturingOrdersOutput": {
                "Path": TABLE_MANUFACTURING_ORDERS_OUTPUT,
                "Role": "Simio process and assignment output",
            },
            "SDBRRunSummary": {
                "Path": TABLE_SDBR_RUN_SUMMARY,
                "Role": "Run-ending process summary",
            },
        },
        "ResourceIDs": sorted({str(item["ResourceName"]) for item in resources}),
        "OrderIDs": sorted({str(item["OrderId"]) for item in orders}),
        "ProductIDs": sorted({str(item["MaterialName"]) for item in orders}),
        "Issues": issues,
        "ReferenceBasis": [
            "model/Simio API Reference Guide.pdf",
            "https://github.com/SimioLLC/SimioApiHelper",
            str(SIMIO_API_DLL_PATH),
        ],
    }


def create_simio_validation_run(
    *,
    planning_run: dict[str, object],
    output_package: dict[str, object],
    runner_mode: str = "auto",
    requested_by: str = "planner",
    requested_at: datetime | None = None,
    template_path: Path = SIMIO_TEMPLATE_PATH,
    template_registry: dict[str, dict[str, object]] | None = None,
    active_template_id: str | None = None,
    template_id: str | None = None,
    output_root: Path = SIMIO_OUTPUT_ROOT,
) -> dict[str, object]:
    requested = requested_at or datetime.now(timezone.utc)
    template_record = (
        resolve_simio_template(
            template_registry=template_registry,
            active_template_id=active_template_id,
            requested_template_id=template_id,
        )
        if template_registry is not None or active_template_id is not None or template_id
        else _template_record_from_path(template_path)
    )
    package = build_simio_validation_package(
        planning_run=planning_run,
        output_package=output_package,
        template_path=Path(str(template_record.get("TemplatePath") or template_path)),
        template_record=template_record,
        output_root=output_root,
        generated_at=requested,
    )
    mode = runner_mode if runner_mode in {"auto", "mock", "local"} else "auto"
    result = run_simio_validation_package(
        package=package,
        runner_mode=mode,
        evaluated_at=requested,
    )
    validation_run_id = f"SIMIO-RUN-{package['RunID']}-{str(requested.timestamp()).replace('.', '')}"
    return {
        "ValidationRunID": validation_run_id,
        "RunID": package["RunID"],
        "ProblemID": package["ProblemID"],
        "ScheduleFingerprint": package["ScheduleFingerprint"],
        "RunnerMode": mode,
        "RequestedBy": requested_by,
        "RequestedAt": requested.isoformat(),
        "Status": result["Status"],
        "Package": package,
        "Result": result,
    }


def run_simio_validation_package(
    *,
    package: dict[str, object],
    runner_mode: str,
    evaluated_at: datetime | None = None,
) -> dict[str, object]:
    evaluated = evaluated_at or datetime.now(timezone.utc)
    if runner_mode == "mock":
        return _mock_runner_result(package=package, evaluated_at=evaluated)
    if runner_mode == "local":
        return _local_runner_result(package=package, evaluated_at=evaluated)

    local = _local_runner_result(package=package, evaluated_at=evaluated)
    if local["Status"] in {"Completed", "Failed"}:
        return local
    fallback = _mock_runner_result(package=package, evaluated_at=evaluated)
    return {
        **fallback,
        "RunnerMode": "auto",
        "FallbackReason": local,
    }


def latest_simio_validation_for_run(
    *,
    simio_validation_runs: dict[str, dict[str, object]],
    run_id: str,
) -> dict[str, object] | None:
    scoped = [
        item
        for item in simio_validation_runs.values()
        if str(item.get("RunID")) == run_id
    ]
    if not scoped:
        return None
    return max(scoped, key=lambda item: str(item.get("RequestedAt", "")))


def summarize_simio_validation(
    *,
    simio_validation_runs: dict[str, dict[str, object]],
    run_id: str,
) -> dict[str, object]:
    latest = latest_simio_validation_for_run(
        simio_validation_runs=simio_validation_runs,
        run_id=run_id,
    )
    if latest is None:
        return {
            "Status": "NotRequested",
            "Message": "Simio validation has not been requested for this planning run.",
            "LatestValidationRunID": None,
        }
    result = _dict(latest.get("Result"))
    package = _dict(latest.get("Package"))
    return {
        "Status": latest.get("Status"),
        "LatestValidationRunID": latest.get("ValidationRunID"),
        "RunnerMode": latest.get("RunnerMode"),
        "RunnerBackend": result.get("RunnerBackend"),
        "RequestedAt": latest.get("RequestedAt"),
        "RequestedBy": latest.get("RequestedBy"),
        "PackageID": package.get("PackageID"),
        "ModelPath": package.get("ModelPath"),
        "ResultModelPath": result.get("ResultModelPath"),
        "TemplateID": package.get("TemplateID"),
        "TemplateName": package.get("TemplateName"),
        "TemplateVersion": package.get("TemplateVersion"),
        "TemplateSourcePath": package.get("TemplateSourcePath"),
        "TemplateFrozenSnapshot": package.get("TemplateFrozenSnapshot"),
        "FeasibilityConclusion": result.get("FeasibilityConclusion"),
        "ScheduleFingerprint": latest.get("ScheduleFingerprint"),
        "RlmStatus": result.get("RlmStatus"),
        "IssueCount": len(_dict_list(result.get("Issues"))),
        "Issues": _dict_list(result.get("Issues")),
        "Kpis": result.get("Kpis"),
        "Throughput": result.get("Throughput"),
        "QueueMetrics": result.get("QueueMetrics"),
        "WipMetrics": result.get("WipMetrics"),
        "ResourceUtilization": result.get("ResourceUtilization"),
        "ScheduleAdherence": result.get("ScheduleAdherence"),
        "ResultCoverage": result.get("ResultCoverage"),
        "Message": result.get("Message"),
    }


def ensure_rlm_running(
    *,
    rlm_path: Path = SIMIO_RLM_PATH,
    start_if_missing: bool = True,
) -> dict[str, object]:
    if os.name != "nt":
        return {
            "Status": "NotApplicable",
            "Message": "RLM process management is only available on Windows.",
        }
    if _windows_process_running("rlm.exe"):
        return {
            "Status": "AlreadyRunning",
            "Path": str(rlm_path),
            "Message": "Simio RLM license process is already running.",
        }
    if not start_if_missing:
        return {
            "Status": "Missing",
            "Path": str(rlm_path),
            "Message": "Simio RLM license process is not running.",
        }
    if not rlm_path.exists():
        return {
            "Status": "StartFailed",
            "Path": str(rlm_path),
            "Message": "Simio RLM executable was not found.",
        }
    try:
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        subprocess.Popen(
            [str(rlm_path)],
            cwd=str(rlm_path.parent),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=creationflags,
        )
    except OSError as error:
        return {
            "Status": "StartFailed",
            "Path": str(rlm_path),
            "Message": str(error),
        }
    return {
        "Status": "Started",
        "Path": str(rlm_path),
        "Message": "Simio RLM license process was started.",
    }


def _write_simio_package_tables(
    *,
    template_path: Path,
    output_path: Path,
    resources: list[dict[str, object]],
    routings: list[dict[str, object]],
    orders: list[dict[str, object]],
) -> dict[str, object]:
    replacements = {
        TABLE_RESOURCES: _fragment_xml(resources),
        TABLE_ROUTINGS: _fragment_xml(routings),
        TABLE_MANUFACTURING_ORDERS: _fragment_xml(orders),
    }
    if template_path.suffix.lower() == ".xml":
        return _write_xml_export_as_spfx(
            template_path=template_path,
            output_path=output_path,
            replacements=replacements,
        )
    if template_path.suffix.lower() != ".spfx":
        raise SimioValidationError(
            status="SimioTemplateConversionUnavailable",
            message=(
                "Simio template must be a .spfx package or a Simio XML project "
                f"export: {template_path}."
            ),
        )
    return _write_spfx_tables(
        template_path=template_path,
        output_path=output_path,
        replacements=replacements,
    )


def _write_spfx_tables(
    *,
    template_path: Path,
    output_path: Path,
    replacements: dict[str, str],
) -> dict[str, object]:
    replaced: list[str] = []
    with ZipFile(template_path, "r") as source:
        with ZipFile(output_path, "w", compression=ZIP_DEFLATED) as target:
            for info in source.infolist():
                normalized = _simio_package_path(info.filename)
                if normalized in replacements:
                    target.writestr(normalized, replacements[normalized])
                    replaced.append(normalized)
                else:
                    target.writestr(
                        info,
                        _normalize_simio_validation_payload(
                            normalized,
                            source.read(info.filename),
                        ),
                    )
    return {
        "Status": "CopiedFromSpfx",
        "SourcePath": str(template_path),
        "OutputPath": str(output_path),
        "ReplacedTables": sorted(replaced),
    }


def _write_xml_export_as_spfx(
    *,
    template_path: Path,
    output_path: Path,
    replacements: dict[str, str],
) -> dict[str, object]:
    try:
        tree = ET.parse(template_path)
    except ET.ParseError as error:
        raise SimioValidationError(
            status="SimioTemplateConversionUnavailable",
            message=f"Simio XML template could not be parsed: {error}.",
        ) from error

    root = tree.getroot()
    namespace = _xml_namespace(root.tag)
    files_tag = f"{{{namespace}}}Files" if namespace else "Files"
    file_tag = f"{{{namespace}}}File" if namespace else "File"
    binary_tag = f"{{{namespace}}}BinaryData" if namespace else "BinaryData"
    files_node = root.find(f".//{files_tag}")
    if files_node is None:
        raise SimioValidationError(
            status="SimioTemplateConversionUnavailable",
            message="Simio XML template does not contain an embedded Files section.",
        )
    parent_map = {child: parent for parent in root.iter() for child in parent}
    files_parent = parent_map.get(files_node)
    if files_parent is None:
        raise SimioValidationError(
            status="SimioTemplateConversionUnavailable",
            message="Simio XML Files section could not be detached.",
        )

    embedded: list[tuple[str, bytes]] = []
    for file_node in files_node.findall(file_tag):
        name = _simio_package_path(str(file_node.attrib.get("Name") or ""))
        binary_node = file_node.find(binary_tag)
        if not name or binary_node is None or not (binary_node.text or "").strip():
            continue
        embedded.append((name, base64.b64decode(binary_node.text.strip())))

    files_parent.remove(files_node)
    if namespace:
        ET.register_namespace("", namespace)
    project_xml = ET.tostring(
        root,
        encoding="utf-8",
        xml_declaration=True,
        short_empty_elements=False,
    )
    replaced: list[str] = []
    with ZipFile(output_path, "w", compression=ZIP_DEFLATED) as target:
        target.writestr("Project.xml", project_xml)
        for name, payload in embedded:
            if name in replacements:
                target.writestr(name, replacements[name])
                replaced.append(name)
            else:
                target.writestr(
                    name,
                    _normalize_simio_validation_payload(name, payload),
                )
    return {
        "Status": "ConvertedFromXmlExport",
        "SourcePath": str(template_path),
        "OutputPath": str(output_path),
        "EmbeddedFileCount": len(embedded),
        "ReplacedTables": sorted(replaced),
    }


def _normalize_simio_validation_payload(name: str, payload: bytes) -> bytes:
    if not name.endswith(".xml"):
        return payload
    if "Models/Model/" not in name and "Models/SchedServer/" not in name:
        return payload
    normalized = payload
    for old, new in SIMIO_ZERO_AUXILIARY_TASK_REPLACEMENTS:
        normalized = normalized.replace(old, new)
    return normalized


def _resource_rows(
    *,
    output_package: dict[str, object],
    template_path: Path | None = None,
) -> list[dict[str, object]]:
    rows: dict[str, dict[str, object]] = {}
    if template_path is not None:
        for item in _template_table_rows(
            template_path=template_path,
            table_path=TABLE_RESOURCES,
        ):
            resource_id = _simio_resource_id(item.get("ResourceName"))
            if not resource_id:
                continue
            rows[resource_id] = {
                key: value
                for key, value in item.items()
                if key != "__RowIndex"
            }
            rows[resource_id]["ResourceName"] = resource_id
    for item in _dict_list(output_package.get("ResourceLoadSummary")):
        resource_id = _simio_resource_id(item.get("ResourceID"))
        rows.setdefault(resource_id, {})
        rows[resource_id].update(
            {
                "ResourceName": resource_id,
                "ObjectType": rows[resource_id].get("ObjectType") or "SchedServer",
                "WorkSchedule": rows[resource_id].get("WorkSchedule") or "5DayWeek",
                "CostRate": rows[resource_id].get("CostRate") or 0,
            }
        )
    for operation in _dict_list(output_package.get("Operations")):
        resource_id = _simio_resource_id(operation.get("ResourceID"))
        if resource_id not in rows:
            rows[resource_id] = {
                "ResourceName": resource_id,
                "ObjectType": "SchedServer",
                "WorkSchedule": "5DayWeek",
                "CostRate": 0,
            }
    return sorted(rows.values(), key=lambda item: str(item["ResourceName"]))


def _routing_rows(*, output_package: dict[str, object]) -> list[dict[str, object]]:
    work_orders_by_id = {
        str(item.get("OrderID")): item for item in _dict_list(output_package.get("WorkOrders"))
    }
    operations_by_product: dict[str, list[dict[str, object]]] = {}
    for operation in _dict_list(output_package.get("Operations")):
        order_id = str(operation.get("OrderID"))
        product_id = str(work_orders_by_id.get(order_id, {}).get("ProductID") or order_id)
        operations_by_product.setdefault(product_id, []).append(operation)

    rows: list[dict[str, object]] = []
    for product_id, operations in sorted(operations_by_product.items()):
        ordered = sorted(
            operations,
            key=lambda item: (
                str(item.get("Start", "")),
                str(item.get("End", "")),
                str(item.get("OperationID", "")),
            ),
        )
        for index, operation in enumerate(ordered, start=1):
            route_number = index * 10
            rows.append(
                {
                    "RoutingKey": f"{product_id}-{route_number}",
                    "MaterialName": product_id,
                    "RouteNumber": route_number,
                    "Sequence": _simio_resource_id(operation.get("ResourceID")),
                    "SetupTime": 0,
                    "ProcessTime": int(operation.get("DurationMinutes") or 0),
                    "ApsOperationID": operation.get("OperationID"),
                    "ApsOrderID": operation.get("OrderID"),
                }
            )
        rows.append(
            {
                "RoutingKey": f"{product_id}-{(len(ordered) + 1) * 10}",
                "MaterialName": product_id,
                "RouteNumber": (len(ordered) + 1) * 10,
                "Sequence": "TST_SINK",
                "SetupTime": 0,
                "ProcessTime": 0,
            }
        )
    return rows


def _manufacturing_order_rows(
    *,
    output_package: dict[str, object],
    time_mapping: dict[str, object] | None = None,
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for order in _dict_list(output_package.get("WorkOrders")):
        rows.append(
            {
                "OrderId": order.get("OrderID"),
                "MaterialName": order.get("ProductID") or order.get("OrderID"),
                "Quantity": order.get("Quantity") or 1,
                "ReleaseDate": _simio_datetime(
                    order.get("SuggestedReleaseAt") or order.get("ScheduledStart"),
                    time_mapping=time_mapping,
                ),
                "DueDate": _simio_datetime(
                    order.get("DueDate") or order.get("ScheduledEnd"),
                    time_mapping=time_mapping,
                ),
                "ApsScheduledStart": _simio_datetime(
                    order.get("ScheduledStart"),
                    time_mapping=time_mapping,
                ),
                "ApsScheduledEnd": _simio_datetime(
                    order.get("ScheduledEnd"),
                    time_mapping=time_mapping,
                ),
            }
        )
    return sorted(rows, key=lambda item: str(item.get("OrderId")))


def _package_issues(
    *,
    resources: list[dict[str, object]],
    routings: list[dict[str, object]],
    orders: list[dict[str, object]],
    model_path: Path,
) -> list[dict[str, object]]:
    issues = []
    if not model_path.exists():
        issues.append(_issue("MODEL_NOT_WRITTEN", "Generated Simio model package is missing."))
    if not resources:
        issues.append(_issue("NO_RESOURCES", "Simio package has no resource rows."))
    if not routings:
        issues.append(_issue("NO_ROUTINGS", "Simio package has no routing rows."))
    if not orders:
        issues.append(
            _issue("NO_MANUFACTURING_ORDERS", "Simio package has no manufacturing orders.")
        )
    hyphenated = [
        str(item.get("ResourceName"))
        for item in resources
        if "-" in str(item.get("ResourceName"))
    ]
    if hyphenated:
        issues.append(
            _issue(
                "RESOURCE_ID_NOT_SIMIO_SAFE",
                "Simio resource IDs must use underscores.",
                {"ResourceIDs": hyphenated},
            )
        )
    return issues


def _mock_runner_result(
    *,
    package: dict[str, object],
    evaluated_at: datetime,
) -> dict[str, object]:
    issues = _dict_list(package.get("Issues"))
    model_path = Path(str(package.get("ModelPath") or ""))
    if not model_path.exists():
        issues.append(_issue("MODEL_PATH_MISSING", "Generated .spfx path does not exist."))
    else:
        issues.extend(_spfx_table_issues(model_path))
    status = "Failed" if issues else "Completed"
    simio_result = _mock_simio_result(package=package, issues=issues)
    return {
        "Status": status,
        "RunnerBackend": "mock",
        "RunnerMode": "mock",
        "CompletedAt": evaluated_at.isoformat(),
        "Message": (
            "Mock Simio validation completed from generated package."
            if not issues
            else "Mock Simio validation found package issues."
        ),
        "Issues": issues,
        **simio_result,
        "Kpis": {
            "ResourceCount": len(package.get("ResourceIDs", [])),
            "OrderCount": len(package.get("OrderIDs", [])),
            "ProductCount": len(package.get("ProductIDs", [])),
            "ModelPackageGenerated": model_path.exists(),
            "FeasibilityConclusion": simio_result["FeasibilityConclusion"],
        },
    }


def _local_runner_result(
    *,
    package: dict[str, object],
    evaluated_at: datetime,
) -> dict[str, object]:
    rlm = ensure_rlm_running()
    if not SIMIO_API_DLL_PATH.exists():
        return {
            "Status": "Unavailable",
            "RunnerBackend": "local",
            "RunnerMode": "local",
            "CompletedAt": evaluated_at.isoformat(),
            "RlmStatus": rlm,
            "Message": f"Local Simio API DLL was not found: {SIMIO_API_DLL_PATH}.",
            "Issues": [_issue("SIMIO_API_DLL_MISSING", "Local Simio API DLL is missing.")],
        }
    helper = _ensure_headless_helper()
    if helper["Status"] != "Compiled":
        return {
            "Status": "Unavailable",
            "RunnerBackend": "local",
            "RunnerMode": "local",
            "CompletedAt": evaluated_at.isoformat(),
            "RlmStatus": rlm,
            "Message": "Local Simio headless helper could not be compiled.",
            "Issues": [
                _issue(
                    "LOCAL_HEADLESS_HELPER_COMPILE_FAILED",
                    str(helper.get("Message") or "Helper compilation failed."),
                    {"Helper": helper},
                )
            ],
        }
    model_path = Path(str(package.get("ModelPath") or ""))
    result_model_path = Path(str(package.get("ResultModelPath") or model_path))
    helper_result = _run_headless_helper(
        model_path=model_path,
        result_model_path=result_model_path,
    )
    issues = [
        _issue(
            "LOCAL_HEADLESS_HELPER_FAILED",
            str(helper_result.get("Message") or "Local helper failed."),
            {"HelperResult": helper_result},
        )
    ] if helper_result.get("Status") != "Completed" else []
    parsed_result = _parse_simio_result_package(
        package=package,
        result_model_path=result_model_path,
        helper_result=helper_result,
        issues=issues,
    )
    return {
        "Status": "Completed" if helper_result.get("Status") == "Completed" else "Failed",
        "RunnerBackend": "local",
        "RunnerMode": "local",
        "CompletedAt": helper_result.get("CompletedAt") or evaluated_at.isoformat(),
        "RlmStatus": rlm,
        "ResultModelPath": helper_result.get("ResultModelPath") or str(result_model_path),
        "Message": helper_result.get("Message"),
        "Issues": issues + _dict_list(parsed_result.get("Issues")),
        **{key: value for key, value in parsed_result.items() if key != "Issues"},
        "Kpis": {
            "ResourceCount": len(package.get("ResourceIDs", [])),
            "OrderCount": len(package.get("OrderIDs", [])),
            "ProductCount": len(package.get("ProductIDs", [])),
            "ModelPackageGenerated": model_path.exists(),
            "ResultModelSaved": result_model_path.exists(),
            "ProjectName": helper_result.get("ProjectName"),
            "ModelName": helper_result.get("ModelName"),
            "PlanRunCompleted": helper_result.get("Status") == "Completed",
            "FeasibilityConclusion": parsed_result.get("FeasibilityConclusion"),
        },
        "RunnerDiagnostics": {
            "SelectedModelReason": helper_result.get("SelectedModelReason"),
            "AvailableModels": helper_result.get("AvailableModels"),
            "PostRunLogSummary": _post_run_log_summary(helper_result),
            "InteractiveStatistics": helper_result.get("InteractiveStatistics"),
        },
        "Helper": {
            "HelperPath": helper.get("HelperPath"),
            "TempDir": helper_result.get("TempDir"),
            "FactoryType": helper_result.get("FactoryType"),
            "PlanType": helper_result.get("PlanType"),
        },
    }


def _post_run_log_summary(helper_result: dict[str, object]) -> list[dict[str, object]]:
    summary: list[dict[str, object]] = []
    for item in _dict_list(helper_result.get("PostRunLogExports")):
        summary.append(
            {
                "Property": item.get("Property"),
                "RuntimeType": item.get("RuntimeType"),
                "Count": item.get("Count"),
                "InteractiveExportStatus": _dict(item.get("Interactive")).get("Status"),
                "PlanExportStatus": _dict(item.get("Plan")).get("Status"),
                "SampleStatus": _dict(item.get("Samples")).get("Status"),
            }
        )
    return summary


def _ensure_headless_helper() -> dict[str, object]:
    source_path = Path("tools/simio_headless_helper/Program.cs")
    if (
        SIMIO_HELPER_DLL_PATH.exists()
        and source_path.exists()
        and SIMIO_HELPER_DLL_PATH.stat().st_mtime >= source_path.stat().st_mtime
    ):
        return {
            "Status": "Compiled",
            "HelperPath": str(SIMIO_HELPER_DLL_PATH),
        }
    if not SIMIO_HELPER_COMPILE_SCRIPT.exists():
        return {
            "Status": "Missing",
            "Message": f"Compile script was not found: {SIMIO_HELPER_COMPILE_SCRIPT}.",
        }
    result = subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(SIMIO_HELPER_COMPILE_SCRIPT),
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=60,
    )
    if result.returncode != 0:
        return {
            "Status": "Failed",
            "Message": (result.stderr or result.stdout).strip(),
        }
    return _json_line(result.stdout) | {
        "Status": "Compiled",
        "HelperPath": str(SIMIO_HELPER_DLL_PATH),
    }


def _run_headless_helper(
    *,
    model_path: Path,
    result_model_path: Path,
) -> dict[str, object]:
    SIMIO_HELPER_TEMP_DIR.mkdir(parents=True, exist_ok=True)
    result_model_path.parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        [
            "dotnet",
            "exec",
            str(SIMIO_HELPER_DLL_PATH),
            "--mode",
            "run-plan",
            "--source",
            str(model_path.resolve()),
            "--output",
            str(result_model_path.resolve()),
            "--temp",
            str(SIMIO_HELPER_TEMP_DIR.resolve()),
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=180,
    )
    payload = _json_line(result.stdout)
    if result.returncode != 0 and "Status" not in payload:
        return {
            "Status": "Failed",
            "Message": (result.stderr or result.stdout).strip(),
            "ReturnCode": result.returncode,
        }
    return payload | {"ReturnCode": result.returncode}


def _json_line(text: str) -> dict[str, object]:
    import json

    for line in reversed(text.splitlines()):
        stripped = line.strip()
        if not stripped:
            continue
        try:
            value = json.loads(stripped)
        except json.JSONDecodeError:
            continue
        return value if isinstance(value, dict) else {}
    return {}


def _spfx_table_issues(model_path: Path) -> list[dict[str, object]]:
    issues: list[dict[str, object]] = []
    try:
        with ZipFile(model_path, "r") as package:
            names = {_simio_package_path(name) for name in package.namelist()}
            for required in (
                TABLE_RESOURCES,
                TABLE_ROUTINGS,
                TABLE_MANUFACTURING_ORDERS,
                TABLE_MANUFACTURING_ORDERS_OUTPUT,
                TABLE_SDBR_RUN_SUMMARY,
                *SDBR_PROCESS_PATHS,
            ):
                if required not in names:
                    issues.append(_issue("SIMIO_TABLE_MISSING", f"Missing {required}."))
    except Exception as error:
        issues.append(_issue("SPFX_UNREADABLE", str(error)))
    return issues


def _mock_simio_result(
    *,
    package: dict[str, object],
    issues: list[dict[str, object]],
) -> dict[str, object]:
    resource_ids = list(package.get("ResourceIDs", []))
    order_count = len(package.get("OrderIDs", []))
    conclusion = "Infeasible" if issues else "Feasible"
    return {
        "FeasibilityConclusion": conclusion,
        "Throughput": {
            "Status": "Mocked",
            "PlannedOrderCount": order_count,
            "CompletedOrderCount": 0 if issues else order_count,
            "UnfinishedOrderCount": order_count if issues else 0,
            "ProducedQuantity": None,
        },
        "QueueMetrics": {
            "Status": "NotSimulated",
            "Message": "Mock runner does not simulate queue dynamics.",
            "Resources": [],
        },
        "WipMetrics": {
            "Status": "NotSimulated",
            "Message": "Mock runner does not simulate WIP dynamics.",
            "SystemAverageWip": None,
            "SystemMaxWip": None,
            "Resources": [],
        },
        "ResourceUtilization": {
            "Status": "NotSimulated",
            "Resources": [
                {"ResourceID": str(resource_id), "UtilizationPercent": None}
                for resource_id in resource_ids
            ],
        },
        "ScheduleAdherence": {
            "Status": "NotSimulated",
            "Rows": [],
        },
        "ResultCoverage": {
            "Status": "Mocked",
            "ParsedSources": [],
            "UnavailableSources": list(RESULT_LOG_PATHS),
        },
    }


def _parse_simio_result_package(
    *,
    package: dict[str, object],
    result_model_path: Path,
    helper_result: dict[str, object],
    issues: list[dict[str, object]],
) -> dict[str, object]:
    if helper_result.get("Status") != "Completed":
        return {
            "FeasibilityConclusion": "ResultUnavailable",
            "Throughput": _unavailable_metric("Headless helper did not complete."),
            "QueueMetrics": _unavailable_metric("Headless helper did not complete."),
            "WipMetrics": _unavailable_metric("Headless helper did not complete."),
            "ResourceUtilization": _unavailable_metric("Headless helper did not complete."),
            "ScheduleAdherence": _unavailable_metric("Headless helper did not complete."),
            "ResultCoverage": {
                "Status": "Unavailable",
                "ParsedSources": [],
                "UnavailableSources": [str(result_model_path)],
            },
            "Issues": [],
        }
    if not result_model_path.exists():
        return {
            "FeasibilityConclusion": "ResultUnavailable",
            "Throughput": _unavailable_metric("Result model was not saved."),
            "QueueMetrics": _unavailable_metric("Result model was not saved."),
            "WipMetrics": _unavailable_metric("Result model was not saved."),
            "ResourceUtilization": _unavailable_metric("Result model was not saved."),
            "ScheduleAdherence": _unavailable_metric("Result model was not saved."),
            "ResultCoverage": {
                "Status": "Unavailable",
                "ParsedSources": [],
                "UnavailableSources": [str(result_model_path)],
            },
            "Issues": [
                _issue(
                    "SIMIO_RESULT_MODEL_MISSING",
                    "Local Simio runner did not save a result model.",
                )
            ],
        }

    parse_issues: list[dict[str, object]] = []
    output_rows: list[dict[str, str]] = []
    order_rows: list[dict[str, str]] = []
    routing_rows: list[dict[str, str]] = []
    result_logs: dict[str, dict[str, object]] = {}
    sqlite_output_rows: list[dict[str, str]] = []
    sqlite_output_source: str | None = None
    try:
        with ZipFile(result_model_path, "r") as archive:
            names = {_simio_package_path(name): name for name in archive.namelist()}
            order_entry = names.get(TABLE_MANUFACTURING_ORDERS)
            if order_entry:
                order_rows = _rows_from_fragment_text(
                    archive.read(order_entry).decode("utf-8", errors="replace")
                )
            routing_entry = names.get(TABLE_ROUTINGS)
            if routing_entry:
                routing_rows = _rows_from_fragment_text(
                    archive.read(routing_entry).decode("utf-8", errors="replace")
                )
            output_entry = names.get(TABLE_MANUFACTURING_ORDERS_OUTPUT)
            if output_entry:
                output_rows = _rows_from_fragment_text(
                    archive.read(output_entry).decode("utf-8", errors="replace")
                )
            else:
                parse_issues.append(
                    _issue(
                        "SIMIO_OUTPUT_TABLE_MISSING",
                        f"Missing {TABLE_MANUFACTURING_ORDERS_OUTPUT}.",
                        severity="Warning",
                    )
                )
            sqlite_entry = names.get(TABLE_STATES_SQLITE)
            if sqlite_entry:
                sqlite_output_rows, sqlite_output_source = _sqlite_output_rows(
                    payload=archive.read(sqlite_entry),
                    order_rows=order_rows,
                    routing_rows=routing_rows,
                )
            for log_path in RESULT_LOG_PATHS:
                entry = names.get(log_path)
                if entry is None:
                    result_logs[log_path] = {"Status": "Missing", "Bytes": 0}
                    parse_issues.append(
                        _issue(
                            "SIMIO_RESULT_LOG_MISSING",
                            f"Missing {log_path}.",
                            {"Path": log_path},
                            severity="Warning",
                        )
                    )
                    continue
                payload = archive.read(entry)
                result_logs[log_path] = _binary_log_summary(log_path, payload)
    except Exception as error:
        return {
            "FeasibilityConclusion": "ResultUnavailable",
            "Throughput": _unavailable_metric(str(error)),
            "QueueMetrics": _unavailable_metric(str(error)),
            "WipMetrics": _unavailable_metric(str(error)),
            "ResourceUtilization": _unavailable_metric(str(error)),
            "ScheduleAdherence": _unavailable_metric(str(error)),
            "ResultCoverage": {
                "Status": "Unreadable",
                "ParsedSources": [],
                "UnavailableSources": [str(result_model_path)],
            },
            "Issues": [_issue("SIMIO_RESULT_UNREADABLE", str(error))],
        }

    planned_order_count = len(package.get("OrderIDs", []))
    if _business_populated_rows(sqlite_output_rows):
        output_rows = sqlite_output_rows
        output_source = sqlite_output_source or TABLE_STATES_SQLITE
    else:
        output_source = TABLE_MANUFACTURING_ORDERS_OUTPUT
    populated_output_rows = _business_populated_rows(output_rows)
    completed_order_ids = {
        str(row.get("OrderId") or row.get("OrderID"))
        for row in populated_output_rows
        if row.get("OrderId") or row.get("OrderID")
    }
    completed_order_count = _completed_order_count(
        rows=populated_output_rows,
        planned_order_count=planned_order_count,
        completed_order_ids=completed_order_ids,
    )
    incomplete_count = (
        max(planned_order_count - completed_order_count, 0)
        if populated_output_rows
        else None
    )
    stat_rows = _interactive_statistics_rows(helper_result)
    stat_metrics = _metrics_from_interactive_statistics(
        rows=stat_rows,
        resource_ids=[str(item) for item in package.get("ResourceIDs", [])],
    )
    post_run_metrics = _metrics_from_post_run_logs(helper_result=helper_result)
    output_row_metrics = _metrics_from_output_rows(
        rows=populated_output_rows,
        resource_ids=[str(item) for item in package.get("ResourceIDs", [])],
        output_source=output_source,
    )
    if output_row_metrics.get("QueueMetrics"):
        stat_metrics["QueueMetrics"] = output_row_metrics["QueueMetrics"]
    if output_row_metrics.get("WipMetrics"):
        stat_metrics["WipMetrics"] = output_row_metrics["WipMetrics"]
    if not stat_rows and post_run_metrics.get("ResourceUtilization"):
        stat_metrics["ResourceUtilization"] = post_run_metrics["ResourceUtilization"]
    has_binary_partial = any(
        summary.get("Status") == "BinaryLogPresent"
        for summary in result_logs.values()
    )
    if issues:
        conclusion = "Infeasible"
    elif populated_output_rows and incomplete_count == 0:
        conclusion = (
            "FeasibleWithWarnings"
            if has_binary_partial and stat_metrics["ResultCoverageStatus"] != "Parsed"
            else "Feasible"
        )
    elif populated_output_rows and incomplete_count and incomplete_count > 0:
        conclusion = "Infeasible"
    else:
        conclusion = "FeasibleWithWarnings"
    if incomplete_count and incomplete_count > 0:
        parse_issues.append(
            _issue(
                "SIMIO_UNFINISHED_ORDERS",
                "Simio output indicates one or more planned orders did not finish.",
                {
                    "PlannedOrderCount": planned_order_count,
                    "CompletedOrderCount": completed_order_count,
                    "UnfinishedOrderCount": incomplete_count,
                    "OutputSource": output_source,
                },
            )
        )
    if has_binary_partial and stat_metrics["ResultCoverageStatus"] != "Parsed":
        utilization_status = _dict(stat_metrics.get("ResourceUtilization")).get("Status")
        partial_message = (
            "Simio result logs are present; resource utilization was parsed from "
            "post-run logs, but queue and WIP logs are still not fully mapped."
            if utilization_status == "ParsedFromPostRunLogs"
            else (
                "Simio result logs are present, but queue, WIP and resource "
                "utilization logs are still proprietary binary logs and were "
                "not fully decoded."
            )
        )
        parse_issues.append(
            _issue(
                "SIMIO_BINARY_LOGS_PARTIAL",
                partial_message,
                severity="Warning",
            )
        )
    if not populated_output_rows or incomplete_count not in {0, None}:
        parse_issues.append(
            _issue(
                "SIMIO_RESULT_PARTIAL",
                (
                    "Simio RunPlan completed, but detailed result tables or binary "
                    "logs could only be partially parsed."
                ),
                severity="Warning",
            )
        )

    resource_ids = [str(item) for item in package.get("ResourceIDs", [])]
    throughput = {
        "Status": "Parsed" if populated_output_rows else "PartialResultParsed",
        "PlannedOrderCount": planned_order_count,
        "CompletedOrderCount": (
            completed_order_count if populated_output_rows else None
        ),
        "UnfinishedOrderCount": incomplete_count,
        "ProducedQuantity": _sum_numeric_field(
            populated_output_rows,
            ("ScheduledQuantity", "Quantity", "CompletedQuantity"),
        ),
        "OutputRowCount": len(output_rows),
        "PopulatedOutputRowCount": len(populated_output_rows),
        "OutputSource": output_source,
    }
    throughput.update(stat_metrics["Throughput"])
    parsed_sources = _dedupe_strings(
        [
            output_source,
            *([SIMIO_STATS_SOURCE] if stat_rows else []),
            *(
                ["SimioAPI.PostRunLogs"]
                if _dict(post_run_metrics.get("ResourceUtilization")).get("Status")
                == "ParsedFromPostRunLogs"
                else []
            ),
            *[
                path
                for path, summary in result_logs.items()
                if summary.get("Status") != "Missing"
            ],
        ]
    )
    return {
        "FeasibilityConclusion": conclusion,
        "Throughput": throughput,
        "QueueMetrics": stat_metrics["QueueMetrics"],
        "WipMetrics": stat_metrics["WipMetrics"],
        "ResourceUtilization": _attach_resource_evidence(
            utilization=stat_metrics["ResourceUtilization"],
            result_logs=result_logs,
        ),
        "ScheduleAdherence": _schedule_adherence_from_rows(
            output_rows=populated_output_rows,
            package=package,
        ),
        "ResultCoverage": {
            "Status": stat_metrics["ResultCoverageStatus"],
            "ParsedSources": parsed_sources,
            "UnavailableSources": [
                path
                for path, summary in result_logs.items()
                if summary.get("Status") == "Missing"
            ],
            "Logs": result_logs,
        },
        "Issues": parse_issues,
    }


def _fragment_xml(rows: list[dict[str, object]]) -> str:
    fragment = ET.Element("Fragment")
    for row in rows:
        row_node = ET.SubElement(fragment, "Row")
        properties = ET.SubElement(row_node, "Properties")
        for key, value in row.items():
            attributes = {"Name": str(key)}
            if str(key) in SIMIO_MINUTE_FIELDS:
                attributes["Units"] = "Minutes"
            prop = ET.SubElement(properties, "Property", attributes)
            prop.text = "" if value is None else str(value)
    return ET.tostring(fragment, encoding="unicode", short_empty_elements=False)


def _sqlite_table_rows(payload: bytes, table_name: str) -> list[dict[str, str]]:
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".sqlite") as temp_file:
            temp_file.write(payload)
            temp_path = temp_file.name
        connection = sqlite3.connect(temp_path)
        try:
            connection.row_factory = sqlite3.Row
            cursor = connection.execute(f'SELECT * FROM "{table_name}"')
            return [
                {
                    key: "" if value is None else str(value)
                    for key, value in dict(row).items()
                }
                for row in cursor.fetchall()
            ]
        finally:
            connection.close()
    except Exception:
        return []
    finally:
        if temp_path:
            try:
                os.unlink(temp_path)
            except OSError:
                pass


def _sqlite_output_rows(
    *,
    payload: bytes,
    order_rows: list[dict[str, str]],
    routing_rows: list[dict[str, str]],
) -> tuple[list[dict[str, str]], str | None]:
    sources = (
        (
            "Table_ManufacturingOrdersOutput_States_PlanValues",
            f"{TABLE_STATES_SQLITE}:PlanValues",
        ),
        (
            "Table_ManufacturingOrdersOutput_States_InteractiveValues",
            f"{TABLE_STATES_SQLITE}:InteractiveValues",
        ),
    )
    for table_name, source in sources:
        rows = _sqlite_table_rows(payload, table_name)
        resolved = _resolve_simio_output_foreign_keys(
            rows=rows,
            order_rows=order_rows,
            routing_rows=routing_rows,
        )
        if _business_populated_rows(resolved):
            return resolved, source
    return [], None


def _resolve_simio_output_foreign_keys(
    *,
    rows: list[dict[str, str]],
    order_rows: list[dict[str, str]],
    routing_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    resolved: list[dict[str, str]] = []
    for row in rows:
        item = dict(row)
        order_index = _sqlite_foreign_key_index(item.get("OrderId") or item.get("OrderID"))
        if order_index is not None and 0 <= order_index < len(order_rows):
            item["OrderId"] = (
                order_rows[order_index].get("OrderId")
                or order_rows[order_index].get("OrderID")
                or str(order_index)
            )
        routing_index = _sqlite_foreign_key_index(item.get("RoutingKey"))
        if routing_index is not None and 0 <= routing_index < len(routing_rows):
            item["RoutingKey"] = routing_rows[routing_index].get("RoutingKey") or str(
                routing_index
            )
        resolved.append(item)
    return resolved


def _sqlite_foreign_key_index(value: object) -> int | None:
    if value in {None, ""}:
        return None
    try:
        return int(float(str(value)))
    except ValueError:
        return None


def _business_populated_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    return [
        row
        for row in rows
        if any(
            key != "__RowIndex" and str(value).strip()
            for key, value in row.items()
        )
    ]


def _completed_order_count(
    *,
    rows: list[dict[str, str]],
    planned_order_count: int,
    completed_order_ids: set[str],
) -> int:
    if not rows:
        return 0
    if completed_order_ids:
        grouped: dict[str, list[dict[str, str]]] = {}
        for row in rows:
            order_id = str(row.get("OrderId") or row.get("OrderID") or "").strip()
            if order_id:
                grouped.setdefault(order_id, []).append(row)
        completed = [
            order_id
            for order_id, scoped_rows in grouped.items()
            if scoped_rows and all(_row_has_completion_time(row) for row in scoped_rows)
        ]
        return min(planned_order_count, len(completed)) if planned_order_count else len(completed)
    rows_with_completion = [row for row in rows if _row_has_completion_time(row)]
    return min(planned_order_count, len(rows_with_completion))


def _row_has_completion_time(row: dict[str, str]) -> bool:
    for key in ("ActualEndTime", "CompletedAt", "ScheduledEndTime", "EndTime"):
        if str(row.get(key) or "").strip():
            return True
    return False


def _interactive_statistics_rows(helper_result: dict[str, object]) -> list[dict[str, object]]:
    stats = _dict(helper_result.get("InteractiveStatistics"))
    if stats.get("Status") != "Parsed":
        return []
    return _dict_list(stats.get("Rows"))


def _metrics_from_post_run_logs(
    *,
    helper_result: dict[str, object],
) -> dict[str, object]:
    metrics = _dict(helper_result.get("PostRunMetrics"))
    if metrics.get("Status") != "Parsed":
        return {}
    result: dict[str, object] = {}
    resource_utilization = _dict(metrics.get("ResourceUtilization"))
    if resource_utilization.get("Status") == "ParsedFromPostRunLogs":
        result["ResourceUtilization"] = resource_utilization
    queue_metrics = _dict(metrics.get("QueueMetrics"))
    if queue_metrics.get("Status") not in {None, "Unavailable"}:
        result["QueueMetrics"] = queue_metrics
    wip_metrics = _dict(metrics.get("WipMetrics"))
    if wip_metrics.get("Status") not in {None, "Unavailable"}:
        result["WipMetrics"] = wip_metrics
    return result


def _metrics_from_interactive_statistics(
    *,
    rows: list[dict[str, object]],
    resource_ids: list[str],
) -> dict[str, object]:
    if not rows:
        return {
            "ResultCoverageStatus": "PartialResultParsed",
            "Throughput": {},
            "QueueMetrics": {
                "Status": "PartialResultParsed",
                "Message": (
                    "Interactive statistics were not returned by the local Simio helper."
                ),
                "Resources": [
                    {
                        "ResourceID": resource_id,
                        "AverageQueueLength": None,
                        "MaxQueueLength": None,
                        "AverageWaitMinutes": None,
                    }
                    for resource_id in resource_ids
                ],
                "SourceLogs": [
                    "Results/Model/TaskState.log",
                    "Results/Model/ResourceState.log",
                ],
            },
            "WipMetrics": {
                "Status": "PartialResultParsed",
                "SystemAverageWip": None,
                "SystemMaxWip": None,
                "Resources": [
                    {"ResourceID": resource_id, "AverageWip": None, "MaxWip": None}
                    for resource_id in resource_ids
                ],
                "SourceLogs": [
                    "Results/Model/StateObservation.log",
                    "Results/Model/Task.log",
                ],
            },
            "ResourceUtilization": {
                "Status": "PartialResultParsed",
                "Resources": [
                    {
                        "ResourceID": resource_id,
                        "UtilizationPercent": None,
                        "BusyMinutes": None,
                        "StarvedMinutes": None,
                        "BlockedMinutes": None,
                        "Evidence": [],
                    }
                    for resource_id in resource_ids
                ],
                "SourceLogs": [
                    "Results/Model/Interactive_Results.stats",
                    "Results/Model/ResourceUsage.log",
                    "Results/Model/ResourceState.log",
                ],
            },
        }

    throughput = {
        "SimioEntityCreated": _stat_value(
            rows,
            object_name="DefaultEntity",
            data_source="[Population]",
            statistic_category="Throughput",
            statistic_type="Total",
            data_item="NumberCreated",
        ),
        "SimioEntityDestroyed": _stat_value(
            rows,
            object_name="DefaultEntity",
            data_source="[Population]",
            statistic_category="Throughput",
            statistic_type="Total",
            data_item="NumberDestroyed",
        ),
    }
    resource_wip = []
    queue_resources = []
    utilization_resources = []
    for resource_id in resource_ids:
        average_station_content = _stat_value(
            rows,
            object_name=resource_id,
            data_source="Processing",
            statistic_category="Content",
            statistic_type="Average",
            data_item="NumberInStation",
        )
        max_station_content = _stat_value(
            rows,
            object_name=resource_id,
            data_source="Processing",
            statistic_category="Content",
            statistic_type="Maximum",
            data_item="NumberInStation",
        )
        average_time_in_station_hours = _stat_value(
            rows,
            object_name=resource_id,
            data_source="Processing",
            statistic_category="HoldingTime",
            statistic_type="Average",
            data_item="TimeInStation",
        )
        queue_resources.append(
            {
                "ResourceID": resource_id,
                "AverageQueueLength": None,
                "MaxQueueLength": None,
                "AverageWaitMinutes": None,
                "AverageStationContent": average_station_content,
                "MaxStationContent": max_station_content,
                "AverageTimeInStationMinutes": _hours_to_minutes(
                    average_time_in_station_hours
                ),
                "NumberEntered": _stat_value(
                    rows,
                    object_name=resource_id,
                    data_source="Processing",
                    statistic_category="Throughput",
                    statistic_type="Total",
                    data_item="NumberEntered",
                ),
                "NumberExited": _stat_value(
                    rows,
                    object_name=resource_id,
                    data_source="Processing",
                    statistic_category="Throughput",
                    statistic_type="Total",
                    data_item="NumberExited",
                ),
                "MetricBasis": (
                    "Processing.NumberInStation and TimeInStation from "
                    "Interactive_Results.stats; this is station content, not a "
                    "dedicated input queue-only counter."
                ),
            }
        )
        resource_wip.append(
            {
                "ResourceID": resource_id,
                "AverageWip": average_station_content,
                "MaxWip": max_station_content,
                "MetricBasis": "Processing.NumberInStation from Interactive_Results.stats.",
            }
        )
        busy_hours = _stat_value(
            rows,
            object_name=resource_id,
            data_source="[Resource]",
            statistic_category="ResourceState",
            statistic_type="Total",
            data_item="TimeProcessing",
        )
        starved_hours = _stat_value(
            rows,
            object_name=resource_id,
            data_source="[Resource]",
            statistic_category="ResourceState",
            statistic_type="Total",
            data_item="TimeStarved",
        )
        utilization_resources.append(
            {
                "ResourceID": resource_id,
                "UtilizationPercent": _stat_value(
                    rows,
                    object_name=resource_id,
                    data_source="[Resource]",
                    statistic_category="ResourceState",
                    statistic_type="Percent",
                    data_item="TimeProcessing",
                ),
                "ScheduledUtilizationPercent": _stat_value(
                    rows,
                    object_name=resource_id,
                    data_source="[Resource]",
                    statistic_category="Capacity",
                    statistic_type="Percent",
                    data_item="ScheduledUtilization",
                ),
                "BusyMinutes": _hours_to_minutes(busy_hours),
                "StarvedMinutes": _hours_to_minutes(starved_hours),
                "BlockedMinutes": _hours_to_minutes(
                    _stat_value(
                        rows,
                        object_name=resource_id,
                        data_source="[Resource]",
                        statistic_category="ResourceState",
                        statistic_type="Total",
                        data_item="TimeBlocked",
                    )
                ),
                "UnitsScheduledAverage": _stat_value(
                    rows,
                    object_name=resource_id,
                    data_source="[Resource]",
                    statistic_category="Capacity",
                    statistic_type="Average",
                    data_item="UnitsScheduled",
                ),
                "Evidence": [SIMIO_STATS_SOURCE],
            }
        )

    return {
        "ResultCoverageStatus": "Parsed",
        "Throughput": throughput,
        "QueueMetrics": {
            "Status": "ParsedFromInteractiveStatistics",
            "Message": (
                "Parsed station-content and time-in-station statistics from "
                "Simio Interactive_Results.stats. Dedicated queue-only counters "
                "are not yet separated."
            ),
            "Resources": queue_resources,
            "SourceLogs": [SIMIO_STATS_SOURCE],
        },
        "WipMetrics": {
            "Status": "ParsedFromInteractiveStatistics",
            "SystemAverageWip": _stat_value(
                rows,
                object_name="DefaultEntity",
                data_source="[Population]",
                statistic_category="Content",
                statistic_type="Average",
                data_item="NumberInSystem",
            ),
            "SystemMaxWip": _stat_value(
                rows,
                object_name="DefaultEntity",
                data_source="[Population]",
                statistic_category="Content",
                statistic_type="Maximum",
                data_item="NumberInSystem",
            ),
            "Resources": resource_wip,
            "SourceLogs": [SIMIO_STATS_SOURCE],
        },
        "ResourceUtilization": {
            "Status": "ParsedFromInteractiveStatistics",
            "Resources": utilization_resources,
            "SourceLogs": [SIMIO_STATS_SOURCE],
        },
    }


def _metrics_from_output_rows(
    *,
    rows: list[dict[str, str]],
    resource_ids: list[str],
    output_source: str,
) -> dict[str, object]:
    if not rows:
        return {}
    queue_values_by_resource: dict[str, list[float]] = {}
    wip_values_by_resource: dict[str, list[float]] = {}
    for row in rows:
        resource_id = str(row.get("ScheduledResource") or "").strip()
        if not resource_id:
            continue
        queue_wait = _numeric_value(row.get("QueueWaitMinutes"))
        if queue_wait is not None:
            queue_values_by_resource.setdefault(resource_id, []).append(queue_wait)
        for key in ("WipAfterStart", "WipAfterEnd"):
            wip_value = _numeric_value(row.get(key))
            if wip_value is not None:
                wip_values_by_resource.setdefault(resource_id, []).append(wip_value)

    result: dict[str, object] = {}
    if queue_values_by_resource:
        result["QueueMetrics"] = {
            "Status": "ParsedFromSDBROutputRows",
            "Message": (
                "Parsed queue wait evidence from SDBR fields written into "
                "ManufacturingOrdersOutput."
            ),
            "Resources": [
                {
                    "ResourceID": resource_id,
                    "AverageQueueLength": None,
                    "MaxQueueLength": None,
                    "AverageWaitMinutes": _average(values),
                    "MaxWaitMinutes": max(values),
                    "ObservationCount": len(values),
                    "MetricBasis": "ManufacturingOrdersOutput.QueueWaitMinutes",
                }
                for resource_id, values in sorted(queue_values_by_resource.items())
            ],
            "SourceLogs": [output_source],
        }
    if wip_values_by_resource:
        all_wip_values = [
            value
            for values in wip_values_by_resource.values()
            for value in values
        ]
        result["WipMetrics"] = {
            "Status": "ParsedFromSDBROutputRows",
            "SystemAverageWip": _average(all_wip_values),
            "SystemMaxWip": max(all_wip_values),
            "Resources": [
                {
                    "ResourceID": resource_id,
                    "AverageWip": _average(values),
                    "MaxWip": max(values),
                    "MetricBasis": (
                        "ManufacturingOrdersOutput.WipAfterStart/WipAfterEnd"
                    ),
                }
                for resource_id, values in sorted(wip_values_by_resource.items())
            ],
            "SourceLogs": [output_source],
        }
    return result


def _numeric_value(value: object) -> float | None:
    if value in {None, ""}:
        return None
    try:
        return float(str(value))
    except ValueError:
        return None


def _average(values: list[float]) -> float | None:
    if not values:
        return None
    return round(sum(values) / len(values), 6)


def _stat_value(
    rows: list[dict[str, object]],
    *,
    object_name: str,
    data_source: str,
    statistic_category: str,
    statistic_type: str,
    data_item: str,
) -> float | None:
    for row in rows:
        if (
            str(row.get("ObjectName") or "") == object_name
            and str(row.get("DataSource") or "") == data_source
            and str(row.get("StatisticCategory") or "") == statistic_category
            and str(row.get("StatisticType") or "") == statistic_type
            and str(row.get("DataItem") or "") == data_item
        ):
            for key in ("Value", "Average", "Maximum", "Minimum"):
                value = row.get(key)
                if value in {None, ""}:
                    continue
                try:
                    return float(str(value))
                except ValueError:
                    continue
    return None


def _hours_to_minutes(value: float | None) -> float | None:
    return round(value * 60, 6) if value is not None else None


def _dedupe_strings(values: list[str]) -> list[str]:
    result = []
    seen = set()
    for value in values:
        if value in seen:
            continue
        result.append(value)
        seen.add(value)
    return result


def _attach_resource_evidence(
    *,
    utilization: dict[str, object],
    result_logs: dict[str, dict[str, object]],
) -> dict[str, object]:
    resources = []
    for item in _dict_list(utilization.get("Resources")):
        resource_id = str(item.get("ResourceID") or "")
        evidence = list(item.get("Evidence") or [])
        evidence.extend(_resource_log_evidence(result_logs, resource_id))
        resources.append({**item, "Evidence": sorted(set(evidence))})
    return {**utilization, "Resources": resources}


def _simio_resource_id(value: object) -> str:
    resource_id = str(value or "UNKNOWN_RESOURCE")
    return resource_id.replace("-", "_").replace(" ", "_")


def _simio_time_mapping(
    *,
    output_package: dict[str, object],
    template_path: Path,
) -> dict[str, object]:
    simio_anchor = _template_run_start(template_path) or datetime(2019, 12, 2, 8)
    candidates: list[datetime] = []
    for order in _dict_list(output_package.get("WorkOrders")):
        for key in (
            "SuggestedReleaseAt",
            "ScheduledStart",
            "ScheduledEnd",
            "DueDate",
        ):
            parsed = _parse_datetime(order.get(key))
            if parsed is not None:
                candidates.append(parsed)
    aps_anchor = min(candidates) if candidates else simio_anchor
    if aps_anchor.tzinfo is not None:
        aps_anchor = aps_anchor.astimezone(timezone.utc).replace(tzinfo=None)
    if simio_anchor.tzinfo is not None:
        simio_anchor = simio_anchor.astimezone(timezone.utc).replace(tzinfo=None)
    offset = simio_anchor - aps_anchor
    return {
        "Status": "Applied",
        "ApsAnchorAt": aps_anchor.isoformat(),
        "SimioAnchorAt": simio_anchor.isoformat(),
        "OffsetMinutes": int(offset.total_seconds() / 60),
    }


def _template_run_start(template_path: Path) -> datetime | None:
    try:
        if template_path.suffix.lower() == ".spfx":
            with ZipFile(template_path, "r") as archive:
                payload = archive.read("Project.xml").decode("utf-8")
        else:
            payload = template_path.read_text(encoding="utf-8")
        root = ET.fromstring(payload)
        for node in root.iter():
            if node.tag.split("}", 1)[-1] == "StartDate" and node.text:
                return _parse_datetime(node.text)
    except Exception:
        return None
    return None


def _parse_datetime(value: object) -> datetime | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    normalized = text.replace("Z", "+00:00")
    if normalized.endswith(".0000000"):
        normalized = normalized[: -len(".0000000")]
    try:
        return datetime.fromisoformat(normalized)
    except ValueError:
        return None


def _shift_datetime(value: object, time_mapping: dict[str, object] | None) -> datetime | None:
    parsed = _parse_datetime(value)
    if parsed is None or not time_mapping:
        return parsed
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
    offset_minutes = int(time_mapping.get("OffsetMinutes") or 0)
    return parsed + timedelta(minutes=offset_minutes)


def _simio_datetime(
    value: object,
    *,
    time_mapping: dict[str, object] | None = None,
) -> str:
    if value is None:
        return datetime.now(timezone.utc).isoformat()
    shifted = _shift_datetime(value, time_mapping)
    if shifted is None:
        text = str(value)
        if text.endswith("+00:00"):
            return text.replace("+00:00", ".0000000")
        return text
    return shifted.replace(tzinfo=None).isoformat() + ".0000000"



def _template_source_type(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".xml":
        return "SimioXmlProjectExport"
    if suffix == ".spfx":
        return "SimioSpfxPackage"
    return "Unknown"


def _simio_package_path(value: str) -> str:
    return value.replace("\\", "/")


def _template_table_rows(
    *,
    template_path: Path,
    table_path: str,
) -> list[dict[str, str]]:
    normalized_table_path = _simio_package_path(table_path)
    try:
        if template_path.suffix.lower() == ".spfx":
            with ZipFile(template_path, "r") as archive:
                for name in archive.namelist():
                    if _simio_package_path(name) == normalized_table_path:
                        return _rows_from_fragment_text(
                            archive.read(name).decode("utf-8")
                        )
            return []
        if template_path.suffix.lower() != ".xml":
            return []
        tree = ET.parse(template_path)
        root = tree.getroot()
        namespace = _xml_namespace(root.tag)
        file_tag = f"{{{namespace}}}File" if namespace else "File"
        binary_tag = f"{{{namespace}}}BinaryData" if namespace else "BinaryData"
        for file_node in root.findall(f".//{file_tag}"):
            name = _simio_package_path(str(file_node.attrib.get("Name") or ""))
            if name != normalized_table_path:
                continue
            binary_node = file_node.find(binary_tag)
            if binary_node is None or not (binary_node.text or "").strip():
                return []
            return _rows_from_fragment_text(
                base64.b64decode(binary_node.text.strip()).decode("utf-8")
            )
    except Exception:
        return []
    return []


def _xml_namespace(tag: str) -> str:
    if tag.startswith("{") and "}" in tag:
        return tag[1:].split("}", 1)[0]
    return ""


def _rows_from_fragment_text(fragment_text: str) -> list[dict[str, str]]:
    root = ET.fromstring(fragment_text)
    rows: list[dict[str, str]] = []
    for index, row in enumerate(root.findall("./Row"), start=1):
        values: dict[str, str] = {"__RowIndex": str(index)}
        for prop in row.findall("./Properties/Property"):
            value = (prop.text or "").strip()
            nested = prop.find("./Value")
            if nested is not None:
                value = (nested.text or "").strip()
            values[str(prop.attrib.get("Name"))] = value
        rows.append(values)
    return rows


def _binary_log_summary(path: str, payload: bytes) -> dict[str, object]:
    strings = _ascii_strings(payload)
    return {
        "Status": "BinaryLogPresent",
        "Path": path,
        "Bytes": len(payload),
        "ExtractedStringCount": len(strings),
        "SampleStrings": strings[:30],
    }


def _ascii_strings(payload: bytes, minimum: int = 4) -> list[str]:
    strings: list[str] = []
    current: list[str] = []
    for byte in payload:
        if 32 <= byte <= 126:
            current.append(chr(byte))
        else:
            if len(current) >= minimum:
                strings.append("".join(current))
            current = []
    if len(current) >= minimum:
        strings.append("".join(current))
    deduped: list[str] = []
    seen: set[str] = set()
    for value in strings:
        if value not in seen:
            deduped.append(value)
            seen.add(value)
    return deduped


def _resource_log_evidence(
    logs: dict[str, dict[str, object]],
    resource_id: str,
) -> list[str]:
    evidence = []
    for path, summary in logs.items():
        samples = [str(item) for item in summary.get("SampleStrings", [])]
        if any(resource_id in sample for sample in samples):
            evidence.append(path)
    return evidence


def _schedule_adherence_from_rows(
    *,
    output_rows: list[dict[str, str]],
    package: dict[str, object],
) -> dict[str, object]:
    if not output_rows:
        return {
            "Status": "Unavailable",
            "Rows": [],
            "Message": "ManufacturingOrdersOutput rows did not contain populated values.",
        }
    return {
        "Status": "Parsed",
        "Rows": [
            {
                "OrderID": row.get("OrderId") or row.get("OrderID"),
                "RoutingKey": row.get("RoutingKey"),
                "ScheduledResource": row.get("ScheduledResource"),
                "ScheduledStartTime": row.get("ScheduledStartTime"),
                "ScheduledEndTime": row.get("ScheduledEndTime"),
                "ScheduledQuantity": row.get("ScheduledQuantity"),
                "ActualStartTime": row.get("ActualStartTime"),
                "ActualEndTime": row.get("ActualEndTime"),
                "QueueEnteredTime": row.get("QueueEnteredTime"),
                "QueueWaitMinutes": row.get("QueueWaitMinutes"),
                "WipAfterStart": row.get("WipAfterStart"),
                "WipAfterEnd": row.get("WipAfterEnd"),
                "EventStatus": row.get("EventStatus"),
            }
            for row in output_rows
        ],
        "Message": "Parsed available Simio ManufacturingOrdersOutput rows.",
    }


def _sum_numeric_field(
    rows: list[dict[str, str]],
    names: tuple[str, ...],
) -> float | None:
    total = 0.0
    found = False
    for row in rows:
        for name in names:
            value = row.get(name)
            if value in {None, ""}:
                continue
            try:
                total += float(str(value))
            except ValueError:
                continue
            found = True
            break
    return total if found else None


def _unavailable_metric(message: str) -> dict[str, object]:
    return {"Status": "Unavailable", "Message": message}


def _windows_process_running(image_name: str) -> bool:
    try:
        result = subprocess.run(
            ["tasklist", "/FI", f"IMAGENAME eq {image_name}", "/FO", "CSV"],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired):
        result = None
    if result is not None and result.returncode == 0:
        output = result.stdout.lower()
        return image_name.lower() in output and "no tasks" not in output

    process_name = image_name[:-4] if image_name.lower().endswith(".exe") else image_name
    try:
        fallback = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                f"if (Get-Process -Name '{process_name}' -ErrorAction SilentlyContinue) {{ 'RUNNING' }}",
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return "RUNNING" in fallback.stdout


def _issue(
    code: str,
    message: str,
    details: dict[str, object] | None = None,
    severity: str = "Error",
) -> dict[str, object]:
    return {
        "Code": code,
        "Severity": severity,
        "Message": message,
        "Details": details or {},
    }


def _dict(value: object) -> dict[str, object]:
    return value if isinstance(value, dict) else {}


def _dict_list(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]
