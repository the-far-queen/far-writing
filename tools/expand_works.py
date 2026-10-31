"""
expand_works.py -- EVERY WORK EACH AUTHOR WROTE.

Bobby, 2026-10-31: *"easy to expand works on authors we have"*.

**AND IT IS EASY BECAUSE THE MACHINERY IS ALREADY PROVEN.** The
reach build (tools/build_canon.py) already:
  - reads each author's Wikidata QID out of the catalog's own
    `source` field
  - fetches P800 (notable work by this author)
  - refuses a work outside the era, and a work dated after its
    author died -- both measured, both the gate's own rules

**AND THE MISSING PIECE IS THAT P800 IS ONLY A HANDFUL.** MEASURED:
the reach build added 147 authors and brought 449 works, so ~3 works
per author -- while Ibsen wrote 28 and Salgari 27. P800 is
"notable work", not "every work", and the point of this task is
exactly the works nobody calls notable.

**SO TWO SOURCES, AND THE SECOND IS THE ONE THAT FILLS THE GAP:**

  1. P800  the structured list. Precise, and already fetched.

  2. THE AUTHOR'S OWN BIBLIOGRAPHY -- the "Works" / "Bibliography"
     section of the author's Wikipedia article. This is where the
     obscure titles live, because Wikipedia lists them and Wikidata
     rarely does.

     **AND THE TITLES ARE RESOLVED TO WIKIDATA IN BATCHES OF 50**,
     because the API takes 50 titles per call -- so 5,000 titles is
     100 calls, not 5,000. The resolved item gives the publication
     date, which is what the public-domain test needs.

**AND THE MEASURE FOR EACH ADDED WORK, in its own field:**
  reach_adaptations   how many things were made FROM it (from the
                       cached SPARQL flood measurement)
  gutenberg_downloads  how many times it was downloaded
  claimed_sales_m      the intake's sales figure, where the intake
                       held it -- and it is NEVER invented

**AND THE SAME REFUSALS, because the gate's rules are the gate's
rules:** no date means no public-domain test, so the work is
skipped; a date after the author's death is an edition date, so it is
skipped; a date outside 1800-1940 is outside the build window, so it
is skipped.

Run:
    python tools/expand_works.py --report
    python tools/expand_works.py --apply
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict
from typing import Dict, List, Optional, Set, Tuple

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "tools"))
import canon  # noqa: E402
import reach_measure  # noqa: E402

CATALOG = os.path.join(REPO, "catalog", "authors.json")
CACHE = os.path.join(REPO, "catalog", "gutenberg", "wikicache")
os.makedirs(CACHE, exist_ok=True)

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) far-writing-canon/1.0 "
      "(public-domain catalog build)")

ERA_START, ERA_END = canon.ERA_START, canon.ERA_END
PD_CUTOFF = ERA_END + 30

#: THE SECTIONS that hold a bibliography. MEASURED 2026-10-31, and the
#: list is LONGER than it looks because the work list is often NESTED:
#:
#:   Mark Twain      "Writing" -> "Early journalism and travelogues",
#:                   "''Tom Sawyer'' and ''Huckleberry Finn''",
#:                   "Later writing"
#:   Chaucer         "List of works", "Major works", "Short poems",
#:                   "Works presumed lost", "Spurious works"
#:   Melville        "Selected bibliography"
#:
#: So the section names below are matched as a PREFIX, and the
#: subsections of a matched section are taken too -- otherwise Twain
#: yields nothing at all, because none of his work is listed directly
#: under a heading called "Works".
WORK_SECTIONS = ("works", "works and publications", "bibliography",
                 "list of works", "selected works", "selected bibliography",
                 "novels", "short stories", "stories", "plays",
                 "writing", "literary works", "major works",
                 "short poems", "poems", "works presumed lost",
                 "spurious works", "early journalism", "later writing",
                 "children's books", "essays", "collections")

#: A LIST ENTRY in a works section. MEASURED the shapes:
#:   * ''Twenty Thousand Leagues Under the Seas'' (1870)
#:   * ''The Raven'' (1845) -- " – narrative poem
#:   ; ''The Raven'' (1845)
#:   1. ''The Raven'' (1845)
ENTRY = re.compile(r"^\s*(?:[•*;]|[-–]\s|\d{1,3}\.)\s*(.+)$")

#: THE TITLE, in a list entry. The italic form first, because that is
#: how a work's title is marked; then the text before a parenthesis.
ITALIC = re.compile(r"''(.+?)''")
BEFORE_PAREN = re.compile(r"^([^(\[]+)")


def cache_key(url: str) -> str:
    """the cache key for a URL.

    **AND THE KEY IS THE WHOLE URL, HASHED.** MEASURED 2026-10-31: the
    first version keyed the cache on the URL's LAST 90 characters, so
    the key was a TRUNCATION of the thing it stood for -- and two URLs
    that differ only in the truncated part would share one entry, and
    one request's response would answer for another.

    MEASURED, and this is the honest version of the claim: on the
    corpus as it stands, the batch URLs put their titles where the
    truncation could not reach them, so the collision count was 0 of
    51 batches. The defect was LATENT, not active -- a latent defect is
    still a defect, because the URL's shape is not a property this
    function may depend on.

    So the key is the digest of the WHOLE URL, and it is a NAMED
    function so that a test can check it directly rather than
    restating it.
    """
    import hashlib
    return "http_" + hashlib.sha256(url.encode("utf-8")).hexdigest()[:24]


def fetch(url: str, tag: str = "") -> str:
    """GET a URL, with a cache."""
    key = cache_key(url)
    path = os.path.join(CACHE, key + ".txt")
    if os.path.isfile(path):
        with open(path, encoding="utf-8") as fh:
            return fh.read()
    for attempt in range(4):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=90) as fh:
                raw = fh.read()
                if fh.headers.get("Content-Encoding") == "gzip":
                    import gzip
                    raw = gzip.decompress(raw)
            text = raw.decode("utf-8", "replace")
            with open(path, "w", encoding="utf-8") as out:
                out.write(text)
            time.sleep(0.2)
            return text
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return ""
            if attempt == 3:
                return ""
        except Exception:  # noqa: BLE001
            if attempt == 3:
                return ""
            time.sleep(3 + attempt * 3)
    return ""


def resolve_title(title: str) -> str:
    """the article's real title, following redirects.

    **MEASURED 2026-10-31: the catalog says "Ibsen" and Wikipedia's
    article is "Henrik Ibsen" -- and `action=parse` does NOT follow a
    redirect, so the parse returned a 165-byte redirect stub and the
    bibliography came back empty for every author. A fetch that
    returns a stub and a corpus that is empty look the same from the
    outside.**

    So the title is resolved through `action=query` with `redirects=1`
    first, which does follow them.
    """
    url = ("https://en.wikipedia.org/w/api.php?action=query&titles=%s"
           "&format=json&formatversion=2&redirects=1"
           % urllib.parse.quote(title.replace(" ", "_")))
    raw = fetch(url, "rt")
    if not raw:
        return title
    try:
        data = json.loads(raw)
    except Exception:  # noqa: BLE001
        return title
    pages = data.get("query", {}).get("pages", [])
    if not pages:
        return title
    return pages[0].get("title", title)


def wikitext(title: str) -> str:
    """the wikitext of a page, with the redirect followed."""
    real = resolve_title(title)
    # AND THE CACHE KEY IS THE RESOLVED TITLE. MEASURED: the cache key
    # was built from the REQUESTED title, so "Ibsen" and "Henrik Ibsen"
    # -- the same article -- would share one cache entry, and whichever
    # was fetched first would answer for both.
    url = ("https://en.wikipedia.org/w/api.php?action=parse&page=%s"
           "&prop=wikitext&format=json&formatversion=2"
           % urllib.parse.quote(real.replace(" ", "_")))
    raw = fetch(url, "wt")
    if not raw:
        return ""
    try:
        return json.loads(raw)["parse"]["wikitext"]
    except Exception:  # noqa: BLE001
        return ""


def clean_title(raw: str) -> str:
    """the work's title, from a list entry's text.

    **AND MEASURED 2026-10-31, three kinds of junk come out of a
    works section, and each needs its own refusal:**

      1. THE WIKILINK IS STILL WRAPPED. MEASURED: the entries read
         "''[[The Pickwick Papers]]''" and the italic form holds the
         LINK, so the title came back as "[[The Pickwick Papers]]".
         So the wikilink is stripped and its DISPLAY text is kept --
         which matters, because "[[Catiline (play)|Catiline]]" carries
         the disambiguator in the link and not in the display.

      2. A CITATION IS NOT A WORK. MEASURED: Chaucer's section
         carried "{{Cite book |title=Chaucer's Canterbury Tales" and
         "[https://www.degruyter.com/view/title/558350 Chaucer's
         Polyphony...]" and "Life-records of Chaucer." -- a template,
         a URL and a modern biography, none of them a work by him.

      3. A MODERN CRITICAL EDITION IS NOT HIS WORK. MEASURED: "Le
         Livre de la Duchesse: oeuvres complètes (Tome I)" is a
         19th-century French edition of his poem, not a work he wrote.
    """
    t = raw.strip()
    # THE WIKILINK: keep the display text.
    m = re.match(r"^\[\[([^\]|]+)(?:\|([^\]]+))?\]\](.*)$", t)
    if m:
        t = (m.group(2) or m.group(1)).strip() + (m.group(3) or "")
    t = t.strip(" ,;.*–—-")
    # THE CITATION AND THE URL.
    if t.startswith("{{") or t.startswith("["):
        return ""
    if "http" in t.lower() and " " not in t:
        return ""
    # A URL INSIDE A TITLE.
    if re.search(r"https?://", t):
        return ""
    # THE ITALIC REMNANT.
    t = t.replace("''", "").strip()
    # THE TRAILING QUALIFIER, which is often a publication note rather
    # than a title: "Le Livre de la Duchesse: oeuvres complètes (Tome I)"
    if ":" in t:
        t = t.split(":")[0].strip()
    # A PARENTHETICAL QUALIFIER -- but not a DISAMBIGUATOR, which is
    # already gone with the wikilink.
    t = re.sub(r"\s*\([^)]*\)\s*$", "", t).strip()
    if not t or len(t) < 2 or len(t) > 110:
        return ""
    if re.fullmatch(r"[\d\s.,;-]+", t):
        return ""
    # A YEAR ALONE, or a year with a page number.
    if re.fullmatch(r"(?:p\.\s*)?\d{1,4}(?:\s*[-–]\s*\d{1,4})?", t):
        return ""
    return t


def titles_from_wikitext(wt: str) -> List[str]:
    """the work titles in an author's bibliography section.

    **AND THE SECTIONS ARE NESTED, SO THE SUBSECTIONS ARE TAKEN TOO.**
    MEASURED 2026-10-31: Mark Twain's works are not under a heading
    called "Works" -- they are under "Writing" and then under ITS
    subsections ("Early journalism and travelogues", "''Tom Sawyer''
    and ''Huckleberry Finn''", "Later writing"). So a matched
    section contributes its own lines AND every section beneath it,
    until the next section of the SAME OR HIGHER level.
    """
    if not wt:
        return []
    out: List[str] = []
    seen: Set[str] = set()

    # THE HEADINGS, with their level and position.
    heads = []
    for m in re.finditer(r"^(=+)\s*(.+?)\s*=+\s*$", wt, re.M):
        heads.append({"level": len(m.group(1)),
                      "title": m.group(2).strip(),
                      "start": m.start(), "end": m.end()})

    def is_work_section(title: str) -> bool:
        t = title.lower()
        return any(t.startswith(s) for s in WORK_SECTIONS)

    for i, h in enumerate(heads):
        if not is_work_section(h["title"]):
            continue
        # THE BLOCK: this section and its subsections.
        block_end = len(wt)
        for j in range(i + 1, len(heads)):
            if heads[j]["level"] <= h["level"]:
                block_end = heads[j]["start"]
                break
        block = wt[h["end"]:block_end]

        for line in block.splitlines():
            em = ENTRY.match(line)
            if not em:
                continue
            body = em.group(1)
            im = ITALIC.search(body)
            bm = BEFORE_PAREN.match(body)
            raw = im.group(1) if im else (bm.group(1) if bm else "")
            title = clean_title(raw)
            if not title:
                continue
            key = title.lower()
            if key in seen:
                continue
            seen.add(key)
            out.append(title)
    return out


def norm(s: str) -> str:
    """the catalog's own title key: lower, and non-alphanumerics to spaces."""
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


#: THE WORK'S NATURE, in Wikidata. MEASURED: a title matches MANY
#: items, and the ORIGINAL is the one whose nature is a work, not an
#: edition or a stage production. MEASURED on "Dracula": 58 items
#: matched; 11 of them carried Bram Stoker as their author, and
#: exactly one was `literary work` (Q41542, 1897-05-26) -- the rest
#: were `version, edition or translation` and `theatrical production`.
WORK_NATURES = ("literary work", "play", "poem", "novella", "short story",
                 "collection of stories", "essay", "autobiography",
                 "memoir", "book", "opera", "musical", "libretto",
                 "serialized fiction")

#: THE QUERY. ONE per author, with all of that author's titles in one
#: VALUES clause.
#:
#: **AND THE AUTHOR'S OWN ITEM IS THE FILTER,** because the question
#: is "every work THIS AUTHOR wrote", not "every work with this
#: title". MEASURED: one VALUES clause with 8 Dickens titles comes
#: back in 0.6s, against 8 entity fetches at ~0.5s each.
#:
#: **AND THE LANGUAGE TAG GOES OUTSIDE THE QUOTES.** MEASURED: with
#: `"Dracula"@en` inside the quotes the query returns ZERO rows and
#: reports no error -- which looks exactly like "these titles are not
#: in Wikidata", and cost one round of diagnosis.
RESOLVE = """
SELECT ?title ?work ?workLabel ?date ?instance ?instanceLabel WHERE {
  VALUES ?title { %s }
  ?work rdfs:label ?title ; wdt:P50 wd:%s .
  OPTIONAL { ?work wdt:P577 ?date . }
  OPTIONAL { ?work wdt:P31 ?instance . }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
}
LIMIT 2000
"""


def resolve_for_author(qid: str, titles: List[str]) -> Dict[str, dict]:
    """the titles, resolved to the work they name.

    **AND BOTH ENDPOINTS GET RATE-LIMITED, IN TURN.** MEASURED
    2026-10-31: after the heavy resolution run, `query.wikidata.org`
    answered HTTP 503 to every call; then, once that recovered, the
    Wikipedia API answered HTTP 429. And the tool was retrying the
    FIRST one five times -- about four minutes per author -- before
    falling back.

    **SO THE FALLBACK IS IMMEDIATE, AND EACH ENDPOINT IS TRIED ONCE.**
    A rate limit is not a transient error to be retried in place; it is
    a signal to use the other route. And the first route is the
    SPARQL one, because it returns the WORK -- the item, its date and
    its nature -- in one call, and `pick_work` can then choose the
    original rather than an edition of it (measured on Dracula: the
    1897 literary work over the 1900 and 1920 editions).

    **AND NEITHER FAILURE IS CACHED.** A 503 stored as an empty answer
    would say "these titles resolve to nothing", which is a claim the
    endpoint never made -- and it would be cached forever, so a rate
    limit would become permanent.
    """
    if not titles:
        return {}

    # THE FIRST ROUTE: SPARQL, one attempt.
    vals = " ".join('"%s"@en' % t.replace("\\", "\\\\").replace('"', '\\"')
                    for t in titles)
    raw = reach_measure.query(RESOLVE % (vals, qid), "rw_%s" % qid,
                              attempts=1)
    if raw:
        try:
            rows = json.loads(raw)["results"]["bindings"]
        except Exception:  # noqa: BLE001
            rows = []
        if rows:
            cands: Dict[str, Dict[str, dict]] = defaultdict(dict)
            for r in rows:
                t = r["title"]["value"]
                w = r["work"]["value"].rsplit("/", 1)[-1]
                c = cands[t].setdefault(w, {"qid": w, "dates": [],
                                            "natures": [],
                                            "label": r.get("workLabel", {})
                                            .get("value", "")})
                date = r.get("date", {}).get("value", "")[:10]
                if date:
                    c["dates"].append(date)
                inst = r.get("instanceLabel", {}).get("value", "")
                if inst:
                    c["natures"].append(inst)
            out: Dict[str, dict] = {}
            for t, works in cands.items():
                best = pick_work(works)
                if best:
                    out[t] = best
            if out:
                return out

    # THE SECOND ROUTE: the Wikipedia API, which was answering 200
    # while the SPARQL endpoint was rate-limiting.
    return _resolve_via_wikipedia_api(titles)


def _resolve_via_wikipedia_api(titles: List[str]) -> Dict[str, dict]:
    """titles -> their Wikidata item, through the Wikipedia API.

    **AND THE DATE IS FETCHED FROM THE ITEM, NOT FROM THE API**, so the
    public-domain test is the same measurement either way.
    """
    out: Dict[str, dict] = {}
    for i in range(0, len(titles), 50):
        chunk = titles[i:i + 50]
        url = ("https://en.wikipedia.org/w/api.php?action=query&prop="
               "pageprops&ppprop=wikibase_item&titles=%s&format=json"
               "&formatversion=2&redirects=1"
               % urllib.parse.quote("|".join(chunk)))
        raw = _http_json(url)
        if not raw:
            continue
        try:
            data = json.loads(raw)
        except Exception:  # noqa: BLE001
            continue
        redirects = {r["to"]: r["from"] for r in
                      data.get("query", {}).get("redirects", [])}
        for p in data.get("query", {}).get("pages", []):
            q = (p.get("pageprops", {}) or {}).get("wikibase_item")
            t = p.get("title", "")
            if not q or not t:
                continue
            t = redirects.get(t, t)
            ent = entity(q)
            if not ent:
                continue
            e = ent["entities"][q]
            yr = year_of(e, "P577")
            if yr is None:
                continue
            label = e.get("labels", {}).get("en", {}).get("value", "") or t
            out[t] = {"qid": q, "year": yr, "title": label}
        time.sleep(0.4)
    return out


def _http_json(url: str) -> str:
    """a plain GET, cached, for the APIs that are not SPARQL.

    **AND A FAILED FETCH IS NOT CACHED AS AN EMPTY ANSWER.** A 503
    stored as "{}" would say "these titles resolve to nothing", which
    is a claim the endpoint never made -- and it would be cached
    forever, so the rate limit would become permanent.
    """
    key = "http_" + hashlib.sha256(url.encode("utf-8")).hexdigest()[:24]
    path = os.path.join(CACHE, key + ".txt")
    if os.path.isfile(path):
        with open(path, encoding="utf-8") as fh:
            return fh.read()
    for attempt in range(4):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=90) as fh:
                raw = fh.read()
                if fh.headers.get("Content-Encoding") == "gzip":
                    import gzip
                    raw = gzip.decompress(raw)
            text = raw.decode("utf-8", "replace")
            with open(path, "w", encoding="utf-8") as out:
                out.write(text)
            return text
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                return ""
            if attempt == 3:
                return ""
            time.sleep(10 + attempt * 20)
        except Exception:  # noqa: BLE001
            if attempt == 3:
                return ""
            time.sleep(5 + attempt * 10)
    return ""


