"""Recover only proved, pre-exposure native prefixes; never execute an agent.

This is intentionally conservative. Selected formal-source tasks remain held
from their start. An observed-only hold does not become a safe whole episode.
In the current corpus the only additionally proved cases are initial, generic
directory discovery actions, before any tool return. Formal-derived route
returns are excluded as well as original source bodies. No serializer, token
array, original mask, or privacy projection is rewritten to manufacture data.
"""
from __future__ import annotations

from array import array
from collections import Counter
from copy import deepcopy
import gzip
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / "output/20261025_wrd_reasoning_recovery_v4"
OUT = ROOT / "output/20261026_wrd_strict226_expansion/prefixes"
SID = re.compile(r"conv_[a-f0-9]{12}")
OBSERVED = "model_observed_user_or_tool_source_content"
# Manually inspected generic protocol variants, not business instructions.
# Their differences add generic reuse/repair guidance only. No source identity,
# source body, answer, route steps or feedback appears in these segments.
GENERIC_TASK_SHA256 = {
    "ddf6ab6d981ebb52f94813612d07f4db06c1581fca409533f3146ce6ff521b06",
    "fef6f14fca54753e4467c5e0fec5082ca51e2ea6a422c9e6df4c2d444899822e",
    "8a4e47ba07827683639f0e36cb513034d39e7fe814094992a803a890b5318234",
}
GUIDE_SHA256 = "6defd93cb315969b52914419afc3df63f57ec046378d1c104d277464c798dbd6"
SYSTEM_SHA256 = "f25619d1becde0e6f1c15aee38100b41a96b24952c609528e0f3a1d1b0658c62"
PURE_DISCOVERY_COMMANDS = {
    "find /workspace -maxdepth 3 -type f | head -80 && echo '---' && ls /workspace/outputs 2>/dev/null",
    "find /workspace -type f | head -100 && echo '---' && ls /workspace/outputs 2>/dev/null",
}


