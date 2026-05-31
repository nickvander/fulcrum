# Fulcrum — PM Critique & Loop Decision (UX Loop)

_Owner: Product. Inputs: `user-novice.md` (Diego), `user-power.md` (Sofía), `market-research.md` (brand), prior `redesign/04-pm-decision.md` + `redesign/06-build-review.md`. Engineering feasibility pre-verified. Date: 2026-05-31._

**Bottom line:** Both personas independently rated the **same** issue P0 — the Buyer Q&A page is a read-only SLA report you cannot answer from. That convergence, plus a clean in-pattern backend path, makes the decision easy: **build in-app Buyer Q&A answering (with an optional AI-draft assist) this loop.** Everything else is real but ranks below it. Below I critique each report (no rubber-stamping), then scope the one feature, then rank the next 3–5, then distill the brand steer.

---

## 1. Critique of each report

### 1a. Novice ("Diego") — mostly strong, one inflated item

**Real & high-impact (accept):**
- **P0 "Preguntas can't answer"** — confirmed in source. `qa-page.component.ts` has `displayedColumns = ['asked_at','source','item','question','sla','hours_open']` (no actions column) and **zero mutation methods**; the answer only shows in a tooltip. The subtitle literally tells him to answer fast (`es-MX.json:431`) while giving no way to. This is the strongest finding in the whole loop. **Accept as the headline.**
- **"SLA" shown raw** (col header, "Más de {{hours}}h SLA") — legitimate jargon hit and a *cheap* copy fix. **Accept**, and I'm folding it into the Q&A feature scope (we're already in that file).
- **"Crear OC" (supplier PO) vs "Enviar a ML Full" (transfer) conflation** in the low-stock flow — real mental-model trap, genuinely confusing for a solo seller. **Accept, backlog** (copy + action-split, not structural).

**Where I push back / downgrade:**
- **#2 "No profit/margin view" rated P0 — I disagree on the P0.** It's a real gap and the single best *next* feature, but it is **not** co-equal with Q&A: Q&A is a *daily, time-boxed, reputation-damaging* task with a hard SLA; "am I making money?" is a periodic question the power user can already answer from order-detail (`sales-order-detail.html` has full economics). One is a blocked daily workflow, the other is a missing convenience view. **Downgrade to P1, rank #1 in backlog.**
- **#4 "Day-1 dashboard is enterprise onboarding"** — partially **already resolved**. Per `06-build-review.md` and `dashboard.component.ts:121-125`, the cockpit is maturity-gated; the onboarding hero only shows for truly empty accounts. The *content* of that checklist is still operator-flavored ("Cuenta de administrador" first, "rastro auditable", "OC"), so there's a **copy** fix here, not a structural one. **Accept as a small copy item, not a redesign.**
- **#3 "Stale screenshots" — NOT product work.** This is a tooling artifact: the PNGs were shot with the old `capture.mjs` (light/English/old-nav) and never regenerated with `capture2.mjs`. Diego himself correctly evaluated the *code* instead. **Explicitly out of scope as a product item** — it's a one-line re-capture chore for whoever runs the next review, and it must not consume engineering of the build loop. I'm calling this out because it appears in *both* persona reports and could otherwise masquerade as work.
- **Payments "respuesta cruda/webhook" jargon (#7), inventory-term inconsistency (#8)** — real but low-traffic P2 copy nits. **Accept, low backlog**, ride a future microcopy pass.

### 1b. Power ("Sofía") — disciplined, well-cited, minimal over-scope

**Real & high-impact (accept):**
- **P0 Q&A read-only** — same finding, independently reached from the power angle ("I can see I'm 3 over SLA but can't answer one"). Reinforces the decision. The AI-assist ask is hers; I'm including it as an *optional, additive* element, not a blocker (see scope).
- **Ship→push-to-ML doesn't surface expired-OAuth inline** (`stock-transfer-detail.ts:82-101`) — confirmed asymmetry: `syncListings` renders a Reconnect banner from `summary.needs_reauthorization`, but `ship(true)` falls through to the generic interceptor toast. This is a genuine recoverability gap on a money path. **Accept, backlog #2** (it's a focused reuse of an existing banner, not new infra).
- **Orders list: no pagination/search + bare `$` + no margin column** (`sales-order-list.html:81`) — three real defects in one screen. The bare `$` is the *exact* ambiguity `MoneyPipe` exists to kill and it's being bypassed. **Accept, backlog #3.** I'd bundle these since they're the same file.

