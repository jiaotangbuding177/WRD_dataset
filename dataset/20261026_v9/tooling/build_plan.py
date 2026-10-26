"""Bind the training plan and readiness to actual exported v9 sequences."""
from collections import Counter,defaultdict
from datetime import datetime,timezone
import gzip
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'output/20261026_wrd_dataset_v9'


def js(v):return json.dumps(v,ensure_ascii=False,separators=(',',':'))
def rows(p):
    with gzip.open(p,'rt',encoding='utf-8')as f:
        for line in f:
            if line.strip():yield json.loads(line)
def digest(p):
    h=hashlib.sha256()
    with Path(p).open('rb')as f:
        for b in iter(lambda:f.read(1048576),b''):h.update(b)
    return h.hexdigest()
def save(n,v):(OUT/n).write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


def main():
    compile_report=json.loads((OUT/'COMPILATION_REPORT.json').read_text(encoding='utf-8'))
    qa=json.loads((OUT/'COMPILED_QA.json').read_text(encoding='utf-8'))
    assert qa['status']=='PASS'and not qa['failures']
    expected={(str((OUT/r['path']).resolve()),r['bytes'],r['sha256'])for r in compile_report['split']['files']}
    observed={(str(Path(r['path']).resolve()),r['bytes'],r['sha256'])for r in qa['verified_files']}
    assert expected==observed,'stale_QA_file_set_or_bytes'
    current_pins={(str(Path(r['path']).resolve()),r['bytes'],r['sha256'])for r in compile_report['immutable_input_pins']if '/coordination/'in r['path'].replace('\\','/')}
    qa_pins={(str(Path(r['path']).resolve()),r['bytes'],r['sha256'])for r in qa['actual_coordination_input_pins_verified']}
    assert current_pins==qa_pins,'stale_QA_source_pins'
    for row in compile_report['immutable_input_pins']:assert Path(row['path']).stat().st_size==row['bytes']and digest(row['path'])==row['sha256']
    for key in ['official_template_sha256','causal_template_sha256','asset_sha256']:
        assert qa['tokenizer_and_template_proof'][key]==compile_report['tokenizer_and_template_proof'][key]
    allstats=Counter();bybank=defaultdict(Counter);components=Counter();owners=set();file_rows=[];source_split={}
    stage=defaultdict(Counter);entry_counts=Counter();categories=Counter()
    for item in compile_report['split']['files']:
        p=OUT/item['path'];assert digest(p)==item['sha256']
        count=0
        for r in rows(p):
            count+=1;bank=r['bank'];split=r['split'];scope=split+'_'
            allstats[scope+'sequences']+=1;allstats[scope+'targets']+=len(r['targets'])
            allstats[scope+'input_tokens']+=r['total_tokens'];allstats[scope+'supervised_tokens']+=r['supervised_tokens']
            bybank[bank][scope+'sequences']+=1;bybank[bank][scope+'targets']+=len(r['targets']);bybank[bank][scope+'supervised_tokens']+=r['supervised_tokens']
            bybank[bank][scope+'input_tokens']+=r['total_tokens']
            bybank[bank]['le16k_sequences'if r['total_tokens']<=16384 else 'gt16k_le32k_sequences']+=1
            for lo,hi,cl,w in r['supervision_spans']:
                components[cl]+=hi-lo;allstats[scope+'weighted_loss_token_mass']+=(hi-lo)*w
            owners.update(t['id']for t in r['targets'])
            if bank=='coordination':
                origin=r['annotation_provenance'];entry_counts[str(origin)+'_sequences']+=1;entry_counts[str(origin)+'_targets']+=len(r['targets'])
                if r.get('coordination_original_record',{}).get('category'):categories[r['coordination_original_record']['category']]+=1
            for s in r.get('source_ids',[]):
                assert s not in source_split or source_split[s]==split
                source_split[s]=split
        file_rows.append({**item,'sequences':count})
    assert qa['counts']['verified_sequences']==sum(allstats[s+'_sequences']for s in ['train','dev','test'])
    for bank,v in bybank.items():
        assert qa['by_bank'][bank]['rows']==sum(v[s+'_sequences']for s in ['train','dev','test'])
        assert qa['by_bank'][bank]['supervised_tokens']==sum(v[s+'_supervised_tokens']for s in ['train','dev','test'])
        assert qa['by_bank'][bank]['input_tokens']==sum(v[s+'_input_tokens']for s in ['train','dev','test'])
    for r in rows(OUT/'processed/targets.processing.jsonl.gz'):
        if r['id']in owners:stage[r['stage']or'unknown'][r['supervision_tier']]+=1
    stats={'schema_version':'wrd-v9-actual-final-data-statistics','all_splits':dict(allstats),'by_bank':{k:dict(v)for k,v in bybank.items()},
        'native_active_targets_by_historical_stage':{k:dict(v)for k,v in stage.items()},'annotation_origins':dict(entry_counts),'active_entrypoint_categories':dict(categories),
        'supervised_component_tokens':dict(components),'unique_source_ids_in_active_sequences':len(source_split),'files':file_rows,
        'outcome_backed_skill_supervised_targets':0,'evidence_review_semantic_supervised_targets':0,'original_reasoning_supervised_tokens':components.get('R',0),
        'full_autonomous_real_native_demonstrations':0,'training_started':False}
    final_outcomes=json.loads((OUT/'outcomes/recomputed_scope_overlay/SUMMARY.json').read_text(encoding='utf-8'))
    stats['effective_outcome_and_source_summary']=final_outcomes
    coordination_summary=json.loads((OUT/'coordination/SUMMARY.json').read_text(encoding='utf-8'))
    stats['real_poststage_coordination']={'processed_state_decisions':coordination_summary['program_annotated_real_state_decisions'],
        'source_closed_admitted':coordination_summary['admitted_source_closed_real_state_decisions'],
        'original_route_trace_views':coordination_summary['original_route_trace_views'],'is_distinct_from_source_free_rule_traces':True}
    # This status is intentionally independent of a file/array QA PASS.
    assert not any(t.get('outcome_skill_silver',0)or t.get('evidence_review_silver',0) for t in stage.values())
    save('FINAL_DATA_STATISTICS.json',stats)
    config=json.loads((ROOT/'output/20261025_wrd_training_dataset/git_release/plans/20261025_14b_spark/TRAINING_CONFIG.json').read_text(encoding='utf-8'))
    plan={
        'schema_version':'wrd-v9-outcome-conditioned-training-plan','design_revision':'5.0.35','change_id':'ALG-20261026-08',
        'status':'AUXILIARY_DATA_COMPILED_FULL_WRD_MAIN_SFT_BLOCKED','execution_authorized':False,'is_launch_config':False,'training_started':False,
        'models':config['models'],'hardware_report':config['hardware_report'],'environment_candidate':config['environment_candidate'],
        'shared_lora_candidate':config['shared_lora_candidate'],'shared_sft_candidate':config['shared_sft_candidate'],
        'actual_data_statistics':'FINAL_DATA_STATISTICS.json','actual_data_manifest':'TRAINING_MANIFEST.json',
        'phase_policy':[
            {'phase':'offline_data','status':'completed','outputs':['recovery','outcomes','coordination','processed','sft'],'new_teacher_actor_calls':0},
            {'phase':'auxiliary_protocol_and_coordination','status':'data_compiled_not_recommended_as_standalone_full_goal_training','banks':['native_process','coordination'],
             'native_read_only_weight':0.1,'clean_entrypoint_annotation_weight':0.1,'source_free_boundary_and_trace_weight':0.05,'maximum_source_parent_exposures':1},
            {'phase':'outcome_backed_native_process_SFT','status':'blocked','reason':'No skill write/revision or semantic review targets satisfy both source/label ancestry isolation and outcome-evidence requirements.',
             'requires':['clean_source_actual_native_make_and_revision_actions','matched_skill_tree_and_real_trial_observations','evidence_based_review_with_closed_label_ancestry','all_required_phase_and_branch_coverage']},
            {'phase':'student_closed_loop_validation','status':'not_started_not_authorized','runtime':'same_fixed_native_OpenClaw','never_reset_to_gold_history':True}
        ],
        'loss_contract':{'implementation':'tooling/dataset_loader.py','labels':'input_ids in explicit approved spans only; all other tokens -100',
            'loss_weights':'span fourth field, causal shift once; sum(weight*CE)/count(active_labels), not division by sum(weights)',
            'old_wrong_or_unknown_steps':'preserved context with zero positive loss','single_file_outcome_credit':'does not approve adjacent explanation, R or other actions',
            'original_readable_R':'preserved in recovered mother and same-ID overlay; no admitted positive R in this final SFT subset',
            'annotated_rule_rationale':'not original teacher CoT or empirical tool/trial feedback','metadata_never_model_input':True},
        'inference_contract':{'input':'complete conversation, real materials, current library and actual budget/state','runtime':'native OpenClaw tool discovery/read/tools and persistent session',
            'desired_output':'actual tool actions and qualified versioned skill package, or justified stop/defer','coordination_JSON_is_auxiliary_planning_not_a_new_agent_loop':True,
            'current_data_do_not_prove_complete_autonomous_execution':True,'future_native_deployment_integration_completed':False},
        'evaluation':{'primary':['full delivery TSR','independent five-dimensional Q','total cost per independently qualified skill'],
            'secondary':['correct defer/reject/stop','version-specific reuse and repair','external model calls','human/teacher fallback','worst phase and branch'],
            'compare':['base14B','SFT14B','base8B','SFT8B','original_teacher_under_same_clean_conditions'],
            'current_dev_test':'source-group static auxiliary holdouts, not native closed-loop task benchmarks','original226_and_new_H':'isolated from training, label creation and model/threshold selection'},
        'cost_formula':'(new data/annotation + training + validation + all inference/tools/external-model/retries/human/teacher fallback in the same accounting period) / independently qualified skills in that period; amortize each one-time cost once; historic sunk distillation separate',
        'no_throughput_or_effect_claim_without_Spark_measurement':True,
        'historical_optional_reference_not_automatically_joined':{'path_in_existing_git':'reasoning/20261026_lineage_v6/TRAINING_MANIFEST.json',
            'historical_main_responses':106,'historical_readable_R_responses':30,'historical_R_tokens':121511,
            'historical_execution_conditions_and_quality_standard_preserved':True,'not_counted_as_current_native_outcome_main':True,
            'requires_new_H_and_new_outcome_criteria_revalidation_before_any_new_profile_merge':True},
    }
    sft=plan['shared_sft_candidate'];sft.update(loss_type='weighted_masked_causal_NLL',completion_only_loss=False,assistant_only_loss=False,
        loss_scope='explicit approved assistant span ownership, including multi-turn synthetic rule trace targets; all original history/unknown/error/feedback masked',
        initial_passes=1,maximum_passes_before_new_decision=1,packing=False,truncation_allowed=False)
    plan['shared_sft_candidate']['enable_thinking']=False
    plan['causal_template_policy']={'variant_sha256':compile_report['tokenizer_and_template_proof']['causal_template_sha256'],
        'not_unmodified_official_template':True,'explicit_recorded_R_preserved':'yes_in_evidence_mother_not_positive_main_loss',
        'same_variant_required_for_future_inference':True,'future_api_integration_not_yet_done':True}
    save('TRAINING_PLAN.json',plan)
    manifest={'schema_version':'wrd-v9-training-manifest','created_at_utc':datetime.now(timezone.utc).isoformat(),
        'auxiliary_arrays_technically_ready':True,'full_goal_main_training_ready':False,'training_execution_authorized':False,'training_started':False,
        'original226_and_new_H_isolation_preserved':True,'actual_files_with_messages_input_ids_masks':file_rows,
        'profiles':{'wrd_outcome_main':{'admitted_targets':0,'ready':False},'native_process':{'meaning':'read-only tool protocol auxiliary, not skill quality',**dict(bybank['native_process'])},
                    'coordination':{'meaning':'clean input entrypoint annotation plus source-free hypothetical rule supervision, not real successful autonomous trajectories',**dict(bybank['coordination'])}},
        'source_group_manifest':'SOURCE_GROUP_SPLIT.json','QA':'COMPILED_QA.json','statistics':'FINAL_DATA_STATISTICS.json','plan':'TRAINING_PLAN.json',
        'raw_evidence_not_default_training_inputs':['recovery','outcomes','processed','processing_history'],
        'explicit_allowlist_required_not_glob_all_jsonl':True,'controlled_data_delivered_in_authenticated_archive':True,
        'all_model_mask_fields_implemented_by':'tooling/dataset_loader.py','old_v6_arrays_unchanged_not_automatically_promoted':True}
    save('TRAINING_MANIFEST.json',manifest)
    # A concrete, non-executing gap repair specification; it does not invent
    # successful trajectories or use protected outcomes as labels.
    clean_by_category=defaultdict(list)
    for row in rows(OUT/'coordination/entrypoint_controller.native_paths.source_closed.jsonl.gz'):
        sid=row['source_id']
        if source_split.get(sid)=='train':clean_by_category[row['category']].append(row)
    repair=[]
    for category,values in sorted(clean_by_category.items()):
        ordered=sorted(values,key=lambda r:hashlib.sha256(('v9-clean-seed:'+r['source_id']).encode()).hexdigest())
        first=ordered[0]
        repair.append({'category':category,'seed_source_id':first['source_id'],'source_group_id':first['source_group_id'],
            'native_conversation_path':'/workspace/inputs/conversations/'+first['source_id']+'.json',
            'remaining_training_sources_in_category':[r['source_id']for r in ordered[1:]],
            'category_is_not_proof_of_same_workflow_or_valid_independent_trial':True})
    recollection={'schema_version':'wrd-v9-bounded-clean-gap-repair-plan','status':'PLAN_ONLY_NO_NEW_EXECUTION_AUTHORIZATION',
        'execution_authorized':False,'training_started':False,'new_teacher_calls_started':0,
        'source_pool':'replay_inputs plus REPLAY_INPUT_MANIFEST.json','train_only_seeds':repair,
        'exclude_all_static_dev_test_original226_new_H_and_their_derived_skill_resources':True,
        'before_trial':'native agent must verify real same-workflow task and required real inputs; category match alone is insufficient',
        'runtime':'existing fixed native OpenClaw; same image/model/tools/budgets; no replacement loop',
        'proposed_stage_upper_bounds':{'screen':12,'initial_make':12,'prepare':12,'initial_actor_both_arms':24,'initial_review':12,'one_optional_revision_make':12,'revision_actor_both_arms':24,'revision_review':12},
        'proposed_maximum_new_stage_sessions':120,'not_a_guarantee_of_12_skills_or_sufficient_final_training_scale':True,
        'capture':'full original same-ID request/system/tools/response/readable reasoning and native tool results; progress and encrypted fields separately typed',
        'sampling_policy':'stop on no_value/missing real input; reuse only strictly identical clean already-paid evidence; never refill slots for volume',
        'purpose':'repair missing clean empirical process supervision, then assess source-scale learning curve; not a new effect claim'}
    save('CLEAN_RECOLLECTION_PLAN.json',recollection)
    raw=json.loads((OUT/'recovery/REPORT.json').read_text(encoding='utf-8'));o=final_outcomes
    assert raw['counts']['episodes']==1843 and raw['counts']['assistant_responses']==34239
    assert o['version_trial_review_edges']==271 and o['positive_silver_version_trial_edges']==229 and o['positive_outcome_loss_candidates_before_source_quality_context']==145 and o['evidence_review_silver_writes_before_source_filter']==87
    native_sequences=sum(bybank['native_process'][s+'_sequences']for s in ['train','dev','test'])
    native_targets=sum(bybank['native_process'][s+'_targets']for s in ['train','dev','test'])
    native_supervised=sum(bybank['native_process'][s+'_supervised_tokens']for s in ['train','dev','test'])
    assert qa['by_bank']['native_process']['rows']==native_sequences and qa['counts']['native_owned_targets_checked']==native_targets and qa['by_bank']['native_process']['supervised_tokens']==native_supervised
    assert qa['counts']['native_positive_protocol_targets_without_observed_tool_failure']==native_targets
    assert compile_report['coordination']['counts']['input_rows']==1041 and compile_report['coordination']['counts']['held_gt32k_no_truncation']==33
    assert coordination_summary['program_annotated_real_state_decisions']==3771 and coordination_summary['admitted_source_closed_real_state_decisions']==0
    text=f'''# WRD大规模数据处理与对应训练计划v9

**实际处理、正文与数组已经交付；完整WRD主训练尚未放行。** 本轮不是候选清单：原native正文、工具操作和反馈、同ID可读推理、版本/试跑/评审图、逐目标来源与监督处理、共同token数组、loss spans及分组切分均已实际生成。它们不能被合称为“已经足量的自主沉淀训练集”。

## 实际数量

- 原native恢复：{raw['counts']['episodes']}会话、{raw['counts']['assistant_responses']}助手位置；同responseId原字段恢复56。原system完整6，重建接口与原捕获分开。
- 原API请求/响应：1536组，257含可读reasoning字段；历史执行条件与native不混称，加密思考不伪造解密。
- 全121路线图：326制作版本attempt/308内容树；271版本-试跑-评审关联，229有匹配消费及case通过的历史银标。145精确文件写入和87证据审阅候选已关联结果，但在来源及标签祖先隔离后，当前可正监督制作/修订/语义评审仍为0。后续恢复overlay纠正保护/未知归类，不将保护数据转正。
- 实际train：{allstats['train_sequences']}序列、{allstats['train_targets']}批准assistant目标、{allstats['train_input_tokens']}输入tokens、{allstats['train_supervised_tokens']}未加权监督tokens；dev {allstats['dev_sequences']}、test {allstats['test_sequences']}序列。它们是辅助资料，不是同数量独立完整WRD任务。
- 原生只读辅助：{native_sequences}序列/{native_targets}动作/{native_supervised}监督tokens，历史阶段虽跨筛选、制作、选题、Actor、评审，但正loss只对应无已记录工具错误的read/ls格式，不授予技能正确性。10个未获独立认可的报错探测已撤销正loss，全部原上下文保留，见TARGET_QUALITY_ERRATA.json。
- 新协调层：867原干净会话输入、162纯规则边界、12完整假设控制trace/82决策；33个入口超过32K保留但不截断放入SFT。完整trace是明确假设状态，不伪造工具返回/试跑成败，不算真实自主任务。
- 原真实阶段状态也已实际构建3771条协调决策正文、234个路线trace视图；来源/精确时点准入0，全部保全在隔离证据，不拿新增的12条假设序列冒充这部分真实数据已经可训。
- 原思考/失败/修订完整保留；当前正loss中的原R为{components.get('R',0)} tokens。不得将保全R的数量充作已通过来源与质量审核的R监督。

旧v6的106响应与30原R（121511 R tokens）保持原历史清单和不同执行条件，并未删除；本轮更严格的原生版本-试跑标准及新H尚未使其自动成为全目标主监督，不能与本轮新原生覆盖混加。

逐银行/阶段/来源及16K/32K实数见[统计](FINAL_DATA_STATISTICS.json)，实际文件与SHA见[训练清单](TRAINING_MANIFEST.json)。独立QA按两个真实CPU tokenizer逐序列重编码，重建-100标签、权重、助手边界与分组隔离；这不是领域质量金标。

## 为什么动作必须对应结果，以及如何使用负结果

文件写入须连接具体完整包版本；版本须连接Actor真实读取/试跑；试跑与两臂完整成本及原case评审相连。版本通过只提供观察性银标，不证明每一步因果贡献。相邻思考、宣称和其它动作不能因一个正确文件一并拿正loss；成本减负与交付质量分开。负面结果可以监督有证据的诊断和返修决策，但其反馈标签本身也必须无保护祖先。错误/未知历史保留为上下文，不全丢，也不全学。

本轮发现部分原路线卡和机械投影确实源于读取原226预览后的状态。后来的学习source列表干净，不能消除上游已见保护内容的影响。这解释了为何原始记录很多、有成功技能、也不能在保持原评测边界时直接转成大量主正例。报告没有把这说成原过程无价值。

## 对应14B／8B的训练安排

沿用锁定的Qwen3-14B主、Qwen3-8B对照与同tokenizer资产；Spark采用候选BF16 LoRA r32/alpha64、microbatch1/accum16、lr1e-4、checkpointing，16K后仅处理互斥32K长分片。ARM容器/内核与实际吞吐尚未在Spark验证，不据内存算术声称跑通。当前不建议只用这些辅助标签花GPU完成“正式WRD训练”。

所有训练loss按显式span实现：系统、用户、工具反馈、错误和未知动作-100；只读辅助0.1，入口程序标注0.1，纯规则/完整假设trace0.05。分母用活跃标签数，不能用权重和把低权重抵消。新标注不是教师CoT，协调JSON是规划辅助，也不是新Agent执行器。

完整目标下一阶段缺的是**干净来源下实际原生制作、试跑、反馈修订的闭环监督**，而非更多文件复制或同模板行数。必须先补这些主证据，再做领域SFT；不能因封包/数组QA通过就启动。后续若获授权采集，应只对具体缺口有界补采，复用已提供的867干净会话与字节核验资源，不能复用保护试跑来打标签。当前辅助数据不保证正式训练后的收益。

[具体补缺草案](CLEAN_RECOLLECTION_PLAN.json)已经从现有train来源群选每类一个起点，给出原生输入路径及剩余匹配池；先核真实同工作流/真实材料，再试跑。草案最多120原生阶段会话（12筛选、12初制、12选题、24双臂试跑、12评审，最多另一次12修订+24试跑+12评审），不是120模型请求，也不保证12技能或最终足量。仅计划，未执行；静态dev/test及原226/新H均不投制作。

真正验收需让学生从新完整会话出发，在同一原生OpenClaw循环与真实工具反馈上自己继续执行；比较基座、14B、8B和同条件教师的完整TSR、独立五维Q、正确停止、跨案例复用及每个合格技能总成本。不能用gold-history下一步准确率或当前控制标签dev/test替代。原226与新H不进训练、超参或门槛选择。

每个合格技能总成本计入本次数据整理/标注、训练/验证与同周期全部推理、工具、外模、重试、人工和教师回退；历史沉淀已付另列，一次性成本只摊一次。没有模型闭环结果，不给保证降本比例。

## 交付结构与读取

数据正文及原始证据放认证加密实包，沿用本地已有密钥；密钥不进Git。公开层提供报告、清单、QA和工具脚本；这不是只交哈希索引，解包后实际`sft/`含messages、input_ids和监督span，并由dataset_loader重建labels/weights。训练只读取TRAINING_MANIFEST的明确文件，不glob恢复母本/隔离资料。

867输入会话及112真实附件别名已按原stages挂载合同实化。附件93个不同字节对象已在原Git dist包逐对象核验，按EXISTING_RESOURCE_REUSE引用，不重复上传相同417951031字节；旧完整包的12分片SHA也已核。缺件、合成或未核历史材料没有伪造。

本轮0训练、0权重加载、0新Teacher/Actor/业务试跑；原生工具/循环、生产文件与正在执行的消融未由本轮更改。双稿5.0.35/ALG-20261026-08，消融仍绑定其原冻结5.0.33合同。
'''
    (OUT/'TRAINING_PLAN.md').write_text(text,encoding='utf-8')
    print(js({'stats':dict(allstats),'active_banks':list(bybank),'wrd_main_ready':False}))


if __name__=='__main__':main()
