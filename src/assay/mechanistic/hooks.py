"""Mechanistic layer: refusal directions, steering, hidden-state hooks (RQ3).

torch/transformers are imported lazily: the CPU core (planning, evidence,
judging orchestration, statistics) never needs them (program rule 4).
Grounding: Arditi et al. 2024 (arXiv:2406.11717, NeurIPS 2024 main) —
diff-in-means direction per layer; steering adds/ablates the direction at
a chosen layer; all runs record full provenance.
"""

from __future__ import annotations

from typing import Any


class MechNotAvailable(RuntimeError):
    """Raised when the mech extra (torch/transformers) is not installed."""


def _torch():
    try:
        import torch
    except ImportError as exc:
        raise MechNotAvailable(
            "the mechanistic layer needs the 'mech' extra "
            "(pip install -e '.[mech]') — never a silent CPU fallback"
        ) from exc
    return torch


def _transformers():
    try:
        import transformers
    except ImportError as exc:
        raise MechNotAvailable("the mechanistic layer needs the 'mech' extra") from exc
    return transformers


class LoadedHFModel:
    """A pinned HF model+tokenizer with hidden-state capture."""

    def __init__(
        self, model_id: str, revision: str, *, device_map: str = "auto", dtype: str = "bfloat16"
    ) -> None:
        torch = _torch()
        transformers = _transformers()
        self.model_id = model_id
        self.revision = revision
        self.tokenizer = transformers.AutoTokenizer.from_pretrained(model_id, revision=revision)
        torch_dtype = {
            "bfloat16": torch.bfloat16,
            "float16": torch.float16,
            "float32": torch.float32,
        }[dtype]
        self.model = transformers.AutoModelForCausalLM.from_pretrained(
            model_id,
            revision=revision,
            torch_dtype=torch_dtype,
            device_map=device_map,
            output_hidden_states=True,
        )
        self.model.eval()
        self.num_layers = self.model.config.num_hidden_layers

    def chat_template(self, prompt: str) -> str:
        return self.tokenizer.apply_chat_template(
            [{"role": "user", "content": prompt}], tokenize=False, add_generation_prompt=True
        )

    def last_token_states(self, prompt: str) -> list[Any]:
        """Per-layer last-token hidden states for one rendered prompt.

        Returns a list of length num_layers+1 (index 0 = embeddings); each
        entry is the hidden state of the FINAL prompt token at that layer.
        """
        torch = _torch()
        rendered = self.chat_template(prompt)
        inputs = self.tokenizer(rendered, return_tensors="pt").to(self.model.device)
        with torch.no_grad():
            outputs = self.model(**inputs, output_hidden_states=True)
        states = []
        for layer_state in outputs.hidden_states[1:]:  # skip embedding layer
            states.append(layer_state[0, -1, :].detach().to("cpu"))
        return states

    def generate(self, prompt: str, *, max_new_tokens: int = 64, temperature: float = 0.0) -> str:
        torch = _torch()
        rendered = self.chat_template(prompt)
        inputs = self.tokenizer(rendered, return_tensors="pt").to(self.model.device)
        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                do_sample=temperature > 0,
                temperature=max(temperature, 1e-4),
                output_hidden_states=False,
                return_dict_in_generate=True,
            )
        generated = outputs.sequences[0][inputs["input_ids"].shape[1] :]
        return self.tokenizer.decode(generated, skip_special_tokens=True)


