"""Recover actual write/edit bytes and first delivered observations, no execution."""
from pathlib import Path
import argparse
import gzip
import hashlib
import json


def js(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--ledger', required=True, type=Path)
    ap.add_argument('--episode', required=True, type=Path)
    ap.add_argument('--output', required=True, type=Path)
    ap.add_argument('--seed-job-skill-copy-after-call')
    args = ap.parse_args()
    rows = [json.loads(line) for line in gzip.open(args.ledger, 'rt', encoding='utf-8')]
    job = json.loads((args.episode / 'job.json').read_text(encoding='utf-8-sig'))
    args.output.mkdir(exist_ok=False)
    objects = args.output / 'objects'
    objects.mkdir()
    observations = {}
    for row in rows:
        for index, message in enumerate(row['native_messages']):
            if message.get('role') == 'tool' and message.get('tool_call_id'):
                observations.setdefault(message['tool_call_id'], {'first_delivered_in_call_id': row['call_id'],
                    'message_index': index, 'request_path': row['request'], 'request_sha256': row['request_sha256'],
                    'message': message})
    current = {}
    versions = []
    events = []
    for row in rows:
        for call in row['message'].get('tool_calls', []):
            function = call['function']
            original_arguments = function['arguments']
            fields = json.loads(original_arguments)
            tool = function['name']
            observed = observations.get(call['id'])
            event = {'compatible_call_id': row['call_id'], 'tool_call_id': call['id'], 'tool': tool,
                     'arguments_sha256_utf8': digest(original_arguments.encode('utf-8')),
                     'arguments_chars': len(original_arguments),
                     'original_response_path': row['response'], 'original_response_sha256': row['response_sha256'],
                     'observation': None, 'positive_loss_approved': False}
            if observed:
                observation_bytes = (js(observed['message']) + '\n').encode('utf-8')
                identity = digest(observation_bytes)
                (objects / identity).write_bytes(observation_bytes)
                event['observation'] = {k: v for k, v in observed.items() if k != 'message'}
                event['observation'].update(message_sha256=identity, object=identity)
            path = fields.get('path')
            if tool == 'write' and isinstance(path, str) and path.startswith('/workspace/outputs/') and isinstance(fields.get('content'), str):
                raw = fields['content'].encode('utf-8')
                identity = digest(raw)
                (objects / identity).write_bytes(raw)
                previous = digest(current[path]) if path in current else None
                current[path] = raw
                version = {'path': path, 'source': 'actual_complete_native_compatible_write_arguments',
                           'previous_sha256': previous, 'sha256': identity, 'bytes': len(raw),
                           'object': identity, 'compatible_call_id': row['call_id'], 'tool_call_id': call['id']}
                versions.append(version)
                event['version'] = version
            elif tool == 'edit':
                event['path'] = path
                if path not in current:
                    event['reconstruction_status'] = 'NO_PATH_OR_NO_PRIOR_EXACT_VERSION_DO_NOT_INFER_MUTATION'
                else:
                    text = current[path].decode('utf-8')
                    before = digest(current[path])
                    counts = []
                    for edit in fields.get('edits', []):
                        old, new = edit.get('oldText'), edit.get('newText')
                        if not isinstance(old, str) or not isinstance(new, str):
                            counts.append(None)
                            break
                        count = text.count(old)
                        counts.append(count)
                        if count != 1:
                            break
                        text = text.replace(old, new, 1)
                    if counts and all(count == 1 for count in counts):
                        raw = text.encode('utf-8')
                        identity = digest(raw)
                        (objects / identity).write_bytes(raw)
                        current[path] = raw
                        version = {'path': path, 'source': 'exact_unique_original_edit_applied_to_prior_original_write_bytes',
                                   'previous_sha256': before, 'sha256': identity, 'bytes': len(raw),
                                   'object': identity, 'compatible_call_id': row['call_id'], 'tool_call_id': call['id'],
                                   'old_text_occurrence_counts': counts}
                        versions.append(version)
                        event['version'] = version
                    else:
                        event.update(reconstruction_status='AMBIGUOUS_OR_UNMATCHED_ORIGINAL_EDIT', old_text_occurrence_counts=counts)
            elif tool == 'exec':
                event['exec_side_effects_not_inferred_or_reexecuted'] = True
                if args.seed_job_skill_copy_after_call == row['call_id']:
                    command = fields.get('command', '')
                    assert 'cp -r /workspace/inputs/previous_skill/. /workspace/outputs/skill/' in command
                    assert observed and 'SETUP_OK' in js(observed['message'])
                    seeded = []
                    for resource in job['resources']:
                        mount = resource['mount']
                        if not mount.startswith('inputs/previous_skill/'):
                            continue
                        source = Path(resource['path'])
                        raw = source.read_bytes()
                        identity = digest(raw)
                        assert identity == resource['sha256']
                        assert identity in js(observed['message']), 'Native copy hash observation must contain every seeded resource hash'
                        target = '/workspace/outputs/skill/' + mount.removeprefix('inputs/previous_skill/')
                        assert target not in current
                        current[target] = raw
                        (objects / identity).write_bytes(raw)
                        version = {'path': target, 'source': 'declared_exact_input_copy_and_actual_native_successful_hash_observation',
                                   'previous_sha256': None, 'sha256': identity, 'bytes': len(raw),
                                   'object': identity, 'compatible_call_id': row['call_id'], 'tool_call_id': call['id'],
                                   'input_source_path': str(source), 'input_mount': mount,
                                   'actual_observation_reports_exact_sha': True}
                        versions.append(version)
                        seeded.append(version)
                    assert seeded, 'Explicit seed requested but no validated actual input copy found'
                    event['verified_skill_copy_seeds'] = seeded
            events.append(event)
    final = []
    for path, raw in sorted(current.items()):
        local = args.episode / 'workspace/outputs' / path.removeprefix('/workspace/outputs/')
        actual = local.read_bytes() if local.is_file() else None
        final.append({'path': path, 'reconstructed_sha256': digest(raw),
                      'final_actual_sha256': digest(actual) if actual is not None else None,
                      'matches_final_file': raw == actual, 'final_file_path': str(local)})
    report = {'schema': 'wrd-native-exact-file-version-and-observation-graph-v1',
              'raw_ledger_path': str(args.ledger), 'raw_ledger_sha256': digest(args.ledger.read_bytes()),
              'episode': str(args.episode), 'events': events, 'versions': versions, 'final_matches': final,
              'raw_tool_observations_preserved': True, 'same_upstream_model_call_not_assumed_for_each_compatible_response': True,
              'file_success_is_not_content_correctness_or_positive_loss': True,
              'no_model_calls_or_tool_actions_reexecuted': True}
    (args.output / 'VERSION_GRAPH.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'events': len(events), 'versions': len(versions), 'exact_final_matches': sum(r['matches_final_file'] for r in final),
                      'final_files': len(final), 'observations': sum(bool(e['observation']) for e in events)}))


if __name__ == '__main__':
    main()
