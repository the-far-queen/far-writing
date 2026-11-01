"""
test_the_commit_is_runnable.py -- THE COMMIT MUST BE RUNNABLE AS COMMITTED.

**THE DEFECT THIS CATCHES.** On 2026-10-31 the far-writing repo was
pushed with a commit that could not be run. `tools/mutation_check.py`
was committed, and it names two files in its own source:

    "tools/dedupe_authors.py"          <- in MUTATIONS
    "tests/test_dedupe_authors.py"     <- in run_suite()'s argv

NEITHER FILE WAS TRACKED BY GIT. So a fresh clone could not run the
mutation check at all. The commit was green in the working tree and
broken in the clone, and the only way to tell was to clone it and try.

THE RULE. A commit is not a snapshot of a directory. It is a claim that
the tree it names can be run by someone who has only that tree. Two
kinds of thing break that claim:

    1. a file that is committed and NAMED by a committed file, but
       which was never committed itself
    2. a file in tools/ or tests/ that is never committed at all

Both are silent. The suite still passes in the working tree. The
defect only appears in a clone.

SO THE CHECKS ARE THREE, and each is a check that can fail:

    T1  every path named in tools/mutation_check.py is tracked
    T2  every file under tools/ and tests/ is tracked
    T3  the tracked tree holds the same test files the working tree
        holds, so the clone runs the same suite

**AND T1 IS THE ONE THAT CATCHES THE ORIGINAL DEFECT.** A tool that
names a sibling in its own source must have that sibling committed, or
the sibling is a lie in the committed tree.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MUTATION_CHECK = os.path.join(REPO, "tools", "mutation_check.py")


def _git(*args: str) -> str:
    p = subprocess.run(["git", "-C", REPO, *args],
                       capture_output=True, text=True)
    return p.stdout or ""


def tracked() -> set:
    out = _git("ls-files")
    return {line.strip().replace("\\", "/")
            for line in out.splitlines() if line.strip()}


def on_disk(rel_dir: str) -> set:
    """every file under rel_dir, as a repo-relative posix path."""
    root = os.path.join(REPO, rel_dir)
    found = set()
    for dp, _, fs in os.walk(root):
        if "__pycache__" in dp or ".pytest_cache" in dp:
            continue
        for f in fs:
            if f.endswith((".pyc", ".pyo")):
                continue
            full = os.path.join(dp, f)
            found.add(os.path.relpath(full, REPO).replace("\\", "/"))
    return found


def paths_named_by_the_mutation_check() -> set:
    """every repo-relative path the mutation check names in its source.

    it names them in two ways: as the MUTATIONS' file field, and as the
    test files in run_suite()'s argv. BOTH are read from the source
    text, so a new mutation that names a file is covered the moment it
    is written.
    """
    with open(MUTATION_CHECK, encoding="utf-8") as fh:
        src = fh.read()

    named = set()
    # the MUTATIONS list: "tools/whatever.py",
    for m in re.finditer(r'"((?:tools|tests|catalog)/[^"]+)"', src):
        named.add(m.group(1).replace("\\", "/"))
    # run_suite()'s argv: "tests/test_foo.py",
    for m in re.finditer(r'"(tests/[^"]+\.py)"', src):
        named.add(m.group(1).replace("\\", "/"))
    return named


# --------------------------------------------------------------------------
# T1: every file the committed mutation check names is itself committed
# --------------------------------------------------------------------------

def test_T1_every_path_the_mutation_check_names_is_tracked():
    """the original defect: mutation_check.py named two untracked files."""
    named = paths_named_by_the_mutation_check()
    assert named, "the mutation check names no path at all -- the reader broke"

    # the catalog's cache is a runtime artifact and is gitignored on
    # purpose (it is 178 MB of fetched JSON). A name under it is
    # allowed to be untracked, but it must be a name the check reads
    # AT RUNTIME and not one it ships.
    ignored_prefixes = ("catalog/gutenberg/wikicache/",)

    tr = tracked()
    missing = []
    for p in sorted(named):
        if p.startswith(ignored_prefixes):
            continue
        if p not in tr:
            missing.append(p)
    assert not missing, (
        "the committed mutation check names files that are not committed: "
        "%s -- a fresh clone cannot run it" % missing)


# --------------------------------------------------------------------------
# T2: every file under tools/ and tests/ is tracked
# --------------------------------------------------------------------------

def test_T2_every_tool_and_test_on_disk_is_tracked():
    """the second half of the same defect: source that was never added."""
    tr = tracked()
    missing = []
    for rel in ("tools", "tests"):
        for p in sorted(on_disk(rel)):
            if p in tr:
                continue
            missing.append(p)
    assert not missing, (
        "these files are on disk but not committed, so they are lost if "
        "the working tree is lost: %s" % missing)


# --------------------------------------------------------------------------
# T3: the tracked tree runs the same tests the working tree runs
# --------------------------------------------------------------------------

def test_T3_the_clone_runs_the_same_test_files():
    """the count check: 43 in the clone against 76 in the tree is a
    silent loss of 33 checks."""
    tr = {p for p in tracked() if p.startswith("tests/") and
          p.endswith(".py") and os.path.basename(p) != "__init__.py"}
    disk = {p for p in on_disk("tests") if p.endswith(".py") and
            os.path.basename(p) != "__init__.py"}
    missing = sorted(disk - tr)
    assert not missing, (
        "the clone would run fewer tests than the tree: missing %s" % missing)
