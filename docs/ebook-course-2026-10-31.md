# The ebook course: keyword phrases, categories, and the lexical game (2026-10-31)

**Bobby's directives, 2026-10-31:**
*"this keyword phrase work is central not just in academia. make notes in
far-writing: categories of a bookstore first, then which are amenable to
keyword phrases, 4-6 word titles"*, *"reason who would buy a book and why.
skip law and medicine"*, *"highest match keyword must go first it is a
lexical game"*, *"quality of cover but search and order of list results is
the game"*, *"as book seller i know keyword phrases beat great stories.
no one searches for ie. amazon is a search engine"*, *"we write self help
in voice of public domain old authors who were good at storytelling and
communication"*, *"i love nic vujic and tony robbins success nlp self
help"*, and *"we will publish a course in ebook writing"*.

**The machine-readable catalog:** `catalog/keyword_phrases.json`.
**The tool:** `tools/keyword_phrases.py`.
**The checks:** `tests/test_keyword_phrases.py` (47 pass).

---

## THE THREE LAYERS, and the order is fixed

```
1. THE CATEGORY   the bookstore's department.        THE AXIS
2. THE PHRASE     what the buyer TYPES.              THE UNIT
3. THE TITLE      4-6 words, built from the phrase.   THE OUTPUT
```

**The title is not chosen and then searched for. The title is BUILT
from the phrase, and the phrase is chosen from the category.**

**AND THE PHRASE LEADS.** *"highest match keyword must go first it is
a lexical game"*. So the title's first words are the phrase's words,
in the phrase's order -- not the phrase's meaning, its WORDS.

**THE ORDER OF THE LIST IS THE GAME.** The top result is what the
buyer sees first. A title that does not lead with the matched words
does not get there.

---

## THE DEMONSTRATION, and it is the clearest thing measured on this
## machine

**MEASURED 2026-10-31, on Amazon:**

| phrase | results | the top result | price |
|---|---|---|---|
| **rabbit hutch** | 179 | **The Rabbit Hutch: A NOVEL** | $8.16 |
| **how to build a rabbit hutch** | 70 | How to Build Animal Housing: 60 Plans for Coops | $19.99 |

**THE SAME TWO WORDS, IN A DIFFERENT ORDER, AND THE NOVEL IS
EXCLUDED.** The longer phrase is a different query, and the fiction
does not match it.

So the short phrase is NOT automatically the good one. **A phrase wide
enough to admit fiction will rank fiction, and the buyer who typed
"how to build a rabbit hutch" wanted plans, not a novel.** The phrase
has to be *specific enough to exclude the wrong book*, and the
specificity is what buys the top of the list.

---

## THE RABBIT SET, measured in full (2026-10-31)

The whole point of a pet-care category: the buyer's job is a specific
animal's specific problem. And this category holds the widest-open
phrases measured on this machine.

| phrase | results | the top result now | price | the title we would write |
|---|---|---|---|---|
| rabbit shedding | **3** | NETHERLAND DWARF RABBIT HANDBOOK | $16.50 | Rabbit Shedding Explained |
| rabbit nails trimming | **11** | The Rabbit-Raising Problem Solver | $11.99 | Rabbit Nails Trimming Handbook |
| rabbit hay | **18** | Hay is for Rabbits!: A rabbit food primer | $0.00 | Rabbit Hay for Beginners |
| rabbit potty training | **33** | Pet Rabbit Care Made Easy | $0.00 | Rabbit Potty Training for Beginners |
| how to build a rabbit hutch | **70** | How to Build Animal Housing | $19.99 | **How to Build a Rabbit Hutch** |
| what to feed a rabbit | **128** | Feeding Meat Rabbits for Free | $15.99 | What to Feed a Rabbit |
| rabbit diet | 133 | The Complete Rabbit Care Handbook | $19.99 | Rabbit Diet for Beginners |
| rabbit hutch | 179 | **The Rabbit Hutch: A NOVEL** | $8.16 | Rabbit Hutch Step by Step |
| rabbit grooming | 252 | Pet Rabbit Care Made Easy | $0.00 | Rabbit Grooming Handbook |
| netherland dwarf rabbit care | 373 | Netherland Dwarf Rabbit (a BREED book) | $10.17 | Netherland Dwarf Rabbit Care Guide |
| lop eared rabbit care | 381 | Lop Eared Rabbit Calendar 2027 | $12.65 | Lop Eared Rabbit Care Handbook |
| rabbit breeds | 3,000 | Rabbit Breeds: 49 Essential Breeds | $10.21 | Rabbit Breeds and Care |
| rabbit housing | 6,000 | Rabbit Housing: Planning, Building | $18.32 | Rabbit Housing Step by Step |
| rabbit care | 20,000 | My First Pet Rabbit | $19.95 | Rabbit Care for Beginners |

