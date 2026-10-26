"""Offline structural/process quality census of all1763 old native histories.

No admission filter is applied. Outcome flags and temporal repair candidates are
observations, never business-quality gold or evidence of autonomous A-D control.
"""
from __future__ import annotations

import array
import bisect
import collections
import gzip
import hashlib
import json
import math
import re
import shutil
import sys
import time
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "output/20261026_wrd_quality_v8"
OLD = ROOT / "output/20261025_wrd_training_dataset/bundle"
V4 = ROOT / "output/20261025_wrd_reasoning_recovery_v4/native_compiled_controlled_final"
V6 = ROOT / "output/20261026_wrd_lineage_v6/controlled"
V7 = ROOT / "output/20261026_wrd_raw_census_v7"
CORE7 = {"ls", "read", "edit", "write", "apply_patch", "exec", "process"}


def js(x):
    return json.dumps(x, ensure_ascii=False, separators=(",", ":"))


def sha(x):
    return hashlib.sha256(x if isinstance(x, bytes) else x.encode()).hexdigest()


def file_sha(p):
    h = hashlib.sha256()
    with Path(p).open("rb") as f:
        for b in iter(lambda: f.read(1024 * 1024), b""):
            h.update(b)
    return h.hexdigest()


def rows(p):
    op = gzip.open if str(p).endswith(".gz") else open
    with op(p, "rt", encoding="utf-8-sig") as f:
        for line in f:
            if line.strip():
                yield json.loads(line)


def pin(p):
    return {"path": str(p), "sha256": file_sha(p), "bytes": Path(p).stat().st_size}


def summary(values):
    a = sorted(x for x in values if x is not None)
    if not a:
        return {"count": 0}
    q = lambda p: a[min(len(a) - 1, int((len(a) - 1) * p))]
    return {"count": len(a), "sum": sum(a), "min": a[0], "median": q(.5), "p90": q(.9), "p95": q(.95), "p99": q(.99), "max": a[-1]}


def texts(m):
    c = m.get("content")
    if isinstance(c, str):
        return c
    return "\n".join(str(b.get("text", "")) for b in c if isinstance(b, dict) and b.get("type") == "text") if isinstance(c, list) else ""


def calls(m):
    return [b for b in m.get("content", []) if isinstance(b, dict) and b.get("type") == "toolCall"] if isinstance(m.get("content"), list) else []


def arguments(c):
    a = c.get("arguments")
    if isinstance(a, str):
        try:
            return json.loads(a), None
        except ValueError:
            return None, "arguments_string_not_JSON"
    return a, None


def outcome(m):
    d = m.get("details") if isinstance(m.get("details"), dict) else {}
    text = texts(m)
    code = d.get("exitCode")
    status = d.get("status")
    return {
        "is_error_true": m.get("isError") is True,
        "is_error_missing": "isError" not in m,
        "nonzero_exit": isinstance(code, (int, float)) and not isinstance(code, bool) and code != 0,
        "exit_code": code if isinstance(code, (int, float, type(None))) else None,
        "status": status if isinstance(status, (int, str, type(None))) else None,
        "running_status": status == "running",
        "failure_status": status in ("error", "failed", "not_found", "no_answer"),
        "persisted_details_truncated": d.get("persistedDetailsTruncated") is True,
        "visible_truncation_marker": bool(re.search(r"\[Truncated\]|<truncated>|\.\.\.\s*\[truncated\]|output truncated", text, re.I)),
        "exec_failure_word_proxy": m.get("toolName") in ("exec", "process") and bool(re.search(r"Traceback \(most recent call last\)|\b(?:SyntaxError|ModuleNotFoundError|AssertionError|FAILED|FAIL)\b", text)),
        "result_visible_characters": len(text),
    }


def normalized_target(m):
    cc = [{"name": c.get("name"), "arguments": c.get("arguments")} for c in calls(m)]
    s = unicodedata.normalize("NFKC", js({"text": texts(m), "calls": cc}))
    s = s.replace("\\\\", "/")
    s = re.sub(r"\b(?:conv|ep)_[0-9a-f]+\b|\b[0-9a-f]{16,}\b|\b[0-9a-f]{8}-[0-9a-f-]{27,}\b", "<ID>", s, flags=re.I)
    s = re.sub(r"(?:[A-Za-z]:/|/(?:workspace|tmp|mnt|home|root)/)[^\s\"']+", "<PATH>", s)
    s = re.sub(r"\b\d+(?:\.\d+)?\b", "<N>", s)
    return re.sub(r"\s+", " ", s).strip()


def decision_carriers(m):
    """Original JSON fields only; presence does not certify the decision."""
    candidates = [("assistant_visible_text", texts(m))]
    for c in calls(m):
        a, _ = arguments(c)
        if c.get("name") == "write" and isinstance(a, dict):
            candidates.append(("write_tool_content", a.get("content")))
    evidence = []
    fields = {"decision", "verdict", "reuse_decision", "retention_decision", "final_decision", "next_action", "retain", "keep", "revise"}
    enums = {"retain", "revise", "reject", "stop", "continue", "reuse", "skip", "merge", "update", "finish_ready", "no_value", "keep", "candidate", "new_skill", "reuse_existing"}
    for origin, text in candidates:
        if not isinstance(text, str):
            continue
        stripped = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.I)
        try:
            value = json.loads(stripped)
        except ValueError:
            continue
        pending, examined = [("", value)], 0
        while pending and examined < 2000:
            path, node = pending.pop()
            examined += 1
            if isinstance(node, dict):
                for key, child in node.items():
                    normalized = str(key).lower()
                    if normalized in fields:
                        enum = str(child).lower() if isinstance(child, (str, bool)) else None
                        evidence.append({"origin": origin, "json_key": normalized, "json_path_depth": path.count("/") + 1, "value_sha256": sha(js(child)), "safe_enum": enum if enum in enums or isinstance(child, bool) else None})
                    if isinstance(child, (dict, list)) and path.count("/") < 8:
                        pending.append((path + "/" + str(key), child))
            elif isinstance(node, list) and path.count("/") < 8:
                pending.extend((path + "/[]", child) for child in node[:100] if isinstance(child, (dict, list)))
    return evidence


