"""Stat one explicitly identified Codex repair root and one exact external file.

The external C-side session is never opened, hashed, parsed, or searched. Its
directory is not enumerated. This is a metadata census, not training admission.
"""
from __future__ import annotations

import gzip
import json
import os
import stat
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from physical_census import DEFAULT_OUT, EXCLUDED_DIRS, category, hash_file, jread, norm, secure_path, utc
from additional_census import carriers, CORE_NAMES


ROOT = Path('D:/skillloop/output/20261023_codex_assisted_resource_repair')
EXACT_EXTERNAL = Path('C:/Users/22142/.codex/sessions/2026/10/23/rollout-2026-10-23T01-11-23-01a16469-7614-7e01-ba76-1ad2d9707177_01a16498-9504-7342-80c4-b714199ce710.jsonl')


def run(out=DEFAULT_OUT):
    frozen_paths = [out / n for n in ['PHYSICAL_ROOTS.json', 'ADDITIONAL_ORIGINAL_ROOTS.json', 'FINAL_DISCOVERY_ROOTS.json']]
    prior = [jread(p) for p in frozen_paths]
    known = [r for doc in prior for r in doc['roots']]
    keys = {norm(r['path']) for r in known}
    parent = next((r for r in known if norm(ROOT) == norm(r['path']) or norm(ROOT).startswith(norm(r['path']) + os.sep)), None)
    directory_ledger = out / 'controlled/ASSISTED_REPAIR_DIRECTORY_FILES.jsonl.gz'
    cats, sizes, names, ext = Counter(), Counter(), Counter(), Counter()
    errors, omitted = [], []
    with gzip.open(directory_ledger, 'wt', encoding='utf-8') as ledger:
        if ROOT.is_dir() and not parent:
            for base, dirs, files in os.walk(ROOT, followlinks=False, onerror=lambda e: errors.append({'source_path': str(e.filename), 'error': str(e)})):
                base = Path(base)
                keep = []
                for name in sorted(dirs):
                    p = base / name
                    try:
                        attrs = p.lstat()
                        if name.lower() in EXCLUDED_DIRS or p.is_symlink() or getattr(attrs, 'st_file_attributes', 0) & getattr(stat, 'FILE_ATTRIBUTE_REPARSE_POINT', 0):
                            omitted.append({'source_path': str(p), 'reason': 'credential_dependency_or_reparse_directory'})
                        else:
                            keep.append(name)
                    except OSError as e:
                        errors.append({'source_path': str(p), 'error': str(e)})
                dirs[:] = keep
                for name in sorted(files):
                    p = base / name
                    if not secure_path(p):
                        omitted.append({'source_path': str(p), 'reason': 'credential_file_not_opened'})
                        continue
                    try:
                        attrs = p.lstat()
                        if p.is_symlink() or getattr(attrs, 'st_file_attributes', 0) & getattr(stat, 'FILE_ATTRIBUTE_REPARSE_POINT', 0):
                            omitted.append({'source_path': str(p), 'reason': 'reparse_file_reference_not_followed'})
                            continue
                        s = p.stat()
                        if not stat.S_ISREG(s.st_mode):
                            continue
                        cat = category(p, ROOT)
                        ledger.write(json.dumps({'source_path': str(p.absolute()), 'relative_path': p.relative_to(ROOT).as_posix(), 'bytes': s.st_size, 'mtime_utc': utc(s.st_mtime), 'ctime_utc': utc(s.st_ctime), 'filesystem_device': s.st_dev, 'filesystem_file_id': str(s.st_ino), 'category': cat, 'scope': 'historical_Codex_assisted_resource_repair_directory_metadata'}, ensure_ascii=False) + '\n')
                        cats[cat] += 1
                        sizes[cat] += s.st_size
                        names.update(carriers(name))
                        ext[p.suffix.lower() or '[no_extension]'] += 1
                    except OSError as e:
                        errors.append({'source_path': str(p), 'error': str(e)})
    external = {'source_path': str(EXACT_EXTERNAL), 'scope': 'exact_external_original_session_file_stat_only', 'content_opened': False, 'content_hashed': False, 'parent_directory_enumerated': False}
    try:
        attrs = EXACT_EXTERNAL.lstat()
        external['exists'] = True
        external['is_reparse_point'] = bool(getattr(attrs, 'st_file_attributes', 0) & getattr(stat, 'FILE_ATTRIBUTE_REPARSE_POINT', 0))
        if external['is_reparse_point'] or EXACT_EXTERNAL.is_symlink():
            external['status'] = 'reparse_reference_not_followed'
        else:
            s = EXACT_EXTERNAL.stat()
            external.update(status='metadata_stat_complete', bytes=s.st_size, mtime_utc=utc(s.st_mtime), ctime_utc=utc(s.st_ctime), filesystem_device=s.st_dev, filesystem_file_id=str(s.st_ino), regular_file=stat.S_ISREG(s.st_mode))
    except OSError as e:
        external.update(exists=False, status='explicit_missing_or_inaccessible_file', error=str(e))
        errors.append({'source_path': str(EXACT_EXTERNAL), 'error': str(e)})
    external_ledger = out / 'controlled/ASSISTED_REPAIR_EXTERNAL_FILE_STAT.jsonl'
    external_ledger.write_text(json.dumps(external, ensure_ascii=False) + '\n', encoding='utf-8')
    directory = {'path': str(ROOT), 'exists': ROOT.is_dir(), 'role': 'historical_Codex_assisted_resource_repair', 'purpose': 'Explicitly identified extra Codex repair of legal-document-drafting; execution conditions are historical assistance and not presumed equivalent to native WRD maker.', 'coverage_parent': parent['path'] if parent else None, 'files': sum(cats.values()), 'logical_path_bytes': sum(sizes.values()), 'scan_status': 'complete_regular_file_metadata_stat' if ROOT.is_dir() and not parent else 'already_covered' if parent else 'explicit_missing_directory', 'categories': {k: {'files': cats[k], 'logical_path_bytes': sizes[k]} for k in sorted(cats)}, 'extensions': dict(ext), 'filename_counts': {k: names[k] for k in sorted(CORE_NAMES | {'*.raw', '*.sse*', 'other_request_response_named_files'})}}
    summary = {
        'schema_version': 'wrd-assisted-repair-original-source-stat-v7', 'measured_utc': datetime.now(timezone.utc).isoformat(),
        'roots': [directory], 'external_exact_file': external,
        'totals': {'incremental_directory_files': directory['files'], 'incremental_directory_logical_bytes': directory['logical_path_bytes'], 'external_exact_files': int(external.get('status') == 'metadata_stat_complete'), 'external_exact_file_bytes': external.get('bytes'), 'directory_and_external_single_file_kept_separate': True},
        'prior_known_directory_address_count': len(keys), 'known_directory_address_union_count': len(keys | {norm(ROOT)}),
        'frozen_prior_census_sha256': {p.name: hash_file(p) for p in frozen_paths},
        'directory_file_ledger': str(directory_ledger.absolute()), 'external_file_stat_ledger': str(external_ledger.absolute()),
        'scan_errors': errors, 'nontraversed_references': omitted,
        'limitations': ['The exact external C-side session file was stat-only: no body, hash, parsing, or parent-directory search.', 'Directory and external file are separate storage records; no content or semantic dedup is inferred.', 'Historical Codex assistance remains a separate execution condition and is not automatically admitted as native maker training.', 'No current ablation, SQLite content, credentials, or unrelated user sessions were touched.', 'Previous 174-address JSON ledgers remain unchanged; this is the last explicitly identified supplemental pointer, not an exhaustive-history claim.'],
    }
    (out / 'ASSISTED_REPAIR_SOURCE.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'directory_files': directory['files'], 'directory_bytes': directory['logical_path_bytes'], 'external_exists': external['exists'], 'external_bytes': external.get('bytes'), 'known_directory_union': summary['known_directory_address_union_count'], 'errors': len(errors)}, ensure_ascii=False))
    return summary


if __name__ == '__main__':
    run()
