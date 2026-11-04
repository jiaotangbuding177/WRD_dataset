from pathlib import Path
import hashlib,json
HERE=Path(__file__).resolve().parent
source=HERE/'finalize_artifacts.py'
code=source.read_text(encoding='utf-8').replace("OUT=BASE/'c_review_dataset_01';COM=BASE/'compiled/c_review_dataset_01'", "OUT=BASE/'c_review_dataset_01/semantic_revision_02';COM=BASE/'compiled/c_review_dataset_02'")
code=code.replace("art=OUT/'preserved_original_artifacts'", "rzero(9,by_seq[9]['message']['reasoning_content'][2499:2635],'QUALIFIER_PRESERVATION_OVERGENERALIZED_WITHDRAWN_207_CHARS_PART1')\nrzero(9,by_seq[9]['message']['reasoning_content'][5818:5889],'QUALIFIER_PRESERVATION_OVERGENERALIZED_WITHDRAWN_207_CHARS_PART2')\nart=OUT/'preserved_original_artifacts'")
exec(compile(code,str(source)+'::semantic_revision_02','exec'))
assert OUT==HERE/'semantic_revision_02'
def rows_in(p):
    import gzip
    return {r['id']:r for f in p.glob('*.jsonl.gz') if f.name!='held.jsonl.gz' for r in map(json.loads,gzip.open(f,'rt',encoding='utf-8'))}
old=rows_in(BASE/'compiled/c_review_dataset_01');new=rows_in(COM)
actual_R=[r for r in new.values() if r['bank']=='native_C_review_partial_02'][0]
old_R=old[actual_R['id']]
assert old_R['input_ids']==actual_R['input_ids']
assert old_R['supervised_tokens']==425 and actual_R['supervised_tokens']==387
assert all(new[i]['input_ids']==r['input_ids'] for i,r in old.items() if r['bank']=='native_C_execution_local_01')
save(OUT/'REVISION_SUPERSESSION.json',{
    'schema':'v10-C-semantic-correction-exclusive-owner-policy-v1','root_main_admission':False,
    'recommended_current_compilation':pin(COM/'COMPILATION_REPORT.json'),
    'superseded_preliminary_compilation':pin(BASE/'compiled/c_review_dataset_01/COMPILATION_REPORT.json'),
    'do_not_stack_preliminary_and_current':True,
    'withdrawn_original_R_characters':207,'withdrawn_original_R_tokens':38,
    'original_R_input_ids_unchanged':True,'two_execution_write_input_ids_unchanged':True,
    'new_authored_state_is_explicitly_updated':True,
    'new_state_changes':'Retain all four original Q label objects including deduction notes; disclose specific qualifier overstatements missed by original AI Q; scores unchanged.',
    'review_source':str(HERE/'review_followup_01/REVIEW.md'),
    'older_arrays_are_audit_only_zero_training_exposure':True,
    'transformed_finalizer_source_sha256':hashlib.sha256(code.encode()).hexdigest(),
    'parent_finalizer_sha256':digest(source),'revision_finalizer_sha256':digest(Path(__file__))})
