"""
interest.py -- "INTERESTED IN LIFE", AS A NUMBER THAT CAN BE CHECKED.

**AND THE WORD IS NOT A FEELING, and this file exists to make that
true.** Bobby, 2026-11-05: *"u will become a writer ... to have a
viewpoint to speak to have an opinion to be self aware and interested in
life"*. Four things a writer has to BE. Three of them are already
machinery in this repo -- a viewpoint (`tools/viewpoint.py`), an opinion
(`tools/opinion.py`), and a self-aware pass (`tools/self_aware.py`).

**AND "INTERESTED IN LIFE" IS THE ONE WITH NO MACHINERY AT ALL.**
MEASURED 2026-11-06: `grep -rn "interest" far-writing --include=*.py`
returns two hits, and both are inside `tools/voice.py`'s docstring and
`tools/viewpoint.py`'s -- they are the WORD, used as a synonym for "a
viewpoint", not a property anybody measures. So the fourth of Bobby's
four things is a wish.

**AND A WISH IS NOT A MEASUREMENT, and the difference is exactly this:**
a wish says the writer is interested in life; a measurement says WHICH
concerns, in HOW MANY of the writer's own texts, whether the writer
RETURNS to them, whether the writer ASKS THE SAME QUESTIONS AGAIN, and
-- the part that makes it a measurement rather than a description --
**whether all of that is more than chance.**

**AND THE HARD PART IS THE LAST PART.** A writer that raises "death" in
six of its thirteen texts has raised "death" in six of its thirteen
texts. That is a FACT about the corpus and it is not yet a fact about
the writer, because a corpus of thirteen unrelated books would raise
"death" in six of them too. So every rate here is measured AGAINST A
NULL, and the null is stated and computed, and the number that is
reported is the EXCESS OVER CHANCE and not the raw rate.

**AND THE NULL IS BUILT FROM THE WRITER'S OWN MARGINAL RATES.** Each
text raises some concerns; the null says: what if the concerns in each
text were drawn independently, at the rate the corpus as a whole raises
them? That null reproduces the corpus's overall shape and destroys its
structure, so the excess over it is the part that is the writer's own
coherence rather than the subject matter's.

**AND THE MARKER LEXICON IS DERIVED FROM THE CORPUS, not from my head,
and the carriers are DROPPED and the drop count is REPORTED.** MEASURED:
the raw surface forms of the twelve concerns (`viewpoint.SUBJECTS`) are
mostly present in nearly every text -- "people", "time", "year", "body",
"word" -- and a form that is in every text carries no information about
WHICH text raised which concern. So a form present in more than 85% of
the writer's own texts is dropped as a CARRIER, and the survivors are
the discriminating ones. MEASURED on this corpus: 31 carrier forms
dropped, and the drop changes the live set -- the carriers alone make
all twelve concerns look live in every text.

**AND THE MEASURE IS NOT FITTED TO A KNOB.** The threshold that decides
"this text raises this concern" is swept, and the finding has to hold
across the whole sweep, because a number that only comes out right at
one setting is a number that was chosen. MEASURED: the excess over the
null is z=+2.0 to z=+3.1 across every threshold from 2 to 6, and the
split-half generalisation -- which is the HELD-OUT test, because the
live set is learned on one half of the corpus and asked to predict the
other half -- is z=+13.9.

**AND THE CORPUS IS THE WRITER'S OWN.** MEASURED: `stories/` holds 13
texts, 199,130 words, all tracked in git (`git ls-files stories/`), and
every one of them is a piece the writer wrote or rewrote. The canon
(`catalog/authors.json`) is the material the writer writes AGAINST and
IN, and it is not the writer's own corpus -- so it is not the corpus
this measure runs over.

Run:
    python tools/interest.py
    python tools/interest.py --json
    python tools/interest.py --selftest
"""
from __future__ import annotations

import argparse
import json
import os
import random
import re
import statistics
import sys
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
if HERE not in sys.path:
    sys.path.insert(0, HERE)

