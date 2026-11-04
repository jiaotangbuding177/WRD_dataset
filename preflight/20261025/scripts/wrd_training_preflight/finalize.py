"""Finalize the WRD SFT admission manifest from immutable CPU compiler output.

No tokenizer, model, network, historical script or training is invoked. The
input training_eligible flag is pre-compilation only. admission.jsonl.gz and
FINAL_ADMISSION.json are the final entry point; compiled candidates are not.
"""
from __future__ import annotations

import argparse
from array import array
from collections import Counter, defaultdict
from contextlib import contextmanager
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import sys
import time
from typing import Any, Iterator
import uuid


SCHEMA = "wrd-final-admission-v1"
OUTPUTS = ("admission.jsonl.gz", "sft/common16k.jsonl.gz",
           "sft/common32k_long_only.jsonl.gz", "sft/README.md", "FINAL_ADMISSION.json")
MAIN_GATES = ("candidates", "publication_approved", "publication_held", "semantic_review_pass",
              "structural_clear", "precompile_training_eligible", "compiler_input_public",
              "compiler_success_reported", "compile_failed", "postcompile_rejected",
              "held_not_compiled", "public_not_compiled", "dual_model_protocol_mask_valid",
              "validated_public_le16k", "validated_public_le32k", "validated_public_over32k",
              "final_common16k", "final_common32k_long_only", "final_admitted", "not_admitted")


class InvalidRow(Exception):
    """Safe, content-free row rejection code."""


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def file_sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for part in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(part)
    return h.hexdigest()


def int_digest(ids: list[int]) -> str:
    packed = array("I", ids)
    if sys.byteorder != "little":
        packed.byteswap()
    return digest(packed.tobytes())


def labels_from_spans(ids: list[int], spans: list[list[int]]) -> list[int]:
    """Reconstruct the exact stored target mask without re-tokenizing."""
    labels = [-100] * len(ids)
    previous = 0
    for span in spans:
        if not isinstance(span, list) or len(span) != 2:
            raise InvalidRow("invalid_supervision_span")
        begin, end = span
        if type(begin) is not int or type(end) is not int or not 0 <= previous <= begin < end <= len(ids):
            raise InvalidRow("invalid_supervision_span")
        labels[begin:end] = ids[begin:end]
        previous = end
    return labels


def raw_lines(path: Path) -> Iterator[tuple[int, bytes]]:
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rb") as stream:
        for number, line in enumerate(stream, 1):
            if line.strip():
                yield number, line


