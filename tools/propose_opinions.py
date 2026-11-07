#!/usr/bin/env python3
"""
propose_opinions.py -- name the claims the writer now holds that the
register does not.

Bobby, 2026-11-06.

**AND WHY A COMMAND, AND NOT A LIST.** The register holds 6 opinions,
and every one of them was SEEDED -- the reason on each event reads
"seeded from the writer's own texts". So the register is a LIST OF
OPINIONS WRITTEN BY HAND, and a list of opinions written by hand is a
wish written as a fact. The register's own docstring was rewritten for
exactly this defect on 2026-11-05.

**AND IT PRODUCES CANDIDATES, NOT ADDITIONS.** A loop that writes its
own opinions grades its own homework -- the same rule the act step
follows, and for the same reason: the thing that decides is not the
thing being decided about. So this command READS the corpus, finds the
claims it can see, and writes them as CANDIDATES. Nothing is held
until a writer (or a session with a human watching it) puts it there.

**AND A CANDIDATE IS NOT AN OPINION YET.** An opinion needs a subject
from the closed list, a stance, grounds, a date, a confidence and what
would change it -- and the register REFUSES one without them. So this
command's candidates carry the fields it can MEASURE (the claim, where
it came from, how many texts assert it, how strong the assertion is)
and leave the ones it cannot (the grounds, the falsifier) for the
writer.

**AND THE STRENGTH IS MEASURED, NOT ASSIGNED.** A claim that appears
in 1 of 13 texts is weaker than one in 9 of 13, and the frequency is
the measurement. And a claim whose assertion is hedged ("perhaps",
"arguably", "probably") is weaker than one that is not.

Run:
    python tools/propose_opinions.py
    python tools/propose_opinions.py --json
"""

from __future__ import annotations

import argparse
import collections
import json
import os
import re
import sys
from typing import Any, Dict, List, Optional, Sequence, Tuple

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
STORIES = os.path.join(REPO, "stories")
REGISTER = os.path.join(REPO, "state", "opinion_register.jsonl")

sys.path.insert(0, HERE)
import opinion as O  # noqa: E402


#: THE CLAIM PATTERN -- a sentence that makes a claim about a subject.
#:
#: AND IT IS A PATTERN AND NOT A JUDGE, because a command that judges
#: is a command with an opinion in it. The pattern finds SENTENCES THAT
#: ASSERT SOMETHING ABOUT A SUBJECT, and the counting says how often.
#:
#: AND IT NEEDS A SUBJECT FROM THE CLOSED LIST, because the register's
#: subjects are closed (`O.SUBJECTS`), and a claim about something
#: outside the closed list cannot become an opinion -- so naming it
#: would be offering something the register would refuse.
CLAIM_SENTENCE = re.compile(
    r"^[^.!?]*\b(?P<subject>%s)\b[^.!?]*[.!?]\s*$" % "|".join(
        re.escape(s) for s in sorted(O.SUBJECTS, key=len, reverse=True)),
    re.IGNORECASE)

#: THE STANCES, and they are the register's own closed list -- so a
#: candidate's stance is one the register would accept.
#:
#: AND THE STANCE FOLLOWS THE FREQUENCY, and not the hedge. MEASURED
#: 2026-11-06: the first version read the hedge off the sentence
#: ("probably" -> "probably"), but the hedge is the writer's mood on
#: one occasion and the FREQUENCY is how many of its own texts assert
#: the claim. **THE FREQUENCY IS THE MEASUREMENT AND THE HEDGE IS NOT.**
#:
#: So a claim asserted in 4+ texts is held "certainly", in 2-3
#: "probably", in 1 "arguably" -- and the register's own `stance` list
#: says exactly those words.
STANCE_BY_TEXTS: Tuple[Tuple[int, str], ...] = (
    (4, "certainly"),
    (2, "probably"),
    (1, "arguably"),
)


def _stance_for(n_texts: int) -> str:
    """The stance a claim in this many texts is held with."""
    for threshold, stance in STANCE_BY_TEXTS:
        if n_texts >= threshold:
            return stance
    return "arguably"

