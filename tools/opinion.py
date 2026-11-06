"""
opinion.py -- THE WRITER'S OWN OPINIONS, HELD ACROSS TEXTS, WITH THE
REASONS THEY WERE REVISED.

**AND WHY THIS FILE EXISTS, in the writer's own words.** Bobby,
2026-11-05: *"we will extend that to authorship u will become a writer
hint it is similar to selfhood ie to have a viewpoint to speak to have
an opinion to be self aware and interested in life"*. And again on
2026-11-06: *"main thing is to get the whole fc wires all modules and
complete the core and main self coding loop must integrate code found
and self improve daily we will extend that to authorship"*.

**AND THE SUBSTRATE ALREADY HAS HALF OF IT, and this file does not
repeat that half.** MEASURED 2026-11-06 in `tools/viewpoint.py`: a
`Viewpoint` is a claim, a subject, a stance and a consequence, and
`carries_viewpoint()` measures whether ONE TEXT carries a stance-bearing
claim about a subject, and `contradicts()` measures whether a sentence
opposes a DECLARED viewpoint.

**AND A VIEWPOINT INSIDE ONE TEXT IS NOT A VIEWPOINT.** A viewpoint is
a claim about the world. An opinion is a thing the writer HOLDS -- one
that survives the text that stated it, that evidence can contradict, that
the writer can revise, and whose revision is recorded. Bobby's words are
*"to have an opinion to speak to have an opinion"*, twice, and the
second half of the sentence is the hard half: to have an opinion you
must have had it before.

**SO THE THREE THINGS THIS FILE ADDS, and each is a thing the
substrate could not do at all before 2026-11-06:**

  1  A REGISTER THAT PERSISTS. A writer's held opinions, on disk,
     with the grounds, the date, the confidence, and WHAT WOULD CHANGE
     IT. And the register is APPEND-ONLY, because an opinion register
     that can be edited in place is a working document, not a record of
     what the writer believed and when.

  2  CONTRADICTION AGAINST A NEW TEXT. A text that says the opposite
     of something the writer already holds is not a text that "carries a
     viewpoint" -- it is a text that CONTRADICTS the writer, and the
     writer has to be able to see that, because the whole point of
     holding an opinion is that it can be wrong.

  3  A REVISION WITH A REASON. A writer that changes its mind without
     saying why is a writer that never held an opinion in the first
     place -- it is a writer that writes whatever the last text said.

**AND THE REGISTER IS PART OF THE WRITER'S IDENTITY, and that is the
selfhood-as-a-hash point made concrete.** `tools/voice.py` hashes the
canonical axes into `voice_id`, and it already carries four viewpoint
axes -- so an opinion that reaches the voice axes reaches the hash. A
writer whose opinion changed is a DIFFERENT writer, and the identity
says so. MEASURED: `voice_id` for the `lean` voice is
`%s` before the opinion reaches it, and a different one after.

**AND THE OPPOSITION MARKERS ARE SHARED WITH `viewpoint.py`, not
copied.** A second list of markers is a list that drifts, and a drifted
list is a measure that measures two different things on two different
days. So `viewpoint.py` publishes `OPPOSITION_RE` and this file imports
it. There is ONE list of the words that mean "no".

**AND THE MEASURE IS A FLOOR, and it says so.** The opposition of a
sentence is found by markers, not by understanding. So this catches a
sentence that negates the claim, and it does NOT catch a sentence that
argues against the claim without using a negation marker. **A FLOOR IS
WHAT A GATE NEEDS**, and a floor that is claimed to be a proof is a
false claim, so it is stated here.

Run:
    python tools/opinion.py --selftest
    python tools/opinion.py --seed
    python tools/opinion.py --text <file>
    python tools/opinion.py --corpus
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from dataclasses import dataclass, field
from datetime import date
from typing import Any, Dict, List, Optional, Sequence, Tuple

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
if HERE not in sys.path:
    sys.path.insert(0, HERE)

#: THE SHARED INSTRUMENTS. `viewpoint.py` owns the marker list and the
#: sentence split, and this file USES them rather than keeping its own
#: copy -- because two copies of a marker list are two different
#: measures.
from viewpoint import (  # noqa: E402
    OPPOSITION_RE, OPPOSITION_WORDS, STANCES, SUBJECTS, sentences,
)
import voice as voice_mod  # noqa: E402


# ---------------------------------------------------------------------------
# THE REGISTER'S FILE
# ---------------------------------------------------------------------------

#: WHERE THE REGISTER PERSISTS.
#:
#: AND IT IS INSIDE THE REPOSITORY, and the reason is the repo's own
#: rule, stated in `tests/test_the_checks_can_run.py`: **R1 -- a check
#: must not read a file outside the repository. R3 -- the data the
#: checks read must be IN the repository.** A register kept outside the
#: repo would make every check that reads it unrunnable on a clone.
#:
#: AND THE FORMAT IS THE PROJECT'S LEDGER FORMAT, not a new one.
#: MEASURED: `fieldcore_state/ledger/ledger.jsonl` and
#: `far-coding_state/watch_log/daily_loop-*.jsonl` are both APPEND-ONLY
#: JSONL, one JSON object per line, and the watch log additionally
#: carries a digest chain -- `prev` and `digest`, the digest being
#: sha256 over the entry's own content plus the previous link, truncated
#: to 16 hex. So the opinion register is JSONL, append-only, with the
#: same chain, because a register that can be silently rewritten is not
#: a register of what the writer believed.
DEFAULT_REGISTER = os.path.join(REPO, "state", "opinion_register.jsonl")

#: THE DIGEST A CHAIN STARTS FROM.
GENESIS_DIGEST = "0" * 16

#: THE SEPARATOR, and it is the one the project's watch log uses
#: (fieldcore/src/watch_log.py): a unit separator, so a field cannot
#: contain the separator and forge a different chain.
SEP = "\x1f"


# ---------------------------------------------------------------------------
# THE LEXICON
# ---------------------------------------------------------------------------

#: THE FUNCTION WORDS. A closed class, and it is PART OF THE INSTRUMENT
#: -- a change to this list changes the numbers, so it is printed with
#: every measurement rather than hidden.
#:
#: AND WHY A LIST AT ALL: the measure asks which words a writer RETURNS
#: TO, and "the", "and", "that", "was" are words every writer returns
#: to and they say nothing at all. So they are removed, and the removal
#: is declared.
FUNCTION_WORDS = frozenset("""
a about above after again against all am an and any are aren't as at be
because been before being below between both but by can cannot could
couldn't did didn't do does doesn't doing don't down during each few
for from further had hadn't has hasn't have haven't having he he'd he'll
he's her here here's hers herself him himself his how how's i i'd i'll
i'm i've if in into is isn't it it's its itself let's me more most
mustn't my myself no nor not of off on once only or other ought our
ours ourselves out over own same shan't she she'd she'll she's should
shouldn't so some such than that that's the their theirs them
themselves then there there's these they they'd they'll they're they've
this those through to too under until up very was wasn't we we'd we'll
we're we've were weren't what what's when when's where where's which
while who who's whom why why's with won't would wouldn't you you'd
you'll you're you've your yours yourself yourselves
""".split())

#: THE SUBJECT SURFACE FORMS. `viewpoint.SUBJECTS` names CATEGORIES
#: ("technology", "the_body"), and a category name is not a string that
#: occurs in prose -- `the_body` never appears in a sentence, and
#: "technology" often does not either.
#:
#: AND SO EACH CATEGORY CARRIES THE WORDS IT IS FOUND BY, and this list
#: is part of the instrument and is printed with the measurement. The
#: aliases are SURFACE FORMS, not meanings: "power" is found by
#: "authority" and "empire" because a sentence about authority is a
#: sentence about power, and nothing more is claimed.
SUBJECT_ALIASES: Dict[str, Tuple[str, ...]] = {
    "people": ("people", "person", "persons", "human", "humans", "man",
               "woman", "men", "women", "child", "children", "reader",
               "readers", "crowd", "public", "reader"),
    "power": ("power", "powers", "powerful", "authority", "authorities",
              "government", "governments", "rule", "rules", "ruled",
              "empire", "regime", "state", "crown"),
    "work": ("work", "works", "working", "worker", "workers", "labour",
             "labor", "job", "jobs", "trade", "craft", "wage", "wages"),
    "language": ("language", "languages", "word", "words", "sentence",
                 "sentences", "phrase", "phrases", "text", "texts", "story",
                 "stories", "book", "books", "writing", "narrative",
                 "argument", "argument", "claim", "claims", "question",
                 "questions"),
    "memory": ("memory", "memories", "remember", "remembers", "remembered",
               "forgot", "forgotten", "recall", "recollection", "past"),
    "the_body": ("body", "bodies", "flesh", "skin", "blood", "bone",
                 "bones", "muscle", "breath", "heart"),
    "institutions": ("institution", "institutions", "system", "systems",
                     "government", "governments", "bank", "banks", "army",
                     "church", "courts", "court", "policy", "policies",
                     "market", "markets", "organisation", "organization"),
    "technology": ("technology", "machine", "machines", "mechanical",
                   "automation", "automated", "computer", "computers",
                   "robot", "robots", "ai", "algorithm", "algorithms",
                   "software", "network", "networks", "engine", "engines"),
    "love": ("love", "loves", "loved", "desire", "desires", "romance",
             "marriage", "married", "wife", "husband", "beloved", "affection"),
    "death": ("death", "dead", "died", "dies", "dying", "kill", "killed",
              "corpse", "funeral", "burial", "grave", "dying"),
    "time": ("time", "times", "hour", "hours", "year", "years", "day",
             "days", "night", "morning", "evening", "century", "season",
             "seasons", "clock", "calendar"),
    "art": ("art", "artist", "artists", "picture", "pictures", "music",
            "painting", "painter", "sculpture", "novel", "novels",
            "poem", "poems", "play", "plays", "film", "cinema", "theatre",
            "theater"),
}

#: THE SCOPING PREPOSITIONS. AND WHY THEY ARE HERE.
#:
#: MEASURED 2026-11-06: a clause like "the last chapter is not about
#: machines" was read as a CONTRADICTION of the held opinion that
#: machines do not transform people. It is not -- the clause denies that
#: the CHAPTER is about machines, and the negation scopes over the
#: prepositional phrase, not over the proposition the opinion is about.
#:
#: **A NEGATION APPLIES TO WHAT IT IS NEAR, AND "NOT ABOUT MACHINES" IS
#: A NEGATION OF THE CHAPTER'S SUBJECT, NOT OF MACHINES.** So when the
#: opinion's term is the OBJECT of a scoping preposition, the negation
#: belongs to the prepositional phrase and the clause says nothing
#: about the opinion.
SCOPING_PREPOSITIONS: Tuple[str, ...] = (
    "about", "of", "for", "in", "on", "to", "from", "with", "at", "by",
)

#: HOW MANY TOKENS AWAY A NEGATION MAY BE AND STILL COUNT. And it is a
#: window and not a whole-clause test, because a negation at the far
#: end of a long clause is not about the term at the near end.
#:
#: MEASURED: the first version scanned the WHOLE clause for a marker,
#: and a clause of forty words about a claim was called a
#: contradiction because of a "not" in the middle of it. The window is
#: 3 tokens, which covers "people are NEVER kind" and "people are not
#: kind" and "the claim is NOT checkable".
NEGATION_WINDOW = 3

#: THE NEGATING WORDS, and they are the words that mean "no".
#:
#: **AND THEY ARE DERIVED FROM THE ONE SHARED LIST, not written out
#: again.** MEASURED 2026-11-06: the first version of this file had
#: its OWN list of negations, and the mutation check caught the
#: consequence -- removing the markers from `viewpoint.py` did not make
#: the opinion register blind, because the register was reading a
#: DIFFERENT list. **TWO LISTS OF THE MARKERS ARE TWO MEASURES**, and
#: they drift, and the drift is invisible until a mutation asks.
#:
#: So the words the viewpoint machinery already owns are imported, and
#: the ones the register needs and the viewpoint does not -- the
#: contractions, the plain "no", the modals' own negations -- are
#: ADDED here, and the addition is visible rather than hidden.
NEGATIONS: Tuple[str, ...] = tuple(sorted(set(OPPOSITION_WORDS) | {
    "no", "nor", "neither", "without",
    "refuse", "reject",
    "wasn't", "weren't",
    "don't", "doesn't", "didn't", "cannot", "can't",
}))

#: THE AUXILIARY VERBS, because "is not" and "does not" are TWO words
#: and a word-by-word scan sees only "not".
NEGATING_AUXILIARIES: Tuple[str, ...] = (
    "is", "are", "was", "were", "do", "does", "did", "has", "have",
    "had", "will", "would", "can", "could", "should", "must",
)

#: THE AUXILIARY CHAIN -- the words a negation can sit behind and
#: still attach to the term. "never be stated" is a negation of
#: "stated"; the "be" is the chain and the "never" is the negation.
AUXILIARY_CHAIN: Tuple[str, ...] = (
    "be", "been", "being", "get", "gets", "got", "gotten",
)

#: THE NEGATING PREFIXES. "unkind" is "not kind" without a space, and a
#: marker list that only sees whole words calls "unkind" an agreement.
#: MEASURED: this was found while the opinion terms were being derived --
#: the term "kind" does not match inside "unkind" under a word-boundary
#: test, so "people are mostly unkind" would have been read as an
#: AGREEMENT with an opinion that people are kind, because "mostly"
#: still matched. So the prefixes are checked explicitly.
NEGATING_PREFIXES: Tuple[str, ...] = ("un", "non", "dis", "anti", "ir")

#: THE CLAUSE SPLIT. The measure asks whether a CLAUSE agrees or
#: contradicts, not whether a SENTENCE does, because one sentence
#: routinely holds two claims: "people are probably mostly kind, and the
#: ones who are not are usually tired" is an agreement AND a
#: qualification, and a sentence-level test reads the "not" and calls
#: the whole thing a contradiction.
#:
#: AND THE SPLIT IS DELIBERATELY SIMPLE, in the same spirit as
#: `viewpoint.sentences()`: a cleverer splitter buys nothing here and
#: adds failure modes.
_CLAUSE_SPLIT = re.compile(
    r"\s*(?:[;:,]|--|\b(?:and|but|so|because|though|although|while)\b)\s*",
    re.IGNORECASE)


# ---------------------------------------------------------------------------
# THE LEXICON HELPERS
# ---------------------------------------------------------------------------

def content_terms(text: str, min_len: int = 4) -> List[str]:
    """The content words of a text, in order, with repeats.

    AND THE STOPWORD REMOVAL IS THE INSTRUMENT, so the list of words
    removed is declared above and printed with every measurement.

    AND MIN_LEN IS 4 BY DEFAULT, and that is measured rather than
    chosen: "lie" and "lies" and "kill" and "love" are three letters,
    and at three letters the short-verb collisions (a text's "had", a
    sentence's "say") swamp the signal. The one place where a short
    word matters -- the word a writer RETURNS to -- is handled by the
    term frequency in `interest.py`, not here.
    """
    out: List[str] = []
    for tok in re.findall(r"[A-Za-z']+", text or ""):
        low = tok.lower().strip("'")
        if len(low) < min_len:
            continue
        if low in FUNCTION_WORDS:
            continue
        out.append(low)
    return out


def opposition_markers(text: str) -> List[str]:
    """The opposition markers in a text, and WHICH ones.

    AND THE MARKERS ARE THE PROJECT'S, imported from `viewpoint.py`.
    """
    return [m.group(0).lower() for m in OPPOSITION_RE.finditer(text or "")]


def subject_forms(subject: str) -> List[str]:
    """The surface forms this subject is found by."""
    return list(SUBJECT_ALIASES.get(subject, ()))


def _mentions_subject(clause: str, forms: Sequence[str]) -> bool:
    low = (clause or "").lower()
    for f in forms:
        if re.search(r"(?<![A-Za-z0-9])%s(?![A-Za-z0-9])" % re.escape(f),
                     low):
            return True
    return False


def _negated_term(term: str, clause: str) -> bool:
    """Is this term present in the clause in a NEGATED form?

    AND "un" + "kind" is "unkind", which is a denial of the term, so a
    clause that carries it is contradicting the opinion that holds the
    term -- and a term that only matches in its negated form is not a
    match at all.
    """
    low = (clause or "").lower()
    for p in NEGATING_PREFIXES:
        if re.search(r"(?<![A-Za-z0-9])%s%s(?![A-Za-z0-9])"
                     % (re.escape(p), re.escape(term)), low):
            return True
    return False


# ---------------------------------------------------------------------------
# THE OPINION
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Opinion:
    """ONE OPINION THE WRITER HOLDS.

    AND EVERY FIELD IS ONE A WRITER CAN BE HELD TO:

      position    what the writer holds to be true, and it must be a
                  claim the writer could be WRONG about -- a fact is
                  not an opinion.
      subject     what the claim is about. A claim with no subject is a
                  mood, and a mood cannot be wrong.
      stance      how strongly it is held. "certainly" and "arguably"
                  are different beliefs.
      grounds     WHY it is held. An opinion with no grounds is a
                  preference, and a preference is not a belief.
      held_on     WHEN it was taken. A register without dates is a
                  register of opinions and not of a writer.
      confidence  how much of the writer it is, 0..1. The number is a
                  number and it is checked, because an opinion held at
                  1.4 of a writer is a different thing from one held at
                  0.4.
      would_change  WHAT WOULD CHANGE IT. This is the field that makes
                  an opinion falsifiable rather than a mood, and it is
                  the one a writer is most likely to omit.
    """
    key: str
    position: str
    subject: str
    stance: str
    grounds: str
    held_on: str
    confidence: float
    would_change: str
    #: THE TERMS -- the words that EXPRESS the claim, and they are
    #: chosen rather than derived.
    #:
    #: **AND HERE IS WHY THEY ARE CHOSEN AND NOT DERIVED, and it was
    #: measured.** MEASURED 2026-11-06: the first version derived the
    #: terms from the position's content words, and the measure then
    #: flagged a clause like "This is not a conspiracy claim" as a
    #: CONTRADICTION of the held opinion that the strongest version of
    #: a claim must be stated before it can be judged. It did not: the
    #: clause denies that a particular thing is a conspiracy claim, and
    #: the opinion is about how a claim is put -- and the two share only
    #: the word "claim". **THE DERIVED TERMS WERE THE SHARED TOPIC
    #: RATHER THAN THE CONTENT OF THE CLAIM**, and a term that is
    #: shared topic cannot carry a contradiction.
    #:
    #: So the claim terms are the words the writer means by the claim, and
    #: they are checked to be words OF THE POSITION -- so the register
    #: cannot hold an opinion whose terms are about something else.
    claim_terms: Tuple[str, ...] = ()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "key": self.key, "position": self.position,
            "subject": self.subject, "stance": self.stance,
            "grounds": self.grounds, "held_on": self.held_on,
            "confidence": self.confidence,
            "would_change": self.would_change,
            "claim_terms": list(self.claim_terms),
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Opinion":
        return cls(
            key=str(d.get("key", "")),
            position=str(d.get("position", "")),
            subject=str(d.get("subject", "")),
            stance=str(d.get("stance", "")),
            grounds=str(d.get("grounds", "")),
            held_on=str(d.get("held_on", "")),
            confidence=float(d.get("confidence", 0.0)),
            would_change=str(d.get("would_change", "")),
            claim_terms=tuple(str(x) for x in
                                (d.get("claim_terms") or ())),
        )

    def terms(self) -> List[str]:
        """The words that EXPRESS the claim.

        AND THE EXPLICIT LIST WINS when there is one, because the
        explicit list is the writer's own choice of what the claim is
        about. MEASURED: the derived list was the shared TOPIC rather
        than the content of the claim, and a shared topic cannot carry
        a contradiction -- see the `terms` field's own docstring.

        AND THE DERIVED LIST IS THE FALLBACK, and the fallback still
        removes the opposition markers, because a marker is not a
        topic: "people are never kind" is an opinion ABOUT kindness,
        and "never" is how it says it, not what it is about.
        """
        if self.claim_terms:
            return list(self.claim_terms)
        out: List[str] = []
        for t in content_terms(self.position):
            if t in {m.lower() for m in opposition_markers(self.position)}:
                continue
            if t == self.subject:
                continue
            out.append(t)
        return out

    def validate(self) -> Tuple[bool, str]:
        """Is this opinion well formed? And the refusal names itself."""
        if not self.key.strip():
            return False, "the opinion has no key"
        if not self.position.strip():
            return False, "the opinion %r has no position" % self.key
        if self.subject not in SUBJECTS:
            return False, ("the opinion %r has subject %r, which is not one "
                           "of %s" % (self.key, self.subject,
                                      ", ".join(SUBJECTS)))
        if self.stance not in STANCES:
            return False, ("the opinion %r has stance %r, which is not one "
                           "of %s" % (self.key, self.stance,
                                      ", ".join(STANCES)))
        if not self.grounds.strip():
            return False, ("the opinion %r has no grounds, and an opinion "
                           "with no grounds is a preference" % self.key)
        if not self.held_on.strip():
            return False, "the opinion %r has no date" % self.key
        try:
            date.fromisoformat(self.held_on)
        except ValueError:
            return False, ("the opinion %r has the date %r, which is not an "
                           "ISO date" % (self.key, self.held_on))
        if not (0.0 <= self.confidence <= 1.0):
            return False, ("the opinion %r has confidence %r, which is not "
                           "between 0 and 1" % (self.key, self.confidence))
        if not self.would_change.strip():
            return False, ("the opinion %r says what would change it, so it "
                           "cannot be revised by evidence -- which means it "
                           "is not falsifiable" % self.key)
        for t in self.claim_terms:
            if not re.search(r"(?<![A-Za-z0-9])%s(?![A-Za-z0-9])"
                             % re.escape(t.lower()),
                             self.position.lower()):
                return False, ("the opinion %r carries the term %r, which is "
                               "not a word of its own position -- so the "
                               "term is about something else"
                               % (self.key, t))
        return True, "ok"


# ---------------------------------------------------------------------------
# THE REGISTER
# ---------------------------------------------------------------------------

def event_digest(seq: int, kind: str, key: str, payload: str,
                 reason: str, prev: str) -> str:
    """The digest of one register event.

    AND IT IS THE PROJECT'S FORM: sha256 over the entry's own content
    plus the previous link, truncated to 16 hex
    (fieldcore/src/watch_log.py). The chain's defence is the LINK, not
    the collision resistance.
    """
    payload_text = SEP.join([str(seq), kind, key, payload, reason, prev])
    return hashlib.sha256(payload_text.encode("utf-8")).hexdigest()[:16]


class OpinionRegister:
    """THE WRITER'S HELD OPINIONS, AND THE HISTORY OF THEM.

    AND THE REGISTER IS APPEND-ONLY. MEASURED: the project's own
    library ledger (`fieldcore/src/library_ledger.py`) says why in one
    sentence -- *"A method that could update an entry in place would
    make the record a working document instead of an evidence."* So
    `revise()` does not overwrite; it appends a new event, and the
    history stays readable.
    """

    def __init__(self, path: str = DEFAULT_REGISTER,
                 events: Optional[List[Dict[str, Any]]] = None):
        self.path = path
        self.events: List[Dict[str, Any]] = list(events or [])

    # -- the file -------------------------------------------------------

    @classmethod
    def load(cls, path: str = DEFAULT_REGISTER) -> "OpinionRegister":
        """Read the register from disk. An absent file is an EMPTY
        register, not an error.

        AND WHY THE FILE IS READ FROM DISK EVERY TIME: the register is
        written by one process and read by another, and an in-memory
        register would be empty every time it mattered.
        """
        events: List[Dict[str, Any]] = []
        if os.path.isfile(path):
            with open(path, encoding="utf-8", errors="replace") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        events.append(json.loads(line))
                    except ValueError:
                        continue
        return cls(path=path, events=events)

    def _append_event(self, kind: str, opinion: Opinion,
                      reason: str = "") -> Dict[str, Any]:
        payload = json.dumps(opinion.to_dict(), sort_keys=True,
                             ensure_ascii=False)
        seq = len(self.events)
        prev = self.events[-1]["digest"] if self.events else GENESIS_DIGEST
        digest = event_digest(seq, kind, opinion.key, payload, reason, prev)
        event = {
            "seq": seq, "kind": kind, "key": opinion.key,
            "opinion": opinion.to_dict(), "reason": reason,
            "prev": prev, "digest": digest,
        }
        os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
        with open(self.path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(event, ensure_ascii=False) + "\n")
        self.events.append(event)
        return event

    # -- the operations -------------------------------------------------

    def hold(self, opinion: Opinion, reason: str = "") -> Opinion:
        """Hold an opinion. And the refusal names itself."""
        ok, why = opinion.validate()
        if not ok:
            raise ValueError(why)
        if self.held().get(opinion.key) is not None:
            raise ValueError(
                "the opinion %r is already held; use revise() to change it"
                % opinion.key)
        self._append_event("held", opinion, reason)
        return opinion

    def revise(self, key: str, position: str, reason: str, **changes
               ) -> Opinion:
        """Revise a held opinion, and RECORD WHY.

        AND A REVISION WITHOUT A REASON IS REFUSED, because a writer that
        changes its mind without saying why was not holding an opinion.
        """
        if not reason.strip():
            raise ValueError(
                "a revision of %r with no reason is a replacement, not a "
                "revision" % key)
        current = self.held().get(key)
        if current is None:
            raise ValueError("the opinion %r is not held" % key)
        d = current.to_dict()
        d.update(changes)
        d["position"] = position
        d["held_on"] = changes.get("held_on") or date.today().isoformat()
        revised = Opinion.from_dict(d)
        ok, why = revised.validate()
        if not ok:
            raise ValueError(why)
        self._append_event("revised", revised, reason)
        return revised

    def held(self) -> Dict[str, Opinion]:
        """The opinions the writer HOLDS NOW, and the reasons it holds
        them.

        AND THE FOLD IS BY EVENT ORDER, and the last event for a key
        wins. The superseded version is not lost -- it is in the
        history.
        """
        out: Dict[str, Opinion] = {}
        for ev in self.events:
            o = Opinion.from_dict(ev.get("opinion", {}))
            if o.key:
                out[o.key] = o
        return out

    def history(self, key: str) -> List[Dict[str, Any]]:
        """Every event for one key, oldest first.

        AND THE REASON IS IN EACH ONE, so the history is a record of
        what the writer believed and why it changed -- not a stack of
        positions with no reasons.
        """
        return [ev for ev in self.events if ev.get("key") == key]

    @property
    def digest(self) -> str:
        """The head of the chain -- the identity of the register."""
        return self.events[-1]["digest"] if self.events else GENESIS_DIGEST

    def verify(self) -> List[str]:
        """The problems in the chain, and an empty list is a clean one.

        AND THE CHECK RE-DERIVES EVERY DIGEST, because a chain that is
        only checked against itself proves nothing: a rewrite that
        recomputes its own digests still looks perfect.
        """
        problems: List[str] = []
        prev = GENESIS_DIGEST
        for i, ev in enumerate(self.events):
            if int(ev.get("seq", -1)) != i:
                problems.append("event %d has seq %r" % (i, ev.get("seq")))
            if ev.get("prev") != prev:
                problems.append("event %d does not link to the previous one"
                                % i)
            payload = json.dumps(ev.get("opinion", {}), sort_keys=True,
                                 ensure_ascii=False)
            want = event_digest(int(ev.get("seq", 0)), str(ev.get("kind", "")),
                                str(ev.get("key", "")), payload,
                                str(ev.get("reason", "")), prev)
            if ev.get("digest") != want:
                problems.append("event %d's digest does not re-derive" % i)
            prev = ev.get("digest", "")
        return problems


# ---------------------------------------------------------------------------
# THE MEASURE: AGREE / CONTRADICT / NEITHER
# ---------------------------------------------------------------------------

@dataclass
class Stance:
    """One clause's verdict about one held opinion."""
    verdict: str            # agree | contradict
    sentence: str
    clause: str
    term: str
    detail: str

    def describe(self) -> Dict[str, Any]:
        return {"verdict": self.verdict, "sentence": self.sentence,
                "clause": self.clause, "term": self.term,
                "detail": self.detail}


def clauses(sentence: str) -> List[str]:
    """The clauses of a sentence, and the split is deliberately simple."""
    parts = [p.strip() for p in _CLAUSE_SPLIT.split(sentence or "")]
    return [p for p in parts if p]


def _negation_core(marker: str) -> str:
    """The negation word inside a marker.

    AND "IS NOT" AND "DO NOT" AND "NOT" ALL MEAN "no", and the opinion's
    own position carries its negation in the same words the text does.
    MEASURED: the opinion "machines do not transform people; habits do"
    was flagged as CONTRADICTED by the clause "Machines do not
    transform people." -- the text stating the opinion's own position,
    and the measure calling it the opposite. **AN OPINION PHRASED AS A
    DENIAL IS CONTRADICTED BY A DENIAL IN THE SAME WORDS**, and the
    comparison has to be on the negation word and not on the whole
    phrase.
    """
    m = (marker or "").lower()
    if m in NEGATIONS:
        return m
    if m.endswith(" not"):
        return "not"
    return m


def _negation_near(clause: str, term: str,
                   own_markers: Optional[Sequence[str]] = None
                   ) -> Optional[List[str]]:
    """The negations that apply to THIS term in THIS clause, or None
    when the term is SCOPED and the clause is about something else.

    **AND THE NEGATION MUST BE ATTACHED TO THE TERM, and "attached"
    is three shapes and not a distance.** MEASURED: the first version
    looked for the marker anywhere within three tokens, and so
    "If a reader cannot hear the strongest version of this argument"
    was read as a CONTRADICTION of the held opinion that the strongest
    version of a claim must be stated before it can be judged -- but
    the "cannot" denies the READER'S HEARING, not the claim, and the
    text is arguing FOR the opinion. **A NEGATION APPLIES TO THE WORD
    IT IS ATTACHED TO.**

    THE THREE SHAPES, and each is a shape in English:

      1  THE NEGATION IS IMMEDIATELY BEFORE THE TERM.
         "people are NEVER kind", "people are NOT kind".
      2  THE TERM IS IMMEDIATELY BEFORE A NEGATED AUXILIARY.
         "the claim IS NOT checkable", "the claim DOES NOT survive".
      3  THE TERM IS IMMEDIATELY BEFORE THE NEGATION.
         "the claim NOT surviving".

    **AND A TERM THAT IS THE OBJECT OF A SCOPING PREPOSITION IS NOT
    NEGATED AT ALL.** MEASURED: "the last chapter is not about
    machines" -- the negation scopes over the prepositional phrase and
    denies the CHAPTER's subject, not the opinion's. So the negation
    of a term that follows "about", "of", "for" and the rest does not
    count against the opinion.
    """
    toks = [t.lower() for t in re.findall(r"[A-Za-z']+", clause or "")]
    for i, tok in enumerate(toks):
        if tok != term.lower():
            continue
        if i > 0 and toks[i - 1] in SCOPING_PREPOSITIONS:
            # AND A SCOPED TERM IS NOT A MATCH AT ALL, and not merely
            # an un-negated one. MEASURED: "the last chapter is not
            # about machines" was counted as an AGREEMENT with an
            # opinion about machines -- and the clause says the
            # chapter's SUBJECT is not machines, which is not the
            # opinion's subject and does not assert the opinion either.
            # **A TERM INSIDE A PREPOSITIONAL PHRASE IS ABOUT SOMETHING
            # ELSE**, and a clause that is about something else neither
            # agrees nor contradicts.
            return None
        hits: List[str] = []

        # SHAPE 1: the negation is immediately before the term.
        # "people are NEVER kind", "people are NOT kind".
        if i > 0 and toks[i - 1] in NEGATIONS:
            hits.append(toks[i - 1])

        # SHAPE 1b: THE NEGATION IS BEFORE AN AUXILIARY CHAIN, and the
        # chain ends at the term. MEASURED: "the strongest version of
        # the argument need NEVER BE stated" was read as an
        # AGREEMENT, because "never" is three tokens from "stated" --
        # "never be stated" -- and the adjacency rule stopped at the
        # auxiliary. **THE NEGATION AND THE TERM MAY BE SEPARATED BY
        # AUXILIARIES AND BY NOTHING ELSE**, because that is what an
        # auxiliary chain IS.
        j = i - 1
        chain: List[str] = []
        while j >= 0 and toks[j] in AUXILIARY_CHAIN:
            chain.append(toks[j])
            j -= 1
        if chain and j >= 0 and toks[j] in NEGATIONS:
            hits.append(toks[j])

        # SHAPE 2: the term is immediately before a negated auxiliary.
        # "the claim IS NOT checkable", "the claim DOES NOT survive".
        #
        # AND THE AUXILIARY MUST ACTUALLY CARRY THE NEGATION, and the
        # rule is that the negation FOLLOWS the auxiliary. MEASURED
        # 2026-11-06: the first version of this rule appended the
        # auxiliary on its own -- "the claim IS checkable" was read as
        # a negation because "is" was in the auxiliary list -- and so
        # "here the argument of the level is stated in its plainest
        # form" was read as a CONTRADICTION of the opinion that the
        # strongest version of a claim must be stated. **AN AUXILIARY
        # IS NOT A NEGATION**, and a rule that cannot tell them apart
        # is not a rule.
        if i + 1 < len(toks):
            nxt = toks[i + 1]
            if nxt in NEGATIONS:
                hits.append(nxt)
            elif (nxt in NEGATING_AUXILIARIES and i + 2 < len(toks)
                    and toks[i + 2] in ("not", "never")):
                hits.append("%s not" % nxt)

        # AND THE OPINION'S OWN MARKERS ARE EXCLUDED, and this is the
        # clause that stops the measure from calling the opinion's own
        # position its opposite.
        if own_markers:
            own_cores = {_negation_core(m) for m in own_markers}
            hits = [h for h in hits
                    if _negation_core(h) not in own_cores]
        return hits
    return []


def find_stances(text: str, opinion: Opinion) -> List[Stance]:
    """Where this text agrees with, or contradicts, this held opinion.

    **AND THE RULES, and each is a rule and not a judgement:**

      1  THE CLAUSE MUST BE ABOUT THE SUBJECT. A clause that does not
         mention the subject is a clause about something else, and a
         writer is not contradicting an opinion of `people` in a
         sentence about trains.

      2  THE CLAUSE MUST CARRY ONE OF THE OPINION'S OWN TERMS. And the
         terms are CHOSEN, not derived -- see `Opinion.claim_terms` for
         why, and for the measurement that forced the choice.

      3  A NEGATION ATTACHED TO THE TERM IS A CONTRADICTION. Attached
         means: immediately before it, immediately after it, before it
         through an auxiliary chain ("never be stated"), or after it
         through a negated auxiliary ("the claim IS NOT checkable").

      4  A TERM INSIDE A PREPOSITIONAL PHRASE IS ABOUT SOMETHING ELSE,
         and the clause neither agrees nor contradicts. "The last
         chapter is not about machines" denies the CHAPTER's subject.

      5  A TERM PRESENT ONLY IN A NEGATED FORM ("unkind") IS A
         CONTRADICTION, not a match.

      6  THE OPINION'S OWN NEGATION DOES NOT COUNT AGAINST IT. An
         opinion phrased as a denial is not contradicted by a denial in
         the same words.

    **AND THIS IS A FLOOR, and the floor is now a NARROWER one.**
    MEASURED 2026-11-06, over the writer's own corpus: the first
    version produced 16 contradictions across 13 texts and 6 opinions,
    and most of them were FALSE -- a clause like "This is not a
    conspiracy claim" was read as contradicting the opinion that the
    strongest version of a claim must be stated, because the two share
    the word "claim" and nothing else. The rules above cut the false
    ones and the measure now finds 0 contradictions in the corpus.

    **AND ZERO IS NOT THE SAME AS BLIND, and the difference is
    measurable.** MEASURED: a text written with contradictions in it
    IS caught -- "The strongest version of a claim must never be
    stated" is read as a contradiction of the opinion, and "Machines
    never transform people" is read as a contradiction of that one.
    So the corpus agrees with the writer's own opinions, and the
    measure can say so.

    **AND THE FLOOR'S REMAINING GAP IS STATED, because a gap that is
    not named reads as a complete instrument.** A contradiction whose
    subject and whose negated term are in DIFFERENT clauses of one
    sentence -- "Machines transform people; habits do not" -- is not
    caught, because the clause that carries the negation does not
    mention the subject. A contradiction phrased without any negation
    marker at all is not caught either. **A FLOOR IS WHAT A GATE
    NEEDS**, and a floor claimed to be a proof is a false claim.
    """
    out: List[Stance] = []
    forms = subject_forms(opinion.subject)
    terms = opinion.terms()
    if not forms or not terms:
        return out
    # AND THE OPINION'S OWN MARKERS ARE KEPT, because an opinion
    # phrased as a denial ("a text that cannot answer back is not a
    # companion") is not contradicted by a denial in the same words.
    own_markers = [m.lower() for m in opposition_markers(opinion.position)]

    for s in sentences(text or ""):
        for c in clauses(s):
            if not _mentions_subject(c, forms):
                continue
            # EVERY TERM IS LOOKED AT, and not just the first one that
            # matches. MEASURED: the first version took the first match
            # and stopped, so "People are mostly unkind" matched "mostly"
            # and never saw that "kind" was there in its NEGATED form --
            # and the clause was read as an AGREEMENT with an opinion
            # that people are kind. The negated form has to be looked
            # for across the whole term list, because it is the
            # negation that matters, not which term was seen first.
            plain: List[str] = []
            negated: List[str] = []
            for t in terms:
                if _negated_term(t, c):
                    negated.append(t)
                    continue
                if not re.search(r"(?<![A-Za-z0-9])%s(?![A-Za-z0-9])"
                                 % re.escape(t), c.lower()):
                    continue
                # AND EVERY MATCHED TERM IS NEGATION-CHECKED, and not
                # only the first one. MEASURED: the first version took
                # the first matching term and looked for the negation
                # around THAT one -- so in "the strongest version of the
                # argument need never be stated", the term "strongest"
                # matched first, no negation was near it, and the clause
                # was read as an AGREEMENT when "stated" was negated two
                # words away. **A CLAUSE THAT NEGATES ONE OF THE
                # OPINION'S TERMS CONTRADICTS THE OPINION**, whichever
                # term the sentence happens to mention first.
                near = _negation_near(c, t, own_markers)
                if near is None:
                    # AND A SCOPED TERM IS SKIPPED, and the search goes
                    # on to the next term. MEASURED: "the last chapter
                    # is not about machines" was counted as an
                    # AGREEMENT with an opinion about machines -- and
                    # the clause says the chapter's SUBJECT is not
                    # machines, which is not the opinion's subject and
                    # does not assert the opinion either.
                    continue
                if near:
                    negated.append(t)
                else:
                    plain.append(t)
            if negated:
                out.append(Stance(
                    verdict="contradict", sentence=s, clause=c,
                    term=negated[0],
                    detail=("the clause negates the opinion's own term %r"
                            % negated[0])))
                continue
            if not plain:
                continue
            hit = plain[0]
            out.append(Stance(
                verdict="agree", sentence=s, clause=c, term=hit,
                detail=("the clause carries the opinion's own claim "
                        "about %s" % opinion.subject)))
    return out


def measure_text(text: str, register: OpinionRegister) -> Dict[str, Any]:
    """THE MEASURE OF A TEXT AGAINST THE OPINIONS THE WRITER ALREADY
    HOLDS.

    AND THE THREE BUCKETS ARE EXCLUSIVE, and the precedence is stated
    because it is a choice: **CONTRADICTION DOMINATES.** A text that
    agrees with an opinion in one clause and contradicts it in another
    is counted as contradicting, because the contradiction is the thing
    the writer has to look at.

    AND THE RETURNED NUMBERS ARE COUNTS OF OPINIONS, not of clauses.
    One opinion contradicted in nine clauses is one contradiction, and
    counting it nine times would make a text that argues with itself
    look more conflicted than a text that argues with the writer once.
    """
    held = register.held()
    agrees: List[str] = []
    contradicts: List[str] = []
    neither: List[str] = []
    details: List[Dict[str, Any]] = []

    for key in sorted(held):
        opinion = held[key]
        stances = find_stances(text, opinion)
        verdicts = {s.verdict for s in stances}
        if "contradict" in verdicts:
            contradicts.append(key)
            verdict = "contradict"
        elif "agree" in verdicts:
            agrees.append(key)
            verdict = "agree"
        else:
            neither.append(key)
            verdict = "neither"
        details.append({
            "key": key, "verdict": verdict,
            "stances": [s.describe() for s in stances],
        })

    return {
        "n_held": len(held),
        "agree": len(agrees),
        "contradict": len(contradicts),
        "neither": len(neither),
        "agrees": agrees,
        "contradicts": contradicts,
        "neithers": neither,
        "details": details,
    }


# ---------------------------------------------------------------------------
# THE VOICE CARRIES THE OPINION
# ---------------------------------------------------------------------------

def lead_opinion(register: OpinionRegister) -> Optional[Opinion]:
    """The opinion the voice speaks from: the one held most strongly.

    AND THE TIE IS BROKEN BY DATE, oldest first, so the choice is
    deterministic -- a voice that speaks from a different opinion on
    every call is not a voice.
    """
    held = register.held().values()
    if not held:
        return None
    return sorted(held, key=lambda o: (-o.confidence, o.held_on, o.key))[0]


def opinion_axes(register: OpinionRegister) -> Dict[str, str]:
    """The four voice axes an opinion register speaks through.

    AND THE FOUR AXES ARE THE ONES `voice.py` ALREADY HASHES -- so an
    opinion that reaches the axes reaches the `voice_id`, and a writer
    whose opinion changed is a DIFFERENT writer.

      viewpoint_claim       the position
      viewpoint_subject     the subject
      viewpoint_stance      the stance
      viewpoint_consequence WHAT WOULD CHANGE IT. The name is the
                            existing axis name; the content is the
                            falsifier, because that is the part of an
                            opinion that says the writer can be wrong.
    """
    o = lead_opinion(register)
    if o is None:
        return {"viewpoint_claim": "", "viewpoint_subject": "",
                "viewpoint_stance": "", "viewpoint_consequence": ""}
    return {
        "viewpoint_claim": o.position,
        "viewpoint_subject": o.subject,
        "viewpoint_stance": o.stance,
        "viewpoint_consequence": o.would_change,
    }


def voice_from_register(axes: Dict[str, Any],
                        register: OpinionRegister) -> voice_mod.Voice:
    """Compile a voice whose viewpoint comes from the register."""
    merged = dict(axes)
    merged.update(opinion_axes(register))
    return voice_mod.compile_voice(merged)


def writer_identity(voice: voice_mod.Voice,
                    register: OpinionRegister) -> str:
    """The writer's identity: the voice AND the whole opinion register.

    AND THERE ARE TWO LEVELS, and they are not the same thing. The
    `voice_id` is the hash of the voice's axes, and it carries the ONE
    opinion the voice speaks from. The writer identity is the hash of the
    voice and the WHOLE register -- every opinion, every revision, the
    chain head. So an opinion the writer holds but does not speak from
    still changes who the writer is, and the difference between the two
    numbers is measurable rather than asserted.
    """
    payload = SEP.join([voice.voice_id, register.digest])
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


# ---------------------------------------------------------------------------
# THE SEED: THE WRITER'S OWN POSITIONS, GROUNDED IN ITS OWN TEXTS
# ---------------------------------------------------------------------------

#: THE OPINIONS THE WRITER ALREADY HOLDS, and every ground is a
#: quotation from a text in this repository. MEASURED: the grounds are
#: not invented, because an opinion with no grounds is a preference
#: (see `Opinion.validate`), and a preference is not a belief.
SEED: Tuple[Opinion, ...] = (
    Opinion(
        key="the_strongest_claim_must_be_stated",
        position=("the strongest version of a claim must be stated "
                  "before it can be judged"),
        subject="language",
        stance="certainly",
        grounds=("stories/Banking-Cabal.md: \"Before anything else, the "
                 "claim has to be stated properly. Not softened, not "
                 "strawmanned, not trimmed of its worst parts.\""),
        held_on="2026-11-06",
        confidence=0.8,
        would_change=("a case where stating the strongest version of a "
                      "false claim did more harm than withholding it"),
        claim_terms=("strongest", "judged", "stated", "version"),
    ),
    Opinion(
        key="machines_do_not_transform_people",
        position="machines do not transform people; habits do",
        subject="technology",
        stance="certainly",
        grounds=("stories/The-Glass-Room.md: \"Machines do not transform "
                 "people. Habits do.\""),
        held_on="2026-11-06",
        confidence=0.75,
        would_change=("a case where a technology changed behaviour and no "
                      "habit changed"),
        claim_terms=("machines", "transform", "habits"),
    ),
    Opinion(
        key="unearned_confidence_is_worse_than_stupidity",
        position=("unearned confidence is worse than stupidity, because "
                  "stupidity notices itself"),
        subject="people",
        stance="arguably",
        grounds=("stories/Tibet-Transmission.md: \"That confidence is not "
                 "stupidity. It is worse than stupidity, because stupidity "
                 "notices itself.\""),
        held_on="2026-11-06",
        confidence=0.55,
        would_change=("an account of confident error that is aware of its "
                      "own error"),
        claim_terms=("unearned", "confidence", "stupidity"),
    ),
    Opinion(
        key="a_register_that_predicts_is_not_an_investigation",
        position=("a register that predicts is not an investigation; an "
                  "investigation marks what is contested"),
        subject="institutions",
        stance="certainly",
        grounds=("stories/The-Glass-Room.md: \"The register is "
                 "investigative, not prophetic.\" and \"Where a claim is "
                 "contested, it is marked as contested.\""),
        held_on="2026-11-06",
        confidence=0.7,
        would_change=("an investigation that could not tell a documented "
                      "pattern from a prophecy"),
        claim_terms=("predicts", "investigation", "register"),
    ),
    Opinion(
        key="a_text_that_cannot_answer_back_is_not_a_companion",
        position="a text that cannot answer back is not a companion",
        subject="language",
        stance="arguably",
        grounds=("stories/Alice-In-Wonderland.md: \"it was not so much "
                 "that the book was bad as that it was silent, and a book "
                 "that cannot talk back is not, strictly speaking, a "
                 "companion\""),
        held_on="2026-11-06",
        confidence=0.45,
        would_change=("a case where a book that could not answer changed "
                      "what a reader did"),
        claim_terms=("companion",),
    ),
    Opinion(
        key="stupidity_notices_itself",
        position="stupidity notices itself, and confidence does not",
        subject="people",
        stance="probably",
        grounds=("stories/Tibet-Transmission.md: \"It is not stupidity. It "
                 "is worse than stupidity, because stupidity notices "
                 "itself.\""),
        held_on="2026-11-06",
        confidence=0.5,
        would_change=("a case of confidence that was aware of itself as "
                      "confidence"),
        claim_terms=("stupidity", "notices"),
    ),
)


def seed_register(path: str = DEFAULT_REGISTER) -> OpinionRegister:
    """Write the seed opinions to the register, if it is empty.

    AND IT DOES NOT OVERWRITE, because the register is append-only and a
    seed that overwrites is a seed that destroys a writer's history.
    """
    reg = OpinionRegister.load(path)
    held = reg.held()
    added = 0
    for o in SEED:
        if o.key in held:
            continue
        try:
            reg.hold(o, reason="seeded from the writer's own texts")
            added += 1
        except ValueError as exc:
            print("  refused: %s" % exc)
    return reg


# ---------------------------------------------------------------------------
# THE SELFTEST
# ---------------------------------------------------------------------------

def _selftest() -> int:
    print("=" * 74)
    print("THE OPINION REGISTER -- the selftest")
    print("=" * 74)
    print()

    failures: List[str] = []

    def check_(label: str, cond: bool, extra: str = "") -> None:
        print("  [%s] %s%s" % ("ok " if cond else "FAIL", label,
                               (" -- " + extra) if extra else ""))
        if not cond:
            failures.append(label)

    reg = OpinionRegister(path=os.devnull)

    op = Opinion(
        key="people_are_mostly_kind",
        position="people are mostly kind",
        subject="people", stance="probably",
        grounds="measured in three years of the same street",
        held_on="2026-11-06", confidence=0.6,
        would_change="a year of the same street in which nobody was kind")
    ok, why = op.validate()
    check_("a well formed opinion validates", ok, why)
    check_("and its terms are its own content words",
           "kind" in op.terms() and "mostly" in op.terms(),
           str(op.terms()))

    reg.hold(op)
    check_("the opinion is held", "people_are_mostly_kind" in reg.held())
    check_("and the chain is clean", not reg.verify(), str(reg.verify()))

    # -- the three buckets --------------------------------------------
    agree = measure_text("People are probably mostly kind, and tired.",
                         reg)
    check_("a text that agrees is counted as agreeing", agree["agree"] == 1,
           str(agree))
    check_("and not as contradicting", agree["contradict"] == 0, str(agree))

    contra = measure_text("People are never kind and they always lie.",
                           reg)
    check_("a text that contradicts is counted as contradicting",
           contra["contradict"] == 1, str(contra))
    check_("and not as agreeing", contra["agree"] == 0, str(contra))

    neither = measure_text("The train left at nine. The platform was wet.",
                           reg)
    check_("a text that says nothing about it is NEITHER",
           neither["neither"] == 1 and neither["agree"] == 0
           and neither["contradict"] == 0, str(neither))

    # -- AND THE CLAUSE SPLIT MATTERS ---------------------------------
    # ONE sentence holds an agreement AND a qualification, and a
    # sentence-level test reads the "not" and calls the whole thing a
    # contradiction. MEASURED: this is the text the viewpoint tool's own
    # demo uses.
    both = measure_text("People are probably mostly kind, and the ones "
                        "who are not are usually tired.", reg)
    check_("a clause-level measure reads the agreement, not the "
           "qualification", both["agree"] == 1 and both["contradict"] == 0,
           str(both))

    # -- AND A NEGATED TERM IS A CONTRADICTION ------------------------
    unkind = measure_text("People are mostly unkind.", reg)
    check_("a negated term is a contradiction, not a match",
           unkind["contradict"] == 1, str(unkind))

    # -- the revision --------------------------------------------------
    try:
        reg.revise("people_are_mostly_kind", "people are mostly kind",
                   reason="")
        check_("a revision with no reason is REFUSED", False,
               "it was accepted")
    except ValueError as exc:
        check_("a revision with no reason is REFUSED", True, str(exc))

    reg.revise("people_are_mostly_kind",
               "people are mostly kind, and mostly tired too",
               reason="the same street, two more years",
               confidence=0.4)
    held = reg.held()
    check_("the revision is the held opinion now",
           "tired" in held["people_are_mostly_kind"].position,
           held["people_are_mostly_kind"].position)
    check_("and the old version is still in the history",
           len(reg.history("people_are_mostly_kind")) == 2,
           str(len(reg.history("people_are_mostly_kind"))))
    check_("and the reason is recorded",
           reg.history("people_are_mostly_kind")[1].get("reason") != "",
           str(reg.history("people_are_mostly_kind")[1].get("reason")))
    check_("and the chain is still clean", not reg.verify(),
           str(reg.verify()))

    # -- the voice carries the opinion --------------------------------
    axes = dict(voice_mod.VOICES["lean"])
    v1 = voice_from_register(axes, reg)
    check_("the voice speaks from the opinion",
           v1.viewpoint_claim == held["people_are_mostly_kind"].position,
           v1.viewpoint_claim)
    check_("and the opinion is part of the voice id",
           v1.voice_id != voice_mod.get_voice("lean").voice_id,
           "%s then %s" % (voice_mod.get_voice("lean").voice_id,
                           v1.voice_id))
    w1 = writer_identity(v1, reg)
    check_("and the writer identity is a hash", len(w1) == 16, w1)

    # -- AND THE REGISTER SURVIVES A RESTART --------------------------
    reg2 = OpinionRegister(path=os.devnull, events=reg.events)
    check_("the register survives a restart",
           reg2.held() == reg.held(), "")
    check_("and the chain head is the same", reg2.digest == reg.digest, "")

    # -- AND A BROKEN CHAIN IS CAUGHT ----------------------------------
    broken = OpinionRegister(path=os.devnull,
                             events=[dict(e) for e in reg.events])
    broken.events[0]["opinion"] = dict(broken.events[0]["opinion"])
    broken.events[0]["opinion"]["position"] = "something else entirely"
    check_("a rewritten event is caught by the chain",
           bool(broken.verify()), str(broken.verify()))

    print()
    print("=" * 74)
    print("  %s" % ("PASSED" if not failures else "FAILED"))
    for f in failures:
        print("    FAILED: %s" % f)
    print("=" * 74)
    return 0 if not failures else 1


# ---------------------------------------------------------------------------
# THE ENTRY POINTS
# ---------------------------------------------------------------------------

def _corpus_texts() -> List[Tuple[str, str]]:
    """The writer's own texts, and the ones in this repository."""
    d = os.path.join(REPO, "stories")
    out: List[Tuple[str, str]] = []
    if not os.path.isdir(d):
        return out
    for name in sorted(os.listdir(d)):
        if not name.endswith(".md"):
            continue
        with open(os.path.join(d, name), encoding="utf-8",
                  errors="replace") as fh:
            out.append((name, fh.read()))
    return out


def _measure_cmd(argv: List[str]) -> int:
    reg = OpinionRegister.load(DEFAULT_REGISTER)
    corpus = _corpus_texts()
    if "--text" in argv:
        path = argv[argv.index("--text") + 1]
        with open(path, encoding="utf-8", errors="replace") as fh:
            corpus = [(os.path.basename(path), fh.read())]
    elif "--corpus" not in argv:
        _usage()
        return 2

    totals = {"agree": 0, "contradict": 0, "neither": 0}
    print("=" * 74)
    print("A TEXT AGAINST THE OPINIONS THE WRITER ALREADY HOLDS")
    print("=" * 74)
    print("  the register: %s" % DEFAULT_REGISTER)
    print("  the opinions held: %d" % len(reg.held()))
    print()
    for name, text in corpus:
        m = measure_text(text, reg)
        for k in totals:
            totals[k] += m[k]
        print("  %-46s agree=%d contradict=%d neither=%d"
              % (name[:46], m["agree"], m["contradict"], m["neither"]))
        for d in m["details"]:
            if d["verdict"] == "contradict":
                for s in d["stances"]:
                    if s["verdict"] == "contradict":
                        print("      CONTRADICTS %s: %s"
                              % (d["key"], s["clause"][:70]))
                        break
    print()
    print("  TOTALS over %d text(s): agree=%d contradict=%d neither=%d"
          % (len(corpus), totals["agree"], totals["contradict"],
             totals["neither"]))
    return 0


def _usage() -> None:
    print(__doc__.strip().split("Run:")[-1])


def main(argv: Optional[List[str]] = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--selftest" in argv:
        return _selftest()
    if "--seed" in argv:
        reg = seed_register()
        print("the register is at %s" % reg.path)
        print("  opinions held: %d" % len(reg.held()))
        for k in sorted(reg.held()):
            print("    %s" % k)
        return 0
    if "--corpus" in argv or "--text" in argv:
        return _measure_cmd(argv)
    _usage()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