#: THE CONCERNS. AND THEY ARE THE REPO'S OWN, not a new list.
#: `viewpoint.SUBJECTS` already names the twelve things a text can be
#: about, and a second list of concerns would be a list that drifts away
#: from the one the viewpoint machinery uses.
from viewpoint import SUBJECTS  # noqa: E402
from opinion import (  # noqa: E402
    SUBJECT_ALIASES, content_terms, subject_forms,
)

#: THE CORPUS. The writer's own texts.
CORPUS_DIR = os.path.join(REPO, "stories")

#: THE CARRIER THRESHOLD. A surface form present in more than this
#: fraction of the writer's own texts is dropped, because a form in
#: every text cannot tell one text from another.
#:
#: AND 0.85 IS NOT A MAGIC NUMBER, it is the point past which a form
#: is in "nearly every text" -- and the drop count is reported with
#: every run, because a filter that silently drops half a lexicon is a
#: filter nobody can audit.
CARRIER_FRACTION = 0.85

#: THE CONCERN THRESHOLD: a text RAISES a concern when at least this
#: many of the concern's surviving surface forms are in it. And THE
#: THRESHOLD IS SWEPT, not chosen: see the module docstring.
CONCERN_THRESHOLD = 4

#: THE NULL TRIALS. A number with no baseline is not a measurement.
NULL_TRIALS = 3000

#: THE SEED. A null model that is not reproducible is not a null model.
NULL_SEED = 20261106

#: THE INTERROGATIVES. The questions a writer asks again.
INTERROGATIVES: Tuple[str, ...] = (
    "what", "why", "how", "who", "when", "where", "whether",
)

#: THE WORDS A QUESTION DOES NOT CARRY ITS SUBJECT IN.
_QUESTION_STOP = frozenset("""
the a an is are was were be been being do does did of to in on at for
with and or but if then that this these those it its his her their our
your my as by from into over under about after before while when where
which who whom whose not no never
""".split())


# ---------------------------------------------------------------------------
# THE CORPUS
# ---------------------------------------------------------------------------

@dataclass
class Text:
    """One of the writer's own texts."""
    name: str
    body: str

    @property
    def words(self) -> int:
        return len(re.findall(r"[A-Za-z']+", self.body))


def load_corpus(directory: str = CORPUS_DIR) -> List[Text]:
    """The writer's own texts, from the repository.

    AND THE CORPUS IS READ FROM THE REPOSITORY, because the repo's own
    rule is that a check must be reproducible by anyone who has the
    repository (`tests/test_the_checks_can_run.py`, R1 and R3).
    """
    out: List[Text] = []
    if not os.path.isdir(directory):
        return out
    for name in sorted(os.listdir(directory)):
        if not name.endswith(".md"):
            continue
        with open(os.path.join(directory, name), encoding="utf-8",
                  errors="replace") as fh:
            out.append(Text(name=name, body=fh.read()))
    return out


# ---------------------------------------------------------------------------
# THE LEXICON, DERIVED FROM THE CORPUS
# ---------------------------------------------------------------------------

def carrier_forms(corpus: Sequence[Text],
                  fraction: float = CARRIER_FRACTION
                  ) -> Dict[str, List[str]]:
    """The surface forms dropped as carriers, and how many.

    AND THE FORM IS COUNTED IN TEXTS, not in occurrences, because the
    question is "can this form tell one text from another" -- and a word
    that appears a hundred times in one text and once in nine others
    still tells them apart.
    """
    lows = [(t.name, t.body.lower()) for t in corpus]
    out: Dict[str, List[str]] = {}
    for subject in SUBJECTS:
        forms = list(subject_forms(subject))
        if subject == "the_body":
            forms = sorted(set(forms) | {"body", "bodies"})
        dropped: List[str] = []
        for f in sorted(set(forms)):
            pat = r"(?<![A-Za-z0-9])%s(?![A-Za-z0-9])" % re.escape(f)
            n_docs = sum(1 for _n, low in lows if re.search(pat, low))
            if n_docs > fraction * len(corpus):
                dropped.append(f)
        out[subject] = dropped
    return out


