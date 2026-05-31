# Fulcrum — User Journey Map

_AI-first commerce hub for Mexican e-commerce sellers. Angular 21 PWA + Angular
Material + Transloco (en / es-MX). FastAPI backend. Primary market: Mexico.
Primary fulfillment: MercadoLibre (ML) Full._

> **Evidence note.** Everything below was read directly from source:
> `app-routing.module.ts` (top-level routes), every `*-routing*.ts` child module,
> `marketing.routes.ts`, the core shell (`core/components/sidenav/sidenav.html`
> + `.ts`, `core/components/header/header.html`), full directory listings of all
> feature modules, and all eight `docs/user-guides/*.md`. Route strings, file
> paths, nav labels, and step text are verified, not guessed. The few places that
> infer behavior from a service/component name rather than a read-through of that
> component's template are marked **(inferred)**.

---

## App summary

Fulcrum is the "operating system" for a Mexican online-retail business. Per
`docs/user-guides/index.md` it covers: inventory across products + bundles; cost
control (purchase history, average cost, profitability); selling on Amazon (NA)
and MercadoLibre (MLM); and AI automation (generate descriptions/listings, match
barcodes, extract POs and receipts). The defining house style is **AI-assisted
data entry** (camera/barcode scan to create products, drag-drop invoices/receipts
to extract POs and expenses, AI-generated marketplace listings and social copy)
layered over **marketplace + fulfillment automation** (orders ingested via
webhook/poller, stock pushed to ML Full / Amazon FBA via explicit stock
transfers, settlement reconciliation, buyer Q&A SLA).

It is an authenticated SPA. Every functional route is guarded by `AuthGuard`
(`auth/guards/auth-guard`). `/login` (`auth/components/login/login`) is behind a
`LoginGuard`; recovery is `/forgot-password` and `/reset-password`. Empty path
redirects to `/dashboard`; wildcard redirects to `/products`. Two **public**
buyer-facing routes exist: `/qr/:id` (`public/qr-redirect`) and
`/store/products/:id` (`public/store-product`). Admin areas (Users, audit logs)
are additionally gated by `AdminGuard` (`core/guards/admin.guard`).

Cross-cutting concerns live in `core/`: `ai.service` (content generation),
`hardware.service` (camera/Bluetooth/USB barcode scanners), `currency.service`
(MXN + FX), `settings.service` (theme/language/AI provider), `notification.service`,
`report-download.service`, an `http-error.interceptor` with translated API errors
(`core/errors/translate-api-error.ts`), a `loading.interceptor`, and the auth
interceptor (`auth/interceptors/auth-interceptor.ts`).

> **One observed anomaly:** the top-level `/ingest` route
> (`products/product-ingestion/product-ingestion`) is declared **without
> `AuthGuard`** in `app-routing.module.ts`, unlike every other functional route.
> `/marketplaces` is also declared twice (lines 14 and 129) — harmless duplicate.

---

## Information architecture (current navigation)

The app shell is `core/components/header/` (top bar: hamburger + Fulcrum logo
only — the user menu was intentionally moved out) and
`core/components/sidenav/sidenav.html`. The sidenav has two labeled groups plus a
user footer. **This is the real nav, read from `sidenav.html`:**

