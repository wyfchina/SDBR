from __future__ import annotations

from copy import deepcopy
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
from threading import Thread

from fastapi.testclient import TestClient
from jsonschema import Draft202012Validator

from sdbr.api import create_app
from sdbr.ddsop_contracts import (
    canonical_operating_model_fingerprint,
    config_ack_schema,
    feedback_ack_schema,
    feedback_schema,
)
from sdbr.environment_paths import resolve_ddae_interface_contract_root
from sdbr.state_store import WorkbenchStateStore
from sdbr.test_data import (
    BASELINE_MASTER_DATA_VERSION_ID,
    BASELINE_OPERATIONAL_STATE_ID,
    seed_baseline_test_data,
)


CONTRACT_ROOT = resolve_ddae_interface_contract_root()
CONFIG_EXAMPLES = CONTRACT_ROOT / "contracts" / "ddsop-config-inbound-v1" / "examples"


def test_ddsop_config_inbound_accepts_ack_and_rejects_duplicate() -> None:
    store = _store_with_contract_references()
    client = TestClient(create_app(state_store=store))
    message = _load_example("golden-operating-model-configuration.json")

    response = client.post("/planner/workbench/ddsop/config-inbound", json=message)
    assert response.status_code == 200
    ack = response.json()["Data"]["Ack"]
    Draft202012Validator(config_ack_schema()).validate(ack)
    assert ack["ProcessingStatus"] == "Accepted"
    assert ack["UsableForPlanningRun"] is True
    assert ack["AcceptedConfigurationID"] == "DDSOP-OMC-20260626-A"

    duplicate = client.post("/planner/workbench/ddsop/config-inbound", json=message)
    assert duplicate.status_code == 200
    duplicate_ack = duplicate.json()["Data"]["Ack"]
    Draft202012Validator(config_ack_schema()).validate(duplicate_ack)
    assert duplicate_ack["ProcessingStatus"] == "Duplicate"


def test_ddsop_config_inbound_rejects_draft_status() -> None:
    client = TestClient(create_app(state_store=_store_with_contract_references()))
    message = _load_example("rejected-draft-status.json")

    response = client.post("/planner/workbench/ddsop/config-inbound", json=message)

    assert response.status_code == 200
    ack = response.json()["Data"]["Ack"]
    Draft202012Validator(config_ack_schema()).validate(ack)
    assert ack["ProcessingStatus"] == "Rejected"
    assert ack["UsableForPlanningRun"] is False
    assert ack["Errors"][0]["Code"] == "CONFIGURATION_NOT_APPROVED"


