"""Incremental v6 remote readback using the previously verified Git/LFS cache.

Invoked explicitly only after the parent pushes --commit. No keys or plaintext
archives are accessed, no model/agent loop is started, no training is possible.
"""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def main():
    path = ROOT / 'research/data_prep/wrd_reasoning_v5/verify_release.py'
    spec = importlib.util.spec_from_file_location('prior_incremental_git_verifier', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.OUT = ROOT / 'output/20261026_wrd_lineage_v6'
    module.OLD_RECEIPT = ROOT / 'output/20261026_wrd_strict226_expansion/REMOTE_GIT_VERIFICATION.json'
    module.REPORT = module.OUT / 'REMOTE_GIT_VERIFICATION.json'
    module.PROGRESS = module.OUT / 'REMOTE_GIT_VERIFICATION_PROGRESS.json'
    module.NEW_PREFIX = 'reasoning/20261026_lineage_v6/'
    module.LFS_INCLUDE = module.NEW_PREFIX + '**'
    module.main()


if __name__ == '__main__':
    main()
