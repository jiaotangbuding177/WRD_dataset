"""Target-level historical raw quality overlay from actual recorded outcomes.

Do not use final validation success to bless earlier resource versions. Reads,
tests and diagnosis remain useful when the tested resource fails. Known failed
calls and unverified candidate resource writers are not correctness positives.
No model code or validator is executed by this audit.
"""
from __future__ import annotations
import ast
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[3]
BASE=ROOT/'output/20261025_wrd_reasoning_recovery_v4'
OUT=ROOT/'output/20261026_wrd_sequences_v6'
def js(x):return json.dumps(x,ensure_ascii=False,separators=(',',':'))
def bsha(x):return hashlib.sha256(x).hexdigest()
def digest(p):return bsha(p.read_bytes())
def rows(p):
    with gzip.open(p,'rt',encoding='utf-8-sig') as f:
        for line in f:
            if line.strip():yield json.loads(line)
def save(p,r):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def dump(p,rs):
    p.parent.mkdir(parents=True,exist_ok=True)
    with gzip.open(p,'wt',encoding='utf-8',newline='\n') as f:
        for r in rs:f.write(js(r)+'\n')

UNKNOWN=object()
def static_value(n,env):
    if isinstance(n,ast.Constant):return n.value
    if isinstance(n,ast.Name):return env.get(n.id,UNKNOWN)
    if isinstance(n,ast.BinOp):
        a,b=static_value(n.left,env),static_value(n.right,env)
        if isinstance(a,str) and isinstance(b,str):
            if isinstance(n.op,ast.Div):return a.rstrip('/')+'/'+b.lstrip('/')
            if isinstance(n.op,ast.Add):return a+b
        return UNKNOWN
    if isinstance(n,ast.Call):
        args=[static_value(a,env) for a in n.args]
        if isinstance(n.func,ast.Name) and n.func.id in {'Path','str'} and len(args)==1 and isinstance(args[0],str):return args[0]
        if isinstance(n.func,ast.Attribute) and n.func.attr=='join' and isinstance(n.func.value,ast.Attribute) and n.func.value.attr=='path' and all(isinstance(a,str) for a in args):return '/'.join(args)
        if isinstance(n.func,ast.Attribute) and n.func.attr=='replace' and len(args) in {2,3}:
            value=static_value(n.func.value,env)
            if isinstance(value,str) and all(a is not UNKNOWN for a in args):return value.replace(*args)
    return UNKNOWN

def production_writes(code):
    """Only literal/static path and string propagation; never eval/exec."""
    try:tree=ast.parse(code);normalization='original_code'
    except SyntaxError:
        try:tree=ast.parse(code.replace('\\n','\n'));normalization='literal_backslash_newline_projection_for_path_review_only'
        except SyntaxError:return [],'unparseable'
    env={};writes=[]
    for statement in tree.body:
        if isinstance(statement,(ast.Assign,ast.AnnAssign)):
            value=static_value(statement.value,env)
            targets=statement.targets if isinstance(statement,ast.Assign) else [statement.target]
            for target in targets:
                if isinstance(target,ast.Name):env[target.id]=value
        for n in ast.walk(statement):
            if not isinstance(n,ast.Call):continue
            path=UNKNOWN;data=UNKNOWN
            if isinstance(n.func,ast.Attribute) and n.func.attr in {'write_text','write_bytes'}:
                path=static_value(n.func.value,env)
                if n.args:data=static_value(n.args[0],env)
            elif isinstance(n.func,ast.Attribute) and n.func.attr=='write' and isinstance(n.func.value,ast.Call):
                op=n.func.value
                if isinstance(op.func,ast.Name) and op.func.id=='open' and op.args:
                    path=static_value(op.args[0],env)
                    if n.args:data=static_value(n.args[0],env)
            elif isinstance(n.func,ast.Name) and n.func.id=='open' and len(n.args)>=2:
                mode=static_value(n.args[1],env)
                if isinstance(mode,str) and any(c in mode for c in 'wax'):
                    path=static_value(n.args[0],env)
            if isinstance(path,str) and path.replace('\\','/').lstrip('./').startswith(('outputs/candidate/','outputs/skill/')):
                hashes=[]
                if isinstance(data,str):
                    hashes=[bsha(data.encode()),bsha(data.replace('\r\n','\n').replace('\n','\r\n').encode())]
                elif isinstance(data,bytes):hashes=[bsha(data)]
                writes.append({'path':path,'static_written_content_sha256_variants':sorted(set(hashes)),
                    'string_bytes_fully_static':bool(hashes),'analysis':normalization})
    # A source path in copy/read/diagnostic code is not a resource write. Open
    # handles count only with an explicit write mode; no broad path co-occurrence.
    return writes,normalization

