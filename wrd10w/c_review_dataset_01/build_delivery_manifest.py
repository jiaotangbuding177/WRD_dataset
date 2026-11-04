from pathlib import Path
import gzip,hashlib,json
HERE=Path(__file__).resolve().parent
BASE=HERE.parent
CUR=HERE/'semantic_revision_02'
COM=BASE/'compiled/c_review_dataset_02'
def pin(p):return {'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size}
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def save(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
rows=[json.loads(x) for f in COM.glob('*.jsonl.gz') if f.name!='held.jsonl.gz' for x in gzip.open(f,'rt',encoding='utf-8')]
assert len(rows)==4 and sum(r['supervised_tokens'] for r in rows)==1458
required={'schema':'v10-C-root-independent-admission-request-v1','root_main_admission':False,
    'current_version':'semantic_revision_02','reviewable_report':pin(HERE/'REPORT.md'),
    'compiled_report':pin(COM/'COMPILATION_REPORT.json'),'independent_dual_tokenizer_qa':pin(CUR/'INDEPENDENT_DUAL_TOKENIZER_QA.json'),
    'local_independent_semantic_review':pin(HERE/'review_followup_01/REVIEW.md'),
    'candidate_records':[{'id':r['id'],'bank':r['bank'],'tokens':r['total_tokens'],'supervised_tokens':r['supervised_tokens'],
        'components':r['supervised_tokens_by_component'],'root_main_admission':False} for r in rows],
    'current_input_files':[pin(CUR/x) for x in ['original_R.core7.candidates.jsonl.gz','execution_local.core7.candidates.jsonl.gz','new_real_state_cost_stop.candidate.jsonl.gz']],
    'do_not_admit':['superseded v1 draft','held >32K original histories','original invalid write with missing path','full53 long candidates before separate review/compilation','entire original Q/decision/feedback/R by outcome alone'],
    'independent_root_scope':'Read exact original approved spans and evidence, new authored state/output, actual two writes and the independent report; approve only current local owners if satisfied. Keep original vs newly authored R distinct.',
    'the_root_review_has_not_been_claimed_completed':True,'original226_newH_static_dev_test_isolated':True,
    'no_training_or_model_or_native_execution':True}
save(HERE/'ROOT_REVIEW_REQUIRED.json',required)
essential=[HERE/'REPORT.md',HERE/'ROOT_REVIEW_REQUIRED.json',HERE/'inspect_review.py',HERE/'build_dataset.py',HERE/'build_semantic_revision_02.py',
    HERE/'finalize_artifacts.py',HERE/'finalize_semantic_revision_02.py',Path(__file__),
    HERE/'independent_process_review/REVIEW.md',HERE/'independent_process_review/PROCESS_CANDIDATES.json',
    HERE/'review_followup_01/REVIEW.md',HERE/'review_followup_01/MECHANICAL_AUDIT.json']
essential.extend(p for p in CUR.rglob('*') if p.is_file())
essential.extend(p for p in COM.rglob('*') if p.is_file())
essential.extend(p for p in (HERE/'independent_process_review').rglob('*') if p.is_file())
essential.extend(p for p in (HERE/'review_followup_01').rglob('*') if p.is_file())
if (HERE/'review_followup_01/V2_FINAL_AUDIT.json').exists():essential.append(HERE/'review_followup_01/V2_FINAL_AUDIT.json')
manifest={'schema':'v10-C-local-delivery-manifest-v2','root_main_admission':False,'local_semantic_and_mechanical_review_complete':True,
    'current_candidate_only':True,'sequences':4,'input_tokens':76289,'supervised_tokens':1458,
    'components':{'original_native_R':387,'new_AI_summary_R':132,'actual_tool_A':781,'new_assistant_D':158},
    'weighted_token_equivalents':364.5,'source_group_count':1,'ancestry_sources':4,'AI_silver_not_human_gold':True,
    'files':[pin(p) for p in sorted(set(essential))],'exclude_runtime_private_and_credentials':True,
    'superseded_v1_preserved_at':str(HERE),'superseded_compilation':str(BASE/'compiled/c_review_dataset_01'),
    'no_shared_or_active_or_native_changes':True,'no_training_started':True}
save(HERE/'DELIVERY_MANIFEST.json',manifest)
print(json.dumps({'files':len(manifest['files']),'manifest_sha256':hashlib.sha256((HERE/'DELIVERY_MANIFEST.json').read_bytes()).hexdigest()},ensure_ascii=False))
