"""Authenticated encrypted delivery of controlled records, never key disclosure.

No model, agent, GPU or training. AES-256-GCM uses the maintained cryptography
library. The random key stays outside the Git publication checkout.
"""
import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
import secrets
import tarfile
import time

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

MAGIC = b'WRDENC4\x00'
ROOT = Path(__file__).resolve().parents[3]


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda: f.read(1024 * 1024), b''):
            h.update(b)
    return h.hexdigest()


def rows(path):
    with gzip.open(path, 'rt', encoding='utf-8-sig') as f:
        for line in f:
            if line.strip():
                yield json.loads(line)


def encrypt(plain, cipher, key_path, reuse_key=False):
    if cipher.exists() or (key_path.exists() and not reuse_key):
        raise ValueError('new encrypted output and key paths required unless explicit safe key reuse')
    key_path.parent.mkdir(parents=True, exist_ok=True)
    key = key_path.read_bytes() if reuse_key else secrets.token_bytes(32)
    if len(key) != 32:
        raise ValueError('invalid key length')
    if not reuse_key:
        with key_path.open('xb') as f:
            f.write(key)
    os.chmod(key_path, 0o600)
    nonce = secrets.token_bytes(12)
    enc = Cipher(algorithms.AES(key), modes.GCM(nonce)).encryptor()
    enc.authenticate_additional_data(MAGIC)
    with plain.open('rb') as src, cipher.open('xb') as dst:
        dst.write(MAGIC + nonce)
        for b in iter(lambda: src.read(1024 * 1024), b''):
            dst.write(enc.update(b))
        dst.write(enc.finalize())
        dst.write(enc.tag)
    # Independent authenticated decryption to a digest, no extra plaintext copy.
    expected = sha(plain)
    result = decrypt_hash(cipher, key_path)
    if result != expected:
        raise ValueError('authenticated roundtrip SHA mismatch')
    return {'format': 'WRDENC4', 'algorithm': 'AES-256-GCM', 'authenticated_header': True,
            'nonce_bytes': 12, 'tag_bytes': 16, 'plaintext_sha256': expected,
            'ciphertext_sha256': sha(cipher), 'ciphertext_bytes': cipher.stat().st_size,
            'authenticated_roundtrip_sha_verified': True,
            'key_stored_only_locally_not_in_git': True, 'key_bytes': 32}


def decrypt_hash(cipher, key_path, output=None):
    key = key_path.read_bytes()
    if len(key) != 32:
        raise ValueError('key length must be exactly 32 bytes')
    if output is not None and output.exists():
        raise ValueError('refusing to overwrite output')
    size = cipher.stat().st_size
    temp = output.with_name(output.name + '.unverified.tmp') if output else None
    if temp and temp.exists():
        raise ValueError('temporary output already exists')
    h = hashlib.sha256()
    writer = None
    try:
        with cipher.open('rb') as src:
            if src.read(len(MAGIC)) != MAGIC:
                raise ValueError('unexpected archive format')
            nonce = src.read(12)
            src.seek(size - 16)
            tag = src.read(16)
            src.seek(len(MAGIC) + 12)
            dec = Cipher(algorithms.AES(key), modes.GCM(nonce, tag)).decryptor()
            dec.authenticate_additional_data(MAGIC)
            if temp:
                temp.parent.mkdir(parents=True, exist_ok=True)
                writer = temp.open('xb')
            remaining = size - len(MAGIC) - 12 - 16
            while remaining:
                b = src.read(min(1024 * 1024, remaining))
                if not b:
                    raise ValueError('truncated ciphertext')
                remaining -= len(b)
                plain = dec.update(b)
                h.update(plain)
                if writer:
                    writer.write(plain)
            last = dec.finalize()
            h.update(last)
            if writer:
                writer.write(last)
                writer.close()
                writer = None
                temp.replace(output)
    finally:
        if writer:
            writer.close()
    return h.hexdigest()


