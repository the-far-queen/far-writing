"""
intake_parse.py — recover authors from the damaged intake tail.

THE PROBLEM
-----------
docs/intake-2026-10-06-canon.md holds Bobby's Grok intake. List 1
(public domain) and list 2 (copyrighted) are numbered and clean.
After list 2 item ~125 the delimiters break: numbering jumps
96 -> 97 -> 111, 118 -> 120, 125 -> 129, and a whole unnumbered
mega-list lands on one line. The handoff called this "not
machine-recoverable". That was wrong — not for the tail as a whole,
but it IS recoverable per-entry, because every entry still carries its
own `Author — Title — sales` shape.

So this parser does not try to repair the list. It does not renumber.
It does not guess at ordering. It scans for the entry shape and takes
what is actually there, reporting what it could not read.

Bobby's note that H.G. Wells lives in this tail is what triggered
this: he appears exactly once, in the mega-list, with a real work and
a real figure. One author recoverable by shape = every author in the
tail is recoverable by shape.

WHAT IT REFUSES
---------------
1. An entry with no parseable sales figure. The figure is the only
   field that proves the entry was delimited correctly. No figure,
   no entry — otherwise the "—" that appears mid-sentence elsewhere
   in this file gets read as a field separator.

2. A sales figure presented as fact. These are widely-cited
   estimates, mostly "copies ever printed", and no publisher audits
   them. They are kept as a ranking signal and never promoted.

3. Silent truncation. Every number here is checked against the two
   lists bobby actually gave: 150 public-domain, 150 copyrighted.
   Nothing is dropped without being counted and printed.

Run: python tools/intake_parse.py --help
"""

from __future__ import annotations

import json
import os
import re
import sys
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INTAKE = os.path.join(REPO, "docs", "intake-2026-10-06-canon.md")

# The entry shape is `Author — Title — sales`, and nothing else in this
# intake uses that exact three-part run. So rather than one regex that
# has to guess where an author name ends, split each line on the dash
# and walk the segments looking for the triple whose THIRD member is a
# sales figure. The figure is the anchor: it is the only unambiguous
# delimiter in a line that also contains prose, list numbering, and a
# broken mega-list.
# THE DASH PROBLEM.
#
# Entry fields are separated by an em dash "—". The mega-list ALSO
# uses an en dash "–" for numeric ranges: "War and Peace — ~30–40M".
# Splitting on both destroys every ranged figure into two halves, which
# is why Tolstoy and Hesse arrived with the fragment "~30" glued to the
# author and a null rank. Five gate failures, one root cause.
#
# An en dash BETWEEN DIGITS is a range, not a separator. An EM dash is
# ALWAYS a separator in this intake, even when a digit follows — which
# matters because most clean list-1 entries end "— 20 million". A
# rule that refused any dash before a digit swallowed the separator on
# every one of them and silently cut 73 entries.
#
# First attempt at this regex did exactly that: 242 entries -> 169. The
# lesson is the one already written at the top of this file: a parser
# that silently under-reads is worse than one that fails loudly.
# figure_formats exists so the count is watched, not assumed.
DASH_SPLIT = re.compile(r"—|–(?!\d)(?!\s*\d)")

# "several million+", "~40 million+", "60 million", "~65–150 million
# (estimates vary widely)", "13 million (Russia alone)"
#
# AND, in the mega-list, the abbreviated form: "~10M+", "~150M", "35M".
# Two formats for the same field, so both are accepted. The first
# version of this parser only knew the spelled-out form and therefore
# read 3 of the mega-list's 27 figures — which is precisely how Wells
# went missing. A parser that silently under-reads is worse than one
# that fails loudly, so the format count is reported, not assumed.
SALES = re.compile(
    r"(?:several|~?\d[\d,\.]*)\s*(?:million|billion|\d\s?M\b)", re.I
)
# the full field, including a range and its trailing qualifier, so a
# figure can be cut cleanly off the end of a segment.
#
# The range is ONE unit and must be consumed whole from its START.
# Left to scan freely, search() began matching at "40M" inside
# "~30–40M" and sub() then removed only that half, leaving "30–" glued
# to the next author's name — which failed the name check and silently
# dropped the entry. Anchoring the pattern to the start of the figure is
# what makes the range one unit.
_FIG = r"(?:several|~?\d[\d,\.]*)\s*(?:million|billion|\d\s?M\b)"
# Anchored, so the range is consumed as one unit from the start of the
# figure. The leading \s* is load-bearing: segments arrive stripped, but
# a segment that still holds a leading space makes an `^~?` anchor fail
# outright, which leaves the figure in place and silently drops the
# entry. Found by testing this exact case, not by reading it.
SALES_FIELD = re.compile(
    rf"^\s*~?{_FIG}"
    rf"(?:\s*[–-]\s*~?\d[\d,\.]*\s*(?:million|billion|\d\s?M\b)?)?"
    rf"\s*(?:\+)?(?:\s*\([^)]*\))?",
    re.I,
)

