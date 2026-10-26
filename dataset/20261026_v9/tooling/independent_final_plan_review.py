"""Independent read-only CPU review of final v9 plan, pins, and SFT payloads.

Writes only output/20261026_wrd_dataset_v9/PLAN_REVIEW.json. No models,
tokenizer calls, agent loops, business execution, training, or network calls.
The separate bound per-sequence QA provides the dual-tokenizer re-encoding.
"""
from array import array
from collections import Counter, defaultdict
from datetime import datetime, timezone
import gzip
import hashlib
import json
import math
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'output/20261026_wrd_dataset_v9'


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for block in iter(lambda: handle.read(1048576), b''):
            h.update(block)
    return h.hexdigest()


def pin(path):
    p = Path(path)
    return {'path': str(p.resolve()), 'bytes': p.stat().st_size, 'sha256': digest(p)}


def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def rows(path):
    op = gzip.open if str(path).endswith('.gz') else open
    with op(path, 'rt', encoding='utf-8-sig') as handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)


def resolved_set(items):
    result = set()
    for item in items:
        p = Path(item['path'])
        if not p.is_absolute():
            p = OUT / p
        result.add((str(p.resolve()), item['bytes'], item['sha256']))
    assert len(result) == len(items), 'duplicate artifact paths'
    return result


def verify_pins(items):
    result = []
    for item in items:
        p = Path(item['path'])
        if not p.is_absolute():
            p = OUT / p
        actual = pin(p)
        assert (actual['bytes'], actual['sha256']) == (item['bytes'], item['sha256']), str(p)
        result.append(actual)
    return result


def equal_numbers(a, b):
    assert set(a) == set(b), (set(a) - set(b), set(b) - set(a))
    for key in a:
        assert math.isclose(a[key], b[key], abs_tol=1e-6), (key, a[key], b[key])


