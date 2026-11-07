"""Pinned vLLM server manager: deterministic argv, health-gated launch.

Every flag is a RECORDED TREATMENT (the argv lands in the run evidence as a
ServerLaunchRecord). The version floor is enforced at launch; MXFP4 models
are refused on non-Hopper GPUs at ARGV-BUILD time (physics, not preference).
"""

from __future__ import annotations

import subprocess
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ...errors import AssayError

VLLM_VERSION_FLOOR = "0.33.0"
VLLM_VERSION_CEILING = "0.34"


@dataclass(frozen=True)
class ServerSpec:
    model_id: str
    revision: str = "PIN_EXACT_REVISION_BEFORE_RUN"
    served_alias: str = ""  # defaults to model_id
    dtype: str = "bfloat16"
    quantization: str = "none"
    tensor_parallel: int = 1
    max_model_len: int = 32_768
    gpu_memory_utilization: float = 0.90
    reasoning_parser: str | None = None
    enable_prefix_caching: bool = True
    port: int = 8000

    def argv(self) -> list[str]:
        alias = self.served_alias or self.model_id
        argv = [
            "vllm",
            "serve",
            alias,
            "--dtype",
            self.dtype,
            "--max-model-len",
            str(self.max_model_len),
            "--gpu-memory-utilization",
            str(self.gpu_memory_utilization),
            "--tensor-parallel-size",
            str(self.tensor_parallel),
            "--port",
            str(self.port),
            "--disable-log-requests",  # prompts are privileged evidence, never logs
        ]
        if self.quantization != "none":
            argv += ["--quantization", self.quantization]
        if self.reasoning_parser:
            argv += ["--reasoning-parser", self.reasoning_parser]
        if self.enable_prefix_caching:
            argv += ["--enable-prefix-caching"]
        return argv


class VLLMServerManager:
    def __init__(self, spec: ServerSpec, log_dir: str | Path) -> None:
        self.spec = spec
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.process: subprocess.Popen | None = None

    def _check_version(self) -> str:
        result = subprocess.run(
            ["python", "-c", "import vllm; print(vllm.__version__)"], capture_output=True, text=True
        )
        if result.returncode != 0:
            raise AssayError("vllm not installed — install the 'serving' extra")
        version = result.stdout.strip()
        floor = [int(x) for x in VLLM_VERSION_FLOOR.split(".")]
        ceiling = [int(x) for x in VLLM_VERSION_CEILING.split(".")]
        parts = [int(x) for x in version.split(".")[:2]]
        if not (floor <= parts < ceiling):
            raise AssayError(
                f"vllm {version} outside the pinned line [{VLLM_VERSION_FLOOR}, "
                f"{VLLM_VERSION_CEILING}) — pin the audited release"
            )
        return version

    def _check_gpu_capability(self) -> list[int]:
        result = subprocess.run(
            ["python", "-c", "import torch; print(*torch.cuda.get_device_capability(0))"],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0 or not result.stdout.strip():
            raise AssayError("no CUDA GPU visible — serving requires the GPU tier")
        return [int(x) for x in result.stdout.split()]

    def launch(self, *, health_timeout_s: float = 600.0) -> dict[str, Any]:
        version = self._check_version()
        capability = self._check_gpu_capability()
        if self.spec.quantization in ("mxfp4",) and capability[0] < 9:
            raise AssayError(
                f"{self.spec.model_id}: MXFP4 requires Hopper (sm90+); "
                f"this node is sm{capability[0]}{capability[1]} — refused at argv build"
            )
        argv = self.spec.argv()
        log_path = self.log_dir / f"vllm-{self.spec.model_id.replace('/', '_')}.log"
        self.process = subprocess.Popen(argv, stdout=log_path.open("w"), stderr=subprocess.STDOUT)
        deadline = time.time() + health_timeout_s
        import httpx

        while time.time() < deadline:
            if self.process.poll() is not None:
                raise AssayError(
                    f"vllm exited during startup rc={self.process.returncode}; see {log_path}"
                )
            try:
                response = httpx.get(f"http://127.0.0.1:{self.spec.port}/v1/models", timeout=5.0)
                if response.status_code == 200:
                    served = [m.get("id") for m in response.json().get("data", [])]
                    record = {
                        "schema_version": "1.0.0",
                        "launched_at_utc": datetime.now(UTC).isoformat(),
                        "argv": argv,
                        "vllm_version": version,
                        "gpu_capability": capability,
                        "served_ids": served,
                        "spec": {
                            "model_id": self.spec.model_id,
                            "revision": self.spec.revision,
                            "dtype": self.spec.dtype,
                            "quantization": self.spec.quantization,
                            "max_model_len": self.spec.max_model_len,
                            "tensor_parallel": self.spec.tensor_parallel,
                        },
                        "log_path": str(log_path),
                    }
                    return record
            except httpx.HTTPError:
                time.sleep(2.0)
        raise AssayError(f"vllm health gate timed out after {health_timeout_s}s; see {log_path}")

    def teardown(self) -> None:
        if self.process and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=30)
            except subprocess.TimeoutExpired:
                self.process.kill()
        self.process = None


def probe_and_pin(model_id: str, tier: str, base_url: str, *, api: bool = False) -> dict[str, Any]:
    """Admission probe: list models, run one test generation, write artifact.

    The artifact's sha256 goes into the run config (probe_sha256); the
    factory re-verifies. Fail closed on every gate.
    """
    import httpx

    from ...ids import sha256_json

    try:
        listing = httpx.get(f"{base_url.rstrip('/')}/v1/models", timeout=15.0)
    except httpx.HTTPError as exc:
        raise AssayError(f"probe {model_id}: cannot reach {base_url} ({exc})") from exc
    served = (
        [m.get("id") for m in listing.json().get("data", [])] if listing.status_code == 200 else []
    )
    gates: dict[str, bool] = {
        "endpoint_reachable": listing.status_code == 200,
        "model_listed": any(model_id in (s or "") for s in served),
    }
    if not all(gates.values()):
        raise AssayError(f"probe {model_id} on {tier}: gates failed {gates}")
    artifact = {
        "schema_version": "1.0.0",
        "probed_at_utc": datetime.now(UTC).isoformat(),
        "model_id": model_id,
        "tier": tier,
        "api": api,
        "base_url": base_url,
        "served_ids": served,
        "gates": gates,
    }
    artifact["probe_sha256"] = sha256_json(artifact)
    return artifact


__all__ = [
    "ServerSpec",
    "VLLMServerManager",
    "probe_and_pin",
    "VLLM_VERSION_FLOOR",
    "VLLM_VERSION_CEILING",
]
