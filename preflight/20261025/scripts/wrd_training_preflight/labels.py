"""Recover WRD terminal and route-decision labels from immutable evidence.

Offline transformation only: no model, training, agent loop, tool execution or
network request. Outputs may contain private source text and are work files,
not a public release. A later publication pass must inspect and sanitize them.
"""
from __future__ import annotations

import argparse
from collections import Counter
from hashlib import sha256
import gzip
import importlib.util
import json
from pathlib import Path
from typing import Any, Iterator


OLD_TOOLKIT = Path(__file__).resolve().parents[1] / "wrd_training"


CORE7 = ("ls", "read", "edit", "write", "apply_patch", "exec", "process")
DECISION_ACTIONS = {"new", "reuse", "defer", "no_value", "skip"}


def compact(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def value_sha(value: Any) -> str:
    return sha256(compact(value).encode("utf-8")).hexdigest()


def file_sha(path: Path) -> str:
    h = sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def read_rows(path: Path) -> Iterator[dict]:
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8-sig") as stream:
        for number, line in enumerate(stream, 1):
            if line.strip():
                value = json.loads(line)
                if not isinstance(value, dict):
                    raise ValueError(f"Non-object JSONL row {path.name}:{number}")
                yield value


class Writer:
    def __init__(self, path: Path):
        self.path = path
        self.stream = (gzip.open(path, "wt", encoding="utf-8", newline="\n", compresslevel=3)
                       if path.suffix == ".gz" else path.open("w", encoding="utf-8", newline="\n"))
        self.count = 0

    def write(self, value: Any) -> None:
        self.stream.write(compact(value) + "\n")
        self.count += 1

    def close(self) -> None:
        self.stream.close()


def excerpt_messages(messages: list[dict], max_chars: int = 18000) -> list[dict]:
    """An explicit partial view for triage, never a replacement SFT prefix."""
    selected = []
    indices = list(range(min(2, len(messages)))) + list(range(max(2, len(messages) - 4), len(messages)))
    for index in sorted(set(indices)):
        message = messages[index]
        body = message.get("content")
        body = body if isinstance(body, str) else compact(body)
        selected.append({"original_message_index": index, "role": message.get("role"),
                         "content_excerpt": body[:max_chars], "original_characters": len(body),
                         "excerpt_truncated": len(body) > max_chars})
    return selected


def _safe_object(bundle: Path, row: dict) -> bytes:
    base = (bundle / "archive/objects").resolve()
    path = (bundle / "archive" / row["object"]).resolve()
    if not path.is_relative_to(base):
        raise ValueError("Archive object escapes object directory")
    content = path.read_bytes()
    if len(content) != row["bytes"] or sha256(content).hexdigest() != row["sha256"]:
        raise ValueError("Archive object byte/hash mismatch")
    return content


def extract_labels(bundle: Path, output: Path, legacy_toolkit: Path | None = None) -> dict:
    # Resolve the frozen offline converter by file rather than a generic
    # `training` import, so public reproductions cannot import an unrelated
    # installed module. The default sibling layout remains unchanged.
    toolkit = (legacy_toolkit or OLD_TOOLKIT).resolve()
    converter_path = toolkit / "training.py"
    if not converter_path.is_file():
        raise ValueError("Frozen offline toolkit missing; supply --legacy-toolkit with training.py and resources/")
    spec = importlib.util.spec_from_file_location("wrd_frozen_offline_training", converter_path)
    if spec is None or spec.loader is None:
        raise ValueError("Cannot load frozen offline converter")
    converter = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(converter)
    _calls = converter._calls
    _clean_content = converter._clean_content
    _openai_message = converter._openai_message
    _protocol_valid = converter._protocol_valid
    _schema_map = converter._schema_map
    _text = converter._text
    bundle, output = bundle.resolve(), output.resolve()
    if output.is_relative_to(bundle) or bundle.is_relative_to(output):
        raise ValueError("Output and read-only input bundle must not overlap")
    if output.exists() and any(output.iterdir()):
        raise ValueError("Output must be new or empty; no silent overwrite")
    output.mkdir(parents=True, exist_ok=True)
    final_path = bundle / "datasets/final_candidates.train.jsonl.gz"
    action_path = bundle / "datasets/native_actions_core7.train.jsonl.gz"
    canonical_path = bundle / "canonical/native_episodes.jsonl.gz"
    archive_index = bundle / "archive/file_index.jsonl"
    resource = toolkit / "resources/native_coding_tools_97a0.json"
    source_paths = [final_path, action_path, canonical_path, archive_index, resource]
    before = {p.as_posix(): file_sha(p) for p in source_paths}
    schemas, issues = _schema_map(resource)
    if issues or set(schemas) != set(CORE7):
        raise ValueError("Frozen core7 schema resource is incomplete")
    tools = [schemas[name] for name in CORE7]
    finals = list(read_rows(final_path))
    by_episode: dict[str, list[dict]] = {}
    for row in finals:
        by_episode.setdefault(row["episode_id"], []).append(row)
    output_names = [
        "terminal_candidates.core7.jsonl.gz", "terminal_candidates.quarantine.jsonl.gz",
        "terminal_audit.jsonl", "screen_write_decisions.jsonl", "screen_artifact_decisions.jsonl",
        "screen_artifact_routes.jsonl", "screen_artifacts_index.jsonl", "screen_action_review_packets.jsonl",
    ]
    writers = {name: Writer(output / name) for name in output_names}
    counts, actions, final_actions, terminal_types = Counter(), Counter(), Counter(), Counter()
    failures = []
    screen_terminals = {r["archive_path"]: r for r in finals if r["kind"] == "screen"}
    canonical_seen = set()
    try:
        for episode in read_rows(canonical_path):
            eid = episode["episode_id"]
            if eid not in by_episode:
                continue
            if eid in canonical_seen:
                raise ValueError("Duplicate canonical episode")
            canonical_seen.add(eid)
            messages = episode["messages"]
            assistants = [i for i, message in enumerate(messages) if message.get("role") == "assistant"]
            for original in by_episode[eid]:
                index = original["target_message_index"]
                target = messages[index]
                expected_target = {k: v for k, v in target.items()
                                   if k not in ("details", "timestamp", "stopReason", "_multimodal")}
                prefix = []
                if isinstance(episode.get("system"), str) and episode["system"]:
                    system, _, _ = _clean_content(episode["system"])
                    prefix.append({"role": "system", "content": system})
                prefix += messages[:index]
                checks = {
                    "exact_native_prefix": original["prompt"] == prefix,
                    "exact_native_target": original["completion"] == [expected_target],
                    "identifier_matches_target_position": original["id"] == sha256((eid + ":" + str(index)).encode()).hexdigest()[:24],
                    "event_line_matches": episode["source_event_lines"][index] == original["target_event_line"],
                    "last_assistant_in_episode": bool(assistants) and index == assistants[-1],
                    "native_stop_reason": target.get("stopReason") == "stop",
                    "no_target_tool_calls": not _calls(target),
                    "nonempty_visible_target": bool(_text(target).strip()),
                    "historical_pairing_valid": _protocol_valid(prefix),
                    "native_environment_verified": original.get("native_verified") is True,
                    "no_known_benchmark_exposure": original.get("benchmark_exposed") is False,
                    "original_filter_reasons_empty": original.get("filter_reasons") == [],
                    "context_fully_recoverable": episode.get("context_fully_recoverable") is True,
                }
                used = {c.get("name") for m in prefix for c in _calls(m)}
                extra = sorted(str(x) for x in used - set(CORE7))
                audit = {"id": original["id"], "episode_id": eid, "kind": original["kind"],
                         "target_message_index": index, "target_event_line": original["target_event_line"],
                         "checks": checks, "noncore_historical_tools": extra,
                         "native_target_sha256": value_sha(original["completion"]),
                         "semantic_approval": None, "human_gold": False,
                         "claim": "exact_terminal_provenance_is_not_semantic_quality_approval"}
                writers["terminal_audit.jsonl"].write(audit)
                if not all(checks.values()):
                    failures.append({"id": original["id"], "failed_checks": [k for k, v in checks.items() if not v]})
                    writers["terminal_candidates.quarantine.jsonl.gz"].write({**original, "terminal_provenance": audit,
                                                                            "quarantine_reason": "terminal_provenance_check_failed"})
                    continue
                counts["terminal_exact_verified"] += 1
                terminal_types[original["kind"]] += 1
                if extra:
                    counts["terminal_noncore_schema_quarantine"] += 1
                    writers["terminal_candidates.quarantine.jsonl.gz"].write({**original, "terminal_provenance": audit,
                                                                            "quarantine_reason": "noncore_historical_tool_definition_not_recovered"})
                    continue
                standard = {**original, "schema_version": "wrd-openai-terminal-completion-v1",
                            "prompt": [_openai_message(m) for m in prefix],
                            "completion": [_openai_message(target)], "tools": tools,
                            "target_kind": "terminal_text", "semantic_review": "pending_ai_review",
                            "label": "exact_native_terminal_candidate_not_semantic_gold",
                            "terminal_type": "screen_output_handoff" if original["kind"] == "screen" else "make_completion_or_handoff",
                            "terminal_provenance": audit, "derived_from_final_candidates": True,
                            "independent_new_source": False, "uniform_core_tool_names": list(CORE7),
                            "tool_definition_scope": "uniform_fixed_image_core7_subset",
                            "tool_schema_status": "complete_for_all_observed_prefix_calls",
                            "not_full_original53_access_policy": True,
                            "requires_publication_privacy_review": True}
                # Timestamp/details/stopReason are not model-visible OpenAI content.
                # _openai_message is the same converter used for the existing main actions.
                writers["terminal_candidates.core7.jsonl.gz"].write(standard)
                counts["terminal_standard_core7"] += 1
                counts["terminal_standard_core7_" + original["kind"]] += 1
        missing = sorted(set(by_episode) - canonical_seen)
        if missing:
            raise ValueError(f"Canonical references missing for {len(missing)} final episodes")

        screen_rows = []
        write_rows = []
        decision_source_ids = set()
        for row in read_rows(action_path):
            if row.get("kind") != "screen":
                continue
            screen_rows.append(row)
            for message_index, message in enumerate(row["completion"]):
                for call_index, call in enumerate(message.get("tool_calls", [])):
                    function = call["function"]
                    counts["screen_target_call_" + function["name"]] += 1
                    if function["name"] != "write":
                        continue
                    args = function["arguments"]
                    args = json.loads(args) if isinstance(args, str) else args
                    if Path(str(args.get("path", "")).replace("\\", "/")).name != "routes.json":
                        continue
                    content = args.get("content")
                    if not isinstance(content, str):
                        continue
                    try:
                        data = json.loads(content)
                    except json.JSONDecodeError:
                        counts["screen_write_routes_json_parse_failed"] += 1
                        continue
                    if not isinstance(data, dict) or not isinstance(data.get("decisions"), list):
                        counts["screen_write_routes_schema_unexpected"] += 1
                        continue
                    write_rows.append(row)
                    counts["screen_route_write_parent_actions"] += 1
                    for n, decision in enumerate(data["decisions"]):
                        if not isinstance(decision, dict):
                            counts["screen_write_non_object_decision"] += 1
                            continue
                        label = decision.get("action")
                        actions[str(label)] += 1
                        sid = decision.get("source_id")
                        if isinstance(sid, str):
                            decision_source_ids.add(sid)
                        writers["screen_write_decisions.jsonl"].write({
                            "schema_version": "wrd-screen-decision-subtarget-v1",
                            "parent_sample_id": row["id"], "episode_id": row["episode_id"],
                            "target_message_index": row["target_message_index"],
                            "target_event_line": row["target_event_line"],
                            "target_completion_message_index": message_index,
                            "target_tool_call_index": call_index, "tool_call_id": call.get("id"),
                            "json_pointer_in_decoded_written_content": f"/decisions/{n}",
                            "target_completion_sha256": value_sha(row["completion"]),
                            "written_content_sha256": sha256(content.encode()).hexdigest(),
                            "decision": decision, "observed_action": label,
                            "known_action_vocabulary": label in DECISION_ACTIONS,
                            "evidence_level": "exact_actual_teacher_write_target",
                            "semantic_approval": None, "human_gold": False,
                            "is_separate_sft_example": False, "new_independent_sample": False,
                            "future_artifact_inserted_into_prompt": False,
                            "requires_publication_privacy_review": True,
                        })
                        counts["screen_write_decision_subtargets"] += 1
        counts["screen_write_distinct_source_ids"] = len(decision_source_ids)

        # Keep all direct structured targets in the proposed 100-action review,
        # then sample the remaining action positions evenly and deterministically.
        chosen = {r["id"]: r for r in write_rows}
        remaining = [r for r in screen_rows if r["id"] not in chosen]
        needed = max(0, 100 - len(chosen))
        if needed and remaining:
            positions = [min(len(remaining) - 1, i * len(remaining) // needed) for i in range(needed)]
            for position in positions:
                chosen[remaining[position]["id"]] = remaining[position]
        for row in sorted(chosen.values(), key=lambda r: r["id"]):
            writers["screen_action_review_packets.jsonl"].write({
                "schema_version": "wrd-screen-ai-review-packet-v1", "id": row["id"],
                "episode_id": row["episode_id"], "kind": row["kind"],
                "target_message_index": row["target_message_index"], "tool_call_names": row["tool_call_names"],
                "target": row["completion"], "target_sha256": value_sha(row["completion"]),
                "actual_past_prefix_sha256": value_sha(row["prompt"]),
                "past_context_excerpt": excerpt_messages(row["prompt"]),
                "excerpt_not_full_dependency_review": True,
                "full_context_source": "datasets/native_actions_core7.train.jsonl.gz",
                "full_context_lookup_id": row["id"], "semantic_approval": None,
                "review_must_check_actual_past_dependency_not_future_artifact": True,
                "contains_restricted_source_text": True, "do_not_publish_without_privacy_review": True,
            })

        wanted = {prefix + "/workspace/outputs/routes.json": terminal
                  for prefix, terminal in screen_terminals.items()}
        found_paths = set()
        for archived in read_rows(archive_index):
            logical = archived["logical_path"]
            if logical not in wanted:
                continue
            if logical in found_paths:
                raise ValueError("Duplicate final routes.json archive alias")
            found_paths.add(logical)
            terminal = wanted[logical]
            raw = _safe_object(bundle, archived)
            data = json.loads(raw.decode("utf-8-sig"))
            if not isinstance(data, dict) or not isinstance(data.get("decisions"), list):
                raise ValueError("Unexpected final route artifact schema")
            provenance = {"episode_id": terminal["episode_id"], "terminal_sample_id": terminal["id"],
                          "artifact_logical_path": logical, "artifact_sha256": archived["sha256"],
                          "archive_object": archived["object"], "artifact_bytes": archived["bytes"],
                          "artifact_relation": "final_workspace_side_evidence_not_past_supervision",
                          "is_separate_sft_example": False, "human_gold": False,
                          "semantic_approval": None, "requires_publication_privacy_review": True}
            writers["screen_artifacts_index.jsonl"].write({**provenance, "status": "present_hash_verified",
                                                          "decisions": len(data["decisions"]),
                                                          "routes": len(data.get("routes", []))})
            counts["screen_final_route_artifacts"] += 1
            for n, decision in enumerate(data["decisions"]):
                if not isinstance(decision, dict):
                    raise ValueError("Non-object final decision")
                final_actions[str(decision.get("action"))] += 1
                writers["screen_artifact_decisions.jsonl"].write({**provenance,
                    "schema_version": "wrd-screen-final-artifact-decision-audit-v1",
                    "json_pointer": f"/decisions/{n}", "decision": decision,
                    "claim": "recorded_final_artifact_decision_not_automatically_correct_or_independent"})
                counts["screen_final_artifact_decisions"] += 1
            for n, route in enumerate(data.get("routes", [])):
                writers["screen_artifact_routes.jsonl"].write({**provenance,
                    "schema_version": "wrd-screen-final-artifact-route-audit-v1",
                    "json_pointer": f"/routes/{n}", "route": route})
                counts["screen_final_artifact_routes"] += 1
        for logical in sorted(set(wanted) - found_paths):
            terminal = wanted[logical]
            writers["screen_artifacts_index.jsonl"].write({"episode_id": terminal["episode_id"],
                "terminal_sample_id": terminal["id"], "artifact_logical_path": logical,
                "status": "missing_not_fabricated", "is_separate_sft_example": False})
            counts["screen_final_routes_artifact_missing"] += 1
    finally:
        for writer in writers.values():
            writer.close()

    after = {p.as_posix(): file_sha(p) for p in source_paths}
    if before != after:
        raise ValueError("An input source changed during label recovery")
    report = {
        "schema_version": "wrd-label-recovery-report-v1", "status": "PASS" if not failures else "FAIL",
        "scope": "offline exact provenance, schema adaptation and recorded decision extraction only; not semantic gold approval",
        "contains_restricted_working_text": True, "safe_to_publish_as_is": False,
        "counts": dict(counts), "terminal_native_counts_by_kind": dict(terminal_types),
        "screen_write_target_decision_actions": dict(actions),
        "screen_final_artifact_decision_actions": dict(final_actions),
        "failures": failures,
        "outputs": [{"path": name, "rows": writer.count, "bytes": writer.path.stat().st_size,
                     "sha256": file_sha(writer.path)} for name, writer in writers.items()],
        "input_sha256_before": before, "input_sources_unchanged": before == after,
        "labels_py_sha256": file_sha(Path(__file__)),
        "old_openai_converter_py_sha256": file_sha(converter_path),
        "gold_semantic_approved": 0, "new_models_invoked": 0, "weights_trained": False,
        "limits": [
            "Terminal messages are exact actual last assistant targets; natural stop does not prove delivery or semantic quality.",
            "Screen write decisions are subtarget annotations, not independent training records.",
            "Final workspace artifacts are side evidence and must never be backfilled into historical prompts.",
            "Four noncore terminal histories require real tool schemas and are preserved in quarantine.",
            "All textual work outputs require privacy review before any public release.",
        ],
    }
    (output / "label_recovery_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--legacy-toolkit", type=Path, default=OLD_TOOLKIT,
                        help="Frozen offline toolkit directory containing training.py and resources/; default is sibling wrd_training/")
    args = parser.parse_args()
    result = extract_labels(args.bundle, args.output, args.legacy_toolkit)
    print(json.dumps({"status": result["status"], "counts": result["counts"],
                      "output_rows": {r["path"]: r["rows"] for r in result["outputs"]},
                      "input_sources_unchanged": result["input_sources_unchanged"],
                      "semantic_gold": 0, "weights_trained": False}, ensure_ascii=True))
    if result["failures"]:
        raise SystemExit(1)
