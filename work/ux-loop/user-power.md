# Fulcrum — Power-user evaluation (persona: "Sofía", high-volume ML Full seller, MX)

Evaluated against **shipped source at HEAD (a34fc68)**. NOTE: the screenshots in
`work/redesign/shots/` are **stale** — they show the pre-redesign "MENU" sidenav and an
onboarding-dominated dashboard. The actual shipped nav and dashboard are materially
better than the shots; where they diverge I evaluate the code as truth and flag the
staleness.

---

## Journey 1 — Morning triage  ⚠️ (friction, mostly stale-shot artifact)

What I *want*: log in → one dense screen telling me what bleeds money today (low stock /
stockout risk, Q&A over SLA, breached). What the **code** actually ships is good:
- `dashboard.component.html:127-204` — four hero cards (inventory value, sales-vs-spend,
  inventory health w/ low-stock count, **Buyer-Q&A breached count**) + a dense
  "needs attention" table (critical+low rows, on-hand, days-left, suggested reorder,
  severity chip). This is exactly the signal I need, and money is MXN via `MoneyPipe`.
- Q&A SLA hero card links to `/reports/qa` (`dashboard.component.html:142`).

The friction:
- The whole cockpit is gated behind `isEmptyAccount()` (`dashboard.component.ts:121-125`):
  if I have 0 products AND onboarding incomplete, I get the onboarding checklist hero
  instead (this is what the screenshot shows). Fine for true day-1, but the gate is
  binary on `totalProducts===0` — a real account is never empty, so in practice I land
  on the cockpit. OK.
- The "needs attention" table is **capped at 8 rows** (`dashboard.component.ts:139`) with
  only a "view all → /products?filter=low-stock" escape. At hundreds of SKUs, 8 is a
  teaser, not triage. I'd want the top 25 with sort.
- Stockout *risk* = days-of-inventory is shown, good, but there's no "reorder now"
  action inline on the dashboard table — I have to leave to /products.

Rating: ⚠️ — signal is dense and fast **once populated**; cap-at-8 and stale shots are the friction.

## Journey 2 — Push / send stock to ML Full  ⚠️ (recoverable, but inconsistent failure UX)

Flow: sidenav "Send to ML Full" (`sidenav.html:25`, 1 tap) → Stock Transfers → New Transfer
→ pick products → Ship / "Ship + push to marketplace".
- Create dialog (`stock-transfer-create-dialog.ts`): product picker is **capped at 25
  results** (`:101`, `slice(0,25)`) with client-side filter only, and shows **no on-hand
  stock** while I set quantities. At my SKU count I can't trust I'm not over-committing
  internal stock. Friction.
- **OAuth-expired on the push is handled inconsistently.** The `syncListings` path has a
  proper inline **reauth banner** with a Reconnect link (`stock-transfer-detail.html:150-161`,
  driven by `summary.needs_reauthorization`). But the actual **`ship(true)` push-to-marketplace**
  path (`stock-transfer-detail.ts:82-101`) has *no* reauth-specific handling — a failed
  push falls through to the generic `HttpErrorInterceptor` toast
  (`http-error.interceptor.ts:38`). So if my ML token is expired when I hit "Ship + push",
  I get a transient snackbar with a backend string and **no inline Reconnect CTA** — I
  have to know to go to /marketplaces myself. Not a silent failure (good), but not
  recoverable inline like sync is.
- Mitigation: the Marketplaces page **does** surface token state with `expired`/`reauth`
  chips + a Reconnect button (`marketplace-list.html:116-168`), so the connection health
  is discoverable — just not at the moment of the failed push.

Rating: ⚠️ — visible failure, recoverable in 2 hops; the ship path should reuse the sync reauth banner.

## Journey 3 — Buyer Q&A  ❌ (BLOCKED: read-only, cannot answer in-app)

This is the biggest gap for a seller. `/reports/qa` (`qa-page.component.*`) is a
**read-only report table**: asked-at, source, item, question text, SLA pill, hours-open,
with paginator and window/status filters. There is:
- **No answer field, no reply button, no AI-assist, no row action** — `displayedColumns`
  (`qa-page.component.ts:71-78`) has no actions column; the component has zero mutation
  methods. The answer text only appears as a **tooltip** on the question
  (`qa-page.component.html:86`).
So I can *see* I'm 3 questions over my 24h SLA, but I **cannot answer a single one here** —
I have to go to MercadoLibre's own console to actually reply. The whole SLA-tracking value
is undercut because the tool can't close the loop. The class comment even says it
"mirrors the returns page" — i.e. it was built as a report, not a workflow.

Rating: ❌ — surfaces SLA breaches but is a dead-end; no answering, no AI assist.

