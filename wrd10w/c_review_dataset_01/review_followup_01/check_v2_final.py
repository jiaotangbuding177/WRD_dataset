import gzip
import hashlib
import json
from pathlib import Path

import numpy as np

OUT = Path(__file__).parent
BASE = OUT.parent
ROOT = BASE.parent
V2 = BASE / "semantic_revision_02"
COMPILED = ROOT / "compiled/c_review_dataset_02"


def sha(value):
    return hashlib.sha256(value).hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_bank(path):
    result = {}
    for file in Path(path).glob("*.train.*.jsonl.gz"):
        for line in gzip.open(file, "rt", encoding="utf-8"):
            record = json.loads(line)
            result[record["id"]] = record
    return result


report = read(COMPILED / "COMPILATION_REPORT.json")
dense_receipt = read(V2 / "DENSE_ARRAY_RECEIPT.json")
qa = read(V2 / "INDEPENDENT_DUAL_TOKENIZER_QA.json")
zeros = read(V2 / "EXPLICIT_ZERO_ERROR_RANGES.json")
for receipt in [dense_receipt["source_compilation_report"], dense_receipt["array_file"]]:
    path = Path(receipt["path"])
    assert sha(path.read_bytes()) == receipt["sha256"] and path.stat().st_size == receipt["bytes"]
assert qa["status"] == "PASS" and qa["counts"] == {"records_checked": 4, "direct_dual_tokenizer_canaries": 4}
assert qa["compiled_report_sha256"] == sha((COMPILED / "COMPILATION_REPORT.json").read_bytes())
assert qa["actual_recount"]["supervised_tokens"] == 1458 and qa["actual_recount"]["input_tokens"] == 76289
for file_receipt in report["files"]:
    file = COMPILED / file_receipt["path"]
    assert sha(file.read_bytes()) == file_receipt["sha256"] and file.stat().st_size == file_receipt["bytes"]

records = load_bank(COMPILED)
assert len(records) == 4
arrays = np.load(dense_receipt["array_file"]["path"], allow_pickle=False)
results = []
for entry in dense_receipt["records"]:
    record = records[entry["id"]]
    prefix = entry["array_prefix"]
    ids = arrays[prefix + "_input_ids"]
    labels = arrays[prefix + "_labels"]
    mask = arrays[prefix + "_loss_mask"]
    weights = arrays[prefix + "_loss_weights"]
    assert ids.dtype == np.dtype("uint32") and labels.dtype == np.dtype("int64")
    assert mask.dtype == np.dtype("uint8") and weights.dtype == np.dtype("float32")
    assert ids.shape == labels.shape == mask.shape == weights.shape == (record["total_tokens"],)
    assert np.array_equal(ids, np.asarray(record["input_ids"], dtype="<u4"))
    expected_mask = np.zeros(len(ids), dtype="u1")
    expected_weights = np.zeros(len(ids), dtype="<f4")
    for start, end, component, weight in record["supervision_spans"]:
        assert 0 <= start < end <= len(ids) <= 32768 and weight == 0.25
        assert not np.any(expected_mask[start:end])
        expected_mask[start:end] = 1
        expected_weights[start:end] = weight
    expected_labels = np.where(expected_mask, ids, -100).astype("<i8")
    assert np.array_equal(mask, expected_mask) and np.array_equal(weights, expected_weights)
    assert np.array_equal(labels, expected_labels)
    assert int(mask.sum()) == record["supervised_tokens"] == entry["supervised_tokens"]
    assert sha(ids.astype("<u4", copy=False).tobytes()) == entry["input_ids_u32le_sha256"] == record["input_ids_sha256_u32le"]
    assert sha(labels.astype("<i8", copy=False).tobytes()) == entry["labels_i64le_sha256"]
    assert sha(weights.astype("<f4", copy=False).tobytes()) == entry["loss_weights_f32le_sha256"]
    assert sha(mask.tobytes()) == entry["loss_mask_u8_sha256"]
    assert record["original_record_metadata"]["root_main_admission"] is False
    results.append({"id": entry["id"], "input_tokens": len(ids), "supervised_tokens": int(mask.sum()), "all_4_dense_arrays_exactly_reconstructed_from_spans": True, "all_4_array_sha_pass": True})

