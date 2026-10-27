"""Quality pilot of eight real, formerly source-eligible Actor writes.

Resolve the actual task-prompt producer before assigning semantic credit or
running any program. Protected request/title bytes are used only to prove
exclusion; the report contains hashes and pointers, never protected text.
"""
from collections import Counter, defaultdict
import argparse
import importlib.util
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'output/20261027_wrd_main_v10/execution_rescue_01'
BUNDLE = ROOT / 'output/20261025_wrd_training_dataset/bundle'
PILOT = [
    '874f734c5198497a8a3cda31', '3eae9267e8fa6dd367e217e2',
    '4e819190cc4ca6bf54f21cfb', '0dd5502eec8fa8afa8343b48',
    'befe257a688eb74361966e52', '50a3b236baa2f7324e247fba',
    'c9753a249f6f08a9c7726efa', '36b278e3e411541fe6bffa61',
]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--all-source-eligible', action='store_true')
    parser.add_argument('--recover-legacy-producers', action='store_true')
    parser.add_argument('--plaintext-previews', action='store_true')
    parser.add_argument('--legacy-artifact-paths', action='store_true')
    args = parser.parse_args()
    spec = importlib.util.spec_from_file_location('ancestry_helpers',
        ROOT / 'research/data_prep/wrd_main_v10/audit_prepare_ancestry.py')
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    output = OUT / ('producer57_artifact_paths' if args.legacy_artifact_paths else 'producer57_full_views' if args.plaintext_previews else 'producer57_refined' if args.recover_legacy_producers else 'producer57') if args.all_source_eligible else OUT
    output.mkdir(parents=True, exist_ok=True)
    if (output / 'PRODUCER_AUDIT.json').exists():
        raise RuntimeError('Refuse to overwrite finished pilot')
    inventory_path = ROOT / 'output/20261027_wrd_main_v10/clean_prefix_rescue_01/BUSINESS_ACTOR_WRITE_INVENTORY.json'
    inventory = {r['id']: r for r in helper.load(inventory_path)['targets']}
    selected = sorted(r['id'] for r in inventory.values() if r['current_rescue_status'] == 'CLEAN_SOURCE_PREFIX_SEMANTICS_NOT_YET_CERTIFIED') if args.all_source_eligible else PILOT
    assert len(selected) == len(set(selected)) == (57 if args.all_source_eligible else 8)
    assert all(inventory[x]['current_rescue_status'] == 'CLEAN_SOURCE_PREFIX_SEMANTICS_NOT_YET_CERTIFIED' for x in selected)
    episodes = {r['episode_id']: r for r in helper.rows(BUNDLE / 'catalog/episodes.jsonl')}
    jobs = {r['id']: r for r in helper.rows(BUNDLE / 'catalog/jobs.jsonl')}
    files = {r['logical_path']: r for r in helper.rows(BUNDLE / 'archive/file_index.jsonl')}
    selected_eids = {inventory[x]['episode_id'] for x in selected}
    target_scopes = {(r['episode_id'], r['source_event_line']): r for r in helper.rows(
        ROOT / 'output/20261026_wrd_dataset_v9/outcomes/recomputed_scope_overlay/target_outcome_labels.jsonl.gz')}
    current_scopes = {r['source_id']: r for r in helper.rows(
        ROOT / 'output/20261027_wrd_main_v10/clean_inputs/source_scope.metadata.jsonl.gz')}
    original226 = set()
    for path in sorted((ROOT / 'benchmark').glob('*/contracts/evaluation.jsonl')):
        ids = {r.get('session_id') for r in helper.rows(path)} - {None}
        if len(ids) == 226:
            assert not original226 or ids == original226
            original226 = ids
    assert len(original226) == 226
    newH = set(helper.SID.findall(helper.canonical(helper.load(ROOT / 'output/20261026_ablation_v2/holdout_registry.json'))))
    protected = original226 | newH
    protected_titles = {}
    title_checks = []
    proof_inputs = [OUT / 'PRODUCER_AUDIT.json']
    if args.recover_legacy_producers:
        proof_inputs.append(OUT / 'producer57/PRODUCER_AUDIT.json')
    for pilot_path in proof_inputs:
      if args.all_source_eligible and pilot_path.is_file():
        for e in helper.load(pilot_path)['episodes']:
            for p in e['matched_producers']:
                for proof in p['earlier_protected_deliveries']:
                    if proof['title_exactly_present_in_original_user_body']:
                        protected_titles[proof['source_id']] = {
                            'title_sha256': proof['title_sha256'], 'title_chars': proof['title_chars'],
                            'source': proof['original_title_source'], 'basis': 'REUSED_FROZEN_PILOT_EXACT_MATCH_PROOF'}

    def title_proof(sid, observed_title):
        if not isinstance(observed_title, str) or len(observed_title) < 8:
            return None
        known = protected_titles.get(sid)
        if known is not None:
            return known if known['title_sha256'] == helper.sha(observed_title) else None
        path = ROOT / 'output/20261021_workflow_skill_library/sources' / sid / 'conversation.json'
        if not path.is_file():
            return None
        source = helper.load(path)
        title = source.get('title', '')
        if title != observed_title:
            return None
        bodies = [value for m in source.get('messages', []) if m.get('role') == 'user'
                  for _, value in helper.walk(m.get('content', '')) if isinstance(value, str)]
        if any(title in value for value in bodies):
            result = {'title_sha256': helper.sha(title), 'title_chars': len(title),
                      'source': helper.pin(path), 'basis': 'EXACT_OBSERVED_TITLE_EQUALS_SOURCE_TITLE_AND_SUBSTRING_OF_ORIGINAL_USER_BODY'}
            protected_titles[sid] = result
            title_checks.append({'source_id': sid, **result, 'raw_text_not_serialized': True})
            return result
        return None

    plaintext_title_cache = {}

    def plaintext_title_proof(sid, observed):
        key = (sid, helper.sha(observed))
        if key in plaintext_title_cache:
            return plaintext_title_cache[key]
        if len(observed) < 8:
            return None
        path = ROOT / 'output/20261021_workflow_skill_library/sources' / sid / 'conversation.json'
        if not path.is_file():
            return None
        source = helper.load(path)
        original_title = source.get('title', '')
        if not isinstance(original_title, str) or original_title[:60] != observed:
            plaintext_title_cache[key] = None
            return None
        bodies = [value for m in source.get('messages', []) if m.get('role') == 'user'
                  for _, value in helper.walk(m.get('content', '')) if isinstance(value, str)]
        if not any(original_title in body for body in bodies):
            plaintext_title_cache[key] = None
            return None
        result = {'source': helper.pin(path), 'original_title_sha256': helper.sha(original_title),
                  'observed_title_prefix_sha256': helper.sha(observed), 'observed_prefix_chars': len(observed),
                  'original_title_is_exact_substring_of_original_user_body': True,
                  'observed_matches_exact_first60_original_title_chars': True,
                  'raw_text_not_serialized': True}
        plaintext_title_cache[key] = result
        title_checks.append({'source_id': sid, **result, 'basis': 'ACTUAL_PLAINTEXT_PRINTED_PRIVATE_USER_TITLE_PREFIX'})
        return result
    event_cache = {}
    results = []

    def archived(eid, relative):
        ref = files.get('episodes/' + eid + '/' + relative)
        if not ref:
            return None
        path = BUNDLE / 'archive' / ref['object']
        assert helper.pin(path)['sha256'] == ref['sha256']
        return path

    for eid in sorted(selected_eids):
        episode = episodes[eid]
        job = jobs.get(episode.get('job_id'), {})
        case = (job.get('payload') or {}).get('case') or {}
        request_path = archived(eid, 'request.json')
        native_path = archived(eid, 'openclaw_transport/session_events.jsonl')
        result = {'episode_id': eid, 'targets': [x for x in selected if inventory[x]['episode_id'] == eid],
            'kind': episode.get('kind'), 'route_id': episode.get('route_id'),
            'source_ids_from_actual_old_prefix': sorted({s for x in selected if inventory[x]['episode_id'] == eid for s in inventory[x]['source_ids']}),
            'source_status_before_producer_audit': 'TRAIN_SOURCE_ELIGIBLE_NOT_QUALITY_ADMITTED',
            'classification': 'HOLD_MISSING_TASK_PRODUCER_CLOSURE',
            'new_positive_loss_tokens': 0, 'matched_producers': [], 'unknowns': []}
        if not request_path or not native_path:
            result['unknowns'].append('ORIGINAL_ACTOR_REQUEST_OR_NATIVE_CAPTURE_NOT_FOUND')
            results.append(result)
            continue
        request = helper.load(request_path)
        task = request.get('input')
        result['actor_request'] = helper.pin(request_path)
        result['actor_native_events'] = helper.pin(native_path)
        if not isinstance(task, str):
            result['unknowns'].append('ORIGINAL_REQUEST_INPUT_NOT_A_TEXT_FIELD')
            results.append(result)
            continue
        result['task_input_sha256'] = helper.sha(task)
        deliveries = [{'native_event_line_1based': line,
                       'actual_user_text_sha256': helper.sha(helper.text(msg))}
                      for line, msg in helper.events(native_path)
                      if msg.get('role') == 'user' and task in helper.text(msg)]
        result['actual_native_task_deliveries'] = deliveries
        assert deliveries
        candidates = []
        if case.get('_prepared_episode'):
            candidates.append((Path(case['_prepared_episode']), None))
        for other_eid, ep in episodes.items():
            if ep.get('kind') == 'prepare' and ep.get('route_id') == episode.get('route_id'):
                p = Path(ep['source_path'])
                if not any(p == path for path, _ in candidates):
                    candidates.append((p, other_eid))
        if args.recover_legacy_producers:
            normalized_route = re.sub(r'_c\d+_(?:no_skill|workflow|blindjudge)$', '', episode.get('route_id') or '')
            for other_eid, ep in episodes.items():
                tail = Path(ep['source_path']).name
                if tail == normalized_route + '_devprep' or ep.get('route_id') == normalized_route + '_devprep':
                    p = Path(ep['source_path'])
                    if not any(p == path for path, _ in candidates):
                        candidates.append((p, other_eid))
        for directory, producer_eid in candidates:
            path = directory / 'openclaw_transport/session_events.jsonl'
            if not path.is_file() and producer_eid:
                path = archived(producer_eid, 'openclaw_transport/session_events.jsonl')
            if not path or not path.is_file():
                continue
            key = str(path)
            if key not in event_cache:
                event_cache[key] = helper.events(path)
            messages = event_cache[key]
            for index, (line, msg) in enumerate(messages):
                if msg.get('role') != 'assistant':
                    continue
                for call in helper.calls(msg):
                    for emission in helper.emitted_json(call):
                        matches = [{'pointer': pointer, 'case_id': value.get('id')}
                                   for pointer, value in helper.walk(emission['value'])
                                   if isinstance(value, dict) and value.get('prompt') == task]
                        if not matches:
                            continue
                        confirmation = None
                        if emission.get('requires_output_artifact_confirmation'):
                            artifact = directory / 'workspace/outputs/tasks.json'
                            if args.legacy_artifact_paths and not artifact.is_file():
                                call_args = call.get('arguments', {})
                                call_args = json.loads(call_args) if isinstance(call_args, str) else call_args
                                cmd = call_args.get('command', '') if isinstance(call_args, dict) else ''
                                legacy_artifact = directory / 'workspace/outputs/development_tasks.json'
                                if 'development_tasks.json' in cmd and legacy_artifact.is_file():
                                    artifact = legacy_artifact
                            if not artifact.is_file():
                                continue
                            actual = helper.load(artifact)
                            if not any(isinstance(v, dict) and v.get('prompt') == task for _, v in helper.walk(actual)):
                                continue
                            confirmation = helper.pin(artifact)
                        proofs = []
                        prior_calls = {c.get('id'): c for _, item in messages[:index] for c in helper.calls(item)}
                        for prior_line, prior in messages[:index]:
                            if prior.get('role') not in {'tool', 'toolResult'}:
                                continue
                            observation = helper.text(prior)
                            if args.plaintext_previews:
                                prior_call = prior_calls.get(prior.get('toolCallId'), {})
                                prior_args = prior_call.get('arguments', {})
                                prior_args = json.loads(prior_args) if isinstance(prior_args, str) else prior_args
                                command = prior_args.get('command', '') if isinstance(prior_args, dict) else ''
                                if prior_call.get('name') == 'exec' and 'title' in command and 'source_id' in command:
                                    for observation_line, displayed in enumerate(observation.splitlines(), 1):
                                        match = re.fullmatch(r'===\s+(conv_[a-f0-9]{12})\s+\|\s+(.*?)\s+\|\s+[^|]+', displayed)
                                        if not match or match[1] not in protected:
                                            continue
                                        private_preview = plaintext_title_proof(match[1], match[2])
                                        if private_preview is None:
                                            continue
                                        proofs.append({'source_id': match[1], 'protected_set': 'original226' if match[1] in original226 else 'newH',
                                            'native_event_line_1based': prior_line, 'tool_call_id': prior.get('toolCallId'),
                                            'observation_sha256': helper.sha(observation), 'observation_text_line_1based': observation_line,
                                            'observation_line_sha256': helper.sha(displayed), 'exec_command_sha256': helper.sha(command),
                                            'proof_kind': 'EXACT_PLAINTEXT_PRINTED_PROTECTED_USER_TITLE_PREFIX',
                                            'title_exactly_present_in_original_user_body': True,
                                            'title_sha256': private_preview['observed_title_prefix_sha256'],
                                            'title_chars': private_preview['observed_prefix_chars'],
                                            'original_title_source': private_preview['source'],
                                            'original_title_sha256': private_preview['original_title_sha256'],
                                            'preview_is_full_title': private_preview['observed_prefix_chars'] < 60,
                                            'raw_text_not_serialized': True})
                            for offset, obj in helper.json_chunks(observation):
                                for pointer, value in helper.walk(obj):
                                    if not isinstance(value, dict) or value.get('source_id', value.get('session_id')) not in protected:
                                        continue
                                    sid = value.get('source_id', value.get('session_id'))
                                    direct = [r for r in value.get('requests', []) if isinstance(r, dict) and isinstance(r.get('text'), str) and r['text']]
                                    if args.recover_legacy_producers:
                                        direct.extend(r for r in value.get('user_requests', []) if isinstance(r, dict) and isinstance(r.get('text'), str) and r['text'])
                                        for source_m in value.get('messages', []) if isinstance(value.get('messages'), list) else []:
                                            if isinstance(source_m, dict) and source_m.get('role') == 'user':
                                                direct.extend({'text': text} for _, text in helper.walk(source_m.get('content', '')) if isinstance(text, str) and text)
                                    title = title_proof(sid, value.get('title'))
                                    title_ok = title is not None
                                    if not direct and not title_ok:
                                        continue
                                    proofs.append({'source_id': sid, 'protected_set': 'original226' if sid in original226 else 'newH',
                                        'native_event_line_1based': prior_line, 'tool_call_id': prior.get('toolCallId'),
                                        'observation_sha256': helper.sha(observation), 'json_chunk_char_offset': offset,
                                        'json_pointer': pointer,
                                        'direct_request_text_sha256': [helper.sha(r['text']) for r in direct],
                                        'title_exactly_present_in_original_user_body': title_ok,
                                        'title_sha256': title['title_sha256'] if title_ok else None,
                                        'title_chars': title['title_chars'] if title_ok else 0,
                                        'original_title_source': title['source'] if title_ok else None})
                        actual_producer_eid = producer_eid
                        if actual_producer_eid is None:
                            matching_eids = [k for k, e in episodes.items() if Path(e['source_path']) == directory]
                            if len(matching_eids) == 1:
                                actual_producer_eid = matching_eids[0]
                        producer_scope = target_scopes.get((actual_producer_eid, line))
                        scope_receipt = None
                        if producer_scope:
                            scope_receipt = {k: producer_scope.get(k) for k in ['id', 'episode_id', 'source_event_line',
                                'source_message_index', 'source_admission', 'scope_status', 'source_ids_visible_prefix',
                                'protected_sources_visible_prefix', 'unknown_reasons', 'scope_proof_id']}
                            scope_receipt['current_source_statuses'] = {
                                sid: current_scopes.get(sid, {}).get('status', 'UNKNOWN')
                                for sid in producer_scope['source_ids_visible_prefix']}
                        result['matched_producers'].append({'producer_episode_id': actual_producer_eid,
                            'producer_events': helper.pin(path), 'task_emission_native_line_1based': line,
                            'task_emission_call_id': call.get('id'), 'operation': emission['kind'],
                            'actual_source_command_sha256': emission.get('actual_source_command_sha256'),
                            'emission_content_sha256': helper.sha(emission['content']),
                            'artifact_path_correction_only': str(artifact.relative_to(directory)).replace('\\', '/') if confirmation else None,
                            'original_producer_scope_receipt': scope_receipt,
                            'exact_matching_task_fields': matches, 'frozen_artifact_confirmation': confirmation,
                            'earlier_protected_deliveries': proofs})
        if any(p['earlier_protected_deliveries'] for p in result['matched_producers']):
            result['classification'] = 'HOLD_CONFIRMED_PROTECTED_TASK_PRODUCER'
        elif result['matched_producers']:
            result['unknowns'].append('TASK_JOIN_PROVEN_BUT_ROUTE_AND_ALL_RESOURCE_PRODUCERS_NOT_YET_CLOSED')
        else:
            result['unknowns'].append('NO_EXACT_TASK_PROMPT_EMISSION_TO_ACTOR_JOIN_FOUND')
        results.append(result)
    report = {'schema': 'wrd-v10-execution-write-producer-audit-57' if args.all_source_eligible else 'wrd-v10-eight-execution-write-pilot-producer-audit',
        'status': 'ACTUAL_PRODUCER_AUDIT_COMPLETE_NO_BLANKET_QUALITY_ADMISSION',
        'selected_target_ids': selected, 'selected_targets': len(selected), 'selected_episodes': len(results),
        'episode_classifications': dict(Counter(r['classification'] for r in results)),
        'target_classifications': dict(Counter({key: sum(len(r['targets']) for r in results if r['classification'] == key)
                                               for key in {r['classification'] for r in results}})),
        'episodes': results, 'new_execution_main_sequences': 0, 'new_positive_loss_tokens': 0,
        'protected_content_bodies_in_report': False, 'new_model_calls': 0,
        'new_program_executions': 0, 'training_started': False,
        'AI_review_cost': 'UNKNOWN_NOT_ZERO', 'script': helper.pin(Path(__file__)),
        'source_inventory': helper.pin(inventory_path),
        'new_minimal_title_source_checks': len(title_checks),
        'legacy_producer_and_record_schema_recovery_enabled': args.recover_legacy_producers,
        'plaintext_exact_title_prefix_recovery_enabled': args.plaintext_previews,
        'legacy_development_tasks_artifact_path_recovery_enabled': args.legacy_artifact_paths,
        'scope': 'All 57 formerly train-source-eligible writes; no old protected or static-dev/test write is promoted.' if args.all_source_eligible else 'Only the specified eight substantive targets; not an assertion about the other 49 write targets.'}
    helper.save(output / 'PROTECTED_TITLE_MATCH_PROOFS.json', {'checks': title_checks, 'raw_text_included': False})
    helper.save(output / 'PRODUCER_AUDIT.json', report)
    print(json.dumps({k: report[k] for k in ['selected_targets', 'selected_episodes', 'episode_classifications', 'target_classifications', 'new_execution_main_sequences']}))


if __name__ == '__main__':
    main()
