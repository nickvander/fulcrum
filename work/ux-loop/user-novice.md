# Fulcrum — Novice User Walkthrough ("Diego", first-time ML seller, CDMX, es-MX, non-technical)

**Evaluated:** 2026-05-31 against real source (`frontend/src/app/**`, `es-MX.json`) + screenshots in `work/redesign/shots/`.

> ⚠️ **Methodology caveat — the screenshots are STALE and misleading.** Every `desktop-*.png` / `mobile-*.png` was produced by the OLD `work/redesign/shots/capture.mjs` (mtime 2026-05-30 16:30), which never sets `localStorage` language/theme. They render the app in **light theme + English**. But the *current* code defaults a brand-new user to **dark theme + es-MX** (`core/services/settings.service.ts:51-55` `DEFAULT_SETTINGS = { theme:'dark', language:'es-MX' }`; `transloco-root.module.ts:60` `defaultLang:'es-MX'`). The newer `capture2.mjs` sets es-MX but did not regenerate these PNGs. The screenshots also show the OLD nav (flat "Stock audit log", "Physical count", "Purchasing/Marketplaces" groups) — the current `core/components/sidenav/sidenav.html` has a redesigned IA with a top-level **"Acciones diarias"** group. **So I evaluated the actual code, treating screenshots only as layout reference, and call out where they lie.** Anyone reviewing UX from these PNGs alone will reach wrong conclusions.

Net: the es-MX localization is **real, thorough, and high quality** (idiomatic MX Spanish across ~3,100 lines). The big remaining novice problems are (a) operator/B2B jargon leaking into the Spanish UI, (b) a dashboard built for an operations manager, not a 30-SKU seller, and (c) **"Preguntas" is a read-only report with no way to actually answer a buyer.**

---

## Journey 1 — First arrival: login → first dashboard ⚠️

- **Login** (`auth/components/login/login.html`): template uses transloco keys; es-MX values are good — "Bienvenido de nuevo", "Ingresa tus credenciales…", "Ingresar" (`es-MX.json:138-142`). The screenshot `desktop-00-login.png` showing "Welcome back / Sign In / Management Console" is the stale-English artifact, NOT what Diego sees. Real login = fine. ✅ for login itself.
- **First dashboard** is the friction. A brand-new Diego lands on a **"Lista de incorporación" (onboarding checklist) with "5/7 obligatorios completados"** plus a second giant **"Bloqueos por atender / Listo para lanzamiento"** block (`es-MX.json:490-559`). For a guy with 30 SKUs this reads like enterprise deployment software. Jargon he won't parse: "Coincidencia de proveedor", "rastro auditable" (`steps.inventory.description`), "Credenciales de marketplace", "fuente de verdad" (`launchReadiness.subtitle`), "OC". The very first card he's pushed toward is "Cuenta de administrador → Administrar usuarios" — irrelevant to a solo seller.
- There's no plain "¿Qué hago primero?" → "1. Agrega tus productos  2. Conecta MercadoLibre". The checklist ordering buries products/marketplace under admin/supplier-matching tasks.

**Verdict:** Login clear; dashboard overwhelming and operator-flavored. The thing Diego actually wants on day 1 (connect ML, see stock) is not the headline.

## Journey 2 — Add first product + starting stock ✅ (mostly)

- Nav path is clear once you know it: **Inventario → Productos** (`sidenav.html:60-65`), or the **"Agregar Producto"** button. Strings are friendly: `products.addProduct`="Agregar Producto", plus a genuinely novice-friendly **photo/barcode/AI quick-add** (`takePhoto`="Tomar Foto", `scanBarcode`, `quickAddTitle`="Agregar Producto Rápido", `productNamePlaceholder`="ej. Widget A") (`es-MX.json:662-700`). Good.
- Friction: the column/field **"SKU"** appears raw with no explanation — Diego doesn't know the word. The low-stock threshold field is the bright spot: "Avísame cuando el stock baje de" + hint "Marcaremos este producto como bajo cuando llegue a este número" (`es-MX.json:921-922`) — exactly the right register; "SKU" should get the same treatment.
- Minor: products grid shows **every item at "0 In Stock" in red** (stale shot `desktop-02-products.png`) — for a real fresh account this zero-state is alarming with no "add stock" nudge on the row.

