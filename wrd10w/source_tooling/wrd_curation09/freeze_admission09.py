"""Freeze the concrete reviewed 49-row addition and 23-row revocation."""
from pathlib import Path
from collections import Counter
import argparse,gzip,hashlib,importlib.util,json
ROOT=Path(__file__).resolve().parents[3];WORK=ROOT/'output/20261031_wrd_curation09';DATA=ROOT/'output/20261027_wrd_main_v10'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def save(p,x):p.parent.mkdir(parents=True,exist_ok=True);assert not p.exists();p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def pin(p):p=Path(p).resolve();return {'path':str(p),'bytes':p.stat().st_size,'sha256':sha(p)}
def rows(p):
 with gzip.open(p,'rt',encoding='utf-8-sig')as f:
  for l in f:
   if l.strip():yield json.loads(l)
def main(a):
 dest=WORK/'admission';dest.mkdir(exist_ok=False)
 tool=ROOT/'research/data_prep/wrd_curation09/admit09.py';spec=importlib.util.spec_from_file_location('freeze09_recounter',tool);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
 report=load(a.report);records=[r for f in report['files']for r in rows(mod.verify_ref(a.report.parent,f))];assert len(records)==49
 qas=[WORK/'token_peer/run01/INDEPENDENT_TOKEN_MASK_SOURCE_OWNER_QA.json',a.qa17]
 for q in qas:assert load(q)['status'].startswith('PASS')
 assert load(qas[0])['compiled_report']['sha256']==sha(WORK/'compiled_staging01/compiled02/COMPILATION_REPORT.json')
 closure=WORK/'holdout/PROTECTED_CURRENT569_REVOCATION_CLOSURE.json';rev=load(closure);assert len(rev['revoke_current_view_ids'])==23
 reserve=load(WORK/'holdout/holdout_reservation.json');forbidden=set(reserve['reserved_source_ids'])|set(rev['revoke_source_ids'])
 groups=set(reserve['reserved_source_scope_components'])|set(rev['revoke_source_scope_component_ids'])
 scope={r['source_id']:r for r in rows(DATA/'clean_inputs/source_scope.metadata.jsonl.gz')}
 for r in records:
  assert not forbidden.intersection(r['source_ids'])and not groups.intersection(scope[s]['component_id']for s in r['source_ids'])
 assert a.protection.is_file()
 save(dest/'PINNED_INDEPENDENT_NEW49_TECH_QA.json',{'status':'PASS_COMPOSITION_OF_DISJOINT_INDEPENDENT_32_AND_17_TECHNICAL_QA','proofs':[pin(p)for p in qas],
  'combined_compilation_report':pin(a.report),'record_ids':sorted(r['id']for r in records),'source_reports':report['source_compilation_reports'],
  'no_new_tokenizer_calls_by_composition':True,'semantics_not_inferred_from_arrays':True,'training_started':False})
 resource_paths=[WORK/'resource_qa02/workspace/RESULT.json',WORK/'extra_resource_qa/workspace/RESULT.json',WORK/'lesson_qa/workspace/RESULT.json',
  WORK/'process_peer_qa/INDEPENDENT_PEER_REVIEW.json',WORK/'writers/ALL31_SEMANTIC_VERDICTS.json',WORK/'process/SEMANTIC_REVIEW05.json',
  WORK/'process/VISIBLE_DECISION_REVIEW12.json',WORK/'ROOT_ADDITIONAL_CODE_EXCLUSIONS09.json',a.qa17,
  WORK/'process/batch02/resource_qa03/workspace/qa_outputs/RESULTS.json',WORK/'process/batch02/CANDIDATE_FINAL14_v2_TRANSFORM.json',
  WORK/'process/batch02/CANDIDATE_ADDITIONAL03_v3_TRANSFORM.json']
 assert all(p.is_file()for p in resource_paths)
 acceptance={'status':'ADMIT_ROOT_REVIEWED_SCOPED_RESOURCE_ACTION_VISIBLE_DECISION_AND_LOCAL_REPAIR_ONLY','record_ids':sorted(r['id']for r in records),
  'compilation_report_sha256':sha(a.report),'record_count':49,'positive_tokens':sum(r['supervised_tokens']for r in records),
  'semantic_evidence':[pin(p)for p in resource_paths],'protection_and_actual_prefix_scan':pin(a.protection),'baseline_correction':pin(closure),
  'rows':[{'id':r['id'],'source_ids':r['source_ids'],'stage':r['stage'],'components':r['supervised_tokens_by_component'],
    'credit':r['original_record_metadata'].get('credit')or r['original_record_metadata'].get('semantic_scope'),
    'recorded_R_new_positive':False,'whole_business_or_skill_utility_approved':False}for r in records],
  'new_author_R_tokens':261,'new_original_teacher_R_tokens':0,'human_gold':False,'full_autonomous_demonstrations':0,'qualified_KEEP':0,
  'original_bodies_errors_feedback_revisions_preserved':True,'post_action_observations_used_only_for_credit_not_earlier_input':True,
  'known_bad_content_and_crossing_tokens_masked':True,'original_system_capture_gaps_not_repaired_by_projection':True,
  'execution_scope':'Offline data admission only; no weight loading, training or new business Teacher/Actor',
  'script_sha256':sha(__file__)}
 save(dest/'ROOT_SEMANTIC_ACCEPTANCE09.json',acceptance)
 old=load(DATA/'TRAINING_MANIFEST.json');assert sha(DATA/'TRAINING_MANIFEST.json')=='cbb233f2a44bcb61035e4fcb046830178510529cb149cf3ea6100c613babe555'
 oldrows=[r for f in old['actual_train_files']for r in rows(mod.verify_ref(DATA,f))];revoked=set(rev['revoke_current_view_ids']);keep=[r for r in oldrows if r['id']not in revoked]
 rebased=mod.recount(keep);final=mod.recount(keep+records)
 assert len(keep)==546 and final['actual_counts']['targets']==595 and final['actual_counts']['supervised_tokens']==216154 and final['actual_counts']['input_tokens']==3518732
 for k in ['original_native_R_tokens','historical_original_R_tokens','recorded_cumulative_original_R_excerpt_tokens']:
  assert final['supervision_origin_tokens'][k]==old['supervision_origin_tokens'][k]
 freeze={'status':'ROOT_FROZEN_CURATION09_STAGE_AUTHORIZATION','admit09_script_sha256':sha(tool),'baseline_manifest_sha256':sha(DATA/'TRAINING_MANIFEST.json'),
  'revocations':pin(closure),'new_compilation_report':pin(a.report),'root_semantic_acceptance':pin(dest/'ROOT_SEMANTIC_ACCEPTANCE09.json'),
  'independent_token_qa':pin(dest/'PINNED_INDEPENDENT_NEW49_TECH_QA.json'),'independent_protection_qa':pin(WORK/'holdout/PROTECTED_VS_TRAIN_INDEPENDENT_QA.json'),
  'new_candidate_prefix_scan':pin(a.protection),'new_allowed_record_ids':acceptance['record_ids'],'new_revoked_record_ids':[],
  'new_bank_relative':'compiled/curation09_process_01','expected_rebased_counts':{k:rebased['actual_counts'][k]for k in ['targets','supervised_tokens','input_tokens']},
  'expected_final_counts':{k:final['actual_counts'][k]for k in ['targets','supervised_tokens','input_tokens']},'training_started':False}
 save(dest/'FROZEN_ADMISSION_INPUTS09.json',freeze)
 print(json.dumps({'freeze':pin(dest/'FROZEN_ADMISSION_INPUTS09.json'),'expected_final_counts':freeze['expected_final_counts']}))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--report',type=Path,required=True);p.add_argument('--qa17',type=Path,required=True);p.add_argument('--protection',type=Path,required=True);main(p.parse_args())
