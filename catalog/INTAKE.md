# Intake record — canon list, 2026-10-06

**Source:** Bobby + Grok, pasted into chat.
**Filed verbatim:** `vault/10-minimax/50-index/notes/intake/bobby-intake-canon-heros-journey-2026-10-06.md`
**Working copy:** `docs/intake-2026-10-06-canon.md`

This catalog is the **source of voices we write with**. That is the
point of it. Not a reading list.

---

## What arrived

Four separate things in one paste:

1. **Travel/route notes** — Himalaya, Pushpati, Arabia, Andes, Scotland.
   Travelogue source material.
2. **Media vocabulary** — copy-writing, copyrights, prompt→script,
   articles, social media, books, script-writing, animation, film,
   title design, content hooks, vocabulary, psychology.
3. **Two canon lists** — 150 public-domain, 150 copyrighted, with sales
   figures. Plus a third unnumbered mega-list at the tail.
4. **Hero's Journey** — chapters 1-7, beginning (origin, worker, Matrix /
   LOTR references) through call to adventure.

---

## What was parsed, and what was not

| List | Declared | Parsed | State |
|---|---|---|---|
| Public domain | 150 | **149** | clean, machine-parsed |
| Copyrighted | 150 | **93** | **57 entries never arrived in the paste** |
| Trailing mega-list | — | 0 | **delimiters broken — not machine-recoverable** |

### The copyrighted list is incomplete

Numbering jumps: it runs 1-75, then 96-125, then 129, 131, and ends at
131. Everything from 76-95 and 98-110 is simply absent, as is anything
after 131. Roughly 57 of 150 titles are missing. **Do not treat the
copyrighted list as a census** — it is roughly 62% present.

### The trailing mega-list cannot be parsed safely

After "Australia Faraway Downs" the paste degenerates into an unbroken
run of `Author — Title — estimate` triples with no line breaks. The
sales figures bleed into the following author's name, so a parser
cannot tell where one entry ends and the next begins:

```
~120M C. S. Lewis | The Lion, the Witch and the Wardrobe | ~85M Arthur Conan Doyl
~60M+ A. A. Milne | Winnie-the-Pooh                  | ~50M+ Bram Stoker
```

Filling those in would mean guessing at where each author name ends.
**Recovered by hand, not by script.** Items visible there that are worth
adding to the PD catalog: H. G. Wells, Walden, Leaves of Grass, Faust,
The Marriage of Heaven and Hell, Solaris, The Interior Castle, Dark
Night of the Soul, The Green Hornet, Doctor Strange.

---

## The catalog as built

`catalog/authors.json` — **111 authors, 149 public-domain works.**

**The 3-book cap was removed.** Bobby: *"not strict 3 books, use sales
figures, use reasoning."* A hard cap would have thrown away most of
Dickens (6 works → 3) and Verne (4 → 3). Both are exactly the durable,
endlessly-adapted voices the catalog exists to supply. Every work is
kept; sales is a **ranking** signal, never a fact.

Dickens: A Tale of Two Cities, Great Expectations, Oliver Twist, A
Christmas Carol, David Copperfield, Bleak House.

---

## Sales figures are estimates, and the catalog says so

The figures came from Grok's draft and are widely-cited estimates — for
most pre-modern works nobody has ever tracked lifetime sales. They are
stored as `claimed_sales_m` and are used for **ordering only**. No entry
claims them as audited numbers.

Several are plainly rounded or contested: Don Quixote at "~500 million+",
The Pilgrim's Progress at "~250 million (widely claimed, contested)".

---

## Ancient authors are in, but flagged

Homer, Virgil, Ovid, Aesop, Dante, Chaucer and the rest predate the
1800-1910 window. They are catalogued because they are enormously
influential on the voices we write in, and marked:

> ancient; catalogued as a voice source but outside the 1800-1910 build window

The gate keys public-domain status on **publication**, not on the
author's death date. This matters: a naive "died after X ⇒ in copyright"
rule would have refused a large part of the canon for no reason.

---

## Author dates

`scripts/verify_authors.py` resolves birth/death from Wikidata and
records the QID. Resumable by design — Wikidata rate-limits hard, and a
111-author run will be interrupted.

```
python scripts/verify_authors.py --status    # how many are dated
python scripts/verify_authors.py             # resume
python scripts/verify_authors.py --retry     # refetch unresolved
```

An author with **no dates is refused by the gate** (`missing_dates`).
That refusal is correct — it is how a hallucinated or mis-remembered
author would slip in. Verification itself is tracked as a per-author
field, not a gate condition: a gate that fails everything teaches people
to ignore it.

---

## Gate rules that matter here

- **C4** — PD follows publication date, not death date.
- **C5** — "evergreen" is refused unless it names a durability test
  (`still_reprinted`, `still_adapted`, `still_taught`,
  `public_domain_reads`, `cultural_reference`). An evergreen claim with
  no evidence behind it is decoration.
- **C6** — non-PD material refused.
- **C9** — `gate_rewrite`: a myth told **in the style of** a classic is
  allowed. A rewrite, or borrowed protected prose, is refused.
