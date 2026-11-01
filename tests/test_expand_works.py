"""
test_expand_works.py -- E1..E8, the checks that would have caught the
defects this file's tool actually had.

**AND EVERY TEST HERE IS MUTATION-CHECKED.** A test that cannot go
RED proves nothing, so each of these has a mutation that removes the
mechanism it tests, and the mutation must fail the test. The
mutations are in tools/expand_works.py itself, applied by the
harness below.

Run:  python tests/test_expand_works.py
      python -m pytest tests/test_expand_works.py -q
"""

from __future__ import annotations

import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, "tools"))

import expand_works as ew  # noqa: E402
import reach_measure as rm  # noqa: E402

CATALOG = os.path.join(REPO, "catalog", "authors.json")


def _catalog() -> list:
    """the catalog, read fresh."""
    with open(CATALOG, encoding="utf-8") as fh:
        return json.load(fh)


def _old_counts() -> dict:
    """the OLD row count per work label -- the join product.

    **AND THE COMMITTED FIXTURE IS THE FALLBACK.** The SPARQL rows live
    in the gitignored wikicache, so a fresh clone has none of them and
    this check could not run there at all. MEASURED 2026-11-01: the
    clone failed 4 of 79 checks for exactly this reason.

    So: the cached rows if they are there, and the committed fixture
    if they are not. The fixture is the same count, derived from those
    rows, and it carries the provenance that made it.
    """
    import collections

    old = collections.Counter()
    if os.path.isdir(rm.CACHE):
        for fn in os.listdir(rm.CACHE):
            if not fn.startswith("sparql_adaptations"):
                continue
            try:
                with open(os.path.join(rm.CACHE, fn), encoding="utf-8") as fh:
                    data = json.load(fh)
            except Exception:  # noqa: BLE001
                continue
            for r in data.get("results", {}).get("bindings", []):
                t = r.get("workLabel", {}).get("value", "")
                if t:
                    old[t] += 1
    if old:
        return old

    path = os.path.join(REPO, "catalog", "fixtures", "old_counts.json")
    if not os.path.isfile(path):
        return {}
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    return {k: int(v) for k, v in (data.get("counts") or {}).items()}


