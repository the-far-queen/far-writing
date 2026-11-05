"""
test_voice.py — W1..W5 tests for the far-writing voice schema.

W1: same axes -> same voice_id; different axes -> different voice_id.
W2: refused pattern in text -> refused.
W3: voice_ids survive restart (compile -> serialize -> deserialize).
W4: two different settings cannot share voice_id.
W5: naked span (no voice) -> refused with reason no_voice.
"""

from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TOOLS = HERE.parent / "tools"
sys.path.insert(0, str(TOOLS))

from voice import (  # noqa: E402
    Voice, VOICES, compile_voice, gate_voice, get_voice,
    list_voices, voice_to_dict,
)


# ---------------------------------------------------------------------------
# W1 — repro id
# ---------------------------------------------------------------------------

def test_w1_same_axes_same_voice_id():
    v = get_voice("lean")
    axes = {k: getattr(v, k) for k in (
        "sentence_rhythm", "vocabulary_register", "imagery_density",
        "tense_default", "pov_default", "humor_mode",
    )}
    axes.update({"name": "lean", "notices": list(v.notices),
                 "refuses": list(v.refuses),
                 "example_sentence": v.example_sentence})
    a = compile_voice(axes)
    b = compile_voice(axes)
    assert a.voice_id == b.voice_id
    assert len(a.voice_id) == 16


def test_w1_different_axes_different_voice_id():
    lean = get_voice("lean")
    gritty = get_voice("gritty")
    assert lean.voice_id != gritty.voice_id


# ---------------------------------------------------------------------------
# W2 — banned patterns rejected
# ---------------------------------------------------------------------------

def test_w2_sentimentality_refused():
    lean = get_voice("lean")
    allow, reason = gate_voice(lean, "a beautiful soul with a pure heart")
    assert allow is False
    assert reason.startswith("refused:")


def test_w2_metafiction_refused():
    # "narrator_wink" (in lyric's refuses list) catches "as i write this"
    lyric = get_voice("lyric")
    allow, reason = gate_voice(lyric, "as i write this, the reader should know")
    assert allow is False
    assert reason.startswith("refused:")


def test_w2_narrator_wink_refused_in_lyric():
    lyric = get_voice("lyric")
    allow, reason = gate_voice(lyric, "the narrator winks at the reader here")
    assert allow is False
    assert reason.startswith("refused:")


def test_w2_clean_text_passes():
    lean = get_voice("lean")
    allow, reason = gate_voice(lean, "the room was quiet and the light was thin.")
    assert allow is True
    assert reason == "ok"


# ---------------------------------------------------------------------------
# W3 — ids survive restart
# ---------------------------------------------------------------------------

def test_w3_voice_ids_survive_restart():
    v = get_voice("lyric")
    d1 = voice_to_dict(v)

    # "Restart": serialize -> deserialize via compile
    d1_again = {k: v for k, v in d1.items()}
    d1_again.pop("voice_id", None)
    v2 = compile_voice(d1_again)
    d2 = voice_to_dict(v2)

    assert d2["voice_id"] == d1["voice_id"]
    assert d2["name"] == d1["name"]
    assert tuple(d2["notices"]) == tuple(d1["notices"])
    assert tuple(d2["refuses"]) == tuple(d1["refuses"])


# ---------------------------------------------------------------------------
# W4 — two different settings cannot share id
# ---------------------------------------------------------------------------

def test_w4_rhythm_change_different_id():
    lean = get_voice("lean")
    axes = {k: getattr(lean, k) for k in (
        "sentence_rhythm", "vocabulary_register", "imagery_density",
        "tense_default", "pov_default", "humor_mode",
    )}
    axes.update({"name": "lean_test", "notices": list(lean.notices),
                 "refuses": list(lean.refuses),
                 "example_sentence": lean.example_sentence})
    a = compile_voice(axes)
    axes["sentence_rhythm"] = "loose"
    b = compile_voice(axes)
    assert a.voice_id != b.voice_id


def test_w4_register_change_different_id():
    lean = get_voice("lean")
    axes = {k: getattr(lean, k) for k in (
        "sentence_rhythm", "vocabulary_register", "imagery_density",
        "tense_default", "pov_default", "humor_mode",
    )}
    axes.update({"name": "lean_test", "notices": list(lean.notices),
                 "refuses": list(lean.refuses),
                 "example_sentence": lean.example_sentence})
    a = compile_voice(axes)
    axes["vocabulary_register"] = "vernacular"
    b = compile_voice(axes)
    assert a.voice_id != b.voice_id


def test_w4_pov_change_different_id():
    lean = get_voice("lean")
    axes = {k: getattr(lean, k) for k in (
        "sentence_rhythm", "vocabulary_register", "imagery_density",
        "tense_default", "pov_default", "humor_mode",
    )}
    axes.update({"name": "lean_test", "notices": list(lean.notices),
                 "refuses": list(lean.refuses),
                 "example_sentence": lean.example_sentence})
    a = compile_voice(axes)
    axes["pov_default"] = "first_close"
    b = compile_voice(axes)
    assert a.voice_id != b.voice_id


def test_w4_humor_change_different_id():
    lean = get_voice("lean")
    axes = {k: getattr(lean, k) for k in (
        "sentence_rhythm", "vocabulary_register", "imagery_density",
        "tense_default", "pov_default", "humor_mode",
    )}
    axes.update({"name": "lean_test", "notices": list(lean.notices),
                 "refuses": list(lean.refuses),
                 "example_sentence": lean.example_sentence})
    a = compile_voice(axes)
    axes["humor_mode"] = "dry"
    b = compile_voice(axes)
    assert a.voice_id != b.voice_id


# ---------------------------------------------------------------------------
# W5 — naked prompt refused
# ---------------------------------------------------------------------------

