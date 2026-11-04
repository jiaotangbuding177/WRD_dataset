"""Finalize the bounded native collection census; not a training readiness claim."""
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / 'output/20261027_wrd_main_v10'
RUN = BASE / 'runtime_preflight'
OUT = RUN / 'quality/FIRST_CHAIN_INDEPENDENT_REVIEW'


def load(p):
    return json.loads(p.read_text(encoding='utf-8-sig'))


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    episode_ids = ['technical_native_child_capture_probe', 'A_screen_narrative_01',
                   'B_make_report_01', 'B_make_report_02', 'B_revision_report_01',
                   'C_L_no_skill_01', 'C_L_skill_01', 'C_E_skill_01', 'C_E_no_skill_01',
                   'C_review_report_01']
    episodes = []
    complete_responses = r_chars = 0
    for job_id in episode_ids:
        episode = RUN / 'episodes' / job_id
        raw_report = BASE / 'native_records' / job_id / 'raw_recovery/EXTRACTION_REPORT.json'
        extraction = load(raw_report) if raw_report.is_file() else None
        count = len([p for p in (episode / 'api_audit').iterdir() if p.is_dir()])
        row = {'job_id': job_id, 'outer_dispatch_sha256': sha(episode / 'dispatch.json'),
               'actual_job_sha256': sha(episode / 'job.json'), 'compatible_HTTP_records': count,
               'result': load(episode / 'result.json')['status'] if (episode / 'result.json').is_file() else 'DISPATCHED_INTERRUPTED_UNRESOLVED',
               'original_R_extraction': None}
        if extraction:
            row['original_R_extraction'] = {
                'path': str(raw_report), 'sha256': sha(raw_report),
                'complete_responses': extraction['captured_complete_responses'],
                'original_readable_R_chars': extraction['original_readable_R_chars'],
                'reviewed_student_records_from_raw_recovery': extraction['reviewed_student_records']}
            complete_responses += extraction['captured_complete_responses']
            r_chars += extraction['original_readable_R_chars']
        episodes.append(row)
    cost = load(OUT / 'ACTUAL_COST_RECONCILIATION.json')
    qcalc = load(OUT / 'Q_ARITHMETIC_AUDIT.json')
    q = qcalc['calculations']
    metrics = {}
    for case, mapping in {'L': {'no_skill': 'B', 'skill': 'A'}, 'E': {'no_skill': 'A', 'skill': 'B'}}.items():
        metrics[case] = {}
        for arm, label in mapping.items():
            ep = RUN / 'episodes' / ('C_' + case + '_' + arm + '_01')
            usage = load(ep / 'usage.json')
            metrics[case][arm] = {'seconds': load(ep / 'result.json')['seconds'],
                'actual_model_calls': usage['model_calls'], 'actual_total_tokens': usage['total_tokens'],
                'Q_0_to_100_uncalibrated': q[case + '_' + label]['recomputed_Q_0_to_100'],
                'actual_native_full_skill_read': bool(load(ep / 'response.json')['loaded_skill_ids']),
                'functional_bytes_stable': load(ep / 'CONSUMPTION_AUDIT.json')['all_supplied_skill_functional_bytes_stable']}
    ns = sum(row['no_skill']['actual_total_tokens'] for row in metrics.values())
    skill = sum(row['skill']['actual_total_tokens'] for row in metrics.values())
    summary = {'schema': 'wrd-first-bounded-native-chain-census-and-evidence-v1',
        'status': 'FIRST_PILOT_COLLECTION_AND_SCOPED_AUDIT_COMPLETE_NOT_FULL_MAIN_DATASET_READY',
        'execution_design_revision': '5.0.39', 'physical_outer_dispatches': len(episodes),
        'actual_native_sessions': 11, 'technical_probe_parent_and_child_are_two_sessions': True,
        'unique_business_source_ids': ['conv_d1ef29d65e7a', 'conv_41874c950938', 'conv_246b5e915810', 'conv_27abfa260f9c'],
        'business_mechanism_families': 1, 'episodes': episodes,
        'compatible_HTTP_total': sum(e['compatible_HTTP_records'] for e in episodes),
        'complete_business_compatible_responses_original_fields_recovered': complete_responses,
        'complete_business_original_readable_R_chars': r_chars,
        'interrupted_B01_original_R_chars_additionally_preserved': 6157,
        'complete_responses_or_chars_not_claimed_positive_training_targets': True,
        'raw_recovery_views_compiled_by_this_collection_agent': 0,
        'training_admission_and_actual_common_token_arrays_owned_by_root': True,
        'stage_coverage': {
            'A': 'one actual clean native source-screening session; source-only interpretation separately reviewed',
            'B': 'one actual make plus interrupted attempt; actual code/schema/template/header and tests preserved',
            'feedback_revision': 'actual independent valid-input rejection and malformed nested refs probes -> native exact local repair -> original21 plus independent8 verification',
            'C': 'two actual source tasks x fresh NoSkill/Skill sessions; one maker-seen reproduction, one maker-unseen train-development source, same clean five-file version',
            'C_review_to_logical_D': 'one real native review; source-only blind Q written and acknowledged before arm/cost/candidate reads, then STOP and feedback',
            'full_autonomous_single_native_A_to_D': 0,
            'qualified_retained_skills': 0},
        'consumption_metrics': metrics,
        'consumption_total_tokens': {'no_skill': ns, 'skill': skill, 'skill_div_no_skill': skill / ns},
        'actual_known_cost_after_native_review': cost,
        'blind_order_audit': str(OUT / 'BLIND_ORDER_AUDIT.json'),
        'Q_arithmetic_audit': str(OUT / 'Q_ARITHMETIC_AUDIT.json'),
        'semantic_errata': str(OUT / 'SEMANTIC_ERRATA.json'),
        'final_native_decision': 'STOP', 'sealed_skill_created': False,
        'no_phase11_or_more_dispatched': True, 'own_bridge_left_running_without_new_model_requests': True,
        'original226_newH_static_dev_test_still_isolated': True, 'training_started': False,
        'remaining_gaps': ['retained positive complete chains', 'other mechanisms and real attachments',
                           'native full autonomous controller', 'main labels and loss arrays still need scoped semantic curation',
                           'independent final generalization and Spark model runtime not tested'],
        'source_packet_safety': 'Do not tar the whole runtime/workspace. Exact native APIs/response fields/observations/declared outputs/version objects may be packaged via explicit selection. runtime_preflight/private and clean_inputs/private_credential_audit raw SQLite/SDK traces stay private.'}
    path = OUT / 'FIRST_CHAIN_SUMMARY.json'
    assert not path.exists()
    path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'summary': str(path), 'HTTP': summary['compatible_HTTP_total'],
                      'complete_business_responses': complete_responses, 'original_R_chars': r_chars,
                      'native_known_tokens': cost['known_total_tokens'], 'native_requests': cost['actual_request_identities'],
                      'skill_token_multiplier': skill / ns, 'retained': 0}))


if __name__ == '__main__':
    main()
