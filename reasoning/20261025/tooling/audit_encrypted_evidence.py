"""Independent authenticated supplement and streamed member audit; secret-free QA.

Reuses only the independently written QA crypto/path helpers, not the producer.
No archive regeneration, plaintext output, Git action or delivery-key disclosure.
"""
from __future__ import annotations
import base64
import hashlib
import json
from pathlib import Path,PurePosixPath
import re
import tarfile
import time
from cryptography.exceptions import InvalidTag
from audit_encrypted_delivery import file_sha,authenticated_digest,safe_tar_name,EXPECTED_MAGIC

ROOT=Path(__file__).resolve().parents[3]
BASE=ROOT/'output/20261025_wrd_reasoning_recovery_v4'
DEST=BASE/'encrypted_delivery'


def main():
    started=time.monotonic();failures=[]
    output=DEST/'ENCRYPTED_EVIDENCE_INDEPENDENT_QA.json'
    if output.exists():raise ValueError('independent_evidence_qa_already_exists')
    producer_path=DEST/'ENCRYPTED_EVIDENCE_REPORT.json'
    producer=json.loads(producer_path.read_text(encoding='utf-8-sig'))
    cipher=DEST/'wrd-controlled-evidence-v4.tar.gz.aesgcm'
    plaintext=DEST/'wrd-controlled-evidence-v4.tar.gz'
    manifest_path=DEST/'EVIDENCE_SUPPLEMENT_MANIFEST.private.json'
    primary_manifest_path=DEST/'CONTROLLED_INPUT_MANIFEST.private.json'
    primary_cipher=DEST/'wrd-controlled-records-v4.tar.gz.aesgcm'
    primary_report_path=DEST/'ENCRYPTED_DELIVERY_REPORT.json'
    primary_qa_path=DEST/'ENCRYPTED_DELIVERY_INDEPENDENT_QA.json'
    key_path=BASE/'local_delivery_key/wrd-reasoning-v4.key'
    watched=[producer_path,cipher,plaintext,manifest_path,primary_manifest_path,primary_report_path,primary_qa_path,key_path]
    before={str(p):file_sha(p) for p in watched}
    primary_stat=(primary_cipher.stat().st_size,primary_cipher.stat().st_mtime_ns)
    key=key_path.read_bytes()
    if len(key)!=32:raise ValueError('delivery_key_length_not_32')
    with primary_cipher.open('rb') as f:primary_header=f.read(8);primary_nonce=f.read(12)
    with cipher.open('rb') as f:
        header=f.read(8);nonce=f.read(12);f.seek(-16,2);tag=f.read(16)
    assert header==primary_header==EXPECTED_MAGIC and len(nonce)==len(primary_nonce)==12 and len(tag)==16
    assert nonce!=primary_nonce
    assert cipher.stat().st_size-plaintext.stat().st_size==36
    recovered_sha,recovered_size=authenticated_digest(cipher,key,header,nonce,tag)
    assert recovered_sha==producer['plaintext_sha256']==before[str(plaintext)]
    assert recovered_size==plaintext.stat().st_size
    assert before[str(cipher)]==producer['ciphertext_sha256'] and cipher.stat().st_size==producer['ciphertext_bytes']
    wrong_key=bytes([key[0]^1])+key[1:];wrong_key_rejected=False
    try:authenticated_digest(cipher,wrong_key,header,nonce,tag,keep_digest=False)
    except InvalidTag:wrong_key_rejected=True
    assert wrong_key_rejected
    print(json.dumps({'phase':'supplement_authentication','status':'PASS','fresh_nonce_different_from_primary':True}),flush=True)

    primary_manifest=json.loads(primary_manifest_path.read_text(encoding='utf-8-sig'))
    primary_hashes={x['sha256'] for x in primary_manifest['files']}
    primary_report=json.loads(primary_report_path.read_text(encoding='utf-8-sig'))
    actual={};embedded=None;members=0;regular=0;hardlinks=0;contents_bytes=0
    key_hits=0;key_named=[]
    key_patterns=(key,key.hex().encode(),base64.b64encode(key),base64.urlsafe_b64encode(key))
    tail_size=max(map(len,key_patterns))-1
    forbidden_name=re.compile(r'local_delivery_key|wrd-reasoning-v4\.key|\.key$',re.I)
    with tarfile.open(plaintext,mode='r|gz') as archive:
        for member in archive:
            members+=1;name=member.name
            if not safe_tar_name(name):raise ValueError('unsafe_supplement_member_path')
            if name in actual:raise ValueError('duplicate_supplement_member_path')
            if forbidden_name.search(name):key_named.append(name)
            if member.issym():raise ValueError('supplement_symlink_not_allowed')
            if member.islnk():
                hardlinks+=1
                if not safe_tar_name(member.linkname) or member.linkname not in actual:
                    raise ValueError('supplement_unsafe_or_forward_hardlink')
                v=actual[member.linkname]
                actual[name]={'sha256':v['sha256'],'bytes':v['bytes'],'kind':'safe_hardlink'}
                continue
            if not member.isfile():raise ValueError('supplement_nonfile_member_not_allowed')
            regular+=1;stream=archive.extractfile(member)
            if stream is None:raise ValueError('supplement_member_content_missing')
            h=hashlib.sha256();size=0;tail=b'';parts=[]
            while True:
                block=stream.read(1024*1024)
                if not block:break
                h.update(block);size+=len(block);combined=tail+block
                if any(pattern in combined for pattern in key_patterns):key_hits+=1
                tail=combined[-tail_size:]
                if name=='EVIDENCE_SUPPLEMENT_MANIFEST.json':parts.append(block)
            if size!=member.size:raise ValueError('supplement_member_size_not_equal_tar_header')
            actual[name]={'sha256':h.hexdigest(),'bytes':size,'kind':'regular_file'};contents_bytes+=size
            if name=='EVIDENCE_SUPPLEMENT_MANIFEST.json':embedded=json.loads(b''.join(parts).decode('utf-8-sig'))
            if members%1000==0:print(json.dumps({'phase':'stream_supplement','members':members}),flush=True)
    assert embedded is not None
    assert actual['EVIDENCE_SUPPLEMENT_MANIFEST.json']['sha256']==before[str(manifest_path)]
    expected={r['path']:r for r in embedded['files']}
    assert len(expected)==len(embedded['files'])==4922
    assert set(actual)==set(expected)|{'EVIDENCE_SUPPLEMENT_MANIFEST.json'}
    for name,r in expected.items():
        if not safe_tar_name(name):raise ValueError('unsafe_supplement_manifest_path')
        if actual[name]['sha256']!=r['sha256'] or actual[name]['bytes']!=r['bytes']:
            failures.append({'code':'member_sha_or_size_differs_from_internal_manifest','path':name,
                             'expected_sha256':r['sha256'],'actual_sha256':actual[name]['sha256'],
                             'expected_bytes':r['bytes'],'actual_bytes':actual[name]['bytes']})
    assert members==producer['input_files']==4923
    supplemental_hashes={v['sha256'] for v in actual.values()}
    objects={n:v for n,v in actual.items() if n.startswith('evidence_objects/')}
    for name,v in objects.items():
        if PurePosixPath(name).name!=v['sha256']:
            failures.append({'code':'evidence_object_name_not_content_sha256','path':name})
    primary_aliases=0;supplement_aliases=0
    for alias in embedded['aliases']:
        h=alias['sha256']
        if alias['in_primary_archive']:
            if h not in primary_hashes:failures.append({'code':'alias_primary_sha_unresolved'})
            primary_aliases+=1
        else:
            if h not in supplemental_hashes:failures.append({'code':'alias_supplement_sha_unresolved'})
            supplement_aliases+=1
    assert not embedded['unresolved_or_historical_missing_reference_paths'] and producer['unresolved_reference_count']==0
    assert embedded['primary_plaintext_sha256']==primary_report['plaintext_sha256']
    assert not key_named and key_hits==0
    assert not key_path.resolve().is_relative_to((ROOT/'output/20261025_wrd_training_dataset/git_release').resolve())
    unchanged=all(file_sha(p)==before[str(p)] for p in watched)
    primary_cipher_unchanged_by_stat=primary_stat==(primary_cipher.stat().st_size,primary_cipher.stat().st_mtime_ns)
    assert unchanged and primary_cipher_unchanged_by_stat
    result={'schema_version':'wrd-encrypted-evidence-independent-qa-v4','status':'PASS' if not failures else 'FAIL',
            'algorithm':'AES-256-GCM','shared_key_length_bytes':32,'nonce_length_bytes':12,'tag_length_bytes':16,
            'authenticated_header_magic_verified':True,'nonce_different_from_primary_archive':True,
            'same_existing_local_key_independently_authenticates_supplement':True,
            'independent_authenticated_plaintext_sha256':recovered_sha,'plaintext_bytes':recovered_size,
            'ciphertext_sha256':before[str(cipher)],'ciphertext_bytes':cipher.stat().st_size,
            'wrong_key_raises_invalid_tag':True,'streamed_tar_members':members,'regular_file_count':regular,
            'safe_hardlink_count':hardlinks,'member_content_bytes':contents_bytes,'manifest_data_file_count':len(expected),
            'archive_and_manifest_member_sets_equal':True,'all_file_sha_and_sizes_match_manifest':not failures,
            'embedded_manifest_matches_private_manifest_file':True,'evidence_object_count':len(objects),
            'evidence_object_names_equal_content_sha256':not any(x['code']=='evidence_object_name_not_content_sha256' for x in failures),
            'source_alias_count':len(embedded['aliases']),'source_aliases_resolved_in_primary_manifest':primary_aliases,
            'source_aliases_resolved_in_supplement':supplement_aliases,
            'unresolved_reference_paths_at_build':0,'unresolved_zero_does_not_prove_all_historical_code_versions_match':True,
            'only_container_integrity_and_recorded_reference_content_resolved_not_semantic_version_equivalence':True,
            'all_member_paths_safe_no_traversal_or_unsafe_links':True,'delivery_key_named_archive_members':0,
            'delivery_key_raw_hex_base64_material_matches_in_member_bytes':0,'key_outside_git_publication_checkout':True,
            'primary_cipher_file_unchanged_by_size_and_mtime':primary_cipher_unchanged_by_stat,
            'primary_report_and_original_independent_qa_unchanged':True,
            'all_audited_inputs_unchanged':unchanged,'no_plaintext_copy_archive_regeneration_or_remote_write':True,
            'no_key_or_private_row_bodies_in_report':True,'not_automatic_training_admission':True,
            'elapsed_seconds':round(time.monotonic()-started,3),'script_sha256':file_sha(Path(__file__)),
            'training_started':False,'failures':failures}
    output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'status':result['status'],'members':members,'data_files':len(expected),
                      'source_aliases':len(embedded['aliases']),'mismatches':len(failures),'elapsed_seconds':result['elapsed_seconds']}),flush=True)
    if failures:raise SystemExit(1)


if __name__=='__main__':main()
