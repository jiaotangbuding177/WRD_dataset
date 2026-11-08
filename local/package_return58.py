#!/usr/bin/env python3
"""Package existing WRD58 producer evidence without running a model or a tool host."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
import sys
import zipfile


ARMS = tuple(f'wrd58-{size}-{step}' for size in ('8b', '14b') for step in (0, 26, 241))
METADATA_NAMES = ('RUN_SUMMARY.md', 'RETURN_FILLED.json', 'RETURN_RECEIPT.json',
                  'RETURN_TEMPLATE.filled.json', 'CANDIDATE_STATUS.json')
FIXED_TIME = (1980, 1, 1, 0, 0, 0)


def checked_stat(path):
    info = path.lstat()
    if (stat.S_ISLNK(info.st_mode)
            or getattr(info, 'st_file_attributes', 0) & 0x400):
        raise ValueError(f'Symlink or reparse point is not allowed: {path}')
    if not (stat.S_ISREG(info.st_mode) or stat.S_ISDIR(info.st_mode)):
        raise ValueError(f'Non-regular entry is not allowed: {path}')
    return info


def collect(path, package_root):
    info = checked_stat(path)
    if stat.S_ISREG(info.st_mode):
        relative = path.relative_to(package_root)
        if relative.is_absolute() or any(part in ('', '.', '..') for part in relative.parts):
            raise ValueError(f'Unsafe archive path: {relative}')
        return [(relative.as_posix(), path)]
    files = []
    for child in sorted(path.iterdir(), key=lambda value: value.name):
        files.extend(collect(child, package_root))
    return files


def optional_path(path):
    # lexists also notices dangling symlinks, which must be rejected, not ignored.
    return os.path.lexists(path)


def zip_info(name):
    value = zipfile.ZipInfo(name, FIXED_TIME)
    value.create_system = 3
    value.external_attr = (stat.S_IFREG | 0o644) << 16
    value.compress_type = zipfile.ZIP_DEFLATED
    return value


def read_json(path):
    try:
        checked_stat(path)
        return json.loads(path.read_text(encoding='utf-8-sig'))
    except (OSError, ValueError) as error:
        return {'_read_error': type(error).__name__}


def arm_summary(package_root, arm, budget_profile='standard'):
    producers = 'producers_mini' if budget_profile == 'mini' else 'producers'
    attempt = package_root / 'local/dev_pilot' / producers / arm
    result_path = attempt / 'producer_result.json'
    result = read_json(result_path) if result_path.is_file() else {}
    skill = attempt / 'workspace/outputs/skill'
    has_skill = (skill / 'SKILL.md').is_file()
    candidate_file = package_root / 'CANDIDATE_STATUS.json'
    candidate = read_json(candidate_file).get('arms', {}).get(arm, {}) if candidate_file.is_file() else {}
    if '_read_error' in result:
        status = 'RESULT_UNREADABLE'
    elif not result_path.is_file():
        status = 'HELD_BY_PROTOCOL' if candidate.get('status') == 'HOLD' else 'NOT_REPORTED'
    elif result.get('returncode') == 0:
        status = 'PROCESS_EXIT_0_UNREVIEWED'
    else:
        status = 'PROCESS_FAILED'
    return {
        'arm': arm, 'budget_profile': budget_profile,
        'execution_status': status, 'returncode': result.get('returncode'),
        'skill_md_present': has_skill,
        'skill_file_count': len(collect(skill, package_root)) if skill.is_dir() else 0,
        'result_path': result_path.relative_to(package_root).as_posix(),
        'quality_verdict': 'REVIEW_PENDING',
        'candidate_gate': candidate.get('status'), 'hold_reason': candidate.get('reason'),
    }


def build_archive(package_root, out):
    package_root = Path(package_root).absolute()
    out = Path(out).absolute()
    sidecar = Path(str(out) + '.sha256')
    checked_stat(package_root)
    if not out.parent.is_dir():
        raise ValueError('Output parent directory must already exist')
    checked_stat(out.parent)
    if optional_path(out):
        raise ValueError('Output already exists; choose a new file name')
    if optional_path(sidecar):
        raise ValueError('Output SHA256 sidecar already exists; choose a new file name')

    # These explicit roots never select global environment, credential or consumer trees.
    roots = ('local/dev_pilot/producers', 'local/dev_pilot/producers_mini', 'local/dev_pilot/stage_receipt.json',
             'local/spark_receipts', 'local/runs', 'local/diagnostic_evidence')
    optional = list(roots)
    optional.extend(path.relative_to(package_root).as_posix()
                    for path in sorted((package_root / 'local/dev_pilot').glob('stage_receipt.before241.*.json')))
    optional.extend(METADATA_NAMES)
    optional.extend('local/' + name for name in METADATA_NAMES)
    selected, missing = [], []
    for name in optional:
        source = package_root / name
        if not optional_path(source):
            missing.append(name)
            continue
        if out == source or source in out.parents:
            raise ValueError('Output must be outside all selected evidence paths')
        # Check ancestors too so a junction at local/ or dev_pilot/ cannot escape.
        for parent in reversed(source.parents):
            if parent == package_root or package_root in parent.parents:
                checked_stat(parent)
        selected.extend(collect(source, package_root))
    selected = sorted(dict(selected).items())
    summaries = [arm_summary(package_root, arm) for arm in ARMS]
    mini_summaries = [arm_summary(package_root, arm, 'mini') for arm in ARMS
                      if arm.endswith('-241') or (package_root / 'local/dev_pilot/producers_mini' / arm).exists()]
    producer_files = sum(name.startswith(('local/dev_pilot/producers/', 'local/dev_pilot/producers_mini/'))
                         for name, _ in selected)
    manifest = {
        'schema': 'wrd58-producer-return-package-v1',
        'scope': 'skills_generation_only', 'consumer_runs': 0,
        'arms': summaries, 'mini_arms': mini_summaries, 'missing_optional_paths': missing,
        'evidence_file_count': len(selected),
        'producer_evidence_file_count': producer_files,
        'package_status': 'PRODUCER_EVIDENCE_PRESENT_REVIEW_PENDING' if producer_files else 'NO_PRODUCER_EVIDENCE',
        'pending_arms': [row['arm'] for row in summaries if row['execution_status'] == 'NOT_REPORTED'],
        'pending_mini_arms': [row['arm'] for row in mini_summaries if row['execution_status'] == 'NOT_REPORTED'],
        'cost_source': 'Preserved producer_result.json, budget.json and model_http receipts; no estimates added',
        'quality_note': 'A zero process exit code is not a package quality verdict',
    }
    hashes = []
    # Exclusive creation prevents overwriting any existing output.
    with out.open('xb') as target:
        with zipfile.ZipFile(target, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
            for name, source in selected:
                before = checked_stat(source)
                digest = hashlib.sha256()
                with source.open('rb') as handle:
                    opened = os.fstat(handle.fileno())
                    if (opened.st_dev, opened.st_ino) != (before.st_dev, before.st_ino):
                        raise ValueError(f'File changed before reading: {name}')
                    with archive.open(zip_info(name), 'w') as dest:
                        for chunk in iter(lambda: handle.read(1024 * 1024), b''):
                            digest.update(chunk)
                            dest.write(chunk)
                    after = os.fstat(handle.fileno())
                    if (after.st_size, after.st_mtime_ns) != (before.st_size, before.st_mtime_ns):
                        raise ValueError(f'File changed while reading: {name}')
                hashes.append(f'{digest.hexdigest()}  {name}')
            manifest_bytes = (json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2) + '\n').encode('utf-8')
            archive.writestr(zip_info('RETURN_PACKAGE_MANIFEST.json'), manifest_bytes)
            hashes.append(f'{hashlib.sha256(manifest_bytes).hexdigest()}  RETURN_PACKAGE_MANIFEST.json')
            archive.writestr(zip_info('SHA256SUMS.txt'), ('\n'.join(sorted(hashes)) + '\n').encode('utf-8'))
    archive_hash = hashlib.sha256()
    with out.open('rb') as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b''):
            archive_hash.update(chunk)
    archive_sha256 = archive_hash.hexdigest()
    with sidecar.open('x', encoding='ascii', newline='\n') as handle:
        handle.write(archive_sha256 + '\n')
    return {**manifest, 'archive_sha256': archive_sha256, 'sha256_file': str(sidecar)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', required=True, type=Path, help='New ZIP file; parent directory must exist')
    args = parser.parse_args()
    try:
        result = build_archive(Path(__file__).resolve().parent.parent, args.out)
    except (OSError, ValueError, zipfile.BadZipFile) as error:
        print(f'{type(error).__name__}: {error}', file=sys.stderr)
        return 1
    print(json.dumps({'output': str(args.out.absolute()), **result}, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
