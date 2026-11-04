"""Offline byte-preserving recovery of the 31 explicitly queued writer owners.

No recovered code is imported or executed. No semantic training admission occurs.
"""
from __future__ import annotations

import gzip
import hashlib
import json
from collections import Counter
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[3]
CORPUS = ROOT / 'output/20261030_wrd_gap08/corpus'
AUDIT = ROOT / 'output/20261031_wrd_readiness_plan/reviews/corpus_audit.json'
OUT = ROOT / 'output/20261031_wrd_curation09/writers'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def dump(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def rows(path):
    with gzip.open(path, 'rt', encoding='utf-8-sig') as f:
        for line in f:
            if line.strip():
                yield json.loads(line)


def text(message):
    body = message.get('content', '')
    if isinstance(body, str):
        return body
    return '\n'.join(x.get('text', '') for x in body if x.get('type') == 'text')


def calls(message):
    body = message.get('content', [])
    return [x for x in body if x.get('type') == 'toolCall'] if isinstance(body, list) else []


def main():
    assert not (OUT / 'RECOVERY_INDEX.json').exists(), 'preserve completed recovery'
    audit = json.loads(AUDIT.read_text(encoding='utf-8'))
    queue = audit['source_closed_full_writes']['remaining31_not_in_first6_or_current_writer_bank']
    want = set(queue['owner_ids'])
    assert len(want) == 31
    writers = {x['canonical_owner_id']: x for x in rows(CORPUS / 'RECOVERABLE_COMPLETE_NATIVE_WRITES.with_code.jsonl.gz') if x['canonical_owner_id'] in want}
    owners = {x['canonical_owner_id']: x for x in rows(CORPUS / 'CORPUS_OWNER_COVERAGE.native.jsonl.gz') if x['canonical_owner_id'] in want}
    eps = {x['episode_id'] for x in writers.values()}
    contexts = {x['episode_id']: x for x in rows(CORPUS / 'audit_inputs/native1843.contexts.original.jsonl.gz') if x['episode_id'] in eps}
    assert set(writers) == set(owners) == want and set(contexts) == eps
    index = []
    for episode, context in sorted(contexts.items()):
        dump(OUT / 'episodes' / f'{episode}.context.original.json', context)
        source = context['source_native']
        raw = Path(source['path']).read_bytes()
        assert len(raw) == source['bytes'] and sha(raw) == source['sha256']
        path = OUT / 'native' / f"{source['sha256']}.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            assert path.read_bytes() == raw
        else:
            path.write_bytes(raw)
        overview = []
        for i, message in enumerate(context['messages']):
            overview.append({'index': i, 'role': message.get('role'), 'text': text(message),
                             'calls': calls(message), 'toolCallId': message.get('toolCallId'),
                             'toolName': message.get('toolName'), 'isError': message.get('isError'),
                             'details': message.get('details'), 'responseId': message.get('responseId'),
                             'reasoning_blocks': [x for x in message.get('content', []) if isinstance(x, dict) and x.get('type') in {'thinking', 'reasoning'}] if isinstance(message.get('content'), list) else []})
        dump(OUT / 'episodes' / f'{episode}.timeline.json', overview)
    for owner_id in sorted(want):
        writer, owner = writers[owner_id], owners[owner_id]
        ctx = contexts[writer['episode_id']]
        message_index = writer['original_body_ref']['message_index']
        message = ctx['messages'][message_index]
        call = next(c for c in calls(message) if c['id'] == writer['original_tool_call_id'])
        assert call['name'] == 'write'
        assert call['arguments']['path'] == writer['native_path']
        code = writer['full_code']
        assert call['arguments']['content'] == code
        assert len(code) == writer['characters'] and sha(code.encode('utf-8')) == writer['original_content_utf8_SHA256']
        suffix = PurePosixPath(writer['native_path']).suffix or '.txt'
        code_path = OUT / 'code' / f'{owner_id}{suffix}'
        code_path.parent.mkdir(parents=True, exist_ok=True)
        code_path.write_bytes(code.encode('utf-8'))
        receipts = [{'index': i, 'message': m} for i, m in enumerate(ctx['messages']) if m.get('toolCallId') == call['id']]
        assert receipts, 'write receipt missing'
        packet = {'schema_version': 'wrd_curation09_writer_recovery_v1',
                  'canonical_owner_id': owner_id, 'writer_original': writer, 'owner_proof_original': owner,
                  'context_ref': f"episodes/{writer['episode_id']}.context.original.json",
                  'timeline_ref': f"episodes/{writer['episode_id']}.timeline.json",
                  'code_ref': code_path.relative_to(OUT).as_posix(), 'code_utf8_sha256': writer['original_content_utf8_SHA256'],
                  'original_target_message': message, 'original_write_ack': receipts,
                  'native_ref': f"native/{ctx['source_native']['sha256']}.jsonl",
                  'original_system_capture_status': ctx['system_capture_status'],
                  'original_prefix_equivalence_claimed': False,
                  'holdout_reservation_checked': False, 'semantic_training_admission': False,
                  'training_admitted': False, 'semantic_status': 'RECOVERED_UNREVIEWED',
                  'cost': {'new_business_teacher_actor_calls': 0, 'training_started': False,
                           'ai_cpu_curation_cost': 'UNKNOWN_NOT_ZERO'}}
        dump(OUT / 'packets' / f'{owner_id}.json', packet)
        index.append({'owner_id': owner_id, 'episode_id': writer['episode_id'], 'route_id': writer['route_id'],
                      'source_ids': writer['source_ids'], 'native_path': writer['native_path'],
                      'characters': len(code), 'code_sha256': sha(code.encode('utf-8')),
                      'code_ref': code_path.relative_to(OUT).as_posix(),
                      'packet_ref': f'packets/{owner_id}.json', 'message_index': message_index,
                      'native_r_blocks': owner['native_readable_R_blocks'],
                      'original_system_capture_status': ctx['system_capture_status'],
                      'called_tool_names': ctx['called_tool_names'], 'execution_condition': ctx['execution_condition']})
    dump(OUT / 'RECOVERY_INDEX.json', {'schema_version': 'wrd_curation09_writer_recovery_v1',
                                     'status': 'COMPLETE_ENTITY_RECOVERY_NOT_SEMANTIC_ADMISSION',
                                     'input_audit_sha256': sha(AUDIT.read_bytes()), 'owner_count': len(index),
                                     'episode_count': len(eps), 'source_count': len({s for x in index for s in x['source_ids']}),
                                     'total_code_characters': sum(x['characters'] for x in index),
                                     'route_counts': dict(Counter(x['route_id'] for x in index)), 'rows': index})
    print(json.dumps({'owners': len(index), 'episodes': len(eps), 'code_characters': sum(x['characters'] for x in index),
                      'original_r_blocks': sum(x['native_r_blocks'] for x in index), 'training_admitted': False}))


if __name__ == '__main__':
    main()
