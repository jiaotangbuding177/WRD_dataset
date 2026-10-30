"""Authenticate checkpoint09 and merge explicit files into a NEW root.

Saved payload programs are never imported or run. Canonical array validation is
implemented here with JSON, gzip and struct, rather than invoking a saved loader.
"""
from pathlib import Path, PurePosixPath
from itertools import zip_longest
import argparse, gzip, hashlib, importlib.util, json, math, shutil, struct, sys, tarfile

DELTA_SCHEMA = 'wrd-exact-merged08-authenticated-delta09'
BASE_SCHEMA = 'wrd-authenticated-merged07-plus-delta08-file-union'
INDEX_REL = 'canonical_arrays09/ARRAY_INDEX09.json'
PIN_REL = 'canonical_arrays09/INDEX_PIN09.json'
LOADER_REL = 'canonical_arrays09/binary_loader09.py'
LOADER_SHA256 = '61598377d258f126faeebc6cc2f7f4f9046aec77fb274c6f5a58402995ce122d'
LOADER_APPROVED_EXACT_SHA256 = frozenset({LOADER_SHA256,
    '4a4836cfb78f3d30212ac1e14b7562b443febd40173a2b9b06e42806b5f6099e'})
GENERATED = {'PAYLOAD_MANIFEST.json', 'MERGE_RESULT.json',
             'merge_evidence/merged08_authenticated_manifest.json',
             'merge_evidence/delta09_authenticated_manifest.json'}


def sha(p):
    h = hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(1048576), b''): h.update(b)
    return h.hexdigest()
def unique_object(pairs):
    result = {}
    for k,v in pairs:
        assert k not in result, 'DUPLICATE_JSON_OBJECT_KEY'
        result[k] = v
    return result
def parse(value): return json.loads(value,object_pairs_hook=unique_object)
def load(p): return parse(Path(p).read_text(encoding='utf-8-sig'))
def canonical(v): return json.dumps(v, ensure_ascii=False, separators=(',', ':')).encode()
def save(p, v):
    Path(p).parent.mkdir(parents=True, exist_ok=True)
    Path(p).write_bytes((json.dumps(v, ensure_ascii=False, indent=2)+'\n').encode())
def check_hash(value):
    assert isinstance(value, str) and len(value) == 64 and all(c in '0123456789abcdef' for c in value), 'INVALID_SHA256'
def path_name(name):
    assert isinstance(name, str) and name and not any(c in name for c in '\r\n\x00:\\'), 'UNSAFE_PATH'
    q = PurePosixPath(name)
    assert q.parts and q.as_posix() == name and not q.is_absolute() and '..' not in q.parts, 'NONCANONICAL_PATH'
    assert not any(p.endswith((' ', '.')) for p in q.parts), 'WINDOWS_PATH_ALIAS'
    reserved = {'con','prn','aux','nul', *('com'+str(n) for n in range(1,10)), *('lpt'+str(n) for n in range(1,10))}
    assert not any(p.split('.')[0].casefold() in reserved for p in q.parts), 'WINDOWS_RESERVED_DEVICE'
    return q
def safe(root, name):
    root = Path(root).resolve(); p = root.joinpath(*path_name(name).parts)
    assert p.resolve().is_relative_to(root), 'PATH_ESCAPE'
    for ancestor in [p, *p.parents]:
        assert not ancestor.is_symlink() and not (hasattr(ancestor,'is_junction') and ancestor.is_junction()), 'SYMLINK_OR_JUNCTION'
        if ancestor == root: break
    return p
