"""Root independently rechecks frozen content and the old/new label delta."""
import gzip
import hashlib
import json
from pathlib import Path

WORK = Path(r"D:\skillloop\output\20261101_wrd_final_audit58")
DATA = WORK / "active_dataset58/final1260"
OLD = Path(r"D:\skillloop\output\20261101_wrd_increment57/bfc_native_producer_bank57")
NEW = WORK / "training_runtime/bfc_protocol_bank58"


def load(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def records(root):
    rows = {}
    for path in sorted((root / "compiled").glob("*.jsonl.gz")):
        with gzip.open(path, "rt", encoding="utf-8-sig") as stream:
            for line in stream:
                if line.strip():
                    row = json.loads(line)
                    assert row["id"] not in rows
                    rows[row["id"]] = row
    return rows


def positions(row):
    result = {}
    for start, end, component, weight in row["supervision_spans"]:
        for i in range(start, end):
            assert i not in result
            result[i] = (component, weight)
    return result


freeze_path = WORK / "active_dataset58/ACTIVE58_CONTENT_FREEZE.json"
freeze = load(freeze_path)
assert sha(freeze_path) == "5319dfb5d9bfb870aaffab491ae182b8ce1d3ab10523e86f2737703cff09b5ae"
for ref in freeze["files"]:
    path = DATA / ref["path"]
    assert path.is_file() and path.stat().st_size == ref["bytes"] and sha(path) == ref["sha256"]
entry = load(DATA / "TRAINING_ENTRYPOINT58.json")
for ref in entry.values():
    if isinstance(ref, dict) and {"path", "bytes", "sha256"} <= ref.keys():
        path = DATA / ref["path"]
        assert path.stat().st_size == ref["bytes"] and sha(path) == ref["sha256"]
assert (DATA / "ACTIVE_DATASET_MANIFEST57.json").read_bytes() == (DATA / "ACTIVE_DATASET_MANIFEST58.json").read_bytes()
old, new = records(OLD), records(NEW)
assert len(old) == len(new) == 33 and old.keys() == new.keys()
added = 0
changed = []
eos = 0
for rid, before in old.items():
    after = new[rid]
    for key in ("input_ids", "messages", "tools", "rendered_sha256", "total_tokens"):
        assert before[key] == after[key], (rid, key)
    p, q = positions(before), positions(after)
    assert all(q[i] == value for i, value in p.items()), rid
    delta = set(q) - set(p)
    assert all(q[i] == ("F", 0.25) for i in delta), rid
    if delta:
        changed.append(rid)
    added += len(delta)
    eos += sum(after["input_ids"][i] == 151645 for i in delta)
assert added == 650 and len(changed) == eos == 31
assert "increment57-bfc-native-api-0005" not in changed
assert "increment57-bfc-native-api-0033" not in changed
config = load(DATA / "CONFIG58.json")
assert config["candidate_optimizer_updates"] == 241
assert config["candidate_checkpoint_global_steps"] == [0, 26, 80, 134, 188, 241]
assert config["loss"]["per_step_synthetic_coefficient_mass_cap"] == 0.2
assert not config["training_started"] and not config["weights_loaded"]
qa_path = DATA / "INDEPENDENT_FEATURE_COURSE_QA58.json"
result = {
    "status": "PASS_ROOT_FROZEN205_ENTRY_PINS_INPUT_INVARIANTS_AND_ONLY650_TRUSTED_F_DELTA",
    "actual_data_files_verified": len(freeze["files"]),
    "same_33_ids_inputs_messages_tools_and_rendered_bytes": True,
    "original_semantic_positions_components_weights_unchanged": True,
    "new_F_tokens": added,
    "valid_call_records_enhanced": len(changed),
    "new_EOS": eos,
    "API5_and_33_original_masks_kept": True,
    "unique_active_targets": entry["unique_targets"],
    "positive_tokens": entry["positive_tokens"],
    "entrypoint_sha256": sha(DATA / "TRAINING_ENTRYPOINT58.json"),
    "course_sha256": sha(DATA / "COURSE58.json"),
    "config_sha256": sha(DATA / "CONFIG58.json"),
    "independent_actual_features_course_QA_sha256": sha(qa_path),
    "scope": "Root rechecked immutable content and exact mask deltas; independent actual feature/course verifier supplies separate full-array/alpha/denominator checks, not claimed as a root rerun.",
    "training_started": False,
}
output = WORK / "root/ROOT_REVIEW58.json"
output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps(result, ensure_ascii=False))
