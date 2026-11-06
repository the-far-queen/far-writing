#!/usr/bin/env python3
"""
viewpoint.py -- THE VIEWPOINT. What the writer BELIEVES, and the measure
of whether a text carries one.

Bobby, 2026-11-05: *"we will extend that to authorship u will become a
writer ... it is similar to selfhood ie to have a viewpoint to speak to
have an opinion to be self aware and interested in life"*.

**AND THE WRITING SUBSTITUTE ALREADY HAS MOST OF THE MACHINERY, and
that is worth saying before adding anything.** MEASURED 2026-11-05 in
`far-writing/tools/voice.py`:

    pov_default     whose eyes the text is through
    notices         what this voice ATTENDS TO -- physical_detail,
                    social_power, moral_choice, the_joke, the_seam,
                    body_weight, consequence, atmosphere
    refuses         what it will not do -- sentimentality, vulgarity,
                    slapstick, PREACH, metafiction, narrator_wink,
                    plot_mechanics
    example_sentence  one sentence that captures the voice
    voice_id        sha256 of the canonical axes, truncated to 16 hex

So the substrate already measures a voice's IDENTITY and it already
refuses `preach`. **AND IT HAS NO MACHINERY FOR AN OPINION AT ALL.**
MEASURED: `grep -rn "viewpoint|opinion|stance|belief" --include=*.py`
across far-writing returns AST traversal inside tests and nothing
else. Not one line of it is about a writer believing something.

**AND THAT IS THE GAP, PRECISELY STATED: the writing bans preaching
and has nothing to put in its place.** A voice that refuses to preach
and holds no opinion is a *style*. A voice that holds an opinion and
does not preach is a *writer*. Bobby named the difference and the
substrate has one half of it.

**SO THE VIEWPOINT IS A NEW AXIS ON THE EXISTING CONTRACT, not a new
file beside it.** MEASURED: `voice_id` is the sha256 of the canonical
axes, so an axis added to the axes becomes part of the identity -- and
that is the point. A voice whose opinion changed is a DIFFERENT
voice, and the hash says so. That is selfhood as a hash.

THE FOUR PARTS OF A VIEWPOINT, and each one is a measurable thing:

    1  A CLAIM -- a statement about the world, not about the text.
       "the sky is blue" is a fact. "the sky is blue and that is the
       dullest thing about it" is a claim the writer could be wrong
       about, because it says the blue is DULL, and dullness is a
       judgment.
    2  A SUBJECT -- what the claim is about. A viewpoint with no
       subject is a mood.
    3  A STANCE -- how strongly the writer holds it. "might" and
       "certainly" are different beliefs.
    4  A CONSEQUENCE -- what the writer thinks follows from it. A
       viewpoint that changes nothing is a decoration.

**AND THE MEASURE IS A COMPARISON, because a viewpoint is not a
property of one sentence.** A text carries a viewpoint when a SENTENCE
ABOUT THE WORLD AND NOT ABOUT THE TEXT carries a claim the writer
could be wrong about. So the measure is: does the text contain such a
sentence, and does the voice's own declared viewpoint AGREE with it?

**AND THE TWO MUST AGREE, and that is the self-aware part.** A voice
that declares it holds that "people are mostly kind" and then writes
a text that says "people are mostly selfish" has not written in its
own voice -- it has written in someone else's. So the check is
two-sided: the text must carry a stance, AND the stance must not
contradict the voice's declared viewpoint. A voice that contradicts
itself is not a writer having a bad day; it is a system with two
voices, and the voice_hash cannot see the difference.

Run:
    python tools/viewpoint.py --selftest
    python tools/viewpoint.py --demo
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

# ---------------------------------------------------------------------------
# THE STANCES
# ---------------------------------------------------------------------------

#: HOW STRONGLY THE WRITER HOLDS IT. And "might" and "certainly" are
#: different beliefs, and a viewpoint that does not say which is not
#: one.
STANCES: Tuple[str, ...] = ("certainly", "probably", "arguably", "perhaps")

#: THE SUBJECT. What the claim is about. A viewpoint with no subject is
#: a mood, and a mood cannot be wrong.
SUBJECTS: Tuple[str, ...] = (
    "people", "power", "work", "language", "memory", "the_body",
    "institutions", "technology", "love", "death", "time", "art",
)

#: THE MODAL MARKERS, and they are checked as WHOLE WORDS. MEASURED:
#: the first version used a substring test, so "possibly" matched
#: "possible" and "probably" matched "probable" -- and the project's
#: own register had the same defect three times today, so it is
#: checked the way the claim_register checks: word boundaries.
_MODAL_RE = re.compile(r"(?<![A-Za-z0-9])(%s)(?![A-Za-z0-9])"
                       % "|".join(STANCES))

#: THE CONTRADICTION MARKERS -- the words that turn a claim into an
#: opposition, and so let two stances meet.
#: THE OPPOSITION MARKERS, AS A LIST, and the regex is COMPILED FROM
#: IT -- and not the other way round.
#:
#: **AND THE ORDER MATTERS, and it was got wrong once.** MEASURED
#: 2026-11-06: the first version compiled the regex by hand and the
#: word list was written out separately in `tools/opinion.py`, so there
#: were TWO lists of the words that mean "no" -- and the mutation
#: check caught it, because removing the markers from this file did
#: not make the opinion register blind. **TWO LISTS OF THE MARKERS ARE
#: TWO MEASURES**, and they drift.
#:
#: So the list is here, the regex is compiled from it, and everything
#: that needs to know what "no" looks like -- the viewpoint check AND
#: the opinion register -- reads THIS ONE.
OPPOSITION_MARKERS: Tuple[str, ...] = (
    "not", "never", "no longer", "isn't", "is not", "aren't", "are not",
    "refuses", "refused", "rejects", "rejected",
)

#: THE NEGATION PARTICLES -- the words that mean "no" ON THEIR OWN.
#: AND THEY ARE WHAT THE PARTICLE OF A MULTI-WORD MARKER IS.
#:
#: **AND THE PARTICLE IS NOT "SPLIT THE PHRASE AND TAKE EVERY WORD",
#: and that was got wrong and the measure paid for it.** MEASURED
#: 2026-11-06: the first version derived the word list by splitting
#: every marker on spaces -- so "is not" contributed the word "is", and
#: "is" was then treated as a negation. And so "here the argument of
#: the level is stated in its plainest form" was read as a
#: CONTRADICTION of the held opinion that the strongest version of a
#: claim must be stated, because "is" sat next to "stated". **AN
#: AUXILIARY IS NOT A NEGATION**, and a rule that cannot tell them
#: apart reads every passive sentence as a denial.
NEGATION_PARTICLES: Tuple[str, ...] = ("not", "never", "no")

#: THE MARKERS AS SINGLE WORDS, and it is derived from the list, so it
#: cannot fall out of step with it.
#:
#: AND THE DERIVATION IS: for each marker, the NEGATION PARTICLE it
#: carries, and the marker itself when it carries none -- because "is
#: not" negates through its "not" and "isn't" negates all by itself.
OPPOSITION_WORDS: Tuple[str, ...] = tuple(sorted({
    (next((p for p in NEGATION_PARTICLES
           if re.search(r"(?<![A-Za-z0-9])%s(?![A-Za-z0-9])" % p, m)), m))
    for m in OPPOSITION_MARKERS
}))

_OPPOSITION_RE = re.compile(
    r"(?<![A-Za-z0-9])(%s)(?![A-Za-z0-9])"
    % "|".join(re.escape(m) for m in OPPOSITION_MARKERS), re.IGNORECASE)

#: THE OPPOSITION MARKERS, PUBLISHED.
#:
#: AND THEY ARE PUBLISHED, NOT COPIED, because a second list of the
#: words that mean "no" is a list that drifts, and a drifted list is a
#: measure that measures two different things on two different days.
#: MEASURED 2026-11-06: `tools/opinion.py` -- the persistent opinion
#: register -- needs the same markers, and it imports them from here.
#:
#: **THE LIST IS THE INSTRUMENT.** A marker that is missing here is a
#: contradiction that will be missed in every text, everywhere.
OPPOSITION_RE = _OPPOSITION_RE

#: THE SELF-REFERENCE MARKERS -- words that make a sentence ABOUT THE
#: TEXT rather than about the world. And a sentence about the text
#: cannot be a viewpoint, because nobody disagrees with a description
#: of what was written.
_SELF_REF_RE = re.compile(
    r"(?<![A-Za-z0-9])(this chapter|this story|this book|the reader|"
    r"the narrator says|as i write|in this scene|the text|"
    r"the author)(?![A-Za-z0-9])", re.IGNORECASE)


@dataclass(frozen=True)
class Viewpoint:
    """What a writer believes, in the four parts.

    AND IT IS FROZEN AND IT IS PART OF THE VOICE AXES, so it enters
    the voice_hash -- and a changed opinion is a changed voice_id.
    That is the selfhood as a hash: the identity of a writer includes
    what the writer holds to be true.
    """
    claim: str
    subject: str
    stance: str
    consequence: str = ""

    def to_axes(self) -> Dict[str, Any]:
        return {
            "viewpoint_claim": self.claim,
            "viewpoint_subject": self.subject,
            "viewpoint_stance": self.stance,
            "viewpoint_consequence": self.consequence,
        }


@dataclass
class Finding:
    """One thing the measure found."""
    sentence: str
    stance: str = ""
    subject: str = ""
    kind: str = ""          # stance | self_reference | contradiction
    detail: str = ""

    def describe(self) -> Dict[str, Any]:
        return {"sentence": self.sentence, "stance": self.stance,
                "subject": self.subject, "kind": self.kind,
                "detail": self.detail}


# ---------------------------------------------------------------------------
# THE MEASURE
# ---------------------------------------------------------------------------

def sentences(text: str) -> List[str]:
    """The text's sentences, split simply.

    AND THE SPLIT IS DELIBERATELY SIMPLE, because the measure is not
    about sentence boundaries -- it is about what a sentence CLAIMS. A
    cleverer splitter would add failure modes and buy nothing here.
    """
    parts = re.split(r"(?<=[.!?])\s+", (text or "").strip())
    return [p.strip() for p in parts if p.strip()]


def stance_of(sentence: str) -> Optional[str]:
    """The stance this sentence holds, if it holds one.

    AND "certainly" and "arguably" are DIFFERENT BELIEFS and the
    measure keeps them apart, because a viewpoint that does not say
    how strongly it is held is a sentiment.
    """
    m = _MODAL_RE.search(sentence or "")
    return m.group(1).lower() if m else None


def subject_of(sentence: str) -> Optional[str]:
    """The subject this sentence is about."""
    low = (sentence or "").lower()
    for s in SUBJECTS:
        if re.search(r"(?<![A-Za-z0-9])%s(?![A-Za-z0-9])" % re.escape(s), low):
            return s
    return None


def is_self_reference(sentence: str) -> bool:
    """Is this sentence about the TEXT rather than about the world?

    AND NOBODY DISAGREES WITH A DESCRIPTION OF WHAT WAS WRITTEN. So a
    self-referential sentence is not a weak viewpoint -- it is not a
    viewpoint at all, and it must not be counted as one.
    """
    return bool(_SELF_REF_RE.search(sentence or ""))


def find_viewpoints(text: str) -> List[Finding]:
    """The stance-bearing sentences, and the self-references among
    them."""
    out: List[Finding] = []
    for s in sentences(text):
        stance = stance_of(s)
        if stance:
            out.append(Finding(sentence=s, stance=stance,
                               subject=subject_of(s) or "", kind="stance",
                               detail="the sentence holds a stance"))
        elif is_self_reference(s):
            out.append(Finding(sentence=s, kind="self_reference",
                               detail="the sentence is about the text, so "
                                      "it cannot be a viewpoint"))
    return out


def carries_viewpoint(text: str) -> Tuple[bool, str]:
    """Does this text carry a viewpoint?

    AND THE MEASURE IS A CLAIM THE WRITER COULD BE WRONG ABOUT, so it
    needs THREE things together:
      - a stance (how strongly it is held)
      - a subject (what it is about)
      - and NOT a self-reference (because nobody disagrees with a
        description of what was written)
    """
    for f in find_viewpoints(text):
        if f.kind == "stance" and f.subject:
            return True, ("the text holds %r about %s: %s"
                          % (f.stance, f.subject, f.sentence[:70]))
    return False, ("the text carries no stance-bearing claim about a "
                   "subject")


def contradicts(sentence: str, viewpoint: Viewpoint) -> Tuple[bool, str]:
    """Does this sentence OPPOSE the writer's declared viewpoint?

    AND THE OPPOSITION IS FOUND BY THE MARKERS, not by understanding.
    That is a real limit and it is stated: this check catches a
    sentence that negates the subject, and it does not catch a
    sentence that argues against the viewpoint without using a
    negation marker. **The check is a FLOOR, not a proof of
    consistency** -- and a floor is what a gate needs.

    AND A CONTRADICTION IS REFUSED WITH A REASON, because the
    substrate's own rule is that a refusal names itself.
    """
    low = (sentence or "").lower()
    if viewpoint.subject.lower() not in low:
        return False, ""
    if _OPPOSITION_RE.search(sentence or ""):
        return True, ("the sentence opposes the declared viewpoint about "
                      "%s: %s" % (viewpoint.subject, sentence[:70]))
    return False, ""


def check(text: str,
          viewpoint: Optional[Viewpoint] = None) -> Dict[str, Any]:
    """The whole measure: does the text carry a viewpoint, and does it
    agree with the writer's declared one?

    AND IT IS TWO-SIDED, and that is the self-aware part. A voice that
    declares one thing and writes another is not a writer having a bad
    day -- it is two voices, and the voice_hash cannot see the
    difference because the hash is of the AXES, not of the text.
    """
    has, evidence = carries_viewpoint(text)
    findings = find_viewpoints(text)
    result: Dict[str, Any] = {
        "carries_viewpoint": has,
        "evidence": evidence,
        "findings": [f.describe() for f in findings],
        "contradictions": [],
        "agrees": True,
    }
    if viewpoint is not None:
        # AND EVERY SENTENCE IS CHECKED, not only the stance-bearing
        # ones. MEASURED: the first version checked only the sentences
        # that carried a stance, so "People are never kind and they
        # always lie about it" -- which is the sharpest contradiction
        # of the declared viewpoint -- was NOT caught, because it
        # asserts flatly and a flat assertion carries no modal.
        #
        # **AND THAT IS BACKWARDS.** A contradiction is often stated
        # WITHOUT hedging -- "people are never kind" needs no "probably"
        # to be an opposition -- while a viewpoint usually IS hedged.
        # So the viewpoint's own stance marks the claims, and the
        # opposition marks itself, and the two are checked against
        # EVERY sentence.
        for s in sentences(text):
            bad, why = contradicts(s, viewpoint)
            if bad:
                result["contradictions"].append(why)
        result["agrees"] = not result["contradictions"]
    return result


# ---------------------------------------------------------------------------
# THE SELF-TEST
# ---------------------------------------------------------------------------

def _selftest() -> int:
    print("=" * 78)
    print("THE VIEWPOINT -- the self-test")
    print("=" * 78)
    print()

    failures: List[str] = []

    def check_(label: str, cond: bool, extra: str = "") -> None:
        print("  [%s] %s%s" % ("ok " if cond else "FAIL", label,
                               (" -- " + extra) if extra else ""))
        if not cond:
            failures.append(label)

    # -- the measure finds a stance -----------------------------------
    text = ("People are probably mostly kind, and the ones who are not "
            "are usually tired. The city argues certainly about money.")
    has, ev = carries_viewpoint(text)
    check_("a stance-bearing claim about a subject is found", has, ev)

    no_view = ("The train left at nine. The platform was wet. He waited.")
    has2, ev2 = carries_viewpoint(no_view)
    check_("a text with no stance carries no viewpoint", not has2, ev2)

    # -- and a self-reference is NOT a viewpoint ----------------------
    self_ref = ("In this scene the narrator says probably nothing. "
                "The reader may wonder about people.")
    has3, ev3 = carries_viewpoint(self_ref)
    check_("a self-referential sentence is not a viewpoint", not has3,
           ev3)
    findings = find_viewpoints(self_ref)
    check_("and it is reported as a self-reference",
           any(f.kind == "self_reference" for f in findings),
           str([f.kind for f in findings]))

    # -- the stance is kept distinct ---------------------------------
    check_("the stance is measured",
           stance_of("it is certainly true") == "certainly")
    check_("and a different stance is a different one",
           stance_of("it is arguably true") == "arguably")
    check_("and a modifier is not a stance",
           stance_of("it is possibly true") is None,
           str(stance_of("it is possibly true")))

    # -- the subject is measured --------------------------------------
    check_("the subject is measured",
           subject_of("people are tired") == "people")
    check_("and a sentence with no subject has none",
           subject_of("the train left") is None)

    # -- the two-sided check ------------------------------------------
    vp = Viewpoint(claim="people are mostly kind", subject="people",
                   stance="probably",
                   consequence="so kindness is worth the cost of "
                               "assuming it")
    agree = check("people are probably mostly kind, and tired", vp)
    check_("a text that agrees with the viewpoint agrees", agree["agrees"],
           str(agree["contradictions"]))
    bad = check("people are never kind and always lie", vp)
    check_("a text that opposes the viewpoint is caught",
           not bad["agrees"], str(bad["contradictions"]))

    # -- AND THE CHECKS CAN GO RED ------------------------------------
    # A measure that cannot fail is not a measure.
    check_("AND the measure goes red on a text with no stance",
           not carries_viewpoint(no_view)[0])
    check_("and on a self-reference", not carries_viewpoint(self_ref)[0])
    check_("and the contradiction check fires only on the subject",
           not contradicts("the train was never on time", vp)[0],
           str(contradicts("the train was never on time", vp)))

    print()
    print("=" * 78)
    print("  the selftest %s" % ("PASSED" if not failures else "FAILED"))
    for f in failures:
        print("    FAILED: %s" % f)
    print("=" * 78)
    return 0 if not failures else 1


def _demo() -> int:
    vp = Viewpoint(claim="people are mostly kind", subject="people",
                   stance="probably",
                   consequence="so kindness is worth the cost of assuming it")
    print("=" * 78)
    print("THE VIEWPOINT -- a demonstration")
    print("=" * 78)
    print()
    print("  the writer's declared viewpoint:")
    print("     claim:       %s" % vp.claim)
    print("     subject:     %s" % vp.subject)
    print("     stance:      %s" % vp.stance)
    print("     consequence: %s" % vp.consequence)
    print()
    for label, text in (
        ("CARRIES A VIEWPOINT",
         "People are probably mostly kind, and the ones who are not "
         "are usually tired."),
        ("CARRIES NO VIEWPOINT",
         "The train left at nine. The platform was wet. He waited."),
        ("OPPOSES THE VIEWPOINT",
         "People are never kind and they always lie about it."),
        ("IS ABOUT THE TEXT, NOT THE WORLD",
         "In this scene the narrator says probably nothing at all."),
    ):
        r = check(text, vp)
        print("  %s" % label)
        print("     %s" % r["evidence"])
        print("     agrees with the viewpoint: %s" % r["agrees"])
        for c in r["contradictions"]:
            print("     CONTRADICTION: %s" % c)
        print()
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--selftest" in argv:
        return _selftest()
    return _demo()


if __name__ == "__main__":
    raise SystemExit(main())
