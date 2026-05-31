# Fulcrum — Brand Signature Moments (SCOPE, not implementation)

_Design/brand lead deliverable for the "Obsidian & Chile" UX loop. Date: 2026-05-31._

**Mandate:** A tasteful, BOUNDED set of "signature brand moments" that make Fulcrum
feel beautiful, modern, and ownable — without touching the locked brand, regressing
a11y/perf, or breaking the i18n/contrast guards. This doc picks **3 moments + 1
deferred**, gives the exact tokens/files, the risk, and the de-risk. It is a scope,
not a patch.

**Authoritative inputs:** `work/redesign/05a-BRAND-LOCK.md` (brand lock),
`work/ux-loop/market-research.md` (researcher recs, critiqued below), and the
verified code ground-truth in `frontend/src/theme/` + the components cited inline.

---

## 0. What's ALREADY done (don't re-do it)

Verified in-repo so we scope the *gap*, not the whole brief:

- **Tokens are already AA-hardened.** `frontend/src/theme/_tokens.scss` shows
  `text-hint`, `error-color` (`#FF6B61`), `info-color` (`#6BA1FF`), and light
  `warning-color` (`#8A5E00`) were already nudged to pass AA, with the math in
  comments. The four reds/colors are already distinct: `--primary-color #FF4D2E`
  (brand), `--accent-color #4C8DFF` (affordance), `--accent-2 #FFC23D` (AI gold),
  `--error-color #FF6B61` (loss). **Do not touch these.**
- **The "big honest number" already exists — but only in ONE widget.**
  `frontend/src/app/dashboard/widgets/profit-summary-widget/...scss` has a
  `.hero-number` (2.75rem, `tabular-nums`, display face, loss=`--error-color` never
  chile-red). It is **not generalized** into a reusable primitive. → Moment C.
- **The pivot-wedge mark already exists** as a `clip-path` polygon:
  `header.scss` `.logo-mark` (`clip-path: polygon(0 0,100% 50%,0 100%,28% 50%)`)
  and the same in `sidenav.scss`. It is **static** today. → Moment D (deferred).
- **AI surfaces currently read BLUE, not gold.** `ai-prompt-preview.scss` uses
  `var(--accent-color)` (blue) for `.ai-icon`, `.token-badge`, section headers;
  `ai-search-bar.html` uses a plain `search_spark` icon with no accent. Only
  `analytics-reports-widget.scss` uses `--accent-2`, for a single refunds icon.
  → Moment B — the cleanest identity win.
- **Shared `empty-state`** (`empty-state.component.{ts,html,scss}`) takes
  `icon/title/description` + projected content. Generic. → Moment E (folded in).

---

## 1. Critique of the researcher's recommendations (keep / cut)

| Researcher rec | Verdict | Why |
|---|---|---|
| Warm the neutrals (a) | **DEFER (cut from this round)** | Highest *feel* leverage but highest *blast radius* — every surface, every screen, both themes, and the dark hexes proposed (`#100F0E…`) drop chroma without a luminance audit across all `text-on-surface` pairs. Not worth the regression risk in a "signature moments" round. See §3. |
| AI = gold (b) | **KEEP — top pick** | Low risk, high identity payoff, fixes a real inconsistency (AI reads blue today). Moment B. |
| "Honest MXN number" primitive (c) | **KEEP** | The treatment already exists and is loved; extracting it is mechanical and defines the money signature. Moment C. |
| Pivot-wedge sync/success motion (d) | **DEFER to a thin slice** | Genuinely ownable but easy to make gimmicky/janky. Scope only a *reduced-motion-safe sync pulse on the existing mark*, and only if Moments B/C land clean. Moment D. |
| Peer-voice empty states (e) | **KEEP, folded into B's round** | Cheap, warm, on-pillar ("Warm" is the weakest-executed pillar). Moment E. |
| Animate success "tilt up" + numbers | **CUT** | Lock says *never animate the data/numbers*. A separate success animation is gold-plating; the sync pulse (D) covers the motif. |
| Re-palette / new lead color / loss-red move | **CUT** | Brand locked; reds already distinct & AA-passing. Out of scope. |
| Glassmorphism / gradient-orb AI surface | **CUT** | Brief + researcher both flag it as 2024 cliché and a mid-range-Android perf hit. |

---

## 2. THE CHOSEN MOMENTS (3 + 1 deferred)

