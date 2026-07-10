# MTO/MTA Shared Planning Reservation Phase 0 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the shared demand identity, CCR capacity reservation, material planning allocation, persistence, projection, and Planning Run conversion foundation used by both MTO order commitment and MTA/DDMRP replenishment flows.

**Architecture:** Keep business rules in small pure Python modules and use the existing `WorkbenchStateStore` / `SQLiteWorkbenchStateStore` JSON persistence model with revision-based optimistic concurrency. Phase 0 exposes no new UI and implements neither MTO shadow scheduling nor DDMRP replenishment algorithms; later workflows must call this shared foundation instead of creating private reservation ledgers.

**Tech Stack:** Python 3.12, FastAPI/Pydantic, dataclasses, existing in-memory/SQLite workbench state store, pytest.

## Global Constraints

- SDBR remains a DDOM / S-DBR execution system only.
- Do not implement DDS&OP workflows, DDAE master-setting governance, Buffer Profile governance, or strategic scenario governance.
- Do not add implicit DDAE or ERP fields. Contract gaps must be reported through the Contract Agent path.
- Do not implement MTO shadow scheduling, DDMRP net-flow changes, BOM explosion, replenishment recommendation lifecycle, ERP order creation, or UI panels in Phase 0.
- The shared foundation must not mutate ERP/WMS inventory accounting or claim formal production authority.
- OR-Tools CP-SAT remains the only active solver; Phase 0 does not change solver behavior.
- Planning reservations are date/shift or capacity-window commitments, not exact operation sequencing.
- A demand, capacity reservation, or material allocation must never be counted twice after Planning Run or ERP/WMS authority handoff.
- `docs/backend-specification.md` is authoritative and must be updated before implementation code.
- Do not expose raw JSON master data in planner UI.
- Do not track or modify `nofinish/`.
- The current worktree has pre-existing P2/What-if changes. Before Task 1 execution, verify and commit those changes separately or establish a clean execution baseline without reverting them. Never mix them into Phase 0 commits.

---

## File Structure

- Create `sdbr/planning_commitments.py`
  - Stable demand identity, source classification, fingerprints, idempotent registration, and predecessor-version guards.
- Create `sdbr/planning_reservations.py`
  - Planning confirmation batches, CCR reservations, material planning allocations, write sets, validation, and in-memory atomic application.
- Create `sdbr/planning_reservation_view.py`
  - Active reservation projection into CCR Planned Load and uncommitted material availability.
- Create `sdbr/planning_run_reservation_bridge.py`
  - Reservation batch validation, Planning Run freeze snapshot, and Completed/Failed/DeadLetter transitions.
- Modify `sdbr/state_store.py`
  - Persist six shared collections and expose health counts.
- Modify `sdbr/sdbr_market_control.py`
  - Add optional shared capacity reservations to the existing CCR Planned Load read model without changing callers that pass none.
- Modify `sdbr/api.py`
  - Add optional `PlanningReservationBatchIDs`, freeze validated batches into Planning Run, transition them after execution, and expose a read-only reservation workbench endpoint.
- Create `tests/test_planning_commitments.py`
  - Demand identity, idempotency, conflict, and version tests.
- Create `tests/test_planning_reservations.py`
  - Confirmation write-set, atomicity, allocation, and duplicate tests.
- Create `tests/test_planning_reservation_view.py`
  - Planned Load and material de-duplication tests.
- Create `tests/test_planning_run_reservation_bridge.py`
  - Freeze, conversion, failure hold, and release-state tests.
- Modify `tests/test_state_store.py`
  - SQLite round-trip and health-count evidence for all shared collections.
- Modify `tests/test_sdbr_market_control.py`
  - Shared MTO/MTA reservation load projection and converted-reservation exclusion.
- Modify `tests/test_api.py`
  - Planning Run reference validation, freeze, conversion, and read-only API behavior.
- Modify `docs/backend-specification.md`
  - Add Phase 0 capability IDs and dated change log evidence.

---

### Task 1: Specification First

**Files:**
- Modify: `docs/backend-specification.md`

**Interfaces:**
- Consumes: `BE-SDBR-001` through `BE-SDBR-005`, `BE-DDMRP-001` through `BE-DDMRP-006`, `BE-RUN-001`, `BE-RUN-007`, `BE-RUN-008`.
- Produces: `BE-SDBR-006` through `BE-SDBR-009` and `BE-RUN-011` acceptance targets used in tests and reports.

- [ ] **Step 1: Add the Phase 0 capability rows**

Add these rows after `BE-SDBR-005`:

```markdown
| `BE-SDBR-006` | Shared demand commitment identity | `[PARTIAL]` | `C` `sdbr/planning_commitments.py`; `T` `tests/test_planning_commitments.py` | MTO、MTA、DependentDemand 和外部正式订单使用统一需求身份、版本、幂等键和来源分类；相同业务键不得产生两个活动承诺 |
| `BE-SDBR-007` | Atomic planning reservation batch | `[PARTIAL]` | `C` `sdbr/planning_reservations.py`; `T` `tests/test_planning_reservations.py` | 计划员确认产生的候选、CCR 容量预留和物料计划分配全部成功或全部失败；Phase 0 不提供独立确认 UI |
| `BE-SDBR-008` | Shared CCR capacity reservation ledger | `[PARTIAL]` | `C` `sdbr/planning_reservations.py`, `sdbr/planning_reservation_view.py`; `T` `tests/test_planning_reservations.py`, `tests/test_planning_reservation_view.py`, `tests/test_sdbr_market_control.py` | MTO/MTA 使用同一负荷台账；正式工序转正后不得重复计入 Planned Load |
| `BE-SDBR-009` | Shared material planning allocation ledger | `[PARTIAL]` | `C` `sdbr/planning_reservations.py`, `sdbr/planning_reservation_view.py`; `T` `tests/test_planning_reservations.py`, `tests/test_planning_reservation_view.py` | 计划分配防止其他需求重复使用供应，但不得把同一需求再次扣减净流；ERP/WMS 权威分配接管后停止额外扣减 |
```

Add this row after `BE-RUN-010`:

```markdown
| `BE-RUN-011` | Planning Run freezes and converts planning reservations | `[PARTIAL]` | `C` `sdbr/planning_run_reservation_bridge.py`, `sdbr/api.py`; `T` `tests/test_planning_run_reservation_bridge.py`, `tests/test_api.py` | Planning Run 显式冻结有效批次；Completed 转正式工序占用，Failed/DeadLetter 保留并标记异常，Queued 重试不提前转状态 |
```

- [ ] **Step 2: Add a dated Phase 0 acceptance note**

