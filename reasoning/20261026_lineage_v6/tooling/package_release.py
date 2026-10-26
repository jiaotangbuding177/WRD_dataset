"""Package finalized positive process data and complete v6 evidence, no training.

Requires the independent final QA receipt and a non-pending compiled manifest.
Does not run Git, any old executor, or a model. Keys stay outside the checkout.
"""
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import shutil
import tarfile

ROOT = Path(__file__).resolve().parents[3]
AUDIT = ROOT / 'output/20261026_wrd_lineage_v6'
SEQ = ROOT / 'output/20261026_wrd_sequences_v6'
RELEASE = ROOT / 'output/20261025_wrd_training_dataset/git_release'
DEST = RELEASE / 'reasoning/20261026_lineage_v6'
PLAN = ROOT / 'research/plans/20261026_wrd_lineage_v6'


def sha(p):
    x = hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda: f.read(1048576), b''):
            x.update(b)
    return x.hexdigest()


def read(p):
    return json.loads(p.read_text(encoding='utf-8-sig'))


def save(p, v):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(v, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def main():
    manifest = read(SEQ / 'TRAINING_MANIFEST.json')
    data = read(SEQ / 'ADMITTED_DATA_REPORT.json')
    qa = read(AUDIT / 'INDEPENDENT_FINAL_DATA_QA.json')
    assert qa['status'].startswith('PASS') and not qa['failures']
    assert manifest['native_lineage_review_pending'] is False
    assert manifest['resource_closed_quality_covered_process_data_ready'] is True
    assert manifest['training_started'] is False
    assert data['all_native_and_R_rows_both_CPU_tokenizers_freshly_verified'] is True
    assert isinstance(data['actual_full_A_D_autonomous_native_chains'], int)
    # All counts come from the actual final files, never the original candidate pool.
    assert sum(data['scopes']['controlled'][k]['supervised_tokens'] for k in ('native_core', 'reasoning')) > 0
    native = read(AUDIT / 'LINEAGE_AUDIT_REPORT.json')
    assert sum(native['fixed91_terminal_counts'].values()) == 91
    DEST.mkdir(exist_ok=False)
    (DEST / 'data').mkdir()
    (DEST / 'controlled').mkdir()
    (DEST / 'tooling').mkdir()
    for role in ('native_core', 'actor_aux', 'reasoning'):
        for scope in ('controlled', 'public'):
            profile = manifest['profiles'][scope][role]
            p = SEQ / Path(profile['path'].replace('\\', '/'))
            assert sha(p) == profile['sha256'] and p.stat().st_size == profile['bytes']
            if scope == 'public':
                name = 'public.' + p.name
                shutil.copyfile(p, DEST / 'data' / name)
                profile['path'] = 'data/' + name
            else:
                profile['archive_member'] = 'sequences/' + str(p.relative_to(SEQ)).replace('\\', '/')
                profile['path'] = None
    manifest.update(controlled_archive='controlled/wrd-lineage-process-v6.tar.gz.aesgcm',
                    controlled_archive_requires_local_private_key=True,
                    process_data_readiness_is_not_training_execution_authorization=True,
                    standalone_data_does_not_execute_any_historical_runtime=True)
    save(DEST / 'TRAINING_MANIFEST.json', manifest)
    shutil.copyfile(SEQ / 'ADMITTED_DATA_REPORT.json', DEST / 'ADMITTED_DATA_REPORT.json')
    shutil.copyfile(AUDIT / 'INDEPENDENT_FINAL_DATA_QA.json', DEST / 'INDEPENDENT_FINAL_DATA_QA.json')
    # Public reports include metadata/IDs/hashes only. Full original evidence is
    # always included in the authenticated controlled archive below.
    safe_names = ['LINEAGE_AUDIT_REPORT.json', 'REASONING_LINEAGE_REPORT.json',
                  'INDEPENDENT_NONMAKE_REVIEW.json', 'INDEPENDENT_REASONING_REVIEW.json',
                  'REASONING_QUALITY_OVERLAY_REPORT.json', 'HISTORICAL_RAW_QUALITY_REPORT.json',
                  'INDEPENDENT_RAW_QUALITY_QA.json', 'EXACT_PROTECTED_CONTENT_CHECK.json', 'LINEAGE_FROZEN_QA.json']
    for name in safe_names:
        p = AUDIT / name
        if not p.is_file():
            p = SEQ / name
        if p.is_file():
            # These reports are generated as no-body summaries by the reviewers.
            shutil.copyfile(p, DEST / name)
    for name in ('NATIVE91_PREPARATION_REPORT.json', 'REASONING_PREPARATION_REPORT.json', 'FROZEN_NATIVE91_SET.json'):
        shutil.copyfile(SEQ / name, DEST / name)
    for p in sorted((ROOT / 'research/data_prep/wrd_reasoning_v6').glob('*.py')):
        shutil.copyfile(p, DEST / 'tooling' / p.name)
    # Include every newly recovered original/context/resource and all held-chain
    # evidence. Keep intermediate audits as history, never auto-load as positives.
    members = {}
    for label, base in (('sequences', SEQ), ('lineage', AUDIT)):
        for p in sorted(base.rglob('*')):
            if not p.is_file():
                continue
            rel = p.relative_to(base)
            if rel.parts[0] in {'encrypted_delivery', 'local_delivery_key'}:
                continue
            if p.is_symlink() or p.suffix.lower() in {'.key', '.pem', '.pfx', '.p12'}:
                raise ValueError('unexpected link or private key in v6 evidence')
            if p.name in {'REMOTE_GIT_VERIFICATION.json', 'REMOTE_GIT_VERIFICATION_PROGRESS.json', 'FINAL_DELIVERY_RECEIPT.json'}:
                continue
            members[label + '/' + rel.as_posix()] = p
    for p in sorted(PLAN.glob('*')):
        if p.is_file():
            members['plan/' + p.name] = p
    inner = {'schema_version': 'wrd-lineage-controlled-manifest-v6',
             'includes_held_and_failed_evidence_not_automatic_training_admission': True,
             'private_key_included': False,
             'training_manifest_member': 'sequences/TRAINING_MANIFEST.json',
             'files': [{'path': n, 'bytes': p.stat().st_size, 'sha256': sha(p)} for n, p in members.items()]}
    encryption_dir = AUDIT / 'encrypted_delivery'
    encryption_dir.mkdir(exist_ok=False)
    plain = encryption_dir / 'wrd-lineage-process-v6.tar.gz'
    with tarfile.open(plain, 'w:gz') as tf:
        for name, p in members.items():
            tf.add(p, arcname=name, recursive=False)
        body = (json.dumps(inner, ensure_ascii=False, indent=2) + '\n').encode()
        info = tarfile.TarInfo('MANIFEST.json')
        info.size = len(body)
        tf.addfile(info, io.BytesIO(body))
    helper = ROOT / 'research/data_prep/wrd_reasoning_v4/encrypted_delivery.py'
    spec = importlib.util.spec_from_file_location('previous_authenticated_encryption', helper)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    cipher = encryption_dir / 'wrd-lineage-process-v6.tar.gz.aesgcm'
    key = ROOT / 'output/20261025_wrd_reasoning_recovery_v4/local_delivery_key/wrd-reasoning-v4.key'
    report = module.encrypt(plain, cipher, key, reuse_key=True)
    with cipher.open('rb') as f:
        header = f.read(20)
    for old in RELEASE.rglob('*.aesgcm'):
        with old.open('rb') as f:
            assert f.read(20)[8:20] != header[8:20], 'nonce collision'
    report.update(schema_version='wrd-lineage-process-encrypted-delivery-v6',
                  members_with_manifest=len(members) + 1,
                  full_original_chain_and_resource_evidence_delivered=True,
                  old_v4_v5_large_archives_reuploaded=False,
                  reused_local_key_with_distinct_new_nonce=True,
                  training_started=False)
    save(AUDIT / 'ENCRYPTED_DELIVERY_REPORT.json', report)
    shutil.copyfile(cipher, DEST / 'controlled' / cipher.name)
    shutil.copyfile(AUDIT / 'ENCRYPTED_DELIVERY_REPORT.json', DEST / 'ENCRYPTED_DELIVERY_REPORT.json')
    save(AUDIT / 'PACKAGING_RECEIPT.json', {'status': 'ASSEMBLED_NOT_YET_PUSHED',
         'controlled_members_with_manifest': len(members) + 1,
         'cipher_bytes': cipher.stat().st_size,
         'final_data_manifest_sha256': sha(DEST / 'TRAINING_MANIFEST.json'),
         'training_started': False})
    print(json.dumps({'status': 'PACKAGED_NOT_YET_PUSHED', 'cipher_bytes': cipher.stat().st_size,
                      'members_with_manifest': len(members) + 1, 'training_started': False}))


if __name__ == '__main__':
    main()