def test_planning_run_freezes_operating_model_configuration_and_feedback_payloads() -> None:
    store = _store_with_contract_references()
    seed_baseline_test_data(store)
    _add_contract_references(store)
    _align_master_data_with_golden_config(store)
    client = TestClient(create_app(state_store=store))
    message = _load_example("golden-operating-model-configuration.json")
    assert client.post("/planner/workbench/ddsop/config-inbound", json=message).status_code == 200

    create_response = client.post(
        "/planner/workbench/planning-runs",
        json={
            "RunID": "TST-RUN-DDSOP-FREEZE-001",
            "ProblemID": "TST-PROBLEM-DDSOP-FREEZE",
            "MasterDataVersionID": BASELINE_MASTER_DATA_VERSION_ID,
            "OperationalStateSnapshotID": BASELINE_OPERATIONAL_STATE_ID,
            "OperatingModelConfigurationID": "DDSOP-OMC-20260626-A",
            "ScheduleStartAt": "2026-06-22T08:00:00+08:00",
            "SolverBackendID": "ortools",
            "RequestedBy": "planner-1",
            "RequestedAt": "2026-06-22T07:50:00+08:00",
        },
    )
    assert create_response.status_code == 200
    pending = create_response.json()["Data"]["PlanningRun"]
    assert pending["OperatingModelConfigurationID"] == "DDSOP-OMC-20260626-A"
    assert pending["OperatingModelFingerprint"] == message["Payload"]["Fingerprint"]
    assert pending["SchedulingConfigurationID"] == "DDSOP-SCH-20260626-A"
    assert pending["DDMRPConfigurationID"] == "DDSOP-DDMRP-20260626-A"

    execute_response = client.post(
        "/planner/workbench/planning-runs/TST-RUN-DDSOP-FREEZE-001/execute",
        json={
            "ExecutedBy": "planner-1",
            "StartedAt": "2026-06-22T07:55:00+08:00",
            "CompletedAt": "2026-06-22T07:57:00+08:00",
        },
    )
    assert execute_response.status_code == 200
    completed = execute_response.json()["Data"]["PlanningRun"]
    assert completed["OperatingModelConfigurationID"] == "DDSOP-OMC-20260626-A"

    planning_feedback = client.get(
        "/planner/workbench/ddsop/feedback/planning-runs/TST-RUN-DDSOP-FREEZE-001"
    )
    assert planning_feedback.status_code == 200
    planning_message = planning_feedback.json()["Data"]["Message"]
    Draft202012Validator(feedback_schema()).validate(planning_message)
    assert planning_message["Payload"]["FeedbackType"] == "PlanningRunFeedback"

    variance_feedback = client.get(
        "/planner/workbench/ddsop/feedback/variance-analysis/TST-RUN-DDSOP-FREEZE-001"
    )
    assert variance_feedback.status_code == 200
    variance_message = variance_feedback.json()["Data"]["Message"]
    Draft202012Validator(feedback_schema()).validate(variance_message)
    assert variance_message["Payload"]["FeedbackType"] == "VarianceAnalysisFeedback"


def test_ddsop_feedback_delivery_pushes_to_endpoint_and_records_ack() -> None:
    store = _store_with_contract_references()
    seed_baseline_test_data(store)
    _add_contract_references(store)
    _align_master_data_with_golden_config(store)
    client = TestClient(create_app(state_store=store))
    message = _load_example("golden-operating-model-configuration.json")
    assert client.post("/planner/workbench/ddsop/config-inbound", json=message).status_code == 200
    assert (
        _create_ddsop_planning_run(
            client,
            run_id="TST-RUN-DDSOP-DELIVERY-001",
        ).status_code
        == 200
    )
    assert (
        client.post(
            "/planner/workbench/planning-runs/TST-RUN-DDSOP-DELIVERY-001/execute",
            json={
                "ExecutedBy": "planner-1",
                "StartedAt": "2026-06-22T07:55:00+08:00",
                "CompletedAt": "2026-06-22T07:57:00+08:00",
            },
        ).status_code
        == 200
    )
    server, received_messages = _start_feedback_ack_server()
    try:
        response = client.post(
            "/planner/workbench/ddsop/feedback/runs/TST-RUN-DDSOP-DELIVERY-001/deliver",
            json={
                "TargetEndpoint": f"http://127.0.0.1:{server.server_port}/feedback",
                "DeliveredBy": "contract-test",
                "DeliveredAt": "2026-06-22T08:05:00+00:00",
            },
        )
    finally:
        server.shutdown()
        server.server_close()

    assert response.status_code == 200
    records = response.json()["Data"]["DeliveryRecords"]
    assert len(records) == 2
    assert len(received_messages) == 2
    for record in records:
        assert record["DeliveryStatus"] == "Accepted"
        assert record["Ack"] is not None
        Draft202012Validator(feedback_ack_schema()).validate(record["Ack"])
        assert record["Ack"]["OriginalMessageID"] == record["MessageID"]

    ledger_response = client.get("/planner/workbench/ddsop/feedback/delivery-ledger")
    assert ledger_response.status_code == 200
    assert ledger_response.json()["Data"]["RecordCount"] == 2


def test_fingerprint_uses_contract_canonical_payload() -> None:
    message = _load_example("golden-operating-model-configuration.json")
    assert (
        canonical_operating_model_fingerprint(message["Payload"])
        == message["Payload"]["Fingerprint"]
    )


