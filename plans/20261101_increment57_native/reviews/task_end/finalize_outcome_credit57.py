"""Record root semantic review and actual outcome scope, without a model call."""
import hashlib
import json
from pathlib import Path

ROOT = Path(r"D:\skillloop\output\20261101_wrd_increment57")
REVIEW = ROOT / "root_review57"
FINAL = ROOT / "task_end_checks57/TASK_END_EVIDENCE_FINAL57.json"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def save(name, value):
    path = REVIEW / name
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"path": str(path), "sha256": sha(path), "bytes": path.stat().st_size}


evidence = load(FINAL)
assert sha(FINAL) == "f3151a32b8fad077484c794bac9e388e9dadd1786c58cc65e37be0fc14f1d2ba"
assert evidence["actual_additional_provider_requests"] == 0
assert evidence["actual_additional_native_Agent_sessions"] == 0
rows = []
for packet in evidence["disclosure_review_packet"]:
    ref = packet["original_HTML"]
    path = Path(ref["path"])
    assert sha(path) == ref["sha256"] and path.stat().st_size == ref["bytes"]
    source = path.read_text(encoding="utf-8")
    for excerpt in packet["original_HTML_source_excerpts"]:
        start, end = excerpt["HTML_character_span"]
        assert source[start:end] == excerpt["original_line"]
    assert packet["actual_attempted_remote_requests"] == []
    assert packet["actual_websockets"] == []
    rows.append({
        "alias": packet["alias"],
        "arm": packet["arm_root_mapping_for_root_only"],
        "original_HTML": ref,
        "criterion_6": "PASS",
        "review_type": "ROOT_SEMANTIC_REVIEW_OF_ORIGINAL_TEXT_AND_ACTUAL_BROWSER_EVIDENCE",
        "reason": "原文明确披露浏览器localStorage、本地记录及不上传服务器，并明确页面口令不是服务器鉴权；实际本地试跑无远程请求或WebSocket。",
        "supporting_visible_text": packet["actual_visible_boundary_lines"],
        "scope": "Only the frozen case and observed local paths; not a universal security or backend authorization claim.",
    })
c6_receipt = save("ROOT_C6_MANUAL_REVIEW57.json", {
    "schema": "wrd57-root-semantic-criterion6-review-v1",
    "task_end_evidence_sha256": sha(FINAL),
    "original_browser_reports_unchanged": True,
    "root_judgments": rows,
    "Q_or_D1_D5_scores_created": False,
    "student_training_started": False,
})
matrix = []
for row in evidence["aliases"]:
    criteria = dict(row["objective_criteria"])
    criteria["6"] = "PASS"
    matrix.append({
        "arm": row["arm_root_mapping_for_root_only"],
        "alias": row["alias"],
        "artifact_sha256": row["artifact_sha256"],
        "criteria": criteria,
        "passed_criteria": sum(v == "PASS" for v in criteria.values()),
        "all_six_frozen_case_criteria_pass": all(v == "PASS" for v in criteria.values()),
        "consumer_run_status": "BUDGET_CENSORED",
    })
assert {r["arm"]: r["passed_criteria"] for r in matrix} == {"NS": 6, "V1": 5, "V0": 5}
mask_path = REVIEW / "CSV_FORMULA_MASK_AUDIT57.json"
assert sha(mask_path) == "599fcb8b6f905c288358b09083f7715727adb1b54d6a5b29dad4c3ba8c164fda"
decision = save("OUTCOME_CREDIT_DECISION57.json", {
    "schema": "wrd57-root-outcome-linked-training-credit-v1",
    "task_end_evidence": {"path": str(FINAL), "sha256": sha(FINAL)},
    "criterion6_review": c6_receipt,
    "actual_case1_matrix": matrix,
    "actual_failure": "V0/V1 actual CSV exported fixture formula text '=1+1' unchanged. JSON and rank/persistence/roundtrip checks passed. NS neutralized the CSV formula prefix in this fixture.",
    "mask_intersection_audit": {"path": str(mask_path), "sha256": sha(mask_path)},
    "positive_credit_decision": "RETAIN_ONLY_PREVIOUS_LOCAL_CSV_SERIALIZATION_AND_EXPORT_CREDIT",
    "reason": "API4 positive scope was exact retained code plus local test evidence, explicitly without blanket security credit. The selected code implements CSV quoting/serialization/export; no formula-safety assertion occurs in all 33 original decoded R/A/visible outputs. The new independent-case failure establishes an unimplemented extra requirement and denies whole-skill acceptance; it does not rewrite the original source task or invent a successful repair.",
    "formula_safety_positive_claims": 0,
    "whole_skill_KEEP_or_utility_credit": False,
    "data_or_masks_modified": False,
    "active_unique_targets": 1260,
    "positive_tokens": 294828,
    "next_real_chain_priority": "On a future authorized TRAIN-MINING repair, expose this exact CSV failure and require versioned repair plus regression on the same fixture and independent new inputs; retain failed attempts and cost. Do not fabricate a recorded teacher repair now.",
    "not_claimed": ["Q or five-dimension score", "student-model effect", "completed-consumer cost", "cross-device success", "qualified skill KEEP", "new independent source from a window"],
    "new_native_or_provider_calls": 0,
    "training_started": False,
})
print(json.dumps({"criterion6": c6_receipt, "decision": decision, "matrix": matrix}, ensure_ascii=False))