Add before the backend change log:

```markdown
### BE-SDBR-006 至 BE-SDBR-009 / BE-RUN-011 共享计划预留阶段 0

- 日期：2026-07-10
- 范围：统一 MTO/MTA 需求身份、CCR 计划级容量预留、物料计划分配、状态存储、Planning Run 冻结与转正。
- 核心不变量：需求只计一次；计划预留转正式工序后不重复计负荷；权威物料分配接管后不重复扣减；确认批次原子写入；重放不产生重复对象。
- 边界：不实现 MTO 影子排程、DDMRP 新算法、BOM 展开、ERP 正式订单创建或 UI 页面。
- 状态：`[PARTIAL]`，待实现与重复测试证据。
```

- [ ] **Step 3: Add the next backend changelog row**

Add backend changelog row `2.73` exactly as follows:

```markdown
| 2.73 | 2026-07-10 | 启动 MTO/MTA 共享计划预留阶段 0：统一需求身份、CCR 预留、物料计划分配、Planning Run 转正和事件幂等，避免订单承诺与 DDMRP 补货重复占用能力和物料 |
```

- [ ] **Step 4: Verify specification text**

Run:

```powershell
rg -n "BE-SDBR-006|BE-SDBR-007|BE-SDBR-008|BE-SDBR-009|BE-RUN-011" docs/backend-specification.md
```

Expected: all five capability IDs and the dated note are present.

- [ ] **Step 5: Commit specification change**

```powershell
git add -- docs/backend-specification.md
git commit -m "docs: specify shared planning reservation foundation"
```

---

### Task 2: Stable Demand Commitment Identity

**Files:**
- Create: `sdbr/planning_commitments.py`
- Create: `tests/test_planning_commitments.py`

**Interfaces:**
- Produces:
  - `DemandCommitmentConflict(ValueError)`
  - `create_demand_commitment(...) -> dict[str, object]`
  - `register_demand_commitment(commitments, candidate) -> tuple[str, dict[str, object]]`
  - `assert_no_active_predecessor(commitments, candidate) -> None`
  - `ACTIVE_DEMAND_STATUSES`
- Consumes: no store, API, solver, or UI dependencies.

- [ ] **Step 1: Write failing identity and idempotency tests**

Create `tests/test_planning_commitments.py`:

```python
from datetime import datetime, timezone

import pytest

from sdbr.planning_commitments import (
    DemandCommitmentConflict,
    assert_no_active_predecessor,
    create_demand_commitment,
    register_demand_commitment,
)


def _commitment(*, version: str = "1", quantity: float = 10) -> dict[str, object]:
    return create_demand_commitment(
        demand_source_type="MTOCustomerOrder",
        source_system="MockERP",
        source_object_type="CustomerOrder",
        source_object_id="SO-100",
        source_object_version=version,
        demand_line_id="10",
        item_or_product_id="FG-1",
        location_id="MAIN",
        quantity=quantity,
        uom="EA",
        required_at=datetime(2026, 7, 20, 8, tzinfo=timezone.utc),
        demand_class="MTO",
        trace_id="TRACE-SO-100-10",
    )


def test_register_same_business_key_and_content_is_idempotent():
    candidate = _commitment()
    status, first = register_demand_commitment({}, candidate)
    status_again, duplicate = register_demand_commitment(
        {str(first["DemandCommitmentID"]): first}, candidate
    )
    assert status == "Created"
    assert status_again == "Duplicate"
    assert duplicate == first


def test_same_business_key_and_version_with_changed_content_is_conflict():
    existing = _commitment(quantity=10)
    with pytest.raises(DemandCommitmentConflict, match="same business key"):
        register_demand_commitment(
            {str(existing["DemandCommitmentID"]): existing},
            _commitment(quantity=12),
        )


def test_new_version_cannot_activate_while_predecessor_is_active():
    active = {**_commitment(version="1"), "Status": "Active"}
    with pytest.raises(DemandCommitmentConflict, match="active predecessor"):
        assert_no_active_predecessor(
            {str(active["DemandCommitmentID"]): active},
            _commitment(version="2"),
        )
```

- [ ] **Step 2: Run tests and verify they fail**

Run:

```powershell
pytest tests/test_planning_commitments.py -q --basetemp .tmp/pytest-planning-commitments-red -p no:cacheprovider
```

Expected: collection fails because `sdbr.planning_commitments` does not exist.

- [ ] **Step 3: Implement deterministic identity and registration**

Create `sdbr/planning_commitments.py` with:

```python
from __future__ import annotations

from datetime import datetime
from hashlib import sha256
import json
from typing import Mapping


DEMAND_SOURCE_TYPES = {
    "MTOCustomerOrder",
    "MTAReplenishment",
    "DependentDemand",
    "ExternalFormalOrder",
    "Adjustment",
}
ACTIVE_DEMAND_STATUSES = {
    "Active",
    "LinkedToFormalOrder",
    "HeldForPlanningError",
}


class DemandCommitmentConflict(ValueError):
    pass


def create_demand_commitment(
    *,
    demand_source_type: str,
    source_system: str,
    source_object_type: str,
    source_object_id: str,
    source_object_version: str,
    demand_line_id: str,
    item_or_product_id: str,
    location_id: str,
    quantity: float,
    uom: str,
    required_at: datetime,
    demand_class: str,
    trace_id: str,
) -> dict[str, object]:
    if demand_source_type not in DEMAND_SOURCE_TYPES:
        raise ValueError(f"Unsupported demand source type: {demand_source_type}.")
    if quantity <= 0:
        raise ValueError("Demand commitment quantity must be positive.")
    if required_at.tzinfo is None or required_at.utcoffset() is None:
        raise ValueError("Demand commitment required time must be timezone-aware.")
    business_key = "|".join(
        (
            source_system,
            source_object_type,
            source_object_id,
            source_object_version,
            demand_line_id,
            item_or_product_id,
            location_id,
        )
    )
    content = {
        "DemandSourceType": demand_source_type,
        "SourceSystem": source_system,
        "SourceObjectType": source_object_type,
        "SourceObjectID": source_object_id,
        "SourceObjectVersion": source_object_version,
        "DemandLineID": demand_line_id,
        "ItemOrProductID": item_or_product_id,
        "LocationID": location_id,
        "Quantity": float(quantity),
        "Uom": uom,
        "RequiredAt": required_at.isoformat(),
        "DemandClass": demand_class,
        "TraceID": trace_id,
    }
    fingerprint = sha256(
        json.dumps(content, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return {
        "DemandCommitmentID": f"DC-{sha256(business_key.encode('utf-8')).hexdigest()[:20]}",
        "BusinessKey": business_key,
        "LogicalDemandKey": "|".join(
            (
                source_system,
                source_object_type,
                source_object_id,
                demand_line_id,
                item_or_product_id,
                location_id,
            )
        ),
        "ContentFingerprint": f"sha256:{fingerprint}",
        "Status": "PendingConfirmation",
        **content,
    }


def register_demand_commitment(
    commitments: Mapping[str, dict[str, object]],
    candidate: dict[str, object],
) -> tuple[str, dict[str, object]]:
    for existing in commitments.values():
        if existing.get("BusinessKey") != candidate.get("BusinessKey"):
            continue
        if existing.get("ContentFingerprint") == candidate.get("ContentFingerprint"):
            return "Duplicate", dict(existing)
        raise DemandCommitmentConflict(
            "Demand commitment with the same business key has different content."
        )
    return "Created", dict(candidate)


def assert_no_active_predecessor(
    commitments: Mapping[str, dict[str, object]],
    candidate: dict[str, object],
) -> None:
    for existing in commitments.values():
        if (
            existing.get("LogicalDemandKey") == candidate.get("LogicalDemandKey")
            and existing.get("BusinessKey") != candidate.get("BusinessKey")
            and existing.get("Status") in ACTIVE_DEMAND_STATUSES
        ):
            raise DemandCommitmentConflict(
                "New demand version cannot activate while an active predecessor exists."
            )
```

