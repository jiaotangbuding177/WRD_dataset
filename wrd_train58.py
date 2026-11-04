#!/usr/bin/env python3
"""WRD audit58 SFT trainer: course-driven, per-token weighted CE with shared denominator.

Contract (CONFIG58.json + objective_adapter58):
  - Two phases in order: contract (401 exposures, acc<=16, 26 updates), process (859, acc<=4, 215)
  - loss = sum(effective_weight_i * CE_i) / N_step   over ALL microbatches of one optimizer step
    N_step = count of nonignored shifted targets in that whole step; no /accumulation, no /weight-sum
  - effective weights from objective_adapter58.prepare_optimizer_step (applies auxiliary alpha
    to synthetic pool only); adapter validates every step against COURSE58 pins
  - AdamW lr 5e-5 constant_with_warmup(3 global updates), betas (0.9,0.999), eps 1e-8, wd 0.01,
    max_grad_norm 1.0, seed 20261101, microbatch 1, max len 32768, no truncation allowed
  - LoRA r32 alpha64 dropout0.05 on q/k/v/o/gate/up/down; base + embeddings + lm_head frozen
  - checkpoints at global steps 0/26/80/134/188/241 (step 0 = pre-SFT baseline)
Pure manual loop (no Trainer): full control of accumulation and loss scaling.
"""
import argparse
import json
import math
import os
import random
import sys
from fractions import Fraction
from pathlib import Path

import torch
import torch.nn.functional as F


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--model", choices=["14b", "8b"], required=True)
    p.add_argument("--active-root", default="/workspace/active58", help="restored active58 root")
    p.add_argument("--base10-root", default="/workspace/wrd10w")
    p.add_argument("--package11-root", default="/workspace/wrd11")
    p.add_argument("--adapter-path", default="/workspace/tooling/objective_adapter58.py")
    p.add_argument("--output-dir", required=True)
    p.add_argument("--profile", default="budget_projection")
    p.add_argument("--limit-updates", type=int, default=0, help="0 = full 241")
    p.add_argument("--start-step", type=int, default=0,
                   help="resume: skip optimizer steps before this global step")
    p.add_argument("--init-adapter", default="",
                   help="resume: load LoRA weights from this checkpoint dir")
    p.add_argument("--ce-chunk", type=int, default=2048,
                   help="tokens per CE chunk (memory bounding; math unchanged)")
    p.add_argument("--max-length", type=int, default=32768)
    p.add_argument("--save-steps", default="0,26,80,134,188,241")
    p.add_argument("--seed", type=int, default=20261101)
    p.add_argument("--log-every", type=int, default=1)
    p.add_argument("--max-mb-tokens", type=int, default=0,
                   help="debug: skip microbatches longer than this (breaks course contract)")
    return p.parse_args()


MODEL_PATHS = {
    "14b": ("Qwen/Qwen3-14B", "40c069824f4251a91eefaf281ebe4c544efd3e18"),
    "8b": ("Qwen/Qwen3-8B", "b968826d9c46dd6066d109eabc6255188de91218"),
}


def chunked_ce(logits, tgt, chunk):
    """Per-token CE with fp32 log_softmax, chunked along the sequence dimension.

    log_softmax normalizes over vocab per position, so chunking along seq is
    mathematically (and bitwise per row) identical to the full-tensor form:
        ce = gather(log_softmax(logits.float()), tgt)
    Full-tensor fp32 logp at 32K x 152K vocab is ~20GB kept for backward plus
    a ~20GB grad - that alone OOMs GB10 once AdamW moments exist. Each chunk is
    wrapped in checkpoint() so it is recomputed at backward: peak extra memory
    is one chunk (~1.2GB fp32 at chunk=2048) instead of the full matrix.
    """
    from torch.utils.checkpoint import checkpoint as torch_checkpoint
    outs = []
    L = logits.shape[1]
    for s in range(0, L, chunk):
        e = min(s + chunk, L)

        def _ce(lg, tt):
            logp = F.log_softmax(lg.float(), dim=-1)
            return torch.gather(logp, 2, tt.unsqueeze(-1).clamp_min(0)).squeeze(-1)

        outs.append(torch_checkpoint(_ce, logits[:, s:e, :], tgt[:, s:e],
                                     use_reentrant=False))
    return torch.cat(outs, dim=1)


