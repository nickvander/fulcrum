# Fulcrum Redesign — Discovery Phase: Executive Summary

_Program lead summary for founder review. Date: 2026-05-30._

## Overview

This is the discovery output for a full visual + UX redesign of Fulcrum, our AI-first commerce operations hub for Mexican MercadoLibre (ML) Full sellers. We mapped every screen and journey from the live Angular 21 / Material code, pressure-tested it through two opposing personas (a power-seller and a first-time seller), defined a distinctive brand position that deliberately avoids both the "yellow ML clone" and the "forgettable SaaS-blue ERP" traps, and turned all of it into a build-ready design system and a foundation-first implementation plan. The headline finding: the product is **functionally strong but credibility-undermined** — a powerful operator cockpit wearing a half-finished, half-English, default-Material skin. The redesign's job is to finish the Spanish, fix the money, and give the app an ownable identity — without dumbing down the cockpit our power users switched for.

Discovery artifacts (read in order):
[00-journey-map.md](00-journey-map.md) · [01-ux-persona-sofia.md](01-ux-persona-sofia.md) · [02-ux-persona-diego.md](02-ux-persona-diego.md) · [03-market-brand-brief.md](03-market-brand-brief.md) · [04-pm-decision.md](04-pm-decision.md) · [05-design-system-and-plan.md](05-design-system-and-plan.md)

## Headline UX problems (most painful first)

**1. The app is not actually Spanish-first (P0, trust-critical).**
Both personas independently verified hardcoded English on first-run-critical screens. Whole dialogs (`quick-post-dialog`, settings `ai-tab`) have zero i18n; English literals leak into login, product-list, product-form, scanner, expense-dialog, and po-ingest; the Transloco default language is still `en`. For a Mexico-first product whose brand pillar is "native es-MX," this directly undercuts the entire positioning — and it is the cheapest, highest-confidence fix in the stack.

**2. Money shows in the wrong currency (P0, trust-critical).**
The dashboard "Total Value" card renders inventory value in **USD** (`dashboard.component.html` line 105); expense KPIs hardcode a bare `'$'`. A Mexican seller seeing dollars on the first card is a direct trust hit. Five-minute fix, no debate.

**3. The novice vs. power-user tension on density and discoverability.**
- *Novice (Diego):* the dashboard is a ~15-widget analytics cockpit on day one, mostly showing zeros; pervasive jargon (SKU, COGS, SLA, FBA, landed cost, reconciliation) with no teaching of the core "stock lives in 3 buckets, move it with transfers" mental model; the "first product" flow has no starting-quantity field, so a new product shows 0 stock until you find a buried kebab dialog.
- *Power-seller (Sofía):* daily-money tasks (Stock Transfers, Buyer Questions, Expenses) sit two taps deep inside sidenav expanders; a failed stock push (expired OAuth) fails silently with no inline reauth.
- These pull in opposite directions; the resolution is progressive disclosure keyed to account maturity, not a compromise screen.

**4. Buyer Q&A is under-served for an SLA/reputation task.**
No dashboard presence (no "X over SLA" count), no in-app answer composer, and a nav-label / route / module mismatch (Marketplaces label, `/reports/qa` route, `dashboard/pages/qa-page` component).

**5. Generic, unfinished visual identity.**
There is no Angular Material M3 theme at all — the app renders unstyled MDC defaults recolored through a ~970-line `!important` override pile; Inter is referenced but never actually loaded (Roboto is the de-facto font). It reads as "software," not as a product anyone is proud to open.

**Out of the design loop (routed to engineering bug queue):** `/ingest` declared without `AuthGuard`; `/marketplaces` route registered twice.

## Chosen brand direction

**Leverage Indigo** — a deep, confident indigo-violet lead (`#4F46E5`) with an electric-cyan AI accent (`#06B6D4`) over near-neutral surfaces, paired with a polished **Cockpit Dark** mode for AI surfaces. It owns an unexpected, premium color (the Kavak/Konfío lesson), is unmistakably *not* ML-yellow and *not* Bind/Alegra SaaS-blue, and indigo→cyan is the canonical 2025-26 "AI/automation" pairing. Identity is a **pivot-wedge mark** (a lever balancing on a fulcrum, doubling as an upward chevron). Personality: decisive, sharp/intelligent, composed under density, grounded/local (es-MX, `tú` voice), bold. _Volcán_ (warm clay-coral) is a one-map swap if the team wants overt Mexican warmth as the differentiator.

