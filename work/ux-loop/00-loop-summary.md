# UX Improvement Loop — Summary

_Multi-agent UX loop run 2026-05-31. Goal: make Fulcrum easy to use, modern,
learnable, performant, with an ownable brand identity._

## What ran

1. **Pending `work/` tasks — verified & closed.** The redesign build-review's
   open items were already resolved in committed code: `/ingest` now has
   `AuthGuard`, the duplicate `/marketplaces` route is gone, and the
   QuickPostDialog specs pass. Full frontend suite green (130 files / 774
   tests) at start of loop.
2. **Market researcher subagent** → `market-research.md`. Verdict: "Obsidian &
   Chile" (dark + chile-red `#FF4D2E`) genuinely stands apart in a market of
   light blue/yellow brands, but risks looking like generic dark-dev-SaaS.
   Cheap differentiators: warm the neutral greys, separate the brand-red from
   loss-red, route AI to warm gold (not red), add signature "honest MXN number"
   + pivot-wedge sync moment, keep self-hosted fonts + skeletons for speed.
3. **Two persona subagents** (novice "Diego" + power "Sofía") →
   `user-novice.md`, `user-power.md`. **Both independently rated the same P0:**
   the Buyer Q&A page (`/reports/qa`) was a read-only SLA report with no way to
   answer questions in-app — the core daily, SLA-bound ML workflow was a dead
   end. (Also noted: the `work/redesign/shots/` screenshots are stale tooling
   artifacts, not product state.)
4. **PM subagent** → `pm-critique.md`. Picked **in-app Buyer Q&A answering** as
   the one feature this loop; corrected a feasibility claim (`ai_service.py` is
   embeddings-only → no AI-draft, manual answering only); ranked the next
   backlog.
5. **Engineer subagent** → implemented it full-stack with tests.
6. **Re-validation loop** — both personas re-walked the journey on the new
   code: **✅ fixed & solid** (real ML `POST /answers`, in-place row update,
   inline Reconnect on expired token, plain es-MX copy).

## Feature shipped this loop: in-app Buyer Q&A answering

- **Backend:** `MercadoLibreConnector.post_answer()` → ML `POST /answers`;
  `questions_service.answer_question()` (resolves the credential by
  `credential_id`, posts, persists `answer_text`/`answered_at`/`status`,
  idempotent, maps reauth/not-found/empty); `POST
  /api/v1/reports/questions/{id}/answer` (400/404/409/502 mapping, `409
  {code:"needs_reauthorization"}` for the UI).
- **Frontend:** per-row "Responder" composer on `qa-page` (chile-red "Enviar
  respuesta" CTA), in-place row + live counter update (no reload), inline
  Reconnect banner on 409; SLA jargon → plain es-MX ("Tiempo de respuesta",
  "Tarde"). es-MX + en keys under `dashboard.qaPage.*`.
- **Tests:** backend 12 (docker stack), frontend +7 (full suite 781 green),
  i18n + theme-contrast guards pass.

## Next-loop backlog (ranked, from PM + re-validation)

1. **Profit / "¿gané o perdí?" summary** (M) — novice has no plain
   make-or-lose-money view; margins exist only deep in order-detail.
2. **Inline ML reauth on Ship→push-to-ML** (S) — reuse the sync-listings
   Reconnect banner pattern (now also used by Q&A) on the stock-push path.
3. **Orders list: pagination + search + MoneyPipe + margin column** (M) —
   currently bare `$`, no paging, no margin.
4. **Low-stock "Crear OC" vs "Enviar a ML Full" disambiguation** (S).
5. **Q&A workflow polish at volume** (P1/P2): keyboard submit (Ctrl/Cmd+Enter),
   just-answered row lingering under the "unanswered" filter (list/counter
   drift), map `already_answered` to a specific "recargar" message, wire (or
   remove) the orphaned `answerSuccess` toast key, product name instead of raw
   `item_id` in the "Artículo" column.
6. **Brand signature moments** (S–M): warm-neutral token nudge, AI→gold,
   pivot-wedge sync/success animation, oversized tabular MXN hero numbers.
