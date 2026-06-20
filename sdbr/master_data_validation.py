from __future__ import annotations

from dataclasses import dataclass

from sdbr.planner_view import InventoryBufferPolicy
from sdbr.planner_workbench import Resource, Routing, SchedulingOrder


@dataclass(frozen=True, slots=True)
class MasterDataIssue:
    severity: str
    code: str
    message: str
    field: str


@dataclass(frozen=True, slots=True)
class MasterDataValidationResult:
    is_valid: bool
    summary: dict[str, int]
    issues: list[MasterDataIssue]


@dataclass(frozen=True, slots=True)
class MaterialRequirement:
    order_id: str
    item_id: str
    location_id: str
    required_qty: float


def validate_master_data(
    resources: list[Resource],
    routings: list[Routing],
    orders: list[SchedulingOrder],
    inventory_buffers: list[InventoryBufferPolicy],
    material_requirements: list[MaterialRequirement] | None = None,
    calendar_timezone: str | None = None,
) -> MasterDataValidationResult:
    resource_ids = {resource.resource_id for resource in resources}
    routed_products = {routing.product_id for routing in routings}
    order_ids = {order.order_id for order in orders}
    inventory_buffer_keys = {
        (buffer.item_id, buffer.location_id)
        for buffer in inventory_buffers
    }
    material_requirements = material_requirements or []
    issues: list[MasterDataIssue] = []

    seen_resource_ids: set[str] = set()
    duplicate_resource_ids: set[str] = set()
    for resource in resources:
        if resource.resource_id in seen_resource_ids:
            duplicate_resource_ids.add(resource.resource_id)
        seen_resource_ids.add(resource.resource_id)
        for capacity_date, capacity_minutes in sorted(resource.daily_capacity_minutes.items()):
            if capacity_minutes < 0:
                issues.append(
                    MasterDataIssue(
                        severity="Error",
                        code="NEGATIVE_RESOURCE_CAPACITY",
                        message=(
                            f"Resource {resource.resource_id} has negative capacity "
                            f"on {capacity_date.isoformat()}."
                        ),
                        field=(
                            f"Resources.{resource.resource_id}."
                            f"DailyCapacityMinutes.{capacity_date.isoformat()}"
                        ),
                    )
                )
        if resource.calendar is not None:
            for weekday in sorted(resource.calendar.working_weekdays):
                if weekday < 0 or weekday > 6:
                    issues.append(
                        MasterDataIssue(
                            severity="Error",
                            code="INVALID_CALENDAR_WEEKDAY",
                            message=(
                                f"Calendar {resource.calendar.calendar_id} "
                                f"has invalid weekday {weekday}."
                            ),
                            field=(
                                f"Resources.{resource.resource_id}."
                                f"Calendar.WorkingWeekdays"
                            ),
                        )
                    )
            for shift in resource.calendar.shifts:
                if shift.end <= shift.start:
                    issues.append(
                        MasterDataIssue(
                            severity="Error",
                            code="INVALID_SHIFT_WINDOW",
                            message=(
                                f"Shift {shift.name} in calendar "
                                f"{resource.calendar.calendar_id} must end after it starts."
                            ),
                            field=(
                                f"Resources.{resource.resource_id}."
                                f"Calendar.Shifts.{shift.name}"
                            ),
                        )
                    )
            for maintenance in resource.calendar.maintenance_windows:
                if maintenance.end <= maintenance.start:
                    issues.append(
                        MasterDataIssue(
                            severity="Error",
                            code="INVALID_MAINTENANCE_WINDOW",
                            message=(
                                "Maintenance window in calendar "
                                f"{resource.calendar.calendar_id} must end after it starts."
                            ),
                            field=(
                                f"Resources.{resource.resource_id}."
                                f"Calendar.MaintenanceWindows"
                            ),
                        )
                    )
    for resource_id in sorted(duplicate_resource_ids):
        issues.append(
            MasterDataIssue(
                severity="Error",
                code="DUPLICATE_RESOURCE_ID",
                message=f"Resource {resource_id} is defined more than once.",
                field=f"Resources.{resource_id}.ResourceID",
            )
        )

    if not any(resource.is_constraint for resource in resources):
        issues.append(
            MasterDataIssue(
                severity="Error",
                code="NO_CONSTRAINT_RESOURCE",
                message="At least one resource must be marked as the drum constraint.",
                field="Resources.IsConstraint",
            )
        )

    if calendar_timezone is None and any(resource.calendar is not None for resource in resources):
        issues.append(
            MasterDataIssue(
                severity="Error",
                code="MISSING_CALENDAR_TIMEZONE",
                message="CalendarTimezone is required when resource calendars are configured.",
                field="CalendarTimezone",
            )
        )

    routing_ids_by_product: dict[str, set[str]] = {}
    duplicate_routing_keys: set[tuple[str, str]] = set()
    primary_count_by_product: dict[str, int] = {}
    for routing in routings:
        product_routing_ids = routing_ids_by_product.setdefault(routing.product_id, set())
        if routing.routing_id in product_routing_ids:
            duplicate_routing_keys.add((routing.product_id, routing.routing_id))
        product_routing_ids.add(routing.routing_id)
        if routing.is_primary:
            primary_count_by_product[routing.product_id] = (
                primary_count_by_product.get(routing.product_id, 0) + 1
            )
        seen_sequences: set[int] = set()
        duplicate_sequences: set[int] = set()
        for operation in routing.operations:
            if operation.duration_minutes <= 0:
                issues.append(
                    MasterDataIssue(
                        severity="Error",
                        code="NON_POSITIVE_OPERATION_DURATION",
                        message=f"Operation {operation.operation_id} must have a positive duration.",
                        field=(
                            f"Routings.{routing.product_id}.{routing.routing_id}."
                            f"Operations.{operation.operation_id}.DurationMinutes"
                        ),
                    )
                )
            if operation.sequence <= 0:
                issues.append(
                    MasterDataIssue(
                        severity="Error",
                        code="NON_POSITIVE_OPERATION_SEQUENCE",
                        message=f"Operation {operation.operation_id} must have a positive sequence.",
                        field=(
                            f"Routings.{routing.product_id}.{routing.routing_id}."
                            f"Operations.{operation.operation_id}.Sequence"
                        ),
                    )
                )
            if operation.sequence in seen_sequences:
                duplicate_sequences.add(operation.sequence)
            seen_sequences.add(operation.sequence)
            if operation.resource_id not in resource_ids:
                issues.append(
                    MasterDataIssue(
                        severity="Error",
                        code="UNKNOWN_OPERATION_RESOURCE",
                        message=(
                            f"Operation {operation.operation_id} references missing "
                            f"resource {operation.resource_id}."
                        ),
                        field=(
                            f"Routings.{routing.product_id}.{routing.routing_id}."
                            f"Operations.{operation.operation_id}.ResourceID"
                        ),
                    )
                )
            for alternate_resource_id in operation.alternate_resource_ids or []:
                if alternate_resource_id not in resource_ids:
                    issues.append(
                        MasterDataIssue(
                            severity="Error",
                            code="UNKNOWN_OPERATION_ALTERNATE_RESOURCE",
                            message=(
                                f"Operation {operation.operation_id} references missing "
                                f"alternate resource {alternate_resource_id}."
                            ),
                            field=(
                                f"Routings.{routing.product_id}.{routing.routing_id}."
                                f"Operations.{operation.operation_id}.AlternateResourceIDs"
                            ),
                        )
                    )
        for sequence in sorted(duplicate_sequences):
            issues.append(
                MasterDataIssue(
                    severity="Error",
                    code="DUPLICATE_OPERATION_SEQUENCE",
                    message=(
                        f"Routing {routing.routing_id} for product {routing.product_id} "
                        f"uses sequence {sequence} more than once."
                    ),
                    field=(
                        f"Routings.{routing.product_id}.{routing.routing_id}."
                        "Operations.Sequence"
                    ),
                )
            )

    for product_id, routing_id in sorted(duplicate_routing_keys):
        issues.append(
            MasterDataIssue(
                severity="Error",
                code="DUPLICATE_ROUTING_ID",
                message=f"Routing {routing_id} for product {product_id} is defined more than once.",
                field=f"Routings.{product_id}.{routing_id}",
            )
        )

    for product_id in sorted(routing_ids_by_product):
        primary_count = primary_count_by_product.get(product_id, 0)
        if primary_count == 0:
            issues.append(
                MasterDataIssue(
                    severity="Error",
                    code="MISSING_PRIMARY_ROUTING",
                    message=f"Product {product_id} must have exactly one primary routing.",
                    field=f"Routings.{product_id}.IsPrimary",
                )
            )
        elif primary_count > 1:
            issues.append(
                MasterDataIssue(
                    severity="Error",
                    code="DUPLICATE_PRIMARY_ROUTING",
                    message=f"Product {product_id} has more than one primary routing.",
                    field=f"Routings.{product_id}.IsPrimary",
                )
            )

    seen_order_ids: set[str] = set()
    duplicate_order_ids: set[str] = set()
    for order in orders:
        if order.order_id in seen_order_ids:
            duplicate_order_ids.add(order.order_id)
        seen_order_ids.add(order.order_id)
        if order.quantity <= 0:
            issues.append(
                MasterDataIssue(
                    severity="Error",
                    code="NON_POSITIVE_ORDER_QUANTITY",
                    message=f"Order {order.order_id} must have a positive quantity.",
                    field=f"Orders.{order.order_id}.Quantity",
                )
            )
        if order.product_id not in routed_products:
            issues.append(
                MasterDataIssue(
                    severity="Error",
                    code="UNKNOWN_PRODUCT_ROUTING",
                    message=(
                        f"Order {order.order_id} references product "
                        f"{order.product_id} without a routing."
                    ),
                    field=f"Orders.{order.order_id}.ProductID",
                )
            )
    for order_id in sorted(duplicate_order_ids):
        issues.append(
            MasterDataIssue(
                severity="Error",
                code="DUPLICATE_ORDER_ID",
                message=f"Order {order_id} is defined more than once.",
                field=f"Orders.{order_id}.OrderID",
            )
        )

    for buffer in inventory_buffers:
        if not (
            0 <= buffer.red_zone_qty <= buffer.yellow_zone_qty <= buffer.green_zone_qty
        ):
            issues.append(
                MasterDataIssue(
                    severity="Error",
                    code="INVALID_INVENTORY_BUFFER_ZONES",
                    message=(
                        f"Inventory buffer {buffer.item_id} at {buffer.location_id} "
                        "must satisfy 0 <= red <= yellow <= green."
                    ),
                    field=f"InventoryBuffers.{buffer.item_id}.{buffer.location_id}",
                )
            )

    for requirement in material_requirements:
        if requirement.required_qty <= 0:
            issues.append(
                MasterDataIssue(
                    severity="Error",
                    code="NON_POSITIVE_MATERIAL_REQUIREMENT_QTY",
                    message=(
                        f"Material requirement for {requirement.item_id} on order "
                        f"{requirement.order_id} must have a positive quantity."
                    ),
                    field=(
                        f"MaterialRequirements.{requirement.order_id}."
                        f"{requirement.item_id}.RequiredQty"
                    ),
                )
            )
        if requirement.order_id not in order_ids:
            issues.append(
                MasterDataIssue(
                    severity="Error",
                    code="UNKNOWN_MATERIAL_REQUIREMENT_ORDER",
                    message=(
                        f"Material requirement for {requirement.item_id} "
                        f"references missing order {requirement.order_id}."
                    ),
                    field=(
                        f"MaterialRequirements.{requirement.order_id}."
                        f"{requirement.item_id}.OrderID"
                    ),
                )
            )
        if (requirement.item_id, requirement.location_id) not in inventory_buffer_keys:
            issues.append(
                MasterDataIssue(
                    severity="Error",
                    code="UNKNOWN_MATERIAL_REQUIREMENT_BUFFER",
                    message=(
                        f"Material requirement for {requirement.item_id} at "
                        f"{requirement.location_id} does not match an inventory buffer."
                    ),
                    field=(
                        f"MaterialRequirements.{requirement.order_id}."
                        f"{requirement.item_id}.{requirement.location_id}"
                    ),
                )
            )

    summary = {
        "ResourceCount": len(resources),
        "ConstraintResourceCount": sum(1 for resource in resources if resource.is_constraint),
        "CalendarResourceCount": sum(1 for resource in resources if resource.calendar is not None),
        "RoutingCount": len(routings),
        "OrderCount": len(orders),
        "InventoryBufferCount": len(inventory_buffers),
        "MaterialRequirementCount": len(material_requirements),
    }
    return MasterDataValidationResult(
        is_valid=not any(issue.severity == "Error" for issue in issues),
        summary=summary,
        issues=issues,
    )
