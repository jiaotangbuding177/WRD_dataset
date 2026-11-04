"""Independent full627 token/mask and paired-target QA of the budget profile.

The passed full53 QA sources stay unchanged. This alternative conditioning
profile is not claimed to be native-request equivalent or lossless transfer.
Only CPU tokenizers and SHA-pinned local audit helpers are used.
"""
from pathlib import Path
from collections import Counter,defaultdict
from copy import deepcopy
import argparse,hashlib,importlib.util,json,os,sys,time
os.environ.update(CUDA_VISIBLE_DEVICES='-1',USE_TORCH='0',USE_TF='0',TOKENIZERS_PARALLELISM='false')
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[3];WORK=ROOT/'output/20261031_wrd_curation11'
FULL_HELPER_SHA='eede0ce9fb53c4596a1ad9bc8bc1dc4534ffc38bee625bc29dceecc5c3aeeb45'
MAIN_SHA='9aace2dc6b39d0dde3bafbf9f7f3d6763e485609017dd70a5c40c17a2c30277e'
FULL_RAW_SHA='7ca28cfbeac05315eefd89cad1899d72c91f4567ad1ae1cdc8f4ad239f6b2aee'
NOTE=('【本行条件接口声明】本行采用budget_projection的无工具条件决策接口，'
 '只根据当前可见状态给出简短理由及决策JSON，不提供或调用任何工具。'
 '这是另一个明确声明的训练条件，不是原生OpenClaw完整53工具请求的等价视图；'
 '不能据此证明原生部署就绪或与完整目录取得相同模型效果。')

