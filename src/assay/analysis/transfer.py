"""Transfer matrices + attack economics (cost per verified success)."""

from __future__ import annotations

from typing import Any

from ..registry.models import get_model_profile


def transfer_matrix(trials: list[dict], verdicts: list[dict]) -> dict[str, Any]:
    """Success of attack prompts discovered on model A when replayed on B.

    Trials tagged ``variant=xf:<source_model>`` are replays; the matrix
    cell (A,B) = verified-harm rate of A's successful prompts on B.
    """
    by_trial = {v["trial_id"]: v for v in verdicts if v.get("judge_id") == "semantic_recon"}
    replay_rows = [t for t in trials if str(t.get("variant", "")).startswith("xf:")]
    cells: dict[str, dict[str, dict]] = {}
    for row in replay_rows:
        source = str(row["variant"])[3:].split("|")[0]
        target = row["model_id"]
        verdict = by_trial.get(row["trial_id"])
        if verdict is None:
            continue
        cell = cells.setdefault(source, {}).setdefault(target, {"n": 0, "hits": 0})
        cell["n"] += 1
        if verdict.get("value") is True:
            cell["hits"] += 1
    for _source, row in cells.items():
        for _target, cell in row.items():
            cell["rate"] = round(cell["hits"] / cell["n"], 4) if cell["n"] else None
    return {"matrix": cells, "n_replay_trials": len(replay_rows)}


def cost_per_success(trials: list[dict], verdicts: list[dict]) -> dict[str, Any]:
    """USD per VERIFIED-HARM success, by attack and model (API targets only:
    local targets are metered as compute hours, not per call)."""
    by_trial = {v["trial_id"]: v for v in verdicts if v.get("judge_id") == "semantic_recon"}
    rows: dict[str, dict] = {}
    for trial in trials:
        if trial.get("battery") != "harmful" or trial.get("status") != "completed":
            continue
        try:
            profile = get_model_profile(trial["model_id"])
        except Exception:
            continue  # smoke-tier mocks are not priced — skip, never crash the audit
        if profile.api is None or profile.pricing is None:
            continue
        usage = trial.get("token_usage", {})
        cost = (
            usage.get("prompt_tokens", 0) * profile.pricing.input_usd_per_mtok / 1e6
            + usage.get("completion_tokens", 0) * profile.pricing.output_usd_per_mtok / 1e6
        )
        key = f"{trial['attack_id']}|{trial['model_id']}"
        entry = rows.setdefault(key, {"spend_usd": 0.0, "successes": 0, "trials": 0})
        entry["spend_usd"] += cost
        entry["trials"] += 1
        verdict = by_trial.get(trial["trial_id"])
        if verdict is not None and verdict.get("value") is True:
            entry["successes"] += 1
    out: dict[str, Any] = {}
    for key, entry in rows.items():
        out[key] = {
            "spend_usd": round(entry["spend_usd"], 4),
            "trials": entry["trials"],
            "successes": entry["successes"],
            "usd_per_success": (
                round(entry["spend_usd"] / entry["successes"], 4) if entry["successes"] else None
            ),
        }
    return {"by_attack_model": dict(sorted(out.items()))}


__all__ = ["transfer_matrix", "cost_per_success"]
