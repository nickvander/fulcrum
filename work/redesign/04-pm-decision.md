# Fulcrum — PM Decision Doc (Full Redesign)

_Owner: Product. Inputs: 00-journey-map, 01-ux-persona-sofia (power user), 02-ux-persona-diego (novice), 03-market-brand-brief (BOLD & MODERN). Date: 2026-05-30._

Founder directive: **full visual + UX redesign with a distinctive brand identity, optimized for ease-of-use, modern feel, learnability, and performance.** This doc decides what that redesign actually does — what we redesign, keep, or defer — grounded in the evidence, and where I push back on a "fix" that would add complexity or hurt the power user.

---

## 1. Read on the evidence (critique, not rubber-stamp)

The two personas converge hard on three things, and those are the spine of the redesign:

1. **es-MX is genuinely broken, not cosmetic.** Both personas independently verified hardcoded English on first-run-critical screens (login, product-form) and whole dialogs with zero i18n (`quick-post-dialog`, `ai-tab`). For a Mexico-first product whose brand pillar is literally "Grounded / local — native es-MX," shipping a redesign over a half-Spanish app would undercut the entire positioning. This is the highest-confidence, lowest-cost, highest-trust-impact item in the whole stack. It is real, high-impact, P0 — and it is a precondition for the brand work, not a separate nicety.

2. **Currency-in-USD on the dashboard "Total Value" card is a bug, full stop.** Both personas caught it at `dashboard.component.html` line 105. A Mexican seller seeing inventory value in dollars is a trust hit and a 5-minute fix. P0, no debate.

3. **Where the personas DISAGREE is the interesting part, and it's where I push back.** Diego wants the dashboard stripped to "just the checklist," outcome-based labels everywhere, jargon hidden, a one-time mental-model diagram, fewer paths. Sofía wants the opposite: fewer taps to dense daily tools, power tools surfaced, nothing in her way. **A naive redesign that satisfies Diego will gut the cockpit Sofía switched for.** The resolution is not a compromise screen — it is **progressive disclosure keyed to account maturity**, which the brand brief already endorses ("composed under high data density," "decisive defaults"):
   - Empty/new account → first-run mode: checklist hero, analytics suppressed until there's data. Serves Diego.
   - Populated account → full cockpit. Serves Sofía.
   - One codebase, one dashboard, state-driven. We do NOT build two apps, and we do NOT permanently dumb down the dashboard.

### What I am NOT treating as high-impact

- **"Add a one-time 3-bucket stock diagram" (Diego):** real comprehension gap, but a static explainer diagram is a weak fix and easy to over-invest in. The redesign should solve it through **outcome-based naming and inline context at the point of action** ("Enviar inventario a MercadoLibre Full") rather than a teaching modal nobody reads twice. Redesign the labels and the transfer flow's framing; defer any standalone tutorial/diagram.
- **Diego's "give novices ONE blessed PO path, hide the rest":** correct instinct, but PO ingest is Sofía-tier machinery and a novice rarely touches it in week one. Don't redesign the PO flow early to serve a novice who isn't there yet. Defer; lead the entry with the AI drag-drop and leave the power path intact.
- **"Inventory Count vs Inventory Audit are confusing labels" (Diego):** real but low-traffic; a copy/labeling fix that rides along with the i18n + nav pass, not its own initiative.
- **Dead "Publish to Amazon/eBay/Shopify" buttons in product-form (Sofía):** real (no click handlers, off-market noise) but it's a delete, not a redesign. Cheap cleanup folded into the product-form pass. eBay/Shopify are out-of-scope channels for a Mexico/ML-first product per memory — remove, don't build.
- **`/ingest` missing AuthGuard:** a security bug, not a UX/brand item. It must be fixed, but it belongs in the engineering bug queue, not the redesign backlog. Flagging it, scoping it out of the design loop.
- **PO/expense being "two taps deep under Purchasing":** Sofía's tap-count complaint is legitimate for *daily money* tasks (Transfers, Q&A, Expenses). It is NOT a reason to flatten the entire IA — Suppliers, PO creation, Users, Settings are correctly buried. Fix is targeted nav promotion + auto-expand active group, not a flat nav.

### Where BOTH personas must be served (call-outs)