def validate_refs(refs, reserve_generated=True):
    assert isinstance(refs, list), 'FILES_MUST_BE_LIST'
    seen = {}
    for ref in refs:
        assert isinstance(ref, dict), 'BAD_FILE_REFERENCE'
        n = ref['path']; path_name(n); k = n.casefold()
        assert k not in seen, 'DUPLICATE_OR_CASE_ALIAS_MANIFEST_PATH'
        if reserve_generated:
            assert k not in {x.casefold() for x in GENERATED}, 'RESERVED_GENERATED_PATH'
            assert not k.startswith('history/pre_delta09/'), 'RESERVED_HISTORY_PREFIX'
        assert type(ref['bytes']) is int and ref['bytes'] >= 0, 'INVALID_FILE_SIZE'
        check_hash(ref['sha256']); seen[k] = n
    names = set(seen)
    for k in names:
        parts = k.split('/')
        assert not any('/'.join(parts[:i]) in names for i in range(1,len(parts))), 'FILE_DIRECTORY_PATH_COLLISION'
    return seen
def verify_file(p, ref):
    assert p.is_file() and not p.is_symlink(), 'MISSING_REAL_FILE'
    assert p.stat().st_size == ref['bytes'] and sha(p) == ref['sha256'], 'FILE_PIN_MISMATCH'
    with p.open('rb') as f: header = f.read(128)
    assert not header.splitlines() or header.splitlines()[0] != b'version https://git-lfs.github.com/spec/v1', 'LFS_POINTER_NOT_PAYLOAD'
    return p


