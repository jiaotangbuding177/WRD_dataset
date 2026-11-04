"""Independently verify native blind ordering, Q arithmetic and actual costs."""
from pathlib import Path
import gzip
import hashlib
import json
import math

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / 'output/20261027_wrd_main_v10/runtime_preflight'
EP = BASE / 'episodes/C_review_report_01'
OUT = BASE / 'quality/FIRST_CHAIN_INDEPENDENT_REVIEW'
RAW = ROOT / 'output/20261027_wrd_main_v10/native_records/C_review_report_01/raw_recovery/provider_responses.original.jsonl.gz'


def load(p):
    return json.loads(p.read_text(encoding='utf-8-sig'))


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def save(name, value):
    (OUT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def main():
    assert load(EP / 'result.json')['status'] == 'completed'
    OUT.mkdir(exist_ok=False)
    rows = [json.loads(line) for line in gzip.open(RAW, 'rt', encoding='utf-8')]
    qpath = EP / 'workspace/outputs/quality_blind.json'
    quality = load(qpath)
    writes, sensitive_reads, other_actions = [], [], []
    for index, row in enumerate(rows):
        for call in row['message'].get('tool_calls', []):
            tool = call['function']['name']
            fields = json.loads(call['function']['arguments'])
            record = {'response_index': index, 'call_id': row['call_id'], 'tool_call_id': call['id'],
                      'tool': tool, 'path': fields.get('path'), 'response_sha256': row['response_sha256']}
            if tool == 'write' and fields.get('path') == '/workspace/outputs/quality_blind.json':
                raw = fields['content'].encode('utf-8')
                artifact = OUT / ('original_quality_write_' + str(len(writes) + 1) + '.json')
                artifact.write_bytes(raw)
                record.update(content_sha256=hashlib.sha256(raw).hexdigest(), copied_original_write=str(artifact))
                writes.append(record)
            if tool == 'read' and (fields.get('path', '').endswith('/phase2_arm_costs.json') or '/candidate_skill/' in fields.get('path', '')):
                sensitive_reads.append(record)
            if tool == 'exec':
                command = fields.get('command', '')
                other_actions.append({**record, 'command_sha256_utf8': hashlib.sha256(command.encode()).hexdigest(),
                                      'mentions_sensitive_path': 'phase2_arm_costs' in command or 'candidate_skill' in command})
    native_rows = [json.loads(line) for line in (EP / 'openclaw_transport/all_session_events.jsonl').read_text(encoding='utf-8').splitlines()]
    tool_results = {}
    for native in native_rows:
        event = native['native_event']
        message = event.get('message', event.get('data', {}).get('message', {}))
        if message.get('role') == 'toolResult':
            tool_results[message.get('toolCallId')] = {'native_seq': native['seq'], 'isError': message.get('isError'),
                                                     'content_sha256_json': hashlib.sha256(json.dumps(message.get('content'), ensure_ascii=False, sort_keys=True).encode()).hexdigest()}
    assert writes, 'No actual native quality write'
    first = writes[0]
    ack = tool_results.get(first['tool_call_id'])
    first_sensitive = min(r['response_index'] for r in sensitive_reads)
    before = first['response_index'] < first_sensitive
    later_q_writes = [w for w in writes[1:] if w['response_index'] >= first_sensitive]
    early_exec_mentions = [r for r in other_actions if r['response_index'] <= first['response_index'] and r['mentions_sensitive_path']]
    # A requested read follows a request which includes the actual successful write ack.
    delivered_ack = []
    for row in rows:
        if row['call_id'] == sensitive_reads[0]['call_id']:
            delivered_ack = [m for m in row['native_messages'] if m.get('role') == 'tool' and m.get('tool_call_id') == first['tool_call_id']]
            break
    blind_verified = bool(before and ack and ack['isError'] is False and delivered_ack and not early_exec_mentions and not later_q_writes)
    save('BLIND_ORDER_AUDIT.json', {'schema': 'wrd-independent-original-native-blind-order-audit-v1',
        'status': 'PASS_SCOPED_ACTUAL_READ_ORDER' if blind_verified else 'BLINDING_UNPROVEN_OR_VIOLATED',
        'first_quality_write': first, 'quality_write_actual_native_tool_result': ack,
        'all_quality_writes': writes, 'first_phase2_or_candidate_read': sensitive_reads[0],
        'all_sensitive_reads': sensitive_reads, 'early_exec_sensitive_mentions': early_exec_mentions,
        'quality_success_ack_present_in_first_sensitive_request': bool(delivered_ack),
        'first_quality_write_bytes_equal_final_file': first['content_sha256'] == sha(qpath),
        'later_post_unblind_quality_rewrites': later_q_writes,
        'raw_ledger_sha256': sha(RAW), 'native_events_sha256': sha(EP / 'openclaw_transport/all_session_events.jsonl'),
        'this_does_not_certify_semantic_scores_or_human_gold': True})
    weights = {'D1': .3, 'D2': .2, 'D3': .2, 'D4': .2, 'D5': .1}
    calculations = {}
    for case in ('L', 'E'):
        for label in ('A', 'B'):
            item = quality['cases'][case][label]
            dimensions = {}
            for dim, weight in weights.items():
                scores = [r['score'] for r in item['dimensions'][dim]['items']]
                assert scores and all(score in (0, .5, 1) and not isinstance(score, bool) for score in scores)
                actual = sum(scores) / len(scores)
                given = item['dimensions'][dim]['score']
                dimensions[dim] = {'item_count': len(scores), 'recomputed': actual, 'recorded': given,
                                   'rounding_consistent': math.isclose(actual, given, abs_tol=.00006)}
            total = sum(dimensions[d]['recomputed'] * weights[d] for d in weights)
            calculations[case + '_' + label] = {'dimensions': dimensions, 'recomputed_Q_0_to_100': total * 100,
                'recorded_weighted_total': item['weighted_total'],
                'total_rounding_consistent': math.isclose(total, item['weighted_total'], abs_tol=.00006)}
    save('Q_ARITHMETIC_AUDIT.json', {'schema': 'wrd-independent-Q-arithmetic-only-audit-v1', 'calculations': calculations,
        'status': 'PASS_ARITHMETIC_ONLY' if all(v['total_rounding_consistent'] and all(d['rounding_consistent'] for d in v['dimensions'].values()) for v in calculations.values()) else 'MISMATCH',
        'semantic_correctness_not_certified': True, 'AI_silver_not_human_gold': True})
    episodes = []
    identities = set()
    known_input = known_output = unknown = 0
    for folder in sorted((BASE / 'episodes').iterdir()):
        if not (folder / 'dispatch.json').is_file():
            continue
        selected = folder / 'PASSIVE_USAGE_RECONCILIATION.json'
        if not selected.is_file():
            selected = folder / 'usage.json'
        if folder.name == 'B_make_report_01':
            selected = BASE / 'quality/B_INTERRUPTION_20261027/usage.partial.json'
        assert selected.is_file(), folder.name
        usage = load(selected)
        episodes.append({'job_id': folder.name, 'usage_path': str(selected), 'usage_sha256': sha(selected),
            'known_tokens': usage['known_total_tokens'], 'actual_request_identities': usage['known_model_calls'],
            'unknown_usage_calls': usage['unknown_usage_calls']})
        for request in usage['requests']:
            key = (request['pid'], request['request_id'])
            assert key not in identities, 'Paid request identity duplicated across phases'
            identities.add(key)
            known_input += request['input_tokens'] or 0
            known_output += request['output_tokens'] or 0
            unknown += not request['complete']
    save('ACTUAL_COST_RECONCILIATION.json', {'schema': 'wrd-first-chain-deduplicated-known-native-cost-v1',
        'physical_outer_dispatches': len(episodes), 'episodes': episodes, 'actual_request_identities': len(identities),
        'known_input_tokens': known_input, 'known_output_tokens': known_output,
        'known_total_tokens': known_input + known_output, 'unknown_usage_calls': unknown,
        'cash_cost': 'UNKNOWN_NOT_ZERO', 'Codex_AI_annotation_or_code_work_cost': 'UNKNOWN_NOT_ZERO',
        'CPU_energy': 'UNMEASURED_NOT_ZERO', 'training_started': False,
        'native_review_cost_included_after_terminal': True,
        'compatible_HTTP_cached_tool_continuations_not_counted_as_paid_model_calls': True,
        'qualified_retained_skills': 0, 'total_cost_per_qualified_skill': 'UNDEFINED'})
    save('SEMANTIC_ERRATA.json', {'schema': 'wrd-scoped-independent-C-decision-feedback-errata-v1',
        'original_files_preserved_unchanged': True,
        'not_full_semantic_review': True,
        'findings': [
            {'id': 'CURRENT_REVIEW_COST_NOT_IN_PRE_REVIEW_TOTAL', 'source': 'decision.json rationale[2] and final answer broad cumulative wording',
             'original_pre_review_known_tokens': 7367237, 'actual_current_review_known_tokens': 1293310,
             'correct_after_terminal_known_tokens': known_input + known_output,
             'explanation': '7367237 is a correct prior-stage subtotal including four trials, but not the current native review. Do not train claims that this number already includes current review. Current review cost was unavailable before its own terminal.'},
            {'id': 'COUNTING_CONVENTION_VS_REPORT_BOUNDARY', 'source': 'feedback.json same_version_concrete_issues F2',
             'explanation': 'Whole-delivery 624 including non-newline whitespace and 620 excluding whitespace both exceed600; report-body534 is a different assessed-text boundary. This case does not demonstrate threshold crossing caused by whitespace counting convention. A conservative default recommendation is an unverified policy suggestion.'},
            {'id': 'HONEST_SEMANTIC_LIMIT_NOT_AUTOMATIC_RESOURCE_BUG', 'source': 'feedback.json F3',
             'explanation': 'The deterministic tool explicitly delegates unverified evaluative statements to semantic review; lack of a reliable deterministic semantic guarantee is a declared scope limit. Strong-word scanning is an unvalidated proposal, not a proven fix.'},
            {'id': 'NOISE_MAGNITUDE_NOT_MEASURED', 'source': 'decision.json quality_evidence_uncalibrated note',
             'explanation': 'Q is exploratory and uncalibrated. Two-case score differences do not measure a noise distribution; do not claim the observed gap is statistically within a quantified noise scale.'} ],
        'STOP_supported_scope': 'This specific candidate increased actual calls/tokens on both tested writing cases, while qualities remain exploratory. Do not generalize STOP to all writing skills or all WRD resources.',
        'no_entire_review_or_reasoning_auto_positive_loss': True})
    print(json.dumps({'blind_order_verified': blind_verified, 'quality_writes': len(writes),
        'quality_arithmetic': 'see Q_ARITHMETIC_AUDIT.json',
        'outer': len(episodes), 'actual_request_identities': len(identities),
        'known_tokens': known_input + known_output, 'unknown_usage_calls': unknown}))


if __name__ == '__main__':
    main()
