"""Post-episode independent resource audit in the same fixed image, no Agent."""
from pathlib import Path
import hashlib
import json
import shutil
import subprocess
import time

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / 'output/20261027_wrd_main_v10/runtime_preflight'
EP = BASE / 'episodes/B_make_report_02'
OUT = BASE / 'quality/B02_INDEPENDENT_RESOURCE_AUDIT'
IMAGE = 'sha256:97a0f55bec1ef293c15ddd5a17cc843050387bd2369dcf2fd388b1afd40810a2'


def load(p):
    return json.loads(p.read_text(encoding='utf-8-sig'))


def save(p, value):
    p.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def run(label, args):
    started = time.monotonic()
    command = ['docker', 'run', '--rm', '--network', 'none', '--memory', '1g', '--cpus', '1',
               '--mount', 'type=bind,source=' + str(OUT / 'isolated_copy') + ',target=/workspace/outputs',
               '--mount', 'type=bind,source=' + str(OUT / 'extra_fixtures') + ',target=/independent,readonly',
               '--entrypoint', 'python', IMAGE] + args
    result = subprocess.run(command, capture_output=True, timeout=90)
    (OUT / (label + '.stdout.log')).write_bytes(result.stdout)
    (OUT / (label + '.stderr.log')).write_bytes(result.stderr)
    return {'label': label, 'command': command, 'returncode': result.returncode,
            'seconds': time.monotonic() - started,
            'stdout_sha256': hashlib.sha256(result.stdout).hexdigest(),
            'stderr_sha256': hashlib.sha256(result.stderr).hexdigest()}


def main():
    assert load(EP / 'result.json')['status'] == 'completed'
    OUT.mkdir(exist_ok=False)
    copy = OUT / 'isolated_copy'
    copy.mkdir()
    for name in ('skill', 'tests'):
        original = EP / 'workspace/outputs' / name
        assert all(not p.is_symlink() for p in original.rglob('*'))
        shutil.copytree(original, copy / name)
    extra = OUT / 'extra_fixtures'
    extra.mkdir()
    sources = {'sources': [{'source_id': 'independent_synthetic', 'messages': [
        {'message_id': 'm1', 'content': '2025年实际培训100人；2026年计划培训100人。'}]}]}
    facts = []
    for fid, kind, year, quote in (
        ('F1', 'user_statement', '2025', '2025年实际培训100人'),
        ('F2', 'planned_goal', '2026', '2026年计划培训100人')):
        facts.append({'fact_id': fid, 'fact_type': kind, 'claim': quote, 'value': '100', 'unit': '人',
                      'subject': '培训人数', 'time': year, 'explicit_user': True, 'must_keep': True,
                      'evidence_refs': [{'source_id': 'independent_synthetic', 'message_id': 'm1', 'quote': quote}]})
    ledger = {'schema': 'wrd-fact-ledger-v1', 'ledger_id': 'independent_valid_temporal_coexistence',
              'facts': facts, 'derived_rules': [], '_note': 'New explicitly synthetic independent audit, not real enterprise evidence.'}
    draft = {'schema': 'wrd-draft-v1', 'draft_id': 'valid_two_years', 'document_kind': 'one_paragraph',
             'text': '2025年实际培训100人，2026年计划培训100人。',
             'fact_refs': [{'fact_id': 'F1', 'as_type': 'achieved_fact'}, {'fact_id': 'F2', 'as_type': 'planned_goal'}],
             'declared_numbers': [{'fact_id': f['fact_id'], 'value': '100', 'unit': '人', 'subject': '培训人数'} for f in facts],
             'word_delivery': {'target_provided': False, 'written': False}}
    save(extra / 'legal_sources.json', sources)
    save(extra / 'legal_ledger.json', ledger)
    save(extra / 'legal_draft.json', draft)
    rows = [run('maker_21_independent_reproduction', ['/workspace/outputs/tests/run_tests.py']),
            run('valid_actual_and_goal_same_value_different_year', ['/workspace/outputs/skill/scripts/validate_pack.py',
                'validate', '--ledger', '/independent/legal_ledger.json', '--draft', '/independent/legal_draft.json',
                '--sources', '/independent/legal_sources.json', '--report', '/workspace/outputs/independent_temporal_report.json'])]
    tree = {p.relative_to(EP / 'workspace/outputs/skill').as_posix(): sha(p)
            for p in sorted((EP / 'workspace/outputs/skill').rglob('*')) if p.is_file()}
    findings = {
        'schema': 'wrd-native-resource-independent-posthoc-audit-v1', 'b_job_id': 'B_make_report_02',
        'status': 'HOLD_KNOWN_VALID_INPUT_REJECTED_REPAIR_REQUIRED_BEFORE_C',
        'fixed_image': IMAGE, 'executed_by': 'pure_deterministic_posthoc_tool_scorer_no_Agent_no_model',
        'resource_original_not_modified': True, 'source_skill_tree': tree,
        'skill_sha256_tree': hashlib.sha256(json.dumps(tree, sort_keys=True, ensure_ascii=False).encode()).hexdigest(),
        'runs': rows, 'maker_reproduction': load(copy / 'tests/test_run_log.json'),
        'temporal_counterexample_report': load(copy / 'independent_temporal_report.json'),
        'counterexample_expected': 'Structural pass with honest semantic review: different-year actual and planned goal may legitimately share subject/value/unit. Both source quotes and draft wording preserve their distinct temporal and epistemic status.',
        'findings': [
            {'id': 'OVERSTRONG_TEMPORAL_CONFLICT', 'evidence': 'validate_pack.py conflict key ignores time, claim identity and relation; all differing fact_type values are hard-rejected for equal subject/value/unit.',
             'severity': 'actual_valid_input_false_rejection', 'positive_loss_for_this_rule': False},
            {'id': 'MUST_KEEP_R_DESIGN_NOT_CARRIED_INTO_CODE', 'evidence': 'Actual code rejects must_keep only for new_assumption, not planned_goal; normal n2 fixture already permits planned_goal+must_keep. Do not misreport the broader R design mistake as an actual code bug.',
             'severity': 'scoped_correction_to_reasoning_review'}],
        'full_semantic_or_business_reuse_quality_approved': False,
        'new_AI_or_native_model_calls': 0, 'training_started': False,
        'CPU_energy_cost': 'unmeasured_not_zero'}
    save(OUT / 'REVIEW.json', findings)
    print(json.dumps({'output': str(OUT), 'status': findings['status'],
                      'runs': [{k: row[k] for k in ('label', 'returncode', 'seconds')} for row in rows],
                      'rejection_ids': [f['id'] for f in findings['temporal_counterexample_report']['failures']]}))


if __name__ == '__main__':
    main()
