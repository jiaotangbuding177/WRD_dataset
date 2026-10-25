"""Refresh and verify exact publication bytes; no network, models or training."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess


def sha(p):
    h = hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda: f.read(1024 * 1024), b''):
            h.update(b)
    return h.hexdigest()


def save(p, x):
    p.write_text(json.dumps(x, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def main():
    root = Path(__file__).resolve().parents[3]
    repo = root / 'output/20261025_wrd_training_dataset/git_release'
    local = root / 'research/plans/20261025_wrd_fullchain_distillation'
    public = repo / 'plans/20261025_fullchain_distillation'
    dest = repo / 'fullchain/20261025'
    plan = json.loads((local / 'TRAINING_PLAN.json').read_text(encoding='utf-8'))
    assert plan['execution_authorized'] is False and plan['training_started'] is False
    assert plan['data_scope']['training_admission_manifest'] is None
    ledger = json.loads((local / 'DATA_LEDGER.json').read_text(encoding='utf-8'))
    for n, expected in ledger['source_reports_sha256'].items():
        assert sha(root / 'output/20261025_wrd_fullchain_reaudit' / n) == expected
    provenance = json.loads((local / 'PROVENANCE.json').read_text(encoding='utf-8'))
    for f in provenance['files']:
        p = local / f['path']
        f.update(sha256=sha(p), bytes=p.stat().st_size)
    provenance['research_source_head'] = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip()
    provenance['uncommitted_research_script_sha256'] = {
        p.name: sha(p) for p in sorted(Path(__file__).parent.glob('*.py'))}
    save(local / 'PROVENANCE.json', provenance)
    for p in local.iterdir():
        if p.suffix in {'.md', '.json'}:
            shutil.copy2(p, public / p.name)
    shutil.copy2(Path(__file__), dest / 'tooling/verify_release.py')
    manifest_path = dest / 'MANIFEST.json'
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    paths = [p for d in [dest, public] for p in d.rglob('*') if p.is_file() and p != manifest_path]
    paths += [repo / 'README.md', repo / 'TRAINING_ENTRYPOINT.json', repo / '.gitattributes']
    manifest['files'] = [{'path': str(p.relative_to(repo)).replace('\\', '/'), 'sha256': sha(p),
                          'bytes': p.stat().st_size} for p in sorted(paths)]
    save(manifest_path, manifest)
    for f in manifest['files']:
        p = repo / f['path']
        assert p.stat().st_size == f['bytes'] and sha(p) == f['sha256']
    for p in public.glob('*.json'):
        json.loads(p.read_text(encoding='utf-8-sig'))
    assert len(list(public.iterdir())) == 9
    print(json.dumps({'status': 'PASS_STATIC_BYTES_NOT_TRAINING_READINESS', 'manifest_payload_files': len(paths),
                      'manifest_sha256': sha(manifest_path), 'bytes': sum(x['bytes'] for x in manifest['files']),
                      'plan_files': 9, 'training_started': False}))


if __name__ == '__main__':
    main()
