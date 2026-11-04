"""Root admission of explicitly audited authored data, never model readiness."""
from pathlib import Path
from collections import Counter
import hashlib,json
ROOT=Path(__file__).resolve().parents[3];WORK=ROOT/'output/20261031_wrd_curation11'
def load(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def pin(p):return {'path':str(p.resolve()),'bytes':p.stat().st_size,'sha256':sha(p)}
def save(p,x):p.parent.mkdir(parents=True,exist_ok=True);assert not p.exists();p.write_bytes((json.dumps(x,ensure_ascii=False,indent=2)+'\n').encode())
def main():
 paths=['semantic_review/FINAL_RUN07_QA.json','technical_qa01/ALL627_SYNTHETIC_TOKEN_MASK_SOURCE_QA.json',
 'technical_qa01/ALL832_CURRICULUM_BINARY_FOUR_FEATURES_QA.json',
 'technical_budget_qa01/ALL627_BUDGET_FRESH_DUAL_TOKEN_MASK_PAIRED_TARGET_QA.json',
 'technical_budget_qa01/ALL832_BUDGET_ACTUAL_ARRAY_FOUR_FEATURES_QA.json',
 'exposure_review/INDEPENDENT_EXPOSURE_QA11.json','public_doc_review/DOCS_QA11.json']
 evidence=[]
 for n in paths:
  p=WORK/n;j=load(p);assert j['status'].startswith('PASS'),('NOT_PASSED',n,j['status']);evidence.append(pin(p))
 base=ROOT/'output/20261027_wrd_main_v10/TRAINING_MANIFEST.json';assert sha(base)=='9aace2dc6b39d0dde3bafbf9f7f3d6763e485609017dd70a5c40c17a2c30277e'
 full=load(WORK/'curriculum01/CURRICULUM_MANIFEST11.json');budget=load(WORK/'budget_curriculum01/CURRICULUM_MANIFEST11.json')
 assert full['synthetic_counts']['targets']==budget['synthetic_counts']['targets']==627
 assert full['synthetic_counts']['positive_tokens']==budget['synthetic_counts']['positive_tokens']==57362
 selection={'schema':'wrd11-explicit-mutually-exclusive-curriculum-profile-selection','profiles':{},
  'unique_new_targets':627,'original_primary_targets':623,'available_unique_targets':1250,'default_process_unique_targets':832,
  'default_training_entrypoint':None,'training_started':False,'full_autonomous_WRD_ready':False}
 for name,directory in [('full_native53','curriculum01'),('budget_projection','budget_curriculum01')]:
  manifest=WORK/directory/'CURRICULUM_MANIFEST11.json';index=WORK/directory/'canonical_arrays11/ARRAY_INDEX11.json'
  selection['profiles'][name]={'manifest_relative_path':directory+'/CURRICULUM_MANIFEST11.json','manifest_sha256':sha(manifest),
   'index_relative_path':directory+'/canonical_arrays11/ARRAY_INDEX11.json','index_sha256':sha(index),'loader_relative_path':directory+'/curriculum_loader11.py',
   'loader_sha256':sha(WORK/directory/'curriculum_loader11.py'),'requires_existing_authenticated_checkpoint10':True,
   'native_request_equivalence_claimed':False,'not_to_be_combined_with_other_profile':True}
 save(WORK/'CURRICULUM_SELECTION11.json',selection)
 e=load(WORK/'exposure11_final/SUMMARY.json');stats={
  'schema':'wrd11-actual-unique-targets-profiles-and-training-exposure','design_revision':'5.0.54','change_id':'ALG-20261031-06',
  'primary_manifest_unchanged_sha256':sha(base),'original_primary_targets':623,'original_contract_targets':418,'original_process_targets':205,
  'new_selected_targets':627,'new_controller_conditional_targets':576,'new_resource_supported_targets':51,
  'new_resource_raw_cases':60,'repeated_resource_cost_cases_audit_only':9,
  'available_unique_targets':1250,'default_process_curriculum_unique_targets':832,
  'original_positive_tokens':227233,'new_positive_tokens':57362,'available_positive_tokens':284595,
  'original_process_positive_tokens':156341,'process_curriculum_positive_tokens':213703,
  'new_R_all_new_authored_tokens':19656,'new_A_unexecuted_native_intent_tokens':8966,'new_D_tokens':28740,'new_original_teacher_R_tokens':0,
  'original_source_groups_unchanged':44,'original_process_source_ids_unchanged':56,'new_enterprise_source_ids':0,
  'controller_primitive_families':32,'controller_family_labels_including_guards':40,'controller_mechanism_groups':13,'resource_mechanism_families':10,
  'single_premise_pairs':256,'cross_condition_and_policy_guard_pairs':64,'qa_only_nuisance_variants':576,
  'synthetic_conditional_KEEP_labels':32,'real_qualified_KEEP':0,'complete_native_autonomous_A_D_chains':0,
  'new_CPU_resource_runs':40,'new_CPU_fixture_checks':140,
  'synthetic_static_weight':0.05,'synthetic_weighted_mass':2868.1,'unique_pool_synthetic_weighted_fraction':full['synthetic_fraction_of_effective_process_supervision'],
  'profiles':{p:{'synthetic_counts':m['synthetic_counts'],'synthetic_by_stage':m['synthetic_by_stage'],
    'new_actual_binary_files':1881,'new_actual_binary_bytes':load(WORK/d/'canonical_arrays11/ARRAY_INDEX11.json')['binary_bytes'],
    'one_unique_pass_process_sequence_tokens':m['real_process_counts']['sequence_tokens']+m['synthetic_counts']['sequence_tokens']} for p,d,m in [('full_native53','curriculum01',full),('budget_projection','budget_curriculum01',budget)]},
  'new_profile_static_sequence_reduction_fraction':1-budget['synthetic_counts']['sequence_tokens']/full['synthetic_counts']['sequence_tokens'],
  'gpu_hours_energy_and_quality_reduction_not_measured':True,'exposure_summary':e,
  'independent24_challenges':{'fully_comparable_pass':4,'partial_subproblem_pass':4,'not_comparable':16,'not_student_evaluation':True},
  'fixed22_development_probes':{'before_failed':19,'after_passed':22,'used_for_revision_not_unseen_test':True},
  'source_original226_and_all_reserved_isolation_kept':True,'component_data_prepared':True,'Spark_training_runtime_verified':False,
  'full_WRD_training_ready':False,'training_started':False,'current_qualified_student_skills':0,'cost_per_qualified_skill':'UNDEFINED_K_ZERO',
  'AI_curation_CPU_costs':'UNKNOWN_NOT_ZERO'}
 save(WORK/'DATA_STATISTICS11.json',stats);save(ROOT/'research/plans/20261031_wrd_curation11/DATA_STATISTICS11.json',stats)
 receipt={'status':'ROOT_ACCEPTED_FINITE_CURRICULUM_DATA_NOT_FULL_AUTONOMOUS_READY','design_revision':'5.0.54',
  'unique_new_targets':627,'unique_profiles_not_double_counted':True,'original623_main_unchanged_sha256':sha(base),
  'evidence':evidence,'selection':pin(WORK/'CURRICULUM_SELECTION11.json'),'statistics':pin(WORK/'DATA_STATISTICS11.json'),
  'all_future_or_rejected_records_audit_only':True,'original_teacher_R_not_replaced':True,'qualified_KEEP_not_inferred_from_constructed_labels':True,
  'training_started':False,'weights_loaded':False,'new_business_native_sessions':0,'full_pipeline_ready':False,'script':pin(Path(__file__))}
 save(WORK/'ROOT_ACCEPTANCE11.json',receipt)
 print(json.dumps({'status':receipt['status'],'new_targets':627,'total_unique':1250,'process_unique':832}))
if __name__=='__main__':main()
