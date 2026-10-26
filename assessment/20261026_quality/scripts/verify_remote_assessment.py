"""Read back the explicitly pushed v8 report and every real LFS object."""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--commit', required=True)
    parser.add_argument('--project-root', type=Path, default=Path(__file__).resolve().parents[3])
    args = parser.parse_args()
    root = args.project_root.resolve()
    shared = root / 'research/data_prep/wrd_raw_census_v7/verify_remote_index.py'
    if not shared.is_file():
        shared = Path(__file__).with_name('shared_v7_verify_remote_index.py')
    spec = importlib.util.spec_from_file_location('wrd_remote_readback', shared)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.ROOT = root
    module.LOCAL = root / 'output/20261025_wrd_training_dataset/git_release'
    module.OUT = root / 'output/20261026_wrd_quality_v8'
    module.V4 = root / 'output/20261025_wrd_reasoning_recovery_v4'
    module.BARE = module.V4 / 'outputv4remote_verify.git'
    module.CACHE = module.V4 / 'outputv4remote_lfs_empty'
    module.PREFIX = 'assessment/20261026_quality/'
    module.PRIOR = '16446172f0828c639eb1eba10e22630910ca4def'
    module.verify(args.commit)
    receipt_path = module.OUT / 'REMOTE_GIT_VERIFICATION.json'
    receipt = json.loads(receipt_path.read_text(encoding='utf-8'))
    receipt['schema_version'] = 'wrd-v8-remote-quality-assessment-readback'
    receipt['new_SFT_compilation_completed'] = False
    receipt_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
