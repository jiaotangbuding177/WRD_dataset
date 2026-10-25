"""Build the quantitative, non-executable v4 plan from actual final receipts."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def sha(p):
    h = hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda: f.read(1024 * 1024), b''):
            h.update(b)
    return h.hexdigest()


def save(p, value):
    p.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def main():
    base = ROOT / 'output/20261025_wrd_reasoning_recovery_v4'
    plan = ROOT / 'research/plans/20261025_wrd_reasoning_distillation_v4'
    names = ['RAW_RECOVERY_REPORT.json', 'SSE_REASONING_RECOVERY_REPORT.json', 'RAW_SCOPE_REVIEW.json',
             'SSE_ACTION_OUTCOME_AUDIT.json', 'SSE_SEMANTIC_SAMPLE_REVIEW.json',
             'HISTORICAL_NATIVE_RECOVERY_REPORT.json', 'NATIVE_SOURCE_SPLIT_AUDIT.json',
             'FINAL_NATIVE_COMPILATION_REPORT.json', 'COMPILED_DATA_INDEPENDENT_QA.entrypoints.json']
    r = {name: json.loads((base / name).read_text(encoding='utf-8')) for name in names}
    native = json.loads((base / 'curated_native/CURATED_NATIVE_REPORT.json').read_text(encoding='utf-8'))
    original = json.loads((base / 'curated_reasoning/CURATED_REASONING_REPORT.json').read_text(encoding='utf-8'))
    gate = json.loads((base / 'source_gated_profiles/SOURCE_GATED_PROFILE_REPORT.json').read_text(encoding='utf-8'))
    pub = json.loads((base / 'public_reasoning_compiled_final/PUBLIC_REASONING_COMPILATION_REPORT.json').read_text(encoding='utf-8'))
    data = {
        'schema_version': 'wrd-reasoning-data-report-v4',
        'design_revision': '5.0.28', 'change_id': 'ALG-20261026-01',
        'status': 'RECOVERED_COMPILED_AUDITED_PROCESS_SILVER_NOT_PROVEN_FULL_AGENT',
        'archived_original_sse': r['SSE_REASONING_RECOVERY_REPORT.json']['counts'],
        'raw_request_response_recovery': r['RAW_RECOVERY_REPORT.json']['counts_by_scope'],
        'original_sse_outcome_gate': {'source_qualified': 45, 'observed': 17, 'applied': 14,
                                      'finished_structural_only': 2, 'rejected_masked': 12},
        'current_native_quality_curated': native['reports'],
        'original_reasoning_quality_curated': original['counts'],
        'strict_226_and_wider_scope_profiles': gate,
        'public_original_reasoning_compiler_report': pub,
        'old_rejected_ai_review_ids_masked': 61,
        'source_reasoning_characters_are_not_tokens': True,
        'stage_windows_are_not_full_autonomous_runs': True,
        'raw_response_pairs_are_not_independent_enterprise_tasks': True,
        'source_scope_decision': 'pending user clarification; protected226 retained by default',
        'training_started': False, 'human_semantic_gold': 0,
        'source_receipt_sha256': {name: sha(base / name) for name in names},
        'curated_receipt_sha256': {path: sha(base / path) for path in
            ['curated_native/CURATED_NATIVE_REPORT.json', 'curated_reasoning/CURATED_REASONING_REPORT.json',
             'source_gated_profiles/SOURCE_GATED_PROFILE_REPORT.json',
             'public_reasoning_compiled_final/PUBLIC_REASONING_COMPILATION_REPORT.json']},
    }
    save(plan / 'DATA_REPORT.json', data)
    config = {
        'schema_version': 'wrd-reasoning-distillation-plan-v4',
        'design_revision': '5.0.28', 'change_id': 'ALG-20261026-01',
        'execution_authorized': False, 'is_launch_config': False, 'training_started': False,
        'goal': 'single-business-input autonomous WRD skill distillation in native OpenClaw',
        'models': [
            {'role': 'primary', 'id': 'Qwen/Qwen3-14B', 'revision': '40c069824f4251a91eefaf281ebe4c544efd3e18'},
            {'role': 'control', 'id': 'Qwen/Qwen3-8B', 'revision': 'b968826d9c46dd6066d109eabc6255188de91218'}],
        'hardware': {'device': 'DGX Spark GB10', 'architecture': 'aarch64', 'unified_memory_gib': 121,
                     'source': 'user report; no device execution this round', 'container_digest': None},
        'method': 'source-verified sequence distillation with original reasoning, segment loss and feedback repair',
        'sft': {'dtype': 'bfloat16', 'method': 'LoRA', 'rank': 32, 'alpha': 64, 'dropout': 0.05,
                'target_modules': ['q_proj', 'k_proj', 'v_proj', 'o_proj', 'gate_proj', 'up_proj', 'down_proj'],
                'optimizer': 'AdamW', 'learning_rate': 1e-4, 'repair_learning_rate': 3e-5,
                'warmup_ratio': 0.03, 'lr_schedule': 'cosine', 'weight_decay': 0.01, 'clip_norm': 1.0,
                'microbatch': 1, 'gradient_accumulation': 16, 'gradient_checkpointing': True,
                'use_cache': False, 'attention_candidate': 'sdpa',
                'length_buckets': [4096, 8192, 16384, 32768], 'automatic_truncation': False,
                'train_models_sequentially': True, 'initial_normalized_exposure_epochs': 1.0,
                'extra_feedback_exposure_max_fraction': 0.5,
                'runtime_compatibility_and_throughput_verified': False},
        'loss': {'segment_means_before_stage_parent_mean': True,
                 'lambda': {'R_original_reasoning': 0.25, 'E_visible_explanation': 0.10,
                            'A_actions_resources': 0.45, 'D_decisions': 0.20},
                 'format_loss_auxiliary_lambda': 0.02,
                 'missing_segments_renormalized_not_invented': True,
                 'compiler_span_weights_are_base_masks_not_the_full_training_objective': True,
                 'stage_weights': {'A': 0.20, 'B': 0.35, 'C': 0.30, 'D': 0.15},
                 'actor_auxiliary_loss_max_fraction': 0.10,
                 'derived_control_or_summary_max_fraction_of_main_budget': 0.20,
                 'candidate_original_reasoning_supervision_exposure_fraction': 0.10,
                 'original_reasoning_parent_replay_max_normalized_passes': 2,
                 'reasoning_replay_included_in_total_exposure_budget': True,
                 'rare_decision_sampling_cap': 3,
                 'do_not_double_apply_sampling_and_class_loss_weights': True,
                 'one_native_target_one_loss_owner': True,
                 'ignore_label': -100,
                 'loss_implementation_as_training_runner_completed': False},
        'curriculum': ['original reasoning and short causal decisions',
                       'native multi-turn resource construction and observations',
                       'actual feedback repairs and provenance-labelled phase control'],
        'data_profiles': {'default': 'strict226_direct_source_teacher_silver',
                          'protected226_override_authorized': False,
                          'wider_scope_records_are_candidates_not_default_training_rows': True,
                          'never_merge_public_and_controlled_duplicate_projections': True,
                          'full_target_readiness': False},
        'serialization': {'causal_qwen3_template_variant': True,
                          'claim_unmodified_official_template': False,
                          'same_template_required_in_future_student_api': True,
                          'api_template_integration_verified': False},
        'conditional_dpo': {'part_of_main_required_training': False, 'same_state_verified_pairs': None,
                            'do_not_pair_before_feedback_failure_with_after_feedback_repair': True},
        'on_policy': {'implemented': False, 'execution_authorized': False,
                      'purpose_if_later_authorized': 'student-own errors and long-horizon stagnation; fixed native harness'},
        'evaluation': {'single_input_no_human_stage_prompts_required': True,
                       'fixed_business_actor_for_skill_quality_comparison': True,
                       'quality_metrics': ['TSR', 'independent_five_dimension_Q', 'K_Q', 'K_R', 'K_G'],
                       'proposed_new_independent_groups': 24, 'tasks_per_group': 2,
                       'main_arms': ['teacher', '8B_student', '14B_student'],
                       'base_making_slots': 72, 'base_consumption_slots': 192,
                       'proposed_q_noninferiority_margin_points': 5,
                       'proposed_tsr_margin_percentage_points': 5,
                       'proposed_operating_cpqs_reduction': 0.30,
                       'thresholds_calibrated': False, 'new_independent_blind_test_ready': False},
        'cost': {'processed_tokens_including_masked_inputs_counted': True,
                 'count_failures_revisions_assessment_human_fallback_and_training_amortization': True,
                 'actual_spark_training_tokens_per_second': None, 'actual_device_hours': None,
                 'actual_whole_machine_kwh': None, 'currency_total': None,
                 'assistant_research_and_annotation_service_cost': 'not measured; not zero'},
    }
    save(plan / 'TRAINING_PLAN.json', config)
    readiness = {
        'schema_version': 'wrd-reasoning-readiness-v4',
        'raw_original_thinking_recovered': True, 'causal_token_mask_checks_passed': True,
        'process_teacher_silver_available': True,
        'full_autonomous_target_training_ready': False, 'deployment_ready': False,
        'training_started': False,
        'open_items': [
            'protected226 scope clarification pending; strict profile retained by default',
            'strict profile A-screen4 and C-prepare3 windows cannot support a claim of full-chain sufficiency',
            'historical original reasoning has limited independent source diversity and a different action protocol',
            'causal template and fixed-Actor child-trial interface need runtime compatibility validation',
            'independent development and single-input full-loop evaluation have not been executed',
            'full semantic gold and complete transitive resource/source isolation are not established'],
        'do_not_infer_from_static_pass': ['all reasoning correct', 'enough for guaranteed autonomy', 'training authorized'],
    }
    save(plan / 'READINESS.json', readiness)
    print(json.dumps({'plan_files_written': 3, 'full_target_training_ready': False,
                      'source_scope': 'pending clarification; strict default'}, ensure_ascii=False))


if __name__ == '__main__':
    main()
