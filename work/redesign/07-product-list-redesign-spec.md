# Fulcrum Product-List — FINAL Unified Redesign Spec

**Status:** Implementation-ready. Lead-designer final call.
**Component:** `frontend/src/app/products/components/product-list/` (`product-list.ts` / `.html` / `.scss`)
**Theme:** Obsidian & Chile (DARK default, warm-paper LIGHT), token-driven, OnPush, Transloco es-MX default.

This spec synthesizes three committed directions (A "dense power", B "visual grid", C "adaptive hybrid") and the four research briefs into ONE buildable system. Where they conflicted, decisions are made here and the rationale is stated.

---

## 0. The decisive synthesis (conflicts resolved)

| Conflict | A | B | C | **FINAL DECISION** |
|---|---|---|---|---|
| Default desktop view | table | grid | adaptive | **Table is desktop default; grid is mobile default + an explicit desktop toggle.** Sofía lives in a dense triage console all day; grid wins phones. (A+C over B.) |
| Progressive disclosure | tooltips | card peek | row expander / card peek | **Adopt C's one-interaction-deeper layer** via an **overlay panel** anchored to the row (keeps virtual-scroll `itemSize` fixed) + a grid card peek bottom-sheet. The 3-bucket stock explainer lives here. |
| Density steps | 40/48/56 | 40/48/56 | 44/52/60 | **40 / 48 / 56** (Compacta / Normal / Cómoda). Rounder, matches A/B and the research; 8px rhythm. |
| Status pill fill | tinted | tinted/outline | **outline-only (no `--*-rgb`)** | **C wins on token reality:** there are NO `--success-rgb/--warning-rgb/--error-rgb` triplets. Pills = `--bg-raised` fill + 1px status-color border + status-color icon+text. This is also the a11y-correct non-color-redundant pattern. |
| Spacing scale | `--space-*` 8px-base | `--space-*` 8px-base | **numeric 4px scale** | **Numeric 4px scale confirmed in source:** `--space-1=4 … --space-4=16 --space-6=24 --space-8=32`. No `-sm/-md` spacing tokens. |
| Radius scale | sm/md | sm/md | **xs/sm/md/lg/pill** | **Confirmed:** `--radius-xs/sm/md/lg/pill`. Pills use `--radius-pill`. |

Everything else (precomputed VM + signals + CDK fixed-size virtual scroll, server-side sort, retire infinite-scroll FAB, kill scroll-listener leak, token-fix all raw hex, one status vocabulary, saved-view chips with counts, cross-page select-all fix, bulk price edit) is **common to all three** and is adopted wholesale.

---

## 1. Design principles + the single status/semantic visual language

### 1.1 Principles

1. **The default row answers four questions in under a second** — *Can it sell on ML? (status) · Can a buyer buy it now? (ML-available stock) · Do I need to reorder? (reorder/days-left) · Is it worth selling? (price + margin).* Everything else is one interaction deeper.
2. **Problems are loud; healthy is quiet.** Out/closed/negative = `--error-color`; low/paused/sin-publicar/reorder/thin-margin = `--warning-color`; healthy/active = muted `--success-color` or neutral. Never paint a screen of low-stock rows in brand red.
3. **Status is never color-alone.** Every status = **icon/shape + word (+ count) + color**, ≥3:1 non-text contrast (WCAG 1.4.11). Pills are outline-style.
4. **Brand discipline.** `--primary-color` (chile-red) = the single primary button + destructive Delete ONLY. `--accent-color` (cool blue) = ALL interactive chrome (chips, toggles, links, focus rings, selected state, "¿0?"). `--accent-2` (gold) = campaign/AI only. `--ml-yellow` = the ML "Full" source chip ONLY.
5. **One view-model, two renderers.** Table and grid read identical `ProductRowVM` fields and render the same pills. This kills the existing grid (`stock_quantity`) vs table (`getCurrentStock()`) disagreement.
6. **Render only the visible window.** CDK fixed-size virtual scroll for both views; paginated fetch + virtualized render; server-side sort. No per-row method calls in templates.
7. **Honest es-MX/MXN.** `$1,234.50` peso-prefix, comma thousands, period decimal, 2 decimals; only show a currency code when `currency !== 'MXN'`.

### 1.2 The status/semantic language (one vocabulary → exact tokens)

Pill construction (all): `background: var(--bg-raised)`; `border: 1px solid <token>`; icon + text in `<token>`; `border-radius: var(--radius-pill)`; padding `var(--space-1) var(--space-2)`.

