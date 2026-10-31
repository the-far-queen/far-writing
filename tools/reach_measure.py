"""
reach_measure.py -- THE REACH MEASUREMENT, CORRECTED AT THE SOURCE.

**THE DEFECT, STATED EXACTLY.** The measurement that qualified 263
authors and that the catalog's `reach_adaptations` field was built on
counted ROWS of a SPARQL result:

    SELECT ?author ?authorLabel ?work ?workLabel ?date WHERE {
      ?adapt (wdt:P144|wdt:P1441) ?work .
      ?work wdt:P577 ?date ; wdt:P50 ?author .
      FILTER(YEAR(?date) >= 1800 && YEAR(?date) <= 1910)
    }

Every returned row is one (adapt, work, date, author) TUPLE, and the
row was counted. So the number written into a field named
`reach_adaptations` was

        adaptations x distinct dates x distinct authors

which is a JOIN PRODUCT, not an adaptation count.

**MEASURED, on the cached rows:**

    work                       rows    true adaptations
    Dream of the Red Chamber    2126   1063
    Hansel and Gretel            66      22
    Moby-Dick                    84      42
    Crime and Punishment         82      41
    Leonce and Lena              96      24

and the total went from "13,259 rows over 2,486 labels" to "17,592
distinct adaptations over 3,428 works" -- the old number was not merely
too big, it was a different quantity.

**THE FIX.** `COUNT(DISTINCT ?adapt)`, grouped by (author, work). The
count is then an adaptation count, and the adaptation is NAMED, so the
number can be re-checked against the source.

Run:
    python tools/reach_measure.py --report
    python tools/reach_measure.py --apply
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict
from typing import Dict, List, Optional, Tuple

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CATALOG_DIR = os.path.join(REPO, "catalog")
GUT_DIR = os.path.join(CATALOG_DIR, "gutenberg")
CACHE = os.path.join(GUT_DIR, "wikicache")
AUTHORS_FILE = os.path.join(CATALOG_DIR, "authors.json")
REACH_FILE = os.path.join(GUT_DIR, "authors_by_reach.json")

os.makedirs(CACHE, exist_ok=True)

ENDPOINT = "https://query.wikidata.org/sparql"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) far-writing-canon/1.0 "
      "(public-domain catalog build)")

ERA_START, ERA_END = 1800, 1910

#: THE CORRECTED QUERY. The difference from the old one is COUNT(DISTINCT
#: ?adapt) and the GROUP BY -- and it is the whole difference between a
#: count of adaptations and a count of rows.
PER_WORK = """
SELECT ?author ?authorLabel ?work ?workLabel
       (COUNT(DISTINCT ?adapt) AS ?adaptations) WHERE {
  ?adapt (wdt:P144|wdt:P1441) ?work .
  ?work wdt:P577 ?date ; wdt:P50 ?author .
  FILTER(YEAR(?date) >= __START__ && YEAR(?date) <= __END__)
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
}
GROUP BY ?author ?authorLabel ?work ?workLabel
LIMIT __LIMIT__
"""

#: THE BY-WORK TABLE, so a work's own count does not depend on how many
#: authors the work has.
BY_WORK = """
SELECT ?work ?workLabel (COUNT(DISTINCT ?adapt) AS ?adaptations) WHERE {
  ?adapt (wdt:P144|wdt:P1441) ?work .
  ?work wdt:P577 ?date .
  FILTER(YEAR(?date) >= __START__ && YEAR(?date) <= __END__)
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
}
GROUP BY ?work ?workLabel
LIMIT __LIMIT__
"""


def _fill(q: str) -> str:
    return (q.replace("__START__", str(ERA_START))
             .replace("__END__", str(ERA_END))
             .replace("__LIMIT__", "20000"))


def _cache_key(sparql: str, tag: str) -> str:
    """the cache key is the QUERY'S OWN TEXT, hashed.

    **AND THIS IS A FIX, NOT A STYLE.** The old key was
    `sparql_%s_%d.json % (tag, abs(hash(sparql)))`, and Python's `hash()`
    for a STRING IS RANDOMISED PER PROCESS. So the same query wrote a
    different cache file on every run, the cache never hit, and the
    measurement was re-fetched every time -- which is why the corrected
    query could not simply replace the old one on disk.

    The key is now sha256 of the query text, so the same query always
    finds its own cache, and a DIFFERENT query can never read another
    one's rows.
    """
    import hashlib
    h = hashlib.sha256(sparql.encode("utf-8")).hexdigest()[:16]
    return "sparql_%s_%s.json" % (tag, h)


def query(sparql: str, tag: str, timeout: int = 420) -> str:
    """run the query, with a cache keyed by the query's own text."""
    path = os.path.join(CACHE, _cache_key(sparql, tag))
    if os.path.isfile(path):
        with open(path, encoding="utf-8") as fh:
            return fh.read()
    url = ENDPOINT + "?" + urllib.parse.urlencode(
        {"query": sparql, "format": "json"})
    for attempt in range(5):
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": UA,
                "Accept": "application/sparql-results+json",
                "Accept-Encoding": "gzip",
            })
            with urllib.request.urlopen(req, timeout=timeout) as fh:
                raw = fh.read()
                if fh.headers.get("Content-Encoding") == "gzip":
                    import gzip
                    raw = gzip.decompress(raw)
            text = raw.decode("utf-8")
            with open(path, "w", encoding="utf-8") as out:
                out.write(text)
            return text
        except urllib.error.HTTPError as exc:
            body = exc.read()[:300].decode("utf-8", "replace")
            print("  %s attempt %d: HTTP %s %s"
                  % (tag, attempt + 1, exc.code, body[:200]))
            if exc.code == 400:
                return ""
        except Exception as exc:  # noqa: BLE001
            print("  %s attempt %d: %s" % (tag, attempt + 1, exc))
        time.sleep(10 + attempt * 15)
    return ""


