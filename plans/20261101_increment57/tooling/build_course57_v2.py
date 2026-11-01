"""Prepare the reviewed active57 mixed course. No training or model imports.

Preserves frozen v1 files. The v2 process phase separates real-source ordering
from auxiliary-family ordering, then distributes its unavoidable all-auxiliary
updates evenly across the phase.
"""
from pathlib import Path
from decimal import Decimal
from array import array
import argparse
import collections
import hashlib
import importlib.util
import json
import shutil
import sys

SEED = 20261101
V1_PINS = {
    "COURSE57.json": "5eccca9b2944c2d22f85aab096285e29a0074e03a8f0044e77bf6f878815dd68",
    "CONFIG57.json": "16b1bd5bb4ec9dbfe2d7e9aeb90ef409670ff70fd615230bcb5c219ef287ff80",
    "COURSE_QA57.json": "3378c94f7c8331a6921964ad38ccb15bdf89f862884b38d06419109e53ff03c7",
}
V1_HELPER_SHA = "7ad2def36f65ba893d4da6bfd2da6d58b08b369806ebd01f1876e344c189875d"


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def require(value, message):
    if not value:
        raise ValueError(message)


def module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def actual_rows(root, base_root, package11_root, helper):
    loader = module(root / "tooling/active_loader57.py", "active57_v2_reviewed_loader")
    _, manifest = loader.validated_manifest(root)
    components = load(loader.verified(root, manifest["source_component_map"]))["source_to_component"]
    ledger = load(root / "ACTIVE_TARGET_LEDGER57.json")["profiles"]
    result = {}
    for profile in manifest["profiles"]:
        records = []
        by_id = {r["id"]: r for r in ledger[profile]}
        for item in loader.iter_features(root, base_root, package11_root, profile=profile, with_metadata=True):
            features = item["features"]
            sources = [s for s in item["source_ids"] if s in components]
            ordering_group = ("enterprise:" + "|".join(sorted({components[s] for s in sources}))) if sources else "declared:" + str(item["source_group_id"])
            positive = [v for v in features["labels"] if v != -100]
            mass = sum((Decimal(str(w)) for label, w in zip(features["labels"], features["loss_weights"]) if label != -100), Decimal(0))
            record = {"id": item["id"], "pool": item["pool"], "stage": item["stage"], "bank": item["bank"],
                      "ordering_group": ordering_group, "sequence_tokens": len(features["input_ids"]),
                      "positive_tokens": len(positive), "valid_shifted_target_count": sum(v != -100 for v in features["labels"][1:]),
                      "weighted_mass": str(mass), "positive_token_ids_sha256_u32le": helper.token_sha(positive)}
            pin = by_id[record["id"]]
            require(record["positive_tokens"] == pin["positive_tokens"] and record["positive_token_ids_sha256_u32le"] == pin["positive_token_ids_sha256_u32le"], "V2_ACTUAL_TARGET_DIFFERS_FROM_PINNED_LEDGER")
            record["positive_by_component"] = pin["positive_by_component"]
            records.append(record)
        require(len(records) == len({r["id"] for r in records}) == manifest["actual_counts"][profile]["unique_targets"], "V2_ACTIVE_ROW_COUNT_MISMATCH")
        result[profile] = records
    return manifest, result