def verify_training(resolve, index_relative=INDEX_REL, pin_relative=PIN_REL):
    """Check every declared shard/report/admission and every canonical element.

    resolve(name) supplies a frozen physical file from a merged root or the
    planned exact base+delta union. The manifest alone selects training rows.
    """
    manifest_path = resolve('TRAINING_MANIFEST.json'); m = load(manifest_path)
    assert sha(resolve(LOADER_REL)) in LOADER_APPROVED_EXACT_SHA256, 'CANONICAL09_TRUSTED_LOADER_IDENTITY_MISMATCH'
    for field in ['actual_train_files','active_compilation_reports','external_root_admission_receipts']:
        refs = m.get(field, []); assert isinstance(refs,list)
        seen = set()
        for ref in refs:
            path_name(ref['path']); assert ref['path'].casefold() not in seen, 'DUPLICATE_TRAINING_REFERENCE'
            seen.add(ref['path'].casefold()); p = resolve(ref['path']); check_hash(ref['sha256'])
            assert sha(p) == ref['sha256'], 'TRAINING_REFERENCE_PIN_MISMATCH'
            if 'bytes' in ref: assert p.stat().st_size == ref['bytes']
    idx_path = resolve(index_relative); idx = load(idx_path); pin = load(resolve(pin_relative))
    assert idx['schema'] == 'wrd-canonical-binary-array-index09-v1', 'WRONG_CANONICAL_INDEX_SCHEMA'
    assert pin['index_relative_path'] == index_relative and pin['index_bytes'] == idx_path.stat().st_size
    assert sha(idx_path) == pin['index_sha256'], 'CANONICAL_INDEX_PIN_MISMATCH'
    assert idx['manifest_relative_path'] == 'TRAINING_MANIFEST.json'
    assert idx['manifest_sha256'] == pin['manifest_sha256'] == sha(manifest_path), 'CANONICAL_MANIFEST_PIN_MISMATCH'
    records = idx['records']; assert isinstance(records,list) and len(records) == idx['record_count']
    def rows():
        for ref in m['actual_train_files']:
            with gzip.open(resolve(ref['path']),'rt',encoding='utf-8-sig') as f:
                ordinal = 0
                for line in f:
                    if not line.strip(): continue
                    yield ref['path'], ordinal, parse(line); ordinal += 1
    seen_ids = set(); paths = set(); counts = {'sequences':0,'input_tokens':0,'supervised_tokens':0,'binary_files':0,'binary_bytes':0}
    for position, (entry, source) in enumerate(zip_longest(records, rows())):
        assert entry is not None and source is not None, 'CANONICAL_ROW_COUNT_MISMATCH'
        file_name, ordinal, row = source; ids = row['input_ids']; n = len(ids)
        assert row['id'] not in seen_ids, 'DUPLICATE_ROW_OWNER'; seen_ids.add(row['id'])
        assert entry['position'] == position and entry['source_train_file'] == file_name and entry['source_record_index'] == ordinal
        assert entry['id'] == row['id'] and entry['total_tokens'] == row['total_tokens'] == n and 0 < n <= 32768
        assert all(type(t) is int and 0 <= t <= 4294967295 for t in ids), 'INVALID_TOKEN_ID'
        spans = row['supervision_spans']; span_sha = hashlib.sha256(canonical(spans)).hexdigest()
        assert span_sha == row['supervision_spans_sha256'] == entry['supervision_spans_sha256'], 'SPAN_PIN_MISMATCH'
        expected_labels = [-100]*n; expected_weights = [0.]*n; last = 0; positive = 0
        for lo, hi, _, w in spans:
            assert type(lo) is int and type(hi) is int and 0 <= last <= lo < hi <= n
            assert type(w) in (int,float) and math.isfinite(w) and 0 < w <= 1
            for i in range(lo,hi): expected_labels[i] = ids[i]; expected_weights[i] = w
            positive += hi-lo; last = hi
        assert positive == row['supervised_tokens'] == entry['supervised_tokens']
        refs = entry['arrays']; assert set(refs) == {'input_ids','labels','loss_weights'}
        expected = {'input_ids':('I','uint32_le',ids), 'labels':('q','int64_le',expected_labels),
                    'loss_weights':('f','float32_le',expected_weights)}
        for name, (kind, dtype, values) in expected.items():
            ref = refs[name]; path_name(ref['path']); k = ref['path'].casefold()
            assert k not in paths and ref['path'].startswith(index_relative.rsplit('/',1)[0]+'/arrays/'), 'CANONICAL_BINARY_PATH_COLLISION'
            paths.add(k); assert ref['dtype'] == dtype
            p = verify_file(resolve(ref['path']), ref); b = p.read_bytes()
            want = struct.pack('<'+kind*n, *values)
            assert b == want, 'CANONICAL_ARRAY_DISAGREES_WITH_SOURCE_SPANS_'+name.upper()
            if name == 'input_ids': assert ref['sha256'] == row['input_ids_sha256_u32le']
            counts['binary_files'] += 1; counts['binary_bytes'] += len(b)
        counts['sequences'] += 1; counts['input_tokens'] += n; counts['supervised_tokens'] += positive
    for key in ['sequences','input_tokens','supervised_tokens']:
        assert counts[key] == m['actual_counts'][key], 'ACTUAL_COUNTS_MISMATCH'
    assert counts['sequences'] == idx['record_count'] and counts['input_tokens'] == idx['input_tokens']
    assert counts['supervised_tokens'] == idx['supervised_tokens'] and counts['binary_files'] == idx['binary_files']
    assert counts['binary_bytes'] == idx['binary_bytes']
    return dict(status='PASS_ALL_MANIFEST_REFERENCES_AND_CANONICAL_ARRAY_ELEMENTS', **counts,
                legacy_binary_arrays_ignored=True, saved_payload_source_executed=False, training_started=False)


def plan_union(base, delta):
    base = Path(base).resolve(); delta = Path(delta).resolve()
    bm = load(base/'PAYLOAD_MANIFEST.json'); dm = load(delta/'PAYLOAD_MANIFEST.json')
    assert bm['schema'] == BASE_SCHEMA and dm['schema'] == DELTA_SCHEMA, 'WRONG_CHECKPOINT_SCHEMA'
    assert sha(base/'PAYLOAD_MANIFEST.json') == dm['base_payload_manifest_sha256'], 'BASE_PAYLOAD_IDENTITY_MISMATCH'
    assert sha(base/'TRAINING_MANIFEST.json') == dm['base_training_manifest_sha256'], 'BASE_TRAINING_IDENTITY_MISMATCH'
    bnames = validate_refs(bm['files']); dnames = validate_refs(dm['files'])
    for k in bnames.keys() & dnames.keys(): assert bnames[k] == dnames[k], 'CROSS_MANIFEST_CASE_ALIAS'
    union = {}; origins = {}
    for root, refs in [(base,bm['files']),(delta,dm['files'])]:
        for ref in refs:
            p = verify_file(safe(root,ref['path']),ref); union[ref['path']] = ref; origins[ref['path']] = p
    validate_refs(list(union.values()))
    assert sha(origins['TRAINING_MANIFEST.json']) == dm['current_training_manifest_sha256'], 'CURRENT_MAIN_PIN_MISMATCH'
    index_rel = dm.get('canonical_index_relative_path',INDEX_REL)
    assert sha(origins[index_rel]) == dm['canonical_index_sha256'], 'CURRENT_CANONICAL_INDEX_PIN_MISMATCH'
    return bm, dm, union, origins


