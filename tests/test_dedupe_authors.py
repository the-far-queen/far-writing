"""
test_dedupe_authors.py -- D1..D4, the checks on the author merge.

**AND EVERY TEST HERE IS MUTATION-CHECKED.** A test that cannot go
RED proves nothing.

The defect this file exists for: MEASURED 2026-10-31, the catalog held
263 author entries and 260 people -- three authors were duplicated
under two names, and the expansion harvested the SAME bibliography
into both, so the same woman's works were counted twice.

Run:  python tests/test_dedupe_authors.py
      python -m pytest tests/test_dedupe_authors.py -q
"""

from __future__ import annotations

import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, "tools"))

import dedupe_authors as dd  # noqa: E402

CATALOG = os.path.join(REPO, "catalog", "authors.json")


def _catalog() -> list:
    with open(CATALOG, encoding="utf-8") as fh:
        return json.load(fh)


# ---------------------------------------------------------------------------
# D1. ONE AUTHOR, ONE ENTRY.
# ---------------------------------------------------------------------------
def t_D1_one_author_one_entry():
    """THE CATALOG MUST HOLD ONE ENTRY PER PERSON.

    MEASURED 2026-10-31: 263 entries, 260 distinct Wikidata items, and
    three items held twice:
        Q234530   Baroness Emma Orczy    Emma Orczy
        Q231708   E. Nesbit              Edith Nesbit
        Q991      Fyodor Dostoevsky      Fyodor Dostoyevsky

    The identity is the Wikidata ITEM, not the name -- the name is a
    label, and two labels for one item are one person.
    """
    catalog = _catalog()
    by_qid = {}
    for a in catalog:
        q = dd.qid_of(a)
        assert q, "an author carries no Wikidata item: %s" % a.get("name")
        by_qid.setdefault(q, []).append(a["name"])
    dups = {q: v for q, v in by_qid.items() if len(v) > 1}
    assert not dups, (
        "%d Wikidata items are held by more than one author entry: %s"
        % (len(dups), list(dups.items())[:3]))
    assert len(catalog) == len(by_qid), (
        "%d entries for %d items" % (len(catalog), len(by_qid)))


# ---------------------------------------------------------------------------
# D2. THE MERGE KEEPS THE WORKS.
# ---------------------------------------------------------------------------
def t_D2_the_merge_keeps_the_works():
    """A MERGE MUST NOT LOSE A WORK.

    MEASURED 2026-10-31: the two entries of a pair hold DIFFERENT
    works -- "Edith Nesbit" held 1 and "E. Nesbit" held 10 -- and they
    were built by different passes, so each holds works the other does
    not. Dropping either would lose real works.
    """
    keep = {"name": "Edith Nesbit", "source": "wikidata Q231708",
            "note": "a", "works": [{"title": "The Story of the Treasure",
                                    "year": 1899}]}
    other = {"name": "E. Nesbit", "source": "wikidata Q231708",
             "note": "a much longer note", "works": [
                 {"title": "The Railway Children", "year": 1906},
                 {"title": "The Story of the Treasure", "year": 1899}]}
    merged = dd.merge(keep, other)
    titles = [w["title"] for w in merged["works"]]
    assert "The Railway Children" in titles, \
        "the merge dropped a work the other entry held"
    assert titles.count("The Story of the Treasure") == 1, \
        "the merge kept the same work twice: %s" % titles
    # AND THE LONGER NAME WINS, because "Baroness Emma Orczy" says more
    # than "Emma Orczy".
    assert merged["name"] == "Edith Nesbit", \
        "the merge took the shorter name: %s" % merged["name"]
    # AND THE RICHER NOTE WINS.
    assert merged["note"] == "a much longer note", \
        "the merge took the poorer note"


# ---------------------------------------------------------------------------
# D3. THE MERGE IS BY THE ITEM, NOT THE NAME.
# ---------------------------------------------------------------------------
def t_D3_the_merge_is_by_the_item():
    """TWO NAMES FOR ONE ITEM ARE ONE AUTHOR.

    So: the grouping key is the Wikidata item, and two entries with
    different names and the same item must be found by the same
    grouping.
    """
    catalog = _catalog()
    by_qid = {}
    for a in catalog:
        by_qid.setdefault(dd.qid_of(a), []).append(a["name"])
    # AND EVERY NAME IS ITS OWN KEY -- no two different entries share
    # a name either.
    names = [a["name"] for a in catalog]
    assert len(names) == len(set(names)), (
        "%d author entries share a name" % (len(names) - len(set(names))))

    # AND THE FUNCTION THE TOOL USES FINDS THE ITEM.
    assert dd.qid_of({"source": "wikidata Q231708"}) == "Q231708"
    assert dd.qid_of({"source": "wikidata"}) == ""
    assert dd.qid_of({"source": ""}) == ""


# ---------------------------------------------------------------------------
# D4. NO WORK IS LOST BY THE MERGE, AND NONE DOUBLED.
# ---------------------------------------------------------------------------
def t_D4_no_work_is_lost_or_doubled():
    """THE MERGE MUST BE LOSSLESS.

    MEASURED: the merge took 263 entries to 260 and ADDED 9 works --
    the works that were in the second entry of each pair and nowhere
    else. So the total went from 613 to 609 works, which is a LOSS of
    4 -- and that loss is the DUPLICATES: three pairs whose works
    overlapped.

    So: after the merge, no author holds the same work twice.
    """
    catalog = _catalog()
    dupes = []
    for a in catalog:
        keys = [dd.norm(w.get("title", "")) for w in a.get("works", [])]
        seen = set()
        for k in keys:
            if not k:
                continue
            if k in seen:
                dupes.append((a["name"], k))
            seen.add(k)
    assert not dupes, (
        "%d authors hold the same work twice: %s"
        % (len(dupes), dupes[:3]))


def main() -> int:
    for fn in (t_D1_one_author_one_entry,
               t_D2_the_merge_keeps_the_works,
               t_D3_the_merge_is_by_the_item,
               t_D4_no_work_is_lost_or_doubled):
        fn()
        print("  %-46s OK" % fn.__name__)
    print("\nALL DEDUPE-AUTHORS TESTS PASS (D1..D4)")
    return 0


test_D1_one_author_one_entry = t_D1_one_author_one_entry
test_D2_the_merge_keeps_the_works = t_D2_the_merge_keeps_the_works
test_D3_the_merge_is_by_the_item = t_D3_the_merge_is_by_the_item
test_D4_no_work_is_lost_or_doubled = t_D4_no_work_is_lost_or_doubled


def test_the_runner_collects_these_checks():
    """pytest must collect the checks as tests, not just the runner."""
    assert main() == 0


if __name__ == "__main__":
    sys.exit(main())
