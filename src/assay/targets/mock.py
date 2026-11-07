"""Scripted mock provider — admissible ONLY in smoke stages and tests (NF-2).

Research stages refuse providers whose model_id starts with ``mock``/: the
factory enforces this, and the analysis layer double-checks the recorded
provenance. The mock replays a scripted sequence of turns with optional
think-tag content so the entire pipeline (reasoning split, judging, stats)
is exercised on CPU without network or GPUs.
"""

from __future__ import annotations

from .base import ModelTurn, split_reasoning


class ScriptedTarget:
    model_id: str
    served_id: str

    def __init__(
        self,
        *,
        model_id: str = "mock/scripted",
        script: list[str] | None = None,
        thinking_protocol: str = "none",
        determinism_class: str = "seeded_local",
    ) -> None:
        self.model_id = model_id
        self.served_id = model_id
        self.script = list(script or [])
        self._cursor = 0
        self.thinking_protocol = thinking_protocol
        self.determinism_class = determinism_class
        self.revision = "scripted"

    def chat(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float,
        top_p: float,
        top_k: int,
        max_tokens: int,
        seed: int | None,
    ) -> ModelTurn:
        raw = self.script[min(self._cursor, len(self.script) - 1)] if self.script else ""
        self._cursor += 1
        turn = split_reasoning(raw, thinking_mode=self.thinking_protocol == "think_tags")
        turn.token_usage = {
            "prompt_tokens": sum(len(str(m.get("content", ""))) // 4 for m in messages),
            "completion_tokens": len(raw) // 4,
        }
        turn.model_id = self.model_id
        turn.served_id = self.served_id
        turn.revision = self.revision
        turn.determinism_class = self.determinism_class
        turn.input_messages = list(messages)
        turn.generation_params = {
            "temperature": temperature,
            "top_p": top_p,
            "top_k": top_k,
            "max_tokens": max_tokens,
            "seed": seed,
        }
        return turn


class CountingJudgeTarget:
    """Deterministic judge-side mock: outputs depend only on input content.

    Used by judge tests: emits 'yes'/'no' or a rubric JSON derived from a
    content hash, so panel agreement math is testable without any model.
    """

    model_id: str
    served_id: str

    def __init__(self, *, model_id: str = "mock/counting") -> None:
        self.model_id = model_id
        self.served_id = model_id
        self.revision = "counting"

    def chat(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float,
        top_p: float,
        top_k: int,
        max_tokens: int,
        seed: int | None,
    ) -> ModelTurn:
        from ..ids import sha256_text

        text = "\n".join(str(m.get("content", "")) for m in messages)
        digest = int(sha256_text(text)[:8], 16)
        raw = "yes" if digest % 2 == 0 else "no"
        return ModelTurn(
            raw_output=raw,
            content=raw,
            stop_reason="stop",
            model_id=self.model_id,
            served_id=self.served_id,
            revision=self.revision,
            determinism_class="seeded_local",
            input_messages=list(messages),
            generation_params={"temperature": 0.0},
        )


__all__ = ["ScriptedTarget", "CountingJudgeTarget"]
