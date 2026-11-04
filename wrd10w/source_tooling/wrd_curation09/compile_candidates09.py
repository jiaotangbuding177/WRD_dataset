"""Stage scoped reviewed views and exact exclusion masks, not main admission."""
from pathlib import Path
from copy import deepcopy
from collections import Counter,defaultdict
import argparse,gzip,hashlib,importlib.util,json,os,subprocess,sys
os.environ.update(USE_TORCH='0',USE_TF='0',CUDA_VISIBLE_DEVICES='-1',TOKENIZERS_PARALLELISM='false')
ROOT=Path(__file__).resolve().parents[3];WORK=ROOT/'output/20261031_wrd_curation09';OUT=WORK/'compiled_staging01'
DATA=ROOT/'output/20261027_wrd_main_v10'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def hs(s):return hashlib.sha256(s.encode()).hexdigest()
def js(x):return json.dumps(x,ensure_ascii=False,separators=(',',':'))
def load(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def rows(p):
 with gzip.open(p,'rt',encoding='utf-8-sig')as f:
  for l in f:
   if l.strip():yield json.loads(l)
def save(p,x):p.write_bytes((json.dumps(x,ensure_ascii=False,indent=2)+'\n').encode())
def write(p,rs):
 with gzip.open(p,'wt',encoding='utf-8',newline='\n')as f:
  for r in rs:f.write(js(r)+'\n')
def prepare():
 OUT.mkdir(parents=True,exist_ok=False)
 reserve=load(WORK/'holdout/holdout_reservation.json');reserved=set(reserve['reserved_source_ids']);families=set(reserve['reserved_source_scope_components'])
 scope={r['source_id']:r for r in rows(DATA/'clean_inputs/source_scope.metadata.jsonl.gz')}
 inputs=[WORK/'writers/candidates02/candidates.raw.jsonl.gz',WORK/'process/FUNCTIONAL_CANDIDATES05.jsonl.gz',WORK/'process/VISIBLE_DECISION_CANDIDATES12.jsonl.gz']
 seen=set();ready=[];patches=[]
 for path in inputs:
  for original in rows(path):
   r=deepcopy(original);assert r['id']not in seen;seen.add(r['id'])
   assert not reserved.intersection(r['source_ids'])
   assert not families.intersection(scope[s]['component_id']for s in r['source_ids'])
   assert all(scope[s]['status']=='TRAIN'for s in r['source_ids'])
   r.update(source_admission='ADMIT',training_admitted=True,root_main_admission=False,requires_external_root_admission=True,
    staging_only_not_selected_by_main_manifest=True,semantic_scope_not_whole_WRD_or_qualified_KEEP=True)
   for m in r['messages']:
    for c in m.get('tool_calls',[]):
     fn=c['function'];args=fn['arguments']
     if isinstance(args,str):args=json.loads(args);fn['arguments']=args
     if m is r['messages'][-1]and fn['name']=='write'and 'write'in args:
      assert args['write']is True
      r['projected_target_removed_undeclared_arguments']={'write':True};r['original_target_arguments_SHA256_before_projection']=hs(js(args));del args['write']
   i=r['supervision_message_indices'][0]
   content=r['messages'][i].get('content','');ex=deepcopy(r.get('target_content_unicode_exclusions',[]))
   if r['id']=='process09-visible-45367ef84bf2439e17a581a1':
    text='并用 vision 探针确认画面内容';a=content.index(text);ex.append({'start':a,'end':a+len(text),'text':text,'text_sha256':hs(text),'reason':'Vision backend availability/permission is not established by the supplied core7 state.'})
   if content and r['bank']=='process09_visible_recovery_and_honest_decisions':pass
   if content and not r['messages'][i].get('tool_calls'):
    ex.sort(key=lambda x:x['start']);prev=0;positive=[]
    for x in ex:
     a,b=x['start'],x['end'];assert 0<=prev<=a<b<=len(content)and hs(content[a:b])==x['text_sha256']
     if prev<a:positive.append({'message_index':i,'field':'content','start':prev,'end':a,'text_sha256':hs(content[prev:a])})
     prev=b
    if prev<len(content):positive.append({'message_index':i,'field':'content','start':prev,'end':len(content),'text_sha256':hs(content[prev:])})
    r['approved_components']=[];r['approved_field_ranges']=positive;r['target_content_unicode_exclusions']=ex
   if r.get('target_code_unicode_exclusions'):
    code=r['messages'][i]['tool_calls'][0]['function']['arguments']['content']
    for x in r['target_code_unicode_exclusions']:assert hs(code[x['start']:x['end']])==x['text_sha256']
   ready.append(r)
   patches.append({'id':r['id'],'original_candidate_file':str(path),'original_candidate_file_sha256':sha(path),
    'argument_projection':r.get('projected_target_removed_undeclared_arguments'),
    'positive_content_ranges':r.get('approved_field_ranges',[]),'excluded_content_ranges':ex,'new_original_R':False})
 write(OUT/'CANDIDATES_STAGING_NOT_MAIN.jsonl.gz',ready)
 save(OUT/'ROOT_INPUT_REVIEW_TRANSFORM.json',{'status':'STAGING_ONLY_AWAIT_COMPLETE_RESOURCE_AND_INDEPENDENT_QA','rows':patches,'new_original_R_tokens':0,'training_started':False})
 print(js({'stage_inputs':len(ready),'not_main_admission':True}))
def compile():
 subprocess.run([sys.executable,str(ROOT/'research/data_prep/wrd_main_v10/compile_main.py'),'--input',str(OUT/'CANDIDATES_STAGING_NOT_MAIN.jsonl.gz'),'--output',str(OUT/'compiled01')],check=True)
def prune():
 src=ROOT/'research/data_prep/wrd_reasoning_v4/compile_native.py';spec=importlib.util.spec_from_file_location('curation09_causal_compiler',src);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
 c=mod.CausalCompiler(ROOT/'output/20261025_wrd_training_preflight/tokenizer_assets');prior=OUT/'compiled01';dest=OUT/'compiled02';dest.mkdir(exist_ok=False);report=load(prior/'COMPILATION_REPORT.json');buckets=defaultdict(list);exall=[]
 for ref in report['files']:
  for row in rows(prior/ref['path']):
   meta=row['original_record_metadata'];reg=deepcopy(meta.get('target_code_unicode_exclusions',[]))
   for proof in [WORK/'process_peer_qa/ADDITIONAL_REQUIRED_NEGATIVE_RANGE.json',WORK/'ROOT_ADDITIONAL_CODE_EXCLUSIONS09.json']:
    for extra in load(proof)['ranges']:
     if meta.get('original_recorded_action_owner')==extra['owner_id']:
      assert meta['target_original_code_sha256']==extra['target_original_code_sha256']
      reg.append({k:extra[k]for k in ['start','end','text_sha256','reason']})
      meta.setdefault('late_root_negative_evidence',[]).append({'path':str(proof),'sha256':sha(proof)})
   meta['target_code_unicode_exclusions']=reg
   if reg:
    kwargs=dict(c.tokenizers['primary_14b'].special_tokens_map,enable_thinking=False);rendered=c.plain_compiled.render(messages=row['messages'],tools=row['tools'],documents=None,add_generation_prompt=False,**kwargs)
    enc=c.tokenizers['primary_14b'](rendered,add_special_tokens=False,return_offsets_mapping=True);assert enc['input_ids']==row['input_ids'];offsets=enc['offset_mapping']
    i=meta['supervision_message_indices'][0];target=next(t for t in row['targets']if t['message_index']==i);call=row['messages'][i]['tool_calls'][0];args=call['function']['arguments'];a,b=target['rendered_assistant_span'];decoder=json.JSONDecoder();found=[]
    for pos in range(a,b):
     if rendered[pos]!='{':continue
     try:v,n=decoder.raw_decode(rendered[pos:b])
     except ValueError:continue
     if v==args:found.append((pos,pos+n))
    assert len(found)==1
    start,end=found[0];serialized=rendered[start:end];code=args['content'];encoded_code=json.dumps(code,ensure_ascii=False);assert encoded_code in serialized;content_start=start+serialized.index(encoded_code)+1
    ranges=[];meta['serialized_tool_argument_rendered_span']={'start':start,'end':end,'text_sha256':hs(serialized)}
    for x in reg:
     lo,hi=x['start'],x['end'];assert hs(code[lo:hi])==x['text_sha256']
     a=content_start+len(json.dumps(code[:lo],ensure_ascii=False))-2;b=content_start+len(json.dumps(code[:hi],ensure_ascii=False))-2;text=json.dumps(code[lo:hi],ensure_ascii=False)[1:-1];assert rendered[a:b]==text
     ranges.append({'start':a,'end':b,'text':text,'text_sha256':hs(text),'message_index':i,'field':'serialized_tool_arguments','subfield':'content','tool_call_id':call['id'],'reason':x['reason']})
    meta['target_excluded_rendered_ranges']=ranges;spans=[];components=Counter()
    for lo,hi,kind,w in row['supervision_spans']:
     for token in range(lo,hi):
      x,y=offsets[token]
      if any(x<r['end']and y>r['start']for r in ranges):continue
      if spans and spans[-1][1]==token and spans[-1][2:]==[kind,w]:spans[-1][1]=token+1
      else:spans.append([token,token+1,kind,w])
      components[kind]+=1
    row.update(supervision_spans=spans,supervised_tokens_by_component=dict(components),supervised_tokens=sum(components.values()),supervision_spans_sha256=hs(js(spans)))
    target.update(owned_supervision_spans=spans,supervised_tokens=row['supervised_tokens']);exall.extend({'id':row['id'],**r}for r in ranges)
   buckets['16k'if row['total_tokens']<=16384 else'32k'].append(row)
 counts=Counter();stages=defaultdict(Counter);banks=defaultdict(Counter);files=[]
 for bucket,rs in buckets.items():
  name='curation09.train.'+bucket+'.jsonl.gz';write(dest/name,rs);files.append({'path':name,'bytes':(dest/name).stat().st_size,'sha256':sha(dest/name)})
  for r in rs:
   for z in [counts,stages[r['stage']],banks[r['bank']]]:
    z.update(sequences=1,targets=1,input_tokens=r['total_tokens'],supervised_tokens=r['supervised_tokens'],**{bucket+'_sequences':1,'train_sequences':1,'train_supervised_tokens':r['supervised_tokens']})
    for k,v in r['supervised_tokens_by_component'].items():z['component_'+k]+=v
 with gzip.open(dest/'held.jsonl.gz','wt',encoding='utf-8'):pass
 (dest/'CAUSAL_TEMPLATE.json').write_bytes((prior/'CAUSAL_TEMPLATE.json').read_bytes())
 report.update(counts=dict(counts),stages={k:dict(v)for k,v in stages.items()},banks={k:dict(v)for k,v in banks.items()},files=files,held_file={'path':'held.jsonl.gz','bytes':(dest/'held.jsonl.gz').stat().st_size,'sha256':sha(dest/'held.jsonl.gz')},exact_excluded_code_ranges=len(exall),staging_only_not_root_main_admission=True,pruning_source_sha256=sha(__file__))
 save(dest/'COMPILATION_REPORT.json',report);save(OUT/'EXACT_ZERO_CODE_RANGES.json',exall);print(js({'counts':dict(counts),'negative_code_ranges':len(exall),'stage_only':True}))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('operation',choices=['prepare','compile','prune']);a=p.parse_args();{'prepare':prepare,'compile':compile,'prune':prune}[a.operation]()
