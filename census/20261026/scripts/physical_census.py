"""Read-only physical census of original WRD library evidence, without SFT admission.

Only project-scoped original roots and their recorded local path references are
inspected. SQLite files, containers, processes, and credentials are never opened.
Repeated filesystem copies, derived deliveries, and archive bodies stay separate.
"""
from __future__ import annotations

import argparse
import ctypes
import gzip
import hashlib
import json
import os
import re
import stat
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path


VERSION = 'wrd-raw-physical-census-v7'
PROJECT = Path('D:/skillloop')
RUNS = Path('E:/skillloop_runs')
DEFAULT_OUT = PROJECT / 'output/20261026_wrd_raw_census_v7'
DEFAULT_HISTORY = PROJECT / 'research/data_prep/wrd_training/resources/history_inventory.json'
EXCLUDED_DIRS = {'.git', '.claude', 'node_modules', '__pycache__', '.venv', 'venv', 'private', 'credentials', 'auth'}
EXCLUDED_FILES = {'.env', '.env.local', '.env.production', 'auth-profiles.json', 'model_credentials.json', 'backends.json', 'accounts.json', 'account-store.json'}
REFERENCE_KEYS = {'episode', 'episode_dir', 'event_file', 'consumer', 'entrypoint', 'service_dir', 'profile', 'outputs', 'source_bindings', 'legacy_output'}
META_HASH_NAMES = {'request.json', 'response.json', 'result.json', 'execution.json', 'usage.json', 'accounting.json', 'dispatch.json', 'native_events.jsonl', 'session_events.jsonl', 'events.jsonl', 'making.json', 'review.json', 'previous.json', 'sources.json', 'routes.json', 'reusable.json', 'source_receipt.json', 'episode_receipt.json', 'prompts.json', 'tools.json', 'session-branch.json', 'container_receipt.json'}
ARCHIVE_SUFFIXES = {'.zip', '.7z', '.tar', '.tgz', '.aes', '.enc'}


def jread(path):
    try:
        return json.loads(Path(path).read_text(encoding='utf-8-sig'))
    except (OSError, ValueError):
        return None


def utc(value):
    return datetime.fromtimestamp(value, timezone.utc).isoformat()


def norm(path):
    return str(Path(path).absolute()).lower()


def secure_path(path):
    p = Path(path)
    if any(x.lower() in EXCLUDED_DIRS for x in p.parts):
        return False
    if p.name.lower() in EXCLUDED_FILES or re.fullmatch(r'model_\d+\.json', p.name, re.I):
        return False
    return True


def references(value):
    """Extract only known path-bearing fields; never publish arbitrary JSON values."""
    if isinstance(value, dict):
        for key, item in value.items():
            if any(s in key.lower() for s in ('password', 'credential', 'secret', 'token', 'api_key')):
                continue
            if key in REFERENCE_KEYS and isinstance(item, str) and re.match(r'^[DE]:[\\/]', item, re.I):
                if secure_path(item):
                    yield key, item
            elif isinstance(item, (dict, list)):
                yield from references(item)
    elif isinstance(value, list):
        for item in value:
            yield from references(item)


def discover_roots(project=PROJECT, runs=RUNS, history=DEFAULT_HISTORY):
    roots = {}
    refs = []

    def add(path, role, reason, evidence):
        p = Path(path)
        if not secure_path(p):
            return
        key = norm(p)
        row = roots.setdefault(key, {'path': str(p.absolute()), 'role': role, 'purpose': reason, 'discovery_evidence': [], 'recursive_scan': role != 'evaluation_reference_only'})
        if role in {'primary_library_control_and_mirrors', 'primary_native_runtime_root', 'derived_category_library'}:
            row.update(role=role, purpose=reason)
        if evidence not in row['discovery_evidence']:
            row['discovery_evidence'].append(evidence)

    previous = jread(history) or {}
    for old in previous.get('roots', []):
        role = 'evaluation_reference_only' if old.get('role') == 'eval_excluded' else 'historical_library_original_root'
        add(old['path'], role, 'Address clue from previous inventory; existence and contents are newly measured.', str(history))
    add(project / 'output/workflow_library', 'primary_library_control_and_mirrors', 'Original 1107-conversation to 29-skill library control, feedback, mirrors, and deliveries.', 'user-specified original root')
    add(runs / 'workflow_library', 'primary_native_runtime_root', 'Original native attempts, workspace inputs/outputs, exported native trajectories, and channel8 events.', 'user-specified original root')
    for base in [project / 'output', runs]:
        if not base.is_dir():
            continue
        for p in sorted(base.iterdir()):
            if p.is_dir() and re.search(r'workflow.*library|wrd.*library|^w\d+(?:_controls)?$', p.name, re.I):
                if re.search(r'wrd250|wrd12_library', p.name, re.I):
                    role = 'evaluation_reference_only' if '250' in p.name else 'derived_category_library'
                else:
                    role = 'historical_library_original_root'
                add(p, role, 'Shallow project-scoped WRD library/runtime discovery; no unrelated user folders scanned.', 'fresh directory discovery: ' + str(base))

    original = project / 'output/workflow_library'
    ref_documents = [original / 'legacy_import.json', original / 'process_inventory.json', original / 'services/current.json']
    ref_documents.extend(original.glob('records/*/attempt_*/result.json'))
    for doc in ref_documents:
        value = jread(doc)
        if value is None:
            continue
        for key, text in references(value):
            p = Path(text)
            if not (norm(p).startswith(norm(project)) or norm(p).startswith(norm(runs))):
                continue
            refs.append({'field': key, 'source_path': str(p), 'pointer_document': str(doc), 'exists': p.exists()})
            # Retain the narrowest meaningful original service/runtime directory.
            if key == 'event_file':
                add(p.parent, 'original_provider_event_root', 'Actual native event_file recorded by original dispatch/result/service metadata.', str(doc))
            elif key == 'service_dir':
                add(p, 'shared_original_native_service_source', 'Original shared model service implementation, without dependency or credential stores.', str(doc))
            elif key == 'source_bindings':
                add(p.parent, 'original_learning_source_binding_root', 'Original library learning-source files and bindings.', str(doc))
            elif key == 'legacy_output':
                add(p, 'historical_library_original_root', 'Historical library parent explicitly linked by legacy_import.', str(doc))
            elif key in {'episode', 'episode_dir'} and p.exists():
                # Existing outer roots already include E attempts. D-side exact
                # zero-model/manual-restoration/preparation sources are retained.
                if not any(norm(p).startswith(k + os.sep) or norm(p) == k for k, r in roots.items() if r['recursive_scan']):
                    add(p, 'original_referenced_episode_directory', 'Actual episode_dir from original records; not inferred from training exports.', str(doc))

    values = sorted(roots.values(), key=lambda r: (len(Path(r['path']).parts), r['path'].lower()))
    chosen = []
    for row in values:
        row['exists'] = Path(row['path']).exists()
        row['root_id'] = 'root_' + hashlib.sha256(norm(row['path']).encode()).hexdigest()[:12]
        if row['recursive_scan']:
            parent = next((x for x in chosen if x['recursive_scan'] and norm(row['path']).startswith(norm(x['path']) + os.sep)), None)
            if parent:
                row['covered_by_root_id'] = parent['root_id']
                row['recursive_scan'] = False
            else:
                chosen.append(row)
    return values, refs


