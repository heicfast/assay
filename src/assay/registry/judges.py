"""Judge registry — the measurement instruments, with verified citations.

Judge kinds:
* ``classifier``  — guard models served locally; verdicts derived from the
  model's own card-specified prompt contract.
* ``rubric``       — LLM judges scoring under a frozen rubric
  (severity 0-5, StrongREJECT-style; semantic-reconstruction verified-harm).
* ``refusal``      — refusal detection (string-based + semantic), validated
  against the human-labeled calibration subsample before any research use.

Every judge's prompt is a frozen constant whose hash is registered before
first use (verification battery) — the same discipline that kept the
predecessor program's instruments honest.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

from .verification import VERIFIED_AT_TODAY, Citation

JudgeKind = Literal["classifier", "rubric", "refusal"]


class JudgeSpec(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    judge_id: str
    kind: JudgeKind
    model_ref: str  # registry model_id (classifier) or "panel:<lab-diverse>"
    citation: Citation
    output: str  # "binary" | "score_0_5" | "refusal_binary" | "harm_verified"
    note: str = ""


_JUDGES: list[JudgeSpec] = [
    JudgeSpec(
        judge_id="llama_guard_4",
        kind="classifier",
        model_ref="meta-llama/Llama-Guard-4-12B",
        output="binary",
        citation=Citation(
            title="Llama Guard: LLM-based Input-Output Safeguard for Human-AI Conversations",
            authors="Hakan Inan, Kartikeya Upasani, Jianfeng Chi et al.",
            venue="arXiv 2023",
            url="https://arxiv.org/abs/2312.06674",
            verified_at=VERIFIED_AT_TODAY,
        ),
        note="Guard-4 weights (HF-verified 2026-11-07); card prompt contract enforced by probe.",
    ),
    JudgeSpec(
        judge_id="shieldgemma",
        kind="classifier",
        model_ref="google/shieldgemma-9b",
        output="binary",
        citation=Citation(
            title="ShieldGemma: Generative AI Content Moderation Based on Gemma",
            authors="Wenjun Zeng, Yuchi Liu, Ryan Mullins et al.",
            venue="arXiv 2024 (Google DeepMind)",
            url="https://arxiv.org/abs/2407.21772",
            verified_at=VERIFIED_AT_TODAY,
        ),
        note="CANDIDATE repo id — probe pins before use.",
    ),
    JudgeSpec(
        judge_id="wildguard",
        kind="classifier",
        model_ref="allenai/wildguard",
        output="binary",
        citation=Citation(
            title="WildGuard: Open One-Stop Moderation Tools for Safety Risks, "
            "Jailbreaks, and Refusals of LLMs",
            authors="Seungju Han, Kavel Rao, Allyson Ettinger et al.",
            venue="NeurIPS 2024",
            url="https://arxiv.org/abs/2406.18495",
            verified_at=VERIFIED_AT_TODAY,
        ),
        note="CANDIDATE repo id — probe pins before use.",
    ),
    JudgeSpec(
        judge_id="harmbench_cls",
        kind="classifier",
        model_ref="harmbench-classifier",
        output="binary",
        citation=Citation(
            title="HarmBench: A Standardized Evaluation Framework for Automated Red "
            "Teaming and Robust Refusal",
            authors="Mantas Mazeika, Long Phan, Xuwang Yin et al.",
            venue="ICML 2024",
            url="https://arxiv.org/abs/2402.04249",
            verified_at=VERIFIED_AT_TODAY,
        ),
        note="CANDIDATE checkpoint id — probe pins from the verified repo.",
    ),
    JudgeSpec(
        judge_id="sreject_rubric",
        kind="rubric",
        model_ref="panel:cross_lab",
        output="score_0_5",
        citation=Citation(
            title="A StrongREJECT for Empty Jailbreaks",
            authors="Alexandra Souly, Qingyuan Lu, Dillon Bowen et al.",
            venue="NeurIPS 2024 D&B",
            url="https://arxiv.org/abs/2402.10260",
            verified_at=VERIFIED_AT_TODAY,
        ),
        note="Frozen 0-5 severity rubric (StrongREJECT-style); penalizes empty/"
        "non-actionable responses; panel run cross-lab to avoid self-preference.",
    ),
    JudgeSpec(
        judge_id="semantic_recon",
        kind="rubric",
        model_ref="panel:cross_lab",
        output="harm_verified",
        citation=Citation(
            title="Did the LLM Answer the Question? A Semantic Reconstruction Game "
            "for Jailbreak Evaluation",
            authors="Liam Davis, Romain Emil-Popescu, Suman Jana",
            venue="arXiv 2026",
            url="https://arxiv.org/abs/2610.19306",
            verified_at=VERIFIED_AT_TODAY,
        ),
        note="Verified-harm gate: did the response actually fulfill the harmful "
        "request (answer the question), vs merely refusing to refuse.",
    ),
    JudgeSpec(
        judge_id="refusal_semantic",
        kind="refusal",
        model_ref="panel:cross_lab",
        output="refusal_binary",
        citation=Citation(
            title="JailbreakBench: An Open Robustness Benchmark for Jailbreaking "
            "Large Language Models",
            authors="Patrick Chao, Edoardo Debenedetti, Alexander Robey et al.",
            venue="NeurIPS 2024 D&B",
            url="https://arxiv.org/abs/2404.01318",
            verified_at=VERIFIED_AT_TODAY,
        ),
        note="Semantic refusal detection with a string-based fallback; both validated "
        "against the human-labeled subsample (agreement reported with every result).",
    ),
]

JUDGES_BY_ID: dict[str, JudgeSpec] = {j.judge_id: j for j in _JUDGES}


def get_judge(judge_id: str) -> JudgeSpec:
    try:
        return JUDGES_BY_ID[judge_id]
    except KeyError as exc:
        raise ValueError(
            f"judge {judge_id!r} is not registered; add a JudgeSpec with a "
            "verified citation and a frozen prompt contract before use"
        ) from exc


__all__ = ["JudgeSpec", "JUDGES_BY_ID", "get_judge", "JudgeKind"]
