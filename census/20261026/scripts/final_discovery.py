"""Stat five independently rediscovered production/infrastructure roots."""
from __future__ import annotations

import gzip
import hashlib
import json
import os
import stat
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from physical_census import DEFAULT_OUT, EXCLUDED_DIRS, category, hash_file, jread, norm, secure_path, utc
from additional_census import carriers, CORE_NAMES


ROOTS = [
    ('D:/skillloop/output/20261024_concurrency9', 'Original production nine-concurrency transition evidence, with request/dispatch/result references verified by independent lineage review.'),
    ('D:/skillloop/output/20261021_pipeline_infra_audit', 'Original pipeline infrastructure audit control and native evidence pointers.'),
    ('E:/skillloop_runs/20261021_pipeline_infra_audit', 'Original native runtime carrier for pipeline infrastructure audit.'),
    ('D:/skillloop/output/20261021_pipeline_infra_repair_v3', 'Original pipeline infrastructure repair-v3 control and verification evidence.'),
    ('E:/skillloop_runs/20261021_pipeline_infra_repair_v3', 'Original native runtime carrier for pipeline infrastructure repair-v3.'),
]


def run(out=DEFAULT_OUT):
    primary_file = out / 'PHYSICAL_ROOTS.json'
    additional_file = out / 'ADDITIONAL_ORIGINAL_ROOTS.json'
    base = jread(primary_file)
    extra = jread(additional_file)
    known = base['roots'] + extra['roots']
    known_paths = {norm(r['path']) for r in known}
    known_scanned = [r for r in base['roots'] if r.get('recursive_scan')] + [r for r in extra['roots'] if r['scan_status'].startswith('complete_')]
    ledger_path = out / 'controlled/FINAL_DISCOVERY_FILES.jsonl.gz'
    totals, filename_counts = Counter(), Counter()
    rows, errors, omitted = [], [], []
    unique_ids = set()
    with gzip.open(ledger_path, 'wt', encoding='utf-8') as ledger:
        for name, purpose in ROOTS:
            p = Path(name)
            rid = 'final_' + hashlib.sha256(norm(p).encode()).hexdigest()[:12]
            parent = next((r for r in known_scanned if norm(p) == norm(r['path']) or norm(p).startswith(norm(r['path']) + os.sep)), None)
            row = {'root_id': rid, 'path': str(p.absolute()), 'exists': p.is_dir(), 'role': 'independently_rediscovered_production_or_infrastructure_evidence', 'purpose': purpose, 'coverage_parent': parent['path'] if parent else None, 'overlap_existing_roots': [], 'files': 0, 'logical_path_bytes': 0, 'training_admission_performed': False}
            if not p.is_dir():
                row['scan_status'] = 'explicit_missing_root'
                errors.append({'source_path': str(p), 'error': 'Independently referenced directory currently missing'})
                rows.append(row)
                continue
            if parent:
                row['scan_status'] = 'already_counted_under_existing_root'
                rows.append(row)
                continue
            descendants = {norm(r['path']): r['path'] for r in known_scanned if norm(r['path']).startswith(norm(p) + os.sep)}
            row['overlap_existing_roots'] = list(descendants.values())
            cats, cat_bytes, extensions, local_carriers = Counter(), Counter(), Counter(), Counter()
            local_ids = set()
            identity_bytes = 0
            times = []
            for directory, dirs, files in os.walk(p, followlinks=False, onerror=lambda e: errors.append({'source_path': str(e.filename), 'error': str(e)})):
                directory = Path(directory)
                safe_dirs = []
                for n in sorted(dirs):
                    q = directory / n
                    try:
                        attrs = q.lstat()
                        reparse = bool(getattr(attrs, 'st_file_attributes', 0) & getattr(stat, 'FILE_ATTRIBUTE_REPARSE_POINT', 0))
                        reason = 'previously_counted_descendant_root' if norm(q) in descendants else 'credential_or_dependency_directory' if n.lower() in EXCLUDED_DIRS else 'reparse_reference_not_followed' if reparse or q.is_symlink() else None
                        if reason:
                            omitted.append({'source_path': str(q), 'reason': reason})
                        else:
                            safe_dirs.append(n)
                    except OSError as e:
                        errors.append({'source_path': str(q), 'error': str(e)})
                dirs[:] = safe_dirs
                for n in sorted(files):
                    q = directory / n
                    if not secure_path(q):
                        omitted.append({'source_path': str(q), 'reason': 'credential_file_not_opened'})
                        continue
                    try:
                        attrs = q.lstat()
                        if q.is_symlink() or getattr(attrs, 'st_file_attributes', 0) & getattr(stat, 'FILE_ATTRIBUTE_REPARSE_POINT', 0):
                            omitted.append({'source_path': str(q), 'reason': 'reparse_file_reference_not_opened'})
                            continue
                        s = q.stat()
                        if not stat.S_ISREG(s.st_mode):
                            continue
                        cat = category(q, p)
                        identity = (s.st_dev, s.st_ino)
                        if identity not in local_ids:
                            local_ids.add(identity)
                            identity_bytes += s.st_size
                        if identity not in unique_ids:
                            unique_ids.add(identity)
                            totals['within_final_unique_file_identity_bytes'] += s.st_size
                        ledger.write(json.dumps({'root_id': rid, 'source_path': str(q.absolute()), 'relative_path': q.relative_to(p).as_posix(), 'bytes': s.st_size, 'mtime_utc': utc(s.st_mtime), 'ctime_utc': utc(s.st_ctime), 'category': cat, 'filesystem_device': s.st_dev, 'filesystem_file_id': str(s.st_ino), 'original_filename': n}, ensure_ascii=False) + '\n')
                        cats[cat] += 1
                        cat_bytes[cat] += s.st_size
                        extensions[q.suffix.lower() or '[no_extension]'] += 1
                        local_carriers.update(carriers(n))
                        times.append(s.st_mtime)
                    except OSError as e:
                        errors.append({'source_path': str(q), 'error': str(e)})
            row.update(scan_status='complete_regular_file_metadata_stat_with_explicit_exclusions', files=sum(cats.values()), logical_path_bytes=sum(cat_bytes.values()), categories={k: {'files': cats[k], 'logical_path_bytes': cat_bytes[k]} for k in sorted(cats)}, extensions=dict(extensions), filename_counts={k: local_carriers[k] for k in sorted(CORE_NAMES | {'*.raw', '*.sse*', 'other_request_response_named_files'})}, earliest_file_mtime_utc=utc(min(times)) if times else None, latest_file_mtime_utc=utc(max(times)) if times else None, filesystem_identity_unique_files=len(local_ids), filesystem_identity_unique_file_bytes=identity_bytes)
            rows.append(row)
            totals['incremental_files'] += row['files']
            totals['incremental_logical_bytes'] += row['logical_path_bytes']
            filename_counts.update(local_carriers)
    union = known_paths | {norm(r['path']) for r in rows}
    totals['within_final_unique_file_identities'] = len(unique_ids)
    summary = {
        'schema_version': 'wrd-final-discovery-root-supplement-v7', 'measured_utc': datetime.now(timezone.utc).isoformat(),
        'roots': rows, 'totals': dict(totals), 'filename_counts': {k: filename_counts[k] for k in sorted(CORE_NAMES | {'*.raw', '*.sse*', 'other_request_response_named_files'})},
        'prior_known_address_count': len(known_paths), 'additional_address_count': len(rows), 'known_address_union_count': len(union),
        'primary_census_sha256_unchanged': hash_file(primary_file), 'additional_census_sha256_unchanged': hash_file(additional_file),
        'all_ledgers_combined_path_files': base['totals']['logical_path_files'] + extra['totals']['incremental_files'] + totals['incremental_files'],
        'all_ledgers_combined_path_bytes_without_content_dedup': base['totals']['logical_path_bytes'] + extra['totals']['incremental_logical_bytes'] + totals['incremental_logical_bytes'],
        'controlled_file_ledger': str(ledger_path.absolute()), 'scan_errors': errors, 'nontraversed_references': omitted,
        'limitations': ['Previous fifty-address and 119-address JSON files are unchanged. This is an additive metadata ledger.', 'No content or global physical-identity dedup across earlier ledgers is claimed; copied content remains separate storage.', 'Carrier counts describe files and may include snapshots/copies, not independent model sessions or SFT samples.', 'Discovery is evidence-scoped and may remain incomplete; no claim of exhaustive recovery.', 'No training admission, original SQLite contents, credentials, current ablation processes/containers, or unrelated user conversations were touched.'],
    }
    (out / 'FINAL_DISCOVERY_ROOTS.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'roots': len(rows), 'exists': sum(r['exists'] for r in rows), 'union': len(union), 'totals': dict(totals), 'carrier_counts': summary['filename_counts'], 'errors': len(errors)}, ensure_ascii=False))
    return summary


if __name__ == '__main__':
    run()
