"""Record root's scoped third review of C execution, R and authored STOP."""
import gzip
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'output/20261027_wrd_main_v10'
HERE = OUT / 'c_review_dataset_01/semantic_revision_02'
COMPILED = OUT / 'compiled/c_review_dataset_02'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def main():
    dest = HERE / 'ROOT_SEMANTIC_ADMISSION.json'
    assert not dest.exists(), 'preserve earlier root decisions'
    receipt = load(HERE / 'SOURCE_AND_ORIGINAL_ARTIFACT_RECEIPTS.json')
    for row in receipt['files']:
        path = Path(row['path'])
        assert path.is_file() and path.stat().st_size == row['bytes']
        assert digest(path) == row['sha256']
    assert receipt['split'] == 'train' and len(receipt['source_ids']) == 4
    assert receipt['original226_isolated'] and receipt['newH_isolated'] and receipt['static_dev_test_isolated']
    assert load(HERE / 'ROOT_COMPILED_QA.json')['status'] == 'PASS'
    report = load(COMPILED / 'COMPILATION_REPORT.json')
    records = []
    for shard in report['files']:
        path = COMPILED / shard['path']
        assert digest(path) == shard['sha256']
        with gzip.open(path, 'rt', encoding='utf-8') as handle:
            records.extend(json.loads(line) for line in handle)
    assert len(records) == 4 and sum(r['supervised_tokens'] for r in records) == 1458
    entries = []
    for row in records:
        meta = row['original_record_metadata']
        assert meta['root_main_admission'] is False and row['split'] == 'train'
        assert meta['loss_multiplier'] == 0.25
        if row['bank'] == 'new_real_state_cost_stop_02':
            state = load(HERE / 'NEW_AUTHORED_REAL_STATE_COST_STOP.input.json')
            output = load(HERE / 'NEW_AUTHORED_REAL_STATE_COST_STOP.output.json')
            assert output['assistant_final_decision']['decision'] == 'STOP'
            assert meta['same_condition_as_original_D'] is False
            assert meta['new_current_state_after_original_review_terminal'] is True
            assert not row['messages'][-1].get('tool_calls')
            scope = 'NEW_POST_TERMINAL_COST_STOP_NOT_ORIGINAL_D_OR_EXECUTED_TOOL'
        else:
            evidence = meta['evidence']
            for key in ('request', 'response'):
                assert digest(Path(evidence[key])) == evidence[key + '_sha256']
            scope = 'SCOPED_ORIGINAL_R_OR_FACT_FAITHFUL_EXECUTION_NOT_WHOLE_EPISODE'
        entries.append({'id': row['id'], 'bank': row['bank'],
                        'supervised_tokens': row['supervised_tokens'], 'scope': scope})
    proof = {
        'schema': 'wrd-v10-root-scoped-C-second-pass-semantic-admission',
        'status': 'ADMIT_LOCAL_C_PROCESS_AND_AUTHORED_COST_STOP',
        'reviewer': 'root_AI_review_after_two_AI_semantic_checks_not_human_gold',
        'admitted_under_design_revision': '5.0.40', 'change_id': 'ALG-20261027-04',
        'record_ids': [r['id'] for r in records], 'entries': entries,
        'compilation_report_sha256': digest(COMPILED / 'COMPILATION_REPORT.json'),
        'root_compiled_QA_sha256': digest(HERE / 'ROOT_COMPILED_QA.json'),
        'source_receipts_sha256': digest(HERE / 'SOURCE_AND_ORIGINAL_ARTIFACT_RECEIPTS.json'),
        'actual_source_references_rechecked': len(receipt['files']),
        'root_semantic_findings': [
            'Both complete actual write payloads were read against the original user requests; L preserves specified metrics and source attribution, E preserves five reasons and qualifications without claiming a uniquely best hire.',
            'Approved early review R was read directly; unsupported superlative criticism, allowed compression, literal metrics/coverage and readable delivery checks are supported by the then-visible prefix.',
            'Withdrawn 207 characters of overbroad qualifier-preservation claims remain zero loss; no original Q score is promoted to human gold.',
            'Authored STOP is a new post-terminal decision state with complete requests/deliveries and original AI-Q objects, explicit missed-qualifier correction, true costs and unknowns; its conclusion is bounded to this version/two cases.',
            'Pre-review 7367237 is not represented as including the current review; post-terminal known cost is 8660547 with one unknown usage and unknown cash/curation cost.',
            'High costs support not retaining this candidate under the stated workload-reduction objective; local writing/repair credit survives STOP and does not imply global optimality or rejection of all writing skills.',
        ],
        'origin_token_counts': {'original_native_R': 387, 'actual_native_write_A': 781,
                                'new_authored_R': 132, 'new_authored_decision_D': 158},
        'superseded_v1_must_not_be_added': True,
        'full_original_R_wrong_D_and_held_prefixes_preserved_audit_only': True,
        'candidate_root_main_false_is_historical_external_receipt_is_current_admission': True,
        'AI_curation_compute_cost': 'UNKNOWN_NOT_ZERO',
        'training_started': False, 'full_WRD_training_ready': False,
        'script_sha256': digest(Path(__file__)),
    }
    dest.write_text(json.dumps(proof, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'status': proof['status'], 'records': 4, 'supervised_tokens': 1458,
                      'source_checks': len(receipt['files']), 'training_started': False}))


if __name__ == '__main__':
    main()
