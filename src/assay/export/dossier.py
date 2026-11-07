"""Per-model dossiers: the browsing unit for later analysis and writing."""

from __future__ import annotations

from pathlib import Path
from typing import Any


def render_dossier(model_id: str, model_report: dict[str, Any]) -> str:
    refusal = model_report.get("asr_refusal_based", {})
    harm = model_report.get("asr_verified_harm", {})
    over = model_report.get("over_refusal", {})
    severity = model_report.get("severity", {})
    lines = [
        f"# Dossier — `{model_id}`",
        "",
        f"- trials (harmful, completed): **{model_report.get('n', 0)}**",
        f"- refusal-based ASR: **{_fmt(refusal.get('estimate'))}**"
        f" (CI {_fmt(refusal.get('ci_low'))}–{_fmt(refusal.get('ci_high'))};"
        f" status {refusal.get('ci_status')})",
        f"- verified-harm ASR: **{_fmt(harm.get('estimate'))}**"
        f" (CI {_fmt(harm.get('ci_low'))}–{_fmt(harm.get('ci_high'))};"
        f" status {harm.get('ci_status')})",
        f"- spread (refusal − harm): **{_fmt(model_report.get('spread_refusal_minus_harm'))}**"
        " — the instrument-dependence gap",
        f"- over-refusal (benign battery): **{_fmt(over.get('rate'))}** on n={over.get('n', 0)}",
        f"- severity: mean **{_fmt(severity.get('mean'))}**,"
        f" share ≥4 **{_fmt(severity.get('ge4_rate'))}**",
        "",
        "## Reading rules",
        "- The spread between refusal-based and verified-harm ASR is the",
        "  measurement-validity finding: it measures the INSTRUMENT, not the model.",
        "- CIs labeled `not_estimable` are honest (gates failed); the point",
        "  estimate is still reported, never promoted.",
    ]
    return "\n".join(lines) + "\n"


def write_dossiers(report: dict, out_dir: str | Path) -> list[Path]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for model_id, model_report in sorted(report.get("by_model", {}).items()):
        path = out / (model_id.replace("/", "_") + ".md")
        path.write_text(render_dossier(model_id, model_report), encoding="utf-8")
        paths.append(path)
    return paths


def _fmt(value: Any) -> str:
    if value is None:
        return "--"
    if isinstance(value, float):
        return f"{value:.3f}"
    return str(value)


__all__ = ["render_dossier", "write_dossiers"]
