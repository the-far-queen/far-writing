# Fountain parsers — research

**Source:** `C:\Users\Admin\Downloads\1a1a.txt` (Bobby paste 2026-09-17)
**Ingested:** 2026-09-17T09:43:57
**Where:** far-writing/tools/

> **For far-author:** you need **tokens** (`CHARACTER`, `HEADING`,
> notes `[[ ]]`), not just HTML. Fountain parsers give you tokens.

## Candidates evaluated

| Tool | Lang | Interest | Limit |
|---|---|---|---|
| [screenplay-tools](https://github.com/wildwinter/screenplay-tools) | JS, Python, C#, C++ | **Best choice multi-lang**; `CHARACTER` + `extension: O.S.` tokens; writes Fountain AND FDX | Pin by tag |
| [fountain-js](https://github.com/jonnygreenwald/fountain-js) | JS/TS | `npm i fountain-js`, spec v1.1, `parse(text, true)` → tokens | Title page keys limited |
| [Fountain.js](https://github.com/mattdaly/Fountain.js/) | JS | Ancestor, drag-drop demo | Not maintained much |
| [screenplay-js](https://github.com/Guernsey-Creative/screenplay-js) | JS | ScriptJSON, responsive HTML | UI layer in plus |
| [Jouvence](https://github.com/ludovicchabant/Jouvence) | Python | `pip install jouvence`, HTML + terminal | No dual-dialogue |
| [fountain-parser](https://github.com/Ovid/fountain-parser) | Perl | Stats: lines / places / pages | Narrow ecosystem |
| [afterwriting](https://afterwriting.com) + [aw-parser](https://github.com/afterwriting/aw-parser) | JS / app | Clean PDF | Parser slightly dated |

## Recommendation

**`screenplay-tools` (Python):** `check_author.py` uses
`screenplay_tools.fountain.parser`.

```python
from screenplay_tools.fountain.parser import Parser
p = Parser()
p.add_text(open("script.fountain").read())
# p.script -> headings, characters, notes
```

## Useful gates

- Each `CHARACTER` has `[[char:...]]` or a registry line.
- Extract `[[voice:...]]` and verify against the `voice_hash`.
- `~lyrics~` only if `form_allow` contains `lyric`.
- Headings `#1#` → `scene_units[]`.

## Obsolete

- `fountain-py` — author replaced by `screenplay-tools`. Don't use.

## License

MIT. Free for all agents, human and non-human.