def system_capture_artifacts(episode_ids):
    counts, variants = collections.Counter(), {}
    for row in rows(OLD / "archive/file_index.jsonl"):
        path = row["logical_path"]
        parts = path.split("/")
        if len(parts) != 5 or parts[0] != "episodes" or parts[1] not in episode_ids or parts[2:4] != ["openclaw_transport", "evidence"] or parts[4] not in ("system-prompt.txt", "prompts.json", "tools.json"):
            continue
        counts[parts[4]] += 1
        if parts[4] == "system-prompt.txt" and row["sha256"] not in variants:
            raw = (OLD / "archive" / row["object"]).read_bytes()
            assert sha(raw) == row["sha256"]
            text = raw.decode("utf-8-sig")
            variants[row["sha256"]] = {"sha256": row["sha256"], "bytes": len(raw), "characters": len(text), "truncation_marker": "<truncated>" in text, "malformed_diagnostic_placeholder": "[Malformed diagnostic JSON redacted]" in text}
    return {"direct_same_episode_artifact_counts": dict(counts), "system_text_content_variants": list(variants.values()), "complete_system_from_this_txt_alternative_not_found": all(v["truncation_marker"] or v["malformed_diagnostic_placeholder"] for v in variants.values()), "not_a_global_absence_claim": True, "wire_or_fixed_runtime_recovery_requires_exact_same_episode_identity": True}


def external_model_hints(c):
    """Read-only parameter-string hints; never execute or equate to API bills."""
    s = js(c.get("arguments"))
    modes = re.findall(r"ecnu_tools(?:\.py)?(?:\\?['\"])?\s+(text|vision|image|speech|asr|tts)\b", s, flags=re.I)
    modes += re.findall(r"ecnu_tools(?:\.py)?[^\n]{0,120}?(?:--mode|--task)\s+(text|vision|image|speech|asr|tts)\b", s, flags=re.I)
    clients = []
    for name, pattern in {
        "OpenAI_client_literal": r"\b(?:AsyncOpenAI|OpenAI)\s*\(|from\s+openai\s+import|import\s+openai\b",
        "Anthropic_client_literal": r"\b(?:AsyncAnthropic|Anthropic)\s*\(|import\s+anthropic\b",
        "LiteLLM_literal": r"\blitellm\b",
        "chat_completion_method": r"\.chat\.completions\.create\s*\(",
        "responses_method": r"\.responses\.create\s*\(",
        "model_API_endpoint_literal": r"/(?:v1/)?(?:chat/completions|responses|images/generations|audio/(?:speech|transcriptions))\b",
        "image_generation_method": r"\.images\.(?:generate|edit|create_variation)\s*\(",
        "speech_generation_method": r"\.audio\.speech\.create\s*\(",
        "speech_recognition_method": r"\.audio\.transcriptions\.create\s*\(",
    }.items():
        if re.search(pattern, s, flags=re.I):
            clients.append(name)
    ecnu = bool(re.search(r"ecnu_tools(?:\.py)?", s, flags=re.I))
    return {"ecnu_tools_parameter_mentions": len(re.findall(r"ecnu_tools(?:\.py)?", s, flags=re.I)), "explicit_ecnu_mode_command_occurrences": dict(collections.Counter(m.lower() for m in modes)), "equivalent_client_literal_hints": clients, "external_vision_input_literal_hint": bool((ecnu or clients) and re.search(r"image_url|input_image|\bvision\b", s, flags=re.I)), "sessions_spawn_tool_block": c.get("name") == "sessions_spawn", "skill_workshop_tool_block_model_cost_unknown": c.get("name") == "skill_workshop", "possible_external_model_dependency": ecnu or bool(clients) or c.get("name") in ("sessions_spawn", "skill_workshop"), "not_actual_API_call_count": True}


def approximate_near_groups(groups):
    """Bounded operational repetition proxy, not semantic deduplication."""
    import numpy as np
    buckets = collections.defaultdict(list)
    sketches, lengths, edges = {}, {}, []
    comparisons = capped = short = 0
    for key in sorted(groups):
        item = groups[key]
        s = item["normalized"]
        if len(s) < 80:
            short += 1
            continue
        sample = s[:4096]
        hs = {int.from_bytes(hashlib.blake2b(sample[i:i + 5].encode(), digest_size=8).digest(), "little") for i in range(max(0, len(sample) - 4))}
        sketch = set(sorted(hs)[:128])
        if not sketch:
            continue
        arr = np.array(sorted(sketch), dtype="<u8")
        bits = np.unpackbits(arr.view(np.uint8)).reshape(-1, 64).sum(axis=0) >= len(arr) / 2
        sig = int.from_bytes(np.packbits(bits).tobytes(), "little")
        candidates = set()
        for band in range(4):
            values = buckets[(item["role"], band, (sig >> (16 * band)) & 65535)]
            if len(values) > 1000:
                capped += 1
            candidates.update(values[-1000:])
        for other in sorted(candidates):
            if comparisons >= 200000:
                capped += 1
                break
            comparisons += 1
            osig, ohs = sketches[other]
            if (sig ^ osig).bit_count() > 3 or min(len(s), lengths[other]) / max(len(s), lengths[other]) < .8:
                continue
            overlap = len(sketch & ohs) / len(sketch | ohs)
            if overlap >= .9:
                edges.append({"normalized_group_a": other, "normalized_group_b": key, "simhash_hamming": (sig ^ osig).bit_count(), "bottom128_shingle_overlap": overlap, "representative_target_a": groups[other]["ids"][0], "representative_target_b": item["ids"][0]})
        sketches[key] = (sig, sketch)
        lengths[key] = len(s)
        for band in range(4):
            buckets[(item["role"], band, (sig >> (16 * band)) & 65535)].append(key)
    return edges, {"unique_normalized_groups_examined": len(groups), "short_under80_char_groups_not_compared": short, "candidate_comparisons": comparisons, "candidate_or_comparison_cap_events": capped, "near_edges": len(edges), "scope": "same corrected role; normalized first4096 characters; bottom128 character5-shingle sketch; SimHash64 four16-bit bands, hamming<=3, length ratio>=.8, sketch overlap>=.9; <=1000 candidates/band and200000 comparisons", "not_exhaustive_or_semantic_duplicate_rate": True}


