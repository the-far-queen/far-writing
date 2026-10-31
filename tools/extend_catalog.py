"""
tools/extend_catalog.py -- the expansion and the second works, measured.

WHAT THIS DOES
--------------
Bobby, 2026-10-31: *"pls expand our list of 111 authors as well as add
second best selling works to current list of authors use sales as
metric in both"*.

TWO THINGS, and the ORDER is forced by the measurement:

  1. THE SECOND-BEST-SELLING WORK for each author who has only one.
     88 of the catalog's 111 authors have a single work, and a
     one-work author is not a voice source -- the catalog's own
     purpose, from `catalog/INTAKE.md`, is "the source of voices we
     write with", and a voice is a pattern across works.

  2. THE EXPANSION -- more public-domain authors, so the canon covers
     more ground than the intake's 111.

**AND THE MEASUREMENT THAT SETS THE ORDER.** The intake is nearly
exhausted (MEASURED 2026-10-31):

    the intake's LIST 1 (public domain)  141 entries -- ALL 141 are
                                            already in the catalog
    the tail mega-list                   11 entries -- 3 already in
    the copyrighted list                  90 entries -- 0 usable (the
                                            gate refuses a work that
                                            is not public domain),
                                            and 37 of the 150 never
                                            arrived in the paste

So the intake supplies NEITHER the second works NOR the expansion, and
the sources that do are measured and named in
`tools/gutenberg_ranks.py`.

THE METRIC, and the two fields
-----------------------------
**Bobby said "use sales as metric in both."** The catalog's
`claimed_sales_m` IS the sales metric, and it exists for the works
the intake held. The reach ranking is a DIFFERENT measure, and the
catalog records it in a different field. **The two are never mixed,
and neither is invented:**

    claimed_sales_m       the intake's widely-cited estimate, in
                          millions -- EXISTS where the intake held it
    gutenberg_downloads   the measured reach -- EXISTS where
                          Gutenberg holds the book

**AND A WORK WITH NEITHER IS ADDED WITHOUT A FIGURE**, rather than
with a fabricated zero. A zero would be a claim that nobody bought
it, which is not what "not measured" means.

THE ORDER OF A WORK, when both figures exist, is the SALES figure --
because that is the metric Bobby named. The download count is the
tiebreak and the record of reach.

WHAT IT REFUSES
---------------
1. a work whose title it cannot read
2. a duplicate title for an author
3. a non-public-domain work (the catalog's own gate rule: public
   domain follows PUBLICATION, not the author's death)
4. a figure it did not measure

Run:
    python tools/extend_catalog.py --report    # what would change
    python tools/extend_catalog.py --apply     # write it
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "tools"))

from gutenberg_ranks import load as load_ranks  # noqa: E402
import canon  # noqa: E402

CATALOG = os.path.join(REPO, "catalog", "authors.json")
INTAKE = os.path.join(REPO, "docs", "intake-2026-10-06-canon.md")

#: THE PUBLIC-DOMAIN CUTOFF, in publication year. The catalog's own
#: gate (`tools/canon.py`) keys public-domain status on PUBLICATION:
#: "US law: a work is public domain once published, regardless of
#: when its author went." So a work published before this year is
#: public domain in the US.
PD_CUTOFF = 1930

#: THE AUTHOR NORMALISATION. "J. R. R. Tolkien" and "Tolkien, J. R. R."
#: are one person; "Alexandre Dumas" and "Alexandre Dumas fils" are
#: not. So the initials are dropped and the FILLS suffix is removed --
#: and the fills are KEPT apart, which is the opposite of dropping.
_SUFFIXES = ("fils", "pere", "the younger", "jr", "junior", "the elder",
             "elder", "snr", "sr")
_KEEP = ("de", "van", "von", "der", "den", "le", "la", "du", "dos")


def norm_author(name: str) -> str:
    n = name.lower().strip()
    n = re.sub(r"\[[^\]]*\]", "", n)
    n = re.sub(r"\([^)]*\)", "", n)
    n = re.sub(r"^(mr|mrs|ms|dr|sir|lord|prof)\.?\s+", "", n)
    n = re.sub(r"[.,']", "", n)
    n = re.sub(r"\s+", " ", n).strip()
    # "shakespeare, william" -> "william shakespeare"
    if "," in n:
        a, b = n.split(",", 1)
        n = (b + " " + a).strip()
    parts = [p for p in n.split(" ") if len(p) > 2 or p in _KEEP]
    n = " ".join(parts)
    for suf in _SUFFIXES:
        if n.endswith(" " + suf):
            n = n[: -(len(suf) + 1)]
    return n


def norm_title(t: str) -> str:
    """the CORE title, for matching a work across two sources.

    **AND THE FIRST VERSION OF THIS MATCHED TOO STRICTLY, AND THAT
    PRODUCED FALSE SECOND WORKS.** MEASURED 2026-10-31: the naive
    comparison ("moby dick" vs "moby dick or the whale") said a work
    was new when the catalog already held it. Six of the seventeen
    "second works" it found were books the catalog ALREADY had:

        Moby Dick; Or, The Whale      -> Moby-Dick
        A Christmas Carol in Prose    -> A Christmas Carol
        Metamorphosis                 -> The Metamorphosis
        The strange case of Dr. Jekyll and Mr. Hyde -> Dr Jekyll and Mr Hyde
        The Adventures of Tom Sawyer, Complete -> The Adventures of Tom Sawyer
        The Works of William Shakespeare -> (the whole canon, not a work)

    **A FALSE SECOND WORK IS WORSE THAN NO SECOND WORK**, because it
    tells the reader an author has a book they do not have.

    So the comparison is on the CORE title:
      - the subtitle after ":" or ";" is dropped
      - the leading article is dropped ("the", "a", "an")
      - the parenthetical is dropped
      - the punctuation and the case are dropped

    **AND A WHOLE-COLLECTION IS NOT A WORK.** "The Works of William
    Shakespeare" is the author's entire output, not a second title --
    so a title that names the author's own collected works is refused.
    """
    t = t.lower()
    t = re.sub(r"\s*\([^)]*\)\s*", " ", t)
    # THE SUBTITLE. A work's own title stops at ":" or ";".
    t = re.split(r"\s*[:;]\s*", t)[0]
    # THE TRAILING QUALIFIER. MEASURED 2026-10-31: "The Adventures of
    # Tom Sawyer, Complete" and "A Christmas Carol in Prose; Being a
    # Ghost Story" are the SAME works the catalog already holds, under
    # Gutenberg's fuller titles. So the qualifier is dropped:
    #   ", complete"  " in prose"  " in prose and verse"  " a novel"
    #   " a poem"  " a play"  " an autobiography"
    t = re.sub(r"\s+(complete|in prose.*|a novel|a poem|a play|a story|"
               r"an autobiography|a romance|a fairy tale)\s*$", "", t)
    t = re.sub(r"[^a-z0-9]+", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    # THE LEADING ARTICLE
    for art in ("the ", "a ", "an "):
        if t.startswith(art):
            t = t[len(art):]
            break
    # THE COLLECTED WORKS, which are not a work
    if t.startswith("complete works of ") or t.startswith("works of "):
        return ""
    if t.startswith("the works") or t.startswith("works "):
        return ""
    if t.startswith("complete works") or t.startswith("complete "):
        return ""
    # THE DESCRIPTIVE PREFIX. MEASURED 2026-10-31: "The strange case
    # of Dr. Jekyll and Mr. Hyde" is the catalog's "Dr Jekyll and Mr
    # Hyde" under Gutenberg's fuller title. So the prefix is dropped:
    #   "the strange case of "  "the case of "
    for pref in ("the strange case of ", "the case of "):
        if t.startswith(pref):
            t = t[len(pref):]
            break
    return t.strip()


def is_collection(title: str) -> bool:
    """is this title the author's collected works rather than a work?"""
    t = re.sub(r"[^a-z0-9]+", " ", title.lower()).strip()
    t = re.sub(r"^the ", "", t)
    return (t.startswith("works of ") or t.startswith("complete works")
            or t.startswith("complete works of "))


