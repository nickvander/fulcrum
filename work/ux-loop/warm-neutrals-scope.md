# Warm Dark Neutrals — Scope & WCAG Audit

_Design-systems deliverable for the "Obsidian & Chile" dark theme. Date: 2026-05-31._
_Source of truth for current values: `frontend/src/theme/_tokens.scss` (`$obsidian` map). Emitter: `frontend/src/theme/variables.scss`._

## Why

`work/ux-loop/market-research.md` found Fulcrum's dark neutrals read **cool / blue-black** (hue ≈ 220–228°), which undercuts the locked **"Warm / grounded, Mexican"** pillar — the reds and gold are already warm, but they sit on cold grey, so the surfaces feel like generic dark-dev-tool SaaS rather than warm obsidian/clay. This round warms **only the greys**, with a subtle clay-amber cast, and proves no legibility regression.

## Approach

Rotate each neutral's hue from cool (~225°) toward **warm clay-amber (~12–37°)** while holding **relative luminance ≈ constant** (every change is within ±0.006 in linear luminance), so existing WCAG ratios are preserved or slightly improved. Saturation is kept **low** (HSL S ≤ ~12% on surfaces) so the result reads "warm obsidian," not brown/sepia. Mechanically: nudge **R up a few points, G roughly flat, B down** at these dark levels. Text inks get the same warm cast at much lower saturation so they don't tint visibly but harmonize with the warm surfaces.

`text-on-primary` stays `#FFFFFF`. Brand reds, affordance blue, AI gold, all semantics, `ml-yellow`, and `focus-ring` are **untouched**. The light `$warm-paper` map is **untouched** (already warm; no inconsistency found).

## Old → New hex (the only changes)

| Token (map key) | Old | New | Old hue° | New hue° | rel-lum Δ |
|---|---|---|---|---|---|
| `bg-app` | `#0E0F13` | `#11100F` | 228 | 30 | +0.0004 |
| `bg-card` | `#1A1C22` | `#201C1B` | 225 | 12 | +0.0005 |
| `bg-raised` | `#22252E` | `#292420` | 225 | 27 | −0.0002 |
| `bg-hover` | `#22252E` | `#292420` | 225 | 27 | −0.0002 |
| `bg-header` | `#141519` | `#171513` | 228 | 30 | +0.0001 |
| `text-main` | `#F5F4F2` | `#F6F3EF` | 40 | 34 | −0.0060 |
| `text-secondary` | `#A8ABB4` | `#B0ABA3` | 225 | 37 | +0.0025 |
| `text-hint` | `#8B909B` | `#94908A` | 221 | 36 | +0.0028 |
| `border-color` | `#2A2D36` | `#302B27` | 225 | 27 | −0.0013 |
| `border-hover` | `#3A3E49` | `#433D38` | 224 | 27 | −0.0001 |
| `text-on-primary` | `#FFFFFF` | `#FFFFFF` | — | — | 0 |

All luminance deltas are negligible (|Δ| ≤ 0.006 linear), so contrast ratios move by hundredths.

## WCAG 2.1 contrast matrix — text (binding floor 4.5:1 body)

Ratios computed from sRGB relative luminance, WCAG 2.1 §1.4.3.

| Pair | Old | New | Floor | Verdict |
|---|---|---|---|---|
| text-main on bg-app | 17.43 | **17.18** | 4.5 | PASS |
| text-main on bg-card | 15.49 | **15.27** | 4.5 | PASS |
| text-main on bg-raised | 13.92 | **13.88** | 4.5 | PASS |
| text-main on bg-header | 16.60 | **16.46** | 4.5 | PASS |
| text-main on bg-hover | 13.92 | **13.88** | 4.5 | PASS |
| text-secondary on bg-app | 8.34 | **8.33** | 4.5 | PASS |
| text-secondary on bg-card | 7.42 | **7.40** | 4.5 | PASS |
| text-secondary on bg-raised | 6.67 | **6.73** | 4.5 | PASS (↑) |
| text-secondary on bg-header | 7.95 | **7.98** | 4.5 | PASS (↑) |
| text-secondary on bg-hover | 6.67 | **6.73** | 4.5 | PASS (↑) |
| **text-hint on bg-app** | 5.98 | **5.99** | 4.5 | PASS (↑) |
| **text-hint on bg-card** | 5.32 | **5.32** | 4.5 | PASS |
| **text-hint on bg-raised** ◀ tightest | 4.78 | **4.84** | 4.5 | PASS (↑) |
| text-hint on bg-header | 5.70 | **5.74** | 4.5 | PASS (↑) |
| **text-hint on bg-hover** ◀ tightest | 4.78 | **4.84** | 4.5 | PASS (↑) |

No pair drops below 4.5:1. The two tightest pairs in the whole theme — `text-hint` on `bg-raised`/`bg-hover` — **improve** from 4.78 → 4.84, so no token needed a corrective nudge. The largest single drop anywhere is `text-main on bg-app` (17.43 → 17.18), comfortably above floor and imperceptible.

## Semantic colors on NEW surfaces (unchanged values; floor 3:1 chip/icon)

