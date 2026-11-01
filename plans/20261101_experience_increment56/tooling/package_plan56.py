"""Package planning documents only; no data collection, model or training."""
from pathlib import Path
import hashlib
import json
import shutil

BASE = Path(__file__).resolve().parents[3]
REPO = BASE / "output/20261025_wrd_training_dataset/git_release"
SOURCE = BASE / "research/plans/20261101_wrd_experience_increment56"
WORK = BASE / "output/20261101_wrd_increment_plan56"
DEST = REPO / "plans/20261101_experience_increment56"

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

def copy(src, dst):
    if not src.is_file() or src.is_symlink():
        raise ValueError("Expected reviewed regular source")
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, dst)
    if sha(src) != sha(dst):
        raise ValueError("Copy mismatch")

status = json.loads((SOURCE / "PLAN_STATUS.json").read_text(encoding="utf-8-sig"))
checks = {"plan_only": status["plan_only"], "not_launch_config": not status["is_launch_config"],
          "no_new_targets": status["new_admitted_targets"] == 0,
          "data1250_unchanged": status["current_active_data_targets"] == 1250,
          "course55_236_unchanged": status["current_active_course_updates_candidate"] == 236,
          "full_train_groups267": status["current_train_joined_source_groups"] == 267,
          "original226_isolated": status["original226_and_all_existing_reserved_groups_isolated"],
          "no_training": not status["training_started"],
          "no_business_execution": not status["new_business_execution_authorized_this_turn"]}
b = status["budget_plan"]
checks["each_group13_sessions"] = b["each_group"]["native_sessions_total"] == 1 + 4 + 6 + 2 == 13
checks["each_group104_requests"] = b["each_group"]["model_requests_total"] == 48 + 6 * 8 + 2 * 4 == 104
for count, key in ((2,"cumulative2_including_preflight"),(6,"cumulative6_including_pilot_and_preflight"),(12,"cumulative12_later_proposal")):
    row = b[key]
    for field, per, initial in (("native_sessions",13,2),("model_requests",104,8),("actual_IO_tokens",4000000,1000000),("budget_hours",8,2)):
        checks[f"budget_{count}_{field}"] = row[field] == count * per + initial
for name in ("A_B_MODULES.md", "PIPELINE.md"):
    content = (BASE / "research/designs" / name).read_text(encoding="utf-8-sig")
    checks[f"design56_{name}"] = "设计版本：5.0.56" in content and "变更编号：ALG-20261101-02" in content and "接口版本：workflow-pipeline-v1" in content
if not all(checks.values()):
    raise ValueError("Plan checks failed: " + str([k for k,v in checks.items() if not v]))
for name in ("PLAN.md", "PLAN_STATUS.json"):
    copy(SOURCE / name, DEST / name)
for name in ("INVENTORY_REVIEW.md", "DESIGN_REVIEW.md", "FINAL_PLAN_QA56.json"):
    copy(WORK / name, DEST / "reviews" / name)
for name in ("A_B_MODULES.md", "PIPELINE.md"):
    copy(BASE / "research/designs" / name, DEST / "designs" / name)
    copy(BASE / "research/designs/history/5.0.55/increment_plan56_20261101" / name,
         DEST / "designs/history/5.0.55" / name)
copy(Path(__file__), DEST / "tooling/package_plan56.py")
write(DEST / "PLANNING_DELIVERY_QA56.json", {"schema": "wrd56-planning-document-qa-not-data-admission",
      "status": "PASS_PLAN_BUDGETS_AND_SCOPE", "checks": checks,
      "checks_count": len(checks), "source_script_sha256": sha(Path(__file__)),
      "new_data_targets": 0, "business_calls": 0, "weights_or_training": 0})
entry_path = REPO / "TRAINING_ENTRYPOINT.json"
entry = json.loads(entry_path.read_text(encoding="utf-8-sig"))
if entry["current_plan"] != "plans/20261101_full_pipeline_sft/PLAN.md":
    raise ValueError("Unexpected current course")
entry.update({"next_data_increment_plan": "plans/20261101_experience_increment56/PLAN.md",
              "next_data_increment_plan_revision": "5.0.56", "next_data_increment_plan_only": True,
              "next_data_increment_new_admitted_targets": 0})
write(entry_path, entry)
prefix = """## 下一轮独立经验与真实修订链增量计划56（2026-11-01，尚未执行）

[详细增量计划](plans/20261101_experience_increment56/PLAN.md) · [范围与预算](plans/20261101_experience_increment56/PLAN_STATUS.json) · [独立复核](plans/20261101_experience_increment56/reviews/FINAL_PLAN_QA56.json)

先按全部TRAIN来源闭包重基，规划12个首次新TRAIN组及4dev/4test；离线恢复优先，缺链TRAIN才做原生2→6组有界补采。所有数量为工作目标，当前新增准入0、模型/训练/采集0；已有1250目标和55完整训练课程保持。后验版本消费不冒充父当时反馈，全部失败及费用保留，原226及保留组不回TRAIN。

---

"""
readme = REPO / "README.md"
original = readme.read_text(encoding="utf-8-sig")
if not original.startswith("## 下一轮独立经验与真实修订链增量计划56"):
    readme.write_text(prefix + original, encoding="utf-8")
refs = [{"path": p.relative_to(DEST).as_posix(), "bytes": p.stat().st_size, "sha256": sha(p)}
        for p in sorted(DEST.rglob("*")) if p.is_file() and p.name != "PUBLIC_MANIFEST.json"]
write(DEST / "PUBLIC_MANIFEST.json", {"schema": "wrd56-increment-planning-public-files", "design_revision": "5.0.56",
      "file_count": len(refs), "files": refs, "new_data_targets": 0, "training_started": False})
print(json.dumps({"plan": str(DEST), "files": len(refs), "plan_checks": len(checks), "manifest_sha256": sha(DEST / "PUBLIC_MANIFEST.json")}))
