"""Independent CPU-only verification of the frozen input-only evaluation arrays.

Uses official AutoTokenizer.apply_chat_template directly. Does not import the
compiler, its renderer, its causal-template functions, or any business program.
Writes only beside this script. Never loads weights, infers, or trains.
"""
import os

os.environ.update(
    USE_TORCH="0", USE_TF="0", CUDA_VISIBLE_DEVICES="-1",
    HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1",
    HF_HUB_DISABLE_TELEMETRY="1", TOKENIZERS_PARALLELISM="false",
)
import collections
import copy
import gzip
import hashlib
import importlib.util
import json
import platform
from pathlib import Path
import struct
import sys
import time

sys.dont_write_bytecode = True
ROOT = Path("D:/skillloop")
OUT = Path(__file__).resolve().parent
ARRAYS = ROOT / "output/20261031_wrd_curation09/eval_input_arrays09"
HOLD = ROOT / "output/20261031_wrd_curation09/holdout"
ASSETS = ROOT / "output/20261025_wrd_training_preflight/tokenizer_assets"
TRAIN = ROOT / "output/20261031_wrd_curation09/compiled_staging01/compiled01"
CAPTURE = ROOT / "output/20261027_wrd_main_v10/historical_v6_native_repair_01/TOOLS_CAPTURE_53.json"
EXPECTED = {
    "index": "1d8b8c36b300e906f458a37fcbac3d1800a42f5f7dc7a2e81244efc612983779",
    "array_manifest": "31bfb8d20d613d2fa5861a89ff519e57ae60597d70f05aed9f61db61d4e87b54",
    "hold_manifest": "b931d3c4df580b31f559b1c25aa971c781b3aa85675c2f32f06405a13d68bc0a",
    "capture": "a47db18b7c6bafcfddfe4bce79ae68787303320225a1edf99457720ee1622345",
    "causal_template": "5b5e083127485923d9d66e3262ccfb08ceb51afec37b8c4abfafa30cb18a17b4",
    "official_template": "a55ee1b1660128b7098723e0abcd92caa0788061051c62d51cbe87d9cf1974d8",
}
FEATURES = {"input_ids": ("i", 4), "labels": ("i", 4),
            "loss_weights": ("f", 4), "attention_mask": ("B", 1)}
MODELS = {
    "primary_14b": {"repository": "Qwen/Qwen3-14B", "revision": "40c069824f4251a91eefaf281ebe4c544efd3e18"},
    "control_8b": {"repository": "Qwen/Qwen3-8B", "revision": "b968826d9c46dd6066d109eabc6255188de91218"},
}


def digest(data):
    return hashlib.sha256(data if isinstance(data, bytes) else data.encode()).hexdigest()


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def pin(path):
    return {"path": str(path.relative_to(ROOT)).replace("\\", "/"),
            "bytes": path.stat().st_size, "sha256": digest(path.read_bytes())}


def verify_pin(path, descriptor):
    data = path.read_bytes()
    assert len(data) == descriptor["bytes"] and digest(data) == descriptor["sha256"], str(path)
    return data


def verify_tree(root, expected_sha):
    path = root / "MANIFEST.json"
    assert digest(path.read_bytes()) == expected_sha
    manifest = read(path)
    named = {f["path"] for f in manifest["files"]}
    actual = {str(p.relative_to(root)).replace("\\", "/") for p in root.rglob("*") if p.is_file()}
    assert actual == named | {"MANIFEST.json"}, (actual - named, named - actual)
    assert len(named) == len(manifest["files"]) == manifest["file_count"]
    total = 0
    for descriptor in manifest["files"]:
        p = (root / descriptor["path"]).resolve()
        assert p.is_relative_to(root.resolve())
        total += len(verify_pin(p, descriptor))
    assert total == manifest["bytes"]
    return {"manifest_pin": pin(path), "file_count_excluding_manifest": len(named), "entity_bytes_excluding_manifest": total}


def validate_independent(features):
    if set(features) != set(FEATURES):
        raise ValueError("FEATURE_SET")
    n = len(features["input_ids"])
    if n == 0 or any(len(v) != n for v in features.values()):
        raise ValueError("FEATURE_LENGTH")
    if any(v != -100 for v in features["labels"]):
        raise ValueError("EVAL_LABEL_MUST_IGNORE")
    if any(v != 0.0 for v in features["loss_weights"]):
        raise ValueError("EVAL_WEIGHT_MUST_ZERO")
    if any(v != 1 for v in features["attention_mask"]):
        raise ValueError("EVAL_ATTENTION_MUST_ONE")