**Group: `nav.menu` (primary)**
| Label (i18n key)            | routerLink                  | Component                                              |
| --------------------------- | --------------------------- | ----------------------------------------------------- |
| Dashboard                   | `/dashboard`                | `dashboard/pages/dashboard/dashboard.component`        |
| Products                    | `/products`                 | `products/components/product-list/product-list`         |
| Inventory Audit             | `/products/audit`           | `products/pages/inventory-audit/inventory-audit`        |
| Inventory Count             | `/inventory/count`          | `inventory-count/pages/list/inventory-count-list`       |
| Orders                      | `/orders`                   | `sales-orders/pages/sales-order-list/sales-order-list`  |
| Alerts                      | `/alerts`                   | `alerts/pages/alerts-page/alerts-page`                  |
| Payments                    | `/payments`                 | `payments/pages/payments-page/payments-page`            |
| **Purchasing** (expander)   | —                           | —                                                      |
| ↳ Purchase Orders           | `/suppliers/po`             | `suppliers/.../purchase-order-list`                     |
| ↳ Suppliers                 | `/suppliers`                | `suppliers/supplier-list/supplier-list`                 |
| ↳ Expenses                  | `/expenses`                 | `expenses/components/expense-list/expense-list`         |
| **Marketplaces** (expander) | —                           | —                                                      |
| ↳ Channels                  | `/marketplaces`             | `marketplaces/pages/marketplace-list/marketplace-list`  |
| ↳ Stock Transfers           | `/marketplaces/transfers`   | `marketplaces/stock-transfers/stock-transfer-list`      |
| ↳ Marketplace Health        | `/marketplaces/health`      | `marketplaces/marketplace-health/...health-page`        |
| ↳ Buyer Questions           | `/reports/qa`               | `dashboard/pages/qa-page/qa-page`                       |
| Marketing                   | `/marketing`                | `marketing/components/campaign-list/campaign-list`      |

**Group: `nav.management`**
| Label    | routerLink   | Component                              |
| -------- | ------------ | ------------------------------------- |
| Users    | `/users`     | `users/components/user-list/user-list` (AdminGuard) |
| Settings | `/settings`  | `settings/components/settings/settings` |

**User footer** (per-user card): theme toggle (light/dark), language switch
(English / Español MX), sign out. Role shown from `user.user_type`
(admin/employee/customer).

**Routes reachable but NOT in the sidenav** (deep links / contextual / detail):
- `/orders/:id` — order detail (`sales-orders/pages/sales-order-detail`).
- `/reports/refunds` (`dashboard/pages/refunds-page`), `/reports/returns` (`dashboard/pages/returns-page`) — also surfaced as dashboard widgets.
- `/products/dashboard` (`products/pages/product-dashboard`), `/products/new`, `/products/edit/:id` (`product-form`).
- `/inventory/count/:id` — count detail (`inventory-count/pages/detail`).
- `/suppliers/dashboard`, `/suppliers/id/new`, `/suppliers/id/:id`, `/suppliers/po/create`, `/suppliers/po/:id`.
- `/marketplaces/transfers/planner`, `/marketplaces/transfers/reconciliation`, `/marketplaces/transfers/:id`, `/marketplaces/:id`, `/marketplaces/settings/:type`, `/marketplaces/:type/callback` (OAuth return).
- `/marketing/new`, `/marketing/calendar`, `/marketing/connectors`, `/marketing/:id`, `/marketing/:id/edit`.
- `/ingest` (scanner ingestion page — no AuthGuard), `/users/account`, `/users/create`, `/users/edit/:id`, `/users/audit-logs`, `/users/force-password-change`.
- Public: `/qr/:id`, `/store/products/:id`.

---

## Canonical user journeys

### 1. Onboarding / first login + first product
- **Entry route:** `/login`
- **Steps:**
  1. Land on `/login`; `LoginGuard` bounces already-authenticated users.
  2. Enter credentials → `AuthGuard` admits → empty path redirects to `/dashboard`.
  3. Dashboard shows an **Onboarding Checklist** widget (`dashboard/widgets/onboarding-checklist`, backed by `dashboard/services/onboarding.service.ts`) guiding setup.
  4. Per `index.md` getting-started: **Products → + Product** (journey 3), set initial stock via the Stock Adjustment dialog (⋮/gear on a product card), then **Settings → Marketplaces / Connect** a channel (journey 7).
  5. Recovery path: `/forgot-password` → email link → `/reset-password`. First-time/forced rotation: `/users/force-password-change`.