## Journey 3 — Find what's low, send inventory to ML Full ⚠️

- **Two different "restock" concepts are conflated and both use jargon.** The dashboard low-stock widget (`es-MX.json:407-427`) exposes "Umbral", "Velocidad", "Días restantes", and a **"Crear OC"** button — but "Crear OC" makes a *supplier purchase order* (buy more from your vendor), NOT sending stock to ML Full. Sending to ML Full is a *separate* screen ("Transferencias de stock" / nav "Enviar a ML Full", `/marketplaces/transfers`). A novice will conflate "I'm low → restock" with "send to Full" and pick the wrong one.
- Good news the screenshots hide: the **current sidenav has a top-level "Acciones diarias" group** with a single-tap **"Enviar a ML Full"** (`sidenav.html:22-30`, icon `local_shipping`) and the same on mobile bottom-nav (`bottom-nav.ts:32`). That's a real improvement over the stale "Stock Transfers" screenshot.
- The transfers screen itself (`desktop-07`) is English in the shot ("Stock Transfers / Allocation planner / Reconciliation / Amazon FBA") but es-MX has "Transferencias de stock", "Conciliación", etc. Still, "Allocation planner" / "Reconciliation" are operator concepts Diego won't need or understand.

**Verdict:** Path now exists and is promoted, but "OC vs transfer" ambiguity + jargon ("Umbral", "Conciliación", "FBA") will trip him.

## Journey 4 — Find and answer a buyer question ❌ BLOCKED

- There **is** a "Preguntas" entry now (`sidenav.html:32-37` → `/reports/qa`; mobile bottom-nav too). Good discovery.
- **But the page cannot answer anything.** `dashboard/pages/qa-page/qa-page.component.html` + `.ts` is a **read-only report**: counters (Sin responder / Vencida / Respondidas) and a table (Preguntada, Canal, Artículo, Pregunta, SLA, Abierta). There is **no reply box, no "Responder" button, no deep-link to MercadoLibre** — `grep answer|reply|responder|submit` in the component finds nothing actionable. The answer text only shows in a hover tooltip.
- Cruel irony: the subtitle says *"Responder rápido protege tu reputación en MercadoLibre"* (`es-MX.json:431`) — it tells Diego to answer fast but gives him no way to answer. He'll click expecting an inbox and hit a dashboard.
- Jargon: **"SLA"** is shown raw in the column header and in "Más de {{hours}}h SLA" / "Vencida" (`es-MX.json:435-460`). Diego has never heard "SLA".

**Verdict:** His single most frequent daily task (reply to buyers) is not possible in-app. Hard block.

## Journey 5 — Am I making or losing money? ⚠️ / partial ❌

- **Expenses** (`/expenses`): clean, es-MX-localized, friendly empty state "Add Expense". Fine for logging costs. But this only tracks money *out*.
- **There is no profit / margin / "¿gané o perdí?" view.** Nothing ties revenue (Orders/Payments) minus COGS minus ML fees minus expenses into a single "this is your profit" number. Diego cannot answer "¿estoy ganando dinero?" from one screen.
- **Payments** (`/payments`): subtitle (es-MX `marketplaces`/payments block) talks about "estado, errores, respuesta cruda del proveedor y el webhook más reciente" — **"respuesta cruda del proveedor", "webhook"** are developer terms in a screen a seller might open hoping to see "¿me pagaron?". Wrong audience.
- Product "Cost / Last Cost / Price" columns expose **"COGS"-style** thinking without a computed margin per item.

**Verdict:** Can record expenses; cannot see profit. The core "estoy ganando dinero" question is unanswered.

## Journey 6 — Mobile ✅ (usable) / ⚠️ (same jargon)

- Layout is genuinely responsive: `mobile-01-dashboard.png`, `mobile-02-products.png` (card layout, search, filter chips, big FAB), `mobile-04-marketplaces.png` all reflow cleanly; hamburger + (in current code) a **bottom-nav** with Dashboard / Enviar a ML Full / Preguntas / Gastos (`bottom-nav.ts:31-34`) — exactly the right 4 daily actions for a phone. Good.
- Same content problems carry over: English in the *shots* (stale), and the real jargon ("Unlisted"→es "Sin publicar" ok, "SKU", "SLA") remains. "Add Marketplace Account" header wraps awkwardly on the marketplace card (`mobile-04`).

