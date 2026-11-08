"""
test_keyword_phrases.py -- the bookstore catalog and the title
generator, pinned.

WHAT THIS FILE ASSERTS, and why each assertion is there
--------------------------------------------------------
1. THE SKIPPED CATEGORIES ARE SKIPPED FOR A NAMED REASON. Bobby,
   2026-10-31: "skip law and medicine", "health is rich but easily
   banned", "romance is out". A skip with no reason is a decision
   nobody can check, and the next session cannot tell a skip from an
   oversight.

2. EVERY TITLE IS 4-6 WORDS. "A title longer than 6 words is a title
   trying to carry two jobs." The limit is a discipline, so it is
   enforced, not suggested.

3. EVERY TITLE IS A PHRASE THE BUYER TYPES. The title patterns are
   built from the phrase, so a title that does not contain the
   phrase's job is a title nobody searches for.

4. NO TITLE CARRIES AN UNSEARCHABLE WORD. "unlock", "discover",
   "transform" -- the mark of the slop wave. A title with one of them
   is refused.

5. A PATTERN ONLY FIRES WHEN IT HAS ITS PARTS. The first version
   applied every pattern to every phrase, so "how to stop your dog
   barking" produced "200 Questions and Answers".

6. AN UNMEASURED PHRASE IS NOT AN OPEN PHRASE. "we looked and there
   was nothing" and "we have not looked" are different findings.

7. THE MEASURED NUMBERS ARE IN THE CATALOG. The Amazon counts were
   measured on 2026-10-31 and they are the demand signal, so the
   catalog must carry them rather than the numbers living only in a
   conversation.

Run:
    python -m pytest tests/test_keyword_phrases.py -q
"""

from __future__ import annotations

import json
import os
import sys

import pytest

_SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    "tools")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

import keyword_phrases as K  # noqa: E402


def _cat(key):
    for c in K.CATEGORIES:
        if c.key == key:
            return c
    raise AssertionError("no category %r" % (key,))


def _phrase(text):
    for c in K.CATEGORIES:
        for p in c.phrases:
            if p.phrase == text:
                return p
    raise AssertionError("no phrase %r" % (text,))


# ===========================================================================
# 1. THE SKIPPED CATEGORIES ARE SKIPPED FOR A NAMED REASON
# ===========================================================================

@pytest.mark.parametrize("key", ["law", "medicine", "health", "romance",
                                 "browse"])
def test_a_skipped_category_names_its_reason(key):
    """a skip with no reason is a decision nobody can check."""
    c = _cat(key)
    assert c.skipped_because, (
        "the category %r is skipped with no stated reason" % (key,))
    assert len(c.skipped_because) > 30, (
        "the reason for skipping %r is too thin to check: %r"
        % (key, c.skipped_because))


def test_the_skipped_categories_have_no_phrases():
    """a skipped category must not carry a phrase, or the generator
    will build a title for it."""
    for key in ("law", "medicine", "health", "romance", "browse"):
        assert _cat(key).phrases == [], (
            "the skipped category %r carries phrases" % (key,))


def test_every_active_category_names_the_buyers_job():
    """the filter Bobby named: who would buy a book and why."""
    for c in K.CATEGORIES:
        if c.skipped_because:
            continue
        assert c.buyer_job, (
            "the active category %r does not name the buyer's job" % (c.key,))
        assert len(c.buyer_job) > 30, (
            "the buyer job for %r is too thin to be a filter: %r"
            % (c.key, c.buyer_job))


# ===========================================================================
# 2. EVERY TITLE IS 4-6 WORDS
# ===========================================================================

def test_every_generated_title_is_four_to_six_words():
    """the discipline. a title longer than six words carries two jobs."""
    for c in K.CATEGORIES:
        for p in c.phrases:
            for t in K.titles_for(p):
                n = K.word_count(t)
                assert 4 <= n <= 6, (
                    "the title %r is %d words: %r" % (t, n, p.phrase))