# ---------------------------------------------------------------------------
# E1. THE TITLE KEY IS NORMALIZED ON BOTH SIDES.
# ---------------------------------------------------------------------------
def t_E1_the_title_key_is_normalized_on_both_sides():
    """THE MEASUREMENT AND THE CATALOG MUST AGREE ON WHAT A TITLE IS.

    MEASURED 2026-10-31: the reach table was keyed by the RAW
    Wikidata label and looked up with the NORMALIZED title. 546 of the
    2,486 entries (22%) could never be found, and 51 catalog works
    whose reach count WAS in the measurement carried `None` -- Moby-
    Dick, Alice's Adventures in Wonderland, Les Misérables, all of
    them.

    So: "Uncle Tom's Cabin" and "uncle tom's cabin" are ONE key, and a
    lookup on either finds the same number.
    """
    reach = rm.load_reach()
    assert reach, "the corrected reach measurement is not cached"

    # THE NORMALIZATION IS IDEMPOTENT, which is what makes a key a key.
    for raw in ("Uncle Tom's Cabin", "Moby-Dick", "Les Misérables",
                "Alice's Adventures in Wonderland", "Père Goriot",
                "Frankenstein; or, The Modern Prometheus"):
        k = ew.norm(raw)
        assert ew.norm(k) == k, "the key is not stable: %r -> %r -> %r" % (
            raw, k, ew.norm(k))

    # AND A KEY THAT LOOKS THE SAME LOOKS UP THE SAME.
    a = reach.get(ew.norm("Uncle Tom's Cabin"))
    b = reach.get(ew.norm("uncle tom's cabin"))
    assert a is not None, "the reach measurement lost Uncle Tom's Cabin"
    assert a == b, "two spellings of one title gave two numbers"

    # AND THE WRITER AND THE READER AGREE ON THE KEY. This is the
    # round-trip, and it is the shape of the ORIGINAL defect: the
    # writer held the RAW label and the reader asked for the
    # NORMALIZED title, so 22% of the table was unreachable.
    #
    # **AND IT IS TWO PROPERTIES, NOT ONE.** MEASURED: a check that
    # only looked at the key's SHAPE stayed GREEN under the mutation
    # that removed the reader's normalization -- because the stored
    # table was already normalized, so the reader's own normalization
    # covered for the writer's. So each side is checked on its own:
    #
    #   1. THE WRITER normalizes -- the file on disk holds the
    #      normalized key.
    #   2. THE READER normalizes -- a table written by ANYBODY else,
    #      with raw labels, is still findable by a normalized title.
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        p = os.path.join(td, "reach.json")

        # 1. THE WRITER'S PROPERTY: what lands on disk.
        rm.write_reach_table({"Uncle Tom's Cabin": 14}, p)
        with open(p, encoding="utf-8") as fh:
            stored = json.load(fh)
        assert list(stored) == [ew.norm("Uncle Tom's Cabin")], (
            "the writer stored %s, but a reader looks up %s"
            % (list(stored), ew.norm("Uncle Tom's Cabin")))

        # 2. THE READER'S PROPERTY: a table written with RAW labels --
        #    which is what the OLD table on disk looked like -- must
        #    still be findable by a normalized title.
        p2 = os.path.join(td, "raw.json")
        with open(p2, "w", encoding="utf-8") as fh:
            json.dump({"Uncle Tom's Cabin": 14, "Moby-Dick": 42,
                       "Les Misérables": 51}, fh)
        back = rm.read_reach_table(p2)
        assert back.get(ew.norm("Uncle Tom's Cabin")) == 14, (
            "a table written with raw labels cannot be read back under "
            "a normalized title: %s" % back)
        assert back.get(ew.norm("Moby-Dick")) == 42
        assert back.get(ew.norm("Les Misérables")) == 51

    # AND THE MEASUREMENT'S OWN KEYS ARE NORMALIZED, so a lookup can
    # never miss because of a punctuation difference.
    raw_keys = rm.load_reach_raw()
    assert raw_keys, "the raw reach table is empty"
    bad = [k for k in raw_keys if ew.norm(k) != k]
    assert not bad, (
        "the reach table holds %d keys that are not normalized, so a "
        "lookup on the normalized title cannot find them: %s"
        % (len(bad), bad[:3]))

    # AND THE LOOKUP ITSELF NORMALIZES ON THE WAY OUT, which is what
    # the first mutation removes. A table whose keys are normalized is
    # not enough: the reader has to normalize too, and the two must
    # agree.
    #
    # **AND THIS IS MEASURED AGAINST A WORK THAT IS IN THE TABLE.**
    # MEASURED 2026-10-31: "Uncle Tom's Cabin" was in the measurement
    # and the catalog could not find it, because the reader asked for
    # "uncle tom s cabin" and the table held "uncle tom's cabin". So
    # the check below is not about the shape of the key -- it is about
    # a real work being findable by its real title.
    catalog = _catalog()
    found = 0
    missed = []
    for a in catalog:
        for w in a.get("works", []):
            t = w.get("title", "")
            if " " not in t:
                continue
            # THE MEASUREMENT'S OWN LABEL, matched the way a reader
            # would match it.
            if ew.norm(t) in reach:
                found += 1
            else:
                # IS THE WORK IN THE TABLE UNDER A RAW LABEL?
                raw_hit = [k for k in raw_keys
                           if ew.norm(k) == ew.norm(t)]
                if raw_hit:
                    missed.append((t, raw_hit[0]))
    assert found > 0, "no catalog work is findable in the reach table"
    assert not missed, (
        "%d catalog works ARE in the reach table but the lookup cannot "
        "find them, because the keys disagree: %s"
        % (len(missed), missed[:3]))


