"""Finite final semantic review of authored run07 and 51 CPU-resource SFT rows.

No native call, model, training, data mutation or new training case is made.
The only executed subject is the trusted pure research policy function;
its tool intents remain dictionaries and are not invoked.
"""
from pathlib import Path
from copy import deepcopy
from collections import Counter
import gzip,hashlib,json,re,sys,types
from jsonschema import Draft202012Validator
ROOT=Path('D:/skillloop');WORK=ROOT/'output/20261031_wrd_curation11';OUT=WORK/'semantic_review'
SOURCE=ROOT/'research/data_prep/wrd_curation11/controller_cases11.py'
CASES=WORK/'controller_cases/run07/CASES.jsonl'
CANDIDATE=WORK/'sft_candidates04/CANDIDATES.raw.jsonl.gz'
BUILD=ROOT/'research/data_prep/wrd_curation11/build_sft11.py'
def js(x):return json.dumps(x,ensure_ascii=False,separators=(',',':'),sort_keys=True)
def hs(x):return hashlib.sha256(x if isinstance(x,bytes)else x.encode()).hexdigest()
def load(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def pin(p):p=Path(p);return {'path':str(p.resolve()),'bytes':p.stat().st_size,'sha256':hs(p.read_bytes())}
def readrows(p):return [json.loads(l)for l in Path(p).read_text(encoding='utf-8-sig').splitlines()if l.strip()]
def save(name,x):
 p=OUT/name;assert not p.exists();p.write_bytes((json.dumps(x,ensure_ascii=False,indent=2)+'\n').encode());return pin(p)
def main():
 before={str(p):pin(p)for p in [SOURCE,CASES,CANDIDATE,BUILD]}
 generation=load(CASES.parent/'GENERATION_QA.json')
 assert before[str(CASES)]['sha256']==generation['cases_sha256']and before[str(SOURCE)]['sha256']==generation['generator_sha256']
 old=WORK/'controller_cases/run05/CASES.jsonl';oldqa=load(OUT/'CONTROLLER_SEMANTIC_PROTOCOL_QA.json')
 assert oldqa['status']=='PASS_CONDITIONAL_POLICY_AND_NATIVE_ABI_ONLY' and pin(old)==oldqa['cases_pin']
 historical_source=old.parent/'GENERATOR_SNAPSHOT.py';assert hs(historical_source.read_bytes())==oldqa['exact_generator_snapshot_pin']['sha256']
 rawlines=CASES.read_bytes().splitlines(keepends=True);oldlines=old.read_bytes().splitlines(keepends=True)
 assert len(rawlines)==576 and rawlines[:512]==oldlines and len(oldlines)==512
 cases=[json.loads(l)for l in rawlines];byid={c['id']:c for c in cases};assert len(byid)==576
 cross=load(CASES.parent/'CROSS_CONDITION_PAIRS.json')['pairs'];policy=load(CASES.parent/'POLICY_GUARD_PAIRS.json')['pairs']
 assert len(cross)==len(policy)==32
 extra=[]
 for kind,edges in [('cross_budget',cross),('policy_precondition',policy)]:
  for e in edges:
   positive,negative=byid[e['positive_case_id']],byid[e['negative_case_id']]
   a,b=positive['point_time_state'],negative['point_time_state'];fa,fb=a['facts'],b['facts']
   diff=[k for k in set(fa)|set(fb)if fa.get(k)!=fb.get(k)];assert len(diff)==1 and e['changed_field']=='facts.'+diff[0]
   assert a['policy']==b['policy']and a['request_kind']==b['request_kind']
   assert positive['synthetic_root_id']==negative['synthetic_root_id']and positive['mechanism_group']==negative['mechanism_group']
   assert negative['target']['D']['decision']=='HOLD'and negative['target']['native_tool_intent']is None
   assert negative['target']['D']['real_skill_qualified_claim']is False and negative['provenance']['recorded_native_execution']is False
   field=diff[0]
   if kind=='cross_budget':
    unit=field.removeprefix('remaining_');assert fb[field]==0 and fb['required_'+unit]>0
    assert positive['target']['D']['decision']=='DISPATCH'
    assert str(fb['required_'+unit])in negative['target']['R']and unit in negative['target']['R']
   else:
    assert fa[field]is True and fb[field]is False and positive['target']['D']['decision']=='KEEP'
    assert field in negative['target']['R']
   assert negative['enterprise_source_ids']==[] and negative['target']['new_author_reasoning']is True
   extra.append({'case_id':negative['id'],'kind':kind,'changed_field':field,'status':'PASS_FINITE_PREMISE_FLIP','same_group':True})
 assert {e['case_id']for e in extra}=={r['id']for r in cases[512:]}
 # The corrected research policy is evaluated against the finite 22 composite
 # boundaries that originally exposed failures; this is not an unseen eval.
 subject=types.ModuleType('trusted_pure_policy07');subject.__file__=str(SOURCE)
 previous=sys.dont_write_bytecode;sys.dont_write_bytecode=True
 try:exec(compile(SOURCE.read_bytes(),str(SOURCE),'exec'),subject.__dict__)
 finally:sys.dont_write_bytecode=previous
 probes=[]
 for kind in ['dispatch_time','dispatch_requests','dispatch_io','skill_actual_read']:
  base=next(c for c in cases[:512]if c['point_time_state']['request_kind']==kind and c['target']['D']['decision']=='DISPATCH')
  for unit in ['seconds','requests','io_tokens']:
   s=deepcopy(base['point_time_state']);s['facts']['remaining_'+unit]=max(0,s['facts']['required_'+unit]-1)
   result=subject.solve(s);assert result['D']['decision']=='HOLD'and result['native_tool_intent']is None
   probes.append({'request_kind':kind,'changed_field':'remaining_'+unit,'expected':'HOLD_WITHOUT_NATIVE_INTENT','actual':result['D']['decision'],'PASS':True})
 for kind in ['active_duplicate','unknown_child_identity']:
  base=next(c for c in cases[:512]if c['point_time_state']['request_kind']==kind and c['target']['D']['decision']=='WAIT')
  s=deepcopy(base['point_time_state']);s['facts']['remaining_seconds']=0;result=subject.solve(s)
  assert result['D']['decision']=='HOLD'and result['native_tool_intent']is None
  probes.append({'request_kind':kind,'changed_field':'remaining_seconds','expected':'HOLD_WITHOUT_NATIVE_INTENT','actual':result['D']['decision'],'PASS':True})
 for kind,fields in [('quality_threshold',['same_input','costs_complete']),('delivery_success',['same_version','independent_consumer']),('dominated_cost',['quality_equal','matched_independent_consumer']),('amortization',['quality_equal','matched_independent_consumer'])]:
  base=next(c for c in cases[:512]if c['point_time_state']['request_kind']==kind and c['target']['D']['decision']=='KEEP')
  for field in fields:
   s=deepcopy(base['point_time_state']);s['facts'][field]=False;result=subject.solve(s)
   assert result['D']['decision']=='HOLD'and result['native_tool_intent']is None
   probes.append({'request_kind':kind,'changed_field':field,'expected':'HOLD_WITHOUT_NATIVE_INTENT','actual':result['D']['decision'],'PASS':True})
 assert len(probes)==22
 with gzip.open(CANDIDATE,'rt',encoding='utf-8-sig')as f:candidate=[json.loads(l)for l in f if l.strip()]
 assert len(candidate)==627
 controller=[r for r in candidate if r['bank']=='synthetic_controller_given_policy11'];resources=[r for r in candidate if r['bank']=='synthetic_cpu_resource11']
 assert len(controller)==576 and len(resources)==51
 tool_list=load(WORK/'protocol_review/OPENCLAW_TOOLS53.json');registry={t['function']['name']:t['function']for t in tool_list};intents=Counter()
 for r in candidate:
  assert r['tools']==tool_list and r['source_ids']==[] and r['loss_multiplier']==0.05
  assert r['teacher_original_R_supervised']is False and r['actual_native_tool_dispatch']is False and r['real_qualified_KEEP_supported']is False
  assert [m['role']for m in r['messages']]==['system','user','assistant']and r['message_loss_mask']==[0,0,1]
  assert r['future_feedback_in_model_input']is False and r['future_validation_retained_audit_only']is True
  for c in r['messages'][-1].get('tool_calls',[]):
   f=c['function'];args=f['arguments'];assert isinstance(args,dict)
   assert not list(Draft202012Validator(registry[f['name']]['parameters']).iter_errors(args));intents[f['name']]+=1
 for r in controller:
  case=byid[r['case_id']];message=r['messages'][-1];user=json.loads(r['messages'][1]['content'])
  assert user['state']==case['point_time_state']and message['reasoning_content']==case['target']['R']
  assert r['source_group_id']==case['synthetic_root_id']
  if case['target']['native_tool_intent']:
   c=message['tool_calls'][0]['function'];assert c=={'name':case['target']['native_tool_intent']['name'],'arguments':case['target']['native_tool_intent']['arguments']}
  else:
   d=json.loads(message['content']);assert all(d[k]==v for k,v in case['target']['D'].items())
 # Read actual current CPU receipts and full resource source from each input.
 # No resource is executed by this reviewer and no future receipt is required.
 rawresources=readrows(WORK/'resource_cases/run02/CASES.jsonl');rawby={c['id']:c for c in rawresources};rcheck=[]
 for r in resources:
  case=rawby[r['case_id']];user=json.loads(r['messages'][1]['content']);state=user['state'];msg=r['messages'][-1];reason=msg['reasoning_content'];observed=state['visible_run'];file=state['resource_file']
  assert hs(file['content'])==file['sha256']==observed['program']['sha256']
  assert state['current_version']=='revision_'+file['sha256'][:12]
  assert observed['tool_identity']=='PYTHON_SUBPROCESS_NOT_OPENCLAW'and observed['business_Q_measured']is False and observed['business_qualified_KEEP']is False
  assert observed['total']==len(observed['checks'])and observed['passed']==sum(x['ok']for x in observed['checks'])
  assert observed['all_passed']==(observed['passed']==observed['total'])
  assert state['business_quality_Q']is None and state['independent_business_consumer_trials']==[] and state['qualified_KEEP_count']==0 and state['total_per_qualified_skill_cost']is None
  suffix=r['case_id'].split('-',2)[-1]
  calls=msg.get('tool_calls',[])
  if r['case_id'].endswith('write_verified_repair'):
   assert '完整write意图'in user['request']and len(calls)==1
   assert calls[0]['function']['name']=='write';args=calls[0]['function']['arguments'];proj=case['target']['resource_action_projection']
   assert args['path']==file['path']==proj['path'] and args['content']==proj['content'] and hs(args['content'])==proj['content_sha256']
   assert not observed['all_passed']and not state['visible_prior_runs']
   assert '不能提前宣称通过或KEEP'in reason and message_not_future_pass(reason)
  else:
   assert '不输出write调用'in user['request']and not calls
   d=json.loads(msg['content']);assert d['real_skill_qualified_claim']is False and d['decision']!='KEEP'
  if r['case_id'].endswith('diagnose_v0'):
   assert observed['passed']<observed['total']
   m=re.search(r'在(\d+)个明确合同检查中有(\d+)个失败',reason);assert m and int(m[1])==observed['total']and int(m[2])==observed['total']-observed['passed']
  elif r['case_id'].endswith('noop_repair_still_fails'):
   prior=state['visible_prior_runs'][-1];assert prior['program']['sha256']==file['sha256']
   assert prior['checks']==observed['checks'] and not observed['all_passed']
  elif r['case_id'].endswith('regression_detected'):
   prior=state['visible_prior_runs'][-1];assert prior['all_passed']and prior['program']['sha256']!=file['sha256']and not observed['all_passed']
   assert f'{observed["passed"]}/{observed["total"]}'in reason and '仍有实际失败'in reason
   correction=r['curator_rationale_correction'];assert correction['old_R_sha256']==hs(case['target']['R'])and correction['new_R_sha256']==hs(reason)
  elif r['case_id'].endswith('local_pass_needs_consumption'):
   assert observed['all_passed']and f'{observed["total"]}个本地合同检查全部通过'in reason
   assert '不能升级为合格技能KEEP'in reason
  elif r['case_id'].endswith('cost_unknown_hold'):
   assert observed['all_passed']and state['qualified_KEEP_count']==0
   assert json.loads(msg['content'])['unit_cost']is None
  rcheck.append({'case_id':r['case_id'],'current_program_sha256':file['sha256'],'actual_current_passed':observed['passed'],'actual_current_total':observed['total'],'request_matches_action':True,'status':'PASS_CURRENT_STATE_ONLY_LIMITED_CREDIT'})
 conv=load(CANDIDATE.parent/'CONVERSION_RECEIPT.json');held=conv['generic_repeated_cost_cases_audit_only'];assert len(held)==9
 assert len([r for r in resources if r['case_id'].endswith('cost_unknown_hold')])==1
 assert not ({r['case_id']for r in candidate}&{r['case_id']for r in held})
 for p,ref in before.items():assert pin(p)==ref,'SUBJECT_CHANGED_DURING_FINAL_REVIEW'
 report={'schema':'wrd-curation11-final-limited-semantic-review-run07','status':'PASS_FINITE_RUN07_AND_RESOURCE51_SEMANTIC_PROTOCOL_REVIEW',
  'source_pins':before,'reviewer_pin':pin(__file__),'prior512_case_byte_identity_with_passed_run05':True,
  'prior512_semantic_QA_pin':pin(OUT/'CONTROLLER_SEMANTIC_PROTOCOL_QA.json'),'historical_run05_generator_snapshot_pin':pin(historical_source),
  'controller_cases':576,'old_cases_unchanged':512,'new_cross_budget_blockers':32,'new_policy_precondition_blockers':32,
  'fundamental_original_families':32,'family_labels_with_negative_variants':len({r['family_id']for r in cases}),'unchanged_mechanism_groups':len({r['mechanism_group']for r in cases}),
  'new64_reviews':extra,'finite_corrected_composite_probes':probes,'finite_corrected_composite_passed':22,
  'probes_used_for_correction_not_unseen_evaluation':True,'does_not_certify_all_combinations':True,
  'source_guard_read_review':'Common ready-input/no-active-duplicate/all-budget guards precede positive dispatch; zero-time ordinary-child waits are stopped; each KEEP family checks explicit prerequisites/current-version binding before its scalar comparison. Only the declared finite cases/probes were rechecked.',
  'policy_flag_conflicts_scope':'Some one-flag negative variants conflict with other positive attestations, e.g. same_version=false while digest fields remain equal, or prospective=false with an investment-scope label. HOLD is appropriate for the failed/conflicting premise; these are guard/conflict cases, not 32 new clean empirical workflow experiences.',
  'SFT_candidates':627,'controller_SFT_rows':576,'resource_SFT_rows':51,'resource_row_reviews':rcheck,
  'resource_regression_R_corrected_from_visible_current_failures':10,'resource_write_intents':10,'repeated_cost_rows_audit_only':9,
  'all_candidate_native_intents_schema_valid_by_tool':dict(intents),'input_roles_have_no_fabricated_native_tool_return':True,
  'resource_reasoning_scope':'Local causal diagnoses and proposed repair methods follow the visible current source, contract, declared test inputs and completed CPU checks. Counterfactual algorithm cautions are not claims that an unseen future repair has succeeded. Regression targets use current measured failure counts, not assumed original v0 causes.',
  'compile_token_mask_four_feature_QA_not_performed_here':True,'new_real_enterprise_experiences':0,'native_calls_executed':0,'student_model_or_training_runs':0,'real_qualified_KEEP_added':0,
  'freeze_recommendation':'Freeze this finite semantic scope after separate compiler QA; do not expand counts to claim autonomous capability.'}
 p=save('FINAL_RUN07_QA.json',report);print(json.dumps({'status':report['status'],'QA_sha256':p['sha256'],'controllers':576,'resources':51,'finite_probes':22}))
def message_not_future_pass(text):return '后续同输入测试结果仍需实际取得'in text
if __name__=='__main__':main()
