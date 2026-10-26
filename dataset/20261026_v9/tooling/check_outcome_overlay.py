"""Independent read-only comparison of the final v9 source-scope overlay."""
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'output/20261026_wrd_dataset_v9/outcomes'
FINAL = OUT / 'recomputed_scope_overlay'


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1048576), b''):
            h.update(block)
    return h.hexdigest()


def rows(path):
    with gzip.open(path, 'rt', encoding='utf-8-sig') as f:
        for line in f:
            if line.strip():
                yield json.loads(line)


def main():
    receipt = json.loads((FINAL / 'OVERLAY_RECEIPT.json').read_text(encoding='utf-8'))
    for name, expected in receipt['base_files_preserved'].items():
        assert digest(OUT / name) == expected, name
    counters = Counter()
    transitions = Counter()
    file_contributions, review_writes = Counter(), Counter()
    clean_base, clean_final, changed, semantic_changed = set(), set(), set(), set()
    base = rows(OUT / 'target_outcome_labels.jsonl.gz')
    new = rows(FINAL / 'target_outcome_labels.jsonl.gz')
    sentinel = object()
    from itertools import zip_longest
    for a, b in zip_longest(base, new, fillvalue=sentinel):
        assert a is not sentinel and b is not sentinel
        assert a['id'] == b['id'] and a['episode_id'] == b['episode_id']
        assert a['source_message_index'] == b['source_message_index'] and a['source_message_sha256'] == b['source_message_sha256']
        counters['targets_compared'] += 1
        transitions[a['source_admission'] + '->' + b['source_admission']] += 1
        if a['source_admission'] == 'ADMIT':
            clean_base.add(a['id'])
            assert b['source_admission'] == 'ADMIT'
            assert a['source_ids_visible_prefix'] == b['source_ids_visible_prefix']
            assert not b['protected_sources_visible_prefix'] and not b['unknown_reasons']
        if b['source_admission'] == 'ADMIT':
            clean_final.add(b['id'])
            assert not b['protected_sources_visible_prefix'] and not b['unknown_reasons']
        if a != b:
            changed.add(a['id'])
            if {key for key in a if a[key] != b[key]} - {'evidence_refs', 'scope_proof_id'}:
                semantic_changed.add(a['id'])
        if b.get('positive_outcome_loss_candidate'):
            file_contributions[b['source_admission']] += 1
        if b.get('quality_positive_review_candidate'):
            review_writes[b['source_admission']] += 1
        assert b.get('all_steps_in_retained_route_are_positive') is False
        assert b.get('training_admitted') is False
        if b['source_admission'] != 'ADMIT':
            assert b.get('positive_skill_action_eligible') is False
            assert b.get('quality_positive_review_eligible_scope') is False
    assert clean_base == clean_final and len(clean_final) == 3149
    assert transitions['HOLD_MISSING_EVIDENCE->HOLD_PROTECTED'] == 439
    assert transitions['HOLD_MISSING_EVIDENCE->ADMIT'] == 0
    assert transitions['HOLD_PROTECTED->ADMIT'] == 0
    assert file_contributions == {'HOLD_PROTECTED': 144, 'HOLD_MISSING_EVIDENCE': 1}
    assert review_writes == {'HOLD_PROTECTED': 85, 'HOLD_MISSING_EVIDENCE': 2}
    updates = list(rows(FINAL / 'explicit_resource_updates.jsonl.gz'))
    assert len(updates) == 48 and len({x['node_id'] for x in updates}) == 48
    kinds = Counter(x['kind'] for x in updates)
    framework = [x for x in updates if x['kind'] == 'CLOSED_FIXED_FRAMEWORK_BODY_ONLY']
    for item in framework:
        assert not item['source_ids'] and not item['parents']
        assert item['evidence']
        for evidence in item['evidence']:
            if evidence.get('source_sha256') and evidence.get('path'):
                assert digest(evidence['path']) == evidence['source_sha256']
                counters['fixed_framework_original_source_files_rehashed'] += 1
    updates_by_id = {x['id']: x for x in rows(FINAL / 'target_source_scope_updates.jsonl.gz')}
    assert len(updates_by_id) == receipt['target_scope_update_count']
    assert semantic_changed <= set(updates_by_id) <= changed
    assert receipt['explicit_resource_update_count'] == len(updates)
    result = {'schema_version': 'wrd-v9-independent-final-outcome-overlay-review-1.0', 'status': 'PASS',
        'counts': dict(counters), 'all_target_scope_transitions': dict(transitions),
        'clean_target_ids_unchanged': len(clean_final), 'explicit_resource_update_kinds': dict(kinds),
        'additional_proof_identifier_only_changes_not_in_semantic_update_list': len(changed - set(updates_by_id)),
        'trial_supported_file_contribution_source_statuses': dict(file_contributions),
        'evidence_review_write_source_statuses': dict(review_writes),
        'unknown_or_protected_targets_promoted_to_ADMIT': 0,
        'no_retained_route_blanket_positive_loss': True,
        'compiled_clean_input_prefix_set_remains_valid_after_overlay': True,
        'known_framework_identity_does_not_certify_business_resource_ancestry': True,
        'business_semantic_gold_or_full_autonomous_success_not_certified': True,
        'training_started': False,
        'final_target_labels_sha256': digest(FINAL / 'target_outcome_labels.jsonl.gz'),
        'explicit_resource_updates_sha256': digest(FINAL / 'explicit_resource_updates.jsonl.gz'),
        'overlay_receipt_sha256': digest(FINAL / 'OVERLAY_RECEIPT.json'),
        'verifier_script_sha256': digest(Path(__file__))}
    (OUT / 'OUTCOME_FINAL_REVIEW.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()