**WHAT THE TABLE SHOWS, and it is three things:**

**1. THE WIDEST-OPEN PHRASES ARE SINGLE-TASK.** "rabbit shedding" (3),
"rabbit nails trimming" (11), "rabbit hay" (18), "rabbit potty
training" (33). One task, one animal, one phrase. **That is where a
new book reaches the top of the list, because there is nothing to
outrank.** The gurus' rule and the measured numbers agree.

**2. THE BY-TYPE PHRASES ARE WIDE BUT UNFILLED.** "netherland dwarf
rabbit care" (373) has a BREED BOOK at the top, and "lop eared rabbit
care" (381) has a CALENDAR. **Nobody has written the care book for
either type.** That is the gap Bobby pointed at with *"by type of
rabbit"*, and the measurement confirms it: the phrase is wide enough
to hold a care book and nobody has written one.

**3. THE PRICE IS WHAT THE MARKET PAYS, AND IT IS NOT THE CHEAP
END.** The top results sit at **$10.17-$19.99**. The $0.00 entries
are KU books. The saturated $6.48-$8.34 prices belong to the
saturated phrases -- the laminated cards. **The open phrases are
worth more, and that is the reward for being specific.**

---

## THE TITLE RULES, and every one of them is enforced

**1. FOUR TO SIX WORDS.** A longer title is carrying two jobs.

**2. THE PHRASE LEADS, IN ITS OWN WORDS, IN ITS OWN ORDER.**
`How to Build a Rabbit Hutch`, not `The Complete Guide to Building
Rabbit Housing`.

**3. THE SMALL WORDS STAY SMALL.** "How to Build a Rabbit Hutch", not
"How To Build A Rabbit Hutch". A title with every word capitalised
looks keyword-stuffed, which is what the slop wave looks like.

**4. NO UNSEARCHABLE WORD.** "unlock", "discover", "transform",
"journey", "tapestry", "secret", "wisdom", "legacy". These are the
mark of the slop wave, and they are not searched. Matched as WHOLE
WORDS -- "unlock" must not fire inside "unlocksmith".

**5. THE TITLE CARRIES THE PHRASE'S SUBJECT.** "500 Chemistry
Questions and Answers" does not contain "equations review" but it
carries "Chemistry", which is what the buyer searched for.

**6. A PATTERN ONLY FIRES WHEN IT HAS ITS PARTS.** A job phrase
("how to stop your dog barking") yields a "how to" title and NOT
"200 Questions and Answers". A subject phrase yields the count
titles and not the "how to" ones.

---

## THE PATTERNS, and the job each one names

| pattern | example | the job |
|---|---|---|
| how_to | How to Price Your Freelance Work | a named action on a named thing |
| how_to_qualifier | How to Fix Clay Soil Fast | the same job, narrowed |
| how_to_for | How to Meditate for Beginners | the job, narrowed to a person |
| count_questions | 200 Chemistry Questions and Answers | the exam job |
| count_exam | 200 Chemistry Exam Questions and Answers | the exam job, named |
| subject_guide | Chemistry Study Guide for Beginners | the study job |
| count_guides | 200 Chemistry Study Guides and Answers | the list job |
| count_recipes | 100 One-Pot Meals for Beginners | the making job |
| subject_workbook | Chemistry Workbook for Beginners | the practice job |
| **phrase_lead** | Rabbit Hutch Step by Step | **the phrase's words at the front** |
| phrase_lead_audience | Rabbit Hutch for Beginners | the phrase, then the person |
| phrase_only | How to Build a Rabbit Hutch | the phrase ALONE, when it is 4-6 words |

---

## THE CATEGORIES, and the filter that put each one where it is

**THE FILTER IS BOBBY'S:** *"reason who would buy a book and why. skip
law and medicine"*, *"health is rich but easily banned"*, *"romance is
out"*.

**ACTIVE:** Test Preparation (50,000), Business (80,000), Self-Help
(80,000), Gardening (60,000), Pets & Animal Care (70,000), Parenting
(70,000), Religion & Spirituality (80,000), Relationships & Dating
(70,000), Cookbooks (70,000, DEFERRED on the cover).

**SKIPPED, each with its reason:**

| category | why |
|---|---|
| **Law** | the bar is sold as a COURSE (BarPrep Hero, Themis, Adaptibar); the book is the optional part |
| **Medicine** | the boards are sold as a QUESTION BANK at $200-400 (UWorld, Lecturio, Osmosis); and our 182,822-question bank is INDIAN-EXAM material, a different market |
| **Health & Fitness** | rich in demand and rich in CLAIMS -- a health book that makes a claim is a regulatory target and the enforcement lands on the listing |
| **Romance** | buyers BROWSE, they do not search |
| **Biography / History / Philosophy** | browse categories; the buyer's job is understanding, not a task with a deadline |

