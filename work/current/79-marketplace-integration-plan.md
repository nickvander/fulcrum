# Plan: Marketplace Integration Completeness (Phase 6)

## Goal
Finalize the **Marketplace Integration Engine** (Milestone 3). While the core scaffolding (listings, sync status) exists, we need to bridge the gap between "technical connectivity" and "intelligent automation". The primary focus is enabling **AI-Assisted Listing Generation** and ensuring the synchronization logic is robust for production use.

## Current Status
*   **Milestone 1 (AI Content)**: ✅ Complete (Media Gallery + AI Description Gen).
*   **Milestone 2 (Intelligent PO)**: ✅ Complete (PO Ingest + Receiving Dialogs).
*   **Milestone 3 (Marketplace)**: ⚠️ Partial.
    *   *Implemented*: Marketplace List, Detail View, Sync Service, OAuth flow (scaffolding).
    *   *Missing*: AI Listing Description Generation, "Publish" workflow UX polish, Deep testing of Sync Logic.

## Technology Stack
*   **Backend**: FastAPI, `MarketplaceConnector` abstraction.
*   **frontend**: Angular, `ProductForm` (additions needed), `MarketplaceDetail`.
*   **AI**: Google ADK / Gemini (via existing `AiService`).

## Phased Implementation

### Phase 1: AI-Assisted Listing Generation
**Goal**: Allow users to generate marketplace-specific descriptions (e.g., "Optimize for Amazon SEO") directly from the interface.

1.  **Backend Extensions**:
    *   Verify/Implement `POST /ai/generate-listing-description` endpoint.
    *   Input: `product_id`, `marketplace_name` (target platform context).
    *   Output: Optimized Title, Description, Keywords.

2.  **Frontend UX**:
    *   Update `MarketplaceDetailComponent` or create a `ListingEditorDialog`.
    *   Add "Generate with AI" button for Listing Description.
    *   Allow reviewing/editing the generated text before "Publish/Update".

### Phase 2: Marketplace Workflow Hardening
**Goal**: Ensure the user trusts the data sync.

1.  **Sync Visualization**:
    *   Improve `MarketplaceListing` status indicators (Synced vs Dirty vs Error).
    *   Show "Last Synced" timestamp clearly.
2.  **Error Handling**:
    *   Better UI for OAuth token expiration / re-auth prompts.
    *   Clearer error messages when sync fails (e.g. "SKU not found on remote").

### Phase 3: Preparation for Storefront (Milestone 4)
**Goal**: Lay the groundwork for the Hybrid E-commerce Storefront.

1.  **Public API Review**:
    *   Ensure `GET /public/products/{id}` is ready to serve data to the storefront.
    *   Verify it includes `marketplace_links` (for "Buy on Amazon" buttons).

## Implementation Steps

### Backend
1.  **AI Endpoint**: Add `generate_marketplace_listing` to `ai_router`.
2.  **Connector Logic**: Review `MercadoLibreConnector` implementation for edge cases.

### Frontend
1.  **Listing Dialog**: Create `MarketplaceListingDialogComponent` for editing/creating listings.
2.  **AI Integration**: Wire up `AiService` to the new dialog.
3.  **Status UI**: Polish `marketplace-status.component`.

## Verification
*   **Unit Tests**: Test the new AI endpoint.
*   **Manual**: Generate a listing description for a dummy product and verify it "sounds" like it belongs on the target marketplace.
