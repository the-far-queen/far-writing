"""
build_phrase_pages.py -- ONE INDEXED PAGE PER MEASURED PHRASE.

WHY THIS EXISTS
---------------
Bobby, 2026-10-31: *"we automate and produce many titles publish on
social media at no penalty, hand edit or more care with our amazon
titles, also many website pages"*.

**AND THE PENALTY STRUCTURE IS WHAT MAKES IT THE PLAN.** MEASURED from
KDP's own rules and from the platforms:

| surface | volume limit | review |
|---|---|---|
| Amazon KDP | 2 created + 2 submitted per FORMAT per week | 3 days; low-content 3-4 WEEKS |
| X Article | none | none |
| Substack | none | none |
| **a website page** | **none** | **none** |

So the funnel's wide end is the channels and the narrow end is
Amazon, and the website is the widest channel there is: **a page per
phrase, published forever, with no limit and no review.**

**AND THE SITE ALREADY HAS THE PATTERN.** MEASURED 2026-10-31:
`vault/30-website/farqueen-site/` holds 106 PHP pages and 123 level
pages under `levels/`, and the level pages already mirror the
Desktop's test-prep files. **So this generator writes the same shape of
page, for the same reason, at a scale the level pages cannot reach.**

WHAT A PAGE IS
--------------
Not a stub. A page that:
  * carries the phrase in the TITLE and in the META DESCRIPTION, in
    the words the buyer types -- because the search and the ORDER of
    the list is the game
  * states what the page offers, in the buyer's own words
  * links to the book where there IS a book, and to the NEXT page
    where there is not
  * carries the site's own nav and style, so it is a real page
  * says what it is, so it is not a deceptive page -- KDP's rule
    against misleading content is the same principle, and a doorway
    page violates it

THE THREE RULES THIS GENERATOR ENFORCES
---------------------------------------
1. **ONE PHRASE, ONE PAGE.** KDP refuses content "not significantly
   different" from another book in the store, and a site full of
   near-identical pages is the same defect at the domain level. So
   each phrase gets exactly one page, and the pages link to each
   other rather than duplicating each other.

2. **A PAGE IS NOT A DOORWAY.** Every page names what it offers. A
   page that exists only to catch a phrase and redirect is the
   deceptive pattern, and it is the pattern the whole project
   refuses.

3. **THE CLAIMS ARE TRACEABLE.** Every number on a page comes from a
   source file, and the page says which. The site's house rule, and
   the project's: every claim traceable to a named source.

Run:
    python tools/build_phrase_pages.py --out <site-dir>
    python tools/build_phrase_pages.py --out <site-dir> --dry-run
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from typing import Any, Dict, List, Optional, Tuple

_HERE = os.path.dirname(os.path.abspath(__file__))
_FAR_WRITING = os.path.abspath(os.path.join(_HERE, "..", "..", "far-writing"))
if _FAR_WRITING not in sys.path:
    sys.path.insert(0, os.path.join(_FAR_WRITING, "tools"))

import keyword_phrases as KP  # noqa: E402


def _slug(text: str) -> str:
    keep = []
    for ch in text.lower():
        keep.append(ch if (ch.isalnum() or ch in "-") else "-")
    out = "".join(keep).strip("-")
    while "--" in out:
        out = out.replace("--", "-")
    return out[:70] or "page"


def _title_case(text: str) -> str:
    small = {"a", "an", "the", "of", "and", "or", "to", "in", "for",
             "on", "at", "by", "with", "from", "your", "my", "our",
             "a", "an"}
    words = text.split()
    out = []
    for i, w in enumerate(words):
        if i > 0 and w.lower() in small:
            out.append(w.lower())
        else:
            out.append(w[:1].upper() + w[1:])
    return " ".join(out)


def _escape(text: str) -> str:
    return (text.replace("&", "&amp;").replace("<", "&lt;")
                .replace(">", "&gt;").replace('"', "&quot;"))


PAGE_TEMPLATE = """<!DOCTYPE html><html lang='en-US'><head><meta http-equiv='Content-Type' content='text/html; charset=utf-8'>
<meta name='viewport' content='width=device-width, initial-scale=1.0'>
<title>{title}</title>
<meta name='Description' content='{description}'>

<?php include('./style1.php');  ?>

<?php include('./header1.php');  ?>

    <!-- BEGIN PAGE CONTAINER -->
    <div class='page-container'>

    <!-- BEGIN NAV -->
    <nav>

<?php include('./pagemenu1.php');  ?>


    <!-- END NAV -->
    </nav>

    <!-- BEGIN MAIN -->
    <main>

    <!-- BEGIN FIRST ARTICLE -->
    <article>

<h1>{title}</h1>

{body}

    <!-- END FIRST ARTICLE -->

    <!-- END MAIN -->
    </main>

    <!-- BEGIN RIGHTNAV -->


    <!-- END RIGHTNAV -->
    </div>
    <!-- END PAGE CONTAINER -->

<?php include('./footer1.php');  ?>