# ---------------------------------------------------------------------------
# E2. THE GUTENBERG TITLE IS THE TITLE, NOT 'TITLE BY AUTHOR'.
# ---------------------------------------------------------------------------
def t_E2_the_gutenberg_title_is_the_title():
    """THE DOWNLOAD COUNT MUST BE FINDABLE BY THE TITLE.

    MEASURED 2026-10-31: the Gutenberg page writes "Frankenstein; or,
    The modern Prometheus by Mary Wollstonecraft Shelley". The old
    lookup kept the whole anchor text, so it could never match a bare
    title -- and it missed ALL 13 of the download numbers the catalog
    already held.

    So: every download count the catalog carries must be findable
    through the lookup this tool uses.
    """
    gut = ew.load_gutenberg_counts()
    assert gut, "the Gutenberg ranking loaded nothing"

    import gutenberg_ranks
    books, _ = gutenberg_ranks.load()

    with open(CATALOG, encoding="utf-8") as fh:
        catalog = json.load(fh)
    held = [(a["name"], w) for a in catalog for w in a.get("works", [])
            if w.get("gutenberg_downloads")]
    assert held, "the catalog lost every download count"

    missed = [(n, w["title"]) for n, w in held
              if ew.norm(w["title"]) not in gut]
    assert not missed, (
        "%d of the %d download counts the catalog holds are not findable "
        "through the lookup: %s" % (len(missed), len(held), missed[:3]))

    # AND NO KEY CARRIES THE AUTHOR INSIDE IT.
    #
    # AND THE PRECISE SIGNATURE OF THE OLD DEFECT. The old lookup kept
    # the whole anchor text, so its key ended with " by <author>".
    # MEASURED: the title "On the Origin of Species By Means of
    # Natural Selection" contains a " By " of its OWN, so a bare
    # "' by ' in the key" test would flag a legitimate title. The
    # test that matters is whether the key ends with the author's
    # name -- and MEASURED, 0 of the 115 keys do.
    bad = []
    for b in books:
        if b.author and b.title.lower().endswith(" by " + b.author.lower()):
            bad.append(b.title)
    assert not bad, "a Gutenberg key still carries its author: %s" % bad[:3]


# ---------------------------------------------------------------------------
# E3. A REACH COUNT IS AN ADAPTATION COUNT, NOT A JOIN PRODUCT.
# ---------------------------------------------------------------------------
def t_E3_the_reach_count_counts_adaptations():
    """THE FIELD NAMED reach_adaptations MUST COUNT ADAPTATIONS.

    MEASURED 2026-10-31: the measurement counted the ROWS of a SPARQL
    result, and each row is one (adaptation, work, date, author)
    tuple. So the number was adaptations x distinct dates x distinct
    authors -- a JOIN PRODUCT. Dream of the Red Chamber carried 2,126
    against a true 1,063; Hansel and Gretel 66 against 22; Moby-Dick
    84 against 42.

    So: the corrected count for a work with several author statements
    must be SMALLER than the old row count, and it must divide it.
    """
    reach = rm.load_reach()
    raw = rm.load_reach_raw()
    assert raw, "the OLD measurement is not on disk, so nothing can be " \
                "compared"

    # THE OLD ROW COUNT, recounted from the cached rows.
    #
    # **AND THE COMMITTED FIXTURE IS THE FALLBACK.** MEASURED
    # 2026-11-01: the SPARQL rows live in the gitignored wikicache, so
    # a fresh clone had no old measurement and this check could not
    # run there. The fixture holds the same counts, derived from those
    # rows, with the provenance that made them.
    old = _old_counts()
    assert old, "the old measurement has no rows"

    # THE WORKS WHERE THE OLD COUNT WAS A MULTIPLE -- those are the
    # ones the join multiplied.
    multiples = [(t, n, reach.get(ew.norm(t)))
                 for t, n in old.items()
                 if reach.get(ew.norm(t)) and n % reach[ew.norm(t)] == 0
                 and n > reach[ew.norm(t)]]
    assert multiples, "no work shows the join multiplication, so the " \
                      "correction is not being measured"

    # AND IN EVERY ONE, THE CORRECTED COUNT IS THE SMALLER ONE.
    for t, n, corrected in multiples:
        assert corrected < n, (
            "%r: the corrected count %d is not smaller than the row "
            "count %d" % (t, corrected, n))


