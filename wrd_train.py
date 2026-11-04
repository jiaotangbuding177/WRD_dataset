#!/usr/bin/env python3
"""WRD LoRA SFT training script for DGX Spark (GB10, aarch64).

Implements wrd-sft-plan-v2 (plans/20261025_14b_spark):
  - Qwen3-8B (control) / Qwen3-14B (primary), pinned revisions
  - BF16 LoRA r32 alpha64 dropout0.05, targets q/k/v/o/gate/up/down
  - embedding/lm_head frozen, bias=none
  - LR 1e-4, adamw (0.9/0.999, eps 1e-8, wd 0.01), cosine, warmup 3%
  - micro batch 1 x grad accum 16, seed 42, 1 epoch
  - completion_only_loss, thinking disabled, 16K context
  - SDPA + gradient checkpointing (use_reentrant=False)

Data: training/native_actions_core7.train.jsonl.gz (6774 records).
Rows are chat-format dicts with keys: prompt (list[message]), completion
(list[message]), tools (list[7 function defs]). Serialised to the Qwen chat
template whole-string, tokenized once (no per-segment BPE concatenation).
"""
import argparse
import json
import os
import random
import sys

import torch
from torch.utils.data import Dataset
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    Trainer,
    TrainingArguments,
)
from peft import LoraConfig, get_peft_model

MODELS = {
    "8b": {
        "id": "Qwen/Qwen3-8B",
        "revision": "b968826d9c46dd6066d109eabc6255188de91218",
    },
    "14b": {
        "id": "Qwen/Qwen3-14B",
        "revision": "40c069824f4251a91eefaf281ebe4c544efd3e18",
    },
}


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--model", choices=MODELS.keys(), required=True)
    p.add_argument("--data", required=True)
    p.add_argument("--output-dir", required=True)
    p.add_argument("--max-length", type=int, default=16384)
    p.add_argument("--epochs", type=float, default=1.0)
    p.add_argument("--lr", type=float, default=1e-4)
    p.add_argument("--micro-batch", type=int, default=1)
    p.add_argument("--grad-accum", type=int, default=16)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--max-samples", type=int, default=0,
                   help="0 = all; used for smoke runs")
    p.add_argument("--compile-stats-only", action="store_true",
                   help="tokenize all rows, report token/mask stats, exit")
    return p.parse_args()


