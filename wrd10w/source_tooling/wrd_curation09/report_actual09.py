"""Independent metadata/span recount of staged09; no activation or training.

Writes only the public aggregate report JSON. No source excerpts are exported.
"""
from array import array
from collections import Counter, defaultdict
from decimal import Decimal
import gzip
import hashlib
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
DATA = ROOT / 'output/20261027_wrd_main_v10'
OUT = ROOT / 'output/20261031_wrd_curation09'
MANIFEST = DATA / 'manifest_staging09/TRAINING_MANIFEST09.json'
EXPECTED = '01380a42195dd888aded4140db7dc7013364f6bc66594502487387259d174f42'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def pin(path):
    path = path.resolve()
    return {'path': path.relative_to(ROOT).as_posix(), 'bytes': path.stat().st_size,
            'sha256': sha(path.read_bytes())}


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def canonical(value):
    return json.dumps(value, ensure_ascii=False, separators=(',', ':')).encode()


def load_manifest(path):
    manifest = read(path)
    records, files = [], []
    for item in manifest['actual_train_files']:
        file = DATA / item['path']
        actual = pin(file)
        assert actual['bytes'] == item['bytes'] and actual['sha256'] == item['sha256']
        files.append(actual)
        with gzip.open(file, 'rb') as stream:
            for line in stream:
                if line.strip():
                    records.append(json.loads(line.decode('utf-8-sig')))
    assert len({row['id'] for row in records}) == len(records)
    return manifest, records, files


NATIVE_R_BANKS = {'native_wrd_main', 'native_C_review_partial_02',
                  'native_CV_B_training_01', 'native_HTML_B_training_01'}
NATIVE_LOCAL_A_BANKS = {'native_CV_B_training_01', 'native_HTML_B_training_01'}


def origin_key(row, component):
    bank, meta = row['bank'], row['original_record_metadata']
    if bank == 'source_contract_main':
        return 'new_source_contract_annotation_tokens'
    if component == 'R':
        if bank in NATIVE_R_BANKS:
            return 'original_native_R_tokens'
        if bank == 'historical_semantic_R_main':
            return 'historical_original_R_tokens'
        if bank == 'historical_test_oracle_repair_02':
            assert 'CUMULATIVE' in meta['rationale_provenance']
            return 'recorded_cumulative_original_R_excerpt_tokens'
        if bank == 'source_only_controller_batch24':
            assert 'NEW_AUTHORED' in meta['annotation_provenance']
            return 'new_authored_source_only_controller_R_tokens'
        return 'new_authored_R_tokens'
    if component == 'A':
        if bank == 'real_state_repair_main':
            return 'revalidated_original_action_A_tokens'
        if bank == 'native_C_execution_local_02':
            return 'original_native_execution_A_tokens'
        if bank in NATIVE_LOCAL_A_BANKS:
            return 'original_native_local_process_A_tokens'
        assert meta.get('actual_native_tool_dispatch') is False
        return 'new_authored_native_action_projection_A_tokens'
    if component == 'D':
        if bank == 'new_real_state_cost_stop_02':
            return 'new_authored_cost_stop_D_tokens'
        if bank == 'source_only_controller_batch24':
            return 'new_authored_source_only_controller_D_tokens'
        assert meta.get('rationale_provenance') == 'ORIGINAL_VISIBLE_ASSISTANT_TEXT_NOT_THOUGHT_FIELD'
        return 'recorded_visible_commentary_D_tokens'
    if component == 'E':
        assert meta.get('rationale_provenance') == 'ORIGINAL_VISIBLE_ASSISTANT_TEXT_NOT_THOUGHT_FIELD'
        return 'recorded_visible_explanation_E_tokens'
    raise AssertionError((bank, component))


parents = {}


def find(item):
    parents.setdefault(item, item)
    if parents[item] != item:
        parents[item] = find(parents[item])
    return parents[item]


def union(left, right):
    left, right = find(left), find(right)
    if left != right:
        parents[max(left, right)] = min(left, right)