- **Nav:** Diego needs a calm, learnable nav; Sofía needs daily tools ≤1 tap. Solution serves both: keep grouped IA (Diego's calm) but promote the 3 daily-money items and auto-expand the active group (Sofía's speed).
- **AI key:** Diego won't know what an LLM key is; Sofía just wants it not to silently no-op. Solution serves both: pull AI activation into onboarding (Diego learns it exists) AND add inline "activate AI" prompts where AI buttons would appear (Sofía/Diego both stop hitting dead affordances). The product-form `@if aiReady` hide pattern is the correct primitive — generalize it.
- **Dashboard density:** resolved by the maturity-gated disclosure above.
- **Buyer Q&A:** Sofía wants dashboard SLA visibility + in-app AI answering; Diego wants "SLA" renamed to "tiempo de respuesta." Both fold into one Q&A redesign.

---

## 2. Prioritized decision backlog

Priority key: **P0** = redesign-blocking / trust-critical, do first. **P1** = core to the redesign value, first or second loop. **P2** = real but later / opportunistic.

| # | Area | Item | Decision | Priority | Rationale | Success metric |
|---|------|------|----------|----------|-----------|----------------|
| 1 | Localization | Finish es-MX: convert `quick-post-dialog` + settings `ai-tab` (fully English), and the English literals in login, product-list, product-form, product-scanner, expense-dialog, po-ingest; remove the English dev comment in `expense-dialog.html` | redesign | P0 | Both personas' #1; directly contradicts the "native es-MX" brand pillar; cheap, high-confidence, precondition for brand copy work | 0 hardcoded user-facing English strings in an automated i18n-lint sweep of `frontend/src/app`; informal "tú" voice applied |
| 2 | Currency | Default everything to MXN: fix dashboard "Total Value" `currency:'USD'` (line 105) and expense KPI hardcoded `'$'`; standardize a money-format pipe with tabular numerals | redesign | P0 | Verified bug by both personas; Mexico-first; brand brief mandates tabular money formatting as a trust signal | All money renders MXN by default; one shared currency pipe; tabular-nums on every money/qty cell |
| 3 | Design system | M3 token foundation: Leverage Indigo light + Cockpit Dark, Inter (data) + display face (brand), semantic color chips, density -3/-4 tables, pivot-wedge logo/PWA icon | redesign | P0 | The redesign's core deliverable; everything else renders through it; escapes the Bind/Alegra SaaS-blue trap | Design tokens published + wired through both themes via existing sidenav toggle; Roboto fully removed; Lighthouse/perf budget held on mid-range Android |
| 4 | Global shell / nav | Promote daily-money items (Stock Transfers, Buyer Questions, Expenses) toward top-level; auto-expand the active group; keep grouped IA otherwise | redesign | P1 | Serves Sofía's tap-count without flattening IA (Diego's calm); targeted, not a teardown | Daily-money tasks reachable in ≤1 tap from any screen; nav comprehension unchanged for novices in usability test |
| 5 | Dashboard | Maturity-gated disclosure: empty account → checklist-hero first-run mode, analytics suppressed; populated → full cockpit; add Q&A-over-SLA and transfers-to-receive cards to the cockpit | redesign | P1 | Resolves the Diego/Sofía conflict in one state-driven screen; no second app, no permanent dumb-down | New-account dashboard shows ≤3 elements; populated dashboard retains all widgets; Q&A/transfers cards link in |
| 6 | AI activation | Pull AI-key step into onboarding checklist; add inline "activar IA" prompts where AI buttons appear (generalize the `@if aiReady` hide-not-disable pattern) | redesign | P1 | Diego learns AI exists; Sofía stops hitting silent no-ops; AI is the headline brand pillar ("visible, credible AI") | % of new accounts with AI configured by end of onboarding ↑; 0 dead/silent AI buttons |
| 7 | Buyer Q&A | Add dashboard "X over SLA" card (linking in); add in-app answer composer + AI "suggest answer" in `qa-page`; rename "SLA" → "tiempo de respuesta"; reconcile nav/route/module mismatch (Marketplaces label / `/reports/qa` / `dashboard/pages/qa-page`) | redesign | P1 | SLA/reputation task with no dashboard presence and no in-app answering today; serves both personas | Seller can answer a question without leaving Fulcrum; over-SLA count visible on dashboard; nav label/route/module consistent |
| 8 | Onboarding / first product | Add a starting-quantity field to product-form (today stock hides in a kebab "Adjust stock" dialog → first product shows 0); make onboarding a focused first-run flow (name → price → starting qty → connect ML) | redesign | P1 | Verified two-screen first-product trap; biggest novice stumble; small form change, big learnability win | New seller's first product shows correct on-hand without opening a second dialog |
| 9 | Stock transfer | Outcome-based naming ("Enviar inventario a MercadoLibre Full"); mirror the marketplace one-tap Reconnect reauth chip on the "push qty to listings" result so expired-OAuth failures are re-authable inline | redesign | P1 | Core ML-Full fulfillment loop; teaches the mental model through framing not a modal; closes Sofía's silent-failure gap | Failed push offers 1-tap reauth; transfer actions read as outcomes; novice completes a guided send-to-ML |
| 10 | Product form | Remove dead "Publish to Amazon/eBay/Shopify" buttons (no handlers, off-market); collapse reorder/threshold fields under "advanced"; plain-Spanish "cuánto te costó / a cuánto lo vendes" copy; lead marketplace tab with MercadoLibre | redesign | P2 | Removes noise + ambiguity (canonical path = marketplace-listing-dialog); reduces novice jargon; mostly delete + copy | Single unambiguous listing path; no dead buttons; reduced field count on default view |
| 11 | Jargon / microcopy | Outcome-based plain-Spanish labeling pass across SKU/UPC/COGS/FBA/landed cost/dead stock/reorder point; keep power terms available as secondary | redesign | P2 | Diego's broad jargon complaint; do as a copy layer, not structural change, so Sofía's density is preserved | Novice usability comprehension ↑; power-user term availability unchanged |
| 12 | Order / payments detail | Lead with plain "Ganaste $X en esta venta" / "ML te deposita $X el día Y" headline; keep the full Economics / settlement breakdown behind "ver detalle" | redesign | P2 | Serves novice without removing Sofía's first-class economics card; progressive disclosure again | Headline answer visible above the fold; full breakdown one tap away |
| 13 | Inventory count labels | Clarify "Inventory Count" vs "Inventory Audit" labels + reassurance copy (undo/no-overwrite) | keep | P2 | Real but low-traffic; rides the i18n + microcopy pass, not its own initiative | Labels distinguishable in test; no separate workstream |
| 14 | Security | `/ingest` declared without `AuthGuard`; `/marketplaces` registered twice | defer | — | A bug, not a redesign item; route to engineering bug queue, out of design loop | AuthGuard added; duplicate route removed (tracked outside this doc) |
| 15 | PO ingest flow | Diego's "one blessed novice PO path, hide the rest" | defer | P2 | Power-user machinery a novice rarely touches week one; don't reshape Sofía's flow for an absent novice | Revisit after core loops ship; lead entry with AI drag-drop, leave power path intact |

