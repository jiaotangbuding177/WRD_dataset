"""Assemble an allowlisted offline preflight release; never pushes or trains."""
from __future__ import annotations
import argparse
import gzip
import hashlib
import importlib.metadata
import json
from pathlib import Path
import shutil
import time


def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()


def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def save(p,v):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def cp(src,dst):dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst)


def verify_receipts(root,records):
    for record in records:
        path=(root/record['path']).resolve()
        if not path.is_relative_to(root.resolve()) or not path.is_file():raise ValueError('receipt path outside declared root or missing')
        if path.stat().st_size!=record['bytes'] or sha(path)!=record['sha256']:raise ValueError('receipt bytes/hash mismatch: '+record['path'])


def main():
    q=argparse.ArgumentParser();q.add_argument('--preflight',type=Path,required=True);q.add_argument('--repo',type=Path,required=True);q.add_argument('--plan',type=Path,required=True);q.add_argument('--bundle',type=Path,required=True);q.add_argument('--design-revision',default='5.0.21');a=q.parse_args()
    started=time.monotonic();base=a.preflight.resolve();public=base/'prepared_gated/public';compiled=base/'work_compiled_full'
    admission=load(public/'FINAL_ADMISSION.json');prep=load(public/'reports/preparation.json');tokens=load(compiled/'report.json')
    if admission.get('status')!='PASS' or not admission.get('release_ready'):raise ValueError('final admission not release ready')
    if tokens['limited_run'] is not None or tokens['training_started'] or tokens['weights_loaded'] or tokens['gpu_used']:raise ValueError('not a full CPU-only audit')
    if admission['compiler_report_sha256']!=sha(compiled/'report.json'):raise ValueError('admission/compiler binding changed')
    verify_receipts(public,admission['files']);verify_receipts(compiled,tokens['files'])
    verify_receipts(public/'data',[{**r,'path':r['name']} for r in tokens['inputs']])
    if tokens['counts']['rows_seen']!=prep['counts']['public:actions']+prep['counts']['public:labels']:raise ValueError('public population mismatch')
    all_root=base/'work_compiled_controlled_all';all_tokens=load(all_root/'report.json')
    if (all_tokens['limited_run'] is not None or all_tokens['training_started'] or all_tokens['weights_loaded'] or all_tokens['gpu_used']
        or all_tokens['status'] not in {'PASS','COMPLETE_WITH_FAILURES'} or all_tokens['counts']['rows_seen']!=admission['expected_candidate_population']):
        raise ValueError('controlled-all population/CPU-only completion mismatch')
    verify_receipts(all_root,all_tokens['files'])
    verify_receipts(base/'prepared_gated/local_clean_inputs',[{**r,'path':r['name']} for r in all_tokens['inputs']])
    dest=a.repo.resolve()/'preflight/20261025'
    if dest.resolve().parent!=a.repo.resolve()/'preflight':raise ValueError('unexpected release target')
    if dest.exists() and any(dest.iterdir()):raise ValueError('release target must be absent or empty; stale files are never merged')
    shutil.copytree(public,dest,dirs_exist_ok=True)
    # Copy only the public arrays, their harmless indexes, and audit report.
    shutil.copytree(compiled/'compiled/public_candidates',dest/'compiled/compiled/public_candidates',dirs_exist_ok=True)
    shutil.copytree(compiled/'ids',dest/'compiled/ids',dirs_exist_ok=True)
    for n in ('row_lengths.jsonl','compile_failures.jsonl','report.json'):cp(compiled/n,dest/'compiled'/n)
    cp(base/'work_compiled_controlled_all/report.json',dest/'reports/controlled_all_token_report.json')
    cp(base/'work_compiled_controlled_all/row_lengths.jsonl',dest/'audit/all_candidate_lengths.jsonl')
    cp(base/'work_compiled_controlled_all/compile_failures.jsonl',dest/'audit/all_candidate_compile_failures.jsonl')
    for n,source in {
      'semantic_review_summary.json':base/'work_reports/semantic_review_summary.json',
      'structure_report.json':base/'work_structure/structure_report.json',
      'label_recovery_report.json':base/'work_labels/label_recovery_report.json',
      'label_portability_replay.json':base/'work_labels_portable_check/label_recovery_report.json',
      'support_extraction_report.json':base/'work_support/support_extraction_report.json',
      'archive_coverage.json':base/'work_archive_inventory/archive_coverage.json',
      'controlled_all_safe_summary.json':base/'work_reports/controlled_all_safe_summary.json',
    }.items():cp(source,dest/'reports'/n)
    cp(base/'work_reports/AUDIT_METHOD.md',dest/'AUDIT_METHOD.md')
    save(dest/'LABEL_COMPLETENESS.json',{'schema_version':'wrd-label-completeness-v1',
         'terminal_recovered_and_exact_last_message':347,'terminal_standard_core7':343,'terminal_noncore_quarantine':4,
         'core_terminal_semantically_reviewed':125,'core_terminal_semantically_unreviewed':218,
         'direct_routes_json_write_targets':36,'direct_decision_subannotations':546,'independent_extra_sft_samples_from_subannotations':0,
         'screen_exec_targets_retained_as_commands_not_blindly_converted_to_decision_gold':337,
         'final_routes_artifacts_recovered':63,'final_routes_artifacts_missing':2,'final_artifact_decisions_evidence_only':1292,
         'final_artifact_routes_evidence_only':661,'future_artifact_inserted_into_past_prompt':False,
         'all_route_decisions_semantically_approved':False,'human_gold':0,'training_started':False})
    cp(base/'work_archive_inventory/archive_opaque_inventory.jsonl.gz',dest/'support/archive_opaque_inventory.jsonl.gz')
    if (base/'work_reports/publication_wiring_review.json').exists():cp(base/'work_reports/publication_wiring_review.json',dest/'reports/publication_wiring_review.json')
    if (base/'work_reports/public_payload_spotcheck.json').exists():cp(base/'work_reports/public_payload_spotcheck.json',dest/'reports/public_payload_spotcheck.json')
    script_root=Path(__file__).resolve().parent
    for script in script_root.glob('*.py'):cp(script,dest/'scripts/wrd_training_preflight'/script.name)
    cp(script_root.parent/'wrd_training/training.py',dest/'scripts/wrd_training/training.py')
    for n in ('native_coding_tools_97a0.json','native_coding_tools_97a0.provenance.json'):
        cp(a.bundle/'protocol'/n,dest/'scripts/wrd_training/resources'/n)
        cp(a.bundle/'protocol'/n,dest/'protocol'/n)
    shutil.copytree(base/'tokenizer_assets',dest/'tokenizer_assets',dirs_exist_ok=True)
    cp(a.plan,dest/'plan_snapshot/TRAINING_CONFIG.json')
    versions={x:importlib.metadata.version(x) for x in ('transformers','tokenizers','jinja2','jsonschema','PyMuPDF','torch')}
    (dest/'requirements-audit.txt').write_text('\n'.join(f'{k}=={versions[k]}' for k in ('transformers','tokenizers','jinja2','jsonschema','PyMuPDF'))+'\n',encoding='utf-8')
    save(dest/'CPU_ENVIRONMENT.json',{'scope':'Observed Windows CPU audit, not a Spark training dependency lock','packages':versions,'torch_installation_not_requested':True,'training_started':False})
    save(dest/'PUBLICATION_SCOPE.json',{'schema_version':'wrd-training-preflight-v1','design_revision_at_task_start':'5.0.21','design_revision_at_delivery':a.design_revision,
         'enterprise_semantic_data_publication_authorized_by_user':True,'publication_policy_supersedes_previous_plan_only_scope':True,
         'candidate_body_scope':'known-pattern-clear and table-gate-clear derived records only; not a complete anonymization certification',
         'controlled_not_published':['private salt and reversible mappings','held personal records and uncertain column-linked tables','unreviewed original binary attachments','runtime dependency archive bodies and version-control internals'],
         'held_records_have_public_reason_manifests':True,'complete_archive_metadata_alias_count':654948,'all_archive_bytes_publication_asserted':False,
         'original_archive_not_repacked_or_reuploaded':True,'formal_226_250_and_current49_outputs_not_new_training_inputs':True,'dataset_license_assigned_in_this_task':False,
         'model_weights_loaded':False,'gpu_used':False,'training_started':False})
    save(dest/'OFFLINE_COST_LEDGER.json',{'scope':'This offline audit only; not model CPQS','support_extraction_final_wall_seconds':load(base/'work_support/support_extraction_report.json')['elapsed_seconds'],
         'preparation_wall_seconds':prep['elapsed_seconds'],'token_compilation_wall_seconds':tokens['elapsed_seconds'],
         'controlled_all_token_compilation_wall_seconds':all_tokens['elapsed_seconds'],
         'public_and_controlled_compilations_ran_concurrently':True,'summing_stage_wall_seconds_is_not_total_elapsed_wall_time':True,
         'aborted_earlier_preparation_attempt':{'reason':'add table-column publication gate before writing public data','wall_seconds_lower_bound':63.7,'exact_cost':None},
         'archive_inventory_wall_seconds':load(base/'work_archive_inventory/archive_coverage.json')['elapsed_seconds'],
         'earlier_canary_and_revision_runs_must_be_counted':True,'total_paid_audit_cost':None,'assistant_audit_compute_cost':None,'cpu_energy_kwh':None,'human_hour_rate':None,
         'unmeasured_cost_is_not_zero':True,'new_training_gpu_hours':0,'new_teacher_actor_judge_experiment_calls':0,
         'KG':None,'CPQS':None,'reason_qualification_and_cost_not_measured':'No student training or new skill-consumption evaluation; preprocessing wall time is not Spark throughput.'})
    cov=tokens['coverage_public_candidates'];ec=tokens['coverage_training_eligible'];c=prep['counts']
    silver_stats=load(public/'reports/sft_statistics.json')
    ac=all_tokens['counts'];all16=ac.get('common16k',0);all32=all16+ac.get('common32k_long',0)
    save(dest/'READINESS.json',{'scope':'Release integrity and technical silver admission are distinct from full training readiness',
         'release_integrity_passed':bool(admission['release_ready']),'full_scale_training_ready':False,'training_execution_authorized':False,
         'all_core_candidates':7117,'all_core_compiled_identical':ac.get('compiled_models_identical',0),
         'all_core_complete_le16k':all16,'all_core_complete_le32k':all32,
         'public_compile_report':'compiled/report.json','controlled_all_report':'reports/controlled_all_token_report.json',
         'controlled_all_arrays_published':False,'admitted_silver_report':'FINAL_ADMISSION.json',
         'unresolved':['300-action primary audit below proposed95percent gate','218 make terminal candidates not semantically reviewed',
                       'human semantic gold zero','no independent dev/test groups','Spark training compatibility, memory and throughput unmeasured',
                       f"16K admitted silver {admission['counts']['final_common16k']} and <=32K {admission['counts']['final_admitted']}, below planned128-256 smoke pool; no duplicate padding",
                       'direct route-decision admitted parent only1, reuse16 subdecisions; new/defer/no_value have no admitted direct positives'],
         'training_started':False})
    guide=f'''# WRD 14B / 8B 训练前数据审核包

2026-10-25。已完成离线整理与 CPU 编译，**未启动训练、加载模型权重或使用 GPU**。

本包与 [14B 主模型 / 8B 对照方案](../../plans/20261025_14b_spark/README.md) 配套。新增公开范围已按本轮用户授权包含处理后的企业语义内容。原归档及历史失败保留，不改原文伪造正例。

| 核对层 | 实际数量 |
| --- | ---: |
| 原主动作候选 | 6,774 |
| 恢复真实末条收尾 | 347（343 核心格式，4 非核心隔离） |
| 核心格式总审核母表 | 7,117 |
| 可公开正文动作 / 收尾 | {c.get('public:actions',0)} / {c.get('public:labels',0)} |
| 结构存在明确问题 | 113（错误类别可重叠） |
| AI 审阅唯一目标 | 425（动作300＋收尾125），另60条动作二审 |
| 人工语义 gold / 独立 dev-test 连通组 | 0 / 0 |
| 全7117候选双模型完整编译通过 | {ac.get('compiled_models_identical',0)} |
| 全7117候选 ≤16K / ≤32K（累计） | {all16} / {all32} |
| 公开候选双模型完整编译通过 | {tokens['counts'].get('compiled_models_identical',0)} |
| 公开候选 ≤16K | {cov['complete_le_16k']} / {cov['denominator']} |
| 公开候选 ≤32K（累计） | {cov['complete_le_32k']} / {cov['denominator']} |
| 编译前语义银标 ≤16K / ≤32K（累计） | {ec['complete_le_16k']} / {ec['complete_le_32k']}（分母 {ec['denominator']}） |

最终可进入后续小规模验证的技术银标数量，以 [FINAL_ADMISSION.json](FINAL_ADMISSION.json) 和 [admission.jsonl.gz](admission.jsonl.gz) 为准。源候选中的 `training_eligible` 是编译前标志，不能据此跳过协议、mask 和长度门。两模型已共用同一份 ID 和数组；后续训练还须固定同样顺序与曝光量，当前未训练。

全7117候选另在本地做了相同CPU编译，汇总和无正文长度/失败统计已附；被隔离正文与其token数组留在本地。公开报告仅使用公开的两个输入文件，可按exact SHA复跑。全候选统计的受控部分不能只凭公开正文复现，二者分母分别记录，不混写覆盖率。

**训练数据入口是 [sft/README.md](sft/README.md)。** `sft/common16k.jsonl.gz` 与 `sft/common32k_long_only.jsonl.gz` 互斥，后者只含 (16K,32K]，不重复短样本。完整历史前缀、历史助手、用户和工具结果的 label 均为 `-100`；只监督当前 completion，含正常终止标记。监督 spans 可精确还原 labels。两套官方 tokenizer 分别执行并逐行比较 token 和 mask，不作截断。

本轮300条动作一审有215条局部通过，未达到原方案建议95%门槛；未审记录未整体转银标。AI 审阅不等于人工 gold，也不批准整个技能的业务质量。已恢复可验证的路线决策与真实终态候选，难以核实者保留 needs_context。路线直写36条含546个子决策，最终63/65产物含1292个侧证决策；337条exec目标保留为原命令，不盲目转换为正确决策。详见 [LABEL_COMPLETENESS.json](LABEL_COMPLETENESS.json)。现有来源图只有1个连通分量，不能把相邻前缀随机拆成独立验证集。本包不代表已经具备全量训练与效果比较的准入条件。

93条最终银标目前含83条工具动作和10条收尾；直接路线写入仅1个父样本、16个reuse子决定，new/defer/no_value尚无准入直接正例。累计32K一遍实际处理1,620,754 tokens，仅18,205 tokens参与loss（约1.12%）；masked历史仍有计算成本。详见 [sft统计](reports/sft_statistics.json)。应先补关键路线分支与收尾审阅，不能用候选规模或重复样本凑满训练量。

该300条是分层、有意覆盖特定子集的局部AI抽审，215/300不能外推为总体正确率，也不能替代人工校准。支持材料本地文字提取成功为4750条，本次可公开正文为 {c.get('public:support',0)} / {c.get('rows:support',0)}；其余按hold清单受控保留。

## 文件用途

- `data/`：可公开的完整动作/收尾候选，包含拒绝和未审状态，供继续整理；不要直接全量喂给 SFT。
- `sft/`：通过公开、局部银标、结构、协议、双模型 mask 与长度门的最终子集。
- `compiled/`：全部公开候选中编译通过的数组、长度、ID 清单及失败原因；包括不应训练的候选和超长记录。
- `audit/`、`admission.jsonl.gz`：全7117母表的最小准入/隔离清单和逐条 AI 理由；子 decision 不额外扩成独立样本。
- `support/`：可公开的完整记录子集，包括原生历史（含失败）、源会话、附件文字、retained 技能内容、路线侧证和支持清单，全部 evidence_only。支持提取4750条是本地记录总数，不是独立SFT样本或全部公开正文数。
- `support/archive_opaque_inventory.jsonl.gz`：原归档654948别名/58288对象的完整哈希与范围索引，隐去个人文件名/宿主路径；不表示全部原对象字节已经公开。
- `reports/`、[AUDIT_METHOD.md](AUDIT_METHOD.md)：实际恢复、静态检查、抽审、清理、覆盖和局限。未公开正文有明确原因清单，原件仍在本地受控保留。
- `tokenizer_assets/`：两模型锁定 revision 的官方分词器和原许可文件，不含权重。`scripts/` 是离线数据工具，不是 Agent 循环或训练执行器。

## CPU 复核

在本目录执行（输出目录须尚不存在）。审计依赖见 `requirements-audit.txt`，其中不安装 torch。观察到的 Windows CPU 包版本不是 Spark ARM64 训练锁；继续使用 NVIDIA 训练环境原有 torch，未来训练环境兼容性仍需另验。

```sh
python scripts/wrd_training_preflight/token_compile.py --input data/candidates.actions.jsonl.gz --input data/candidates.labels.jsonl.gz --assets tokenizer_assets --plan plan_snapshot/TRAINING_CONFIG.json --output replay_token_masks --workers 2
python scripts/wrd_training_preflight/finalize.py --public . --compiled replay_token_masks --output replay_admission
```

复跑公开数据可核验 token/mask、覆盖和技术准入。重新从原始会话/CAS恢复标签或提取附件，还需要原受控 bundle；公开清理版本不能替代被隔离的原文。`labels.py` 可用 `--legacy-toolkit scripts/wrd_training` 指向附带只读 helper。

算力结果目前仅有离线整理 wall time；未测 Spark 训练速度、峰值内存、耗电或每个合格技能总成本。质量及 CPQS 仍按既定方案在独立新来源上评价，不能用本轮候选量、通过率或 tokenizer 速度代替。
'''
    (dest/'README.md').write_text(guide,encoding='utf-8')
    prohibited=('privacy_private_mapping','privacy_hmac_salt','local_restricted','local_clean_inputs','unapproved_local_only')
    files=[]
    for p in sorted(dest.rglob('*')):
        if not p.is_file():continue
        rel=p.relative_to(dest).as_posix()
        if any(x in rel for x in prohibited):raise ValueError('restricted path in release')
        if p.suffix.lower() in {'.safetensors','.pt','.pth','.bin'}:raise ValueError('unexpected weight or binary file')
        if rel=='MANIFEST.json':continue
        files.append({'path':rel,'bytes':p.stat().st_size,'sha256':sha(p)})
    save(dest/'MANIFEST.json',{'schema_version':'wrd-training-preflight-release-v1','files':files,'file_count':len(files),'total_bytes':sum(x['bytes'] for x in files),'training_started':False,'contains_private_salt_or_mapping':False})
    print(json.dumps({'release':str(dest),'files':len(files),'bytes':sum(x['bytes'] for x in files),'elapsed_seconds':round(time.monotonic()-started,3)}),flush=True)


if __name__=='__main__':main()
