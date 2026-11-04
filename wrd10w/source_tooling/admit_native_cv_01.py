"""Publish root's scoped CV process admission after independent semantic QA.

All original R ranges and ten full action arguments were read by root. Whole
resource writes/final hiring judgments remain masked; no training is launched.
"""
from pathlib import Path
import gzip
import hashlib
import json

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'output/20261027_wrd_main_v10'
SOURCE = OUT / 'native_CV_B_training_01'
BANK = OUT / 'compiled/native_CV_B_partial_01'


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def load(p):
    return json.loads(Path(p).read_text(encoding='utf-8-sig'))


def rows(p):
    with gzip.open(p, 'rt', encoding='utf-8') as handle:
        return [json.loads(line) for line in handle if line.strip()]


def main():
    report_path = BANK / 'COMPILATION_REPORT.json'
    report = load(report_path)
    assert load(BANK / 'ROOT_TOKEN_QA.json')['status'] == 'PASS'
    review = load(SOURCE / 'REVIEW.json')
    raw_root = OUT / 'native_records/B_phase2_cv_01/raw_recovery'
    original = {r['call_id']: r['message'] for r in rows(raw_root / 'provider_responses.original.jsonl.gz')}
    length = load(raw_root / 'NONSTOP_0019_ORIGINAL_FIELDS.json')
    original[length['call_id']] = {'role': 'assistant', 'reasoning_content': length['reasoning_content'],
                                  'content': length['content']}
    assert len(original) == 27
    assert sum(len(m.get('reasoning_content', '')) for m in original.values()) == 22806
    for region in review['ranges'] + review['explicit_zero_ranges']:
        text = original[region['call_id']]['reasoning_content'][region['start']:region['end']]
        assert text == region['text'] and hashlib.sha256(text.encode()).hexdigest() == region['text_sha256']
    scopes = {r['source_id']: r for r in rows(OUT / 'clean_inputs/source_scope.metadata.jsonl.gz')}
    records = [r for ref in report['files'] for r in rows(BANK / ref['path'])]
    assert len(records) == 21 and report['counts']['supervised_tokens'] == 6469
    for row in records:
        assert all(scopes[s]['status'] == 'TRAIN' for s in row['source_ids'])
        meta = row['original_record_metadata']
        call = meta['canonical_response_owner'].removeprefix('native_B_phase2_cv_01_')
        assert row['messages'][-1]['reasoning_content'] == original[call].get('reasoning_content', '')
        assert row['messages'][-1].get('content', '') == original[call].get('content', '')
    pins = 0
    for manifest_name in ('DELIVERY_MANIFEST.json', 'RESOURCE_CLOSURE_OVERLAY_MANIFEST.json'):
        manifest = load(SOURCE / manifest_name)
        for ref in manifest['files']:
            path = Path(ref['path'])
            if not path.is_absolute():
                path = SOURCE / ref['path']
            assert path.stat().st_size == ref['bytes'] and sha(path) == ref['sha256']
            pins += 1
    proof = {'schema': 'wrd-root-native-CV-local-process-semantic-admission-v1',
             'status': 'ADMIT_ORIGINAL_NATIVE_CV_PROCESS_R_AND_LOCAL_ACTIONS',
             'design_revision': '5.0.41', 'change_id': 'ALG-20261027-05',
             'record_ids': [r['id'] for r in records],
             'compilation_report_sha256': sha(report_path),
             'root_compiled_QA_sha256': sha(BANK / 'ROOT_TOKEN_QA.json'),
             'review_sha256': sha(SOURCE / 'REVIEW.json'),
             'asof_map_sha256': sha(SOURCE / 'ASOF_PREMISE_MAP.json'),
             'source_and_version_pins_rechecked': pins,
             'root_semantic_review': 'Read all22 selected verbatim R ranges and all explicit exclusions; read all ten approved action arguments, original source/JD and page extraction, exact first-delivered claims error and actual original22-test observation. Planning/hypotheses receive only bounded process credit, not execution or hiring gold.',
             'original_R_tokens': 4988, 'original_native_process_action_A_tokens': 1481,
             'whole_resource_code_writes_and_final_delivery_loss': 0,
             'known_bad_watermark_heuristic_and_hiring_conclusions_loss': 0,
             'length19_exact_prefix_without_fake_EOS': True,
             'call22_is_fixture_wrapper_repair_not_resource_implementation_repair': True,
             'later_CV_revision_and_eight_PDF_results_not_in_original_input': True,
             'one_Maker_source_one_mechanism_not_21_skills': True,
             'same_response_core_full53_views_mutually_exclusive': True,
             'full_WRD_main_training_ready': False, 'training_started': False}
    path = BANK / 'ROOT_SEMANTIC_ADMISSION.json'
    assert not path.exists()
    path.write_text(json.dumps(proof, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'admitted_targets': 21, 'original_R': 4988, 'original_A': 1481, 'pins': pins}))


if __name__ == '__main__':
    main()