#: THE CLAIM VERBS -- the words that make a sentence ASSERT rather
#: than describe. MEASURED: a sentence with no claim verb is a
#: description, and a description is not an opinion.
CLAIM_VERBS = re.compile(
    r"\b(is|are|was|were|does|do|did|has|have|had|will|would|can|cannot|"
    r"should|must|makes|make|turns|turn|keeps|keep|takes|take|gives|give)\b",
    re.IGNORECASE)


def _read_texts(stories: str) -> List[Tuple[str, str]]:
    """Every text in the corpus, and its name."""
    out: List[Tuple[str, str]] = []
    if not os.path.isdir(stories):
        return out
    for name in sorted(os.listdir(stories)):
        if not name.endswith(".md"):
            continue
        path = os.path.join(stories, name)
        try:
            with open(path, encoding="utf-8") as fh:
                out.append((name, fh.read()))
        except OSError:
            continue
    return out


def _sentences(text: str) -> List[str]:
    """The sentences, and the ones that are long enough to claim
    something."""
    out: List[str] = []
    for raw in re.split(r"(?<=[.!?])\s+", text or ""):
        s = " ".join(raw.split())
        if len(s) < 25:
            continue
        out.append(s)
    return out


#: THE CLAIM TERMS -- the content words a claim is ABOUT, and the
#: carrier list is the same one the interest measure drops, because a
#: claim about "the day" is not a claim about anything.
#:
#: AND THIS IS THE TURN, AND IT IS THE ONE THAT MATTERS. MEASURED
#: 2026-11-06: the first version of this command matched WHOLE
#: SENTENCES and found 770 claim-shaped sentences across the 13 texts
#: -- and NOT ONE of them appeared in two texts, so the command
#: proposed nothing.
#:
#: **AND THAT WAS TRUE AND USELESS.** The writer's claims are not
#: repeated sentences; they are repeated TOPICS. The same claim about
#: power is made in six different books in six different words, and
#: matching the words finds nothing.
#:
#: So the candidate is a CLUSTER of claims about the same subject and
#: the same content words -- and the count is how many TEXTS assert
#: that cluster. **THE THING A WRITER HOLDS IS NOT A SENTENCE. IT IS
#: WHAT THE SENTENCES ARE ABOUT.**
CARRIER_TERMS = frozenset("""
day days hour hours morning time times year years past present
work working works thing things word words sentence sentences
story book argument question language writing way ways
human man people person reader woman women child children
power state country government law money work
""".split())


def _claim_terms(sentence: str) -> frozenset:
    """The content words the claim is about, with the carriers dropped."""
    words = [w.lower() for w in re.findall(r"[A-Za-z']+", sentence)]
    keep = [w for w in words
            if len(w) > 3 and w not in CARRIER_TERMS
            and w not in O.FUNCTION_WORDS]
    return frozenset(keep)


