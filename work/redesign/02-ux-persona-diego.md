# UX Persona Review — Diego (first-time, non-technical ML Full seller)

> **Who I am.** Diego, 24, just signed up for Fulcrum. First online business.
> Never touched an ERP or inventory tool. Spanish-first (es-MX). I get
> overwhelmed by jargon, dense tables, and screens with twenty buttons. I need
> the app to tell me *what to do next* and reassure me I didn't break anything.
> My lens for this whole review: **first-run clarity & onboarding for a novice.**

> **Method + evidence.** Code read-through, not a live click-through. I read the
> recon journey map (`work/redesign/00-journey-map.md`) for the IA/routes, then
> opened the actual Angular templates for the onboarding flow. Templates I read
> line-by-line and quote directly: `auth/components/login/login.html`,
> `dashboard/pages/dashboard/dashboard.component.html`,
> `dashboard/widgets/onboarding-checklist/onboarding-checklist.component.html`
> (+ `.ts`), `core/components/sidenav/sidenav.html`,
> `products/components/product-list/product-list.html`,
> `products/components/product-form/product-form.html`. For journeys whose
> templates I did not open this pass (PO, stock transfer, payments, Q&A,
> marketing, settings, inventory count, orders, marketplaces, scanner), findings
> lean on the verified journey map and are marked **(from journey map — template
> not opened this pass)**. Those are honest follow-ups, not invented detail.

---

## Overall first impression

Fulcrum is powerful and clearly built for someone who already runs this kind of
business. As a complete beginner my honest reaction is: it's an ERP wearing a
nice Material theme. The single best thing for me is that there's a real
**Onboarding Checklist** on the dashboard with progress, clear steps, action
buttons per step, and even a "create demo workspace" button — that genuinely
helps. But three things undercut it badly, and I confirmed all three in the
actual code:

1. **The app is NOT Spanish-first out of the box.** The login screen has
   hardcoded English ("Management Console") and hardcoded English validation
   errors. Several core forms have hardcoded English buttons. For a Spanish-first
   user, the very first screen already speaks the wrong language in places.
2. **The dashboard is a 12+ widget analytics cockpit**, and the onboarding
   checklist is just one item near the top of it, not a focused first-run screen.
3. **Pervasive accounting/warehouse jargon** with no teaching of the core
   "stock lives in 3 buckets, move it with transfers" mental model.

My across-journey rating for a first-run novice: about **2.4 / 5**. Not broken —
intimidating. The gap is teaching, sequencing, and finishing the Spanish.

---

## Journey-by-journey

### 1. Onboarding / first login + first product — **Rating: 3 / 5**
Route: `/login` → `/dashboard`

**Delight (verified):** The onboarding checklist
(`onboarding-checklist.component.html`) is well built — an eyebrow + title +
subtitle (lines 29–31), a `mat-progress-bar` (line 53), an "X / Y required done"
counter (lines 47–48), per-step cards with a state icon, label, description, and a
primary action button that routes me to the right place
(`[routerLink]="step.route"`, line 67). There's also a **"Create demo workspace"**
button (`science` icon, lines 35–40) so I can see the app populated before I have
real data, and a tidy success banner when I finish (lines 4–23). For my persona
this is the lifeline, and it's the strongest part of the app.

**Verified friction on the login screen (`login.html`):**
- Line 10: `<p>Management Console</p>` is **hardcoded English**, not a
  translation key. My first impression in Spanish mode is still "Management
  Console." Jargon AND wrong language in the same breath.
- Lines 26–28: the email validation errors are **hardcoded English** —
  `{{ t('common.email') }} is required` and `Please enter a valid email`. So if
  I fumble my email, Fulcrum scolds me in English. Same on password (line 36).
- There is a clear "forgot password" link (line 41, translated) — good — but
  **no "create account," no "what is Fulcrum," no reassurance.** It's a bare
  console login. A nervous first-timer gets no welcome.

**Verified friction on the "first product" path:** Adding a product and setting
its starting stock are two different places. In `product-list.html` the stock
quantity is only adjustable through a kebab menu item "Adjust stock"
(`openStockAdjustmentDialog`) — there is **no quantity field on the create form at
all** (confirmed: `product-form.html` has name/SKU/barcode/description, price,
cost, dims, reorder points, but no on-hand quantity input). So as a beginner I
create my first product, it shows `0` in stock, and the way to fix that is buried
in a three-dot menu. That is exactly where I'd get stuck.

**Top fix:** Make onboarding a focused first-run wizard (name → price → starting
quantity → connect ML), and finish translating the login screen.

---

### 2. Read the dashboard — **Rating: 2 / 5**
Route: `/dashboard`

