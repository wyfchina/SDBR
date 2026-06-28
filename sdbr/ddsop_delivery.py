from __future__ import annotations

from copy import deepcopy
from datetime import datetime
import json
from typing import Any, Mapping
from urllib import error, request

from jsonschema import Draft202012Validator

from sdbr.ddsop_contracts import feedback_ack_schema


def deliver_ddsop_feedback_message(
    message: Mapping[str, Any],
    *,
    target_endpoint: str,
    attempted_at: datetime,
    timeout_seconds: int = 10,
) -> dict[str, Any]:
    payload = deepcopy(dict(message))
    delivery_id = f"SDBR-DELIVERY-{payload.get('MessageID', 'UNKNOWN')}"
    ledger_record: dict[str, Any] = {
        "DeliveryID": delivery_id,
        "ContractID": payload.get("ContractID"),
        "ContractVersion": payload.get("ContractVersion"),
        "MessageID": payload.get("MessageID"),
        "MessageType": payload.get("MessageType"),
        "IdempotencyKey": payload.get("IdempotencyKey"),
        "TargetEndpoint": target_endpoint,
        "AttemptedAt": attempted_at.isoformat(),
        "DeliveryStatus": "Pending",
        "ResponseStatusCode": None,
        "Ack": None,
        "Error": None,
        "RequestPayload": payload,
    }

    try:
        http_request = request.Request(
            target_endpoint,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with request.urlopen(http_request, timeout=timeout_seconds) as response:
            response_body = response.read().decode("utf-8")
            ack = json.loads(response_body) if response_body else {}
            Draft202012Validator(feedback_ack_schema()).validate(ack)
            ledger_record.update(
                {
                    "DeliveryStatus": str(ack.get("ProcessingStatus", "Accepted")),
                    "ResponseStatusCode": response.status,
                    "Ack": ack,
                }
            )
    except error.HTTPError as exc:
        response_body = exc.read().decode("utf-8", errors="replace")
        ledger_record.update(
            {
                "DeliveryStatus": "Failed",
                "ResponseStatusCode": exc.code,
                "Error": response_body or str(exc),
            }
        )
    except Exception as exc:  # pragma: no cover - exercised through integration paths.
        ledger_record.update({"DeliveryStatus": "Failed", "Error": str(exc)})
    return ledger_record
