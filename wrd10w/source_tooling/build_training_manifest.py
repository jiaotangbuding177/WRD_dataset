"""Build an explicit, non-launching manifest from approved compiled banks.

Only listed banks enter this view. Historical/withdrawn outputs are never
discovered by a recursive training-data glob.
"""
from collections import Counter, defaultdict
import gzip
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'output/20261027_wrd_main_v10'
ACTIVE=['compiled/source_events_02','compiled/native_A_partial_03','compiled/native_B_partial_01','compiled/real_state_repair_02','compiled/c_review_dataset_02','compiled/historical_semantic_R_26_01','compiled/historical_v6_native_repair_01','compiled/native_CV_B_partial_01']
ROOT_ADMISSIONS={
    'compiled/real_state_repair_02':'real_state_reconstruction_02/ROOT_SEMANTIC_ADMISSION.json',
    'compiled/c_review_dataset_02':'c_review_dataset_01/semantic_revision_02/ROOT_SEMANTIC_ADMISSION.json',
    'compiled/historical_semantic_R_26_01':'compiled/historical_semantic_R_26_01/ROOT_SEMANTIC_ADMISSION.json',
    'compiled/historical_v6_native_repair_01':'historical_v6_native_repair_01/ROOT_SEMANTIC_ADMISSION.json',
    'compiled/native_CV_B_partial_01':'compiled/native_CV_B_partial_01/ROOT_SEMANTIC_ADMISSION.json',
}

def digest(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(1048576),b''):h.update(b)
    return h.hexdigest()