def test_planning_run_rejects_unresolved_required_master_data_references() -> None:
    scenarios = [
        ("ProductID", _remove_golden_product_reference),
        ("PrimaryRoutingID", _remove_golden_primary_routing_reference),
        ("ResourceID", _remove_golden_resource_reference),
        ("ItemID", _remove_golden_item_reference),
        ("LocationID", _remove_golden_location_reference),
    ]
    for expected_reference_type, mutator in scenarios:
        store = _store_with_contract_references()
        seed_baseline_test_data(store)
        _add_contract_references(store)
        _align_master_data_with_golden_config(store)
        mutator(store.master_data_versions[BASELINE_MASTER_DATA_VERSION_ID])
        client = TestClient(create_app(state_store=store))
        message = _load_example("golden-operating-model-configuration.json")
        assert client.post("/planner/workbench/ddsop/config-inbound", json=message).status_code == 200

        response = _create_ddsop_planning_run(
            client,
            run_id=f"TST-RUN-DDSOP-MISSING-{expected_reference_type}",
        )

        assert response.status_code == 409
        data = response.json()["Data"]
        assert data["Status"] == "REFERENCE_NOT_FOUND"
        assert any(
            error["Code"] == "REFERENCE_NOT_FOUND"
            and error["ReferenceType"] == expected_reference_type
            for error in data["Errors"]
        )


def test_legacy_planning_run_path_is_marked_non_ddsop_contract_path() -> None:
    store = WorkbenchStateStore()
    seed_baseline_test_data(store)
    client = TestClient(create_app(state_store=store))

    response = client.post(
        "/planner/workbench/planning-runs",
        json={
            "RunID": "TST-RUN-LEGACY-NON-DDSOP-001",
            "ProblemID": "TST-PROBLEM-LEGACY",
            "MasterDataVersionID": BASELINE_MASTER_DATA_VERSION_ID,
            "OperationalStateSnapshotID": BASELINE_OPERATIONAL_STATE_ID,
            "ScheduleStartAt": "2026-06-22T08:00:00+08:00",
            "SolverBackendID": "ortools",
            "RequestedBy": "planner-1",
            "RequestedAt": "2026-06-22T07:50:00+08:00",
        },
    )

    assert response.status_code == 200
    run = response.json()["Data"]["PlanningRun"]
    assert run["ContractPath"] == "LegacyNonDdsopConfigInboundV1"
    assert run["LegacyPlanningRunPath"] is True


def _load_example(filename: str) -> dict[str, object]:
    return json.loads((CONFIG_EXAMPLES / filename).read_text(encoding="utf-8-sig"))


def _store_with_contract_references() -> WorkbenchStateStore:
    store = WorkbenchStateStore()
    _add_contract_references(store)
    return store


def _add_contract_references(store: WorkbenchStateStore) -> None:
    store.dbr_release_policies["DBR-RELEASE-POLICY-20260626-A"] = {
        "VersionID": "DBR-RELEASE-POLICY-20260626-A",
        "Status": "Active",
    }
    store.base_calendars["5DayWeek"] = {
        "CalendarID": "5DayWeek",
        "Status": "Active",
    }
    store.scheduling_strategy_versions["SCH-STRATEGY-DDOM-FLOW-001"] = {
        "StrategyID": "SCH-STRATEGY-DDOM-FLOW-001",
        "Status": "Active",
        "ObjectiveWeights": {
            "TardinessWeight": 100.0,
            "MakespanWeight": 1.0,
            "AlternateResourcePenaltyWeight": 10.0,
        },
    }


