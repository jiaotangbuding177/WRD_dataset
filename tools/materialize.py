"""Restore a logical archive subtree without using any original machine paths."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath


def materialize(bundle, prefix, output):
    bundle, output = Path(bundle).resolve(), Path(output).resolve()
    prefix = prefix.strip('/')
    if output.exists() and any(output.iterdir()):
        raise SystemExit('Destination must be empty: ' + str(output))
    output.mkdir(parents=True, exist_ok=True)
    count = 0
    with (bundle / 'archive/file_index.jsonl').open(encoding='utf-8') as f:
        for line in f:
            row = json.loads(line)
            logical = row['logical_path']
            if prefix and logical != prefix and not logical.startswith(prefix + '/'):
                continue
            relative = logical[len(prefix):].lstrip('/') if prefix else logical
            if not relative:
                relative = PurePosixPath(logical).name
            pp = PurePosixPath(relative)
            if pp.is_absolute() or '..' in pp.parts or any(':' in part for part in pp.parts):
                raise ValueError('Unsafe logical path: ' + relative)
            obj = (bundle / 'archive' / row['object']).resolve()
            if not obj.is_relative_to(bundle / 'archive/objects'):
                raise ValueError('Unsafe object path')
            raw = obj.read_bytes()
            if len(raw) != row['bytes'] or hashlib.sha256(raw).hexdigest() != row['sha256']:
                raise ValueError('Object integrity failure: ' + row['sha256'])
            target = output.joinpath(*pp.parts)
            if not target.resolve().is_relative_to(output):
                raise ValueError('Unsafe output path')
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)
            count += 1
    if count == 0:
        raise ValueError('No files match this logical prefix')
    return count


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--bundle', type=Path, required=True)
    p.add_argument('--prefix', default='', help='e.g. episodes/ep_ID/workspace or sources/conv_ID')
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    print(json.dumps({'restored_files': materialize(a.bundle, a.prefix, a.output)}))