**Where I push back / downgrade:**
- **#5 transfer picker capped at 25 / no on-hand** and **#6 dashboard "needs attention" capped at 8** — both real at volume, but these are **tuning** items, not workflow blockers. The 8-row cap has a "view all" escape; the picker cap has client filter. **Downgrade to P2**, opportunistic.
- **#7 "inline reorder on dashboard triage table"** — I **reject for now.** Adding a mutating PO action onto a read-optimized triage table grows surface and risks the "two restock concepts" confusion Diego flagged. The triage table's job is *route me to the fix*, not *be the fix*. Keep it a link. Revisit only if data shows drop-off.
- **#8 stale screenshots** — same tooling artifact as Diego's #3. Not product work.

**Net on the two personas:** They converge on Q&A (P0) and diverge exactly where `04-pm-decision.md` predicted — Diego wants outcomes/simplicity (profit view, plain words), Sofía wants density/scale (pagination, margin column, inline reauth). Both are served *sequentially* by the backlog below; neither requires dumbing down the cockpit. I am explicitly **protecting the power user**: no feature this loop removes density or hides a power affordance.

### 1c. Market & Brand — sharp, but mostly *steer*, not *build*

Strong, well-sourced, and correctly skeptical (the Clip/Konfío evidence that warm-non-blue reads trustworthy in MX is the useful spine). But for an *engineering build loop* most of it is **directional**, and a few items I won't fund now:

- **Accept as cheap directives (see §4):** warm the neutral tokens a few degrees; keep brand-red strictly for action/identity and *off* data/loss; use gold `--accent-2` (not red) for the AI surface; the "big honest MXN number" treatment. These are token/usage rules that cost ~nothing and directly de-generic the UI.
- **Push back / defer:** the **pivot-wedge sync animation** and **tilt-up success state** are lovely "signature moments" but are net-new motion work with no user-blocked workflow behind them — **defer to a dedicated brand-polish loop**, not this one. Same for font-self-hosting/skeleton overhaul (real perf wins, but separate workstream; `06-build-review` says fonts were self-hosted in S1 — researcher may be reading stale memory).
- **Disagree (or at least: not now):** **"respect `prefers-color-scheme` on first run."** The brand is *locked* dark-default per memory (`project_obsidian_chile_redesign.md`), the contrast guard enforces dark tokens, and "dark-first" is the deliberate market wedge. The daylight-warehouse concern is real but the answer is a *first-class light theme* (already shipped + guarded), not weakening the default. **No change this loop.**
- **The red-vs-loss-red collision (~1 hue apart)** is the one brand item with *functional* teeth. I accept the principle but it's a guard/token tweak — **fold into §4 as a directive**, let the contrast guard own enforcement, don't make it a feature.

---

## 2. THE DECISION — In-app Buyer Q&A answering (with optional AI-draft assist)

**Why this and not profit-view:** two independent personas, P0 each; it's a *daily, SLA-bound, reputation-critical* ML workflow (the core job-to-be-done for a Full seller); and the backend path is clean and in-pattern. The tool already tells the seller to answer fast and tracks their breaches — not letting them act is the single biggest promise/reality gap in the product. Building the answer action makes the existing SLA report *true*.

### Full-stack surface

