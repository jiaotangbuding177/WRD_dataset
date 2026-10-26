"""Offline source/resource closure for the historical original-reasoning layer."""
from collections import Counter
import gzip
import hashlib
import importlib.util
import json
import re
from pathlib import Path
import shutil

ROOT = Path('D:/skillloop')
OUT = ROOT / 'output/20261026_wrd_lineage_v6'
INPUT = ROOT / 'output/20261026_wrd_sequences_v6/controlled/reasoning_pair_lineage_inputs.jsonl.gz'
def js(v): return json.dumps(v, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
def h(v): return hashlib.sha256(v).hexdigest()
def hf(p): return h(p.read_bytes())
def rows(p):
    with gzip.open(p, 'rt', encoding='utf-8') as f:
        for line in f: yield json.loads(line)
def strings(v):
    if isinstance(v, str): yield v
    elif isinstance(v, dict):
        for x in v.values(): yield from strings(x)
    elif isinstance(v, list):
        for x in v: yield from strings(x)
def ids(v):
    import re
    return set(re.findall(r'conv_[a-f0-9]{12}', js(v)))
def main():
    OUT.mkdir(exist_ok=True, parents=True); control = OUT / 'controlled'; control.mkdir(exist_ok=True)
    cas = control / 'reasoning_resource_cas'; cas.mkdir(exist_ok=True)
    if (OUT/'REASONING_LINEAGE_REPORT.json').exists():
        old=OUT/'history'/('reasoning_'+hf(OUT/'REASONING_LINEAGE_REPORT.json')[:16]);old.mkdir(parents=True,exist_ok=True)
        shutil.copy2(OUT/'REASONING_LINEAGE_REPORT.json',old/'REASONING_LINEAGE_REPORT.json')
        for name in ['reasoning_pair_lineage_decisions.jsonl.gz','reasoning_resource_nodes.jsonl.gz']:
            shutil.copy2(control/name,old/name)
    independent_path=OUT/'INDEPENDENT_REASONING_REVIEW.json'
    independent_bytes=independent_path.read_bytes() if independent_path.exists() else None
    independent_sha=h(independent_bytes) if independent_bytes else None
    independent=json.loads(independent_bytes) if independent_bytes else {}
    if independent_bytes:
        frozen=OUT/'frozen'/('reasoning_review_'+independent_sha+'.json');frozen.parent.mkdir(exist_ok=True)
        if not frozen.exists():frozen.write_bytes(independent_bytes)
    independent_sse={p['pair_id']:p for p in independent.get('sse_pair_proofs',[])}
    independent_copies={(p['consumer_run_id'],p['destination']):p for p in independent.get('prior_candidate_output_copy_edges',[])
        if p.get('copy_and_source_and_prior_result_output_sha_equal') and p.get('parent_finished_before_consumer_started')}
    independent_feedback={(p['consumer_run_id'],p['destination']):p for p in independent.get('real_feedback_field_projection_proofs',[])
        if p.get('actual_dispatched_copy_sha_verified')}
    independent_reads={(p['run_id'],p['call_id']):p for p in independent.get('raw_read_file_unique_calls',[])
        if p.get('read_only_tool_with_declared_input_copy')}
    independent_dynamic={(p['run_id'],p['call_id']):p for p in independent.get('exact_raw_dynamic_call_closure_proofs',[])
        if p.get('actual_script_universal_newline_text_equals_original_call_code') and
        (p.get('syntax_failure_actual_receipt_verified') or p.get('imports_fixed_and_no_eval_exec_network_api'))}
    contracts = [p for p in (ROOT / 'benchmark').glob('*/contracts/evaluation.jsonl') if p.parent.parent.name in {
        'enterprise_split_v9_20261010','enterprise_input_closed_v11_20261012',
        'enterprise_original_inputs_v10_20261011','enterprise_final_delivery_v8_20261010'}]
    protected = {json.loads(l)['session_id'] for p in contracts for l in p.open(encoding='utf-8-sig') if l.strip()}
    helper = ROOT / 'research/data_prep/wrd_reasoning_v6/lineage_audit.py'
    spec = importlib.util.spec_from_file_location('native_lineage_readonly', helper)
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    artifacts = []; decisions = []; resource_nodes = {}; verified = {}
    def preserve(path, expected, kind, sid=None):
        key = (str(path), expected)
        if key in verified: return verified[key]
        p = Path(path); good = p.is_file() and hf(p) == expected
        node = {'node_id': h((str(p)+'\n'+str(expected)).encode()), 'source_path': str(p),
            'sha256': expected, 'bytes': p.stat().st_size if p.is_file() else None,
            'immutable_bytes_sha256_verified': good, 'kind': kind, 'source_id': sid,
            'historical_real_material_claimed_by_this_audit': False, 'body_exported': False}
        if good:
            dest = cas / expected
            if not dest.exists(): shutil.copy2(p, dest)
            assert hf(dest) == expected
            node['immutable_export_path'] = str(dest.relative_to(ROOT))
        resource_nodes[node['node_id']] = node; verified[key] = node
        return node
    independent_nodes_by_sha={}
    for item in independent.get('preserved_evidence_files',[]):
        p=ROOT/item['immutable_export_path']
        assert p.is_file() and hf(p)==item['sha256']
        node={'node_id':h((item['source_path']+'\n'+item['sha256']).encode()),
            'source_path':item['source_path'],'sha256':item['sha256'],'bytes':item['bytes'],
            'immutable_bytes_sha256_verified':True,'kind':item['kind'],
            'immutable_export_path':item['immutable_export_path'],
            'historical_real_material_claimed_by_this_audit':False,'body_exported':False}
        resource_nodes[node['node_id']]=node;independent_nodes_by_sha[item['sha256']]=node
    for x in rows(INPUT):
        missing = []; refs = []; proof = []; request = x['original_request']; current_ids = ids(request)
        for dep in x['source_file_dependencies']:
            p = ROOT / dep['immutable_export_path']; good = p.is_file() and hf(p) == dep['actual_sha256'] and dep.get('declared_sha256_matches')
            if not good: missing.append({'reason': 'ORIGINAL_REQUEST_RESPONSE_OR_RECEIPT_BYTES_NOT_VERIFIED', 'source_role': dep.get('role')})
        if current_ids & protected:
            missing.append({'reason': 'REQUEST_CONTAINS_PROTECTED_SOURCE_ID_REQUIRES_EXCLUSION', 'source_ids': sorted(current_ids & protected)})
        run = x.get('parent_run_record')
        if not run:
            scope = x['existing_source_identity_review']; sp = scope.get('source_proof') or {}
            if not (sp.get('physical_line_sha_matches') and sp.get('source_identity_matches') and sp.get('in_current_evolution_index')):
                missing.append({'reason': 'ORIGINAL_SOURCE_RECORD_PIN_NOT_VERIFIED'})
            u = json.loads(request['messages'][1]['content']); sid = u['current_source_id']; source = u['complete_source']
            restored = dict(source)
            if 'messages' not in restored:
                restored['messages'] = [m for t in restored['turns'] for m in [t['user'], *t['assistant_messages']]]
            reconstructed = h(js(restored).encode())
            declared_source_hash = u.get('original_complete_source_sha256')
            if declared_source_hash is not None and reconstructed != declared_source_hash:
                missing.append({'reason': 'COMPLETE_SOURCE_POLICY_PROJECTION_HASH_NOT_RECONSTRUCTED'})
            elif declared_source_hash is None:
                missing.append({'reason': 'COMPLETE_SOURCE_POLICY_PROJECTION_ORIGINAL_HASH_ABSENT',
                    'reconstructed_complete_source_sha256': reconstructed})
            else: proof.append({'reason': 'EXACT_SOURCE_FOR_POLICY_DEDUP_PROJECTION_INVERTED',
                'complete_source_sha256': reconstructed, 'projection': 'remove duplicated messages equal expanded turns',
                'controller_source_path': 'research/pipelines/skillsloop_ewi_v2/pipeline.py',
                'controller_source_sha256': hf(ROOT/'research/pipelines/skillsloop_ewi_v2/pipeline.py')})
            outcome = x['original_action_outcome_evidence']; tp = Path(outcome['source_transcript_path'])
            transcript = json.loads(tp.read_text(encoding='utf-8-sig'))
            if hf(tp) != outcome['source_transcript_sha256']: missing.append({'reason': 'TRANSCRIPT_SHA_MISMATCH'})
            before = [z for z in transcript if z['decision'] < u['decision_number']]
            expected = json.loads(json.dumps(before[-4:]))
            for z in expected:
                ob = z.get('event', {}).pop('observation', None)
                if ob is not None: z['event']['observation_ref'] = {k: ob.get(k) for k in ('execution_id','tool_return_ref','tool_return_sha256')}
            if u['recent_interactions'] != expected:
                missing.append({'reason': 'RECENT_INTERACTIONS_NOT_EXACT_PRIOR_TRANSCRIPT_PUBLIC_PROJECTION'})
            else: proof.append({'reason': 'EXACT_PRIOR_TRANSCRIPT_LAST4_WITH_OBSERVATION_SHA_REFERENCES',
                'source_transcript_sha256': outcome['source_transcript_sha256'],
                'prior_decision_numbers': [z['decision'] for z in before[-4:]]})
            state = u['state']
            for a in state.get('input_assets', []) + state.get('assets', []):
                sid2 = a.get('source_id', sid); digest = a.get('sha256_actual', a.get('sha256'))
                n = preserve(a['path'], digest, a.get('origin_type','source_material'), sid2); refs.append(n['node_id'])
                if not n['immutable_bytes_sha256_verified']: missing.append({'reason': 'ASSET_BYTES_NOT_VERIFIED', 'resource_node_id': n['node_id']})
                if sid2 != sid: missing.append({'reason': 'CROSS_SOURCE_ASSET_NEEDS_ADDITIONAL_ANCESTRY', 'source_id': sid2})
                if a.get('origin_type') == 'current_executed':
                    # Original asset ledger describes a product from this same
                    # source episode; require an earlier actual tool product SHA.
                    earlier = [z for z in before if digest in js(z.get('event', {}))]
                    if not earlier: missing.append({'reason': 'GENERATED_ASSET_NO_PRIOR_TRANSCRIPT_PRODUCT_SHA', 'resource_node_id': n['node_id']})
            for ob in state.get('recent_observations', []):
                n = preserve(ob['tool_return_ref'], ob['tool_return_sha256'], 'actual_prior_tool_observation', ob.get('source_id'))
                refs.append(n['node_id'])
                if not n['immutable_bytes_sha256_verified']: missing.append({'reason': 'PRIOR_OBSERVATION_BYTES_NOT_VERIFIED', 'resource_node_id': n['node_id']})
                if ob.get('source_id') != sid: missing.append({'reason': 'CROSS_SOURCE_TOOL_OBSERVATION', 'source_id': ob.get('source_id')})
                if not any(ob == z.get('event', {}).get('observation') for z in before):
                    missing.append({'reason': 'STATE_OBSERVATION_NOT_FOUND_IN_PRIOR_TRANSCRIPT', 'resource_node_id': n['node_id']})
            if state.get('related_source_ids'):
                missing.append({'reason': 'RELATED_SOURCE_HISTORY_NOT_IN_SINGLE_SOURCE_PACKET', 'source_ids': state['related_source_ids']})
            # A source-local workflow/state is an original deterministic controller
            # view of prior proposals, not a newly generated training explanation.
            if ids(state) - {sid}: missing.append({'reason': 'STATE_CONTAINS_OTHER_SOURCE_RECORDS', 'source_ids': sorted(ids(state)-{sid})})
            branch = 'historical_sse_original_reasoning'
        else:
            branch = 'historical_raw_generation_repair'; packet = run['observed_input_packet']; fm = run['observed_final_messages']
            if isinstance(fm, dict): fm = fm['messages']
            if request['messages'] != fm[:len(request['messages'])]: missing.append({'reason': 'REQUEST_NOT_EXACT_ORIGINAL_RUN_PREFIX'})
            else: proof.append({'reason': 'REQUEST_IS_EXACT_ORIGINAL_RUN_FINAL_MESSAGES_PREFIX',
                'request_message_count': len(request['messages']), 'parent_run_id': run['run_id']})
            copies = packet.get('copies', []); originals = set()
            for copy in copies:
                pin = copy['copy']; n = preserve(pin['path'], pin['sha256'], 'original_dispatched_raw_run_input');refs.append(n['node_id'])
                if not n['immutable_bytes_sha256_verified']: missing.append({'reason':'RAW_DISPATCHED_INPUT_BYTES_NOT_VERIFIED','resource_node_id':n['node_id']})
                if copy['source'].get('sha256') != pin['sha256']: missing.append({'reason':'SOURCE_TO_DISPATCH_COPY_IDENTITY_MISMATCH'})
                if copy['destination'] == 'inputs/conversation.json' and n['immutable_bytes_sha256_verified']:
                    value=json.loads(Path(pin['path']).read_text(encoding='utf-8-sig')); originals.update(ids(value))
                if any(k in copy['destination'] for k in ('feedback','previous_candidate','previous_learning')):
                    missing.append({'reason':'RAW_REPAIR_FEEDBACK_OR_PREVIOUS_VERSION_PRODUCER_NOT_YET_PROVEN',
                        'destination':copy['destination'],'resource_node_id':n['node_id']})
            if not originals or originals & protected: missing.append({'reason':'RAW_ORIGINAL_SOURCE_ROOT_NOT_ALLOWED','source_ids':sorted(originals)})
            for mi,m in enumerate(request['messages']):
                for call in m.get('tool_calls', []):
                    f=call.get('function') or {}; args=json.loads(f.get('arguments','{}'))
                    if f.get('name') != 'execute_python':
                        if (run['run_id'],call.get('id')) in independent_reads:
                            proof.append({'reason':'EXACT_READ_FILE_OF_ORIGINAL_DISPATCHED_COPY',
                                'native_message_index':mi,'call_id':call.get('id'),
                                'independent_proof':independent_reads[(run['run_id'],call.get('id'))]})
                        elif f.get('name')=='finish':
                            proof.append({'reason':'DECLARED_FINISH_IS_OUTPUT_ONLY_NOT_NEW_EXTERNAL_BUSINESS_INPUT',
                                'native_message_index':mi,'call_id':call.get('id'),
                                'original_tool_schema_sha256':h(js(request.get('tools')).encode())})
                        else:missing.append({'reason':'UNSUPPORTED_HISTORICAL_TOOL_RESOURCE_ACCESS','native_message_index':mi,
                            'call_id':call.get('id'),'tool_name':f.get('name')})
                        continue
                    paths,dynamic,writes=mod.python_read_paths(args.get('code',''))
                    for p in paths:
                        if p.startswith(('/', '\\')) or '..' in Path(p).parts or (len(p)>1 and p[1]==':'):
                            missing.append({'reason':'RAW_READ_OUTSIDE_PROVEN_DISPATCH_WORKSPACE','native_message_index':mi,'path':p})
                    if dynamic:
                        narrow=independent_dynamic.get((run['run_id'],call.get('id')))
                        if narrow and h(args.get('code','').encode())==narrow['code_sha256']:
                            proof.append({'reason':'EXACT_ORIGINAL_CALL_FINITE_DATAFLOW_AND_RECORDED_FILE_OPEN_CLOSURE',
                                'native_message_index':mi,'call_id':call.get('id'),
                                'independent_report_sha256':independent_sha,'narrow_exact_call_proof':narrow})
                            digests=set(re.findall(r'\b[a-f0-9]{64}\b',js(narrow)))
                            refs.extend(independent_nodes_by_sha[d]['node_id'] for d in digests if d in independent_nodes_by_sha)
                        else:missing.append({'reason':'RAW_DYNAMIC_READ_TARGET_NEEDS_RESOLUTION','native_message_index':mi,
                            'call_id':call.get('id'),'syntax_evidence':dynamic})
                    if any(k in args.get('code','') for k in ('urlopen(', 'requests.get(', 'requests.post(', 'socket.')):
                        missing.append({'reason':'RAW_EXTERNAL_NETWORK_RESOURCE_ANCESTRY_NOT_PROVEN','native_message_index':mi})
        independently_resolved=[]
        if x['pair_id'] in independent_sse:
            reviewed=independent_sse[x['pair_id']]
            if reviewed.get('lineage_missing_reasons_resolved'):
                resolved=set(reviewed['resolved_reason_codes'])
                independently_resolved=[b for b in missing if b['reason'] in resolved]
                missing=[b for b in missing if b['reason'] not in resolved]
                proof.append({'reason':'INDEPENDENT_EXACT_ORIGINAL_SOURCE_AND_CONTROLLER_PROJECTIONS',
                    'report_path':str(independent_path.relative_to(ROOT)),
                    'report_sha256':independent_sha,'pair_id':x['pair_id'],
                    'resolved_reason_codes':sorted(resolved),
                    'proof_source_complete_canonical_sha256':reviewed['source_complete_canonical_sha256']})
        if run:
            remaining=[]
            for block in missing:
                key=(run['run_id'],block.get('destination'))
                if block['reason']=='RAW_REPAIR_FEEDBACK_OR_PREVIOUS_VERSION_PRODUCER_NOT_YET_PROVEN' and (
                    key in independent_copies or key in independent_feedback):
                    independently_resolved.append(block)
                    edge=independent_copies.get(key) or independent_feedback[key]
                    proof.append({'reason':'EXACT_ORIGINAL_PREVIOUS_CANDIDATE_OR_REAL_FEEDBACK_PROJECTION',
                        'independent_report_sha256':independent_sha,'edge':edge})
                else:remaining.append(block)
            missing=remaining
        status = 'HOLD_PROTECTED' if current_ids & protected else 'HOLD_MISSING_EVIDENCE' if missing else 'ADMIT'
        decisions.append({'pair_id':x['pair_id'],'parent_run_id':x.get('parent_run_id'), 'branch':branch,
            'status':status,'resource_closure_proven':status=='ADMIT','protected_ancestor_present':status=='HOLD_PROTECTED',
            'original_request_canonical_sha256':x['original_request_canonical_sha256'],
            'source_record_sha256':x['source_record_sha256'], 'resource_node_ids':sorted(set(refs)),
            'observed_evolution_source_ids':sorted(current_ids-protected) if not run else sorted(originals-protected),
            'blocking_evidence':missing, 'positive_evidence':proof, 'existing_source_quality_overlay_not_replaced':True,
            'independently_resolved_prior_missing_evidence':independently_resolved,
            'historical_protocol_not_native_equivalent':True,'training_started':False,'body_exported':False})
    p=control/'reasoning_pair_lineage_decisions.jsonl.gz';q=control/'reasoning_resource_nodes.jsonl.gz'
    for path, vals in [(p,decisions),(q,resource_nodes.values())]:
        with gzip.open(path,'wt',encoding='utf-8',newline='\n') as f:
            for v in vals:f.write(js(v)+'\n')
    report={'schema_version':'wrd-reasoning-resource-lineage-v6','pairs':len(decisions),
        'terminal_counts':dict(Counter(v['status'] for v in decisions)),
        'by_branch':{k:dict(Counter(v['status'] for v in decisions if v['branch']==k)) for k in sorted({v['branch'] for v in decisions})},
        'missing_reasons':dict(Counter(b['reason'] for v in decisions for b in v['blocking_evidence'])),
        'resource_nodes':len(resource_nodes),'verified_resource_nodes':sum(v['immutable_bytes_sha256_verified'] for v in resource_nodes.values()),
        'source_input_sha256':hf(INPUT),'controller_projection_sha256':hf(ROOT/'research/pipelines/skillsloop_ewi_v2/pipeline.py'),
        'independent_reasoning_review_sha256':independent_sha,
        'artifact_sha256':{str(z.relative_to(OUT)):hf(z) for z in [p,q]},'script_sha256':hf(Path(__file__)),
        'new_model_calls':0,'training_started':False,'scope_admission_not_outcome_or_semantic_gold':True}
    (OUT/'REASONING_LINEAGE_REPORT.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False))
if __name__=='__main__':main()
