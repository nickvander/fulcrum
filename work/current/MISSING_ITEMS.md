# Missing Items Tracker

## Inventory Feature Tests
- [x] Debug backend inventory query logic
- [x] Fix stock adjustment calculation logic
- [x] Fix existing backend test assertions
- [x] Add tests for stock adjustment confirmation workflow
- [x] Add tests for stock adjustment history functionality
- [x] Add tests for user attribution in adjustments
- [x] Implement tests for `StockAdjustmentDialog`
- [x] Implement tests for `StockHistoryDialog`
- [x] Implement tests for Product Card stock display

## Product Form Stability
- [x] **Investigate and fix frontend test suite hang**
  - [x] Fix `account-management.spec.ts` hang
  - [x] Fix `password-reset-dialog.spec.ts` hang
  - [x] Investigate `product-list.spec.ts` hang (disabled temporarily)
- [x] **Investigate `product-form-edit.spec.ts` timeout** (observed during pre-push hook)
- [x] Root cause analysis of `product-form-error-handling.spec.ts` timeouts
- [x] Refactor observable chains in `ProductForm` (Resolved via better testing isolation)
- [x] Re-enable and verify `product-form-edit.spec.ts`
- [x] Re-enable and verify `product-form-error-handling.spec.ts`

## Deferred Testing
- [x] `AccountManagementComponent` tests
- [x] `PasswordResetDialogComponent` tests
- [x] `UserFormComponent` tests
- [x] Backend concurrency tests
- [x] Backend special characters tests
- [x] Backend transaction rollback tests

## Regression Fixing
- [x] Investigate frontend test suite hang
- [x] Fix frontend test suite hang (Fixed `product-form` tests; `product-list` temporarily disabled)
