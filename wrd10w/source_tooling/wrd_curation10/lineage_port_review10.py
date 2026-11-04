"""Independent, key-free checkpoint10 source-port and active-data review.

This is not an encryption/restore run. Synthetic scanner fixtures live only in
one explicitly named temporary file outside the delivery tree and are removed.
"""
from pathlib import Path
import ast
import copy
import difflib
import gzip
import hashlib
import importlib.util
import json
import os
import re
import sys
import tempfile
import uuid

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'output/20261031_wrd_curation10/delivery_review'
DATA = ROOT / 'output/20261027_wrd_main_v10'
BASE = ROOT / 'output/wrd09root01'


def sha(p):
    h = hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda: f.read(1048576), b''):
            h.update(b)
    return h.hexdigest()


def load(p):
    return json.loads(Path(p).read_text('utf-8-sig'))


def module(label, p):
    spec = importlib.util.spec_from_file_location(label, p)
    obj = importlib.util.module_from_spec(spec)
    old = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        spec.loader.exec_module(obj)
    finally:
        sys.dont_write_bytecode = old
    return obj


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    paths = {f'{name}{v}.py': ROOT / f'research/data_prep/wrd_curation{v}/{name}{v}.py'
             for v in ('09', '10') for name in ('package', 'merge_delta', 'admit')}
    paths['checkpoint05_guard'] = ROOT / 'research/data_prep/wrd_main_v10/package_checkpoint05.py'
    paths['existing_AES_API'] = ROOT / 'research/data_prep/wrd_reasoning_v4/encrypted_delivery.py'
    sources = {name: {'path': str(p), 'bytes': p.stat().st_size, 'sha256': sha(p)}
               for name, p in paths.items()}
    auth09 = load(BASE / 'merge_evidence/delta09_authenticated_manifest.json')
    authenticated_unchanged = {}
    for name, expected in auth09['trusted_tooling_sha256'].items():
        assert sources[name]['sha256'] == expected, ('AUTHENTICATED_09_TOOL_CHANGED', name)
        authenticated_unchanged[name] = expected
    bm = load(BASE / 'PAYLOAD_MANIFEST.json')
    old_admit_refs = [r for r in bm['files'] if r['path'].endswith('/admit09.py')]
    assert old_admit_refs and all(r['sha256'] == sources['admit09.py']['sha256'] for r in old_admit_refs)
    authenticated_unchanged['admit09.py'] = sources['admit09.py']['sha256']
    literals = {}
    diff_meta = {}
    for name in ('package', 'merge_delta', 'admit'):
        a, b = (paths[f'{name}{v}.py'].read_text('utf-8') for v in ('09', '10'))
        for v, text in [('09', a), ('10', b)]:
            literals[f'{name}{v}.py'] = sorted({n.value for n in ast.walk(ast.parse(text))
                if isinstance(n, ast.Constant) and isinstance(n.value, str)
                and re.fullmatch('[0-9a-f]{64}', n.value)})
        diff = '\n'.join(difflib.unified_diff(a.splitlines(), b.splitlines(), n=1))
        diff_meta[name] = {'unified_diff_sha256_utf8': hashlib.sha256(diff.encode()).hexdigest(),
                           'changed_hunks': sum(x.startswith('@@') for x in diff.splitlines())}
    assert literals['package09.py'] == literals['package10.py'] == []
    assert literals['admit09.py'] == literals['admit10.py'] == [
        'edf1d3b8e1834fd7205e2f920112408cbeb062271ca372e509be2149ae3d8777']
    pkg = module('lineage_package10_review', paths['package10.py'])
    merger = module('lineage_merge10_review', paths['merge_delta10.py'])
    admit = module('lineage_admit10_review', paths['admit10.py'])
    assert bm['schema'] == merger.BASE_SCHEMA == 'wrd-authenticated-merged08-plus-delta09-file-union'
    assert merger.DELTA_SCHEMA == 'wrd-exact-merged09-authenticated-delta10'
    assert sha(admit.LOADER_SOURCE) == admit.LOADER_SOURCE_SHA
    code = admit.loader_code().replace('\r\n', '\n')
    loader_hashes = {'LF': hashlib.sha256(code.encode()).hexdigest(),
                     'CRLF': hashlib.sha256(code.replace('\n', '\r\n').encode()).hexdigest()}
    assert set(loader_hashes.values()) == set(merger.LOADER_APPROVED_EXACT_SHA256)
    assert set(literals['merge_delta10.py']) == set(loader_hashes.values())
    active_loader_sha = sha(DATA / merger.LOADER_REL)
    assert active_loader_sha in set(loader_hashes.values())
    tests = []

    def reject(label, fn):
        try:
            fn()
        except (AssertionError, ValueError, KeyError, TypeError):
            tests.append({'case': label, 'result': 'REJECTED_AS_EXPECTED'})
        else:
            raise AssertionError(('CANARY_NOT_REJECTED', label))

    for label, name in [
        ('parent_traversal', '../escape'), ('absolute_posix', '/escape'),
        ('absolute_windows', 'C:/escape'), ('backslash', 'a\\b'),
        ('windows_ADS', 'a:b'), ('newline', 'a\nb'), ('carriage_return', 'a\rb'),
        ('nul', 'a\0b'), ('trailing_dot', 'a./b'), ('trailing_space', 'a /b'),
        ('device_CON', 'a/CON.txt'), ('device_COM', 'COM9/x'),
        ('device_LPT', 'lpt1.txt'), ('double_separator', 'a//b'),
        ('dot_segment', 'a/./b'), ('leading_dot_segment', './a')]:
        reject('path_' + label, lambda name=name: merger.path_name(name))
    assert merger.path_name('clear/a.json').as_posix() == 'clear/a.json'
    def ref(name, size=0):
        return {'path': name, 'bytes': size, 'sha256': '0' * 64}
    for label, refs in [
        ('duplicate', [ref('a'), ref('a')]), ('case_alias', [ref('Ab'), ref('aB')]),
        ('file_directory', [ref('a'), ref('a/b')]),
        ('generated', [ref('PAYLOAD_MANIFEST.json')]),
        ('reserved_history', [ref('history/pre_delta10/x')]),
        ('negative_size', [ref('a', -1)]), ('bool_size', [ref('a', True)])]:
        reject('refs_' + label, lambda refs=refs: merger.validate_refs(refs))
    for label, value in [('short', '0' * 63), ('uppercase', 'A' * 64), ('wrong_type', 0)]:
        reject('hash_' + label, lambda value=value: merger.check_hash(value))
    merger.check_hash('a' * 64)
    reject('json_duplicate_top', lambda: merger.parse('{"x":1,"x":2}'))
    reject('json_duplicate_nested', lambda: merger.parse('{"a":{"x":1,"x":2}}'))
    # No real key or credential file is opened. All fixture values are artificial.
    tmp = Path(tempfile.gettempdir()).resolve() / ('wrd10_lineage_review_' + uuid.uuid4().hex + '.tmp')
    assert tmp.parent == Path(tempfile.gettempdir()).resolve() and not tmp.exists()
    try:
        cases = {
            'known_needle': (b'fixture-' + b'n' * 24, [b'fixture-' + b'n' * 24]),
            'key_shape': (b'sk' + b'-' + b'x' * 28, []),
            'bearer': (b'Bearer ' + b'x' * 28, []),
            'json_credential': (json.dumps({'api_key': 'x' * 28}).encode(), []),
            'private_key': (b'-----BEGIN ' + b'PRIVATE KEY-----\n' + b'x' * 28, []),
            'url_password': (b'https://' + b'user:' + b'p' * 8 + b'@example.invalid/', []),
            'signed_url': (b'https://example.invalid/a?' + b'token=' + b'x' * 16, []),
        }
        for name, (body, needles) in cases.items():
            tmp.write_bytes(body)
            reject('scan_' + name, lambda needles=needles: pkg.scan_file(tmp, needles))
        tmp.write_bytes(gzip.compress(cases['bearer'][0]))
        reject('scan_gzip_decoded', lambda: pkg.scan_file(tmp))
        tmp.write_bytes(json.dumps({'api_key': '<REDACTED_CREDENTIAL>'}).encode())
        assert pkg.scan_file(tmp)['views'] == 1
        signed = cases['signed_url'][0]
        tmp.write_bytes(signed)
        match_sha = hashlib.sha256(signed).hexdigest()
        assert pkg.scan_file(tmp, url_exception={('raw', match_sha): 1})['encrypted_audit_URL_occurrences'] == 1
        reject('scan_wrong_exception_count', lambda: pkg.scan_file(tmp, url_exception={('raw', match_sha): 2}))
        reject('scan_wrong_exception_sha', lambda: pkg.scan_file(tmp, url_exception={('raw', '0' * 64): 1}))
    finally:
        if tmp.exists():
            assert tmp.resolve().parent == Path(tempfile.gettempdir()).resolve()
            tmp.unlink()
    policy = {'files': [dict(ref('audit/file.txt'), category='CONTROLLED_AUDIT')],
        'encrypted_audit_url_policy': pkg.ENCRYPTED_AUDIT_POLICY,
        'encrypted_audit_url_exceptions': [{'archive_path': 'audit/file.txt', 'source_sha256': '0' * 64,
             'matches': [{'layer': 'raw', 'match_sha256': 'a' * 64, 'count': 1}]}]}
    assert pkg.validate_url_policy(policy, merger) == {'audit/file.txt': {('raw', 'a' * 64): 1}}
    reject('url_policy_training_path', lambda: pkg.validate_url_policy(policy, merger, ['audit/file.txt']))
    for label, mutate in [
        ('category', lambda p: p['files'][0].update(category='TRAINING')),
        ('source_sha', lambda p: p['encrypted_audit_url_exceptions'][0].update(source_sha256='1' * 64)),
        ('public_export', lambda p: p.update(public_exports=[{'archive_path': 'audit/file.txt'}])),
        ('count', lambda p: p['encrypted_audit_url_exceptions'][0]['matches'][0].update(count=0)),
        ('layer', lambda p: p['encrypted_audit_url_exceptions'][0]['matches'][0].update(layer='arbitrary'))]:
        bad = copy.deepcopy(policy)
        mutate(bad)
        reject('url_policy_' + label, lambda bad=bad: pkg.validate_url_policy(bad, merger))
    active_qa = merger.verify_training(lambda name: merger.safe(DATA, name))
    assert active_qa['sequences'] == 623 and active_qa['supervised_tokens'] == 227233
    assert active_qa['input_tokens'] == 3853977 and active_qa['binary_files'] == 1869
    manifest_sha = sha(DATA / 'TRAINING_MANIFEST.json')
    assert manifest_sha == '9aace2dc6b39d0dde3bafbf9f7f3d6763e485609017dd70a5c40c17a2c30277e'
    result = {
        'status': 'PASS_SOURCE_PORT_CONTRACT_KEY_FREE_GUARDS_AND_ACTIVE_DATA_PREFLIGHT_NOT_REAL_RESTORE',
        'reviewer': '/root/curation10_lineage', 'review_script_sha256': sha(__file__),
        'sources': sources, 'authenticated09_tools_unchanged': authenticated_unchanged,
        'base09_payload_manifest_sha256': sha(BASE / 'PAYLOAD_MANIFEST.json'),
        'base09_schema': bm['schema'], 'delta10_schema': merger.DELTA_SCHEMA,
        'base09_compatibility': 'MATCHES_ACTUAL_AUTHENTICATED09_MERGED_ROOT',
        'sha256_literals_AST': literals, 'source_diff_metadata': diff_meta,
        'approved_loader_exact_byte_hashes': loader_hashes,
        'old07_loader_source_sha256_unchanged': sha(admit.LOADER_SOURCE),
        'active10_loader_sha256': active_loader_sha,
        'negative_canaries': tests, 'negative_canary_count': len(tests),
        'active_training_manifest_sha256': manifest_sha, 'active_data_preflight': active_qa,
        'tar_contract_review': {
            'receipt_cipher_plain_manifest_pins_checked': True,
            'authenticated_decrypt_before_tar_member_read': True,
            'manifest_first_regular_and_bounded': True,
            'manifest_names_validated_before_member_extraction': True,
            'members_exact_manifest_set_regular_only_unique_size_and_sha': True,
            'exclusive_file_create_and_new_disjoint_roots': True,
            'saved_payload_source_never_imported_by_merge': True,
            'old_replaced_bytes_preserved_under_content_sha_history': True,
            'runtime_tar_adversarial_fixture_executed': False},
        'admit10_contract_review': {
            'script_and_all_frozen_input_pins_checked': True,
            'retained_json_lines_copied_as_bytes': True,
            'root_semantic_and_peer_receipts_required': True,
            'exact_new_id_and_revocation_sets': True,
            'new_R_provenance_and_new_A_identity_assertions': True,
            'stage_does_not_activate_and_exact_sha_activation': True,
            'activation_keeps_old_manifest_and_statistics': True,
            'admission_safe_is_not_general_untrusted_archive_validator': True,
            'admit_does_not_explicitly_enforce_windows_devices_case_alias_or_all_junction_ancestors': True,
            'scope': 'ROOT_FROZEN_TRUSTED_INPUTS_PLUS_STRONGER_FINAL_PACKAGE_MERGE_VALIDATION'},
        'review_boundaries': [
            'Source diff read and old authenticated hashes checked; package and merger guards unchanged except declared version/path/schema/loader identities.',
            'admit10 adds explicit recontextualized R/A provenance accounting and counts only targets with owned positive spans.',
            'active-data preflight checked all source references and canonical byte arrays, not a checkpoint10 restoration.',
            'Dual tokenizer and exact semantic masks were independently checked in full_stage_qa01; current review does not claim a new restored-root tokenizer run.',
            'No real encryption key read, encryption, restore, remote download, model inference or training in this review.',
            'Exclude locally generated .pyc.evidence diagnostic bytes from default payload; preserve diagnostic metadata and source records.'],
        'real_checkpoint10_restore_performed': False, 'real_checkpoint10_restore_status': 'NOT_YET_RUN',
        'remote_QA_performed': False, 'training_started': False, 'model_weights_loaded': False,
    }
    target = OUT / 'PORT_REVIEW10.json'
    target.write_bytes((json.dumps(result, ensure_ascii=False, indent=2) + '\n').encode())
    print(json.dumps({'path': str(target), 'sha256': sha(target), 'canaries': len(tests), 'active_data': active_qa}))


if __name__ == '__main__':
    main()
