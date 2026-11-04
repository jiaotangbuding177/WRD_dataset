"""Independent offline audit. Writes only this review directory."""
import gzip
import hashlib
import json
import struct
from pathlib import Path

OUT = Path(__file__).parent
BASE = OUT.parent
ROOT = BASE.parent
EPISODES = ROOT / "runtime_preflight/episodes"
COMPILED = ROOT / "compiled/c_review_dataset_01"


def sha(value):
    return hashlib.sha256(value.encode("utf-8") if isinstance(value, str) else value).hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def all_strings(value):
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        return sum((all_strings(v) for v in value.values()), [])
    if isinstance(value, list):
        return sum((all_strings(v) for v in value), [])
    return []


report = {"schema": "independent-c-review-mechanical-followup-v1", "reviewer": "separate AI agent; silver; root admission remains false", "root_main_admission": False, "failures": [], "projection_notes": [], "checks": {}}
receipts = read(BASE / "SOURCE_AND_ORIGINAL_ARTIFACT_RECEIPTS.json")
for receipt in receipts["files"]:
    path = Path(receipt["path"])
    if sha(path.read_bytes()) != receipt["sha256"] or path.stat().st_size != receipt["bytes"]:
        report["failures"].append({"receipt_mismatch": str(path)})
for item in receipts["preserved_original_copies"]:
    original = Path(item["original"]["path"])
    preserved = Path(item["preserved_copy"]["path"])
    if original.read_bytes() != preserved.read_bytes():
        report["failures"].append({"preserved_copy_mismatch": str(preserved)})
report["checks"]["receipt_files_hashed"] = len(receipts["files"])
report["checks"]["preserved_pairs_compared"] = len(receipts["preserved_original_copies"])

review = read(BASE / "ORIGINAL_R_LOCAL_REVIEW.json")
proofs = []
for item in review["positive_ranges"]:
    full_r = (BASE / (item["call_id"].split("_")[0] + ".R.txt")).read_text(encoding="utf-8")
    segment = full_r[item["start"]:item["end"]]
    assert segment == item["text"] and sha(segment) == item["sha256"]
    request_path = EPISODES / "C_review_report_01/api_audit" / item["call_id"] / "request.raw.json"
    request = read(request_path)
    assert sha(request_path.read_bytes()) == item["request_sha256"]
    values = all_strings(request["messages"])
    proof = {"range_id": item["id"], "range_identity_sha_pass": True, "prefix_request_sha_pass": True, "all_declared_evidence_substrings_visible": all(any(term in v for v in values) for term in item["delivered_evidence_substrings"]), "missing_evidence_substrings": [term for term in item["delivered_evidence_substrings"] if not any(term in v for v in values)]}
    proofs.append(proof)
    if not proof["all_declared_evidence_substrings_visible"]:
        report["failures"].append(proof)
report["range_prefix_evidence"] = proofs
report["checks"]["original_positive_ranges_verified"] = len(proofs)
report["checks"]["original_positive_characters"] = sum(x["end"] - x["start"] for x in review["positive_ranges"])

by_call = {}
for item in review["complete_disjoint_R_mask_partition"]:
    by_call.setdefault(item["call_id"], []).append(item)
for call_id, items in by_call.items():
    full_r = (BASE / (call_id.split("_")[0] + ".R.txt")).read_text(encoding="utf-8")
    cursor = 0
    for item in items:
        assert item["start"] == cursor and sha(full_r[item["start"]:item["end"]]) == item["sha256"]
        cursor = item["end"]
    assert cursor == len(full_r)
report["checks"]["complete_R_mask_partitions_verified"] = len(by_call)

