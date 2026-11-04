"""Reconcile closed native collection only; never count a live job as free."""
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'output/20261027_wrd_main_v10'


def load(p):
    return json.loads(Path(p).read_text(encoding='utf-8-sig'))


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    path = OUT / 'COST_ACCOUNTING_SCOPE.json'
    previous = load(path)
    ledger_path = OUT / 'runtime_preflight/quality/FIRST_CHAIN_INDEPENDENT_REVIEW/ACTUAL_COST_RECONCILIATION.json'
    ledger = load(ledger_path)
    pins = list(ledger['episodes'])
    for name in ('A_phase2_source_screen_01', 'B_phase2_cv_01', 'B_phase2_html_01', 'B_phase2_cv_revision_01'):
        usage_path = OUT / 'runtime_preflight/episodes' / name / 'usage.json'
        pins.append({'job_id': name, 'usage_path': str(usage_path), 'usage_sha256': sha(usage_path)})
    requests = {}
    details = []
    for ref in pins:
        p = Path(ref['usage_path'])
        assert sha(p) == ref['usage_sha256']
        usage = load(p)
        for request in usage['requests']:
            identity = (request['pid'], request['request_id'])
            assert identity not in requests, 'closed_scope_request_double_count'
            requests[identity] = request
        details.append({'job_id': ref['job_id'], 'usage_path': str(p), 'usage_sha256': sha(p),
                        'known_total_tokens': usage['known_total_tokens'],
                        'request_identities': len(usage['requests']),
                        'unknown_usage': usage['unknown_usage_calls']})
    known = sum((r.get('input_tokens') or 0) + (r.get('output_tokens') or 0) for r in requests.values())
    unknown = sum(not r['complete'] for r in requests.values())
    assert (len(pins), len(requests), known, unknown) == (14, 206, 16197610, 2)
    root_scope = OUT / 'runtime_preflight/jobs/ROOT_PHASE2_HTML_REV_AND_CV_C4_SCOPE.json'
    snapshot = {'as_of': 'CV_REVISION_CLOSED_BEFORE_HTML_REVISION_OUTCOME',
                'physical_outer_dispatches': 14, 'actual_native_sessions_including_probe_child': 15,
                'known_total_tokens': known, 'actual_request_identities': len(requests), 'unknown_usage_calls': unknown,
                'compatible_HTTP_records': 255, 'transport_complete_HTTP': 253,
                'supported_stop_tool_HTTP': 252, 'transport_complete_length_HTTP': 1, 'transport_partial_HTTP': 2,
                'original_explicit_R_unicode_characters': 384215,
                'HTML_vision_helper_5030_tokens_already_included_not_added_twice': True,
                'exact_closed_usage_files': details,
                'currently_authorized_scope_sha256': sha(root_scope),
                'later_authorized_or_live_HTML_revision_and_four_C_trials_excluded_pending_terminal_usage': True,
                'qualified_retained_skills': 0,
                'cash_cost': None, 'no_free_running_session_claim': True}
    previous['as_of'] = snapshot['as_of']
    previous['latest_closed_native_collection_snapshot'] = snapshot
    previous['qualified_retained_skills_in_latest_closed_scope'] = 0
    previous['cost_per_qualified_skill_status'] = 'UNDEFINED_ZERO_QUALIFIED_DENOMINATOR'
    path.write_text(json.dumps(previous, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: snapshot[k] for k in ('physical_outer_dispatches','actual_native_sessions_including_probe_child','known_total_tokens','actual_request_identities','unknown_usage_calls')}))


if __name__ == '__main__':
    main()