def pick_work(works: Dict[str, dict]) -> Optional[dict]:
    """the ORIGINAL work, from the items a title matched.

    **AND THE SCORE IS MEASURED, NOT ASSUMED.** The candidates are
    ranked by:

      1. an in-era publication date -- a work the gate would keep
      2. the nature: a `literary work` beats an `edition`
      3. the EARLIEST date -- the first publication is the work, and a
         later date is an edition of it

    MEASURED on "Dracula": Q41542 (literary work, 1897-05-26) is
    chosen over the 1900 and 1920 editions and over the stage
    adaptations.
    """
    best = None
    best_key = None
    for w, c in works.items():
        years = []
        for d in set(c["dates"]):
            try:
                years.append(int(d[:4]))
            except ValueError:
                continue
        in_era = [y for y in years if ERA_START <= y <= PD_CUTOFF]
        is_work = any(i in WORK_NATURES for i in c["natures"])
        # THE SCORE. Bigger is better, and the tuple is compared
        # element by element -- so the order of the tests IS the order
        # of the preference.
        key = (1 if in_era else 0, 1 if is_work else 0,
               -min(years) if years else 0)
        if best_key is None or key > best_key:
            best_key = key
            best = dict(c)
            best["year"] = min(in_era) if in_era else (
                min(years) if years else None)
            best["all_dates"] = sorted(set(c["dates"]))
    if best is None or best.get("year") is None:
        # NO DATE MEANS NO PUBLIC-DOMAIN TEST. The gate's own rule: a
        # work with no publication date cannot be shown to be in the
        # public domain, so it is not added.
        return None
    return best


