"""Reconcile the v8 computable report with every emitted metadata ledger row."""
import collections
import gzip
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
B = ROOT / "output/20261026_wrd_quality_v8"


def sha(p):
    h = hashlib.sha256()
    with Path(p).open("rb") as f:
        for b in iter(lambda: f.read(1048576), b""):
            h.update(b)
    return h.hexdigest()


def rows(p):
    with gzip.open(p, "rt", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def main():
    report_path = B / "NATIVE_QUALITY.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    targets = rows(B / "controlled/native_targets.quality.jsonl.gz")
    episodes = rows(B / "controlled/native_episodes.quality.jsonl.gz")
    checks = []

    def check(name, result):
        checks.append({"check": name, "passed": bool(result)})

    check("source script SHA", sha(ROOT / "research/data_prep/wrd_quality_v8/native_quality.py") == report["script_sha256"])
    for p in report["source_pins"] + report["outputs"]:
        check("bound file SHA and size:" + p["path"], sha(p["path"]) == p["sha256"] and Path(p["path"]).stat().st_size == p["bytes"])
    ids = {r["id"] for r in targets}
    eids = {r["episode_id"] for r in episodes}
    check("all32342 original target owners unique", len(targets) == len(ids) == 32342)
    check("all1763 episode identities unique", len(episodes) == len(eids) == 1763)
    counts = collections.Counter(r["episode_id"] for r in targets)
    check("per episode target counts", all(counts[r["episode_id"]] == r["counts"]["assistant_positions"] for r in episodes))
    check("30438 tool blocks", sum(r["call_count"] for r in targets) == report["population"]["tool_calls"] == 30438)
    check("all targets have the existing-episode lineage qualifier", all(r["lineage_label_scope"] == "existing_v6_episode_scope_not_target_prefix_proof" for r in targets))
    check("all target boundaries present and coherent", all(r["serialized_prompt_tokens_before_assistant_body"] + r["serialized_target_body_with_controls_tokens"] == r["serialized_causal_end_tokens"] <= r["original_full_stage_tokens"] for r in targets))
    for key in ("nonempty", "current_exchange_structurally_paired", "observed_tool_failure", "is_process_poll", "poll_returned_still_running", "has_visible_text_with_tool_call", "text_only_response", "explicit_write_edit_patch_tool", "explicit_mutation_after_earlier_failure_temporal_only", "result_details_truncated", "result_visible_truncation_marker", "nonempty_incomplete_stop", "repeated_normalized_action_adjacent"):
        check("target metric:" + key, sum(bool(r[key]) for r in targets) == report["global_target_metrics"][key])
    check("all old mask labels retained25141/7201", sum(r["prior_v4_positive_loss"] for r in targets) == 25141 and sum(not r["prior_v4_positive_loss"] for r in targets) == 7201)
    check("derived representation length16K", sum(r["nonempty"] and r["serialized_causal_end_tokens"] <= 16384 for r in targets) == 11804)
    check("derived representation length32K", sum(r["nonempty"] and r["serialized_causal_end_tokens"] <= 32768 for r in targets) == 21690)
    check("all semantic/admission labels unset", all(r["semantic_quality"] == "NOT_AUTOMATICALLY_ESTABLISHED" and not r["training_admitted_by_this_audit"] for r in targets))
    check("system capture classes partition1763", sum(r["system_truncation_marker"] for r in episodes) == 1577 and sum(r["system_malformed_placeholder"] for r in episodes) == 2 and sum(not r["system_recorded"] for r in episodes) == 184)
    check("existing lineage scope classes partition1763", dict(collections.Counter(r["lineage_status"] for r in episodes)) == {"HOLD_PROTECTED": 1139, "HOLD_MISSING_EVIDENCE": 560, "ADMIT": 64})
    check("core7 and noncore and text and empty partition32342", dict(collections.Counter(r["tool_set_scope"] for r in targets)) == {"core7_only": 28442, "noncore_only": 1996, "text_only": 1576, "empty": 328})
    check("82 independent second calls plus1681 reuse", report["tokenizer_pair_existing_proof_modes"] == {"independent_call_equal": 82, "byte_identical_assets_and_deterministic_reuse": 1681})
    external = rows(B / "controlled/native_external_model_dependency_hints.jsonl.gz")
    check("external hint rows target refs valid", len(external) == 1066 and all(r["target_id"] in ids for r in external))
    check("external hints are not API bills", all(r["hints"]["not_actual_API_call_count"] for r in external))
    near = rows(B / "controlled/native_near_duplicate_proxy_edges.jsonl.gz")
    check("342 qualified near-proxy edges", len(near) == 342 and all(r["representative_target_a"] in ids and r["representative_target_b"] in ids and r["simhash_hamming"] <= 3 and r["bottom128_shingle_overlap"] >= .9 for r in near))
    sample = json.loads((B / "NATIVE_REVIEW_SAMPLE_MANIFEST.json").read_text(encoding="utf-8"))
    sampled = [r["id"] for s in sample["strata"] for r in s["targets"]]
    check("203 stratified candidate owners valid unique", len(sampled) == len(set(sampled)) == sample["sampled_targets"] == 203 and set(sampled) <= ids)
    # Focused locators supplement the general coverage sample. These remain
    # deterministic audit candidates, not a random semantic accuracy estimate.
    categories = {
        "explicit_original_JSON_decision_field": lambda r: r["explicit_JSON_decision_field_proxy"],
        "external_model_dependency_parameter_hint": lambda r: r["possible_external_model_dependency_proxy"],
        "schema_unknown_core7": lambda r: r["tool_set_scope"] == "core7_only" and r["schema_unknown"],
        "error_then_later_mutation_temporal_not_causal_proof": lambda r: r["explicit_mutation_after_earlier_failure_temporal_only"],
        "at_least_third_consecutive_process_poll": lambda r: r["consecutive_poll_position"] >= 3,
    }
    focused = []
    for name, predicate in categories.items():
        grouped = collections.defaultdict(list)
        for r in targets:
            if predicate(r):
                grouped[r["request_corrected_role"]].append(r)
        for role, values in sorted(grouped.items()):
            chosen = sorted(values, key=lambda r: r["id"])[:2]
            focused.append({"category": name, "role": role, "population_targets": len(values), "target_refs": [{k: r[k] for k in ("id", "episode_id", "source_message_index", "source_event_line", "source_event_CAS", "lineage_status")} for r in chosen]})
    focused_path = B / "NATIVE_FOCUSED_REVIEW_MANIFEST.json"
    focused_path.write_text(json.dumps({"schema_version": "wrd-native-v8-focused-review-locators", "sampling": "two smallest target IDs per category and corrected role; not an unbiased quality estimate", "strata": focused, "no_original_body_copied": True, "no_semantic_approval_or_training_admission": True}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    failures = [r["check"] for r in checks if not r["passed"]]
    out = {"schema_version": "wrd-native-computable-quality-reconciliation-v8", "status": "PASS_WITH_SCOPE_LIMITS" if not failures else "FAIL", "quality_report_sha256": sha(report_path), "checks": checks, "failure_count": len(failures), "failures": failures, "extra_counts": {"nonempty_exact_action_payload_types_without_call_ids": len({r["exact_action_payload_group_without_native_call_ids"] for r in targets if r["nonempty"]}), "nonempty_targets": 32014, "structured_decision_field_target_refs": sum(r["explicit_JSON_decision_field_proxy"] for r in targets), "recorded_nontext_content_block_types": report["capture_completeness"]["recorded_nontext_content_block_types"]}, "focused_manifest": {"path": str(focused_path), "sha256": sha(focused_path)}, "limits": ["Reconciliation verifies metric/count/reference consistency, not an independent semantic judge.", "Original episode lineage status does not retrospectively contaminate every early target prefix.", "Failed tests and polling are not automatically negative training actions.", "Raw tool-model dependency strings are not billed API invocation counts.", "16K/32K lengths are for the old derived training representation with incomplete system/tool capture, not complete original API requests."], "training_started": False, "new_model_or_business_calls": 0, "script_sha256": sha(__file__)}
    path = B / "NATIVE_COMPUTABLE_QA.json"
    path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": out["status"], "checks": len(checks), "failures": failures, "report_sha256": out["quality_report_sha256"], "QA_sha256": sha(path), "extra_counts": out["extra_counts"]}, ensure_ascii=True))


if __name__ == "__main__":
    main()