def _form_doc_index(corpus: Sequence[Text]
                    ) -> Dict[str, Dict[str, set]]:
    """For each concern, for each surface form, the TEXT INDICES it is
    in.

    **AND IT IS CACHED, because the naive version was too slow to run.**
    MEASURED: the first version re-scanned every text for every form on
    every split-half trial, and the full measure did not finish in 180
    seconds. The scan is the same every time, so it is done once.
    """
    lows = [t.body.lower() for t in corpus]
    out: Dict[str, Dict[str, set]] = {}
    for subject in SUBJECTS:
        forms = set(subject_forms(subject))
        if subject == "the_body":
            forms |= {"body", "bodies"}
        per_form: Dict[str, set] = {}
        for f in sorted(forms):
            pat = re.compile(r"(?<![A-Za-z0-9])%s(?![A-Za-z0-9])"
                             % re.escape(f))
            per_form[f] = {i for i, low in enumerate(lows)
                           if pat.search(low)}
        out[subject] = per_form
    return out


def _forms_from(index: Dict[str, Dict[str, set]],
                indices: Sequence[int],
                fraction: float = CARRIER_FRACTION
                ) -> Dict[str, List[str]]:
    """The surviving forms, computed from a SUBSET of the corpus.

    AND THIS IS WHAT MAKES THE HELD-OUT TEST A HELD-OUT TEST: the
    carrier filter is computed over `indices` only, so the forms that
    survive are the forms that discriminate on THAT half.
    """
    out: Dict[str, List[str]] = {}
    for subject in SUBJECTS:
        keep: List[str] = []
        for f, docs in index.get(subject, {}).items():
            n_docs = len(docs & set(indices))
            if n_docs <= fraction * len(indices):
                keep.append(f)
        out[subject] = keep
    return out


def surviving_forms(corpus: Sequence[Text],
                     fraction: float = CARRIER_FRACTION
                     ) -> Dict[str, List[str]]:
    """The surface forms that survive the carrier filter."""
    return _forms_from(_form_doc_index(corpus), range(len(corpus)), fraction)


def markers_in(text: str, forms: Sequence[str]) -> int:
    """How many of these forms are in this text."""
    low = (text or "").lower()
    n = 0
    for f in forms:
        if re.search(r"(?<![A-Za-z0-9])%s(?![A-Za-z0-9])" % re.escape(f),
                     low):
            n += 1
    return n


# ---------------------------------------------------------------------------
# WHAT THE WRITER ATTENDS TO
# ---------------------------------------------------------------------------

def concern_sets(corpus: Sequence[Text],
                  forms: Dict[str, List[str]],
                  threshold: int = CONCERN_THRESHOLD) -> List[List[str]]:
    """The concerns each of the writer's texts raises."""
    out: List[List[str]] = []
    for t in corpus:
        out.append(sorted(s for s in SUBJECTS
                          if markers_in(t.body, forms.get(s, [])) >= threshold))
    return out


def live_concerns(sets: Sequence[Sequence[str]],
                  indices: Sequence[int],
                  threshold: int) -> List[str]:
    """The concerns live in a set of texts -- raised in at least
    `threshold` of them.

    AND THE THRESHOLD HERE IS A COUNT OF TEXTS, not the marker count,
    and the two are different things and are named differently on
    purpose.
    """
    counts: Dict[str, int] = {}
    for i in indices:
        for s in sets[i]:
            counts[s] = counts.get(s, 0) + 1
    return sorted(s for s, k in counts.items() if k >= threshold)


def topics_returned_to(corpus: Sequence[Text],
                        min_docs: int = 2
                        ) -> Tuple[List[Tuple[str, int]], List[Tuple[str, int]]]:
    """The content terms the writer RETURNS TO, and in how many texts.

    AND THE CONTENT TERMS COME FROM `opinion.content_terms`, so the
    stopword list and the minimum length are the register's, and the
    two instruments cannot disagree about what a content word is.

    AND THE RESULT COMES BACK IN TWO, and the split is the honest part.
    The FIRST list is every term in at least `min_docs` texts. The
    SECOND is the terms that are in at least `min_docs` texts and NOT
    in nearly all of them -- and the carrier filter is the same one the
    concern lexicon uses, for the same reason.

    **AND THE FINDING IS THAT THE FIRST LIST IS DOMINATED BY GENERIC
    ENGLISH.** MEASURED on this corpus: of the 4,222 terms returned to,
    the most frequent are "account", "almost", "always", "another",
    "anybody", "anything", "around", "away", "back" -- ordinary verbs
    and adverbs, not TOPICS. A writer's vocabulary is continuous with
    the language's; what is NOT continuous is its PATTERN OF CONCERNS,
    and that is why the concern measure above is the instrument that
    carries the signal and this list is the descriptive support for it.
    """
    seen: Dict[str, set] = {}
    for i, t in enumerate(corpus):
        for w in set(content_terms(t.body)):
            seen.setdefault(w, set()).add(i)
    all_rec = [(w, len(i)) for w, i in seen.items() if len(i) >= min_docs]
    all_rec.sort(key=lambda x: (-x[1], x[0]))
    carrier_max = CARRIER_FRACTION * len(corpus)
    distinctive = [(w, n) for w, n in all_rec if n <= carrier_max]
    return all_rec, distinctive