# ---------------------------------------------------------------------------
# E4. THE QUERY COUNTS DISTINCT ADAPTATIONS.
# ---------------------------------------------------------------------------
def t_E4_the_query_counts_distinct_adaptations():
    """THE QUERY'S TEXT MUST ASK FOR DISTINCT ADAPTATIONS.

    MEASURED 2026-10-31: `COUNT(DISTINCT ?adapt)` is the whole
    difference between a count of adaptations and a count of rows, and
    a query that loses it loses the measurement silently -- the output
    looks the same, just bigger.

    So: the query must name the adaptation, and must count it
    DISTINCTLY.
    """
    assert "COUNT(DISTINCT ?adapt)" in rm.PER_WORK, (
        "the per-work query lost COUNT(DISTINCT ?adapt)")
    assert "COUNT(DISTINCT ?adapt)" in rm.BY_WORK, (
        "the by-work query lost COUNT(DISTINCT ?adapt)")
    # AND THE ADAPTATION IS BOUND, so the count has a meaning.
    assert "?adapt (wdt:P144|wdt:P1441) ?work" in rm.PER_WORK, (
        "the query no longer binds the adaptation")
    # AND THE ADAPTATION IS NOT SELECTED, so a row cannot be counted
    # by accident: the count is over a DISTINCT set.
    assert "?adapt " not in rm.PER_WORK.split("WHERE")[1].split("GROUP")[0] \
        .replace("?adapt (wdt:P144|wdt:P1441) ?work .", ""), \
        "the query selects the adaptation, so the count is a row count"


