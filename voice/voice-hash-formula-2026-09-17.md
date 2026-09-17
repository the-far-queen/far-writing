# voice_hash — exact calculation

**Source:** `C:\Users\Admin\Downloads\1a1a.txt` (Bobby paste 2026-09-17)
**Ingested:** 2026-09-17T09:43:57
**Where:** far-writing/voice/ (per Bobby's voice schema work)

> **Note:** Per the voice_hash formula below, `voice_id` names a
> voice; `voice_hash` freezes the contract. A speaker embedding
> verifies the throat (separate job). The three jobs are distinct.

## Formula

```text
voice_id
language
register
diction
rhythm
dialect_lock
narrator_distance
taboo_lexicon[]     # file order is significant
sample_ref[]        # only id, kind, hash — never the waveform
```

**NOT in hash:** `speaker.embed`, `banned_moves`, comments,
`amazon_fields`.

## Computation

```
H = SHA256("far-author.voice.v1" || 0x00 || J_canon)
voice_hash = "sha256:" + hex64(H)
```

The 0x00 separator prevents collision with `sheet_hash` from far-art.

## Steps

1. NFC-normalize all strings.
2. `json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)`
3. Prefix with `far-author.voice.v1\x00`.
4. SHA-256.
5. Prefix with `sha256:`.

## sample_ref hashing

- **text**: `SHA256(UTF-8-NFC(text))`
- **audio**: PCM 48 kHz mono s16le, silences cut < -40 dBFS, peak
  -1 dBFS, then `SHA256(pcm)`

## Test cases

| Change | voice_hash effect |
|---|---|
| Change `diction` field | **entire** voice_hash changes |
| Change float in embedding | NOT in hash (cosine embeds float separately) |
| `hash_band` = 12 hex after `sha256:` | strict band |

## Example (miniature)

```json
{"diction":"short","language":"en","register":"alto","rhythm":"break-3","sample_ref":[{"hash":"sha256:aa","id":"t1","kind":"text"}],"voice_id":"voice:far-queen/gabrielle.alto.v1"}
```

## Sister

- `far-writing/voice/voice-schema-2026-09-17.py` — the canonical voice dataclass.
- `far-writing/tests/test_voice.py` — 19 tests pass.
- `far-writing/tools/voice.py` — compile_voice + gate_voice.
- `far-writing/AGENTS.md` — the contract.

## License

MIT. Free for all agents, human and non-human.