def main():
    args = parse_args()
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    save_steps = {int(x) for x in args.save_steps.split(",")}

    # --- deterministic seeding ---
    random.seed(args.seed)
    import numpy as np
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)
    torch.cuda.manual_seed_all(args.seed)

    # --- load trusted tooling (from restored/pinned copies) ---
    tooling_dir = Path(args.active_root) / "tooling"
    sys.path.insert(0, str(tooling_dir))
    import active_loader57
    import importlib.util
    spec = importlib.util.spec_from_file_location("objective_adapter58", args.adapter_path)
    oa = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(oa)

    course = json.load(open(Path(args.active_root) / "COURSE58.json"))
    profile = course["profiles"][args.profile]
    phases = profile["phases"]

    # --- build global step plan: ordered list of (global_step, step_dict, phase_name) ---
    plan = []
    gstep = 0
    for ph in phases:
        for st in ph["steps"]:
            gstep += 1
            plan.append((gstep, st, ph["name"]))
    total_updates = plan[-1][0]
    if args.limit_updates:
        plan = [x for x in plan if x[0] <= args.limit_updates]
        total_updates = args.limit_updates
    print(f"[plan] {total_updates} optimizer updates; "
          f"microbatches total = {sum(len(s['microbatches']) for _, s, _ in plan)}", flush=True)

    # --- load features for ALL microbatch ids once (1260 rows, ~10.6M tokens budget profile) ---
    # iter_features validates manifest pins, exclusions and TRAIN freeze as it yields.
    need_pools = {"contract_optional", "real_process", "synthetic", "increment_process"}
    print("[data] streaming features via active_loader57 (validates pins)...", flush=True)
    rows_by_id = {}
    for rec in active_loader57.iter_features(
        args.active_root, args.base10_root, args.package11_root,
        profile=args.profile, pools=tuple(sorted(need_pools)), with_metadata=True):
        rows_by_id[rec["id"]] = rec
    print(f"[data] loaded {len(rows_by_id)} unique targets", flush=True)

    # verify every course microbatch id is present
    missing = []
    for _, st, _ in plan:
        for mb in st["microbatches"]:
            if mb["id"] not in rows_by_id:
                missing.append(mb["id"])
    if missing:
        sys.exit(f"FATAL: {len(missing)} course ids missing from loader, e.g. {missing[:3]}")

    # skip-too-long debug mode (contract-breaking, only for memory probes)
    skip_long = {}
    if args.max_mb_tokens:
        for rid, rec in rows_by_id.items():
            n = len(rec["features"]["input_ids"])
            if n > args.max_mb_tokens:
                skip_long[rid] = n
        print(f"[debug] would skip {len(skip_long)} rows > {args.max_mb_tokens} tokens", flush=True)

    # --- model ---
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from peft import LoraConfig, get_peft_model

    model_id, revision = MODEL_PATHS[args.model]
    print(f"[model] loading {model_id} @ {revision}", flush=True)
    model = AutoModelForCausalLM.from_pretrained(
        model_id, revision=revision, torch_dtype=torch.bfloat16,
        attn_implementation="sdpa")
    model.config.use_cache = False
    tokenizer = AutoTokenizer.from_pretrained(model_id, revision=revision)

    lcfg = LoraConfig(
        r=32, lora_alpha=64, lora_dropout=0.05, bias="none",
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                        "gate_proj", "up_proj", "down_proj"],
        task_type="CAUSAL_LM",
    )
    model = get_peft_model(model, lcfg)
    # freeze embeddings + lm_head (already excluded from LoRA targets; also freeze explicitly)
    base = model.get_base_model()
    for name in ["embed_tokens", "lm_head"]:
        mod = getattr(base, name, None)
        if mod is not None:
            for prm in mod.parameters():
                prm.requires_grad = False
    if args.init_adapter:
        from safetensors.torch import load_file
        from peft.utils import set_peft_model_state_dict
        sd = load_file(str(Path(args.init_adapter) / "adapter_model.safetensors"))
        set_peft_model_state_dict(model, sd)
        print(f"[resume] loaded adapter weights from {args.init_adapter}", flush=True)
    model.print_trainable_parameters()
    model.gradient_checkpointing_enable(gradient_checkpointing_kwargs={"use_reentrant": False})
    model.enable_input_require_grads()
    model.cuda()

    # --- optimizer/scheduler (config58) ---
    trainable = [p for p in model.parameters() if p.requires_grad]
    opt = torch.optim.AdamW(trainable, lr=5e-5, betas=(0.9, 0.999), eps=1e-8, weight_decay=0.01)
    from transformers import get_constant_schedule_with_warmup
    sched = get_constant_schedule_with_warmup(opt, num_warmup_steps=3)

    def save_ckpt(gs, phase_name):
        ck = out_dir / f"checkpoint-{gs}"
        ck.mkdir(exist_ok=True)
        model.save_pretrained(ck, safe_serialization=True)
        meta = {"global_step": gs, "phase": phase_name, "model": args.model,
                "profile": args.profile, "seed": args.seed}
        json.dump(meta, open(ck / "train_meta.json", "w"), indent=1)
        print(f"[ckpt] saved {ck}", flush=True)

    # checkpoint 0 = baseline (no optimizer update performed)
    if 0 in save_steps and not args.init_adapter:
        save_ckpt(0, "baseline")

    # resume: keep the LR schedule aligned with the global step
    # (AdamW moments restart fresh - documented deviation for crash recovery)
    if args.start_step > 0:
        for _ in range(args.start_step):
            sched.step()
        print(f"[resume] scheduler advanced to step {args.start_step}, "
              f"lr={sched.get_last_lr()[0]:.2e}", flush=True)

    # --- training loop ---
    model.train()
    global_step = 0
    t_log = {"loss_sum": 0.0, "denom_sum": 0}
    mem_floor = None

    for gs, step, phase_name in plan:
        if gs <= args.start_step:
            continue
        loaded_rows = []
        for mb in step["microbatches"]:
            if mb["id"] in skip_long:
                continue
            rec = rows_by_id[mb["id"]]
            loaded_rows.append({"id": rec["id"], "pool": rec["pool"],
                                "features": rec["features"]})
        if not loaded_rows:
            print(f"[step {gs}] all microbatches skipped; stop.", flush=True)
            break

        prepared = oa.prepare_optimizer_step(step, loaded_rows)
        denominator = prepared["denominator"]

        # zero grads, then accumulate microbatches; loss numerator accumulates weighted CE;
        # divide by shared denominator ONCE per optimizer step at backward time:
        # backward each microbatch with (weight*CE summed)/denominator so autograd sums correct.
        opt.zero_grad(set_to_none=True)
        step_loss_value = 0.0
        n_tok_step = 0
        for row in prepared["microbatches"]:
            f = row["features"]
            ids = torch.tensor([f["input_ids"]], dtype=torch.long, device="cuda")
            labels = torch.tensor([f["labels"]], dtype=torch.long, device="cuda")
            weights = torch.tensor([f["loss_weights"]], dtype=torch.float32, device="cuda")
            logits = model(input_ids=ids).logits
            # shift
            logits = logits[:, :-1, :]
            tgt = labels[:, 1:]
            w = weights[:, 1:]
            ce = chunked_ce(logits, tgt, args.ce_chunk)
            mask = (tgt != -100).float()
            tok_loss = (ce * w * mask).sum() / denominator
            tok_loss.backward()
            step_loss_value += tok_loss.item() * denominator  # recompute numerator part
            n_tok_step += int(mask.sum().item())
            del logits, ce, tok_loss
        # course denominator counts ALL positive targets (== n_tok_step after shift)
        torch.nn.utils.clip_grad_norm_(trainable, 1.0)
        opt.step()
        sched.step()
        global_step = gs

        num = step_loss_value
        loss_val = num / denominator
        t_log["loss_sum"] += loss_val
        t_log["denom_sum"] += 1
        if mem_floor is None:
            mem_floor = torch.cuda.mem_get_info()[0] / 2**30
        mem_floor = min(mem_floor, torch.cuda.mem_get_info()[0] / 2**30)
        if gs % args.log_every == 0 or gs == total_updates:
            avg = t_log["loss_sum"] / t_log["denom_sum"]
            print(f"[step {gs}/{total_updates}] {phase_name} acc={len(prepared['microbatches'])} "
                  f"loss={loss_val:.4f} avg={avg:.4f} denom={denominator} "
                  f"lr={sched.get_last_lr()[0]:.2e} floor_gpu_free={mem_floor:.1f}GB", flush=True)
            t_log = {"loss_sum": 0.0, "denom_sum": 0}
        if gs in save_steps and gs != 0:
            save_ckpt(gs, phase_name)

    print("[done]", flush=True)


if __name__ == "__main__":
    main()
