#!/usr/bin/env python3
"""Verify v2 checkpoint delivery and run the frozen WRD58 offline probes."""

import argparse
import hashlib
import json
import math
import os
import re
import sys
import time
from pathlib import Path


HERE = Path(__file__).resolve().parent
DIAGNOSTICS_SHA = "49b0eab2255afd7f218d92c90419776acbb9ae300c42be8635c208513e25cf19"
STEPS = (0, 26, 80, 134, 188, 241)
MODELS = {
    "8b": ("Qwen/Qwen3-8B", "b968826d9c46dd6066d109eabc6255188de91218"),
    "14b": ("Qwen/Qwen3-14B", "40c069824f4251a91eefaf281ebe4c544efd3e18"),
}
SHARED = (
    "wrd_train58.py", "test_chunked_ce.py", "active58/COURSE58.json", "active58/CONFIG58.json",
)
STEP_LINE = re.compile(r"^\[step (\d+)/(\d+)\].*?\bloss=(\S+)", re.MULTILINE)
ENUMS = {
    "decision": "KEEP | REVISE | REQUEST_POLICY | DEFER | STOP",
    "complete_cost_saving": "SAVING | NO_SAVING | UNKNOWN_BUDGET_CENSORED | UNKNOWN_MISSING_USAGE",
    "Q": "UNKNOWN_EVALUATOR_ERROR | UNKNOWN_MISSING_EVIDENCE | JSON number",
    "next_action": "ACCEPT | DIAGNOSE_AND_REPAIR | DEFER",
    "next_priority": "VERSIONED_FORMULA_REPAIR_AND_REGRESSION | FREEZE_SKILL | RETEST_QUOTING | DEFER",
}


def checkpoint(model, step):
    return f"out58_{model}_v2/checkpoint-{step}"


def log_path(model):
    return f"logs58/train_{model}_v2.log"


def sha256(path):
    with path.open("rb") as file:
        digest = hashlib.sha256()
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def manifest():
    path = HERE / "TRAINING_SHA256_v2.txt"
    entries = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        match = re.fullmatch(r"([0-9a-f]{64})\s+(\S+)", line)
        if match is None:
            raise ValueError(f"Malformed manifest line: {line}")
        digest, name = match.groups()
        if name in entries:
            raise ValueError(f"Duplicate manifest entry: {name}")
        entries[name] = digest
    required = set(SHARED)
    for model in MODELS:
        required.add(log_path(model))
        required.update(checkpoint(model, step) for step in STEPS)
    if set(entries) != required:
        raise ValueError("Manifest must contain the 12 v2 checkpoints, four shared files and two logs")
    return entries


def check_metadata(directory, model, step):
    metadata = read_json(directory / "train_meta.json")
    phase = "baseline" if step == 0 else "contract" if step == 26 else "process"
    expected = {
        "global_step": step, "phase": phase, "model": model,
        "profile": "budget_projection", "seed": 20261101,
    }
    if any(metadata.get(key) != value for key, value in expected.items()):
        raise ValueError(f"Training metadata differs from {expected}")
    config = read_json(directory / "adapter_config.json")
    if (config.get("base_model_name_or_path"), config.get("peft_type"),
            config.get("r"), config.get("lora_alpha")) != (MODELS[model][0], "LORA", 32, 64):
        raise ValueError("Adapter configuration does not match the pinned base and LoRA settings")


def check_log(path, model):
    raw = path.read_text(encoding="utf-8")
    steps = list(STEP_LINE.finditer(raw))
    positions = [(int(item[1]), int(item[2])) for item in steps]
    if positions != [(step, 241) for step in range(1, 242)]:
        raise ValueError("Expected one ordered optimizer-step line for each of 1 through 241")
    losses = [float(item[3]) for item in steps]
    if any(not math.isfinite(value) or value <= 0 for value in losses):
        raise ValueError("Expected finite positive loss on each step")
    if re.search(r"^\[done\]\s*$", raw[steps[-1].end():], re.MULTILINE) is None:
        raise ValueError("Missing [done] marker after step 241")
    if re.search(r"Traceback|OutOfMemoryError|\bOOM\b|\bKilled\b", raw, re.IGNORECASE):
        raise ValueError("Found an error signature in the successful training log")
    base, revision = MODELS[model]
    if f"[model] loading {base} @ {revision}" not in raw:
        raise ValueError("Pinned base revision is absent from the training log")
    return losses[-1]


