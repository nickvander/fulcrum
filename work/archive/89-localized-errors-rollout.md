# 89: Localized backend errors — extend rollout to other routers

> **STATUS: ✅ COMPLETE as of 2026-05-17.** All routers in
> `backend/src/api/v1/endpoints/` that raise `HTTPException` have been
> migrated to `LocalizedHTTPException`. **107 raise sites across 12
> routers, 96 distinct codes** spanning 11 namespaces under
> `apiErrors.*`. See "Final state" at the bottom for the commit-by-
> commit roll-up and what's now reusable.

The infrastructure (commit history below) is end-to-end:

- Backend: `LocalizedHTTPException(status_code, code, params, detail)` in
  `backend/src/core/errors.py` + exception handler wired in `src/main.py`.
- Frontend: `HttpErrorInterceptor` calls `translateApiError` which
  resolves `body.code` via transloco with `body.params`. Falls back to
  `body.detail` for any endpoint that still raises plain HTTPException
  (or for FastAPI default 422 / 405 responses).
- i18n: `frontend/src/assets/i18n/{en,es-MX}.json` namespace tree under
  `apiErrors.*`. Parity enforced by `check_i18n_consistency.py` in the
  pre-commit hook.

## Mechanical pattern (still applies for new routes you add)

```python
raise LocalizedHTTPException(
    status_code=N,
    code="apiErrors.<resource>.<situation>",
    params={"<relevant_id>": value},
    detail="X",  # keep English as the log-friendly fallback
)
```

Add the `code` key under `apiErrors.<resource>` in BOTH
`frontend/src/assets/i18n/en.json` and `es-MX.json`. The i18n
validator in `check_i18n_consistency.py` will block the commit if you
forget one side.

## How to verify a new migration

Wire-shape unit test template in `backend/tests/core/test_errors.py`;
per-router round-trip examples in any of the
`tests/api/v1/test_*_localized_errors.py` files (8 of them). Assert
this shape:

```python
body = response.json()
assert body == {"detail": "...", "code": "apiErrors.X.Y", "params": {...}}
```

End-to-end check: switch locale to es-MX (kebab → Language) and hit
the failing path in the browser. The duplicate-SKU 409 in the Add
Product dialog was the reference smoke test — it still works.

## Final state — commits in landing order

| Commit | Router(s) | Sites |
| --- | --- | --- |
| `4c6c79e` | `products.py` | 16 |
| `b955e1a` | (frontend interceptor → `translateApiError` global) | — |
| `e1e749e` | (frontend inline-error fields in 5 components) | — |
| `8c91b8c` | `users.py` + `onboarding.py` | 16 |
| `97ba57d` | `marketplace_credentials.py` | 7 |
| `410382f` | `purchase_orders.py` | 46 |
| `b2dea0c` | `expenses.py`, `marketplace.py`, `bulk_users.py`, `sales_orders.py`, `stock_transfers.py`, `settings.py`, `suppliers.py` (parallel batch via 3 sub-agents) | 22 |

**107 raise sites migrated. 0 routers with raise sites remaining.**

## No-op routers

`backend/src/api/v1/endpoints/webhooks.py` and `inventory_settings.py`
were checked and have zero `raise HTTPException` sites — nothing to
migrate.

## Namespaces that now exist

```
apiErrors.product.*          (notFound, notFoundBySku, skuExists, …)
apiErrors.user.*             (invalidCredentials, notEnoughPrivileges, notFound, …)
apiErrors.onboarding.*       (cleanupNotConfirmed, cleanupBlocked)
apiErrors.marketplaceCredentials.* (tokenExchangeFailed, unsupportedMarketplace, …)
apiErrors.purchaseOrder.*    (notFound, mustConfirmCosts, importReviewNotPending, …)
apiErrors.expense.*          (notFound, receiptNotFound, aiDisabled, …)
apiErrors.marketplace.*      (listingNotFound, importFailed, publishFailed, …)
apiErrors.bulkUsers.*        (onlyCsvAllowed, missingRequiredColumns, …)
apiErrors.salesOrder.notFound
apiErrors.stockTransfer.notFound
apiErrors.setting.unknownMarketplace
apiErrors.supplier.notFound
apiErrors.network            (interceptor — status 0)
apiErrors.unknown            (interceptor — final fallback)
```

Cross-router code reuses (intentional, not duplication): `apiErrors.user.notEnoughPrivileges`
covers every 403 across routers; `apiErrors.product.notFound` / `apiErrors.product.skuExists` are
reused inside the purchase-order import-review flow when it operates on products;
`apiErrors.marketplaceCredentials.marketplaceNotFound` is reused by `marketplace.py`.

## What's still NOT covered (out of scope for this initiative)

- **FastAPI default 422 validation errors.** Pydantic field validation
  emits `{"detail": [{"type": "value_error", "loc": [...], "msg": "..."}]}`.
  The interceptor flattens these into a single readable string and
  shows them as snackbars, but they have no stable code. Migrating
  this would require either custom Pydantic validators that throw
  `LocalizedHTTPException` directly, or a richer `translateApiError`
  branch for the array-detail shape.
- **`onboarding.demo-cleanup` 409 with `{detail: {message,
  blocked_reasons, records}}`.** Already has a code
  (`apiErrors.onboarding.cleanupBlocked`) AND preserves the nested
  detail; the dashboard component still reads `detail.blocked_reasons`
  and `detail.records` to render the inline list. No further work
  needed; documenting here as the canonical example of nested-detail
  preservation.
- **ICU plural handling** — issue #7 from `87-handoff`. Independent
  of error translation.
- **Frontend inline-error fields in components that DON'T yet call
  `translateApiError`.** A handful of consumer-level error handlers
  still set `this.error = err.error?.detail || 'fallback'` instead of
  using the helper. Lower priority since the interceptor's snackbar
  covers the user notification path; inline fields are duplicate
  reinforcement.

## Lessons learned (for the next multi-router refactor)

1. **Parallel sub-agents work** if you partition by file. Three agents
   in parallel finished 22 sites + 13 tests in ~3 minutes wall-clock
   — vs. the ~30 minutes the same work would have taken serially.
2. **Don't let parallel agents write to shared files** (here:
   `en.json` and `es-MX.json`). Have them return key suggestions in a
   structured JSON shape; merge centrally. One agent in this batch
   produced `{columns}` (Python f-string syntax) instead of
   `{{columns}}` (transloco syntax) — caught at merge time.
3. **The `LocalizedHTTPException` subclass of `HTTPException` is
   load-bearing.** Several routers had `except HTTPException as e:`
   blocks that needed to keep catching both. Don't drop the
   `HTTPException` import from `from fastapi import …` if any
   `except HTTPException` remains.
4. **Programmatic rewrites via `python3 /tmp/migrate_X.py` with
   exact-string matches beat hand-Editing** for any router with >10
   raise sites. Each pattern in the script asserts an expected match
   count so a copy-paste typo fails loudly instead of silently
   half-migrating.
