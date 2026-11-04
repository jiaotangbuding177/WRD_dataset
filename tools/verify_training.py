"""Read-only consistency audit for a completed WRD training export.

Only TRAINING_VALIDATION.json is written. No model, tokenizer, or tool is run.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import gzip
from hashlib import sha256
import json
from pathlib import Path
import time

from build import clean_value
from training import (
    INCOMPLETE_MARKERS, _calls, _clean_content, _openai_message,
    _protocol_valid, _result_success, _target_call_id_errors,
)


def fingerprint(value):
    serialized = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return sha256(serialized.encode("utf-8")).hexdigest()


def read_rows(path):
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        for number, line in enumerate(handle, 1):
            if line.strip():
                yield number, json.loads(line)


def verify_training(bundle):
    bundle = Path(bundle).resolve()
    started = time.monotonic()
    counts, failure_counts = Counter(), Counter()
    failures, requested, seen_ids = [], defaultdict(list), set()

    def fail(reason, dataset, number=None, sample_id=None, episode_id=None):
        failure_counts[reason] += 1
        if len(failures) < 200:
            failures.append({"reason": reason, "dataset": dataset, "line": number, "sample_id": sample_id, "episode_id": episode_id})

    def check(condition, reason, dataset, number, row):
        if not condition:
            fail(reason, dataset, number, row.get("id"), row.get("episode_id"))
        return condition

    datasets = (
        ("native_actions", "execution_verified_candidate", "pending"),
        ("artifact_verified_write", "artifact_byte_verified_write_candidate", "byte_match_verified_not_global_semantic_approval"),
    )
    for dataset, label, review in datasets:
        path = bundle / "datasets" / f"{dataset}.train.jsonl.gz"
        for number, row in read_rows(path):
            counts[f"{dataset}_rows"] += 1
            identity = (dataset, row.get("id"))
            check(identity not in seen_ids, "duplicate_sample_id", dataset, number, row)
            seen_ids.add(identity)
            check(row.get("target_message_index") == row.get("prompt_end_message_exclusive"), "target_boundary_mismatch", dataset, number, row)
            check(row.get("split") == "train" and row.get("native_verified") is True and row.get("benchmark_exposed") is False, "invalid_training_eligibility", dataset, number, row)
            check(row.get("kind") in ("make", "screen"), "non_builder_primary_example", dataset, number, row)
            check(row.get("label") == label and row.get("semantic_review") == review, "label_is_not_limited_candidate", dataset, number, row)
            check(row.get("context_is_actual_past_prefix") is True, "incomplete_context_claim", dataset, number, row)
            check(row.get("online_policy_rollout") is False and row.get("reward") is None, "historical_example_mislabelled_rollout", dataset, number, row)
            declared_format = row.get("schema_version")
            standard = declared_format == "wrd-openai-tool-completion-v1"
            native_pending = declared_format == "wrd-completion-candidate-v1" and row.get("tool_schema_status") == "pending"
            check(standard or (dataset == "artifact_verified_write" and native_pending), "unsupported_declared_example_format", dataset, number, row)
            counts[f"{dataset}_{'standard_tool_format' if standard else 'native_schema_pending'}"] += 1
            tools = row.get("tools", [])
            serialized_tools = json.dumps(tools, ensure_ascii=False)
            check(not any(marker in serialized_tools for marker in INCOMPLETE_MARKERS), "truncated_tool_schema", dataset, number, row)
            definitions = {tool.get("function", {}).get("name"): tool.get("function", {}) for tool in tools if isinstance(tool, dict)}
            used_names = {call.get("function", {}).get("name") for message in row.get("prompt", []) + row.get("completion", []) for call in message.get("tool_calls", [])}
            check(used_names.issubset(definitions), "missing_used_tool_definition", dataset, number, row)
            check(all(isinstance(definitions[name].get("parameters"), dict) for name in used_names if name in definitions), "invalid_tool_parameters", dataset, number, row)
            completion = row.get("completion", [])
            check(len(completion) == 1 and completion[0].get("role") == "assistant", "invalid_completion_shape", dataset, number, row)
            requested[row.get("episode_id")].append({
                "dataset": dataset, "line": number, "id": row.get("id"),
                "index": row.get("target_message_index"),
                "prompt_sha": fingerprint(row.get("prompt")),
                "completion_sha": fingerprint(completion),
                "target_event_line": row.get("target_event_line"),
                "artifact_evidence": row.get("artifact_evidence", []),
                "declared_format": declared_format,
            })
            if number % 1000 == 0:
                print(f"indexed {dataset}: {number} rows; elapsed {time.monotonic() - started:.1f}s", flush=True)

    canonical_path = bundle / "canonical" / "native_episodes.jsonl.gz"
    last_progress = time.monotonic()
    for number, episode in read_rows(canonical_path):
        counts["canonical_episodes_read"] += 1
        episode_id = episode.get("episode_id")
        targets = requested.pop(episode_id, [])
        if not targets:
            continue
        counts["canonical_episodes_with_targets"] += 1
        messages = episode.get("messages", [])
        system = episode.get("system")
        for target in targets:
            dataset, line = target["dataset"], target["line"]
            ref = {"id": target["id"], "episode_id": episode_id}
            index = target["index"]
            if not isinstance(index, int) or index < 0 or index >= len(messages):
                fail("target_index_out_of_bounds", dataset, line, target["id"], episode_id)
                continue
            current = messages[index]
            prefix = []
            if isinstance(system, str) and system:
                prefix.append({"role": "system", "content": _clean_content(system)[0]})
            prefix.extend(messages[:index])
            if target["declared_format"] == "wrd-openai-tool-completion-v1":
                expected_prompt = clean_value([_openai_message(message) for message in prefix])
                expected_completion = clean_value([_openai_message(current)])
            else:
                # The strong byte-match subset legitimately includes native
                # examples whose tool schemas still need adaptation. Compare
                # their declared representation exactly; do not pretend they
                # are standard OpenAI tool examples or relax content equality.
                expected_prompt = clean_value(prefix)
                native_target = {key: value for key, value in current.items() if key not in ("details", "timestamp", "stopReason", "_multimodal")}
                expected_completion = clean_value([native_target])
            matched_prompt = check(fingerprint(expected_prompt) == target["prompt_sha"], "prompt_is_not_exact_past_prefix", dataset, line, ref)
            matched_completion = check(fingerprint(expected_completion) == target["completion_sha"], "completion_is_not_actual_target", dataset, line, ref)
            check(current.get("role") == "assistant", "canonical_target_is_not_assistant", dataset, line, ref)
            check(episode.get("split") == "train" and episode.get("native_verified") is True and episode.get("benchmark_exposed") is False, "canonical_training_ineligible", dataset, line, ref)
            check(episode.get("context_fully_recoverable") is True and not episode.get("message_parse_issues"), "canonical_context_not_fully_recoverable", dataset, line, ref)
            check(episode.get("source_event_lines", [])[index] == target["target_event_line"], "target_event_line_mismatch", dataset, line, ref)
            check(_protocol_valid(prefix), "historical_tool_protocol_invalid", dataset, line, ref)
            calls = _calls(current)
            check(bool(calls) and not _target_call_id_errors(calls, prefix), "target_tool_ids_invalid", dataset, line, ref)
            following = []
            for message in messages[index + 1:]:
                if message.get("role") == "assistant":
                    break
                following.append(message)
            results = defaultdict(list)
            for message in following:
                if message.get("role") in ("toolResult", "tool"):
                    results[message.get("toolCallId")].append(message)
            matched_results = []
            for call in calls:
                linked = results.get(call.get("id"), [])
                if not check(len(linked) == 1, "target_tool_result_not_unique", dataset, line, ref):
                    continue
                result = linked[0]
                check(result.get("toolName") in (None, call.get("name")), "target_result_tool_name_mismatch", dataset, line, ref)
                check(_result_success(result, call.get("name"))[0], "target_tool_result_not_successful", dataset, line, ref)
                matched_results.append(result)
            check(_protocol_valid(prefix + [current] + matched_results), "target_and_result_protocol_invalid", dataset, line, ref)
            if matched_prompt and matched_completion:
                counts[f"{dataset}_exact_checked"] += 1
            if dataset == "artifact_verified_write":
                evidence = target["artifact_evidence"]
                check(bool(evidence), "artifact_evidence_missing", dataset, line, ref)
                calls_by_id = {call.get("id"): call for call in calls}
                for item in evidence:
                    artifact = (bundle / item.get("retained_file", "")).resolve()
                    confined = artifact.is_relative_to(bundle / "skills" / "retained29")
                    if not check(confined and artifact.is_file(), "artifact_missing_or_outside_retained29", dataset, line, ref):
                        continue
                    digest = sha256(artifact.read_bytes()).hexdigest()
                    check(digest == item.get("content_sha256"), "retained_file_sha_mismatch", dataset, line, ref)
                    call = calls_by_id.get(item.get("tool_call_id"), {})
                    content = call.get("arguments", {}).get("content")
                    check(call.get("name") == "write" and isinstance(content, str), "artifact_not_supported_by_write_call", dataset, line, ref)
                    if isinstance(content, str):
                        check(sha256(content.encode("utf-8")).hexdigest() == digest, "write_content_not_byte_equal_artifact", dataset, line, ref)
                    counts["artifact_files_sha_checked"] += 1
        if time.monotonic() - last_progress > 20:
            print(f"canonical checked {number}; exact actions {counts['native_actions_exact_checked']}; elapsed {time.monotonic() - started:.1f}s", flush=True)
            last_progress = time.monotonic()

    for episode_id, targets in requested.items():
        for target in targets:
            fail("canonical_episode_missing", target["dataset"], target["line"], target["id"], episode_id)
    report = {
        "schema_version": "wrd-training-validation-v1",
        "validated_at": datetime.now(timezone.utc).isoformat(),
        "status": "PASS" if not failure_counts else "FAIL",
        "elapsed_seconds": round(time.monotonic() - started, 3),
        "counts": dict(counts), "failure_counts": dict(failure_counts),
        "failures": failures, "failures_total": sum(failure_counts.values()),
        "failures_list_limited_to": 200,
        "validator_sha256": sha256(Path(__file__).read_bytes()).hexdigest(),
        "scope": "All exported standard tool-action train examples and retained-artifact write examples: exact historical prefix/target in each declared standard or native representation, protocol, successful actual tool results, metadata, schema completeness where declared standard, artifact SHA consistency. Native schema-pending artifact examples are counted separately and are not called standard tool-format examples.",
        "limits": "Consistency audit only; not semantic human approval, training, tokenizer compilation, or a claim of no undiscovered leakage.",
    }
    (bundle / "TRAINING_VALIDATION.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "counts": report["counts"], "failure_counts": report["failure_counts"], "elapsed_seconds": report["elapsed_seconds"]}, ensure_ascii=False), flush=True)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", type=Path)
    args = parser.parse_args()
    result = verify_training(args.bundle)
    raise SystemExit(0 if result["status"] == "PASS" else 1)
