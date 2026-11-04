"""Root-freeze the explicit reviewed 29 additions and one scoped withdrawal."""
from pathlib import Path
import argparse,gzip,hashlib,importlib.util,json
ROOT=Path(__file__).resolve().parents[3];DATA=ROOT/'output/20261027_wrd_main_v10';WORK=ROOT/'output/20261031_wrd_curation10'
BASE='01380a42195dd888aded4140db7dc7013364f6bc66594502487387259d174f42'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def pin(p):p=Path(p).resolve();return{'path':str(p),'bytes':p.stat().st_size,'sha256':sha(p)}
def save(p,x):p.parent.mkdir(parents=True,exist_ok=True);assert not p.exists();p.write_bytes((json.dumps(x,ensure_ascii=False,indent=2)+'\n').encode())
def main(a):
 tool=ROOT/'research/data_prep/wrd_curation10/admit10.py';s=importlib.util.spec_from_file_location('freeze10_count',tool);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
 assert sha(DATA/'TRAINING_MANIFEST.json')==BASE
 report=load(a.report);new=[r for f in report['files']for _,r in m.raw_rows(m.verify_ref(a.report.parent,f))]
 assert len(new)==29 and sum(r['supervised_tokens']for r in new)==20984
 qas=[WORK/'reasoning_native10/EARLY15_INDEPENDENT_SOURCE_TOKEN_MASK_QA.json',
  WORK/'resource_review10/meeting_gen01/INDEPENDENT_TOKEN_MASK_QA.json',
  WORK/'identity_semantic/COMPONENT3_TOKEN_PEER_QA.json',a.r5qa]
 for p in qas:assert load(p)['status'].startswith('PASS'),str(p)
 isolation=WORK/'admission/NEW29_INPUT_ISOLATION_QA.json';assert load(isolation)['status'].startswith('PASS')
 assert load(isolation)['new_compilation_report']['sha256']==sha(a.report)
 direct=load(WORK/'lineage/revocations.json');revoked=set(direct['revoke_view_ids']);assert revoked=={'process09-0f1603b601613eac2fecb014'}
 old=load(DATA/'TRAINING_MANIFEST.json');oldrows=[r for _,_,r in m.bank_records(DATA,old)]
 kept=[r for r in oldrows if r['id']not in revoked];assert len(kept)==594
 sources=set();scope={r['source_id']:r for _,r in m.raw_rows(DATA/'clean_inputs/source_scope.metadata.jsonl.gz')}
 reserve=load(ROOT/'output/20261031_wrd_curation09/holdout/holdout_reservation.json');sources.update(reserve['reserved_source_ids']);sources.add('conv_34b56ae9c535')
 sources.update(load(ROOT/'output/20261031_wrd_curation09/holdout/PROTECTED_CURRENT569_REVOCATION_CLOSURE.json')['revoke_source_ids'])
 groups={scope[s]['component_id']for s in sources}
 for r in new+kept:
  assert not sources.intersection(r['source_ids'])and not groups.intersection(scope[s]['component_id']for s in r['source_ids'])
  assert all(scope[s]['status']=='TRAIN'for s in r['source_ids'])
 ids={r['id']for r in new};assert len(ids)==29 and not ids.intersection(r['id']for r in oldrows)
 retained=m.recount(kept);final=m.recount(kept+new)
 assert {k:final['actual_counts'][k]for k in ['targets','supervised_tokens','input_tokens']}=={'targets':623,'supervised_tokens':227233,'input_tokens':3853977}
 assert final['supervision_origin_tokens']['original_native_R_tokens']==old['supervision_origin_tokens']['original_native_R_tokens']+201
 assert final['supervision_origin_tokens']['historical_original_R_tokens']==old['supervision_origin_tokens']['historical_original_R_tokens']
 assert final['supervision_origin_tokens']['recorded_compatible_R_excerpt_recontextualized_tokens']==4326
 evidence=[WORK/'early_reads/ROOT_SEMANTIC_READ_REVIEW.json',
  WORK/'resource_review10/meeting_gen01/RESOURCE_SEMANTIC_REVIEW.json',WORK/'resource_review10/meeting_gen01/SOURCE_ARTIFACT_QA.json',
  WORK/'identity_semantic/SEMANTIC_RECOMMENDATIONS.json',WORK/'identity_semantic/TOOL_ABI_V2_FIX_REVIEW.json',WORK/'identity_semantic/COMPONENT3_SOURCE_PEER_QA.json',
  WORK/'reasoning_semantic10/ROOT_R5_SCOPED_SEMANTIC_APPROVAL.json',WORK/'reasoning_semantic10/FROZEN5_SEMANTIC_STATE_AND_SOURCE_QA.json',
  WORK/'reasoning_semantic10/OLD_VS_REVISED_REAL_COUNTEREXAMPLES.json',WORK/'lineage/P0_QA.json']
 for ref in load(WORK/'reasoning_semantic10/ROOT_R5_SCOPED_SEMANTIC_APPROVAL.json')['evidence']:assert pin(ref['path'])==ref,'ROOT_R5_EVIDENCE_CHANGED'
 acceptance={'status':'ADMIT_ROOT_REVIEWED_CURATION10_LOCAL_R_READ_RESOURCE_REPAIR_AND_HOLD_ONLY',
  'record_ids':sorted(ids),'compilation_report_sha256':sha(a.report),'record_count':len(new),'positive_tokens':20984,
  'semantic_evidence':[pin(p)for p in evidence],'independent_token_and_mask_evidence':[pin(p)for p in qas],
  'new_compatible_original_R_tokens':201,'new_recontextualized_original_compatible_R_tokens':4326,
  'new_authored_R_tokens':135,'new_recorded_visible_D_tokens':71,
  'source_and_actor_independence_not_inferred_from_view_count':True,'original_errors_and_versions_preserved':True,
  'new_business_calls':0,'full_autonomy':0,'qualified_KEEP':0,'human_gold':False,'training_started':False,'script':pin(__file__)}
 save(WORK/'admission/ROOT_SEMANTIC_ACCEPTANCE10.json',acceptance)
 rev={'status':'ROOT_APPROVED_REVOCATION_SET','baseline_manifest_sha256':BASE,
  'revoked_record_ids':sorted(revoked),'protected_source_ids':sorted(sources),'protected_source_scope_components':sorted(groups),
  'new_allowed_record_ids':sorted(ids),'new_revoked_record_ids':[],
  'P0_immutable_revocation':pin(WORK/'lineage/revocations.json'),'source_withdrawal_due_to_this_P0':[],
  'reason':'One specific unresolved protected-producer linkage is temporarily excluded; no proven contamination or whole-source withdrawal claimed. Old/new reserved sources remain excluded.'}
 save(WORK/'admission/ROOT_REVOCATION_SET10.json',rev)
 technical={'status':'PASS_COMPOSED_INDEPENDENT_DISJOINT_15_6_3_5_FULL_GEOMETRY_QA','record_ids':sorted(ids),
  'proofs':[pin(p)for p in qas],'combined_compilation_report':pin(a.report),'no_new_tokenizer_calls_in_composition':True,'training_started':False}
 save(WORK/'admission/PINNED_INDEPENDENT_NEW29_TECH_QA.json',technical)
 freeze={'status':'ROOT_FROZEN_CURATION10_STAGE_AUTHORIZATION','admit10_script_sha256':sha(tool),'baseline_manifest_sha256':BASE,
  'revocations':pin(WORK/'admission/ROOT_REVOCATION_SET10.json'),'new_compilation_report':pin(a.report),
  'root_semantic_acceptance':pin(WORK/'admission/ROOT_SEMANTIC_ACCEPTANCE10.json'),
  'independent_token_qa':pin(WORK/'admission/PINNED_INDEPENDENT_NEW29_TECH_QA.json'),
  'independent_protection_qa':pin(WORK/'lineage/P0_QA.json'),'new_candidate_prefix_scan':pin(isolation),
  'new_allowed_record_ids':sorted(ids),'new_revoked_record_ids':[],'new_bank_relative':'compiled/curation10_process_01',
  'expected_rebased_counts':{k:retained['actual_counts'][k]for k in ['targets','supervised_tokens','input_tokens']},
  'expected_final_counts':{k:final['actual_counts'][k]for k in ['targets','supervised_tokens','input_tokens']},
  'training_started':False,'model_weights_loaded':False}
 save(WORK/'admission/FROZEN_ADMISSION_INPUTS10.json',freeze)
 print(json.dumps({'freeze':pin(WORK/'admission/FROZEN_ADMISSION_INPUTS10.json'),'expected_counts':freeze['expected_final_counts']}))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--report',type=Path,required=True);p.add_argument('--r5qa',type=Path,required=True);main(p.parse_args())
