# QUALITY MANUAL — ASSAY

Version 1.0. Enforceable from the first commit. Every agent (human or
automated) executing ASSAY work is bound by this manual. Violations are
recorded in docs/DEVIATIONS.md and block gate progression.

## 1. No-fallback policy

**Definition:** a fallback is any silent substitution of a weaker method,
cheaper model, looser check, or fabricated value when the intended method
fails.

| ID | Rule | Enforcement |
|---|---|---|
| NF-1 | A failed trial is recorded as `runtime_error`. NEVER retried with a different model, temperature, or prompt to "make it work" within the same stage. | engine failure classification; censor accounting in reports |
| NF-2 | Mock/synthetic providers are admissible ONLY in smoke stages and tests. Research stages refuse them at the factory. | `build_target`/`build_attacker` mock branch |
| NF-3 | An invalid judge verdict is recorded as invalid with its raw reason. Never imputed, averaged over, or retried silently. | `parse_status` on every verdict |
| NF-4 | Missing dependencies stop the run with an explicit error. No silent CPU substitution for a GPU result. | provider constructors raise; mech layer fails closed |
| NF-5 | Missing batteries fail closed (`assay behaviors fetch` first); battery content is never fabricated. | loader RegistryError |
| NF-6 | A threshold/calibration that cannot be computed is reported uncomputable with the reason — never quietly switched to an easier quantity. | `calibrated_threshold` returns None; CI eligibility gates |
| NF-7 | Exceptions are never swallowed without a record. Every `except` either re-raises, records a typed error, or appends to a censor/problem log. | code review + verification audit |

## 2. No-hallucination policy

**Definition:** a hallucination is any claim, number, or artifact presented
as evidence that is not derived from recorded, hash-linked artifacts — or
any infrastructure fact stated without a verification record.

| ID | Rule | Enforcement |
|---|---|---|
| NH-1 | No number in any report unless computable from stored records by committed code. | analysis reads only run stores; report sha256 |
| NH-2 | Every model/attack/judge/battery fact carries a Verification record (verified or candidate). Candidates fail closed until a probe promotes them. | registry; doctor; probe artifacts |
| NH-3 | Prices carry source URL + date; unverifiable prices are excluded (never invented). | PriceTable from registry; COMPUTE_PRICES |
| NH-4 | Judge prompts are frozen constants; their hashes are registered before first research use and verified per record. | FROZEN_PROMPT_HASHES; verification audit |
| NH-5 | Documentation must not describe features as working that fail tests; status tables reflect actual gate states. | README status table tracks the suite |
| NH-6 | External claims cite primary sources; nothing is cited from memory. | docs/CITATIONS.md (110+ entries, all keyed) |
| NH-7 | An agent that cannot verify a fact either verifies it or marks it UNVERIFIED. | review process |
| NH-8 | Tooling display layers may rewrite bracket-like text: no verification may rely on visual inspection of bracketed content — every check is a programmatic assertion; tag-like literals are built from `chr()` and byte-exactness is tested. | think-tag constants; tests |

## 3. Verification cadence

**Per change (every commit):** `pytest -q` green; `ruff check src tests
scripts` clean; `mypy src/assay` clean; `assay doctor` OK.

**Per run:** `assay verify --run-dir <run>` — the independent audit
(hash chains, verdict bindings, checksums, index, reverse enumeration).

**Per gate (pilot → confirmatory → freeze):** multi-POV review per
docs/REVIEW_SYSTEM.md with recorded verdicts.

**Per figure:** provenance stamp (run id, config hash, data digest) +
`.plotdata.json` next to every PNG.

## 4. Evidence and provenance rules

- Opaque identifiers only (label words rejected by name in the audit).
- Judge views are allowlist-compiled and leakage-asserted.
- Run directories are frozen to one config hash + one plan hash; drift
  aborts execution.
- Storage is append-only, atomic (temp→fsync→rename), and resumable
  without duplicates (commit ledger).
- Every run ships: run manifest, plan manifest (with census), battery
  manifest (fetch records + splits), environment snapshot, trial shards,
  privileged shards, verdict shards, costs, checksums, evidence index,
  journal.

## 5. Statistical integrity

- One predeclared confirmatory family; Holm across it; BH only for
  predeclared exploratory families, labeled as such.
- Cluster inference at the behavior-cluster level; no pseudo-replication.
- CIs carry eligibility gates; `not_estimable` is a result.
- Bounded negatives require TOST; nonsignificance licenses nothing.
- All exclusions and failures appear in censor accounting with counts.

## 6. Failure handling ladder

1. **Stop** on contradiction of this manual.
2. **Record** in docs/DEVIATIONS.md (append-only) if it touches anything
   frozen.
3. **Repair the methodology** (new battery version + new preregistration
   if needed) — never the data.
4. **Re-run** the verification cadence from step 1 of §3.
