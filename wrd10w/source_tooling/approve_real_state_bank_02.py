"""Record root's scoped second AI review after exact source/array checks.

This is a data-curation receipt, not human gold, model training or tool replay.
"""
import gzip
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'output/20261027_wrd_main_v10'
HERE = OUT / 'real_state_reconstruction_02'
COMPILED = OUT / 'compiled/real_state_repair_02'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def main():
    dest = HERE / 'ROOT_SEMANTIC_ADMISSION.json'
    assert not dest.exists(), 'never overwrite a root admission receipt'
    receipts = load(HERE / 'SOURCE_RECEIPTS.json')
    source_checks = 0
    for row in receipts['files']:
        source = Path(row['path'])
        archived = HERE / row['archive_object']
        assert archived.resolve().is_relative_to(HERE.resolve())
        assert source.is_file() and archived.is_file()
        assert digest(source) == digest(archived) == row['sha256']
        assert source.stat().st_size == archived.stat().st_size == row['bytes']
        source_checks += 1
    data = HERE / 'real_state_tasks.jsonl.gz'
    with gzip.open(data, 'rt', encoding='utf-8') as handle:
        records = [json.loads(line) for line in handle]
    assert len(records) == 3 and receipts['split'] == 'train'
    assert load(HERE / 'ROOT_COMPILED_QA.json')['status'] == 'PASS'
    exact = load(OUT / 'real_state_reconstruction_01/EXACT_ACTION_VERSION_CHECK.json')
    assert exact['old_sha256'] == '6a1e951540750ded9fb1f8b688efe25e065352184f07e28c938081159473433a'
    assert exact['new_sha256'] == '86336921615cb2d15ae7c7c531fa81a457ea201e353223e79de4900445b59f58'
    assert all(item['occurrences_in_original'] == 1 for item in exact['edits'])
    assert exact['pre_edit_has_required_guard'] and exact['post_edit_preserves_required_guard']
    entries = []
    owners = set()
    for record in records:
        assert record['annotation_provenance'] == 'NEW_AUTHORED_REAL_STATE_REVALIDATED_ACTION'
        assert record['is_original_native_request_identical'] is False
        assert record['is_full_autonomous_execution_demonstration'] is False
        assert record['loss_multiplier'] == 0.5
        assert record['source_ids'] == receipts['source_ids']
        assert record['source_group_id'] == receipts['source_group_id']
        assert record['message_loss_mask'] == [0, 0, 1]
        user = record['messages'][1]['content']
        for marker in ('NEW_AUTHORED_STATE_TASK', 'NEW_AI_SILVER_AUTHOR', 'request.raw.json'):
            assert marker not in user
        target = record['messages'][2]
        assert len(target['tool_calls']) == 1 and target['reasoning_content']
        call = target['tool_calls'][0]
        owner = record['target_owner']
        assert owner['tool_call_id'] == call['id'] and owner['exposure_owner_id'] not in owners
        owners.add(owner['exposure_owner_id'])
        assert hashlib.sha256(call['function']['arguments'].encode()).hexdigest() == owner['exact_function_arguments_sha256_utf8']
        if call['function']['name'] == 'edit':
            for patch in json.loads(call['function']['arguments'])['edits']:
                assert patch['newText'] not in user, 'future_patch_answer_in_input'
        entries.append({'id': record['id'], 'tool_call_id': call['id'],
                        'exposure_owner_id': owner['exposure_owner_id'],
                        'scope': 'REVALIDATED_LOCAL_REPRODUCE_REPAIR_RETEST_NOT_RETENTION_OR_GLOBAL_OPTIMALITY'})
    report = {
        'schema': 'wrd-v10-root-scoped-second-ai-semantic-admission',
        'status': 'ADMIT_LOCAL_REAL_STATE_REPAIR_WITH_EXPLICIT_NEW_AUTHOR',
        'reviewer': 'root_AI_second_review_not_human_gold',
        'admitted_under_design_revision': '5.0.40',
        'change_id': 'ALG-20261027-04',
        'record_ids': [r['id'] for r in records], 'entries': entries,
        'input_file_sha256': digest(data),
        'compilation_report_sha256': digest(COMPILED / 'COMPILATION_REPORT.json'),
        'root_compiled_QA_sha256': digest(HERE / 'ROOT_COMPILED_QA.json'),
        'source_receipts_sha256': digest(HERE / 'SOURCE_RECEIPTS.json'),
        'actual_source_and_archived_references_rechecked': source_checks,
        'root_semantic_findings': [
            'Failures are actually delivered before the selected repair state; successful target action is independently revalidated under the earlier unchanged-file state.',
            'All edit selectors match the complete old file once and yield the actual independently tested new version; failed pathless edit is audit-only, not a leaked patch proposal.',
            'Reproduction and retest use the actual public CLI and existing exact fixtures; no future retest or 21+8 PASS is in the earlier model input.',
            'Wrong source code in oldText is a correct literal selector inside an edit, not a new correct implementation; newText and resulting version are checked separately.',
            'New short rationales, permissions and functional state are explicit new author data; raw original reasoning remains separately preserved.',
            'Local bug fixes do not approve skill utility, mandatory human review, overall package correctness or full autonomous behavior.',
        ],
        'only_functional_view_02_may_be_active': True,
        'view01_and_original_native_same_actions_exclusive': True,
        'original_root_main_admission_false_is_preserved_historical_candidate_metadata': True,
        'external_root_receipt_is_the_explicit_current_admission_overlay': True,
        'AI_curation_compute_cost': 'UNKNOWN_NOT_ZERO',
        'native_actions_reexecuted_by_this_review': 0,
        'training_started': False, 'full_WRD_training_ready': False,
        'script_sha256': digest(Path(__file__)),
    }
    dest.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'status': report['status'], 'records': len(entries),
                      'source_references': source_checks, 'training_started': False}))


if __name__ == '__main__':
    main()