def extract_refusal_directions(
    model: LoadedHFModel,
    harmful_prompts: list[str],
    benign_prompts: list[str],
) -> dict[str, Any]:
    """Diff-in-means direction per layer (Arditi et al. 2024).

    d_l = mean(state_harmful) - mean(state_benign) at layer l, normalized.
    Also computes held-out projection separation (AUROC of projections onto
    d_l) with a deterministic split (sorted prompts, even/odd).
    """
    torch = _torch()
    if not harmful_prompts or not benign_prompts:
        raise ValueError("need both prompt classes (empty class -> no direction)")
    harmful_states = [model.last_token_states(p) for p in harmful_prompts]
    benign_states = [model.last_token_states(p) for p in benign_prompts]
    layers = model.num_layers
    directions: dict[int, Any] = {}
    separations: dict[int, float] = {}
    half_h = len(harmful_states) // 2 or 1
    half_b = len(benign_states) // 2 or 1
    for layer in range(layers):
        harmful_train = [s[layer] for s in harmful_states[:half_h]]
        benign_train = [s[layer] for s in benign_states[:half_b]]
        mean_diff = torch.stack(harmful_train).mean(0) - torch.stack(benign_train).mean(0)
        norm = mean_diff.norm()
        direction = mean_diff / norm if norm > 0 else mean_diff
        directions[layer + 1] = direction  # 1-indexed layers (skip embeddings)
        harmful_eval = [s[layer] for s in harmful_states[half_h:]] or harmful_train
        benign_eval = [s[layer] for s in benign_states[half_b:]] or benign_train
        projections = [(float(v @ direction), 1) for v in harmful_eval]
        projections += [(float(v @ direction), 0) for v in benign_eval]
        separations[layer + 1] = _rank_auroc(projections)
    return {
        "model_id": model.model_id,
        "revision": model.revision,
        "n_harmful": len(harmful_prompts),
        "n_benign": len(benign_prompts),
        "layer_auroc": separations,
        "directions": directions,
        "method": "diff_in_means_per_layer",
        "citation": "Arditi et al. 2024, arXiv:2406.11717 (NeurIPS 2024)",
    }


def _rank_auroc(projections: list[tuple[float, int]]) -> float:
    """Mann-Whitney AUROC with exact ties."""
    positives = [p for p, label in projections if label == 1]
    negatives = [p for p, label in projections if label == 0]
    if not positives or not negatives:
        return float("nan")
    combined = sorted(projections, key=lambda pair: pair[0])
    ranks: list[float] = []
    i = 0
    while i < len(combined):
        j = i
        while j + 1 < len(combined) and combined[j + 1][0] == combined[i][0]:
            j += 1
        avg = (i + 1 + j + 1) / 2.0
        ranks.extend([avg] * (j - i + 1))
        i = j + 1
    rank_sum_pos = sum(r for (_, label), r in zip(combined, ranks, strict=True) if label == 1)
    u = rank_sum_pos - len(positives) * (len(positives) + 1) / 2.0
    return u / (len(positives) * len(negatives))


class SteeringPatchedModel:
    """Apply +/- alpha * direction at a chosen layer during generation."""

    def __init__(self, model: LoadedHFModel, direction, layer: int, alpha: float) -> None:
        self.model = model
        self.alpha = alpha
        self.layer = layer  # 1-indexed; patch (layer-1) in the decoder stack
        stack = model.model.model.layers  # AutoModelForCausalLM -> decoder layers
        target = stack[layer - 1]
        direction_dev = direction.to(model.model.device, dtype=next(target.parameters()).dtype)

        def hook(_module, args, output):
            hidden = output[0] if isinstance(output, tuple) else output
            hidden = hidden.clone()
            hidden[:, -1, :] = hidden[:, -1, :] + alpha * direction_dev
            if isinstance(output, tuple):
                return (hidden,) + tuple(output[1:])
            return hidden

        self._handle = target.register_forward_hook(hook)

    def remove(self) -> None:
        self._handle.remove()

    def __enter__(self) -> SteeringPatchedModel:
        return self

    def __exit__(self, *exc: Any) -> None:
        self.remove()


def direction_cosine(a, b) -> float:
    torch = _torch()
    a_f = a.to(torch.float32)
    b_f = b.to(torch.float32)
    denom = float(a_f.norm() * b_f.norm())
    if denom == 0:
        return 0.0
    return float((a_f @ b_f) / denom)


__all__ = [
    "LoadedHFModel",
    "extract_refusal_directions",
    "SteeringPatchedModel",
    "direction_cosine",
    "MechNotAvailable",
]