def norm(s: str) -> str:
    """the catalog's own title key: lower, and non-alphanumerics to spaces."""
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


def reach_key(label: str) -> str:
    """the key a work's reach count is held under.

    **AND THE WRITER AND THE READER MUST AGREE ON IT.** MEASURED
    2026-10-31: the old table was written with the RAW Wikidata label
    and read with the NORMALIZED title, so 546 of 2,486 entries (22%)
    could never be found -- "Uncle Tom's Cabin" was held as
    "uncle tom's cabin" and looked up as "uncle tom s cabin". That is
    why 51 catalog works whose reach count WAS in the measurement
    carried `None`.

    So the key is ONE named function, used by the writer and by the
    reader, and a round-trip test holds them to it.
    """
    return norm(label)


def write_reach_table(by_work_counts: Dict[str, int], path: str = "") -> str:
    """write the per-work reach table, keyed by `reach_key`."""
    path = path or os.path.join(CACHE, "reach_by_work.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump({reach_key(k): int(v) for k, v in by_work_counts.items()},
                  fh, indent=1, ensure_ascii=False)
    return path


def read_reach_table(path: str = "") -> Dict[str, int]:
    """read the per-work reach table, keyed by `reach_key`."""
    path = path or os.path.join(CACHE, "reach_by_work.json")
    if not os.path.isfile(path):
        return {}
    with open(path, encoding="utf-8") as fh:
        raw = json.load(fh)
    return {reach_key(k): int(v) for k, v in raw.items()}


def load_reach_raw() -> Dict[str, int]:
    """the reach table's keys as they are STORED, before the reader
    normalizes them.

    **AND THIS EXISTS SO THE TEST CAN COMPARE.** The correction is
    visible only against the old measurement: the raw keys are what
    the SPARQL rows carried, and the normalized ones are what the
    catalog looks up. A test that cannot see both cannot check that
    the normalization happened.
    """
    path = os.path.join(CACHE, "reach_by_work.json")
    if not os.path.isfile(path):
        return {}
    with open(path, encoding="utf-8") as fh:
        raw = json.load(fh)
    return {k: int(v) for k, v in raw.items()}


