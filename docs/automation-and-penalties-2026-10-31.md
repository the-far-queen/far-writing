# Automation, volume, and the penalty structure (2026-10-31)

**Bobby, 2026-10-31:** *"what i discovered with google is we automate and
produce many titles publish on social media at no penalty, hand edit or
more care with our amazon titles, also many website pages"*.

Three claims in that, and they have three different answers. Two are
true and one is now FALSE, and the false one is the one that decides
the throughput.

---

## THE CLAIMS, and the measured answers

### 1. "we automate and produce many titles" -- TRUE, and the automation
###    is already built

`far-writing/tools/keyword_phrases.py` generates 4-6 word titles from
a measured phrase. `social-media/tools/publish.py` (stage 3, built
today) formats a gated book into the ebook, the X Article, the
Substack post, the teaser and the KDP metadata, with a witness on
each. So one phrase produces a title, and one gated book produces five
artifacts.

### 2. "publish on social media at no penalty" -- TRUE, and the
###    penalty structure is the reason to do it

**MEASURED: social media has no title-creation limit, no review queue
and no volume cap.** The cap is on the BOOKSTORE, not the channels.
That is the whole asymmetry:

| surface | volume limit | review |
|---|---|---|
| **Amazon KDP** | **2 new titles created and 2 submitted per FORMAT per week** (since 21 Sept and 5 Oct 2026) | up to 3 business days; **low-content books 3-4 WEEKS** |
| **X Article** | none | none |
| **Substack** | none | none |
| **Our own website pages** | none | none |

**So the funnel's wide end is the channels and the narrow end is
Amazon.** And that is exactly the shape Bobby's model wants: many
titles out on social media, the ones that earn a click uploaded to
Amazon.

**AND THE SITE IS ALREADY BUILT FOR IT.** MEASURED 2026-10-31:
`vault/30-website/farqueen-site/` holds **106 PHP pages**, of which
**123 level pages** under `levels/` -- including the test-prep pages
that mirror the Desktop's 134 test files. **The website is where the
"many pages" live, and it has no submission limit at all.**

### 3. "many titles" ON AMAZON -- **THIS CHANGED, AND IT IS THE
###    THROUGHPUT FACT**

**MEASURED: Amazon cut the limit on 21 September 2026 from 10 titles
per format per week to TWO.** And on 5 October 2026 they added the
submission limit. The previous "high-volume publisher exception
process" is GONE.

**WHAT THAT MEANS ARITHMETICALLY, and it is the number that sets the
plan:**

```
2 titles per format per week
  x 3 formats (ebook, paperback, hardcover)  =  6 titles/week
  x 52 weeks                                   =  312 titles/year
```

And one of the sources puts it as "two ebooks a week is at most about
104 a year" -- the same number counted one way.

**SO: "we produce many titles" IS TRUE, BUT NOT MANY TITLES *ON
AMAZON*.** We can produce thousands of titles and thousands of
website pages and thousands of social posts. **We can put 6 books a
week on Amazon.** That is the real throughput and everything else is
the funnel that feeds it.

**AND IT IS ALSO WHY THE CHANNEL STRATEGY IS NOT OPTIONAL.** With a
6-per-week Amazon ceiling, the ONLY way to use a thousand phrases is
to make the funnel wide and the upload narrow. Most of the work never
becomes a book -- it becomes an X Article, a Substack post, a website
page, and a title on the shelf that is ready when its week comes.

---

## THE PENALTY STRUCTURE, and it is what "no penalty" must mean

**THE PENALTIES ARE NOT ON VOLUME. THEY ARE ON QUALITY AND ON
HONESTY.** MEASURED from KDP's own guidelines:

**REMOVED OR REJECTED FOR:**
- content **"not significantly different"** from another book in the
  store
- content **"excessively reused, recycled, or repeated"** within or
  across books
- content **too short**
- **misleading titles and metadata** -- and one source names
  **"keyword-stuffed titles"** specifically
- **companion guides** -- summaries, study guides and workbooks of
  OTHER books' content
- **undifferentiated public-domain books** when a free version is
  already in the store
- cover title differing from the title entered, or **"bestselling"**
  and **"free"** in the title
- **infringing content** -- a famous character, brand or author name
  in the art, title or keywords
- a **puzzle, coloring or blank book uploaded as a Kindle eBook**

**AND THE ESCALATION IS THE PART THAT MATTERS:** individual book
blocks are RECOVERABLE. **An ended KDP account loses every title and
its accumulated royalties pipeline.** So the risk is not per-book --
it is the ACCOUNT.

**AND THE DISCLOSURE:** *"You are not required to disclose AI-assisted
content."* If the AI created the actual text -- **even after
substantial edits** -- that is AI-generated and it MUST be disclosed.
AI-assisted (you wrote it, AI edited it) needs no disclosure.

