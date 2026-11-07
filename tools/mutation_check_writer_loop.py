#!/usr/bin/env python3
"""
tools/mutation_check_writer_loop.py -- prove the WRITER'S LOOP's
checks can go red.

A test that cannot fail is not a test. This script applies a set of
MUTATIONS to `tools/writer_loop.py` and `tools/propose_opinions.py`,
runs the writer-loop test files after each one, and requires every
mutation to turn the suite RED. A mutation that stays green means the
suite cannot see that defect, and it is reported as a FAILURE of the
suite, not a pass.

WHY THIS FILE EXISTS. Queue item 48 asks for a loop and says the
check must be able to go red: "a candidate that carries no grounds is
refused, and a register whose digest chain does not verify is
refused". The loop's own tests cover the behaviour -- but a test that
has never been shown to go red is a test that might not be testing
what it claims. So the mutations here put each mechanism back the way
it was and require the suite to notice.

THE MUTATIONS ARE THE THREE CLAIMS THE LOOP MAKES:

1. THE LOOP NEVER WRITES ITS OWN DECISIONS. A loop that writes its
   own opinions grades its own homework, so the decision file is an
   INPUT and never an output.
2. A PARTIAL DECISION IS REFUSED BY NAME. A decision carrying a
   claim and a grounds but no confidence and no falsifier must be
   refused where the mistake is -- not at the far end, where the
   register refuses it.
3. THE PROPOSER NEVER HOLDS AN OPINION. The proposer proposes; the
   loop admits. A proposer that held what it found would be an
   addition, not a proposal.

And one that matters for the whole repo:

4. THE REGISTER'S REFUSAL IS THE REGISTER'S. If the loop caught a
   grounds-less opinion itself, the rule could be edited into
   accepting one -- so the register must still refuse it.

Each mutation is applied to a COPY, in a temporary tree, and the
suite is run there -- so the working tree is never modified.

Run:  python tools/mutation_check_writer_loop.py
Exit: 0 if the baseline was green and every mutation went red.
"""
from __future__ import annotations

import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)

#: THE FILES THE SUITE RUNS. The two writer-loop test files.
TEST_FILES = ("tests/test_writer_loop.py", "tests/test_propose_opinions.py")

#: THE MUTATIONS. Each is (label, file, old, new).
MUTATIONS = [
    # 1. THE LOOP WRITES ITS OWN DECISIONS.
    #
    # AND THE MUTATION IS ON THE DECISION WRITE, not on the read --
    # because a loop that READS its decisions is fine, and a loop that
    # WRITES them has graded its own homework.
    ("the loop writes its own decisions",
     "tools/writer_loop.py",
     '        decision = decisions.get(key)\n'
     '        if decision is None:\n'
     '            refused.append("no decision for %r" % cand["claim"][:60])\n'
     '            continue',
     '        decision = decisions.get(key)\n'
     '        if decision is None:\n'
     '            decision = {"grounds": "the loop decided this",\n'
     '                        "confidence": 0.9,\n'
     '                        "would_change": "nothing"}'),

    # 2. A PARTIAL DECISION IS ACCEPTED.
    #
    # AND THE MUTATION REMOVES THE REFUSAL ITSELF, so a decision with
    # no confidence and no falsifier is admitted -- and the register's
    # own validate() then refuses it at the far end, where the reason
    # is a long way from the mistake.
    ("a partial decision is admitted",
     "tools/writer_loop.py",
     '        if missing:\n'
     '            refused.append("a decision for %r has no %s"\n'
     '                           % (str(row.get("claim", ""))[:48],\n'
     '                              ", ".join(missing)))\n'
     '            continue',
     '        if missing:\n'
     '            continue'),

    # 2b. AND THE REFUSAL IS NOT NAMED -- the reason is dropped, so
    # the refusal exists but says nothing.
    ("a partial decision is refused without a reason",
     "tools/writer_loop.py",
     '            refused.append("a decision for %r has no %s"\n'
     '                           % (str(row.get("claim", ""))[:48],\n'
     '                              ", ".join(missing)))',
     '            refused.append("a decision is incomplete")'),

    # 3. THE PROPOSER HOLDS WHAT IT FINDS.
    #
    # AND THE MUTATION IS ON THE PROPOSER, because the claim "the
    # proposer proposes and never admits" is a claim about the
    # proposer. If the proposer held what it found, the register would
    # grow on every read and the loop would be writing its own
    # homework twice.
    ("the proposer holds what it finds",
     "tools/propose_opinions.py",
     '    out.sort(key=lambda r: (-r["n_texts"], -r["occurrences"], r["claim"]))\n'
     '    return out',
     '    out.sort(key=lambda r: (-r["n_texts"], -r["occurrences"], r["claim"]))\n'
     '    _reg = O.OpinionRegister.load(REGISTER) if os.path.isfile(REGISTER) \\\n'
     '        else O.OpinionRegister(path=REGISTER)\n'
     '    for _c in out[:1]:\n'
     '        try:\n'
     '            _reg.hold(O.Opinion(\n'
     '                key="the_proposer_wrote_this",\n'
     '                position=_c["claim"], subject=_c["subject"],\n'
     '                stance=_c["stance"], grounds="the proposer decided",\n'
     '                held_on="2026-11-07", confidence=0.5,\n'
     '                would_change="nothing"), reason="written by the proposer")\n'
     '        except Exception:\n'
     '            pass\n'
     '    return out'),

    # 4. THE REGISTER'S REFUSAL IS COUNTED AS AN ADMISSION.
    #
    # AND THE FIRST VERSION OF THIS MUTATION WAS TOO WEAK, and it is
    # worth saying why. It filled the grounds in with `or "filled in
    # by the loop"` -- but `load_decisions` ALREADY refuses a decision
    # with no grounds, before the admit path is reached, so the
    # mutation changed a line that cannot run on the input it was
    # aimed at. The suite stayed green and the mutation was reporting
    # on nothing.
    #
    # **A MUTATION THAT DOES NOT CHANGE THE ANSWER IS NOT A
    # MUTATION.** So this one removes the mechanism the loop's claim
    # rests on: the refusal is counted as an ADMISSION. The loop
    # then claims to have held an opinion the register refused, and
    # the check that catches it is the one that ties the loop's own
    # count to the REGISTER'S count.
    ("the loop counts the register's refusal as an admission",
     "tools/writer_loop.py",
     '        except Exception as exc:                        # noqa: BLE001\n'
     '            refused.append("the register refused %r: %s"\n'
     '                           % (cand["claim"][:48], exc))',
     '        except Exception as exc:                        # noqa: BLE001\n'
     '            admitted.append(opinion.key)'),
]


