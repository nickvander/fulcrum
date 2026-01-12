# MVP Launch Plan: Fulcrum

Based on the thorough audit of the project status (`Phase 4` in progress), the existing `00-project-plan.md`, and the codebase structure, here are the **5 Key Milestones** to launch a competitive Minimum Viable Product (MVP).

Recent progress has solidified the Core Foundation (Phase 1), PWA Interface (Phase 2), and Ingestion (Phase 3). The path to launch focuses on closing the loop between "Stock In" and "Sales Out".

## Milestone 1: Complete AI Content & Media Suite (Phase 4)
**Status:** ✅ *Complete*
**Focus:** Finalize the tools needed to market products effectively.
- **Goals:**
  - Complete the `MediaManagerComponent` for handling product assets.
  - Finalize AI image and description generation endpoints.
  - **Why:** High-quality content is a prerequisite for successful marketplace listings (Milestone 3).

## Milestone 2: Intelligent Purchase Order & Receiving (Phase 5)
**Status:** ✅ *Complete*
**Focus:** Solve the "Stock In" problem to fuel inventory.
- **Goals:**
  - Implement AI parsing for supplier Invoices/POs to automate data entry.
  - Build the transactional "Receiving" workflow to accurately update stock levels.
  - **Why:** You cannot sell what you cannot accurately track. This automates the inventory supply chain.

## Milestone 3: Marketplace Integration Engine (Phase 6)
**Status:** 🔄 *In Progress*
**Focus:** Enable multi-channel sales (The core "Fulcrum" value).
- **Goals:**
  - Develop the `MarketplaceConnector` abstraction layer.
  - Implement **MercadoLibre** integration (Priority 1) for syncing stock and orders.
  - Implement **Amazon** integration (Priority 2) if schedule permits, or defer to post-launch.
  - **Why:** This is the primary revenue driver and the main differentiator of the platform.

## Milestone 4: Hybrid E-commerce Storefront (Phase 7)
**Status:** *Pending*
**Focus:** Establish a direct-to-consumer brand channel.
- **Goals:**
  - Build the public-facing, SEO-optimized Angular storefront.
  - Integrate **Stripe** for secure on-site checkout.
  - Implement "Also available at" links for marketplace redirection.
  - **Why:** Provides higher margin sales and brand ownership while leveraging marketplace traffic.

## Milestone 5: Production Hardening & Launch Prep
**Status:** *Pending*
**Focus:** Ensure stability, visibility, and trust.
- **Goals:**
  - **Analytics (Phase 8 Lite):** Implement basic "Sales by Channel" reporting to verify business logic.
  - **E2E Testing:** Verify the Critical Path: `Scan` -> `Stock` -> `List` -> `Sell` -> `Ship`.
  - **Deployment:** Finalize Docker production config and CI/CD pipelines.
  - **Why:** A buggy financial/inventory system is fatal. Stability is paramount for launch.

---
**Recommendation:** Proceed immediately to finish Milestone 1, then confirm the technical design for Milestone 2 (PO Parsing).
