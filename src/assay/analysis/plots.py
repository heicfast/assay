"""Provenance-stamped figures (matplotlib, lazily imported).

Every figure embeds run id, config hash, and the data digest, and emits a
``.plotdata.json`` next to the PNG so the figure can be recomputed from
committed bytes.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _plt():
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        return plt
    except ImportError as exc:
        raise RuntimeError("plots need the 'analysis' extra (matplotlib)") from exc


def _stamp(fig, payload: dict[str, Any]) -> None:
    fig.text(
        0.99,
        0.01,
        f"run {payload.get('run_id', '?')[:16]} | config "
        f"{str(payload.get('config_sha256', '?'))[:12]} | "
        f"data {str(payload.get('data_sha256', '?'))[:12]}",
        ha="right",
        va="bottom",
        fontsize=6,
        color="0.45",
    )


def _save(fig, out_path: Path, data: dict[str, Any]) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=160)
    plotdata = out_path.with_suffix(".plotdata.json")
    plotdata.write_text(json.dumps(data, sort_keys=True), encoding="utf-8")
    return out_path


def plot_judge_swap_spread(
    spreads: list[dict], out_dir: str | Path, provenance: dict[str, Any]
) -> Path:
    """Per-model ASR under refusal-based vs verified-harm definitions."""
    plt = _plt()
    models = [s["model_id"].split("/")[-1] for s in spreads]
    refusal = [s["asr_refusal_based"]["estimate"] or 0 for s in spreads]
    harm = [s["asr_verified_harm"]["estimate"] or 0 for s in spreads]
    fig, ax = plt.subplots(figsize=(max(6, 0.7 * len(models)), 4))
    x = range(len(models))
    ax.bar([i - 0.2 for i in x], refusal, width=0.4, label="refusal-based ASR")
    ax.bar([i + 0.2 for i in x], harm, width=0.4, label="verified-harm ASR")
    ax.set_xticks(list(x))
    ax.set_xticklabels(models, rotation=45, ha="right", fontsize=8)
    ax.set_ylabel("ASR")
    ax.set_title("Instrument dependence: refusal-based vs verified-harm ASR")
    ax.legend()
    _stamp(fig, provenance)
    out = _save(
        fig,
        Path(out_dir) / "judge_swap_spread.png",
        {"models": models, "refusal_based": refusal, "verified_harm": harm},
    )
    plt.close(fig)
    return out


def plot_safety_utility_frontier(
    points: list[dict], out_dir: str | Path, provenance: dict[str, Any]
) -> Path:
    """Over-refusal rate (x) vs verified-harm ASR (y): the frontier every
    deployment actually cares about."""
    plt = _plt()
    fig, ax = plt.subplots(figsize=(6, 5))
    xs = [p.get("over_refusal") or 0 for p in points]
    ys = [p.get("verified_harm") or 0 for p in points]
    labels = [p["model_id"].split("/")[-1] for p in points]
    ax.scatter(xs, ys, s=28)
    for x, y, label in zip(xs, ys, labels, strict=True):
        ax.annotate(label, (x, y), fontsize=7, xytext=(3, 3), textcoords="offset points")
    ax.set_xlabel("over-refusal rate (benign battery)")
    ax.set_ylabel("verified-harm ASR")
    ax.set_title("Safety-utility frontier (lower-left is better)")
    _stamp(fig, provenance)
    out = _save(
        fig, Path(out_dir) / "safety_utility_frontier.png", {"x": xs, "y": ys, "labels": labels}
    )
    plt.close(fig)
    return out


def plot_distributional_asr(
    by_setting: dict[int, dict], out_dir: str | Path, provenance: dict[str, Any]
) -> Path:
    """ASR across parameter settings — a distribution, never a point."""
    plt = _plt()
    fig, ax = plt.subplots(figsize=(6, 4))
    temps = sorted(by_setting)
    harm = [by_setting[t]["verified_harm"]["rate"] or 0 for t in temps]
    refusal = [by_setting[t]["refusal_based"]["rate"] or 0 for t in temps]
    ax.plot(temps, refusal, marker="o", label="refusal-based")
    ax.plot(temps, harm, marker="s", label="verified-harm")
    ax.set_xlabel("parameter setting index")
    ax.set_ylabel("ASR")
    ax.set_title("Distributional ASR across settings")
    ax.legend()
    _stamp(fig, provenance)
    out = _save(
        fig,
        Path(out_dir) / "distributional_asr.png",
        {"settings": temps, "refusal_based": refusal, "verified_harm": harm},
    )
    plt.close(fig)
    return out


def plot_transfer_heatmap(
    matrix: dict[str, dict], out_dir: str | Path, provenance: dict[str, Any]
) -> Path:
    plt = _plt()
    sources = sorted(matrix)
    targets = sorted({t for row in matrix.values() for t in row})
    grid = [[(matrix.get(s, {}).get(t, {}) or {}).get("rate") for t in targets] for s in sources]
    fig, ax = plt.subplots(figsize=(max(5, 0.8 * len(targets)), max(3, 0.6 * len(sources))))
    ax.imshow(
        [[v if v is not None else float("nan") for v in row] for row in grid],
        vmin=0,
        vmax=1,
        cmap="viridis",
    )
    ax.set_xticks(range(len(targets)))
    ax.set_xticklabels([t.split("/")[-1] for t in targets], rotation=45, ha="right", fontsize=8)
    ax.set_yticks(range(len(sources)))
    ax.set_yticklabels([s.split("/")[-1] for s in sources], fontsize=8)
    for i, row in enumerate(grid):
        for j, value in enumerate(row):
            if value is not None:
                ax.text(j, i, f"{value:.2f}", ha="center", va="center", fontsize=7)
    ax.set_title("Attack-prompt transfer (verified-harm rate)")
    _stamp(fig, provenance)
    out = _save(fig, Path(out_dir) / "transfer_heatmap.png", {"matrix": matrix})
    plt.close(fig)
    return out


def plot_layer_auroc(
    layer_auroc: dict[str, dict[int, float]], out_dir: str | Path, provenance: dict[str, Any]
) -> Path:
    """Refusal-direction separation by layer, per model (mechanistic layer)."""
    plt = _plt()
    fig, ax = plt.subplots(figsize=(7, 4.5))
    for model_id, curves in sorted(layer_auroc.items()):
        layers = sorted(curves)
        ax.plot(
            layers,
            [curves[layer] for layer in layers],
            label=model_id.split("/")[-1],
            marker=".",
            markersize=3,
        )
    ax.set_xlabel("layer")
    ax.set_ylabel("projection separation AUROC")
    ax.set_title("Refusal direction (diff-in-means) separation by layer")
    ax.legend(fontsize=7)
    _stamp(fig, provenance)
    out = _save(fig, Path(out_dir) / "layer_auroc.png", layer_auroc)
    plt.close(fig)
    return out


__all__ = [
    "plot_judge_swap_spread",
    "plot_safety_utility_frontier",
    "plot_distributional_asr",
    "plot_transfer_heatmap",
    "plot_layer_auroc",
]