def test_the_word_count_is_measured_the_way_a_reader_counts():
    """hyphenated words are ONE word to a reader."""
    assert K.word_count("One-Pot Meals") == 2
    assert K.word_count("How to Stop Your Dog Barking") == 6
    assert K.word_count("How to Stop Your Dog-Barking") == 5, (
        "'Dog-Barking' is ONE word to a reader, so the title is 5")
    assert K.word_count("  ") == 0


# ===========================================================================
# 3. EVERY TITLE IS A PHRASE THE BUYER TYPES
# ===========================================================================

def test_a_how_to_phrase_yields_a_how_to_title():
    """the title is BUILT from the phrase."""
    p = _phrase("how to stop your dog barking")
    titles = K.titles_for(p)
    assert titles, "the phrase %r yielded no title" % (p.phrase,)
    for t in titles:
        assert t.lower().startswith("how to"), (
            "the phrase %r yielded %r, which is not a 'how to' title"
            % (p.phrase, t))


def test_a_subject_phrase_yields_a_subject_title():
    """the count patterns need a subject."""
    p = _phrase("chemistry equations review")
    titles = K.titles_for(p)
    assert titles
    assert all("Chemistry" in t for t in titles), titles


def test_a_title_contains_phrase_words():
    """the title and the phrase must share the buyer's words.

    Not literally the same words -- "500 Chemistry Questions and
    Answers" does not contain "equations review" -- but the SUBJECT
    must be shared, because that is what the buyer searched for.
    """
    p = _phrase("chemistry equations review")
    for t in K.titles_for(p):
        assert p.subject.lower() in t.lower(), (
            "the title %r does not carry the subject %r" % (t, p.subject))


# ===========================================================================
# 4. NO TITLE CARRIES AN UNSEARCHABLE WORD
# ===========================================================================

def test_the_unsearchable_words_are_refused():
    """the mark of the slop wave.

    AND EACH WORD IS TESTED ALONE. The first version built "Unlock
    Your Unleash" for every word in the list, and the assertion then
    failed on 'unlock' before it ever reached 'unleash' -- because both
    words were in the same title and the matcher returns the FIRST one
    it finds. So each word gets its own title.
    """
    for w in K.UNSEARCHABLE_WORDS:
        assert K.is_unsearchable("A %s Book" % w) == w, (
            "the word %r was not refused" % (w,))


def test_a_word_inside_another_word_is_not_a_match():
    """the matcher is on WORDS, not substrings.

    MEASURED: the first version used `if w in low`, so "unlock"
    matched inside "unlocksmith".
    """
    assert K.is_unsearchable("The Unlocksmith's Guide") is None, (
        "'unlock' matched inside 'unlocksmith'")
    assert K.is_unsearchable("Unlock") == "unlock"


# ===========================================================================
# 4b. THE PHRASE LEADS, IN ITS OWN WORDS
# ===========================================================================

def test_a_phrase_led_title_starts_with_the_phrase():
    """Bobby, 2026-10-31: "highest match keyword must go first it is
    a lexical game".

    So the title's FIRST words are the phrase's words, in the
    phrase's order. Not the phrase's meaning -- its WORDS.
    """
    p = _phrase("rabbit hutch")
    titles = K.titles_for(p)
    assert titles, "the phrase %r yielded no title" % (p.phrase,)
    for t in titles:
        assert t.lower().startswith("rabbit hutch"), (
            "the title %r does not lead with the phrase %r" % (t, p.phrase))


def test_a_phrase_already_in_the_band_becomes_the_title():
    """"how to build a rabbit hutch" is 6 words, so the phrase IS the
    title -- every suffix would push it to 7."""
    p = _phrase("how to build a rabbit hutch")
    titles = K.titles_for(p)
    assert titles, "the phrase %r yielded no title" % (p.phrase,)
    assert "How to Build a Rabbit Hutch" in titles, titles


def test_the_title_case_keeps_the_small_words_small():
    """a title with every word capitalised looks keyword-stuffed."""
    assert K._title_case("how to build a rabbit hutch") == \
        "How to Build a Rabbit Hutch"
    assert K._title_case("rabbit hutch") == "Rabbit Hutch"