## Journey 4 — Cross-currency margins / order economics  ✅ (strong) / ⚠️ (list)

Order **detail** is genuinely good (`sales-order-detail.html:43-105`): a full economics
block — revenue → COGS → ML fees → shipping → ad spend → other → **net profit + net
margin %**, each via `MoneyPipe` with the row's own currency, plus an MXN-converted
revenue line (`revenue_amount_mxn`). Per-line margin column too. This is real money I can
trust, MX$ vs US$ disambiguated by design (`money.pipe.ts`).

The friction is the **list** (`sales-order-list.html:81`): Total is rendered with
`currency:'MXN':'symbol-narrow'` → a **bare `$425.50`** (matches the screenshot), which is
the *exact* ambiguity `MoneyPipe` exists to kill, and it's bypassed here. And the list has
**no margin column** — I must click into each order one-by-one to see if it made money.

Rating: ✅ detail / ⚠️ list (bare `$`, no margin-at-a-glance).

## Journey 5 — Bulk / efficiency at volume  ⚠️

- Products: real batch toolbar — select-all, batch price update, batch category, batch
  delete (`batch-action-toolbar.html`). Good.
- **Orders list has NO paginator** (`sales-order-list.html`) — the whole window (e.g. 30
  days = potentially hundreds of orders) renders in one Material table, no pagination, no
  free-text/order-ID search. That's slow and unscannable at my volume.
- Stock-transfer product picker capped at 25, no on-hand (see J2).
- No global keyboard shortcuts / scan-to-find anywhere I can see; everything is mouse +
  mat-select filters.

Rating: ⚠️ — products bulk-edit is good; orders list and transfer picker don't scale.

## Journey 6 — Reliability / trust  ✅ (mostly honest)

- No fake "publish" stubs found on the paths I walked — ship/sync/reconcile all hit real
  endpoints (`stock-transfer.service.ts:167-205`) and reflect returned state.
- Failures surface (interceptor toast + status-0 network message,
  `http-error.interceptor.ts:21-26`); the sync reauth banner is a model of honest failure UX.
- Marketplace "Coming soon"/eBay is clearly labelled as planned, not faked
  (`marketplace-list.ts:109-110`).
- Money is correct/MXN-tagged everywhere **except** the orders-list bare-`$` (J4).
The one trust wobble: the Q&A SLA card promises action ("over SLA") but the destination
can't act (J3) — promise/reality gap.

Rating: ✅ — no silent no-ops or money lies on these paths; the Q&A dead-end is the dent.

---

## Top 8 friction points (ranked)

1. **P0 — Buyer Q&A is read-only; cannot answer in-app (no AI assist).**
   `qa-page.component.ts:71-78` / `.html`. *Fix:* add a reply drawer/dialog per row with a
   POST-answer endpoint and an AI-draft button; this is the core seller workflow.

2. **P1 — Ship→push-to-ML doesn't surface expired-OAuth inline.**
   `stock-transfer-detail.ts:82-101`. *Fix:* have `ship(true)` detect `needs_reauthorization`
   (like `syncListings`) and render the existing reauth banner with the Reconnect CTA.

3. **P1 — Orders list has no pagination or search.**
   `sales-order-list.html`. *Fix:* add `mat-paginator` (server-side) + an order-ID/SKU
   search box; don't dump a whole window into one table.

4. **P1 — Orders list shows bare `$` and no margin.**
   `sales-order-list.html:81`. *Fix:* switch Total to `| money:order.currency` and add a
   net-margin% column so profitability is scannable without drilling in.

5. **P1 — Stock-transfer product picker capped at 25, no on-hand stock.**
   `stock-transfer-create-dialog.ts:101`. *Fix:* server-side search/pagination and show
   available internal qty per row so I don't over-commit.

6. **P2 — Dashboard "needs attention" capped at 8 rows.**
   `dashboard.component.ts:139`. *Fix:* raise to ~25 with column sort, or make the cap a
   user setting; 8 is a teaser at hundreds of SKUs.

7. **P2 — No inline "reorder" / quick action on dashboard triage table.**
   `dashboard.component.html:179-194`. *Fix:* add a per-row "create PO / reorder" action so
   triage doesn't require leaving the dashboard.

8. **P2 — Screenshots/onboarding-first impression are stale vs shipped UI.**
   `work/redesign/shots/*`. *Fix:* re-capture shots against HEAD so the redesigned
   "Daily Actions" nav and populated cockpit are what reviewers/users actually see.

---

## Re-validation (post-fix) — Sofía

**Journey 3 — Buyer Q&A in-app answering** — was ❌ (read-only dead-end). Re-verdict: **✅ fixed & solid.**

