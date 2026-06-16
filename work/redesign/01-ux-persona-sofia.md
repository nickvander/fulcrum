# UX Walkthrough — Sofía, MercadoLibre Full power-seller (es-MX)

> Soy Sofía. Vendo ~800 SKUs en MercadoLibre Full desde Guadalajara y manejo todo
> el negocio desde el celular, entre llamadas con proveedores. Si algo me toma más
> de dos taps o no se entiende a la primera, lo abandono. Me importan tres cosas:
> velocidad, acciones en lote, y no perder dinero por quiebres de stock o
> comisiones.

**Method.** Code read-through of the real Angular templates under
`frontend/src/app`, guided by the recon map
(`work/redesign/00-journey-map.md`). I read the actual `.html` for: login, header,
sidenav, dashboard, onboarding-checklist, product-list, product-form,
product-scanner, stock-transfer list + create dialog, sales-order list + detail,
PO-ingest dialog, expense list + dialog, marketplace list + listing dialog, Q&A
page, inventory-count list, payments page, AI settings tab, settings shell, and
quick-post dialog. Quotes below are literal from those files.

---

## The thing that hits me first: half the app isn't in Spanish

This is an es-MX app (the sidenav even has an English / Español MX switch), but a
lot of screens hardcode English literals right next to the Transloco `t(...)`
calls. As a Spanish-first seller this is the fastest way to make me distrust the
product. Verified in the code:

- **`marketing/components/quick-post-dialog`: fully English, zero i18n.** Title
  "Create Quick Post", "Publish a one-off update to your social channels.", "Link
  Products (Required for AI)", "AI Content Assistant", "Tone", "Content Prompt",
  "Generate Text", "Select Channel", "Post Content", "Save Draft", "Post Now",
  "Please link a product above to use AI generation." None of it goes through `t()`.
- **`settings/components/tabs/ai-tab`: fully English.** "Configure AI-powered
  features…", "Enable AI Features", "Active Provider", "Model Override (Optional)",
  "API Key for …", "Key required to enable AI", "Show/Hide Other Provider Keys".
- **`product-form.html`:** "Regenerate SKU", "Generate QR", "Regenerate Barcode",
  label "Barcode / UPC", placeholder "Scan or Enter Code".
- **`product-list.html`:** empty-state "Build your product catalog", "Add your
  first product manually…", "Import supplier PO", "Showing {{n}} of {{m}}
  products", "Scroll for more", "Unlisted", "Bundle".
- **`product-scanner.component.html`:** "Drop image to scan", "or drag and drop an
  image here", "OR".
- **`expense-dialog.html`:** "Drop receipt to auto-fill", "Analyzing receipt…",
  plus a giant English developer comment left in the template (~lines 144-159).
- **`po-ingest-dialog`:** "Import review #…", "Confirm the supplier and Fulcrum
  product matches…", "Needs review", "Create product", "Learn alias", "Approve &
  create PO". The whole AI-PO flow is English mid-dialog.
- **`login.html`:** "Management Console", "© 2025 Fulcrum Inc.", and validation
  errors are English concatenation ("… is required", "Please enter a valid email").
- **`sales-order-detail.html`:** "SKU:" and "Product #…" fallbacks hardcoded.

That's the #1 fix. Now the journeys.

---

## Cross-cutting delights
- **Scan-to-create is ONE tap from the catalog.** `product-list.html` has a
  `qr_code_scanner` mini-fab in BOTH the desktop and mobile action rows (lines 49
  & 67). The scanner (`product-scanner`) is genuinely great: camera capture fab +
  drag-drop + a barcode tab with an autofocus, enter-to-submit field (perfect for
  my USB/Bluetooth scanner) and a `BarcodeDetector` camera mode, then a
  "Product Found" card that branches to Edit-existing vs Create-new. This is why
  I'd switch.
- **AI ingest is one drag, with confidence + review.** `po-ingest-dialog` shows a
  confidence badge ("Confidence: … (87%)"), per-line warnings, and per-line
  "Create product" / "Learn alias" — it's teaching itself my supplier's SKUs.
  `expense-dialog` is the same drop-to-autofill pattern.
- **Order economics are first-class** (`sales-order-detail.html`): revenue − COGS
  − fees − shipping − ad spend − other = net + margin%, a settled-vs-estimated
  badge with tooltips, an MXN-equivalent line at the order-date FX rate, plus a
  status timeline and refund events. Exactly the number I obsess over.
- **The marketplace channel screen is Mexico-aware and polished**
  (`marketplace-list.html`): a "Recommended for Mexico" badge on connectable
  channels, a "Primary channel" badge, connected-state quick stats
  (listings/healthy/issues), and — crucially — a **reauth chip with a one-tap
  "Reconnect"** when the OAuth token is expiring. That directly answers my biggest
  ML Full fear (silent token death killing my stock sync).
