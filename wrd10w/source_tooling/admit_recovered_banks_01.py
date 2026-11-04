"""Record root's scoped admission after original-text, peer and resource QA.

No old ADMIT flag is inherited as semantic approval. No training or model run.
"""
from collections import defaultdict
import gzip
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'output/20261027_wrd_main_v10'
LEGACY = OUT / 'historical_v6_reasoning_review_01'
FINAL = LEGACY / 'first3_semantic_revision_05'
HELPER = OUT / 'historical_v6_native_repair_01'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def rows(path):
    with gzip.open(path, 'rt', encoding='utf-8-sig') as handle:
        return [json.loads(line) for line in handle if line.strip()]


def save_new(path, value):
    assert not path.exists(), 'preserve prior admission receipts'
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def char_sets(review):
    result = defaultdict(set)
    for item in review['ranges']:
        result[item['pair_id']].update(range(item['start'], item['end']))
    return result


def main():
    scope_path = OUT / 'clean_inputs/source_scope.metadata.jsonl.gz'
    scopes = {r['source_id']: r for r in rows(scope_path)}
    before = load(LEGACY / 'first3_semantic_revision_04/REVIEW.json')
    after = load(FINAL / 'REVIEW.json')
    changes = load(FINAL / 'SEMANTIC_CHANGE_RECEIPT.json')
    peer_path = LEGACY / 'peer_review_first3_04/REVIEW.json'
    peer = load(peer_path)
    assert peer['status'] == 'REVISE_EIGHT_SMALL_SPANS_KEEP_BOUNDED_EXPLORATION'
    assert peer['literal_positive_spans_fully_read'] == 42
    assert peer['author_review_sha256'] == changes['parent_review_sha256'] == sha(LEGACY / 'first3_semantic_revision_04/REVIEW.json')
    assert changes['review_sha256'] == sha(FINAL / 'REVIEW.json')
    old_sets, new_sets = char_sets(before), char_sets(after)
    removed = defaultdict(set)
    original_pairs = {r['id']: r for r in rows(Path(after['source_file']))}
    for item in changes['exact_exclusions']:
        text = original_pairs[item['pair_id']]['original_response']['choices'][0]['message']['reasoning_content']
        segment = text[item['start']:item['end']]
        assert segment == item['text'] and hashlib.sha256(segment.encode()).hexdigest() == item['text_sha256']
        removed[item['pair_id']].update(range(item['start'], item['end']))
    assert sum(map(len, removed.values())) == 164
    assert set(old_sets) == set(new_sets)
    assert all(new_sets[key] == old_sets[key] - removed[key] for key in old_sets)
    assert load(FINAL / 'INDEPENDENT_TOKEN_QA.json')['status'] == 'PASS'
    normalized = OUT / 'compiled/historical_semantic_R_05_03'
    assert load(normalized / 'ROOT_TOKEN_QA.json')['status'] == 'PASS'
    report = load(normalized / 'COMPILATION_REPORT.json')
    assert report['counts']['sequences'] == 12 and report['counts']['supervised_tokens'] == 16938
    records = [r for ref in report['files'] for r in rows(normalized / ref['path'])]
    assert len(records) == 12
    for r in records:
        assert r['split'] == 'train' and set(r['supervised_tokens_by_component']) == {'R'}
        assert all(scopes[s]['status'] == 'TRAIN' for s in r['source_ids'])
        assert r['original_record_metadata']['root_main_admission'] is False
    legacy_proof = {
        'schema': 'wrd-root-historical-R-scoped-semantic-admission-v1',
        'status': 'ADMIT_PARTIAL_HISTORICAL_R_SEMANTIC_STAGE',
        'design_revision': '5.0.41', 'change_id': 'ALG-20261027-05',
        'record_ids': [r['id'] for r in records],
        'compilation_report_sha256': sha(normalized / 'COMPILATION_REPORT.json'),
        'root_compiled_QA_sha256': sha(normalized / 'ROOT_TOKEN_QA.json'),
        'original_review_sha256': sha(FINAL / 'REVIEW.json'),
        'full_selected_text_second_AI_review_sha256': sha(peer_path),
        'exact_eight_exclusions_applied': True,
        'current_source_scope_sha256': sha(scope_path),
        'root_review_scope': 'Read all peer dispositions and exact eight exclusions; manually checked original budget/planning spans and new metadata/token mask; relies on full-selected-text second AI review for other ranges, not human gold.',
        'original_R_tokens': 16938, 'new_short_reasoning_tokens': 0,
        'old_ActionProposal_A_D_and_format_loss_zero': True,
        'historical_condition_not_current_native_equivalence': True,
        'valid_plans_and_hypotheses_are_not_claimed_executed_or_whole_quality_proven': True,
        'same_original_v6_and_other_review_owners_exclusive': True,
        'full_WRD_main_training_ready': False, 'training_started': False}

    manifest = load(HELPER / 'DELIVERY_MANIFEST.json')
    for ref in manifest['files']:
        p = Path(ref['path'])
        assert p.stat().st_size == ref['bytes'] and sha(p) == ref['sha256']
    portable = load(HELPER / 'PORTABLE_SELECTION.json')
    for profile in ('core7', 'full53_conditional64k'):
        selected = portable[profile]
        assert len(selected['arrays']) == 9
        for ref in selected['arrays']:
            assert '\\' not in ref['path']
            p = HELPER / ref['path']
            assert p.stat().st_size == ref['bytes'] and sha(p) == ref['sha256']
    assert load(HELPER / 'RESOURCE_QA.json')['status'] == 'PASS'
    assert load(HELPER / 'ROOT_TOKEN_QA.json')['status'] == 'PASS'
    assert load(HELPER / 'PYTHON_PATH_PROOF.json')['status'].startswith('PASS')
    bank = OUT / 'compiled/historical_v6_native_repair_01'
    report = load(bank / 'COMPILATION_REPORT.json')
    records = [r for ref in report['files'] for r in rows(bank / ref['path'])]
    assert len(records) == 3 and report['counts']['supervised_tokens'] == 1098
    for r in records:
        assert all(scopes[s]['status'] == 'TRAIN' for s in r['source_ids'])
        assert r['original_record_metadata']['actual_native_tool_dispatch'] is False
        assert r['original_record_metadata']['annotation_provenance'] == 'NEW_AUTHORED_NATIVE_ACTION_PROJECTION_VERIFIED_OFFLINE'
    helper_proof = {
        'schema': 'wrd-root-historical-new-native-action-projection-admission-v1',
        'status': 'ADMIT_NEW_AUTHORED_NATIVE_RESOURCE_REPAIR_PROJECTION',
        'design_revision': '5.0.41', 'change_id': 'ALG-20261027-05',
        'record_ids': [r['id'] for r in records],
        'compilation_report_sha256': sha(bank / 'COMPILATION_REPORT.json'),
        'root_compiled_QA_sha256': sha(HELPER / 'ROOT_TOKEN_QA.json'),
        'resource_QA_sha256': sha(HELPER / 'RESOURCE_QA.json'),
        'portable_selection_sha256': sha(HELPER / 'PORTABLE_SELECTION.json'),
        'python_environment_proof_sha256': sha(HELPER / 'PYTHON_PATH_PROOF.json'),
        'all_base_delivery_pins_rechecked': len(manifest['files']),
        'root_review_scope': 'Read all three target rationales and complete action arguments, actual old/new replacements, user state boundaries and independent bad/fixed/mutation results; full promised files and bytes separately rechecked.',
        'new_authored_R_tokens': 155, 'new_authored_projected_action_A_tokens': 943,
        'actual_native_Agent_tool_dispatch_claimed': False,
        'partial_old_program_report_evidence_credit_not_whole_business_Q_or_retention': True,
        'same_original_action_and_other_view_owners_exclusive': True,
        'core7_default_full53_conditional_not_duplicated': True,
        'full_WRD_main_training_ready': False, 'training_started': False}
    # Check every input before publishing either admission receipt.
    assert not (normalized / 'ROOT_SEMANTIC_ADMISSION.json').exists()
    assert not (HELPER / 'ROOT_SEMANTIC_ADMISSION.json').exists()
    save_new(normalized / 'ROOT_SEMANTIC_ADMISSION.json', legacy_proof)
    save_new(HELPER / 'ROOT_SEMANTIC_ADMISSION.json', helper_proof)
    print(json.dumps({'semantically_admitted_banks': 2, 'new_targets': 15,
                      'historical_original_R_tokens': 16938, 'new_authored_R': 155,
                      'new_authored_projected_A': 943, 'training_started': False}))


if __name__ == '__main__':
    main()
