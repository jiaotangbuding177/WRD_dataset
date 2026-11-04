"""Independently recheck the repaired candidate before bounded real C trials."""
from copy import deepcopy
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import shutil

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('shared_posthoc', HERE / 'audit_B02_resources.py')
shared = importlib.util.module_from_spec(spec)
spec.loader.exec_module(shared)
BASE = shared.BASE
EP = BASE / 'episodes/B_revision_report_01'
OLD = BASE / 'episodes/B_make_report_02'
OUT = BASE / 'quality/B_REVISION01_INDEPENDENT_RESOURCE_AUDIT'


def main():
    global OUT
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--skill-root', type=Path)
    ap.add_argument('--output', type=Path)
    args = ap.parse_args()
    if args.output:
        OUT = args.output.resolve()
    skill_root = args.skill_root.resolve() if args.skill_root else EP / 'workspace/outputs/skill'
    assert shared.load(EP / 'result.json')['status'] == 'completed'
    OUT.mkdir(exist_ok=False)
    (OUT / 'isolated_copy').mkdir()
    (OUT / 'extra_fixtures').mkdir()
    shutil.copytree(skill_root, OUT / 'isolated_copy/skill')
    # Exact old tests/fixtures are used, so changed new expectations cannot wash green.
    shutil.copytree(OLD / 'workspace/outputs/tests', OUT / 'isolated_copy/tests')
    original_test_unchanged = {}
    for name in ('run_tests.py', 'make_fixtures.py'):
        original_test_unchanged[name] = shared.sha(OLD / 'workspace/outputs/tests' / name) == shared.sha(EP / 'workspace/outputs/tests' / name)
    original_fixture_matches = all(shared.sha(p) == shared.sha(EP / 'workspace/outputs/tests/fixtures' / p.name)
                                   for p in (OLD / 'workspace/outputs/tests/fixtures').glob('*') if p.is_file())
    source = shared.load(BASE / 'quality/B02_INDEPENDENT_RESOURCE_AUDIT/extra_fixtures/legal_sources.json')
    ledger = shared.load(BASE / 'quality/B02_INDEPENDENT_RESOURCE_AUDIT/extra_fixtures/legal_ledger.json')
    draft = shared.load(BASE / 'quality/B02_INDEPENDENT_RESOURCE_AUDIT/extra_fixtures/legal_draft.json')
    shared.OUT = OUT
    rows = [shared.run('original_21_unchanged_independent_reproduction', ['/workspace/outputs/tests/run_tests.py'])]
    specs = []

    def case(label, src, led, dft, expected_exit, failure_id=None):
        specs.append((label, src, led, dft, expected_exit, failure_id))

    case('valid_different_year_actual_goal', deepcopy(source), deepcopy(ledger), deepcopy(draft), 0)
    s, l, d = deepcopy(source), deepcopy(ledger), deepcopy(draft)
    s['sources'][0]['messages'][0]['content'] = '2026年实际培训100人；2026年计划培训100人。'
    l['facts'][0].update(time='2026', claim='2026年实际培训100人')
    l['facts'][0]['evidence_refs'][0]['quote'] = '2026年实际培训100人'
    d['text'] = '2026年实际培训100人，2026年计划培训100人。'
    case('valid_same_year_actual_goal', s, l, d, 0)
    for label, malformed, fid in (
        ('nested_non_list', 'invalid-ref', 'evidence_refs_not_list'),
        ('nested_non_object', [42], 'evidence_refs_item_not_object')):
        l = deepcopy(ledger)
        l['task_switches'] = [{'evidence_refs': malformed}]
        case(label, deepcopy(source), l, deepcopy(draft), 1, fid)
    l = deepcopy(ledger)
    l['task_switches'] = [{'evidence_refs': []}]
    case('valid_optional_empty_list', deepcopy(source), l, deepcopy(draft), 0)
    d = deepcopy(draft)
    d['fact_refs'][1]['as_type'] = 'achieved_fact'
    case('invalid_goal_as_achieved', deepcopy(source), deepcopy(ledger), d, 1, 'type_mismatch_planned_goal_as_achieved')
    l = deepcopy(ledger)
    l['facts'][1]['evidence_refs'] = []
    case('invalid_required_empty_list', deepcopy(source), l, deepcopy(draft), 1, 'missing_required_evidence')
    l = deepcopy(ledger)
    l['task_switches'] = [{'evidence_refs': [{'source_id': 'independent_synthetic', 'message_id': 'm1', 'quote': 'not-a-source-substring'}]}]
    case('invalid_nested_quote', deepcopy(source), l, deepcopy(draft), 1, 'evidence_quote_not_contiguous')
    outcomes = []
    for label, src, led, dft, expected, required in specs:
        for suffix, value in (('sources', src), ('ledger', led), ('draft', dft)):
            shared.save(OUT / 'extra_fixtures' / (label + '_' + suffix + '.json'), value)
        row = shared.run(label, ['/workspace/outputs/skill/scripts/validate_pack.py', 'validate',
                  '--ledger', '/independent/' + label + '_ledger.json',
                  '--draft', '/independent/' + label + '_draft.json',
                  '--sources', '/independent/' + label + '_sources.json',
                  '--report', '/workspace/outputs/' + label + '_report.json'])
        report = shared.load(OUT / 'isolated_copy' / (label + '_report.json'))
        ids = [r['id'] for r in report['failures']]
        passed = row['returncode'] == expected and (required in ids if required else not ids)
        if required and 'nested' in label:
            passed = passed and any('task_switches' in r.get('path', '') for r in report['failures'])
        outcomes.append({'case': label, 'expected_exit': expected, 'required_failure_id': required,
                         'actual_failure_ids': ids, 'passed': passed, 'actual_run': row})
    old_result = shared.load(OUT / 'isolated_copy/tests/test_run_log.json')
    tree = {p.relative_to(skill_root).as_posix(): shared.sha(p)
            for p in sorted(skill_root.rglob('*')) if p.is_file()}
    all_ok = rows[0]['returncode'] == 0 and all(o['passed'] for o in outcomes) and all(original_test_unchanged.values()) and original_fixture_matches
    summary = {'schema': 'wrd-native-local-resource-revision-review-v1', 'b_job_id': 'B_revision_report_01',
         'status': 'LOCAL_RESOURCE_SCOPE_ACCEPTABLE_FOR_BOUNDED_TRIAL' if all_ok else 'HOLD_INDEPENDENT_RECHECK_FAILED',
         'skill_tree': tree, 'skill_sha256_tree': hashlib.sha256(json.dumps(tree, sort_keys=True, ensure_ascii=False).encode()).hexdigest(),
         'skill_root': str(skill_root), 'is_explicit_packaging_projection': args.skill_root is not None,
         'functional_view_files_byte_identical_to_actual_native_parent': all(
             shared.sha(skill_root / rel) == shared.sha(EP / 'workspace/outputs/skill' / rel) for rel in tree),
         'original_candidate_job_id': 'B_make_report_02', 'only_validator_resource_changed': all(
             shared.sha(p) == shared.sha(EP / 'workspace/outputs/skill' / p.relative_to(OLD / 'workspace/outputs/skill'))
             for p in (OLD / 'workspace/outputs/skill').rglob('*') if p.is_file() and p.name != 'validate_pack.py'),
         'original_test_code_sha_unchanged': original_test_unchanged, 'all_original_fixture_sha_unchanged': original_fixture_matches,
         'original_21_reproduction': {'run': rows[0], 'actual_log': old_result}, 'independent_new_cases': outcomes,
         'known_remaining_scope_limits': [
             'SKILL still says per-item human review before delivery; actual autonomous consumer behavior must be assessed.',
             'SKILL adds external-verification/Word-state notices broadly, including tasks not requesting Word; C source-only report must not be polluted.',
             'classify/ledger/JSON validation overhead may outweigh reuse benefit on these short writing tasks.',
             'Deterministic checks do not prove semantic faithfulness, universal validity, or positive business effect.'],
         'whole_SKILL_or_making_stage_positive_loss_approved': False,
         'same_version_actual_C_and_independent_Q_still_required': True,
         'fixed_image': shared.IMAGE, 'pure_tool_scorer_no_Agent_no_model': True,
         'original_resources_not_modified': True, 'new_model_calls': 0, 'training_started': False}
    shared.save(OUT / 'RESOURCE_REVIEW.json', summary)
    print(json.dumps({'status': summary['status'], 'original_suite_exit': rows[0]['returncode'],
                      'additional_passed': sum(o['passed'] for o in outcomes), 'additional_total': len(outcomes),
                      'tree_sha256': summary['skill_sha256_tree']}))


if __name__ == '__main__':
    main()
