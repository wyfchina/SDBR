from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from threading import get_ident
from time import sleep

from fastapi.testclient import TestClient

from sdbr.api import create_app
from sdbr.operational_state import create_operational_state_snapshot
from sdbr.release_authorization import create_release_authorization
from sdbr.replanning import ReplanRequest
from sdbr.state_store import WorkbenchStateStore


def test_planner_workbench_demo_endpoint_returns_payload():
    client = TestClient(create_app())

    response = client.get("/planner/workbench/demo")

    assert response.status_code == 200
    payload = response.json()
    assert payload["Endpoint"] == "/planner/workbench/demo"
    assert payload["StatusCode"] == 200
    assert payload["Data"]["SolverBackendID"] == "baseline-finite"
    assert payload["Data"]["SolverStatus"] == "Feasible"
    assert payload["Data"]["LoadGraphRows"]
    assert payload["Data"]["GanttRows"]


def test_planner_workbench_demo_endpoint_accepts_solver_backend_query():
    client = TestClient(create_app())

    response = client.get("/planner/workbench/demo?solver_backend_id=ortools")

    assert response.status_code == 200
    payload = response.json()
    assert payload["Data"]["SolverBackendID"] == "ortools"
    assert payload["Data"]["SolverStatus"] in {"Optimal", "Feasible"}
    assert payload["Data"]["GanttRows"]
    assert payload["Data"]["LoadGraphRows"]


