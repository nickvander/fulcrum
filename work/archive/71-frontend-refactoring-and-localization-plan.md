# Phase 11: Frontend Refactoring & Full Localization

## Goal

Make the Fulcrum frontend more **modular, organized, and maintainable** while
adding **complete localization support** for English and Spanish (Mexico). This
involves refactoring large components, consolidating shared code, expanding
Transloco translations to cover the entire UI, and adding a language selector in
Settings.

---

## User Review Required

> [!IMPORTANT] **Scope Decision**: This plan covers a comprehensive refactoring.
> Given the scope, we can prioritize work in phases:
>
> - **Phase A**: Localization infrastructure + language selector (quick win)
> - **Phase B**: Full UI translation (systematic, module-by-module)
> - **Phase C**: Code modularity refactoring (component splitting, shared code)

> [!NOTE] **Translation Approach**: We will translate all user-facing strings
> but keep code-level comments, console logs, and developer-facing text in
> English.

---

## Part 1: Localization Infrastructure & Language Selector

### 1.1 Language Selector in Settings

#### [MODIFY] [settings.ts](file:///home/nickvander/fulcrum/frontend/src/app/settings/components/settings/settings.ts)

- Inject `TranslocoService` for language switching
- Add `currentLang` property bound to Transloco's active language
- Add `changeLang(lang: string)` method

#### [MODIFY] [settings.html](file:///home/nickvander/fulcrum/frontend/src/app/settings/components/settings/settings.html)

- Add Language selector dropdown in General tab (after Theme selector)
- Options: "English" and "Español (México)"

### 1.2 Persist Language Preference

#### [MODIFY] [settings.service.ts](file:///home/nickvander/fulcrum/frontend/src/app/core/services/settings.service.ts)

- Add `language` field to settings model
- Persist language preference to localStorage
- Load and apply language on app startup

---

## Part 2: Full UI Translation

### 2.1 Expand Translation Files

#### [MODIFY] [en.json](file:///home/nickvander/fulcrum/frontend/src/assets/i18n/en.json)

Expand to include all UI text organized by module:

```json
{
  "common": {
    /* buttons, actions */
  },
  "nav": {
    /* navigation labels */
  },
  "auth": {
    /* login, password screens */
  },
  "dashboard": {
    /* dashboard widgets */
  },
  "products": {
    /* product list, form, dialogs */
  },
  "suppliers": {
    /* supplier management, POs */
  },
  "expenses": {
    /* expense tracking */
  },
  "marketing": {
    /* campaigns, posts */
  },
  "marketplaces": {
    /* marketplace integration */
  },
  "users": {
    /* user management */
  },
  "settings": {
    /* all settings tabs */
  }
}
```

#### [MODIFY] [es-MX.json](file:///home/nickvander/fulcrum/frontend/src/assets/i18n/es-MX.json)

- Mirror structure of `en.json` with Spanish (Mexico) translations

### 2.2 Apply Translations to Templates

Apply `transloco` pipe and structural directives across all modules:

---

#### Core Module

