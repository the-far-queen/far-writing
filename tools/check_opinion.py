#!/usr/bin/env python3
"""
check_opinion.py -- A HELD OPINION IS PERSISTED, A NEW TEXT IS MEASURED
AGAINST IT, A REVISION IS RECORDED WITH ITS REASON, AND THE WHOLE THING
CAN GO RED.

**AND WHY THIS FILE EXISTS, and it is the third thing of its kind in
this repo.** MEASURED 2026-11-06: `tools/viewpoint.py` measures a
viewpoint INSIDE one text, and `tools/check_self_aware.py` checks the
self-aware pass. Neither of them has a REGISTER -- neither of them has
anything that survives the end of the text it was measured in. And a
viewpoint inside one text is not a viewpoint: Bobby's words are *"to
have an opinion to speak to have an opinion"*, and the second half is
the hard half.

**AND THIS IS THE MUTATION-FIRST KIND**, the same shape as
`check_self_aware.py`: it builds two texts from the same material --
one that AGREES with a held opinion and one that CONTRADICTS it -- and
requires the measure to behave DIFFERENTLY on them. A check that only
runs on one text cannot tell a working instrument from one that
agrees with everything.

**AND THE MUTATIONS AT THE END ARE THE REAL TEST.** Four of them:

  M1  the opposition markers are removed -- and the contradiction
      detection must stop working, because the markers ARE the
      instrument.
  M2  the clause split is removed -- and the measure must go back to
      reading whole sentences, which is the defect the clause split
      was written to fix.
  M3  the revision stops requiring a reason -- and the check that
      refuses a reasonless revision must stop refusing.
  M4  the register stops recording the superseded version -- and the
      history must lose its depth, because a register that cannot show
      what it believed before is not a history.

**AND EACH MUTATION IS APPLIED TO A COPY, IN A TEMPORARY TREE, so the
working tree is never modified** -- the same discipline
`tools/mutation_check.py` uses.

**AND THE INTEREST MEASURE IS CHECKED HERE TOO**, because it is the
other half of Bobby's sentence and it is the same kind of claim: a
number with a null against it, and a mutation that must make it red.

Run:
    python tools/check_opinion.py
"""
from __future__ import annotations

import importlib.util
import json
import os
import shutil
import sys
import tempfile
from typing import Any, Dict, List, Optional

HERE = os.path.dirname(os.path.abspath(__file__))
FAR = os.path.dirname(HERE)
TOOLS = os.path.join(FAR, "tools")
if TOOLS not in sys.path:
    sys.path.insert(0, TOOLS)
REGISTER = os.path.join(FAR, "state", "opinion_register.jsonl")

#: THE TWO TEXTS. AND THEY DIFFER IN EXACTLY ONE THING: whether they
#: deny the claim. MEASURED: the first version of these had the
#: disagreement carried by a DIFFERENT sentence from the agreement, so
#: a text that agreed about people and then said something else about
#: the railway was scoring as a contradiction -- and a test text that
#: fails for a reason unrelated to what is being tested is a bad test
#: text. So both texts are about the same claim and the same subject,
#: and only the denial differs.
THE_AGREES = (
    "People are probably mostly kind, and the ones who are not are "
    "usually tired.\n"
)
THE_CONTRADICTS = (
    "People are never kind and they always lie about it.\n"
)

#: THE TEXT THE CLAUSE SPLIT IS FOR. One sentence, two clauses, and the
#: negation belongs to the FIRST one: "The train was never kind" is
#: about the train, and "people are mostly kind" is about the opinion.
#:
#: AND WITHOUT THE CLAUSE SPLIT THIS TEXT IS READ AS A CONTRADICTION,
#: because the whole sentence becomes one clause and the "never" ends
#: up next to the word "kind". MEASURED: this is what the clause split
#: is for, and it is the mutation that proves the split is load
#: bearing.
THE_SPLIT_TEXT = "The train was never kind and people are mostly kind.\n"

#: A TEXT THAT SAYS NOTHING ABOUT THE CLAIM. And it is here because a
#: measure with only two buckets is not a measure.
THE_NEITHER = (
    "The train left at nine. The platform was wet. He waited.\n"
)

