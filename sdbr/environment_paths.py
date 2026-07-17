from __future__ import annotations

from collections.abc import Mapping
import os
from pathlib import Path


LEGACY_DDAE_INTERFACE_CONTRACT_ROOT = Path(
    r"D:\Documents\DDAE_INTERFACE_CONTRACT"
)


def resolve_ddae_interface_contract_root(
    environ: Mapping[str, str] | None = None,
) -> Path:
    values = os.environ if environ is None else environ
    configured = values.get("DDAE_INTERFACE_CONTRACT_ROOT")
    if configured:
        return Path(configured)
    return LEGACY_DDAE_INTERFACE_CONTRACT_ROOT


def resolve_public_demo_package_root(
    environ: Mapping[str, str] | None = None,
) -> Path:
    values = os.environ if environ is None else environ
    configured = values.get("SDBR_PUBLIC_DEMO_PACKAGE_ROOT")
    if configured:
        return Path(configured)
    return (
        resolve_ddae_interface_contract_root(values)
        / "data"
        / "public-demo-golden-data-v1"
    )