| Concept | State | Material icon | Word (es-MX) | Token (border + icon + text) | Emphasis |
|---|---|---|---|---|---|
| **Stock health** | healthy | `check_circle` | `Disp.` + n | `--success-color` | quiet (muted/neutral) |
| | low | `warning` (triangle) | `Bajo` + n | `--warning-color` | medium |
| | out | `cancel` | `Sin stock` | `--error-color` | loud |
| | on-hand>0, ML-avail=0 | `info` | `Sin stock` + `¿0?` | text `--error-color`, `¿0?` link `--accent-color` | opens explainer |
| **ML listing** | active | `radio_button_checked` | `Activa` | `--success-color` (muted) | quiet |
| | paused | `pause_circle` | `Pausada` | `--warning-color` | medium |
| | unlisted | `cloud_off` | `Sin publicar` | `--warning-color` | medium, action-inviting (kebab → "Publicar en ML") |
| | closed | `block` | `Cerrada` | `--error-color` | loud |
| **ML source / Full** | — | `bolt` | `Full` | **`--ml-yellow` ONLY** | source marker, not health |
| **Reorder** | triggered | `inventory_2` | `Reordenar` | `--warning-color` | sortable; NOT red |
| **Margin** | healthy ≥20% | — | `{n}%` | `--text-main` | neutral |
| | thin 10–20% | `trending_down` | `{n}%` | `--warning-color` | tooltip = MXN spread |
| | negative/<10% | `trending_down` | `{n}%` | `--error-color` | |
| **Bundle** | is_bundle | `widgets` | `Kit` / `Kit · {n}` | `--accent-color` text on `--bg-raised` | informational tag, not a column |
| **Campaign** | active | `local_offer` | `{n}` | `--accent-2` | subtle, droppable |
| **Days of inv.** | below threshold | — | `{n}d` | `--warning-color` else `--text-hint` | |
| **Inbound** | qty known | `local_shipping` | `+{n} en camino` | `--text-secondary` | informational |

---

## 2. Toolbar / header

One sticky toolbar; wraps to two rows below ~900px. Three zones, left→right. Replaces today's 4-mini-FAB ×2 crowding (8 red circles) and the floating infinite-scroll FAB. Chrome is `--accent-color`; the lone primary split-button is the only brand-red moment in the toolbar.

```
┌──────────────────────────────────────────────────────────────────────────────────────────┐
│ ROW 1                                                                                       │
│ 🔎[ Buscar nombre · SKU · código…        ✕]      [▦/☰ Vista] [⤓ Densidad] [⚙] [＋ Agregar ▾]│
├──────────────────────────────────────────────────────────────────────────────────────────┤
│ ROW 2 — quick-views (saved triage chips, scrollable rail)                                   │
│ ⟦Todos 812⟧ ⟦Activa⟧ ⟦Sin publicar 14⟧ ⟦Bajo 28⟧ ⟦Sin stock 9⟧ ⟦Reordenar 37⟧ ⟦Paquetes⟧ ⟦＋⟧│
├──────────────────────────────────────────────────────────────────────────────────────────┤
│ active filters (only when set): ⟨Tipo: Paquete ✕⟩ ⟨Precio ≤ $500 ✕⟩   Limpiar               │
└──────────────────────────────────────────────────────────────────────────────────────────┘
```

**Zone 1 — Search (left).** Full-width-ish field, `--bg-raised`, `--border-color`, focus ring `--accent-color`. Matches **name + SKU + barcode**, partial, case-insensitive. **Route through the existing `debounceTime(400)` + `distinctUntilChanged` stream** — search currently bypasses it; fix. Clear (`✕`) button. Match highlighting in result rows.

**Zone 2 — Right cluster, in order:**
- **View switch** `[▦/☰]` — existing `mat-button-toggle-group` (grid/list), active segment `--accent-color`.
- **Density** `[⤓]` — menu: Compacta 40 / Normal 48 / Cómoda 56. Persisted per-user (`density` signal → `data-density` attr on table host). **Table-mode only** (hidden in grid).
- **Overflow** `[⚙]` `mat-menu` — Column config (show/hide/reorder/freeze + **Restablecer**), advanced-filters panel toggle, dashboard panel toggle, **infinite-scroll setting** (demoted here from its FAB), Escanear, Importar catálogo, Exportar CFDI/SAT.
- **Primary split-button** `[＋ Agregar ▾]` — `mat-flat-button`, `--primary-color`. Main click = Add product; caret menu = {Escanear código, Importar catálogo}. Collapses 4 mini-FABs → 1 primary + overflow. **Render once**; CSS reflows for mobile (delete the duplicate desktop/mobile action blocks).

**Zone 3 — Quick-views rail (ROW 2).** Toggle-pills **with live counts** that double as saved triage views: `Todos · Activa · Sin publicar · Bajo · Sin stock · Reordenar · Paquetes`, then `＋` (save current filter+sort+density+columns as a named view). These ARE the upgraded quick-filter chips (in/out/low) plus the two highest-value ML-Full triage views (`Sin publicar`, `Reordenar`). Selected = `--accent-color` border + text on `--bg-raised`; idle = `--border-color`/`--text-secondary`; counts in `--text-hint`.

**Active-filter chips row** appears only when advanced filters are set: removable chips + `Limpiar`. Replaces the per-CD `(activeFilters | json) != '{}'` test with a `hasActiveFilters()` computed signal.

**Advanced filter panel** stays a collapsible faceted panel (price range, stock range, product type all/product/bundle); its state mirrors into the chips above. **Dashboard panel** stays collapsible (toggled from `⚙`), remembers state.

---

## 3. TABLE / list

### 3.1 Columns + order + alignment

Replaces `select · image · name · sku · cost_price · price · stock · marketplaces · actions`.