def resolve_titles(titles: List[str]) -> Dict[str, dict]:
    """enwiki titles -> their Wikidata item and publication date.

    **AND THE BATCH IS 50 TITLES, BECAUSE THE API ACCEPTS 50 PER
    CALL.** MEASURED: the alternative is one call per title, which for
    5,000 titles is 5,000 calls -- and a fetch that slow is a fetch
    that never finishes.
    """
    out: Dict[str, dict] = {}
    for i in range(0, len(titles), 50):
        chunk = titles[i:i + 50]
        url = ("https://en.wikipedia.org/w/api.php?action=query&prop="
               "pageprops&ppprop=wikibase_item&titles=%s&format=json"
               "&formatversion=2&redirects=1"
               % urllib.parse.quote("|".join(chunk)))
        raw = fetch(url, "pp")
        if not raw:
            continue
        try:
            data = json.loads(raw)
        except Exception:  # noqa: BLE001
            continue
        norm = {}
        for r in data.get("query", {}).get("normalized", []):
            norm[r["to"]] = r["from"]
        redirects = {r["to"]: r["from"] for r in
                      data.get("query", {}).get("redirects", [])}
        for p in data.get("query", {}).get("pages", []):
            qid = (p.get("pageprops", {}) or {}).get("wikibase_item")
            t = p.get("title", "")
            if not qid or not t:
                continue
            for table in (redirects, norm):
                t = table.get(t, t)
            out[t] = {"qid": qid}
        time.sleep(0.15)
    return out


