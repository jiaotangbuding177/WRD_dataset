"""Derive a uniform core-tool view of existing WRD examples, without new data.

The original dataset is read-only. This is the same set of examples with seven
fixed-image coding definitions present in every row; it is not a reconstruction
of all 53 tools or an original per-episode tool access policy.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import gzip
from hashlib import sha256
from itertools import zip_longest
import json
import os
from pathlib import Path
import time

from build import clean_value
from training import INCOMPLETE_MARKERS, _schema_map


CORE7 = ("ls", "read", "edit", "write", "apply_patch", "exec", "process")
SOURCE_DATASET = "datasets/native_actions.train.jsonl.gz"
DERIVED_DATASET = "datasets/native_actions_core7.train.jsonl.gz"


def file_sha(path):
    digest = sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def rows(path):
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        for number, line in enumerate(handle, 1):
            if line.strip():
                yield number, json.loads(line)


def required_tools(row):
    return {call.get("function", {}).get("name") for message in row.get("prompt", []) + row.get("completion", []) for call in message.get("tool_calls", [])}


def schema_names(row):
    return {tool.get("function", {}).get("name"): tool for tool in row.get("tools", []) if isinstance(tool, dict)}


def record_profile(path):
    kinds, routes_count, buckets = Counter(), Counter(), Counter()
    lengths = []
    boundaries = (8192, 32768, 65536, 131072, 262144)
    for _, row in rows(path):
        kinds[row.get("kind", "unknown")] += 1
        routes_count[row.get("route_id", "")] += 1
        value = {key: row.get(key) for key in ("prompt", "completion", "tools")}
        length = len(json.dumps(value, ensure_ascii=False, separators=(",", ":")))
        lengths.append(length)
        bucket = next((f"characters_le_{limit}" for limit in boundaries if length <= limit), "characters_gt_262144")
        buckets[bucket] += 1
    lengths.sort()
    return {
        "counts_by_kind": dict(kinds),
        "counts_by_route": dict(sorted(routes_count.items())),
        "serialized_prompt_completion_tools_characters": {
            "unit": "unicode_characters_of_serialized_prompt_completion_tools_not_tokens",
            "target_tokenizer": None, "target_chat_template": None,
            "rows": len(lengths), "min": lengths[0] if lengths else None,
            "median": lengths[len(lengths) // 2] if lengths else None,
            "p95": lengths[min(len(lengths) - 1, int(len(lengths) * .95))] if lengths else None,
            "p99": lengths[min(len(lengths) - 1, int(len(lengths) * .99))] if lengths else None,
            "max": lengths[-1] if lengths else None, "sum": sum(lengths),
            "mutually_exclusive_buckets": dict(buckets),
            "truncation_applied": False,
        },
    }


def uniform_tools(bundle):
    bundle = Path(bundle).resolve()
    source, output = bundle / SOURCE_DATASET, bundle / DERIVED_DATASET
    if source == output:
        raise ValueError("Derived output must differ from read-only source.")
    resource = Path(__file__).parent / "resources" / "native_coding_tools_97a0.json"
    core, resource_issues = _schema_map(resource)
    if set(core) != set(CORE7):
        raise ValueError("The frozen-image resource must contain exactly seven complete coding definitions.")
    started = time.monotonic()
    source_before = file_sha(source)
    temporary = output.with_name(output.name + ".tmp")
    counts, failures = Counter(), []
    extra_sets = Counter()
    with gzip.open(temporary, "wt", encoding="utf-8", newline="\n", compresslevel=3) as handle:
        for number, original in rows(source):
            existing = schema_names(original)
            merged = [existing.get(name, core[name]) for name in CORE7]
            extras = [tool for tool in original.get("tools", []) if tool.get("function", {}).get("name") not in CORE7]
            merged.extend(extras)
            extra_names = sorted(tool["function"]["name"] for tool in extras)
            extra_sets[",".join(extra_names) or "none"] += 1
            derived = {
                **original,
                "tools": merged,
                "tool_definition_scope": "uniform_fixed_image_core7_subset",
                "not_full_original53_access_policy": True,
                "source_dataset": SOURCE_DATASET,
                "derived_representation_of_same_samples": True,
                "independent_new_samples": False,
                "uniform_core_tool_names": list(CORE7),
                "uniform_core_schema_source": "existing_row_definition_preferred_then_frozen_native_image_97a0",
                "extra_tool_definitions_preserved_from_source": extra_names,
                "extra_definitions_can_still_depend_on_observed_prefix_or_target": bool(extra_names),
            }
            cleaned = clean_value(derived)
            for field in ("id", "prompt", "completion"):
                if cleaned.get(field) != original.get(field):
                    failures.append({"reason": "cleaning_would_change_source_value", "line": number, "field": field, "sample_id": original.get("id")})
            if failures:
                break
            serialized = json.dumps(cleaned, ensure_ascii=False, separators=(",", ":"))
            handle.write(serialized + "\n")
            counts["source_rows_transformed"] += 1
            counts["rows_with_non_core_tools"] += bool(extra_names)
            if number % 1000 == 0:
                print(f"uniform core7 transformed {number}; elapsed {time.monotonic() - started:.1f}s", flush=True)

    # Read the actual compressed file back and compare every data value that is
    # required to remain unchanged, rather than relying on in-memory equality.
    if not failures:
        for source_item, output_item in zip_longest(rows(source), rows(temporary)):
            if source_item is None or output_item is None:
                failures.append({"reason": "row_count_mismatch"})
                break
            number, original = source_item
            _, derived = output_item
            for field in ("id", "prompt", "completion"):
                if original.get(field) != derived.get(field):
                    failures.append({"reason": "source_value_changed", "line": number, "field": field, "sample_id": original.get("id")})
            definitions = schema_names(derived)
            if not set(CORE7).issubset(definitions):
                failures.append({"reason": "uniform_core7_definition_missing", "line": number})
            if not required_tools(derived).issubset(definitions):
                failures.append({"reason": "called_tool_definition_missing", "line": number})
            original_definitions = schema_names(original)
            for name, definition in original_definitions.items():
                if definitions.get(name) != definition:
                    failures.append({"reason": "existing_tool_definition_changed", "line": number, "tool_name": name})
            for name, definition in definitions.items():
                function = definition.get("function", {})
                if not isinstance(function.get("parameters"), dict) or any(marker in json.dumps(definition, ensure_ascii=False) for marker in INCOMPLETE_MARKERS):
                    failures.append({"reason": "incomplete_tool_schema", "line": number, "tool_name": name})
            if clean_value(derived) != derived:
                failures.append({"reason": "sanitization_not_idempotent", "line": number})
            if derived.get("source_dataset") != SOURCE_DATASET or derived.get("independent_new_samples") is not False:
                failures.append({"reason": "derived_representation_metadata_invalid", "line": number})
            counts["readback_exact_identity_prompt_completion_checked"] += 1
            counts["readback_all_called_tool_schemas_checked"] += 1
            if number % 2000 == 0:
                print(f"uniform core7 readback checked {number}; elapsed {time.monotonic() - started:.1f}s", flush=True)
            if len(failures) >= 100:
                break

    source_after = file_sha(source)
    if source_after != source_before:
        failures.append({"reason": "read_only_source_changed_during_derivation"})
    status = "FAIL" if failures else "PASS"
    output_sha = file_sha(temporary)
    if status == "PASS":
        os.replace(temporary, output)
    report = {
        "schema_version": "wrd-uniform-core7-tools-validation-v1",
        "validated_at": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "elapsed_seconds": round(time.monotonic() - started, 3),
        "source_dataset": SOURCE_DATASET,
        "derived_dataset": DERIVED_DATASET,
        "source_sha256_before": source_before,
        "source_sha256_after": source_after,
        "source_unchanged": source_before == source_after,
        "derived_sha256": output_sha,
        "counts": dict(counts),
        "uniform_core_tool_names": list(CORE7),
        "non_core_tool_sets_and_rows": dict(extra_sets),
        "core_resource_sha256": file_sha(resource),
        "resource_parse_issues": dict(resource_issues),
        "tool_definition_scope": "uniform_fixed_image_core7_subset",
        "not_full_original53_access_policy": True,
        "independent_new_samples": 0,
        "failures": failures,
        "limits": "Same examples and exact id/prompt/completion values. Seven coding definitions are uniformly available; extra non-core definitions, if any, remain as in the source and can depend on observed calls. This does not reconstruct all 53 original definitions, native access policy, or semantic gold approval.",
        "converter_sha256": file_sha(Path(__file__)),
    }
    if status == "PASS":
        report.update(record_profile(output))
    (bundle / "UNIFORM_TOOLS_VALIDATION.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": status, "counts": report["counts"], "source_unchanged": report["source_unchanged"], "derived_sha256": output_sha, "failure_count": len(failures), "elapsed_seconds": report["elapsed_seconds"]}, ensure_ascii=False), flush=True)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", type=Path)
    result = uniform_tools(parser.parse_args().bundle)
    raise SystemExit(0 if result["status"] == "PASS" else 1)