def main():
    artifact_names = ['TRAINING_PLAN.json', 'TRAINING_PLAN.md', 'TRAINING_MANIFEST.json',
                      'FINAL_DATA_STATISTICS.json', 'COMPILATION_REPORT.json', 'COMPILED_QA.json',
                      'SOURCE_GROUP_SPLIT.json', 'TARGET_QUALITY_ERRATA.json',
                      'FAILED_READ_ERRATUM_INDEPENDENT_QA.json', 'CLEAN_RECOLLECTION_PLAN.json']
    initial_pins = [pin(OUT / name) for name in artifact_names]
    plan, manifest, stats, report, qa, split, errata, errata_qa, recollection = [
        load(OUT / name) for name in artifact_names if name != 'TRAINING_PLAN.md']
    checks = []

    def checked(name, evidence):
        checks.append({'check': name, 'status': 'PASS', 'evidence': evidence})

    assert qa['status'] == 'PASS' and not qa['failures'] and not any(qa['cross_split_errors'].values())
    assert resolved_set(report['split']['files']) == resolved_set(qa['verified_files'])
    assert resolved_set(report['split']['files']) == resolved_set(manifest['actual_files_with_messages_input_ids_masks'])
    assert resolved_set(report['split']['files']) == resolved_set(stats['files'])
    assert {str(p.resolve()) for p in (OUT / 'sft').glob('*.jsonl.gz')} == {
        x[0] for x in resolved_set(report['split']['files'])}
    verified_files = verify_pins(report['split']['files'])
    assert qa['verifier_script_sha256'] == digest(ROOT / 'research/data_prep/wrd_dataset_v9/check_compiled.py')
    checked('final_SFT_allowlist_and_QA_exact_path_bytes_SHA', {'files': len(verified_files), 'QA_status': 'PASS'})

    input_pins = verify_pins(report['immutable_input_pins'])
    coord_pins = [p for p in report['immutable_input_pins'] if Path(p['path']).parent == OUT / 'coordination']
    assert resolved_set(coord_pins) == resolved_set(qa['actual_coordination_input_pins_verified'])
    for key in ['official_template_sha256', 'causal_template_sha256', 'asset_sha256']:
        assert report['tokenizer_and_template_proof'][key] == qa['tokenizer_and_template_proof'][key]
    asset_pins = []
    for role, assets in qa['tokenizer_and_template_proof']['asset_sha256'].items():
        for name, expected in assets.items():
            actual = pin(ROOT / 'output/20261025_wrd_training_preflight/tokenizer_assets' / role / name)
            assert actual['sha256'] == expected
            asset_pins.append(actual)
    assert qa['all_sequences_reencoded_with_both_actual_frozen_tokenizers'] is True
    assert qa['actual_ignore_index_labels_reconstructed'] is True
    assert qa['tokenizer_and_template_proof']['independent_second_tokenizer_calls'] == 1968
    checked('source_input_pins_and_actual_dual_tokenizer_assets',
            {'input_pins': len(input_pins), 'coordination_input_pins': len(coord_pins),
             'actual_asset_files_rehashed': len(asset_pins), 'bound_dual_tokenizer_reencoded_sequences': 1968})

    quality = {r['id']: r['observed_tool_failure'] for r in rows(Path(errata['quality_source']['path']))}
    protected = set()
    for p in (ROOT / 'benchmark').glob('*/contracts/evaluation.jsonl'):
        group = {r.get('session_id') for r in rows(p)} - {None}
        if len(group) == 226:
            protected.update(group)
    assert len(protected) >= 226
    holdout = load(ROOT / 'output/20261026_ablation_v2/holdout_registry.json')
    new_holdout_sources = set(re.findall(r'conv_[0-9a-f]{12}', json.dumps(holdout)))
    protected.update(new_holdout_sources)
    by_split = Counter()
    by_bank = defaultdict(Counter)
    components = Counter()
    origins = Counter()
    native_target_ids = set()
    identities = set()
    source_splits, route_splits, component_splits, lineage_splits = [defaultdict(set) for _ in range(4)]
    actual_group_rows = defaultdict(set)
    counts_per_file = {}
    all_rows = 0
    for item in report['split']['files']:
        count = 0
        for row in rows(OUT / item['path']):
            count += 1
            all_rows += 1
            assert row['id'] not in identities
            identities.add(row['id'])
            bank, subset = row['bank'], row['split']
            scope = subset + '_'
            ids = row['input_ids']
            assert len(ids) == row['total_tokens'] <= 32768
            assert (row['total_tokens'] <= 16384) == ('.16k.' in item['path'])
            a = array('I', ids)
            if sys.byteorder != 'little':
                a.byteswap()
            assert hashlib.sha256(a.tobytes()).hexdigest() == row['input_ids_sha256_u32le']
            spans = row['supervision_spans']
            assert hashlib.sha256(json.dumps(spans, ensure_ascii=False, separators=(',', ':')).encode()).hexdigest() == row['supervision_spans_sha256']
            last, owned, supervised, weighted = 0, [], 0, 0.0
            for lo, hi, component, weight in spans:
                assert 0 <= last <= lo < hi <= len(ids) and 0 < weight <= 0.1 + 1e-9
                assert component != 'R'
                last = hi
                supervised += hi - lo
                weighted += (hi - lo) * weight
                components[component] += hi - lo
            assert supervised == row['supervised_tokens'] > 0
            for target in row['targets']:
                owned.extend(target['owned_supervision_spans'])
                assert target['supervised_tokens'] == sum(hi - lo for lo, hi, _, _ in target['owned_supervision_spans'])
                assert row['messages'][target['message_index']]['role'] == 'assistant'
                if bank == 'native_process':
                    assert target['id'] not in native_target_ids
                    native_target_ids.add(target['id'])
                    assert quality[target['id']] is False
                    assert target['supervision_tier'] == 'read_only_protocol_auxiliary'
                    message = row['messages'][target['message_index']]
                    assert not message.get('content') and not message.get('reasoning_content')
                    assert all(c['function']['name'] in {'read', 'ls'} for c in message['tool_calls'])
            assert owned == spans
            assert row['is_full_autonomous_execution_demonstration'] is False
            assert row['training_started'] is False
            for key, amount in [('sequences', 1), ('targets', len(row['targets'])), ('input_tokens', len(ids)), ('supervised_tokens', supervised)]:
                by_split[scope + key] += amount
                by_bank[bank][scope + key] += amount
            by_split[scope + 'weighted_loss_token_mass'] += weighted
            by_bank[bank]['le16k_sequences' if len(ids) <= 16384 else 'gt16k_le32k_sequences'] += 1
            for source in row.get('source_ids', []):
                assert source not in protected
                source_splits[source].add(subset)
            if row.get('route_id'):
                route_splits[row['route_id']].add(subset)
            component_splits[row['source_component_id']].add(subset)
            actual_group_rows[row['source_component_id']].add(row['id'])
            if bank == 'coordination':
                assert row['is_original_teacher_CoT'] is False
                origin = row['annotation_provenance']
                origins[origin + '_sequences'] += 1
                origins[origin + '_targets'] += len(row['targets'])
                original = row['coordination_original_record']
                if original.get('source_group_id'):
                    lineage_splits[original['source_group_id']].add(subset)
                if 'synthetic' in origin.lower():
                    assert subset == 'train' and not row['source_ids']
        counts_per_file[item['path']] = count
    equal_numbers(by_split, stats['all_splits'])
    for bank in by_bank:
        equal_numbers(by_bank[bank], stats['by_bank'][bank])
        actual_profile = {k: v for k, v in manifest['profiles'][bank].items() if k != 'meaning'}
        equal_numbers(by_bank[bank], actual_profile)
        assert qa['by_bank'][bank]['rows'] == sum(by_bank[bank][s + '_sequences'] for s in ['train', 'dev', 'test'])
        assert qa['by_bank'][bank]['supervised_tokens'] == sum(by_bank[bank][s + '_supervised_tokens'] for s in ['train', 'dev', 'test'])
    assert dict(components) == stats['supervised_component_tokens']
    assert dict(origins) == stats['annotation_origins']
    for item in manifest['actual_files_with_messages_input_ids_masks']:
        assert counts_per_file[item['path']] == item['sequences']
    assert all_rows == qa['counts']['verified_sequences'] == 1968
    assert len(native_target_ids) == qa['counts']['native_owned_targets_checked'] == 1368
    assert len(native_target_ids) == qa['counts']['native_positive_protocol_targets_without_observed_tool_failure']
    checked('all_actual_SFT_rows_arrays_spans_weights_and_statistics_recounted',
            {'rows': all_rows, 'all_splits': dict(by_split), 'by_bank': {k: dict(v) for k, v in by_bank.items()},
             'component_tokens': dict(components), 'annotation_origins': dict(origins)})

    for grouping in [source_splits, route_splits, component_splits, lineage_splits]:
        assert all(len(v) == 1 for v in grouping.values())
    assert {g['component_id']: set(g['row_ids']) for g in split['groups']} == dict(actual_group_rows)
    for group in split['groups']:
        assert group['rows'] == len(group['row_ids']) and component_splits[group['component_id']] == {group['split']}
    assert split['dev_test_are_static_record_holdouts_not_closed_loop_success_measurements'] is True
    checked('source_route_lineage_split_and_protected_source_separation',
            {'source_ids': len(source_splits), 'components': len(component_splits),
             'protected_source_intersections': 0, 'new_holdout_registry_source_ids_checked': len(new_holdout_sources),
             'static_holdout_is_not_closed_loop_evaluation': True})

    removed = errata['removed_positive_owner_records']
    removed_ids = {r['target']['id'] for r in removed}
    assert len(removed) == len(removed_ids) == 10 and not removed_ids.intersection(native_target_ids)
    assert all(quality[r['target']['id']] is True for r in removed)
    removed_components = Counter()
    for item in removed:
        for lo, hi, component, _ in item['target']['owned_supervision_spans']:
            removed_components[component] += hi - lo
    assert dict(removed_components) == {'F': 60, 'A': 293}
    assert errata_qa['status'] == 'PASS' and errata_qa['erratum_sha256'] == digest(OUT / 'TARGET_QUALITY_ERRATA.json')
    assert errata_qa['counts']['removed_positive_tokens'] == sum(removed_components.values()) == 353
    assert errata_qa['all_native_input_ids_messages_rendered_source_fields_unchanged'] is True
    assert errata_qa['all_1843_full_trace_messages_and_tools_unchanged'] is True
    snapshot = OUT / 'publication_history/failed_read_fix'
    before_native = rows(snapshot / 'compiled/native.pre_split.jsonl.gz')
    after_native = rows(OUT / 'compiled/native.pre_split.jsonl.gz')
    volatile = {'targets', 'supervision_spans', 'supervised_tokens', 'supervised_tokens_by_component', 'supervision_spans_sha256', 'postcompile_quality_erratum'}
    compared = 0
    sentinel = object()
    from itertools import zip_longest
    for before, after in zip_longest(before_native, after_native, fillvalue=sentinel):
        assert before is not sentinel and after is not sentinel
        assert {k: v for k, v in before.items() if k not in volatile} == {k: v for k, v in after.items() if k not in volatile}
        assert [t for t in before['targets'] if t['id'] not in removed_ids] == after['targets']
        assert [s for t in before['targets'] if t['id'] not in removed_ids for s in t['owned_supervision_spans']] == after['supervision_spans']
        compared += 1
    assert compared == 960
    unchanged_coord_items = errata['unchanged_coordination_inputs_pre_split_and_sft']
    if isinstance(unchanged_coord_items, dict):
        unchanged_coord_items = list(unchanged_coord_items.values())
    unchanged_coord = verify_pins(unchanged_coord_items)
    checked('failed_read_erratum_exact_loss_removal_preserves_native_inputs_and_coordination',
            {'removed_owners': 10, 'removed_supervised_tokens': 353, 'components': dict(removed_components),
             'compiled_native_rows_independently_compared': compared, 'coordination_pins_rehashed': len(unchanged_coord),
             'full_trace_preservation_bound_to_independent_QA': 1843,
             'errata_pending_status_is_historical_application_time': True})

    assert plan['status'] == 'AUXILIARY_DATA_COMPILED_FULL_WRD_MAIN_SFT_BLOCKED'
    assert plan['execution_authorized'] is False and plan['is_launch_config'] is False and plan['training_started'] is False
    assert manifest['full_goal_main_training_ready'] is False and manifest['training_execution_authorized'] is False
    assert manifest['profiles']['wrd_outcome_main'] == {'admitted_targets': 0, 'ready': False}
    for key in ['outcome_backed_skill_supervised_targets', 'evidence_review_semantic_supervised_targets',
                'original_reasoning_supervised_tokens', 'full_autonomous_real_native_demonstrations']:
        assert stats[key] == 0
    assert stats['real_poststage_coordination']['source_closed_admitted'] == 0
    assert stats['real_poststage_coordination']['processed_state_decisions'] == 3771
    assert plan['models'] == load(ROOT / 'output/20261025_wrd_training_dataset/git_release/plans/20261025_14b_spark/TRAINING_CONFIG.json')['models']
    historical = plan['historical_optional_reference_not_automatically_joined']
    assert (historical['historical_main_responses'], historical['historical_readable_R_responses'], historical['historical_R_tokens']) == (106, 30, 121511)
    assert historical['not_counted_as_current_native_outcome_main'] is True
    assert plan['inference_contract']['future_native_deployment_integration_completed'] is False
    assert plan['no_throughput_or_effect_claim_without_Spark_measurement'] is True
    assert plan['shared_sft_candidate']['truncation_allowed'] is False
    assert plan['shared_sft_candidate']['maximum_passes_before_new_decision'] == 1
    assert recollection['execution_authorized'] is False and recollection['proposed_maximum_new_stage_sessions'] == 120
    assert sum(recollection['proposed_stage_upper_bounds'].values()) == 120
    assert len(recollection['train_only_seeds']) == 12
    for seed in recollection['train_only_seeds']:
        assert source_splits[seed['seed_source_id']] == {'train'}
        for source in seed['remaining_training_sources_in_category']:
            assert source_splits[source] == {'train'}
    md = (OUT / 'TRAINING_PLAN.md').read_text(encoding='utf-8')
    for phrase in ['2090', '403788', '1368', '44651', 'TARGET_QUALITY_ERRATA.json', '14B', '8B', '121511', '不保证', '静态dev/test', '原226', '新H']:
        assert phrase in md, phrase
    checked('plan_preserves_full_WRD_goal_and_blocks_training_without_empirical_main_supervision',
            {'current_complete_main_targets': 0, 'original_R_positive_tokens': 0,
             'historical_v6_preserved_not_merged': {'main_responses': 106, 'R_responses': 30, 'R_tokens': 121511},
             'hypothetical_full_controller_traces': 12, 'hypothetical_decisions': 82,
             'models': plan['models'], 'native_integration_complete': False,
             'recollection_plan_only_maximum_sessions': 120, 'no_effect_or_cost_guarantee': True})

    final_pins = [pin(OUT / name) for name in artifact_names]
    assert initial_pins == final_pins, 'artifacts changed during review'
    receipt = {'schema_version': 'wrd-v9-independent-final-plan-review-2.0',
               'reviewed_at_utc': datetime.now(timezone.utc).isoformat(),
               'status': 'PASS_WITH_FULL_GOAL_MAIN_TRAINING_BLOCKED',
               'review_is_training_authorization': False, 'training_started': False, 'weights_loaded': False,
               'new_teacher_actor_business_calls': 0, 'checks': checks,
               'reviewed_final_artifact_pins': final_pins, 'verified_SFT_files': verified_files,
               'verified_immutable_source_inputs': input_pins, 'verified_actual_tokenizer_assets': asset_pins,
               'reviewer_script': pin(Path(__file__)),
               'static_guard_review': {'current_guard_matches_final_receipt': True,
                   'nonblocking_limits': ['build_plan compares tokenizer proofs; this review additionally hashes all ten actual assets',
                                          'build_plan writes some outputs before late assertions; final successful output set is independently pinned here']},
               'scope_limits': ['technical arrays/statistics/pins and plan consistency; not semantic gold or empirical effectiveness',
                                'dual-tokenizer re-encoding is the separate pinned COMPILED_QA result; this script independently rechecks arrays/spans/pins',
                                'source static dev/test do not substitute for native student closed-loop evaluation',
                                'full native integration, Spark kernels/throughput, model quality and cost reduction are unverified',
                                'authenticated delivery archive and remote publication are outside this plan review'],
               'supersedes_old_PLAN_REVIEW': 'prior receipt preserved in publication_history; current receipt binds the 10-owner/353-token erratum'}
    (OUT / 'PLAN_REVIEW.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'status': receipt['status'], 'checks': len(checks), 'rows': all_rows,
                      'plan_review': pin(OUT / 'PLAN_REVIEW.json')}, ensure_ascii=False))


if __name__ == '__main__':
    main()