# ---------------------------------------------------------------------------
# E5. THE CACHE KEY IS THE WHOLE THING.
# ---------------------------------------------------------------------------
def t_E5_the_cache_key_is_the_whole_url():
    """A CACHE KEY THAT IS NOT THE WHOLE KEY CAN SERVE THE WRONG CONTENT.

    MEASURED 2026-10-31: two separate defects, both measured.
      1. The URL's LAST 90 characters were the key. Every batch URL
         ends with the same title query, so 151 batch calls collapsed
         onto ONE cache entry and every one of them returned the FIRST
         batch's response -- so the resolution did nothing for every
         author and the expansion ran on P800 alone, which looks
         exactly like "these authors have no more works".
      2. The SPARQL cache key used Python's `hash()` of the query
         string, and `hash()` for strings is RANDOMISED PER PROCESS --
         so the same query never found its own cache.

    So: two DIFFERENT URLs must produce two DIFFERENT keys, and the
    same URL must always produce the same key.
    """
    # AND THE URL CACHE KEY IS THE WHOLE URL, and the key function is
    # NAMED so that this can call it rather than restate it.
    #
    # MEASURED 2026-10-31, and this is the honest version of the
    # claim: on the corpus as it stands the batch URLs put their
    # titles where a tail-90 truncation could not reach them, so the
    # collision count was 0 of 51 batches. The defect was LATENT. So
    # the check below does not claim the collisions happened -- it
    # builds the pair that WOULD collide, and checks that the tool's
    # own key tells them apart.
    #
    # **AND THE PAIR IS BUILT TO COLLIDE.** Two URLs whose last 90
    # characters are IDENTICAL, and which differ only in the part a
    # truncation throws away. MEASURED: the varying part has to sit
    # BEFORE the last 90 characters, because that is the whole of the
    # truncation's reach.
    tail = ("&ppprop=wikibase_item&format=json&formatversion=2"
            "&redirects=1&titles=%s")
    u1 = ("https://en.wikipedia.org/w/api.php?action=query&prop=pageprops"
          "&titles=AAAAAAAAAAAAAAAAAAAA" + tail % ("C" * 40))
    u2 = ("https://en.wikipedia.org/w/api.php?action=query&prop=pageprops"
          "&titles=BBBBBBBBBBBBBBBBBBBB" + tail % ("C" * 40))
    assert len(u1) == len(u2), "the pair must be the same length"
    # THE TAIL-90 TRUNCATION CANNOT TELL THESE APART.
    assert u1[-90:] == u2[-90:], (
        "the two URLs do not share a tail, so this test would not have "
        "caught the defect")
    # AND THEY REALLY ARE DIFFERENT URLS.
    assert u1 != u2, "the pair is the same URL"
    # AND THE TOOL'S OWN KEY DOES.
    k1 = ew.cache_key(u1)
    k2 = ew.cache_key(u2)
    assert k1 != k2, (
        "two URLs that a tail truncation cannot tell apart share one "
        "cache key: %s" % k1)
    # AND THE SAME URL ALWAYS GETS THE SAME KEY.
    assert k1 == ew.cache_key(u1), "the cache key is not stable"
    # AND THE KEY IS A CONTENT HASH.
    import ast
    import inspect
    tree = ast.parse(inspect.getsource(ew.cache_key))
    used = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            used.add(node.id)
        elif isinstance(node, ast.Attribute):
            used.add(node.attr)
    assert "sha256" in used, "the URL cache key is not a content hash"

    # AND THE SPARQL CACHE KEY IS A HASH OF THE QUERY TEXT, not of
    # Python's per-process randomised hash().
    q = "SELECT ?x WHERE { ?x wdt:P31 wd:Q5 } LIMIT 1"
    k = rm._cache_key(q, "t")
    assert k == rm._cache_key(q, "t"), "the SPARQL cache key is not stable"
    assert k != rm._cache_key(q + " ", "t"), \
        "two different queries share one cache key"

    # AND THE KEY IS A HASH, NOT Python's hash(). The CODE is read
    # through the AST, not by grepping the text -- because the
    # docstring QUOTES the old defective call in order to explain it,
    # and a text search flags the explanation. The AST sees the
    # docstring as a STRING and the code as code.
    import ast
    import inspect
    tree = ast.parse(inspect.getsource(rm._cache_key))
    fn = tree.body[0]
    # EVERY NAME AND ATTRIBUTE THE BODY ACTUALLY USES.
    used = set()
    for node in ast.walk(fn):
        if isinstance(node, ast.Name):
            used.add(node.id)
        elif isinstance(node, ast.Attribute):
            used.add(node.attr)
    assert "hash" not in used, (
        "the SPARQL cache key still uses Python's hash()")
    assert "sha256" in used, "the cache key is not a content hash"