- **Modules:** auth, core (shell), dashboard.
- **Key files:** `auth/components/login/login`, `auth/components/forgot-password/forgot-password.component`, `auth/components/reset-password/reset-password.component`, `auth/guards/auth-guard.ts`, `auth/guards/login-guard.ts`, `core/services/auth.service.ts`, `dashboard/widgets/onboarding-checklist/onboarding-checklist.component.ts`, `dashboard/services/onboarding.service.ts`.

### 2. Read the dashboard (daily operating overview)
- **Entry route:** `/dashboard` (default landing)
- **Steps:**
  1. Land on Dashboard (`dashboard/pages/dashboard/dashboard.component`).
  2. Scan KPI widgets: Today's Profit, Sales vs Spend, Sales-by-Channel, Margin-by-Channel, Top Movers, Inventory Health, Dead Stock, Refunds, Returns, Analytics Reports, plus stat cards and a Low-Stock list.
  3. Drill from a widget into the relevant area — Low-Stock list → reorder (journey 4) or replenish ML Full (journey 8); Refunds/Returns widgets → `/reports/refunds`, `/reports/returns`.
- **Modules:** dashboard, alerts, sales-orders, payments, core.
- **Key files:** `dashboard/pages/dashboard/dashboard.component.ts`, `dashboard/services/dashboard-stats.service.ts`, `dashboard/services/analytics-reports.service.ts`, `dashboard/services/low-stock.service.ts`, `dashboard/widgets/*` (today-profit, sales-vs-spend, sales-by-channel, margin-by-channel, top-movers, inventory-health, dead-stock, refunds, returns, low-stock-list, stat-card).

### 3. Add a product (manual catalog entry)
- **Entry route:** `/products` → **+ Product** (`/products/new`)
- **Steps:**
  1. Open Products list (`product-list`); use Grid/List toggle, quick filters (In/Out/Low stock), advanced filters (type, price/stock ranges — debounced 400ms), pagination.
  2. Click **+ Product** → product form (`product-form`).
  3. Fill Name, SKU (auto-generated if blank), Cost Price, Resale Price; optionally Description (AI can generate — `ai.service`), images (drag-drop, `enhanced-image-management` / `product-form-image-gallery`), custom fields.
  4. (Alt) **+ Bundle**: add component products + quantities; estimated cost computed from components; stock derived dynamically.
  5. Save. Manage stock later via Stock Adjustment dialog (`stock-adjustment-dialog`) and view history (`stock-history-dialog`). Batch edits via `batch-action-toolbar`.
- **Modules:** products, core (ai.service, currency.service).
- **Key files:** `products/components/product-list/product-list.ts`, `products/components/product-form/product-form.ts`, `products/components/stock-adjustment-dialog/stock-adjustment-dialog.ts`, `products/components/enhanced-image-management/enhanced-image-management.ts`, `products/services/product.ts`, `products/models/product.model.ts`. Guide: `docs/user-guides/products.md`.

### 4. Scan a product to create/identify it (AI + barcode)
- **Entry route:** Products → **Scan** (camera icon opens `product-scanner` dialog); standalone ingestion page at `/ingest`
- **Steps:**
  1. Open the Product Scanner (`products/components/product-scanner/product-scanner.component`).
  2. **Camera tab (AI image scan):** Start Camera → Capture → AI returns name/brand/category/price/dimensions.
  3. **Barcode tab:** scan with camera or Bluetooth/USB scanner (`core/services/hardware.service.ts`); formats UPC/EAN/Code 128/QR.
  4. If product exists → opens its details; if new → opens the creation form pre-filled (barcode saved automatically). Optionally **Generate Store Barcode** (`STORE-{SKU}`) for items without manufacturer codes.
  5. Review and Save. (AI features require an AI provider key in **Settings → AI Agents**.)
