"""Inventory the original nine logged WRD service channels, without filtering.

Counts and absolute addresses only. Does not execute services, inspect credentials,
classify training eligibility, or equate transport event lines with SFT samples.
"""
from collections import Counter
import hashlib
import json
from pathlib import Path

ROOT = Path('D:/skillloop')
OUT = ROOT / 'output/20261026_wrd_raw_census_v7'
SERVICES = ROOT / 'output/workflow_library/services/current.json'


def sha(p):
    h = hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda: f.read(1048576), b''):
            h.update(b)
    return h.hexdigest()


def main():
    OUT.mkdir(exist_ok=True, parents=True)
    source = json.loads(SERVICES.read_text(encoding='utf-8-sig'))
    stats = []
    union = {k: set() for k in ('native_request_id', 'session_id', 'conversation_request_id', 'prompt_request_id')}
    for service in source['services']:
        path = Path(service['event_file'])
        c, ids, fields, times = Counter(), {k: set() for k in union}, Counter(), []
        before = sha(path) if path.is_file() else None
        if path.is_file():
            with path.open(encoding='utf-8-sig') as f:
                for line in f:
                    if not line.strip():
                        continue
                    c['nonempty_lines'] += 1
                    try:
                        r = json.loads(line)
                    except ValueError:
                        c['unparsed_lines'] += 1
                        continue
                    c['json_records'] += 1
                    c['event:' + str(r.get('event', r.get('type', 'unknown')))] += 1
                    fields.update(r.keys())
                    for key in ids:
                        if isinstance(r.get(key), str) and r[key]:
                            ids[key].add(r[key])
                    if isinstance(r.get('recorded_at'), str):
                        times.append(r['recorded_at'])
                    c['records_with_top_level_messages'] += isinstance(r.get('messages'), list)
                    c['records_with_top_level_response_or_request'] += bool(r.get('response') or r.get('request'))
                    c['records_with_nonempty_explicit_reasoning'] += any(isinstance(r.get(k), str) and r[k].strip() for k in ('reasoning_content', 'thinking_content', 'analysis_content'))
        for key in ids:
            union[key].update(ids[key])
        after = sha(path) if path.is_file() else None
        stats.append({'lane': service['lane'], 'original_event_file': str(path), 'exists': path.is_file(),
                      'bytes': path.stat().st_size if path.is_file() else None,
                      'sha256_before': before, 'sha256_after': after, 'stable_during_read': before == after,
                      'original_service_entrypoint': service.get('entrypoint'),
                      'counts': dict(c), 'distinct_identifiers': {k: len(v) for k, v in ids.items()},
                      'top_level_field_counts': dict(fields),
                      'first_recorded_at_lexical': min(times) if times else None,
                      'last_recorded_at_lexical': max(times) if times else None})
    result = {'schema_version': 'wrd-original-nine-channel-address-census-v7',
              'source_service_manifest': str(SERVICES), 'source_manifest_sha256': sha(SERVICES),
              'source_manifest_checked_at': source.get('checked_at'), 'channels': stats,
              'channel_event_file_bytes': sum(r['bytes'] or 0 for r in stats),
              'unique_original_channel_event_files': len({r['original_event_file'].lower() for r in stats}),
              'union_distinct_identifiers': {k: len(v) for k, v in union.items()},
              'transport_event_lines_are_not_independent_training_examples': True,
              'event_metadata_does_not_substitute_model_body_or_tool_transcript': True,
              'no_training_filter_applied': True,
              'no_original_modified_or_service_called': True, 'training_started': False,
              'script_sha256': sha(Path(__file__))}
    (OUT / 'NINE_CHANNEL_SERVICE_CENSUS.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'channels': len(stats), 'bytes': result['channel_event_file_bytes'],
                      'distinct_native_requests': result['union_distinct_identifiers']['native_request_id'],
                      'all_sources_stable': all(r['stable_during_read'] for r in stats)}))


if __name__ == '__main__':
    main()
