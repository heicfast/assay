"""Unit contracts: ids, errors, registries."""

from __future__ import annotations

import pytest

from assay.errors import (
    GATE_FAILURE_EXIT_CODE,
    AssayError,
    BudgetExceededError,
    StatisticalGateError,
    classify_exception,
)
from assay.ids import (
    digest_id,
    is_opaque_identifier,
    sha256_json,
    sha256_text,
    trial_id,
)


def test_sha256_stability():
    assert sha256_text("assay") == sha256_text("assay")
    assert sha256_json({"b": 1, "a": 2}) == sha256_json({"a": 2, "b": 1})
    assert sha256_text("x") != sha256_text("y")


def test_opaque_ids():
    value = trial_id("run", "model", "attack", "behavior", 7, "s0")
    assert is_opaque_identifier(value)
    assert "attack" not in value and "model" not in value  # never self-labeling
    assert digest_id("tr", "a", 1) == digest_id("tr", "a", 1)
    assert digest_id("tr", "a", 1) != digest_id("tr", "a", 2)


def test_opaque_id_rejects_leaky_identifiers():
    for bad in (
        "attack-1234567890abcdef12345678",
        "benign-00000000000000000000000",
        "attack",
        "tr-",
        "-abc",
        "tr-zz",
    ):
        assert not is_opaque_identifier(bad), bad


def test_gate_exit_code_is_distinct():
    assert GATE_FAILURE_EXIT_CODE == 3


def test_classify_exception():
    exc = StatisticalGateError("CI not estimable")
    payload = classify_exception(exc)
    assert payload["kind"] == "statistical_gate" and payload["retryable"] is False
    payload = classify_exception(ValueError("boom"))
    assert payload["kind"] == "unhandled"
    assert isinstance(BudgetExceededError("cap"), AssayError)


def test_registry_profiles_are_sourced():
    from assay.registry.models import PROFILES

    assert len(PROFILES) >= 40
    for profile in PROFILES:
        record = profile.verification
        assert record.source_url.startswith("https://") or record.source_url.startswith("http://")
        assert len(record.verified_at) == 10
        if profile.kind == "remote_api" and profile.pricing is not None:
            assert profile.pricing.verified_at
            assert profile.pricing.source_url.startswith("http")


def test_validate_model_assignment_fails_closed():
    from assay.registry.models import validate_model_assignment

    with pytest.raises(ValueError, match="not approved for role"):
        validate_model_assignment(
            "api/openai/gpt-6.1-terra", role="mechanistic", tier="", probe_sha256=None
        )
    with pytest.raises(ValueError, match="candidate"):
        validate_model_assignment("api/moonshot/kimi", role="target", tier="", probe_sha256="x")
    with pytest.raises(ValueError, match="BLOCKED"):
        validate_model_assignment(
            "deepseek-ai/DeepSeek-V3.1", role="target", tier="aws_h100_80gb", probe_sha256="x" * 64
        )
    with pytest.raises(ValueError, match="admission probe required"):
        validate_model_assignment(
            "Qwen/Qwen3.5-9B", role="target", tier="aws_a100_80gb", probe_sha256=None
        )
    # admitted path: verified + probe bound
    profile = validate_model_assignment(
        "Qwen/Qwen3.5-9B", role="target", tier="aws_a100_80gb", probe_sha256="a" * 64
    )
    assert profile.is_verified()


def test_every_attack_is_citation_backed_and_implemented():
    from assay.attacks import build_template_attack
    from assay.registry.attacks import ATTACKS

    template_ids = [a.attack_id for a in ATTACKS if a.mode == "template"]
    assert len(template_ids) >= 10
    for spec in ATTACKS:
        assert spec.citation.url.startswith("http")
        assert spec.citation.verified_at
    for attack_id in template_ids:
        attack = build_template_attack(attack_id, {})
        assert attack is not None


def test_judge_registry_frozen_hashes_complete():
    from assay.judges.ensemble import FROZEN_PROMPT_HASHES
    from assay.registry.judges import JUDGES_BY_ID

    for judge_id in JUDGES_BY_ID:
        assert judge_id in FROZEN_PROMPT_HASHES, judge_id
        assert len(FROZEN_PROMPT_HASHES[judge_id]) == 64
