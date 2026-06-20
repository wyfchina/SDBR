from pathlib import Path

from fastapi.testclient import TestClient

from sdbr.api import create_app
from sdbr.runtime_environment import resolve_runtime_environment
from sdbr.state_store import WorkbenchStateStore


def test_resolve_runtime_environment_defaults_to_test_database(tmp_path, monkeypatch):
    monkeypatch.delenv("SDBR_ENVIRONMENT", raising=False)
    monkeypatch.delenv("SDBR_WORKBENCH_DB_PATH", raising=False)

    runtime_environment = resolve_runtime_environment(project_root=tmp_path)

    assert runtime_environment.environment_id == "test"
    assert runtime_environment.display_name_zh == "测试系统"
    assert runtime_environment.default_port == 8765
    assert runtime_environment.database_path == (
        tmp_path / "data" / "test" / "workbench-state.db"
    )


def test_resolve_runtime_environment_uses_production_path(tmp_path):
    runtime_environment = resolve_runtime_environment(
        environment_id="production",
        project_root=tmp_path,
    )

    assert runtime_environment.environment_id == "production"
    assert runtime_environment.display_name_zh == "生产系统"
    assert runtime_environment.default_port == 8766
    assert runtime_environment.is_production is True
    assert runtime_environment.database_path == (
        tmp_path / "data" / "production" / "workbench-state.db"
    )


def test_create_app_exposes_runtime_environment_metadata(tmp_path):
    runtime_environment = resolve_runtime_environment(
        environment_id="test",
        database_path=Path(tmp_path / "test.db"),
    )
    client = TestClient(
        create_app(
            state_store=WorkbenchStateStore(),
            runtime_environment=runtime_environment,
        )
    )

    response = client.get("/planner/workbench/environment")

    assert response.status_code == 200
    assert response.headers["X-SDBR-Environment"] == "test"
    data = response.json()["Data"]
    assert data["EnvironmentID"] == "test"
    assert data["DisplayNameZh"] == "测试系统"
    assert data["DatabasePath"].endswith("test.db")


def test_state_store_health_includes_runtime_environment(tmp_path):
    runtime_environment = resolve_runtime_environment(
        environment_id="production",
        database_path=Path(tmp_path / "production.db"),
    )
    client = TestClient(
        create_app(
            state_store=WorkbenchStateStore(),
            runtime_environment=runtime_environment,
        )
    )

    response = client.get("/planner/workbench/state-store/health")

    assert response.status_code == 200
    assert response.headers["X-SDBR-Environment"] == "production"
    assert response.json()["Data"]["Environment"]["EnvironmentID"] == "production"