def mixed_process_phase(records, offset, helper):
    real = helper.order_source_balanced([r for r in records if r["pool"] in {"real_process", "increment_process"}])
    auxiliary = helper.order_source_balanced([r for r in records if r["pool"] == "synthetic"])
    require(len(real) == 199 and len(auxiliary) == 627, "V2_FROZEN_ACTIVE_PROCESS_COUNTS_CHANGED")
    number_batches = (len(records) + 3) // 4
    pure_count = number_batches - len(real)
    require(number_batches == 207 and pure_count == 8, "V2_BATCH_COUNT_CHANGED")
    # Midpoints of eight equal intervals: zero-based 12,38,...,194. The final
    # partial batch therefore contains a real item and is flushed with two rows.
    pure_positions = {((2 * i + 1) * number_batches) // (2 * pure_count) for i in range(pure_count)}
    require(len(pure_positions) == pure_count and number_batches - 1 not in pure_positions, "V2_PURE_BATCH_SPACING_INVALID")
    steps = []
    real_index = auxiliary_index = 0
    for index in range(number_batches):
        capacity = min(4, len(records) - 4 * index)
        group = []
        if index not in pure_positions:
            group.append(real[real_index])
            real_index += 1
        needed = capacity - len(group)
        group.extend(auxiliary[auxiliary_index:auxiliary_index + needed])
        auxiliary_index += needed
        require(len(group) == capacity, "V2_AUXILIARY_ALLOCATION_UNDERFLOW")
        summary = helper.summarise(group)
        steps.append({"phase_step_one_based": index + 1, "global_step_one_based": offset + index + 1,
                      "microbatches": group, "actual_accumulation_count": len(group),
                      "valid_shifted_target_denominator": summary["valid_shifted_target_denominator"],
                      "weighted_mass": summary["weighted_mass_exposed"], "synthetic_weighted_mass": summary["synthetic_weighted_mass"],
                      "synthetic_fraction_of_weighted_mass": summary["synthetic_fraction_of_weighted_mass"],
                      "has_existing_process": any(r["pool"] == "real_process" for r in group),
                      "has_new_reviewed_process": any(r["pool"] == "increment_process" for r in group)})
    require(real_index == len(real) and auxiliary_index == len(auxiliary), "V2_PROCESS_ALLOCATION_NOT_EXHAUSTIVE")
    all_rows = [r for step in steps for r in step["microbatches"]]
    require(len(all_rows) == len({r["id"] for r in all_rows}) == len(records), "V2_PROCESS_DUPLICATE_OR_OMITTED_TARGET")
    positions = sorted(i + 1 for i in pure_positions)
    return {"name": "process", "accumulation_max": 4, "microbatch": 1, "single_pass": True,
            "repeat_views_to_fill_tail": False, "flush_final_partial_accumulation": True,
            "ordering": "real source components and auxiliary families are separately seed-balanced; one real row in each of 199 batches, eight pure auxiliary batches at equal-interval midpoints; fill remaining slots with ordered auxiliary rows",
            "optimizer_updates_candidate": len(steps), "summary": helper.summarise(all_rows), "steps": steps,
            "real_process_batches": len(real), "pure_auxiliary_batch_phase_steps": positions,
            "pure_auxiliary_batch_global_steps": [offset + n for n in positions],
            "pure_auxiliary_minimum_given_one_real_per_batch_and_no_repetition": pure_count}


def main():
    require(not sys.flags.optimize, "OPTIMIZED_PYTHON_REJECTED")
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--base-root", type=Path, required=True)
    parser.add_argument("--package11-root", type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    outputs = ["COURSE57_v2.json", "CONFIG57_v2.json", "COURSE_QA57_v2.json", "TRAINING_ENTRYPOINT57.json"]
    require(not any((root / name).exists() for name in outputs), "V2_COURSE_ALREADY_FROZEN")
    for name, pin in V1_PINS.items():
        require(sha(root / name) == pin, "FROZEN_V1_CHANGED")
    helper_path = root / "tooling/build_course57.py"
    require(sha(helper_path) == V1_HELPER_SHA, "UNTRUSTED_V1_HELPER")
    helper = module(helper_path, "active57_v1_fixed_helpers")
    manifest, profiles = actual_rows(root, args.base_root, args.package11_root, helper)
    v1 = load(root / "COURSE57.json")
    course = {"schema": "wrd57-active-mixed-real-auxiliary-single-pass-course-v2-not-launcher", "design_revision": "5.0.57",
              "change_id": "ALG-20261101-03", "seed": SEED, "supersedes_as_default": "COURSE57.json",
              "v1_preserved": V1_PINS, "same_adapter_and_optimizer_across_phases": True,
              "profiles_are_mutually_exclusive": True, "profiles": {}, "training_started": False}
    for profile, records in profiles.items():
        contract = [r for r in records if r["pool"] == "contract_optional"]
        p1 = helper.make_phase(contract, "contract", 16, 0)
        require(p1 == v1["profiles"][profile]["phases"][0], "V2_CONTRACT_ORDER_CHANGED")
        p2 = mixed_process_phase([r for r in records if r["pool"] != "contract_optional"], len(p1["steps"]), helper)
        steps = p1["steps"] + p2["steps"]
        all_rows = [r for step in steps for r in step["microbatches"]]
        require(len(all_rows) == len({r["id"] for r in all_rows}) == len(records), "V2_COURSE_DUPLICATE_OR_OMITTED_TARGET")
        require(not set(manifest["excluded_original_primary_ids"]) & {r["id"] for r in all_rows}, "V2_REVOKED_TARGET")
        summary = helper.summarise(all_rows)
        require(summary == v1["profiles"][profile]["summary"], "V2_COURSE_TOTALS_DIFFER_FROM_V1")
        require(summary["synthetic_fraction_of_weighted_mass"] <= .2 and p2["summary"]["synthetic_fraction_of_weighted_mass"] <= .2, "V2_GLOBAL_AUXILIARY_MASS_CAP")
        fractions = [s["synthetic_fraction_of_weighted_mass"] for s in p2["steps"]]
        pure = [s["phase_step_one_based"] for s in p2["steps"] if not s["has_existing_process"] and not s["has_new_reviewed_process"]]
        require(pure == p2["pure_auxiliary_batch_phase_steps"] and len(pure) == 8, "V2_PURE_AUXILIARY_BATCH_COUNT")
        require(p2["steps"][-1]["actual_accumulation_count"] == 2 and (p2["steps"][-1]["has_existing_process"] or p2["steps"][-1]["has_new_reviewed_process"]), "V2_FINAL_PARTIAL_FLUSH_INVALID")
        course["profiles"][profile] = {"active_manifest_sha256": sha(root / "ACTIVE_DATASET_MANIFEST57.json"), "phases": [p1, p2],
            "summary": summary, "optimizer_updates_candidate": len(steps), "last_partial_contract": 1, "last_partial_process": 2,
            "batch_mass_audit": {"process_batches": len(p2["steps"]), "real_process_batches": 199,
                "pure_auxiliary_batches": len(pure), "pure_auxiliary_phase_steps": pure,
                "local_synthetic_fraction_over20percent_batches": sum(v > .2 for v in fractions),
                "local_synthetic_fraction100percent_batches": sum(v == 1 for v in fractions),
                "max_local_synthetic_fraction": max(fractions),
                "global20percent_is_not_a_local_batch_cap_or_gradient_norm_claim": True}}
    ids = lambda profile: [[r["id"] for r in step["microbatches"]] for phase in course["profiles"][profile]["phases"] for step in phase["steps"]]
    profile_names = list(course["profiles"])
    require(ids(profile_names[0]) == ids(profile_names[1]), "V2_PROFILE_BATCH_ID_ORDER_DIFFERS")
    default = course["profiles"][manifest["default_profile"]]
    config = load(root / "CONFIG57.json")
    config.update({"schema": "wrd57-active-mixed-real-auxiliary-sft-config-v2-not-launcher", "course_file": "COURSE57_v2.json",
                   "default_training_entrypoint": "TRAINING_ENTRYPOINT57.json", "course_version": 2,
                   "process_batch_mixing": {"real_process_rows": 199, "auxiliary_rows": 627, "updates": 207,
                       "real_process_batches": 199, "pure_auxiliary_batches": 8,
                       "pure_auxiliary_phase_steps": default["phases"][1]["pure_auxiliary_batch_phase_steps"],
                       "pure_auxiliary_batches_evenly_distributed": True, "no_tail_clustering": True},
                   "v1_config_preserved_sha256": V1_PINS["CONFIG57.json"],
                   "weight005_is_not_claimed_to_bound_adam_parameter_update_or_gradient_norm": True})
    write(root / "COURSE57_v2.json", course)
    config["course_sha256"] = sha(root / "COURSE57_v2.json")
    write(root / "CONFIG57_v2.json", config)
    shutil.copyfile(Path(__file__), root / "tooling/build_course57_v2.py")
    qa = {"schema": "wrd57-actual-feature-mixed-course-v2-QA", "status": "PASS_ACTUAL_FEATURES_199_REAL_BATCHES_8_SPREAD_AUX_BATCHES_NO_REPEAT_OR_OMISSION",
          "actual_four_features_reread_both_profiles": True, "cross_profile_each_batch_ID_order_identical": True,
          "contract_batches_identical_to_v1": True, "each_active_ID_exactly_once": True, "excluded44_IDs_absent": True,
          "profiles": {p: {"summary": v["summary"], "optimizer_updates_candidate": v["optimizer_updates_candidate"],
              "phase_updates": [len(x["steps"]) for x in v["phases"]], "batch_mass_audit": v["batch_mass_audit"]} for p, v in course["profiles"].items()},
          "course_sha256": sha(root / "COURSE57_v2.json"), "config_sha256": sha(root / "CONFIG57_v2.json"),
          "source_script_sha256": sha(Path(__file__)), "v1_artifacts_before_and_after": V1_PINS,
          "model_weights_loaded": False, "forward_or_backward_executed": False, "optimizer_updates_executed": 0, "training_started": False}
    for name, pin in V1_PINS.items():
        require(sha(root / name) == pin, "V1_WAS_MUTATED_WHILE_BUILDING_V2")
    write(root / "COURSE_QA57_v2.json", qa)
    ref = lambda name: {"path": name, "bytes": (root / name).stat().st_size, "sha256": sha(root / name)}
    entry = {"schema": "wrd57-default-active-course-training-entrypoint-not-launcher", "design_revision": "5.0.57", "course_version": 2,
             "status": "CPU_DATA_AND_COURSE_PREPARED_NO_TRAINING_STARTED", "default_profile": manifest["default_profile"],
             "profiles_are_mutually_exclusive": True, "dataset_manifest": ref("ACTIVE_DATASET_MANIFEST57.json"),
             "dataset_pin": ref("ACTIVE_DATASET_PIN57.json"), "loader": ref("tooling/active_loader57.py"),
             "course": ref("COURSE57_v2.json"), "config": ref("CONFIG57_v2.json"), "course_QA": ref("COURSE_QA57_v2.json"),
             "unique_targets": default["summary"]["unique_targets"], "positive_tokens": default["summary"]["positive_tokens_exposed"],
             "candidate_optimizer_updates": default["optimizer_updates_candidate"], "superseded_default_only_v1_preserved": V1_PINS,
             "old_manifest_course_pointer_null_is_pre_course_snapshot_not_default_course": True,
             "training_execution_authorized": False, "model_weights_loaded": False, "training_started": False}
    write(root / "TRAINING_ENTRYPOINT57.json", entry)
    print(json.dumps({"status": qa["status"], "profiles": qa["profiles"], "course_sha256": qa["course_sha256"],
                      "config_sha256": qa["config_sha256"], "qa_sha256": sha(root / "COURSE_QA57_v2.json"),
                      "entrypoint_sha256": sha(root / "TRAINING_ENTRYPOINT57.json")}))


if __name__ == "__main__":
    main()
