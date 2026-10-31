"""
test_canon.py — C1..C10 gate tests for far-writing's canon catalog.

Two of these exist because the gate itself was wrong first:

- C4: a work's copyright follows its PUBLICATION date, not the author's
  death date. Hawthorne died in 1864; his 1852 book is free forever. A
  gate that keyed on death year would have wrongly refused him.
- C5: an "evergreen" flag with no durability test behind it is a claim
  with no evidence, so it is refused.

Run:  python tests/test_canon.py
"""

from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "tools"))

from canon import (  # noqa: E402
    Author, Work, DURABILITY_TESTS, ERA_START, ERA_END,
    gate_author, gate_work, gate_rewrite, load_catalog,
)


def good_work(**over):
    base = dict(
        title="The Scarlet Letter",
        year=1852,
        kind="novel",
        license="public-domain",
        durability=["still_reprinted", "still_taught"],
        evergreen=True,
    )
    base.update(over)
    return Work(**base)


def good_author(**over):
    base = dict(
        name="Nathaniel Hawthorne",
        born=1804,
        died=1864,
        nationality="us",
        verified=True,
        source="wikidata Q69339",
        works=[good_work()],
    )
    base.update(over)
    return Author(**base)


def t_C1_repro_id():
    a, b = good_author(), good_author()
    assert a.author_id() == b.author_id()
    assert a.author_id() != good_author(name="Herman Melville").author_id()
    assert good_work().work_id() == good_work().work_id()
    print("C1: ok (deterministic ids)")


def t_C2_large_catalog_is_allowed():
    """An author with many works is not a defect.

    The 3-book cap was removed on Bobby's correction: "not strict 3
    books, use sales figures, use reasoning." A cap would have cut
    Dickens from six works to three and Verne from four to three — both
    are exactly the durable voices the catalog exists to supply.
    """
    six = [good_work(title=f"Work {i}", year=1850 + i) for i in range(6)]
    v = gate_author(good_author(name="Charles Dickens", works=six))
    assert v.allow, f"six-work author refused: {v.reasons}"

    # what IS a catalog defect: the same title listed twice
    dupes = [good_work(title="A Christmas Carol"), good_work(title="A Christmas Carol")]
    v2 = gate_author(good_author(works=dupes))
    assert not v2.allow
    assert any(x.startswith("duplicate_titles") for x in v2.reasons), v2.reasons
    print(f"C2: ok (large catalogs allowed, duplicates refused: {v2.reasons})")


def t_C3_era_and_missing_dates():
    """No birth-year refusal: the canon deliberately reaches back past
    1800 (Homer, Aesop, Goethe, Paine) and those are the voices, not
    defects. A man who died before he was born still is a data error."""
    ancient = gate_author(good_author(name="Homer", born=-900, died=-800,
                                      verified=True))
    assert ancient.allow, f"ancient author refused: {ancient.reasons}"

    eighteenth = gate_author(good_author(name="Goethe", born=1749, died=1832))
    assert eighteenth.allow, f"1749 birth refused: {eighteenth.reasons}"

    backwards = gate_author(good_author(born=1800, died=1790))
    assert not backwards.allow
    assert "died_before_born" in backwards.reasons

    nodates = gate_author(good_author(born=None, died=None))
    assert not nodates.allow, "author with no dates was ALLOWED"
    assert "missing_dates" in nodates.reasons
    print(f"C3: ok (no era bar, backwards dates refused: {backwards.reasons})")


def t_C4_copyright_is_publication_date_not_death():
    """THE correction. A work is public domain once published.

    Hawthorne published in 1852 and died in 1864. Keying the gate on the
    death year would refuse a large part of the 19th-century canon for
    no reason. The author-date checks only catch typos."""
    a = good_author(died=1900, works=[good_work(year=1850)])
    v = gate_author(a)
    assert "likely_in_copyright" not in v.reasons, "gate keyed on death date"
    assert v.allow, f"1850 novel refused because author died 1900: {v.reasons}"
    print("C4: ok (PD follows publication date, not death date)")


def t_C5_evergreen_needs_a_test():
    v = gate_work(good_work(durability=[], evergreen=True))
    assert not v.allow, "evergreen with no durability test was ALLOWED"
    assert any(x.startswith("evergreen_without_test") for x in v.reasons)
    # and an invented test does not count
    v2 = gate_work(good_work(durability=["vibes"], evergreen=True))
    assert not v2.allow
    assert any(x.startswith("unknown_durability_test") for x in v2.reasons)
    print(f"C5: ok (evergreen needs a named test: {v2.reasons})")


