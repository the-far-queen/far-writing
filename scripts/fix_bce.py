"""
fix_bce.py — repair ancient-author dates that lost their era sign.

A bug in the first pass: Wikidata encodes BCE as a negative year
("-0600-01-01"), and slicing [1:5] off the string turned 620 BCE into
the number 620. The catalog then held "Aesop 620-564", which looks like
a man who died 56 years before he was born, and the gate correctly
refused it.

This script re-fetches every author whose dates look impossible and
stores the sign properly: BCE years are negative.

    python scripts/fix_bce.py
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
CATALOG = os.path.join(HERE, "..", "catalog", "authors.json")
UA = {"User-Agent": "far-writing-canon/1.0 (catalog repair)"}


def signed_year(claim) -> int | None:
    """Wikidata time string -> signed integer year. 620 BCE is -619."""
    v = claim["mainsnak"].get("datavalue", {}).get("value", {})
    t = v.get("time")
    if not t:
        return None
    body = t[1:]                      # strip the leading +/- sign
    year = int(body[:4])
    return -year if t.startswith("-") else year


def entity(qid: str):
    url = f"https://www.wikidata.org/wiki/Special:EntityData/{qid}.json"
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA),
                                timeout=30) as r:
        return json.loads(r.read().decode())["entities"][qid]


def main() -> int:
    with open(CATALOG, encoding="utf-8") as f:
        authors = json.load(f)

    suspects = []
    for a in authors:
        b, d = a.get("born"), a.get("died")
        if b is None or d is None:
            continue
        if d < b or (d - b) < 20:          # impossible: died before born, or 3-year life
            suspects.append(a)

    print(f"{len(suspects)} authors with impossible dates")
    fixed = unresolved = 0

    for a in suspects:
        src = a.get("source", "")
        qid = src.split()[-1] if src.startswith("wikidata") else None
        if not qid:
            a["note"] = (a.get("note", "") + " [bad dates, no source qid]").strip()
            unresolved += 1
            continue
        try:
            e = entity(qid)
            claims = e.get("claims", {})
            b = next((signed_year(c) for c in claims.get("P569", [])), None)
            d = next((signed_year(c) for c in claims.get("P570", [])), None)
            if b is None or d is None:
                a["note"] = (a.get("note", "") + " [qid has no dates]").strip()
                unresolved += 1
                continue
            old = (a["born"], a["died"])
            a["born"], a["died"] = b, d
            a["verified"] = True
            if b < 1800:
                a["note"] = ("ancient; catalogued as a voice source but outside "
                             "the 1800-1910 build window")
            fixed += 1
            era = lambda y: f"{abs(y)} BCE" if y < 0 else f"{y} CE"   # noqa: E731
            print(f"  {a['name']:26s} {old} -> {b}..{d}  "
                  f"({era(b)} - {era(d)})")
        except Exception as ex:                                  # noqa: BLE001
            a["note"] = (a.get("note", "") + f" [{type(ex).__name__}]").strip()
            unresolved += 1
        time.sleep(1.0)

    with open(CATALOG, "w", encoding="utf-8") as f:
        json.dump(authors, f, indent=2, ensure_ascii=False)

    print(f"\nfixed {fixed}, unresolved {unresolved}")
    return 0 if unresolved == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
