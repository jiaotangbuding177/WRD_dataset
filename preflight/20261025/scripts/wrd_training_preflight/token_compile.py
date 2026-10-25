"""CPU-only, loss-boundary-checked compilation for the pinned WRD Qwen3 pair.

This is offline data preparation. It never loads model weights, invokes an agent,
or performs a GPU forward/backward pass. Inputs must already carry explicit
publication_approved and training_eligible decisions from the parent audit.
"""
from __future__ import annotations

import argparse
from array import array
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import gzip
import hashlib
import importlib.metadata
from itertools import islice
import json
import os
from pathlib import Path
import sys
import time
from typing import Any, Iterable

os.environ.setdefault("CUDA_VISIBLE_DEVICES", "-1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")


class RowIssue(Exception):
    """A content-free failure code, so exception logs cannot leak row text."""


def digest_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def digest_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for part in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(part)
    return h.hexdigest()


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")


def int_digest(ids: list[int]) -> str:
    data = array("I", ids)
    if sys.byteorder != "little":
        data.byteswap()
    return digest_bytes(data.tobytes())


def labels_from_spans(ids: list[int], spans: list[list[int]], ignore_index: int = -100) -> list[int]:
    """The stored spans are a complete, reversible completion loss mask."""
    labels = [ignore_index] * len(ids)
    for begin, end in spans:
        if not 0 <= begin < end <= len(ids):
            raise ValueError("invalid_supervision_span")
        labels[begin:end] = ids[begin:end]
    return labels


def json_stream(path: Path) -> Iterable[tuple[int, bytes]]:
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rb") as stream:
        for line_no, line in enumerate(stream, 1):
            if line.strip():
                yield line_no, line


def check_protocol(row: dict[str, Any]) -> dict[str, int]:
    """Check pairing in the historical prefix, then only the current target.

    Historical tool failures are valid observations and are not required to pass
    the current tool argument schema. Current positive targets are validated.
    """
    from jsonschema import Draft202012Validator

    prompt, completion, tools = row.get("prompt"), row.get("completion"), row.get("tools")
    if not isinstance(prompt, list) or not prompt:
        raise RowIssue("missing_prompt_messages")
    if not isinstance(completion, list) or len(completion) != 1:
        raise RowIssue("completion_must_be_one_current_assistant")
    if completion[0].get("role") != "assistant":
        raise RowIssue("completion_role_not_assistant")
    if not isinstance(tools, list) or not tools:
        raise RowIssue("missing_uniform_tool_registry")
    registry = {}
    for tool in tools:
        if not isinstance(tool, dict) or tool.get("type") != "function":
            raise RowIssue("unsupported_tool_definition")
        function = tool.get("function")
        if not isinstance(function, dict) or not isinstance(function.get("name"), str):
            raise RowIssue("tool_definition_name_missing")
        name = function["name"]
        if name in registry:
            raise RowIssue("duplicate_tool_definition")
        schema = function.get("parameters")
        if not isinstance(schema, dict):
            raise RowIssue("tool_parameters_schema_missing")
        registry[name] = schema
    pending: set[str] = set()
    seen_calls: set[str] = set()
    calls = results = 0
    for message in prompt:
        if not isinstance(message, dict) or message.get("role") not in {"system", "user", "assistant", "tool"}:
            raise RowIssue("unsupported_prompt_role")
        role = message["role"]
        if role in {"system", "user", "assistant"} and pending:
            raise RowIssue("historical_tool_result_missing")
        if role == "assistant":
            for call in message.get("tool_calls") or []:
                call_id = call.get("id")
                fn = call.get("function")
                if not isinstance(call_id, str) or not call_id or call_id in seen_calls:
                    raise RowIssue("historical_call_id_missing_or_duplicate")
                if not isinstance(fn, dict) or fn.get("name") not in registry:
                    raise RowIssue("historical_tool_not_in_registry")
                seen_calls.add(call_id)
                pending.add(call_id)
                calls += 1
        elif role == "tool":
            call_id = message.get("tool_call_id")
            if call_id not in pending:
                raise RowIssue("historical_orphan_or_duplicate_tool_result")
            pending.remove(call_id)
            results += 1
    if pending:
        raise RowIssue("historical_tool_result_missing")
    target = completion[0]
    target_calls = target.get("tool_calls") or []
    if not target_calls and not isinstance(target.get("content"), str):
        raise RowIssue("current_target_has_no_text_or_calls")
    if not target_calls and not target["content"].strip():
        raise RowIssue("current_target_empty_text")
    target_ids = set()
    for call in target_calls:
        call_id = call.get("id")
        fn = call.get("function")
        if not isinstance(call_id, str) or not call_id or call_id in target_ids or call_id in seen_calls:
            raise RowIssue("current_call_id_missing_or_duplicate")
        if not isinstance(fn, dict) or fn.get("name") not in registry:
            raise RowIssue("current_tool_not_in_registry")
        target_ids.add(call_id)
        arguments = fn.get("arguments")
        if isinstance(arguments, str):
            try:
                arguments = json.loads(arguments)
            except (ValueError, TypeError):
                raise RowIssue("current_tool_arguments_not_json") from None
        if not isinstance(arguments, dict):
            raise RowIssue("current_tool_arguments_not_object")
        validator = Draft202012Validator(registry[fn["name"]])
        if next(validator.iter_errors(arguments), None) is not None:
            raise RowIssue("current_tool_argument_schema_error")
    return {"historical_tool_calls": calls, "historical_tool_results": results, "current_tool_calls": len(target_calls)}


