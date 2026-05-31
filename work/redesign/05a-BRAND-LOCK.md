# 05a — BRAND LOCK (AUTHORITATIVE): "Obsidian & Chile"

> **This file is the single source of truth for the brand and color palette.**
> The founder approved **"Obsidian & Chile"** (dark-first control room, ONE
> electric chile-red accent). The market brief (`03`) explores three options and
> recommends **"Leverage Indigo"** — **that recommendation is SUPERSEDED.**
>
> **Wherever any other artifact (`03`, `04`, `05`, `README`) says "Leverage
> Indigo", "Cockpit Dark", indigo `#4F46E5`, or cyan `#06B6D4` as the brand —
> IGNORE IT and substitute the Obsidian & Chile palette below.** Use chile-red
> `#FF4D2E`, NOT indigo. Read `05-design-system-and-plan.md` ONLY for its verified
> *code ground-truth* (existing token names, file locations, "no M3 theme exists
> yet", "Inter not actually loaded", "Transloco defaultLang is en", the sidenav
> `toggleTheme()` wiring, existing mixins) — but take all COLOR/identity decisions
> from THIS file.

Brand personality (in order): **Decisive, Sharp, Grounded, Warm, Modern.**
Dark-first. One disciplined accent. Near-neutral surfaces so data is the hero.
es-MX-first, tú-form. NOT generic-enterprise-blue; NOT a yellow-ML clone; no
fiesta kitsch.

---

## Color tokens (KEEP existing variable names; re-point to these values)

Brand accent shared across modes: **chile-red `#FF4D2E`** (dark) / **`#E5482E`**
(light, deeper for AA on warm paper). Affordance/interactive **blue is kept
separate** from brand red so red never competes with "clickable". The brand red is
**NOT** the semantic negative/loss red — negative is a distinct cooler red, always
icon-paired.

| Token (existing name kept) | Role | Dark (DEFAULT / product) | Light (warm paper) |
|---|---|---|---|
| `--primary-color` | Brand accent (chile-red) | `#FF4D2E` | `#E5482E` |
| `--primary-hover` *(new)* | Brand hover | `#FF6347` | `#CC3D24` |
| `--accent-color` | Interactive/affordance (cool) | `#4C8DFF` | `#0B5FFF` |
| `--accent-light` | Selected text / links-on-dark | `#7FB0FF` | `#2F6BFF` |
| `--accent-2` *(new — AI/insight gold, sparingly)* | AI/insight highlight only | `#FFC23D` | `#C8860A` |
| `--bg-app` | App canvas | `#0E0F13` | `#F7F4EE` |
| `--bg-card` | Card / surface | `#1A1C22` | `#FFFFFF` |
| `--bg-raised` *(new)* | Menus, dialogs, popovers | `#22252E` | `#FFFFFF` |
| `--bg-hover` | Hover / sunken / chip rest | `#22252E` | `#EFEAE0` |
| `--bg-header` *(existing)* | Toolbar/header surface | `#141519` | `#FFFFFF` |
| `--text-main` | Primary ink | `#F5F4F2` | `#16140F` |
| `--text-secondary` | Secondary ink | `#A8ABB4` | `#5C574C` |
| `--text-hint` | Placeholders / tertiary | `#6E727C` | `#8C8678` |
| `--text-on-primary` *(existing)* | Ink on chile-red | `#FFFFFF` | `#FFFFFF` |
| `--border-color` | Hairlines, table rows | `#2A2D36` | `#E6E1D7` |
| `--border-hover` | Input outline / hover | `#3A3E49` | `#D6CFC0` |
| `--success-color` / `--success-bg` | Positive (paid, in-stock) | `#1FB872` / `rgba(31,184,114,.14)` | `#137A4D` / `#E4F2EA` |
| `--warning-color` / `--warning-bg` | Warning (low stock, SLA at-risk) | `#F5A623` / `rgba(245,166,35,.14)` | `#C8860A` / `#FBF1DF` |
| `--error-color` / `--error-bg` | Negative/loss (distinct from brand red) | `#F0473E` / `rgba(240,71,62,.14)` | `#C0392B` / `#FBE7E5` |
| `--info-color` / `--info-bg` *(existing/new)* | Info | `#4C8DFF` / `rgba(76,141,255,.14)` | `#0B5FFF` / `#E7EEFD` |
| `--focus-ring` *(new)* | Focus outline | `#FF4D2E` | `#E5482E` |
| `--primary-light` / `--primary-dark` *(existing)* | brand tints | `#FF6347` / `#C9351D` | `#FF6347` / `#B8331C` |

