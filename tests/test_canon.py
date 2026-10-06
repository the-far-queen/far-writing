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
    print("\nALL FAR-WRITING CANON TESTS PASS (C1..C10)")


if __name__ == "__main__":
    main()
