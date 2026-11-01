"""
tools/gutenberg_ranks.py -- the per-book and per-author reach ranking.

WHAT THIS IS
------------
Bobby, 2026-10-31: *"pls expand our list of 111 authors as well as
add second best selling works to current list of authors use sales as
metric in both"*.

**AND THE MEASUREMENT THAT DECIDED HOW THIS IS BUILT.** The intake
(Bobby + Grok, 2026-10-06) holds 242 entries for 188 authors, and the
catalog took 111 of them. MEASURED 2026-10-31:

    the intake's LIST 1 (public domain)  141 entries -- ALL 141 already
                                            in the catalog
    the tail mega-list                   11 entries -- 3 already in
    the copyrighted list (LIST 2)         90 entries -- 0 usable, the
                                            catalog's gate refuses a
                                            work that is not public
                                            domain, and 37 of the
                                            150 never arrived in the
                                            paste at all (numbers
                                            76-95, 98-110, 126-128,
                                            130)

So **the intake cannot supply the expansion or the second works.** And
the per-book figures it does hold are the BEST work per author, so an
author's SECOND book is not in it either.

Wikipedia was tried and MEASURED, and it is the wrong instrument for
this corpus:

    "List of best-selling books"        63 rows parsed, 58 authors --
                                          only 8 of them are the
                                          catalog's authors, because
                                          a modern best-seller list
                                          ranks what sells NOW
    "List of literary works by number
     of translations"                 100 rows -- 12 of the catalog's
                                          authors; a per-BOOK reach
                                          measure, which is right for
                                          the pre-1950 canon but
                                          does not cover the canon's
                                          authors either

**AND THE SOURCE THAT DOES COVER IT IS PROJECT GUTENBERG'S OWN
RANKING.** It is per-book AND per-author, it is over exactly the
public-domain canon the catalog holds, and it is the corpus we can
actually fetch from. MEASURED 2026-10-31:

    300 books, 288 with an author parsed
    300 author entries, ranked by total downloads
    30 of the catalog's 111 authors appear, and 17 can gain a work

**AND IT IS NOT SALES, AND THE MODULE SAYS SO.** Gutenberg's own note
on the page reads: *"Calculated from the number of times each eBook
gets downloaded."* Downloads are a reach measure, not copies sold.

So the catalog gains TWO fields, each labelled for what it is:

    claimed_sales_m       the intake's widely-cited estimate, in
                          millions. EXISTS for the works the intake
                          held. The ranking metric Bobby asked for.
    gutenberg_downloads   the measured reach, per book and per author.
                          EXISTS for the works Gutenberg holds.

**AND THE TWO ARE NEVER MIXED.** The sales figure ranks where it
exists; the download count fills the second slot where it exists; and
an entry with neither is not given a fabricated number. The catalog's
INTAKE.md already says the rule for the sales figures: *"widely-cited
estimates... used for ordering only. No entry claims them as audited
numbers."* The same rule applies here.

WHAT IT REFUSES
---------------
1. a work whose title or author it cannot read
2. a figure it did not measure (no invented zeros)
3. a claim that a download count is a sales figure

Run:
    python tools/gutenberg_ranks.py --fetch     # fetch and cache
    python tools/gutenberg_ranks.py --report    # the tables
    python tools/gutenberg_ranks.py --json      # machine-readable
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE_DIR = os.path.join(REPO, "catalog", "gutenberg")
BOOKS_CACHE = os.path.join(CACHE_DIR, "top.html")

#: THE COMMITTED FIXTURE. **THE PAGE IS GITIGNORED** --
#: `catalog/gutenberg/.gitignore` excludes `top.html` -- and MEASURED
#: 2026-11-01: a fresh clone had no page, and the checks that read the
#: download counts FAILED there. So the loader falls back to the
#: PARSED result, which is committed and carries its provenance.
#:
#: The page is 60 KB of HTML and the parsed books are 23 KB of JSON,
#: and the parsed form is what the checks are about -- the title, the
#: author, and the count, already split.
FIXTURE = os.path.join(REPO, "catalog", "fixtures", "gutenberg_books.json")

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
      "far-writing-canon-gutenberg/1.0")

TOP_URL = "https://www.gutenberg.org/browse/scores/top"

#: THE BOOK ROW. MEASURED from the real page:
#:
#:     href="/ebooks/84">Frankenstein; or, The modern Prometheus by
#:       Mary Wollstonecraft Shelley (7904)</a>
#:
#: So the DOWNLOAD COUNT IS INSIDE THE ANCHOR TEXT, not after it. The
#: first version of this pattern expected it after the tag and matched
#: ZERO rows -- and reported zero without erroring.
BOOK_ROW = re.compile(
    r'href="/ebooks/(\d+)">(.+?)\s*\((\d[\d,]*)\)</a>', re.S)

#: THE AUTHOR ROW. MEASURED:
#:
#:     href="/browse/authors/s#a65">Shakespeare, William (18238)</a>
AUTHOR_ROW = re.compile(
    r'href="/browse/authors/[^"]+">([^<]+?)\s*\((\d[\d,]*)\)</a>')

#: A TITLE AND ITS AUTHOR. The page writes "Title by Author", and the
#: split is on the LAST " by " -- because a title can contain one
#: ("The Castle by O. Henry" is fine, but "Billy by the Sea" is not).
#:
#: **AND THE REGEX NOW MATCHES THE CONTRACT IT STATES.** MEASURED
#: 2026-11-01: the pattern was `^(.*?)\s+by\s+(.*)$` -- a LAZY first
#: group, so it split on the FIRST " by " while the comment above
#: promised the LAST one. MEASURED on the two cases that tell them
#: apart:
#:
#:     "Billy by the Sea by Jack London"
#:         the lazy pattern   -> ("Billy", "the Sea by Jack London")
#:         the greedy pattern -> ("Billy by the Sea", "Jack London")
#:
#: **AND THE PAGE ITSELF DID NOT CATCH IT.** MEASURED: of the 115
#: distinct book rows on the cached page, 0 hold a second " by ", so
#: both patterns split every row identically -- 0 rows differ. The
#: defect was invisible in the data and visible only in the contract.
#: A title of the catalog's own carries a " by " ("Poems by Currer,
#: Ellis, and Acton Bell"), so the shape is real; it just is not on
#: this page yet.
TITLE_AUTHOR = re.compile(r"^(.*)\s+by\s+(.*)$")


@dataclass
class BookRank:
    ebook_id: str
    title: str
    author: str
    downloads: int

    def to_dict(self) -> dict:
        return {"ebook_id": self.ebook_id, "title": self.title,
                "author": self.author, "downloads": self.downloads}


@dataclass
class AuthorRank:
    author: str
    downloads: int

    def to_dict(self) -> dict:
        return {"author": self.author, "downloads": self.downloads}


def fetch(url: str, dest: str) -> str:
    """fetch a page, and cache it."""
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=90) as fh:
                data = fh.read()
            with open(dest, "wb") as out:
                out.write(data)
            return dest
        except Exception as exc:  # noqa: BLE001
            if attempt == 3:
                raise
            sys.stderr.write("  fetch attempt %d failed (%s); waiting\n"
                             % (attempt + 1, exc))
            time.sleep(8 + attempt * 8)
    return dest


def clean(text: str) -> str:
    t = re.sub(r"<[^>]+>", "", text)
    t = t.replace("&amp;", "&").replace("&quot;", '"').replace("&#39;", "'")
    t = t.replace("&mdash;", "-").replace("&ndash;", "-")
    t = t.replace("&nbsp;", " ")
    return re.sub(r"\s+", " ", t).strip()


def split_title_author(text: str) -> Tuple[str, str]:
    """the title and the author, or the title and an empty author."""
    t = clean(text)
    m = TITLE_AUTHOR.match(t)
    if not m:
        return t, ""
    return m.group(1).strip(), m.group(2).strip()


def parse_book_rows(rows) -> List[BookRank]:
    """the books, from the RAW rows.

    **AND THE ROWS ARE THE RAW ANCHOR TEXT, NOT A SPLIT PAIR.** The
    split happens HERE, so it happens on every path -- the cached page
    and the committed fixture alike.

    **AND THIS EXISTS BECAUSE THE FIXTURE MADE THE SPLIT UNREACHABLE.**
    MEASURED 2026-11-01: the committed fixture held the books already
    split into title and author, so `load()` could hand them back
    without calling the splitter at all. The E2 mutation -- "the
    Gutenberg title keeps its author" -- then stayed GREEN: the check
    could not see the change, because nothing on the default path
    called the code it was about. MEASURED, with the mutation applied
    to a copy of the tree: the check passed with the fixture present
    and failed with the fixture taken away.

    So the fixture holds the RAW ROWS, and the parse is the loader's
    job. The measurement is committed; the reading of it is not.
    """
    out: List[BookRank] = []
    seen = set()
    for eid, anchor, dl in rows:
        t, a = split_title_author(anchor)
        if not t or eid in seen:
            continue
        seen.add(eid)
        out.append(BookRank(ebook_id=eid, title=t, author=a,
                            downloads=int(str(dl).replace(",", ""))))
    return out


def parse_author_rows(rows) -> List[AuthorRank]:
    """the authors, from the RAW rows.

    **AND THE ROWS ARE 3-WIDE, LIKE THE BOOK ROWS.** The book's row is
    (id, anchor, count); the author's is (name, name, count) -- the
    name stands in for both the key and the text, because the page's
    author anchor holds nothing but the name and the count.
    """
    out: List[AuthorRank] = []
    seen = set()
    for name, _text, dl in rows:
        n = clean(name)
        if not n or n in seen:
            continue
        seen.add(n)
        out.append(AuthorRank(author=n, downloads=int(str(dl).replace(",", ""))))
    return out


def parse_books(html: str) -> List[BookRank]:
    """the books, from a page."""
    return parse_book_rows(BOOK_ROW.findall(html))


def parse_authors(html: str) -> List[AuthorRank]:
    """the authors, from a page."""
    return parse_author_rows([(n, n, dl)
                              for n, dl in AUTHOR_ROW.findall(html)])


def load() -> Tuple[List[BookRank], List[AuthorRank]]:
    """the ranking, from the committed measurement.

    **AND THE FIXTURE IS THE AUTHORITY, NOT THE CACHE.** MEASURED
    2026-11-01, and this is the third defect in this family:

    1. the cache is gitignored, so a fresh clone had no page at all;
    2. the clone then FETCHED the page, and the live page is a MOVING
       TARGET -- it had 306 book rows against the fixture's 115
       parsed books, and 114 of the 115 fixture titles were absent from
       it. So the clone's ranking was a DIFFERENT MEASUREMENT from the
       working tree's, and the check that read it failed on two real
       titles -- Villette and Howards End, both of which ARE in the
       fixture.

    So a check that reads a LIVE page is not reproducible, and a
    check that is not reproducible is not a check. The committed
    fixture is the measurement; the page is only how the measurement
    was made.

    **SO THE ORDER IS: the fixture first, then the cache, and the
    fetch ONLY when the caller asks for it.** Nothing here reaches
    the network by default.

    **AND THE FIXTURE HOLDS THE RAW ROWS, NOT THE PARSED BOOKS.**
    MEASURED 2026-11-01, and this is the defect that the fixture
    commit introduced into its own fix: the fixture held the books
    already split into title and author, so this function could hand
    them back without calling `split_title_author()` at all. The E2
    mutation -- "the Gutenberg title keeps its author" -- then stayed
    GREEN, because the check could not see a change to code that
    nothing on this path called.

    A fixture that holds the ANSWER is a fixture that cannot check
    the answer. So the fixture holds the raw rows -- the anchor text
    and the count -- and the parse happens here, on every path, so
    the parser is always exercised and always measurable.
    """
    fixed = load_fixture()
    if fixed is not None:
        return fixed

    if os.path.isfile(BOOKS_CACHE):
        with open(BOOKS_CACHE, encoding="utf-8") as fh:
            html = fh.read()
        return parse_books(html), parse_authors(html)

    raise FileNotFoundError(
        "neither the committed fixture (%s) nor the cached page (%s) is "
        "there -- run tools/build_fixtures.py to derive the measurement"
        % (FIXTURE, BOOKS_CACHE))


def load_fixture() -> Optional[Tuple[List[BookRank], List[AuthorRank]]]:
    """the committed measurement, or None if it is not there.

    **AND THE ROWS ARE PARSED HERE, NOT STORED SPLIT.** See `load()`.
    """
    if not os.path.isfile(FIXTURE):
        return None
    try:
        with open(FIXTURE, encoding="utf-8") as fh:
            data = json.load(fh)
    except Exception:  # noqa: BLE001
        return None
    books = parse_book_rows(_rows(data, "books"))
    authors = parse_author_rows(_rows(data, "authors"))
    if not books:
        return None
    return books, authors


def _rows(data: dict, key: str):
    """the raw rows of a fixture section.

    **AND THE OLD FORM IS STILL READ, SO THE FIXTURE CAN BE MIGRATED
    WITHOUT A FLAG DAY.** MEASURED: the fixture that shipped on
    2026-11-01 held the books already split, as
    `{"ebook_id", "title", "author", "downloads"}`. The new form holds
    the raw rows, as `{"ebook_id", "anchor", "downloads"}`. A reader
    that understands both is what makes the change safe: the fixture
    can be rebuilt by the tool that owns it, and the old file keeps
    working until it does.
    """
    rows = []
    for entry in (data.get(key) or []):
        if "anchor" in entry:
            rows.append((entry.get("ebook_id", ""),
                         entry.get("anchor", ""),
                         entry.get("downloads", 0)))
        elif key == "authors":
            rows.append((entry.get("author", ""),
                         entry.get("author", ""),
                         entry.get("downloads", 0)))
        else:
            # THE OLD, PRE-SPLIT FORM: the anchor is rebuilt from the
            # pair, so the parse still runs and the splitter is still
            # exercised. It is a lossy rebuild -- the author's own " by "
            # cannot be told from the separator's -- but it is enough to
            # keep the check meaningful, and the rebuild is rebuilt from
            # the page by `tools/build_fixtures.py` at the next build.
            title = entry.get("title", "")
            author = entry.get("author", "")
            anchor = title + (" by " + author if author else "")
            rows.append((entry.get("ebook_id", ""), anchor,
                         entry.get("downloads", 0)))
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description="the Gutenberg ranking")
    ap.add_argument("--fetch", action="store_true",
                    help="fetch and cache the page")
    ap.add_argument("--report", action="store_true",
                    help="print the tables")
    ap.add_argument("--json", action="store_true",
                    help="write the machine-readable form")
    args = ap.parse_args()

    if args.fetch:
        fetch(TOP_URL, BOOKS_CACHE)
        print("cached: %s (%d bytes)"
              % (BOOKS_CACHE, os.path.getsize(BOOKS_CACHE)))
        return 0

    books, authors = load()
    print("=" * 74)
    print("THE GUTENBERG RANKING")
    print("=" * 74)
    print("  books  %d   authors %d" % (len(books), len(authors)))
    print("  THE MEASURE IS DOWNLOADS, and Gutenberg's own page says so:")
    print("  \"Calculated from the number of times each eBook gets")
    print("  downloaded.\" **This is a reach measure, not copies sold,**")
    print("  and the catalog records it in its own field.")
    print()
    if args.report:
        print("  the top 20 books:")
        for b in sorted(books, key=lambda b: -b.downloads)[:20]:
            print("    %8d  %-42s %s"
                  % (b.downloads, b.title[:42], b.author[:28]))
        print()
        print("  the top 20 authors:")
        for a in sorted(authors, key=lambda a: -a.downloads)[:20]:
            print("    %8d  %s" % (a.downloads, a.author))
    if args.json:
        out = os.path.join(CACHE_DIR, "ranks.json")
        payload = {
            "source": TOP_URL,
            "measure": "downloads (not sales)",
            "books": [b.to_dict() for b in books],
            "authors": [a.to_dict() for a in authors],
        }
        with open(out, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=1, ensure_ascii=False)
        print("  written: %s" % out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
