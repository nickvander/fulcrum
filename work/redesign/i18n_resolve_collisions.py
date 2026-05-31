#!/usr/bin/env python3
"""Resolve flat-key-as-namespace collisions before merging agent keys.

Several existing keys are flat strings that the localization agents also want to use
as namespaces (e.g. products.productList = "Product List" + products.productList.emptyTitle).
For each, move the original flat value to a subkey (default '.label'), delete the flat key
so an object can live there, and rewrite the few code references t('X')/'X'|transloco.
"""
import json
import os

BASE = "/home/nickvander/fulcrum"
EN = os.path.join(BASE, "frontend/src/assets/i18n/en.json")
ES = os.path.join(BASE, "frontend/src/assets/i18n/es-MX.json")
APP = os.path.join(BASE, "frontend/src/app")

# flatKey -> leaf to relocate the original value under
RELOCATE = {
    "auth.forgotPassword": "link",
    "auth.resetPassword": "label",
    "expenses.expenseList": "label",
    "marketing.campaignList": "label",
    "products.productList": "label",
    "settings.marketingTab": "label",
    "suppliers.supplierList": "label",
    "users.forcePasswordChange": "label",
    "users.userList": "label",
    "errors.generic": "message",
}


def pop(d, dotted):
    parts = dotted.split(".")
    cur = d
    for p in parts[:-1]:
        cur = cur[p]
    return cur.pop(parts[-1])


def setk(d, dotted, val):
    parts = dotted.split(".")
    cur = d
    for p in parts[:-1]:
        cur = cur.setdefault(p, {})
    cur[parts[-1]] = val


def main():
    en = json.load(open(EN, encoding="utf-8"))
    es = json.load(open(ES, encoding="utf-8"))
    for flat, leaf in RELOCATE.items():
        ev = pop(en, flat)
        sv = pop(es, flat)
        assert isinstance(ev, str) and isinstance(sv, str), flat
        setk(en, f"{flat}.{leaf}", ev)
        setk(es, f"{flat}.{leaf}", sv)
        print(f"relocated {flat} -> {flat}.{leaf}  ({ev!r} / {sv!r})")
    json.dump(en, open(EN, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    open(EN, "a", encoding="utf-8").write("\n")
    json.dump(es, open(ES, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    open(ES, "a", encoding="utf-8").write("\n")

    # rewrite code references
    edits = 0
    for flat, leaf in RELOCATE.items():
        new = f"{flat}.{leaf}"
        patterns = [
            (f"t('{flat}')", f"t('{new}')"),
            (f't("{flat}")', f't("{new}")'),
            (f"'{flat}' | transloco", f"'{new}' | transloco"),
            (f'"{flat}" | transloco', f'"{new}" | transloco'),
            (f"translate('{flat}')", f"translate('{new}')"),
            (f'translate("{flat}")', f'translate("{new}")'),
        ]
        for dp, _, fns in os.walk(APP):
            for fn in fns:
                if not (fn.endswith(".html") or fn.endswith(".ts")) or fn.endswith(".spec.ts"):
                    continue
                p = os.path.join(dp, fn)
                txt = open(p, encoding="utf-8").read()
                orig = txt
                for a, b in patterns:
                    txt = txt.replace(a, b)
                if txt != orig:
                    open(p, "w", encoding="utf-8").write(txt)
                    edits += 1
                    print(f"  ref updated: {os.path.relpath(p, BASE)}")
    print(f"done: {edits} files updated")


if __name__ == "__main__":
    main()