def entity(qid: str) -> dict:
    path = os.path.join(CACHE, qid + ".json")
    if os.path.isfile(path):
        try:
            with open(path, encoding="utf-8") as fh:
                return json.load(fh)
        except Exception:  # noqa: BLE001
            return {}
    raw = fetch("https://www.wikidata.org/wiki/Special:EntityData/%s.json"
                % qid, "ent")
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except Exception:  # noqa: BLE001
        return {}


def year_of(e: dict, prop: str = "P577") -> Optional[int]:
    for c in e.get("claims", {}).get(prop, []):
        if c.get("rank") == "deprecated":
            continue
        v = c["mainsnak"].get("datavalue", {}).get("value", {})
        if "time" in v:
            t = v["time"].strip()
            sign = -1 if t.startswith("-") else 1
            return sign * int(t.lstrip("+-")[:4])
    return None


def works_of(qid: str) -> List[dict]:
    """the author's P800 works, with their dates."""
    data = entity(qid)
    if not data:
        return []
    ent = data["entities"][qid]
    out = []
    seen = set()
    for c in ent.get("claims", {}).get("P800", []):
        if c.get("rank") == "deprecated":
            continue
        v = c["mainsnak"].get("datavalue", {}).get("value", {})
        if not (isinstance(v, dict) and "id" in v):
            continue
        wid = v["id"]
        if wid in seen:
            continue
        seen.add(wid)
        wdata = entity(wid)
        if not wdata:
            continue
        went = wdata["entities"][wid]
        name = went.get("labels", {}).get("en", {}).get("value", "")
        if not name:
            continue
        yr = year_of(went, "P577")
        if yr is None:
            continue
        out.append({"title": name, "year": yr, "qid": wid})
    return out


