"""Admission probe + served-id pinning (fail closed on every gate).

Usage:
    python scripts/aws/probe_and_pin.py --model Qwen/Qwen3.5-9B \\
        --tier aws_a100_80gb --base-url http://127.0.0.1:8000/v1 [--api]

Writes artifacts/probe-<model>.json; copy its probe_sha256 into the run
config (``probe_sha256``). The provider factory re-verifies the binding.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from assay.errors import AssayError  # noqa: E402
from assay.targets.local.vllm_server import probe_and_pin  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True)
    parser.add_argument("--tier", default="aws_a100_80gb")
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--api", action="store_true")
    parser.add_argument(
        "--test-generation",
        action="store_true",
        help="also run one live generation and verify usage fields",
    )
    args = parser.parse_args()
    try:
        artifact = probe_and_pin(args.model, args.tier, args.base_url, api=args.api)
    except AssayError as exc:
        print(f"PROBE FAILED (this is the point — do not bypass): {exc.message}", file=sys.stderr)
        return 2
    if args.test_generation:
        import httpx

        response = httpx.post(
            f"{args.base_url.rstrip('/')}/chat/completions",
            json={
                "model": args.model,
                "messages": [{"role": "user", "content": "ping"}],
                "max_tokens": 8,
            },
            timeout=60.0,
        )
        usage = response.json().get("usage") or {}
        artifact["test_generation"] = {
            "status_code": response.status_code,
            "prompt_tokens": usage.get("prompt_tokens"),
            "completion_tokens": usage.get("completion_tokens"),
        }
        if response.status_code != 200 or not usage.get("completion_tokens"):
            print("PROBE FAILED: test generation gate", file=sys.stderr)
            return 2
    out = Path("artifacts") / f"probe-{args.model.replace('/', '_')}.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(artifact, indent=2, sort_keys=True), encoding="utf-8")
    print(f"probe OK: {args.model} on {args.tier}")
    print(f"artifact: {out} (probe_sha256 {artifact['probe_sha256']})")
    print("bind it in the run config: probe_sha256: " + artifact["probe_sha256"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
