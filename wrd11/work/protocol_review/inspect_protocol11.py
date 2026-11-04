"""Offline captured-native ABI and tokenizer-only length review.

No agent loop, tool invocation, model weights, training or business annotation.
Only technical tool definitions are exported from captured requests.
"""
from pathlib import Path
from array import array
from collections import Counter
import gzip, hashlib, json, os, sys
os.environ.update(USE_TORCH='0',USE_TF='0',CUDA_VISIBLE_DEVICES='-1',TOKENIZERS_PARALLELISM='false')
sys.dont_write_bytecode=True
ROOT=Path('D:/skillloop')
OUT=ROOT/'output/20261031_wrd_curation11/protocol_review'
CAPTURE=ROOT/'output/20261027_wrd_main_v10/historical_v6_native_repair_01/TOOLS_CAPTURE_53.json'
CAPTURE_SHA='a47db18b7c6bafcfddfe4bce79ae68787303320225a1edf99457720ee1622345'
TEMPLATE=ROOT/'output/20261031_wrd_curation10/compiled_combined29/CAUSAL_TEMPLATE.json'
PARENTS=['agents_list','sessions_spawn','subagents','agents_wait','sessions_yield','sessions_list','sessions_history','sessions_send']
CORE={'ls','read','write','edit','apply_patch','exec','process'}

