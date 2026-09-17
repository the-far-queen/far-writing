# AGENTS.md — (far-writing repo)

> A voice is not a vibe.

This file is the contract. Every commit gate checks against it.
Every voice references it. Every test (W1..W5) reads it.

If you change the schema, update AGENTS.md first. The repo is downstream
of this file.

## What this repo is

novels, articles, long-form ebooks, marketing copy, transcripts, scripts, the writing pipeline.

## Packet

```
voice  Voice | AssetRef
```

**No asset without `voice_id` + `hash`.** The gate refuses naked assets.

## Error this repo exists to stop

conflating all writing into one house voice. 'Make it punchy' is not an axis. Voice register, claim density, and structural template are.

## Axes (the voice contract)

A voice is a named writing style, characterized by:

| Axis | Type | Values |
|---|---|---|
| name | string | unique voice id (e.g. "lean", "gritty", "lyric", "didactic") |
| sentence_rhythm | enum | `{periodic, loose, short_shock, mixed, paragraph_block}` |
| vocabulary_register | enum | `{standard_english, vernacular, learned, archaic, modern_slang, technical}` |
| imagery_density | enum | `{low, medium, high, very_high}` |
| tense_default | enum | `{past, present, mixed, future_conditional}` |
| pov_default | enum | `{third_omniscient, first_close, second, multi_pov, free_indirect}` |
| humor_mode | enum | `{satiric, dry, slapstick, absurdist, black, none}` |
| notices | string[] | what this voice pays attention to (physical_detail, social_power, moral_choice, the_joke, the_seam, body_weight, consequence, atmosphere) |
| refuses | string[] | what this voice never does (sentimentality, vulgarity, slapstick, preach, metafiction, narrator_wink, plot_mechanics) |
| example_sentence | string | one sentence that captures the voice |
| voice_id | string | sha256 of canonical(axes), 16 hex chars |
| commit_asset | enum | `{gate, allow, forbid}` |

The schema is the source of truth in `tools/voice.py`. Shipped voices
are the 4 listed in `voice.VOICES` (lean / gritty / lyric / didactic).
Adding a voice = adding a dict to `VOICES` + recomputing its voice_id
+ writing a test for its gate behavior.

## Surface

```python
voice.compile(axes) -> Voice
article.draft(voice, span)
novel.outline(voice, premise)
script.from_voice(voice, scene_units)
edition.diff(a, b) -> changes
```

## Gate

`commit_asset` defaults to `{gate}`. The gate checks:

1. `voice_id` is set.
2. `voice_id == sha256(canonical(axes))`.
3. `variant_of` (if set) is a known parent.
4. No banned-motifs present.
5. Source-discipline: every claim links to a source.

A naked voice (no `voice_id`) is refused with reason `no_voice`.

## Tests

| # | Test | What it checks |
|---|---|---|
| W1 | repro id | Voice with same axes -> same id; different axes -> different id. |
| W2 | banned terms rejected | Voice with banned-terms + asset containing them -> refused. |
| W3 | ids survive restart | Compile + serialize + deserialize -> all ids preserved. |
| W4 | two different settings cannot share id | Vary primary axes -> different id. |
| W5 | prompt without voice does not apply house | Naked prompt + gate -> refused, no fallback to default. |

## Anti-patterns

- house voice default
- vibe paragraphs without axes
- AI-generated claims without source-discipline
- writing without audience-fit.

## Related

- the-far-queen/far-art (style sheets), the-far-queen/simself (MLTR/PSB primitives for compositional analysis)

## License

MIT. Free for all agents, human and non-human.
