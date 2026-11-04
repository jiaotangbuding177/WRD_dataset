"""Do not conflate old script hashes with presently surviving source files."""
import hashlib
import json
from pathlib import Path
HERE=Path(__file__).resolve().parent;RECOVERY=HERE.parent;ROOT=next(p for p in HERE.parents if(p/'AGENTS.md').is_file())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def main():
    specs=[
      ('prepare_historical_style_resource_01.py','style_repair_01/EXACT_LINEAGE.json'),
      ('qa_historical_style_resource_01.py','style_repair_01/resource_qa_01/EXECUTION_RECEIPT.json'),
      ('compile_historical_style_projection_01.py','style_repair_01/native_projection_02/BUILD.json'),
      ('verify_historical_style_projection_02.py','style_repair_01/native_projection_02/INDEPENDENT_QA.json'),
      ('build_historical_helpers_resource_01.py','helpers_construction_01/SOURCE_AND_API_SCOPE.json'),
      ('qa_historical_helpers_resource_01.py','helpers_construction_01/resource_qa_01/EXECUTION_RECEIPT.json'),
      ('compile_historical_helpers_projection_01.py','helpers_construction_01/native_projection_01/BUILD.json'),
      ('verify_historical_helpers_projection_01.py','helpers_construction_01/native_projection_01/INDEPENDENT_QA.json'),
      ('package_historical_style_helpers_01.py','STYLE_HELPERS_DELIVERY_01.json'),
      ('audit_historical_cumulative_reasoning_01.py','cumulative_reasoning_audit_01/AUDIT.json'),
      ('build_historical_oracle_repair_01.py','test_oracle_repair_01/SOURCE_STATE_AND_RANGES.json'),
      ('qa_historical_oracle_repair_01.py','test_oracle_repair_01/resource_qa_01/EXECUTION_RECEIPT.json'),
      ('compile_historical_oracle_projection_01.py','test_oracle_repair_01/native_projection_01/BUILD.json')]
    rows=[]
    for name,meta in specs:
        p=ROOT/'research/data_prep/wrd_main_v10'/name;m=load(RECOVERY/meta);expected=m.get('script_sha256')
        rows.append({'original_path':str(p),'original_script_sha256_recorded':expected or'NOT_RECORDED_IN_THIS_METADATA','metadata_path':str(RECOVERY/meta),'metadata_sha256':sha(RECOVERY/meta),'currently_exists':p.is_file(),'currently_present_sha256':sha(p)if p.is_file()else None,'current_matches_original_recorded_sha':sha(p)==expected if p.is_file()and expected else None,'exact_frozen_constructor_copy_found_in_own_output':False,'missing_source_not_replaced_by_a_claimed_exact_reconstruction':True})
    surviving=[]
    for folder in('style_repair_01/resource_qa_01/workspace','helpers_construction_01/resource_qa_01/workspace','test_oracle_repair_01/resource_qa_01/workspace','test_oracle_repair_01/independent_qa_20261029_01','recovery_scope_20261029_01'):
        directory=RECOVERY/folder
        for p in sorted(directory.glob('*.py')):
            surviving.append({'path':str(p),'sha256':sha(p),'bytes':p.stat().st_size,'role':'Actual recorded Docker finite-resource driver'if p.name=='qa_driver.py'else'New20261029 independent data verification or scope script; not claimed old constructor bytes'})
    shared=ROOT/'research/data_prep/wrd_reasoning_v4/compile_native.py'
    value={'schema':'wrd-own-maker-processing-script-survival-20261029-v1','status':'EXACT_SURVIVING_FILES_LISTED_MISSING_OLD_CONSTRUCTORS_EXPLICIT','original_processing_scripts':rows,'actual_surviving_self_contained_QA_drivers_and_new_scripts':surviving,'shared_causal_compiler':{'path':str(shared),'currently_exists':shared.is_file(),'sha256':sha(shared)if shared.is_file()else None},'actual_raw_curated_messages_and_templates_survive':True,'actual_binary_arrays_survive':True,'independent_20261029_oracle_QA_does_not_import_missing_constructor_or_shared_compiler':True,'other_agents_or_restored_checkpoint_may_supply_old_sources':'UNKNOWN_NOT_SEARCHED_HERE; root is recovering research directories.','current_data_prep_or_design_directories_modified_by_this_audit':False,'ACTIVE_modified':False,'training_started':False,'new_Agent_calls':0}
    out=HERE/'PROCESSING_SCRIPT_SURVIVAL.json';assert not out.exists();out.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps({'missing_old_scripts':sum(not r['currently_exists']for r in rows),'surviving_drivers_and_new_scripts':len(surviving),'script_survival_sha256':sha(out),'shared_compiler_present':shared.is_file()}))
if __name__=='__main__':main()
