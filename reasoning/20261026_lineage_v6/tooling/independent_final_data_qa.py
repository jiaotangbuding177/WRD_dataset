"""Independent final arrays/source/mask review. CPU only; no trainer or weights.

Re-renders original source objects with the declared causal template, performs
fresh tokenizer calls, derives owned token positions from original role/field
boundaries, and checks immutable source/resource snapshots. Never fuses stages.
"""
from array import array
from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
import gzip
import hashlib
import json
import os
from pathlib import Path
import sys
import traceback

os.environ['CUDA_VISIBLE_DEVICES'] = ''
ROOT = Path('D:/skillloop')
OUT = ROOT / 'output/20261026_wrd_sequences_v6'
V4 = ROOT / 'output/20261025_wrd_reasoning_recovery_v4'
REPORT = ROOT / 'output/20261026_wrd_lineage_v6/INDEPENDENT_FINAL_DATA_QA.json'
EXPECTED_MANIFEST = '00cf9a2091ddf623c6136bf25e8a61579181d307575c9b938506a5147f4c443c'
HEADER = '<|im_start|>assistant\n'
END = '<|im_end|>\n'
OPEN = '<think>\n'
CLOSE = '\n</think>\n\n'

def sha(b): return hashlib.sha256(b).hexdigest()
def js(v): return json.dumps(v, ensure_ascii=False, separators=(',', ':'))
def sorted_js(v): return json.dumps(v, ensure_ascii=False, separators=(',', ':'), sort_keys=True)
def read(p): return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def hf(p):
    h = hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda: f.read(1048576), b''): h.update(b)
    return h.hexdigest()

def rows(p):
    with gzip.open(p, 'rt', encoding='utf-8-sig') as f:
        return [json.loads(l) for l in f if l.strip()]

def id_hash(ids):
    a = array('I', ids)
    if sys.byteorder != 'little': a.byteswap()
    return sha(a.tobytes())

def native_adapter(source):
    result = []
    if source.get('system'): result.append({'role': 'system', 'content': source['system']})
    for m in source['messages']:
        c = m.get('content', ''); text = ''; calls = []; thought = ''
        if isinstance(c, str): text = c
        else:
            for b in c or []:
                if b.get('type') == 'text': text += str(b.get('text', ''))
                elif b.get('type') == 'toolCall': calls.append({'id': b.get('id'), 'type': 'function', 'function': {'name': b.get('name'), 'arguments': js(b.get('arguments', {}))}})
                elif b.get('type') in ('thinking', 'reasoning'): thought += str(b.get('thinking', b.get('text', '')))
                else: raise AssertionError('unsupported original native content block')
        role = m['role']
        if role in ('toolResult', 'tool'): r = {'role': 'tool', 'tool_call_id': m.get('toolCallId'), 'content': text}
        else:
            r = {'role': role, 'content': text}
            if calls: r['tool_calls'] = calls
            if role == 'assistant': r['reasoning_content'] = m.get('reasoning_content') if isinstance(m.get('reasoning_content'), str) else thought
        result.append(r)
    return result

def registry(raw):
    if isinstance(raw, dict): raw = raw.get('tools', [])
    result = {}
    for value in raw or []:
        if not isinstance(value, dict): continue
        f = value.get('function', value)
        if not isinstance(f, dict) or not isinstance(f.get('name'), str) or not isinstance(f.get('parameters'), dict): continue
        if any(k in js(f) for k in ('trajectory-depth-limit', '[Truncated]', '[Malformed diagnostic JSON redacted]')): continue
        result[f['name']] = {'type': 'function', 'function': f}
    return list(result.values())

def normalize_messages(values):
    values = deepcopy(values)
    for m in values:
        if m.get('role') == 'assistant': m['reasoning_content'] = m.get('reasoning_content') if isinstance(m.get('reasoning_content'), str) else ''
    return values

