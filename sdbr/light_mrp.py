from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from sdbr.master_data_validation import MaterialRequirement
from sdbr.planner_view import InventoryBufferPolicy
from sdbr.release_candidates import MaterialAvailability


@dataclass(frozen=True, slots=True)
class LightMrpLine:
    order_id: str
    item_id: str
    location_id: str
    required_qty: float
    on_hand_qty: float
    allocated_qty: float
    available_qty: float
    inbound_qty: float
    inbound_available_at: datetime | None
    material_check_window_end: datetime
    net_shortage_qty: float
    status: str
    reason_code: str | None

    def to_dict(self) -> dict[str, object]:
        return {
            "OrderID": self.order_id,
            "ItemID": self.item_id,
            "LocationID": self.location_id,
            "RequiredQty": self.required_qty,
            "OnHandQty": self.on_hand_qty,
            "AllocatedQty": self.allocated_qty,
            "AvailableQty": self.available_qty,
            "InboundQty": self.inbound_qty,
            "InboundAvailableAt": (
                self.inbound_available_at.isoformat()
                if self.inbound_available_at is not None
                else None
            ),
            "MaterialCheckWindowEnd": self.material_check_window_end.isoformat(),
            "NetShortageQty": self.net_shortage_qty,
            "Status": self.status,
            "ReasonCode": self.reason_code,
        }


def evaluate_light_mrp(
    *,
    material_requirements: list[MaterialRequirement],
    inventory_buffers: list[InventoryBufferPolicy],
    material_availability: list[MaterialAvailability],
    evaluated_at: datetime,
    material_check_window_minutes: int,
) -> dict[str, object]:
    if evaluated_at.tzinfo is None or evaluated_at.utcoffset() is None:
        raise ValueError("Light MRP evaluation time must be timezone-aware.")
    if material_check_window_minutes < 0:
        raise ValueError("Light MRP material check window cannot be negative.")

    inventory_by_key = {
        (item.item_id, item.location_id): item for item in inventory_buffers
    }
    availability_by_key = {
        (item.item_id, item.location_id): item for item in material_availability
    }
    window_end = evaluated_at + timedelta(minutes=material_check_window_minutes)
    lines = [
        _evaluate_requirement(
            requirement=requirement,
            inventory=inventory_by_key.get(
                (requirement.item_id, requirement.location_id)
            ),
            availability=availability_by_key.get(
                (requirement.item_id, requirement.location_id)
            ),
            window_end=window_end,
        )
        for requirement in sorted(
            material_requirements,
            key=lambda item: (item.order_id, item.item_id, item.location_id),
        )
    ]
    return {
        "EvaluationMode": "LightMRPV1",
        "Boundary": (
            "This is a first-version material feasibility check for planning "
            "and release. It does not replace ERP inventory accounting or full "
            "multi-level MRP."
        ),
        "EvaluatedAt": evaluated_at.isoformat(),
        "MaterialCheckWindowMinutes": material_check_window_minutes,
        "Summary": {
            "RequirementCount": len(lines),
            "AvailableCount": sum(1 for line in lines if line.status == "Available"),
            "CoveredByInboundCount": sum(
                1 for line in lines if line.status == "CoveredByInbound"
            ),
            "ShortageCount": sum(1 for line in lines if line.status == "Shortage"),
            "MissingInventoryCount": sum(
                1 for line in lines if line.status == "MissingInventory"
            ),
            "ReadyForPlanning": all(
                line.status in {"Available", "CoveredByInbound"} for line in lines
            ),
        },
        "Lines": [line.to_dict() for line in lines],
    }


def _evaluate_requirement(
    *,
    requirement: MaterialRequirement,
    inventory: InventoryBufferPolicy | None,
    availability: MaterialAvailability | None,
    window_end: datetime,
) -> LightMrpLine:
    if inventory is None:
        return LightMrpLine(
            order_id=requirement.order_id,
            item_id=requirement.item_id,
            location_id=requirement.location_id,
            required_qty=requirement.required_qty,
            on_hand_qty=0.0,
            allocated_qty=0.0,
            available_qty=0.0,
            inbound_qty=0.0,
            inbound_available_at=None,
            material_check_window_end=window_end,
            net_shortage_qty=requirement.required_qty,
            status="MissingInventory",
            reason_code="MISSING_INVENTORY_BALANCE",
        )

    allocated_qty = availability.allocated_qty if availability is not None else 0.0
    inbound_qty = availability.inbound_qty if availability is not None else 0.0
    inbound_available_at = (
        availability.inbound_available_at if availability is not None else None
    )
    available_qty = max(0.0, inventory.on_hand_qty - allocated_qty)
    shortage_without_inbound = max(0.0, requirement.required_qty - available_qty)
    if shortage_without_inbound == 0:
        status = "Available"
        reason_code = None
        net_shortage_qty = 0.0
    elif (
        inbound_available_at is not None
        and inbound_available_at <= window_end
        and available_qty + inbound_qty >= requirement.required_qty
    ):
        status = "CoveredByInbound"
        reason_code = "INBOUND_WITHIN_WINDOW"
        net_shortage_qty = 0.0
    else:
        status = "Shortage"
        reason_code = "MATERIAL_SHORTAGE"
        net_shortage_qty = max(
            0.0,
            requirement.required_qty
            - available_qty
            - (
                inbound_qty
                if inbound_available_at is not None
                and inbound_available_at <= window_end
                else 0.0
            ),
        )
    return LightMrpLine(
        order_id=requirement.order_id,
        item_id=requirement.item_id,
        location_id=requirement.location_id,
        required_qty=requirement.required_qty,
        on_hand_qty=inventory.on_hand_qty,
        allocated_qty=allocated_qty,
        available_qty=available_qty,
        inbound_qty=inbound_qty,
        inbound_available_at=inbound_available_at,
        material_check_window_end=window_end,
        net_shortage_qty=net_shortage_qty,
        status=status,
        reason_code=reason_code,
    )