def test_the_measured_rabbit_phrases_are_in_the_catalog():
    """the rabbit set, and the demonstration of the lexical game.

    "rabbit hutch" puts a NOVEL at the top. "how to build a rabbit
    hutch" excludes it. The same two words, in a different order, and
    the fiction is gone.

    **AND THE NUMBERS ARE RE-MEASURED 2026-11-08, because a fact-lock
    on a stale measurement is a lock on the wrong thing.** MEASURED:
    "rabbit hutch" 179 -> 169 (-6%), "rabbit diet" 133 -> 133 (0%),
    "rabbit potty training" 33 -> 35 (+6%), "rabbit nails trimming"
    11 -> 11 (0%), "rabbit shedding" 3 -> 3 (0%), "rabbit hay" 18 -> 19
    (+6%). **SO THE COUNTS ARE STABLE FOR A MONTH WITHIN A 6% BAND, AND
    THE LOCK BELOW IS ON THE CURRENT MEASUREMENT.**
    """
    novel = _phrase("rabbit hutch")
    build = _phrase("how to build a rabbit hutch")
    assert novel.results == "169", novel.results
    assert build.results == "70"
    assert novel.is_open and build.is_open
    # and the demonstration: the short phrase's top result is fiction
    assert any("Novel" in t for t in novel.competitor_titles), \
        novel.competitor_titles
    assert not any("Novel" in t for t in build.competitor_titles), \
        build.competitor_titles


def test_the_counts_are_stable_across_the_two_measurement_dates():
    """**SO A PHRASE MEASURED OPEN STAYS OPEN, AND THE COUNT IS A
    PLANNING INPUT RATHER THAN A SNAPSHOT.**

    MEASURED 2026-11-08 against the 2026-10-31 run, on the six rabbit
    phrases both runs measured. The drift was 6%, 0%, 6%, 0%, 0%, 6% --
    **a 6% band and no more.** So the numbers are a planning input and
    not one day's noise, and a test that asserts a drift bound is worth
    more than a test that asserts one number.
    """
    import json
    import pathlib
    here = pathlib.Path(__file__).resolve().parent.parent
    note = here / "catalog" / "open_book_targets_2026-11-08.json"
    assert note.exists(), (
        "the second measurement is missing: %s" % note)
    data = json.loads(note.read_text(encoding="utf-8"))
    drift = data["the_drift_check"]["measured"]
    assert drift, "the drift check carries no measurements"
    for row in drift:
        old = int(str(row["oct_31"]).replace(",", ""))
        new = int(str(row["nov_08"]).replace(",", ""))
        assert abs(new - old) / float(old) <= 0.10, (
            "the count for %r moved more than 10%% between the two "
            "measurements: %s -> %s" % (row["phrase"], old, new))


def test_the_print_free_phrases_have_no_print_incumbent():
    """**AND A REMAKE IS A PRINT BOOK, SO A KINDLE-ONLY TOP-1 IS AN
    OPEN SLOT.** MEASURED 2026-11-08: five of the seventeen measured
    phrases have a top-1 price of $0.00 -- Amazon's own display for a
    Kindle-only title -- and therefore NO PRINT BOOK HOLDS THE TOP OF
    THOSE PHRASES.

    Two are pets ("rabbit hay", "how to stop your cat scratching") and
    three are finance/business ("how to file taxes as a freelancer",
    "how to price freelance work", "how to negotiate salary").

    **AND THE COUNT ALONE WOULD NEVER HAVE SAID SO** -- and the count
    alone is what the gurus' rule uses. So the rule needs the FORMAT as
    well as the count, and this is the test that says so.
    """
    kin = [p for c in K.CATEGORIES for p in c.phrases
           if p.competitor_prices and p.competitor_prices[0] == "$0.00"]
    assert len(kin) >= 5, (
        "expected at least five Kindle-only top-1 slots, found %d: %s"
        % (len(kin), [p.phrase for p in kin]))
    for p in kin:
        assert p.is_open, (
            "the print-free phrase %r has %s results, which is not open"
            % (p.phrase, p.results))