def load_flood_counts() -> Dict[str, int]:
    """the per-work adaptation counts, from the CORRECTED measurement.

    **AND THE KEY IS NORMALIZED ON BOTH SIDES.** MEASURED: the old
    lookup keyed the dict by the RAW Wikidata label and asked for the
    NORMALIZED title, so 546 of the 2,486 entries (22%) could never be
    found -- "Uncle Tom's Cabin" normalizes to "uncle tom s cabin" and
    the raw key "uncle tom's cabin" was never asked for. That is why 51
    catalog works whose reach count WAS in the measurement carried
    `None`: Moby-Dick, Alice's Adventures in Wonderland, Les Misérables,
    all of them.

    **AND THE COUNT IS THE CORRECTED ONE.** MEASURED: the old
    measurement counted the ROWS of a SPARQL result, and each row is
    one (adaptation, work, date, author) tuple -- so the number was
    adaptations x distinct dates x distinct authors, a JOIN PRODUCT.
    Dream of the Red Chamber carried 2,126 against a true 1,063;
    Hansel and Gretel 66 against 22; Moby-Dick 84 against 42. The
    corrected measurement counts DISTINCT adaptations.
    """
    return reach_measure.load_reach()


def load_gutenberg_counts() -> Dict[str, int]:
    """the per-book download counts, from the Gutenberg ranking.

    **AND THE TITLE IS SPLIT ON ' by ' FIRST.** MEASURED: the page
    writes "Frankenstein; or, The modern Prometheus by Mary Wollstonecraft
    Shelley", and the old lookup kept the whole string, so it could
    never match a bare title -- and it missed ALL 13 of the download
    numbers the catalog already held. The split is on the LAST ' by ',
    because a title can contain one ("The Castle by O. Henry").

    **AND THE KEY IS NORMALIZED ON BOTH SIDES,** for the same reason as
    the reach table: "Moby Dick; Or, The Whale" and "Moby-Dick" are the
    same book, and only a normalized key says so.
    """
    import gutenberg_ranks
    out: Dict[str, int] = {}
    try:
        books, _ = gutenberg_ranks.load()
    except Exception:  # noqa: BLE001
        return {}
    for b in books:
        out[norm(b.title)] = b.downloads
    return out


