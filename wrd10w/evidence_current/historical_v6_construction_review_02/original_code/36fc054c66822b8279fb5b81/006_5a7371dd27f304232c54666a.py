import json
fb = json.load(open('inputs/validation_feedback.json', encoding='utf-8'))
diags = fb['development_case_diagnostics']
print('ids:', [d['id'] for d in diags])
for d in diags:
    print('===', d['id'], 'passed:', d.get('passed'), 'exit:', d.get('exit_code'))
    for c in d.get('failed_or_unknown_checks', []):
        print(' check:', c['id'], c['name'], 'pass=', c.get('pass'), 'status=', c.get('status'), 'critical=', c.get('critical'))
        ev = c.get('evidence')
        if ev: print('   evidence:', json.dumps(ev, ensure_ascii=False)[:800])
    se = d.get('stderr')
    if se: print(' stderr:', se[:500])