def main():
    started = time.monotonic()
    trees_before = {
        "holdout": verify_tree(HOLD, EXPECTED["hold_manifest"]),
        "eval_arrays": verify_tree(ARRAYS, EXPECTED["array_manifest"]),
    }
    assert trees_before["holdout"]["file_count_excluding_manifest"] == 783
    assert trees_before["holdout"]["entity_bytes_excluding_manifest"] == 104596453
    assert digest((ARRAYS / "INDEX.json").read_bytes()) == EXPECTED["index"]
    index = read(ARRAYS / "INDEX.json")
    assert index["sequence_profile_instances"] == 104 and index["actual_feature_entities"] == 416
    assert index["no_padding_or_truncation"] is True and index["add_special_tokens"] is False
    assert index["add_generation_prompt"] is True and index["enable_thinking"] is True
    assert index["not_a_training_manifest"] is True
    entrypoint = read(HOLD / "INPUT_ONLY_EVAL_ENTRYPOINT05.json")
    verify_pin(ROOT / index["source_entrypoint"]["path"], index["source_entrypoint"])
    verify_pin(ROOT / index["source_holdout_manifest"]["path"], index["source_holdout_manifest"])
    entries = {e["task_id"]: e for e in entrypoint["entries"]}
    assert len(entries) == 26
    assert digest(CAPTURE.read_bytes()) == EXPECTED["capture"]
    full = read(CAPTURE)["tools"]
    names = [t["function"]["name"] for t in full]
    assert len(full) == len(set(names)) == 53
    core_names = ["apply_patch", "edit", "exec", "ls", "process", "read", "write"]
    by_name = {t["function"]["name"]: t for t in full}
    tools = {"core7": [by_name[n] for n in core_names], "full53": full}
    assert read(ARRAYS / "tool_profiles/core7.json")["tools"] == tools["core7"]
    assert (ARRAYS / "tool_profiles/full53_CAPTURE.original.json").read_bytes() == CAPTURE.read_bytes()
    train_proof = read(TRAIN / "COMPILATION_REPORT.json")["tokenizer_proof"]
    asset_pins = {}
    for name in MODELS:
        asset_pins[name] = {filename: digest((ASSETS / name / filename).read_bytes())
                            for filename in train_proof["asset_sha256"][name]}
        assert asset_pins[name] == train_proof["asset_sha256"][name] == index["tokenizer_asset_sha256"][name]
    assert asset_pins["primary_14b"] == asset_pins["control_8b"]
    assert digest((ARRAYS / "CAUSAL_TEMPLATE.jinja").read_bytes()) == EXPECTED["causal_template"]
    assert digest(read(TRAIN / "CAUSAL_TEMPLATE.json")["variant"]) == EXPECTED["causal_template"]
    # Causal template is only byte-audited. Rendering below uses the official API,
    # not the producer's Jinja renderer or the causal-variant implementation.
    import transformers
    import tokenizers
    from transformers import AutoTokenizer
    tokenizers_actual = {name: AutoTokenizer.from_pretrained(ASSETS / name,
                         local_files_only=True, trust_remote_code=False) for name in MODELS}
    assert all(digest(t.chat_template) == EXPECTED["official_template"] for t in tokenizers_actual.values())
    assert digest((ARRAYS / "OFFICIAL_TEMPLATE.jinja").read_bytes()) == EXPECTED["official_template"]
    spec = importlib.util.spec_from_file_location("independent_eval_published_loader", ARRAYS / "binary_loader.py")
    published_loader = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(published_loader)
    reference = {}
    with gzip.open(ARRAYS / "tokenized_inputs.standard.jsonl.gz", "rt", encoding="utf-8") as stream:
        for line in stream:
            r = json.loads(line)
            k = (r["profile_id"], r["task_id"])
            assert k not in reference
            reference[k] = r
    assert len(reference) == 104
    call_counts = collections.Counter()
    render_counts = collections.Counter()
    rows = []
    profiles = {}
    paired = {}
    entities = set()
    first_features = None
    for profile in index["profiles"]:
        pid, name, tool_name = profile["profile_id"], profile["tokenizer"], profile["tool_profile"]
        tokenizer = tokenizers_actual[name]
        assert profile["model"] == MODELS[name]
        assert len(profile["records"]) == 26 and {r["task_id"] for r in profile["records"]} == set(entries)
        lengths = []
        for row in profile["records"]:
            task_id = row["task_id"]
            entry = entries[task_id]
            packet_path = HOLD / entry["input_packet"]["path"]
            packet = json.loads(verify_pin(packet_path, entry["input_packet"]).decode("utf-8-sig"))
            messages = packet["messages"]
            assert all(m["role"] == "user" for m in messages)
            assert digest(json.dumps(messages, ensure_ascii=False, separators=(",", ":"), sort_keys=True)) == entry["messages_canonical_sha256_sorted_utf8"]
            assert row["material_mount_manifest"] == packet["input_files"]
            for material in packet["input_files"]:
                verify_pin(packet_path.parent / material["relative_path"], material)
            official = tokenizer.apply_chat_template(messages, tools=tools[tool_name], documents=None,
                tokenize=False, add_generation_prompt=True, enable_thinking=True)
            render_counts[name] += 1
            ids = tokenizer.apply_chat_template(messages, tools=tools[tool_name], documents=None,
                tokenize=True, add_generation_prompt=True, enable_thinking=True, return_dict=False,
                return_tensors=None, truncation=False, padding=False)
            call_counts[name] += 1
            assert isinstance(ids, list) and ids and all(isinstance(x, int) for x in ids)
            assert official.endswith("<|im_start|>assistant\n")
            prompt = verify_pin(ARRAYS / row["rendered_prompt"]["path"], row["rendered_prompt"])
            assert prompt == official.encode("utf-8")
            n = len(ids)
            assert n == row["tokens"]
            expected = {"input_ids": ids, "labels": [-100] * n,
                        "loss_weights": [0.0] * n, "attention_mask": [1] * n}
            actual = {}
            for field, (code, size) in FEATURES.items():
                descriptor = row["features"][field]
                assert descriptor["typecode"] == code and descriptor["byte_order"] == "little"
                path = (ARRAYS / descriptor["path"]).resolve()
                assert path.is_relative_to(ARRAYS.resolve())
                binary = verify_pin(path, descriptor)
                assert len(binary) == n * size
                actual[field] = list(struct.unpack("<" + str(n) + code, binary))
                assert actual[field] == expected[field] == reference[(pid, task_id)][field]
                assert descriptor["path"] not in entities
                entities.add(descriptor["path"])
            validate_independent(actual)
            assert published_loader.load_record(ARRAYS, pid, task_id) == actual
            if first_features is None:
                first_features = copy.deepcopy(actual)
            pair = (tool_name, task_id)
            if name == "primary_14b":
                paired[pair] = (official, ids)
            else:
                assert paired[pair] == (official, ids)
            assert row["supervised_tokens"] == 0 and row["positive_loss_weights"] == 0
            assert row["headroom_if_context16k"] == max(0, 16384 - n)
            assert row["headroom_if_context32k"] == max(0, 32768 - n)
            lengths.append(n)
            rows.append({"profile_id": pid, "task_id": task_id, "split": row["split"],
                         "tokens": n, "official_prompt_sha256": digest(official),
                         "input_ids_i32le_SHA256": row["features"]["input_ids"]["sha256"],
                         "four_features_all_values_equal_independent_standard_binary_and_published_loader": True,
                         "labels_positive_count": 0, "nonzero_weights": 0,
                         "headroom32k": 32768 - n})
        totals = {"records": len(lengths), "input_tokens": sum(lengths),
                  "le16k": sum(n <= 16384 for n in lengths),
                  "le32k": sum(n <= 32768 for n in lengths),
                  "over32k": sum(n > 32768 for n in lengths)}
        assert totals == profile["counts"]
        assert min(lengths) == profile["minimum_tokens"] and max(lengths) == profile["maximum_tokens"]
        profiles[pid] = {**totals, "min": min(lengths), "max": max(lengths),
                         "minimum_headroom32k": 32768 - max(lengths)}
    assert len(rows) == 104 and len(entities) == 416
    assert dict(call_counts) == {"primary_14b": 52, "control_8b": 52}
    assert dict(render_counts) == {"primary_14b": 52, "control_8b": 52}
    canaries = {}
    for field, value in [("labels", first_features["input_ids"][0]), ("loss_weights", 1.0)]:
        malformed = copy.deepcopy(first_features)
        malformed[field][0] = value
        rejected = {}
        for validator_name, validator in [("independent", validate_independent),
                                          ("published_stdlib_loader", published_loader.validate_features)]:
            try:
                validator(malformed)
            except (ValueError, AssertionError) as exc:
                rejected[validator_name] = str(exc)
            else:
                raise AssertionError("POSITIVE_CANARY_ACCEPTED:" + field)
        canaries[field] = {"both_rejected": True, "reasons": rejected,
                           "sealed_files_mutated": False, "test_scope": "in-memory semantic guard mutation"}
    trees_after = {
        "holdout": verify_tree(HOLD, EXPECTED["hold_manifest"]),
        "eval_arrays": verify_tree(ARRAYS, EXPECTED["array_manifest"]),
    }
    assert trees_before == trees_after
    qa = {
        "schema": "wrd09-independent-eval-input-array-QA-v1",
        "status": "PASS_104_OFFICIAL_TEMPLATE_REENCODINGS_416_BINARY_FEATURES_INPUT_ONLY",
        "authorship": "Independent current_source_registry reviewer; official apply_chat_template called directly. Compiler and compiler render logic not imported/executed.",
        "script_pin": pin(Path(__file__).resolve()),
        "index_pin": pin(ARRAYS / "INDEX.json"),
        "entrypoint_pin": pin(HOLD / "INPUT_ONLY_EVAL_ENTRYPOINT05.json"),
        "frozen_trees_verified_before_and_after": trees_before,
        "counts": {"tasks": 26, "profile_instances": len(rows), "binary_feature_entities": len(entities),
                   "independent_tokenize_calls": dict(call_counts), "official_render_calls": dict(render_counts),
                   "total_profile_instance_input_tokens": sum(r["tokens"] for r in rows),
                   "positive_labels": 0, "nonzero_loss_weights": 0,
                   "standard_reference_rows_compared": len(reference)},
        "profile_counts": profiles,
        "negative_canaries": canaries,
        "record_checks": rows,
        "tokenizer_assets_rehashed_and_equal_pinned_training32": asset_pins,
        "official_template_SHA256": EXPECTED["official_template"],
        "causal_template_byte_pin_verified_only": EXPECTED["causal_template"],
        "tool_capture_pin": pin(CAPTURE),
        "tools_reconstructed_independently_from_original_capture": {"core7": core_names, "full53_count": 53},
        "runtime_versions": {"python": platform.python_version(), "transformers": transformers.__version__,
                             "tokenizers": tokenizers.__version__},
        "torch_module_loaded": "torch" in sys.modules,
        "no_original_system_capture_or_OpenClaw_equivalence_claimed": True,
        "limits": [
            "All104 rows are input-only views of26 tasks, not104 independent tasks or positive SFT examples.",
            "Every label is-100 and loss weight0; these arrays must never be added as positive TRAIN data.",
            "Official/causal render equivalence is established for this pure-user generation-prefix batch only; no assistant reasoning/tool-turn equivalence is newly inferred.",
            "HF default tool/system wrapper is a declared offline profile, not recovered original native OpenClaw system.",
            "core7 inputs all fit16K; full53 inputs fit32K but not16K, with minimum3192 tokens remaining before generated reasoning, tool calls, observations and answer. Output budget/runtime feasibility remains unvalidated.",
            "Binary material contents are mounted resources, not all represented as prompt tokens; future reading/OCR adds context and may consume further budget.",
            "No model weights, inference, training, native tool dispatch or benchmark outcome/quality score were produced. CPU tokenization and AI curation costs are not business rollout costs.",
        ],
        "model_weights_loaded": False, "model_inference_started": False, "training_started": False,
        "sealed_input_trees_modified": False,
        "elapsed_seconds": round(time.monotonic() - started, 3),
    }
    path = OUT / "EVAL_INPUT_ARRAYS_INDEPENDENT_QA.json"
    path.write_text(json.dumps(qa, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": qa["status"], "QA": pin(path), "profiles": profiles,
                      "counts": qa["counts"], "elapsed_seconds": qa["elapsed_seconds"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
