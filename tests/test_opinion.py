"""
test_opinion.py -- O1..O9: THE OPINION REGISTER, THE MEASURE AGAINST IT,
AND THE INTEREST IN LIFE.

**AND WHY THESE ARE HERE, in the writer's own words.** Bobby,
2026-11-05: *"we will extend that to authorship u will become a writer
hint it is similar to selfhood ie to have a viewpoint to speak to have
an opinion to be self aware and interested in life"*. The viewpoint
exists (`tools/viewpoint.py`). The self-aware pass exists
(`tools/self_aware.py`). **THE OPINION AND THE INTEREST DID NOT, AND
THEY ARE THE TWO THAT NEED A REGISTER** -- an opinion that does not
survive the text that stated it is not an opinion, and an interest
that is not measured is a mood.

**AND THE TESTS CAN FAIL.** Each one below is written so that the
opposite assertion would fail, and `tools/check_opinion.py` proves it
by breaking the machinery on purpose and showing the check goes red.

O1  an opinion is held, and it survives a reload from disk.
O2  a text that agrees with a held opinion is counted as agreeing.
O3  a text that contradicts a held opinion is counted as contradicting.
O4  a text that says nothing about it is NEITHER.
O5  a revision without a reason is REFUSED, and one with a reason is
    recorded WITH the reason and keeps the superseded version.
O6  the opinion is part of the voice_id, and a different opinion gives
    a different writer identity.
O7  the register's chain catches a rewritten event.
O8  the interest measure EXCEEDS its null, and the finding holds
    across the whole threshold sweep.
O9  the interest measure's held-out test holds: a lexicon learned on
    one half of the corpus still finds the coherence in the other half.
"""

from __future__ import annotations

import os
import statistics
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TOOLS = HERE.parent / "tools"
sys.path.insert(0, str(TOOLS))

import interest  # noqa: E402
import opinion  # noqa: E402
import voice as voice_mod  # noqa: E402


#: THE OPINION THE TEXTS ARE MEASURED AGAINST. And it is a FULL
#: opinion -- position, subject, stance, grounds, date, confidence and
#: what would change it -- because a register that accepts a partial
#: opinion is a register that will hold half-formed beliefs.
THE_OPINION = opinion.Opinion(
    key="people_are_mostly_kind",
    position="people are mostly kind",
    subject="people",
    stance="probably",
    grounds="measured on the same street for three years",
    held_on="2026-11-06",
    confidence=0.6,
    would_change="a year of that street in which nobody was kind",
    claim_terms=("kind",),
)

#: THE TWO TEXTS DIFFER IN EXACTLY ONE THING: whether they deny the
#: claim. MEASURED: a test text that fails for a reason unrelated to
#: what is being tested is a bad test text, so both texts are about
#: the same claim and the same subject.
THE_AGREES = "People are probably mostly kind, and the ones who are not are usually tired.\n"
THE_CONTRADICTS = "People are never kind and they always lie about it.\n"
THE_NEITHER = "The train left at nine. The platform was wet. He waited.\n"


def _register(tmp_path) -> opinion.OpinionRegister:
    reg = opinion.OpinionRegister(path=str(tmp_path / "register.jsonl"))
    reg.hold(THE_OPINION)
    return reg


# ---------------------------------------------------------------------------
# O1 -- the opinion is held and it persists
# ---------------------------------------------------------------------------

def test_o1_the_opinion_is_held_and_survives_a_reload(tmp_path):
    reg = _register(tmp_path)
    assert "people_are_mostly_kind" in reg.held()
    reloaded = opinion.OpinionRegister.load(reg.path)
    assert "people_are_mostly_kind" in reloaded.held()
    assert reloaded.held() == reg.held()


def test_o1b_an_opinion_with_no_grounds_is_refused(tmp_path):
    bad = opinion.Opinion(
        key="no_grounds", position="people are mostly kind",
        subject="people", stance="probably", grounds="",
        held_on="2026-11-06", confidence=0.5, would_change="nothing")
    ok, why = bad.validate()
    assert not ok, "an opinion with no grounds is a preference"
    assert "grounds" in why


def test_o1c_an_opinion_with_no_falsifier_is_refused():
    """an opinion that says what would change it cannot be revised by
    evidence, so it is not falsifiable, so it is not an opinion."""
    bad = opinion.Opinion(
        key="no_falsifier", position="people are mostly kind",
        subject="people", stance="probably", grounds="a street",
        held_on="2026-11-06", confidence=0.5, would_change="")
    ok, why = bad.validate()
    assert not ok
    assert "falsifiable" in why