def merge_restored(base, delta, out):
    base = Path(base).resolve(); delta = Path(delta).resolve(); out = Path(out).resolve()
    assert base.is_dir() and delta.is_dir() and not out.exists(), 'NEW_OUTPUT_ROOT_REQUIRED'
    roots = [base,delta,out]
    assert all(not (a.is_relative_to(b) or b.is_relative_to(a)) for i,a in enumerate(roots) for b in roots[i+1:]), 'ROOTS_MUST_BE_DISJOINT'
    bm, dm, union, origins = plan_union(base,delta)
    index_rel = dm.get('canonical_index_relative_path', INDEX_REL); pin_rel = dm.get('canonical_pin_relative_path', PIN_REL)
    qa = verify_training(lambda n: origins[n], index_rel, pin_rel)
    out.mkdir(parents=True, exist_ok=False); combined = {}; replaced = []
    def copy(ref, origin, name=None):
        name = name or ref['path']; dst = safe(out,name); dst.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(origin,dst); verify_file(dst, dict(ref,path=name))
        combined[name] = {'path':name,'bytes':ref['bytes'],'sha256':ref['sha256']}
    for ref in bm['files']: copy(ref,safe(base,ref['path']))
    for ref in dm['files']:
        old = combined.get(ref['path'])
        if old and old['sha256'] != ref['sha256']:
            name = 'history/pre_delta09/'+old['sha256']+'/'+ref['path']
            assert name not in combined
            copy(old,safe(out,ref['path']),name)
            replaced.append({'path':ref['path'],'old_sha256':old['sha256'],'preserved_at':name})
        copy(ref,safe(delta,ref['path']))
    for label, root in [('merged08',base),('delta09',delta)]:
        p = root/'PAYLOAD_MANIFEST.json'; name = 'merge_evidence/'+label+'_authenticated_manifest.json'
        copy({'path':name,'bytes':p.stat().st_size,'sha256':sha(p)},p)
    validate_refs(list(combined.values()),reserve_generated=False)
    merged = {'schema':'wrd-authenticated-merged08-plus-delta09-file-union','files':list(combined.values()),
              'base_authenticated_manifest_sha256':sha(base/'PAYLOAD_MANIFEST.json'),
              'delta_authenticated_manifest_sha256':sha(delta/'PAYLOAD_MANIFEST.json'),
              'current_training_manifest_sha256':sha(out/'TRAINING_MANIFEST.json'),
              'canonical_index_relative_path':index_rel,'no_saved_source_executed':True,'training_started':False}
    save(out/'PAYLOAD_MANIFEST.json',merged)
    output_qa = verify_training(lambda n: safe(out,n),index_rel,pin_rel); assert output_qa == qa
    proof = {'status':'PASS_AUTHENTICATED_MERGED08_AND_DELTA09_EXPLICIT_NEW_ROOT',
             'base_files':len(bm['files']),'delta_files':len(dm['files']),'merged_files':len(combined),
             'replaced_old_bytes_preserved':replaced,'canonical_QA':qa,'training_started':False,
             'requires_independent_dual_tokenizer_and_remote_QA':True}
    save(out/'MERGE_RESULT.json',proof); return proof