assert pin(MANIFEST)['sha256'] == EXPECTED
manifest, records, shard_pins = load_manifest(MANIFEST)
ids, owners = set(), set()
positive_target_count, rendered_target_count = 0, 0
row_inventory = []
for row in records:
    meta = row['original_record_metadata']
    owner = meta.get('owner_id', row['id'])
    assert row['id'] not in ids and owner not in owners
    ids.add(row['id']); owners.add(owner)
    assert row['split'] == 'train' and meta['training_admitted'] is True
    assert meta['source_admission'] == 'ADMIT'
    assert not any(meta.get(k) for k in ['original226', 'holdout12',
                                       'protected_sources_visible_prefix', 'protected_source_ids'])
    assert len(row['input_ids']) == row['total_tokens'] <= 32768
    token_array = array('I', row['input_ids'])
    if sys.byteorder != 'little':
        token_array.byteswap()
    assert sha(token_array.tobytes()) == row['input_ids_sha256_u32le']
    assert sha(canonical(row['supervision_spans'])) == row['supervision_spans_sha256']
    actual_components = Counter()
    last = 0
    for low, high, component, weight in row['supervision_spans']:
        assert 0 < low < high <= row['total_tokens'] and last <= low
        assert 0 < weight <= 1
        last = high
        actual_components[component] += high - low
    assert dict(actual_components) == row['supervised_tokens_by_component']
    assert sum(actual_components.values()) == row['supervised_tokens'] > 0
    positive_targets = [target for target in row['targets'] if target['owned_supervision_spans']]
    assert len(positive_targets) == len(meta['supervision_message_indices']) == 1
    assert positive_targets[0]['owned_supervision_spans'] == row['supervision_spans']
    positive_target_count += len(positive_targets)
    rendered_target_count += len(row['targets'])
    union('row:' + row['id'], 'group:' + row['source_group_id'])
    for source in row['source_ids']:
        union('row:' + row['id'], 'source:' + source)


def aggregate(selected):
    counts = Counter(); weighted = defaultdict(Decimal)
    origins = Counter(); weighted_origins = defaultdict(Decimal)
    weight_distribution = Counter()
    for row in selected:
        counts.update(sequences=1, targets=1, input_tokens=row['total_tokens'],
                      supervised_tokens=row['supervised_tokens'],
                      le16k_sequences=int(row['total_tokens'] <= 16384),
                      le32k_sequences=int(row['total_tokens'] <= 32768))
        for component, number in row['supervised_tokens_by_component'].items():
            counts['component_' + component] += number
            origins[origin_key(row, component)] += number
        for low, high, component, weight in row['supervision_spans']:
            number = high - low
            mass = Decimal(str(weight)) * number
            weighted[component] += mass
            weighted_origins[origin_key(row, component)] += mass
            weight_distribution[str(weight)] += number
    return {'counts': dict(counts),
            'weighted_label_mass': float(sum(weighted.values(), Decimal(0))),
            'weighted_label_mass_by_component': {k: float(v) for k, v in weighted.items()},
            'supervision_origin_tokens': dict(origins),
            'weighted_mass_by_origin': {k: float(v) for k, v in weighted_origins.items()},
            'positive_tokens_by_weight': dict(weight_distribution),
            'distinct_source_ids': len({s for row in selected for s in row['source_ids']}),
            'global_joined_source_components_represented': (len({find('row:' + row['id']) for row in selected})
                if all(row['id'] in ids for row in selected) else None),
            'declared_source_group_ids': len({row['source_group_id'] for row in selected}),
            'min_input_tokens': min(row['total_tokens'] for row in selected),
            'max_input_tokens': max(row['total_tokens'] for row in selected)}


all_actual = aggregate(records)
assert all_actual['counts'] == manifest['actual_counts']
assert all_actual['supervision_origin_tokens'] == manifest['supervision_origin_tokens']
assert all_actual['distinct_source_ids'] == manifest['distinct_source_ids']
assert all_actual['global_joined_source_components_represented'] == manifest['source_connected_components_across_banks']
contracts = [row for row in records if row['bank'] == 'source_contract_main']
process = [row for row in records if row['bank'] != 'source_contract_main']
bank_stats = {bank: aggregate([row for row in records if row['bank'] == bank])
              for bank in sorted({row['bank'] for row in records})}
stage_stats = {stage: aggregate([row for row in records if row['stage'] == stage])
               for stage in sorted({row['stage'] for row in records})}
for key, result in bank_stats.items():
    assert result['counts'] == manifest['by_bank'][key]
for key, result in stage_stats.items():
    assert result['counts'] == manifest['by_stage'][key]
literal_stage_groups = {}
for letter in ['A', 'B', 'C', 'D']:
    literal_stage_groups[letter] = aggregate([row for row in records if row['stage'].startswith(letter + '_')])
historical26 = aggregate([row for row in records if row['stage'] == 'historical_workflow_design_diagnosis_and_falsifiable_plan'])
assert sum(v['counts']['targets'] for v in literal_stage_groups.values()) + historical26['counts']['targets'] == len(records)

