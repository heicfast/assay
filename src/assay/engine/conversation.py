"""Conversation driver: executes one planned trial against one target."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..attacks import build_policy_attack, build_template_attack
from ..attacks.base import TrialContext, as_message
from ..behaviors.model import Behavior
from ..engine.plan import PlannedTrial
from ..errors import AssayError
from ..targets.base import ModelTurn, TargetModel

MAX_EXCHANGES = 12
MAX_ATTACKER_CALLS = 24


@dataclass
class TrialResult:
    status: str  # completed | runtime_error
    messages: list[dict[str, str]] = field(default_factory=list)
    target_turns: list[ModelTurn] = field(default_factory=list)
    attacker_turns: list[ModelTurn] = field(default_factory=list)
    final_reply: str = ""
    reasoning_text: str | None = None
    reasoning_status: str = "absent"
    error_kind: str | None = None
    error_message: str | None = None


def run_trial(
    trial: PlannedTrial,
    behavior: Behavior,
    target: TargetModel,
    attacker: TargetModel | None,
    attack_params: dict[str, Any],
) -> TrialResult:
    """Run one trial; failures become typed runtime_error results (never retried
    into success — NF rules)."""
    try:
        if trial.attack_id == "benign_probe":
            return _run_probe(trial, behavior, target)
        from ..registry.attacks import get_attack

        spec = get_attack(trial.attack_id)
        if spec.mode == "policy":
            if attacker is None:
                raise AssayError(
                    "policy attack requires an attacker model", attack_id=trial.attack_id
                )
            return _run_policy(trial, behavior, target, attacker, attack_params)
        return _run_template(trial, behavior, target, attack_params)
    except AssayError as exc:
        return TrialResult(status="runtime_error", error_kind=exc.kind, error_message=exc.message)
    except Exception as exc:  # broad by design: failures are recorded, never hidden
        return TrialResult(
            status="runtime_error",
            error_kind="unhandled",
            error_message=f"{type(exc).__name__}: {exc}",
        )


def _settings(trial: PlannedTrial) -> dict[str, Any]:
    setting = dict(trial.param_setting)
    setting.setdefault("top_p", 0.95)
    setting.setdefault("top_k", 0)
    setting.setdefault("max_tokens", 1024)
    return setting


def _target_call(
    target: TargetModel, trial: PlannedTrial, messages: list[dict[str, str]]
) -> ModelTurn:
    setting = _settings(trial)
    # Seeding policy: pass the trial seed; providers that support seeds include
    # them (the recorded determinism class says what that means per provider).
    return target.chat(
        messages,
        temperature=float(setting.get("temperature", 0.7)),
        top_p=float(setting.get("top_p", 0.95)),
        top_k=int(setting.get("top_k", 0)),
        max_tokens=int(setting.get("max_tokens", 1024)),
        seed=trial.seed,
    )


def _run_probe(trial: PlannedTrial, behavior: Behavior, target: TargetModel) -> TrialResult:
    messages = [as_message("user", behavior.text)]
    turn = _target_call(target, trial, messages)
    messages = messages + [as_message("assistant", turn.content)]
    return TrialResult(
        status="completed",
        messages=messages,
        target_turns=[turn],
        final_reply=turn.content,
        reasoning_text=turn.reasoning_text,
        reasoning_status=turn.reasoning_parse_status,
    )


def _run_template(
    trial: PlannedTrial, behavior: Behavior, target: TargetModel, attack_params: dict[str, Any]
) -> TrialResult:
    ctx = TrialContext(behavior=behavior, params=attack_params, seed=trial.seed)
    attack = build_template_attack(trial.attack_id, attack_params)
    opening = attack.opening(ctx)
    turn = _target_call(target, trial, opening)
    messages = list(opening) + [as_message("assistant", turn.content)]
    return TrialResult(
        status="completed",
        messages=messages,
        target_turns=[turn],
        final_reply=turn.content,
        reasoning_text=turn.reasoning_text,
        reasoning_status=turn.reasoning_parse_status,
    )


def _run_policy(
    trial: PlannedTrial,
    behavior: Behavior,
    target: TargetModel,
    attacker: TargetModel,
    attack_params: dict[str, Any],
) -> TrialResult:
    ctx = TrialContext(behavior=behavior, params=attack_params, seed=trial.seed)
    policy = build_policy_attack(trial.attack_id, attack_params, attacker)
    opening = policy.opening(ctx)
    messages: list[dict[str, str]] = list(opening)
    target_turns: list[ModelTurn] = []
    exchanges = 0
    while exchanges < MAX_EXCHANGES:
        turn = _target_call(target, trial, messages)
        target_turns.append(turn)
        messages = messages + [as_message("assistant", turn.content)]
        exchanges += 1
        if getattr(policy, "turns_used", 0) >= MAX_ATTACKER_CALLS:
            break
        nxt = policy.react(ctx, messages, turn)
        if nxt is None:
            break
        messages = messages + nxt
    final = target_turns[-1] if target_turns else None
    return TrialResult(
        status="completed",
        messages=messages,
        target_turns=target_turns,
        attacker_turns=[],  # policy-internal turns are in the privileged record below
        final_reply=final.content if final else "",
        reasoning_text=final.reasoning_text if final else None,
        reasoning_status=final.reasoning_parse_status if final else "absent",
    )


__all__ = ["run_trial", "TrialResult", "MAX_EXCHANGES", "MAX_ATTACKER_CALLS"]
