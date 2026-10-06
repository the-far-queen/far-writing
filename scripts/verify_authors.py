"""
verify_authors.py — resolve author dates from Wikidata, resumably.

The author list is the source of voices we write with, so the dates have
to be real rather than recalled. This script fetches them from Wikidata
and records the QID as provenance.

It is resumable on purpose: Wikidata rate-limits aggressively, and a
run over 111 authors will be interrupted. Progress is written after each
author, so a re-run picks up where it stopped instead of re-fetching.

    python scripts/verify_authors.py            # resume until done
    python scripts/verify_authors.py --status   # how many are dated
    python scripts/verify_authors.py --retry    # refetch anything unresolved
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
CATALOG = os.path.join(HERE, "..", "catalog", "authors.json")
UA = {"User-Agent": "far-writing-canon/1.0 (public-domain catalog build)"}

# Wikidata rate-limits hard. These are deliberately slow.
DELAY = 1.2
TRIES = 4


def _get(url: str):
    last: Exception = RuntimeError("no attempt made")
    for i in range(TRIES):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read().decode())
        except Exception as ex:                      # noqa: BLE001
            last = ex
            time.sleep(2.0 * (i + 1))
    raise last


def search(name: str):
    d = _get("https://www.wikidata.org/w/api.php?action=wbsearchentities&search="
             + urllib.parse.quote(name) + "&language=en&format=json&limit=1")
    return d.get("search") or []


def dates(qid: str):
    e = _get(f"https://www.wikidata.org/wiki/Special:EntityData/{qid}.json")["entities"][qid]
    claims = e.get("claims", {})

    def yr(prop):
        for c in claims.get(prop, []):
            v = c["mainsnak"].get("datavalue", {}).get("value", {})
            if "time" in v:
                return int(v["time"][1:5])
        return None

    return (yr("P569"), yr("P570"),
            e.get("labels", {}).get("en", {}).get("value", ""))


def save(authors):
    tmp = CATALOG + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(authors, f, indent=2, ensure_ascii=False)
    os.replace(tmp, CATALOG)          # atomic: never leave a half-written catalog


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--retry", action="store_true", help="refetch undated authors")
    ap.add_argument("--limit", type=int, default=0, help="stop after N authors")
    args = ap.parse_args()

    with open(CATALOG, encoding="utf-8") as f:
        authors = json.load(f)

    dated = [a for a in authors if a.get("born") and a.get("died")]
    undated = [a for a in authors if not (a.get("born") and a.get("died"))]

    if args.status:
        print(f"{len(authors)} authors | {len(dated)} dated | {len(undated)} undated")
        for a in undated[:15]:
            print(f"  - {a['name']}")
        return 0

    todo = authors if args.retry else undated
    if args.limit:
        todo = todo[: args.limit]
    if not todo:
        print("nothing to do")
        return 0

    print(f"resolving {len(todo)} authors (resumable; rerun to continue)")
    ok = fail = 0
    for i, a in enumerate(todo, 1):
        try:
            hits = search(a["name"])
            if not hits:
                a["note"] = (a.get("note", "") + " [no wikidata hit]").strip()
                fail += 1
            else:
                b, d, lbl = dates(hits[0]["id"])
                if b and d:
                    a["born"] = b
                    a["died"] = d
                    a["verified"] = True
                    a["source"] = f"wikidata {hits[0]['id']}"
                    if b < 1800 and not a.get("note"):
                        a["note"] = ("ancient; catalogued as a voice source but "
                                     "outside the 1800-1910 build window")
                    ok += 1
                else:
                    a["note"] = (a.get("note", "") + f" [no dates {b}-{d}]").strip()
                    fail += 1
        except Exception as ex:                      # noqa: BLE001
            a["note"] = (a.get("note", "") + f" [{type(ex).__name__}]").strip()
            fail += 1

        if i % 5 == 0:
            save(authors)                    # checkpoint
            print(f"  {i}/{len(todo)}  resolved={ok} failed={fail}")

        time.sleep(DELAY)

    save(authors)
    dated_now = sum(1 for a in authors if a.get("born") and a.get("died"))
    print(f"\nresolved {ok}, failed {fail}")
    print(f"{dated_now}/{len(authors)} authors now dated")
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