old_records = load_bank(ROOT / "compiled/c_review_dataset_01")
r_id = next(key for key in records if key.endswith("_local_R"))
old_r, new_r = old_records[r_id], records[r_id]
assert old_r["input_ids"] == new_r["input_ids"]
assert old_r["messages"] == new_r["messages"] and old_r["tools"] == new_r["tools"]
def positions(record):
    return {i for start, end, _, _ in record["supervision_spans"] for i in range(start, end)}
old_positions, new_positions = positions(old_r), positions(new_r)
assert new_positions < old_positions and len(old_positions) == 425 and len(new_positions) == 387
removed_tokens = sorted(old_positions - new_positions)
assert len(removed_tokens) == 38 and not (new_positions - old_positions)
revised_r = read(V2 / "ORIGINAL_R_LOCAL_REVIEW.json")
withdrawn = [item for item in zeros["exact_known_spans"] if item.get("category", "").startswith("QUALIFIER_PRESERVATION_OVERGENERALIZED_WITHDRAWN")]
assert [(item["start"], item["end"]) for item in withdrawn] == [(2499, 2635), (5818, 5889)]
full_r = (BASE / "0009.R.txt").read_text(encoding="utf-8")
for item in withdrawn:
    assert item["mask"] == 0 and full_r[item["start"]:item["end"]] == item["text"]
    assert sha(item["text"].encode("utf-8")) == item["sha256"]
    assert all(not (approved["start"] < item["end"] and item["start"] < approved["end"]) for approved in revised_r["positive_ranges"] if approved["call_id"] == item["call_id"])

counts = report["counts"]
assert counts["sequences"] == 4 and counts["input_tokens"] == 76289 and counts["supervised_tokens"] == 1458
assert counts["component_R"] == 519 and counts["component_A"] == 781 and counts["component_D"] == 158
result = {
    "schema": "independent-c-review-v2-final-dense-array-audit-v1",
    "status": "PASS_SCOPED_PENDING_ROOT",
    "reviewer_identity": "Separate AI assistant; silver, not human gold",
    "root_main_admission": False,
    "compiled_report": {"path": str(COMPILED / "COMPILATION_REPORT.json"), "sha256": sha((COMPILED / "COMPILATION_REPORT.json").read_bytes())},
    "dense_npz": dense_receipt["array_file"],
    "records": results,
    "counts": {"sequences": 4, "input_tokens": 76289, "supervised_tokens": 1458, "original_R": 387, "new_authored_R": 132, "A": 781, "D": 158},
    "original_R_v1_v2_comparison": {"input_ids_identical": True, "messages_identical": True, "tools_identical": True, "v1_supervised_tokens": 425, "v2_supervised_tokens": 387, "removed_token_positions": removed_tokens, "removed_tokens": 38, "newly_supervised_token_positions": []},
    "withdrawn_character_ranges_zero_and_disjoint_from_v2_positive_R": [[2499, 2635], [5818, 5889]],
    "withdrawn_characters": 207,
    "dual_tokenizer_QA": {"status": qa["status"], "direct_pairs": 4, "receipt_reconciled": True, "additional_tokenizer_run_by_this_audit": False},
    "labels_unshifted": True,
    "nonowned_labels_minus100_mask0_weight0": True,
    "training_exposure_rule": "Use v2 only for these owners; retain v1 as history and never add its positive-loss view to v2.",
    "no_model_training_or_native_call": True,
}
(OUT / "V2_FINAL_AUDIT.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({"status": result["status"], "counts": result["counts"], "R_removed_tokens": 38, "dense_arrays_checked": 16}))
