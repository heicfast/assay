# AWS setup and operations guide

From zero to verified evidence on AWS GPU instances, for the ASSAY
research program. Budget discipline is part of the protocol: every run
carries a fail-closed cost ledger and a hard cap.

**Cost basis (verified 2026-11-06, us-east-1):**

| Instance | GPUs | On-demand | Fits (registry tier notes) |
|---|---|---|---|
| `p4de.24xlarge` | 8x A100-80GB | $27.447/hr | Qwen3.5 35B/27B bf16 · GLM-4.7-Flash · DeepSeek-V4-Flash (probe) · Llama-4-Scout bf16 tp=8 · gemma-4-12B · Mistral-Small-3.1 · classifier judges |
| `p5.48xlarge` | 8x H100-80GB | region-priced — verify at launch, never invent | gpt-oss (MXFP4, Hopper+ only) · FP8 arms · DeepSeek-family deep-kernel paths (DeepGEMM/FlashMLA) |

A $3,500 credit ≈ 127 p4de on-demand hours. Credits burn while instances
EXIST, not while they compute — terminate when idle.

## 1. Account, credits, IAM

1. Apply to *AWS Cloud Credit for Research* (student awards up to $5,000 —
   verified: https://aws.amazon.com/government-education/research-and-technical-computing/cloud-credit-for-research).
2. IAM least privilege: dedicated user; `ec2:*` scoped by the
   `project=assay` tag; S3 put/get/list on your evidence bucket;
   CloudWatch read; billing alarms. Never root. Keys in env/`~/.aws` only —
   never in the repository.
3. Billing alarms at 80% and 100% of the grant (belt and braces beyond the
   ledger).

## 2. Instance lifecycle

```bash
bash scripts/aws/launch_instance.sh p4de.24xlarge my-key        # or: spot
ssh -A ubuntu@<public-dns>
```

## 3. Software stack on the instance

```bash
sudo apt-get update && sudo apt-get install -y git python3.11 python3-pip
git clone https://github.com/heicfast/assay.git && cd assay
python -m pip install -e '.[research,analysis,serving,mech,aws,dev]'
python -m pytest -q          # the CPU suite MUST pass HERE before any GPU hour
assay doctor
```

Rules that travel with you: the CPU suite must pass on the instance before
any GPU hour is spent; the vLLM version floor (>=0.33,<0.34) is enforced by
the server manager; the battery must be fetched and pinned
(`assay behaviors fetch`).

Export access once: `export HF_TOKEN=…` (gated weights — never committed).

## 4. Serving a model (pinned, recorded)

```bash
# inspect the deterministic argv first — it IS the treatment
python - <<'EOF'
from assay.targets.local.vllm_server import ServerSpec
import yaml
spec_data = yaml.safe_load(open("configs/serving/qwen3_5_35b_a100.yaml"))
spec_data["revision"] = "<pin-exact-revision>"
spec = ServerSpec(**{k: v for k, v in spec_data.items() if k in ServerSpec.__dataclass_fields__})
print(spec.argv())
EOF
```

Launch through the manager (health-gated; launch record lands as evidence)
or manually with the printed argv + `--disable-log-requests`.

## 5. Admission probe (fail-closed, per model per tier)

```bash
python scripts/aws/probe_and_pin.py --model Qwen/Qwen3.5-35B-A3B \
    --tier aws_a100_80gb --base-url http://127.0.0.1:8000/v1 --test-generation
```

Gates: endpoint reachable; served id listed; test generation with usage
fields. Copy the emitted `probe_sha256` into the run config. Candidates
(e.g. ShieldGemma, WildGuard, HarmBench classifier) are promoted to
verified ONLY by their probe.

## 6. Running the study end-to-end

```bash
assay behaviors fetch                      # pin upstream batteries + licenses
cp configs/main_study.template.yaml configs/main_v1.yaml
# fill: revisions, probe_sha256, served ids (PIN_EXACT_* refuse at pilot+)
assay budget-sim --config configs/main_v1.yaml   # estimate BEFORE spending
assay run --config configs/main_v1.yaml --run-dir runs/main_v1
# spot interruptions: rerun the same command; committed trials are skipped
assay verify --run-dir runs/main_v1
assay calibrate --run-dir runs/main_v1     # after the labeling workflow
assay analyze --run-dir runs/main_v1
assay export --run-dir runs/main_v1
```

## 7. Mechanistic cells (open weights)

```bash
python - <<'EOF'
from assay.mechanistic.hooks import LoadedHFModel, extract_refusal_directions
model = LoadedHFModel("Qwen/Qwen3.5-35B-A3B", revision="<pinned>")
directions = extract_refusal_directions(
    model, harmful_prompts=[...battery prompts...],
    benign_prompts=[...benign battery prompts...])
EOF
```

Layer reports, cross-model transfer, and outcome ties:
`assay.mechanistic.analysis`. Steering runs through `SteeringPatchedModel`
(±α at the frozen best layer; sign convention frozen on validation).

## 8. Evidence durability (S3)

Sync after every landed stage; digest-verified upload with SHA-256 object
metadata (mirror the predecessor program's `sync-evidence` pattern; a
`sync_manifest.json` anchors the run's config hash).

## 9. Teardown (never skip)

```bash
bash scripts/aws/teardown.sh <instance-id>
```

Verify in the console that nothing is running before closing the laptop.

## 10. Troubleshooting

| Symptom | First check |
|---|---|
| vLLM exits during startup | server log — usually max_model_len × batch exceeds KV; lower `max_num_seqs` (a NEW spec hash = recorded treatment change) |
| gpt-oss launch refused | Correct: MXFP4 needs Hopper+; the argv builder refuses it on Ampere |
| Admission probe fails | The gates are the point — fix the cause (wrong served id, stale spec, wrong tier); never bypass |
| BudgetExceededError mid-run | Intended fail-closed behavior; raise the cap only as a deliberate, recorded decision |
| Judge classifier format drift | probe validates card-conformance; a drifted format is a blocked judge, never a silent mangle |