**Verified:** `dashboard.component.html` renders, in order: onboarding checklist
(lines 14–16), a "launch readiness" panel with its own grid of sections + a
demo-data cleanup guardrail (lines 18–98), **4 stat cards** (Total Products, Total
Value, Open Purchase Orders, Open Sales Orders, lines 100–116), then a **2×2
analytics grid** (Today's Profit, Sales vs Spend, Margin by Channel, Top Movers,
lines 126–131), then Dead Stock full width (line 140), then Refunds + Returns side
by side (lines 150–153), then Sales by Channel + Low-Stock + Inventory Health
(lines 155–168), then a full-width Analytics Reports row (line 179). That's
**~15 distinct widgets** on the landing page.

For me on day one — no products, no sales — this is overwhelming: a wall of
panels I don't understand, most showing zeros. The checklist I actually need is
competing with "Margin by Channel" and "Dead Stock."

- **Verified currency bug that would confuse me:** the Total Value stat card
  formats with `currency:'USD'` (line 105). My market is Mexico/MXN. Seeing my
  inventory value in **US dollars** on the very first card is wrong and
  confusing for a Mexican seller.
- **Jargon on the wall:** "Margin by Channel," "Dead Stock," "Top Movers,"
  "Launch readiness," "Inventory Health" — undefined to me.

