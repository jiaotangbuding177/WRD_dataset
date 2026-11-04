import json
d = json.load(open('inputs/conversation.json', encoding='utf-8'))
msgs = d['messages']
for m in msgs:
    print('='*10, m.get('id'), m.get('role'))
    c = m.get('content','')
    print(c[:1000])
    print()