### Moment B — "The AI glows gold" (PRIMARY)
**What:** Route every AI affordance to `--accent-2` (`#FFC23D` dark / `#C8860A`
light) as a *restrained* signal — icon tint + a thin left-border / hairline on AI
output regions, plus a gold shimmer on the "pensando…" state. **Never a gold flood,
never a gold fill behind text.** Action stays chile-red; affordance stays blue; AI
becomes gold. Three accents, one job each.

**Why ownable:** No competitor has a consistent "the AI is working" color. It also
pulls red *off* the AI surface, killing the "energy-drink" risk the researcher flags.

**Exact change (tokens already exist — only component SCSS/HTML):**
- `ai-prompt-preview.scss` — repoint `.ai-icon`, `.section-header`, and the
  `.token-badge` from `var(--accent-color)` → `var(--accent-2)`. The badge currently
  has `color:white` on a blue fill; **invert it** to gold *text/hairline on a tinted
  chip* (`background: rgba(255,194,61,.14); color: var(--accent-2)`) — do NOT put
  white or dark text directly on a `#FFC23D` fill at small sizes (fails AA, see §3).
- `ai-search-bar.{html,scss}` — tint the `search_spark` prefix icon
  `var(--accent-2)`; add a 1px gold focus hairline on `.search-field` focus only.
- `quick-post-dialog` (marketing) + any "Activar IA" affordance — same gold icon
  treatment. Grep `search_spark|auto_awesome|aiPromptPreview|aiSearchBar` to find
  call sites; route them all through one shared `.ai-accent` utility class rather
  than per-component hexes (keeps it `var(--*)`-only and one-stop to tune).
- AI "thinking" shimmer: a gold-tinted skeleton shimmer keyframe, **gated behind
  `prefers-reduced-motion` via the existing mixin pattern in `mixins.scss`**
  (reduce → opacity-only / static gold dot, no sweep).

**Risk:** Gold misused as a text/fill background fails contrast; gold creep dilutes
the "rare = premium" rule.
**De-risk:** Gold is icon/hairline/shimmer ONLY — never a fill behind text. One
shared `.ai-accent` class so it can't drift. Contrast pairs recomputed in §3.

---

### Moment C — The "honest MXN number" primitive (`appHonestNumber`)
**What:** Extract the profit-summary `.hero-number` treatment into a reusable
**attribute directive** `appHonestNumber` (or a tiny `<app-honest-number>` if a
unit slot is cleaner): Space Grotesk display face, `font-variant-numeric:
tabular-nums lining-nums`, `font-feature-settings:"tnum" 1`, oversized, with the
`MX$` / `MXN` unit rendered small + `--text-secondary`. Tone is **semantic** (profit
`--success-color`, loss `--error-color`) — **never chile-red on money** (lock rule).
Apply it to the single top dashboard KPI and the profit hero; leave dense table
cells as-is (they already set tabular-nums).

**Why ownable:** Money is the product. A confident, consistent big number is more
trust-building and more recognizable than any logo flourish, and directly answers
the "is this real?" anxiety. It makes the money typography a *brand asset*, not a
per-widget accident.

**Exact change:**
- New: `frontend/src/app/shared/directives/honest-number.directive.ts` (standalone)
  + a `_honest-number.scss` partial holding the type rules (so the existing
  `.hero-number` block and any new call site share ONE source of truth).
- Refactor `profit-summary-widget` to consume the directive (no visual change — it
  is the reference implementation; snapshot/spec must stay green).
- Apply to the top dashboard KPI card (the `kpi-card` mixin already does the
  display-face/tabular treatment; the directive standardizes the unit + tone).
- Money string still flows through the **single existing MXN formatter** (`$1,234.50
  MXN`); the directive only styles, it does not reformat — no logic duplication.

**Risk:** Over-application (every number gets huge) or duplicating the MXN format.
**De-risk:** Directive is presentation-only and opt-in; apply to hero KPI(s) only,
not tables; formatting stays in the one formatter. profit-summary is the golden test.

---

### Moment E — Peer-voice empty states (warm, es-MX, tú)
**What:** Add an optional `tone="peer"` presentation to the shared `empty-state`
component: warm es-MX peer-voice copy + the wedge glyph (reuse the `clip-path`
polygon from `header.scss`, not a new asset) as the icon when no Material icon is
passed. Delivers the under-executed "Warm" pillar where it actually lands — in the
voice and the first-run feel.

