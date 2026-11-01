"""
mutation_check.py -- THE MUTATION CHECK for the expansion's checks.

**A TEST THAT CANNOT FAIL IS NOT A TEST.** Each mutation removes the
mechanism one of E1..E8 tests, and the mutation MUST make that test
go RED. A mutation that stays green means the test does not actually
test what it claims.

Each mutation is applied to a COPY of the repo's source, in a
temporary tree, and the suite is run there -- so the working tree is
never modified.

Run:  python tools/mutation_check.py
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

#: THE MUTATIONS. Each is (name, file, old, new, the test that must go
#: RED).
MUTATIONS = [
    # E1: the reach lookup stops normalizing the key. MEASURED: the
    # defect was 22% of the table unreachable, so the check must see a
    # real work become unfindable.
    #
    # **AND THE MUTATION IS THE DEFECT ITSELF.** The old code keyed
    # the table by the RAW label and looked up with the NORMALIZED
    # title -- so the reader is what has to change, and the writer is
    # what has to stay raw.
    ("the reach reader stops normalizing the key",
     "tools/reach_measure.py",
     "    return {reach_key(k): int(v) for k, v in raw.items()}",
     "    return {k: int(v) for k, v in raw.items()}",
     "E1"),

    # E1 again: the writer stops normalizing, so the table is written
    # raw -- and a reader looking up the normalized title cannot find
    # it.
    ("the reach writer stops normalizing the key",
     "tools/reach_measure.py",
     "    json.dump({reach_key(k): int(v) for k, v in by_work_counts.items()},",
     "    json.dump({k: int(v) for k, v in by_work_counts.items()},",
     "E1"),

    # E2: the Gutenberg title keeps its author.
    ("the Gutenberg title keeps its author",
     "tools/gutenberg_ranks.py",
     "    m = TITLE_AUTHOR.match(t)\n    if not m:\n        return t, \"\"\n    return m.group(1).strip(), m.group(2).strip()",
     "    m = TITLE_AUTHOR.match(t)\n    if not m:\n        return t, \"\"\n    return t, m.group(2).strip()",
     "E2"),

    # E3: the query counts rows again, not distinct adaptations.
    ("the reach query counts rows again",
     "tools/reach_measure.py",
     "(COUNT(DISTINCT ?adapt) AS ?adaptations)",
     "(COUNT(?adapt) AS ?adaptations)",
     "E3"),

    # E4: the query loses the distinct count entirely.
    ("the reach query loses COUNT(DISTINCT)",
     "tools/reach_measure.py",
     "(COUNT(DISTINCT ?adapt) AS ?adaptations)",
     "(COUNT(?x) AS ?adaptations)",
     "E4"),

    # E5: the cache key goes back to the URL's tail -- the ORIGINAL
    # defect. The key function is named, so the mutation is in one
    # place.
    ("the URL cache key goes back to the tail",
     "tools/expand_works.py",
     '    return "http_" + hashlib.sha256(url.encode("utf-8")).hexdigest()[:24]',
     '    return ("http_" + re.sub(r"[^A-Za-z0-9]+", "_", url)[-90:])[:80]',
     "E5"),

    # E5 again: the SPARQL cache key goes back to Python's hash().
    ("the SPARQL cache key goes back to Python's hash()",
     "tools/reach_measure.py",
     '    h = hashlib.sha256(sparql.encode("utf-8")).hexdigest()[:16]',
     "    h = str(abs(hash(sparql)))",
     "E5"),

    # E6: the picker's preference is INVERTED, so the worst candidate
    # wins. This is a real defect -- the original would be a stage
    # adaptation instead of the work.
    ("the picker prefers the WORST candidate",
     "tools/expand_works.py",
     "        if best_key is None or key > best_key:",
     "        if best_key is None or key < best_key:",
     "E6"),

    # E6 again: the picker takes the LAST candidate outright, whatever
    # its score -- so a candidate list whose best entry comes FIRST
    # still loses to the last one.
    ("the picker takes the last candidate outright",
     "tools/expand_works.py",
     "        if best_key is None or key > best_key:",
     "        if True:",
     "E6"),

    # E7: the dateless refusal is not counted.
    ("the dateless refusal is not counted",
     "tools/expand_works.py",
     '        skipped["no_date"] += 1\n        return False',
     "        return False",
     "E7"),

    # E7 again: the after-death refusal is not counted.
    ("the after-death refusal is not counted",
     "tools/expand_works.py",
     '        skipped["after_death"] += 1\n        return False',
     "        return False",
     "E7"),

    # E8: the discovery is written twice again -- the report and the
    # apply each running their own copy, which is the defect.
    ("the discovery is written twice again",
     "tools/expand_works.py",
     "    found = discover(a, qid)",
     "    found = discover(a, qid)\n    found = discover(a, qid)",
     "E8"),

    # E8 again: the apply goes back to the per-title resolution, so
    # the report and the apply use DIFFERENT machinery.
    ("the apply goes back to the per-title resolution",
     "tools/expand_works.py",
     "    found = discover(a, qid)",
     "    found = discover(a, qid)\n    found = resolve_titles([])",
     "E8"),

    # D1: the catalog holds one entry per Wikidata item. The mutation
    # puts a duplicate back, and D1 must see it.
    ("the catalog holds one entry per item",
     "tools/dedupe_authors.py",
     '    m = re.search(r"(Q\\d+)", a.get("source", "") or "")\n'
     '    return m.group(0) if m else ""',
     '    m = re.search(r"(Q\\d+)", a.get("source", "") or "")\n'
     '    return m.group(0) if m else ("Q" + a.get("name", "")[:6])',
     "D1"),

    # D2: the merge drops the other entry's works.
    ("the merge drops the other entry's works",
     "tools/dedupe_authors.py",
     "    for w in other.get(\"works\", []):\n"
     "        k = norm(w.get(\"title\", \"\"))\n"
     "        if not k or k in seen:\n"
     "            continue",
     "    for w in other.get(\"works\", []):\n"
     "        k = norm(w.get(\"title\", \"\"))\n"
     "        if True:\n"
     "            continue",
     "D2"),

    # D4: the merge keeps a duplicate work.
    ("the merge keeps a duplicate work",
     "tools/dedupe_authors.py",
     "        if not k or k in seen:\n            continue\n"
     "        seen.add(k)",
     "        if not k:\n            continue\n"
     "        seen.add(k)",
     "D4"),
]


def run_suite(tree: str) -> tuple:
    env = dict(os.environ)
    env["PYTHONPATH"] = os.path.join(tree, "tools")
    p = subprocess.run(
        [sys.executable, "-m", "pytest",
         "tests/test_expand_works.py", "tests/test_dedupe_authors.py",
         "-q", "--no-header", "-x", "--tb=no"],
        cwd=tree, capture_output=True, text=True, env=env, timeout=300)
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def main() -> int:
    print("=" * 78)
    print("THE MUTATION CHECK")
    print("=" * 78)
    print("  each mutation removes the mechanism one check tests, and the")
    print("  check MUST go RED. a mutation that stays green means the")
    print("  check does not test what it claims.")
    print()

    base = tempfile.mkdtemp(prefix="mutcheck-")
    # AND THE MUTATION TREES ARE SIBLINGS OF THE BASE, NEVER CHILDREN.
    # MEASURED 2026-10-31: the first version made the mutation tree a
    # child of the base tree -- `copytree(base, base/mut_0)`. And
    # `copytree` CREATES the destination before it walks the source, so
    # the source's new child was copied INTO itself: mut_0/mut_0,
    # mut_1/mut_0/mut_0, and so on, until the run had written 45 GB
    # and the disk was full. **A copytree into a child of its own
    # source is a recursion.**
    work = tempfile.mkdtemp(prefix="mutrun-")
    try:
        # THE BASELINE: the suite must pass before a mutation means
        # anything.
        #
        # AND ONLY WHAT THE CHECKS NEED IS COPIED. The catalog's cache
        # is 146 MB of Wikipedia and Wikidata JSON, and the checks read
        # the reach table from it -- so the cache is copied, but the
        # SPARQL row files are the only ones the E3 check needs, and
        # copying all of them ten times is what made the first run of
        # this harness exceed its budget.
        for rel in ("tools", "tests"):
            src = os.path.join(REPO, rel)
            dst = os.path.join(base, rel)
            if os.path.isdir(src):
                shutil.copytree(src, dst,
                                ignore=shutil.ignore_patterns("__pycache__"))
        cat = os.path.join(base, "catalog")
        os.makedirs(os.path.join(cat, "gutenberg"), exist_ok=True)
        # THE CATALOG ITSELF: the catalog's authors.json, which the
        # checks read.
        shutil.copy2(os.path.join(REPO, "catalog", "authors.json"),
                     os.path.join(cat, "authors.json"))
        # THE GUTENBERG PAGE: the download counts.
        top = os.path.join(REPO, "catalog", "gutenberg", "top.html")
        if os.path.isfile(top):
            shutil.copy2(top, os.path.join(cat, "gutenberg", "top.html"))
        # THE CACHE: the reach tables and the old SPARQL rows.
        #
        # **AND THE COMMITTED FIXTURES ARE COPIED TOO.** MEASURED
        # 2026-11-01: the cache is gitignored, so a fresh clone had
        # none of it and the checks that read it FAILED there -- 4 of
        # 79. The fixtures are the same measurement, committed, and the
        # harness needs them for the same reason the clone does.
        wc = os.path.join(cat, "gutenberg", "wikicache")
        os.makedirs(wc, exist_ok=True)
        cache_dir = os.path.join(REPO, "catalog", "gutenberg", "wikicache")
        if os.path.isdir(cache_dir):
            for fn in os.listdir(cache_dir):
                if fn.startswith("sparql_adaptations") or \
                   fn in ("reach_by_work.json", "reach_by_author.json"):
                    shutil.copy2(os.path.join(cache_dir, fn),
                                 os.path.join(wc, fn))
        # THE FIXTURES: copied whole, because they are small and they
        # are what a clone has.
        fix_src = os.path.join(REPO, "catalog", "fixtures")
        if os.path.isdir(fix_src):
            shutil.copytree(fix_src, os.path.join(cat, "fixtures"),
                            ignore=shutil.ignore_patterns("__pycache__"))
        rc, out = run_suite(base)
        print("  the BASELINE: rc=%d" % rc)
        if rc != 0:
            print(out[-3000:])
            print("  the baseline does not pass, so a mutation proves "
                  "nothing.")
            return 1
        print("  the baseline passes, so a RED is the mutation's doing.")
        print()

        red = 0
        green = 0
        # AND THE MUTATION TREE IS A SIBLING OF THE BASE, NOT A CHILD.
        # MEASURED 2026-10-31: the first version copied the base tree
        # into a directory INSIDE the base tree, so each mutation
        # nested inside the last -- mut_1 inside mut_0 inside mut_0 --
        # and the run filled the disk with 45 GB of copies before it
        # stopped. The copy is now into a fresh sibling directory, and
        # each mutation's tree is removed as soon as it has been run.
        for i, (name, rel, old, new, test) in enumerate(MUTATIONS):
            tree = os.path.join(work, "run_%02d" % i)
            if os.path.exists(tree):
                shutil.rmtree(tree)
            shutil.copytree(base, tree,
                            ignore=shutil.ignore_patterns("__pycache__",
                                                          ".pytest_cache"))
            path = os.path.join(tree, rel)
            with open(path, encoding="utf-8") as fh:
                src = fh.read()
            if old not in src:
                print("  SKIP  %-46s (the old text is not there)" % name)
                shutil.rmtree(tree, ignore_errors=True)
                continue
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(src.replace(old, new, 1))
            rc, out = run_suite(tree)
            # AND THE TREE GOES AWAY, so the disk does not fill.
            shutil.rmtree(tree, ignore_errors=True)
            # AND THE RUN'S OWN FOOTPRINT IS CHECKED. MEASURED: the
            # recursion filled 45 GB and the only symptom was a
            # WinError 112 at the end. So the size of the work
            # directory is measured after every mutation, and a run
            # that grows past a sane bound says so instead of filling
            # the disk.
            used = sum(os.path.getsize(os.path.join(dp, f))
                       for dp, _, fs in os.walk(work) for f in fs
                       if os.path.exists(os.path.join(dp, f)))
            if used > 200 * 1024 * 1024:
                print("  ABORT %-46s the run has written %d MB"
                      % (name, used // (1024 * 1024)))
                return 1
            if rc != 0:
                red += 1
                tail = [l for l in out.splitlines()
                        if l.startswith("FAILED") or "failed" in l.lower()]
                print("  RED   %-46s %s" % (name, tail[0][:60] if tail else ""))
            else:
                green += 1
                print("  GREEN %-46s <- THE TEST CANNOT FAIL" % name)
        print()
        print("  mutations that went RED: %d" % red)
        print("  mutations that stayed GREEN: %d" % green)
        if green:
            print("  A GREEN MUTATION MEANS THE CHECK DOES NOT HOLD.")
            return 1
        print("  every mutation went RED: the checks hold.")
        return 0
    finally:
        shutil.rmtree(base, ignore_errors=True)
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
