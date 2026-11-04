import json
fb = json.load(open('inputs/validation_feedback.json', encoding='utf-8'))
for d in fb['development_case_diagnostics']:
    print('===', d.get('id'), 'passed:', d.get('passed'), 'exit:', d.get('exit_code'))
    for c in d.get('failed_or_unknown_checks', []):
        print('  CHECK:', json.dumps(c, ensure_ascii=False)[:1200])
print()
rev = fb['independent_public_content_review']
print('content review passed:', rev.get('passed'), 'ready:', rev.get('content_ready_for_freeze'))
print('keys:', list(rev.keys()))
