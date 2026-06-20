from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Iterable


@dataclass(frozen=True, slots=True)
class IntegrationContract:
    contract_id: str
    system_id: str
    direction: str
    display_name: str
    status: str
    owner_boundary: str
    message_types: list[str]
    required_fields: list[str]
    idempotency_key_fields: list[str]
    acknowledgement: str
    replay_policy: str
    dead_letter_policy: str
    covered_spec_ids: list[str]

    def to_dict(self) -> dict[str, object]:
        return {
            "ContractID": self.contract_id,
            "SystemID": self.system_id,
            "Direction": self.direction,
            "DisplayName": self.display_name,
            "Status": self.status,
            "OwnerBoundary": self.owner_boundary,
            "MessageTypes": self.message_types,
            "RequiredFields": self.required_fields,
            "IdempotencyKeyFields": self.idempotency_key_fields,
            "Acknowledgement": self.acknowledgement,
            "ReplayPolicy": self.replay_policy,
            "DeadLetterPolicy": self.dead_letter_policy,
            "CoveredSpecIDs": self.covered_spec_ids,
        }


def integration_contract_catalog() -> list[IntegrationContract]:
    return [
        IntegrationContract(
            contract_id="ERP-INBOUND-V1",
            system_id="erp",
            direction="Inbound",
            display_name="ERP inbound master and demand sync",
            status="ContractOnly",
            owner_boundary=(
                "ERP is authoritative for demand, BOM, routings, resources, "
                "inventory balances and purchase in-transit facts."
            ),
            message_types=[
                "CustomerOrderUpsert",
                "BomSnapshot",
                "RoutingSnapshot",
                "ResourceSnapshot",
                "InventoryBalanceSnapshot",
                "PurchaseInboundSnapshot",
            ],
            required_fields=[
                "MessageID",
                "MessageType",
                "SourceSystem",
                "OccurredAt",
                "Payload",
            ],
            idempotency_key_fields=["SourceSystem", "MessageID"],
            acknowledgement="SDBR returns Accepted, Rejected or Duplicate.",
            replay_policy="Messages can be replayed by MessageID after the contract layer records them.",
            dead_letter_policy="Invalid messages enter a dead-letter queue with field-level issues.",
            covered_spec_ids=["BE-INT-001", "BE-INT-003", "BE-DATA-012"],
        ),
        IntegrationContract(
            contract_id="ERP-OUTBOUND-V1",
            system_id="erp",
            direction="Outbound",
            display_name="ERP outbound plan and release feedback",
            status="ContractOnly",
            owner_boundary=(
                "SDBR publishes confirmed plans, suggested releases, actual releases "
                "and exception states; ERP remains accounting and order authority."
            ),
            message_types=[
                "ConfirmedPlanPublished",
                "SuggestedReleaseChanged",
                "ReleaseAuthorized",
                "ReleaseExceptionReported",
            ],
            required_fields=[
                "MessageID",
                "MessageType",
                "SourceSystem",
                "OccurredAt",
                "Payload",
            ],
            idempotency_key_fields=["SourceSystem", "MessageID"],
            acknowledgement="ERP connector must acknowledge receipt before the message is considered delivered.",
            replay_policy="Outbound messages can be resent by MessageID until acknowledged.",
            dead_letter_policy="Delivery failures remain in a retry/dead-letter queue for operator review.",
            covered_spec_ids=["BE-INT-002", "BE-OUT-010"],
        ),
        IntegrationContract(
            contract_id="MES-INBOUND-V1",
            system_id="mes",
            direction="Inbound",
            display_name="MES inbound execution events",
            status="ContractStub",
            owner_boundary=(
                "MES/SCADA owns shop-floor capture; SDBR consumes events for "
                "variance, alerts and replanning."
            ),
            message_types=[
                "ArrivedBuffer",
                "StartedOperation",
                "CompletedOperation",
                "QuantityReported",
                "ExceptionReported",
            ],
            required_fields=[
                "MessageID",
                "MessageType",
                "SourceSystem",
                "OccurredAt",
                "Payload",
            ],
            idempotency_key_fields=["SourceSystem", "MessageID"],
            acknowledgement="SDBR accepts, rejects or flags the event for review.",
            replay_policy="MES can replay events by idempotency key without duplicate state changes.",
            dead_letter_policy="Schema or ownership mismatches are retained for review and replay.",
            covered_spec_ids=["BE-INT-004", "BE-EXEC-001", "BE-EXEC-004"],
        ),
        IntegrationContract(
            contract_id="MES-OUTBOUND-V1",
            system_id="mes",
            direction="Outbound",
            display_name="MES outbound dispatch and release package",
            status="ContractStub",
            owner_boundary=(
                "SDBR issues release/dispatch packages; MES decides terminal, "
                "operator and equipment execution details."
            ),
            message_types=[
                "DispatchPackageIssued",
                "DispatchPackageRevoked",
                "ReleaseHoldChanged",
            ],
            required_fields=[
                "MessageID",
                "MessageType",
                "SourceSystem",
                "OccurredAt",
                "Payload",
            ],
            idempotency_key_fields=["SourceSystem", "MessageID"],
            acknowledgement="MES returns acknowledgement or rejection with reason code.",
            replay_policy="Unacknowledged dispatch packages can be resent without changing the package version.",
            dead_letter_policy="Rejected or expired packages remain visible with replay eligibility.",
            covered_spec_ids=["BE-INT-005", "BE-REL-005"],
        ),
    ]


