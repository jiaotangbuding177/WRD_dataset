"""Independent final course/pin review; no model import, training or dispatch."""
import hashlib
import json
from pathlib import Path

ROOT = Path(r"D:\skillloop\output\20261101_wrd_increment57")
DATA = ROOT / "active_dataset57/native_bfc_checkpoint01"
OUT = ROOT / "root_review57/ROOT_NATIVE_CHECKPOINT_REVIEW57.json"


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


entry = read(DATA / "TRAINING_ENTRYPOINT57.json")
for key in ("dataset_manifest", "dataset_pin", "loader", "course", "config", "course_QA"):
    ref = entry[key]
    actual = DATA / ref["path"]
    assert actual.stat().st_size == ref["bytes"] and sha(actual) == ref["sha256"], key
assert entry["unique_targets"] == 1260 and entry["positive_tokens"] == 294828
assert entry["candidate_optimizer_updates"] == 241
assert entry["training_started"] is False
manifest = read(DATA / "ACTIVE_DATASET_MANIFEST57.json")
assert len(manifest["excluded_original_primary_ids"]) == 44
course = read(DATA / "COURSE57_NATIVE.json")
profile_rows = {}
checks = {}
for profile, data in course["profiles"].items():
    phases = data["phases"]
    assert [(p["name"], p["optimizer_updates_candidate"]) for p in phases] == [("contract", 26), ("process", 215)]
    flat = []
    process_anchors = 0
    for phase in phases:
        assert phase["single_pass"] and not phase["repeat_views_to_fill_tail"]
        for step in phase["steps"]:
            batch = step["microbatches"]
            assert 1 <= len(batch) <= phase["accumulation_max"]
            if phase["name"] == "process":
                assert any(r["pool"] in {"real_process", "increment_process"} for r in batch)
                process_anchors += 1
            flat.extend(batch)
    ids = [r["id"] for r in flat]
    assert len(ids) == len(set(ids)) == 1260
    assert sum(r["positive_tokens"] for r in flat) == 294828
    assert sum(r["valid_shifted_target_count"] for r in flat) == 294828
    assert all(r["sequence_tokens"] <= 32768 for r in flat)
    assert not set(ids) & set(manifest["excluded_original_primary_ids"])
    profile_rows[profile] = [(r["id"], r["pool"], r["positive_tokens"], r["positive_token_ids_sha256_u32le"]) for r in flat]
    checks[profile] = {
        "targets": len(ids),
        "positive_tokens": 294828,
        "sequence_tokens": sum(r["sequence_tokens"] for r in flat),
        "short_le16k": sum(r["sequence_tokens"] <= 16384 for r in flat),
        "long_16to32k": sum(16384 < r["sequence_tokens"] <= 32768 for r in flat),
        "process_batches_with_real_anchor": process_anchors,
        "pure_auxiliary_batches": 0,
    }
assert profile_rows["budget_projection"] == profile_rows["full_native53"]
assert checks["budget_projection"]["sequence_tokens"] == 10631405
assert checks["full_native53"]["sequence_tokens"] == 21207839
abi_path = ROOT / "abi_semantic_audit57/ABI_FINAL_QA57.json"
abi = read(abi_path)
assert abi["conflicts"] == 0 and abi["exec_timeout_key_positive_examples"] == 0
assert abi["unique_active_targets"] == 1260
result = {
    "status": "PASS_INDEPENDENT_COURSE_PINS_ORDER_POSITIVE_IDS_ABI_AND_EXCLUSIONS",
    "scope": "Root independently rechecked immutable pins and every course microbatch; feature/tokenizer QA separately pinned, not rerun here.",
    "profiles": checks,
    "same_order_and_positive_token_id_SHA_both_profiles": True,
    "manifest_sha256": sha(DATA / "ACTIVE_DATASET_MANIFEST57.json"),
    "course_sha256": sha(DATA / "COURSE57_NATIVE.json"),
    "config_sha256": sha(DATA / "CONFIG57_NATIVE.json"),
    "entrypoint_sha256": sha(DATA / "TRAINING_ENTRYPOINT57.json"),
    "feature_ready_receipt_sha256": sha(DATA / "CHECKPOINT_READY57.json"),
    "tool_ABI_qa_sha256": sha(abi_path),
    "whole_skill_KEEP_or_consumer_utility_approved": False,
    "weights_loaded": False,
    "training_started": False,
}
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps(result, ensure_ascii=False))