def stats(rs):
    ts = [t for r in rs for t in r['targets'] if t['owned_supervision_spans']]
    comp = Counter()
    for r in rs: comp.update(r['supervised_tokens_by_component'])
    return {'windows': len(rs), 'original_parent_targets': len(ts),
        'input_tokens': sum(len(r['input_ids']) for r in rs),
        'supervised_tokens': sum(r['supervised_tokens'] for r in rs),
        'supervised_tokens_by_component': dict(comp), 'le16k_windows': sum(len(r['input_ids']) <= 16384 for r in rs),
        'le32k_windows': sum(len(r['input_ids']) <= 32768 for r in rs),
        'target_causal_end_le16k': sum(t['response_end_token_exclusive'] <= 16384 for t in ts),
        'target_causal_end_le32k': len(ts),
        'complete_native_stage_windows': sum(r.get('stage_complete_in_this_view') is True for r in rs),
        'explicit_native_stage_prefix_windows': sum(r.get('stage_complete_in_this_view') is False for r in rs),
        'complete_original_request_current_response_windows': sum('source_pair_file' in r for r in rs),
        'original_R_positive_windows': sum(any(s[2].startswith('R') for s in r['supervision_spans']) for r in rs),
        'exact_historical_resource_execution_versions_proven': sum(r.get('exact_historical_resource_execution_version_proven') is True for r in rs),
        'by_original_stage': dict(Counter(r.get('kind', r.get('role_scope')) for r in rs))}

