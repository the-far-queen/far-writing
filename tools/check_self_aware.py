#!/usr/bin/env python3
"""
check_self_aware.py -- AN UNCERTAIN CLAIM IS MARKED, AND AN UNMARKED
ONE IS CAUGHT.

**AND THIS IS THE SHAPE THE PATTERN TABLE NAMED.** MEASURED
2026-11-05: "an uncertain claim is MARKED as uncertain and an unmarked
one is caught."

**AND THE CHECK IS THE MUTATION-FIRST KIND**: it builds two texts from
the same material -- one that marks its uncertainty and one that does
not -- and requires the pass to behave DIFFERENTLY on them. A check
that only runs on one text cannot tell a working instrument from one
that marks everything or nothing.

And the mutation at the end takes the MARKER LIST away, and the catch
must stop working -- because **the marker list is the instrument**. If
the markers are wrong, the pass misses everything, and a pass that
misses everything looks exactly like a text with nothing uncertain in
it.

Run:
    python tools/check_self_aware.py
"""
from __future__ import annotations

import importlib.util
import os
import shutil
import sys
import tempfile
from typing import List

HERE = os.path.dirname(os.path.abspath(__file__))
FAR = os.path.dirname(HERE)
SRC = os.path.join(FAR, "tools", "self_aware.py")

#: THE MARKED TEXT and the UNMARKED TEXT. AND THEY ARE THE SAME CLAIM,
#: so the pass has to notice the difference and nothing else.
#:
#: AND THE FIRST VERSION OF THESE TEXTS HAD A BUG IN THEM, and the
#: check caught it -- which is the check working. MEASURED: both texts
#: began with the bare sentence "The canon is complete." -- and that
#: sentence is ITSELF a contested claim with no marker in it, so the
#: pass caught it in the MARKED text too, and the marked text was
#: indistinguishable from the unmarked one.
#:
#: **A TEST TEXT THAT FAILS FOR A REASON UNRELATED TO WHAT IS BEING
#: TESTED IS A BAD TEST TEXT**, and the fix is to make the two texts
#: differ in exactly ONE thing: the hedge.
THE_MARKED = (
    "I think the canon is complete, and the reader should know that is "
    "my read rather than a measurement.\n"
)
THE_UNMARKED = (
    "The canon is complete, and every author in the canon is "
    "represented in the corpus without exception.\n"
)


def load(name: str = "sa_probe"):
    spec = importlib.util.spec_from_file_location(name, SRC)
    if spec is None or spec.loader is None:
        raise SystemExit("the self-aware module could not be loaded")
    mod = importlib.util.module_from_spec(spec)
    # AND THE MODULE IS REGISTERED BEFORE IT RUNS. MEASURED: a module
    # loaded by importlib without being registered is None in
    # sys.modules, and `dataclasses` resolves a class's annotations
    # through sys.modules[cls.__module__] -- so the probe died with
    # "'NoneType' object has no attribute '__dict__'".
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def main() -> int:
    print("=" * 74)
    print("AN UNCERTAIN CLAIM IS MARKED, AND AN UNMARKED ONE IS CAUGHT")
    print("=" * 74)
    print()

    failures: List[str] = []

    def check(label: str, cond: bool, extra: str = "") -> None:
        print("  [%s] %s%s" % ("ok " if cond else "FAIL", label,
                               (" -- " + extra) if extra else ""))
        if not cond:
            failures.append(label)

    m = load()

    # -- the marked text ----------------------------------------------
    rep_m = m.audit(THE_MARKED, did=["read the canon"],
                    did_not=["read the works"])
    print("   the marked text:")
    for f in rep_m.findings:
        print("      %-24s marked=%-5s %s"
              % (f.key, f.marked, f.sentence[:56]))
    print("   the unmarked text:")
    rep_u = m.audit(THE_UNMARKED, did=["read the canon"],
                    did_not=["read the works"])
    for f in rep_u.findings:
        print("      %-24s marked=%-5s %s"
              % (f.key, f.marked, f.sentence[:56]))
    print()

    check("the marked text's contested claim is RECORDED as uncertain",
          len(rep_m.uncertain) == 1, str(rep_m.uncertain)[:70])
    check("and it is NOT caught",
          len(rep_m.unmarked) == 0, str(rep_m.unmarked)[:70])
    check("and the UNMARKED text's claim IS caught",
          len(rep_u.unmarked) == 1, str(rep_u.unmarked)[:70])
    check("and the caught sentence is named",
          bool(rep_u.unmarked)
          and "canon" in rep_u.unmarked[0].sentence,
          rep_u.unmarked[0].sentence[:70] if rep_u.unmarked else "")

    # -- AND THE PASS TELLS THE THREE THINGS -------------------------
    check("and the report says what was done",
          rep_u.did == ["read the canon"], str(rep_u.did))
    check("and what was NOT done",
          rep_u.did_not == ["read the works"], str(rep_u.did_not))
    check("and the footer says all three",
          "what I did" in rep_u.render()
          and "what I did not do" in rep_u.render()
          and "uncertain" in rep_u.render().lower(),
          rep_u.render()[:90])

    # -- AND A MARKER IS NOT A MARKER INSIDE A WORD ------------------
    check("and 'may' inside 'mayonnaise' is NOT a hedge",
          m.marker_in("The mayonnaise is on the table.") == "",
          m.marker_in("The mayonnaise is on the table."))
    check("and 'may' on its own IS",
          m.marker_in("This may be the best one.") != "",
          m.marker_in("This may be the best one."))

    # -- AND THE PASS CAN GO RED -------------------------------------
    print()
    print("  AND THE PASS CAN GO RED")
    print()
    # THE MUTATION: the marker list is emptied. The catch must stop
    # working -- because the markers ARE the instrument.
    original = m.MARKERS
    try:
        m.MARKERS = ()
        rep_no_markers = m.audit(THE_MARKED)
        blind = len(rep_no_markers.uncertain) == 0
        print("     with the markers removed, the marked text yields %d "
              "uncertain claim(s)" % len(rep_no_markers.uncertain))
        check("with the markers removed the catch goes BLIND", blind,
              str(len(rep_no_markers.uncertain)))
        check("and a blind pass is distinguishable from a working one",
              len(rep_no_markers.uncertain) != len(rep_m.uncertain),
              "%d then %d" % (len(rep_m.uncertain),
                              len(rep_no_markers.uncertain)))
    finally:
        m.MARKERS = original

    # and the second mutation: the registry is emptied, so nothing is
    # contested and nothing can be caught
    original_c = m.CONTESTED
    try:
        m.CONTESTED = {}
        rep_no_registry = m.audit(THE_UNMARKED)
        print("     with the contested registry removed, the unmarked "
              "text yields %d caught claim(s)"
              % len(rep_no_registry.unmarked))
        check("with the registry removed nothing is caught",
              len(rep_no_registry.unmarked) == 0,
              str(len(rep_no_registry.unmarked)))
        check("and that is distinguishable from the working pass",
              len(rep_no_registry.unmarked) != len(rep_u.unmarked),
              "%d then %d" % (len(rep_u.unmarked),
                              len(rep_no_registry.unmarked)))
    finally:
        m.CONTESTED = original_c

    # -- AND THE MODULE'S OWN SELFTEST --------------------------------
    print()
    print("  AND THE MODULE'S OWN SELFTEST")
    print()
    rc = m._selftest()
    check("and the module's selftest passes", rc == 0, "rc %s" % rc)

    print()
    print("=" * 74)
    print("  %s" % ("PASSED" if not failures else "FAILED"))
    for f in failures:
        print("    FAILED: %s" % f)
    print("=" * 74)
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
