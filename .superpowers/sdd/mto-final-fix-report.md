# MTO Final Review Fix Report

Date: 2026-07-12

Review source: `.superpowers/sdd/mto-final-review.md`

Specifications: `BE-SDBR-010`, `UI-COMMIT-001`

## Result

The five final-review findings were fixed in one wave. User confirmation remains pending: `UI-COMMIT-001` and acceptance unit 17.13 stay `已验证待用户确认`, never `用户已确认`. `BE-SDBR-010` remains `[PARTIAL]` with its deferred authority boundaries unchanged.

## Fixes

1. **Blank typed request fields:** reusable stripped nonblank Pydantic strings now cover intake identifiers, nested material identifiers, supplied reevaluation IDs, and decision identifiers/reasons/fingerprint. Whitespace-only values return structured HTTP 422 and do not mutate any public store collection.
2. **Material reason canonicalization:** `normalize_material_check_skip_reason` supplies one canonical value to material evidence and the decision-staleness basis. Padded and trimmed opt-out reasons are equivalent at decision time.
3. **Protection threshold projection:** the workbench reads canonical `TargetPercent`, restoring real values such as the 80% reference fallback.
4. **Drawer accessibility:** the MTO detail drawer is a modal dialog, focuses the close control, excludes the app shell with `inert`, handles Escape without closing an active native decision dialog, and restores the invoking detail control after ordinary close or list rerender.
5. **Reevaluation recovery:** transport and JSON decoding failures are caught, produce bilingual retry guidance, retain enabled controls, and produce no unhandled browser console error.

## Adversarial Coverage

- 16 intake identifier cases, including nested material identifiers.
- 3 reevaluation actor/supplied-ID cases.
- 4 decision identifier/reason/fingerprint cases.
- Padded opt-out reason equivalence through a successful conditional acceptance.
- Canonical threshold values through direct view and real API projections.
- Static modal/focus/Escape/return-focus contracts plus real desktop/mobile browser interaction.
- Forced rejected fetch in Chinese and English with visible recovery and zero console errors.

## Verification

- Red run: 29 expected failures and 7 passes reproduced all findings.
- Python compile: exit 0.
- Bundled Node parser: PASS via `vm.Script`.
- Final focused suite: 312 passed, 1 known Starlette warning, 43.01s, unique basetemp `.tmp/pytest-mto-final-fix-focused-20260712-4-b72e`.
- Fresh full-suite attempt: 1098 passed, 1 failed, 1 known warning, 142.08s, unique basetemp `.tmp/pytest-full-mto-final-fix-20260712-1815-a91c`.
- The sole full-suite failure was a test-only exact-indentation assertion invalidated by the new reevaluation `try/catch`; it was replaced by branch-order assertions. The affected UI reevaluation class then passed 6/6, and the complete 312-test focused set passed.
- Per the user's explicit instruction to end testing and commit immediately, the 1099-test full suite was not rerun after that test-only correction.

## Browser Evidence

- Desktop 1280x720 and mobile 390x844: no page-level horizontal overflow; focus opens on the close button; app shell becomes inert; Escape closes and restores the exact invoking details control.
- Mobile drawer rect: `x=23.40625`, `width=366.59375`, `height=844`.
- Chinese recovery: `无法重新评估当前订单承诺。 请确认服务可用后重试。`
- English recovery: `This order commitment could not be re-evaluated. Check the service and retry.`
- Reevaluate control remained enabled; browser error logs were empty.
- Screenshots are retained under `.tmp/mto-final-fix-*.png` and enumerated in `docs/mto-order-commitment-task28-evidence-2026-07-12.md`.

## Residual Risks

1. The final focused suite is green, but the post-correction full 1099-test rerun is intentionally absent due to the user's stop instruction. The last full execution is therefore 1098 passed plus one subsequently corrected static test.
2. Browser screenshots and SQLite fixtures are local `.tmp` evidence and are not committed product assets.
3. The known Starlette/httpx deprecation warning remains unrelated to this change.
4. Approved CCR-threshold intake and external formal-order/ERP/MES authority remain deferred by specification.
