"""Read real restored58 features and independently apply each course alpha.

Only byte-pinned repository parser code is imported. Restored code is data,
never executed. This is CPU bookkeeping, not a model loss or training run.
"""
from pathlib import Path
from fractions import Fraction
from collections import Counter, defaultdict
from array import array
import argparse
import hashlib
import importlib.util
import json
import math
import sys

ROOT = Path(__file__).resolve().parents[3]
ACTIVE_SHA = "8b107ec2cb6ed1af29cbf4c25bd2158884097aab05cf0d8e31efbc944115c27a"
OLD_SHA = "a2d5f03fb9dec90763b238c5c499199176f1eddbf54b935475274981bc952c1c"
OBJECTIVE_SHA = "38e5ab2485cb69449d089052cc5599a88fe40c7bde9d995fa3448e8cf2c101f0"


def require(ok, reason):
    if not ok:
        raise ValueError(reason)


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1048576), b""):
            h.update(block)
    return h.hexdigest()


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def scale(value):
    result = Fraction(int(value["numerator"]), int(value["denominator"]))
    require(result > 0 and math.isfinite(value["float64"]) and abs(float(result) - value["float64"]) <= 1e-15, "SCALE_EXACT_RATIONAL_FLOAT_MISMATCH")
    return result


def positive_sha(values):
    packed = array("I", values)
    require(packed.itemsize == 4, "U32_PLATFORM_REQUIRED")
    if sys.byteorder != "little":
        packed.byteswap()
    return hashlib.sha256(packed.tobytes()).hexdigest()


def feature_digest(feature):
    h = hashlib.sha256()
    for name, dtype in (("input_ids", "I"), ("labels", "i"), ("loss_weights", "d"), ("attention_mask", "B")):
        data = array(dtype, feature[name])
        if sys.byteorder != "little" and data.itemsize > 1:
            data.byteswap()
        h.update(data.tobytes())
    return h.hexdigest()


