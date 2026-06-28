import base64
import xml.etree.ElementTree as ET
from pathlib import Path
from zipfile import ZipFile


SIMIO_TEMPLATE = Path("model/Simple_DBR_XML/SDBR_Example.xml")
SIMIO_DEFAULT_TEMPLATE = Path("model/templates/simio/SDBR_Example_Base.xml")
SIMIO_DEBUG_PACKAGE = Path("model/SDBR_Example.spfx")
SIMIO_NS = {"s": "http://www.simio.com/projects/v1"}


def _embedded_file(name: str, template: Path = SIMIO_TEMPLATE) -> str:
    root = ET.parse(template).getroot()
    for file_node in root.findall(".//s:File", SIMIO_NS):
        if file_node.attrib.get("Name") != name:
            continue
        binary = file_node.find("s:BinaryData", SIMIO_NS)
        assert binary is not None
        return base64.b64decode(binary.text.strip()).decode("utf-8")
    raise AssertionError(f"Missing embedded Simio file {name}")


def _rows(name: str) -> list[dict[str, str]]:
    fragment = ET.fromstring(_embedded_file(name))
    rows: list[dict[str, str]] = []
    for row in fragment.findall("./Row"):
        values: dict[str, str] = {}
        for prop in row.findall("./Properties/Property"):
            value = (prop.text or "").strip()
            nested = prop.find("./Value")
            if nested is not None:
                value = (nested.text or "").strip()
            values[prop.attrib["Name"]] = value
        rows.append(values)
    return rows


def _package_file(name: str, package: Path = SIMIO_DEBUG_PACKAGE) -> str:
    with ZipFile(package, "r") as archive:
        return archive.read(name.replace("\\", "/")).decode("utf-8")


def test_simio_template_uses_underscore_resource_ids_and_5dayweek():
    resources = _rows(r"Models\Model\TableData\Resources.xml")
    resource_ids = {row["ResourceName"] for row in resources}

    assert {
        "TST_WC_PREP",
        "TST_WC_DRUM",
        "TST_WC_ALT_DRUM",
        "TST_WC_PAINT",
        "TST_WC_ASSY",
        "TST_WC_PACK",
    } <= resource_ids
    assert not any(resource_id.startswith("TST-WC-") for resource_id in resource_ids)
    assert all(row["WorkSchedule"] == "5DayWeek" for row in resources)


def test_simio_template_contains_all_fg_routings_with_fixed_process_times():
    routings = _rows(r"Models\Model\TableData\Routings.xml")
    by_material = {}
    for row in routings:
        by_material.setdefault(row["MaterialName"], []).append(row)

    expected = {
        "TST-FG-A": [
            ("10", "TST_WC_PREP", "35"),
            ("20", "TST_ALT_DRUM_NODE", "95"),
            ("30", "TST_WC_ASSY", "60"),
            ("40", "TST_WC_PACK", "25"),
            ("50", "TST_SINK", "0"),
        ],
        "TST-FG-B": [
            ("10", "TST_WC_PREP", "25"),
            ("20", "TST_ALT_DRUM_NODE", "120"),
            ("30", "TST_WC_PAINT", "70"),
            ("40", "TST_WC_PACK", "30"),
            ("50", "TST_SINK", "0"),
        ],
        "TST-FG-C": [
            ("10", "TST_WC_PREP", "45"),
            ("20", "TST_ALT_DRUM_NODE", "80"),
            ("30", "TST_WC_ASSY", "90"),
            ("40", "TST_WC_PACK", "35"),
            ("50", "TST_SINK", "0"),
        ],
    }
    actual = {
        material: [
            (row["RouteNumber"], row["Sequence"], row["ProcessTime"])
            for row in sorted(rows, key=lambda item: int(item["RouteNumber"]))
        ]
        for material, rows in by_material.items()
    }

    assert actual == expected


def test_simio_template_preserves_drum_routing_destinations():
    destinations = _rows(r"Models\Model\TableData\RoutingDestinations.xml")

    assert {
        ("TST_ALT_DRUM_NODE", "Input@TST_WC_DRUM"),
        ("TST_ALT_DRUM_NODE", "Input@TST_WC_ALT_DRUM"),
    } == {(row["ResourceName"], row["Node"]) for row in destinations}


def test_simio_template_process_time_is_deterministic():
    model = _embedded_file(r"Models\Model\08358427-0097-42e8-b044-3ebfe2d801f5.xml")

    assert (
        "ManufacturingOrders.Quantity * Routings.ProcessTime"
        in model
    )
    assert (
        "Random.Triangular(.8, 1, 1.2) * ManufacturingOrders.Quantity * Routings.ProcessTime"
        not in model
    )


def test_simio_changeover_and_source_do_not_require_material_row_selection():
    # BE-SIM-002 / BE-SIM-003
    for template in [SIMIO_TEMPLATE, SIMIO_DEFAULT_TEMPLATE]:
        model = _embedded_file(
            r"Models\Model\08358427-0097-42e8-b044-3ebfe2d801f5.xml",
            template=template,
        )

        assert "OperationAttribute\">Routings.MaterialName" in model
        assert "OperationAttribute\">Materials.MaterialColor" not in model
        assert "ChangeoverMatrixName\">Resources.ChangeoverMatrix" not in model
        assert "AssignmentsBeforeExitingNewValue\">Materials.MaterialColor" not in model

    package_model = _package_file(
        r"Models\Model\08358427-0097-42e8-b044-3ebfe2d801f5.xml"
    )
    assert "OperationAttribute\">Routings.MaterialName" in package_model
    assert "OperationAttribute\">Materials.MaterialColor" not in package_model
    assert "ChangeoverMatrixName\">Resources.ChangeoverMatrix" not in package_model
    assert "AssignmentsBeforeExitingNewValue\">Materials.MaterialColor" not in package_model


def test_simio_template_contains_sdbr_process_feedback_chain():
    model = _embedded_file(r"Models\Model\08358427-0097-42e8-b044-3ebfe2d801f5.xml")

    for process_name in [
        "SDBR_MfgStart",
        "SDBR_OperationStart",
        "SDBR_OperationEnd",
        "SDBR_MfgEnd",
        "SDBR_RunEndSummary",
    ]:
        assert f'Models\\Model\\Processes\\{process_name}.xml' in model
        assert _embedded_file(rf"Models\Model\Processes\{process_name}.xml")

    assert "ProducedMaterialAddOnProcess" in model
    assert "<Value>SDBR_MfgEnd</Value>" in model
    for state_name in [
        "ActualStartTime",
        "ActualEndTime",
        "QueueEnteredTime",
        "QueueWaitMinutes",
        "WipAfterStart",
        "WipAfterEnd",
        "EventStatus",
    ]:
        assert state_name in model
    assert _embedded_file(r"Models\Model\TableData\SDBRRunSummary.xml")