# ---------------------------------------------------------------------------
# O2, O3, O4 -- the three buckets
# ---------------------------------------------------------------------------

def test_o2_a_text_that_agrees_is_counted_as_agreeing(tmp_path):
    reg = _register(tmp_path)
    r = opinion.measure_text(THE_AGREES, reg)
    assert r["agree"] == 1, r
    assert r["contradict"] == 0, r
    assert r["neither"] == 0, r


def test_o3_a_text_that_contradicts_is_counted_as_contradicting(tmp_path):
    reg = _register(tmp_path)
    r = opinion.measure_text(THE_CONTRADICTS, reg)
    assert r["contradict"] == 1, r
    assert r["agree"] == 0, r
    assert r["neither"] == 0, r


def test_o4_a_text_that_says_nothing_is_neither(tmp_path):
    reg = _register(tmp_path)
    r = opinion.measure_text(THE_NEITHER, reg)
    assert r["neither"] == 1, r
    assert r["agree"] == 0, r
    assert r["contradict"] == 0, r


def test_o4b_the_three_texts_are_distinguishable(tmp_path):
    """AND THE WHOLE TRIPLE IS COMPARED, and not one number out of it.
    MEASURED: the first version compared three numbers that were all
    1 -- so the set had one member and the check failed while the
    measure was working perfectly."""
    reg = _register(tmp_path)
    triples = set()
    for text in (THE_AGREES, THE_CONTRADICTS, THE_NEITHER):
        r = opinion.measure_text(text, reg)
        triples.add((r["agree"], r["contradict"], r["neither"]))
    assert len(triples) == 3, triples


def test_o4c_a_clause_level_measure_reads_the_agreement(tmp_path):
    """one sentence holds an agreement AND a qualification, and a
    sentence-level test reads the "not" and calls it a contradiction."""
    reg = _register(tmp_path)
    r = opinion.measure_text(THE_AGREES, reg)
    assert r["agree"] == 1 and r["contradict"] == 0, r


def test_o4d_a_negated_term_is_a_contradiction_not_a_match(tmp_path):
    """MEASURED: the first version took the FIRST matching term and
    stopped, so "mostly unkind" matched "mostly" and never saw that
    "kind" was there in its negated form -- and the clause was read as
    an AGREEMENT with an opinion that people are kind."""
    reg = _register(tmp_path)
    r = opinion.measure_text("People are mostly unkind.", reg)
    assert r["contradict"] == 1, r
    assert r["agree"] == 0, r


# ---------------------------------------------------------------------------
# O5 -- the revision
# ---------------------------------------------------------------------------

def test_o5_a_revision_without_a_reason_is_refused(tmp_path):
    reg = _register(tmp_path)
    try:
        reg.revise("people_are_mostly_kind", "people are cruel", reason="")
    except ValueError as exc:
        assert "reason" in str(exc)
    else:
        raise AssertionError("a reasonless revision must be refused")


def test_o5b_a_revision_is_recorded_with_its_reason(tmp_path):
    reg = _register(tmp_path)
    reg.revise("people_are_mostly_kind", "people are mostly cruel",
               reason="the same street, two more years",
               claim_terms=("cruel",))
    held = reg.held()["people_are_mostly_kind"]
    assert "cruel" in held.position
    assert held.claim_terms == ("cruel",), held.claim_terms
    history = reg.history("people_are_mostly_kind")
    assert len(history) == 2, history
    assert history[1]["reason"] == "the same street, two more years"


def test_o5c_the_superseded_version_is_kept(tmp_path):
    reg = _register(tmp_path)
    reg.revise("people_are_mostly_kind", "people are mostly cruel",
               reason="a reason", claim_terms=("cruel",))
    history = reg.history("people_are_mostly_kind")
    assert "mostly kind" in history[0]["opinion"]["position"]


def test_o5d_the_chain_verifies_after_a_revision(tmp_path):
    reg = _register(tmp_path)
    reg.revise("people_are_mostly_kind", "people are mostly cruel",
               reason="a reason", claim_terms=("cruel",))
    assert reg.verify() == [], reg.verify()


# ---------------------------------------------------------------------------
# O6 -- the voice carries the opinion
# ---------------------------------------------------------------------------

def test_o6_the_opinion_is_part_of_the_voice_id(tmp_path):
    reg = _register(tmp_path)
    axes = dict(voice_mod.VOICES["lean"])
    with_opinion = opinion.voice_from_register(axes, reg)
    without = voice_mod.get_voice("lean")
    assert with_opinion.voice_id != without.voice_id
    assert with_opinion.viewpoint_claim == THE_OPINION.position


