import json, subprocess, sys
from pathlib import Path

run_py = Path('outputs/candidate/scripts/run.py').resolve()
cases = json.load(open('inputs/development_cases.json', encoding='utf-8'))
results = {}
for case in cases:
    cid = case['id']
    out_root = (Path('outputs/repair_tests') / cid).resolve()
    cmd = [sys.executable, '-X', 'utf8', '-B', str(run_py), '--request', case['request'], '--output-root', str(out_root)]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', timeout=120)
    results[cid] = {'exit_code': r.returncode, 'stdout': r.stdout, 'stderr': r.stderr}
    print(cid, 'exit', r.returncode, ('stderr: ' + r.stderr[:150].replace('\n',' | ')) if r.stderr else '')

out_root = (Path('outputs/repair_tests/original_recovery')).resolve()
cmd = [sys.executable, '-X', 'utf8', '-B', str(run_py), '--request', 'inputs/dev_request.json', '--output-root', str(out_root)]
r = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', timeout=120)
results['original_recovery'] = {'exit_code': r.returncode, 'stdout': r.stdout, 'stderr': r.stderr}
print('original_recovery', 'exit', r.returncode, ('stderr: ' + r.stderr[:150]) if r.stderr else '')

Path('work/raw_run_results.json').write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8')
print('--- dev_01 stdout checks ---')
s = json.loads(results['dev_01']['stdout'])
print('status:', s['status'])
for c in s['checks']:
    print(' ', c['name'], c['status'], '| evidence[:80]:', c['evidence'][:80])
