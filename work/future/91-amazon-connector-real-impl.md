# 91: Real implementation for AmazonConnector.fetch_all_listings()

The last surviving "stub still here" item from the May 2026 ranked
list. After `dce6ed9` made `MercadoLibreConnector.publish_listing`
real, the Amazon equivalent for listing fetch is the one remaining
hardcoded stub returning one fake product.

## Current state

`backend/src/services/marketplaces/amazon.py` — `fetch_all_listings()`
returns a single hardcoded `MarketplaceListing(...)` ignoring the
provided credentials. Used by:

```
backend/src/services/marketplaces/__init__.py → MarketplaceServiceRegistry
backend/src/api/v1/endpoints/marketplace_credentials.py → /sync endpoint
```

The connector class extends `BaseMarketplaceConnector` (see
`backend/src/services/marketplaces/base.py`).

## Reference implementation

`mercadolibre.py:publish_listing` (after `dce6ed9`) is the pattern.
Same pattern applies:

1. Detect missing/stub token early, return a deterministic fake
   so dev/test flows still work:
   ```python
   if not access_token or access_token.startswith("STUB-"):
       return [MarketplaceListing(sku="AMZN-STUB-1", ...)]
   ```
2. Otherwise `httpx.AsyncClient` to the real Amazon endpoint with
   bearer auth.

## Amazon-specific gotchas

- **SP-API is the modern surface.** The Selling Partner API uses
  AWS-SigV4 + LWA (Login With Amazon) refresh-token rotation, NOT
  raw OAuth bearer tokens like ML. Check what the auth flow in
  `marketplace_credentials.py` actually stores — if it's only a
  bearer token, the connector will need a refresh step.
- **Endpoint for listings**: `GET /listings/2021-08-01/items/{sellerId}`
  with `marketplaceIds` query param. Different region = different
  base URL (NA: `sellingpartnerapi-na.amazon.com`, EU, FE).
- **Paginated.** Response has `nextToken`; loop until missing.
- **MEX marketplace ID**: `A1AM78C64UM0Y8`. Hard-code or move to
  config; Fulcrum's primary market is Mexico.

## Test plan

Mirror `tests/services/test_mercadolibre_connector.py`. Four test
cases minimum:

1. `test_fetch_all_listings_calls_sp_api_with_creds` — minimal happy
   path, mock `httpx.AsyncClient.get`, assert URL + auth header +
   `marketplaceIds=A1AM78C64UM0Y8`.
2. `test_fetch_all_listings_paginates_via_next_token` — multi-page
   response.
3. `test_fetch_all_listings_returns_stub_without_token`.
4. `test_fetch_all_listings_returns_stub_for_stub_token`.

## Out of scope

- Real SP-API integration tests (live API). Mark with
  `@pytest.mark.integration_amazon` (marker already declared in
  `pytest.ini`).
- A working `publish_listing` / `update_inventory` for Amazon —
  separate connector methods, separate tickets.
