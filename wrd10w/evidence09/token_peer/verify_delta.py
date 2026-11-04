"""Independent dual-tokenizer and mask audit; never import the root pruner.

This reviewer authored writer candidates, so semantic-author independence is not
claimed. Rendering, range reconstruction and negative canaries are independently
implemented here against the final frozen compiled bank.
"""
from pathlib import Path
from collections import Counter,defaultdict
from copy import deepcopy
from array import array
import argparse,gzip,hashlib,importlib.util,json,os,sys,time
os.environ.update(USE_TORCH='0',USE_TF='0',CUDA_VISIBLE_DEVICES='-1',TOKENIZERS_PARALLELISM='false')
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[3]
BASE=ROOT/'output/20261027_wrd_main_v10'
ASSETS=ROOT/'output/20261025_wrd_training_preflight/tokenizer_assets'
RES=ROOT/'output/20261031_wrd_curation09/holdout/holdout_reservation.json'

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def hs(t):return hashlib.sha256(t.encode('utf-8')).hexdigest()
def js(x):return json.dumps(x,ensure_ascii=False,separators=(',',':'))
def load(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def rows(p):
 with gzip.open(p,'rt',encoding='utf-8-sig')as f:
  for line in f:
   if line.strip():yield json.loads(line)
def pin(p):return {'path':str(Path(p).resolve()),'sha256':sha(p),'bytes':Path(p).stat().st_size}
def ids_sha(ids):
 a=array('I',ids)
 if sys.byteorder!='little':a.byteswap()
 return hashlib.sha256(a.tobytes()).hexdigest()
def save(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

def verify_authorized_late_ranges(candidate,meta):
 original=candidate.get('target_code_unicode_exclusions',[])
 if original==meta.get('target_code_unicode_exclusions',[]):return []
 def key(r):return(r['start'],r['end'],r['text_sha256'],r['reason'])
 evidence=[];additions=[]
 for ref in meta.get('late_root_negative_evidence',[]):
  p=Path(ref['path']);assert sha(p)==ref['sha256'],'LATE_EVIDENCE_PIN_CHANGED'
  proof=load(p)
  matching=[r for r in proof['ranges']if r['owner_id']==candidate['owner_id']]
  assert matching,'LATE_RANGE_OWNER_MISMATCH'
  for r in matching:
   assert r['target_original_code_sha256']==meta['target_original_code_sha256']
   additions.append(key(r))
  evidence.append(pin(p))
 assert evidence and {key(r)for r in meta['target_code_unicode_exclusions']}=={key(r)for r in original}|set(additions),'UNAUTHORIZED_CODE_RANGE_CHANGE'
 return evidence

def independent_negative_ranges(row,text):
 meta=row['original_record_metadata'];target_index=meta['supervision_message_indices'][0]
 message=row['messages'][target_index];target=next(t for t in row['targets']if t['message_index']==target_index)
 a,b=target['rendered_assistant_span'];derived=[]
 if meta.get('target_code_unicode_exclusions'):
  call=message['tool_calls'][0];args=call['function']['arguments']
  if isinstance(args,str):args=json.loads(args)
  code=args['content'];assert hs(code)==meta['target_original_code_sha256']
  candidates=[];decoder=json.JSONDecoder()
  for pos in range(a,b):
   if text[pos]!='{':continue
   try:obj,end=decoder.raw_decode(text[pos:b])
   except ValueError:continue
   if obj==args:candidates.append((pos,pos+end))
  assert len(candidates)==1,'ARGS_SERIALIZATION_NOT_UNIQUE'
  start,end=candidates[0];serialized=text[start:end];encoded=json.dumps(code,ensure_ascii=False)
  assert serialized.count(encoded)==1
  origin=start+serialized.index(encoded)+1
  for reg in meta['target_code_unicode_exclusions']:
   lo,hi=reg['start'],reg['end'];assert 0<=lo<hi<=len(code)and hs(code[lo:hi])==reg['text_sha256']
   x=origin+len(json.dumps(code[:lo],ensure_ascii=False))-2
   y=origin+len(json.dumps(code[:hi],ensure_ascii=False))-2
   assert text[x:y]==json.dumps(code[lo:hi],ensure_ascii=False)[1:-1]
   derived.append({'kind':'code','start':x,'end':y,'text_sha256':hs(text[x:y]),'code_start':lo,'code_end':hi})
  actual=meta['target_excluded_rendered_ranges']
  assert {(r['start'],r['end'],r['text_sha256'])for r in derived}=={(r['start'],r['end'],r['text_sha256'])for r in actual},'COMPILER_CODE_MASK_MAPPING_NOT_EXACT'
 if meta.get('target_content_unicode_exclusions'):
  content=message.get('content','')or'';reasoning=message.get('reasoning_content','')or''
  start=a+len('<|im_start|>assistant\n<think>\n')+len(reasoning)+len('\n</think>\n\n')
  assert text[start:start+len(content)]==content
  for reg in meta['target_content_unicode_exclusions']:
   lo,hi=reg['start'],reg['end'];assert 0<=lo<hi<=len(content)and hs(content[lo:hi])==reg['text_sha256']
   derived.append({'kind':'content','start':start+lo,'end':start+hi,'text_sha256':reg['text_sha256']})
 return derived

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--compiled',type=Path,required=True);ap.add_argument('--raw',type=Path,required=True)
 ap.add_argument('--expected-targets',type=int,required=True);ap.add_argument('--expected-code-ranges',type=int,required=True)
 ap.add_argument('--expected-content-ranges',type=int,required=True);ap.add_argument('--out',type=Path,required=True)
 ap.add_argument('--baseline-manifest-sha',default='cbb233f2a44bcb61035e4fcb046830178510529cb149cf3ea6100c613babe555')
 args=ap.parse_args();args.out.mkdir(exist_ok=False);start=time.monotonic()
 baseline=BASE/'TRAINING_MANIFEST.json';assert sha(baseline)==args.baseline_manifest_sha
 reservation=load(RES);scopes={r['source_id']:r for r in rows(BASE/'clean_inputs/source_scope.metadata.jsonl.gz')}
 old_ids=set();old_owners=set();old_calls=set();old_recorded=set()
 for ref in load(baseline)['actual_train_files']:
  p=BASE/ref['path'];assert sha(p)==ref['sha256']and p.stat().st_size==ref['bytes']
  for r in rows(p):
   old_ids.add(r['id']);m=r['original_record_metadata'];old_owners.add(m.get('owner_id',r['id']))
   if m.get('original_recorded_action_owner'):old_recorded.add(m['original_recorded_action_owner'])
   for t in r['targets']:
    if any(s[2]=='A'for s in t['owned_supervision_spans']):old_calls.update(c['id']for c in r['messages'][t['message_index']].get('tool_calls',[]))
 assert len(old_ids)==569
 raw={r['id']:r for r in rows(args.raw)};report=load(args.compiled/'COMPILATION_REPORT.json');compiled=[]
 actual_asset_sha={}
 for name,files in report['tokenizer_proof']['asset_sha256'].items():
  actual_asset_sha[name]={filename:sha(ASSETS/name/filename)for filename in files}
  assert actual_asset_sha[name]==files,'PINNED_TOKENIZER_ASSET_CHANGED'
 template_meta=load(args.compiled/'CAUSAL_TEMPLATE.json')
 assert hs(template_meta['variant'])==report['tokenizer_proof']['causal_template_sha256']==template_meta['causal_template_sha256']
 for ref in report['files']:
  p=args.compiled/ref['path'];assert sha(p)==ref['sha256']and p.stat().st_size==ref['bytes'];compiled.extend(rows(p))
 assert len(compiled)==len(raw)==args.expected_targets and {r['id']for r in compiled}==set(raw)
 from transformers import AutoTokenizer
 from transformers.utils.chat_template_utils import _compile_jinja_template
 class Proxy:
  def __init__(self,t):self.t=t;self.calls=0;self.last=None
  def __getattr__(self,k):return getattr(self.t,k)
  def __call__(self,*a,**k):self.calls+=1;self.last=self.t(*a,**k);return self.last
 toks={n:Proxy(AutoTokenizer.from_pretrained(ASSETS/n,local_files_only=True,trust_remote_code=False))for n in ['primary_14b','control_8b']}
 template=_compile_jinja_template(template_meta['variant'])
 path=ROOT/'research/data_prep/wrd_main_v10/verify_main05.py';spec=importlib.util.spec_from_file_location('independent_portable_verify05',path)
 verifier=importlib.util.module_from_spec(spec);spec.loader.exec_module(verifier)
 seen_ids=set();seen_owners=set();seen_calls=set();seen_recorded=set();counts=Counter();stages=defaultdict(Counter);origins=defaultdict(Counter)
 findings=[];code_ranges=content_ranges=0;first_bad_case=None;new_R_rows=[];observed_sources=set();groups=set();late_pins=[]
 for row in compiled:
  meta=row['original_record_metadata'];candidate=raw[row['id']]
  assert row['messages']==candidate['messages']and row['tools']==candidate['tools']
  for k,v in candidate.items():
   if k not in {'messages','tools','target_code_unicode_exclusions'}:assert meta[k]==v,('RAW_METADATA_CHANGED',row['id'],k)
  late_pins+=verify_authorized_late_ranges(candidate,meta)
  assert row['id']not in old_ids|seen_ids;seen_ids.add(row['id'])
  owner=meta['owner_id'];assert owner not in old_owners|seen_owners;seen_owners.add(owner)
  original_owner=meta.get('original_recorded_action_owner')
  if original_owner:
   assert original_owner not in old_recorded|seen_recorded
   seen_recorded.add(original_owner)
  assert meta['training_admitted']is True and meta['source_admission']=='ADMIT'
  assert meta['loss_multiplier']==.25 and meta['teacher_original_R_supervised']is False
  assert meta['original_native_prompt_equivalence_claimed']is False and not meta['is_full_autonomous_execution_demonstration']and not meta['is_qualified_KEEP_demonstration']
  assert not any(meta.get(k)for k in ['original226','holdout12','protected_sources_visible_prefix','protected_source_ids'])
  assert row['split']=='train'and not(set(row['source_ids'])&set(reservation['reserved_source_ids']))
  assert not({scopes[s]['component_id']for s in row['source_ids']}&set(reservation['reserved_source_scope_components']))
  assert all(scopes[s]['status']=='TRAIN'for s in row['source_ids'])
  observed_sources.update(row['source_ids']);groups.add(row['source_group_id'])
  assert meta['message_loss_mask']==[0,0,1] and meta['supervision_message_indices']==[2]
  assert row.get('view')!='EXACT_TOKEN_PREFIX_OMITTING_ONLY_UNSUPERVISED_FUTURE_COMPLETION','NO_STATIC_TRUNCATION_ALLOWED'
  verifier.verify_token_row(row,template,toks)
  text=template.render(messages=row['messages'],tools=row.get('tools')or None,documents=None,add_generation_prompt=False,**dict(toks['primary_14b'].special_tokens_map,enable_thinking=False))
  offsets=toks['primary_14b'].last['offset_mapping'];ids=row['input_ids'];assert ids_sha(ids)==row['input_ids_sha256_u32le']and len(ids)==row['total_tokens']<=32768
  derived=independent_negative_ranges(row,text)
  code_ranges+=sum(r['kind']=='code'for r in derived);content_ranges+=sum(r['kind']=='content'for r in derived)
  labels=[-100]*len(ids);weights=[0.0]*len(ids);components=Counter();last=0
  for lo,hi,c,w in row['supervision_spans']:
   assert 0<=last<=lo<hi<=len(ids)and c in {'R','A','D'}and w==.25;last=hi
   for i in range(lo,hi):
    x,y=offsets[i];assert not any(x<r['end']and y>r['start']for r in derived),'INDEPENDENT_BAD_RANGE_HAS_POSITIVE_LOSS'
    assert labels[i]==-100;labels[i]=ids[i];weights[i]=w;components[c]+=1
  assert dict(components)==row['supervised_tokens_by_component']and sum(components.values())==row['supervised_tokens']
  assert hs(js(row['supervision_spans']))==row['supervision_spans_sha256']
  assert [s for t in row['targets']for s in t['owned_supervision_spans']]==row['supervision_spans']
  assert sum(v!=-100 for v in labels)==sum(components.values())
  if components['R']:
   assert row['messages'][2].get('reasoning_content')and meta['rationale_provenance'].startswith('NEW_'),'ORIGINAL_R_NOT_PRESENT_IN_THIS_DELTA'
   new_R_rows.append(row['id'])
  if components['A']:
   for call in row['messages'][2].get('tool_calls',[]):assert call['id']not in old_calls|seen_calls;seen_calls.add(call['id'])
  for counter in [counts,stages[row['stage']],origins[meta.get('rationale_provenance','UNKNOWN')]]:
   counter.update(targets=1,input_tokens=len(ids),supervised_tokens=sum(components.values()),le16k=int(len(ids)<=16384),le32k=int(len(ids)<=32768))
   for c,n in components.items():counter['component_'+c]+=n
  findings.append({'id':row['id'],'owner_id':owner,'total_tokens':len(ids),'supervised_tokens':sum(components.values()),'components':dict(components),
      'code_exclusions':sum(r['kind']=='code'for r in derived),'content_exclusions':sum(r['kind']=='content'for r in derived),
      'labels_and_weights_rebuilt':True,'prompt_loss_tokens':0,'crossing_or_bad_range_loss_tokens':0,'source_ids':row['source_ids']})
  if first_bad_case is None and any(r['kind']=='code'for r in derived):first_bad_case=(row,text,offsets,derived)
 assert code_ranges==args.expected_code_ranges and content_ranges==args.expected_content_ranges
 actual_calls={k:t.calls for k,t in toks.items()};assert all(n==args.expected_targets for n in actual_calls.values())
 # Memory-only malformed labels: keep the original immutable rows on disk.
 canaries=[]
 for kind in ['prompt','bad_code']:
  row,text,offsets,derived=first_bad_case;bad=deepcopy(row)
  token=next(i for i,(a,b)in enumerate(offsets)if 0<a<b<row['targets'][0]['rendered_assistant_span'][0])if kind=='prompt'else next(i for i,(a,b)in enumerate(offsets)if any(a<r['end']and b>r['start']for r in derived if r['kind']=='code'))
  bad['supervision_spans']=[[token,token+1,'A',.25]]
  bad['targets'][0]['owned_supervision_spans']=deepcopy(bad['supervision_spans'])
  try:verifier.verify_token_row(bad,template,toks)
  except AssertionError as e:canaries.append({'kind':kind,'rejected':True,'reason':str(e)})
  else:raise AssertionError('NEGATIVE_CANARY_ACCEPTED_'+kind)
 assert sha(baseline)==args.baseline_manifest_sha
 result={'status':'PASS_INDEPENDENT_TECHNICAL_TOKEN_MASK_SOURCE_OWNER_QA_NOT_TRAINING',
    'compiled_report':pin(args.compiled/'COMPILATION_REPORT.json'),'raw_candidates':pin(args.raw),'baseline_manifest':pin(baseline),'reservation':pin(RES),
    'actual_counts':dict(counts),'by_stage':{k:dict(v)for k,v in stages.items()},'by_rationale_provenance':{k:dict(v)for k,v in origins.items()},
    'source_ids':len(observed_sources),'source_groups':len(groups),'code_ranges':code_ranges,'content_ranges':content_ranges,
    'authorized_late_code_range_evidence_pins':late_pins,
    'original_R_positive_tokens':0,'new_R_rows':new_R_rows,'actual_pinned_tokenizer_asset_sha256':actual_asset_sha,
    'causal_template_sha256':hs(template_meta['variant']),'dual_tokenizer_calls_for_actual_rows':actual_calls,
    'dual_tokenizer_calls_including_negative_canaries':{k:t.calls for k,t in toks.items()},'negative_canaries':canaries,'rows':findings,
    'prompt_or_history_or_role_header_positive_tokens':0,'bad_or_crossing_positive_tokens':0,'owner_or_call_overlap_with_original569':0,
    'source_or_component_overlap_with_reservation':0,'original_system_equivalence_or_full_autonomy_or_KEEP_credit':0,
    'independence':{'root_prune_program_imported':False,'independent_unicode_to_JSON_to_rendered_range_reconstruction':True,'semantic_writer_authorship_overlap_disclosed':True},
    'serialized_binary_arrays_checked':False,'note':'Rows and exact regenerated token masks verified; future canonical array entrypoint is separately verified by root.',
    'elapsed_seconds':round(time.monotonic()-start,3),'model_weights_loaded':False,'training_started':False,'new_business_Teacher_Actor_calls':0,'ai_cpu_curation_cost':'UNKNOWN_NOT_ZERO'}
 save(args.out/'INDEPENDENT_TOKEN_MASK_SOURCE_OWNER_QA.json',result)
 print(js({'status':result['status'],'counts':dict(counts),'code_ranges':code_ranges,'content_ranges':content_ranges,'elapsed_seconds':result['elapsed_seconds']}))

if __name__=='__main__':main()