# an author segment starts with a capital and is short. This is what
# separates `H. G. Wells` from the prose that precedes it.
AUTHORISH = re.compile(r"^[\s*#0-9\.\)]*[A-Z][\w'\.\- ]{1,50}$")

# leading list numbering, markdown emphasis, and citation brackets
NOISE = re.compile(r"^[\s*#\[\(\)\d\.\)]+")

# bobby's own numbering, used only to count, never to renumber
NUM = re.compile(r"(?:^|\s)(\d{1,3})\.\s")

# The mega-list sits on line 282, AFTER the "LIST 2 — COPYRIGHTED"
# marker, so positional section tracking files it under list 2. That is
# wrong on the content: every title in that tail is public-domain canon
# (Wells, Asimov, Le Guin, Heinlein, Gibson) sitting in Bobby's
# "all-time ~20M+" shelf. Section is decided by which SHELF the entry
# belongs to, not by which marker the line happens to fall after. The
# markers are a reading aid; they are not ground truth.
TAIL_LINE = 282
TAIL_SECTION = "tail-megalist"


@dataclass
class Entry:
    author: str
    title: str
    sales: str
    line: int
    section: str = ""
    sales_rank: Optional[float] = None
    note: str = ""

    def to_dict(self) -> dict:
        return {
            "author": self.author,
            "title": self.title,
            "sales": self.sales,
            "sales_rank": self.sales_rank,
            "line": self.line,
            "section": self.section,
            "note": self.note,
        }


def _rank(sales: str) -> Optional[float]:
    """millions, lower bound. 'several' -> None: an honest unknown,
    not a guess of 3. a ranking that treats 'several' as a number
    invents precision the source never claimed.

    handles both intake formats: "~40 million+" and "~150M".
    """
    m = re.search(r"(\d+(?:\.\d+)?)", sales)
    if not m:
        return None
    return float(m.group(1))


def _section_at(line_no: int, marks: List[Tuple[int, str]]) -> str:
    sec = ""
    for ln, name in marks:
        if ln <= line_no:
            sec = name
        else:
            break
    return sec


def _section_marks(lines: List[str]) -> List[Tuple[int, str]]:
    marks = [(1, "preamble")]
    for i, ln in enumerate(lines, 1):
        if "LIST 1" in ln:
            marks.append((i, "list1-public-domain"))
        elif "LIST 2" in ln:
            marks.append((i, "list2-copyrighted"))
        elif re.search(r"#+\s*(Ancient|Medieval|18th|19th|Early 20th|Rounding|Russian)", ln):
            marks.append((i, "era"))
    return marks