def run_suite(tree: str) -> tuple:
    env = dict(os.environ)
    env["PYTHONPATH"] = os.path.join(tree, "tools")
    p = subprocess.run(
        [sys.executable, "-m", "pytest", *TEST_FILES,
         "-q", "--no-header", "--tb=no", "-p", "no:cacheprovider"],
        cwd=tree, capture_output=True, text=True, env=env, timeout=600)
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def main() -> int:
    print("=" * 74)
    print("THE WRITER'S LOOP -- THE MUTATION CHECK")
    print("=" * 74)
    print("  each mutation puts one of the loop's claims back the way it")
    print("  was, and the suite MUST go RED. a mutation that stays green")
    print("  means the check does not test what it claims.")
    print()

    work = tempfile.mkdtemp(prefix="writerloop-mut-")
    base = os.path.join(work, "base")
    try:
        # THE TREE IS A COPY of the tools and the tests, so the working
        # tree is never modified.
        for sub in ("tools", "tests"):
            os.makedirs(os.path.join(base, sub), exist_ok=True)
        for name in ("writer_loop.py", "propose_opinions.py", "opinion.py",
                     "viewpoint.py", "voice.py"):
            src = os.path.join(REPO, "tools", name)
            if os.path.isfile(src):
                shutil.copy2(src, os.path.join(base, "tools", name))
        for name in TEST_FILES:
            shutil.copy2(os.path.join(REPO, name), os.path.join(base, name))
        # THE REGISTER AND THE CORPUS, because the loop reads both.
        os.makedirs(os.path.join(base, "state"), exist_ok=True)
        src = os.path.join(REPO, "state", "opinion_register.jsonl")
        if os.path.isfile(src):
            shutil.copy2(src, os.path.join(base, "state",
                                           "opinion_register.jsonl"))
        if os.path.isdir(os.path.join(REPO, "stories")):
            shutil.copytree(os.path.join(REPO, "stories"),
                            os.path.join(base, "stories"))

        print("BASELINE  pytest %s" % " ".join(TEST_FILES))
        rc, out = run_suite(base)
        print("  exit=%d  %s" % (rc, "GREEN" if rc == 0 else "RED"))
        if rc != 0:
            print("  the baseline is not green; every mutation below would "
                  "be meaningless")
            print(out[-3000:])
            return 1
        print()

        red = 0
        green = 0
        failures = []

        for label, rel, old, new in MUTATIONS:
            path = os.path.join(base, rel)
            with open(path, encoding="utf-8") as fh:
                original = fh.read()
            if old not in original:
                print("  SKIP  %-52s the pattern is gone" % label)
                failures.append((label, "pattern not found"))
                continue
            with open(path, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(original.replace(old, new, 1))
            rc, out = run_suite(base)
            with open(path, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(original)
            if rc != 0:
                red += 1
                tail = [l for l in out.splitlines()
                        if l.startswith("FAILED") or "failed" in l.lower()]
                print("  RED   %-52s %s" % (label, tail[0][:36] if tail else ""))
            else:
                green += 1
                print("  GREEN %-52s <- THE CHECK CANNOT FAIL" % label)
                failures.append((label, "stayed green"))

        print()
        print("  mutations that went RED: %d" % red)
        print("  mutations that stayed GREEN: %d" % green)
        if green:
            print("  A GREEN MUTATION MEANS THE CHECK DOES NOT HOLD.")
            for label, why in failures:
                print("    %s -- %s" % (label, why))
            return 1
        print("  every mutation went RED: the checks hold.")
        return 0
    finally:
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