- **Modules:** products, products/product-ingestion, core (hardware.service, ai.service, settings.service).
- **Key files:** `products/components/product-scanner/product-scanner.component.ts`, `products/product-ingestion/product-ingestion.ts`, `core/services/hardware.service.ts`, `core/services/ai.service.ts`. Guide: `docs/user-guides/product-scanner.md`.

### 5. Create a purchase order to a supplier (incl. AI invoice ingest)
- **Entry route:** Purchasing → **Suppliers** (`/suppliers`) and **Purchase Orders** (`/suppliers/po`)
- **Steps:**
  1. (If new vendor) **+ Add Supplier** → fill name, contact, phone, address, lead-time days; Save (`supplier-detail` at `/suppliers/id/new`).
  2. Go to Purchase Orders list (`purchase-order-list`); filter by supplier/status/date; review KPI summary.
  3. **+ Create PO** (`/suppliers/po/create`, `purchase-order-edit`): either drag-drop an invoice to AI-extract supplier/currency/shipping/tax/line items, or enter manually (select supplier, add line items via product search / `quick-product-dialog`, set status Draft/Ordered/Received).
  4. Alternatively **Import PO** (`po-ingest-dialog`): upload a supplier document → staged in a review queue (Pending/History/All; "Reject stale" for >30 days) → approve to create a Draft PO. Unmatched lines resolved via Create product / Learn alias.
  5. When goods arrive: open PO → **Import Invoice** to match (`invoice-match-dialog`: Matched/Diff/Unmatched, Apply Invoice Values; allocate landed costs via `cost-allocation-dialog`) → **Mark as Received** (`receiving-dialog`), which updates internal stock and recalculates average cost.
- **Modules:** suppliers, products, core (ai.service, currency.service).
- **Key files:** `suppliers/purchase-orders/purchase-order-edit/purchase-order-edit.component.ts`, `suppliers/purchase-orders/po-ingest-dialog/po-ingest-dialog.component.ts`, `suppliers/purchase-orders/invoice-match-dialog/invoice-match-dialog.component.ts`, `suppliers/purchase-orders/receiving-dialog/receiving-dialog.component.ts`, `suppliers/supplier-detail/supplier-detail.component.ts`, `suppliers/suppliers.service.ts`. Guide: `docs/user-guides/suppliers.md`.

### 6. Do an inventory count (and inventory audit)
- **Entry route:** **Inventory Count** (`/inventory/count`); **Inventory Audit** (`/products/audit`)
- **Steps:**
  1. Open count list (`inventory-count-list`); start or open a count session → detail (`/inventory/count/:id`, `inventory-count-detail`).
  2. Add items by scanning SKUs (`scan-sku-dialog`, using `hardware.service`) or manual entry; enter counted quantities.
  3. Reconcile counted vs expected; commit adjustments to on-hand stock (`inventory-count.service`).
  4. Review the full change history later via **Inventory Audit** (`inventory-audit.component`, `inventory-audit.service`).
- **Modules:** inventory-count, products (audit), core (hardware.service).
- **Key files:** `inventory-count/pages/list/inventory-count-list.component.ts`, `inventory-count/pages/detail/inventory-count-detail.component.ts`, `inventory-count/components/scan-sku-dialog/scan-sku-dialog.component.ts`, `inventory-count/services/inventory-count.service.ts`, `products/pages/inventory-audit/inventory-audit.component.ts`.

### 7. Connect a marketplace + publish an AI listing
- **Entry route:** Marketplaces → **Channels** (`/marketplaces`); App credentials in **Settings → Integrations/Marketplaces**
- **Steps:**
  1. (Admin) Configure App Credentials (Client ID/Secret) for Amazon / MercadoLibre. Note: per `settings.md`, marketplace credentials are entered from the Marketplaces connect flow, not the Settings tab; tokens stored AES-256-GCM.
  2. **+ Connect Account** → pick platform → **Authorize** → OAuth redirect → return to `/marketplaces/:type/callback` (`marketplace-callback`) with the connection established.
  3. Open a connected account (`/marketplaces/:id`, `marketplace-detail`) to view synced listings and sync status.
  4. From a product's details, **Create Listing** (`marketplace-listing-dialog`): pick channel (Amazon EN / MercadoLibre ES / eBay), **Generate with AI** title/description/keywords, edit, Save as draft (PENDING until published), then Publish.
