from fastapi.testclient import TestClient

from sdbr.api import create_app
from sdbr.state_store import SQLiteWorkbenchStateStore, WorkbenchStateStore


def test_integration_contract_catalog_defines_erp_mes_boundaries():
    # BE-INT-001 / BE-INT-002 / BE-INT-004 / BE-INT-005
    client = TestClient(create_app())

    response = client.get("/planner/workbench/integrations/contracts")

    assert response.status_code == 200
    data = response.json()["Data"]
    assert data["Status"] == "MockApiFirstVersion"
    assert data["FirstVersionIntegrationMode"] == "MockAPI"
    assert data["MesDispatchDeliveryMode"] == "RecommendationOnly"
    assert data["AdapterStrategy"]["ActiveAdapterID"] == "mock_api"
    assert data["AdapterStrategy"]["OutboundMesPolicy"]["SendsToMes"] is False
    assert data["Summary"]["ContractCount"] == 4
    assert data["Summary"]["MockApiEnabled"] is True
    contracts = {item["ContractID"]: item for item in data["Contracts"]}
    assert contracts["ERP-INBOUND-V1"]["Status"] == "ContractOnly"
    assert contracts["ERP-INBOUND-V1"]["OwnerBoundary"].startswith("ERP is authoritative")
    assert "CustomerOrderUpsert" in contracts["ERP-INBOUND-V1"]["MessageTypes"]
    assert contracts["ERP-OUTBOUND-V1"]["Direction"] == "Outbound"
    assert "ConfirmedPlanPublished" in contracts["ERP-OUTBOUND-V1"]["MessageTypes"]
    assert contracts["MES-INBOUND-V1"]["Status"] == "ContractStub"
    assert "ArrivedBuffer" in contracts["MES-INBOUND-V1"]["MessageTypes"]
    assert contracts["MES-OUTBOUND-V1"]["Status"] == "ContractStub"
    assert "DispatchPackageIssued" in contracts["MES-OUTBOUND-V1"]["MessageTypes"]


def test_be_int_mock_api_status_declares_replaceable_adapter_boundary():
    # BE-INT-001 / BE-INT-004 / BE-INT-005 / BE-INT-007
    client = TestClient(create_app())

    response = client.get("/planner/workbench/integrations/mock-api/status")

    assert response.status_code == 200
    data = response.json()["Data"]
    assert data["ActiveAdapterID"] == "mock_api"
    assert data["OutboundMesPolicy"]["DeliveryMode"] == "RecommendationOnly"
    assert data["OutboundMesPolicy"]["SendsToMes"] is False
    adapter_statuses = {item["AdapterID"]: item["Status"] for item in data["Adapters"]}
    assert adapter_statuses == {
        "mock_api": "EnabledForV1",
        "direct_erp_mes": "Deferred",
        "uns_mqtt": "Deferred",
    }


def test_integration_message_stub_accepts_and_deduplicates_by_idempotency_key():
    # BE-INT-001 / BE-INT-004 / BE-INT-007
    store = WorkbenchStateStore()
    client = TestClient(create_app(state_store=store))
    message = {
        "ContractID": "ERP-INBOUND-V1",
        "MessageID": "ERP-MSG-001",
        "MessageType": "CustomerOrderUpsert",
        "SourceSystem": "ERP-TEST",
        "OccurredAt": "2026-06-20T09:00:00+00:00",
        "Payload": {"OrderID": "WO-ERP-001"},
    }

    first = client.post("/planner/workbench/integrations/messages", json=message)
    duplicate = client.post("/planner/workbench/integrations/messages", json=message)

    assert first.status_code == 200
    assert first.json()["Data"]["Status"] == "Accepted"
    assert first.json()["Data"]["Acknowledgement"]["Status"] == "Accepted"
    assert duplicate.status_code == 200
    assert duplicate.json()["Data"]["Status"] == "Duplicate"
    assert len(store.integration_messages) == 1
    assert store.integration_messages[0]["IdempotencyKey"] == "ERP-TEST:ERP-MSG-001"


def test_integration_message_stub_dead_letters_invalid_payload_and_allows_replay():
    # BE-INT-004 / BE-INT-005 / BE-INT-007
    store = WorkbenchStateStore()
    client = TestClient(create_app(state_store=store))

    rejected = client.post(
        "/planner/workbench/integrations/messages",
        json={
            "ContractID": "MES-INBOUND-V1",
            "MessageID": "MES-MSG-001",
            "MessageType": "UnsupportedEvent",
            "SourceSystem": "MES-TEST",
            "OccurredAt": "2026-06-20T09:05:00+00:00",
            "Payload": {"OrderID": "WO-1"},
        },
    )

    assert rejected.status_code == 409
    rejected_data = rejected.json()["Data"]
    assert rejected_data["Status"] == "Rejected"
    assert rejected_data["ReplayEligible"] is True
    assert rejected_data["Issues"][0]["Code"] == "MESSAGE_TYPE_NOT_ALLOWED"

    dead_letters = client.get("/planner/workbench/integrations/messages/dead-letter")
    assert dead_letters.status_code == 200
    assert dead_letters.json()["Data"]["Count"] == 1
    assert dead_letters.json()["Data"]["Messages"][0]["MessageID"] == "MES-MSG-001"

    replay = client.post(
        "/planner/workbench/integrations/messages/MES-MSG-001/replay",
        json={
            "ActorID": "admin-1",
            "ReplayedAt": "2026-06-20T09:10:00+00:00",
        },
    )

    assert replay.status_code == 200
    message = replay.json()["Data"]["Message"]
    assert message["ReplayStatus"] == "ReadyForReplay"
    assert message["ReplayRequestedBy"] == "admin-1"


def test_integration_message_stub_reports_missing_required_fields():
    # BE-INT-001 / BE-INT-007
    client = TestClient(create_app())

    response = client.post(
        "/planner/workbench/integrations/messages",
        json={
            "ContractID": "ERP-INBOUND-V1",
            "MessageID": "ERP-MSG-002",
            "SourceSystem": "ERP-TEST",
            "OccurredAt": "2026-06-20T09:15:00+00:00",
            "Payload": {},
        },
    )

    assert response.status_code == 409
    data = response.json()["Data"]
    assert data["Status"] == "Rejected"
    assert {
        "Code": "REQUIRED_FIELD_MISSING",
        "Field": "MessageType",
        "Severity": "Error",
        "Message": "MessageType is required by ERP-INBOUND-V1.",
    } in data["Issues"]


def test_integration_dead_letter_persists_for_sqlite_store(tmp_path):
    # BE-INT-007 / BE-OPS-003
    database_path = tmp_path / "workbench.db"
    client = TestClient(create_app(state_store=SQLiteWorkbenchStateStore(database_path)))

    response = client.post(
        "/planner/workbench/integrations/messages",
        json={
            "ContractID": "MES-INBOUND-V1",
            "MessageID": "MES-MSG-SQLITE-1",
            "MessageType": "UnsupportedEvent",
            "SourceSystem": "MES-TEST",
            "OccurredAt": "2026-06-20T09:20:00+00:00",
            "Payload": {"OrderID": "WO-1"},
        },
    )
    assert response.status_code == 409

    reloaded = TestClient(create_app(state_store=SQLiteWorkbenchStateStore(database_path)))
    dead_letters = reloaded.get("/planner/workbench/integrations/messages/dead-letter")

    assert dead_letters.status_code == 200
    assert dead_letters.json()["Data"]["Messages"][0]["MessageID"] == "MES-MSG-SQLITE-1"
