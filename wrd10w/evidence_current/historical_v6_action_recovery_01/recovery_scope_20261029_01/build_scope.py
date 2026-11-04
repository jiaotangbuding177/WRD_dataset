"""A complete 113-owner ledger, not an automatic semantic admission list."""
import ast
from collections import Counter
import csv
import gzip
import hashlib
import json
from pathlib import Path
HERE=Path(__file__).resolve().parent;RECOVERY=HERE.parent;BASE=RECOVERY.parent;ROOT=next(p for p in HERE.parents if(p/'AGENTS.md').is_file())
def sha(b):return hashlib.sha256(b).hexdigest()
def digest(p):return sha(Path(p).read_bytes())
def load(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def save(p,v):assert not p.exists();p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def original(p,compressed_sha,restored_sha):
    p=ROOT/p;raw=p.read_bytes();assert sha(raw)==compressed_sha;data=gzip.decompress(raw);assert sha(data)==restored_sha;return json.loads(data),len(data)
def name(n):
    if isinstance(n,ast.Name):return n.id
    if isinstance(n,ast.Attribute):return name(n.value)+'.'+n.attr
    return type(n).__name__
def main():
    assert not(HERE/'SCOPE.json').exists();census=load(RECOVERY/'RAW_CREATOR_CENSUS_02.json');assert len(census['rows'])==113
    base_active={
      '0753780cad3b696a12766199':'ADMITTED_SCOPED_REPORT_EVIDENCE_REPAIR',
      '0ef558c25137e296148ca0cc':'ADMITTED_SCOPED_RUNNER_CORRECTION',
      '82b9c29cc2544f668555c7d2':'ADMITTED_SCOPED_LOCAL_EVIDENCE_VERIFY'}
    pending={
      'cf6b8ff4f33e92f07a4a1474':('HELPERS_NATIVE_ARRAYS_ROOT_PENDING','7 verbatim functions plus dependency-complete module are ready; original full main still has unhandled same-output/report path and incomplete full-schema validation, and original style comparator is wrong.'),
      'fd11a2fdcff6dc66ca1b8502':('STYLE_NATIVE_ARRAYS_ROOT_PENDING','Two copy-style edits are finitely verified. Original overstrong StyleProxy mechanism comment is not gold; newest functional input requires independent semantic approval.'),
      '745cfaf25e274c9f1268bce6':('ORACLE_NATIVE_ARRAYS_ROOT_PENDING','Two original test-oracle literal edits verified; original raw action/API not relabelled native. Explicit new-state native edit ready for semantic peer/root.'),
      '4ecfa75943c1855d9ea5c82c':('CUMULATIVE_R_PARTIAL_EXCERPT_NEW_STATE_ROOT_PENDING','49942char field is collector-accumulated across the tool chain, not final-step faithful CoT. Only one event-grounded contiguous1596 excerpt has1539 positive chars in explicit new state; all other48403 original chars remain audit mask0.'),
      'a8d04db0b8823d9faa129e71':('CUMULATIVE_R_HOLD_STEP_ALIGNMENT','407char final field also belongs to cumulative bridge. Do not auto-label as newly generated final-call R; no new training sequence.'),
      '487d2244138acee4cbc891e1':('FULL_TEST_CREATOR_RECOVERED_TWO_BAD_ORACLES','Original11337char test script recovered exactly and has two wrong expected values. Repaired11417char version is finitely verified31/31. A complete newly authored construction view needs independent full test-design review, current creator action remains0.'),
      'f11ccd753dedeec8bcaef753':('README_WORKFLOW_CREATOR_RECOVERABLE_UNREVIEWED','Original README/workflow creation present but old resource-version quality link was incomplete. Need static extraction, exact versions and check overbroad full-format/schema/completion claims; do not reject because the program had one style bug.')}
    rows=[];counts=Counter();toolcounts=Counter();callcounts=Counter();allbytes=Counter();future=[]
    for r in census['rows']:
        q,qbytes=original(r['original_request']['path'],r['original_request']['sha256'],r['original_request_restored_sha256'])
        response,rbytes=original(r['original_response']['path'],r['original_response']['sha256'],r['original_response_restored_sha256']);m=response['choices'][0]['message'];owner=r['canonical_original_response_owner'];features=[]
        for call in m.get('tool_calls',[]):
            fn=call['function'];toolcounts[fn['name']]+=1;args=json.loads(fn['arguments']);code=args.get('code');f={'tool_call_id':call['id'],'historical_function':fn['name'],'argument_characters':len(fn['arguments']),'code_characters':len(code)if isinstance(code,str)else 0,'code_AST_parses':None,'static_write_hints':[],'copy_call_count':0,'replace_call_count':0,'subprocess_call_count':0,'top_level_function_names':[],'literal_programs':[]}
            if isinstance(code,str):
                try:tree=ast.parse(code);f['code_AST_parses']=True
                except SyntaxError as e:f['code_AST_parses']=False;f['syntax_error']={'line':e.lineno,'offset':e.offset,'message':e.msg};tree=None
                if tree:
                    f['top_level_function_names']=[n.name for n in tree.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))]
                    for n in ast.walk(tree):
                        if isinstance(n,ast.Call):
                            called=name(n.func);callcounts[called]+=1
                            if called.endswith(('.write_text','.write_bytes','.dump','.dump_json'))or called=='open'and any(isinstance(x,ast.Constant)and isinstance(x.value,str)and ('w'in x.value or'a'in x.value)for x in n.args[1:2]):
                                f['static_write_hints'].append({'function':called,'path_expression':ast.unparse(n.args[0])[:180]if n.args else'IMPLICIT_RECEIVER','line':n.lineno})
                            f['copy_call_count']+=called in('shutil.copy','shutil.copyfile','shutil.copytree')
                            f['replace_call_count']+=called.endswith('.replace')
                            f['subprocess_call_count']+=called.startswith('subprocess.')
                        if isinstance(n,ast.Assign)and isinstance(n.value,ast.Constant)and isinstance(n.value.value,str)and len(n.value.value)>=1000:
                            s=n.value.value
                            try:t=ast.parse(s)
                            except SyntaxError:continue
                            if any(isinstance(z,(ast.FunctionDef,ast.Import,ast.ImportFrom))for z in t.body):f['literal_programs'].append({'assigned_names':[ast.unparse(t)for t in n.targets],'characters':len(s),'utf8_sha256':sha(s.encode())})
            features.append(f)
        oldhold=r.get('old_known_quality_hold');oldreasons=oldhold.get('reasons',[])if oldhold else[]
        if owner in base_active:status=base_active[owner];why='Already represented by a different exact new-native adaptation, root admitted; do not add original/raw or another projection of same owner as an independent positive.'
        elif owner in pending:status,why=pending[owner]
        elif any(f.get('code_AST_parses')is False for f in features):status='HOLD_ORIGINAL_ACTION_SYNTAX_ERROR';why='Actual original Python syntax is invalid. Preserve failed action/context and feedback; do not assign positive action loss.'
        elif 'recorded_current_execute_call_failed_not_correct_process_action'in oldreasons:status='HOLD_RECORDED_EXECUTION_FAILURE';why='Original actual outer execution failed; preserve exact error and preceding condition. Some diagnosis may teach a bounded future repair, but failure does not make the entire current action correct.'
        elif 'current_action_outcome_not_linked_to_original_tool_result'in oldreasons:status='HOLD_MISSING_SAME_ACTION_RESULT';why='No original same-action delivered tool receipt was linked before trace termination. Later files or another run cannot silently substitute for the missing action result.'
        elif all(f['historical_function']=='read_file'for f in features)and features:status='READ_OBSERVATION_AVAILABLE_SEMANTIC_REVIEW_PENDING';why='Exact read/observation history exists; no new positive semantic credit. Prioritise substantive code construction/revision first.'
        else:status='ACTION_BYTES_RECOVERED_SEMANTIC_RESOURCE_REVIEW_PENDING';why='Exact request/response, code and subsequent observation are preserved. Need actual-version resource semantics, failure interpretation, code/feedback linkage and owner-exclusive native adaptation before positive loss; old ABI alone is not a rejection reason.'
        row={'canonical_original_response_owner':owner,'source_id':'conv_b5e6f3d3bab9','source_status':'TRAIN','run_id':r['run_id'],'request_ordinal':r['request_ordinal'],'original_request':r['original_request'],'request_restored_bytes':qbytes,'original_response':r['original_response'],'response_restored_bytes':rbytes,'original_reasoning_characters':r['original_reasoning_characters'],'ordinary_visible_content_characters':r['ordinary_visible_content_characters'],'old_original116':r['old_original116'],'old_admitted106':r['old_admitted106'],'old_hold_reasons':oldreasons,'old_candidate_write_paths':[x.get('path')for x in oldhold.get('candidate_resource_writes',[])]if oldhold else[],'next_request_prefix_exact':r.get('next_original_request_exact_prefix'),'current_response_delivered_in_next_request':r.get('current_response_delivered_in_next_request'),'static_features_not_semantic_review':features,'current_recovery_status':status,'specific_remaining_boundary':why,'new_main_admission_from_this_table':False,'current_native_loop_equivalence':False}
        rows.append(row);counts[status]+=1;allbytes['restored_requests']+=qbytes;allbytes['restored_responses']+=rbytes;allbytes['code_characters']+=sum(f['code_characters']for f in features);allbytes['original_R_characters']+=r['original_reasoning_characters']
        if status=='ACTION_BYTES_RECOVERED_SEMANTIC_RESOURCE_REVIEW_PENDING'and any(f['static_write_hints']or f['copy_call_count']or f['replace_call_count']for f in features):future.append({'owner':owner,'run_id':r['run_id'],'ordinal':r['request_ordinal'],'code_characters':sum(f['code_characters']for f in features),'write_or_copy_or_replace_hints':sum(len(f['static_write_hints'])+f['copy_call_count']+f['replace_call_count']for f in features),'not_yet_semantically_admissible':True})
    with gzip.open(HERE/'OWNER_SCOPE_113.jsonl.gz','wt',encoding='utf-8',newline='\n')as f:
        for row in rows:f.write(json.dumps(row,ensure_ascii=False,separators=(',',':'))+'\n')
    with(HERE/'OWNER_SCOPE_113.csv').open('w',encoding='utf-8-sig',newline='')as f:
        fields=['canonical_original_response_owner','run_id','request_ordinal','old_original116','old_admitted106','original_reasoning_characters','current_recovery_status','specific_remaining_boundary'];w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows({k:r[k]for k in fields}for r in rows)
    scope={'schema':'wrd-113-original-owner-recovery-scope-20261029-v1','status':'COMPLETE_OWNER_AND_RESOURCE_SCOPE_LEDGER_NOT_NEW_TRAINING_ADMISSION','original_responses':113,'original_runs':5,'independent_original_sources':1,'all_current_source_TRAIN':True,'all113_request_response_compressed_and_restored_SHA_reverified':True,'count_by_status':dict(counts),'actual_tool_calls':dict(toolcounts),'corpus_sizes':dict(allbytes),'existing_root_admitted_native_owners':3,'ready_additional_scoped_native_action_candidates':3,'new_candidates_additive_training_targets_if_root_approves':3,'candidate_original_R_exposure_is_one_contiguous_excerpt_not_49942whole':True,'remaining_usable_training_tokens':'UNKNOWN_PENDING_SEMANTIC_VERSION_REVIEW_NOT_INFERRED_FROM_RAW_BYTES','remaining_action_resource_priority':sorted(future,key=lambda x:-x['code_characters']),'known_next_substantive_construction':{'original_creator_owner':'487d2244138acee4cbc891e1','resource':'Complete repaired11417char boundary test script, exact original two oracle edits applied. Current fixed-image31checks pass with candidate unchanged; a new creation-state target still needs independent full test-design semantics and owner admission.','root_admitted':False},'protected_sources_or_private_sessions_read_for_new_labels':0,'new_main_from_this_ledger':0,'whole_pipeline_demonstrations':0,'new_Agent_calls':0,'training_started':False,'ACTIVE_modified':False,'script_sha256':digest(Path(__file__))}
    save(HERE/'SCOPE.json',scope);print(json.dumps({'counts':dict(counts),'size':dict(allbytes),'future_resource_action_candidates':len(future),'scope_sha256':digest(HERE/'SCOPE.json')}))
if __name__=='__main__':main()