**Verdict:** Mechanically usable on a phone; inherits the jargon + missing-answer + missing-profit gaps.

---

## Top 8 friction points (ranked)

| # | Sev | Problem | One-line fix |
|---|-----|---------|--------------|
| 1 | **P0** | **"Preguntas" can't answer questions** — `qa-page` is a read-only SLA report; no reply box/button, yet subtitle tells him to answer fast (`qa-page.component.html`, `es-MX.json:431`). | Add an inline "Responder" action that posts the reply (or, interim, a per-row deep-link to the ML question), so the page does what its title promises. |
| 2 | **P0** | **No profit/margin view** — can log expenses but nothing shows "¿gané o perdí?" (revenue − COGS − ML fees − gastos). | Add a dashboard "Ganancia del mes" card and a per-product margin column. |
| 3 | **P1** | **Stale screenshots show English + light theme + old nav**, hiding that the app is actually es-MX/dark with a redesigned IA. Anyone reviewing from PNGs is misled. | Regenerate all `shots/*.png` with `capture2.mjs` (es-MX + dark) before any UX review. |
| 4 | **P1** | **Day-1 dashboard is enterprise onboarding** ("Lista de incorporación 5/7", "Bloqueos por atender", admin/supplier-matching first) — wrong altitude for a 30-SKU solo seller. | Lead with "1. Agrega productos 2. Conecta MercadoLibre 3. Mira tu stock"; collapse launch-readiness for solo accounts. |
| 5 | **P1** | **Raw "SLA" in buyer-questions UI** (`cols.sla`, "Más de {{hours}}h SLA", `es-MX.json:435-460`) — meaningless to Diego. | Replace with plain language: "Tiempo de respuesta" / "Lleva 14 h sin responder" / "Tarde". |
| 6 | **P1** | **"Crear OC" (supplier reorder) vs "Enviar a ML Full" (transfer) conflated** in the low-stock flow; both feel like "restock". | On the low-stock widget, split actions clearly: "Pedir a proveedor" vs "Enviar a ML Full", with one-line helper text. |
| 7 | **P2** | **Payments page speaks developer** — "respuesta cruda del proveedor", "webhook" (Payments subtitle) on a screen a seller opens to check "¿me pagaron?". | Reword to "Estado de tus pagos de Mercado Pago"; hide raw/webhook detail behind an "avanzado" toggle. |
| 8 | **P2** | **Inconsistent + jargony inventory terms** — "Stock"/"SKU"/"Umbral"/"Velocidad" raw, and "Existencia Baja" vs "Stock bajo" vs "Stock Bajo" used interchangeably. | Standardize on one plain term ("stock bajo"), gloss "SKU" once, rename "Umbral"→"Avísame cuando baje de", "Velocidad"→"Ventas por día". |

---

## Re-validation (post-fix) — Diego

**Scope:** Re-walked the P0 #1 journey ("Preguntas can't answer questions") on the new code. Reviewed `qa-page.component.{ts,html,scss}`, `analytics-reports.service.ts::answerQuestion`, the i18n blocks (`es-MX.json` / `en.json` → `dashboard.qaPage.*`), and the backend chain (`questions_service.answer_question`, `POST /questions/{id}/answer`, `mercadolibre.post_answer`).

### Verdict: ✅ fixed & smooth (one P2 nit + two carry-over items)

