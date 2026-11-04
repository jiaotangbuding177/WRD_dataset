"""Freeze one unused source group as a dev consumer input before labels."""
from pathlib import Path
import gzip,hashlib,json
ROOT=Path('D:/skillloop');MAIN=ROOT/'output/20261027_wrd_main_v10'
OUT=ROOT/'output/20261031_wrd_curation10/parent_inputs'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def rows(p):return [json.loads(x) for x in gzip.open(p,'rt',encoding='utf-8-sig') if x.strip()]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def pin(p):return {'path':str(p),'bytes':p.stat().st_size,'sha256':sha(p)}
def main():
 audit=read(OUT/'SOURCE_ISOLATION_AUDIT.json')
 byid={r['source_id']:r for r in audit['results']}
 pool={r['source_id']:r for r in rows(MAIN/'clean_inputs/source_pool.with_body.jsonl.gz')}
 source='conv_34b56ae9c535';group=pool[source]['source_group_id']
 ids=sorted(s for s,r in pool.items() if r['source_group_id']==group)
 assert ids==[source]
 r=byid[source]
 assert not any(r[k] for k in ['direct_protected_or_known_private_ancestry',
  'in_current_train_ids','known_scope_in_train','known_material_train_intersection',
  'protected_input_alias_detected','reserved_private_answer_alias_detected',
  'current_train_whole_original_user_request_hits_ge32'])
 old=read(ROOT/'output/20261031_wrd_curation09/holdout/holdout_reservation.json')
 assert not set(ids)&set(old['reserved_source_ids'])
 reservation={'schema':'wrd10-parent-case-holdout-reservation-v1',
  'authorship':'NEW_OFFLINE_SPLIT_FREEZE_BY_RESEARCH_CURATOR_NOT_ORIGINAL_DATASET_LABEL',
  'source_scope_component_ids':[group],'reserved_source_ids':ids,'split':'dev',
  'authentic_material_sha256':[],
  'purpose':'One genuine independent-source HTML game consumption candidate for dev parent; no second case invented.',
  'exclude_from_all_new_training_views_and_ancestry':True,
  'do_not_return_to_train_if_incomplete':True,
  'known_source_scope_material_and_original_request_train_intersection':0,
  'protected_original_user_exact160_and_reserved_source_private_answer_exact160_matches':0,
  'ancestry_closure_status':'KNOWN_RECORDED_SOURCE_RESOURCE_GRAPH_AND_EXACT_TEXT_AUDIT_ONLY',
  'native_runtime_and_consumer_suitability_not_validated':True,
  'ready_full_parent_tasks_created':0,
  'new_training_labels':0,'new_business_calls':0,'training_started':False,
  'source_pins':[pin(MAIN/'TRAINING_MANIFEST.json'),pin(MAIN/'clean_inputs/source_pool.with_body.jsonl.gz'),pin(OUT/'SOURCE_ISOLATION_AUDIT.json'),pin(Path(__file__))]}
 p=OUT/'reservation.json';assert not p.exists()
 p.write_text(json.dumps(reservation,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print(json.dumps(pin(p)))
if __name__=='__main__':main()
