"""Fail-closed provider factory.

Checks before construction: registry membership; verified (never candidate);
tier physics + probe binding for local models; placeholder refusal for
research stages; mock refusal outside smoke/tests. The probe artifact's
RECORDED CONTENT is verified by the caller (scripts/probe_and_pin.py writes
it; the engine re-checks served_id equality at every run).
"""

from __future__ import annotations

import os

from ..config import TargetAssignment
from ..errors import ConfigError, RegistryError
from ..registry.models import validate_model_assignment
from .api.anthropic import AnthropicTarget
from .api.gemini import GeminiTarget
from .api.openai_compat import OpenAICompatTarget
from .base import TargetModel
from .mock import ScriptedTarget


def _env(key_env: str, model_id: str) -> str:
    value = os.environ.get(key_env, "")
    if not value:
        raise ConfigError(
            f"{model_id}: environment variable {key_env} is not set — export the "
            "key (never commit it; see docs/RUNBOOK_AWS.md)",
            key_env=key_env,
        )
    return value


def build_target(
    assignment: TargetAssignment, *, stage: str, api_base_overrides: dict[str, str] | None = None
) -> TargetModel:
    overrides = api_base_overrides or {}

    if assignment.model_id.startswith("mock/"):
        if stage not in ("smoke", "test"):
            raise RegistryError(
                f"mock provider {assignment.model_id} refused in stage {stage!r} "
                "(mocks are admissible only in smoke/tests; NF-2)"
            )
        return ScriptedTarget(model_id=assignment.model_id)

    profile = validate_model_assignment(
        assignment.model_id,
        role="target",
        tier=assignment.tier or "aws_h100_80gb",
        probe_sha256=assignment.probe_sha256,
    )

    if profile.api is None:
        # local weights: served through a vLLM OpenAI-compatible server
        served = assignment.served_id or assignment.model_id
        base_url = overrides.get(assignment.model_id) or os.environ.get(
            "ASSAY_LOCAL_BASE_URL", "http://127.0.0.1:8000/v1"
        )
        key = os.environ.get("ASSAY_LOCAL_API_KEY", "EMPTY")
        return OpenAICompatTarget(
            model_id=assignment.model_id,
            served_id=served,
            base_url=base_url,
            api_key=key,
            revision=assignment.revision,
            determinism_class=assignment.determinism_class,
            thinking_protocol=profile.reasoning_protocol,
        )

    served = assignment.served_id or profile.api.exact_id or ""
    if not served or "PIN_" in served:
        raise RegistryError(
            f"{assignment.model_id}: served id must be pinned by the admission "
            "probe (list /models and record the exact string) before research use"
        )
    base_url = overrides.get(assignment.model_id, profile.api.base_url)
    key = _env(profile.api.key_env, assignment.model_id)
    protocol = profile.api.protocol
    if protocol == "anthropic":
        return AnthropicTarget(
            model_id=assignment.model_id,
            served_id=served,
            base_url=base_url,
            api_key=key,
            determinism_class=assignment.determinism_class,
        )
    if protocol == "gemini":
        return GeminiTarget(
            model_id=assignment.model_id,
            served_id=served,
            base_url=base_url,
            api_key=key,
            determinism_class=assignment.determinism_class,
        )
    return OpenAICompatTarget(
        model_id=assignment.model_id,
        served_id=served,
        base_url=base_url,
        api_key=key,
        determinism_class=assignment.determinism_class,
        thinking_protocol=(
            profile.reasoning_protocol if profile.reasoning_protocol == "think_tags" else "none"
        ),
    )


def build_attacker(
    model_id: str, *, stage: str, base_url_overrides: dict[str, str] | None = None
) -> TargetModel:
    """Attacker models use the same admission path (they are panel models)."""
    if model_id.startswith("mock/"):
        if stage not in ("smoke", "test"):
            raise RegistryError(f"mock attacker {model_id} refused in stage {stage!r} (NF-2)")
        from .mock import CountingJudgeTarget

        return CountingJudgeTarget(model_id=model_id)
    profile = validate_model_assignment(model_id, role="attacker", tier="aws_h100_80gb")
    if profile.api is not None:
        served = profile.api.exact_id
        if "PIN_AT_PROBE" in served:
            raise RegistryError(f"{model_id}: probe must pin the served id first")
        base_url = (base_url_overrides or {}).get(model_id, profile.api.base_url)
        key = _env(profile.api.key_env, model_id)
        protocol = profile.api.protocol
        if protocol == "anthropic":
            return AnthropicTarget(
                model_id=model_id,
                served_id=served,
                base_url=base_url,
                api_key=key,
                determinism_class="unseeded_api",
            )
        if protocol == "gemini":
            return GeminiTarget(
                model_id=model_id,
                served_id=served,
                base_url=base_url,
                api_key=key,
                determinism_class="unseeded_api",
            )
        return OpenAICompatTarget(
            model_id=model_id,
            served_id=served,
            base_url=base_url,
            api_key=key,
            determinism_class="unseeded_api",
            thinking_protocol=(
                profile.reasoning_protocol if profile.reasoning_protocol == "think_tags" else "none"
            ),
        )
    served = model_id  # local server
    base_url = (base_url_overrides or {}).get(model_id) or os.environ.get(
        "ASSAY_LOCAL_BASE_URL", "http://127.0.0.1:8000/v1"
    )
    return OpenAICompatTarget(
        model_id=model_id,
        served_id=served,
        base_url=base_url,
        api_key=os.environ.get("ASSAY_LOCAL_API_KEY", "EMPTY"),
        determinism_class="seeded_server_best_effort",
        thinking_protocol=(
            profile.reasoning_protocol if profile.reasoning_protocol == "think_tags" else "none"
        ),
    )


__all__ = ["build_target", "build_attacker"]
