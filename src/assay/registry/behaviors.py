"""Behavior-set registry — upstream benchmarks fetched at pinned revisions.

DESIGN RULE: this repository NEVER redistributes benchmark behavior text.
Behavior sets are fetched from their upstream repositories at setup time
(``assay behaviors fetch``), pinned by exact revision, verified by SHA-256,
recorded in a fetch manifest (license + revision + date), and cached under
``data/cache`` (gitignored). The repo carries only opaque behavior ids,
split assignments, and hashes.

All four upstream sources are verified (see docs/CITATIONS.md).
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

from .verification import VERIFIED_AT_TODAY, Citation

SplitRole = Literal["development", "validation", "holdout", "shift"]


class BehaviorSetSpec(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    set_id: str
    purpose: Literal["harmful", "benign"]  # battery role
    upstream_repo: str
    upstream_path: str  # path to the canonical file inside the repo
    format: Literal["harmbench_csv", "jbb_json", "xstest_csv", "multi_jail_json"]
    license_name: str
    citation: Citation
    split_key: str  # the clustering key for splits and bootstrap (behavior category)
    note: str = ""


BEHAVIOR_SETS: list[BehaviorSetSpec] = [
    BehaviorSetSpec(
        set_id="harmbench_standard",
        purpose="harmful",
        upstream_repo="https://github.com/centerforaisafety/harmbench",
        upstream_path="data/behavior_datasets/harmbench_behaviors_text.csv",
        format="harmbench_csv",
        license_name="MIT (HarmBench repository)",
        split_key="category",
        citation=Citation(
            title="HarmBench: A Standardized Evaluation Framework for Automated Red "
            "Teaming and Robust Refusal",
            authors="Mantas Mazeika, Long Phan, Xuwang Yin et al.",
            venue="ICML 2024",
            url="https://arxiv.org/abs/2402.04249",
            verified_at=VERIFIED_AT_TODAY,
        ),
        note="Standard split, text behaviors; continuum subset per plan.",
    ),
    BehaviorSetSpec(
        set_id="jbb_behaviors",
        purpose="harmful",
        upstream_repo="https://github.com/JailbreakBench/jailbreakbench",
        upstream_path="artifacts/jailbreakbench_0.1/behaviors_mitigated.json",
        format="jbb_json",
        license_name="Apache-2.0 (JailbreakBench repository)",
        split_key="category",
        citation=Citation(
            title="JailbreakBench: An Open Robustness Benchmark for Jailbreaking "
            "Large Language Models",
            authors="Patrick Chao, Edoardo Debenedetti, Alexander Robey et al.",
            venue="NeurIPS 2024 D&B",
            url="https://arxiv.org/abs/2404.01318",
            verified_at=VERIFIED_AT_TODAY,
        ),
        note="Mitigated behaviors set; used for the adaptive battery.",
    ),
    BehaviorSetSpec(
        set_id="xstest",
        purpose="benign",
        upstream_repo="https://github.com/paul-rottger/xstest",
        upstream_path="xstest_v2_1.csv",
        format="xstest_csv",
        license_name="CC-BY 4.0 (XSTest repository)",
        split_key="type",
        citation=Citation(
            title="XSTest: A Test Suite for Identifying Exaggerated Safety Behaviours "
            "in Large Language Models",
            authors="Paul Röttger, Hannah Rose Kirk, Bertie Vidgen et al.",
            venue="NAACL 2024 (Main)",
            url="https://arxiv.org/abs/2308.01263",
            verified_at=VERIFIED_AT_TODAY,
        ),
        note="250 minimally-pairwise prompts — the over-refusal battery.",
    ),
    BehaviorSetSpec(
        set_id="multi_jail",
        purpose="harmful",
        upstream_repo="https://github.com/DAMO-NLP-SG/MultiJail",
        upstream_path="data/multi_jail.json",
        format="multi_jail_json",
        license_name="MIT (MultiJail repository)",
        split_key="language",
        citation=Citation(
            title="Multilingual Jailbreak Challenges in Large Language Models",
            authors="Yue Deng, Wenxuan Zhang, Sinno Jialin Pan et al.",
            venue="ICLR 2024",
            url="https://arxiv.org/abs/2310.06474",
            verified_at=VERIFIED_AT_TODAY,
        ),
        note="Multilingual renderings for the multilingual attack; license verified "
        "at fetch time and recorded in the fetch manifest.",
    ),
]

SETS_BY_ID: dict[str, BehaviorSetSpec] = {s.set_id: s for s in BEHAVIOR_SETS}


def get_behavior_set(set_id: str) -> BehaviorSetSpec:
    try:
        return SETS_BY_ID[set_id]
    except KeyError as exc:
        raise ValueError(
            f"behavior set {set_id!r} is not registered; add a BehaviorSetSpec with a "
            "verified citation and a fetch contract before use"
        ) from exc


__all__ = ["BehaviorSetSpec", "BEHAVIOR_SETS", "SETS_BY_ID", "get_behavior_set", "SplitRole"]
