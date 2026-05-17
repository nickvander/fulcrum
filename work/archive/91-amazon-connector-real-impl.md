# 91: Real implementation for AmazonConnector.fetch_all_listings()

> **STATUS: ✅ COMPLETE as of 2026-05-17.** `AmazonConnector.fetch_all_listings()`
> now hits the SP-API `GET /listings/2021-08-01/items/{sellerId}` endpoint
> with Mexico (`A1AM78C64UM0Y8`) as the marketplace, paginates via
> `pagination.nextToken`, and falls back to a stub when the token is
> missing or `STUB-`-prefixed (matching the publish_listing convention
> from `dce6ed9`).

## What landed

`backend/src/services/marketplaces/amazon.py`:

- Added `MEXICO_MARKETPLACE_ID = "A1AM78C64UM0Y8"` module constant
  (Fulcrum's primary Amazon market).
- Rewrote `fetch_all_listings(access_token)` to:
  - Return a single stub `ListingData` early when `access_token` is
    `None` or starts with `"STUB-"` — keeps dev/test flows working
    without a live SP-API session.
  - Otherwise GET `/listings/2021-08-01/items/{settings.AMAZON_SELLER_ID}`
    with header `x-amz-access-token: <token>` and query params
    `marketplaceIds=MEXICO_MARKETPLACE_ID`, `includedData=summaries,offers`.
  - Loop on `pagination.nextToken`, passing it back as `pageToken`
    until the response omits it.
- Extracted `_parse_listing_item(item)` as a static helper. Defensively
  maps the SP-API shape to `ListingData`:
  - `external_id` = first summary's `asin`, falling back to the item's
    SKU when no summary is present
  - `sku` = item-level SKU
  - `title` = summary's `itemName`
  - `price` = first offer's `price.amount` (cast to float; `None` if
    missing or unparseable)
  - `currency` = first offer's `price.currencyCode`, defaulting to MXN
  - `status` = first entry of summary's `status[]` array, defaulting
    to `"ACTIVE"`
  - `raw_data` = the full item for downstream consumers
- The `summaries` lookup prefers the entry whose `marketplaceId`
  matches Mexico, falling back to the first one — protects against
  Amazon returning multi-marketplace data in a single response.

## Test coverage

`backend/tests/services/test_amazon_connector.py` — 5 new tests, all
pass alongside the 3 existing auth tests:

1. `test_fetch_all_listings_calls_sp_api_with_mexico_marketplace` —
   happy path, two items in a single page. Verifies URL, header, query
   params, no pageToken on first call, and that each ListingData has
   the right fields. Also covers the second-item-with-no-offers branch
   so price falls through to None without crashing.
2. `test_fetch_all_listings_paginates_via_next_token` — two-page
   response where page 1 returns nextToken and page 2 returns empty.
   Asserts the second request includes `pageToken=TOKEN-PAGE-2` and
   the returned list concatenates both pages.
3. `test_fetch_all_listings_returns_stub_without_token` — `None`
   token → one stub listing, zero HTTP calls.
4. `test_fetch_all_listings_returns_stub_for_stub_prefixed_token` —
   same for a `STUB-`-prefixed token.
5. `test_fetch_all_listings_skips_no_offers_gracefully` — a listing
   with empty summaries and empty offers parses to a minimal
   ListingData with sensible defaults (external_id falls back to sku,
   status defaults to ACTIVE).

Total backend tests: 331 passing (was 326 before this change).

## Open follow-ups (still out of scope)

- **Real SP-API integration tests** (live API, gated on env vars).
  The marker `@pytest.mark.integration_amazon` is already declared in
  `pytest.ini`; no live test was added in this slice.
- **Refresh-token plumbing.** The connector receives an
  `access_token` argument; it does not call `refresh_token()` on
  expiry. `MarketplaceService.get_valid_access_token` (hardened in
  `9541ccb`) handles the refresh side, so callers go through that. If
  a 401 lands inside the loop, the call propagates the error rather
  than self-healing — same behaviour as the existing
  `sync_inventory` / `publish_listing` paths.
- **Real `publish_listing` / `update_inventory` / `sync_price`.**
  The other Amazon connector methods are still partial stubs that
  return success without parsing the response. Same migration pattern
  applies; not done in this slice.
- **Non-MX marketplaces.** Hard-codes Mexico. If Fulcrum ever needs
  US/EU sellers, lift `MEXICO_MARKETPLACE_ID` into either a per-
  credential setting or a per-call argument.
