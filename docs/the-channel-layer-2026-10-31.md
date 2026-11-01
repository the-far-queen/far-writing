# The channel layer: X Premium, many accounts, and what it costs (2026-10-31)

**Bobby, 2026-10-31:** *"many social media accts sign up and pay for
generous posting limits, automated"*, *"i have x premium we pay more x
super bundles grok use now"*, and earlier: *"we automate and produce
many titles publish on social media at no penalty, hand edit or more
care with our amazon titles, also many website pages"*.

**THE FINDING IS THE OPPOSITE OF WHAT "NO PENALTY" ASSUMES.** The
penalty is not on the books. **It is on the API bill**, and on the
account-per-platform rules. So "many accounts, generous limits" is the
right instinct and the wrong mechanism, and the difference is money.

---

## THE X TIERS, AND THE CHANGE ON 12 OCTOBER 2026

**MEASURED 2026-10-31, from multiple secondary sources (X's own pages
are unreadable from this machine -- MEASURED: `x.com/help` returned a
258-byte Cloudflare "Just a moment..." challenge, and
`x.com/i/premium_sign_up` returned a 98-byte shell):**

| tier | monthly | what Bobby's Super gives |
|---|---|---|
| Free | $0 | |
| Plus | $8 | |
| Premium | $30 | |
| **Super** | **$100** | **Bobby's tier** |
| Ultra | $200 | |

**ON 12 OCTOBER 2026, X FOLDED GROK, CURSOR AND X PREMIUM INTO ONE
PLAN -- "The X Subscription".** So Bobby's **$100 Super bundle covers
the X posting side AND the Grok writing side together.** That is the
important consequence: **Grok is now inside the same subscription that
carries the posting limits, so the drafting and the distribution come
from one line item.**

**AND THE PAID TIERS SHARE ONE WEEKLY USAGE POOL** between Grok and
Cursor, stated as a multiple of Plus. So Grok usage and Cursor usage
compete with each other inside the same $100.

**AND THE API IS STILL SEPARATE.** The xAI API (for Grok) is a
developer service billed per token, from about **$1 per 1M tokens**,
and it does not come with the subscription. **So "use Grok now" is
answered two ways:**
- **the subscription's Grok** -- inside the $100, for drafting and for
  the interactive work
- **the xAI API** -- per token, for AUTOMATED drafting at volume, and
  it is a separate line item

**AND THE X POSTING API IS PAY-PER-USE AND SEPARATE FROM PREMIUM
TOO:**

| thing | the number |
|---|---|
| **post published** | **$0.015** |
| post containing a **link** | **$0.20** -- a URL tax, **13x** a plain post |
| post read | $0.005 |
| user profile read | $0.010 |
| free tier | **NONE** -- one-time starter credits of up to $70 since Oct 2026 |
| Basic and Pro tiers | **closed to new developers** |
| account-level cap (unverified accounts) | 50 original posts + 200 replies per day |
| reads | 3M posts/month without Enterprise |

**PREMIUM DOES NOT BUY API ACCESS.** Premium buys the account's
posting limits and the Grok/Cursor bundle. **The API is separately
metered.** That is the trap: "we have X Premium" and "we can post
1,500 times a day for free" are different claims.

---

## THE URL TAX IS THE NUMBER THAT DECIDES THE FUNNEL

**$0.015 for a plain post and $0.20 for one with a link is 13x.**

```
50 posts/day/account  x  30 accounts  =  1,500 posts/day
  all plain posts, at $0.015      =  $22.50/day  =  $675/month
  all with a link, at $0.20       =  $300/day    =  $9,000/month
```

**SO THE FUNNEL'S SHAPE IS FORCED: many posts, few links.** And that
is exactly the structure we already built -- the **free chapter** is
the post, and the link to the book is the deliberate, expensive, rare
thing.

**AND THE CHEAPEST WIDE CHANNEL IS NOT SOCIAL AT ALL.** It is our own
site: MEASURED, `vault/30-website/farqueen-site/` holds 106 PHP pages
and 123 level pages. A page per phrase costs hosting and nothing else,
has no limit, no review and no API bill -- and it is the indexed home,
which is the company's stated purpose: *"give indexed homes to the
millions of small repos lacking visibility."*

**SO THE ORDER OF CHEAPNESS, MEASURED:**

| channel | marginal cost | limit | review |
|---|---|---|---|
| **our own page** | hosting only | none | none |
| **Substack post** | free tier | none | none |
| **a Grok-drafted post** | inside the $100 Super | the pool | none |
| **an X post via the API** | $0.015 | 50/day/account | none |
| **an X post with a link** | $0.20 | 50/day/account | none |
| **a book on Amazon** | the slot | **2/format/week** | 3 days to 4 weeks |

