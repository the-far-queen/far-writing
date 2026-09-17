"""
voice.py — Voice dataclass + compile_voice() + gate_voice().

The voice gate for far-writing. Mirrors far-art/tools/sheet.py.

A Voice is a named writing style. Every title gets one voice_id,
deterministically derived from the voice's canonical axes. Naked
spans (no voice_id) are refused with reason 'no_voice'.

Sample voices shipped with this version:
- lean       (Austen-ish, ironic omniscient)
- gritty     (Didion-ish, hard observation)
- lyric      (Bolaño-ish, long lyric sentence)
- didactic   (Chesterton-ish, paradox + clarity)

Adding a voice = add a VOICE dict to VOICES + ship a sample
voice_id (sha256(canonical(axes))) for it.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Voice quality axes (the contract)
# ---------------------------------------------------------------------------

# Sentence rhythm
SENTENCE_RHYTHM = {"periodic", "loose", "short_shock", "mixed",
                   "paragraph_block"}
# Vocabulary register
VOCABULARY_REGISTER = {"standard_english", "vernacular", "learned",
                       "archaic", "modern_slang", "technical"}
# Imagery density
IMAGERY_DENSITY = {"low", "medium", "high", "very_high"}
# Tense defaults
TENSE_DEFAULT = {"past", "present", "mixed", "future_conditional"}
# POV default
POV_DEFAULT = {"third_omniscient", "first_close", "second",
               "multi_pov", "free_indirect"}
# Humor mode
HUMOR_MODE = {"satiric", "dry", "slapstick", "absurdist",
              "black", "none"}
# What this voice notices
NOTICES = {"physical_detail", "social_power", "moral_choice",
           "the_joke", "the_seam", "body_weight", "consequence",
           "atmosphere"}
# What this voice refuses (ban list)
REFUSES = {"sentimentality", "vulgarity", "slapstick", "preach",
           "metafiction", "narrator_wink", "plot_mechanics"}


# ---------------------------------------------------------------------------
# Voice (canonical 56-axis record)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Voice:
    name: str
    sentence_rhythm: str
    vocabulary_register: str
    imagery_density: str
    tense_default: str
    pov_default: str
    humor_mode: str
    notices: Tuple[str, ...]
    refuses: Tuple[str, ...]
    example_sentence: str  # one sentence that captures the voice
    voice_id: str  # sha256 of canonical(axes), truncated 16 hex
    commit_asset: str  # "gate" | "allow" | "forbid"


# ---------------------------------------------------------------------------
# Compile (the canonical form for hashing)
# ---------------------------------------------------------------------------

def _canonical(axes: Dict[str, Any]) -> str:
    def norm(v):
        if isinstance(v, (list, tuple)):
            return sorted([norm(x) for x in v])
        if isinstance(v, dict):
            return {k: norm(val) for k, val in sorted(v.items())}
        if v is None:
            return None
        return v

    return json.dumps(norm(axes), sort_keys=True, separators=(",", ":"))


def compile_voice(axes: Dict[str, Any]) -> Voice:
    """Compile a dict of voice axes into a frozen Voice."""
    canonical = _canonical(axes)
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]

    for k, vs, label in [
        ("sentence_rhythm", SENTENCE_RHYTHM, "rhythm"),
        ("vocabulary_register", VOCABULARY_REGISTER, "register"),
        ("imagery_density", IMAGERY_DENSITY, "imagery"),
        ("tense_default", TENSE_DEFAULT, "tense"),
        ("pov_default", POV_DEFAULT, "pov"),
        ("humor_mode", HUMOR_MODE, "humor"),
    ]:
        v = axes.get(k)
        if v is not None and v not in vs:
            raise ValueError(f"{label} axis {k!r}={v!r} not in {sorted(vs)}")

    for k, vs, label in [
        ("notices", NOTICES, "notices"),
        ("refuses", REFUSES, "refuses"),
    ]:
        v = axes.get(k, [])
        if v:
            for item in v:
                if item not in vs:
                    raise ValueError(f"{label} contains {item!r} not in {sorted(vs)}")

    return Voice(
        name=axes["name"],
        sentence_rhythm=axes["sentence_rhythm"],
        vocabulary_register=axes["vocabulary_register"],
        imagery_density=axes["imagery_density"],
        tense_default=axes["tense_default"],
        pov_default=axes["pov_default"],
        humor_mode=axes["humor_mode"],
        notices=tuple(axes.get("notices", [])),
        refuses=tuple(axes.get("refuses", [])),
        example_sentence=axes.get("example_sentence", ""),
        voice_id=digest,
        commit_asset=axes.get("commit_asset", "gate"),
    )


# ---------------------------------------------------------------------------
# Gate (the single commit_asset checker for voice)
# ---------------------------------------------------------------------------

def gate_voice(voice: Optional[Voice], text: str = "") -> Tuple[bool, str]:
    """Check the voice gate. Returns (allow, reason)."""

    if voice is None:
        return False, "no_voice"

    if voice.commit_asset == "forbid":
        return False, "commit_forbidden"

    if voice.commit_asset == "allow":
        return True, "ok"

    # commit_asset == "gate" (default)
    if not voice.voice_id:
        return False, "no_voice_id"

    # Refused patterns (cheap heuristic — production needs full MLTR check)
    if voice.refuses:
        text_lower = text.lower()
        for r in voice.refuses:
            if r == "sentimentality" and any(
                w in text_lower for w in ["beautiful soul", "pure heart",
                                          "tender moment", "lovely scene"]
            ):
                return False, f"refused:{r}"
            if r in ("metafiction", "narrator_wink") and any(
                w in text_lower for w in ["as i write this", "this story",
                                          "the reader should know",
                                          "narrator winks", "as the author"]
            ):
                return False, f"refused:{r}"

    return True, "ok"


# ---------------------------------------------------------------------------
# Sample voices (the 4 shipped)
# ---------------------------------------------------------------------------

VOICES: Dict[str, Dict[str, Any]] = {
    "lean": {
        "name": "lean",
        "sentence_rhythm": "periodic",
        "vocabulary_register": "standard_english",
        "imagery_density": "low",
        "tense_default": "past",
        "pov_default": "third_omniscient",
        "humor_mode": "satiric",
        "notices": ["social_power", "moral_choice", "the_joke"],
        "refuses": ["sentimentality", "vulgarity", "preach"],
        "example_sentence": (
            "It is a truth universally acknowledged, that a single man "
            "in possession of a good fortune, must be in want of a wife."
        ),
        "commit_asset": "gate",
    },
    "gritty": {
        "name": "gritty",
        "sentence_rhythm": "mixed",
        "vocabulary_register": "vernacular",
        "imagery_density": "high",
        "tense_default": "past",
        "pov_default": "first_close",
        "humor_mode": "dry",
        "notices": ["physical_detail", "social_power", "the_seam"],
        "refuses": ["sentimentality", "metafiction"],
        "example_sentence": (
            "The light in the lobby was the color of weak tea, and the "
            "man behind the desk had been reading the same page of his "
            "novel for an hour."
        ),
        "commit_asset": "gate",
    },
    "lyric": {
        "name": "lyric",
        "sentence_rhythm": "paragraph_block",
        "vocabulary_register": "learned",
        "imagery_density": "very_high",
        "tense_default": "mixed",
        "pov_default": "free_indirect",
        "humor_mode": "absurdist",
        "notices": ["atmosphere", "body_weight", "consequence"],
        "refuses": ["slapstick", "plot_mechanics", "narrator_wink"],
        "example_sentence": (
            "The rain had stopped, or seemed to have stopped, somewhere "
            "beyond the window where the dusk was beginning to thicken "
            "into the colour of old silver, and the man at the desk, "
            "who was not a man but the memory of a man, lit another "
            "cigarette and watched the smoke unspool into nothing."
        ),
        "commit_asset": "gate",
    },
    "didactic": {
        "name": "didactic",
        "sentence_rhythm": "short_shock",
        "vocabulary_register": "standard_english",
        "imagery_density": "medium",
        "tense_default": "present",
        "pov_default": "first_close",
        "humor_mode": "dry",
        "notices": ["moral_choice", "the_joke", "consequence"],
        "refuses": ["preach", "vulgarity", "sentimentality"],
        "example_sentence": (
            "The modern world is a complicated place; the people in it "
            "are mostly simple; the result is a kind of permanent, "
            "low-grade tragedy that nobody notices because everyone is "
            "busy."
        ),
        "commit_asset": "gate",
    },
}


def get_voice(name: str) -> Voice:
    """Return one of the shipped voices."""
    if name not in VOICES:
        raise ValueError(f"unknown voice: {name!r}; choices: {sorted(VOICES)}")
    return compile_voice(VOICES[name])


def list_voices() -> List[str]:
    """Return sorted list of shipped voice names."""
    return sorted(VOICES)


def voice_to_dict(voice: Voice) -> Dict[str, Any]:
    """Return a plain dict from a Voice."""
    d = asdict(voice)
    return {k: list(v) if isinstance(v, tuple) else v for k, v in d.items()}


__all__ = [
    "Voice",
    "compile_voice",
    "gate_voice",
    "get_voice",
    "list_voices",
    "voice_to_dict",
    # enums (re-export)
    "SENTENCE_RHYTHM", "VOCABULARY_REGISTER", "IMAGERY_DENSITY",
    "TENSE_DEFAULT", "POV_DEFAULT", "HUMOR_MODE", "NOTICES", "REFUSES",
]
