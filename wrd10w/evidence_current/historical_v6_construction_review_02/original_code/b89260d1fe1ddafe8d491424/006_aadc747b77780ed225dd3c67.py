import json
fb = json.load(open('inputs/validation_feedback.json', encoding='utf-8'))
diag = fb['development_case_diagnostics']
for d in diag:
    print('=== id:', d.get('id'), 'passed:', d.get('passed'))
    for k, v in d.items():
        if k in ('id', 'passed'): continue
        s = json.dumps(v, ensure_ascii=False)
        if len(s) > 1600: s = s[:1600] + ' ...TRUNC'
        print(' ', k, '=', s)