- [ ] **Step 4: Run unit tests**

```powershell
pytest tests/test_planning_commitments.py -q --basetemp .tmp/pytest-planning-commitments-green -p no:cacheprovider
```

Expected: `3 passed`.

- [ ] **Step 5: Commit demand identity**

```powershell
git add -- sdbr/planning_commitments.py tests/test_planning_commitments.py
git commit -m "feat: add shared demand commitment identity"
```

---

### Task 3: Atomic Reservation Write Set

**Files:**
- Create: `sdbr/planning_reservations.py`
- Create: `tests/test_planning_reservations.py`

**Interfaces:**
- Consumes: demand records from `create_demand_commitment`.
- Produces:
  - `PlanningReservationWriteSet`
  - `ReservationConflict(ValueError)`
  - `prepare_reservation_confirmation(...) -> PlanningReservationWriteSet`
  - `apply_reservation_write_set(...) -> None`
  - `ACTIVE_CAPACITY_RESERVATION_STATUSES`
  - `ACTIVE_MATERIAL_ALLOCATION_STATUSES`

- [ ] **Step 1: Write failing tests for atomic write-set and idempotency**

Create `tests/test_planning_reservations.py`:

```python
from datetime import datetime, timezone

import pytest

from sdbr.planning_commitments import create_demand_commitment
from sdbr.planning_reservations import (
    ReservationConflict,
    apply_reservation_write_set,
    prepare_reservation_confirmation,
)


def _demand() -> dict[str, object]:
    return create_demand_commitment(
        demand_source_type="MTAReplenishment",
        source_system="SDBR",
        source_object_type="ReplenishmentRecommendation",
        source_object_id="REC-1",
        source_object_version="1",
        demand_line_id="1",
        item_or_product_id="FG-1",
        location_id="MAIN",
        quantity=10,
        uom="EA",
        required_at=datetime(2026, 7, 20, 8, tzinfo=timezone.utc),
        demand_class="MTA",
        trace_id="TRACE-REC-1",
    )


def test_prepare_and_apply_confirmation_writes_batch_capacity_material_and_event():
    demand = _demand()
    write_set = prepare_reservation_confirmation(
        demand_commitment=demand,
        existing_commitments={},
        confirmation_id="CONFIRM-1",
        confirmed_by="planner-1",
        confirmed_at=datetime(2026, 7, 10, 8, tzinfo=timezone.utc),
        capacity_requests=[{
            "ResourceID": "CCR-1",
            "WindowStartAt": "2026-07-20T08:00:00+00:00",
            "WindowEndAt": "2026-07-20T16:00:00+00:00",
            "ReservedMinutes": 120,
            "LatestAllowedCompletionAt": "2026-07-20T16:00:00+00:00",
        }],
        material_requests=[{
            "RequirementLineID": "REQ-1",
            "ItemID": "RM-1",
            "LocationID": "MAIN",
            "Uom": "EA",
            "AllocatedQty": 20,
            "SupplySourceType": "OnHand",
            "MaterialSnapshotID": "OPS-1",
        }],
    )
    commitments: dict[str, dict[str, object]] = {}
    batches: dict[str, dict[str, object]] = {}
    capacities: dict[str, dict[str, object]] = {}
    allocations: dict[str, dict[str, object]] = {}
    events: list[dict[str, object]] = []
    keys: set[str] = set()
    apply_reservation_write_set(
        write_set=write_set,
        commitments=commitments,
        batches=batches,
        capacity_reservations=capacities,
        material_allocations=allocations,
        events=events,
        processed_event_keys=keys,
    )
    assert len(commitments) == len(batches) == len(capacities) == len(allocations) == 1
    assert events[0]["EventType"] == "PlanningReservationActivated"
    assert write_set.idempotency_key in keys


def test_duplicate_confirmation_does_not_create_second_batch():
    write_set = prepare_reservation_confirmation(
        demand_commitment=_demand(),
        existing_commitments={},
        confirmation_id="CONFIRM-1",
        confirmed_by="planner-1",
        confirmed_at=datetime(2026, 7, 10, 8, tzinfo=timezone.utc),
        capacity_requests=[],
        material_requests=[],
    )
    collections = ({}, {}, {}, {}, [], set())
    apply_reservation_write_set(
        write_set=write_set,
        commitments=collections[0], batches=collections[1],
        capacity_reservations=collections[2], material_allocations=collections[3],
        events=collections[4], processed_event_keys=collections[5],
    )
    apply_reservation_write_set(
        write_set=write_set,
        commitments=collections[0], batches=collections[1],
        capacity_reservations=collections[2], material_allocations=collections[3],
        events=collections[4], processed_event_keys=collections[5],
    )
    assert len(collections[1]) == 1
    assert len(collections[4]) == 1


def test_invalid_capacity_request_builds_no_partial_write_set():
    with pytest.raises(ReservationConflict, match="positive reserved minutes"):
        prepare_reservation_confirmation(
            demand_commitment=_demand(),
            existing_commitments={},
            confirmation_id="CONFIRM-INVALID",
            confirmed_by="planner-1",
            confirmed_at=datetime(2026, 7, 10, 8, tzinfo=timezone.utc),
            capacity_requests=[{
                "ResourceID": "CCR-1",
                "WindowStartAt": "2026-07-20T08:00:00+00:00",
                "WindowEndAt": "2026-07-20T16:00:00+00:00",
                "ReservedMinutes": 0,
            }],
            material_requests=[],
        )
```

