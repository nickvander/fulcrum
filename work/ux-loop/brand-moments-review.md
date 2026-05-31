# Brand Signature Moments — Acceptance Review

_Brand/design critic, final gate before commit. Date: 2026-05-31._
_Scope reviewed: Moment B (AI=gold), C (honest-MXN-number), E (peer-voice empty states). D (wedge motion) correctly deferred — no app-wide sync/success event exists to hook it to._

## VERDICT: ⚠️ Ship after small fixes

The three moments are tasteful, restrained, on-brand, and genuinely make the app feel more ownable — this is real signature work, not cosmetic noise. Guards pass (`check_theme_contrast` 117 SCSS clean; `check_i18n_consistency` no missing keys), `tsc --noEmit` clean, and the new specs assert the load-bearing rules ("never chile-red on money"; all four wedge/tone paths). Two should-fix items below before commit; the rest are P2 follow-ups.

---

## 1. Restraint / taste — PASS

- **Gold is icon/hairline/tint only, never a flood.** `styles.scss:655-710`: `.ai-accent` tints the glyph; `.ai-accent--region` is a 2px left hairline + a 6%→0% wash; `.ai-accent__chip` is a 14%-alpha tint with text on `--text-main` (NOT gold text on a light tint — the exact AA trap the lock warned about, correctly avoided). `ai-prompt-preview.scss:68-75` inverts the old white-on-blue token badge to the tinted-chip pattern.
- **Red is OFF AI surfaces and OFF money.** No `--primary`/`--accent` on any AI scss; the honest-number partial (`_honest-number.scss:40-42`) routes tone to `--success-color`/`--error-color`/`--text-main` only. Directive spec explicitly asserts `not.toMatch(/primary|result-won/)` on the money node (`honest-number.directive.spec.ts:47,56`).
- **Honest-number is hero-only, not carpet-bombed.** Applied to the profit hero (`profit-summary-widget.component.html:46`) and only 2 of 4 dashboard KPI cards — the two *money* values opt in via `[honest]="true"` (`dashboard.component.html:137,141`); the % health card stays plain. `metric-card` defaults `honest=false`, `tone='neutral'` (`metric-card.component.ts:124-127`). Tables untouched. Textbook restraint.
- **Peer empty states are warm, not cheesy, plain es-MX `tú`.** `es-MX.json:503/708/1153`: "contéstala aquí en un toque —responder rápido te gana la venta", "Por ahora no tienes que hacer nada", "Tú puedes con esto". Idiomatic Mexican, reassuring-competent, zero kitsch, zero English leakage. Parity in `en.json`.

## 2. On-brand & ownable — PASS (with one consistency gap)

- **Collectively a recognizable signature, not noise.** Three accents, one job each (red=action, blue=affordance, gold=AI) + a confident money number + a peer voice carrying the brand wedge into first-run. This is the differentiation the research demanded (Konfío peer-voice lesson; "money is the product").
- **Strongest moment: C (honest number).** Cleanest, most defensible, best-tested; a no-visual-change refactor of a loved treatment into one reusable source of truth (`_honest-number.scss` + directive), with size driven by `--honest-number-size` so the profit hero (2.75rem) and KPI (32px) share one type spec.
- **Weakest moment: B (AI=gold) — under-propagated.** The gold treatment is correct where applied, but only ~3 of ~13 AI touchpoints are routed through `.ai-accent`. `auto_awesome`/`psychology` icons in `marketplace-listing-dialog`, `po-ingest-dialog`, `purchase-order-edit`, `quick-product-dialog`, `product-form`, `catalog-import-dialog`, `expense-dialog`, `product-scanner`, `settings` are still default-colored. The "AI consistently glows gold" identity is only partially delivered this round. Two of the three gold components (`ai-search-bar`, `ai-prompt-preview`) are not even rendered on a live page; the one live, shipping gold AI surface is the **quick-post-dialog** panel-header icon (`quick-post-dialog.component.html:41`, opened from campaign-list).
- **Inconsistency:** quick-post-dialog's "Generar" button (`quick-post-dialog.component.html:102-105`) is `mat-flat-button color="accent"` (affordance blue) with an `auto_awesome` icon — an AI action still reading blue. Defensible as an *action* button, but it sits two lines under the gold AI header, so the AI/action color story is muddled there. P2.