**Why ownable:** Konfío's lesson — LatAm SMB trust is won by sounding like a *peer*,
not a bank. "Aún no tienes preguntas — cuando lleguen, respóndelas aquí en un toque"
beats "No data."

**Exact change:**
- `empty-state.component.ts` — add `@Input() tone: 'neutral'|'peer' = 'neutral'`
  and an optional `useWedge` flag (renders the wedge glyph span vs. `<mat-icon>`).
- `empty-state.component.scss` — wedge glyph via the existing clip-path; warmer max-
  width / spacing for the peer tone. `var(--*)` only.
- i18n: peer-voice copy lives in the **calling feature's** key namespace (orders,
  products, expenses, marketing) — `en.json` + `es-MX.json` **both**, layouts sized
  for +20–25% Spanish length. es-MX is `tú`, reassuring-competent, no kitsch.

**Risk:** Scope creep across many feature screens; i18n parity drift.
**De-risk:** Ship the *capability* + convert 2–3 highest-traffic empties (Q&A,
orders, expenses) this round; the rest adopt incrementally. `check_i18n_consistency.py`
gates parity.

---

### Moment D — Pivot-wedge sync pulse (DEFERRED — thin slice only, ship last)
**What:** On a real sync/success event (ML Full push completes, payment reconciled),
the **existing** header/rail wedge does ONE subtle "settle" — a 1-step
tilt-and-rebalance via `transform: rotate()` settling to 0, 180–260ms, `--ease-
emphasized`. Not a loop, not a spinner.

**Why ownable:** "Leverage finding equilibrium" — literally the name. No competitor
has an animated motif.

**Why deferred:** Pure delight; easy to make janky/gimmicky; depends on a real
event hook. Only build if B+C land clean and time remains.

**Exact change (if built):**
- A `.wedge--settle` state class on the existing `.logo-mark`, triggered by a sync-
  success signal. **GPU-cheap `transform` only** (no layout/paint thrash on mid-
  range Android). **`prefers-reduced-motion: reduce` → no rotation; opacity-only
  acknowledgment**, reusing the reduced-motion pattern already in `mixins.scss`.
**Risk:** jank/perceived-perf hit; motion-sickness.
**De-risk:** one-shot transform, ≤260ms, reduced-motion fallback mandatory, fires
only on explicit success (never on every render).

---

## 3. Why (a) "warm the neutrals" is DEFERRED — the rigor it would need

It is the single biggest *feel* lever AND the biggest risk: it repaints every
surface in both themes. The researcher's proposed darks (`bg-app #100F0E`,
`bg-card #1B1A1E`, `bg-raised #24221F`, `border #2C2A2B`) keep luminance roughly flat
but shift chroma warm. Before it could ship, an engineer must recompute AA for EVERY
`text-on-surface` pair on the new `bg-card`:
- `text-main #F5F4F2` on new `bg-card #1B1A1E` — L_text≈0.918, L_bg≈0.0102 →
  (0.918+0.05)/(0.0102+0.05) ≈ **16.1:1** (passes, fine).
- `text-secondary #A8ABB4` on `#1B1A1E` → ≈ **7.0:1** (passes).
- `text-hint #8B909B` on `#1B1A1E` → ≈ **4.9:1** (passes AA for normal text) — but
  this is the *tight* one and must be re-verified on `bg-raised #24221F` and
  `bg-hover` too, since hint sits at the AA floor today.
The numbers likely pass, but "likely" isn't the bar for a global repaint. **Defer to
its own dedicated round** with a full pair matrix + side-by-side screenshots + the
`check_theme_contrast.py` run, not bundled into signature moments. Shipping B/C/E
first delivers most of the *perceived* warmth (gold AI, peer voice) at a fraction of
the risk.

**Gold (`--accent-2`) contrast sanity for Moment B (icons/non-text graphics, AA
non-text floor 3:1):**
- `#FFC23D` relative luminance ≈ **0.586**. On `bg-card #1A1C22` (L≈0.0126):
  (0.586+0.05)/(0.0126+0.05) ≈ **10.1:1** — passes for icon/large/hairline easily.
- On `bg-raised #22252E` (L≈0.0205): ≈ **8.9:1** — passes.
- **Gold as small text fill (e.g. dark text on a `#FFC23D` chip):** `#16140F` on
  `#FFC23D` ≈ 11:1 (would pass) BUT white/light text on gold fails — so the rule
  stands: **gold = icon/hairline/tinted-chip-text, never a flood with light text.**
