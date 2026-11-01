"""CPU-only WRD55 course compiler/verifier; never imports a model framework.

Run from a trusted Git checkout with --loader pointing to its reviewed stdlib
curriculum_loader11.py. Restored payload Python source is never imported.
The default mode verifies the existing FULL_COURSE55.json and STATS55.json;
--build creates these two deterministic planning files before verifying them.
"""
import argparse
import copy
import hashlib
import importlib.util
import json
import math
import random
import sys
from array import array
from collections import Counter, defaultdict
from decimal import Decimal
from pathlib import Path

sys.dont_write_bytecode = True
LOADER_SHA = "a2d5f03fb9dec90763b238c5c499199176f1eddbf54b935475274981bc952c1c"
PINS = {
    "base_main": "9aace2dc6b39d0dde3bafbf9f7f3d6763e485609017dd70a5c40c17a2c30277e",
    "base_payload_manifest": "88e0f8b6bd19d02cade6dbad89d60ebea15e254ceb5193b58facdc89b8bfd83d",
    "base_array_index": "712c96c0e483c6d171f3a245a83364ab217593004796404b4ce60917c4c60c4a",
    "full_native53": "a209934dac8dfe0eb5d91ef200d07fe07dd5adf2603c7c89ee0a811a4799778a",
    "budget_projection": "70046fa55828249718849968a29ed2bee95940f3390cc10a31d84e8e1ab84321",
    "source_exposure_schedule": "8652f318cbbc88e9ab117e56185be4724c2ad692f9467dc35afddf21ad214593",
    "source_real_exposure_control": "bd712a47cb1164018d1ac559956424db7b59f7227e2426dc4109d1c701217034",
}
PROFILE_DIRS = {"budget_projection": "budget_curriculum01", "full_native53": "curriculum01"}
SEED = 20261101


def require(ok, message):
    if not ok:
        raise ValueError(message)


def sha(path):
    result = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for data in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(data)
    return result.hexdigest()


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def write(path, obj):
    Path(path).write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def mass(value):
    return Decimal(str(value))


def summary(records):
    workflow_stages = Counter(
        r["stage"].split("_", 1)[0] if r["stage"].split("_", 1)[0] in {"A", "B", "C", "D"}
        else "historical_workflow_R" for r in records
    )
    return {
        "sequence_exposures": len(records),
        "unique_targets": len({r["id"] for r in records}),
        "sequence_tokens_unpadded": sum(r["sequence_tokens"] for r in records),
        "positive_tokens": sum(r["positive_tokens"] for r in records),
        "shifted_valid_target_count": sum(r["shifted_valid_target_count"] for r in records),
        "weighted_mass": float(sum((mass(r["weighted_mass"]) for r in records), Decimal(0))),
        "le16k_exposures": sum(r["sequence_tokens"] <= 16384 for r in records),
        "long16to32k_exposures": sum(16384 < r["sequence_tokens"] <= 32768 for r in records),
        "over32k_exposures": sum(r["sequence_tokens"] > 32768 for r in records),
        "by_stage": dict(sorted(Counter(r["stage"] for r in records).items())),
        "by_workflow_stage": dict(sorted(workflow_stages.items())),
        "exposure_count_by_pool": dict(sorted(Counter(r["pool"] for r in records).items())),
    }