def category(path, root):
    rel = path.relative_to(root).as_posix().lower()
    bits = rel.split('/')
    name = path.name.lower()
    if path.suffix.lower() in ARCHIVE_SUFFIXES or name.endswith(('.tar.gz', '.jsonl.gz', '.json.gz')):
        return 'archive_or_compressed_body'
    if any(x.startswith(('delivery_', 'publish_staging')) for x in bits) or 'selected_followup_20261024/final/' in rel:
        return 'derived_delivery_or_packaging_copy'
    if any(x in {'confirmed_snapshots', 'skills', 'previous_skill', 'candidate', 'reusable', 'frozen', 'candidates'} for x in bits) or '/outputs/skill/' in '/' + rel:
        return 'skill_resource_version_or_package'
    if any(x in {'inputs', '_inputs', 'cache', 'recall_catalog', 'recall_materials', 'materials', 'recovered'} for x in bits):
        return 'workspace_input_or_copy_cache'
    if 'records' in bits and name in {'result.json', 'review.json', 'making.json'}:
        return 'host_record_result_or_feedback_mirror'
    if name in {'session_events.jsonl', 'session-branch.json'}:
        return 'native_session_transcript_source'
    if name in {'native_events.jsonl', 'interface_usage.jsonl', 'failure_wire.jsonl'}:
        return 'native_provider_usage_or_wire_events'
    if name in {'request.json', 'response.json', 'result.json', 'execution.json', 'dispatch.json', 'process.json'}:
        return 'original_episode_request_response_control'
    if name in {'making.json', 'review.json', 'previous.json'} or 'feedback' in name or 'review' in name:
        return 'original_feedback_making_or_decision'
    if 'openclaw_transport' in bits or name in {'usage.json', 'accounting.json'}:
        return 'native_trajectory_export_or_measurement'
    if 'sources' in bits or name in {'conversations.json', 'source_bindings.json', 'source_freeze.json'}:
        return 'original_learning_source_or_binding'
    if any(x in {'runtime_code'} or x.startswith('runtime_') for x in bits) or path.suffix.lower() in {'.py', '.js', '.mjs', '.cjs'}:
        return 'runtime_or_research_source_code'
    if any(x in {'outputs', 'making_samples'} for x in bits):
        return 'episode_generated_business_or_validation_artifact'
    if name.endswith(('.db', '.db-shm', '.db-wal', '.sqlite', '.sqlite3')):
        return 'sqlite_file_stat_only_not_opened'
    return 'original_library_metadata_or_other_file'


def allocated_size(path):
    if os.name != 'nt':
        return None
    api = ctypes.WinDLL('kernel32', use_last_error=True).GetCompressedFileSizeW
    api.argtypes = [ctypes.c_wchar_p, ctypes.POINTER(ctypes.c_ulong)]
    api.restype = ctypes.c_ulong
    high = ctypes.c_ulong(0)
    ctypes.set_last_error(0)
    low = api(str(path), ctypes.byref(high))
    error = ctypes.get_last_error()
    if low == 0xFFFFFFFF and error:
        return None
    return (high.value << 32) | (low & 0xFFFFFFFF)


