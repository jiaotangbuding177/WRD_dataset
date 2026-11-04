import json, subprocess, sys
from pathlib import Path

run_py = Path('outputs/candidate/scripts/run.py').resolve()
cases = json.load(open('inputs/development_cases.json', encoding='utf-8'))
results = {}
all_cases = [(c['id'], c['request'], c['valid_input']) for c in cases]
all_cases.append(('original_recovery', 'inputs/dev_request.json', True))
for cid, req, valid in all_cases:
    out_root = (Path('outputs/repair_tests') / cid).resolve()
    cmd = [sys.executable, '-X', 'utf8', '-B', str(run_py), '--request', req, '--output-root', str(out_root)]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', timeout=120)
    results[cid] = {'exit_code': r.returncode, 'valid_input': valid, 'stdout': r.stdout, 'stderr': r.stderr}
    ok = (r.returncode == 0) == valid
    print(f"{cid}: exit={r.returncode} valid={valid} {'OK' if ok else 'MISMATCH'}")
Path('work/raw_run_results.json').write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8')

# dev_06 table evidence
s = json.loads(results['dev_06']['stdout'])
for c in s['checks']:
    if c['name'] == 'types_and_tables_preserved':
        print('dev_06 tables check:', c['status'], c['evidence'][:160])
print('dev_06 totals:', s['totals'])