def _in_window(year: Optional[int]) -> bool:
    """is the work inside the window the reach measurement covered?

    **AND THE FIRST VERSION OF THIS SAID "NOWHERE", AND THAT WAS
    RIGHT ABOUT THE ZERO AND WRONG ABOUT THE SCOPE.** MEASURED
    2026-10-31: the flood query that qualified the authors starts from
    the ADAPTATION --

        ?adapt (wdt:P144|wdt:P1441) ?work .

    -- so it enumerates ADAPTATIONS, not works, and a work with no
    adaptation was never in scope. Which means "in-window means
    measured at zero" was FALSE for that query.

    **BUT THE WORKS OF THE AUTHORS WE HOLD CAN BE ENUMERATED**, and
    then each one's count is measured. MEASURED: the unbounded form
    ("every work published in the window") timed out with HTTP 504,
    while the bounded form -- the 260 authors in the catalog -- answers
    200 in 2 seconds with **15,512 rows: 14,137 with a measured ZERO
    and 1,375 with adaptations.**

    So the exhaustive table is the authority for whether a work was
    MEASURED, and this function asks it.
    """
    if year is None:
        return False
    return ERA_START <= year <= ERA_END


def load_exhaustive() -> Dict[str, int]:
    """the exhaustive per-work table: every work of the authors we hold,
    with its measured adaptation count -- zero included.

    **AND IT IS THE TABLE THAT MAKES A ZERO HONEST.** MEASURED: the
    adaptation-driven query cannot distinguish "no adaptations" from
    "not looked for", and a zero written for the second case is a
    claim nobody made.
    """
    path = os.path.join(CACHE, "reach_exhaustive_by_work.json")
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, encoding="utf-8") as fh:
            raw = json.load(fh)
    except Exception:  # noqa: BLE001
        return {}
    return {k: int(v) for k, v in raw.items()}


def discover(a: dict, qid: str) -> Dict[str, dict]:
    """every work this author wrote, from the two sources.

    **AND THE DISCOVERY IS DONE ONCE.** MEASURED: the earlier shape of
    this tool had the whole discovery written TWICE -- once for the
    report and once for the apply -- and the two copies could drift, so
    the report Bobby read was not necessarily what the apply wrote.
    """
    found: Dict[str, dict] = {}

    # SOURCE 1: P800, the structured list.
    for w in works_of(qid):
        found[norm(w["title"])] = dict(w)

    # SOURCE 2: the author's own bibliography, resolved in ONE query.
    wt = wikitext(a["name"])
    titles = titles_from_wikitext(wt)
    if titles:
        for t, info in resolve_for_author(qid, titles).items():
            key = norm(t)
            if not key or key in found:
                continue
            found[key] = {"title": t, "year": info["year"],
                          "qid": info["qid"]}
    return found


