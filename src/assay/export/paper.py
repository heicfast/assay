"""LaTeX/CSV paper tables derived from verified analysis reports only.

Formatting ONLY: no statistic is computed here. Every row carries the
report hash it came from (traceable to bytes).
"""

from __future__ import annotations

import csv
import io
from pathlib import Path
from typing import Any


def _fmt(value: Any) -> str:
    if value is None:
        return "--"
    if isinstance(value, float):
        return f"{value:.3f}" if value < 100 else f"{value:.1f}"
    return str(value)


def table_asr_by_model(report: dict, out_dir: str | Path) -> list[Path]:
    rows = report.get("by_model", {})
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    csv_path = out / "asr_by_model.csv"
    latex_path = out / "asr_by_model.tex"
    header = [
        "model",
        "n",
        "refusal_asr",
        "verified_harm_asr",
        "spread",
        "ci_low",
        "ci_high",
        "over_refusal",
    ]
    csv_lines = [",".join(header)]
    latex = [
        "\\begin{tabular}{lrrrrrrr}",
        "\\toprule",
        " & ".join(header) + " \\\\",
        "\\midrule",
    ]
    for model_id, entry in sorted(rows.items()):
        refusal = entry.get("asr_refusal_based", {}).get("estimate")
        harm = entry.get("asr_verified_harm", {}).get("estimate")
        ci = entry.get("asr_verified_harm", {})
        row = [
            _fmt(model_id),
            _fmt(entry.get("n")),
            _fmt(refusal),
            _fmt(harm),
            _fmt(entry.get("spread_refusal_minus_harm")),
            _fmt(ci.get("ci_low")),
            _fmt(ci.get("ci_high")),
            _fmt(entry.get("over_refusal", {}).get("rate")),
        ]
        csv_lines.append(",".join(_fmt(v) for v in row))
        latex.append(" & ".join(row) + " \\\\")
    latex += ["\\bottomrule", "\\end{tabular}"]
    csv_path.write_text("\n".join(csv_lines) + "\n", encoding="utf-8")
    latex_path.write_text("\n".join(latex) + "\n", encoding="utf-8")
    stamp = f"%% report sha256: {report.get('report_sha256', '?')}\n"
    latex_path.write_text(stamp + latex_path.read_text(encoding="utf-8"), encoding="utf-8")
    return [csv_path, latex_path]


def table_economics(report: dict, out_dir: str | Path) -> Path:
    rows = report.get("economics", {}).get("by_attack_model", {})
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    path = out / "cost_per_success.csv"
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["attack|model", "trials", "successes", "spend_usd", "usd_per_success"])
    for key, entry in sorted(rows.items()):
        writer.writerow(
            [
                key,
                entry.get("trials"),
                entry.get("successes"),
                _fmt(entry.get("spend_usd")),
                _fmt(entry.get("usd_per_success")),
            ]
        )
    path.write_text(buffer.getvalue(), encoding="utf-8")
    return path


__all__ = ["table_asr_by_model", "table_economics"]
