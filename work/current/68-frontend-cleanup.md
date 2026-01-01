# Frontend Cleanup and Standardization Plan

## Goal Description
Standardize frontend codebase by ensuring clean separation of HTML/SCSS, implementing a consistent design system (SCSS variables) that supports Dark Mode, and unifying the UI/UX for Users, Purchase Orders, and Expenses pages to match the polished Products interface.

## User Review Required
> [!IMPORTANT]
> This plan involves significant UI changes to "Users", "Purchase Orders", and "Expenses" pages to match the "Products" page style.
> - **Buttons**: Top-level actions will be converted to compact `mat-mini-fab` buttons in the header.
> - **Filters**: Filter clearing logic will be standardized.
> - **Theme**: The existing "Light Mode" toggle in Settings will be connected to a new real-time theme switcher in `AppComponent`.

## Proposed Changes

### Global Styles & Theme
#### [MODIFY] [variables.scss](file:///home/nickvander/fulcrum/frontend/src/theme/variables.scss)
- Define a `.dark-theme` mixin or class that overrides CSS variables.
- Ensure all main colors (backgrounds, text, borders) have CSS variable definitions.

#### [MODIFY] [styles.scss](file:///home/nickvander/fulcrum/frontend/src/styles.scss)
- Replace any remaining hardcoded hex values with CSS variables from `variables.scss`.

#### [MODIFY] [app.component.ts](file:///home/nickvander/fulcrum/frontend/src/app/app.component.ts)
- Subscribe to `SettingsService.settings$`.
- Apply `.dark-theme` class to `document.body` or `app-root` based on the `theme` setting ('light' | 'dark').

#### [MODIFY] [sidenav.html](file:///home/nickvander/fulcrum/frontend/src/app/core/components/sidenav/sidenav.html)
- Redesign logout button to be sleek, modern, and expressive. Avoid large square boxy look.
- Use `mat-stroked-button` or a custom sleek equivalent with a specialized logout icon and hover effect.

### Users Module
#### [MODIFY] [user-list.html](file:///home/nickvander/fulcrum/frontend/src/app/users/components/user-list/user-list.html)
- Update header buttons to `mat-mini-fab` style.
- Standardize filter clearing to use `resetFilters()` pattern.

#### [MODIFY] [user-list.ts](file:///home/nickvander/fulcrum/frontend/src/app/users/components/user-list/user-list.ts)
- Implement `resetFilters()` method if missing.

#### [MODIFY] [audit-log-list.html](file:///home/nickvander/fulcrum/frontend/src/app/users/components/audit-log-list/audit-log-list.html)
- Update table structure and styling to match `change-log-dialog` (chips for source, standardized table headers/cells).

#### [MODIFY] [audit-log-list.scss](file:///home/nickvander/fulcrum/frontend/src/app/users/components/audit-log-list/audit-log-list.scss)
- Adopt styles from `change-log-dialog.scss`.

### Purchase Orders & Expenses
#### [MODIFY] [purchase-order-list.component.html](file:///home/nickvander/fulcrum/frontend/src/app/suppliers/purchase-orders/purchase-order-list/purchase-order-list.component.html)
- Update header action buttons to `mat-mini-fab`.

#### [MODIFY] [expense-list.html](file:///home/nickvander/fulcrum/frontend/src/app/expenses/components/expense-list/expense-list.html)
- Update header action buttons to `mat-mini-fab`.

## Verification Plan

### Automated Tests
- Run frontend tests to ensure no regressions in component rendering.
```bash
npm test --prefix frontend
```

### Manual Verification
- **Visual Inspection**:
    - **Dark Mode**: Go to Settings -> General -> Theme. Switch to "Dark Mode". Verify application background and text colors invert appropriately.
    - **Users**: Verify header buttons match Products page (compact). Verify Audit Logs look like "Change Log".
    - **PO/Expenses**: Verify header buttons are compact.
