# Budget model (research-credit scope, ~$3,000–4,000)

Every number below is either verified (source + date in the registry /
price table) or explicitly marked unverified and excluded from planning.
The ledger is fail-closed: crossing `budget.hard_cap_usd` halts the run.

## Verified unit costs

| Line | Unit | Source |
|---|---|---|
| `p4de.24xlarge` (8x A100-80) | $27.447/hr on-demand us-east-1 | vantage + AWS pricing, verified 2026-11-06 |
| API models (haiku/luna/flash-lite class) | $0.10–0.75 in / $0.50–3.75 out per 1M | registry (each entry carries its source) |
| Flagship APIs (fable/terra/argon class) | $1–10 in / $5–50 out per 1M | registry (core grid only — see below) |
| `p5.48xlarge` | region-priced | NOT in the table until verified at launch |

## Grid policy inside the grant

- **Open weights**: full grid — compute is a fixed server cost, so breadth
  is nearly free once the node is up (~10-20 p4de-hours per cell).
- **Cheap/mid APIs**: full grid.
- **Expensive flagships**: predeclared CORE grid (40% behaviors × 60%
  attacks — a recorded treatment, never silently equal to full).
- White-box GCG: separate, small plan on ≤ 4 models (compute-bound).

## Worked scenarios (p4de reference line)

| Scenario | Compute | API | Total | Notes |
|---|---|---|---|---|
| S1 pilot (1 A100 node, 40 hr + cheap/mid APIs core-of-full) | ~$1,100 | ~$300 | ~$1,400 | gates + calibration + review |
| S2 confirmatory + mechanistic (60 hr + flagship core grids) | ~$1,650 | ~$1,200 | ~$2,850 | holdout judged once |
| S3 full program incl. GCG sub-plan (80 hr) | ~$2,200 | ~$1,500 | ~$3,700 | at the top of the grant |

Use `assay budget-sim --config <config>` for the live estimate of the
current grid; OVER BUDGET exits with the gate failure code — shrink the
grid or raise the cap as a recorded decision, never silently.

## Guardrails (all fail-closed)

1. `budget.hard_cap_usd` per run; the ledger raises on crossing.
2. `api_call_cap_per_run` bounds call counts.
3. Compute hours metered into the same ledger as API spend — one
   `costs/summary.json` answers "what did this study cost".
4. Billing alarms at 80% / 100% of the grant (console-level, belt and
   braces beyond the ledger).
5. Terminate idle instances — credits burn while instances exist.
