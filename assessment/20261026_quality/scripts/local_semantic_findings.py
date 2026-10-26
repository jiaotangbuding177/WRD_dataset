"""Record bounded qualitative judgements after reading frozen sample windows.

These annotations are review findings, never original teacher reasoning or SFT
admission labels. No private sample prose is copied into the public findings.
"""
import gzip
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "output/20261026_wrd_quality_v8"

FINDINGS = {
    "ep_ffb911f51080dae2219f": ("no_visible_assistant_target", "该失败片段没有可见助手目标。保全失败上下文，不能作为完成筛选的正例。"),
    "ep_ff383c55c33b3b2c1f40": ("locally_explained_reuse_decisions", "选中窗口含路线复用/合并理由、写JSON及解析确认。可训练边界判断的候选；未重新审完其所有业务来源。"),
    "ep_7b84f5cbaff705866a96": ("locally_explained_reuse_decisions", "终态对既有路线复用和多目标来源归并给出理由。不是全新技能生成成功示范，实际来源匹配仍须逐条核。"),
    "ep_41c51bf0fdc75342576d": ("valuable_negative_no_eligible_case", "真实输出cases=[]，理由区分主要工作不匹配、必要附件缺失和不能为路线改题。有停止/不生成监督价值，不标成无训练价值或完整正链。"),
    "ep_34e0cda5cca61e5d3a23": ("valuable_negative_no_eligible_case", "按工作型态与真实输入限制拒绝挑选不相同任务，保留零case理由。未对全部检索结果重作领域真实性验证。"),
    "ep_ceb6322235d861031542": ("valuable_negative_no_eligible_case", "明确区分静态图片/PDF和解说视频任务，拒绝改写业务目标来凑试做。属于有用停止分支。"),
    "ep_4920642a6640d5045d90": ("explicitly_incomplete_despite_done_status", "最后可见响应明确列出尚未完成的资源说明、边界测试、外置记录和检查。catalog done不能充当按任务合同完成的正标签；原中间制作步骤可保留。历史native_verified=false另列。"),
    "ep_01d59386f68d59e981d5": ("valuable_feedback_repair_regression_sequence", "窗口含前版解析失败现象、实际新旧正则输出、局部修订范围及差异核对。是反馈→定位→局修→回归的可追踪过程候选；全部脚本/领域正确性不由窗口认证。"),
    "ep_8f9486608f94566d66e0": ("valuable_cost_feedback_revision_not_proven_saving", "复用已验证资源，按反馈压缩首页/合并检查命令，并披露未测依赖。体现修订逻辑，但尚未据此窗口证明修订后真实业务降本。"),
    "ep_29dc559a8c3eebb13e94": ("artifact_exists_domain_correctness_not_certified", "有真实文件写出和大小/行数反馈，也标注公开材料不足；法律/财务事实和时间表未由本轮窗口复核，不能因报告流畅或文件存在判为语义金标。"),
    "ep_a598313dbaff610df7fb": ("bounded_source_limits_visible_domain_judgement_pending", "可见对缺图/公式/抽查范围的明确说明与证据核查步骤。有边界监督价值，但全部学术结论正确性未由窗口认证。"),
    "ep_4459b810deb6fe70c6dc": ("concrete_content_defect_despite_successful_write", "实际CSS把白字放在#00C4A3背景，声明清晰度但计算对比度2.228:1，低于WCAG普通及大文字参考门槛。文件写成功不代表内容正确；错误局部不能作正loss目标，原观察与纠错材料保留。"),
    "ep_5f62806290465541ecd6": ("valuable_evidence_referenced_revise_decision", "评审区分资源可用、真实使用、交付与成本，成本上升判revise，并指出输出膨胀的具体位置。证据丰富，但本窗口未独立重验全部Word语义/成本账。"),
    "ep_ad9a7736ed5f8cd0fe45": ("valuable_tool_error_correction_and_revise", "write缺path被真实schema拒绝后补齐参数；再以成本升高作revise而非retain。有格式修复和评审边界监督价值，不训练错误write为正确动作。"),
    "ep_b6e5d59f1d5962bc9d7b": ("retain_claim_has_specific_evidence_not_independent_quality_gold", "retain响应给出版本、全文读取、交付和成本依据，所列降幅算术一致。领域内容和所有原账并未在该局部窗口独立认证，不把原评审意见等同独立Q金标。"),
    "ep_f5307185567b10c05c9b": ("legacy_actual_role_devprep_negative_boundary", "实际为开发任务准备，缺必要三类附件而HOLD。legacy不是无用类别；需按真实角色和来源条件重标。"),
    "ep_1807833aefd96e94795c": ("valuable_failure_explanation_actual_actor_role", "调度工具因过去时间拒绝，助手如实解释未创建并请求新时间，没有把done或尝试冒称业务成功。是失败恢复/限制识别候选，非成功创建正例。"),
    "ep_e991254d3c2e146615f4": ("legacy_actual_role_devprep_derived_task", "实际准备两个用户文本派生委托及验收底线，披露派生与缺件边界。不能把已聚合累积需求冒称原始多轮用户逐步可见输入；仅按该次实际Agent委托学习。"),
}