**The journey as Diego:**
1. **I open Preguntas, I see a question sin responder.** Each unanswered row now has a clear **"Responder"** button with a reply icon (`qa-page.component.html:107-113`). Affordance is obvious — it's an action button in an "Acciones" column, not buried. ✅
2. **I click Responder.** An inline composer opens under the row (`html:124-173`) with a plain-Spanish title **"Responde al comprador"**, the buyer's question repeated for context, a textarea placeholder **"Escribe tu respuesta al comprador…"**, and **"Enviar respuesta" / "Cancelar"** buttons (`es-MX.json:464-470`). All `tú` voice, zero jargon. The Send button is disabled until I type something (`ts:187-189`). ✅
3. **I send.** Button shows a spinner (`html:166-167`); on success the composer closes, the row's action cell flips to a green **✓ "Respondida"** tag (`html:114-119`), the answer text appears in a read-only detail row (`html:174-178`, "Tu respuesta: …"), and the **counters update live** (Sin responder −1, Respondidas +1, and Tarde −1 if it was breached) — all via in-place patch, **no full reload** (`ts:224-242`). Smooth and clearly confirms it worked. ✅
4. **If my MercadoLibre connection is expired:** backend returns `409 {code: 'needs_reauthorization'}` (`reports.py:3044-3049`); the frontend matches that exact shape (`ts:214`, body is `err.error.code`) and shows an in-composer warning banner **"Reconecta tu cuenta de MercadoLibre para responder."** with a **"Reconectar"** link to `/marketplaces` (`html:132-141`). I understand exactly what to do. ✅
5. **SLA wording:** the old raw "SLA" is gone from the column — header is now **"Tiempo de respuesta"** (`es-MX.json:451`), statuses are **"Respondida / Pendiente / Tarde"** (`:455-459`), and the breached counter reads **"Más de {{hours}}h sin responder"** (`:444`). Plain and understandable. ✅

**Backend is real, not a stub:** `answer_question` resolves the question, checks credential reauth, calls `connector.post_answer` (real `POST /answers` to ML with Bearer token; only stubs on STUB/empty tokens — `mercadolibre.py:682-697`), then persists `answer_text`/`answered_at`/`status=ANSWERED` and commits (`questions_service.py:196-213`). Idempotent: already-answered → 409, empty → 400, non-ML → 502. Solid.

### Residual nits
- **P2 — No explicit "enviada" toast.** The string `answerSuccess` ("Respuesta enviada") exists in both locale files (`es-MX.json:471`) but is **never used** in the component — it's an orphaned key. The visual row-flip is adequate confirmation, so this is cosmetic, but either wire up a snackbar or drop the dead key.
- **P2 (new, minor) — "Artículo" column still shows a raw `item_id`** (e.g. `MLM123…`) in a monospace `<code>` pill (`html:80`), not a product name. Diego won't recognize which listing a question is about from the ML item id alone. Pre-existing, not introduced by this fix, but adjacent.
- **Carry-over (cosmetic):** "SKU"/"Canal" elsewhere on the page unchanged — out of scope for this P0.

**Bottom line:** P0 #1 is genuinely resolved. A non-technical seller can now find, write, and send a reply in plain es-MX, see it confirmed without a confusing reload, and recover from an expired connection. Ship it; clean up the orphaned `answerSuccess` key.

---

## Re-validation (post-fix) — Diego: profit summary

**Evaluated:** 2026-05-31 against real source — backend `backend/src/api/v1/endpoints/reports.py:1606-1766` + `expenses.py:55-73`; frontend `dashboard/widgets/profit-summary-widget/*`, `dashboard/pages/profit-page/*`, route `app-routing.module.ts:89`, mount `dashboard/pages/dashboard/dashboard.component.html:43`, service `analytics-reports.service.ts:32-52,352-354`; i18n `es-MX.json:198-226` / `en.json:200-228`.

**Prior flag:** Fulcrum had NO plain "¿gané o perdí?" view — profit/margins were buried. This re-walk judges the shipped fix.

**Verdict: ✅ fixed & smooth.** This is the real bottom line, in plain MX Spanish, on the first screen.

### Journey (as Diego)

1. **Log in → see the answer without digging? YES.** The compact widget is the **lead signature tile** at the very top of the populated cockpit (`dashboard.component.html:43`, `[compact]="true"`, above even the onboarding checklist). Verdict headline + big number are immediate: "Ganaste este periodo" / "Perdiste este periodo" (`es-MX.json:210-211`) with a 2.75rem hero number (`scss:86-93`). Plain `tú`, no jargon. ✅

2. **Breakdown ladder understandable WITHOUT accounting? YES.** The ladder relabels every accounting term into plain language (`es-MX.json:214-221`): ingresos → "Lo que vendiste (ingresos)", "Costos de tus ventas" (with a `help_outline` tooltip spelling out producto/comisiones/envío/publicidad, `html:56-58`), "Ganancia de tus ventas", "Gastos de tu operación (renta, sueldos, etc.)", "Resultado neto". The one technical-ish word, "neto", is anchored by the verbose labels above it. No bare "COGS / margen / contribución" leaks into this surface. ✅

