# es-MX Localization Sweep (follow-up to "Obsidian & Chile" S3)

Date: 2026-05-31

## Goal
Drive user-facing hardcoded English to zero across the Angular frontend. The app is
Spanish-first (default Transloco lang `es-MX`); every label/button/placeholder/
validation-error/empty-state/tooltip/snackbar should flow through Transloco, authored
es-MX-first (tú-form, plain Mexican Spanish) with matching `en.json` entries.

## What shipped
- **66 components localized** (templates + `.ts` snackbars). Baseline leak scan found
  390 template + 63 `.ts`-snackbar English strings; post-sweep the leak detector reports
  only legitimate skips (brand names, currency codes, example placeholders, dev stubs).
- **561 new bilingual keys** merged into `en.json` / `es-MX.json` (now 2518 leaf keys each,
  perfectly in sync).
- **11 pre-existing missing keys fixed** (keys referenced in templates but never defined,
  which rendered raw key text in the UI — e.g. `users.email`, `products.loadingMore`,
  `errors.generic.title/retry`).
- **Flat-key-as-namespace collisions resolved**: 9 keys (e.g. `products.productList`,
  `users.forcePasswordChange`, `errors.generic`) existed as flat strings but also needed
  subkeys; original values relocated to `.label` / `.message` and the ~6 references updated.
- **4 module-import fixes** where agents introduced a directive without its module:
  `TranslocoModule` (campaign-detail), `MatTooltipModule` (product-variants).

## Method (multi-agent workflow)
1. `scripts/find_hardcoded_strings.py` — heuristic leak detector → ranked work-list of 66 components.
2. Workflow fanned out **one agent per component** (sonnet). Each agent edited only its own
   files, reused `common.*`, and put new keys under a unique per-component prefix
   (e.g. `marketing.campaignWizard.*`) so there were **no cross-agent key collisions**.
   Agents returned bilingual keys as structured output rather than writing the shared JSON.
3. The orchestrator was the **single writer** to `en.json`/`es-MX.json` (deterministic merge),
   avoiding 66-way races on the i18n files.

## Regression guards (kept under `scripts/`)
- `scripts/find_hardcoded_strings.py` — flags hardcoded English in templates (allowlists
  brand/currency/format tokens; ignores mat-icon ligatures, `&&`/`||` expressions, `<code>`).
- `scripts/check_i18n_keys_used.py` — verifies every statically-referenced `t('…')` /
  `translate('…')` / `| transloco` key resolves in **both** JSON files (catches typos and
  defined-but-missing keys). Both exit non-zero on failure, suitable for CI.

## Test suite
The localization routed snackbar/label strings through `transloco.translate(...)`, which
broke 101 unit tests across 23 specs that asserted on the old English literals (the suite
was green on origin/main beforehand — confirmed via a HEAD~1 worktree). Fixed with a shared
testing helper `src/app/testing/transloco-testing.ts` (`getTranslocoTestingModule()`) that
loads the **real** en/es-MX JSON with `defaultLang: 'en'`, so `translate()` returns the
original English and the existing assertions hold. A second per-spec workflow applied it to
all 23 specs; only one assertion needed a value change. Full suite back to 130 files / 770
tests passing.

## Verification
- `ng build` — passes (only pre-existing third-party ESM warnings for qrcode/jsbarcode).
- `ng test` (full frontend suite) — 130 files / 770 tests pass.
- `check_i18n_consistency.py` — passes (no duplicate keys, no missing keys across en/es-MX).
- `check_i18n_keys_used.py` — all 2012 referenced keys resolve.
- `find_hardcoded_strings.py` — remaining hits are all legitimate (brand names, currency
  codes, example placeholders like `you@gmail.com`, and the two `public/` dev-stub pages).

## Intentionally left (low-risk, would need logic changes — noted for later)
- Backend-enum category names rendered as-is in expense badges (dynamic data; needs a mapping).
- A few model-default / `[displayWith]` strings: `'New Variant'` default, `'No SKU'` in a
  purchase-order autocomplete display fn, draft-name default in quick-post-dialog.