I re-walked it on the new code and the answering is **REAL, not a snackbar stub**, end to end:

- **It hits ML.** `qa-page.component.ts:204` → `analytics.answerQuestion()` (`analytics-reports.service.ts:477` POSTs `/reports/questions/{id}/answer`) → endpoint `reports.py:3008` → `questions_service.answer_question` (`questions_service.py:138`) → `connector.post_answer` (`mercadolibre.py:672`) which does a real `POST {API_URL}/answers` with `{question_id, text}` + Bearer token (`:691-696`). The stub branch (`:682`) only fires for missing/`STUB` tokens (dev), so production answers actually land on MercadoLibre, then the row is persisted `answer_text`/`answered_at`/`status=ANSWERED` and committed (`questions_service.py:201-204`). This is the thing I needed and it's honest.

- **Speed / tap-count.** Answer = **2 taps + typing**: "Responder" opens the inline composer (`qa-page.component.html:108`, `openComposer` `:173`), type, "Enviar respuesta" (`:162`). The composer is an in-row expansion (`composer` column `:124-181`), not a modal — good for staying in the list.

- **In-place update, no full reload.** On success `applyAnsweredRow` (`qa-page.component.ts:224`) patches the row object + flips the headline counters live: `unanswered--`, `answered++`, and `breached--` if it was breached (`:235-241`). Spec proves it (`qa-page.component.spec.ts:142-166`, asserts `questionsList` called exactly twice = init only, counters correct). Counters move without a refetch — exactly what I want during a backlog burn-down.

- **Reliability holds.** Empty/whitespace answer is blocked client-side (`submitDisabled` `:187`) **and** server-side (`questions_service.py:155-157` → 400). Already-answered is protected server-side (`answered_at is not None` → 409 `already_answered` `:166-167`, endpoint `:3037`) and the button is hidden once `row.answered` (html `:107`/`:114`). Double-submit guarded by `submitting` (`:199`).

- **Expired token → inline Reconnect, no silent fail / no generic toast.** This was the second half of my P0. The chain is genuine: `get_valid_access_token` raises `ReauthorizationRequiredError` and flips `needs_reauthorization=True` (`marketplace_service.py:100-101`) → `answer_question` catches it (`questions_service.py:206`) → endpoint returns **409 `code: 'needs_reauthorization'`** (`reports.py:3044-3048`) → component checks `status===409 && err.error.code==='needs_reauthorization'` and sets `reauthRowId` (`qa-page.component.ts:214-215`) → inline red banner with a **"Reconectar" link to /marketplaces** renders *inside the composer* (`qa-page.component.html:132-140`), keeping my typed text. Spec covers both the 409-reauth and the generic-500 error branches (`spec.ts:168-191`). es-MX strings all present (`es-MX.json:463-471`). No silent no-op, no money lie.

**Top 3 next improvements for this workflow at volume:**

1. **P1 — No keyboard submit + no bulk answer.** At a 50-row backlog I'm mouse-bound: there's no Ctrl/⌘+Enter to send (`submitAnswer` is click-only, `qa-page.component.html:162`), no canned-reply/template picker, and no multi-select to answer repetitive "¿hay stock?" questions in batch. *Fix:* `(keydown.control.enter)`/`(keydown.meta.enter)` on the textarea, a saved-replies dropdown, and a checkbox + "responder en lote" path. This is the single biggest volume lever now that answering works.

2. **P1 — Just-answered row lies under the "Sin responder" filter until reload.** When `statusFilter==='unanswered'`, `applyAnsweredRow` patches the row in place but doesn't drop it from the filtered list, so it lingers showing the green "answered" tag while the counter says one fewer — a momentary list/counter mismatch that erodes trust during fast triage. The `total`/pagination count also drifts from the now-stale server count until next fetch. *Fix:* when answering under the `unanswered` filter, splice the row out (or visually de-emphasize) and decrement `totalRows`.

3. **P2 — No fresh-data / stale-backlog guard + thin error recovery.** The list only loads on init/filter/page; if a question was answered elsewhere (ML app, teammate) my row is stale and I'll hit the server-side `already_answered` 409 — which currently falls into the **generic** `answerError` toast (`qa-page.component.ts:216-217`), not a specific "ya estaba respondida, recargar" message, so I don't know to refresh. There's also no manual "Actualizar" refresh button and no auto-poll. *Fix:* map the `already_answered` 409 to its own inline message with a "recargar" action, and add a refresh control (or light poll) so the SLA backlog isn't silently stale.

## Re-validation (post-fix) — Sofía: orders list

