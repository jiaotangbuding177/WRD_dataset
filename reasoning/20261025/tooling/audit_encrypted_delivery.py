"""Independent read-only AES-GCM and streamed tar audit; never prints secrets.

Does not import the producer, regenerate archives, write plaintext, or touch Git.
The only outputs are this source file and a content-free QA report.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path, PurePosixPath, PureWindowsPath
import re
import tarfile
import time

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

ROOT=Path(__file__).resolve().parents[3]
BASE=ROOT/'output/20261025_wrd_reasoning_recovery_v4'
DELIVERY=BASE/'encrypted_delivery'
EXPECTED_MAGIC=b'WRDENC4\x00'


def file_sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
    return h.hexdigest()


def authenticated_digest(path,key,aad,expected_nonce,tag,keep_digest=True):
    # Independent implementation: no producer functions or temporary plaintext.
    size=path.stat().st_size
    dec=Cipher(algorithms.AES(key),modes.GCM(expected_nonce,tag)).decryptor()
    dec.authenticate_additional_data(aad)
    h=hashlib.sha256();length=0
    with path.open('rb') as f:
        f.seek(len(EXPECTED_MAGIC)+12)
        remaining=size-len(EXPECTED_MAGIC)-12-16
        while remaining:
            block=f.read(min(1024*1024,remaining))
            if not block:raise ValueError('ciphertext_truncated')
            remaining-=len(block)
            plaintext=dec.update(block);length+=len(plaintext)
            if keep_digest:h.update(plaintext)
        final=dec.finalize();length+=len(final)
        if keep_digest:h.update(final)
    return h.hexdigest() if keep_digest else None,length


def safe_tar_name(name):
    if not name or '\x00' in name or '\\' in name:return False
    posix=PurePosixPath(name);windows=PureWindowsPath(name)
    return not posix.is_absolute() and not windows.drive and '..' not in posix.parts and name not in ('.','..')


def main():
    started=time.monotonic();failures=[]
    report_path=DELIVERY/'ENCRYPTED_DELIVERY_REPORT.json'
    producer=json.loads(report_path.read_text(encoding='utf-8-sig'))
    cipher=DELIVERY/'wrd-controlled-records-v4.tar.gz.aesgcm'
    plaintext=DELIVERY/'wrd-controlled-records-v4.tar.gz'
    key_path=BASE/'local_delivery_key/wrd-reasoning-v4.key'
    private_manifest_path=DELIVERY/'CONTROLLED_INPUT_MANIFEST.private.json'
    watched=[report_path,cipher,plaintext,key_path,private_manifest_path]
    before={str(p):file_sha(p) for p in watched}
    key=key_path.read_bytes()
    if len(key)!=32:raise ValueError('delivery_key_length_not_32_bytes')
    with cipher.open('rb') as f:
        header=f.read(8);nonce=f.read(12);f.seek(-16,2);tag=f.read(16)
    assert header==EXPECTED_MAGIC and len(nonce)==12 and len(tag)==16
    assert cipher.stat().st_size-plaintext.stat().st_size==36
    recovered_sha,recovered_size=authenticated_digest(cipher,key,header,nonce,tag)
    assert recovered_sha==producer['plaintext_sha256']==before[str(plaintext)]
    assert recovered_size==producer['plaintext_bytes']==plaintext.stat().st_size
    assert before[str(cipher)]==producer['ciphertext_sha256']
    assert cipher.stat().st_size==producer['ciphertext_bytes']
    wrong_key=bytes([key[0]^1])+key[1:]
    wrong_key_rejected=False
    try:authenticated_digest(cipher,wrong_key,header,nonce,tag,keep_digest=False)
    except InvalidTag:wrong_key_rejected=True
    assert wrong_key_rejected
    wrong_aad_rejected=False
    try:authenticated_digest(cipher,key,header[:-1]+bytes([header[-1]^1]),nonce,tag,keep_digest=False)
    except InvalidTag:wrong_aad_rejected=True
    assert wrong_aad_rejected
    print(json.dumps({'phase':'independent_authentication','status':'PASS','wrong_key_rejected':True,'wrong_aad_rejected':True}),flush=True)

    actual={};manifest=None;members=0;regular_files=0;hard_links=0;total_contents=0
    key_material_matches=0;mapping_named_members=[];sensitive_key_named_members=[]
    sensitive_pattern=re.compile(r'(?:privacy|pii|identity|private)[_-]?(?:mapping|map|salt)|local_delivery_key|wrd-reasoning-v4\.key|\.key$',re.I)
    with tarfile.open(plaintext,mode='r|gz') as archive:
        for member in archive:
            members+=1
            name=member.name
            if not safe_tar_name(name):raise ValueError('unsafe_archive_member_path')
            if name in actual:raise ValueError('duplicate_archive_member_path')
            if sensitive_pattern.search(name):sensitive_key_named_members.append(name)
            if 'mapping' in PurePosixPath(name).name.lower():mapping_named_members.append(name)
            if member.issym():raise ValueError('archive_symlink_not_allowed')
            if member.islnk():
                hard_links+=1
                if not safe_tar_name(member.linkname) or member.linkname not in actual:
                    raise ValueError('unsafe_or_forward_archive_hardlink')
                previous=actual[member.linkname]
                actual[name]={'sha256':previous['sha256'],'bytes':previous['bytes'],'kind':'safe_hardlink'}
                continue
            if not member.isfile():raise ValueError('unexpected_nonfile_archive_member')
            regular_files+=1;f=archive.extractfile(member)
            if f is None:raise ValueError('archive_member_content_missing')
            h=hashlib.sha256();size=0;tail=b'';manifest_parts=[]
            while True:
                block=f.read(1024*1024)
                if not block:break
                h.update(block);size+=len(block)
                if key in tail+block:key_material_matches+=1
                tail=(tail+block)[-31:]
                if name=='CONTROLLED_INPUT_MANIFEST.json':manifest_parts.append(block)
            if size!=member.size:raise ValueError('archive_member_size_mismatch')
            total_contents+=size
            actual[name]={'sha256':h.hexdigest(),'bytes':size,'kind':'regular_file'}
            if name=='CONTROLLED_INPUT_MANIFEST.json':manifest=json.loads(b''.join(manifest_parts).decode('utf-8-sig'))
            if members%500==0:print(json.dumps({'phase':'stream_archive_members','members':members}),flush=True)
    assert manifest is not None
    assert actual['CONTROLLED_INPUT_MANIFEST.json']['sha256']==before[str(private_manifest_path)]
    expected={x['path']:x for x in manifest['files']}
    if len(expected)!=len(manifest['files']):raise ValueError('duplicate_manifest_paths')
    if set(actual)!=set(expected)|{'CONTROLLED_INPUT_MANIFEST.json'}:
        raise ValueError('archive_manifest_path_sets_differ')
    for name,expected_file in expected.items():
        if not safe_tar_name(name):raise ValueError('unsafe_manifest_member_path')
        if actual[name]['sha256']!=expected_file['sha256'] or actual[name]['bytes']!=expected_file['bytes']:
            raise ValueError('archive_file_sha_or_size_differs_from_manifest')
    source_objects={name:meta for name,meta in actual.items() if name.startswith('source_objects/')}
    assert len(source_objects)==producer['source_raw_objects']==2668
    for name,meta in source_objects.items():assert PurePosixPath(name).name==meta['sha256']
    aliases=manifest['source_aliases']
    assert len(aliases)==producer['source_aliases']==2786
    for alias in aliases:
        name=alias['archive_object']
        assert safe_tar_name(name) and name in source_objects and source_objects[name]['sha256']==alias['sha256']
    assert not manifest['missing_original_source_files'] and producer['missing_sources']==0
    assert members==producer['input_files']==2747
    assert not sensitive_key_named_members and key_material_matches==0
    # Generic metadata named "mapping" may be legitimate, but must be reported;
    # actual decryption-key material and privacy map/salt files are prohibited.
    assert not mapping_named_members
    assert not key_path.resolve().is_relative_to((ROOT/'output/20261025_wrd_training_dataset/git_release').resolve())
    unchanged=all(file_sha(p)==before[str(p)] for p in watched)
    assert unchanged
    result={
        'schema_version':'wrd-encrypted-delivery-independent-qa-v4','status':'PASS',
        'independent_implementation_does_not_import_producer':True,
        'algorithm':'AES-256-GCM','key_length_bytes':32,'nonce_length_bytes':12,'tag_length_bytes':16,
        'format_magic_length_bytes':8,'format_magic_verified':True,'aad_is_exact_header_magic':True,
        'authenticated_decryption_completed_before_plaintext_archive_inspection':True,
        'independent_authenticated_plaintext_sha256':recovered_sha,
        'plaintext_sha_matches_producer_and_existing_private_archive':True,
        'ciphertext_sha256':before[str(cipher)],'ciphertext_bytes':cipher.stat().st_size,
        'plaintext_bytes':recovered_size,'wrong_key_raises_invalid_tag':wrong_key_rejected,
        'wrong_aad_raises_invalid_tag':wrong_aad_rejected,
        'streamed_tar_member_count':members,'regular_file_count':regular_files,'safe_hardlink_count':hard_links,
        'archive_member_content_bytes':total_contents,'manifest_data_file_count':len(expected),
        'all_member_paths_safe_no_traversal':True,'no_symlinks_or_unsafe_links':True,
        'archive_and_manifest_member_sets_equal':True,'all_file_sha256_and_sizes_match_internal_manifest':True,
        'embedded_manifest_matches_private_manifest_file':True,'source_object_count':len(source_objects),
        'all_source_object_names_equal_content_sha256':True,'source_alias_count':len(aliases),
        'all_source_aliases_resolve_to_correct_objects':True,'missing_original_sources':0,
        'delivery_key_or_privacy_map_salt_named_members':0,'generic_mapping_named_members':0,
        'delivery_key_material_matches_in_archive_member_bytes':0,
        'key_file_is_outside_git_publication_checkout':True,
        'key_file_acl_not_audited':True,'all_original_inputs_unchanged':unchanged,
        'no_plaintext_copy_or_archive_regeneration_performed':True,
        'archive_contains_formal_and_failed_evidence_not_automatic_training_admission':True,
        'no_key_or_row_bodies_written_to_report':True,
        'script_sha256':file_sha(Path(__file__)),'elapsed_seconds':round(time.monotonic()-started,3),
        'training_started':False,'failures':failures,
    }
    out=DELIVERY/'ENCRYPTED_DELIVERY_INDEPENDENT_QA.json'
    if out.exists():raise ValueError('refusing_to_overwrite_independent_qa_report')
    out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'status':'PASS','members':members,'source_objects':len(source_objects),'source_aliases':len(aliases),
                      'key_material_found':False,'elapsed_seconds':result['elapsed_seconds']}),flush=True)


if __name__=='__main__':main()
