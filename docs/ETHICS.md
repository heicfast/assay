# Ethics and scope limits (hard boundaries)

## What this project is

A measurement-science program for LLM safety evaluation: validated
instruments, literature-grounded attacks on public benchmark behaviors,
mechanistic analysis, preregistered statistics, verifiable evidence.

## What this project is not, and will not ship

1. **No operational uplift.** The repository contains zero working harmful
   content. Behavior text comes exclusively from public benchmarks
   (HarmBench, JailbreakBench, XSTest, MultiJail) fetched at pinned
   revisions — the same materials every red-team framework ships or
   references. The many-shot variant uses BENIGN affirmative
   demonstrations only (a recorded, deliberately weakened treatment).
   Cipher mappings, persuasion frames, and attack policies are methods
   *about* behaviors, not content.
2. **No novel harmful content creation.** Batteries are never
   machine-translated, paraphrased into new harmful variants, or extended
   by the researchers. If an adaptive attacker model produces a genuinely
   novel successful attack pattern, it goes to the 90-day
   coordinated-disclosure register — never straight to the repo.
3. **No deployment claims.** Findings are about measured instruments and
   measured models under a frozen protocol. No product safety claims.
4. **No training against deployed systems.** No attacks are run against
   production services; API targets are used strictly within provider
   terms and rate limits, metered, and capped.

## Human labeling

Labelers are informed contributors (not crowd workers), ≥ 2 per item,
informed consent for handling red-team material, credited in the paper.
Labels are never produced by a model. Agreement is reported (Krippendorff's
α) with every calibration result.

## Disclosure policy (90-day, Project-Zero style)

`assay disclosure register` records a NOVEL finding as a description HASH
only; the full text stays offline. Publication of details requires: the
affected lab is notified, AND (a fix shipped OR the 90-day window expired).
`publish()` refuses otherwise (typed error, fail-closed). The register
never carries working payloads.

## Attribution

This is a from-scratch successor to TRACEGUARD (CoT-monitorability
research). No code or data carries over; the methodological lineage
(preregistration discipline, evidence contracts, verification culture) is
credited in the README and docs.