- **Modules:** marketplaces, products, settings, core (ai.service, settings.service).
- **Key files:** `marketplaces/pages/marketplace-list/marketplace-list.ts`, `marketplaces/pages/marketplace-detail/marketplace-detail.ts`, `marketplaces/pages/marketplace-callback/marketplace-callback.ts`, `marketplaces/components/marketplace-listing-dialog/marketplace-listing-dialog.component.ts`, `marketplaces/marketplace-catalog.service.ts`, `settings/services/integrations.service.ts`. Guides: `docs/user-guides/marketplaces.md`, `docs/user-guides/settings.md`.

### 8. Push stock to MercadoLibre Full via a stock transfer (core fulfillment loop)
- **Entry route:** Marketplaces → **Stock Transfers** (`/marketplaces/transfers`)
- **Steps:**
  1. Mental model: stock lives at `default` (warehouse), `ml-full`, `amazon-fba`. PO receiving updates internal stock only; moving it to a channel is always an explicit transfer.
  2. **New Transfer** (`stock-transfer-create-dialog`): pick destination (ML Full / Amazon FBA), search products, set units → **Create draft** → detail page (`stock-transfer-detail`), status Draft.
  3. Ship: **Mark shipped** (status only) or **Ship + reserve inbound** (calls marketplace API, stores `external_inbound_id` — the typical ML Full path). Source stock is decremented; an inventory-adjustment audit row is written.
  4. Receive: **Receive items** (`receive-transfer-dialog`) → Record receipt → status Partially received / Received. Discrepancies (qty_received ≠ qty_shipped) surface on **Reconciliation** (`/marketplaces/transfers/reconciliation`).
  5. **Push qty to listings**: updates `available_quantity` on each `marketplace_listing`; result panel reports synced / failed (often expired OAuth) / no-listing-yet.
  6. (Bulk) **Allocation planner** (`/marketplaces/transfers/planner`): split received inventory across ML Full + Amazon FBA in one pass; creates one draft transfer per destination.
- **Modules:** marketplaces (stock-transfers), products, inventory-count (on-hand source), core.
- **Key files:** `marketplaces/stock-transfers/stock-transfer-list/stock-transfer-list.ts`, `.../stock-transfer-create-dialog/stock-transfer-create-dialog.ts`, `.../stock-transfer-detail/stock-transfer-detail.ts`, `.../receive-transfer-dialog/receive-transfer-dialog.ts`, `.../stock-transfer-planner/stock-transfer-planner.ts`, `.../stock-transfer-reconciliation/stock-transfer-reconciliation.ts`, `marketplaces/stock-transfers/stock-transfer.service.ts`. Guide: `docs/user-guides/marketplaces.md` (Stock Transfers).

### 9. Handle a sales order
- **Entry route:** `/orders`
- **Steps:**
  1. Open Orders list (`sales-order-list`): ML + Amazon orders (ingested via webhook + back-fill poller) alongside internal `FULCRUM` orders.
  2. Open an order → detail (`/orders/:id`, `sales-order-detail`): header with channel/number/date/status/total in native currency + external-reference link.
  3. Read the **Economics** card (revenue − COGS − fees − shipping − ad spend − other = net profit + margin%, with settled vs estimated badge); for non-MXN orders an MXN-equivalent line shows the FX rate applied on the order date.
  4. Review line items (with unmatched-SKU markers + per-line margin), the Status timeline (ml_webhook/ml_poll/amazon_poll/manual), and refund events.
  5. **Record return** (`record-return-dialog`) when a physical return arrives — re-credits stock.