def main():
    from tokenizers import Tokenizer
    from transformers.utils.chat_template_utils import _compile_jinja_template
    manifest_path = OUT / 'TRAINING_MANIFEST.json'; manifest_sha = hf(manifest_path)
    assert manifest_sha == EXPECTED_MANIFEST, 'final manifest differs from compiler freeze signal'
    manifest = read(manifest_path); data_report = read(OUT / 'ADMITTED_DATA_REPORT.json')
    assert not manifest['training_started'] and not manifest['training_execution_authorized']
    assert not manifest['complete_autonomous_training_or_deployment_ready']
    assert not manifest['native_lineage_review_pending']
    contracts = {p.parent.parent.name: p for p in (ROOT / 'benchmark').glob('*/contracts/evaluation.jsonl') if p.parent.parent.name in {
        'enterprise_split_v9_20261010', 'enterprise_input_closed_v11_20261012', 'enterprise_original_inputs_v10_20261011', 'enterprise_final_delivery_v8_20261010'}}
    protected = {json.loads(l)['session_id'] for p in contracts.values() for l in p.open(encoding='utf-8-sig') if l.strip()}
    assert len(protected) == 226
    source_hashes = {}
    for path, expected in manifest['source_sha256'].items():
        p = Path(path) if Path(path).is_absolute() else ROOT / path
        assert hf(p) == expected, 'manifest source evidence changed'
        source_hashes[str(p)] = expected
    snapshots = {}
    for name, pin in manifest['immutable_lineage_decision_inputs'].items():
        p = OUT / pin['immutable_snapshot']; assert hf(p) == pin['sha256']
        snapshots[name] = rows(p)
    nd = {d['episode_id']: d for d in snapshots['native_decisions']}
    rd = {d['pair_id']: d for d in snapshots['reasoning_decisions']}
    resource_receipts = []; exported_nodes = set()
    for name in ('admitted.resource_closure.index.jsonl.gz', 'admitted.reasoning_resource_closure.index.jsonl.gz'):
        for n in rows(OUT / 'controlled' / name):
            identity = n.get('file_identity', n); p = OUT / n['byte_exact_export_path']
            assert p.stat().st_size == identity['bytes'] and hf(p) == identity['sha256']
            assert p.name == identity['sha256']
            node = n['resource_closure_node']
            assert not node.get('protected_source_ids', [])
            if node.get('source_id'): assert node['source_id'] not in protected
            exported_nodes.add(n['node_id']); resource_receipts.append({'node_id': n['node_id'], 'sha256': identity['sha256'], 'bytes': identity['bytes']})
    admitted_native = {d['episode_id']: d for d in rows(OUT / 'controlled/admitted.lineage_decisions.jsonl.gz')}
    admitted_r = {d['pair_id']: d for d in rows(OUT / 'controlled/admitted.reasoning_lineage_decisions.jsonl.gz')}
    for key, entries, full in [('episode_id', admitted_native, nd), ('pair_id', admitted_r, rd)]:
        for ident, d in entries.items():
            assert d == full[ident] and d['status'] == 'ADMIT' and d['resource_closure_proven'] and d['protected_ancestor_present'] is False
            assert not d['blocking_evidence'] and set(d.get('resource_node_ids', [])) <= exported_nodes
            assert not (set(d.get('observed_allowed_source_ids', d.get('observed_evolution_source_ids', []))) & protected)
    original_pairs = {x['pair_id']: x for x in rows(OUT / 'controlled/reasoning_pair_lineage_inputs.jsonl.gz')}
    exported_pairs = {x['pair_id']: x for x in rows(OUT / 'controlled/admitted.reasoning_source_contexts.jsonl.gz')}
    for oid, x in exported_pairs.items(): assert x == original_pairs[oid] and oid in admitted_r
    raw_quality = {r['pair_id']: r for r in rows(OUT / 'controlled/historical_raw_quality_overlay.jsonl.gz')}
    raw_holds = {i for i, r in raw_quality.items() if not r['target_positive_allowed']}
    native_holds = {r['id'] for r in rows(V4 / 'curated_native/controlled.quality_target_overlay.jsonl.gz')}
    sse_rejects = {r['id'] for r in rows(V4 / 'controlled/sse_action_outcome.labels.jsonl.gz') if r['definite_negative_action']}
    public_pairs = {x['id']: x for name in ('sse_core', 'historical_generation') for x in rows(V4 / ('curated_reasoning/public/' + name + '.pairs.jsonl.gz'))}
    tokenizer_root = ROOT / 'output/20261025_wrd_training_preflight/tokenizer_assets'
    tp = [tokenizer_root / role / 'tokenizer.json' for role in ('primary_14b', 'control_8b')]
    assert hf(tp[0]) == hf(tp[1]); tokenizers = [Tokenizer.from_file(str(p)) for p in tp]
    template = read(V4 / 'CAUSAL_TEMPLATE.json'); assert sha(template['variant'].encode()) == manifest['causal_template_sha256']
    renderer = _compile_jinja_template(template['variant'])
    def render(messages, tools):
        return renderer.render(messages=messages, tools=tools or None, documents=None, add_generation_prompt=False, enable_thinking=False)
    raw_sse_cache = {}; source_file_checks = {}; profiles = {}; per_scope_owners = {}; per_row = []
    r_sources = set(); raw_runs = set(); native_sources = set(); actual_checks = Counter()
    jobs = {x['id']: x for x in (json.loads(l) for l in (ROOT / 'output/20261025_wrd_training_dataset/bundle/catalog/jobs.jsonl').open(encoding='utf8'))}
    for scope in ('controlled', 'public'):
        context = {x['episode_id']: x['original_context'] for x in rows(OUT / scope / 'admitted.contexts.jsonl.gz')}
        owners = {}; scope_banks = {}
        for bank, receipt in manifest['profiles'][scope].items():
            path = OUT / receipt['path']; assert hf(path) == receipt['sha256'] and path.stat().st_size == receipt['bytes']
            bank_rows = rows(path); scope_banks[bank] = stats(bank_rows)
            for key, value in receipt['counts'].items(): assert scope_banks[bank][key] == value, 'manifest count differs from actual arrays'
            for row in bank_rows:
                assert row['training_manifest_admitted'] and row['training_admitted'] and not row['training_execution_authorized']
                assert not row['full_autonomous_controller_demonstration']
                oid = row.get('source_original_pair_id'); eid = row.get('episode_id')
                if bank == 'reasoning':
                    assert oid in admitted_r and oid not in raw_holds | sse_rejects
                    pair = original_pairs[oid]['original_pair'] if scope == 'controlled' else public_pairs[row['id']]
                    req, resp = pair['original_request'], pair['original_response']
                    messages = normalize_messages(req['messages'] + [{**resp['choices'][0]['message'], 'role': 'assistant'}])
                    tools = registry(req.get('tools', [])); decision = admitted_r[oid]
                    if scope == 'controlled':
                        assert row['resource_closure_decision'] == decision
                        for dep in original_pairs[oid]['source_file_dependencies']:
                            p = ROOT / dep['immutable_export_path']
                            source_file_checks[str(p)] = hf(p) == dep['actual_sha256'] == dep['declared_sha256']
                            assert source_file_checks[str(p)]
                        rsrc = original_pairs[oid].get('historical_source_episode_id')
                        if rsrc: r_sources.add(rsrc)
                        proof = original_pairs[oid].get('existing_source_identity_review') or {}
                        evidence = proof.get('complete_semantic_source_evidence') or {}
                        if evidence.get('verified_current_evolution_complete_source'): r_sources.add(evidence['source_id'])
                        if original_pairs[oid].get('parent_run_id'): raw_runs.add(original_pairs[oid]['parent_run_id'])
                    current_reason = messages[-1]['reasoning_content']
                    if scope == 'controlled' and current_reason:
                        pin = pair.get('source_sse'); assert pin is not None, 'explicit R source is not original SSE'
                        if pin['sha256'] not in raw_sse_cache:
                            dep = next(d for d in original_pairs[oid]['source_file_dependencies'] if d['actual_sha256'] == pin['sha256'])
                            raw = (ROOT / dep['immutable_export_path']).read_bytes(); assert sha(raw) == pin['sha256']
                            pieces = []
                            for line in raw.decode('utf-8-sig').splitlines():
                                if not line.startswith('data:'): continue
                                content = line[5:].strip()
                                if not content or content == '[DONE]': continue
                                event = json.loads(content)
                                for choice in event.get('choices', []):
                                    value = (choice.get('delta') or {}).get('reasoning_content')
                                    if isinstance(value, str): pieces.append(value)
                            raw_sse_cache[pin['sha256']] = ''.join(pieces)
                        assert current_reason.encode('utf8') == raw_sse_cache[pin['sha256']].encode('utf8')
                        actual_checks['controlled_original_SSE_R_byte_reconstruction'] += 1
                else:
                    assert eid in admitted_native
                    source = context[eid]; decision = admitted_native[eid]
                    if scope == 'controlled':
                        assert sha(sorted_js(source).encode()) == decision['canonical_episode_sha256']
                        assert row['resource_closure_decision'] == decision
                        job = jobs[source['job_id']]; case = job['payload']['case']
                        assert case['source_id'] not in protected and case['prompt'] in source['messages'][0]['content']
                        proof = next(p for p in decision['initial_case_source_binding_proof'] if p['job_id'] == source['job_id'])
                        assert sha(case['prompt'].encode()) == proof['case_prompt_sha256'] and sha(sorted_js(job).encode()) == proof['catalog_job_sha256']
                        native_sources.add(case['source_id'])
                    if not row['stage_complete_in_this_view']:
                        source = {**source, 'messages': source['messages'][:max(t['source_message_index'] for t in row['targets']) + 1]}
                    messages = normalize_messages(native_adapter(source)); tools = row['tools']
                if scope == 'public': assert row['resource_closure_decision']['controlled_evidence_record_sha256'] == sha(js(decision).encode())
                text = render(messages, tools); ids = row['input_ids']
                assert sha(text.encode()) == row['rendered_sha256'] and row['serialization'] == manifest['causal_template_sha256']
                encoded = tokenizers[0].encode(text, add_special_tokens=False)
                offsets = encoded.offsets
                assert encoded.ids == ids and tokenizers[1].encode(text, add_special_tokens=False).ids == ids
                for tok in tokenizers: assert tok.decode(ids, skip_special_tokens=False) == text
                actual_checks['fresh_encode_calls_each_tokenizer'] += 1; actual_checks['fresh_decode_calls_each_tokenizer'] += 1
                assert len(ids) == row['total_tokens'] <= 32768 and id_hash(ids) == row['input_ids_sha256_u32le']
                assert row['label_ignore_index'] == -100 and sha(js(row['supervision_spans']).encode()) == row['supervision_spans_sha256']
                spans = row['supervision_spans']; assert spans == sorted(s for t in row['targets'] for s in t['owned_supervision_spans'])
                actual_positions = set(); actual_components = Counter()
                for lo, hi, component, weight in spans:
                    assert 0 <= lo < hi <= len(ids) and not actual_positions.intersection(range(lo, hi))
                    actual_positions.update(range(lo, hi)); actual_components[component] += hi - lo
                assert len(actual_positions) == row['supervised_tokens'] > 0 and dict(actual_components) == row['supervised_tokens_by_component']
                expected_positions = set(); expected_components = {}
                for target in row['targets']:
                    owned = target['owned_supervision_spans']; assert sum(b-a for a,b,_,_ in owned) == target['supervised_tokens']
                    if not owned: continue
                    assert target['id'] not in owners and target['id'] not in native_holds
                    assert target['mechanical_usable'] and target.get('observed_native_stop_reason') not in {'length','error','aborted'}
                    mi = target['message_index']; assert messages[mi]['role'] == 'assistant'
                    until = render(messages[:mi + 1], tools); before = render(messages[:mi], tools)
                    assert text.startswith(until) and until.startswith(before)
                    a, b = len(before), len(until)
                    assert target['rendered_assistant_span'] == [a,b] and text[a:b].startswith(HEADER) and text[a:b].endswith(END)
                    thought = messages[mi]['reasoning_content']; content = messages[mi].get('content') or ''
                    assert isinstance(content, str)
                    body = a + len(HEADER); ra = body + len(OPEN); rb = ra + len(thought); ca = rb + len(CLOSE); cb = ca + len(content); end = b-len(END)
                    assert text[a:b].startswith(HEADER + OPEN + thought + CLOSE + content)
                    ranges = [(body,ra,'F'),(ra,rb,'R'),(rb,ca,'F'),(ca,cb,'E' if messages[mi].get('tool_calls') else 'D'),(cb,end,'A'),(end,b,'F')]
                    ranges = [interval for interval in ranges if interval[0] < interval[1]]
                    expected = {i for i,(lo,hi) in enumerate(offsets) if body <= lo < hi <= b}
                    owned_positions = {i for lo,hi,_,_ in owned for i in range(lo,hi)}
                    assert owned_positions == expected and not expected_positions.intersection(expected)
                    for i in expected:
                        lo,hi = offsets[i]; labels = {c for x,y,c in ranges if x<hi and y>lo}
                        expected_components[i] = next(iter(labels)) if len(labels)==1 else 'R_BOUNDARY_MIXED' if 'R' in labels else 'MIXED'
                    for lo,hi,c,w in owned:
                        assert all(expected_components[i] == c for i in range(lo,hi)), 'component differs: '+scope+'/'+bank+'/'+row['id']+'/'+str(lo)+'/'+c
                        assert w == (0.2 if c=='F' else 1.0)
                    expected_positions.update(expected)
                    ending = next((i for i,(lo,hi) in enumerate(offsets) if lo >= b),len(ids))
                    assert ending == target['response_end_token_exclusive']
                    if thought:
                        assert text[ra:rb].encode('utf8') == thought.encode('utf8')
                        actual_checks[scope + ':R_source_field_and_rendered_slice_exact'] += 1
                    if bank != 'reasoning':
                        srcmi = target['source_message_index']; original = context[eid]['messages'][srcmi]
                        assert target['source_message_sha256'] == sha(js(original).encode())
                    owners[target['id']] = (row['id'], bank, oid, target['owned_supervision_spans'])
                assert actual_positions == expected_positions
                labels = [-100] * len(ids)
                for i in actual_positions: labels[i] = ids[i]
                assert sum(v != -100 for v in labels) == row['supervised_tokens']
                actual_checks['source_role_boundaries_and_full_mask_recomputed_rows'] += 1
                per_row.append({'scope':scope,'bank':bank,'record_id':row['id'],'source_pair_id':oid,'episode_id':eid,'tokens':len(ids),'supervised_tokens':row['supervised_tokens'],'original_source_render_and_offsets_match':True})
                if len(per_row) % 16 == 0: print(js({'phase':'independent_original_source_token_offset_mask_QA','rows':len(per_row)}), flush=True)
        recorded = {x['target_id']:x for x in rows(OUT / scope / 'admitted.target_owners.jsonl.gz')}
        assert set(recorded) == set(owners)
        for tid,(record,bank,oid,owned) in owners.items():
            assert recorded[tid]['record_id'] == record and recorded[tid]['bank'] == bank and recorded[tid]['owned_supervision_spans'] == owned
        profiles[scope] = scope_banks; per_scope_owners[scope] = owners
        for r in rows(OUT / scope / 'held.reasoning_known_quality.jsonl.gz'):
            assert not r['training_manifest_admitted'] and not r['training_admitted'] and r['supervision_spans'] == [] and r['supervised_tokens'] == 0
            assert all(t['owned_supervision_spans'] == [] and t['supervised_tokens'] == 0 for t in r['targets'])
    assert set(exported_pairs) == set(admitted_r)
    assert not set(exported_pairs) & (raw_holds | sse_rejects)
    assert profiles['controlled']['native_core']['windows'] == data_report['fixed91_native_quality_positive_episodes'] == 0
    assert len(r_sources) == data_report['historical_unique_proven_business_sources']
    assert len(raw_runs) == data_report['historical_reasoning_parent_raw_runs']
    assert len(native_sources | r_sources) == data_report['all_native_and_historical_unique_proven_business_sources']
    assert data_report['actual_full_A_D_autonomous_native_chains'] == 0
    assert hf(manifest_path) == manifest_sha
    assert all(hf(path) == expected for path,expected in source_hashes.items())
    result = {'schema_version':'wrd-independent-final-source-token-mask-qa-v6',
        'status':'PASS_FOR_SOURCE_CLOSED_PROCESS_SILVER_NOT_COMPLETE_AUTONOMY',
        'manifest_sha256':manifest_sha,'data_report_sha256':hf(OUT/'ADMITTED_DATA_REPORT.json'),
        'profiles_recounted_from_arrays':profiles,'actual_verification_counts':dict(actual_checks),
        'all_immutable_decision_snapshot_hashes_verified':True,'all_positive_decisions_match_frozen_ADMIT_records':True,
        'resource_objects_checked':len(resource_receipts),'resource_receipts':resource_receipts,
        'original_request_response_receipt_SSE_files_checked':len(source_file_checks),
        'all_original_SSE_R_reconstructed_from_raw_stream_deltas_and_compared_as_utf8_bytes':True,
        'all_loss_masks_independently_recomputed_from_original_role_and_field_offsets':True,
        'known_native_reject_or_syntax_hold_targets_checked':len(native_holds),'known_sse_negative_targets_checked':len(sse_rejects),
        'raw_quality_hold_targets_checked':len(raw_holds),'known_held_targets_never_positive':True,
        'owned_target_counts':{s:len(v) for s,v in per_scope_owners.items()},'per_scope_target_owners_unique':True,
        'public_and_controlled_are_overlapping_alternative_projections_not_additive':True,
        'historical_proven_business_source_ids':sorted(r_sources),'historical_raw_parent_run_ids':sorted(raw_runs),
        'native_proven_business_source_ids':sorted(native_sources),
        'source_ids_not_independent_task_count':True,'complete_single_input_native_A_D_autonomous_chains':0,
        'original226_contract_hashes':{k:hf(p) for k,p in contracts.items()},'original226_source_count':len(protected),
        'protected_sources_not_relabelled_or_allowed_for_training_or_checkpoint_threshold_tuning':True,
        'tokenizer_asset_sha256':hf(tp[0]),'causal_template_sha256':manifest['causal_template_sha256'],
        'full_autonomous_training_or_deployment_ready':False,'training_started':False,'weights_loaded':False,'gpu_used':False,'business_api_calls':0,
        'per_row_checks':per_row,'failures':[],
        'limits':['Process silver, not human semantic gold; historical FINISH READY and file writes are not current skill retain/freeze decisions.',
            'The first historical grader bytes differ from its receipt; later repair evidence is bound to the exact later program version, not retroactive success.',
            'Native environment equivalence of historical reasoning protocol and future causal-template runtime integration remain unverified.',
            'Independent Q calibration, complete agent behavior, Spark throughput/cost and training effect were not measured.',
            'Source identifiers and window counts do not establish independent task diversity; semantic near-duplicate groups are unknown.',
            'The original IO sensors are not OS sandbox proofs; narrow fixed-program path evidence is documented in the independent reasoning review.'],
        'script_sha256':hf(Path(__file__))}
    REPORT.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(js({'status':result['status'],'manifest_sha256':manifest_sha,'profiles':profiles,'report_sha256':hf(REPORT)}),flush=True)

if __name__ == '__main__':
    try: main()
    except Exception as error:
        failure={'schema_version':'wrd-independent-final-source-token-mask-qa-v6','status':'FAIL',
            'failures':[{'type':type(error).__name__,'message':str(error),'traceback':traceback.format_exc()}],
            'training_started':False,'gpu_used':False,'business_api_calls':0,'script_sha256':hf(Path(__file__))}
        REPORT.parent.mkdir(parents=True,exist_ok=True)
        REPORT.write_text(json.dumps(failure,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
        print(js({'status':'FAIL','failure_type':type(error).__name__,'detail':str(error)}),flush=True)
        raise