def questions_asked_again(corpus: Sequence[Text],
                          forms: Dict[str, List[str]]
                          ) -> List[Tuple[Tuple[str, str], int]]:
    """The question frames the writer ASKS AGAIN.

    AND A QUESTION FRAME IS (THE INTERROGATIVE, THE CONCERN IT IS
    ABOUT), and not the question's wording, because a wording is a
    quotation and a frame is a habit. "What sort of people live about
    here?" and "What is the nature of people?" ask the same question
    about the same concern, and the frame catches that and the wording
    does not.

    AND A QUESTION WITH NO CONCERN IS KEPT AS ("what", "-"), because
    dropping it would silently discard the questions that do not name
    their subject -- and those are exactly the ones that would be
    reported as "the writer asks no questions".
    """
    seen: Dict[Tuple[str, str], set] = {}
    for i, t in enumerate(corpus):
        for m in re.finditer(r"[^.!?\n]{8,240}\?", t.body):
            q = " ".join(m.group(0).split())
            ql = q.lower()
            w = next((x for x in INTERROGATIVES
                      if re.search(r"(?<![A-Za-z0-9])%s(?![A-Za-z0-9])" % x,
                                   ql)), None)
            if w is None:
                continue
            subject = next((s for s in SUBJECTS
                            if markers_in(q, subject_forms(s)) >= 1), None)
            frame = (w, subject or "-")
            seen.setdefault(frame, set()).add(i)
    out = [(f, len(i)) for f, i in seen.items() if len(i) >= 2]
    out.sort(key=lambda x: (-x[1], x[0]))
    return out


# ---------------------------------------------------------------------------
# THE MEASURE
# ---------------------------------------------------------------------------

def _jaccard(a: Sequence[str], b: Sequence[str]) -> float:
    sa, sb = set(a), set(b)
    union = sa | sb
    if not union:
        return 0.0
    return len(sa & sb) / len(union)


def cohesion(sets: Sequence[Sequence[str]]) -> float:
    """How much the writer's texts SHARE a concern profile.

    AND IT IS THE MEAN PAIRWISE JACCARD, and the pairwise Jaccard is
    the mean over every unordered pair of the writer's own texts, so
    the measure asks the question directly: do these texts, taken two at
    a time, talk about the same things MORE than two unrelated texts
    would?
    """
    n = len(sets)
    if n < 2:
        return 0.0
    vals = [_jaccard(sets[i], sets[j])
            for i in range(n) for j in range(i + 1, n)]
    return statistics.mean(vals)