def main():
    pair_path=OUT/'controlled/reasoning_pair_lineage_inputs.jsonl.gz'
    pairs=list(rows(pair_path));scope_path=BASE/'controlled/raw_scope_review.by_run.jsonl.gz'
    scope_by_path={str(Path(r['run_path'])).lower():r for r in rows(scope_path)}
    independent_path=ROOT/'output/20261026_wrd_lineage_v6/INDEPENDENT_REASONING_REVIEW.json'
    independent=json.loads(independent_path.read_text(encoding='utf-8')) if independent_path.is_file() else {}
    repair=independent.get('complete_causal_repair_example_without_enterprise_body') or {}
    overlay=[];counts=Counter();run_summaries={};run_cache={}
    for item in pairs:
        if item['parent_run_id'] is None:continue
        run=item['parent_run_record'];rid=run['run_id'];pair=item['original_pair'];pid=item['pair_id']
        scope=scope_by_path.get(str(Path(run['run_path'])).lower(),{})
        receipts=scope.get('existing_historical_validation_receipts',[])
        passed_hashes={f['expected_sha256'] for r in receipts if r.get('recorded_passed') is True and r.get('all_recorded_candidate_file_hashes_match') is True
                       for f in r.get('candidate_file_checks',[]) if f.get('sha_matches') is True}
        if rid not in run_cache:
            run_cache[rid]={s['pair_id']:s for s in run['actual_steps']}
            run_summaries[rid]={'run_path':run['run_path'],'scope_review_found_by_path_not_incompatible_run_id':bool(scope),
                'historical_validation':[{'path':r['validation_path'],'sha256':r['validation_sha256'],
                    'passed':r['recorded_passed'],'cases_passed':r.get('recorded_cases_passed'),'cases':r.get('recorded_development_cases'),
                    'validator_source_current_sha_matches':r.get('validator_source_current_sha_matches'),
                    'candidate_file_hashes_match':r.get('all_recorded_candidate_file_hashes_match')} for r in receipts],
                'final_success_not_retroactive_to_other_resource_versions':True}
        step=run_cache[rid][pid];message=pair['original_response']['choices'][0]['message']
        call_ids={c.get('id') for c in message.get('tool_calls',[])}
        actual_results=[]
        for m in step.get('observations_before_next_response',[]):
            if m.get('role')=='tool' and m.get('tool_call_id') in call_ids:
                try:out=json.loads(m['content'])
                except ValueError:continue
                actual_results.append(out)
        reasons=[];evidence=[];writes=[]
        for call in message.get('tool_calls',[]):
            args=call.get('function',{}).get('arguments',{})
            try:args=json.loads(args) if isinstance(args,str) else args
            except ValueError:continue
            code=args.get('code') if isinstance(args,dict) else None
            if isinstance(code,str):
                current,projection=production_writes(code);writes.extend(current)
        for outcome in actual_results:
            if outcome.get('exit_code') not in (None,0):
                stderr=outcome.get('stderr','');frames=re.findall(r'File "([^"]+)"',stderr)
                resource_frames=[f for f in frames if '/outputs/candidate/' in f.replace('\\','/').lower()
                    or '/outputs/skill/' in f.replace('\\','/').lower()]
                exceptions=re.findall(r'\b[A-Za-z_]*(?:Error|Exception)\b',stderr)
                if exceptions and not resource_frames:
                    reasons.append('recorded_current_execute_call_failed_not_correct_process_action')
                    evidence.append({'type':'actual_tool_result','exit_code':outcome.get('exit_code'),
                        'exception_classes':sorted(set(exceptions)),'stderr_sha256':bsha(stderr.encode()),
                        'resource_stack_frames_present':False})
            stdout=outcome.get('stdout','')
            if 'FAIL' in stdout or '"passed": false' in stdout.lower():
                evidence.append({'type':'actual_failed_resource_probe_retained_as_valid_test_action',
                    'stdout_sha256':bsha(stdout.encode()),'exit_code':outcome.get('exit_code')})
        if writes:
            all_verified=all(set(w['static_written_content_sha256_variants'])&passed_hashes for w in writes)
            if pid==repair.get('original_repair_response_pair_id'):
                # A separately audited literal line patch has a stronger exact
                # version proof than this deliberately small static evaluator.
                # Validate the source, observed result, output bytes and actual
                # validation receipt before clearing only this writer target.
                expected=repair['repaired_program_sha256']
                program=Path(run['run_path'])/'workspace/outputs/candidate/scripts/run.py'
                receipt_path=Path(repair['later_validation_path'])
                source_request_hash=bsha(js(pair['original_request']).encode())
                assert source_request_hash==repair['original_request_canonical_sha256']
                assert pair['source_response']['sha256']==repair['original_response_canonical_sha256']
                assert repair['static_literal_line_patch_reconstruction_equals_actual_output'] is True
                assert repair['historical_program_not_executed_by_auditor'] is True
                assert repair['previous_program_source_and_input_copy_sha_equal'] is True
                assert repair['feedback_derived_from_actual_validation04_report_and_quality_proven_above'] is True
                assert program.is_file() and program.stat().st_size==repair['repaired_program_bytes'] and digest(program)==expected
                assert receipt_path.is_file() and digest(receipt_path)==repair['later_validation_sha256']
                assert expected in passed_hashes
                assert any(o.get('exit_code')==0 and expected in o.get('stdout','') for o in actual_results)
                assert step['next_request_has_exact_current_prefix'] is True and step['next_request_contains_current_response_body'] is True
                assert repair['later_validation_same_candidate_program_sha256'] is True
                assert repair['later_validation_passes']==repair['later_validation_cases']==12
                all_verified=True
                evidence.append({'type':'independent_exact_literal_patch_to_actual_observed_output_and_later_same_version_validation',
                    'independent_report_sha256':digest(independent_path),'original_pair_id':pid,
                    'repaired_program_sha256':expected,'repaired_program_bytes':repair['repaired_program_bytes'],
                    'original_actual_tool_exit_code':0,'later_validation_sha256':repair['later_validation_sha256'],
                    'later_validation_passes':12,'later_validation_cases':12,
                    'earlier_failed_writer_versions_not_relabelled_correct':True})
            if not all_verified:
                reasons.append('candidate_resource_writer_draft_not_byte_matched_to_successful_validation')
                evidence.append({'type':'resource_version_quality_not_proven','writes':writes,
                    'same_run_recorded_validation_found':bool(receipts),
                    'same_run_recorded_validation_failed':any(r.get('recorded_passed') is False for r in receipts),
                    'not_a_claim_every_line_or_the_entire_run_is_wrong':True})
            else:
                evidence.append({'type':'exact_static_written_resource_bytes_match_recorded_successful_validation',
                    'writes':writes,'only_this_version_not_earlier_versions_is_covered':True})
        # No output observation is not replaced with a fictional successful one.
        if message.get('tool_calls') and not actual_results:
            reasons.append('current_action_outcome_not_linked_to_original_tool_result')
        decision='HOLD_TARGET_ZERO_LOSS' if reasons else 'PROCESS_ACTION_SILVER_NOT_BUSINESS_QUALITY_GOLD'
        counts[decision]+=1
        for reason in reasons:counts[reason]+=1
        overlay.append({'pair_id':pid,'parent_run_id':rid,'request_ordinal':pair['request_ordinal'],
            'decision':decision,'target_positive_allowed':not reasons,'reasons':sorted(set(reasons)),
            'evidence':evidence,'candidate_resource_writes':writes,
            'source_request_sha256':pair['source_request']['sha256'],
            'source_response_sha256':pair['source_response']['sha256'],
            'raw_source_context_and_failed_versions_preserved':True,'future_outcome_not_inserted_in_original_prompt':True,
            'historical_validator_not_current_independent_Q':True,'human_gold':False})
    dump(OUT/'controlled/historical_raw_quality_overlay.jsonl.gz',overlay)
    report={'schema_version':'wrd-v6-historical-target-quality-overlay','raw_targets_reviewed':len(overlay),'counts':dict(counts),
        'parent_runs':run_summaries,'test_failure_does_not_make_legitimate_test_or_read_action_wrong':True,
        'unknown_candidate_writer_is_draft_not_correct_resource_positive':True,
        'precise_failure_bytes_and_timing_not_final_success_retroactivity':True,
        'full_semantic_resource_code_review_claimed':False,'training_started':False,'new_tool_or_program_executions':0,
        'source_sha256':{str(pair_path.relative_to(ROOT)):digest(pair_path),str(scope_path.relative_to(ROOT)):digest(scope_path)},
        'overlay_sha256':digest(OUT/'controlled/historical_raw_quality_overlay.jsonl.gz'),'script_sha256':digest(Path(__file__))}
    if independent_path.is_file():report['source_sha256'][str(independent_path.relative_to(ROOT))]=digest(independent_path)
    save(OUT/'HISTORICAL_RAW_QUALITY_REPORT.json',report)
    print(js({'raw_targets':len(overlay),'counts':dict(counts)}),flush=True)

if __name__=='__main__':main()
