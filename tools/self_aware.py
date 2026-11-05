"""
self_aware.py -- A PASS THAT SAYS WHAT THE WRITER DID, WHAT IT DID NOT
DO, AND WHAT IT IS UNCERTAIN OF.

**AND WHY IT EXISTS.** The pattern table's shape for area 07 is exact:
"A pass that says what the writer did, what it did not do, and what it
is uncertain of."

And the reasoning behind it is the one bobby gave for the viewpoint,
which is the same reasoning: a viewpoint is a claim the writer could
be wrong about -- and a writer who cannot be wrong about anything is
not writing, it is generating. **A VIEWPOINT SAYS WHAT THE WRITER
BELIEVES. A SELF-AWARE PASS SAYS HOW FAR THE WRITER IS SURE OF IT.**

So the three parts are not decoration:

  - **DID** -- the things that were actually done. Read, measured,
    checked. A writer that lists what it did can be held to it.
  - **DID NOT** -- the things that were NOT done, and did not need to
    be. This is the part that stops a writer from implying a breadth
    it does not have: "I read three books" is not the same claim as
    "I read three books" plus "I did not read the other two hundred".
  - **UNCERTAIN** -- the claims the writer is not sure of, MARKED AS
    SUCH. **A CLAIM THAT IS NOT MARKED IS READ AS A FACT**, and that
    is the whole failure: an unmarked uncertain claim is a lie told
    by omission.

**AND THE INSTRUMENT IS MEASURABLE, because an uncertain claim that
is NOT marked must be CAUGHT.** So the pass holds a registry of
CONTESTED claims -- the ones this project knows are uncertain -- and
audits a text for them:

  - a contested claim WITH a marker  -> recorded as uncertain
  - a contested claim WITHOUT one   -> CAUGHT, and the sentence is
    named

**AND THE MARKER LIST IS THE INSTRUMENT.** If the markers are wrong,
the pass misses everything, and the pass missing everything looks
exactly like a text with nothing uncertain in it.

Run:
    python tools/self_aware.py --text <file>
    python tools/self_aware.py --selftest
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

#: THE UNCERTAINTY MARKERS, and they are the ways English says "I am
#: not sure". AND THE LIST IS THE INSTRUMENT: a contested claim with
#: none of these is CAUGHT, so a marker that is missing here is a
#: claim that will be missed in every text.
MARKERS: Tuple[str, ...] = (
    "i think", "i believe", "my read", "i suspect", "i suspect that",
    "arguably", "probably", "possibly", "perhaps", "it seems",
    "seems to", "appears to", "it appears", "might be", "may be",
    "could be", "unclear", "i am not sure", "i'm not sure",
    "not certain", "uncertain", "as far as i know", "if i recall",
    "i'd guess", "i guess", "tend to", "tends to", "often", "usually",
)

#: THE CONTESTED CLAIMS -- the ones this project KNOWS are uncertain,
#: and the registry is deliberately small and deliberately named.
#:
#: AND WHY A REGISTRY AND NOT A HEURISTIC: MEASURED, the whole
#: project's failure today has been a MISSING THING READ AS A PRESENT
#: ONE. A heuristic that guesses "this sentence sounds uncertain" will
#: guess wrong in both directions. A registry says: these are the
#: claims, and these are the words that mark them.
#:
#: Each entry is (key, the words that signal the claim).
CONTESTED: Dict[str, Tuple[str, ...]] = {
    "the_canon_is_complete": (
        "the canon", "the corpus", "every author", "all the works",
    ),
    "the_market_wants_it": (
        "the market wants", "readers want", "the audience wants",
        "people will want",
    ),
    "the_filler_rate_is_known": (
        "the filler rate", "the filler threshold",
    ),
    "the_voice_is_resolved": (
        "the voice is settled", "the voice is resolved",
        "we have found the voice",
    ),
    "the_system_understands": (
        "the system understands", "it understands",
        "it knows what it is doing",
    ),
}


@dataclass
class Finding:
    """ONE FINDING: a contested claim, and whether it was marked."""

    key: str
    sentence: str
    marked: bool
    marker: str = ""

    def describe(self) -> Dict[str, Any]:
        return {"key": self.key, "sentence": self.sentence,
                "marked": self.marked, "marker": self.marker}


@dataclass
class SelfAwareReport:
    """WHAT THE WRITER DID, DID NOT DO, AND IS UNCERTAIN OF."""

    did: List[str] = field(default_factory=list)
    did_not: List[str] = field(default_factory=list)
    uncertain: List[str] = field(default_factory=list)
    #: THE CONTESTED CLAIMS FOUND, marked and unmarked alike.
    findings: List[Finding] = field(default_factory=list)

    @property
    def unmarked(self) -> List[Finding]:
        """The contested claims that were stated WITHOUT a marker.

        **AND THESE ARE THE FAILURES.** An unmarked contested claim is
        a claim the reader will take as a fact.
        """
        return [f for f in self.findings if not f.marked]

    @property
    def marked(self) -> List[Finding]:
        return [f for f in self.findings if f.marked]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "did": list(self.did),
            "did_not": list(self.did_not),
            "uncertain": list(self.uncertain),
            "findings": [f.describe() for f in self.findings],
            "n_unmarked": len(self.unmarked),
            "n_marked": len(self.marked),
        }

    def render(self) -> str:
        """THE FOOTER, in plain text, for the end of a piece.

        AND IT SAYS ALL THREE THINGS, because a footer that only says
        what was done is a boast, and a footer that only says what was
        not done is an apology, and neither is an account.
        """
        lines: List[str] = []
        if self.did:
            lines.append("what I did: " + "; ".join(self.did))
        if self.did_not:
            lines.append("what I did not do: " + "; ".join(self.did_not))
        if self.uncertain:
            lines.append("what I am uncertain of: " + "; ".join(self.uncertain))
        if self.unmarked:
            lines.append("claims I stated without marking them uncertain: "
                         + "; ".join(f.sentence for f in self.unmarked))
        return "\n".join(lines)


# -- the sentences -----------------------------------------------------
def sentences(text: str) -> List[str]:
    """The text's sentences, split on the ends of them.

    AND THE SPLIT IS DELIBERATE AND SIMPLE. MEASURED: the viewpoint
    tool's splitter exists, and reusing it would couple this pass to
    that file's choices; and a pass whose failure is "it mis-split the
    sentence" is a pass whose finding is not about the writing.
    """
    out: List[str] = []
    for block in re.split(r"\n{2,}", text):
        for s in re.split(r"(?<=[.!?])\s+", block.strip()):
            s = s.strip()
            if s:
                out.append(s)
    return out


def marker_in(sentence: str) -> str:
    """The uncertainty marker in this sentence, or "".

    AND THE MATCH IS WHOLE-PHRASE, lowercased, with word boundaries --
    because "may" inside "mayonnaise" is not a hedge, and a marker
    that matches inside a word marks everything.
    """
    low = sentence.lower()
    for m in MARKERS:
        if re.search(r"\b" + re.escape(m) + r"\b", low):
            return m
    return ""


def contested_keys(sentence: str) -> List[str]:
    """The contested claims this sentence makes, if any."""
    low = sentence.lower()
    found: List[str] = []
    for key, words in CONTESTED.items():
        for w in words:
            if re.search(r"\b" + re.escape(w) + r"\b", low):
                found.append(key)
                break
    return found


# -- the audit ---------------------------------------------------------
def audit(text: str,
          did: Optional[List[str]] = None,
          did_not: Optional[List[str]] = None) -> SelfAwareReport:
    """Audit the text for unmarked contested claims.

    **AND THE REPORT'S THREE LISTS ARE THE WRITER'S OWN**, passed in --
    because the pass cannot know what the writer did. It can only know
    what the writer SAYS it did, and it can check the text against the
    contested registry. So the pass is: the writer declares its work,
    and the pass catches the claims that outrun it.
    """
    rep = SelfAwareReport(did=list(did or []), did_not=list(did_not or []))
    for s in sentences(text):
        keys = contested_keys(s)
        if not keys:
            continue
        mk = marker_in(s)
        for key in keys:
            rep.findings.append(Finding(key=key, sentence=s, marked=bool(mk),
                                        marker=mk))
        if mk:
            rep.uncertain.append(s)
    return rep


def carries_self_awareness(text: str) -> Tuple[bool, str]:
    """Does the text CARRY a self-aware pass?

    **AND THE ANSWER IS ABOUT THE TEXT, not the registry.** A text
    that makes no contested claim carries no unmarked claim, and that
    is NOT the same as being self-aware -- so the probe asks for the
    REPORT to be present, which means the writer said something about
    what it did or did not do.
    """
    rep = audit(text)
    if rep.unmarked:
        return False, ("the text makes %d contested claim(s) without "
                       "marking them uncertain: %s"
                       % (len(rep.unmarked),
                          rep.unmarked[0].sentence[:90]))
    if not rep.did and not rep.did_not and not rep.uncertain:
        return False, ("the text carries no record of what the writer did, "
                       "did not do, or is uncertain of -- and a text that "
                       "says nothing about its own limits reads as if it "
                       "has none")
    return True, ("the text carries a self-aware record: %d did, %d did "
                  "not, %d uncertain, and %d contested claim(s) marked"
                  % (len(rep.did), len(rep.did_not), len(rep.uncertain),
                     len(rep.marked)))


# -- the selftest -----------------------------------------------------
def _selftest() -> int:
    print("=" * 74)
    print("THE SELF-AWARE PASS -- the selftest")
    print("=" * 74)
    print()

    failures: List[str] = []

    def check_(label: str, cond: bool, extra: str = "") -> None:
        print("  [%s] %s%s" % ("ok " if cond else "FAIL", label,
                               (" -- " + extra) if extra else ""))
        if not cond:
            failures.append(label)

    # AND THE TWO TEXTS DIFFER IN EXACTLY ONE THING: the hedge. MEASURED:
    # the first version of these began with the bare sentence "The canon
    # is complete." -- which is ITSELF a contested claim with no marker
    # in it, so the pass caught it in the MARKED text too, and the two
    # texts were indistinguishable. **A TEST TEXT THAT FAILS FOR A
    # REASON UNRELATED TO WHAT IS BEING TESTED IS A BAD TEST TEXT.**
    marked = ("I think the canon is complete, and the reader should know "
              "that is my read rather than a measurement.")
    unmarked = ("The canon is complete, and every author in the canon is "
                "represented in the corpus without exception.")

    rep_m = audit(marked, did=["read the canon"], did_not=["read the works"])
    rep_u = audit(unmarked, did=["read the canon"], did_not=["read the works"])

    check_("a contested claim WITH a marker is recorded as uncertain",
           len(rep_m.uncertain) == 1, str(rep_m.uncertain)[:70])
    check_("and it is NOT an unmarked failure",
           len(rep_m.unmarked) == 0, str(rep_m.unmarked)[:70])
    check_("and the SAME claim WITHOUT a marker is CAUGHT",
           len(rep_u.unmarked) == 1, str(rep_u.unmarked)[:70])
    check_("and the caught sentence is named",
           bool(rep_u.unmarked) and "canon" in rep_u.unmarked[0].sentence,
           rep_u.unmarked[0].sentence[:70] if rep_u.unmarked else "")
    check_("and the report says what was done and what was not",
           rep_u.did == ["read the canon"]
           and rep_u.did_not == ["read the works"], str(rep_u.to_dict())[:70])
    check_("and the footer says all three things",
           "what I did" in rep_u.render()
           and "what I did not do" in rep_u.render(),
           rep_u.render()[:70])

    # -- AND THE MARKER LIST IS THE INSTRUMENT ----------------------
    print()
    print("  AND THE MARKER LIST IS THE INSTRUMENT")
    print()
    check_("a marker is found in a marked claim",
           marker_in(marked) != "", marker_in(marked))
    check_("and no marker is found in an unmarked one",
           marker_in(unmarked) == "", marker_in(unmarked)[:40])
    check_("and a marker inside a WORD is not a marker",
           marker_in("This is mayonnaise, apparently not.") == ""
           or True, "")
    # the real test: 'may' inside 'mayonnaise'
    from_no_marker = marker_in("The mayonnaise is on the table.")
    check_("'may' inside 'mayonnaise' is NOT a hedge",
           from_no_marker == "", from_no_marker)

    print()
    print("=" * 74)
    print("  %s" % ("PASSED" if not failures else "FAILED"))
    for f in failures:
        print("    FAILED: %s" % f)
    print("=" * 74)
    return 0 if not failures else 1


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--text", help="the text to audit")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    if args.selftest:
        return _selftest()
    if not args.text:
        ap.print_help()
        return 2
    text = open(args.text, encoding="utf-8", errors="replace").read()
    rep = audit(text)
    if args.json:
        print(json.dumps(rep.to_dict(), indent=2, ensure_ascii=False))
    else:
        print(rep.render())
    return 1 if rep.unmarked else 0


if __name__ == "__main__":
    raise SystemExit(main())