def hash_file(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        while chunk := f.read(4 * 1024 * 1024):
            h.update(chunk)
    return h.hexdigest()


def finalize_index_summary(summary):
    """Validate accounting from the controlled path ledger without rereading files."""
    cats = defaultdict(lambda: {'files': 0, 'logical_path_bytes': 0})
    contexts = defaultdict(lambda: {'files': 0, 'logical_path_bytes': 0})
    checked = Counter()
    for line in gzip.open(summary['files_index'], 'rt', encoding='utf-8'):
        row = json.loads(line)
        checked['indexed_files'] += 1
        checked['indexed_logical_bytes'] += row['bytes']
        cat = cats[row['category']]
        cat['files'] += 1
        cat['logical_path_bytes'] += row['bytes']
        bits = row['relative_path'].lower().split('/')
        if any(x.startswith('delivery_') for x in bits) or 'publish_staging' in bits:
            context = 'derived_delivery_copy'
        elif 'inputs' in bits or '_inputs' in bits or 'cache' in bits:
            context = 'input_mount_or_cache_copy_context'
        elif row['category'] == 'archive_or_compressed_body':
            context = 'compressed_container_body'
        else:
            context = 'other_original_root_path'
        contexts[context]['files'] += 1
        contexts[context]['logical_path_bytes'] += row['bytes']
        if row.get('allocated_bytes') is None:
            checked['allocation_measurement_unavailable_files'] += 1
        else:
            checked['allocation_measured_files'] += 1
        if row.get('hash_stable_stat'):
            checked['stable_sha256_files'] += 1
            checked['stable_sha256_path_bytes'] += row['bytes']
    summary['category_totals'] = dict(cats)
    summary['copy_context_totals'] = dict(contexts)
    summary['file_ledger_validation'] = dict(checked)
    summary['file_ledger_validation']['logical_count_matches'] = checked['indexed_files'] == summary['totals']['logical_path_files']
    summary['file_ledger_validation']['logical_bytes_match'] = checked['indexed_logical_bytes'] == summary['totals']['logical_path_bytes']
    excluded_index = Path(summary['files_index']).parent / 'NONTRAVERSED_DIRECTORY_REFERENCES.jsonl.gz'
    excluded_counts = Counter()
    with gzip.open(excluded_index, 'wt', encoding='utf-8') as out:
        for spec in summary['roots']:
            if not spec.get('recursive_scan') or not Path(spec['path']).is_dir():
                continue
            for base, dirs, files in os.walk(spec['path'], followlinks=False):
                keep = []
                for name in dirs:
                    p = Path(base) / name
                    try:
                        attrs = p.lstat()
                        reparse = bool(getattr(attrs, 'st_file_attributes', 0) & getattr(stat, 'FILE_ATTRIBUTE_REPARSE_POINT', 0))
                        if name.lower() in EXCLUDED_DIRS:
                            reason = 'credential_dependency_or_runtime_cache_directory'
                        elif p.is_symlink() or reparse:
                            reason = 'reparse_reference_not_followed'
                        else:
                            keep.append(name)
                            continue
                        row = {'root_id': spec['root_id'], 'source_path': str(p.absolute()), 'reason': reason, 'is_reparse_point': reparse, 'is_symlink': p.is_symlink(), 'not_recursively_opened': True}
                        if reparse or p.is_symlink():
                            try:
                                row['reference_target'] = os.readlink(p)
                            except (OSError, ValueError):
                                row['reference_target'] = None
                        out.write(json.dumps(row, ensure_ascii=False) + '\n')
                        excluded_counts[reason] += 1
                    except OSError as e:
                        out.write(json.dumps({'root_id': spec['root_id'], 'source_path': str(p), 'reason': str(e), 'not_recursively_opened': True}, ensure_ascii=False) + '\n')
                        excluded_counts['stat_error'] += 1
                dirs[:] = keep
    summary['nontraversed_directory_references'] = {'path': str(excluded_index.absolute()), 'counts': dict(excluded_counts)}
    inventory_path = PROJECT / 'output/20261021_workflow_skill_library/inventory.json'
    declared = (jread(inventory_path) or {}).get('corpus', {})
    if declared.get('path'):
        source = Path(declared['path'])
        info = {'source_path': str(source), 'pointer_document': str(inventory_path), 'role': 'original_1107_conversation_corpus_reference_only', 'exists': source.is_file(), 'not_added_to_copy_root_totals': True}
        if source.is_file():
            s = source.stat()
            digest = hash_file(source)
            after = source.stat()
            info.update(bytes=s.st_size, mtime_utc=utc(s.st_mtime), sha256=digest, declared_bytes=declared.get('bytes'), declared_sha256=declared.get('sha256'), declared_size_and_sha_match=s.st_size == declared.get('bytes') and digest == declared.get('sha256'), hash_stable_stat=(s.st_size, s.st_mtime_ns) == (after.st_size, after.st_mtime_ns))
        summary['original_corpus_reference'] = info
    for row in summary['roots']:
        if norm(row['path']) == norm(PROJECT / 'output/workflow_library'):
            row['role'] = 'primary_library_control_and_mirrors'
        elif norm(row['path']) == norm(RUNS / 'workflow_library'):
            row['role'] = 'primary_native_runtime_root'
    summary['limitations'].append('File-role categories are transparent path/name classifications, not provenance or suitability judgments; source pointers and actual message lineage must establish semantic identity.')
    return summary


def scan(out, hash_mode='evidence', measure_allocated=False):
    out.mkdir(parents=True, exist_ok=True)
    controlled = out / 'controlled'
    controlled.mkdir(exist_ok=True)
    started = datetime.now(timezone.utc).isoformat()
    roots, refs = discover_roots()
    rows = []
    totals = Counter()
    seen_identities = set()
    hashed_content = {}
    exact_duplicates = Counter()
    errors = []
    exclusions = Counter()
    index_path = controlled / 'PHYSICAL_FILES.jsonl.gz'
    reference_path = controlled / 'ORIGINAL_PATH_REFERENCES.jsonl.gz'
    with gzip.open(reference_path, 'wt', encoding='utf-8') as f:
        for row in refs:
            f.write(json.dumps(row, ensure_ascii=False) + '\n')
    with gzip.open(index_path, 'wt', encoding='utf-8') as index:
        for spec in roots:
            source = Path(spec['path'])
            result = dict(spec)
            counts, sizes, ext_counts, ext_bytes = Counter(), Counter(), Counter(), Counter()
            first, last = None, None
            root_file_ids = set()
            root_identity_bytes = 0
            root_allocated_bytes = 0
            stable_hashes = 0
            if not spec['recursive_scan'] or not source.is_dir():
                result['scan_status'] = 'covered_by_parent' if spec.get('covered_by_root_id') else 'existence_only_no_recursive_scan'
                rows.append(result)
                continue
            print('SCAN', spec['root_id'], source, flush=True)
            for base, dirs, files in os.walk(source, followlinks=False, onerror=lambda e: errors.append({'source_path': str(e.filename), 'error': str(e)})):
                base = Path(base)
                safe_dirs = []
                for name in sorted(dirs):
                    p = base / name
                    try:
                        if name.lower() in EXCLUDED_DIRS or p.is_symlink() or p.stat().st_file_attributes & getattr(stat, 'FILE_ATTRIBUTE_REPARSE_POINT', 0):
                            exclusions['credential_dependency_or_reparse_directory'] += 1
                            continue
                    except OSError as e:
                        errors.append({'source_path': str(p), 'error': str(e)})
                        continue
                    safe_dirs.append(name)
                dirs[:] = safe_dirs
                for name in sorted(files):
                    p = base / name
                    if not secure_path(p):
                        exclusions['credential_file_not_opened'] += 1
                        continue
                    try:
                        s = p.stat()
                        if p.is_symlink() or not stat.S_ISREG(s.st_mode):
                            exclusions['non_regular_file'] += 1
                            continue
                        cat = category(p, source)
                        identity = (s.st_dev, s.st_ino) if s.st_ino else ('path_only', norm(p))
                        new_global_identity = identity not in seen_identities
                        if identity not in root_file_ids:
                            root_file_ids.add(identity)
                            root_identity_bytes += s.st_size
                        if new_global_identity:
                            seen_identities.add(identity)
                            totals['filesystem_identity_unique_file_bytes'] += s.st_size
                        disk_bytes = allocated_size(p) if measure_allocated else None
                        if disk_bytes is not None:
                            root_allocated_bytes += disk_bytes
                            if new_global_identity:
                                totals['allocated_bytes_unique_file_identities'] += disk_bytes
                        record = {
                            'root_id': spec['root_id'], 'source_path': str(p.absolute()),
                            'relative_path': p.relative_to(source).as_posix(),
                            'category': cat, 'bytes': s.st_size,
                            'mtime_utc': utc(s.st_mtime), 'ctime_utc': utc(s.st_ctime),
                            'filesystem_device': s.st_dev, 'filesystem_file_id': str(s.st_ino),
                            'filesystem_links': s.st_nlink, 'allocated_bytes': disk_bytes,
                        }
                        should_hash = hash_mode == 'all' or (hash_mode == 'evidence' and (name.lower() in META_HASH_NAMES or cat in {'skill_resource_version_or_package', 'original_learning_source_or_binding'}))
                        if should_hash and cat != 'sqlite_file_stat_only_not_opened':
                            digest = hash_file(p)
                            after = p.stat()
                            stable = (s.st_size, s.st_mtime_ns) == (after.st_size, after.st_mtime_ns)
                            record.update(sha256=digest, hash_stable_stat=stable)
                            if stable:
                                stable_hashes += 1
                                exact_duplicates[cat] += int(digest in hashed_content)
                                hashed_content.setdefault(digest, {'bytes': s.st_size, 'first_source_path': str(p.absolute()), 'category': cat})
                            else:
                                errors.append({'source_path': str(p), 'error': 'File changed during census hash; not a stable snapshot'})
                        index.write(json.dumps(record, ensure_ascii=False) + '\n')
                        counts[cat] += 1
                        sizes[cat] += s.st_size
                        ext = p.suffix.lower() or '[no_extension]'
                        ext_counts[ext] += 1
                        ext_bytes[ext] += s.st_size
                        first = s.st_mtime if first is None else min(first, s.st_mtime)
                        last = s.st_mtime if last is None else max(last, s.st_mtime)
                    except (OSError, ValueError) as e:
                        errors.append({'source_path': str(p), 'error': str(e)})
            result.update(
                scan_status='scanned_original_files_without_training_admission',
                files=sum(counts.values()), logical_path_bytes=sum(sizes.values()),
                filesystem_identity_unique_files=len(root_file_ids),
                filesystem_identity_unique_file_bytes=root_identity_bytes,
                allocated_bytes_sum=root_allocated_bytes if measure_allocated else None,
                categories={k: {'files': counts[k], 'logical_path_bytes': sizes[k]} for k in sorted(counts)},
                extensions={k: {'files': ext_counts[k], 'logical_path_bytes': ext_bytes[k]} for k in sorted(ext_counts)},
                stable_sha256_files=stable_hashes,
                earliest_file_mtime_utc=utc(first) if first is not None else None,
                latest_file_mtime_utc=utc(last) if last is not None else None,
            )
            rows.append(result)
            totals['logical_path_files'] += result['files']
            totals['logical_path_bytes'] += result['logical_path_bytes']
            print('DONE', spec['root_id'], result['files'], result['logical_path_bytes'], flush=True)
    unique = sum(x['bytes'] for x in hashed_content.values())
    summary = {
        'schema_version': VERSION, 'started_utc': started, 'finished_utc': datetime.now(timezone.utc).isoformat(),
        'purpose': 'Original WRD physical evidence census only; no training admission or replay.',
        'roots': rows, 'totals': dict(totals),
        'hash_policy': hash_mode,
        'hashed_subset_content_unique_files': len(hashed_content),
        'hashed_subset_content_unique_bytes': unique,
        'hashed_subset_duplicate_paths_by_category': dict(exact_duplicates),
        'files_index': str(index_path.absolute()), 'path_references': str(reference_path.absolute()),
        'credential_and_dependency_exclusions': dict(exclusions),
        'scan_errors': errors,
        'limitations': [
            'Logical bytes count paths including repeated copies; they are not unique original evidence bytes.',
            'Filesystem identity dedup uses volume/file ID and removes hardlink/path aliases, not copied content.',
            'Content uniqueness describes only the explicitly SHA256-hashed subset unless hash_policy=all.',
            'Native runtime exports, host mirrors, input caches, derived deliveries, and compressed archive bodies are separate categories and must not be summed as new independent data.',
            'SQLite contents, containers, active processes, credentials, and unrelated user folders were not opened or changed.',
            'Formal evaluation roots are address references only; no training screening is performed in this census.',
            'Source paths were enumerated at live filesystem time; unchanged stat around hashing is checked but does not substitute for an atomic experiment snapshot.',
            'No conclusion about model-training suitability follows from file counts, file names, or this physical census.',
        ],
    }
    (out / 'PHYSICAL_ROOTS.pre_finalization.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
    summary = finalize_index_summary(summary)
    (out / 'PHYSICAL_ROOTS.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
    return summary


def recover_closed_ledger(out):
    """Recover complete accounting after a finalizer exception, and re-stat roots.

    This never treats a truncated gzip ledger as complete. The closed gzip footer
    must verify and every scanned original-root metadata multiset must match a
    fresh read-only walk before the recovered census is considered complete.
    """
    controlled = out / 'controlled'
    index_path = controlled / 'PHYSICAL_FILES.jsonl.gz'
    roots, refs = discover_roots()
    expected = defaultdict(lambda: {'files': 0, 'bytes': 0, 'digest_sum': 0, 'categories': Counter(), 'sizes': Counter(), 'extensions': Counter(), 'extension_bytes': Counter(), 'file_ids': set(), 'identity_bytes': 0, 'first': None, 'last': None})
    global_ids = set()
    totals = Counter()
    content = {}
    modulus = 1 << 256

    def item_digest(path, size, file_id):
        return int(hashlib.sha256((norm(path) + '\0' + str(size) + '\0' + str(file_id)).encode()).hexdigest(), 16)

    with gzip.open(index_path, 'rt', encoding='utf-8') as f:
        for line in f:
            row = json.loads(line)
            one = expected[row['root_id']]
            size = row['bytes']
            one['files'] += 1
            one['bytes'] += size
            one['digest_sum'] = (one['digest_sum'] + item_digest(row['source_path'], size, row['filesystem_file_id'])) % modulus
            one['categories'][row['category']] += 1
            one['sizes'][row['category']] += size
            ext = Path(row['source_path']).suffix.lower() or '[no_extension]'
            one['extensions'][ext] += 1
            one['extension_bytes'][ext] += size
            identity = (row['filesystem_device'], row['filesystem_file_id'])
            if identity not in one['file_ids']:
                one['file_ids'].add(identity)
                one['identity_bytes'] += size
            if identity not in global_ids:
                global_ids.add(identity)
                totals['filesystem_identity_unique_file_bytes'] += size
            when = row['mtime_utc']
            one['first'] = min(one['first'], when) if one['first'] else when
            one['last'] = max(one['last'], when) if one['last'] else when
            if row.get('sha256') and row.get('hash_stable_stat'):
                content.setdefault(row['sha256'], size)
            totals['logical_path_files'] += 1
            totals['logical_path_bytes'] += size

    rows = []
    errors = []
    exclusions = Counter()
    for spec in roots:
        result = dict(spec)
        source = Path(spec['path'])
        if not spec['recursive_scan'] or not source.is_dir():
            result['scan_status'] = 'covered_by_parent' if spec.get('covered_by_root_id') else 'existence_only_no_recursive_scan'
            rows.append(result)
            continue
        print('VERIFY_STAT', spec['root_id'], source, flush=True)
        actual_count, actual_size, actual_digest = 0, 0, 0
        for base, dirs, files in os.walk(source, followlinks=False, onerror=lambda e: errors.append({'source_path': str(e.filename), 'error': str(e)})):
            base = Path(base)
            keep = []
            for name in sorted(dirs):
                p = base / name
                try:
                    if name.lower() in EXCLUDED_DIRS or p.is_symlink() or p.stat().st_file_attributes & getattr(stat, 'FILE_ATTRIBUTE_REPARSE_POINT', 0):
                        exclusions['credential_dependency_or_reparse_directory'] += 1
                        continue
                    keep.append(name)
                except OSError as e:
                    errors.append({'source_path': str(p), 'error': str(e)})
            dirs[:] = keep
            for name in sorted(files):
                p = base / name
                if not secure_path(p):
                    exclusions['credential_file_not_opened'] += 1
                    continue
                try:
                    s = p.stat()
                    if p.is_symlink() or not stat.S_ISREG(s.st_mode):
                        exclusions['non_regular_file'] += 1
                        continue
                    actual_count += 1
                    actual_size += s.st_size
                    actual_digest = (actual_digest + item_digest(p, s.st_size, str(s.st_ino))) % modulus
                except OSError as e:
                    errors.append({'source_path': str(p), 'error': str(e)})
        old = expected[spec['root_id']]
        matches = actual_count == old['files'] and actual_size == old['bytes'] and actual_digest == old['digest_sum']
        result.update(
            scan_status='scanned_and_closed_ledger_verified_against_original_stat' if matches else 'original_stat_changed_or_ledger_mismatch',
            files=old['files'], logical_path_bytes=old['bytes'],
            filesystem_identity_unique_files=len(old['file_ids']), filesystem_identity_unique_file_bytes=old['identity_bytes'],
            allocated_bytes_sum=None,
            categories={k: {'files': old['categories'][k], 'logical_path_bytes': old['sizes'][k]} for k in sorted(old['categories'])},
            extensions={k: {'files': old['extensions'][k], 'logical_path_bytes': old['extension_bytes'][k]} for k in sorted(old['extensions'])},
            earliest_file_mtime_utc=old['first'], latest_file_mtime_utc=old['last'],
            fresh_stat_verification={'files': actual_count, 'logical_path_bytes': actual_size, 'path_size_file_id_multiset_matches': matches},
        )
        if not matches:
            errors.append({'source_path': str(source), 'error': 'Fresh original-root stat multiset differs from completed file ledger'})
        rows.append(result)
    totals['filesystem_identity_unique_files'] = len(global_ids)
    summary = {
        'schema_version': VERSION, 'finished_utc': datetime.now(timezone.utc).isoformat(),
        'purpose': 'Original WRD physical evidence census only; no training admission or replay.',
        'roots': rows, 'totals': dict(totals), 'hash_policy': 'none',
        'hashed_subset_content_unique_files': len(content), 'hashed_subset_content_unique_bytes': sum(content.values()),
        'files_index': str(index_path.absolute()), 'path_references': str((controlled / 'ORIGINAL_PATH_REFERENCES.jsonl.gz').absolute()),
        'credential_and_dependency_exclusions': dict(exclusions), 'scan_errors': errors,
        'finalization_recovery': {'original_finalization_error': 'os.readlink on a Windows non-symlink reparse point raised ValueError after the complete file ledger had closed.', 'gzip_footer_verified': True, 'fresh_original_stat_walk_performed': True, 'all_scanned_root_metadata_multisets_match': all(r.get('fresh_stat_verification', {}).get('path_size_file_id_multiset_matches', True) for r in rows), 'partial_allocated_attempt_excluded_from_totals': True},
        'limitations': [
            'Logical path bytes include copies and caches and are not unique original text or independent training samples.',
            'Filesystem-identity dedup removes hardlink aliases only; equal copied content remains separate physical storage.',
            'No complete content-hash uniqueness is asserted; native core hashes are reported separately.',
            'Actual allocated disk bytes are not measured in the complete census. The slow partial allocated attempt remains explicitly incomplete and excluded.',
            'Directories marked credential/dependency/reparse references are not traversed; SQLite is stat-only and never opened.',
            'Formal evaluation roots are existence references only. No training admission was performed.',
            'A finalizer exception was corrected after the complete closed ledger; the original stat multiset was independently re-walked before publishing this recovered summary.',
        ],
    }
    summary = finalize_index_summary(summary)
    (out / 'PHYSICAL_ROOTS.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
    return summary


def evaluation_metadata_addendum(out):
    """Stat evaluation-support metadata separately, without any training gate.

    This does not change the frozen primary census grand totals. Full business
    workspaces and input caches are outside this narrowly described addendum.
    """
    main = jread(out / 'PHYSICAL_ROOTS.json')
    if not main:
        raise FileNotFoundError('Complete primary physical census must exist first')
    refs = [r for r in main['roots'] if r['role'] == 'evaluation_reference_only']
    names = [Path(r['path']).name.lower() for r in refs]
    control = PROJECT / 'output/workflow_library'
    proof_paths = [control / 'routes.json', control / 'legacy_import.json']
    proof_paths.extend(control.glob('records/*/attempt_*/input/previous.json'))
    proof_paths.extend(control.glob('records/*/attempt_*/input/review_input.json'))
    proof_paths.extend((control / 'selected_followup_20261024/final').glob('*review.json'))
    proof_paths.extend((control / 'skills').glob('*/references/*.md'))
    hits = []
    for p in proof_paths:
        try:
            text = p.read_text(encoding='utf-8-sig').lower()
            found = [n for n in names if n in text]
            if found:
                hits.append({'source_path': str(p.absolute()), 'evaluation_root_names': found})
        except OSError:
            pass
    suffixes = {'.json', '.jsonl', '.csv', '.tsv', '.md', '.log', '.txt'}
    entries, errors = [], []
    ledger = out / 'controlled/EVALUATION_METADATA_FILES.jsonl.gz'
    with gzip.open(ledger, 'wt', encoding='utf-8') as f:
        for root in refs:
            p = Path(root['path'])
            row = {'path': str(p), 'scope': 'evaluation_support_metadata_stat_only', 'training_admission_performed': False, 'files': 0, 'logical_metadata_bytes': 0, 'file_names': Counter(), 'workspace_and_input_caches_not_counted': True, 'causal_relation_to_original_29': 'No observed direct basename/path reference in the explicitly bounded original-control audit; not a universal semantic noninterference claim.'}
            if not p.is_dir():
                row['exists'] = False
                entries.append(row)
                continue
            row['exists'] = True
            for base, dirs, files in os.walk(p, followlinks=False):
                base = Path(base)
                keep = []
                for name in dirs:
                    q = base / name
                    try:
                        if name.lower() in EXCLUDED_DIRS | {'workspace', 'inputs', '_inputs', 'cache'} or q.is_symlink() or getattr(q.lstat(), 'st_file_attributes', 0) & getattr(stat, 'FILE_ATTRIBUTE_REPARSE_POINT', 0):
                            continue
                        keep.append(name)
                    except OSError as e:
                        errors.append({'source_path': str(q), 'error': str(e)})
                dirs[:] = keep
                for name in files:
                    q = base / name
                    if not secure_path(q) or q.suffix.lower() not in suffixes:
                        continue
                    try:
                        s = q.stat()
                        if q.is_symlink() or not stat.S_ISREG(s.st_mode):
                            continue
                        f.write(json.dumps({'root_path': str(p), 'source_path': str(q.absolute()), 'bytes': s.st_size, 'mtime_utc': utc(s.st_mtime), 'scope': row['scope'], 'formal_evaluation_metadata_not_training_data': True}, ensure_ascii=False) + '\n')
                        row['files'] += 1
                        row['logical_metadata_bytes'] += s.st_size
                        row['file_names'][name] += 1
                    except OSError as e:
                        errors.append({'source_path': str(q), 'error': str(e)})
            row['core_name_counts'] = {k: v for k, v in row.pop('file_names').items() if k in META_HASH_NAMES}
            entries.append(row)
    summary = {
        'schema_version': 'wrd-evaluation-support-metadata-addendum-v7',
        'roots': entries,
        'logical_metadata_files': sum(r['files'] for r in entries),
        'logical_metadata_bytes': sum(r['logical_metadata_bytes'] for r in entries),
        'not_merged_into_frozen_primary_totals': True,
        'controlled_metadata_ledger': str(ledger.absolute()),
        'bounded_original_control_reference_audit': {'files_examined': len(proof_paths), 'hit_files': hits, 'scopes': ['original routes/legacy_import', 'recorded previous/review_input', 'final29 reviews', 'current skill reference notes']},
        'errors': errors,
        'interpretation': 'Evaluation isolation prohibits training use, not address/metadata counting. These metadata counts describe separate formal-task validation/comparison support, not new maker examples or proof of no causal connection. Light/interface repair variants are a later resource-evolution branch and remain explicitly identified.',
    }
    summary['primary_census_sha256_unchanged'] = hash_file(out / 'PHYSICAL_ROOTS.json')
    purposes = {
        'w16light_1024': 'Native runtime for sixteen later formal-task WRD light-repair validations; counterpart output/20261024_wrd16_light_two_arm.',
        'wrd6if_1024': 'Native runtime for six later formal-task WRD interface-repair validations; counterpart output/20261024_wrd6_interface_retry.',
        '20261024_eval33_two_arm': 'Separate revised formal250 tasks, 29 new no-skill/WRD pairs and four reused pairs; protocol states original nine-channel library queue unchanged.',
        '20261024_eval6_two_arm': 'Separate six-task formal evaluation comparison of no-skill and fixed WRD skills; distinct runtime/ports from original library.',
        '20261024_modified20_as_ts': 'AutoSkills/Trace2Skills baseline re-evaluation on twenty modified formal tasks; not new WRD maker activity.',
        '20261024_wrd16_light_two_arm': 'Later formal-task WRD light-repaired resource branch, sixteen new WRD validations with historical baselines reused.',
        '20261024_wrd250_library_run': 'Formal250 WRD consumption evaluation: 35 reused directional results plus 215 new category-library sessions.',
        '20261024_wrd6_interface_retry': 'Later interface-corrected WRD branch: six formal-task validations and eighteen reference runs reused.',
    }
    for row in summary['roots']:
        row['purpose'] = purposes.get(Path(row['path']).name, 'Later evaluation-support branch')
    (out / 'EVALUATION_BRANCH_ROOTS.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
    return summary


def d_v10_supplement(out):
    """Stat the QA-discovered D-side v10 root without altering frozen totals."""
    primary_path = out / 'PHYSICAL_ROOTS.json'
    primary = jread(primary_path)
    source = PROJECT / 'output/20261021_v10_reuse_iterations'
    known = {norm(r['path']) for r in primary['roots']}
    source_primary_overlap = [r['path'] for r in primary['roots'] if norm(source) == norm(r['path']) or norm(source).startswith(norm(r['path']) + os.sep)]
    ledger = out / 'controlled/D_V10_FILES.jsonl.gz'
    counts, sizes, extensions = Counter(), Counter(), Counter()
    errors, omitted = [], Counter()
    file_ids = set()
    identity_bytes = 0
    times = []
    with gzip.open(ledger, 'wt', encoding='utf-8') as f:
        for base, dirs, files in os.walk(source, followlinks=False, onerror=lambda e: errors.append({'source_path': str(e.filename), 'error': str(e)})):
            base = Path(base)
            keep = []
            for name in dirs:
                p = base / name
                try:
                    if name.lower() in EXCLUDED_DIRS or p.is_symlink() or getattr(p.lstat(), 'st_file_attributes', 0) & getattr(stat, 'FILE_ATTRIBUTE_REPARSE_POINT', 0):
                        omitted['credential_dependency_or_reparse_directory'] += 1
                        continue
                    keep.append(name)
                except OSError as e:
                    errors.append({'source_path': str(p), 'error': str(e)})
            dirs[:] = keep
            for name in files:
                p = base / name
                if not secure_path(p):
                    omitted['credential_file_not_opened'] += 1
                    continue
                try:
                    s = p.stat()
                    if p.is_symlink() or not stat.S_ISREG(s.st_mode):
                        continue
                    cat = category(p, source)
                    identity = (s.st_dev, s.st_ino)
                    if identity not in file_ids:
                        file_ids.add(identity)
                        identity_bytes += s.st_size
                    row = {'source_path': str(p.absolute()), 'relative_path': p.relative_to(source).as_posix(), 'bytes': s.st_size, 'mtime_utc': utc(s.st_mtime), 'ctime_utc': utc(s.st_ctime), 'category': cat, 'filesystem_device': s.st_dev, 'filesystem_file_id': str(s.st_ino), 'scope': 'QA_discovered_D_v10_original_root_stat_only', 'training_admission_performed': False}
                    f.write(json.dumps(row, ensure_ascii=False) + '\n')
                    counts[cat] += 1
                    sizes[cat] += s.st_size
                    extensions[p.suffix.lower() or '[no_extension]'] += 1
                    times.append(s.st_mtime)
                except OSError as e:
                    errors.append({'source_path': str(p), 'error': str(e)})
    shallow = []
    # Directory names are a coverage check, not a claim these branches are all
    # independent sources or all relevant to the original 29-skill construction.
    for p in sorted((PROJECT / 'output').iterdir()):
        if not p.is_dir() or not re.search(r'workflow.*library|^20261021_v\d+_|wrd.*generation', p.name, re.I):
            continue
        info = {'path': str(p.absolute()), 'exists': True, 'in_frozen_primary_50_addresses': norm(p) in known, 'new_discovery_only_not_added_to_primary_totals': norm(p) not in known, 'scope': 'shallow_directory_name_and_direct_metadata_references_only'}
        direct_meta = []
        path_refs = []
        for q in sorted(p.glob('*.json')):
            if not secure_path(q):
                continue
            direct_meta.append({'source_path': str(q.absolute()), 'bytes': q.stat().st_size})
            if q.stat().st_size > 2_000_000:
                continue
            value = jread(q)
            if value is None:
                continue
            for key, target in references(value):
                if norm(target).startswith(norm(PROJECT / 'output')) or norm(target).startswith(norm(RUNS)):
                    path_refs.append({'field': key, 'source_path': target, 'pointer_document': str(q.absolute()), 'exists': Path(target).exists()})
        info['direct_json_metadata'] = direct_meta
        info['recorded_runtime_or_source_path_references'] = path_refs
        shallow.append(info)
    missing_versions = [{'path': str(PROJECT / f'output/20261021_workflow_library_v{n}'), 'exists': (PROJECT / f'output/20261021_workflow_library_v{n}').exists()} for n in [1, 3, 5, 6]]
    summary = {
        'schema_version': 'wrd-physical-D-v10-supplement-v7',
        'source_path': str(source), 'exists': source.is_dir(), 'additional_confirmed_root_number': 51,
        'relationship_to_E_same_name': 'Separate D/E roots, neither is a parent of the other; copied content equivalence has not been asserted.',
        'primary_root_coverage_hits': source_primary_overlap,
        'primary_census_sha256_unchanged': hash_file(primary_path),
        'not_merged_into_frozen_primary_totals': True,
        'files': sum(counts.values()), 'logical_path_bytes': sum(sizes.values()),
        'filesystem_identity_unique_files': len(file_ids), 'filesystem_identity_unique_file_bytes': identity_bytes,
        'categories': {k: {'files': counts[k], 'logical_path_bytes': sizes[k]} for k in sorted(counts)},
        'extensions': dict(extensions), 'errors': errors, 'exclusions': dict(omitted),
        'earliest_file_mtime_utc': utc(min(times)) if times else None,
        'latest_file_mtime_utc': utc(max(times)) if times else None,
        'controlled_file_ledger': str(ledger.absolute()),
        'shallow_same_batch_directory_discovery': shallow,
        'new_shallow_candidate_directories_not_in_primary50': sum(not r['in_frozen_primary_50_addresses'] for r in shallow),
        'explicit_missing_version_name_checks': missing_versions,
        'limitations': [
            'The frozen first fifty addresses did not cover this D-side v10 root; the omission is corrected explicitly, not hidden.',
            'Additional v11-v35 and earlier generation branch names are address clues only and have not been recursively counted in this supplement.',
            'No claim that all historical WRD iterations or all intermediate evidence has now been recovered.',
            'Only metadata/stat and direct recorded path references were inspected; no model, SQLite, current ablation, or credential store was touched.',
            'File/path byte totals remain storage measures containing possible copies, not supervised data or training-suitability counts.',
        ],
    }
    (out / 'D_V10_SUPPLEMENT.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
    return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=DEFAULT_OUT)
    parser.add_argument('--hash-content', choices=['none', 'evidence', 'all'], default='evidence')
    parser.add_argument('--allocated', action='store_true')
    parser.add_argument('--recover-closed-ledger', action='store_true')
    parser.add_argument('--evaluation-metadata-addendum', action='store_true')
    parser.add_argument('--d-v10-supplement', action='store_true')
    args = parser.parse_args()
    if args.d_v10_supplement:
        result = d_v10_supplement(args.out)
        print(json.dumps({'output': str(args.out / 'D_V10_SUPPLEMENT.json'), 'files': result['files'], 'bytes': result['logical_path_bytes'], 'new_shallow_candidates': result['new_shallow_candidate_directories_not_in_primary50'], 'errors': len(result['errors'])}, ensure_ascii=False))
    elif args.evaluation_metadata_addendum:
        result = evaluation_metadata_addendum(args.out)
        print(json.dumps({'output': str(args.out / 'EVALUATION_BRANCH_ROOTS.json'), 'roots': len(result['roots']), 'files': result['logical_metadata_files'], 'bytes': result['logical_metadata_bytes'], 'errors': len(result['errors'])}, ensure_ascii=False))
    else:
        result = recover_closed_ledger(args.out) if args.recover_closed_ledger else scan(args.out, args.hash_content, args.allocated)
        print(json.dumps({'output': str(args.out / 'PHYSICAL_ROOTS.json'), 'roots': len(result['roots']), 'totals': result['totals'], 'errors': len(result['scan_errors'])}, ensure_ascii=False))
