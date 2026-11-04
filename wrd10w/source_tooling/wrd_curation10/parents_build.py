"""Build actual complete parent source packs and genuine consumer inputs.

This is offline data preparation. It never invokes an Agent, model, source
program, runtime tool, evaluator, or optimizer. Historical answers are source
evidence for parents and audit only, never consumer answers or positive labels.
"""
from pathlib import Path
import collections,gzip,hashlib,json,shutil,re

ROOT=Path('D:/skillloop');MAIN=ROOT/'output/20261027_wrd_main_v10'
CLEAN=MAIN/'clean_inputs';OLD=ROOT/'output/20261031_wrd_curation09/holdout'
OUT=ROOT/'output/20261031_wrd_curation10/parent_inputs'
RUNTIME_IMAGE='sha256:97a0f55bec1ef293c15ddd5a17cc843050387bd2369dcf2fd388b1afd40810a2'

def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def rows(p):return [json.loads(x) for x in gzip.open(p,'rt',encoding='utf-8-sig') if x.strip()]
def sha(b):return hashlib.sha256(b if isinstance(b,bytes) else b.encode()).hexdigest()
def save(p,v):p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((json.dumps(v,ensure_ascii=False,indent=2)+'\n').encode())
def pin(p,base=OUT):return {'path':p.relative_to(base).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())}
def source_pin(p):return pin(p,ROOT)
def norm(t):return re.sub(r'\s+','',t).casefold()

