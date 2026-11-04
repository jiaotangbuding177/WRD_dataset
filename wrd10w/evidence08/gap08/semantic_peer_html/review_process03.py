"""Independent real dual-tokenizer, source and exact-mask audit of bank03."""
from pathlib import Path
from collections import Counter, defaultdict
import copy,gzip,hashlib,importlib.util,json,os,re,sys,time
os.environ.update(USE_TORCH='0',USE_TF='0',CUDA_VISIBLE_DEVICES='-1',TOKENIZERS_PARALLELISM='false')
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[3]
BASE=ROOT/'output/20261030_wrd_gap08';BANK=BASE/'process_bank03';COMP=BANK/'compiled02'
DATA=ROOT/'output/20261027_wrd_main_v10'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def hs(t):return hashlib.sha256(t.encode()).hexdigest()
def load(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def rows(p):
 with gzip.open(p,'rt',encoding='utf-8-sig')as f:
  for l in f:
   if l.strip():yield json.loads(l)
def pin(p):return {'path':str(p),'bytes':p.stat().st_size,'sha256':sha(p)}
def normal(m):
 c=m.get('content',[]);blocks=[]if isinstance(c,str)else c
 text=c if isinstance(c,str)else '\n'.join(b.get('text','')for b in c if isinstance(b,dict)and b.get('type')=='text')
 if m['role']=='toolResult':
  if any(b.get('type')=='image'for b in blocks if isinstance(b,dict)):text+='\n[此文本状态没有提供原图像像素；图像内容不据此视为已核验。]'
  return {'role':'tool','tool_call_id':m.get('toolCallId'),'content':text}
 if m['role']=='assistant':
  x={'role':'assistant','content':text,'reasoning_content':''};calls=[]
  for b in blocks:
   if isinstance(b,dict)and b.get('type')=='toolCall':
    a=b['arguments'];a=json.loads(a)if isinstance(a,str)else a
    calls.append({'id':b['id'],'type':'function','function':{'name':b['name'],'arguments':a}})
  if calls:x['tool_calls']=calls
  return x
 return {'role':'user','content':text}
def call_args(x):
 a=x['function']['arguments'];return json.loads(a)if isinstance(a,str)else a

def main():
 start=time.monotonic();raw=list(rows(BANK/'candidate17.jsonl.gz'));rawmap={r['id']:r for r in raw};assert len(rawmap)==len(raw)==17
 report=load(COMP/'COMPILATION_REPORT.json');template_meta=load(COMP/'CAUSAL_TEMPLATE.json')
 compiled=[];files=[]
 for ref in report['files']:
  p=COMP/ref['path'];assert p.stat().st_size==ref['bytes']and sha(p)==ref['sha256'];files.append(pin(p));compiled.extend(rows(p))
 assert len(compiled)==17 and {r['id']for r in compiled}==set(rawmap)
 zero_file=load(BANK/'EXACT_ZERO_RANGES.json');assert len(zero_file)==22
 scopes={r['source_id']:r for r in rows(DATA/'clean_inputs/source_scope.metadata.jsonl.gz')}
 existing_ids=set();existing_owners=set();existing_calls=set();existing_origin_calls=set()
 for ref in load(DATA/'TRAINING_MANIFEST.json')['actual_train_files']:
  for r in rows(DATA/ref['path']):
   existing_ids.add(r['id']);meta=r['original_record_metadata'];existing_owners.add(meta.get('owner_id',r['id']))
   if meta.get('actual_recorded_repair_call_id'):existing_origin_calls.add(meta['actual_recorded_repair_call_id'])
   for t in r['targets']:
    if any(s[2]=='A'for s in t.get('owned_supervision_spans',[])):
     existing_calls.update(c['id']for c in r['messages'][t['message_index']].get('tool_calls',[]))
 assert len(existing_ids)==552,'BASELINE_CHANGED_DURING_REVIEW'
 mandatory=defaultdict(list)
 for finding in load(BASE/'semantic_peer/THREE_PROGRAM_SEMANTIC_QA02.json')['findings']:
  for x in finding['mandatory_zero_loss_code_ranges']:
   mandatory[finding['target_owner_id']].append((x['code_range']['start'],x['code_range']['end'],x['code_text_SHA256']))
 for x in load(BASE/'semantic_peer_html/MANDATORY_LOSS0_SPANS.json')['spans']:
  mandatory[x['original_target_id']].append((x['start'],x['end'],x['span_sha256_utf8']))
 from transformers import AutoTokenizer
 from transformers.utils.chat_template_utils import _compile_jinja_template
 class Proxy:
  def __init__(self,t):self.t=t;self.calls=0;self.last=None
  def __getattr__(self,n):return getattr(self.t,n)
  def __call__(self,*a,**k):self.calls+=1;self.last=self.t(*a,**k);return self.last
 assets=ROOT/'output/20261025_wrd_training_preflight/tokenizer_assets'
 toks={n:Proxy(AutoTokenizer.from_pretrained(assets/n,local_files_only=True,trust_remote_code=False))for n in ['primary_14b','control_8b']}
 template=_compile_jinja_template(template_meta['variant'])
 path=ROOT/'research/data_prep/wrd_main_v10/verify_main05.py';s=importlib.util.spec_from_file_location('independent_verify05_bank03',path);verify=importlib.util.module_from_spec(s);s.loader.exec_module(verify)
 seen_calls=set();seen_owners=set();seen_recorded=set();totals=Counter();stages=Counter();groups={};audits=[];new_r=0;zero_count=0;visible_sources=set();writer_tokens=Counter();duplicates_as_context=[]
 for row in compiled:
  candidate=rawmap[row['id']];meta=row['original_record_metadata'];msgs=row['messages']
  assert msgs==candidate['messages']and row['tools']==candidate['tools']
  for k,v in candidate.items():
   if k not in {'messages','tools'}:assert meta[k]==v,('COMPILED_METADATA_CHANGED',row['id'],k)
  assert row['id']not in existing_ids and meta['owner_id']not in existing_owners and meta['owner_id']not in seen_owners
  seen_owners.add(meta['owner_id']);assert meta['loss_multiplier']==.25
  assert meta['curation_cost']=='UNKNOWN_NOT_ZERO'and meta['new_business_Teacher_Actor_calls']==0
  assert not meta['teacher_original_R_supervised']and not meta['actual_native_tool_dispatch']
  assert not meta['original_native_prompt_equivalence_claimed']and not meta['is_full_autonomous_execution_demonstration']and not meta['is_qualified_KEEP_demonstration']
  assert not meta['original226']and not meta['holdout12']and not meta['protected_sources_visible_prefix']and not meta['protected_source_ids']
  assert meta['root_main_admission']is False and meta['requires_external_root_admission']is True
  for source in row['source_ids']:assert scopes[source]['status']=='TRAIN'
  scope_pin=meta['source_context'];p=Path(scope_pin['path']);assert p.stat().st_size==scope_pin['bytes']and sha(p)==scope_pin['sha256']
  g=load(p);groups[g['original_context']['episode_id']]=g
  original=g['original_context']['messages'];index=meta['original_message_index']
  assert row['source_ids']==g['source_and_resource_proofs']['source_ids']
  assert meta['supervision_message_indices']==[len(msgs)-1]and meta['message_loss_mask']==[0]*(len(msgs)-1)+[1]
  target=msgs[-1];assert target['role']=='assistant'and target['content']==''and len(target['tool_calls'])==1
  call=target['tool_calls'][0];args=call_args(call)
  assert call['id']==meta['target_tool_call_id']and call['id']not in seen_calls|existing_calls
  seen_calls.add(call['id'])
  assert [t['function']['name']for t in row['tools']]==[t['function']['name']for t in candidate['tools']]
  assert set(t['function']['name']for t in row['tools'])=={'apply_patch','edit','exec','ls','process','read','write'}
  cap=meta['tool_schema_provenance'];assert sha(Path(cap['path']))==cap['sha256']
  found=re.findall(r'conv_[0-9a-f]{12}',json.dumps(msgs,ensure_ascii=False));vs=set(found);visible_sources|=vs
  bad={x:scopes.get(x,{}).get('status','UNKNOWN')for x in vs if scopes.get(x,{}).get('status')!='TRAIN'};assert not bad,('PROTECTED_OR_UNKNOWN_SOURCE_VISIBLE',row['id'],bad)
  writer=meta['stage']=='B_resource_implementation_from_execution_auxiliary'
  if writer:
   owner=meta['owner_id'];record=next(t for t in g['original_targets_with_feedback']if t['original_target_id']==owner)
   source_call=normal(record['original_message'])['tool_calls'][0]
   assert call==source_call and call['function']['name']=='write'
   code=Path(record['original_code_file']['path']).read_text(encoding='utf-8')
   assert args['content']==code and hs(code)==meta['target_original_code_sha256']==record['original_code_file']['sha256']
   assert msgs[2:-1]==[normal(m)for m in original[1:index]],('HISTORICAL_PREFIX_CHANGED',owner)
   actual={(x['start'],x['end'],x['text_sha256'])for x in meta['target_code_unicode_exclusions']}
   assert actual==set(mandatory[owner]),('NEGATIVE_RANGES_CHANGED',owner)
   for lo,hi,h in actual:assert hs(code[lo:hi])==h
   if any(args['content']==call_args(c).get('content')for m in msgs[:-1]for c in m.get('tool_calls',[])):
    duplicates_as_context.append({'id':row['id'],'interpretation':'FULL_BODY_ALREADY_VISIBLE_IN_FAILED_WRITE; target teaches valid retry/persistence and verbatim reproduction, not independent from-scratch code discovery'})
  elif meta['stage']=='B_verified_local_repair_new_functional_state':
   original_call=normal(original[index])['tool_calls'][0]
   assert args==call_args(original_call)and call['function']['name']==original_call['function']['name']
   assert meta['actual_recorded_repair_call_id']==original_call['id']
   assert original_call['id']not in existing_calls|existing_origin_calls|seen_recorded;seen_recorded.add(original_call['id'])
   assert len(msgs)==3 and meta['original_prefix_admission'].startswith('HOLD_OR_INCOMPLETE')
   resource=Path(meta['necessary_before_resource']['path']);before=resource.read_text(encoding='utf-8')
   assert sha(resource)==meta['necessary_before_resource']['sha256']and before in msgs[1]['content']
   native_path=args.get('path','/workspace/tmp/test_game.js');assert native_path in msgs[1]['content']
   if call['function']['name']=='edit':
    for e in args['edits']:assert before.count(e['oldText'])==1
   else:assert "sed -i '2d'"in args['command']and before.splitlines()[1]=='let chromium;'
   assert not target['reasoning_content']
  elif meta['stage']=='B_new_source_preservation_repair':
   prop=load(Path(meta['correction_proposal']['path']));original_owner=meta['original_writer_owner'];record=next(t for t in g['original_targets_with_feedback']if t['original_target_id']==original_owner)
   proposal=next(p for p in prop['programs']if p['original_owner_id']==original_owner)
   assert args=={'path':record['native_path'],'edits':[{k:c[k]for k in ['oldText','newText']}for c in proposal['changes']]}
   assert msgs[2:-3]==[normal(m)for m in original[1:index+1]]
   assert meta['do_not_train_corrected_whole_write_alongside_this_repair']is True
   assert sha(Path(meta['actual_resource_QA']['path']))==meta['actual_resource_QA']['sha256']
  else:
   assert meta['stage']=='B_new_actual_viewport_repair'
   assert args==load(BASE/'semantic_root/overlay_viewport_repair/NEW_NATIVE_EDIT_ARGUMENTS.json')
   before=Path(meta['necessary_before_resource']['path']).read_text(encoding='utf-8');assert before in msgs[1]['content']and args['path']in msgs[1]['content']
  if target['reasoning_content']:
   new_r+=1;assert meta['rationale_provenance']=='NEW_AUTHORED_SCOPED_RATIONALE'and meta['approved_components']==['R','A']
  else:assert meta['rationale_provenance']=='NO_ORIGINAL_R_IN_THIS_VIEW'and meta['approved_components']==['A']
  n,excluded=verify.verify_token_row(row,template,toks)
  offsets=toks['primary_14b'].last['offset_mapping'];rendered=template.render(messages=msgs,tools=row['tools']or None,documents=None,add_generation_prompt=False,enable_thinking=False,**toks['primary_14b'].special_tokens_map)
  positives=set();components=Counter()
  for lo,hi,component,w in row['supervision_spans']:
   assert w==.25 and component in meta['approved_components'];components[component]+=hi-lo
   for ti in range(lo,hi):assert ti not in positives;positives.add(ti)
  assert len(positives)==row['supervised_tokens']and dict(components)==row['supervised_tokens_by_component']
  mapped=[]
  for reg in meta.get('target_excluded_rendered_ranges',[]):
   a,b=reg['start'],reg['end'];assert reg in [{k:v for k,v in z.items()if k!='id'}for z in zero_file if z['id']==row['id']]
   scope=meta['serialized_tool_argument_rendered_span'];serialized=rendered[scope['start']:scope['end']]
   code=call_args(call)['content'];encoded=json.dumps(code,ensure_ascii=False);origin=scope['start']+serialized.index(encoded)+1
   candidate_matches=[]
   for ex in meta['target_code_unicode_exclusions']:
    lo,hi=ex['start'],ex['end'];ea=origin+len(json.dumps(code[:lo],ensure_ascii=False)[1:-1]);eb=origin+len(json.dumps(code[:hi],ensure_ascii=False)[1:-1])
    if (ea,eb)==(a,b):candidate_matches.append(ex)
   assert len(candidate_matches)==1 and rendered[a:b]==json.dumps(code[candidate_matches[0]['start']:candidate_matches[0]['end']],ensure_ascii=False)[1:-1]
   overlapping=[i for i,(x,y)in enumerate(offsets)if x<b and y>a];assert not(positives&set(overlapping))
   mapped.append({'start':a,'end':b,'tokens_forced_zero':len(overlapping),'text_sha256':reg['text_sha256']})
  assert excluded==len(mapped);zero_count+=excluded
  totals.update(sequences=1,input_tokens=n,supervised_tokens=len(positives),**{'component_'+k:v for k,v in components.items()})
  stages[row['stage']]+=1
  if writer:writer_tokens.update(components)
  audits.append({'id':row['id'],'source_ids':row['source_ids'],'owner_id':meta['owner_id'],'stage':row['stage'],
      'input_tokens':n,'supervised_tokens':len(positives),'components':dict(components),'dual_tokenizers':'DIRECT_BOTH_PASS',
      'negative_ranges':mapped,'original_R_positive':0,'new_R_tokens':components.get('R',0),'current_file_path_supplied':not writer,
      'original_native_prompt_equivalence_claimed':False,'positive_scope':'LOCAL_RESOURCE_OR_REPAIR_ONLY'})
 assert new_r==5 and zero_count==22
 expected={k:report['counts'][k]for k in ['sequences','input_tokens','supervised_tokens','component_A','component_R']}
 assert dict(totals)==expected
 assert toks['primary_14b'].calls==toks['control_8b'].calls==17
 # Negative canaries are in-memory only, not edits to any frozen row.
 canaries=[]
 probe=copy.deepcopy(compiled[0]);probe['supervision_spans'].append([0,1,'A',.25])
 try:verify.verify_token_row(probe,template,toks);raise RuntimeError('PROMPT_LOSS_CANARY_NOT_REJECTED')
 except AssertionError as e:canaries.append({'kind':'prompt_positive_loss','rejected':str(e)})
 probe=copy.deepcopy(next(r for r in compiled if r['original_record_metadata'].get('target_excluded_rendered_ranges')))
 verify.verify_token_row(probe,template,toks);offsets=toks['primary_14b'].last['offset_mapping'];reg=probe['original_record_metadata']['target_excluded_rendered_ranges'][0]
 ti=next(i for i,(a,b)in enumerate(offsets)if a<reg['end']and b>reg['start']);probe['supervision_spans'].append([ti,ti+1,'A',.25])
 try:verify.verify_token_row(probe,template,toks);raise RuntimeError('NEGATIVE_SPAN_CANARY_NOT_REJECTED')
 except AssertionError as e:canaries.append({'kind':'excluded_code_positive_loss','rejected':str(e)})
 result={'status':'PASS_INDEPENDENT_REAL_DUAL_TOKENIZER_AND_EXACT_MASK_SCOPE03',
   'candidate':pin(BANK/'candidate17.jsonl.gz'),'compilation_report':pin(COMP/'COMPILATION_REPORT.json'),'compiled_files':files,
   'verifier':pin(path),'review_program':pin(Path(__file__)),'checked_counts':dict(totals),'by_stage':dict(stages),
   'common_14B_8B_sequences':17,'le16k':sum(r['total_tokens']<=16384 for r in compiled),'le32k':sum(r['total_tokens']<=32768 for r in compiled),
   'direct_dual_tokenizer_rows_before_canaries':17,'tokenizer_calls_including_canaries':{k:v.calls for k,v in toks.items()},
   'new_authored_R_targets':new_r,'original_R_positive_tokens':0,'mapped_original_negative_code_ranges':zero_count,
   'distinct_source_ids':sorted({s for r in raw for s in r['source_ids']}),'source_components':sorted({scopes[s]['component_id']for r in raw for s in r['source_ids']}),
   'visible_source_ids_all_frozen_TRAIN':sorted(visible_sources),'baseline_existing_targets':552,
   'candidate_owner_and_actual_call_overlap_with_baseline':0,'negative_canaries':canaries,'records':audits,
   'important_interpretations':duplicates_as_context,
   'source_boundary':'Original226/H/static are not overridden. Full raw original prefixes of four projected repairs remain HOLD; only explicit clean current program state and local task are used.',
   'scope_limits':['This is 17 local targets over six sources, not 17 independent autonomous A-D tasks.',
       'Only new author R5 is supervised. Original visible commentary and all historical prompt messages have zero loss.',
       'Original system and full53 original request are not recovered; current core7 wrapper is explicit.',
       'Local correctness and source preservation do not establish skill utility, KEEP, independent Q or cost reduction.'],
   'withdrawn_prior_banks':'process_bank01 and process_bank02 and compiled01 are audit only, not default training.',
   'main_manifest_modified':False,'training_started':False,'new_business_Teacher_Actor_calls':0,
   'AI_curation_and_CPU_cost':'UNKNOWN_NOT_ZERO','wall_seconds':time.monotonic()-start}
 destination=BANK/'INDEPENDENT_TOKEN_AND_SCOPE_QA.json';assert not destination.exists();destination.write_bytes((json.dumps(result,ensure_ascii=False,indent=2)+'\n').encode())
 print(json.dumps({'status':result['status'],'counts':dict(totals),'QA':pin(destination)},ensure_ascii=False))

if __name__=='__main__':main()
