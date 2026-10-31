"""Actual restored-root full623 audit; never constructs or restores the root.

Run only after root reports authenticated checkpoint10 merge completion.
Calls the existing full audit afresh on that root, rather than reusing stage QA.
"""
from pathlib import Path
from types import SimpleNamespace
import argparse
import hashlib
import importlib.util
import json
import os
import sys
import time

os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
os.environ['USE_TORCH'] = '0'
os.environ['USE_TF'] = '0'
os.environ['TOKENIZERS_PARALLELISM'] = 'false'
ROOT = Path('D:/skillloop')
EXPECTED_MAIN = '9aace2dc6b39d0dde3bafbf9f7f3d6763e485609017dd70a5c40c17a2c30277e'


def pin(path):
    path = Path(path)
    h = hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda: f.read(1048576), b''):
            h.update(b)
    return {'path': str(path), 'bytes': path.stat().st_size, 'sha256': h.hexdigest()}


def load(path):
    return json.loads(Path(path).read_text('utf-8-sig'))


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    obj = importlib.util.module_from_spec(spec)
    previous = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        spec.loader.exec_module(obj)
    finally:
        sys.dont_write_bytecode = previous
    return obj


def main(a):
    started = time.time()
    restored = a.root.resolve()
    assert restored == (ROOT / 'output/wrd10root01').resolve(), 'EXACT_REAL_RESTORE_ROOT_REQUIRED'
    assert restored.is_dir(), 'WAIT_FOR_REAL_AUTHENTICATED_MERGE_ROOT'
    assert not a.out.exists(), 'NEW_QA_OUTPUT_DIRECTORY_REQUIRED'
    pm = restored / 'PAYLOAD_MANIFEST.json'
    main_manifest = restored / 'TRAINING_MANIFEST.json'
    merge_receipt = restored / 'MERGE_RESULT.json'
    for p in (pm, main_manifest, merge_receipt):
        assert p.is_file(), ('REAL_MERGE_OUTPUT_MISSING', p.name)
    assert pin(main_manifest)['sha256'] == EXPECTED_MAIN
    payload = load(pm)
    merge_result = load(merge_receipt)
    assert payload['schema'] == 'wrd-authenticated-merged09-plus-delta10-file-union'
    assert payload['no_saved_source_executed'] is True and payload['training_started'] is False
    assert merge_result['status'] == 'PASS_AUTHENTICATED_MERGED09_AND_DELTA10_EXPLICIT_NEW_ROOT'
    assert merge_result['canonical_QA']['sequences'] == 623
    assert merge_result['training_started'] is False
    delta_manifest = restored / 'merge_evidence/delta10_authenticated_manifest.json'
    old_manifest = restored / 'merge_evidence/merged09_authenticated_manifest.json'
    delta = load(delta_manifest)
    assert delta['schema'] == 'wrd-exact-merged09-authenticated-delta10'
    assert delta['current_training_manifest_sha256'] == EXPECTED_MAIN
    assert delta['base_payload_manifest_sha256'] == pin(old_manifest)['sha256']
    assert pin(old_manifest)['sha256'] == pin(ROOT / 'output/wrd09root01/PAYLOAD_MANIFEST.json')['sha256']
    assert payload['base_authenticated_manifest_sha256'] == pin(old_manifest)['sha256']
    assert payload['delta_authenticated_manifest_sha256'] == pin(delta_manifest)['sha256']
    assert payload['current_training_manifest_sha256'] == EXPECTED_MAIN
    toolkit = ROOT / 'research/data_prep/wrd_curation10'
    for name in ('package10.py', 'merge_delta10.py'):
        assert pin(toolkit / name)['sha256'] == delta['trusted_tooling_sha256'][name]
    merger = module('lineage_actual_restored10_port_verifier', toolkit / 'merge_delta10.py')
    # Require an approved exact byte identity before the full audit imports the
    # saved canonical loader; text/newline equivalence is not sufficient here.
    loader_pin = pin(restored / 'canonical_arrays10/binary_loader10.py')
    assert loader_pin['sha256'] in merger.LOADER_APPROVED_EXACT_SHA256
    for name in ('primary_14b', 'control_8b'):
        assert (a.assets / name / 'tokenizer.json').is_file(), ('TOKENIZER_ASSET_MISSING', name)
    a.out.mkdir(parents=True, exist_ok=False)
    detail = a.out / 'FULL623_FRESH_RUN_DETAIL.json'
    auditor_path = toolkit / 'lineage_verify_staged623.py'
    auditor = module('lineage_real_restore10_fresh_auditor', auditor_path)
    # The library retains its historical staged623 status string. This call
    # creates a NEW detail result from the actual restored root, not a copy.
    auditor.main(SimpleNamespace(root=restored, assets=a.assets, out=detail))
    actual = load(detail)
    assert actual['root'] == str(restored)
    assert actual['manifest']['sha256'] == EXPECTED_MAIN
    assert actual['standard_QA']['every_row_direct_dual_tokenized'] == 623
    assert actual['retained_original_rows_byte_exact'] == 594
    assert actual['new_views_exact_compiled29_membership'] == 29
    assert actual['canonical']['binary_files'] == 1869
    assert actual['four_features_all_rows_equal'] is True
    assert actual['all1869_array_body_SHA_and_little_endian_bytes_equal'] is True
    assert actual['actual_in_memory_prompt_label_negative_canary'] == 'REJECTED_INPUT_OR_ROLE_HEADER_HAS_LOSS'
    declarative = merger.verify_training(lambda n: merger.safe(restored, n))
    assert declarative['sequences'] == 623 and declarative['supervised_tokens'] == 227233
    assert declarative['input_tokens'] == 3853977 and declarative['binary_files'] == 1869
    result = {
        'status': 'PASS_INDEPENDENT_REAL_RESTORED10_ALL623_DUAL_TOKEN_MASK_SOURCE_ABI_594_BYTES_29_MEMBERS_AND_FOUR_FEATURES',
        'reviewer': '/root/curation10_lineage', 'actual_restored_root': str(restored),
        'actual_restored_root_existed_before_run': True,
        'full623_executed_afresh_on_actual_root': True,
        'stage_QA_result_reused_as_restore': False,
        'restored_payload_manifest': pin(pm), 'restored_training_manifest': pin(main_manifest),
        'actual_merge_receipt': pin(merge_receipt), 'authenticated_delta_manifest': pin(delta_manifest),
        'authenticated_base09_manifest': pin(old_manifest), 'fresh_full623_detail': pin(detail),
        'exact_loader_pin_checked_before_import': loader_pin,
        'fresh_full623_standard_QA': actual['standard_QA'], 'canonical': actual['canonical'],
        'retained_original_rows_byte_exact': 594, 'new_views_exact_compiled29_membership': 29,
        'four_features_all_rows_equal': True,
        'actual_prompt_label_negative_canary': actual['actual_in_memory_prompt_label_negative_canary'],
        'additional_no_saved_source_array_verification': declarative,
        'script_pin': pin(__file__), 'full_auditor_script_pin': pin(auditor_path),
        'verify_main10_pin': pin(toolkit / 'verify_main10.py'),
        'elapsed_seconds': round(time.time() - started, 3),
        'this_audit_did_not_decrypt_again': True,
        'this_audit_verifies_root_of_completed_authenticated_merge': True,
        'remote_QA_performed_by_this_audit': False, 'model_weights_loaded': False,
        'training_started': False, 'new_business_calls': 0,
        'semantic_effectiveness_not_inferred_from_array_checks': True,
    }
    destination = a.out / 'INDEPENDENT_REAL_RESTORED10_QA.json'
    destination.write_bytes((json.dumps(result, ensure_ascii=False, indent=2) + '\n').encode())
    print(json.dumps({'status': result['status'], 'output': pin(destination)}), flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', type=Path, default=ROOT / 'output/wrd10root01')
    p.add_argument('--assets', type=Path, default=ROOT / 'output/20261025_wrd_training_preflight/tokenizer_assets')
    p.add_argument('--out', type=Path, default=ROOT / 'output/20261031_wrd_curation10_delivery/restored_full_qa01')
    main(p.parse_args())
