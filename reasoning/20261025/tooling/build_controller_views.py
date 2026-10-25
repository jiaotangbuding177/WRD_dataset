"""Derive explicit, provenance-labelled phase decisions after observed reviews.

These are supplementary policy demonstrations, never fabricated teacher thought
or evidence that a high-level native tool interface already exists.
"""
import gzip
import hashlib
import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


def rows(p):
    with gzip.open(p, 'rt', encoding='utf-8-sig') as f:
        for line in f:
            if line.strip():
                yield json.loads(line)


def dumps(x):
    return json.dumps(x, ensure_ascii=False, separators=(',', ':'))


def main():
    out = ROOT / 'output/20261025_wrd_reasoning_recovery_v4/controller_views'
    out.mkdir(parents=True, exist_ok=False)
    repairs = {}
    for r in rows(ROOT / 'output/20261025_wrd_fullchain_reaudit/controlled_linkage/revision_pairs.extracted.jsonl.gz'):
        repairs.setdefault(r['review_episode_id'], []).append(r)
    sources = {
        'controlled': ROOT / 'output/20261025_wrd_training_dataset/bundle/canonical/native_episodes.jsonl.gz',
        'public': ROOT / 'output/20261025_wrd_fullchain_reaudit/public_projection/fullchain.native_sessions.jsonl.gz',
    }
    report = {}
    for scope, source in sources.items():
        counts = Counter()
        with gzip.open(out / (scope + '.controller_decisions.jsonl.gz'), 'wt', encoding='utf-8', newline='\n') as dst:
            for session_line, r in enumerate(rows(source), 1):
                if r.get('kind') != 'review':
                    continue
                messages = r['messages']
                for i, m in enumerate(messages):
                    if m.get('role') != 'assistant' or not isinstance(m.get('content'), list):
                        continue
                    for call in m['content']:
                        if call.get('type') != 'toolCall' or call.get('name') != 'write':
                            continue
                        arg = call.get('arguments', {})
                        if not isinstance(arg, dict) or not str(arg.get('path', '')).replace('\\', '/').endswith('/review.json'):
                            continue
                        raw = arg.get('content', '')
                        try:
                            review = json.loads(raw)
                        except (ValueError, TypeError):
                            counts['non_json_review_write'] += 1
                            continue
                        decision = review.get('decision')
                        if decision not in {'retain', 'revise', 'reject', 'defer'}:
                            continue
                        result_index = None
                        for j in range(i + 1, len(messages)):
                            follow = messages[j]
                            if follow.get('role') == 'toolResult' and follow.get('toolCallId') == call.get('id'):
                                if not follow.get('isError'):
                                    result_index = j
                                break
                        if result_index is None:
                            counts['write_not_confirmed_in_native_history'] += 1
                            continue
                        proof = repairs.get(r['episode_id'], [])
                        if decision == 'revise':
                            phase, action = 'B', 'revise_existing_resources_then_reproduce'
                            origin = 'actual_orchestrator_reference_plus_declared_policy' if proof else 'assistant_derived_policy_annotation'
                        elif decision == 'retain':
                            phase, action, origin = 'D', 'package_and_freeze_subject_to_evidence_checks', 'assistant_derived_policy_annotation'
                        elif decision == 'reject':
                            phase, action, origin = None, 'stop_current_candidate', 'assistant_derived_policy_annotation'
                        else:
                            phase, action, origin = None, 'defer_do_not_freeze_exact_next_tool_unknown', 'assistant_derived_policy_annotation'
                        target = {'review_decision': decision, 'next_phase': phase, 'high_level_action': action,
                                  'basis_from_observed_review': review.get('reason', ''),
                                  'execution_interface_verified': False}
                        uid = hashlib.sha256((r['episode_id'] + ':' + str(i) + ':' + str(call.get('id'))).encode()).hexdigest()[:24]
                        record = {
                            'schema_version': 'wrd-controller-demonstration-v4', 'id': uid,
                            'episode_id': r['episode_id'], 'parent_id': r['episode_id'],
                            'session_source': 'fullchain.native_sessions.jsonl.gz', 'session_line_1based': session_line,
                            'prompt_native_message_range_exclusive': [0, result_index + 1],
                            'instruction': '基于已经观察到的本轮审查结果，明确下一阶段或暂缓/停止。不得假定尚未执行的验证成功。',
                            'completion': [{'role': 'assistant', 'content': dumps(target)}],
                            'annotation_origin': origin, 'teacher_original_thinking': False,
                            'observed_report_source': {'message_index': i, 'tool_call_id': call.get('id'),
                                                       'confirmed_result_message_index': result_index,
                                                       'review_content_sha256': hashlib.sha256(str(raw).encode()).hexdigest()},
                            'explicit_later_revision_references': len(proof),
                            'future_revision_outputs_added_to_prompt': False,
                            'high_level_action_is_not_a_native_tool_call': True,
                            'human_gold': False, 'semantic_review': 'derived_rule_requires_review',
                            'training_admitted': False, 'publication_approved': scope == 'public',
                            'independent_new_task': False,
                        }
                        dst.write(dumps(record) + '\n')
                        counts['demonstrations'] += 1
                        counts['decision:' + decision] += 1
                        counts['origin:' + origin] += 1
        report[scope] = dict(counts)
    report.update(training_started=False, source_files_modified=False,
                  status='DERIVED_POLICY_VIEWS_NOT_AUTONOMOUS_AGENT_PROOF',
                  note='Only after confirmed review output; high-level native action compatibility remains unverified.')
    (out / 'CONTROLLER_VIEW_REPORT.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(dumps(report))


if __name__ == '__main__':
    main()
