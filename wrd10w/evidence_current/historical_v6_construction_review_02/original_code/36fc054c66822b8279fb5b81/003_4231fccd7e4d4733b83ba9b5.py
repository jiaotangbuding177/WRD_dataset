import json
fb = json.load(open('inputs/validation_feedback.json', encoding='utf-8'))
pv = fb['previous_validation']
print('--- development_cases ---')
for c in pv['development_cases']:
    print(json.dumps(c, ensure_ascii=False, indent=1)[:1500])
    print('...')