- **Stock transfers have honest states and the power tools are right there.**
  `stock-transfer-list.html` header has "Planner" and "Reconciliation" buttons
  next to "New Transfer", status-filter tabs, a units-received/planned column, and
  a real empty state. The create dialog is clean (destination, notes, product
  search, qty table, save-disabled-until-valid).
- **Empty/loading/error states are consistently handled** across Q&A, payments,
  transfers, orders, inventory-count — spinners, empty cards, and (Q&A) a retry
  button.

## Cross-cutting frictions
1. **English leaks (above).** Pervasive, credibility-killing for me.
2. **Daily money tasks sit behind sidenav expanders.** `sidenav.html` buries
   Stock Transfers, Buyer Questions, and Expenses inside collapsible
   `mat-expansion-panel`s (Marketplaces / Purchasing). An extra tap every visit.
3. **Buyer Q&A has no dashboard presence.** The Q&A *page* is good (see #10), but
   the dashboard never shows me a "X questions over SLA" count, and the nav
   label/route/module disagree (Marketplaces label, `/reports/qa` route,
   `dashboard/pages/qa-page` component). For an SLA task that's a miss.
4. **Currency inconsistency.** Orders list total uses `currency:'MXN'` (good), but
   the dashboard "Total Value" stat card uses `currency:'USD'` and the expense KPI
   cards hardcode a bare `'$'` prefix. Mixed signals about what currency I'm in.

---

## Per-journey ratings

### 1. Onboarding / first login + first product — 3/5
`login.html` is clean but English-branded ("Management Console") with concatenated
English errors. After login the `onboarding-checklist` is genuinely good: a
progress bar, "{{completed}}/{{total}} required", per-step cards with a
`[routerLink]` action button, and a "Create demo workspace" option to explore with
sample data. **Friction:** first product still defaults to the manual form when
the marquee feature is scan-to-create; and whether the AI-key step is a checklist
item determines whether a new seller ever sees the AI magic.

### 2. Read the dashboard — 4/5
Money-first: 4 deep-linking stat cards (Total Products, Total Value, Open POs, Open
Sales Orders) then today-profit → sales-vs-spend → margin-by-channel → top-movers,
dead-stock, refunds+returns, sales-by-channel/low-stock/inventory-health, analytics.
Loading spinner + launch-readiness panel present. **Friction:** ~12 widgets = long
mobile scroll; no Buyer-Q&A-over-SLA or transfers-to-receive card up top; "Total
Value" is in USD.

### 3. Add a product (manual) — 3/5
`product-form.html` is a thorough two-tab, multi-card form with an AI-description
button gated on `aiReady`. **Friction:** English literals; and the Marketplaces
tab has dead "Publish to Amazon / eBay / Shopify" buttons with no click handlers
(and eBay/Shopify aren't my market). For 800 SKUs I'd avoid this path entirely.

### 4. Scan a product (AI + barcode) — 5/5 (the headline, and it earns it)
One tap from the catalog, camera + drag-drop + hardware-scanner barcode field +
BarcodeDetector mode + clean found/new branching. The best-feeling flow in the
app. **Only friction:** English literals and the AI-key dependency (if my key is
unset the camera-permission hint logic hides behind `!isAiEnabled` and the value
quietly drops).

### 5. Create a PO (AI invoice ingest) — 3/5
`po-ingest-dialog` is impressive: upload → AI extract with a confidence score →
editable preview with supplier detection, per-line product matching, "Create
product"/"Learn alias", warnings → "Approve & create PO"; it also detects when the
doc is actually an invoice for an existing PO and shows a line-by-line match diff.
**Friction:** it's the heaviest flow (multi-step + a dialog stack on receiving),
the mid-dialog copy is English, and on a phone this is a desk job.

### 6. Inventory count + audit — 4/5
`inventory-count-list.html` lets me start a count inline (location + notes + Start)
and links to Audit history; the detail uses the scan-SKU hardware dialog. Clean
states. Solid for warehouse work.

### 7. Connect marketplace + AI listing — 4/5
`marketplace-list.html` is a delight (Mexico-recommended badge, primary badge,
reauth chip + one-tap reconnect, connected quick-stats, sync-now). The
`marketplace-listing-dialog` does channel select → "Generate with AI"
title/description/keywords (with a copy-keywords button) → save draft→publish.
**Friction:** the listing dialog uses `t(...) || 'English fallback'` everywhere, so
if a key is missing I see English; and the product-form's separate dead publish
buttons confuse which path is canonical.

### 8. Push stock to ML Full (stock transfer) — 4/5 (my core loop, better than I feared)
The planner and reconciliation ARE reachable — as header buttons on
`stock-transfer-list.html` — so my bulk-allocation leverage isn't lost (it's just
one level inside the Marketplaces expander). The model is honest and the create
dialog is fast. **Friction:** still two taps to reach the transfers page; and I
need a failed push ("expired OAuth") to be re-authable inline — the
marketplace-list reauth chip is the right pattern to mirror on the push result.

### 9. Handle a sales order — 4/5
`sales-order-list.html`: channel + window filters, CSV/PDF export, MXN totals,
clickable rows, empty state. `sales-order-detail.html`: the Economics card, line
items with per-line margin + unmatched-SKU markers, returns section with
record-return, refund events, status timeline. Genuinely deep. **Friction:**
Economics card legibility on a narrow phone is the thing to verify.

### 10. Answer a buyer question (Q&A + SLA) — 3/5 (page is good; discovery + answering are the gaps)
Correction to my first impression: the `qa-page` template is actually
well-built — three SLA counter cards (unanswered / **breached (>N h)** / answered),
window + status filters, a table with an SLA pill per row and an hours-open column,
and proper loading/error(retry)/empty states. **But:** (a) there is **no visible
way to compose/post an answer in this template** — no answer field, no AI
"suggest answer" button (the question text just shows the answer as a tooltip), so
I may be bounced to MercadoLibre to actually reply; (b) it's buried in the
Marketplaces expander with no dashboard count, so I won't notice a breach until
it's late. For a reputation-and-SLA task, fix discovery and add in-app answering.

### 11. Reconcile payments/payouts — 3/5
`payments-page.html`: status filter, a table (id/date/status/amount/payer/provider
id/order) with a view-detail button, paginator, empty + loading states.
Functional. **Friction:** payout→order linkage is a single "#id" column, so
matching a settlement to its orders looks manual; refunds/returns live elsewhere.

### 12. Record an expense (AI receipt scan) — 3/5
`expense-list.html` has KPI cards, date-range presets, category/type filters,
CSV/PDF export, and a clean table; the dialog does drop-to-AI-fill. Capability is
strong. **Friction:** buried two taps deep under Purchasing; English literals; a
stray English dev comment in the dialog; KPI values hardcode `'$'`.

### 13. Marketing campaign + quick posts — 2/5
`quick-post-dialog` has a nice AI Content Assistant (tone chips, text/image
generation, product linking required for AI). **But it is 100% hardcoded English**
— every label and button. For an es-MX seller this screen reads as a different,
unfinished app. Lowest-localized journey I found.

### 14. Settings (AI/integrations/currency/data) — 3/5
`settings.html` is a clean 6-tab shell (icons + labels via `t()`). The Currency
tab (date-stamped FX) powers my MXN math. **Friction:** the `ai-tab` — the global
unlock for every AI feature — is entirely English, and this make-or-break key
lives in a settings tab instead of being pulled into onboarding. It does at least
show a "Key required to enable AI" / "Key configured" status, which is good.

### 15. Manage team (admin) — 3/5
List + create/edit, password reset, bulk import, audit log behind AdminGuard. Not
my daily concern; the right admin features exist.

---

## Top issues to fix first (Sofía's priority)

1. **Finish es-MX localization.** Start with the worst offenders:
   `quick-post-dialog` and `ai-tab` (fully English), then the English literals in
   product-list, product-form, scanner, expense-dialog, po-ingest, login. Remove
   the English dev comment in `expense-dialog.html`. This is my #1.
2. **Give Buyer Q&A a dashboard count + in-app answering.** Surface "X over SLA"
   as a top dashboard card linking straight in, add an answer composer + AI
   "suggest answer" to `qa-page`, and reconcile the nav/route/module naming.
3. **Cut taps to daily money actions.** Pull Stock Transfers, Buyer Questions, and
   Expenses out of the sidenav expanders (or auto-expand the active group). Keep
   scan-product (already 1 tap) and add a near-1-tap scan-receipt.
4. **Fix currency consistency.** Dashboard "Total Value" is USD and expense KPIs
   hardcode `'$'` while orders use MXN — default everything to MXN.
5. **Mirror the marketplace reauth chip on the stock-transfer push result** so a
   failed push (expired OAuth) is re-authable in one tap.
6. **Remove or wire the dead "Publish to Amazon/eBay/Shopify" buttons** in
   product-form, and drop non-Mexico channels from the headline.
7. **Fix the `/ingest` missing-AuthGuard bug** (per recon) before launch.
