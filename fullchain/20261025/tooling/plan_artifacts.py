"""Build a non-executable, aggregate-only full-chain training plan ledger."""
import hashlib
import json
from pathlib import Path


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def write(p, value):
    p.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def main():
    root = Path(__file__).resolve().parents[3]
    source = root / 'output/20261025_wrd_fullchain_reaudit'
    out = root / 'research/plans/20261025_wrd_fullchain_distillation'
    reports = {n: json.loads((source / n).read_text(encoding='utf-8-sig')) for n in
               ('FULLCHAIN_COVERAGE.json', 'CONTENT_AUDIT.json', 'LINK_AUDIT.json')}
    coverage, content, link = reports.values()
    core = ('screen', 'make', 'prepare', 'review')
    nonempty = {s: v['assistant_targets'] - v['empty_targets'] for s, v in content['by_stage'].items()}
    assert sum(nonempty[s] for s in core) == 19728
    assert sum(nonempty.values()) == 32014
    ledger = {
        'schema_version': 'wrd-fullchain-data-ledger-v3',
        'status': 'OBSERVED_INVENTORY_NOT_FULL_SFT_ADMISSION',
        'enterprise_source_conversations': 1107,
        'canonical_execution_sessions': coverage['controlled_master']['episodes'],
        'assistant_positions': coverage['controlled_master']['assistant_targets'],
        'content_by_stage': content['by_stage'],
        'nonempty_candidate_positions_by_stage': nonempty,
        'core_distiller_sessions': sum(content['by_stage'][s]['episodes'] for s in core),
        'core_distiller_nonempty_candidates': sum(nonempty[s] for s in core),
        'core_distiller_visible_text_targets': sum(content['by_stage'][s]['visible_text_targets'] for s in core),
        'public_projection_sessions': coverage['public_projection']['episodes'],
        'public_projection_assistant_positions': coverage['public_projection']['assistant_targets'],
        'unique_artifact_text_objects': coverage['artifact_recovery']['unique_resource_or_stage_json_text_objects'],
        'artifact_objects_by_stage': coverage['artifact_recovery']['unique_text_objects_by_stage'],
        'recovered_label_units': link['recovered_structured_label_units'],
        'extracted_parent_document_counts': link['stage_extracted_parent_document_counts'],
        'extracted_field_record_counts': link['stage_extracted_field_record_counts'],
        'extracted_field_records': sum(link['stage_extracted_field_record_counts'].values()),
        'review_decision_counts': link['structured_decision_class_counts']['review_decision:decision'],
        'screen_decision_counts': link['structured_decision_class_counts']['screen_decisions:action'],
        'explicit_link_edges': link['explicit_edges_total'],
        'route_presence_counts': link['route_group_counts'],
        'review_to_revision_make_pairs': link['explicit_review_to_make_episode_pairs'],
        'pairs_with_explicit_predecessor_make': link['revision_pairs_with_explicit_predecessor_make_reference'],
        'missing_canonical_sessions': link['missing_canonical_episode_count'],
        'noncanonical_evidence_counts': link['noncanonical_evidence_counts'],
        'new_fullchain_semantic_admission_completed': False,
        'new_fullchain_mask_compilation_completed': False,
        'new_fullchain_common16k_count': None,
        'new_fullchain_common32k_count': None,
        'new_fullchain_supervised_token_count': None,
        'new_verified_same_state_dpo_pairs': None,
        'confirmed_independent_generalization_groups': None,
        'reviewed_or_extracted_labels_are_not_human_gold': True,
        'legacy_93_are_diagnostic_only': True,
        'source_reports_sha256': {n: sha(source / n) for n in reports},
        'training_started': False,
        'new_business_model_calls': 0,
    }
    assert ledger['extracted_field_records'] == 15104
    write(out / 'DATA_LEDGER.json', ledger)
    plan = {
        'schema_version': 'wrd-fullchain-distillation-plan-v3',
        'execution_authorized': False, 'is_launch_config': False, 'training_started': False,
        'status': 'PLAN_ONLY_DATA_ADMISSION_PENDING',
        'models': [
            {'role': 'primary', 'id': 'Qwen/Qwen3-14B', 'revision': '40c069824f4251a91eefaf281ebe4c544efd3e18'},
            {'role': 'control', 'id': 'Qwen/Qwen3-8B', 'revision': 'b968826d9c46dd6066d109eabc6255188de91218'}],
        'data_scope': {'core_stages': list(core), 'core_candidate_nonempty_positions': 19728,
                       'actor_auxiliary_nonempty_candidates': 11683, 'legacy_nonempty_candidates_separate': 603,
                       'same_source_split_ids_and_supervision_exposure': True,
                       'training_admission_manifest': None, 'public_release_is_not_local_training_admission': True},
        'candidate_hardware': {'device': 'DGX Spark GB10', 'architecture': 'aarch64', 'unified_memory_gib': 121,
                               'container_digest': None, 'on_device_validation_completed': False},
        'sft': {'method': 'BF16 LoRA', 'r': 32, 'alpha': 64, 'dropout': 0.05,
                'target_modules': ['q_proj', 'k_proj', 'v_proj', 'o_proj', 'gate_proj', 'up_proj', 'down_proj'],
                'microbatch': 1, 'gradient_accumulation': 16, 'optimizer': 'AdamW',
                'base_learning_rate': 1e-4, 'feedback_refinement_learning_rate': 3e-5,
                'warmup_ratio': 0.03, 'lr_schedule': 'cosine', 'weight_decay': 0.01, 'max_grad_norm': 1.0,
                'gradient_checkpointing': True, 'use_cache': False, 'attention_candidate': 'sdpa',
                'training_processes': 1, 'train_models_sequentially': True,
                'candidate_total_sequence_lengths': [4096, 8192, 16384, 32768],
                'automatic_truncation': False, 'runtime_options_verified': False},
        'curriculum': [
            {'phase': 1, 'objective': 'stage decisions and evidence summaries', 'length_candidates': [4096, 8192]},
            {'phase': 2, 'objective': 'native resource construction and multi-turn trajectories', 'length_candidates': [16384, 32768]},
            {'phase': 3, 'objective': 'observed feedback-conditioned repairs and phase transitions', 'extra_supervised_exposure_max_fraction': 0.5}],
        'loss': {'core_stage_weights': {'A': 0.2, 'B': 0.35, 'C': 0.30, 'D': 0.15},
                 'core_weight': 0.9, 'actor_auxiliary_weight_if_admitted': 0.1,
                 'normalization': 'stage, parent, admitted target tokens; explicit parent view budget',
                 'rare_decision_sampling_probability_ratio_cap': 3,
                 'derived_summary_max_fraction_of_main_budget': 0.2,
                 'masked_inputs': ['system', 'user', 'tool_results', 'unadmitted_assistant_history',
                                   'admitted_but_not_owned_history', 'all_tokens_outside_owned_admitted_target_spans', 'padding'],
                 'native_tool_schema': 'actual recorded per-session schemas; never delete non-core7 context to fit old exporter',
                 'rare_class_sampling_and_loss_multiplier_not_duplicated': True,
                 'stage_parent_weighted_loss_implementation_completed': False,
                 'one_owner_per_native_target_in_overlapping_windows': True},
        'dpo': {'part_of_required_main_training': False, 'verified_same_prompt_pairs': None,
                'conditional_beta': 0.1, 'conditional_learning_rate': 5e-6, 'conditional_max_epochs': 1,
                'no_pairing_pre_feedback_failure_with_post_feedback_repair': True},
        'thinking': {'existing_visible_text_supervision': True, 'derived_evidence_summaries_labeled': True,
                     'inspected_request_objects': 3817, 'inspected_response_objects': 1807, 'inspected_event_objects': 1763,
                     'observed_explicit_reasoning_payloads_in_inspected_fields': 0,
                     'thinking_off_configuration_response_objects': 1579,
                     'source_visible_text_targets': 9723, 'core_visible_text_targets': 6045,
                     'claim_hidden_teacher_cot_recovered': False, 'logit_distillation_available': False},
        'evaluation': {'fixed_native_openclaw_loop': True, 'fixed_business_actor_for_main_comparison': True,
                       'proposed_independent_blind_groups': 24, 'tasks_per_group': 2,
                       'main_arms': ['T', 'S8', 'S14'], 'base_making_slots': 72, 'base_consumption_slots': 192,
                       'independent_groups_currently_verified': None, 'formal_226_250_not_training_or_selection': True,
                       'proposed_quality_noninferiority_margin_points': 5,
                       'proposed_tsr_noninferiority_margin_percentage_points': 5,
                       'proposed_operating_cpqs_reduction_fraction': 0.30,
                       'thresholds_calibrated_and_frozen': False},
        'cost': {'actual_training_throughput': None, 'actual_peak_memory': None,
                 'actual_device_hours': None, 'actual_training_kwh': None,
                 'count_all_failures_revisions_teacher_fallback_and_training_amortization': True},
    }
    write(out / 'TRAINING_PLAN.json', plan)
    print(json.dumps({'core_nonempty_candidates': 19728, 'all_nonempty_candidates': 32014,
                      'field_records': ledger['extracted_field_records'], 'repair_pairs': ledger['review_to_revision_make_pairs'],
                      'execution_authorized': False}))


if __name__ == '__main__':
    main()
