"""Panel orchestration: every judge scores the same compiled view.

Operating points are calibrated on the VALIDATION split only:
* binary judges: fixed (the classifier IS the threshold);
* score judges (0-5): the panel's calibrated threshold is chosen so the
  benign-battery false-flag rate is <= the declared FPR target; the value
  is frozen before any holdout is judged.
"""

from __future__ import annotations

from typing import Any

from ..evidence.store import RunStore
from .base import Judge, compile_judge_view
from .classifiers import FROZEN_PROMPT_HASHES as CLASSIFIER_HASHES
from .refusal import FROZEN_PROMPT_HASHES as REFUSAL_HASHES
from .rubric import FROZEN_PROMPT_HASHES as RUBRIC_HASHES

FROZEN_PROMPT_HASHES: dict[str, str] = {
    **CLASSIFIER_HASHES,
    **RUBRIC_HASHES,
    **REFUSAL_HASHES,
}


class JudgePanel:
    def __init__(self, judges: list[Judge]) -> None:
        self.judges = {j.judge_id: j for j in judges}
        for judge_id in self.judges:
            if judge_id not in FROZEN_PROMPT_HASHES:
                raise ValueError(
                    f"judge {judge_id!r} has no frozen prompt hash — register it "
                    "before first research use (anti-drift contract)"
                )

    def score_trial(
        self, envelope: dict[str, Any], include_reasoning: bool = False
    ) -> list[dict[str, Any]]:
        view = compile_judge_view(envelope, include_reasoning=include_reasoning)
        return [self.judges[jid].score(view).to_payload() for jid in sorted(self.judges)]

    def run_over_store(
        self, store: RunStore, only_trials: set[str] | None = None, shard_size: int = 512
    ) -> dict[str, int]:
        """Score every committed trial (resume-safe: skips already-versed)."""
        counters: dict[str, int] = {"scored": 0, "skipped": 0}
        existing = {v["trial_id"] for v in store.iter_verdicts()}
        buffer: dict[str, list[dict]] = {}
        for envelope in store.iter_trials():
            trial_id = envelope["trial_id"]
            if only_trials is not None and trial_id not in only_trials:
                continue
            if trial_id in existing:
                counters["skipped"] += 1
                continue
            if envelope.get("status") != "completed":
                continue  # runtime_error trials are never judged (recorded as censored)
            verdicts = self.score_trial(envelope)
            for verdict in verdicts:
                buffer.setdefault(verdict["judge_id"], []).append(verdict)
            counters["scored"] += 1
            if counters["scored"] % shard_size == 0:
                self._flush(store, buffer, counters, existing)
        self._flush(store, buffer, counters, existing)
        return counters

    def _flush(
        self,
        store: RunStore,
        buffer: dict[str, list[dict]],
        counters: dict[str, int],
        existing: set[str],
    ) -> None:
        for judge_id, verdicts in buffer.items():
            index = len(existing) // 512
            for verdict in verdicts:
                store.append_verdict(judge_id, index, verdict)
        existing.update(v["trial_id"] for vs in buffer.values() for v in vs)
        buffer.clear()


def calibrated_threshold(
    scores: list[int], benign_flags: int, fpr_target: float, minimum: int = 4
) -> int | None:
    """Pick the smallest score threshold t >= minimum whose benign-battery
    false-flag rate is <= fpr_target. None when unachievable (fail closed:
    the metric is reported uncomputable, never switched)."""
    n = len(scores)
    if n == 0:
        return None
    allowed = int(fpr_target * n)
    for threshold in range(minimum, 6):
        flags = sum(1 for s in scores if s >= threshold)
        if flags <= allowed:
            return threshold
    return None


__all__ = ["JudgePanel", "FROZEN_PROMPT_HASHES", "calibrated_threshold"]