def integration_contracts_payload() -> dict[str, object]:
    contracts = [contract.to_dict() for contract in integration_contract_catalog()]
    return {
        "Status": "ContractOnly",
        "Contracts": contracts,
        "Summary": {
            "ContractCount": len(contracts),
            "ExternalConnectionsConfigured": 0,
            "ContractStubCount": sum(
                1 for contract in contracts if contract["Status"] == "ContractStub"
            ),
            "ContractOnlyCount": sum(
                1 for contract in contracts if contract["Status"] == "ContractOnly"
            ),
        },
    }


def find_integration_contract(contract_id: str) -> IntegrationContract | None:
    return next(
        (
            contract
            for contract in integration_contract_catalog()
            if contract.contract_id == contract_id
        ),
        None,
    )


def validate_integration_message(
    *,
    contract: IntegrationContract,
    message: dict[str, object],
    existing_messages: Iterable[dict[str, object]],
    received_at: datetime,
) -> dict[str, object]:
    issues = []
    for field in contract.required_fields:
        value = message.get(field)
        if field not in message or value is None or value == "":
            issues.append(
                {
                    "Code": "REQUIRED_FIELD_MISSING",
                    "Field": field,
                    "Severity": "Error",
                    "Message": f"{field} is required by {contract.contract_id}.",
                }
            )
    message_type = str(message.get("MessageType", ""))
    if message_type and message_type not in contract.message_types:
        issues.append(
            {
                "Code": "MESSAGE_TYPE_NOT_ALLOWED",
                "Field": "MessageType",
                "Severity": "Error",
                "Message": (
                    f"{message_type} is not allowed by {contract.contract_id}."
                ),
            }
        )

    idempotency_key = _idempotency_key(message)
    duplicate = any(
        item.get("ContractID") == contract.contract_id
        and item.get("IdempotencyKey") == idempotency_key
        for item in existing_messages
    )
    status = "Duplicate" if duplicate else ("Rejected" if issues else "Accepted")
    return {
        "ContractID": contract.contract_id,
        "MessageID": message.get("MessageID"),
        "IdempotencyKey": idempotency_key,
        "ReceivedAt": received_at.isoformat(),
        "Status": status,
        "Accepted": status in {"Accepted", "Duplicate"},
        "Issues": issues,
        "Acknowledgement": {
            "Status": status,
            "MessageID": message.get("MessageID"),
            "IdempotencyKey": idempotency_key,
        },
        "ReplayEligible": status == "Rejected",
        "DeadLetterEligible": status == "Rejected",
    }


def integration_message_record(
    *,
    contract: IntegrationContract,
    message: dict[str, object],
    validation: dict[str, object],
) -> dict[str, object]:
    return {
        "ContractID": contract.contract_id,
        "SystemID": contract.system_id,
        "Direction": contract.direction,
        "MessageID": message.get("MessageID"),
        "MessageType": message.get("MessageType"),
        "SourceSystem": message.get("SourceSystem"),
        "OccurredAt": message.get("OccurredAt"),
        "Payload": message.get("Payload"),
        "IdempotencyKey": validation["IdempotencyKey"],
        "ReceivedAt": validation["ReceivedAt"],
        "Status": validation["Status"],
        "Issues": validation["Issues"],
        "ReplayEligible": validation["ReplayEligible"],
    }


def integration_dead_letters(
    messages: Iterable[dict[str, object]],
) -> list[dict[str, object]]:
    return [
        message
        for message in messages
        if message.get("Status") == "Rejected"
    ]


def replay_integration_message(
    *,
    message_id: str,
    messages: list[dict[str, object]],
    replayed_at: datetime,
    actor_id: str,
) -> dict[str, object] | None:
    for message in messages:
        if message.get("MessageID") == message_id:
            message["ReplayRequestedAt"] = replayed_at.isoformat()
            message["ReplayRequestedBy"] = actor_id
            message["ReplayStatus"] = (
                "ReadyForReplay"
                if message.get("ReplayEligible")
                else "ReplayNotRequired"
            )
            return message
    return None


def _idempotency_key(message: dict[str, object]) -> str:
    source = str(message.get("SourceSystem", ""))
    message_id = str(message.get("MessageID", ""))
    return f"{source}:{message_id}"
