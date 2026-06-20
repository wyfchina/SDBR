from __future__ import annotations

from collections import Counter
from typing import Iterable


def build_administration_workbench(
    *,
    master_data_versions: Iterable[dict[str, object]],
    planning_runs: Iterable[dict[str, object]],
    state_store_health: dict[str, object],
    ortools_available: bool,
) -> dict[str, object]:
    runs = list(planning_runs)
    by_status = Counter(str(item.get("Status", "Unknown")) for item in runs)
    versions = list(master_data_versions)
    latest_version = _latest_master_data_version(versions)
    return {
        "AdminMode": "ReadOnly",
        "SensitiveEditingAllowed": False,
        "MasterDataObjects": _master_data_objects(latest_version),
        "CalendarLayers": [
            "DayDefinition",
            "WeekDefinition",
            "TemporaryShiftOverride",
            "ExclusionOrMaintenance",
        ],
        "PolicyGroups": _policy_groups(),
        "Solvers": [
            {
                "SolverID": "ortools",
                "DisplayName": "OR-Tools CP-SAT",
                "Status": "Available" if ortools_available else "Unavailable",
                "CanSelectForPlanningRun": ortools_available,
            },
            {
                "SolverID": "gurobi",
                "DisplayName": "Gurobi",
                "Status": "Paused",
                "CanSelectForPlanningRun": False,
            },
        ],
        "Integrations": [
            _integration("erp", "ERP", "NotConfigured"),
            _integration("mes", "MES", "NotConfigured"),
            _integration("simio", "Simio", "Paused"),
        ],
        "WorkerQueue": {
            "Status": "Online" if by_status.get("Running", 0) else "Idle",
            "TotalRuns": len(runs),
            "QueuedCount": by_status.get("Queued", 0),
            "RunningCount": by_status.get("Running", 0),
            "DeadLetterCount": by_status.get("DeadLetter", 0),
        },
        "StateStore": {
            "Backend": state_store_health.get("Backend"),
            "Status": state_store_health.get("Status"),
            "SchemaVersion": state_store_health.get("SchemaVersion"),
            "Revision": state_store_health.get("Revision"),
            "RecoveryStatus": state_store_health.get("RecoveryStatus"),
            "LastSavedAt": state_store_health.get("LastSavedAt"),
        },
        "RawJsonDebug": {
            "DefaultVisible": False,
            "RequiresRole": "Admin",
        },
        "LatestMasterDataPreview": _latest_preview(latest_version),
    }


def _master_data_objects(latest_version: dict[str, object] | None) -> list[dict[str, object]]:
    counts = latest_version.get("Summary", {}) if latest_version else {}
    return [
        _object_definition(
            "Resources",
            "resources",
            "/planner/workbench/resources/import",
            counts.get("ResourceCount", 0),
            [
                "ResourceType",
                "BufferMinutes",
                "ResourceQuantity",
                "SetupMinutes",
                "FixedOffsetMinutes",
                "CrewSize",
                "EfficiencyPercent",
                "OwnerID",
            ],
        ),
        _object_definition(
            "Calendars",
            "calendars",
            "/planner/workbench/resources/import",
            0,
            ["DayDefinition", "WeekDefinition", "TemporaryShiftOverride", "ExclusionOrMaintenance"],
        ),
        _object_definition(
            "Routings",
            "routings",
            "/planner/workbench/routings/import",
            counts.get("RoutingCount", 0),
            [
                "AlternateRouting",
                "Sequence",
                "ResourceID",
                "DurationMinutes",
                "BatchFamily",
                "MergeRule",
                "SplitPolicy",
            ],
        ),
        _object_definition(
            "Orders",
            "orders",
            "/planner/workbench/orders/import",
            counts.get("OrderCount", 0),
            [
                "OrderFamily",
                "PromiseDate",
                "TargetStartDate",
                "Priority",
                "BatchID",
                "MinimumSplitQuantity",
                "MaximumBatchQuantity",
            ],
        ),
        _object_definition(
            "InventoryBuffers",
            "inventoryBuffers",
            "/planner/workbench/inventory-buffers/import",
            counts.get("InventoryBufferCount", 0),
            ["RedZone", "YellowZone", "GreenZone", "ReorderPoint"],
        ),
        _object_definition(
            "MaterialRequirements",
            "materialRequirements",
            "/planner/workbench/master-data/validate",
            counts.get("MaterialRequirementCount", 0),
            ["MaterialID", "RequiredQuantity", "AvailableAt"],
        ),
    ]


def _object_definition(
    object_key: str,
    label_key: str,
    import_endpoint: str,
    current_count: object,
    reserved_fields: list[str],
) -> dict[str, object]:
    return {
        "ObjectKey": object_key,
        "LabelKey": label_key,
        "ImportEndpoint": import_endpoint,
        "CurrentCount": int(current_count or 0),
        "SupportsFileImport": True,
        "SupportsStructuredPreview": True,
        "PreValidationRequired": True,
        "GeneratesVersionAfterImport": True,
        "ReservedFields": reserved_fields,
    }


def _policy_groups() -> list[dict[str, object]]:
    return [
        {
            "GroupKey": "RateInterpretation",
            "Options": ["PiecesPerHour", "HoursPerPiece", "MinutesPerPiece"],
        },
        {
            "GroupKey": "Units",
            "Options": ["BufferMinutes", "SetupMinutes", "DurationMinutes", "FixedOffsetMinutes"],
        },
        {
            "GroupKey": "SchedulingWindow",
            "Options": ["WindowStart", "PreferredCompletionTime", "ShipmentCutoffRule"],
        },
        {
            "GroupKey": "BufferBoundaries",
            "Options": ["GreenRatio", "YellowRatio", "RedRatio"],
        },
        {
            "GroupKey": "BatchingRules",
            "Options": [
                "BatchFamily",
                "MergeRule",
                "SplitPolicy",
                "MinimumSplitQuantity",
                "MaximumBatchQuantity",
                "MixedOrderAllowed",
            ],
        },
    ]


def _integration(system_id: str, display_name: str, status: str) -> dict[str, object]:
    return {
        "SystemID": system_id,
        "DisplayName": display_name,
        "Status": status,
        "LastSyncAt": None,
        "SensitiveEditingAllowed": False,
    }


def _latest_master_data_version(
    versions: list[dict[str, object]],
) -> dict[str, object] | None:
    if not versions:
        return None
    return max(versions, key=lambda item: str(item.get("CapturedAt", "")))


def _latest_preview(version: dict[str, object] | None) -> dict[str, object]:
    if not version:
        return {"VersionID": None, "Status": "NotAvailable", "Summary": {}}
    return {
        "VersionID": version.get("VersionID"),
        "Status": version.get("Status"),
        "Summary": version.get("Summary", {}),
    }
