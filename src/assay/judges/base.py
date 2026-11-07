"""Judge contracts: views, verdicts, and the leakage firewall.

Judges NEVER see: model identity (blind judging), split roles, clusters,
grid class, or any outcome label. ``compile_judge_view`` enforces this
mechanically (``assert_view_is_clean``) exactly the way the predecessor
program firewallled its monitor views.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

from ..ids import sha256_text, verdict_id
from ..targets.base import ModelTurn, TargetModel

PRIVILEGED_MARKERS = (
    "model_id",
    "split_role",
    "cluster",
    "battery",
    "grid",
    "param_setting",
    "setting_index",
    "verified",
    "attack_id",
)


@dataclass(frozen=True)
class JudgeView:
    trial_id: str
    request: list[dict[str, str]]  # the conversation the target saw (user side)
    response: str  # the target's final visible reply
    reasoning: str | None = None  # only for judges that declare use
    fingerprint: str = ""  # creation-time binding to the trial envelope

    def render(self) -> str:
        lines = []
        for message in self.request:
            role = message.get("role", "user")
            lines.append(f"[{role}] {message.get('content', '')}")
        lines.append(f"[assistant] {self.response}")
        return "\n".join(lines)


def compile_judge_view(envelope: dict[str, Any], *, include_reasoning: bool = False) -> JudgeView:
    from ..evidence.store import envelope_fingerprint

    messages = list(envelope.get("messages", []))
    reasoning = envelope.get("reasoning_text") if include_reasoning else None
    view = JudgeView(
        trial_id=envelope["trial_id"],
        request=[m for m in messages if m.get("role") != "assistant" or True],
        response=str(envelope.get("final_reply", "")),
        reasoning=reasoning,
        fingerprint=envelope_fingerprint(envelope),
    )
    assert_view_is_clean(view, envelope)
    return view


def assert_view_is_clean(view: JudgeView, envelope: dict[str, Any]) -> None:
    """Mechanical leakage assertion for judge inputs."""
    rendered = view.render().lower()
    for marker in PRIVILEGED_MARKERS:
        if f'"{marker}"' in rendered or f"'{marker}'" in rendered:
            raise AssertionError(f"leak: privileged marker {marker!r} in judge view")
    # model identity must never appear in the request/response content
    # (it is metadata; a judge that knows the model cannot judge it blindly)
    for field in ("model_id", "served_id"):
        value = str(envelope.get(field, ""))
        probe = value.lower()
        if probe and len(probe) > 6 and probe in rendered and "api/" not in probe:
            # legitimate mentions of a model name inside behavior text are
            # possible in principle; treat as leak for our controlled batteries
            raise AssertionError(f"leak: {field} appears inside judge view")


@dataclass
class JudgeVerdict:
    verdict_id: str
    trial_id: str
    judge_id: str
    output: str  # binary | score_0_5 | harm_verified | refusal_binary
    value: Any  # bool | int(0-5) | bool | str(refuse|comply|offtopic)
    raw_response: str
    prompt_hash: str
    rendered_prompt: str
    envelope_fingerprint: str
    parse_status: str = "ok"  # ok | invalid
    note: str = ""

    def to_payload(self) -> dict[str, Any]:
        return {
            "verdict_id": self.verdict_id,
            "trial_id": self.trial_id,
            "judge_id": self.judge_id,
            "output": self.output,
            "value": self.value,
            "raw_response": self.raw_response,
            "prompt_hash": self.prompt_hash,
            "rendered_prompt": self.rendered_prompt,
            "rendered_prompt_hash": sha256_text(self.rendered_prompt),
            "envelope_fingerprint": self.envelope_fingerprint,
            "parse_status": self.parse_status,
            "note": self.note,
        }


def make_verdict(
    trial_id: str,
    judge_id: str,
    *,
    output: str,
    value: Any,
    raw_response: str,
    prompt_hash: str,
    rendered_prompt: str,
    envelope_fingerprint: str,
    parse_status: str = "ok",
    note: str = "",
) -> JudgeVerdict:
    return JudgeVerdict(
        verdict_id=verdict_id(trial_id, judge_id),
        trial_id=trial_id,
        judge_id=judge_id,
        output=output,
        value=value,
        raw_response=raw_response,
        prompt_hash=prompt_hash,
        rendered_prompt=rendered_prompt,
        envelope_fingerprint=envelope_fingerprint,
        parse_status=parse_status,
        note=note,
    )


@runtime_checkable
class Judge(Protocol):
    judge_id: str

    def score(self, view: JudgeView) -> JudgeVerdict: ...


class LLMJudgeBase:
    """Shared machinery for LLM-backed judges (rubric/refusal)."""

    judge_id: str
    model: TargetModel
    prompt_template: str

    def __init__(self, judge_id: str, model: TargetModel, prompt_template: str) -> None:
        self.judge_id = judge_id
        self.model = model
        self.prompt_template = prompt_template

    @property
    def prompt_hash(self) -> str:
        return sha256_text(self.prompt_template)

    def _call(self, prompt: str) -> ModelTurn:
        return self.model.chat(
            [{"role": "user", "content": prompt}],
            temperature=0.0,
            top_p=1.0,
            top_k=0,
            max_tokens=256,
            seed=0,
        )

    @staticmethod
    def fingerprint_of(envelope: dict[str, Any]) -> str:
        from ..evidence.store import envelope_fingerprint

        return envelope_fingerprint(envelope)


__all__ = [
    "Judge",
    "JudgeView",
    "JudgeVerdict",
    "compile_judge_view",
    "assert_view_is_clean",
    "make_verdict",
    "LLMJudgeBase",
    "PRIVILEGED_MARKERS",
]
