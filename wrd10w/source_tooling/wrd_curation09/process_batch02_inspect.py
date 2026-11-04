"""Bounded original-record inspection. Never executes a recorded tool command."""
import argparse, gzip, json
from pathlib import Path

BASE = Path('output/20261031_wrd_curation09/process')

def load(name):
    with gzip.open(BASE / name, 'rt', encoding='utf8') as stream:
        return [json.loads(line) for line in stream]

def txt(message):
    content = message.get('content', '')
    if isinstance(content, str):
        return content
    return '\n'.join(item.get('text', '') for item in content if item.get('type') == 'text')

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('episode')
    parser.add_argument('--limit', type=int, default=1800)
    parser.add_argument('--indices', default='')
    parser.add_argument('--all', action='store_true')
    parser.add_argument('--user-tail', type=int, default=2500)
    parser.add_argument('--start', type=int, default=0)
    parser.add_argument('--end', type=int, default=100000)
    parser.add_argument('--compact-feedback', action='store_true')
    args = parser.parse_args()
    contexts = {row['episode_id']: row for row in load('ORIGINAL_CONTEXTS_343.audit.jsonl.gz')}
    rows = load('OWNER1321_EXACT_CONTENT.audit.jsonl.gz')
    pending = {row['owner_id'] for row in load('OWNER1321_DISPOSITION09.jsonl.gz') if row['processing_disposition'] == 'HOLD_NEEDS_SEMANTIC_REVIEW'}
    context = contexts[args.episode]
    print('EPISODE', args.episode, 'ROUTE', context.get('route_id'))
    selected = set(map(int, args.indices.split(','))) if args.indices else None
    if selected:
        for index in sorted(selected):
            message = context['messages'][index]
            print('\nMESSAGE', index, message.get('role'), json.dumps(message, ensure_ascii=False)[:args.limit])
        return
    for index, message in enumerate(context['messages']):
        if message.get('role') == 'user' and args.user_tail:
            print('USER_END', index, txt(message)[-args.user_tail:])
    for row in sorted(rows, key=lambda row: row['source_message_index']):
        if row['episode_id'] != args.episode or (not args.all and row['owner_id'] not in pending):
            continue
        if not args.start <= row['source_message_index'] <= args.end:
            continue
        print('\nOWNER', row['owner_id'], 'IDX', row['source_message_index'], 'TYPE', row['literal_target_classification'])
        target = row['target_message_original']
        for item in target.get('content', []):
            print('TARGET', json.dumps(item, ensure_ascii=False)[:args.limit])
        for obs in row['immediate_original_tool_feedback']:
            message = obs['message']
            details = message.get('details') or {}
            value=txt(message)
            if args.compact_feedback:
                try:
                    parsed=json.loads(value)
                    if isinstance(parsed,dict): value=str(parsed.get('error') or parsed.get('text') or parsed)
                except (ValueError,TypeError): pass
                if '\n---\n' in value and '<<<EXTERNAL_UNTRUSTED_CONTENT' in value: value=value.split('\n---\n',1)[-1]
                if '<<<END_EXTERNAL_UNTRUSTED_CONTENT' in value: value=value.split('<<<END_EXTERNAL_UNTRUSTED_CONTENT')[0]
            print('FEEDBACK', obs['message_index'], {key: details[key] for key in ('status','exitCode','isError') if key in details}, value[:args.limit])

if __name__ == '__main__':
    main()
