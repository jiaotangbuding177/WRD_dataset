"""Independent byte/line/prompt checks for the 57-write producer audit."""
from collections import Counter
import importlib.util
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'output/20261027_wrd_main_v10/execution_rescue_01'
REPORT = OUT / 'producer57_extended_static/PRODUCER_AUDIT.json'


def main():
    spec = importlib.util.spec_from_file_location('helpers', ROOT / 'research/data_prep/wrd_main_v10/audit_prepare_ancestry.py')
    h = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(h)
    report = h.load(REPORT)
    projector_spec = importlib.util.spec_from_file_location('literal_projector', ROOT / 'research/data_prep/wrd_main_v10/static_task_dump_projection.py')
    projector = importlib.util.module_from_spec(projector_spec)
    projector_spec.loader.exec_module(projector)
    assert h.pin(report['bounded_static_projector']['path']) == report['bounded_static_projector']
    original226 = set()
    protected_set_pins = []
    for path in sorted((ROOT / 'benchmark').glob('*/contracts/evaluation.jsonl')):
        ids = {r.get('session_id') for r in h.rows(path)} - {None}
        if len(ids) == 226:
            assert not original226 or ids == original226
            original226 = ids
            protected_set_pins.append(h.pin(path))
    newH_path = ROOT / 'output/20261026_ablation_v2/holdout_registry.json'
    newH = set(h.SID.findall(h.canonical(h.load(newH_path))))
    assert len(original226) == 226
    assert report['selected_targets'] == len(set(report['selected_target_ids'])) == 57
    assert report['selected_episodes'] == len(report['episodes']) == 39
    assert h.pin(report['script']['path']) == report['script']
    cache = {}
    counters = Counter()
    affected = []
    all_target_ids = set()

    def checked_events(pin):
        if pin['path'] not in cache:
            assert h.pin(pin['path']) == pin
            cache[pin['path']] = h.events(pin['path'])
        return cache[pin['path']]

    for episode in report['episodes']:
        assert h.pin(episode['actor_request']['path']) == episode['actor_request']
        request = h.load(episode['actor_request']['path'])
        task = request['input']
        assert h.sha(task) == episode['task_input_sha256']
        native = dict(checked_events(episode['actor_native_events']))
        for delivery in episode['actual_native_task_deliveries']:
            msg = native[delivery['native_event_line_1based']]
            assert msg['role'] == 'user' and task in h.text(msg)
            assert h.sha(h.text(msg)) == delivery['actual_user_text_sha256']
            counters['actual_actor_task_deliveries_rechecked'] += 1
        valid_protected_edges = 0
        for producer in episode['matched_producers']:
            events = checked_events(producer['producer_events'])
            lookup = dict(events)
            line = producer['task_emission_native_line_1based']
            msg = lookup[line]
            calls = [c for c in h.calls(msg) if c.get('id') == producer['task_emission_call_id']]
            assert len(calls) == 1
            emissions = [e for e in h.emitted_json(calls[0]) if h.sha(e['content']) == producer['emission_content_sha256']]
            if producer['operation'] == 'bounded_AST_literal_JSON_dump_projection':
                args = calls[0].get('arguments', {})
                args = json.loads(args) if isinstance(args, str) else args
                command = args['command']
                assert h.sha(command) == producer['actual_source_command_sha256']
                emissions = [{'value': value} for value in projector.project(command)
                             if h.sha(h.canonical(value)) == producer['emission_content_sha256']]
            assert emissions
            assert any(isinstance(v, dict) and v.get('prompt') == task for e in emissions for _, v in h.walk(e['value']))
            if producer['frozen_artifact_confirmation']:
                ref = producer['frozen_artifact_confirmation']
                assert h.pin(ref['path']) == ref
                actual = h.load(ref['path'])
                assert any(isinstance(v, dict) and v.get('prompt') == task for _, v in h.walk(actual))
                counters['actual_task_artifact_byte_and_prompt_checks'] += 1
            counters['exact_actual_task_emission_joins_rechecked'] += 1
            for proof in producer['earlier_protected_deliveries']:
                sid = proof['source_id']
                assert sid in original226 | newH
                assert proof['protected_set'] == ('original226' if sid in original226 else 'newH')
                counters['exact_original226_or_newH_membership_checks'] += 1
                prior_line = proof['native_event_line_1based']
                assert prior_line < line
                prior = lookup[prior_line]
                assert prior['role'] in {'tool', 'toolResult'}
                assert prior.get('toolCallId') == proof['tool_call_id']
                observation = h.text(prior)
                assert h.sha(observation) == proof['observation_sha256']
                if proof.get('proof_kind') == 'EXACT_PLAINTEXT_PRINTED_PROTECTED_USER_TITLE_PREFIX':
                    displayed = observation.splitlines()[proof['observation_text_line_1based'] - 1]
                    assert h.sha(displayed) == proof['observation_line_sha256']
                    match = re.fullmatch(r'===\s+(conv_[a-f0-9]{12})\s+\|\s+(.*?)\s+\|\s+[^|]+', displayed)
                    assert match and match[1] == proof['source_id']
                    assert h.sha(match[2]) == proof['title_sha256'] and len(match[2]) == proof['title_chars']
                    ref = proof['original_title_source']
                    assert h.pin(ref['path']) == ref
                    source = h.load(ref['path'])
                    assert source['title'][:60] == match[2]
                    assert any(source['title'] in v for m in source['messages'] if m.get('role') == 'user'
                               for _, v in h.walk(m.get('content', '')) if isinstance(v, str))
                    counters['actual_plaintext_private_title_prefix_checks'] += 1
                else:
                    chunks = dict(h.json_chunks(observation))
                    obj = chunks[proof['json_chunk_char_offset']]
                    value = next(v for pointer, v in h.walk(obj) if pointer == proof['json_pointer'])
                    assert value.get('source_id', value.get('session_id')) == proof['source_id']
                    texts = [r['text'] for key in ['requests', 'user_requests'] for r in value.get(key, [])
                             if isinstance(r, dict) and isinstance(r.get('text'), str) and r['text']]
                    texts.extend(v for m in value.get('messages', []) if isinstance(m, dict) and m.get('role') == 'user'
                                 for _, v in h.walk(m.get('content', '')) if isinstance(v, str) and v)
                    assert set(proof['direct_request_text_sha256']) <= {h.sha(t) for t in texts}
                    if proof['title_exactly_present_in_original_user_body']:
                        title = value['title']
                        assert h.sha(title) == proof['title_sha256'] and len(title) == proof['title_chars']
                        ref = proof['original_title_source']
                        assert h.pin(ref['path']) == ref
                        source = h.load(ref['path'])
                        assert title == source['title']
                        assert any(title in v for m in source['messages'] if m.get('role') == 'user'
                                   for _, v in h.walk(m.get('content', '')) if isinstance(v, str))
                    assert texts or proof['title_exactly_present_in_original_user_body']
                    counters['actual_JSON_private_request_or_title_checks'] += 1
                valid_protected_edges += 1
        expected = 'HOLD_CONFIRMED_PROTECTED_TASK_PRODUCER' if valid_protected_edges else 'HOLD_MISSING_TASK_PRODUCER_CLOSURE'
        assert episode['classification'] == expected
        for tid in episode['targets']:
            assert tid not in all_target_ids
            all_target_ids.add(tid)
            affected.append({'target_id': tid, 'episode_id': episode['episode_id'],
                'action': 'REVOKE_ANY_FUTURE_POSITIVE_LOSS' if valid_protected_edges else 'HOLD_NO_POSITIVE_LOSS',
                'reason': expected, 'all_original_messages_and_negative_records_preserved': True,
                'input_scope_begins_with_this_actual_derived_prompt': True,
                'loss_multiplier': 0, 'new_main_admitted': False})
    assert all_target_ids == set(report['selected_target_ids'])
    target_counts = Counter(r['reason'] for r in affected)
    assert dict(target_counts) == report['target_classifications']
    assert target_counts == {'HOLD_CONFIRMED_PROTECTED_TASK_PRODUCER': 34, 'HOLD_MISSING_TASK_PRODUCER_CLOSURE': 23}
    h.save(OUT / 'PRODUCER57_IMPACT_FINAL.json', {'schema': 'wrd-v10-57-business-write-loss-impact',
        'report': h.pin(REPORT), 'targets': affected, 'training_started': False,
        'old_v9_or_v10_frozen_files_modified': False, 'new_main_sequences': 0})
    h.save(OUT / 'PRODUCER57_INDEPENDENT_QA_FINAL.json', {'status': 'PASS_SCOPED_REAL_BYTES_AND_DELIVERED_PREFIX_CHECKS',
        'counters': dict(counters), 'targets': len(affected), 'target_classifications': dict(target_counts),
        'unique_native_capture_files_byte_checked': len(cache), 'new_main_admitted': 0,
        'new_model_calls': 0, 'new_program_executions': 0, 'training_started': False,
        'AI_curation_cost': 'UNKNOWN_NOT_ZERO', 'report': h.pin(REPORT),
        'original226_set_pins': protected_set_pins, 'newH_registry': h.pin(newH_path),
        'verifier': h.pin(Path(__file__)), 'raw_private_text_in_output': False})
    print(json.dumps({'status': 'PASS', 'targets': len(affected), 'target_counts': dict(target_counts),
                      'counters': dict(counters), 'native_files': len(cache)}))


if __name__ == '__main__':
    main()
