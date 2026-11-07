"""
test_writer_loop.py -- the writer's daily pass can go RED.

Bobby, 2026-11-06: *"u will become a writer"*.

**AND WHAT IS BEING PROVEN:**

    1  THE DECISION IS AN INPUT, NOT A MODEL CALL -- and the loop NEVER
       writes its own decisions.
    2  A PARTIAL DECISION IS REFUSED BY NAME, because the register
       would refuse the opinion it produces.
    3  THE LOOP'S COUNTS ADD UP: proposed = admitted + refused.
    4  THE ARTIFACT CARRIES A DIGEST OF ITS OWN CONTENT, and the
       digest is over the payload WITHOUT the digest field.
    5  THE DRY RUN WRITES NOTHING.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
TOOLS = os.path.join(REPO, "tools")
if TOOLS not in sys.path:
    sys.path.insert(0, TOOLS)

import opinion as O  # noqa: E402
import propose_opinions as P  # noqa: E402
import writer_loop as W  # noqa: E402


# ---------------------------------------------------------------------------
# 1. the decision is an INPUT
# ---------------------------------------------------------------------------

def test_the_loop_never_writes_its_own_decisions():
    """**A LOOP THAT WRITES ITS OWN DECISIONS GRADES ITS OWN
    HOMEWORK.**

    AND THE CHECK IS ON THE SOURCE, because a loop that opens the
    decisions file for WRITING is a loop that grades its own homework,
    and it would look exactly like one that does not.
    """
    src = open(os.path.join(TOOLS, "writer_loop.py"), encoding="utf-8").read()
    assert '"w"' not in src, "the loop opens the decisions file for writing"
    assert "'w'" not in src, "the loop opens the decisions file for writing"
    # AND IT MUST NOT WRITE THE DECISIONS FILE AT ALL.
    assert "confirmed.json" not in src.split("DECISIONS_FILE = ")[1][:200] \
        or "open(" not in src.split("DECISIONS_FILE = ")[1][:200]


def test_a_decision_is_read_by_claim_text(tmp_path):
    """**AND THE CONFIRMATION IS BY THE CLAIM THE WRITER READ**, not by
    a key the proposer derived -- because the key would change if the
    corpus changed."""
    d = {"confirmed": [{
        "claim": "The writer is a voice and not a person.",
        "grounds": "measured over 6 texts",
        "confidence": 0.5,
        "would_change": "a text that says otherwise",
    }]}
    path = tmp_path / "confirmed.json"
    path.write_text(json.dumps(d), encoding="utf-8")
    decisions, refusals = W.load_decisions(str(path))
    assert not refusals, refusals
    assert len(decisions) == 1
    assert "the writer is a voice and not a person." in decisions


def test_the_key_is_derived_from_the_claim():
    """**AND THE KEY IS THE SAME ONE THE PROPOSER DERIVES**, so a
    decision about a candidate and the candidate itself agree."""
    claim = "The writer is a voice and not a person."
    key = W._key_for(claim)
    assert key.startswith("candidate_")
    # AND IT IS STABLE.
    assert W._key_for(claim) == key
    # AND A DIFFERENT CLAIM GETS A DIFFERENT KEY.
    assert W._key_for(claim + " And more.") != key


# ---------------------------------------------------------------------------
# 2. a partial decision is refused by name
# ---------------------------------------------------------------------------

def test_a_partial_decision_is_refused_and_named(tmp_path):
    """**A DECISION FILE THAT CARRIES A PARTIAL OPINION WOULD PUSH THE
    FAILURE TO THE FAR END.**"""
    d = {"confirmed": [{"claim": "x", "grounds": ""}]}
    path = tmp_path / "confirmed.json"
    path.write_text(json.dumps(d), encoding="utf-8")
    decisions, refusals = W.load_decisions(str(path))
    assert not decisions
    assert len(refusals) == 1
    for field in ("grounds", "confidence", "would_change"):
        assert field in refusals[0], refusals[0]


def test_a_decision_with_every_field_is_accepted(tmp_path):
    d = {"confirmed": [{
        "claim": "The writer is a voice.",
        "grounds": "measured",
        "confidence": 0.4,
        "would_change": "a text that says otherwise",
    }]}
    path = tmp_path / "confirmed.json"
    path.write_text(json.dumps(d), encoding="utf-8")
    decisions, refusals = W.load_decisions(str(path))
    assert len(decisions) == 1
    assert not refusals


def test_a_missing_decisions_file_is_not_an_error(tmp_path):
    """**AND A DAY WITH NO DECISIONS IS A QUIET DAY, NOT A BROKEN
    ONE.**"""
    decisions, refusals = W.load_decisions(str(tmp_path / "nothing.json"))
    assert decisions == {}
    assert refusals == []


# ---------------------------------------------------------------------------
# 3. the counts add up
# ---------------------------------------------------------------------------

def test_the_counts_add_up(tmp_path):
    """**A SCORE THAT DOES NOT ADD UP IS A SCORE NOBODY CAN TRUST
    WITHOUT REDOING THE SUM BY HAND.**"""
    payload = W.run(decisions_path=str(tmp_path / "nothing.json"))
    assert payload["candidates"] >= 1
    # AND THE REFUSALS ARE ONE PER CANDIDATE THAT WAS NOT ADMITTED.
    assert payload["refused"] >= payload["candidates"] - payload["admitted"]
    assert payload["register_after"] >= payload["register_before"]


def test_a_candidate_with_no_decision_is_refused_by_name(tmp_path):
    payload = W.run(decisions_path=str(tmp_path / "nothing.json"))
    assert payload["admitted"] == 0, payload["admitted"]
    assert payload["refusal_reasons"], "the refusals were not named"


# ---------------------------------------------------------------------------
# 3b. a CONFIRMED candidate is ADMITTED, not refused by the register
# ---------------------------------------------------------------------------

def test_a_confirmed_candidate_is_admitted_and_not_refused(tmp_path):
    """**AND A CONFIRMED CANDIDATE ACTUALLY GETS IN.**

    MEASURED 2026-11-07: the loop handed the register the CLUSTER's
    terms -- `cand["terms"][:4]` -- but a cluster's terms are the
    words the cluster is about, and a cluster spans several
    sentences, so most of them are words of the OTHER claims in the
    cluster. The register refuses an opinion whose claim term is not
    a word of its position, and it refused HALF the admissions:

        candidates 21, admitted 10, refused 11
        the register refused 'And the reason it is addressed to every
        species ': the opinion 'candidate_6970fdce' carries the term
        'imperial', which is not a word of it

    So the loop was throwing away its own work, and the reason was
    pushed to the far end where the mistake was.

    **AND THE CHECK IS ON THE REAL CORPUS, with a decision for EVERY
    candidate** -- because a check that only admits a hand-written
    claim would not have seen this at all: the hand-written claim
    "The writer is a voice." carries no cluster terms, so it took
    the path that worked.
    """
    cands = [c for c in P.find_candidates() if c["n_texts"] >= 2]
    assert cands, "the proposer found no candidate in the writer's corpus"
    d = {"confirmed": [{
        "claim": c["claim"],
        "grounds": "asserted in %d of the writer's own texts" % c["n_texts"],
        "confidence": 0.5,
        "would_change": "a text that denies it",
    } for c in cands]}
    path = tmp_path / "confirmed.json"
    path.write_text(json.dumps(d), encoding="utf-8")

    # AND THE REGISTER IS A COPY, because the loop writes to it and
    # the writer's real register is not a test scratchpad.
    import shutil
    state = tmp_path / "state"
    shutil.copytree(os.path.join(REPO, "state"), str(state))
    old_state = W.STATE
    W.STATE = str(state)
    try:
        payload = W.run(decisions_path=str(path))
    finally:
        W.STATE = old_state

    assert payload["admitted"] == payload["candidates"], (
        "only %d of %d confirmed candidates were admitted -- the refusals "
        "were: %s" % (payload["admitted"], payload["candidates"],
                      payload["refusal_reasons"][:3]))
    assert payload["refused"] == 0, payload["refusal_reasons"][:3]


def test_the_claim_terms_are_words_of_the_claim():
    """**AND EVERY CLAIM TERM IS A WORD OF THE POSITION.**

    The register refuses an opinion whose claim term is not a word of
    its own position -- a term that is about something else would carry
    a contradiction against the wrong thing. So the terms the loop
    hands over must pass that rule.
    """
    for c in P.find_candidates():
        terms = W._claim_terms(c)
        for t in terms:
            assert re.search(r"(?<![A-Za-z0-9])%s(?![A-Za-z0-9])"
                             % re.escape(t.lower()),
                             c["claim"].lower()), (
                "the term %r is not a word of the claim %r"
                % (t, c["claim"][:60]))


def test_the_loop_terms_fall_back_to_the_positions_own_words():
    """**AND WHEN NO CLUSTER TERM IS A WORD OF THE CLAIM, THE POSITION'S
    OWN CONTENT WORDS ARE USED.** Because those are always words of
    the position."""
    c = {"claim": "The writer is a voice, and the voice is measured.",
         "terms": ["elephant", "giraffe"]}
    terms = W._claim_terms(c)
    assert terms, "no terms were derived at all"
    for t in terms:
        assert re.search(r"(?<![A-Za-z0-9])%s(?![A-Za-z0-9])"
                         % re.escape(t.lower()), c["claim"].lower()), t


def test_the_admitted_count_matches_the_register(tmp_path):
    """**AND THE LOOP'S OWN COUNT MATCHES THE REGISTER'S OWN COUNT.**

    A loop that says "21 admitted" while the register grew by 6 has
    counted something that did not happen -- and the way it goes
    wrong is by counting a REFUSAL as an admission.

    MEASURED 2026-11-07: this check is what catches the mutation
    where the register's refusal is counted as an admission. The loop
    would report every candidate as held, and the register would hold
    only the ones it actually accepted. So the two numbers must agree.
    """
    import shutil
    cands = [c for c in P.find_candidates() if c["n_texts"] >= 2]
    assert cands, "the proposer found no candidate in the writer's corpus"
    d = {"confirmed": [{
        "claim": c["claim"],
        "grounds": "asserted in %d of the writer's own texts" % c["n_texts"],
        "confidence": 0.5,
        "would_change": "a text that denies it",
    } for c in cands]}
    path = tmp_path / "confirmed.json"
    path.write_text(json.dumps(d), encoding="utf-8")

    state = tmp_path / "state"
    shutil.copytree(os.path.join(REPO, "state"), str(state))
    old_state = W.STATE
    W.STATE = str(state)
    try:
        payload = W.run(decisions_path=str(path))
    finally:
        W.STATE = old_state

    grew = payload["register_after"] - payload["register_before"]
    assert payload["admitted"] == grew, (
        "the loop says it admitted %d opinions and the register grew by "
        "%d -- so a refusal was counted as an admission"
        % (payload["admitted"], grew))
    assert payload["refused"] == payload["candidates"] - payload["admitted"]


# ---------------------------------------------------------------------------
# 4. the artifact carries a digest of its own content
# ---------------------------------------------------------------------------

def test_the_digest_is_over_the_payload_without_the_digest_field():
    """**A DIGEST THAT DOES NOT MATCH ITS OWN ARTIFACT IS WORSE THAN
    NO DIGEST, BECAUSE IT SAYS 'THIS HAS BEEN TAMPERED WITH' ABOUT
    ITSELF.**"""
    payload = W.run(decisions_path=os.path.join(REPO, "state",
                                                 "nothing.json"))
    body = {k: v for k, v in payload.items() if k != "artifact_digest"}
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":"),
                           ensure_ascii=False)
    recomputed = "sha256:" + hashlib.sha256(
        canonical.encode("utf-8")).hexdigest()
    assert recomputed == payload["artifact_digest"]


def test_the_artifact_names_its_type():
    payload = W.run(decisions_path=os.path.join(REPO, "state",
                                                 "nothing.json"))
    assert payload["artifact_type"] == "writer-loop"


# ---------------------------------------------------------------------------
# 5. the dry run writes nothing
# ---------------------------------------------------------------------------

def test_the_dry_run_writes_nothing(tmp_path):
    """**A DRY RUN THAT WRITES IS NOT A DRY RUN.**"""
    path = os.path.join(REPO, "state", "opinion_register.jsonl")
    before = _event_count(path)
    import subprocess
    py = os.path.join(os.path.dirname(REPO), ".venv", "Scripts",
                      "python.exe")
    if not os.path.isfile(py):
        py = sys.executable
    proc = subprocess.run(
        [py, os.path.join(TOOLS, "writer_loop.py"), "--dry-run"],
        capture_output=True, text=True, cwd=REPO)
    assert proc.returncode == 0, proc.stderr[-500:]
    after = _event_count(path)
    assert before == after, "the dry run wrote into the register"


def _event_count(path: str) -> int:
    if not os.path.isfile(path):
        return 0
    with open(path, encoding="utf-8") as fh:
        return sum(1 for line in fh if line.strip())


def test_the_loop_runs_as_a_script():
    import subprocess
    py = os.path.join(os.path.dirname(REPO), ".venv", "Scripts",
                      "python.exe")
    if not os.path.isfile(py):
        py = sys.executable
    proc = subprocess.run(
        [py, os.path.join(TOOLS, "writer_loop.py"), "--json",
         "--decisions", os.path.join(REPO, "state", "nothing.json")],
        capture_output=True, text=True, cwd=REPO)
    assert proc.returncode == 0, proc.stderr[-500:]
    data = json.loads(proc.stdout)
    assert data["artifact_type"] == "writer-loop"