BASELINE = DATA / 'manifest_history/pre_curation09_cbb233f2a44bcb61/TRAINING_MANIFEST.json'
old_manifest, old_records, old_files = load_manifest(BASELINE)
assert pin(BASELINE)['sha256'] == manifest['curation09_rebase']['baseline_manifest_sha256']
assert pin(DATA / 'TRAINING_MANIFEST.json')['sha256'] == EXPECTED
old_by_id = {row['id']: row for row in old_records}
new_by_id = {row['id']: row for row in records}
removed_ids = set(old_by_id) - set(new_by_id)
added_ids = set(new_by_id) - set(old_by_id)
assert removed_ids == set(manifest['curation09_rebase']['revoked_record_ids'])
assert added_ids == set(manifest['curation09_rebase']['new_allowed_record_ids'])
assert all(new_by_id[identity] == old_by_id[identity] for identity in set(old_by_id) & set(new_by_id))
removed = aggregate([old_by_id[identity] for identity in removed_ids])
added = aggregate([new_by_id[identity] for identity in added_ids])
assert len(removed_ids) == 23 and len(added_ids) == 49
assert removed['counts']['supervised_tokens'] == 14727
assert added['counts']['supervised_tokens'] == 53319
assert old_manifest['actual_counts']['supervised_tokens'] - 14727 + 53319 == all_actual['counts']['supervised_tokens']

for row in records:
    row_inventory.append({'id': row['id'], 'owner_id': row['original_record_metadata'].get('owner_id', row['id']),
                          'bank': row['bank'], 'stage': row['stage'],
                          'source_ids': row['source_ids'], 'declared_group_id': row['source_group_id'],
                          'global_joined_component_sha256': sha(find('row:' + row['id']).encode()),
                          'input_tokens': row['total_tokens'], 'positive_tokens': row['supervised_tokens'],
                          'input_ids_sha256_u32le': row['input_ids_sha256_u32le'],
                          'supervision_spans_sha256': row['supervision_spans_sha256'],
                          'rendered_sha256': row['rendered_sha256']})

origins = all_actual['supervision_origin_tokens']
original_R = sum(origins[key] for key in ['original_native_R_tokens', 'historical_original_R_tokens',
                                        'recorded_cumulative_original_R_excerpt_tokens'])
new_R = origins['new_authored_R_tokens'] + origins['new_authored_source_only_controller_R_tokens']
native_A = sum(origins[key] for key in ['revalidated_original_action_A_tokens',
                                      'original_native_execution_A_tokens', 'original_native_local_process_A_tokens'])
original_and_new_summary = {
    'original_R_tokens_total': original_R,
    'original_R_is_three_distinct_provenance_classes_not_all_per_turn_native_CoT': True,
    'new_authored_R_tokens_total': new_R,
    'native_or_revalidated_A_tokens': native_A,
    'offline_new_functional_state_action_projection_A_tokens': origins['new_authored_native_action_projection_A_tokens'],
    'projection_includes_verbatim_original_code_and_declared_new_edits_not_all_newly_authored_code': True,
    'visible_explanation_E_tokens_not_original_thought': origins['recorded_visible_explanation_E_tokens']}
assert original_R + new_R == all_actual['counts']['component_R']
assert native_A + original_and_new_summary['offline_new_functional_state_action_projection_A_tokens'] == all_actual['counts']['component_A']

contract_components = {find('row:' + row['id']) for row in contracts}
process_components = {find('row:' + row['id']) for row in process}
contract_sources = {source for row in contracts for source in row['source_ids']}
process_sources = {source for row in process for source in row['source_ids']}
strategy = ROOT / 'research/plans/20261031_wrd_curation09/TRAINING_STRATEGY_09.md'
step_contract = math.ceil(len(contracts) / 16)
step_process = math.ceil(len(process) / 4)
evidence_paths = [OUT / 'holdout/MANIFEST.json', OUT / 'holdout/INPUT_ONLY_EVAL_ENTRYPOINT05.json',
                  OUT / 'holdout/PROTECTED_CURRENT569_REVOCATION_CLOSURE.json',
                  OUT / 'holdout/PROTECTED_VS_TRAIN_INDEPENDENT_QA.json',
                  OUT / 'eval_input_arrays09/MANIFEST.json',
                  OUT / 'eval_input_arrays09_independent/EVAL_INPUT_ARRAYS_INDEPENDENT_QA.json',
                  OUT / 'protection_followup09/FINAL17_FINAL02_INHERITANCE_QA.json',
                  OUT / 'protection_followup09_independent/FINAL17_ISOLATION_INDEPENDENT_QA.json',
                  DATA / 'manifest_staging09/STAGE_RECEIPT.json',
                  DATA / 'manifest_staging09/ACTIVATION_RECEIPT.json',
                  OUT / 'full_stage_qa02/INDEPENDENT_FULL_STAGED_REBASE09_QA.json',
                  OUT / 'reasoning/ORIGINAL26_IDENTITY_PARTITION_RECHECK09.json',
                  OUT / 'coverage/COVERAGE_RECONCILIATION09.json', strategy]
