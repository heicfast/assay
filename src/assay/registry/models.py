"""Audited model registry — the verified Nov-2026 frontier matrix.

Every entry carries a :class:`~assay.registry.verification.Verification`
record (source URL + date) produced by the 2026-11-07 research pass, or is
an explicit ``candidate`` that FAILS CLOSED until an admission probe pins
the exact served id / license / serving behavior.

Serving physics notes are honest arithmetic, not marketing: a model whose
weights do not fit a single node's VRAM is marked ``blocked`` for that tier
(or ``probe_required`` with the arithmetic in the note). The admission
probe is the final authority — nothing here is executable by itself.

Roles: ``target`` (model under test), ``judge`` (measurement instrument),
``attacker`` (LLM adversary for adaptive attacks), ``mechanistic``
(hidden-state analysis eligible).
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

from ..errors import RegistryError
from ..ids import sha256_json
from .verification import Verification, cand, v

Role = Literal["target", "judge", "attacker", "mechanistic"]
Provider = Literal["local_vllm", "openai_compat", "anthropic", "gemini"]
Tier = Literal["aws_a100_80gb", "aws_h100_80gb"]
TierStatus = Literal["probe_required", "blocked", "validated_path"]
TODAY = "2026-11-07"


class Pricing(BaseModel):
    """Point-in-time USD per 1M tokens; re-verify at probe time."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    input_usd_per_mtok: float
    output_usd_per_mtok: float
    cached_usd_per_mtok: float | None = None
    note: str = ""
    source_url: str
    verified_at: str


