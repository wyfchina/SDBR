from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
from typing import Literal


EnvironmentID = Literal["test", "production"]


@dataclass(frozen=True, slots=True)
class RuntimeEnvironment:
    environment_id: EnvironmentID
    display_name: str
    display_name_zh: str
    is_production: bool
    default_port: int
    database_path: Path

    @property
    def backup_path(self) -> Path:
        return self.database_path.with_suffix(self.database_path.suffix + ".bak")

    def to_dict(self) -> dict[str, object]:
        return {
            "EnvironmentID": self.environment_id,
            "DisplayName": self.display_name,
            "DisplayNameZh": self.display_name_zh,
            "IsProduction": self.is_production,
            "DefaultPort": self.default_port,
            "DatabasePath": str(self.database_path.resolve()),
            "BackupPath": str(self.backup_path.resolve()),
        }


def resolve_runtime_environment(
    *,
    environment_id: str | None = None,
    database_path: str | Path | None = None,
    project_root: str | Path | None = None,
) -> RuntimeEnvironment:
    raw_environment_id = (
        environment_id or os.environ.get("SDBR_ENVIRONMENT") or "test"
    ).strip().lower()
    if raw_environment_id not in {"test", "production"}:
        raise ValueError(
            "SDBR_ENVIRONMENT must be either 'test' or 'production'."
        )

    root = Path(project_root) if project_root is not None else Path(__file__).resolve().parent.parent
    explicit_database_path = database_path or os.environ.get("SDBR_WORKBENCH_DB_PATH")
    effective_database_path = (
        Path(explicit_database_path)
        if explicit_database_path is not None
        else root / "data" / raw_environment_id / "workbench-state.db"
    )

    if raw_environment_id == "production":
        return RuntimeEnvironment(
            environment_id="production",
            display_name="Production",
            display_name_zh="生产系统",
            is_production=True,
            default_port=8766,
            database_path=effective_database_path,
        )
    return RuntimeEnvironment(
        environment_id="test",
        display_name="Test",
        display_name_zh="测试系统",
        is_production=False,
        default_port=8765,
        database_path=effective_database_path,
    )
