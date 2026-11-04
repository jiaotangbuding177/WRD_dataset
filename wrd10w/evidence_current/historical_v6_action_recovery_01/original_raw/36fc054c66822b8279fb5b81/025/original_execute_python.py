import json
conv = json.load(open('inputs/conversation.json', encoding='utf-8'))
# find message ids of interest
msgs = conv['messages']
for i, m in enumerate(msgs):
    mid = m.get('id') or m.get('message_id')
    if mid in ('conv_b5e6f3d3bab9:23a61c50', 'conv_b5e6f3d3bab9:9619dde6'):
        print('index', i, 'id', mid, 'role', m.get('role'))
        print(repr(m.get('content')))
        print('---')
print(json.dumps(list(conv.keys()), ensure_ascii=False))
print('CASES FILE:')