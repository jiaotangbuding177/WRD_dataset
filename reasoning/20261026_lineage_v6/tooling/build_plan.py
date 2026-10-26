"""Generate the non-executable v6 plan from final, actually exported positives."""
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SEQ = ROOT / 'output/20261026_wrd_sequences_v6'
AUDIT = ROOT / 'output/20261026_wrd_lineage_v6'
PLAN = ROOT / 'research/plans/20261026_wrd_lineage_v6'


def read(p):
    return json.loads(p.read_text(encoding='utf-8-sig'))


def save(p, x):
    p.write_text(json.dumps(x, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    data = read(SEQ / 'ADMITTED_DATA_REPORT.json')
    manifest = read(SEQ / 'TRAINING_MANIFEST.json')
    lineage = read(AUDIT / 'LINEAGE_AUDIT_REPORT.json')
    assert data['native_lineage_review_pending'] is False
    assert data['reasoning_resource_closed_original_pairs'] == 116
    assert manifest['resource_closed_quality_covered_process_data_ready'] is True
    old = read(ROOT / 'research/plans/20261025_wrd_reasoning_distillation_v4/TRAINING_PLAN.json')
    cfg = {k: old[k] for k in ('models', 'hardware', 'sft', 'loss', 'conditional_dpo', 'on_policy', 'evaluation', 'cost')}
    cfg.update(schema_version='wrd-resource-closed-training-plan-v6', design_revision='5.0.31', change_id='ALG-20261026-04',
               execution_authorized=False, is_launch_config=False, training_started=False,
               full_goal='single-input autonomous WRD A/B/C/D in fixed native OpenClaw',
               current_data_support='source-closed historical domain reasoning/resource/feedback adaptation; optional native business Actor process',
               original226_kept_isolated=True, current_formal250_kept_isolated=True,
               evaluation_or_derived_feedback_may_tune_thresholds_or_checkpoints=False,
               final_training_manifest='../../reasoning/20261026_lineage_v6/TRAINING_MANIFEST.json')
    c = data['scopes']['controlled']
    main_windows = c['native_core']['windows'] + c['reasoning']['windows']
    cfg['actual_exposure_arithmetic'] = {
        'main_process_windows': main_windows,
        'main_owned_targets': c['native_core']['original_parent_targets'] + c['reasoning']['original_parent_targets'],
        'main_supervised_tokens_one_pass': c['native_core']['supervised_tokens'] + c['reasoning']['supervised_tokens'],
        'main_processed_input_tokens_one_pass': c['native_core']['input_tokens'] + c['reasoning']['input_tokens'],
        'microbatch': 1, 'gradient_accumulation': 16,
        'optimizer_updates_one_main_pass_ceiling': math.ceil(main_windows / 16),
        'optimizer_updates_if_all_optional_actor_loaded_ceiling': math.ceil((main_windows + c['actor_aux']['windows']) / 16),
        'tiny_update_count_not_claimed_sufficient': True,
        'future_exposure_grid_if_independent_development_sources_ready': [1.0, 2.0, 3.0],
        'replay_is_not_new_independent_data': True,
        'grid_execution_authorized': False}
    cfg['sft']['initial_normalized_exposure_epochs'] = None
    cfg['sft']['exposure_selection_status'] = 'Not frozen: actual main-pass update count is small and independent development is not prepared.'
    cfg['sft']['future_total_normalized_parent_exposure_cap'] = 3.0
    cfg['sft']['extra_feedback_exposure_max_fraction'] = 0.5
    cfg['sft']['extra_feedback_exposure_included_in_total_cap'] = True
    cfg['data_profiles'] = {'choose_one_projection': ['controlled_original', 'public_deidentified'],
                            'main': ['native_core_if_nonempty', 'historical_reasoning_domain_process'],
                            'optional_actor_aux_enabled_by_default': False,
                            'optional_actor_aux_max_loss_fraction': 0.10,
                            'source_closed_known_quality_process_sft_data_ready': True,
                            'full_autonomous_target_data_sufficiency_proven': False,
                            'historical_protocol_is_not_native_ABI': True,
                            'old_BCD_effect_conclusions_are_not_quality_gold': True}
    cfg['serialization'] = {'causal_qwen3_template_variant': True,
                            'causal_template_sha256': manifest['causal_template_sha256'],
                            'same_variant_required_in_future_student_API': True,
                            'thinking_mode_intended_for_exploration_repair': True,
                            'inference_template_or_thinking_switch_integration_verified': False,
                            'context_and_output_share_32768_total_candidate_budget': True}
    cfg['loss']['sparse_missing_native_stages_are_not_synthetically_filled'] = True
    cfg['loss']['stage_weights_apply_only_when_original_stage_is_evidenced'] = True
    cfg['loss']['historical_banks_not_relabelled_as_complete_native_stages'] = True
    cfg['loss']['parent_normalization_unit'] = 'original business source/task; five raw versions of the same source share the parent budget'
    cfg['loss']['original_reasoning_parent_replay_max_normalized_passes'] = 3
    cfg['loss']['candidate_original_reasoning_supervision_exposure_fraction'] = None
    cfg['loss']['R_exposure_target_status'] = 'Old v4 10% replay target is inapplicable: use actual final data composition and segment/parent loss budgets.'
    cfg['loss']['actual_main_pure_R_supervised_token_fraction'] = c['reasoning']['supervised_tokens_by_component'].get('R', 0) / max(1, cfg['actual_exposure_arithmetic']['main_supervised_tokens_one_pass'])
    cfg['loss']['boundary_component_assignment_once_only'] = {
        'R_BOUNDARY_MIXED': 'R_original_reasoning', 'F': 'format_auxiliary', 'MIXED': 'format_auxiliary'}
    cfg['loss']['base_span_weights_applied_within_each_component_weighted_mean'] = True
    cfg['loss']['actor_aux_optional_default_disabled_to_focus_on_distillation_maker'] = True
    cfg['cost']['current_preparation_business_model_calls'] = 0
    cfg['cost']['current_assistant_review_service_currency_cost'] = None
    save(PLAN / 'TRAINING_PLAN.json', cfg)
    save(PLAN / 'DATA_REPORT.json', data)
    readiness = {'schema_version': 'wrd-v6-separated-process-and-autonomy-readiness',
                 'positive_process_sft_dataset_ready': True,
                 'final_positive_files_exist_with_nonempty_owned_loss': True,
                 'training_execution_authorized': False, 'training_started': False,
                 'full_autonomous_target_training_ready': False, 'deployment_ready': False,
                 'independent_development_or_holdout_ready': False,
                 'actual_full_A_D_autonomous_native_chains': data['actual_full_A_D_autonomous_native_chains'],
                 'native_core_positive_windows': c['native_core']['windows'],
                 'current_native_actor_is_not_WRD_maker_supervision': True,
                 'open_gaps': ['Source-pure native WRD A route selection, B production, C task selection/comparison, D qualified freeze demonstrations are not supplied by historical domain pairs or Actor consumption.',
                              'No verified single-input autonomous A-to-D native demonstration; outer stage dispatch is not a student decision.',
                              'Independent development/holdout, semantic near-duplicate separation, causal-template inference ABI and GB10 ARM64 forward/backward feasibility remain unverified.',
                              'Historical original-reasoning sources and five raw repair runs have limited independent diversity; replay cannot expand it.',
                              'Offline teacher-state SFT does not establish recovery from student-own errors or quality/cost targets.'],
                 'blocked_91_audit_terminal_counts': lineage['fixed91_terminal_counts']}
    save(PLAN / 'READINESS.json', readiness)
    lines = []
    for scope, label in (('controlled', '本地受控原件'), ('public', '公开去标识投影')):
        for bank, name in (('native_core', '原生WRD沉淀主体'), ('reasoning', '历史原思考/制作修订'), ('actor_aux', '原生业务Actor辅助')):
            r = data['scopes'][scope][bank]
            lines.append(f"| {label} | {name} | {r['windows']} | {r['original_parent_targets']} | {r['supervised_tokens']} | {r['input_tokens']} | {r['le16k_windows']} | {r['le32k_windows']} |")
    totals = lineage['fixed91_terminal_counts']
    text = f'''# WRD训练计划v6：资源血缘、真实正例与目标能力

2026-10-26；双稿5.0.31 / ALG-20261026-04。**不启动训练。** 原226保持评测隔离，不训练、补注回流或调参；当前正式250同样保留。

本轮交付实际正loss数据、原上下文/资源和反馈修订链。它们可用于过程SFT；现有数据**尚不足以声称已覆盖你的完整原生自主沉淀目标**。这两个结论分开，不能因未训练把可用数据仍说成候选，也不能因恢复了数据就保证最终模型。

## 实际可训练数据

| 投影 | 数据角色 | 窗口/完整响应 | owned助手目标 | 正监督tokens | 处理input tokens | ≤16K窗口 | ≤32K累计 |
|---|---|---:|---:|---:|---:|---:|---:|
''' + '\n'.join(lines) + f'''

受控与公开是同源投影，选一种使用，不能相加。Actor是消费业务的辅助数据，默认不混入主训练，预算最多10%；不能用它补WRD制作阶段数。历史响应保留原system/tools和执行条件，不冒称现行原生工具ABI。原R、失败上下文、反馈、实际工具返回都保留；环境观察和已知错误目标不计算正loss。详情见[DATA_REPORT](DATA_REPORT.json)和[实际训练manifest](../../reasoning/20261026_lineage_v6/TRAINING_MANIFEST.json)。

主过程数据一遍约{main_windows}个窗口，按microbatch1×累积16只有约{math.ceil(main_windows/16)}次更新，不能只写“1epoch”就宣称足够。曝光选择须在未来独立开发源上有限比较，本轮没有启动搜索。历史主集内有{c['reasoning']['original_R_positive_windows']}条含原始思考，R正文{c['reasoning']['supervised_tokens_by_component'].get('R', 0)}tokens；各分支动作和原source/run见DATA_REPORT，SSE增量帧、子字段和重复窗口不计独立任务。

## 91个会话的真实结论

终态分类：{json.dumps(totals, ensure_ascii=False)}。每项都有原消息、实际读取、资源身份、创建前prefix/确定复制或具体缺证。source闭合还要经过系统/工具/质量审核，不能直接计训练。原标screen的一场是旧业务消费，不是WRD A筛选。91里的80份父文档与全1763范围119条结构化候选不同；旧文字易误读，本版明确纠正，子字段不增加独立样本。

有保护正文/确定资源祖先的隔离；身份不明的作者或运行输入保留具体缺证，不伪称已核清。初始目录可用不当正文已读；晚于资源创建的信息不倒污染早期产物；确定逐字段复制继续追原作者，不因复制会话其他内容重新染色。全部原始链和未决证据通过加密包交付。

## 为什么这样训练，以及不能承诺什么

[明确的因果链与训练算法](CAUSAL_TRAINING_RATIONALE.md)按“当时输入→原思考/动作→实际观察→反馈后真实修订/停止”逐层解释直接监督信号。SFT学习这些条件行为；片段/父任务预算避免长代码淹没选择，原工具返回不当目标，错误不因最后成功变正确。它可以支持领域理解、资源设计、反馈条件修复和已有原生操作适配；原生WRD阶段数据和自主控制示范缺失时，不能推导出模型必然会自行串完整A—D。

14B主、8B对照均用固定Qwen3 revision、同数据/模板/曝光和原生工具合同；BF16 LoRA r32/alpha64、microbatch1/累积16等见[TRAINING_PLAN](TRAINING_PLAN.json)。ARM64 NVIDIA栈、同因果模板/原生thinking模式及8K/16K/32K前后向尚需未来实测，不把内存规格当已跑通。

后续验收必须从单次业务输入启动，模型自行选择目标与工具；教师/14B/8B比较TSR、独立五维Q、资源复现、正确停止和自身失败恢复。主要技能质量比较固定业务Actor。每个合格技能总成本包括所有失败、修订、评审、Actor、教师/人工兜底和训练/数据整理摊销；不知道的费用不记0。本轮没有模型效果或Spark速度/能耗结果。

## 下一步缺口

首先补新且与原226/正式250隔离的原生WRD路线筛选、制作、取题、双臂比较、修订和合格冻结示范，并保留模型自己的阶段控制。若现有未决原件不能补齐，就需要新的干净过程记录；不能靠补注伪造工具返回或增加重复次数获得这些证据。独立开发与留出源、工具/模板兼容和后续学生自身错误测试也未就绪。当前[READINESS](READINESS.json)明确为过程数据ready、完整自主目标false。

[准入合同](ADMISSION_CONTRACT.md) · [数据、掩码和解密说明](DATA_LOADING.md)。所有旧候选、失败、未决、原思考原件保全，未执行旧自建Agent、未启动新原生业务、模型权重或GPU训练。
'''
    (PLAN / 'README.md').write_text(text, encoding='utf-8')
    save(PLAN / 'SOURCE_RECEIPTS.json', {'schema_version': 'wrd-v6-plan-input-receipts',
         'design_revision': '5.0.31', 'change_id': 'ALG-20261026-04',
         'source_sha256': {str(p.relative_to(ROOT)).replace('\\', '/'): sha(p) for p in
                          [SEQ / 'ADMITTED_DATA_REPORT.json', SEQ / 'TRAINING_MANIFEST.json', AUDIT / 'LINEAGE_AUDIT_REPORT.json',
                           ROOT / 'research/designs/A_B_MODULES.md', ROOT / 'research/designs/PIPELINE.md']},
         'training_started': False})
    print(json.dumps({'plan_generated': True, 'main_process_windows': main_windows,
                      'main_updates_one_pass': math.ceil(main_windows / 16), 'training_started': False}))


if __name__ == '__main__':
    main()
