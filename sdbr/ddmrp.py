from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time, timedelta
from math import ceil

from sdbr.planner_view import InventoryBufferPolicy


@dataclass(frozen=True, slots=True)
class DecouplingPoint:
    item_id: str
    location_id: str
    buffer_profile_id: str
    dlt_minutes: int
    order_multiple_qty: float = 0.0
    minimum_order_qty: float = 0.0
    status: str = "Active"

    def to_dict(self) -> dict[str, object]:
        return {
            "ItemID": self.item_id,
            "LocationID": self.location_id,
            "BufferProfileID": self.buffer_profile_id,
            "DLTMinutes": self.dlt_minutes,
            "OrderMultipleQty": self.order_multiple_qty,
            "MinimumOrderQty": self.minimum_order_qty,
            "Status": self.status,
        }


@dataclass(frozen=True, slots=True)
class DemandSignal:
    item_id: str
    location_id: str
    demand_qty: float
    demand_due_at: datetime
    demand_type: str = "CustomerOrder"
    is_qualified_spike: bool = False
    demand_id: str | None = None
    uom: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "ItemID": self.item_id,
            "LocationID": self.location_id,
            "DemandQty": self.demand_qty,
            "DemandDueAt": self.demand_due_at.isoformat(),
            "DemandType": self.demand_type,
            "IsQualifiedSpike": self.is_qualified_spike,
            "DemandID": self.demand_id,
            "Uom": self.uom,
        }


@dataclass(frozen=True, slots=True)
class OpenSupply:
    item_id: str
    location_id: str
    supply_qty: float
    expected_at: datetime | None
    status: str = "Open"
    supply_id: str | None = None
    uom: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "ItemID": self.item_id,
            "LocationID": self.location_id,
            "SupplyQty": self.supply_qty,
            "ExpectedAt": self.expected_at.isoformat() if self.expected_at else None,
            "Status": self.status,
            "SupplyID": self.supply_id,
            "Uom": self.uom,
        }


@dataclass(frozen=True, slots=True)
class DdmrpIssue:
    severity: str
    code: str
    message: str
    item_id: str | None = None
    location_id: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "Severity": self.severity,
            "Code": self.code,
            "Message": self.message,
            "ItemID": self.item_id,
            "LocationID": self.location_id,
        }


def evaluate_ddmrp_net_flow(
    *,
    decoupling_points: list[DecouplingPoint],
    stock_buffers: list[InventoryBufferPolicy],
    demand_signals: list[DemandSignal],
    open_supply: list[OpenSupply],
    evaluated_at: datetime,
) -> dict[str, object]:
    if evaluated_at.tzinfo is None or evaluated_at.utcoffset() is None:
        raise ValueError("DDMRP evaluation time must be timezone-aware.")
    _validate_inputs(decoupling_points, stock_buffers, demand_signals, open_supply)

    issues: list[DdmrpIssue] = []
    active_points: list[DecouplingPoint] = []
    seen_points: set[tuple[str, str]] = set()
    for point in sorted(decoupling_points, key=lambda item: (item.item_id, item.location_id)):
        key = (point.item_id, point.location_id)
        if key in seen_points:
            issues.append(
                DdmrpIssue(
                    severity="Error",
                    code="DUPLICATE_DECOUPLING_POINT",
                    message="Duplicate decoupling point was ignored.",
                    item_id=point.item_id,
                    location_id=point.location_id,
                )
            )
            continue
        seen_points.add(key)
        if point.status == "Active":
            active_points.append(point)

    stock_by_key = {(item.item_id, item.location_id): item for item in stock_buffers}
    demand_by_key = _group_by_key(demand_signals)
    supply_by_key = _group_by_key(open_supply)

    lines = []
    for point in active_points:
        key = (point.item_id, point.location_id)
        buffer = stock_by_key.get(key)
        if buffer is None:
            issues.append(
                DdmrpIssue(
                    severity="Error",
                    code="STOCK_BUFFER_MISSING",
                    message="No stock buffer snapshot was provided for the decoupling point.",
                    item_id=point.item_id,
                    location_id=point.location_id,
                )
            )
            continue
        line = _evaluate_point(
            point=point,
            buffer=buffer,
            demand_signals=demand_by_key.get(key, []),
            open_supply=supply_by_key.get(key, []),
            evaluated_at=evaluated_at,
            issues=issues,
        )
        lines.append(line)

    return {
        "EvaluationMode": "DDMRPNetFlowV1",
        "Boundary": (
            "This is a DDOM runtime calculation that consumes externally configured "
            "DDMRP parameters. It does not configure Buffer Profiles or replace ERP "
            "inventory accounting."
        ),
        "EvaluatedAt": evaluated_at.isoformat(),
        "Summary": {
            "DecouplingPointCount": len(active_points),
            "LineCount": len(lines),
            "RedCount": sum(1 for line in lines if line["PlanningStatus"] == "Red"),
            "YellowCount": sum(1 for line in lines if line["PlanningStatus"] == "Yellow"),
            "GreenCount": sum(1 for line in lines if line["PlanningStatus"] == "Green"),
            "AboveGreenCount": sum(
                1 for line in lines if line["PlanningStatus"] == "AboveGreen"
            ),
            "ReplenishmentSuggestionCount": sum(
                1 for line in lines if line["SuggestedReplenishmentQty"] > 0
            ),
            "MissingDataCount": sum(1 for issue in issues if issue.severity == "Error"),
            "ReadyForRuntime": not any(issue.severity == "Error" for issue in issues),
        },
        "Lines": lines,
        "Issues": [issue.to_dict() for issue in issues],
    }