def main():
    require(not sys.flags.optimize, "OPTIMIZED_PYTHON_REJECTED")
    p = argparse.ArgumentParser()
    p.add_argument("--restored-root", type=Path, required=True)
    p.add_argument("--active-relative", default="active58")
    p.add_argument("--base-root", type=Path, required=True)
    p.add_argument("--package11-root", type=Path, required=True)
    p.add_argument("--trusted-active-loader", type=Path)
    p.add_argument("--trusted-immutable-loader", type=Path)
    p.add_argument("--trusted-objective-adapter", type=Path)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    require(not a.out.exists(), "PRESERVE_PREVIOUS_VERIFICATION")
    root = a.restored_root.resolve()
    active = (root / a.active_relative).resolve()
    require(active.is_relative_to(root), "ACTIVE_ROOT_ESCAPES_RESTORE")
    receipt = load(root / "RESTORE_RECEIPT57.json")
    require(receipt["status"] == "PASS_REAL_AUTHENTICATED_ARCHIVE_RESTORE_EVERY_EXPLICIT_FILE_SHA", "REAL_AUTHENTICATED_RESTORE_REQUIRED")
    entry = load(active / "TRAINING_ENTRYPOINT58.json")
    for name in ("dataset_manifest", "compatibility_manifest", "dataset_pin", "compatibility_pin", "loader", "immutable_loader", "course", "config", "course_QA"):
        ref = entry[name]
        file = (active / ref["path"]).resolve()
        require(file.is_relative_to(active) and file.stat().st_size == ref["bytes"] and sha(file) == ref["sha256"], "RESTORED_ENTRYPOINT_PIN_MISMATCH")
    local = a.trusted_active_loader or ROOT / "research/data_prep/wrd_increment57/active_loader57.py"
    old = a.trusted_immutable_loader or ROOT / "research/data_prep/wrd_curation11/curriculum_loader11.py"
    if not local.is_file() and a.trusted_active_loader is None:
        local = Path(__file__).with_name("active_loader57.py")
    if not old.is_file() and a.trusted_immutable_loader is None:
        old = Path(__file__).with_name("immutable_curriculum_loader11.py")
    require(not local.resolve().is_relative_to(root) and not old.resolve().is_relative_to(root), "RESTORED_PARSER_MUST_NOT_BE_EXECUTED")
    require(sha(local) == ACTIVE_SHA and sha(old) == OLD_SHA, "TRUSTED_LOCAL_PARSER_PIN")
    spec = importlib.util.spec_from_file_location("reviewed_local_active58_feature_reader", local)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    objective_path = a.trusted_objective_adapter or ROOT / "output/20261101_wrd_final_audit58/objective_adapter58/objective_adapter58.py"
    if not objective_path.is_file() and a.trusted_objective_adapter is None:
        objective_path = Path(__file__).with_name("objective_adapter58.py")
    require(not objective_path.resolve().is_relative_to(root) and sha(objective_path) == OBJECTIVE_SHA, "TRUSTED_OBJECTIVE_ADAPTER_PIN_OR_LOCATION")
    objective_spec = importlib.util.spec_from_file_location("reviewed_local_objective_adapter58", objective_path)
    objective = importlib.util.module_from_spec(objective_spec)
    objective_spec.loader.exec_module(objective)
    manifest = load(active / "ACTIVE_DATASET_MANIFEST58.json")
    course = load(active / entry["course"]["path"])
    require(manifest["actual_counts"]["budget_projection"]["unique_targets"] == 1260 and entry["positive_tokens"] == 295478, "FROZEN58_EXPECTED_TARGETS")
    summaries, payloads = {}, {}
    for profile, plan in course["profiles"].items():
        lookup, steps = {}, {}
        for phase in plan["phases"]:
            for step in phase["steps"]:
                sid = step["global_step_one_based"]
                require(sid not in steps, "DUPLICATE_COURSE_STEP")
                steps[sid] = {"phase": phase["name"], "expected": step, "real": Fraction(0), "aux": Fraction(0), "base": Fraction(0), "denominator": 0, "seen": 0}
                for micro in step["microbatches"]:
                    require(micro["id"] not in lookup, "REPEATED_TARGET_IN_COURSE")
                    alpha = scale(micro["extra_course_loss_scale"])
                    require((0 < alpha <= 1) if micro["pool"] == "synthetic" else alpha == 1, "INVALID_POOL_SCALE")
                    lookup[micro["id"]] = (sid, alpha, micro)
        require(len(lookup) == 1260 and len(steps) == 241, "ONEPASS_COURSE_SIZE")
        actual, ids, base_mass = Counter(), {}, Fraction(0)
        loaded_cache, feature_before = {}, {}
        for value in module.iter_features(active, a.base_root, a.package11_root, profile=profile, immutable_loader_path=old, with_metadata=True):
            rid, feature = value["id"], value["features"]
            require(rid in lookup and rid not in ids, "FEATURE_ID_NOT_UNIQUE_COURSE_MEMBER")
            sid, alpha, micro = lookup[rid]
            require(value["pool"] == micro["pool"], "FEATURE_POOL_COURSE_MISMATCH")
            positive = [token for token in feature["labels"] if token != -100]
            phash = positive_sha(positive)
            require(phash == micro["positive_token_ids_sha256_u32le"], "ACTUAL_POSITIVE_TOKEN_PAYLOAD_DIFFERS_FROM_COURSE")
            n = len(positive)
            require(n == micro["positive_tokens"] == micro["valid_shifted_target_count"], "ACTUAL_MASK_COUNT_DIFFERS_FROM_COURSE")
            mass = sum((Fraction(str(w)) for token, w in zip(feature["labels"], feature["loss_weights"]) if token != -100), Fraction(0))
            require(mass == Fraction(micro["weighted_mass"]), "ACTUAL_BASE_WEIGHTS_DIFFER_FROM_COURSE")
            ids[rid] = phash
            loaded_cache[rid] = value
            feature_before[rid] = feature_digest(feature)
            actual["unique_targets"] += 1
            actual["positive_tokens"] += n
            actual["sequence_tokens"] += len(feature["input_ids"])
            actual["le16k_targets" if len(feature["input_ids"]) <= 16384 else "long16to32k_targets"] += 1
            require(len(feature["input_ids"]) <= 32768, "OVER_COMMON32K")
            base_mass += mass
            step = steps[sid]
            step["seen"] += 1
            step["base"] += mass
            step["denominator"] += n
            step["aux" if value["pool"] == "synthetic" else "real"] += mass * alpha
        require(set(ids) == set(lookup), "UNREAD_COURSE_TARGETS")
        effective, aux, maximum, process = Fraction(0), Fraction(0), Fraction(0), 0
        objective_steps, scaled_steps = 0, 0
        for step in steps.values():
            expected = step["expected"]
            require(step["seen"] == len(expected["microbatches"]) and step["denominator"] == expected["valid_shifted_target_denominator"], "STEP_ACTUAL_DENOMINATOR_MISMATCH")
            require(step["base"] == Fraction(expected["original_array_weighted_mass"]), "STEP_BASE_MASS_MISMATCH")
            total = step["real"] + step["aux"]
            require(abs(total - Fraction(expected["effective_weighted_mass"])) < Fraction(1, 10**20), "STEP_EFFECTIVE_MASS_MISMATCH")
            fraction = step["aux"] / total
            if step["phase"] == "process":
                process += 1
                require(step["real"] > 0 and fraction <= Fraction(1, 5), "PROCESS_STEP_STATIC_AUX_MASS_OVER20_PERCENT")
                maximum = max(maximum, fraction)
            effective += total
            aux += step["aux"]
            ordered = [loaded_cache[micro["id"]] for micro in expected["microbatches"]]
            prepared = objective.prepare_optimizer_step(expected, ordered)
            require(prepared["denominator"] == step["denominator"] and prepared["extra_accumulation_divisor"] == 1 and not prepared["weights_sum_normalization"], "EXECUTABLE_OBJECTIVE_DENOMINATOR_OR_EXTRA_DIVISION")
            vectors, oracle_parts = {}, []
            for loaded, micro in zip(ordered, expected["microbatches"]):
                f = loaded["features"]
                vector = [0.0] * len(f["labels"])
                alpha = scale(micro["extra_course_loss_scale"])
                terms = []
                for pos, (label, w) in enumerate(zip(f["labels"], f["loss_weights"])):
                    if label != -100:
                        ce = 0.1 + (int(f["input_ids"][pos]) % 97 + 3 * (pos % 11) + 7 * (expected["global_step_one_based"] % 19)) / 128
                        vector[pos] = ce
                        terms.append(float(Fraction(str(w)) * alpha) * ce)
                vectors[loaded["id"]] = vector
                oracle_parts.append(math.fsum(terms))
            oracle = math.fsum(oracle_parts) / step["denominator"]
            actual_cpu_reference = objective.reference_step_loss(prepared, vectors)
            require(math.isclose(actual_cpu_reference, oracle, rel_tol=1e-12, abs_tol=1e-12), "FRESH_EXECUTABLE_OBJECTIVE_VARIABLE_CE_ORACLE")
            objective_steps += 1
            scaled_steps += int(scale(expected["auxiliary_extra_loss_scale"]) < 1)
            for loaded in ordered:
                require(feature_digest(loaded["features"]) == feature_before[loaded["id"]], "BASE_FEATURES_MUTATED_BY_OBJECTIVE")
        expected = manifest["actual_counts"][profile]
        for name in ("unique_targets", "positive_tokens", "sequence_tokens", "le16k_targets", "long16to32k_targets"):
            require(actual[name] == expected[name], "ACTUAL_RESTORED_FEATURE_COUNTS_MISMATCH")
        require(base_mass == Fraction("85003.30") and process == 215, "BASE_MASS_OR_PROCESS_STEPS")
        require(effective == Fraction("84227.1375") and aux == Fraction("2091.9375"), "EXPECTED_COURSE_EFFECTIVE_MASS")
        require(objective_steps == 241 and scaled_steps == 92, "EXECUTABLE_OBJECTIVE_STEP_COVERAGE")
        summaries[profile] = {**dict(actual), "raw_array_weighted_mass": str(float(base_mass)), "course_effective_weighted_mass": str(float(effective)),
                              "course_effective_auxiliary_mass": str(float(aux)), "max_process_step_static_aux_fraction": float(maximum),
                              "all215_process_steps_with_real_anchor_and_at_most20percent_static_aux_mass": True,
                              "fresh_executable_objective_steps_variable_CE_verified": objective_steps,
                              "scaled_objective_steps": scaled_steps, "all_base_four_features_unchanged_after_objective": True}
        payloads[profile] = ids
        del loaded_cache
    require(payloads["budget_projection"] == payloads["full_native53"], "CROSS_PROFILE_POSITIVE_PAYLOADS_DIFFER")
    result = {"status": "PASS_FRESH58_RESTORE_ALL1260_BOTH_PROFILES_FOUR_FEATURES_AND_ACTUAL_COURSE_ALPHA",
              "authenticated_manifest_sha256": receipt["manifest_sha256"], "archive_files_verified": receipt["files_verified"],
              "active_manifest_sha256": sha(active / "ACTIVE_DATASET_MANIFEST58.json"), "entrypoint_sha256": sha(active / "TRAINING_ENTRYPOINT58.json"),
              "course_sha256": sha(active / "COURSE58.json"), "profiles": summaries,
              "same_positive_IDs_and_tokens_both_profiles": True, "restored_payload_code_executed": False,
              "only_reviewed_repository_local_parser_imported": True, "static_coefficient_mass_cap_not_CE_gradient_or_Adam_cap": True,
              "trusted_active_loader_sha256": ACTIVE_SHA, "trusted_immutable_loader_sha256": OLD_SHA,
              "trusted_executable_objective_adapter_sha256": OBJECTIVE_SHA,
              "source_code_sha256": sha(__file__), "weights_loaded": False, "training_started": False}
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "profiles": summaries, "QA_sha256": sha(a.out)}))


if __name__ == "__main__":
    main()