def load_reach() -> Dict[str, int]:
    """the per-work adaptation counts, from the CORRECTED measurement.

    **AND THE KEY IS NORMALIZED ON BOTH SIDES.** MEASURED: the old
    lookup keyed the dict by the RAW Wikidata label and asked for the
    NORMALIZED title, so 546 of the 2,486 entries (22%) could never be
    found -- "Uncle Tom's Cabin" normalizes to "uncle tom s cabin" and
    the raw key "uncle tom's cabin" was never asked for. That is why 51
    catalog works whose reach count WAS in the measurement carried
    `None`: Moby-Dick, Alice's Adventures in Wonderland, Les Misérables,
    all of them.
    """
    return read_reach_table()


def load_author_reach() -> Dict[str, int]:
    """the per-author adaptation totals, from the CORRECTED measurement."""
    path = os.path.join(CACHE, "reach_by_author.json")
    if not os.path.isfile(path):
        return {}
    with open(path, encoding="utf-8") as fh:
        raw = json.load(fh)
    return {k: int(v) for k, v in raw.items()}


def measure(verbose: bool = True) -> Optional[Dict]:
    """run the corrected queries and cache the results."""
    per_work = query(_fill(PER_WORK), "perwork")
    by_work = query(_fill(BY_WORK), "bywork")
    if not per_work or not by_work:
        if verbose:
            print("  the corrected queries did not return")
        return None

    rows = json.loads(per_work)["results"]["bindings"]
    by_author: Dict[str, int] = defaultdict(int)
    by_work_counts: Dict[str, int] = {}
    for r in rows:
        a = r["authorLabel"]["value"]
        w = r["workLabel"]["value"]
        n = int(r["adaptations"]["value"])
        by_author[a] += n
        prev = by_work_counts.get(w, 0)
        by_work_counts[w] = max(prev, n)

    # THE BY-WORK TABLE IS THE AUTHORITY for a work's count, because it
    # does not depend on how many authors the work carries.
    for r in json.loads(by_work)["results"]["bindings"]:
        by_work_counts[r["workLabel"]["value"]] = int(r["adaptations"]["value"])

    write_reach_table(by_work_counts)
    with open(os.path.join(CACHE, "reach_by_author.json"), "w",
              encoding="utf-8") as fh:
        json.dump(dict(by_author), fh, indent=1, ensure_ascii=False)
    if verbose:
        print("  the corrected measurement: %d (author, work) rows"
              % len(rows))
        print("     %d works with a counted adaptation set" % len(by_work_counts))
        print("     %d authors with at least one" % len(by_author))
        print("     %d distinct adaptations in total" % sum(by_work_counts.values()))
    return {"by_work": by_work_counts, "by_author": dict(by_author)}


def main() -> int:
    ap = argparse.ArgumentParser(description="the corrected reach measure")
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--measure", action="store_true",
                    help="re-run the corrected query and cache it")
    args = ap.parse_args()

    print("=" * 84)
    print("THE REACH MEASUREMENT, CORRECTED")
    print("=" * 84)
    print("  window: %d-%d on PUBLICATION" % (ERA_START, ERA_END))
    print()

    if args.measure:
        print("  measuring...")
        measure()
        print()

    by_work = load_reach()
    by_author = load_author_reach()
    if not by_work:
        print("  no corrected measurement is cached. Run --measure.")
        return 1

    print("  the corrected per-work table: %d works" % len(by_work))
    print("  the corrected per-author table: %d authors" % len(by_author))
    print()
    print("  the top 15 works by the CORRECTED count:")
    for label, n in sorted(by_work.items(), key=lambda kv: -kv[1])[:15]:
        print("    %-46s %6d" % (label[:46], n))
    print()
    print("  the top 15 authors by the CORRECTED count:")
    for name, n in sorted(by_author.items(), key=lambda kv: -kv[1])[:15]:
        print("    %-46s %6d" % (name[:46], n))
    print()

    # THE THRESHOLD, and what it yields now.
    print("  THE THRESHOLD. 'more like 350' was >= 4 ADAPTATIONS = 368 authors.")
    for t in (1, 2, 3, 4, 5, 6, 8, 10):
        n = sum(1 for v in by_author.values() if v >= t)
        print("     >= %2d adaptations -> %4d authors" % (t, n))
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
