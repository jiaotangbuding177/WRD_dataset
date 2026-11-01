"""Derive transparent stage-by-pool coverage from the frozen public course."""
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

DATA = Path(r"D:\skillloop\output\20261101_wrd_increment57\active_dataset57\native_bfc_checkpoint01")
SOURCE = DATA / "COURSE57_NATIVE.json"
assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == "06b15abbbbe4870db0240d06f2a47956248796465e534c9fbe4a4699136327ff"
course = json.loads(SOURCE.read_text(encoding="utf-8"))
counts = defaultdict(Counter)
tokens = defaultdict(Counter)
for phase in course["profiles"]["budget_projection"]["phases"]:
    for step in phase["steps"]:
        for row in step["microbatches"]:
            stage = row["stage"].split("_")[0]
            if stage == "historical":
                stage = "historical_workflow_R"
            counts[row["pool"]][stage] += 1
            tokens[row["pool"]][stage] += row["positive_tokens"]
real_counts = counts["real_process"] + counts["increment_process"]
real_tokens = tokens["real_process"] + tokens["increment_process"]
assert sum(real_counts.values()) == 232
assert sum(real_tokens.values()) == 169708
assert sum(sum(c.values()) for c in counts.values()) == 1260
result = {
    "schema": "wrd57-post-freeze-derived-stage-pool-coverage-v1",
    "source_course_sha256": hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
    "source_training_data_modified": False,
    "targets_by_pool_and_stage": dict(counts),
    "positive_tokens_by_pool_and_stage": dict(tokens),
    "real_process_combined_targets_by_stage": dict(real_counts),
    "real_process_combined_positive_tokens_by_stage": dict(real_tokens),
    "all_stage_counts_include_contract_and_explicit_synthetic_pools": True,
    "interpretation": "Observed process is strongest in B resource construction. A additionally has 401 source contracts; C/D have explicit low-weight auxiliary policy curriculum. Prioritize additional independent real evaluation, outcome-linked repair and finalization chains; do not describe all 1260 as independent full rollouts.",
    "new_training_targets_or_model_calls": 0,
    "training_started": False,
}
target = Path(__file__).with_name("POOL_STAGE_COVERAGE57.json")
target.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps(result, ensure_ascii=False))
