import json
fb = json.load(open('inputs/validation_feedback.json', encoding='utf-8'))
print('top keys:', list(fb.keys()))
pv = fb['previous_validation']
print('pv keys:', list(pv.keys()))
for k in pv:
    v = pv[k]
    if isinstance(v, (str, int, bool, float)) or v is None:
        print(k, '=', v)
    elif isinstance(v, list):
        print(k, ': list of', len(v))
    elif isinstance(v, dict):
        print(k, ': dict keys', list(v.keys()))
# look for failure summaries
for k in fb:
    if k != 'previous_validation':
        v = fb[k]
        s = json.dumps(v, ensure_ascii=False)
        print('===', k, len(s))
        print(s[:3000])
