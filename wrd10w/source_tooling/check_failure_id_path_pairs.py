"""Read frozen real reports and bind a failure ID and path to one object.

The previous independent checker tested ID/path separately. This strengthening
does not rerun or rewrite resources, results, expected cases or old receipts.
"""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / 'output/20261027_wrd_main_v10/runtime_preflight/quality'
SPECS = {
    'nested_non_list': ('evidence_refs_not_list', 'ledger:$.task_switches[0].evidence_refs'),
    'nested_non_object': ('evidence_refs_item_not_object', 'ledger:$.task_switches[0].evidence_refs[0]'),
    'invalid_nested_quote': ('evidence_quote_not_contiguous', 'ledger:$.task_switches[0].evidence_refs[0]'),
}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    dest = BASE / 'B_REVISION_FAILURE_OBJECT_PAIRS_01'
    dest.mkdir(exist_ok=False)
    rows = []
    for parent in ('B_REVISION01_INDEPENDENT_RESOURCE_AUDIT', 'B_REVISION01_CLEAN_VIEW_RECHECK'):
        for case, (failure_id, exact_path) in SPECS.items():
            path = BASE / parent / 'isolated_copy' / (case + '_report.json')
            data = json.loads(path.read_text(encoding='utf-8-sig'))
            matches = [item for item in data['failures']
                       if item.get('id') == failure_id and item.get('path') == exact_path]
            assert data['verdict'] == 'STRUCTURAL_FAIL' and data['structural_pass'] is False
            assert len(matches) == 1, 'ID_AND_EXACT_PATH_MUST_BELONG_TO_THE_SAME_FAILURE'
            rows.append({'path': str(path), 'bytes': path.stat().st_size,
                         'sha256': digest(path), 'case': case,
                         'required_failure_id': failure_id, 'required_path': exact_path,
                         'same_object_matches': len(matches), 'actual_failure_objects': data['failures']})
    report = {
        'schema': 'wrd-v10-existing-failure-object-pair-audit-v1',
        'status': 'PASS_RECORDED_REPORTS_SUPPORT_PRECISE_LOCAL_NESTED_FAILURE_CLAIMS',
        'reports_rechecked': rows,
        'prior_checker_separate_ID_and_path_predicates_were_weaker': True,
        'does_not_retroactively_validate_wrong_top_level_path_in_Teacher_R': True,
        'old_resources_reports_and_receipts_unchanged': True,
        'new_Agent_model_or_resource_test_runs': 0,
        'qualified_retained_skills_added': 0,
        'training_started': False,
        'script_sha256': digest(Path(__file__)),
    }
    (dest / 'AUDIT.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'status': report['status'], 'actual_report_objects': len(rows), 'new_test_runs': 0}))


if __name__ == '__main__':
    main()
