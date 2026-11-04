"""Read-only independent staged checkpoint09 verifier. No admit/prune import."""
from pathlib import Path
from collections import Counter,defaultdict
from copy import deepcopy
from array import array
import argparse,gzip,hashlib,importlib.util,itertools,json,os,sys,time
os.environ.update(USE_TORCH='0',USE_TF='0',CUDA_VISIBLE_DEVICES='-1',TOKENIZERS_PARALLELISM='false')
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[3]
CUR=ROOT/'output/20261031_wrd_curation09'
ASSETS=ROOT/'output/20261025_wrd_training_preflight/tokenizer_assets'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def hs(s):return hashlib.sha256(s.encode()).hexdigest()
def js(x):return json.dumps(x,ensure_ascii=False,separators=(',',':'))
def load(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def pin(p):return{'path':str(Path(p).resolve()),'sha256':sha(p),'bytes':Path(p).stat().st_size}
def safe(root,p):
 q=Path(p);assert not q.is_absolute()and'..'not in q.parts
 x=(root/q).resolve();x.relative_to(root.resolve());return x
def lines(p):
 with gzip.open(p,'rb')as f:
  for i,line in enumerate(f):
   if line.strip():yield i,line,json.loads(line)
def records(root,manifest):
 for ref in manifest['actual_train_files']:
  p=safe(root,ref['path']);assert sha(p)==ref['sha256']and p.stat().st_size==ref['bytes']
  for i,line,row in lines(p):yield ref['path'],i,line,row
def module(path,name):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def features(row):
 ids=row['input_ids'];labels=[-100]*len(ids);weights=[0.]*len(ids)
 for a,b,_,w in row['supervision_spans']:
  for i in range(a,b):assert labels[i]==-100;labels[i]=ids[i];weights[i]=w
 return{'input_ids':ids,'labels':labels,'loss_weights':weights,'attention_mask':[1]*len(ids)}
def same_features(actual,expected):
 assert set(actual)==set(expected)=={'input_ids','labels','loss_weights','attention_mask'}
 for k in expected:assert actual[k]==expected[k],('BINARY_FEATURE_MISMATCH',k)
def origin(row):
 m=row['original_record_metadata'];b=row['bank'];out=Counter()
 nr={'native_wrd_main','native_C_review_partial_02','native_CV_B_training_01','native_HTML_B_training_01'}
 for c,n in row['supervised_tokens_by_component'].items():
  if b=='source_contract_main':k='new_source_contract_annotation_tokens'
  elif c=='R':
   if b in nr:k='original_native_R_tokens'
   elif b=='historical_semantic_R_main':k='historical_original_R_tokens'
   elif b=='historical_test_oracle_repair_02':k='recorded_cumulative_original_R_excerpt_tokens'
   elif b=='source_only_controller_batch24':k='new_authored_source_only_controller_R_tokens'
   else:assert m.get('teacher_original_R_supervised')is False or b in {'real_state_repair_main','new_real_state_cost_stop_02','historical_v6_native_repair_01','CV_clean_resource_construction_02','historical_style_repair_02','historical_helpers_construction_01','gap08_resource_and_repair_process'};k='new_authored_R_tokens'
  elif c=='A':
   if b=='real_state_repair_main':k='revalidated_original_action_A_tokens'
   elif b=='native_C_execution_local_02':k='original_native_execution_A_tokens'
   elif b in {'native_CV_B_training_01','native_HTML_B_training_01'}:k='original_native_local_process_A_tokens'
   else:assert m.get('actual_native_tool_dispatch')is False;k='new_authored_native_action_projection_A_tokens'
  elif c=='D':
   if b=='source_only_controller_batch24':k='new_authored_source_only_controller_D_tokens'
   elif b=='new_real_state_cost_stop_02':k='new_authored_cost_stop_D_tokens'
   else:assert m.get('rationale_provenance')=='ORIGINAL_VISIBLE_ASSISTANT_TEXT_NOT_THOUGHT_FIELD';k='recorded_visible_commentary_D_tokens'
  elif c=='E':assert m.get('rationale_provenance')=='ORIGINAL_VISIBLE_ASSISTANT_TEXT_NOT_THOUGHT_FIELD';k='recorded_visible_explanation_E_tokens'
  else:raise AssertionError(('UNCLASSIFIED_ORIGIN',b,c))
  out[k]+=n
 return out
def main():
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--manifest',default='manifest_staging09/TRAINING_MANIFEST09.json');p.add_argument('--baseline-manifest',type=Path,required=True);p.add_argument('--freeze',type=Path,required=True);p.add_argument('--freeze-sha256',required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(exist_ok=False);start=time.monotonic()
 assert sha(a.freeze)==a.freeze_sha256;f=load(a.freeze);assert sha(a.baseline_manifest)==f['baseline_manifest_sha256']
 baseline=load(a.baseline_manifest);manifestpath=safe(a.root,a.manifest);current=load(manifestpath);manifest_sha=sha(manifestpath)
 assert f['status']=='ROOT_FROZEN_CURATION09_STAGE_AUTHORIZATION';revpath=Path(f['revocations']['path']);assert sha(revpath)==f['revocations']['sha256'];rev=load(revpath)
 revoked=set(rev.get('revoke_current_view_ids',rev.get('revoked_record_ids',[])));protected=set(rev.get('revoke_source_ids',rev.get('protected_source_ids',[])));pg=set(rev.get('revoke_source_scope_component_ids',rev.get('protected_source_scope_components',[])))
 reservation=load(CUR/'holdout/holdout_reservation.json');protected|=set(reservation['reserved_source_ids']);pg|=set(reservation['reserved_source_scope_components'])
 scopes={r['source_id']:r for _,_,r in lines(a.root/'clean_inputs/source_scope.metadata.jsonl.gz')}
 old={r['id']:(path,i,line,r)for path,i,line,r in records(a.root,baseline)};assert len(old)==569 and revoked<=set(old)
 newreportpath=Path(f['new_compilation_report']['path']);assert sha(newreportpath)==f['new_compilation_report']['sha256'];newreport=load(newreportpath);new={}
 for ref in newreport['files']:
  path=newreportpath.parent/ref['path'];assert sha(path)==ref['sha256']
  for i,line,r in lines(path):assert r['id']not in new;new[r['id']]=(line,r)
 allowed=set(f.get('new_allowed_record_ids',rev.get('new_allowed_record_ids',[])));newrev=set(f.get('new_revoked_record_ids',rev.get('new_revoked_record_ids',[])))
 assert allowed.isdisjoint(newrev)and allowed|newrev==set(new)and not allowed&set(old)
 active=list(records(a.root,current));assert {r['id']for _,_,_,r in active}==(set(old)-revoked)|allowed
 affected={x[0].rsplit('/',1)[0]for k,x in old.items()if k in revoked}
 assert all(ref in current['actual_train_files']for ref in baseline['actual_train_files']if ref['path'].rsplit('/',1)[0]not in affected)
 for path,i,line,r in active:
  if r['id']in old:assert line==old[r['id']][2]and r==old[r['id']][3],'RETAINED_OLD_ROW_CHANGED'
  else:assert line==new[r['id']][0]and r==new[r['id']][1],'NEW_ROW_CHANGED_IN_STAGE'
  assert not set(r['source_ids'])&protected and not {scopes[s]['component_id']for s in r['source_ids']}&pg
  assert all(scopes[s]['status']=='TRAIN'for s in r['source_ids'])
 verifierpath=ROOT/'research/data_prep/wrd_curation09/verify_main09.py';assert sha(verifierpath)=='58eab7a3b83ad2438d3b3bfd05ef68f19778c39ddf95d4057fc194abba6583b8';verifier=module(verifierpath,'independent_staged_verifier09')
 followup=module(CUR/'followup_peer/verify_followup.py','independent_body_range_derivation')
 from transformers import AutoTokenizer
 from transformers.utils.chat_template_utils import _compile_jinja_template
 class Proxy:
  def __init__(self,t):self.t=t;self.calls=0;self.last=None
  def __getattr__(self,k):return getattr(self.t,k)
  def __call__(self,*args,**kwargs):self.calls+=1;self.last=self.t(*args,**kwargs);return self.last
 toks={n:Proxy(AutoTokenizer.from_pretrained(ASSETS/n,local_files_only=True,trust_remote_code=False))for n in ['primary_14b','control_8b']}
 for name,tok in toks.items():assert all(sha(ASSETS/name/k)==v for k,v in newreport['tokenizer_proof']['asset_sha256'][name].items())
 loaderpath=a.root/'canonical_arrays09/binary_loader09.py';assert sha(loaderpath)=='61598377d258f126faeebc6cc2f7f4f9046aec77fb274c6f5a58402995ce122d';loader=module(loaderpath,'independent_staged_binary09');binary=iter(loader.iter_features(a.root,manifest_override=a.manifest))
 indexpath=a.root/'canonical_arrays09/ARRAY_INDEX09.json';idx=load(indexpath);assert idx['manifest_sha256']==manifest_sha and idx['record_count']==len(active)and idx['binary_files']==3*len(active)
 counts=Counter();banks=defaultdict(Counter);stages=defaultdict(Counter);origins=Counter();seenowners=set();seencalls=set();ids=set();sources=set();parent={};templates={};nbody=ntext=0;first=None
 def find(x):
  parent.setdefault(x,x)
  if parent[x]!=x:parent[x]=find(parent[x])
  return parent[x]
 def join(x,y):parent[find(x)]=find(y)
 for position,(path,record_i,line,row)in enumerate(active):
  m=row['original_record_metadata'];assert row['id']not in ids;ids.add(row['id']);owner=m.get('owner_id',row['id']);assert owner not in seenowners;seenowners.add(owner)
  assert m['training_admitted']is True and m['source_admission']=='ADMIT'and not any(m.get(k)for k in ['original226','holdout12','protected_sources_visible_prefix','protected_source_ids'])
  name=path.rsplit('/',1)[0]
  if name not in templates:templates[name]=_compile_jinja_template(load(a.root/name/'CAUSAL_TEMPLATE.json')['variant'])
  template=templates[name];verifier.verify_token_row(row,template,toks)
  want=features(row);got=next(binary);same_features(got,want)
  entry=idx['records'][position];assert (entry['id'],entry['source_train_file'],entry['source_record_index'])==(row['id'],path,record_i)
  assert entry['supervision_spans_sha256']==row['supervision_spans_sha256']and entry['source_input_ids_sha256_u32le']==row['input_ids_sha256_u32le']
  for key,ref in entry['arrays'].items():
   q=safe(a.root,ref['path']);assert q.stat().st_size==ref['bytes']and sha(q)==ref['sha256']
  comps=Counter()
  for lo,hi,c,w in row['supervision_spans']:assert 0<=lo<hi<=len(want['input_ids']);comps[c]+=hi-lo
  assert dict(comps)==row['supervised_tokens_by_component']and sum(comps.values())==row['supervised_tokens']
  assert hs(js(row['supervision_spans']))==row['supervision_spans_sha256']
  for t in row['targets']:
   if any(s[2]=='A'for s in t['owned_supervision_spans']):
    for call in row['messages'][t['message_index']].get('tool_calls',[]):assert call['id']not in seencalls;seencalls.add(call['id'])
  for counter in [counts,banks[row['bank']],stages[row['stage']]]:
   counter.update(sequences=1,targets=1,input_tokens=row['total_tokens'],supervised_tokens=row['supervised_tokens'],le16k_sequences=int(row['total_tokens']<=16384),le32k_sequences=int(row['total_tokens']<=32768));counter.update({'component_'+k:v for k,v in comps.items()})
  origins.update(origin(row));node='r:'+row['id'];find(node)
  for s in row['source_ids']:sources.add(s);join(node,'s:'+s)
  if row['id']in allowed:
   text=template.render(messages=row['messages'],tools=row.get('tools')or None,documents=None,add_generation_prompt=False,**dict(toks['primary_14b'].special_tokens_map,enable_thinking=False))
   excluded,_,_=followup.negative_ranges(row,text);nbody+=sum(x['kind']!='public_text'for x in excluded);ntext+=sum(x['kind']=='public_text'for x in excluded)
   offsets=toks['primary_14b'].last['offset_mapping']
   for lo,hi,_,_ in row['supervision_spans']:
    assert all(not any(x<z['end']and y>z['start']for z in excluded)for x,y in offsets[lo:hi])
  if first is None:first=want
  if position and position%100==0:print(js({'verified_rows':position,'total':len(active)}),flush=True)
 try:next(binary)
 except StopIteration:pass
 else:raise AssertionError('EXTRA_BINARY_ROW')
 assert dict(counts)==current['actual_counts']and {k:dict(v)for k,v in banks.items()}==current['by_bank']and {k:dict(v)for k,v in stages.items()}==current['by_stage']
 assert dict(origins)==current['supervision_origin_tokens']and len(sources)==current['distinct_source_ids']and len({find('r:'+r['id'])for _,_,_,r in active})==current['source_connected_components_across_banks']
 assert current['full_WRD_main_training_ready']is False and current['default_full_pipeline_training_entrypoint']is None and current['training_started']is False
 canaries=[]
 for kind in ['prompt_label','wrong_positive_label','prompt_weight','attention_zero']:
  bad=deepcopy(first)
  if kind=='prompt_label':j=next(i for i,v in enumerate(bad['labels'])if v==-100);bad['labels'][j]=bad['input_ids'][j]
  elif kind=='wrong_positive_label':j=next(i for i,v in enumerate(bad['labels'])if v!=-100);bad['labels'][j]+=1
  elif kind=='prompt_weight':j=next(i for i,v in enumerate(bad['labels'])if v==-100);bad['loss_weights'][j]=.25
  else:bad['attention_mask'][0]=0
  try:same_features(bad,first)
  except AssertionError:canaries.append({'kind':kind,'rejected':True})
  else:raise AssertionError('BINARY_NEGATIVE_CANARY_ACCEPTED')
 assert sha(manifestpath)==manifest_sha and sha(a.baseline_manifest)==f['baseline_manifest_sha256']
 result={'status':'PASS_INDEPENDENT_STAGED_REBASE09_FULL_SOURCE_MASK_ARRAYS_NOT_ACTIVATION','manifest_pin':pin(manifestpath),'baseline_pin':pin(a.baseline_manifest),'freeze_pin':pin(a.freeze),'verifier_pin':pin(verifierpath),
 'actual_counts':dict(counts),'origins':dict(origins),'retained_old_rows':len(old)-len(revoked),'revoked_old_rows_absent':len(revoked),'new_approved_rows':len(allowed),'all_retained_old_lines_byte_identical':True,'all_new_lines_byte_identical':True,
 'dual_actual_tokenizer_calls':{k:v.calls for k,v in toks.items()},'independent_new_body_ranges':nbody,'independent_new_public_text_ranges':ntext,'binary_features_compared':len(active),'binary_file_count':3*len(active),'binary_negative_canaries':canaries,
 'canonical_array_index_pin':pin(indexpath),'loader_pin':pin(loaderpath),'source_count':len(sources),'DSU_components':current['source_connected_components_across_banks'],'root_admit_or_pruner_imported':False,'activation_executed':False,'training_started':False,'new_business_Teacher_Actor_calls':0,'curation_cost':'UNKNOWN_NOT_ZERO','elapsed_seconds':round(time.monotonic()-start,3)}
 out=a.out/'INDEPENDENT_FULL_STAGED_REBASE09_QA.json';out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(js({'status':result['status'],'counts':dict(counts),'sha256':sha(out)}))
if __name__=='__main__':main()