- **Modules:** sales-orders, products, payments, core (currency.service).
- **Key files:** `sales-orders/pages/sales-order-list/sales-order-list.ts`, `sales-orders/pages/sales-order-detail/sales-order-detail.ts`, `sales-orders/components/record-return-dialog/record-return-dialog.component.ts`, `sales-orders/services/sales-orders.service.ts`. Guide: `docs/user-guides/orders.md`.

### 10. Answer a buyer question (Q&A with SLA)
- **Entry route:** Marketplaces → **Buyer Questions** (`/reports/qa`)
- **Steps:**
  1. Open the Q&A page (`dashboard/pages/qa-page`): buyer questions ingested from the ML questions webhook (per repo commit log: webhook wired into Q&A ingestion).
  2. Review pending questions and their SLA status (Buyer Q&A SLA reports, backend per commit log).
  3. Draft and post an answer (AI-assisted via `ai.service` **(inferred)**).
  4. Track SLA adherence to keep response times within target.
- **Modules:** dashboard (qa-page), marketplaces (ML webhook source), core (ai.service).
- **Key files:** `dashboard/pages/qa-page/qa-page.component.ts`. (Backend Q&A ingestion + SLA reports per commit log; ML questions webhook → Q&A ingestion.)

### 11. Reconcile payments / payouts (with refunds & returns)
- **Entry route:** `/payments`
- **Steps:**
  1. Open Payments (`payments-page`): marketplace settlements / payouts.
  2. Drill a settlement (`payment-detail-dialog`); cross-check against orders' net margin (settled vs estimated fees; Amazon fee-split per commit log).
  3. Review refunds (`/reports/refunds`, `refunds-page`) and returns (`/reports/returns`, `returns-page`) for adjustments that reverse cost breakdowns.
- **Modules:** payments, dashboard (refunds/returns pages + widgets), sales-orders, core (currency.service).
- **Key files:** `payments/pages/payments-page/payments-page.component.ts`, `payments/pages/payment-detail-dialog/payment-detail-dialog.component.ts`, `payments/services/payments.service.ts`, `dashboard/pages/refunds-page/refunds-page.component.ts`, `dashboard/pages/returns-page/returns-page.component.ts`.

### 12. Record an expense (with AI receipt scan)
- **Entry route:** Purchasing → **Expenses** (`/expenses`)
- **Steps:**
  1. Open Expenses (`expense-list`): KPI cards (Total, Recurring, One-time, Entries); sort/filter by category/type/date.
  2. **+ Add Expense** (`expense-dialog`): pick One-time or Recurring; fill description, amount (MXN), category (or custom), date, payment method, reference.
  3. (AI) drag-drop a receipt (PDF/image) → AI fills merchant/date/amount/category; review and save. Attach receipts to existing expenses for record-keeping.
  4. Expense feeds profitability: Net Profit = Revenue − COGS − Marketplace Fees − Expenses.
- **Modules:** expenses, core (ai.service, currency.service).
- **Key files:** `expenses/components/expense-list/expense-list.ts`, `expenses/components/expense-dialog/expense-dialog.ts`, `expenses/services/expense.service.ts`, `expenses/models/expense.model.ts`. Guide: `docs/user-guides/expenses.md`.

### 13. Run a marketing campaign (and quick posts)
- **Entry route:** `/marketing`
- **Steps:**
  1. Open Marketing (`campaign-list`): KPI widgets, calendar view, campaign table; filter by date/status/channel.
  2. **New Campaign** (`/marketing/new`, `campaign-wizard`): Setup (name/budget/description) → Products to promote → Schedule dates.
  3. Add events on the **Calendar** (`/marketing/calendar`, `campaign-calendar`): drag-drop to reschedule; weekly/monthly views; click an event for detail.
  4. **Quick Post** (`quick-post-dialog`): pick channel, add content + photo, link products; AI Content Assistant generates copy by tone (Professional/Casual/Viral/Luxury/Custom) and optional image; Post Now or Save Draft.
  5. Configure channel connectors at `/marketing/connectors` (`connector-settings`).
