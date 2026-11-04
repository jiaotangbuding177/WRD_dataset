"""Convert frozen authored cases into explicit standalone SFT candidates.

The original 623-record main manifest is never modified. No model or tool runs.
"""
from pathlib import Path
from copy import deepcopy
from collections import Counter
import gzip,hashlib,json
ROOT=Path(__file__).resolve().parents[3]
WORK=ROOT/'output/20261031_wrd_curation11'
OUT=WORK/'sft_candidates01'
BASE=ROOT/'output/20261027_wrd_main_v10/TRAINING_MANIFEST.json'
BASE_SHA='9aace2dc6b39d0dde3bafbf9f7f3d6763e485609017dd70a5c40c17a2c30277e'
def js(x):return json.dumps(x,ensure_ascii=False,separators=(',',':'),sort_keys=True)
def h(x):return hashlib.sha256(x if isinstance(x,bytes) else x.encode()).hexdigest()
def pin(p):p=Path(p);return {'path':str(p.resolve()),'bytes':p.stat().st_size,'sha256':h(p.read_bytes())}
def load(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def readrows(p):return [json.loads(l) for l in Path(p).read_text(encoding='utf-8-sig').splitlines() if l.strip()]
def save(p,x):p.parent.mkdir(parents=True,exist_ok=True);assert not p.exists();p.write_bytes((json.dumps(x,ensure_ascii=False,indent=2)+'\n').encode())
def lines(p,rs):
 with p.open('wb') as f:
  with gzip.GzipFile(fileobj=f,mode='wb',filename='',mtime=0) as g:
   for r in rs:g.write((js(r)+'\n').encode())

SYSTEM=('你正在解答WRD训练前离线构造的状态任务。保留需求边界和证据顺序，选择下一步、工具意图或给定政策下的收尾。'
 '输入明确区分两类证据：GIVEN_POLICY_STATE里的数值和环境是构造题给定前提，不是真实业务测量；'
 'CPU_FIXTURE_STATE只含已发生的外部本地CPU程序检查，不是OpenClaw原生轨迹，也不证明真实业务Q。'
 '只依据当前可见状态给出简短、可核查的决策依据。未知保持未知，成功状态不覆盖内容失败；不把局部通过称为合格技能。'
 '需要工具时使用给定原生schema，输出未执行的意图，不声称已调用或收到结果；无需工具时输出JSON决策。'
 'KEEP只能表示题给政策的条件结论，不能声称实际产出了合格技能。')

def make(case,state,request,origin,bank,sourcepin,schema_pin,tools,action=None,selected=True):
 identity='sft11-'+h(case['id'])[:24]
 messages=[{'role':'system','content':SYSTEM},
  {'role':'user','content':js({'request':request,'evidence_kind':origin,'case_alias':h(case['id'])[:16],'state':state})}]
 target=case['target'];rationale=target['R'];assert rationale and '\ufffd' not in rationale
 assistant={'role':'assistant','reasoning_content':rationale,'content':''}
 if action:
  assistant['tool_calls']=[{'id':'call_'+h(identity)[:24],'type':'function','function':{'name':action['name'],'arguments':action['arguments']}}]
  approved=['R','A']
 else:
  d=deepcopy(target['D']);d['evidence_origin']=origin;d['real_skill_qualified_claim']=False
  assistant['content']=js(d);approved=['R','D']
 messages.append(assistant)
 record={'id':identity,'owner_id':identity,'split':'train','stage':case['stage'],'bank':bank,
  'source_ids':[],'source_group_id':case['synthetic_root_id'],'source_admission':'ADMIT','training_admitted':True,
  'root_main_admission':False,'requires_external_root_admission':True,'message_loss_mask':[0,0,1],
  'supervision_message_indices':[2],'messages':messages,'tools':tools,'tool_schema_provenance':schema_pin,
  'approved_components':approved,'loss_multiplier':0.05,'allow_reviewed_completion_prefix':False,
  'annotation_provenance':origin,'case_source_pin':sourcepin,'case_id':case['id'],
  'case_family_id':case['family_id'],'case_mechanism_group':case.get('mechanism_group',case['family_id']),
  'pair_id':case.get('pair_id'),'synthetic_root_id':case['synthetic_root_id'],
  'actual_native_tool_dispatch':False,'teacher_original_R_supervised':False,'original_R_provenance':'NONE_NEW_AUTHOR_AUDITABLE_RATIONALE',
  'provenance_class':origin,'is_original_native_request_identical':False,'student_view':'FULL_CAPTURED_NATIVE53_CATALOG_WITH_AUTHORED_SHORT_STATE',
  'is_full_autonomous_execution_demonstration':False,'real_qualified_KEEP_supported':False,
  'future_feedback_in_model_input':False,'future_validation_retained_audit_only':True,
  'model_weights_loaded':False,'training_started':False}
 # Target and rejected alternatives remain in the raw audit case, never input.
 user=messages[1]['content'];assert 'rejected_alternative' not in user and 'future_same_input_credit_evidence' not in user
 assert all(m['role']!='tool' for m in messages),'NO_FAKE_NATIVE_TOOL_RETURN'
 return record

def portable_cpu_state(case):
 s=deepcopy(case['point_time_state'])
 # Actual Windows receipt source paths belong in audit pins, not pretend native
 # container mounts. Program hashes/bytes and all measured values remain exact.
 def sanitize(x):
  if isinstance(x,dict):
   for k,v in list(x.items()):
    if k=='path' and isinstance(v,str) and (':\\' in v or v.startswith('D:/')):
     x[k]='external_cpu_audit/'+Path(v).name
    else:sanitize(v)
  elif isinstance(x,list):
   for v in x:sanitize(v)
 sanitize(s)
 current=s['resource_file']['sha256'];s['current_version']='revision_'+current[:12]
 return s

def main():
 assert pin(BASE)['sha256']==BASE_SHA
 OUT.mkdir(parents=True,exist_ok=False)
 cat=load(WORK/'protocol_review/OPENCLAW_TOOLS53.json');tools=cat['tools'] if isinstance(cat,dict) else cat
 assert len(tools)==53 and len({t['function']['name'] for t in tools})==53
 schema=OUT/'TOOLS_CAPTURE53.json';save(schema,{'tools':tools,'kind':'EXACT_TECHNICAL_CAPTURE_EXPORT_NOT_NEW_TOOL_PROTOCOL'})
 schema_pin=pin(schema)
 cp=WORK/'controller_cases/run04/CASES.jsonl';rp=WORK/'resource_cases/run02/CASES.jsonl'
 controller=readrows(cp);resource=readrows(rp);allrows=[];held=[];mappings=[]
 for c in controller:
  assert c['enterprise_source_ids']==[] and c['provenance']['recorded_teacher_R'] is False
  r=make(c,c['point_time_state'],'依据给定前提决定当前下一步；若有原生工具意图则输出该调用，否则输出JSON决策。',
   'NEW_AUTHORED_GIVEN_POLICY_STATE_NOT_OBSERVED_BUSINESS_METRICS','synthetic_controller_given_policy11',pin(cp),schema_pin,tools,c['target'].get('native_tool_intent'))
  allrows.append(r);mappings.append({'case_id':c['id'],'record_id':r['id'],'selected':True,'request_kind':'CONDITIONAL_NEXT_STEP'})
 costs_seen=set()
 for c in resource:
  assert c['enterprise_source_ids']==[] and c['provenance']['recorded_teacher_R'] is False
  target=c['target'];dedupkey=h(js({'R':target['R'],'D':target['D']}))
  if c['id'].endswith('-cost_unknown_hold'):
   if costs_seen:
    held.append({'case_id':c['id'],'reason':'REPEATED_GENERIC_COST_TARGET_KEEP_AUDIT_QA_ONLY','target_sha256':dedupkey});continue
   costs_seen.add(dedupkey)
  projection=target.get('resource_action_projection');action=None
  if projection:
   assert h(projection['content'])==projection['content_sha256']
   assert projection['path']==c['point_time_state']['resource_file']['path']
   action={'name':'write','arguments':{'path':projection['path'],'content':projection['content']}}
   request='根据当前资源完整源码、合同和已发生失败修复资源，只输出完整write意图；尚未取得后续测试，不得提前宣称通过。'
  else:request='只审查当前资源和已发生的CPU检查，给出下一步JSON决策；此题不要求改写文件，不输出write调用。'
  r=make(c,portable_cpu_state(c),request,'NEW_AUTHORED_SYNTHETIC_RESOURCE_WITH_ACTUAL_CPU_RECEIPTS_NOT_NATIVE',
   'synthetic_cpu_resource11',pin(rp),schema_pin,tools,action)
  allrows.append(r);mappings.append({'case_id':c['id'],'record_id':r['id'],'selected':True,'request_kind':'WRITE_REPAIR' if projection else 'DECISION_ONLY'})
 assert len({r['id'] for r in allrows})==len(allrows)
 # Detect identical conditioning bytes paired with conflicting responses.
 seen={}
 for r in allrows:
  key=h(js(r['messages'][:-1]));target=h(js(r['messages'][-1]))
  assert key not in seen or seen[key]==target,'CONFLICTING_TARGET_FOR_IDENTICAL_INPUT'
  seen[key]=target
 raw=OUT/'CANDIDATES.raw.jsonl.gz';lines(raw,allrows)
 save(OUT/'CONVERSION_RECEIPT.json',{'status':'EXPLICIT_NEW_AUTHOR_CASES_CONVERTED_PENDING_SEMANTIC_ROOT_AND_FULL_TOKEN_QA',
  'controller_raw_cases':len(controller),'resource_raw_cases':len(resource),'selected_records':len(allrows),'generic_repeated_cost_cases_audit_only':held,
  'same_state_different_instruction_resolved_by_visible_user_request':True,'no_tool_return_messages_fabricated':True,
  'native_catalog_count':len(tools),'catalog_pin':schema_pin,'source_case_pins':[pin(cp),pin(rp)],'raw_candidate_pin':pin(raw),
  'base_real_main_unchanged_sha256':BASE_SHA,'source_groups_are_synthetic_not_enterprise_ids':True,
  'selected_by_bank':dict(Counter(r['bank'] for r in allrows)),'selected_by_stage':dict(Counter(r['stage'] for r in allrows)),
  'original_teacher_R_added':0,'new_enterprise_sources':0,'real_qualified_KEEP_added':0,'training_started':False,
  'mapping':mappings,'script':pin(__file__)})
 print(json.dumps({'selected_records':len(allrows),'resource_cases_audit_only':len(held),'native_catalog':53,'main_unchanged':True}))
if __name__=='__main__':main()
