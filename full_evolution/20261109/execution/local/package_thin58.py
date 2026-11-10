#!/usr/bin/env python3
"""Archive the staged native experiment and bind every returned byte."""
import argparse
import hashlib
import json
import zipfile
from pathlib import Path


def file_sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runs', type=Path, required=True)
    parser.add_argument('--selection', type=Path, required=True)
    parser.add_argument('--receipts', type=Path)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    roots = [('runs', args.runs.resolve())]
    if args.receipts:
        roots.append(('receipts', args.receipts.resolve()))
    target = args.out.resolve()
    sidecar = target.with_name(target.name + '.sha256')
    if target.exists() or sidecar.exists() or any(not p.is_dir() or target.is_relative_to(p) for _, p in roots):
        parser.error('Expected existing input directories and a fresh output outside them')
    if not args.selection.is_file():
        parser.error('Expected a frozen selection')

    entries = [('selection.json', args.selection)]
    for label, root in roots:
        for item in sorted(root.rglob('*')):
            if item.is_symlink() or (hasattr(item, 'is_junction') and item.is_junction()):
                parser.error(f'Unexpected link in {label}')
            if item.is_file():
                if item.name in {'local.json', 'upstream.json', 'model_local.json', 'model_upstream.json'}:
                    parser.error('Temporary model configuration must stay outside the return tree')
                entries.append((label + '/' + item.relative_to(root).as_posix(), item))

    stage_names = []
    for name, path in entries:
        if name.startswith('runs/') and '/stages/' in name and name.endswith('/producer_result.json'):
            stage_names.append(name)
    pins = []
    digests = {}
    with zipfile.ZipFile(target, 'x', compression=zipfile.ZIP_DEFLATED) as archive:
        for name, path in entries:
            digest = hashlib.sha256()
            with path.open('rb') as stream, archive.open(name, 'w', force_zip64=True) as member:
                while chunk := stream.read(1024 * 1024):
                    member.write(chunk)
                    digest.update(chunk)
            digests[name] = digest.hexdigest()
            pins.append(digests[name] + '  ' + name)
        manifest = json.dumps({'schema': 'wrd58-thin-pipeline-return-v1',
                               'stage_result_files': [{'path': n, 'sha256': digests[n]} for n in stage_names],
                               'independent_quality_judged': False}, indent=2) + '\n'
        archive.writestr('RETURN_MANIFEST.json', manifest)
        pins.append(hashlib.sha256(manifest.encode()).hexdigest() + '  RETURN_MANIFEST.json')
        archive.writestr('SHA256SUMS', '\n'.join(pins) + '\n')
    checksum = file_sha(target)
    with sidecar.open('x', encoding='ascii') as stream:
        stream.write(f'{checksum}  {target.name}\n')
    print(json.dumps({'sha256': checksum, 'members': len(entries) + 2, 'terminal_stages': len(stage_names)}))


if __name__ == '__main__':
    main()