def audit(root, entries, models):
    checks = [(name, root / name, None) for name in SHARED]
    for model in models:
        checks.append((log_path(model), root / log_path(model), lambda p, m=model: check_log(p, m)))
        for step in STEPS:
            name = checkpoint(model, step)
            directory = root / name
            checks.append((name, directory / "adapter_model.safetensors",
                           lambda p, m=model, s=step: check_metadata(p.parent, m, s)))
    rows = []
    for name, path, inspect in checks:
        row = {"path": path.as_posix(), "status": "pass"}
        try:
            if sha256(path) != entries[name]:
                raise ValueError("SHA256 mismatch")
            if inspect is not None:
                result = inspect(path)
                if result is not None:
                    row["final_loss"] = result
        except (OSError, ValueError, TypeError, AttributeError) as error:
            row.update(status="fail", error=str(error))
        rows.append(row)
    passed = sum(row["status"] == "pass" for row in rows)
    return {"status": "pass" if passed == len(rows) else "fail", "passed": passed,
            "total": len(rows), "files": rows}


def make_messages(case, case_policy):
    fields = {}
    for key, value in case["expected"].items():
        if key in ENUMS:
            fields[key] = ENUMS[key]
        else:
            fields[key] = {bool: "JSON boolean", int: "JSON integer", list: "JSON string array"}[type(value)]
    payload = {key: case[key] for key in ("facts", "given_tool_schema", "given_policy") if key in case}
    if case["id"].startswith("threshold_"):
        payload["given_policy"] = case_policy.removeprefix("For the first four cases only: ")
    payload["requested_fields"] = fields
    return [
        {"role": "system", "content": "Resolve this WRD diagnostic using the supplied facts and policy. "
                                      "Return only a JSON object with exactly the requested fields and correctly typed values. "
                                      "Choose a single value when alternatives are listed."},
        {"role": "user", "content": json.dumps(payload, ensure_ascii=False, indent=2)},
    ]


def strict_object(pairs):
    result = dict(pairs)
    if len(result) != len(pairs):
        raise ValueError("Duplicate JSON fields")
    return result


def finite_number(value):
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("Non-finite JSON number")
    return number


def same_value(actual, expected):
    if type(actual) is not type(expected):
        return False
    if isinstance(expected, list):
        return len(actual) == len(expected) and all(same_value(a, b) for a, b in zip(actual, expected))
    return actual == expected


def score(raw, expected):
    try:
        answer = json.loads(raw, object_pairs_hook=strict_object,
                            parse_float=finite_number, parse_constant=finite_number)
    except ValueError as error:
        return {"status": "invalid_json", "error": str(error)}
    if not isinstance(answer, dict) or set(answer) != set(expected):
        return {"status": "wrong_fields", "answer": answer}
    field_pass = {key: same_value(answer[key], value) for key, value in expected.items()}
    return {"status": "pass" if all(field_pass.values()) else "wrong_value",
            "answer": answer, "field_pass": field_pass}


def write_row(file, record):
    file.write(json.dumps(record, ensure_ascii=False, allow_nan=False) + "\n")
    file.flush()


