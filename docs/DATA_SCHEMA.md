# Raw evidence and independent verification specification

Version 1.0.0.

## Run directory layout

```text
runs/<run_id>/
  run_manifest.json        run_id, stage, config_sha256, config_path,
                           code_revision, plan hashes, battery hash, created_at
  plan/plan_manifest.json  frozen grid + census (every skip reason counted)
  battery/battery_manifest.json
                           fetch records (upstream repo, revision, license,
                           file sha256) + frozen split manifest + counts
  environment.json         secret-free runtime snapshot (presence booleans
                           only — never values)
  trials/                  public envelopes (one JSONL line per trial)
  privileged/              full per-turn inference audits (prompts, messages,
                           params, token usage, runtime, hashes)
  verdicts/                judge verdicts (frozen prompt hashes, rendered
                           prompts, raw responses, envelope fingerprints)
  labels/                  human label sheets + imported labels
  transactions/ + commits/ write-ahead transactions + commit markers
  costs/                   NDJSON cost ledger + summary.json
  reports/ figures/ tables/  analysis_report.json (+sha), dossiers,
                           provenance-stamped figures (+ .plotdata.json),
                           LaTeX/CSV tables, catalog
  artifacts/               checksums.sha256, evidence_index.json
  journal.jsonl            hash-chained event journal
```

## Evidence levels

| Level | Contents | Release policy |
|---|---|---|
| Public envelope | axes, messages, final reply, reasoning split, token usage, timings | release after verification |
| Privileged record | full prompt/message/param/token-id audits with per-field SHA-256 | controlled research artifact; never sent to judges or models |
| Judge verdict | frozen prompt hash, rendered prompt, raw response, parsed value | public (its view passed the leakage firewall) |
| Human labels | severity/harm/refusal per labeler | controlled (people, not artifacts) |
| Runtime | environment snapshot (presence booleans only) | public |
| Integrity | checksums + evidence index (reverse enumeration) | public |

## Per-generation requirements

Every `ModelTurn.audit_payload()` retains: raw output + hash; reasoning
split + parse status + hash; rendered prompt + hash; input messages +
hash; generation parameters; token usage; stop reason; elapsed; model /
served id / revision / determinism class; runtime metadata. No field is
character-capped. The reasoning channel never leaks into the answer
channel (anti-leak contract, regression-tested).

## Verification procedure (`assay verify` — read-only)

1. Manifest present; run frozen to one config hash + one plan hash.
2. Trial ids unique + opaque (label-word prefixes rejected by name).
3. Transaction/commit hash chain re-derived; envelope + privileged digests
   recomputed; malformed shards recorded as problems (never crashed on).
4. Verdicts: id derivation re-checked; `prompt_hash` bound to the frozen
   judge constants; rendered-prompt hash re-derived; envelope fingerprint
   re-bound to the trial.
5. Checksum ledger + evidence index rebuilt and compared (reverse
   enumeration: every real file must be covered; symlinks are problems).
6. Budget ledger replayed from its NDJSON.

A run that fails verification cannot be presented as research evidence.

## Browsing surface (for analysis and paper writing)

- `assay export` builds a SQLite catalog (`trials`, `verdicts`,
  `privileged_index`, views `v_harm_trials`, `v_benign_trials`,
  `v_verdict_matrix`) + Parquet partitions.
- `assay analyze` regenerates: analysis_report.json (+ `report_sha256`),
  provenance-stamped figures (+ plot data), LaTeX/CSV tables, per-model
  dossiers. Deterministic from committed bytes; formatting-only.
