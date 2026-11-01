#!/usr/bin/env python3
"""
tools/build_fixtures.py -- THE MEASUREMENTS THE CHECKS READ, AS DATA.

**THE DEFECT THIS FIXES.** MEASURED 2026-11-01: a fresh clone of
far-writing ran its own suite and 4 of 79 checks FAILED -- because
they read `catalog/gutenberg/wikicache/`, and that directory is
GITIGNORED on purpose:

    catalog/gutenberg/.gitignore:
      wikicache/
      top.html

So the checks that guard the measurement could only run on the machine
that made the measurement. The commit carried the CHECKS and not the
DATA, and a commit that cannot run its own checks is not a commit
that can be verified by anyone but its author.

**THE RULE.** A check must not depend on an artifact that is not in
the repository. There are two ways to fix that and only one of them is
honest:

    (a) commit the artifact -- but the artifact is 178 MB of scraped
        third-party JSON and 60 MB of HTML, and the catalog's own
        `kind`/`license` fields are where the PROVENANCE belongs, not
        a copy of the corpus. That decision was made on purpose.

    (b) commit the PROJECT'S OWN MEASUREMENT -- the numbers this repo
        computed, derived from the corpus -- and have the checks read
        THAT. It is small, it is regenerable, and it is the thing the
        checks are actually about.

This is (b). The fixtures are:

    catalog/fixtures/reach_by_work.json      the per-work adaptation
        counts, keyed by `reach_key` -- 92 KB, the corrected count
    catalog/fixtures/reach_by_author.json    the per-author totals
        -- 28 KB
    catalog/fixtures/gutenberg_books.json    the 115 top books with
        their download counts -- 10 KB
    catalog/fixtures/old_counts.json     the OLD row count per
        work label, which is what E3 compares the corrected count
        against -- 65 KB

**AND THE DERIVATION IS DOCUMENTED, NOT ASSUMED.** Each fixture file
carries a `_provenance` block naming the tool that made it, the date,
and the measurement it holds. A fixture with no provenance is a
number with no command, which is the thing this project refuses.

**AND THE FIXTURES ARE ALSO A THIRD SOURCE.** The reach table, the
Gutenberg ranking and the old row counts all come from ONE place --
the measurement -- and the fixtures are the measurement's own output.
So a check that reads a fixture is reading the measurement, not a
hand-written number.

Run:  python tools/build_fixtures.py
      python tools/build_fixtures.py --check
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CATALOG = os.path.join(REPO, "catalog")
GUT_DIR = os.path.join(CATALOG, "gutenberg")
CACHE = os.path.join(GUT_DIR, "wikicache")
FIX_DIR = os.path.join(CATALOG, "fixtures")

sys.path.insert(0, os.path.join(REPO, "tools"))

#: WHEN THESE FIXTURES WERE DERIVED. A fixture without a date cannot
#: be compared against a measurement taken later.
DERIVED = "2026-10-31"

#: THE PROVENANCE, and it names the tool that made each thing.
PROVENANCE = {
    "reach_by_work.json": {
        "made_by": "tools/reach_measure.py --measure",
        "measures": "the per-work count of DISTINCT adaptations",
        "query": "COUNT(DISTINCT ?adapt), where ?adapt (wdt:P144|wdt:P1441) ?work",
        "note": "the corrected count. the OLD count is in old_counts.json",
    },
    "reach_by_author.json": {
        "made_by": "tools/reach_measure.py --measure",
        "measures": "the per-author total of DISTINCT adaptations",
        "note": "the authors the flood reached",
    },
    "gutenberg_books.json": {
        "made_by": "tools/gutenberg_ranks.py, from the Gutenberg top page",
        "measures": "the download count of the 115 top books",
        "source_url": "https://www.gutenberg.org/browse/scores/top",
        "note": "a DOWNLOAD count -- a reach measure, not copies sold",
    },
    "old_counts.json": {
        "made_by": "tools/build_fixtures.py, from the cached SPARQL rows",
        "measures": "the OLD row count per work label, before the "
                    "join-product correction",
        "note": "E3 compares the corrected count against this. the old "
                "count was rows, and every row was one (adaptation, "
                "work, date, author) tuple, so it held adaptations x "
                "dates x authors",
    },
    "reach_exhaustive_by_work.json": {
        "made_by": "tools/expand_works.py --apply, from the bounded "
                   "per-work query over the 260 authors the catalog holds",
        "measures": "the adaptation count of EVERY work of the authors "
                    "we hold, zero included",
        "query": "the bounded form of the by-work query, over the "
                 "catalog's own 260 authors",
        "note": "this is the table that makes a ZERO honest. the "
                "adaptation-driven query cannot tell 'no adaptations' "
                "from 'not looked for', and a zero written for the "
                "second case is a claim nobody made. 15,512 rows, of "
                "which 14,137 are a measured zero",
    },
}


def _write(name: str, payload: dict) -> str:
    os.makedirs(FIX_DIR, exist_ok=True)
    path = os.path.join(FIX_DIR, name)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=1, ensure_ascii=False)
    return path


def _derive_old_counts() -> dict:
    """the OLD count, recounted from the cached SPARQL rows.

    this is the measurement E3 needs: the corrected count must be
    SMALLER than the old row count, and must divide it, because the
    old count was the join product.
    """
    old = collections.Counter()
    if not os.path.isdir(CACHE):
        return {}
    for fn in os.listdir(CACHE):
        if not fn.startswith("sparql_adaptations"):
            continue
        try:
            with open(os.path.join(CACHE, fn), encoding="utf-8") as fh:
                data = json.load(fh)
        except Exception:  # noqa: BLE001
            continue
        for r in data.get("results", {}).get("bindings", []):
            t = r.get("workLabel", {}).get("value", "")
            if t:
                old[t] += 1
    return dict(old)


def _exhaustive_counts() -> dict:
    """the exhaustive per-work table, from the cache.

    this is the table that makes a zero honest: it holds EVERY work of
    the authors we hold, with its adaptation count, zero included. So
    a count of zero in the catalog is a MEASURED zero and not an
    absence.
    """
    path = os.path.join(CACHE, "reach_exhaustive_by_work.json")
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, encoding="utf-8") as fh:
            raw = json.load(fh)
    except Exception:  # noqa: BLE001
        return {}
    return {str(k): int(v) for k, v in raw.items()}


def _raw_book_rows() -> list:
    """the book's raw anchor rows, from the cached page.

    **AND THE ROWS ARE DEDUPED, AND THE FIRST OCCURRENCE WINS.** The
    page holds the top list three times over -- once for last week,
    once for last month, once for all time -- so the same ebook id
    appears up to 3 times with 3 different counts. MEASURED: 300 raw
    rows, 115 distinct ids, and 99 of those ids carry different
    counts on their repeats.

    So the fixture holds the FIRST occurrence of each id, which is the
    "last 30 days" column -- the same one `parse_books()` takes, since
    it also keeps the first occurrence. MEASURED: the first-occurrence
    rows parse to exactly the 115 books the committed fixture already
    holds, title for title and count for count, 0 differences.
    """
    page = os.path.join(GUT_DIR, "top.html")
    if not os.path.isfile(page):
        return []
    import gutenberg_ranks
    with open(page, encoding="utf-8") as fh:
        html = fh.read()
    rows = []
    seen = set()
    for eid, anchor, dl in gutenberg_ranks.BOOK_ROW.findall(html):
        if eid in seen:
            continue
        seen.add(eid)
        rows.append({"ebook_id": eid, "anchor": anchor, "downloads": dl})
    return rows


def _raw_author_rows() -> list:
    """the author's raw rows, from the cached page.

    Same rule as the books: the first occurrence of each name wins.
    """
    page = os.path.join(GUT_DIR, "top.html")
    if not os.path.isfile(page):
        return []
    import gutenberg_ranks
    with open(page, encoding="utf-8") as fh:
        html = fh.read()
    rows = []
    seen = set()
    for name, dl in gutenberg_ranks.AUTHOR_ROW.findall(html):
        if name in seen:
            continue
        seen.add(name)
        rows.append({"author": name, "downloads": dl})
    return rows


def build() -> int:
    import gutenberg_ranks
    import reach_measure as rm

    # 1. THE REACH TABLES.
    by_work = rm.load_reach()
    by_author = rm.load_author_reach()
    if not by_work:
        print("  the reach table is not on disk -- run "
              "tools/reach_measure.py --measure first")
        return 1
    _write("reach_by_work.json", {
        "_provenance": dict(PROVENANCE["reach_by_work.json"],
                            derived=DERIVED,
                            works=len(by_work)),
        "counts": by_work,
    })
    _write("reach_by_author.json", {
        "_provenance": dict(PROVENANCE["reach_by_author.json"],
                            derived=DERIVED,
                            authors=len(by_author)),
        "counts": by_author,
    })

    # 2. THE GUTENBERG BOOKS. The parser runs over the cached page, and
    #    the RESULT is what the checks need -- the title, the author
    #    and the download count, already split.
    #
    #    **AND WHAT IS COMMITTED IS THE RAW ROW, NOT THE SPLIT PAIR.**
    #    MEASURED 2026-11-01: the first version of this fixture held
    #    the books already split into title and author. That made the
    #    loader able to hand them back without calling the splitter at
    #    all, and the E2 mutation -- "the Gutenberg title keeps its
    #    author" -- then stayed GREEN: the check could not see a change
    #    to code that nothing on the default path called.
    #
    #    A fixture that holds the ANSWER cannot check the answer. So
    #    the fixture holds the measurement as it was OBSERVED -- the
    #    anchor text and the count -- and the parse is the loader's
    #    job. The raw rows come from the cached page, and the page is
    #    the only place they exist, so this is the one build step that
    #    genuinely needs the cache.
    books, authors = gutenberg_ranks.load()
    page_rows = _raw_book_rows()
    page_authors = _raw_author_rows()
    if not page_rows or not page_authors:
        print("  the cached page is not there -- the raw rows cannot be "
              "derived (run tools/gutenberg_ranks.py --fetch)")
        return 1
    _write("gutenberg_books.json", {
        "_provenance": dict(PROVENANCE["gutenberg_books.json"],
                            derived=DERIVED,
                            books=len(books),
                            authors=len(authors),
                            raw_rows=len(page_rows)),
        "books": page_rows,
        "authors": page_authors,
    })

    # 3. THE OLD ROW COUNTS, which E3 compares against.
    old = _derive_old_counts()
    if not old:
        print("  the old SPARQL rows are not cached -- the old row count "
              "cannot be derived")
        return 1
    _write("old_counts.json", {
        "_provenance": dict(PROVENANCE["old_counts.json"],
                            derived=DERIVED,
                            work_labels=len(old),
                            rows=sum(old.values())),
        "counts": old,
    })

    # 4. THE EXHAUSTIVE TABLE, which is what makes a zero honest.
    #    MEASURED 2026-11-01: C14 checks every reach count in the
    #    catalog against this table, and the table was in the
    #    gitignored cache -- so a fresh clone could not run C14.
    exh = _exhaustive_counts()
    if not exh:
        print("  the exhaustive table is not cached -- run "
              "tools/expand_works.py --apply first")
        return 1
    _write("reach_exhaustive_by_work.json", {
        "_provenance": dict(PROVENANCE["reach_exhaustive_by_work.json"],
                            derived=DERIVED,
                            works=len(exh),
                            measured_zeros=sum(1 for v in exh.values()
                                               if v == 0)),
        "counts": exh,
    })

    print("=" * 78)
    print("THE FIXTURES")
    print("=" * 78)
    for name in sorted(PROVENANCE):
        p = os.path.join(FIX_DIR, name)
        if os.path.isfile(p):
            print("  %-28s %8d bytes" % (name, os.path.getsize(p)))
    print()
    print("  these are the PROJECT'S OWN MEASUREMENTS, derived from the")
    print("  corpus and committed. the corpus itself stays out of the")
    print("  repository -- 178 MB of scraped JSON does not belong in a")
    print("  history, and the provenance belongs in the catalog's own")
    print("  fields.")
    return 0


def check() -> int:
    """every fixture is present, and carries its provenance."""
    bad = []
    for name, prov in sorted(PROVENANCE.items()):
        p = os.path.join(FIX_DIR, name)
        if not os.path.isfile(p):
            bad.append("%s is missing" % name)
            continue
        with open(p, encoding="utf-8") as fh:
            data = json.load(fh)
        if "_provenance" not in data:
            bad.append("%s carries no provenance" % name)
            continue
        pv = data["_provenance"]
        if pv.get("made_by") != prov["made_by"]:
            bad.append("%s names the wrong tool" % name)
    if bad:
        print("  the fixtures are wrong:")
        for b in bad:
            print("    - %s" % b)
        return 1
    print("  every fixture is present and carries its provenance")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="build the committed fixtures")
    ap.add_argument("--check", action="store_true",
                    help="check the fixtures are present and carry provenance")
    args = ap.parse_args()
    if args.check:
        return check()
    return build()


if __name__ == "__main__":
    sys.exit(main())
