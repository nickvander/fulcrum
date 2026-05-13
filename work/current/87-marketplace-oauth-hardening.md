# 87: Marketplace OAuth Token Refresh Hardening

## Goal

Once Slice 2 of the marketplace allocation workflow wired up real
MercadoLibre Full inbound shipment + listing-quantity sync calls, the
weakest link became the OAuth token lifecycle. A stale or invalidated
refresh token would surface as a generic "(failed)" line in the listing
sync panel — operators wouldn't know they needed to reconnect the
account. This slice closes that gap.

## What landed

Commit `9541ccb` — "Harden marketplace OAuth token refresh".

### Backend

- New columns on `marketplace_credentials`:
  - `needs_reauthorization` (bool, default false)
  - `last_refresh_error` (string, nullable)
  - Alembic migration `c3d4e5f6a7b8`.
- `MarketplaceService.get_valid_access_token`:
  - Pre-refresh buffer widened from 1 minute to **5 minutes** (constant
    `TOKEN_PRE_REFRESH_BUFFER`) so a slow refresh round-trip can't push
    us past expiry mid-call.
  - New typed exception `ReauthorizationRequiredError(credential_id,
    marketplace_name, reason)` raised whenever the credential cannot be
    refreshed (no refresh token, refresh API error, response missing
    access token, or already marked).
  - On refresh failure, the credential row is marked
    `needs_reauthorization=True` with the captured error so the next
    call short-circuits without spamming the provider.
  - Successful refresh always clears both flags.
- New `MarketplaceService.force_refresh_access_token(credential_id)`
  entry point for the future "API returned 401 even though we thought
  the token was valid" recovery path.
- `StockTransferService.sync_marketplace_listings`:
  - Catches `ReauthorizationRequiredError`, short-circuits the
    connector loop entirely, and surfaces
    `{needs_reauthorization, reauthorization_reason, marketplace}` on
    the response plus per-listing
    `error="needs_reauthorization"` entries with their `sync_status`
    set to `"ERROR"` and a clear `error_message`.

### Frontend

- `StockTransferService` TS interface picks up the new summary fields.
- `StockTransferDetailComponent`:
  - Renders an orange-bordered banner ("MercadoLibre needs
    re-authorization before listings can sync") with the failure
    reason and a deep-link to `/marketplaces` so the operator can
    reconnect in one click.
  - Snackbar copy reflects the reauth case ("Reauthorize ML before
    syncing").
- Full en + es-MX translations for the new strings.

## Verification

- 8 new backend tests in `tests/services/test_marketplace_service_reauth.py`
  covering every branch:
  - within-buffer no-refresh
  - in-window auto-refresh
  - refresh failure marks credential + raises typed error
  - already-marked credential short-circuits
  - successful refresh clears the flag
  - missing access-token in response
  - force-refresh entry point
- 1 new test in `test_stock_transfer_marketplace.py` verifying
  `sync_marketplace_listings` short-circuits cleanly with the banner
  data on the response.
- 1 new frontend vitest spec for the reauth-state branch on the detail
  component.
- `ng build` green.
- Manually verified the banner renders in real Chromium against a
  stale-credential seed (saw "MercadoLibre needs re-authorization
  before listings can sync" with reason "invalid_grant (test
  fixture)").

## Open follow-ups

- Wire the `force_refresh_access_token()` entry point into a
  401-retry decorator on connector calls — currently unused.
- Surface `needs_reauthorization` on the marketplace cards / list page
  too (today only the stock-transfer sync panel shows it).
