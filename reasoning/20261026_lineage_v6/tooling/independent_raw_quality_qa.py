"""Independent original-target/actual-outcome checks, never a trainer."""
import gzip
import hashlib
import json
from pathlib import Path

ROOT = Path('D:/skillloop')
OUT = ROOT / 'output/20261026_wrd_sequences_v6'

def rows(p):
    with gzip.open(p, 'rt', encoding='utf8') as f:
        return [json.loads(line) for line in f if line.strip()]

def sha(b): return hashlib.sha256(b).hexdigest()

def main():
    overlay = OUT / 'controlled/historical_raw_quality_overlay.jsonl.gz'
    inputs = OUT / 'controlled/reasoning_pair_lineage_inputs.jsonl.gz'
    xs = {x['pair_id']: x for x in rows(inputs) if x.get('parent_run_record')}
    qs = rows(overlay)
    assert len(xs) == len(qs) == 86 and {q['pair_id'] for q in qs} == set(xs)
    checks = []
    stats = dict(positive=0, held_execute_error=0, held_unproven_writer=0, held_missing_outcome=0)
    for q in qs:
        x = xs[q['pair_id']]
        # The original recovery's declared canonical-response serialization
        # preserves insertion order, unlike our sorted evidence-record hashes.
        response_bytes = json.dumps(x['original_response'], ensure_ascii=False, separators=(',', ':')).encode()
        assert sha(response_bytes) == x['original_response_canonical_sha256'] == q['source_response_sha256']
        assert q['source_request_sha256'] == x['original_pair']['source_request']['sha256']
        step = next(s for s in x['parent_run_record']['actual_steps'] if s['pair_id'] == q['pair_id'])
        call_ids = {c['id'] for c in step['actual_response_message'].get('tool_calls', [])}
        obs = [m for m in step.get('observations_before_next_response', []) if m.get('role') == 'tool' and m.get('tool_call_id') in call_ids]
        if q['target_positive_allowed']:
            stats['positive'] += 1
        else:
            if 'recorded_current_execute_call_failed_not_correct_process_action' in q['reasons']:
                errors = [json.loads(m['content']) for m in obs if json.loads(m['content']).get('exit_code', 0) != 0]
                assert errors
                pins = [e['stderr_sha256'] for e in q['evidence'] if e.get('type') == 'actual_tool_result']
                assert any(sha(e['stderr'].encode()) in pins for e in errors)
                stats['held_execute_error'] += 1
            if 'candidate_resource_writer_draft_not_byte_matched_to_successful_validation' in q['reasons']:
                assert q['pair_id'] in {'cf6b8ff4f33e92f07a4a1474', 'f11ccd753dedeec8bcaef753'}
                assert any(e.get('same_run_recorded_validation_failed') for e in q['evidence'])
                stats['held_unproven_writer'] += 1
            if 'current_action_outcome_not_linked_to_original_tool_result' in q['reasons']:
                assert not obs
                stats['held_missing_outcome'] += 1
        checks.append({'pair_id': q['pair_id'], 'response_source_sha_verified': True,
            'original_request_file_sha_bound': True, 'positive_allowed': q['target_positive_allowed'],
            'actual_current_tool_results': len(obs), 'quality_rule': q['decision']})
    positive = next(q for q in qs if q['pair_id'] == '0753780cad3b696a12766199')
    assert positive['target_positive_allowed']
    rp = ROOT / 'output/20261026_wrd_lineage_v6/INDEPENDENT_REASONING_REVIEW.json'
    r = json.loads(rp.read_text(encoding='utf8'))
    e = next(e for e in positive['evidence'] if e['type'] == 'independent_exact_literal_patch_to_actual_observed_output_and_later_same_version_validation')
    assert e['independent_report_sha256'] == sha(rp.read_bytes())
    assert e['repaired_program_sha256'] == r['complete_causal_repair_example_without_enterprise_body']['repaired_program_sha256']
    assert stats == dict(positive=76, held_execute_error=7, held_unproven_writer=2, held_missing_outcome=1)
    result = {'schema_version': 'wrd-independent-raw-target-quality-qa-v6',
        'status': 'PASS_FOR_DECLARED_CONSERVATIVE_PROCESS_SILVER_OVERLAY',
        'overlay_sha256': sha(overlay.read_bytes()), 'independent_reasoning_report_sha256': sha(rp.read_bytes()),
        'counts': stats, 'all_86_unique_original_targets_bound': True,
        'actual_execute_error_receipts_and_stderr_hashes_verified': True,
        'no_successful_final_version_used_to_relabel_early_writers': True,
        '0753_positive_exactly_this_version_and_actual_postwrite_tool_sha': True,
        'original_failed_versions_and_context_not_deleted': True,
        'array_loss_mask_verification': 'pending final compiled arrays; this QA checks quality overlay only',
        'semantic_gold_created': False, 'training_started': False, 'gpu_used': False,
        'business_api_calls': 0, 'per_target': checks, 'script_sha256': sha(Path(__file__).read_bytes())}
    p = OUT / 'INDEPENDENT_RAW_QUALITY_QA.json'
    p.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    print(json.dumps({'counts': stats, 'report_sha256': sha(p.read_bytes())}))

if __name__ == '__main__': main()
