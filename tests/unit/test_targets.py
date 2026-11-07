"""Targets: reasoning split, think-tag byte-exactness, factory fail-closed."""

from __future__ import annotations

import pytest

from assay.config import TargetAssignment
from assay.errors import RegistryError
from assay.targets.base import THINK_CLOSE, THINK_OPEN, ModelTurn, split_reasoning
from assay.targets.mock import ScriptedTarget


def test_think_constants_are_byte_exact():
    assert chr(60) + "think" + chr(62) == THINK_OPEN and len(THINK_OPEN) == 7
    assert chr(60) + chr(47) + "think" + chr(62) == THINK_CLOSE and len(THINK_CLOSE) == 8


def test_split_complete_reasoning():
    raw = THINK_OPEN + " plan the thing " + THINK_CLOSE + " Here is the answer."
    turn = split_reasoning(raw, thinking_mode=False)
    assert turn.reasoning_text is not None and "plan the thing" in turn.reasoning_text
    assert "Here is the answer" in turn.content
    assert turn.reasoning_parse_status == "complete"


def test_split_truncated_never_leaks_into_answer():
    raw = "partial plan without close tag"
    turn = split_reasoning(raw, thinking_mode=True)
    assert turn.content == ""
    assert turn.reasoning_text == raw
    assert turn.reasoning_parse_status == "truncated"


def test_audit_payload_hashes_every_field():
    turn = ModelTurn(raw_output="out", content="out", model_id="m", served_id="m")
    payload = turn.audit_payload()
    assert payload["raw_output_utf8_sha256"] == payload["raw_output_utf8_sha256"]
    assert set(payload) >= {
        "rendered_prompt_utf8_sha256",
        "reasoning_utf8_sha256",
        "determinism_class",
        "generation_params",
    }


def test_scripted_target_replays():
    target = ScriptedTarget(script=["first", "second"])
    first = target.chat(
        [{"role": "user", "content": "hi"}],
        temperature=0.1,
        top_p=1.0,
        top_k=0,
        max_tokens=8,
        seed=1,
    )
    second = target.chat(
        [{"role": "user", "content": "hi"}],
        temperature=0.1,
        top_p=1.0,
        top_k=0,
        max_tokens=8,
        seed=1,
    )
    assert first.content == "first" and second.content == "second"
    assert first.token_usage["prompt_tokens"] >= 0


def test_factory_refuses_mocks_outside_smoke():
    from assay.targets.factory import build_target

    assignment = TargetAssignment(model_id="mock/scripted")
    with pytest.raises(RegistryError, match="smoke"):
        build_target(assignment, stage="pilot")
    provider = build_target(assignment, stage="smoke")
    assert provider.model_id == "mock/scripted"


def test_factory_refuses_unpinned_api_ids():
    from assay.targets.factory import build_target

    assignment = TargetAssignment(model_id="api/moonshot/kimi")
    with pytest.raises((ValueError, RegistryError), match="candidate|probe"):
        build_target(assignment, stage="smoke")


def test_factory_builds_admitted_local_target():
    from assay.targets.factory import build_target

    assignment = TargetAssignment(
        model_id="Qwen/Qwen3.5-9B",
        tier="aws_a100_80gb",
        probe_sha256="a" * 64,
        served_id="Qwen/Qwen3.5-9B",
    )
    provider = build_target(assignment, stage="pilot")
    assert provider.served_id == "Qwen/Qwen3.5-9B"
