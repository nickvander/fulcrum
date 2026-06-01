# UX Improvement Loop — Summary

_Multi-agent UX loop run 2026-05-31. Goal: make Fulcrum easy to use, modern,
learnable, performant, with an ownable brand identity._

## What ran

1. **Pending `work/` tasks — verified & closed.** The redesign build-review's
   open items were already resolved in committed code: `/ingest` now has
   `AuthGuard`, the duplicate `/marketplaces` route is gone, and the
   QuickPostDialog specs pass. Full frontend suite green (130 files / 774
   tests) at start of loop.
2. **Market researcher subagent** → `market-research.md`. Verdict: "Obsidian &
   Chile" (dark + chile-red `#FF4D2E`) genuinely stands apart in a market of
   light blue/yellow brands, but risks looking like generic dark-dev-SaaS.
   Cheap differentiators: warm the neutral greys, separate the brand-red from
   loss-red, route AI to warm gold (not red), add signature "honest MXN number"
   + pivot-wedge sync moment, keep self-hosted fonts + skeletons for speed.
3. **Two persona subagents** (novice "Diego" + power "Sofía") →
   `user-novice.md`, `user-power.md`. **Both independently rated the same P0:**
   the Buyer Q&A page (`/reports/qa`) was a read-only SLA report with no way to
   answer questions in-app — the core daily, SLA-bound ML workflow was a dead
   end. (Also noted: the `work/redesign/shots/` screenshots are stale tooling
   artifacts, not product state.)
4. **PM subagent** → `pm-critique.md`. Picked **in-app Buyer Q&A answering** as
   the one feature this loop; corrected a feasibility claim (`ai_service.py` is
   embeddings-only → no AI-draft, manual answering only); ranked the next
   backlog.
5. **Engineer subagent** → implemented it full-stack with tests.
6. **Re-validation loop** — both personas re-walked the journey on the new
   code: **✅ fixed & solid** (real ML `POST /answers`, in-place row update,
   inline Reconnect on expired token, plain es-MX copy).

## Feature shipped this loop: in-app Buyer Q&A answering

- **Backend:** `MercadoLibreConnector.post_answer()` → ML `POST /answers`;
  `questions_service.answer_question()` (resolves the credential by
  `credential_id`, posts, persists `answer_text`/`answered_at`/`status`,
  idempotent, maps reauth/not-found/empty); `POST
  /api/v1/reports/questions/{id}/answer` (400/404/409/502 mapping, `409
  {code:"needs_reauthorization"}` for the UI).