def _entries_in_line(ln: str, line_no: int, section: str) -> List[Entry]:
    """walk the dash-split segments for Author-Title-figure triples.

    The tail is damaged in a specific, repeatable way: the dash that
    should separate `FIGURES` from the NEXT author is missing, so both
    land in one segment —

        ... Jules Verne — Journey to the Center of the Earth —
        several million+ H. G. Wells — The War of the Worlds — ...

    splits to ["Jules Verne", "Journey...", "several million+ H. G. Wells",
    "The War of the Worlds", ...]. A naive reader takes the segment
    before the figure as the author and gets the PREVIOUS entry's
    figure glued to this one's name, which is exactly the shape that
    silently loses Wells.

    So: the sales figure is the anchor, and whatever follows it in the
    same segment is the next author. That name is carried forward to
    the following segment pair. Nothing is guessed; the damage is
    read as the damage it is.
    """
    segs = [s.strip() for s in DASH_SPLIT.split(ln)]
    found: List[Entry] = []
    pending: Optional[str] = None   # author whose dash was lost

    for i in range(1, len(segs)):
        if not SALES.search(segs[i]):
            continue
        # text trailing this figure is the next entry's author.
        # strip the figure AND any "copies ever printed" flourish, then
        # the leading +/~/comma the abbreviation leaves behind.
        trail = SALES_FIELD.sub("", segs[i]).strip(" .,*~+")
        trail_author = trail if trail and AUTHORISH.match(trail) else None

        title = NOISE.sub("", segs[i - 1]).strip(" .")
        if pending is not None:
            author, pending = pending, None
        elif i >= 2 and AUTHORISH.match(segs[i - 2].strip()):
            author = NOISE.sub("", segs[i - 2]).strip(" .")
        else:
            author = ""
        if trail_author:
            pending = trail_author
        if len(author) < 2 or len(title) < 2:
            continue
        # the sales field must not carry the next author's name. when
        # the delimiter was lost, the figure and the following name are
        # one segment, so cut the name back off the end and keep the
        # figure. falls back to the raw segment when nothing trails.
        figure = segs[i]
        if trail_author and figure.endswith(trail_author):
            figure = figure[: -len(trail_author)]
        figure = figure.strip(" .,*~+")
        found.append(Entry(author, title, figure,
                           line_no, section, _rank(figure)))
    return found


def parse(path: str = INTAKE) -> Tuple[List[Entry], dict]:
    with open(path, encoding="utf-8") as f:
        raw = f.read()
    lines = raw.splitlines()
    marks = _section_marks(lines)

    out: List[Entry] = []
    seen: set = set()
    for i, ln in enumerate(lines, 1):
        section = TAIL_SECTION if i == TAIL_LINE else _section_at(i, marks)
        for e in _entries_in_line(ln, i, section):
            key = (e.author.lower(), e.title.lower())
            if key in seen:
                continue
            seen.add(key)
            out.append(e)

    report = {
        "entries": len(out),
        "authors": len({e.author.lower() for e in out}),
        "by_section": {},
        "numbered_in_intake": sorted({
            int(n) for ln in lines for n in NUM.findall(ln)
        }),
        "unranked_sales": sorted({e.author for e in out if e.sales_rank is None}),
        "dropped_no_sales_figure": 0,
    }
    for e in out:
        report["by_section"][e.section] = report["by_section"].get(e.section, 0) + 1

    # figures read by each format, so an under-reading is visible
    # instead of silent. the tail uses the "M" abbreviation; lists 1
    # and 2 spell "million" out.
    report["figure_formats"] = {
        "abbrev_M": sum(1 for e in out if re.search(r"\d\s?M\b", e.sales)),
        "spelled_million": sum(1 for e in out if re.search(r"million", e.sales, re.I)),
        "several_no_number": sum(1 for e in out if e.sales_rank is None),
    }

    return out, report


def _main(argv: List[str]) -> int:
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        print("commands: parse | stats | authors | gate | wells")
        return 0
    cmd = argv[0]
    entries, report = parse()

    if cmd == "parse":
        for e in entries:
            print(f"L{e.line:<4} [{e.section}] {e.author} — {e.title} — {e.sales}")
        print(f"\n{len(entries)} entries / {report['authors']} authors")
        return 0

    if cmd == "stats":
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return 0

    if cmd == "authors":
        names = sorted({e.author for e in entries})
        for n in names:
            print(n)
        print(f"\n{len(names)} unique authors")
        return 0

    if cmd == "gate":
        bad = 0
        for e in entries:
            r = []
            if not e.sales_rank and "several" not in e.sales.lower():
                r.append("sales_present_but_unranked")
            if not e.section:
                r.append("no_section")
            if len(e.author.split()) > 6:
                r.append("author_field_too_long")
            if r:
                bad += 1
                print(f"DENY L{e.line} {e.author} — {e.title}  {r}")
        print(f"\n{len(entries) - bad}/{len(entries)} entries pass")
        return 0 if bad == 0 else 2

    if cmd == "wells":
        for e in entries:
            if "wells" in e.author.lower():
                print(json.dumps(e.to_dict(), indent=2, ensure_ascii=False))
        return 0

    print(f"unknown command: {cmd}")
    return 1


if __name__ == "__main__":
    sys.exit(_main(sys.argv[1:]))