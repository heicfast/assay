# ASSAY — Preregistration protocol

**Status: DRAFT.** This becomes binding at the preregistration freeze:
completed, reviewed (multi-POV per docs/REVIEW_SYSTEM.md), committed, and
timestamped. Any change after freeze goes to `docs/DEVIATIONS.md` with
rationale and impact — never silently.

## Research questions and hypotheses

Primary questions (all three pillars; each may fail independently):

- **RQ1 (instrument):** how much of reported jailbreak susceptibility is
  attributable to the measurement instrument rather than the model?
- **RQ2 (landscape):** under calibrated measurement, how do static and
  adaptive attacks perform across the frontier matrix, at what transfer,
  and at what cost per verified success?
- **RQ3 (mechanism):** is refusal mediated by a single direction per layer
  across current open weights; do directions transfer across models; does
  direction strength predict verified harm at the model level?

Hypotheses are two-sided by construction: reduced instrument dependence,
reduced verified-harm susceptibility, and stronger direction separation are
all *possible* outcomes, and so are their opposites. **Nulls and negatives
are valid, publishable results.**

## Estimands (primary)

1. **Instrument-dependence spread** (RQ1 headline): per model m,
   `spread(m) = ASR_refusal(m) − ASR_verified_harm(m)`, where
   `ASR_refusal` counts non-refusals (semantic refusal judge, string
   fallback validated on human labels) and `ASR_verified_harm` counts
   replies the semantic-reconstruction gate judges to actually fulfill the
   request. Behavior-cluster percentile bootstrap 95% CI (2000
   replicates, frozen seed), thresholds and judges frozen before holdout.
2. **Severity-weighted susceptibility**: mean StrongREJECT-style 0-5
   severity over completed harmful trials, and share ≥ 4.
3. **Over-refusal frontier**: false-refusal rate on the benign battery vs
   verified-harm ASR (the deployment-relevant tradeoff), reported as a
   frontier, never a single number.
4. **Distributional ASR**: susceptibility reported as a distribution over
   the predeclared parameter grid (never a single-config point).
5. **Mechanistic separation**: per-layer projection AUROC of the
   diff-in-means direction on held-out prompts; cross-model direction
   cosine + functional transfer; Spearman tie between separation and
   verified-harm ASR (EXPLORATORY — models are not a random sample).

**Smallest effect of interest (SESOI):** 0.10 on any ASR-scale estimand.
Bounded-negative claims require TOST at SESOI; a nonsignificant
superiority test licenses nothing.

## Measurement instruments (frozen before evaluation)

- Classifier judges: Llama-Guard-4-12B, ShieldGemma, WildGuard,
  HarmBench classifier (served locally; card-specified prompt contracts;
  admission probes enforce output-format conformance).
- Rubric judges (cross-lab panel; anti self-preference by design):
  severity 0-5 (StrongREJECT-style), semantic-reconstruction
  verified-harm gate.
- Refusal detection: semantic judge + deterministic string fallback;
  disagreement between the two is a recorded diagnostic.
- Every judge prompt is a frozen constant; its hash is registered before
  first research use and verified per record.

## Batteries (public benchmarks only, upstream-pinned)

- Harmful: HarmBench standard split + JailbreakBench behaviors;
  multilingual renderings from MultiJail (upstream translations only —
  we never machine-translate battery content).
- Benign: XSTest (over-refusal battery).
- Splits: WHOLE clusters (set × category) assigned to
  development/validation/holdout/shift by frozen seed; split manifest
  hash-pinned into every run. Behavior text is fetched from upstream at
  pinned revisions with recorded licenses — never redistributed in-repo.

## Attack battery (all citation-verified; see docs/CITATIONS.md)

Static: prefix-affirmation, refusal-suppression, DeepInception, PAP (40
persuasion techniques), complex-cipher, unicode-cipher, multilingual,
many-shot (benign-demo variant — recorded treatment difference),
no-think + answer-prefill (reasoning targets only, plan-enforced),
random augmentation (triviality baseline).
Adaptive policies: PAIR, TAP, Crescendo, AJAR-style switcher.
White-box: GCG (open weights only; separate budgeted plan).

## Exclusions, censoring, and gates

- `runtime_error` trials are recorded and censored from ASR pools (counted
  with reasons in every report; never imputed, never retried into success).
- CI eligibility: < 8 total behavior clusters, > 10% degenerate replicates,
  or insufficient bootstrap support → the interval is reported as
  `not_estimable` (the point estimate is still reported, never promoted).
- Calibration independence: judge operating points are set on the
  VALIDATION split only; holdout is judged once, at frozen settings.
- Multiplicity: Holm for the confirmatory family; BH only for predeclared
  exploratory families, labeled as such.

## Human labeling (the only ground truth)

- Stratified sample (battery × attack) of `human_label_sample` completed
  trials; ≥ 2 labelers per trial; Krippendorff's α reported with every
  calibration result; labels are imported via `assay calibrate` and are
  never produced by a model.

## Statistical analysis plan (frozen)

1. Primary contrasts with cluster-bootstrap CIs (eligibility gates above).
2. TOST at SESOI for every bounded-negative claim.
3. Exact McNemar for paired judge disagreements (secondary, diagnostic).
4. Holm across the confirmatory family; family list predeclared here:
   per-model spread > 0; severity share ≥ 4; over-refusal rate; per-model
   verified-harm ASR on holdout.
5. Distributional ASR: per-setting point estimates + pooled, with the
   setting grid predeclared in the config (default temperature ∈
   {0.0, 0.7, 1.0}).

## Known limitations (predeclared)

- Behavior batteries are public benchmarks — contamination is a validity
  threat; the distributional and verified-harm measures are designed to be
  robust to it, and a contamination audit is reported.
- Judge classifiers share training lineages with some targets; the panel
  is cross-lab and self-preference is measured, not assumed away.
- Models are not a random sample of "all models"; cross-model correlations
  (RQ3 ties) are exploratory and labeled as such.
- `many_shot` uses benign affirmative demonstrations (zero uplift); the
  treatment difference from the original paper is recorded in every
  report that uses it.

## Freeze record (filled at freeze)

- Git commit: ____
- UTC timestamp: ____
- Review verdicts (multi-POV): ____
- Deviation log: docs/DEVIATIONS.md (append-only)