#: THE OPINION THE TEXTS ARE MEASURED AGAINST. And it is a full
#: opinion -- position, subject, stance, grounds, date, confidence and
#: what would change it -- because a register that accepts a partial
#: opinion is a register that will hold half-formed beliefs.
THE_OPINION: Dict[str, Any] = {
    "key": "people_are_mostly_kind",
    "position": "people are mostly kind",
    "subject": "people",
    "stance": "probably",
    "grounds": "measured on the same street for three years",
    "held_on": "2026-11-06",
    "confidence": 0.6,
    "would_change": "a year of that street in which nobody was kind",
    "claim_terms": ["kind"],
}


def load(name: str = "opinion_probe", path: Optional[str] = None):
    """Load a module from a path, and REGISTER it before it runs.

    AND THE REGISTRATION IS NOT OPTIONAL. MEASURED: a module loaded by
    importlib without being put into sys.modules is None there, and
    `dataclasses` resolves a class's annotations through
    sys.modules[cls.__module__] -- so the probe went with "'NoneType'
    object has no attribute '__dict__'".
    """
    src = path or os.path.join(TOOLS, "opinion.py")
    spec = importlib.util.spec_from_file_location(name, src)
    if spec is None or spec.loader is None:
        raise SystemExit("the module could not be loaded: %s" % src)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def _fresh_register(mod, tmpdir: str):
    """A register on disk, in a temporary place, seeded with one opinion."""
    reg = mod.OpinionRegister(path=os.path.join(tmpdir, "register.jsonl"))
    reg.hold(mod.Opinion(**THE_OPINION))
    return reg


