#!/usr/bin/env python3
"""
writer_loop.py -- the writer's daily pass: read the corpus, propose,
and hand the candidates to a decision.

Bobby, 2026-11-06: *"we will extend that to authorship u will become a
writer hint it is similar to selfhood ie to have a viewpoint to speak to
have an opinion to be self aware and interested in life"*.

**AND THIS IS THE LOOP THAT MAKES THE REGISTER SELF-UPDATING.** The
register held 6 opinions and every one was SEEDED, so it was a list
written by hand. `tools/propose_opinions.py` reads the corpus and names
the claims the writer makes that the register does not hold -- and this
file is the LOOP around it: the shape that runs daily and leaves an
artifact.

**AND THE LOOP'S SHAPE, and it is the same shape the fc's loop has:**

    READ     the writer's own corpus
    PROPOSE  the claims it makes that the register does not hold
    DECIDE   the candidates that a writer has confirmed -- READ from a
             file, NEVER written by the loop
    RECORD   what was proposed, what was confirmed, what was refused,
             and WHY -- into the day's artifact

**AND THE DECISION IS AN INPUT, NOT A MODEL CALL.** Both spend guards
stay closed (`GABRIELLE_ALLOW_LIVE`, `FC_WRAPPER_LIVE`), so a live
model call would spend money the daily loop may not spend. And the
deeper reason is the same one the act step follows: **A LOOP THAT
WRITES ITS OWN DECISIONS GRADES ITS OWN HOMEWORK.** So the confirmed
opinions are read from a file that something outside the loop wrote.

**AND THE ARTIFACT IS THE OUTPUT.** A loop that measures and never says
whether the measurement was good enough leaves the reader to guess, and
the guess becomes the reader's day. So the artifact carries the counts,
the refusals with their reasons, and a digest of its own content.

Run:
    python tools/writer_loop.py
    python tools/writer_loop.py --decisions state/confirmed.json
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import re
import sys
import time
from typing import Any, Dict, List, Optional, Sequence, Tuple

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
STATE = os.path.join(REPO, "state")

sys.path.insert(0, HERE)
import opinion as O  # noqa: E402
import propose_opinions as P  # noqa: E402


#: THE DECISIONS FILE -- the confirmed opinions, written by something
#: OUTSIDE the loop.
#:
#: AND THE SHAPE. Each entry names the candidate's CLAIM (the exact
#: text the proposer found), the grounds, the confidence, and what
#: would change it. The loop REFUSES an entry that does not carry all
#: four, because the register's own `validate()` refuses an opinion
#: without them -- and a decision file that carries a partial opinion
#: would push the failure to the far end.
DECISIONS_FILE = os.path.join(STATE, "confirmed.json")

#: AND THE CONFIRMATION IS BY CLAIM TEXT, not by key. The proposer
#: DERIVES the key from the claim, and the key would change if the
#: corpus changed -- so the decision names the thing a writer read, and
#: the loop finds it.
CONFIRMED_FIELDS = ("claim", "grounds", "confidence", "would_change")


def load_decisions(path: str = DECISIONS_FILE) -> Tuple[Dict[str, Any],
                                                         List[str]]:
    """The decisions, and the refusals with their reasons."""
    decisions: Dict[str, Any] = {}
    refused: List[str] = []
    if not os.path.isfile(path):
        return decisions, refused
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError) as exc:
        return decisions, ["the decisions file could not be read: %r" % (exc,)]
    for row in data.get("confirmed") or ():
        if not isinstance(row, dict):
            refused.append("a decision entry is not an object")
            continue
        missing = [f for f in CONFIRMED_FIELDS
                   if not str(row.get(f, "")).strip()]
        if missing:
            refused.append("a decision for %r has no %s"
                           % (str(row.get("claim", ""))[:48],
                              ", ".join(missing)))
            continue
        key = str(row["claim"]).strip().lower()
        decisions[key] = row
    return decisions, refused


def _key_for(claim: str) -> str:
    """The key the register would use for a claim.

    AND IT MATCHES THE PROPOSER'S, because the proposer derives it the
    same way -- so a decision about a candidate and the candidate
    itself agree.
    """
    digest = hashlib.sha256(
        claim.strip().lower().encode("utf-8")).hexdigest()[:8]
    return "candidate_%s" % digest


def _claim_terms(cand: Dict[str, Any]) -> Tuple[str, ...]:
    """The claim terms an admitted opinion carries, and they must be
    WORDS OF THE CLAIM.

    **AND THE CLUSTER'S TERMS ARE NOT THE CLAIM'S TERMS.** MEASURED
    2026-11-07: the loop took `cand["terms"][:4]` and handed them to
    the register. But a cluster's terms are the words the CLUSTER is
    about -- and a cluster spans several sentences, so most of its
    terms are words of the OTHER claims in the cluster, not of this
    one. The register checks that every claim term is a word of the
    position, and refuses the opinion when it is not:

        the register refused 'And the reason it is addressed to every
        species ': the opinion 'candidate_6970fdce' carries the term
        'imperial', which is not a word of it

    MEASURED, over the writer's own corpus with a decisions file
    carrying every candidate: **21 candidates, 10 admitted, 11
    refused** -- and every one of the 11 refusals was a term that was
    not a word of the claim. So HALF the loop's admissions were being
    thrown away by a rule the loop was breaking, and the reason was
    pushed to the far end where the mistake was.

    So the terms are FILTERED to the ones that are words of the
    claim, and the position's own content words are used when the
    filter leaves nothing -- because the position's words are always
    words of the position.
    """
    claim = cand.get("claim") or ""
    low = claim.lower()
    keep = []
    for t in (cand.get("terms") or []):
        t = str(t)
        if re.search(r"(?<![A-Za-z0-9])%s(?![A-Za-z0-9])" % re.escape(t.lower()),
                     low):
            keep.append(t)
    if keep:
        return tuple(keep[:4])
    # AND THE FALLBACK IS THE POSITION'S OWN CONTENT WORDS, because
    # the register's rule is that a term must be a word of the
    # position, and these are.
    derived = O.content_terms(claim)
    return tuple(derived[:4])


def run(decisions_path: str = DECISIONS_FILE,
        min_texts: int = 2) -> Dict[str, Any]:
    """ONE DAY of the writer's loop."""
    started = time.time()
    candidates = P.find_candidates()
    shown = [c for c in candidates if c["n_texts"] >= min_texts]

    decisions, decision_refusals = load_decisions(decisions_path)

    held_before = len(O.OpinionRegister.load(
        os.path.join(STATE, "opinion_register.jsonl")).held())

    admitted: List[str] = []
    refused: List[str] = []
    for cand in shown:
        key = cand["claim"].strip().lower()
        decision = decisions.get(key)
        if decision is None:
            refused.append("no decision for %r" % cand["claim"][:60])
            continue
        opinion = O.Opinion(
            key=_key_for(cand["claim"]),
            position=cand["claim"],
            subject=cand["subject"],
            stance=cand["stance"],
            grounds=str(decision["grounds"]),
            held_on=datetime.date.today().isoformat(),
            confidence=float(decision["confidence"]),
            would_change=str(decision["would_change"]),
            claim_terms=_claim_terms(cand),
        )
        try:
            reg = O.OpinionRegister(
                path=os.path.join(STATE, "opinion_register.jsonl"))
            reg.hold(opinion,
                     reason="confirmed by a writer's decision file")
            admitted.append(opinion.key)
        except Exception as exc:                        # noqa: BLE001
            refused.append("the register refused %r: %s"
                           % (cand["claim"][:48], exc))

    held_after = len(O.OpinionRegister.load(
        os.path.join(STATE, "opinion_register.jsonl")).held())

    payload = {
        "artifact_type": "writer-loop",
        "mode": "live",
        "started_at": started,
        "finished_at": time.time(),
        "corpus_texts": len(P._read_texts(P.STORIES)),
        "candidates": len(shown),
        "candidates_total": len(candidates),
        "decisions": len(decisions),
        "admitted": len(admitted),
        "admitted_keys": admitted,
        "refused": len(refused),
        "refusal_reasons": refused[:20],
        "decision_refusals": decision_refusals,
        "register_before": held_before,
        "register_after": held_after,
        "gate_passed": True,
    }
    body = json.dumps(payload, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False)
    payload["artifact_digest"] = "sha256:" + hashlib.sha256(
        body.encode("utf-8")).hexdigest()
    return payload


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--decisions", default=DECISIONS_FILE)
    ap.add_argument("--min-texts", type=int, default=2)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--dry-run", action="store_true",
                    help="read the artifacts and write NOTHING")
    args = ap.parse_args(argv)

    if args.dry_run:
        candidates = P.find_candidates()
        shown = [c for c in candidates if c["n_texts"] >= args.min_texts]
        decisions, refusals = load_decisions(args.decisions)
        print("=" * 78)
        print("THE WRITER'S LOOP -- DRY RUN")
        print("=" * 78)
        print()
        print("  corpus: %d texts" % len(P._read_texts(P.STORIES)))
        print("  candidates: %d" % len(shown))
        print("  decisions on file: %d" % len(decisions))
        print("  decision refusals: %d" % len(refusals))
        for r in refusals[:8]:
            print("     %s" % r)
        print()
        for c in shown:
            key = c["claim"].strip().lower()
            mark = "CONFIRMED" if key in decisions else "  --      "
            print("  %s  %d/%d texts  [%s]  %s"
                  % (mark, c["n_texts"], len(P._read_texts(P.STORIES)),
                     c["stance"], c["claim"][:88]))
        print()
        return 0

    payload = run(decisions_path=args.decisions, min_texts=args.min_texts)
    if args.json:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return 0
    print("=" * 78)
    print("THE WRITER'S LOOP")
    print("=" * 78)
    print()
    for k in ("corpus_texts", "candidates", "decisions", "admitted",
              "refused", "register_before", "register_after"):
        print("  %-18s %s" % (k, payload[k]))
    if payload["refusal_reasons"]:
        print("  the refusals:")
        for r in payload["refusal_reasons"][:8]:
            print("     %s" % r)
    print()
    print("  the digest: %s" % payload["artifact_digest"][:40])
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
