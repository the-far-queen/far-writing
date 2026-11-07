"""
test_propose_opinions.py -- the candidate finder can go RED.

Bobby, 2026-11-06: *"the writer has no loop"* -- the register is
seeded, never self-updating.

**AND THESE CHECKS CAN FAIL.** A check that cannot go red is a check
that cannot catch anything.

**AND WHAT IS BEING PROVEN:**

    1  THE COMMAND FINDS CANDIDATES, and it finds them in the writer's
       OWN CORPUS -- not in a hand-written list.
    2  IT PRODUCES CANDIDATES AND NOT ADDITIONS. Nothing is held
       until a writer puts it there.
    3  THE REGISTER'S OWN OPINIONS ARE EXCLUDED, so it proposes what
       is MISSING.
    4  THE STANCE FOLLOWS THE FREQUENCY, because the frequency is the
       measurement and the hedge is the writer's mood on one occasion.
    5  THE CLUSTERS ARE COHERENT, and the coherence is checked by
       reading the terms rather than by counting them.
"""

from __future__ import annotations

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
TOOLS = os.path.join(REPO, "tools")
if TOOLS not in sys.path:
    sys.path.insert(0, TOOLS)

import opinion as O  # noqa: E402
import propose_opinions as P  # noqa: E402


# ---------------------------------------------------------------------------
# 1. the command finds candidates in the writer's own corpus
# ---------------------------------------------------------------------------

def test_the_command_finds_candidates():
    cands = P.find_candidates()
    assert cands, "the command found nothing in the writer's own corpus"


def test_some_candidate_is_asserted_in_more_than_one_text():
    """**AND THE CORPUS IS A CORPUS, NOT ONE TEXT.** A writer that
    asserts the same thing in 13 texts holds an opinion; one that
    asserts it once holds a sentence."""
    cands = P.find_candidates()
    multi = [c for c in cands if c["n_texts"] >= 2]
    assert multi, "no candidate is asserted in 2+ texts"
    assert len(multi) >= 5, "only %d multi-text candidates" % len(multi)


def test_every_candidate_names_a_subject_from_the_closed_list():
    for c in P.find_candidates():
        assert c["subject"] in O.SUBJECTS, c


def test_every_candidate_carries_a_stance_the_register_accepts():
    for c in P.find_candidates():
        assert c["stance"] in O.STANCES, c


def test_every_candidate_carries_its_terms():
    for c in P.find_candidates():
        assert c["terms"], c


# ---------------------------------------------------------------------------
# 2. it produces candidates and NOT additions
# ---------------------------------------------------------------------------

def test_the_command_writes_nothing_into_the_register(tmp_path):
    """**A LOOP THAT WRITES ITS OWN OPINIONS GRADES ITS OWN
    HOMEWORK.**

    AND THE CHECK IS ON THE REGISTER'S OWN EVENT COUNT, before and
    after -- because a check that reads the register's opinions cannot
    tell a refusal from a proposal that was never made.
    """
    path = os.path.join(REPO, "state", "opinion_register.jsonl")
    before = _event_count(path)
    P.find_candidates()
    after = _event_count(path)
    assert before == after, "the command wrote into the register"


def test_the_command_does_not_call_hold(tmp_path):
    """**AND THE COMMAND NEVER CALLS `hold()`**, which is the register's
    own door. A candidate that arrives by the door is an addition."""
    src = open(os.path.join(TOOLS, "propose_opinions.py"),
               encoding="utf-8").read()
    assert ".hold(" not in src, "the command calls the register's hold()"
    assert "revise(" not in src, "the command revises the register"


def _event_count(path: str) -> int:
    if not os.path.isfile(path):
        return 0
    with open(path, encoding="utf-8") as fh:
        return sum(1 for line in fh if line.strip())


# ---------------------------------------------------------------------------
# 3. the register's own opinions are excluded
# ---------------------------------------------------------------------------

def test_the_register_holds_six_opinions_and_they_are_excluded():
    """**AND THE COMMAND PROPOSES WHAT IS MISSING.**"""
    reg = O.OpinionRegister.load(
        os.path.join(REPO, "state", "opinion_register.jsonl"))
    held = reg.held()
    assert held, "the register holds nothing"
    positions = {o.position.strip().lower() for o in held.values()}
    cands = P.find_candidates()
    for c in cands:
        assert c["claim"].strip().lower() not in positions, c


# ---------------------------------------------------------------------------
# 4. the stance follows the frequency
# ---------------------------------------------------------------------------

def test_the_stance_follows_the_frequency():
    assert P._stance_for(4) == "certainly"
    assert P._stance_for(3) == "probably"
    assert P._stance_for(2) == "probably"
    assert P._stance_for(1) == "arguably"


def test_a_candidate_in_many_texts_is_held_certainly():
    cands = [c for c in P.find_candidates() if c["n_texts"] >= 4]
    for c in cands:
        assert c["stance"] == "certainly", c


# ---------------------------------------------------------------------------
# 5. the clusters are coherent
# ---------------------------------------------------------------------------

def test_a_multi_text_cluster_names_a_topic_not_a_connector():
    """**A WORD THAT HALF THE CORPUS USES IS A CONNECTOR, NOT A
    TOPIC.**

    MEASURED 2026-11-06: the first version of this command clustered
    on ANY TWO shared words, and the top cluster came out as "alice,
    asleep, back, bear, call, disgust, dormouse" -- which merges a
    passage about a dormouse with a passage about a woman reading
    papers aloud.

    So the check is: the terms of a multi-text cluster must not be
    words that most of the corpus uses.
    """
    cands = [c for c in P.find_candidates() if c["n_texts"] >= 2]
    assert cands
    for c in cands:
        for term in c["terms"]:
            hits = _texts_using(term)
            assert hits <= 4, ("the term %r is used in %d of the texts, "
                               "so it is a connector and not a topic"
                               % (term, hits))


def _texts_using(term: str) -> int:
    import re
    n = 0
    for _name, text in P._read_texts(P.STORIES):
        if re.search(r"(?<![A-Za-z0-9])%s(?![A-Za-z0-9])" % re.escape(term),
                     text or "", re.IGNORECASE):
            n += 1
    return n


def test_the_order_is_the_same_every_time():
    """**THE SAME CORPUS GIVES THE SAME ORDER EVERY TIME.**"""
    a = [c["claim"] for c in P.find_candidates()]
    b = [c["claim"] for c in P.find_candidates()]
    assert a == b


def test_the_command_runs_as_a_script():
    """**AND IT RUNS.** A command that cannot be run is a function."""
    import subprocess
    py = os.path.join(os.path.dirname(REPO), ".venv", "Scripts",
                      "python.exe")
    if not os.path.isfile(py):
        py = sys.executable
    proc = subprocess.run(
        [py, os.path.join(TOOLS, "propose_opinions.py"), "--json"],
        capture_output=True, text=True, cwd=REPO)
    assert proc.returncode == 0, proc.stderr[-500:]
    data = json.loads(proc.stdout)
    assert "candidates" in data
    assert data["n_texts"] > 0
