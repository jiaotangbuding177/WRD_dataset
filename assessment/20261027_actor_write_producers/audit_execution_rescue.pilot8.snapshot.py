"""Quality pilot of eight real, formerly source-eligible Actor writes.

Resolve the actual task-prompt producer before assigning semantic credit or
running any program. Protected request/title bytes are used only to prove
exclusion; the report contains hashes and pointers, never protected text.
"""
from collections import Counter, defaultdict
import importlib.util
import json
from pathlib import Path

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
    spec = importlib.util.spec_from_file_location('ancestry_helpers',
        ROOT / 'research/data_prep/wrd_main_v10/audit_prepare_ancestry.py')
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    OUT.mkdir(parents=True, exist_ok=True)
    if (OUT / 'PRODUCER_AUDIT.json').exists():
        raise RuntimeError('Refuse to overwrite finished pilot')
    inventory_path = ROOT / 'output/20261027_wrd_main_v10/clean_prefix_rescue_01/BUSINESS_ACTOR_WRITE_INVENTORY.json'
    inventory = {r['id']: r for r in helper.load(inventory_path)['targets']}
    assert len(PILOT) == len(set(PILOT)) == 8
    assert all(inventory[x]['current_rescue_status'] == 'CLEAN_SOURCE_PREFIX_SEMANTICS_NOT_YET_CERTIFIED' for x in PILOT)
    episodes = {r['episode_id']: r for r in helper.rows(BUNDLE / 'catalog/episodes.jsonl')}
    jobs = {r['id']: r for r in helper.rows(BUNDLE / 'catalog/jobs.jsonl')}
    files = {r['logical_path']: r for r in helper.rows(BUNDLE / 'archive/file_index.jsonl')}
    selected_eids = {inventory[x]['episode_id'] for x in PILOT}
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
    for sid in protected:
        path = ROOT / 'output/20261021_workflow_skill_library/sources' / sid / 'conversation.json'
        if not path.is_file():
            continue
        source = helper.load(path)
        title = source.get('title', '')
        if not isinstance(title, str) or len(title) < 8:
            continue
        bodies = [value for m in source.get('messages', []) if m.get('role') == 'user'
                  for _, value in helper.walk(m.get('content', '')) if isinstance(value, str)]
        if any(title in value for value in bodies):
            protected_titles[sid] = {'title': title, 'source': helper.pin(path)}
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
        result = {'episode_id': eid, 'targets': [x for x in PILOT if inventory[x]['episode_id'] == eid],
            'kind': episode.get('kind'), 'route_id': episode.get('route_id'),
            'source_ids_from_actual_old_prefix': sorted({s for x in PILOT if inventory[x]['episode_id'] == eid for s in inventory[x]['source_ids']}),
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
                            if not artifact.is_file():
                                continue
                            actual = helper.load(artifact)
                            if not any(isinstance(v, dict) and v.get('prompt') == task for _, v in helper.walk(actual)):
                                continue
                            confirmation = helper.pin(artifact)
                        proofs = []
                        for prior_line, prior in messages[:index]:
                            if prior.get('role') not in {'tool', 'toolResult'}:
                                continue
                            observation = helper.text(prior)
                            for offset, obj in helper.json_chunks(observation):
                                for pointer, value in helper.walk(obj):
                                    if not isinstance(value, dict) or value.get('source_id') not in protected:
                                        continue
                                    sid = value['source_id']
                                    direct = [r for r in value.get('requests', []) if isinstance(r, dict) and isinstance(r.get('text'), str) and r['text']]
                                    title = protected_titles.get(sid)
                                    title_ok = title is not None and value.get('title') == title['title']
                                    if not direct and not title_ok:
                                        continue
                                    proofs.append({'source_id': sid, 'protected_set': 'original226' if sid in original226 else 'newH',
                                        'native_event_line_1based': prior_line, 'tool_call_id': prior.get('toolCallId'),
                                        'observation_sha256': helper.sha(observation), 'json_chunk_char_offset': offset,
                                        'json_pointer': pointer,
                                        'direct_request_text_sha256': [helper.sha(r['text']) for r in direct],
                                        'title_exactly_present_in_original_user_body': title_ok,
                                        'title_sha256': helper.sha(title['title']) if title_ok else None,
                                        'title_chars': len(title['title']) if title_ok else 0,
                                        'original_title_source': title['source'] if title_ok else None})
                        result['matched_producers'].append({'producer_episode_id': producer_eid,
                            'producer_events': helper.pin(path), 'task_emission_native_line_1based': line,
                            'task_emission_call_id': call.get('id'), 'operation': emission['kind'],
                            'actual_source_command_sha256': emission.get('actual_source_command_sha256'),
                            'emission_content_sha256': helper.sha(emission['content']),
                            'exact_matching_task_fields': matches, 'frozen_artifact_confirmation': confirmation,
                            'earlier_protected_deliveries': proofs})
        if any(p['earlier_protected_deliveries'] for p in result['matched_producers']):
            result['classification'] = 'HOLD_CONFIRMED_PROTECTED_TASK_PRODUCER'
        elif result['matched_producers']:
            result['unknowns'].append('TASK_JOIN_PROVEN_BUT_ROUTE_AND_ALL_RESOURCE_PRODUCERS_NOT_YET_CLOSED')
        else:
            result['unknowns'].append('NO_EXACT_TASK_PROMPT_EMISSION_TO_ACTOR_JOIN_FOUND')
        results.append(result)
    report = {'schema': 'wrd-v10-eight-execution-write-pilot-producer-audit',
        'status': 'ACTUAL_PRODUCER_AUDIT_COMPLETE_NO_BLANKET_QUALITY_ADMISSION',
        'selected_target_ids': PILOT, 'selected_targets': 8, 'selected_episodes': len(results),
        'episode_classifications': dict(Counter(r['classification'] for r in results)),
        'target_classifications': dict(Counter({key: sum(len(r['targets']) for r in results if r['classification'] == key)
                                               for key in {r['classification'] for r in results}})),
        'episodes': results, 'new_execution_main_sequences': 0, 'new_positive_loss_tokens': 0,
        'protected_content_bodies_in_report': False, 'new_model_calls': 0,
        'new_program_executions': 0, 'training_started': False,
        'AI_review_cost': 'UNKNOWN_NOT_ZERO', 'script': helper.pin(Path(__file__)),
        'source_inventory': helper.pin(inventory_path),
        'scope': 'Only the specified eight substantive targets; not an assertion about the other 49 write targets.'}
    helper.save(OUT / 'PRODUCER_AUDIT.json', report)
    print(json.dumps({k: report[k] for k in ['selected_targets', 'selected_episodes', 'episode_classifications', 'target_classifications', 'new_execution_main_sequences']}))


if __name__ == '__main__':
    main()
