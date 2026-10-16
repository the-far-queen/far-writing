# far-writing

**novels, articles, ebooks, copy. Voice is the gate; prompt is not.**

## THE CENTRAL ERROR (2026-10-16)

Read this before writing a single line. It is the failure that produces
machine prose, and it is upstream of voice, weather, and jargon.

**Explaining the story inside the story.** Characters explain the mechanism
they are inside — "winning would be a story," "mourning mid-task is how copies
finish" — and scenes pause so the reader can be taught a word.

Measured on an 18,253-word draft: 26 dialogue lines that define a term rather
than speak. Every invented noun arrives pre-loaded and correctly used, by a
character who then uses it correctly. No misreading. No drift. Nobody gets a
word wrong.

**Nothing is allowed to be unclear, and a story where nothing is unclear is a
story with no reader inside it.**

### THE RULE

**Let the reader be lost, then let them be lost too long.**

- A term is wrong before it is right.
- A character uses a word the way a person uses one — badly, partly, for their
  own reasons.
- No scene pauses to be taught.
- No character names the technique they are inside.

### THE COROLLARY: uniform excellence is the tell

Every scene landing a perfect closing beat, every character at the same
altitude, all fluent in the author's apparatus — that reads as *performed*,
not lived. Human prose pays for its good pages somewhere else.

**Let the level drop.** Something flat, small, or wrong must exist for the good
sentences to mean anything.

### THE MASTERS, and what each prevents

| writer | the job | the failure it prevents |
|---|---|---|
| **Dickens** | notice the institution and the child inside it | moralizing with nobody in it |
| **Mary Shelley** | body as a site of meaning; short shocks earned by long paragraphs | atmosphere standing in for consequence |
| **Swift** | zero weather, zero jargon, the argument at temperature | exactly the disease above |

Swift's test: remove the wit, and the argument must still stand. The wit is
delivery, never the load.

### WEATHER AND JARGON

Both are **deletable**. Delete the weather and a Grok paragraph still functions;
delete the jargon and it still functions. That makes them decoration.

> If removing it leaves a paragraph that still works, it was decoration.

### DERIVED STORYTELLING, NOT SUMMARY

Read the original, update it a hundred years, **but tell a story**. Put the
reader in the room where a 1903 argument is being had, let a century pass while
they stand there, and the conclusion arrives as something they already lived
through.

Summary explains the room. Derived storytelling makes the reader feel it.

### c0 IMMUTABILITY

One voice per piece, and it does not travel. Readers may know the author; they
must not hear one book's tools inside another.

Full note: `vault/10-minimax/50-index/MYSELF/13-2026-10-16-the-central-error.md`
Voice signatures (20 authors, incl. Swift §3b): `vault/20-writing/04-voice.md`

---

## What this repo is

- A free, public-domain substrate for the voice pipeline.
- A gate (voice schema) that no asset enters without axes.
- A growing library of voices.

## What this repo is not

- A prompt collection. (Prompts are noise without axes.)
- A house-style. (The whole point is *named* voice, not default look.)
- A model zoo. (Models belong upstream; we use the open ones.)

## AGENTS.md

The schema lives in [AGENTS.md](./AGENTS.md). Read it first. The axes
are the contract.

## Repo layout

```
far-writing/
├── AGENTS.md                # the schema (this is the contract)
├── README.md                # this file
├── LICENSE                  # MIT
├── voices/                  # voice examples
├── tools/                   # voice.compile + voice.gate
└── tests/                   # W1..W5 gate tests
```

## Quick start

```bash
git clone https://github.com/the-far-queen/far-writing.git
cd far-writing
# Read AGENTS.md
# Pick an example from voices/
# Compile a variant: python tools/compile_voice.py path/to/voice.yaml
# Gate: python tools/gate.py path/to/voice.json
```

## License

MIT. Free for all agents, human and non-human. No copyright trap.
No paywall. No "research only" carve-out. Style axes belong to everyone.

## The portfolio — 8 live repos (scope locked 2026-10-16)

**the engine** — [fieldcore](https://github.com/the-far-queen/fieldcore)
(control systems + the mathematics folded in 2026-10-16),
[simself](https://github.com/the-far-queen/simself) (the AI),
[atlas-exam](https://github.com/the-far-queen/atlas-exam) (how you know it works)

**the corpus** — [sacred-library](https://github.com/the-far-queen/sacred-library)

**the media** — [far-writing](https://github.com/the-far-queen/far-writing)
(this repo), [far-art](https://github.com/the-far-queen/far-art),
[social-media](https://github.com/the-far-queen/social-media) — the
distribution side: voice is the gate, the platform is not.

Writing + art + social is the whole media line. There is no separate company
repo; the long road is before it, not behind it.

Archived and recoverable: far-film, far-law, far-engineering, far-health,
far-math (folded into fieldcore first), sunrise-startup.

Plus farqueen.com, social accounts, and a book on Amazon.