Re-walked **Pedidos** at volume against the shipped code (not the prior 200-row dump). **Verdict: ✅ fixed & solid** on the four things I flagged (no pagination, no search, bare `$`, no margin column). Two genuine next-step gaps remain (sorting, filter persistence) — both "reasonable next step," not "broken."

### Journey + evidence

1. **Server-side pagination — ✅.** No more 200-row dump. Backend returns the `{items,total,skip,limit}` envelope, counts the *filtered* rows BEFORE offset/limit (`total` is real, not `len(items)`), eager-loads `cost_breakdown` so margin doesn't N+1, and orders `created_at desc, id desc` for stable paging — `sales_orders.py:113-127`. Schema `sales_order.py:48-59`. Front-end drives a real `MatPaginator` with `[length]="total"`; `onPage()` sets `pageIndex/pageSize` and refetches with `skip = pageIndex*pageSize` — `sales-order-list.ts:130,161-165`, `.html:126-132`. Page size 25 (options 25/50/100) — sane default for scanning. `limit` capped at 500 server-side (`sales_orders.py:89`).

2. **External-id search — ✅.** Case-insensitive partial: `func.lower(external_order_id).like(%term%)` — `sales_orders.py:106-108`. Trimmed both ends (component `searchTerm` getter `ts:76-79`, server `.strip()`). Debounced 300ms + `distinctUntilChanged`, and **resets to page 0** on every change — `ts:110-117`. AND-composes with source+days (all `q.filter(...)` chained — `sales_orders.py:99-108`). Distinct empty states: searching-with-no-hits shows `search_off` + `orders.noResults`, vs an empty window showing `inbox` + `orders.empty`, gated on `hasActiveSearch` — `.html:115-124`, `ts:169-171`. Both localized.

3. **Margin scanning — ✅, and done right.** New **Margen** column, right-aligned, `tabular-nums` — `.scss:48-65`, `.html:95-107`. Bands are byte-identical to order-detail's `marginClass()` (loss `<0`, thin `0–15`, healthy `≥15`; null → `''`) — `ts:190-195` vs `sales-order-detail.ts:98-102`. **Missing margin renders an em-dash, never a misleading 0%** — `net_margin_percent` is `None` when there's no breakdown row OR zero-revenue (`sales_orders.py:59-63`), template guards `!= null` with a `—` fallback — `.html:98-105`. **Loss uses the semantic danger token `--error-color`, NOT brand chile-red `--primary`** — `.scss:63`; tokens are explicitly kept distinct (`_tokens.scss:53`: error `#FF6B61` "stays distinct from brand #FF4D2E"). Detail page uses the same tokens (`sales-order-detail.scss:306-308`), so the two views can't drift.

4. **Export CSV/PDF match on-screen scope incl. search — ✅.** `currentExportFilters()` forwards `source/days/search` — `ts:83-89`; the export builder applies the *same* external-id substring + filters (`sales_orders.py:271-273`, comment "WYSIWYG"). Export limit is 5000 (cap 10000) so a quarter dump isn't truncated by the 25-row page.

5. **Paginator localized to es-MX — ✅.** Global `MatPaginatorIntl` override (`app.module.ts:43`) feeds Transloco keys; range reads "1 – 25 de 230", "Elementos por página", etc. — `transloco-paginator-intl.ts:27-47`, es-MX `common.pagination.*` present. i18n keys complete in both `es-MX.json` and `en.json` (`orders.*`), es-MX phrasing is natural MX.

### Top 3 next improvements (orders-at-volume)

1. **P2 — No column sorting.** `order_by` is hard-pinned to `created_at desc` (`sales_orders.py:117`) and the table has no `MatSort`. I can't sort by **Margen** to pull the loss-makers to the top, or by Total to find big-ticket orders — at 25/page I'd have to page through everything. *Fix:* add `MatSortModule` + a `sort` param (whitelist `created_at|total_price|net_margin_percent`) threaded into the query; margin sort needs an outer-join/nullslast on the breakdown.

2. **P2 — No filter/page persistence across navigation.** `source/days/search/pageIndex` are plain component fields (`ts:54-61`), reset on every mount. Click a row → detail → back and I'm dumped to page 1 / Todos los canales / 30 días, losing my place mid-triage. *Fix:* sync state to query params (`?source=&days=&search=&page=`) so back-nav and refresh restore the view (also makes a filtered list shareable with a teammate).

3. **P2 — `status` filter supported by API but not exposed in the UI.** Backend accepts `status` and AND-composes it (`sales_orders.py:101-102`), but the list page has no status dropdown — I can't isolate just `PENDING`/`CONFIRMED` to work an open-orders queue. *Fix:* add a status `mat-select` (localized, "Todos los estados" default) wired through `currentExportFilters()` + `load()` like the existing source filter.