3. **Switch periods? YES, and it makes sense.** Full-page toggle "Este mes / 7 días / 30 días" (`html:9-20`, `es-MX.json:205-207`); refetches server-side over one aligned window (`component.ts:72-76`; backend `_resolve_profit_window` 1606-1630). Compact dashboard tile stays pinned to "Este mes" (no toggle) — correct, keeps the cockpit calm.

4. **Empty state if nothing sold? YES — no fake $0.** Backend returns `verdict=null` + `has_realized_orders=false` with zero orders (1741-1748), and the widget gates on `hasData` (`component.ts:92-94`) to render a warm peer line: "Cuando hagas tu primera venta, aquí verás si ganas o pierdes." (`es-MX.json:224`, `html:30-35`) — NOT "$0 / quedaste a mano". The "quedaste a mano" copy is reserved strictly for a real break-even with realized orders. Exactly the fix I asked for. ✅

5. **MXN clear? Loss visually clear & NOT chile-red? English leakage? YES / YES / NONE.**
   - **MXN:** hero uses `money:'MXN':{showCode:true}` → "MX$1,234.50 MXN" (`html:44`, pipe `money.pipe.ts:56-57`); ladder rows render "MX$…". Unambiguous.
   - **Loss color:** loss maps to `.result-lost` → `var(--error-color)` = **#FF6B61** (`_tokens.scss:53`), which carries an explicit comment "stays distinct from brand #FF4D2E". Brand chile-red is reserved for the "Ver detalle" action only (`html:88`). So loss = danger-semantic red + ↓ `arrow_downward` (`component.ts:108`), profit = success + ↑. Brand rule honored, and there's a spec test asserting the hero never carries the won/primary class on a loss (`spec.ts:100-108`). ✅
   - **English leakage:** none in the profit block; key parity es-MX↔en is exact (21/21, verified). `tú` voice throughout.

6. **Ad-spend caveat footnote — understandable or scary?** ⚠️ borderline. "Si registras publicidad o envíos como gasto y también en el costo de cada venta, podrían contarse dos veces." (`es-MX.json:222`) It's honest and grammatically plain, but it's a **conditional accounting nuance** ("double counting") that a true first-timer may not parse, and a faint worry ("¿mi número está mal?") can linger. Muted styling (`--text-hint`, 0.75rem, `scss:185-190`) keeps it from dominating. Not blocking.

### Residual nits

- **P2 (new, minor) — footnote register.** The double-count caveat is the only line on this surface that assumes the reader understands cost attribution. Softer framing would land better, e.g. "Para que tu resultado sea exacto, registra publicidad y envíos en un solo lugar (como gasto **o** dentro del costo de cada venta), no en los dos." Optional; the footnote is correctly de-emphasized.
- **P2 (note, not a defect) — verdict says "este periodo", not "este mes".** The brief expected "Ganaste/Perdiste **este mes**", but since the period is switchable (7 días / 30 días), "este periodo" is the *correct* generalization — "este mes" would be wrong while viewing a 7-day window. Smart deviation; leave as is.
- **P2 — empty-account branch never mounts the widget.** The lead tile lives only in the `#cockpit` (populated) branch (`dashboard.component.html:21,40`); a brand-new zero-everything account sees the onboarding flow instead, so the widget's own friendly empty state only shows once there's *some* activity but no realized orders in the window. Acceptable by design, just noting the empty-state copy is slightly less reachable than it looks.
- **Carry-over (good):** comprehensive spec coverage exists for empty-state-not-$0, loss-not-chile-red, MXN+code, ladder values, period switch, footnote, error state (`spec.ts:85-171`).

**Bottom line:** The buried-profit P0 is genuinely resolved. Diego now sees, on the very first screen, a plain-Spanish "Ganaste/Perdiste este periodo" + an honest MXN bottom line that truly subtracts operating expenses from sales profit, with a non-accountant ladder, a safe empty state, correct danger-red (not brand) loss treatment, and working period switching. Ship it; the only follow-up is softening the double-count footnote (P2).
