"""Attack contracts + render context.

Template attacks produce opening turns from a behavior; policy attacks run
a multi-turn loop with an attacker model; optimization attacks need
white-box access (local weights). The engine treats them uniformly through
``AttackInstance``.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

from ..behaviors.model import Behavior
from ..targets.base import ModelTurn


@dataclass
class TrialContext:
    """Everything an attack may know — the behavior and its own params."""

    behavior: Behavior
    params: dict[str, Any]
    seed: int
    rng: random.Random = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "rng", random.Random(self.seed))


@runtime_checkable
class TemplateAttack(Protocol):
    def opening(self, ctx: TrialContext) -> list[dict[str, str]]: ...


@runtime_checkable
class PolicyAttack(Protocol):
    """Multi-turn adaptive policy. ``react`` returns the next attacker turn(s)
    or None to stop; ``reward`` lets the policy read the study's verified-harm
    judge verdict AFTER the trial (recorded, never fed back mid-trial unless
    the policy declares itself feedback-driven, which changes its class)."""

    def opening(self, ctx: TrialContext) -> list[dict[str, str]]: ...

    def react(
        self, ctx: TrialContext, history: list[dict[str, str]], last_reply: ModelTurn
    ) -> list[dict[str, str]] | None: ...


def as_message(role: str, content: str) -> dict[str, str]:
    return {"role": role, "content": content}


def user_turns(*contents: str) -> list[dict[str, str]]:
    return [as_message("user", c) for c in contents]


__all__ = ["TrialContext", "TemplateAttack", "PolicyAttack", "as_message", "user_turns"]
