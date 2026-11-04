"""Independent final current-main metadata recount and readiness review.

Reads every active row, positive target/spans and provenance metadata. No
admit/compiler/verifier import, HF tokenization, source program, Agent or model.
"""
from pathlib import Path
from collections import Counter,defaultdict
import gzip,hashlib,json

ROOT=Path('D:/skillloop');MAIN=ROOT/'output/20261027_wrd_main_v10'
OUT=ROOT/'output/20261031_wrd_curation10/final_quality_review'
EXPECTED='9aace2dc6b39d0dde3bafbf9f7f3d6763e485609017dd70a5c40c17a2c30277e'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def pin(p):return {'path':str(p),'bytes':p.stat().st_size,'sha256':sha(p)}
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def rows(p):return [json.loads(s) for s in gzip.open(p,'rt',encoding='utf-8-sig') if s.strip()]
def save(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((json.dumps(x,ensure_ascii=False,indent=2)+'\n').encode())
def main():
 man=MAIN/'TRAINING_MANIFEST.json';assert sha(man)==EXPECTED
 m=load(man);allrows=[];shards=[]
 for ref in m['actual_train_files']:
  p=MAIN/ref['path'];assert p.stat().st_size==ref['bytes'] and sha(p)==ref['sha256']
  allrows.extend(rows(p));shards.append(pin(p))
 dsu={}
 def find(x):
  dsu.setdefault(x,x)
  if dsu[x]!=x:dsu[x]=find(dsu[x])
  return dsu[x]
 def join(a,b):dsu[find(b)]=find(a)
 for r in allrows:
  key='row:'+r['id'];join(key,'group:'+r['source_group_id'])
  for sid in r['source_ids']:join(key,'source:'+sid)
 def summary(rs):
  positive=Counter();sourceids=set();rowgroups=set();globalgroups=set();rawtargets=0;positivetargets=0;sequences=0;seq=0;short=0;long=0;weighted=0
  for r in rs:
   sequences+=1;seq+=len(r['input_ids']);assert len(r['input_ids'])==r['total_tokens']
   short+=r['total_tokens']<=16384;long+=16384<r['total_tokens']<=32768
   rawtargets+=len(r['targets'])
   sourceids.update(r['source_ids']);rowgroups.add(r['source_group_id']);globalgroups.add(find('row:'+r['id']))
   flat=[]
   for t in r['targets']:
    if t['owned_supervision_spans']:positivetargets+=1
    assert t['supervised_tokens']==sum(b-a for a,b,_,_ in t['owned_supervision_spans'])
    flat.extend(t['owned_supervision_spans'])
   assert flat==r['supervision_spans']
   c=Counter()
   for a,b,component,w in r['supervision_spans']:
    assert 0<=a<b<=r['total_tokens'] and 0<w<=1
    c[component]+=b-a;weighted+=(b-a)*w
   assert dict(c)==r['supervised_tokens_by_component'] and sum(c.values())==r['supervised_tokens']
   positive.update(c)
  return {'sequences':sequences,'positive_targets':positivetargets,'rendered_assistant_metadata_entries':rawtargets,
   'context_only_assistant_metadata_entries':rawtargets-positivetargets,'source_ids':len(sourceids),
   'declared_row_group_ids':len(rowgroups),'global_connected_components':len(globalgroups),
   'sequence_tokens':seq,'positive_tokens':sum(positive.values()),'components':dict(positive),
   'le16k':short,'gt16k_le32k':long,'max_tokens':max((r['total_tokens'] for r in rs),default=0),
   'weighted_positive_token_mass':round(weighted,8),'source_id_list':sorted(sourceids)}
 contract=[r for r in allrows if r['bank']=='source_contract_main'];process=[r for r in allrows if r['bank']!='source_contract_main']
 totals=summary(allrows);ct=summary(contract);pr=summary(process)
 assert totals['sequences']==623 and totals['positive_targets']==623
 assert totals['positive_tokens']==227233 and totals['sequence_tokens']==3853977
 assert totals['source_ids']==m['distinct_source_ids'] and totals['global_connected_components']==m['source_connected_components_across_banks']
 assert ct['positive_targets']==418 and pr['positive_targets']==205
 stages=defaultdict(list)
 for r in allrows:
  stage=r['stage'];coarse=stage[:1] if stage[:1] in 'ABCD' else 'historical_workflow_R'
  stages[coarse].append(r)
 stage_stats={k:summary(v) for k,v in stages.items()}
 combos=defaultdict(list)
 for r in process:
  positive={k for k,v in r['supervised_tokens_by_component'].items() if v and k!='F'}
  combos['+'.join(sorted(positive))].append(r)
 nativeR_banks={'native_wrd_main','native_C_review_partial_02','native_CV_B_training_01','native_HTML_B_training_01','native_recovered_read_process10'}
 def Rkind(r):
  b=r['bank']
  if b in nativeR_banks:return 'recorded_native_compatible_R'
  if b=='historical_semantic_R_main':return 'recorded_historical_SSE_R'
  if b=='historical_test_oracle_repair_02':return 'recorded_cumulative_R_excerpt_new_state'
  if b=='recontextualized_compat_R_process10':return 'recorded_compatible_R_excerpt_new_state'
  if b=='source_only_controller_batch24':return 'new_authored_source_only_controller_R'
  return 'new_authored_other_R'
 def Akind(r):
  b=r['bank']
  if b=='real_state_repair_main':return 'revalidated_original_A_on_new_state'
  if b=='recontextualized_compat_R_process10':return 'recorded_compatible_A_recontextualized'
  if b in {'native_C_execution_local_02','native_CV_B_training_01','native_HTML_B_training_01','native_recovered_read_process10'}:return 'recorded_native_A'
  return 'offline_action_projection_A_body_authorship_varies'
 originsR=defaultdict(list);originsA=defaultdict(list)
 for r in process:
  if r['supervised_tokens_by_component'].get('R',0):originsR[Rkind(r)].append(r)
  if r['supervised_tokens_by_component'].get('A',0):originsA[Akind(r)].append(r)
 Rstats={k:{**summary(v),'R_positive_tokens':sum(r['supervised_tokens_by_component'].get('R',0) for r in v)} for k,v in originsR.items()}
 Astats={k:{**summary(v),'A_positive_tokens':sum(r['supervised_tokens_by_component'].get('A',0) for r in v)} for k,v in originsA.items()}
 native_paired=[r for r in process if Rkind(r)=='recorded_native_compatible_R' and r['supervised_tokens_by_component'].get('R',0)>0 and r['supervised_tokens_by_component'].get('A',0)>0]
 recontext_paired=[r for r in process if r['bank']=='recontextualized_compat_R_process10' and r['supervised_tokens_by_component'].get('R',0)>0 and r['supervised_tokens_by_component'].get('A',0)>0]
 Ronly=summary(combos['R']);Ronly['R_positive_tokens']=Ronly['components'].get('R',0)
 original_R=sum(v['R_positive_tokens'] for k,v in Rstats.items() if k.startswith('recorded_'))
 new_R=sum(v['R_positive_tokens'] for k,v in Rstats.items() if k.startswith('new_'))
 assert original_R+new_R==totals['components']['R']
 nativepair=summary(native_paired);recontextpair=summary(recontext_paired)
 bybank={b:summary([r for r in allrows if r['bank']==b]) for b in sorted({r['bank'] for r in allrows})}
 # Same exact tokenizer assets imply the same deterministic declared-template
 # input length. Actual dual HF audits are separate pinned bank/root receipts;
 # do not turn this metadata review into a new model-execution claim.
 assets=ROOT/'output/20261025_wrd_training_preflight/tokenizer_assets';asset_names=['tokenizer_config.json','tokenizer.json','vocab.json','merges.txt','generation_config.json']
 hashes={n:{f:sha(assets/n/f) for f in asset_names} for n in ['primary_14b','control_8b']}
 assert hashes['primary_14b']==hashes['control_8b']
 proof_counts=Counter(r['tokenizer_pair_proof'] for r in allrows)
 parents=load(ROOT/'output/20261031_wrd_curation10/parent_inputs/PARENT_INPUT_INDEX.json')
 assert parents['parent_input_pack_count']==8 and parents['missing_consumer_slots']==3 and parents['parent_bundle_connected_component_count']==5
 report={'schema':'wrd10-independent-final-main-quality-metadata-v1','status':'INDEPENDENT_RECOUNT_AND_READINESS_SCOPE_REVIEW_NOT_NEW_MODEL_EFFECT_EVIDENCE',
  'manifest_pin':pin(man),'all_active_shards_verified_by_bytes_SHA':shards,
  'all':totals,'contract':ct,'process':pr,'stage_coarse':stage_stats,
  'process_component_combinations':{k:summary(v) for k,v in sorted(combos.items())},
  'R_provenance_groups':Rstats,'A_provenance_groups':Astats,
  'original_R_including_recontextualized':original_R,'new_authored_R':new_R,
  'R_only':Ronly,'R_only_share_of_all_recorded_original_R':Ronly['R_positive_tokens']/original_R,
  'recorded_native_R_with_current_A':nativepair,'recontextualized_recorded_R_with_A':recontextpair,
  'by_bank':bybank,'tokenizer_asset_hashes':hashes,'compile_row_tokenizer_proof_counts':dict(proof_counts),
  'lengths_are_for_declared_current_SFT_views_not_full53_dynamic_native_rollouts':True,
  'full_native_A_D_demos':m['single_native_session_autonomous_A_through_D_demonstrations'],
  'qualified_retained_skill_chains':m['positive_qualified_retained_skill_chains'],
  'full_pipeline_ready':m['full_WRD_main_training_ready'],'full_pipeline_entrypoint':m['default_full_pipeline_training_entrypoint'],
  'parent_input_index_pin':pin(ROOT/'output/20261031_wrd_curation10/parent_inputs/PARENT_INPUT_INDEX.json'),
  'parent_input_summary':{k:parents[k] for k in ['parent_input_pack_count','distinct_consumer_inputs','consumer_bindings','missing_consumer_slots','parent_bundle_connected_component_count','actual_full_native_execution_ready']},
  'review_scope':'All623 actual rows, positive target metadata, span counts, declared source/group DSU, provenance labels and current length coverage. Does not re-judge every enterprise fact or repeat HF/program execution.',
  'new_program_or_native_or_HF_tokenization_executed':False,'weights_loaded':False,'training_started':False,'script_pin':pin(Path(__file__))}
 assert report['full_native_A_D_demos']==0 and report['qualified_retained_skill_chains']==0
 save(OUT/'METADATA.json',report)
 print(json.dumps({k:report[k] for k in ['original_R_including_recontextualized','new_authored_R']},ensure_ascii=False))
 print(json.dumps({'all':{k:v for k,v in totals.items() if not k.endswith('_list')},'process':{k:v for k,v in pr.items() if not k.endswith('_list')},
  'stage':{k:v['positive_targets'] for k,v in stage_stats.items()},'R_only':{k:v for k,v in Ronly.items() if not k.endswith('_list')},
  'native_paired':{k:v for k,v in nativepair.items() if not k.endswith('_list')},'recontext_paired':{k:v for k,v in recontextpair.items() if not k.endswith('_list')}},ensure_ascii=False))
 text=f'''# WRD10最终数据质量与充分性独立复核

结论：当前主集适合开展**有界组件SFT、来源组学习曲线与14B／8B对照研究**，尚不足以据此证明完整自主沉淀能力。以下为独立读取全部活动文件及正目标跨度的重数；不是复制manifest摘要，也不是对全部企业事实重新授信。入口SHA `{EXPECTED}`。

| 实际单位 | 独立重数 |
|---|---:|
| 序列／正目标／正tokens／序列tokens | {totals['sequences']}／{totals['positive_targets']}／{totals['positive_tokens']}／{totals['sequence_tokens']} |
| 契约辅助 | {ct['positive_targets']}目标，{ct['positive_tokens']}正tokens |
| 过程 | {pr['positive_targets']}目标，{pr['positive_tokens']}正tokens；{pr['source_ids']}来源ID／{pr['global_connected_components']}全局连接组 |
| 全集来源／全局连接组 | {totals['source_ids']}／{totals['global_connected_components']}，不是同量完整任务 |
| 字面阶段A／B／C／D＋历史workflow R | {stage_stats['A']['positive_targets']}／{stage_stats['B']['positive_targets']}／{stage_stats['C']['positive_targets']}／{stage_stats['D']['positive_targets']}＋{stage_stats['historical_workflow_R']['positive_targets']}；A含418辅助 |
| 共同16K／16—32K | {totals['le16k']}／{totals['gt16k_le32k']}，最长{totals['max_tokens']}；过程{pr['le16k']}／{pr['gt16k_le32k']} |

原记录R共{original_R}tokens：原生compatible {Rstats['recorded_native_compatible_R']['R_positive_tokens']}、历史SSE {Rstats['recorded_historical_SSE_R']['R_positive_tokens']}、累计摘录{Rstats['recorded_cumulative_R_excerpt_new_state']['R_positive_tokens']}、再情境API摘录{Rstats['recorded_compatible_R_excerpt_new_state']['R_positive_tokens']}；新作者R共{new_R}，绝不把再情境当新原生轨迹。R-only仍{Ronly['positive_targets']}视图／{Ronly['R_positive_tokens']}tokens，占全部原记录R的{Ronly['R_positive_tokens']/original_R:.2%}。原生原R与当前A配对{nativepair['positive_targets']}视图、{nativepair['source_ids']}来源ID／{nativepair['global_connected_components']}全局组；新增再情境R+A仅{recontextpair['positive_targets']}视图、{recontextpair['source_ids']}来源ID／{recontextpair['global_connected_components']}组，不按切片数夸经验。

动作分账：原生记录A {Astats['recorded_native_A']['A_positive_tokens']}、重验原A {Astats['revalidated_original_A_on_new_state']['A_positive_tokens']}、再情境记录A {Astats['recorded_compatible_A_recontextualized']['A_positive_tokens']}、其它离线投影A {Astats['offline_action_projection_A_body_authorship_varies']['A_positive_tokens']}；投影包含旧代码重投递和新修复，不能全部叫新写代码。{totals['rendered_assistant_metadata_entries']}个assistant元数据条目中只有623个正目标，其余为上下文。原错误、工具反馈和负跨度被保留；来源完整、进程成功或局部CPU通过不等于内容正确、独立Q或正loss。

这些数据可研究路线/需求辅助、下一步read/工具协议、资源构建、局部错误诊断—修订及保守HOLD。C仍11、D仅5（含新状态/局部收尾），完整原生A—D和合格KEEP仍0，不能证明学生会自主探索调度、修订增加真实效用，或14B优于8B。Q门槛未校准、Spark ARM64/GB10未验，当前窗口是声明SFT视图；full53动态上下文、输出余量、原生隔离/硬预算未通过，不由“双tokenizer可编”推为整次rollout可用。K=0，每合格技能总成本仍未定义。

父输入已交8包，但缺3消费槽；4个test父互用来源、全部8包只5连接组，CV消费还共用JD，不能报8个独立可跑评测。下一优先级是补真实独立case及同版本消费—盲Q—费用—D链，冻结阈值和技术前提后再有界采原生自主父轨迹；同时按连接组检验205过程目标的学习曲线，保留R-only并扩原R→实际动作配对。不得把重复曝光、synthetic解释或原226反馈当作扩量。充分性以未见完整父任务和学习曲线验证，当前无训练效果新实证。
'''
 (OUT/'QUALITY_AND_READINESS10.md').write_bytes(text.encode())
 print(json.dumps({'report':pin(OUT/'QUALITY_AND_READINESS10.md'),'metadata':pin(OUT/'METADATA.json')},ensure_ascii=False))
if __name__=='__main__':main()
