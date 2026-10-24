"""Preserve later deployment/interface variants outside primary training data."""
import argparse
import hashlib
import json
from pathlib import Path

from build import sanitized_bytes, write_json


def preserve(root, bundle):
    root, bundle = Path(root), Path(bundle)
    output = bundle / 'quarantine/late_skill_versions'
    if output.exists() and any(output.iterdir()):
        raise ValueError('Late-version output already exists; preserve previous delivery')
    rows = []
    variants = [('category_library29', '20261024_wrd12_library'), ('light_repair8', '20261024_wrd_light_repair'), ('interface_repair4', '20261024_wrd_interface_repair')]
    for label, directory in variants:
        source = root / 'output' / directory
        files = list((source / 'skills').rglob('*'))
        if label == 'category_library29':
            files += [source / n for n in ['README.md', 'manifest.json', 'libraries.json', 'protocol_libraries.json', 'validation.json']]
        for p in files:
            if not p.is_file() or p.is_symlink() or '__pycache__' in p.parts:
                continue
            raw = p.read_bytes()
            data, changed = sanitized_bytes(p, raw)
            target = output / label / p.relative_to(source)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
            rows.append({'file': target.relative_to(bundle).as_posix(), 'source_path': str(p), 'source_sha256': hashlib.sha256(raw).hexdigest(), 'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data), 'credential_redacted': changed, 'training_split': 'quarantine', 'primary_sft_eligible': False})
    report = {'schema': 'wrd-late-variant-inventory-v1', 'files': rows, 'policy': 'Later manual deployment/interface variants may incorporate known formal-evaluation feedback; preserve as version evidence, never mix into primary builder SFT or blind test labels. They are not new independent skills or native teacher trajectories.', 'new_model_calls': 0}
    write_json(output / 'manifest.json', report)
    print(json.dumps({'late_variant_files': len(rows), 'primary_sft_eligible': False}), flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', type=Path, default=Path('D:/skillloop'))
    p.add_argument('--bundle', type=Path, required=True)
    a = p.parse_args()
    preserve(a.root, a.bundle)