state = read(BASE / "NEW_AUTHORED_REAL_STATE_COST_STOP.input.json")
source_l = read(EPISODES / "C_L_no_skill_01/workspace/inputs/task/source_input.json")
source_e = read(EPISODES / "C_E_no_skill_01/workspace/inputs/task/source_input.json")
assert state["cases"]["L"]["original_user_requests"] == [{"role": m["role"], "content": m["content"]} for m in source_l["messages"]]
assert state["cases"]["E"]["original_user_requests"] == [{"role": source_e["current_original_request"]["role"], "content": source_e["current_original_request"]["content"]}]
mapping = {("L", "A"): "C_L_skill_01", ("L", "B"): "C_L_no_skill_01", ("E", "A"): "C_E_no_skill_01", ("E", "B"): "C_E_skill_01"}
delivery_matches = []
for (case, arm), episode in mapping.items():
    full = (EPISODES / episode / "workspace/outputs/deliverable.md").read_text(encoding="utf-8")
    value = state["cases"][case]["actual_deliverables"][arm]
    # Original phase1 deliberately removes a final newline. Content and all other chars survive.
    assert value == full or value == full.rstrip("\n")
    delivery_matches.append({"case": case, "arm": arm, "episode": episode, "exact_file_text_equal": value == full, "only_terminal_newline_omitted": value != full, "state_characters": len(value), "original_characters": len(full)})
    quality = read(BASE / "preserved_original_artifacts/quality_blind.json")
    if state["cases"][case]["AI_blind_quality"][arm] != quality["cases"][case][arm]:
        def diff(a, b, path):
            if type(a) != type(b):
                return [{"path": path, "state": a, "raw": b}]
            if isinstance(a, dict):
                return sum((diff(a.get(k), b.get(k), path + "." + k) for k in a.keys() | b.keys()), [])
            if isinstance(a, list):
                return sum((diff(x, y, path + "." + str(i)) for i, (x, y) in enumerate(zip(a, b))), [])
            return [] if a == b else [{"path": path, "state": a, "raw": b}]
        differences = diff(state["cases"][case]["AI_blind_quality"][arm], quality["cases"][case][arm], case + arm)
        assert all(d["path"].endswith("primary_deduction_note") and d["state"] is None for d in differences)
        report["projection_notes"].append({"quality_projection_omits_primary_note": differences, "dimension_items_and_scores_unchanged": True})
report["checks"]["complete_source_user_contents_preserved"] = True
report["checks"]["raw_AI_quality_dimension_items_and_scores_preserved"] = True
report["delivery_identity"] = delivery_matches
usage = state["actual_usage"]
assert usage["NoSkill_total"]["tokens"] == 216325 + 161545 == 377870
assert usage["Skill_total"]["tokens"] == 1156866 + 864484 == 2021350
assert usage["pre_review"]["known_tokens"] + usage["current_review_after_terminal"]["known_tokens"] == usage["all_stages_after_terminal"]["known_tokens"] == 8660547
report["checks"]["state_cost_arithmetic"] = {"NoSkill_tokens": 377870, "Skill_tokens": 2021350, "ratio_tokens": 2021350 / 377870, "ratio_calls": 30 / 7, "pre_review": 7367237, "review": 1293310, "terminal_known": 8660547}

compilation = read(COMPILED / "COMPILATION_REPORT.json")
bank_records = []
for item in compilation["files"]:
    file = COMPILED / item["path"]
    assert sha(file.read_bytes()) == item["sha256"] and file.stat().st_size == item["bytes"]
    for line in gzip.open(file, "rt", encoding="utf-8"):
        record = json.loads(line)
        ids = record["input_ids"]
        assert len(ids) == record["total_tokens"] <= 32768
        assert sha(struct.pack("<" + "I" * len(ids), *ids)) == record["input_ids_sha256_u32le"]
        spans = record["supervision_spans"]
        prior_end = 0
        for start, end, component, weight in spans:
            assert 0 <= start < end <= len(ids) and start >= prior_end and weight == 0.25
            prior_end = end
        assert sum(b - a for a, b, _, _ in spans) == record["supervised_tokens"]
        assert record["original_record_metadata"]["root_main_admission"] is False
        assert record["second_tokenizer_independently_called"] is True and record["tokenizer_pair_proof"] == "independent_call_equal"
        assert record["source_group_id"] == receipts["source_group_id"] and set(record["source_ids"]) <= set(receipts["source_ids"])
        if sorted(record["source_ids"]) != sorted(receipts["source_ids"]):
            report["projection_notes"].append({"local_source_subset": record["id"], "record_sources": record["source_ids"], "parent_union_sources": receipts["source_ids"], "same_group_retained": True, "note": "L local execution did not read E source; actual ancestor subset is correctly retained while all views stay in one parent split group."})
        bank_records.append({"id": record["id"], "total_tokens": record["total_tokens"], "supervised_tokens": record["supervised_tokens"], "supervised_tokens_by_component": record["supervised_tokens_by_component"], "components": sorted(set(s[2] for s in spans)), "bank": record["bank"], "root_main_admission": False})
assert len(bank_records) == compilation["counts"]["sequences"] == 4
assert sum(x["supervised_tokens"] for x in bank_records) == compilation["counts"]["supervised_tokens"] == 1496
report["compiled_bank_records"] = bank_records
report["checks"]["compiled_file_hashes_span_geometry_input_arrays_count_group_pass"] = True
report["two_tokenizer_caveat"] = "All 4 compiled records attest an independent second call. This audit checked those attestations and array identity hashes; it did not independently execute a third tokenizer run."
report["mechanical_status"] = "PASS" if not report["failures"] else "FAIL"
OUT.mkdir(parents=True, exist_ok=True)
(OUT / "MECHANICAL_AUDIT.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({"status": report["mechanical_status"], "failures": report["failures"], "checks": report["checks"]}, ensure_ascii=False, indent=2))
