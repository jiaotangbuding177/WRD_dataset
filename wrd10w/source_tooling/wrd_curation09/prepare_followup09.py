"""Prepare explicit second-batch projections; never select the main manifest."""
from pathlib import Path
from copy import deepcopy
import argparse,gzip,hashlib,json
ROOT=Path(__file__).resolve().parents[3]
WORK=ROOT/'output/20261031_wrd_curation09'
DATA=ROOT/'output/20261027_wrd_main_v10'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def hs(s):return hashlib.sha256(s.encode()).hexdigest()
def js(v):return json.dumps(v,ensure_ascii=False,separators=(',',':'))
def load(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def rows(p):
 with gzip.open(p,'rt',encoding='utf-8-sig')as f:
  for l in f:
   if l.strip():yield json.loads(l)
def main(a):
 a.out.mkdir(parents=True,exist_ok=False)
 reserve=load(WORK/'holdout/holdout_reservation.json');closure=load(WORK/'holdout/PROTECTED_CURRENT569_REVOCATION_CLOSURE.json')
 forbidden=set(reserve['reserved_source_ids'])|set(closure['revoke_source_ids'])
 groups=set(reserve['reserved_source_scope_components'])|set(closure['revoke_source_scope_component_ids'])
 scope={r['source_id']:r for r in rows(DATA/'clean_inputs/source_scope.metadata.jsonl.gz')}
 manifest=load(DATA/'TRAINING_MANIFEST.json');existing={r['id']for f in manifest['actual_train_files']for r in rows(DATA/f['path'])}
 out=[];transforms=[];seen=set()
 for p in a.raw:
  for original in rows(p):
   r=deepcopy(original);assert r['id']not in seen|existing;seen.add(r['id'])
   assert not forbidden.intersection(r['source_ids'])and not groups.intersection(scope[s]['component_id']for s in r['source_ids'])
   assert all(scope[s]['status']=='TRAIN'for s in r['source_ids'])
   r.update(source_admission='ADMIT',training_admitted=True,root_main_admission=False,requires_external_root_admission=True,
    staging_only_not_selected_by_main_manifest=True,semantic_scope_not_whole_WRD_or_qualified_KEEP=True)
   indices=r['supervision_message_indices'];assert len(indices)==1;i=indices[0];target=r['messages'][i]
   before=js(target);assert not target.get('reasoning_content'),'UNREVIEWED_ORIGINAL_R'
   r['rationale_provenance']='ORIGINAL_VISIBLE_ASSISTANT_TEXT_NOT_THOUGHT_FIELD'
   for m in r['messages']:
    for c in m.get('tool_calls',[]):
     if isinstance(c['function']['arguments'],str):c['function']['arguments']=json.loads(c['function']['arguments'])
   content=target.get('content')or'';ex=sorted(r.get('target_content_unicode_exclusions',[]),key=lambda x:x['start']);previous=0;positive=[]
   for x in ex:
    lo,hi=x['start'],x['end'];assert 0<=previous<=lo<hi<=len(content)and hs(content[lo:hi])==x['text_sha256']
    if previous<lo:positive.append({'message_index':i,'field':'content','start':previous,'end':lo,'text_sha256':hs(content[previous:lo])})
    previous=hi
   if previous<len(content):positive.append({'message_index':i,'field':'content','start':previous,'end':len(content),'text_sha256':hs(content[previous:])})
   if ex:
    r['approved_components']=[x for x in r['approved_components']if x!='D'];r['approved_field_ranges']=positive
   if r.get('target_code_unicode_exclusions'):
    calls=target.get('tool_calls',[]);assert len(calls)==1
    field=r.get('target_exclusion_argument_field',r.get('target_exclusion_argument_name','content'));r['target_exclusion_argument_field']=field
    assert (calls[0]['function']['name'],field)in {('write','content'),('exec','command')}
    body=calls[0]['function']['arguments'][field];assert isinstance(body,str)
    expected=r.get('target_original_code_sha256');assert expected is None or expected==hs(body)
    r['target_original_code_sha256']=hs(body);previous=0
    for x in sorted(r['target_code_unicode_exclusions'],key=lambda x:x['start']):
     lo,hi=x['start'],x['end'];assert previous<=lo<hi<=len(body)and hs(body[lo:hi])==x['text_sha256'];previous=hi
    r['requires_exact_serialized_body_pruning_before_admission']=True
   r['original_candidate_file_pin']={'path':str(p.resolve()),'bytes':p.stat().st_size,'sha256':sha(p)}
   transforms.append({'id':r['id'],'original_target_projection_before_sha256':hs(before),'parsed_args_only_no_argument_value_change':True,
    'content_bytes_unchanged':content==original['messages'][i].get('content',''),'negative_content_ranges':ex,
    'approved_field_ranges':r.get('approved_field_ranges',[]),'teacher_original_R_supervised':False})
   out.append(r)
 with gzip.open(a.out/'CANDIDATES_STAGING_NOT_MAIN.jsonl.gz','wt',encoding='utf-8',newline='\n')as f:
  for r in out:f.write(js(r)+'\n')
 (a.out/'PREPARATION.json').write_text(json.dumps({'status':'PREPARED_SCOPED_FOLLOWUP_NOT_MAIN','count':len(out),'transformations':transforms,
  'training_started':False,'new_original_R':0,'script_sha256':sha(__file__)},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print(js({'staged_records':len(out),'new_original_R':0,'not_main':True}))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--raw',type=Path,action='append',required=True);p.add_argument('--out',type=Path,required=True);main(p.parse_args())
