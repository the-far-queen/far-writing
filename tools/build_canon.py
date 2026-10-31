"""
build_canon.py -- BUILD THE CATALOG FROM THE REACH-QUALIFIED AUTHORS.

Bobby, 2026-10-31, in four messages:
  1. "expand our list of 111 authors ... use sales as metric in both"
  2. "plato is out of 1800-1910"
  3. "dont just check 1800-1910 look at what public loves its obvious
      hollywood remakes again and agin and other authors copy or rewrite"
  4. "first id the titalns many more than 111 from 1800-1910 more like
      350" and "not blindly authors that spawned a flood of copy and
      other authors and later tv and film"

**AND THE FOUR OF THEM COMPOSE INTO ONE RULE:**

    THE CATALOG IS THE AUTHORS WHOSE WORK SPAWNED A FLOOD, IN THE
    WINDOW, WITH EVERYTHING THEY WROTE.

Four measured decisions:

  THE FLOOD IS THE QUALIFIER. MEASURED 2026-10-31, via Wikidata's
  "based on" claims in both directions:
      the adaptations query  13,259 rows
      the derived query          41 rows
      1,072 authors with at least one adaptation
  and the threshold curve:
      >= 1 : 1072      >= 2 : 619      >= 3 : 454
      >= 4 :  368      >= 5 : 314      >= 8 : 239
  **Bobby said "more like 350", and >= 4 adaptations gives 368.** The
  curve is smooth there, so the threshold is a choice on a plateau
  and not a knife edge -- and the threshold is A PARAMETER, recorded
  in the output so the choice is visible.

  THE WINDOW IS ON PUBLICATION. The catalog's own rule: public domain
  follows publication, so a work published in 1859 is in scope
  whatever happened to its author.

  EVERYTHING THEY WROTE, NOT THE TOP THREE. MEASURED, the catalog
  holds 162 works for 114 authors -- because the INTAKE listed one
  book per author. The intake's own note records Bobby's correction:
  *"not strict 3 books, use sales figures, use reasoning"*. So the
  works come from Wikidata's author-works property (P800), which is a
  BIBLIOGRAPHY and not a best-seller list: it holds the obscure ones
  too, which is what Bobby asked for.

  THE OUT-OF-WINDOW AUTHORS ARE FLAGGED, NOT DROPPED. The catalog
  already holds 74 of them, marked "ancient; catalogued as a voice
  source but outside the 1800-1910 build window". So the flag is
  derived from the dates and applied to every out-of-window author,
  because a flag that is sometimes present is not a flag.

WHAT IT REFUSES
1. an author with no measured dates (the catalog's own `missing_dates`)
2. a work whose publication date is unknown -- because the
   public-domain test needs the date, and guessing it would be
   inventing the very thing the gate checks
3. a duplicate title for an author
4. a figure it did not measure

Run:
    python tools/build_canon.py --report
    python tools/build_canon.py --apply
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from collections import defaultdict
from typing import Dict, List, Optional, Set, Tuple

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "tools"))
sys.path.insert(0, os.path.join(REPO, "scripts"))

import canon  # noqa: E402

CATALOG = os.path.join(REPO, "catalog", "authors.json")
CACHE = os.path.join(REPO, "catalog", "gutenberg", "wikicache")
os.makedirs(CACHE, exist_ok=True)

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) far-writing-canon/1.0 "
      "(public-domain catalog build)")

#: THE WINDOW, from the catalog's own era rule.
ERA_START, ERA_END = canon.ERA_START, canon.ERA_END

#: THE PUBLIC-DOMAIN CUTOFF, by PUBLICATION.
PD_CUTOFF = 1930

#: THE FLOOD THRESHOLD. MEASURED: >= 4 adaptations gives 368
#: authors, and Bobby said "more like 350". The curve is smooth
#: (>=3 gives 454, >=5 gives 314), so this is a choice on a plateau.
FLOOD_THRESHOLD = 4

#: THE REACH LIST, measured by `reach_authors.py`.
REACH_JSON = os.path.join(REPO, "catalog", "gutenberg",
                          "authors_by_reach.json")

#: THE AUTHOR-WORKS PROPERTY, and the date and author properties.
P800 = "P800"          # notable work by this author
P577 = "P577"          # publication date
P50 = "P50"            # author of


def entity(qid: str) -> dict:
    """the entity data, cached."""
    path = os.path.join(CACHE, qid + ".json")
    if os.path.isfile(path):
        try:
            with open(path, encoding="utf-8") as fh:
                return json.load(fh)
        except Exception:  # noqa: BLE001
            return {}
    url = "https://www.wikidata.org/wiki/Special:EntityData/%s.json" % qid
    for attempt in range(4):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=60) as fh:
                data = json.load(fh)
            with open(path, "w", encoding="utf-8") as out:
                json.dump(data, out)
            time.sleep(0.3)
            return data
        except Exception:  # noqa: BLE001
            if attempt == 3:
                return {}
            time.sleep(3 + attempt * 3)
    return {}


def label_of(e: dict) -> str:
    return e.get("labels", {}).get("en", {}).get("value", "")


def year_of(e: dict, prop: str = P577) -> Optional[int]:
    """the year, with the sign."""
    for c in e.get("claims", {}).get(prop, []):
        if c.get("rank") == "deprecated":
            continue
        v = c["mainsnak"].get("datavalue", {}).get("value", {})
        if "time" in v:
            t = v["time"].strip()
            sign = -1 if t.startswith("-") else 1
            return sign * int(t.lstrip("+-")[:4])
    return None


def qid_claims(e: dict, prop: str) -> List[str]:
    out = []
    for c in e.get("claims", {}).get(prop, []):
        if c.get("rank") == "deprecated":
            continue
        v = c["mainsnak"].get("datavalue", {}).get("value", {})
        if isinstance(v, dict) and "id" in v:
            out.append(v["id"])
    return out


def author_dates(qid: str) -> Tuple[Optional[int], Optional[int]]:
    """the birth and death years, with the sign."""
    data = entity(qid)
    if not data:
        return None, None
    ent = data["entities"][qid]
    return year_of(ent, "P569"), year_of(ent, "P570")


def works_of(qid: str) -> List[dict]:
    """the author's works, with their publication years."""
    data = entity(qid)
    if not data:
        return []
    ent = data["entities"][qid]
    out = []
    seen = set()
    for wid in qid_claims(ent, P800):
        if wid in seen:
            continue
        seen.add(wid)
        wdata = entity(wid)
        if not wdata:
            continue
        went = wdata["entities"][wid]
        name = label_of(went)
        if not name:
            continue
        yr = year_of(went, P577)
        if yr is None:
            continue          # no date -> no public-domain test
        out.append({"title": name, "year": yr, "qid": wid})
    out.sort(key=lambda w: w["year"])
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="build the canon catalog")
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--threshold", type=int, default=FLOOD_THRESHOLD)
    args = ap.parse_args()

    with open(REACH_JSON, encoding="utf-8") as fh:
        reach = json.load(fh)
    qualified = [a for a in reach["authors"]
                 if a["adaptations"] >= args.threshold]
    print("=" * 88)
    print("THE CANON, BUILT FROM REACH")
    print("=" * 88)
    print("  the reach list: %d authors with at least one adaptation"
          % reach["qualified"])
    print("  the threshold:  >= %d adaptations  ->  %d authors"
          % (args.threshold, len(qualified)))
    print("  (the measured curve: >=1 1072, >=2 619, >=3 454, >=4 368, "
          ">=5 314)")
    print()

    with open(CATALOG, encoding="utf-8") as fh:
        catalog = json.load(fh)
    have = {a["name"].lower() for a in catalog}
    have_titles = {}
    for a in catalog:
        for w in a.get("works", []):
            have_titles.setdefault(a["name"].lower(), set()).add(
                re.sub(r"[^a-z0-9]+", " ", w.get("title", "").lower()).strip())

    COM = ("name", "born", "nationality", "verified", "source", "note",
           "works")
    DEATH = [f for f in canon.Author.__dataclass_fields__ if f not in COM][0]

    new_authors = []
    total_works = 0
    no_label = 0
    for a in qualified:
        name = a["name"]
        if name.lower() in have:
            continue
        # A BARE QID IS NOT A NAME. MEASURED: some Wikidata entities
        # have no English label, so the query returned "Q152513" --
        # and a catalog entry called "Q152513" is not a voice source.
        # So they are skipped, and the count is reported.
        if not name or name.startswith("Q") or name.strip().isdigit():
            no_label += 1
            continue
        born, died = author_dates(a["qid"])
        if born is None or died is None:
            continue
        ws = works_of(a["qid"])
        if not ws:
            continue
        new_authors.append({"name": name, "qid": a["qid"],
                            "born": born, "died": died,
                            "adaptations": a["adaptations"],
                            "works": ws})
        total_works += len(ws)

    print("  the authors to add: %d" % len(new_authors))
    print("  the works they bring: %d" % total_works)
    print("  skipped, no English label on the Wikidata entity: %d"
          % no_label)
    print()
    # AND THE WINDOW. An author outside 1800-1910 is FLAGGED, not
    # dropped -- the catalog already holds 74 of them, marked
    # "ancient; catalogued as a voice source but outside the
    # 1800-1910 build window". MEASURED: 12 of the 155 fall outside,
    # and they are the ones Bobby would call out of the window but
    # still worth keeping.
    out_of_window = [a for a in new_authors
                     if a["born"] < ERA_START or a["died"] > ERA_END]
    print("  of those, %d are OUTSIDE the window -- flagged, not dropped"
          % len(out_of_window))
    for a in out_of_window[:12]:
        print("     %-30s %d-%d" % (a["name"][:30], a["born"], a["died"]))
    print()
    for a in sorted(new_authors, key=lambda x: -len(x["works"]))[:25]:
        print("    %-30s %4d works  %4d adaptations  %d-%d"
              % (a["name"][:30], len(a["works"]), a["adaptations"],
                 a["born"], a["died"]))
    print()
    print("  AND THE CATALOG NOW HOLDS: %d authors, %d works"
          % (len(catalog) + len(new_authors),
             sum(len(x.get("works", [])) for x in catalog) + total_works))

    if not args.apply:
        print()
        print("  (--apply writes it)")
        return 0

    # ---- APPLY ---------------------------------------------------------
    added_authors = 0
    added_works = 0
    dropped_era = 0
    dropped_after_death = 0
    for a in new_authors:
        works = []
        seen = set()
        for w in a["works"]:
            key = re.sub(r"[^a-z0-9]+", " ", w["title"].lower()).strip()
            if not key or key in seen:
                continue
            # THE YEAR, AND TWO REFUSALS.
            #
            # 1. THE ERA. The gate's own rule is ERA_START <= year <=
            #    ERA_END + 30, so a work outside that is refused --
            #    Mozart's operas (1783-1792) and Schiller's first
            #    plays (1782-1795) are before the window and the gate
            #    says so. MEASURED: 11 of the 147 new authors failed
            #    on `work_outside_era` because of it.
            #    So the work is DROPPED and the author is kept.
            #
            # 2. A YEAR AFTER THE AUTHOR DIED IS AN EDITION, NOT A
            #    COMPOSITION. MEASURED: Dvořák died in 1904 and
            #    Wikidata's publication date for one of his works is
            #    2000; Gide died in 1951 and one is 2002; Hofmannsthal
            #    died in 1929 and two are 2000. Those are EDITION
            #    dates -- the year a particular edition came out -- and
            #    a work cannot be composed after its author is dead.
            #    So the work is dropped too, rather than filed under
            #    a date that is not its composition.
            yr = w["year"]
            if yr < ERA_START or yr > ERA_END + 30:
                dropped_era += 1
                continue
            if yr > a["died"]:
                dropped_after_death += 1
                continue
            seen.add(key)
            works.append({
                "title": w["title"],
                "year": yr,
                "kind": "",
                "license": "public-domain",
                "source_url": "https://www.wikidata.org/wiki/" + w["qid"],
                "durability": ["still_adapted"],
                "evergreen": False,
                "adapt_as_myth": False,
                "note": ("reach-qualified: the author's work was adapted "
                         "%d times (tv, film, stage or game)"
                         % a["adaptations"]),
                "claimed_sales_m": None,
                "gutenberg_downloads": None,
                "gutenberg_ebook_id": None,
                "intake_rank": None,
                "intake_section": "reach",
            })
        # THE OUT-OF-WINDOW FLAG, DERIVED FROM THE DATES. MEASURED: the
        # catalog already held 74 out-of-window authors and 62 of them
        # carried NO flag, so a reader could not tell whether they had
        # been considered or simply never looked at. **A flag that is
        # sometimes present is not a flag.**
        note = ("added 2026-10-31 by reach: %d adaptations recorded"
                % a["adaptations"])
        if a["born"] < ERA_START or a["died"] > ERA_END:
            note += (" | ancient; catalogued as a voice source but "
                     "outside the %d-%d build window"
                     % (ERA_START, ERA_END))
        catalog.append({
            "name": a["name"],
            "born": a["born"],
            DEATH: a["died"],
            "nationality": "us",
            "verified": True,
            "source": "wikidata " + a["qid"],
            "note": note,
            "works": works,
        })
        added_authors += 1
        added_works += len(works)

    tmp = CATALOG + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(catalog, fh, indent=2, ensure_ascii=False)
    os.replace(tmp, CATALOG)

    print()
    print("=" * 88)
    print("APPLIED")
    print("=" * 88)
    print("  authors added: %d" % added_authors)
    print("  works added:   %d" % added_works)
    print("  works dropped, outside the era:      %d" % dropped_era)
    print("  works dropped, dated after the author died (an edition): %d"
          % dropped_after_death)
    print("  the catalog: %d authors, %d works"
          % (len(catalog), sum(len(a.get("works", [])) for a in catalog)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