def build():
    base = ROOT / 'output/20261025_wrd_reasoning_recovery_v4'
    dest = base / 'encrypted_delivery'
    dest.mkdir(exist_ok=False)
    sources = {}
    for directory in ('controlled', 'curated_native', 'curated_reasoning', 'source_gated_profiles',
                      'raw_reasoning_evolution_final', 'historical_native_compiled',
                      'native_compiled_controlled_final', 'controller_views'):
        for p in sorted((base / directory).rglob('*')):
            if p.is_file():
                sources['recovery/' + str(p.relative_to(base)).replace('\\', '/')] = p
    # Evidence mother tables and support are not supplied to a trainer by default.
    mother = ROOT / 'output/20261025_wrd_training_dataset/bundle'
    for name in ('canonical/native_episodes.jsonl.gz', 'catalog/episodes.jsonl', 'catalog/jobs.jsonl',
                 'catalog/routes.jsonl', 'catalog/source_materials.jsonl'):
        p = mother / name
        if p.is_file():
            sources['frozen_bundle/' + name] = p
    for directory in ('controlled_master', 'controlled_linkage'):
        for p in sorted((ROOT / 'output/20261025_wrd_fullchain_reaudit' / directory).glob('*')):
            if p.is_file():
                sources['fullchain_evidence/' + directory + '/' + p.name] = p
    # All controlled support text is preserved; large previously delivered binary
    # archives are referenced by their existing Git manifests rather than recopied.
    support = ROOT / 'output/20261025_wrd_training_preflight/work_support/support.text.jsonl.gz'
    if support.is_file():
        sources['support/support.text.jsonl.gz'] = support
    # Exact original bytes behind recovered JSON/SSE records, deduplicated by SHA.
    objects, aliases, missing = {}, [], []
    for name in ('raw_pairs.all.jsonl.gz', 'sse_reasoning_pairs.all.jsonl.gz'):
        for r in rows(base / 'controlled' / name):
            for k in ('source_request', 'source_response', 'source_sse', 'source_stored_response', 'source_parsed', 'source_receipt'):
                m = r.get(k)
                if not isinstance(m, dict) or not m.get('path'):
                    continue
                p = Path(m['path'])
                if not p.is_file():
                    missing.append({'record_id': r['id'], 'field': k, 'path': str(p)})
                    continue
                h = sha(p)
                if m.get('sha256') and h != m['sha256']:
                    raise ValueError('raw source changed before encrypted delivery')
                objects[h] = p
                aliases.append({'record_id': r['id'], 'field': k, 'original_path': str(p),
                                'sha256': h, 'archive_object': 'source_objects/' + h})
    for h, p in objects.items():
        sources['source_objects/' + h] = p
    manifest = {'schema_version': 'wrd-controlled-encrypted-input-manifest-v4',
                'contains_raw_private_data': True, 'not_a_training_manifest': True,
                'formal_and_failed_records_archived_not_admitted': True,
                'files': [{'path': name, 'sha256': sha(p), 'bytes': p.stat().st_size}
                          for name, p in sorted(sources.items())],
                'source_aliases': aliases, 'missing_original_source_files': missing,
                'public_existing_binary_archive_reference': 'WRD_dataset historical dist/ manifests',
                'training_started': False}
    manifest_path = dest / 'CONTROLLED_INPUT_MANIFEST.private.json'
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    plain = dest / 'wrd-controlled-records-v4.tar.gz'
    started = time.monotonic()
    with tarfile.open(plain, 'w:gz', compresslevel=3, format=tarfile.PAX_FORMAT) as tar:
        for index, (name, path) in enumerate(sorted(sources.items()), 1):
            tar.add(path, arcname=name, recursive=False)
            if index % 500 == 0:
                print(json.dumps({'archive_files': index}), flush=True)
        tar.add(manifest_path, arcname='CONTROLLED_INPUT_MANIFEST.json', recursive=False)
    cipher = dest / 'wrd-controlled-records-v4.tar.gz.aesgcm'
    key_path = base / 'local_delivery_key/wrd-reasoning-v4.key'
    report = encrypt(plain, cipher, key_path)
    report.update(schema_version='wrd-encrypted-delivery-v4', input_files=len(sources) + 1,
                  source_raw_objects=len(objects), source_aliases=len(aliases), missing_sources=len(missing),
                  archive_contains_full_raw_reasoning_and_responses=True,
                  archive_is_not_automatic_training_admission=True,
                  plaintext_bytes=plain.stat().st_size, elapsed_seconds=round(time.monotonic() - started, 3),
                  training_started=False)
    (dest / 'ENCRYPTED_DELIVERY_REPORT.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report), flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--build', action='store_true')
    parser.add_argument('--build-evidence-supplement', action='store_true')
    parser.add_argument('--decrypt', type=Path)
    parser.add_argument('--key-file', type=Path)
    parser.add_argument('--output-tar', type=Path)
    args = parser.parse_args()
    if args.build:
        build()
    elif args.build_evidence_supplement:
        build_evidence_supplement()
    elif args.decrypt and args.key_file and args.output_tar:
        result = decrypt_hash(args.decrypt, args.key_file, args.output_tar)
        print(json.dumps({'authenticated_decryption': 'PASS', 'plaintext_sha256': result,
                          'output_tar': str(args.output_tar), 'training_started': False}))
    else:
        parser.error('use --build, or --decrypt ARCHIVE --key-file KEY --output-tar NEW_PATH')