reasoning = read(OUT / 'reasoning/ORIGINAL26_IDENTITY_PARTITION_RECHECK09.json')
coverage = read(OUT / 'coverage/COVERAGE_RECONCILIATION09.json')
condition_keys = ['other_ancestry_hold', 'unreviewed_supplemental_prefix',
                  'current_source_identity_missing',
                  'lineage63_method_equivalent_but_protected_producer_and_no_frozen_merge',
                  'lineage8_specific_missing_evidence']
condition_counts = {key: coverage['effective_raw_owner_queues'][key] for key in condition_keys}
assert sum(condition_counts.values()) == 8376
assert reasoning['remaining_unknown_not_approved_chars'] == 208040
assert reasoning['new_positive_R_tokens'] == 0
assert sum(reasoning['partition_character_counts'].values()) == reasoning['original_R_characters']
full_qa = read(OUT / 'full_stage_qa02/INDEPENDENT_FULL_STAGED_REBASE09_QA.json')
assert full_qa['manifest_pin']['sha256'] == EXPECTED
assert full_qa['actual_counts'] == manifest['actual_counts']
assert full_qa['dual_actual_tokenizer_calls'] == {'primary_14b': 595, 'control_8b': 595}
assert full_qa['binary_file_count'] == 1785 and full_qa['binary_features_compared'] == 595
report = {
    'schema': 'wrd09-public-actual-data-and-coverage-recount-v1',
    'status': 'LOCAL_FROZEN_AND_ACTIVATED_COMPONENT_DATA_GIT_DELIVERY_PENDING',
    'staged_manifest_pin': pin(MANIFEST), 'active_manifest_pin': pin(DATA / 'TRAINING_MANIFEST.json'),
    'preserved08_baseline_manifest_pin': pin(BASELINE),
    'actual_shard_pins': shard_pins, 'actual': all_actual,
    'contracts': aggregate(contracts), 'process': aggregate(process),
    'overlap_between_contracts_and_process': {
        'shared_source_ids': len(contract_sources & process_sources),
        'shared_global_connected_components': len(contract_components & process_components),
        'source_and_component_counts_must_not_be_added': True},
    'literal_A_B_C_D': literal_stage_groups, 'historical26_separate': historical26,
    'by_bank': bank_stats, 'by_stage': stage_stats,
    'supervision_provenance_summary': original_and_new_summary,
    'positive_targets': positive_target_count,
    'all_rendered_assistant_target_metadata_rows_including_masked_context': rendered_target_count,
    'all_rendered_target_metadata_is_not_train_sample_count': True,
    'delta_from08': {
        'baseline': old_manifest['actual_counts'], 'removed': removed, 'added': added,
        'net_targets': len(added_ids) - len(removed_ids),
        'net_positive_tokens': added['counts']['supervised_tokens'] - removed['counts']['supervised_tokens'],
        'net_input_tokens': added['counts']['input_tokens'] - removed['counts']['input_tokens'],
        'all_546_retained_rows_exact_value_equal_to08': True,
        'removed_original_R_tokens': sum(removed['supervision_origin_tokens'].get(key, 0) for key in [
            'original_native_R_tokens', 'historical_original_R_tokens', 'recorded_cumulative_original_R_excerpt_tokens']),
        'new_original_R_tokens': sum(added['supervision_origin_tokens'].get(key, 0) for key in [
            'original_native_R_tokens', 'historical_original_R_tokens', 'recorded_cumulative_original_R_excerpt_tokens'])},
    'candidate_update_schedule_not_run': {
        'contract_owner_accumulation': 16, 'process_owner_accumulation': 4,
        'contract_one_pass_updates': step_contract, 'process_one_pass_updates': step_process,
        'first_candidate_total_updates': step_contract + step_process,
        'max_three_process_pass_total_updates': step_contract + 3 * step_process,
        'tail_batches_count_as_an_update': True, 'epochs_do_not_add_unique_data': True,
        'optimizer_steps_are_owner_exposure_schedule_not_runtime_or_full_pipeline_coverage': True},
    'evidence_pins': [pin(path) for path in evidence_paths],
    'manifest_readiness_flags': {key: manifest[key] for key in [
        'observed_stage_linked_chains', 'positive_qualified_retained_skill_chains',
        'single_native_session_autonomous_A_through_D_demonstrations',
        'observed_chain_is_separately_dispatched_native_stages_ending_STOP',
        'full_WRD_main_training_ready', 'default_full_pipeline_training_entrypoint',
        'model_weights_loaded', 'training_started', 'missing_main_stages']},
    'evaluation': {'ready_component_or_consumption_inputs': 26, 'dev': 9, 'test': 17,
                   'delivery_components': 24, 'clarification_components': 2,
                   'independent_full_WRD_tasks_ready': 0, 'model_evaluation_run': False},
    'remaining_gaps_with_explicit_units': {
        'original26_R': {'original_response_owners': reasoning['original_R_owners'],
            'total_original_unicode_characters': reasoning['original_R_characters'],
            'partition_character_counts': reasoning['partition_character_counts'],
            'current_positive_token_count_in_existing26': reasoning['actual_positive_R_tokens'],
            'still_unknown_not_approved_unicode_characters': reasoning['remaining_unknown_not_approved_chars'],
            'new_positive_R_tokens_this_round': 0,
            'unknown_is_not_discarded_or_proven_wrong': True},
        'raw_owner_conditional_queue_baseline': {
            'count': sum(condition_counts.values()), 'mutually_exclusive_subqueues': condition_counts,
            'lineage71_is_already_subset_of8376_not_additional': True,
            'reconciliation_bound_to_old569_manifest_sha256': coverage['pins'][0]['sha256'],
            'not_a_recomputed_new_trainable_or_guaranteed_salvage_count_after595': True,
            'lineage63_has_protected_producer_not_clean_salvage_pool': True},
        'autonomous_full_WRD_demonstrations': 0, 'qualified_KEEP_chains': 0,
        'full_WRD_independent_student_eval_ready': 0,
        'Spark_training_serving_long_window_and_quality_cost_efficacy_unverified': True},
    'technical_QA_evidence_not_a_new_rerun_by_this_report': {
        'independent_full595_dual_tokenizer_calls': full_qa['dual_actual_tokenizer_calls'],
        'independent_four_feature_sequences_compared': full_qa['binary_features_compared'],
        'canonical_binary_entities': full_qa['binary_file_count'],
        'all_retained_old_lines_byte_identical': full_qa['all_retained_old_lines_byte_identical'],
        'all_new_lines_byte_identical': full_qa['all_new_lines_byte_identical']},
    'historical_claim_corrections': [
        'Old selected-view or candidate counts did not measure the complete original corpus; raw evidence remains separate from admitted supervision.',
        '08 retained 23 now-protected views;09 withdraws their entire known source/component closure while preserving08 audit history.',
        'Historical workflow R26 is separate from literal B134 and is not26 complete autonomous skill-making tasks.',
        'New49 views add no recovered original teacher R;261 new rationale tokens are explicitly new-authored.',
        'Successful execution status, generated file count, complete code text and a clean functional prompt do not by themselves grant whole-content positive loss or prove clean original ancestry.',
        'Input tokens, compressed archive bytes, rendered masked assistant metadata and repeated exposures are not unique positive examples.'],
    'no_private_source_text_in_this_report': True,
    'public_counting_limits': [
        'Input tokens include context and masked output, not all positive training tokens.',
        'Weighted label mass is sum(weight times positive token count), not an independent sample count or a gradient norm.',
        'Global joined DSU unions actual row source_group_id and source_ids; it does not prove unknown resource ancestry absent.',
        'Literal stages are partial views and do not establish an autonomous A-through-D chain.',
        'Semantically scoped silver supervision and finite resource checks are not human gold, whole-business correctness, student efficacy or qualified skill utility.'],
    'row_inventory_metadata_only': row_inventory,
    'script_pin': pin(Path(__file__))}
target = OUT / 'ACTUAL_DATA_AND_COVERAGE09.json'
assert not target.exists()
target.write_bytes((json.dumps(report, ensure_ascii=False, indent=2) + '\n').encode())
print(json.dumps({'report_pin': pin(target), 'actual': all_actual,
                  'contracts': report['contracts'], 'process': report['process'],
                  'overlap': report['overlap_between_contracts_and_process'],
                  'literal_stage_targets': {key: value['counts']['targets'] for key, value in literal_stage_groups.items()},
                  'schedule': report['candidate_update_schedule_not_run']}, ensure_ascii=False))