def collect(loader, root, base):
    records = {}
    for pool, source, entry, row in loader.iter_records(
        root, base, pools=("contract_optional", "real_process", "synthetic")
    ):
        feature = loader.binary(source, entry, row)
        ids = feature["input_ids"]
        labels = feature["labels"]
        weights = feature["loss_weights"]
        attention = feature["attention_mask"]
        require(len(ids) == len(labels) == len(weights) == len(attention), "FOUR_FEATURE_LENGTHS")
        require(ids and all(type(v) is int and v >= 0 for v in ids), "INVALID_INPUT_IDS")
        require(all(v == 1 for v in attention), "UNPADDED_ATTENTION_MASK")
        require(labels[0] == -100 and weights[0] == 0, "UNTRAINABLE_POSITION_ZERO_TARGET")
        pos_ids = []
        weight_total = Decimal(0)
        for token, label, weight in zip(ids, labels, weights):
            require(math.isfinite(weight) and weight >= 0, "INVALID_WEIGHT")
            if label == -100:
                require(weight == 0, "IGNORED_TARGET_HAS_WEIGHT")
            else:
                require(label == token and weight > 0, "LABEL_OR_WEIGHT_MISMATCH")
                pos_ids.append(label)
                weight_total += mass(weight)
        require(pos_ids, "NO_POSITIVE_LOSS_TARGET")
        component_tokens = Counter()
        component_weights = defaultdict(Decimal)
        for start, end, component, weight in row["supervision_spans"]:
            require(0 < start < end <= len(ids) and weight > 0, "INVALID_SUPERVISION_SPAN")
            component_tokens[component] += end - start
            component_weights[component] += mass(weight) * (end - start)
        require(sum(component_tokens.values()) == len(pos_ids), "SPAN_TARGET_COUNT_MISMATCH")
        encoded = array("I", pos_ids)
        require(encoded.itemsize == 4, "POSITIVE_IDS_NOT_UINT32")
        if sys.byteorder != "little":
            encoded.byteswap()
        record = {
            "id": row["id"],
            "pool": pool,
            "stage": row["stage"],
            "bank": row["bank"],
            "sequence_tokens": len(ids),
            "positive_tokens": len(pos_ids),
            "shifted_valid_target_count": sum(v != -100 for v in labels[1:]),
            "weighted_mass": float(weight_total),
            "positive_token_ids_sha256": hashlib.sha256(encoded.tobytes()).hexdigest(),
            "component_positive_tokens": dict(sorted(component_tokens.items())),
            "component_weighted_mass": {k: float(v) for k, v in sorted(component_weights.items())},
        }
        require(record["id"] not in records, "DUPLICATE_TRAINING_TARGET_ID")
        records[record["id"]] = record
    require(len(records) == 1250, "EXPECTED_1250_TARGETS")
    require(Counter(v["pool"] for v in records.values()) == {
        "contract_optional": 418, "real_process": 205, "synthetic": 627
    }, "POOL_COUNTS")
    return records


def phase(name, items, records, accumulation, offset):
    steps = []
    for index, items_in_step in enumerate(items):
        require(0 < len(items_in_step) <= accumulation, "ACCUMULATION_SIZE")
        microbatches = []
        for item in items_in_step:
            record = records[item["id"]]
            require(record["pool"] == item["pool"], "STEP_POOL_MISMATCH")
            microbatches.append({
                key: record[key] for key in (
                    "id", "pool", "sequence_tokens", "positive_tokens",
                    "shifted_valid_target_count", "weighted_mass"
                )
            })
        steps.append({
            "global_optimizer_step": offset + index + 1,
            "phase_optimizer_step": index + 1,
            "microbatches": microbatches,
            "sum_shifted_valid_target_denominator": sum(v["shifted_valid_target_count"] for v in microbatches),
            "weighted_positive_mass": float(sum((mass(v["weighted_mass"]) for v in microbatches), Decimal(0))),
            "sequence_tokens_unpadded": sum(v["sequence_tokens"] for v in microbatches),
        })
    flat = [records[item["id"]] for group in items for item in group]
    return {
        "name": name,
        "microbatch_size": 1,
        "gradient_accumulation_max": accumulation,
        "optimizer_steps": len(steps),
        "flush_last_partial_accumulation": True,
        "keep_same_adapter_and_optimizer_state": True,
        "stats": summary(flat),
        "steps": steps,
    }


def recipe(contract, process, records, process_name):
    first = phase("contract_alignment", contract, records, 16, 0)
    second = phase(process_name, process, records, 4, len(first["steps"]))
    ids = [v["id"] for p in (first, second) for s in p["steps"] for v in s["microbatches"]]
    stats = summary([records[v] for v in ids])
    stats["optimizer_steps"] = first["optimizer_steps"] + second["optimizer_steps"]
    stats["phase_optimizer_steps"] = [first["optimizer_steps"], second["optimizer_steps"]]
    stats["explicit_repeat_count"] = len(ids) - len(set(ids))
    stats["explicit_repeated_ids"] = sorted(v for v, n in Counter(ids).items() if n > 1)
    return {"phases": [first, second], "stats": stats}