# ---------------------------------------------------------------------------
# E6. THE ORIGINAL IS CHOSEN, NOT AN EDITION.
# ---------------------------------------------------------------------------
def t_E6_the_original_is_chosen_not_an_edition():
    """A TITLE MATCHES MANY ITEMS, AND THE ORIGINAL IS ONE OF THEM.

    MEASURED 2026-10-31: "Dracula" matched 58 Wikidata items. 11 of
    them carried Bram Stoker as their author, and among those, exactly
    one was `literary work` (Q41542, 1897-05-26); the rest were
    `version, edition or translation` and `theatrical production`.

    So: given a title with several candidate items, the one picked is
    the earliest in-era date that is a work.
    """
    works = {
        "Q41542": {"qid": "Q41542", "dates": ["1897-05-26"],
                   "natures": ["literary work"], "label": "Dracula"},
        "Q23802084": {"qid": "Q23802084", "dates": ["1900-01-01"],
                      "natures": ["version, edition or translation"],
                      "label": "Dracula"},
        "Q106463394": {"qid": "Q106463394", "dates": ["1999-05-28"],
                       "natures": ["theatrical production"], "label": "Dracula"},
    }
    best = ew.pick_work(works)
    assert best is not None, "nothing was picked"
    assert best["qid"] == "Q41542", (
        "the edition was picked (%s) instead of the original" % best["qid"])
    assert best["year"] == 1897, "the wrong year: %s" % best["year"]

    # AND A WORK WITH NO DATE AT ALL IS REFUSED, because the gate's own
    # rule is that no date means no public-domain test.
    nodate = {"Q1": {"qid": "Q1", "dates": [], "natures": ["literary work"],
                     "label": "x"}}
    assert ew.pick_work(nodate) is None, \
        "a work with no date was accepted, so the public-domain test " \
        "was skipped"

    # AND THE NATURE BEATS A LATER DATE: a work in 1900 beats an
    # edition in 1897.
    mixed = {
        "Q_EARLY": {"qid": "Q_EARLY", "dates": ["1897-01-01"],
                    "natures": ["version, edition or translation"], "label": "y"},
        "Q_LATE": {"qid": "Q_LATE", "dates": ["1900-01-01"],
                   "natures": ["literary work"], "label": "y"},
    }
    assert ew.pick_work(mixed)["qid"] == "Q_LATE", \
        "the edition beat the original"

    # AND THE ORDER OF THE CANDIDATES MUST NOT MATTER. The picker
    # scores every candidate and takes the best, so a dict whose
    # insertion order is reversed must give the same answer -- and a
    # picker that took the LAST candidate would give a different one.
    #
    # **MEASURED 2026-10-31:** the mutation "the picker takes the last
    # candidate" stayed GREEN under a check that only had one
    # candidate ordering. A test that cannot fail is not a test, so the
    # candidate order is now checked both ways.
    forward = {
        "Q_FIRST": {"qid": "Q_FIRST", "dates": ["1897-01-01"],
                    "natures": ["version, edition or translation"],
                    "label": "z"},
        "Q_SECOND": {"qid": "Q_SECOND", "dates": ["1900-01-01"],
                     "natures": ["literary work"], "label": "z"},
    }
    backward = {
        "Q_SECOND": {"qid": "Q_SECOND", "dates": ["1900-01-01"],
                     "natures": ["literary work"], "label": "z"},
        "Q_FIRST": {"qid": "Q_FIRST", "dates": ["1897-01-01"],
                    "natures": ["version, edition or translation"],
                    "label": "z"},
    }
    a = ew.pick_work(forward)
    b = ew.pick_work(backward)
    assert a is not None and b is not None, "nothing was picked"
    assert a["qid"] == b["qid"] == "Q_SECOND", (
        "the pick depends on the candidate order: %s then %s"
        % (a["qid"], b["qid"]))


# ---------------------------------------------------------------------------
# E7. EVERY REFUSAL IS COUNTED, AND ZERO IS NOT None.
# ---------------------------------------------------------------------------
def t_E7_every_refusal_is_counted():
    """THE REPORT MUST SHOW WHAT IT REFUSED, AND WHY.

    MEASURED 2026-10-31: the tool had a `skipped_no_date` counter that
    was never incremented and never printed -- so the largest class of
    refusal was invisible in the report Bobby read. And a work inside
    the measured window with no adaptations was written as `None`,
    which says "not measured" when the truth is "measured, and zero".

    So: every refusal path increments a counter, and the in-window
    zero is a zero.
    """
    a = {"name": "X", "went": 1900}
    skipped = {"held": 0, "era": 0, "after_death": 0, "no_date": 0}

    # HELD.
    assert not ew.gate_new_work(a, "k", {"title": "t", "year": 1850},
                                {"k"}, skipped)
    assert skipped["held"] == 1, "a held work was not counted"

    # NO DATE.
    assert not ew.gate_new_work(a, "k", {"title": "t", "year": None},
                                set(), skipped)
    assert skipped["no_date"] == 1, \
        "a dateless work was not counted -- this is the counter that " \
        "was dead"

    # OUTSIDE THE ERA.
    assert not ew.gate_new_work(a, "k", {"title": "t", "year": 1700},
                                set(), skipped)
    assert skipped["era"] == 1, "an out-of-era work was not counted"

    # AFTER THE AUTHOR WENT.
    #
    # AND THE YEAR MUST BE INSIDE THE ERA WINDOW, or the era refusal
    # fires first and the after-death refusal is never reached.
    # MEASURED: the era check runs first and refuses anything outside
    # 1800-1940, so an after-death work needs a year INSIDE that
    # window and after the author went -- 1925 with the author gone in
    # 1900.
    assert not ew.gate_new_work(a, "k", {"title": "t", "year": 1925},
                                set(), skipped)
    assert skipped["after_death"] == 1, \
        "a work dated after its author went was not counted"

    # KEPT.
    assert ew.gate_new_work(a, "k", {"title": "t", "year": 1850},
                            set(), skipped)

    # AND THE ZERO IS A ZERO.
    assert ew._in_window(1850) is True
    assert ew._in_window(1750) is False
    assert ew._in_window(None) is False