class PairCompiler:
    def __init__(self, assets: Path, plan: dict[str, Any]):
        from transformers import AutoTokenizer

        self.tokens = {}
        self.asset_records = []
        expected = plan["official_tokenizer_asset_check"]["sha256"]
        names = ["tokenizer_config.json", "tokenizer.json", "vocab.json", "merges.txt", "generation_config.json"]
        for model_key in ("primary_14b", "control_8b"):
            root = assets / model_key
            records = []
            for name in names:
                h = digest_file(root / name)
                if h != expected[name]:
                    raise ValueError("official_asset_hash_mismatch:" + model_key + ":" + name)
                records.append({"file": name, "sha256": h, "bytes": (root / name).stat().st_size})
            config = json.loads((root / "tokenizer_config.json").read_text(encoding="utf-8"))
            if digest_bytes(config["chat_template"].encode("utf-8")) != expected["chat_template_string"]:
                raise ValueError("official_chat_template_hash_mismatch")
            tokenizer = AutoTokenizer.from_pretrained(root, local_files_only=True, trust_remote_code=False)
            self.tokens[model_key] = tokenizer
            self.asset_records.append({"model_key": model_key, "id": plan["models"][model_key]["id"],
                                       "revision": plan["models"][model_key]["revision"], "files": records})

    @staticmethod
    def one(tokenizer: Any, row: dict[str, Any]) -> tuple[list[int], list[int], dict[str, Any]]:
        prefix = tokenizer.apply_chat_template(row["prompt"], tools=row["tools"], tokenize=False,
                                              add_generation_prompt=True, enable_thinking=False)
        full = tokenizer.apply_chat_template(row["prompt"] + row["completion"], tools=row["tools"],
                                            tokenize=False, add_generation_prompt=False, enable_thinking=False)
        if not full.startswith(prefix):
            raise RowIssue("official_character_prefix_not_stable")
        encoded = tokenizer(full, add_special_tokens=False, return_offsets_mapping=True)
        ids, offsets = encoded["input_ids"], encoded["offset_mapping"]
        boundary = len(prefix)
        if any(start < boundary < end for start, end in offsets):
            raise RowIssue("token_straddles_prompt_completion_boundary")
        prompt_ids = tokenizer(prefix, add_special_tokens=False)["input_ids"]
        n_prompt = len(prompt_ids)
        if ids[:n_prompt] != prompt_ids:
            raise RowIssue("official_token_prefix_not_stable")
        mask = [int(start >= boundary and end > start) for start, end in offsets]
        if mask != [0] * n_prompt + [1] * (len(ids) - n_prompt):
            raise RowIssue("completion_mask_not_exact_contiguous_target")
        if not any(mask):
            raise RowIssue("empty_completion_mask")
        target_text = full[boundary:]
        if tokenizer.decode(ids[n_prompt:], skip_special_tokens=False,
                            clean_up_tokenization_spaces=False) != target_text:
            raise RowIssue("target_token_decode_not_exact")
        if not target_text.endswith("<|im_end|>\n"):
            raise RowIssue("current_target_end_marker_missing")
        eos_id = tokenizer.convert_tokens_to_ids("<|im_end|>")
        if ids[n_prompt:].count(eos_id) != 1:
            raise RowIssue("current_target_contains_embedded_end_marker")
        if "<|im_start|>" in target_text:
            raise RowIssue("current_target_contains_embedded_role_marker")
        spans = [[n_prompt, len(ids)]]
        labels = labels_from_spans(ids, spans)
        if any(label != -100 for label in labels[:n_prompt]):
            raise RowIssue("prompt_label_leak")
        if labels[n_prompt:] != ids[n_prompt:]:
            raise RowIssue("target_label_mismatch")
        return ids, mask, {"prompt_tokens": n_prompt, "target_tokens": len(ids) - n_prompt,
                           "total_tokens": len(ids), "supervision_spans": spans,
                           "rendered_prefix_sha256": digest_bytes(prefix.encode("utf-8")),
                           "rendered_target_sha256": digest_bytes(target_text.encode("utf-8"))}

    def compile(self, work: tuple[str, int, bytes]) -> dict[str, Any]:
        source_name, line_no, raw = work
        row: dict[str, Any] = {}
        try:
            row = json.loads(raw)
            if not isinstance(row, dict) or not isinstance(row.get("id"), str):
                raise RowIssue("missing_example_id")
            protocol = check_protocol(row)
            a_ids, a_mask, a_meta = self.one(self.tokens["primary_14b"], row)
            b_ids, b_mask, b_meta = self.one(self.tokens["control_8b"], row)
            if a_ids != b_ids or a_mask != b_mask or a_meta != b_meta:
                raise RowIssue("model_pair_tokens_or_loss_masks_differ")
            publication = row.get("publication_approved") is True
            eligible = row.get("training_eligible") is True
            preserved = {key: row[key] for key in ("semantic_review", "evidence_grade", "target_kind", "privacy_status",
                                                   "publication_status", "admission_status") if key in row}
            record = {"schema_version": "wrd-compiled-sft-v1", "id": row["id"], "kind": row.get("kind", "unknown"),
                      "source_file": source_name, "source_line": line_no, "source_record_sha256": digest_bytes(raw.rstrip(b"\r\n")),
                      "publication_approved": publication, "training_eligible": eligible,
                      "audit_metadata": preserved, "input_ids": a_ids,
                      "supervision_spans": a_meta.pop("supervision_spans"),
                      "label_ignore_index": -100,
                      "labels_definition": "labels[i]=input_ids[i] exactly in supervision_spans, otherwise -100",
                      "input_ids_sha256_u32le": int_digest(a_ids), "completion_mask_sha256_u8": digest_bytes(bytes(a_mask)),
                      "models_tokens_and_masks_identical": True, "tool_protocol": protocol, **a_meta}
            return {"ok": True, "record": record}
        except RowIssue as exc:
            return {"ok": False, "id": row.get("id") if isinstance(row, dict) else None,
                    "kind": row.get("kind", "unknown") if isinstance(row, dict) else "unknown",
                    "source_file": source_name, "source_line": line_no, "failure": str(exc),
                    "publication_approved": isinstance(row, dict) and row.get("publication_approved") is True,
                    "training_eligible": isinstance(row, dict) and row.get("training_eligible") is True}
        except Exception as exc:
            return {"ok": False, "id": row.get("id") if isinstance(row, dict) else None,
                    "kind": row.get("kind", "unknown") if isinstance(row, dict) else "unknown",
                    "source_file": source_name, "source_line": line_no,
                    "failure": "unexpected_" + type(exc).__name__,
                    "publication_approved": isinstance(row, dict) and row.get("publication_approved") is True,
                    "training_eligible": isinstance(row, dict) and row.get("training_eligible") is True}


