"""Stat broadly rediscovered WRD roots without changing the frozen base census."""
from __future__ import annotations

import gzip
import hashlib
import json
import os
import re
import stat
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

from physical_census import PROJECT, RUNS, DEFAULT_OUT, EXCLUDED_DIRS, category, hash_file, jread, norm, secure_path, utc


RULE = re.compile(r'^(20261019|20261020|20261021)_.*(wrd|workflow|handoff|native|T0012|T0145)|^20261021_v\d+_|^(outer152_|wrd153_|p7_|v7_controls_)|^validation_noskill_coordinator_1792382449061790600$', re.I)
CORE_NAMES = {'session_events.jsonl', 'native_events.jsonl', 'request.json', 'response.json', 'result.json', 'SKILL.md'}


def carriers(name):
    values = []
    if name in CORE_NAMES:
        values.append(name)
    low = name.lower()
    if low.endswith('.raw'):
        values.append('*.raw')
    if low.endswith('.sse') or '.sse.' in low:
        values.append('*.sse*')
    if ('request' in low or 'response' in low) and name not in CORE_NAMES:
        values.append('other_request_response_named_files')
    return values


def run(out=DEFAULT_OUT):
    primary_file = out / 'PHYSICAL_ROOTS.json'
    primary = jread(primary_file)
    base_roots = primary['roots']
    base_paths = {norm(r['path']): r for r in base_roots}
    base_scanned = [r for r in base_roots if r.get('recursive_scan')]
    candidates = {}
    shallow = []
    for root in [PROJECT / 'output', RUNS]:
        for p in sorted(root.iterdir()):
            if not p.is_dir() or not RULE.search(p.name):
                continue
            shallow.append({'path': str(p.absolute()), 'discovered_by': 'broad WRD/native/version/temporary-carrier shallow directory-name rule', 'in_frozen_base_addresses': norm(p) in base_paths})
            if norm(p) not in base_paths:
                candidates[norm(p)] = p
    explicit = [PROJECT / 'output/20261020_pipeline_v2_generation']
    for p in explicit:
        shallow.append({'path': str(p.absolute()), 'exists': p.exists(), 'discovered_by': 'independent memory/source-path review', 'in_frozen_base_addresses': norm(p) in base_paths})
        if p.is_dir() and norm(p) not in base_paths:
            candidates[norm(p)] = p
    ledger_path = out / 'controlled/ADDITIONAL_ORIGINAL_FILES.jsonl.gz'
    error_path = out / 'controlled/ADDITIONAL_NONTRAVERSED_REFERENCES.jsonl.gz'
    totals = Counter()
    total_carriers = Counter()
    roots = []
    errors = []
    global_file_ids = set()
    sorted_candidates = sorted(candidates.values(), key=lambda p: (len(p.parts), norm(p)))
    selected = []
    with gzip.open(ledger_path, 'wt', encoding='utf-8') as ledger, gzip.open(error_path, 'wt', encoding='utf-8') as nontraversed:
        for source in sorted_candidates:
            source_key = norm(source)
            previous_parent = next((r for r in base_scanned if source_key.startswith(norm(r['path']) + os.sep)), None)
            additional_parent = next((p for p in selected if source_key.startswith(norm(p) + os.sep)), None)
            rid = 'add_' + hashlib.sha256(source_key.encode()).hexdigest()[:12]
            root_row = {'root_id': rid, 'path': str(source.absolute()), 'role': 'additional_original_WRD_iteration_or_native_case_support', 'purpose': 'Previously unlisted original WRD generation/resource/handoff/native-case/control carrier; discovered without SFT admission.', 'coverage_parent': previous_parent['path'] if previous_parent else str(additional_parent) if additional_parent else None, 'files': 0, 'logical_path_bytes': 0, 'training_admission_performed': False}
            if 'wrd_training_review' in source.name:
                root_row.update(role='derived_research_review_documents', purpose='Historical WRD training-plan review documents; not native model execution records.')
            elif source.name.startswith('20261021_v'):
                root_row['purpose'] = 'WRD resource/handoff revision carrier: ' + source.name + '; per-file originals, copies, and native evidence are listed without inferring independent sessions.'
            if previous_parent or additional_parent:
                root_row['scan_status'] = 'already_covered_by_existing_or_additional_parent_not_rescanned'
                roots.append(root_row)
                continue
            selected.append(source)
            # E/T0012 parent is broader than the previously scanned observed_service
            # child. Skip that exact previously counted subtree to preserve union sums.
            old_descendants = [r['path'] for r in base_scanned if norm(r['path']).startswith(source_key + os.sep)]
            old_desc_keys = {norm(p) for p in old_descendants}
            root_row['previously_counted_descendant_roots_pruned'] = old_descendants
            root_row['overlap_existing_roots'] = old_descendants
            print('STAT_ADDITIONAL', rid, source, flush=True)
            cats, cat_bytes, ext, names, contexts = Counter(), Counter(), Counter(), Counter(), defaultdict(Counter)
            local_ids = set()
            local_identity_bytes = 0
            mtimes = []
            omitted = Counter()
            for base, dirs, files in os.walk(source, followlinks=False, onerror=lambda e: errors.append({'source_path': str(e.filename), 'error': str(e)})):
                base = Path(base)
                keep = []
                for name in sorted(dirs):
                    p = base / name
                    try:
                        attrs = p.lstat()
                        reparse = bool(getattr(attrs, 'st_file_attributes', 0) & getattr(stat, 'FILE_ATTRIBUTE_REPARSE_POINT', 0))
                        reason = 'previously_counted_descendant_root' if norm(p) in old_desc_keys else 'credential_or_dependency_directory' if name.lower() in EXCLUDED_DIRS else 'reparse_reference_not_followed' if reparse or p.is_symlink() else None
                        if reason:
                            nontraversed.write(json.dumps({'root_id': rid, 'source_path': str(p.absolute()), 'reason': reason, 'not_recursively_opened': True}, ensure_ascii=False) + '\n')
                            omitted[reason] += 1
                            continue
                        keep.append(name)
                    except OSError as e:
                        errors.append({'source_path': str(p), 'error': str(e)})
                dirs[:] = keep
                for name in sorted(files):
                    p = base / name
                    if not secure_path(p):
                        omitted['credential_file_not_opened'] += 1
                        continue
                    try:
                        attrs = p.lstat()
                        if p.is_symlink() or getattr(attrs, 'st_file_attributes', 0) & getattr(stat, 'FILE_ATTRIBUTE_REPARSE_POINT', 0):
                            nontraversed.write(json.dumps({'root_id': rid, 'source_path': str(p.absolute()), 'reason': 'reparse_file_reference_not_opened'}, ensure_ascii=False) + '\n')
                            omitted['reparse_file_reference_not_opened'] += 1
                            continue
                        s = p.stat()
                        if not stat.S_ISREG(s.st_mode):
                            continue
                        cat = category(p, source)
                        path_bits = p.relative_to(source).as_posix().lower().split('/')
                        context = 'input_or_cache_copy' if any(x in {'input', 'inputs', '_inputs', 'cache', '.cache'} for x in path_bits) else 'other_original_root_path'
                        identity = (s.st_dev, s.st_ino)
                        if identity not in local_ids:
                            local_ids.add(identity)
                            local_identity_bytes += s.st_size
                        if identity not in global_file_ids:
                            global_file_ids.add(identity)
                            totals['within_additional_unique_file_identity_bytes'] += s.st_size
                        ledger.write(json.dumps({'root_id': rid, 'source_path': str(p.absolute()), 'relative_path': p.relative_to(source).as_posix(), 'bytes': s.st_size, 'mtime_utc': utc(s.st_mtime), 'ctime_utc': utc(s.st_ctime), 'category': cat, 'copy_context': context, 'filesystem_device': s.st_dev, 'filesystem_file_id': str(s.st_ino), 'original_filename': name}, ensure_ascii=False) + '\n')
                        cats[cat] += 1
                        cat_bytes[cat] += s.st_size
                        ext[p.suffix.lower() or '[no_extension]'] += 1
                        for carrier in carriers(name):
                            names[carrier] += 1
                            contexts[context][carrier] += 1
                        mtimes.append(s.st_mtime)
                    except (OSError, ValueError) as e:
                        errors.append({'source_path': str(p), 'error': str(e)})
            root_row.update(scan_status='complete_regular_file_stat_with_explicit_reference_and_dependency_exclusions', files=sum(cats.values()), logical_path_bytes=sum(cat_bytes.values()), categories={k: {'files': cats[k], 'logical_path_bytes': cat_bytes[k]} for k in sorted(cats)}, extensions=dict(ext), filename_counts={k: names[k] for k in sorted(CORE_NAMES | {'*.raw', '*.sse*', 'other_request_response_named_files'})}, carrier_counts_by_path_context={k: dict(v) for k, v in contexts.items()}, filesystem_identity_unique_files=len(local_ids), filesystem_identity_unique_file_bytes=local_identity_bytes, exclusions=dict(omitted), earliest_file_mtime_utc=utc(min(mtimes)) if mtimes else None, latest_file_mtime_utc=utc(max(mtimes)) if mtimes else None)
            roots.append(root_row)
            totals['logical_path_files'] += root_row['files']
            totals['logical_path_bytes'] += root_row['logical_path_bytes']
            total_carriers.update(names)
    totals['within_additional_unique_file_identities'] = len(global_file_ids)
    totals['incremental_files'] = totals['logical_path_files']
    totals['incremental_logical_bytes'] = totals['logical_path_bytes']
    summary = {
        'schema_version': 'wrd-additional-original-roots-census-v7', 'date_utc': datetime.now(timezone.utc).isoformat(),
        'roots': roots, 'totals': dict(totals), 'filename_counts': {k: total_carriers[k] for k in sorted(CORE_NAMES | {'*.raw', '*.sse*', 'other_request_response_named_files'})},
        'frozen_base_address_count': len(base_roots), 'additional_address_count': len(roots),
        'known_address_union_count': len(set(base_paths) | {norm(r['path']) for r in roots}),
        'additional_scanned_roots': sum(r['scan_status'].startswith('complete_') for r in roots),
        'frozen_base_sha256_unchanged': hash_file(primary_file),
        'frozen_base_totals_preserved': primary['totals'],
        'base_plus_additional_path_bytes_without_content_dedup': primary['totals']['logical_path_bytes'] + totals['logical_path_bytes'],
        'base_plus_additional_path_files': primary['totals']['logical_path_files'] + totals['logical_path_files'],
        'global_identity_union_across_base_and_additional_not_computed': True,
        'controlled_file_ledger': str(ledger_path.absolute()), 'nontraversed_references': str(error_path.absolute()),
        'shallow_discovery': shallow, 'scan_errors': errors,
        'explicit_version_name_checks': [{'path': str(RUNS / f'w{n}'), 'exists': (RUNS / f'w{n}').exists()} for n in range(11, 36)] + [{'path': str(PROJECT / f'output/20261021_workflow_library_v{n}'), 'exists': (PROJECT / f'output/20261021_workflow_library_v{n}').exists()} for n in [1, 3, 5, 6]],
        'scope_correction': 'The initial directory rule favored workflow*library and omitted v10-v35, precursor WRD/native/handoff/control roots, and random temporary carriers. The first fifty addresses are a frozen base ledger, not all original making data.',
        'limitations': [
            'Discovery, physical file statistics, and semantic episode/action counts are separate. Carrier filename counts include snapshots/caches and are not independent sessions or new SFT samples.',
            'No content dedup is claimed; additional physical-file-identity counts are not blindly added to base unique identities.',
            'Original D_V10_SUPPLEMENT is subsumed by this additional-root ledger and must not be added twice.',
            'Previously counted descendant directories are pruned when a newly discovered parent is scanned.',
            'No model, SQLite content, current ablation process/container, unrelated user conversation, or credential store was opened or changed.',
            'Known addresses only; further independent memory and actual source-pointer discovery may find more roots.',
        ],
    }
    (out / 'ADDITIONAL_ORIGINAL_ROOTS.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'roots': len(roots), 'known_address_union': summary['known_address_union_count'], 'totals': summary['totals'], 'carrier_counts': summary['filename_counts'], 'errors': len(errors)}, ensure_ascii=False), flush=True)
    return summary


if __name__ == '__main__':
    run()