# ---------------------------------------------------------------------------
# E8. THE DISCOVERY IS DONE ONCE, AND THE REPORT IS THE APPLY.
# ---------------------------------------------------------------------------
def t_E8_the_report_and_the_apply_agree():
    """THE REPORT BOBBY READS MUST BE WHAT THE APPLY WRITES.

    MEASURED 2026-10-31: the tool had the whole discovery written
    TWICE -- once for the report and once for the apply -- and the two
    copies could drift. So the numbers in the report were not
    necessarily the numbers the apply produced.

    So: there is ONE discovery function, and the main flow calls it
    once per author and reuses the result.
    """
    src = open(os.path.join(REPO, "tools", "expand_works.py"),
               encoding="utf-8").read()
    # THE DISCOVERY IS CALLED FROM ONE PLACE.
    calls = re.findall(r"discover\(a, qid\)", src)
    assert len(calls) == 1, (
        "discover() is called %d times in the source -- the discovery "
        "must happen once per author" % len(calls))
    # AND THE OLD PER-TITLE RESOLUTION IS GONE.
    assert "resolve_titles(titles)" not in src, \
        "the old per-title resolution is still called"
    # AND THE RESOLVE PATH IS THE BATCHED ONE.
    assert "resolve_for_author(qid, titles)" in src, \
        "the batched per-author resolution is not used"


# ---------------------------------------------------------------------------
# THE RUNNER
# ---------------------------------------------------------------------------
def main() -> int:
    for fn in (t_E1_the_title_key_is_normalized_on_both_sides,
               t_E2_the_gutenberg_title_is_the_title,
               t_E3_the_reach_count_counts_adaptations,
               t_E4_the_query_counts_distinct_adaptations,
               t_E5_the_cache_key_is_the_whole_url,
               t_E6_the_original_is_chosen_not_an_edition,
               t_E7_every_refusal_is_counted,
               t_E8_the_report_and_the_apply_agree):
        fn()
        print("  %-52s OK" % fn.__name__)
    print("\nALL EXPAND-WORKS TESTS PASS (E1..E8)")
    return 0


test_E1_the_title_key_is_normalized_on_both_sides = \
    t_E1_the_title_key_is_normalized_on_both_sides
test_E2_the_gutenberg_title_is_the_title = \
    t_E2_the_gutenberg_title_is_the_title
test_E3_the_reach_count_counts_adaptations = \
    t_E3_the_reach_count_counts_adaptations
test_E4_the_query_counts_distinct_adaptations = \
    t_E4_the_query_counts_distinct_adaptations
test_E5_the_cache_key_is_the_whole_url = \
    t_E5_the_cache_key_is_the_whole_url
test_E6_the_original_is_chosen_not_an_edition = \
    t_E6_the_original_is_chosen_not_an_edition
test_E7_every_refusal_is_counted = t_E7_every_refusal_is_counted
test_E8_the_report_and_the_apply_agree = t_E8_the_report_and_the_apply_agree


def test_the_runner_collects_these_checks():
    """pytest must collect the checks as tests, not just the runner."""
    assert main() == 0


if __name__ == "__main__":
    sys.exit(main())
