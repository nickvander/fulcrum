# 87: Marketplace OAuth Token Refresh Hardening

> **STATUS: ✅ COMPLETE.** Initial slice landed in `9541ccb`; the two
> open follow-ups identified at the time are now done. Moving to
> `work/archive/`.

## Goal

Once Slice 2 of the marketplace allocation workflow wired up real
MercadoLibre Full inbound shipment + listing-quantity sync calls, the
weakest link became the OAuth token lifecycle. A stale or invalidated
refresh token would surface as a generic "(failed)" line in the listing
sync panel — operators wouldn't know they needed to reconnect the
account. This slice closes that gap.

## What landed (initial slice — commit `9541ccb`)

### Backend

- New columns on `marketplace_credentials`:
  - `needs_reauthorization` (bool, default false)
  - `last_refresh_error` (string, nullable)
  - Alembic migration `c3d4e5f6a7b8`.
- `MarketplaceService.get_valid_access_token`:
  - Pre-refresh buffer widened from 1 minute to **5 minutes**.
  - New typed `ReauthorizationRequiredError` raised when refresh fails.
  - On refresh failure, credential row is marked
    `needs_reauthorization=True` with the captured error.
  - Successful refresh clears both flags.
- `MarketplaceService.force_refresh_access_token(credential_id)` entry
  point added.
- `StockTransferService.sync_marketplace_listings` catches
  `ReauthorizationRequiredError`, short-circuits, and surfaces
  `{needs_reauthorization, reauthorization_reason, marketplace}` on
  the response.

### Frontend

- `StockTransferDetailComponent` renders an orange-bordered banner
  with the reason + deep-link to `/marketplaces`.
- Full en + es-MX translations.

8 backend tests in `test_marketplace_service_reauth.py` + 1
`sync_marketplace_listings` short-circuit test + 1 frontend vitest
spec covered every branch.

## Follow-ups closed this session (2026-05-17)

### 1. `force_refresh_access_token()` wired into a 401-retry helper

New `MarketplaceService.call_with_401_retry(db, credential_id, fn)`
helper centralizes recovery from a stale-token 401:

1. Resolve a valid token via `get_valid_access_token`.
2. Invoke `await fn(token)`.
3. If `fn` raises `httpx.HTTPStatusError` with status 401 → force-
   refresh the credential → retry `fn` once with the new token.
4. If the retry also 401s, or `fn` raises any non-401 error, propagate.
5. If `get_valid_access_token` raises `ReauthorizationRequiredError`
   itself, propagate without calling `fn`.

Why: local expiry metadata can disagree with the provider (refresh-
token rotation, manual revoke, password reset). Without this helper,
every connector method has to duplicate the retry logic.

**Adoption is intentionally incremental.** Existing call sites still
work — they just don't self-heal on a server-side invalidation. New
code adopting the helper:

```python
result = await marketplace_service.call_with_401_retry(
    db, credential_id,
    lambda token: connector.sync_inventory(ext_id, qty, access_token=token),
)
```

5 unit tests in `tests/services/test_marketplace_service_retry.py`
cover every branch.

### 2. `needs_reauthorization` surfaced on the marketplace cards

`GET /api/v1/marketplace/{id}/summary` now returns:
- `needs_reauthorization` (bool)
- `reauthorization_reason` (string, the captured `last_refresh_error`)

`MarketplaceListComponent` adds a `'reauth'` state to `tokenChipState()`
that takes precedence over expiry — a marked credential can't be
refreshed in-process, so showing "expires in 6 days" is misleading.

The card now renders:
- **Orange "Reautorizar"/"Reauthorize" chip** with a warning icon,
  matching the stock-transfer reauth banner style.
- **Tooltip** carries `reauthorization_reason` so the operator knows
  WHY the token went stale (invalid_grant / network error / revoked).
- **Action row flips**: when reauth is required, the "Sync now" button
  is replaced by a prominent "Reconectar"/"Reconnect" button that
  deep-links to `/marketplaces/settings/<name>` for one-click
  re-OAuth. The plain "Sync now" button is also auto-disabled when
  no credential is connected (regardless of reauth state).

4 new i18n keys under `marketing.*`: `needsReauth`, `reconnect`,
`needsReauthTooltip`, `needsReauthTooltipWithReason` (en + es-MX).

3 new backend tests in `tests/api/v1/test_marketplace_summary_reauth.py`
cover: healthy → flag false; marked → flag true with reason; no
credential at all → flag false with reason null (distinct from
`disconnected` state).

## Totals after this session

| Layer | Result |
| --- | --- |
| Backend | 339/0/6 (+8 from baseline of 331) |
| Frontend | 413/0/14 (no regressions) |
| i18n keys with parity | 1138 (+4) |
| Production build | clean |
