# Contributing to ASSAY

## The one rule that implies all the others

**Never present as evidence anything that is not derived from recorded,
hash-linked artifacts — and never silently substitute anything.**
(docs/QUALITY.md is the full manual; it is binding.)

## Workflow

1. Read docs/PROTOCOL.md (what may change when), docs/QUALITY.md (how),
   docs/CITATIONS.md (how to add a fact: with a Verification record).
2. Branch; small commits; every commit keeps the cadence green:
   `pytest -q` · `ruff check src tests scripts` · `mypy src/assay` ·
   `assay doctor`.
3. Anything touching a frozen artifact goes to docs/DEVIATIONS.md FIRST
   (append-only, dated, with rationale and impact).
4. New facts (models, attacks, judges, batteries, prices) REQUIRE a
   verification record — verified (source URL + date) or candidate (fails
   closed until a probe promotes it). No memory citations.
5. Multi-POV review gates for research-affecting changes
   (docs/REVIEW_SYSTEM.md).

## Adding a model

Add a `ModelProfile` to `src/assay/registry/models.py` with a
`Verification` record (verified/candidate), tier physics in notes
(arithmetic, not marketing), and registry roles. The admission probe is
the final authority.

## Adding an attack

Add an `AttackSpec` (citation required) and the implementation class;
register the prompt constants if any; tests for rendering + guards
(reasoning-only, white-box-only, battery pairing rules).

## Adding a judge

Add a `JudgeSpec` + implementation with a FROZEN prompt constant; wire its
hash into `FROZEN_PROMPT_HASHES`; add parsing tests; the panel refuses
unregistered judges.

## Adding a battery

Add a `BehaviorSetSpec` (upstream repo, path hint, license, citation).
Batteries are fetched at pinned revisions, never redistributed in-repo;
the loader fails closed on anything missing.
