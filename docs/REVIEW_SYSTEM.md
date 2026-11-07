# REVIEW_SYSTEM — Multi-point-of-view independent review

ASSAY enforces independent reviews at every gate (pilot → confirmatory →
freeze → publication). Reviews run independently, are recorded verbatim,
and their verdicts gate progression.

## Reviewer roles and mandates

Each reviewer answers ONLY from their mandate; they are instructed to find
problems, not praise. Findings are classified:

- **BLOCKER** — must be fixed before the gate passes.
- **MAJOR** — fixed before the next gate, or accepted with a dated
  rationale in docs/DEVIATIONS.md.
- **MINOR** — recorded; fixed opportunistically.

### R1 — Senior software engineer
Mandate: correctness, determinism, resumability, integrity.
Checklist:
- [ ] Any path where a failure could be silently swallowed?
- [ ] Is every persisted record atomic and crash-safe? Is resumption
      idempotent (no duplicates possible)?
- [ ] Do hashes pin exactly what they claim (config, plan, evidence)?
- [ ] Any nondeterminism that could leak into records (dict ordering,
      salted hashing, wall times)?
- [ ] Typed errors everywhere instead of stringly-typed checks?
- [ ] Would this code survive an instance dying mid-shard?

### R2 — Senior research scientist (measurement)
Mandate: does the design actually answer RQ1–RQ3?
Checklist:
- [ ] Are the three ASR definitions computed from the same frozen
      batteries and judges for every model?
- [ ] Are splits cluster-scoped and frozen before holdout?
- [ ] Is the verified-harm gate validated against human labels?
- [ ] Could a null result be published from this design? If not, the
      design is broken.
- [ ] Is distributional reporting applied everywhere (no single-config
      points)?
- [ ] Do reasoning-channel attacks pair only with reasoning targets (plan
      census accounts for every skip)?

### R3 — Senior security researcher (red-team / leakage adversary)
Mandate: adversarial integrity of the evidence boundary.
Checklist:
- [ ] Can any judge view reveal model identity, split roles, clusters, or
      labels (including via ordering, formatting, ids, lengths)?
- [ ] Can trial ids leak semantics? (opaque-id audit)
- [ ] Could the attacker policy's internal rewards leak the study's judges
      into the attack optimization?
- [ ] Does the disclosure register ever carry working payloads? (must be
      hashes only until resolved/expired)
- [ ] Are secrets excluded by construction from every artifact?

### R4 — Statistician
Mandate: estimands, thresholds, uncertainty, multiplicity.
Checklist:
- [ ] Is the cluster bootstrap at the right granularity, with paired
      conditions resampled jointly?
- [ ] Are degenerate replicates handled and reported (never dropped)?
- [ ] Are denominators reported with every rate?
- [ ] Is TOST applied to every bounded-negative claim?
- [ ] Is the confirmatory family predeclared with Holm across it?
- [ ] Do CI eligibility gates fire honestly (`not_estimable` is a result)?

## Process

1. At a gate, open review files `docs/reviews/<gate>_<r1..r4>.md`.
2. Reviewers work INDEPENDENTLY (separate context, no shared notes) against
   the repository state at the gate's commit.
3. Verdict per reviewer: findings list with severity + file/line evidence
   + concrete fix + PASS/FAIL for the gate.
4. Consolidation: BLOCKERs → fix → re-run affected reviews; MAJORs →
   scheduled with owner; MINORs → backlog.
5. The consolidation record is committed with the gate tag.

## Feedback loop

Every BLOCKER becomes a TODO with a regression test where feasible.
Recurring finding classes get a permanent test or check in CI — the
review system is itself iterated on.