- **Modules:** marketing, products (promoted items), core (ai.service).
- **Key files:** `marketing/components/campaign-list/campaign-list.component.ts`, `marketing/components/campaign-wizard/campaign-wizard.component.ts`, `marketing/components/campaign-calendar/campaign-calendar.component.ts`, `marketing/components/quick-post-dialog/quick-post-dialog.component.ts`, `marketing/components/connector-settings/connector-settings.component.ts`, `marketing/services/marketing.service.ts`, `marketing/marketing.routes.ts`. Guide: `docs/user-guides/marketing.md`.

### 14. Configure settings (AI, integrations, currency, data) — enabler
- **Entry route:** `/settings`
- **Steps:**
  1. Open Settings (`settings` component) — six tabs: AI Agents, Integrations, Marketing, Inventory, Currency, Data.
  2. **AI Agents:** choose provider + store API key (gates every AI button in the app).
  3. **Integrations:** external API keys (e.g. Google Sheets sync), Pending Sync review (`pending-sync-dialog`), Change Log (`change-log-dialog`).
  4. **Inventory:** low-stock days / quantity thresholds (feed alerts + dashboard).
  5. **Currency:** record FX rates (base→quote, rate, date) used for historical MXN conversion of foreign orders (`currency-tab`).
  6. **Data:** export/import products (CSV/JSON); imports needing review go to Pending Sync. Custom fields managed via `custom-field-list` / `custom-field-dialog`.
- **Modules:** settings, core (settings.service, currency.service).
- **Key files:** `settings/components/settings/settings.ts`, `settings/components/tabs/{ai,integrations,marketing,inventory,currency,data}-tab.component.ts`, `settings/services/integrations.service.ts`, `settings/services/custom-field.service.ts`. Guide: `docs/user-guides/settings.md`.

### 15. Manage team members (admin)
- **Entry route:** Management → **Users** (`/users`)
- **Steps:**
  1. Open Users list (`user-list`, AdminGuard); create (`/users/create`, `user-form` / `user-create-modal`) or edit (`/users/edit/:id`).
  2. Reset passwords (`password-reset-dialog`, `generated-password-dialog`), bulk import (`user-bulk-import-dialog`, `bulk-import.service`).
  3. Review the admin audit log (`/users/audit-logs`, `audit-log-list`). Any user edits own profile at `/users/account` (`account-management`, no AdminGuard).
- **Modules:** users, core (admin.guard).
- **Key files:** `users/components/user-list/user-list.ts`, `users/components/user-form/user-form.ts`, `users/components/account-management/account-management.ts`, `users/components/audit-log-list/audit-log-list.ts`, `users/services/user.service.ts`, `core/guards/admin.guard.ts`.

---

## Notable observations for redesign
- The two-expander grouping (**Purchasing** = POs/Suppliers/Expenses; **Marketplaces** = Channels/Transfers/Health/Buyer Questions) is the spine of the IA, but several high-value pages are reachable only by deep link (order detail, transfer planner/reconciliation, inventory audit history, refunds/returns pages) — discoverability gap.
- **Buyer Questions** lives under Marketplaces in nav but its component is `dashboard/pages/qa-page` and its route is `/reports/qa` — module/route/nav mismatch worth normalizing.
- **AI is gated globally** by a provider key in Settings → AI Agents; every AI affordance (product scan, listing gen, PO/receipt extraction, marketing copy, likely Q&A drafting) silently disables without it — a key onboarding dependency.
- `/ingest` is the only functional route missing `AuthGuard` (likely a bug); `/marketplaces` is registered twice in `app-routing.module.ts`.