def main(a):
    # This is an explicitly trusted local delivery tool, never archive content.
    assert a.restore_tool.is_file() and sha(a.restore_tool) == a.restore_tool_sha256, 'RESTORE_TOOL_PIN_MISMATCH'
    assert not a.delta_out.exists() and not a.out.exists(), 'NEW_RESTORE_AND_MERGE_ROOTS_REQUIRED'
    roots = [p.resolve() for p in [a.base,a.delta_out,a.out]]
    assert all(not (x.is_relative_to(y) or y.is_relative_to(x)) for i,x in enumerate(roots) for y in roots[i+1:]), 'ROOTS_MUST_BE_DISJOINT_BEFORE_DECRYPT'
    s = importlib.util.spec_from_file_location('trusted_checkpoint05_restore',a.restore_tool)
    restore = importlib.util.module_from_spec(s)
    previous = sys.dont_write_bytecode; sys.dont_write_bytecode = True
    try: s.loader.exec_module(restore)
    finally: sys.dont_write_bytecode = previous
    authenticated = strict_restore(restore,a.cipher,a.receipt,a.key,a.delta_out)
    proof = merge_restored(a.base,a.delta_out,a.out)
    proof['authenticated_delta_members'] = authenticated['authenticated_files']
    save(a.out/'MERGE_RESULT.json',proof); print(json.dumps(proof))


def strict_restore(restore, cipher, receipt_path, key, out):
    """Keep checkpoint05 AES protocol; validate all names before extraction.

    Its unchanged decrypt API authenticates ciphertext before publishing the
    plaintext tar. We strengthen manifest/path checks before writing members.
    """
    cipher = Path(cipher); out = Path(out); receipt = load(receipt_path)
    for field in ['ciphertext_sha256','plaintext_sha256','payload_manifest_sha256']: check_hash(receipt[field])
    assert cipher.stat().st_size >= len(restore.MAGIC)+12+16 and sha(cipher) == receipt['ciphertext_sha256'], 'CIPHER_PIN_MISMATCH'
    out.mkdir(parents=True,exist_ok=False); plain = out/'payload.verified.tar.gz'
    assert restore.decrypt(cipher,Path(key),plain) == receipt['plaintext_sha256'], 'PLAIN_PIN_MISMATCH'
    found = set()
    with tarfile.open(plain,'r|gz') as tf:
        first = tf.next()
        assert first and first.name == 'PAYLOAD_MANIFEST.json' and first.isfile() and first.size <= 67108864, 'MANIFEST_MUST_BE_FIRST_REGULAR_FILE'
        raw = tf.extractfile(first).read()
        assert hashlib.sha256(raw).hexdigest() == receipt['payload_manifest_sha256'], 'PAYLOAD_MANIFEST_PIN_MISMATCH'
        dm = parse(raw); assert dm['schema'] == DELTA_SCHEMA
        validate_refs(dm['files']); expected = {r['path']:r for r in dm['files']}
        (out/'PAYLOAD_MANIFEST.json').write_bytes(raw)
        while True:
            member = tf.next()
            if member is None: break
            assert member.isfile() and member.name in expected and member.name not in found, 'UNEXPECTED_OR_DUPLICATE_MEMBER'
            ref = expected[member.name]; assert member.size == ref['bytes'], 'ARCHIVE_MEMBER_SIZE_MISMATCH'
            dst = safe(out,member.name); dst.parent.mkdir(parents=True,exist_ok=True)
            with tf.extractfile(member) as source, dst.open('xb') as target:
                shutil.copyfileobj(source,target,1048576)
            verify_file(dst,ref); found.add(member.name)
    assert found == set(expected), 'MISSING_ARCHIVE_MEMBERS'
    return {'status':'PASS_CHECKPOINT05_AES_AND_STRICT_EXPLICIT_TAR_EXTRACTION',
            'authenticated_files':len(found)+1,'training_started':False}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for n in ['base','cipher','receipt','key','out','delta-out','restore-tool']: p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--restore-tool-sha256',required=True)
    main(p.parse_args())
