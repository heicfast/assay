"""ASSAY — turning LLM red-team measurement into measurement science.

An assay is a standardized, quantitative test of purity and strength
(metallurgy, pharmacology). This package applies that discipline to LLM
safety: validated instrumentation (multi-judge panels calibrated against
human labels), literature-grounded attacks, mechanistic analysis, frozen
protocols, and independently verifiable evidence.

Non-negotiable program rules (docs/QUALITY.md):
1. No predetermined conclusion — nulls and negatives are valid outcomes.
2. No fake ground truth — harmfulness labels come from the frozen
   verified-harm rules plus the human-labeled calibration subsample,
   never silently from a single LLM judge.
3. No benchmark leakage — splits, judges, thresholds, and rubrics freeze
   before evaluation; changes go to docs/DEVIATIONS.md.
4. No GPU dependency for core correctness — planning, evidence, judging
   orchestration, statistics, and tests run on CPU.
"""

from __future__ import annotations

__version__ = "0.1.0"
SCHEMA_VERSION = "1.0.0"

__all__ = ["__version__", "SCHEMA_VERSION"]