| # | Column | Align | Width | Content |
|---|---|---|---|---|
| – | **expander** | center | 32px | `▸` chevron → overlay detail panel. Hover-revealed; always shown for `is_bundle` / `Sin publicar`. |
| 1 | **select** | center | 40px | Checkbox; hover-revealed, persistent when any selected. |
| 2 | **image** | center | 56px | 40–48px square thumb, `--radius-sm`, lazy. |
| 3 | **Producto** | left | flex (min 220px) | Name (`--text-main`, 1-line ellipsis) + subline `SKU` (mono, `--text-hint`) · brand · `Kit` tag if bundle. |
| 4 | **ML** | left | 132px | `app-marketplace-status` pill + `Full` marker (`--ml-yellow`). |
| 5 | **Disponible** | **right** | 120px | Stock pill = **ML-available** count, status-colored, icon+word; inline `¿0?` when on-hand>0 & ML-avail=0. |
| 6 | **Reabasto** | center | 88px | `Reordenar` badge (warning) when triggered, else `{n}d` days-of-inventory in `--text-hint`. |
| 7 | **Precio** | **right** | 104px | `$1,299.00` MXN, `tabular-nums`. |
| 8 | **Margen** | **right** | 84px | `{n}%` status-tinted text; tooltip = MXN spread + cost. |
| 9 | **actions** | center | 48px | Kebab, hover-revealed. |

**Optional columns (off by default, via Columns menu):** `costo` (folds into Margen tooltip by default), `marca`, `velocidad` (`sales_velocity`), `campañas` (`active_campaign_count`).

**Alignment & numerics:** text left; all quantitative cells **right-aligned** with `font-variant-numeric: tabular-nums`. SKU left-aligned in `var(--font-mono)`.

### 3.2 Density modes

`data-density` attribute on the table host drives token overrides (signal flip, OnPush-friendly). **Rows are fixed-height per density** — mandatory for fixed-size virtual scroll. Cells truncate (no wrap); the `¿0?` affordance is an icon-button opening the overlay, never inline text that grows the row.

```scss
.product-table[data-density="compact"]     { --row-h: 40px; --cell-pad-y: var(--space-1); --thumb: 32px; }
.product-table[data-density="default"]     { --row-h: 48px; --cell-pad-y: var(--space-2); --thumb: 40px; }
.product-table[data-density="comfortable"] { --row-h: 56px; --cell-pad-y: var(--space-3); --thumb: 48px; }
```

### 3.3 Row / cell anatomy, hover, inline actions

- **No zebra.** 1px `var(--border-color)` bottom hairline per row. Background reserved for state: hover `--bg-hover`; selected `--bg-raised` + 2px inset `--accent-color` left bar; focus ring `--accent-color`.
- **Hover:** checkbox + kebab + expander chevron fade in (`--dur-fast` / `--ease-standard`); row bg → `--bg-hover`.
- **Inline edit (P2, design cell now):** click `Precio` / `costo` / `Reabasto` cell → inline input, Enter/blur commits. High-stakes (stock adjust, bundle composition) stays in dialogs.

### 3.4 Progressive disclosure — the overlay expander

Chevron → overlay panel anchored to the row (`--dur-base` / `--ease-standard`, `--shadow-md`). Using an **overlay** (CDK Overlay) instead of an inline expanding row keeps virtual-scroll `itemSize` truly fixed. Shows, without leaving the list:
- **3-bucket stock breakdown** (surfaces the existing explainer): `Full: 0 · Bodega: 200 · +50 en camino`, with es-MX sentence *"Tienes 200 en tu bodega; envíalo a MercadoLibre Full para que esté disponible"* + `Enviar a Full` action.
- Bundle component list (for `is_bundle`) with per-component stock.
- Margin math (resale − cost = spread, %); velocity (`sales_velocity`, `days_of_inventory`).
- Quick actions: Ajustar stock · Historial · Reordenar/PO · Publicar en ML (when Sin publicar).

Row body click (not chevron) still opens the **full details dialog** (unchanged). Expander = peek; dialog = deep dive.

### 3.5 Sticky header + sort

- **Sticky header rendered OUTSIDE the virtual viewport** (Option A — avoids the documented CDK sticky-header-in-viewport recycling bugs). Header bg `--bg-header`, labels `--text-secondary`; sortable columns show an `--accent-color` chevron.
- **Sort is server-side:** header sets a `sortKey` signal → refetch. **Drop `MatTableDataSource` / `MatSort`** (client sort over one server-paginated page is misleading).

### 3.6 Selection

- Selection by **ID `Set<number>`** in a signal (survives virtualization). `allSelected` / `someSelected` / `selectedCount` are `computed()`.
- Header checkbox = **select current page** (compare against current-page IDs, NOT `products.length` — fixes the cross-page bug). When page fully selected, a banner row appears: *"Las 50 de esta página seleccionadas — Seleccionar las 812 en total"* (explicit cross-page select-all). `Reset` available.
- **Sticky floating selection bar** slides in on first selection (bottom, `--bg-card`, `--shadow-lg`, pinned on scroll):
  `{n} seleccionados   [Editar precio] [Crear paquete] [⋯ Más]   [Eliminar] [✕]`
  Non-destructive controls `--accent-color`; **Delete = `--primary-color` brand red** (the sanctioned moment). **Bulk price edit is added** (the current gap). **Create-bundle-from-selection preserved.**

---

