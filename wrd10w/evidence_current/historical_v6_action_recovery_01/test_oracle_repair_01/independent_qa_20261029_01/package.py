"""Portable, content-hashed selection for actual root-pending oracle arrays."""
import gzip
import hashlib
import json
from pathlib import Path
HERE=Path(__file__).resolve().parent;RESOURCE=HERE.parent;RECOVERY=RESOURCE.parent;BANK=RESOURCE/'native_projection_01'
def load(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def ref(p):
    p=Path(p);return {'path':p.relative_to(RECOVERY).as_posix(),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
def main():
    path=BANK/'PORTABLE_SELECTION.json';assert not path.exists();qa=load(BANK/'INDEPENDENT_QA.json');assert qa['status']=='PASS';source=load(RESOURCE/'SOURCE_STATE_AND_RANGES.json');profiles={}
    for profile in('core7','full53'):
        compiled=BANK/f'native_oracle.{profile}.compiled.jsonl.gz'
        with gzip.open(compiled,'rt',encoding='utf-8')as f:row=json.loads(next(f))
        profiles[profile]={'messages':ref(BANK/f'native_oracle.{profile}.raw.jsonl.gz'),'compiled':ref(compiled),'arrays':[ref(BANK/r['path'])for r in row['binary_arrays']],'sequences':1,'total_sequence_tokens':row['total_tokens'],'supervised_tokens':row['supervised_tokens'],'by_component':row['supervised_tokens_by_component'],'loss_multiplier':.25,'default_training_candidate':profile=='core7','strict_future_serving':next(x for x in qa['details']if x['profile']==profile)}
    actualrefs=[]
    for field in('original_action_response','original_old_test_creator_response','original_asof_request','original_cumulative_R_response'):
        p=Path(source[field]['path']);assert p.is_file();r=ref(p);assert r['sha256']==source[field]['sha256'];actualrefs.append({'role':field,**r})
    files=[ref(p)for p in sorted(RESOURCE.rglob('*'))if p.is_file()and p!=path]
    result={'schema_version':'wrd-explicit-new-state-cumulative-R-native-edit-portable-entry-v1','status':'ACTUAL_ARRAYS_INDEPENDENT_QA_COMPLETE_SEMANTIC_PEER_AND_ROOT_PENDING','path_base':'All path fields below are POSIX relative to recovery_root. Join path parts, not Windows backslash substrings.','recovery_root_relative_to_this_entry':'../..','source_ids':['conv_b5e6f3d3bab9'],'current_source_status':'TRAIN','canonical_R_owner':'historical_cumulative_R:'+source['original_cumulative_R_owner'],'canonical_action_owner':qa['canonical_owners']['canonical_original_action_owner_id'],'R_and_A_have_different_recorded_original_owners':True,'all_views_of_each_original_owner_mutually_exclusive':True,'core_full_profiles_same_target_not_additive':True,'profiles':profiles,
        'original_R_identity':source['original_R_identity'],'original_R_contiguous_excerpt':{'start':source['original_R_excerpt_source_start'],'end':source['original_R_excerpt_source_end'],'characters':source['original_R_excerpt_characters'],'sha256':source['original_R_excerpt_sha256'],'positive_characters':sum(x['end']-x['start']for x in source['positive_excerpt_ranges']),'all_other_original_full_R_mask0_audit_only':True},'original_raw_sources':actualrefs,'source_state_and_ranges':ref(RESOURCE/'SOURCE_STATE_AND_RANGES.json'),'independent_token_mask_and_array_QA':ref(BANK/'INDEPENDENT_QA.json'),'exact_current_526_positive_mask_dedup':ref(HERE/'EXACT_POSITIVE_DEDUP.json'),'finite_resource_QA':ref(RESOURCE/'RESOURCE_QA.json'),'state_root':(RESOURCE/'state_before_edit').relative_to(RECOVERY).as_posix(),'state_files':[ref(p)for p in sorted((RESOURCE/'state_before_edit').rglob('*'))if p.is_file()],'all_actual_resource_bank_QA_files':files,'new_functional_state_and_native_action_authored_by':'Codex AI silver curation; not original Teacher native condition','original_R_text_author':'Recorded historical teacher cumulative thought; excerpt unchanged, no new summary relabelled as original R','future_PASS_and_QA_not_in_prestate':True,'complete_pipeline_demonstrations':0,'qualified_skills':0,'root_main_admission':False,'ACTIVE_modified':False,'training_started':False,'weights_loaded':False,'new_Agent_calls':0}
    path.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'status':result['status'],'entry':ref(path),'profile_counts':{k:{'sequences':v['sequences'],'total':v['total_sequence_tokens'],'supervised':v['supervised_tokens']}for k,v in profiles.items()},'actual_files':len(files)}))
if __name__=='__main__':main()
