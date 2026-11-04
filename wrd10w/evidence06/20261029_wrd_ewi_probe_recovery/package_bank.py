"""Freeze portable actual construction arrays; semantic admission is external."""
import gzip
import hashlib
import json
from pathlib import Path
HERE=Path(__file__).resolve().parent;BANK=HERE/'native_construction_01'
def load(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def ref(p):p=Path(p);return{'path':p.relative_to(HERE).as_posix(),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
def main():
    path=HERE/'PORTABLE_SELECTION.json';assert not path.exists();qa=load(BANK/'INDEPENDENT_QA.json');assert qa['status']=='PASS';profiles={}
    for profile in('core7','full53'):
        compiled=BANK/f'math_resource.{profile}.compiled.jsonl.gz'
        with gzip.open(compiled,'rt',encoding='utf-8')as f:row=json.loads(next(f))
        profiles[profile]={'messages':ref(BANK/f'math_resource.{profile}.raw.jsonl.gz'),'compiled':ref(compiled),'arrays':[ref(BANK/x['path'])for x in row['binary_arrays']],'sequences':1,'total_sequence_tokens':row['total_tokens'],'positive_A':row['supervised_tokens'],'positive_R':0,'loss_multiplier':.25,'default_training_candidate':profile=='core7','strict_future_serving':next(x for x in qa['details']if x['profile']==profile)}
    files=[ref(p)for p in sorted(HERE.rglob('*'))if p.is_file()and p!=path]
    result={'schema':'wrd-scoped-EWI-math-resource-construction-portable-entry-v1','status':'ACTUAL_ARRAYS_FINITE_MATH_QA_AND_INDEPENDENT_MASK_QA_READY_PEER_ROOT_PENDING','path_base':'All paths are POSIX relative to this bundle directory. Resolve path parts; do not use Windows substring filters.','source_ids':['conv_1702b763a7ee'],'current_source_status':'TRAIN','canonical_A_owner':'historical_EWI_action:8856374c439400f01448d478','source_original_response_owner':'8856374c439400f01448d478','source_response_original_R_already_in_main26':True,'new_R_positive_tokens':0,'R_and_A_component_ownership_separate':True,'all_A_views_of_original_response_mutually_exclusive':True,'core_full_profiles_not_additive':True,'profiles':profiles,'state_root':'state_before_write','state_has_no_target_code_or_future_PASS':True,'original_source_function_author':'Recorded historical teacher exact LF action code; physical CRLF source file separately pinned','new_functional_input_header_and_entrypoint_author':'Codex AI silver curation; not original Teacher native-write','original_request_SSE_code_operation_and_finite_receipt_preserved':True,'source_semantic_review':ref(HERE/'SOURCE_REVIEW.json'),'finite_resource_QA':ref(HERE/'FINITE_RESOURCE_QA.json'),'independent_arrays_owner_QA':ref(BANK/'INDEPENDENT_QA.json'),'all_actual_files':files,'financial_accounting_or_legal_gold':False,'qualified_skill_or_full_autonomous_demonstration':False,'new_independent_sources_or_tasks':0,'root_main_admission':False,'ACTIVE_modified':False,'training_started':False,'weights_loaded':False,'new_Agent_calls':0}
    path.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps({'status':result['status'],'entry':ref(path),'files':len(files),'counts':{k:{'total':v['total_sequence_tokens'],'A':v['positive_A'],'R':0}for k,v in profiles.items()}}))
if __name__=='__main__':main()