def main():
    started = time.time()
    OUT.mkdir(parents=True, exist_ok=True)
    if (OUT / "NATIVE_QUALITY.json").exists():
        previous = OUT / "history" / ("native_quality_" + file_sha(OUT / "NATIVE_QUALITY.json"))
        previous.mkdir(parents=True, exist_ok=True)
        shutil.copy2(OUT / "NATIVE_QUALITY.json", previous / "NATIVE_QUALITY.json")
    controlled = OUT / "controlled"
    controlled.mkdir(exist_ok=True)
    source_files = [OLD / "canonical/native_episodes.jsonl.gz", OLD / "archive/file_index.jsonl", V4 / "full_stage_records.jsonl.gz", V4 / "target_inventory.jsonl.gz", V6 / "lineage_episode_decisions.jsonl.gz", V7 / "indexes/episodes.all.jsonl.gz", V7 / "EXPORT_COVERAGE_AUDIT.json"]
    pins = [pin(p) for p in source_files]
    catalogue = {r["episode_id"]: r for r in rows(V7 / "indexes/episodes.all.jsonl.gz")}
    lineage = {r["episode_id"]: r for r in rows(V6 / "lineage_episode_decisions.jsonl.gz")}
    target_meta = {(r["episode_id"], r["source_message_index"]): r for r in rows(V4 / "target_inventory.jsonl.gz")}
    from transformers import AutoTokenizer
    assets = ROOT / "output/20261025_wrd_training_preflight/tokenizer_assets"
    header_encodings = {}
    asset_pins = {}
    for key in ("primary_14b", "control_8b"):
        tokenizer = AutoTokenizer.from_pretrained(assets / key, local_files_only=True, trust_remote_code=False)
        header_encodings[key] = tokenizer.encode("<|im_start|>assistant\n", add_special_tokens=False)
        asset_pins[key] = {n: file_sha(assets / key / n) for n in ("tokenizer_config.json", "tokenizer.json", "vocab.json", "merges.txt")}
    assert header_encodings["primary_14b"] == header_encodings["control_8b"] and asset_pins["primary_14b"] == asset_pins["control_8b"]
    header = header_encodings["primary_14b"]
    schemas, schema_defs, episode_compile = {}, {}, {}
    token_lengths, serialization_checks, pair_proof_counts = {}, collections.Counter(), collections.Counter()
    for r in rows(V4 / "full_stage_records.jsonl.gz"):
        eid = r["episode_id"]
        ids = r["input_ids"]
        buf = array.array("I", ids)
        if sys.byteorder != "little":
            buf.byteswap()
        assert sha(buf.tobytes()) == r["input_ids_sha256_u32le"] and len(ids) == r["total_tokens"]
        starts = [i for i, token in enumerate(ids) if token == header[0] and ids[i:i + len(header)] == header]
        serialization_checks["stage_input_id_hash_and_length_match"] += 1
        serialization_checks["prior_second_tokenizer_proof_independent_call_equal"] += r.get("tokenizer_pair_proof") == "independent_call_equal"
        pair_proof_counts[str(r.get("tokenizer_pair_proof"))] += 1
        matching = len(starts) == len(r["targets"])
        serialization_checks["stage_assistant_header_count_matches_targets"] += matching
        for i, t in enumerate(r["targets"]):
            begin = starts[i] + len(header) if matching else None
            end = t["response_end_token_exclusive"]
            if begin is not None:
                assert begin <= end <= len(ids)
            token_lengths[eid, t["source_message_index"]] = {"serialized_prompt_tokens_before_assistant_body": begin, "serialized_target_body_with_controls_tokens": end - begin if begin is not None else None, "serialized_causal_end_tokens": end, "original_full_stage_tokens": len(ids), "body_start_recovered_from_existing_input_ids": matching}
        registry = {}
        for tool in r["tools"]:
            fn = tool.get("function", {}) if isinstance(tool, dict) else {}
            if not fn.get("name") or not isinstance(fn.get("parameters"), dict):
                continue
            h = sha(js(fn["parameters"]))
            schema_defs[h] = fn["parameters"]
            registry[fn["name"]] = h
        schemas[eid] = registry
        episode_compile[eid] = {"total_tokens": len(ids), "tool_catalog_completeness": r["original_tool_catalog_completeness"], "tool_schema_names_available_in_reused_serialization": sorted(registry), "text_projection_issues": r.get("text_projection_issues", {}), "historical_condition": r.get("historical_condition")}
    from jsonschema import Draft202012Validator
    validators = {h: Draft202012Validator(s) for h, s in schema_defs.items()}
    all_targets, all_episodes, duplicate_content, duplicate_payload, normalized_groups = [], [], collections.defaultdict(list), collections.defaultdict(list), {}
    episode_input_groups, episode_trajectory_groups = collections.defaultdict(list), collections.defaultdict(list)
    raw_event_checks = collections.Counter()
    global_counts = collections.Counter()
    for episode in rows(OLD / "canonical/native_episodes.jsonl.gz"):
        eid = episode["episode_id"]
        cat = catalogue[eid]
        source = lineage[eid]
        role = cat["role_hint_separate_from_raw_catalog_kind"]
        provenance = cat["raw_native_session"]
        raw = Path(provenance["CAS_path"]).read_bytes()
        assert sha(raw) == provenance["sha256"]
        raw_event_checks["CAS_hash_matched_sessions"] += 1
        custom = collections.Counter()
        thinking_levels = collections.Counter()
        native_line_roles = {}
        for number, line in enumerate(raw.decode("utf-8-sig").split("\n"), 1):
            if not line.strip():
                continue
            event = json.loads(line)
            if event.get("type") == "custom_message":
                custom[str(event.get("customType"))] += 1
            if event.get("type") == "thinking_level_change":
                thinking_levels[str(event.get("thinkingLevel", event.get("level")))] += 1
            if event.get("type") == "message":
                native_line_roles[number] = event.get("message", {}).get("role")
        for m, line in zip(episode["messages"], episode["source_event_lines"]):
            assert native_line_roles[line] == m["role"]
        raw_event_checks["all_canonical_message_event_line_roles_match_sessions"] += 1
        messages = episode["messages"]
        nontext_blocks = collections.Counter()
        for observed_message in messages:
            if isinstance(observed_message.get("content"), list):
                for block in observed_message["content"]:
                    if isinstance(block, dict) and block.get("type") not in ("text", "toolCall"):
                        nontext_blocks[str(block.get("type"))] += 1
        assistant_indices = [i for i, m in enumerate(messages) if m["role"] == "assistant"]
        result_indices = [i for i, m in enumerate(messages) if m["role"] in ("toolResult", "tool")]
        results_by_id = collections.defaultdict(list)
        calls_by_id = collections.defaultdict(list)
        for i in result_indices:
            results_by_id[messages[i].get("toolCallId")].append(i)
        for i in assistant_indices:
            for c in calls(messages[i]):
                calls_by_id[c.get("id")].append(i)
        ep_targets = []
        ep_counts = collections.Counter()
        previous_normalized, last_failure_index, consecutive_polls = None, None, 0
        for ordinal, index in enumerate(assistant_indices):
            m = messages[index]
            meta = target_meta[eid, index]
            assert sha(js(m)) == meta["source_message_sha256"]
            next_index = assistant_indices[ordinal + 1] if ordinal + 1 < len(assistant_indices) else len(messages)
            cc, text = calls(m), texts(m)
            links, call_summaries, issues = [], [], []
            mutation = any(c.get("name") in ("write", "edit", "apply_patch") for c in cc)
            poll = False
            result_flags = []
            for c in cc:
                cid, name = c.get("id"), c.get("name")
                args, arg_issue = arguments(c)
                if not isinstance(cid, str) or not cid:
                    issues.append("call_id_missing_or_nonstring")
                if len(calls_by_id[cid]) != 1:
                    issues.append("call_id_reused_in_episode")
                linked = results_by_id.get(cid, [])
                local = [j for j in linked if index < j < next_index]
                if len(linked) > 1:
                    issues.append("multiple_results_for_call_id")
                if not linked:
                    issues.append("no_recorded_result_for_call")
                elif not local:
                    issues.append("result_not_before_next_assistant")
                for j in linked:
                    if j <= index:
                        issues.append("result_not_after_call")
                    if messages[j].get("toolName") not in (None, name):
                        issues.append("call_result_tool_name_mismatch")
                    flags = outcome(messages[j])
                    result_flags.append(flags)
                    links.append({"message_index": j, "source_event_line": episode["source_event_lines"][j], "tool_name": messages[j].get("toolName"), "message_sha256": sha(js(messages[j])), "outcome": flags})
                schema = schemas[eid].get(name)
                schema_error = None
                if arg_issue:
                    schema_error = arg_issue
                elif not schema:
                    schema_error = "schema_not_in_recovered_registry"
                else:
                    try:
                        err = next(validators[schema].iter_errors(args), None)
                        schema_error = "arguments_violate_recovered_schema" if err else None
                    except Exception:
                        schema_error = "schema_or_arguments_validator_unknown"
                if schema_error:
                    ep_counts[schema_error] += 1
                poll |= name == "process" and isinstance(args, dict) and args.get("action") == "poll"
                command = args.get("command", args.get("cmd", "")) if isinstance(args, dict) else ""
                call_summaries.append({"id_sha256": sha(str(cid)), "name": name, "arguments_sha256": sha(js(c.get("arguments"))), "arguments_characters": len(js(c.get("arguments"))), "schema_error": schema_error, "schema_available": bool(schema), "poll_action": name == "process" and isinstance(args, dict) and args.get("action") == "poll", "exec_write_keyword_proxy": name == "exec" and bool(re.search(r"write_text|write_bytes|writeFile|open\([^\n]+['\"](?:w|a)|\btee\b|cat\s*>|mkdir", str(command))), "external_model_hints": external_model_hints(c)})
            observed_failure = any(f["is_error_true"] or f["nonzero_exit"] or f["failure_status"] for f in result_flags)
            poll_running = poll and any(f["running_status"] for f in result_flags)
            nonempty = bool(text.strip()) or bool(cc)
            visible_truncation = bool(re.search(r"\[Truncated\]|<truncated>|trajectory-depth-limit", text))
            incomplete_stop = nonempty and str(m.get("stopReason")) not in ("stop", "toolUse", "None")
            norm_text = normalized_target(m)
            normalized_id = sha(role + "\n" + norm_text)
            exact_id = sha(js({"content": m.get("content")}))
            payload_id = sha(js({"text": text, "calls": [{"name": c.get("name"), "arguments": c.get("arguments")} for c in cc]}))
            decision_fields = decision_carriers(m)
            tool_scope = "core7_only" if cc and all(c.get("name") in CORE7 for c in cc) else "noncore_only" if cc and all(c.get("name") not in CORE7 for c in cc) else "mixed_core_noncore" if cc else "text_only" if text.strip() else "empty"
            # Normalized signatures omit native call IDs; exact content includes
            # them. Both are context-insensitive repetition indicators only.
            same_as_previous = previous_normalized == normalized_id
            previous_normalized = normalized_id
            consecutive_polls = consecutive_polls + 1 if poll else 0
            temporal_after_failure = last_failure_index is not None
            target = {
                "id": meta["id"], "episode_id": eid, "source_message_index": index, "source_event_line": episode["source_event_lines"][index], "source_event_file": provenance["event_file"], "source_event_CAS": provenance["CAS_path"], "source_event_sha256": provenance["sha256"], "source_message_sha256": meta["source_message_sha256"],
                "old_catalog_stage": episode["kind"], "request_corrected_role": role, "route_id": episode["route_id"], "lineage_status": source["status"], "resource_closure_proven": source["resource_closure_proven"], "observed_evolution_source_ids": source["observed_evolution_source_ids"], "direct_protected_source_ids": source["direct_protected_source_ids"], "ancestor_protected": source["protected_ancestor_present"], "metadata_source_ids_not_actual_read_proof": episode.get("source_ids", []),
                "assistant_ordinal": ordinal + 1, "assistant_stop_reason": m.get("stopReason"), "nonempty": nonempty, "visible_text_characters": len(text), "native_payload_characters": len(js(m.get("content"))), "tool_calls": call_summaries, "result_links": links, "pairing_issues": sorted(set(issues)), "call_count": len(cc), "result_count": len(links), "current_exchange_structurally_paired": bool(cc) and len(links) == len(cc) and not issues,
                "observed_tool_failure": observed_failure, "result_failure_word_proxy": any(f["exec_failure_word_proxy"] for f in result_flags), "result_running": any(f["running_status"] for f in result_flags), "result_details_truncated": any(f["persisted_details_truncated"] for f in result_flags), "result_visible_truncation_marker": any(f["visible_truncation_marker"] for f in result_flags), "assistant_visible_truncation_marker": visible_truncation, "nonempty_incomplete_stop": incomplete_stop, "is_process_poll": poll, "poll_returned_still_running": poll_running, "consecutive_poll_position": consecutive_polls, "repeated_normalized_action_adjacent": same_as_previous,
                "explicit_write_edit_patch_tool": mutation, "has_visible_text_with_tool_call": bool(text.strip()) and bool(cc), "text_only_response": bool(text.strip()) and not cc, "following_any_earlier_tool_failure": temporal_after_failure, "explicit_mutation_after_earlier_failure_temporal_only": temporal_after_failure and mutation, "preceding_failure_target_message_index": last_failure_index, "is_last_assistant": ordinal == len(assistant_indices) - 1,
                "exact_native_content_group": exact_id, "normalized_operational_group": normalized_id, "normalization_is_not_semantic_equivalence": True,
                "exact_action_payload_group_without_native_call_ids": payload_id, "tool_set_scope": tool_scope, "prior_v4_positive_loss": meta["supervised_tokens"] > 0, "schema_unknown": any(c["schema_error"] == "schema_not_in_recovered_registry" for c in call_summaries), "arguments_invalid_under_recovered_schema": any(c["schema_error"] in ("arguments_violate_recovered_schema", "arguments_string_not_JSON") for c in call_summaries), "explicit_JSON_decision_field_proxy": bool(decision_fields), "original_JSON_decision_field_evidence_not_quality_gold": decision_fields,
                "possible_external_model_dependency_proxy": any(c["external_model_hints"]["possible_external_model_dependency"] for c in call_summaries),
                "lineage_label_scope": "existing_v6_episode_scope_not_target_prefix_proof",
                "prior_v4_mechanical_usable_not_semantic_gold": meta["mechanical_usable"], "prior_v4_mechanical_reasons": meta["mechanical_reasons"], "prior_v4_supervised_tokens_not_current_admission": meta["supervised_tokens"], **token_lengths[eid, index], "semantic_quality": "NOT_AUTOMATICALLY_ESTABLISHED", "training_admitted_by_this_audit": False,
            }
            duplicate_content[exact_id].append(meta["id"])
            duplicate_payload[payload_id].append(meta["id"])
            normalized_groups.setdefault(normalized_id, {"normalized": norm_text, "role": role, "ids": []})["ids"].append(meta["id"])
            for flag in ("nonempty", "current_exchange_structurally_paired", "observed_tool_failure", "result_failure_word_proxy", "result_running", "result_details_truncated", "result_visible_truncation_marker", "assistant_visible_truncation_marker", "nonempty_incomplete_stop", "is_process_poll", "poll_returned_still_running", "repeated_normalized_action_adjacent", "explicit_write_edit_patch_tool", "has_visible_text_with_tool_call", "text_only_response", "explicit_mutation_after_earlier_failure_temporal_only"):
                ep_counts[flag] += bool(target[flag])
            ep_counts["assistant_positions"] += 1
            ep_counts["tool_call_blocks"] += len(cc)
            ep_counts["targets_with_pairing_issue"] += bool(issues)
            ep_counts["max_consecutive_polls"] = max(ep_counts["max_consecutive_polls"], consecutive_polls)
            if observed_failure:
                last_failure_index = index
            ep_targets.append(target)
            all_targets.append(target)
        orphan_results = [i for i in result_indices if not any(j < i for j in calls_by_id.get(messages[i].get("toolCallId"), []))]
        last = ep_targets[-1] if ep_targets else None
        user_body = js([m.get("content") for m in messages if m["role"] == "user"])
        trajectory = js([{"role": m["role"], "content": m.get("content"), "toolName": m.get("toolName")} for m in messages])
        user_hash, trajectory_hash = sha(user_body), sha(trajectory)
        episode_input_groups[user_hash].append(eid)
        episode_trajectory_groups[trajectory_hash].append(eid)
        request_files = [r for r in cat["key_recording_files"] if r.get("logical_path", "").endswith(("/request.json", "/openclaw_transport/request.json"))]
        episode_row = {"episode_id": eid, "old_catalog_stage": episode["kind"], "request_corrected_role": role, "route_id": episode["route_id"], "job_id": episode["job_id"], "attempt": episode["attempt"], "recorded_status": episode["status"], "native_verified_metadata": episode["native_verified"], "source_event_file": provenance["event_file"], "source_event_CAS": provenance["CAS_path"], "source_event_sha256": provenance["sha256"], "lineage_status": source["status"], "resource_closure_proven": source["resource_closure_proven"], "observed_evolution_source_ids": source["observed_evolution_source_ids"], "direct_protected_source_ids": source["direct_protected_source_ids"], "ancestor_protected": source["protected_ancestor_present"], "metadata_source_ids_not_read_proof": episode.get("source_ids", []), "message_count": len(messages), "tool_result_messages": len(result_indices), "orphan_result_message_indices": orphan_results, "request_recorded_in_frozen_archive": bool(request_files), "request_protocol_recorded": bool(cat["original_request_interface"].get("protocol")), "request_file_refs": [{k: r[k] for k in ("logical_path", "physical_frozen_CAS_path", "stored_sha256")} for r in request_files], "system_recorded": bool(episode.get("system")), "system_visible_characters": len(episode.get("system") or ""), "system_truncation_marker": "<truncated>" in (episode.get("system") or ""), "system_malformed_placeholder": "[Malformed diagnostic JSON redacted]" in (episode.get("system") or ""), "raw_custom_message_counts_not_model_output": dict(custom), "thinking_level_metadata": dict(thinking_levels), "counts": dict(ep_counts), "last_assistant_nonempty": bool(last and last["nonempty"]), "last_assistant_stop_reason": last["assistant_stop_reason"] if last else None, "last_assistant_has_calls": bool(last and last["call_count"]), "complete_text_terminal_proxy": bool(last and last["nonempty"] and last["assistant_stop_reason"] == "stop" and not last["call_count"]), "exact_user_input_group": user_hash, "exact_full_trajectory_group_including_native_call_ids": trajectory_hash, **episode_compile[eid], "semantic_task_success": "NOT_ESTABLISHED_BY_STRUCTURE_OR_EXIT_CODE", "autonomous_full_pipeline_demonstration": False, "training_admitted_by_this_audit": False}
        all_episodes.append(episode_row)
        episode_row["recorded_nontext_content_block_types"] = dict(nontext_blocks)
        episode_row["lineage_label_scope"] = "existing_v6_episode_scope_not_target_prefix_proof"
        global_counts.update(ep_counts)
        global_counts["orphan_tool_result_messages"] += len(orphan_results)
    print(js({"phase": "full_native_structural_census", "episodes": len(all_episodes), "targets": len(all_targets)}), flush=True)
    near_edges, near_meta = approximate_near_groups(normalized_groups)
    target_by_id = {r["id"]: r for r in all_targets}
    near_ids = {r[k] for r in near_edges for k in ("representative_target_a", "representative_target_b")}
    for r in all_targets:
        r["exact_content_group_size"] = len(duplicate_content[r["exact_native_content_group"]])
        r["exact_action_payload_group_size_without_native_call_ids"] = len(duplicate_payload[r["exact_action_payload_group_without_native_call_ids"]])
        r["normalized_operational_group_size"] = len(normalized_groups[r["normalized_operational_group"]]["ids"])
        r["near_proxy_representative"] = r["id"] in near_ids
    def aggregate(items):
        c = collections.Counter()
        for r in items:
            c["targets"] += 1
            c["nonempty"] += r["nonempty"]
            for key in ("current_exchange_structurally_paired", "observed_tool_failure", "is_process_poll", "poll_returned_still_running", "has_visible_text_with_tool_call", "text_only_response", "explicit_write_edit_patch_tool", "explicit_mutation_after_earlier_failure_temporal_only", "result_details_truncated", "result_visible_truncation_marker", "nonempty_incomplete_stop", "repeated_normalized_action_adjacent"):
                c[key] += bool(r[key])
            c["pairing_issue_targets"] += bool(r["pairing_issues"])
            c["schema_gap_or_error_targets"] += any(t["schema_error"] for t in r["tool_calls"])
            c["schema_unknown_targets"] += r["schema_unknown"]
            c["arguments_invalid_under_recovered_schema_targets"] += r["arguments_invalid_under_recovered_schema"]
            c["prior_v4_positive_loss_targets"] += r["prior_v4_positive_loss"]
            c["prior_v4_zero_loss_targets"] += not r["prior_v4_positive_loss"]
            c["explicit_JSON_decision_field_proxy_targets"] += r["explicit_JSON_decision_field_proxy"]
            c["possible_external_model_dependency_proxy_targets"] += r["possible_external_model_dependency_proxy"]
            c["nonempty_causal_end_le16k"] += r["nonempty"] and r["serialized_causal_end_tokens"] <= 16384
            c["nonempty_causal_end_le32k"] += r["nonempty"] and r["serialized_causal_end_tokens"] <= 32768
            c["nonempty_nonpoll_causal_end_le32k"] += r["nonempty"] and not r["is_process_poll"] and r["serialized_causal_end_tokens"] <= 32768
            c["target_body_tokens_including_controls"] += r["serialized_target_body_with_controls_tokens"] or 0
            if r["is_process_poll"]:
                c["poll_target_body_tokens_including_controls"] += r["serialized_target_body_with_controls_tokens"] or 0
        return dict(c)
    groupings = {}
    for field in ("old_catalog_stage", "request_corrected_role", "lineage_status", "route_id", "tool_set_scope"):
        buckets = collections.defaultdict(list)
        for r in all_targets:
            buckets[r[field]].append(r)
        groupings[field] = {key: aggregate(value) for key, value in sorted(buckets.items())}
    for field in ("observed_evolution_source_ids", "direct_protected_source_ids"):
        buckets = collections.defaultdict(list)
        for r in all_targets:
            for sid in r[field]:
                buckets[sid].append(r)
        groupings[field + "_membership_not_disjoint"] = {key: aggregate(value) for key, value in sorted(buckets.items())}
    outputs = []
    def write_gz(name, items):
        p = controlled / name
        with gzip.open(p, "wt", encoding="utf-8", compresslevel=3) as f:
            for row in items:
                f.write(js(row) + "\n")
        outputs.append(pin(p))
    write_gz("native_targets.quality.jsonl.gz", all_targets)
    write_gz("native_episodes.quality.jsonl.gz", all_episodes)
    write_gz("native_near_duplicate_proxy_edges.jsonl.gz", near_edges)
    write_gz("native_exact_and_normalized_groups.jsonl.gz", [{"group_id": k, "scope": "exact_native_content", "target_ids": v} for k, v in duplicate_content.items() if len(v) > 1] + [{"group_id": k, "scope": "normalized_operational_template_not_semantic_equivalence", "target_ids": v["ids"]} for k, v in normalized_groups.items() if len(v["ids"]) > 1])
    write_gz("native_exact_action_payload_groups_without_call_ids.jsonl.gz", [{"group_id": k, "target_ids": v} for k, v in duplicate_payload.items() if len(v) > 1])
    strata = collections.defaultdict(list)
    for r in all_targets:
        category = "failure_then_mutation_temporal" if r["explicit_mutation_after_earlier_failure_temporal_only"] else "observed_failure" if r["observed_tool_failure"] else "poll" if r["is_process_poll"] else "visible_explanation_and_action" if r["has_visible_text_with_tool_call"] else "text_only" if r["text_only_response"] else "other_tool_action"
        strata[(r["request_corrected_role"], r["lineage_status"], category)].append(r)
    samples = []
    for key, candidates in sorted(strata.items()):
        selected = sorted(candidates, key=lambda r: r["id"])[:2]
        samples.append({"stratum": {"role": key[0], "lineage_status": key[1], "process_category": key[2]}, "population_targets": len(candidates), "selection": "deterministic two smallest target hashes; audit coverage sample, not a random unbiased quality estimate", "targets": [{k: r[k] for k in ("id", "episode_id", "source_message_index", "source_event_line", "source_event_CAS", "source_event_file", "source_message_sha256", "serialized_target_body_with_controls_tokens", "pairing_issues", "observed_tool_failure", "explicit_mutation_after_earlier_failure_temporal_only")} for r in selected]})
    sample_path = OUT / "NATIVE_REVIEW_SAMPLE_MANIFEST.json"
    sample_path.write_text(json.dumps({"schema_version": "wrd-native-v8-stratified-review-candidate-list", "strata": samples, "sampled_targets": sum(len(r["targets"]) for r in samples), "contains_no_original_message_body": True, "training_admission": False}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    outputs.append(pin(sample_path))
    agg = aggregate(all_targets)
    report = {"schema_version": "wrd-native-full-population-computable-quality-v8", "scope": "All1763 old parsed native histories/32342 assistant positions, regardless of old93/106 admission; not all175 physical roots or a global data-size upper bound.", "status": "COMPUTABLE_AUDIT_COMPLETE_SEMANTIC_QUALITY_NOT_ESTABLISHED", "source_pins": pins, "tokenizer_asset_sha256": asset_pins, "tokenizer_header_encoding_both_CPU": header_encodings, "length_evidence": "Existing full-stage input_ids rehashed; prior independent dual-tokenizer proof reused. Header positions recover every original assistant response length, including oldmask0. No overlapping-prefix retokenization or weights loaded.", "length_serialization_checks": dict(serialization_checks), "raw_CAS_event_checks": dict(raw_event_checks), "population": {"episodes": len(all_episodes), "assistant_positions": len(all_targets), "tool_calls": sum(r["call_count"] for r in all_targets), "tool_results": sum(r["tool_result_messages"] for r in all_episodes), "source_message_hashes_match_existing_inventory": len(all_targets), "all_original_targets_preserved_in_ledger": True}, "global_target_metrics": agg, "global_episode_metrics": {"request_recorded": sum(r["request_recorded_in_frozen_archive"] for r in all_episodes), "system_recorded": sum(r["system_recorded"] for r in all_episodes), "system_truncation_marker": sum(r["system_truncation_marker"] for r in all_episodes), "complete_text_terminal_proxy": sum(r["complete_text_terminal_proxy"] for r in all_episodes), "recorded_status_counts": dict(collections.Counter(r["recorded_status"] for r in all_episodes)), "last_assistant_stop_reason_counts": dict(collections.Counter(str(r["last_assistant_stop_reason"]) for r in all_episodes)), "episodes_with_any_pairing_issue": sum(r["counts"]["targets_with_pairing_issue"] > 0 or bool(r["orphan_result_message_indices"]) for r in all_episodes), "episodes_with_failures": sum(r["counts"]["observed_tool_failure"] > 0 for r in all_episodes), "episodes_with_failure_then_later_mutation_temporal_only": sum(r["counts"]["explicit_mutation_after_earlier_failure_temporal_only"] > 0 for r in all_episodes), "episodes_with_poll_run_at_least3": sum(r["counts"]["max_consecutive_polls"] >= 3 for r in all_episodes), "native_verified_metadata": sum(r["native_verified_metadata"] for r in all_episodes), "custom_message_counts_not_model_output": dict(sum((collections.Counter(r["raw_custom_message_counts_not_model_output"]) for r in all_episodes), collections.Counter()))}, "token_lengths": {"full_stage": summary(r["total_tokens"] for r in all_episodes), "serialized_prompt_before_target_body": summary(r["serialized_prompt_tokens_before_assistant_body"] for r in all_targets), "serialized_current_target_body_with_controls": summary(r["serialized_target_body_with_controls_tokens"] for r in all_targets), "causal_prefix_end": summary(r["serialized_causal_end_tokens"] for r in all_targets), "target_body_length_unknown": sum(r["serialized_target_body_with_controls_tokens"] is None for r in all_targets)}, "grouped_target_metrics": groupings, "duplicate_proxies": {"exact_native_content_unique_groups": len(duplicate_content), "exact_native_content_repeated_groups": sum(len(v) > 1 for v in duplicate_content.values()), "exact_native_content_repeat_occurrences_beyond_first": sum(len(v) - 1 for v in duplicate_content.values()), "normalized_operational_unique_groups": len(normalized_groups), "normalized_operational_repeated_groups": sum(len(v["ids"]) > 1 for v in normalized_groups.values()), "normalized_operational_repeat_occurrences_beyond_first": sum(len(v["ids"]) - 1 for v in normalized_groups.values()), "exact_user_input_episode_groups": len(episode_input_groups), "exact_user_input_repeated_episode_occurrences_beyond_first": sum(len(v) - 1 for v in episode_input_groups.values()), "exact_full_trajectory_unique_groups_including_native_call_ids": len(episode_trajectory_groups), "near_proxy": near_meta, "not_independent_task_or_semantic_deduplication_counts": True}, "source_boundary_interpretation": {"episode_statuses": dict(collections.Counter(r["lineage_status"] for r in all_episodes)), "HOLD_PROTECTED": "Existing v6 actual direct/resource-prefix protected evidence; not old prepare policy-string flags.", "HOLD_MISSING": "Resource/source lineage unproven; not proven protected and not a quality rejection.", "ADMIT": "Source/resource scope only, not semantic quality or full-pipeline readiness.", "source_id_lists_in_catalog": "Availability/route metadata are retained separately and not called actual read proof or independent task identity.", "fixed_original226_isolation_unchanged": True}, "interpretation_limits": ["A structurally paired successful tool call or exit0 is not task-quality gold, resource reliability, retention validity or autonomous skill-distillation success.", "A failed test/probe or running poll can be a valid training action. Temporal failure→edit candidates require semantic and version-bound receipt review; no repair success is inferred here.", "Visible assistant explanations may convey decision evidence; no claim that tool syntax alone teaches route selection, evaluation or full controller policy. Independent recorded reasoning is not fabricated from text.", "The recovered schema registry contains fixed-image tool definitions plus incomplete original placeholders. Schema coverage is recoverable-interface evidence, not proof of exact per-request original tool access policy.", "Persisted details truncation and visible output markers are counted separately; canonical logs cannot establish all omitted raw API/context bytes. Custom messages/aborted turns remain evidence, not fabricated assistant thoughts.", "Serialized causal lengths use the already declared v4 training template, not a claim that each native API request had this exact prefix or lacked native context management.", "Exact response repetitions can be appropriate under different contexts; normalized path/ID/number templates can merge behaviorally different code. Near-proxy edges are bounded operational similarity, not semantic equivalence and never an automatic deletion policy.", "Grouped source memberships overlap. Routes, attempts, repeated targets, resource versions and independent enterprise tasks are different units.", "This is a diagnostic all-population ledger and stratified review list, not a newly admitted SFT dataset or evidence that14B meets the complete autonomous goal."], "outputs": outputs, "training_started": False, "new_model_or_business_calls": 0, "GPU_used": False, "model_weights_loaded": False, "original_data_modified": False, "script_sha256": file_sha(__file__), "elapsed_seconds": round(time.time() - started, 3)}
    report["length_evidence"] = "All1763 existing full-stage input_id arrays rehashed; all32342 source message hashes and assistant body boundaries matched. Original proof modes:82 independent second-tokenizer calls,1681 deterministic reuse of byte-identical assets. This run independently checks both local asset sets/header encoding but does not recompile55M full-stage tokens or claim fresh dual calls for1763."
    report["tokenizer_pair_existing_proof_modes"] = dict(pair_proof_counts)
    report["context_length_scope_warning"] = "All16K/32K figures describe the old derived training representation's causal prefixes, not complete original native API requests. Captured system/tools are incomplete; same-episode wire/runtime recovery can increase lengths and requires final recompilation. Equal token/mask identity of the declared representation does not prove faithful recovery of all teacher schemas or student tool compatibility."
    report["capture_completeness"] = {
        "system_truncated_snapshot_episodes": sum(r["system_truncation_marker"] for r in all_episodes),
        "system_malformed_diagnostic_placeholder_episodes": sum(r["system_malformed_placeholder"] for r in all_episodes),
        "system_not_recorded_episodes": sum(not r["system_recorded"] for r in all_episodes),
        "request_protocol_metadata_recorded_episodes": sum(r["request_protocol_recorded"] for r in all_episodes),
        "same_episode_alternative_artifacts": system_capture_artifacts({r["episode_id"] for r in all_episodes}),
        "interpretation": "Capture-layer incompleteness, not a blanket semantic-quality rejection. Full wire records found in other sessions cannot be borrowed to fill these episodes. Exact same-identity recovery remains a separate task; all original process evidence is retained.",
        "recorded_nontext_content_block_types": dict(sum((collections.Counter(r["recorded_nontext_content_block_types"]) for r in all_episodes), collections.Counter())),
        "episodes_with_recorded_nontext_content_blocks": sum(bool(r["recorded_nontext_content_block_types"]) for r in all_episodes),
    }
    report["duplicate_proxies"].update({"exact_action_payload_excluding_call_ids_unique_groups": len(duplicate_payload), "exact_action_payload_excluding_call_ids_repeated_groups": sum(len(v) > 1 for v in duplicate_payload.values()), "exact_action_payload_excluding_call_ids_repeats_beyond_first": sum(len(v) - 1 for v in duplicate_payload.values()), "exact_action_payload_definition": "Original visible text plus original call names and exact arguments, omitting only generated native call IDs; identical actions in different contexts are not automatically redundant training records."})
    report["decision_field_proxy_definition"] = "Only parseable original assistant text or write-tool JSON content; keys decision/verdict/reuse_decision/retention_decision/final_decision/next_action/retain/keep/revise. Presence is a review locator, not proof of meaningful reasoning, correct choices or causal repair success. No teacher field was synthesized."
    report["core7_definition"] = sorted(CORE7)
    report["training_toolset_interpretation"] = "core7_only/noncore_only/text_only/empty target classes cover the whole population. Prior-v4 positive/zero loss and recovered-schema unknown/arguments-invalid counts are separately tabulated. No filtering to93/106 or claim that every teacher action fits a seven-tool student adapter."
    report["source_boundary_interpretation"]["label_granularity"] = "Existing v6 episode-scope status distribution only. A protected dependency later in an episode is not retrospective proof that every earlier target prefix saw it. This audit neither admits nor deletes targets using these episode labels; safe-prefix recovery needs exact temporal resource closure."
    report["source_boundary_interpretation"]["HOLD_MISSING_EVIDENCE"] = "Resource/source lineage unproven; not proven protected and not a semantic-quality rejection."
    external_counts, external_modes, external_client_hints = collections.Counter(), collections.Counter(), collections.Counter()
    external_refs = []
    for r in all_targets:
        for c in r["tool_calls"]:
            hint = c["external_model_hints"]
            external_counts["ecnu_tools_parameter_string_occurrences"] += hint["ecnu_tools_parameter_mentions"]
            external_counts["call_blocks_mentioning_ecnu_tools"] += hint["ecnu_tools_parameter_mentions"] > 0
            external_counts["call_blocks_with_equivalent_client_literal"] += bool(hint["equivalent_client_literal_hints"])
            external_counts["sessions_spawn_tool_blocks"] += hint["sessions_spawn_tool_block"]
            external_counts["skill_workshop_blocks_model_cost_unknown"] += hint["skill_workshop_tool_block_model_cost_unknown"]
            external_counts["external_vision_input_literal_hint_blocks"] += hint["external_vision_input_literal_hint"]
            external_modes.update(hint["explicit_ecnu_mode_command_occurrences"])
            external_client_hints.update(hint["equivalent_client_literal_hints"])
            if hint["possible_external_model_dependency"]:
                external_refs.append({"target_id": r["id"], "episode_id": r["episode_id"], "source_event_line": r["source_event_line"], "source_event_CAS": r["source_event_CAS"], "tool_name": c["name"], "arguments_sha256": c["arguments_sha256"], "hints": hint})
    write_gz("native_external_model_dependency_hints.jsonl.gz", external_refs)
    report["external_model_dependency_proxies"] = {"target_count": sum(r["possible_external_model_dependency_proxy"] for r in all_targets), "episode_count": len({r["episode_id"] for r in all_targets if r["possible_external_model_dependency_proxy"]}), "counts": dict(external_counts), "explicit_ecnu_mode_command_string_occurrences_not_API_calls": dict(external_modes), "equivalent_client_literal_call_block_hints": dict(external_client_hints), "interpretation": "All original toolCall parameter strings inspected, including exec commands and written code. Mentions can be documentation/inspection or code not yet run, and wrappers/loops can hide additional real calls. These are dependency locators, never actual API invocation or billed-token counts. sessions_spawn blocks are native delegation requests, not the subagent's downstream call count. A text14B student continuing to use external vision/image/speech/text/delegation has not replaced all large-model compute; cost per qualified skill must include those tool-model bills and uncertainty."}
    report["elapsed_seconds"] = round(time.time() - started, 3)
    path = OUT / "NATIVE_QUALITY.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(js({"report": str(path), "sha256": file_sha(path), "episodes": len(all_episodes), "targets": len(all_targets), "metrics": agg, "elapsed_seconds": report["elapsed_seconds"]}), flush=True)


if __name__ == "__main__":
    main()
