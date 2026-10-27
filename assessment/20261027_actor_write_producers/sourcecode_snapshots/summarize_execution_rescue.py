"""Freeze concrete remaining gaps and future-import loss revocations."""
from collections import Counter, defaultdict
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'output/20261027_wrd_main_v10/execution_rescue_01'


def main():
    spec = importlib.util.spec_from_file_location('helper', ROOT / 'research/data_prep/wrd_main_v10/audit_prepare_ancestry.py')
    h = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(h)
    report_path = OUT / 'producer57_extended_static/PRODUCER_AUDIT.json'
    report = h.load(report_path)
    resource_path = ROOT / 'output/20261026_wrd_dataset_v9/outcomes/recomputed_scope_overlay/resource_scope.jsonl.gz'
    resources = defaultdict(list)
    for row in h.rows(resource_path):
        if not row.get('eligible_scope'):
            resources[row['episode_id']].append(row)
    missing = []
    for episode in report['episodes']:
        if episode['classification'] != 'HOLD_MISSING_TASK_PRODUCER_CLOSURE':
            continue
        scopes = []
        seen = set()
        for producer in episode['matched_producers']:
            receipt = producer.get('original_producer_scope_receipt')
            if not receipt:
                continue
            resource_rows = []
            for row in resources[receipt['episode_id']]:
                if row['observed_after_assistant_message_index'] >= receipt['source_message_index']:
                    continue
                key = row['episode_id'], row['node_id']
                if key in seen:
                    continue
                seen.add(key)
                ref = row.get('file_identity') or {}
                resource_rows.append({'node_id': row['node_id'], 'native_path': row['native_path'],
                    'actual_access_after_assistant_message_index': row['observed_after_assistant_message_index'],
                    'CAS_sha256': ref.get('sha256'), 'CAS_object': ref.get('object'),
                    'source_original_path': ref.get('source_path'), 'original_terminal': row.get('original_terminal'),
                    'unknown_reasons': row.get('unknown_reasons'),
                    'original_proven_producer_prefixes': row.get('original_proven_producer_prefixes'),
                    'old_protected_source_ids': row.get('protected_source_ids', []),
                    'old_scope_source_ids': row.get('source_ids', [])})
            scopes.append({'producer': producer['producer_episode_id'],
                'actual_task_emission_line_1based': producer['task_emission_native_line_1based'],
                'producer_scope_receipt': receipt, 'prior_resource_gaps': resource_rows})
        missing.append({'episode_id': episode['episode_id'], 'target_ids': episode['targets'],
            'task_sha256': episode['task_input_sha256'],
            'exact_task_emission_join_count': len(episode['matched_producers']),
            'remaining_unknowns': episode['unknowns'], 'producer_scope_and_resource_gaps': scopes,
            'not_known_clean_and_not_promoted_by_program_quality': True})
    assert len(missing) == 19 and sum(len(r['target_ids']) for r in missing) == 23
    h.save(OUT / 'REMAINING_GAPS.json', {'scope': '23 write targets in 19 original Actor episodes',
        'cases': missing, 'new_training_admitted': 0,
        'old_source_scope_is_preserved_as_evidence_not_blindly_reasserted_as_complete_proof': True,
        'actual_gap_resource_scope_source': h.pin(resource_path)})

    decisions = {e['episode_id']: e['classification'] for e in report['episodes']}
    rows = []
    shard_pins = []
    by_action = defaultdict(Counter)
    for shard in sorted((ROOT / 'output/20261026_wrd_dataset_v9/sft').glob('native_process.*.jsonl.gz')):
        shard_pins.append(h.pin(shard))
        for record in h.rows(shard):
            eid = record.get('episode_id')
            if eid not in decisions:
                continue
            action = 'REVOKE_ON_FUTURE_IMPORT' if decisions[eid] == 'HOLD_CONFIRMED_PROTECTED_TASK_PRODUCER' else 'HOLD_ON_FUTURE_IMPORT_PENDING_PRODUCER_CLOSURE'
            targets = [t for t in record.get('targets', []) if t.get('supervised_tokens', 0) > 0]
            if not targets:
                continue
            row = {'old_record_id': record['id'], 'episode_id': eid, 'old_split': record['split'],
                'old_shard': shard.name, 'old_supervised_tokens': record['supervised_tokens'],
                'old_weighted_token_mass': sum((hi - lo) * weight for lo, hi, component, weight in record['supervision_spans']),
                'target_ids_to_zero_on_future_import': [t['id'] for t in targets],
                'old_input_ids_sha256': record['input_ids_sha256_u32le'],
                'old_spans_sha256': record['supervision_spans_sha256'], 'action': action,
                'whole_actor_input_affected_from_initial_user_prompt': True,
                'frozen_old_data_not_modified': True}
            rows.append(row)
            by_action[action]['sequences'] += 1
            by_action[action]['targets'] += len(targets)
            by_action[action]['supervised_tokens'] += record['supervised_tokens']
    # This is a new disjoint group of 39 Actors, excluded from the earlier 26
    # audit. Do not add counts twice merely because both errata exist.
    previous = h.load(ROOT / 'output/20261027_wrd_main_v10/prepare_ancestry_audit/actor_prepare_case_evidence.json')
    assert not set(decisions) & {e['episode_id'] for e in previous['cases']}
    h.save(OUT / 'V9_AUX_FUTURE_IMPORT_ERRATUM.json', {
        'scope': 'Only old native auxiliary rows in these 39 Actors; no old file or v10 ACTIVE bank is modified.',
        'source': h.pin(report_path), 'counts': {k: dict(v) for k, v in by_action.items()},
        'records': rows, 'old_shards': shard_pins, 'new_main_sequences': 0,
        'disjoint_from_previous_26_Actor_audit': True, 'v10_active_main_banks_affected': 0,
        'all_original_context_and_historical_cost_preserved': True})
    packet_sha = 'e40342a6574c0d69c4ade268797eb4a606d9792852c35a98fd2b6a8d9d87cfb4'
    packet_path = ROOT / 'output/20261025_wrd_training_dataset/bundle/archive/objects/e4' / packet_sha
    assert h.pin(packet_path)['sha256'] == packet_sha
    packet = h.load(packet_path)
    assert len(packet) == 6 and all('user_requirements' in item for item in packet)
    source_scope_path = ROOT / 'output/20261027_wrd_main_v10/clean_inputs/source_scope.metadata.jsonl.gz'
    source_scopes = {r['source_id']: r['status'] for r in h.rows(source_scope_path)}
    current_holds = sorted(item['source_id'] for item in packet if source_scopes.get(item['source_id']) == 'HOLD_PROTECTED_OR_SHARED_PRIVATE_INPUT')
    assert current_holds == ['conv_1caa4df498cc', 'conv_f9a02361c038']
    h.save(OUT / 'SOURCE_PACKET_STRUCTURAL_NOTE.json', {
        'scope': 'Why a source-eligible Actor output is not automatically producer-closed',
        'fixed_protocol_example': {
            'path': '/workspace/inputs/development_task.md',
            'observed_source_sha256': '3bf9a74cef5827aae357559da0728760370a17e13502360a5b450e497b4ea530',
            'content_type': 'generic_development_task_collection_protocol',
            'no_enterprise_task_or_answer_in_that_protocol': True,
            'whole_other_resource_bank_is_not_certified_by_protocol_identity': True},
        'legacy_jd_devprep': {
            'episode_id': 'ep_4131187edd6c67637d32',
            'development_sources_packet_sha256': 'e40342a6574c0d69c4ade268797eb4a606d9792852c35a98fd2b6a8d9d87cfb4',
            'packet_source_records': 6, 'contains_user_requirements_field': True,
            'two_source_records_have_current_HOLD_PROTECTED_OR_SHARED_PRIVATE_INPUT': ['conv_f9a02361c038', 'conv_1caa4df498cc'],
            'current_task_selected_sources_alone_do_not_close_whole_visible_packet': True,
            'that_structural_observation_alone_is_not_labeled_as_direct_original226_body_proof': True,
            'quality_admitted': False},
        'current_source_scope_pin': h.pin(source_scope_path),
        'no_sensitive_body_or_candidate_personal_details_in_this_note': True})
    print({k: dict(v) for k, v in by_action.items()})


if __name__ == '__main__':
    main()