- **Frontend:** per-row "Responder" composer on `qa-page` (chile-red "Enviar
  respuesta" CTA), in-place row + live counter update (no reload), inline
  Reconnect banner on 409; SLA jargon → plain es-MX ("Tiempo de respuesta",
  "Tarde"). es-MX + en keys under `dashboard.qaPage.*`.
- **Tests:** backend 12 (docker stack), frontend +7 (full suite 781 green),
  i18n + theme-contrast guards pass.

## Iteration 2 — small wins + profit summary

**Small wins (committed `acc22de`):**
- Q&A composer polish: Ctrl/Cmd+Enter submit; answered row leaves the
  "unanswered" filter (no list/counter drift); `already_answered` → specific
  "ya respondida — Recargar" banner; wired the orphaned success toast.
- Stock-transfer → ML Full push: fixed a **silent failure** — `ship(push=True)`
  with an expired ML token used to report success while the push no-op'd.
  `ship()` now commits the inventory move + SHIPPED first, then the push
  raises `ReauthorizationRequiredError` → endpoint 409
  `{code:"needs_reauthorization"}`; detail page shows a persistent inline
  Reconnect banner (syncListings upgraded to the same banner).

**Profit summary "¿Gané o perdí?" (this iteration):**
- PM scoped the real gap (`pm-profit-scope.md`): order-contribution profit
  already exists (`/cost-rollup`, `today-profit-widget`) but **never subtracts
  operating expenses** — so no view answered the owner's true bottom line.
- New `GET /api/v1/reports/profit-summary?period=this_month|last_7d|last_30d`:
  one resolved window, fans out to `aggregate_rollup` + `expense_total_over_window`,
  returns `bottom_line = contribution_profit − operating_expenses`, a
  `verdict`, and a `double_count_warning` (ad-spend overlap; exclusion set
  plumbed but defaulted off). Real empty state (no fake `$0`).
- New `profit-summary-widget` (top of populated cockpit) + `/reports/profit`
  page: plain `tú` verdict ("Ganaste/Perdiste"), big honest MXN signature
  number (loss = danger token + ↓, never brand chile-red), period selector,
  jargon-free breakdown ladder. Orders-list bare `$` → shared MoneyPipe
  (margin column deferred — needs a list-endpoint contract change).
- Tests: backend 33 (docker), frontend 804 (full), i18n + theme guards pass.
- Novice re-validation: **✅ fixed & smooth** (P2 nits only).

## Iteration 3 — orders list: pagination + search + margin column

- PM scope (`pm-orders-scope.md`): the list endpoint returned a bare array
  (no total → no real pagination), no search, and no per-row margin. Chose the
  `{items,total,skip,limit}` envelope (matches existing `PaymentListResponse`),
  search on `external_order_id` only (verified `SalesOrder` has no buyer
  column), margin via `joinedload` (no N+1), null→em-dash.
- `GET /api/v1/sales-orders/` now returns the envelope with a case-insensitive
  `search` param (AND-composes with source/status/days; threaded into exports
  for WYSIWYG) and `net_margin_percent` per row (`count()` before
  offset/limit + joinedload). Frontend: server-side MatPaginator (size 25,
  resets to page 0 on filter/search), 300ms debounced search with distinct
  no-results vs empty-window states, and a banded **Margen** column reusing
  order-detail's `marginClass()` (loss = semantic danger token + tabular,
  never brand chile-red; em-dash when null).
- Tests: backend 30 (docker), frontend 817 (full, +13), i18n + theme guards
  pass. Power-user re-validation: **✅ fixed & solid** (remaining items P2).

## Iteration 4 — brand signature moments

Design-lead scope (`brand-moments-scope.md`) deliberately bounded this to 3
moments + deferred the risky global repaint:
- **B — "The AI glows gold":** routed AI affordances (ai-prompt-preview,
  ai-search-bar, quick-post AI) to `--accent-2` gold as icon/hairline/tint
  only (never a flood, never red), via one reusable `.ai-accent*` treatment +
  a reduced-motion-safe shimmer. Adds `--accent-2-rgb`.
- **C — "Honest MXN number" primitive:** extracted the profit-summary
  big-number treatment into a reusable `appHonestNumber` directive
  (Space Grotesk, tabular, muted MXN suffix, semantic tone — never chile-red
  on money) and applied it to the hero money KPIs (one source of truth).
- **E — Peer-voice empty states:** `tone="peer"` + pivot-wedge glyph on the
  shared empty-state, warm es-MX `tú` copy; converted products / Q&A / orders
  empties.
- **D (wedge motion):** skipped — no app-wide sync/success event to hook it to
  (would need net-new global event plumbing); deferred.
- **A (warm the neutrals):** deferred to its own audited round — it repaints
  every surface in both themes and needs a full contrast matrix.
- Design re-validation: ⚠️→✅ after 2 one-line fixes (darkened light gold
  `#C8860A`→`#A87008` for ≥3:1 on cream; removed a dead `--accent-color`
  self-alias). All AA recomputed; reduced-motion honored.
- Tests: frontend full suite 832 green (+15); i18n + theme-contrast guards pass.

## Iteration 5 — AI-gold consistency + warm the dark neutrals