## Prioritized redesign scope (first loop, in order)

1. **Design-system foundation** (P0) — M3 token layer, Leverage Indigo + Cockpit Dark, self-hosted Inter + display + mono fonts, semantic chips, dense-table density, shared MXN money pipe with tabular numerals, pivot-wedge logo/PWA icon. Everything downstream renders through this.
2. **es-MX completeness + MXN money** (P0) — flip Transloco default to `es-MX`; convert the worst offenders (`quick-post-dialog`, `ai-tab`) then the remaining literals; fix the USD/`$` currency bugs; apply `tú` voice.
3. **Global shell + nav** (P1) — restyle header/sidenav on the new tokens; promote the 3 daily-money items and auto-expand the active group (serves Sofía) while keeping grouped IA (serves Diego).
4. **Dashboard, maturity-gated** (P1) — empty account → checklist-hero first-run mode with analytics suppressed; populated → full cockpit; add Q&A-over-SLA and transfers-to-receive cards.
5. **Onboarding + AI activation** (P1) — focused first-run flow with a starting-quantity field; pull the AI-key step into onboarding; add inline "Activar IA" prompts (hide-not-disable).
6. **Highest-traffic daily journeys** (P1) — Buyer Q&A (dashboard card + in-app AI answering + nav reconcile) and the Stock-transfer push-to-ML loop (outcome naming + inline one-tap reauth chip).

**Loop 2+ (deferred, inherits the system for free):** product-form cleanup, jargon/microcopy pass, order/payments plain-language headline, inventory-count labels, then PO ingest / marketing / payments / admin re-skins.

## Proposed brand/design tokens at a glance

| Token | Value | Role |
|---|---|---|
| Lead / brand | `#4F46E5` (indigo 600) | primary actions, active nav, logo |
| AI accent | `#06B6D4` (cyan) | AI moments, focus, chart highlights |
| Deep ink | `#1E1B4B` | dark-mode base, headers |
| Surface (light) | `#FAFAFB` app / `#FFFFFF` cards | table backgrounds |
| Surface (dark) | `#0B0F14` app / `#141A22` cards | Cockpit Dark |
| Text | `#1F2430` main / `#6B7280` muted | dense table text |
| Success / Warning / Danger | `#16A34A` / `#D97706` / `#DC2626` | semantic status chips |
| ML source chip | `#FFE600` (tiny accent only) | "came from MercadoLibre" tag |
| Display font | Space Grotesk | headings, KPI numbers, wordmark |
| Body / table font | Inter (tabular-nums on money) | UI + dense tables |
| Mono font | JetBrains Mono | SKUs, order IDs, AI traces |
| Radius / spacing | `--border-radius: 10px`; 8px base unit | sharper bold-modern feel |

_Surfaces stay near-neutral; the lead color is reserved for action and identity, never painted across regions. Mandatory: AA+ contrast, tabular numerals on every money/qty cell, layouts that absorb +20-25% Spanish string length._

## Recommended next step

Enter the **implementation loop foundation-first**, exactly as sequenced in [05-design-system-and-plan.md](05-design-system-and-plan.md) §7: land tokens + fonts → introduce the M3 Material theme → es-MX/MXN completeness → shell/nav → shared primitives, *before* any page pass. Each page then becomes composition over an inherited system. The first page passes follow journey order: Dashboard (maturity-gated) → Onboarding + AI activation → Buyer Q&A → Stock-transfer push-to-ML, each verified against longest-Spanish strings, mobile touch targets, and light/dark/mobile screenshot baselines.

**One decision needed before the loop starts:** confirm **Leverage Indigo** (recommended) vs. **Volcán** as the brand direction — it is a one-map swap but should be locked before tokens land.