- [sidenav.html](file:///home/nickvander/fulcrum/frontend/src/app/core/components/sidenav/sidenav.html)
  - Navigation labels, group titles, user section
- [header.html](file:///home/nickvander/fulcrum/frontend/src/app/core/components/header/header.html)

---

#### Settings Module

- [settings.html](file:///home/nickvander/fulcrum/frontend/src/app/settings/components/settings/settings.html)
  - Tab labels, section titles, form labels, button text, hints

---

#### Products Module

- [product-list.html](file:///home/nickvander/fulcrum/frontend/src/app/products/components/product-list/product-list.html)
- [product-form.html](file:///home/nickvander/fulcrum/frontend/src/app/products/components/product-form/product-form.html)
- [product-details-dialog.component.html](file:///home/nickvander/fulcrum/frontend/src/app/products/components/product-details-dialog/product-details-dialog.component.html)
- All other product component templates

---

#### Dashboard Module

- [dashboard.component.html](file:///home/nickvander/fulcrum/frontend/src/app/dashboard/pages/dashboard/dashboard.component.html)
- Widget components

---

#### Auth Module

- [login.html](file:///home/nickvander/fulcrum/frontend/src/app/auth/components/login/login.html)
- [forgot-password.html](file:///home/nickvander/fulcrum/frontend/src/app/auth/components/forgot-password/forgot-password.component.html)

---

#### Other Modules

- Suppliers, Expenses, Marketing, Marketplaces, Users modules

---

## Part 3: Code Modularity Improvements

### 3.1 Consolidate Material Module Imports

#### [NEW] [material.module.ts](file:///home/nickvander/fulcrum/frontend/src/app/shared/material.module.ts)

Create a centralized Material imports module to reduce repetition:

```typescript
const MATERIAL_MODULES = [
  MatButtonModule,
  MatIconModule,
  MatCardModule,
  MatFormFieldModule,
  MatInputModule,
  MatSelectModule,
  MatTableModule,
  MatSortModule,
  MatPaginatorModule,
  MatDialogModule,
  MatTooltipModule,
  MatMenuModule,
  MatCheckboxModule,
  MatProgressSpinnerModule,
  // ... all commonly used Material modules
];

@NgModule({
  imports: MATERIAL_MODULES,
  exports: MATERIAL_MODULES,
})
export class MaterialModule {}
```

#### [MODIFY] [shared-module.ts](file:///home/nickvander/fulcrum/frontend/src/app/shared/shared-module.ts)

- Import and re-export `MaterialModule`
- Remove individual Material imports

---

### 3.2 Refactor Large Components

#### [REFACTOR] ProductList Component (992 lines → ~400 lines)

The `product-list.ts` component handles too many responsibilities. Split into:

1. **ProductListComponent** (core list display, ~300 lines)
2. **ProductListToolbarComponent** (search, filters, view mode toggle)
3. **ProductListActionsComponent** (batch operations, selection management)
4. **ProductListPaginationComponent** (pagination + infinite scroll logic)

#### [REFACTOR] Settings Component (374 lines → modular tabs)

Consider splitting each settings tab into its own component:

- `GeneralSettingsComponent`
- `IntegrationSettingsComponent`
- `MarketingSettingsComponent`
- `InventorySettingsComponent`
- `DataManagementComponent`

---

### 3.3 Extract Reusable UI Patterns

#### [NEW] [empty-state.component.ts](file:///home/nickvander/fulcrum/frontend/src/app/shared/components/empty-state/empty-state.component.ts)

Create reusable empty state component used across lists.

#### [NEW] [loading-spinner.component.ts](file:///home/nickvander/fulcrum/frontend/src/app/shared/components/loading-spinner/loading-spinner.component.ts)

Standardize loading indicators.

---

## Implementation Priority

| Phase | Focus                              | Effort   |
| ----- | ---------------------------------- | -------- |
| A     | Language selector + infrastructure | 2-3 hrs  |
| B     | Full UI translation                | 8-12 hrs |
| C     | Code modularity refactoring        | 6-10 hrs |

**Recommended Order**: A → B → C (localization provides immediate user value)

---

## Verification Plan

### Automated Tests

```bash
# Run all frontend tests
npm test --prefix frontend

# Verify build succeeds
npm run build --prefix frontend
```

### Manual Verification

1. **Language Selector**:
   - Navigate to Settings → General tab
   - Change language from English to Español (México)
   - Verify all visible text changes immediately
   - Refresh page → language preference persists

2. **Translation Coverage**:
   - Navigate through all major pages (Dashboard, Products, Suppliers, Settings)
   - Verify no English text appears when Spanish is selected
   - Check form labels, buttons, table headers, dialogs

3. **No Regressions**:
   - Verify all existing functionality works after refactoring
   - Test product CRUD, navigation, theme switching
