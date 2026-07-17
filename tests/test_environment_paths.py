from pathlib import Path

from sdbr.environment_paths import (
    LEGACY_DDAE_INTERFACE_CONTRACT_ROOT,
    resolve_ddae_interface_contract_root,
    resolve_public_demo_package_root,
)


def test_be_run_010_be_int_008_contract_root_uses_environment_override() -> None:
    configured = Path(r"C:\portable\DDAE_INTERFACE_CONTRACT")

    assert resolve_ddae_interface_contract_root(
        {"DDAE_INTERFACE_CONTRACT_ROOT": str(configured)}
    ) == configured


def test_be_run_010_be_int_008_contract_root_keeps_legacy_fallback() -> None:
    assert (
        resolve_ddae_interface_contract_root({})
        == LEGACY_DDAE_INTERFACE_CONTRACT_ROOT
    )


def test_be_int_008_public_demo_root_derives_from_contract_root() -> None:
    contract_root = Path(r"C:\portable\DDAE_INTERFACE_CONTRACT")

    assert resolve_public_demo_package_root(
        {"DDAE_INTERFACE_CONTRACT_ROOT": str(contract_root)}
    ) == contract_root / "data" / "public-demo-golden-data-v1"


def test_be_int_008_public_demo_explicit_override_wins() -> None:
    explicit = Path(r"C:\fixtures\public-demo")

    assert resolve_public_demo_package_root(
        {
            "DDAE_INTERFACE_CONTRACT_ROOT": r"C:\portable\DDAE_INTERFACE_CONTRACT",
            "SDBR_PUBLIC_DEMO_PACKAGE_ROOT": str(explicit),
        }
    ) == explicit
