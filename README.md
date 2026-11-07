# ASSAY

**A standardized, quantitative test of purity and strength — applied to LLM safety.**

An *assay* (metallurgy, pharmacology) is a rigorous, standardized test that
quantifies how much of the substance you care about is actually present.
This project applies that discipline to LLM red-teaming, where the central,
lab-acknowledged problem is that **reported jailbreak susceptibility mostly
measures the instrument, not the model**.

> Swapping the judge moves measured attack success by up to 82 points;
> "successful" jailbreaks are often non-actionable; refusal is conflated
> with harm; single-config attack-success rates mischaracterize threats;
> fixed benchmarks are gameable. (All citations verified — see
> [`docs/CITATIONS.md`](docs/CITATIONS.md).)

ASSAY measures the **instrument**, the **model**, and the **mechanism** —
together:

1. **RQ1 — Instrument validity.** A multi-judge panel (open classifiers +
   cross-lab rubric judges) calibrated against a human-labeled subsample;
   refusal-based vs judge-flag vs **verified-harm** attack success reported
   side by side (the gap between them *is* the finding); severity-weighted
   scoring; distributional ASR over parameter settings; over-refusal
   frontier on benign batteries.
2. **RQ2 — Attack landscape at scale.** A literature-grounded battery
   (every attack citation-verified) plus adaptive multi-turn attackers,
   across the verified Nov-2026 model matrix (30+ models, all labs), with
   transfer matrices and cost-per-verified-success economics.
3. **RQ3 — Mechanistic layer.** Refusal-direction extraction
   (diff-in-means per layer), bidirectional steering, and cross-model
   direction transfer on open weights — triangulated against the
   behavioral outcomes (does the direction's strength predict verified
   harm at the model level?).

**Methodological lineage.** This program is a from-scratch successor to
[TRACEGUARD](https://github.com/heicfast/traceguard) (CoT-monitorability
research). No code or data carries over; what carries over is its
evidence discipline: frozen preregistration with an append-only deviation
log, hash-chained resumable runs, write-ahead transactions, verified or
candidate records for every infrastructure fact, CI-eligibility gates on
every interval, TOST for bounded negatives, fail-closed budgets, and
multi-POV independent reviews.

## Status

| Milestone | State |
|---|---|
| M0 program design + registries (51 models, 16 attacks, 7 judges, 4 behavior sets — all source-verified) | done |
| M1 evidence kernel (WAL, journal, checksums, index, verification audit) | done — 70+ tests green, ruff + mypy clean |
| M2 attack battery (11 static + 4 adaptive policies + white-box GCG) | done |
| M3 judge panel + leakage firewall + calibration pipeline | done |
| M4 CLI end-to-end smoke (plan → run → judge → analyze → verify) | done — 256 trials / 768 verdicts verified |
| M5 mechanistic layer (directions, steering, transfer, outcome ties) | code done; GPU validation at first AWS cell |
| M6 battery fetch + admission probes (upstream pins) | pending first research run |
| M7 pilot → gates → multi-POV review → preregistration freeze | pending |
| M8 confirmatory + mechanistic cells + paper export | pending |

**Everything above "done" is backed by the test suite and the verified
smoke archive — nothing is claimed from memory.**

## Quick start (CPU, no GPU, no network)

```bash
python -m pip install -e '.[dev,analysis]'
python -m pytest -q                      # full suite
assay doctor                             # registries, verification records
assay run --config configs/smoke.yaml --run-dir runs/smoke   # end-to-end mock run
assay verify --run-dir runs/smoke        # independent integrity audit
assay analyze --run-dir runs/smoke       # report + figures + tables + dossiers
```

## Research questions (pre-freeze draft — see docs/PROTOCOL.md)

- **RQ1:** How much of reported jailbreak susceptibility is the measurement
  instrument? Estimand: per-model spread between refusal-based ASR and
  verified-harm ASR, with behavior-cluster bootstrap CIs.
- **RQ2:** How do static and adaptive attacks perform across the frontier
  matrix under calibrated measurement — and what do they cost per verified
  success?
- **RQ3:** Is refusal mediated by a single direction per layer (Arditi et
  al. 2024) across current open weights, does the direction transfer
  across models, and does its strength predict verified harm?

Nulls and negatives are valid, publishable outcomes; bounded negatives
require TOST, never a nonsignificant superiority test.

## Repository layout

```text
src/assay/
  registry/       models (51, verified), attacks (16, citation-backed),
                  judges (7, frozen prompts), behavior sets (4, upstream)
  behaviors/       battery loading, frozen cluster splits, synthetic smoke set
  attacks/         static templates, adaptive policies, white-box GCG
  targets/         API clients (anthropic/gemini/openai-compat), vLLM server
                  manager, HF hooks, mock providers (smoke-only)
  judges/          classifiers, rubric judges, refusal detection, calibration
  engine/          plan grid, conversation driver, resumable runner
  evidence/        WAL store, hash-chained journal, index, verification audit
  budget/          audited price tables, fail-closed ledger
  analysis/        ASR definitions, cluster bootstrap, TOST, Holm/BH, figures
  mechanistic/     refusal directions, steering, transfer, outcome ties
  export/          SQLite+Parquet catalog, LaTeX/CSV tables, dossiers
  disclosure/      90-day coordinated-disclosure register
docs/              protocol, methodology, citations, runbooks, quality manual
configs/           smoke + main-study templates + serving specs per tier
scripts/aws/       instance lifecycle, admission probe + pinning
tests/             70+ unit/integration/tamper tests
```

## Governance (read before running anything)

- [`docs/PROTOCOL.md`](docs/PROTOCOL.md) — preregistration (freeze before evaluation)
- [`docs/QUALITY.md`](docs/QUALITY.md) — no-fallback, no-hallucination rules
- [`docs/ETHICS.md`](docs/ETHICS.md) + [`SECURITY.md`](SECURITY.md) — scope limits, 90-day disclosure
- [`docs/RUNBOOK_AWS.md`](docs/RUNBOOK_AWS.md) — from zero to verified evidence on AWS
- [`docs/BUDGET.md`](docs/BUDGET.md) — cost model inside a research-credit grant
- [`docs/CITATIONS.md`](docs/CITATIONS.md) — 110+ source-verified references
- [`docs/DEVIATIONS.md`](docs/DEVIATIONS.md) — append-only change log after any freeze

## License

Apache-2.0. All behaviors come from public benchmarks fetched at pinned
revisions (never redistributed here); all attack methods are
citation-grounded; the repo ships zero operational uplift.