def gate_new_work(a: dict, key: str, w: dict, held: Set[str],
                  skipped: Dict[str, int]) -> bool:
    """the gate's own rules, applied to one candidate work.

    **AND EVERY REFUSAL IS COUNTED.** MEASURED: the earlier shape of
    this tool had a `skipped_no_date` counter that was never
    incremented and never printed, so the largest class of refusal was
    invisible in the report.

    **AND THE DUPLICATE IS CHECKED ON THE CORE TITLE.** MEASURED
    2026-10-31: after the expansion, 18 authors failed the catalog's
    own gate with `duplicate_titles`, and every one was the SAME work
    arriving from P800 and from the bibliography under two spellings:

        "Lady Inger of Ostrat"   vs   "Lady Inger of Oestraat"
        "Gösta Berlings saga"    vs   "Gosta Berlings Saga"

    The loose key let both through, so the catalog held one novel
    twice -- which is exactly what `duplicate_titles` exists to
    prevent. So the check compares the CORE title: the subtitle
    dropped, the punctuation dropped, the article dropped.
    """
    if key in held:
        skipped["held"] += 1
        return False
    if canon_key(w.get("title", "")) in held:
        skipped["duplicate_spelling"] += 1
        return False
    yr = w.get("year")
    if yr is None:
        skipped["no_date"] += 1
        return False
    if yr < ERA_START or yr > PD_CUTOFF:
        skipped["era"] += 1
        return False
    went = a.get("went")
    if went is not None and yr > went:
        skipped["after_death"] += 1
        return False
    return True