## 4. GRID / card

Same VM, same pills. Grid wins image-led browsing + mobile. Fixed card height (virtualization).

```
┌───────────────────────────────┐
│ ┌───────────────────────────┐ │  ← 1:1 image, object-fit:cover, --radius-md
│ │                  ⟨⚠ Bajo 3⟩│ │     status overlay top-RIGHT: stock pill (low/out only)
│ │      [ product photo ]     │ │     top-LEFT: ML state pill + Full marker
│ │ ⟨● Activa⟩ ⟨⚡Full⟩  ⟨Kit·3⟩│ │     bottom-left: Kit badge if bundle
│ └───────────────────────────┘ │
│ Audífonos Pro X            ⋮  │  ← name 2-line clamp + kebab
│ SKU-8841 · Acme               │  ← mono SKU · brand, --text-hint
│ ───────────────────────────── │
│ $1,299.00          ⟨⚠ 3 ⟩    │  ← Precio (left) ↔ stock pill (right), one baseline
│ Margen 42%      +6 en camino  │  ← margin (banded) ↔ inbound hint (if any)
└───────────────────────────────┘
```

- **Image: enforced 1:1** (`aspect-ratio: 1/1; object-fit: cover`), `--radius-md`. Empty → centered icon block on `--bg-raised` + `--text-hint` (NO 200px empty well — kills today's mobile waste).
- **Status overlay top-right:** stock pill, shown only when **low/out** (healthy kept off so problems pop). **Top-left:** ML state pill + `Full` marker.
- **Kit badge** bottom-left of image when `is_bundle` (`widgets` + `Kit · {n}`), `--accent-color` tint.
- **Identity:** name 2-line clamp (`--text-main`, `--font-display`); `SKU` mono · brand (`--text-hint`). Kebab top-right of body.
- **Money/stock baseline:** Precio (left, prominent) ↔ stock pill (right). Second line: `Margen {n}%` (banded) ↔ `+{n} en camino` (when inbound known).
- **Card peek (progressive disclosure):** kebab `▾` / long-press → bottom-sheet matching the table overlay (bucket breakdown + "¿0?" explainer + quick actions). Card body tap → details dialog.
- **Dropped from card face** (→ detail dialog): description, full bundle component list, marketplace-icon row (replaced by single ML chip), fixed-36px empty description reserve.
- **Responsive columns:** `grid-template-columns: repeat(auto-fit, minmax(240px, 1fr))` → 2 (mobile) … 5–6 (wide). **Container queries** so the grid responds to its container if the dashboard panel collapses/reflows. Card padding `var(--space-4)`; gap `var(--space-4)`.

---

## 5. Filters, quick-views, empty/loading states

- **Quick-views with counts** (§2 ROW 2) are the headline filter layer + saved triage views. Low-stock quick-filter must respect per-product `low_stock_quantity_threshold` / `reorder_point` (fix the hardcoded `max_stock:10` mismatch).
- **Advanced panel** kept (price/stock ranges, product type all/product/bundle); selections mirror to removable toolbar chips; AND semantics; facet counts.
- **Search:** debounced 400ms + `distinctUntilChanged`, routed through the stream; match highlighting.
- **Loading = skeleton, NOT spinner.** ~10 shimmer rows/cards sized to current `--row-h` / card height; shimmer = `--bg-raised` → `--bg-hover` gradient sweep. No CLS.
- **Two distinct empty states:** (a) no products → "Aún no tienes productos" + `Agregar producto` CTA; (b) no filter matches → "Sin resultados" + `Limpiar filtros` CTA.
- **Reload:** keep the existing sticky top progress bar (`--accent-color`).
- All copy = Transloco keys in BOTH `es-MX.json` and `en.json`.

---

## 6. Responsive + mobile

**Table column collapse priority (drop from the right, least load-bearing first):**
1. `Margen` → fold into Precio tooltip.
2. `Reabasto` days → fold into stock-pill tooltip (keep `Reordenar` as a dot on the pill).
3. `select` header chrome → selection via long-press / card checkbox.
4. `Precio` → merge under the name block.
5. Below ~720px → **auto-switch to grid** (respect `userOverrodeViewMode`).

**Never drop at any width:** image · name+SKU · **ML status** · **Disponible (stock + out/low state)** — the irreducible scanning core.

**Mobile card (Sofía's primary surface), top→bottom:** thumb + name + SKU(mono) + Kit tag · **ML status chip + stock pill on one prominent row** · **Reordenar badge when triggered** · Precio + Margen on one line · kebab. Tap body → details dialog; kebab/peek → {Ajustar stock, Historial, Reordenar, Publicar en ML if Sin publicar, Editar, Eliminar}. Dropped: description, full bundle list, marketplace-icon row.

---

## 7. Performance architecture

### 7.1 Precomputed `ProductRowVM` (P0, do first)

Map each `Product` → flat VM ONCE in the fetch `next:` (or `rxResource` mapper). Template becomes pure property reads — eliminates the ~8 per-row method calls per CD tick (`getCurrentStock` ×5, `getPrimaryImage` ×2, `getEffectiveCost`, `getBundleAverageCost`). Single source of truth fixes grid/table stock disagreement.

```ts
interface ProductRowVM {
  id: number;
  name: string; sku: string; brand: string | null; description: string;
  isBundle: boolean; bundleCount: number;
  bundlePreview: { qty: number; name: string }[];   // first 3, precomputed
  // image
  primaryImageUrl: string;        // fully resolved incl. backend-sized thumb; '' if none
  hasImage: boolean;
  // money
  price: number;                  // default_resale_price
  effectiveCost: number;          // getEffectiveCost()
  avgCost: number; showAvgCost: boolean;
  margin: number;                 // price - effectiveCost (MXN spread)
  marginPct: number;              // margin / price * 100
  marginClass: 'healthy' | 'thin' | 'negative';
  currency: string;               // show code only when !== 'MXN'
  // stock (ML-Full aware)
  currentStock: number;           // getCurrentStock() — total disponible
  mlAvailable: number;            // ml-full bucket
  warehouseStock: number;         // default bucket
  inboundQty: number;             // +N en camino (0 if unknown)
  stockHealth: 'healthy' | 'low' | 'out';
  showWhyZero: boolean;           // warehouse>0 && mlAvailable===0
  daysOfInventory: number | null; // null when >=999 sentinel
  daysWarning: boolean;
  reorderTriggered: boolean;      // currentStock <= (reorder_point ?? low_stock_quantity_threshold)
  // ML listing
  isListed: boolean;              // has any active ML listing
  mlStatus: 'active' | 'paused' | 'unlisted' | 'closed';
  isFull: boolean;                // ml-yellow Full chip
  marketplaceListings: MarketplaceListing[];  // stable ref for app-marketplace-status
  activeCampaignCount: number;
  adjustmentCount: number;
  product: Product;               // original, for dialogs/actions
}
```

In each `next:` handler: `this.rows.set(pageProducts.map(p => this.toRowVM(p)))`.
**Selection is NOT baked into the VM** (would force a full re-map on every toggle). Keep it a `signal<ReadonlySet<number>>`; `[checked]="selectedIds().has(row.id)"` (O(1), explicit signal dep).

### 7.2 Signals + OnPush

Convert `rows`, `isLoading`, `isReloading`, `viewMode`, `density`, `showDashboard`, `selectedIds`, `hasMoreProducts` to `signal()`; derive `chunkedRows`, `allSelected`, `someSelected`, `selectedCount`, `hasActiveFilters` as `computed()`. Delete most `markForCheck()` calls and the `(activeFilters | json)` template expression. Confirm `app-marketplace-status` is OnPush and receives the stable `marketplaceListings` ref from the VM.

### 7.3 CDK fixed-size virtual scroll (both views)

Use `FixedSizeVirtualScrollStrategy` (autosize is `cdk-experimental`, not production-ready). Viewports need `display:block` + explicit height. `trackBy` mandatory.

- **Grid:** `cdk-virtual-scroll-viewport [itemSize]="CARD_ROW_HEIGHT"`; **one virtual item = one row of N cards**: `chunkedRows = computed(() => chunk(rows(), cardsPerRow()))`, `cardsPerRow` from a `ResizeObserver` / container query. `itemSize` = card height + gap. `*cdkVirtualFor="let cardRow of chunkedRows(); trackBy: trackRow"`, inner `@for (row of cardRow; track row.id)`.
- **Table (Option A):** **drop `mat-table`**; render a CSS-grid "table" (`display:grid; grid-template-columns:` shared with the header) inside one viewport via `*cdkVirtualFor="let row of rows(); trackBy: trackId"`, fixed `itemSize = --row-h`, **sticky header OUTSIDE the viewport**. Expander = CDK Overlay (keeps `itemSize` fixed).

### 7.4 Pagination / scroll / sort

- **Lane = paginated fetch + virtualized render.** Keep `MatPaginator`; virtual scroll renders only the visible window within the page.
- **Retire the infinite-scroll FAB and all 3–4 hand-rolled scroll paths** (`window:scroll` HostListener, the **leaked** `document` capture-phase listener never removed in `ngOnDestroy`, container `(scroll)`). CDK viewport owns scrolling. Demote infinite-scroll to a `⚙`-menu setting; if ever needed, reimplement via one debounced `viewport.elementScrolled()`. Scroll-to-top uses `viewport.scrollToIndex(0)`.
- **Server-side sort** (sort key signal → refetch). Funnel fetches through `switchMap` / `rxResource` for cancellation + race-safety.

### 7.5 Images

Plain `<img>` (most robust with recycled virtual nodes) with explicit `width`/`height` (CLS fix) + `loading="lazy"` + `decoding="async"` + `fetchpriority="low"`. Request **backend-sized thumbnails** (`?w=96` for a 48px@2x) — biggest bandwidth win. Replace the base64-SVG `onImageError` and inline `color:#999` with a token-driven `.img-failed` CSS class (`--bg-raised` / `--text-hint`).

### 7.6 CSS containment

`contain: layout paint style` on each card/row; `content-visibility: auto` + `contain-intrinsic-size: var(--row-h)` on the in-DOM-but-offscreen sliver. No blanket `will-change`.

### 7.7 Correctness fixes folded in

- **Delete must reload** the list (today `getProducts()` result is ignored — reassign `rows`).
- **Cross-page selection** semantics (header checkbox vs current page; explicit cross-page banner).
- **Low-stock quick-filter** uses per-product threshold, not hardcoded `max_stock:10`.
- Remove dead code: `onEditProduct` no-op, `openComparisonView` stub, legacy `onPageChange`/`onPageSizeChange`, `pulse-glow` keyframe. Delete stale `product-list.ts.new`.

---

## 8. Token usage cheat-sheet (passes `check_theme_contrast.py` — zero raw hex)

| Element | Token(s) |
|---|---|
| Page / app bg | `var(--bg-app)` |
| Toolbar / card / table body surface | `var(--bg-card)` |
| Search field, pill fill, skeleton base, raised thumb-empty, expander | `var(--bg-raised)` |
| Row/card hover, skeleton shimmer peak | `var(--bg-hover)` |
| Sticky header bg | `var(--bg-header)` |
| Selected row surface | `var(--bg-raised)` + 2px inset `var(--accent-color)` bar |
| Row hairline / pill border / field border | `var(--border-color)`; hover `var(--border-hover)` |
| Name / primary numerics | `var(--text-main)` |
| SKU·brand subline, secondary, inbound | `var(--text-secondary)` |
| Hints, `—`, days, counts, mono SKU | `var(--text-hint)` |
| In-stock / Activa (quiet) | `var(--success-color)` |
| Low / Pausada / Sin publicar / Reordenar / thin margin / days-low | `var(--warning-color)` (outlined pill) |
| Out / Cerrada / negative margin | `var(--error-color)` |
| **Primary split-button + Delete ONLY** | `var(--primary-color)` (tints via `rgba(var(--primary-rgb), a)`) |
| All other interactive chrome, selected, focus ring, `¿0?`, sort chevron, Kit tint, scroll FAB | `var(--accent-color)` |
| Campaign / AI moments | `var(--accent-2)` (tints `rgba(var(--accent-2-rgb), a)`) |
| ML `Full` / source chip ONLY | `var(--ml-yellow)` |
| Radius: pills | `var(--radius-pill)`; thumbs/fields `var(--radius-sm)`; cards `var(--radius-md)` |
| Spacing (numeric 4px scale) | `var(--space-1)=4 / --space-2=8 / --space-3=12 / --space-4=16 / --space-6=24 / --space-8=32` |
| Shadows | `var(--shadow-sm)` cards · `var(--shadow-md)` overlay/expander · `var(--shadow-lg)` selection bar — replace all `rgba(0,0,0,…)` |
| Motion | `var(--dur-fast)` hover reveals · `var(--dur-base)` expander/selection/density · `var(--ease-standard)`. `prefers-reduced-motion` already zeros `--dur-*` in theme. |
| Display / mono / body font | `var(--font-display)` headers+name · `var(--font-mono)` SKU · `var(--font-sans)` body — replace hardcoded `'Space Grotesk'` |

**Hard constraint encoded:** status pill fills MUST use `var(--bg-raised)` (NOT `rgba(var(--success-rgb)…)`, which does not exist — only `--primary-rgb`, `--bg-card-rgb`, `--accent-2-rgb` triplets exist) with border + icon + text in the status token. This is non-color-redundant AND guard-safe.

**Audit raw-hex map (all flagged literals → tokens):** `#cbd5e1`→`--text-secondary`; `#69f0ae`→`--success-color`; `#ffd740`→`--warning-color`; `#ff5252`/`#ff5252`→`--error-color`; `#f1f5f9`→`--bg-hover`; `#475569`/`#e2e8f0`→`--border-color`; `#1e293b`/`#ffffff` (selection bar)→`--bg-card`; off-palette teal `#00BFA5`/`#00DBBD`→`--accent-color`; off-palette pink `#E91E63`/`#D81B60` (create-bundle CTA)→`--accent-color`; marketing gradient `#FF9800→#F57C00`→`--gradient-warn` or warning token; HTML inline `color:#999` (html:399)→`--text-hint`; base64-SVG colors→`.img-failed` class. The entire hand-rolled selection bar (scss:1081–1281) is rebuilt on tokens.

---

## 9. Ordered implementation checklist (engineer)

**Features that MUST keep working** (verify after each phase): bulk multi-select + selection bar, **create-bundle-from-selection**, bulk delete, quick-filter chips, advanced filter panel, search, collapsible dashboard panel, "why 0 disponible?" stock explainer, MatPaginator (+ infinite-scroll now a setting), `is_bundle` bundles + contents preview, `app-marketplace-status`, open details dialog on row/card click, stock-adjustment + stock-history dialogs, scanner + catalog import, deep-link `?open_sku=`.

### P0 — view-model, signals, tokens, correctness (no structural risk)
1. **`product-list.ts`** — add `ProductRowVM` interface + `toRowVM(p)`; populate `rows = signal<ProductRowVM[]>([])` in every fetch `next:`. Remove per-row getters from being template-called (keep them as private helpers used inside `toRowVM`).
2. Convert `isLoading`, `isReloading`, `viewMode`, `density`, `showDashboard`, `selectedIds`, `hasMoreProducts` → signals; add `computed()` for `chunkedRows`, `allSelected`, `someSelected`, `selectedCount`, `hasActiveFilters`. Delete redundant `markForCheck()`.
3. **`product-list.html`** — rewrite table + grid cells as pure property reads (`row.*`). Remove `(activeFilters | json) != '{}'` → `hasActiveFilters()`. Remove inline `style="color:#999"`.
4. Build the **status-pill** markup (one snippet reused in both views) per §1.2; build the **density** `data-density` attribute wiring.
5. **`product-list.scss`** — replace ALL raw hex with §8 tokens; rebuild the selection bar on tokens; add `--row-h`/`--cell-pad-y`/`--thumb` density blocks; hairline rows (drop zebra); right-align + `tabular-nums` on numeric cells; `.img-failed` class.
6. Fix correctness: delete-reload (reassign `rows`); low-stock quick-filter uses per-product threshold; single stock source (VM).
7. Toolbar collapse: 4 mini-FABs ×2 → one `[＋ Agregar ▾]` split + `⚙` overflow + density + view switch; quick-view chips with counts; render once. Add `Sin publicar` + `Reordenar` chips.
8. Run `python …/check_theme_contrast.py` + i18n guard; `ng build`.

### P1 — virtualization, selection, sort, images
9. **Grid virtualization** — `cdk-virtual-scroll-viewport` + `chunkedRows` (1 item = 1 card-row) + `ResizeObserver` `cardsPerRow`; enforce 1:1 card image; status overlay.
10. **Table virtualization (Option A)** — drop `mat-table`/`MatTableDataSource`/`MatSort`; CSS-grid list in viewport; sticky header outside; expander as CDK Overlay.
11. **Server-side sort** (sort key signal → refetch); funnel fetches through `switchMap`/`rxResource`.
12. **Selection across pages** — current-page header checkbox + cross-page select-all banner; add **bulk price edit** action.
13. **Images** — explicit `width`/`height` + `loading="lazy"` + `decoding="async"` + `fetchpriority="low"`; backend-sized thumb request.
14. **Skeleton** rows/cards (token shimmer); two distinct empty states.

### P2 — polish + cleanup
15. Column config (show/hide/reorder/freeze/Restablecer); inline edit (Precio/costo/Reabasto).
16. **Remove** infinite-scroll FAB + all hand-rolled scroll listeners (incl. leaked `document` listener; clean `ngOnDestroy`); `content-visibility`/`contain`.
17. Remove dead code (`onEditProduct`, `openComparisonView`, legacy `onPageChange/Size`, `pulse-glow`); **delete stale `product-list.ts.new`**.

### New small files (optional)
- `product-row.vm.ts` (the `ProductRowVM` interface + a pure `toRowVM` factory) if `product-list.ts` gets too large.
- `status-pill/` shared component (OnPush) if the pill is reused beyond this view.

### New i18n keys (add to BOTH `es-MX.json` and `en.json`)

| Key | es-MX | en |
|---|---|---|
| `products.searchPlaceholder` | `Buscar nombre, SKU o código…` | `Search name, SKU or code…` |
| `products.filter.todos` | `Todos` | `All` |
| `products.filter.activa` | `Activa` | `Active` |
| `products.filter.sinPublicar` | `Sin publicar` | `Unlisted` |
| `products.filter.bajo` | `Bajo` | `Low` |
| `products.filter.sinStock` | `Sin stock` | `Out of stock` |
| `products.filter.reordenar` | `Reordenar` | `Reorder` |
| `products.filter.paquetes` | `Paquetes` | `Bundles` |
| `products.filter.saveView` | `Guardar vista` | `Save view` |
| `products.filter.clear` | `Limpiar` | `Clear` |
| `products.status.disponible` | `Disponible` | `Available` |
| `products.status.bajo` | `Bajo` | `Low` |
| `products.status.sinStock` | `Sin stock` | `Out of stock` |
| `products.status.activa` | `Activa` | `Active` |
| `products.status.pausada` | `Pausada` | `Paused` |
| `products.status.sinPublicar` | `Sin publicar` | `Unlisted` |
| `products.status.cerrada` | `Cerrada` | `Closed` |
| `products.status.full` | `Full` | `Full` |
| `products.status.reordenar` | `Reordenar` | `Reorder` |
| `products.label.kit` | `Kit` | `Kit` |
| `products.label.margin` | `Margen` | `Margin` |
| `products.label.inbound` | `{{n}} en camino` | `{{n}} incoming` |
| `products.label.days` | `{{n}}d` | `{{n}}d` |
| `products.whyZero` | `¿Por qué 0?` | `Why 0?` |
| `products.whyZeroExplainer` | `Tienes {{n}} en tu bodega; envíalo a MercadoLibre Full para que esté disponible.` | `You have {{n}} in your warehouse; send it to MercadoLibre Full to make it available.` |
| `products.action.sendToFull` | `Enviar a Full` | `Send to Full` |
| `products.action.publishMl` | `Publicar en MercadoLibre` | `Publish on MercadoLibre` |
| `products.action.reorder` | `Reordenar` | `Reorder` |
| `products.bulk.editPrice` | `Editar precio` | `Edit price` |
| `products.bulk.more` | `Más` | `More` |
| `products.bulk.selectedCount` | `{{n}} seleccionados` | `{{n}} selected` |
| `products.bulk.selectAllPages` | `Seleccionar las {{total}} en total` | `Select all {{total}}` |
| `products.bulk.pageSelected` | `Las {{n}} de esta página seleccionadas` | `{{n}} on this page selected` |
| `products.density.compact` | `Compacta` | `Compact` |
| `products.density.normal` | `Normal` | `Default` |
| `products.density.comfortable` | `Cómoda` | `Comfortable` |
| `products.empty.noProducts` | `Aún no tienes productos` | `No products yet` |
| `products.empty.noProductsCta` | `Agregar producto` | `Add product` |
| `products.empty.noResults` | `Sin resultados` | `No results` |
| `products.empty.noResultsCta` | `Limpiar filtros` | `Clear filters` |
| `products.skeleton.aria` | `Cargando productos` | `Loading products` |
| `products.columns.title` | `Columnas` | `Columns` |
| `products.columns.reset` | `Restablecer` | `Reset` |

---

## 10. ASCII sketches (final)

**Toolbar**
```
┌──────────────────────────────────────────────────────────────────────────────────────────┐
│ 🔎[ Buscar nombre, SKU, código…              ✕]   [▦/☰][⤓ Densidad][⚙][ ＋ Agregar ▾ ]      │
│ ⟦Todos 812⟧⟦Activa⟧⟦Sin publicar 14⟧⟦Bajo 28⟧⟦Sin stock 9⟧⟦Reordenar 37⟧⟦Paquetes⟧⟦＋⟧      │
│ ⟨Tipo: Paquete ✕⟩ ⟨Precio ≤ $500 ✕⟩  Limpiar                                                │
└──────────────────────────────────────────────────────────────────────────────────────────┘
```

**Table header (sticky, outside viewport)**
```
│▸│☐│img│ PRODUCTO              │ ML        │  DISPONIBLE │ REABASTO │  PRECIO │ MARGEN │⋮│
```

**Table row — Cómoda (56px), hover state**
```
│▸│☑│▢▢ │ Audífonos Pro X       │ ●Activa ⚡│  ⚠ Bajo  8  │Reordenar │$1,299.00│  42%   │⋮│
│ │ │   │ SKU-8841 · Acme · Kit │   Full   │  ¿0?        │   3d     │         │ (warn) │ │
└─ overlay expander: Full 0 · Bodega 200 · +50 en camino · [Enviar a Full] · Margen $384 (42%) · 4/día ─┘
```

**Table row — Compacta (40px)**
```
│▸│☑│▫│ Audífonos Pro X  SKU-8841·Kit │ ●Activa⚡ │ ⚠ Bajo 8 │Reordenar│ $1,299.00 │ 42% │⋮│
```

**Grid card**
```
┌───────────────────────────┐
│ ┌───────────────────────┐ │
│ │              ⟨⚠ Bajo 3⟩│ │  stock pill (warning, outlined), top-right
│ │    [ product image ]  │ │
│ │ ⟨●Activa⟩ ⟨⚡Full⟩ ⟨Kit·3⟩│ │  ML pill (quiet) + Full (ml-yellow) + Kit (accent)
│ └───────────────────────┘ │
│ Audífonos Pro X        ⋮  │
│ SKU-8841 · Acme           │
│ ───────────────────────── │
│ $1,299.00       ⟨⚠ 3 ⟩    │
│ Margen 42%   +6 en camino │
└───────────────────────────┘
```

---

## 11. Implementation notes & deviations (2026-06-02, shipped)

Implemented P0+P1+P2 in `product-list.ts/.html/.scss` + new `product-row.vm.ts`, backend
server-side sort, and i18n. Verified: theme guard (product-list **removed from allowlist**,
now actively checked, clean), i18n parity (no missing keys/dupes), `ng build` (no warnings),
17/17 component specs, and live screenshots (`work/redesign/shots/step7-products/`).

Pragmatic deviations (each backed by a data/architecture reason):
1. **Server-side sort** added for DB columns (`name`, `default_resale_price`, `cost_price`,
   `created_at`, `id`) via new `sort_by`/`sort_order`. **Stock & Margin are NOT sortable**
   (computed aggregates — partial-page sort would mislead).
2. **"Full" chip and "+N en camino" inbound dropped** — the list payload has no ML-fulfillment
   flag or inbound-qty field. ML pill shows listing status derived from `marketplace_listings`;
   the 3-bucket breakdown is computed from `inventory_items` locations where present.
3. **Expander "peek" = `mat-menu`** (buckets + quick actions), not CDK Overlay — robust with
   virtual-scroll recycling, keeps `itemSize` fixed. Row body click still opens the full dialog.
4. **Infinite-scroll mode + FAB + all hand-rolled/leaked scroll listeners removed** (replaced by
   pagination + CDK virtual scroll), not demoted to a setting.
5. **Column config = show/hide + reset** (costo/marca/velocidad/campañas). Drag-reorder/freeze deferred.
6. **Inline edit = price only**; bulk price edit added to the selection bar. Cost/reorder inline deferred.
7. **Grid card image fixed-height (150px, cover)**, not strict 1:1 — fixed-size virtual scroll needs a constant itemSize.
8. **`app-marketplace-status` replaced by the unified ML status pill** for one status language across both views.
