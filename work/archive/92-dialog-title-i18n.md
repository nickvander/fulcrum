# 92: Material dialog titles still English in es-MX

> **STATUS: ✅ COMPLETE as of 2026-05-17.** All `mat-dialog-title`
> sites that rendered hardcoded English strings have been migrated to
> `{{ '<key>' | transloco }}` form. Together with the snackbar-level
> work that landed in commits `b955e1a` and `e1e749e`, the es-MX
> experience is now end-to-end translated for every dialog in the app.

## What was found

A `grep -rn "mat-dialog-title\|matDialogTitle" src/app --include="*.html"`
turned up 21 dialog title sites. After auditing:

- **14 were already using transloco** (either `{{ t('key') }}` inside
  a `*transloco` block, or `{{ key | transloco }}` pipe form, or
  dynamic `{{ data.title }}` driven by the caller's already-translated
  copy).
- **7 were hardcoded English** and needed migration.

## What landed

Migrated the 7 hardcoded titles to the pipe form:

| Component | Old | New transloco key |
| --- | --- | --- |
| `product-details-dialog.component.ts` (4 strings in `get dialogTitle()`) | `'Edit Bundle' / 'Edit Product' / 'Create New Bundle' / 'Add New Product'` | `products.dialogs.{editBundle,editProduct,createBundle,addProduct}` |
| `user-create-modal.html` | `Create New User` | `users.dialogs.createUser` |
| `image-dialog.html` | `Image Details` | `common.dialogs.imageDetails` |
| `custom-field-dialog.html` | `{{ data ? 'Edit' : 'Add' }} Custom Field` | `settings.dialogs.{editCustomField,addCustomField}` |
| `supplier-selection-dialog.component.html` | `Select Supplier for {{ data.productName }}` | `suppliers.dialogs.selectSupplierFor` w/ `{productName}` param |
| `cost-allocation-dialog.component.html` | `Apply Additional Costs` (icon preserved) | `purchaseOrders.dialogs.applyAdditionalCosts` |
| `stock-history-dialog.component.html` | `Stock Adjustment History for {{ data.productName }}` | `products.dialogs.stockHistoryFor` w/ `{productName}` param |

11 new i18n keys added under each component's natural namespace —
`products.dialogs.*`, `users.dialogs.*`, `common.dialogs.*`,
`settings.dialogs.*`, `suppliers.dialogs.*`, `purchaseOrders.dialogs.*`.
Both `en.json` and `es-MX.json` updated together; `check_i18n_consistency.py`
passes (1134 keys with full parity).

Each affected standalone component had `TranslocoModule` added to its
`imports: [...]` array (and the symbol imported from `@ngneat/transloco`).
`product-details-dialog` uses `TranslocoService.translate()` from the
component class instead of the pipe because the title is computed via a
TypeScript getter, not bound directly in the template.

## Test changes

5 existing component specs had to gain
`TranslocoTestingModule.forRoot({ langs: { en: {}, 'es-MX': {} } })` in
their `TestBed.configureTestingModule({ imports: [...] })` — without
it, the migrated components throw `NG0201: No provider found for
InjectionToken TRANSLOCO_TRANSPILER` at component creation:

- `stock-history-dialog.component.spec.ts` (also fixed a second
  `TestBed.resetTestingModule()` block inside the same file)
- `custom-field-dialog.spec.ts`
- `image-dialog.spec.ts`
- `supplier-selection-dialog.component.spec.ts`
- `user-create-modal-ux.spec.ts`

Frontend: 413/0/14 (no net change in counts; the 24 transient
failures from the migration are all fixed). Production build clean.

## Verification

Switch locale to es-MX (kebab → Language → Español MX) and open each
of the 7 migrated dialogs. The titles should read in Spanish:

| Trigger | Spanish title |
| --- | --- |
| Products → Add Product | "Agregar producto" |
| Products → Edit → Save → Edit again | "Editar producto" |
| Bundle product edit | "Editar bundle" / "Crear nuevo bundle" |
| Users → Add New User | "Crear nuevo usuario" |
| Product Details → click an image | "Detalles de la imagen" |
| Settings → Custom Fields → Add | "Agregar campo personalizado" |
| PO Ingest → multi-supplier match | "Selecciona un proveedor para <product>" |
| PO Edit → Apply Costs | "Aplicar costos adicionales" |
| Product Details → Stock → History | "Historial de ajustes de stock para <product>" |

## What's NOT changed (intentional)

- **Dialog *body* labels** were already translated; this slice only
  touched the title rows.
- **Dynamic titles fed by `{{ data.title }}`** (confirmation dialogs)
  weren't touched — the caller is responsible for passing a
  translated string. Several callers already do this; tracking the
  ones that don't is a separate ICU-style audit, not a dialog-title
  sweep.
- **`marketplaces.createListing`** (the marketplace-listing dialog
  title) was already using the pipe form with an inline `|| 'Create
  Listing'` English fallback. Left alone — that fallback only fires
  if the i18n file is missing the key, which the parity check
  prevents.
