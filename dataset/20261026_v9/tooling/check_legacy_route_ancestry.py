"""Recover exact old route-card producer prefixes without executing old code."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'output/20261026_wrd_dataset_v9/outcomes/LEGACY_ROUTE_ANCESTRY_QA.json'


def js(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def sha(raw):
    return hashlib.sha256(raw if isinstance(raw, bytes) else raw.encode()).hexdigest()


def pin(path):
    p = Path(path)
    raw = p.read_bytes()
    return {'path': str(p), 'sha256': sha(raw), 'bytes': len(raw)}


def main():
    protected = set()
    for path in (ROOT / 'benchmark').glob('*/contracts/evaluation.jsonl'):
        group = {json.loads(x).get('session_id') for x in path.read_text(encoding='utf-8-sig').split('\n') if x.strip()}
        if len(group) == 226:
            protected |= group
    assert len(protected) == 226
    observations = []
    for batch in ['batch_002', 'batch_003', 'batch_004', 'batch_009']:
        base = ROOT / 'output/20261021_workflow_library_parallel4_recovery1/route_reviews' / batch
        checked_path = base / 'checked_cards.json'
        checked = json.loads(checked_path.read_text(encoding='utf-8-sig'))
        receipt = checked['native_receipt']
        assert pin(receipt['path']) == receipt
        episode = Path(receipt['path']).parent
        event_path = episode / 'openclaw_transport/session_events.jsonl'
        messages = []
        sid = None
        for line_number, line in enumerate(event_path.read_text(encoding='utf-8-sig').split('\n'), 1):
            if not line.strip():
                continue
            event = json.loads(line)
            if event.get('type') == 'session':
                sid = event['id']
            if event.get('type') == 'message':
                messages.append((line_number, event['message']))
        original_input = json.loads((base / 'input.json').read_text(encoding='utf-8-sig'))
        previews = [preview for proposal in original_input['proposals'] for preview in proposal.get('previews', [])]
        protected_previews = [preview for preview in previews if preview.get('source_id') in protected]
        delivered = []
        compact_input_deliveries = []
        for index, (line_number, message) in enumerate(messages):
            if message.get('role') != 'toolResult':
                continue
            text = '\n'.join(b.get('text', '') for b in message.get('content', []) if isinstance(b, dict) and b.get('type') == 'text')
            try:
                delivered_json = json.loads(text)
            except ValueError:
                delivered_json = None
            if delivered_json == original_input:
                compact_input_deliveries.append({'message_index': index, 'source_event_line_1based': line_number,
                    'tool_call_id': message.get('toolCallId'), 'canonical_input_sha256': sha(js(original_input)),
                    'whole_original_input_JSON_actually_delivered': True})
            proofs = []
            for preview in protected_previews:
                matched = [req for req in preview.get('requests', []) if isinstance(req.get('text'), str) and req['text'] and
                    (req['text'] in text or json.dumps(req['text'], ensure_ascii=False)[1:-1] in text)]
                if preview['source_id'] in text and matched:
                    proofs.append({'source_id': preview['source_id'], 'actual_original_request_text_matches': [
                        {'message_id': req.get('message_id'), 'text_sha256': sha(req['text']), 'characters': len(req['text'])} for req in matched]})
            if proofs:
                delivered.append({'message_index': index, 'source_event_line_1based': line_number,
                    'tool_call_id': message.get('toolCallId'), 'delivered_text_sha256': sha(text),
                    'protected_preview_body_proofs': proofs})
        writes = []
        for index, (line_number, message) in enumerate(messages):
            if message.get('role') != 'assistant':
                continue
            for call in message.get('content') or []:
                if not isinstance(call, dict) or call.get('type') != 'toolCall' or call.get('name') != 'write':
                    continue
                args = call.get('arguments') or {}
                if str(args.get('path')) != '/workspace/outputs/cards.json':
                    continue
                cards = json.loads(args['content'])
                matched = []
                checked_card_views = [('/holds/' + str(i) + '/raw_card', held.get('raw_card')) for i, held in enumerate(checked.get('holds', []))]
                checked_card_views += [('/cards/' + str(i), {k: v for k, v in c.items() if k != 'candidate_gate'}) for i, c in enumerate(checked.get('cards', []))]
                for pointer, raw in checked_card_views:
                    if raw is not None and any(raw == c for c in cards.get('cards', [])):
                        matched.append({'card_id': raw['id'], 'raw_card_canonical_sha256': sha(js(raw)), 'original_checked_pointer': pointer})
                writes.append({'message_index': index, 'source_event_line_1based': line_number,
                    'tool_call_id': call.get('id'), 'output_path': args['path'], 'content_sha256': sha(args['content']),
                    'matched_checked_raw_cards': matched,
                    'protected_body_observation_before_write': any(x['message_index'] < index for x in delivered)})
        observations.append({'batch': batch, 'native_session_id': sid, 'recovery_episode_id': 'native_' + sid,
            'source_native': pin(event_path), 'checked_cards_source': pin(checked_path), 'native_receipt': receipt,
            'protected_preview_source_ids_in_input': sorted({x['source_id'] for x in protected_previews}),
            'whole_compact_input_deliveries': compact_input_deliveries,
            'actual_protected_body_deliveries': delivered, 'native_card_writes': writes,
            'conclusion': 'PROTECTED_ORIGINAL226_BODY_IN_ACTUAL_PRODUCER_PREFIX' if any(w['protected_body_observation_before_write'] for w in writes) else 'NOT_ESTABLISHED_BY_THIS_CHECK'})
    # Batch003 sees no direct protected preview but does see the complete
    # model-created route signatures from protected batch002. This is a pinned
    # deterministic projection, not a new unrelated semantic annotation.
    b2 = ROOT / 'output/20261021_workflow_library_parallel4_recovery1/route_reviews/batch_002/checked_cards.json'
    b3 = ROOT / 'output/20261021_workflow_library_parallel4_recovery1/route_reviews/batch_003/input.json'
    prior = json.loads(b2.read_text(encoding='utf-8-sig'))
    next_input = json.loads(b3.read_text(encoding='utf-8-sig'))
    projected = [{k: c[k] for k in ['id', 'name', 'route_signature']} for c in prior['cards']]
    assert projected == next_input['existing_routes']
    obs2 = next(x for x in observations if x['batch'] == 'batch_002')
    obs3 = next(x for x in observations if x['batch'] == 'batch_003')
    assert obs2['conclusion'].startswith('PROTECTED')
    assert obs3['whole_compact_input_deliveries']
    assert obs3['whole_compact_input_deliveries'][0]['message_index'] < obs3['native_card_writes'][0]['message_index']
    obs3['deterministic_protected_ancestor_projection'] = {
        'source': pin(b2), 'source_json_pointer': '/cards', 'target': pin(b3), 'target_json_pointer': '/existing_routes',
        'projection_fields': ['id', 'name', 'route_signature'], 'projection_equals_target_exactly': True,
        'projected_canonical_sha256': sha(js(projected)), 'upstream_protected_batch': 'batch_002'}
    obs3['conclusion'] = 'PROTECTED_ORIGINAL226_DERIVED_ROUTE_SIGNATURES_IN_ACTUAL_PRODUCER_PREFIX'
    legacy_makers = []
    for route in ['document-translation-route', 'ppt-deck-revision']:
        base = ROOT / 'output/20261021_workflow_library_v9/w' / route / 'r1'
        task_path = base / 'task.json'
        task = json.loads(task_path.read_text(encoding='utf-8-sig'))
        card_path = base / 'sources/route_card.json'
        card = json.loads(card_path.read_text(encoding='utf-8-sig'))
        stripped = {key: value for key, value in card.items() if key not in ('candidate_gate', 'merge_context')}
        assert sha(js(stripped)) == task['accepted_card_sha256']
        batch, number = ('batch_009', 'card_02') if route == 'document-translation-route' else ('batch_004', 'card_01')
        derived_path = ROOT / 'output/20261021_pipeline_infra_audit/route_recovery' / batch / number / 'derived_card.json'
        assert json.loads(derived_path.read_text(encoding='utf-8-sig')) == stripped
        assert task['merge_context'] == card['merge_context'] == json.loads((base / 'merge_context.json').read_text(encoding='utf-8-sig'))
        implementation = []
        for name, source in task['making_implementation_pins'].items():
            moved = Path(source['path'].replace('research\\pipelines\\', 'research\\archive\\workflow_legacy_20261023\\'))
            actual = pin(moved)
            assert actual['sha256'] == source['sha256'] and actual['bytes'] == source['bytes']
            implementation.append({'name': name, 'original_pin': source, 'actual_archived_source': actual})
        source_checks = []
        for source_id, source in task['source_pins'].items():
            assert pin(source['path']) == source
            source_checks.append({'source_id': source_id, 'original_pin': source, 'source_bytes_reverified': True})
        legacy_makers.append({'route_id': route, 'task_source': pin(task_path), 'card_source': pin(card_path),
            'derived_card_source': pin(derived_path), 'accepted_card_sha256_matches_stripped_card': True,
            'stripped_card_equals_original_derived_card': True, 'merge_context_mechanically_equal': True,
            'pinned_implementation_sources_recovered': implementation, 'selected_source_pins_reverified': source_checks,
            'upstream_native_batch': batch, 'clean_selected_sources_do_not_erase_protected_producer_prefix': True})
    result = {'schema_version': 'wrd-v9-legacy-route-producer-ancestry-QA-1.0', 'status': 'PASS',
        'created_at_utc': datetime.now(timezone.utc).isoformat(), 'producer_prefixes': observations,
        'legacy_maker_mechanical_joins': legacy_makers,
        'no_original_business_body_copied_in_this_receipt': True,
        'no_original_source_or_outcome_graph_modified': True, 'training_started': False, 'generated_code_executed': False}
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'status': 'PASS', 'protected_producer_batches': [x['batch'] for x in observations if x['conclusion'].startswith('PROTECTED')], 'output': str(OUT)}, ensure_ascii=False))


if __name__ == '__main__':
    main()
