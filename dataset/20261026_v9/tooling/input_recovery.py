"""Recover actual native histories and same-identity API captures for v9.

This is offline data processing, not an Agent loop. Captured inputs and native
factory schema reconstruction are deliberately distinct. No model is invoked.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timezone
import argparse
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'output/20261026_wrd_dataset_v9/recovery'
V8 = ROOT / 'output/20261026_wrd_quality_v8'
BUNDLE = ROOT / 'output/20261025_wrd_training_dataset/bundle'
V7 = ROOT / 'output/20261026_wrd_raw_census_v7'
IMAGE = 'sha256:97a0f55bec1ef293c15ddd5a17cc843050387bd2369dcf2fd388b1afd40810a2'
FACTORY = ROOT / 'research/data_prep/wrd_training/resources/native_coding_tools_97a0.json'
PROVENANCE = FACTORY.with_suffix('.provenance.json')

spec = importlib.util.spec_from_file_location('v8_raw_recovery', ROOT / 'research/data_prep/wrd_quality_v8/raw_recoverability.py')
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def js(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def rows(path):
    with gzip.open(path, 'rt', encoding='utf-8-sig') as handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)


def load(path, default=None):
    try:
        data = Path(path).read_bytes()
        if str(path).endswith('.gz'):
            data = gzip.decompress(data)
        return json.loads(data.decode('utf-8-sig'))
    except (OSError, ValueError, UnicodeError):
        return default


def pin(path):
    p = Path(path)
    data = p.read_bytes()
    return {'path': str(p), 'bytes': len(data), 'sha256': sha(data)}


def trunc(value):
    if isinstance(value, dict):
        if value.get('truncated') is True:
            return True
        if any(trunc(child) for child in value.values() if isinstance(child, (dict, list))):
            return True
    if isinstance(value, list) and any(trunc(child) for child in value if isinstance(child, (dict, list))):
        return True
    text = js(value)
    return any(marker in text for marker in ['<truncated>', '[Truncated]', '[truncated]', 'Malformed diagnostic JSON redacted'])


def schema_list(value):
    tools = value.get('tools', []) if isinstance(value, dict) else value if isinstance(value, list) else []
    good, bad = [], []
    for entry in tools:
        fn = entry.get('function', entry) if isinstance(entry, dict) else None
        if isinstance(fn, dict) and isinstance(fn.get('name'), str) and isinstance(fn.get('parameters', fn.get('input_schema')), dict) and not trunc(fn):
            good.append({'name': fn['name'], 'description': fn.get('description', ''), 'parameters': fn.get('parameters', fn.get('input_schema'))})
        else:
            bad.append(entry.get('name') if isinstance(entry, dict) else 'NON_DICT_PLACEHOLDER')
    return good, bad


def extract_event(path):
    data = Path(path).read_bytes()
    messages, line_numbers, sid, issues = [], [], None, []
    if str(path).endswith('.gz'):
        data = gzip.decompress(data)
    for number, line in enumerate(data.decode('utf-8-sig').split('\n'), 1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except ValueError:
            issues.append(number)
            continue
        if value.get('type') == 'session' and not sid:
            sid = value.get('id')
        if value.get('type') == 'message' and isinstance(value.get('message'), dict):
            messages.append(value['message'])
            line_numbers.append(number)
    return sid, messages, line_numbers, issues


def source_file(meta, suffix):
    for item in meta.get('key_recording_files', []):
        if item['logical_path'].endswith(suffix):
            p = Path(item['physical_frozen_CAS_path'])
            if p.is_file():
                assert sha(p.read_bytes()) == item['stored_sha256']
                return p
    candidate = Path(meta.get('source_path', '')) / suffix.lstrip('/')
    return candidate if candidate.is_file() else None


def native_context(meta, event_path, canonical=None):
    sid, messages, event_lines, issues = extract_event(event_path)
    episode_id = canonical['episode_id'] if canonical else 'native_' + sid
    api = []
    episode_dir = Path(meta.get('source_path', '')).parent.parent if canonical is None else Path(meta['source_path'])
    for path in sorted((episode_dir / 'openclaw_transport/api_audit').glob('*/native_request.raw.json')):
        req = helper.unwrap_request(load(path))
        if req is None:
            continue
        sys_messages = [m for m in req['messages'] if m.get('role') == 'system']
        schema, bad = schema_list(req)
        api.append({'source': pin(path), 'system_messages': sys_messages, 'tools': schema,
                    'tool_schema_incomplete_entries': bad, 'request_messages_sha256': sha(js(req['messages']).encode()),
                    'system_capture_complete': bool(sys_messages) and not trunc(sys_messages),
                    'request_message_count': len(req['messages']), 'tools_original': req.get('tools', [])})
    system_candidates = []
    for item in api:
        system_candidates.append({'status': 'ORIGINAL_SAME_EPISODE_API', 'source': item['source'],
                                  'messages': item['system_messages'], 'complete': item['system_capture_complete']})
    if canonical:
        sys_path = source_file(meta, '/openclaw_transport/evidence/system-prompt.txt')
        if sys_path:
            text = sys_path.read_text(encoding='utf-8-sig')
            system_candidates.append({'status': 'ORIGINAL_EPISODE_CAPTURE', 'source': pin(sys_path),
                                      'messages': [{'role': 'system', 'content': text}], 'complete': bool(text.strip()) and not trunc(text)})
        tools_path = source_file(meta, '/openclaw_transport/evidence/tools.json')
        exec_path = source_file(meta, '/execution.json')
    else:
        sys_path = episode_dir / 'openclaw_transport/evidence/system-prompt.txt'
        if sys_path.is_file():
            text = sys_path.read_text(encoding='utf-8-sig')
            system_candidates.append({'status': 'ORIGINAL_EPISODE_CAPTURE', 'source': pin(sys_path),
                                      'messages': [{'role': 'system', 'content': text}], 'complete': bool(text.strip()) and not trunc(text)})
        tools_path = episode_dir / 'openclaw_transport/evidence/tools.json'
        exec_path = episode_dir / 'execution.json'
    tools_value = load(tools_path, []) if tools_path else []
    original_tools, bad_tools = schema_list(tools_value)
    original_source = pin(tools_path) if tools_path and tools_path.is_file() else None
    tools_by_name = {x['name']: {'tool': x, 'kind': 'ORIGINAL_EPISODE_CAPTURE', 'source': original_source} for x in original_tools}
    for item in api:
        for tool in item['tools']:
            tools_by_name[tool['name']] = {'tool': tool, 'kind': 'ORIGINAL_SAME_EPISODE_API', 'source': item['source']}
    execution = load(exec_path, {}) if exec_path else {}
    factory_allowed = execution.get('image') == IMAGE
    if factory_allowed:
        for tool in load(FACTORY):
            if tool['name'] not in tools_by_name:
                tools_by_name[tool['name']] = {'tool': tool, 'kind': 'RECONSTRUCTED_PINNED_NATIVE_FACTORY_NOT_ORIGINAL_CAPTURE', 'source': pin(FACTORY), 'provenance_source': pin(PROVENANCE)}
    called = sorted({b.get('name') for m in messages if isinstance(m.get('content'), list) for b in m['content'] if isinstance(b, dict) and b.get('type') == 'toolCall' and b.get('name')})
    complete_sys = next((x for x in system_candidates if x['complete']), None)
    best_sys = complete_sys or next(iter(system_candidates), None)
    readable = []
    for i, message in enumerate(messages):
        if message.get('role') != 'assistant':
            continue
        for field, value in helper.nonempty_reasoning(message):
            readable.append({'message_index': i, 'source_event_line_1based': event_lines[i], 'response_id': message.get('responseId'), 'field': field, 'text': value, 'text_sha256': sha(value.encode()), 'provenance': 'ORIGINAL_NATIVE_MESSAGE'})
    return {
        'schema_version': 'wrd-v9-native-input-recovery-1.0', 'episode_id': episode_id,
        'old_canonical_episode_id': canonical['episode_id'] if canonical else None, 'native_session_id': sid,
        'source_native': pin(event_path), 'source_original_path': str(meta.get('raw_native_session', {}).get('event_file', meta.get('source_path'))),
        'messages': messages, 'source_event_lines': event_lines, 'messages_original_unmodified': True,
        'parse_error_line_numbers': issues, 'stage': canonical.get('kind') if canonical else meta.get('recorded_stage'),
        'route_id': canonical.get('route_id') if canonical else None,
        'old_episode_source_ids_metadata': canonical.get('source_ids', []) if canonical else [],
        'old_native_verified_metadata': canonical.get('native_verified') if canonical else None,
        'execution_condition': {k: execution.get(k) for k in ['image', 'openclaw_version', 'model', 'backend', 'custom_agent_loop'] if k in execution},
        'system_capture_status': 'ORIGINAL_COMPLETE' if complete_sys else 'ORIGINAL_CAPTURE_INCOMPLETE' if best_sys else 'MISSING_ORIGINAL_CAPTURE',
        'system_messages_original': complete_sys['messages'] if complete_sys else [],
        'system_capture_candidates': system_candidates,
        'tools_supported': [tools_by_name[name]['tool'] for name in sorted(tools_by_name)],
        'tool_schema_provenance': [{'name': name, **{k: v for k, v in tools_by_name[name].items() if k != 'tool'}} for name in sorted(tools_by_name)],
        'original_tool_schema_incomplete_entries': bad_tools, 'called_tool_names': called,
        'called_tools_missing_supported_schema': sorted(set(called) - set(tools_by_name)),
        'pinned_factory_schema_reconstruction_allowed': factory_allowed,
        'same_episode_API_capture_count': len(api),
        'api_request_captures': [{'source': x['source'], 'request_messages_sha256': x['request_messages_sha256'], 'request_message_count': x['request_message_count']} for x in api],
        'readable_reasoning_original_native': readable,
        'reasoning_overlays_same_response_id': [],
        'source_admission': 'NOT_PERFORMED_HERE_PROTECTED_AND_UNKNOWN_REMAIN_FOR_PARENT_REVIEW',
        'training_admitted_by_this_recovery': False,
    }


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    old = {x['episode_id']: x for x in rows(BUNDLE / 'canonical/native_episodes.jsonl.gz')}
    old_meta = {x['episode_id']: x for x in rows(V7 / 'indexes/episodes.all.jsonl.gz') if x['episode_id'] in old}
    supplemental = defaultdict(list)
    for item in rows(V8 / 'controlled/native_sessions.metadata.jsonl.gz'):
        if item.get('native_session_id'):
            supplemental[item['native_session_id']].append(item)
    supplemental = [max(group, key=lambda x: (x['messages'], bool(x['same_episode_original_API_contexts']), x['bytes'])) for group in supplemental.values()]
    response_map = {}
    pair_stats = Counter()
    with gzip.open(OUT / 'provider_pairs.original.jsonl.gz', 'wt', encoding='utf-8', compresslevel=3) as output:
        for item in rows(V8 / 'controlled/provider_responses.metadata.jsonl.gz'):
            variants = []
            for path in item['source_response_paths']:
                p = Path(path)
                raw = p.read_bytes()
                text = (gzip.decompress(raw) if p.suffix == '.gz' else raw).decode('utf-8-sig')
                try:
                    value = json.loads(text)
                except ValueError:
                    value = None
                resp = value if isinstance(value, dict) and isinstance(value.get('choices'), list) else helper.sse_response(text)
                if resp is not None and resp.get('choices'):
                    variants.append((resp, pin(p)))
            assert variants, item['provider_response_id']
            resp, source = max(variants, key=lambda pair: sum(len(v) for _, v in helper.nonempty_reasoning(pair[0]['choices'][0].get('message', {}))))
            rid = resp.get('id')
            assert rid == item['provider_response_id']
            request_variants = []
            for path in item['source_request_paths']:
                req = helper.unwrap_request(load(path))
                if req is not None:
                    request_variants.append({'source': pin(path), 'messages': req['messages'], 'tools': req.get('tools', []),
                                             'model_parameters': {k: req.get(k) for k in ['model', 'stream', 'thinking', 'reasoning_effort'] if k in req}})
            assert request_variants
            message = resp['choices'][0].get('message', {})
            row = {'schema_version': 'wrd-v9-original-provider-pair-1.0', 'provider_response_id': rid,
                   'provider_model': resp.get('model'), 'response': message,
                   'response_finish_reason': resp['choices'][0].get('finish_reason'), 'response_source': source,
                   'response_message_sha256': sha(js(message).encode()), 'request_variants': request_variants,
                   'prior_role_label': item['prior_v4_role_label'],
                   'historical_execution_condition': item['prior_recorded_historical_execution_condition'],
                   'native_equivalence_not_assumed': True,
                   'training_admitted_by_this_recovery': False}
            response_map[rid] = row
            output.write(json.dumps(row, ensure_ascii=False) + '\n')
            pair_stats['provider_pairs'] += 1
            pair_stats['pairs_with_readable_reasoning_field'] += bool(helper.nonempty_reasoning(message))
    counts, missing = Counter(), []
    with gzip.open(OUT / 'episodes.contexts.jsonl.gz', 'wt', encoding='utf-8', compresslevel=3) as output, gzip.open(OUT / 'episodes.metadata.jsonl.gz', 'wt', encoding='utf-8', compresslevel=3) as metadata:
        for ordinal, (key, episode) in enumerate(old.items(), 1):
            meta = old_meta[key]
            p = Path(meta['raw_native_session']['CAS_path'])
            assert sha(p.read_bytes()) == meta['raw_native_session']['sha256']
            row = native_context(meta, p, episode)
            emit(row, output, metadata, response_map, counts)
            if ordinal % 200 == 0:
                print('OLD_EPISODES_RECOVERED', ordinal, len(old), flush=True)
        for item in supplemental:
            p = Path(item['source_path'])
            assert sha(p.read_bytes()) == item['source_sha256']
            row = native_context(item, p)
            emit(row, output, metadata, response_map, counts)
    files = [pin(OUT / name) for name in ['episodes.contexts.jsonl.gz', 'episodes.metadata.jsonl.gz', 'provider_pairs.original.jsonl.gz']]
    report = {'schema_version': 'wrd-v9-input-recovery-report-1.0', 'created_at_utc': datetime.now(timezone.utc).isoformat(),
              'old_episode_count': len(old), 'supplemental_native_identity_count': len(supplemental), 'counts': dict(counts),
              'provider_counts': dict(pair_stats), 'files': files,
              'raw_messages_are_original_not_reconstructed': True,
              'incomplete_system_not_replaced_by_other_session': True,
              'factory_schema_is_explicit_reconstruction_not_original_capture': True,
              'reasoning_progress_field_ambiguity_preserved': True,
              'encrypted_reasoning_not_fabricated_or_decrypted': True,
              'source_admission_and_positive_loss_not_performed_here': True,
              'training_started': False, 'model_requests': 0}
    (OUT / 'REPORT.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'report': str(OUT / 'REPORT.json'), 'counts': dict(counts), 'provider_counts': dict(pair_stats)}, ensure_ascii=False), flush=True)


def emit(row, output, metadata, response_map, counts):
    for index, message in enumerate(row['messages']):
        if message.get('role') != 'assistant':
            continue
        rid = message.get('responseId')
        if rid not in response_map:
            continue
        pair = response_map[rid]
        for field, text in helper.nonempty_reasoning(pair['response']):
            row['reasoning_overlays_same_response_id'].append({'message_index': index, 'source_event_line_1based': row['source_event_lines'][index],
                'response_id': rid, 'field': field, 'text': text, 'text_sha256': sha(text.encode()),
                'source': pair['response_source'], 'provenance': 'ORIGINAL_PROVIDER_RESPONSE_ID_EXACT_MATCH',
                'meaning': 'READABLE_REASONING_FIELD_MAY_INCLUDE_RUNTIME_PROGRESS_NOT_CERTIFIED_INTERNAL_COT'})
    output.write(json.dumps(row, ensure_ascii=False) + '\n')
    meta = {k: v for k, v in row.items() if k not in ['messages', 'system_messages_original', 'system_capture_candidates', 'tools_supported', 'readable_reasoning_original_native', 'reasoning_overlays_same_response_id']}
    meta.update({'message_count': len(row['messages']), 'assistant_responses': sum(x.get('role') == 'assistant' for x in row['messages']),
                 'native_reasoning_fields': len(row['readable_reasoning_original_native']),
                 'same_id_reasoning_overlay_fields': len(row['reasoning_overlays_same_response_id'])})
    metadata.write(json.dumps(meta, ensure_ascii=False) + '\n')
    counts['episodes'] += 1
    counts['old_episodes' if row['old_canonical_episode_id'] else 'supplemental_episodes'] += 1
    counts['assistant_responses'] += meta['assistant_responses']
    counts['system_status_' + row['system_capture_status']] += 1
    counts['all_called_tools_have_supported_schema'] += not bool(row['called_tools_missing_supported_schema'])
    counts['episodes_with_factory_schema_reconstruction'] += any(x['kind'].startswith('RECONSTRUCTED') for x in row['tool_schema_provenance'])
    counts['same_id_reasoning_overlay_fields'] += meta['same_id_reasoning_overlay_fields']
    counts['native_reasoning_fields'] += meta['native_reasoning_fields']
    counts['parse_error_lines'] += len(row['parse_error_line_numbers'])


def verify_outputs():
    """Independently reread original native files and positional old targets."""
    canonical = {x['episode_id']: x for x in rows(BUNDLE / 'canonical/native_episodes.jsonl.gz')}
    tally = Counter()
    seen = set()
    overlay_ids = set()
    for row in rows(OUT / 'episodes.contexts.jsonl.gz'):
        assert row['episode_id'] not in seen
        seen.add(row['episode_id'])
        p = Path(row['source_native']['path'])
        assert pin(p) == row['source_native']
        sid, messages, event_lines, issues = extract_event(p)
        assert sid == row['native_session_id'] and messages == row['messages']
        assert event_lines == row['source_event_lines'] and issues == row['parse_error_line_numbers']
        tally['raw_native_files_rehashed_and_messages_equal'] += 1
        if row['episode_id'] in canonical:
            old = canonical[row['episode_id']]
            assert len(old['messages']) == len(messages) and old['source_event_lines'] == event_lines
            tally['old_episode_positions_and_original_event_lines_match'] += 1
            for left, right in zip(messages, old['messages']):
                assert left.get('role') == right.get('role')
                if left.get('role') == 'assistant':
                    assert left.get('content') == right.get('content')
                    tally['old_assistant_target_bodies_equal'] += 1
        for overlay in row['reasoning_overlays_same_response_id']:
            assert messages[overlay['message_index']].get('responseId') == overlay['response_id']
            assert event_lines[overlay['message_index']] == overlay['source_event_line_1based']
            assert sha(overlay['text'].encode()) == overlay['text_sha256']
            overlay_ids.add(overlay['response_id'])
            tally['same_response_id_reasoning_fields_rehashed'] += 1
        for provenance in row['tool_schema_provenance']:
            if provenance['kind'].startswith('RECONSTRUCTED'):
                assert row['execution_condition']['image'] == IMAGE
                assert provenance['source'] == pin(FACTORY)
                assert provenance['provenance_source'] == pin(PROVENANCE)
        for tool in row['tools_supported']:
            assert not trunc(tool)
    assert tally['old_episode_positions_and_original_event_lines_match'] == 1763
    assert tally['old_assistant_target_bodies_equal'] == 32342
    provider_ids = set()
    for pair in rows(OUT / 'provider_pairs.original.jsonl.gz'):
        rid = pair['provider_response_id']
        assert rid not in provider_ids
        provider_ids.add(rid)
        assert sha(js(pair['response']).encode()) == pair['response_message_sha256']
        assert pin(pair['response_source']['path']) == pair['response_source']
        for request in pair['request_variants']:
            assert pin(request['source']['path']) == request['source']
            original = helper.unwrap_request(load(request['source']['path']))
            assert original['messages'] == request['messages'] and original.get('tools', []) == request['tools']
            tally['original_API_request_variants_rehashed_and_exact'] += 1
        tally['provider_response_pairs_rehashed'] += 1
    assert overlay_ids <= provider_ids
    assert tally['provider_response_pairs_rehashed'] == 1536
    result = {'schema_version': 'wrd-v9-input-recovery-QA-1.0', 'status': 'PASS',
              'counts': dict(tally), 'old_target_source_message_indices_safe_to_join': True,
              'raw_native_assistant_content_equals_old_canonical': True,
              'original_message_metadata_need_not_equal_old_sanitized_metadata': True,
              'all_supported_tools_free_of_explicit_truncation_markers': True,
              'no_business_quality_or_source_admission_certified': True,
              'verified_files': [pin(OUT / n) for n in ['episodes.contexts.jsonl.gz', 'episodes.metadata.jsonl.gz', 'provider_pairs.original.jsonl.gz']]}
    (OUT / 'QA.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'input_recovery_QA': result['status'], 'counts': dict(tally)}, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--verify-only', action='store_true')
    args = parser.parse_args()
    if not args.verify_only:
        main()
    verify_outputs()
