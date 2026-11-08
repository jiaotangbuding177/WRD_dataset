#!/usr/bin/env python3
"""Archive existing maker attempts, artifacts, traces and costs without reruns."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import zipfile


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runs', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--selection', type=Path)
    parser.add_argument('--receipts', type=Path)
    args = parser.parse_args(argv)
    root = args.runs.resolve()
    if not root.is_dir() or args.out.exists() or Path(str(args.out) + '.sha256').exists():
        parser.error('Expected existing runs and a fresh output/sha256 path')
    if args.out.resolve().is_relative_to(root):
        parser.error('The return archive must be outside its input runs tree')
    files = []
    for label, directory in [('runs', root), ('receipts', args.receipts.resolve() if args.receipts else None)]:
        if directory is None:
            continue
        if not directory.is_dir():
            parser.error('Receipt directory does not exist')
        for path in sorted(directory.rglob('*')):
            if path.is_symlink():
                parser.error('Symlink in return tree; retain its original evidence and review it explicitly')
            if path.is_file():
                if path.name in ('model_local.json', 'model_upstream.json', 'local.json', 'upstream.json'):
                    parser.error('Credential-like temporary configuration found in evidence tree')
                files.append((label + '/' + path.relative_to(directory).as_posix(), path))
    if args.selection:
        files.append(('selection.json', args.selection.resolve()))
    rows = []
    for path in sorted(root.glob('*/*/attempt-*/producer_result.json')):
        value = json.loads(path.read_text(encoding='utf-8'))
        rows.append({'path': path.relative_to(root).as_posix(), 'arm': value.get('arm'),
                     'returncode': value.get('returncode'), 'artifact_status': value.get('artifact_status'),
                     'quality_judged': False})
    manifest = {'schema': 'wrd58-corpus-return-v1', 'attempt_results': rows,
                'status': 'EVIDENCE_ONLY_REQUIRES_ARTIFACT_REVIEW', 'producer_count': len(rows),
                'model_calls_from_packaging': 0, 'training_from_packaging': 0}
    pins = []
    with zipfile.ZipFile(args.out, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for name, path in files:
            blob = path.read_bytes()
            archive.writestr(name, blob)
            pins.append(hashlib.sha256(blob).hexdigest() + '  ' + name)
        blob = (json.dumps(manifest, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
        archive.writestr('RETURN_MANIFEST.json', blob)
        pins.append(hashlib.sha256(blob).hexdigest() + '  RETURN_MANIFEST.json')
        archive.writestr('SHA256SUMS', '\n'.join(pins) + '\n')
    with args.out.open('rb') as stream:
        checksum = hashlib.file_digest(stream, 'sha256').hexdigest()
    Path(str(args.out) + '.sha256').write_text(checksum + '  ' + args.out.name + '\n', encoding='utf-8')
    print(json.dumps({'archive': str(args.out), 'sha256': checksum,
                      'files': len(files) + 2, 'producer_results': len(rows)}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