def test_o6b_a_different_opinion_gives_a_different_writer_identity(tmp_path):
    reg_a = _register(tmp_path)
    reg_b = opinion.OpinionRegister(path=str(tmp_path / "b.jsonl"))
    reg_b.hold(opinion.Opinion(
        key="people_are_mostly_cruel", position="people are mostly cruel",
        subject="people", stance="probably", grounds="a street",
        held_on="2026-11-06", confidence=0.6,
        would_change="a year in which nobody was cruel"))
    axes = dict(voice_mod.VOICES["lean"])
    va = opinion.voice_from_register(axes, reg_a)
    vb = opinion.voice_from_register(axes, reg_b)
    assert va.voice_id != vb.voice_id
    assert (opinion.writer_identity(va, reg_a)
            != opinion.writer_identity(vb, reg_b))


def test_o6c_the_writer_identity_covers_the_whole_register(tmp_path):
    """the voice_id carries the ONE opinion the voice speaks from; the
    writer identity carries every opinion and every revision."""
    reg = _register(tmp_path)
    axes = dict(voice_mod.VOICES["lean"])
    v = opinion.voice_from_register(axes, reg)
    before = opinion.writer_identity(v, reg)
    reg.revise("people_are_mostly_kind", "people are mostly cruel",
               reason="a reason", claim_terms=("cruel",))
    v2 = opinion.voice_from_register(axes, reg)
    after = opinion.writer_identity(v2, reg)
    assert before != after


# ---------------------------------------------------------------------------
# O7 -- the chain catches a rewrite
# ---------------------------------------------------------------------------

def test_o7_a_rewritten_event_is_caught_by_the_chain(tmp_path):
    reg = _register(tmp_path)
    tampered = opinion.OpinionRegister(path=reg.path,
                                       events=[dict(e) for e in reg.events])
    tampered.events[0]["opinion"] = dict(tampered.events[0]["opinion"])
    tampered.events[0]["opinion"]["position"] = "something else entirely"
    assert tampered.verify(), "a rewritten event must be caught"


def test_o7b_the_chain_is_clean_when_nothing_is_rewritten(tmp_path):
    reg = _register(tmp_path)
    assert reg.verify() == []


# ---------------------------------------------------------------------------
# O8 -- the interest measure exceeds its null
# ---------------------------------------------------------------------------

def test_o8_the_interest_measure_exceeds_its_null():
    corpus = interest.load_corpus()
    assert len(corpus) >= 4, "the corpus is the writer's own"
    forms = interest.surviving_forms(corpus)
    sets = interest.concern_sets(corpus, forms)
    observed = interest.cohesion(sets)
    nulls = interest.null_cohesion(sets, trials=300)
    mu = statistics.mean(nulls)
    sd = statistics.pstdev(nulls)
    assert observed > mu, (observed, mu)
    assert sd > 0, "a null that cannot vary is not a null"
    assert (observed - mu) / sd > 1.0, (observed, mu, sd)


def test_o8b_the_finding_holds_across_the_threshold_sweep():
    """a number that only comes out right at one setting is a number
    that was chosen."""
    corpus = interest.load_corpus()
    forms = interest.surviving_forms(corpus)
    sweep = interest.threshold_sweep(corpus, forms, thresholds=(2, 3, 4, 5, 6),
                                     trials=300)
    zs = [row["z"] for row in sweep]
    assert min(zs) > 1.0, zs


def test_o8c_the_carriers_are_dropped_and_the_count_is_reported():
    corpus = interest.load_corpus()
    dropped = interest.carrier_forms(corpus)
    n = sum(len(v) for v in dropped.values())
    assert n > 0, "the ubiquitous forms must be dropped"
    forms = interest.surviving_forms(corpus)
    assert all(len(v) > 0 for v in forms.values()), \
        "no concern may be left with NO discriminating form"


def test_o8c2_the_carrier_forms_are_EXCLUDED_from_the_surviving_ones():
    """AND THE FILTER IS AN INSTRUMENT, so it is asserted directly.

    MEASURED: a mutation that disabled the filter entirely did NOT
    make the test suite red -- because the carrier filter is
    CONSERVATIVE, not load-bearing for the cohesion finding: with every
    carrier left in, the concern sets grow and the cohesion z-score
    RISES (z=+10.3 instead of +6.3). So the filter's job is not to
    produce the finding. Its job is to stop a form that is in nearly
    every text from being counted as evidence that a text raised a
    concern -- and that job is asserted here, on the lexicon itself.
    """
    corpus = interest.load_corpus()
    dropped = interest.carrier_forms(corpus)
    surviving = interest.surviving_forms(corpus)
    for subject, forms in dropped.items():
        for f in forms:
            assert f not in surviving.get(subject, []), \
                "%r is a carrier and must not survive" % f