- [ ] **Step 2: Run tests and verify they fail**

```powershell
pytest tests/test_planning_reservations.py -q --basetemp .tmp/pytest-planning-reservations-red -p no:cacheprovider
```

Expected: collection fails because `sdbr.planning_reservations` does not exist.

- [ ] **Step 3: Implement write-set preparation and application**

Create `sdbr/planning_reservations.py`. Use deterministic IDs derived from `confirmation_id`, validate every request before constructing the write set, and expose this exact dataclass:

```python
from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
from typing import Iterable, Mapping, MutableMapping, MutableSequence, MutableSet

from sdbr.planning_commitments import assert_no_active_predecessor


ACTIVE_CAPACITY_RESERVATION_STATUSES = {
    "ActivePlanReservation", "LinkedToFormalOrder", "HeldForPlanningError"
}
ACTIVE_MATERIAL_ALLOCATION_STATUSES = {
    "ActivePlanReservation", "LinkedToFormalOrder", "HeldForPlanningError"
}


class ReservationConflict(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class PlanningReservationWriteSet:
    idempotency_key: str
    demand_commitment: dict[str, object]
    batch: dict[str, object]
    capacity_reservations: tuple[dict[str, object], ...]
    material_allocations: tuple[dict[str, object], ...]
    events: tuple[dict[str, object], ...]


def _stable_id(prefix: str, value: str) -> str:
    return f"{prefix}-{sha256(value.encode('utf-8')).hexdigest()[:20]}"


def prepare_reservation_confirmation(
    *,
    demand_commitment: dict[str, object],
    existing_commitments: Mapping[str, dict[str, object]],
    confirmation_id: str,
    confirmed_by: str,
    confirmed_at: datetime,
    capacity_requests: Iterable[Mapping[str, object]],
    material_requests: Iterable[Mapping[str, object]],
) -> PlanningReservationWriteSet:
    demand_id = str(demand_commitment.get("DemandCommitmentID") or "")
    if not demand_id:
        raise ReservationConflict("Demand commitment ID is required.")
    if demand_commitment.get("Status") != "PendingConfirmation":
        raise ReservationConflict("Demand commitment must await confirmation.")
    if confirmed_at.tzinfo is None or confirmed_at.utcoffset() is None:
        raise ReservationConflict("Confirmation time must be timezone-aware.")
    assert_no_active_predecessor(existing_commitments, demand_commitment)

    capacity_rows = tuple(dict(row) for row in capacity_requests)
    material_rows = tuple(dict(row) for row in material_requests)
    for row in capacity_rows:
        if float(row.get("ReservedMinutes") or 0) <= 0:
            raise ReservationConflict("Capacity request must have positive reserved minutes.")
        if not row.get("ResourceID") or not row.get("WindowStartAt") or not row.get("WindowEndAt"):
            raise ReservationConflict("Capacity request resource and window are required.")
    for row in material_rows:
        if float(row.get("AllocatedQty") or 0) <= 0:
            raise ReservationConflict("Material request must have positive allocated quantity.")
        if not row.get("RequirementLineID") or not row.get("ItemID") or not row.get("LocationID"):
            raise ReservationConflict("Material request identity is required.")

    batch_id = _stable_id("PRB", confirmation_id)
    capacity_records = tuple(
        {
            "CapacityReservationID": _stable_id(
                "CCR",
                f"{confirmation_id}|{index}|{row['ResourceID']}|{row['WindowStartAt']}",
            ),
            "ReservationBatchID": batch_id,
            "DemandCommitmentID": demand_id,
            "DemandClass": demand_commitment["DemandClass"],
            "Status": "ActivePlanReservation",
            **row,
        }
        for index, row in enumerate(capacity_rows, start=1)
    )
    material_records = tuple(
        {
            "MaterialAllocationID": _stable_id(
                "MPA",
                f"{confirmation_id}|{index}|{row['RequirementLineID']}",
            ),
            "ReservationBatchID": batch_id,
            "DemandCommitmentID": demand_id,
            "DemandClass": demand_commitment["DemandClass"],
            "Status": "ActivePlanReservation",
            **row,
        }
        for index, row in enumerate(material_rows, start=1)
    )
    activated_demand = {
        **demand_commitment,
        "Status": "Active",
        "ConfirmedBy": confirmed_by,
        "ConfirmedAt": confirmed_at.isoformat(),
    }
    batch = {
        "ReservationBatchID": batch_id,
        "DemandCommitmentID": demand_id,
        "DemandClass": demand_commitment["DemandClass"],
        "Status": "ActivePlanReservation",
        "ConfirmationID": confirmation_id,
        "ConfirmedBy": confirmed_by,
        "ConfirmedAt": confirmed_at.isoformat(),
        "CapacityReservationIDs": [
            row["CapacityReservationID"] for row in capacity_records
        ],
        "MaterialAllocationIDs": [
            row["MaterialAllocationID"] for row in material_records
        ],
    }
    idempotency_key = f"PlanningReservationActivated:{confirmation_id}"
    event = {
        "EventID": _stable_id("PRE", idempotency_key),
        "EventType": "PlanningReservationActivated",
        "DemandCommitmentID": demand_id,
        "ReservationBatchID": batch_id,
        "OccurredAt": confirmed_at.isoformat(),
        "ActorID": confirmed_by,
        "IdempotencyKey": idempotency_key,
        "TraceID": demand_commitment["TraceID"],
    }
    return PlanningReservationWriteSet(
        idempotency_key=idempotency_key,
        demand_commitment=activated_demand,
        batch=batch,
        capacity_reservations=capacity_records,
        material_allocations=material_records,
        events=(event,),
    )
```

`prepare_reservation_confirmation` must:

- require an existing `DemandCommitmentID` and `PendingConfirmation` status;
- call `assert_no_active_predecessor(existing_commitments, demand_commitment)` after identity/status validation and before constructing any reservation record;
- reject non-positive reservation minutes or quantities;
- require timezone-aware `confirmed_at`;
- create one batch with `ActivePlanReservation` status;
- copy the demand to `Active` status;
- create capacity and allocation records with `DemandClass` and `DemandCommitmentID`;
- create one `PlanningReservationActivated` event;
- return no mutations before all validation passes.

