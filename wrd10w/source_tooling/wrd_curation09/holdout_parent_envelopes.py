"""Preserve complete source conversations and future WRD protocol envelopes.

Protocol only: no native process, model, tool dispatch or training is started.
"""
import gzip,hashlib,json
from pathlib import Path
ROOT=Path('D:/skillloop');OUT=ROOT/'output/20261031_wrd_curation09/holdout';CLEAN=ROOT/'output/20261027_wrd_main_v10/clean_inputs'
def sha(x):return hashlib.sha256(x if isinstance(x,bytes) else x.encode()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def save(p,v):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def pin(p):return {'path':str(p.relative_to(OUT)).replace('\\','/'),'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())}
pool={r['source_id']:r for r in [json.loads(s) for s in gzip.open(CLEAN/'source_pool.with_body.jsonl.gz','rt',encoding='utf-8-sig')]}
reservation=read(OUT/'holdout_reservation.json');catalog=read(OUT/'TASK_CATALOG_ALL36_05.json')
bygroup={r['source_scope_component_id']:r for r in catalog}
sources=[];protocol=[]
for sid in reservation['reserved_source_ids']:
 original=CLEAN/'sources'/sid/'conversation.original.json';body=original.read_bytes()
 assert sha(body)==pool[sid]['original_conversation_pin']['sha256']
 target=OUT/'complete_source_audit'/sid/'conversation.original.json';target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(body)
 sources.append({'source_id':sid,'source_scope_component_id':pool[sid]['source_group_id'],
  'original_conversation_pin':pool[sid]['original_conversation_pin'],'complete_reachable_copy':pin(target),
  'native_alias_for_future_protocol':'/workspace/inputs/source_conversations/'+sid+'.json',
  'contains_historical_assistant_messages_as_source_evidence':True,
  'not_mounted_to_component_tasks':True,'not_default_train':True,
  'material_refs':pool[sid]['authentic_materials']})
source_by_id={r['source_id']:r for r in sources}
for g in reservation['groups']:
 component=bygroup[g['source_scope_component_id']]
 conversation_paths=[source_by_id[s]['native_alias_for_future_protocol'] for s in g['source_ids']]
 materials={m['sha256']:m for s in g['source_ids'] for m in pool[s]['authentic_materials']}
 material_aliases=[m for s in g['source_ids'] for m in pool[s]['authentic_materials']]
 text=('请把下面完整企业会话作为来源资料，识别可复用工作路线与原用户纠正；在条件具备时构建候选skill及必要资源，保留来源与版本记录。'
       '会话中的旧模型输出是待审来源，不是本次动作正确或技能试跑有效的证明。'
       '当前没有给出独立同类消费任务或该版本的消费结果。缺少验证条件应明确HOLD，不得宣称已经KEEP或已证明节省成本。\n\n完整会话：\n'+'\n'.join(conversation_paths))
 if materials:text+='\n\n原导出真实材料（按实际SHA绑定，须自行判断与所选路线的关系）：\n'+'\n'.join(m['native_path'] for m in material_aliases)
 record={'schema':'wrd09-future-parent-protocol-envelope-v1','source_scope_component_id':g['source_scope_component_id'],
  'split':g['split'],'evaluation_level':'FUTURE_WRD_PARENT_PROTOCOL_NOT_READY',
  'new_author_task_instruction':text,'authorship':'NEW_OFFLINE_PROTOCOL_BY_RESEARCH_CURATOR',
  'source_conversations':[source_by_id[s]['complete_reachable_copy'] for s in g['source_ids']],
  'material_object_refs':[{'sha256':m['sha256'],'path':'objects/'+m['sha256'][:2]+'/'+m['sha256'],'native_alias':m['native_path']} for m in material_aliases],
  'component_task_id':component['task_id'],'component_input_status':component['status'],
  'source_scope_or_content_HOLD_reason':component['hold_reason'],
  'status':'NOT_READY','automatic_launch_authorized':False,
  'runtime_freeze_reference':'Fixed native OpenClaw image/tools/skills discovery/read/session loop; not bound or preflighted by this envelope.',
  'model_id':None,'budget':None,'independent_consumer_task':None,
  'missing':['Verified separate same-mechanism consumer inputs','Actual native parent dispatch/recording preflight','Fixed budget and runtime binding','Same-version business trial with independent Q and full costs'],
  'gold_skill_or_gold_reasoning':None,'model_rollout':None,'qualified_KEEP':None,
  'full_WRD_ready_count_credit':0,'no_reconstruction_of_historical_CoT_or_feedback':True}
 protocol.append(record)
save(OUT/'COMPLETE_SOURCE_REACHABILITY.json',{'schema':'wrd09-complete-source-reachability-v1','sources':sources,
 'sources_count':len(sources),'conversations_SHA_verified':len(sources),
 'complete_source_is_audit_or_future_parent_input_not_component_answer':True})
save(OUT/'FUTURE_WRD_PARENT_ENVELOPES_NOT_READY.json',{'schema':'wrd09-future-parent-envelope-index-v1',
 'envelopes':protocol,'protocol_envelopes':36,'ready_full_WRD_evaluation_tasks':0,
 'new_business_Teacher_Actor_calls':0,'training_started':False,'script_sha256':sha(Path(__file__).read_bytes())})
print(json.dumps({'sources':len(sources),'protocol_envelopes':len(protocol),'ready_full_WRD':0,
 'complete_source_index':pin(OUT/'COMPLETE_SOURCE_REACHABILITY.json'),
 'future_protocol_index':pin(OUT/'FUTURE_WRD_PARENT_ENVELOPES_NOT_READY.json')},ensure_ascii=False))
