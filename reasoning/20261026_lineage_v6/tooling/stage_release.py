"""Stage the audited v6 delivery and rolling byte manifest; never push/train."""
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[3]
AUDIT = ROOT / 'output/20261026_wrd_lineage_v6'
SEQ = ROOT / 'output/20261026_wrd_sequences_v6'
PLAN = ROOT / 'research/plans/20261026_wrd_lineage_v6'
RELEASE = ROOT / 'output/20261025_wrd_training_dataset/git_release'
DEST = RELEASE / 'reasoning/20261026_lineage_v6'
PUBLIC_PLAN = RELEASE / 'plans/20261026_lineage_training'


def sha(p):
    h = hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda: f.read(1048576), b''):
            h.update(b)
    return h.hexdigest()


def read(p):
    return json.loads(p.read_text(encoding='utf-8-sig'))


def save(p, v):
    p.write_text(json.dumps(v, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def rows(p):
    with gzip.open(p, 'rt', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                yield json.loads(line)


def main():
    data = read(SEQ / 'ADMITTED_DATA_REPORT.json')
    assert data['native_lineage_review_pending'] is False
    assert read(AUDIT / 'INDEPENDENT_FINAL_DATA_QA.json')['failures'] == []
    encrypted_qa = read(AUDIT / 'INDEPENDENT_ENCRYPTED_DELIVERY_QA.json')
    assert encrypted_qa['status'].startswith('PASS') and encrypted_qa['failures'] == []
    assert read(AUDIT / 'EXACT_PROTECTED_CONTENT_CHECK.json')['status'] == 'PASS_EXACT_CHECKS_ONLY'
    assert read(DEST / 'ADMITTED_DATA_REPORT.json') == data
    shutil.copyfile(AUDIT / 'INDEPENDENT_ENCRYPTED_DELIVERY_QA.json', DEST / 'INDEPENDENT_ENCRYPTED_DELIVERY_QA.json')
    shutil.copyfile(AUDIT / 'EXACT_PROTECTED_CONTENT_CHECK.json', DEST / 'EXACT_PROTECTED_CONTENT_CHECK.json')
    fixed = [r for r in rows(AUDIT / 'controlled/lineage_episode_decisions.jsonl.gz') if r['fixed91_member']]
    assert len(fixed) == 91
    decisions = [{k: r.get(k) for k in ('episode_id', 'kind', 'status', 'resource_closure_proven',
                 'native_verified', 'direct_protected_source_ids', 'ancestor_episode_ids',
                 'blocking_evidence', 'canonical_episode_sha256', 'evidence_refs')} for r in fixed]
    save(DEST / 'NATIVE91_AUDIT_TERMINALS.json', {
         'schema_version': 'wrd-v6-native91-terminal-audit-metadata',
         'terminal_counts': dict(Counter(r['status'] for r in decisions)), 'episodes': decisions,
         'does_not_claim_missing_ancestry_resolved': True, 'business_body_exported': False,
         'original226_preserved': True, 'training_started': False})
    gap = {'schema_version': 'wrd-v6-actual-stage-coverage-and-gaps',
           'native_WRD_positive_stages': {'A_route_selection': 0, 'B_workflow_resource_making': 0,
                                        'C_requirement_preparation': 0, 'C_effect_review': 0, 'D_qualified_freeze': 0},
           'historical_positive_operations': data['historical_original_model_high_level_action_kinds'],
           'historical_generation_resource_feedback_positive_responses': data['scopes']['controlled']['reasoning']['by_original_stage'].get('historical_skill_generation_candidate', 0),
           'actual_full_A_D_autonomous_native_chains': data['actual_full_A_D_autonomous_native_chains'],
           'source_pure_process_dataset_exists': True, 'native_full_pipeline_demonstrations_present': False,
           'fixed91_terminal_counts': dict(Counter(r['status'] for r in decisions)),
           'missing_reasons_occurrences_not_independent_cases': dict(Counter(b['reason'] for r in fixed if r['status'] == 'HOLD_MISSING_EVIDENCE' for b in r['blocking_evidence'])),
           'historic_FINISH_READY_is_not_retain_or_freeze': True,
           'actor_consumption_cannot_fill_maker_stage_gaps': True,
           'new_clean_native_full_chain_records_needed_to_support_complete_goal': True,
           'new_records_collected_or_training_started_this_round': False}
    save(DEST / 'COVERAGE_AND_GAPS.json', gap)
    rreview = read(AUDIT / 'INDEPENDENT_REASONING_REVIEW.json')
    save(DEST / 'CAUSAL_REPAIR_EXAMPLE.json', {
         'schema_version': 'wrd-v6-original-feedback-revision-example',
         'source_report_sha256': sha(AUDIT / 'INDEPENDENT_REASONING_REVIEW.json'),
         'example': rreview['complete_causal_repair_example_without_enterprise_body'],
         'historical_validator_fingerprint_limits': rreview['historical_grader_and_validator_fingerprint_limits'],
         'observed_development_pass_is_not_native_autonomous_or_independent_Q_result': True})
    save(DEST / 'DATA_ENTRYPOINT.json', {
         'schema_version': 'wrd-v6-positive-process-data-entrypoint',
         'process_sft_positive_data_ready': True, 'manifest': 'TRAINING_MANIFEST.json',
         'full_WRD_autonomous_training_data_sufficient': False,
         'training_execution_authorized': False, 'training_started': False,
         'public_arrays': 'data/', 'controlled_archive': 'controlled/wrd-lineage-process-v6.tar.gz.aesgcm',
         'controlled_key_stays_local_not_in_git': True,
         'do_not_merge_public_and_controlled_duplicate_views': True,
         'default_actor_auxiliary_enabled': False, 'optional_actor_auxiliary_max_loss_budget': 0.10,
         'historical_protocol_not_current_native_ABI': True,
         'original226_isolation_confirmed_and_preserved': True,
         'current_formal250_kept_isolated': True,
         'do_not_fallback_to_older_candidates_or_history_arrays': True,
         'plan': '../../plans/20261026_lineage_training/README.md'})
    (DEST / 'README.md').write_text('''# WRD v6：实际过程训练数据与资源血缘

**有实际正loss数据；完整原生自主沉淀训练集仍未充分。未启动训练。**

[真实训练manifest](TRAINING_MANIFEST.json) · [详细训练计划](../../plans/20261026_lineage_training/README.md) · [数据到模型能力的因果链](../../plans/20261026_lineage_training/CAUSAL_TRAINING_RATIONALE.md) · [阶段覆盖与缺口](COVERAGE_AND_GAPS.json)

| 可训练角色 | 本地受控窗口/响应 | owned助手目标 | 正监督tokens | ≤16K | ≤32K累计 |
|---|---:|---:|---:|---:|---:|
| 历史原思考/制作修订主过程 | 106 | 106 | 182659 | 44 | 106 |
| 原生业务Actor辅助 | 43 | 178 | 128269 | 31 | 43 |
| 原生WRD核心沉淀 | 0 | 0 | 0 | 0 | 0 |

历史主集含30条原始思考，121511纯R监督tokens；覆盖真实UPDATE12、INSPECT5、READ1、TRY10、FINISH2。其余76个原历史响应包括合法代码、读取、测试、反馈后修复。5次历史run是同一企业源的版本链，和SSE的8个原企业源之一重合，106不是106个独立任务。Actor另有32个原企业源，不能用它们补WRD制作能力；默认不混入主训练，最多10%辅助loss。

公开替代投影为72个历史主响应/80147监督tokens（9原R，49445纯Rtokens）和34个Actor窗口/105789监督tokens。选择公开或受控投影，不能相加训练。[完整数据报告](ADMITTED_DATA_REPORT.json)给出每档SHA、处理tokens、完整阶段/前缀与父来源数。

## 91场追溯结论

54场有实际保护来源/确定派生资源依赖，36场仍缺具体祖先身份或运行输入证据，1场只是源闭包成立的旧业务screen且未通过协议质量；因此91场没有新增合格WRD核心正例。每项终态、消息/资源证据见[NATIVE91_AUDIT_TERMINALS](NATIVE91_AUDIT_TERMINALS.json)。缺证没有被称已核清，候选producer没有被union成确定污染。所有原消息、工具动作、失败、反馈和修订证据完整保全在受控包。

## 一条实际反馈修订因果链

旧版程序输出 → 原验证反馈 → 下一run的同SHA真实投递 → 原教师响应0753780c…的两行局修 → 实际工具exit0及新程序SHA43ab… → 后续同版本12/12开发验证。原request/response、时间、文件和验证器指纹逐项见[CAUSAL_REPAIR_EXAMPLE](CAUSAL_REPAIR_EXAMPLE.json)。10个已知失败或未证正确的raw目标保持零loss，最后成功没有追认早期坏代码。原失败仍留在修复的输入历史里。

这能为领域资源设计和反馈条件修复提供直接监督；原生A筛选、B制作、C取题/双臂效能、D合格冻结以及单次输入自主阶段控制的干净示范仍缺。历史TRY/FINISH协议不等于现行OpenClaw原生调用，写skill或READY不等合格冻结。不能仅凭这些数据承诺得到完整理想模型。

## 文件与核验

`data/`是实际公开正例数组；`controlled/wrd-lineage-process-v6.tar.gz.aesgcm`含受控正例、原始上下文/思考、资源CAS、91全部记录、父版本/反馈及历史中间审核，包内逐成员manifest不等于全部训练准入。私钥沿用本机v4文件，未上传；[解密与mask说明](../../plans/20261026_lineage_training/DATA_LOADING.md)。旧约739MB原件包保持，本轮只新增证据与数据增量。

[独立数据QA](INDEPENDENT_FINAL_DATA_QA.json)逐行重建255行的两投影、双分词器编码解码和逐token角色mask，原30条R另从原SSE逐UTF8比对。[精确保护内容检查](EXACT_PROTECTED_CONTENT_CHECK.json)对最终149个受控正例与原226/正式250长请求和附件hash核验无重叠；这不替代资源血缘，也不宣称语义近重复完全隔离。[加密交付QA](INDEPENDENT_ENCRYPTED_DELIVERY_QA.json)核包内每成员SHA、认证和无私钥材料。

14B主、8B对照的[配置](../../plans/20261026_lineage_training/TRAINING_PLAN.json)保留BF16 LoRA与分段/父任务预算，当前106主窗口一遍仅约7次acc16更新，不能把重放当新数据。原226继续禁训/调参；原生OpenClaw环境、业务Actor和工具循环不改。[质量与每个合格技能全成本](../../plans/20261026_lineage_training/COST_AND_ACCEPTANCE.md)尚需未来新源训练/闭环实测，本轮没有模型权重、GPU或新增业务调用。
''', encoding='utf-8')
    # Bind public source bytes and both same-revision design files.
    provenance = {'schema_version': 'wrd-v6-source-byte-provenance', 'design_revision': '5.0.31', 'change_id': 'ALG-20261026-04',
                  'research_git_head': subprocess.check_output(['git', '-C', str(ROOT), 'rev-parse', 'HEAD']).decode().strip(),
                  'research_git_head_alone_does_not_capture_local_research_edits': True,
                  'source_script_sha256': {p.name: sha(p) for p in sorted((ROOT / 'research/data_prep/wrd_reasoning_v6').glob('*.py'))},
                  'design_sha256': {n: sha(ROOT / 'research/designs' / n) for n in ('A_B_MODULES.md', 'PIPELINE.md')},
                  'plan_files': [{'path': p.name, 'sha256': sha(p), 'bytes': p.stat().st_size} for p in sorted(PLAN.iterdir()) if p.is_file() and p.name != 'PROVENANCE.json'],
                  'data_compilation_manifest_sha256': sha(SEQ / 'TRAINING_MANIFEST.json'),
                  'training_started': False}
    save(PLAN / 'PROVENANCE.json', provenance)
    PUBLIC_PLAN.mkdir(exist_ok=True)
    for p in PLAN.iterdir():
        if p.is_file():
            shutil.copyfile(p, PUBLIC_PLAN / p.name)
    for p in sorted((ROOT / 'research/data_prep/wrd_reasoning_v6').glob('*.py')):
        shutil.copyfile(p, DEST / 'tooling' / p.name)
    p = RELEASE / 'TRAINING_ENTRYPOINT.json'
    entry = read(p)
    entry.update(status='POSITIVE_PROCESS_DATA_EXPORTED_FULL_NATIVE_WRD_COVERAGE_INSUFFICIENT',
                 recommended_dataset=None, process_sft_data_ready=True,
                 recommended_process_sft_manifest='reasoning/20261026_lineage_v6/TRAINING_MANIFEST.json',
                 full_training_readiness='plans/20261026_lineage_training/READINESS.json',
                 detailed_plan='plans/20261026_lineage_training/README.md', data_entrypoint='reasoning/20261026_lineage_v6/DATA_ENTRYPOINT.json',
                 current_scope_audit='reasoning/20261026_lineage_v6/README.md',
                 training_manifest_admitted_rows={'controlled_main': 106, 'controlled_optional_actor': 43, 'public_main': 72, 'public_optional_actor': 34},
                 final_training_manifest='reasoning/20261026_lineage_v6/TRAINING_MANIFEST.json',
                 training_ready=False, training_execution_authorized=False, training_started=False)
    save(p, entry)
    for name in ('reasoning/20261025/DATA_ENTRYPOINT.json',):
        p = RELEASE / name
        old = read(p)
        old.update(superseded_for_current_admission=True,
                   latest_process_training_manifest='../20261026_lineage_v6/TRAINING_MANIFEST.json',
                   latest_plan='../../plans/20261026_lineage_training/README.md',
                   latest_process_data_is_nonempty=True)
        save(p, old)
    p = RELEASE / 'README.md'
    original = p.read_text(encoding='utf-8-sig')
    prefix = ('# 当前交付：资源闭包与真实过程SFT数据v6\n\n'
              '[实际训练数据](reasoning/20261026_lineage_v6/README.md) · [新计划与明确因果链](plans/20261026_lineage_training/README.md)\n\n'
              '主过程106原响应、182659监督tokens（30原思考）；43个原生业务Actor辅助窗另列。原生WRD核心/完整A—D自主链仍为0，不能声称完整理想模型训练数据已足量。原226继续隔离，未训练。下方v4/v5为历史交付口径，当前按v6manifest。\n\n---\n\n')
    if not original.startswith('# 当前交付：资源闭包'):
        p.write_text(prefix + original, encoding='utf-8')
    p = RELEASE / 'reasoning/20261025/MANIFEST.json'
    previous = read(p)
    frozen = AUDIT / 'MANIFEST.baseline_4cc8fdb.json'
    if not frozen.exists():
        shutil.copyfile(p, frozen)
    paths = {r['path'] for r in previous['files']}
    paths.update(p.relative_to(RELEASE).as_posix() for p in DEST.rglob('*') if p.is_file())
    paths.update(p.relative_to(RELEASE).as_posix() for p in PUBLIC_PLAN.rglob('*') if p.is_file())
    previous.update(schema_version='wrd-reasoning-public-rolling-manifest-v6',
                    latest_final_training_manifest='reasoning/20261026_lineage_v6/TRAINING_MANIFEST.json',
                    latest_data_entrypoint='reasoning/20261026_lineage_v6/DATA_ENTRYPOINT.json',
                    baseline_final_commit='4cc8fdb9097c55a4b1fce84da6fc628f6d600ea3')
    previous['files'] = [{'path': n, 'sha256': sha(RELEASE / n), 'bytes': (RELEASE / n).stat().st_size} for n in sorted(paths)]
    save(p, previous)
    print(json.dumps({'status': 'STAGED_FOR_REVIEW_NOT_PUSHED', 'payload_files': len(previous['files']),
                      'payload_bytes': sum(r['bytes'] for r in previous['files']), 'manifest_sha256': sha(p), 'training_started': False}))


if __name__ == '__main__':
    main()
