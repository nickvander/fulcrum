# Unified Testing & Stability Plan

## Goal
To consolidate and execute the remaining testing and stability work for the Fulcrum project, focusing on inventory features, product form stability, and deferred testing items.

## Scope

### 1. Inventory Feature Tests (High Priority)
**Source:** `work/future/fix-failing-inventory-feature-tests.md`

**Objective:** Resolve failing tests for stock adjustments, history tracking, and user attribution.

**Key Issues:**
- Backend logic issues (stock adjustment calculation).
- Query logic problems (finding existing inventory).
- Transaction/commit issues in tests.
- Missing frontend component tests.

**Plan:**
1.  **Debug Backend Logic:**
    -   Analyze inventory query logic.
    -   Fix test data creation.
    -   Correct inventory calculation logic.
2.  **Complete Test Implementation:**
    -   Fix existing test assertions.
    -   Add missing test coverage (confirmation workflow, history, user attribution).
    -   Implement frontend component tests (`StockAdjustmentDialog`, `StockHistoryDialog`, Product Card).
3.  **Validation:**
    -   Manual functionality testing.
    -   Integration testing.

### 2. Product Form Test Stability (Medium Priority)
**Source:** `work/future/product-form-test-stability-remaining-work.md`

**Objective:** Address timeout issues in ProductForm tests (`product-form-edit.spec.ts`, `product-form-error-handling.spec.ts`).

**Plan:**
1.  **Immediate Action:** Temporarily disable problematic tests if not already done.
2.  **Root Cause Analysis:** Investigate observable chains and `customFieldService` interactions.
3.  **Permanent Fix:** Refactor observable chains, implement proper teardown.
4.  **Verification:** Re-enable tests and ensure stability.

### 3. Deferred Testing Work (Low Priority)
**Source:** `work/future/deferred-testing-work.md`

**Objective:** Implement tests deferred during user management implementation.

**Plan:**
1.  **Frontend Component Tests:**
    -   `AccountManagementComponent` (Profile update, Avatar upload).
    -   `PasswordResetDialogComponent` (Reset flow, Validation).
    -   `UserFormComponent` (Validation, Role selection).
2.  **Backend Edge Case Tests:**
    -   Concurrency tests.
    -   Special characters handling.
    -   Transaction rollback tests.

## Execution Strategy

1.  **Phase 1: Inventory Fixes (Critical Path)**
    -   Focus on backend logic and existing failing tests.
2.  **Phase 2: Product Form Stability**
    -   Parallelize if possible, or tackle after critical inventory fixes.
3.  **Phase 3: Frontend Inventory Tests**
    -   Implement missing frontend tests for inventory.
4.  **Phase 4: Deferred Items**
    -   Pick up low priority items as time permits.
5.  **Phase 5: Regression Fixing (Current Priority)**
    -   Investigate and fix the frontend test suite hang/regression.
    -   Ensure all tests pass consistently.

## Tracking
-   **Progress:** `work/current/PROGRESS.md`
-   **Missing Items:** `work/current/MISSING_ITEMS.md`