def _align_master_data_with_golden_config(store: WorkbenchStateStore) -> None:
    master_data = store.master_data_versions[BASELINE_MASTER_DATA_VERSION_ID]
    if not any(
        item.get("ProductID") == "TST-FG-A" and item.get("RoutingID") == "ROUTE-FG-A"
        for item in master_data["Routings"]
    ):
        source_routing = next(
            item for item in master_data["Routings"] if item.get("ProductID") == "TST-FG-A"
        )
        routing = deepcopy(source_routing)
        routing["RoutingID"] = "ROUTE-FG-A"
        routing["IsPrimary"] = True
        master_data["Routings"].append(routing)
    if not any(
        item.get("ItemID") == "RM-STEEL" and item.get("LocationID") == "PLANT-A"
        for item in master_data["InventoryBuffers"]
    ):
        master_data["InventoryBuffers"].append(
            {
                "ItemID": "RM-STEEL",
                "LocationID": "PLANT-A",
                "OnHandQty": 500,
                "RedZoneQty": 100,
                "YellowZoneQty": 250,
                "GreenZoneQty": 450,
            }
        )


def _create_ddsop_planning_run(client: TestClient, *, run_id: str):
    return client.post(
        "/planner/workbench/planning-runs",
        json={
            "RunID": run_id,
            "ProblemID": "TST-PROBLEM-DDSOP-REFERENCES",
            "MasterDataVersionID": BASELINE_MASTER_DATA_VERSION_ID,
            "OperationalStateSnapshotID": BASELINE_OPERATIONAL_STATE_ID,
            "OperatingModelConfigurationID": "DDSOP-OMC-20260626-A",
            "ScheduleStartAt": "2026-06-22T08:00:00+08:00",
            "SolverBackendID": "ortools",
            "RequestedBy": "planner-1",
            "RequestedAt": "2026-06-22T07:50:00+08:00",
        },
    )


def _start_feedback_ack_server():
    received_messages: list[dict[str, object]] = []

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):  # noqa: N802
            content_length = int(self.headers.get("Content-Length", "0"))
            body = self.rfile.read(content_length)
            message = json.loads(body.decode("utf-8"))
            received_messages.append(message)
            payload = message["Payload"]
            ack = {
                "ContractID": "DDSOP-FEEDBACK-OUTBOUND-V1",
                "ContractVersion": "1.0.0",
                "OriginalMessageID": message["MessageID"],
                "IdempotencyKey": message["IdempotencyKey"],
                "ProcessingStatus": "Accepted",
                "ReceivedAt": "2026-06-22T08:06:00+00:00",
                "LinkedOperatingModelConfigurationID": payload[
                    "OperatingModelConfigurationID"
                ],
                "LinkedOperatingModelFingerprint": payload[
                    "OperatingModelFingerprint"
                ],
                "LinkedPlanningRunID": payload["PlanningRunID"],
                "Errors": [],
            }
            encoded = json.dumps(ack).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)

        def log_message(self, format, *args):  # noqa: A002
            return

    server = HTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, received_messages


def _remove_golden_product_reference(master_data: dict[str, object]) -> None:
    for collection_name in ("Routings", "Orders"):
        for item in master_data[collection_name]:
            if item.get("ProductID") == "TST-FG-A":
                item["ProductID"] = "REMOVED-TST-FG-A"


def _remove_golden_primary_routing_reference(master_data: dict[str, object]) -> None:
    master_data["Routings"] = [
        item
        for item in master_data["Routings"]
        if not (
            item.get("ProductID") == "TST-FG-A"
            and item.get("RoutingID") == "ROUTE-FG-A"
        )
    ]


def _remove_golden_resource_reference(master_data: dict[str, object]) -> None:
    master_data["Resources"] = [
        item for item in master_data["Resources"] if item.get("ResourceID") != "TST_WC_DRUM"
    ]


def _remove_golden_item_reference(master_data: dict[str, object]) -> None:
    for collection_name in ("InventoryBuffers", "MaterialRequirements"):
        master_data[collection_name] = [
            item for item in master_data[collection_name] if item.get("ItemID") != "RM-STEEL"
        ]


def _remove_golden_location_reference(master_data: dict[str, object]) -> None:
    for collection_name in ("InventoryBuffers", "MaterialRequirements"):
        master_data[collection_name] = [
            item
            for item in master_data[collection_name]
            if item.get("LocationID") != "PLANT-A"
        ]
