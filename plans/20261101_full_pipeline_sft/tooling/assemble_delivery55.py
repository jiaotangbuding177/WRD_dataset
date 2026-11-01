"""Assemble reviewed planning artifacts only; no credentials, model, or training."""
from pathlib import Path
import hashlib
import json
import shutil

BASE = Path(__file__).resolve().parents[3]
RELEASE = BASE / "output/20261025_wrd_training_dataset/git_release"
WORK = BASE / "output/20261101_wrd_git_full_delivery"
SOURCE = BASE / "research/plans/20261101_wrd_full_pipeline_sft"
DEST = RELEASE / "plans/20261101_full_pipeline_sft"

def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for data in iter(lambda: stream.read(1048576), b""):
            h.update(data)
    return h.hexdigest()

def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

def copy(src, target):
    if not src.is_file() or src.is_symlink():
        raise ValueError(f"Expected regular reviewed source: {src}")
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, target)
    if sha(src) != sha(target):
        raise ValueError("Copy digest mismatch")

def main():
    for name in ("PLAN.md", "TRAINING_CONFIG.json", "RESTORE_AND_VALIDATE.md"):
        copy(SOURCE / name, DEST / name)
    for name in ("FULL_COURSE55.json", "STATS55.json", "COURSE_QA55.json", "OPTIMIZATION_GUARD55.json"):
        copy(WORK / "course55" / name, DEST / name)
    copy(WORK / "course55/README.md", DEST / "COURSE_README.md")
    course_readme = DEST / "COURSE_README.md"
    course_readme.write_text(course_readme.read_text(encoding="utf-8").replace(
        "python verify_course55.py", "python tooling/verify_course55.py"), encoding="utf-8")
    copy(WORK / "course55/verify_course55.py", DEST / "tooling/verify_course55.py")
    copy(BASE / "research/data_prep/wrd_curation11/curriculum_loader11.py", DEST / "tooling/curriculum_loader11.py")
    copy(Path(__file__), DEST / "tooling/assemble_delivery55.py")
    for name in ("DATA_DELIVERY_REVIEW.json", "DATA_DELIVERY_REVIEW.md", "PLAN_REVIEW.md"):
        copy(WORK / name, DEST / "reviews" / name)
    for name in ("ALL1250_JOINT_TRAINABILITY_QA.json", "MODULE_TARGET_COUNTS.json", "MODULE_MAP_REVIEW.md", "audit_joint1250.py"):
        copy(BASE / "output/20261101_wrd_training_value" / name, DEST / "reviews" / name)
    for name in ("A_B_MODULES.md", "PIPELINE.md"):
        copy(BASE / "research/designs" / name, DEST / "designs" / name)
        copy(BASE / "research/designs/history/5.0.54/full_sft_delivery_20261101" / name,
             DEST / "designs/history/5.0.54" / name)
    copy(BASE / "research/memory/2026-11-01_wrd_full_pipeline_sft_scope.md", DEST / "reviews/SCOPE_CLARIFICATION.md")
    data = json.loads((WORK / "DATA_DELIVERY_REVIEW.json").read_text(encoding="utf-8-sig"))
    deps = {"schema": "wrd55-complete-data-dependencies", "design_revision": "5.0.55",
            "order": data["required_package_order"], "packages": data["packages"],
            "total_entity_bytes": sum(x["bytes"] for x in data["packages"]),
            "base_primary_targets": 623, "additional_auxiliary_targets": 627,
            "available_unique_targets": 1250, "existing_local_key_required_for05_through10": True,
            "key_or_credentials_in_git": False, "training_started": False}
    write(DEST / "DATA_DEPENDENCIES.json", deps)
    entry = json.loads((RELEASE / "TRAINING_ENTRYPOINT.json").read_text(encoding="utf-8-sig"))
    entry.update({
        "schema_version": "wrd-full-pipeline-stepwise-sft55-entrypoint",
        "status": "COMPLETE_A_TO_D_STEPWISE_JOINT_SFT_DATA_AND_COURSE_VERIFIED",
        "recommended_dataset": "plans/20261101_full_pipeline_sft/FULL_COURSE55.json",
        "training_ready": True,
        "training_ready_scope": "DATA_AND_SUPERVISION_FOR_COMPLETE_PIPELINE_STEPWISE_JOINT_SFT_NOT_SPARK_RUNTIME_OR_PROVEN_AUTONOMY",
        "joint_full_pipeline_sft_data_ready": True,
        "training_execution_authorized": False, "training_started": False,
        "current_plan": "plans/20261101_full_pipeline_sft/PLAN.md",
        "current_statistics": "plans/20261101_full_pipeline_sft/STATS55.json",
        "current_data_entrypoint": "plans/20261101_full_pipeline_sft/RESTORE_AND_VALIDATE.md",
        "current_QA": "plans/20261101_full_pipeline_sft/COURSE_QA55.json",
        "current_plan_design_revision": "5.0.55",
        "default_full_pipeline_training_entrypoint": "plans/20261101_full_pipeline_sft/TRAINING_CONFIG.json",
        "default_full_pipeline_entrypoint_is_launch_config": False,
        "current_complete_course_unique_targets": 1250,
        "current_complete_course_exposures": 1254,
        "current_complete_course_candidate_optimizer_updates": 236,
        "current_complete_course_contract_required_targets": 418,
        "current_complete_course_process_required_targets": 832,
        "current_complete_course_positive_tokens_exposed": 286573,
        "current_process_only_pool_is_not_the_complete_course": True,
        "current_manifest_623_counts_are_retained_with_original_scope": True,
        "runtime_native53_and_long_context_verified": False,
        "complete_autonomous_student_model_verified": False,
        "remote_status": "SEE_LATEST_EXTERNAL_DELIVERY_RECEIPT",
        "latest_delivery_receipt": "deliveries/20261101_full_data_and_plan/REMOTE_VERIFICATION.json",
        "remote_verification": None,
    })
    write(RELEASE / "TRAINING_ENTRYPOINT.json", entry)
    prefix = """## 当前完整流程SFT计划55（2026-11-01）

[完整14B主／8B对照训练计划](plans/20261101_full_pipeline_sft/PLAN.md) · [完整数据恢复](plans/20261101_full_pipeline_sft/RESTORE_AND_VALIDATE.md) · [明确配置](plans/20261101_full_pipeline_sft/TRAINING_CONFIG.json) · [实际课程验收](plans/20261101_full_pipeline_sft/COURSE_QA55.json)

**当前已具备覆盖A—D完整流程的逐步联合SFT数据入口。**实际1,250唯一目标、284,595正监督；正式课程418契约接832过程，同一adapter共1,254曝光、236次候选更新。budget主课程10,244,527序列tokens，full53同目标参照20,820,961。两profile互斥，原记录／投影／构造明确分账。

完整数据为05→10认证主根＋11公开辅助包，七个真实实体共1,307,762,484字节，路径与SHA见[数据依赖](plans/20261101_full_pipeline_sft/DATA_DEPENDENCIES.json)；历史原始12分卷与原始过程保留。旧包使用用户已有本地密钥，密钥不在Git。

原226及保留来源继续隔离；没有启动训练。Spark运行和训练后的完整自主沉淀效果按计划验收。当前远端交付状态以[最新实体与计划回读回执](deliveries/20261101_full_data_and_plan/REMOTE_VERIFICATION.json)为准；以下旧计划、旧认证阻塞和组件范围是历史记录，当前训练范围以55为准。

---

"""
    readme = RELEASE / "README.md"
    current = readme.read_text(encoding="utf-8-sig")
    marker = "## 当前完整流程SFT计划55（2026-11-01）"
    if not current.startswith(marker):
        readme.write_text(prefix + current, encoding="utf-8")
    rows = []
    for path in sorted(DEST.rglob("*")):
        if not path.is_file() or path.name == "PUBLIC_MANIFEST.json":
            continue
        rows.append({"path": path.relative_to(DEST).as_posix(), "bytes": path.stat().st_size, "sha256": sha(path)})
    write(DEST / "PUBLIC_MANIFEST.json", {"schema": "wrd55-public-plan-files", "design_revision": "5.0.55",
          "files": rows, "file_count": len(rows), "includes_real_schedule_and_verifier": True,
          "does_not_include_keys_or_credentials": True, "training_started": False})
    print(json.dumps({"plan_directory": str(DEST), "files": len(rows),
          "public_manifest_sha256": sha(DEST / "PUBLIC_MANIFEST.json"), "data_entity_bytes": deps["total_entity_bytes"]}))

if __name__ == "__main__":
    main()
