#!/usr/bin/env python3
"""Merge agent-authored bilingual keys into en.json + es-MX.json (single writer).

Input: work/redesign/i18n_results.json — a JSON array of agent results, each:
  { "id": "...", "addedKeys": [ {"key":"a.b.c","en":"...","esMX":"..."}, ... ], ... }
Also merges work/redesign/i18n_central_keys.json (the pre-existing-missing + manual fixes),
same {key,en,esMX} list shape.

Sets each dotted key into both files. Conflicts (key already present with a different
value) are reported and left as-is (existing wins) so we never silently overwrite.
"""
import json
import os

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
I18N = os.path.join(BASE, "frontend", "src", "assets", "i18n")
EN = os.path.join(I18N, "en.json")
ES = os.path.join(I18N, "es-MX.json")
RESULTS = os.path.join(BASE, "work", "redesign", "i18n_results.json")
CENTRAL = os.path.join(BASE, "work", "redesign", "i18n_central_keys.json")


def load(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def set_nested(d, dotted, value):
    """Set value; return ('added'|'same'|'conflict', existing_or_None)."""
    parts = dotted.split(".")
    cur = d
    for p in parts[:-1]:
        nxt = cur.get(p)
        if not isinstance(nxt, dict):
            if p in cur:  # leaf where we need a dict -> structural conflict
                return ("conflict", cur[p])
            cur[p] = {}
            nxt = cur[p]
        cur = nxt
    leaf = parts[-1]
    if leaf in cur:
        if isinstance(cur[leaf], dict):
            return ("conflict", "<dict>")
        if cur[leaf] == value:
            return ("same", value)
        return ("conflict", cur[leaf])
    cur[leaf] = value
    return ("added", None)


def gather():
    pairs = []  # (key, en, esMX, source)
    for path, src in [(RESULTS, "agent"), (CENTRAL, "central")]:
        if not os.path.exists(path):
            continue
        data = load(path)
        items = data if isinstance(data, list) else [data]
        for it in items:
            for k in it.get("addedKeys", []) if isinstance(it, dict) else []:
                if not all(x in k for x in ("key", "en", "esMX")):
                    continue
                pairs.append((k["key"], k["en"], k["esMX"], it.get("id", src)))
            # central file may itself be a flat list of {key,en,esMX}
            if isinstance(it, dict) and "key" in it and "en" in it and "esMX" in it:
                pairs.append((it["key"], it["en"], it["esMX"], "central"))
    return pairs


def main():
    en = load(EN)
    es = load(ES)
    pairs = gather()
    added = conflicts = same = 0
    seen = {}
    for key, en_v, es_v, src in pairs:
        if key in seen and seen[key] != (en_v, es_v):
            print(f"[DUP-DIFF] {key}: two agents gave different values; keeping first ({seen[key][0]!r}) vs ({en_v!r}) from {src}")
            continue
        seen[key] = (en_v, es_v)
        r_en, ex_en = set_nested(en, key, en_v)
        r_es, ex_es = set_nested(es, key, es_v)
        if r_en == "conflict" or r_es == "conflict":
            conflicts += 1
            print(f"[CONFLICT] {key}: exists en={ex_en!r}/es={ex_es!r}; NOT overwriting with en={en_v!r} ({src})")
        elif r_en == "added" or r_es == "added":
            added += 1
        else:
            same += 1
    with open(EN, "w", encoding="utf-8") as f:
        json.dump(en, f, ensure_ascii=False, indent=2)
        f.write("\n")
    with open(ES, "w", encoding="utf-8") as f:
        json.dump(es, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(f"\nMerged: {added} added, {same} already-present, {conflicts} conflicts (skipped). {len(seen)} unique keys processed.")


if __name__ == "__main__":
    main()
