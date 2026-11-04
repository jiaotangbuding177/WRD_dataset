"""Independent source/mask/owner audit of exact staged follow-up rows.

No root pruner is imported. Two pinned tokenizers are actually called per row.
"""
from pathlib import Path
from collections import Counter
from copy import deepcopy
from array import array
import argparse, gzip, hashlib, importlib.util, json, os, sys, time
os.environ.update(USE_TORCH='0',USE_TF='0',CUDA_VISIBLE_DEVICES='-1',TOKENIZERS_PARALLELISM='false')
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[3]
BASE=ROOT/'output/20261027_wrd_main_v10'
CUR=ROOT/'output/20261031_wrd_curation09'
ASSETS=ROOT/'output/20261025_wrd_training_preflight/tokenizer_assets'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def hs(s):return hashlib.sha256(s.encode()).hexdigest()
def js(x):return json.dumps(x,ensure_ascii=False,separators=(',',':'))
def load(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def rows(p):return [json.loads(x)for x in gzip.open(p,'rt',encoding='utf-8-sig')if x.strip()]
def pin(p):return{'path':str(Path(p).resolve()),'sha256':sha(p),'bytes':Path(p).stat().st_size}
def module(path,name):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def native_text(message):
 content=message.get('content',[])
 return content if isinstance(content,str)else ''.join(x.get('text','')for x in content if x.get('type')=='text')
def args_of(call):
 a=call.get('arguments',call.get('function',{}).get('arguments'))
 return json.loads(a)if isinstance(a,str)else a
def features(row):
 ids=row['input_ids'];labels=[-100]*len(ids);weights=[0.]*len(ids)
 for a,b,_,w in row['supervision_spans']:
  for i in range(a,b):assert labels[i]==-100;labels[i]=ids[i];weights[i]=w
 return{'input_ids':ids,'labels':labels,'loss_weights':weights,'attention_mask':[1]*len(ids)}
def validate_E_provenance(meta):
 assert meta.get('rationale_provenance')=='ORIGINAL_VISIBLE_ASSISTANT_TEXT_NOT_THOUGHT_FIELD','E_FAKE_PROVENANCE'
def negative_ranges(row,text):
 m=row['original_record_metadata'];ti=m['supervision_message_indices'][0];msg=row['messages'][ti]
 target=next(t for t in row['targets']if t['message_index']==ti);a,b=target['rendered_assistant_span'];out=[];bodyranges=[]
 if m.get('target_code_unicode_exclusions'):
  call=msg['tool_calls'][0];args=args_of(call);field=m.get('target_exclusion_argument_field','content');body=args[field]
  assert hs(body)==m['target_original_code_sha256']
  found=[];dec=json.JSONDecoder()
  for pos in range(a,b):
   if text[pos]!='{':continue
   try:obj,n=dec.raw_decode(text[pos:b])
   except ValueError:continue
   if obj==args:found.append((pos,pos+n))
  assert len(found)==1,'ARGS_NOT_UNIQUE'
  lo,hi=found[0];encoded=json.dumps(body,ensure_ascii=False);assert text[lo:hi].count(encoded)==1
  origin=lo+text[lo:hi].index(encoded)+1
  for x in m['target_code_unicode_exclusions']:
   aa,bb=x['start'],x['end'];assert 0<=aa<bb<=len(body)and hs(body[aa:bb])==x['text_sha256']
   xx=origin+len(json.dumps(body[:aa],ensure_ascii=False))-2;yy=origin+len(json.dumps(body[:bb],ensure_ascii=False))-2
   assert text[xx:yy]==json.dumps(body[aa:bb],ensure_ascii=False)[1:-1]
   bodyranges.append({'kind':field,'start':xx,'end':yy,'text_sha256':hs(text[xx:yy])})
  assert {(x['start'],x['end'],x['text_sha256'])for x in bodyranges}=={(x['start'],x['end'],x['text_sha256'])for x in m['target_excluded_rendered_ranges']},'BAD_SERIALIZED_MAPPING'
  out+=bodyranges
 content=msg.get('content')or'';reason=msg.get('reasoning_content')or''
 start=a+len('<|im_start|>assistant\n<think>\n')+len(reason)+len('\n</think>\n\n');assert text[start:start+len(content)]==content
 for x in m.get('target_content_unicode_exclusions',[]):
  aa,bb=x['start'],x['end'];assert 0<=aa<bb<=len(content)and hs(content[aa:bb])==x['text_sha256']
  out.append({'kind':'public_text','start':start+aa,'end':start+bb,'text_sha256':x['text_sha256']})
 approved=[]
 for x in m.get('approved_field_ranges',[]):
  assert x['message_index']==ti and x['field']=='content'
  aa,bb=x['start'],x['end'];assert 0<=aa<bb<=len(content)and hs(content[aa:bb])==x['text_sha256']
  approved.append((start+aa,start+bb))
 return out,approved,(start,start+len(content))
def main():
 p=argparse.ArgumentParser();p.add_argument('--compiled',type=Path,required=True);p.add_argument('--raw',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--expected-code-ranges',type=int,required=True);a=p.parse_args();a.out.mkdir(exist_ok=False);st=time.monotonic()
 baseline=BASE/'TRAINING_MANIFEST.json';baseline_sha=sha(baseline);assert baseline_sha=='cbb233f2a44bcb61035e4fcb046830178510529cb149cf3ea6100c613babe555'
 reservation=load(CUR/'holdout/holdout_reservation.json');closure=load(CUR/'holdout/PROTECTED_CURRENT569_REVOCATION_CLOSURE.json');scopes={x['source_id']:x for x in rows(BASE/'clean_inputs/source_scope.metadata.jsonl.gz')}
 protected=set(reservation['reserved_source_ids'])|set(closure['revoke_source_ids']);protected_components=set(reservation['reserved_source_scope_components'])|set(closure['revoke_source_scope_component_ids'])
 old=[]
 for f in load(baseline)['actual_train_files']:
  path=BASE/f['path'];assert sha(path)==f['sha256']and path.stat().st_size==f['bytes'];old+=rows(path)
 prior=CUR/'compiled_staging01/compiled02';prior_report=load(prior/'COMPILATION_REPORT.json')
 for f in prior_report['files']:
  path=prior/f['path'];assert sha(path)==f['sha256'];old+=rows(path)
 oldids={r['id']for r in old};oldowners={r['original_record_metadata'].get('owner_id',r['id'])for r in old}
 oldcalls={c['id']for r in old for t in r['targets']for c in r['messages'][t['message_index']].get('tool_calls',[])if any(s[2]=='A'for s in t['owned_supervision_spans'])}
 oldrecorded={r['original_record_metadata']['original_recorded_action_owner']for r in old if r['original_record_metadata'].get('original_recorded_action_owner')}
 raw={r['id']:r for r in rows(a.raw)};report=load(a.compiled/'COMPILATION_REPORT.json');compiled=[]
 for f in report['files']:
  path=a.compiled/f['path'];assert sha(path)==f['sha256']and path.stat().st_size==f['bytes'];compiled+=rows(path)
 assert len(raw)==len(compiled)==17 and set(raw)=={r['id']for r in compiled}
 assetpins={name:{f:sha(ASSETS/name/f)for f in files}for name,files in report['tokenizer_proof']['asset_sha256'].items()};assert assetpins==report['tokenizer_proof']['asset_sha256']
 tmpl=load(a.compiled/'CAUSAL_TEMPLATE.json');assert hs(tmpl['variant'])==report['tokenizer_proof']['causal_template_sha256']
 from transformers import AutoTokenizer
 from transformers.utils.chat_template_utils import _compile_jinja_template
 class Proxy:
  def __init__(self,t):self.t=t;self.calls=0;self.last=None
  def __getattr__(self,k):return getattr(self.t,k)
  def __call__(self,*args,**kwargs):self.calls+=1;self.last=self.t(*args,**kwargs);return self.last
 toks={n:Proxy(AutoTokenizer.from_pretrained(ASSETS/n,local_files_only=True,trust_remote_code=False))for n in ['primary_14b','control_8b']}
 template=_compile_jinja_template(tmpl['variant']);verifierpath=ROOT/'research/data_prep/wrd_curation09/verify_main09.py'
 assert sha(verifierpath)=='58eab7a3b83ad2438d3b3bfd05ef68f19778c39ddf95d4057fc194abba6583b8'
 verifier=module(verifierpath,'independent09_followup')
 counts=Counter();seenids=set();seenowners=set();seencalls=set();seenrecorded=set();all_sources=set();details=[];nbody=ntext=0;canarycases={};sourcepins=[]
 for row in compiled:
  c=raw[row['id']];m=row['original_record_metadata'];assert row['messages']==c['messages']and row['tools']==c['tools']
  for k,v in c.items():
   if k not in {'messages','tools','requires_exact_serialized_body_pruning_before_admission'}:assert m[k]==v,('RAW_CHANGED',row['id'],k)
  assert row['id']not in oldids|seenids;seenids.add(row['id']);owner=m['owner_id'];assert owner not in oldowners|seenowners;seenowners.add(owner)
  ro=m.get('original_recorded_action_owner')or owner
  assert ro not in oldrecorded|seenrecorded;seenrecorded.add(ro)
  assert m['source_admission']=='ADMIT'and m['training_admitted']is True and m['loss_multiplier']==.25 and m['actual_native_tool_dispatch']is False
  assert m['teacher_original_R_supervised']is False and m['original_native_prompt_equivalence_claimed']is False
  assert not any(m.get(k)for k in ['original226','holdout12','protected_sources_visible_prefix','protected_source_ids','is_full_autonomous_execution_demonstration','is_qualified_KEEP_demonstration'])
  assert not set(row['source_ids'])&protected and not {scopes[s]['component_id']for s in row['source_ids']}&protected_components
  assert all(scopes[s]['status']=='TRAIN'for s in row['source_ids']);all_sources.update(row['source_ids'])
  assert m['message_loss_mask']==[0,0,1]and m['supervision_message_indices']==[2]
  packetpath=Path(m['source_context']['path']);assert sha(packetpath)==m['source_context']['sha256']and packetpath.stat().st_size==m['source_context']['bytes'];packet=load(packetpath);sourcepins.append(pin(packetpath))
  ix=m['original_message_index'];native=packet['original_context']['messages'];assert native[ix]==packet['original_target']
  calls=[x for x in native[ix]['content']if x.get('type')=='toolCall'];assert len(calls)==1
  target=row['messages'][2];assert native_text(native[ix])==(target.get('content')or'')
  assert args_of(calls[0])==args_of(target['tool_calls'][0])and calls[0]['id']==target['tool_calls'][0]['id']and calls[0]['name']==target['tool_calls'][0]['function']['name']
  for selected in packet['selected_before_observations']+packet['selected_before_resources']:
   ni=selected['index'];assert ni<ix and native[ni]==selected['message']
  if owner=='af98d54fb39ba95526215440':
   cli='独立图片理解可调用该helper的 vision --image-path "图片路径" --text "问题" --output /workspace/outputs/说明.txt。'
   assert cli in native_text(native[0])and cli in row['messages'][1]['content']
  verifier.verify_token_row(row,template,toks)
  text=template.render(messages=row['messages'],tools=row['tools']or None,documents=None,add_generation_prompt=False,**dict(toks['primary_14b'].special_tokens_map,enable_thinking=False))
  offsets=toks['primary_14b'].last['offset_mapping'];ids=row['input_ids'];assert len(ids)==row['total_tokens']<=32768
  arr=array('I',ids)
  if sys.byteorder!='little':arr.byteswap()
  assert hashlib.sha256(arr.tobytes()).hexdigest()==row['input_ids_sha256_u32le']
  excluded,approved,content=negative_ranges(row,text);nbody+=sum(x['kind']!='public_text'for x in excluded);ntext+=sum(x['kind']=='public_text'for x in excluded)
  comps=Counter();last=0
  for lo,hi,kind,w in row['supervision_spans']:
   assert 0<=last<=lo<hi<=len(ids)and kind in {'A','E'}and w==.25;last=hi
   for j in range(lo,hi):
    aa,bb=offsets[j];assert not any(aa<x['end']and bb>x['start']for x in excluded),'BAD_OR_CROSS_BOUNDARY_POSITIVE'
    if kind=='E':
     validate_E_provenance(m)
     assert any(x<=aa<bb<=y for x,y in approved),'E_OUTSIDE_REVIEWED_ORIGINAL_VISIBLE_TEXT'
    comps[kind]+=1
  assert dict(comps)==row['supervised_tokens_by_component']and sum(comps.values())==row['supervised_tokens']and hs(js(row['supervision_spans']))==row['supervision_spans_sha256']
  assert [s for t in row['targets']for s in t['owned_supervision_spans']]==row['supervision_spans']
  assert not target.get('reasoning_content')and not comps['R']
  for call in target.get('tool_calls',[]):assert call['id']not in oldcalls|seencalls;seencalls.add(call['id'])
  ft=features(row);assert sum(x!=-100 for x in ft['labels'])==row['supervised_tokens']
  counts.update(targets=1,input_tokens=len(ids),supervised_tokens=sum(comps.values()),le16k=int(len(ids)<=16384),le32k=int(len(ids)<=32768))
  counts.update({'component_'+k:v for k,v in comps.items()})
  details.append({'id':row['id'],'source_ids':row['source_ids'],'total_tokens':len(ids),'positive_tokens':sum(comps.values()),'components':dict(comps),'body_exclusions':sum(x['kind']!='public_text'for x in excluded),'public_text_exclusions':sum(x['kind']=='public_text'for x in excluded),'original_target_args_and_public_text_exact':True,'prompt_loss_tokens':0,'future_feedback_in_input_added':False})
  if excluded and'bad_body'not in canarycases:canarycases['bad_body']=(row,offsets,excluded)
  if comps['E']:canarycases['E']=(row,offsets,excluded)
  if m.get('target_exclusion_argument_field')=='command':canarycases['command']=(row,offsets,excluded)
 actualcalls={k:v.calls for k,v in toks.items()};assert actualcalls=={'primary_14b':17,'control_8b':17}
 assert nbody==a.expected_code_ranges and ntext==4
 assert counts['supervised_tokens']==report['counts']['supervised_tokens']and counts['input_tokens']==report['counts']['input_tokens']
 canaries=[]
 for name in ['prompt','bad_body','E_bad_text','E_fake_provenance']:
  row,offsets,excluded=canarycases['E'if name.startswith('E')else'bad_body'];bad=deepcopy(row)
  if name=='prompt':token=next(i for i,(x,y)in enumerate(offsets)if 0<x<y<row['targets'][0]['rendered_assistant_span'][0])
  elif name in {'bad_body','E_bad_text'}:token=next(i for i,(x,y)in enumerate(offsets)if any(x<q['end']and y>q['start']for q in excluded if (q['kind']=='public_text')==(name=='E_bad_text')))
  else:
   bad['original_record_metadata']['rationale_provenance']='NEW_INTERNAL_THOUGHT_NOT_ORIGINAL_VISIBLE'
   try:validate_E_provenance(bad['original_record_metadata'])
   except AssertionError as e:canaries.append({'name':name,'rejected':True,'by':'independent_E_origin_check','reason':str(e)});continue
   else:raise AssertionError('E_PROVENANCE_CANARY_NOT_REJECTED')
  bad['supervision_spans']=[[token,token+1,'E'if name.startswith('E')else'A',.25]];bad['targets'][0]['owned_supervision_spans']=deepcopy(bad['supervision_spans'])
  try:verifier.verify_token_row(bad,template,toks)
  except AssertionError as e:canaries.append({'name':name,'rejected':True,'reason':str(e)})
  else:raise AssertionError('CANARY_NOT_REJECTED_'+name)
 for name in ['wrong_tool_for_command','wrong_subfield_for_exec','outside_exact_encoded_body']:
  row,_,_=canarycases['command'];bad=deepcopy(row)
  if name=='wrong_tool_for_command':
   # Same character-length name preserves serialized character positions;
   # independently re-pin rendered text/ids so the tool-pair check must reject.
   bad['messages'][2]['tool_calls'][0]['function']['name']='read'
   text=template.render(messages=bad['messages'],tools=bad['tools']or None,documents=None,add_generation_prompt=False,**dict(toks['primary_14b'].special_tokens_map,enable_thinking=False))
   bad['input_ids']=toks['primary_14b'](text,add_special_tokens=False,return_offsets_mapping=True)['input_ids'];bad['rendered_sha256']=hs(text)
  elif name=='wrong_subfield_for_exec':bad['original_record_metadata']['target_excluded_rendered_ranges'][0]['subfield']='content'
  else:
   text=template.render(messages=bad['messages'],tools=bad['tools']or None,documents=None,add_generation_prompt=False,**dict(toks['primary_14b'].special_tokens_map,enable_thinking=False))
   reg=bad['original_record_metadata']['target_excluded_rendered_ranges'][0];start=bad['original_record_metadata']['serialized_tool_argument_rendered_span']['start']+1
   reg.update(start=start,end=start+5,text=text[start:start+5],text_sha256=hs(text[start:start+5]))
  try:verifier.verify_token_row(bad,template,toks)
  except AssertionError as e:canaries.append({'name':name,'rejected':True,'reason':str(e)or'bounded_tool_subfield_or_encoded_body_assertion'})
  else:raise AssertionError('COMMAND_CANARY_ACCEPTED_'+name)
 assert sha(baseline)==baseline_sha
 result={'status':'PASS_INDEPENDENT_FOLLOWUP17_DUAL_TOKEN_MASK_SOURCE_OWNER_QA_NOT_MAIN',
 'raw_pin':pin(a.raw),'compiled_report_pin':pin(a.compiled/'COMPILATION_REPORT.json'),'verifier_pin':pin(verifierpath),'baseline_pin':pin(baseline),'prior32_report_pin':pin(prior/'COMPILATION_REPORT.json'),
 'protection_closure_pin':pin(CUR/'holdout/PROTECTED_CURRENT569_REVOCATION_CLOSURE.json'),'reservation_pin':pin(CUR/'holdout/holdout_reservation.json'),
 'actual_counts':dict(counts),'body_negative_ranges':nbody,'public_text_negative_ranges':ntext,'source_count':len(all_sources),'sources':sorted(all_sources),
 'dual_actual_tokenizer_calls':actualcalls,'dual_calls_with_negative_canaries':{k:v.calls for k,v in toks.items()},'asset_pins':assetpins,'template_sha256':hs(tmpl['variant']),
 'rows':details,'source_packet_pins':sourcepins,'negative_canaries':canaries,'overlap_with_old569_and_prior32_ids_owners_calls':0,'overlap_with_reserved_or_revoked_source_components':0,
 'original_R_tokens':0,'new_R_tokens':0,'public_visible_E_tokens':counts['component_E'],'business_Teacher_Actor_calls':0,'weights_loaded':False,'training_started':False,
 'original_native_system_equivalence_claimed':False,'whole_skill_or_autonomous_or_KEEP_admission':False,
 'root_pruner_imported':False,'semantic_author_overlap_with_these17':False,'binary_arrays_checked':False,'AI_CPU_curation_cost':'UNKNOWN_NOT_ZERO','elapsed_seconds':round(time.monotonic()-st,3)}
 out=a.out/'INDEPENDENT_FOLLOWUP17_QA.json';out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(js({'status':result['status'],'counts':dict(counts),'body_negative_ranges':nbody,'report_sha256':sha(out)}))
if __name__=='__main__':main()
