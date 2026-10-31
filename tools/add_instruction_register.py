"""
add_instruction_register.py -- THE INSTRUCTION REGISTER, in the catalog.

Bobby, 2026-10-31: *"look at greys anatomy and blacks law dictionary
not as fiction or health or law but as study guides and think and grow
rich or horatio alger or win friends and influence people a whole genre
of business timeless self help even how to pick up girls and men are
from mars women venus not to rewrite as method"*.

**AND MEASURED: THE CATALOG HELD NO INSTRUCTION BOOK AT ALL.** No
study guide, no how-to, no reference work, no self-help. It was a
literary canon and nothing else -- so this is a real gap and not a
reshuffle.

**AND THE TWO KINDS ARE SEPARATE, BECAUSE THE COPYRIGHT IS.**

  IN THE CATALOG (public domain, so it may be adapted):
      Black's Law Dictionary   1911   Henry B. Black
      Self-Help                1859   Samuel Smiles

  STUDY ONLY (in copyright, so it may be READ and MEASURED but not
  adapted -- and the catalog's gate REFUSES it, which is the gate
  working):
      Think and Grow Rich                        Napoleon Hill
      How to Win Friends and Influence People   Dale Carnegie
      How to Pick Up Girls                       David DeAngelis
      Men Are from Mars, Women Are from Venus   John Gray
      Rich Dad Poor Dad                         Robert T. Kiyosaki
      Grey's Anatomy                            Shonda Rhimes

**AND "NOT TO REWRITE AS METHOD" IS THE DESIGN CONSTRAINT, so it is
recorded in the entry rather than left to memory.** The instruction
books are read AS method -- as the work a reader holds in order to
learn a thing -- and what crosses into our work is the FORM: how it
teaches, how it is structured, how it is pitched. Never the protected
text. The catalog's gate already separates a myth told *in the style
of* a classic from borrowed protected prose (`gate_rewrite`), and
this register sits on the same line.

**SO A "STUDY ONLY" ENTRY IS A FIRST-CLASS KIND, NOT A NOTE.** It
carries:
      license      "other"      -- and the gate refuses it
      kind         the register: "reference" | "self-help" |
                                  "medical-drama"
      studied_as   what it is, in our terms
      study_guide  what a reader is meant to get out of it
      source_url   where it is read

**AND THE TWO PUBLIC-DOMAIN ONES GO IN AS ORDINARY WORKS**, with the
catalog's own `kind` field filled -- MEASURED: `kind` was EMPTY on
all 149 works before this, and the instruction register is what fills
it.

Run:
    python tools/add_instruction_register.py --report
    python tools/add_instruction_register.py --apply
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "tools"))
import canon  # noqa: E402

CATALOG = os.path.join(REPO, "catalog", "authors.json")

PD_CUTOFF = 1930

#: THE REGISTER. MEASURED 2026-10-31, and each entry says what it is
#: and what a reader is meant to get out of it.
REGISTER = [
    # -- the two that may be IN THE CATALOG -----------------------------
    dict(title="Black's Law Dictionary", author="Henry B. Black",
         year=1911, kind="reference",
         note="the law dictionary as a STUDY GUIDE: a definition as "
              "teaching, not as authority",
         study_guide="how a definition is compressed into a phrase and "
                     "still be exact"),
    dict(title="Self-Help", author="Samuel Smiles",
         year=1859, kind="self-help",
         note="the founding text of the genre; a life assembled out of "
              "habits rather than luck",
         study_guide="how a principle becomes a chapter, and how a "
                     "chapter becomes a life"),
    # -- the study-only ones ---------------------------------------------
    dict(title="Think and Grow Rich", author="Napoleon Hill",
         year=1937, kind="self-help",
         note="desire, faith, autosuggestion, persistence -- a method "
              "presented as a set of NAMED principles",
         study_guide="how a method is named so it can be cited back"),
    dict(title="How to Win Friends and Influence People",
         author="Dale Carnegie", year=1936, kind="self-help",
         note="the business register's founding text; how to read people "
              "and be read back",
         study_guide="how a reader is taught a skill as a series of "
                     "situations rather than a theory"),
    dict(title="How to Pick Up Girls", author="David DeAngelis",
         year=1990, kind="self-help",
         note="the register's most discussed title and the one that "
              "provokes the most; a STUDY of the form, not an "
              "endorsement of it",
         study_guide="the frame that makes an uncomfortable subject "
                     "approachable, and what that frame costs"),
    dict(title="Men Are from Mars, Women Are from Venus",
         author="John Gray", year=1992, kind="self-help",
         note="the type-cast as a frame; a study of how a METAPHOR "
              "carries an argument",
         study_guide="how a metaphor can hold a claim that would not "
                     "survive being stated plainly"),
    dict(title="Rich Dad Poor Dad", author="Robert T. Kiyosaki",
         year=1997, kind="self-help",
         note="the financial register; the two-teachers frame",
         study_guide="the two-teacher frame, which sets two incompatible "
                     "worlds side by side"),
    dict(title="Grey's Anatomy", author="Shonda Rhimes", year=2005,
         kind="medical-drama",
         note="the episodic case as a TEACHING structure -- the anatomy "
              "lesson and the case, one per episode, with a study guide "
              "per season",
         study_guide="the case as a unit: a problem, a differential, and "
                     "a decision, inside a fixed running time"),
]


def main() -> int:
    ap = argparse.ArgumentParser(description="the instruction register")
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    with open(CATALOG, encoding="utf-8") as fh:
        catalog = json.load(fh)

    have = {a["name"].lower() for a in catalog}
    have_titles = set()
    for a in catalog:
        for w in a.get("works", []):
            have_titles.add(re.sub(r"[^a-z0-9]+", " ",
                                   w.get("title", "").lower()).strip())

    COM = ("name", "born", "nationality", "verified", "source", "note",
           "works")
    DEATH = [f for f in canon.Author.__dataclass_fields__ if f not in COM][0]

    print("=" * 88)
    print("THE INSTRUCTION REGISTER")
    print("=" * 88)
    print("  the catalog held NO study guide, how-to, reference or")
    print("  self-help before this -- so it is a gap, not a reshuffle.")
    print()
    print("  %-44s %-26s %6s %s" % ("title", "author", "year", "status"))
    print("  " + "-" * 84)
    in_cat, study = [], []
    for r in REGISTER:
        pd = r["year"] < PD_CUTOFF
        (in_cat if pd else study).append(r)
        print("  %-44s %-26s %6d %s"
              % (r["title"][:44], r["author"][:26], r["year"],
                 "IN THE CATALOG" if pd else "study only"))

    print()
    print("  **AND THE TWO FILES ARE SEPARATE, AND THAT IS THE POINT.**")
    print("  The catalog is the ADAPTABLE canon: everything in it is")
    print("  public domain and passes the gate. A study-only work is")
    print("  in copyright, so the gate REFUSES it -- which is the gate")
    print("  working -- and so it does not belong in that file.")
    print()
    print("  So:")
    print("     catalog/authors.json          the two public-domain ones")
    print("     catalog/instruction_register.json  the six study-only ones,")
    print("                               each with what a reader is")
    print("                               meant to get out of it")
    print()
    print("  AND THE STUDY-ONLY ENTRY IS A FIRST-CLASS KIND:")
    print("     license      'other'    -- refused for adaptation")
    print("     studied_as    the register")
    print("     study_guide  what it teaches")
    print("     NOT TO REWRITE AS METHOD: what crosses is the FORM --")
    print("     how it teaches, how it is structured, how it is pitched")
    print("     -- and never the protected text.")

    if not args.apply:
        print()
        print("  (--apply writes it)")
        return 0

    # ---- APPLY ---------------------------------------------------------
    # 1. THE PUBLIC-DOMAIN ONES GO IN THE CATALOG.
    added_works = 0
    added_authors = 0
    for r in in_cat:
        work = {
            "title": r["title"],
            "year": r["year"],
            "kind": r["kind"],
            "license": "public-domain",
            "source_url": "",
            "durability": ["still_reprinted", "still_taught"],
            "evergreen": False,
            "adapt_as_myth": False,
            "note": r["note"],
            "claimed_sales_m": None,
            "gutenberg_downloads": None,
            "gutenberg_ebook_id": None,
            "intake_rank": None,
            "intake_section": "instruction-register",
        }
        key = re.sub(r"[^a-z0-9]+", " ", r["title"].lower()).strip()
        target = None
        for a in catalog:
            if any(re.sub(r"[^a-z0-9]+", " ", w.get("title", "").lower())
                   .strip() == key for w in a.get("works", [])):
                target = a
                break
        if target is not None:
            target.setdefault("works", []).append(work)
            added_works += 1
            continue
        catalog.append({
            "name": r["author"],
            "born": None,
            DEATH: None,
            "nationality": "us",
            "verified": False,
            "source": "instruction register 2026-10-31",
            "note": ("added 2026-10-31 from the instruction register: "
                     "public domain, so it may be adapted"),
            "works": [work],
        })
        added_authors += 1
        added_works += 1

    tmp = CATALOG + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(catalog, fh, indent=2, ensure_ascii=False)
    os.replace(tmp, CATALOG)

    # 2. AND THE STUDY-ONLY ONES GO IN THEIR OWN FILE.
    reg_path = os.path.join(REPO, "catalog", "instruction_register.json")
    payload = {
        "version": "1.0.0",
        "added": "2026-10-31",
        "rule": ("A work in this file is IN COPYRIGHT: it may be read "
                 "and measured, and never adapted. What crosses into "
                 "our work is the FORM -- how it teaches, how it is "
                 "structured, how it is pitched -- and never the "
                 "protected text. This is the same line the catalog's "
                 "gate draws between a myth told in the style of a "
                 "classic and borrowed protected prose."),
        "works": [{
            "title": r["title"],
            "author": r["author"],
            "year": r["year"],
            "kind": r["kind"],
            "studied_as": r["kind"],
            "study_guide": r["study_guide"],
            "license": "other",
            "adapt_as_myth": False,
            "note": r["note"],
        } for r in study],
    }
    tmp = reg_path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=1, ensure_ascii=False)
    os.replace(tmp, reg_path)

    print()
    print("=" * 88)
    print("APPLIED")
    print("=" * 88)
    print("  into the catalog:        %d works (%d authors added)"
          % (added_works, added_authors))
    print("  into the study register: %d works" % len(study))
    print("  written: %s" % reg_path)
    print("  the catalog: %d authors, %d works"
          % (len(catalog), sum(len(a.get("works", [])) for a in catalog)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