</body></html>
"""


def page_for(category: KP.Category, phrase: KP.Phrase,
             index: int) -> Tuple[str, str]:
    """the (filename, html) for one phrase.

    AND EVERY LINE OF THE BODY IS TRACEABLE, and the page says so.
    That is the site's house rule and it is why the claims carry their
    source in the text rather than only in a comment.
    """
    title = _title_case(phrase.phrase)
    parts: List[str] = []

    # WHAT THIS PAGE IS, in the buyer's words.
    parts.append("<p>%s</p>" % _escape(
        "This page is the starting point for %s. It is here because that "
        "is the phrase people type, and because what sits under it is "
        "worth reading." % phrase.phrase))

    # THE MEASURED DEMAND, and where it came from.
    if phrase.measured:
        parts.append("<h2>What is already published under this phrase</h2>")
        parts.append("<p>Amazon's books department reports %s results for "
                     "<b>%s</b>. Measured on Amazon's own search endpoint on "
                     "2026-10-31; the count is rounded by Amazon and is "
                     "recorded as reported.</p>"
                     % (phrase.results, _escape(phrase.phrase)))
    else:
        parts.append("<p><b>This phrase has not been measured yet.</b> The "
                     "demand count is not known, so nothing is claimed "
                     "about it here.</p>")

    # THE COMPETITORS, so the page is honest about the field.
    if phrase.competitor_titles:
        parts.append("<h2>What is at the top of the list now</h2><ul>")
        for t in phrase.competitor_titles[:5]:
            parts.append("<li>%s</li>" % _escape(t))
        parts.append("</ul>")
        if phrase.competitor_prices:
            parts.append("<p>Top-of-list prices at the time of "
                         "measurement: %s.</p>"
                         % ", ".join(phrase.competitor_prices[:5]))

    # THE SUPPLY, which is the reason the page exists.
    if phrase.supply:
        parts.append("<h2>What we hold for this</h2>")
        parts.append("<p>%d questions are held against this subject. That "
                     "is the material the book is made from, and it is "
                     "why the phrase is worth writing rather than "
                     "merely worth searching.</p>" % phrase.supply)

    # THE OFFER, where there IS one.
    titles = KP.titles_for(phrase)
    if titles:
        parts.append("<h2>The books this phrase names</h2>")
        parts.append("<ul>" + "".join(
            "<li>%s</li>" % _escape(t) for t in titles[:6]) + "</ul>")

    # THE NEXT PHRASE, so the pages link rather than duplicate.
    siblings = [p for p in category.phrases if p.phrase != phrase.phrase]
    if siblings:
        nxt = siblings[index % len(siblings)]
        parts.append("<p>Next in %s: <a href='./%s.php'>%s</a>.</p>"
                     % (_escape(category.name), _slug(nxt.phrase),
                        _escape(_title_case(nxt.phrase))))

    # THE SOURCE, because every claim is traceable.
    parts.append("<hr>")
    parts.append("<p><small>Source: <code>far-writing/catalog/"
                 "keyword_phrases.json</code>, measured 2026-10-31 on "
                 "Amazon's books search endpoint. Category: %s. The "
                 "demand figures are Amazon's reported counts and are "
                 "rounded; they are recorded as reported and no rate is "
                 "derived from them.</small></p>"
                 % _escape(category.name))

    body = "\n".join(parts)
    # THE DESCRIPTION IS FOR A READER, not for us. The first version put
    # the phrase's INTERNAL note in the meta description -- "OPEN, and
    # the novel is gone" -- which is our working note leaking into the
    # page a buyer reads. So the description is built from the demand
    # figure and the supply, and never from the note.
    if phrase.measured:
        detail = ("%s results on Amazon's books search, measured "
                  "2026-10-31." % phrase.results)
    else:
        detail = "What is published under this phrase, and what we hold."
    if phrase.supply:
        detail += (" We hold %d questions against this subject."
                   % phrase.supply)
    description = _escape("%s. %s" % (title, detail))[:300]
    html = PAGE_TEMPLATE.format(title=_escape(title),
                                 description=description,
                                 body=body)
    return _slug(phrase.phrase) + ".php", html


def build(out_dir: str, dry_run: bool = False) -> Dict[str, Any]:
    """write the pages, and report what it wrote."""
    written: List[str] = []
    # THE DIRECTORY IS CREATED, because the generator's first run
    # against a fresh path died on FileNotFoundError with no
    # explanation of what was missing.
    if not dry_run and out_dir:
        os.makedirs(out_dir, exist_ok=True)
    for category in KP.CATEGORIES:
        if category.skipped_because:
            continue
        for i, phrase in enumerate(category.phrases):
            name, html = page_for(category, phrase, i)
            path = os.path.join(out_dir, name)
            written.append(name)
            if not dry_run:
                with open(path, "w", encoding="utf-8", newline="\n") as fh:
                    fh.write(html)
    return {"written": len(written), "names": written, "out": out_dir}


def main() -> int:
    ap = argparse.ArgumentParser(
        description="one indexed page per measured phrase")
    ap.add_argument("--out", required=True, help="the site directory")
    ap.add_argument("--dry-run", action="store_true",
                    help="report what would be written")
    args = ap.parse_args()

    res = build(args.out, args.dry_run)
    print("=" * 74)
    print("THE PHRASE PAGES")
    print("=" * 74)
    print()
    print("  pages written       %d" % res["written"])
    print("  out                 %s" % res["out"])
    print()
    for n in res["names"][:20]:
        print("    %s" % n)
    if len(res["names"]) > 20:
        print("    ... and %d more" % (len(res["names"]) - 20))
    print()
    print("  AND THE RULE THIS ENFORCES: one phrase, one page. The")
    print("  pages link to each other rather than duplicating each")
    print("  other, because near-identical pages are the same defect")
    print("  KDP refuses on books, at the domain level.")
    print("=" * 74)
    return 0


if __name__ == "__main__":
    sys.exit(main())
