"""Revalidate final02 metadata/loss-only replacement against frozen final17 scans.

Offline byte/token audit only. Does not execute business code or modify prior data.
"""
import gzip
import hashlib
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
WORK = ROOT / 'output/20261031_wrd_curation09'
OUT = WORK / 'protection_followup09'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def pin(path):
    path = path.resolve()
    return {'path': str(path.relative_to(ROOT)).replace('\\', '/'),
            'bytes': path.stat().st_size, 'sha256': digest(path.read_bytes())}


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def rows(path):
    with gzip.open(path, 'rt', encoding='utf-8-sig') as stream:
        return [json.loads(line) for line in stream if line.strip()]


def canonical_hash(value, sort=False):
    return digest(json.dumps(value, ensure_ascii=False, sort_keys=sort,
                             separators=(',', ':')).encode())


def load_compiled(folder):
    report_path = folder / 'compiled02/COMPILATION_REPORT.json'
    report = read(report_path)
    result = {}
    file_pins = []
    for item in report['files']:
        path = report_path.parent / item['path']
        actual = pin(path)
        assert actual['bytes'] == item['bytes'] and actual['sha256'] == item['sha256']
        file_pins.append(actual)
        for row in rows(path):
            assert row['id'] not in result
            result[row['id']] = row
    return report, report_path, result, file_pins


def token_credit(row):
    result = {}
    for start, end, component, weight in row['supervision_spans']:
        assert 0 <= start < end <= len(row['input_ids']) and weight > 0
        for token in range(start, end):
            assert token not in result
            result[token] = (component, weight)
    assert len(result) == row['supervised_tokens']
    return result


old_folder = WORK / 'compiled_followup_final01'
new_folder = WORK / 'compiled_followup_final02'
old_prepared_path = old_folder / 'CANDIDATES_STAGING_NOT_MAIN.jsonl.gz'
new_prepared_path = new_folder / 'CANDIDATES_STAGING_NOT_MAIN.jsonl.gz'
old_prepared = {row['id']: row for row in rows(old_prepared_path)}
new_prepared = {row['id']: row for row in rows(new_prepared_path)}
old_report, old_report_path, old_compiled, old_files = load_compiled(old_folder)
new_report, new_report_path, new_compiled, new_files = load_compiled(new_folder)
scan_path = OUT / 'FINAL17_01_ISOLATION_SCAN.json'
binding_path = OUT / 'FINAL17_ACCEPTANCE_BINDING_AND_IMAGE_QA.json'
scan = read(scan_path)
binding = read(binding_path)
assert pin(old_prepared_path) == scan['prepared_pin'] == binding['prepared_pin']
assert pin(old_report_path) == binding['actual_compilation_report_pin']
assert {row['path']: row['sha256'] for row in old_files} == {
    row['path']: row['sha256'] for row in scan['compiled_file_pins']}
assert len(old_prepared) == len(new_prepared) == len(old_compiled) == len(new_compiled) == 17
assert set(old_prepared) == set(new_prepared) == set(old_compiled) == set(new_compiled)
scan_rows = {row['id']: row for row in scan['rows']}
assert set(scan_rows) == set(new_prepared)
allow_prepared_diff = {'original_candidate_file_pin', 'target_code_unicode_exclusions'}
allow_compiled_diff = {'original_record_metadata', 'supervision_spans', 'targets',
                       'supervised_tokens', 'supervised_tokens_by_component',
                       'supervision_spans_sha256'}
checks = []
removed_total = 0
changed_credit = []
for record_id, new in new_prepared.items():
    old = old_prepared[record_id]
    changed_prepared_fields = sorted(key for key in set(old) | set(new)
                                    if old.get(key) != new.get(key))
    assert set(changed_prepared_fields) <= allow_prepared_diff
    if 'target_code_unicode_exclusions' in changed_prepared_fields:
        assert new['owner_id'] == '66e542b63e52392b7e1dbfc2'
        before, after = old['target_code_unicode_exclusions'], new['target_code_unicode_exclusions']
        assert len(before) == len(after) == 1
        assert before[0]['start'] == 554 and after[0]['start'] == 510
        assert before[0]['end'] == after[0]['end'] == 851
        assert after[0]['text'].endswith(before[0]['text'])
        assert digest(after[0]['text'].encode()) == after[0]['text_sha256']
    source_path = Path(new['source_context']['path'])
    source_pin = pin(source_path)
    assert source_pin['bytes'] == new['source_context']['bytes']
    assert source_pin['sha256'] == new['source_context']['sha256']
    assert source_pin == scan_rows[record_id]['packet_pin']
    assert new['owner_id'] == scan_rows[record_id]['owner_id']
    assert new['original_episode_id'] == scan_rows[record_id]['original_episode_id']
    assert new['original_message_index'] == scan_rows[record_id]['original_target_message_index']
    assert new['original_target_sha256_sorted'] == scan_rows[record_id]['original_target_SHA_sorted']
    raw_pin = new['original_candidate_file_pin']
    actual_raw_pin = pin(Path(raw_pin['path']))
    assert actual_raw_pin['bytes'] == raw_pin['bytes'] and actual_raw_pin['sha256'] == raw_pin['sha256']
    old_c, new_c = old_compiled[record_id], new_compiled[record_id]
    assert old_c['messages'] == new_c['messages'] == old['messages'] == new['messages']
    assert old_c['tools'] == new_c['tools'] == old['tools'] == new['tools']
    changed_compiled_fields = sorted(key for key in set(old_c) | set(new_c)
                                    if old_c.get(key) != new_c.get(key))
    assert set(changed_compiled_fields) <= allow_compiled_diff
    assert old_c['input_ids'] == new_c['input_ids']
    assert old_c['rendered_sha256'] == new_c['rendered_sha256']
    assert old_c['input_ids_sha256_u32le'] == new_c['input_ids_sha256_u32le']
    old_credit, new_credit = token_credit(old_c), token_credit(new_c)
    assert all(old_credit.get(index) == value for index, value in new_credit.items())
    removed = sorted(set(old_credit) - set(new_credit))
    if removed:
        assert new['owner_id'] == '66e542b63e52392b7e1dbfc2'
        assert removed == list(range(2280, 2290))
        assert all(old_credit[index] == ('A', 0.25) for index in removed)
        changed_credit.append(record_id)
    removed_total += len(removed)
    checks.append({'id': record_id, 'owner_id': new['owner_id'],
                   'source_context_pin': source_pin, 'source_ids': new['source_ids'],
                   'original_episode_id': new['original_episode_id'],
                   'original_message_index': new['original_message_index'],
                   'original_target_sha256_sorted': new['original_target_sha256_sorted'],
                   'messages_sha256_canonical': canonical_hash(new['messages']),
                   'messages_tools_original_identity_unchanged': True,
                   'compiled_input_ids_and_rendered_sha256_unchanged': True,
                   'prepared_changed_fields': changed_prepared_fields,
                   'compiled_changed_fields': changed_compiled_fields,
                   'removed_positive_token_indices': removed,
                   'added_positive_token_indices': [],
                   'unchanged_positive_component_and_weight': True})