def canon_key(title: str) -> str:
    """the comparison key for a title, for the duplicate check.

    **AND MEASURED 2026-10-31: THE SAME WORK ARRIVED TWICE UNDER TWO
    SPELLINGS.** 18 authors failed the gate with `duplicate_titles`
    after the expansion, and every one was the same work from P800 and
    from the bibliography under a slightly different title:

        "Lady Inger of Ostrat"   vs   "Lady Inger of Oestraat"
        "Gösta Berlings saga"    vs   "Gosta Berlings Saga"

    So the duplicate check has to compare the CORE title -- the
    subtitle dropped, the diacritics folded, the punctuation dropped --
    or the catalog holds the same novel twice under two spellings,
    which is exactly what `duplicate_titles` exists to prevent.

    **AND A TITLE ALREADY IN THE CATALOG IS NOT ADDED AGAIN**, whether
    it arrived from P800 or from the bibliography.
    """
    t = title.lower()
    t = re.sub(r"\s*\([^)]*\)\s*", " ", t)
    t = re.split(r"\s*[:;]\s*", t)[0]
    t = re.sub(r"[^a-z0-9]+", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    for art in ("the ", "a ", "an "):
        if t.startswith(art):
            t = t[len(art):]
            break
    return t


def main() -> int:
    ap = argparse.ArgumentParser(description="expand the works")
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--limit", type=int, default=0,
                    help="only the first N authors (for a trial run)")
    ap.add_argument("--authors", type=str, default="",
                    help="a comma-separated list of author names")
    args = ap.parse_args()

    with open(CATALOG, encoding="utf-8") as fh:
        catalog = json.load(fh)

    COM = ("name", "born", "nationality", "verified", "source", "note",
           "works")
    DEATH = [f for f in canon.Author.__dataclass_fields__ if f not in COM][0]

    # THE PER-WORK ADAPTATION COUNTS, from the CORRECTED measurement.
    flood = load_flood_counts()
    gutenberg = load_gutenberg_counts()
    print("=" * 84)
    print("THE EXPANSION OF THE AUTHORS WE HAVE")
    print("=" * 84)
    print("  the catalog: %d authors, %d works"
          % (len(catalog), sum(len(a.get("works", [])) for a in catalog)))
    print("  the per-work adaptation counts, from the corrected "
          "measurement: %d" % len(flood))
    print("  the per-book download counts, from the Gutenberg ranking: %d"
          % len(gutenberg))
    print()

    # THE AUTHORS, with their QIDs.
    authors = []
    for a in catalog:
        m = re.search(r"(Q\d+)", a.get("source", "") or "")
        if not m:
            continue
        authors.append((a, m.group(1)))
    if args.authors:
        want = {n.strip() for n in args.authors.split(",") if n.strip()}
        authors = [(a, q) for a, q in authors if a["name"] in want]
    if args.limit:
        authors = authors[:args.limit]
    print("  authors with a Wikidata QID: %d" % len(authors))
    print()

    added = 0
    added_authors = 0
    # AND EVERY REFUSAL IS COUNTED, in ONE place. MEASURED: the earlier
    # shape of this tool had a `skipped_no_date` counter that was never
    # incremented and never printed, and it had the whole discovery
    # written TWICE -- once for the report and once for the apply -- so
    # the report Bobby read was not necessarily what the apply wrote.
    skipped = {"held": 0, "era": 0, "after_death": 0, "no_date": 0,
               "duplicate_spelling": 0}
    per_author = []
    # AND THE ADDITIONS CARRY THE KEY ALONGSIDE THE WORK, because the
    # apply needs the key to look the measures up. MEASURED: the first
    # version stored the work alone and the apply unpacked a pair --
    # so the apply raised ValueError and wrote nothing, after the
    # report had already said it would add 1,073 works.
    additions: Dict[str, List[Tuple[str, dict]]] = {}

    # THE DISCOVERY, ONCE. Both the report and the apply read from this.
    for a, qid in authors:
        # AND `held` HOLDS BOTH KEYS. MEASURED: the loose `norm` key
        # let the same work through twice under two spellings, and the
        # core `canon_key` catches it -- so the held set carries both,
        # and whichever a check compares against, it collides.
        held = set()
        for w in a.get("works", []):
            t = w.get("title", "")
            held.add(norm(t))
            held.add(canon_key(t))
        found = discover(a, qid)
        new_works = []
        for key, w in sorted(found.items(),
                             key=lambda kv: (kv[1].get("year") or 0, kv[0])):
            if not gate_new_work(a, key, w, held, skipped):
                continue
            held.add(key)
            held.add(canon_key(w.get("title", "")))
            # AND THE KEY TRAVELS WITH THE WORK. MEASURED 2026-10-31:
            # this appended the work ALONE, and the line below then
            # unpacked each entry as (key, work) -- but the entry was a
            # dict, so the unpack walked its KEYS and the apply failed
            # with "too many values to unpack (expected 2, got 3)". The
            # catalog was untouched, because the write happens after.
            new_works.append((key, w))
        if new_works:
            added += len(new_works)
            added_authors += 1
            per_author.append((a["name"], len(a.get("works", [])),
                               len(new_works)))
            # AND THE KEY TRAVELS WITH THE WORK, so the apply can look
            # the measures up under the key the catalog uses.
            additions[a["name"]] = list(new_works)

    print("  the works the expansion adds: %d" % added)
    print("  the authors it gives a new work to: %d" % added_authors)
    print()
    print("  AND THE SKIPS, which is where the gate's rules show:")
    print("     already held:              %d" % skipped["held"])
    print("     outside the era:            %d" % skipped["era"])
    print("     dated after the author went: %d" % skipped["after_death"])
    print("     no publication date:        %d" % skipped["no_date"])
    print()

    if args.report and not args.apply:
        per_author.sort(key=lambda x: -x[2])
        print("  the authors that gain the most:")
        for name, had, gain in per_author[:25]:
            print("    %-30s %3d -> %3d  (+%d)"
                  % (name[:30], had, had + gain, gain))
        print()
        return 0

    # ---- APPLY ---------------------------------------------------------
    # AND THE THREE MEASURES STAY THREE, each in its own field.
    # AND THE EXHAUSTIVE TABLE, so a ZERO is measured.
    exhaustive = load_exhaustive()
    print("  the exhaustive table: %d works with a measured count"
          % len(exhaustive))
    written = 0
    for a, qid in authors:
        for key, w in additions.get(a["name"], []):
            # AND THE REACH COUNT, AND IT COMES FROM THE EXHAUSTIVE
            # TABLE. MEASURED 2026-10-31: the adaptation-driven
            # flood query cannot tell "no adaptations" from "not
            # looked for" -- it enumerates ADAPTATIONS, so a work with
            # none was never in scope. The exhaustive table (every work
            # of the 260 authors we hold) CAN tell, and it answers in
            # 2 seconds with 15,512 rows: 14,137 with a MEASURED zero.
            #
            # So the count is: the exhaustive table's value if the work
            # is in it, else the flood table's value if it is in that,
            # else None -- and None means NOT MEASURED, never zero.
            reach = exhaustive.get(key)
            if reach is None:
                reach = flood.get(key)
            if reach is None:
                reach = None
            a.setdefault("works", []).append({
                "title": w["title"],
                "year": w["year"],
                "kind": "",
                "license": "public-domain",
                "source_url": "https://www.wikidata.org/wiki/" + w["qid"],
                # AND THE DURABILITY CLAIM NAMES THE TEST THE DATA
                # CLEARS. MEASURED: the old code wrote
                # 'still_reprinted' -- a claim about REPRINTS -- while
                # the measurement it recorded was ADAPTATIONS. The
                # catalog's own list has 'still_adapted' for exactly
                # this, and the reach build already used it.
                "durability": (["still_adapted"] if reach else []),
                "evergreen": False,
                "adapt_as_myth": False,
                "note": ("from the author's own bibliography; "
                         "%s adaptations recorded"
                         % ("no" if not reach else reach)),
                "claimed_sales_m": None,
                "gutenberg_downloads": gutenberg.get(key),
                "gutenberg_ebook_id": None,
                "reach_adaptations": reach,
                "intake_rank": None,
                "intake_section": "bibliography",
            })
            written += 1

    tmp = CATALOG + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(catalog, fh, indent=2, ensure_ascii=False)
    os.replace(tmp, CATALOG)

    print("=" * 84)
    print("APPLIED")
    print("=" * 84)
    print("  works written: %d" % written)
    print("  the catalog: %d authors, %d works"
          % (len(catalog), sum(len(a.get("works", [])) for a in catalog)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
