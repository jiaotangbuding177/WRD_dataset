import json
d = json.load(open('inputs/conversation.json', encoding='utf-8'))
print(type(d))
if isinstance(d, dict):
    print(list(d.keys()))
elif isinstance(d, list):
    print('len', len(d))
    print(json.dumps(d[0], ensure_ascii=False)[:1500])