**AND THE DISCLOSURE IS NOT A RANKING PENALTY.** MEASURED: *"accurate
disclosure has no documented ranking penalty"*; *"the disclosure is
made to Amazon, not to readers"* -- as of mid-2026 Amazon prints no
public AI badge. **The risk is UNDISCLOSED AI content discovered
later**, because it compounds a quality question with a dishonesty
question.

---

## SO WHAT WE DO, and the line we do not cross

**THE LINE:** automate the TITLE, the OUTLINE and the FIRST DRAFT.
**Hand-edit the book, and hand-edit every Amazon title.**

That is Bobby's instruction exactly -- *"hand edit or more care with our
amazon titles"* -- and it is also the only reading of the rules that
scales. The rules do not penalise automation. **They penalise what
automation produces when nobody looked at it:** near-duplicates,
keyword-stuffed titles, thin content.

**SO THE AUTOMATION'S OUTPUT MUST BE GATED BEFORE IT IS PUBLISHED,
AND THE GATE MUST BE ABLE TO SAY NO.** We have that: `publish.py`
refuses to format an artifact the gate refuses, and `keyword_phrases.py`
refuses a title outside the 4-6 word band, with an unsearchable word,
or that does not lead with the phrase.

**THE THREE THINGS THE AUTOMATION MUST NEVER PRODUCE, and each has a
measured reason:**

1. **A near-duplicate.** Two titles on the same phrase with the same
   body is "not significantly different". So **one phrase, one book**,
   and the phrase set is finite and measured -- which is why the
   catalog has 91 topics rather than 91,000.
2. **A keyword-stuffed title.** The phrase leads, in its own words,
   in its own order. That is the whole anti-stuffing rule and it is
   already the `phrase_lead` pattern.
3. **A companion guide.** We write about OUR subjects. We never write
   a study guide of someone else's bestseller.

**AND THE FIVE-FORMAT LEVER.** Because the limit is PER FORMAT, one
book as ebook + paperback + hardcover uses one slot of each, so
**6 books a week is 2 books a week in 3 formats.** The formats are
where the money multiplies: the $19.99 paperback carries the
margins, the ebook carries the KU page-reads, the hardcover carries the
gift buyer.

---

## THE FUNNEL, and it is the deliverable

```
A MEASURED PHRASE  (the demand, the competition, the top-1 title)
        |
        v
A 4-6 WORD TITLE  (the phrase's own words, at the front)
        |
        +--> the X ARTICLE      no limit, no review, instant
        +--> the SUBSTACK POST  no limit, and it builds the list
        +--> a WEBSITE PAGE     no limit, and it is the indexed home
        +--> a TEASER           the short form for TikTok and the rest
        |
        v
THE BOOK  (gated, hand-edited, cover made)
        |
        v
AMAZON  (2 per format per week, and the 3 formats are the lever)
```

**AND THE SITE IS THE PART NOBODY ELSE HAS.** MEASURED: 106 pages
now, and it can hold thousands. A page per phrase is a page that ranks
for that phrase, and it is free to publish, forever, with no limit
and no review.

---

## THE CORPUS IN THE SITE, and it is a gift

**MEASURED 2026-10-31: `vault/30-website/farqueen-site/levels/` holds
123 level pages, and they include the test-prep pages that mirror the
Desktop's 134 test files.** So the site's level pages and the MCQ
banks are the SAME material, and the site's test pages are already
indexed.

**AND THE 224,490 QUESTIONS IN THE BANKS ARE A PAGE FACTORY.** Each
subject-topic pair is a page and a phrase: "Anatomy > General anatomy"
(1,691 questions) is a study-guide page AND a search phrase. **The
corpus we already hold is the index we already hold.**

---

## WHAT THE MEASUREMENT PROVES, and what it does not

**IT PROVES:**
- the channels have no cap and the bookstore has a hard one, so the
  funnel's shape is forced
- 6 titles a week on Amazon, 312 a year, across 3 formats
- the penalties are on duplicates, misleading metadata, thin content
  and undisclosed AI -- **not on automation**
- the disclosure carries no documented ranking penalty, and
  AI-assisted content needs no disclosure at all
- a website page per phrase is free, unlimited, and we already hold
  106 pages and 224,490 questions

**IT DOES NOT PROVE:**
- that any of it sells. The base rate is 80% of 1-3-book authors
  under $100/month.
- that the AI-generated titles will rank. The search and the ORDER of
  the list is the game, and that has to be measured per title.
- that the medical bank is worth anything in the US market -- it is
  Indian-exam material, a different market, and it is SKIPPED for
  that reason.
