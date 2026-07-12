# MTO Task 8 Review-Fix Evidence

**Date:** 2026-07-12
**Task:** Task 8, Default-On Material Feasibility
**Specification IDs:** `BE-SDBR-009`, `BE-SDBR-010`

## Finding

`mto-task8-review.md` identified that the Task 8 material-feasibility evidence
implemented and tested shared-allocation behavior, but its test-module
acceptance-evidence header omitted the required `BE-SDBR-009` citation.

## Files

- `tests/test_order_commitment_evaluation.py`
- `.superpowers/sdd/mto-task8-report.md`

## RED

```powershell
pytest tests/test_order_commitment_evaluation.py::test_material_feasibility_evidence_cites_shared_material_allocation_ledger -q --basetemp .tmp/pytest-mto-task8-be009-red -p no:cacheprovider
```

Result: failed as expected: `BE-SDBR-009` was absent from the acceptance-evidence
header.

## GREEN

```powershell
pytest tests/test_order_commitment_evaluation.py::test_material_feasibility_evidence_cites_shared_material_allocation_ledger -q --basetemp .tmp/pytest-mto-task8-be009-green -p no:cacheprovider
```

Result: `1 passed`.

```powershell
pytest tests/test_order_commitment_evaluation.py::TestOrderCommitmentMaterialFeasibility tests/test_planning_reservation_view.py -q --basetemp .tmp/pytest-mto-task8-be009-related -p no:cacheprovider
```

Result: `36 passed`.

## Commit

`fix: cite BE-SDBR-009 in MTO material evidence`
