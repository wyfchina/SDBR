from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sdbr.master_data_validation import MaterialRequirement
from sdbr.planner_view import InventoryBufferPolicy
from sdbr.schedule_output import scheduled_order_rows_from_schedule


@dataclass(frozen=True, slots=True)
class WipLimit:
    scope_id: str
    current_wip_count: int
    max_wip_count: int
    order_wip_increment: int = 1


@dataclass(frozen=True, slots=True)
class MaterialAvailability:
    item_id: str
    location_id: str
    allocated_qty: float = 0.0
    inbound_qty: float = 0.0
    inbound_available_at: datetime | None = None


def release_candidate_rows_from_schedule(
    *,
    schedule: dict[str, object],
    evaluated_at: datetime,
    inventory_buffers: list[InventoryBufferPolicy],
    material_requirements: list[MaterialRequirement],
    wip_limits: list[WipLimit] | None = None,
    material_availability: list[MaterialAvailability] | None = None,
) -> list[dict[str, object]]:
    active_wip_limits = wip_limits or []
    active_material_availability = material_availability or []
    release_recommendations = _release_recommendations_by_order(schedule)
    candidates = []
    for scheduled_order in scheduled_order_rows_from_schedule(schedule):
        order_id = str(scheduled_order["OrderID"])
        suggested_release_at = release_recommendations.get(order_id)
        if suggested_release_at is None:
            continue
        minutes_until_release = max(
            0,
            int((suggested_release_at - evaluated_at).total_seconds() / 60),
        )
        rope_status = "Ready" if minutes_until_release == 0 else "Early"
        inventory_risks = _inventory_release_risks(
            order_id=order_id,
            scheduled_start=scheduled_order.get("ScheduledStart"),
            inventory_buffers=inventory_buffers,
            material_requirements=material_requirements,
            material_availability=active_material_availability,
        )
        material_status = _material_status_from_risks(inventory_risks)
        wip_risks = _wip_release_risks(order_id=order_id, wip_limits=active_wip_limits)
        wip_status = "Blocked" if wip_risks else "Clear"
        candidates.append(
            {
                "OrderID": order_id,
                "ScheduledStart": scheduled_order["ScheduledStart"],
                "ScheduledEnd": scheduled_order["ScheduledEnd"],
                "SuggestedReleaseAt": suggested_release_at.isoformat(),
                "EvaluatedAt": evaluated_at.isoformat(),
                "RopeStatus": rope_status,
                "MinutesUntilRelease": minutes_until_release,
                "MaterialStatus": material_status,
                "InventoryRisks": inventory_risks,
                "WipStatus": wip_status,
                "WipRisks": wip_risks,
                "RecommendedAction": _recommended_action(
                    rope_status=rope_status,
                    material_status=material_status,
                    wip_status=wip_status,
                ),
            }
        )
    return sorted(
        candidates,
        key=lambda item: (
            _action_rank(str(item["RecommendedAction"])),
            str(item["SuggestedReleaseAt"]),
            str(item["OrderID"]),
        ),
    )


def _release_recommendations_by_order(
    schedule: dict[str, object],
) -> dict[str, datetime]:
    result = {}
    for recommendation in schedule.get("ReleaseRecommendations", []):
        if not isinstance(recommendation, dict):
            continue
        order_id = recommendation.get("OrderID")
        suggested_release_date = recommendation.get("SuggestedReleaseDate")
        if order_id is None or not isinstance(suggested_release_date, str):
            continue
        result[str(order_id)] = datetime.fromisoformat(suggested_release_date)
    return result


