"""Build a mutually-exclusive conditioning profile over the same 627 targets.

Keeps every action, all64 hard guards and one remaining D-only family anchor
under the full captured53 catalog. Other D-only rows explicitly use a distinct
tool-free decision interface. No runtime configuration or real data is changed.
Only the existing CPU tokenizer compiler may run; no model/native/tool action.
"""
from pathlib import Path
from copy import deepcopy
from collections import Counter,defaultdict
from array import array
import argparse,gzip,hashlib,importlib.util,json,os,subprocess,sys
os.environ.update(USE_TORCH='0',USE_TF='0',CUDA_VISIBLE_DEVICES='-1',TOKENIZERS_PARALLELISM='false')
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[3];WORK=ROOT/'output/20261031_wrd_curation11'
SOURCE=WORK/'sft_candidates04/CANDIDATES.raw.jsonl.gz'
SOURCE_SHA='7ca28cfbeac05315eefd89cad1899d72c91f4567ad1ae1cdc8f4ad239f6b2aee'
FULL=WORK/'compiled04';OUT=WORK/'budget_projection01';COMPILED=WORK/'compiled_budget01'
BASE=ROOT/'output/20261027_wrd_main_v10/TRAINING_MANIFEST.json'
BASE_SHA='9aace2dc6b39d0dde3bafbf9f7f3d6763e485609017dd70a5c40c17a2c30277e'
NOTE=('【本行条件接口声明】本行采用budget_projection的无工具条件决策接口，'
 '只根据当前可见状态给出简短理由及决策JSON，不提供或调用任何工具。'
 '这是另一个明确声明的训练条件，不是原生OpenClaw完整53工具请求的等价视图；'
 '不能据此证明原生部署就绪或与完整目录取得相同模型效果。')