def load_rows(path):
    import gzip
    rows = []
    with gzip.open(path, "rt", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def is_precoded(rows):
    """preflight v2 SFT rows carry input_ids + supervision_spans."""
    return bool(rows) and "input_ids" in rows[0]


def rows_from_precoded(rows, max_length):
    """Build examples from official preflight compiled arrays.

    labels = -100 everywhere except supervision_spans (per sft/README.md).
    No re-tokenization, no truncation; only the length gate applies.
    """
    examples = []
    skipped_long = 0
    for r in rows:
        ids = r["input_ids"]
        if len(ids) > max_length:
            skipped_long += 1
            continue
        labels = [-100] * len(ids)
        for begin, end in r["supervision_spans"]:
            labels[begin:end] = ids[begin:end]
        if all(l == -100 for l in labels):
            skipped_long += 1  # count as unusable; separate counter not needed
            continue
        examples.append({
            "input_ids": ids,
            "labels": labels,
            "attention_mask": [1] * len(ids),
        })
    ds = WrdsftDataset.__new__(WrdsftDataset)
    ds.examples = examples
    ds.skipped_long = skipped_long
    ds.skipped_empty = 0
    return ds


class WrdsftDataset(Dataset):
    """Whole-string serialization via the model's chat template.

    Per plan section 5: tokenize the full serialized prompt+completion in one
    pass; supervise only the completion (+ template-mandated EOS), everything
    else -100. Thinking disabled.
    """

    def __init__(self, rows, tokenizer, max_length):
        self.examples = []
        skipped_long = 0
        skipped_empty = 0
        for r in rows:
            prompt_msgs = r["prompt"]
            completion_msgs = r["completion"]
            tools = r.get("tools") or None

            prompt_text = tokenizer.apply_chat_template(
                prompt_msgs,
                tools=tools,
                tokenize=False,
                add_generation_prompt=True,
                enable_thinking=False,
            )
            full_text = tokenizer.apply_chat_template(
                prompt_msgs + completion_msgs,
                tools=tools,
                tokenize=False,
                add_generation_prompt=False,
                enable_thinking=False,
            )
            # completion must be a contiguous suffix of full serialization
            if not full_text.startswith(prompt_text):
                skipped_empty += 1
                continue
            prompt_ids = tokenizer(prompt_text, add_special_tokens=False)["input_ids"]
            full_ids = tokenizer(full_text, add_special_tokens=False)["input_ids"]
            # suffix consistency at token level
            plen = len(prompt_ids)
            if full_ids[:plen] != prompt_ids:
                skipped_empty += 1
                continue
            if len(full_ids) > max_length:
                skipped_long += 1
                continue
            if plen >= len(full_ids):
                skipped_empty += 1
                continue

            labels = [-100] * plen + full_ids[plen:]
            # ensure EOS supervision if template didn't already end with one
            if labels[-1] != tokenizer.eos_token_id:
                full_ids = full_ids + [tokenizer.eos_token_id]
                labels = labels + [tokenizer.eos_token_id]
                if len(full_ids) > max_length:
                    skipped_long += 1
                    continue
            if all(l == -100 for l in labels):
                skipped_empty += 1
                continue

            self.examples.append({
                "input_ids": full_ids,
                "labels": labels,
                "attention_mask": [1] * len(full_ids),
            })
        self.skipped_long = skipped_long
        self.skipped_empty = skipped_empty

    def __len__(self):
        return len(self.examples)

    def __getitem__(self, idx):
        return self.examples[idx]


class Collator:
    def __call__(self, batch):
        # micro batch = 1 per plan; still handle n>1 with right-padding
        maxlen = max(len(b["input_ids"]) for b in batch)
        pad_id = self.pad_token_id
        input_ids, labels, attn = [], [], []
        for b in batch:
            n = len(b["input_ids"])
            pad = maxlen - n
            input_ids.append(b["input_ids"] + [pad_id] * pad)
            labels.append(b["labels"] + [-100] * pad)
            attn.append(b["attention_mask"] + [0] * pad)
        return {
            "input_ids": torch.tensor(input_ids, dtype=torch.long),
            "labels": torch.tensor(labels, dtype=torch.long),
            "attention_mask": torch.tensor(attn, dtype=torch.long),
        }


def main():
    args = parse_args()
    model_spec = MODELS[args.model]
    random.seed(args.seed)

    tokenizer = AutoTokenizer.from_pretrained(
        model_spec["id"], revision=model_spec["revision"]
    )

    rows = []
    for path in args.data.split(","):
        path = path.strip()
        part = load_rows(path)
        print(f"[data] {path}: {len(part)} rows", flush=True)
        rows.extend(part)
    if args.max_samples:
        rows = rows[: args.max_samples]
    print(f"[data] loaded {len(rows)} rows total", flush=True)

    if is_precoded(rows):
        ds = rows_from_precoded(rows, args.max_length)
        print("[data] using official preflight compiled arrays "
              "(input_ids + supervision_spans, no re-tokenization)", flush=True)
    else:
        ds = WrdsftDataset(rows, tokenizer, args.max_length)
    n = len(ds)
    print(f"[data] compiled examples: {n}, skipped_long: {ds.skipped_long}, "
          f"skipped_empty: {ds.skipped_empty}", flush=True)
    if n == 0:
        print("[data] no usable examples, aborting", flush=True)
        sys.exit(1)

    # token stats over supervised rows
    total_tokens = sum(len(e["input_ids"]) for e in ds.examples)
    sup_tokens = sum(sum(1 for l in e["labels"] if l != -100) for e in ds.examples)
    print(f"[stats] total_tokens={total_tokens} supervised_tokens={sup_tokens} "
          f"mean_len={total_tokens/max(n,1):.0f}", flush=True)
    if args.compile_stats_only:
        # length histogram buckets per plan P1
        buckets = [4096, 8192, 16384, 32768]
        hist = {b: sum(1 for e in ds.examples if len(e["input_ids"]) <= b) for b in buckets}
        print(f"[stats] coverage buckets: {hist}", flush=True)
        return

    Collator.pad_token_id = tokenizer.pad_token_id or tokenizer.eos_token_id

    model = AutoModelForCausalLM.from_pretrained(
        model_spec["id"],
        revision=model_spec["revision"],
        dtype=torch.bfloat16,
        attn_implementation="sdpa",
    )
    model.config.use_cache = False

    lora = LoraConfig(
        task_type="CAUSAL_LM",
        r=32,
        lora_alpha=64,
        lora_dropout=0.05,
        bias="none",
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                        "gate_proj", "up_proj", "down_proj"],
    )
    model = get_peft_model(model, lora)
    model.print_trainable_parameters()

    targs = TrainingArguments(
        output_dir=args.output_dir,
        num_train_epochs=args.epochs,
        per_device_train_batch_size=args.micro_batch,
        gradient_accumulation_steps=args.grad_accum,
        learning_rate=args.lr,
        lr_scheduler_type="cosine",
        warmup_ratio=0.03,
        weight_decay=0.01,
        adam_beta1=0.9,
        adam_beta2=0.999,
        adam_epsilon=1e-8,
        max_grad_norm=1.0,
        bf16=True,
        gradient_checkpointing=True,
        gradient_checkpointing_kwargs={"use_reentrant": False},
        optim="adamw_torch",
        logging_steps=5,
        save_steps=max(1, int((n / args.grad_accum) * 0.25)),
        save_total_limit=3,
        seed=args.seed,
        dataloader_num_workers=2,
        report_to=[],
        remove_unused_columns=False,
    )

    trainer = Trainer(
        model=model,
        args=targs,
        train_dataset=ds,
        data_collator=Collator(),
    )
    trainer.train()
    trainer.save_model(os.path.join(args.output_dir, "final_adapter"))
    tokenizer.save_pretrained(os.path.join(args.output_dir, "final_adapter"))
    print("[done] training complete", flush=True)


if __name__ == "__main__":
    main()
