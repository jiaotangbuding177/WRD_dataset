import json
fb = json.load(open('inputs/validation_feedback.json', encoding='utf-8'))
diags = fb['development_case_diagnostics']
for d in diags:
    print('===', d['id'], 'passed:', d.get('passed'), 'exit:', d.get('exit_code'))
    for c in d.get('failed_or_unknown_checks', []):
        print(' check:', c['id'], 'pass=', c.get('pass'), 'status=', c.get('status'), 'critical=', c.get('critical'))
        ev = c.get('evidence')
        if ev: print('   evidence:', json.dumps(ev, ensure_ascii=False)[:600])
    se = d.get('stderr')
    if se: print(' stderr:', se[:300])
print()
print('=== learning evidence review (full) ===')
print(json.dumps(fb['previous_validation'].get('learning_evidence_review'), ensure_ascii=False, indent=1)[:6000])