def js(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def sha_bytes(value):
    return hashlib.sha256(value).hexdigest()


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for part in iter(lambda: f.read(1024 * 1024), b""):
            h.update(part)
    return h.hexdigest()


def rows(path):
    with gzip.open(path, "rt", encoding="utf-8-sig") as f:
        for line in f:
            if line.strip():
                yield json.loads(line)


def int_sha(ids):
    values = array("I", ids)
    if sys.byteorder != "little":
        values.byteswap()
    return sha_bytes(values.tobytes())


def text_blocks(message):
    content = message.get("content")
    if isinstance(content, str):
        return [content]
    return [b.get("text", "") for b in content or []
            if isinstance(b, dict) and b.get("type") == "text"]


def calls(message):
    return [b for b in message.get("content", [])
            if isinstance(b, dict) and b.get("type") == "toolCall"]


def selected_formal(label):
    return [e for e in label["evidence"] if e["type"] != OBSERVED
            and e["direct_source_payload"] and e["formal_source_ids"]]


def triggering_action(messages, observation_index):
    """Return the assistant causing an observed tool result, fail closed."""
    result = messages[observation_index]
    if result.get("role") == "user":
        return observation_index
    if result.get("role") not in {"tool", "toolResult"}:
        return None
    call_id = result.get("toolCallId") or result.get("tool_call_id")
    if not isinstance(call_id, str):
        return None
    matches = [i for i, m in enumerate(messages[:observation_index])
               if m.get("role") == "assistant"
               and any(b.get("id") == call_id for b in calls(m))]
    return matches[0] if len(matches) == 1 else None


def initial_prompt_proof(episode):
    """Inspect actual input structure, never trust source metadata alone."""
    if (not episode.get("native_verified") or not episode.get("context_fully_recoverable")
            or episode.get("message_parse_issues")):
        return None
    if not isinstance(episode.get("system"), str) or sha_bytes(episode["system"].encode()) != SYSTEM_SHA256:
        return None
    messages = episode["messages"]
    if not messages or messages[0].get("role") != "user":
        return None
    content = messages[0].get("content")
    if not isinstance(content, str):
        return None
    try:
        guide, rest = content.split("本题提供的文件：\n")
        file_list, rest = rest.split("\n\n用户提供的上下文：\n")
        context, task = rest.split("\n\n用户任务：\n")
    except ValueError:
        return None
    if context or sha_bytes(guide.encode()) != GUIDE_SHA256:
        return None
    task_hash = sha_bytes(task.encode())
    if task_hash not in GENERIC_TASK_SHA256 or SID.search(guide + context + task):
        return None
    paths = file_list.splitlines()
    if not paths or not all(p.startswith("- /workspace/") and "\r" not in p for p in paths):
        return None
    # These identifiers are file availability only. No file bytes, route,
    # source record, answer, feedback or resource body occurs in this segment.
    return {"system_sha256": SYSTEM_SHA256, "guide_sha256": GUIDE_SHA256,
            "generic_task_sha256": task_hash,
            "initial_user_message_sha256": sha_bytes(content.encode()),
            "initial_context_empty": True, "resource_list_is_paths_only": True,
            "protected_identifiers_only_in_resource_availability_paths": True}


def prove_generic_discovery_prefix(episode, label, formal):
    """Current narrow proof: first generic discovery, next formal route read.

    It deliberately does not admit prefixes with earlier tool observations,
    selected-source instructions, truncated JSON, or unresolved dependencies.
    """
    if selected_formal(label):
        return None, "explicit_selected_formal_dependency_from_start"
    if not label["model_observed_protected_source_body_ids"]:
        return None, "not_later_observed_only_hold"
    proof = initial_prompt_proof(episode)
    if proof is None:
        return None, "initial_actual_input_not_in_proved_generic_protocol"
    messages = episode["messages"]
    if len(messages) < 5 or messages[1].get("role") != "assistant":
        return None, "missing_initial_assistant_action"
    first_calls = calls(messages[1])
    if len(first_calls) != 1 or any(b.get("type") != "toolCall" for b in messages[1].get("content", [])):
        return None, "initial_response_not_pure_single_discovery_call"
    first = first_calls[0]
    args = first.get("arguments")
    is_ls = first.get("name") == "ls" and args == {"path": "/workspace/inputs"}
    is_find = first.get("name") == "exec" and isinstance(args, dict) and set(args) == {"command"} and args["command"] in PURE_DISCOVERY_COMMANDS
    if not (is_ls or is_find):
        return None, "initial_action_not_proved_source_independent_discovery"
    if SID.search(js(first)):
        return None, "initial_action_names_a_source"
    # Find and independently inspect the earlier derived-route observation.
    # Merely using first_protected BODY index would incorrectly retain it.
    route_return = messages[4]
    if route_return.get("role") not in {"tool", "toolResult"}:
        return None, "no_exact_earlier_route_tool_observation"
    route_call_index = triggering_action(messages, 4)
    if route_call_index != 3:
        return None, "route_call_id_not_unique_or_expected"
    route_calls = calls(messages[3])
    if len(route_calls) != 1 or route_calls[0].get("name") != "read" or route_calls[0].get("arguments") != {"path": "/workspace/inputs/route.json"}:
        return None, "earliest_route_action_not_exactly_identified"
    parsed = []
    for text in text_blocks(route_return):
        try:
            parsed.append(json.loads(text))
        except ValueError:
            return None, "route_return_unparseable_hold"
    derived = [v for v in parsed if isinstance(v, dict)
               and set(v.get("source_ids", [])) & formal
               and v.get("steps") and (v.get("reuse_reason") or v.get("value_plan"))]
    if not derived:
        return None, "route_return_not_proved_formal_derived_resource"
    body_index = label["first_protected_model_observation_message_index"]
    body_action = triggering_action(messages, body_index)
    if body_action is None or body_action < 3:
        return None, "first_protected_body_trigger_not_unique_or_earlier"
    return {**proof, "last_safe_native_assistant_index": 1,
            "first_excluded_native_assistant_index": 3,
            "first_excluded_observation_native_index": 4,
            "first_excluded_observation_type": "formal_derived_route_steps_and_reuse_reason_or_value_plan",
            "first_excluded_tool_call_id_sha256": sha_bytes(route_return["toolCallId"].encode()),
            "later_protected_body_observation_native_index": body_index,
            "later_protected_body_triggering_assistant_index": body_action,
            "all_tool_results_excluded_from_recovered_input": True,
            "first_action_type": "directory_listing" if is_ls else "file_names_only_find_and_listing"}, None


def make_prefix(parent, proof, tokenizer_pair, actual_episode, causal_renderer, native_adapter):
    legal = [t for t in parent["targets"] if t["source_message_index"] <= proof["last_safe_native_assistant_index"]]
    positive = [t for t in legal if t["supervised_tokens"] > 0 and t["owned_supervision_spans"]]
    if not positive:
        return None
    end = max(t["response_end_token_exclusive"] for t in positive)
    legal = [deepcopy(t) for t in legal if t["response_end_token_exclusive"] <= end]
    spans = sorted(s for t in legal for s in t["owned_supervision_spans"])
    assert spans and all(s in parent["supervision_spans"] and 0 <= s[0] < s[1] <= end for s in spans)
    assert all(a[1] <= b[0] for a, b in zip(spans, spans[1:]))
    assert parent["label_ignore_index"] == -100
    assert not SID.search(js(parent["tools"]))
    ids = parent["input_ids"][:end]
    rendered = tokenizer_pair[0].decode(ids, skip_special_tokens=False)
    assert rendered == tokenizer_pair[1].decode(ids, skip_special_tokens=False)
    assert rendered.endswith("<|im_end|>\n")
    assert len(rendered) == legal[-1]["rendered_assistant_span"][1]
    assert tokenizer_pair[0].encode(rendered, add_special_tokens=False).ids == ids
    assert tokenizer_pair[1].encode(rendered, add_special_tokens=False).ids == ids
    # Re-render source messages from the beginning through the actual assistant
    # boundary with the unchanged declared template, independently of the
    # compiled array. This proves the prefix contains the original system and
    # initial user message verbatim and no later tool result.
    native_prefix = {**actual_episode, "messages": actual_episode["messages"][:2]}
    native_messages, native_indices, projection_issues = native_adapter(native_prefix)
    assert not projection_issues and native_indices == [None, 0, 1]
    fresh_render = causal_renderer.render(messages=native_messages,
        tools=parent["tools"] or None, documents=None,
        add_generation_prompt=False, enable_thinking=False)
    assert fresh_render == rendered
    assert actual_episode["messages"][0]["content"] in rendered
    assert sum(m["role"] == "tool" for m in native_messages) == 0
    assert int_sha(parent["input_ids"]) == parent["input_ids_sha256_u32le"]
    # Positive source-target IDs are unchanged; only view ownership changes.
    per = Counter()
    for a, b, component, weight in spans:
        per[component] += b - a
    result = deepcopy(parent)
    result.update({"id": parent["episode_id"] + ":strict226_pre_exposure_prefix",
        "view": "strict226_proved_initial_discovery_prefix_not_complete_stage",
        "stage_complete_in_this_view": False,
        "full_autonomous_controller_demonstration": False,
        "training_admitted": True,
        "training_admission_level": "GENERIC_NATIVE_DISCOVERY_SILVER_ONLY_NOT_DOMAIN_OR_SEMANTIC_GOLD",
        "input_ids": ids, "total_tokens": len(ids), "targets": legal,
        "supervision_spans": spans, "supervised_tokens": sum(per.values()),
        "supervised_tokens_by_component": dict(per),
        "input_ids_sha256_u32le": int_sha(ids),
        "supervision_spans_sha256": sha_bytes(js(spans).encode()),
        "rendered_sha256": sha_bytes(rendered.encode()),
        "assistant_generation_spans": [t["rendered_assistant_span"] for t in legal],
        "length_bucket": "prefix_le16k" if end <= 16384 else "prefix_16k_to32k",
        "native_target_owner_view": "strict226_pre_exposure_prefix_only; held_parent_not_training",
        "strict226_prefix_proof": proof,
        "original_source_messages_to_prefix_verbatim_render_verified": True,
        "original_source_message_indices_in_prefix": [0, 1],
        "original_source_prefix_includes_tool_results": False,
        "prefix_parent": {"id": parent["id"], "view": parent["view"],
            "total_tokens": parent["total_tokens"],
            "input_ids_sha256_u32le": parent["input_ids_sha256_u32le"],
            "rendered_sha256": parent["rendered_sha256"],
            "serialization_sha256_unchanged": parent["serialization"],
            "input_ids_are_exact_original_prefix": True,
            "positive_spans_are_exact_original_owned_subset": True},
        "source_scope_policy": "original226_body_answer_feedback_explicit_derived_resources_excluded",
        "full_episode_source_hold_remains": True,
        "complete_transitive_resource_dependency_isolation_proven": False,
        "domain_training_data_quantity_shortfall_solved": False,
        "semantic_approved": False, "human_gold": False})
    assert result["serialization"] == parent["serialization"]
    assert all(t["source_message_index"] < proof["first_excluded_native_assistant_index"] for t in result["targets"])
    assert result["input_ids"] == parent["input_ids"][:end]
    return result


def main():
    from tokenizers import Tokenizer
    from transformers.utils.chat_template_utils import _compile_jinja_template
    sys.path.insert(0, str(ROOT / "research/data_prep/wrd_reasoning_v4"))
    from compile_native import native_messages
    label_path = BASE / "controlled/native_source_split.labels.jsonl.gz"
    source_path = ROOT / "output/20261025_wrd_training_dataset/bundle/canonical/native_episodes.jsonl.gz"
    public_source = ROOT / "output/20261025_wrd_fullchain_reaudit/public_projection/fullchain.native_sessions.jsonl.gz"
    paths = [label_path, source_path, public_source]
    profiles = {scope: [BASE / "curated_native" / (scope + "." + role + ".jsonl.gz")
                        for role in ("core32k", "actor_aux32k")] for scope in ("controlled", "public")}
    strict = {scope: [BASE / "source_gated_profiles" / (scope + ".strict226." + role + ".jsonl.gz")
                      for role in ("core32k", "actor_aux32k")] for scope in profiles}
    paths += [p for group in (profiles, strict) for scope_paths in group.values() for p in scope_paths]
    original_sha = {str(p.relative_to(ROOT)): digest(p) for p in paths}
    labels = {r["episode_id"]: r for r in rows(label_path)}
    formal = {s for r in labels.values() for s in r["direct_formal_source_ids"]}
    selected = {e for e, r in labels.items() if selected_formal(r)}
    observed_only = {e for e, r in labels.items() if r["model_observed_protected_source_body_ids"] and e not in selected}
    proofs = {}; holds = Counter(); decisions = []; proved_episodes = {}
    for episode in rows(source_path):
        eid = episode["episode_id"]
        if eid not in observed_only:
            continue
        proof, reason = prove_generic_discovery_prefix(episode, labels[eid], formal)
        if proof:
            proofs[eid] = proof
            proved_episodes[eid] = episode
        else:
            holds[reason] += 1
        decisions.append({"episode_id": eid, "kind": episode["kind"],
                          "prefix_proof_passed": proof is not None, "hold_reason": reason})
    asset_root = ROOT / "output/20261025_wrd_training_preflight/tokenizer_assets"
    asset_paths = [asset_root / key / "tokenizer.json" for key in ("primary_14b", "control_8b")]
    assert digest(asset_paths[0]) == digest(asset_paths[1])
    tokenizer_pair = [Tokenizer.from_file(str(p)) for p in asset_paths]
    template_path = BASE / "CAUSAL_TEMPLATE.json"
    template = json.loads(template_path.read_text(encoding="utf-8"))
    assert sha_bytes(template["variant"].encode()) == template["causal_template_sha256"]
    causal_renderer = _compile_jinja_template(template["variant"])
    OUT.mkdir(parents=True, exist_ok=True)
    report_scopes = {}; exported_eids = {}
    for scope, scope_paths in profiles.items():
        existing_owners = {t["id"] for p in strict[scope] for r in rows(p)
                           for t in r["targets"] if t["owned_supervision_spans"]}
        owner_ids = set(); counts = Counter(windows=0, targets=0, input_tokens=0,
            supervised_tokens=0, le16k_windows=0, le32k_windows=0)
        by_stage = Counter(); receipts = []
        out_path = OUT / (scope + ".jsonl.gz")
        exported_eids[scope] = set()
        with gzip.open(out_path, "wt", encoding="utf-8", newline="\n", compresslevel=6) as f:
            for path in scope_paths:
                for parent in rows(path):
                    eid = parent["episode_id"]
                    if eid not in proofs:
                        continue
                    # A public result can only originate in the previously
                    # cleared public projection. Never substitute controlled.
                    assert parent["serialization"] == template["causal_template_sha256"]
                    prefix = make_prefix(parent, proofs[eid], tokenizer_pair,
                        proved_episodes[eid], causal_renderer, native_messages)
                    if prefix is None:
                        counts["no_quality_positive_target"] += 1
                        continue
                    positive = [t for t in prefix["targets"] if t["owned_supervision_spans"]]
                    for target in positive:
                        assert target["id"] not in owner_ids and target["id"] not in existing_owners
                        owner_ids.add(target["id"])
                    f.write(js(prefix) + "\n")
                    exported_eids[scope].add(eid)
                    counts["windows"] += 1
                    counts["targets"] += len(positive)
                    counts["input_tokens"] += prefix["total_tokens"]
                    counts["supervised_tokens"] += prefix["supervised_tokens"]
                    counts["le16k_windows"] += prefix["total_tokens"] <= 16384
                    counts["le32k_windows"] += prefix["total_tokens"] <= 32768
                    by_stage[parent["kind"]] += 1
                    receipts.append({"episode_id": eid, "target_ids": [t["id"] for t in positive],
                        "first_action_type": proofs[eid]["first_action_type"],
                        "source_message_sha256": positive[0]["source_message_sha256"],
                        "source_event_line": positive[0]["source_event_line"],
                        "assistant_response_end_token_exclusive": positive[0]["response_end_token_exclusive"],
                        "assistant_rendered_character_span": positive[0]["rendered_assistant_span"],
                        "original_owned_supervision_spans": positive[0]["owned_supervision_spans"],
                        "last_safe_native_assistant_index": 1,
                        "excluded_route_action_native_index": 3,
                        "excluded_route_result_native_index": 4,
                        "later_protected_body_observation_native_index": proofs[eid]["later_protected_body_observation_native_index"],
                        "input_tokens": prefix["total_tokens"], "supervised_tokens": prefix["supervised_tokens"],
                        "prefix_input_ids_sha256_u32le": prefix["input_ids_sha256_u32le"],
                        "prefix_rendered_sha256": prefix["rendered_sha256"],
                        "prefix_supervision_spans_sha256": prefix["supervision_spans_sha256"]})
        report_scopes[scope] = {"counts": dict(counts), "by_stage": dict(by_stage),
            "positive_owner_unique_with_existing_strict_profile": True,
            "receipts": receipts, "path": str(out_path.relative_to(ROOT)),
            "sha256": digest(out_path), "bytes": out_path.stat().st_size,
            "zero_output_reason": "none_of_the_proved_controlled_episodes_has_an_existing_public_projection" if not counts["windows"] else None}
    assert all(digest(ROOT / p) == sha for p, sha in original_sha.items())
    report = {"schema_version": "wrd-strict226-causal-prefix-recovery-v5",
        "status": "VERY_SMALL_GENERIC_DISCOVERY_SUPPLEMENT_NOT_DOMAIN_DATA_SUFFICIENCY",
        "original_evaluation_boundary_preserved": True,
        "explicit_selected_formal_dependency_episodes_held_from_start": len(selected),
        "later_observed_only_episode_candidates": len(observed_only),
        "later_observed_only_by_stage": dict(Counter(labels[e]["kind"] for e in observed_only)),
        "proved_initial_discovery_prefix_episodes": len(proofs),
        "other_observed_only_episodes_still_held": len(observed_only) - len(proofs),
        "conservative_hold_reasons": dict(holds), "scopes": report_scopes,
        "proof_scope": "actual generic initial input plus first source-independent directory action only; no tool returns retained",
        "earlier_derived_route_resources_excluded_not_just_later_source_bodies": True,
        "triggering_tool_call_id_traced_and_triggering_assistant_action_excluded": True,
        "metadata_alone_not_used_as_safety_proof": True,
        "source_pool_availability_paths_not_promoted_to_selected_source_dependency": True,
        "explicit_selected_source_tasks_never_recovered": True,
        "all_original_source_arrays_masks_and_privacy_projections_unchanged": True,
        "serializer_template_unchanged": True,
        "future_protected_tool_results_not_in_input_ids": True,
        "both_tokenizer_decode_and_encode_roundtrips_passed": True,
        "original_source_messages_from_start_verbatim_same_template_render_matches_prefix": True,
        "all_recovered_inputs_include_zero_tool_results": True,
        "static_loss_mask_validation": {
            "ignore_index": -100,
            "positive_spans_exact_unmodified_parent_owned_subset": True,
            "span_end_not_after_last_legal_complete_assistant_response": True,
            "spans_ordered_nonoverlapping_and_inside_input": True,
            "user_system_and_future_observation_tokens_have_no_positive_loss": True,
            "same_original_target_has_single_owner_with_existing_strict_profiles": True,
            "excluded_triggering_actions_not_present_as_context_or_positive_targets": True},
        "publication_permission_not_inferred_for_controlled_output": True,
        "semantic_gold_created": 0, "full_autonomous_chains_created": 0,
        "complete_transitive_independence_claimed": False,
        "domain_training_data_quantity_shortfall_solved": False,
        "training_started": False, "model_weights_loaded": False, "gpu_used": False,
        "agent_or_model_api_called": False,
        "protocol_code_evidence": ["research/pipelines/openclaw_eval/container_runner.py:429",
                                   "research/workflow/stages.py:324"],
        "script_sha256": digest(Path(__file__)),
        "source_sha256_before_and_after_equal": original_sha,
        "tokenizer_assets_sha256": {str(p.relative_to(ROOT)): digest(p) for p in asset_paths},
        "unchanged_causal_template_file_sha256": digest(template_path),
        "decisions_without_body": decisions}
    dest = OUT / "PREFIX_RECOVERY_REPORT.json"
    dest.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(js({"proved_prefix_episodes": len(proofs), "selected_formal_held": len(selected),
              "scopes": {k: v["counts"] for k, v in report_scopes.items()},
              "report": str(dest.relative_to(ROOT))}), flush=True)


if __name__ == "__main__":
    main()
