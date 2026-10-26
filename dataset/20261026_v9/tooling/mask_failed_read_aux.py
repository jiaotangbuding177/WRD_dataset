"""Revoke unsupported read-aux positive owners without changing their context.

Observed tool failure is not declared a semantic mistake. This erratum only
removes the automatic positive auxiliary supervision assigned to those owners.
No tokenization, model loading, execution replay, source regrouping or Git write.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timezone
import copy
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'output/20261026_wrd_dataset_v9'
HISTORY = OUT / 'publication_history/failed_read_fix'
Q = ROOT / 'output/20261026_wrd_quality_v8/controlled/native_targets.quality.jsonl.gz'
ERRATA = OUT / 'TARGET_QUALITY_ERRATA.json'
REASON = 'OBSERVED_TOOL_FAILURE_HAS_NO_AUTOMATIC_POSITIVE_READ_AUX_CREDIT'


def js(value):
    return json.dumps(value, ensure_ascii=False, separators=(',', ':'))


def sha(data):
    return hashlib.sha256(data).hexdigest()


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as handle:
        for block in iter(lambda: handle.read(1048576), b''):
            h.update(block)
    return h.hexdigest()


def rows(path):
    with gzip.open(path, 'rt', encoding='utf-8') as handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)


def info(path):
    return {'path': str(path), 'bytes': path.stat().st_size, 'sha256': digest(path)}


def save(path, value):
    temp = path.with_name(path.name + '.failed-read-tmp')
    with temp.open('w', encoding='utf-8', newline='\n') as handle:
        handle.write(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
    temp.replace(path)


def save_gz(path, values):
    temp = path.with_name(path.name + '.failed-read-tmp')
    with temp.open('wb') as raw:
        with gzip.GzipFile(filename='', mode='wb', fileobj=raw, mtime=0) as compressed:
            for value in values:
                compressed.write((js(value) + '\n').encode('utf-8'))
    temp.replace(path)


def rewrite_metadata_gz(path, change):
    temp = path.with_name(path.name + '.failed-read-tmp')
    hits = 0
    with gzip.open(path, 'rt', encoding='utf-8') as original:
        with temp.open('wb') as raw:
            with gzip.GzipFile(filename='', mode='wb', fileobj=raw, mtime=0) as output:
                for line in original:
                    value = json.loads(line)
                    value, changed = change(value)
                    hits += changed
                    output.write((js(value) + '\n').encode('utf-8') if changed else line.encode('utf-8'))
    temp.replace(path)
    return hits


def main():
    assert not ERRATA.exists(), 'Erratum already exists; do not apply counter decrements twice.'
    assert not HISTORY.exists(), 'Preserve any prior repair history rather than overwrite it.'
    report_path = OUT / 'COMPILATION_REPORT.json'
    split_path = OUT / 'SOURCE_GROUP_SPLIT.json'
    native_path = OUT / 'compiled/native.pre_split.jsonl.gz'
    original_report = json.loads(report_path.read_text(encoding='utf-8'))
    original_split = json.loads(split_path.read_text(encoding='utf-8'))
    native = list(rows(native_path))
    quality = {r['id']: r for r in rows(Q)}
    revoke = {}
    for row in native:
        for target in row['targets']:
            if quality.get(target['id'], {}).get('observed_tool_failure') is True:
                assert target['supervision_tier'] == 'read_only_protocol_auxiliary'
                assert target['supervised_tokens'] > 0
                revoke[target['id']] = {'row_id': row['id'], 'episode_id': row['episode_id'],
                    'target': copy.deepcopy(target), 'quality_source': quality[target['id']]}
    assert len(revoke) == 10, {'unexpected_revocation_population': len(revoke)}

    coord_inputs = [Path(x['path']) for x in original_report['immutable_input_pins']
                    if 'coordination' in x['path']]
    assert len(coord_inputs) == 3
    fixed_paths = coord_inputs + [OUT / 'compiled/coordination.pre_split.jsonl.gz'] + sorted((OUT / 'sft').glob('coordination.*.jsonl.gz'))
    fixed = {str(p): info(p) for p in fixed_paths}
    assert len(list((OUT / 'sft').glob('coordination.*.jsonl.gz'))) == 6
    mutate_paths = [native_path, OUT / 'processed/targets.processing.jsonl.gz',
                    OUT / 'processed/native.student_traces.all.jsonl.gz', report_path, split_path]
    mutate_paths += sorted((OUT / 'sft').glob('native_process.*.jsonl.gz'))
    old_pins = {str(p): info(p) for p in mutate_paths}

    HISTORY.mkdir(parents=True)
    snapshot_paths = set(mutate_paths) | set((OUT / 'sft').glob('*.jsonl.gz')) | set(OUT.glob('*.json'))
    for source in sorted(snapshot_paths):
        target = HISTORY / source.relative_to(OUT)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        assert digest(source) == digest(target)
    save(HISTORY / 'SNAPSHOT.json', {'created_at_utc': datetime.now(timezone.utc).isoformat(),
        'scope': 'Original native arrays, processed labels/traces, all SFT shards and root JSON receipts before failed-read auxiliary correction.',
        'files': [info(p) for p in sorted(snapshot_paths)],
        'history_not_default_publication_payload': True})

    old_owners = sum(len(row['targets']) for row in native)
    old_tokens = sum(row['supervised_tokens'] for row in native)
    new_native = []
    changed_row_ids, dropped_ids = set(), set()
    removed_component = Counter()
    for row in native:
        doomed = [t for t in row['targets'] if t['id'] in revoke]
        if not doomed:
            new_native.append(row)
            continue
        before = copy.deepcopy(row)
        removed_spans = Counter(tuple(s) for t in doomed for s in t['owned_supervision_spans'])
        retained_spans = Counter(tuple(s) for t in row['targets'] if t['id'] not in revoke for s in t['owned_supervision_spans'])
        assert not (removed_spans.keys() & retained_spans.keys())
        assert Counter(tuple(s) for s in row['supervision_spans']) == removed_spans + retained_spans
        for span, multiplicity in removed_spans.items():
            removed_component[span[2]] += (span[1] - span[0]) * multiplicity
        row['targets'] = [t for t in row['targets'] if t['id'] not in revoke]
        row['supervision_spans'] = sorted(s for t in row['targets'] for s in t['owned_supervision_spans'])
        row['supervised_tokens'] = sum(s[1] - s[0] for s in row['supervision_spans'])
        row['supervised_tokens_by_component'] = dict(sum((Counter({s[2]: s[1] - s[0]}) for s in row['supervision_spans']), Counter()))
        row['supervision_spans_sha256'] = sha(js(row['supervision_spans']).encode())
        changed_row_ids.add(row['id'])
        for key in ['input_ids', 'messages', 'tools', 'rendered_sha256', 'full_episode_rendered_sha256',
                    'input_ids_sha256_u32le', 'source_ids', 'source_closure', 'source_native', 'total_tokens']:
            assert row[key] == before[key], (row['id'], key)
        if row['supervised_tokens']:
            new_native.append(row)
        else:
            dropped_ids.add(row['id'])
    save_gz(native_path, new_native)

    def revoke_processing(entry):
        if entry['id'] not in revoke:
            return entry, 0
        entry['supervision_tier'] = None
        entry['loss_multiplier'] = 0.0
        entry.setdefault('mask_reasons', []).append(REASON)
        if 'admitted_in_common_32k' in entry:
            entry['admitted_in_common_32k'] = False
        if 'owned_spans_before_length_filter' in entry:
            entry['owned_spans_before_length_filter'] = []
        entry['quality_erratum'] = 'TARGET_QUALITY_ERRATA.json'
        entry['observed_tool_failure_is_not_automatic_semantic_error'] = True
        return entry, 1

    ledger_hits = rewrite_metadata_gz(OUT / 'processed/targets.processing.jsonl.gz', revoke_processing)

    def revoke_trace(trace):
        hits = 0
        original_messages = js(trace['messages'])
        for i, target in enumerate(trace['targets']):
            trace['targets'][i], changed = revoke_processing(target)
            hits += changed
        assert js(trace['messages']) == original_messages
        return trace, hits

    trace_hits = rewrite_metadata_gz(OUT / 'processed/native.student_traces.all.jsonl.gz', revoke_trace)
    assert ledger_hits == trace_hits == 10

    # Preserve the original group/split assignment. No union-find or resampling.
    assignment = {}
    for group in original_split['groups']:
        for rid in group['row_ids']:
            assert rid not in assignment
            assignment[rid] = (group['split'], group['component_id'])
    new_by_id = {r['id']: r for r in new_native}
    shard_before = {}
    for path in sorted((OUT / 'sft').glob('native_process.*.jsonl.gz')):
        old_rows = list(rows(path))
        shard_before[path.name] = [r['id'] for r in old_rows]
        new_rows = []
        for old in old_rows:
            if old['id'] in dropped_ids:
                continue
            row = copy.deepcopy(new_by_id[old['id']])
            split, component = assignment[row['id']]
            assert split == old['split'] and component == old['source_component_id']
            row['split'], row['source_component_id'] = split, component
            for key in ['input_ids', 'messages', 'tools', 'rendered_sha256', 'input_ids_sha256_u32le',
                        'source_ids', 'source_closure', 'source_native', 'total_tokens']:
                assert row[key] == old[key]
            new_rows.append(row)
        save_gz(path, new_rows)
    groups = []
    for group in original_split['groups']:
        keep = [rid for rid in group['row_ids'] if rid not in dropped_ids]
        if keep:
            groups.append({**group, 'row_ids': keep, 'rows': len(keep)})
    counts = Counter()
    by_bank = defaultdict(Counter)
    files = []
    all_seen = set()
    for path in sorted((OUT / 'sft').glob('*.jsonl.gz')):
        for row in rows(path):
            assert row['id'] not in all_seen
            all_seen.add(row['id'])
            split = row['split']
            assert assignment[row['id']] == (split, row['source_component_id'])
            counts[split + '_rows'] += 1
            counts[split + '_supervised_tokens'] += row['supervised_tokens']
            counts[split + '_input_tokens'] += row['total_tokens']
            by_bank[row['bank']][split + '_rows'] += 1
            by_bank[row['bank']][split + '_supervised_tokens'] += row['supervised_tokens']
        files.append({'path': 'sft/' + path.name, 'bytes': path.stat().st_size, 'sha256': digest(path)})
    assert all_seen == {rid for group in groups for rid in group['row_ids']}
    new_split = {**original_split, 'groups': groups, 'counts': dict(counts),
        'independent_components': len(groups), 'independent_dev_test_available': bool(counts['dev_rows'] and counts['test_rows'])}
    save(split_path, new_split)

    report = copy.deepcopy(original_report)
    report['native']['counts']['native_compiled_sequences'] = len(new_native)
    report['native']['counts']['native_owned_targets'] = sum(len(row['targets']) for row in new_native)
    report['native']['counts']['native_supervised_tokens'] = sum(row['supervised_tokens'] for row in new_native)
    for bad in revoke.values():
        q = bad['quality_source']
        stage = q.get('request_corrected_role') or q.get('old_catalog_stage') or 'unknown'
        report['native']['stage_target_tiers'][stage]['read_only_protocol_auxiliary'] -= 1
        report['native']['stage_target_tiers'][stage]['context_only'] += 1
        report['native']['target_tiers_before_length_filter']['read_only_protocol_auxiliary'] -= 1
        length = report['native']['length_counts']
        end = bad['target']['response_end_token_exclusive']
        length['positive_targets_before_length_filter'] -= 1
        length['positive_targets_le16k' if end <= 16384 else 'positive_targets_gt16k'] -= 1
        length['positive_targets_le32k' if end <= 32768 else 'positive_targets_gt32k'] -= 1
    for rec in report['native']['files']:
        path = Path(rec['path'])
        rec.update(info(path))
    report['split'] = {'counts': dict(counts), 'by_bank': {k: dict(v) for k, v in by_bank.items()},
                       'files': files, 'source_components': len(groups)}
    correction = {'script': str(Path(__file__)), 'script_sha256': digest(Path(__file__)),
        'errata': 'TARGET_QUALITY_ERRATA.json', 'snapshot': str(HISTORY), 'removed_positive_owners': len(revoke),
        'removed_supervised_tokens': sum(removed_component.values()), 'removed_tokens_by_component': dict(removed_component),
        'original_compile_and_native_parent_receipts_preserved': True,
        'retained_row_inputs_messages_rendered_and_source_bytes_unchanged': True,
        'same_split_and_component_no_resampling': True,
        'old_native_pre_split': old_pins[str(native_path)], 'new_native_pre_split': info(native_path)}
    report['native_postcompilation_mask_erratum'] = correction
    save(report_path, report)
    for path, before in fixed.items():
        assert info(Path(path)) == before, path
    new_pins = {str(p): info(p) for p in mutate_paths}
    final_owners = {t['id'] for row in new_native for t in row['targets']}
    assert not (set(revoke) & final_owners)
    assert len(final_owners) == old_owners - 10
    assert sum(row['supervised_tokens'] for row in new_native) == old_tokens - sum(removed_component.values())
    assert report['coordination'] == original_report['coordination']
    save(ERRATA, {'schema_version': 'wrd-v9-target-quality-errata-failed-read-aux-v1',
        'created_at_utc': datetime.now(timezone.utc).isoformat(), 'status': 'APPLIED_PENDING_INDEPENDENT_FRESH_QA',
        'reason': REASON, 'observed_failure_is_not_a_semantic_error_label': True,
        'original_actions_results_failures_reasoning_and_source_closure_preserved': True,
        'removed_positive_owner_records': [{k: v for k, v in bad.items() if k != 'quality_source'} | {
            'observed_tool_failure': True, 'failure_evidence_ref': {'path': str(Q), 'target_id': tid}}
            for tid, bad in revoke.items()],
        'quality_source': info(Q), 'old_files': old_pins, 'new_files': new_pins,
        'unchanged_coordination_inputs_pre_split_and_sft': fixed,
        'native_before': {'rows': len(native), 'owners': old_owners, 'supervised_tokens': old_tokens},
        'native_after': {'rows': len(new_native), 'owners': len(final_owners),
            'supervised_tokens': sum(row['supervised_tokens'] for row in new_native)},
        'dropped_zero_supervision_row_ids': sorted(dropped_ids), 'changed_row_ids': sorted(changed_row_ids),
        'removed_tokens_by_component': dict(removed_component), 'split_after': report['split'],
        'same_split_and_component_no_resampling': True, 'no_reencoding_or_tail_trimming': True,
        'source_script': info(Path(__file__)), 'training_started': False, 'new_business_runs': 0})
    print(json.dumps({'status': 'APPLIED', 'native_before': {'rows': len(native), 'owners': old_owners, 'tokens': old_tokens},
        'native_after': {'rows': len(new_native), 'owners': len(final_owners), 'tokens': sum(row['supervised_tokens'] for row in new_native)},
        'dropped_rows': len(dropped_ids), 'native_pre_split': info(native_path), 'compilation_report': info(report_path),
        'source_group_split': info(split_path), 'errata': info(ERRATA)}, ensure_ascii=True), flush=True)


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    main()
