"""Pin actual feedback inputs and explicit resource ancestry without reusing Q.

Only literal source identities, paths and original file hashes are reported.
No score values, protected grading text or model reasoning is extracted.
"""
from pathlib import Path
from collections import Counter
import importlib.util,json,re

ROOT=Path('D:/skillloop');OUT=ROOT/'output/20261031_wrd_curation10/identity'
s=importlib.util.spec_from_file_location('identity10feedback',ROOT/'research/data_prep/wrd_curation10/identity_recover.py')
a=importlib.util.module_from_spec(s);s.loader.exec_module(a)

def walk_dicts(v,pointer='$'):
 if isinstance(v,dict):
  yield pointer,v
  for k,x in v.items():
   if isinstance(x,(dict,list)):yield from walk_dicts(x,pointer+'/'+k)
 elif isinstance(v,list):
  for i,x in enumerate(v):
   if isinstance(x,(dict,list)):yield from walk_dicts(x,pointer+'/'+str(i))

def main():
 assert not (OUT/'MEETING_FEEDBACK_ANCESTRY.metadata.json').exists()
 discovery=a.load(OUT/'ORIGINAL_ROOT_DISCOVERY.metadata.json')['entries']
 selected=[e for e in discovery if str(e.get('task_id','')).startswith('meeting-minutes-formatting')]
 scope={r['source_id']:r for r in a.rows(a.MAIN/'clean_inputs/source_scope.metadata.jsonl.gz')}
 fixed={json.loads(l)['session_id']for l in (ROOT/'benchmark/enterprise_input_closed_v11_20261012/contracts/evaluation.jsonl').read_text(encoding='utf-8').splitlines()if l.strip()}
 h12=set(re.findall('conv_[0-9a-f]{12}',a.js(a.load(ROOT/'output/20261026_ablation_v2/holdout_registry.json'))))
 hold=a.load(ROOT/'output/20261031_wrd_curation09/holdout/holdout_reservation.json');reserved=set(hold['reserved_source_ids'])
 closure=a.load(ROOT/'output/20261031_wrd_curation09/holdout/PROTECTED_CURRENT569_REVOCATION_CLOSURE.json')
 revoked=set(closure['revoke_source_ids'])
 newp=ROOT/'output/20261031_wrd_curation10/parent_inputs/reservation.json';newids=set(re.findall('conv_[0-9a-f]{12}',a.js(a.load(newp))))
 def state(sid):
  if sid in fixed:return 'ORIGINAL226_PROTECTED'
  if sid in h12:return 'H12_PROTECTED'
  if sid in revoked:return 'CONTENT_ALIAS_PROTECTED09'
  if sid in reserved:return 'RESERVED_HOLDOUT09'
  if sid in newids:return 'RESERVED_PARENT_INPUT10'
  return scope.get(sid,{}).get('status','MISSING_CURRENT_SOURCE_SCOPE')
 result=[]
 for e in selected:
  base=Path(e['original_directory']);req=a.load(base/'request.json');feedback=[];sources=set();external=[]
  taskp=base/'workspace/inputs/repair/task.json';task=a.load(taskp)if taskp.is_file()else{}
  # Exact upstream file identity from the original repair recipe, not a new
  # interpretation of its outcome or an execution of any old evaluator.
  refs=[]
  for z in task.get('feedback_index',[]):
   if isinstance(z.get('pin'),dict):refs.append({'label':z.get('label'),'native_path':z.get('native_path'),'declared_original':z['pin']})
  if not task:
   for rr in e['resource_rows']:
    if 'feedback' in (rr['native_mount']or''):
     refs.append({'label':'actual_feedback_resource','native_path':'/workspace/'+rr['native_mount'],
         'declared_original':rr['original_startup_pin']})
  for ref in refs:
   original=ref.get('declared_original')or{};op=Path(original.get('path','NONEXISTENT'))
   native=ref.get('native_path')or'';mount=native.removeprefix('/workspace/')
   mounted=next((z for z in e['resource_rows']if z['native_mount']==mount),None)
   mp=Path(mounted['original_path'])if mounted else None
   row={**ref,'mounted_original_startup_resource':mounted,'upstream_path_exists':op.is_file(),
        'upstream_current_identity_matches':bool(op.is_file()and original.get('sha256')==a.digest(op)),
        'mounted_identity_equals_declared_upstream':bool(mounted and mounted['actual_pin_now']and mounted['actual_pin_now']['sha256']==original.get('sha256'))}
   p=mp if mp and mp.is_file()else op if op.is_file()else None
   if p and p.suffix.lower()in {'.json','.md','.py','.txt'}:
    text=p.read_text(encoding='utf-8-sig',errors='replace');ids=sorted(set(re.findall('conv_[0-9a-f]{12}',text)));sources.update(ids)
    row['source_id_literals']=ids;row['source_statuses']={x:state(x)for x in ids}
    row['contains_nonTRAIN_source_id_literal']=any(state(x)!='TRAIN'for x in ids)
    if p.suffix.lower()=='.json':
     d=a.load(p)
     row['schema']=d.get('schema',d.get('schema_version'))if isinstance(d,dict)else None
     row['top_level_keys']=list(d)if isinstance(d,dict)else None
     nested=[]
     for ptr,z in walk_dicts(d):
      if isinstance(z.get('path'),str)and isinstance(z.get('sha256'),str):
       zp=Path(z['path']);nested.append({'pointer':ptr,'path':z['path'],'declared_sha256':z['sha256'],
          'declared_bytes':z.get('bytes'),'exists':zp.is_file(),
          'identity_matches_if_present':a.digest(zp)==z['sha256']if zp.is_file()else None})
     row['nested_original_file_references']=nested
    row['read_as_quality_labels_or_score_values']=False
   feedback.append(row)
  # Resource-bank snapshot origins are not assumed clean because it has no
  # obvious source IDs. Preserve the explicit original origins and status.
  shared=task.get('shared_resource_snapshot')or{}
  snap=shared.get('snapshot')or{};sp=Path(snap.get('path','NONEXISTENT'))
  sharedmeta={'declared_snapshot':shared,'actual_identity_matches':bool(sp.is_file()and a.digest(sp)==snap.get('sha256'))}
  if sp.is_file():
   sd=a.load(sp);sharedmeta['snapshot_keys']=list(sd)if isinstance(sd,dict)else None
   sharedmeta['source_id_literals']=sorted(set(re.findall('conv_[0-9a-f]{12}',a.js(sd))))
   sourceids=set(sharedmeta['source_id_literals']);sources.update(sourceids)
   sharedmeta['source_statuses']={x:state(x)for x in sourceids}
   sharedmeta['original_file_refs']=[{'pointer':ptr,'path':z.get('path'),'sha256':z.get('sha256'),'bytes':z.get('bytes')}
       for ptr,z in walk_dicts(sd)if isinstance(z.get('path'),str)and isinstance(z.get('sha256'),str)]
   # Do not copy full unknown bank records or any grading fields here.
   sharedmeta['upstream_resource_authorship_closed_by_this_script']=False
  result.append({'episode_id':e['episode_id'],'task_id':e['task_id'],'source_ids':e['source_ids_from_actual_initial_assignment'],
    'initial_resource_mounts':[r['native_mount']for r in e['resource_rows']],
    'initial_feedback_or_previous_resources':sum(any(k in (r['native_mount']or'')for k in ['feedback','previous','repair'])for r in e['resource_rows']),
    'feedback_sources':feedback,'shared_resource_snapshot':sharedmeta,
    'all_literal_source_ids_seen_in_feedback_or_bank':sorted(sources),'literal_source_statuses':{x:state(x)for x in sources},
    'no_protected_score_or_reasoning_or_review_text_used_for_labels':True,
    'absence_of_protected_source_ID_literals_is_not_proof_of_full_feedback_provenance':True,
    'training_admitted':False,'positive_loss':0})
 out={'status':'EXACT_FEEDBACK_INPUT_IDENTITY_AND_EXPLICIT_REFERENCE_REVIEW_NOT_QUALITY_ADMISSION',
    'episodes':result,'new_business_calls':0,'training_started':False,'script_pin':a.pin(__file__)}
 a.save(OUT/'MEETING_FEEDBACK_ANCESTRY.metadata.json',out)
 print(a.js({'episodes':[{'task':r['task_id'],'initial_feedback_or_previous_resources':r['initial_feedback_or_previous_resources'],
   'feedback_count':len(r['feedback_sources']),'feedback_original_pin_matches':sum(z['upstream_current_identity_matches']for z in r['feedback_sources']),
   'literal_source_statuses':r['literal_source_statuses'],'shared_status':r['shared_resource_snapshot'].get('declared_snapshot',{}).get('status'),
   'shared_authorship_closed':r['shared_resource_snapshot'].get('upstream_resource_authorship_closed_by_this_script')}for r in result]}))

if __name__=='__main__':main()
