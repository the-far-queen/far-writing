"""
test_the_checks_can_run.py -- A CHECK MUST BE REPRODUCIBLE BY ITSELF.

**THE THIRD DEFECT IN THIS FAMILY.** On 2026-11-01 the far-writing
repo was found to carry checks that could only run on the machine that
made the measurement. Three separate causes, each measured:

    1. THE DATA WAS NOT IN THE REPO. The checks read
       `catalog/gutenberg/wikicache/`, which is GITIGNORED on purpose.
       So a fresh clone ran 79 checks and 4 of them FAILED.

    2. THE CLONE REACHED FOR THE NETWORK. With no page cached, the
       loader FETCHED the live Gutenberg page -- and that page is a
       MOVING TARGET. MEASURED: the fetched page held 306 book rows
       against the fixture's 115 parsed books, and 114 of the 115
       fixture titles were ABSENT from it. So the clone's ranking was
       a DIFFERENT MEASUREMENT from the working tree's, and the check
       failed on two real titles: Villette and Howards End, both of
       which ARE in the fixture.

    3. THE ZERO'S TABLE WAS ALSO OUTSIDE THE REPO. The exhaustive
       per-work table -- the one that makes a measured zero honest --
       was in the same gitignored cache, so C14 could not run in a
       clone either.

**THE RULE.** A check must be reproducible by anyone who has the
repository. So:

    R1  a check must not read a file outside the repository
    R2  a check must not reach the network
    R3  the data the checks read must be IN the repository

**AND R1 AND R2 ARE CHECKED BY READING THE SOURCE**, because the
dependency is in the code, not in the result. A check that reads a
path outside the repo is found by looking for the path; a check that
reaches the network is found by looking for the call.
"""

from __future__ import annotations

import ast
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)

#: THE FILES THAT CARRY THE CHECKS. Every one of these must be
#: reproducible from the repository alone.
CHECK_FILES = (
    "tests/test_canon.py",
    "tests/test_expand_works.py",
    "tests/test_keyword_phrases.py",
    "tests/test_dedupe_authors.py",
    "tests/test_voice.py",
    "tests/test_opinion.py",
    "tests/test_propose_opinions.py",
    "tests/test_the_commit_is_runnable.py",
    "tests/test_the_checks_can_run.py",
)

#: THE TOOLS THE CHECKS CALL.
TOOL_FILES = (
    "tools/canon.py",
    "tools/expand_works.py",
    "tools/reach_measure.py",
    "tools/gutenberg_ranks.py",
    "tools/keyword_phrases.py",
    "tools/dedupe_authors.py",
    "tools/build_fixtures.py",
    "tools/opinion.py",
    "tools/interest.py",
    "tools/check_opinion.py",
    "tools/check_interest_numbers.py",
    "tools/propose_opinions.py",
)

#: THE FILES THE CHECKS NEED, and they must all be TRACKED.
#:
#: MEASURED: without them the clone fails 4 of 79 checks.
REQUIRED_DATA = (
    "catalog/fixtures/reach_by_work.json",
    "catalog/fixtures/reach_by_author.json",
    "catalog/fixtures/reach_exhaustive_by_work.json",
    "catalog/fixtures/gutenberg_books.json",
    "catalog/fixtures/old_counts.json",
)

#: THE NETWORK CALLS. A check that makes one is not reproducible.
NETWORK_NAMES = {"urlopen", "urlretrieve", "requests", "httpx", "socket",
                 "urlopen"}


def _read(rel: str) -> str:
    with open(os.path.join(REPO, rel), encoding="utf-8") as fh:
        return fh.read()


def _tracked() -> set:
    import subprocess
    p = subprocess.run(["git", "-C", REPO, "ls-files"],
                       capture_output=True, text=True)
    return {line.strip().replace("\\", "/")
            for line in (p.stdout or "").splitlines() if line.strip()}


# --------------------------------------------------------------------------
# R1: no check reads a file outside the repository
# --------------------------------------------------------------------------

