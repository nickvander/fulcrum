# 92: Material dialog titles still English in es-MX

Verified live on 2026-05-17 in the browser at es-MX: the Add Product
dialog body is fully translated ("Detalles Básicos", "Nombre del
Producto", "Cancelar", "Guardar"), but the header **"Add New Product"**
stays English. Same pattern likely affects every `MatDialog` in the app
whose title is set in the template as a literal string.

## Concrete site

`frontend/src/app/products/components/product-form/product-form.html`
— the `<h2 mat-dialog-title>` (or equivalent) reads `Add New Product`
as a hardcoded string instead of `{{ 'products.dialogs.addNew' |
transloco }}`.

## How to find all of them

```bash
cd frontend
grep -rn "mat-dialog-title\|matDialogTitle" src/app --include="*.html" \
  | xargs -I{} sh -c 'echo "=== {} ==="; head -5 "{}"' 2>/dev/null
```

Expect ~15-20 hits across products, suppliers, marketplaces, stock
transfers, marketing. Each is a one-line template change + one new
i18n key (in both `en.json` and `es-MX.json`).

## Pattern

Replace:

```html
<h2 mat-dialog-title>Add New Product</h2>
```

with:

```html
<h2 mat-dialog-title>{{ 'products.dialogs.addNew' | transloco }}</h2>
```

And add to both i18n files:

```json
"products": {
  "dialogs": {
    "addNew": "Add New Product"  // or "Agregar Producto Nuevo" in es-MX
  }
}
```

## How to verify

Run `python3 check_i18n_consistency.py frontend/src/assets/i18n/en.json
frontend/src/assets/i18n/es-MX.json` after each batch — the pre-commit
hook will block a partial migration that lands keys in one file but
not the other.

Live verify in browser: switch to es-MX, open each dialog, confirm
header reads Spanish. Use Claude in Chrome with `find` tool to
batch-check dialog titles by query.

## Adjacent cleanup

While doing this, watch for dialog buttons that hardcode "Cancel" /
"Save" instead of using `common.cancel` / `common.save`. Should be
rare since the duplicate-SKU walkthrough already showed "Cancelar /
Guardar" working — but worth a sweep.

## Why this matters

A Mexican user sees "Detalles Básicos / Nombre del Producto / Cancelar
/ Guardar / **Add New Product**" — the mixed-language header undercuts
the localization story. Low effort, high cosmetic value.
