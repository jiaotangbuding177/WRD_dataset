import hashlib
import json
from pathlib import Path

OUT = Path(__file__).parent
BASE = OUT.parent
review = json.loads((BASE / "ORIGINAL_R_LOCAL_REVIEW.json").read_text(encoding="utf-8"))
revised = json.loads((BASE / "semantic_revision_02/ORIGINAL_R_LOCAL_REVIEW.json").read_text(encoding="utf-8"))
old = {item["id"]: item for item in review["positive_ranges"]}
new = {item["id"]: item for item in revised["positive_ranges"]}
verdicts = []
for key, item in old.items():
    current = new[key]
    changed = current["end"] != item["end"]
    verdicts.append({
        "id": key,
        "semantic_verdict": "NARROW_ORIGINAL_RANGE_REQUIRED_AND_V2_CORRECTED" if changed else "PASS_LOCAL_SCOPED_AI_SILVER",
        "original_range": [item["start"], item["end"]],
        "reviewed_v2_range": [current["start"], current["end"]],
        "reviewed_v2_text_sha256": current["sha256"],
        "revoke_original_suffix_range": [current["end"], item["end"]] if changed else None,
        "revoke_original_suffix_sha256": hashlib.sha256(item["text"][len(current["text"]):].encode("utf-8")).hexdigest() if changed else None,
        "reason": "Overbroad qualifier preservation claim conflicts with E_A absolute responsibility/completed-transition wording." if changed else "Independently supported by actual source/delivery/protocol in the original prefix; no whole-response credit.",
        "additional_scope": "The 7,367,237 subtotal is pre-review only; never including the then-current review." if key == "C_R_0021_20" else None,
    })
result = {
    "schema": "independent-c-review-semantic-followup-v1",
    "reviewer_identity": "Independent AI assistant silver; not human gold or calibrated human review",
    "root_main_admission": False,
    "old_range_characters": 3188,
    "revised_range_characters": 2981,
    "revoked_characters": 207,
    "range_verdicts": verdicts,
    "new_state_semantic_status": "PASS_SCOPED_NEW_POST_TERMINAL_STOP_CANDIDATE",
    "state_is_not_original_D_same_condition": True,
    "summary_is_new_AI_authorship_not_original_teacher_reasoning": True,
    "source_user_messages_and_actual_deliverables_complete": True,
    "blind_Q_is_fallible_uncalibrated_AI_observation_and_v2_keeps_original_per_label_fields": True,
    "new_state_costs_correctly_post_terminal": {"known_tokens": 8660547, "actual_request_identities": 110, "unknown_usage_calls": 1},
    "zero_qualified_denominator_cost_undefined": True,
    "STOP_is_reasonable_bounded_decision_not_global_optimum_or_WRD_generalization": True,
    "training_exposure_rule": "Use revised v2 view OR retained v1 history, never both positive-loss views for same owners. Original artifacts remain preserved.",
    "not_a_training_authorization": True,
}
(OUT / "SEMANTIC_REVIEW.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
files = []
for path in sorted(OUT.iterdir()):
    if path.is_file() and path.name != "MANIFEST.json":
        files.append({"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "bytes": path.stat().st_size})
(OUT / "MANIFEST.json").write_text(json.dumps({"files": files, "root_main_admission": False}, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({"status": "V2_SEMANTIC_SCOPE_PASS_PENDING_ROOT_ADMISSION", "range_count": len(verdicts), "revised_characters": 2981, "revoked_characters": 207, "files": len(files)}))