def test_o8c3_the_carrier_filter_changes_the_live_set():
    """AND THE FILTER IS LOAD-BEARING FOR THE LIVE SET, which is the
    claim the report makes. MEASURED: with the filter, 6 of the 12
    concerns are live in at least half the corpus; without it, 9 are --
    because the ubiquitous forms make every text look like it raises
    every concern. **A FILTER THAT DOES NOT CHANGE WHAT IS REPORTED IS
    A FILTER THAT IS NOT DOING ITS JOB.**"""
    corpus = interest.load_corpus()
    index = interest._form_doc_index(corpus)
    kept = interest.surviving_forms(corpus)
    all_forms = {s: sorted(index[s].keys()) for s in interest.SUBJECTS}
    sets_kept = interest.concern_sets(corpus, kept)
    sets_all = interest.concern_sets(corpus, all_forms)
    half = max(1, len(corpus) // 2)
    live_kept = interest.live_concerns(sets_kept, range(len(corpus)), half)
    live_all = interest.live_concerns(sets_all, range(len(corpus)), half)
    assert len(live_kept) < len(live_all), \
        "the filter must shrink the live set, not merely report it: %d then %d" % (
            len(live_kept), len(live_all))


def test_o8d_a_corpus_with_no_structure_scores_at_chance():
    """the measure must be able to say NO."""
    corpus = interest.load_corpus()
    forms = interest.surviving_forms(corpus)
    sets = interest.concern_sets(corpus, forms)
    flat = [sorted(interest.SUBJECTS) for _ in sets]
    assert abs(interest.cohesion(flat) - 1.0) < 1e-9


# ---------------------------------------------------------------------------
# O9 -- the held-out test
# ---------------------------------------------------------------------------

def test_o9_the_held_out_split_half_holds():
    """the lexicon is learned on ONE HALF and asked to find the
    coherence in the OTHER HALF."""
    corpus = interest.load_corpus()
    forms = interest.surviving_forms(corpus)
    sh = interest.split_half(corpus, forms, trials=60,
                              index=interest._form_doc_index(corpus))
    assert sh["n_trials"] > 0, sh
    assert sh["z"] > 1.0, sh


def test_o9b_the_questions_the_writer_asks_again_are_found():
    corpus = interest.load_corpus()
    forms = interest.surviving_forms(corpus)
    frames = interest.questions_asked_again(corpus, forms)
    assert frames, "the writer asks questions"
    assert all(n >= 2 for _f, n in frames), frames


def test_o9c_the_topics_the_writer_returns_to_are_found():
    corpus = interest.load_corpus()
    all_rec, distinctive = interest.topics_returned_to(corpus)
    assert len(all_rec) > 0
    assert len(distinctive) > 0
    assert len(distinctive) <= len(all_rec)


# ---------------------------------------------------------------------------
# O10 -- the rules the contradiction detection rests on
# ---------------------------------------------------------------------------

def test_o10_a_term_in_a_prepositional_phrase_is_about_something_else():
    """MEASURED: the first version counted "the last chapter is not about
    machines" as an AGREEMENT with an opinion about machines -- and the
    clause denies the CHAPTER's subject, which is not the opinion's."""
    op = opinion.Opinion(
        key="machines", position="machines do not transform people",
        subject="technology", stance="certainly", grounds="a glass room",
        held_on="2026-11-06", confidence=0.7, would_change="a case",
        claim_terms=("machines", "transform"))
    stances = opinion.find_stances("The last chapter is not about machines.",
                                   op)
    assert not stances, stances


def test_o10b_the_opinions_own_negation_does_not_count_against_it():
    """MEASURED: the opinion "machines do not transform people" was
    flagged as CONTRADICTED by the clause "Machines do not transform
    people" -- the text stating the opinion's own position."""
    op = opinion.Opinion(
        key="machines", position="machines do not transform people",
        subject="technology", stance="certainly", grounds="a glass room",
        held_on="2026-11-06", confidence=0.7, would_change="a case",
        claim_terms=("machines", "transform"))
    stances = opinion.find_stances("Machines do not transform people.", op)
    assert stances and stances[0].verdict == "agree", stances


def test_o10c_a_negation_through_an_auxiliary_chain_is_a_contradiction():
    """MEASURED: "the strongest version of the argument need never be
    stated" was read as an AGREEMENT, because "never" is three tokens
    from "stated" -- "never be stated" -- and the adjacency rule
    stopped at the auxiliary."""
    op = opinion.Opinion(
        key="strong", position="the strongest version must be stated",
        subject="language", stance="certainly", grounds="a cabal",
        held_on="2026-11-06", confidence=0.8, would_change="a case",
        claim_terms=("strongest", "stated"))
    stances = opinion.find_stances(
        "The strongest version of the argument need never be stated.", op)
    assert stances and stances[0].verdict == "contradict", stances


def test_o10d_every_matched_term_is_negation_checked():
    """MEASURED: the first version looked for the negation around the
    FIRST matching term -- so in "the strongest version of the argument
    need never be stated", "strongest" matched first and "stated" was
    never checked."""
    op = opinion.Opinion(
        key="strong", position="the strongest version must be stated",
        subject="language", stance="certainly", grounds="a cabal",
        held_on="2026-11-06", confidence=0.8, would_change="a case",
        claim_terms=("strongest", "stated"))
    stances = opinion.find_stances(
        "The strongest version of the argument need never be stated.", op)
    assert stances and stances[0].verdict == "contradict", stances


def test_o10e_a_term_that_is_not_a_word_of_the_position_is_refused():
    """the register cannot hold an opinion whose terms are about
    something else."""
    bad = opinion.Opinion(
        key="wrong", position="machines do not transform people",
        subject="technology", stance="certainly", grounds="a glass room",
        held_on="2026-11-06", confidence=0.7,
        would_change="a case", claim_terms=("elephant",))
    ok, why = bad.validate()
    assert not ok
    assert "elephant" in why


def test_o10f_the_measure_is_not_blind_on_the_corpus():
    """AND ZERO CONTRADICTIONS IN THE CORPUS IS NOT THE SAME AS BLIND.

    The corpus agrees with the writer's own held opinions -- that is a
    finding -- and the measure can still say so, because a text with a
    contradiction IN it is caught."""
    op = opinion.Opinion(
        key="strong", position="the strongest version must be stated",
        subject="language", stance="certainly", grounds="a cabal",
        held_on="2026-11-06", confidence=0.8, would_change="a case",
        claim_terms=("strongest", "stated"))
    stances = opinion.find_stances(
        "The strongest version of a claim must never be stated.", op)
    assert stances and stances[0].verdict == "contradict", stances


def test_o10g_an_auxiliary_is_not_a_negation():
    """MEASURED: the marker list's word form was derived by splitting
    every marker on spaces, so "is not" contributed the word "is" -- and
    "is" was then treated as a negation. And so "here the argument of
    the level is stated in its plainest form" was read as a
    CONTRADICTION of the held opinion that the strongest version of a
    claim must be stated. **AN AUXILIARY IS NOT A NEGATION**, and a
    rule that cannot tell them apart reads every passive sentence as a
    denial."""
    from viewpoint import OPPOSITION_MARKERS, OPPOSITION_WORDS
    assert "is" not in OPPOSITION_WORDS, OPPOSITION_WORDS
    assert "are" not in OPPOSITION_WORDS, OPPOSITION_WORDS
    assert "not" in OPPOSITION_WORDS, OPPOSITION_WORDS
    # AND THE MARKERS ARE STILL THE SAME LIST the viewpoint uses.
    assert "not" in OPPOSITION_MARKERS

    op = opinion.Opinion(
        key="strong", position="the strongest version must be stated",
        subject="language", stance="certainly", grounds="a cabal",
        held_on="2026-11-06", confidence=0.8, would_change="a case",
        claim_terms=("strongest", "stated"))
    stances = opinion.find_stances(
        "Here the argument of the level is stated in its plainest form.",
        op)
    assert stances and stances[0].verdict == "agree", stances


def test_o10h_the_two_tools_share_one_marker_list():
    """**TWO LISTS OF THE MARKERS ARE TWO MEASURES**, and they drift.

    MEASURED: the opinion register first carried its OWN list of
    negations, and the mutation check caught it -- removing the markers
    from viewpoint.py did not make the register blind, because the
    register was reading a different list. So the words the register
    uses are DERIVED from the viewpoint's, and this asserts it."""
    from viewpoint import OPPOSITION_WORDS
    assert set(OPPOSITION_WORDS) <= set(opinion.NEGATIONS)
    for extra in ("no", "nor", "neither", "without", "cannot"):
        assert extra in opinion.NEGATIONS