class Shards:
    def __init__(self, root: Path, max_rows: int):
        self.root, self.max_rows = root, max_rows
        self.streams: dict[str, Any] = {}
        self.raw_streams: dict[str, Any] = {}
        self.rows: Counter = Counter()
        self.parts: Counter = Counter()
        self.paths = []

    def write(self, group: str, value: dict[str, Any]) -> None:
        if group not in self.streams or self.rows[group] % self.max_rows == 0:
            if group in self.streams:
                self.streams[group].close()
                self.raw_streams[group].close()
            path = self.root / group / ("part-%05d.jsonl.gz" % self.parts[group])
            path.parent.mkdir(parents=True, exist_ok=True)
            raw = path.open("wb")
            self.raw_streams[group] = raw
            self.streams[group] = gzip.GzipFile(fileobj=raw, filename="", mode="wb", compresslevel=3, mtime=0)
            self.parts[group] += 1
            self.paths.append(path)
        self.streams[group].write(canonical(value) + b"\n")
        self.rows[group] += 1

    def close(self) -> None:
        for group in self.streams:
            self.streams[group].close()
            self.raw_streams[group].close()


def quantiles(values: list[int]) -> dict[str, Any]:
    if not values:
        return {"count": 0, "sum": 0}
    values = sorted(values)
    def q(percent: float) -> int:
        return values[min(len(values) - 1, int((len(values) - 1) * percent))]
    return {"count": len(values), "sum": sum(values), "min": values[0], "median": q(.5),
            "p95": q(.95), "p99": q(.99), "max": values[-1]}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, action="append", required=True)
    parser.add_argument("--assets", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--plan", type=Path, default=Path(__file__).resolve().parents[3] / "research/plans/20261025_wrd_14b_spark/TRAINING_CONFIG.json")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--max-shard-rows", type=int, default=256)
    args = parser.parse_args()
    if args.workers < 1 or args.workers > 4 or args.max_shard_rows < 1:
        raise SystemExit("workers must be 1..4; shard rows positive")
    out = args.output.resolve()
    if out.exists() and any(out.iterdir()):
        raise SystemExit("Output must be absent or empty; no overwrite or recursive cleanup is performed")
    out.mkdir(parents=True, exist_ok=True)
    plan = json.loads(args.plan.read_text(encoding="utf-8"))
    compiler = PairCompiler(args.assets.resolve(), plan)
    started = time.perf_counter()
    inputs = [{"name": p.name, "sha256": digest_file(p), "bytes": p.stat().st_size} for p in args.input]
    counts: Counter = Counter()
    by_kind: dict[str, Counter] = defaultdict(Counter)
    lengths, prompts, targets = [], [], []
    failures: Counter = Counter()
    seen_ids = set()
    manifests = {}
    for name in ("common16k.candidates", "common32k.candidates", "over32k.candidates", "common16k.training_eligible", "common32k.training_eligible"):
        d = out / "ids"
        d.mkdir(exist_ok=True)
        manifests[name] = (d / (name + ".jsonl")).open("wb")
    stats = (out / "row_lengths.jsonl").open("wb")
    errors = (out / "compile_failures.jsonl").open("wb")
    writer = Shards(out / "compiled", args.max_shard_rows)

    def works() -> Iterable[tuple[str, int, bytes]]:
        n = 0
        for path in args.input:
            for number, raw in json_stream(path):
                if args.limit is not None and n >= args.limit:
                    return
                n += 1
                yield path.name, number, raw

    def bounded_results(pool: Any) -> Iterable[dict[str, Any]]:
        source = iter(works())
        while batch := list(islice(source, args.workers * 2)):
            yield from pool.map(compiler.compile, batch)

    try:
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            # Small batches bound retained raw rows and token arrays as well as workers.
            for result in bounded_results(pool):
                counts["rows_seen"] += 1
                observed = result["record"] if result["ok"] else result
                observed_public = observed.get("publication_approved") is True
                observed_eligible = observed_public and observed.get("training_eligible") is True
                counts["publication_approved_seen"] += observed_public
                counts["training_eligible_seen"] += observed_eligible
                by_kind[str(observed.get("kind", "unknown"))]["rows_seen"] += 1
                by_kind[str(observed.get("kind", "unknown"))]["training_eligible_seen"] += observed_eligible
                if not result["ok"]:
                    failures[result["failure"]] += 1
                    counts["compile_failed"] += 1
                    errors.write(canonical(result) + b"\n")
                    continue
                row = result["record"]
                if row["id"] in seen_ids:
                    counts["duplicate_ids_not_duplicated"] += 1
                    failures["duplicate_id"] += 1
                    errors.write(canonical({"id": row["id"], "kind": row["kind"], "failure": "duplicate_id",
                                            "source_file": row["source_file"], "source_line": row["source_line"],
                                            "publication_approved": row["publication_approved"],
                                            "training_eligible": row["training_eligible"]}) + b"\n")
                    continue
                seen_ids.add(row["id"])
                counts["compiled_models_identical"] += 1
                kind = str(row["kind"])
                by_kind[kind]["compiled"] += 1
                public = row["publication_approved"]
                eligible = public and row["training_eligible"]
                counts["publication_approved_compiled"] += public
                counts["training_eligible_compiled"] += eligible
                by_kind[kind]["training_eligible_compiled"] += eligible
                n = row["total_tokens"]
                lengths.append(n)
                prompts.append(row["prompt_tokens"])
                targets.append(row["target_tokens"])
                bucket = "common16k" if n <= 16384 else "common32k_long" if n <= 32768 else "over32k"
                counts[bucket] += 1
                by_kind[kind][bucket] += 1
                if eligible:
                    counts[bucket + "_training_eligible"] += 1
                    by_kind[kind][bucket + "_training_eligible"] += 1
                row["length_bucket"] = bucket
                # Private/unapproved canaries cannot accidentally be copied with public shards.
                prefix = "public_candidates" if public else "unapproved_local_only"
                writer.write(prefix + "/" + bucket, row)
                small = {k: row[k] for k in ("id", "kind", "source_file", "source_line", "publication_approved", "training_eligible", "prompt_tokens", "target_tokens", "total_tokens", "length_bucket", "input_ids_sha256_u32le", "completion_mask_sha256_u8")}
                stats.write(canonical(small) + b"\n")
                if public:
                    keys = ["over32k.candidates"] if n > 32768 else ["common32k.candidates"]
                    if n <= 16384:
                        keys.append("common16k.candidates")
                    if eligible and n <= 32768:
                        keys.append("common32k.training_eligible")
                    if eligible and n <= 16384:
                        keys.append("common16k.training_eligible")
                    for key in keys:
                        manifests[key].write(canonical(small) + b"\n")
                if counts["rows_seen"] % 100 == 0:
                    progress = {"status": "RUNNING", "counts": dict(counts), "failure_counts": dict(failures), "elapsed_seconds": round(time.perf_counter() - started, 3)}
                    (out / "progress.json").write_bytes(canonical(progress) + b"\n")
                    print(json.dumps({"rows_seen": counts["rows_seen"], "compiled": counts["compiled_models_identical"], "failed": counts["compile_failed"]}), flush=True)
    finally:
        writer.close()
        stats.close()
        errors.close()
        for stream in manifests.values():
            stream.close()
    elapsed = time.perf_counter() - started
    n_valid = counts["compiled_models_identical"]
    eligible_n = counts["training_eligible_seen"]
    public_n = counts["publication_approved_seen"]
    public_bucket_counts = Counter()
    for path in (out / "ids").glob("*.candidates.jsonl"):
        public_bucket_counts[path.stem] = sum(1 for _ in path.open("rb"))
    common_16 = public_bucket_counts["common16k.candidates"]
    common_32 = public_bucket_counts["common32k.candidates"]
    report = {"schema_version": "wrd-token-mask-compilation-report-v1", "status": "COMPLETE_WITH_FAILURES" if failures else "PASS",
              "finished_utc": datetime.now(timezone.utc).isoformat(), "elapsed_seconds": round(elapsed, 3),
              "scope": "CPU tokenization and exact current-completion loss masks only; not semantic gold, model behavior, training memory feasibility or independent validation",
              "inputs": inputs, "limited_run": args.limit, "counts": dict(counts), "failure_counts": dict(failures),
              "by_kind": {k: dict(v) for k, v in sorted(by_kind.items())},
              "total_tokens": quantiles(lengths), "prompt_tokens": quantiles(prompts), "supervised_tokens": quantiles(targets),
              "coverage_public_candidates": {"denominator": public_n, "compiled_denominator": counts["publication_approved_compiled"], "complete_le_16k": common_16, "complete_le_32k": common_32,
                                            "fraction_le_16k": common_16 / public_n if public_n else None,
                                            "fraction_le_32k": common_32 / public_n if public_n else None},
              "coverage_training_eligible": {"denominator": eligible_n, "compiled_denominator": counts["training_eligible_compiled"],
                                             "complete_le_16k": counts["common16k_training_eligible"],
                                             "complete_le_32k": counts["common16k_training_eligible"] + counts["common32k_long_training_eligible"],
                                             "fraction_le_16k": counts["common16k_training_eligible"] / eligible_n if eligible_n else None,
                                             "fraction_le_32k": (counts["common16k_training_eligible"] + counts["common32k_long_training_eligible"]) / eligible_n if eligible_n else None},
              "all_successful_rows_models_token_and_mask_equal": n_valid == counts["compiled_models_identical"],
              "tokenizer_assets": compiler.asset_records,
              "compiler_sha256": digest_file(Path(__file__)), "plan_sha256": digest_file(args.plan),
              "packages": {name: importlib.metadata.version(name) for name in ("transformers", "tokenizers", "jinja2", "jsonschema")},
              "loss_mask_storage": "single contiguous supervision span, exactly reversible to completion_mask and labels; -100 outside span",
              "no_truncation": True, "weights_loaded": False, "gpu_used": False, "training_started": False,
              "files": [{"path": str(path.relative_to(out)).replace("\\", "/"), "sha256": digest_file(path), "bytes": path.stat().st_size}
                        for path in sorted(out.rglob("*")) if path.is_file() and path.name not in {"progress.json", "report.json"}]}
    (out / "report.json").write_bytes(json.dumps(report, ensure_ascii=False, indent=2).encode("utf-8") + b"\n")
    (out / "progress.json").write_bytes(canonical({"status": report["status"], "counts": report["counts"], "elapsed_seconds": report["elapsed_seconds"]}) + b"\n")
    print(json.dumps({"status": report["status"], "counts": report["counts"], "failure_counts": report["failure_counts"],
                      "coverage_public_candidates": report["coverage_public_candidates"], "coverage_training_eligible": report["coverage_training_eligible"],
                      "elapsed_seconds": report["elapsed_seconds"], "training_started": False}), flush=True)


if __name__ == "__main__":
    main()