@contextmanager
def gz_writer(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as raw:
        with gzip.GzipFile(fileobj=raw, filename="", mode="wb", compresslevel=3, mtime=0) as gz:
            yield gz


def safe_relative(root: Path, value: str) -> Path:
    if not isinstance(value, str) or not value:
        raise ValueError("unsafe_compiler_manifest_path")
    p = PurePosixPath(value.replace("\\", "/"))
    if p.is_absolute() or ".." in p.parts or re.match(r"^[A-Za-z]:", value):
        raise ValueError("unsafe_compiler_manifest_path")
    result = (root / str(p)).resolve()
    result.relative_to(root.resolve())
    return result


def failure_code(value: Any) -> str:
    if isinstance(value, str) and re.fullmatch(r"[A-Za-z0-9_.:-]{1,160}", value):
        return value
    return "compile_failure_detail_not_safe_to_copy"


def validate_record(row: dict[str, Any], audit: dict[str, Any], source: dict[str, Any],
                    length: dict[str, Any] | None, bucket: str) -> None:
    if row.get("schema_version") != "wrd-compiled-sft-v1":
        raise InvalidRow("compiled_schema_version_invalid")
    if row.get("publication_approved") is not True or audit.get("publication_approved") is not True:
        raise InvalidRow("publication_gate_not_passed")
    if row.get("training_eligible") is not audit.get("training_eligible"):
        raise InvalidRow("precompile_eligibility_flag_mismatch")
    if row.get("source_record_sha256") != source["sha256"]:
        raise InvalidRow("compiled_source_record_sha_mismatch")
    if row.get("source_file") != source["file"] or row.get("source_line") != source["line"]:
        raise InvalidRow("compiled_source_record_position_mismatch")
    if row.get("kind") != audit.get("kind") or row.get("kind") != source["kind"]:
        raise InvalidRow("compiled_kind_mismatch")
    if row.get("models_tokens_and_masks_identical") is not True:
        raise InvalidRow("dual_model_token_mask_equality_missing")
    ids = row.get("input_ids")
    if not isinstance(ids, list) or not ids or any(type(x) is not int or not 0 <= x <= 0xFFFFFFFF for x in ids):
        raise InvalidRow("input_ids_not_uint32_array")
    n, prompt, target = row.get("total_tokens"), row.get("prompt_tokens"), row.get("target_tokens")
    if any(type(x) is not int for x in (n, prompt, target)) or n != len(ids) or not 0 < prompt < n or target != n - prompt:
        raise InvalidRow("token_count_or_target_boundary_invalid")
    if row.get("supervision_spans") != [[prompt, n]]:
        raise InvalidRow("mask_not_exact_current_completion_span")
    if row.get("label_ignore_index") != -100:
        raise InvalidRow("label_ignore_index_mismatch")
    if int_digest(ids) != row.get("input_ids_sha256_u32le"):
        raise InvalidRow("input_ids_hash_mismatch")
    mask_sha = digest(bytes(prompt) + bytes([1]) * target)
    if mask_sha != row.get("completion_mask_sha256_u8"):
        raise InvalidRow("completion_mask_hash_mismatch")
    labels = labels_from_spans(ids, row["supervision_spans"])
    if any(x != -100 for x in labels[:prompt]) or labels[prompt:] != ids[prompt:]:
        raise InvalidRow("reconstructed_loss_labels_invalid")
    protocol = row.get("tool_protocol")
    if not isinstance(protocol, dict) or any(type(protocol.get(k)) is not int or protocol[k] < 0 for k in
            ("historical_tool_calls", "historical_tool_results", "current_tool_calls")):
        raise InvalidRow("tool_protocol_proof_missing")
    if protocol["historical_tool_calls"] != protocol["historical_tool_results"]:
        raise InvalidRow("historical_tool_protocol_unpaired")
    expected_bucket = "common16k" if n <= 16384 else "common32k_long" if n <= 32768 else "over32k"
    if row.get("length_bucket") != expected_bucket or bucket != expected_bucket:
        raise InvalidRow("compiled_length_bucket_mismatch")
    if length is None:
        raise InvalidRow("row_length_record_missing")
    for key in ("id", "kind", "source_file", "source_line", "publication_approved", "training_eligible",
                "prompt_tokens", "target_tokens", "total_tokens", "length_bucket",
                "input_ids_sha256_u32le", "completion_mask_sha256_u8"):
        if length.get(key) != row.get(key):
            raise InvalidRow("row_length_metadata_mismatch")


def finalize(public: Path, compiled: Path, output: Path, expected_candidates: int = 7117) -> dict[str, Any]:
    started = time.monotonic()
    public, compiled, output = public.resolve(), compiled.resolve(), output.resolve()
    if output.is_relative_to(compiled):
        raise ValueError("output_cannot_be_inside_compiler_input")
    for name in OUTPUTS:
        if (output / name).exists():
            raise ValueError("final_outputs_already_exist_use_fresh_output")
    report_path = compiled / "report.json"
    if not report_path.is_file():
        raise ValueError("compiler_report_not_ready")
    compiler_report = json.loads(report_path.read_text(encoding="utf-8"))
    global_errors: set[str] = set()
    if compiler_report.get("schema_version") != "wrd-token-mask-compilation-report-v1":
        global_errors.add("compiler_report_schema_invalid")
    if compiler_report.get("status") not in {"PASS", "COMPLETE_WITH_FAILURES"}:
        global_errors.add("compiler_report_not_complete")
    if compiler_report.get("limited_run") is not None:
        global_errors.add("limited_compilation_not_full_population")
    if compiler_report.get("training_started") is not False or compiler_report.get("no_truncation") is not True:
        global_errors.add("compiler_no_training_no_truncation_proof_missing")

    audit_path = public / "audit" / "eligibility.jsonl.gz"
    frozen_files: dict[Path, str] = {report_path: file_sha(report_path), audit_path: file_sha(audit_path)}
    audit: dict[str, dict[str, Any]] = {}
    for _, raw in raw_lines(audit_path):
        try:
            row = json.loads(raw)
        except ValueError:
            global_errors.add("eligibility_json_invalid")
            continue
        if not isinstance(row, dict):
            global_errors.add("eligibility_row_not_object")
            continue
        identifier = row.get("id")
        if not isinstance(identifier, str) or not identifier:
            global_errors.add("eligibility_id_missing")
            continue
        if identifier in audit:
            global_errors.add("duplicate_eligibility_id")
            continue
        audit[identifier] = row
        if type(row.get("publication_approved")) is not bool or type(row.get("training_eligible")) is not bool:
            global_errors.add("eligibility_flags_not_explicit_boolean")
        if row.get("human_gold") not in (False, 0):
            global_errors.add("unexpected_human_gold_claim")
        if not isinstance(row.get("structural_errors"), list):
            global_errors.add("eligibility_structure_proof_invalid")
    if len(audit) != expected_candidates:
        global_errors.add("eligibility_population_count_mismatch")
    public_ids = {i for i, r in audit.items() if r.get("publication_approved") is True}

    # Bind compilation to the exact public inputs and preserve only minimal
    # source metadata in memory. Full prompt/target content is never copied here.
    sources: dict[str, dict[str, Any]] = {}
    input_receipts = []
    input_names = set()
    input_entries = compiler_report.get("inputs", [])
    if not isinstance(input_entries, list):
        global_errors.add("compiler_inputs_manifest_not_array")
        input_entries = []
    for entry in input_entries:
        if not isinstance(entry, dict):
            global_errors.add("compiler_input_manifest_entry_not_object")
            continue
        name = entry.get("name")
        if not isinstance(name, str) or PurePosixPath(name.replace("\\", "/")).name != name or name in input_names:
            global_errors.add("compiler_input_name_invalid_or_duplicate")
            continue
        input_names.add(name)
        path = public / "data" / name
        if not path.is_file():
            global_errors.add("compiler_input_not_in_public_data")
            continue
        h = file_sha(path)
        frozen_files[path] = h
        if h != entry.get("sha256") or path.stat().st_size != entry.get("bytes"):
            global_errors.add("public_input_file_hash_or_size_mismatch")
        input_receipts.append({"path": "data/" + name, "sha256": h, "bytes": path.stat().st_size})
        for number, raw in raw_lines(path):
            try:
                source = json.loads(raw)
            except (ValueError, TypeError):
                global_errors.add("public_candidate_json_invalid")
                continue
            if not isinstance(source, dict):
                global_errors.add("public_candidate_row_not_object")
                continue
            identifier = source.get("id")
            if not isinstance(identifier, str) or not identifier:
                global_errors.add("public_candidate_id_invalid")
                continue
            if identifier not in public_ids:
                global_errors.add("public_input_id_not_public_in_eligibility")
                continue
            if identifier in sources:
                global_errors.add("duplicate_public_input_id")
                continue
            sources[identifier] = {"sha256": digest(raw.rstrip(b"\r\n")), "file": name,
                                   "line": number, "kind": source.get("kind")}
            if source.get("publication_approved") is not True or source.get("training_eligible") is not audit[identifier].get("training_eligible"):
                global_errors.add("public_source_eligibility_flags_mismatch")
    if set(sources) != public_ids:
        global_errors.add("public_input_population_incomplete")

    # Validate the compiler's immutable file manifest before trusting its proof.
    declared_files = set()
    file_entries = compiler_report.get("files", [])
    if not isinstance(file_entries, list):
        global_errors.add("compiler_files_manifest_not_array")
        file_entries = []
    for entry in file_entries:
        if not isinstance(entry, dict):
            global_errors.add("compiler_file_manifest_entry_not_object")
            continue
        relative = entry.get("path", "")
        try:
            path = safe_relative(compiled, relative)
        except ValueError:
            global_errors.add("compiler_file_manifest_path_invalid")
            continue
        if path in declared_files:
            global_errors.add("duplicate_compiler_file_manifest_entry")
            continue
        declared_files.add(path)
        if not path.is_file():
            global_errors.add("compiler_manifest_file_missing")
            continue
        h = file_sha(path)
        frozen_files[path] = h
        if h != entry.get("sha256") or path.stat().st_size != entry.get("bytes"):
            global_errors.add("compiler_output_file_hash_or_size_mismatch")

    lengths: dict[str, dict[str, Any]] = {}
    lengths_path = compiled / "row_lengths.jsonl"
    failures_path = compiled / "compile_failures.jsonl"
    for path in (lengths_path, failures_path):
        if path not in declared_files:
            global_errors.add("required_compiler_index_not_manifested")
        if not path.is_file():
            global_errors.add("required_compiler_index_missing")
    for _, raw in raw_lines(lengths_path) if lengths_path.is_file() else ():
        try:
            row = json.loads(raw)
            identifier = row.get("id")
            if not isinstance(identifier, str) or identifier in lengths:
                global_errors.add("row_lengths_id_missing_or_duplicate")
                continue
            lengths[identifier] = row
        except (ValueError, TypeError, AttributeError):
            global_errors.add("row_lengths_json_invalid")
    compile_failures: dict[str, list[str]] = defaultdict(list)
    failure_rows = 0
    for _, raw in raw_lines(failures_path) if failures_path.is_file() else ():
        failure_rows += 1
        try:
            row = json.loads(raw)
            identifier = row.get("id")
            if not isinstance(identifier, str) or identifier not in public_ids:
                global_errors.add("compile_failure_id_unknown_or_missing")
                continue
            compile_failures[identifier].append(failure_code(row.get("failure")))
            if len(compile_failures[identifier]) > 1:
                global_errors.add("duplicate_compilation_result_id")
        except (ValueError, TypeError, AttributeError):
            global_errors.add("compile_failure_json_invalid")

    # Metadata is small; token arrays are streamed once now and once for output.
    successful: dict[str, dict[str, Any]] = {}
    rejected: dict[str, list[str]] = defaultdict(list)
    compiler_record_ids: set[str] = set()
    expected_indexes: dict[str, set[str]] = defaultdict(set)
    shard_paths = sorted((compiled / "compiled" / "public_candidates").glob("*/part-*.jsonl.gz"))
    for path in shard_paths:
        if path not in declared_files:
            global_errors.add("public_compiled_shard_not_manifested")
        bucket = path.parent.name
        for number, raw in raw_lines(path):
            identifier = None
            try:
                row = json.loads(raw)
                identifier = row.get("id")
                if not isinstance(identifier, str) or identifier not in public_ids:
                    global_errors.add("compiled_record_id_unknown_or_held")
                    continue
                if identifier in compiler_record_ids or identifier in compile_failures:
                    global_errors.add("duplicate_compilation_result_id")
                    rejected[identifier].append("duplicate_compilation_result")
                    continue
                compiler_record_ids.add(identifier)
                if identifier not in sources:
                    rejected[identifier].append("source_record_binding_missing")
                    continue
                # ID manifests describe compiler output, before final validation.
                n = row.get("total_tokens")
                if type(n) is int and n > 0:
                    if n <= 32768:
                        expected_indexes["common32k.candidates"].add(identifier)
                        if row.get("training_eligible") is True:
                            expected_indexes["common32k.training_eligible"].add(identifier)
                    else:
                        expected_indexes["over32k.candidates"].add(identifier)
                    if n <= 16384:
                        expected_indexes["common16k.candidates"].add(identifier)
                        if row.get("training_eligible") is True:
                            expected_indexes["common16k.training_eligible"].add(identifier)
                validate_record(row, audit[identifier], sources[identifier], lengths.get(identifier), bucket)
                successful[identifier] = {"path": str(path.relative_to(compiled)).replace("\\", "/"), "line": number,
                    "source_file": row["source_file"], "source_line": row["source_line"],
                    "source_record_sha256": row["source_record_sha256"],
                    **{k: row[k] for k in ("total_tokens", "prompt_tokens", "target_tokens", "length_bucket",
                       "input_ids_sha256_u32le", "completion_mask_sha256_u8")}}
            except InvalidRow as exc:
                rejected[identifier].append(str(exc))
            except (ValueError, TypeError, KeyError, AttributeError, OverflowError):
                if isinstance(identifier, str) and identifier in public_ids:
                    rejected[identifier].append("compiled_record_parse_or_shape_invalid")
                else:
                    global_errors.add("compiled_record_json_without_identifiable_id")
    if set(lengths) != compiler_record_ids:
        global_errors.add("row_lengths_population_mismatch")
    if compiler_record_ids | set(compile_failures) != public_ids:
        global_errors.add("public_compilation_population_incomplete")
    report_counts = compiler_report.get("counts", {})
    if not isinstance(report_counts, dict):
        global_errors.add("compiler_report_counts_not_object")
        report_counts = {}
    if report_counts.get("rows_seen", 0) != len(public_ids):
        global_errors.add("compiler_report_public_population_mismatch")
    if report_counts.get("compiled_models_identical", 0) != len(compiler_record_ids):
        global_errors.add("compiler_report_success_count_mismatch")
    if report_counts.get("compile_failed", 0) != failure_rows:
        global_errors.add("compiler_report_failure_count_mismatch")
    for name in ("common16k.candidates", "common32k.candidates", "over32k.candidates",
                 "common16k.training_eligible", "common32k.training_eligible"):
        path = compiled / "ids" / (name + ".jsonl")
        if path not in declared_files or not path.is_file():
            global_errors.add("compiler_id_manifest_missing")
            continue
        ids = set()
        for _, raw in raw_lines(path):
            try:
                identifier = json.loads(raw).get("id")
                if not isinstance(identifier, str) or identifier in ids:
                    global_errors.add("compiler_id_manifest_duplicate_or_missing_id")
                ids.add(identifier)
            except (ValueError, TypeError, AttributeError):
                global_errors.add("compiler_id_manifest_json_invalid")
        if ids != expected_indexes[name]:
            global_errors.add("compiler_id_manifest_population_mismatch")

    admissions = []
    admitted: dict[str, str] = {}
    counts: Counter = Counter()
    by_kind: dict[str, Counter] = defaultdict(Counter)
    denial_counts: Counter = Counter()
    def count(key: str, kind: str) -> None:
        counts[key] += 1
        by_kind[kind][key] += 1
    for identifier, row in audit.items():
        kind = str(row.get("kind", "unknown"))
        count("candidates", kind)
        is_public = row.get("publication_approved") is True
        preeligible = row.get("training_eligible") is True
        semantic_pass = row.get("semantic_review") == "pass"
        structural_clear = row.get("structural_errors") == []
        if is_public: count("publication_approved", kind)
        else: count("publication_held", kind)
        if identifier in sources: count("compiler_input_public", kind)
        if identifier in compiler_record_ids: count("compiler_success_reported", kind)
        if semantic_pass: count("semantic_review_pass", kind)
        if structural_clear: count("structural_clear", kind)
        if preeligible: count("precompile_training_eligible", kind)
        reasons = []
        if not is_public: reasons.append("publication_hold")
        if not preeligible: reasons.append("precompile_training_eligible_false")
        if not semantic_pass: reasons.append("semantic_review_not_pass")
        if not structural_clear: reasons.append("structural_errors_or_missing_proof")
        if identifier in rejected:
            reasons.extend(rejected[identifier])
            compiled_status = "postcompile_rejected"
            count("postcompile_rejected", kind)
        elif identifier in compile_failures:
            reasons.extend("compile:" + code for code in compile_failures[identifier])
            compiled_status = "compile_failed"
            count("compile_failed", kind)
        elif identifier in successful:
            compiled_status = "validated"
            count("dual_model_protocol_mask_valid", kind)
        else:
            compiled_status = "public_not_compiled" if is_public else "held_not_compiled"
            count(compiled_status, kind)
            if is_public: reasons.append("public_compilation_result_missing")
        proof = successful.get(identifier) if not rejected.get(identifier) else None
        if proof:
            n = proof["total_tokens"]
            if n <= 16384:
                count("validated_public_le16k", kind)
            if n <= 32768:
                count("validated_public_le32k", kind)
            else:
                count("validated_public_over32k", kind)
                reasons.append("complete_example_over32k")
        is_admitted = bool(is_public and preeligible and semantic_pass and structural_clear and
                           proof and proof["total_tokens"] <= 32768 and not reasons)
        admission_bucket = None
        if is_admitted:
            admission_bucket = "common16k" if proof["total_tokens"] <= 16384 else "common32k_long_only"
            admitted[identifier] = admission_bucket
            count("final_admitted", kind)
            count("final_" + admission_bucket, kind)
        else:
            count("not_admitted", kind)
            denial_counts.update(set(reasons))
        # No source text, token arrays, original names or target body in manifest.
        result = {"schema_version": SCHEMA, "id": identifier, "kind": row.get("kind"),
                  "target_kind": row.get("target_kind"), "publication_approved": is_public,
                  "precompile_training_eligible": preeligible, "semantic_review": row.get("semantic_review"),
                  "structural_error_count": len(row["structural_errors"]) if isinstance(row.get("structural_errors"), list) else None,
                  "compiled_status": compiled_status, "final_admitted": is_admitted,
                  "final_bucket": admission_bucket, "exclusion_reasons": sorted(set(reasons)), "human_gold": False}
        if is_public and proof:
            result.update(proof)
        if is_admitted:
            result["sft_file"] = "sft/" + admission_bucket + ".jsonl.gz"
        admissions.append(result)
    # Keep main report gates stable even when a kind has zero admitted rows.
    for key in MAIN_GATES:
        counts.setdefault(key, 0)
        for values in by_kind.values():
            values.setdefault(key, 0)
    # Any source changed while we were reading invalidates the global release.
    for path, expected in frozen_files.items():
        if not path.is_file() or file_sha(path) != expected:
            global_errors.add("input_changed_during_finalization")

    output.mkdir(parents=True, exist_ok=True)
    stage = output / (".finalize-stage-" + uuid.uuid4().hex)
    stage.mkdir()
    with gz_writer(stage / "admission.jsonl.gz") as stream:
        for row in admissions:
            stream.write(canonical(row) + b"\n")
    written_ids = set()
    with gz_writer(stage / "sft/common16k.jsonl.gz") as small, \
            gz_writer(stage / "sft/common32k_long_only.jsonl.gz") as large:
        for path in shard_paths:
            for _, raw in raw_lines(path):
                try:
                    row = json.loads(raw)
                    identifier = row.get("id")
                except (ValueError, TypeError, AttributeError):
                    continue
                if identifier not in admitted or identifier in written_ids:
                    continue
                # Preserve original arrays, boundaries and spans exactly.
                row.update(final_admitted=True, final_admission_bucket=admitted[identifier],
                           precompile_training_eligible=row.get("training_eligible") is True,
                           training_eligible_stage="precompile", human_gold=False,
                           final_admission_manifest="admission.jsonl.gz")
                (small if admitted[identifier] == "common16k" else large).write(canonical(row) + b"\n")
                written_ids.add(identifier)
    if written_ids != set(admitted):
        global_errors.add("sft_output_population_mismatch")
    # A second proof check also covers the second streaming output pass.
    for path, expected in frozen_files.items():
        if not path.is_file() or file_sha(path) != expected:
            global_errors.add("input_changed_during_output")
    readme = """# WRD 最终 SFT 入口\n\n先检查上一级 FINAL_ADMISSION.json 的 status=PASS、release_ready=true，再读取 admission.jsonl.gz 中 final_admitted=true 的 ID。编译候选上的 training_eligible 是编译前标记，不能作为最终入口。\n\n- 16K：只使用 common16k.jsonl.gz。\n- 32K：使用 common16k.jsonl.gz 与 common32k_long_only.jsonl.gz 的并集，两文件 ID 互斥，不重复曝光。\n- 大于32K、未审、拒绝、隐私hold或编译/mask失败的样本均不在这两个SFT文件中。\n\n文件保留 input_ids、supervision_spans 与 label_ignore_index=-100，未重新分词、未裁剪。重建labels：\n\n```python\nlabels = [-100] * len(row[\"input_ids\"])\nfor begin, end in row[\"supervision_spans\"]:\n    labels[begin:end] = row[\"input_ids\"][begin:end]\n```\n\n本轮未启动训练。所有语义审核是AI局部证据银标，人工gold为0；不代表独立测试通过或Spark训练性能已实测。\n"""
    (stage / "sft/README.md").write_text(readme, encoding="utf-8")
    def fraction(a: int, b: int) -> float | None:
        return a / b if b else None
    report = {"schema_version": SCHEMA, "status": "FAIL" if global_errors else "PASS",
              "release_ready": not global_errors, "finished_utc": datetime.now(timezone.utc).isoformat(),
              "expected_candidate_population": expected_candidates, "counts": dict(counts),
              "by_kind": {k: dict(v) for k, v in sorted(by_kind.items())},
              "denominators": {"all_candidates_including_holds": len(audit), "public_candidates": len(public_ids),
                  "precompile_semantic_and_structure_eligible": counts["precompile_training_eligible"],
                  "compiler_input_public": len(sources), "compiler_success_reported": len(compiler_record_ids),
                  "dual_model_protocol_mask_valid": counts["dual_model_protocol_mask_valid"]},
              "coverage": {"validated_public_le16k_over_public": fraction(counts["validated_public_le16k"], len(public_ids)),
                  "validated_public_le32k_over_public": fraction(counts["validated_public_le32k"], len(public_ids)),
                  "final_le16k_over_precompile_eligible": fraction(counts["final_common16k"], counts["precompile_training_eligible"]),
                  "final_le32k_over_precompile_eligible": fraction(counts["final_admitted"], counts["precompile_training_eligible"])},
              "exclusion_reason_counts_nonexclusive": dict(denial_counts), "global_errors": sorted(global_errors),
              "compiler_status": compiler_report.get("status"), "compiler_report_sha256": frozen_files[report_path],
              "eligibility_sha256": frozen_files[audit_path], "public_source_inputs": input_receipts,
              "compiler_files_verified": len(declared_files),
              "source_files_checked_unchanged": not any(x.startswith("input_changed_") for x in global_errors),
              "script_sha256": file_sha(Path(__file__)), "human_gold": 0,
              "training_started": False, "weights_loaded": False, "gpu_used": False,
              "retokenization_performed": False, "truncation_performed": False,
              "scope": "Final subset selection and reversible loss-mask integrity proof only; AI silver labels, not human gold or model-quality evaluation.",
              "entrypoint_rule": "Require report PASS and release_ready, then admission.final_admitted; input training_eligible is precompile only.",
              "sft_nonempty": bool(written_ids),
              "mutually_exclusive_sft_buckets": True, "sft_output_ids": len(written_ids),
              "elapsed_seconds": round(time.monotonic() - started, 3),
              "files": [{"path": str(p.relative_to(stage)).replace("\\", "/"), "sha256": file_sha(p),
                         "bytes": p.stat().st_size} for p in sorted(stage.rglob("*")) if p.is_file()]}
    (stage / "FINAL_ADMISSION.json").write_bytes(json.dumps(report, ensure_ascii=False, indent=2).encode("utf-8") + b"\n")
    # Each artifact is replaced atomically, and the commit report appears last.
    for name in OUTPUTS:
        destination = output / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        (stage / name).replace(destination)
    (stage / "sft").rmdir()
    stage.rmdir()
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--public", type=Path, required=True)
    parser.add_argument("--compiled", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--expected-candidates", type=int, default=7117,
                        help="Default full population; smaller explicit values are for isolated synthetic fixtures only")
    args = parser.parse_args()
    report = finalize(args.public, args.compiled, args.output, args.expected_candidates)
    print(json.dumps({"status": report["status"], "release_ready": report["release_ready"],
                      "counts": report["counts"], "global_errors": report["global_errors"],
                      "training_started": False}, ensure_ascii=False))
    if not report["release_ready"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