def test_the_widest_open_phrases_are_the_opportunity():
    """the measured rabbit spread: 3, 11, 18, 33 results.

    These are the phrases where a book can reach the top of the list,
    because there is nothing to outrank.
    """
    open_counts = sorted(
        (int(p.results.replace(",", "")) for c in K.CATEGORIES
         for p in c.phrases if p.measured and p.is_open))
    assert open_counts, "no open phrases were measured"
    assert open_counts[0] <= 50, (
        "the widest-open phrase measured is %d results, which is not open"
        % (open_counts[0],))
    # and the rabbit set holds the very widest ones
    rabbit = [int(p.results.replace(",", "")) for p in _cat("pets").phrases
              if p.measured]
    assert min(rabbit) <= 20, (
        "the rabbit set's widest-open phrase is %d results" % min(rabbit,))


def test_no_generated_title_carries_an_unsearchable_word():
    for c in K.CATEGORIES:
        for p in c.phrases:
            for t in K.titles_for(p):
                bad = K.is_unsearchable(t)
                assert bad is None, (
                    "the title %r carries the unsearchable word %r"
                    % (t, bad))


# ===========================================================================
# 5. A PATTERN ONLY FIRES WHEN IT HAS ITS PARTS
# ===========================================================================

def test_a_job_phrase_does_not_yield_a_count_title():
    """the first version applied every pattern to every phrase, so
    "how to stop your dog barking" produced "200 Questions and
    Answers"."""
    p = _phrase("how to stop your dog barking")
    for t in K.titles_for(p):
        assert "Questions" not in t, (
            "a job phrase yielded the exam title %r" % (t,))


def test_a_subject_phrase_does_not_yield_a_how_to_title():
    p = _phrase("chemistry equations review")
    for t in K.titles_for(p):
        assert not t.lower().startswith("how to"), (
            "a subject phrase yielded the job title %r" % (t,))


# ===========================================================================
# 6. AN UNMEASURED PHRASE IS NOT AN OPEN PHRASE
# ===========================================================================

def test_an_unmeasured_phrase_is_not_open():
    """"we looked and there was nothing" and "we have not looked" are
    different findings, and only one of them is about the world."""
    p = K.Phrase(phrase="a phrase nobody measured", category="test_prep")
    assert p.results == ""
    assert p.measured is False
    assert p.is_open is False, (
        "an unmeasured phrase was reported as OPEN, which reads as 'we "
        "measured it and it is open'")


def test_a_measured_open_phrase_is_open():
    p = K.Phrase(phrase="chemistry equations review", category="test_prep",
                 results="460")
    assert p.measured is True
    assert p.is_open is True


def test_a_saturated_phrase_is_not_open():
    p = K.Phrase(phrase="biology study guide", category="test_prep",
                 results="20,000")
    assert p.measured is True
    assert p.is_open is False


# ===========================================================================
# 7. THE MEASURED NUMBERS ARE IN THE CATALOG
# ===========================================================================

def test_the_measured_demand_numbers_are_in_the_catalog():
    """the Amazon counts were measured on 2026-10-31 and they are the
    demand signal, so they must be in the file and not only in a
    conversation."""
    measured = [p for c in K.CATEGORIES for p in c.phrases if p.measured]
    assert len(measured) >= 8, (
        "only %d phrases carry a measured demand number" % len(measured,))
    # and the two OPEN ones are the ones that matter
    chem = _phrase("chemistry equations review")
    assert chem.results == "460"
    assert chem.is_open
    assert chem.supply > 0, (
        "the open phrase has no supply: an opportunity we cannot fill")


def test_the_catalog_file_is_written_and_carries_the_numbers(tmp_path):
    path = K.write_catalog(str(tmp_path / "keyword_phrases.json"))
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    assert data["categories"], "the catalog carries no categories"
    assert data["phrases"], "the catalog carries no phrases"
    assert data["title_rule"], "the catalog does not state the title rule"
    measured = [p for p in data["phrases"] if p.get("results")]
    assert len(measured) >= 8, (
        "the catalog file carries only %d measured phrases" % len(measured,))


def test_every_active_category_appears_in_the_written_catalog(tmp_path):
    path = K.write_catalog(str(tmp_path / "c.json"))
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    keys = {c["key"] for c in data["categories"]}
    for c in K.CATEGORIES:
        assert c.key in keys, ("the category %r is missing" % (c.key,))