- Light mode: `--accent-2` is already `#C8860A` (the darker AA-safe gold); use it
  the same way (icon/hairline), never as small text on white.

---

## 4. Explicitly OUT OF SCOPE / rejected (anti-creep)

- **Any re-palette, new lead color, or moving the loss-red** — brand locked; reds
  already distinct + AA-passing.
- **Warming the global neutrals (a)** this round — deferred to its own audited round (§3).
- **Animating numbers / a bespoke "tilt-up" success animation** — lock forbids
  animating data; the sync pulse (D) is the only motion, and it's deferred.
- **Glassmorphism / frosted panels / gradient-orb AI surface** — cliché + perf hit.
- **New display typeface (Geist/Mona Sans)** — low payoff, brand-adjacent risk; keep
  Space Grotesk, earn distinctiveness via numerals (C) + wedge (D).
- **Gold fills, gold text-on-light, gold beyond AI** — violates the "rare/one-job"
  discipline.
- **Hardcoded hexes anywhere** — `var(--*)` tokens only (guard-enforced).

---

## 5. Acceptance criteria (the bar the engineer must hit)

1. **`var(--*)` tokens only** — zero new hardcoded colors; `check_theme_contrast.py`
   passes (pre-commit/pre-push/CI). No new undefined tokens.
2. **AA preserved & spot-checked.** Gold (`--accent-2`) used only as
   icon/hairline/tinted-chip-text (≥3:1 non-text, ≥4.5:1 if it ever carries text);
   no light text on a gold fill. The §3 ratios hold; recompute any pair you newly create.
3. **Reduced-motion respected.** Every new animation (gold shimmer; deferred wedge
   pulse) has a `prefers-reduced-motion: reduce` branch → opacity-only / static,
   reusing the `mixins.scss` pattern. No motion that hurts perceived speed.
4. **i18n parity.** Every new string in BOTH `en.json` + `es-MX.json`; es-MX is `tú`,
   peer-voice, no kitsch; layouts absorb +20–25% length. `check_i18n_consistency.py` green.
5. **Both themes verified** — dark (default) AND warm-paper light, screenshot each
   touched surface.
6. **No guard/test regression; full suite green.** Baseline **133 files / 817 tests**
   stays green; profit-summary spec/snapshot unchanged (Moment C is a no-visual-
   change refactor); new directive + empty-state `tone` get unit tests using
   `getTranslocoTestingModule()` where they render strings.
7. **Bounded.** Only B, C, E this round; D only if B+C+E land clean with time left.
   No surface gets a gold flood; the honest-number directive touches hero KPI(s) only.

---

## 6. Verification checklist (eyeball + recompute)

**Screens/states to eyeball in DARK *and* LIGHT:**
- AI search bar (`ai-search-bar`): rest + focus — gold prefix icon + focus hairline,
  no blue left on AI.
- AI prompt preview (`ai-prompt-preview`): collapsed + expanded — gold icon, gold
  section headers, **inverted gold-on-tint token badge** (verify legible, not a flood).
- "pensando…"/AI thinking state — gold shimmer animates; with reduced-motion ON it's
  static (no sweep).
- Dashboard top KPI + profit-summary hero — `appHonestNumber`: display face, tabular,
  `MXN` unit muted, profit=green / loss=`--error-color` (confirm **no chile-red on a
  money number**).
- Empty states (Q&A, orders, expenses) — peer-voice es-MX copy, wedge glyph, no
  English leakage, no overflow at +25% length.
- (If D) header/rail wedge on a real ML-Full sync success — one settle, then still;
  reduced-motion → no rotation.

**Contrast pairs to recompute (give the ratio in the PR):**
- `#FFC23D` on `--bg-card #1A1C22` and `--bg-raised #22252E` (≥3:1 non-text) — §3 ≈10:1/8.9:1.
- Gold token-badge: chosen text color on its tinted background (≥4.5:1 if it carries text).
- Light-mode `--accent-2 #C8860A` on `#FFFFFF` card (icon ≥3:1) and any text use ≥4.5:1.
- Any honest-number tone on its surface: `--success-color`/`--error-color` on
  `--bg-card` (≥4.5:1 — these already pass, confirm unchanged).
