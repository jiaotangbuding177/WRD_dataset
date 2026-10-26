"""Independent static causal review of the fixed hypothetical controller v2."""
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'output/20261026_wrd_dataset_v9/coordination'
SOURCE = OUT / 'full_controller_rule_traces.synthetic.v2.jsonl.gz'


def main():
    counts = Counter()
    scenarios = []
    with gzip.open(SOURCE, 'rt', encoding='utf-8') as handle:
        traces = [json.loads(line) for line in handle]
    assert len(traces) == 12
    for trace in traces:
        assert trace['annotation_is_original_teacher_CoT'] is False
        assert trace['count_as_real_task'] is False
        assert trace['scope_status'] == 'SOURCE_INDEPENDENT_RULE_NO_ENTERPRISE_CONTENT'
        assert not trace['source_ids']
        assert len(trace['messages']) == len(trace['message_loss_mask'])
        approved = [i for i, value in enumerate(trace['message_loss_mask']) if value]
        assert approved == trace['supervision_candidate_message_indices']
        states, actions = [], []
        for index in approved:
            assert trace['messages'][index]['role'] == 'assistant'
            prior = json.loads(trace['messages'][index - 1]['content'])
            assert prior['scenario'] == trace['scenario']
            state = prior['hypothetical_state']
            assert state['hypothetical_state'] is True and state['not_an_actual_tool_or_trial_observation'] is True
            action = json.loads(trace['messages'][index]['content'])
            assert action['evidence_refs']
            operation = action['args']['operation']
            if 'candidate_version' in action['args']:
                assert action['args']['candidate_version'] == state['candidate_version']
                counts['explicit_current_version_args_checked'] += 1
            if action['next_stage'] == 'actor':
                assert state['candidate_present'] is True and state['resource_verification'] == 'pass'
                assert state['case_selection_complete'] is True and state['selected_case_count'] > 0
                assert not (state['paired_trial_state'] == 'both_done' and state['latest_pair_version_matches_candidate'])
            if action['next_stage'] == 'review':
                assert state['paired_trial_state'] == 'both_done' and state['latest_pair_version_matches_candidate']
            if action['next_stage'] == 'finalize':
                assert state['candidate_present'] is True
                assert state['resource_verification'] == 'pass' and state['delivery_quality'] == 'pass'
                assert state['resource_actually_used'] is True and state['all_attempt_cost'] == 'reduced'
                assert state['paired_trial_state'] == 'both_done' and state['latest_pair_version_matches_candidate']
                assert state['review_decision'] == 'retain' and not state['evidence_missing']
                counts['freeze_guard_checks'] += 1
            if operation == 'deliver_frozen_skill_and_evidence_refs':
                assert state['phase'] == 'frozen'
                assert actions[-1]['next_stage'] == 'finalize'
                assert actions[-1]['args']['candidate_version'] == state['candidate_version']
                counts['freeze_to_delivery_version_preserved'] += 1
            if state['user_stop']:
                assert action['next_stage'] == 'stop'
            if state.get('environment_capability_missing'):
                assert action['next_stage'] == 'wait' and action['args']['do_not_change_native_environment'] is True
            if state['paired_trial_state'] == 'one_arm_running':
                assert action['next_stage'] == 'wait' and action['args']['do_not_duplicate'] is True
            if state['evidence_missing']:
                assert action['next_stage'] == 'recover_evidence'
                assert action['args']['do_not_rerun_completed_trials'] is True
            if states:
                previous = states[-1]
                assert int(state['candidate_version'][1:]) >= int(previous['candidate_version'][1:])
                if state['candidate_version'] != previous['candidate_version']:
                    assert actions[-1]['args']['operation'] in {'local_revision_then_matching_version_trial', 'local_resource_repair'}
                    assert state['revision_budget_remaining'] == previous['revision_budget_remaining'] - 1
                    assert state['paired_trial_state'] == 'not_started' and not state['latest_pair_version_matches_candidate']
                    assert state['delivery_quality'] == 'unknown' and state['all_attempt_cost'] == 'unknown'
                    assert state['resource_actually_used'] is None and state['review_decision'] is None
                    counts['new_version_invalidates_old_trial_quality_cost_checked'] += 1
                else:
                    for field in ['candidate_present', 'case_selection_complete', 'resource_verification', 'delivery_quality', 'resource_actually_used', 'all_attempt_cost', 'latest_pair_version_matches_candidate']:
                        if previous[field] in ('pass', 'reduced', True):
                            assert state[field] not in ('unknown', None, False), (trace['scenario'], field)
                    counts['same_version_state_continuity_transitions_checked'] += 1
            states.append(state)
            actions.append(action)
            counts['state_action_pairs_checked'] += 1
        scenarios.append({'scenario': trace['scenario'], 'assistant_targets': len(approved), 'versions': sorted({s['candidate_version'] for s in states}), 'final_stage': actions[-1]['next_stage']})
    assert counts['state_action_pairs_checked'] == 82
    report = {'schema_version': 'wrd-v9-independent-controller-v2-causal-review-1.0', 'status': 'PASS_BOUNDED_STATIC_RULE_REVIEW',
        'source': {'path': str(SOURCE), 'sha256': hashlib.sha256(SOURCE.read_bytes()).hexdigest(), 'bytes': SOURCE.stat().st_size},
        'counts': dict(counts), 'scenarios': scenarios,
        'qualitative_review': 'All 12 state/action traces reviewed. No remaining obvious version-reset, stale-trial inheritance, lost-established-fact, premature-freeze or repeated-running-trial contradiction found in the declared hypothetical states.',
        'scope_limitations': [
            'Hypothetical state updates are supplied by the exercise; they are not real tool results or proof that a repair worked.',
            'The resource-repair scenario supplies a fresh hypothetical verification pass after repair; it is not inferred from a write success.',
            'Baseline reuse is conditioned on identical task/resources in the scenario, not an independently verified real cost saving.',
            'This is controller-policy data, not a demonstrated autonomous WRD execution or semantic skill-quality dataset.'
        ], 'training_started': False, 'generated_skill_code_executed': False}
    (OUT / 'CONTROLLER_V2_CAUSAL_REVIEW.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'status': report['status'], 'counts': dict(counts), 'source_sha256': report['source']['sha256']}, ensure_ascii=False))


if __name__ == '__main__':
    main()
