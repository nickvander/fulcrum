# Fulcrum — Design System & First-Redesign Plan
### BOLD & MODERN, build-ready for Angular 21 + Angular Material 20 + SCSS + Transloco (es-MX)

_Design Lead deliverable. Turns `03-market-brand-brief.md` (Leverage Indigo + pivot-wedge identity), `04-pm-decision.md` (P0/P1 scope), and `00-journey-map.md` (IA + journeys) into concrete tokens, component language, a shell redesign, page plans, and an engineer-ordered implementation sequence — mapped onto the **actual** code in `frontend/src/styles.scss`, `frontend/src/theme/variables.scss`, `frontend/src/theme/mixins.scss`, `frontend/src/app/core/`, and verified versions (Angular 21.0.3, @angular/material 20.2.7, @ngneat/transloco 6.0.4)._

---

## 0. Ground truth: what exists today (verified by reading the code)

The redesign is additive and re-points existing tokens; it is not a rewrite. Confirmed facts:

- **Theming is hand-rolled CSS custom properties — there is NO Angular Material SCSS theme yet.** `styles.scss` does **not** `@use '@angular/material'`; nothing in `src/**/*.scss` calls `mat.core` / `mat.theme` / `mat.define-theme`. The app currently renders Material's unstyled MDC defaults and recolors them through custom properties + a ~970-line `body.dark-theme` `!important` override pile in `styles.scss`. **The M3 theme layer must be *introduced*** (see §3) — this is the single biggest leverage point and the reason brand color/Roboto look generic today.
- **The token contract to preserve** (defined in `theme/variables.scss`, light on `:root`, dark on `.dark-theme`): `--primary-color/-light/-dark`, `--accent-color/-light/-dark`, `--success-color/-bg`, `--warning-color/-bg`, `--error-color/-bg`, `--info-color/-bg`, `--bg-app/-card/-hover/-header`, `--text-main/-secondary/-hint/-on-primary`, `--border-color/-hover`, `--border-radius` (currently **12px**), `--spacing-unit` (8px), `--card-padding` (24px), `--shadow-sm/-md/-lg`, and marketing `--gradient-*`. **Keep every name**; the redesign changes values and adds new tokens (ramps, fonts, motion).
- **Dark mode = `body.dark-theme`**, toggled from the **sidenav footer** menu (`sidenav.ts` `toggleTheme()` → `settings.service.saveSettings({theme})`, persisted in `localStorage('fulcrum_settings')`). Reuse this switch; do not add a new one. **[GAP to fix in wiring]** `toggleTheme()` saves the setting but the code that actually adds/removes `dark-theme` on `<body>` lives elsewhere (likely `app.component`); confirm it flips on save.
- **Fonts are effectively unstyled.** `index.html` loads only **Material Icons via Google CDN**; `Inter` is named in `body { font-family }` but **is not actually loaded anywhere**, and Roboto is the de-facto MDC default. So "swap to Inter + display + mono" means *actually adding* the fonts (self-host), not just referencing them.
- **i18n default is wrong for a Mexico-first product.** `transloco-root.module.ts`: `availableLangs: ['en','es-MX']`, **`defaultLang: 'en'`**. Locale data `es-MX` is registered in `main.ts`. Brand pillar is native es-MX → flip the Transloco default to `es-MX` (small, high-trust). Language switch (EN / Español MX) lives in the sidenav footer.
- **Reusable primitives already exist** — lean on them: `theme/mixins.scss` (`card-style`, `kpi-card($gradient)`, `status-badge`/`-active`/`-warning`/`-error`, `filter-toolbar`, `touch-target` = 48px, `sleek-scrollbar`); `styles.scss` `app-chip-success/-warning/-error` (pill, selected/unselected) via `app-chip-color`; the normalized compact paginator; `sleek-select` (pill outline); 16px dialog radius; `_forms.scss` (`page-container`, `page-header`, `form-row`, `search-field-compact`, `ai-badge`). **Note:** `kpi-card` currently fills with a brand **gradient** — the brief warns against heavy gradients/painted regions, so re-point KPI cards to neutral surfaces with a big number (see §4).
- **Shell** = `core/components/header` (mat-toolbar: hamburger + "Fulcrum" wordmark + `change_history` triangle icon — note this triangle already gestures at the pivot-wedge mark) and `core/components/sidenav` (groups `nav.menu` / `nav.management` via `mat-expansion-panel` for Purchasing + Marketplaces; user footer with theme toggle, language, sign out). Nav labels are Transloco `nav.*` keys. **`purchasingExpanded = true` / `marketplacesExpanded = false` are hardcoded in `sidenav.ts`** — the PM's "auto-expand active group" replaces these with route-derived state.
- **PWA is real**: `@angular/service-worker` 21.0.3 + `manifest.webmanifest` present.

