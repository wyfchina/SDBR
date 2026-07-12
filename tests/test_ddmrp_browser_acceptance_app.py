"""Acceptance evidence for BE-DDMRP-007 and UI-DDMRP-003."""

from __future__ import annotations

from copy import deepcopy
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from sdbr.api import create_app
from sdbr.ddmrp_replenishment_view import build_ddmrp_replenishment_workbench
from sdbr.state_store import SQLiteWorkbenchStateStore
from sdbr.test_data import reset_test_database


DDMRP_WORKBENCH_ENDPOINT = "/planner/workbench/ddmrp/workbench"
_EMPTY_WORKBENCH_KEYS = {
    "Evaluation",
    "Summary",
    "Rows",
    "ActiveGraphs",
    "History",
    "Issues",
    "Boundary",
    "TechnicalDetails",
}


def _acceptance_client(tmp_path):
    database_path = tmp_path / "ddmrp-browser-acceptance.db"
    reset_test_database(database_path=database_path)
    store = SQLiteWorkbenchStateStore(database_path)
    fixture_module = _acceptance_fixture_module()
    return TestClient(
        fixture_module.create_ddmrp_browser_acceptance_app(store)
    ), store


def _acceptance_fixture_module():
    fixture_path = Path(__file__).with_name("ddmrp_browser_acceptance_app.py")
    spec = spec_from_file_location("ddmrp_browser_acceptance_app", fixture_path)
    assert spec is not None and spec.loader is not None
    fixture_module = module_from_spec(spec)
    spec.loader.exec_module(fixture_module)
    return fixture_module


@pytest.mark.parametrize(
    ("mode", "status_code"),
    [
        ("seeded", 200),
        ("empty", 200),
        ("error", 500),
        ("403", 403),
        ("409", 409),
    ],
)
def test_ui_ddmrp_003_browser_acceptance_fixture_modes_are_exact(
    tmp_path,
    mode: str,
    status_code: int,
) -> None:
    client, store = _acceptance_client(tmp_path)
    before = deepcopy(store.snapshot_state())

    mode_response = client.put(f"/__ddmrp_acceptance__/mode/{mode}")
    response = client.get(DDMRP_WORKBENCH_ENDPOINT)

    assert mode_response.status_code == 200
    assert mode_response.json() == {"Mode": mode}
    assert response.status_code == status_code
    assert response.headers["X-Workbench-Revision"] == str(store.current_revision())
    assert deepcopy(store.snapshot_state()) == before

    if mode == "seeded":
        expected = TestClient(create_app(state_store=store)).get(
            DDMRP_WORKBENCH_ENDPOINT
        )
        assert response.json() == expected.json()
        assert response.json()["Data"]["Summary"] == {
            "RedCount": 1,
            "YellowCount": 1,
            "GreenCount": 1,
            "AboveGreenCount": 1,
            "BlockedRecommendationCount": 2,
            "PendingReviewCount": 0,
            "AdjustmentRequiredCount": 0,
            "ActiveGraphCount": 0,
        }
        assert sorted(
            (row["ItemID"], row["LocationID"])
            for row in response.json()["Data"]["Rows"]
        ) == [
            ("TST-DDMRP-RO-ABOVE-GREEN", "TST-MAIN"),
            ("TST-DDMRP-RO-GREEN", "TST-MAIN"),
            ("TST-DDMRP-RO-RED", "TST-MAIN"),
            ("TST-DDMRP-RO-YELLOW", "TST-MAIN"),
        ]
    elif mode == "empty":
        expected_empty = build_ddmrp_replenishment_workbench(
            evaluation_runs={},
            evaluation_rows={},
            chains={},
            recommendations={},
            events=(),
            active_replenishment_graphs={},
        )
        assert response.json() == {
            "Endpoint": DDMRP_WORKBENCH_ENDPOINT,
            "StatusCode": 200,
            "Data": expected_empty,
        }
        assert set(response.json()["Data"]) == _EMPTY_WORKBENCH_KEYS
    else:
        status = {"error": "FixtureError", "403": "Forbidden", "409": "Conflict"}[mode]
        assert response.json() == {
            "Endpoint": DDMRP_WORKBENCH_ENDPOINT,
            "StatusCode": status_code,
            "Data": {
                "Status": status,
                "Message": f"DDMRP acceptance fixture mode: {mode}",
            },
        }

    invalid_response = client.put("/__ddmrp_acceptance__/mode/unsupported")
    assert invalid_response.status_code == 422
    assert invalid_response.json() == {
        "detail": "Unsupported DDMRP acceptance mode."
    }
    assert deepcopy(store.snapshot_state()) == before


def test_ui_ddmrp_003_browser_acceptance_fixture_is_absent_from_production_app(
    tmp_path,
) -> None:
    database_path = tmp_path / "ddmrp-browser-production.db"
    reset_test_database(database_path=database_path)
    fixture_module = _acceptance_fixture_module()
    production_client = TestClient(
        create_app(state_store=SQLiteWorkbenchStateStore(database_path))
    )

    response = production_client.put("/__ddmrp_acceptance__/mode/seeded")

    assert fixture_module.DDMRP_ACCEPTANCE_MODES == frozenset(
        {"seeded", "empty", "error", "403", "409"}
    )
    assert response.status_code == 404
