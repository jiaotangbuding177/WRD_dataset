"""Package only a root-frozen, SHA-pinned explicit checkpoint08 allowlist.

audit is key-free. build requires a separate root freeze receipt, performs the
checkpoint05 known-credential scan, and reuses its existing local AES key API.
No wildcard discovery, Git operation, model, or training occurs here.
"""
from pathlib import Path
import argparse, gzip, hashlib, importlib.util, json, re, shutil, sys, tarfile

ROOT = Path(__file__).resolve().parents[3]
ALLOWLIST_SCHEMA = 'wrd-delta08-root-frozen-allowlist-v1'
FREEZE_STATUS = 'ROOT_FROZEN_ALLOWLIST_APPROVED_FOR_PACKAGE08'
AUTO_FILES = {'packaging_evidence/ROOT_ALLOWLIST08.json', 'packaging_evidence/ROOT_FREEZE_RECEIPT08.json'}
CATEGORIES = {'TRAINING','CONTROLLED_AUDIT','TOOLING','DESIGN','QA','CANONICAL_ARRAY'}
ENCRYPTED_AUDIT_POLICY = 'POTENTIALLY_SENSITIVE_EMBEDDED_URLS_ENCRYPTED_ONLY'


def module(name, path):
    s = importlib.util.spec_from_file_location(name,path); m = importlib.util.module_from_spec(s)
    previous = sys.dont_write_bytecode; sys.dont_write_bytecode = True
    try: s.loader.exec_module(m)
    finally: sys.dont_write_bytecode = previous
    return m
def sha(p):
    h = hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(1048576),b''): h.update(b)
    return h.hexdigest()
def unique_object(pairs):
    result = {}
    for k,v in pairs:
        assert k not in result, 'DUPLICATE_JSON_OBJECT_KEY'
        result[k] = v
    return result
def load(p): return json.loads(Path(p).read_text(encoding='utf-8-sig'),object_pairs_hook=unique_object)
def save(p,v):
    Path(p).parent.mkdir(parents=True,exist_ok=True)
    Path(p).write_bytes((json.dumps(v,ensure_ascii=False,indent=2)+'\n').encode())


def guard_source(p, helper):
    p = Path(helper.source_guard(Path(p)))
    assert p.is_absolute() and p.is_file(), 'ABSOLUTE_REAL_SOURCE_REQUIRED'
    bad_parts = {'__pycache__','local_delivery_key','.aws','.azure','.config','credentials'}
    assert not any(part.casefold() in bad_parts for part in p.parts), 'PRIVATE_SOURCE_DIRECTORY'
    assert p.suffix.casefold() not in {'.pem','.p12','.pfx','.env','.kdbx'}, 'PRIVATE_SOURCE_EXTENSION'
    assert p.name.casefold() not in {'credentials.json','secrets.json','auth.json','config.env','model_consumer.json','model_upstream.json'}, 'PRIVATE_SOURCE_CONFIG'
    return p