**AI-gold propagation (`3835c9b`):** the prior loop's "AI = gold" only reached
~3 surfaces. Enumerated 13 AI touchpoints and routed them all to the gold
token via `.ai-accent` — including several "AI" badges that were painted in
chile-**red** (PO-ingest, quick-product, purchase-order-edit, expense-dialog),
a brand-rule violation now fixed. Also dropped the red "(requerido para IA)"
from the quick-post product field (Material renders a focused label in
`--primary`, so red was carrying the AI meaning) → neutral label + gold hint.
Left deterministic generators / commit buttons / data-links as-is. 836 green.

**Warm the dark neutrals (this iteration):** the deferred high-risk repaint.
Design-systems pass (`warm-neutrals-scope.md`) shifted the 10 dark neutral
tokens from cool blue-black (~225°) to warm obsidian/clay (~12–30°) at matched
luminance, so contrast is preserved. NOTE: `check_theme_contrast.py` validates
token discipline only — NOT WCAG ratios — so the contrast matrix is the
safeguard. I independently recomputed every text-on-surface pair: all ≥4.5:1
(tightest `text-hint` on `bg-raised`/`bg-hover` 4.78→**4.84**, improved), all
semantics ≥3:1. Only the `$obsidian` map values changed; reds/blue/gold/
semantics and the (already-warm) light map untouched. Verified live in dark
(dashboard, orders, products) — warmer surfaces, text still crisp, dividers
visible, chile-red still pops. 836 green; guards pass. Warming kept
deliberately subtle (low saturation) to avoid a muddy "brown SaaS" look.

## Iteration 6 — backlog cleanup (4 items)

- **Orders sorting + status filter + URL persistence (`01a0183`):** MatSort on
  all columns (backend `sort_by`/`sort_dir` allowlist, margin sort nulls-last
  N+1-safe), a status dropdown, and full filter/sort/page persistence via URL
  query params (survives refresh/back). 844 FE / 15 BE.
- **Q&A product name instead of raw item_id (`d949d85`):** resolve item_id →
  product name via a grouped dedup subquery (1:1, no row inflation), id as
  tooltip fallback; also fixed a latent CDK multi-row table error. 847 FE / 15 BE.
- **Low-stock "Enviar a ML Full" vs "Crear OC" (`5477869`):** made data-driven —
  the low-stock report now splits on-hand by location, so each row offers the
  *correct* primary action (transfer to Full when you have warehouse stock,
  reorder OC when out everywhere) with plain-es-MX tooltips. 849 FE / 12 BE.
- **Wedge sync-pulse (`7bfdb62`):** a shared BrandPulseService; the chile-red
  pivot-wedge tilts/settles (760ms, reduced-motion → gold-glow only) on real ML
  sync successes (stock push / listing sync, never on reauth). 863 FE.
  Verified by tests + code (fires only on a real ML credential sync, so not
  pixel-captured).

## Next-loop backlog (ranked, from PM + re-validation)

1. **Profit / "¿gané o perdí?" summary** (M) — novice has no plain
   make-or-lose-money view; margins exist only deep in order-detail.
2. **Inline ML reauth on Ship→push-to-ML** (S) — reuse the sync-listings
   Reconnect banner pattern (now also used by Q&A) on the stock-push path.
3. **Orders list: pagination + search + MoneyPipe + margin column** (M) —
   currently bare `$`, no paging, no margin.
4. **Low-stock "Crear OC" vs "Enviar a ML Full" disambiguation** (S).
5. **Q&A workflow polish at volume** (P1/P2): keyboard submit (Ctrl/Cmd+Enter),
   just-answered row lingering under the "unanswered" filter (list/counter
   drift), map `already_answered` to a specific "recargar" message, wire (or
   remove) the orphaned `answerSuccess` toast key, product name instead of raw
   `item_id` in the "Artículo" column.
6. **Brand signature moments** (S–M): warm-neutral token nudge, AI→gold,
   pivot-wedge sync/success animation, oversized tabular MXN hero numbers.
