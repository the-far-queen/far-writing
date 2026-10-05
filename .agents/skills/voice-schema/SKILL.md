---
name: voice-schema
description: >-
  Use when the user wants to compile a writing voice, run the W gate, or pick from the 4
  shipped voices (lean/gritty/lyric/didactic). Triggers: "voice", "voice axes", "compile
  voice", "W gate", "lean voice", "gritty voice".
---

# Voice schema (far-writing)

The voice is the **canonical unit** of writing style in this repo. 4 voices ship: lean / gritty / lyric / didactic.

## Compile

```python
from far_writing.tools.voice import compile_voice, gate_voice, get_voice, list_voices

# Pick a shipped voice
v = get_voice("lean")
# or
v = get_voice("gritty")
v = get_voice("lyric")
v = get_voice("didactic")

# Or compile custom
custom_v = compile_voice({
    "name": "hyper-specific",
    "sentence_rhythm": "short_shock",
    "vocabulary_register": "technical",
    "imagery_density": "medium",
    "tense_default": "present",
    "pov_default": "first_close",
    "humor_mode": "dry",
    "notices": ["physical_detail", "the_joke"],
    "refuses": ["sentimentality", "preach"],
    "example_sentence": "The light in the lobby was the color of weak tea.",
})
```

The voice_id is `sha256(canonical(axes))[:16]`.

## Gate

```python
allow, reason = gate_voice(v, text=...)
```

`commit_asset="gate"` refuses:
- naked text (no voice) → `no_voice`
- sentimentality / metafiction / narrator_wink detected → `refused:<term>`

## Public-domain sources

See `docs/sources.md` in the repo. project gutenberg + wikisource + loc.gov free ebooks.

## See also

- `AGENTS.md` in the repo — the contract (13 voice axes)
- `tools/gate.py` — CLI gate check
- `tools/compile_voice.py` — CLI compile
- 4 shipped voices: lean (Austen-ish), gritty (Didion-ish), lyric (Bolaño-ish), didactic (Chesterton-ish)