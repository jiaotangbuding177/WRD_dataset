"""Independent all-row dual-HF, exact mask and source QA for authored WRD11.

Tokenizer assets only; no weights, torch, native session, tool dispatch or
training. This is separate from the compiler's sparse control-tokenizer calls.
"""
from pathlib import Path
from collections import Counter,defaultdict
from copy import deepcopy
from array import array
import argparse,gzip,hashlib,importlib.util,json,os,sys,time
os.environ.update(CUDA_VISIBLE_DEVICES='-1',USE_TORCH='0',USE_TF='0',TOKENIZERS_PARALLELISM='false')
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[3]
WORK=ROOT/'output/20261031_wrd_curation11'
MAIN=ROOT/'output/20261027_wrd_main_v10/TRAINING_MANIFEST.json'
MAIN_SHA='9aace2dc6b39d0dde3bafbf9f7f3d6763e485609017dd70a5c40c17a2c30277e'
HEADER='<|im_start|>assistant\n';THINK='<think>\n';CLOSE='\n</think>\n\n';END='<|im_end|>\n'

def hs(x):return hashlib.sha256(x if isinstance(x,bytes) else x.encode()).hexdigest()
def digest(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def load(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def js(x):return json.dumps(x,ensure_ascii=False,separators=(',',':'))
def canonical(x):return json.dumps(x,ensure_ascii=False,separators=(',',':'),sort_keys=True)
def save(p,x):
 p.parent.mkdir(parents=True,exist_ok=True);assert not p.exists(),'PRESERVE_PRIOR_QA'
 p.write_bytes((json.dumps(x,ensure_ascii=False,indent=2)+'\n').encode())
def pin(p):return {'path':str(Path(p).resolve()),'bytes':Path(p).stat().st_size,'sha256':digest(p)}
def checkpin(ref):
 p=Path(ref['path']);assert p.is_file() and p.stat().st_size==ref['bytes'] and digest(p)==ref['sha256'],'SOURCE_PIN_MISMATCH'
 return p
def rows(p):
 op=gzip.open if str(p).endswith('.gz') else open
 with op(p,'rt',encoding='utf-8-sig') as f:
  for line in f:
   if line.strip():yield json.loads(line)
def module(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def idsha(ids):
 a=array('I',ids)
 if sys.byteorder!='little':a.byteswap()
 return hs(a.tobytes())


class CountTokenizer:
 def __init__(self,tok):self.tok=tok;self.calls=0;self.last=None;self.last_text=None
 @property
 def special_tokens_map(self):return self.tok.special_tokens_map
 def __call__(self,text,**kwargs):
  self.calls+=1;self.last_text=text;self.last=self.tok(text,**kwargs);return self.last
 def decode(self,*args,**kwargs):return self.tok.decode(*args,**kwargs)


def geometry(row,text,offsets):
 """Rebuild positive positions from raw assistant fields and fresh offsets."""
 assert len(row['targets'])==1 and len(row['messages'])==3
 target=row['targets'][0];assert target['message_index']==2
 a,b=target['rendered_assistant_span'];m=row['messages'][2]
 assert text[a:b].startswith(HEADER) and text[a:b].endswith(END)
 r=m.get('reasoning_content','');d=m.get('content','')
 start=a+len(HEADER);assert text[start:].startswith(THINK+r+CLOSE+d)
 ra=start+len(THINK);rb=ra+len(r);da=rb+len(CLOSE);db=da+len(d);end=b-len(END)
 bounds=[]
 if r:bounds.append((ra,rb,'R'))
 if d:bounds.append((da,db,'E' if m.get('tool_calls') else 'D'))
 if m.get('tool_calls'):
  assert not d,'SYNTHETIC_ACTION_SHOULD_NOT_MIX_PUBLIC_DECISION_CONTENT'
  assert text[db:end].startswith('<tool_call>\n') and text[db:end].endswith('</tool_call>')
  bounds.append((db,end,'A'))
 else:assert db==end
 approved=set(row['original_record_metadata']['approved_components'])
 assert approved==({'R','A'} if m.get('tool_calls') else {'R','D'})
 expected=[None]*len(offsets)
 for i,(s,e) in enumerate(offsets):
  matches=[c for x,y,c in bounds if x<=s<e<=y and c in approved]
  assert len(matches)<=1
  if matches:expected[i]=matches[0]
 actual=[None]*len(offsets);counts=Counter();last=0
 for lo,hi,c,w in row['supervision_spans']:
  assert type(lo) is int and type(hi) is int and 0<=lo<hi<=len(actual) and lo>=last
  assert c in {'R','A','D'} and type(w) is float and w==0.05
  last=hi
  for i in range(lo,hi):assert actual[i] is None;actual[i]=c;counts[c]+=1
 assert actual==expected,'INDEPENDENT_OFFSET_MASK_COMPONENT_MISMATCH'
 assert dict(counts)==row['supervised_tokens_by_component']
 assert sum(counts.values())==row['supervised_tokens']==target['supervised_tokens']
 assert target['owned_supervision_spans']==row['supervision_spans']
 assert idsha(row['input_ids'])==row['input_ids_sha256_u32le']
 assert hs(js(row['supervision_spans']))==row['supervision_spans_sha256']
 for i,(s,e) in enumerate(offsets):
  if actual[i]:assert a+len(HEADER)<=s<e<=end
 assert all(x is None for x,(s,e) in zip(actual,offsets) if e<=a+len(HEADER))
 return counts


def sanitized_cpu_state(case):
 s=deepcopy(case['point_time_state'])
 def walk(x):
  if isinstance(x,dict):
   for k,v in list(x.items()):
    if k=='path' and isinstance(v,str) and (':\\' in v or v.startswith('D:/')):x[k]='external_cpu_audit/'+Path(v).name
    else:walk(v)
  elif isinstance(x,list):
   for v in x:walk(v)
 walk(s);s['current_version']='revision_'+s['resource_file']['sha256'][:12]
 return s


def no_audit_payload_in_state(state):
 forbidden={'target','rejected_alternative','future_same_input_credit_evidence','validation','expected_decision'}
 def walk(x):
  if isinstance(x,dict):
   assert not set(x)&forbidden,'AUDIT_OR_FUTURE_LABEL_IN_STATE'
   for v in x.values():walk(v)
  elif isinstance(x,list):
   for v in x:walk(v)
 walk(state)


def main(a):
 started=time.perf_counter();assert not a.out.exists() or not any(a.out.iterdir())
 assert digest(MAIN)==MAIN_SHA,'ORIGINAL623_MAIN_CHANGED'
 report=load(a.compiled/'COMPILATION_REPORT.json');template_meta=load(a.compiled/'CAUSAL_TEMPLATE.json')
 assert report['counts']['sequences']==627 and report['counts']['supervised_tokens']==57362
 assert report['counts']['input_tokens']==16929495
 raw_path=checkpin(report['immutable_inputs'][0]);raw={r['id']:r for r in rows(raw_path)};assert len(raw)==627
 conversion=load(raw_path.parent/'CONVERSION_RECEIPT.json')
 assert checkpin(conversion['raw_candidate_pin'])==raw_path
 selected={m['record_id']:m for m in conversion['mapping'] if m['selected']}
 assert set(selected)==set(raw)
 sourcecases={};sourcepins=[]
 for p in conversion['source_case_pins']:
  path=checkpin(p);sourcepins.append(p)
  for c in rows(path):assert c['id'] not in sourcecases;sourcecases[c['id']]=c
 tools_path=checkpin(conversion['catalog_pin']);tools=load(tools_path)['tools']
 assert len(tools)==53 and len({x['function']['name'] for x in tools})==53
 protocol=load(WORK/'protocol_review/PROTOCOL_AND_SOURCE_PINS11.json')
 cap=load(checkpin(protocol['source_capture']));req=load(checkpin(protocol['original_request_capture']))
 assert tools==cap['tools']==req['tools'],'FULL53_SCHEMA_NOT_IDENTICAL_TO_REAL_CAPTURE'
 registry={x['function']['name']:x['function'] for x in tools}
 from transformers import AutoTokenizer
 from transformers.utils.chat_template_utils import _compile_jinja_template
 from jsonschema import Draft202012Validator
 tokenizer_pins={}
 for name,assets in report['tokenizer_proof']['asset_sha256'].items():
  for filename,expected in assets.items():assert digest(a.assets/name/filename)==expected
  tokenizer_pins[name]={n:pin(a.assets/name/n) for n in assets}
 toks={n:CountTokenizer(AutoTokenizer.from_pretrained(a.assets/n,local_files_only=True,trust_remote_code=False)) for n in ['primary_14b','control_8b']}
 template=_compile_jinja_template(template_meta['variant'])
 audit=module('independent_existing_mask_and_token_audit10',ROOT/'research/data_prep/wrd_curation10/verify_main10.py')
 all_counts=Counter();by_bank=defaultdict(Counter);by_stage=defaultdict(Counter);tool_counts=Counter();seen=set();inputs={};lengths=[];details=[]
 first_row=None;source_checks=Counter()
 for ref in report['files']:
  file=a.compiled/ref['path'];assert digest(file)==ref['sha256'] and file.stat().st_size==ref['bytes']
  for row in rows(file):
   assert row['id'] not in seen;seen.add(row['id']);original=raw[row['id']];meta=row['original_record_metadata']
   assert row['messages']==original['messages'] and row['tools']==original['tools']==tools
   assert meta=={k:v for k,v in original.items() if k not in {'messages','tools'}}
   assert row['source_ids']==meta['source_ids']==[] and row['split']=='train'
   assert meta['teacher_original_R_supervised'] is False and meta['original_R_provenance']=='NONE_NEW_AUTHOR_AUDITABLE_RATIONALE'
   assert meta['actual_native_tool_dispatch'] is False and meta['real_qualified_KEEP_supported'] is False
   assert meta['is_original_native_request_identical'] is False and row['is_full_autonomous_execution_demonstration'] is False
   assert meta['model_weights_loaded'] is False and meta['training_started'] is False
   assert meta['loss_multiplier']==0.05 and meta['message_loss_mask']==[0,0,1] and meta['supervision_message_indices']==[2]
   assert meta['root_main_admission'] is False and meta['requires_external_root_admission'] is True
   assert [m['role'] for m in row['messages']]==['system','user','assistant'],'FAKE_OR_HISTORICAL_TOOL_MESSAGE_IN_SYNTHETIC_CASE'
   assert all(m['role']!='tool' for m in row['messages'])
   assert meta['tool_schema_provenance']==conversion['catalog_pin']
   source=sourcecases[meta['case_id']];assert source['enterprise_source_ids']==[] and source['provenance']['recorded_teacher_R'] is False
   assert meta['case_source_pin'] in sourcepins and meta['source_group_id']==source['synthetic_root_id']
   assert row['id']=='sft11-'+hs(source['id'])[:24]
   user=json.loads(row['messages'][1]['content']);assert set(user)=={'request','evidence_kind','case_alias','state'}
   no_audit_payload_in_state(user['state'])
   assert user['case_alias']==hs(source['id'])[:16]
   if row['bank']=='synthetic_cpu_resource11':
    assert user['state']==sanitized_cpu_state(source)
    assert 'CPU' in row['messages'][0]['content'] and 'NOT_NATIVE' in user['evidence_kind']
    if source['target'].get('resource_action_projection'):
     assert 'write' in user['request'];assert selected[row['id']]['request_kind']=='WRITE_REPAIR'
    else:assert selected[row['id']]['request_kind']=='DECISION_ONLY'
   else:
    assert user['state']==source['point_time_state'] and 'GIVEN_POLICY' in user['evidence_kind']
   assistant=row['messages'][2];corrected=meta.get('curator_rationale_correction')
   if corrected:
    assert hs(source['target']['R'])==corrected['old_R_sha256']
    assert hs(assistant['reasoning_content'])==corrected['new_R_sha256']
    assert selected[row['id']]['rationale_correction']==corrected
   else:assert assistant['reasoning_content']==source['target']['R']
   calls=assistant.get('tool_calls',[])
   if calls:
    assert len(calls)==1 and not assistant['content'];call=calls[0];fn=call['function'];args=fn['arguments']
    assert fn['name'] in registry and not list(Draft202012Validator(registry[fn['name']]['parameters']).iter_errors(args))
    if row['bank']=='synthetic_cpu_resource11':
     projection=source['target']['resource_action_projection']
     assert fn['name']=='write' and args=={'path':projection['path'],'content':projection['content']}
     assert hs(args['content'])==projection['content_sha256']
    else:assert fn==source['target']['native_tool_intent']
    tool_counts[fn['name']]+=1
   else:
    expected=deepcopy(source['target']['D']);expected.update(evidence_origin=user['evidence_kind'],real_skill_qualified_claim=False)
    assert json.loads(assistant['content'])==expected
   normalized=deepcopy(user);normalized.pop('case_alias')
   key=hs(canonical({'system':row['messages'][0]['content'],'user':normalized,'tools':tools}))
   value=hs(canonical(assistant));assert key not in inputs or inputs[key]==value,'CONFLICTING_TARGET_AFTER_ALIAS_REMOVAL'
   inputs[key]=value
   count,excluded=audit.verify_token_row(row,template,toks)
   assert count==len(row['input_ids'])==row['total_tokens']<=32768
   assert excluded==0 and not meta.get('target_excluded_rendered_ranges')
   component=geometry(row,toks['primary_14b'].last_text,toks['primary_14b'].last['offset_mapping'])
   assert toks['primary_14b'].last==toks['control_8b'].last
   assert row['view'] if False else True  # No prefix view is accepted below.
   assert row.get('view')!='EXACT_TOKEN_PREFIX_OMITTING_ONLY_UNSUPERVISED_FUTURE_COMPLETION'
   for counter in [all_counts,by_bank[row['bank']],by_stage[row['stage']]]:
    counter.update(sequences=1,targets=1,input_tokens=count,supervised_tokens=sum(component.values()),
                   le16k=int(count<=16384),le32k=int(count<=32768))
    for c,n in component.items():counter['component_'+c]+=n
   source_checks.update(case_rows=1,source_fields_preserved=1,source_provenance_new=1,actual_native_tool_returns=0)
   lengths.append(count);details.append({'id':row['id'],'bank':row['bank'],'stage':row['stage'],'total_tokens':count,
       'positive_tokens':sum(component.values()),'components':dict(component),'calls':[c['function']['name'] for c in calls],
       'source_case_id':meta['case_id'],'source_group_id':row['source_group_id'],'render_sha':row['rendered_sha256']})
   if first_row is None:first_row=deepcopy(row)
   if len(seen)%100==0:print(json.dumps({'fresh_dual_tokenized_rows':len(seen),'expected_rows':627}),flush=True)
 assert seen==set(raw) and len(seen)==627
 assert all_counts['input_tokens']==16929495 and all_counts['supervised_tokens']==57362
 assert {k:all_counts['component_'+k] for k in ['R','A','D']}=={'R':19656,'A':8966,'D':28740}
 # Meaningful negative canary uses the actual first synthetic row, not fixture
 # implementation mirroring. The unchanged audit must reject prompt loss.
 calls_before={n:t.calls for n,t in toks.items()}
 canary=deepcopy(first_row);canary['supervision_spans'].insert(0,[0,1,'A',0.05])
 try:audit.verify_token_row(canary,template,toks)
 except AssertionError as e:
  assert str(e)=='INPUT_OR_ROLE_HEADER_HAS_LOSS';negative='REJECTED_'+str(e)
 else:raise AssertionError('PROMPT_LOSS_NEGATIVE_NOT_REJECTED')
 assert calls_before=={'primary_14b':627,'control_8b':627}
 assert digest(MAIN)==MAIN_SHA and 'torch' not in sys.modules
 a.out.mkdir(parents=True,exist_ok=True)
 save(a.out/'ALL627_ROW_DETAILS.json',{'rows':details})
 result={'schema':'wrd11-independent-all627-synthetic-token-mask-source-QA',
  'status':'PASS_ALL627_FRESH_DUAL_HF_EXACT_MASK_NATIVE53_SCHEMA_SOURCE_AND_NEW_AUTHOR_PROVENANCE',
  'compiled':str(a.compiled),'raw':pin(raw_path),'compilation_report':pin(a.compiled/'COMPILATION_REPORT.json'),
  'direct_dual_tokenized_rows':627,'independent_tokenizer_calls_main_rows':calls_before,
  'total_tokenizer_calls_including_actual_prompt_loss_negative':{n:t.calls for n,t in toks.items()},
  'original_compiler_control_calls_not_reused':report['tokenizer_proof']['independent_second_tokenizer_calls'],
  'actual_counts':dict(all_counts),'by_bank':{k:dict(v) for k,v in by_bank.items()},
  'by_stage':{k:dict(v) for k,v in by_stage.items()},'native_schema_tool_intent_counts':dict(tool_counts),
  'fresh_offsets_rebuilt_every_positive_component_and_zero_mask':True,
  'all_positive_weight':0.05,'weighted_positive_mass':round(all_counts['supervised_tokens']*0.05,8),
  'source_ids_empty':True,'new_author_R_not_original_teacher_thought':True,
  'source_case_pins':sourcepins,'native53_capture':protocol['source_capture'],'native53_request_tools_only':protocol['original_request_capture'],
  'full53_structural_equality_to_both_original_technical_captures':True,
  'future_credit_and_rejected_alternatives_audit_only':True,'fake_native_tool_messages':0,
  'alias_removed_identical_input_conflicts':0,'distinct_alias_removed_conditioning_states':len(inputs),
  'token_length':{'min':min(lengths),'max':max(lengths),'le16k':sum(n<=16384 for n in lengths),'le32k':sum(n<=32768 for n in lengths)},
  'actual_prompt_loss_negative_canary':negative,'legacy_original_reasoning_characters_field_is_count_not_provenance':True,
  'base623_manifest_sha256_unchanged':MAIN_SHA,'tokenizer_asset_pins':tokenizer_pins,
  'script':pin(Path(__file__)),'reused_independent_checker':pin(ROOT/'research/data_prep/wrd_curation10/verify_main10.py'),
  'training_started':False,'weights_loaded':False,'native_business_sessions_started':0,
  'business_quality_Q_or_real_KEEP_inferred_from_this_QA':False,
  'semantic_credit_requires_root_and_independent_semantic_QA':True,'binary_arrays_QA_pending_separate_run':True,
  'elapsed_seconds_local_CPU':time.perf_counter()-started}
 save(a.out/'ALL627_SYNTHETIC_TOKEN_MASK_SOURCE_QA.json',result)
 print(json.dumps({k:result[k] for k in ['status','direct_dual_tokenized_rows','actual_counts','native_schema_tool_intent_counts','actual_prompt_loss_negative_canary']}))


if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--compiled',type=Path,default=WORK/'compiled04')
 p.add_argument('--assets',type=Path,default=ROOT/'output/20261025_wrd_training_preflight/tokenizer_assets')
 p.add_argument('--out',type=Path,default=WORK/'technical_qa01')
 main(p.parse_args())
