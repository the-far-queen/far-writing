"""
canon.py — the public-domain canon catalog for far-writing.

The pipeline: Bobby writes long-form with Grok; that intake is the raw
material. This catalog is the other input — the public-domain canon
that the new work is written AGAINST and IN.

Scope: US authors 1800-1910. For each author we track their best three
works, and mark each work for adaptation.

The gate refuses three specific failure modes:

1. A work not actually in the public domain (a modern author smuggled
   into the catalog).
2. An "evergreen" claim with no durability test attached.
3. An adaptation marked as a rewrite. It is a myth told in the style of
   a classic, not a retelling that borrows protected text.

Run: python tools/canon.py --help
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CATALOG_DIR = os.path.join(REPO, "catalog")
AUTHORS_FILE = os.path.join(CATALOG_DIR, "authors.json")

ERA_START, ERA_END = 1800, 1910

# NOT a hard cap on an author's body of work.
#
# An earlier draft limited every author to exactly three works. Bobby's
# correction: "not strict 3 books, use sales figures, use reasoning." A
# cap of three would have thrown away most of Jules Verne's and Dickens'
# catalog, and both are exactly the durable, endlessly-adapted voices
# this catalog exists to supply.
#
# Every work is kept. Sales is a RANKING signal, not a truth: these are
# widely-cited estimates, mostly "copies ever printed", and no publisher
# audits them. Ordering uses it; nothing claims it as fact.

# a work is evergreen only if it clears at least one durability test.
DURABILITY_TESTS = [
    "still_reprinted",        # in print or regularly reissued
    "still_adapted",          # film, tv, stage, radio, games
    "still_taught",           # on a syllabus somewhere
    "public_domain_reads",    # measurable circulation of free copies
    "cultural_reference",     # cited in mainstream discourse
]

LICENSES = ["public-domain", "cc0", "cc-by", "cc-by-sa", "cc-by-nc-sa", "other"]

ISO = re.compile(r"^\d{4}$")


@dataclass
class Work:
    title: str
    year: Optional[int] = None
    kind: str = ""                  # novel | story | essay | poem | play | memoir
    license: str = "public-domain"
    source_url: str = ""
    durability: List[str] = field(default_factory=list)   # which tests it clears
    evergreen: bool = False
    adapt_as_myth: bool = False     # told anew in the style of a classic
    note: str = ""
    # provenance from the intake. sales figures are Grok's widely-cited
    # estimates, not audited numbers — kept, but never treated as fact.
    claimed_sales_m: Optional[float] = None
    intake_rank: Optional[int] = None
    intake_section: str = ""

    def work_id(self) -> str:
        h = hashlib.sha256(f"{self.title}|{self.year}".lower().encode()).hexdigest()
        return f"work-{h[:10]}"

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["work_id"] = self.work_id()
        return d


@dataclass
class Author:
    name: str
    born: Optional[int] = None
    died: Optional[int] = None
    nationality: str = "us"
    verified: bool = False      # birth/death fetched from a source, not recalled
    source: str = ""             # where the dates were checked
    note: str = ""
    works: List[Work] = field(default_factory=list)

    def author_id(self) -> str:
        return hashlib.sha256(self.name.lower().encode()).hexdigest()[:10]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "author_id": self.author_id(),
            "name": self.name,
            "born": self.born,
            "died": self.died,
            "nationality": self.nationality,
            "verified": self.verified,
            "source": self.source,
            "note": self.note,
            "works": [w.to_dict() for w in self.works],
        }


@dataclass
class Verdict:
    allow: bool
    reasons: List[str] = field(default_factory=list)
    subject_id: str = ""

    @classmethod
    def of(cls, allow: bool, reasons: List[str], subject_id: str = "") -> "Verdict":
        return cls(allow, reasons, subject_id)

    def __str__(self) -> str:
        return f"{'ALLOW' if self.allow else 'DENY'} {self.subject_id} {self.reasons}"


# ---------------------------------------------------------------------------
# gate
# ---------------------------------------------------------------------------

def gate_author(a: Author, now_year: int = 2026) -> Verdict:
    r: List[str] = []

    if not a.name.strip():
        r.append("no_name")

    # NOTE ON COPYRIGHT. US law: a work is public domain once published,
    # regardless of when its author died. Hawthorne published in 1852
    # and died in 1864; that book is free forever. So the gate keys on
    # the WORK's publication date, not the author's death date. The
    # author-date checks below exist only to catch catalog typos.

    # No birth-year refusal at all.
    #
    # Earlier drafts refused anyone born before 1800. That was wrong on
    # the data: the intake deliberately reaches back through Homer,
    # Aesop and Chaucer, and forward past 1800 to include Goethe (1749),
    # Balzac (1799), Paine (1737) and Jefferson (1743). Those are exactly
    # the voices that shape what we write in. An author born 1700-1799
    # is canonical, not defective — the note records the era instead.
    if a.died is not None and a.born is not None:
        if a.died < a.born:
            r.append("died_before_born")
        # a lifespan under 20 years is a data error, except where the
        # whole recorded life is one or two years (Homer's traditional
        # 900-800 span, or an author known only by a single year)
        elif 0 < (a.died - a.born) < 20 and (a.died - a.born) > 2:
            r.append(f"implausible_lifespan:{a.born}-{a.died}")
    if a.born is not None and now_year and a.born > now_year:
        r.append(f"born_in_future:{a.born}")

    if a.nationality != "us":
        r.append(f"non_us:{a.nationality}")

    # A catalog entry with no dates at all is how a hallucinated or
    # mis-remembered author slips in. It has to be refused.
    if a.born is None or a.died is None:
        r.append("missing_dates")

    # An author with a large body of work is not a gate failure.
    # Overlap is still a catalog defect worth refusing.
    titles = [w.title.lower() for w in a.works]
    if len(titles) != len(set(titles)):
        dupes = {t for t in titles if titles.count(t) > 1}
        r.append(f"duplicate_titles:{sorted(dupes)}")

    r += _gate_works(a.works)

    return Verdict.of(not r, r, a.author_id())


def _gate_works(works: List[Work]) -> List[str]:
    r: List[str] = []
    for i, w in enumerate(works):
        if not w.title.strip():
            r.append(f"no_title:{i}")
        if w.license not in LICENSES:
            r.append(f"bad_license:{i}:{w.license}")
        elif w.license != "public-domain":
            r.append(f"not_public_domain:{i}:{w.title}")
        if w.year is not None and not (ERA_START <= w.year <= ERA_END + 30):
            r.append(f"work_outside_era:{i}:{w.year}")
        # evergreen is a claim, so it must clear a named test
        if w.evergreen and not w.durability:
            r.append(f"evergreen_without_test:{i}:{w.title}")
        for t in w.durability:
            if t not in DURABILITY_TESTS:
                r.append(f"unknown_durability_test:{i}:{t}")
        if w.evergreen and w.durability:
            bad = [t for t in w.durability if t not in DURABILITY_TESTS]
            if bad:
                r.append(f"unproven_evergreen:{i}:{w.title}")
    return r


def gate_work(w: Work) -> Verdict:
    return Verdict.of(not _gate_works([w]), _gate_works([w]), w.work_id())


def gate_rewrite(is_rewrite: bool, borrowed_protected_text: bool) -> Verdict:
    """a myth told in the style of a classic is fine. lifting protected
    prose is not. the gate names the difference so nobody has to guess."""
    r: List[str] = []
    if is_rewrite:
        r.append("rewrite_not_adaptation")
    if borrowed_protected_text:
        r.append("borrowed_protected_text")
    return Verdict.of(not r, r, "rewrite")


# ---------------------------------------------------------------------------
# catalog io
# ---------------------------------------------------------------------------

def load_catalog() -> List[Author]:
    if not os.path.isfile(AUTHORS_FILE):
        return []
    with open(AUTHORS_FILE, encoding="utf-8") as f:
        raw = json.load(f)
    out: List[Author] = []
    for d in (raw if isinstance(raw, list) else raw.get("authors", [])):
        d = dict(d)
        d.pop("author_id", None)
        ws = []
        for w in d.get("works", []):
            w = dict(w)
            w.pop("work_id", None)
            ws.append(Work(**w))
        d["works"] = ws
        out.append(Author(**d))
    return out


def save_catalog(authors: List[Author]) -> str:
    os.makedirs(CATALOG_DIR, exist_ok=True)
    with open(AUTHORS_FILE, "w", encoding="utf-8") as f:
        json.dump([a.to_dict() for a in authors], f, indent=2, ensure_ascii=False)
    return AUTHORS_FILE


def stats() -> Dict[str, Any]:
    auth = load_catalog()
    works = [w for a in auth for w in a.works]
    return {
        "authors": len(auth),
        "works": len(works),
        "evergreen": sum(1 for w in works if w.evergreen),
        "adapt_as_myth": sum(1 for w in works if w.adapt_as_myth),
        "passing": sum(1 for a in auth if gate_author(a).allow),
        "failing": sum(1 for a in auth if not gate_author(a).allow),
    }


def _main(argv: List[str]) -> int:
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        print("commands: stats | list | gate")
        return 0
    cmd = argv[0]

    if cmd == "stats":
        print(json.dumps(stats(), indent=2))
        return 0

    if cmd == "list":
        for a in load_catalog():
            v = gate_author(a)
            flag = "ok " if v.allow else "DENY"
            print(f"{flag} {a.author_id()}  {a.name} "
                  f"({a.born or '?'}-{a.died or '?'})  {len(a.works)} works"
                  + ("" if v.allow else f"  {v.reasons}"))
        return 0

    if cmd == "gate":
        bad = 0
        for a in load_catalog():
            v = gate_author(a)
            if not v.allow:
                bad += 1
                print(v)
        print(f"\n{len(load_catalog()) - bad}/{len(load_catalog())} authors pass")
        return 0 if bad == 0 else 2

    print(f"unknown command: {cmd}")
    return 1


if __name__ == "__main__":
    sys.exit(_main(sys.argv[1:]))