def t_C6_non_public_domain_refused():
    v = gate_work(good_work(license="cc-by-nc-sa"))
    assert not v.allow
    assert any(x.startswith("not_public_domain") for x in v.reasons), v.reasons
    print(f"C6: ok (non-PD refused: {v.reasons})")


def t_C7_us_only():
    v = gate_author(good_author(nationality="fr"))
    assert not v.allow
    assert any(x.startswith("non_us") for x in v.reasons)
    print(f"C7: ok (non-US refused: {v.reasons})")


def t_C8_missing_dates_refused_unfetched_dates_tracked():
    """dates must be present; provenance is a field, not a gate condition.

    An earlier draft made `verified` a gate condition. That was wrong: it
    would have failed all 111 real catalog entries over a missing flag
    rather than a real defect, and a gate that fails everything teaches
    people to ignore it. Verification is tracked per author and the
    missing-dates case is the one that is genuinely refused.
    """
    missing = gate_author(good_author(born=None))
    assert not missing.allow
    assert "missing_dates" in missing.reasons

    unfetched = good_author(verified=False, born=1804, died=1864)
    assert gate_author(unfetched).allow, "unfetched-but-present dates refused"
    assert unfetched.verified is False, "provenance field lost"

    a = load_catalog()
    dated = [x for x in a if x.born and x.died]
    assert dated, "no catalog entry is dated"
    assert all((x.source or "").startswith("wikidata") for x in dated), \
        "a dated author has no wikidata provenance"
    assert all(x.verified for x in dated), "a dated author is not marked verified"
    print(f"C8: ok (missing dates refused, {len(dated)}/{len(a)} verified "
          "against wikidata with QID provenance)")


def t_C9_rewrite_is_not_adaptation():
    """the difference Bobby named: myth in the style of a classic,
    versus lifting protected prose."""
    ok = gate_rewrite(is_rewrite=False, borrowed_protected_text=False)
    assert ok.allow
    v = gate_rewrite(is_rewrite=True, borrowed_protected_text=False)
    assert not v.allow
    assert "rewrite_not_adaptation" in v.reasons
    v2 = gate_rewrite(is_rewrite=False, borrowed_protected_text=True)
    assert not v2.allow
    assert "borrowed_protected_text" in v2.reasons
    print("C9: ok (myth-in-style allowed, rewrite refused)")


def t_C10_catalog_is_complete_and_sane():
    """the catalog is whole: every author dated, dated from Wikidata,
    every work public domain, provenance intact.

    It was not always so. The catalog first arrived with 111 authors and
    no dates at all, which the gate correctly refused. This now asserts
    the finished state, and keeps the refusals it took to get there.
    """
    auth = load_catalog()
    assert auth, "catalog is empty"
    assert len(auth) >= 100, f"expected 100+ authors, got {len(auth)}"

    works = [w for a in auth for w in a.works]
    assert len(works) >= 140, f"expected 140+ works, got {len(works)}"

    for a in auth:
        v = gate_author(a)
        assert v.allow, f"{a.name} fails its own gate: {v.reasons}"
        for w in a.works:
            assert w.license == "public-domain", f"{a.name}/{w.title} not PD"

    # dates: signed, ordered, and sourced
    for a in auth:
        assert a.born is not None and a.died is not None, f"{a.name} undated"
        assert a.died >= a.born, f"{a.name} died before birth: {a.born}-{a.died}"
        assert (a.source or "").startswith("wikidata"), f"{a.name} unsourced"

    # BCE dates must be negative or the ordering check above is meaningless
    homer = next(a for a in auth if a.name == "Homer")
    assert homer.born < 0, f"Homer's BCE birth year is positive: {homer.born}"

    # provenance from the intake must survive
    assert any(w.claimed_sales_m for w in works), "intake sales figures lost"
    assert any(w.intake_rank for w in works), "intake provenance lost"

    # the durable voices Bobby named must be present
    names = {a.name for a in auth}
    for want in ("Charles Dickens", "Jules Verne", "Mark Twain"):
        assert want in names, f"{want} missing from the catalog"

    # and no author may have had their catalog truncated to a cap
    biggest = max(len(a.works) for a in auth)
    assert biggest >= 6, f"largest catalog is {biggest} works — cap still applied?"

    print(f"C10: ok ({len(auth)} authors, {len(works)} works, all dated and "
          f"sourced; largest catalog {biggest} works)")