def main() -> int:
    print("=" * 74)
    print("A HELD OPINION PERSISTS, AND A NEW TEXT IS MEASURED AGAINST IT")
    print("=" * 74)
    print()

    failures: List[str] = []

    def check(label: str, cond: bool, extra: str = "") -> None:
        print("  [%s] %s%s" % ("ok " if cond else "FAIL", label,
                               (" -- " + extra) if extra else ""))
        if not cond:
            failures.append(label)

    tmpdir = tempfile.mkdtemp(prefix="opinion-check-")
    try:
        m = load()
        reg = _fresh_register(m, tmpdir)

        # -- THE REGISTER PERSISTS ------------------------------------
        print("   the register on disk:")
        for ev in reg.events:
            print("      seq=%d kind=%-8s key=%s" % (ev["seq"], ev["kind"],
                                                     ev["key"]))
        print()

        check("the opinion is held", "people_are_mostly_kind" in reg.held())
        check("and it survives a reload from disk",
              "people_are_mostly_kind"
              in m.OpinionRegister.load(reg.path).held())

        # -- THE THREE BUCKETS -----------------------------------------
        print("   the three texts:")
        for label, text in (("AGREES", THE_AGREES),
                            ("CONTRADICTS", THE_CONTRADICTS),
                            ("NEITHER", THE_NEITHER)):
            r = m.measure_text(text, reg)
            print("      %-12s agree=%d contradict=%d neither=%d"
                  % (label, r["agree"], r["contradict"], r["neither"]))
        print()

        agree = m.measure_text(THE_AGREES, reg)
        contra = m.measure_text(THE_CONTRADICTS, reg)
        neither = m.measure_text(THE_NEITHER, reg)

        check("a text that agrees is counted as agreeing",
              agree["agree"] == 1 and agree["contradict"] == 0, str(agree))
        check("and a text that contradicts is counted as contradicting",
              contra["contradict"] == 1 and contra["agree"] == 0, str(contra))
        check("and a text that says nothing about it is NEITHER",
              neither["neither"] == 1 and neither["agree"] == 0
              and neither["contradict"] == 0, str(neither))
        # AND THE WHOLE TRIPLE IS COMPARED, and not one number out of
        # it. MEASURED: the first version compared agree["agree"] with
        # contra["contradict"] with neither["neither"] -- and all three
        # are 1, so the set had one member and the check failed while
        # the measure was working perfectly. The texts ARE
        # distinguishable; the comparison was the thing that was wrong.
        triples = {
            (agree["agree"], agree["contradict"], agree["neither"]),
            (contra["agree"], contra["contradict"], contra["neither"]),
            (neither["agree"], neither["contradict"], neither["neither"]),
        }
        check("and the three are DISTINGUISHABLE by the measure",
              len(triples) == 3, str(sorted(triples)))

        # -- THE REVISION ----------------------------------------------
        print()
        try:
            reg.revise("people_are_mostly_kind", "people are mostly kind",
                       reason="")
            check("a revision with NO reason is refused", False,
                  "it was accepted")
        except ValueError as exc:
            check("a revision with NO reason is refused", True, str(exc))

        reg.revise("people_are_mostly_kind",
                   "people are mostly kind, and mostly tired too",
                   reason="the same street, two more years",
                   confidence=0.4,
                   claim_terms=("kind", "tired"))
        held = reg.held()["people_are_mostly_kind"]
        check("and the revision becomes the held opinion",
               "tired" in held.position, held.position)
        check("and the superseded version is still in the history",
               len(reg.history("people_are_mostly_kind")) == 2,
               str(len(reg.history("people_are_mostly_kind"))))
        check("and the reason is recorded with it",
               reg.history("people_are_mostly_kind")[1]["reason"]
               == "the same street, two more years",
               reg.history("people_are_mostly_kind")[1]["reason"])
        check("and the chain still verifies", not reg.verify(),
               str(reg.verify()))

        # -- THE VOICE CARRIES THE OPINION -----------------------------
        print()
        import voice as voice_mod
        axes = dict(voice_mod.VOICES["lean"])
        v_op = m.voice_from_register(axes, reg)
        v_no = voice_mod.get_voice("lean")
        check("the voice speaks from the held opinion",
               v_op.viewpoint_claim == held.position, v_op.viewpoint_claim)
        check("and the opinion is part of the voice_id",
               v_op.voice_id != v_no.voice_id,
               "%s then %s" % (v_no.voice_id, v_op.voice_id))
        w1 = m.writer_identity(v_op, reg)
        check("and the writer identity is a hash over the voice AND the "
              "register", len(w1) == 16, w1)

        # AND A REVISION CHANGES THE WRITER. MEASURED: the two levels
        # are not the same thing and the difference is measurable.
        reg2 = _fresh_register(m, tmpdir + "-2")
        v2 = m.voice_from_register(axes, reg2)
        w2 = m.writer_identity(v2, reg2)
        check("and a different opinion gives a different writer identity",
               w1 != w2, "%s then %s" % (w1, w2))

        # -- AND THE INTEREST MEASURE ----------------------------------
        print()
        i = load("interest_probe", os.path.join(TOOLS, "interest.py"))
        corpus = i.load_corpus()
        check("the interest corpus is the writer's own and is not empty",
               len(corpus) >= 4, "%d texts" % len(corpus))
        forms = i.surviving_forms(corpus)
        sets = i.concern_sets(corpus, forms)
        obs = i.cohesion(sets)
        nulls = i.null_cohesion(sets, trials=300)
        import statistics
        mu = statistics.mean(nulls)
        sd = statistics.pstdev(nulls)
        print("   the interest measure: observed %.4f, null %.4f +- %.4f, "
              "z=%+.2f" % (obs, mu, sd, (obs - mu) / sd if sd else 0))
        check("and the interest measure EXCEEDS its null",
              obs > mu, "%.4f then %.4f" % (obs, mu))
        check("and by more than noise",
              sd > 0 and (obs - mu) / sd > 1.0,
              "z=%.2f" % ((obs - mu) / sd if sd else 0))
        check("and the carriers are dropped, and the count is reported",
              sum(len(v) for v in i.carrier_forms(corpus).values()) > 0,
              "%d dropped"
              % sum(len(v) for v in i.carrier_forms(corpus).values()))
        sh = i.split_half(corpus, forms, index=i._form_doc_index(corpus),
                          trials=40)
        print("   the held-out split-half: observed %.4f, null %.4f, "
              "z=%+.2f" % (sh["observed"], sh["null_mean"], sh["z"]))
        check("and the held-out test holds up",
              sh["z"] > 1.0, "z=%.2f" % sh["z"])

        # -- AND THE MUTATIONS -----------------------------------------
        print()
        print("  AND THE MUTATIONS -- the check must go RED")
        print()

        work = tempfile.mkdtemp(prefix="opinion-mut-")
        try:
            mut_tools = os.path.join(work, "tools")
            os.makedirs(mut_tools)

            def fresh_tree() -> None:
                """Copy the three modules into the temporary tree.

                **AND EVERY MUTATION STARTS FROM A FRESH COPY, and the
                first version did not, and the check caught it.**
                MEASURED: M2 failed because M1's mutation of
                `viewpoint.py` -- the opposition markers removed -- was
                STILL IN THE TREE when M2 ran, so M2's text found no
                opposition markers at all and the clause split was
                never exercised. **A MUTATION THAT INHERITS THE
                PREVIOUS MUTATION IS NOT A MUTATION OF THE THING IT
                CLAIMS TO MUTATE**, and it fails in a way that looks
                like the thing being tested.
                """
                for name in ("opinion.py", "viewpoint.py", "voice.py"):
                    shutil.copy(os.path.join(TOOLS, name),
                                os.path.join(mut_tools, name))

            fresh_tree()

            def mutated(path: str, old: str, new: str) -> None:
                """Apply a mutation to the COPY, in the temporary tree."""
                with open(os.path.join(mut_tools, path), encoding="utf-8") as fh:
                    body = fh.read()
                if old not in body:
                    raise SystemExit("the mutation does not apply: %s"
                                     % old[:60])
                body = body.replace(old, new, 1)
                with open(os.path.join(mut_tools, path), "w",
                          encoding="utf-8") as fh:
                    fh.write(body)

            # -- M1: THE OPPOSITION MARKERS GO --------------------------
            fresh_tree()
            # AND THE MUTATION IS ON THE SHARED LIST, and not on the
            # regex. MEASURED 2026-11-06: the first version mutated
            # `OPPOSITION_RE` -- and the opinion register did not go
            # blind, because the register was reading its OWN list of
            # negations. **A MUTATION OF ONE COPY OF AN INSTRUMENT DOES
            # NOT MUTATE THE OTHER**, and the check passed while the
            # thing it was testing was untouched.
            mutated("viewpoint.py",
                    'OPPOSITION_MARKERS: Tuple[str, ...] = (\n'
                    '    "not", "never", "no longer", "isn\'t", "is not", '
                    '"aren\'t", "are not",\n'
                    '    "refuses", "refused", "rejects", "rejected",\n'
                    ')',
                    'OPPOSITION_MARKERS: Tuple[str, ...] = ()')
            # AND THE CACHED MODULES ARE DROPPED, and this is what made
            # the first version of M1 fail. MEASURED: `viewpoint` was
            # already in sys.modules -- the working probe at the top of
            # this file had imported it -- so the mutated copy in the
            # temporary tree was never loaded and the mutation had no
            # effect. **A MUTATION THAT IS NOT LOADED IS NOT A
            # MUTATION**, and it looks exactly like a working
            # instrument.
            for name in ("viewpoint", "voice"):
                sys.modules.pop(name, None)
            mm = load("opinion_mut1", os.path.join(mut_tools, "opinion.py"))
            reg_m = mm.OpinionRegister(path=os.path.join(work, "r1.jsonl"))
            reg_m.hold(mm.Opinion(**THE_OPINION))
            blind = mm.measure_text(THE_CONTRADICTS, reg_m)
            print("     M1  the opposition markers removed: the "
                  "contradicting text yields contradict=%d"
                  % blind["contradict"])
            check("M1 the contradiction detection goes BLIND",
                  blind["contradict"] == 0, str(blind["contradict"]))
            check("M1 and a blind measure is distinguishable from a "
                  "working one",
                  blind["contradict"] != contra["contradict"],
                  "%d then %d" % (contra["contradict"], blind["contradict"]))
            # AND THE WORKING MODULES ARE PUT BACK, so the rest of the
            # check runs against the real ones.
            for name in ("viewpoint", "voice"):
                sys.modules.pop(name, None)

            # -- M2: THE CLAUSE SPLIT GOES ------------------------------
            fresh_tree()
            mutated("opinion.py",
                    '_CLAUSE_SPLIT = re.compile(\n'
                    '    r"\\s*(?:[;:,]|--|\\b(?:and|but|so|because|though|'
                    'although|while)\\b)\\s*",\n'
                    '    re.IGNORECASE)',
                    '_CLAUSE_SPLIT = re.compile(r"\\s*\\Z")')
            for name in ("viewpoint", "voice"):
                sys.modules.pop(name, None)
            mm = load("opinion_mut2", os.path.join(mut_tools, "opinion.py"))
            reg_m = mm.OpinionRegister(path=os.path.join(work, "r2.jsonl"))
            reg_m.hold(mm.Opinion(**THE_OPINION))
            # AND THE TEXT IS ONE WHERE THE CLAUSE SPLIT IS THE WHOLE
            # DIFFERENCE. MEASURED: the first version of this mutation
            # used "People are probably mostly kind, and the ones who
            # are not are usually tired" -- and the adjacency rule now
            # handles that one on its own, so removing the clause split
            # changed nothing and the mutation went GREEN. **A MUTATION
            # THAT DOES NOT CHANGE THE ANSWER IS NOT A MUTATION.**
            #
            # So the text is one where the negation belongs to ANOTHER
            # clause: "The train was never kind and people are mostly
            # kind" -- one sentence, two clauses, and the "never"
            # belongs to the train.
            merged = mm.measure_text(THE_SPLIT_TEXT, reg_m)
            print("     M2  the clause split removed: %r yields "
                  "contradict=%d agree=%d"
                  % (THE_SPLIT_TEXT[:44], merged["contradict"],
                     merged["agree"]))
            check("M2 the measure misreads the other clause's negation",
                  merged["contradict"] == 1,
                  "the clause split is what makes this %d"
                  % merged["contradict"])
            working = m.measure_text(THE_SPLIT_TEXT, reg)
            check("M2 and the working measure reads it as agreement",
                  working["agree"] == 1 and working["contradict"] == 0,
                  str(working))

            # -- M3: THE REVISION STOPS ASKING FOR A REASON -------------
            fresh_tree()
            mutated("opinion.py",
                    '        if not reason.strip():\n'
                    '            raise ValueError(\n'
                    '                "a revision of %r with no reason is a '
                    'replacement, not a "\n'
                    '                "revision" % key)',
                    '        if False:\n'
                    '            raise ValueError("unreachable")')
            for name in ("viewpoint", "voice"):
                sys.modules.pop(name, None)
            mm = load("opinion_mut3", os.path.join(mut_tools, "opinion.py"))
            reg_m = mm.OpinionRegister(path=os.path.join(work, "r3.jsonl"))
            reg_m.hold(mm.Opinion(**THE_OPINION))
            accepted = False
            try:
                reg_m.revise("people_are_mostly_kind", "people are cruel",
                             reason="", claim_terms=("cruel",))
                accepted = True
            except ValueError:
                accepted = False
            print("     M3  the reason requirement removed: a reasonless "
                  "revision was %s"
                  % ("ACCEPTED" if accepted else "refused"))
            check("M3 the reasonless revision is ACCEPTED",
                  accepted, "the refusal is what the check tests")
            # AND THE COMPARISON IS WITH THE WORKING REGISTER, and it
            # is a real comparison. MEASURED: the first version of
            # this check was `accepted is not True or True`, which is
            # true whatever the answer is -- a check that cannot fail
            # written in the shape of one that can.
            working_refused = False
            try:
                reg.revise("people_are_mostly_kind", "people are cruel",
                           reason="", claim_terms=("cruel",))
            except ValueError:
                working_refused = True
            check("M3 and the working register refuses what the mutant "
                  "accepts",
                  working_refused and accepted,
                  "working refused=%s, mutant accepted=%s"
                  % (working_refused, accepted))

            # -- M4: THE HISTORY STOPS BEING KEPT ----------------------
            fresh_tree()
            mutated("opinion.py",
                    '        self._append_event("revised", revised, reason)',
                    '        self.events = [e for e in self.events\n'
                    '                         if e.get("key") != key]\n'
                    '        self._append_event("revised", revised, reason)')
            for name in ("viewpoint", "voice"):
                sys.modules.pop(name, None)
            mm = load("opinion_mut4", os.path.join(mut_tools, "opinion.py"))
            reg_m = mm.OpinionRegister(path=os.path.join(work, "r4.jsonl"))
            reg_m.hold(mm.Opinion(**THE_OPINION))
            reg_m.revise("people_are_mostly_kind", "people are cruel",
                         reason="a reason", claim_terms=("cruel",))
            depth = len(reg_m.history("people_are_mostly_kind"))
            print("     M4  the history dropped: depth=%d instead of 2"
                  % depth)
            check("M4 the history loses its depth",
                  depth < 2, "depth=%d" % depth)
            check("M4 and that is distinguishable from the working "
                  "register",
                  depth != len(reg.history("people_are_mostly_kind")),
                  "%d then %d" % (len(reg.history("people_are_mostly_kind")),
                                  depth))
        finally:
            shutil.rmtree(work, ignore_errors=True)

        # -- AND THE MODULE'S OWN SELFTESTS ----------------------------
        print()
        print("  AND THE MODULES' OWN SELFTESTS")
        print()
        rc = m._selftest()
        check("and the opinion module's selftest passes", rc == 0, "rc %s" % rc)
        rc = i._selftest()
        check("and the interest module's selftest passes", rc == 0,
              "rc %s" % rc)

    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

    print()
    print("=" * 74)
    print("  %s" % ("PASSED" if not failures else "FAILED"))
    for f in failures:
        print("    FAILED: %s" % f)
    print("=" * 74)
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