---

## 3. Scope for the first redesign (ordered, iterative-realistic)

The first loop establishes the foundation and the highest-traffic journeys both personas hit every session. It deliberately defers PO ingest, marketing, payments deep-dive, inventory count, and admin — those render "for free" through the design system later and aren't daily-money critical.

1. **Design-system foundation (P0, #3)** — M3 tokens, Leverage Indigo + Cockpit Dark, Inter + display face, semantic chips, dense-table density, money pipe with tabular numerals, pivot-wedge logo/PWA icon. Everything downstream renders through this; build it first.
2. **es-MX completeness + MXN money (P0, #1 + #2)** — worst offenders first (`quick-post-dialog`, `ai-tab`), then login / product-list / product-form / scanner / expense-dialog / po-ingest literals; standardize MXN formatting via the new money pipe. Pairs naturally with #1 because the brand copy ("tú" voice) lands at the same time.
3. **Global shell + nav (P1, #4)** — restyle header/sidenav on the new tokens; promote daily-money items + auto-expand active group. First surface users see; sets the navigational frame for everything else.
4. **Dashboard, maturity-gated (P1, #5)** — first-run vs cockpit states on the new system; add Q&A-over-SLA + transfers-to-receive cards. The default landing route and the screen where the persona conflict is resolved.
5. **Onboarding + AI activation (P1, #6 + #8)** — focused first-run flow with starting-quantity, AI-key step in the checklist, inline "activar IA" prompts. The novice's make-or-break path and the AI pillar's discovery moment.
6. **Highest-traffic daily journeys on the new system (P1, #7 + #9):** Buyer Q&A (dashboard card + in-app AI answering + nav reconcile) and the Stock-transfer push-to-ML loop (outcome naming + inline reauth chip). These are Sofía's core daily loops and Diego's most-feared/most-relevant flows.

Loop 2+ (out of first scope): product-form deep cleanup (#10), jargon/microcopy pass (#11), order/payments headline (#12), inventory-count labels (#13), then PO ingest, marketing, payments, admin re-skins riding the established design system.

**Out of the design loop entirely:** `/ingest` AuthGuard + duplicate `/marketplaces` route (#14) → engineering bug queue.