assert removed_total == 10 and len(changed_credit) == 1
counts = Counter()
for record in new_compiled.values():
    counts['sequences'] += 1
    counts['targets'] += len(record['targets'])
    counts['input_tokens'] += len(record['input_ids'])
    counts['supervised_tokens'] += len(token_credit(record))
    for component, number in record['supervised_tokens_by_component'].items():
        counts['component_' + component] += number
for key in ['sequences', 'targets', 'input_tokens', 'supervised_tokens', 'component_A', 'component_E']:
    assert counts[key] == new_report['counts'][key]
assert counts['input_tokens'] == 97773 and counts['supervised_tokens'] == 11000
assert counts['component_A'] == 10845 and counts['component_E'] == 155
assert new_report['tokenizer_proof'] == old_report['tokenizer_proof']
for item in new_report['immutable_inputs']:
    assert pin(Path(item['path']))['sha256'] == item['sha256']

image_checks = []
for material in binding['actual_recovered_image_QA']:
    paths = [material['restored_actual_pin'], material['original_actual_workspace_pin']]
    paths += [entry['actual_source_file_pin'] for entry in material['all1107_binding_SHA_occurrences']]
    for entry in paths:
        path = Path(entry['path'])
        if not path.is_absolute():
            path = ROOT / path
        assert path.stat().st_size == entry['bytes'] and digest(path.read_bytes()) == entry['sha256']
    assert new_prepared[material['candidate_id']]['execution_material_dependencies'] == old_prepared[
        material['candidate_id']]['execution_material_dependencies']
    image_checks.append({'candidate_id': material['candidate_id'], 'actual_bytes_rechecked': True,
                         'sha256': material['material']['sha256'],
                         'unchanged_material_metadata': True, 'actual_copy_count_rechecked': len(paths),
                         'scope': 'Restored, original historical workspace and provided export exact bytes; not proof of original model visual receipt or unrecorded ancestry.'})
for key in ['sealed_holdout_manifest_pin', 'sealed_eval_array_manifest_pin']:
    assert pin(ROOT / binding[key]['path']) == binding[key]

result = {
    'schema': 'wrd09-final17-final02-scan-inheritance-v1',
    'status': 'PASS_IDENTICAL_INPUT_AND_ANCESTRY_WITH_ONLY_TEN_A_TOKENS_WITHDRAWN',
    'prepared_pin': pin(new_prepared_path), 'actual_compilation_report_pin': pin(new_report_path),
    'compiled_file_pins': new_files, 'actual_compilation_counts': new_report['counts'],
    'prior_scan_pin': pin(scan_path), 'prior_image_and_isolation_binding_pin': pin(binding_path),
    'prior_prepared_pin': pin(old_prepared_path), 'prior_compilation_report_pin': pin(old_report_path),
    'inheritance_basis': 'All 17 actual messages/tools/input_ids/rendered SHA and source_context packet pins/target identities are equal; only raw revision pins and one exclusion metadata changed. Prior captured native prefix and new-state scans apply byte-for-byte.',
    'protected_private_business_long_text_matches': binding['protected_private_business_long_text_matches'],
    'eval26_long_text_matches': binding['eval26_long_text_matches'],
    'generic_only_match': binding['generic_only_match'],
    'removed_A_tokens': removed_total, 'added_positive_tokens': 0, 'row_checks': checks,
    'actual_recovered_image_recheck': image_checks,
    'sealed_holdout_manifest_pin': binding['sealed_holdout_manifest_pin'],
    'sealed_eval_array_manifest_pin': binding['sealed_eval_array_manifest_pin'],
    'scope_limit': binding['scope_limit'],
    'protected_thought_or_answer_semantics_read': False,
    'new_full_text_scan_performed': False,
    'model_or_training_started': False, 'main_or_sealed_outputs_modified': False,
    'script_pin': pin(Path(__file__))
}
destination = OUT / 'FINAL17_FINAL02_INHERITANCE_QA.json'
assert not destination.exists()
destination.write_bytes((json.dumps(result, ensure_ascii=False, indent=2) + '\n').encode())
print(json.dumps({'receipt_pin': pin(destination), 'prepared_pin': result['prepared_pin'],
                  'report_pin': result['actual_compilation_report_pin'],
                  'counts': result['actual_compilation_counts'], 'removed_A_tokens': removed_total,
                  'protected_private_business_matches': 0, 'eval26_matches': 0}, ensure_ascii=False))