Status fills always pair `*-bg` + `*-color`. Keep the existing `app-chip-*`
classes and the `app-chip-color` mixin; re-point their values to the table above.

**ML-yellow `#FFE600`** may appear ONLY as a tiny "came from MercadoLibre" source
chip — never as brand chrome.

---

## Type

- **Body / UI / tables:** `'Inter'` (must be *actually loaded* — it is referenced
  but NOT loaded today; self-host via @font-face). Stack
  `'Inter', system-ui, 'Segoe UI', Roboto, sans-serif`. Full es-MX glyphs
  (`ñ á é í ó ú ü ¿ ¡`).
- **Display / brand / hero:** `'Space Grotesk'` (page titles, hero KPI numbers,
  login/onboarding).
- **Numbers are a brand asset:** every money/fee/stock/% cell sets
  `font-variant-numeric: tabular-lining; font-feature-settings:"tnum" 1;` and is
  **right-aligned**. Money always via the single MXN formatter → `$1,234.50 MXN`.
- Optional mono (`JetBrains Mono`/`Geist Mono`) for SKUs/IDs/AI traces.

Type scale tokens to add: `--font-display-lg 40/44 700`, `--font-display 32/38
700`, `--font-h1 24/30 600`, `--font-h2 20/28 600`, `--font-h3 16/24 600`,
`--font-body 14/20 400`, `--font-body-strong 14/20 600`, `--font-caption 12.5/16
500`, `--font-overline 11/14 600 uppercase +0.06em`. Swap Material's type *family*
to Inter (plain) + Space Grotesk (display/headline) via the M3 typography config.

## Spacing / radius / elevation / motion

- Spacing 4px base: `--space-1:4 … --space-16:64`. (Existing `--spacing-unit:8px`
  and `--card-padding:24px` stay.)
- Radius: existing `--border-radius` is **12px** — keep it as the card radius
  (`--radius-md`). Add `--radius-xs:4`, `--radius-sm:8`, `--radius-lg:16` (dialogs,
  matches existing 16px rule), `--radius-pill:999`.
- Elevation: keep `--shadow-sm/-md/-lg`; dark mode leans on raised surface +
  `1px solid var(--border-color)` hairline ring over heavy shadow. One layer only.
- Motion: `--ease-standard cubic-bezier(.2,0,0,1)`, `--ease-emphasized
  cubic-bezier(.2,0,0,1.1)`, `--dur-fast 120ms / --dur-base 180ms / --dur-slow
  260ms`. Global `@media (prefers-reduced-motion: reduce)` → 0ms/opacity-only.
  Never animate the data/numbers.

---

## Dark-by-default (required for the dark-first brand)

Dark must be the DEFAULT for a brand-new user with no saved `fulcrum_settings`.
Set the SettingsService default theme to `'dark'` and ensure `app.component`
applies `body.dark-theme` when no setting exists. Keep the existing sidenav-footer
`toggleTheme()` + EN/ES-MX switch wiring intact — change values/presentation, not
the mechanism. Also flip Transloco `defaultLang` `'en' → 'es-MX'`.

## Brand motif

A minimal geometric **pivot/lever wedge** (triangle balancing a bar; doubles as an
upward chevron = momentum). The header already uses a `change_history` triangle —
evolve it into the wedge. Reuse the wedge as: the active-nav 3px left indicator,
the AI-insight marker, empty-state glyph, and the maskable PWA icon. One-color +
reversed-on-dark variants. Avoid scales/seesaws/barbells.

## Component & shell direction

Follow `05-design-system-and-plan.md` §2/§3/§4 for component language, shell IA,
and page plans — but apply THIS palette. Highlights: filled primary buttons in
chile-red; metric/hero cards with a 3px chile-red top border (re-point the
gradient `kpi-card` mixin to neutral surface + big tabular number); dense tables
with sticky headers, pinned SKU column, tabular right-aligned money, status chips
(never bare color), compact-density toggle; skeleton loading; first-class
empty/error states with the wedge + one es-MX CTA. Shell: flatten the sidenav
expanders, promote daily money actions (Enviar a ML Full / Preguntas / Gastos) to
single-tap, mobile bottom-tab bar, label = route = component.
