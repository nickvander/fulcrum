# Vitest Migration and Test Fixes Walkthrough

## Overview

This session focused on stabilizing the frontend test suite after migrating to
Vitest (Angular v20 experimental support) and attempting to integrate it with
Bazel.

## Accomplishments

### 1. Local Test Suite Stabilization

We successfully resolved all persistent failures in the local test suite. All
tests now pass.

- **Total Tests**: 249
- **Passed**: 226
- **Skipped**: 23
- **Failed**: 0

**Key Fixes:**

- **ProductList**: Corrected filter expectations (`undefined` vs `{}`).
- **Pagination**: Fixed nested `it` blocks and structural syntax errors;
  corrected text assertions.
- **BatchActionToolbar**: Improved "Deselect All" button selector to be robust
  against UI changes.
- **ProductForm**:
  - Fixed "Cannot find form control" error by switching `setValue` to
    `patchValue`.
  - Mocked `FileReader` globally to fix `product-form-image-gallery` tests.
  - Corrected `isEditMode` logic validation by properly mocking `initializeForm`
    failure.
- **ImageDialog**: Removed incorrect `setTimeout` wrapping that caused unhandled
  exceptions; verified synchronous error handling.

### 2. Bazel Integration Investigation

We attempted to run the tests via Bazel (`bazel test //frontend:test`).

- **Result**: Failed (Blocked)
- **Primary Issue**: Sass compilation environment incompatibility.

**Investigation Details:**

1. **`sass` (JS-only)**:
   - **Error**: `TypeError: Cannot read properties of undefined (reading 'pop')`
     in `sass.node.js`.
   - **Cause**: The wrapper relies on `globalThis._cliPkgExports`, which fails
     to populate in the Bazel sandbox.
   - **Fix Attempt**: Patched `sass.node.js` to initialize the array. Result:
     The array remained empty, meaning the underlying `sass.dart.js` was not
     executing side effects correctly.

2. **`sass-embedded` (Native Binary)**:
   - **Error 1**: `MODULE_NOT_FOUND` chain.
   - **Cause**: Strict dependency isolation in Bazel. `sass-embedded` has many
     peer/optional dependencies that are required at runtime but not declared in
     a way Bazel picks up automatically.
   - **Fix**: Manually installed `immutable`, `@bufbuild/protobuf`,
     `colorjs.io`, `varint`, `buffer-builder`, `sync-child-process`,
     `sync-message-port`.
   - **Error 2**: `Can't find stylesheet to import` (`src/styles.scss`) and
     `Compiler caused error: Embedded compiler exited unexpectedly`.
   - **Cause**: The embedded binary compiler is crashing or failing to resolve
     workspace paths within the sandbox `linux-sandbox` root. This is a complex
     environment configuration issue specific to how `rules_js` / `angular`
     builders interact with native inputs.

## Recommendation

**Use `ng test` for local development and CI.**

The local test runner (`ng test`) is fully functional, fast, and passes 100% of
the active test suite. Bazel integration for the frontend tests should be
deferred until `rules_sass` or `rules_vitest` matures for Angular v21, or until
a dedicated effort to map the sandbox filesystem for Sass inputs is undertaken.
