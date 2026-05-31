# PM Scope — "¿Gané o perdí?" profit summary

_Pragmatic PM scoping. Date: 2026-05-31. Grounded in shipped HEAD source, not a rebuild._
_Personas: `work/ux-loop/user-novice.md` (Diego, P0 #2 "no profit view"), `work/ux-loop/user-power.md` (Sofía, P1 #4 orders-list bare `$`). Brand: `work/ux-loop/market-research.md` §4.2.3 "the big honest number."_

---

## 1. The real gap — confirmed, with one sharpening

**The PM read is correct.** The gap is NOT missing profit math — order-contribution profit is fully shipped and trustworthy:

- `GET /api/v1/reports/cost-rollup` (`backend/src/api/v1/endpoints/reports.py:1536`) → `aggregate_rollup` (`backend/src/services/order_cost_engine.py:442`) sums realized-order breakdowns into `revenue_amount_mxn − cogs − marketplace_fees − shipping − ad_spend − other = net_profit_amount` + `net_margin_percent`. By-channel and daily variants exist.
- Frontend already consumes it: `today-profit-widget` (window=1) and `margin-by-channel-widget` are mounted on the cockpit (`frontend/src/app/dashboard/pages/dashboard/dashboard.component.ts`), via `AnalyticsReportsService.costRollup()` (`frontend/src/app/dashboard/services/analytics-reports.service.ts:12`, `CostRollup` interface).

**The gap is twofold and exactly as stated:**
1. **Operating expenses are never subtracted.** `GET /api/v1/expenses/summary` (`backend/src/api/v1/endpoints/expenses.py:39`, returns `total_amount` over `start_date`/`end_date`) lives in a totally separate module. No surface computes **`order_contribution_profit − operating_expenses = business bottom line`**. That is the owner's real question and it is unanswered.
2. **Discoverability.** Even the contribution number is buried — `today-profit-widget` is one tile in a dense cockpit, framed as "hoy" not "este mes," with no plain win/lose verdict and no `tú`-voice. Diego (P0 #2) can't find "¿estoy ganando dinero?" from one screen.

So the feature = **combine contribution profit + operating expenses into ONE plain-language period bottom-line, made a signature, discoverable moment.** Confirmed.

### Build decision: NEW thin backend endpoint `GET /api/v1/reports/profit-summary`

**Recommend a new backend endpoint, not frontend composition.** Why:

- **Single source of truth for the subtraction.** The "after everything" number and the double-count rule (below) are *accounting semantics*, not presentation. Computing `contribution − opex` on the client means every future consumer (a report export, a future email digest, the mobile bottom-nav) re-derives it and can disagree. Centralize it.
- **Window alignment is a correctness trap on the client.** `cost-rollup` takes `window_days` (rolling N days from `utcnow`); `expenses/summary` takes `start_date`/`end_date` (calendar). Composing them on the frontend means hand-converting "Este mes" → both a `window_days` AND a date range and hoping they cover the same span. A server endpoint takes ONE period contract and fans out internally, eliminating the mismatch. **This alone justifies the endpoint.**
- **It's thin.** The endpoint orchestrates two existing functions — `aggregate_rollup(db, window_days=...)` and an expenses sum over the matching range — and returns a flat DTO. No new tables, no cost-engine changes. ~40 lines + schema.
- **Frontend stays dumb:** one call, render. Reuses `AnalyticsReportsService` (add `profitSummary(period)`).

**Period contract:** accept a `period` enum (`this_month` | `last_7d` | `last_30d`) OR an explicit `start`/`end`. Endpoint resolves the period ONCE, derives `window_days` for the rollup from the same span, and passes the same `[start, end]` to the expense sum. Return both the resolved range and `window_days` in the response so the UI/tests can assert alignment.

### Double-counting ad spend — the rule (call it out explicitly)

Verified ground truth: in the cost engine, order-level **`ad_spend` defaults to `0.0`** (`order_cost_engine.py:145`) — the column exists but is effectively **unpopulated for ML orders today**, while ad/marketing spend that sellers actually log lives as an **expense under the "Marketing" category** (`expenses.py:35`). So today the practical risk is near-zero, but it is structurally real the moment per-order ad attribution lands.

**Rule for the endpoint (must be implemented now, not deferred):**
- The bottom line = `net_profit_amount` (already net of breakdown `ad_spend`) `− operating_expenses`, where **`operating_expenses` EXCLUDES any expense category already represented in the cost breakdown.** Concretely: subtract a configurable `DOUBLE_COUNTED_CATEGORIES = {"Marketing", "Shipping"}` set from the expense total **only when** the corresponding breakdown line is non-zero for the period; otherwise count the expense.
- **Simplest correct v1 (recommend):** since order-level `ad_spend` and breakdown `shipping` provenance differ from the expense module, for v1 **subtract the FULL `expenses.total_amount`** and surface a one-line footnote in the response + UI: _"Si registras publicidad o envíos como gasto Y también en el costo de cada venta, podrían contarse dos veces."_ Ship the `category_excluded` plumbing but default it OFF (empty set) so behavior is predictable and auditable. Revisit when per-order ad attribution ships. Document this in the endpoint docstring and the test.

---

## 2. The feature — fully scoped

**"¿Gané o perdí?" — your business bottom line for the period.**

### Where it lives (decision: BOTH, one shared component)

- **Dashboard card (populated accounts):** a new `profit-summary-widget` mounted at the TOP of the cockpit (above the four hero cards) in `dashboard.component.html`, **only when `!isEmptyAccount()`**. It is the lead "signature number." Default period = **Este mes.**
- **Dedicated page `/reports/profit`:** the same `ProfitSummaryComponent` rendered full-bleed, linked from the sidenav "Reportes" group and from a "Ver detalle" affordance on the dashboard card. This is where the period selector + breakdown live in full; the dashboard card is a compact embed of it.
- **Empty/new accounts:** the dashboard card is **suppressed** (no realized orders → the honest answer is "aún no"). Instead the onboarding hero gets ONE line: _"Cuando hagas tu primera venta, aquí verás si ganas o pierdes."_ The `/reports/profit` page still loads and shows a calm empty state (no fake zeros) with the same line. **Rule: the big number never renders against zero realized orders — it shows the empty state.**

### The surface (top → bottom)

1. **Verdict line (plain `tú`, es-MX):** computed from the bottom line —
   - `> 0`: **"Ganaste este mes"** (semantic positive token + ↑ icon)
   - `< 0`: **"Perdiste este mes"** (semantic **danger/loss** token + ↓ icon — NEVER chile-red; always icon-paired per brand)
   - `== 0`: **"Quedaste a mano"** (neutral)
2. **The big honest number** — the bottom line in MXN, oversized, display face, tabular-lining, via the shared `MoneyPipe` / `money` formatter with explicit `MXN`: `$12,480.50 MXN`. This is the brand "signature number" moment (`market-research.md` §4.2.3). Never animated.
3. **Period selector:** segmented control — **Este mes / 7 días / 30 días** (maps to `this_month` / `last_7d` / `last_30d`). Default Este mes. Re-fetches on change.
4. **Plain breakdown (non-accountant ladder):**
   | Plain es-MX label | source field |
   |---|---|
   | Lo que vendiste (ingresos) | `revenue_amount_mxn` |
   | − Costos de tus ventas (producto, comisiones de ML, envío) | `cogs + marketplace_fees + shipping + ad_spend + other` |
   | = Ganancia de tus ventas | `net_profit_amount` (contribution) |
   | − Gastos de tu operación (renta, sueldos, etc.) | `operating_expenses` |
   | **= Resultado neto** | **`bottom_line`** |
   Each row right-aligned MXN via MoneyPipe. The two costs collapsed into one "costos de tus ventas" line with a tooltip/expander breaking out the four sub-lines (don't lead with COGS/fees jargon).
5. **Honesty footnote:** the ad/shipping double-count caveat (§1) as muted helper text, shown only when relevant.
6. **AI surface (optional, out-of-scope for v1 build but reserve the slot):** a warm-gold (not red) one-line "¿por qué?" insight. **Not built this loop** — reserve layout space.

### Acceptance criteria

- [ ] `GET /api/v1/reports/profit-summary?period=this_month` returns `{ period, start, end, window_days, revenue_amount_mxn, sales_costs_amount, contribution_profit_amount, operating_expenses_amount, bottom_line_amount, verdict: 'won'|'lost'|'even', has_realized_orders, double_count_warning: bool }`. `bottom_line = contribution_profit − operating_expenses`.
- [ ] Rollup window and expense date-range cover the **same resolved span** (assert in a test: `start`/`end`/`window_days` are mutually consistent).
- [ ] `has_realized_orders == false` → endpoint still 200s with zeros and `verdict` omitted/`null`; UI shows empty state, NOT a `$0.00 MXN` "quedaste a mano."
- [ ] Dashboard `profit-summary-widget` renders at top of cockpit for populated accounts only; suppressed for `isEmptyAccount()`.
- [ ] `/reports/profit` route + sidenav entry under Reportes; AuthGuard; lazy-loaded like `reports/qa`.
- [ ] Period selector switches this_month / 7d / 30d and refetches; default this_month.
- [ ] Loss renders in semantic danger token + ↓ icon, never chile-red `#FF4D2E`; passes `check_theme_contrast.py`; all colors via `var(--*)`.
- [ ] Big number uses shared MoneyPipe with explicit `MXN`, tabular numerals, not animated.
- [ ] **i18n:** every string in `es-MX.json` (default) AND `en.json` under `dashboard.profitSummary.*`; no raw strings; passes the i18n guard scripts.
- [ ] **Tests:** backend — `aggregate_rollup`+expense composition, window/range alignment, double-count flag, zero-orders branch, won/lost/even verdict boundaries (`bottom_line` exactly 0). Frontend — `profit-summary.component.spec.ts`: verdict mapping, period switch refetch, empty-state vs number, loss styling; uses `getTranslocoTestingModule()`.

### Out of scope (explicit)

- No new expense-categorization UI or per-order ad attribution; double-count handled by the documented v1 rule + footnote only.
- No charts/trend lines on this surface (sales-vs-spend already exists).
- No AI "¿por qué?" insight build (reserve slot only).
- No CSV/PDF export of profit-summary this loop.
- No custom date-range picker — fixed period enum only.
- No multi-currency: bottom line is MXN (revenue already MXN-normalized in rollup; expenses assumed MXN).

### Brand/UX bar (non-negotiable)

- The number is the hero: display face, oversized, tabular, `$X,XXX.XX MXN`, muted unit. Never jitters, never animates.
- Loss = semantic danger token **+ icon**, never chile-red; chile-red reserved for the single primary action ("Ver detalle"/identity). AI (if ever) = warm gold.
- Voice: `tú`, peer not bank ("Ganaste", "Perdiste"), zero accounting jargon in the headline; jargon only behind the expander tooltip.
- Empty state = warm peer line, never zero-number theatre.

---

## 3. Fold-in decision: orders-list money fix — **YES, fold the minimal version in**

Fold **only** Sofía's P1 #4 (`work/ux-loop/user-power.md:132`) into THIS loop: swap the bare `$` to `| money:order.currency` and add a net-margin% column in `sales-order-list.html:81`. **Defer** P1 #3 (server-side pagination + search) to its own loop.

**Justification:**
- **Thematic coherence + cheap.** This loop's whole subject is "can I trust the money number / did I make money." A bare ambiguous `$` on the orders list (the exact ambiguity MoneyPipe exists to kill) is a direct contradiction of the signature-number brand moment we're shipping. Fixing it here is ~1 line + one column reading `net_margin_percent` already present on order detail — order detail already shows full economics (`sales-order-detail.html`), so the data exists; the list just isn't using it.
- **Pagination/search is a different beast.** It needs a server-side endpoint contract change (windowed query → paged), a `mat-paginator`, and a search param — real backend work that would bloat this loop and has nothing to do with the profit narrative. Defer cleanly as its own ranked item.

So: MoneyPipe + margin column = in. Pagination/search = next loop.

---

## 4. Ranked remainder (loop backlog after this)

1. **P1 — Orders list pagination + search** (`sales-order-list.html`). Server-side `mat-paginator` + order-ID/SKU search; the deferred half of Sofía P1 #3. At hundreds of orders the list is unscannable.
2. **P1 — Ship→push-to-ML inline reauth** (`stock-transfer-detail.ts:82-101`). Reuse the sync reauth banner on the `ship(true)` path so expired-OAuth on push is recoverable inline, not just a toast. (Sofía P1 #2.)
3. **P1 — Stock-transfer picker: server-side search + show on-hand qty** (`stock-transfer-create-dialog.ts:101`, capped at 25, no stock shown → over-commit risk). (Sofía P1 #5.)
4. **P1 — Day-1 dashboard altitude** (`es-MX.json:490-559`). Lead solo sellers with "1. Agrega productos 2. Conecta ML 3. Mira tu stock"; collapse enterprise launch-readiness/admin-first checklist. (Diego P1 #4.)
5. **P2 — Q&A volume levers**: Ctrl/⌘+Enter submit, saved-reply templates, just-answered row drops from "Sin responder" filter, `already_answered` 409 → specific "recargar" message. (Sofía re-eval top-3.)
6. **P2 — Dashboard "needs attention" cap-at-8 → ~25 + sort** (`dashboard.component.ts:139`); inline reorder action on triage rows. (Sofía P1 #6/#7.)
7. **P2 — Jargon sweep**: Payments "webhook/respuesta cruda" → "Estado de tus pagos"; gloss "SKU"; "Umbral"→"Avísame cuando baje de", "Velocidad"→"Ventas por día"; standardize "stock bajo". (Diego P1/P2 #5–8.)
8. **P2 — Regenerate `work/redesign/shots/*.png`** with `capture2.mjs` (es-MX + dark) so reviewers stop reading stale English/light/old-nav screenshots. (Both personas P1.)
