"""
compile_voice.py — CLI for compiling a voice YAML/JSON file.

Usage:
    python tools/compile_voice.py path/to/voice.yaml
    python tools/compile_voice.py --stdin   # JSON via stdin
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from voice import compile_voice, voice_to_dict  # noqa: E402


def _load_yaml(path: Path) -> dict:
    """Tiny YAML loader. Tries JSON first, then minimal YAML."""
    text = path.read_text(encoding="utf-8")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    out = {}
    for line in text.splitlines():
        line = line.rstrip()
        if not line or line.lstrip().startswith("#"):
            continue
        if ":" not in line:
            raise ValueError(f"Cannot parse YAML line: {line!r}")
        key, _, val = line.partition(":")
        key = key.strip()
        val = val.strip()
        if len(val) >= 2 and val[0] == val[-1] and val[0] in ('"', "'"):
            val = val[1:-1]
        # Naive list parsing for `notices` / `refuses`
        if val.startswith("[") and val.endswith("]"):
            items = val[1:-1].split(",")
            val = [i.strip().strip('"').strip("'") for i in items if i.strip()]
        out[key] = val
    return out


def main(argv):
    p = argparse.ArgumentParser(description="Compile a far-writing voice.")
    p.add_argument("path", nargs="?", help="Path to voice YAML/JSON file.")
    p.add_argument("--stdin", action="store_true", help="Read JSON from stdin.")
    args = p.parse_args(argv)

    if args.stdin:
        axes = json.loads(sys.stdin.read())
    elif args.path:
        path = Path(args.path)
        if not path.exists():
            print(f"error: {path} does not exist", file=sys.stderr)
            return 2
        axes = _load_yaml(path)
    else:
        # No arg: list shipped voices
        from voice import list_voices, get_voice, voice_to_dict
        print("shipped voices:")
        for name in list_voices():
            v = get_voice(name)
            d = voice_to_dict(v)
            print(f"  {name:10s} voice_id={d['voice_id']}  example: {d['example_sentence'][:60]}...")
        return 0

    try:
        voice = compile_voice(axes)
    except (KeyError, ValueError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    out = voice_to_dict(voice)
    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