def expected_artifacts(base, package11, loader_path):
    require(not sys.flags.optimize, "PYTHON_OPTIMIZATION_DISABLES_REVIEWED_LOADER_ASSERTIONS")
    require(sha(loader_path) == LOADER_SHA, "TRUSTED_LOADER_SHA_MISMATCH")
    require(sha(base / "TRAINING_MANIFEST.json") == PINS["base_main"], "BASE_MAIN_SHA")
    require(sha(base / "PAYLOAD_MANIFEST.json") == PINS["base_payload_manifest"], "BASE_PAYLOAD_SHA")
    require(sha(base / "canonical_arrays10/ARRAY_INDEX10.json") == PINS["base_array_index"], "BASE_INDEX_SHA")
    schedule_path = package11 / "work/exposure11_final/EXPOSURE_SCHEDULES11.json"
    control_path = package11 / "work/exposure11_final/FULL_REAL_EXPOSURE_CONTROL11.json"
    require(sha(schedule_path) == PINS["source_exposure_schedule"], "SOURCE_SCHEDULE_SHA")
    require(sha(control_path) == PINS["source_real_exposure_control"], "SOURCE_CONTROL_SHA")
    spec = importlib.util.spec_from_file_location("trusted_wrd_curriculum_loader11", loader_path)
    loader = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loader)
    source_schedule, source_control = load(schedule_path), load(control_path)
    all_records = {}
    for profile_name, dirname in PROFILE_DIRS.items():
        root = package11 / "work" / dirname
        require(sha(root / "CURRICULUM_MANIFEST11.json") == PINS[profile_name], "PROFILE_MANIFEST_SHA")
        all_records[profile_name] = collect(loader, root, base)
    budget = all_records["budget_projection"]
    full = all_records["full_native53"]
    require(set(budget) == set(full), "PROFILE_TARGET_ID_MISMATCH")
    for key in budget:
        left, right = budget[key], full[key]
        for field in ("pool", "stage", "bank", "positive_tokens", "shifted_valid_target_count",
                      "weighted_mass", "positive_token_ids_sha256", "component_positive_tokens",
                      "component_weighted_mass"):
            require(left[field] == right[field], "PROFILE_TARGET_PAYLOAD_MISMATCH:" + field)
    contract_ids = sorted(v["id"] for v in budget.values() if v["pool"] == "contract_optional")
    random.Random(SEED).shuffle(contract_ids)
    contract_items = [{"id": v, "pool": "contract_optional"} for v in contract_ids]
    contract_steps = [contract_items[i:i + 16] for i in range(0, len(contract_items), 16)]
    course = {
        "schema": "wrd55-full-pipeline-sft-planned-course-not-launcher-v1",
        "design_revision": "5.0.55",
        "change_id": "ALG-20261101-01",
        "data_contract_revisions_unchanged": {"primary": "5.0.52", "auxiliary": "5.0.54"},
        "contract_shuffle_seed": SEED,
        "frozen_inputs_sha256": dict(PINS, trusted_loader=LOADER_SHA),
        "loss": {
            "formula": "sum_over_accumulated_microbatches(weight_i * shifted_CE_i) / sum_over_accumulated_microbatches(shifted_label_i != -100)",
            "microbatch_means_must_not_be_averaged": True,
            "denominator_is_unweighted_valid_target_count": True,
            "frozen_per_token_weights_unchanged": True,
            "new627_weights": 0.05,
        },
        "training_started": False,
        "is_training_launcher": False,
        "profiles_are_mutually_exclusive": True,
        "profiles": {},
    }
    stats = {
        "schema": "wrd55-full-pipeline-course-counts-v1",
        "design_revision": "5.0.55",
        "unique_target_count": 1250,
        "unique_positive_tokens": 284595,
        "profiles": {},
        "no_new_source_or_target_added": True,
        "not_model_benchmark_or_runtime_measurement": True,
        "training_started": False,
    }
    for profile_name in PROFILE_DIRS:
        records = all_records[profile_name]
        process_steps = source_schedule["profiles"][profile_name]["full"]["steps"]
        require(process_steps == source_schedule["profiles"]["budget_projection"]["full"]["steps"],
                "CROSS_PROFILE_PROCESS_ORDER_MISMATCH")
        whole = recipe(contract_steps, process_steps, records, "full_process")
        control = recipe(contract_steps, source_control["steps"], records, "real_exposure_control")
        require(whole["stats"]["optimizer_steps"] == 236 and whole["stats"]["unique_targets"] == 1250
                and whole["stats"]["sequence_exposures"] == 1254, "FULL_COURSE_COUNTS")
        require(control["stats"]["optimizer_steps"] == 80 and control["stats"]["unique_targets"] == 623
                and control["stats"]["sequence_exposures"] == 627, "CONTROL_COURSE_COUNTS")
        course["profiles"][profile_name] = {
            "full_1250": whole,
            "same_real_exposure_control_623": control,
            "control_matches_real_exposure_not_compute": True,
        }
        all_summary = summary(list(records.values()))
        by_pool = {pool: summary([v for v in records.values() if v["pool"] == pool])
                   for pool in ("contract_optional", "real_process", "synthetic")}
        component_tokens = Counter()
        component_rows = Counter()
        for record in records.values():
            component_tokens.update(record["component_positive_tokens"])
            component_rows.update(record["component_positive_tokens"].keys())
        stats["profiles"][profile_name] = {
            "unique_all1250": all_summary,
            "unique_by_pool": by_pool,
            "unique_component_positive_tokens": dict(sorted(component_tokens.items())),
            "unique_component_rows_overlap_allowed": dict(sorted(component_rows.items())),
            "full_1250_course": copy.deepcopy(whole["stats"]),
            "control_623_course": copy.deepcopy(control["stats"]),
        }
    require(stats["profiles"]["budget_projection"]["unique_all1250"]["sequence_tokens_unpadded"] == 10207038,
            "UNIQUE_BUDGET_SEQUENCE_COUNT")
    require(stats["profiles"]["budget_projection"]["full_1250_course"]["sequence_tokens_unpadded"] == 10244527,
            "EXPOSED_BUDGET_SEQUENCE_COUNT")
    require(stats["profiles"]["full_native53"]["full_1250_course"]["sequence_tokens_unpadded"] == 20820961,
            "EXPOSED_FULL53_SEQUENCE_COUNT")
    return course, stats


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-root", required=True, type=Path)
    parser.add_argument("--package11-root", required=True, type=Path)
    parser.add_argument("--loader", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--build", action="store_true")
    args = parser.parse_args()
    course, stats = expected_artifacts(args.base_root.resolve(), args.package11_root.resolve(), args.loader.resolve())
    args.out.mkdir(parents=True, exist_ok=True)
    course_path, stats_path = args.out / "FULL_COURSE55.json", args.out / "STATS55.json"
    if args.build:
        write(course_path, course)
        write(stats_path, stats)
    require(load(course_path) == course, "COURSE_FILE_DIFFERS_FROM_REBUILT_PLANNED_COURSE")
    require(load(stats_path) == stats, "STATS_FILE_DIFFERS_FROM_ACTUAL_ARRAY_COUNTS")
    qa = {
        "schema": "wrd55-fresh-actual-array-and-full-course-verification-v1",
        "status": "PASS_ALL1250_BOTH_PROFILES_AND236_STEP_FULL_COURSE",
        "data_read": "actual binary arrays with trusted SHA-pinned stdlib loader",
        "unique_targets_per_profile": 1250,
        "physical_views_read_both_profiles": 2500,
        "positive_tokens_per_profile": 284595,
        "all_four_features_checked": True,
        "all_labels_weights_shifted_denominators_checked": True,
        "same_positive_payload_and_IDs_between_profiles": True,
        "source_schedule_and_control_sha_checked": True,
        "full_course_unique_targets": 1250,
        "full_course_sequence_exposures": 1254,
        "full_course_optimizer_steps_planned_not_executed": 236,
        "control_unique_targets": 623,
        "control_sequence_exposures": 627,
        "control_optimizer_steps_planned_not_executed": 80,
        "four_repeated_existing_process_targets_explicit": True,
        "source_or_eval_split_changed": False,
        "model_weights_loaded": False,
        "forward_or_backward_executed": False,
        "optimizer_steps_executed": 0,
        "training_started": False,
        "files": {p.name: {"sha256": sha(p), "bytes": p.stat().st_size}
                  for p in (course_path, stats_path, Path(__file__))},
        "verified_inputs_sha256": dict(PINS, trusted_loader=LOADER_SHA),
    }
    write(args.out / "COURSE_QA55.json", qa)
    print(json.dumps({"status": qa["status"], "course_sha256": sha(course_path),
                      "stats_sha256": sha(stats_path), "qa_sha256": sha(args.out / "COURSE_QA55.json"),
                      "verifier_sha256": sha(Path(__file__)), "profiles": {
                          name: {key: value[key] for key in ("unique_all1250", "full_1250_course", "control_623_course")}
                          for name, value in stats["profiles"].items()
                      }}, ensure_ascii=False))


if __name__ == "__main__":
    main()