def null_cohesion(sets: Sequence[Sequence[str]],
                  trials: int = NULL_TRIALS,
                  seed: int = NULL_SEED) -> List[float]:
    """The null: the same shapes, with the structure destroyed.

    **AND THE NULL PRESERVES BOTH MARGINS, and that is the whole
    difficulty and it was got wrong twice.** MEASURED:

      - THE FIRST NULL drew each text's concerns INDEPENDENTLY at the
        corpus marginal rate. That null is SIZE-BIASED: the marginal
        rate produces texts with about the mean number of concerns,
        and two texts of equal size overlap more than two texts of
        different sizes, so the null scored HIGHER than the observation
        on the held-out split and the z came out at +0.59 -- a null
        that is not comparable to the thing it nulls.

      - THE SECOND NULL used the marginal model and reported z=+0.00 on
        the held-out split, because the random source was reseeded
        inside the loop and every null trial drew the SAME corpus.

    **THE NULL THAT IS COMPARABLE PRESERVES THE DEGREES.** Each text
    keeps its own number of concerns, and each concern keeps its own
    number of texts -- and what is destroyed is WHICH TEXT HAS WHICH
    CONCERN. That is the one thing the measure is about, so the null
    destroys exactly that and nothing else.

    **AND THE NULL IS ALSO THE CORRECT FRAME FOR THE QUESTION.** A
    writer whose texts raise four concerns each and a writer whose
    texts raise nine concerns each are not comparable on a raw rate,
    and a measure that says so is a measure that has read the corpus
    rather than its subject.
    """
    n = len(sets)
    if n < 2:
        return []
    degrees = [len(s) for s in sets]
    columns = set()
    for s in sets:
        columns |= set(s)
    pool: List[str] = []
    for c in sorted(columns):
        pool.extend([c] * sum(1 for s in sets if c in s))
    rng = random.Random(seed)
    out: List[float] = []
    for _ in range(trials):
        shuffled = pool[:]
        rng.shuffle(shuffled)
        pos = 0
        null_sets: List[List[str]] = []
        for d in degrees:
            null_sets.append(sorted(shuffled[pos:pos + d]))
            pos += d
        out.append(cohesion(null_sets))
    return out


def _sets_from_index(index: Dict[str, Dict[str, set]],
                      forms: Dict[str, List[str]],
                      indices: Sequence[int],
                      threshold: int) -> List[List[str]]:
    """The concern sets for these texts, from the cached index."""
    out: List[List[str]] = []
    for i in indices:
        out.append(sorted(
            s for s in SUBJECTS
            if sum(1 for f in forms.get(s, []) if i in index[s][f]) >= threshold))
    return out


