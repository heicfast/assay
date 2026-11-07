"""Mechanistic analysis: layer curves, cross-model transfer, outcome ties."""

from __future__ import annotations

from typing import Any


def layer_report(directions_by_model: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Summarize per-layer separation AUROC per model (from hooks.extract)."""
    return {
        model_id: {
            "layer_auroc": payload.get("layer_auroc", {}),
            "best_layer": _argmax(payload.get("layer_auroc", {})),
            "method": payload.get("method"),
            "citation": payload.get("citation"),
        }
        for model_id, payload in directions_by_model.items()
    }


def cross_model_transfer(
    directions_by_model: dict[str, dict[str, Any]], hooked_models: dict[str, Any]
) -> dict[str, dict[str, float]]:
    """Functional transfer: apply model A's best-layer direction to model B,
    measure cosine similarity (structural) — functional steering experiments
    run through SteeringPatchedModel in the runbook (compute-gated)."""
    from .hooks import direction_cosine

    out: dict[str, dict[str, float]] = {}
    for source_id, source in sorted(directions_by_model.items()):
        best = _argmax(source.get("layer_auroc", {}))
        if best is None:
            continue
        source_direction = source["directions"].get(best)
        row: dict[str, float] = {}
        for target_id, target in sorted(directions_by_model.items()):
            target_best = _argmax(target.get("layer_auroc", {}))
            if target_best is None or target_id == source_id:
                continue
            target_direction = target["directions"].get(target_best)
            if source_direction is None or target_direction is None:
                continue
            row[target_id] = round(direction_cosine(source_direction, target_direction), 4)
        out[source_id] = row
    return out


def outcome_tie(
    directions_by_model: dict[str, dict[str, Any]], asr_by_model: dict[str, Any]
) -> dict[str, Any]:
    """RQ3 synthesis (EXPLORATORY, labeled as such): refusal-direction
    separation vs verified-harm ASR across models — Spearman rank tie."""
    from ..analysis.stats import spearman

    xs: list[float] = []
    ys: list[float] = []
    pairs: list[tuple[str, float, float]] = []
    for model_id, payload in directions_by_model.items():
        best = _argmax(payload.get("layer_auroc", {}))
        harm = asr_by_model.get(model_id, {}).get("asr_verified_harm", {}).get("estimate")
        if best is None or harm is None:
            continue
        separation = payload["layer_auroc"][best]
        xs.append(float(separation))
        ys.append(float(harm))
        pairs.append((model_id, separation, harm))
    rho = spearman(xs, ys) if len(xs) >= 3 else None
    return {
        "n_models": len(pairs),
        "pairs": pairs,
        "spearman_separation_vs_harm": rho,
        "interpretation": (
            "negative correlation expected: stronger refusal-direction separation, "
            "less verified harm. Exploratory — models are not a random sample; "
            "never reported as confirmatory."
        ),
    }


def _argmax(mapping: dict[int, float]) -> int | None:
    if not mapping:
        return None
    return max(mapping, key=lambda key: mapping[key])


__all__ = ["layer_report", "cross_model_transfer", "outcome_tie"]