def _evaluate_point(
    *,
    point: DecouplingPoint,
    buffer: InventoryBufferPolicy,
    demand_signals: list[DemandSignal],
    open_supply: list[OpenSupply],
    evaluated_at: datetime,
    issues: list[DdmrpIssue],
) -> dict[str, object]:
    qualified_demands = [
        signal
        for signal in demand_signals
        if _is_qualified_demand(signal=signal, evaluated_at=evaluated_at)
    ]
    qualified_supply = [
        supply
        for supply in open_supply
        if _is_qualified_supply(supply=supply, issues=issues)
    ]
    qualified_demand_qty = sum(item.demand_qty for item in qualified_demands)
    qualified_supply_qty = sum(item.supply_qty for item in qualified_supply)
    top_of_red = buffer.red_zone_qty
    top_of_yellow = buffer.red_zone_qty + buffer.yellow_zone_qty
    top_of_green = top_of_yellow + buffer.green_zone_qty
    net_flow_position = buffer.on_hand_qty + qualified_supply_qty - qualified_demand_qty
    planning_status = _buffer_status(net_flow_position, top_of_red, top_of_yellow, top_of_green)
    execution_status = _buffer_status(buffer.on_hand_qty, top_of_red, top_of_yellow, top_of_green)
    planning_priority_percent = _priority_percent(net_flow_position, top_of_green)
    execution_priority_percent = _priority_percent(buffer.on_hand_qty, top_of_red)
    raw_replenishment_qty = (
        max(0.0, top_of_green - net_flow_position)
        if planning_status in {"Red", "Yellow"}
        else 0.0
    )
    suggested_replenishment_qty = _rounded_replenishment_qty(
        raw_qty=raw_replenishment_qty,
        minimum_order_qty=point.minimum_order_qty,
        order_multiple_qty=point.order_multiple_qty,
    )
    return {
        "ItemID": point.item_id,
        "LocationID": point.location_id,
        "BufferProfileID": point.buffer_profile_id,
        "DLTMinutes": point.dlt_minutes,
        "OnHandQty": buffer.on_hand_qty,
        "QualifiedOnHandQty": buffer.on_hand_qty,
        "QualifiedOpenSupplyQty": qualified_supply_qty,
        "QualifiedDemandQty": qualified_demand_qty,
        "NetFlowPosition": net_flow_position,
        "TopOfRed": top_of_red,
        "TopOfYellow": top_of_yellow,
        "TopOfGreen": top_of_green,
        "PlanningStatus": planning_status,
        "ExecutionStatus": execution_status,
        "PlanningPriorityPercent": planning_priority_percent,
        "ExecutionPriorityPercent": execution_priority_percent,
        "SuggestedReplenishmentQty": suggested_replenishment_qty,
        "RecommendedAction": "Replenish" if suggested_replenishment_qty > 0 else "Monitor",
        "DemandComponents": [
            {
                "DemandID": item.demand_id,
                "DemandQty": item.demand_qty,
                "DemandDueAt": item.demand_due_at.isoformat(),
                "DemandType": item.demand_type,
                "IsQualifiedSpike": item.is_qualified_spike,
                "Uom": item.uom,
            }
            for item in qualified_demands
        ],
        "SupplyComponents": [
            {
                "SupplyID": item.supply_id,
                "SupplyQty": item.supply_qty,
                "ExpectedAt": item.expected_at.isoformat() if item.expected_at else None,
                "Status": item.status,
                "Uom": item.uom,
            }
            for item in qualified_supply
        ],
    }


