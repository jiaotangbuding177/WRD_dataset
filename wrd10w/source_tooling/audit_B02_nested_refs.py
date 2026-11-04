"""Check claimed all-nested-reference validation with malformed shapes."""
from pathlib import Path
import importlib.util
import json

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('b_resource_audit_shared', HERE / 'audit_B02_resources.py')
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


def main():
    ledger = audit.load(audit.OUT / 'extra_fixtures/legal_ledger.json')
    ledger['facts'] = ledger['facts'][:1]
    draft = audit.load(audit.OUT / 'extra_fixtures/legal_draft.json')
    draft['text'] = '2025年实际培训100人。'
    draft['fact_refs'] = draft['fact_refs'][:1]
    draft['declared_numbers'] = draft['declared_numbers'][:1]
    audit.save(audit.OUT / 'extra_fixtures/valid_single_draft.json', draft)
    rows = []
    for label, invalid in (('nested_refs_not_list', 'malformed-reference-string'),
                           ('nested_refs_non_object_item', [42])):
        changed = json.loads(json.dumps(ledger))
        changed['task_switches'] = [{'evidence_refs': invalid}]
        audit.save(audit.OUT / 'extra_fixtures' / (label + '.json'), changed)
        rows.append(audit.run(label, ['/workspace/outputs/skill/scripts/validate_pack.py', 'validate',
                    '--ledger', '/independent/' + label + '.json',
                    '--draft', '/independent/valid_single_draft.json', '--sources', '/independent/legal_sources.json',
                    '--report', '/workspace/outputs/' + label + '_report.json']))
    result = {'schema': 'wrd-independent-malformed-reference-probe-v1',
              'status': 'KNOWN_MALFORMED_NESTED_EVIDENCE_REFS_SILENTLY_SKIPPED',
              'business_or_model_calls': 0, 'original_candidate_unchanged': True,
              'runs': rows, 'reports': {r['label']: audit.load(audit.OUT / 'isolated_copy' / (r['label'] + '_report.json')) for r in rows},
              'scope': 'All-nested-reference structural contract should reject malformed evidence_refs or explicitly report unsupported input; current function iter_evidence_refs ignores non-list values and non-dict list entries.'}
    audit.save(audit.OUT / 'MALFORMED_NESTED_REFS_REVIEW.json', result)
    print(json.dumps({'status': result['status'], 'returncodes': [r['returncode'] for r in rows],
                      'failure_counts': [len(v['failures']) for v in result['reports'].values()]}))


if __name__ == '__main__':
    main()