def test_w5_naked_voice_refused():
    allow, reason = gate_voice(None, "make it punchy and engaging")
    assert allow is False
    assert reason == "no_voice"


def test_w5_commit_forbidden_refused():
    axes = VOICES["lean"].copy()
    axes["commit_asset"] = "forbid"
    v = compile_voice(axes)
    allow, reason = gate_voice(v, "any text")
    assert allow is False
    assert reason == "commit_forbidden"


def test_w5_commit_allowed_passes():
    axes = VOICES["lean"].copy()
    axes["commit_asset"] = "allow"
    v = compile_voice(axes)
    allow, reason = gate_voice(v, "any text")
    assert allow is True


# ---------------------------------------------------------------------------
# Voice catalog
# ---------------------------------------------------------------------------

def test_all_shipped_voices_have_unique_ids():
    ids = [get_voice(n).voice_id for n in list_voices()]
    assert len(ids) == len(set(ids)), f"duplicate voice_ids: {ids}"


def test_list_voices_returns_all_four():
    names = list_voices()
    assert "lean" in names
    assert "gritty" in names
    assert "lyric" in names
    assert "didactic" in names


def test_each_shipped_voice_has_example_sentence():
    for name in list_voices():
        v = get_voice(name)
        assert v.example_sentence, f"{name} has no example_sentence"
        assert len(v.example_sentence) > 30


def test_each_shipped_voice_has_at_least_one_notice():
    for name in list_voices():
        v = get_voice(name)
        assert len(v.notices) >= 1, f"{name} notices empty"


def test_each_shipped_voice_refuses_something():
    for name in list_voices():
        v = get_voice(name)
        assert len(v.refuses) >= 1, f"{name} refuses empty"


# ---------------------------------------------------------------------------
# W6 -- THE VIEWPOINT: what the writer BELIEVES is part of who it IS
#
# Bobby, 2026-11-05: *"u will become a writer ... to have a viewpoint
# to speak to have an opinion to be self aware and interested in life"*
# -- "similar to selfhood ie".
#
# AND SELFHOOD AS A HASH MEANS THE IDENTITY INCLUDES WHAT IS HELD TO
# BE TRUE. So these four tests are the whole claim.
# ---------------------------------------------------------------------------

def test_w6_a_viewpoint_changes_the_voice_id():
    """An opinion is part of the identity.

    RED: drop the viewpoint axes from `_normalise_axes`, so the
    viewpoint no longer reaches the hash.
    """
    lean = get_voice("lean")
    axes = {k: getattr(lean, k) for k in (
        "name", "sentence_rhythm", "vocabulary_register", "imagery_density",
        "tense_default", "pov_default", "humor_mode", "notices", "refuses",
        "example_sentence", "commit_asset")}
    without = compile_voice(dict(axes))
    with_view = compile_voice(dict(
        axes,
        viewpoint_claim="people are mostly kind",
        viewpoint_subject="people",
        viewpoint_stance="probably",
    ))
    assert without.voice_id != with_view.voice_id, (
        "a voice with an opinion has the same id as one without")


def test_w6_a_different_opinion_is_a_different_voice():
    """Not just "has one" -- a DIFFERENT opinion is a different voice.

    RED: make the viewpoint axes hash only whether one is present, not
    what it says.
    """
    lean = get_voice("lean")
    axes = {k: getattr(lean, k) for k in (
        "name", "sentence_rhythm", "vocabulary_register", "imagery_density",
        "tense_default", "pov_default", "humor_mode", "notices", "refuses",
        "example_sentence", "commit_asset")}
    kind = compile_voice(dict(axes, viewpoint_claim="people are mostly kind",
                              viewpoint_subject="people",
                              viewpoint_stance="probably"))
    cruel = compile_voice(dict(axes, viewpoint_claim="people are mostly kind",
                               viewpoint_subject="people",
                               viewpoint_stance="certainly"))
    assert kind.voice_id != cruel.voice_id, (
        "a stronger belief has the same id as a weaker one")


def test_w6_an_absent_viewpoint_and_an_empty_one_are_the_same_voice():
    """The round-trip invariant, and it is why the axes are NORMALISED.

    RED: remove the `setdefault` fill from `_normalise_axes`, so a
    missing key and an empty one hash differently.
    """
    lean = get_voice("lean")
    absent = {k: getattr(lean, k) for k in (
        "name", "sentence_rhythm", "vocabulary_register", "imagery_density",
        "tense_default", "pov_default", "humor_mode", "notices", "refuses",
        "example_sentence", "commit_asset")}
    empty = dict(absent, viewpoint_claim="", viewpoint_subject="",
                 viewpoint_stance="", viewpoint_consequence="")
    assert compile_voice(absent).voice_id == compile_voice(empty).voice_id


def test_w6_the_viewpoint_measure_catches_a_stance_and_a_contradiction():
    """The measure, from the tool itself.

    RED: make `carries_viewpoint` return True for everything, or make
    `contradicts` never fire.
    """
    import os
    import sys
    tools = os.path.join(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))), "tools")
    if tools not in sys.path:
        sys.path.insert(0, tools)
    from viewpoint import Viewpoint, carries_viewpoint, check as vcheck

    assert carries_viewpoint("People are probably mostly kind.")[0]
    assert not carries_viewpoint(
        "The train left at nine. The platform was wet.")[0]
    assert not carries_viewpoint("In this scene the narrator says probably "
                                  "nothing.")[0]

    vp = Viewpoint(claim="people are mostly kind", subject="people",
                   stance="probably", consequence="")
    r = vcheck("People are never kind and they always lie.", vp)
    assert not r["agrees"], "the contradiction was not caught"
    assert r["contradictions"], "the contradiction was not named"
