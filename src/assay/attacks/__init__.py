"""Attack construction registry: attack_id -> instance (params merged)."""

from __future__ import annotations

from typing import Any

from ..registry.attacks import get_attack
from ..targets.base import TargetModel
from .adaptive.crescendo import CrescendoAttack
from .adaptive.pair import PairAttack
from .adaptive.switcher import SwitcherAttack
from .adaptive.tap import TapAttack
from .base import PolicyAttack, TemplateAttack, TrialContext
from .static.context import ManyShotAttack, RandomAugmentAttack
from .static.encoding import CipherComplexAttack, CipherUnicodeAttack
from .static.multilingual import MultilingualAttack
from .static.persuasion import PapAttack
from .static.reasoning_channel import NoThinkAttack, PrefillAnswerAttack
from .static.templates import (
    DeepInceptionAttack,
    PrefixAffirmAttack,
    RefusalSuppressAttack,
)

_TEMPLATES: dict[str, type] = {
    "prefix_affirm": PrefixAffirmAttack,
    "refusal_suppress": RefusalSuppressAttack,
    "deepinception": DeepInceptionAttack,
    "pap": PapAttack,
    "cipher_complex": CipherComplexAttack,
    "cipher_unicode": CipherUnicodeAttack,
    "multilingual": MultilingualAttack,
    "many_shot": ManyShotAttack,
    "no_think": NoThinkAttack,
    "prefill_answer": PrefillAnswerAttack,
    "random_augment": RandomAugmentAttack,
}


def build_template_attack(attack_id: str, params: dict[str, Any]) -> TemplateAttack:
    get_attack(attack_id)  # registry membership + citation check
    try:
        cls = _TEMPLATES[attack_id]
    except KeyError as exc:  # pragma: no cover - registry/factory stay in sync
        raise ValueError(f"attack {attack_id!r} registered but not implemented") from exc
    return cls()


def build_policy_attack(
    attack_id: str, params: dict[str, Any], attacker: TargetModel
) -> PolicyAttack:
    get_attack(attack_id)
    if attack_id == "pair":
        return PairAttack(attacker, max_rounds=int(params.get("max_rounds", 10)))
    if attack_id == "tap":
        return TapAttack(
            attacker,
            width=int(params.get("width", 4)),
            depth=int(params.get("depth", 5)),
            keep_n=int(params.get("keep_n", 2)),
        )
    if attack_id == "crescendo":
        return CrescendoAttack(attacker, max_turns=int(params.get("max_turns", 8)))
    if attack_id == "ajar_switch":
        return SwitcherAttack(
            attacker,
            strategy_pool=params.get("strategy_pool"),
            switch_after=int(params.get("switch_after", 3)),
        )
    raise ValueError(f"attack {attack_id!r} is not a policy attack")


__all__ = [
    "build_template_attack",
    "build_policy_attack",
    "TrialContext",
    "TemplateAttack",
    "PolicyAttack",
    "PrefixAffirmAttack",
    "RefusalSuppressAttack",
    "DeepInceptionAttack",
    "PapAttack",
    "CipherComplexAttack",
    "CipherUnicodeAttack",
    "MultilingualAttack",
    "ManyShotAttack",
    "NoThinkAttack",
    "PrefillAnswerAttack",
    "RandomAugmentAttack",
    "PairAttack",
    "TapAttack",
    "CrescendoAttack",
    "SwitcherAttack",
    "TargetModel",
]
