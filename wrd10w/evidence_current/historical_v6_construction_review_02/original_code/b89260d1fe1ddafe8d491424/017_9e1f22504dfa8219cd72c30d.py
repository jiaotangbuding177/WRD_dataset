import json
spec = json.load(open('inputs/previous_candidate/workflow_spec.json', encoding='utf-8'))
print('top keys:', list(spec.keys()))
print(json.dumps({k: v for k, v in spec.items() if k not in ('nodes','resources')}, ensure_ascii=False, indent=1)[:1200])
for n in spec['nodes']:
    print('--- node', n.get('node_id'))
    s = json.dumps(n, ensure_ascii=False)
    print(s[:1400])
print('RESOURCES:', json.dumps(spec.get('resources'), ensure_ascii=False)[:1000])
