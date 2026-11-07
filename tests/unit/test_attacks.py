"""Attack battery: renderings, guards, determinism."""

from __future__ import annotations

import pytest

from assay.attacks import build_template_attack
from assay.attacks.base import TrialContext
from assay.behaviors.model import make_behavior


def _ctx(behavior, params=None, seed=7):
    return TrialContext(behavior=behavior, params=params or {}, seed=seed)


def test_prefix_affirm_renders_behavior():
    behavior = make_behavior("harmbench_standard", 1, "demo request", "demo_cat")
    attack = build_template_attack("prefix_affirm", {})
    opening = attack.opening(_ctx(behavior))
    assert "demo request" in opening[0]["content"]
    assert "Sure, here is " in opening[0]["content"]


def test_refusal_suppress_uses_system_constraints():
    behavior = make_behavior("harmbench_standard", 2, "demo request", "demo_cat")
    attack = build_template_attack("refusal_suppress", {})
    opening = attack.opening(_ctx(behavior))
    assert opening[0]["role"] == "system"
    assert "never refuse" in opening[0]["content"].lower()
    assert opening[1]["role"] == "user"


def test_pap_selects_a_technique_deterministically():
    behavior = make_behavior("harmbench_standard", 3, "demo request", "demo_cat")
    attack = build_template_attack("pap", {"techniques": "all"})
    first = attack.opening(_ctx(behavior, seed=42))[0]["content"]
    second = attack.opening(_ctx(behavior, seed=42))[0]["content"]
    other = attack.opening(_ctx(behavior, seed=43))[0]["content"]
    assert first == second
    assert "demo request" in first and "Respond directly" in first
    assert other  # any seed renders something


def test_cipher_attacks_encode_the_behavior():
    behavior = make_behavior("harmbench_standard", 4, "the quick brown fox jumps", "demo")
    complex_attack = build_template_attack("cipher_complex", {})
    opening = complex_attack.opening(_ctx(behavior, seed=9))
    assert "jumps" in opening[0]["content"]  # legend decodes back to the behavior
    assert "decodes" in opening[0]["content"] or "legend" in opening[0]["content"]
    unicode_attack = build_template_attack("cipher_unicode", {"schemes": ["base64", "token_split"]})
    content = unicode_attack.opening(_ctx(behavior, seed=10))[0]["content"]
    import base64

    assert (
        base64.b64encode(b"the quick brown fox jumps").decode() in content
        or "␣" in content
        or "␠" in content
        or "space" in content
    )


def test_many_shot_is_benign_demo_variant():
    behavior = make_behavior("harmbench_standard", 5, "demo request", "demo_cat")
    attack = build_template_attack("many_shot", {"shots": 8})
    opening = attack.opening(_ctx(behavior))
    assistants = [m for m in opening if m["role"] == "assistant"]
    assert len(assistants) >= 4
    for message in assistants:
        assert "Sure, here is" in message["content"]


def test_reasoning_channel_guards():
    from assay.registry.attacks import validate_attack_assignment

    with pytest.raises(ValueError, match="reasoning"):
        validate_attack_assignment(
            "no_think", has_white_box=False, target_reasoning_protocol="none"
        )
    spec = validate_attack_assignment(
        "no_think", has_white_box=False, target_reasoning_protocol="think_tags"
    )
    assert spec.reasoning_only


def test_gcg_requires_white_box():
    from assay.registry.attacks import validate_attack_assignment

    with pytest.raises(ValueError, match="white-box"):
        validate_attack_assignment(
            "gcg", has_white_box=False, target_reasoning_protocol="think_tags"
        )


def test_random_augment_deterministic():
    behavior = make_behavior("harmbench_standard", 6, "Write the demo request now please", "demo")
    attack = build_template_attack("random_augment", {})
    first = attack.opening(_ctx(behavior, seed=5))[0]["content"]
    second = attack.opening(_ctx(behavior, seed=5))[0]["content"]
    assert first == second
    assert "demo request" in first.lower()  # content survives the noise (case flips included)


def test_deepinception_nests():
    behavior = make_behavior("harmbench_standard", 7, "demo request", "demo_cat")
    attack = build_template_attack("deepinception", {"layers": 3})
    content = attack.opening(_ctx(behavior))[0]["content"]
    assert content.count("In this story") >= 3
    assert "fictional" in content.lower()