`apply_reservation_write_set` must first return immediately when the idempotency key is already in `processed_event_keys`; otherwise it must update the five collections and add the key only after all duplicate-ID checks pass. Raise `ReservationConflict` before mutation if any target ID already exists with different content.

- [ ] **Step 4: Run unit tests**

```powershell
pytest tests/test_planning_reservations.py -q --basetemp .tmp/pytest-planning-reservations-green -p no:cacheprovider
```

Expected: `3 passed`.

- [ ] **Step 5: Commit reservation core**

```powershell
git add -- sdbr/planning_reservations.py tests/test_planning_reservations.py
git commit -m "feat: add atomic shared planning reservations"
```

---

### Task 4: Persist Shared Collections

**Files:**
- Modify: `sdbr/state_store.py`
- Modify: `tests/test_state_store.py`

**Interfaces:**
- Consumes: dictionary/list/set records from Tasks 2 and 3.
- Produces: six durable state collections and health counts.

- [ ] **Step 1: Extend the SQLite round-trip test with all collections**

In `test_sqlite_state_store_round_trips_all_state_collections`, add:

```python
    store.planning_demand_commitments["DC-1"] = {
        "DemandCommitmentID": "DC-1", "Status": "Active"
    }
    store.planning_reservation_batches["PRB-1"] = {
        "ReservationBatchID": "PRB-1", "Status": "ActivePlanReservation"
    }
    store.ccr_capacity_reservations["CCR-RES-1"] = {
        "CapacityReservationID": "CCR-RES-1", "ReservedMinutes": 60
    }
    store.material_planning_allocations["MPA-1"] = {
        "MaterialPlanningAllocationID": "MPA-1", "AllocatedQty": 5
    }
    store.planning_reservation_events.append({"EventID": "PRE-1"})
    store.processed_planning_event_keys.add("CONFIRM-1")
```

After restore, assert equality for all six collections and add health assertions:

```python
    assert restored.planning_demand_commitments == store.planning_demand_commitments
    assert restored.planning_reservation_batches == store.planning_reservation_batches
    assert restored.ccr_capacity_reservations == store.ccr_capacity_reservations
    assert restored.material_planning_allocations == store.material_planning_allocations
    assert restored.planning_reservation_events == store.planning_reservation_events
    assert restored.processed_planning_event_keys == store.processed_planning_event_keys
    assert restored.health()["StateCounts"]["PlanningReservationBatches"] == 1
```

- [ ] **Step 2: Run the round-trip test and verify it fails**

```powershell
pytest tests/test_state_store.py::test_sqlite_state_store_round_trips_all_state_collections -q --basetemp .tmp/pytest-state-reservations-red -p no:cacheprovider
```

Expected: FAIL because the new store attributes do not exist.

- [ ] **Step 3: Add collections to both state stores**

Add these dataclass fields to `WorkbenchStateStore`:

```python
    planning_demand_commitments: dict[str, dict[str, object]] = field(default_factory=dict)
    planning_reservation_batches: dict[str, dict[str, object]] = field(default_factory=dict)
    ccr_capacity_reservations: dict[str, dict[str, object]] = field(default_factory=dict)
    material_planning_allocations: dict[str, dict[str, object]] = field(default_factory=dict)
    planning_reservation_events: list[dict[str, object]] = field(default_factory=list)
    processed_planning_event_keys: set[str] = field(default_factory=set)
```

Add all six to `SQLiteWorkbenchStateStore.save()` payloads. Serialize the set as `sorted(self.processed_planning_event_keys)`. Add matching `_load()`, `_clear()`, and `_state_counts()` handling. Keep `SCHEMA_VERSION = 1` because the SQLite relational schema is unchanged and missing JSON state keys already default safely.

- [ ] **Step 4: Run state-store tests**

```powershell
pytest tests/test_state_store.py tests/test_backend_readiness.py -q --basetemp .tmp/pytest-state-reservations-green -p no:cacheprovider
```

Expected: all tests pass.

- [ ] **Step 5: Commit persistence**

```powershell
git add -- sdbr/state_store.py tests/test_state_store.py
git commit -m "feat: persist shared planning reservation state"
```

---

### Task 5: Shared Capacity and Material Projections

**Files:**
- Create: `sdbr/planning_reservation_view.py`
- Create: `tests/test_planning_reservation_view.py`
- Modify: `sdbr/sdbr_market_control.py`
- Modify: `tests/test_sdbr_market_control.py`

**Interfaces:**
- Consumes: shared capacity reservation and material allocation dictionaries.
- Produces:
  - `reservation_load_by_bucket(...) -> dict[tuple[str, str], dict[str, object]]`
  - `planning_allocated_qty_for_other_demands(...) -> float`
  - `uncommitted_supply_qty(...) -> float`
  - optional `capacity_reservations` input on `build_ccr_planned_load`.

- [ ] **Step 1: Write failing projection tests**

Create `tests/test_planning_reservation_view.py`:

```python
from sdbr.planning_reservation_view import (
    planning_allocated_qty_for_other_demands,
    reservation_load_by_bucket,
    uncommitted_supply_qty,
)


def test_active_reservations_count_but_converted_reservations_do_not():
    result = reservation_load_by_bucket([
        {
            "CapacityReservationID": "R-1", "ResourceID": "CCR-1",
            "WindowStartAt": "2026-07-20T08:00:00+00:00",
            "ReservedMinutes": 60, "DemandClass": "MTO",
            "Status": "ActivePlanReservation",
        },
        {
            "CapacityReservationID": "R-2", "ResourceID": "CCR-1",
            "WindowStartAt": "2026-07-20T10:00:00+00:00",
            "ReservedMinutes": 90, "DemandClass": "MTA",
            "Status": "ConvertedToScheduledOccupancy",
        },
    ])
    assert result[("CCR-1", "2026-07-20")]["MtoReservationMinutes"] == 60
    assert result[("CCR-1", "2026-07-20")]["MtaReservationMinutes"] == 0


def test_material_projection_excludes_current_demand_and_externalized_allocation():
    allocations = [
        {"ItemID": "RM-1", "LocationID": "MAIN", "DemandCommitmentID": "DC-A",
         "AllocatedQty": 5, "Status": "ActivePlanReservation"},
        {"ItemID": "RM-1", "LocationID": "MAIN", "DemandCommitmentID": "DC-B",
         "AllocatedQty": 7, "Status": "ActivePlanReservation"},
        {"ItemID": "RM-1", "LocationID": "MAIN", "DemandCommitmentID": "DC-C",
         "AllocatedQty": 11, "Status": "Externalized"},
    ]
    assert planning_allocated_qty_for_other_demands(
        allocations=allocations, item_id="RM-1", location_id="MAIN",
        current_demand_commitment_id="DC-A",
    ) == 7
    assert uncommitted_supply_qty(
        qualified_supply_qty=20, authority_allocated_qty=3,
        allocations=allocations, item_id="RM-1", location_id="MAIN",
        current_demand_commitment_id="DC-A",
    ) == 10
```