**Backend (`backend/`):**
1. **ML client method** — add `async def post_answer(self, question_id: str, text: str, access_token: str) -> Dict[str, Any]` to `services/marketplaces/mercadolibre.py`, mirroring `fetch_question`/`sync_inventory`: `POST {API_URL}/answers` with body `{"question_id": <int>, "text": <str>}`, `Authorization: Bearer`, `raise_for_status()`. Honor the existing **stub-token** convention (return a deterministic stub dict when token is missing/`STUB`) so tests/dev exercise the path offline, exactly like `publish_listing`.
2. **Endpoint** — add `POST /api/v1/reports/questions/{id}/answer` in `endpoints/reports.py` (sibling to the existing `GET /questions`). Body: `{ "text": str }` (validate non-empty, trim, length cap e.g. 2000). Loads the `MarketplaceQuestion` by id, resolves its credential, calls `post_answer` through the **existing `MarketplaceService.call_with_401_retry`** wrapper (so an expired token force-refreshes once). On success: set `answer_text`, `answered_at=now`, `status` → answered, commit; return the updated row shape (reuse `QuestionRow`). On token-dead: surface a structured `needs_reauthorization` signal (don't just 500) so the UI can show Reconnect.
3. **(Optional, additive) AI draft** — `POST /api/v1/reports/questions/{id}/draft-answer` returning `{ "draft": str }`. **NOTE / correction to the brief:** `services/ai_service.py` is an *embeddings-only* Protocol (SentenceTransformer/Dummy) — there is **no LLM text-generation service today**. So the AI-draft must either (a) call the existing LLM path the marketing `quick-post`/`ai-tab` features use, if one exists, or (b) ship behind a feature flag with a `DummyAIService`-style stub. **The AI draft is explicitly OPTIONAL and must not block the answer feature.** If the LLM wiring isn't trivially reusable, ship answering *without* it and backlog the draft.

**Frontend (`frontend/src/app/dashboard/pages/qa-page/`):**
4. **Service** — add `answerQuestion(id, text)` (and optional `draftAnswer(id)`) to `dashboard/services/analytics-reports.service.ts`, returning the updated `QuestionRow`.
5. **Composer UI** — add an **actions column** + per-row **"Responder"** button → opens a compact answer composer (inline expansion row or a `mat-dialog`). Composer shows the buyer question (full text, not just tooltip), a `mat-form-field` textarea, optional **"Borrador con IA"** secondary button (only if the draft endpoint ships), a **chile-red primary "Enviar respuesta" CTA**, and a cancel. On submit: disable + spinner, call service.
6. **Local-state update** — on success, patch the row in `rows[]` in place (`answer_text`, `answered=true`, `sla_status='answered'`, recompute counters: `unansweredCount--`, `answeredCount++`, `breachedCount--` if it was breached) **without a full reload**, and toast success. `QuestionRow` already carries `external_question_id` + `answer_text` to the client, so no extra fetch is needed.
7. **Inline reauth** — if the response signals `needs_reauthorization`, render a Reconnect affordance (reuse the marketplace reauth banner pattern) instead of a generic toast — this is the *same* gap Sofía flagged on Ship; solving it here sets the reuse precedent.
8. **Jargon fix (rides along, same file):** rename raw **"SLA"** → "Tiempo de respuesta"; "Más de {{hours}}h SLA" → "Lleva {{hours}} h sin responder"; "Vencida" stays. Plain `tú` voice throughout the composer.

**i18n (`es-MX.json` + `en.json`):** new keys under `dashboard.qaPage.*`: `answer` ("Responder"), `answerComposerTitle`, `answerPlaceholder` ("Escribe tu respuesta al comprador…"), `sendAnswer` ("Enviar respuesta"), `aiDraft` ("Borrador con IA"), `cancel`, `answerSuccess` ("Respuesta enviada"), `answerError`, `reauthNeeded` ("Reconecta tu cuenta de MercadoLibre para responder"), plus the renamed `cols.sla`/SLA strings. es-MX is default and authoritative; en parity required (the i18n guard enforces both).

**Tests:**
- Backend: `post_answer` stub-token path + real-token payload shape; endpoint success (persists `answer_text`/`answered_at`, updates counters), empty-text 422, unknown-id 404, **401→reauth** structured response (not 500).
- Frontend: `qa-page` spec — composer opens, submit calls service, **local row + counters update without reload**, error shows toast, reauth shows Reconnect. Use the existing `getTranslocoTestingModule()` helper. Must keep the suite green (currently 130 files / 774 tests).

### Acceptance criteria (crisp)
1. From `/reports/qa`, a seller can click **Responder** on any unanswered/breached row, type a reply, and submit **without leaving Fulcrum**.
2. On success the answer reaches ML via `POST /answers` (real token) or the deterministic stub (dev/test), and the row flips to **answered** in place with counters updated — **no full page reload**.
3. An expired ML token surfaces an **inline Reconnect** affordance, not a generic toast.
4. Empty/whitespace answers are blocked client- and server-side; the textarea enforces a sane max length.
5. Raw **"SLA"** is gone from the user-facing Q&A UI, replaced with plain es-MX `tú` copy.
6. Primary CTA is **chile-red `#FF4D2E`**; AI-draft (if shipped) is a *secondary* affordance; money (none on this screen) N/A; all new strings localized es-MX + en, i18n guard passes.
7. Full test suite green; new backend + frontend tests cover success, validation, and reauth paths.

### Explicitly OUT of scope (do NOT gold-plate)
- AI draft is **optional**; ship answering without it if LLM wiring isn't a clean reuse.
- No bulk/multi-answer, no canned-reply templates, no answer editing/deletion, no answer history beyond the single `answer_text`.
- No new Q&A webhook/ingest work (ingest already exists via `questions_service.py`).
- No dashboard changes, no profit view, no orders-list work (those are backlog).
- **Stale screenshots are not part of this** — re-capture is a reviewer chore, tracked separately.

---

## 3. Ranked backlog (next 3–5, for the loop to continue)

| Rank | Item | Files | Effort | Impact | Notes |
|---|---|---|---|---|---|
| **1** | **Profit / "¿gané o perdí?" summary** — dashboard "Ganancia del mes" card (revenue − COGS − ML fees − gastos) + per-product margin column. | `dashboard.component.*`, products list, reuse order-detail economics. | **M** | **High** | Diego's #2; the data exists in order-detail/economics — this is *aggregation + surfacing*, not new accounting. Strongest *next* feature. |
| **2** | **Inline ML reauth on Ship→push** — `ship(true)` detects `needs_reauthorization` and renders the existing sync reauth banner + Reconnect CTA. | `stock-transfer-detail.ts:82-101` / `.html`. | **S** | **High** | Sofía P1; pure reuse of the sync banner; closes a money-path recoverability gap. Pairs naturally with the Q&A reauth work (same pattern). |
| **3** | **Orders list: pagination + search + MoneyPipe + margin column** — `mat-paginator` (server-side), order-ID/SKU search, switch bare `$` → `\| money:order.currency`, add net-margin% column. | `sales-order-list.html`, orders service. | **M** | **High** | Sofía's #3+#4 bundled (same file). Bare `$` is an active trust/MXN bug; margin-at-a-glance serves both personas. |
| **4** | **Low-stock "OC vs Enviar a ML Full" disambiguation** — split the low-stock widget actions into "Pedir a proveedor" vs "Enviar a ML Full" with one-line helpers; plain-Spanish "Umbral"→"Avísame cuando baje de", "Velocidad"→"Ventas por día". | dashboard low-stock widget, `es-MX.json`. | **S** | **Med** | Diego's #6/#8; copy + action-label change, no structural work. |
| **5** | **Brand "signature moment" (pick ONE)** — the **"tilt-up to the right" success state** on a completed money action (e.g. after answering a question or pushing stock), built from the pivot-wedge SVG (CSS, `prefers-reduced-motion` → opacity). | shared success/confirmation primitive. | **S–M** | **Med** | The cheapest, most ownable brand item from §4.2; do exactly one, well, and reuse it. Defer the sync-load animation. |

Deferred / opportunistic (P2, not in next 5): dashboard triage cap 8→25 + sort; transfer picker 25-cap + on-hand qty; payments "webhook/respuesta cruda" rewording; broad jargon microcopy pass.

---

## 4. Brand steer — 2–3 cheap directives for ANY new UI this loop

These are **token/usage rules**, not new components — honor them in the Q&A composer and anything else built this loop:

1. **Chile-red is for the ONE primary CTA and identity only — never for data, deltas, or loss.** The brand-red `#FF4D2E` and loss-red are ~1 hue apart and *will* read identically to a stressed seller. So: the composer's "Enviar respuesta" = chile-red; everything else (AI-draft, cancel, links) = cool-blue `--accent-2`/affordance or neutral. **Always icon-pair loss/danger** (↓/arrow) so red never carries status alone. The `check_theme_contrast.py` guard owns enforcement of chile-red-as-text.

2. **AI surface = warm gold `--accent-2 (#FFC23D)`, calm, never red.** If the AI-draft button/affordance ships, tint it gold and give it a quiet shimmer "pensando…" state — *not* a red glow. This keeps red off the AI surface (avoids the "energy-drink" read) and gives AI its own consistent signal across the app.

3. **The "big honest MXN number" wherever money appears.** When the backlog profit/orders work lands: hero money number oversized, **tabular-lining**, display face, with the unit small/muted (`$248,300.50 MXN`), right-aligned, never jittering — via the existing shared `MoneyPipe`/`mxn` pipe. (No money on the Q&A screen, but this binds the profit + orders backlog items.) Pair with the §4.1 *warm-neutral token nudge* (cool greys → a few degrees warm) — a one-time token edit that delivers the locked "Warm" pillar for free and is the difference between "obsidian" and "another blue-grey dark theme."

_Voice on everything new: plain es-MX, `tú`, peer-not-bank (Konfío lesson). Design columns/buttons for ~15–25% Spanish overflow._
