# PM Scope — Orders list: server-side pagination + search + margin column

_Loop: orders-list volume fixes. Persona driver: "Sofía" (high-volume ML Full
seller) — `work/ux-loop/user-power.md` J5/J4: the list client-fetches `limit:200`
with **no paginator, no search, no margin-at-a-glance**. Deferred from the
profit-summary loop because the margin column needs a list-endpoint contract
change (`00-loop-summary.md` backlog #3). The bare-`$` is already fixed —
`sales-order-list.html:81` uses `| money:order.currency`._

**One feature this loop.** Ship the contract change cleanly: paged envelope +
`search` param + a `net_margin_percent` field on the list row, then migrate the
**single** JSON consumer (frontend `list()`) and its tests. `/export`,
`/export-pdf`, `/summary*`, and `/{id}` detail are **untouched**.

---

## 1. Pagination contract — DECISION: (a) paged envelope `{items, total}`

**Recommended: change `GET /api/v1/sales-orders/` to return a paged envelope.**
Rejected the alternatives:

- **(b) `X-Total-Count` header on the array** — no existing precedent in this
  codebase; the frontend `HttpClient` calls all read the body directly
  (`sales-orders.service.ts:103` returns `Observable<SalesOrder[]>`), so we'd
  have to switch to `observe: 'response'` and parse a header — *more* consumer
  churn than the envelope, and headers are easy to drop through proxies.
- **(c) parallel endpoint** — leaves two list paths to keep in sync; pure debt.

**The envelope is the house pattern.** This is already how every other paged
list in the app works, so eng has copy-paste precedent and reviewers have a
mental model:
- `backend/src/schemas/payment.py:55` `PaymentListResponse {items, total}`
  ("`total` is the count BEFORE skip/limit so the UI can render `Showing N–M of
  Total`").
- `analytics-reports.service.ts:162/188` `RefundsListResponse` /
  `ReturnsListResponse` `{items, total}`, consumed by the qa/returns/refunds
  pages with `MatPaginator` server-side (`qa-page.component.ts:65` `pageSize=50`,
  `:137` `totalRows = resp.total`, `:156` `onPage`).

**Response model** (`backend/src/schemas/sales_order.py`, new):
```python
class SalesOrderListResponse(BaseModel):
    items: List[SalesOrder]   # SalesOrder schema, now incl. net_margin_percent
    total: int                # count of rows matching filters+search, pre-skip/limit
    skip: int                 # echo back (so the client can trust its own paging)
    limit: int
```
`{skip, limit}` are echoed (cheap, and the qa/payments envelopes only return
`{items,total}` — we go one better so the client never has to assume its own
request was honored). Endpoint change at `sales_orders.py:65`:
- `response_model=SalesOrderListResponse` (was `List[SalesOrderSchema]`).
- Build the filtered query once; `total = q.count()` **before** `offset/limit`;
  then `items = [_serialize_order(o) for o in q.offset(skip).limit(limit).all()]`.
- Keep existing param contract: `source`/`status`/`days`/`skip`/`limit(<=500)`,
  `order_by created_at desc nullslast, id desc`. Default `limit` stays 100;
  frontend will request `limit:25` (or 50).

This touches **one** JSON consumer. `/export*` build rows via the separate
`_build_sales_order_export_rows` (`sales_orders.py:211`) — leave as-is.

---

## 2. Search scope — DECISION: `external_order_id` only (substring, case-insensitive)

**Param:** `search: Optional[str] = Query(None)`. Trim; if empty/whitespace after
trim, treat as absent (no filter). Case-insensitive substring:
```python
if search and search.strip():
    term = f"%{search.strip().lower()}%"
    q = q.filter(func.lower(SalesOrder.external_order_id).like(term))
```
`external_order_id` is what Sofía pastes from the ML notification / packing slip
— it's the one identifier she actually has in hand. It's a column on
`sales_orders` (`order.py` `external_order_id = Column(String)`), so this is a
single indexed-ish WHERE with **no join, no N+1**.

**Explicitly NOT in v1 search:**
- **Buyer name — impossible without a schema change.** `SalesOrder` has **no
  buyer/customer/nickname column** (verified `order.py:34-58`). Out of scope;
  flag as a follow-up if Sofía asks (needs an ingest + migration).
- **SKU / product name — deferred (join cost).** Would require
  `JOIN sales_order_items JOIN products` with a `DISTINCT`/`EXISTS` subquery and
  changes the `total` count semantics (one order, many lines). Real value but
  it's a second, riskier query shape — defer to keep this loop a clean contract
  change. If we ever add it, do it as `EXISTS (SELECT 1 FROM sales_order_items
  ... )` to avoid row multiplication, **not** a plain join.
- Anything fuzzy / full-text / ranked. Plain `LIKE` substring only.

**Composition:** `search` **AND**s with the existing `source`/`status`/`days`
filters (all narrow the same query). `total` reflects the filtered+searched set.
Changing `search` resets the paginator to page 0 (client-side).

---

## 3. Margin column — DECISION: add `net_margin_percent` to the list row

**Source:** `OrderCostBreakdown.net_margin_percent` (1:1 with the order,
`order.py:93/160`, `uselist=False`). **Nullable by design** — the model comment
is explicit: "NULL when revenue is 0 — dividing by zero would lie. Caller treats
NULL as 'no margin data' rather than 0%." Also NULL when an order simply has **no
breakdown row** (un-computed / legacy).

**Serialization** — add the field to the `SalesOrder` schema
(`sales_order.py:28`) so it flows through both list and detail:
```python
net_margin_percent: Optional[float] = None  # from OrderCostBreakdown; None = unknown
```
`_serialize_order` (`sales_orders.py:52`) reads
`order.cost_breakdown.net_margin_percent if order.cost_breakdown else None`.

**Avoid N+1 — single eager load.** The list query must
`.options(joinedload(SalesOrder.cost_breakdown))` (the detail endpoint already
does this at `sales_orders.py:336`). One LEFT JOIN, one row per order (1:1
relationship → no fan-out, `total` count unaffected). Do **not** lazy-load per
row. (`_serialize_order` is shared with detail, which already eager-loads, so the
field is free there.)

**Null/unknown semantics:** `null` → render an **em-dash `—`**, never `0%`,
never a colour band. A 0% real margin (breakeven) is distinct from unknown and
DOES band (thin).

**Brand bar — reuse the order-detail bands exactly.** Detail already defines the
banding (`sales-order-detail.ts:98-102`): `<0 → margin-loss`, `0–15 →
margin-thin`, `≥15 → margin-healthy`; null → `''`. SCSS tokens
(`sales-order-detail.scss:306-308`): healthy `var(--success-color)`, thin
`var(--warning-color)`, loss `var(--error-color)`. **Loss is the semantic
`--error-color`, NOT brand chile-red `#FF4D2E`** (per `market-research.md` —
separate brand-red from loss-red). Lift `marginClass()` into the list component
(or a tiny shared helper) so the two pages can't drift.
- **Right-aligned, tabular numerals** (`font-variant-numeric: tabular-nums` /
  `font-feature-settings: 'tnum'`) so the column scans as a vertical ledger.
- Format `{{ value | number:'1.0-1' }}%` (matches detail `:94`).
- New column id `'margin'`, inserted after `'total'`:
  `['created_at','source','external','status','total','margin']`.

**Total colour-by-status — NO.** Keep `total` neutral. Status already has its own
chip (`statusChipClass`), and colouring the total too would double-encode and
fight the margin column for the eye. Margin is the one profitability signal in
this row; total stays a plain honest MXN number via `MoneyPipe`.

---

## 4. Acceptance criteria + full-stack surface

**Backend**
- [ ] `GET /sales-orders/` returns `SalesOrderListResponse {items,total,skip,limit}`;
      `total` is the filtered+searched count pre-skip/limit.
- [ ] New `search` param: trimmed, case-insensitive substring on
      `external_order_id`; empty→ignored; AND-composes with source/status/days.
- [ ] `SalesOrder` schema gains `net_margin_percent: Optional[float]`;
      `_serialize_order` populates it from `cost_breakdown`; list query
      `joinedload(cost_breakdown)` (no N+1).
- [ ] `/export`, `/export-pdf`, `/summary*`, `GET /{id}` unchanged
      (detail still serializes fine — same `_serialize_order`).

**Frontend** (`sales-orders.service.ts` + `sales-order-list.*`)
- [ ] `list()` return type → `Observable<SalesOrderListResponse>` (`{items,total,
      skip,limit}`); add `search?: string` to opts → `params.set('search', …)`.
- [ ] `SalesOrder` interface gains `net_margin_percent?: number | null`.
- [ ] `MatPaginator` (server-side): `pageSize` default 25, options `[25,50,100]`;
      `onPage` sets `pageIndex/pageSize`, refetches with `skip=pageIndex*pageSize`,
      `limit=pageSize`; bind `[length]="total"`. Localized via the existing
      `TranslocoPaginatorIntl` (`shared/services/transloco-paginator-intl.ts`)
      and `common.pagination.*` keys (already present).
- [ ] Debounced search input (`mat-form-field` + `matInput`, ~300ms
      `debounceTime` + `distinctUntilChanged`); changing it resets `pageIndex=0`.
      Composes with existing source/days `mat-select`s and the refresh button.
- [ ] Margin column: id `'margin'` after `'total'`, `marginClass()` band, em-dash
      on null, right-aligned tabular nums, `number:'1.0-1'%`.
- [ ] Export buttons keep reusing `currentExportFilters()` — **also pass the
      current `search`** so an exported file matches the on-screen scope (add
      `search` to `/export*` params is in-scope; the export query just adds the
      same `external_order_id` LIKE — trivial, keeps WYSIWYG. If eng judges it
      non-trivial, drop search from export and note it.)

**i18n** (`es-MX.json` default + `en.json`, under `orders.*`)
- [ ] `orders.searchLabel` ("Buscar pedido"), `orders.searchPlaceholder`
      ("Número de pedido…"), `orders.margin` ("Margen"), `orders.noResults`
      ("No hay pedidos que coincidan con tu búsqueda."). Reuse existing
      `common.pagination.*`. Plain **`tú`** voice, es-MX. i18n guard must pass
      (keys present in both files, no orphans).

**Tests**
- [ ] Backend: envelope shape `{items,total,skip,limit}`; `total` correct vs a
      filtered page; `search` matches external id case-insensitively + composes
      with source/days; margin present when breakdown exists, `null` when absent;
      no N+1 (one query / joinedload).
- [ ] Frontend: `list()` parses the envelope; paginator drives skip/limit refetch;
      debounced search resets to page 0 + sends `search`; `marginClass()` bands
      (reuse detail's cases) + em-dash on null; no-results empty state renders.
      Full suite stays green; theme-contrast guard passes (only `var(--*)` tokens).

**UX bar**
- [ ] Plain `tú`, dark Obsidian tokens, no hardcoded hex.
- [ ] Loss = semantic danger token, **never** brand chile-red.
- [ ] Paginator fully localized (es-MX default).
- [ ] Two distinct empty states: **no orders in window** (existing `orders.empty`)
      vs **search returned nothing** (`orders.noResults` — only when a search term
      is active). Search box clears easily.
- [ ] Margin column right-aligned, tabular, em-dash for unknown.

**Out of scope (explicit):** column sorting (unless the Material header sort is
genuinely trivial and free — otherwise defer); saved filters / saved searches;
buyer-name search (no column); SKU/product-name search (join, deferred);
fuzzy/full-text/ranked search; per-row inline actions; total colour-by-status;
infinite scroll; CSV/PDF format changes.

---

## 5. Ranked remainder of backlog (after this)

1. **Inline ML reauth on Ship→push-to-ML (S)** — reuse the sync-listings /
   Q&A Reconnect banner on `stock-transfer-detail.ts:82-101`. (Loop-summary says
   a related silent-failure was fixed in `acc22de`; confirm the banner now covers
   the `ship(true)` 409 path and close if done.)
2. **Stock-transfer product picker: server-side search + on-hand qty (M)** —
   `stock-transfer-create-dialog.ts:101` caps at 25 client-side with no on-hand;
   over-commit risk at volume. Same paginate+search pattern as this loop.
3. **Q&A volume polish (S)** — saved-reply templates + bulk "responder en lote"
   for repetitive "¿hay stock?"; product name instead of raw `item_id`.
4. **Dashboard "needs attention" cap 8 → ~25 + sort (S)** —
   `dashboard.component.ts:139`; 8 is a teaser at hundreds of SKUs.
5. **Inline "reorder / Crear OC" action on dashboard triage (S)** — so triage
   doesn't require leaving the dashboard; pairs with low-stock disambiguation.
6. **Brand signature moments (S–M)** — warm-neutral token nudge, AI→gold,
   pivot-wedge sync/success animation, oversized tabular MXN hero numbers.