**THE PATTERN ACROSS ALL FIVE, and it is the useful part:** they are
the categories where the buyer's job is satisfied by a COURSE or a
SUBSCRIPTION, or where the content carries a claim that can be
enforced against us. **In every case the book is not where the money
is made.**

---

## WHERE OUR SUPPLY IS

**MEASURED 2026-10-31, `Desktop/test-prep/testing`: 224,490 questions**
across 9 banks.

| bank | questions |
|---|---|
| MCQs-medical.csv | 182,822 (21 subjects, 2,388 topics) |
| Psychology.csv.txt | 9,830 |
| World-History.csv.txt | 9,205 |
| Economics.csv.txt | 8,989 |
| Science-MCQ.csv | 5,144 |
| MCQ-uncategorized.csv | 4,858 |
| Biology-MCQ.csv | 1,783 |
| History-MCQs-1000.csv | 1,142 |
| Physiology.csv | 561 |

Plus 134 finished test pages in `Desktop/test-prep/` and an
`MCQ-maker.php`.

**AND THE PHRASES THAT SUPPLY IMPLIES ARE ALREADY IN THE CATALOG:**
"chemistry equations review" (460 results, OPEN) and "physics
equations review" (627, OPEN) are the narrowest test-prep phrases
measured, and we hold 5,144 science questions.

**THE MEDICAL BANK IS A DIFFERENT MARKET, and it is stated rather
than used.** Its topics are "All India exam", "G.I.T", "C.V.S",
"Endocrinology" -- Indian-exam material. It is a real, enormous
asset, and it does not address the US boards. **Use it for the
Indian market, or not at all.**

---

## THE COURSE, and what it teaches

**"We will publish a course in ebook writing."** The course is this
document's method, and it is already taught by the tooling:

| lesson | the tool that teaches it |
|---|---|
| 1. a category is a buyer's JOB | the `buyer_job` field, and the skip reasons |
| 2. the phrase is the unit of demand | `keyword_phrases.py --titles` |
| 3. demand + competition = the opportunity | the `results` count and `is_open` |
| 4. the title LEADS with the phrase | the `phrase_lead` pattern |
| 5. 4-6 words, no unsearchable word | `word_count` and `is_unsearchable` |
| 6. the cover is the click | far-art's 56-axis sheet schema |
| 7. the free chapters are the funnel | `social-media/tools/publish.py` |
| 8. the voice is the difference | far-writing's voice gate |
| 9. the measurement closes the loop | copies per title per month |

**AND THE COURSE IS ITSELF A COURSE, so it goes through the same
pipeline:** free chapters on X and Substack, the book offer, the
ebook. The first book IS the course. **That is the demo: we cannot
sell a course we have not run ourselves.**

---

## THE MEASUREMENT NOTE, and it is a limitation

**MEASURED 2026-10-31: Amazon's `/s` endpoint returns HTTP 503 to a
plain `urllib` request.** The homepage returns 200; every search
returns 503, from every header combination tried (browser User-Agent,
Accept-Encoding, sec-fetch headers, session-id cookie). **A browser
session returns 200 with the full result set.**

**AND this machine's delivery country is NEPAL**, so Amazon's
bestseller grid for that store returns *"Sorry, there are no Best
Sellers available in this category."* The SEARCH works from any
store; the GRID does not.

**So every count in this document came from the search endpoint, and
the grid was unreachable.** Any future tool must say which endpoint it
used, because a demand number with no endpoint behind it is not a
measurement.

---

## WHAT IS NEXT, in order

1. **MEASURE THE OPEN PHRASES WE HAVE NOT MEASURED.** The Business,
   Self-Help, Gardening, Parenting, Religion and Relationships phrases
   are all UNMEASURED -- they carry the jobs we chose, and their demand
   is unknown. That is the next measurement, and it is the one that
   picks the FIRST book.
2. **THE COVER.** far-art's 56-axis sheet schema has no cover
   use-case. Pedruzzi and Ken both say the cover is the click, and
   the rabbit set's top results are $10.17-$19.99 books with real
   covers.
3. **THE SELF-HELP VOICE.** The 4 shipped voices are literary. The
   success-blueprint register Bobby names is missing, and it is a
   FIFTH voice: axes, not an author's name.
4. **THE FIRST BOOK.** One category, one phrase, one title, the free
   chapters, the offer, the upload, the measurement.
