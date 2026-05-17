# 89: Localized backend errors — extend rollout to other routers

After `4c6c79e` / `b955e1a` / `e1e749e`, the frontend translates every
HTTP error globally via `HttpErrorInterceptor` → `translateApiError`.
Inline-error fields in 5 components also call the helper. The Spanish
copy fires the moment the backend returns a `{detail, code, params}`
payload.

The infrastructure works but **only `backend/src/api/v1/endpoints/products.py`
has been migrated to `LocalizedHTTPException` so far** (16 sites). Every
other router still raises plain `HTTPException(status_code=N, detail="raw English")`,
so the frontend falls back to the English `detail` even in es-MX.

## What's left

Sites still raising plain `HTTPException`:

```bash
grep -rn "raise HTTPException" backend/src/api/v1/endpoints | grep -v products.py | wc -l
```

Run that against the current tree — last count was ~60 sites across:

- `users.py` (auth errors: "Incorrect email or password", "Inactive user", token expired)
- `suppliers.py` (404, conflicts)
- `purchase_orders.py` (state machine errors: "PO already received", "Cannot delete received items")
- `sales_orders.py`
- `marketplace.py` + `marketplace_credentials.py` (OAuth flow errors are user-visible)
- `bulk_users.py` (CSV validation errors)
- `webhooks.py`
- `onboarding.py` (demo-cleanup blocked, demo-workspace already exists)
- `expenses.py`, `stock_transfers.py`, `inventory_settings.py`, `settings.py`

## Mechanical pattern

For each `raise HTTPException(status_code=N, detail="X")`:

```python
raise LocalizedHTTPException(
    status_code=N,
    code="apiErrors.<resource>.<situation>",
    params={"<relevant_id>": value},
    detail="X",  # keep English as the fallback
)
```

Then add the `code` key under `apiErrors.<resource>` in BOTH
`frontend/src/assets/i18n/en.json` and `es-MX.json`. The i18n validator
in `check_i18n_consistency.py` enforces parity.

## How to verify

Spec at `backend/tests/core/test_errors.py` is the template — assert
the wire shape:

```python
body = response.json()
assert body == {"detail": "...", "code": "apiErrors.X.Y", "params": {...}}
```

End-to-end check in the browser at `http://localhost:4200` after
switching locale to es-MX (kebab → Language → Español MX). The
duplicate-SKU 409 in the Add Product dialog is the reference example:
"Ya existe un producto con el SKU DEMO-CATALOG-CERAMIC-MUG."

## Suggested order

1. **`users.py`** — auth errors are the first thing a Mexican user
   sees, and `login/access-token` 401 ("Incorrect email or password")
   still shows raw English on the login page.
2. **`onboarding.py`** — the demo-workspace flow is on the new-user
   path; today the cleanup-blocked 409 lights a hand-translated
   fallback (`dashboard.demoCleanupBlocked`), which works, but the
   underlying error has no stable code.
3. **`marketplace_credentials.py`** — OAuth callback errors hit
   `marketplace-callback.ts` which already calls `translateApiError`.
4. **`purchase_orders.py`** — state-machine errors are
   action-blocking and frequent.

Each router is a self-contained chunk; you can land them one at a time
without ordering dependencies.

## Out of scope here

- New code paths that emit complex/nested error payloads (like the
  current `onboarding.demo-cleanup` 409 with `{detail: {message,
  blocked_reasons, records}}`). Those need a small backend redesign
  to fit the `{code, params}` shape, OR an extension to
  `translateApiError` to handle nested detail.
- ICU plural handling (issue #7 in `87-handoff`).
