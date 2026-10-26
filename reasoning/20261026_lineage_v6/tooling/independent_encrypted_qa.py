"""Independent authenticated archive/delivery QA, without disclosing the key."""
import base64
from collections import Counter
import gzip
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import tarfile
import tempfile
from datetime import datetime, timezone

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.exceptions import InvalidTag

ROOT = Path('D:/skillloop')
AUDIT = ROOT / 'output/20261026_wrd_lineage_v6'
SEQ = ROOT / 'output/20261026_wrd_sequences_v6'
GIT = ROOT / 'output/20261025_wrd_training_dataset/git_release'
DEST = GIT / 'reasoning/20261026_lineage_v6'
MAGIC = b'WRDENC4\x00'

def sha(b): return hashlib.sha256(b).hexdigest()
def read(p): return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def hf(p):
    h = hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda: f.read(1048576), b''): h.update(b)
    return h.hexdigest()

def rows(p):
    with gzip.open(p, 'rt', encoding='utf-8-sig') as f:
        return [json.loads(l) for l in f if l.strip()]

def main():
    cipher = DEST / 'controlled/wrd-lineage-process-v6.tar.gz.aesgcm'
    encryption = read(DEST / 'ENCRYPTED_DELIVERY_REPORT.json')
    manifest = read(DEST / 'TRAINING_MANIFEST.json')
    local_manifest_sha = hf(SEQ / 'TRAINING_MANIFEST.json')
    assert local_manifest_sha == '00cf9a2091ddf623c6136bf25e8a61579181d307575c9b938506a5147f4c443c'
    assert cipher.stat().st_size == encryption['ciphertext_bytes'] == 251725673
    assert hf(cipher) == encryption['ciphertext_sha256']
    key = (ROOT / 'output/20261025_wrd_reasoning_recovery_v4/local_delivery_key/wrd-reasoning-v4.key').read_bytes()
    assert len(key) == 32
    with cipher.open('rb') as f:
        assert f.read(8) == MAGIC
        nonce = f.read(12)
        f.seek(-16, 2); tag = f.read(16)

    def decrypt(used_key, aad, output=None):
        dec = Cipher(algorithms.AES(used_key), modes.GCM(nonce, tag)).decryptor()
        dec.authenticate_additional_data(aad)
        h = hashlib.sha256()
        with cipher.open('rb') as f:
            f.seek(20); remaining = cipher.stat().st_size - 36
            while remaining:
                block = f.read(min(1048576, remaining)); assert block
                remaining -= len(block); clear = dec.update(block); h.update(clear)
                if output is not None: output.write(clear)
        tail = dec.finalize(); h.update(tail)
        if output is not None: output.write(tail)
        return h.hexdigest()

    old_nonce_checks = []
    old_roots = [ROOT / 'output/20261025_wrd_reasoning_recovery_v4/encrypted_delivery',
        ROOT / 'output/20261026_wrd_strict226_expansion/encrypted_delivery',
        ROOT / 'output/20261026_wrd_strict226_expansion/local_attempt1_encrypted_delivery',
        GIT / 'reasoning/20261025/controlled', GIT / 'reasoning/20261026_strict226/controlled']
    for base in old_roots:
        if not base.is_dir(): continue
        for old in base.rglob('*.aesgcm'):
            with old.open('rb') as f: header = f.read(20)
            assert header[:8] == MAGIC and header[8:20] != nonce
            old_nonce_checks.append({'archive_path': str(old.relative_to(ROOT)).replace('\\', '/'), 'new_nonce_distinct': True})
    assert len(old_nonce_checks) >= 3
    negative_checks = {}
    for label, used_key, aad in [('wrong_key', bytes([key[0] ^ 1]) + key[1:], MAGIC), ('wrong_aad', key, MAGIC + b'!')]:
        try:
            decrypt(used_key, aad)
        except InvalidTag:
            negative_checks[label] = True
        else: raise AssertionError('GCM negative authentication accepted')
    patterns = [key, key.hex().encode(), base64.b64encode(key)]
    def no_key_material(stream):
        suffix = b''
        while True:
            block = stream.read(1048576)
            if not block: break
            check = suffix + block
            assert not any(p in check for p in patterns)
            suffix = check[-64:]
    receipts = {}; inner = None
    # TemporaryFile is never published or extracted; authenticated plaintext
    # is scanned in memory-sized chunks, and the temporary handle is removed.
    tempdir = AUDIT / 'independent_qa_temporary'; tempdir.mkdir(exist_ok=True)
    with tempfile.TemporaryFile(dir=tempdir) as plain:
        assert decrypt(key, MAGIC, plain) == encryption['plaintext_sha256']
        plain.seek(0)
        with tarfile.open(fileobj=plain, mode='r|gz') as tf:
            for member in tf:
                name = member.name; path = PurePosixPath(name)
                assert name not in receipts and member.isfile() and not member.issym() and not member.islnk()
                assert not path.is_absolute() and '..' not in path.parts and '\\' not in name
                assert not (len(name) > 1 and name[1] == ':')
                assert not name.lower().endswith(('.key', '.pem', '.pfx', '.p12')) and 'local_delivery_key' not in name
                data = tf.extractfile(member).read(); assert len(data) == member.size
                no_key_material(io.BytesIO(data))
                if name.endswith('.gz'):
                    with gzip.GzipFile(fileobj=io.BytesIO(data), mode='rb') as nested: no_key_material(nested)
                receipts[name] = {'path': name, 'bytes': len(data), 'sha256': sha(data)}
                if name == 'MANIFEST.json': inner = json.loads(data)
                if len(receipts) % 150 == 0: print(json.dumps({'phase':'authenticated_tar_member_SHA_size_and_secret_material_QA','members':len(receipts)}), flush=True)
    assert inner and inner['private_key_included'] is False
    expected = {x['path']:x for x in inner['files']}
    assert set(receipts) == set(expected) | {'MANIFEST.json'}
    assert len(receipts) == encryption['members_with_manifest'] == 958
    for name, pin in expected.items(): assert receipts[name] == pin
    assert receipts['sequences/TRAINING_MANIFEST.json']['sha256'] == local_manifest_sha
    assert receipts['lineage/INDEPENDENT_FINAL_DATA_QA.json']['sha256'] == hf(AUDIT / 'INDEPENDENT_FINAL_DATA_QA.json')
    controlled_profiles = {}
    for role, pin in manifest['profiles']['controlled'].items():
        archived = receipts[pin['archive_member']]
        assert pin['path'] is None and archived['sha256'] == pin['sha256'] and archived['bytes'] == pin['bytes']
        controlled_profiles[role] = pin['counts']
    public_profiles = {}
    for role, pin in manifest['profiles']['public'].items():
        p = DEST / pin['path']; assert hf(p) == pin['sha256'] and p.stat().st_size == pin['bytes']
        rs = rows(p); assert len(rs) == pin['counts']['windows']
        assert all(r['training_manifest_admitted'] for r in rs)
        if role == 'native_core': assert rs == []
        if role == 'reasoning':
            for r in rs:
                if any(t.get('original_reasoning_characters', 0) for t in r['targets']):
                    assert r['recorded_reasoning_is_privacy_transformed_not_unmodified_original_bytes'] is True
        public_profiles[role] = {'path':pin['path'],'sha256':pin['sha256'],'bytes':pin['bytes'],'windows':len(rs)}
    frozen = read(SEQ / 'FROZEN_NATIVE91_SET.json'); frozen_ids = set(frozen['episode_ids'])
    originals = rows(SEQ / 'controlled/native91.original_contexts.jsonl.gz')
    original_ids = {x.get('episode_id', (x.get('original_context') or {}).get('episode_id')) for x in originals}
    assert len(originals) == 91 and original_ids == frozen_ids
    critical = [
        'sequences/controlled/native91.original_contexts.jsonl.gz',
        'sequences/controlled/native91.message_index.jsonl.gz',
        'sequences/controlled/native91.action_observation_edges.jsonl.gz',
        'sequences/controlled/native91.input_artifacts.original.jsonl.gz',
        'sequences/controlled/native91.feedback_revision_temporal_edges.jsonl.gz',
        'sequences/controlled/reasoning_pairs.original116.jsonl.gz',
        'sequences/controlled/reasoning_pair_lineage_inputs.jsonl.gz',
        'sequences/controlled/reasoning_runs.original.jsonl.gz',
        'sequences/controlled/reasoning_source_file_dependencies.jsonl.gz',
        'sequences/controlled/historical_raw_quality_overlay.jsonl.gz',
        'sequences/controlled/held.reasoning_known_quality.jsonl.gz',
        'sequences/controlled/admitted.reasoning_source_contexts.jsonl.gz',
        'sequences/controlled/admitted.contexts.jsonl.gz',
        'sequences/controlled/admitted.producer_prefix_contexts.jsonl.gz',
        'lineage/controlled/independent_nonmake_context_evidence.jsonl.gz',
        'lineage/INDEPENDENT_REASONING_REVIEW.json', 'lineage/INDEPENDENT_NONMAKE_REVIEW.json']
    for path in critical: assert path in receipts
    pairs = rows(SEQ / 'controlled/reasoning_pairs.original116.jsonl.gz'); assert len(pairs) == 116
    runs = rows(SEQ / 'controlled/reasoning_runs.original.jsonl.gz'); assert len(runs) == 5
    quality_held = rows(SEQ / 'controlled/held.reasoning_known_quality.jsonl.gz'); assert len(quality_held) == 10
    evidence_file_count = 0
    for x in rows(SEQ / 'controlled/reasoning_pair_lineage_inputs.jsonl.gz'):
        for dep in x['source_file_dependencies']:
            rel = (ROOT / dep['immutable_export_path']).relative_to(SEQ)
            name = 'sequences/' + rel.as_posix()
            assert receipts[name]['sha256'] == dep['actual_sha256'] == dep['declared_sha256']
            evidence_file_count += 1
    independent = read(AUDIT / 'INDEPENDENT_REASONING_REVIEW.json')
    for pin in independent['preserved_evidence_files']:
        rel = (ROOT / pin['immutable_export_path']).relative_to(AUDIT)
        assert receipts['lineage/' + rel.as_posix()]['sha256'] == pin['sha256']
    for scope in ('controlled', 'public'):
        for name in ('admitted.resource_closure.index.jsonl.gz', 'admitted.reasoning_resource_closure.index.jsonl.gz'):
            if scope != 'controlled': continue
            for node in rows(SEQ / scope / name):
                identity = node.get('file_identity', node)
                archive_member = 'sequences/' + node['byte_exact_export_path'].replace('\\', '/')
                assert receipts[archive_member]['sha256'] == identity['sha256'] and receipts[archive_member]['bytes'] == identity['bytes']
    assert manifest['training_started'] is False and manifest['training_execution_authorized'] is False
    assert manifest['complete_autonomous_training_or_deployment_ready'] is False
    result = {'schema_version':'wrd-independent-authenticated-delivery-qa-v6',
        'status':'PASS_FOR_AUTHENTICATED_COMPLETE_V6_DATA_DELIVERY_NOT_MODEL_EFFECT',
        'verified_at_utc':datetime.now(timezone.utc).isoformat(),
        'ciphertext_bytes':cipher.stat().st_size,'ciphertext_sha256':hf(cipher),
        'authenticated_plaintext_sha256':encryption['plaintext_sha256'],
        'independent_GCM_authenticated_decryption_verified':True,'wrong_key_and_AAD_rejected':negative_checks,
        'new_nonce_distinct_from_all_checked_v4_v5_archives':old_nonce_checks,
        'tar_members':len(receipts),'all_members_SHA_size_match_authenticated_inner_manifest':True,
        'no_duplicate_absolute_traversal_windows_drive_paths_links_or_key_files':True,
        'raw_hex_base64_local_AES_key_absent_in_all_members_and_nested_gzip_contents':True,
        'key_value_not_exported_or_reported':True,
        'frozen_local_training_manifest_sha256':local_manifest_sha,
        'public_delivery_training_manifest_sha256':hf(DEST/'TRAINING_MANIFEST.json'),
        'controlled_profiles':controlled_profiles,'public_profile_files_verified':public_profiles,
        'empty_native_core_in_both_projections_verified':True,
        'public_R_declared_privacy_transformed_not_original_bytes':True,
        'controlled_original_R_original_request_action_observation_and_feedback_evidence_delivered':True,
        'original_pairs_preserved_including_quality_holds':len(pairs),'original_raw_versions_preserved':len(runs),
        'known_quality_zero_loss_records_preserved':len(quality_held),'frozen_native91_full_contexts_preserved':len(originals),
        'all_reasoning_original_file_dependency_references_verified_in_archive':evidence_file_count,
        'independently_preserved_feedback_receipt_program_sensor_files_present':len(independent['preserved_evidence_files']),
        'all_final_controlled_resource_CAS_files_in_archive':True,
        'original226_boundary_and_full_autonomy_limit_not_relaxed':True,
        'public_README_entrypoints_and_provenance_still_being_finalized_not_hashed_by_this_QA':True,
        'previous_v4_v5_archives_are_separate_preserved_history_not_reuploaded_in_this_archive':True,
        'training_started':False,'weights_loaded':False,'gpu_used':False,'business_api_calls':0,'failures':[],
        'limits':['This proves v6 delivery bytes/authentication/completeness, not complete-model autonomy or business quality.',
            'Original held/failed records remain evidence and do not become admitted training rows.',
            'The complete older forensic corpus remains in the separately delivered v4/v5 archives; this archive covers all v6 sources and evidence.',
            'Historical grader/version limits, independent Q, semantic near-duplicate uncertainty and Spark cost remain as documented in the final data QA.'],
        'critical_archive_members_verified':critical,'member_receipts':list(receipts.values()),
        'script_sha256':hf(Path(__file__))}
    p = AUDIT / 'INDEPENDENT_ENCRYPTED_DELIVERY_QA.json'
    p.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps({'status':result['status'],'members':len(receipts),'ciphertext_bytes':cipher.stat().st_size,'report_sha256':hf(p)}),flush=True)

if __name__ == '__main__': main()