def _validate_inputs(
    decoupling_points: list[DecouplingPoint],
    stock_buffers: list[InventoryBufferPolicy],
    demand_signals: list[DemandSignal],
    open_supply: list[OpenSupply],
) -> None:
    for point in decoupling_points:
        if point.dlt_minutes < 0:
            raise ValueError(f"Decoupling point {point.item_id}/{point.location_id} has negative DLT.")
        if point.order_multiple_qty < 0 or point.minimum_order_qty < 0:
            raise ValueError(
                f"Decoupling point {point.item_id}/{point.location_id} has negative order sizing."
            )
    for buffer in stock_buffers:
        if min(buffer.on_hand_qty, buffer.red_zone_qty, buffer.yellow_zone_qty, buffer.green_zone_qty) < 0:
            raise ValueError(
                f"Stock buffer {buffer.item_id}/{buffer.location_id} has negative quantity."
            )
    for signal in demand_signals:
        if signal.demand_qty < 0:
            raise ValueError(f"Demand signal {signal.item_id}/{signal.location_id} has negative demand.")
        _require_aware(signal.demand_due_at, "Demand signal due time")
    for supply in open_supply:
        if supply.supply_qty < 0:
            raise ValueError(f"Open supply {supply.item_id}/{supply.location_id} has negative supply.")
        if supply.expected_at is not None:
            _require_aware(supply.expected_at, "Open supply expected time")
    _validate_component_uoms(demand_signals, open_supply)


def _validate_component_uoms(
    demand_signals: list[DemandSignal],
    open_supply: list[OpenSupply],
) -> None:
    expected_by_key: dict[tuple[str, str], str] = {}
    for source, items in (("DemandSignal", demand_signals), ("OpenSupply", open_supply)):
        for item in items:
            if item.uom is None:
                continue
            key = (item.item_id, item.location_id)
            expected = expected_by_key.setdefault(key, item.uom)
            if item.uom != expected:
                raise ValueError(
                    f"UnitOfMeasure reference mismatch for {key[0]}/{key[1]}: "
                    f"expected {expected}, but {source} uses {item.uom}."
                )


def _require_aware(value: datetime, label: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{label} must be timezone-aware.")


def _is_qualified_demand(
    *,
    signal: DemandSignal,
    evaluated_at: datetime,
) -> bool:
    due_at = signal.demand_due_at.astimezone(evaluated_at.tzinfo)
    day_start = datetime.combine(evaluated_at.date(), time.min, tzinfo=evaluated_at.tzinfo)
    day_end = day_start + timedelta(days=1)
    return due_at < day_start or day_start <= due_at < day_end or signal.is_qualified_spike


def _is_qualified_supply(
    *,
    supply: OpenSupply,
    issues: list[DdmrpIssue],
) -> bool:
    if supply.status in {"Cancelled", "Closed", "Completed", "Received"}:
        return False
    if supply.expected_at is None:
        issues.append(
            DdmrpIssue(
                severity="Warning",
                code="OPEN_SUPPLY_DATE_MISSING",
                message="Open supply without expected date was excluded from net flow.",
                item_id=supply.item_id,
                location_id=supply.location_id,
            )
        )
        return False
    return True


def _priority_percent(numerator: float, denominator: float) -> float | None:
    if denominator <= 0:
        return None
    return numerator / denominator * 100


def _rounded_replenishment_qty(
    *,
    raw_qty: float,
    minimum_order_qty: float,
    order_multiple_qty: float,
) -> float:
    if raw_qty <= 0:
        return 0.0
    qty = max(raw_qty, minimum_order_qty) if minimum_order_qty > 0 else raw_qty
    if order_multiple_qty > 0:
        qty = ceil(qty / order_multiple_qty) * order_multiple_qty
    return qty


def _buffer_status(value: float, top_of_red: float, top_of_yellow: float, top_of_green: float) -> str:
    if value <= top_of_red:
        return "Red"
    if value <= top_of_yellow:
        return "Yellow"
    if value <= top_of_green:
        return "Green"
    return "AboveGreen"


def _group_by_key(items: list[DemandSignal] | list[OpenSupply]) -> dict[tuple[str, str], list]:
    result: dict[tuple[str, str], list] = {}
    for item in items:
        result.setdefault((item.item_id, item.location_id), []).append(item)
    return result