---

## 1. Design principles (the five brand adjectives, operationalized)

From the brief: **Decisive, Sharp/intelligent, Composed, Grounded/local, Bold.**

1. **Bold = contrast + type + one vivid color, never painted regions.** Leverage Indigo is for primary actions, active nav, focus, identity. Surfaces stay near-neutral so dense data is the hero (brief don't: "Don't paint large regions in the brand color").
2. **Decisive = exactly one filled primary action per view.**
3. **Composed under density.** Operator screens (Orders, Products, Stock Transfers, Q&A, Payments) are dense tables tuned for scan speed via Material density `-2`/`-3`.
4. **Sharp/intelligent = AI is a distinct premium surface.** AI affordances get the cyan accent + soft glow + sparkle; where no AI key is configured they **hide, not disable** (generalize `@if aiReady`; PM #6).
5. **Grounded = es-MX + money first.** `tú` voice, MXN default, tabular numerals on every money/qty cell, layouts that absorb +20–25% Spanish length.

---

## 2. Design Tokens

Emitted as **(a)** CSS custom properties on `:root` / `body.dark-theme` (the existing contract, re-pointed) and **(b)** inputs to a new Angular Material M3 theme (§3). Recommended scheme: **Leverage Indigo (light) + Cockpit Dark (dark)** per the brief; **Volcán** is a one-map swap (§2.2).

### 2.1 Color — Leverage Indigo (recommended)

**Brand / lead ramp** (core 500 = `#4F46E5`):

| New token | Light | Dark (Cockpit) |
|---|---|---|
| `--brand-50`  | `#EEF0FF` | `#1A1B3A` |
| `--brand-100` | `#DDE0FF` | `#23255A` |
| `--brand-200` | `#BEC4FF` | `#2E3180` |
| `--brand-300` | `#959EFF` | `#3E43A8` |
| `--brand-400` | `#6E74F2` | `#5A60E0` |
| `--brand-500` | `#4F46E5` | `#7C82FF` |
| `--brand-600` | `#4338CA` | `#9AA0FF` |
| `--brand-700` | `#372FA8` | `#B9BEFF` |
| `--brand-800` | `#2A2480` | `#1E1B4B` (deep ink) |
| `--brand-900` | `#1E1B4B` | `#ECEEFF` |

Re-point existing: `--primary-color: var(--brand-500)`, `--primary-light: var(--brand-300)`, `--primary-dark: var(--brand-800)`.

**Accent / AI signal — electric cyan** (AI moments, focus, chart highlights only; never a 2nd brand color):

| New token | Light | Dark |
|---|---|---|
| `--accent-500` | `#06B6D4` | `#22D3EE` |
| `--accent-600` | `#0891B2` | `#67E8F9` |

Re-point: `--accent-color: var(--accent-500)`, `--accent-light: var(--brand-300)` (note: today `--accent-light` is teal; if components rely on it for AI buttons, keep it cyan-ish).

**Semantic** (light = brief; dark aligned to the chip colors already in `styles.scss` so existing `.dark-theme .app-chip-*` rules stay consistent):

| Token (existing) | Meaning | Light | Dark |
|---|---|---|---|
| `--success-color` | pagado / enviado / en stock | `#16A34A` | `#34D399` |
| `--warning-color` | stock bajo / tiempo de respuesta en riesgo | `#D97706` | `#FBBF24` |
| `--error-color`   | vencido / sin stock / error | `#DC2626` | `#F87171` |
| `--info-color`    | estado neutral | `#0EA5E9` | `#38BDF8` |
| `--*-bg`          | chip tint | `color-mix(in srgb, var(--*-color) 12%, var(--bg-card))` | `color-mix(... 22% ...)` |
| `--ml-yellow` *(new)* | ML "source/channel" chip ONLY | `#FFE600` | `#FFE600` |

**Neutrals / surfaces** (re-point existing names):

| Token | Light | Dark (Cockpit) |
|---|---|---|
| `--bg-app`        | `#FAFAFB` | `#0B0F14` |
| `--bg-card`       | `#FFFFFF` | `#141A22` |
| `--bg-hover`      | `#F1F3F7` | `#1C2530` |
| `--bg-header`     | `#FFFFFF` | `#141A22` |
| `--border-color`  | `#E4E7EC` | `#283442` |
| `--border-hover`  | `#CDD2DC` | `#3A4756` |
| `--text-main`     | `#1F2430` | `#E6EAF0` |
| `--text-secondary`| `#6B7280` | `#94A0B0` |
| `--text-hint`     | `#9AA1AE` | `#6E7A89` |
| `--text-on-primary` | `#FFFFFF` | `#0B0F14` |

Contrast (brief "AA+"): `--text-main` on `--bg-card` ≥ 12:1; white on `--brand-500 #4F46E5` ≥ 4.6:1 ✓. **Never cyan text on white** (fails AA) — cyan only as fill behind white/dark text, or as text on dark surfaces.

### 2.2 Volcán alternate (swap-in)
Warm-Mexican differentiation: `--brand-500:#E2553B` (clay-coral), deep ink `#221F1E`, `--accent-500:#0F9D7A` (agave jade), `--bg-app:#FBF7F4` (warm paper), semantics `#1E9E5A`/`#E08A00`/`#C73A2A`. Type/spacing/components unchanged — only the color map changes. Keep warmth in accents/identity; workspace stays warm-neutral paper.

### 2.3 Typography (actually add the fonts)
```
--font-display: "Space Grotesk", "Inter", system-ui, sans-serif;  /* headings, KPI numbers, wordmark */
--font-sans:    "Inter", system-ui, "Segoe UI", Roboto, sans-serif; /* body + tables */
--font-mono:    "JetBrains Mono", ui-monospace, monospace;          /* SKUs, order IDs, system traces */
```
Self-host all three via `@fontsource` (PWA must work offline; the current Google-CDN-only setup breaks that for fonts). Preload in `index.html`. Confirm `¿ ¡ ñ á é í ó ú` glyphs. Drop the implicit Roboto reliance (PM #3 success metric: "Roboto fully removed").

Scale (display in `--font-display`, body Inter; tight on data):

| Token | size / line / weight | use |
|---|---|---|
| `--t-display` | 36 / 40 / 700 | KPI hero number, login hero |
| `--t-h1` | 28 / 34 / 700 | page title |
| `--t-h2` | 22 / 28 / 600 | section header |
| `--t-h3` | 18 / 24 / 600 | card title |
| `--t-body` | 14 / 20 / 400 | default UI / table cell |
| `--t-sm` | 13 / 18 / 400 | helper, dense cell |
| `--t-xs` | 12 / 16 / 500 | chips, captions |
| `--t-overline` | 11 / 14 / 600, +0.06em, uppercase | eyebrow / table headers / nav group labels |

`font-variant-numeric: tabular-nums;` on every money/qty element — a brand trust requirement, not a nicety.

### 2.4 Spacing
Keep `--spacing-unit:8px`; add a scale: `--sp-1:4 --sp-2:8 --sp-3:12 --sp-4:16 --sp-5:20 --sp-6:24 --sp-8:32 --sp-10:40 --sp-12:48` (px). Dense table row padding `--sp-2`; comfortable forms `--sp-4`.

### 2.5 Radius
Reduce the current friendly `--border-radius:12px` toward a sharper bold-modern feel; add a scale: `--r-xs:4 --r-sm:6 --r-md:10 --r-lg:14 --r-pill:999`. Set `--border-radius: var(--r-md) /*10*/`. Buttons `--r-sm`, cards/inputs `--r-md`, chips/avatars `--r-pill`, **dialogs stay 16px** (matches the existing `.mdc-dialog__surface` rule). Tables: square inner cells, rounded outer container only.

### 2.6 Elevation (reuse existing `--shadow-*`, GPU-cheap — mid-range Android)
```
--shadow-sm: 0 1px 2px rgba(15,18,30,.06), 0 1px 1px rgba(15,18,30,.04);
--shadow-md: 0 2px 8px rgba(15,18,30,.08), 0 1px 2px rgba(15,18,30,.05);
--shadow-lg: 0 8px 24px rgba(15,18,30,.12);
```
Cockpit dark already uses `rgba(0,0,0,.3–.5)` for `--shadow-*` (keep) **plus a 1px `--border-color` ring** on cards (shadows read poorly on near-black). No heavy blur, no gradient orbs.

### 2.7 Motion / easing (new)
```
--ease-standard:  cubic-bezier(.2,0,0,1);
--ease-emphasized:cubic-bezier(.2,0,0,1.2);   /* slight overshoot = bold */
--dur-fast:120ms; --dur-base:200ms; --dur-slow:320ms;
```
Motion = feedback (sync ticking, AI "pensando…", state change, route slide), never decorative. Guard: `@media (prefers-reduced-motion: reduce) { → 0ms / opacity-only }`. The existing `card-style` mixin's `translateY(-2px)` hover is fine but should respect reduced-motion.

---

## 3. Angular Material M3 theme wiring (NEW layer to introduce)

There is no Material theme today. Add one so Material components inherit brand color/type/density instead of MDC defaults, then let it carry surfaces so the 970-line `.dark-theme` `!important` block can shrink.

Create `src/theme/_material.scss` (or add to top of `styles.scss`):
```scss
@use '@angular/material' as mat;

$fulcrum-primary:  ( /* M3 palette from the --brand-* ramp; 500 = #4F46E5 */ );
$fulcrum-tertiary: ( /* M3 palette from the --accent-* ramp; 500 = #06B6D4 */ );

html {
  @include mat.theme((
    color: ( primary: $fulcrum-primary, tertiary: $fulcrum-tertiary, theme-type: light ),
    typography: ( brand-family: 'Space Grotesk', plain-family: 'Inter' ),
    density: 0,
  ));
}
body.dark-theme {                      // reuse the EXISTING dark switch
  @include mat.theme((color: (theme-type: dark)));
}
```
Then a **bridge**: after `mat.theme`, declare the `--brand-*`/`--accent-*`/surface/spacing/radius/elevation/motion custom properties, and map Material system tokens onto ours where they overlap (`--mat-sys-primary → var(--brand-500)`, `--mat-sys-surface → var(--bg-card)`, `--mat-sys-on-surface → var(--text-main)`, etc.). Because every component already reads `--bg-card`/`--text-main`/`--primary-color`, re-pointing values flips the whole app; with Material now owning surface tokens, **delete redundant `.dark-theme` `!important` rules incrementally** and verify visually.

**Density:** global `0`; apply `mat.*-density(-2)` (to `-3` for the densest tables) scoped to the dense-table wrapper + toolbar controls. Brief asks `-3/-4`; start `-2/-3` to protect 48px mobile touch targets (the `touch-target` mixin already enforces 48px on ≤tablet).

### i18n / es-MX (must stay intact, one fix)
- **Flip `transloco-root.module.ts` `defaultLang` to `'es-MX'`** (Mexico-first; keep `en` available). Keep `LOCALE_ID`/`registerLocaleData('es-MX')` from `main.ts`.
- All redesigned components use `transloco` pipe / `*transloco` — zero new hardcoded strings (PM #1; i18n-lint sweep → 0).
- One **shared MXN currency pipe** defaulting to `'MXN':'symbol-narrow':'1.2-2':'es-MX'` (PM #2) — replaces the dashboard `currency:'USD'` bug (`dashboard.component.html` line 105) and the expense KPI hardcoded `'$'`; tabular-nums everywhere.
- Design every label/button/column for +20–25% length; `tú` voice.

---

## 4. Component language

**Buttons** — `filled` (primary, `--brand-500`/white, `--r-sm`, `--shadow-sm`), `tonal` (`--brand-50`/`--brand-700`), `outline` (`--border-hover`), `ghost/text`, `danger` (filled `--error-color`), `ai` (cyan-tinted + sparkle; for "Generar con IA", "Sugerir respuesta"). One filled primary per view. Heights 40 / 32 dense / **48 mobile-primary**. Press scale .98 `--dur-fast`. Labels 600.

**Cards** — extend the existing `card-style` mixin (it already does `--bg-card` + border + `--shadow-sm`, hover `--shadow-md`). **KPI card: re-point `kpi-card` away from gradient fill** to neutral surface + a giant `--t-display` tabular number in `--font-display` + overline label + optional delta chip (success/danger). (Gradient violates the brief's "no painted regions"; keep `--gradient-*` only for true marketing surfaces.)

**Tables (core of Fulcrum)** — sticky header (`--bg-hover` fill, `--t-overline` uppercase `--text-secondary` headers). Rows 40 dense / 48 comfortable, hairline `--border-color` bottoms, hover `--bg-hover`, selected row 3px left `--brand-500` bar. Right-align numerics; `--font-mono` for SKUs/order IDs/amounts. Status via `app-chip-*`. Row actions reveal on hover (desktop) / kebab (mobile). Sticky first column on h-scroll. Density toggle persisted via `settings.service`. Skeleton rows on load. Keep the normalized compact paginator + `sleek-scrollbar`.

**Forms** — Material outline, `--r-md`, visible labels, helper `--t-sm --text-secondary`, error `--error-color` + icon, **16px input on mobile**. Reuse `_forms.scss` (`form-row`, `form-section`, `search-field-compact`) and `sleek-select`. Group fields with `--t-overline` section labels. Validate on blur, summarize on submit.

**Chips / badges** — standardize on `app-chip-success/-warning/-error`; **add `app-chip-info` and `app-chip-ml`** (the only place `--ml-yellow` appears — a small "MercadoLibre" source tag). The `status-badge` mixins in `mixins.scss` already cover non-chip pills. Nav count badges use `--accent-500`.

**Empty / loading / error** (brief: no stock 3D blobs):
- *Empty*: centered `--t-h2` headline + one-line `tú` guidance + single primary CTA + a light line illustration from the **pivot-wedge motif** (the `change_history` triangle is the seed).
- *Loading*: layout-matching skeletons, brand-tinted shimmer, ≤200ms delay (the app already has a `loading.service` + `loading.interceptor` to hook).
- *Error*: `--error-color` icon, plain-Spanish message via the existing `translate-api-error`, "Reintentar", no stack traces. **Also remove the dev-only red `window.onerror` overlay in `main.ts` from production builds** (it dumps raw stacks — contradicts the polished error language).

**AI surface** — cyan accent + soft glow ring + sparkle; "pensando…" cyan shimmer. No AI key → inline **"Activar IA"** prompt linking to Settings → AI Agents (generalized `@if aiReady`; PM #6), reading `ai_config` from `settings.service.storeSettings$`.

---

## 5. Shell redesign (`core/header` + `core/sidenav`)

Restyle on the new tokens; **preserve the router-outlet, the `nav.*` Transloco keys, the `mat-expansion-panel` groups, and the user-footer controls**. IA change is the PM-mandated promotion + auto-expand only (PM #4).

**Desktop (≥1024px):** persistent **left rail**, collapsible 256 ↔ 72px icon-only. Top: pivot-wedge mark (evolve `change_history`) + "fulcrum" in `--font-display`. Groups `nav.menu`/`nav.management` with `--t-overline` labels. **Active item = `--brand-50` pill bg + `--brand-700` text + 3px left brand bar.** **Auto-expand the active group** — replace the hardcoded `purchasingExpanded=true / marketplacesExpanded=false` in `sidenav.ts` with route-derived `[expanded]` so the current section opens automatically. **Promote daily-money to ≤1 tap** (PM #4): surface **Stock Transfers**, **Buyer Questions** (relabel "Preguntas / Tiempo de respuesta"), **Expenses** as top-level entries (keep them inside their groups too, or add a "Diario" cluster). Rest of grouped IA stays buried. Footer keeps theme/language/sign-out.

**In-content top bar** (evolve `core/header`, currently just hamburger+logo): page title (`--t-h1`), breadcrumbs, **global search**, the single page primary action, an **ML-Full sync/connection status pill** (green/amber/red, fed by marketplace health), and notifications with an `--accent-500` count badge (home for over-SLA Q&A and inbound-transfer counts).

**Mobile / PWA (<768px):** top app bar (mark + search + avatar) + **bottom tab bar** of ≤5: **Dashboard, Pedidos, Productos, Transferencias, Preguntas** at 48px targets (`touch-target` mixin) with accent badges; "Más" sheet exposes the full grouped nav. Rail hidden. Route transitions slide `--ease-emphasized`. PWA: themed splash/status-bar `--brand-500` (light) / Cockpit `--bg-app` (dark) in `manifest.webmanifest`, maskable pivot-wedge icon, offline shell. GPU-cheap effects.

**Tablet (768–1023px):** rail collapsed icon-only, expandable. Breakpoints reuse `mixins.scss` (`$mobile-max:767 $tablet-min:768 $tablet-max:1023 $desktop-min:1024`); add `--bp-xl:1280`. Content max-width 1440px (raise the `_forms.scss` `page-container` 1200px cap on data pages), gutters `--sp-6`.

---

## 6. Page plans — scopeForFirstRedesign (PM §3, in order)

| Surface (route / file) | Visual + UX changes |
|---|---|
| **Foundations** (`theme/variables.scss`, new `theme/_material.scss`, `styles.scss`, `mixins.scss`) | Re-point all tokens to §2; add ramps, `--info`/`--ml-yellow`, fonts, spacing/radius/elevation/motion vars; introduce `mat.theme` (§3); re-point `kpi-card` off gradient; self-host fonts + remove Roboto; begin shrinking the `.dark-theme` `!important` block. |
| **es-MX + MXN** (PM #1/#2) | Flip Transloco `defaultLang` → `es-MX`; convert remaining English (`quick-post-dialog`, settings `ai-tab`, plus literals in `login`, `product-list`, `product-form`, `product-scanner`, `expense-dialog`, `po-ingest`); delete the English dev comment in `expense-dialog.html`; ship one shared MXN currency pipe (tabular-nums); fix dashboard `currency:'USD'` (line 105) + expense KPI `'$'`; `tú` voice. |
| **Shell / nav** (`core/header`, `core/sidenav`) | §5: rail + route-derived auto-expand (replace hardcoded `*Expanded`) + daily-money promotion + top-bar (search, page action, ML-sync pill, notifications) + mobile bottom tabs. New `nav.*` keys for promoted items. |
| **Dashboard** (`dashboard/pages/dashboard`) | **Maturity-gated** (PM #5): empty account → `onboarding-checklist` hero only, analytics suppressed (≤3 elements, Diego); populated → full cockpit — KPI hero row (display-font tabular MXN + delta chips) reusing the re-pointed `kpi-card`/`stat-card`, existing widgets, **plus two new cards**: "Preguntas sobre tiempo de respuesta" (over-SLA → `/reports/qa`) and "Transferencias por recibir" (→ reconciliation). Skeleton-first; one bold primary. |
| **Onboarding + AI activation** (`onboarding-checklist`, `product-form`, AI affordances) | Focused first-run: **nombre → precio → cantidad inicial → conectar ML** (PM #8 — add a starting-quantity field so the first product isn't 0). Add the AI-key step to the checklist; generalize **"Activar IA"** inline prompts (hide-not-disable, PM #6) off `settings.service.storeSettings$.ai_config`; AI surfaces use cyan/glow. |
| **Buyer Q&A** (`dashboard/pages/qa-page`, route `/reports/qa`) | Two-pane inbox desktop / single-column mobile; per-question **"tiempo de respuesta" countdown chip** (warning→error; rename SLA, PM #7); prominent **Responder** + AI **"Sugerir respuesta"** (cyan); in-app compose+post; ML-webhook **source chip** (`app-chip-ml`). Reconcile the nav-label(Marketplaces)/route(`/reports/qa`)/module(`dashboard/pages/qa-page`) mismatch. |
| **Stock-transfer push-to-ML** (`marketplaces/stock-transfers/*`) | Outcome naming **"Enviar inventario a MercadoLibre Full"** (PM #9). On the **push-qty-to-listings** result panel, render synced/failed/no-listing rows as chips; for expired-OAuth failures show a **one-tap "Reconectar" reauth chip** inline (mirror marketplace reconnect) so silent failures become re-authable. Dense transfer + reconciliation tables on new tokens. |

(Loop-2 — product-form deep cleanup #10, jargon pass #11, order/payments headline #12, inventory-count labels #13, then PO/marketing/payments/admin re-skins — inherit the system for free and are out of this scope. `/ingest` AuthGuard + duplicate `/marketplaces` route → engineering bug queue, not design.)

---

## 7. Implementation sequence (foundation-first)

1. **Tokens + fonts.** Re-point `theme/variables.scss` (`:root` light, `.dark-theme` Cockpit) to §2; add ramps, `--info`/`--ml-yellow`, `--font-display`/`--font-mono`, spacing/radius/elevation/motion vars; set `--border-radius:10px`. Self-host Inter + Space Grotesk + JetBrains Mono via `@fontsource`, preload in `index.html`, remove Roboto reliance.
2. **Material M3 theme (new).** Add `theme/_material.scss` with `$fulcrum-primary`/`$fulcrum-tertiary` palettes from the ramps; call `mat.theme()` on `html` + dark on `body.dark-theme`; bridge `--mat-sys-*` → our tokens. Then start deleting redundant `.dark-theme` `!important` overrides as Material covers surfaces.
3. **Global base + utilities.** Typography classes (`.t-h1`…`.t-overline`), extend `mixins.scss` (re-point `kpi-card` off gradient; add motion-aware hovers), `:focus-visible` ring (`2px --brand-500`), reduced-motion guard, tabular-nums utility. Build the shared MXN currency pipe (PM #2).
4. **es-MX completeness (PM #1).** Flip Transloco `defaultLang → es-MX`; convert the listed English offenders; delete the dev comment; `tú` voice; i18n-lint sweep → 0.
5. **Dark-mode wiring.** Verify the sidenav `toggleTheme()` path actually flips `body.dark-theme` through the new Material+token layer; update PWA `theme-color` dynamically; drop the dev `window.onerror` overlay from prod.
6. **Shell.** Restyle `core/header` + `core/sidenav` per §5 (rail, route-derived auto-expand, daily-money promotion, top-bar search/action/ML-sync pill/notifications, mobile bottom tabs); add `nav.*` keys.
7. **Shared primitives.** Button variants (+`ai`), KPI/stat card (neutral), status-chip set (+`info`,+`ml`), dense-table wrapper (sticky header, density toggle, skeleton), form-field defaults, empty/loading/error components, AI-surface + "Activar IA" prompt.
8. **Page passes (journey order).** Dashboard (maturity-gated, PM #5) → Onboarding + AI activation (PM #6/#8) → Buyer Q&A (PM #7) → Stock-transfer push-to-ML (PM #9). Each: apply tokens+primitives, add skeleton/empty/error, verify es-MX longest strings + mobile touch targets.
9. **Responsive + PWA polish.** Breakpoint audit, bottom-tab nav, maskable pivot-wedge icon + branded splash in `manifest.webmanifest`, offline shell, Lighthouse/perf budget on mid-range Android (PM #3 metric).
10. **A11y + i18n QA + visual baseline.** AA+ contrast (light, Cockpit dark, accent — no cyan-on-white text); keyboard nav + focus order; SR labels via Transloco; tabular-nums on numerics; +25% string-length stress; capture light/dark/mobile screenshots per page as the regression baseline.

**Why this order:** tokens → M3 theme → es-MX/MXN → shell → primitives all land before any page, so each page is composition on an inherited system. The existing custom-property contract means re-pointing values flips light/dark globally without touching components.

---

## 8. Verify-before-merge checklist
- **[DECIDE]** Brand direction: **Leverage Indigo** (recommended) vs **Volcán** (§2.2 swap). Pivot-wedge mark + cyan-pivot AI accent (brief §7).
- **[FIX]** Transloco `defaultLang` is `en` today → set `es-MX` (Mexico-first pillar).
- **[INTRODUCE]** There is no `mat.theme` in the repo yet — §3 is a *new* layer; confirm Material 20.2.7 M3 API (`mat.theme`) when adding it.
- **[CONFIRM]** Dark-mode toggle actually adds/removes `body.dark-theme` (path runs `sidenav.toggleTheme` → `settings.service` → ???); wire if missing.
- **[CONFIRM]** Daily-money promotion list + the 5 mobile bottom-tab destinations against current `nav.*` keys.
- **[KEEP]** Existing token names, `body.dark-theme`, `app-chip-*`, `card-style`/`kpi-card`/`status-*`/`touch-target` mixins, `sleek-select`, compact paginator, 16px dialog radius, `_forms.scss` helpers — extend, don't replace.
- **[REMOVE]** Dev `window.onerror` red stack overlay from production; stale `product-list.ts.new`.