## 3. Accessibility — PASS in dark; latent light-mode landmine (preventive fix)

Recomputed (WCAG relative luminance):

| Surface | Gold token | Ratio | 3:1 non-text floor |
|---|---|---|---|
| dark `bg-card #1A1C22` | `#FFC23D` | **10.57:1** | pass (huge headroom) |
| dark `bg-raised #22252E` | `#FFC23D` | **9.5:1** | pass |
| dark `bg-app #0E0F13` | `#FFC23D` | **11.89:1** | pass |
| light `bg-raised/bg-card #FFFFFF` | `#C8860A` | **3.06:1** | pass (thin) |
| light `bg-app #F7F4EE` (cream) | `#C8860A` | **2.78:1** | **FAIL** |

**The engineer's flag is accurate, but it does NOT ship as a live defect today.** Every live gold AI icon sits on a *white* surface: quick-post panel-header is `background: var(--bg-raised)` = `#FFFFFF` (3.06:1, passes); ai-prompt-preview header/section sit on `--bg-raised` = white. The 2.78:1 case is the `ai-search-bar` prefix on cream — and `app-ai-search-bar` is **not rendered in any template** (only referenced in a product-list spec). So the AA story holds on every real surface. **But it's a latent landmine:** the search bar's intended home is a page toolbar over `bg-app`, and `.ai-accent` is a global utility anyone can drop onto a cream surface. Fix it before it bites (S1 below). **Reduced-motion: honored** — `.ai-accent--thinking` has a `@media (prefers-reduced-motion: reduce)` branch killing the sweep for a static 10%-alpha wash (`styles.scss:700-704`), mirroring the existing `mixins.scss` pattern.

## 4. Did anything regress the feel? — NO

No over-animation: the only new motion is the AI shimmer (reduced-motion-gated) and it's gated to the "thinking" state, not idle. Numbers are never animated (lock honored). Spacing is consistent — `empty-state--peer` adds deliberate breathing room (56px) and a 44ch column sized for +25% Spanish (`empty-state.component.scss:64-76`). Profit-summary refactor is no-visual-change (size preserved via CSS var, `profit-summary-widget.component.scss:89-92`).

---

## Should-fix before commit (2)

- **S1 (a11y, latent):** Darken the light-mode AI-gold token OR scope `.ai-accent` away from cream. Minimal: bump light `accent-2 #C8860A` to ~`#B5790A`/`#A86E00` (≥3:1 on `#F7F4EE`) in `_tokens.scss:82` — keeps the utility safe on ANY surface and costs nothing visually. (Alternative: only render the gold AI icon on `bg-card`/`bg-raised`/outlined-field surfaces — more fragile.) Prevents the search-bar prefix failing the instant it's placed on a toolbar.
- **S2 (dead code):** Remove the now-orphaned `--accent-color: var(--accent-color);` self-alias at `ai-prompt-preview.scss:10` — the icon/header/badge were all repointed to `--accent-2`, so this line is dead and misleading.

## Nice-to-have follow-ups (P2)

- **P2-a:** Propagate `.ai-accent` to the remaining ~10 AI affordances (`marketplace-listing-dialog`, `po-ingest`, `purchase-order-edit`, `quick-product-dialog`, `product-form`, `catalog-import`, `expense-dialog`, `product-scanner`, `settings`) so "AI = gold" is actually app-wide. The capability exists; this is mechanical adoption, gated incrementally like Moment E.
- **P2-b:** quick-post "Generar" button (`quick-post-dialog.component.html:102`) — decide whether the AI generate action carries the gold icon or stays a blue action button; currently mixed next to the gold AI header.
- **P2-c:** `.token-badge` styling is duplicated (component `ai-prompt-preview.scss:68-75` + global `.ai-accent__chip`); collapse to the global class only to keep one source of truth.

**Bottom line: ship after S1 + S2 (both one-liners). The work is tasteful and on-brand; the only true defect is latent, and the gold signal just needs to spread to the rest of the AI surfaces in a later pass.**