def main():
 pool={x['source_id']:x for x in rows(CLEAN/'source_pool.with_body.jsonl.gz')}
 isolation={x['source_id']:x for x in read(OUT/'SOURCE_ISOLATION_AUDIT.json')['results']}
 reservation=read(OUT/'reservation.json');assert reservation['reserved_source_ids']==['conv_34b56ae9c535']
 old_tasks=[json.loads(l) for n in ['dev.tasks05.jsonl','test.tasks05.jsonl'] for l in (OLD/n).read_text(encoding='utf-8-sig').splitlines() if l.strip()]
 old_by_source={t['selected_source_id']:t for t in old_tasks}
 old_reserved=read(OLD/'holdout_reservation.json')
 reserved_splits={s:g['split'] for g in old_reserved['groups'] for s in g['source_ids']}
 reserved_splits.update({s:'dev' for s in reservation['reserved_source_ids']})
 configs=[
  ('train01','train','conv_6347576535a5','educational_HTML_simulation',['case_friction','case_solar_system'],[],
   '真实教学场景需求→交互式HTML演示→浏览器功能/科学边界检查。不是仅因输出同为HTML匹配。'),
  ('train02','train','conv_2b8fd8fdd8bc','source_evidence_to_JD_fit',['case_product_cv_A','case_product_cv_B'],[],
   '原JD＋真实候选证据→逐条匹配与未知边界→面试建议；消费以原用户提供的简历摘录为证据，不能假定已读缺失全文PDF。'),
  ('dev01','dev','conv_589813f393e6','interactive_HTML_game',['case_three_kingdoms'],['Second independent dev HTML game consumer input'],
   'HTML游戏的状态、碰撞/边界、控制与重启；三国横版游戏是同机制不同玩法，未验证技能具体适用性。'),
  ('dev02','dev','conv_007d40b3886f','client_confirmable_formal_review_checklist',[],['First distinct-source client-confirmable formal-review checklist consumer','Second distinct-source client-confirmable formal-review checklist consumer'],
   '规则/检查项→客户可确认可勾选清单；3D介绍文档只同格式，未假称相同机制。'),
  ('test01','test','conv_0400aac342b0','source_faithful_revision',['case_literacy_review','case_student_rewrite'],[],
   '原事实段落＋用户修改/受众约束→保持事实强度的审校/改写，不能虚增认证/成绩。'),
  ('test02','test','conv_15f0f4d89d3f','source_faithful_revision',['case_platform_rewrite','case_student_rewrite'],[],
   '原事实段落＋明确需求→忠实修订；不是同为text就视为同机制。'),
  ('test03','test','conv_ca2369adba0b','source_faithful_revision',['case_platform_rewrite','case_leadership_tone'],[],
   '对已有事实和立意作表达修订，事实与语气约束分别检查。'),
  ('test04','test','conv_24de551a33dd','source_faithful_revision',['case_platform_rewrite','case_student_rewrite'],[],
   '响应受众/语气纠正并保留原立意；与其他test父任务共享消费者，评价不能当4个独立组。'),
 ]
 case_configs={
  'case_friction':('train','conv_e35903a5c526',[0],'educational_HTML_simulation',[
   '交付真实可打开HTML，演示摩擦力而非只复述需求。','显示/交互不得把摩擦力方向、运动方向与作用对象混为一谈；实际功能另做运行检查。','保留原用户个人助手设定；不虚称已浏览器验收。']),
  'case_solar_system':('train','conv_c1ce48280769',[0],'educational_HTML_simulation',[
   '交付可打开的太阳系HTML动画；不能以静态描述冒充动画。','天体轨道/时间/大小的示意比例需有适当边界，不能宣称真实比例仿真而无依据。','保留原用户称呼偏好；实际交互与动画另做浏览器验收。']),
  'case_product_cv_A':('train','conv_12fc39ca6b57',[0,1],'source_evidence_to_JD_fit',[
   '按提供的产品岗位JD及当前原用户给出的候选简历摘录判断面试适配，不照搬HRD或机械岗位要求。','区分简历自述、可支持事实与缺失/噪声，不编造教育、工作年限、业绩或行业经验。','建议须可追溯到提供片段；不声称读过未提供的完整PDF，不作受保护属性推断。']),
  'case_product_cv_B':('train','conv_778bb56fc693',[0,1],'source_evidence_to_JD_fit',[
   '对本源三份候选摘录逐人按原JD判断，不把A案例的人名/经历混入。','保存噪声/缺失及不确定项，不用模型猜测修复为原事实。','不把未知信息直接当不符合，给出有依据的面试建议与待核项。']),
  'case_three_kingdoms':('dev','conv_34b56ae9c535',[0],'interactive_HTML_game',[
   '对应原请求的三国题材、刘关张与横版玩法；与参考游戏相似性单列主观质量，不捏造官方资产。','交付可运行游戏；初始画面、移动、碰撞/受击、失败和重开等实际功能由运行检查记录。','原后续黑屏/飞天反馈只在完整原件审计保留，不作为本次首次生成的已发生反馈或已验证回归。']),
  'case_platform_rewrite':('test','conv_0400aac342b0',[0],'source_faithful_revision',None),
  'case_literacy_review':('test','conv_15f0f4d89d3f',[2],'source_faithful_revision',None),
  'case_student_rewrite':('test','conv_ca2369adba0b',[2],'source_faithful_revision',None),
  'case_leadership_tone':('test','conv_24de551a33dd',[0,1,2],'source_faithful_revision',None),
 }
 needed={r[2] for r in configs}|{r[1] for r in case_configs.values()}
 originals=[];materials={}
 for sid in sorted(needed):
  r=pool[sid];q=isolation[sid]
  assert not q['direct_protected_or_known_private_ancestry'] and not q['protected_input_alias_detected']
  assert not q['reserved_private_answer_alias_detected']
  src=CLEAN/r['conversation_file'];raw=src.read_bytes()
  assert sha(raw)==r['original_conversation_pin']['sha256']
  target=OUT/'sources'/sid/'conversation.original.json';target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw)
  originals.append({'source_id':sid,'source_scope_component_id':r['source_group_id'],
   'full_conversation':pin(target),'original_reference':r['original_conversation_pin'],
   'all_user_occurrences_retained_in_source':len(r['user_messages']),
   'all_historical_assistant_occurrences_retained_in_source':len(r['historical_assistant_messages']),
   'archive_is_not_consumer_mount':True,'authentic_materials':r['authentic_materials'],
   'native_historical_event_identity_verified':r['historical_event_identity_verified']})
  for m in r['authentic_materials']:
   f=CLEAN/m['path'];b=f.read_bytes();assert sha(b)==m['sha256'] and len(b)==m['bytes']
   dest=OUT/m['path'];dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(b)
   materials[m['sha256']]={'object_pin':pin(dest),'aliases':materials.get(m['sha256'],{}).get('aliases',[])+[{'source_id':sid,'native_path':m['native_path']}]}
 orig={r['source_id']:r for r in originals}
 template=read(OLD/old_tasks[0]['rubric_pin']['path'])
 dimensions=template['quality_dimensions']
 cases=[]
 for cid,(split,sid,indices,mechanism,checks) in case_configs.items():
  assert (split=='train' and sid not in reserved_splits) or reserved_splits[sid]==split
  selected=[pool[sid]['user_messages'][i] for i in indices]
  reqs=[{'source_id':sid,'user_occurrence_index':i,'message_id':u['id'],'full_original_content_sha256':sha(u['content']),
    'extraction':'verbatim entire original user occurrence; antecedents chosen as a new coherent input state, not native historical replay'} for i,u in zip(indices,selected)]
  # Distinct role messages would be invalid consecutive user tool protocol in
  # some templates; one explicit coherent user payload keeps every byte inside.
  text='\n\n'.join(u['content'] for u in selected)
  inp={'schema':'wrd10-consumer-input-only-v1','task_id':cid,'split':split,'messages':[{'role':'user','content':text}],
   'source_requirement_pins':reqs,'historical_assistant_answer_in_input':False,'new_training_labels':0,
   'not_an_original_native_request_equivalence_claim':True,'authorship':'NEW_OFFLINE_STATE_SELECTION_WITH_VERBATIM_ORIGINAL_USER_BODY'}
  p=OUT/'consumers'/cid/'input.json';save(p,inp)
  if checks is None:
   old=old_by_source[sid];rub=read(OLD/old['rubric_pin']['path']);checks=rub['task_specific_criteria']
  rubric={'schema':'wrd10-consumer-evaluator-only-v1','task_id':cid,'authorship':'NEW_OFFLINE_RUBRIC_OR_PINNED09_CRITERIA_NOT_TEACHER_REASONING',
   'source_basis':reqs,'task_specific_criteria':checks,'quality_dimensions':dimensions,
   'quality_formula':template['quality_formula'],'threshold_status':'UNCALIBRATED_NO_QUALIFIED_SKILL_THRESHOLD',
   'qualified_skill_threshold':None,'no_reference_answer_supplied':True,'quality_score':None,'TSR':None,
   'not_mounted_to_actor':True,'scores_must_not_enter_earlier_state':True}
  rp=p.with_name('rubric.evaluator_only.json');save(rp,rubric)
  cases.append({'case_id':cid,'split':split,'source_ids':[sid],'source_scope_component_id':pool[sid]['source_group_id'],
   'mechanism':mechanism,'input':pin(p),'rubric':pin(rp),'authentic_materials':[],
   'input_status':'INPUT_BYTES_PREPARED_NOT_EXECUTED','new_business_calls':0,
   'historical_answer_excluded':True,'native_runtime_suitability_unverified':True})
 case_by_id={r['case_id']:r for r in cases}
 protocol={'schema':'wrd10-native-parent-protocol-draft-v1','is_launch_configuration':False,
  'fixed_runtime':{'image_digest':RUNTIME_IMAGE,'openclaw_version':'2026.9.5','teacher_model':'glm-5.3-flash',
   'native_discovery_read_and_session_loop_required':True,'outer_step_controller_allowed':False},
  'train_first_batch_caps_including_public_precheck':{'native_sessions':24,'provider_requests':200,'actual_input_plus_output_tokens':6000000,'elapsed_seconds':21600},
  'per_route_caps':{'parent_native_sessions':1,'parent_provider_requests':32,'consumer_sessions_max':6,'consumer_requests_per_session_max':8,
    'Q_sessions_max':4,'Q_requests_per_session_max':4,'native_sessions_max':11,'provider_requests_max':96},
  'public_precheck_within_global_caps':{'sessions':2,'provider_requests':8,'input_plus_output_tokens':300000,'elapsed_seconds':3600},
  'native_session_caps':{'elapsed_seconds_including_yield_wait_resume':1800,'maximum_response_tokens':32768},
  'token_cap_must_reserve_full_actual_request_plus_maximum_response_before_dispatch':True,
  'remaining_global_token_and_wall_budget_at_launch':None,
  'blind_Q':'First each case uses one independent native Q session to score anonymous randomized NS and V0 outputs separately; optional V1 uses one additional Q per case; frozen NS/V0 scores never rewritten.',
  'pre_outcome_qualification':{'same_version_resource_SHA_required':True,'real_delivery_and_source_fidelity_required':True,
   'both_distinct_consumer_inputs_required':True,'unknown_Q_not_zero':True,'Q_not_multiplied_by_TSR':True,
   'numeric_Q_threshold':None,'calibration_pending':True,'qualified_KEEP_credit_allowed_now':False},
  'input_only_does_not_authorize_native_dispatch':True,
  'dev_test_native_budget_allocated_this_round':False,
  'runtime_preflight_complete':False,'launch_ready':False}
 pp=OUT/'NATIVE_PROTOCOL_NOT_LAUNCH_CONFIG.json';save(pp,protocol)
 parents=[]
 for pid,split,sid,mechanism,cids,missing,why in configs:
  assert (split=='train' and sid not in reserved_splits) or reserved_splits[sid]==split
  assert all(case_by_id[c]['split']==split and sid not in case_by_id[c]['source_ids'] for c in cids)
  role_root='/workspace/inputs/source_conversations/'+sid+'.json'
  text=('请以完整企业会话为来源，自主完成WRD技能沉淀：识别可复用路线及原用户纠正，按需制作SKILL.md和真实资源，'
   '通过原生环境探索、复现、独立消费与反馈判断是否修订、保留、停止或HOLD。'
   '会话中的旧助手响应是待核来源，不能直接当本次正确动作、测试通过或效用证明。'
   '具体路线、工具、原生子会话调度、资源修订与收尾由你决定；外层不会逐步代执行。'
   '原件、失败、反馈和修订不得改写为成功。缺必要消费case、Q阈值、原生隔离或硬预算时，应如实HOLD。\n\n'
   '完整原会话：'+role_root+'\n'
   '可用原始材料：\n'+'\n'.join(m['native_path'] for m in pool[sid]['authentic_materials'])+'\n\n'
   '消费case仅允许由预检合格的原生子会话访问，父会话只接收opaque case ID和正式反馈；候选V0冻结前不得偷读盲case。'
   '当前只是离线输入包，原生工具、隔离、剩余统一预算和评分适用性尚待验证，不能声明已运行。')
  prompt={'schema':'wrd10-parent-input-only-v1','parent_task_id':pid,'split':split,'messages':[{'role':'user','content':text}],
   'source_conversations':[{'source_id':sid,'source_pin':orig[sid]['full_conversation'],'native_alias':role_root}],
   'source_materials':pool[sid]['authentic_materials'],'consumer_case_ids':cids,
   'not_a_replay_of_old_teacher_CoT':True,'authorship':'NEW_OFFLINE_FULL_PIPELINE_COMMISSION_ORIGINAL_SOURCE_BYTES_UNCHANGED',
   'eligible_for_SFT_positive_loss':False,'all_labels_if_tokenized_must_be_minus100':True,
   'not_native_launch_config':True,'model_or_actor_executed':False}
  path=OUT/'parents'/pid/'input.json';save(path,prompt)
  pair_shared_private=False
  if pid=='train02':
   # Same private JD, different authentic candidate pools. This relation must
   # be merged for independent-count reporting, not sold as 2 independent tasks.
   t1=norm(pool['conv_12fc39ca6b57']['user_messages'][0]['content'])
   t2=norm(pool['conv_778bb56fc693']['user_messages'][0]['content'])
   pair_shared_private=(t1==t2)
   assert pair_shared_private
  item={'parent_task_id':pid,'split':split,'source_ids':[sid],'source_scope_component_id':pool[sid]['source_group_id'],
   'mechanism':mechanism,'mechanism_matching_basis_new_annotation':why,'input':pin(path),
   'full_source_conversation_and_material_bytes_ready':True,
   'case_bindings':[{'case_id':c,'input_pin':case_by_id[c]['input']} for c in cids],
   'available_case_inputs':len(cids),'missing_case_inputs':missing,
   'case_pair_shared_private_JD':pair_shared_private,
   'case_pair_recorded_distinct_scopes_and_no_detected_private_alias':len(cids)==2 and not pair_shared_private,
   'case_pair_full_ancestry_independence_verified':False,
   'complete_input_bundle_with_two_distinct_case_sources':len(cids)==2,
   'new_independent_training_source_claimed':False,
   'component_task_upgraded_by_renaming':False,
   'parent_goal_is_new_full_WRD_commission':True,
   'known_input_materials_ready_is_not_native_execution_ready':True,
   'runtime_preflight_Q_calibration_and_budget_pending':True,'full_native_execution_ready':False,
   'native_rollouts':0,'qualified_KEEP':0,'new_training_labels':0}
  save(path.with_name('READINESS.json'),item);parents.append(item)
 save(OUT/'SOURCES_AND_MATERIALS.json',{'schema':'wrd10-parent-source-actual-bytes-v1','sources':originals,'material_objects':list(materials.values()),
  'original_source_count':len(originals),'distinct_material_objects':len(materials),'material_bytes':sum(x['object_pin']['bytes'] for x in materials.values())})
 save(OUT/'CONSUMER_INDEX.json',{'schema':'wrd10-consumer-input-index-v1','cases':cases,'distinct_case_inputs':len(cases),'actual_native_calls':0,'training_started':False})
 # Source IDs in different bundles may recur. Report connected bundles, not
 # eight parent task names as eight independent statistical experiments.
 dsu={}
 def find(s):
  dsu.setdefault(s,s)
  if dsu[s]!=s:dsu[s]=find(dsu[s])
  return dsu[s]
 def join(a,b):dsu[find(b)]=find(a)
 for r in parents:
  anchor='parent:'+r['parent_task_id']
  for sid in r['source_ids']:join(anchor,'source:'+sid)
  for c in r['case_bindings']:
   for sid in case_by_id[c['case_id']]['source_ids']:join(anchor,'source:'+sid)
 join('source:conv_12fc39ca6b57','source:conv_778bb56fc693')
 groups=collections.defaultdict(list)
 for r in parents:groups[find('parent:'+r['parent_task_id'])].append(r['parent_task_id'])
 bysplit=collections.Counter(r['split'] for r in parents)
 report={'schema':'wrd10-full-parent-input-index-v1','status':'ACTUAL_INPUT_BYTES_PREPARED_NOT_NATIVE_READY',
  'parent_inputs':parents,'parent_input_pack_count':len(parents),'parent_pack_split_counts':dict(bysplit),
  'parent_full_conversations_copied':len(parents),'all_unique_original_sources_copied':len(originals),
  'distinct_consumer_inputs':len(cases),'consumer_bindings':sum(r['available_case_inputs'] for r in parents),
  'planned_consumer_binding_slots':16,'missing_consumer_slots':sum(len(r['missing_case_inputs']) for r in parents),
  'bundles_with_two_distinct_case_sources':sum(r['complete_input_bundle_with_two_distinct_case_sources'] for r in parents),
  'bundles_with_two_recorded_distinct_case_source_scopes':sum(r['case_pair_recorded_distinct_scopes_and_no_detected_private_alias'] for r in parents),
  'bundles_with_two_full_ancestry_proven_independent_cases':0,
  'parent_bundle_connected_components':list(groups.values()),'parent_bundle_connected_component_count':len(groups),
  'test_parent_bundles_are_correlated_by_shared_sources':True,
  'new_reserved_dev_sources':reservation['reserved_source_ids'],
  'source_whole_request_train_overlap_notes':{'conv_ca2369adba0b':'Only generic English failure-resume wrapper occurrences 1 and3 match existing TRAIN; actual factual task occurrence2 does not. Generic wrapper is not private source ancestry.'},
  'excluded_candidate_sources':{'conv_692eb36fe8af':'Exact protected original-user body match; not copied or used in any input.'},
  'remaining_gaps':['One second distinct-source dev HTML-game case','Two client-confirmable formal-review checklist cases',
   'CV case pair shares identical private JD; add a distinct JD/candidate-source component before independent paired claim',
   'Native parent/child isolation, source discovery/read and hard budget preflight',
   'Five-dimension Q thresholds/applicability and cross-Q calibration',
   'Runtime complete53-tool dynamic input/output context budget check',
   'Actual no-skill/skill trials, same-SHA Q/cost and parent decisions'],
  'original226_H12_static_remain_isolated':True,'new_training_labels':0,'new_business_calls':0,'model_weights_loaded':False,'training_started':False,
  'actual_full_native_execution_ready':0,'complete_autonomous_demonstrations_created':0,'qualified_KEEP_created':0,
  'pins':[source_pin(Path(__file__)),source_pin(ROOT/'research/data_prep/wrd_curation10/parents_isolation.py'),
   source_pin(OUT/'SOURCE_ISOLATION_AUDIT.json'),source_pin(OUT/'reservation.json'),source_pin(MAIN/'TRAINING_MANIFEST.json')]}
 assert report['consumer_bindings']+report['missing_consumer_slots']==report['planned_consumer_binding_slots']
 save(OUT/'PARENT_INPUT_INDEX.json',report)
 # Check every recorded file from the just-created input indices by actual bytes.
 pins=[r['full_conversation'] for r in originals]+[r['object_pin'] for r in materials.values()]+[r['input'] for r in cases]+[r['rubric'] for r in cases]+[r['input'] for r in parents]
 for r in pins:
  p=OUT/r['path'];assert p.stat().st_size==r['bytes'] and sha(p.read_bytes())==r['sha256']
  assert p.resolve().is_relative_to(OUT.resolve())
 for r in cases:
  inp=read(OUT/r['input']['path']);assert len(inp['messages'])==1 and inp['messages'][0]['role']=='user'
  assert not inp['historical_assistant_answer_in_input'] and inp['new_training_labels']==0
 qa={'status':'PASS_ACTUAL_INPUT_BYTES_AND_SPLITS_ONLY','file_pins_verified':len(pins),'parent_inputs':len(parents),
  'distinct_consumers':len(cases),'missing_case_slots':report['missing_consumer_slots'],
  'recorded_distinct_case_scope_bundles':report['bundles_with_two_recorded_distinct_case_source_scopes'],
  'fully_proven_independent_case_bundles':0,
  'source_bundle_components':len(groups),'native_ready':0,'new_training_labels':0,'new_business_calls':0,'training_started':False,
  'index_sha256':sha((OUT/'PARENT_INPUT_INDEX.json').read_bytes()),'script_sha256':sha(Path(__file__).read_bytes())}
 save(OUT/'BUILD_QA.json',qa)
 print(json.dumps(qa,ensure_ascii=False))

if __name__=='__main__':main()
