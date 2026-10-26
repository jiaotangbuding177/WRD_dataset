"""Independent, CPU-only synthesis audit; does not execute any recorded program.

Reads the v8 metadata/quality ledgers, not original enterprise bodies, provider
credentials, the C-drive conversation body, models, or production databases.
"""
from __future__ import annotations

import collections
import datetime as dt
import gzip
import hashlib
import json
import pathlib


ROOT = pathlib.Path(__file__).resolve().parents[3]
BASE = ROOT / "output" / "20261026_wrd_quality_v8"
EXPECTED_REPORT_SHA = "fcc72b8623e93777436167c481195aa3615a5de9e04eb38c6c40e56fd7c7859f"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(name):
    return json.loads((BASE / name).read_text(encoding="utf-8"))


def lines(name):
    return [json.loads(x) for x in (BASE / name).read_text(encoding="utf-8").splitlines() if x]


def luminance(hex_color):
    values = [int(hex_color[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    linear = [v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4 for v in values]
    return sum(v * weight for v, weight in zip(linear, (0.2126, 0.7152, 0.0722)))


def main():
    checks = []

    def check(name, actual, expected):
        checks.append({"check": name, "actual": actual, "expected": expected, "pass": actual == expected})

    report_path = BASE / "QUALITY_ASSESSMENT.md"
    report = report_path.read_text(encoding="utf-8")
    summary = read("ASSESSMENT_SUMMARY.json")
    native = read("NATIVE_QUALITY.json")
    chain = read("CHAIN_QUALITY.json")
    raw = read("RAW_RECOVERABILITY.json")
    artifact = read("ARTIFACT_STATIC_QUALITY.json")
    numeric = read("NUMERIC_CONTENT_COUNTEREXAMPLE.json")
    literature = read("LITERATURE_EVIDENCE.json")
    check("reviewed_report_identity", sha(report_path), EXPECTED_REPORT_SHA)
    check("source_pin_count", len(summary["source_pins"]), 8)
    for pin in summary["source_pins"]:
        path = pathlib.Path(pin["path"])
        check(path.name + ":sha256", sha(path), pin["sha256"])
        check(path.name + ":bytes", path.stat().st_size, pin["bytes"])

    # Recompute population denominators from all existing target metadata rows.
    # These rows contain hashes/counts and source labels, not original content.
    counts = collections.Counter()
    episode_ids = set()
    with gzip.open(BASE / "controlled/native_targets.quality.jsonl.gz", "rt", encoding="utf-8") as stream:
        for line in stream:
            r = json.loads(line)
            episode_ids.add(r["episode_id"])
            counts["targets"] += 1
            counts["calls"] += r["call_count"]
            counts["results"] += r["result_count"]
            counts["nonempty"] += bool(r["nonempty"])
            counts["text_only"] += bool(r["text_only_response"])
            counts["visible_text_and_call"] += bool(r["has_visible_text_with_tool_call"])
            counts["tokens"] += r["serialized_target_body_with_controls_tokens"]
            counts["poll_tokens"] += r["serialized_target_body_with_controls_tokens"] if r["is_process_poll"] else 0
            counts["le16k"] += bool(r["nonempty"] and r["serialized_causal_end_tokens"] <= 16384)
            counts["le32k"] += bool(r["nonempty"] and r["serialized_causal_end_tokens"] <= 32768)
            counts["previous_positive_loss"] += bool(r["prior_v4_positive_loss"])
            counts["new_admission"] += bool(r["training_admitted_by_this_audit"])
    for key, expected in {"targets": 32342, "calls": 30438, "results": 30437, "nonempty": 32014,
                          "text_only": 1576, "visible_text_and_call": 8147, "tokens": 10674583,
                          "poll_tokens": 76924, "le16k": 11804, "le32k": 21690,
                          "previous_positive_loss": 25141, "new_admission": 0}.items():
        check("target_ledger:" + key, counts[key], expected)
    check("target_ledger:episode_ids", len(episode_ids), 1763)
    check("calls_plus_text_only_plus_empty", counts["calls"] + counts["text_only"] + counts["targets"] - counts["nonempty"], counts["targets"])
    check("16k_percent_old_derived_nonempty", round(counts["le16k"] / counts["nonempty"] * 100, 2), 36.87)
    check("32k_percent_old_derived_nonempty", round(counts["le32k"] / counts["nonempty"] * 100, 2), 67.75)
    check("poll_tokens_percent", round(counts["poll_tokens"] / counts["tokens"] * 100, 2), 0.72)
    episode_counts = collections.Counter()
    with gzip.open(BASE / "controlled/native_episodes.quality.jsonl.gz", "rt", encoding="utf-8") as stream:
        for line in stream:
            r = json.loads(line)
            episode_counts["rows"] += 1
            episode_counts[r["lineage_status"]] += 1
            for flag in ("system_recorded", "system_truncation_marker", "system_malformed_placeholder"):
                episode_counts[flag] += bool(r[flag])
    check("episode_ledger:rows", episode_counts["rows"], 1763)
    check("episode_ledger:scope_labels", {k: episode_counts[k] for k in ("HOLD_PROTECTED", "HOLD_MISSING_EVIDENCE", "ADMIT")},
          {"HOLD_PROTECTED": 1139, "HOLD_MISSING_EVIDENCE": 560, "ADMIT": 64})
    check("system_capture_partition", episode_counts["system_truncation_marker"] + episode_counts["system_malformed_placeholder"] + episode_counts["rows"] - episode_counts["system_recorded"], 1763)
    check("native_report_population_matches", native["population"]["assistant_positions"], counts["targets"])

    check("task_case_partition", chain["output_branch_coverage"]["tasks_positive_attempts"] + chain["output_branch_coverage"]["tasks_zero_case_attempts"], 259)
    boundary = chain["original226_boundary"]
    for key, expected in {"routes_with_declared_learning226": 66, "routes_with_selected_business226": 17,
                          "outer_groups_with_no_declared_learning_or_selected_case226": 25,
                          "all_selected_stage_attempts_source_closed_non226_groups": 0}.items():
        check("boundary:" + key, boundary[key], expected)
    for key, expected in {"all_routes_A_B_C_outer_interface_groups": 77,
                          "retained29_A_B_C_outer_interface_groups": 29,
                          "full_autonomous_A_to_D_native_demonstrations_verified": 0,
                          "feedback_inputs_with_exact_prior_review_field_projection": 114,
                          "feedback_inputs_with_exact_prior_review_projection_and_actual_read": 113}.items():
        check("chain:" + key, chain["documented_chain_coverage"][key], expected)
    check("new_native_history_partition", raw["native"]["totals"]["already_in_v4_historical_inventory"] + raw["native"]["totals"]["outside_old1763_and_v4_native_inventory"], 80)
    p = raw["provider_responses"]
    check("provider_history_partition", p["totals"]["already_v4_provider_id"] + p["totals"]["outside_v4_provider_id_and_message_content_references"], 1536)
    check("plaintext_reasoning_groups", p["totals"]["with_original_readable_reasoning"], 257)
    check("plaintext_reasoning_new_content_not_workflows", p["reasoning_contents_outside_v4_reference"], 141)
    c = raw["exact_codex_session"]
    check("codex_LF_json_records", c["counts"]["json_lines"], 17016)
    check("codex_original_call_output_pair_count", (c["call_ids"], c["output_ids"]), (1893, 1893))
    check("encrypted_is_not_raw_R", (c["counts"]["encrypted_reasoning_items"], c["counts"]["event_reasoning_nonempty_raw_content"]), (2296, 0))
    check("static_hash_counts", (artifact["counts"]["files"], artifact["counts"]["manifest_hash_equal"]), (154, 154))
    check("static_not_runtime", (artifact["generated_scripts_executed"], artifact["runtime_replay_done"]), (False, False))
    local = lines("LOCAL_SEMANTIC_FINDINGS.jsonl")
    cases = lines("CASE_REVIEWS.jsonl")
    check("bounded_local_windows", len(local), 18)
    check("stratified_case_reviews", len(cases), 20)
    check("no_human_expert_gold_claim_in_local_reviews", all(r["not_human_expert_gold"] and not r["whole_episode_quality_certified"] for r in local), True)
    check("explicit_non_human_gold_flags_in_chain_reviews", sum(r.get("not_human_gold") is True for r in cases), 16)
    check("no_contradictory_gold_flag_in_chain_reviews", any(r.get("not_human_gold") is False for r in cases), False)
    check("no_new_admission_in_chain_reviews", all(r["not_new_training_admission"] for r in cases), True)
    lum = sorted((luminance(numeric["foreground"]), luminance(numeric["background"])))
    ratio = (lum[1] + 0.05) / (lum[0] + 0.05)
    check("independent_sRGB_contrast", abs(ratio - numeric["computed_contrast_ratio"]) < 1e-12, True)
    check("CSS_below_normal_and_large_text_reference", ratio < 3.0 and ratio < 4.5, True)
    for phrase in ("这不是原完整API输入覆盖率", "不能把后段保护依赖倒灌", "不能据它宣布SFT必失败", "加密串不是可训练原始思考", "未授权启动训练", "不自动产生可用训练链"):
        check("report_scope:" + phrase, phrase in report, True)
    check("literature_primary_only_contract", literature["primary_sources_only_in_conclusions"], True)
    check("summary_not_final_training_admission", summary["final_semantically_and_source_admitted_training_count_established"], False)
    check("summary_not_goal_guarantee", summary["ideal_model_outcome_proven_or_guaranteed"], False)
    check("summary_not_population_quality_rate", summary["population_semantic_pass_rate_or_quality_score_estimated"], False)

    findings = [{"severity": "clarification", "status": "resolved_before_final_review",
                 "issue": "Cost formula could be read as amortizing setup costs twice.",
                 "resolution": "Reviewed final report uses one-time total setup/training/validation costs plus all online costs in the same period, divided once by qualified skills; cross-period allocation is counted once."}]
    result = {
        "schema_version": "wrd-v8-independent-synthesis-review-1.0",
        "measured_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "status": "PASS_BOUNDED_SYNTHESIS" if all(c["pass"] for c in checks) else "REVIEW_FAILED_CHECKS",
        "reviewed_report": {"path": str(report_path), "sha256": sha(report_path)},
        "reviewed_summary_sha256": sha(BASE / "ASSESSMENT_SUMMARY.json"),
        "reviewer_script_sha256": sha(pathlib.Path(__file__)),
        "source_pins_verified": summary["source_pins"],
        "checks": checks,
        "checks_passed": sum(c["pass"] for c in checks), "checks_total": len(checks),
        "findings": findings,
        "independent_recomputations": {"all_old_native_target_metadata": dict(counts),
                                       "episode_metadata": dict(episode_counts), "css_contrast_ratio": ratio},
        "primary_literature_spot_checks": [
            {"url": "https://arxiv.org/html/2504.21798v2", "location": "Table 3 and final-data construction, lines 140-165",
             "finding": "50k is the task pool; final 32B SFT is 5016 trajectories, Table 3 marks 7B about 2k. The report correctly preserves the paper's table/prose tension rather than relabelling 50k as training trajectories."},
            {"url": "https://arxiv.org/html/2609.21187v1", "location": "sections 4.3 and Limitations, lines 96-108",
             "finding": "Qwen3-14B strict completion 8/77 and holistic 0/77 do not prove WRD or SFT impossible. Single-domain, exact-reference replay and deterministic gold users limit transfer of this counterexample."}],
        "interpretation": "The report supports investing in causal restoration and audited domain SFT preparation, not current readiness of a fully admitted training corpus or an assurance of autonomous teacher-equivalent WRD.",
        "remaining_limits": ["No independent human/domain quality gold or population semantic pass rate established.",
                             "No complete original wire context restoration across all 1763 episodes.",
                             "No fully source-admitted final training count or same-policy autonomous A-to-D demonstration established.",
                             "No learner closed-loop TSR/Q, Spark throughput, model-loaded test, training run or cost saving established.",
                             "18 bounded windows and 20 stratified cases are qualitative evidence, with possible overlap, not 38 independent tasks."],
        "actions": {"training_started": False, "model_weights_loaded": False, "new_teacher_actor_business_runs": 0,
                    "original_bodies_reread": False, "credentials_read": False, "original_masks_or_226_policy_changed": False,
                    "production_or_ablation_modified": False, "primary_report_modified_by_reviewer": False}}
    target = BASE / "V8_SYNTHESIS_REVIEW.json"
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "checks_passed": result["checks_passed"],
                      "checks_total": len(checks), "report_sha256": result["reviewed_report"]["sha256"],
                      "failed_checks": [x for x in checks if not x["pass"]], "output": str(target)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