def validate_url_policy(prepared, merger, training_paths=()):
    """Exact encrypted-audit exceptions; no global host/value exemption."""
    policies = prepared.get('encrypted_audit_url_exceptions',[])
    assert isinstance(policies,list), 'URL_EXCEPTION_POLICY_MUST_BE_LIST'
    if not policies: return {}
    assert prepared.get('encrypted_audit_url_policy') == ENCRYPTED_AUDIT_POLICY, 'ENCRYPTED_AUDIT_POLICY_NOT_DECLARED'
    refs = {r['path']:r for r in prepared['files']};seen = set();result = {};sensitive_hashes = set()
    for item in policies:
        name = item['archive_path'];merger.path_name(name);k = name.casefold()
        assert k not in seen and name in refs, 'URL_EXCEPTION_WRONG_OR_DUPLICATE_FILE'
        seen.add(k);ref = refs[name]
        assert ref.get('category') == 'CONTROLLED_AUDIT', 'URL_EXCEPTION_REQUIRES_CONTROLLED_AUDIT'
        assert name not in set(training_paths), 'URL_EXCEPTION_MUST_NOT_BE_DEFAULT_TRAINING_FILE'
        merger.check_hash(item['source_sha256'])
        assert item['source_sha256'] == ref['sha256'], 'URL_EXCEPTION_SOURCE_SHA_MISMATCH'
        matches = item['matches'];assert isinstance(matches,list) and matches, 'EXACT_URL_MATCHES_REQUIRED'
        wanted = {}
        for match in matches:
            layer = match['layer'];assert layer in {'raw','gzip_decoded'}, 'URL_EXCEPTION_LAYER_INVALID'
            merger.check_hash(match['match_sha256']);identity = (layer,match['match_sha256'])
            assert identity not in wanted, 'DUPLICATE_URL_MATCH_POLICY'
            assert type(match['count']) is int and match['count'] > 0, 'URL_EXCEPTION_COUNT_INVALID'
            wanted[identity] = match['count']
        result[name] = wanted;sensitive_hashes.add(ref['sha256'])
    for export in prepared.get('public_exports',[]):
        name = export['archive_path']
        assert name not in result and refs[name]['sha256'] not in sensitive_hashes, 'ENCRYPTED_AUDIT_URL_MUST_NOT_BE_PUBLIC_EXPORT'
    return result


