"""
dedupe_authors.py -- ONE AUTHOR, ONE ENTRY.

MEASURED 2026-10-31: the catalog held 263 authors and **260 distinct
Wikidata items**, because three authors appear TWICE under two names:

    Q234530   Baroness Emma Orczy    Emma Orczy
    Q231708   E. Nesbit              Edith Nesbit
    Q991      Fyodor Dostoevsky      Fyodor Dostoyevsky

Each pair is the SAME PERSON, with the SAME birth year and the SAME
Wikidata item -- one entry was added by the reach build and one by the
intake, and nothing ever noticed they were the same person.

**AND THIS IS NOT COSMETIC.** The expansion resolves each author's
titles against the author's own Wikidata item, so BOTH entries of a
pair harvest the SAME bibliography -- and the "Emma Orczy" entry ends
up with 31 works and the "Baroness Emma Orczy" entry with 31 more, and
the catalog carries the same author's works twice. MEASURED: the
expansion added 30 works to "Emma Orczy" and 32 to "Baroness Emma
Orczy", for the same woman.

**SO THE MERGE IS BY THE AUTHOR'S OWN ITEM**, not by the name -- the
name is a label and Wikidata's item is the identity. And the entries
are MERGED, not dropped: their works are combined, and the longest
title and the richest note are kept.

Run:
    python tools/dedupe_authors.py --report
    python tools/dedupe_authors.py --apply
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from typing import Dict, List, Tuple

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CATALOG = os.path.join(REPO, "catalog", "authors.json")


def qid_of(a: dict) -> str:
    m = re.search(r"(Q\d+)", a.get("source", "") or "")
    return m.group(0) if m else ""


def norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


def merge(keep: dict, other: dict) -> dict:
    """the two entries of one author, as ONE entry.

    **AND THE WORKS ARE COMBINED, NOT REPLACED.** The two entries were
    built by different passes, and each holds works the other does
    not -- MEASURED, "Edith Nesbit" held 1 work and "E. Nesbit" held
    10. Dropping either would lose real works.

    **AND A DUPLICATE TITLE IS DROPPED.** The two entries can hold the
    SAME work -- MEASURED, "Fyodor Dostoevsky" and "Fyodor Dostoyevsky"
    each held 18 works, and the sets overlap -- so the merge is on the
    normalized title, and the first one wins.
    """
    out = dict(keep)
    seen = {norm(w.get("title", "")) for w in out.get("works", [])}
    added = 0
    for w in other.get("works", []):
        k = norm(w.get("title", ""))
        if not k or k in seen:
            continue
        seen.add(k)
        out.setdefault("works", []).append(w)
        added += 1
    # THE NAME: the longer one, because "Baroness Emma Orczy" is more
    # informative than "Emma Orczy" and "Edith Nesbit" more than
    # "E. Nesbit". MEASURED: the reach build's label is the bare one
    # and the intake's carries the title.
    if len(other.get("name", "")) > len(out.get("name", "")):
        out["name"] = other["name"]
    # THE NOTE: the one that carries the most information.
    if len(other.get("note", "")) > len(out.get("note", "")):
        out["note"] = other["note"]
    out["_merged"] = (out.get("_merged", "") + " + " + other["name"]).strip(" +")
    out["_added_works"] = added
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="merge duplicate authors")
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    with open(CATALOG, encoding="utf-8") as fh:
        catalog = json.load(fh)

    by_qid: Dict[str, List[int]] = {}
    for i, a in enumerate(catalog):
        q = qid_of(a)
        if q:
            by_qid.setdefault(q, []).append(i)

    dups = {q: idx for q, idx in by_qid.items() if len(idx) > 1}

    print("=" * 84)
    print("THE AUTHORS WE HOLD")
    print("=" * 84)
    print("  author entries:      %d" % len(catalog))
    print("  distinct items:      %d" % len(by_qid))
    print("  items held TWICE:    %d" % len(dups))
    print()
    for q, idx in sorted(dups.items()):
        names = [catalog[i]["name"] for i in idx]
        works = [len(catalog[i].get("works", [])) for i in idx]
        print("    %-10s %s  (works: %s)"
              % (q, " + ".join(names), " + ".join(str(w) for w in works)))
    print()

    if not args.apply:
        print("  (--apply merges them)")
        return 0

    # THE MERGE. One entry per item, and the merged entry keeps the
    # FIRST index so the catalog's order is stable.
    merged_out = []
    seen_qid = set()
    total_added = 0
    for a in catalog:
        q = qid_of(a)
        if not q or q not in dups:
            merged_out.append(a)
            continue
        if q in seen_qid:
            # THIS ONE IS THE SECOND OF A PAIR: its works are folded
            # into the first.
            first = next(x for x in merged_out if qid_of(x) == q)
            before = len(first.get("works", []))
            m = merge(first, a)
            total_added += m.get("_added_works", 0)
            first.clear()
            first.update(m)
            continue
        seen_qid.add(q)
        merged_out.append(a)

    # THE MERGE MARKERS ARE INTERNAL.
    for a in merged_out:
        a.pop("_merged", None)
        a.pop("_added_works", None)

    tmp = CATALOG + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(merged_out, fh, indent=2, ensure_ascii=False)
    os.replace(tmp, CATALOG)

    print("=" * 84)
    print("APPLIED")
    print("=" * 84)
    print("  author entries: %d -> %d" % (len(catalog), len(merged_out)))
    print("  works added by the merge: %d" % total_added)
    print("  the catalog: %d authors, %d works"
          % (len(merged_out), sum(len(a.get("works", [])) for a in merged_out)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