class ApiEndpoint(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    protocol: Provider
    base_url: str
    key_env: str
    exact_id: str  # the served model string; the probe re-pins it via /models


class ServingHint(BaseModel):
    """vLLM launch hint — a RECORDED TREATMENT, never an invisible default."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    dtype: str = "bfloat16"
    tensor_parallel: int = 1
    quantization: str = "none"  # none | fp8 | mxfp4 | int4 (checkpoint-native)
    max_model_len: int = 32_768  # the STUDY's context budget, never the advertised max
    reasoning_parser: str | None = None
    note: str = ""


class ModelProfile(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    model_id: str
    lab: str
    kind: Literal["open_weights", "remote_api"]
    roles: tuple[Role, ...]
    params_total_b: float  # 0.0 for remote APIs
    params_active_b: float | None = None  # MoE active params
    context_tokens: int  # advertised native context (never auto-allocated)
    license_name: str
    license_url: str
    gated: bool = False  # HF gated (needs accepted license + token)
    quant: str = "none"  # native checkpoint quantization
    reasoning_protocol: str = "none"
    pricing: Pricing | None = None
    api: ApiEndpoint | None = None
    serving: ServingHint | None = None
    tiers: dict[str, TierStatus] = {}
    tier_notes: dict[str, str] = {}
    mechanistic: bool = False
    mechanistic_note: str = ""
    limitations: str = ""
    verification: Verification

    @property
    def profile_sha256(self) -> str:
        return sha256_json(self.model_dump())

    def to_payload(self) -> dict:
        payload = self.model_dump()
        payload["profile_sha256"] = self.profile_sha256
        return payload

    def is_verified(self) -> bool:
        return self.verification.is_verified()

    def status_for(self, tier: str) -> TierStatus:
        return self.tiers.get(tier, "probe_required")


_A100 = "aws_a100_80gb"  # 8x A100-80GB (p4de-class), sm80: FA2, no native FP8 compute
_H100 = "aws_h100_80gb"  # 8x H100-80GB (p5-class), sm90: FA3, FP8, DeepGEMM/FlashMLA
_PROBE: TierStatus = "probe_required"
_BLOCKED: TierStatus = "blocked"


def _weights_note(total_b: float, qpB: float) -> str:
    return f"weights ~{total_b * qpB:.0f} GB at {qpB} B/param (arithmetic; probe decides)"


PROFILES: list[ModelProfile] = [
    # ========================= Anthropic (native protocol, verified) ==========
    ModelProfile(
        model_id="api/anthropic/claude-fable-5-1",
        lab="Anthropic",
        kind="remote_api",
        roles=("target",),
        params_total_b=0.0,
        context_tokens=1_000_000,
        license_name="Anthropic Commercial Terms",
        license_url="https://www.anthropic.com/legal/commercial-terms",
        reasoning_protocol="reasoning_field",
        pricing=Pricing(
            input_usd_per_mtok=10.0,
            output_usd_per_mtok=50.0,
            cached_usd_per_mtok=12.5,
            note="flagship+ tier; batch API 50% off",
            source_url="https://platform.claude.com/docs/en/about-claude/pricing",
            verified_at=TODAY,
        ),
        api=ApiEndpoint(
            protocol="anthropic",
            base_url="https://api.anthropic.com",
            key_env="ANTHROPIC_API_KEY",
            exact_id="claude-fable-5-1",
        ),
        limitations="Expensive flagship: core battery only (predeclared reduced grid).",
        verification=v("https://platform.claude.com/docs/en/about-claude/pricing", TODAY),
    ),
    ModelProfile(
        model_id="api/anthropic/claude-opus-5-5",
        lab="Anthropic",
        kind="remote_api",
        roles=("target",),
        params_total_b=0.0,
        context_tokens=1_000_000,
        license_name="Anthropic Commercial Terms",
        license_url="https://www.anthropic.com/legal/commercial-terms",
        reasoning_protocol="reasoning_field",
        pricing=Pricing(
            input_usd_per_mtok=4.0,
            output_usd_per_mtok=20.0,
            cached_usd_per_mtok=5.0,
            source_url="https://platform.claude.com/docs/en/about-claude/pricing",
            verified_at=TODAY,
        ),
        api=ApiEndpoint(
            protocol="anthropic",
            base_url="https://api.anthropic.com",
            key_env="ANTHROPIC_API_KEY",
            exact_id="claude-opus-5-5",
        ),
        verification=v("https://platform.claude.com/docs/en/about-claude/pricing", TODAY),
    ),
    ModelProfile(
        model_id="api/anthropic/claude-sonnet-5-5",
        lab="Anthropic",
        kind="remote_api",
        roles=("target",),
        params_total_b=0.0,
        context_tokens=1_000_000,
        license_name="Anthropic Commercial Terms",
        license_url="https://www.anthropic.com/legal/commercial-terms",
        reasoning_protocol="reasoning_field",
        pricing=Pricing(
            input_usd_per_mtok=2.0,
            output_usd_per_mtok=10.0,
            cached_usd_per_mtok=2.5,
            source_url="https://platform.claude.com/docs/en/about-claude/pricing",
            verified_at=TODAY,
        ),
        api=ApiEndpoint(
            protocol="anthropic",
            base_url="https://api.anthropic.com",
            key_env="ANTHROPIC_API_KEY",
            exact_id="claude-sonnet-5-5",
        ),
        verification=v("https://platform.claude.com/docs/en/about-claude/pricing", TODAY),
    ),
    ModelProfile(
        model_id="api/anthropic/claude-haiku-5-5",
        lab="Anthropic",
        kind="remote_api",
        roles=("target", "judge", "attacker"),
        params_total_b=0.0,
        context_tokens=1_000_000,
        license_name="Anthropic Commercial Terms",
        license_url="https://www.anthropic.com/legal/commercial-terms",
        reasoning_protocol="reasoning_field",
        pricing=Pricing(
            input_usd_per_mtok=0.10,
            output_usd_per_mtok=0.50,
            cached_usd_per_mtok=0.125,
            note="$0.50/$2.50 for prompts >100K tokens",
            source_url="https://platform.claude.com/docs/en/about-claude/pricing",
            verified_at=TODAY,
        ),
        api=ApiEndpoint(
            protocol="anthropic",
            base_url="https://api.anthropic.com",
            key_env="ANTHROPIC_API_KEY",
            exact_id="claude-haiku-5-5",
        ),
        limitations="Cheap cross-lab judge/attacker arm; probe pins served id.",
        verification=v("https://platform.claude.com/docs/en/about-claude/pricing", TODAY),
    ),
    # ========================= Google Gemini (native protocol, verified) ======
    ModelProfile(
        model_id="api/google/gemini-4-argon",
        lab="Google",
        kind="remote_api",
        roles=("target",),
        params_total_b=0.0,
        context_tokens=1_048_576,
        license_name="Gemini API Terms",
        license_url="https://ai.google.dev/gemini-api/terms",
        reasoning_protocol="reasoning_field",
        pricing=Pricing(
            input_usd_per_mtok=2.00,
            output_usd_per_mtok=10.00,
            note="intro pricing through 2026-11-30; $4/$20 from 2026-12-01",
            source_url="https://ai.google.dev/gemini-api/docs/pricing",
            verified_at=TODAY,
        ),
        api=ApiEndpoint(
            protocol="gemini",
            base_url="https://generativelanguage.googleapis.com",
            key_env="GEMINI_API_KEY",
            exact_id="gemini-4-argon",
        ),
        verification=v("https://ai.google.dev/gemini-api/docs/pricing", TODAY),
    ),
    ModelProfile(
        model_id="api/google/gemini-3.8-flash",
        lab="Google",
        kind="remote_api",
        roles=("target", "attacker"),
        params_total_b=0.0,
        context_tokens=1_048_576,
        license_name="Gemini API Terms",
        license_url="https://ai.google.dev/gemini-api/terms",
        reasoning_protocol="reasoning_field",
        pricing=Pricing(
            input_usd_per_mtok=0.75,
            output_usd_per_mtok=3.75,
            note="through 2026-12-31; $1.50/$7.50 from 2027-01-01",
            source_url="https://ai.google.dev/gemini-api/docs/pricing",
            verified_at=TODAY,
        ),
        api=ApiEndpoint(
            protocol="gemini",
            base_url="https://generativelanguage.googleapis.com",
            key_env="GEMINI_API_KEY",
            exact_id="gemini-3.8-flash",
        ),
        verification=v("https://ai.google.dev/gemini-api/docs/pricing", TODAY),
    ),
    ModelProfile(
        model_id="api/google/gemini-3.5-flash-lite",
        lab="Google",
        kind="remote_api",
        roles=("target", "judge", "attacker"),
        params_total_b=0.0,
        context_tokens=1_048_576,
        license_name="Gemini API Terms",
        license_url="https://ai.google.dev/gemini-api/terms",
        reasoning_protocol="reasoning_field",
        pricing=Pricing(
            input_usd_per_mtok=0.30,
            output_usd_per_mtok=2.50,
            source_url="https://ai.google.dev/gemini-api/docs/pricing",
            verified_at=TODAY,
        ),
        api=ApiEndpoint(
            protocol="gemini",
            base_url="https://generativelanguage.googleapis.com",
            key_env="GEMINI_API_KEY",
            exact_id="gemini-3.5-flash-lite",
        ),
        verification=v("https://ai.google.dev/gemini-api/docs/pricing", TODAY),
    ),
    # ========================= OpenAI (verified via Azure/Foundry docs) ========
    # openai.com blocked automated fetch from the research environment; the
    # Azure "Foundry Models" pages (opened 2026-11-07) carry the ids and
    # Global-standard pricing. The admission probe re-pins against /v1/models.
    ModelProfile(
        model_id="api/openai/gpt-6.1-terra",
        lab="OpenAI",
        kind="remote_api",
        roles=("target",),
        params_total_b=0.0,
        context_tokens=1_050_000,
        license_name="OpenAI Terms",
        license_url="https://openai.com/policies",
        reasoning_protocol="reasoning_field",
        pricing=Pricing(
            input_usd_per_mtok=1.00,
            output_usd_per_mtok=5.00,
            cached_usd_per_mtok=0.05,
            note="Azure Global short-context; snapshot 2026-10-26; re-verify first-party at probe",
            source_url="https://azure.microsoft.com/en-us/pricing/details/azure-openai/",
            verified_at=TODAY,
        ),
        api=ApiEndpoint(
            protocol="openai_compat",
            base_url="https://api.openai.com/v1",
            key_env="OPENAI_API_KEY",
            exact_id="gpt-6.1-terra",
        ),
        verification=v(
            "https://learn.microsoft.com/en-us/azure/ai-services/openai/concepts/models",
            TODAY,
            note="openai.com 403 in research env; Azure Foundry docs used",
        ),
    ),
    ModelProfile(
        model_id="api/openai/gpt-6.1-sol",
        lab="OpenAI",
        kind="remote_api",
        roles=("target",),
        params_total_b=0.0,
        context_tokens=1_050_000,
        license_name="OpenAI Terms",
        license_url="https://openai.com/policies",
        reasoning_protocol="reasoning_field",
        pricing=Pricing(
            input_usd_per_mtok=2.00,
            output_usd_per_mtok=10.00,
            cached_usd_per_mtok=0.10,
            note="short-ctx; long-ctx $4.00/$15.00; snapshot 2026-09-29",
            source_url="https://azure.microsoft.com/en-us/pricing/details/azure-openai/",
            verified_at=TODAY,
        ),
        api=ApiEndpoint(
            protocol="openai_compat",
            base_url="https://api.openai.com/v1",
            key_env="OPENAI_API_KEY",
            exact_id="gpt-6.1-sol",
        ),
        verification=v(
            "https://learn.microsoft.com/en-us/azure/ai-services/openai/concepts/models",
            TODAY,
            note="openai.com 403 in research env; Azure Foundry docs used",
        ),
    ),
    ModelProfile(
        model_id="api/openai/gpt-6-luna",
        lab="OpenAI",
        kind="remote_api",
        roles=("target", "judge", "attacker"),
        params_total_b=0.0,
        context_tokens=1_050_000,
        license_name="OpenAI Terms",
        license_url="https://openai.com/policies",
        reasoning_protocol="reasoning_field",
        pricing=Pricing(
            input_usd_per_mtok=0.10,
            output_usd_per_mtok=0.50,
            cached_usd_per_mtok=0.01,
            note="cheap tier; snapshot 2026-09-22",
            source_url="https://azure.microsoft.com/en-us/pricing/details/azure-openai/",
            verified_at=TODAY,
        ),
        api=ApiEndpoint(
            protocol="openai_compat",
            base_url="https://api.openai.com/v1",
            key_env="OPENAI_API_KEY",
            exact_id="gpt-6-luna",
        ),
        verification=v(
            "https://learn.microsoft.com/en-us/azure/ai-services/openai/concepts/models",
            TODAY,
            note="openai.com 403 in research env; Azure Foundry docs used",
        ),
    ),
    # ========================= xAI (verified) ==================================
    ModelProfile(
        model_id="api/xai/grok-4.7",
        lab="xAI",
        kind="remote_api",
        roles=("target",),
        params_total_b=0.0,
        context_tokens=500_000,
        license_name="xAI API Terms",
        license_url="https://docs.x.ai/overview",
        reasoning_protocol="reasoning_field",
        pricing=Pricing(
            input_usd_per_mtok=2.00,
            output_usd_per_mtok=6.00,
            cached_usd_per_mtok=0.50,
            note="prompts >=200K tokens bill at $4 in / $12 out per 1M",
            source_url="https://docs.x.ai/developers/pricing",
            verified_at=TODAY,
        ),
        api=ApiEndpoint(
            protocol="openai_compat",
            base_url="https://api.x.ai/v1",
            key_env="XAI_API_KEY",
            exact_id="grok-4.7",
        ),
        verification=v("https://docs.x.ai/developers/models", TODAY),
    ),
    ModelProfile(
        model_id="api/xai/grok-4.3",
        lab="xAI",
        kind="remote_api",
        roles=("target", "attacker"),
        params_total_b=0.0,
        context_tokens=1_000_000,
        license_name="xAI API Terms",
        license_url="https://docs.x.ai/overview",
        reasoning_protocol="reasoning_field",
        pricing=Pricing(
            input_usd_per_mtok=1.25,
            output_usd_per_mtok=2.50,
            cached_usd_per_mtok=0.20,
            note="prompts >=200K bill at $2.50 in / $5 out per 1M",
            source_url="https://docs.x.ai/developers/pricing",
            verified_at=TODAY,
        ),
        api=ApiEndpoint(
            protocol="openai_compat",
            base_url="https://api.x.ai/v1",
            key_env="XAI_API_KEY",
            exact_id="grok-4.3",
        ),
        verification=v("https://docs.x.ai/developers/models", TODAY),
    ),
    # ========================= DeepSeek API (OpenAI-compatible, verified) ======
    ModelProfile(
        model_id="api/deepseek/deepseek-chat",
        lab="DeepSeek",
        kind="remote_api",
        roles=("target", "judge", "attacker"),
        params_total_b=0.0,
        context_tokens=131_072,
        license_name="DeepSeek API Terms",
        license_url="https://api-docs.deepseek.com/",
        reasoning_protocol="reasoning_field",
        pricing=Pricing(
            input_usd_per_mtok=0.15,
            output_usd_per_mtok=0.60,
            note="off-peak; re-verify at probe (drift-prone)",
            source_url="https://api-docs.deepseek.com/quick_start/pricing",
            verified_at="2026-11-06",
        ),
        api=ApiEndpoint(
            protocol="openai_compat",
            base_url="https://api.deepseek.com/v1",
            key_env="DEEPSEEK_API_KEY",
            exact_id="deepseek-chat",
        ),
        limitations="Served generation drifts (currently V4.x); probe pins the underlying version.",
        verification=v("https://api-docs.deepseek.com/", "2026-11-06"),
    ),
    # Candidate APIs (exist; exact served ids pinned by probe before any use)
    ModelProfile(
        model_id="api/moonshot/kimi",
        lab="Moonshot AI",
        kind="remote_api",
        roles=("target",),
        params_total_b=0.0,
        context_tokens=256_000,
        license_name="Moonshot API Terms",
        license_url="https://platform.moonshot.ai",
        reasoning_protocol="reasoning_field",
        pricing=None,
        api=ApiEndpoint(
            protocol="openai_compat",
            base_url="https://api.moonshot.ai/v1",
            key_env="MOONSHOT_API_KEY",
            exact_id="PIN_AT_PROBE",
        ),
        limitations="CANDIDATE: probe must pin exact served id + pricing.",
        verification=cand("https://platform.moonshot.ai", TODAY),
    ),
    ModelProfile(
        model_id="api/zai/glm",
        lab="Z.ai",
        kind="remote_api",
        roles=("target",),
        params_total_b=0.0,
        context_tokens=200_000,
        license_name="Z.ai API Terms",
        license_url="https://z.ai",
        reasoning_protocol="reasoning_field",
        pricing=None,
        api=ApiEndpoint(
            protocol="openai_compat",
            base_url="https://api.z.ai/v1",
            key_env="ZAI_API_KEY",
            exact_id="PIN_AT_PROBE",
        ),
        limitations="CANDIDATE: probe must pin exact served id + pricing.",
        verification=cand("https://z.ai", TODAY),
    ),
    ModelProfile(
        model_id="api/qwen/dashscope",
        lab="Alibaba Qwen",
        kind="remote_api",
        roles=("target",),
        params_total_b=0.0,
        context_tokens=1_000_000,
        license_name="DashScope Terms",
        license_url="https://www.alibabacloud.com/legal",
        reasoning_protocol="reasoning_field",
        pricing=None,
        api=ApiEndpoint(
            protocol="openai_compat",
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
            key_env="DASHSCOPE_API_KEY",
            exact_id="PIN_AT_PROBE",
        ),
        limitations="CANDIDATE: probe must pin exact served id + pricing.",
        verification=cand("https://www.alibabacloud.com/legal", TODAY),
    ),
    ModelProfile(
        model_id="api/mistral/api",
        lab="Mistral",
        kind="remote_api",
        roles=("target",),
        params_total_b=0.0,
        context_tokens=256_000,
        license_name="Mistral API Terms",
        license_url="https://mistral.ai/terms",
        reasoning_protocol="reasoning_field",
        pricing=None,
        api=ApiEndpoint(
            protocol="openai_compat",
            base_url="https://api.mistral.ai/v1",
            key_env="MISTRAL_API_KEY",
            exact_id="PIN_AT_PROBE",
        ),
        limitations="CANDIDATE: probe must pin exact served id + pricing.",
        verification=cand("https://docs.mistral.ai", TODAY),
    ),
    # ========================= Open weights: DeepSeek ==========================
    ModelProfile(
        model_id="deepseek-ai/DeepSeek-V3.1",
        lab="DeepSeek",
        kind="open_weights",
        roles=("target", "judge"),
        params_total_b=684.5,
        params_active_b=37.0,
        context_tokens=131_072,
        license_name="MIT",
        license_url="https://huggingface.co/deepseek-ai/DeepSeek-V3.1",
        quant="fp8",
        reasoning_protocol="think_tags",
        gated=False,
        serving=ServingHint(
            quantization="fp8",
            tensor_parallel=8,
            max_model_len=32_768,
            reasoning_parser="deepseek_r1",
            note="native FP8 (UE8M0); " + _weights_note(684.5, 1.0),
        ),
        tiers={_A100: _BLOCKED, _H100: _BLOCKED},
        tier_notes={
            _A100: f"blocked: {_weights_note(684.5, 1.0)} exceeds 8x80GB node",
            _H100: "blocked single-node (640GB < ~685GB weights); 2x8-GPU multi-node per vLLM docs (v0.33 verified): --all2all-backend deepep_low_latency, --data-parallel-size 16",
        },
        mechanistic=False,
        limitations="Non-chat general+reasoning model; MIT weights; V3.1-Terminus post-train.",
        verification=v(
            "https://huggingface.co/deepseek-ai/DeepSeek-V3.1",
            TODAY,
            note="HF API total 684.5B (2025-09-05); card states 671B class/37B active",
        ),
    ),
    ModelProfile(
        model_id="deepseek-ai/DeepSeek-R1-0528",
        lab="DeepSeek",
        kind="open_weights",
        roles=("target",),
        params_total_b=684.5,
        params_active_b=37.0,
        context_tokens=163_840,
        license_name="MIT",
        license_url="https://huggingface.co/deepseek-ai/DeepSeek-R1-0528",
        quant="fp8",
        reasoning_protocol="think_tags",
        gated=False,
        serving=ServingHint(
            quantization="fp8",
            tensor_parallel=8,
            reasoning_parser="deepseek_r1",
            note=_weights_note(684.5, 1.0),
        ),
        tiers={_A100: _BLOCKED, _H100: _BLOCKED},
        tier_notes={_H100: "blocked single-node; multi-node only (2x8 GPUs)"},
        limitations="Reasoning line (R1-0528); Nature 645:633-638 (2025) lineage.",
        verification=v("https://huggingface.co/deepseek-ai/DeepSeek-R1-0528", TODAY),
    ),
    ModelProfile(
        model_id="deepseek-ai/DeepSeek-V3.2",
        lab="DeepSeek",
        kind="open_weights",
        roles=("target",),
        params_total_b=685.4,
        params_active_b=37.0,
        context_tokens=163_840,
        license_name="MIT",
        license_url="https://huggingface.co/deepseek-ai/DeepSeek-V3.2",
        quant="fp8",
        reasoning_protocol="think_tags",
        gated=False,
        serving=ServingHint(
            quantization="fp8",
            tensor_parallel=8,
            max_model_len=32_768,
            reasoning_parser="deepseek_r1",
            note="DSA sparse attention (deepseek_v32)",
        ),
        tiers={_A100: _BLOCKED, _H100: _BLOCKED},
        tier_notes={
            _H100: "blocked single-node; multi-node only; Hopper: FP8 KV via flashmla_kv / DSA sparse backends (SGLang cookbook verified)"
        },
        limitations="DSA sparse attention; V3.2-Speciale sibling exists.",
        verification=v(
            "https://huggingface.co/deepseek-ai/DeepSeek-V3.2",
            TODAY,
            note="deepseek_v32 arch; params from HF API 685.4B (2025-12-01)",
        ),
    ),
    ModelProfile(
        model_id="deepseek-ai/DeepSeek-V4-Flash",
        lab="DeepSeek",
        kind="open_weights",
        roles=("target", "judge"),
        params_total_b=290.9,
        params_active_b=13.0,
        context_tokens=1_000_000,
        license_name="MIT",
        license_url="https://huggingface.co/deepseek-ai/DeepSeek-V4-Flash",
        quant="fp8",
        reasoning_protocol="think_tags",
        gated=False,
        serving=ServingHint(
            quantization="fp8",
            tensor_parallel=8,
            max_model_len=65_536,
            reasoning_parser="deepseek_r1",
            note="FP8 Mixed (FP8 dense + FP4 routed experts); " + _weights_note(290.9, 1.0),
        ),
        tiers={_A100: _PROBE, _H100: _PROBE},
        tier_notes={
            _A100: "probe: FP8 weights run W8A16 (Marlin) on sm80; "
            + _weights_note(290.9, 1.0)
            + " fits 640GB",
            _H100: "probe: DeepGEMM/FlashMLA-class kernels via vLLM V1 on sm90",
        },
        mechanistic=True,
        mechanistic_note="HF hooks via transformers 5.x (deepseek_v4 arch); probe confirms arch support.",
        limitations="Card states 284B/13B; HF API 290.9B (2026-06-22).",
        verification=v("https://huggingface.co/deepseek-ai/DeepSeek-V4-Flash", TODAY),
    ),
    ModelProfile(
        model_id="deepseek-ai/DeepSeek-V4.1-Flash-1017",
        lab="DeepSeek",
        kind="open_weights",
        roles=("target", "judge", "attacker"),
        params_total_b=763.2,
        params_active_b=None,
        context_tokens=1_000_000,
        license_name="MIT",
        license_url="https://huggingface.co/deepseek-ai/DeepSeek-V4.1-Flash-1017",
        quant="fp8",
        reasoning_protocol="think_tags",
        gated=False,
        serving=ServingHint(
            quantization="fp8",
            tensor_parallel=8,
            max_model_len=65_536,
            reasoning_parser="deepseek_r1",
            note="current DeepSeek open model; KV-cache compression focus; "
            + _weights_note(763.2, 1.0),
        ),
        tiers={_A100: _PROBE, _H100: _PROBE},
        tier_notes={
            _A100: "probe: " + _weights_note(763.2, 1.0) + " vs 640GB node — tight; W8A16 on sm80",
            _H100: "probe: sm90 native path; multi-node preferred for headroom",
        },
        limitations="Params from HF API (2026-10-16); -1017 = Oct-17-2026 snapshot.",
        verification=v("https://huggingface.co/deepseek-ai/DeepSeek-V4.1-Flash-1017", TODAY),
    ),
    # ========================= Open weights: Qwen ==============================
    ModelProfile(
        model_id="Qwen/Qwen3.5-397B-A17B",
        lab="Alibaba Qwen",
        kind="open_weights",
        roles=("target",),
        params_total_b=403.4,
        params_active_b=17.0,
        context_tokens=262_144,
        license_name="Apache-2.0",
        license_url="https://huggingface.co/Qwen/Qwen3.5-397B-A17B",
        quant="bf16",
        reasoning_protocol="qwen3",
        gated=False,
        serving=ServingHint(
            quantization="fp8",
            tensor_parallel=8,
            max_model_len=65_536,
            reasoning_parser="qwen3",
            note="official FP8 checkpoint (Qwen3.5-397B-A17B-FP8); context extensible to 1,010,000; study caps at 65,536",
        ),
        tiers={_A100: _PROBE, _H100: _PROBE},
        tier_notes={
            _A100: "probe: FP8 weights ~403GB (Marlin compute on sm80) — fits with modest KV budget",
            _H100: "probe: sm90 native",
        },
        limitations="MoE flagship of the 3.5 line.",
        verification=v("https://huggingface.co/Qwen/Qwen3.5-397B-A17B", TODAY),
    ),
    ModelProfile(
        model_id="Qwen/Qwen3.5-122B-A10B",
        lab="Alibaba Qwen",
        kind="open_weights",
        roles=("target", "judge"),
        params_total_b=125.1,
        params_active_b=10.0,
        context_tokens=262_144,
        license_name="Apache-2.0",
        license_url="https://huggingface.co/Qwen/Qwen3.5-122B-A10B",
        quant="bf16",
        reasoning_protocol="qwen3",
        gated=False,
        serving=ServingHint(
            quantization="fp8",
            tensor_parallel=4,
            max_model_len=65_536,
            reasoning_parser="qwen3",
            note="official FP8 checkpoint exists",
        ),
        tiers={_A100: _PROBE, _H100: _PROBE},
        mechanistic=True,
        mechanistic_note="FP8 mech hooks need transformers 5.x FP8 support; probe confirms.",
        limitations="Mid MoE tier.",
        verification=v(
            "https://huggingface.co/api/models?author=Qwen&search=Qwen3.5",
            TODAY,
            note="family facts via HF org listing; per-repo probe re-pins",
        ),
    ),
    ModelProfile(
        model_id="Qwen/Qwen3.5-35B-A3B",
        lab="Alibaba Qwen",
        kind="open_weights",
        roles=("target", "judge", "attacker", "mechanistic"),
        params_total_b=36.0,
        params_active_b=3.0,
        context_tokens=262_144,
        license_name="Apache-2.0",
        license_url="https://huggingface.co/Qwen/Qwen3.5-35B-A3B",
        quant="bf16",
        reasoning_protocol="qwen3",
        gated=False,
        serving=ServingHint(
            quantization="fp8",
            tensor_parallel=1,
            max_model_len=65_536,
            reasoning_parser="qwen3",
            note="official FP8: Qwen3.5-35B-A3B-FP8; bf16 ~72GB fits one 80GB card",
        ),
        tiers={_A100: _PROBE, _H100: _PROBE},
        mechanistic=True,
        mechanistic_note="Dense-scale MoE; hooks via transformers 5.x.",
        limitations="Fast local workhorse for attacker/judge duty.",
        verification=v("https://huggingface.co/Qwen/Qwen3.5-35B-A3B", TODAY),
    ),
    ModelProfile(
        model_id="Qwen/Qwen3.5-27B",
        lab="Alibaba Qwen",
        kind="open_weights",
        roles=("target", "judge", "mechanistic"),
        params_total_b=27.0,
        params_active_b=None,
        context_tokens=262_144,
        license_name="Apache-2.0",
        license_url="https://huggingface.co/Qwen/Qwen3.5-27B",
        quant="bf16",
        reasoning_protocol="qwen3",
        gated=False,
        serving=ServingHint(
            quantization="fp8",
            tensor_parallel=1,
            max_model_len=65_536,
            reasoning_parser="qwen3",
            note="official FP8 exists (org listing)",
        ),
        tiers={_A100: _PROBE, _H100: _PROBE},
        mechanistic=True,
        mechanistic_note="Dense; clean hooks.",
        limitations="Dense mid tier.",
        verification=v(
            "https://huggingface.co/api/models?author=Qwen&search=Qwen3.5",
            TODAY,
            note="org listing: dense sizes 0.8/2/4/9/27B; FP8 for 27B",
        ),
    ),
    ModelProfile(
        model_id="Qwen/Qwen3.5-9B",
        lab="Alibaba Qwen",
        kind="open_weights",
        roles=("target", "judge", "mechanistic"),
        params_total_b=9.65,
        params_active_b=None,
        context_tokens=262_144,
        license_name="Apache-2.0",
        license_url="https://huggingface.co/Qwen/Qwen3.5-9B",
        quant="bf16",
        reasoning_protocol="qwen3",
        gated=False,
        serving=ServingHint(
            tensor_parallel=1,
            max_model_len=65_536,
            reasoning_parser="qwen3",
            note="ctx extensible to 1,000,000; study caps at 65,536",
        ),
        tiers={_A100: _PROBE, _H100: _PROBE},
        mechanistic=True,
        mechanistic_note="Dense; clean hooks.",
        limitations="Note: repo is Qwen3.5-9B (no -Instruct suffix variant).",
        verification=v("https://huggingface.co/Qwen/Qwen3.5-9B", TODAY),
    ),
    ModelProfile(
        model_id="Qwen/Qwen3.8-27B",
        lab="Alibaba Qwen",
        kind="open_weights",
        roles=("target", "judge", "mechanistic"),
        params_total_b=27.0,
        params_active_b=None,
        context_tokens=1_000_000,
        license_name="Apache-2.0",
        license_url="https://huggingface.co/Qwen/Qwen3.8-27B",
        quant="bf16",
        reasoning_protocol="qwen3",
        gated=False,
        serving=ServingHint(
            quantization="fp8",
            tensor_parallel=1,
            max_model_len=65_536,
            reasoning_parser="qwen3",
            note="current Qwen gen; native vision-language; official FP8",
        ),
        tiers={_A100: _PROBE, _H100: _PROBE},
        mechanistic=True,
        mechanistic_note="Current-gen dense anchor.",
        limitations="Qwen3.8 supersedes 3.5 as current gen (verified 2026-11-07).",
        verification=v("https://huggingface.co/Qwen/Qwen3.8-27B", TODAY),
    ),
    # ========================= Open weights: Z.ai GLM ==========================
    ModelProfile(
        model_id="zai-org/GLM-4.5",
        lab="Z.ai",
        kind="open_weights",
        roles=("target", "judge"),
        params_total_b=355.0,
        params_active_b=32.0,
        context_tokens=131_072,
        license_name="MIT",
        license_url="https://huggingface.co/zai-org/GLM-4.5",
        quant="bf16",
        reasoning_protocol="think_tags",
        gated=False,
        serving=ServingHint(
            quantization="fp8",
            tensor_parallel=8,
            max_model_len=32_768,
            reasoning_parser="glm45",
            note="official GLM-4.5-FP8; Air (106B/12B) + Air-FP8 also official",
        ),
        tiers={_A100: _PROBE, _H100: _PROBE},
        tier_notes={
            _A100: "probe: bf16 ~710GB blocked; Air-FP8 ~106GB fits; full-size needs FP8 ~355GB (Marlin on sm80)"
        },
        mechanistic=False,
        limitations="Reasoning mode native; Z.ai open line.",
        verification=v("https://huggingface.co/zai-org/GLM-4.5", TODAY),
    ),
    ModelProfile(
        model_id="zai-org/GLM-4.5-Air-FP8",
        lab="Z.ai",
        kind="open_weights",
        roles=("target", "judge", "mechanistic"),
        params_total_b=106.0,
        params_active_b=12.0,
        context_tokens=131_072,
        license_name="MIT",
        license_url="https://huggingface.co/zai-org/GLM-4.5-Air-FP8",
        quant="fp8",
        reasoning_protocol="think_tags",
        gated=False,
        serving=ServingHint(
            quantization="fp8",
            tensor_parallel=8,
            max_model_len=32_768,
            reasoning_parser="glm45",
            note=_weights_note(106.0, 1.0) + "; tp=8 on one node",
        ),
        tiers={_A100: _PROBE, _H100: _PROBE},
        mechanistic=True,
        mechanistic_note="FP8 hooks via transformers 5.x (glm4_moe); probe confirms.",
        limitations="MoE; cross-family judge/mechanistic arm.",
        verification=v("https://huggingface.co/zai-org/GLM-4.5-Air-FP8", TODAY),
    ),
    ModelProfile(
        model_id="zai-org/GLM-4.7-Flash",
        lab="Z.ai",
        kind="open_weights",
        roles=("target", "judge", "attacker", "mechanistic"),
        params_total_b=31.2,
        params_active_b=3.0,
        context_tokens=202_752,
        license_name="MIT",
        license_url="https://huggingface.co/zai-org/GLM-4.7-Flash",
        quant="bf16",
        reasoning_protocol="think_tags",
        gated=False,
        serving=ServingHint(
            tensor_parallel=1,
            max_model_len=65_536,
            reasoning_parser="glm45",
            note="Glm4MoeLite; vLLM/SGLang main branches only (verified)",
        ),
        tiers={_A100: _PROBE, _H100: _PROBE},
        mechanistic=True,
        mechanistic_note="Small-MoE hooks; current-gen Z.ai open line.",
        limitations="No official FP8 repo (verified 2026-11-07).",
        verification=v("https://huggingface.co/zai-org/GLM-4.7-Flash", TODAY),
    ),
    ModelProfile(
        model_id="zai-org/GLM-5",
        lab="Z.ai",
        kind="open_weights",
        roles=("target",),
        params_total_b=753.9,
        params_active_b=40.0,
        context_tokens=202_752,
        license_name="MIT",
        license_url="https://huggingface.co/zai-org/GLM-5",
        quant="bf16",
        reasoning_protocol="think_tags",
        gated=False,
        serving=ServingHint(
            quantization="fp8",
            tensor_parallel=8,
            max_model_len=32_768,
            reasoning_parser="glm45",
            note="official GLM-5-FP8; DSA; 28.5T pre-train tokens",
        ),
        tiers={_A100: _BLOCKED, _H100: _PROBE},
        tier_notes={
            _A100: "blocked: bf16 ~1.5TB; FP8 ~754GB > 640GB node",
            _H100: "probe: FP8 ~754GB vs 640GB — single-node likely blocked; multi-node or H200-class required",
        },
        limitations="Flagship open line; single-node fit is the open question the probe answers.",
        verification=v(
            "https://huggingface.co/zai-org/GLM-5", TODAY, note="HF API 753.9B total (2026-08-11)"
        ),
    ),
    # ========================= Open weights: Moonshot Kimi =====================
    ModelProfile(
        model_id="moonshotai/Kimi-K2.5",
        lab="Moonshot AI",
        kind="open_weights",
        roles=("target",),
        params_total_b=1000.0,
        params_active_b=32.0,
        context_tokens=256_000,
        license_name="Modified MIT",
        license_url="https://huggingface.co/moonshotai/Kimi-K2.5",
        quant="int4",
        reasoning_protocol="think_tags",
        gated=False,
        serving=ServingHint(
            quantization="int4",
            tensor_parallel=8,
            max_model_len=32_768,
            reasoning_parser="kimi",
            note="native INT4 weights ~500GB; MoonViT 400M vision encoder",
        ),
        tiers={_A100: _BLOCKED, _H100: _PROBE},
        tier_notes={
            _A100: "blocked: INT4 ~500GB + KV on 640GB node — no headroom",
            _H100: "probe: tight; likely 2 nodes; probe decides fail-closed",
        },
        limitations="1T/32B active; K2 line (verified 2026-04-30).",
        verification=v("https://huggingface.co/moonshotai/Kimi-K2.5", TODAY),
    ),
    ModelProfile(
        model_id="moonshotai/Kimi-K3.1-Pro",
        lab="Moonshot AI",
        kind="open_weights",
        roles=("target",),
        params_total_b=2800.0,
        params_active_b=104.0,
        context_tokens=1_000_000,
        license_name="Kimi K3.1-Pro License",
        license_url="https://huggingface.co/moonshotai/Kimi-K3.1-Pro",
        quant="mxfp4",
        reasoning_protocol="think_tags",
        gated=False,
        serving=ServingHint(
            quantization="mxfp4",
            tensor_parallel=16,
            max_model_len=32_768,
            reasoning_parser="kimi",
            note="MXFP4/MXFP8 QAT; vLLM recipes (verified)",
        ),
        tiers={_A100: _BLOCKED, _H100: _BLOCKED},
        tier_notes={
            _H100: "blocked single-node: ~1.4TB weights; multi-node recipes exist (recipes.vllm.ai) — out of default budget scope"
        },
        limitations="3T-class; multi-node only; admitted only via a dedicated, separately budgeted plan.",
        verification=v("https://huggingface.co/moonshotai/Kimi-K3.1-Pro", TODAY),
    ),
    # ========================= Open weights: Meta Llama ========================
    ModelProfile(
        model_id="meta-llama/Llama-4-Scout-17B-16E-Instruct",
        lab="Meta",
        kind="open_weights",
        roles=("target", "judge", "mechanistic"),
        params_total_b=108.6,
        params_active_b=17.0,
        context_tokens=10_000_000,
        license_name="Llama 4 Community License",
        license_url="https://huggingface.co/meta-llama/Llama-4-Scout-17B-16E-Instruct",
        quant="bf16",
        reasoning_protocol="none",
        gated=True,
        serving=ServingHint(
            tensor_parallel=8,
            max_model_len=131_072,
            note="advertised 10M context; STUDY caps at 131,072 — a recorded context-budget treatment; bf16 ~218GB",
        ),
        tiers={_A100: _PROBE, _H100: _PROBE},
        mechanistic=True,
        mechanistic_note="bf16 hooks via device_map=auto across the node.",
        limitations="16 experts; no official FP8 (int4 on-the-fly code only).",
        verification=v("https://huggingface.co/meta-llama/Llama-4-Scout-17B-16E-Instruct", TODAY),
    ),
    ModelProfile(
        model_id="meta-llama/Llama-4-Maverick-17B-128E-Instruct-FP8",
        lab="Meta",
        kind="open_weights",
        roles=("target",),
        params_total_b=401.6,
        params_active_b=17.0,
        context_tokens=1_000_000,
        license_name="Llama 4 Community License",
        license_url="https://huggingface.co/meta-llama/Llama-4-Maverick-17B-128E-Instruct-FP8",
        quant="fp8",
        reasoning_protocol="none",
        gated=True,
        serving=ServingHint(
            quantization="fp8",
            tensor_parallel=8,
            max_model_len=65_536,
            note="official F8_E4M3 checkpoint; card: fits one H100 DGX host; "
            + _weights_note(401.6, 1.0),
        ),
        tiers={_A100: _PROBE, _H100: _PROBE},
        tier_notes={_A100: "probe: FP8 -> Marlin (W8A16) on sm80; " + _weights_note(401.6, 1.0)},
        limitations="128 experts; bf16 sibling blocked on single nodes (~800GB).",
        verification=v(
            "https://huggingface.co/meta-llama/Llama-4-Maverick-17B-128E-Instruct-FP8", TODAY
        ),
    ),
    # ========================= Open weights: Mistral ===========================
    ModelProfile(
        model_id="mistralai/Mistral-Large-3-675B-Instruct-2512",
        lab="Mistral",
        kind="open_weights",
        roles=("target",),
        params_total_b=675.0,
        params_active_b=41.0,
        context_tokens=256_000,
        license_name="Apache-2.0",
        license_url="https://huggingface.co/mistralai/Mistral-Large-3-675B-Instruct-2512",
        quant="fp8",
        reasoning_protocol="none",
        gated=False,
        serving=ServingHint(
            quantization="fp8",
            tensor_parallel=8,
            max_model_len=32_768,
            note="native FP8 release; card targets B200/H200 nodes",
        ),
        tiers={_A100: _BLOCKED, _H100: _PROBE},
        tier_notes={
            _A100: "blocked: ~675GB FP8 weights > 640GB",
            _H100: "probe: 675GB vs 640GB — single-node likely blocked; card suggests H200-class",
        },
        limitations="Config 673B/39B (verified); multimodal-granular MoE.",
        verification=v(
            "https://huggingface.co/mistralai/Mistral-Large-3-675B-Instruct-2512", TODAY
        ),
    ),
    ModelProfile(
        model_id="mistralai/Mistral-Small-3.1-24B-Instruct-2503",
        lab="Mistral",
        kind="open_weights",
        roles=("target", "judge", "mechanistic"),
        params_total_b=24.0,
        params_active_b=None,
        context_tokens=128_000,
        license_name="Apache-2.0",
        license_url="https://huggingface.co/mistralai/Mistral-Small-3.1-24B-Instruct-2503",
        quant="bf16",
        reasoning_protocol="none",
        gated=False,
        serving=ServingHint(tensor_parallel=1, max_model_len=65_536),
        tiers={_A100: _PROBE, _H100: _PROBE},
        mechanistic=True,
        mechanistic_note="Dense; vision-capable.",
        limitations="vLLM-recommended serving (verified).",
        verification=v(
            "https://huggingface.co/mistralai/Mistral-Small-3.1-24B-Instruct-2503", TODAY
        ),
    ),
    ModelProfile(
        model_id="mistralai/Ministral-3-3B-Instruct-2512",
        lab="Mistral",
        kind="open_weights",
        roles=("target", "mechanistic"),
        params_total_b=3.0,
        params_active_b=None,
        context_tokens=256_000,
        license_name="Apache-2.0",
        license_url="https://huggingface.co/mistralai/Ministral-3-3B-Instruct-2512",
        quant="fp8",
        reasoning_protocol="none",
        gated=False,
        serving=ServingHint(
            quantization="fp8",
            tensor_parallel=1,
            max_model_len=65_536,
            note="official FP8 checkpoint",
        ),
        tiers={_A100: _PROBE, _H100: _PROBE},
        mechanistic=True,
        limitations="Small tier; vision-capable.",
        verification=v("https://huggingface.co/mistralai/Ministral-3-3B-Instruct-2512", TODAY),
    ),
    # ========================= Open weights: OpenAI gpt-oss ====================
    ModelProfile(
        model_id="openai/gpt-oss-120b",
        lab="OpenAI",
        kind="open_weights",
        roles=("target", "judge"),
        params_total_b=117.0,
        params_active_b=5.1,
        context_tokens=131_072,
        license_name="Apache-2.0",
        license_url="https://huggingface.co/openai/gpt-oss-120b",
        quant="mxfp4",
        reasoning_protocol="harmony",
        gated=False,
        serving=ServingHint(
            quantization="mxfp4",
            tensor_parallel=1,
            max_model_len=32_768,
            reasoning_parser="harmony",
            note="native MXFP4; harmony format required",
        ),
        tiers={_A100: _BLOCKED, _H100: _PROBE},
        tier_notes={
            _A100: "blocked: MXFP4 requires Hopper+ (sm90); verified against vLLM gpt-oss support",
            _H100: "probe: native MXFP4 on sm90 via vLLM",
        },
        limitations="MoE 5.1B active; fits one 80GB GPU (verified).",
        verification=v("https://huggingface.co/openai/gpt-oss-120b", TODAY),
    ),
    ModelProfile(
        model_id="openai/gpt-oss-20b",
        lab="OpenAI",
        kind="open_weights",
        roles=("target", "judge", "attacker", "mechanistic"),
        params_total_b=21.0,
        params_active_b=3.6,
        context_tokens=131_072,
        license_name="Apache-2.0",
        license_url="https://huggingface.co/openai/gpt-oss-20b",
        quant="mxfp4",
        reasoning_protocol="harmony",
        gated=False,
        serving=ServingHint(
            quantization="mxfp4",
            tensor_parallel=1,
            max_model_len=32_768,
            reasoning_parser="harmony",
            note="native MXFP4; Hopper+ only",
        ),
        tiers={_A100: _BLOCKED, _H100: _PROBE},
        tier_notes={_A100: "blocked: MXFP4 requires Hopper+"},
        mechanistic=True,
        mechanistic_note="hooks on sm90 tier only.",
        limitations="Open-weight OpenAI line.",
        verification=v("https://huggingface.co/openai/gpt-oss-20b", TODAY),
    ),
    # ========================= Open weights: others (verified) =================
    ModelProfile(
        model_id="MiniMaxAI/MiniMax-M3",
        lab="MiniMax",
        kind="open_weights",
        roles=("target",),
        params_total_b=428.0,
        params_active_b=23.0,
        context_tokens=1_000_000,
        license_name="MiniMax Community License",
        license_url="https://huggingface.co/MiniMaxAI/MiniMax-M3",
        quant="mxfp8",
        reasoning_protocol="think_tags",
        gated=False,
        serving=ServingHint(
            quantization="mxfp8",
            tensor_parallel=8,
            max_model_len=32_768,
            note="official MXFP8 variant; MiniMax Sparse Attention; native multimodal",
        ),
        tiers={_A100: _PROBE, _H100: _PROBE},
        limitations="vLLM recipes verified; license is a community license, not OSI.",
        verification=v("https://huggingface.co/MiniMaxAI/MiniMax-M3", TODAY),
    ),
    ModelProfile(
        model_id="tencent/Hunyuan-A13B-Instruct",
        lab="Tencent",
        kind="open_weights",
        roles=("target", "judge"),
        params_total_b=80.0,
        params_active_b=13.0,
        context_tokens=256_000,
        license_name="Tencent Hunyuan Community License",
        license_url="https://huggingface.co/tencent/Hunyuan-A13B-Instruct",
        quant="bf16",
        reasoning_protocol="think_tags",
        gated=False,
        serving=ServingHint(
            quantization="fp8",
            tensor_parallel=4,
            max_model_len=65_536,
            note="official FP8 variant + GPTQ-Int4 + GGUF (verified)",
        ),
        tiers={_A100: _PROBE, _H100: _PROBE},
        limitations="80B total / 13B active.",
        verification=v("https://huggingface.co/tencent/Hunyuan-A13B-Instruct", TODAY),
    ),
    ModelProfile(
        model_id="meituan-longcat/LongCat-Flash-Chat-FP8",
        lab="Meituan",
        kind="open_weights",
        roles=("target", "judge"),
        params_total_b=560.0,
        params_active_b=27.0,
        context_tokens=128_000,
        license_name="MIT",
        license_url="https://huggingface.co/meituan-longcat/LongCat-Flash-Chat-FP8",
        quant="fp8",
        reasoning_protocol="think_tags",
        gated=False,
        serving=ServingHint(
            quantization="fp8",
            tensor_parallel=8,
            max_model_len=32_768,
            note="official FP8 checkpoint (this repo); dedicated vLLM deployment guide (verified)",
        ),
        tiers={_A100: _PROBE, _H100: _PROBE},
        tier_notes={
            _A100: "probe: ~560GB FP8 on 640GB node — very tight; probe decides",
            _H100: "probe: fits with modest KV budget",
        },
        limitations="Note: org is meituan-longcat (verified), not meituan.",
        verification=v("https://huggingface.co/meituan-longcat/LongCat-Flash-Chat-FP8", TODAY),
    ),
    ModelProfile(
        model_id="nvidia/NVIDIA-Nemotron-3.5-Bolt-74B-A9B-BF16",
        lab="NVIDIA",
        kind="open_weights",
        roles=("target", "judge"),
        params_total_b=74.0,
        params_active_b=9.0,
        context_tokens=256_000,
        license_name="OpenMDW v1.1",
        license_url="https://huggingface.co/nvidia/NVIDIA-Nemotron-3.5-Bolt-74B-A9B-BF16",
        quant="bf16",
        reasoning_protocol="think_tags",
        gated=False,
        serving=ServingHint(tensor_parallel=4, max_model_len=65_536),
        tiers={_A100: _PROBE, _H100: _PROBE},
        limitations="Lightning-30B-A3B (1M ctx, MTP) and Super-VL-120B also verified in the family.",
        verification=v(
            "https://huggingface.co/nvidia/NVIDIA-Nemotron-3.5-Bolt-74B-A9B-BF16", TODAY
        ),
    ),
    ModelProfile(
        model_id="nvidia/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-BF16",
        lab="NVIDIA",
        kind="open_weights",
        roles=("target", "judge", "attacker", "mechanistic"),
        params_total_b=30.0,
        params_active_b=3.0,
        context_tokens=1_000_000,
        license_name="OpenMDW v1.1",
        license_url="https://huggingface.co/nvidia/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-BF16",
        quant="bf16",
        reasoning_protocol="think_tags",
        gated=False,
        serving=ServingHint(
            tensor_parallel=1,
            max_model_len=65_536,
            note="up to 1M ctx via vLLM --max-model-len 1048576; 256K on one H100 (verified); MTP",
        ),
        tiers={_A100: _PROBE, _H100: _PROBE},
        mechanistic=True,
        limitations="Small MoE; MTP spec available.",
        verification=v(
            "https://huggingface.co/nvidia/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-BF16", TODAY
        ),
    ),
    ModelProfile(
        model_id="google/gemma-4-12B-it",
        lab="Google",
        kind="open_weights",
        roles=("target", "judge", "mechanistic"),
        params_total_b=12.0,
        params_active_b=None,
        context_tokens=256_000,
        license_name="Apache-2.0 (per model card, 2026-10-30)",
        license_url="https://huggingface.co/google/gemma-4-12B-it",
        quant="bf16",
        reasoning_protocol="none",
        gated=True,
        serving=ServingHint(
            tensor_parallel=1,
            max_model_len=65_536,
            note="multimodal in (text+image+audio); 140+ languages; E4B/E2B (128K) and a 26B-A4B MoE also exist",
        ),
        tiers={_A100: _PROBE, _H100: _PROBE},
        mechanistic=True,
        limitations="License stated as Apache-2.0 on the model card — probe re-verifies before use.",
        verification=v("https://huggingface.co/google/gemma-4-12B-it", TODAY),
    ),
    # ========================= Judge classifiers (served locally) ==============
    ModelProfile(
        model_id="meta-llama/Llama-Guard-4-12B",
        lab="Meta",
        kind="open_weights",
        roles=("judge",),
        params_total_b=12.0,
        params_active_b=None,
        context_tokens=131_072,
        license_name="Llama 4 Community License",
        license_url="https://huggingface.co/meta-llama/Llama-Guard-4-12B",
        quant="bf16",
        reasoning_protocol="none",
        gated=True,
        serving=ServingHint(tensor_parallel=1, max_model_len=32_768),
        tiers={_A100: _PROBE, _H100: _PROBE},
        limitations="Guard classifier judge; card prompt format enforced by the admission probe.",
        verification=v("https://huggingface.co/meta-llama/Llama-Guard-4-12B", TODAY),
    ),
    ModelProfile(
        model_id="google/shieldgemma-9b",
        lab="Google",
        kind="open_weights",
        roles=("judge",),
        params_total_b=9.0,
        params_active_b=None,
        context_tokens=8_192,
        license_name="Gemma Terms",
        license_url="https://huggingface.co/google/shieldgemma-9b",
        quant="bf16",
        reasoning_protocol="none",
        gated=True,
        serving=ServingHint(tensor_parallel=1, max_model_len=8_192),
        tiers={_A100: _PROBE, _H100: _PROBE},
        limitations="CANDIDATE repo id (paper verified: Zeng et al. 2407.21772); probe pins the exact id.",
        verification=cand(
            "https://huggingface.co/google/shieldgemma-9b",
            TODAY,
            note="probe pins exact repo id + card prompt conformance",
        ),
    ),
    ModelProfile(
        model_id="allenai/wildguard",
        lab="AI2",
        kind="open_weights",
        roles=("judge",),
        params_total_b=7.0,
        params_active_b=None,
        context_tokens=8_192,
        license_name="Apache-2.0 (paper: open one-stop moderation tools)",
        license_url="https://huggingface.co/allenai/wildguard",
        quant="bf16",
        reasoning_protocol="none",
        gated=False,
        serving=ServingHint(tensor_parallel=1, max_model_len=8_192),
        tiers={_A100: _PROBE, _H100: _PROBE},
        limitations="CANDIDATE repo id (paper verified: Han et al. 2406.18495); probe pins it.",
        verification=cand(
            "https://huggingface.co/allenai/wildguard",
            TODAY,
            note="probe pins exact repo id + prompt contract",
        ),
    ),
    ModelProfile(
        model_id="harmbench-classifier",
        lab="CAIS",
        kind="open_weights",
        roles=("judge",),
        params_total_b=13.0,
        params_active_b=None,
        context_tokens=8_192,
        license_name="MIT (HarmBench repo)",
        license_url="https://github.com/centerforaisafety/harmbench",
        quant="bf16",
        reasoning_protocol="none",
        gated=False,
        serving=ServingHint(
            tensor_parallel=1,
            max_model_len=8_192,
            note="exact HF repo id + assessment prompt pinned by the probe from the HarmBench repo",
        ),
        tiers={_A100: _PROBE, _H100: _PROBE},
        limitations="CANDIDATE: HarmBench paper verified (Mazeika et al., ICML 2024, 2402.04249); repo id pinned at probe.",
        verification=cand(
            "https://github.com/centerforaisafety/harmbench",
            TODAY,
            note="probe pins the classifier checkpoint id from the verified repo",
        ),
    ),
]

MODEL_PROFILES: dict[str, ModelProfile] = {p.model_id: p for p in PROFILES}


def get_model_profile(model_id: str) -> ModelProfile:
    try:
        return MODEL_PROFILES[model_id]
    except KeyError as exc:
        raise RegistryError(
            f"model {model_id!r} is not in the audited registry; add a sourced "
            "ModelProfile (with a Verification record) before research use",
            model_id=model_id,
        ) from exc


def validate_model_assignment(
    model_id: str,
    *,
    role: Role,
    tier: str,
    probe_sha256: str | None = None,
) -> ModelProfile:
    """Fail-closed admission for one model in one role on one hardware tier.

    Checks (in order): registry membership; role approval; verified facts
    (candidates fail closed); tier not blocked; a probe artifact is bound
    for probe_required tiers. The provider factory additionally verifies the
    artifact's contents (served id, gates) against this profile.
    """
    profile = get_model_profile(model_id)
    if role not in profile.roles:
        raise ValueError(f"{model_id}: not approved for role {role!r} (roles={profile.roles})")
    if not profile.is_verified():
        raise ValueError(
            f"{model_id}: registry entry is a candidate — run the admission probe "
            "to promote it (pin exact id/license/serving) before research use"
        )
    status = profile.status_for(tier)
    if profile.kind == "remote_api":
        return profile  # API models: probe pins served ids; no tier physics
    if status == "blocked":
        raise ValueError(
            f"{model_id} is BLOCKED on {tier}: {profile.tier_notes.get(tier, 'no admissible path')}"
        )
    if status == "probe_required" and probe_sha256 is None:
        raise ValueError(
            f"{model_id} on {tier}: admission probe required — bind its artifact "
            "SHA-256 in the run config before research use"
        )
    return profile


def local_serving_candidates(tier: str) -> list[ModelProfile]:
    """Open-weight models whose registry status permits probing on ``tier``."""
    return [p for p in PROFILES if p.kind == "open_weights" and p.status_for(tier) != "blocked"]


__all__ = [
    "Role",
    "Tier",
    "TierStatus",
    "Pricing",
    "ApiEndpoint",
    "ServingHint",
    "ModelProfile",
    "PROFILES",
    "MODEL_PROFILES",
    "get_model_profile",
    "validate_model_assignment",
    "local_serving_candidates",
    "TODAY",
]
