import tomllib
from pathlib import Path


def test_pyproject_declares_package_metadata_and_pytest_defaults():
    pyproject_path = Path(__file__).resolve().parents[1] / "pyproject.toml"

    data = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))

    assert data["project"]["name"] == "sdbr"
    assert data["project"]["requires-python"] == ">=3.11"
    assert "fastapi>=0.115" in data["project"]["optional-dependencies"]["api"]
    assert "httpx>=0.28" in data["project"]["optional-dependencies"]["api"]
    assert "uvicorn>=0.30" in data["project"]["optional-dependencies"]["api"]
    assert data["tool"]["pytest"]["ini_options"]["testpaths"] == ["tests"]
    assert data["tool"]["pytest"]["ini_options"]["pythonpath"] == ["."]
