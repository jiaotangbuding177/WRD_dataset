import json, subprocess, sys
from pathlib import Path

run_py = Path('outputs/candidate/scripts/run.py').resolve()
cases = json.load(open('inputs/development_cases.json', encoding='utf-8'))
results = {}
for case in cases:
    cid = case['id']
    out_root = (Path('outputs/repair_tests') / cid).resolve()
    req = case['request']  # workspace-relative
    cmd = [sys.executable, '-X', 'utf8', '-B', str(run_py), '--request', req, '--output-root', str(out_root)]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', timeout=120)
    results[cid] = {'exit_code': r.returncode, 'stdout': r.stdout, 'stderr': r.stderr}
    print(cid, 'exit', r.returncode, 'stderr:', (r.stderr or '')[:200].replace('\n', ' | '))

# original_recovery: inputs/dev_request.json + inputs/dev_input.xlsx
out_root = (Path('outputs/repair_tests/original_recovery')).resolve()
cmd = [sys.executable, '-X', 'utf8', '-B', str(run_py), '--request', 'inputs/dev_request.json', '--output-root', str(out_root)]
r = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', timeout=120)
results['original_recovery'] = {'exit_code': r.returncode, 'stdout': r.stdout, 'stderr': r.stderr}
print('original_recovery', 'exit', r.returncode, 'stderr:', (r.stderr or '')[:200].replace('\n', ' | '))

Path('work').mkdir(exist_ok=True)
Path('work/raw_run_results.json').write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8')
# show one valid stdout
print('--- sample stdout (dev_01) ---')
print(results['dev_01']['stdout'][:2500])