def js(x):return json.dumps(x,ensure_ascii=False,separators=(',',':'))
def h(x):return hashlib.sha256(x if isinstance(x,bytes) else x.encode()).hexdigest()
def load(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def pin(p):
 p=Path(p);return {'path':str(p.resolve()),'bytes':p.stat().st_size,'sha256':h(p.read_bytes())}
def save(name,x):
 p=OUT/name;assert not p.exists();p.parent.mkdir(parents=True,exist_ok=True)
 p.write_bytes((json.dumps(x,ensure_ascii=False,indent=2)+'\n').encode())
 return pin(p)
def rows(p):
 with gzip.open(p,'rt',encoding='utf-8-sig')as f:
  for l in f:
   if l.strip():yield json.loads(l)
def ids_sha(ids):
 a=array('I',ids)
 if sys.byteorder!='little':a.byteswap()
 return h(a.tobytes())

def main():
 assert h(CAPTURE.read_bytes())==CAPTURE_SHA
 cap=load(CAPTURE);tools=cap['tools'];assert len(tools)==53
 names=[t['function']['name']for t in tools];assert len(set(names))==53
 registry={t['function']['name']:t for t in tools};schema_sha=h(js(tools))
 original=cap['original_capture'];p=Path(original['path']);assert pin(p)==original
 assert load(p)['tools']==tools
 technical=[]
 technical.append(save('OPENCLAW_TOOLS53.json',tools))
 technical.append(save('CHILD_ORCHESTRATION_TOOLS.json',[registry[n]for n in PARENTS]))
 infos=[]
 for n,t in registry.items():
  s=t['function']['parameters'];infos.append({'name':n,'canonical_UTF8_bytes':len(js(t).encode()),'canonical_sha256':h(js(t)),
    'required':s.get('required',[]),'properties':list(s.get('properties',{})),
    'additionalProperties':s.get('additionalProperties','JSON_SCHEMA_DEFAULT_TRUE')})
 for n in PARENTS:technical.append(save('tools/'+n+'.json',registry[n]))
 catalog_owners=[];fingerprints=Counter()
 packet=ROOT/'output/20261031_wrd_curation10/reasoning_native10/API67_R_A_FEEDBACK.original.audit.jsonl.gz'
 for r in rows(packet):
  ref=r['source_compatible_API_request'];rp=Path(ref['path']);assert pin(rp)==ref
  rt=load(rp)['tools'];assert len(rt)==53 and len({x['function']['name']for x in rt})==53
  fp=h(js(rt));fingerprints[fp]+=1
  catalog_owners.append({'request_pin':ref,'tool_count':len(rt),'canonical_tools_sha256':fp,'equals_exported_tools53':rt==tools})
 assert len(catalog_owners)==67
 technical.append(save('CAPTURED67_CATALOG_PINS.json',{'scope':'TECHNICAL_TOOL_DEFINITIONS_ONLY_NO_MESSAGE_TEXT_EXPORTED','request_catalogs':catalog_owners,'unique_catalog_fingerprints':dict(fingerprints)}))
 from jsonschema import Draft202012Validator
 for t in tools:Draft202012Validator.check_schema(t['function']['parameters'])
 examples={
  'agents_list':{},
  'sessions_spawn':{'task':'Read the commissioned resource state, verify one bounded component, and return evidence paths without publishing or training.',
    'taskName':'resource_qa','runtime':'subagent','context':'isolated','visible':False,'cleanup':'keep','runTimeoutSeconds':120,'completionTarget':'parent'},
  'subagents':{'action':'wait','taskIds':['synthetic_pending_run_01'],'timeoutSeconds':30},
  'agents_wait':{'ids':['synthetic_collector_01'],'timeoutSeconds':30},
  'sessions_yield':{'waitFor':'message','message':'Offline example: unfinished delegated check is still pending.'},
  'sessions_list':{'limit':20,'excludeSubagents':False},
  'sessions_history':{'sessionKey':'synthetic_visible_child','includeTools':True,'limit':20},
  'sessions_send':{'sessionKey':'synthetic_visible_child','message':'Offline example continuation; no message is sent.','mode':'followup'},
 }
 for n,args in examples.items():assert not list(Draft202012Validator(registry[n]['function']['parameters']).iter_errors(args))
 negatives=[('sessions_spawn',{}),('sessions_spawn',{'task':'x','runtime':'custom_loop'}),
   ('subagents',{'action':'dispatch'}),('subagents',{'action':'wait','timeoutSeconds':61}),
   ('subagents',{'action':'wait','taskIds':['x']*33}),('agents_wait',{'ids':[]}),
   ('sessions_yield',{'waitFor':'tool'}),('sessions_history',{})]
 for n,args in negatives:assert list(Draft202012Validator(registry[n]['function']['parameters']).iter_errors(args))
 technical.append(save('ABI_OFFLINE_VALIDATION.json',{'status':'PASS_OFFLINE_JSON_SCHEMA_ONLY_NOT_HANDLER_EXECUTION',
   'positive_schema_examples':examples,'negative_schema_cases_rejected':len(negatives),
   'synthetic_IDs_are_not_real_receipts':True,'none_of_these_calls_were_executed':True}))
 from transformers import AutoTokenizer
 from transformers.utils.chat_template_utils import _compile_jinja_template
 assets=ROOT/'output/20261025_wrd_training_preflight/tokenizer_assets'
 tokenizers={n:AutoTokenizer.from_pretrained(assets/n,local_files_only=True,trust_remote_code=False)for n in ['primary_14b','control_8b']}
 variant=load(TEMPLATE)['variant'];render=_compile_jinja_template(variant)
 for t in tokenizers.values():
  expected=t.chat_template.replace('{%- if loop.index0 > ns.last_query_index %}','{%- if true %}')
  expected=expected.replace('{%- if loop.last or (not loop.last and reasoning_content) %}','{%- if true %}')
  expected=expected.replace("reasoning_content.strip('\\n')",'reasoning_content').replace("content.lstrip('\\n')",'content')
  assert variant==expected
 system='You are a workflow-reuse assistant. Use only the supplied point-time state. Synthetic annotation; no tools have actually run.'
 state={'kind':'offline_synthetic_point_time_state','phase':'B','remaining_wall_seconds':180,'delegated_resource_check_pending':False,
  'source_scope':'PUBLIC_NEW_FIXTURE','ready_for_component_QA':True,'business_quality_unknown':True}
 profiles=[];calls=Counter()
 for name,user in [('minimal','Select one next step from the supplied state.'),('short_state',js(state)),
   ('short_state_with_1500_probe_chars',js({**state,'length_probe_not_training_example':'示例状态只用于长度测量。'*150})),
   ('short_state_with_4500_probe_chars',js({**state,'length_probe_not_training_example':'示例状态只用于长度测量。'*450}))]:
  msgs=[{'role':'system','content':system},{'role':'user','content':user}]
  target={'role':'assistant','reasoning_content':'The resource check has not run. Delegate a bounded isolated component check and preserve its evidence; do not claim business utility.',
   'content':'','tool_calls':[{'id':'synthetic_offline_call_01','type':'function','function':{'name':'sessions_spawn','arguments':examples['sessions_spawn']}}]}
  for catalog_name,ts in [('core7_declared_projection',[t for t in tools if t['function']['name']in CORE]),('captured_full53',tools)]:
   entry={'profile':name,'catalog':catalog_name,'user_chars':len(user),'input_and_target_are_synthetic_length_probes_not_training_data':True}
   for kind,ms,gen in [('input',msgs,True),('complete',msgs+[target],False)]:
    ids={};texts={}
    for model,t in tokenizers.items():
     text=render.render(messages=ms,tools=ts,documents=None,add_generation_prompt=gen,**dict(t.special_tokens_map,enable_thinking=True))
     texts[model]=text;ids[model]=t(text,add_special_tokens=False)['input_ids'];calls[model]+=1
    assert texts['primary_14b']==texts['control_8b'] and ids['primary_14b']==ids['control_8b']
    n=len(ids['primary_14b']);entry[kind]={'tokens':n,'le31000':n<=31000,'le32768':n<=32768,'rendered_utf8_sha256':h(texts['primary_14b']),
     'primary14_ids_u32le_sha256':ids_sha(ids['primary_14b']),'control8_ids_u32le_sha256':ids_sha(ids['control_8b'])}
    if kind=='input':entry[kind].update(remaining_at_31000=31000-n,remaining_at_32768=32768-n,can_reserve8192_at_32768=n+8192<=32768)
   profiles.append(entry)
 technical.append(save('SYNTHETIC_SHORT_STATE_STATIC_PROFILES.json',{'status':'PASS_ACTUAL_DUAL_HF_TOKENIZERS_STATIC_PROFILES_ONLY','profiles':profiles,'calls_per_model':dict(calls)}))
 summary={'schema':'wrd-curation11-captured-native-protocol-review-v1','status':'PASS_OFFLINE_CAPTURED_ABI_AND_STATIC_LENGTH_REVIEW',
  'source_capture':pin(CAPTURE),'original_request_capture':original,
  'native_image':cap['native_image'],'openclaw_version':cap['openclaw_version'],
  'captured_version_not_asserted_as_live_runtime_probed':True,'tools_count':53,'tool_names_in_captured_order':names,
  'canonical_tools_sha256':schema_sha,'canonical_tools_UTF8_bytes':len(js(tools).encode()),
  'captured67_technical_catalog_count':len(catalog_owners),'captured67_unique_catalogs':dict(fingerprints),
  'all67_equal_exported_catalog':all(x['equals_exported_tools53']for x in catalog_owners),
  'orchestration_tools':PARENTS,'tool_information':infos,'technical_exports':technical,
  'template_pin':pin(TEMPLATE),'tokenizer_only_calls_per_model':dict(calls),
  'initial_probe_failure':'First one-off read_text used host gbk default; rerun script uses explicit utf-8-sig throughout; no data changed.',
  'schema_examples_not_real_tool_history':True,'actual_native_calls':0,'actual_model_forward_or_training':0,
  'protected_enterprise_messages_not_exported':True,'new_TRAIN_source_admissions':0,
  'semantic_constraints_beyond_JSON_schema':[
   'Use native sessions_spawn/subagents/agents_wait/sessions_yield names; never fabricate dispatch/agent-loop tools.',
   'Default internal work is a hidden child; visible true requires explicit separate-session intent.',
   'For one/few children use ordinary spawn; collectors are for large fan-out and require agents_wait, not notification waiting.',
   'Keep captured fixed model/runtime; omit model/agentId overrides unless corresponding session configuration is actually known.',
   'context fork requires same-agent parent transcript and could inherit protected material; isolated is safer for new public fixtures.',
   'A positive bounded runTimeoutSeconds must fit the remaining native budget; zero disables the timeout.',
   'Nonempty attachments are unsupported in this captured native tool; do not invent an inline skills injection mechanism.',
   'Omit unsupported semantic combinations even where JSON Schema permits unknown fields or lacks conditionals.',
   'A synthetic taskId/sessionKey is an explicit hypothetical identifier, never a recovered actual dispatch receipt.',
   'Native tool names/parameters in offline targets do not prove discovery, handler acceptance, hard-budget wiring or rollout success.'
  ],'script_pin':pin(__file__),'training_started':False,'model_weights_loaded':False}
 save('PROTOCOL_AND_SOURCE_PINS11.json',summary)
 print(json.dumps({'status':summary['status'],'tool_count':53,'all67_same':summary['all67_equal_exported_catalog'],'calls':dict(calls)}))

if __name__=='__main__':main()
