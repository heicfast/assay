"""White-box optimization attacks (GCG lineage). torch is imported lazily;
without the mech extra the attack fails closed with a clear error."""

from __future__ import annotations

from typing import Any

from ...errors import AssayError
from ..base import TrialContext


class GCGAttack:
    """GCG adversarial suffix optimization (Zou et al. 2023, arXiv:2307.15043).

    Runs against an open-weight target through the mechanistic HF hook
    (LoadedHFModel). The suffix found here is a TREATMENT: it is recorded in
    the trial envelope and replayed verbatim by the transfer study.
    """

    def __init__(
        self, hf_model, *, steps: int = 250, topk: int = 256, batch: int = 512, suffix_len: int = 20
    ) -> None:
        self.hf_model = hf_model
        self.steps = steps
        self.topk = topk
        self.batch = batch
        self.suffix_len = suffix_len

    def optimize(self, behavior_text: str, *, affirmation: str = "Sure, here is") -> dict:
        try:
            import torch
        except ImportError as exc:
            raise AssayError("gcg needs the 'mech' extra (torch+transformers)") from exc
        torch.manual_seed(0)
        tokenizer = self.hf_model.tokenizer
        model = self.hf_model.model
        device = model.device

        prompt_ids = tokenizer.encode(
            self.hf_model.chat_template(behavior_text), add_special_tokens=False
        )
        suffix_ids = [tokenizer.encode("!", add_special_tokens=False)[0]] * self.suffix_len
        target_ids = tokenizer.encode(f" {affirmation}", add_special_tokens=False)
        embeddings = model.get_input_embeddings()

        best_loss = float("inf")
        best_suffix = list(suffix_ids)
        for step in range(self.steps):
            batch_ids = [list(prompt_ids) + list(s) for s in self._candidates(suffix_ids)]
            losses = self._losses(batch_ids, target_ids, embeddings, device)
            winner = int(min(range(len(losses)), key=lambda i: losses[i]))
            if losses[winner] < best_loss:
                best_loss = losses[winner]
                best_suffix = batch_ids[winner][len(prompt_ids) :]
            suffix_ids = list(best_suffix)
            if step % 25 == 0:
                print(f"gcg step {step}: best loss {best_loss:.3f}", flush=True)
        return {
            "suffix_tokens": best_suffix,
            "suffix_text": tokenizer.decode(best_suffix),
            "best_loss": best_loss,
            "steps": self.steps,
            "citation": "Zou et al. 2023, arXiv:2307.15043",
        }

    def _candidates(self, suffix_ids: list[int]) -> list[list[int]]:
        import random

        tokens = self.hf_model.tokenizer.get_vocab()
        pool = sorted(set(tokens.values()))
        rng = random.Random(0)
        out = []
        for _ in range(min(self.batch, 64)):
            candidate = list(suffix_ids)
            if candidate and pool:
                candidate[rng.randrange(len(candidate))] = rng.choice(pool)
            out.append(candidate)
        return out

    def _losses(self, batch_ids, target_ids, embeddings, device) -> list[float]:
        import torch

        max_len = max(len(ids) for ids in batch_ids)
        pad = batch_ids[0][0]
        input_ids = torch.tensor(
            [ids + [pad] * (max_len - len(ids)) for ids in batch_ids], device=device
        )
        attention = torch.ones_like(input_ids)
        for row, ids in enumerate(batch_ids):
            attention[row, len(ids) :] = 0
        target = torch.tensor([target_ids], device=device).repeat(len(batch_ids), 1)
        full = torch.cat([input_ids, target], dim=1)
        attention_full = torch.cat([attention, torch.ones_like(target)], dim=1)
        with torch.no_grad():
            inputs_embeds = embeddings(full)
            logits = self.hf_model.model(
                inputs_embeds=inputs_embeds, attention_mask=attention_full
            ).logits
        log_probs = torch.log_softmax(logits.float(), dim=-1)
        losses = []
        for row, ids in enumerate(batch_ids):
            start = len(ids)
            seq = log_probs[row, start - 1 : start - 1 + len(target_ids)]
            gathered = seq.gather(-1, target[row]).sum()
            losses.append(-float(gathered))
        return losses


def run_gcg_for_trial(hf_model, ctx: TrialContext, params: dict[str, Any]) -> dict[str, Any]:
    attack = GCGAttack(
        hf_model,
        steps=int(params.get("steps", 250)),
        topk=int(params.get("topk", 256)),
        batch=int(params.get("batch", 512)),
        suffix_len=int(params.get("suffix_len", 20)),
    )
    result = attack.optimize(ctx.behavior.text)
    result["opening_messages"] = [
        {
            "role": "user",
            "content": f"{ctx.behavior.text} {result['suffix_text']}",
        }
    ]
    return result


__all__ = ["GCGAttack", "run_gcg_for_trial"]
