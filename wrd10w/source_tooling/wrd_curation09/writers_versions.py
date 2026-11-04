"""Reconstruct exact literal same-file versions without executing resources."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'output/20261031_wrd_curation09/writers'


def hs(s): return hashlib.sha256(s.encode('utf-8')).hexdigest()
def load(p): return json.loads(p.read_text(encoding='utf-8'))
def save(p, x):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(x, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def main():
    index = load(OUT / 'RECOVERY_INDEX.json')
    reservation_path = ROOT / 'output/20261031_wrd_curation09/holdout/holdout_reservation.json'
    reservation = load(reservation_path)
    reserved = set(reservation['reserved_source_ids'])
    results = []
    for row in index['rows']:
        owner = row['owner_id']
        directory = OUT / 'versions' / owner
        directory.mkdir(parents=True, exist_ok=False)
        timeline = load(OUT / 'episodes' / f"{row['episode_id']}.timeline.json")
        current = (OUT / row['code_ref']).read_text(encoding='utf-8')
        records = []
        native_state_uncertain = False
        extension = Path(row['code_ref']).suffix
        version_path = directory / f"{row['message_index']:03d}_original{extension}"
        version_path.write_bytes(current.encode('utf-8'))
        for event in timeline:
            if event['index'] <= row['message_index']:
                continue
            for call in event['calls']:
                args = call['arguments']
                receipts = [r for r in timeline if r['toolCallId'] == call['id']]
                ack = bool(receipts) and all(not r['isError'] for r in receipts)
                outcome = None
                before = current
                if call['name'] == 'write' and args.get('path') == row['native_path']:
                    outcome = 'EXACT_LATER_RECORDED_WRITE' if ack and 'Successfully wrote' in receipts[0]['text'] else 'WRITE_FAILED_OR_UNCONFIRMED'
                    if outcome.startswith('EXACT'):
                        current = args['content']
                        native_state_uncertain = False
                elif call['name'] == 'edit' and args.get('path') == row['native_path']:
                    after = current
                    exact = True
                    for edit in args.get('edits', []):
                        if after.count(edit['oldText']) != 1:
                            exact = False
                            break
                        after = after.replace(edit['oldText'], edit['newText'], 1)
                    if ack and 'Successfully replaced' in receipts[0]['text'] and exact:
                        current = after
                        outcome = 'EXACT_LITERAL_EDIT_WITH_NATIVE_ACK'
                    else:
                        outcome = 'FAILED_EDIT_ACK_RESOURCE_STATE_UNKNOWN' if not ack else 'EDIT_NOT_RECONSTRUCTED_NO_FALSE_VERSION'
                        native_state_uncertain = True
                elif call['name'] == 'apply_patch' and row['native_path'] in str(args):
                    outcome = 'PATCH_NEEDS_SEPARATE_EXACT_RECONSTRUCTION' if ack else 'FAILED_PATCH_ACK_RESOURCE_STATE_UNKNOWN'
                    native_state_uncertain = True
                if outcome:
                    record = {'message_index': event['index'], 'call_original': call,
                              'receipt_indices': [r['index'] for r in receipts], 'ack_not_error': ack,
                              'outcome': outcome, 'before_code_sha256': hs(before), 'after_code_sha256': hs(current),
                              'native_state_still_uncertain': native_state_uncertain,
                              'literal_transform_is_not_native_byte_identity_when_uncertain': native_state_uncertain}
                    if current != before:
                        p = directory / f"{event['index']:03d}_after{extension}"
                        p.write_bytes(current.encode('utf-8'))
                        record['after_code_ref'] = p.relative_to(OUT).as_posix()
                    records.append(record)
        result = {'owner_id': owner, 'source_ids': row['source_ids'],
                  'reserved_source_intersection': sorted(reserved.intersection(row['source_ids'])),
                  'reservation_sha256': hashlib.sha256(reservation_path.read_bytes()).hexdigest(),
                  'operations': records, 'latest_exact_code_sha256': hs(current),
                  'latest_exact_code_ref': (directory / ('latest_exact' + extension)).relative_to(OUT).as_posix(),
                  'latest_exact_means_tracked_literal_text_not_authenticated_native_state': native_state_uncertain,
                  'not_executed_by_this_recovery': True, 'training_admitted': False}
        (directory / ('latest_exact' + extension)).write_bytes(current.encode('utf-8'))
        save(directory / 'VERSION_CHAIN.json', result)
        results.append({k: v for k, v in result.items() if k != 'operations'} | {'operation_count': len(records), 'exact_changed_versions': sum(r['before_code_sha256'] != r['after_code_sha256'] for r in records)})
    save(OUT / 'VERSION_AND_RESERVATION_INDEX.json', {'rows': results,
         'owners': len(results), 'held_reserved_owners': sum(bool(r['reserved_source_intersection']) for r in results),
         'remaining_nonreserved_owners': sum(not r['reserved_source_intersection'] for r in results),
         'note': 'This index checks explicit source IDs; full component/ancestor closure remains mandatory before admission.'})
    print(json.dumps({'owners': len(results), 'reserved': sum(bool(r['reserved_source_intersection']) for r in results),
                      'exact_changed_versions': sum(r['exact_changed_versions'] for r in results)}))


if __name__ == '__main__': main()