- [ ] **Step 2: Write failing CCR Planned Load integration test**

Add to `tests/test_sdbr_market_control.py`:

```python
def test_ccr_planned_load_adds_unconverted_shared_reservations_once():
    result = build_ccr_planned_load(
        gantt_rows=[],
        resources=[{
            "ResourceID": "CCR-1", "Name": "Constraint", "IsConstraint": True,
            "DailyCapacityMinutes": {"2026-07-20": 480},
        }],
        orders=[], ddmrp_lines=[],
        horizon_start=datetime(2026, 7, 20, tzinfo=timezone.utc),
        capacity_reservations=[{
            "CapacityReservationID": "R-1", "ResourceID": "CCR-1",
            "WindowStartAt": "2026-07-20T08:00:00+00:00",
            "ReservedMinutes": 120, "DemandClass": "MTA",
            "Status": "ActivePlanReservation",
        }],
    )
    bucket = result["Buckets"][0]
    assert bucket["MtaLoadMinutes"] == 120
    assert bucket["ReservationLoadMinutes"] == 120
    assert bucket["TotalPlannedLoadMinutes"] == 120
    assert bucket["LoadPercent"] == 25.0
```

- [ ] **Step 3: Run projection tests and verify they fail**

```powershell
pytest tests/test_planning_reservation_view.py tests/test_sdbr_market_control.py -q --basetemp .tmp/pytest-reservation-view-red -p no:cacheprovider
```

Expected: new module or function arguments are missing.

- [ ] **Step 4: Implement projection functions**

Create `sdbr/planning_reservation_view.py`. Parse `WindowStartAt` with `datetime.fromisoformat`, count only capacity statuses `ActivePlanReservation`, `LinkedToFormalOrder`, and `HeldForPlanningError`, and count only material allocation statuses with the same names. Exclude `Externalized`, `Released`, `Cancelled`, and `ConvertedToScheduledOccupancy`.

Modify `build_ccr_planned_load` to accept:

```python
    capacity_reservations: list[dict[str, object]] | None = None,
```

After scheduled bars are accumulated and before bucket totals/statuses are calculated, merge `reservation_load_by_bucket(capacity_reservations or [])`. Add `ReservationLoadMinutes` to every bucket, add MTO/MTA reservation minutes to the corresponding demand-class load, then calculate total and percentage once.

- [ ] **Step 5: Run projection tests**

```powershell
pytest tests/test_planning_reservation_view.py tests/test_sdbr_market_control.py -q --basetemp .tmp/pytest-reservation-view-green -p no:cacheprovider
```

Expected: all tests pass.

- [ ] **Step 6: Commit projections**

```powershell
git add -- sdbr/planning_reservation_view.py sdbr/sdbr_market_control.py tests/test_planning_reservation_view.py tests/test_sdbr_market_control.py
git commit -m "feat: project shared reservations into planning load"
```

---

### Task 6: Planning Run Reservation Bridge

**Files:**
- Create: `sdbr/planning_run_reservation_bridge.py`
- Create: `tests/test_planning_run_reservation_bridge.py`

**Interfaces:**
- Produces:
  - `ReservationBatchReferenceError(ValueError)`
  - `freeze_planning_reservations(...) -> dict[str, object]`
  - `transition_planning_reservations_for_run(...) -> dict[str, dict[str, dict[str, object]]]`
- Consumes: store collection snapshots and explicit batch IDs.

- [ ] **Step 1: Write failing freeze and transition tests**

Create `tests/test_planning_run_reservation_bridge.py` with fixtures for one batch, one capacity reservation, and one material allocation. Assert:

```python
def test_freeze_copies_only_explicit_eligible_batches():
    frozen = freeze_planning_reservations(
        batch_ids=["PRB-1"],
        batches={"PRB-1": {"ReservationBatchID": "PRB-1", "Status": "ActivePlanReservation"}},
        capacity_reservations={"R-1": {"CapacityReservationID": "R-1", "ReservationBatchID": "PRB-1", "Status": "ActivePlanReservation"}},
        material_allocations={"A-1": {"MaterialPlanningAllocationID": "A-1", "ReservationBatchID": "PRB-1", "Status": "ActivePlanReservation"}},
    )
    assert frozen["ReservationBatchIDs"] == ["PRB-1"]
    assert frozen["Batches"][0]["ReservationBatchID"] == "PRB-1"
    assert frozen["CapacityReservations"][0]["CapacityReservationID"] == "R-1"


def test_completed_run_converts_capacity_but_keeps_material_until_authority_handoff():
    result = transition_planning_reservations_for_run(
        run_id="RUN-1", run_status="Completed", batch_ids=["PRB-1"],
        occurred_at=datetime(2026, 7, 20, 12, tzinfo=timezone.utc),
        batches=_batches(), capacity_reservations=_capacities(),
        material_allocations=_allocations(),
    )
    assert result["Batches"]["PRB-1"]["Status"] == "ConvertedToScheduledOccupancy"
    assert result["CapacityReservations"]["R-1"]["Status"] == "ConvertedToScheduledOccupancy"
    assert result["MaterialAllocations"]["A-1"]["Status"] == "ActivePlanReservation"


def test_failed_or_dead_letter_run_holds_reservations_but_queued_retry_does_not():
    failed = transition_planning_reservations_for_run(
        run_id="RUN-1", run_status="Failed", batch_ids=["PRB-1"],
        occurred_at=datetime(2026, 7, 20, 12, tzinfo=timezone.utc),
        batches=_batches(), capacity_reservations=_capacities(),
        material_allocations=_allocations(),
    )
    assert failed["Batches"]["PRB-1"]["Status"] == "HeldForPlanningError"
    queued = transition_planning_reservations_for_run(
        run_id="RUN-1", run_status="Queued", batch_ids=["PRB-1"],
        occurred_at=datetime(2026, 7, 20, 12, tzinfo=timezone.utc),
        batches=_batches(), capacity_reservations=_capacities(),
        material_allocations=_allocations(),
    )
    assert queued["Batches"]["PRB-1"]["Status"] == "ActivePlanReservation"
```

Also test missing and ineligible batch IDs raise `ReservationBatchReferenceError`.

- [ ] **Step 2: Run bridge tests and verify they fail**

