"""
keyword_phrases.py -- THE TITLE GENERATOR'S SUPPLY.

WHAT THIS IS
------------
Bobby, 2026-10-31: *"this keyword phrase work is central not just in
academia. make notes in far-writing: categories of a bookstore first,
then which are amenable to keyword phrases, 4-6 word titles"*, and
*"scan amazon categories by keyword phrases. as book seller i know
keyword phrases beat great stories. no one searches for ie. amazon is
a search engine"*.

So there are THREE things and they are in a fixed order:

    1. THE CATEGORY   the bookstore's department. The axis.
    2. THE PHRASE     what the buyer TYPES. The unit of demand.
    3. THE TITLE      4-6 words, built from the phrase.

And the order matters, because the TITLE is not chosen and then
searched for -- the TITLE is BUILT from the phrase, and the phrase is
chosen from the category.

WHY THE PHRASE IS THE UNIT, and not the title
-----------------------------------------------
Nobody types a title. They type their problem: "how to stop my dog
barking", "chemistry equations review". So the demand measurement is
on phrases, and the title is an OUTPUT of the phrase.

THE FOUR-WORD RULE, and the six-word ceiling
--------------------------------------------
A TITLE IS 4-6 WORDS. The limit is a DISCIPLINE, not a style: a title
longer than six words is trying to carry two jobs, and one title
carries one job.

THE TITLE PATTERNS, and each one names a JOB
--------------------------------------------
Every pattern below was measured against real Amazon titles on
2026-10-31, and every pattern names a buyer job rather than a mood.

THE DEMAND NUMBERS
------------------
The `results` field is Amazon's REPORTED result count for the phrase,
measured 2026-10-31 through a browser session. Amazon rounds these and
they are approximate, so they are recorded as reported and no rate is
derived from them.

**THE COMPETITION READ, which is the number that decides.** The gurus'
rule -- demand plus FEW competitors -- is visible in the measured data:

    "chemistry study guide"       10,000 results  (saturated)
    "chemistry equations review"    460 results  (OPEN)
    "physics equations review"      627 results  (OPEN)

A 60,000-result phrase is a race we lose to a laminated card. A
460-result phrase with a real buyer is the opportunity.

Run:
    python tools/keyword_phrases.py --list
    python tools/keyword_phrases.py --category test_prep
    python tools/keyword_phrases.py --titles "chemistry equations review"
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Sequence, Tuple

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CATALOG_DIR = os.path.join(REPO, "catalog")
PHRASES_FILE = os.path.join(CATALOG_DIR, "keyword_phrases.json")

#: THE TITLE PATTERNS. Each is (pattern_id, template, the job it
#: names). The template uses {n} for a count and {subject}, {object},
#: {verb}, {qualifier} for the phrase's parts.
TITLE_PATTERNS: Tuple[Tuple[str, str, str], ...] = (
    ("how_to", "How to {verb} {object_}",
     "the most common buyer job: a named action on a named thing"),
    ("how_to_qualifier", "How to {verb} {object_} {qualifier}",
     "the same job, narrowed to a case"),
    ("how_to_for", "How to {verb} {object_} for {audience}",
     "the job, narrowed to a person"),
    ("count_questions", "{n} {subject} Questions and Answers",
     "the exam job: a bank of questions"),
    ("count_exam", "{n} {subject} Exam Questions and Answers",
     "the exam job, named as an exam"),
    ("subject_guide", "{subject} Study Guide for {audience}",
     "the study job, narrowed to a person"),
    ("count_guides", "{n} {subject} Study Guides and Answers",
     "the list job: many small books sold together"),
    ("count_recipes", "{n} {subject} Recipes for {audience}",
     "the making job: a set of things to do"),
    ("subject_workbook", "{subject} Workbook for {audience}",
     "the practice job: do it, not read it"),
    # -- THE PHRASE-LEAD PATTERN, and it is the most important one ----
    #
    # Bobby, 2026-10-31: *"highest match keyword must go first it is a
    # lexical game"*, and *"quality of cover but search and order of
    # list results is the game"*.
    #
    # SO THE TITLE LEADS WITH THE PHRASE, IN THE PHRASE'S OWN WORDS.
    # Not the phrase's meaning -- its WORDS, in its ORDER, at the
    # FRONT.
    #
    # AND THE MEASUREMENT THAT PROVES IT, 2026-10-31, on Amazon:
    #
    #   "rabbit hutch"                  179 results
    #       top result: "The Rabbit Hutch: A NOVEL"  ($8.16)
    #   "how to build a rabbit hutch"    70 results
    #       top result: "How to Build Animal Housing: 60 Plans for Coops"
    #
    # The same two words, in a different order, and the novel is
    # EXCLUDED -- because the longer phrase is a different query, and
    # the fiction that matched "rabbit hutch" does not match "how to
    # build a rabbit hutch".
    #
    # And the same thing at the title level: a title that puts the
    # matched words at the FRONT is the one the search ranks on.
    ("phrase_lead", "{phrase} {suffix}",
     "the phrase's own words, at the front, in the phrase's order"),
    ("phrase_lead_audience", "{phrase} for {audience}",
     "the phrase's own words, then the person"),
    ("phrase_only", "{phrase}",
     "the phrase ALONE, when the phrase is already 4-6 words"),
)

#: THE SUFFIXES the phrase-lead pattern uses to reach the 4-6 band.
#: Each one is a noun a reader would use, and each one keeps the
#: phrase's words at the FRONT.
PHRASE_SUFFIXES: Tuple[str, ...] = (
    "Guide", "Plans", "Handbook", "Manual", "Essentials", "Basics",
    "for Beginners", "for Owners", "Explained", "Step by Step",
)

#: THE STOP WORDS -- and they are a REFUSAL, not a preference. These
#: are the words that make a title unsearchable, because nobody types
#: them.
UNSEARCHABLE_WORDS = (
    "journey", "tapestry", "symphony", "odyssey", "unlock", "unleash",
    "discover", "unlocking", "transform", "transformation", "awaken",
    "awakening", "enlighten", "enlightenment", "mastery", "secret",
    "secrets", "truth", "wisdom", "legacy", "guide to your",
)


# ===========================================================================
# THE CATALOG
# ===========================================================================

@dataclass
class Phrase:
    """one phrase, and what is known about it."""
    phrase: str
    category: str
    #: Amazon's reported result count, measured 2026-10-31. Rounded.
    results: str = ""
    #: The titles Amazon's top results use for this phrase. The FORMAT
    #: to beat and the price band the market accepts.
    competitor_titles: List[str] = field(default_factory=list)
    competitor_prices: List[str] = field(default_factory=list)
    #: The subject the phrase names, used to build the title.
    subject: str = ""
    #: The verb the title needs, when the pattern is "how to".
    verb: str = ""
    object_: str = ""
    qualifier: str = ""
    audience: str = ""
    #: How many questions we hold for this subject. The supply.
    supply: int = 0
    note: str = ""

    @property
    def is_open(self) -> bool:
        """OPEN means few competitors -- the opportunity.

        The threshold is 2,000 results. MEASURED: "chemistry equations
        review" is 460 and "physics equations review" is 627, while the
        saturated study-guide phrases are 10,000-60,000.

        AND AN UNMEASURED PHRASE IS NOT OPEN. It is UNMEASURED. The
        first version returned True for a phrase with no result count
        at all, so every phrase we had not yet measured showed up as
        "OPEN" -- which reads as "we measured it and it is open", when
        the truth is "we have not looked". Those are different findings
        and only one of them is about the world.
        """
        if not self.results:
            return False
        try:
            return int(self.results.replace(",", "")) < 2000
        except ValueError:
            return False

    @property
    def measured(self) -> bool:
        """has this phrase been measured at all?"""
        return bool(self.results)

    def describe(self) -> Dict[str, Any]:
        d = asdict(self)
        d["is_open"] = self.is_open
        return d


@dataclass
class Category:
    """one bookstore department."""
    key: str
    name: str
    #: WHY the buyer's job is buyable here. The filter Bobby named.
    buyer_job: str = ""
    #: WHY this category is or is not keyword-amenable.
    keywordable: str = ""
    #: The reason a category is skipped, when it is.
    skipped_because: str = ""
    #: Amazon's reported result count for the category word.
    results: str = ""
    phrases: List[Phrase] = field(default_factory=list)

    def __post_init__(self) -> None:
        # A tuple of phrases is what the CATEGORIES literal uses, and a
        # tuple is not a list. Normalising here means the catalog code
        # never has to care which one it was handed.
        self.phrases = list(self.phrases)

    @property
    def open_phrases(self) -> List[Phrase]:
        return [p for p in self.phrases if p.is_open]

    def describe(self) -> Dict[str, Any]:
        return {
            "key": self.key, "name": self.name,
            "buyer_job": self.buyer_job,
            "keywordable": self.keywordable,
            "skipped_because": self.skipped_because,
            "results": self.results,
            "phrases": len(self.phrases),
            "open_phrases": len(self.open_phrases),
        }


#: THE CATEGORIES, and the filter that put each one where it is.
#:
#: The filter is Bobby's: *"reason who would buy a book and why. skip
#: law and medicine"*, *"health is rich but easily banned"*, *"romance
#: is out"*.
#:
#: EVERY `results` HERE WAS MEASURED on Amazon's books department on
#: 2026-10-31. The phrase results likewise.
CATEGORIES: Tuple[Category, ...] = (
    Category(
        key="test_prep",
        name="Test Preparation",
        buyer_job="pass an exam on a DATE. the purest job there is, and "
                  "it has a deadline, which means urgency.",
        keywordable="BEST IN CLASS. the phrase IS the job: 'chemistry "
                    "equations review', 'biology exam questions'. and we "
                    "hold 224,490 questions already.",
        results="50,000",
        phrases=(
            Phrase(phrase="chemistry equations review", category="test_prep",
                   results="460", subject="Chemistry",
                   competitor_titles=["Chemistry Equations & Answers: a "
                                      "QuickStudy Laminated Reference Guide"],
                   competitor_prices=["$8.34"],
                   supply=5144, note="OPEN. 460 results."),
            Phrase(phrase="physics equations review", category="test_prep",
                   results="627", subject="Physics",
                   competitor_titles=["Equations of Physics: for "
                                      "Undergraduate Level"],
                   competitor_prices=["$0.00"], supply=0,
                   note="OPEN. 627 results."),
            Phrase(phrase="chemistry study guide", category="test_prep",
                   results="10,000", subject="Chemistry",
                   competitor_titles=["Chemistry: a QuickStudy Laminated "
                                      "Reference Guide"],
                   competitor_prices=["$6.49"], supply=5144,
                   note="saturated. a laminated card is the top result."),
            Phrase(phrase="chemistry lab notes", category="test_prep",
                   results="3,000", subject="Chemistry",
                   competitor_titles=["Chemistry Student Lab Notebook: "
                                      "Cornell Notes-Grid Format"],
                   competitor_prices=["$9.99"], supply=5144),
            Phrase(phrase="biology study guide", category="test_prep",
                   results="20,000", subject="Biology",
                   competitor_titles=["Biology: a QuickStudy Laminated "
                                      "Reference Guide"],
                   competitor_prices=["$8.34"], supply=1783),
            Phrase(phrase="psychology study guide", category="test_prep",
                   results="30,000", subject="Psychology",
                   competitor_titles=["Psychology Terminology: a QuickStudy "
                                      "Laminated Reference Guide"],
                   competitor_prices=["$6.95"], supply=9830),
            Phrase(phrase="accounting study guide", category="test_prep",
                   results="10,000", subject="Accounting",
                   competitor_titles=["Accounting Equations & Answers"],
                   competitor_prices=["$6.48"], supply=8989),
            Phrase(phrase="pharmacology study guide", category="test_prep",
                   results="7,000", subject="Pharmacology",
                   competitor_titles=["Top 200 Drugs Simplified"],
                   competitor_prices=["$22.13"], supply=0),
            Phrase(phrase="medical student notes", category="test_prep",
                   results="10,000", subject="Medical",
                   competitor_titles=["Nursing Success Bundle: 400+ Page "
                                      "Handwritten Notes"],
                   competitor_prices=["$99.99"], supply=182822,
                   note="the supply is real but the market is Indian exams, "
                        "not the US boards. see the category note."),
        ),
    ),
    Category(
        key="business",
        name="Business",
        buyer_job="do a MONEY job: price it, sell it, raise for it, "
                  "hire for it, get the first customer.",
        keywordable="YES. the job has a name and the name is typed. "
                    "nobody searches 'business insights'; they search "
                    "'how to price my freelance work'.",
        results="80,000",
        phrases=(
            Phrase(phrase="how to price freelance work",
                   category="business", results="", verb="Price",
                   object_="Your Freelance Work",
                   audience="Freelancers",
                   competitor_titles=[], competitor_prices=[]),
            Phrase(phrase="how to raise your first round",
                   category="business", results="", verb="Raise",
                   object_="Your First Round",
                   audience="Founders",
                   competitor_titles=[], competitor_prices=[]),
            Phrase(phrase="how to find your first customer",
                   category="business", results="", verb="Find",
                   object_="Your First Customer",
                   audience="Freelancers",
                   competitor_titles=[], competitor_prices=[]),
            Phrase(phrase="how to hire your first employee",
                   category="business", results="", verb="Hire",
                   object_="Your First Employee",
                   audience="Small Business Owners",
                   competitor_titles=[], competitor_prices=[]),
        ),
    ),
    Category(
        key="self_help",
        name="Self-Help",
        buyer_job="change a behaviour they have ALREADY tried to change. "
                  "which is why the phrase is nearly always 'how to "
                  "stop...' or 'how to build...'.",
        keywordable="YES. and the difference is the VOICE: the title is "
                    "keyword-shaped and the book is written in a public-"
                    "domain literary voice. two layers, both ours.",
        results="80,000",
        phrases=(
            Phrase(phrase="how to stop procrastinating", category="self_help",
                   results="", verb="Stop", object_="Procrastinating",
                   audience="Everyone"),
            Phrase(phrase="how to build discipline", category="self_help",
                   results="", verb="Build", object_="Discipline That Lasts",
                   audience="Everyone"),
            Phrase(phrase="how to think clearly under pressure",
                   category="self_help", results="", verb="Think",
                   object_="Clearly Under Pressure", audience="Everyone"),
            Phrase(phrase="how to overcome fear of failure",
                   category="self_help", results="", verb="Overcome",
                   object_="Fear of Failure", audience="Everyone"),
        ),
    ),
    Category(
        key="gardening",
        name="Gardening",
        buyer_job="grow a specific plant in a specific place. that is a "
                  "PHRASE, not a feeling: 'how to grow tomatoes in "
                  "containers', 'how to fix clay soil'.",
        keywordable="YES. and low claim risk, low cost, and the cover is "
                    "SHOWABLE -- a garden sells with a photograph.",
        results="60,000",
        phrases=(
            Phrase(phrase="how to grow tomatoes in containers",
                   category="gardening", results="", verb="Grow",
                   object_="Tomatoes in Containers",
                   audience="Beginners"),
            Phrase(phrase="how to fix clay soil", category="gardening",
                   results="", verb="Fix", object_="Clay Soil Fast",
                   audience="Gardeners"),
            Phrase(phrase="what to plant in shaded beds",
                   category="gardening", results="", verb="Plant",
                   object_="in Shaded Beds", audience="Gardeners"),
        ),
    ),
    Category(
        key="pets",
        name="Pets & Animal Care",
        buyer_job="stop one specific ANIMAL behaviour. 'how to stop my "
                  "dog barking', 'how to stop my cat scratching'.",
        keywordable="YES. the job has a phrase and the phrase is the "
                    "title. and it RECURS: a dog's behaviour changes "
                    "with age, and a second dog is a second sale.",
        results="70,000",
        phrases=(
            Phrase(phrase="how to stop your dog barking",
                   category="pets", results="", verb="Stop",
                   object_="Your Dog Barking", audience="Dog Owners"),
            Phrase(phrase="how to stop your cat scratching",
                   category="pets", results="", verb="Stop",
                   object_="Your Cat Scratching", audience="Cat Owners"),
            Phrase(phrase="how to stop a dog pulling on leash",
                   category="pets", results="", verb="Stop",
                   object_="a Dog Pulling on Leash",
                   audience="Dog Owners"),
            # -- THE RABBIT SET -------------------------------------------
            #
            # MEASURED 2026-10-31 on Amazon, and it is the clearest
            # demonstration of the lexical game that has been measured
            # on this machine.
            #
            #   "rabbit hutch"                   179 results
            #       top: "The Rabbit Hutch: A NOVEL"           $8.16
            #   "how to build a rabbit hutch"      70 results
            #       top: "How to Build Animal Housing: 60 Plans" $19.99
            #
            # THE SAME TWO WORDS, IN A DIFFERENT ORDER, AND THE NOVEL IS
            # EXCLUDED. The longer phrase is a different query, and the
            # fiction does not match it.
            #
            # And the ORDER OF THE LIST is the game, as Bobby said: the
            # top result is what the buyer sees first, and a title that
            # does not lead with the matched words does not get there.
            Phrase(phrase="rabbit hutch", category="pets",
                   results="179",
                   competitor_titles=["The Rabbit Hutch: A Novel"],
                   competitor_prices=["$8.16"],
                   note="the top result is a NOVEL. the phrase alone "
                        "does not exclude fiction -- the longer phrase "
                        "does."),
            Phrase(phrase="how to build a rabbit hutch", category="pets",
                   results="70",
                   competitor_titles=["How to Build Animal Housing: 60 "
                                      "Plans for Coops"],
                   competitor_prices=["$19.99"],
                   note="OPEN, and the novel is gone. this is the "
                        "phrase that excludes fiction."),
            Phrase(phrase="rabbit diet", category="pets", results="133",
                   competitor_titles=["The Complete Rabbit Care Handbook"],
                   competitor_prices=["$19.99"]),
            Phrase(phrase="what to feed a rabbit", category="pets",
                   results="128",
                   competitor_titles=["Feeding Meat Rabbits for Free"],
                   competitor_prices=["$15.99"],
                   note="the top result is about MEAT rabbits -- a "
                        "different buyer. the phrase is open."),
            Phrase(phrase="rabbit breeds", category="pets", results="3,000",
                   competitor_titles=["Rabbit Breeds: The Pocket Guide to "
                                      "49 Essential Breeds"],
                   competitor_prices=["$10.21"]),
            Phrase(phrase="netherland dwarf rabbit care", category="pets",
                   results="373",
                   competitor_titles=["Netherland Dwarf Rabbit"],
                   competitor_prices=["$10.17"],
                   note="BY TYPE OF RABBIT. the top result is a BREED "
                        "BOOK, not a care book -- so the by-type title "
                        "is not yet being written."),
            Phrase(phrase="lop eared rabbit care", category="pets",
                   results="381",
                   competitor_titles=["Lop Eared Rabbit Calendar 2027"],
                   competitor_prices=["$12.65"],
                   note="the top result is a CALENDAR. nobody has written "
                        "the care book for this type."),
            Phrase(phrase="rabbit grooming", category="pets",
                   results="252",
                   competitor_titles=["Pet Rabbit Care Made Easy"],
                   competitor_prices=["$0.00"]),
            Phrase(phrase="rabbit potty training", category="pets",
                   results="33",
                   competitor_titles=["Pet Rabbit Care Made Easy"],
                   competitor_prices=["$0.00"],
                   note="the widest-open phrase measured: 33 results."),
            Phrase(phrase="rabbit nails trimming", category="pets",
                   results="11",
                   competitor_titles=["The Rabbit-Raising Problem Solver"],
                   competitor_prices=["$11.99"],
                   note="11 results. nothing competes here."),
            Phrase(phrase="rabbit shedding", category="pets", results="3",
                   competitor_titles=["NETHERLAND DWARF RABBIT HANDBOOK"],
                   competitor_prices=["$16.50"],
                   note="3 results. the widest-open phrase measured."),
            Phrase(phrase="rabbit hay", category="pets", results="18",
                   competitor_titles=["Hay is for Rabbits!: A rabbit food "
                                      "primer"],
                   competitor_prices=["$0.00"],
                   note="18 results, and the top title is already "
                        "phrase-led."),
        ),
    ),
    Category(
        key="parenting",
        name="Parenting",
        buyer_job="get through a STAGE. the stage has a name and a date: "
                  "toddlers, sleep, teenagers, the first school year.",
        keywordable="YES. the phrases are the AGES, and the ages are the "
                    "market.",
        results="70,000",
        phrases=(
            Phrase(phrase="how to talk to a teenager",
                   category="parenting", results="", verb="Talk",
                   object_="to a Teenager", audience="Parents"),
            Phrase(phrase="how to get your toddler to sleep",
                   category="parenting", results="", verb="Get",
                   object_="Your Toddler to Sleep", audience="Parents"),
            Phrase(phrase="how to handle a temper tantrum",
                   category="parenting", results="", verb="Handle",
                   object_="a Temper Tantrum", audience="Parents"),
        ),
    ),
    Category(
        key="religion",
        name="Religion & Spirituality",
        buyer_job="a PRACTICE, not a topic. 'prayer for anxiety', 'how "
                  "to meditate', 'understanding the book of psalms'.",
        keywordable="YES, and it is the one NOBODY ELSE CAN COPY. 30 "
                    "years of sitting 5 hours every other day, 7-hour "
                    "singing, Tsongkhapa at Jonang and Nala Gompa, 17,000 "
                    "feet. a writer can copy a technique; a writer "
                    "cannot copy 30 years in a monastery.",
        results="80,000",
        phrases=(
            Phrase(phrase="how to meditate for beginners",
                   category="religion", results="", verb="Meditate",
                   object_="for Beginners", audience="Beginners"),
            Phrase(phrase="how to pray when you cannot",
                   category="religion", results="", verb="Pray",
                   object_="When You Cannot", audience="Believers"),
            Phrase(phrase="how to sit with difficult emotions",
                   category="religion", results="", verb="Sit",
                   object_="With Difficult Emotions", audience="Meditators"),
        ),
    ),
    Category(
        key="relationships",
        name="Relationships & Dating",
        buyer_job="get one specific OUTCOME, or communicate with one "
                  "specific person.",
        keywordable="YES, with a CAUTION: this is where AI slop "
                    "concentrates, because the phrases are easy and the "
                    "advice is cheap. enter it only with a specific "
                    "mechanism and a voice.",
        results="70,000",
        phrases=(
            Phrase(phrase="how to rebuild trust after betrayal",
                   category="relationships", results="", verb="Rebuild",
                   object_="Trust After Betrayal", audience="Couples"),
            Phrase(phrase="how to text someone you like",
                   category="relationships", results="", verb="Text",
                   object_="Someone You Like", audience="Singles"),
            Phrase(phrase="how to fight without hurting",
                   category="relationships", results="", verb="Fight",
                   object_="Without Hurting", audience="Couples"),
        ),
    ),
    Category(
        key="cookbooks",
        name="Cookbooks",
        buyer_job="cook a specific DISH. the phrase is exact: 'one pot "
                  "meals', 'sourdough bread recipe'.",
        keywordable="PARTLY. a cookbook sells on the PHOTOGRAPH, not the "
                    "title. and a cookbook without a cover pipeline "
                    "cannot ship. DEFERRED until far-art's sheet schema "
                    "has a cover use-case. the keywords are ready when "
                    "it does.",
        results="70,000",
        phrases=(
            Phrase(phrase="100 one pot meals for beginners",
                   category="cookbooks", results="", subject="One-Pot Meals",
                   audience="Beginners"),
            Phrase(phrase="sourdough bread without a starter",
                   category="cookbooks", results="", subject="Sourdough Bread",
                   audience="Beginners"),
            Phrase(phrase="meal prep for two",
                   category="cookbooks", results="", subject="Meal Prep",
                   audience="Households"),
        ),
    ),
    Category(
        key="health",
        name="Health & Fitness",
        buyer_job="a body PROBLEM. and every health book makes a claim.",
        keywordable="SKIPPED. rich in demand and rich in claims: a health "
                    "book that makes a claim is a regulatory target, and "
                    "the enforcement lands on the LISTING. this is where "
                    "the marginal book is most likely to be pulled.",
        skipped_because="easily banned. Bobby, 2026-10-31.",
        results="80,000",
        phrases=(),
    ),
    Category(
        key="law",
        name="Law",
        buyer_job="pass the bar.",
        keywordable="SKIPPED. the bar is sold as a COURSE -- BarPrep "
                    "Hero, Themis, Adaptibar -- and a book is the "
                    "optional part of the purchase.",
        skipped_because="the job is sold as a course, not a book. "
                        "Bobby, 2026-10-31.",
        results="70,000",
        phrases=(),
    ),
    Category(
        key="medicine",
        name="Medicine",
        buyer_job="pass the boards.",
        keywordable="SKIPPED. the boards are sold as a QUESTION BANK at "
                    "$200-400 (UWorld, Lecturio, Picmonic, Osmosis) and a "
                    "book cannot beat a question bank. AND OUR SUPPLY IS "
                    "THE WRONG MARKET: the 182,822-question bank is "
                    "Indian-exam material ('All India exam', G.I.T), so "
                    "it does not address the US boards at all.",
        skipped_because="the job is sold as a question bank, and our "
                        "supply is a different market.",
        results="",
        phrases=(),
    ),
    Category(
        key="romance",
        name="Romance",
        buyer_job="be entertained.",
        keywordable="SKIPPED. buyers BROWSE, they do not search.",
        skipped_because="romance is out. Bobby, 2026-10-31.",
        results="70,000",
        phrases=(),
    ),
    Category(
        key="browse",
        name="Biography, History, Philosophy",
        buyer_job="understand a life or an idea.",
        keywordable="SKIPPED. browse, not search. and the buyer's job is "
                    "understanding, not doing.",
        skipped_because="browse categories. the buyer's job is not a "
                        "task with a deadline.",
        results="70,000-80,000",
        phrases=(),
    ),
)


# ===========================================================================
# THE TITLE GENERATOR
# ===========================================================================

def _title_case(phrase: str) -> str:
    """the phrase as it would appear at the front of a title.

    AND THE SMALL WORDS STAY SMALL. "how to build a rabbit hutch"
    becomes "How to Build a Rabbit Hutch", not "How To Build A Rabbit
    Hutch" -- a title with every word capitalised looks like a
    keyword-stuffed title, which is what the slop wave looks like.
    """
    small = {"a", "an", "the", "of", "and", "or", "to", "in", "for",
             "on", "at", "by", "with", "from", "your", "my", "our"}
    words = phrase.split()
    out = []
    for i, w in enumerate(words):
        if i > 0 and w.lower() in small:
            out.append(w.lower())
        else:
            out.append(w[:1].upper() + w[1:])
    return " ".join(out)


def word_count(text: str) -> int:
    """the words a reader counts.

    AND A HYPHENATED WORD IS ONE WORD. "One-Pot Meals" is 2 words to
    every reader and to Amazon's search, and counting it as 3 would
    push a good title out of the 4-6 band for no reason. The first
    version split on hyphens and got this wrong.
    """
    return len([w for w in re.split(r"\s+", text.strip()) if w])


def is_unsearchable(title: str) -> Optional[str]:
    """the refusal: a title with a word nobody types.

    MEASURED, from the gurus' own failure mode: Pedruzzi's "top
    selling" titles are flat and the slop wave is full of
    "unlock", "discover", "transform". Those words are not searched
    and they are the mark of the product.

    AND IT MATCHES ON WORDS, NOT SUBSTRINGS. The first version used
    `if w in low`, so "unlock" matched inside "unleash" -- and a title
    could be refused for the wrong word, or a word could hide inside
    another. So the words are matched as whole words.
    """
    low = title.lower()
    tokens = set(re.findall(r"[a-z']+", low))
    for w in UNSEARCHABLE_WORDS:
        if " " in w:
            # A PHRASE, and phrases match as phrases. "guide to your"
            # is a phrase, not a word, and matching it as a word
            # would never fire.
            if w in low:
                return w
        elif w in tokens:
            return w
    return None


def titles_for(phrase: Phrase, n: int = 200,
               audience: str = "") -> List[str]:
    """the 4-6 word titles a phrase yields.

    AND THE WORD COUNT IS ENFORCED, because a title that runs long is
    a title carrying two jobs. A pattern that produces a title outside
    4-6 words is DROPPED, not padded.

    AND A PATTERN ONLY FIRES WHEN IT HAS ITS PARTS. The first version
    applied EVERY pattern to every phrase, so "how to stop your dog
    barking" -- which has no subject and no verb field -- produced
    "200 Questions and Answers" and "Study Guide for Dog Owners". The
    generator was inventing a product for a phrase that names a job
    rather than a subject. So each pattern now requires its own parts,
    and a phrase with no subject yields no count-patterns.
    """
    out: List[str] = []
    aud = audience or phrase.audience or "Beginners"
    has_subject = bool(phrase.subject)
    has_job = bool(phrase.verb and phrase.object_)

    for pid, template, _job in TITLE_PATTERNS:
        try:
            if pid in ("how_to", "how_to_qualifier", "how_to_for"):
                if not has_job:
                    continue
                if pid == "how_to":
                    title = template.format(verb=phrase.verb,
                                            object_=phrase.object_)
                elif pid == "how_to_qualifier":
                    if not phrase.qualifier:
                        continue
                    title = template.format(verb=phrase.verb,
                                            object_=phrase.object_,
                                            qualifier=phrase.qualifier)
                else:
                    title = template.format(verb=phrase.verb,
                                            object_=phrase.object_,
                                            audience=aud)
            elif pid in ("count_questions", "count_exam", "count_guides",
                         "count_recipes"):
                if not has_subject:
                    continue
                title = template.format(n=n, subject=phrase.subject)
            elif pid == "subject_guide":
                if not has_subject:
                    continue
                title = template.format(subject=phrase.subject,
                                        audience=aud)
            elif pid == "subject_workbook":
                if not has_subject:
                    continue
                title = template.format(subject=phrase.subject,
                                        audience=aud)
            elif pid == "phrase_lead":
                # THE PHRASE'S OWN WORDS, AT THE FRONT. And the phrase
                # is title-cased as it would appear in a title, because
                # a title is not a search query -- it is a search query
                # wearing a title's clothes.
                lead = _title_case(phrase.phrase)
                for suffix in PHRASE_SUFFIXES:
                    title = template.format(phrase=lead, suffix=suffix)
                    if 4 <= word_count(title) <= 6:
                        out.append(re.sub(r"\s+", " ", title).strip())
            elif pid == "phrase_lead_audience":
                lead = _title_case(phrase.phrase)
                title = template.format(phrase=lead, audience=aud)
                if 4 <= word_count(title) <= 6:
                    out.append(re.sub(r"\s+", " ", title).strip())
            elif pid == "phrase_only":
                # THE PHRASE ALONE, when the phrase is already 4-6
                # words. "how to build a rabbit hutch" is 6 words, and
                # every suffix would push it to 7 -- so the phrase IS
                # the title, which is the most search-led title there
                # is.
                lead = _title_case(phrase.phrase)
                if 4 <= word_count(lead) <= 6:
                    out.append(lead)
            else:
                continue
        except KeyError:
            continue
        title = re.sub(r"\s+", " ", title).strip()
        if not (4 <= word_count(title) <= 6):
            continue
        if is_unsearchable(title):
            continue
        out.append(title)
    # preserve order, drop duplicates
    seen = set()
    uniq = []
    for t in out:
        if t.lower() not in seen:
            seen.add(t.lower())
            uniq.append(t)
    return uniq


# ===========================================================================
# THE CATALOG FILE
# ===========================================================================

def build_catalog() -> Dict[str, Any]:
    """the catalog as it is written to disk."""
    return {
        "generated": "2026-10-31",
        "title_rule": "4-6 words, and a phrase the buyer types",
        "patterns": [{"id": p[0], "template": p[1], "job": p[2]}
                     for p in TITLE_PATTERNS],
        "unsearchable_words": list(UNSEARCHABLE_WORDS),
        "categories": [c.describe() for c in CATEGORIES],
        "phrases": [p.describe()
                    for c in CATEGORIES for p in c.phrases],
    }


def write_catalog(path: str = PHRASES_FILE) -> str:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(build_catalog(), fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    return path


# ===========================================================================
# THE CLI
# ===========================================================================

def main() -> int:
    ap = argparse.ArgumentParser(description="the keyword-phrase catalog")
    ap.add_argument("--list", action="store_true",
                    help="list the categories and their phrases")
    ap.add_argument("--category", default=None, help="one category key")
    ap.add_argument("--titles", default=None,
                    help="the titles a phrase yields")
    ap.add_argument("--write", action="store_true",
                    help="write catalog/keyword_phrases.json")
    args = ap.parse_args()

    if args.titles:
        for c in CATEGORIES:
            for p in c.phrases:
                if p.phrase == args.titles:
                    print("  %s" % p.phrase)
                    print("  the titles:")
                    for t in titles_for(p):
                        print("    %-46s (%d words)" % (t, word_count(t)))
                    return 0
        print("  no such phrase in the catalog")
        return 1

    print("=" * 78)
    print("THE BOOKSTORE -- categories, phrases, titles")
    print("=" * 78)
    print()
    for c in CATEGORIES:
        if args.category and c.key != args.category:
            continue
        mark = "SKIPPED" if c.skipped_because else "ACTIVE"
        print("  %-28s %-8s amazon=%s" % (c.name[:28], mark, c.results))
        if c.skipped_because:
            print("     %s" % c.skipped_because[:70])
        print("     %s" % c.buyer_job[:70])
        for p in c.phrases:
            if not p.measured:
                flag = "  ? "
            elif p.is_open:
                flag = "OPEN"
            else:
                flag = "    "
            print("     %s %-38s results=%-8s supply=%s"
                  % (flag, p.phrase[:38], p.results or "UNMEASURED",
                     p.supply or "-"))
        print()

    if args.write:
        path = write_catalog()
        print("wrote: %s" % path)
    print("=" * 78)
    return 0


if __name__ == "__main__":
    sys.exit(main())