def _inventory_release_risks(
    *,
    order_id: str,
    scheduled_start: object,
    inventory_buffers: list[InventoryBufferPolicy],
    material_requirements: list[MaterialRequirement],
    material_availability: list[MaterialAvailability],
) -> list[dict[str, object]]:
    buffers_by_key = {
        (buffer.item_id, buffer.location_id): buffer
        for buffer in inventory_buffers
    }
    availability_by_key = {
        (item.item_id, item.location_id): item
        for item in material_availability
    }
    scheduled_start_at = _parse_datetime(scheduled_start)
    risks: list[dict[str, object]] = []
    for requirement in material_requirements:
        if requirement.order_id != order_id:
            continue
        buffer = buffers_by_key.get((requirement.item_id, requirement.location_id))
        if buffer is None:
            continue
        availability = availability_by_key.get((requirement.item_id, requirement.location_id))
        allocated_qty = availability.allocated_qty if availability is not None else 0.0
        available_qty = buffer.on_hand_qty - allocated_qty
        projected_available = available_qty - requirement.required_qty
        if projected_available < buffer.red_zone_qty:
            if (
                availability is not None
                and availability.inbound_available_at is not None
                and scheduled_start_at is not None
                and projected_available + availability.inbound_qty >= buffer.red_zone_qty
            ):
                if availability.inbound_available_at > scheduled_start_at:
                    risks.append(
                        {
                            "OrderID": requirement.order_id,
                            "ItemID": requirement.item_id,
                            "LocationID": requirement.location_id,
                            "RiskType": "InboundLate",
                            "RequiredQty": requirement.required_qty,
                            "OnHandQty": buffer.on_hand_qty,
                            "AllocatedQty": allocated_qty,
                            "AvailableQty": available_qty,
                            "InboundQty": availability.inbound_qty,
                            "InboundAvailableAt": availability.inbound_available_at.isoformat(),
                            "ScheduledStart": scheduled_start_at.isoformat(),
                            "ProjectedAvailableQty": projected_available,
                            "ProjectedWithInboundQty": projected_available + availability.inbound_qty,
                            "RedZoneQty": buffer.red_zone_qty,
                            "Message": (
                                f"Inbound {requirement.item_id} at "
                                f"{requirement.location_id} arrives after the "
                                f"scheduled start for order {requirement.order_id}."
                            ),
                        }
                    )
                    continue
                risks.append(
                    {
                        "OrderID": requirement.order_id,
                        "ItemID": requirement.item_id,
                        "LocationID": requirement.location_id,
                        "RiskType": "InboundPending",
                        "RequiredQty": requirement.required_qty,
                        "OnHandQty": buffer.on_hand_qty,
                        "AllocatedQty": allocated_qty,
                        "AvailableQty": available_qty,
                        "InboundQty": availability.inbound_qty,
                        "InboundAvailableAt": availability.inbound_available_at.isoformat(),
                        "ProjectedAvailableQty": projected_available,
                        "ProjectedWithInboundQty": projected_available + availability.inbound_qty,
                        "RedZoneQty": buffer.red_zone_qty,
                        "Message": (
                            f"Releasing order {requirement.order_id} requires waiting "
                            f"for inbound {requirement.item_id} at "
                            f"{requirement.location_id} before scheduled start."
                        ),
                    }
                )
                continue
            risks.append(
                {
                    "OrderID": requirement.order_id,
                    "ItemID": requirement.item_id,
                    "LocationID": requirement.location_id,
                    "RequiredQty": requirement.required_qty,
                    "OnHandQty": buffer.on_hand_qty,
                    "ProjectedOnHandQty": buffer.on_hand_qty - requirement.required_qty,
                    "RedZoneQty": buffer.red_zone_qty,
                    "Message": (
                        f"Releasing order {requirement.order_id} would project "
                        f"{requirement.item_id} at {requirement.location_id} "
                        "below the red zone."
                    ),
                }
            )
    return risks


def _material_status_from_risks(risks: list[dict[str, object]]) -> str:
    if not risks:
        return "Clear"
    if all(risk.get("RiskType") == "InboundPending" for risk in risks):
        return "PendingInbound"
    return "Blocked"


def _wip_release_risks(
    *,
    order_id: str,
    wip_limits: list[WipLimit],
) -> list[dict[str, object]]:
    risks: list[dict[str, object]] = []
    for limit in wip_limits:
        projected_wip = limit.current_wip_count + limit.order_wip_increment
        if projected_wip > limit.max_wip_count:
            risks.append(
                {
                    "ScopeID": limit.scope_id,
                    "CurrentWipCount": limit.current_wip_count,
                    "MaxWipCount": limit.max_wip_count,
                    "ProjectedWipCount": projected_wip,
                    "OrderWipIncrement": limit.order_wip_increment,
                    "Message": (
                        f"Releasing order {order_id} would project WIP in "
                        f"{limit.scope_id} above the configured limit."
                    ),
                }
            )
    return risks


def _recommended_action(*, rope_status: str, material_status: str, wip_status: str) -> str:
    if material_status == "Blocked":
        return "ExpediteMaterial"
    if material_status == "PendingInbound":
        return "WaitForInbound"
    if wip_status == "Blocked":
        return "HoldForWip"
    if rope_status == "Early":
        return "HoldUntilRope"
    return "ReadyForRelease"


def _action_rank(action: str) -> int:
    return {
        "ExpediteMaterial": 0,
        "WaitForInbound": 1,
        "HoldForWip": 2,
        "ReadyForRelease": 3,
        "HoldUntilRope": 4,
    }.get(action, 3)


def _parse_datetime(value: object) -> datetime | None:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        return datetime.fromisoformat(value)
    return None