def js(x):return json.dumps(x,ensure_ascii=False,separators=(',',':'),sort_keys=True)
def h(x):return hashlib.sha256(x if isinstance(x,bytes)else x.encode()).hexdigest()
def load(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def pin(p):p=Path(p);return {'path':str(p.resolve()),'bytes':p.stat().st_size,'sha256':h(p.read_bytes())}
def save(name,x):
 p=OUT/name;assert not p.exists();p.write_bytes((json.dumps(x,ensure_ascii=False,indent=2)+'\n').encode());return pin(p)
def rows(p):
 with gzip.open(p,'rt',encoding='utf-8-sig')as f:
  for l in f:
   if l.strip():yield json.loads(l)
def module(name,p):
 s=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def build():
 assert pin(SOURCE)['sha256']==SOURCE_SHA and pin(BASE)['sha256']==BASE_SHA
 assert not OUT.exists() and not COMPILED.exists(),'NEW_EXPLICIT_PROFILE_OUTPUTS_REQUIRED'
 OUT.mkdir(parents=True)
 original=list(rows(SOURCE));assert len(original)==627 and len({r['id']for r in original})==627
 source_pin=pin(SOURCE);reasons={};eligible=defaultdict(list)
 for r in original:
  assert len(r['tools'])==53 and r['messages'][-1]['role']=='assistant'
  if r['messages'][-1].get('tool_calls'):reasons[r['id']]='NATIVE_ACTION_REQUIRES_FULL53'
  elif r['case_family_id'].startswith(('cross_condition_','policy_guard_')):reasons[r['id']]='HARD_GUARD_FULL53_NO_TOOL_UNAVAILABLE_SHORTCUT'
  else:eligible[(r['bank'],r['case_family_id'])].append(r)
 anchors=[]
 for (bank,family),group in sorted(eligible.items()):
  r=min(group,key=lambda x:x['id']);reasons[r['id']]='D_ONLY_ORIGINAL_FAMILY_FULL53_ANCHOR'
  anchors.append({'bank':bank,'case_family_id':family,'anchor_record_id':r['id'],'case_id':r['case_id'],
   'eligible_D_only_count':len(group),'rule':'MIN_LEXICOGRAPHIC_TARGET_ID_WITHIN_BANK_AND_ORIGINAL_FAMILY'})
 assert Counter(reasons.values())=={'NATIVE_ACTION_REQUIRES_FULL53':122,'HARD_GUARD_FULL53_NO_TOOL_UNAVAILABLE_SHORTCUT':64,'D_ONLY_ORIGINAL_FAMILY_FULL53_ANCHOR':39}
 projected=[];mapping=[]
 for original_row in original:
  r=deepcopy(original_row);target=js(r['messages'][-1]);full=r['id']in reasons
  r['source_annotation_provenance']=r['annotation_provenance'];r['source_provenance_class']=r['provenance_class']
  kind='RETAINED_FULL53_CONDITION'if full else'EXPLICIT_TOOL_FREE_DECISION_INTERFACE_PROJECTION'
  r['annotation_provenance']='AUTHORED_BUDGET_PROFILE_'+kind+';SOURCE='+r['source_annotation_provenance']
  r['provenance_class']=r['annotation_provenance'];r['conditioning_interface_profile']='budget_projection01'
  r['student_view']='BUDGET_PROFILE_RETAINED_CAPTURED_NATIVE53_GIVEN_STATE'if full else'EXPLICIT_DECISION_ONLY_TOOL_FREE_NOT_NATIVE_REQUEST_EQUIVALENT'
  r['budget_projection_provenance']={'kind':kind,'full53_raw_source':source_pin,'same_target_id':r['id'],
   'same_assistant_message_sha256':h(target),'full53_reference_profile':'full53','mutually_exclusive_alternative_profile':True,
   'retention_reason':reasons.get(r['id']),'not_additional_independent_target':True,'not_runtime_configuration_change':True,
   'not_asserted_lossless_transfer_or_deployment_readiness':True}
  if not full:
   assert not r['messages'][-1].get('tool_calls')and r['approved_components']==['R','D']
   r['messages'][0]['content']+='\n'+NOTE
   user=load_user(r['messages'][1]['content']);state=js(user['state'])
   user['request']=('仅依据当前资源源码、声明合同与已发生的本地CPU检查，输出条件决策JSON；这是无工具的离线判断接口，不要求改写文件或产生工具调用。'
      if r['bank']=='synthetic_cpu_resource11'else'仅依据题给状态与政策，输出下一步条件决策JSON；这是无工具的离线判断接口，不要求选择或执行工具。')
   user['conditioning_interface']='EXPLICIT_TOOL_FREE_CONDITIONAL_DECISION_NOT_NATIVE53'
   r['messages'][1]['content']=js(user);assert js(load_user(r['messages'][1]['content'])['state'])==state
   r['tools']=[];r['source_full53_schema_provenance']=r['tool_schema_provenance'];r['tool_schema_provenance']=None
  else:assert r['messages']==original_row['messages']and r['tools']==original_row['tools']
  assert js(r['messages'][-1])==target and r['id']==original_row['id'] and r['source_group_id']==original_row['source_group_id']
  assert r['loss_multiplier']==original_row['loss_multiplier']==0.05
  assert r['teacher_original_R_supervised']is False and r['actual_native_tool_dispatch']is False
  mapping.append({'id':r['id'],'case_id':r['case_id'],'bank':r['bank'],'family':r['case_family_id'],
   'view':'FULL53'if full else'DECISION_ONLY_TOOL_FREE','retention_reason':reasons.get(r['id']),
   'source_group_id':r['source_group_id'],'same_target_message_sha256':h(target),
   'source_condition_messages_sha256':h(js(original_row['messages'][:-1])),
   'new_condition_messages_sha256':h(js(r['messages'][:-1]))})
  projected.append(r)
 assert len([r for r in projected if r['tools']])==225 and len([r for r in projected if not r['tools']])==402
 raw=OUT/'CANDIDATES.raw.jsonl.gz'
 with raw.open('wb')as f:
  with gzip.GzipFile(fileobj=f,mode='wb',filename='',mtime=0)as z:
   for r in projected:z.write((js(r)+'\n').encode())
 full_report=load(FULL/'COMPILATION_REPORT.json');refs=[pin(FULL/'COMPILATION_REPORT.json'),pin(FULL/'CAUSAL_TEMPLATE.json')]
 for ref in full_report['files']:
  pp=pin(FULL/ref['path']);assert pp['sha256']==ref['sha256']and pp['bytes']==ref['bytes'];refs.append(pp)
 save('FULL53_REFERENCE.json',{'status':'UNMODIFIED_REFERENCE_PROFILE_SAME_TARGET_IDS','raw_source':source_pin,'compiled_references':refs,
  'full53_counts':full_report['counts'],'do_not_sum_alternative_profile_target_counts':True})
 save('VIEW_MAP.json',{'schema':'wrd11-same-target-mutually-exclusive-conditioning-profiles','rows':mapping,'anchors':anchors,
  'anchor_rule':'After reserving every native action and64 hard guards, select min lexicographic target ID within each remaining (bank, original family). Families already fully represented by actions need no extra D-only anchor.',
  'same_targets':627,'full53_rows':225,'tool_free_D_only_rows':402,'actions_full53':122,'hard_guards_full53':64,'additional_family_anchors_full53':39})
 save('BUILD_RECEIPT.json',{'status':'DECLARED_ALTERNATIVE_PROFILE_BUILT_PENDING_TOKEN_COMPILE_AND_DEV_COMPARISON',
  'source':source_pin,'profile_raw':pin(raw),'script_pin':pin(__file__),'base_real_main':pin(BASE),
  'same_target_ids_and_assistant_text_and_arguments':True,'same_point_time_state':True,'same_groups':True,
  'no_target_repeats_added':True,'source_full53_unchanged':pin(SOURCE)==source_pin,
  'same_targets':627,'full53_rows':225,'tool_free_D_only_rows':402,'requires_future_real_dev_comparison':True,
  'native_execution_or_training':False})
 return raw
def load_user(s):return json.loads(s)
def analyze():
 from transformers import AutoTokenizer
 from transformers.utils.chat_template_utils import _compile_jinja_template
 assets=ROOT/'output/20261025_wrd_training_preflight/tokenizer_assets'
 toks={n:AutoTokenizer.from_pretrained(assets/n,local_files_only=True,trust_remote_code=False)for n in ['primary_14b','control_8b']}
 vr=module('trusted_verify_main10_low_level',ROOT/'research/data_prep/wrd_curation10/verify_main10.py')
 report=load(COMPILED/'COMPILATION_REPORT.json');fullreport=load(FULL/'COMPILATION_REPORT.json')
 fullrows={};newrows={}
 for root,rep,dest in [(FULL,fullreport,fullrows),(COMPILED,report,newrows)]:
  for ref in rep['files']:
   pp=pin(root/ref['path']);assert pp['sha256']==ref['sha256']and pp['bytes']==ref['bytes']
   for r in rows(root/ref['path']):assert r['id']not in dest;dest[r['id']]=r
 assert set(fullrows)==set(newrows)and len(newrows)==627
 template=_compile_jinja_template(load(COMPILED/'CAUSAL_TEMPLATE.json')['variant'])
 views={r['id']:r['view']for r in load(OUT/'VIEW_MAP.json')['rows']};details=[];counts=Counter();byview=defaultdict(Counter)
 for ident,r in newrows.items():
  old=fullrows[ident];vr.verify_token_row(r,template,toks)
  assert old['messages'][-1]==r['messages'][-1]and old['source_group_id']==r['source_group_id']
  def positives(row):
   result=defaultdict(list)
   for lo,hi,component,weight in row['supervision_spans']:
    assert weight==0.05
    result[component].extend(row['input_ids'][lo:hi])
   return dict(result)
  assert positives(old)==positives(r),'POSITIVE_TARGET_TOKEN_IDS_CHANGED'
  assert old['supervised_tokens']==r['supervised_tokens']and old['supervised_tokens_by_component']==r['supervised_tokens_by_component']
  if views[ident]=='FULL53':assert r['input_ids']==old['input_ids']and r['supervision_spans']==old['supervision_spans']
  else:assert r['tools']==[]and not r['messages'][-1].get('tool_calls')
  n=len(r['input_ids']);positive=r['supervised_tokens']
  for c in [counts,byview[views[ident]]]:
   c.update(rows=1,sequence_tokens=n,positive_tokens=positive,le16k=int(n<=16384),le32k=int(n<=32768))
  details.append({'id':ident,'view':views[ident],'full53_sequence_tokens':len(old['input_ids']),'budget_sequence_tokens':n,
   'positive_tokens_same':positive,'sequence_tokens_removed':len(old['input_ids'])-n,'target_token_ids_same':True})
 oldtotal=fullreport['counts']['input_tokens'];newtotal=counts['sequence_tokens']
 assert counts['rows']==627 and counts['positive_tokens']==fullreport['counts']['supervised_tokens']==57362
 assert pin(SOURCE)['sha256']==SOURCE_SHA and pin(BASE)['sha256']==BASE_SHA
 save('ALL627_DIRECT_DUAL_TOKEN_AND_MASK_QA.json',{'status':'PASS_ALL627_BUDGET_PROFILE_DIRECT_DUAL_TOKEN_MASK_SAME_TARGET_AND_RETAINED_FULL_CONTEXT',
  'counts':dict(counts),'by_view':{k:dict(v)for k,v in byview.items()},'rows':details,
  'all627_each_direct_14B_and8B_tokenized_with_offsets':True,'every_positive_target_token_ID_by_component_identical_to_full53':True,
  'all225_retained_full53_input_IDs_and_spans_exact':True,'all122_actions_and64_hard_guards_have_full53':True,
  'constant_0_05_loss_multiplier_preserved':True,'script_pin':pin(__file__),'compiler_report_pin':pin(COMPILED/'COMPILATION_REPORT.json'),
  'no_actual_model_weights_training_or_native_calls':True,'no_model_effect_or_lossless_transfer_claim':True})
 save('COST_AND_COVERAGE_COMPARISON.json',{'status':'ACTUAL_TOKENIZER_WORKLOAD_COMPARISON_NOT_GPU_OR_QUALITY_MEASUREMENT',
  'same_targets':627,'same_positive_tokens':57362,'same_weighted_target_mass':57362*0.05,
  'full53_sequence_tokens':oldtotal,'budget_sequence_tokens':newtotal,'sequence_tokens_saved':oldtotal-newtotal,
  'sequence_token_reduction_fraction':(oldtotal-newtotal)/oldtotal,
  'full53_le16k':sum(len(r['input_ids'])<=16384 for r in fullrows.values()),'budget_le16k':counts['le16k'],
  'full53_16k_to32k':sum(16384<len(r['input_ids'])<=32768 for r in fullrows.values()),'budget_16k_to32k':counts['le32k']-counts['le16k'],
  'full53_max_sequence_tokens':max(len(r['input_ids'])for r in fullrows.values()),'budget_max_sequence_tokens':max(len(r['input_ids'])for r in newrows.values()),
  'counts_by_view':{k:dict(v)for k,v in byview.items()},
  'real_process_plus_full53_one_pass_sequence_tokens':2537926+oldtotal,
  'real_process_plus_budget_one_pass_sequence_tokens':2537926+newtotal,
  'GPU_hours_energy_quality_and_native_rollout_delta':'UNKNOWN_NOT_MEASURED',
  'interfaces_differ_for402_D_only_rows':True,'requires_real_dev_comparison':True,
  'both_profiles_are_mutually_exclusive_views_of_same_target_ids_not1254_targets':True,
  'does_not_change_native_OpenClaw_tools_or_claim_deployment_readiness':True,'training_started':False})
 print(json.dumps({'status':'PASS_BUDGET_PROFILE_ACTUAL_TOKEN_COMPARISON','full_sequence':oldtotal,'budget_sequence':newtotal,'positive':counts['positive_tokens'],'le16k':counts['le16k'],'le32k':counts['le32k']}))
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--compile',action='store_true');a=ap.parse_args()
 raw=build()
 if a.compile:
  subprocess.run([sys.executable,str(ROOT/'research/data_prep/wrd_main_v10/compile_main.py'),'--input',str(raw),'--output',str(COMPILED)],check=True)
  analyze()
