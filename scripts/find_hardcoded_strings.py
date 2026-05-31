#!/usr/bin/env python3
"""Heuristic detector for hardcoded user-facing English strings in Angular templates.

Scans *.html templates under frontend/src/app and flags text/attribute content that
looks like natural-language English and is NOT routed through Transloco ({{ t('...') }}
or | transloco). Intended as a regression guard and a work-list generator for the
es-MX localization sweep. Heuristic: expect some false positives (icon names, code).

Usage:
    python3 scripts/find_hardcoded_strings.py [--json] [path ...]
Exit code 1 if any leaks found (so it can be used as a CI guard).
"""
import os
import re
import sys
import json

ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend", "src", "app")

# Material icon ligatures and other non-translatable tokens we should ignore as element text.
IGNORE_TEXT = re.compile(r"^[\s]*$")
# A "word" that looks like English prose (>=2 letters), used to decide if text is natural language.
WORD = re.compile(r"[A-Za-z]{2,}")
# Things that are clearly not prose: pure interpolation, bindings, code-ish tokens.
INTERP = re.compile(r"\{\{")
# mat-icon ligature names (single token, often snake_case) — common false positives.
ICON_LINE = re.compile(r"<mat-icon[^>]*>[^<]+</mat-icon>")

# Attribute patterns that carry user-facing text when given a string literal.
ATTR_PATTERNS = [
    re.compile(r'\bplaceholder\s*=\s*"([^"{}]*[A-Za-z]{2,}[^"{}]*)"'),
    re.compile(r'\bmatTooltip\s*=\s*"([^"{}]*[A-Za-z]{2,}[^"{}]*)"'),
    re.compile(r'\baria-label\s*=\s*"([^"{}]*[A-Za-z]{2,}[^"{}]*)"'),
    re.compile(r"\[matTooltip\]\s*=\s*\"'([^'\"]*[A-Za-z]{2,}[^'\"]*)'\""),
    re.compile(r"\[placeholder\]\s*=\s*\"'([^'\"]*[A-Za-z]{2,}[^'\"]*)'\""),
    re.compile(r"\[attr\.aria-label\]\s*=\s*\"'([^'\"]*[A-Za-z]{2,}[^'\"]*)'\""),
]
# Element text content: >Text< capturing what is between tags.
TEXT_BETWEEN = re.compile(r">([^<>{}]*[A-Za-z]{2,}[^<>{}]*)<")

# Tokens that, if the captured text equals one of these, are not prose.
NON_PROSE = {
    "true", "false", "null", "px", "em", "rem", "ngIf", "ngFor", "ngClass",
}

# Proper nouns / brand & product names / technical tokens that are intentionally not translated.
ALLOW = {
    "fulcrum", "mercadolibre", "amazon", "gmail", "outlook", "yahoo", "openai",
    "anthropic claude", "google gemini", "qwen (alibaba)", "seller central",
    "developer center", "csv", "json", "pdf", "png", "jpg", "pdf, png, jpg",
    "usd", "eur", "cny", "mxn", "gbp", "sku", "upc", "qr", "smtp", "api",
    "english", "español (méxico)", "español (mx)", "email",
}


def looks_english(text):
    t = text.strip()
    if not t or not WORD.search(t):
        return False
    if t in NON_PROSE:
        return False
    if t.lower() in ALLOW:
        return False
    # Angular control-flow / boolean expression fragments captured as text (e.g. "0 && x || 0").
    if "&&" in t or "||" in t:
        return False
    # Currency/markup artifacts like "$&nbsp;" or "&nbsp;MXN".
    if t.replace("&nbsp;", "").replace("$", "").strip() == "" or t.replace("&nbsp;", "").strip().lower() in ALLOW:
        return False
    # Skip if it's a single material-icon ligature token (snake_case, no spaces) — handled separately.
    if " " not in t and "_" in t:
        return False
    # Skip if it's clearly an interpolation/binding fragment.
    if "{{" in t or "}}" in t or t.startswith("@") or t.startswith("#"):
        return False
    # Skip pure punctuation-with-one-word artifacts like "&nbsp;"
    if t.replace("&nbsp;", "").strip() == "":
        return False
    # Skip if it is just an Angular pipe/expression-looking token (no spaces, has a dot or paren)
    if " " not in t and ("(" in t or ")" in t or t.endswith(":")):
        return False
    return True


def scan_file(path):
    leaks = []
    try:
        with open(path, encoding="utf-8") as f:
            lines = f.readlines()
    except Exception:
        return leaks
    for i, line in enumerate(lines, 1):
        # Attribute literals
        for pat in ATTR_PATTERNS:
            for m in pat.finditer(line):
                val = m.group(1)
                if looks_english(val):
                    leaks.append((i, "attr", val.strip()))
        # Element text content (skip mat-icon ligature lines for the text check)
        scrubbed = ICON_LINE.sub("<mat-icon></mat-icon>", line)
        # Multi-line <mat-icon> whose closing tag (with the ligature) lands on this line.
        scrubbed = re.sub(r">[^<>{}]*</mat-icon>", "></mat-icon>", scrubbed)
        # <code> contents are literal identifiers (CSV columns, field names), not prose.
        scrubbed = re.sub(r"<code>[^<]*</code>", "<code></code>", scrubbed)
        for m in TEXT_BETWEEN.finditer(scrubbed):
            val = m.group(1)
            if "transloco" in line and "|" in val:
                continue
            if looks_english(val):
                leaks.append((i, "text", val.strip()))
    return leaks


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    as_json = "--json" in sys.argv
    targets = []
    roots = args if args else [ROOT]
    for r in roots:
        if os.path.isfile(r):
            targets.append(r)
        else:
            for dp, _, fns in os.walk(r):
                for fn in fns:
                    if fn.endswith(".html"):
                        targets.append(os.path.join(dp, fn))

    results = {}
    total = 0
    for path in sorted(targets):
        leaks = scan_file(path)
        if leaks:
            rel = os.path.relpath(path, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            results[rel] = leaks
            total += len(leaks)

    if as_json:
        print(json.dumps({k: [{"line": ln, "kind": k2, "text": t} for (ln, k2, t) in v] for k, v in results.items()}, ensure_ascii=False, indent=2))
    else:
        for rel in sorted(results, key=lambda k: -len(results[k])):
            print(f"\n{rel}  ({len(results[rel])} leaks)")
            for (ln, kind, t) in results[rel][:40]:
                print(f"  {ln:>4} [{kind}] {t[:90]}")
        print(f"\n=== {total} candidate leaks across {len(results)} files ===")

    sys.exit(1 if total else 0)


if __name__ == "__main__":
    main()
