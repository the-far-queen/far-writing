"""
test_the_fixture_holds_the_measurement_not_the_answer.py -- A FIXTURE
THAT HOLDS THE ANSWER CANNOT CHECK THE ANSWER.

**THE DEFECT THIS CATCHES.** MEASURED 2026-11-01. The commit that made
the far-writing checks reproducible did it by committing the Gutenberg
measurement as a fixture, so a fresh clone could run the checks without
the gitignored cache.

The fixture held the books ALREADY SPLIT --

    {"ebook_id": "84", "title": "Frankenstein; or, The modern
     Prometheus", "author": "Mary Wollstonecraft Shelley",
     "downloads": 7904}

-- so `gutenberg_ranks.load()` could hand them straight back without
calling `split_title_author()` at all. The parser was unreachable on
the default path.

And the mutation check said so. MEASURED, `python
tools/mutation_check.py` reported 15 of 16 mutations RED and this one
GREEN:

    GREEN the Gutenberg title keeps its author   <- THE TEST CANNOT FAIL

The mutation changes the splitter so the title keeps its author. The
E2 check looks at the download counts and at the key shape -- and on
the default path it never sees a splitter, so it cannot see the
change. A check that cannot fail is not a check.

MEASURED, the mechanism, with the mutation applied to a copy of the
tree:

    the fixture present (the default path)   the E2 check PASSED
    the fixture taken away                   the E2 check FAILED

So the fix is not a better assertion. The fix is that the FIXTURE
holds the raw row -- the anchor text and the count -- and the parse
happens in the loader, on every path. Then the parser is always
exercised, and always measurable.

THE CHECKS, and each is a check that can fail:

    F1  the committed fixture holds the RAW row -- the anchor text --
        and not a pre-split title/author pair
    F2  the loader parses the fixture, so the parser is on the path
    F3  the parsed fixture measures the SAME thing the raw page does
        -- the fixture is the measurement, not a different one
    F4  THE MUTATION MUST GO RED. The splitter is broken on a copy of
        the tree, and the E2 check must fail there. This is the check
        that cannot be satisfied by a fixture that holds the answer.

**AND F4 IS THE ONE THAT MATTERS.** F1 and F2 are shape checks; they
can be satisfied by a fixture that holds the answer and a loader that
never calls the splitter. F4 measures the thing itself.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, "tools"))

FIXTURE = os.path.join(REPO, "catalog", "fixtures", "gutenberg_books.json")
PAGE = os.path.join(REPO, "catalog", "gutenberg", "top.html")

#: THE MUTATION. It is the same text the mutation check uses, so the
#: two cannot drift apart.
MUT_FILE = "tools/gutenberg_ranks.py"
MUT_OLD = ('    m = TITLE_AUTHOR.match(t)\n'
           '    if not m:\n'
           '        return t, ""\n'
           '    return m.group(1).strip(), m.group(2).strip()')
MUT_NEW = ('    m = TITLE_AUTHOR.match(t)\n'
           '    if not m:\n'
           '        return t, ""\n'
           '    return t, m.group(2).strip()')

#: THE CHECK THE MUTATION MUST BREAK.
E2_CALL = ("import sys; sys.path.insert(0, 'tools'); "
           "sys.path.insert(0, 'tests'); "
           "import test_expand_works as t; "
           "t.t_E2_the_gutenberg_title_is_the_title(); "
           "print('E2 PASSED')")


def _fixture() -> dict:
    with open(FIXTURE, encoding="utf-8") as fh:
        return json.load(fh)


# --------------------------------------------------------------------------
# F1: the fixture holds the raw row, not a pre-split pair
# --------------------------------------------------------------------------

def test_F1_the_fixture_holds_the_raw_row_and_not_a_split_pair():
    """the fixture must hold what was OBSERVED, not what was DERIVED.

    MEASURED: the fixture that shipped on 2026-11-01 held
    {"ebook_id", "title", "author", "downloads"}. The raw form holds
    {"ebook_id", "anchor", "downloads"}.
    """
    data = _fixture()
    books = data.get("books") or []
    assert books, "the fixture holds no books"

    with_anchor = [b for b in books if "anchor" in b]
    with_pair = [b for b in books if "title" in b and "author" in b]
    assert with_anchor, (
        "the fixture holds no raw anchor rows -- it holds %d pre-split "
        "pairs, so the loader can hand them back without parsing and "
        "the parser is unreachable" % len(with_pair))
    assert not with_pair, (
        "%d fixture books still hold a pre-split title/author pair -- "
        "a fixture that holds the answer cannot check the answer"
        % len(with_pair))


def test_F2_the_loader_parses_the_fixture():
    """the loader must call the parser, not hand the rows back.

    MEASURED: this is the defect itself -- `load_fixture()` used to
    build `BookRank` objects straight out of the JSON, so
    `split_title_author()` was never called on the default path.
    """
    import gutenberg_ranks

    src = open(os.path.join(REPO, MUT_FILE), encoding="utf-8").read()
    fixture_body = src.split("def load_fixture(", 1)[1]
    fixture_body = fixture_body.split("\ndef ", 1)[0]
    assert "parse_book_rows" in fixture_body, (
        "load_fixture() does not parse the rows -- it hands them back "
        "as they are stored, so the parser is not on the path")
    assert "parse_author_rows" in fixture_body, (
        "load_fixture() does not parse the author rows")

    # AND THE LOADER WORKS.
    books, authors = gutenberg_ranks.load()
    assert books, "the loader returned no books"
    assert authors, "the loader returned no authors"


def test_F3_the_fixture_measures_the_same_thing_the_page_does():
    """the fixture IS the measurement -- so it must equal the page.

    MEASURED: 115 books and 111 authors on both sides, title for
    title and count for count.
    """
    import gutenberg_ranks

    books, authors = gutenberg_ranks.load()
    assert len(books) == 115, (
        "the fixture measures %d books, not the 115 the page holds"
        % len(books))
    assert len(authors) == 111, (
        "the fixture measures %d authors, not the 111 the page holds"
        % len(authors))

    if not os.path.isfile(PAGE):
        # the page is gitignored, so a clone does not have it. The
        # committed fixture is the measurement there, and the check
        # above already ran.
        return

    with open(PAGE, encoding="utf-8") as fh:
        html = fh.read()
    page_books = gutenberg_ranks.parse_books(html)
    page_authors = gutenberg_ranks.parse_authors(html)

    assert [b.to_dict() for b in books] == [b.to_dict() for b in page_books], (
        "the fixture and the page measure different books -- the "
        "fixture is supposed to BE the page's measurement")
    assert ([a.to_dict() for a in authors]
            == [a.to_dict() for a in page_authors]), (
        "the fixture and the page measure different authors")


# --------------------------------------------------------------------------
# F4: THE MUTATION MUST GO RED
# --------------------------------------------------------------------------

def _mutated_tree() -> str:
    """a copy of the tree with the splitter broken."""
    root = tempfile.mkdtemp(prefix="fixprobe-")
    for rel in ("tools", "tests"):
        shutil.copytree(os.path.join(REPO, rel),
                        os.path.join(root, rel),
                        ignore=shutil.ignore_patterns("__pycache__"))
    cat = os.path.join(root, "catalog")
    os.makedirs(os.path.join(cat, "gutenberg"), exist_ok=True)
    shutil.copy2(os.path.join(REPO, "catalog", "authors.json"),
                 os.path.join(cat, "authors.json"))
    fix_src = os.path.join(REPO, "catalog", "fixtures")
    if os.path.isdir(fix_src):
        shutil.copytree(fix_src, os.path.join(cat, "fixtures"),
                        ignore=shutil.ignore_patterns("__pycache__"))

    path = os.path.join(root, MUT_FILE)
    with open(path, encoding="utf-8") as fh:
        src = fh.read()
    assert MUT_OLD in src, (
        "the mutation's old text is not in %s -- the mutation cannot be "
        "applied, so this check cannot measure anything" % MUT_FILE)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(src.replace(MUT_OLD, MUT_NEW, 1))
    return root


def test_F4_the_E2_mutation_goes_red():
    """THE ONE THAT MATTERS.

    The splitter is broken on a copy of the tree, and the E2 check
    must FAIL there. MEASURED before the fix: the check PASSED with
    the mutation in place, and the mutation check reported the E2
    mutation as GREEN.
    """
    tree = _mutated_tree()
    try:
        env = dict(os.environ)
        env["PYTHONPATH"] = os.path.join(tree, "tools")
        p = subprocess.run([sys.executable, "-c", E2_CALL], cwd=tree,
                           capture_output=True, text=True, env=env,
                           timeout=300)
    finally:
        shutil.rmtree(tree, ignore_errors=True)

    assert p.returncode != 0, (
        "the E2 check PASSED with the splitter broken -- it cannot see "
        "a change to the parser, so it does not test the parser. The "
        "mutation check reported this as GREEN for exactly this reason.")
    out = (p.stdout or "") + (p.stderr or "")
    assert "AssertionError" in out, (
        "the check failed for a reason other than its assertion: %s"
        % out[-400:])
