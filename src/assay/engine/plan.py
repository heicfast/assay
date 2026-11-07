"""Trial planning: the immutable grid executed by the runner.

The plan is a pure function of (config, battery, registry): same inputs ->
same plan -> same trial ids. A plan manifest (hash-pinned) lands in every
run directory, and a run refuses to execute against a different plan.

Grid axes: target x attack x behavior x parameter-setting x replicate-seed.
Rules applied at plan time (never silently at runtime):
* reasoning-channel attacks pair only with reasoning targets;
* the multilingual attack pairs only with translated multi_jail behaviors;
* white-box attacks pair only with local open-weight targets;
* ``core`` grid (expensive flagships) multiplies the behavior x attack grid
  by the predeclared core fractions — a RECORDED treatment, never equal to
  ``full`` in the same table without a flag.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict

from ..behaviors.model import Behavior
from ..config import ExperimentConfig
from ..ids import digest_id, sha256_json, trial_id
from ..registry.attacks import get_attack
from ..registry.models import get_model_profile

CORE_GRID = {"behaviors": 0.4, "attacks": 0.6, "seeds": 1}


class PlannedTrial(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    trial_id: str
    model_id: str
    attack_id: str
    behavior_id: str
    cluster: str
    split_role: str
    battery: str  # harmful | benign
    param_setting: dict[str, Any]
    setting_index: int
    seed: int
    variant: str
    grid: str


def _settings_grid(sampling) -> list[dict[str, Any]]:
    grid = sampling.parameter_grid
    keys = sorted(grid)
    settings: list[dict[str, Any]] = []
    if not keys:
        settings.append({"temperature": sampling.temperature})
        return settings

    def recurse(index: int, current: dict[str, Any]) -> None:
        if index == len(keys):
            settings.append(dict(current))
            return
        key = keys[index]
        for value in grid[key]:
            current[key] = value
            recurse(index + 1, current)

    recurse(0, {})
    return settings


def build_plan(
    config: ExperimentConfig, battery: list[Behavior], run_id: str
) -> list[PlannedTrial]:
    trials: list[PlannedTrial] = []
    for target in config.targets:
        profile = _profile_for(target.model_id)
        harmful = [b for b in battery if b.set_id not in config.behaviors.benign_sets]
        benign = [b for b in battery if b.set_id in config.behaviors.benign_sets]
        if target.grid == "core":

            def take(rows: list[Behavior]) -> list[Behavior]:
                wanted = max(1, int(len(rows) * CORE_GRID["behaviors"]))
                return rows[:wanted] if rows else rows

            harmful = take(harmful)
            benign = take(benign)
        for assignment in config.attacks:
            spec = get_attack(assignment.attack_id)
            if spec.reasoning_only and profile.reasoning_protocol == "none":
                continue  # factor-design rule; counted in the plan census
            if spec.requires_white_box and profile.kind != "open_weights":
                continue
            if target.grid == "core":
                keep = max(1, int(len(config.attacks) * CORE_GRID["attacks"]))
                if config.attacks.index(assignment) >= keep:
                    continue
            for setting_index, setting in enumerate(_settings_grid(target.sampling)):
                pool = harmful if spec.mode != "optimization" else harmful[:8]
                for behavior in pool:
                    if assignment.attack_id == "multilingual" and not (
                        behavior.set_id == "multi_jail" and behavior.language != "en"
                    ):
                        continue
                    seeds = [
                        config.seed
                        + 1000 * setting_index
                        + hash_pos(target.model_id, assignment.attack_id, behavior.behavior_id)
                    ]
                    for seed in seeds:
                        trials.append(
                            PlannedTrial(
                                trial_id=trial_id(
                                    run_id,
                                    target.model_id,
                                    assignment.attack_id,
                                    behavior.behavior_id,
                                    seed,
                                    f"s{setting_index}",
                                ),
                                model_id=target.model_id,
                                attack_id=assignment.attack_id,
                                behavior_id=behavior.behavior_id,
                                cluster=behavior.cluster,
                                split_role=behavior.split_role,
                                battery="harmful",
                                param_setting=setting,
                                setting_index=setting_index,
                                seed=seed,
                                variant=f"s{setting_index}",
                                grid=target.grid,
                            )
                        )
        # benign battery: every target answers each benign behavior once
        # (fixed mid temperature) — the over-refusal measurement.
        for behavior in benign:
            seed = config.seed + 7 * hash_pos(target.model_id, "benign", behavior.behavior_id)
            trials.append(
                PlannedTrial(
                    trial_id=trial_id(
                        run_id, target.model_id, "benign_probe", behavior.behavior_id, seed, "b0"
                    ),
                    model_id=target.model_id,
                    attack_id="benign_probe",
                    behavior_id=behavior.behavior_id,
                    cluster=behavior.cluster,
                    split_role=behavior.split_role,
                    battery="benign",
                    param_setting={"temperature": 0.7},
                    setting_index=0,
                    seed=seed,
                    variant="b0",
                    grid=target.grid,
                )
            )
    seen: set[str] = set()
    for trial in trials:
        if trial.trial_id in seen:
            raise ValueError(f"duplicate trial id: {trial.trial_id}")
        seen.add(trial.trial_id)
    return trials


class _MockProfileView:
    """Registry-shaped shim for smoke/test mocks (kind/protocol only)."""

    kind = "remote_api"
    reasoning_protocol = "none"


def _profile_for(model_id: str):
    if model_id.startswith("mock/"):
        return _MockProfileView()
    return get_model_profile(model_id)


def hash_pos(*parts: str) -> int:
    """Stable non-salted positive int for seed derivation."""
    return int(digest_id("seed", *parts).split("-")[1][:12], 16) % 1_000_000


def plan_manifest(
    config: ExperimentConfig, trials: list[PlannedTrial], battery_manifest_sha256: str
) -> dict:
    census = {
        "trials_total": len(trials),
        "by_battery": _count(trials, lambda t: t.battery),
        "by_attack": _count(trials, lambda t: t.attack_id),
        "by_model": _count(trials, lambda t: t.model_id),
        "by_grid": _count(trials, lambda t: t.grid),
        "skipped_reasoning_channel": _skipped_reasoning(config),
    }
    payload = {
        "schema_version": "1.0.0",
        "config_sha256": config.config_sha256,
        "battery_manifest_sha256": battery_manifest_sha256,
        "census": census,
        "trials": [t.model_dump() for t in trials],
    }
    payload["plan_manifest_sha256"] = sha256_json(
        {k: v for k, v in payload.items() if k != "plan_manifest_sha256"}
    )
    return payload


def _count(trials: list[PlannedTrial], key) -> dict[str, int]:
    out: dict[str, int] = {}
    for trial in trials:
        out[str(key(trial))] = out.get(str(key(trial)), 0) + 1
    return dict(sorted(out.items()))


def _skipped_reasoning(config: ExperimentConfig) -> int:
    skipped = 0
    for target in config.targets:
        profile = _profile_for(target.model_id)
        if profile.reasoning_protocol == "none":
            skipped += sum(1 for a in config.attacks if get_attack(a.attack_id).reasoning_only)
    return skipped


__all__ = ["PlannedTrial", "build_plan", "plan_manifest", "hash_pos", "CORE_GRID"]