def load(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def save(p,r):p.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

class Union:
    def __init__(self):self.p={}
    def find(self,x):
        self.p.setdefault(x,x)
        if self.p[x]!=x:self.p[x]=self.find(self.p[x])
        return self.p[x]
    def join(self,a,b):
        a,b=self.find(a),self.find(b)
        if a!=b:self.p[max(a,b)]=min(a,b)

def main():
    counts=Counter();stages=defaultdict(Counter);banks=defaultdict(Counter)
    files=[];reports=[];seen=set();source_ids=set();u=Union();owner_ids=set()
    bank_groups=defaultdict(set);action_owners=set();native_R_owners=set()
    projected_action_owners=set();historical_R_owners=set();canonical_projected_owners=set()
    admission_receipts=[];origin_tokens=Counter()
    for relative in ACTIVE:
        folder=OUT/relative;report=load(folder/'COMPILATION_REPORT.json')
        admission=None;admission_ids=set();observed_ids=set()
        if relative in ROOT_ADMISSIONS:
            proof_path=OUT/ROOT_ADMISSIONS[relative];admission=load(proof_path)
            assert admission['status'] in {'ADMIT_LOCAL_REAL_STATE_REPAIR_WITH_EXPLICIT_NEW_AUTHOR','ADMIT_LOCAL_C_PROCESS_AND_AUTHORED_COST_STOP','ADMIT_PARTIAL_HISTORICAL_R_SEMANTIC_STAGE','ADMIT_NEW_AUTHORED_NATIVE_RESOURCE_REPAIR_PROJECTION','ADMIT_ORIGINAL_NATIVE_CV_PROCESS_R_AND_LOCAL_ACTIONS'}
            assert admission['compilation_report_sha256']==digest(folder/'COMPILATION_REPORT.json')
            admission_ids=set(admission['record_ids'])
            assert len(admission_ids)==len(admission['record_ids'])
            admission_receipts.append({'path':ROOT_ADMISSIONS[relative],'sha256':digest(proof_path),
                'compiled_bank':relative,'scope':'local_revalidated_real_state_only_not_complete_WRD'})
        reports.append({'path':relative+'/COMPILATION_REPORT.json','sha256':digest(folder/'COMPILATION_REPORT.json')})
        for f in report['files']:
            path=folder/f['path'];assert digest(path)==f['sha256'] and path.stat().st_size==f['bytes']
            files.append({**f,'path':relative+'/'+f['path']})
            with gzip.open(path,'rt',encoding='utf-8') as handle:
                for line in handle:
                    r=json.loads(line);assert r['id'] not in seen;seen.add(r['id'])
                    metadata=r.get('original_record_metadata',{})
                    observed_ids.add(r['id'])
                    if metadata.get('root_main_admission') is False:
                        assert admission and r['id'] in admission_ids,'candidate_requires_explicit_root_admission'
                    owner=metadata.get('owner_id',r['id']);assert owner not in owner_ids;owner_ids.add(owner)
                    assert r['split']=='train' and r['total_tokens']==len(r['input_ids'])<=32768
                    assert sum(b-a for a,b,_,_ in r['supervision_spans'])==r['supervised_tokens']>0
                    for target in r['targets']:
                        if not any(span[2]=='A' for span in target.get('owned_supervision_spans',[])):continue
                        for call in r['messages'][target['message_index']].get('tool_calls',[]):
                            key=call['id']
                            owners=projected_action_owners if metadata.get('actual_native_tool_dispatch') is False else action_owners
                            assert key and key not in action_owners|projected_action_owners,'duplicate_tool_action_exposure'
                            owners.add(key)
                    components=r['supervised_tokens_by_component']
                    if r['bank'] in {'native_wrd_main','native_C_review_partial_02','native_CV_B_training_01'}:
                        if components.get('R',0):
                            key=metadata['actual_response_sha256'] if r['bank']=='native_CV_B_training_01' else metadata['evidence']['response_sha256']
                            assert key not in native_R_owners,'duplicate_original_R_response_view'
                            native_R_owners.add(key)
                            origin_tokens['original_native_R_tokens']+=components['R']
                        if r['bank']=='native_CV_B_training_01':origin_tokens['original_native_local_process_A_tokens']+=components.get('A',0)
                    elif r['bank']=='real_state_repair_main':
                        origin_tokens['new_authored_R_tokens']+=components.get('R',0)
                        origin_tokens['revalidated_original_action_A_tokens']+=components.get('A',0)
                    elif r['bank']=='source_contract_main':
                        origin_tokens['new_source_contract_annotation_tokens']+=r['supervised_tokens']
                    elif r['bank']=='native_C_execution_local_02':
                        origin_tokens['original_native_execution_A_tokens']+=components.get('A',0)
                    elif r['bank']=='new_real_state_cost_stop_02':
                        origin_tokens['new_authored_R_tokens']+=components.get('R',0)
                        origin_tokens['new_authored_cost_stop_D_tokens']+=components.get('D',0)
                    elif r['bank']=='historical_semantic_R_main':
                        key=metadata['canonical_original_response_owner']
                        assert key not in historical_R_owners,'duplicate_historical_original_R_response_view'
                        historical_R_owners.add(key)
                        origin_tokens['historical_original_R_tokens']+=components.get('R',0)
                        assert not components.get('A',0) and not components.get('D',0)
                    elif r['bank']=='historical_v6_native_repair_01':
                        key=metadata['target_owner']['canonical_original_action_owner_id']
                        assert key not in canonical_projected_owners,'duplicate_historical_action_projection_view'
                        canonical_projected_owners.add(key)
                        origin_tokens['new_authored_R_tokens']+=components.get('R',0)
                        origin_tokens['new_authored_native_action_projection_A_tokens']+=components.get('A',0)
                    else:origin_tokens['other_explicitly_named_bank_tokens']+=r['supervised_tokens']
                    key='record:'+r['id'];u.find(key)
                    if r.get('source_group_id'):u.join(key,'group:'+r['source_group_id'])
                    for s in r.get('source_ids',[]):source_ids.add(s);u.join(key,'source:'+s)
                    for c in (counts,stages[r['stage']],banks[r['bank']]):
                        c['sequences']+=1;c['targets']+=len(metadata.get('supervision_message_indices',[len(r['messages'])-1]))
                        c['input_tokens']+=r['total_tokens'];c['supervised_tokens']+=r['supervised_tokens']
                        c['le16k_sequences']+=r['total_tokens']<=16384
                        c['le32k_sequences']+=r['total_tokens']<=32768
                        for component,n in r['supervised_tokens_by_component'].items():c['component_'+component]+=n
                    bank_groups[r['bank']].add(u.find(key))
        if admission:assert observed_ids==admission_ids,'root_admission_ids_do_not_match_bank'
    components={u.find('record:'+x) for x in seen}
    report={'schema_version':'wrd-verified-main-v10-actual-manifest','status':'PARTIAL_MAIN_SUBTASKS_ONLY_FULL_WRD_NOT_READY',
        'design_revision':'5.0.41','change_id':'ALG-20261027-05','workflow_schema_version':'workflow-pipeline-v1',
        'actual_train_files':files,'active_compilation_reports':reports,'actual_counts':dict(counts),
        'by_stage':{k:dict(v) for k,v in stages.items()},'by_bank':{k:dict(v) for k,v in banks.items()},
        'supervision_origin_tokens':dict(origin_tokens),'external_root_admission_receipts':admission_receipts,
        'actual_action_owners_with_positive_loss':len(action_owners),'original_native_R_response_owners':len(native_R_owners),
        'new_authored_projected_action_owners':len(projected_action_owners),'historical_original_R_response_owners':len(historical_R_owners),
        'actual_native_action_and_offline_projection_are_different_evidence_units':True,
        'distinct_source_ids':len(source_ids),'source_connected_components_across_banks':len(components),
        'original_source_group_and_teacher_batch_component_are_different_units':True,
        'all_windows_share_frozen_train_ancestry':True,'original226_and_newH_and_static_dev_test_excluded':True,
        'main_means_approved_semantic_subtask_not_completed_autonomous_pipeline':True,
        'full_native_53tool_request_coverage_is_not_core7_student_view_coverage':True,
        'observed_stage_linked_chains':1,'positive_qualified_retained_skill_chains':0,
        'single_native_session_autonomous_A_through_D_demonstrations':0,
        'observed_chain_is_separately_dispatched_native_stages_ending_STOP':True,
        'conditional_native64_profile':{'path':'native_context_64k_01/FINAL_MANIFEST.json',
            'sha256':digest(OUT/'native_context_64k_01/FINAL_MANIFEST.json'),
            'not_in_default_active_counts':True,'must_replace_overlapping_core32_owners_not_add_them':True,
            'Spark_position_attention_memory_and_serving_budget_not_validated':True},
        'missing_main_stages':['B_multimechanism_verified_resource_construction','multimechanism_C_outcome_supervision','positive_retained_packaging_chains','native_autonomous_controller'],
        'engineering_targets':{'nontrivial_main_targets':2000,'main_supervised_tokens':1000000,'clean_original_source_groups':50,'mechanism_families':12,'real_make_trial_feedback_chain_required':True},
        'full_WRD_main_training_ready':False,'default_full_pipeline_training_entrypoint':None,
        'model_weights_loaded':False,'training_started':False,'is_training_launch_configuration':False,
        'withdrawn_local_banks':['compiled/source_events_01','clean_inputs/source_event_release_01','compiled/native_A_partial_01','compiled/native_A_partial_02','compiled/real_state_repair_01','compiled/c_review_dataset_01','compiled/historical_semantic_R_05','compiled/historical_semantic_R_05_02','compiled/historical_semantic_R_05_03'],
        'withdrawn_banks_are_not_to_be_added_to_this_manifest':True,
        'v9_aux_not_implicitly_imported_prepare_producer_erratum_pending':True,
        'script_sha256':digest(Path(__file__))}
    save(OUT/'TRAINING_MANIFEST.json',report)
    save(OUT/'ACTUAL_DATA_STATISTICS.json',{k:report[k] for k in ['status','actual_counts','by_stage','by_bank','supervision_origin_tokens','actual_action_owners_with_positive_loss','original_native_R_response_owners','new_authored_projected_action_owners','historical_original_R_response_owners','distinct_source_ids','source_connected_components_across_banks','missing_main_stages','engineering_targets','full_WRD_main_training_ready','training_started']})
    print(json.dumps({'counts':dict(counts),'sources':len(source_ids),'components':len(components),'full_WRD_ready':False}))

if __name__=='__main__':main()
