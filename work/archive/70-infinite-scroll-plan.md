# Infinite Scroll Enhancement & Pagination Standardization

## Goal Description

Fix infinite scrolling for grid view in the Products page, integrate infinite
scroll as a user-accessible option in pagination controls, and standardize this
functionality across all list views in the application. Also update the default
pagination size from 10 to 25 items for better UX.

## User Review Required

> [!IMPORTANT] **Breaking UX Changes:**
>
> - Default pagination will change from 10 to 25 items
> - A new "Infinite Scroll" toggle will appear in pagination controls
> - When enabled, traditional paginator will be hidden

> [!NOTE] **Standard Pagination Defaults:** Industry standards typically use
> 20-25 items for desktop web applications. This balances initial load time with
> user convenience (less clicking).

## Root Cause Analysis

### Grid View Infinite Scroll Issue

The current `InfiniteScrollDirective` listens to **window scroll events** and
triggers when the user scrolls near the bottom of the page. However:

1. The grid view content is rendered inside a **scrollable container**
   (`overflow: auto`)
2. The container itself doesn't trigger window scroll events
3. The infinite scroll trigger element is placed outside the grid loop

**Solution**: Modify the directive to optionally listen to container scroll
events when a host element is specified, or ensure the grid view uses window
scrolling like list view.

## Proposed Changes

### Shared Module

#### [MODIFY] [infinite-scroll.directive.ts](file:///home/nickvander/fulcrum/frontend/src/app/products/directives/infinite-scroll.directive.ts)

- Move directive from `products/directives` to `shared/directives` for reuse
- Add support for both window and container-based scrolling
- Add configurable threshold distance (default 200px)

#### [NEW] [index.ts](file:///home/nickvander/fulcrum/frontend/src/app/shared/directives/index.ts)

- Create barrel export for shared directives

---

### Products Module

#### [MODIFY] [product-list.html](file:///home/nickvander/fulcrum/frontend/src/app/products/components/product-list/product-list.html)

- Remove the separate "Settings Menu" for infinite scroll toggle
- Move infinite scroll toggle to the paginator area using a slide toggle
- Ensure the infinite scroll trigger works for both grid and list views
- Place the infinite scroll sentinel inside the scrollable container

#### [MODIFY] [product-list.ts](file:///home/nickvander/fulcrum/frontend/src/app/products/components/product-list/product-list.ts)

- Update default `pageSize` from 10 to 25
- Update directive import path
- Add `cdr.markForCheck()` after scroll loading completes

#### [MODIFY] [product-list.scss](file:///home/nickvander/fulcrum/frontend/src/app/products/components/product-list/product-list.scss)

- Add styles for inline infinite scroll toggle

---

### Suppliers Module

#### [MODIFY] [supplier-list.component.html](file:///home/nickvander/fulcrum/frontend/src/app/suppliers/supplier-list/supplier-list.component.html)

- Update paginator `pageSize` from 10 to 25
- Add infinite scroll toggle alongside paginator
- Import and use shared infinite scroll directive

#### [MODIFY] [supplier-list.component.ts](file:///home/nickvander/fulcrum/frontend/src/app/suppliers/supplier-list/supplier-list.component.ts)

- Add `useInfiniteScroll` state variable
- Add toggle and scroll handler methods

---

#### [MODIFY] [purchase-order-list.component.html](file:///home/nickvander/fulcrum/frontend/src/app/suppliers/purchase-orders/purchase-order-list/purchase-order-list.component.html)

- Update paginator `pageSize` from 10 to 25
- Add infinite scroll toggle alongside paginator

#### [MODIFY] [purchase-order-list.component.ts](file:///home/nickvander/fulcrum/frontend/src/app/suppliers/purchase-orders/purchase-order-list/purchase-order-list.component.ts)

- Add infinite scroll support methods

---

### Expenses Module

#### [MODIFY] [expense-list.html](file:///home/nickvander/fulcrum/frontend/src/app/expenses/components/expense-list/expense-list.html)

- Update paginator `pageSize` from 10 to 25
- Add infinite scroll toggle

#### [MODIFY] [expense-list.ts](file:///home/nickvander/fulcrum/frontend/src/app/expenses/components/expense-list/expense-list.ts)

- Add infinite scroll support

---

### Marketing Module

#### [MODIFY] [campaign-list.component.html](file:///home/nickvander/fulcrum/frontend/src/app/marketing/components/campaign-list/campaign-list.component.html)

- Update paginator configuration
- Add infinite scroll toggle

#### [MODIFY] [campaign-list.component.ts](file:///home/nickvander/fulcrum/frontend/src/app/marketing/components/campaign-list/campaign-list.component.ts)

- Add infinite scroll support

---

## Verification Plan

### Automated Tests

```bash
# Run all frontend tests
npm test --prefix frontend
```

- Ensure existing product-list tests pass
- Ensure new infinite scroll directive tests pass

### Manual Verification

1. **Products Page - Grid View:**
   - Navigate to Products, switch to Grid view
   - Enable infinite scroll
   - Scroll to bottom - verify more products load
   - Verify loading spinner appears during load

2. **Products Page - List View:**
   - Navigate to Products, switch to List view
   - Enable infinite scroll
   - Scroll to bottom - verify more products load
   - Disable infinite scroll - verify paginator returns

3. **Other Pages (Suppliers, POs, Expenses, Marketing):**
   - Navigate to each page
   - Verify default page size is 25
   - Enable infinite scroll toggle if added
   - Verify functionality

4. **Persist Preference (Optional Future Work):**
   - If implemented, verify toggle state persists across navigation