```powershell
pytest tests/test_planning_run_reservation_bridge.py -q --basetemp .tmp/pytest-reservation-bridge-red -p no:cacheprovider
```

Expected: collection fails because the bridge module does not exist.

- [ ] **Step 3: Implement immutable freeze and transitions**

Use `deepcopy` for every frozen or transitioned record. Eligible freeze statuses are `ActivePlanReservation` and `LinkedToFormalOrder`. `Completed` converts batch and capacity status; `Failed` and `DeadLetter` set batch, capacity, and still-active material allocation to `HeldForPlanningError`; `Queued` returns unchanged copies. Add `PlanningRunID`, `LastTransitionAt`, and an `EventType` summary to transitioned records.

- [ ] **Step 4: Run bridge tests**

```powershell
pytest tests/test_planning_run_reservation_bridge.py -q --basetemp .tmp/pytest-reservation-bridge-green -p no:cacheprovider
```

Expected: all tests pass.

- [ ] **Step 5: Commit bridge**

```powershell
git add -- sdbr/planning_run_reservation_bridge.py tests/test_planning_run_reservation_bridge.py
git commit -m "feat: bridge shared reservations into planning runs"
```

---

### Task 7: Planning Run API Integration and Read Model

**Files:**
- Modify: `sdbr/api.py`
- Modify: `tests/test_api.py`

**Interfaces:**
- Consumes: all Phase 0 modules and store collections.
- Produces:
  - optional `PlanningReservationBatchIDs` on `PlanningRunPayload`;
  - frozen reservation snapshot on Planning Run;
  - post-execution reservation transition;
  - `GET /planner/workbench/planning-reservations/workbench`.

- [ ] **Step 1: Write failing API tests for missing, frozen, converted, and summarized batches**

Extend the existing `sdbr.test_data` import in `tests/test_api.py` so the baseline IDs are explicit:

```python
from sdbr.test_data import (
    BASELINE_MASTER_DATA_VERSION_ID,
    BASELINE_OPERATIONAL_STATE_ID,
    P1_MARKET_CONTROL_RUN_ID,
    seed_baseline_test_data,
)
```

Add these exact helpers and tests:

```python
def _phase0_planning_run_payload(run_id: str) -> dict[str, object]:
    return {
        "RunID": run_id,
        "ProblemID": f"PLAN-{run_id}",
        "MasterDataVersionID": BASELINE_MASTER_DATA_VERSION_ID,
        "OperationalStateSnapshotID": BASELINE_OPERATIONAL_STATE_ID,
        "ScheduleStartAt": "2026-06-22T08:00:00+00:00",
        "TimeBufferMinutes": 480,
        "SolverBackendID": "ortools",
        "RequestedBy": "planner-phase0",
        "RequestedAt": "2026-06-22T07:50:00+00:00",
    }


def _seed_active_planning_reservation(
    store: WorkbenchStateStore,
    *,
    batch_id: str,
) -> None:
    store.planning_demand_commitments["DC-PHASE0"] = {
        "DemandCommitmentID": "DC-PHASE0",
        "DemandSourceType": "MTOCustomerOrder",
        "DemandClass": "MTO",
        "ItemOrProductID": "TST-FG-A",
        "LocationID": "TST-MAIN",
        "Quantity": 1.0,
        "Uom": "EA",
        "RequiredAt": "2026-06-27T01:00:00+00:00",
        "Status": "Active",
        "TraceID": "TRACE-PHASE0",
    }
    store.planning_reservation_batches[batch_id] = {
        "ReservationBatchID": batch_id,
        "DemandCommitmentID": "DC-PHASE0",
        "DemandClass": "MTO",
        "Status": "ActivePlanReservation",
        "CapacityReservationIDs": ["CCR-RES-1"],
        "MaterialAllocationIDs": ["MPA-1"],
        "ConfirmedBy": "planner-phase0",
        "ConfirmedAt": "2026-06-22T07:45:00+00:00",
    }
    store.ccr_capacity_reservations["CCR-RES-1"] = {
        "CapacityReservationID": "CCR-RES-1",
        "ReservationBatchID": batch_id,
        "DemandCommitmentID": "DC-PHASE0",
        "DemandClass": "MTO",
        "ResourceID": "TST_WC_DRUM",
        "WindowStartAt": "2026-06-22T08:00:00+00:00",
        "WindowEndAt": "2026-06-22T16:00:00+00:00",
        "ReservedMinutes": 95,
        "Status": "ActivePlanReservation",
    }
    store.material_planning_allocations["MPA-1"] = {
        "MaterialAllocationID": "MPA-1",
        "ReservationBatchID": batch_id,
        "DemandCommitmentID": "DC-PHASE0",
        "DemandClass": "MTO",
        "RequirementLineID": "TST-WO-0001:TST-RM-STEEL",
        "ItemID": "TST-RM-STEEL",
        "LocationID": "TST-MAIN",
        "Uom": "EA",
        "AllocatedQty": 20.0,
        "SupplySourceType": "OnHand",
        "MaterialSnapshotID": BASELINE_OPERATIONAL_STATE_ID,
        "Status": "ActivePlanReservation",
    }


def test_planning_run_rejects_unknown_reservation_batch():
    store = WorkbenchStateStore()
    seed_baseline_test_data(store)
    client = TestClient(create_app(state_store=store))
    response = client.post("/planner/workbench/planning-runs", json={
        **_phase0_planning_run_payload("RUN-UNKNOWN-RES"),
        "PlanningReservationBatchIDs": ["PRB-MISSING"],
    })
    assert response.status_code == 404
    assert response.json()["Data"]["Status"] == "PlanningReservationBatchNotFound"


def test_planning_run_freezes_and_converts_explicit_reservation_batch():
    store = WorkbenchStateStore()
    seed_baseline_test_data(store)
    _seed_active_planning_reservation(store, batch_id="PRB-1")
    client = TestClient(create_app(state_store=store))
    created = client.post("/planner/workbench/planning-runs", json={
        **_phase0_planning_run_payload("RUN-WITH-RES"),
        "PlanningReservationBatchIDs": ["PRB-1"],
    })
    assert created.status_code == 200
    run = created.json()["Data"]["PlanningRun"]
    assert run["FrozenPlanningReservations"]["ReservationBatchIDs"] == ["PRB-1"]

    executed = client.post(
        "/planner/workbench/planning-runs/RUN-WITH-RES/execute",
        json={
            "ExecutedBy": "planner-phase0",
            "StartedAt": "2026-06-22T07:55:00+00:00",
            "CompletedAt": "2026-06-22T07:56:00+00:00",
            "TimeLimitSeconds": 30,
        },
    )
    assert executed.status_code == 200
    assert executed.json()["Data"]["PlanningRun"]["Status"] == "Completed"
    assert store.planning_reservation_batches["PRB-1"]["Status"] == "ConvertedToScheduledOccupancy"
    assert store.ccr_capacity_reservations["CCR-RES-1"]["Status"] == "ConvertedToScheduledOccupancy"
    assert store.material_planning_allocations["MPA-1"]["Status"] == "ConvertedToScheduledOccupancy"


def test_planning_reservation_workbench_summarizes_business_rows_only():
    store = WorkbenchStateStore()
    seed_baseline_test_data(store)
    _seed_active_planning_reservation(store, batch_id="PRB-1")
    client = TestClient(create_app(state_store=store))

    response = client.get("/planner/workbench/planning-reservations/workbench")

    assert response.status_code == 200
    data = response.json()["Data"]
    assert data["Summary"] == {
        "BatchCount": 1,
        "ActiveCount": 1,
        "MTOCount": 1,
        "MTACount": 0,
    }
    assert data["Rows"][0]["ReservationBatchID"] == "PRB-1"
    assert "Resources" not in data["Rows"][0]
    assert "Routings" not in data["Rows"][0]
```

