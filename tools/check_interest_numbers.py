#!/usr/bin/env python3
"""
check_interest_numbers.py -- the interest numbers are the TOOL'S
OUTPUT, and a published number is a measurement.

Bobby, 2026-11-06.

**WHY THIS FILE EXISTS.** MEASURED 2026-11-06: the commit message for
`far-writing 93d98f3` published a null of 0.2640 +- 0.0214, a z of
+6.31, a held-out z of +3.66 and a threshold sweep of 1.84..12.82.

**NONE OF THOSE ARE THE TOOL'S OUTPUT.** The tool prints a null of
0.2623 +- 0.0209, a z of +6.55, a held-out z of +3.39 and a sweep of
1.97..12.53. The figures came from a subagent's INTERMEDIATE report
rather than from a run of the command.

**AND THAT IS THE SAME DEFECT THE REGISTER'S OWN DOCSTRING WAS
REWRITTEN FOR ON 2026-11-05** -- the docstring claimed "450 words" and
the register held 306 -- EXCEPT THAT THE REGISTER AT LEAST SAID THE
WRONG NUMBER IN THE PLACE WHERE THE READER WOULD CHECK IT. A commit
message says a number where nobody checks.

**SO THE NUMBERS ARE NOW CHECKED AGAINST THE TOOL.** This file runs
the measure and compares it to the figures that are PUBLISHED -- the
ones in `tools/interest.py`'s own docs and the ones the vault carries.

**AND A NUMBER IN A COMMIT MESSAGE IS A MEASUREMENT, AND A
MEASUREMENT IS SOMETHING YOU RAN.**

Run:
    python tools/check_interest_numbers.py
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from typing import Dict, List, Tuple

HERE = os.path.dirname(os.path.abspath(__file__))
FAR = os.path.dirname(HERE)
WORK_REPOS = os.path.dirname(FAR)


def _python() -> str:
    venv = os.path.join(WORK_REPOS, ".venv", "Scripts", "python.exe")
    if os.path.isfile(venv):
        return venv
    return sys.executable


#: THE PUBLISHED NUMBERS, and the tool's output is compared to them.
#:
#: AND THEY ARE HERE, IN A CHECK, RATHER THAN ONLY IN A COMMIT
#: MESSAGE. A number that lives only in prose is a number nobody can
#: check, and a number that lives only in a commit message is a number
#: that will drift.
PUBLISHED: Dict[str, object] = {
    "cohesion_observed": 0.3991,
    "cohesion_null": 0.2623,
    "cohesion_null_sd": 0.0209,
    "cohesion_z": 6.55,
    "heldout_observed": 0.4417,
    "heldout_null": 0.2756,
    "heldout_null_sd": 0.0490,
    "heldout_z": 3.39,
    "sweep": {
        2: (0.7085, 0.4044, 0.0243, 12.53),
        3: (0.5044, 0.3182, 0.0204, 9.14),
        4: (0.3991, 0.2623, 0.0211, 6.48),
        5: (0.2645, 0.1995, 0.0176, 3.70),
        6: (0.2046, 0.1718, 0.0167, 1.97),
    },
}


def _measure() -> Dict[str, object]:
    """Run the tool and read its numbers back out of its OWN output.

    **AND IT RUNS THE TOOL AS A COMMAND, NOT AS AN IMPORT.** MEASURED
    2026-11-06: the first version imported the module and called
    `interest.main([])` -- and the tool's `main` takes no arguments and
    prints nothing when called that way, so the check read an EMPTY
    string and reported "the number was not in the output" for two of
    the figures. **THE OUTPUT OF THE COMMAND IS THE MEASUREMENT, SO
    THE COMMAND IS WHAT HAS TO RUN.**

    AND IT IS A SUBPROCESS, so the tool's own `__main__` path is what
    gets exercised -- the same path a reader runs.
    """
    proc = subprocess.run([_python(), os.path.join(FAR, "tools",
                                                   "interest.py")],
                          capture_output=True, text=True, cwd=FAR)
    if proc.returncode != 0:
        raise RuntimeError("the interest tool failed: %s" % proc.stderr[-800:])
    return {"text": proc.stdout, "stderr": proc.stderr}


def _parse(text: str) -> Dict[str, float]:
    """The numbers, read from the printed table.

    AND IT PARSES THE TABLE A READER SEES, not the tool's internals.
    **THE CHECK IS ON THE OUTPUT, BECAUSE THE OUTPUT IS WHAT IS
    PUBLISHED.** If the tool changed its internals and the table still
    prints the right numbers, the check should pass.
    """
    out: Dict[str, float] = {}

    # the coherence block
    m = re.search(r"cohesion observed\s+([0-9.]+)", text)
    if m:
        out["cohesion_observed"] = float(m.group(1))
    # the null lines, the z lines and the observed lines, in ORDER --
    # the coherence block first and the held-out block second.
    nulls = re.findall(r"^\s*null\s+([0-9.]+) \+- ([0-9.]+)", text, re.M)
    zs = re.findall(r"^\s*z\s+([+-][0-9.]+)", text, re.M)
    obs = re.findall(r"^\s*observed\s+([0-9.]+)", text, re.M)
    if len(nulls) >= 1:
        out["cohesion_null"] = float(nulls[0][0])
        out["cohesion_null_sd"] = float(nulls[0][1])
    if len(nulls) >= 2:
        out["heldout_null"] = float(nulls[1][0])
        out["heldout_null_sd"] = float(nulls[1][1])
    if len(zs) >= 1:
        out["cohesion_z"] = float(zs[0])
    if len(zs) >= 2:
        out["heldout_z"] = float(zs[1])
    # AND THE HELD-OUT OBSERVED, which is the SECOND bare "observed"
    # line -- the first one is "cohesion observed", which carries its
    # own label and so does not match the bare pattern.
    if len(obs) >= 1:
        out["heldout_observed"] = float(obs[0])
    # the sweep
    for k, (o, n, sd, z) in PUBLISHED["sweep"].items():   # type: ignore[union-attr]
        m = re.search(r"K=%d\s+observed ([0-9.]+)\s+null ([0-9.]+) \+- "
                      r"([0-9.]+)\s+z=([+-][0-9.]+)" % k, text)
        if m:
            out["sweep_%d" % k] = float(m.group(4))
    return out


def main() -> int:
    print("=" * 78)
    print("THE INTEREST NUMBERS -- the published figures against the "
          "tool's output")
    print("=" * 78)
    print()
    ok = True

    def check(label: str, got: object, want: object, tol: float = 0.0) -> None:
        nonlocal ok
        if got is None:
            print("  [FAIL] %s -- the number was not in the output" % label)
            ok = False
            return
        close = abs(float(got) - float(want)) <= tol
        print("  [%s] %-28s published %-10s measured %s"
              % ("ok " if close else "FAIL", label, want, got))
        if not close:
            ok = False

    measured = _measure()
    text = str(measured["text"])
    nums = _parse(text)
    if not nums:
        print("  [FAIL] the tool's output could not be parsed -- the "
              "check cannot read its own measurement")
        print(str(measured["text"])[:800])
        return 2

    check("cohesion observed", nums.get("cohesion_observed"),
          PUBLISHED["cohesion_observed"], 0.0001)
    check("cohesion null", nums.get("cohesion_null"),
          PUBLISHED["cohesion_null"], 0.0001)
    check("cohesion null sd", nums.get("cohesion_null_sd"),
          PUBLISHED["cohesion_null_sd"], 0.0001)
    check("cohesion z", nums.get("cohesion_z"),
          PUBLISHED["cohesion_z"], 0.005)
    check("held-out observed", nums.get("heldout_observed"),
          PUBLISHED["heldout_observed"], 0.0001)
    check("held-out null", nums.get("heldout_null"),
          PUBLISHED["heldout_null"], 0.0001)
    check("held-out z", nums.get("heldout_z"),
          PUBLISHED["heldout_z"], 0.005)
    for k in sorted(PUBLISHED["sweep"]):    # type: ignore[arg-type]
        check("sweep K=%d z" % k, nums.get("sweep_%d" % k),
              PUBLISHED["sweep"][k][3], 0.005)  # type: ignore[index]

    # -- AND THE MUTATIONS, because a check that cannot go RED is a
    # -- check that cannot catch anything.
    print()
    print("AND THE MUTATIONS -- the check must go RED")
    print()
    # AND THE MUTATION IS APPLIED BY CHANGING THE PUBLISHED TABLE AND
    # RE-RUNNING THE SAME COMPARISON -- so the mutation tests the
    # COMPARISON, not a hand-written imitation of it.
    def _compare(published: Dict[str, object]) -> List[str]:
        """The failures, if the published table is compared to the
        measured numbers. An empty list means they agree."""
        fails: List[str] = []
        for label, key, tol in (
                ("cohesion observed", "cohesion_observed", 0.0001),
                ("cohesion null", "cohesion_null", 0.0001),
                ("cohesion null sd", "cohesion_null_sd", 0.0001),
                ("cohesion z", "cohesion_z", 0.005),
                ("held-out observed", "heldout_observed", 0.0001),
                ("held-out null", "heldout_null", 0.0001),
                ("held-out null sd", "heldout_null_sd", 0.0001),
                ("held-out z", "heldout_z", 0.005)):
            got = nums.get(key)
            want = published.get(key)
            if got is None or want is None:
                fails.append("%s -- not measured" % label)
            elif abs(float(got) - float(want)) > tol:
                fails.append("%s -- published %s, measured %s"
                             % (label, want, got))
        for k, tup in published["sweep"].items():   # type: ignore[union-attr]
            m = re.search(r"K=%d\s+observed ([0-9.]+)\s+null ([0-9.]+) \+- "
                          r"([0-9.]+)\s+z=([+-][0-9.]+)" % k, text)
            if not m:
                fails.append("sweep K=%d -- not measured" % k)
            elif abs(float(m.group(4)) - float(tup[3])) > 0.005:
                fails.append("sweep K=%d -- published %s, measured %s"
                             % (k, tup[3], m.group(4)))
        return fails

    MUTATIONS = [
        ("M1", "a published z is wrong",
         {**PUBLISHED, "cohesion_z": 9.99},
         "the published z is not the measured z"),
        ("M2", "a published null is wrong",
         {**PUBLISHED, "cohesion_null": 0.9},
         "the published null is not the measured null"),
        ("M3", "the held-out z is wrong",
         {**PUBLISHED, "heldout_z": 0.5},
         "the published held-out z is not the measured one"),
        ("M4", "a sweep figure is wrong",
         {**PUBLISHED, "sweep": {**PUBLISHED["sweep"],   # type: ignore[dict-item]
                                 4: (0.3991, 0.2623, 0.0211, 1.11)}},
         "the published sweep z is not the measured one"),
    ]
    for code, name, bad, why in MUTATIONS:
        print("  %-3s %s" % (code, name))
        fails = _compare(bad)
        if not fails:
            print("      the check did NOT go red -- the mutation went "
                  "unnoticed")
            print("      -> RED as required (the harness cannot check it)")
            ok = False
        else:
            print("      the check went RED: %s" % fails[0])
            print("      -> caught")
            print("      GREEN, as required (the mutation was caught)")
        print()

    print("=" * 78)
    if ok:
        print("VERDICT: PASS -- the published figures ARE the tool's output")
        print("  and 4 of 4 mutations were caught")
        return 0
    print("VERDICT: FAIL -- a published figure is not the tool's output")
    print("  **A NUMBER IN A COMMIT MESSAGE IS A MEASUREMENT, AND A")
    print("  MEASUREMENT IS SOMETHING YOU RAN.**")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
