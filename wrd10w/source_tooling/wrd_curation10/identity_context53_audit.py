"""Static full53 catalog length audit, never an Agent rollout or training run.

Measures the 29 activated new-state rows and the 67 original compatible API
request inputs separately, using each real captured catalog and two actual
local HF tokenizer calls per rendered profile. No history/R truncation.
"""
from pathlib import Path
from collections import Counter
from copy import deepcopy
from array import array
import gzip,hashlib,json,os,statistics,sys,time
os.environ.update(USE_TORCH='0',USE_TF='0',CUDA_VISIBLE_DEVICES='-1',TOKENIZERS_PARALLELISM='false')
ROOT=Path('D:/skillloop');WORK=ROOT/'output/20261031_wrd_curation10';OUT=WORK/'context53_audit10'
DATA=ROOT/'output/20261027_wrd_main_v10';MAIN_SHA='9aace2dc6b39d0dde3bafbf9f7f3d6763e485609017dd70a5c40c17a2c30277e'
NEW=WORK/'compiled_combined29';API=WORK/'reasoning_native10/API67_R_A_FEEDBACK.original.audit.jsonl.gz'

def h(x):return hashlib.sha256(x if isinstance(x,bytes)else x.encode()).hexdigest()
def js(v):return json.dumps(v,ensure_ascii=False,separators=(',',':'))
def load(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def rows(p):
 with gzip.open(p,'rt',encoding='utf-8-sig')as f:
  for line in f:
   if line.strip():yield json.loads(line)
def pin(p):p=Path(p);b=p.read_bytes();return {'path':str(p),'bytes':len(b),'sha256':h(b)}
def validate(ref):
 p=Path(ref['path']);assert p.is_file()and pin(p)==ref,('PIN_CHANGED',str(p));return p
def save(name,v):(OUT/name).write_bytes((json.dumps(v,ensure_ascii=False,indent=2)+'\n').encode())
def u32sha(ids):
 a=array('I',ids)
 if sys.byteorder!='little':a.byteswap()
 return h(a.tobytes())

def normalized(messages):
 result=deepcopy(messages);projections=[]
 for i,m in enumerate(result):
  if isinstance(m.get('content'),list):
   blocks=m['content'];assert all(isinstance(b,dict)and b.get('type')=='text'and isinstance(b.get('text'),str)for b in blocks),('UNSUPPORTED_NONTEXT_CONTENT_NOT_DROPPED',i)
   m['content']='\n'.join(b['text']for b in blocks)
   projections.append({'message_index':i,'rule':'JOIN_ALL_TEXT_BLOCKS_WITH_NEWLINE','original_blocks_sha256':h(js(blocks))})
  if m.get('role')=='assistant'and not isinstance(m.get('reasoning_content'),str):
   assert m.get('reasoning_content')is None
   m['reasoning_content']=''
   projections.append({'message_index':i,'rule':'EXPLICIT_EMPTY_REASONING_IF_ABSENT_OR_NULL_PREVENT_CODE_THINK_DELIMITER_MINING'})
 return result,projections

def catalog(ref):
 p=Path(ref['path']);assert pin(p)['sha256']==ref['sha256']
 d=load(p);tools=d['tools']if isinstance(d,dict)else d
 assert isinstance(tools,list)and len(tools)==53
 names=[t['function']['name']for t in tools]
 assert len(set(names))==53 and all(t.get('type')=='function'for t in tools)
 return tools

def limits(n):
 return {'input_tokens':n,'required_context_with_8192_output':n+8192,'required_context_with_32768_output':n+32768,
  'windows':{str(window):{'fits_input':n<=window,'signed_tokens_remaining_after_input':window-n,
     'max_nonnegative_output_tokens':max(0,window-n),'can_reserve_8192_output_tokens':n+8192<=window,
     'can_reserve_32768_output_tokens':n+32768<=window}for window in [16384,32768]}}

def metric_summary(values):
 return {'count':len(values),'sum':sum(values),'min':min(values),'median':statistics.median(values),'max':max(values),
   'le16K':sum(v<=16384 for v in values),'16_to_32K':sum(16384<v<=32768 for v in values),
   'over32K':sum(v>32768 for v in values),
   'input_plus8192_le16K':sum(v+8192<=16384 for v in values),
   'input_plus8192_le32K':sum(v+8192<=32768 for v in values),
   'input_plus32768_le16K':sum(v+32768<=16384 for v in values),
   'input_plus32768_le32K':sum(v+32768<=32768 for v in values)}

def main():
 assert not OUT.exists(),'EXPLICIT_NEW_OUTPUT_ONLY'
 OUT.mkdir(parents=True);start=time.monotonic()
 mainpin=pin(DATA/'TRAINING_MANIFEST.json');assert mainpin['sha256']==MAIN_SHA
 mf=load(DATA/'TRAINING_MANIFEST.json');assert mf['actual_counts']['targets']==623 and mf['training_started']is False
 original26=ROOT/'output/20261031_wrd_curation09/eval_input_arrays09/BUILD_QA.json';evalpin=pin(original26)
 api=list(rows(API));assert len(api)==67
 nr=load(NEW/'COMPILATION_REPORT.json');new=[]
 for f in nr['files']:
  p=NEW/f['path'];assert pin(p)['sha256']==f['sha256'];new.extend(rows(p))
 assert len(new)==29
 new_by_id={r['id']:r for r in new};active={}
 for f in mf['actual_train_files']:
  p=DATA/f['path'];assert pin(p)['sha256']==f['sha256']
  for r in rows(p):
   if r['id']in new_by_id:active[r['id']]=r
 assert set(active)==set(new_by_id)
 for ident,r in active.items():
  assert r['messages']==new_by_id[ident]['messages']and r['input_ids']==new_by_id[ident]['input_ids']and r['tools']==new_by_id[ident]['tools']
 from transformers import AutoTokenizer
 from transformers.utils.chat_template_utils import _compile_jinja_template
 assets=ROOT/'output/20261025_wrd_training_preflight/tokenizer_assets'
 tokenizers={name:AutoTokenizer.from_pretrained(assets/name,local_files_only=True,trust_remote_code=False)for name in ['primary_14b','control_8b']}
 variant=load(NEW/'CAUSAL_TEMPLATE.json')['variant'];render=_compile_jinja_template(variant)
 for t in tokenizers.values():
  expected=t.chat_template.replace('{%- if loop.index0 > ns.last_query_index %}','{%- if true %}')
  expected=expected.replace('{%- if loop.last or (not loop.last and reasoning_content) %}','{%- if true %}')
  expected=expected.replace("reasoning_content.strip('\\n')",'reasoning_content').replace("content.lstrip('\\n')",'content')
  assert expected==variant
 calls=Counter()
 def measure(messages,tools,generation,thinking):
  renderings={};encoded={}
  for name,t in tokenizers.items():
   text=render.render(messages=messages,tools=tools,documents=None,add_generation_prompt=generation,
        **dict(t.special_tokens_map,enable_thinking=thinking))
   renderings[name]=text;encoded[name]=t(text,add_special_tokens=False)['input_ids'];calls[name]+=1
  assert renderings['primary_14b']==renderings['control_8b']and encoded['primary_14b']==encoded['control_8b']
  return {'tokens':len(encoded['primary_14b']),'rendered_utf8_sha256':h(renderings['primary_14b']),
    'primary14_input_ids_u32le_sha256':u32sha(encoded['primary_14b']),
    'control8_input_ids_u32le_sha256':u32sha(encoded['control_8b']),
    'independent_tokenizer_calls_equal':True},renderings['primary_14b']
 new_audit=[]
 for r in new:
  m=r['original_record_metadata'];ref=m['tool_schema_provenance'];full=catalog(ref)
  reg={t['function']['name']:t for t in full}
  assert all(t==reg[t['function']['name']]for t in r['tools'])
  msgs,projection=normalized(r['messages']);targets=[t['message_index']for t in r['targets']if t['supervised_tokens']]
  assert len(targets)==1 and targets[0]==len(msgs)-1 and msgs[-1]['role']=='assistant'
  inp,header=measure(msgs[:-1],full,True,True)
  closed,closed_text=measure(msgs[:-1],full,True,False)
  complete,complete_text=measure(msgs,full,False,False)
  core_in,core_text=measure(msgs[:-1],r['tools'],True,True)
  assert complete_text.startswith(header),'HEADER_INPUT_MUST_BE_LITERAL_PREFIX_OF_COMPLETE_TARGET'
  assert closed_text!=header and closed_text.startswith(header)
  # Full53 changes only the public tool catalog. Past and current messages,
  # complete recorded R (including zero-loss portions) and full target remain.
  new_audit.append({'id':r['id'],'bank':r['bank'],'source_ids':r['source_ids'],
    'scope':'COUNTERFACTUAL_FULL53_CATALOG_PROFILE_OF_CURRENT_NEW_STATE_NOT_ORIGINAL_NATIVE_REQUEST',
    'catalog_provenance':ref,'catalog_tools':53,'catalog_sha256':h(js(full)),
    'actual_core_tool_count':len(r['tools']),'core7_compiled_complete_tokens':r['total_tokens'],
    'core7_header_input_profile':core_in,
    'full53_header_input_profile':{**inp,**limits(inp['tokens'])},
    'full53_empty_think_prefill_input_profile':{**closed,**limits(closed['tokens'])},
    'full53_complete_target_profile':{**complete,'le16K':complete['tokens']<=16384,'le32K':complete['tokens']<=32768,
       'difference_from_original_compiled_core_catalog':complete['tokens']-r['total_tokens']},
    'header_input_is_exact_rendered_complete_target_prefix':True,
    'empty_think_prefill_is_alternative_input_profile_not_claimed_as_nonempty_R_target_prefix':True,
    'full_past_and_target_preserved':True,'complete_current_target_R_characters':len(msgs[-1].get('reasoning_content','')),
    'text_block_projection':projection,'labels_created':False,'rollout_or_inference_executed':False})
 original=[]
 for a in api:
  ref=a['source_compatible_API_request'];p=validate(ref);request=load(p)
  tools=request['tools'];assert len(tools)==53 and len({t['function']['name']for t in tools})==53
  assert request['messages']==a['compatible_request_messages_original']and tools==a['compatible_request_tools_original']
  msgs,projection=normalized(request['messages'])
  inp,_=measure(msgs,tools,True,True);closed,_=measure(msgs,tools,True,False)
  original.append({'episode_id':a['episode_id'],'stage':a['stage'],'call_id':a['call_id'],'response_id':a['response_id'],
    'scope':'QWEN_CAUSAL_TEMPLATE_RERENDER_OF_ORIGINAL_COMPATIBLE_REQUEST_INPUT_NOT_TEACHER_USAGE_OR_EXECUTION',
    'source_request':ref,'original_message_count':len(request['messages']),'catalog_tools':53,'catalog_sha256':h(js(tools)),
    'input_profile':{**inp,**limits(inp['tokens'])},'empty_think_prefill_input_profile':{**closed,**limits(closed['tokens'])},
    'all_original_past_explicit_R_characters':sum(len(m.get('reasoning_content',''))for m in msgs if m.get('role')=='assistant'),
    'text_block_projection':projection,'no_current_response_added':True,'no_original_past_or_R_truncated':True,
    'not_billed_teacher_tokens':True,'new_inference_or_rollout_executed':False})
 save('NEW29_FULL53_STATIC_PROFILES.json',{'status':'PASS_DUAL_TOKENIZER_FULL29_STATIC_CATALOG_PROFILE_ONLY','rows':new_audit})
 save('ORIGINAL67_FULL53_INPUT_PROFILES.json',{'status':'PASS_DUAL_TOKENIZER_ORIGINAL67_INPUT_RERENDER_ONLY','rows':original})
 def bins(rr,inputkey):return metric_summary([r[inputkey]['tokens']for r in rr])
 summary={'status':'PASS_FULL53_STATIC_CONTEXT_AUDIT_NO_EXECUTION_OR_DATA_CHANGE','main_manifest':mainpin,
    'main_targets_unchanged':623,'new29_rows_are_already_activated_not_additional_training_samples':True,
    'new29':{'rows':29,'core_catalog_compiled_complete':metric_summary([r['total_tokens']for r in new]),
      'core_catalog_header_input':bins(new_audit,'core7_header_input_profile'),
      'full53_header_input':bins(new_audit,'full53_header_input_profile'),
      'full53_empty_think_prefill_input':bins(new_audit,'full53_empty_think_prefill_input_profile'),
      'full53_complete_target':bins(new_audit,'full53_complete_target_profile'),
      'by_bank':{bank:{'rows':sum(r['bank']==bank for r in new_audit),
          'full53_input':bins([r for r in new_audit if r['bank']==bank],'full53_header_input_profile'),
          'full53_complete':bins([r for r in new_audit if r['bank']==bank],'full53_complete_target_profile')}
          for bank in sorted({r['bank']for r in new_audit})}},
    'original67':{'rows':67,'full53_header_input':bins(original,'input_profile'),
       'full53_empty_think_prefill_input':bins(original,'empty_think_prefill_input_profile'),
       'by_stage':{stage:{'rows':sum(r['stage']==stage for r in original),
           'full53_input':bins([r for r in original if r['stage']==stage],'input_profile')}
           for stage in sorted({r['stage']for r in original})}},
    'model_tokenizer_calls':dict(calls),'each_render_separately_tokenized_for_both_models':True,
    'no_tokenizer_ID_reuse_in_place_of_control_model_call':True,
    'main_profile':'Qwen causal variant; input add_generation_prompt=True, enable_thinking=True gives assistant-header prefix. Full target has all R and uses same variant.',
    'secondary_profile':'enable_thinking=False adds empty think prefill. It is measured separately and is not asserted to be the same prefix as a target with nonempty R.',
    'window_budgets_checked':[16384,32768],'output_reservations_checked':[8192,32768],
    'required_context_lengths_are_arithmetic_not_64K_or_128K_readiness':True,
    'original_teacher_API_token_metering_not_replaced_or_reestimated':True,
    'P4_parent_inputs_not_measured_as_native_prompt':'Parent input bundles are not captured native system/tool/past requests; this optional extension was not simulated.',
    'prior26_component_eval_full53_QA_unchanged':evalpin,
    'prior26_full53_initial_26671_to29576_not_reinterpreted_as_rollout_pass':True,
    'dynamic_future_rollout_lengths_unknown':True,'native_full53_rollout_passed_by_this_audit':False,
    'model_weights_loaded':False,'new_forward_or_backward_or_training':False,'new_Agent_or_business_calls':0,
    'elapsed_CPU_audit_seconds':time.monotonic()-start,'script':pin(__file__)}
 assert pin(DATA/'TRAINING_MANIFEST.json')==mainpin and pin(original26)==evalpin
 save('CONTEXT53_STATIC_AUDIT_QA.json',summary)
 print(js({'status':summary['status'],'new29':{k:v for k,v in summary['new29'].items()if k!='by_bank'},
    'original67':summary['original67']['full53_header_input'],'tokenizer_calls':dict(calls),'main_623_unchanged':True}))

if __name__=='__main__':main()