def find_candidates(stories: str = STORIES) -> List[Dict[str, Any]]:
    """The claims the corpus makes that are not in the register.

    **AND THE COUNT IS A COUNT OF TEXTS, NOT OF SENTENCES.** A claim
    asserted five times in one text is one text's claim, and counting
    it five times would make a writer that repeats itself look like it
    holds an opinion more strongly than one that says it once in five
    texts.

    AND THE CANDIDATE IS A CLUSTER, and the cluster is over the
    CONTENT WORDS of the claim -- because the writer's claims are
    repeated topics, not repeated sentences. And the cluster's key is
    its subject plus the words it shares with the other claims in the
    cluster.

    AND THE REGISTER'S OWN OPINIONS ARE EXCLUDED, so the command
    proposes what is MISSING and not what is already held.
    """
    reg = O.OpinionRegister.load(REGISTER) if os.path.isfile(REGISTER) \
        else O.OpinionRegister(path=REGISTER)
    held = reg.held()
    held_positions = {o.position.strip().lower() for o in held.values()}
    held_terms = {t.lower() for o in held.values() for t in o.terms()}

    # the claims, by their normalised shape
    by_claim: Dict[str, Dict[str, Any]] = {}
    for name, text in _read_texts(stories):
        for sent in _sentences(text):
            m = CLAIM_SENTENCE.match(sent)
            if not m:
                continue
            if not CLAIM_VERBS.search(sent):
                continue
            subject = m.group("subject").lower()
            claim = " ".join(sent.split())
            key = claim.lower()
            if key in held_positions:
                continue
            row = by_claim.setdefault(key, {
                "claim": claim,
                "subject": subject,
                "texts": [],
                "occurrences": 0,
            })
            if name not in row["texts"]:
                row["texts"].append(name)
            row["occurrences"] += 1

    # -- AND THE CLUSTERS, over the RAREST shared words ----------------
    #
    # AND THE CLUSTERING IS OVER THE SHARED CONTENT WORDS, and not over
    # the sentences. Two claims are in the same cluster when they share
    # a subject and enough of their content words.
    #
    # **AND THE SHARED WORDS MUST BE RARE, WHICH IS THE WHOLE FIX.**
    # MEASURED 2026-11-06: the first version clustered on ANY TWO
    # shared words -- and the top cluster came out as
    # "alice, asleep, back, bear, call, disgust, dormouse", which
    # merges a passage about a dormouse with a passage about a woman
    # reading papers aloud. The two shared words were "great" and
    # "piece", and those words are in HALF the corpus.
    #
    # **A WORD THAT HALF THE CORPUS USES IS A CONNECTOR, NOT A TOPIC.**
    # So the shared words that count are the ones that are RARE -- and
    # the rarity is measured from the corpus itself, by counting how
    # many TEXTS use each word.
    #
    # AND THE RARITY CUT IS NAMED, and it is a CONSTANT so it can be
    # swept: a word used in at most RARE_MAX_TEXTS of the corpus's
    # texts is distinctive enough to define a topic.
    RARE_MAX_TEXTS = 4
    MIN_SHARED = 1

    # AND HOW DEEP INTO THE RARE TERMS THE LINK MAY BE. A word that is
    # the cluster's 7th rarest is not what the cluster is about.
    LINK_DEPTH = 4

    # -- the word frequencies, by TEXT -------------------------------
    word_texts: collections.Counter = collections.Counter()
    for _name, _text in _read_texts(stories):
        for w in set(re.findall(r"[A-Za-z']+", (_text or "").lower())):
            if len(w) > 3:
                word_texts[w] += 1

    def _distinctive(terms: frozenset) -> frozenset:
        """The terms of the claim that are RARE in the corpus."""
        return frozenset(w for w in terms
                         if word_texts.get(w, 0) <= RARE_MAX_TEXTS)

    clusters: Dict[Tuple[str, frozenset], Dict[str, Any]] = {}
    for key, row in by_claim.items():
        terms = _claim_terms(row["claim"])
        if not terms:
            continue
        distinctive = _distinctive(terms)
        if not distinctive:
            # AND A CLAIM WITH NO RARE WORD IS ABOUT THE COMMON
            # GROUND, and it does not define a topic of its own.
            continue
        placed = False
        for (c_subject, c_terms), crow in clusters.items():
            if c_subject != row["subject"]:
                continue
            # AND THE SHARED WORD MUST BE AMONG THE RAREST OF BOTH
            # CLAIMS' TERMS.
            #
            # MEASURED 2026-11-06: with "any one shared rare word", the
            # top cluster came out with 45 terms spanning banks and coal
            # and coal-mines and baths -- because a cluster ACCEPTS a
            # claim on ONE shared word and then absorbs everything the
            # new claim brings with it. **A CLUSTER THAT ACCEPTS ON ONE
            # WORD AND THEN GROWS IS A CLUSTER THAT DRIFTS.**
            #
            # SO THE SHARED WORD MUST BE RARE ON BOTH SIDES -- the
            # rarest few of the cluster's terms, and the rarest few of
            # the claim's terms. So a claim joins a cluster only when
            # the word that links them is the WORD THAT DEFINES BOTH.
            link = distinctive & c_terms
            if not link:
                continue
            rarest_cluster = sorted(c_terms, key=lambda w: word_texts.get(w, 0))
            rarest_claim = sorted(distinctive, key=lambda w: word_texts.get(w, 0))
            cut_cluster = set(rarest_cluster[:LINK_DEPTH])
            cut_claim = set(rarest_claim[:LINK_DEPTH])
            if not (link & cut_cluster) or not (link & cut_claim):
                continue
            crow["claims"].append(row)
            crow["terms"] = c_terms | distinctive
            for t in row["texts"]:
                if t not in crow["texts"]:
                    crow["texts"].append(t)
            placed = True
            break
        if not placed:
            clusters[(row["subject"], distinctive)] = {
                "subject": row["subject"],
                "terms": distinctive,
                "claims": [row],
                "texts": list(row["texts"]),
            }

    out: List[Dict[str, Any]] = []
    for (subject, terms), crow in clusters.items():
        # AND A CLUSTER WHOSE TERMS ARE ALL ALREADY HELD IS NOT A NEW
        # OPINION -- it is the same opinion said again, and the register
        # already has it.
        if terms and terms <= held_terms:
            continue
        n_texts = len(crow["texts"])
        if n_texts < 1:
            continue
        # AND THE REPRESENTATIVE IS THE CLAIM WITH THE MOST TEXTS, and
        # then the longest, so the proposal is the writer's clearest
        # statement of the topic rather than its first.
        claims = sorted(crow["claims"],
                        key=lambda r: (-len(r["texts"]), -len(r["claim"])))
        rep = claims[0]
        stance = _stance_for(n_texts)
        out.append({
            "claim": rep["claim"],
            "subject": subject,
            "n_texts": n_texts,
            "occurrences": sum(c["occurrences"] for c in claims),
            "n_claims": len(claims),
            "stance": stance,
            "terms": sorted(terms)[:12],
            "texts": sorted(crow["texts"]),
            "examples": [c["claim"] for c in claims[:3]],
        })
    # AND THE ORDER IS BY HOW MANY TEXTS ASSERT IT, and then by the
    # claim, so the same corpus gives the same order every time.
    out.sort(key=lambda r: (-r["n_texts"], -r["occurrences"], r["claim"]))
    return out


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--stories", default=STORIES)
    ap.add_argument("--min-texts", type=int, default=2,
                    help="the fewest texts that must assert the claim")
    args = ap.parse_args(argv)

    candidates = find_candidates(args.stories)
    shown = [c for c in candidates if c["n_texts"] >= args.min_texts]
    n_texts_total = len(_read_texts(args.stories))

    if args.json:
        print(json.dumps({"candidates": shown,
                          "n_candidates": len(shown),
                          "n_clusters": len(candidates),
                          "n_texts": n_texts_total}, indent=2))
        return 0

    print("=" * 78)
    print("THE CLAIMS THE WRITER MAKES THAT THE REGISTER DOES NOT HOLD")
    print("=" * 78)
    print()
    print("  AND THESE ARE CANDIDATES, NOT OPINIONS. Nothing is held")
    print("  until a writer puts it there, and an opinion the register")
    print("  would refuse -- no grounds, no falsifier -- is not offered.")
    print()
    if not shown:
        print("  no candidate is asserted in %d or more texts" % args.min_texts)
        print()
        return 0
    n_texts_total = len(_read_texts(args.stories))
    for c in shown:
        print("  %d/%d texts  %d claims  [%s]" % (
            c["n_texts"], n_texts_total, c["n_claims"], c["stance"]))
        print("      %s" % c["claim"][:150])
        print("      the terms: %s" % ", ".join(c["terms"][:8]))
        print("      %s" % ", ".join(c["texts"][:4]))
        print()
    print("  %d candidate(s), and %d in total below the threshold"
          % (len(shown), len(candidates) - len(shown)))
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
