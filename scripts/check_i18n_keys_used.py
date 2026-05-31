#!/usr/bin/env python3
"""Verify every statically-referenced Transloco key resolves in the i18n JSON files.

Scans frontend/src/app for:
  - template usages:  t('a.b.c')   and   'a.b.c' | transloco
  - TS usages:        <svc>.translate('a.b.c')  /  .selectTranslate('a.b.c')

Any static (string-literal) key not present in BOTH en.json and es-MX.json is reported.
Keys built dynamically (concatenation / interpolation) are skipped — we can only
verify literals. Exit 1 if any missing, so it doubles as a CI/regression guard.
"""
import json
import os
import re
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP = os.path.join(BASE, "frontend", "src", "app")
I18N = os.path.join(BASE, "frontend", "src", "assets", "i18n")

KEY_RE = re.compile(r"""(?:\bt\(\s*|\btranslate\(\s*|\bselectTranslate\(\s*)(['"])([A-Za-z0-9_.]+)\1""")
PIPE_RE = re.compile(r"""(['"])([A-Za-z0-9_.]+)\1\s*\|\s*transloco""")


def all_keys(path):
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    keys = set()
    def walk(o, p=""):
        for k, v in o.items():
            kk = f"{p}.{k}" if p else k
            if isinstance(v, dict):
                walk(v, kk)
            else:
                keys.add(kk)
    walk(data)
    return keys


def main():
    en = all_keys(os.path.join(I18N, "en.json"))
    es = all_keys(os.path.join(I18N, "es-MX.json"))
    used = {}  # key -> first "file:line"
    for dp, _, fns in os.walk(APP):
        for fn in fns:
            if not (fn.endswith(".html") or fn.endswith(".ts")) or fn.endswith(".spec.ts"):
                continue
            p = os.path.join(dp, fn)
            for i, line in enumerate(open(p, encoding="utf-8"), 1):
                for m in KEY_RE.finditer(line):
                    used.setdefault(m.group(2), f"{os.path.relpath(p, BASE)}:{i}")
                for m in PIPE_RE.finditer(line):
                    used.setdefault(m.group(2), f"{os.path.relpath(p, BASE)}:{i}")

    # Drop dynamic-concatenation fragments (literal ends with '.', meaning code appends a variable).
    used = {k: v for k, v in used.items() if not k.endswith(".")}
    missing_en = sorted(k for k in used if k not in en)
    missing_es = sorted(k for k in used if k not in es)
    if missing_en or missing_es:
        if missing_en:
            print(f"[ERROR] {len(missing_en)} keys used but missing in en.json:")
            for k in missing_en:
                print(f"    {k}   ({used[k]})")
        if missing_es:
            print(f"[ERROR] {len(missing_es)} keys used but missing in es-MX.json:")
            for k in missing_es:
                print(f"    {k}   ({used[k]})")
        sys.exit(1)
    print(f"[OK] all {len(used)} referenced keys resolve in en.json and es-MX.json")


if __name__ == "__main__":
    main()