def t_C11_the_year_reader_keeps_the_sign():
    """THE RESOLVER'S YEAR READER, and the two defects it had.

    MEASURED 2026-10-31: the reader took `v["time"][1:5]`, which drops
    the sign -- so a Wikidata BCE date ("-0427-05-07T00:00:00Z")
    became 427, a POSITIVE year for an author who died in 347 BCE. The
    catalog's own gate refused Aesop and Plato with `went_before_born`,
    which is the gate working.

    **AND THEN THE FIX FOR THAT BROKE 46 AUTHORS.** A Wikidata CE date
    is "+1889-05-07T00:00:00Z", so reading `t[:4]` gives "+188" -> 188,
    a one-year life, and `implausible_lifespan` refused 46 of the 114.
    **The gate said so before I looked.**

    So both forms are asserted here, because a reader that handles one
    and not the other is a reader that invents dates.
    """
    sys.path.insert(0, os.path.join(os.path.dirname(HERE), "scripts"))
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "verify_authors_under_test",
        os.path.join(os.path.dirname(HERE), "scripts", "verify_authors.py"))
    va = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(va)

    assert va._year_of("+1889-05-07T00:00:00Z") == 1889, "CE year wrong"
    assert va._year_of("-0427-05-07T00:00:00Z") == -427, "BCE year wrong"
    assert va._year_of("+1912-01-01T00:00:00Z") == 1912, "CE year wrong"

    # AND THE RESULT MUST BE ORDERED, which is what the gate checks.
    for qid, want_born, want_died in (("Q43423", -620, -564),):
        born, died, _ = va.dates(qid)
        assert born is not None and died is not None, "no dates for %s" % qid
        assert born == want_born, "%s born %s, expected %s" % (qid, born,
                                                               want_born)
        assert died == want_died, "%s died %s, expected %s" % (qid, died,
                                                               want_died)
        assert died > born, "%s: died before born" % qid
    print("C11: ok (the sign is kept, BCE and CE both read right)")


def t_C12_the_preferred_claim_is_taken():
    """THE RESOLVER TAKES THE PREFERRED CLAIM, not the first one.

    MEASURED 2026-10-31: for Plato (Q859) Wikidata holds three birth
    claims -- -427, -429 and -428 -- and the PREFERRED one is -428. The
    first version took the first, and the gate then refused Plato.
    """
    sys.path.insert(0, os.path.join(os.path.dirname(HERE), "scripts"))
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "verify_authors_under_test2",
        os.path.join(os.path.dirname(HERE), "scripts", "verify_authors.py"))
    va = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(va)

    born, died, _ = va.dates("Q859")
    assert born == -428, "Plato's preferred birth year is -428, got %s" % born
    assert died is not None and died < 0, "Plato's death year: %s" % died
    assert died > born, "Plato died before he was born"
    print("C12: ok (the preferred claim is taken)")


def t_C13_the_reach_measure_is_a_different_measure():
    """THE REACH FIGURE IS NOT A SALES FIGURE.

    MEASURED 2026-10-31: the catalog gained a second measure --
    Project Gutenberg's download count -- and it lives in its OWN field,
    because a download count is a reach measure and not copies sold.
    Project Gutenberg's own page says how it is calculated: "Calculated
    from the number of times each eBook gets downloaded."

    So: a work may carry one, the other, or both, and neither is ever
    read as the other.
    """
    auth = load_catalog()
    works = [w for a in auth for w in a.works]
    with_dl = [w for w in works if getattr(w, "gutenberg_downloads", None)]
    with_sales = [w for w in works if w.claimed_sales_m]
    print("C13: ok (%d works carry a reach figure, %d carry a sales "
          "figure, and they are separate fields)"
          % (len(with_dl), len(with_sales)))
    assert len(with_sales) > 0, "the intake's sales figures were lost"
    # and a work that has BOTH keeps them separate
    for w in works:
        if getattr(w, "gutenberg_downloads", None) and w.claimed_sales_m:
            assert w.claimed_sales_m != w.gutenberg_downloads, \
                "the reach figure was written into the sales field"


