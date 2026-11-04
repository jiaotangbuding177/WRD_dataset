"""Publish honest per-owner processing state, not a blanket semantic PASS."""
from pathlib import Path
from collections import Counter
import gzip,hashlib,json
ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'output/20261031_wrd_curation09/process'
RES=ROOT/'output/20261031_wrd_curation09/holdout/holdout_reservation.json'
def load(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def js(v):return json.dumps(v,ensure_ascii=False,separators=(',',':'))
def save(p,j):p.write_text(json.dumps(j,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='')
def rows(p):
 with gzip.open(p,'rt',encoding='utf-8-sig')as f:
  for l in f:
   if l.strip():yield json.loads(l)
def main():
 assert not (OUT/'OWNER1321_DISPOSITION09.jsonl.gz').exists()
 reserved=set(load(RES)['reserved_source_ids'])
 candidates={r['owner_id']:r for f in ['FUNCTIONAL_CANDIDATES05.jsonl.gz','VISIBLE_DECISION_CANDIDATES12.jsonl.gz']for r in rows(OUT/f)}
 assert len(candidates)==17
 groups=Counter();states=Counter();literal=Counter();ledger=[];nativeR=0;texts=0;reserved_ids=[]
 for r in rows(OUT/'OWNER1321_EXACT_CONTENT.audit.jsonl.gz'):
  oid=r['owner_id'];scope='ISOLATED_NEW_DEV_TEST_RESERVED_SOURCE'if set(r['source_ids'])&reserved else'TRAIN_SOURCE_PENDING_CREDIT'
  if scope.startswith('ISOLATED'):
   state='ISOLATED_NEW_DEV_TEST_RESERVATION_NO_NEW_LOSS';review='SOURCE_SCOPE_ONLY_NOT_SEMANTIC_REVIEW';reserved_ids.append(oid)
  elif oid in candidates:
   state='SCOPED_SEMANTIC_CANDIDATE_PENDING_ROOT_QA_AND_COMPILATION';review='DECLARED_SCOPE_DEEP_REVIEW_ONLY_NOT_WHOLE_BUSINESS_GOLD'
  elif r['literal_target_classification']=='LITERAL_READ_LIST_ONLY':
   state='CONTEXT_ONLY_READ_LIST_NO_TARGET_SUPERVISION_PROPOSED';review='EXACT_LITERAL_CONTENT_ONLY_SELECTION_VALUE_NOT_DEEP_REVIEWED'
  else:
   state='HOLD_NEEDS_SEMANTIC_REVIEW';review='LITERAL_RECOVERED_NOT_DEEPLY_SEMANTICALLY_REVIEWED'
  if oid=='530e90edab23aea04adcfca2':
   assert scope=='TRAIN_SOURCE_PENDING_CREDIT'
   state='HOLD_ORIGINAL_EXEC_ARGUMENT_ERROR_NOT_CODE_NEGATION';review='EXACT_RECORDED_UNSUPPORTED_TIMEOUT_PARAMETER_FEEDBACK'
  groups[r['queue']]+=1;states[state]+=1;literal[r['literal_target_classification']]+=1
  nativeR+=bool(r['native_readable_reasoning_blocks']);texts+=bool(r['text_characters'])
  ledger.append({'owner_id':oid,'queue':r['queue'],'episode_id':r['episode_id'],'route_id':r['route_id'],'source_ids':r['source_ids'],
   'source_scope_at09_reservation':scope,'literal_target_classification':r['literal_target_classification'],
   'processing_disposition':state,'semantic_review_scope':review,'original_target_sha256_sorted':r['target_original_SHA256_sorted'],
   'audit_content':'OWNER1321_EXACT_CONTENT.audit.jsonl.gz','original_contexts':'ORIGINAL_CONTEXTS_343.audit.jsonl.gz',
   'new_positive_loss_admitted_by_this_lane':False,'future_review_required':state in{'HOLD_NEEDS_SEMANTIC_REVIEW','SCOPED_SEMANTIC_CANDIDATE_PENDING_ROOT_QA_AND_COMPILATION'},
   'candidate_profile':candidates[oid]['id']if oid in candidates else None})
 assert len(ledger)==1321 and sum(states.values())==1321
 with (OUT/'OWNER1321_DISPOSITION09.jsonl.gz').open('wb')as raw:
  with gzip.GzipFile(fileobj=raw,mode='wb',mtime=0)as f:
   for r in ledger:f.write((js(r)+'\n').encode())
 summary={'status':'ALL1321_EXACT_BODIES_RECOVERED_PER_OWNER_STATE_NOT_ALL_SEMANTICALLY_APPROVED',
  'owners':len(ledger),'episodes':343,'queue_counts':dict(groups),'disposition_counts':dict(states),'literal_classes':dict(literal),
  'owners_with_nonempty_public_text':texts,'owners_with_native_readable_R':nativeR,
  'qualified_KEEP_or_complete_autonomy_admitted':0,'new_positive_targets_admitted_by_lane':0,
  'scoped_resource_or_edit_candidates':5,'recorded_public_decision_text_candidates':12,
  'recorded_public_text_is_not_internal_thought':True,'native_R_absence_not_proof_provider_never_generated_R':True,
  'new_reservation_excluded_owner_count':len(reserved_ids),'reserved_owner_ids':reserved_ids,
  'reservation_sha256':sha(RES),'candidate_files':{f:sha(OUT/f)for f in ['FUNCTIONAL_CANDIDATES05.jsonl.gz','VISIBLE_DECISION_CANDIDATES12.jsonl.gz']},
  'script_sha256':sha(__file__),'weights_loaded':False,'training_started':False,'business_Teacher_Actor_calls':0,'curation_cost':'UNKNOWN_NOT_ZERO'}
 save(OUT/'LANE_SUMMARY09.json',summary)
 print(json.dumps({k:v for k,v in summary.items()if k in ['status','owners','queue_counts','disposition_counts','owners_with_nonempty_public_text','owners_with_native_readable_R','new_positive_targets_admitted_by_lane']}))
if __name__=='__main__':main()