---

## THE ACCOUNT QUESTION, and the honest answer

**Bobby's instinct -- many accounts, generous limits -- is right in
shape and wrong in mechanism:**

- **the limits ARE generous on paper** (50 original posts + 200 replies
  per day on an unverified X account)
- **but the API is billed per post**, so the limits make it
  *possible*, not *cheap*
- **and "many accounts" on one platform is a platform-rule risk.** The
  account-per-platform rules target exactly that, and the enforcement
  is on the ACCOUNT -- which is the whole asset, the same escalation
  KDP has.

**SO THE MECHANISM THAT GETS THE SAME MULTIPLICATION WITHOUT THE
RISK: ONE ACCOUNT PER PUBLISHING VOICE.**

We have **19 author voices** in far-writing. Nineteen accounts, each
with its own voice, its own topic, its own reader -- and each one is
a legitimate presence rather than an evasion. **Same multiplication,
and it is the version that does not get a platform to ban us.**

**AND THE RULE THAT KEEPS IT HONEST: no two accounts cover the same
phrase.** One phrase, one book, one account. Near-duplicate accounts
posting near-duplicate content is the pattern every platform's
duplicate-content rule is aimed at, and it is the pattern that gets
the whole estate flagged rather than one post removed.

---

## THE ACCOUNT LEDGER, and it is the missing artifact

**Nothing in the repo holds this.** So the thing to build is a ledger,
and every row carries:

| column | why |
|---|---|
| platform | |
| handle | |
| **the voice it writes in** | one account per voice |
| **the category and phrases it covers** | so no two accounts compete |
| the credential location | in the vault, never in a repo |
| the plan | and its monthly cost |
| posts used / limit | so the ceiling is known before it is hit |
| the account's age | reach depends on it |
| **whether it posts links** | and why -- the URL tax is 13x |

---

## WHAT IS BUILT, and what is not

**BUILT (2026-10-31):**
- `far-writing/tools/keyword_phrases.py` -- the phrase catalog and the
  4-6 word title generator. 47 phrases, 12 categories, 9 skipped with
  reasons.
- `far-writing/tools/build_phrase_pages.py` -- **47 indexed pages, one
  per phrase**, each carrying the measured demand, the top-of-list
  competitors and prices, the supply and the titles the phrase names.
  The pages LINK to each other rather than duplicating each other.
- `social-media/tools/publish.py` -- stage 3: the ebook, the X
  Article, the Substack post, the teaser, the KDP metadata, each with
  a SHA-256 witness, and the royalty computed.

**NOT BUILT, and this is the next thing:**
1. **THE PUBLISHER.** Stage 3 writes the files. Nothing POSTS them,
   and the posting is where the money is spent and the rules live.
2. **THE ACCOUNT LEDGER.** Nothing holds it.
3. **THE API BUDGET.** How many posts a day, how many with links,
   what that costs a month against the $100 Super, and what it buys.
4. **THE REVENUE MEASUREMENT.** Posts made, clicks, and copies sold,
   per title, per account, from the dashboard into the queue.

---

## A SITE DEFECT FOUND ALONG THE WAY, and it is not ours to fix silently

**MEASURED 2026-10-31: the site's 56 level pages include
`./1-style.php`, `./1-header.php` and `./1-footer.php`, and 15 include
`./pagemenu1.php` -- and NONE of those four files exists in
`vault/30-website/farqueen-site/`.** The nearest copies are in
`vault/chat-transcripts/intake/2026-10-09/`.

**So the level pages' includes resolve to nothing from the deployed
directory.** That is a PRE-EXISTING condition of the deployed site and
it is not caused by today's work -- the phrase pages are a separate
set and they use the site's other include set (`style1.php`,
`header1.php`, `footer1.php`), which DOES exist.

**It is recorded here rather than fixed here, because the site is
Bobby's working memory and the fix belongs to whoever owns the
deploy.** And because a deploy that changes 56 pages to add four nav
files is a different risk than adding 47 new pages.

---

## THE STANDING ORDER, and it is unchanged

- **the card is NEVER used.** The `sk-cp-` key is the coding-plan
  key, not the card.
- **the Desktop is copy-only**, never deleted.
- **every number carries the command or the endpoint that produced
  it.** Every figure here says whether it came from Amazon's search
  endpoint (which works from this machine's Nepal store), from KDP's
  own help pages, or from a secondary source -- because **X's own
  pages could not be read directly from this machine (MEASURED)**.
