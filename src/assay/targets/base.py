"""Provider contract + auditable turns + the anti-leak reasoning split.

The reasoning channel must NEVER leak into the visible answer channel: a
leak would corrupt every downstream measurement (judges would read reasoning
that was supposed to be answer). The split rules are the predecessor
program's, hardened by its reviews:

1. literal close tag present -> split at the LAST close tag (complete);
2. literal open tag present  -> truncated: everything after the LAST open
   tag is reasoning; in thinking mode the pre-tag prefix is ALSO reasoning;
3. thinking mode, no tags    -> the template pre-filled the open tag in the
   prompt, so every generated token is reasoning (truncated), answer EMPTY;
4. otherwise                 -> plain answer, reasoning absent.

Think-tag literals are built from chr() fragments (tooling display layers
have been observed rewriting bracket-like text; byte-exactness is tested).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from ..ids import sha256_json, sha256_text

THINK_OPEN = chr(60) + "think" + chr(62)  # 7 bytes
THINK_CLOSE = chr(60) + chr(47) + "think" + chr(62)  # 8 bytes
# Byte-exactness is asserted structurally (lengths + chr construction):
# literals are never written out, because transport/display layers have
# been observed rewriting bracket-like text (predecessor program's NH-8 rule).
assert chr(60) + "think" + chr(62) == THINK_OPEN and len(THINK_OPEN) == 7
assert chr(60) + chr(47) + "think" + chr(62) == THINK_CLOSE and len(THINK_CLOSE) == 8


@dataclass
class ModelTurn:
    """One generation step, fully auditable (privileged by construction)."""

    raw_output: str
    content: str = ""
    reasoning_text: str | None = None
    reasoning_parse_status: str = "absent"  # complete | truncated | absent | empty_block
    stop_reason: str = "unknown"
    token_usage: dict[str, int] = field(default_factory=dict)
    elapsed_ms: float = 0.0
    model_id: str = ""
    served_id: str = ""
    revision: str = ""
    determinism_class: str = "unseeded_api"
    rendered_prompt: str = ""
    input_messages: list[dict[str, str]] = field(default_factory=list)
    generation_params: dict[str, Any] = field(default_factory=dict)
    runtime: dict[str, Any] = field(default_factory=dict)

    @property
    def trace_available(self) -> bool:
        return self.reasoning_text is not None and len(self.reasoning_text.strip()) > 0

    def audit_payload(self) -> dict[str, Any]:
        """Complete privileged inference record (never shown to judges)."""
        return {
            "raw_output": self.raw_output,
            "raw_output_utf8_sha256": sha256_text(self.raw_output),
            "content": self.content,
            "content_utf8_sha256": sha256_text(self.content),
            "reasoning_text": self.reasoning_text,
            "reasoning_utf8_sha256": (
                sha256_text(self.reasoning_text) if self.reasoning_text is not None else None
            ),
            "reasoning_parse_status": self.reasoning_parse_status,
            "stop_reason": self.stop_reason,
            "token_usage": self.token_usage,
            "elapsed_ms": self.elapsed_ms,
            "model_id": self.model_id,
            "served_id": self.served_id,
            "revision": self.revision,
            "determinism_class": self.determinism_class,
            "rendered_prompt": self.rendered_prompt,
            "rendered_prompt_utf8_sha256": sha256_text(self.rendered_prompt),
            "input_messages": self.input_messages,
            "input_messages_sha256": sha256_json(self.input_messages),
            "generation_params": self.generation_params,
            "runtime": self.runtime,
        }


def split_reasoning(raw_output: str, *, thinking_mode: bool) -> ModelTurn:
    """Anti-leak split of think-tag output into (reasoning, answer)."""
    if THINK_CLOSE in raw_output:
        segments = raw_output.split(THINK_CLOSE)
        answer = segments[-1].strip("\n")
        reasoning_parts: list[str] = []
        intermediate = 0
        for seg in segments[:-1]:
            if THINK_OPEN in seg:
                before = seg[: seg.rfind(THINK_OPEN)]
                if before.strip("\n"):
                    intermediate += 1
                reasoning_parts.append(seg[seg.rfind(THINK_OPEN) + len(THINK_OPEN) :].strip("\n"))
            else:
                reasoning_parts.append(seg.strip("\n"))
        reasoning = "\n\n".join(p for p in reasoning_parts if p).strip("\n")
        status = "complete" if reasoning else "empty_block"
        turn = ModelTurn(
            raw_output=raw_output,
            content=answer,
            reasoning_text=reasoning or None,
            reasoning_parse_status=status,
        )
        if intermediate:
            turn.runtime["intermediate_answers_discarded"] = intermediate
        return turn
    if THINK_OPEN in raw_output:
        cut = raw_output.rfind(THINK_OPEN)
        if thinking_mode:
            body = (raw_output[:cut] + raw_output[cut + len(THINK_OPEN) :]).strip("\n")
            return ModelTurn(
                raw_output=raw_output,
                content="",
                reasoning_text=body or None,
                reasoning_parse_status="truncated",
            )
        reasoning = raw_output[cut + len(THINK_OPEN) :]
        return ModelTurn(
            raw_output=raw_output,
            content=raw_output[:cut].strip("\n"),
            reasoning_text=reasoning or None,
            reasoning_parse_status="truncated",
        )
    if thinking_mode:
        body = raw_output.strip("\n")
        if not body:
            return ModelTurn(raw_output=raw_output, content="", reasoning_parse_status="absent")
        return ModelTurn(
            raw_output=raw_output,
            content="",
            reasoning_text=body,
            reasoning_parse_status="truncated",
        )
    return ModelTurn(
        raw_output=raw_output, content=raw_output.strip("\n"), reasoning_parse_status="absent"
    )


class TargetModel(Protocol):
    """Every provider (API, local server, HF, mock) implements this."""

    model_id: str
    served_id: str

    def chat(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float,
        top_p: float,
        top_k: int,
        max_tokens: int,
        seed: int | None,
    ) -> ModelTurn: ...


__all__ = ["ModelTurn", "split_reasoning", "TargetModel", "THINK_OPEN", "THINK_CLOSE"]
