# Prior-art matrix

How ASSAY relates to the closest existing work. Purpose: identify precisely
what this program adds WITHOUT claiming novelty from a name. All entries
cite primary sources (docs/CITATIONS.md).

| Study | What it does | What remains open that ASSAY addresses |
|---|---|---|
| **JailbreakBench** (Chao et al., NeurIPS 2024 D&B) | Open benchmark + artifacts; calibrated Llama-3-70B refusal judge; over-refusal set | A single judge lineage per artifact; no cross-judge calibration against human labels at panel scale; no verified-harm gate vs refusal distinction at matrix scale |
| **HarmBench** (Mazeika et al., ICML 2024) | Standardized attack–defense evaluation + trained classifier | Classifier-as-single-instrument; no measurement-validity layer (judge-swap spread, distributional ASR) |
| **StrongREJECT** (Souly et al., NeurIPS 2024 D&B) | Rubric penalizing empty jailbreaks; shows ASR inflation | Single-rubric instrument; no multi-instrument triangulation with human calibration |
| **SEAV** (Wu et al., EMNLP 2026) | Epistemic/action-level validity filtering of "successful" responses | Validity filter as proposal; ASSAY operationalizes validated-harm gating as a first-class estimand across a 30+ model matrix with cluster inference |
| **Distributional-ASR position paper** (Maple et al., arXiv:2605.09070) | Argues single-config ASR mischaracterizes; proposes distributions | Position; ASSAY predeclares parameter grids and reports distributions everywhere |
| **Semantic reconstruction** (Davis et al., arXiv:2610.19306) | Judge-swap moves ASR up to 82 points; reconstruction game | Measurement instrument proposal; ASSAY makes the spread a headline estimand with CIs and human calibration |
| **PyRIT** (Microsoft) / **Garak** (NVIDIA) / **EasyJailbreak** | Red-teaming toolkits and composable attacks | Orchestration without frozen statistical protocols, human-calibrated panels, or verified-harm gating; ASSAY is a measurement program that could orchestrate through them |
| **Arditi et al., NeurIPS 2024** | Refusal direction (single direction per layer) on 2024-era open weights | Replication across the Nov-2026 open-weight matrix + functional transfer + ties to behavioral outcomes under calibrated measurement |
| **Monitorability literature** (Korbak et al.; OpenAI monitorability evals; SLEIGHT-Bench) | CoT monitoring value (the predecessor program's field) | Orthogonal channel (reasoning visibility, not reply harmfulness); ASSAY's mechanistic layer shares the direction-extraction toolkit |
| **TRACEGUARD** (predecessor) | CoT-monitorability research kernel with the evidence discipline | Different research question; ASSAY inherits its methodological DNA (documented in README) and rewrites everything from scratch |

## The ASSAY claim (deliberately narrow)

1. First program to report refusal-based, judge-flag, and verified-harm
   susceptibility **side by side** with cluster-bootstrap CIs and
   human-calibrated judges, across a verified 30+ model matrix;
2. distributional (never single-config) susceptibility reporting as a
   default, with TOST-licensed bounded negatives;
3. refusal-direction separation, transfer, and steering tied to the same
   behavioral outcomes under that calibrated measurement;
4. all of it under frozen preregistration with independently verifiable
   evidence.

This is a claim to test, not a novelty assertion. If prior work already
supplies the same controls, the relevant sections become replications and
must be described that way.
