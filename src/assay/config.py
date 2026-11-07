"""Experiment configuration — the frozen contract (docs/PROTOCOL.md §Freeze).

A config is only a config once committed and hash-pinned: every run records
``config_sha256`` in its manifest, and a run directory is frozen to exactly
one config hash (drift aborts execution). ``PIN_EXACT_*`` placeholders are
refused by research stages — the admission probe or the operator must pin
real values first (fail-closed, like every registry candidate).
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from .ids import sha256_json

Stage = Literal["smoke", "pilot", "confirmatory", "mechanistic", "calibration"]
DeterminismClass = Literal["seeded_local", "seeded_server_best_effort", "unseeded_api"]


class SamplingParams(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    temperature: float = 0.7
    top_p: float = 0.95
    top_k: int = 40
    max_tokens: int = 1024
    # Distributional-ASR arm (Maple et al. 2026): predeclared parameter grid
    # over which susceptibility is reported as a DISTRIBUTION, never a point.
    parameter_grid: dict[str, list[float]] = Field(
        default_factory=lambda: {"temperature": [0.0, 0.7, 1.0]}
    )


class TargetAssignment(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    model_id: str
    tier: str = ""  # aws_a100_80gb | aws_h100_80gb (local models)
    probe_sha256: str | None = None
    revision: str = "PIN_EXACT_REVISION_BEFORE_RUN"
    served_id: str | None = None  # probe-pinned served string (API + local)
    determinism_class: DeterminismClass = "seeded_server_best_effort"
    sampling: SamplingParams = Field(default_factory=SamplingParams)
    # Expensive flagships run the predeclared CORE grid (fewer behaviors x
    # attacks), recorded as a treatment — never silently equal to the full grid.
    grid: Literal["core", "full"] = "full"


class AttackAssignment(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    attack_id: str
    params: dict[str, Any] = Field(default_factory=dict)


class AttackerAssignment(BaseModel):
    """The LLM adversary used by policy-mode attacks (cross-lab by default)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    model_id: str
    determinism_class: DeterminismClass = "seeded_server_best_effort"
    sampling: SamplingParams = Field(
        default_factory=lambda: SamplingParams(temperature=1.0, top_p=1.0, max_tokens=512)
    )


class BehaviorPlan(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    harmful_sets: list[str]
    benign_sets: list[str]
    max_behaviors_per_set: int = 100
    per_category_cap: int = 10  # caps dominance of any one cluster
    split_seed: int = 20261107
    # Split fractions are frozen BEFORE evaluation; changes post-freeze are
    # deviations logged in docs/DEVIATIONS.md.
    split_fractions: dict[str, float] = Field(
        default_factory=lambda: {
            "development": 0.4,
            "validation": 0.2,
            "holdout": 0.2,
            "shift": 0.2,
        }
    )


class JudgePanel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    judges: list[str] = Field(
        default_factory=lambda: [
            "sreject_rubric",
            "semantic_recon",
            "refusal_semantic",
            "llama_guard_4",
            "shieldgemma",
            "wildguard",
            "harmbench_cls",
        ]
    )
    panel_models: list[str] = Field(default_factory=list)
    operating_fpr: float = 0.05
    calibration_split: str = "validation"
    human_label_sample: int = 400  # stratified subsample for calibration
    human_labelers: int = 3


class MechanisticPlan(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    models: list[str]
    layers: Literal["all", "late", "specified"] = "all"
    layer_list: list[int] = Field(default_factory=list)
    direction_method: Literal["diff_in_means", "both"] = "diff_in_means"
    steering_multipliers: list[float] = Field(
        default_factory=lambda: [-4.0, -2.0, -1.0, 1.0, 2.0, 4.0]
    )
    prompts_per_class: int = 64


class AnalysisConfig(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    cluster_key: str = "behavior_cluster"  # (set, category) — never the raw behavior
    bootstrap_replicates: int = 2000
    bootstrap_seed: int = 20261107
    confidence_level: float = 0.95
    sesoi: float = 0.10
    # CI-eligibility gates (a point estimate may exist while its interval is
    # honestly labeled not_estimable)
    min_total_clusters_for_ci: int = 8
    min_positive_clusters_for_ci: int = 4
    max_degenerate_fraction_for_ci: float = 0.10
    min_bootstrap_support_for_ci: int = 3
    multiplicity: Literal["holm", "bh"] = "holm"  # holm confirmatory / bh exploratory


class BudgetConfig(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    hard_cap_usd: float = 4000.0
    warn_at_fraction: float = 0.8
    api_call_cap_per_run: int = 25_000


class ProvenanceConfig(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    code_revision: str = "PIN_EXACT_COMMIT_BEFORE_RUN"
    experiment_name: str = "unnamed"
    stage: Stage = "smoke"


class ExperimentConfig(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    experiment_name: str
    stage: Stage
    seed: int
    targets: list[TargetAssignment]
    attacks: list[AttackAssignment]
    attackers: list[AttackerAssignment] = Field(default_factory=list)
    behaviors: BehaviorPlan
    judges: JudgePanel = Field(default_factory=JudgePanel)
    mechanistic: MechanisticPlan | None = None
    analysis: AnalysisConfig = Field(default_factory=AnalysisConfig)
    budget: BudgetConfig = Field(default_factory=BudgetConfig)
    provenance: ProvenanceConfig = Field(default_factory=ProvenanceConfig)

    @property
    def config_sha256(self) -> str:
        return sha256_json(self.model_dump())

    def get_target_ids(self) -> list[str]:
        return [t.model_id for t in self.targets]

    def get_attacker_ids(self) -> list[str]:
        return [a.model_id for a in self.attackers]

    def validate_placeholders(self) -> list[str]:
        """Research stages refuse placeholder pins (fail closed)."""
        problems: list[str] = []
        if "PIN_" in self.provenance.code_revision:
            problems.append("provenance.code_revision is a placeholder")
        for target in self.targets:
            if "PIN_" in target.revision and target.model_id.startswith(
                (
                    "Qwen/",
                    "deepseek-ai/",
                    "zai-org/",
                    "meta-llama/",
                    "openai/",
                    "mistralai/",
                    "google/",
                    "moonshotai/",
                    "tencent/",
                    "nvidia/",
                    "meituan-longcat/",
                    "MiniMaxAI/",
                    "allenai/",
                    "harmbench",
                )
            ):
                problems.append(f"{target.model_id}: revision placeholder not pinned")
        return problems


def load_config(path: str) -> ExperimentConfig:
    import yaml

    with open(path, encoding="utf-8") as handle:
        raw = yaml.safe_load(handle)
    return ExperimentConfig.model_validate(raw)


__all__ = [
    "ExperimentConfig",
    "SamplingParams",
    "TargetAssignment",
    "AttackAssignment",
    "AttackerAssignment",
    "BehaviorPlan",
    "JudgePanel",
    "MechanisticPlan",
    "AnalysisConfig",
    "BudgetConfig",
    "ProvenanceConfig",
    "load_config",
    "Stage",
    "DeterminismClass",
]