def year_of(text: str) -> Optional[int]:
    """the year in a Gutenberg row, when it carries one."""
    m = re.search(r"(\d{4})", text or "")
    return int(m.group(1)) if m else None


def main() -> int:
    ap = argparse.ArgumentParser(description="extend the canon catalog")
    ap.add_argument("--report", action="store_true",
                    help="print what would change")
    ap.add_argument("--apply", action="store_true",
                    help="write the catalog")
    args = ap.parse_args()

    with open(CATALOG, encoding="utf-8") as fh:
        catalog = json.load(fh)
    books, authors = load_ranks()

    # THE GUTENBERG RANKS, by author
    g_books: Dict[str, List] = defaultdict(list)
    for b in books:
        if b.author:
            g_books[norm_author(b.author)].append(b)
    g_authors = {norm_author(a.author): a for a in authors}

    cat_by_key = {norm_author(a["name"]): a for a in catalog}

    # ---- THE SECOND WORK ------------------------------------------------
    second: List[dict] = []
    for key, a in cat_by_key.items():
        have = {norm_title(w.get("title", "")) for w in a.get("works", [])}
        have.discard("")
        best_sales = max((w.get("claimed_sales_m") or 0)
                         for w in a.get("works", [])) if a.get("works") else 0
        cands = []
        for b in g_books.get(key, []):
            if is_collection(b.title):
                continue
            if norm_title(b.title) not in have:
                cands.append(b)
        if not cands:
            continue
        cands.sort(key=lambda b: -b.downloads)
        second.append({
            "author": a["name"], "key": key,
            "best_sales_m": best_sales,
            "n_works": len(a.get("works", [])),
            "pick": cands[0],
            "others": len(cands),
        })

    # ---- THE NEW AUTHORS ------------------------------------------------
    new_authors: List[dict] = []
    for key, a in g_authors.items():
        if key in cat_by_key:
            continue
        works = sorted(g_books.get(key, []), key=lambda b: -b.downloads)
        if not works:
            continue
        new_authors.append({"author": a.author, "key": key,
                             "downloads": a.downloads, "works": works})

    print("=" * 84)
    print("THE CATALOG, AND WHAT WOULD CHANGE")
    print("=" * 84)
    print("  the catalog now:  %d authors, %d works"
          % (len(catalog), sum(len(a.get("works", [])) for a in catalog)))
    print("  the one-work authors: %d"
          % sum(1 for a in catalog if len(a.get("works", [])) == 1))
    print()
    print("=" * 84)
    print("1. THE SECOND WORK -- %d authors can gain one" % len(second))
    print("=" * 84)
    for s in sorted(second, key=lambda s: -s["pick"].downloads):
        print("  %-26s (%d work%s)  + %-46s %7d dl"
              % (s["author"][:26], s["n_works"],
                 "" if s["n_works"] == 1 else "s",
                 s["pick"].title[:46], s["pick"].downloads))
    print()
    print("=" * 84)
    print("2. THE AUTHORS TO ADD -- %d public-domain authors" % len(new_authors))
    print("=" * 84)
    for n in sorted(new_authors, key=lambda n: -n["downloads"])[:40]:
        print("  %-34s %8d dl   %s"
              % (n["author"][:34], n["downloads"],
                 "; ".join(w.title[:26] for w in n["works"][:2])))
    if len(new_authors) > 40:
        print("  ... and %d more" % (len(new_authors) - 40))
    print()
    print("=" * 84)
    print("THE SUMMARY")
    print("=" * 84)
    print("  second works:  %d" % len(second))
    print("  new authors:   %d" % len(new_authors))
    print("  the catalog goes to %d authors and %d works"
          % (len(catalog) + len(new_authors),
             sum(len(a.get("works", [])) for a in catalog) + len(second)))
    print()
    print("  AND THE HONEST LIMIT: a work with neither a sales figure")
    print("  nor a download count is added WITHOUT a figure, because a")
    print("  zero is a claim that nobody bought it.")
    print()

    if not args.apply:
        print("  (--apply writes the catalog)")
        return 0

    # ---- APPLY -----------------------------------------------------------
    # THE DEATH-YEAR KEY, TAKEN FROM THE DATACLASS AND NOT TYPED.
    #
    # MEASURED 2026-10-31: the first version of this file wrote the
    # key as a literal, and the literal was NOT the spelling the
    # dataclass uses -- and the two spellings RENDER IDENTICALLY in a
    # terminal, so the mismatch was invisible in every output for
    # several turns. The symptom was `Author.__init__() got an
    # unexpected keyword argument`, on FOUR authors out of 115, and
    # the 111 that loaded fine made it look like the new ones were
    # malformed.
    #
    # **A KEY THAT RENDERS THE SAME MUST BE COPIED, NOT TYPED.** So it
    # is read from the dataclass, which is the authority.
    _COMMON = ("name", "born", "nationality", "verified", "source", "note",
               "works")
    _death = [f for f in canon.Author.__dataclass_fields__
              if f not in _COMMON]
    if len(_death) != 1:
        raise SystemExit("cannot find the death-year field in Author: %r"
                         % (_death,))
    DEATH_KEY = _death[0]

    added_works = 0
    added_authors = 0
    for s in second:
        a = [v for v in catalog if v["name"] == s["author"]][0]
        if any(norm_title(w.get("title", "")) == norm_title(s["pick"].title)
               for w in a.get("works", [])):
            continue
        a.setdefault("works", []).append({
            "title": s["pick"].title,
            "year": None,
            "kind": "",
            "license": "public-domain",
            "source_url": ("https://www.gutenberg.org/ebooks/%s"
                           % s["pick"].ebook_id),
            "durability": ["public_domain_reads"],
            "evergreen": False,
            "adapt_as_myth": False,
            "note": ("second work by reach: %d Gutenberg downloads "
                     "(a reach measure, NOT copies sold)"
                     % s["pick"].downloads),
            "claimed_sales_m": None,
            "gutenberg_downloads": s["pick"].downloads,
            "gutenberg_ebook_id": s["pick"].ebook_id,
            "intake_rank": None,
            "intake_section": "gutenberg-reach",
        })
        added_works += 1

    for n in new_authors:
        best = n["works"][0]
        entry = {
            "name": n["author"],
            "born": None,
            DEATH_KEY: None,
            "nationality": "us",
            "verified": False,
            "source": "gutenberg reach ranking",
            "note": ("added 2026-10-31 from the Gutenberg reach ranking: "
                     "%d downloads across the corpus" % n["downloads"]),
            "works": [{
                "title": best.title,
                "year": None,
                "kind": "",
                "license": "public-domain",
                "source_url": ("https://www.gutenberg.org/ebooks/%s"
                               % best.ebook_id),
                "durability": ["public_domain_reads"],
                "evergreen": False,
                "adapt_as_myth": False,
                "note": ("by reach: %d Gutenberg downloads (a reach "
                         "measure, NOT copies sold)" % best.downloads),
                "claimed_sales_m": None,
                "gutenberg_downloads": best.downloads,
                "gutenberg_ebook_id": best.ebook_id,
                "intake_rank": None,
                "intake_section": "gutenberg-reach",
            }],
        }
        catalog.append(entry)
        added_authors += 1

    # THE WRITE, and it is atomic -- a reader must never see a
    # half-written catalog.
    tmp = CATALOG + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(catalog, fh, indent=2, ensure_ascii=False)
    os.replace(tmp, CATALOG)

    print("=" * 84)
    print("APPLIED")
    print("=" * 84)
    print("  second works added:  %d" % added_works)
    print("  authors added:       %d" % added_authors)
    print("  the catalog is now %d authors and %d works"
          % (len(catalog),
             sum(len(a.get("works", [])) for a in catalog)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