def test_planner_workbench_routing_import_endpoint_returns_routings_and_validation():
    client = TestClient(create_app())

    response = client.post(
        "/planner/workbench/routings/import",
        json={
            "Resources": [
                {
                    "ResourceID": "WC-DRUM",
                    "Name": "Constraint Cutter",
                    "IsConstraint": True,
                    "DailyCapacityMinutes": {"2026-06-16": 480},
                }
            ],
            "Rows": [
                {
                    "ProductID": "FG-A",
                    "RoutingID": "PRIMARY",
                    "IsPrimary": True,
                    "OperationID": "ASM",
                    "ResourceID": "WC-DRUM",
                    "DurationMinutes": 80,
                    "Sequence": 2,
                },
                {
                    "ProductID": "FG-A",
                    "RoutingID": "PRIMARY",
                    "IsPrimary": True,
                    "OperationID": "CUT",
                    "ResourceID": "WC-DRUM",
                    "DurationMinutes": 120,
                    "Sequence": 1,
                },
            ],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["Endpoint"] == "/planner/workbench/routings/import"
    assert payload["Data"]["Validation"]["IsValid"] is True
    assert payload["Data"]["Routings"] == [
        {
            "ProductID": "FG-A",
            "RoutingID": "PRIMARY",
            "IsPrimary": True,
            "Operations": [
                {
                    "OperationID": "CUT",
                    "ResourceID": "WC-DRUM",
                    "DurationMinutes": 120,
                    "Sequence": 1,
                    "AlternateResourceIDs": [],
                },
                {
                    "OperationID": "ASM",
                    "ResourceID": "WC-DRUM",
                    "DurationMinutes": 80,
                    "Sequence": 2,
                    "AlternateResourceIDs": [],
                },
            ],
        }
    ]


def test_planner_workbench_order_import_endpoint_returns_orders_and_validation():
    client = TestClient(create_app())

    response = client.post(
        "/planner/workbench/orders/import",
        json={
            "Resources": [
                {
                    "ResourceID": "WC-DRUM",
                    "Name": "Constraint Cutter",
                    "IsConstraint": True,
                    "DailyCapacityMinutes": {"2026-06-16": 480},
                }
            ],
            "Routings": [
                {
                    "ProductID": "FG-A",
                    "RoutingID": "PRIMARY",
                    "IsPrimary": True,
                    "Operations": [
                        {
                            "OperationID": "CUT",
                            "ResourceID": "WC-DRUM",
                            "DurationMinutes": 120,
                            "Sequence": 1,
                        }
                    ],
                }
            ],
            "Rows": [
                {
                    "OrderID": "WO-2",
                    "ProductID": "FG-A",
                    "Quantity": 2,
                    "DueDate": "2026-06-21T08:00:00+00:00",
                    "TargetStartDate": "2026-06-17",
                },
                {
                    "OrderID": "WO-1",
                    "ProductID": "FG-A",
                    "Quantity": 1,
                    "DueDate": "2026-06-20T08:00:00+00:00",
                    "TargetStartDate": "2026-06-16",
                },
            ],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["Endpoint"] == "/planner/workbench/orders/import"
    assert payload["Data"]["Validation"]["IsValid"] is True
    assert [order["OrderID"] for order in payload["Data"]["Orders"]] == ["WO-1", "WO-2"]
    assert payload["Data"]["Orders"][0]["DueDate"] == "2026-06-20T08:00:00+00:00"


def test_planner_workbench_resource_import_endpoint_returns_resources_and_validation():
    client = TestClient(create_app())

    response = client.post(
        "/planner/workbench/resources/import",
        json={
            "Rows": [
                {
                    "ResourceID": "WC-ASM",
                    "Name": "Assembly Cell",
                    "IsConstraint": False,
                    "CapacityDate": "2026-06-17",
                    "CapacityMinutes": 960,
                },
                {
                    "ResourceID": "WC-DRUM",
                    "Name": "Constraint Cutter",
                    "IsConstraint": True,
                    "CapacityDate": "2026-06-16",
                    "CapacityMinutes": 480,
                },
                {
                    "ResourceID": "WC-ASM",
                    "Name": "Assembly Cell",
                    "IsConstraint": False,
                    "CapacityDate": "2026-06-16",
                    "CapacityMinutes": 960,
                },
            ],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["Endpoint"] == "/planner/workbench/resources/import"
    assert payload["Data"]["Validation"]["IsValid"] is True
    assert payload["Data"]["Resources"] == [
        {
            "ResourceID": "WC-ASM",
            "Name": "Assembly Cell",
            "IsConstraint": False,
            "DailyCapacityMinutes": {
                "2026-06-16": 960,
                "2026-06-17": 960,
            },
        },
        {
            "ResourceID": "WC-DRUM",
            "Name": "Constraint Cutter",
            "IsConstraint": True,
            "DailyCapacityMinutes": {
                "2026-06-16": 480,
            },
        },
    ]


def test_planner_workbench_resource_import_endpoint_attaches_calendar_rows():
    client = TestClient(create_app())

    response = client.post(
        "/planner/workbench/resources/import",
        json={
            "Rows": [
                {
                    "ResourceID": "WC-DRUM",
                    "Name": "Constraint Cutter",
                    "IsConstraint": True,
                    "CapacityDate": "2026-06-16",
                    "CapacityMinutes": 480,
                }
            ],
            "CalendarRows": [
                {
                    "ResourceID": "WC-DRUM",
                    "CalendarID": "CAL-DRUM",
                    "WorkingWeekdays": [0, 1, 2, 3, 4],
                    "ShiftName": "Day",
                    "ShiftStart": "08:00:00",
                    "ShiftEnd": "16:00:00",
                    "MaintenanceStart": "2026-06-16T10:00:00+00:00",
                    "MaintenanceEnd": "2026-06-16T11:00:00+00:00",
                }
            ],
            "CalendarTimezone": "UTC",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["Data"]["Validation"]["IsValid"] is True
    assert payload["Data"]["Resources"][0]["Calendar"] == {
        "CalendarID": "CAL-DRUM",
        "WorkingWeekdays": [0, 1, 2, 3, 4],
        "Shifts": [
            {
                "Name": "Day",
                "Start": "08:00:00",
                "End": "16:00:00",
            }
        ],
        "MaintenanceWindows": [
            {
                "Start": "2026-06-16T10:00:00+00:00",
                "End": "2026-06-16T11:00:00+00:00",
            }
        ],
        "Holidays": [],
    }


def test_planner_workbench_inventory_import_endpoint_returns_buffers_and_validation():
    client = TestClient(create_app())

    response = client.post(
        "/planner/workbench/inventory-buffers/import",
        json={
            "Resources": [
                {
                    "ResourceID": "WC-DRUM",
                    "Name": "Constraint Cutter",
                    "IsConstraint": True,
                    "DailyCapacityMinutes": {"2026-06-16": 480},
                }
            ],
            "Rows": [
                {
                    "ItemID": "WIP-KIT",
                    "LocationID": "LINE-SUPERMARKET",
                    "OnHandQty": 160,
                    "RedZoneQty": 40,
                    "YellowZoneQty": 90,
                    "GreenZoneQty": 160,
                },
                {
                    "ItemID": "RM-STEEL",
                    "LocationID": "SUPPLIER-DECOUPLING",
                    "OnHandQty": 35,
                    "RedZoneQty": 50,
                    "YellowZoneQty": 120,
                    "GreenZoneQty": 200,
                },
            ],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["Endpoint"] == "/planner/workbench/inventory-buffers/import"
    assert payload["Data"]["Validation"]["IsValid"] is True
    assert payload["Data"]["InventoryBuffers"][0] == {
        "ItemID": "RM-STEEL",
        "LocationID": "SUPPLIER-DECOUPLING",
        "OnHandQty": 35,
        "RedZoneQty": 50,
        "YellowZoneQty": 120,
        "GreenZoneQty": 200,
    }


def test_planner_workbench_material_availability_import_endpoint_returns_standard_rows():
    client = TestClient(create_app())

    response = client.post(
        "/planner/workbench/material-availability/import",
        json={
            "Rows": [
                {
                    "ItemID": "WIP-KIT",
                    "LocationID": "LINE",
                    "AllocatedQty": 2,
                },
                {
                    "ItemID": "RM-STEEL",
                    "LocationID": "SUPPLIER-DECOUPLING",
                    "AllocatedQty": 5,
                    "InboundQty": 15,
                    "InboundAvailableAt": "2026-06-16T07:30:00+00:00",
                },
            ]
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["Endpoint"] == "/planner/workbench/material-availability/import"
    assert payload["Data"]["MaterialAvailability"][0] == {
        "ItemID": "RM-STEEL",
        "LocationID": "SUPPLIER-DECOUPLING",
        "AllocatedQty": 5,
        "InboundQty": 15,
        "InboundAvailableAt": "2026-06-16T07:30:00+00:00",
    }


def test_planner_workbench_material_availability_import_rejects_negative_qty():
    client = TestClient(create_app())

    response = client.post(
        "/planner/workbench/material-availability/import",
        json={
            "Rows": [
                {
                    "ItemID": "RM-STEEL",
                    "LocationID": "SUPPLIER-DECOUPLING",
                    "AllocatedQty": -1,
                }
            ]
        },
    )

    assert response.status_code == 409
    assert response.json()["Data"]["Status"] == "MaterialAvailabilityInvalid"


def test_planner_workbench_wip_limits_import_endpoint_returns_standard_rows():
    client = TestClient(create_app())

    response = client.post(
        "/planner/workbench/wip-limits/import",
        json={
            "Rows": [
                {
                    "ScopeID": "LINE",
                    "CurrentWipCount": 2,
                    "MaxWipCount": 8,
                },
                {
                    "ScopeID": "DRUM-FEED",
                    "CurrentWipCount": 5,
                    "MaxWipCount": 6,
                    "OrderWipIncrement": 2,
                },
            ]
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["Endpoint"] == "/planner/workbench/wip-limits/import"
    assert payload["Data"]["WipLimits"][0] == {
        "ScopeID": "DRUM-FEED",
        "CurrentWipCount": 5,
        "MaxWipCount": 6,
        "OrderWipIncrement": 2,
    }


def test_planner_workbench_wip_limits_import_rejects_current_above_max():
    client = TestClient(create_app())

    response = client.post(
        "/planner/workbench/wip-limits/import",
        json={
            "Rows": [
                {
                    "ScopeID": "DRUM-FEED",
                    "CurrentWipCount": 7,
                    "MaxWipCount": 6,
                }
            ]
        },
    )

    assert response.status_code == 409
    assert response.json()["Data"]["Status"] == "WipLimitsInvalid"


def test_planner_workbench_master_data_import_endpoint_returns_package_and_validation():
    client = TestClient(create_app())

    response = client.post(
        "/planner/workbench/master-data/import",
        json={
            "ResourceRows": [
                {
                    "ResourceID": "WC-DRUM",
                    "Name": "Constraint Cutter",
                    "IsConstraint": True,
                    "CapacityDate": "2026-06-16",
                    "CapacityMinutes": 480,
                },
                {
                    "ResourceID": "WC-ASM",
                    "Name": "Assembly Cell",
                    "IsConstraint": False,
                    "CapacityDate": "2026-06-16",
                    "CapacityMinutes": 960,
                },
            ],
            "RoutingRows": [
                {
                    "ProductID": "FG-A",
                    "RoutingID": "PRIMARY",
                    "IsPrimary": True,
                    "OperationID": "ASM",
                    "ResourceID": "WC-ASM",
                    "DurationMinutes": 80,
                    "Sequence": 2,
                },
                {
                    "ProductID": "FG-A",
                    "RoutingID": "PRIMARY",
                    "IsPrimary": True,
                    "OperationID": "CUT",
                    "ResourceID": "WC-DRUM",
                    "DurationMinutes": 120,
                    "Sequence": 1,
                },
            ],
            "OrderRows": [
                {
                    "OrderID": "WO-1",
                    "ProductID": "FG-A",
                    "Quantity": 1,
                    "DueDate": "2026-06-20T08:00:00+00:00",
                    "TargetStartDate": "2026-06-16",
                }
            ],
            "InventoryBufferRows": [
                {
                    "ItemID": "RM-STEEL",
                    "LocationID": "SUPPLIER-DECOUPLING",
                    "OnHandQty": 55,
                    "RedZoneQty": 50,
                    "YellowZoneQty": 120,
                    "GreenZoneQty": 200,
                }
            ],
            "MaterialRequirementRows": [
                {
                    "OrderID": "WO-1",
                    "ItemID": "RM-STEEL",
                    "LocationID": "SUPPLIER-DECOUPLING",
                    "RequiredQty": 10,
                }
            ],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["Endpoint"] == "/planner/workbench/master-data/import"
    assert payload["Data"]["Validation"]["IsValid"] is True
    assert [resource["ResourceID"] for resource in payload["Data"]["Resources"]] == [
        "WC-ASM",
        "WC-DRUM",
    ]
    assert payload["Data"]["Routings"][0]["Operations"][0]["OperationID"] == "CUT"
    assert payload["Data"]["Orders"][0]["OrderID"] == "WO-1"
    assert payload["Data"]["InventoryBuffers"][0]["ItemID"] == "RM-STEEL"
    assert payload["Data"]["MaterialRequirements"] == [
        {
            "OrderID": "WO-1",
            "ItemID": "RM-STEEL",
            "LocationID": "SUPPLIER-DECOUPLING",
            "RequiredQty": 10.0,
        }
    ]


def test_planner_workbench_master_data_version_endpoint_persists_validated_package(tmp_path):
    from sdbr.state_store import SQLiteWorkbenchStateStore

    database_path = tmp_path / "workbench.db"
    client = TestClient(create_app(state_store=SQLiteWorkbenchStateStore(database_path)))
    request_payload = _master_data_import_calculate_payload()
    request_payload.pop("ProblemID")
    request_payload.pop("ScheduleStartAt")
    request_payload.update(
        {
            "VersionID": "MDV-2026-06-16-A",
            "CapturedAt": "2026-06-16T07:30:00+00:00",
            "SourceSystem": "ERP",
            "CreatedBy": "planner-1",
        }
    )

    create_response = client.post(
        "/planner/workbench/master-data/versions",
        json=request_payload,
    )

    assert create_response.status_code == 200
    created = create_response.json()["Data"]["Version"]
    assert created["VersionID"] == "MDV-2026-06-16-A"
    assert created["Status"] == "Valid"
    assert created["SourceSystem"] == "ERP"
    assert created["Validation"]["Summary"]["ResourceCount"] == 1
    assert created["Resources"][0]["ResourceID"] == "WC-DRUM"
    assert create_response.headers["X-Workbench-Revision"] == "1"

    duplicate = client.post(
        "/planner/workbench/master-data/versions",
        headers={"If-Match": "1"},
        json=request_payload,
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["Data"]["Status"] == "MasterDataVersionConflict"

    recreated_client = TestClient(
        create_app(state_store=SQLiteWorkbenchStateStore(database_path))
    )
    read_response = recreated_client.get(
        "/planner/workbench/master-data/versions/MDV-2026-06-16-A"
    )
    assert read_response.status_code == 200
    restored = read_response.json()["Data"]["Version"]
    assert restored["CreatedBy"] == "planner-1"
    assert restored["Orders"][0]["OrderID"] == "WO-1"


def test_be_data_010_011_013_master_data_compare_publish_and_rollback():
    # BE-DATA-010 / BE-DATA-011 / BE-DATA-013
    client = TestClient(create_app())
    baseline = _master_data_import_calculate_payload()
    baseline.pop("ProblemID")
    baseline.pop("ScheduleStartAt")
    baseline.update(
        {
            "VersionID": "MDV-GOV-1",
            "CapturedAt": "2026-06-16T07:30:00+00:00",
            "CreatedBy": "planner-1",
        }
    )
    candidate = _master_data_import_calculate_payload()
    candidate.pop("ProblemID")
    candidate.pop("ScheduleStartAt")
    candidate["ResourceRows"].append(
        {
            "ResourceID": "WC-PACK",
            "Name": "Packing Cell",
            "IsConstraint": False,
            "CapacityDate": "2026-06-16",
            "CapacityMinutes": 360,
        }
    )
    candidate.update(
        {
            "VersionID": "MDV-GOV-2",
            "CapturedAt": "2026-06-16T07:45:00+00:00",
            "CreatedBy": "planner-1",
        }
    )
    assert client.post("/planner/workbench/master-data/versions", json=baseline).status_code == 200
    assert client.post("/planner/workbench/master-data/versions", json=candidate).status_code == 200

    comparison = client.get(
        "/planner/workbench/master-data/version-comparison",
        params={
            "baseline_version_id": "MDV-GOV-1",
            "candidate_version_id": "MDV-GOV-2",
        },
    ).json()["Data"]
    resources = next(row for row in comparison["Rows"] if row["ObjectKey"] == "Resources")
    assert resources["AddedIDs"] == ["WC-PACK"]

    published = client.post(
        "/planner/workbench/master-data/versions/MDV-GOV-2/publish",
        json={
            "ActorID": "admin-1",
            "OccurredAt": "2026-06-16T08:00:00+00:00",
            "Reason": "validated capacity update",
        },
    ).json()["Data"]["Version"]
    assert published["PublicationStatus"] == "Published"
    rollback = client.post(
        "/planner/workbench/master-data/versions/MDV-GOV-1/rollback",
        json={
            "ActorID": "admin-1",
            "OccurredAt": "2026-06-16T08:10:00+00:00",
            "Reason": "restore baseline",
        },
    ).json()["Data"]["Version"]
    assert rollback["PublicationStatus"] == "Published"
    assert client.get(
        "/planner/workbench/master-data/versions/MDV-GOV-2"
    ).json()["Data"]["Version"]["PublicationStatus"] == "Inactive"


def test_planning_run_lifecycle_executes_frozen_inputs_with_cp_sat_and_persists(tmp_path):
    from sdbr.state_store import SQLiteWorkbenchStateStore

    database_path = tmp_path / "workbench.db"
    client = TestClient(create_app(state_store=SQLiteWorkbenchStateStore(database_path)))
    master_data_payload = _master_data_import_calculate_payload()
    master_data_payload.pop("ProblemID")
    master_data_payload.pop("ScheduleStartAt")
    master_data_payload.update(
        {
            "VersionID": "MDV-RUN-1",
            "CapturedAt": "2026-06-16T07:30:00+00:00",
            "SourceSystem": "ERP",
            "CreatedBy": "planner-1",
        }
    )
    assert client.post(
        "/planner/workbench/master-data/versions",
        json=master_data_payload,
    ).status_code == 200
    assert client.post(
        "/planner/workbench/operational-state/snapshots",
        json={
            "SnapshotID": "OPS-RUN-1",
            "CapturedAt": "2026-06-16T07:45:00+00:00",
        },
    ).status_code == 200

    paused_response = client.post(
        "/planner/workbench/planning-runs",
        json={
            "RunID": "RUN-GUROBI-PAUSED",
            "ProblemID": "PLAN-1",
            "MasterDataVersionID": "MDV-RUN-1",
            "OperationalStateSnapshotID": "OPS-RUN-1",
            "ScheduleStartAt": "2026-06-16T08:00:00+00:00",
            "SolverBackendID": "gurobi",
            "RequestedBy": "planner-1",
            "RequestedAt": "2026-06-16T07:49:00+00:00",
        },
    )
    assert paused_response.status_code == 409
    assert paused_response.json()["Data"]["Status"] == "SolverBackendPaused"

    create_response = client.post(
        "/planner/workbench/planning-runs",
        json={
            "RunID": "RUN-1",
            "ProblemID": "PLAN-1",
            "MasterDataVersionID": "MDV-RUN-1",
            "OperationalStateSnapshotID": "OPS-RUN-1",
            "ScheduleStartAt": "2026-06-16T08:00:00+00:00",
            "TimeBufferMinutes": 120,
            "ObjectiveStrategyID": "flow_first",
            "SetupTransitions": [
                {
                    "ResourceID": "WC-DRUM",
                    "FromFamily": "FG-A",
                    "ToFamily": "FG-B",
                    "SetupMinutes": 30,
                }
            ],
            "SolverBackendID": "ortools",
            "RequestedBy": "planner-1",
            "RequestedAt": "2026-06-16T07:50:00+00:00",
        },
    )

    assert create_response.status_code == 200
    pending_run = create_response.json()["Data"]["PlanningRun"]
    assert pending_run["RunID"] == "RUN-1"
    assert pending_run["Status"] == "Pending"
    assert pending_run["Schedule"] is None
    assert pending_run["ObjectiveStrategyID"] == "flow_first"
    assert pending_run["SetupTransitions"] == [
        {
            "ResourceID": "WC-DRUM",
            "FromFamily": "FG-A",
            "ToFamily": "FG-B",
            "SetupMinutes": 30,
        }
    ]
    assert pending_run["StatusHistory"] == [
        {
            "Status": "Pending",
            "ChangedAt": "2026-06-16T07:50:00+00:00",
            "ChangedBy": "planner-1",
        }
    ]

    execute_response = client.post(
        "/planner/workbench/planning-runs/RUN-1/execute",
        json={
            "ExecutedBy": "planner-1",
            "StartedAt": "2026-06-16T07:55:00+00:00",
            "CompletedAt": "2026-06-16T07:56:00+00:00",
            "TimeLimitSeconds": 30,
        },
    )

    assert execute_response.status_code == 200
    run = execute_response.json()["Data"]["PlanningRun"]
    assert run["MasterDataVersionID"] == "MDV-RUN-1"
    assert run["OperationalStateSnapshotID"] == "OPS-RUN-1"
    assert run["SolverBackendID"] == "ortools"
    assert run["Status"] in {"Completed", "Failed"}
    assert run["StartedAt"] == "2026-06-16T07:55:00+00:00"
    assert run["CompletedAt"] == "2026-06-16T07:56:00+00:00"
    assert run["TimeLimitSeconds"] == 30
    assert run["ObjectiveStrategyID"] == "flow_first"
    assert run["SetupTransitions"] == pending_run["SetupTransitions"]
    assert run["Schedule"]["ProblemID"] == "PLAN-1"
    assert run["Schedule"]["SolverBackendID"] == "ortools"
    assert run["Schedule"]["SolverStatus"] in {
        "Optimal",
        "Feasible",
        "Unavailable",
        "Infeasible",
        "Error",
    }
    assert any(
        diagnostic["Code"] == "ORTOOLS_TIME_LIMIT_CONFIGURED"
        and diagnostic["Message"] == "OR-Tools CP-SAT time limit set to 30 seconds."
        for diagnostic in run["Schedule"]["SolverDiagnostics"]
    )

    recreated_client = TestClient(
        create_app(state_store=SQLiteWorkbenchStateStore(database_path))
    )
    read_response = recreated_client.get("/planner/workbench/planning-runs/RUN-1")
    assert read_response.status_code == 200
    restored = read_response.json()["Data"]["PlanningRun"]
    assert restored == run

    duplicate_execute = recreated_client.post(
        "/planner/workbench/planning-runs/RUN-1/execute",
        json={
            "ExecutedBy": "planner-1",
            "StartedAt": "2026-06-16T08:00:00+00:00",
            "CompletedAt": "2026-06-16T08:01:00+00:00",
        },
    )
    assert duplicate_execute.status_code == 409
    assert duplicate_execute.json()["Data"]["Status"] == "PlanningRunNotPending"


def test_be_solver_012_planning_run_freezes_source_run_and_release_policy():
    # BE-SOLVER-012 / BE-REL-012
    client = TestClient(create_app())
    _create_master_data_and_snapshot(client, version_id="MDV-SOURCE", snapshot_id="OPS-SOURCE")
    assert client.post(
        "/planner/workbench/dbr/release-policies",
        json={
            "VersionID": "DBR-POLICY-1",
            "CreatedAt": "2026-06-16T07:20:00+00:00",
            "CreatedBy": "planner-1",
            "RopeBufferMinutes": 90,
            "Status": "Active",
        },
    ).status_code == 200
    _create_and_execute_planning_run(
        client,
        run_id="RUN-SOURCE",
        master_data_version_id="MDV-SOURCE",
        snapshot_id="OPS-SOURCE",
    )

    response = client.post(
        "/planner/workbench/planning-runs",
        json={
            "RunID": "RUN-CANDIDATE",
            "ProblemID": "P-IMPORT-CALC",
            "SourceRunID": "RUN-SOURCE",
            "ReleasePolicyVersionID": "DBR-POLICY-1",
            "MasterDataVersionID": "MDV-SOURCE",
            "OperationalStateSnapshotID": "OPS-SOURCE",
            "ScheduleStartAt": "2026-06-16T08:00:00+00:00",
            "SolverBackendID": "ortools",
            "RequestedBy": "planner-1",
            "RequestedAt": "2026-06-16T08:10:00+00:00",
        },
    )

    assert response.status_code == 200
    run = response.json()["Data"]["PlanningRun"]
    assert run["SourceRunID"] == "RUN-SOURCE"
    assert run["ReleasePolicyVersionID"] == "DBR-POLICY-1"
    assert run["FrozenReleasePolicy"]["RopeBufferMinutes"] == 90
    detail = client.get(
        "/planner/workbench/planning-runs/RUN-CANDIDATE/workbench"
    ).json()["Data"]
    assert detail["FrozenInputs"]["SourceRunID"] == "RUN-SOURCE"
    assert detail["FrozenReleasePolicy"]["VersionID"] == "DBR-POLICY-1"


def test_be_rel_012_release_policy_list_supports_admin_configuration():
    # BE-REL-012 / BE-UI-006
    client = TestClient(create_app())
    assert client.post(
        "/planner/workbench/dbr/release-policies",
        json={
            "VersionID": "DBR-POLICY-CONFIG-1",
            "CreatedAt": "2026-06-20T08:00:00+00:00",
            "CreatedBy": "admin-1",
            "RopeBufferMinutes": 150,
            "GreenZoneRatio": 0.4,
            "YellowZoneRatio": 0.35,
            "RedZoneRatio": 0.25,
            "MaxWipCount": 12,
            "MaterialLookaheadMinutes": 720,
            "Status": "Active",
        },
    ).status_code == 200

    response = client.get("/planner/workbench/dbr/release-policies")

    assert response.status_code == 200
    data = response.json()["Data"]
    assert data["PolicyCount"] == 1
    assert data["ActivePolicyVersionID"] == "DBR-POLICY-CONFIG-1"
    assert data["Policies"][0]["RopeBufferMinutes"] == 150
    assert data["Policies"][0]["TimeBufferRatios"] == {
        "Green": 0.4,
        "Yellow": 0.35,
        "Red": 0.25,
    }
    assert "MaterialLookaheadMinutes" in data["ConfigurableParameters"]

    admin = client.get("/planner/workbench/administration/workbench").json()["Data"]
    assert (
        admin["ReleasePolicyConfiguration"]["ActivePolicyVersionID"]
        == "DBR-POLICY-CONFIG-1"
    )


def test_pending_planning_run_can_be_cancelled_but_not_executed():
    client = TestClient(create_app())
    master_data_payload = _master_data_import_calculate_payload()
    master_data_payload.pop("ProblemID")
    master_data_payload.pop("ScheduleStartAt")
    master_data_payload.update(
        {
            "VersionID": "MDV-CANCEL-1",
            "CapturedAt": "2026-06-16T07:30:00+00:00",
            "CreatedBy": "planner-1",
        }
    )
    assert client.post(
        "/planner/workbench/master-data/versions", json=master_data_payload
    ).status_code == 200
    assert client.post(
        "/planner/workbench/operational-state/snapshots",
        json={
            "SnapshotID": "OPS-CANCEL-1",
            "CapturedAt": "2026-06-16T07:45:00+00:00",
        },
    ).status_code == 200
    assert client.post(
        "/planner/workbench/planning-runs",
        json={
            "RunID": "RUN-CANCEL-1",
            "ProblemID": "PLAN-CANCEL-1",
            "MasterDataVersionID": "MDV-CANCEL-1",
            "OperationalStateSnapshotID": "OPS-CANCEL-1",
            "ScheduleStartAt": "2026-06-16T08:00:00+00:00",
            "RequestedBy": "planner-1",
            "RequestedAt": "2026-06-16T07:50:00+00:00",
        },
    ).status_code == 200

    cancel_response = client.post(
        "/planner/workbench/planning-runs/RUN-CANCEL-1/cancel",
        json={
            "CancelledBy": "planner-2",
            "CancelledAt": "2026-06-16T07:52:00+00:00",
            "Reason": "Material snapshot requires correction.",
        },
    )

    assert cancel_response.status_code == 200
    cancelled = cancel_response.json()["Data"]["PlanningRun"]
    assert cancelled["Status"] == "Cancelled"
    assert cancelled["CancelledBy"] == "planner-2"
    assert cancelled["CancellationReason"] == "Material snapshot requires correction."
    assert cancelled["Schedule"] is None

    execute_response = client.post(
        "/planner/workbench/planning-runs/RUN-CANCEL-1/execute",
        json={
            "ExecutedBy": "planner-1",
            "StartedAt": "2026-06-16T07:55:00+00:00",
            "CompletedAt": "2026-06-16T07:56:00+00:00",
        },
    )
    assert execute_response.status_code == 409
    assert execute_response.json()["Data"]["CurrentStatus"] == "Cancelled"


def test_planning_run_worker_lease_recovers_after_restart_and_rejects_stale_owner(
    tmp_path,
):
    from sdbr.state_store import SQLiteWorkbenchStateStore

    database_path = tmp_path / "workbench.db"
    client = TestClient(create_app(state_store=SQLiteWorkbenchStateStore(database_path)))
    master_data_payload = _master_data_import_calculate_payload()
    master_data_payload.pop("ProblemID")
    master_data_payload.pop("ScheduleStartAt")
    master_data_payload.update(
        {
            "VersionID": "MDV-WORKER-1",
            "CapturedAt": "2026-06-16T07:30:00+00:00",
            "CreatedBy": "planner-1",
        }
    )
    assert client.post(
        "/planner/workbench/master-data/versions", json=master_data_payload
    ).status_code == 200
    assert client.post(
        "/planner/workbench/operational-state/snapshots",
        json={
            "SnapshotID": "OPS-WORKER-1",
            "CapturedAt": "2026-06-16T07:45:00+00:00",
        },
    ).status_code == 200
    assert client.post(
        "/planner/workbench/planning-runs",
        json={
            "RunID": "RUN-WORKER-1",
            "ProblemID": "PLAN-WORKER-1",
            "MasterDataVersionID": "MDV-WORKER-1",
            "OperationalStateSnapshotID": "OPS-WORKER-1",
            "ScheduleStartAt": "2026-06-16T08:00:00+00:00",
            "RequestedBy": "planner-1",
            "RequestedAt": "2026-06-16T07:50:00+00:00",
        },
    ).status_code == 200

    enqueue_response = client.post(
        "/planner/workbench/planning-runs/RUN-WORKER-1/enqueue",
        json={
            "EnqueuedBy": "planner-1",
            "EnqueuedAt": "2026-06-16T07:51:00+00:00",
        },
    )
    assert enqueue_response.status_code == 200
    assert enqueue_response.json()["Data"]["PlanningRun"]["Status"] == "Queued"

    first_claim = client.post(
        "/planner/workbench/planning-runs/jobs/claim-next",
        json={
            "WorkerID": "worker-a",
            "ClaimedAt": "2026-06-16T07:52:00+00:00",
            "LeaseSeconds": 60,
        },
    )
    assert first_claim.status_code == 200
    first_run = first_claim.json()["Data"]["PlanningRun"]
    assert first_run["Status"] == "Running"
    assert first_run["WorkerID"] == "worker-a"
    assert first_run["AttemptCount"] == 1
    first_token = first_run["LeaseToken"]

    recreated_client = TestClient(
        create_app(state_store=SQLiteWorkbenchStateStore(database_path))
    )
    stored_run = recreated_client.app.state.workbench_state_store.planning_runs[
        "RUN-WORKER-1"
    ]
    assert "LeaseToken" not in stored_run
    assert stored_run["LeaseTokenHash"]
    read_run = recreated_client.get(
        "/planner/workbench/planning-runs/RUN-WORKER-1"
    ).json()["Data"]["PlanningRun"]
    assert "LeaseToken" not in read_run
    assert "LeaseTokenHash" not in read_run

    heartbeat = recreated_client.post(
        "/planner/workbench/planning-runs/RUN-WORKER-1/renew-lease",
        json={
            "WorkerID": "worker-a",
            "LeaseToken": first_token,
            "RenewedAt": "2026-06-16T07:52:30+00:00",
            "LeaseSeconds": 180,
        },
    )
    assert heartbeat.status_code == 200
    renewed_run = heartbeat.json()["Data"]["PlanningRun"]
    assert renewed_run["LeaseExpiresAt"] == "2026-06-16T07:55:30+00:00"
    assert renewed_run["LeaseRenewalCount"] == 1

    no_claim = recreated_client.post(
        "/planner/workbench/planning-runs/jobs/claim-next",
        json={
            "WorkerID": "worker-b",
            "ClaimedAt": "2026-06-16T07:54:00+00:00",
            "LeaseSeconds": 60,
        },
    )
    assert no_claim.status_code == 200
    assert no_claim.json()["Data"]["PlanningRun"] is None

    second_claim = recreated_client.post(
        "/planner/workbench/planning-runs/jobs/claim-next",
        json={
            "WorkerID": "worker-b",
            "ClaimedAt": "2026-06-16T07:56:00+00:00",
            "LeaseSeconds": 60,
        },
    )
    assert second_claim.status_code == 200
    second_run = second_claim.json()["Data"]["PlanningRun"]
    assert second_run["WorkerID"] == "worker-b"
    assert second_run["AttemptCount"] == 2
    assert second_run["RecoveredFromExpiredLease"] is True
    second_token = second_run["LeaseToken"]
    assert second_token != first_token

    stale_execute = recreated_client.post(
        "/planner/workbench/planning-runs/RUN-WORKER-1/execute",
        json={
            "ExecutedBy": "worker-a",
            "StartedAt": "2026-06-16T07:56:10+00:00",
            "CompletedAt": "2026-06-16T07:56:20+00:00",
            "TimeLimitSeconds": 30,
            "LeaseToken": first_token,
        },
    )
    assert stale_execute.status_code == 409
    assert stale_execute.json()["Data"]["Status"] == "PlanningRunLeaseMismatch"

    execute_response = recreated_client.post(
        "/planner/workbench/planning-runs/RUN-WORKER-1/execute",
        json={
            "ExecutedBy": "worker-b",
            "StartedAt": "2026-06-16T07:56:10+00:00",
            "CompletedAt": "2026-06-16T07:56:20+00:00",
            "TimeLimitSeconds": 30,
            "LeaseToken": second_token,
        },
    )
    assert execute_response.status_code == 200
    completed = execute_response.json()["Data"]["PlanningRun"]
    assert completed["Status"] in {"Completed", "Failed"}
    assert completed["WorkerID"] == "worker-b"

    audit_response = recreated_client.get(
        "/planner/workbench/planning-runs/audit-events",
        params={"run_id": "RUN-WORKER-1"},
    )
    assert audit_response.status_code == 200
    actions = [
        event["Action"]
        for event in audit_response.json()["Data"]["AuditEvents"]
    ]
    assert actions == [
        "PlanningRunCreated",
        "PlanningRunEnqueued",
        "PlanningRunClaimed",
        "PlanningRunLeaseRenewed",
        "PlanningRunLeaseRecovered",
        "PlanningRunExecuted",
    ]


def test_planning_run_rbac_can_be_enforced_without_affecting_default_dev_mode():
    client = TestClient(create_app(require_auth=True))

    missing_identity = client.get("/planner/workbench/planning-runs")
    assert missing_identity.status_code == 401
    assert missing_identity.json()["Data"]["Status"] == "AuthenticationRequired"

    viewer = client.get(
        "/planner/workbench/planning-runs",
        headers={"X-Actor-ID": "viewer-1", "X-Actor-Role": "Viewer"},
    )
    assert viewer.status_code == 200

    forbidden = client.post(
        "/planner/workbench/planning-runs/jobs/claim-next",
        headers={"X-Actor-ID": "planner-1", "X-Actor-Role": "Planner"},
        json={
            "WorkerID": "worker-1",
            "ClaimedAt": "2026-06-16T08:00:00+00:00",
            "LeaseSeconds": 120,
        },
    )
    assert forbidden.status_code == 403
    assert forbidden.json()["Data"]["Status"] == "PermissionDenied"

    impersonation = client.post(
        "/planner/workbench/planning-runs/jobs/claim-next",
        headers={"X-Actor-ID": "worker-1", "X-Actor-Role": "Worker"},
        json={
            "WorkerID": "worker-2",
            "ClaimedAt": "2026-06-16T08:00:00+00:00",
            "LeaseSeconds": 120,
        },
    )
    assert impersonation.status_code == 403
    assert impersonation.json()["Data"]["Status"] == "ActorIdentityMismatch"

    worker = client.post(
        "/planner/workbench/planning-runs/jobs/claim-next",
        headers={"X-Actor-ID": "worker-1", "X-Actor-Role": "Worker"},
        json={
            "WorkerID": "worker-1",
            "ClaimedAt": "2026-06-16T08:00:00+00:00",
            "LeaseSeconds": 120,
        },
    )
    assert worker.status_code == 200
    assert worker.json()["Data"]["PlanningRun"] is None


def test_concurrent_workers_cannot_claim_the_same_planning_run(monkeypatch):
    client = TestClient(create_app())
    master_data_payload = _master_data_import_calculate_payload()
    master_data_payload.pop("ProblemID")
    master_data_payload.pop("ScheduleStartAt")
    master_data_payload.update(
        {
            "VersionID": "MDV-CONCURRENT-1",
            "CapturedAt": "2026-06-16T07:30:00+00:00",
            "CreatedBy": "planner-1",
        }
    )
    assert client.post(
        "/planner/workbench/master-data/versions", json=master_data_payload
    ).status_code == 200
    assert client.post(
        "/planner/workbench/operational-state/snapshots",
        json={
            "SnapshotID": "OPS-CONCURRENT-1",
            "CapturedAt": "2026-06-16T07:45:00+00:00",
        },
    ).status_code == 200
    assert client.post(
        "/planner/workbench/planning-runs",
        json={
            "RunID": "RUN-CONCURRENT-1",
            "ProblemID": "PLAN-CONCURRENT-1",
            "MasterDataVersionID": "MDV-CONCURRENT-1",
            "OperationalStateSnapshotID": "OPS-CONCURRENT-1",
            "ScheduleStartAt": "2026-06-16T08:00:00+00:00",
            "RequestedBy": "planner-1",
            "RequestedAt": "2026-06-16T07:50:00+00:00",
        },
    ).status_code == 200
    assert client.post(
        "/planner/workbench/planning-runs/RUN-CONCURRENT-1/enqueue",
        json={
            "EnqueuedBy": "planner-1",
            "EnqueuedAt": "2026-06-16T07:51:00+00:00",
        },
    ).status_code == 200

    def slow_token(_length):
        sleep(0.2)
        return f"lease-{get_ident()}"

    monkeypatch.setattr("sdbr.api.token_urlsafe", slow_token)

    def claim(worker_id):
        return client.post(
            "/planner/workbench/planning-runs/jobs/claim-next",
            json={
                "WorkerID": worker_id,
                "ClaimedAt": "2026-06-16T07:52:00+00:00",
                "LeaseSeconds": 120,
            },
        ).json()["Data"]["PlanningRun"]

    with ThreadPoolExecutor(max_workers=2) as executor:
        claims = list(executor.map(claim, ["worker-a", "worker-b"]))

    claimed_runs = [claim for claim in claims if claim is not None]
    assert len(claimed_runs) == 1
    assert claimed_runs[0]["RunID"] == "RUN-CONCURRENT-1"
    audit = client.get(
        "/planner/workbench/planning-runs/audit-events",
        params={"run_id": "RUN-CONCURRENT-1", "action": "PlanningRunClaimed"},
    ).json()["Data"]
    assert audit["Total"] == 1


def test_planning_run_retries_recoverable_failure_then_moves_to_dead_letter(
    monkeypatch,
):
    client = TestClient(create_app())
    master_data_payload = _master_data_import_calculate_payload()
    master_data_payload.pop("ProblemID")
    master_data_payload.pop("ScheduleStartAt")
    master_data_payload.update(
        {
            "VersionID": "MDV-RETRY-1",
            "CapturedAt": "2026-06-16T07:30:00+00:00",
            "CreatedBy": "planner-1",
        }
    )
    assert client.post(
        "/planner/workbench/master-data/versions", json=master_data_payload
    ).status_code == 200
    assert client.post(
        "/planner/workbench/operational-state/snapshots",
        json={
            "SnapshotID": "OPS-RETRY-1",
            "CapturedAt": "2026-06-16T07:45:00+00:00",
        },
    ).status_code == 200
    assert client.post(
        "/planner/workbench/planning-runs",
        json={
            "RunID": "RUN-RETRY-1",
            "ProblemID": "PLAN-RETRY-1",
            "MasterDataVersionID": "MDV-RETRY-1",
            "OperationalStateSnapshotID": "OPS-RETRY-1",
            "ScheduleStartAt": "2026-06-16T08:00:00+00:00",
            "RequestedBy": "planner-1",
            "RequestedAt": "2026-06-16T07:50:00+00:00",
        },
    ).status_code == 200
    enqueue = client.post(
        "/planner/workbench/planning-runs/RUN-RETRY-1/enqueue",
        json={
            "EnqueuedBy": "planner-1",
            "EnqueuedAt": "2026-06-16T07:51:00+00:00",
            "MaxAttempts": 2,
            "RetryDelaySeconds": 60,
        },
    )
    assert enqueue.status_code == 200

    monkeypatch.setattr(
        "sdbr.api._execute_planning_run",
        lambda **_kwargs: {
            "Status": "Failed",
            "SolverStatus": "Error",
            "SolverMessage": "Temporary solver service failure.",
            "Schedule": None,
        },
    )

    first_claim = client.post(
        "/planner/workbench/planning-runs/jobs/claim-next",
        json={
            "WorkerID": "worker-1",
            "ClaimedAt": "2026-06-16T07:52:00+00:00",
            "LeaseSeconds": 120,
        },
    ).json()["Data"]["PlanningRun"]
    first_failure = client.post(
        "/planner/workbench/planning-runs/RUN-RETRY-1/execute",
        json={
            "ExecutedBy": "worker-1",
            "StartedAt": "2026-06-16T07:52:01+00:00",
            "CompletedAt": "2026-06-16T07:52:10+00:00",
            "LeaseToken": first_claim["LeaseToken"],
        },
    )
    assert first_failure.status_code == 200
    retry_run = first_failure.json()["Data"]["PlanningRun"]
    assert retry_run["Status"] == "Queued"
    assert retry_run["NextAttemptAt"] == "2026-06-16T07:53:10+00:00"
    assert retry_run["LastFailure"]["SolverStatus"] == "Error"

    early_claim = client.post(
        "/planner/workbench/planning-runs/jobs/claim-next",
        json={
            "WorkerID": "worker-2",
            "ClaimedAt": "2026-06-16T07:53:00+00:00",
            "LeaseSeconds": 120,
        },
    )
    assert early_claim.json()["Data"]["PlanningRun"] is None

    second_claim = client.post(
        "/planner/workbench/planning-runs/jobs/claim-next",
        json={
            "WorkerID": "worker-2",
            "ClaimedAt": "2026-06-16T07:54:00+00:00",
            "LeaseSeconds": 120,
        },
    ).json()["Data"]["PlanningRun"]
    second_failure = client.post(
        "/planner/workbench/planning-runs/RUN-RETRY-1/execute",
        json={
            "ExecutedBy": "worker-2",
            "StartedAt": "2026-06-16T07:54:01+00:00",
            "CompletedAt": "2026-06-16T07:54:10+00:00",
            "LeaseToken": second_claim["LeaseToken"],
        },
    )
    assert second_failure.status_code == 200
    dead_letter = second_failure.json()["Data"]["PlanningRun"]
    assert dead_letter["Status"] == "DeadLetter"
    assert dead_letter["AttemptCount"] == 2
    assert dead_letter["DeadLetterReason"] == "MaxAttemptsExceeded"

    no_more_claims = client.post(
        "/planner/workbench/planning-runs/jobs/claim-next",
        json={
            "WorkerID": "worker-3",
            "ClaimedAt": "2026-06-16T08:00:00+00:00",
            "LeaseSeconds": 120,
        },
    )
    assert no_more_claims.json()["Data"]["PlanningRun"] is None

    dead_letter_list = client.get(
        "/planner/workbench/planning-runs",
        params={"status": "DeadLetter", "limit": 10, "offset": 0},
    )
    assert dead_letter_list.status_code == 200
    listed = dead_letter_list.json()["Data"]
    assert listed["Total"] == 1
    assert listed["PlanningRuns"][0]["RunID"] == "RUN-RETRY-1"

    metrics = client.get(
        "/planner/workbench/planning-runs/metrics",
        params={"observed_at": "2026-06-16T08:00:00+00:00"},
    )
    assert metrics.status_code == 200
    metric_data = metrics.json()["Data"]
    assert metric_data["ByStatus"]["DeadLetter"] == 1
    assert metric_data["DeadLetterCount"] == 1
    assert metric_data["TotalAttempts"] == 2

    recover = client.post(
        "/planner/workbench/planning-runs/RUN-RETRY-1/recover",
        json={
            "RecoveredBy": "planner-2",
            "RecoveredAt": "2026-06-16T08:01:00+00:00",
            "Reason": "Solver service restored.",
            "ResetAttempts": True,
        },
    )
    assert recover.status_code == 200
    recovered = recover.json()["Data"]["PlanningRun"]
    assert recovered["Status"] == "Queued"
    assert recovered["AttemptCount"] == 0
    assert recovered["NextAttemptAt"] == "2026-06-16T08:01:00+00:00"
    assert recovered["PreviousDeadLetter"]["Reason"] == "MaxAttemptsExceeded"
    assert recovered["RecoveryReason"] == "Solver service restored."

    recovered_claim = client.post(
        "/planner/workbench/planning-runs/jobs/claim-next",
        json={
            "WorkerID": "worker-3",
            "ClaimedAt": "2026-06-16T08:01:00+00:00",
            "LeaseSeconds": 120,
        },
    )
    assert recovered_claim.status_code == 200
    claimed = recovered_claim.json()["Data"]["PlanningRun"]
    assert claimed["RunID"] == "RUN-RETRY-1"
    assert claimed["AttemptCount"] == 1


def test_planning_run_rejects_unknown_or_invalid_frozen_inputs():
    client = TestClient(create_app())

    missing = client.post(
        "/planner/workbench/planning-runs",
        json={
            "RunID": "RUN-MISSING",
            "ProblemID": "PLAN-MISSING",
            "MasterDataVersionID": "MDV-MISSING",
            "OperationalStateSnapshotID": "OPS-MISSING",
            "ScheduleStartAt": "2026-06-16T08:00:00+00:00",
            "RequestedBy": "planner-1",
            "RequestedAt": "2026-06-16T07:50:00+00:00",
        },
    )
    assert missing.status_code == 404
    assert missing.json()["Data"]["Status"] == "MasterDataVersionNotFound"


def test_planner_workbench_master_data_import_calculate_endpoint_returns_workbench_view():
    client = TestClient(create_app())

    response = client.post(
        "/planner/workbench/master-data/import/calculate",
        json=_master_data_import_calculate_payload(),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["Endpoint"] == "/planner/workbench/master-data/import/calculate"
    assert payload["Data"]["Validation"]["IsValid"] is True
    assert payload["Data"]["OrderCount"] == 1
    assert payload["Data"]["SolverStatus"] == "Feasible"
    assert payload["Data"]["LoadGraphRows"][0]["ResourceID"] == "WC-DRUM"
    assert payload["Data"]["GanttRows"][0]["Bars"][0]["OrderID"] == "WO-1"
    assert payload["Data"]["InventoryBufferBoard"][0]["ItemID"] == "RM-STEEL"


def test_planner_workbench_master_data_import_calculate_endpoint_rejects_invalid_package():
    client = TestClient(create_app(), raise_server_exceptions=False)
    request_payload = _master_data_import_calculate_payload()
    request_payload["OrderRows"][0]["ProductID"] = "FG-MISSING"

    response = client.post(
        "/planner/workbench/master-data/import/calculate",
        json=request_payload,
    )

    assert response.status_code == 409
    payload = response.json()
    assert payload["Endpoint"] == "/planner/workbench/master-data/import/calculate"
    assert payload["StatusCode"] == 409
    assert payload["Data"]["Validation"]["IsValid"] is False
    assert {
        "Severity": "Error",
        "Code": "UNKNOWN_PRODUCT_ROUTING",
        "Message": "Order WO-1 references product FG-MISSING without a routing.",
        "Field": "Orders.WO-1.ProductID",
    } in payload["Data"]["Validation"]["Issues"]


def test_planner_workbench_master_data_import_calculate_endpoint_uses_calendar_rows():
    client = TestClient(create_app())
    request_payload = _master_data_import_calculate_payload()
    request_payload["CalendarTimezone"] = "UTC"
    request_payload["ResourceRows"][0]["CapacityMinutes"] = 999
    request_payload["CalendarRows"] = [
        {
            "ResourceID": "WC-DRUM",
            "CalendarID": "CAL-DRUM",
            "WorkingWeekdays": [0, 1, 2, 3, 4],
            "ShiftName": "Day",
            "ShiftStart": "08:00:00",
            "ShiftEnd": "12:00:00",
            "MaintenanceStart": "2026-06-16T10:00:00+00:00",
            "MaintenanceEnd": "2026-06-16T11:00:00+00:00",
        }
    ]

    response = client.post(
        "/planner/workbench/master-data/import/calculate",
        json=request_payload,
    )

    assert response.status_code == 200
    payload = response.json()
    cell = payload["Data"]["LoadGraphRows"][0]["Cells"][0]
    assert payload["Data"]["Validation"]["IsValid"] is True
    assert cell["CapacityMinutes"] == 180
    assert cell["RequiredMinutes"] == 120


def test_planner_workbench_master_data_import_release_endpoint_blocks_inventory_risk():
    client = TestClient(create_app())
    request_payload = _master_data_import_calculate_payload()
    request_payload["InventoryBufferRows"][0]["OnHandQty"] = 55
    request_payload["MaterialRequirementRows"] = [
        {
            "OrderID": "WO-1",
            "ItemID": "RM-STEEL",
            "LocationID": "SUPPLIER-DECOUPLING",
            "RequiredQty": 10,
        }
    ]

    response = client.post(
        "/planner/workbench/master-data/import/release",
        json={
            **request_payload,
            "OrderID": "WO-1",
            "RequestedReleaseAt": "2026-06-20T06:00:00+00:00",
        },
    )

    assert response.status_code == 409
    payload = response.json()
    assert payload["Endpoint"] == "/planner/workbench/master-data/import/release"
    assert payload["Data"]["Allowed"] is False
    assert payload["Data"]["Status"] == "ReleaseBlockedByInventoryBuffer"
    assert payload["Data"]["InventoryRisks"][0]["ProjectedOnHandQty"] == 45.0


def test_planner_workbench_master_data_import_release_endpoint_rejects_invalid_material_requirements():
    client = TestClient(create_app(), raise_server_exceptions=False)
    request_payload = _master_data_import_calculate_payload()
    request_payload["MaterialRequirementRows"] = [
        {
            "OrderID": "WO-MISSING",
            "ItemID": "RM-STEEL",
            "LocationID": "SUPPLIER-DECOUPLING",
            "RequiredQty": 10,
        }
    ]

    response = client.post(
        "/planner/workbench/master-data/import/release",
        json={
            **request_payload,
            "OrderID": "WO-1",
            "RequestedReleaseAt": "2026-06-20T06:00:00+00:00",
        },
    )

    assert response.status_code == 409
    payload = response.json()
    assert payload["Endpoint"] == "/planner/workbench/master-data/import/release"
    assert payload["Data"]["Validation"]["IsValid"] is False
    assert {
        "Severity": "Error",
        "Code": "UNKNOWN_MATERIAL_REQUIREMENT_ORDER",
        "Message": "Material requirement for RM-STEEL references missing order WO-MISSING.",
        "Field": "MaterialRequirements.WO-MISSING.RM-STEEL.OrderID",
    } in payload["Data"]["Validation"]["Issues"]


def test_data_readiness_endpoint_returns_structured_empty_state():
    client = TestClient(create_app())

    response = client.get(
        "/planner/workbench/data-readiness",
        params={"EvaluatedAt": "2026-06-19T08:00:00+00:00"},
    )

    assert response.status_code == 200
    data = response.json()["Data"]
    assert data["OverallStatus"] == "Empty"
    assert data["CanCreatePlanningRun"] is False
    assert data["LatestMasterDataVersion"] is None
    assert data["LatestOperationalStateSnapshot"] is None
    assert [issue["Code"] for issue in data["Issues"]] == [
        "MASTER_DATA_VERSION_MISSING",
        "OPERATIONAL_STATE_SNAPSHOT_MISSING",
    ]


def test_data_readiness_endpoint_returns_latest_safe_summaries():
    client = TestClient(create_app())
    master_data_payload = _master_data_import_calculate_payload()
    master_data_payload.pop("ProblemID")
    master_data_payload.pop("ScheduleStartAt")
    master_data_payload.update(
        {
            "VersionID": "MDV-READY-1",
            "CapturedAt": "2026-06-19T07:00:00+00:00",
            "SourceSystem": "ERP",
            "CreatedBy": "planner-1",
        }
    )
    assert client.post(
        "/planner/workbench/master-data/versions", json=master_data_payload
    ).status_code == 200
    assert client.post(
        "/planner/workbench/operational-state/snapshots",
        json={
            "SnapshotID": "OPS-READY-1",
            "CapturedAt": "2026-06-19T07:30:00+00:00",
            "InventoryBuffers": [
                {
                    "ItemID": "RM-STEEL",
                    "LocationID": "SUPPLIER-DECOUPLING",
                    "OnHandQty": 35,
                    "RedZoneQty": 50,
                    "YellowZoneQty": 120,
                    "GreenZoneQty": 200,
                }
            ],
            "MaterialAvailability": [
                {
                    "ItemID": "RM-STEEL",
                    "LocationID": "SUPPLIER-DECOUPLING",
                    "AllocatedQty": 10,
                    "InboundQty": 20,
                    "InboundAvailableAt": "2026-06-19T10:00:00+00:00",
                }
            ],
            "WipLimits": [
                {"ScopeID": "PLANT", "CurrentWipCount": 3, "MaxWipCount": 10}
            ],
        },
    ).status_code == 200

    response = client.get(
        "/planner/workbench/data-readiness",
        params={
            "EvaluatedAt": "2026-06-19T08:00:00+00:00",
            "MaxSnapshotAgeMinutes": 60,
        },
    )

    assert response.status_code == 200
    data = response.json()["Data"]
    assert data["OverallStatus"] == "ReadyWithWarnings"
    assert data["CanCreatePlanningRun"] is True
    assert data["LatestMasterDataVersion"] == {
        "VersionID": "MDV-READY-1",
        "CapturedAt": "2026-06-19T07:00:00+00:00",
        "SourceSystem": "ERP",
        "CreatedBy": "planner-1",
        "Status": "Valid",
        "Summary": {
            "ResourceCount": 1,
            "ConstraintResourceCount": 1,
            "CalendarResourceCount": 0,
            "RoutingCount": 1,
            "OrderCount": 1,
            "InventoryBufferCount": 1,
            "MaterialRequirementCount": 0,
        },
    }
    snapshot = data["LatestOperationalStateSnapshot"]
    assert snapshot["SnapshotID"] == "OPS-READY-1"
    assert snapshot["Freshness"]["Status"] == "Fresh"
    assert snapshot["Freshness"]["AgeMinutes"] == 30.0
    assert snapshot["Summary"] == {
        "InventoryBufferCount": 1,
        "MaterialAvailabilityCount": 1,
        "InboundItemCount": 1,
        "WipScopeCount": 1,
        "ResourceStatusCount": None,
    }
    assert snapshot["SourceSystem"] is None
    assert [issue["Code"] for issue in data["Issues"]] == [
        "OPERATIONAL_SOURCE_NOT_PROVIDED",
        "RESOURCE_STATUS_NOT_CAPTURED",
    ]
    assert "Resources" not in data["LatestMasterDataVersion"]
    assert "MaterialAvailability" not in snapshot


def test_data_readiness_endpoint_blocks_stale_operational_snapshot():
    store = WorkbenchStateStore()
    store.operational_state_snapshots["OPS-STALE"] = create_operational_state_snapshot(
        snapshot_id="OPS-STALE",
        captured_at=datetime(2026, 6, 19, 5, 0, tzinfo=timezone.utc),
        inventory_buffers=[],
        material_availability=[],
        wip_limits=[],
    )
    client = TestClient(create_app(state_store=store))

    response = client.get(
        "/planner/workbench/data-readiness",
        params={
            "EvaluatedAt": "2026-06-19T08:00:00+00:00",
            "MaxSnapshotAgeMinutes": 60,
        },
    )

    data = response.json()["Data"]
    assert data["CanCreatePlanningRun"] is False
    assert data["LatestOperationalStateSnapshot"]["Freshness"]["Status"] == "Stale"
    assert "OPERATIONAL_STATE_SNAPSHOT_STALE" in [
        issue["Code"] for issue in data["Issues"]
    ]


def test_planner_workbench_page_returns_semantic_application_shell():
    client = TestClient(create_app())

    response = client.get("/planner/workbench")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    html = response.text
    assert "<title>SDBR Planner Workbench</title>" in html
    assert 'class="app-shell"' in html
    assert 'id="primary-navigation"' in html
    assert 'id="top-context"' in html
    assert 'id="workspace"' in html
    assert 'data-route="overview"' in html
    assert 'data-route="data-readiness"' in html
    assert 'data-route="planning-runs"' in html
    assert 'data-route="schedule-results"' in html
    assert 'data-route="release-management"' in html
    assert 'data-route="exceptions"' in html
    assert 'data-route="administration"' in html
    assert 'id="master-data-version"' in html
    assert 'id="snapshot-freshness"' in html
    assert 'id="system-health"' in html
    assert 'id="current-user"' in html
    assert 'id="language-select"' in html
    assert 'value="zh"' in html
    assert 'value="en"' in html
    assert "需求驱动计划员工作台" in html
    assert 'href="/planner/assets/planner-workbench.css"' in html
    assert 'src="/planner/assets/planner-workbench.js?v=20260620-ui-confirmation"' in html
    assert 'id="master-data-input"' not in html
    assert "DEFAULT_MASTER_DATA" not in html


def test_planner_workbench_page_exposes_data_readiness_workspace_without_raw_json():
    client = TestClient(create_app())

    html = client.get("/planner/workbench").text
    script = client.get("/planner/assets/planner-workbench.js").text

    assert 'id="data-readiness-view"' in html
    assert 'id="readiness-overall-status"' in html
    assert 'id="master-data-summary"' in html
    assert 'id="operational-state-summary"' in html
    assert 'id="readiness-issues"' in html
    assert 'id="issues-drawer"' in html
    assert 'id="issues-drawer" class="issues-drawer"' in html
    assert 'aria-hidden="true" hidden' in html
    assert 'id="select-planning-inputs"' in html
    assert 'id="create-master-data-version"' in html
    assert "/planner/workbench/data-readiness" in script
    assert "loadDataReadiness" in script
    assert "renderReadinessIssues" in script
    assert "readiness-issue-group" in script
    assert 'errors: "阻塞问题"' in script
    assert 'warnings: "警告"' in script
    assert "function localizedSeverity" in script
    assert "function localizedEntityType" in script
    assert 'entityMasterDataVersion: "主数据版本"' in script
    assert 'entityOperationalStateSnapshot: "运行状态快照"' in script
    assert 'technicalCode: "技术代码"' in script
    assert 'latestMasterDataVersion: "最新主数据版本"' in script
    assert 'latestOperationalSnapshot: "最新运行状态快照"' in script
    assert 'version: "版本编号"' in script
    assert 'snapshot: "快照编号"' in script
    assert 'wipScopes: "在制品（WIP）范围"' in script
    assert "最新 Master Data Version" not in html
    assert "最新 Operational State Snapshot" not in html
    assert '`${issue.Severity} / ${issue.EntityType}' not in script
    assert '.empty-workspace[hidden]' in client.get(
        "/planner/assets/planner-workbench.css"
    ).text
    assert "DEFAULT_MASTER_DATA" not in script


def test_planning_run_workbench_endpoint_returns_safe_rows_and_capabilities():
    store = WorkbenchStateStore()
    store.planning_runs["RUN-PENDING"] = {
        "RunID": "RUN-PENDING",
        "ProblemID": "PLAN-A",
        "Status": "Pending",
        "MasterDataVersionID": "MDV-1",
        "OperationalStateSnapshotID": "OPS-1",
        "ScheduleStartAt": "2026-06-19T08:00:00+00:00",
        "TimeBufferMinutes": 120,
        "SolverBackendID": "gurobi",
        "SolverStatus": "Pending",
        "SolverMessage": "Waiting.",
        "RequestedBy": "planner-1",
        "RequestedAt": "2026-06-19T07:00:00+00:00",
        "StartedAt": None,
        "CompletedAt": None,
        "AttemptCount": 0,
        "StatusHistory": [],
        "LeaseTokenHash": "secret-hash",
    }
    client = TestClient(create_app(state_store=store))

    response = client.get("/planner/workbench/planning-runs/workbench")

    assert response.status_code == 200
    data = response.json()["Data"]
    assert data["Total"] == 1
    assert data["Rows"][0]["RunID"] == "RUN-PENDING"
    assert data["Rows"][0]["AllowedActions"] == ["Enqueue", "Execute", "Cancel"]
    assert data["Rows"][0]["DurationSeconds"] is None
    assert "LeaseTokenHash" not in data["Rows"][0]
    assert [item["BackendID"] for item in data["Capabilities"]["Solvers"]] == [
        "ortools",
        "gurobi",
    ]
    assert data["Capabilities"]["Solvers"][0]["Available"] is True
    assert data["Capabilities"]["Solvers"][1]["Status"] == "Paused"
    assert data["Capabilities"]["Simio"]["Available"] is False


def test_worker_does_not_claim_queued_run_for_paused_gurobi_backend():
    store = WorkbenchStateStore()
    store.planning_runs["RUN-GUROBI-QUEUED"] = {
        "RunID": "RUN-GUROBI-QUEUED",
        "ProblemID": "PLAN-HISTORICAL",
        "Status": "Queued",
        "SolverBackendID": "gurobi",
        "RequestedAt": "2026-06-19T07:00:00+00:00",
        "EnqueuedAt": "2026-06-19T07:01:00+00:00",
        "NextAttemptAt": "2026-06-19T07:01:00+00:00",
        "StatusHistory": [],
    }
    client = TestClient(create_app(state_store=store))

    response = client.post(
        "/planner/workbench/planning-runs/jobs/claim-next",
        json={
            "WorkerID": "worker-1",
            "ClaimedAt": "2026-06-19T08:00:00+00:00",
            "LeaseSeconds": 120,
        },
    )

    assert response.status_code == 200
    assert response.json()["Data"]["PlanningRun"] is None
    assert store.planning_runs["RUN-GUROBI-QUEUED"]["Status"] == "Queued"


def test_planning_run_creation_freezes_solver_and_retry_policy_for_ui_run_002():
    client = TestClient(create_app())
    master_data_payload = _master_data_import_calculate_payload()
    master_data_payload.pop("ProblemID")
    master_data_payload.pop("ScheduleStartAt")
    master_data_payload.update(
        {
            "VersionID": "MDV-UI-POLICY",
            "CapturedAt": "2026-06-19T06:30:00+00:00",
            "SourceSystem": "ERP",
            "CreatedBy": "planner-1",
        }
    )
    assert client.post(
        "/planner/workbench/master-data/versions",
        json=master_data_payload,
    ).status_code == 200
    assert client.post(
        "/planner/workbench/operational-state/snapshots",
        json={
            "SnapshotID": "OPS-UI-POLICY",
            "CapturedAt": "2026-06-19T06:45:00+00:00",
        },
    ).status_code == 200

    response = client.post(
        "/planner/workbench/planning-runs",
        json={
            "RunID": "RUN-UI-POLICY",
            "ProblemID": "PLAN-UI-POLICY",
            "MasterDataVersionID": "MDV-UI-POLICY",
            "OperationalStateSnapshotID": "OPS-UI-POLICY",
            "ScheduleStartAt": "2026-06-19T08:00:00+00:00",
            "TimeBufferMinutes": 120,
            "SolverBackendID": "ortools",
            "TimeLimitSeconds": 420,
            "MaxAttempts": 4,
            "RetryDelaySeconds": 90,
            "RequestedBy": "planner-1",
            "RequestedAt": "2026-06-19T07:00:00+00:00",
        },
    )

    assert response.status_code == 200
    planning_run = response.json()["Data"]["PlanningRun"]
    assert planning_run["TimeLimitSeconds"] == 420
    assert planning_run["MaxAttempts"] == 4
    assert planning_run["RetryDelaySeconds"] == 90


def test_planning_run_workbench_detail_combines_timeline_audit_and_safe_worker_summary():
    store = WorkbenchStateStore()
    store.planning_runs["RUN-RUNNING"] = {
        "RunID": "RUN-RUNNING",
        "ProblemID": "PLAN-B",
        "Status": "Running",
        "MasterDataVersionID": "MDV-2",
        "MasterDataCapturedAt": "2026-06-19T06:00:00+00:00",
        "OperationalStateSnapshotID": "OPS-2",
        "OperationalStateCapturedAt": "2026-06-19T06:30:00+00:00",
        "ScheduleStartAt": "2026-06-19T08:00:00+00:00",
        "TimeBufferMinutes": 90,
        "SolverBackendID": "gurobi",
        "SolverStatus": "Running",
        "SolverMessage": "Solving.",
        "RequestedBy": "planner-2",
        "RequestedAt": "2026-06-19T06:50:00+00:00",
        "StartedAt": "2026-06-19T07:00:00+00:00",
        "CompletedAt": None,
        "AttemptCount": 1,
        "MaxAttempts": 3,
        "WorkerID": "worker-a",
        "LeaseClaimedAt": "2026-06-19T07:00:00+00:00",
        "LeaseExpiresAt": "2026-06-19T07:05:00+00:00",
        "LeaseRenewalCount": 2,
        "LeaseTokenHash": "secret-hash",
        "StatusHistory": [
            {
                "Status": "Pending",
                "ChangedAt": "2026-06-19T06:50:00+00:00",
                "ChangedBy": "planner-2",
            },
            {
                "Status": "Running",
                "ChangedAt": "2026-06-19T07:00:00+00:00",
                "ChangedBy": "worker-a",
            },
        ],
    }
    store.audit_events.append(
        {
            "EventID": "AUD-1",
            "RunID": "RUN-RUNNING",
            "Action": "PlanningRunClaimed",
            "ActorID": "worker-a",
            "OccurredAt": "2026-06-19T07:00:00+00:00",
            "Details": {"AttemptCount": 1},
        }
    )
    client = TestClient(create_app(state_store=store))

    response = client.get(
        "/planner/workbench/planning-runs/RUN-RUNNING/workbench"
    )

    assert response.status_code == 200
    detail = response.json()["Data"]
    assert detail["AllowedActions"] == []
    assert detail["Worker"] == {
        "WorkerID": "worker-a",
        "LeaseClaimedAt": "2026-06-19T07:00:00+00:00",
        "LeaseExpiresAt": "2026-06-19T07:05:00+00:00",
        "LeaseRenewalCount": 2,
    }
    assert len(detail["Timeline"]) == 2
    assert detail["AuditEvents"][0]["Action"] == "PlanningRunClaimed"
    assert "LeaseTokenHash" not in str(detail)


def test_planner_workbench_page_exposes_planning_run_center_and_wizard():
    client = TestClient(create_app())

    html = client.get("/planner/workbench").text
    script = client.get("/planner/assets/planner-workbench.js").text

    assert 'id="planning-runs-view"' in html
    assert 'id="planning-run-table"' in html
    assert 'id="planning-run-status-filter"' in html
    assert 'id="planning-run-time-filter"' in html
    assert 'id="planning-run-solver-filter"' in html
    assert 'id="create-planning-run"' in html
    assert 'id="planning-run-wizard"' in html
    assert 'id="planning-run-detail"' in html
    assert 'id="solver-gurobi"' in html
    assert 'id="solver-ortools"' in html
    assert 'id="solver-ortools" type="radio" name="solver" value="ortools" checked' in html
    assert 'id="solver-gurobi" type="radio" name="solver" value="gurobi" disabled' in html
    assert "OR-Tools CP-SAT" in html
    assert 'id="simio-validation"' in html
    assert "/planner/workbench/planning-runs/workbench" in script
    assert "loadPlanningRuns" in script
    assert "renderPlanningRunDetail" in script
    assert "submitPlanningRun" in script
    assert 'SolverBackendID: "ortools"' in script
    assert 'confirmExecute: "确认立即调用 OR-Tools CP-SAT 执行此排程任务？"' in script
    assert 'confirmExecute: "Run this planning task with OR-Tools CP-SAT now?"' in script
    assert 'action === "Execute"' in script
    assert 'action === "Cancel"' in script
    assert 'action === "Recover"' in script
    assert "/execute`" in script
    assert "/cancel`" in script
    assert "/recover`" in script


def _schedule_result_test_store() -> WorkbenchStateStore:
    store = WorkbenchStateStore()
    store.master_data_versions["MDV-RESULT"] = {
        "VersionID": "MDV-RESULT",
        "Resources": [
            {
                "ResourceID": "WC-DRUM",
                "Name": "Drum",
                "IsConstraint": True,
                "ResourceType": "Machine",
                "LocationID": "PLANT-A",
                "OwnerID": "planner-1",
                "Category": "Cutting",
                "Calendar": {
                    "CalendarID": "CAL-DRUM",
                    "MaintenanceWindows": [
                        {
                            "Start": "2026-06-19T10:00:00+00:00",
                            "End": "2026-06-19T11:00:00+00:00",
                        }
                    ],
                },
            }
        ],
        "Orders": [
            {
                "OrderID": "WO-1",
                "ProductID": "FG-A",
                "Quantity": 1,
                "OrderDate": "2026-06-18T08:00:00+00:00",
                "DueDate": "2026-06-19T12:00:00+00:00",
                "PromiseDate": "2026-06-19T12:00:00+00:00",
                "TargetStartDate": "2026-06-19",
                "OrderFamily": "FAMILY-A",
            }
        ],
        "Routings": [
            {
                "RoutingID": "ROUTE-FG-A",
                "ProductID": "FG-A",
                "IsPrimary": True,
                "Operations": [],
            }
        ],
        "MaterialRequirements": [
            {
                "OrderID": "WO-1",
                "ItemID": "RM-STEEL",
                "LocationID": "SUPPLIER-DECOUPLING",
                "RequiredQty": 10,
            }
        ],
    }
    store.planning_runs["RUN-RESULT"] = {
        "RunID": "RUN-RESULT",
        "ProblemID": "PLAN-RESULT",
        "Status": "Completed",
        "MasterDataVersionID": "MDV-RESULT",
        "OperationalStateSnapshotID": "OPS-RESULT",
        "TimeBufferMinutes": 120,
        "SolverBackendID": "gurobi",
        "SolverStatus": "Optimal",
        "SolverMessage": "Solved.",
        "RequestedBy": "planner-1",
        "RequestedAt": "2026-06-19T07:00:00+00:00",
        "StartedAt": "2026-06-19T07:05:00+00:00",
        "CompletedAt": "2026-06-19T07:06:00+00:00",
        "AttemptCount": 1,
        "Schedule": {
            "GeneratedAt": "2026-06-19T07:06:00+00:00",
            "SolverBackendID": "gurobi",
            "SolverStatus": "Optimal",
            "SolverMessage": "Solved.",
            "SolverDiagnostics": [],
            "OrderCount": 1,
            "ConstraintOverloadCount": 1,
            "LoadGraphRows": [
                {
                    "ResourceID": "WC-DRUM",
                    "ResourceName": "Drum",
                    "IsConstraint": True,
                    "Cells": [
                        {
                            "Date": "2026-06-19",
                            "RequiredMinutes": 600,
                            "CapacityMinutes": 480,
                            "OverloadMinutes": 120,
                            "LoadPercent": 125.0,
                        }
                    ],
                }
            ],
            "GanttRows": [
                {
                    "ResourceID": "WC-DRUM",
                    "Bars": [
                        {
                            "OperationID": "CUT",
                            "OrderID": "WO-1",
                            "Start": "2026-06-19T08:00:00+00:00",
                            "End": "2026-06-19T10:00:00+00:00",
                            "DurationMinutes": 120,
                        }
                    ],
                }
            ],
            "ReleaseRecommendations": [
                {
                    "OrderID": "WO-1",
                    "SuggestedReleaseDate": "2026-06-19T06:00:00+00:00",
                }
            ],
            "BufferBoard": [
                {
                    "OrderID": "WO-1",
                    "Zone": "Red",
                    "SuggestedReleaseDate": "2026-06-19T06:00:00+00:00",
                    "TargetStartDate": "2026-06-19",
                }
            ],
            "BufferSummary": {
                "RedCount": 1,
                "YellowCount": 0,
                "GreenCount": 0,
                "HasCriticalAlert": True,
                "HighestSeverity": "Red",
            },
            "BottleneckCandidates": [],
            "ExecutionPriorityQueue": [
                {
                    "Rank": 1,
                    "OrderID": "WO-1",
                    "Zone": "Red",
                    "PriorityReason": "Red buffer penetration",
                    "RecommendedAction": "Expedite",
                    "SuggestedReleaseDate": "2026-06-19T06:00:00+00:00",
                }
            ],
        },
    }
    return store


def test_be_ui_003_schedule_result_workbench_returns_kpis_gantt_and_load_views():
    client = TestClient(create_app(state_store=_schedule_result_test_store()))

    response = client.get(
        "/planner/workbench/schedule-results/runs/RUN-RESULT/workbench"
    )

    assert response.status_code == 200
    data = response.json()["Data"]
    assert data["Context"]["RunID"] == "RUN-RESULT"
    assert data["KPIs"]["OrderCount"] == 1
    assert data["KPIs"]["TotalOverloadMinutes"] == 120
    assert data["KPIs"]["RedBufferCount"] == 1
    assert data["Gantt"]["Rows"][0]["Bars"][0]["BarType"] == "TimeBuffer"
    assert data["Gantt"]["Rows"][0]["Bars"][1]["BarType"] == "Processing"
    assert data["Gantt"]["Rows"][0]["Bars"][2]["BarType"] == "Maintenance"
    assert data["Gantt"]["Rows"][0]["Bars"][0]["BufferZone"] == "Red"
    assert data["SystemLoad"]["Rows"][0]["LoadPercent"] == 125.0
    assert data["ResourceLoad"]["Rows"][0]["RemainingMinutes"] == 600
    assert data["FilterOptions"]["Resources"][0]["ResourceID"] == "WC-DRUM"
    assert data["OrderDelivery"][0]["Status"] == "OnTime"
    assert "Schedule" not in data


def test_be_ui_003_schedule_result_rejects_incomplete_run():
    store = _schedule_result_test_store()
    store.planning_runs["RUN-RESULT"]["Status"] = "Running"
    client = TestClient(create_app(state_store=store))

    response = client.get(
        "/planner/workbench/schedule-results/runs/RUN-RESULT/workbench"
    )

    assert response.status_code == 409
    assert response.json()["Data"]["Status"] == "ScheduleResultUnavailable"


def test_be_ui_003_compares_runs_and_audits_selected_scenario():
    store = _schedule_result_test_store()
    candidate = dict(store.planning_runs["RUN-RESULT"])
    candidate["RunID"] = "RUN-CANDIDATE"
    candidate["Schedule"] = dict(candidate["Schedule"])
    candidate["Schedule"]["ConstraintOverloadCount"] = 0
    candidate["Schedule"]["LoadGraphRows"] = [
        {
            **candidate["Schedule"]["LoadGraphRows"][0],
            "Cells": [
                {
                    "Date": "2026-06-19",
                    "RequiredMinutes": 420,
                    "CapacityMinutes": 480,
                    "OverloadMinutes": 0,
                    "LoadPercent": 87.5,
                }
            ],
        }
    ]
    store.planning_runs["RUN-CANDIDATE"] = candidate
    client = TestClient(create_app(state_store=store))

    comparison = client.get(
        "/planner/workbench/schedule-results/compare",
        params={
            "baseline_run_id": "RUN-RESULT",
            "candidate_run_id": "RUN-CANDIDATE",
        },
    )
    assert comparison.status_code == 200
    assert comparison.json()["Data"]["RecommendedRunID"] == "RUN-CANDIDATE"
    assert comparison.json()["Data"]["Delta"]["TotalOverloadMinutes"] == -120

    selection = client.post(
        "/planner/workbench/schedule-results/select",
        json={
            "BaselineRunID": "RUN-RESULT",
            "CandidateRunID": "RUN-CANDIDATE",
            "SelectedRunID": "RUN-CANDIDATE",
            "SelectedBy": "planner-1",
            "SelectedAt": "2026-06-19T08:00:00+00:00",
            "Reason": "Lower overload",
        },
    )
    assert selection.status_code == 200
    assert selection.json()["Data"]["Status"] == "SelectedForReview"
    assert store.audit_events[-1]["Action"] == "ScheduleScenarioSelected"


def test_planner_workbench_page_exposes_schedule_result_workspace():
    client = TestClient(create_app())

    html = client.get("/planner/workbench").text
    script = client.get("/planner/assets/planner-workbench.js").text

    assert 'id="schedule-results-view"' in html
    assert 'id="schedule-result-run-select"' in html
    assert 'id="schedule-tab-gantt"' in html
    assert 'id="schedule-tab-load"' in html
    assert 'id="schedule-tab-delivery"' in html
    assert 'id="schedule-tab-diagnostics"' in html
    assert 'id="gantt-board"' in html
    assert 'id="system-load-view"' in html
    assert 'id="resource-load-view"' in html
    assert 'id="scenario-comparison"' in html
    assert "/planner/workbench/schedule-results/runs/" in script
    assert "/planner/workbench/schedule-results/compare" in script


def test_planner_workbench_page_exposes_case_acceptance_overview():
    # UI-OVERVIEW-001 / BE-DATA-014
    client = TestClient(create_app())

    html = client.get("/planner/workbench").text
    script = client.get("/planner/assets/planner-workbench.js").text

    assert 'id="overview-view"' in html
    assert 'id="case-acceptance-cards"' in html
    assert 'data-case-summary="PassedCount"' in html
    assert "/planner/workbench/test-data/acceptance" in script
    assert "caseAcceptanceTitle" in script


def test_planner_workbench_page_exposes_plan_publication_governance():
    # UI-PLANPUB-001 / BE-RUN-009 / BE-OUT-010
    client = TestClient(create_app())

    html = client.get("/planner/workbench").text
    script = client.get("/planner/assets/planner-workbench.js").text

    assert 'id="plan-publication-governance"' in html
    assert 'id="publication-status-chip"' in html
    assert 'id="publication-actions"' in html
    assert 'id="publication-package"' in html
    assert 'id="publication-history"' in html
    assert "/planner/workbench/planning-runs/" in script
    assert "/publication/" in script
    assert 'statusDraft: "草案"' in script
    assert 'statusReviewed: "已复核"' in script
    assert 'statusApproved: "已批准"' in script
    assert 'statusPublished: "已发布"' in script
    assert 'statusPublicationRevoked: "已撤销"' in script
    assert 'statusSuperseded: "已被替代"' in script


def _add_release_snapshot(client: TestClient, *, current_wip: int = 0) -> None:
    response = client.post(
        "/planner/workbench/operational-state/snapshots",
        json={
            "SnapshotID": "OPS-RESULT",
            "CapturedAt": "2026-06-19T07:30:00+00:00",
            "InventoryBuffers": [
                {
                    "ItemID": "RM-STEEL",
                    "LocationID": "SUPPLIER-DECOUPLING",
                    "OnHandQty": 80,
                    "RedZoneQty": 50,
                    "YellowZoneQty": 120,
                    "GreenZoneQty": 200,
                }
            ],
            "WipLimits": [
                {
                    "ScopeID": "DRUM-FEED",
                    "CurrentWipCount": current_wip,
                    "MaxWipCount": 5,
                }
            ],
        },
    )
    assert response.status_code == 200


def test_be_out_008_009_work_order_read_model_and_audited_commands():
    store = _schedule_result_test_store()
    client = TestClient(create_app(state_store=store))

    response = client.get(
        "/planner/workbench/schedule-results/runs/RUN-RESULT/work-orders/workbench"
    )

    assert response.status_code == 200
    data = response.json()["Data"]
    row = data["Rows"][0]
    assert row["OrderID"] == "WO-1"
    assert row["ProductID"] == "FG-A"
    assert row["PlannedReleaseAt"] == "2026-06-19T06:00:00+00:00"
    assert row["PromiseDate"] == "2026-06-19T12:00:00+00:00"
    assert row["ReleaseStatus"] == "NotReleased"
    assert row["ExecutionPriority"] == 1
    assert row["RoutingID"] == "ROUTE-FG-A"
    assert row["ResourceIDs"] == ["WC-DRUM"]
    assert data["ViewMetadata"]["GeneratedAt"] == "2026-06-19T07:06:00+00:00"

    command = client.post(
        "/planner/workbench/schedule-results/runs/RUN-RESULT/work-orders/commands",
        json={
            "Command": "Lock",
            "OrderIDs": ["WO-1"],
            "ActorID": "planner-1",
            "OccurredAt": "2026-06-19T07:45:00+00:00",
        },
    )
    assert command.status_code == 200
    assert store.audit_events[-1]["Action"] == "ScheduledWorkOrdersLocked"

    detail = client.get(
        "/planner/workbench/schedule-results/runs/RUN-RESULT/work-orders/WO-1/workbench"
    )
    assert detail.status_code == 200
    detail_data = detail.json()["Data"]
    assert detail_data["Order"]["IsLocked"] is True
    assert detail_data["Operations"][0]["OperationID"] == "CUT"
    assert detail_data["PlanningContext"]["RunID"] == "RUN-RESULT"
    assert detail_data["PlanningContext"]["MasterDataVersionID"] == "MDV-RESULT"
    assert detail_data["CommercialContext"]["CustomerID"] is None
    assert detail_data["ProductionContext"]["ResourceIDs"] == ["WC-DRUM"]
    assert detail_data["ReleaseContext"]["DispatchStatus"] == "NotReleased"
    assert detail_data["Notes"] == []
    assert detail_data["UserDefinedFields"] == {}
    assert detail_data["AuditEvents"][0]["Action"] == "ScheduledWorkOrdersLocked"


def test_be_ui_004_planning_run_release_workbench_authorizes_only_ready_order():
    store = _schedule_result_test_store()
    client = TestClient(create_app(state_store=store))
    _add_release_snapshot(client)

    response = client.get(
        "/planner/workbench/release-management/runs/RUN-RESULT/workbench",
        params={"evaluated_at": "2026-06-19T07:50:00+00:00"},
    )

    assert response.status_code == 200
    data = response.json()["Data"]
    candidate = data["Candidates"][0]
    assert candidate["OrderID"] == "WO-1"
    assert candidate["BufferZone"] == "Red"
    assert candidate["BufferPenetrationPercent"] > 90
    assert candidate["RopeStatus"] == "Ready"
    assert candidate["MaterialStatus"] == "Clear"
    assert candidate["WipStatus"] == "Clear"
    assert candidate["CanAuthorize"] is True
    assert candidate["BlockingReasons"] == []

    authorization = client.post(
        "/planner/workbench/release-management/runs/RUN-RESULT/orders/WO-1/authorize",
        json={
            "ReleasedBy": "planner-1",
            "ReleasedAt": "2026-06-19T07:50:00+00:00",
            "OperationalStateMaxAgeMinutes": 60,
        },
    )
    assert authorization.status_code == 200
    record = authorization.json()["Data"]["Authorization"]
    assert record["Status"] == "Authorized"
    dispatch = client.get(
        f"/planner/workbench/release-authorizations/{record['AuthorizationID']}/dispatch-package"
    )
    assert dispatch.status_code == 200
    assert dispatch.json()["Data"]["DispatchPackage"]["OrderID"] == "WO-1"


def test_be_rel_012_release_management_returns_frozen_policy_snapshot():
    # BE-REL-012
    client = TestClient(create_app())
    _create_master_data_and_snapshot(
        client, version_id="MDV-REL-POL", snapshot_id="OPS-REL-POL"
    )
    assert client.post(
        "/planner/workbench/dbr/release-policies",
        json={
            "VersionID": "DBR-POLICY-REL",
            "CreatedAt": "2026-06-16T07:20:00+00:00",
            "CreatedBy": "planner-1",
            "RopeBufferMinutes": 75,
            "ConsecutiveBlockedThreshold": 4,
            "Status": "Active",
        },
    ).status_code == 200
    _create_and_execute_planning_run(
        client,
        run_id="RUN-REL-POL",
        master_data_version_id="MDV-REL-POL",
        snapshot_id="OPS-REL-POL",
        release_policy_version_id="DBR-POLICY-REL",
    )

    response = client.get(
        "/planner/workbench/release-management/runs/RUN-REL-POL/workbench",
        params={"evaluated_at": "2026-06-16T08:30:00+00:00"},
    )

    assert response.status_code == 200
    data = response.json()["Data"]
    assert data["ReleasePolicyVersionID"] == "DBR-POLICY-REL"
    assert data["ReleasePolicySnapshot"]["RopeBufferMinutes"] == 75
    assert data["ReleasePolicySnapshot"]["StabilityPolicy"][
        "ConsecutiveBlockedThreshold"
    ] == 4


def test_be_ui_004_release_workbench_returns_structured_wip_block_reason():
    client = TestClient(create_app(state_store=_schedule_result_test_store()))
    _add_release_snapshot(client, current_wip=5)

    response = client.get(
        "/planner/workbench/release-management/runs/RUN-RESULT/workbench",
        params={"evaluated_at": "2026-06-19T07:50:00+00:00"},
    )

    assert response.status_code == 200
    candidate = response.json()["Data"]["Candidates"][0]
    assert candidate["CanAuthorize"] is False
    assert candidate["RecommendedAction"] == "HoldForWip"
    assert candidate["BlockingReasons"][0]["Code"] == "WIP_LIMIT_EXCEEDED"


def test_planner_workbench_page_exposes_scheduled_orders_and_release_management():
    client = TestClient(create_app())

    html = client.get("/planner/workbench").text
    script = client.get("/planner/assets/planner-workbench.js").text

    assert 'id="scheduled-orders-panel"' in html
    assert 'id="scheduled-orders-table"' in html
    assert 'id="scheduled-order-detail"' in html
    assert 'id="release-management-view"' in html
    assert 'id="release-candidate-table"' in html
    assert 'id="release-reason-detail"' in html
    assert 'id="dispatch-package-detail"' in html
    assert "SCHEDULE_VIEW_STORAGE_KEY" in script
    assert "/work-orders/workbench" in script
    assert "/release-management/runs/" in script
    assert "/authorize`" in script


def _buffer_board_test_store() -> WorkbenchStateStore:
    store = _schedule_result_test_store()
    store.master_data_versions["MDV-RESULT"]["Orders"][0]["CustomerID"] = "CUSTOMER-A"
    candidate = {
        "OrderID": "WO-1",
        "ScheduledStart": "2026-06-19T08:00:00+00:00",
        "ScheduledEnd": "2026-06-19T10:00:00+00:00",
        "SuggestedReleaseAt": "2026-06-19T06:00:00+00:00",
        "RecommendedAction": "ReadyForRelease",
    }
    store.release_authorizations.append(
        create_release_authorization(
            request_id="RUN-RESULT",
            candidate=candidate,
            released_by="planner-1",
            released_at=datetime(2026, 6, 19, 7, 30, tzinfo=timezone.utc),
            operational_state_snapshot_id="OPS-RESULT",
        )
    )
    return store


def test_be_rel_010_buffer_board_returns_two_stages_and_five_zones():
    store = _buffer_board_test_store()
    client = TestClient(create_app(state_store=store))

    response = client.get(
        "/planner/workbench/buffer-board/runs/RUN-RESULT/workbench",
        params={"evaluated_at": "2026-06-19T07:50:00+00:00"},
    )

    assert response.status_code == 200
    data = response.json()["Data"]
    assert data["Context"] == {
        "RunID": "RUN-RESULT",
        "LocationID": "PLANT-A",
        "ConstraintResourceID": "WC-DRUM",
        "ConstraintResourceName": "Drum",
        "BufferOwnerID": "planner-1",
        "DailyLoadMinutes": 120,
        "LastScheduledAt": "2026-06-19T07:06:00+00:00",
        "EvaluatedAt": "2026-06-19T07:50:00+00:00",
    }
    assert [row["Stage"] for row in data["Rows"]] == [
        "YetToBeReceived",
        "Received",
    ]
    assert [cell["Zone"] for cell in data["Rows"][0]["Cells"]] == [
        "Early",
        "Green",
        "Yellow",
        "Red",
        "Late",
    ]
    red = data["Rows"][0]["Cells"][3]
    assert red["OrderCount"] == 1
    assert red["TotalLoadMinutes"] == 120
    assert red["Orders"][0]["OrderID"] == "WO-1"
    assert red["Orders"][0]["ProductID"] == "FG-A"
    assert red["Orders"][0]["Quantity"] == 1
    assert data["TransactionPolicy"]["MeasureTypes"] == [
        "Quantity",
        "CompletionPercent",
        "Hours",
    ]
    assert data["TransactionPolicy"]["ReasonRequiredZones"] == ["Late"]


def test_be_rel_010_buffer_board_moves_arrived_order_to_received_and_returns_detail():
    store = _buffer_board_test_store()
    authorization = store.release_authorizations[0]
    store.execution_events.append(
        {
            "AuthorizationID": authorization.authorization_id,
            "OrderID": "WO-1",
            "EventType": "ArrivedBuffer",
            "EventAt": "2026-06-19T07:55:00+00:00",
            "TargetStartAt": "2026-06-19T08:00:00+00:00",
            "ExceptionCode": None,
            "Status": "Accepted",
            "RequiresReview": False,
        }
    )
    client = TestClient(create_app(state_store=store))

    board = client.get(
        "/planner/workbench/buffer-board/runs/RUN-RESULT/workbench",
        params={"evaluated_at": "2026-06-19T07:55:00+00:00"},
    ).json()["Data"]
    assert board["Rows"][1]["Cells"][3]["OrderCount"] == 1

    response = client.get(
        "/planner/workbench/buffer-board/runs/RUN-RESULT/orders/WO-1/workbench",
        params={"evaluated_at": "2026-06-19T07:55:00+00:00"},
    )
    assert response.status_code == 200
    detail = response.json()["Data"]
    assert detail["Order"]["CustomerID"] == "CUSTOMER-A"
    assert detail["Order"]["PromiseDate"] == "2026-06-19T12:00:00+00:00"
    assert detail["Order"]["Priority"] == 1
    assert detail["Execution"]["Stage"] == "Received"
    assert detail["Execution"]["Zone"] == "Red"
    assert detail["Execution"]["CurrentReasonCode"] is None


def test_be_exec_003_buffer_board_late_transaction_requires_standard_reason_code():
    store = _buffer_board_test_store()
    client = TestClient(create_app(state_store=store))
    authorization_id = store.release_authorizations[0].authorization_id
    endpoint = "/planner/workbench/buffer-board/runs/RUN-RESULT/orders/WO-1/transactions"
    payload = {
        "EventType": "ArrivedBuffer",
        "EventAt": "2026-06-19T08:10:00+00:00",
        "ActorID": "operator-1",
        "MeasureType": "Quantity",
        "MeasureValue": 1,
    }

    rejected = client.post(endpoint, json=payload)

    assert rejected.status_code == 409
    assert rejected.json()["Data"]["Status"] == "ReasonCodeRequired"
    assert rejected.json()["Data"]["AuthorizationID"] == authorization_id

    accepted = client.post(
        endpoint,
        json={**payload, "ExceptionCode": "MATERIAL_SHORTAGE"},
    )
    assert accepted.status_code == 200
    event = accepted.json()["Data"]["Event"]
    assert event["AuthorizationID"] == authorization_id
    assert event["MeasureType"] == "Quantity"
    assert event["MeasureValue"] == 1
    assert event["ActorID"] == "operator-1"


def test_ui_buffer_001_workbench_exposes_bilingual_buffer_execution_board():
    client = TestClient(create_app())

    html = client.get("/planner/workbench").text
    script = client.get("/planner/assets/planner-workbench.js").text

    assert 'data-route="buffer-board"' in html
    assert 'id="buffer-board-view"' in html
    assert 'id="buffer-board-matrix"' in html
    assert 'id="buffer-order-detail"' in html
    assert 'id="buffer-transaction-dialog"' in html
    assert 'navBuffer: "缓冲执行"' in script
    assert 'navBuffer: "Buffer Execution"' in script
    assert "/planner/workbench/buffer-board/runs/" in script


def _exception_center_test_store() -> WorkbenchStateStore:
    store = _buffer_board_test_store()
    store.operational_state_snapshots["OPS-RESULT"] = create_operational_state_snapshot(
        snapshot_id="OPS-RESULT",
        captured_at=datetime(2026, 6, 19, 7, 30, tzinfo=timezone.utc),
        inventory_buffers=[],
        material_availability=[],
        wip_limits=[],
    )
    store.planning_runs["RUN-FAILED"] = {
        "RunID": "RUN-FAILED",
        "ProblemID": "PLAN-FAILED",
        "Status": "Failed",
        "MasterDataVersionID": "MDV-RESULT",
        "OperationalStateSnapshotID": "OPS-RESULT",
        "SolverBackendID": "gurobi",
        "SolverStatus": "Error",
        "SolverMessage": "Solver stopped before a feasible schedule was produced.",
        "RequestedBy": "planner-1",
        "RequestedAt": "2026-06-19T07:10:00+00:00",
        "StartedAt": "2026-06-19T07:11:00+00:00",
        "CompletedAt": "2026-06-19T07:12:00+00:00",
        "AttemptCount": 1,
        "LastFailure": {"SolverStatus": "Error", "SolverMessage": "Solver stopped."},
        "StatusHistory": [
            {"Status": "Failed", "ChangedAt": "2026-06-19T07:12:00+00:00", "ChangedBy": "worker-1"}
        ],
    }
    store.planning_runs["RUN-DEAD"] = {
        **store.planning_runs["RUN-FAILED"],
        "RunID": "RUN-DEAD",
        "ProblemID": "PLAN-DEAD",
        "Status": "DeadLetter",
        "DeadLetterReason": "MaxAttemptsExceeded",
        "RequestedAt": "2026-06-19T07:00:00+00:00",
        "CompletedAt": "2026-06-19T07:20:00+00:00",
        "AttemptCount": 3,
    }
    store.audit_events.append(
        {
            "RunID": "RUN-DEAD",
            "Action": "PlanningRunMovedToDeadLetter",
            "ActorID": "worker-1",
            "OccurredAt": "2026-06-19T07:20:00+00:00",
        }
    )
    store.replan_requests.append(
        ReplanRequest(
            request_id="RPL-EXC-1",
            problem_id="PLAN-RESULT",
            order_id="WO-1",
            planned_release_at=datetime(2026, 6, 19, 6, 0, tzinfo=timezone.utc),
            detected_at=datetime(2026, 6, 19, 8, 5, tzinfo=timezone.utc),
            reason_code="ExecutionDeviationCritical",
            deviation_minutes=125,
            consecutive_blocked_count=3,
            source="ExecutionVariance",
            status="PendingReview",
            source_reference_id="PKG-EXC-1",
            requested_by="planner-1",
        )
    )
    return store


def test_be_ui_005_exception_center_aggregates_structured_business_exceptions():
    client = TestClient(create_app(state_store=_exception_center_test_store()))

    response = client.get(
        "/planner/workbench/exceptions/workbench",
        params={"evaluated_at": "2026-06-19T08:10:00+00:00"},
    )

    assert response.status_code == 200
    data = response.json()["Data"]
    assert data["Summary"]["TotalCount"] >= 5
    assert data["Summary"]["CriticalCount"] >= 2
    assert data["Summary"]["OpenCount"] == data["Summary"]["TotalCount"]
    assert {row["ExceptionType"] for row in data["Rows"]} >= {
        "PlanningRunDeadLetter",
        "PlanningRunFailed",
        "ConstraintBufferRisk",
        "ExecutionAlert",
        "ReplanSuggestion",
    }
    dead_letter = next(row for row in data["Rows"] if row["ObjectID"] == "RUN-DEAD")
    assert dead_letter["Severity"] == "Critical"
    assert dead_letter["ObjectType"] == "PlanningRun"
    assert dead_letter["ReasonCode"] == "MaxAttemptsExceeded"
    assert dead_letter["SuggestedActionCode"] == "RecoverPlanningRun"
    assert dead_letter["AuditTrail"][0]["Action"] == "PlanningRunMovedToDeadLetter"
    assert set(dead_letter) == {
        "ExceptionID",
        "ExceptionType",
        "Severity",
        "Status",
        "ObjectType",
        "ObjectID",
        "OccurredAt",
        "ReasonCode",
        "BusinessImpactCode",
        "SuggestedActionCode",
        "OwnerID",
        "Source",
        "AuditTrail",
    }
    assert "Schedule" not in data


def test_be_ui_005_exception_center_returns_detail_by_exception_id():
    client = TestClient(create_app(state_store=_exception_center_test_store()))
    workbench = client.get(
        "/planner/workbench/exceptions/workbench",
        params={"evaluated_at": "2026-06-19T08:10:00+00:00"},
    ).json()["Data"]
    exception_id = next(
        row["ExceptionID"]
        for row in workbench["Rows"]
        if row["ExceptionType"] == "ReplanSuggestion"
    )

    response = client.get(
        f"/planner/workbench/exceptions/{exception_id}/workbench",
        params={"evaluated_at": "2026-06-19T08:10:00+00:00"},
    )

    assert response.status_code == 200
    detail = response.json()["Data"]
    assert detail["Exception"]["ExceptionID"] == exception_id
    assert detail["Exception"]["ObjectID"] == "RPL-EXC-1"
    assert detail["RelatedObjects"][0]["ObjectType"] == "WorkOrder"
    assert detail["ResolutionActions"][0]["ActionCode"] == "ReviewReplanRequest"


def test_ui_exception_001_workbench_exposes_bilingual_exception_center():
    client = TestClient(create_app())

    html = client.get("/planner/workbench").text
    script = client.get("/planner/assets/planner-workbench.js").text

    assert 'id="exceptions-view"' in html
    assert 'id="exception-center-table"' in html
    assert 'id="exception-detail"' in html
    assert 'navExceptions: "异常中心"' in script
    assert 'navExceptions: "Exceptions"' in script
    assert "/planner/workbench/exceptions/workbench" in script


def test_be_ui_006_administration_workbench_returns_safe_configuration_model():
    # BE-UI-006 / UI-ADMIN-001 / UI-ADMIN-002
    client = TestClient(create_app(state_store=_exception_center_test_store()))

    response = client.get("/planner/workbench/administration/workbench")

    assert response.status_code == 200
    payload = response.json()
    assert payload["Endpoint"] == "/planner/workbench/administration/workbench"
    data = payload["Data"]
    assert data["AdminMode"] == "ReadOnly"
    assert data["SensitiveEditingAllowed"] is False
    assert data["MasterDataObjects"][0]["ObjectKey"] == "Resources"
    assert "Routings" in [item["ObjectKey"] for item in data["MasterDataObjects"]]
    resources = next(
        item for item in data["MasterDataObjects"] if item["ObjectKey"] == "Resources"
    )
    routings = next(
        item for item in data["MasterDataObjects"] if item["ObjectKey"] == "Routings"
    )
    orders = next(
        item for item in data["MasterDataObjects"] if item["ObjectKey"] == "Orders"
    )
    assert "ResourceQuantity" in resources["ReservedFields"]
    assert "SetupMinutes" in resources["ReservedFields"]
    assert "OwnerID" in resources["ReservedFields"]
    assert "BatchFamily" in routings["ReservedFields"]
    assert "SplitPolicy" in routings["ReservedFields"]
    assert "BatchID" in orders["ReservedFields"]
    assert "MaximumBatchQuantity" in orders["ReservedFields"]
    batching = next(
        item for item in data["PolicyGroups"] if item["GroupKey"] == "BatchingRules"
    )
    assert batching["Options"] == [
        "BatchFamily",
        "MergeRule",
        "SplitPolicy",
        "MinimumSplitQuantity",
        "MaximumBatchQuantity",
        "MixedOrderAllowed",
    ]
    assert data["CalendarLayers"] == [
        "DayDefinition",
        "WeekDefinition",
        "TemporaryShiftOverride",
        "ExclusionOrMaintenance",
    ]
    assert data["CalendarConfiguration"]["Status"] == "EditableViaVersionedMasterData"
    assert data["CalendarConfiguration"]["TemporaryOverrideApiStatus"] == "Available"
    assert data["CalendarConfiguration"]["OverrideCount"] == 0
    assert data["ReleasePolicyConfiguration"]["Status"] == "Versioned"
    assert "RopeBufferMinutes" in data["ReleasePolicyConfiguration"]["ConfigurableParameters"]
    assert data["SchedulingStrategyConfiguration"]["ActiveSolverBackendID"] == "ortools"
    assert "gurobi" in data["SchedulingStrategyConfiguration"]["PausedSolverBackendIDs"]
    assert (
        data["SchedulingStrategyConfiguration"]["CustomWeightPersistenceStatus"]
        == "Available"
    )
    assert "Batching" in data["SchedulingStrategyConfiguration"]["DeferredBusinessRules"]
    assert data["IntegrationContracts"]["Status"] == "ContractOnly"
    assert data["IntegrationContracts"]["ContractCount"] == 4
    assert data["RawJsonDebug"]["DefaultVisible"] is False
    assert data["Solvers"][0]["SolverID"] == "ortools"
    assert data["Solvers"][0]["Status"] == "Available"
    assert data["Solvers"][0]["CanSelectForPlanningRun"] is True
    assert next(item for item in data["Solvers"] if item["SolverID"] == "gurobi")[
        "Status"
    ] == "Paused"
    assert next(item for item in data["Solvers"] if item["SolverID"] == "ortools")[
        "Status"
    ] == "Available"
    assert next(item for item in data["Integrations"] if item["SystemID"] == "simio")[
        "Status"
    ] == "Paused"
    assert data["StateStore"]["Status"] in {"Healthy", "Unhealthy"}
    assert data["WorkerQueue"]["TotalRuns"] >= 0
    assert "Resources" not in str(data.get("LatestMasterDataPreview", {}))


def test_be_data_010_ui_006_calendar_override_configuration_is_persisted(tmp_path):
    # BE-DATA-010 / BE-UI-006
    from sdbr.state_store import SQLiteWorkbenchStateStore

    database_path = tmp_path / "workbench.db"
    client = TestClient(create_app(state_store=SQLiteWorkbenchStateStore(database_path)))

    response = client.post(
        "/planner/workbench/admin/calendar-overrides",
        json={
            "OverrideID": "CAL-OVR-001",
            "CalendarID": "CAL-DRUM",
            "ResourceID": "WC-DRUM",
            "OverrideType": "ExclusionOrMaintenance",
            "EffectiveStartAt": "2026-06-20T10:00:00+00:00",
            "EffectiveEndAt": "2026-06-20T11:30:00+00:00",
            "CapacityDeltaMinutes": -90,
            "Reason": "planned maintenance",
            "CreatedAt": "2026-06-19T09:00:00+00:00",
            "CreatedBy": "planner-1",
            "Status": "Active",
        },
    )

    assert response.status_code == 200
    override = response.json()["Data"]["Override"]
    assert override["OverrideID"] == "CAL-OVR-001"
    assert override["SolverDriverStatus"] == "NotApplied"

    invalid = client.post(
        "/planner/workbench/admin/calendar-overrides",
        json={
            "OverrideID": "CAL-OVR-BAD",
            "CalendarID": "CAL-DRUM",
            "OverrideType": "Overtime",
            "EffectiveStartAt": "2026-06-20T11:30:00+00:00",
            "EffectiveEndAt": "2026-06-20T11:30:00+00:00",
            "CreatedAt": "2026-06-19T09:00:00+00:00",
            "CreatedBy": "planner-1",
        },
    )
    assert invalid.status_code == 422
    assert invalid.json()["Data"]["Status"] == "CalendarOverrideInvalid"

    recreated_client = TestClient(
        create_app(state_store=SQLiteWorkbenchStateStore(database_path))
    )
    listed = recreated_client.get("/planner/workbench/admin/calendar-overrides")
    assert listed.status_code == 200
    assert listed.json()["Data"]["ActiveOverrideCount"] == 1
    admin = recreated_client.get("/planner/workbench/administration/workbench").json()[
        "Data"
    ]
    calendar_config = admin["CalendarConfiguration"]
    assert calendar_config["OverrideCount"] == 1
    assert calendar_config["OverrideTypeCounts"]["ExclusionOrMaintenance"] == 1
    assert calendar_config["ConflictCheckStatus"] == "NotEnforced"
    assert admin["StateStore"]["Status"] == "Healthy"


def test_be_solver_014_ui_006_scheduling_strategy_configuration_is_persisted(tmp_path):
    # BE-SOLVER-014 / BE-UI-006
    from sdbr.state_store import SQLiteWorkbenchStateStore

    database_path = tmp_path / "workbench.db"
    client = TestClient(create_app(state_store=SQLiteWorkbenchStateStore(database_path)))

    first = client.post(
        "/planner/workbench/admin/scheduling-strategies",
        json={
            "StrategyID": "STRAT-DELIVERY-CUSTOM",
            "DisplayName": "Delivery custom",
            "CreatedAt": "2026-06-19T09:05:00+00:00",
            "CreatedBy": "planner-1",
            "TardinessWeight": 250,
            "MakespanWeight": 1,
            "AlternateResourcePenaltyWeight": 8,
            "Status": "Active",
        },
    )
    second = client.post(
        "/planner/workbench/admin/scheduling-strategies",
        json={
            "StrategyID": "STRAT-FLOW-CUSTOM",
            "DisplayName": "Flow custom",
            "CreatedAt": "2026-06-19T09:10:00+00:00",
            "CreatedBy": "planner-1",
            "TardinessWeight": 50,
            "MakespanWeight": 20,
            "AlternateResourcePenaltyWeight": 3,
            "Status": "Active",
        },
    )

    assert first.status_code == 200
    assert second.status_code == 200
    recreated_client = TestClient(
        create_app(state_store=SQLiteWorkbenchStateStore(database_path))
    )
    listed = recreated_client.get("/planner/workbench/admin/scheduling-strategies")
    assert listed.status_code == 200
    data = listed.json()["Data"]
    assert data["StrategyCount"] == 2
    assert data["ActiveStrategyID"] == "STRAT-FLOW-CUSTOM"
    assert next(
        item
        for item in data["Strategies"]
        if item["StrategyID"] == "STRAT-DELIVERY-CUSTOM"
    )["Status"] == "Retired"

    admin = recreated_client.get("/planner/workbench/administration/workbench").json()[
        "Data"
    ]
    strategy_config = admin["SchedulingStrategyConfiguration"]
    assert strategy_config["PersistedStrategyCount"] == 2
    assert strategy_config["ActiveStrategyID"] == "STRAT-FLOW-CUSTOM"
    assert "balanced" in strategy_config["ObjectiveStrategies"]
    assert "STRAT-FLOW-CUSTOM" in strategy_config["ObjectiveStrategies"]
    assert strategy_config["StrategyStatusCounts"] == {"Retired": 1, "Active": 1}


def test_ui_admin_001_002_workbench_exposes_bilingual_administration_workspace():
    # UI-ADMIN-001 / UI-ADMIN-002
    client = TestClient(create_app())

    html = client.get("/planner/workbench").text
    script = client.get("/planner/assets/planner-workbench.js").text

    assert 'id="administration-view"' in html
    assert 'id="admin-master-data-objects"' in html
    assert 'id="admin-import-preview"' in html
    assert 'id="admin-routings-import"' in html
    assert 'id="admin-system-capabilities"' in html
    assert 'id="admin-cp-sat-assumptions"' in html
    assert 'id="admin-policy-groups"' in html
    assert 'id="admin-calendar-override-form"' in html
    assert 'id="admin-calendar-overrides"' in html
    assert 'id="admin-debug-json-toggle"' in html
    assert "/planner/workbench/administration/workbench" in script
    assert "/planner/workbench/admin/cp-sat/assumptions" in script
    assert "/planner/workbench/admin/calendar-overrides" in script
    assert 'adminMasterDataTitle: "主数据后台"' in script
    assert 'adminMasterDataTitle: "Master Data Administration"' in script
    assert 'calendarOverrideConfig: "日历临时覆盖配置"' in script
    assert 'calendarOverrideConfig: "Calendar temporary override configuration"' in script
    assert 'partialEditable: "部分可配置"' in script
    assert 'partialEditable: "Partially configurable"' in script
    assert 'cpSatAssumptions: "CP-SAT 建模假设"' in script
    assert 'cpSatAssumptions: "CP-SAT Modeling Assumptions"' in script
    assert 'problem: "计划场景"' in script
    assert 'problem: "Planning scenario"' in script
    assert 'rawJsonHidden: "原始 JSON 默认隐藏，仅管理员调试模式可查看。"' in script
    assert 'rawJsonHidden: "Raw JSON is hidden by default and available only in administrator debug mode."' in script
    assert 'id="master-data-input"' not in html
    assert "DEFAULT_MASTER_DATA" not in script


def test_ui_quality_001_workbench_exposes_shared_components_and_state_contracts():
    # UI-COMP-001..005 / UI-STATE-001..004
    client = TestClient(create_app())

    html = client.get("/planner/workbench").text
    script = client.get("/planner/assets/planner-workbench.js").text
    css = client.get("/planner/assets/planner-workbench.css").text

    assert 'id="notification-region"' in html
    assert 'aria-live="polite"' in html
    assert 'id="action-confirm-dialog"' in html
    assert 'id="confirm-action-impact"' in html
    assert 'data-quality-component="status-chip"' in html
    assert 'data-quality-component="data-table"' in html
    assert 'data-quality-state="loading"' in html
    assert 'data-quality-state="empty"' in html
    assert 'data-quality-state="error"' in html
    assert "function showNotification" in script
    assert "function confirmAction" in script
    assert "window.confirm" not in script
    assert "notifySuccess" in script
    assert "notifyError" in script
    assert ".notification-region" in css
    assert ".notification-item.success" in css
    assert ".confirm-dialog" in css
    assert ".status-chip.is-paused" in css
    assert ".status-chip.is-unavailable" in css
    assert ".loading-block" in css


def test_planner_workbench_styles_define_restrained_and_responsive_layout():
    client = TestClient(create_app())

    response = client.get("/planner/assets/planner-workbench.css")

    assert response.status_code == 200
    assert "text/css" in response.headers["content-type"]
    css = response.text
    assert "--color-primary:" in css
    assert "--color-success:" in css
    assert "--radius-card: 8px" in css
    assert "grid-template-columns: var(--nav-width) minmax(0, 1fr)" in css
    assert "@media (max-width: 900px)" in css
    assert ".navigation.is-open" in css
    assert "overflow-x: auto" in css
    assert "gradient(" not in css


def test_planner_workbench_script_supports_persistent_i18n_routes_and_health():
    client = TestClient(create_app())

    response = client.get("/planner/assets/planner-workbench.js")

    assert response.status_code == 200
    assert "javascript" in response.headers["content-type"]
    script = response.text
    assert "sdbr.language" in script
    assert "localStorage.getItem" in script
    assert "localStorage.setItem" in script
    assert "Intl.DateTimeFormat" in script
    assert "hashchange" in script
    assert "function renderRoute(focusWorkspace = false)" in script
    assert 'window.addEventListener("hashchange", () => renderRoute(true))' in script
    assert "/planner/workbench/state-store/health" in script
    assert "aria-expanded" in script
    assert "document.documentElement.lang" in script


def test_planner_workbench_master_data_validate_endpoint_returns_summary_and_issues():
    client = TestClient(create_app())
    request_payload = _calculate_payload()
    request_payload["Orders"].append(
        {
            "OrderID": "WO-MISSING",
            "ProductID": "FG-MISSING",
            "Quantity": 1,
            "DueDate": "2026-06-21T08:00:00+00:00",
            "TargetStartDate": "2026-06-17",
        }
    )
    request_payload["Routings"][0]["Operations"].append(
        {
            "OperationID": "PACK",
            "ResourceID": "WC-MISSING",
            "DurationMinutes": 30,
            "Sequence": 2,
        }
    )

    response = client.post(
        "/planner/workbench/master-data/validate",
        json=request_payload,
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["Endpoint"] == "/planner/workbench/master-data/validate"
    assert payload["StatusCode"] == 200
    assert payload["Data"]["IsValid"] is False
    assert payload["Data"]["Summary"] == {
        "ResourceCount": 1,
        "ConstraintResourceCount": 1,
        "CalendarResourceCount": 0,
        "RoutingCount": 1,
        "OrderCount": 2,
        "InventoryBufferCount": 1,
        "MaterialRequirementCount": 0,
    }
    assert {
        "Severity": "Error",
        "Code": "UNKNOWN_PRODUCT_ROUTING",
        "Message": "Order WO-MISSING references product FG-MISSING without a routing.",
        "Field": "Orders.WO-MISSING.ProductID",
    } in payload["Data"]["Issues"]
    assert {
        "Severity": "Error",
        "Code": "UNKNOWN_OPERATION_RESOURCE",
        "Message": "Operation PACK references missing resource WC-MISSING.",
        "Field": "Routings.FG-A.PRIMARY.Operations.PACK.ResourceID",
    } in payload["Data"]["Issues"]


def test_planner_workbench_master_data_validate_endpoint_requires_timezone_for_calendars():
    client = TestClient(create_app())
    request_payload = _calculate_payload()
    request_payload["Resources"][0]["Calendar"] = {
        "CalendarID": "CAL-DRUM-DAY",
        "WorkingWeekdays": [0, 1, 2, 3, 4],
        "Holidays": [],
        "Shifts": [
            {"Name": "Day", "Start": "08:00", "End": "16:00"},
        ],
        "MaintenanceWindows": [],
    }

    response = client.post(
        "/planner/workbench/master-data/validate",
        json=request_payload,
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["Data"]["IsValid"] is False
    assert {
        "Severity": "Error",
        "Code": "MISSING_CALENDAR_TIMEZONE",
        "Message": "CalendarTimezone is required when resource calendars are configured.",
        "Field": "CalendarTimezone",
    } in payload["Data"]["Issues"]


def test_planner_workbench_calculate_endpoint_accepts_master_data_payload():
    client = TestClient(create_app())

    response = client.post(
        "/planner/workbench/calculate",
        json=_calculate_payload(),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["Endpoint"] == "/planner/workbench/calculate"
    assert payload["Data"]["Validation"]["IsValid"] is True
    assert payload["Data"]["Validation"]["Issues"] == []
    assert payload["Data"]["OrderCount"] == 1
    assert payload["Data"]["SolverStatus"] == "Feasible"
    assert payload["Data"]["LoadGraphRows"][0]["ResourceID"] == "WC-DRUM"
    assert payload["Data"]["GanttRows"][0]["Bars"][0]["OrderID"] == "WO-1"
    assert payload["Data"]["InventoryBufferBoard"] == [
        {
            "ItemID": "RM-STEEL",
            "LocationID": "SUPPLIER-DECOUPLING",
            "OnHandQty": 35.0,
            "RedZoneQty": 50.0,
            "YellowZoneQty": 120.0,
            "GreenZoneQty": 200.0,
            "Zone": "Red",
            "PenetrationPercent": 70.0,
            "RecommendedAction": "Expedite replenishment",
        }
    ]


def test_planner_workbench_calculate_endpoint_rejects_invalid_master_data():
    client = TestClient(create_app(), raise_server_exceptions=False)
    request_payload = _calculate_payload()
    request_payload["Orders"][0]["ProductID"] = "FG-MISSING"

    response = client.post(
        "/planner/workbench/calculate",
        json=request_payload,
    )

    assert response.status_code == 409
    payload = response.json()
    assert payload["Endpoint"] == "/planner/workbench/calculate"
    assert payload["StatusCode"] == 409
    assert payload["Data"]["Validation"]["IsValid"] is False
    assert {
        "Severity": "Error",
        "Code": "UNKNOWN_PRODUCT_ROUTING",
        "Message": "Order WO-1 references product FG-MISSING without a routing.",
        "Field": "Orders.WO-1.ProductID",
    } in payload["Data"]["Validation"]["Issues"]


def test_planner_workbench_calculate_endpoint_accepts_solver_backend():
    client = TestClient(create_app())
    request_payload = _calculate_payload()
    request_payload["SolverBackendID"] = "ortools"

    response = client.post("/planner/workbench/calculate", json=request_payload)

    assert response.status_code == 200
    payload = response.json()
    assert payload["Data"]["SolverBackendID"] == "ortools"
    assert payload["Data"]["SolverStatus"] in {"Optimal", "Feasible"}
    assert payload["Data"]["GanttRows"]
    assert payload["Data"]["LoadGraphRows"][0]["ResourceID"] == "WC-DRUM"
    assert payload["Data"]["SolverDiagnostics"][0]["Code"] == "ORTOOLS_CP_SAT_MODEL"


def test_planner_workbench_calculate_endpoint_accepts_advanced_cp_sat_fields():
    client = TestClient(create_app())
    request_payload = _calculate_payload()
    request_payload["SolverBackendID"] = "ortools"
    request_payload["ObjectiveStrategyID"] = "delivery_first"
    request_payload["Resources"][0]["EfficiencyPercent"] = 50
    request_payload["Routings"][0]["Operations"][0]["SetupFamily"] = "FAM-A"
    request_payload["Routings"][0]["Operations"][0]["EarliestStartAt"] = (
        "2026-06-16T08:00:00+00:00"
    )
    request_payload["Routings"][0]["Operations"][0]["LatestEndAt"] = (
        "2026-06-16T16:00:00+00:00"
    )
    request_payload["SetupTransitions"] = [
        {
            "ResourceID": "WC-DRUM",
            "FromFamily": "FAM-A",
            "ToFamily": "FAM-B",
            "SetupMinutes": 30,
        }
    ]

    response = client.post("/planner/workbench/calculate", json=request_payload)

    assert response.status_code == 200
    payload = response.json()
    data = payload["Data"]
    assert data["ObjectiveStrategyID"] == "delivery_first"
    assert data["SetupTransitions"] == request_payload["SetupTransitions"]
    codes = {item["Code"] for item in data["SolverDiagnostics"]}
    assert "ORTOOLS_OBJECTIVE_STRATEGY" in codes
    assert "ORTOOLS_SETUP_TRANSITIONS_ENABLED" in codes
    assert "ORTOOLS_RESOURCE_EFFICIENCY_ENABLED" in codes
    assert "ORTOOLS_OPERATION_TIME_WINDOWS_ENABLED" in codes


def test_be_solver_014_cp_sat_assumptions_endpoint_lists_tunable_parameters():
    # BE-SOLVER-014 / BE-UI-006
    client = TestClient(create_app())

    response = client.get("/planner/workbench/admin/cp-sat/assumptions")

    assert response.status_code == 200
    data = response.json()["Data"]
    assert data["SolverBackendID"] == "ortools"
    assert "gurobi" in data["PausedSolverBackendIDs"]
    assert {item["AssumptionID"] for item in data["ModelingAssumptions"]} >= {
        "TIME_INTEGER_MINUTES",
        "NO_FULL_MRP_IN_SOLVER",
        "SINGLE_UNIT_SETUP_ONLY",
    }
    assert {item["ParameterID"] for item in data["TunableParameters"]} >= {
        "TimeLimitSeconds",
        "ObjectiveStrategyID",
        "ObjectiveWeights",
        "ReleasePolicy",
    }
    assert "BomMrp" in data["DeferredRules"]


def test_be_solver_014_calculate_applies_custom_objective_strategy():
    # BE-SOLVER-014
    client = TestClient(create_app())
    assert client.post(
        "/planner/workbench/admin/scheduling-strategies",
        json={
            "StrategyID": "STRAT-CUSTOM-FAST-FLOW",
            "DisplayName": "Custom fast flow",
            "CreatedAt": "2026-06-19T09:10:00+00:00",
            "CreatedBy": "planner-1",
            "TardinessWeight": 7,
            "MakespanWeight": 13,
            "AlternateResourcePenaltyWeight": 2,
            "Status": "Active",
        },
    ).status_code == 200
    request_payload = _calculate_payload()
    request_payload["SolverBackendID"] = "ortools"
    request_payload["ObjectiveStrategyID"] = "STRAT-CUSTOM-FAST-FLOW"

    response = client.post("/planner/workbench/calculate", json=request_payload)

    assert response.status_code == 200
    data = response.json()["Data"]
    assert data["ObjectiveStrategyID"] == "STRAT-CUSTOM-FAST-FLOW"
    assert data["ObjectiveWeights"] == {
        "StrategyID": "STRAT-CUSTOM-FAST-FLOW",
        "TardinessWeight": 7.0,
        "MakespanWeight": 13.0,
        "AlternateResourcePenaltyWeight": 2.0,
    }
    codes = {item["Code"] for item in data["SolverDiagnostics"]}
    assert "ORTOOLS_CUSTOM_OBJECTIVE_WEIGHTS_ENABLED" in codes

    missing = dict(request_payload)
    missing["ObjectiveStrategyID"] = "STRAT-MISSING"
    rejected = client.post("/planner/workbench/calculate", json=missing)
    assert rejected.status_code == 404
    assert rejected.json()["Data"]["Status"] == "SchedulingStrategyNotFound"


def test_be_solver_014_planning_run_freezes_custom_objective_strategy():
    # BE-SOLVER-014 / BE-RUN-001
    client = TestClient(create_app())
    _create_master_data_and_snapshot(
        client, version_id="MDV-STRATEGY-FREEZE", snapshot_id="OPS-STRATEGY-FREEZE"
    )
    assert client.post(
        "/planner/workbench/admin/scheduling-strategies",
        json={
            "StrategyID": "STRAT-FROZEN",
            "DisplayName": "Frozen custom",
            "CreatedAt": "2026-06-19T09:10:00+00:00",
            "CreatedBy": "planner-1",
            "TardinessWeight": 11,
            "MakespanWeight": 3,
            "AlternateResourcePenaltyWeight": 5,
            "Status": "Active",
        },
    ).status_code == 200
    create_response = client.post(
        "/planner/workbench/planning-runs",
        json={
            "RunID": "RUN-STRATEGY-FREEZE",
            "ProblemID": "P-STRATEGY-FREEZE",
            "MasterDataVersionID": "MDV-STRATEGY-FREEZE",
            "OperationalStateSnapshotID": "OPS-STRATEGY-FREEZE",
            "ScheduleStartAt": "2026-06-16T08:00:00+00:00",
            "ObjectiveStrategyID": "STRAT-FROZEN",
            "SolverBackendID": "ortools",
            "RequestedBy": "planner-1",
            "RequestedAt": "2026-06-16T07:50:00+00:00",
        },
    )
    assert create_response.status_code == 200
    pending = create_response.json()["Data"]["PlanningRun"]
    assert pending["FrozenSchedulingStrategy"]["ObjectiveWeights"][
        "TardinessWeight"
    ] == 11

    assert client.post(
        "/planner/workbench/admin/scheduling-strategies",
        json={
            "StrategyID": "STRAT-FROZEN-REPLACEMENT",
            "DisplayName": "Replacement custom",
            "CreatedAt": "2026-06-19T09:20:00+00:00",
            "CreatedBy": "planner-1",
            "TardinessWeight": 99,
            "MakespanWeight": 99,
            "AlternateResourcePenaltyWeight": 99,
            "Status": "Active",
        },
    ).status_code == 200
    execute_response = client.post(
        "/planner/workbench/planning-runs/RUN-STRATEGY-FREEZE/execute",
        json={
            "ExecutedBy": "planner-1",
            "StartedAt": "2026-06-16T07:55:00+00:00",
            "CompletedAt": "2026-06-16T07:56:00+00:00",
        },
    )

    assert execute_response.status_code == 200
    run = execute_response.json()["Data"]["PlanningRun"]
    assert run["Status"] == "Completed"
    assert run["Schedule"]["ObjectiveWeights"] == {
        "StrategyID": "STRAT-FROZEN",
        "TardinessWeight": 11.0,
        "MakespanWeight": 3.0,
        "AlternateResourcePenaltyWeight": 5.0,
    }


def test_planner_workbench_calculate_endpoint_exposes_gurobi_solver_diagnostics():
    client = TestClient(create_app())
    request_payload = _calculate_payload()
    request_payload["SolverBackendID"] = "gurobi"

    response = client.post("/planner/workbench/calculate", json=request_payload)

    assert response.status_code == 200
    payload = response.json()
    assert payload["Data"]["SolverBackendID"] == "gurobi"
    assert payload["Data"]["SolverStatus"] in {"Unavailable", "Optimal", "Feasible"}
    assert payload["Data"]["SolverDiagnostics"]
    if payload["Data"]["SolverStatus"] in {"Optimal", "Feasible"}:
        assert payload["Data"]["GanttRows"][0]["Bars"][0]["OrderID"] == "WO-1"


def test_planner_workbench_calculate_endpoint_passes_alternate_resources_to_gurobi():
    client = TestClient(create_app())
    request_payload = _calculate_payload()
    request_payload["SolverBackendID"] = "gurobi"
    request_payload["Resources"].append(
        {
            "ResourceID": "WC-LASER",
            "Name": "Laser Cell",
            "IsConstraint": True,
            "DailyCapacityMinutes": {"2026-06-16": 480},
        }
    )
    request_payload["Orders"].append(
        {
            "OrderID": "WO-2",
            "ProductID": "FG-A",
            "Quantity": 1,
            "DueDate": "2026-06-20T08:00:00+00:00",
            "TargetStartDate": "2026-06-16",
        }
    )
    request_payload["Routings"][0]["Operations"][0]["AlternateResourceIDs"] = ["WC-LASER"]

    response = client.post("/planner/workbench/calculate", json=request_payload)

    assert response.status_code == 200
    payload = response.json()
    if payload["Data"]["SolverStatus"] == "Unavailable":
        assert payload["Data"]["SolverDiagnostics"]
        return
    rows_by_resource = {
        row["ResourceID"]: row
        for row in payload["Data"]["GanttRows"]
    }
    assert payload["Data"]["SolverStatus"] in {"Optimal", "Feasible"}
    assert "WC-LASER" in rows_by_resource
    assert rows_by_resource["WC-LASER"]["Bars"][0]["OrderID"] in {"WO-1", "WO-2"}


def test_planner_workbench_compare_endpoint_recommends_lower_overload_scenario():
    client = TestClient(create_app())
    baseline = _calculate_payload()
    baseline["Resources"][0]["DailyCapacityMinutes"] = {
        "2026-06-16": 480,
        "2026-06-17": 480,
    }
    baseline["Orders"] = [
        {
            "OrderID": "WO-1",
            "ProductID": "FG-A",
            "Quantity": 3,
            "DueDate": "2026-06-20T08:00:00+00:00",
            "TargetStartDate": "2026-06-16",
        },
        {
            "OrderID": "WO-2",
            "ProductID": "FG-A",
            "Quantity": 3,
            "DueDate": "2026-06-20T08:00:00+00:00",
            "TargetStartDate": "2026-06-16",
        },
    ]
    candidate = {
        **baseline,
        "Orders": [
            baseline["Orders"][0],
            {
                **baseline["Orders"][1],
                "TargetStartDate": "2026-06-17",
            },
        ],
    }

    response = client.post(
        "/planner/workbench/scenarios/compare",
        json={
            "Baseline": baseline,
            "Candidate": candidate,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["Endpoint"] == "/planner/workbench/scenarios/compare"
    assert payload["StatusCode"] == 200
    assert payload["Data"]["RecommendedScenario"] == "Candidate"
    assert payload["Data"]["Baseline"]["TotalOverloadMinutes"] == 240
    assert payload["Data"]["Candidate"]["TotalOverloadMinutes"] == 0
    assert payload["Data"]["Delta"] == {
        "ConstraintOverloadCount": -1,
        "TotalOverloadMinutes": -240,
        "RedBufferCount": -1,
        "CriticalAlertImproved": False,
    }
    assert payload["Data"]["DecisionReasons"] == [
        "Candidate reduces total overload by 240 minutes.",
        "Candidate reduces red buffer count by 1.",
    ]


def test_planner_workbench_compare_endpoint_identifies_invalid_candidate():
    client = TestClient(create_app())
    baseline = _calculate_payload()
    candidate = {
        **baseline,
        "Orders": [
            {
                **baseline["Orders"][0],
                "ProductID": "FG-MISSING",
            }
        ],
    }

    response = client.post(
        "/planner/workbench/scenarios/compare",
        json={
            "Baseline": baseline,
            "Candidate": candidate,
        },
    )

    assert response.status_code == 409
    payload = response.json()
    assert payload["Endpoint"] == "/planner/workbench/scenarios/compare"
    assert payload["StatusCode"] == 409
    assert payload["Data"]["InvalidScenario"] == "Candidate"
    assert payload["Data"]["Message"] == "Candidate scenario failed master data validation."
    assert payload["Data"]["BaselineValidation"]["IsValid"] is True
    assert payload["Data"]["CandidateValidation"]["IsValid"] is False


def test_planner_workbench_calculate_endpoint_uses_resource_calendar_capacity():
    client = TestClient(create_app())
    request_payload = _calculate_payload()
    request_payload["CalendarTimezone"] = "UTC"
    request_payload["Resources"][0]["DailyCapacityMinutes"] = {"2026-06-16": 999}
    request_payload["Resources"][0]["Calendar"] = {
        "CalendarID": "CAL-DRUM-2SHIFT",
        "WorkingWeekdays": [0, 1, 2, 3, 4],
        "Holidays": [],
        "Shifts": [
            {"Name": "Day", "Start": "08:00", "End": "12:00"},
            {"Name": "Afternoon", "Start": "13:00", "End": "17:00"},
        ],
        "MaintenanceWindows": [
            {
                "Start": "2026-06-16T10:00:00+00:00",
                "End": "2026-06-16T12:00:00+00:00",
            }
        ],
    }

    response = client.post("/planner/workbench/calculate", json=request_payload)

    assert response.status_code == 200
    payload = response.json()
    cell = payload["Data"]["LoadGraphRows"][0]["Cells"][0]
    assert cell["CapacityMinutes"] == 360
    assert cell["RequiredMinutes"] == 120
    assert cell["LoadPercent"] == 33.33


def test_planner_workbench_simio_export_endpoint_returns_operation_rows():
    client = TestClient(create_app())

    response = client.post("/planner/workbench/simio/export", json=_calculate_payload())

    assert response.status_code == 200
    payload = response.json()
    assert payload["Endpoint"] == "/planner/workbench/simio/export"
    assert payload["StatusCode"] == 200
    assert payload["Data"]["ProblemID"] == "P-CALC"
    assert payload["Data"]["Format"] == "operation_rows"
    assert payload["Data"]["Rows"] == [
        {
            "OperationID": "WO-1:CUT",
            "OrderID": "WO-1",
            "ResourceID": "WC-DRUM",
            "DurationMinutes": 120,
            "RoutingID": "PRIMARY",
        }
    ]


def test_planner_workbench_release_endpoint_blocks_early_release():
    client = TestClient(create_app())

    response = client.post(
        "/planner/workbench/release",
        json={
            **_calculate_payload(),
            "OrderID": "WO-1",
            "RequestedReleaseAt": "2026-06-20T05:00:00+00:00",
        },
    )

    assert response.status_code == 409
    payload = response.json()
    assert payload["Endpoint"] == "/planner/workbench/release"
    assert payload["StatusCode"] == 409
    assert payload["Data"]["Allowed"] is False
    assert payload["Data"]["Status"] == "ReleaseBlocked"
    assert payload["Data"]["MinutesEarly"] == 60


def test_planner_workbench_release_endpoint_allows_release_at_rope_date():
    client = TestClient(create_app())

    response = client.post(
        "/planner/workbench/release",
        json={
            **_calculate_payload(),
            "OrderID": "WO-1",
            "RequestedReleaseAt": "2026-06-20T06:00:00+00:00",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["Data"]["Allowed"] is True
    assert payload["Data"]["Status"] == "ReleaseAllowed"
    assert payload["Data"]["Stability"] == {
        "DeviationMinutes": 0,
        "AbsoluteDeviationMinutes": 0,
        "TimingStatus": "OnTime",
        "Severity": "Normal",
        "Action": "Monitor",
        "ReplanRequired": False,
        "ReasonCode": "WithinTolerance",
        "ConsecutiveBlockedCount": 0,
    }


def test_planner_workbench_release_endpoint_blocks_when_material_release_penetrates_red_zone():
    client = TestClient(create_app())
    request_payload = _calculate_payload()
    request_payload["InventoryBuffers"][0]["OnHandQty"] = 55
    request_payload["MaterialRequirements"] = [
        {
            "OrderID": "WO-1",
            "ItemID": "RM-STEEL",
            "LocationID": "SUPPLIER-DECOUPLING",
            "RequiredQty": 10,
        }
    ]

    response = client.post(
        "/planner/workbench/release",
        json={
            **request_payload,
            "OrderID": "WO-1",
            "RequestedReleaseAt": "2026-06-20T06:00:00+00:00",
        },
    )

    assert response.status_code == 409
    payload = response.json()
    assert payload["Data"]["Allowed"] is False
    assert payload["Data"]["Status"] == "ReleaseBlockedByInventoryBuffer"
    assert payload["Data"]["InventoryRisks"] == [
        {
            "OrderID": "WO-1",
            "ItemID": "RM-STEEL",
            "LocationID": "SUPPLIER-DECOUPLING",
            "RequiredQty": 10.0,
            "OnHandQty": 55.0,
            "ProjectedOnHandQty": 45.0,
            "RedZoneQty": 50.0,
            "Message": (
                "Releasing order WO-1 would project RM-STEEL at "
                "SUPPLIER-DECOUPLING below the red zone."
            ),
        }
    ]


def test_planner_workbench_release_endpoint_allows_when_material_remains_above_red_zone():
    client = TestClient(create_app())
    request_payload = _calculate_payload()
    request_payload["InventoryBuffers"][0]["OnHandQty"] = 80
    request_payload["MaterialRequirements"] = [
        {
            "OrderID": "WO-1",
            "ItemID": "RM-STEEL",
            "LocationID": "SUPPLIER-DECOUPLING",
            "RequiredQty": 10,
        }
    ]

    response = client.post(
        "/planner/workbench/release",
        json={
            **request_payload,
            "OrderID": "WO-1",
            "RequestedReleaseAt": "2026-06-20T06:00:00+00:00",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["Data"]["Allowed"] is True
    assert payload["Data"]["Status"] == "ReleaseAllowed"
    assert payload["Data"]["InventoryRisks"] == []


def test_release_endpoint_stability_replans_after_third_inventory_block():
    client = TestClient(create_app())
    request_payload = _calculate_payload()
    request_payload["InventoryBuffers"][0]["OnHandQty"] = 55
    request_payload["MaterialRequirements"] = [
        {
            "OrderID": "WO-1",
            "ItemID": "RM-STEEL",
            "LocationID": "SUPPLIER-DECOUPLING",
            "RequiredQty": 10,
        }
    ]

    response = client.post(
        "/planner/workbench/release",
        json={
            **request_payload,
            "OrderID": "WO-1",
            "RequestedReleaseAt": "2026-06-20T06:00:00+00:00",
            "PreviousConsecutiveBlockedCount": 2,
        },
    )

    assert response.status_code == 409
    stability = response.json()["Data"]["Stability"]
    assert stability["ConsecutiveBlockedCount"] == 3
    assert stability["Action"] == "Replan"
    assert stability["ReplanRequired"] is True
    assert stability["ReasonCode"] == "ConsecutiveGateBlocks"


def test_release_endpoint_stability_resets_block_count_when_release_is_allowed():
    client = TestClient(create_app())

    response = client.post(
        "/planner/workbench/release",
        json={
            **_calculate_payload(),
            "OrderID": "WO-1",
            "RequestedReleaseAt": "2026-06-20T06:00:00+00:00",
            "PreviousConsecutiveBlockedCount": 2,
        },
    )

    assert response.status_code == 200
    stability = response.json()["Data"]["Stability"]
    assert stability["ConsecutiveBlockedCount"] == 0
    assert stability["Action"] == "Monitor"


def test_release_endpoint_stability_suppresses_replan_during_cooldown():
    client = TestClient(create_app())
    request_payload = _calculate_payload()
    request_payload["InventoryBuffers"][0]["OnHandQty"] = 55
    request_payload["MaterialRequirements"] = [
        {
            "OrderID": "WO-1",
            "ItemID": "RM-STEEL",
            "LocationID": "SUPPLIER-DECOUPLING",
            "RequiredQty": 10,
        }
    ]

    response = client.post(
        "/planner/workbench/release",
        json={
            **request_payload,
            "OrderID": "WO-1",
            "RequestedReleaseAt": "2026-06-20T06:00:00+00:00",
            "PreviousConsecutiveBlockedCount": 2,
            "LastReplanAt": "2026-06-20T05:30:00+00:00",
        },
    )

    assert response.status_code == 409
    stability = response.json()["Data"]["Stability"]
    assert stability["ConsecutiveBlockedCount"] == 3
    assert stability["Action"] == "Review"
    assert stability["ReplanRequired"] is False
    assert stability["ReasonCode"] == "ReplanCooldownActive"


def test_release_endpoint_returns_no_replan_request_when_not_required():
    client = TestClient(create_app())

    response = client.post(
        "/planner/workbench/release",
        json={
            **_calculate_payload(),
            "OrderID": "WO-1",
            "RequestedReleaseAt": "2026-06-20T06:00:00+00:00",
        },
    )

    assert response.status_code == 200
    assert response.json()["Data"]["ReplanRequest"] is None


def test_replan_request_queue_deduplicates_repeated_release_trigger():
    client = TestClient(create_app())
    request_payload = _calculate_payload()
    request_payload["InventoryBuffers"][0]["OnHandQty"] = 55
    request_payload["MaterialRequirements"] = [
        {
            "OrderID": "WO-1",
            "ItemID": "RM-STEEL",
            "LocationID": "SUPPLIER-DECOUPLING",
            "RequiredQty": 10,
        }
    ]
    release_payload = {
        **request_payload,
        "OrderID": "WO-1",
        "RequestedReleaseAt": "2026-06-20T06:00:00+00:00",
        "PreviousConsecutiveBlockedCount": 2,
    }

    first = client.post("/planner/workbench/release", json=release_payload)
    repeated = client.post("/planner/workbench/release", json=release_payload)
    queue = client.get("/planner/workbench/replan-requests")

    assert first.status_code == 409
    assert repeated.status_code == 409
    first_request = first.json()["Data"]["ReplanRequest"]
    assert first_request["ProblemID"] == "P-CALC"
    assert first_request["OrderID"] == "WO-1"
    assert first_request["Status"] == "PendingReview"
    assert first_request["Source"] == "ReleaseStability"
    assert repeated.json()["Data"]["ReplanRequest"]["RequestID"] == first_request["RequestID"]
    assert queue.status_code == 200
    assert queue.json()["Data"] == {
        "Count": 1,
        "Requests": [first_request],
    }


def test_replan_request_decision_approves_pending_request():
    client = TestClient(create_app())
    request_id = _trigger_replan_request(client)["RequestID"]

    response = client.post(
        f"/planner/workbench/replan-requests/{request_id}/decision",
        json={
            "Decision": "Approve",
            "DecidedBy": "planner-1",
            "DecidedAt": "2026-06-20T07:00:00+00:00",
            "Comment": "Capacity and material risks reviewed.",
        },
    )

    assert response.status_code == 200
    request = response.json()["Data"]["Request"]
    assert request["Status"] == "Approved"
    assert request["DecidedBy"] == "planner-1"
    assert request["DecidedAt"] == "2026-06-20T07:00:00+00:00"
    assert request["DecisionComment"] == "Capacity and material risks reviewed."
    queue_request = client.get(
        "/planner/workbench/replan-requests"
    ).json()["Data"]["Requests"][0]
    assert queue_request == request


def test_replan_request_decision_returns_not_found_for_unknown_request():
    client = TestClient(create_app())

    response = client.post(
        "/planner/workbench/replan-requests/RPL-MISSING/decision",
        json={
            "Decision": "Approve",
            "DecidedBy": "planner-1",
            "DecidedAt": "2026-06-20T07:00:00+00:00",
        },
    )

    assert response.status_code == 404
    assert response.json()["Data"]["Status"] == "ReplanRequestNotFound"


def test_replan_request_decision_reject_requires_comment():
    client = TestClient(create_app())
    request_id = _trigger_replan_request(client)["RequestID"]

    response = client.post(
        f"/planner/workbench/replan-requests/{request_id}/decision",
        json={
            "Decision": "Reject",
            "DecidedBy": "planner-1",
            "DecidedAt": "2026-06-20T07:00:00+00:00",
        },
    )

    assert response.status_code == 409
    assert response.json()["Data"]["Status"] == "ReplanDecisionConflict"
    assert response.json()["Data"]["Message"] == "Reject decision requires a comment"


def test_replan_request_decision_rejects_second_decision():
    client = TestClient(create_app())
    request_id = _trigger_replan_request(client)["RequestID"]
    decision_url = f"/planner/workbench/replan-requests/{request_id}/decision"
    client.post(
        decision_url,
        json={
            "Decision": "Approve",
            "DecidedBy": "planner-1",
            "DecidedAt": "2026-06-20T07:00:00+00:00",
        },
    )

    response = client.post(
        decision_url,
        json={
            "Decision": "Reject",
            "DecidedBy": "planner-2",
            "DecidedAt": "2026-06-20T08:00:00+00:00",
            "Comment": "Changed decision.",
        },
    )

    assert response.status_code == 409
    assert response.json()["Data"]["Message"] == (
        "Only PendingReview requests can be decided"
    )


def test_replan_execution_rejects_request_that_is_not_approved():
    client = TestClient(create_app())
    request_id = _trigger_replan_request(client)["RequestID"]
    execution_payload = _calculate_payload()
    execution_payload["SolverBackendID"] = "gurobi"

    response = client.post(
        f"/planner/workbench/replan-requests/{request_id}/execute",
        json=execution_payload,
    )

    assert response.status_code == 409
    assert response.json()["Data"]["Status"] == "ReplanExecutionConflict"
    assert response.json()["Data"]["Message"] == (
        "Only Approved requests can be executed"
    )


def test_replan_execution_rejects_snapshot_problem_mismatch():
    client = TestClient(create_app())
    request_id = _approve_replan_request(client)["RequestID"]
    execution_payload = _calculate_payload()
    execution_payload["ProblemID"] = "P-OTHER"
    execution_payload["SolverBackendID"] = "gurobi"

    response = client.post(
        f"/planner/workbench/replan-requests/{request_id}/execute",
        json=execution_payload,
    )

    assert response.status_code == 409
    assert response.json()["Data"]["Status"] == "ReplanProblemMismatch"


def test_replan_execution_rejects_paused_gurobi_backend():
    client = TestClient(create_app())
    request_id = _approve_replan_request(client)["RequestID"]

    execution_payload = _calculate_payload()
    execution_payload["SolverBackendID"] = "gurobi"
    response = client.post(
        f"/planner/workbench/replan-requests/{request_id}/execute",
        json=execution_payload,
    )

    assert response.status_code == 409
    assert response.json()["Data"]["Status"] == "ReplanBackendRejected"


def test_replan_execution_invalid_master_data_keeps_request_approved():
    client = TestClient(create_app(), raise_server_exceptions=False)
    request_id = _approve_replan_request(client)["RequestID"]
    execution_payload = _calculate_payload()
    execution_payload["SolverBackendID"] = "ortools"
    execution_payload["Orders"][0]["ProductID"] = "FG-MISSING"

    response = client.post(
        f"/planner/workbench/replan-requests/{request_id}/execute",
        json=execution_payload,
    )

    assert response.status_code == 409
    assert response.json()["Data"]["Status"] == "ReplanMasterDataInvalid"
    queue_request = client.get(
        "/planner/workbench/replan-requests"
    ).json()["Data"]["Requests"][0]
    assert queue_request["Status"] == "Approved"


def test_replan_execution_runs_cp_sat_and_records_solver_outcome():
    client = TestClient(create_app())
    request_id = _approve_replan_request(client)["RequestID"]
    execution_payload = _calculate_payload()
    execution_payload["SolverBackendID"] = "ortools"

    response = client.post(
        f"/planner/workbench/replan-requests/{request_id}/execute",
        json=execution_payload,
    )

    assert response.status_code == 200
    data = response.json()["Data"]
    assert data["Schedule"]["SolverBackendID"] == "ortools"
    solver_status = data["Schedule"]["SolverStatus"]
    expected_request_status = (
        "Completed" if solver_status in {"Optimal", "Feasible"} else "Failed"
    )
    assert data["Request"]["Status"] == expected_request_status
    assert data["Request"]["SolverStatus"] == solver_status
    assert data["Request"]["ExecutionStartedAt"] is not None
    assert data["Request"]["ExecutionCompletedAt"] is not None
    queue_request = client.get(
        "/planner/workbench/replan-requests"
    ).json()["Data"]["Requests"][0]
    assert queue_request == data["Request"]


def test_replan_execution_preserves_locked_orders_from_latest_completed_plan():
    client = TestClient(create_app())
    master_data_payload = _master_data_import_calculate_payload()
    master_data_payload.pop("ProblemID")
    master_data_payload.pop("ScheduleStartAt")
    master_data_payload.update(
        {
            "VersionID": "MDV-LOCKED-REPLAN",
            "CapturedAt": "2026-06-16T07:30:00+00:00",
            "SourceSystem": "ERP",
            "CreatedBy": "planner-1",
        }
    )
    assert client.post(
        "/planner/workbench/master-data/versions",
        json=master_data_payload,
    ).status_code == 200
    assert client.post(
        "/planner/workbench/operational-state/snapshots",
        json={
            "SnapshotID": "OPS-LOCKED-REPLAN",
            "CapturedAt": "2026-06-16T07:45:00+00:00",
        },
    ).status_code == 200
    assert client.post(
        "/planner/workbench/planning-runs",
        json={
            "RunID": "RUN-LOCKED-SOURCE",
            "ProblemID": "P-CALC",
            "MasterDataVersionID": "MDV-LOCKED-REPLAN",
            "OperationalStateSnapshotID": "OPS-LOCKED-REPLAN",
            "ScheduleStartAt": "2026-06-16T08:00:00+00:00",
            "SolverBackendID": "ortools",
            "RequestedBy": "planner-1",
            "RequestedAt": "2026-06-16T07:50:00+00:00",
        },
    ).status_code == 200
    source_run = client.post(
        "/planner/workbench/planning-runs/RUN-LOCKED-SOURCE/execute",
        json={
            "ExecutedBy": "planner-1",
            "StartedAt": "2026-06-16T07:55:00+00:00",
            "CompletedAt": "2026-06-16T07:56:00+00:00",
        },
    ).json()["Data"]["PlanningRun"]
    source_gantt_row = source_run["Schedule"]["GanttRows"][0]
    source_operation = source_gantt_row["Bars"][0]
    assert client.post(
        (
            "/planner/workbench/schedule-results/runs/RUN-LOCKED-SOURCE"
            "/work-orders/commands"
        ),
        json={
            "Command": "Lock",
            "OrderIDs": ["WO-1"],
            "ActorID": "planner-1",
            "OccurredAt": "2026-06-16T08:05:00+00:00",
        },
    ).status_code == 200

    request_id = _approve_replan_request(client)["RequestID"]
    execution_payload = _calculate_payload()
    execution_payload["SolverBackendID"] = "ortools"
    response = client.post(
        f"/planner/workbench/replan-requests/{request_id}/execute",
        json=execution_payload,
    )

    assert response.status_code == 200
    schedule = response.json()["Data"]["Schedule"]
    assert schedule["FixedAssignments"] == [
        {
            "OperationID": source_operation["OperationID"],
            "ResourceID": source_gantt_row["ResourceID"],
            "StartAt": source_operation["Start"],
        }
    ]
    replan_gantt_row = schedule["GanttRows"][0]
    replan_operation = schedule["GanttRows"][0]["Bars"][0]
    assert replan_operation["OperationID"] == source_operation["OperationID"]
    assert replan_operation["Start"] == source_operation["Start"]
    assert replan_gantt_row["ResourceID"] == source_gantt_row["ResourceID"]


def test_replan_execution_preserves_operations_inside_freeze_window():
    client = TestClient(create_app())
    master_data_payload = _master_data_import_calculate_payload()
    master_data_payload.pop("ProblemID")
    master_data_payload.pop("ScheduleStartAt")
    master_data_payload.update(
        {
            "VersionID": "MDV-FREEZE-REPLAN",
            "CapturedAt": "2026-06-16T07:30:00+00:00",
            "SourceSystem": "ERP",
            "CreatedBy": "planner-1",
        }
    )
    assert client.post(
        "/planner/workbench/master-data/versions",
        json=master_data_payload,
    ).status_code == 200
    assert client.post(
        "/planner/workbench/operational-state/snapshots",
        json={
            "SnapshotID": "OPS-FREEZE-REPLAN",
            "CapturedAt": "2026-06-16T07:45:00+00:00",
        },
    ).status_code == 200
    assert client.post(
        "/planner/workbench/planning-runs",
        json={
            "RunID": "RUN-FREEZE-SOURCE",
            "ProblemID": "P-CALC",
            "MasterDataVersionID": "MDV-FREEZE-REPLAN",
            "OperationalStateSnapshotID": "OPS-FREEZE-REPLAN",
            "ScheduleStartAt": "2026-06-16T08:00:00+00:00",
            "SolverBackendID": "ortools",
            "RequestedBy": "planner-1",
            "RequestedAt": "2026-06-16T07:50:00+00:00",
        },
    ).status_code == 200
    source_run = client.post(
        "/planner/workbench/planning-runs/RUN-FREEZE-SOURCE/execute",
        json={
            "ExecutedBy": "planner-1",
            "StartedAt": "2026-06-16T07:55:00+00:00",
            "CompletedAt": "2026-06-16T07:56:00+00:00",
        },
    ).json()["Data"]["PlanningRun"]
    source_gantt_row = source_run["Schedule"]["GanttRows"][0]
    source_operation = source_gantt_row["Bars"][0]

    request_id = _approve_replan_request(client)["RequestID"]
    execution_payload = _calculate_payload()
    execution_payload["SolverBackendID"] = "ortools"
    execution_payload["FreezeWindowMinutes"] = 60
    response = client.post(
        f"/planner/workbench/replan-requests/{request_id}/execute",
        json=execution_payload,
    )

    assert response.status_code == 200
    schedule = response.json()["Data"]["Schedule"]
    assert schedule["FixedAssignments"] == [
        {
            "OperationID": source_operation["OperationID"],
            "ResourceID": source_gantt_row["ResourceID"],
            "StartAt": source_operation["Start"],
        }
    ]
    replan_gantt_row = schedule["GanttRows"][0]
    replan_operation = replan_gantt_row["Bars"][0]
    assert replan_operation["OperationID"] == source_operation["OperationID"]
    assert replan_operation["Start"] == source_operation["Start"]
    assert replan_gantt_row["ResourceID"] == source_gantt_row["ResourceID"]


def test_be_solver_012_replan_execution_returns_source_trace_and_diff():
    # BE-SOLVER-012
    client = TestClient(create_app())
    master_data_payload = _master_data_import_calculate_payload()
    master_data_payload.pop("ProblemID")
    master_data_payload.pop("ScheduleStartAt")
    master_data_payload.update(
        {
            "VersionID": "MDV-REPLAN-DIFF",
            "CapturedAt": "2026-06-16T07:30:00+00:00",
            "CreatedBy": "planner-1",
        }
    )
    assert client.post(
        "/planner/workbench/master-data/versions", json=master_data_payload
    ).status_code == 200
    assert client.post(
        "/planner/workbench/operational-state/snapshots",
        json={
            "SnapshotID": "OPS-REPLAN-DIFF",
            "CapturedAt": "2026-06-16T07:45:00+00:00",
        },
    ).status_code == 200
    _create_and_execute_planning_run(
        client,
        run_id="RUN-REPLAN-DIFF-SOURCE",
        master_data_version_id="MDV-REPLAN-DIFF",
        snapshot_id="OPS-REPLAN-DIFF",
        problem_id="P-CALC",
    )

    request_id = _approve_replan_request(client)["RequestID"]
    execution_payload = _calculate_payload()
    execution_payload["SolverBackendID"] = "ortools"
    execution_payload["SourceRunID"] = "RUN-REPLAN-DIFF-SOURCE"
    response = client.post(
        f"/planner/workbench/replan-requests/{request_id}/execute",
        json=execution_payload,
    )

    assert response.status_code == 200
    schedule = response.json()["Data"]["Schedule"]
    assert schedule["SourceRunID"] == "RUN-REPLAN-DIFF-SOURCE"
    assert schedule["ReplanTrace"]["SourceRunID"] == "RUN-REPLAN-DIFF-SOURCE"
    assert schedule["ReplanDiff"]["Summary"]["AddedCount"] == 0
    assert schedule["ReplanDiff"]["Operations"][0]["OperationID"] == "WO-1:CUT"


def test_scheduled_work_orders_returns_completed_replan_operations():
    client = TestClient(create_app())
    request_id = _approve_replan_request(client)["RequestID"]
    execution_payload = _calculate_payload()
    execution_payload["SolverBackendID"] = "ortools"
    execution = client.post(
        f"/planner/workbench/replan-requests/{request_id}/execute",
        json=execution_payload,
    ).json()["Data"]

    response = client.get(
        f"/planner/workbench/replan-requests/{request_id}/scheduled-work-orders"
    )

    if execution["Request"]["Status"] != "Completed":
        assert response.status_code == 409
        assert response.json()["Data"]["Status"] == "ScheduledWorkOrdersUnavailable"
        return
    assert response.status_code == 200
    payload = response.json()
    assert payload["Data"]["RequestID"] == request_id
    assert payload["Data"]["SolverStatus"] in {"Optimal", "Feasible"}
    assert payload["Data"]["Operations"]
    first_operation = payload["Data"]["Operations"][0]
    assert set(first_operation) == {
        "OrderID",
        "OperationID",
        "ResourceID",
        "Start",
        "End",
        "DurationMinutes",
    }


def test_scheduled_orders_returns_completed_replan_order_rows():
    client = TestClient(create_app())
    request_id = _approve_replan_request(client)["RequestID"]
    execution_payload = _calculate_payload()
    execution_payload["SolverBackendID"] = "ortools"
    execution = client.post(
        f"/planner/workbench/replan-requests/{request_id}/execute",
        json=execution_payload,
    ).json()["Data"]

    response = client.get(
        f"/planner/workbench/replan-requests/{request_id}/scheduled-orders"
    )

    if execution["Request"]["Status"] != "Completed":
        assert response.status_code == 409
        assert response.json()["Data"]["Status"] == "ScheduledOrdersUnavailable"
        return
    assert response.status_code == 200
    payload = response.json()
    assert payload["Data"]["RequestID"] == request_id
    assert payload["Data"]["SolverStatus"] in {"Optimal", "Feasible"}
    assert payload["Data"]["Orders"] == [
        {
            "OrderID": "WO-1",
            "ScheduledStart": "2026-06-16T08:00:00+00:00",
            "ScheduledEnd": "2026-06-16T10:00:00+00:00",
            "FirstOperationID": "WO-1:CUT",
            "FirstResourceID": "WC-DRUM",
            "LastOperationID": "WO-1:CUT",
            "LastResourceID": "WC-DRUM",
            "OperationCount": 1,
            "TotalDurationMinutes": 120,
            "ResourceIDs": ["WC-DRUM"],
        }
    ]


def test_scheduled_work_orders_returns_not_found_for_unknown_request():
    client = TestClient(create_app())

    response = client.get(
        "/planner/workbench/replan-requests/RPL-MISSING/scheduled-work-orders"
    )

    assert response.status_code == 404
    assert response.json()["Data"]["Status"] == "ReplanRequestNotFound"


def test_scheduled_work_orders_rejects_request_without_completed_output():
    client = TestClient(create_app())
    request_id = _trigger_replan_request(client)["RequestID"]

    response = client.get(
        f"/planner/workbench/replan-requests/{request_id}/scheduled-work-orders"
    )

    assert response.status_code == 409
    assert response.json()["Data"]["Status"] == "ScheduledWorkOrdersUnavailable"


def test_scheduled_orders_returns_not_found_for_unknown_request():
    client = TestClient(create_app())

    response = client.get(
        "/planner/workbench/replan-requests/RPL-MISSING/scheduled-orders"
    )

    assert response.status_code == 404
    assert response.json()["Data"]["Status"] == "ReplanRequestNotFound"


def test_scheduled_orders_rejects_request_without_completed_output():
    client = TestClient(create_app())
    request_id = _trigger_replan_request(client)["RequestID"]

    response = client.get(
        f"/planner/workbench/replan-requests/{request_id}/scheduled-orders"
    )

    assert response.status_code == 409
    assert response.json()["Data"]["Status"] == "ScheduledOrdersUnavailable"


def test_release_candidates_return_completed_replan_release_readiness():
    client = TestClient(create_app())
    request_id = _approve_replan_request(client)["RequestID"]
    execution_payload = _calculate_payload()
    execution_payload["SolverBackendID"] = "ortools"
    execution = client.post(
        f"/planner/workbench/replan-requests/{request_id}/execute",
        json=execution_payload,
    ).json()["Data"]

    response = client.post(
        f"/planner/workbench/replan-requests/{request_id}/release-candidates",
        json={
            "EvaluatedAt": "2026-06-20T06:00:00+00:00",
            "InventoryBuffers": [
                {
                    "ItemID": "RM-STEEL",
                    "LocationID": "SUPPLIER-DECOUPLING",
                    "OnHandQty": 80,
                    "RedZoneQty": 50,
                    "YellowZoneQty": 120,
                    "GreenZoneQty": 200,
                }
            ],
            "MaterialRequirements": [
                {
                    "OrderID": "WO-1",
                    "ItemID": "RM-STEEL",
                    "LocationID": "SUPPLIER-DECOUPLING",
                    "RequiredQty": 10,
                }
            ],
            "WipLimits": [
                {
                    "ScopeID": "DRUM-FEED",
                    "CurrentWipCount": 0,
                    "MaxWipCount": 5,
                }
            ],
        },
    )

    if execution["Request"]["Status"] != "Completed":
        assert response.status_code == 409
        assert response.json()["Data"]["Status"] == "ReleaseCandidatesUnavailable"
        return
    assert response.status_code == 200
    payload = response.json()
    assert payload["Data"]["RequestID"] == request_id
    assert payload["Data"]["Candidates"] == [
        {
            "OrderID": "WO-1",
            "ScheduledStart": "2026-06-16T08:00:00+00:00",
            "ScheduledEnd": "2026-06-16T10:00:00+00:00",
            "SuggestedReleaseAt": "2026-06-20T06:00:00+00:00",
            "EvaluatedAt": "2026-06-20T06:00:00+00:00",
            "RopeStatus": "Ready",
            "MinutesUntilRelease": 0,
            "MaterialStatus": "Clear",
            "InventoryRisks": [],
            "WipStatus": "Clear",
            "WipRisks": [],
            "RecommendedAction": "ReadyForRelease",
        }
    ]


def test_release_candidates_consume_operational_state_snapshot():
    client = TestClient(create_app())
    snapshot_response = client.post(
        "/planner/workbench/operational-state/snapshots",
        json={
            "SnapshotID": "OPS-20260620-0600",
            "CapturedAt": "2026-06-20T06:00:00+00:00",
            "InventoryBuffers": [
                {
                    "ItemID": "RM-STEEL",
                    "LocationID": "SUPPLIER-DECOUPLING",
                    "OnHandQty": 80,
                    "RedZoneQty": 50,
                    "YellowZoneQty": 120,
                    "GreenZoneQty": 200,
                }
            ],
            "WipLimits": [
                {
                    "ScopeID": "DRUM-FEED",
                    "CurrentWipCount": 0,
                    "MaxWipCount": 5,
                }
            ],
        },
    )
    assert snapshot_response.status_code == 200

    request_id = _completed_replan_request_id(client)
    response = client.post(
        f"/planner/workbench/replan-requests/{request_id}/release-candidates",
        json={
            "EvaluatedAt": "2026-06-20T06:00:00+00:00",
            "OperationalStateSnapshotID": "OPS-20260620-0600",
            "MaterialRequirements": [
                {
                    "OrderID": "WO-1",
                    "ItemID": "RM-STEEL",
                    "LocationID": "SUPPLIER-DECOUPLING",
                    "RequiredQty": 10,
                }
            ],
        },
    )

    assert response.status_code == 200
    data = response.json()["Data"]
    assert data["OperationalStateSnapshotID"] == "OPS-20260620-0600"
    assert data["OperationalStateCapturedAt"] == "2026-06-20T06:00:00+00:00"
    assert data["Candidates"][0]["RecommendedAction"] == "ReadyForRelease"


def test_release_candidates_reject_unknown_operational_state_snapshot():
    client = TestClient(create_app())
    request_id = _completed_replan_request_id(client)

    response = client.post(
        f"/planner/workbench/replan-requests/{request_id}/release-candidates",
        json={
            "EvaluatedAt": "2026-06-20T06:00:00+00:00",
            "OperationalStateSnapshotID": "OPS-MISSING",
        },
    )

    assert response.status_code == 404
    assert response.json()["Data"]["Status"] == "OperationalStateSnapshotNotFound"


def test_release_decision_package_is_idempotent_and_retrievable():
    client = TestClient(create_app())
    snapshot_response = client.post(
        "/planner/workbench/operational-state/snapshots",
        json={
            "SnapshotID": "OPS-DECISION-1",
            "CapturedAt": "2026-06-20T06:00:00+00:00",
            "InventoryBuffers": [
                {
                    "ItemID": "RM-STEEL",
                    "LocationID": "SUPPLIER-DECOUPLING",
                    "OnHandQty": 80,
                    "RedZoneQty": 50,
                    "YellowZoneQty": 120,
                    "GreenZoneQty": 200,
                }
            ],
        },
    )
    assert snapshot_response.status_code == 200
    request_id = _completed_replan_request_id(client)
    payload = {
        "EvaluatedAt": "2026-06-20T06:00:00+00:00",
        "OperationalStateSnapshotID": "OPS-DECISION-1",
        "MaterialRequirements": [
            {
                "OrderID": "WO-1",
                "ItemID": "RM-STEEL",
                "LocationID": "SUPPLIER-DECOUPLING",
                "RequiredQty": 10,
            }
        ],
    }

    first = client.post(
        f"/planner/workbench/replan-requests/{request_id}/release-decision-packages",
        json=payload,
    )
    second = client.post(
        f"/planner/workbench/replan-requests/{request_id}/release-decision-packages",
        json=payload,
    )

    assert first.status_code == 200
    assert second.status_code == 200
    package = first.json()["Data"]["DecisionPackage"]
    assert second.json()["Data"]["DecisionPackage"] == package
    assert package["DecisionPackageID"].startswith("RDP-")
    assert package["ScheduleSnapshotID"].startswith("SCH-")
    assert package["RequestID"] == request_id
    assert package["OperationalStateSnapshotID"] == "OPS-DECISION-1"
    assert package["OperationalStateCapturedAt"] == "2026-06-20T06:00:00+00:00"
    assert package["Candidates"][0]["RecommendedAction"] == "ReadyForRelease"
    assert package["MaterialRequirements"] == payload["MaterialRequirements"]

    retrieved = client.get(
        f"/planner/workbench/release-decision-packages/{package['DecisionPackageID']}"
    )
    assert retrieved.status_code == 200
    assert retrieved.json()["Data"]["DecisionPackage"] == package


def test_release_authorization_consumes_frozen_decision_package():
    client = TestClient(create_app())
    request_id = _completed_replan_request_id(client)
    decision_package = _create_release_decision_package(client, request_id)

    response = client.post(
        f"/planner/workbench/replan-requests/{request_id}/release-authorizations",
        json={
            "OrderID": "WO-1",
            "ReleasedBy": "planner-1",
            "ReleasedAt": "2026-06-20T06:05:00+00:00",
            "EvaluatedAt": "2026-06-20T06:00:00+00:00",
            "DecisionPackageID": decision_package["DecisionPackageID"],
        },
    )

    assert response.status_code == 200
    authorization = response.json()["Data"]["Authorization"]
    assert authorization["DecisionPackageID"] == decision_package["DecisionPackageID"]
    assert authorization["OperationalStateSnapshotID"] == "OPS-AUTH-PACKAGE"
    assert authorization["OperationalStateCapturedAt"] == "2026-06-20T06:00:00+00:00"

    dispatch = client.get(
        f"/planner/workbench/release-authorizations/{authorization['AuthorizationID']}/dispatch-package"
    )
    assert dispatch.status_code == 200
    dispatch_package = dispatch.json()["Data"]["DispatchPackage"]
    assert dispatch_package["DecisionPackageID"] == decision_package["DecisionPackageID"]


def test_release_decision_package_reports_linked_authorizations():
    client = TestClient(create_app())
    request_id = _completed_replan_request_id(client)
    decision_package = _create_release_decision_package(client, request_id)
    package_id = decision_package["DecisionPackageID"]

    before = client.get(
        f"/planner/workbench/release-decision-packages/{package_id}/authorizations"
    )
    assert before.status_code == 200
    assert before.json()["Data"] == {
        "DecisionPackageID": package_id,
        "AuthorizationStatus": "NotAuthorized",
        "AuthorizationCount": 0,
        "Authorizations": [],
    }

    authorization_response = client.post(
        f"/planner/workbench/replan-requests/{request_id}/release-authorizations",
        json={
            "OrderID": "WO-1",
            "ReleasedBy": "planner-1",
            "ReleasedAt": "2026-06-20T06:05:00+00:00",
            "EvaluatedAt": "2026-06-20T06:00:00+00:00",
            "DecisionPackageID": package_id,
        },
    )
    assert authorization_response.status_code == 200
    authorization = authorization_response.json()["Data"]["Authorization"]

    after = client.get(
        f"/planner/workbench/release-decision-packages/{package_id}/authorizations"
    )
    assert after.status_code == 200
    data = after.json()["Data"]
    assert data["AuthorizationStatus"] == "Authorized"
    assert data["AuthorizationCount"] == 1
    assert data["Authorizations"] == [authorization]


def test_release_decision_package_execution_trace_reaches_shop_floor_events():
    client = TestClient(create_app())
    request_id = _completed_replan_request_id(client)
    decision_package = _create_release_decision_package(client, request_id)
    package_id = decision_package["DecisionPackageID"]
    authorization_response = client.post(
        f"/planner/workbench/replan-requests/{request_id}/release-authorizations",
        json={
            "OrderID": "WO-1",
            "ReleasedBy": "planner-1",
            "ReleasedAt": "2026-06-20T06:05:00+00:00",
            "EvaluatedAt": "2026-06-20T06:00:00+00:00",
            "DecisionPackageID": package_id,
        },
    )
    assert authorization_response.status_code == 200
    authorization = authorization_response.json()["Data"]["Authorization"]
    event_response = client.post(
        "/shop-floor/execution/event",
        json={
            "AuthorizationID": authorization["AuthorizationID"],
            "OrderID": "WO-1",
            "EventType": "StartedOperation",
            "EventAt": "2026-06-16T08:05:00+00:00",
            "TargetStartAt": "2026-06-16T08:00:00+00:00",
        },
    )
    assert event_response.status_code == 200

    response = client.get(
        f"/planner/workbench/release-decision-packages/{package_id}/execution-trace"
    )

    assert response.status_code == 200
    data = response.json()["Data"]
    assert data["DecisionPackageID"] == package_id
    assert data["OverallExecutionStatus"] == "InProcess"
    assert data["AuthorizationCount"] == 1
    assert len(data["Rows"]) == 1
    row = data["Rows"][0]
    assert row["AuthorizationID"] == authorization["AuthorizationID"]
    assert row["OrderID"] == "WO-1"
    assert row["ExecutionStatus"] == "InProcess"
    assert row["Events"][0]["EventType"] == "StartedOperation"
    assert row["Events"][0]["AuthorizationID"] == authorization["AuthorizationID"]


def test_release_decision_package_reports_schedule_execution_variance():
    client = TestClient(create_app())
    request_id = _completed_replan_request_id(client)
    decision_package = _create_release_decision_package(client, request_id)
    package_id = decision_package["DecisionPackageID"]
    authorization_response = client.post(
        f"/planner/workbench/replan-requests/{request_id}/release-authorizations",
        json={
            "OrderID": "WO-1",
            "ReleasedBy": "planner-1",
            "ReleasedAt": "2026-06-20T06:05:00+00:00",
            "EvaluatedAt": "2026-06-20T06:00:00+00:00",
            "DecisionPackageID": package_id,
        },
    )
    assert authorization_response.status_code == 200
    authorization_id = authorization_response.json()["Data"]["Authorization"][
        "AuthorizationID"
    ]
    for event_type, event_at in (
        ("StartedOperation", "2026-06-16T08:05:00+00:00"),
        ("CompletedOperation", "2026-06-16T10:20:00+00:00"),
    ):
        event_response = client.post(
            "/shop-floor/execution/event",
            json={
                "AuthorizationID": authorization_id,
                "OrderID": "WO-1",
                "EventType": event_type,
                "EventAt": event_at,
                "TargetStartAt": "2026-06-16T08:00:00+00:00",
            },
        )
        assert event_response.status_code == 200

    response = client.get(
        f"/planner/workbench/release-decision-packages/{package_id}/execution-variance"
    )

    assert response.status_code == 200
    data = response.json()["Data"]
    assert data["DecisionPackageID"] == package_id
    assert data["VarianceStatus"] == "Late"
    assert data["Summary"] == {
        "OrderCount": 1,
        "StartedCount": 1,
        "CompletedCount": 1,
        "PendingStartCount": 0,
        "PendingCompletionCount": 0,
        "StartLateCount": 1,
        "CompletionLateCount": 1,
        "MaxAbsoluteDeviationMinutes": 20,
    }
    row = data["Rows"][0]
    assert row["AuthorizationID"] == authorization_id
    assert row["PlannedStartAt"] == "2026-06-16T08:00:00+00:00"
    assert row["ActualStartAt"] == "2026-06-16T08:05:00+00:00"
    assert row["StartDeviationMinutes"] == 5
    assert row["StartTimingStatus"] == "Late"
    assert row["PlannedCompletionAt"] == "2026-06-16T10:00:00+00:00"
    assert row["ActualCompletionAt"] == "2026-06-16T10:20:00+00:00"
    assert row["CompletionDeviationMinutes"] == 20
    assert row["CompletionTimingStatus"] == "Late"
    assert row["CompletionBasis"] == "CompletedOperation"


def test_execution_variance_stability_suppresses_replan_during_cooldown():
    client = TestClient(create_app())
    request_id = _completed_replan_request_id(client)
    decision_package = _create_release_decision_package(client, request_id)
    package_id = decision_package["DecisionPackageID"]
    authorization_response = client.post(
        f"/planner/workbench/replan-requests/{request_id}/release-authorizations",
        json={
            "OrderID": "WO-1",
            "ReleasedBy": "planner-1",
            "ReleasedAt": "2026-06-20T06:05:00+00:00",
            "EvaluatedAt": "2026-06-20T06:00:00+00:00",
            "DecisionPackageID": package_id,
        },
    )
    assert authorization_response.status_code == 200
    authorization_id = authorization_response.json()["Data"]["Authorization"][
        "AuthorizationID"
    ]
    for event_type, event_at in (
        ("StartedOperation", "2026-06-16T08:05:00+00:00"),
        ("CompletedOperation", "2026-06-16T10:20:00+00:00"),
    ):
        event_response = client.post(
            "/shop-floor/execution/event",
            json={
                "AuthorizationID": authorization_id,
                "OrderID": "WO-1",
                "EventType": event_type,
                "EventAt": event_at,
                "TargetStartAt": "2026-06-16T08:00:00+00:00",
            },
        )
        assert event_response.status_code == 200

    response = client.get(
        f"/planner/workbench/release-decision-packages/{package_id}/execution-stability",
        params={
            "ToleranceMinutes": 10,
            "ReplanThresholdMinutes": 15,
            "ReplanCooldownMinutes": 60,
            "LastReplanAt": "2026-06-16T10:00:00+00:00",
        },
    )

    assert response.status_code == 200
    data = response.json()["Data"]
    assert data["OverallAction"] == "Review"
    assert data["ReplanRequired"] is False
    row = data["Rows"][0]
    assert row["DeviationBasis"] == "Completion"
    assert row["DeviationMinutes"] == 20
    assert row["Action"] == "Review"
    assert row["ReasonCode"] == "ReplanCooldownActive"


def test_execution_variance_replan_enters_review_queue_without_running_solver():
    client = TestClient(create_app())
    request_id = _completed_replan_request_id(client)
    decision_package = _create_release_decision_package(client, request_id)
    package_id = decision_package["DecisionPackageID"]
    authorization_response = client.post(
        f"/planner/workbench/replan-requests/{request_id}/release-authorizations",
        json={
            "OrderID": "WO-1",
            "ReleasedBy": "planner-1",
            "ReleasedAt": "2026-06-20T06:05:00+00:00",
            "EvaluatedAt": "2026-06-20T06:00:00+00:00",
            "DecisionPackageID": package_id,
        },
    )
    assert authorization_response.status_code == 200
    authorization_id = authorization_response.json()["Data"]["Authorization"][
        "AuthorizationID"
    ]
    for event_type, event_at in (
        ("StartedOperation", "2026-06-16T08:05:00+00:00"),
        ("CompletedOperation", "2026-06-16T10:20:00+00:00"),
    ):
        event_response = client.post(
            "/shop-floor/execution/event",
            json={
                "AuthorizationID": authorization_id,
                "OrderID": "WO-1",
                "EventType": event_type,
                "EventAt": event_at,
                "TargetStartAt": "2026-06-16T08:00:00+00:00",
            },
        )
        assert event_response.status_code == 200
    payload = {
        "DetectedAt": "2026-06-16T10:25:00+00:00",
        "RequestedBy": "planner-1",
        "ToleranceMinutes": 10,
        "ReplanThresholdMinutes": 15,
        "ReplanCooldownMinutes": 60,
    }

    first = client.post(
        f"/planner/workbench/release-decision-packages/{package_id}/execution-replan-requests",
        json=payload,
    )
    repeated = client.post(
        f"/planner/workbench/release-decision-packages/{package_id}/execution-replan-requests",
        json=payload,
    )

    assert first.status_code == 200
    assert repeated.status_code == 200
    data = first.json()["Data"]
    assert data["Count"] == 1
    request = data["Requests"][0]
    assert repeated.json()["Data"]["Requests"][0]["RequestID"] == request["RequestID"]
    assert request["Status"] == "PendingReview"
    assert request["Source"] == "ExecutionVariance"
    assert request["SourceReferenceID"] == package_id
    assert request["RequestedBy"] == "planner-1"
    assert request["SolverBackendID"] is None

    linked_response = client.get(
        f"/planner/workbench/release-decision-packages/{package_id}/replan-requests"
    )
    assert linked_response.status_code == 200
    linked = linked_response.json()["Data"]
    assert linked["DecisionPackageID"] == package_id
    assert linked["FeedbackStatus"] == "PendingReview"
    assert linked["Count"] == 1
    assert linked["Requests"] == [request]


def test_release_authorization_rejects_unknown_decision_package():
    client = TestClient(create_app())
    request_id = _completed_replan_request_id(client)

    response = client.post(
        f"/planner/workbench/replan-requests/{request_id}/release-authorizations",
        json={
            "OrderID": "WO-1",
            "ReleasedBy": "planner-1",
            "ReleasedAt": "2026-06-20T06:05:00+00:00",
            "EvaluatedAt": "2026-06-20T06:00:00+00:00",
            "DecisionPackageID": "RDP-MISSING",
        },
    )

    assert response.status_code == 404
    assert response.json()["Data"]["Status"] == "ReleaseDecisionPackageNotFound"


def test_release_authorization_rejects_changed_evidence_for_same_event():
    client = TestClient(create_app())
    request_id = _completed_replan_request_id(client)
    decision_package = _create_release_decision_package(client, request_id)
    packaged_response = client.post(
        f"/planner/workbench/replan-requests/{request_id}/release-authorizations",
        json={
            "OrderID": "WO-1",
            "ReleasedBy": "planner-1",
            "ReleasedAt": "2026-06-20T06:05:00+00:00",
            "EvaluatedAt": "2026-06-20T06:00:00+00:00",
            "DecisionPackageID": decision_package["DecisionPackageID"],
        },
    )
    assert packaged_response.status_code == 200

    conflicting_response = client.post(
        f"/planner/workbench/replan-requests/{request_id}/release-authorizations",
        json={
            "OrderID": "WO-1",
            "ReleasedBy": "planner-1",
            "ReleasedAt": "2026-06-20T06:05:00+00:00",
            "EvaluatedAt": "2026-06-20T06:00:00+00:00",
        },
    )

    assert conflicting_response.status_code == 409
    data = conflicting_response.json()["Data"]
    assert data["Status"] == "ReleaseAuthorizationEvidenceConflict"
    assert data["ExistingEvidence"]["DecisionPackageID"] == decision_package[
        "DecisionPackageID"
    ]
    assert data["RequestedEvidence"]["DecisionPackageID"] is None


def test_release_candidates_block_when_wip_limit_is_full():
    client = TestClient(create_app())
    request_id = _approve_replan_request(client)["RequestID"]
    execution_payload = _calculate_payload()
    execution_payload["SolverBackendID"] = "ortools"
    execution = client.post(
        f"/planner/workbench/replan-requests/{request_id}/execute",
        json=execution_payload,
    ).json()["Data"]

    response = client.post(
        f"/planner/workbench/replan-requests/{request_id}/release-candidates",
        json={
            "EvaluatedAt": "2026-06-20T06:00:00+00:00",
            "WipLimits": [
                {
                    "ScopeID": "DRUM-FEED",
                    "CurrentWipCount": 5,
                    "MaxWipCount": 5,
                }
            ],
        },
    )

    if execution["Request"]["Status"] != "Completed":
        assert response.status_code == 409
        assert response.json()["Data"]["Status"] == "ReleaseCandidatesUnavailable"
        return
    assert response.status_code == 200
    candidate = response.json()["Data"]["Candidates"][0]
    assert candidate["WipStatus"] == "Blocked"
    assert candidate["RecommendedAction"] == "HoldForWip"
    assert candidate["WipRisks"][0]["ProjectedWipCount"] == 6


def test_release_candidates_wait_for_inbound_material_before_start():
    client = TestClient(create_app())
    request_id = _approve_replan_request(client)["RequestID"]
    execution_payload = _calculate_payload()
    execution_payload["SolverBackendID"] = "ortools"
    execution = client.post(
        f"/planner/workbench/replan-requests/{request_id}/execute",
        json=execution_payload,
    ).json()["Data"]

    response = client.post(
        f"/planner/workbench/replan-requests/{request_id}/release-candidates",
        json={
            "EvaluatedAt": "2026-06-20T06:00:00+00:00",
            "InventoryBuffers": [
                {
                    "ItemID": "RM-STEEL",
                    "LocationID": "SUPPLIER-DECOUPLING",
                    "OnHandQty": 55,
                    "RedZoneQty": 50,
                    "YellowZoneQty": 120,
                    "GreenZoneQty": 200,
                }
            ],
            "MaterialRequirements": [
                {
                    "OrderID": "WO-1",
                    "ItemID": "RM-STEEL",
                    "LocationID": "SUPPLIER-DECOUPLING",
                    "RequiredQty": 10,
                }
            ],
            "MaterialAvailability": [
                {
                    "ItemID": "RM-STEEL",
                    "LocationID": "SUPPLIER-DECOUPLING",
                    "AllocatedQty": 5,
                    "InboundQty": 15,
                    "InboundAvailableAt": "2026-06-16T07:30:00+00:00",
                }
            ],
        },
    )

    if execution["Request"]["Status"] != "Completed":
        assert response.status_code == 409
        assert response.json()["Data"]["Status"] == "ReleaseCandidatesUnavailable"
        return
    assert response.status_code == 200
    candidate = response.json()["Data"]["Candidates"][0]
    assert candidate["MaterialStatus"] == "PendingInbound"
    assert candidate["RecommendedAction"] == "WaitForInbound"
    assert candidate["InventoryRisks"][0]["RiskType"] == "InboundPending"


def test_release_candidates_mark_late_inbound_material():
    client = TestClient(create_app())
    request_id = _approve_replan_request(client)["RequestID"]
    execution_payload = _calculate_payload()
    execution_payload["SolverBackendID"] = "ortools"
    execution = client.post(
        f"/planner/workbench/replan-requests/{request_id}/execute",
        json=execution_payload,
    ).json()["Data"]

    response = client.post(
        f"/planner/workbench/replan-requests/{request_id}/release-candidates",
        json={
            "EvaluatedAt": "2026-06-20T06:00:00+00:00",
            "InventoryBuffers": [
                {
                    "ItemID": "RM-STEEL",
                    "LocationID": "SUPPLIER-DECOUPLING",
                    "OnHandQty": 55,
                    "RedZoneQty": 50,
                    "YellowZoneQty": 120,
                    "GreenZoneQty": 200,
                }
            ],
            "MaterialRequirements": [
                {
                    "OrderID": "WO-1",
                    "ItemID": "RM-STEEL",
                    "LocationID": "SUPPLIER-DECOUPLING",
                    "RequiredQty": 10,
                }
            ],
            "MaterialAvailability": [
                {
                    "ItemID": "RM-STEEL",
                    "LocationID": "SUPPLIER-DECOUPLING",
                    "AllocatedQty": 5,
                    "InboundQty": 15,
                    "InboundAvailableAt": "2026-06-16T09:30:00+00:00",
                }
            ],
        },
    )

    if execution["Request"]["Status"] != "Completed":
        assert response.status_code == 409
        assert response.json()["Data"]["Status"] == "ReleaseCandidatesUnavailable"
        return
    assert response.status_code == 200
    candidate = response.json()["Data"]["Candidates"][0]
    assert candidate["MaterialStatus"] == "Blocked"
    assert candidate["RecommendedAction"] == "ExpediteMaterial"
    assert candidate["InventoryRisks"][0]["RiskType"] == "InboundLate"


def test_release_authorization_creates_record_for_ready_candidate():
    client = TestClient(create_app())
    request_id = _completed_replan_request_id(client)

    response = client.post(
        f"/planner/workbench/replan-requests/{request_id}/release-authorizations",
        json={
            "OrderID": "WO-1",
            "ReleasedBy": "planner-1",
            "ReleasedAt": "2026-06-20T06:05:00+00:00",
            "EvaluatedAt": "2026-06-20T06:00:00+00:00",
            "InventoryBuffers": [
                {
                    "ItemID": "RM-STEEL",
                    "LocationID": "SUPPLIER-DECOUPLING",
                    "OnHandQty": 80,
                    "RedZoneQty": 50,
                    "YellowZoneQty": 120,
                    "GreenZoneQty": 200,
                }
            ],
            "MaterialRequirements": [
                {
                    "OrderID": "WO-1",
                    "ItemID": "RM-STEEL",
                    "LocationID": "SUPPLIER-DECOUPLING",
                    "RequiredQty": 10,
                }
            ],
            "WipLimits": [
                {
                    "ScopeID": "DRUM-FEED",
                    "CurrentWipCount": 0,
                    "MaxWipCount": 5,
                }
            ],
        },
    )

    assert response.status_code == 200
    authorization = response.json()["Data"]["Authorization"]
    assert authorization["RequestID"] == request_id
    assert authorization["OrderID"] == "WO-1"
    assert authorization["Status"] == "Authorized"
    assert authorization["ReleasedBy"] == "planner-1"
    queue = client.get("/planner/workbench/release-authorizations")
    assert queue.status_code == 200
    assert queue.json()["Data"]["Authorizations"] == [authorization]


def test_release_authorization_preserves_operational_state_snapshot_provenance():
    client = TestClient(create_app())
    snapshot_response = client.post(
        "/planner/workbench/operational-state/snapshots",
        json={
            "SnapshotID": "OPS-AUTH-20260620-0600",
            "CapturedAt": "2026-06-20T06:00:00+00:00",
            "InventoryBuffers": [
                {
                    "ItemID": "RM-STEEL",
                    "LocationID": "SUPPLIER-DECOUPLING",
                    "OnHandQty": 80,
                    "RedZoneQty": 50,
                    "YellowZoneQty": 120,
                    "GreenZoneQty": 200,
                }
            ],
        },
    )
    assert snapshot_response.status_code == 200
    request_id = _completed_replan_request_id(client)

    response = client.post(
        f"/planner/workbench/replan-requests/{request_id}/release-authorizations",
        json={
            "OrderID": "WO-1",
            "ReleasedBy": "planner-1",
            "ReleasedAt": "2026-06-20T06:05:00+00:00",
            "EvaluatedAt": "2026-06-20T06:00:00+00:00",
            "OperationalStateSnapshotID": "OPS-AUTH-20260620-0600",
            "MaterialRequirements": [
                {
                    "OrderID": "WO-1",
                    "ItemID": "RM-STEEL",
                    "LocationID": "SUPPLIER-DECOUPLING",
                    "RequiredQty": 10,
                }
            ],
        },
    )

    assert response.status_code == 200
    authorization = response.json()["Data"]["Authorization"]
    assert authorization["OperationalStateSnapshotID"] == "OPS-AUTH-20260620-0600"
    assert authorization["OperationalStateCapturedAt"] == "2026-06-20T06:00:00+00:00"

    dispatch_response = client.get(
        f"/planner/workbench/release-authorizations/{authorization['AuthorizationID']}/dispatch-package"
    )
    assert dispatch_response.status_code == 200
    dispatch_package = dispatch_response.json()["Data"]["DispatchPackage"]
    assert dispatch_package["OperationalStateSnapshotID"] == "OPS-AUTH-20260620-0600"
    assert dispatch_package["OperationalStateCapturedAt"] == "2026-06-20T06:00:00+00:00"


def test_release_authorization_rejects_stale_operational_state_snapshot():
    client = TestClient(create_app())
    snapshot_response = client.post(
        "/planner/workbench/operational-state/snapshots",
        json={
            "SnapshotID": "OPS-STALE",
            "CapturedAt": "2026-06-20T04:00:00+00:00",
        },
    )
    assert snapshot_response.status_code == 200
    request_id = _completed_replan_request_id(client)

    response = client.post(
        f"/planner/workbench/replan-requests/{request_id}/release-authorizations",
        json={
            "OrderID": "WO-1",
            "ReleasedBy": "planner-1",
            "ReleasedAt": "2026-06-20T06:05:00+00:00",
            "EvaluatedAt": "2026-06-20T06:00:00+00:00",
            "OperationalStateSnapshotID": "OPS-STALE",
            "OperationalStateMaxAgeMinutes": 60,
        },
    )

    assert response.status_code == 409
    data = response.json()["Data"]
    assert data["Status"] == "OperationalStateSnapshotStale"
    assert data["SnapshotID"] == "OPS-STALE"
    assert data["AgeMinutes"] == 120
    assert data["MaxAgeMinutes"] == 60


def test_release_authorization_stability_report_returns_actual_release_deviation():
    client = TestClient(create_app())
    request_id = _completed_replan_request_id(client)
    authorization = _authorize_release(client, request_id)

    response = client.get("/planner/workbench/release-authorizations/stability-report")

    assert response.status_code == 200
    payload = response.json()
    assert payload["Endpoint"] == "/planner/workbench/release-authorizations/stability-report"
    assert payload["Data"]["Rows"] == [
        {
            "AuthorizationID": authorization["AuthorizationID"],
            "RequestID": request_id,
            "OrderID": "WO-1",
            "SuggestedReleaseAt": "2026-06-20T06:00:00+00:00",
            "ReleasedAt": "2026-06-20T06:05:00+00:00",
            "DeviationMinutes": 5,
            "AbsoluteDeviationMinutes": 5,
            "TimingStatus": "Late",
            "Severity": "Normal",
            "Action": "Monitor",
            "ReplanRequired": False,
            "ReasonCode": "WithinTolerance",
        }
    ]


def test_release_authorization_rejects_blocked_candidate():
    client = TestClient(create_app())
    request_id = _completed_replan_request_id(client)

    response = client.post(
        f"/planner/workbench/replan-requests/{request_id}/release-authorizations",
        json={
            "OrderID": "WO-1",
            "ReleasedBy": "planner-1",
            "ReleasedAt": "2026-06-20T06:05:00+00:00",
            "EvaluatedAt": "2026-06-20T06:00:00+00:00",
            "WipLimits": [
                {
                    "ScopeID": "DRUM-FEED",
                    "CurrentWipCount": 5,
                    "MaxWipCount": 5,
                }
            ],
        },
    )

    assert response.status_code == 409
    assert response.json()["Data"]["Status"] == "ReleaseAuthorizationRejected"
    assert response.json()["Data"]["Candidate"]["RecommendedAction"] == "HoldForWip"


def test_release_authorization_dispatch_package_returns_ready_to_issue():
    client = TestClient(create_app())
    request_id = _completed_replan_request_id(client)
    authorization = _authorize_release(client, request_id)

    response = client.get(
        f"/planner/workbench/release-authorizations/{authorization['AuthorizationID']}/dispatch-package"
    )

    assert response.status_code == 200
    package = response.json()["Data"]["DispatchPackage"]
    assert package["AuthorizationID"] == authorization["AuthorizationID"]
    assert package["RequestID"] == request_id
    assert package["OrderID"] == "WO-1"
    assert package["DispatchStatus"] == "ReadyToIssue"


def test_shop_floor_execution_event_records_authorization_trace():
    client = TestClient(create_app())
    request_id = _completed_replan_request_id(client)
    authorization = _authorize_release(client, request_id)

    response = client.post(
        "/shop-floor/execution/event",
        json={
            "AuthorizationID": authorization["AuthorizationID"],
            "OrderID": "WO-1",
            "EventType": "StartedOperation",
            "EventAt": "2026-06-16T08:05:00+00:00",
            "TargetStartAt": "2026-06-16T08:00:00+00:00",
        },
    )

    assert response.status_code == 200
    events = client.get("/shop-floor/execution/events").json()["Data"]["Events"]
    assert events == [
        {
            "AuthorizationID": authorization["AuthorizationID"],
            "OrderID": "WO-1",
            "EventType": "StartedOperation",
            "EventAt": "2026-06-16T08:05:00+00:00",
            "TargetStartAt": "2026-06-16T08:00:00+00:00",
            "ExceptionCode": None,
            "Status": "Accepted",
            "RequiresReview": False,
        }
    ]


def test_shop_floor_authorized_execution_status_returns_dispatch_progress():
    client = TestClient(create_app())
    request_id = _completed_replan_request_id(client)
    authorization = _authorize_release(client, request_id)
    client.post(
        "/shop-floor/execution/event",
        json={
            "AuthorizationID": authorization["AuthorizationID"],
            "OrderID": "WO-1",
            "EventType": "StartedOperation",
            "EventAt": "2026-06-16T08:05:00+00:00",
            "TargetStartAt": "2026-06-16T08:00:00+00:00",
        },
    )

    response = client.get("/shop-floor/execution/authorized-status")

    assert response.status_code == 200
    payload = response.json()
    assert payload["Endpoint"] == "/shop-floor/execution/authorized-status"
    assert payload["Data"]["Rows"] == [
        {
            "AuthorizationID": authorization["AuthorizationID"],
            "RequestID": request_id,
            "OrderID": "WO-1",
            "ScheduledStart": "2026-06-16T08:00:00+00:00",
            "ScheduledEnd": "2026-06-16T10:00:00+00:00",
            "ExecutionStatus": "InProcess",
            "LastEventType": "StartedOperation",
            "LastEventAt": "2026-06-16T08:05:00+00:00",
            "RequiresReview": False,
            "ExceptionCodes": [],
        }
    ]


def test_shop_floor_authorized_execution_alerts_returns_missed_start():
    client = TestClient(create_app())
    request_id = _completed_replan_request_id(client)
    authorization = _authorize_release(client, request_id)

    response = client.get(
        "/shop-floor/execution/authorized-alerts"
        "?EvaluatedAt=2026-06-16T09:45:00%2B00:00"
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["Endpoint"] == "/shop-floor/execution/authorized-alerts"
    assert payload["Data"]["Alerts"] == [
        {
            "AuthorizationID": authorization["AuthorizationID"],
            "OrderID": "WO-1",
            "AlertType": "StartMissed",
            "Severity": "Critical",
            "Message": "Order WO-1 has not started by the scheduled start time.",
            "MinutesLate": 105,
            "ExceptionCodes": [],
        }
    ]


def test_shop_floor_execution_event_rejects_authorization_order_mismatch():
    client = TestClient(create_app())
    request_id = _completed_replan_request_id(client)
    authorization = _authorize_release(client, request_id)

    response = client.post(
        "/shop-floor/execution/event",
        json={
            "AuthorizationID": authorization["AuthorizationID"],
            "OrderID": "WO-OTHER",
            "EventType": "StartedOperation",
            "EventAt": "2026-06-16T08:05:00+00:00",
            "TargetStartAt": "2026-06-16T08:00:00+00:00",
        },
    )

    assert response.status_code == 409
    assert response.json()["Data"]["Status"] == "ExecutionAuthorizationMismatch"


def _trigger_replan_request(client: TestClient) -> dict[str, object]:
    request_payload = _calculate_payload()
    request_payload["InventoryBuffers"][0]["OnHandQty"] = 55
    request_payload["MaterialRequirements"] = [
        {
            "OrderID": "WO-1",
            "ItemID": "RM-STEEL",
            "LocationID": "SUPPLIER-DECOUPLING",
            "RequiredQty": 10,
        }
    ]
    response = client.post(
        "/planner/workbench/release",
        json={
            **request_payload,
            "OrderID": "WO-1",
            "RequestedReleaseAt": "2026-06-20T06:00:00+00:00",
            "PreviousConsecutiveBlockedCount": 2,
        },
    )
    assert response.status_code == 409
    return response.json()["Data"]["ReplanRequest"]


def _approve_replan_request(client: TestClient) -> dict[str, object]:
    request = _trigger_replan_request(client)
    response = client.post(
        f"/planner/workbench/replan-requests/{request['RequestID']}/decision",
        json={
            "Decision": "Approve",
            "DecidedBy": "planner-1",
            "DecidedAt": "2026-06-20T07:00:00+00:00",
        },
    )
    assert response.status_code == 200
    return response.json()["Data"]["Request"]


def _create_master_data_and_snapshot(
    client: TestClient,
    *,
    version_id: str,
    snapshot_id: str,
) -> None:
    master_data_payload = _master_data_import_calculate_payload()
    master_data_payload.pop("ProblemID")
    master_data_payload.pop("ScheduleStartAt")
    master_data_payload.update(
        {
            "VersionID": version_id,
            "CapturedAt": "2026-06-16T07:30:00+00:00",
            "SourceSystem": "ERP",
            "CreatedBy": "planner-1",
        }
    )
    assert client.post(
        "/planner/workbench/master-data/versions",
        json=master_data_payload,
    ).status_code == 200
    assert client.post(
        "/planner/workbench/operational-state/snapshots",
        json={
            "SnapshotID": snapshot_id,
            "CapturedAt": "2026-06-16T07:45:00+00:00",
            "InventoryBuffers": master_data_payload["InventoryBufferRows"],
        },
    ).status_code == 200


def _create_and_execute_planning_run(
    client: TestClient,
    *,
    run_id: str,
    master_data_version_id: str,
    snapshot_id: str,
    problem_id: str = "P-IMPORT-CALC",
    release_policy_version_id: str | None = None,
) -> dict[str, object]:
    create_payload = {
        "RunID": run_id,
        "ProblemID": problem_id,
        "MasterDataVersionID": master_data_version_id,
        "OperationalStateSnapshotID": snapshot_id,
        "ScheduleStartAt": "2026-06-16T08:00:00+00:00",
        "SolverBackendID": "ortools",
        "RequestedBy": "planner-1",
        "RequestedAt": "2026-06-16T07:50:00+00:00",
    }
    if release_policy_version_id is not None:
        create_payload["ReleasePolicyVersionID"] = release_policy_version_id
    assert client.post(
        "/planner/workbench/planning-runs",
        json=create_payload,
    ).status_code == 200
    response = client.post(
        f"/planner/workbench/planning-runs/{run_id}/execute",
        json={
            "ExecutedBy": "planner-1",
            "StartedAt": "2026-06-16T07:55:00+00:00",
            "CompletedAt": "2026-06-16T07:56:00+00:00",
        },
    )
    assert response.status_code == 200
    return response.json()["Data"]["PlanningRun"]


def _completed_replan_request_id(client: TestClient) -> str:
    request_id = _approve_replan_request(client)["RequestID"]
    execution_payload = _calculate_payload()
    execution_payload["SolverBackendID"] = "ortools"
    response = client.post(
        f"/planner/workbench/replan-requests/{request_id}/execute",
        json=execution_payload,
    )
    assert response.status_code == 200
    assert response.json()["Data"]["Request"]["Status"] == "Completed"
    return request_id


def _authorize_release(client: TestClient, request_id: str) -> dict[str, object]:
    response = client.post(
        f"/planner/workbench/replan-requests/{request_id}/release-authorizations",
        json={
            "OrderID": "WO-1",
            "ReleasedBy": "planner-1",
            "ReleasedAt": "2026-06-20T06:05:00+00:00",
            "EvaluatedAt": "2026-06-20T06:00:00+00:00",
            "InventoryBuffers": [
                {
                    "ItemID": "RM-STEEL",
                    "LocationID": "SUPPLIER-DECOUPLING",
                    "OnHandQty": 80,
                    "RedZoneQty": 50,
                    "YellowZoneQty": 120,
                    "GreenZoneQty": 200,
                }
            ],
            "MaterialRequirements": [
                {
                    "OrderID": "WO-1",
                    "ItemID": "RM-STEEL",
                    "LocationID": "SUPPLIER-DECOUPLING",
                    "RequiredQty": 10,
                }
            ],
            "WipLimits": [
                {
                    "ScopeID": "DRUM-FEED",
                    "CurrentWipCount": 0,
                    "MaxWipCount": 5,
                }
            ],
        },
    )
    assert response.status_code == 200
    return response.json()["Data"]["Authorization"]


def _create_release_decision_package(
    client: TestClient,
    request_id: str,
) -> dict[str, object]:
    snapshot_response = client.post(
        "/planner/workbench/operational-state/snapshots",
        json={
            "SnapshotID": "OPS-AUTH-PACKAGE",
            "CapturedAt": "2026-06-20T06:00:00+00:00",
            "InventoryBuffers": [
                {
                    "ItemID": "RM-STEEL",
                    "LocationID": "SUPPLIER-DECOUPLING",
                    "OnHandQty": 80,
                    "RedZoneQty": 50,
                    "YellowZoneQty": 120,
                    "GreenZoneQty": 200,
                }
            ],
        },
    )
    assert snapshot_response.status_code == 200
    response = client.post(
        f"/planner/workbench/replan-requests/{request_id}/release-decision-packages",
        json={
            "EvaluatedAt": "2026-06-20T06:00:00+00:00",
            "OperationalStateSnapshotID": "OPS-AUTH-PACKAGE",
            "MaterialRequirements": [
                {
                    "OrderID": "WO-1",
                    "ItemID": "RM-STEEL",
                    "LocationID": "SUPPLIER-DECOUPLING",
                    "RequiredQty": 10,
                }
            ],
        },
    )
    assert response.status_code == 200
    return response.json()["Data"]["DecisionPackage"]


def test_planner_workbench_release_endpoint_returns_not_found_for_unknown_order():
    client = TestClient(create_app(), raise_server_exceptions=False)

    response = client.post(
        "/planner/workbench/release",
        json={
            **_calculate_payload(),
            "OrderID": "WO-MISSING",
            "RequestedReleaseAt": "2026-06-20T06:00:00+00:00",
        },
    )

    assert response.status_code == 404
    payload = response.json()
    assert payload["Endpoint"] == "/planner/workbench/release"
    assert payload["StatusCode"] == 404
    assert payload["Data"] == {
        "OrderID": "WO-MISSING",
        "Allowed": False,
        "Status": "ReleaseOrderNotFound",
        "Message": "No release recommendation exists for order WO-MISSING.",
    }


def test_planner_workbench_release_endpoint_rejects_invalid_master_data():
    client = TestClient(create_app(), raise_server_exceptions=False)
    request_payload = _calculate_payload()
    request_payload["Orders"][0]["ProductID"] = "FG-MISSING"

    response = client.post(
        "/planner/workbench/release",
        json={
            **request_payload,
            "OrderID": "WO-1",
            "RequestedReleaseAt": "2026-06-20T06:00:00+00:00",
        },
    )

    assert response.status_code == 409
    payload = response.json()
    assert payload["Endpoint"] == "/planner/workbench/release"
    assert payload["StatusCode"] == 409
    assert payload["Data"]["Validation"]["IsValid"] is False
    assert {
        "Severity": "Error",
        "Code": "UNKNOWN_PRODUCT_ROUTING",
        "Message": "Order WO-1 references product FG-MISSING without a routing.",
        "Field": "Orders.WO-1.ProductID",
    } in payload["Data"]["Validation"]["Issues"]


def test_shop_floor_execution_event_rejects_late_buffer_arrival_without_exception_code():
    client = TestClient(create_app())

    response = client.post(
        "/shop-floor/execution/event",
        json={
            "OrderID": "WO-1",
            "EventType": "ArrivedBuffer",
            "EventAt": "2026-06-16T09:00:00+00:00",
            "TargetStartAt": "2026-06-16T08:00:00+00:00",
        },
    )

    assert response.status_code == 409
    payload = response.json()
    assert payload["Endpoint"] == "/shop-floor/execution/event"
    assert payload["StatusCode"] == 409
    assert payload["Data"]["Accepted"] is False
    assert payload["Data"]["RequiresExceptionCode"] is True


def test_shop_floor_execution_event_accepts_late_buffer_arrival_with_exception_code():
    client = TestClient(create_app())

    response = client.post(
        "/shop-floor/execution/event",
        json={
            "OrderID": "WO-1",
            "EventType": "ArrivedBuffer",
            "EventAt": "2026-06-16T09:00:00+00:00",
            "TargetStartAt": "2026-06-16T08:00:00+00:00",
            "ExceptionCode": "MATERIAL_SHORTAGE",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["Data"]["Accepted"] is True
    assert payload["Data"]["Status"] == "AcceptedWithException"
    assert payload["Data"]["RequiresReview"] is True


def test_shop_floor_execution_event_rejects_unknown_exception_code():
    client = TestClient(create_app())

    response = client.post(
        "/shop-floor/execution/event",
        json={
            "OrderID": "WO-1",
            "EventType": "ArrivedBuffer",
            "EventAt": "2026-06-16T09:00:00+00:00",
            "TargetStartAt": "2026-06-16T08:00:00+00:00",
            "ExceptionCode": "UNKNOWN_DELAY",
        },
    )

    assert response.status_code == 409
    payload = response.json()
    assert payload["Data"]["Accepted"] is False
    assert payload["Data"]["Message"] == "Unknown exception code."


def test_shop_floor_exception_codes_endpoint_returns_default_catalog():
    client = TestClient(create_app())

    response = client.get("/shop-floor/execution/exception-codes")

    assert response.status_code == 200
    payload = response.json()
    assert payload["Endpoint"] == "/shop-floor/execution/exception-codes"
    assert {
        "Code": "EQUIPMENT_DOWN",
        "DisplayName": "Equipment down",
        "Category": "Equipment",
    } in payload["Data"]


def test_shop_floor_execution_events_endpoint_returns_recorded_events():
    client = TestClient(create_app())

    client.post(
        "/shop-floor/execution/event",
        json={
            "OrderID": "WO-1",
            "EventType": "ArrivedBuffer",
            "EventAt": "2026-06-16T09:00:00+00:00",
            "TargetStartAt": "2026-06-16T08:00:00+00:00",
            "ExceptionCode": "MATERIAL_SHORTAGE",
        },
    )
    client.post(
        "/shop-floor/execution/event",
        json={
            "OrderID": "WO-1",
            "EventType": "StartedOperation",
            "EventAt": "2026-06-16T09:30:00+00:00",
            "TargetStartAt": "2026-06-16T08:00:00+00:00",
        },
    )
    response = client.get("/shop-floor/execution/events")

    assert response.status_code == 200
    payload = response.json()
    assert payload["Endpoint"] == "/shop-floor/execution/events"
    assert payload["StatusCode"] == 200
    assert payload["Data"]["Events"] == [
        {
            "OrderID": "WO-1",
            "EventType": "ArrivedBuffer",
            "EventAt": "2026-06-16T09:00:00+00:00",
            "TargetStartAt": "2026-06-16T08:00:00+00:00",
            "ExceptionCode": "MATERIAL_SHORTAGE",
            "Status": "AcceptedWithException",
            "RequiresReview": True,
        },
        {
            "OrderID": "WO-1",
            "EventType": "StartedOperation",
            "EventAt": "2026-06-16T09:30:00+00:00",
            "TargetStartAt": "2026-06-16T08:00:00+00:00",
            "ExceptionCode": None,
            "Status": "Accepted",
            "RequiresReview": False,
        },
    ]
    assert payload["Data"]["Summary"] == {
        "TotalEvents": 2,
        "RequiresReviewCount": 1,
        "ExceptionCodeCounts": {
            "MATERIAL_SHORTAGE": 1,
        },
        "ExceptionCategoryCounts": {
            "Supply": 1,
        },
        "TopExceptionCategories": [
            {
                "Rank": 1,
                "Category": "Supply",
                "Count": 1,
                "Percent": 100.0,
                "RecommendedAction": "Expedite replenishment and review supplier reliability.",
            }
        ],
        "LateArrivalSummary": {
            "LateArrivalCount": 1,
            "AverageLateMinutes": 60.0,
            "MaxLateMinutes": 60.0,
        },
        "ReworkLoopCount": 0,
        "ProcessTransitions": [
            {
                "From": "ArrivedBuffer",
                "To": "StartedOperation",
                "Count": 1,
                "AverageElapsedMinutes": 30.0,
                "RequiresReviewCount": 1,
                "IsReworkLoop": False,
            }
        ],
    }


def _calculate_payload() -> dict[str, object]:
    return {
        "ProblemID": "P-CALC",
        "ScheduleStartAt": "2026-06-16T08:00:00+00:00",
        "Resources": [
            {
                "ResourceID": "WC-DRUM",
                "Name": "Constraint Cutter",
                "IsConstraint": True,
                "DailyCapacityMinutes": {"2026-06-16": 480},
            }
        ],
        "Routings": [
            {
                "ProductID": "FG-A",
                "RoutingID": "PRIMARY",
                "IsPrimary": True,
                "Operations": [
                    {
                        "OperationID": "CUT",
                        "ResourceID": "WC-DRUM",
                        "DurationMinutes": 120,
                        "Sequence": 1,
                    }
                ],
            }
        ],
        "Orders": [
            {
                "OrderID": "WO-1",
                "ProductID": "FG-A",
                "Quantity": 1,
                "DueDate": "2026-06-20T08:00:00+00:00",
                "TargetStartDate": "2026-06-16",
            }
        ],
        "InventoryBuffers": [
            {
                "ItemID": "RM-STEEL",
                "LocationID": "SUPPLIER-DECOUPLING",
                "OnHandQty": 35,
                "RedZoneQty": 50,
                "YellowZoneQty": 120,
                "GreenZoneQty": 200,
            }
        ],
    }


def _master_data_import_calculate_payload() -> dict[str, object]:
    return {
        "ProblemID": "P-IMPORT-CALC",
        "ScheduleStartAt": "2026-06-16T08:00:00+00:00",
        "ResourceRows": [
            {
                "ResourceID": "WC-DRUM",
                "Name": "Constraint Cutter",
                "IsConstraint": True,
                "CapacityDate": "2026-06-16",
                "CapacityMinutes": 480,
            }
        ],
        "RoutingRows": [
            {
                "ProductID": "FG-A",
                "RoutingID": "PRIMARY",
                "IsPrimary": True,
                "OperationID": "CUT",
                "ResourceID": "WC-DRUM",
                "DurationMinutes": 120,
                "Sequence": 1,
            }
        ],
        "OrderRows": [
            {
                "OrderID": "WO-1",
                "ProductID": "FG-A",
                "Quantity": 1,
                "DueDate": "2026-06-20T08:00:00+00:00",
                "TargetStartDate": "2026-06-16",
            }
        ],
        "InventoryBufferRows": [
            {
                "ItemID": "RM-STEEL",
                "LocationID": "SUPPLIER-DECOUPLING",
                "OnHandQty": 35,
                "RedZoneQty": 50,
                "YellowZoneQty": 120,
                "GreenZoneQty": 200,
            }
        ],
    }
