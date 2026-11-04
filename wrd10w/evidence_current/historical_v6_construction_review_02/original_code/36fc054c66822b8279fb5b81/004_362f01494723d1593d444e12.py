import json
fb = json.load(open('inputs/validation_feedback.json', encoding='utf-8'))
pv = fb['previous_validation']
# Summarize quality blocks concisely
for c in pv['development_cases']:
    q = c.get('quality') or {}
    print('===', c['id'], 'exit', c.get('exit_code'))
    print(json.dumps(q, ensure_ascii=False)[:2000])
    print()