**Top fix:** On an empty/new account, show ONLY the checklist (+ a "primeros
pasos" hero) and hide the analytics until there's data. Fix the USD formatting to
MXN.

---

### 3. Add a product (manual) — **Rating: 2 / 5**
Route: `/products` → `/products/new` (`product-form.html`)

**Verified delights:**
- AI "generate description" button is gated on `@if (aiReady)` (line 83) — so it
  **hides** rather than showing a dead greyed-out button when AI isn't
  configured. That's better than I feared (see cross-cutting note).
- The products toolbar exposes Add, Scan, and Catalog Import as discoverable
  mini-fabs (`product-list.html` lines 46–54) — the scan button especially is
  right where I'd hope.

**Verified friction (this screen has a real es-MX problem):**
- **Hardcoded English buttons/labels** despite the rest using `t(...)`:
  "Regenerate SKU" (`product-form.html` line 48), "Generate QR" (line 59),
  **"Barcode / UPC"** label (line 68) and "Scan or Enter Code" placeholder
  (line 69), "Regenerate Barcode" (line 73). For a Spanish-first novice this is a
  constant flicker between languages.
- **Jargon I don't understand, unexplained:** "SKU," "Barcode / UPC," "QR,"
  "Reorder point," "Reorder quantity," "Average cost." I came to add one product
  and I'm staring at codes and thresholds.
- **"Cost Price" vs "Resale Price"** — I'd want plain "cuánto te costó" / "a
  cuánto lo vendes." These *are* translation keys, so the fix is just copy.
- **No starting-stock field** (confirmed above) — the single most confusing gap.

**Top fix:** Add a starting-quantity field; finish the Spanish; collapse the
reorder/threshold fields behind "advanced"; lead the marketplace tab with
MercadoLibre.

---

### 4. Scan a product (AI + barcode) — **Rating: 4 / 5**
Route: Products → Scan (`openScanner()`, `product-list.html` line 49) / `/ingest`
*(scanner dialog template not opened this pass)*

This is the journey that excites me most: point the camera at the box and let AI
fill the product in. The scan button is right there on the products toolbar (a
`qr_code_scanner` mini-fab, verified line 49), which is discoverable. Per the
journey map it branches exists-vs-new and auto-saves the barcode — all
beginner-friendly.

Caveats I can't fully verify this pass: camera-permission-denied and
no-camera-on-desktop empty states, and whether the AI tab hides cleanly when no
key is set (the product form *does* hide its AI button via `@if (aiReady)`, which
is encouraging). Also the journey map flags `/ingest` is missing `AuthGuard`
(confirmed in `app-routing.module.ts` lines 110–116) — a bug, though not
something I'd feel as a user.

---

### 5. Create a purchase order (incl. AI invoice ingest) — **Rating: 1 / 5**
Route: Purchasing → `/suppliers/po` *(from journey map — templates not opened
this pass)*

Per the journey map this is the deepest, most jargon-dense flow: supplier
lead-time days, a PO "KPI summary," three ways to create a PO at once (manual /
AI invoice drag-drop / a separate "Import PO" review queue with
Pending/History/All and "Reject stale >30 days" and "Learn alias"), then on
arrival an invoice-match dialog (Matched/Diff/Unmatched, "Apply Invoice Values"),
a landed-cost allocation dialog, "Mark as Received," and "average cost
recalculation." Every clause there is vocabulary I don't have. I would not
attempt this without a human. The AI invoice drag-drop is the only part that
sounds approachable, and it's buried among power-user machinery.

**Top fix:** Give novices ONE blessed path ("sube la factura de tu proveedor")
and hide the rest behind advanced mode. (Worth re-reviewing once templates are
opened — empty states and es-MX coverage unverified.)

---

### 6. Inventory count + audit — **Rating: 2 / 5**
Routes: `/inventory/count`, `/products/audit` *(from journey map — templates not
opened this pass)*

The verb "count what's on the shelf" I can grasp. But the nav has two adjacent
items, **"Inventory Count"** and **"Inventory Audit"** (verified in
`sidenav.html` lines 25–33), and I can't tell from the labels which I want —
"audit" sounds scary. The map's flow uses "reconcile" and "commit adjustments,"
which make me afraid I'll overwrite something with no undo. Needs reassurance and
clearer labels. (Empty/first-run state unverified.)

---

### 7. Connect a marketplace + publish a listing — **Rating: 3 / 5**
Route: Marketplaces → Channels (`/marketplaces`) *(from journey map — templates
not opened this pass)*

This is what I actually care about. "+ Connect Account → pick platform →
Authorize → OAuth" is a familiar pattern, so connecting is OK. Friction: the map
says an admin first configures "App Credentials (Client ID/Secret)" — I have no
idea what those are; for a solo seller that must be invisible. Also the nav label
is **"Channels"** (verified `sidenav.html` line 83, `nav.marketplaceChannels`),
but I'm looking for a button that literally says "Conectar MercadoLibre."

---

### 8. Push stock to ML Full via stock transfer — **Rating: 1 / 5**
Route: Marketplaces → Stock Transfers (`/marketplaces/transfers`) *(from journey
map — templates not opened this pass)*

The journey map literally labels step 1 a **"Mental model":** stock lives at
`default`, `ml-full`, `amazon-fba`, and receiving a PO only updates internal
stock — moving it to ML is "always an explicit transfer." **I do not have this
model and nothing teaches it.** I'd receive goods, list on ML, and be baffled
that ML shows 0 available. Then the vocabulary — "Ship + reserve inbound,"
"external_inbound_id," "Reconciliation," "Push qty to listings," "Allocation
planner" — reads like warehouse software. The nav even surfaces this as a raw
"Stock Transfers" link (verified `sidenav.html` line 86, `nav.stockTransfers`).
For my market, where ML Full *is* the fulfillment, this should be the most
hand-held flow and it's the most expert.

**Top fix:** Teach the three-bucket model with a one-time diagram; rename actions
to outcomes ("Enviar inventario a MercadoLibre Full").

---

### 9. Handle a sales order — **Rating: 2 / 5**
Routes: `/orders`, `/orders/:id` *(from journey map — templates not opened this
pass)*

Seeing orders is intuitive. The **Economics card** (revenue − COGS − fees −
shipping − ad spend − other = net profit + margin%, "settled vs estimated"
badge, plus an MXN-equivalent FX line) is over my head: I don't know COGS or
"settled vs estimated." For a peso-only beginner the FX line is extra noise.

**Fix:** Lead with a plain "Ganaste $X en esta venta" headline; tuck the
accountant-grade breakdown behind a "ver detalle."

---

### 10. Answer a buyer question (Q&A + SLA) — **Rating: 2 / 5**
Route: Marketplaces → Buyer Questions (`/reports/qa`) *(from journey map —
template not opened this pass)*

I understand and care about answering buyer questions. But **"SLA"** is in the
feature's name and means nothing to me — call it "tiempo de respuesta." Also the
nav says "Buyer Questions" under *Marketplaces* (verified `sidenav.html` lines
91–93), while the route is `/reports/qa` and the component is
`dashboard/pages/qa-page`; if any title says "Reports" I'll think I took a wrong
turn (the map flags this mismatch too). AI-assisted drafting is marked inferred
even in the map, so I can't promise the one feature that would most help me here.

---

### 11. Reconcile payments / payouts — **Rating: 1 / 5**
Route: `/payments` *(from journey map — templates not opened this pass)*

"Reconcile," "settlements," "payouts," "settled vs estimated fees," "Amazon
fee-split," cross-checked against "net margin," plus separate Refunds and Returns
pages. This is finance-team territory. What I actually want is one sentence:
"MercadoLibre te depositará $X el día Y." That headline is missing.

---

### 12. Record an expense (AI receipt scan) — **Rating: 4 / 5**
Route: Purchasing → Expenses (`/expenses`) *(from journey map — template not
opened this pass)*

A delight in concept and a model for the rest of the app: drag a receipt photo,
AI fills merchant/date/amount/category, review, save. One-time vs Recurring is
understandable; amounts in MXN are right. This is the interaction the whole app
should copy. (es-MX coverage of this dialog unverified — given what I found in
products/login, worth a copy check.)

---

### 13. Run a marketing campaign / quick posts — **Rating: 3 / 5**
Route: `/marketing` *(from journey map — templates not opened this pass)*

**Quick Post** (pick channel, photo, AI Content Assistant by tone, Post Now /
Save Draft) is fun and accessible — makes me feel like a real seller. The full
**Campaign Wizard** + drag-drop **Calendar** is a lot of surface for someone who
just wants to post a product photo, and "Connectors" is jargon for "link my
Instagram." The KPI widgets repeat the dashboard's "numbers I don't get yet"
problem.

---

### 14. Settings (the enabler) — **Rating: 2 / 5**
Route: `/settings` *(from journey map — templates not opened this pass)*

Six tabs: AI Agents, Integrations, Marketing, Inventory, Currency, Data — buried
under "Management" at the bottom of the nav (verified `sidenav.html` lines
104–115). The map says **every AI feature is gated by a provider API key** entered
in AI Agents. A non-technical first-timer does not have an LLM API key and won't
know what one is.

**Important nuance I verified:** at least the product form *hides* its AI button
when AI isn't ready (`@if (aiReady)`, line 83), so it's not a dead greyed-out
button there. That's the right pattern. The remaining risk is **discovery** — I
never learn that pasting a key in Settings unlocks all the scan/receipt/listing
magic that drew me to Fulcrum. It should be a step in the onboarding checklist
(which already supports per-step routes), or AI should be provided/managed for me.

---

### 15. Manage team members (admin) — **Rating: 3 / 5**
Route: Management → Users (`/users`) *(from journey map — templates not opened
this pass)*

Irrelevant to me as a solo seller on day one, and correctly gated by AdminGuard.
No complaint that it's advanced; it just shouldn't occupy prime nav for a
one-person account.

---

## Cross-cutting issues (what hurts me most as a beginner)

1. **es-MX is incomplete on first-run-critical screens (verified).** Hardcoded
   English in `login.html` ("Management Console" line 10, validation errors lines
   26–28/36) and in `product-form.html` ("Regenerate SKU" line 48, "Generate QR"
   line 59, "Barcode / UPC" line 68, "Scan or Enter Code" line 69, "Regenerate
   Barcode" line 73). For a Spanish-first persona this is the most immediate,
   concrete, fixable harm.

2. **No teaching of the core mental model.** The 3-bucket stock model and the
   PO-receiving-vs-transfer split are treated as prior knowledge. Breaks
   journeys 5, 6, 8, 9.

3. **Wrong currency on the dashboard (verified).** Total Value renders in
   `USD` (`dashboard.component.html` line 105) for a Mexico/MXN business.

4. **Dashboard is a ~15-widget cockpit on day one (verified).** The one thing I
   need (the checklist) competes with Dead Stock / Margin by Channel / etc., all
   showing zeros.

5. **Jargon everywhere:** SKU, UPC, QR, COGS, SLA, FBA, landed cost,
   reconciliation, settled vs estimated, allocation planner, dead stock, reorder
   point. Needs outcome-based plain Spanish.

6. **Two-screen "first product."** No starting-stock field on the form
   (verified); quantity hides in a kebab "Adjust stock" dialog.

7. **AI discoverability, not (only) gating.** The product form hides the AI
   button cleanly when no key is set (verified `@if aiReady`, line 83), which is
   good — the real problem is I never learn AI exists or how to turn it on. Put it
   in the onboarding checklist.

## Delights worth keeping (verified)

- The **onboarding checklist** is genuinely good: progress bar, per-step routes,
  optional pills, success banner, and a **"create demo workspace"** button.
- AI affordances **hide** rather than dead-disable when unconfigured (product
  form `@if aiReady`).
- A discoverable products toolbar with Add / Scan / Import mini-fabs.
- **Drag-a-receipt expenses** and **Quick Post with AI tones** (from map) are the
  effortless, modern interactions the rest of the app should copy.
- **`?lang=es-MX` persisted locale switch** in the shell (`app.component.ts`).

## Honest limitations of this pass

I opened the login, dashboard, onboarding, sidenav, product-list, and
product-form templates directly and quote them above with line numbers. The other
ten journeys' templates I did not open this pass; those findings rely on the
verified journey map and are labeled as such. Given that I found real
hardcoded-English and a USD-currency bug in the screens I *did* open, I'd treat
es-MX completeness and MXN formatting as likely-broken-until-checked across the
unopened screens too — that's the priority follow-up for a full re-run.
