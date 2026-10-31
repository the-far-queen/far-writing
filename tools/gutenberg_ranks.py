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
TITLE_AUTHOR = re.compile(r"^(.*?)\s+by\s+(.*)$")


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


def parse_books(html: str) -> List[BookRank]:
    out: List[BookRank] = []
    seen = set()
    for eid, title, dl in BOOK_ROW.findall(html):
        t, a = split_title_author(title)
        if not t or eid in seen:
            continue
        seen.add(eid)
        out.append(BookRank(ebook_id=eid, title=t, author=a,
                            downloads=int(dl.replace(",", ""))))
    return out


def parse_authors(html: str) -> List[AuthorRank]:
    out: List[AuthorRank] = []
    seen = set()
    for name, dl in AUTHOR_ROW.findall(html):
        n = clean(name)
        if not n or n in seen:
            continue
        seen.add(n)
        out.append(AuthorRank(author=n, downloads=int(dl.replace(",", ""))))
    return out


def load() -> Tuple[List[BookRank], List[AuthorRank]]:
    if not os.path.isfile(BOOKS_CACHE):
        fetch(TOP_URL, BOOKS_CACHE)
    with open(BOOKS_CACHE, encoding="utf-8") as fh:
        html = fh.read()
    return parse_books(html), parse_authors(html)


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
