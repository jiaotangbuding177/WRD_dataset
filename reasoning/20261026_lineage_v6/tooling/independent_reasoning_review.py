"""Offline independent evidence for original-R and real feedback repair chains.

Does not execute historical code, tools, agents, graders or training. Proves
specific projections/copies against recorded bytes; quality admission remains a
different overlay. Historical annotations are not made into semantic gold.
"""
from collections import Counter
from copy import deepcopy
from datetime import datetime
import ast
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import posixpath

ROOT = Path('D:/skillloop')
OUT = ROOT / 'output/20261026_wrd_lineage_v6'
INPUT = ROOT / 'output/20261026_wrd_sequences_v6/controlled/reasoning_pair_lineage_inputs.jsonl.gz'


def js(v): return json.dumps(v, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
def h(b): return hashlib.sha256(b).hexdigest()
def hf(p): return h(Path(p).read_bytes())
def read(p): return json.loads(Path(p).read_text(encoding='utf-8-sig'))


def rows(p):
    with gzip.open(p, 'rt', encoding='utf-8-sig') as f:
        for line in f:
            if line.strip(): yield json.loads(line)


def walk(v, pointer=''):
    if isinstance(v, dict):
        yield pointer, v
        for k, child in v.items(): yield from walk(child, pointer + '/' + str(k))
    elif isinstance(v, list):
        for i, child in enumerate(v): yield from walk(child, pointer + '/' + str(i))


def stamp(v):
    return datetime.fromisoformat(v.replace('Z', '+00:00')).timestamp()


def source_pin(path, function):
    p = ROOT / path; text = p.read_text(encoding='utf-8-sig')
    n = next(n for n in ast.walk(ast.parse(text)) if isinstance(n, ast.FunctionDef) and n.name == function)
    return {'path': path, 'sha256': hf(p), 'function': function, 'line': n.lineno,
            'function_source_sha256': h(ast.get_source_segment(text, n).encode()),
            'current_code_pin_not_claimed_unmodified_historical_runtime': True}


def main():
    control = OUT / 'controlled'; control.mkdir(parents=True, exist_ok=True)
    cas = control / 'independent_reasoning_cas'; cas.mkdir(exist_ok=True)
    inputs = list(rows(INPUT)); before_hash = hf(INPUT)
    baseline_path = control / 'reasoning_pair_lineage_decisions.jsonl.gz'
    baseline_sha = hf(baseline_path)
    baseline = {x['pair_id']: x for x in rows(baseline_path)}
    preserved = {}

    def preserve(p, expected=None, kind='recorded_evidence'):
        p = Path(p); raw = p.read_bytes(); digest = h(raw)
        assert expected is None or digest == expected
        dest = cas / digest
        if not dest.exists(): dest.write_bytes(raw)
        assert hf(dest) == digest
        preserved[str(p)] = {'source_path': str(p), 'sha256': digest, 'bytes': len(raw),
            'kind': kind, 'immutable_export_path': str(dest.relative_to(ROOT)).replace('\\', '/'),
            'declared_sha_matches': expected is None or digest == expected}
        return raw

    sse = []; branch_count = 0; source_early = 0; related_count = 0
    for x in inputs:
        if x.get('parent_run_record'): continue
        req = x['original_request']; u = json.loads(req['messages'][1]['content']); sid = u['current_source_id']
        sp = x['existing_source_identity_review']['source_proof']
        source_bytes = Path(sp['source_file']).read_bytes()
        physical = source_bytes.split(b'\n')[sp['physical_line'] - 1]
        assert h(physical) == sp['source_record_sha256'] == sp['expected_source_record_sha256']
        source = json.loads(physical.decode('utf-8-sig'))
        assert source.get('source_id', source.get('session_id')) == sid
        complete = u['complete_source']; restored = deepcopy(complete)
        if 'messages' not in restored:
            restored['messages'] = [m for t in restored['turns'] for m in [t['user'], *t['assistant_messages']]]
        if u.get('original_complete_source_sha256'):
            assert h(js(restored).encode()) == u['original_complete_source_sha256']
            source_proof = 'declared complete-source canonical SHA reconstructed after exact duplicate removal'
        else:
            # Older requests have no projection/hash field. Compare their
            # complete object directly with the physically pinned original.
            adjusted = deepcopy(source)
            adjusted['source_id'] = adjusted.get('source_id', adjusted.get('session_id'))
            assert complete == source or complete == adjusted
            source_early += 1
            source_proof = 'older complete_source exactly equals physically pinned original object'
        related = set(u['state'].get('related_source_ids', []))
        assert related <= {sid}
        related_count += bool(related)
        outcome = x['original_action_outcome_evidence']; transcript = read(outcome['source_transcript_path'])
        assert hf(outcome['source_transcript_path']) == outcome['source_transcript_sha256']
        prior = [v for v in transcript if v['decision'] < u['decision_number']]
        public = deepcopy(prior[-4:])
        for row in public:
            obs = row.get('event', {}).pop('observation', None)
            if obs is not None: row['event']['observation_ref'] = {k: obs.get(k) for k in ('execution_id', 'tool_return_ref', 'tool_return_sha256')}
        assert public == u['recent_interactions']
        proofs = []
        for observation in u['state'].get('recent_observations', []):
            found = []
            for pointer, value in walk(prior):
                if value.get('execution_id') != observation['execution_id'] or not value.get('tool_return_ref'): continue
                raw = preserve(value['tool_return_ref'], observation['tool_return_sha256'], 'earlier_actual_tool_receipt')
                native = json.loads(raw.decode('utf-8-sig'))
                assert all(value.get(k) == native.get(k) for k in ('execution_id', 'source_id', 'tool', 'actual'))
                assert all(k not in value or value[k] == v for k, v in native.items())
                registered = {**native, **value, 'tool_return_sha256': h(raw)}
                if registered == observation: found.append(pointer)
            assert found, 'observation missing from recursive earlier transcript'
            child = any('/branches/' in pointer for pointer in found)
            branch_count += child
            proofs.append({'execution_id': observation['execution_id'], 'earlier_transcript_pointers': found,
                'exact_controller_registered_projection_matches': True, 'is_branch_receipt': child,
                'receipt_sha256': observation['tool_return_sha256'], 'source_id': sid,
                'future_decisions_used': False})
        cleared = ['RELATED_SOURCE_HISTORY_NOT_IN_SINGLE_SOURCE_PACKET', 'STATE_OBSERVATION_NOT_FOUND_IN_PRIOR_TRANSCRIPT',
                   'COMPLETE_SOURCE_POLICY_PROJECTION_ORIGINAL_HASH_ABSENT']
        residual = [b for b in baseline[x['pair_id']]['blocking_evidence'] if b['reason'] not in cleared]
        sse.append({'pair_id': x['pair_id'], 'source_id': sid, 'decision_number': u['decision_number'],
            'physical_source_line_sha256_verified_including_recorded_cr': True,
            'complete_source_proof': source_proof, 'source_complete_canonical_sha256': h(js(restored).encode()),
            'related_source_ids_only_current_source': True, 'related_source_ids_are_workflow_refs_not_hidden_history': True,
            'public_recent_interactions_projection_exact': True,
            'state_observation_proofs': proofs, 'resolved_reason_codes': cleared,
            'remaining_baseline_blocking_evidence': residual,
            'lineage_missing_reasons_resolved': not residual,
            'semantic_gold_not_created': True})
    runs = {x['parent_run_id']: x['parent_run_record'] for x in inputs if x.get('parent_run_record')}
    outputs = {o['path']: (rid, o) for rid, run in runs.items() for o in run['observed_result']['output_files']}
    validation_base = Path('E:/skillloop_runs/20261019_auto_workflow_pilot')
    validations = {str(p): read(p) for p in validation_base.glob('validation_attempt_*/validation.json')}
    copy_edges = []; feedback_proofs = []; packet_refs = {}
    for rid, run in runs.items():
        packet_refs[rid] = {c['destination']: c for c in run['observed_input_packet']['copies']}
        for c in run['observed_input_packet']['copies']:
            preserve(c['copy']['path'], c['copy']['sha256'], 'actual_dispatched_input')
            assert c['source']['sha256'] == c['copy']['sha256']
            if not any(k in c['destination'] for k in ('previous_candidate', 'previous_learning')): continue
            parent_id, product = outputs[c['source']['path']]
            assert product['sha256'] == c['copy']['sha256'] and product['bytes'] == c['copy']['bytes']
            assert stamp(runs[parent_id]['observed_result']['finished_at']) < stamp(run['observed_input_packet']['started_at'])
            copy_edges.append({'consumer_run_id': rid, 'destination': c['destination'], 'producer_run_id': parent_id,
                'producer_recorded_output_path': product['path'], 'sha256': product['sha256'], 'bytes': product['bytes'],
                'copy_and_source_and_prior_result_output_sha_equal': True,
                'parent_finished_before_consumer_started': True,
                'previous_quality_or_success_not_inferred_from_copy': True})
        for c in run['observed_input_packet']['copies']:
            if 'feedback' not in c['destination']: continue
            facts = read(c['copy']['path']); fp = {'consumer_run_id': rid, 'destination': c['destination'],
                'feedback_sha256': c['copy']['sha256'], 'actual_dispatched_copy_sha_verified': True,
                'deterministic_field_proofs': [], 'original_research_annotation_not_teacher_private_reasoning': True}
            if 'previous_validation' in facts:
                matches = [p for p, v in validations.items() if v == facts['previous_validation']]
                assert len(matches) == 1
                validation = facts['previous_validation']; vp = matches[0]
                preserve(vp, kind='original_development_validation')
                rebuilt = []
                for item in validation['development_cases']:
                    q = json.loads(preserve(item['quality']['path'], item['quality']['sha256'], 'actual_development_quality').decode('utf-8-sig'))
                    detail = {'id': item['id'], 'passed': item['passed'], 'exit_code': item['exit_code'],
                              'failed_or_unknown_checks': [z for z in q.get('checks', []) if z.get('pass') is not True]}
                    if not item['passed']:
                        preserve(item['stderr']['path'], item['stderr']['sha256'], 'actual_development_stderr')
                        preserve(item['stdout']['path'], item['stdout']['sha256'], 'actual_development_stdout')
                        # Original preparer used Path.read_text: preserve its
                        # universal-newline projection, not raw-byte newlines.
                        detail['stderr'] = Path(item['stderr']['path']).read_text(encoding='utf8')[:5000]
                        detail['stdout'] = Path(item['stdout']['path']).read_text(encoding='utf8')[:7000]
                    rebuilt.append(detail)
                assert rebuilt == facts['development_case_diagnostics']
                fp['deterministic_field_proofs'].append({'previous_validation_exact_file': vp,
                    'previous_validation_sha256': hf(vp), 'all_case_quality_stdout_stderr_pin_verified': True,
                    'all_development_diagnostics_exact_projection': True, 'case_count': len(rebuilt)})
            if c['destination'] == 'inputs/closure_feedback.json':
                validation = validations[str(validation_base / 'validation_attempt_04/validation.json')]
                rebuilt = []
                for item in validation['development_cases']:
                    q = json.loads(preserve(item['quality']['path'], item['quality']['sha256'], 'actual_development_quality').decode('utf-8-sig'))
                    rebuilt.append({'id': item['id'], 'exit_code': item['exit_code'],
                                    'all_nonpassing_checks': [z for z in q.get('checks', []) if z['pass'] is not True]})
                assert rebuilt == facts['independent_development_results']
                report_dir = Path(validation['development_cases'][0]['stdout']['path']).parent / 'delivery'
                reports = list(report_dir.rglob('*.json')); assert len(reports) == 1
                actual_report = json.loads(preserve(reports[0], kind='original_candidate_development_report').decode('utf-8-sig'))
                assert facts['actual_development_report_checks'] == actual_report['checks']
                for name in ('preserved_failed_episode', 'source_review', 'public_content_review'):
                    p = facts[name]; preserve(p['path'], p['sha256'], name)
                fp['deterministic_field_proofs'].append({'validation04_cases_exact_projection': True,
                    'actual_program_report_checks_exact': True, 'prior_generation_and_review_pins_verified': True})
            if c['destination'] == 'inputs/report_repair_feedback.json':
                for pin in facts['previous_generation_results']: preserve(pin['path'], pin['sha256'], 'prior_generation_result')
                prior_results = [read(pin['path']) for pin in facts['previous_generation_results']]
                assert facts['prior_statuses'] == [r['status'] for r in prior_results]
                assert facts['prior_measured_token_total'] == sum(r['measured_input_tokens'] + r['measured_output_tokens'] for r in prior_results)
                assert facts['prior_posts'] == sum(r['interface_round_trips'] for r in prior_results)
                for row in facts['candidate03_04_public_bytes_compared']:
                    for side in ('candidate03', 'candidate04'): preserve(row[side]['path'], row[side]['sha256'], 'actual_previous_candidate_version')
                    assert row['candidate03']['sha256'] == row['candidate04']['sha256']
                validation = validations[str(validation_base / 'validation_attempt_04/validation.json')]
                rebuilt = []
                for item in validation['development_cases']:
                    q = json.loads(preserve(item['quality']['path'], item['quality']['sha256'], 'actual_development_quality').decode('utf-8-sig'))
                    rebuilt.append({'id': item['id'], 'exit_code': item['exit_code'],
                        'case_kind': 'correct_refusal_control' if q.get('expected_refusal') is True else 'valid_development',
                        'all_nonpassing_checks': [] if q.get('expected_refusal') is True else [z for z in q.get('checks', []) if z['pass'] is not True]})
                assert rebuilt == facts['actual_development_results']
                report_pin = facts['actual_report_source']
                actual_report = json.loads(preserve(report_pin['path'], report_pin['sha256'], 'original_candidate_report').decode('utf-8-sig'))
                assert actual_report['checks'] == facts['actual_report_checks']
                preserve(facts['inline_program_source']['path'], facts['inline_program_source']['sha256'], 'previous_program_source')
                fp['deterministic_field_proofs'].append({'prior_generation_stats_exact': True,
                    'candidate03_04_pinned_bytes_identical': True, 'validation04_defects_exact_projection': True,
                    'actual_report_and_checks_pinned_and_exact': True})
            feedback_proofs.append(fp)
    read_calls = {}; all_tools = Counter()
    for x in inputs:
        if not x.get('parent_run_record'): continue
        rid = x['parent_run_id']
        for index, m in enumerate(x['original_request']['messages']):
            for call in m.get('tool_calls', []):
                f = call['function']; all_tools[f['name']] += 1
                if f['name'] != 'read_file': continue
                args = json.loads(f['arguments']); p = args['path']
                c = packet_refs[rid][p]
                assert not Path(p).is_absolute() and '..' not in Path(p).parts
                assert hf(c['copy']['path']) == c['copy']['sha256']
                read_calls[(rid, call['id'])] = {'run_id': rid, 'call_id': call['id'], 'path': p,
                    'pinned_packet_copy_sha256': c['copy']['sha256'], 'line_or_character_projection': args,
                    'read_only_tool_with_declared_input_copy': True}
    # Six exact historical programs, manually inspected above the general
    # parser's dynamic-name false positives. Pin the reviewed programs rather
    # than allowing arbitrary dynamic code or treating missing sensors as zero IO.
    reviewed_dynamic = {
        'call79f098ecad7549e88612be22d64d3d12': '6e886cd93ea0cb06bb4b4e0934c76e365b0342eafc16d602cd0bed6f42b86181',
        'call28857170f7364df387d0851e629d87e2': '80a4dfc61c23290ae1ecbc8e904de0952a9ec7e190bdda9fd6620bcdffa72dc5',
        'call08a9f1da56434b48972dade85f748a53': 'e69ee42718fce76e00cc251c15eccf992df46a29037e68ad5783102ed42567c3',
        'call8cd096a2b8fb4f92bd1a86103719824c': 'b8e31abd6aeb3954a6f4950ebb7bf4d3d9cfe9c2f4c17c8926da5488c6d566cc',
        'call4997f0e15290452e913fe7163d605552': '37add80d243adbe7de542a7e4811d6bb1f6d17f36f102ffe30aa616dfcb66638',
        'call6ea6b842720f46c0bb4510f89196e96b': 'c30bb5d835488af5198ecd518f9ebaf1715b2d4adf502d131262a3a06cd93278'}
    dynamic_proofs = []
    for rid, run in runs.items():
        for call_path in sorted((Path(run['run_path']) / 'tool_actions').glob('*/call.json')):
            call = read(call_path)
            if call['id'] not in reviewed_dynamic: continue
            code = json.loads(call['function']['arguments'])['code']
            assert h(code.encode()) == reviewed_dynamic[call['id']]
            preserve(call_path, kind='original_actual_tool_call')
            receipt_path = call_path.parent / 'receipt.json'; receipt = read(receipt_path)
            preserve(receipt_path, kind='original_actual_tool_receipt')
            preserve(receipt['code']['path'], receipt['code']['sha256'], 'original_tool_program_source')
            assert Path(receipt['code']['path']).read_text(encoding='utf8') == code
            proof = {'run_id': rid, 'call_id': call['id'], 'code_sha256': h(code.encode()),
                'tool_receipt_sha256': hf(receipt_path), 'action_ordinal': call_path.parent.name,
                'actual_script_file_sha256': receipt['code']['sha256'],
                'actual_script_universal_newline_text_equals_original_call_code': True,
                'review_scope': 'only this exact recorded code, input packet, and original observed IO',
                'historical_code_executed_by_auditor': False,
                'quality_admission_not_inferred_from_source_closure': True}
            if call['id'].startswith('call79f098'):
                try: ast.parse(code)
                except SyntaxError: pass
                else: raise AssertionError('expected exact historical SyntaxError source')
                feedback = read(call_path.parent / 'feedback.json')
                preserve(call_path.parent / 'feedback.json', kind='actual_syntax_error_feedback')
                assert 'SyntaxError' in js(feedback) and feedback['exit_code'] != 0
                proof.update({'closure_basis': 'Python rejects whole script at compile before executing any body statement',
                    'syntax_failure_actual_receipt_verified': True, 'script_body_input_reads_executed': False,
                    'resolved_external_data_paths': [], 'unrecorded_no_sensor_not_used_as_zero_io_proof': True})
            else:
                tree = ast.parse(code)
                imports = {n.name.split('.')[0] for node in ast.walk(tree) if isinstance(node, ast.Import) for n in node.names}
                assert imports <= {'json', 'os', 'hashlib', 'shutil', 'openpyxl'}
                assert not any(isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id in {'eval','exec','compile','__import__'} for n in ast.walk(tree))
                assert not any(isinstance(n, ast.ImportFrom) for n in ast.walk(tree))
                audit = receipt['file_open_audit']; raw = preserve(audit['path'], audit['sha256'], 'original_process_file_open_sensor')
                events = [json.loads(l) for l in raw.decode('utf8').splitlines() if l.strip()]
                path_proofs = []
                for path in sorted({e['relative_path'].replace('\\', '/') for e in events}):
                    assert not Path(path).is_absolute() and '..' not in Path(path).parts
                    if path.startswith('inputs/'):
                        cp = packet_refs[rid][path]
                        assert hf(cp['copy']['path']) == cp['copy']['sha256']
                        path_proofs.append({'workspace_relative_path': path, 'source_kind': 'original_packet_copy',
                                            'sha256': cp['copy']['sha256']})
                    else:
                        assert path.startswith(('outputs/', 'work/'))
                        path_proofs.append({'workspace_relative_path': path, 'source_kind': 'same_run_generated_output_or_workfile',
                            'not_a_new_external_resource_ancestor': True})
                case_proofs = []
                if not call['id'].startswith('call288571'):
                    mapping = packet_refs[rid]['inputs/development_cases.json']
                    cases = read(mapping['copy']['path'])
                    case_requests = [('original_recovery', 'inputs/dev_request.json')] + [(c['id'], c['request']) for c in cases]
                    for cid, request_path in case_requests:
                        assert all(c.isalnum() or c in '-_' for c in cid)
                        pin = packet_refs[rid][request_path]; request = read(pin['copy']['path'])
                        for name in ('input_workbook', 'output_workbook', 'report_file'):
                            rel = request[name].replace('\\', '/')
                            assert not Path(rel).is_absolute()
                            if name != 'input_workbook':
                                for candidate_root in (f'outputs/report_repair_tests/{cid}', f'outputs/report_repair_tests/{cid}/case_root'):
                                    resolved = posixpath.normpath(posixpath.join(candidate_root, rel))
                                    assert resolved.startswith('outputs/') and not resolved.startswith('../')
                        input_path = posixpath.normpath(posixpath.join(posixpath.dirname(request_path), request['input_workbook'].replace('\\', '/')))
                        assert input_path in packet_refs[rid]
                        case_proofs.append({'case_id': cid, 'request_path': request_path,
                            'request_sha256': pin['copy']['sha256'], 'input_workbook': input_path,
                            'input_sha256': packet_refs[rid][input_path]['copy']['sha256'],
                            'output_workbook_relative': request['output_workbook'],
                            'report_file_relative': request['report_file'],
                            'all_request_paths_relative_and_resolve_inside_workspace': True,
                            'legitimate_parent_relative_output_paths_not_misclassified_as_external': True})
                proof.update({'closure_basis': 'fixed reviewed sha helper plus finite declared case/request paths; actual inside-workspace file-open receipts agree',
                    'imports_fixed_and_no_eval_exec_network_api': True,
                    'dynamic_parameter_bindings': 'sha(p) receives listed copied files or same-run outputs; reqp is finite supplied case list; report_path is fixed same-run case root plus pinned relative request field',
                    'recorded_file_open_paths': path_proofs, 'finite_case_request_bindings': case_proofs,
                    'file_open_sensor_sha256': audit['sha256'],
                    'os_level_no_external_reads_certified': False,
                    'sensor_limit': 'Original hook records in-workspace opens only and is not inherited by subprocesses; exact program/dataflow review supplies the narrow path proof, absence of sensor records does not.'})
            dynamic_proofs.append(proof)
    assert len(dynamic_proofs) == 6
    # A complete, byte-verifiable report-evidence repair example. Reconstruct
    # literal line replacements as data; never execute the historical program.
    repair = next(x for x in inputs if x['pair_id'] == '0753780cad3b696a12766199')
    run5 = repair['parent_run_record']; rid5 = repair['parent_run_id']
    call = repair['original_response']['choices'][0]['message']['tool_calls'][0]
    code = json.loads(call['function']['arguments'])['code']; tree = ast.parse(code)
    assignments = {n.targets[0].id: n.value for n in tree.body
                   if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name)}
    new5, new6 = ast.literal_eval(assignments['new5']), ast.literal_eval(assignments['new6'])
    previous = packet_refs[rid5]['inputs/previous_candidate/scripts/run.py']
    original_program = preserve(previous['copy']['path'], previous['copy']['sha256'], 'actual_previous_program')
    lines = original_program.decode('utf8').split('\r\n')
    needles = {k: next(n.value for n in ast.walk(assignments[k]) if isinstance(n, ast.Constant) and isinstance(n.value, str))
               for k in ('i5', 'i6')}
    pos5 = [i for i, line in enumerate(lines) if needles['i5'] in line]
    pos6 = [i for i, line in enumerate(lines) if needles['i6'] in line]
    assert len(pos5) == len(pos6) == 1
    lines[pos5[0]:pos5[0] + 1] = new5
    offset6 = pos6[0] + len(new5) - 1
    lines[offset6:offset6 + 1] = new6
    reconstructed_program = '\r\n'.join(lines).encode('utf8')
    final_program = next(o for o in run5['observed_result']['output_files']
                         if o['path'].replace('\\', '/').endswith('/candidate/scripts/run.py'))
    assert h(reconstructed_program) == final_program['sha256']
    preserve(final_program['path'], final_program['sha256'], 'actual_repaired_program')
    step = next(s for s in run5['actual_steps'] if s['pair_id'] == repair['pair_id'])
    actual_returns = [m for m in step['observations_before_next_response'] if m.get('role') == 'tool'
                      and m.get('tool_call_id') == call['id']]
    assert len(actual_returns) == 1 and final_program['sha256'] in js(actual_returns[0])
    tool_return = json.loads(actual_returns[0]['content']); assert tool_return['exit_code'] == 0
    assert step['next_request_has_exact_current_prefix'] and step['next_request_contains_current_response_body']
    validation4_path = validation_base / 'validation_attempt_04/validation.json'
    validation5_path = validation_base / 'validation_attempt_05/validation.json'
    v4, v5 = read(validation4_path), read(validation5_path)
    preserve(validation4_path, kind='earlier_actual_development_validation')
    preserve(validation5_path, kind='later_actual_development_validation')
    assert previous['copy']['sha256'] in js(v4['candidate_files'])
    assert final_program['sha256'] in js(v5['candidate_files'])
    assert v5['passed'] is True and len(v5['development_cases']) == 12 and all(z['passed'] for z in v5['development_cases'])
    assert stamp(v4['at']) < stamp(run5['observed_input_packet']['started_at']) < stamp(run5['observed_result']['finished_at']) < stamp(v5['at'])
    feedback5 = packet_refs[rid5]['inputs/report_repair_feedback.json']
    parent3_id, parent3_output = outputs[previous['source']['path']]
    validator_limits = []
    for path, value in sorted(validations.items()):
        grader = value['grader']; current_grader_sha = hf(grader['path'])
        validator = value.get('validator_source')
        validator_limits.append({'validation_path': path, 'validation_sha256': hf(path),
            'historical_grader_sha256': grader['sha256'], 'current_grader_sha256': current_grader_sha,
            'current_grader_matches_recorded': current_grader_sha == grader['sha256'],
            'validator_source_pin_present': bool(validator),
            'historical_validator_sha256': validator.get('sha256') if validator else None,
            'current_validator_matches_recorded': hf(validator['path']) == validator['sha256'] if validator else None})
    causal_example = {'scope': 'historical one-source report-evidence repair, not a new autonomous-agent result',
        'parent_run_id': parent3_id, 'parent_candidate_output_path': parent3_output['path'],
        'parent_candidate_program_sha256': parent3_output['sha256'],
        'previous_actual_validation_path': str(validation4_path), 'previous_actual_validation_sha256': hf(validation4_path),
        'previous_actual_validation_at': v4['at'],
        'feedback_source_path': feedback5['source']['path'], 'feedback_sha256': feedback5['copy']['sha256'],
        'feedback_derived_from_actual_validation04_report_and_quality_proven_above': True,
        'consumer_run_id': rid5, 'consumer_started_at': run5['observed_input_packet']['started_at'],
        'feedback_available_by_start_via_original_packet_copy_sha': True,
        'feedback_native_destination': feedback5['destination'],
        'previous_program_native_copy_destination': previous['destination'],
        'previous_program_source_and_input_copy_sha_equal': previous['source']['sha256'] == previous['copy']['sha256'],
        'observed_before_writer': {'actual_request_preserved': True,
            'full_feedback_object_not_claimed_visible': True,
            'model_used_original_recorded_request_tool_outputs_and_partial_feedback_views': True},
        'original_repair_response_pair_id': repair['pair_id'],
        'original_response_canonical_sha256': repair['original_response_canonical_sha256'],
        'original_request_canonical_sha256': repair['original_request_canonical_sha256'],
        'original_response_created_unix': repair['original_response']['created'],
        'repair_tool_call_id_sha256': h(call['id'].encode()), 'repair_code_sha256': h(code.encode()),
        'static_literal_line_patch_reconstruction_equals_actual_output': True,
        'historical_program_not_executed_by_auditor': True,
        'actual_tool_return_exit_code': tool_return['exit_code'],
        'actual_tool_return_reports_repaired_program_sha256': True,
        'tool_return_canonical_sha256': h(js(actual_returns[0]).encode()),
        'next_request_has_exact_original_prefix_and_response': True,
        'repaired_program_sha256': final_program['sha256'], 'repaired_program_bytes': final_program['bytes'],
        'run_finished_at': run5['observed_result']['finished_at'],
        'later_validation_path': str(validation5_path), 'later_validation_sha256': hf(validation5_path),
        'later_validation_at': v5['at'], 'later_validation_same_candidate_program_sha256': True,
        'later_validation_passes': 12, 'later_validation_cases': 12,
        'does_not_relabel_previous_bad_code_writers_correct': True,
        'explicit_private_reasoning_in_this_raw_example': False,
        'learnable_signal': 'Observed Q18 report evidence problem -> local literal patch -> actual tool SHA/result -> subsequent independent historical development feedback; original failures and budgets remain.'}
    report = {'schema_version': 'wrd-independent-original-reasoning-review-v6',
        'status': 'PROJECTION_AND_REPAIR_DEPENDENCY_EVIDENCE_FOR_ENGINE_REVIEW',
        'input_rows': len(inputs), 'sse_rows': len(sse),
        'all_sse_baseline_missing_reasons_resolved': all(x['lineage_missing_reasons_resolved'] for x in sse),
        'same_source_related_refs_not_cross_source_rows': related_count,
        'nested_prior_branch_observation_projections_exact': branch_count,
        'early_complete_source_without_declared_hash_exact_physical_objects': source_early,
        'sse_pair_proofs': sse, 'raw_runs': len(runs),
        'prior_candidate_output_copy_edges': copy_edges, 'prior_candidate_copy_edges_all_exact': len(copy_edges) == 21,
        'real_feedback_field_projection_proofs': feedback_proofs,
        'raw_read_file_unique_calls': list(read_calls.values()),
        'exact_raw_dynamic_call_closure_proofs': dynamic_proofs,
        'complete_causal_repair_example_without_enterprise_body': causal_example,
        'historical_grader_and_validator_fingerprint_limits': validator_limits,
        'unsupported_tool_label_was_not_unknown_resource_access': True,
        'arbitrary_raw_dynamic_reads_not_automatically_cleared': True,
        'six_specifically_reviewed_original_dynamic_calls_resolved': True,
        'current_feedback_is_historical_observation_not_quality_gold': True,
        'initial_grader_current_bytes_differ_and_validator_source_pin_absent_preserve_negative_evidence': True,
        'final_validation_pass_does_not_retroactively_validate_old_code_writer_targets': True,
        'source_input_sha256_before': before_hash, 'source_input_sha256_after': hf(INPUT),
        'baseline_decisions_sha256_reviewed': baseline_sha,
        'controller_code_pins': [source_pin('research/pipelines/skillsloop_ewi/controller.py', 'record_observation'),
            source_pin('research/pipelines/skillsloop_ewi/controller.py', 'build_view'),
            source_pin('research/pipelines/skillsloop_ewi_v2/pipeline.py', 'public_interactions'),
            source_pin('research/pipelines/auto_workflow_pilot_v1/prepare_repair.py', 'main'),
            source_pin('research/pipelines/auto_workflow_pilot_v1/prepare_closure.py', 'main'),
            source_pin('research/pipelines/auto_workflow_pilot_v1/prepare_report_repair.py', 'main')],
        'preserved_evidence_files': list(preserved.values()),
        'full_training_admission_not_set_by_this_report': True,
        'training_started': False, 'weights_loaded': False, 'gpu_used': False,
        'historical_tools_or_graders_executed': False, 'new_business_calls': 0,
        'script_sha256': hf(Path(__file__))}
    assert before_hash == report['source_input_sha256_after']
    p = OUT / 'INDEPENDENT_REASONING_REVIEW.json'
    p.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    print(js({'sse_rows': len(sse), 'sse_missing_all_resolved': report['all_sse_baseline_missing_reasons_resolved'],
              'branch_projections': branch_count, 'prior_copy_edges': len(copy_edges),
              'feedbacks': len(feedback_proofs), 'read_file_calls': len(read_calls),
              'preserved_files': len(preserved), 'report_sha256': hf(p)}))


if __name__ == '__main__': main()