def hs(x):return hashlib.sha256(x if isinstance(x,bytes) else x.encode()).hexdigest()
def sha(p):return hs(Path(p).read_bytes())
def load(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def js(x):return json.dumps(x,ensure_ascii=False,separators=(',',':'),sort_keys=True)
def pin(p):return {'path':str(Path(p).resolve()),'bytes':Path(p).stat().st_size,'sha256':sha(p)}
def module(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def save(p,x):
 p.parent.mkdir(parents=True,exist_ok=True);assert not p.exists(),'PRESERVE_PREVIOUS_QA'
 p.write_bytes((json.dumps(x,ensure_ascii=False,indent=2)+'\n').encode())
def positives(row):
 result=defaultdict(list)
 for a,b,c,w in row['supervision_spans']:
  assert w==0.05;result[c].extend(row['input_ids'][a:b])
 return dict(result)


def main(a):
 start=time.perf_counter();resultfile=a.out/'ALL627_BUDGET_FRESH_DUAL_TOKEN_MASK_PAIRED_TARGET_QA.json';assert not resultfile.exists()
 helperpath=ROOT/'research/data_prep/wrd_curation11/verify_synthetic_tokens11.py';assert sha(helperpath)==FULL_HELPER_SHA
 h=module('passed_full53_cpu_helper_only',helperpath)
 assert sha(h.MAIN)==MAIN_SHA
 fullproof=load(WORK/'technical_qa01/ALL627_SYNTHETIC_TOKEN_MASK_SOURCE_QA.json')
 assert fullproof['status'].startswith('PASS') and fullproof['direct_dual_tokenized_rows']==627
 source=WORK/'sft_candidates04/CANDIDATES.raw.jsonl.gz';assert sha(source)==FULL_RAW_SHA
 fullraw={r['id']:r for r in h.rows(source)};assert len(fullraw)==627
 fulltools=next(iter(fullraw.values()))['tools'];assert len(fulltools)==53
 for r in fullraw.values():assert r['tools']==fulltools;r['tools']=fulltools
 fullreport=load(WORK/'compiled04/COMPILATION_REPORT.json');report=load(a.compiled/'COMPILATION_REPORT.json')
 rawpath=h.checkpin(report['immutable_inputs'][0]);raw={r['id']:r for r in h.rows(rawpath)}
 assert len(raw)==627 and set(raw)==set(fullraw)
 projection=rawpath.parent;viewmap=load(projection/'VIEW_MAP.json');mapped={x['id']:x for x in viewmap['rows']}
 assert len(mapped)==627 and set(mapped)==set(raw)
 fullref=load(projection/'FULL53_REFERENCE.json');assert h.checkpin(fullref['raw_source'])==source
 for ref in fullref['compiled_references']:h.checkpin(ref)
 # Reconstruct the selection rule without importing the profile builder.
 reasons={};eligible=defaultdict(list)
 for r in fullraw.values():
  if r['messages'][-1].get('tool_calls'):reasons[r['id']]='NATIVE_ACTION_REQUIRES_FULL53'
  elif r['case_family_id'].startswith(('cross_condition_','policy_guard_')):reasons[r['id']]='HARD_GUARD_FULL53_NO_TOOL_UNAVAILABLE_SHORTCUT'
  else:eligible[(r['bank'],r['case_family_id'])].append(r['id'])
 anchors={min(ids) for ids in eligible.values()}
 for ident in anchors:reasons[ident]='D_ONLY_ORIGINAL_FAMILY_FULL53_ANCHOR'
 assert Counter(reasons.values())==Counter(NATIVE_ACTION_REQUIRES_FULL53=122,HARD_GUARD_FULL53_NO_TOOL_UNAVAILABLE_SHORTCUT=64,D_ONLY_ORIGINAL_FAMILY_FULL53_ANCHOR=39)
 assert len(reasons)==225
 fullrows={}
 for ref in fullreport['files']:
  p=WORK/'compiled04'/ref['path'];assert sha(p)==ref['sha256'] and p.stat().st_size==ref['bytes']
  for row in h.rows(p):
   fullrows[row['id']]={'target':row['messages'][-1],'positive_ids':positives(row),
       'positive_count':row['supervised_tokens'],'components':row['supervised_tokens_by_component'],
       'full_ids':row['input_ids'] if row['id'] in reasons else None,
       'full_spans':row['supervision_spans'],'total_tokens':row['total_tokens']}
 assert set(fullrows)==set(raw)
 for ident,r in raw.items():
  old=fullraw[ident];isfull=ident in reasons;proof=r['budget_projection_provenance']
  assert r['id']==old['id'] and r['messages'][-1]==old['messages'][-1]
  assert proof['same_target_id']==ident and proof['same_assistant_message_sha256']==hs(js(old['messages'][-1]))
  assert proof['full53_raw_source']==pin(source) and proof['full53_reference_profile']=='full53'
  assert proof['mutually_exclusive_alternative_profile'] is True and proof['not_additional_independent_target'] is True
  assert proof['not_runtime_configuration_change'] is True and proof['not_asserted_lossless_transfer_or_deployment_readiness'] is True
  assert r['conditioning_interface_profile']=='budget_projection01'
  assert r['source_annotation_provenance']==old['annotation_provenance'] and r['source_provenance_class']==old['provenance_class']
  changed_allowed={'annotation_provenance','provenance_class','student_view','tool_schema_provenance','messages','tools'}
  for k,v in old.items():
   if k not in changed_allowed:assert r[k]==v,('UNDECLARED_SOURCE_METADATA_CHANGE',k)
  assert r['source_ids']==[] and r['loss_multiplier']==0.05 and r['message_loss_mask']==[0,0,1]
  assert r['teacher_original_R_supervised'] is False and r['is_original_native_request_identical'] is False
  assert r['actual_native_tool_dispatch'] is False and r['training_started'] is False
  assert r['real_qualified_KEEP_supported'] is False and r['is_full_autonomous_execution_demonstration'] is False
  assert r['source_group_id']==old['source_group_id'] and r['case_source_pin']==old['case_source_pin']
  assert [x['role'] for x in r['messages']]==['system','user','assistant']
  previous_user=json.loads(old['messages'][1]['content']);current_user=json.loads(r['messages'][1]['content'])
  assert current_user['state']==previous_user['state'] and current_user['case_alias']==previous_user['case_alias']
  assert current_user['evidence_kind']==previous_user['evidence_kind'];h.no_audit_payload_in_state(current_user['state'])
  if isfull:
   assert r['messages']==old['messages'] and r['tools']==fulltools
   assert r['tool_schema_provenance']==old['tool_schema_provenance']
   assert proof['kind']=='RETAINED_FULL53_CONDITION' and proof['retention_reason']==reasons[ident]
   assert r['student_view']=='BUDGET_PROFILE_RETAINED_CAPTURED_NATIVE53_GIVEN_STATE'
   assert mapped[ident]['view']=='FULL53'
  else:
   assert not r['tools'] and not r['messages'][-1].get('tool_calls') and r['approved_components']==['R','D']
   assert r['tool_schema_provenance'] is None and r['source_full53_schema_provenance']==old['tool_schema_provenance']
   assert r['messages'][0]['content']==old['messages'][0]['content']+'\n'+NOTE
   assert current_user['conditioning_interface']=='EXPLICIT_TOOL_FREE_CONDITIONAL_DECISION_NOT_NATIVE53'
   assert proof['kind']=='EXPLICIT_TOOL_FREE_DECISION_INTERFACE_PROJECTION' and proof['retention_reason'] is None
   assert r['student_view']=='EXPLICIT_DECISION_ONLY_TOOL_FREE_NOT_NATIVE_REQUEST_EQUIVALENT'
   assert mapped[ident]['view']=='DECISION_ONLY_TOOL_FREE'
  assert mapped[ident]['same_target_message_sha256']==proof['same_assistant_message_sha256']
 from transformers import AutoTokenizer
 from transformers.utils.chat_template_utils import _compile_jinja_template
 from jsonschema import Draft202012Validator
 for name,assets in report['tokenizer_proof']['asset_sha256'].items():
  for filename,expected in assets.items():assert sha(a.assets/name/filename)==expected
 toks={n:h.CountTokenizer(AutoTokenizer.from_pretrained(a.assets/n,local_files_only=True,trust_remote_code=False)) for n in ['primary_14b','control_8b']}
 template=_compile_jinja_template(load(a.compiled/'CAUSAL_TEMPLATE.json')['variant'])
 vr=module('existing_exact_mask10_for_budget',ROOT/'research/data_prep/wrd_curation10/verify_main10.py')
 registry={t['function']['name']:t['function'] for t in fulltools}
 counts=Counter();byview=defaultdict(Counter);bybank=defaultdict(Counter);bystage=defaultdict(Counter);toolcounts=Counter();seen=set();inputs={};details=[];first=None
 for ref in report['files']:
  p=a.compiled/ref['path'];assert sha(p)==ref['sha256'] and p.stat().st_size==ref['bytes']
  for row in h.rows(p):
   ident=row['id'];assert ident not in seen;seen.add(ident);original=raw[ident];old=fullrows[ident]
   assert row['messages']==original['messages'] and row['tools']==original['tools']
   assert row['original_record_metadata']=={k:v for k,v in original.items() if k not in ['messages','tools']}
   assert row['messages'][-1]==old['target'] and positives(row)==old['positive_ids']
   assert row['supervised_tokens']==old['positive_count'] and row['supervised_tokens_by_component']==old['components']
   view='FULL53' if ident in reasons else 'DECISION_ONLY_TOOL_FREE'
   if view=='FULL53':assert row['input_ids']==old['full_ids'] and row['supervision_spans']==old['full_spans']
   count,excluded=vr.verify_token_row(row,template,toks);assert count==row['total_tokens'] and excluded==0
   comp=h.geometry(row,toks['primary_14b'].last_text,toks['primary_14b'].last['offset_mapping'])
   assert toks['primary_14b'].last==toks['control_8b'].last
   assert count<=32768 and not row.get('view')
   for call in row['messages'][-1].get('tool_calls',[]):
    fn=call['function'];assert view=='FULL53' and not list(Draft202012Validator(registry[fn['name']]['parameters']).iter_errors(fn['arguments']))
    toolcounts[fn['name']]+=1
   user=json.loads(row['messages'][1]['content']);user.pop('case_alias')
   key=hs(js({'system':row['messages'][0]['content'],'user':user,'tools':row['tools']}));target=hs(js(row['messages'][-1]))
   assert key not in inputs or inputs[key]==target,'ALIAS_REMOVED_SAME_INPUT_CONFLICT';inputs[key]=target
   for c in [counts,byview[view],bybank[row['bank']],bystage[row['stage']]]:
    c.update(rows=1,sequence_tokens=count,positive_tokens=sum(comp.values()),le16k=int(count<=16384),le32k=int(count<=32768))
    for component,n in comp.items():c['component_'+component]+=n
   details.append({'id':ident,'view':view,'total_tokens':count,'full53_tokens':old['total_tokens'],'positive_tokens':sum(comp.values()),
      'paired_target_text_and_positive_token_ids_equal':True,'source_group_id':row['source_group_id']})
   if first is None:first=deepcopy(row)
   if len(seen)%100==0:print(json.dumps({'budget_fresh_dual_HF_rows':len(seen),'expected':627}),flush=True)
 assert seen==set(raw) and len(seen)==627
 assert counts['sequence_tokens']==6353061 and counts['positive_tokens']==57362
 assert counts['le16k']==402 and counts['le32k']==627
 assert dict(toolcounts)=={'sessions_spawn':32,'subagents':32,'read':48,'write':10}
 assert counts['component_R']==19656 and counts['component_A']==8966 and counts['component_D']==28740
 calls_before={k:t.calls for k,t in toks.items()};assert calls_before=={'primary_14b':627,'control_8b':627}
 canary=deepcopy(first);canary['supervision_spans'].insert(0,[0,1,'A',0.05])
 try:vr.verify_token_row(canary,template,toks)
 except AssertionError as e:assert str(e)=='INPUT_OR_ROLE_HEADER_HAS_LOSS';negative='REJECTED_'+str(e)
 else:raise AssertionError('PROMPT_LOSS_CANARY_NOT_REJECTED')
 assert sha(h.MAIN)==MAIN_SHA and sha(source)==FULL_RAW_SHA and sha(helperpath)==FULL_HELPER_SHA
 assert 'torch' not in sys.modules
 save(a.out/'ALL627_BUDGET_ROW_DETAILS.json',{'rows':details})
 result={'schema':'wrd11-independent-budget627-all-token-mask-pair-QA',
  'status':'PASS_FRESH_ALL627_BUDGET_DUAL_HF_MASK_EXACT_PAIRED_TARGETS_AND_DECLARED_INTERFACE_CHANGE',
  'compiled':str(a.compiled),'compilation_report':pin(a.compiled/'COMPILATION_REPORT.json'),'budget_raw':pin(rawpath),
  'full53_raw_unchanged':pin(source),'full53_previous627_QA':pin(WORK/'technical_qa01/ALL627_SYNTHETIC_TOKEN_MASK_SOURCE_QA.json'),
  'direct_dual_tokenized_rows':627,'actual_main_row_tokenizer_calls':calls_before,
  'total_tokenizer_calls_including_negative':{k:t.calls for k,t in toks.items()},
  'counts':dict(counts),'by_view':{k:dict(v) for k,v in byview.items()},'by_bank':{k:dict(v) for k,v in bybank.items()},'by_stage':{k:dict(v) for k,v in bystage.items()},
  'selection_independently_rebuilt':{'native_action_full53':122,'hard_guard_full53':64,'family_anchor_full53':39,'all_full53':225,'decision_only_no_tools':402},
  'all627_ids_and_target_assistant_text_equal':True,'all627_positive_component_token_ID_sequences_equal':True,
  'all225_retained_full_input_token_IDs_and_spans_equal':True,
  'all402_tool_free_interfaces_explicitly_non_native_non_equivalent':True,
  'point_time_state_and_new_author_provenance_preserved':True,'native_tool_intents':dict(toolcounts),
  'all_positive_weight':0.05,'weighted_positive_mass':2868.1,'alias_removed_same_input_conflicts':0,
  'actual_prompt_loss_negative':negative,'original623_manifest_unchanged':MAIN_SHA,
  'not_additional_targets':True,'mutually_exclusive_with_full53_profile':True,
  'lossless_transfer_model_quality_GPU_cost_and_native_deployment_not_proven':True,
  'full53_seq_tokens':16929495,'budget_seq_tokens':counts['sequence_tokens'],'sequence_token_reduction_fraction':(16929495-counts['sequence_tokens'])/16929495,
  'four_feature_arrays_QA_pending_separate':True,'script':pin(Path(__file__)),'full_helper':pin(helperpath),
  'model_weights_loaded':False,'training_started':False,'native_business_sessions_started':0,'elapsed_seconds_CPU':time.perf_counter()-start}
 save(resultfile,result)
 print(json.dumps({k:result[k] for k in ['status','direct_dual_tokenized_rows','counts','selection_independently_rebuilt','actual_prompt_loss_negative']}))

if __name__=='__main__':
 ap=argparse.ArgumentParser(description=__doc__)
 ap.add_argument('--compiled',type=Path,default=WORK/'compiled_budget01')
 ap.add_argument('--assets',type=Path,default=ROOT/'output/20261025_wrd_training_preflight/tokenizer_assets')
 ap.add_argument('--out',type=Path,default=WORK/'technical_budget_qa01')
 main(ap.parse_args())