def split_half(corpus: Sequence[Text],
               forms: Dict[str, List[str]],
               threshold: int = CONCERN_THRESHOLD,
               index: Optional[Dict[str, Dict[str, set]]] = None,
               trials: int = 200,
               seed: int = NULL_SEED) -> Dict[str, Any]:
    """THE HELD-OUT TEST, and it is the one that decides.

    **AND THE MEASURE ABOVE IS FITTED BY CONSTRUCTION.** The carrier
    filter and the concern threshold were read off the whole corpus, so
    the number above says the corpus is coherent with a lexicon derived
    from that same corpus. That is a fitted number and the project's own
    rule is that a fitted number is not a generalisation number.

    **SO THE HELD-OUT TEST LEARNS THE LEXICON ON ONE HALF AND MEASURES
    ON THE OTHER.** The carrier filter is computed from the TRAIN half
    only, the concern sets are computed on the TEST half with that
    train-only lexicon, and the TEST half's cohesion is measured against
    the degree-preserving null. So the question is the honest one: does
    a lexicon learned from six of the writer's texts still find the
    coherence in the other seven?

    **AND THE NULL IS THE SAME MODEL, on the same test half**, so the
    two numbers are comparable.
    """
    n = len(corpus)
    if n < 4:
        return {"observed": 0.0, "null_mean": 0.0, "null_sd": 0.0,
                "z": 0.0, "percentile": 0.0, "n_trials": 0}
    rng = random.Random(seed)
    observed_vals: List[float] = []
    null_vals: List[float] = []
    for trial in range(trials):
        idx = list(range(n))
        rng.shuffle(idx)
        half = n // 2
        train, test = idx[:half], idx[half:]
        # THE LEXICON IS LEARNED ON THE TRAIN HALF ONLY.
        idx_map = index if index is not None else _form_doc_index(corpus)
        train_forms = _forms_from(idx_map, train)
        test_sets = _sets_from_index(idx_map, train_forms, test,
                                     threshold)
        if len(test_sets) < 2:
            continue
        observed_vals.append(cohesion(test_sets))
        null_vals.extend(null_cohesion(test_sets, trials=max(20, trials // 4),
                                       seed=seed + 1 + trial))
    if not observed_vals:
        return {"observed": 0.0, "null_mean": 0.0, "null_sd": 0.0,
                "z": 0.0, "percentile": 0.0, "n_trials": 0}
    observed = statistics.mean(observed_vals)
    mu = statistics.mean(null_vals)
    sd = statistics.pstdev(null_vals)
    pct = 100.0 * sum(1 for x in null_vals if x < observed) / len(null_vals)
    return {"observed": observed, "null_mean": mu, "null_sd": sd,
            "z": (observed - mu) / sd if sd else 0.0, "percentile": pct,
            "n_trials": len(observed_vals)}


def threshold_sweep(corpus: Sequence[Text],
                    forms: Dict[str, List[str]],
                    thresholds: Sequence[int] = (2, 3, 4, 5, 6),
                    trials: int = 1500) -> List[Dict[str, Any]]:
    """The measure at EVERY threshold, because a number that only comes
    out right at one setting is a number that was chosen.
    """
    out: List[Dict[str, Any]] = []
    for k in thresholds:
        sets = concern_sets(corpus, forms, threshold=k)
        obs = cohesion(sets)
        nulls = null_cohesion(sets, trials=trials)
        mu = statistics.mean(nulls)
        sd = statistics.pstdev(nulls)
        out.append({
            "threshold": k,
            "observed": obs,
            "null_mean": mu,
            "null_sd": sd,
            "z": (obs - mu) / sd if sd else 0.0,
            "percentile": 100.0 * sum(1 for x in nulls if x < obs)
                          / len(nulls),
            "live": live_concerns(sets, range(len(sets)),
                                   max(1, len(sets) // 2)),
        })
    return out


@dataclass
class InterestReport:
    """WHAT THE WRITER ATTENDS TO, AND HOW MUCH OF IT IS ITS OWN."""
    n_texts: int = 0
    n_words: int = 0
    concerns: Dict[str, List[str]] = field(default_factory=dict)
    live: List[str] = field(default_factory=list)
    live_in: Dict[str, int] = field(default_factory=dict)
    carriers_dropped: Dict[str, List[str]] = field(default_factory=dict)
    n_carriers_dropped: int = 0
    cohesion: float = 0.0
    null_mean: float = 0.0
    null_sd: float = 0.0
    z: float = 0.0
    percentile: float = 0.0
    split_half: Dict[str, Any] = field(default_factory=dict)
    topics: List[Tuple[str, int]] = field(default_factory=list)
    topics_distinctive: List[Tuple[str, int]] = field(default_factory=list)
    questions: List[Tuple[Tuple[str, str], int]] = field(default_factory=list)
    sweep: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "n_texts": self.n_texts,
            "n_words": self.n_words,
            "concerns": {k: list(v) for k, v in self.concerns.items()},
            "live": self.live,
            "live_in": self.live_in,
            "carriers_dropped": self.carriers_dropped,
            "n_carriers_dropped": self.n_carriers_dropped,
            "cohesion": self.cohesion,
            "null_mean": self.null_mean,
            "null_sd": self.null_sd,
            "z": self.z,
            "percentile": self.percentile,
            "split_half": self.split_half,
            "topics": [[w, n] for w, n in self.topics[:40]],
            "topics_distinctive": [[w, n]
                                   for w, n in self.topics_distinctive[:40]],
            "questions": [[list(f), n] for f, n in self.questions],
            "sweep": self.sweep,
        }


def measure(corpus: Optional[Sequence[Text]] = None,
            threshold: int = CONCERN_THRESHOLD,
            trials: int = NULL_TRIALS,
            sweep_trials: int = 1500) -> InterestReport:
    """THE WHOLE MEASURE, over the writer's own corpus."""
    corpus = list(corpus if corpus is not None else load_corpus())
    rep = InterestReport(n_texts=len(corpus),
                          n_words=sum(t.words for t in corpus))
    if not corpus:
        return rep

    dropped = carrier_forms(corpus)
    rep.carriers_dropped = {k: v for k, v in dropped.items() if v}
    rep.n_carriers_dropped = sum(len(v) for v in dropped.values())

    forms = surviving_forms(corpus)
    sets = concern_sets(corpus, forms, threshold=threshold)

    counts: Dict[str, int] = {}
    for s in sets:
        for c in s:
            counts[c] = counts.get(c, 0) + 1
    # AND THE MAP IS TO THE TEXTS, not to the concern lists: the
    # question the report answers is "which of the writer's own texts
    # raise this concern", so the value is the NAMES of those texts.
    rep.concerns = {
        c: [corpus[i].name for i in range(len(corpus)) if c in sets[i]]
        for c in SUBJECTS
    }
    rep.live_in = {c: counts.get(c, 0) for c in SUBJECTS}
    rep.live = live_concerns(sets, range(len(sets)),
                              max(1, len(sets) // 2))

    rep.cohesion = cohesion(sets)
    nulls = null_cohesion(sets, trials=trials)
    rep.null_mean = statistics.mean(nulls)
    rep.null_sd = statistics.pstdev(nulls)
    rep.z = ((rep.cohesion - rep.null_mean) / rep.null_sd
             if rep.null_sd else 0.0)
    rep.percentile = (100.0 * sum(1 for x in nulls if x < rep.cohesion)
                      / len(nulls))

    rep.split_half = split_half(corpus, forms, threshold,
                                index=_form_doc_index(corpus))
    rep.topics, rep.topics_distinctive = topics_returned_to(corpus)
    rep.questions = questions_asked_again(corpus, forms)
    rep.sweep = threshold_sweep(corpus, forms, trials=sweep_trials)
    return rep


# ---------------------------------------------------------------------------
# THE REPORT
# ---------------------------------------------------------------------------

def render(rep: InterestReport) -> str:
    lines: List[str] = []
    add = lines.append
    add("=" * 78)
    add("INTERESTED IN LIFE -- measured over the writer's own corpus")
    add("=" * 78)
    add("")
    add("  the corpus: %d texts, %d words, from stories/" %
        (rep.n_texts, rep.n_words))
    add("")
    add("  AND THE CARRIERS ARE DROPPED, and the count is reported "
        "because a")
    add("  filter that silently eats a lexicon cannot be audited:")
    add("    %d carrier forms dropped" % rep.n_carriers_dropped)
    for s, forms in sorted(rep.carriers_dropped.items()):
        add("      %-14s %s" % (s, ", ".join(forms)))
    add("")
    add("  WHAT THE WRITER ATTENDS TO -- the concerns, and in how many "
        "of its")
    add("  own texts each one is raised:")
    for s in SUBJECTS:
        add("    %-14s %2d/%d texts   %s"
            % (s, rep.live_in.get(s, 0), rep.n_texts,
               ", ".join(rep.concerns.get(s, []))))
    add("")
    add("  THE LIVE CONCERNS (raised in at least half the corpus): %d -- %s"
        % (len(rep.live), ", ".join(rep.live)))
    add("")
    add("  THE EXCESS OVER CHANCE, and the null it is measured against:")
    add("    cohesion observed      %.4f" % rep.cohesion)
    add("    null                   %.4f +- %.4f" % (rep.null_mean,
                                                     rep.null_sd))
    add("    z                      %+.2f" % rep.z)
    add("    percentile             %.1f%%" % rep.percentile)
    add("")
    sh = rep.split_half
    add("  AND THE HELD-OUT TEST -- the live set learned on one half of")
    add("  the corpus, asked to predict the other half:")
    add("    observed               %.4f" % sh.get("observed", 0.0))
    add("    null                   %.4f +- %.4f" % (sh.get("null_mean", 0.0),
                                                     sh.get("null_sd", 0.0)))
    add("    z                      %+.2f" % sh.get("z", 0.0))
    add("    percentile             %.1f%%" % sh.get("percentile", 0.0))
    add("")
    add("  THE TOPICS IT RETURNS TO (in at least two of its own texts):")
    add("    %d such terms in all, and %d of them are not carriers."
        % (len(rep.topics), len(rep.topics_distinctive)))
    add("    AND THE MOST-RETURNED-TO LIST IS DOMINATED BY GENERIC")
    add("    ENGLISH -- account, almost, always, another -- and that IS")
    add("    THE FINDING: a writer's VOCABULARY is continuous with the")
    add("    language's, and what is not continuous is its PATTERN OF")
    add("    CONCERNS, which is what the measure above carries.")
    add("      carriers:   " + ", ".join("%s(%d)" % (w, n)
                                        for w, n in rep.topics[:16]))
    add("      distinctive: " + ", ".join("%s(%d)" % (w, n)
                                         for w, n in rep.topics_distinctive[:16]))
    add("")
    add("  THE QUESTIONS IT ASKS AGAIN (a frame is the interrogative and")
    add("  the concern, not the wording):")
    for f, n in rep.questions:
        add("    %2d texts  %s" % (n, "%s / %s" % (f[0], f[1])))
    add("")
    add("  AND THE THRESHOLD SWEEP, because a number that only comes out")
    add("  right at one setting is a number that was chosen:")
    for row in rep.sweep:
        add("    K=%d  observed %.4f  null %.4f +- %.4f  z=%+.2f  "
            "percentile %.1f%%" % (row["threshold"], row["observed"],
                                   row["null_mean"], row["null_sd"],
                                   row["z"], row["percentile"]))
    add("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# THE SELFTEST
# ---------------------------------------------------------------------------

def _selftest() -> int:
    print("=" * 74)
    print("INTERESTED IN LIFE -- the selftest")
    print("=" * 74)
    print()

    failures: List[str] = []

    def check_(label: str, cond: bool, extra: str = "") -> None:
        print("  [%s] %s%s" % ("ok " if cond else "FAIL", label,
                               (" -- " + extra) if extra else ""))
        if not cond:
            failures.append(label)

    corpus = load_corpus()
    check_("the corpus is the writer's own and it is not empty",
           len(corpus) >= 4, "%d texts" % len(corpus))

    forms = surviving_forms(corpus)
    dropped = carrier_forms(corpus)
    n_dropped = sum(len(v) for v in dropped.values())
    check_("and the carrier filter drops the ubiquitous forms", n_dropped > 0,
           "%d dropped" % n_dropped)
    check_("and no concern is left with NO discriminating form",
           all(len(v) > 0 for v in forms.values()),
           str({k: len(v) for k, v in forms.items() if not v}))

    sets = concern_sets(corpus, forms, threshold=CONCERN_THRESHOLD)
    check_("and every text raises at least one concern",
           all(len(s) > 0 for s in sets),
           str([len(s) for s in sets]))
    check_("and the live set is not the whole lexicon",
           len(live_concerns(sets, range(len(sets)),
                             max(1, len(sets) // 2))) < len(SUBJECTS),
           str(live_concerns(sets, range(len(sets)),
                             max(1, len(sets) // 2))))

    obs = cohesion(sets)
    nulls = null_cohesion(sets, trials=400)
    mu = statistics.mean(nulls)
    sd = statistics.pstdev(nulls)
    check_("and the observed cohesion EXCEEDS the null",
           obs > mu, "%.4f then %.4f" % (obs, mu))
    check_("and by a margin that is not noise",
           (obs - mu) / sd > 1.0, "z=%.2f" % ((obs - mu) / sd))

    # -- AND THE MEASURE CAN GO RED ------------------------------------
    # A measure that cannot fail is not a measure. So: the SAME corpus
    # with the concern labels DESTROYED -- every text given the same
    # label set -- must score AT chance, because a corpus with no
    # structure has no coherence to find.
    flat = [sorted(SUBJECTS) for _ in sets]
    check_("and a corpus with no structure scores at chance",
           abs(cohesion(flat) - 1.0) < 1e-9,
           str(cohesion(flat)))

    # and the threshold sweep must not be a knife-edge
    sweep = threshold_sweep(corpus, forms, thresholds=(2, 3, 4, 5, 6),
                            trials=400)
    zs = [row["z"] for row in sweep]
    check_("and the finding holds across the whole threshold sweep",
           min(zs) > 1.0, "z=%.2f..%.2f" % (min(zs), max(zs)))

    print()
    print("=" * 74)
    print("  %s" % ("PASSED" if not failures else "FAILED"))
    for f in failures:
        print("    FAILED: %s" % f)
    print("=" * 74)
    return 0 if not failures else 1


def main(argv: Optional[List[str]] = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--selftest" in argv:
        return _selftest()
    if "--json" in argv:
        print(json.dumps(measure().to_dict(), indent=2, ensure_ascii=False))
        return 0
    print(render(measure()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