def build_evidence_supplement():
    base = ROOT / 'output/20261025_wrd_reasoning_recovery_v4'
    dest = base / 'encrypted_delivery'
    original = json.loads((dest / 'CONTROLLED_INPUT_MANIFEST.private.json').read_text(encoding='utf-8'))
    prior = {r['sha256'] for r in original['files']}
    files = {('audit_reports/' + p.name): p for p in sorted(base.glob('*')) if p.suffix in {'.json', '.md'}}
    # The old local AI notes underpin the conservative reject overlay.
    for p in sorted((ROOT / 'output/20261025_wrd_training_preflight/local_review').glob('*.jsonl')):
        files['prior_local_ai_reviews/' + p.name] = p
    missing, aliases = [], []
    candidates = set()
    def references(x):
        if isinstance(x, dict):
            for k, v in x.items():
                if isinstance(v, str) and ('path' in k or k.endswith('_file')) and len(v) < 1024:
                    p = Path(v)
                    if p.is_absolute() and str(p).lower().startswith(('d:\\skillloop\\', 'e:\\skillloop_runs\\', 'd:/skillloop/', 'e:/skillloop_runs/')):
                        candidates.add(p)
                references(v)
        elif isinstance(x, list):
            for v in x:
                references(v)
    for p in base.glob('*.json'):
        references(json.loads(p.read_text(encoding='utf-8')))
    for p in (base / 'controlled').glob('*.jsonl.gz'):
        if any(s in p.name for s in ('labels', 'scope_review', 'source_split')):
            for r in rows(p):
                references(r)
    allowed = {'.json', '.jsonl', '.ndjson', '.raw', '.txt', '.md', '.py', '.yaml', '.yml', '.log', '.csv'}
    for p in sorted(candidates):
        if p.suffix.lower() not in allowed:
            continue
        if any(s in p.name.lower() for s in ('privacy_hmac_salt', 'privacy_private_mapping', '.key')):
            continue
        if not p.is_file():
            missing.append(str(p))
            continue
        h = sha(p)
        aliases.append({'original_path': str(p), 'sha256': h, 'in_primary_archive': h in prior})
        if h not in prior:
            files['evidence_objects/' + h] = p
    manifest = {'schema_version': 'wrd-controlled-evidence-supplement-v4',
                'primary_plaintext_sha256': sha(dest / 'wrd-controlled-records-v4.tar.gz'),
                'files': [{'path': n, 'sha256': sha(p), 'bytes': p.stat().st_size} for n, p in sorted(files.items())],
                'aliases': aliases, 'unresolved_or_historical_missing_reference_paths': missing,
                'not_training_admission': True}
    mpath = dest / 'EVIDENCE_SUPPLEMENT_MANIFEST.private.json'
    mpath.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    plain = dest / 'wrd-controlled-evidence-v4.tar.gz'
    with tarfile.open(plain, 'w:gz', compresslevel=3, format=tarfile.PAX_FORMAT) as tar:
        for name, p in sorted(files.items()):
            tar.add(p, arcname=name, recursive=False)
        tar.add(mpath, arcname='EVIDENCE_SUPPLEMENT_MANIFEST.json', recursive=False)
    report = encrypt(plain, dest / 'wrd-controlled-evidence-v4.tar.gz.aesgcm',
                     base / 'local_delivery_key/wrd-reasoning-v4.key', reuse_key=True)
    report.update(schema_version='wrd-encrypted-evidence-supplement-v4',
                  input_files=len(files) + 1, shared_local_key_with_fresh_random_nonce=True,
                  unresolved_reference_count=len(missing), training_started=False)
    (dest / 'ENCRYPTED_EVIDENCE_REPORT.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report), flush=True)


if __name__ == '__main__':
    main()