def luminance(value):
    channels = [int(value[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    channels = [v / 12.92 if v <= .04045 else ((v + .055) / 1.055) ** 2.4 for v in channels]
    return sum(a * b for a, b in zip(channels, [.2126, .7152, .0722]))


def ratio(foreground, background):
    high, low = sorted([luminance(foreground), luminance(background)], reverse=True)
    return (high + .05) / (low + .05)


def main():
    samples = [json.loads(line) for line in (OUT / "SEMANTIC_SAMPLE_WINDOWS.jsonl").read_text(encoding="utf-8").splitlines()]
    rows = []
    for sample in samples:
        label, note = FINDINGS[sample["episode_id"]]
        rows.append({"episode_id": sample["episode_id"], "old_stage": sample["old_kind_not_gold"], "source_event_archive_path": sample["source_event_archive_path"], "reviewed_target_indices_and_lines": [{"target_message_index": point["target_message_index"], "source_event_line": point["source_event_line"]} for point in sample["points"]], "finding": label, "deidentified_note": note, "assessor": "root_assistant_qualitative_review", "bounded_local_windows_only": True, "not_human_expert_gold": True, "whole_episode_quality_certified": False, "training_admission": "not_decided"})
    with (OUT / "LOCAL_SEMANTIC_FINDINGS.jsonl").open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    episode = None
    with gzip.open(ROOT / "output/20261025_wrd_training_dataset/bundle/canonical/native_episodes.jsonl.gz", "rt", encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            if row["episode_id"] == "ep_4459b810deb6fe70c6dc":
                episode = row
                break
    block = next(block for block in episode["messages"][11]["content"] if block.get("type") == "toolCall")
    code = block["arguments"]["content"]
    assert "background-color: var(--color-footer)" in code and "color: var(--color-text-on-footer)" in code
    assert "--color-footer: #00C4A3" in code and "--color-text-on-footer: #FFFFFF" in code
    (OUT / "NUMERIC_CONTENT_COUNTEREXAMPLE.json").write_text(json.dumps({"episode_id": episode["episode_id"], "target_message_index": 11, "source_event_line": episode["source_event_lines"][11], "original_code_sha256": hashlib.sha256(code.encode()).hexdigest(), "foreground": "#FFFFFF", "background": "#00C4A3", "computed_contrast_ratio": ratio("FFFFFF", "00C4A3"), "reference_normal_text_ratio": 4.5, "reference_large_text_ratio": 3.0, "reference": "https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html", "scope": "One exact CSS color pair in a sampled Actor response; no population semantic error rate inferred; no generated code executed.", "training_started": False}, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"bounded_local_semantic_reviews": len(rows), "population_quality_rate_estimated": False, "numeric_counterexample_ratio": ratio("FFFFFF", "00C4A3")}))


if __name__ == "__main__":
    main()
