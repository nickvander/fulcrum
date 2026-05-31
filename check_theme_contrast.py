#!/usr/bin/env python3
"""Theme-contrast guard for the Fulcrum frontend.

Catches the two bug classes that repeatedly broke dark mode in the
"Obsidian & Chile" design system, BEFORE they land:

  1. HARDCODED COLOR LITERALS on color/background/border/fill/outline
     properties in component SCSS. The app is dark-by-default; a literal
     like `color: #333` or `background: #fff` that should be a token
     (`var(--text-main)`, `var(--bg-card)`) renders invisible/ugly on the
     dark Obsidian surfaces. Components must use the var(--*) contract so
     they adapt to both themes.

  2. UNDEFINED CSS CUSTOM PROPERTIES — `var(--surface-card)`,
     `var(--primary-rgb)`, `var(--warn-color)` etc. that are not defined
     anywhere (and aren't framework --mat-*/--mdc-* tokens). These silently
     fall back to nothing / a light literal, which is how several dark-mode
     bugs slipped in.

Intentional exceptions (brand/channel colors, chart palettes, camera
surfaces, modal scrims, gradient cards with white text, deliberately-dark
hero panels, dual-palette blocks with their own .dark-theme overrides) are
handled two ways:
  - per-line escape hatch: end the line with `// theme-ok`
  - per-file allowlist: ALLOWLIST below (components that are legitimately
    full of intentional non-token colors).

Usage:
    python3 check_theme_contrast.py [frontend/src/app]
Exits non-zero if any violation is found.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

DEFAULT_ROOT = Path("frontend/src/app")
THEME_DIR = Path("frontend/src/theme")
STYLES = [Path("frontend/src/styles.scss"), Path("frontend/src/styles")]

# Components that are legitimately full of intentional, non-token colors.
# (brand/channel identity, chart palettes, camera affordances, scrims, gradient
#  cards, the always-dark login hero, dual-palette blocks with dark overrides).
ALLOWLIST = {
    "product-scanner",                 # camera viewfinder: opaque black, white reticle/markers
    "scan-sku-dialog",                 # barcode camera viewfinder: opaque black + dimming overlay
    "stat-card",                       # KPI gradient cards + white-on-gradient text
    "sales-by-channel-widget",         # MercadoLibre/Amazon channel brand gradients
    "margin-by-channel-widget",        # categorical cost-segment chart palette
    "campaign-list",                   # social channel brand colors
    "campaign-calendar",               # categorical calendar-status palette
    "connector-settings",              # email/social provider brand colors
    "quick-post-dialog",
    "quick-post-detail-dialog",
    "marketplace-status",              # channel badges w/ explicit .dark-theme overrides
    "login",                           # deliberately-dark Obsidian brand hero
    "product-list",                    # selection bar dual-palette + :host-context(.dark-theme)
    "product-form",                    # gallery overlays + gold primary markers
    "product-form-image-gallery",
    "loading-spinner",                 # overlay scrim only
}

# Color-bearing properties we police. Shadows are deliberately excluded.
PROP_RE = re.compile(
    r"^\s*(-?\b(?:background|background-color|color|border|border-top|border-bottom|"
    r"border-left|border-right|border-color|outline|outline-color|fill|stroke)\b)\s*:",
    re.IGNORECASE,
)
HEX_RE = re.compile(r"#[0-9a-fA-F]{3,8}\b")
RGB_RE = re.compile(r"\brgba?\(", re.IGNORECASE)
NAMED_RE = re.compile(r"\b(white|black)\b", re.IGNORECASE)
# white literal — allowed as a `color:` value (white text on a colored/brand
# surface is the norm in a dark-default app); still policed on backgrounds.
WHITE_RE = re.compile(r"^\s*(#fff(?:fff)?|white)\s*$", re.IGNORECASE)
# rgba(...,0) / rgba(...,0.0) — fully transparent, harmless in either theme.
TRANSPARENT_ALPHA_RE = re.compile(r"rgba?\([^)]*,\s*0(?:\.0+)?\s*\)", re.IGNORECASE)
# A var() reference with NO fallback: var(--x). These break hard when --x is
# undefined. var(--x, fallback) degrades gracefully, so we don't police it.
VAR_NOFALLBACK_RE = re.compile(r"var\(\s*(--[A-Za-z0-9-]+)\s*\)")
# a custom property *definition*: `--name:`
VAR_DEF_RE = re.compile(r"(--[A-Za-z0-9-]+)\s*:")


def scss_files(root: Path):
    return sorted(p for p in root.rglob("*.scss"))


def collect_defined_tokens() -> set[str]:
    """Every --custom-prop defined anywhere (theme files, global styles, and
    per-component local :host blocks). Union is intentionally global — a token
    defined in any file counts as defined."""
    defined: set[str] = set()
    search_roots = [DEFAULT_ROOT, THEME_DIR] + STYLES
    seen: set[Path] = set()
    for r in search_roots:
        if not r.exists():
            continue
        files = scss_files(r) if r.is_dir() else [r]
        for f in files:
            if f in seen:
                continue
            seen.add(f)
            for line in f.read_text(encoding="utf-8", errors="ignore").splitlines():
                for m in VAR_DEF_RE.finditer(line):
                    defined.add(m.group(1))
    return defined


def is_allowlisted(path: Path) -> bool:
    parts = set(path.parts)
    stem = path.stem.replace(".component", "")
    return stem in ALLOWLIST or bool(ALLOWLIST & parts)


def check_hardcoded_colors(files) -> list[str]:
    violations = []
    for f in files:
        if is_allowlisted(f):
            continue
        for i, line in enumerate(f.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
            if "theme-ok" in line:
                continue
            low = line.lower()
            if "box-shadow" in low or "text-shadow" in low:
                continue
            m = PROP_RE.search(line)
            if not m:
                continue
            prop = m.group(1).lstrip("-").lower()
            # strip the transparent rgba(...,0) form so it doesn't trip RGB_RE
            scrubbed = TRANSPARENT_ALPHA_RE.sub("", line)
            value = scrubbed.split(":", 1)[1] if ":" in scrubbed else scrubbed
            # white *text* (color:) on a colored/brand surface is idiomatic in a
            # dark-default app; only police white on backgrounds/borders.
            value_no_bang = re.sub(r"!important|;.*$", "", value).strip()
            if prop == "color" and WHITE_RE.match(value_no_bang):
                continue
            has_literal = HEX_RE.search(value) or RGB_RE.search(value) or NAMED_RE.search(value)
            if not has_literal:
                continue
            # var(--token) is the correct pattern; allow it even with a fallback.
            if "var(" in value:
                continue
            violations.append(f"{f}:{i}: hardcoded color -> use a var(--*) token: {line.strip()}")
    return violations


def check_undefined_tokens(files, defined: set[str]) -> list[str]:
    violations = []
    for f in files:
        for i, line in enumerate(f.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
            if "theme-ok" in line:
                continue
            for m in VAR_NOFALLBACK_RE.finditer(line):
                tok = m.group(1)
                # framework-provided tokens (Angular Material) are defined at runtime
                if tok.startswith("--mat-") or tok.startswith("--mdc-"):
                    continue
                if tok not in defined:
                    violations.append(f"{f}:{i}: undefined token {tok}: {line.strip()}")
    return violations


def main() -> int:
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_ROOT
    if not root.exists():
        print(f"[theme-guard] path not found: {root}", file=sys.stderr)
        return 2

    files = scss_files(root)
    defined = collect_defined_tokens()

    hard = check_hardcoded_colors(files)
    undef = check_undefined_tokens(files, defined)

    if not hard and not undef:
        print(f"[theme-guard] OK — {len(files)} SCSS files clean "
              f"(no hardcoded colors, no undefined tokens).")
        return 0

    if hard:
        print(f"\n[theme-guard] {len(hard)} hardcoded color literal(s) "
              f"(use a var(--*) token, or add `// theme-ok` if intentional):")
        for v in hard:
            print("  " + v)
    if undef:
        print(f"\n[theme-guard] {len(undef)} undefined CSS custom-property reference(s) "
              f"(define it in theme/variables.scss or fix the name):")
        for v in undef:
            print("  " + v)
    print(f"\n[theme-guard] FAILED: {len(hard) + len(undef)} issue(s).")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