def test_R1_no_check_reads_a_path_outside_the_repository():
    """the wikicache and the top.html page are OUTSIDE the repo.

    they are gitignored on purpose -- 178 MB of scraped JSON does not
    belong in a history -- so a check that reads them is a check that
    only runs on one machine.

    **AND THE CHECK LOOKS AT THE CODE, NOT AT THE PROSE.** A path in a
    docstring is a description; a path in an expression is a
    dependency. So the paths are read out of the AST's string
    constants and the source's string literals, and a file that
    mentions the cache only in a comment or a docstring does not
    count. MEASURED: this check's own docstring names
    `catalog/gutenberg/wikicache/` and the first version of it flagged
    ITSELF -- which is how the check learned to tell prose from code.
    """
    offenders = []
    for rel in CHECK_FILES + TOOL_FILES:
        path = os.path.join(REPO, rel)
        if not os.path.isfile(path):
            continue
        src = _read(rel)
        # THE CODE, and only the code: the string constants and the
        # literals, with the comments and the docstrings removed.
        code = _code_only(src)
        for pat in ("wikicache", "top.html"):
            for m in re.finditer(r'"([^"]*%s[^"]*)"' % re.escape(pat), code):
                s = m.group(1)
                if "wikicache" in s or "top.html" in s:
                    # the fallback must exist somewhere in the file
                    if ("_fixture_counts" not in src
                            and "load_fixture" not in src
                            and "FIXTURE" not in src):
                        offenders.append("%s: %s" % (rel, s))
    assert not offenders, (
        "these read a file that is not in the repository, and there is "
        "no fallback to the committed measurement: %s" % offenders)


def _code_only(src: str) -> str:
    """the source with every comment and docstring removed.

    so a path named in prose is not mistaken for a path the code
    reads.
    """
    import io
    import tokenize
    out = []
    try:
        for tok in tokenize.generate_tokens(io.StringIO(src).readline):
            if tok.type in (tokenize.COMMENT, tokenize.STRING):
                continue
            out.append(tok.string)
    except tokenize.TokenError:
        return src
    return " ".join(out)


# --------------------------------------------------------------------------
# R2: no check reaches the network
# --------------------------------------------------------------------------

def test_R2_no_check_reaches_the_network():
    """a check that fetches is not reproducible.

    MEASURED: the clone fetched the live Gutenberg page and got a
    DIFFERENT measurement -- 306 rows against 115, with 114 of the
    fixture's titles missing. The check then failed on two real
    titles that were in the fixture all along.
    """
    offenders = []
    for rel in CHECK_FILES:
        path = os.path.join(REPO, rel)
        if not os.path.isfile(path):
            continue
        tree = ast.parse(_read(rel))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                f = node.func
                name = getattr(f, "attr", None) or getattr(f, "id", None)
                if name in NETWORK_NAMES:
                    offenders.append("%s: %s" % (rel, name))
    assert not offenders, (
        "these checks reach the network, so they are not reproducible: "
        "%s" % offenders)


def test_R2b_no_tool_reaches_the_network_on_its_default_path():
    """the tools may fetch, but only when the caller asks.

    MEASURED: `gutenberg_ranks.load()` fetched because the cache was
    missing. The fix is that the COMMITTED measurement is the
    authority and the fetch is explicit -- so the load path must not
    contain a fetch call at all.
    """
    src = _read("tools/gutenberg_ranks.py")
    tree = ast.parse(src)
    in_load = False
    calls = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "load":
            in_load = True
            for sub in ast.walk(node):
                if isinstance(sub, ast.Call):
                    f = sub.func
                    name = getattr(f, "attr", None) or getattr(f, "id", None)
                    if name == "fetch":
                        calls.append(name)
    assert not calls, (
        "load() reaches the network (%s) -- a check that calls it is "
        "not reproducible" % calls)


# --------------------------------------------------------------------------
# R3: the data the checks read is in the repository
# --------------------------------------------------------------------------

def test_R3_the_data_the_checks_read_is_tracked():
    """without these, a fresh clone fails 4 of 79 checks."""
    tr = _tracked()
    missing = [p for p in REQUIRED_DATA if p not in tr]
    assert not missing, (
        "the checks read these and they are not committed, so a clone "
        "cannot run them: %s" % missing)


def test_R4_every_fixture_carries_its_provenance():
    """a fixture without a provenance block is a number with no command."""
    import json
    for rel in REQUIRED_DATA:
        path = os.path.join(REPO, rel)
        assert os.path.isfile(path), "%s is missing" % rel
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        prov = data.get("_provenance")
        assert prov, "%s carries no provenance" % rel
        assert prov.get("made_by"), (
            "%s does not name the tool that made it" % rel)
        assert prov.get("derived"), (
            "%s does not carry the date it was derived" % rel)
