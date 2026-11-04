"""Replace the twelve-owner bank with peer-refined twenty-six original owners."""
from collections import defaultdict
import gzip
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'output/20261027_wrd_main_v10'
BASE = OUT / 'historical_v6_reasoning_review_01'
SOURCE = BASE / 'combined26_peer_refined_01'
BANK = OUT / 'compiled/historical_semantic_R_26_01'


def load(p):
    return json.loads(Path(p).read_text(encoding='utf-8-sig'))


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def rows(p):
    with gzip.open(p, 'rt', encoding='utf-8') as handle:
        return [json.loads(line) for line in handle if line.strip()]


def ranges(review):
    result = defaultdict(set)
    for r in review['ranges']:
        result[r['pair_id']].update(range(r['start'], r['end']))
    return result


def main():
    after = ranges(load(SOURCE / 'REVIEW.json'))
    before = defaultdict(set)
    for name in ('first3_semantic_revision_05', 'voucher_source_review_03',
                 'valuation_source_review_01', 'docx_source_review_01'):
        for owner, selected in ranges(load(BASE / name / 'REVIEW.json')).items():
            assert owner not in before
            before[owner] = selected
    peer_path = BASE / 'peer_review_remaining3_01/REVIEW.json'
    peer = load(peer_path)
    assert peer['status'] == 'FOUR_PRECISE_SUBSPAN_REVISIONS_KEEP_BOUNDED_PLANNING'
    assert peer['actual_positive_ranges_read'] == 73 and peer['actual_asof_facts_checked'] == 194
    removed = defaultdict(set)
    for r in peer['precise_zero_ranges']:
        removed[r['pair_id']].update(range(r['start'], r['end']))
    assert sum(map(len, removed.values())) == 283 and set(after) == set(before)
    assert all(after[k] == before[k] - removed[k] for k in before)
    assert load(SOURCE / 'INDEPENDENT_TOKEN_QA.json')['status'] == 'PASS'
    assert load(BANK / 'ROOT_TOKEN_QA.json')['status'] == 'PASS'
    report = load(BANK / 'COMPILATION_REPORT.json')
    current = [r for f in report['files'] for r in rows(BANK / f['path'])]
    assert len(current) == 26 and report['counts']['supervised_tokens'] == 33153
    old_bank = OUT / 'compiled/historical_semantic_R_05_03'
    old_report = load(old_bank / 'COMPILATION_REPORT.json')
    old = {r['original_record_metadata']['canonical_original_response_owner']: r
           for f in old_report['files'] for r in rows(old_bank / f['path'])}
    current_owners = {}
    scopes = {r['source_id']: r for r in rows(OUT / 'clean_inputs/source_scope.metadata.jsonl.gz')}
    for r in current:
        meta = r['original_record_metadata']
        owner = meta['canonical_original_response_owner']
        assert owner not in current_owners
        current_owners[owner] = r
        assert all(scopes[s]['status'] == 'TRAIN' for s in r['source_ids'])
        assert set(r['supervised_tokens_by_component']) == {'R'}
        if owner in old:
            for key in ('input_ids', 'supervision_spans', 'total_tokens', 'messages', 'tools', 'supervised_tokens'):
                assert r[key] == old[owner][key]
    for ref in load(SOURCE / 'PORTABLE_SELECTION_26.json')['arrays']:
        p = SOURCE / ref['path']
        assert '\\' not in ref['path'] and p.stat().st_size == ref['bytes'] and sha(p) == ref['sha256']
    proof = {'schema': 'wrd-root-historical-R-scoped-semantic-admission-v1',
             'status': 'ADMIT_PARTIAL_HISTORICAL_R_SEMANTIC_STAGE',
             'design_revision': '5.0.41', 'change_id': 'ALG-20261027-05',
             'record_ids': [r['id'] for r in current],
             'compilation_report_sha256': sha(BANK / 'COMPILATION_REPORT.json'),
             'root_compiled_QA_sha256': sha(BANK / 'ROOT_TOKEN_QA.json'),
             'original_review_sha256': sha(SOURCE / 'REVIEW.json'),
             'peer_first3_sha256': sha(BASE / 'peer_review_first3_04/REVIEW.json'),
             'peer_remaining3_sha256': sha(peer_path),
             'all340_actual_asof_pointer_QA_sha256': sha(BASE / 'ALL6_ASOF_POINTER_QA_01.json'),
             'replacement_of_12_owner_bank': 'compiled/historical_semantic_R_05_03',
             'all_previous12_input_and_positive_spans_unchanged': True,
             'extra_original_response_owners': 14, 'extra_original_R_tokens': 16215,
             'four_remaining_peer_exclusions_exactly283_characters_no_new_positives': True,
             'root_review_scope': 'Read every remaining peer disposition and exact four exclusions, review original numerical/finance/DOCX/budget scope and all replacement identities; relies on independent peer full-positive-text reading for other65k characters, not human gold.',
             'original_R_tokens': 33153, 'new_short_reasoning_tokens': 0,
             'historical_condition_not_current_native_equivalence': True,
             'old_ActionProposal_A_D_and_format_loss_zero': True,
             'all_six_source_original_R_preserved_characters': 396231,
             'no_blanket_all_remaining_content_rejected_as_useless': True,
             'same_original_v6_other_review_or_prior12_owners_exclusive': True,
             'full_WRD_main_training_ready': False, 'training_started': False}
    dest = BANK / 'ROOT_SEMANTIC_ADMISSION.json'
    assert not dest.exists()
    dest.write_text(json.dumps(proof, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'replacement_owners': 26, 'net_new': 14, 'original_R': 33153}))


if __name__ == '__main__':
    main()