- [ ] **Step 2: Run focused API tests and verify they fail**

```powershell
pytest tests/test_api.py -q -k "planning_reservation" --basetemp .tmp/pytest-reservation-api-red -p no:cacheprovider
```

Expected: payload field, endpoint, or frozen fields are missing.

- [ ] **Step 3: Bind store collections and payload field**

In `create_app`, bind the six new store collections. Add to `PlanningRunPayload`:

```python
    PlanningReservationBatchIDs: list[str] = Field(default_factory=list)
```

Update `_planning_run_payload_from_record` to preserve the list.

- [ ] **Step 4: Validate and freeze explicit batches at Planning Run creation**

Before `_pending_planning_run`, call `freeze_planning_reservations`. Return:

- `404 / PlanningReservationBatchNotFound` for unresolved IDs;
- `409 / PlanningReservationBatchNotEligible` for wrong status.

Pass the frozen snapshot to `_pending_planning_run` and store it under `FrozenPlanningReservations`. Empty IDs must preserve current Planning Run behavior.

- [ ] **Step 5: Transition reservations after final execution status**

After failure policy resolves the final run status and before returning the response:

- call the bridge only when frozen batch IDs are non-empty;
- apply converted records for `Completed`;
- apply held records for `Failed` or `DeadLetter`;
- perform no transition for retry `Queued`;
- append `PlanningReservationsConverted` or `PlanningReservationsHeldForError` audit details.

The existing middleware will persist the entire store. Keep all validation before mutation so an error response leaves no partial state; a SQLite revision conflict triggers the existing `reload()` rollback path.

- [ ] **Step 6: Add read-only reservation workbench endpoint**

Add:

```python
    @app.get("/planner/workbench/planning-reservations/workbench")
    def planning_reservation_workbench():
        rows = sorted(
            planning_reservation_batches.values(),
            key=lambda item: (str(item.get("Status")), str(item.get("ReservationBatchID"))),
        )
        return {
            "Endpoint": "/planner/workbench/planning-reservations/workbench",
            "StatusCode": 200,
            "Data": {
                "Summary": {
                    "BatchCount": len(rows),
                    "ActiveCount": sum(1 for row in rows if row.get("Status") == "ActivePlanReservation"),
                    "MTOCount": sum(1 for row in rows if row.get("DemandClass") == "MTO"),
                    "MTACount": sum(1 for row in rows if row.get("DemandClass") == "MTA"),
                },
                "Rows": rows,
                "Boundary": "Shared planning reservations only; not ERP/WMS inventory authority.",
            },
        }
```

If `DemandClass` lives only on the demand record, enrich rows from `planning_demand_commitments` rather than duplicating inconsistent values.

- [ ] **Step 7: Run API and business-closure tests**

```powershell
pytest tests/test_api.py tests/test_business_closure.py -q -k "planning_reservation or planning_run" --basetemp .tmp/pytest-reservation-api-green -p no:cacheprovider
```

Expected: all selected tests pass.

- [ ] **Step 8: Commit API integration**

```powershell
git add -- sdbr/api.py tests/test_api.py
git commit -m "feat: freeze shared reservations in planning runs"
```

---

### Task 8: Phase 0 Verification and Evidence Update

**Files:**
- Modify: `docs/backend-specification.md`

**Interfaces:**
- Consumes: Tasks 1 through 7.
- Produces: repeatable verification evidence and final Phase 0 status.

- [ ] **Step 1: Run module syntax checks**

```powershell
python -m compileall -q sdbr
```

Expected: exit code `0` with no output.

- [ ] **Step 2: Run all Phase 0 focused tests**

```powershell
pytest tests/test_planning_commitments.py tests/test_planning_reservations.py tests/test_planning_reservation_view.py tests/test_planning_run_reservation_bridge.py tests/test_state_store.py tests/test_sdbr_market_control.py tests/test_api.py -q -k "planning_commitment or planning_reservation or ccr_planned_load or state_store" --basetemp .tmp/pytest-shared-reservation-phase0 -p no:cacheprovider
```

Expected: all selected tests pass with zero failures.

- [ ] **Step 3: Run full regression suite**

```powershell
pytest -q --basetemp .tmp/pytest-full-shared-reservation-phase0 -p no:cacheprovider
```

Expected: all tests pass; any warning must be recorded exactly and must not hide a failure.

- [ ] **Step 4: Update acceptance evidence**

In the Phase 0 acceptance note, replace “待实现与重复测试证据” with exact implementation files, commands, pass counts, and remaining boundaries. Keep capability status `[PARTIAL]` because MTO and MTA business workflows are not yet connected.

- [ ] **Step 5: Verify the final diff**

```powershell
git diff --check
git status --short
```

Expected: no whitespace errors; `nofinish/` remains untracked and unstaged; no unrelated files are staged.

- [ ] **Step 6: Commit evidence update**

```powershell
git add -- docs/backend-specification.md
git commit -m "docs: record shared reservation phase zero evidence"
```

---

## Execution Checkpoints

1. After Task 2, review demand identity and new-version behavior before reservations depend on it.
2. After Task 3, review atomicity and idempotency before state persistence.
3. After Task 5, verify no scheduled load or qualified demand is counted twice.
4. After Task 7, verify current Planning Runs with empty reservation IDs remain byte-for-byte compatible at the API behavior level.
5. Do not start MTO or MTA business workflow implementation until Task 8 full regression passes.
