## Frontend Testing

- [x] ~~`UserBulkImportDialogComponent` tests disabled due to 120s timeout~~
      **DONE 2026-05-17** in commit `1178b8d`. Root cause was happy-dom
      vs Angular Material — switching `vitest.config.ts` env to `jsdom`
      unstuck the bootstrap. 12 tests in
      `user-bulk-import-dialog.spec.ts` now run + pass.
- [x] ~~5 product-form spec files intentionally skipped~~
      **DONE 2026-05-18** in commit `afb760f`. The four product-form
      specs (`product-form-create.spec.ts`, `product-form-edit.spec.ts`,
      `product-form-error-handling.spec.ts`,
      `product-form-advanced-error-handling.spec.ts`) are now running
      green. Root fixes were mostly infrastructure: missing
      `TranslocoTestingModule`, stale
      `httpMock.expectOne('/custom-fields')` calls from the
      pre-initializer-service architecture, missing
      `generateUniqueSku`/`generateBarcodeFromSku` mock methods,
      missing `queryParams` on the `ActivatedRoute` mock, and
      `setValue()` calls that listed only 12 of the 20+ form controls
      (switched to `patchValue`). One assertion against
      `notificationService.showError` was rewritten — errors flow
      through `HttpErrorInterceptor` + `translateApiError` since
      `b955e1a`. The fifth file `products.spec.ts` was deleted along
      with its dead component (`ProductsComponent` had no route, no
      external references). Frontend suite: 450 passed, 0 skipped.
