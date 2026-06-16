# Obsidian & Chile Redesign — Build Review (S1–S6)

**Executive line:** All 6 steps are implemented, design-critiqued, and (where flagged) fixed. The tracked tree builds (every step's final `buildStatus` is PASS; cumulative diff is **43 files, +2,423 / −1,851**). The dark-by-default, es-MX-first "Obsidian & Chile" cockpit is **ready for founder review** — with two honest caveats: **S2 shell screenshots were never re-captured** (1 PNG only, a tooling/dev-server block, not a code defect) and **3 of 4 known engineering bugs are NOT yet addressed** (`/ingest` AuthGuard, duplicate `/marketplaces` route — both still open).

---

## Per-step results

| Step | What changed | Critic | Verdict | Build |
|------|--------------|:--:|---------|:--:|
| **S1** Design-system foundation | Tokens + Obsidian/Chile theme (dark default) + M3 bridge, self-hosted fonts, shared primitives (metric-card, error-state, dense-table), MoneyPipe. Collapsed ~970-line `!important` block. | 8 | fix-then-ship → **fixed** | PASS |
| **S2** Global shell + sidenav IA | Flattened sidenav w/ route auto-expand + 3px red wedge, daily-actions cluster, collapsible rail, new mobile bottom-nav, header collapse toggle. | 7 | fix-then-ship → **partial fix** | PASS |
| **S3** es-MX localization sweep | Routed all named hardcoded-English offenders through Transloco; +65 keys parity; money standardized to MXN; es-MX `registerLocaleData`. | 4 | fix-then-ship → **fixed** | PASS |
| **S4** Login + first-run | Obsidian/warm-paper split-panel login (wedge motif, red CTA, blue affordance link), kept resumable onboarding, product starting-quantity field. | 9 | **ship** | PASS |
| **S5** Dashboard progressive disclosure | Empty-account hero vs full cockpit (density guardrail), 4 hero metric cards incl. Q&A-SLA card, dense needs-attention table, skeletons + `@defer`. | 7 | fix-then-ship → **fixed** | PASS |
| **S6** Product form + list | Removed dead Amazon/eBay/Shopify buttons → ML-led publish block, outcome-led cost/price labels (jargon kept as aria), shared MXN pipe, 3-bucket stock explainer. | 8 | **ship** | PASS |

---

## Headline visual wins
- **Coherent dark control-room** across all rendered routes: deep `#0E0F13` canvas, neutral `#1A1C22` cards, **one** chile-red `#FF4D2E` accent reserved for action/identity; cool-blue `#4C8DFF` kept strictly for affordance/links (the "red never competes with clickable" rule holds).
- **Split-panel login** (S4, scored 9) — obsidian brand side w/ red radial glow + pivot-wedge mark, Space Grotesk hero, es-MX value props; red `Ingresar` CTA, blue forgot-password link.
- **Real IA upgrade:** flattened sidenav with daily-money actions promoted to single-tap (Enviar a ML Full / Preguntas / Gastos), active-item red left wedge, mobile bottom-tab bar.
- **Progressive disclosure** done right: new accounts get a getting-started hero instead of ~15 zero-widgets; populated accounts keep the full cockpit (no widget removed).
- **Money is MXN everywhere** via shared formatter — tabular, right-aligned, `$NaN` collapses to em-dash; Space Grotesk tabular hero numbers on KPI cards.

## Verified bugs — what actually got fixed
- ✅ **Dashboard "Total Value" USD → MXN** — fixed (S1 fix + S3 verified; was `currency:'USD'`, now shared MoneyPipe MXN).
- ✅ **Expense KPI bare `$` → MXN** — fixed (getters return numbers, piped through `money`/`mxn`).
- ✅ **Dead "Publish to Amazon / eBay / Shopify" buttons** — removed (S6), replaced with ML-led publish block.
- ❌ **`/ingest` missing AuthGuard** — **NOT addressed (verified open).** `app-routing.module.ts` lines 110–116: the `ingest` route still has no `canActivate: [AuthGuard]`. Flagged in S1/S2 queue; no fix in any step.
- ❌ **Duplicate `/marketplaces` route** — **NOT addressed (verified open).** Defined twice in `app-routing.module.ts`: lines 13–17 and again line 129 (identical lazy-load). Noted, out of redesign scope, still open.

## Unresolved must-fixes / known gaps (honest)
- **S2 screenshots never re-captured.** `shots/step2-shell/` holds **1 PNG only** (`desktop-login-FAILED.png`). Cause: the long-running `:4200` Vite dev server wedged on a stale optimized-dep (504 "Outdated Optimize Dep"); the cache-clear/restart was denied by an env guardrail during S2. **Code fixes for S2 (red CTAs via M3 bridge, buyer-Q&A back link, shell color audit) are believed correct from static evidence but are not pixel-confirmed.** S3+ captures (which exercise the same shell) did render clean, giving indirect confidence.
- **Pre-existing red test suite:** 13 failures, all in `marketing/.../quick-post-dialog.component.spec.ts` (NG0201 `TRANSLOCO_TRANSPILER` under full-suite cross-contamination). Confirmed identical on clean HEAD — **not a redesign regression**, but the gate isn't meaningfully green until fixed separately.
- **Stub / copy-only:** `publishToMercadoLibre()` is a snackbar stub (no real ML endpoint); the 3-bucket stock explainer is static copy, not live per-channel counts.
- **Deferred:** optional guided first-product path; backend `/onboarding/status` "conectar AI/ML" steps; dynamic PWA theme-color; Sass deprecation cleanup.

## Diff footprint
- **43 files changed, +2,423 / −1,851.** Heaviest: `styles.scss` (−~1,117, the `!important` collapse), `variables.scss`, `en.json`/`es-MX.json`.
- **New files (untracked):** `core/components/bottom-nav/`, `shared/components/metric-card/`, `shared/components/error-state/`, `shared/directives/dense-table.directive.ts`, `shared/money/`, `shared/pipes/mxn.pipe.ts`, `theme/_material.scss`, `theme/_tokens.scss`.

## Screenshot directories (per step)
- `work/redesign/shots/step1-foundation/` (21 PNG)
- `work/redesign/shots/step2-shell/` (**1 PNG — login-FAILED only; re-capture needed**)
- `work/redesign/shots/step3-i18n/` (20 PNG)
- `work/redesign/shots/step4-onboarding/` (21 PNG)
- `work/redesign/shots/step5-dashboard/` (20 PNG)
- `work/redesign/shots/step6-products/` (20 PNG)

## Recommended next action
1. **Review the diff + the S3/S4/S5/S6 shots** (these are the trustworthy visual proof). Treat S2 chrome as verified-by-proxy through those captures.
2. **Re-capture S2:** kill the wedged `:4200` server, `rm -rf frontend/.angular/cache && frontend/node_modules/.vite`, restart `ng serve`, then `node work/redesign/shots/capture2.mjs step2-shell dark`. Spot-check `desktop-07-marketplaces` / `desktop-08-stock-transfers` (red CTAs, not blue) and `desktop-09-buyer-questions` (back-link contrast).
3. **Spot-check** before commit: dark login split-panel separation (dark-mode-only polish noted), MXN tabular money on dashboard + expenses + product-list, no raw `nav.*`/`login.*` keys on any authenticated page.
4. **Commit:** the tracked tree builds and tests (excluding the pre-existing QuickPostDialog suite) are green — safe to commit to `main` per workflow. **Before/after commit, open two follow-up tickets:** (a) `/ingest` AuthGuard + duplicate `/marketplaces` route fix, (b) QuickPostDialog `TRANSLOCO_TRANSPILER` spec fix. Do **not** treat the redesign as closing those.
