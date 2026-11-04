"""Merge exact current views and immutable raw-owner dispositions, no admission."""
from pathlib import Path
from collections import Counter,defaultdict
import gzip,json,hashlib
ROOT=Path(__file__).resolve().parents[3]
DATA=ROOT/'output/20261027_wrd_main_v10'
OLD=ROOT/'output/20261030_wrd_gap08/corpus'
WORK=ROOT/'output/20261031_wrd_curation09'
OUT=WORK/'coverage'
def load(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def js(r):return json.dumps(r,ensure_ascii=False,separators=(',',':'))
def rows(p):
 with gzip.open(p,'rt',encoding='utf-8-sig')as f:
  for line in f:
   if line.strip():yield json.loads(line)
def save(p,r):p.write_bytes((json.dumps(r,ensure_ascii=False,indent=2)+'\n').encode())
def gzwrite(p,records):
 with gzip.open(p,'wt',encoding='utf-8',newline='\n')as f:
  for r in records:f.write(js(r)+'\n')
def pin(p):return {'path':str(Path(p).resolve()),'bytes':Path(p).stat().st_size,'sha256':sha(p)}
def main():
 assert sha(DATA/'TRAINING_MANIFEST.json')=='cbb233f2a44bcb61035e4fcb046830178510529cb149cf3ea6100c613babe555'
 OUT.mkdir(parents=True,exist_ok=False)
 m=load(DATA/'TRAINING_MANIFEST.json');audit=load(ROOT/'output/20261031_wrd_readiness_plan/reviews/corpus_audit.json')
 reserve=load(WORK/'holdout/holdout_reservation.json');reserved=set(reserve['reserved_source_ids']);groups=set(reserve['reserved_source_scope_components'])
 scope={r['source_id']:r for r in rows(DATA/'clean_inputs/source_scope.metadata.jsonl.gz')}
 partition={}
 for group,v in audit['disjoint_primary_owner_work_queue'].items():
  for owner in v['owner_ids']:
   assert owner not in partition;partition[owner]=group
 assert len(partition)==34616
 prior={r['view_id']:r for r in rows(OLD/'CURRENT552_VIEW_COMPONENT_COVERAGE.jsonl.gz')};assert len(prior)==552
 delta={r['current_view']:r for r in load(ROOT/'output/20261030_wrd_gap08/DELTA08_VIEW_OWNER_OVERLAY.json')['rows']};assert len(delta)==17
 linked=defaultdict(list);views=[];totals=Counter();seen=set()
 for f in m['actual_train_files']:
  assert sha(DATA/f['path'])==f['sha256']
  for r in rows(DATA/f['path']):
   assert r['id']not in seen;seen.add(r['id']);meta=r['original_record_metadata']
   old=prior.get(r['id']);new=delta.get(r['id']);assert (old is None)!=(new is None)
   native_links=old['native_owner_links']if old else ([new['original_recorded_action_owner']]if new.get('original_recorded_action_owner')else[])
   external=old['external_historical_owner_links']if old else[]
   condition=old['view_conditioning']if old else'NEW_AUTHORED_FUNCTIONAL_STATE'
   v={'view_id':r['id'],'bank':r['bank'],'stage':r['stage'],'compiled_file':f['path'],'source_ids':r['source_ids'],
    'native_owner_links':native_links,'external_historical_owner_links':external,'view_conditioning':condition,
    'component_tokens':r['supervised_tokens_by_component'],'supervised_tokens':r['supervised_tokens'],
    'supervision_spans':r['supervision_spans'],'approved_field_ranges':meta.get('approved_field_ranges',old.get('approved_field_ranges',[])if old else[]),
    'target_excluded_rendered_ranges':meta.get('target_excluded_rendered_ranges',[]),'rendered_sha256':r['rendered_sha256'],
    'origin':meta.get('annotation_provenance'),'full_original_prefix_admitted_by_this_view':False,
    'raw_text_retained_at_authenticated_compiled_file':True,'reserved_source_intersection':sorted(set(r['source_ids'])&reserved)}
   assert not v['reserved_source_intersection']
   assert not {scope[s]['component_id']for s in r['source_ids']} & groups
   for o in native_links:
    assert o in partition
    linked[o].append({k:v[k]for k in ['view_id','bank','stage','view_conditioning','component_tokens','supervised_tokens','approved_field_ranges','target_excluded_rendered_ranges','rendered_sha256']})
   views.append(v);totals.update(targets=1,input_tokens=r['total_tokens'],supervised_tokens=r['supervised_tokens'])
 assert totals['targets']==569 and totals['supervised_tokens']==177562 and totals['input_tokens']==3496949
 gzwrite(OUT/'CURRENT569_VIEW_COMPONENTS.jsonl.gz',views)
 counts=Counter();owner_rows=[];covered=set()
 for r in rows(OLD/'CORPUS_OWNER_COVERAGE.native.jsonl.gz'):
  o=r['canonical_owner_id'];assert o not in covered;covered.add(o)
  q=partition[o];hits=sorted(set(r['source_ids'])&reserved)
  familyhits=sorted({scope[s]['component_id']for s in r['source_ids']if s in scope}&groups)
  r['09_effective_queue']=q;r['09_current_view_links']=linked.get(o,[])
  r['09_reserved_sources']=hits;r['09_reserved_scope_components']=familyhits
  r['09_new_semantic_admission']=False
  r['09_original_prefix_not_promoted_by_new_state']=True
  r['09_coverage_note']='A current view can own a scoped field/action with a different explicit input; prefix, whole response, original R/A and new state credit must not be merged.'
  owner_rows.append(r);counts[q]+=1
 assert covered==set(partition)and len(owner_rows)==34616
 gzwrite(OUT/'CURRENT34616_OWNER_COVERAGE09.jsonl.gz',owner_rows)
 assert {k:v['owners']for k,v in audit['disjoint_primary_owner_work_queue'].items()}==dict(counts)
 summary={'status':'PASS_CURRENT569_VIEW_RAW34616_OWNER_AND_RESERVATION_RECONCILIATION',
  'raw_native_owner_rows':34616,'current_views':569,'positive_tokens':177562,'input_tokens':3496949,
  'native_linked_view_count':sum(bool(v['native_owner_links'])for v in views),
  'distinct_raw_native_owners_with_linked_current_views':len(linked),
  'historical_external_linked_views':sum(bool(v['external_historical_owner_links'])for v in views),
  'views_without_native_or_external_owner_link':sum(not v['native_owner_links']and not v['external_historical_owner_links']for v in views),
  'missing_owner_link_does_not_imply_new_reasoning_authorship':True,
  'effective_raw_owner_queues':dict(counts),'source_reserved_owner_rows':sum(bool(r['09_reserved_sources']or r['09_reserved_scope_components'])for r in owner_rows),
  'reservation_is_not_final_ancestry_clearance':True,'current_positive_reservation_intersection':0,
  'full_original_response_or_prefix_admission_not_inferred':True,'new_training_admissions':0,'training_started':False,
  'pins':[pin(p)for p in [DATA/'TRAINING_MANIFEST.json',ROOT/'output/20261031_wrd_readiness_plan/reviews/corpus_audit.json',WORK/'holdout/holdout_reservation.json',OUT/'CURRENT569_VIEW_COMPONENTS.jsonl.gz',OUT/'CURRENT34616_OWNER_COVERAGE09.jsonl.gz']],
  'script_sha256':sha(__file__)}
 save(OUT/'COVERAGE_RECONCILIATION09.json',summary);print(js({k:v for k,v in summary.items()if k not in ['pins','effective_raw_owner_queues']}))
if __name__=='__main__':main()
