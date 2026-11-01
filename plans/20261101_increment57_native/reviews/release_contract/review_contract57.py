"""Read-only independent release-contract review. No model or train imports."""
import hashlib
import json
from pathlib import Path

PLAN = Path(r"D:\skillloop\output\20261025_wrd_training_dataset\git_release\plans\20261101_increment57_native")
OUT = Path(r"D:\skillloop\output\20261101_wrd_increment57\release_review57")


def read(name):
    return json.loads((PLAN / name).read_text(encoding="utf-8-sig"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


config = read("CONFIG57_NATIVE.json")
entry = read("TRAINING_ENTRYPOINT57.json")
course = read("COURSE57_NATIVE.json")
status = read("CONSUMPTION_STATUS57.json")
pins = {}
for name in ("dataset_manifest", "dataset_pin", "loader", "course", "config", "course_QA"):
    ref = entry[name]
    target = PLAN / ref["path"]
    assert target.stat().st_size == ref["bytes"] and sha(target) == ref["sha256"], name
    pins[name] = True
assert config["unique_targets"] == entry["unique_targets"] == 1260
assert config["positive_tokens_exposed"] == entry["positive_tokens"] == 294828
assert config["candidate_optimizer_updates"] == entry["candidate_optimizer_updates"] == 241
assert config["max_training_sequence_length"] == 32768
assert config["training_started"] is False and config["weights_loaded"] is False
assert config["optimizer_updates_executed"] == 0
profiles = {}
order = []
for name, profile in course["profiles"].items():
    phases = profile["phases"]
    assert [(p["name"], len(p["steps"])) for p in phases] == [("contract", 26), ("process", 215)]
    rows = [r for phase in phases for step in phase["steps"] for r in step["microbatches"]]
    ids = [r["id"] for r in rows]
    assert len(ids) == len(set(ids)) == 1260
    assert sum(r["positive_tokens"] for r in rows) == 294828
    assert max(r["sequence_tokens"] for r in rows) <= 32768
    process = phases[1]
    assert all(any(r["pool"] in {"real_process", "increment_process"} for r in step["microbatches"]) for step in process["steps"])
    order.append([(r["id"], r["positive_token_ids_sha256_u32le"]) for r in rows])
    profiles[name] = {
        "targets": len(rows),
        "positive_tokens": sum(r["positive_tokens"] for r in rows),
        "sequence_tokens": sum(r["sequence_tokens"] for r in rows),
        "short_le16k": sum(r["sequence_tokens"] <= 16384 for r in rows),
        "long16to32k": sum(r["sequence_tokens"] > 16384 for r in rows),
        "contract_updates": 26,
        "process_updates": 215,
        "process_batches_with_real_anchor": 215,
    }
assert order[0] == order[1]
assert profiles["budget_projection"]["sequence_tokens"] == 10631405
assert profiles["full_native53"]["sequence_tokens"] == 21207839
ledger = status["closed_cost_ledger"]["global"]
assert ledger == {
    "provider_requests": 83,
    "native_sessions": 11,
    "known_IO_tokens": 5896235,
    "unreconciled_strict_IO_reservation": 1032768,
    "conservative_IO_charge": 6929003,
}
assert status["whole_skill_KEEP_qualified"] is False
assert status["student_training_or_inference_executed"] is False
assert all(status["case2"][arm]["status"] == "SKIP_BUDGET_RESERVE" for arm in ["V0", "V1", "Q"])
matrix = status["task_end_deterministic_checks"]["final_criterion_matrix"]
assert {r["arm"]: r["passed_criteria"] for r in matrix} == {"NS": 6, "V0": 5, "V1": 5}
assert all(r["criteria"]["5"] == ("PASS" if r["arm"] == "NS" else "FAIL") for r in matrix)
files = ["PLAN.md", "ACTUAL_DATA_REPORT.md", "CONFIG57_NATIVE.json", "COURSE57_NATIVE.json", "TRAINING_ENTRYPOINT57.json", "CONSUMPTION_STATUS57.json", "SPARK_DEPLOYMENT_CONTRACT57.md"]
snapshots = {n: {"sha256": sha(PLAN / n), "bytes": (PLAN / n).stat().st_size} for n in files}
lines = (PLAN / "CONSUMPTION_STATUS57.json").read_text(encoding="utf-8").splitlines()
scope_line = next((i for i, line in enumerate(lines, 1) if '"Q_rubric_or_tests_not_authored_by_outer"' in line), None)
notes = []
if scope_line:
    notes.append({
        "severity": "METADATA_SCOPE_CLARIFICATION",
        "file": "CONSUMPTION_STATUS57.json",
        "line": scope_line,
        "description": "Q_rubric_or_tests_not_authored_by_outer=true should explicitly scope model-Q rubric versus newly authored outer task-end deterministic scorer. Other fields already distinguish task-end from model Q; data and evidence are unaffected.",
    })
notes.append({
    "severity": "FUTURE_CAUSAL_ATTRIBUTION_DESIGN_NOTE_NOT_DATA_BLOCKER",
    "file": "PLAN.md",
    "description": "Old1227 versus new1260 also changes the schedule233-to241 and pure auxiliary batches8-to0. Equal device-hour replay controls extra compute; isolate curriculum mixing separately before attributing an experimental gain solely to new experience. No gain is currently claimed.",
})
receipt = {
    "schema": "wrd57-independent-public-contract-review-v1",
    "status": "PASS_CORE_DATA_TRAINING_CONSUMPTION_AND_DEPLOYMENT_CONTRACT",
    "entrypoint_pins": pins,
    "profiles": profiles,
    "same_ID_order_and_positive_token_hashes": True,
    "closed_ledger": ledger,
    "manual_reading_confirmed": {
        "33_windows_one_producer_not33_independent_tasks": True,
        "401_contract_232_real_process_627_auxiliary_separate": True,
        "provider_R_preserved_and_original_vs_authored_state_distinguished": True,
        "no_future_Q_in_earlier_state_claims_match_frozen_policy": True,
        "case1_formula_failure_not_KEEP_or_model_Q": True,
        "Spark_ARM_service_separate_from_fixed_amd64_OpenClaw_tool_loop": True,
        "training32K_separate_from_candidate128K_YaRN_not_deployed": True,
        "official_history_thinking_policy_distinct_from_frozen_R_variant": True,
        "original226_and_reserved_source_closure_isolation_preserved": True,
        "no_student_training_or_effect_claim": True,
    },
    "notes": notes,
    "reviewed_file_snapshots": snapshots,
    "scope_limits": "Contract and actual course metadata review only; did not repeat HF/bin tests, inspect every raw source, run models, native sessions, training, package restore, Git push or remote cold download.",
    "new_provider_or_native_calls": 0,
    "repository_files_modified": False,
}
OUT.mkdir(parents=True, exist_ok=True)
target = OUT / "INDEPENDENT_RELEASE_CONTRACT_REVIEW57.json"
target.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"receipt": str(target), "sha256": sha(target), "notes": notes, "profiles": profiles}, ensure_ascii=False))