| Pair | Old | New | Floor | Verdict |
|---|---|---|---|---|
| success `#1FB872` on bg-card | 6.62 | 6.56 | 3.0 | PASS |
| success on bg-raised | 5.95 | 5.97 | 3.0 | PASS |
| warning `#F5A623` on bg-card | 8.40 | 8.33 | 3.0 | PASS |
| warning on bg-raised | 7.55 | 7.58 | 3.0 | PASS |
| error `#FF6B61` on bg-card | 6.10 | 6.05 | 3.0 | PASS |
| error on bg-raised | 5.49 | 5.50 | 3.0 | PASS |
| info `#6BA1FF` on bg-card | 6.62 | 6.57 | 3.0 | PASS |
| info on bg-raised | 5.95 | 5.97 | 3.0 | PASS |

All semantics clear 3:1 for chips/icons by a wide margin. They also all exceed **4.5:1**, so where any semantic color is used as **text** (e.g. error helper text, success ledger figures) it still passes body-text AA on the new surfaces.

## Borders / hairlines (non-essential; reference ~1.3:1)

| Pair | Old | New | Note |
|---|---|---|---|
| border-color on bg-app | 1.39 | 1.36 | Visible hairline — OK |
| border-color on bg-card | 1.24 | **1.21** | See note below |
| border-hover on bg-app | 1.79 | 1.78 | OK |
| border-hover on bg-card | 1.59 | 1.58 | OK |

**Note on `border-color` inside a card (1.21):** this was already sub-1.3 **today** (1.24) — it is a pre-existing, intentional inset divider (a hairline between rows *on* a card) that reads via the small luminance step plus the adjacent `bg-raised` surface, not via a hard contrast threshold. WCAG sets no minimum for purely decorative borders. The new value (1.21) is a 0.03 change, **not a regression introduced by warming**, and was deliberately *not* "fixed" by lightening `bg-card`: doing so would erode the tighter, binding `text-hint on bg-card` ratio (5.32), which matters far more. Card-outer borders against `bg-app` (1.36) remain clearly visible.

## Hue-shift sanity check (is the warmth real but subtle?)

| Surface | Old hex | Old hue | New hex | New hue | HSL sat |
|---|---|---|---|---|---|
| bg-app | `#0E0F13` | **228° (cool blue)** | `#11100F` | **30° (warm clay)** | 6.2% |
| bg-card | `#1A1C22` | **225° (cool blue)** | `#201C1B` | **12° (warm clay)** | 8.5% |

The hue rotates a full ~190–215° from the cool blue quadrant (220–230°) into the warm clay-amber quadrant (12–30°), confirming the shift is **directionally real**. Saturation stays ≤ 8.5% so it reads "warm obsidian," not brown. In a side-by-side the surfaces are perceptibly warmer; in isolation they still read as near-black neutral, which is the intent.

## Apply instructions (for the implementing engineer)

In `frontend/src/theme/_tokens.scss`, in the **`$obsidian` map only**, replace these ten key values with the New column above: `bg-app`, `bg-card`, `bg-raised`, `bg-hover`, `bg-header`, `text-main`, `text-secondary`, `text-hint`, `border-color`, `border-hover`. Leave `text-on-primary: #FFFFFF`. **Change nothing else** — not the brand reds (`primary*`), not affordance `accent*`/`info`, not AI `accent-2`, not `success`/`warning`/`error` or their `-bg` tints, not `ml-yellow`, not `focus-ring`, not `shadow-*`, and **do not touch the `$warm-paper` (light) map**. No edit to `variables.scss` is required: it emits every neutral mechanically via `#{map.get($c, <key>)}` (lines 46–58), so the new hexes flow straight through to the `--bg-*` / `--text-*` / `--border-*` custom properties. The derived `--bg-card-rgb` triplet (`color.channel(... bg-card ...)`, line 27) will recompute from the new `bg-card` automatically, so scanner-glow / `rgba(var(--bg-card-rgb), …)` tints warm in step — intended. After editing, run `check_theme_contrast.py` (it validates token discipline only — it will pass — and this document is the contrast safeguard it does not provide).

## Risk notes

- **Marginal pairs to watch (still PASS):** `text-hint on bg-raised` / `bg-hover` at **4.84:1** are the tightest in the theme. Any future surface that lightens `bg-raised`, or any hint text placed on an even-lighter ad-hoc surface, could cross the 4.5 floor. Treat 4.84 as the headroom budget; do not lighten `bg-raised` without re-running this matrix.
- **Borders read softer, not invisible:** intra-card dividers (`border-color` on `bg-card`, 1.21) are deliberately faint. If QA finds a divider that disappears on a specific dense table, prefer switching that divider to `border-hover` (1.58) rather than lightening `border-color` globally.
- **No light-theme change**, so light mode is unaffected by this round.
- **Screens to eyeball first (warm cast is most load-bearing on large flat fields):**
  1. Dashboard / home — large `bg-app` canvas; biggest warm payoff and easiest to spot a muddy result.
  2. Orders & inventory tables — many `bg-card` rows + faint dividers; verify hairlines still separate rows and hint/secondary text stays crisp.
  3. Inputs / raised surfaces & hover states (`bg-raised`/`bg-hover`) — the tightest hint contrast lives here.
  4. Header / sidenav (`bg-header`) — confirm chile-red and ML-yellow chips still pop against the warmer near-black.
  5. AI panel — confirm the `bg-card-rgb`-derived glow tints warmed pleasantly and gold/blue AI accents remain distinct.
