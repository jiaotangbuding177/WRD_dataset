import json
fb = json.load(open('inputs/validation_feedback.json', encoding='utf-8'))
print(list(fb.keys()))
# everything except previous_validation
for k,v in fb.items():
    if k == 'previous_validation': continue
    print('='*20, k)
    print(json.dumps(v, ensure_ascii=False, indent=1))