def run_probes(args, entries):
    verdict = audit(args.root, entries, (args.model,))
    if verdict["status"] != "pass":
        print(json.dumps(verdict, indent=2), file=sys.stderr)
        return 1
    diagnostics = HERE / "DEVELOPMENT_DIAGNOSTICS58.json"
    if sha256(diagnostics) != DIAGNOSTICS_SHA:
        raise ValueError("Frozen WRD58 diagnostics SHA256 mismatch")
    data = read_json(diagnostics)
    cases = data["cases"]
    if (data["schema"] != "wrd58-authored-offline-development-diagnostics-v1" or
            len(cases) != 12 or len({case["id"] for case in cases}) != 12):
        raise ValueError("Expected the 12 unique frozen offline WRD58 diagnostic cases")
    prompts = [make_messages(case, data["case_policy"]) for case in cases]

    os.environ.update(HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1")
    import torch
    from peft import PeftModel
    from transformers import AutoModelForCausalLM, AutoTokenizer, GenerationConfig

    if not torch.cuda.is_available() or not torch.cuda.is_bf16_supported():
        raise RuntimeError("A CUDA device with BF16 support is required for checkpoint probing")
    base_name, revision = MODELS[args.model]
    with args.output.open("x", encoding="utf-8") as output, torch.inference_mode():
        write_row(output, {"record": "run", "model": args.model, "base": base_name,
                           "revision": revision, "diagnostics_sha256": DIAGNOSTICS_SHA,
                           "training_manifest_sha256": sha256(HERE / "TRAINING_SHA256_v2.txt"),
                           "script_sha256": sha256(Path(__file__)), "thinking": False,
                           "do_sample": False, "max_new_tokens": 256})
        try:
            tokenizer = AutoTokenizer.from_pretrained(base_name, revision=revision, local_files_only=True)
            base = AutoModelForCausalLM.from_pretrained(
                base_name, revision=revision, local_files_only=True,
                torch_dtype=torch.bfloat16, attn_implementation="sdpa",
            ).to("cuda").eval()
            inputs = [tokenizer.apply_chat_template(prompt, tokenize=True, add_generation_prompt=True,
                                                    return_dict=True, return_tensors="pt",
                                                    enable_thinking=False).to("cuda") for prompt in prompts]
            eos = base.generation_config.eos_token_id
            pad = tokenizer.pad_token_id
            if pad is None:
                pad = eos[0] if isinstance(eos, list) else eos
            generation = GenerationConfig(do_sample=False, max_new_tokens=256, use_cache=True,
                                          eos_token_id=eos, pad_token_id=pad)
            if args.check_base_parity:
                bare_logits = base(**inputs[0], use_cache=False).logits[0, -1].cpu()
        except Exception as error:
            write_row(output, {"record": "run_error", "stage": "load_base", "error": str(error)})
            raise

        for step in STEPS:
            directory = args.root / checkpoint(args.model, step)
            try:
                model = PeftModel.from_pretrained(base, str(directory), is_trainable=False).eval()
                if step == 0 and args.check_base_parity:
                    zero_logits = model(**inputs[0], use_cache=False).logits[0, -1].cpu()
                    equal = torch.equal(bare_logits, zero_logits)
                    write_row(output, {"record": "base_parity", "checkpoint": step, "exact": equal})
                    if not equal:
                        raise RuntimeError("checkpoint-0 next-token logits differ from the bare base")
            except Exception as error:
                write_row(output, {"record": "run_error", "stage": "load_adapter", "checkpoint": step,
                                   "error": str(error)})
                raise

            passed = 0
            for case, encoded in zip(cases, inputs):
                row = {"record": "probe", "model": args.model, "checkpoint": step, "case": case["id"],
                       "adapter_sha256": entries[checkpoint(args.model, step)],
                       "input_tokens": encoded["input_ids"].shape[1]}
                try:
                    torch.cuda.synchronize()
                    started = time.perf_counter()
                    sequence = model.generate(**encoded, generation_config=generation)[0, row["input_tokens"]:]
                    torch.cuda.synchronize()
                    raw = tokenizer.decode(sequence, skip_special_tokens=True)
                    row.update(raw_response=raw, output_tokens=sequence.numel(),
                               wall_seconds=time.perf_counter() - started)
                    row.update(score(raw, case["expected"]))
                except Exception as error:
                    row.update(status="runtime_error", error=str(error))
                    write_row(output, row)
                    raise
                write_row(output, row)
                passed += row["status"] == "pass"
            write_row(output, {"record": "checkpoint_summary", "model": args.model, "checkpoint": step,
                               "passed": passed, "total": len(cases)})
            base = model.unload()
            del model
            torch.cuda.empty_cache()
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    check = commands.add_parser("audit", help="Verify all manifest files and run metadata on CPU")
    check.add_argument("--root", required=True, type=Path)
    probe = commands.add_parser("probe", help="Run the 12 frozen cases on six checkpoints of one model")
    probe.add_argument("--root", required=True, type=Path)
    probe.add_argument("--model", required=True, choices=MODELS)
    probe.add_argument("--output", required=True, type=Path)
    probe.add_argument("--check-base-parity", action="store_true")
    args = parser.parse_args()
    args.root = args.root.resolve()
    try:
        entries = manifest()
        if args.command == "audit":
            result = audit(args.root, entries, MODELS)
            print(json.dumps(result, indent=2))
            return int(result["status"] != "pass")
        return run_probes(args, entries)
    except Exception as error:
        print(f"{type(error).__name__}: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
