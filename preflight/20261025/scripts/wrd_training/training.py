"""Offline WRD native trajectory export. No agent loop or model invocation.

The native protocol candidates are evidence-bearing examples, not automatically
approved gold labels. Tool execution success is a narrower claim than quality.
"""
from __future__ import annotations

from collections import Counter
from contextlib import ExitStack
from hashlib import sha256
import gzip
import json
from pathlib import Path
import re
from typing import Any


FORMAL_MARKER = re.compile(r"\bT\d{4}\b|eval(?:uation)?[_ -]?250|evaluation_visible|正式\s*250|固定\s*226|当前\s*250", re.I)
REASONING_TAG = re.compile(r"<(?:think|thinking|reasoning)>[\s\S]*?</(?:think|thinking|reasoning)>", re.I)
INCOMPLETE_MARKERS = ("trajectory-depth-limit", "[Truncated]", "[Malformed diagnostic JSON redacted]")
SPLITS = ("train", "validation", "test", "quarantine")
BENCHMARK_PROHIBITION = "不得访问正式250测试任务或答案"


def _benchmark_exposed(messages: list[dict]) -> bool:
    # A fixed prohibition in every make prompt is not evidence that test content
    # was actually supplied. Only this exact known template is ignored in the
    # detection view; the archived messages retain every original character.
    detection_view = _json(messages).replace(BENCHMARK_PROHIBITION, "")
    return bool(FORMAL_MARKER.search(detection_view))


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _load(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return default


def _clean_content(content: Any) -> tuple[Any, int, bool]:
    """Keep visible blocks and native calls; never export private reasoning."""
    if isinstance(content, str):
        cleaned, count = REASONING_TAG.subn("", content)
        return cleaned, count, False
    if not isinstance(content, list):
        return content, 0, content is not None
    result, removed, multimodal = [], 0, False
    for block in content:
        if not isinstance(block, dict):
            result.append(block)
            multimodal = True
            continue
        kind = block.get("type", "")
        if kind in ("thinking", "reasoning", "redacted_thinking"):
            removed += 1
            continue
        copied = dict(block)
        if kind == "text":
            copied["text"], count = REASONING_TAG.subn("", str(block.get("text", "")))
            removed += count
        elif kind != "toolCall":
            multimodal = True
        result.append(copied)
    return result, removed, multimodal


def _messages(event_file: Path) -> tuple[list[dict], list[int], Counter]:
    messages, event_lines, stats = [], [], Counter()
    if not event_file.is_file():
        stats["missing_event_file"] += 1
        return messages, event_lines, stats
    with event_file.open(encoding="utf-8-sig") as handle:
        for number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                stats["malformed_event_lines"] += 1
                continue
            source = row.get("message")
            if row.get("type") != "message" or not isinstance(source, dict):
                continue
            role = source.get("role")
            if role not in ("system", "user", "assistant", "toolResult", "tool"):
                stats["unknown_message_role"] += 1
                continue
            content, removed, multimodal = _clean_content(source.get("content", ""))
            stats["reasoning_blocks_removed"] += removed
            if multimodal:
                stats["multimodal_messages"] += 1
            message = {"role": role, "content": content}
            for key in ("toolCallId", "toolName", "isError", "details", "timestamp", "stopReason"):
                if key in source:
                    message[key] = source[key]
            if multimodal:
                message["_multimodal"] = True
            messages.append(message)
            event_lines.append(number)
    return messages, event_lines, stats


def _calls(message: dict) -> list[dict]:
    content = message.get("content")
    return [x for x in content if isinstance(x, dict) and x.get("type") == "toolCall"] if isinstance(content, list) else []


def _text(message: dict) -> str:
    content = message.get("content", "")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(str(x.get("text", "")) for x in content if isinstance(x, dict) and x.get("type") == "text")
    return ""


def _result_success(result: dict, name: str) -> tuple[bool, str]:
    if result.get("isError") is not False:
        return False, "tool_error_or_success_flag_unknown"
    details = result.get("details")
    details = details if isinstance(details, dict) else {}
    if "exitCode" in details and details["exitCode"] not in (0, None):
        return False, "nonzero_exit_code"
    if details.get("noOutputTimedOut") is True:
        return False, "tool_timeout"
    if details.get("status") in ("error", "failed", "running", "pending", "timeout"):
        return False, "tool_not_confirmed_complete"
    if name in ("exec", "process"):
        if details.get("exitCode") != 0:
            return False, "process_exit_not_confirmed_zero"
    return True, "tool_result_success"


def _schema_map(path: Path) -> tuple[dict[str, dict], Counter]:
    raw = _load(path, [])
    if isinstance(raw, dict):
        raw = raw.get("tools", [])
    result, stats = {}, Counter()
    for item in raw if isinstance(raw, list) else []:
        if not isinstance(item, dict):
            stats["truncated_tool_entries"] += 1
            continue
        tool = item.get("function", item)
        if not isinstance(tool, dict) or not isinstance(tool.get("name"), str):
            stats["invalid_tool_entries"] += 1
            continue
        serialized = _json(tool)
        if any(marker in serialized for marker in INCOMPLETE_MARKERS):
            stats["incomplete_tool_entries"] += 1
            continue
        if not isinstance(tool.get("parameters"), dict):
            stats["missing_parameters_entries"] += 1
            continue
        result[tool["name"]] = {"type": "function", "function": tool}
    return result, stats


def _openai_message(message: dict) -> dict:
    role = message["role"]
    if role in ("toolResult", "tool"):
        return {"role": "tool", "tool_call_id": message.get("toolCallId", ""), "content": _text(message)}
    converted = {"role": role, "content": _text(message)}
    calls = _calls(message)
    if calls:
        converted["tool_calls"] = [{"id": x.get("id", ""), "type": "function", "function": {"name": x.get("name", ""), "arguments": _json(x.get("arguments", {}))}} for x in calls]
        if not converted["content"]:
            converted["content"] = None
    return converted


def _protocol_valid(messages: list[dict]) -> bool:
    """Every historical tool call must have exactly one matching result."""
    pending: set[str] = set()
    seen: set[str] = set()
    for message in messages:
        if message["role"] == "assistant":
            if pending:
                return False
            for call in _calls(message):
                identifier = call.get("id")
                if not identifier or identifier in seen:
                    return False
                pending.add(identifier)
                seen.add(identifier)
        elif message["role"] in ("tool", "toolResult"):
            identifier = message.get("toolCallId")
            if identifier not in pending:
                return False
            pending.remove(identifier)
        elif pending:
            return False
    return not pending


def _target_call_id_errors(calls: list[dict], prefix: list[dict]) -> list[str]:
    """Check current calls too: prefix validity alone cannot detect reuse."""
    identifiers = [call.get("id") for call in calls]
    errors = []
    if any(not isinstance(identifier, str) or not identifier.strip() for identifier in identifiers):
        errors.append("missing_target_tool_call_id")
    valid_ids = [identifier for identifier in identifiers if isinstance(identifier, str) and identifier.strip()]
    if len(valid_ids) != len(set(valid_ids)):
        errors.append("duplicate_target_tool_call_id")
    historical_ids = {call.get("id") for message in prefix for call in _calls(message) if isinstance(call.get("id"), str)}
    if historical_ids.intersection(valid_ids):
        errors.append("target_tool_call_id_reused_in_prefix")
    return errors


def _artifact_match(calls: list[dict], route: str, output: Path) -> list[dict]:
    matches = []
    if not route:
        return matches
    for call in calls:
        arguments = call.get("arguments", {})
        if call.get("name") != "write" or not isinstance(arguments, dict):
            continue
        target = str(arguments.get("path", arguments.get("file_path", ""))).replace("\\", "/")
        marker = "outputs/skill/"
        if marker not in target or not isinstance(arguments.get("content"), str):
            continue
        relative = target.split(marker, 1)[1]
        if not relative or ".." in Path(relative).parts:
            continue
        content = arguments["content"].encode("utf-8")
        candidates = (output / "artifacts" / "retained29" / route / relative,
                      output / "skills" / "retained29" / route / relative,
                      output / "retained29" / route / relative)
        for candidate in candidates:
            if candidate.is_file() and sha256(candidate.read_bytes()).digest() == sha256(content).digest():
                matches.append({"tool_call_id": call.get("id"), "retained_file": candidate.relative_to(output).as_posix(), "content_sha256": sha256(content).hexdigest(), "claim": "written_content_byte_equal_retained_artifact", "comparison_representation": "credential_sanitized_export"})
                break
    return matches


def export_training(episodes: list[dict], routes: list[dict], output_dir: Path) -> dict:
    """Export all available chains plus narrowly labelled action candidates.

    The loss mask must be compiled for a selected tokenizer later. Native
    protocol datasets preserve the exact visible prefix, without adding later
    review feedback or final artifacts to the model's historical context.
    """
    from build import clean_value

    output = Path(output_dir)
    canonical_dir, dataset_dir, audit_dir = (output / x for x in ("canonical", "datasets", "training_audit"))
    for directory in (canonical_dir, dataset_dir, audit_dir):
        directory.mkdir(parents=True, exist_ok=True)
    stats: Counter = Counter()
    reasons: Counter = Counter()
    lengths = []
    route_map = {r.get("id", r.get("route_id", "")): r for r in routes}
    recovered_schema_path = Path(__file__).parent / "resources" / "native_coding_tools_97a0.json"
    recovered_schemas, _ = _schema_map(recovered_schema_path)
    paths = []
    with ExitStack() as stack:
        canonical = stack.enter_context(gzip.open(canonical_dir / "native_episodes.jsonl.gz", "wt", encoding="utf-8", newline="\n", compresslevel=3))
        action_index = stack.enter_context((audit_dir / "action_index.jsonl").open("w", encoding="utf-8", newline="\n"))
        review_index = stack.enter_context((audit_dir / "review_queue.jsonl").open("w", encoding="utf-8", newline="\n"))
        writers = {}
        for name in ("native_protocol_actions", "native_actions", "final_candidates", "artifact_verified_write", "auxiliary"):
            for split in SPLITS:
                path = dataset_dir / f"{name}.{split}.jsonl.gz"
                writers[name, split] = stack.enter_context(gzip.open(path, "wt", encoding="utf-8", newline="\n", compresslevel=3))
                paths.append(path.relative_to(output).as_posix())

        def emit(name: str, split: str, row: dict) -> None:
            writers[name, split].write(_json(clean_value(row)) + "\n")
            stats[f"{name}.{split}"] += 1

        for episode in episodes:
            stats["episodes_seen"] += 1
            source = Path(episode.get("source_path", ""))
            transport = source / "openclaw_transport"
            messages, lines, message_stats = _messages(transport / "session_events.jsonl")
            stats.update(message_stats)
            context_recoverable = not (message_stats["malformed_event_lines"] or message_stats["unknown_message_role"])
            if not messages:
                stats["episodes_without_messages"] += 1
                continue
            # Derive every representation from the same sanitized native
            # objects. Sanitizing a dict and its serialized JSON string in
            # different orders can otherwise leave escaped credentials behind
            # or produce different historical prefixes in the two exports.
            messages = clean_value(messages)
            prompts = _load(transport / "evidence" / "prompts.json", {})
            system = prompts.get("system") if isinstance(prompts, dict) else None
            system_path = transport / "evidence" / "system-prompt.txt"
            if not isinstance(system, str) and system_path.is_file():
                system = system_path.read_text(encoding="utf-8-sig")
            system = clean_value(system)
            schema_file = Path(episode["tools_path"]) if episode.get("tools_path") else transport / "evidence" / "tools.json"
            schemas, schema_stats = _schema_map(schema_file)
            stats.update(schema_stats)
            actual_schema_names = set(schemas)
            if episode.get("native_verified") is True:
                for tool_name, schema in recovered_schemas.items():
                    schemas.setdefault(tool_name, schema)
            benchmark = _benchmark_exposed(messages)
            original_split = episode.get("split", "quarantine")
            original_split = original_split if original_split in SPLITS else "quarantine"
            native = episode.get("native_verified") is True
            split = original_split if native and not benchmark else "quarantine"
            episode_id = str(episode.get("episode_id", episode.get("job_id", source.as_posix())))
            route_id = episode.get("route_id", "")
            route = route_map.get(route_id, {})
            metadata = {key: episode.get(key) for key in ("job_id", "kind", "route_id", "status", "attempt", "archive_path", "source_ids", "component_id")}
            metadata.update({"episode_id": episode_id, "split": split, "source_split": original_split, "native_verified": native, "benchmark_exposed": benchmark, "route_library_status": route.get("library_status"), "route_status_is_not_action_approval": True})
            full = {"schema_version": "wrd-native-trajectory-v1", **metadata, "system": system, "messages": messages, "source_event_lines": lines, "reasoning_exported": False, "messages_sanitized_before_derivation": True, "context_fully_recoverable": context_recoverable, "message_parse_issues": {key: message_stats[key] for key in ("malformed_event_lines", "unknown_message_role") if message_stats[key]}, "tools_definition_path": (str(episode.get("archive_path", "")) + "/openclaw_transport/evidence/tools.json"), "complete_tool_schema_names": sorted(schemas), "recovered_tool_schema_names": sorted(set(schemas) - actual_schema_names), "requires_private_storage": True}
            canonical.write(_json(clean_value(full)) + "\n")
            stats["canonical_episodes"] += 1
            stats["canonical_messages"] += len(messages)
            stats["benchmark_exposed_episodes"] += int(benchmark)
            prefix = []
            if isinstance(system, str) and system:
                cleaned_system, _, _ = _clean_content(system)
                prefix.append({"role": "system", "content": cleaned_system})
            primary = episode.get("kind") in ("make", "screen")
            auxiliary = not primary
            for index, message in enumerate(messages):
                if message["role"] != "assistant":
                    prefix.append(message)
                    continue
                stats["assistant_targets_seen"] += 1
                identifier = sha256((episode_id + ":" + str(index)).encode()).hexdigest()[:24]
                calls = _calls(message)
                row = {"schema_version": "wrd-completion-candidate-v1", "id": identifier, **metadata, "target_message_index": index, "target_event_line": lines[index], "prompt_end_message_exclusive": index, "canonical_ref": "canonical/native_episodes.jsonl.gz", "semantic_review": "pending", "loss_scope": "completion_only_requires_target_tokenizer_compiler", "token_count": None, "reward": None, "online_policy_rollout": False}
                rejects = []
                if not native:
                    rejects.append("native_environment_unverified")
                if not context_recoverable:
                    rejects.append("context_not_fully_recoverable")
                if split == "quarantine":
                    rejects.append("quarantined_component_or_benchmark_exposure")
                if episode.get("status") not in ("done", "completed", "COMPLETED"):
                    rejects.append("episode_not_success_terminal")
                if not isinstance(system, str) or not system:
                    rejects.append("missing_system_context")
                if any(x.get("_multimodal") for x in prefix) or message.get("_multimodal"):
                    rejects.append("multimodal_context_requires_media_adapter")
                if not any(x.get("role") == "user" for x in prefix):
                    rejects.append("missing_user_context")
                if not _protocol_valid(prefix):
                    rejects.append("incomplete_historical_tool_pairing")
                if calls:
                    rejects.extend(_target_call_id_errors(calls, prefix))
                    following = []
                    for later in messages[index + 1:]:
                        if later["role"] == "assistant":
                            break
                        following.append(later)
                    result_map = {}
                    for result in following:
                        if result["role"] in ("toolResult", "tool"):
                            result_map.setdefault(result.get("toolCallId"), []).append(result)
                    for call in calls:
                        linked = result_map.get(call.get("id"), [])
                        if len(linked) != 1:
                            rejects.append("missing_or_duplicate_target_tool_result")
                        elif linked[0].get("toolName") not in (None, call.get("name")):
                            rejects.append("tool_name_result_mismatch")
                        else:
                            success, reason = _result_success(linked[0], str(call.get("name", "")))
                            if not success:
                                rejects.append(reason)
                elif not _text(message).strip():
                    rejects.append("empty_assistant_target")
                action = {**row, "tool_call_names": [x.get("name") for x in calls], "filter_reasons": sorted(set(rejects)), "target_kind": "tool_calls" if calls else "final_text_candidate"}
                action_index.write(_json(clean_value(action)) + "\n")
                reasons.update(set(rejects))
                if rejects:
                    stats["targets_filtered"] += 1
                    prefix.append(message)
                    continue
                if auxiliary:
                    emit("auxiliary", split, {**action, "use": "auxiliary_evidence_not_primary_skill_builder_sft"})
                    prefix.append(message)
                    continue
                target = {key: value for key, value in message.items() if key not in ("details", "timestamp", "stopReason", "_multimodal")}
                candidate = {**action, "prompt": list(prefix), "completion": [target], "prompt_characters": len(_json(prefix)), "completion_characters": len(_json(target)), "label": "execution_verified_candidate" if calls else "unverified_final_answer_candidate", "teacher_forced_history": True, "context_is_actual_past_prefix": context_recoverable, "tool_schema_status": "pending"}
                lengths.append(candidate["prompt_characters"] + candidate["completion_characters"])
                review_index.write(_json(clean_value({**action, "proposed_label": candidate["label"], "approval": None, "reviewer": None, "review_notes": None})) + "\n")
                if calls:
                    emit("native_protocol_actions", split, candidate)
                    used_tools = {call.get("name") for old in prefix + [message] for call in _calls(old)}
                    missing = sorted(str(name) for name in used_tools if name not in schemas)
                    openai = None
                    if not missing:
                        recovered_used = sorted(used_tools - actual_schema_names)
                        openai = {**candidate, "schema_version": "wrd-openai-tool-completion-v1", "prompt": [_openai_message(old) for old in prefix], "completion": [_openai_message(message)], "tools": [schemas[name] for name in sorted(used_tools)], "tool_schema_status": "complete_for_all_observed_prefix_and_target_calls", "tool_schema_source": "recovered_from_frozen_native_image" if recovered_used else "actual_episode_export", "recovered_tool_names": recovered_used, "tool_access_policy_reconstructed": False}
                        emit("native_actions", split, openai)
                    else:
                        stats["native_action_schema_pending"] += 1
                    if episode.get("kind") == "make":
                        matches = _artifact_match(calls, route_id, output)
                        if matches:
                            emit("artifact_verified_write", split, {**(openai or candidate), "label": "artifact_byte_verified_write_candidate", "artifact_evidence": matches, "semantic_review": "byte_match_verified_not_global_semantic_approval"})
                else:
                    emit("final_candidates", split, candidate)
                prefix.append(message)

    lengths.sort()
    length_stats = {"unit": "unicode_characters_of_serialized_native_prompt_plus_completion_without_tools_or_target_chat_template_not_tokens", "count": len(lengths), "min": lengths[0] if lengths else None, "median": lengths[len(lengths) // 2] if lengths else None, "p95": lengths[min(len(lengths) - 1, int(len(lengths) * .95))] if lengths else None, "max": lengths[-1] if lengths else None, "truncated_examples": 0}
    result = {"schema_version": "wrd-training-export-v1", "counts": dict(sorted(stats.items())), "filter_reasons": dict(sorted(reasons.items())), "lengths": length_stats, "dataset_paths": paths, "canonical_path": "canonical/native_episodes.jsonl.gz", "action_index": "training_audit/action_index.jsonl", "semantic_review_queue": "training_audit/review_queue.jsonl", "gold_approved_actions": 0, "compiled_token_masks": False, "weights_trained": False, "benchmark_prohibition_ignored_only_for_detection": BENCHMARK_PROHIBITION, "recovered_tool_schema_resource": recovered_schema_path.name if recovered_schemas else None, "notes": ["Only make/screen are primary builder candidates; actor/prepare/review are auxiliary.", "Execution success and retained artifact byte equality are explicit limited labels, not blanket semantic approval.", "No future review, final artifact, or performance result is inserted in historical prompts.", "Quarantined and formally benchmark-exposed episodes are archived but excluded from primary SFT candidates.", "The exact fixed prohibition against accessing the formal test set is not considered exposure; original prompts are unchanged.", "Absence of benchmark markers is not proof of no semantic or feedback leakage.", "Recovered coding schemas describe fixed-image tool definitions, not a recreated episode-specific access policy.", "No tokenizer, context truncation, online GRPO rollout, or DPO pairs are fabricated."]}
    (audit_dir / "training_export_report.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result
