## Frontend Testing

- [x] ~~`UserBulkImportDialogComponent` tests disabled due to 120s timeout~~
      **DONE 2026-05-17** in commit `1178b8d`. Root cause was happy-dom
      vs Angular Material — switching `vitest.config.ts` env to `jsdom`
      unstuck the bootstrap. 12 tests in
      `user-bulk-import-dialog.spec.ts` now run + pass.
- [ ] **5 product-form spec files intentionally skipped** —
      `product-form-create.spec.ts`, `product-form-edit.spec.ts`,
      `product-form-error-handling.spec.ts`,
      `product-form-advanced-error-handling.spec.ts`,
      `products.spec.ts`. Each carries an explicit `describe.skip` with
      a comment citing a real test-design bug (form-group control
      mismatches, incomplete dialog mocks, async-mock instability) —
      not flaky, deliberately disabled pending a test refactor. See
      `1178b8d` commit message for the full triage. Unblocking
      these would require rewriting the test setup, not a config tweak.