def scan_file(p, needles=(), max_expanded_bytes=2147483648, url_exception=None):
    """Scan raw plus gzip-decoded bytes without printing matching material."""
    patterns = [
      ('KEY_SHAPED_VALUE',re.compile(rb'\bsk-[A-Za-z0-9_-]{24,}\b')),
      ('PRIVATE_KEY_BODY',re.compile(rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----[\r\n]+[A-Za-z0-9+/=]{16,}')),
      ('BEARER_VALUE',re.compile(rb'\bBearer[ \t]+[A-Za-z0-9._~+/-]{24,}')),
      ('JSON_CREDENTIAL_VALUE',re.compile(rb'"(?:api_key|apikey|authorization|password|client_secret|access_token|refresh_token)"\s*:\s*"(?P<value>[^"\r\n]{12,})"',re.I)),
      ('URL_EMBEDDED_PASSWORD',re.compile(rb'https?://[^\s"\x27<>/@:]+:[^\s"\x27<>/@]{6,}@',re.I)),
      ('SIGNED_OR_TOKENIZED_URL',re.compile(rb'https?://[^\s"\x27<>]{1,8192}[?&](?:x-amz-signature|x-amz-credential|signature|sig|access_token|api_key|apikey|token|key-pair-id)=[^&\s"\x27<>]{8,}',re.I)),
    ]
    tailsize = max(16384,max((len(n) for n in needles),default=0))
    count = 0; views = 0;matched_urls = {};seen_urls = set()
    def one(stream, limit, layer):
        nonlocal count, views
        tail = b''; expanded = 0; views += 1
        while True:
            part = stream.read(1048576)
            if not part: break
            start = expanded-len(tail)
            expanded += len(part); assert expanded <= limit, 'SCAN_EXPANSION_LIMIT'
            buf = tail+part
            assert not any(n in buf for n in needles), 'KNOWN_CREDENTIAL_VALUE_IN_PAYLOAD'
            for name, pattern in patterns:
                if name == 'JSON_CREDENTIAL_VALUE':
                    # Exact pre-existing redaction text is not a credential.
                    # No substring/host/hash exception may bypass real values.
                    for match in pattern.finditer(buf):
                        assert match.group('value') == b'<REDACTED_CREDENTIAL>', name
                    continue
                if name != 'SIGNED_OR_TOKENIZED_URL':
                    assert not pattern.search(buf), name
                    continue
                for match in pattern.finditer(buf):
                    match_sha = hashlib.sha256(match.group()).hexdigest()
                    occurrence = (layer,start+match.start(),match_sha)
                    if occurrence in seen_urls: continue
                    seen_urls.add(occurrence);identity = (layer,match_sha)
                    assert url_exception is not None and identity in url_exception, name
                    matched_urls[identity] = matched_urls.get(identity,0)+1
                    assert matched_urls[identity] <= url_exception[identity], 'ENCRYPTED_AUDIT_URL_OCCURRENCE_COUNT_EXCEEDED'
            tail = buf[-tailsize:]; count += len(part)
    with Path(p).open('rb') as f: head = f.read(2)
    with Path(p).open('rb') as f: one(f,max(Path(p).stat().st_size,1),'raw')
    if head == b'\x1f\x8b':
        with gzip.open(p,'rb') as f: one(f,max_expanded_bytes,'gzip_decoded')
    if url_exception is not None:
        assert matched_urls == url_exception, 'ENCRYPTED_AUDIT_URL_EXACT_COUNTS_MISMATCH'
    return {'views':views,'bytes_scanned':count,'encrypted_audit_URL_occurrences':sum(matched_urls.values())}


def audit(allowlist, expected, base, guard_tool, merger_tool, known_credentials=False):
    assert sha(allowlist) == expected, 'ROOT_ALLOWLIST_CHANGED'
    prepared = load(allowlist); assert prepared['schema'] == ALLOWLIST_SCHEMA
    helper = module('trusted_checkpoint05_guard08',guard_tool)
    merger = module('trusted_delta08_validation',merger_tool)
    base = Path(base).resolve(); bm = load(base/'PAYLOAD_MANIFEST.json')
    assert bm['schema'] == merger.BASE_SCHEMA
    assert sha(base/'PAYLOAD_MANIFEST.json') == prepared['base_payload_manifest_sha256'], 'BASE_PAYLOAD_IDENTITY_MISMATCH'
    assert sha(base/'TRAINING_MANIFEST.json') == prepared['base_training_manifest_sha256'], 'BASE_MAIN_IDENTITY_MISMATCH'
    bnames = merger.validate_refs(bm['files']); names = merger.validate_refs(prepared['files'])
    for k in bnames.keys() & names.keys(): assert bnames[k] == names[k], 'CROSS_MANIFEST_CASE_ALIAS'
    assert not any(n in names for n in {x.casefold() for x in AUTO_FILES}), 'AUTO_METADATA_NAME_COLLISION'
    main_ref = next(r for r in prepared['files'] if r['path'] == 'TRAINING_MANIFEST.json')
    main_source = merger.verify_file(guard_source(main_ref['source'],helper),main_ref)
    training_paths = {r['path'] for r in load(main_source)['actual_train_files']}
    url_policy = validate_url_policy(prepared,merger,training_paths)
    needles = helper.credential_needles() if known_credentials else ()
    origins = {}; union = {}; scans = {'files':0,'views':0,'bytes_scanned':0,'encrypted_audit_URL_occurrences':0}
    for ref in bm['files']:
        p = merger.verify_file(merger.safe(base,ref['path']),ref); union[ref['path']] = ref; origins[ref['path']] = p
    for ref in prepared['files']:
        assert ref.get('category') in CATEGORIES, 'EXPLICIT_FILE_CATEGORY_REQUIRED'
        p = guard_source(ref['source'],helper); merger.verify_file(p,ref)
        report = scan_file(p,needles,url_exception=url_policy.get(ref['path']))
        scans['files'] += 1; scans['views'] += report['views']; scans['bytes_scanned'] += report['bytes_scanned']
        scans['encrypted_audit_URL_occurrences'] += report['encrypted_audit_URL_occurrences']
        union[ref['path']] = ref; origins[ref['path']] = p
    merger.validate_refs(list(union.values()))
    assert 'TRAINING_MANIFEST.json' in names.values() and 'ACTUAL_DATA_STATISTICS.json' in names.values(), 'CURRENT_ENTRYPOINT_FILES_REQUIRED_IN_DELTA'
    assert sha(origins['TRAINING_MANIFEST.json']) == prepared['current_training_manifest_sha256'], 'CURRENT_MAIN_PIN_MISMATCH'
    index_rel = prepared.get('canonical_index_relative_path',merger.INDEX_REL)
    pin_rel = prepared.get('canonical_pin_relative_path',merger.PIN_REL)
    assert sha(origins[index_rel]) == prepared['canonical_index_sha256'], 'CURRENT_CANONICAL_INDEX_PIN_MISMATCH'
    training = merger.verify_training(lambda n:origins[n],index_rel,pin_rel)
    exports = prepared.get('public_exports',[]); merger.validate_refs([
        dict(path=x['path'],bytes=union[x['archive_path']]['bytes'],sha256=union[x['archive_path']]['sha256']) for x in exports])
    for export in exports:
        assert export['archive_path'] in names.values(), 'PUBLIC_EXPORT_MUST_BE_EXPLICIT_DELTA_FILE'
        assert not export['path'].startswith(('controlled/','packaging_evidence/')), 'RESERVED_PUBLIC_OUTPUT_PATH'
        assert export['path'] not in {'ENCRYPTED_DELIVERY_REPORT.json','BUILD_RECEIPT.json'}, 'RESERVED_PUBLIC_RECEIPT_PATH'
        assert export.get('root_reviewed_public') is True, 'PUBLIC_EXPORT_REQUIRES_EXPLICIT_ROOT_REVIEW'
    return {'status':'PASS_FROZEN_ALLOWLIST_AND_BASE_UNION','files':len(prepared['files']),
            'source_bytes':sum(r['bytes'] for r in prepared['files']),'scan':scans,
            'known_credential_scan_performed':known_credentials,'generic_raw_and_gzip_scan':'PASS',
            'encrypted_audit_URL_policy':ENCRYPTED_AUDIT_POLICY if url_policy else None,
            'encrypted_audit_URL_exception_files':len(url_policy),
            'URL_exception_does_not_assert_no_sensitive_values':True,
            'canonical_training_QA':training,'allowlist_sha256':expected,'training_started':False}, prepared, origins


def build(a):
    assert not a.dest.exists() and not a.work.exists(), 'NEW_BUILD_AND_PUBLIC_DEST_REQUIRED'
    roots = [p.resolve() for p in [a.base,a.work,a.dest]]
    assert all(not (x.is_relative_to(y) or y.is_relative_to(x)) for i,x in enumerate(roots) for y in roots[i+1:]), 'BASE_BUILD_AND_PUBLIC_ROOTS_MUST_BE_DISJOINT'
    assert sha(a.allowlist) == a.expected_sha256
    freeze_sha256 = sha(a.freeze_receipt)
    freeze = load(a.freeze_receipt)
    assert freeze['status'] == FREEZE_STATUS and freeze['allowlist_sha256'] == a.expected_sha256, 'ROOT_FREEZE_NOT_AUTHORIZED'
    prepared0 = load(a.allowlist)
    for k in ['base_payload_manifest_sha256','base_training_manifest_sha256','current_training_manifest_sha256','canonical_index_sha256']:
        assert freeze[k] == prepared0[k], 'ROOT_FREEZE_PIN_MISMATCH'
    if prepared0.get('encrypted_audit_url_exceptions'):
        policy_sha = hashlib.sha256(json.dumps(prepared0['encrypted_audit_url_exceptions'],ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
        assert freeze.get('encrypted_audit_url_exceptions_sha256') == policy_sha, 'ROOT_ENCRYPTED_AUDIT_POLICY_NOT_FROZEN'
        assert freeze.get('encrypted_audit_url_policy') == ENCRYPTED_AUDIT_POLICY, 'ROOT_ENCRYPTED_AUDIT_DISPOSITION_NOT_FROZEN'
    guard = module('trusted_checkpoint05_guard_key_identity08',a.guard_tool)
    assert a.key.resolve() == Path(guard.KEY).resolve(), 'MUST_REUSE_EXISTING_LOCAL_DELIVERY_KEY'
    report, prepared, origins = audit(a.allowlist,a.expected_sha256,a.base,a.guard_tool,a.merger_tool,known_credentials=True)
    # Stage immutable real byte copies. Source mutation cannot change tar inputs.
    a.work.mkdir(parents=True,exist_ok=False); frozen = a.work/'frozen_files'; frozen.mkdir()
    refs = []
    merger = module('trusted_delta08_build_validation',a.merger_tool)
    for ref in prepared['files']:
        source = origins[ref['path']]; merger.verify_file(source,ref)
        dst = merger.safe(frozen,ref['path']); dst.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(source,dst); merger.verify_file(dst,ref); merger.verify_file(source,ref)
        refs.append({k:ref[k] for k in ['path','bytes','sha256','category']})
    for name,source in [('packaging_evidence/ROOT_ALLOWLIST08.json',a.allowlist),('packaging_evidence/ROOT_FREEZE_RECEIPT08.json',a.freeze_receipt)]:
        # Includes metadata in the same credential scan, rather than exempting it.
        helper = module('trusted_checkpoint05_guard_metadata08',a.guard_tool)
        scan_file(source,helper.credential_needles())
        assert sha(a.allowlist) == a.expected_sha256 and sha(a.freeze_receipt) == freeze_sha256, 'ROOT_FREEZE_INPUT_CHANGED_DURING_BUILD'
        dst = merger.safe(frozen,name); dst.parent.mkdir(parents=True,exist_ok=True); shutil.copyfile(source,dst)
        refs.append({'path':name,'bytes':dst.stat().st_size,'sha256':sha(dst),'category':'QA'})
    merger.validate_refs(refs)
    manifest = {'schema':merger.DELTA_SCHEMA,'files':refs,
      'base_checkpoint_required':'05_plus_06_plus_07_authenticated_merged_root',
      'base_payload_manifest_sha256':prepared['base_payload_manifest_sha256'],
      'base_training_manifest_sha256':prepared['base_training_manifest_sha256'],
      'current_training_manifest_sha256':prepared['current_training_manifest_sha256'],
      'canonical_index_relative_path':prepared.get('canonical_index_relative_path',merger.INDEX_REL),
      'canonical_pin_relative_path':prepared.get('canonical_pin_relative_path',merger.PIN_REL),
      'canonical_index_sha256':prepared['canonical_index_sha256'],
      'prepared_allowlist_sha256':a.expected_sha256,'root_freeze_receipt_sha256':freeze_sha256,
      'encrypted_audit_url_policy':prepared.get('encrypted_audit_url_policy'),
      'encrypted_audit_url_exceptions_sha256':hashlib.sha256(json.dumps(prepared.get('encrypted_audit_url_exceptions',[]),ensure_ascii=False,separators=(',',':')).encode()).hexdigest(),
      'URL_exception_files_are_not_public_exports_or_training_files':True,
      'trusted_tooling_sha256':{'package08.py':sha(Path(__file__)),'merge_delta08.py':sha(a.merger_tool),
                              'checkpoint05_guard':sha(a.guard_tool),'existing_AES_API':sha(a.encrypt_tool)},
      'actual_counts':load(origins['TRAINING_MANIFEST.json'])['actual_counts'],
      'audit_files_are_not_automatic_training_admission':True,'training_started':False,
      'full_WRD_main_training_ready':False}
    pm = a.work/'PAYLOAD_MANIFEST.json'; save(pm,manifest)
    plain = a.work/'wrd-v10-delta08.tar.gz'
    with tarfile.open(plain,'w:gz',compresslevel=3,format=tarfile.PAX_FORMAT) as tf:
        tf.add(pm,arcname='PAYLOAD_MANIFEST.json',recursive=False)
        for ref in refs:
            source = merger.safe(frozen,ref['path']); merger.verify_file(source,ref)
            tf.add(source,arcname=ref['path'],recursive=False)
    assert sha(a.allowlist) == a.expected_sha256, 'ROOT_ALLOWLIST_CHANGED_DURING_BUILD'
    assert sha(a.freeze_receipt) == freeze_sha256, 'ROOT_FREEZE_RECEIPT_CHANGED_DURING_BUILD'
    a.dest.mkdir(parents=True,exist_ok=False); (a.dest/'controlled').mkdir()
    enc = module('trusted_existing_AES_API08',a.encrypt_tool)
    receipt = enc.encrypt(plain,a.dest/'controlled/wrd-v10-delta08.tar.gz.aesgcm',a.key,reuse_key=True)
    receipt.update(schema_version='wrd-v10-checkpoint08-encryption-receipt',payload_manifest_sha256=sha(pm),
        authenticated_files=len(refs)+1,plaintext_bytes=plain.stat().st_size,
        base_payload_manifest_sha256=prepared['base_payload_manifest_sha256'],
        base_training_manifest_sha256=prepared['base_training_manifest_sha256'],
        current_training_manifest_sha256=prepared['current_training_manifest_sha256'],
        prepared_allowlist_sha256=a.expected_sha256,training_started=False,full_WRD_main_training_ready=False)
    save(a.dest/'ENCRYPTED_DELIVERY_REPORT.json',receipt)
    for export in prepared.get('public_exports',[]):
        ref = next(r for r in refs if r['path'] == export['archive_path'])
        source = merger.safe(frozen,ref['path']); dst = merger.safe(a.dest,export['path'])
        dst.parent.mkdir(parents=True,exist_ok=True); shutil.copyfile(source,dst); merger.verify_file(dst,ref)
    report.update(status='BUILT_AUTHENTICATED_DELTA08_PENDING_REAL_MERGE_DUAL_TOKENIZER_AND_REMOTE_QA',
                  authenticated_members=len(refs)+1,ciphertext_bytes=receipt['ciphertext_bytes'],
                  ciphertext_sha256=receipt['ciphertext_sha256'],final_Git_upload_performed=False)
    save(a.work/'BUILD_RECEIPT.json',report)
    print(json.dumps({'status':report['status'],'members':len(refs)+1,'ciphertext_bytes':receipt['ciphertext_bytes']}))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('operation',choices=['audit','build'])
    p.add_argument('--allowlist',type=Path,required=True); p.add_argument('--expected-sha256',required=True)
    p.add_argument('--base',type=Path,default=ROOT/'output/wrd07root02')
    p.add_argument('--guard-tool',type=Path,default=ROOT/'research/data_prep/wrd_main_v10/package_checkpoint05.py')
    p.add_argument('--merger-tool',type=Path,default=Path(__file__).with_name('merge_delta08.py'))
    p.add_argument('--encrypt-tool',type=Path,default=ROOT/'research/data_prep/wrd_reasoning_v4/encrypted_delivery.py')
    p.add_argument('--report',type=Path)
    for name in ['freeze-receipt','key','work','dest']: p.add_argument('--'+name,type=Path)
    a = p.parse_args()
    if a.operation == 'audit':
        assert a.report is None or not a.report.exists(), 'NEW_AUDIT_REPORT_PATH_REQUIRED'
        report,_,_ = audit(a.allowlist,a.expected_sha256,a.base,a.guard_tool,a.merger_tool)
        if a.report: save(a.report,report)
        print(json.dumps(report))
    else:
        assert all(getattr(a,n) is not None for n in ['freeze_receipt','key','work','dest']), 'BUILD_ARGUMENTS_REQUIRED'
        build(a)