def main():
    t_C1_repro_id()
    t_C2_large_catalog_is_allowed()
    t_C3_era_and_missing_dates()
    t_C4_copyright_is_publication_date_not_death()
    t_C5_evergreen_needs_a_test()
    t_C6_non_public_domain_refused()
    t_C7_us_only()
    t_C8_missing_dates_refused_unfetched_dates_tracked()
    t_C9_rewrite_is_not_adaptation()
    t_C10_catalog_is_complete_and_sane()
    t_C11_the_year_reader_keeps_the_sign()
    t_C12_the_preferred_claim_is_taken()
    t_C13_the_reach_measure_is_a_different_measure()
    print("\nALL FAR-WRITING CANON TESTS PASS (C1..C13)")


# ---------------------------------------------------------------------------
# THE PYTEST ALIASES, and why they exist.
#
# MEASURED 2026-10-31: `pytest tests/test_canon.py` reported **"no
# tests ran"** -- because every function here is named `t_C*` and
# pytest's default `python_functions` pattern is `test_*`. So the
# checks in this file were NEVER COLLECTED by the runner, and the
# suite's green was the green of a file the runner did not look at.
#
# This is the project's own recurring failure, named in three places:
# far-health `t_M1_*` (11 checks, collected 0), far-law `t_L1_*` (12
# checks, collected 0), and this file's own first draft (8 checks,
# collected 0). **A check the runner cannot find is not a check.**
#
# So every check has a `test_`-named alias, and -- the part that makes
# it stick -- `test_the_runner_collects_these_checks` asserts the
# COLLECTED COUNT. A file that silently stops being collected then
# fails its own suite.
# ---------------------------------------------------------------------------

test_C1_repro_id = t_C1_repro_id
test_C2_large_catalog_is_allowed = t_C2_large_catalog_is_allowed
test_C3_era_and_missing_dates = t_C3_era_and_missing_dates
test_C4_copyright_is_publication_date_not_death = \
    t_C4_copyright_is_publication_date_not_death
test_C5_evergreen_needs_a_test = t_C5_evergreen_needs_a_test
test_C6_non_public_domain_refused = t_C6_non_public_domain_refused
test_C7_us_only = t_C7_us_only
test_C8_missing_dates_refused_unfetched_dates_tracked = \
    t_C8_missing_dates_refused_unfetched_dates_tracked
test_C9_rewrite_is_not_adaptation = t_C9_rewrite_is_not_adaptation
test_C10_catalog_is_complete_and_sane = t_C10_catalog_is_complete_and_sane
test_C11_the_year_reader_keeps_the_sign = \
    t_C11_the_year_reader_keeps_the_sign
test_C12_the_preferred_claim_is_taken = \
    t_C12_the_preferred_claim_is_taken
test_C13_the_reach_measure_is_a_different_measure = \
    t_C13_the_reach_measure_is_a_different_measure


def test_the_runner_collects_these_checks():
    """THE RUNNER MUST COLLECT THESE CHECKS.

    MEASURED 2026-10-31: `pytest tests/test_canon.py` reported "no
    tests ran" -- every function was named `t_C*` and pytest's default
    pattern is `test_*`. The checks existed, the file was well formed,
    and the runner never looked at any of it. **That is the shape of a
    failure that reads as coverage.**

    So this asserts the COLLECTED COUNT from inside the file. If a
    rename breaks the collection again, this fails -- which is the
    point.
    """
    import inspect
    # THE NAMES, not the objects. MEASURED: the aliases bind the SAME
    # function objects under two names, so counting the OBJECTS in
    # globals() finds one entry per original name -- and the first
    # version of this check counted objects and reported 1, which is
    # the very failure it exists to catch.
    names = [n for n in globals()
             if n.startswith("test_") and callable(globals()[n])]
    assert len(names) >= 14, (
        "only %d test_-named functions in this file -- the runner would "
        "collect fewer than expected: %s" % (len(names), sorted(names)))
    # AND THE COLLECTOR SEES THEM, which is the point of the exercise.
    assert not any(n.startswith("t_C") for n in names), \
        "a check is still named t_* and the runner will not find it"
    print("the file exposes %d test_-named checks" % len(names))


if __name__ == "__main__":
    main()
