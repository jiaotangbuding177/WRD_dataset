import subprocess, json, os, sys

prog = os.path.abspath('outputs/candidate/scripts/run.py')
run_root = os.path.abspath('outputs/report_repair_tests')
os.makedirs(run_root, exist_ok=True)

cases = [('original_recovery', 'inputs/dev_request.json')]
for c in json.load(open('inputs/development_cases.json', encoding='utf-8')):
    cases.append((c['id'], c['request']))
print('cases:', [c[0] for c in cases])

results = []
for cid, req in cases:
    outroot = os.path.join(run_root, cid) if cid == 'original_recovery' else os.path.join(run_root, cid, 'case_root')
    os.makedirs(outroot, exist_ok=True)
    cmd = [sys.executable, prog, '--request', os.path.abspath(req), '--output-root', outroot]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace', cwd='.')
    meta = {
        'id': cid,
        'request': os.path.abspath(req),
        'command': cmd,
        'exit_code': r.returncode,
        'stdout': r.stdout,
        'stderr': r.stderr,
        'output_root': outroot,
    }
    with open(os.path.join(run_root, cid, 'run_meta.json'), 'w', encoding='utf-8') as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    results.append({'id': cid, 'exit_code': r.returncode, 'stderr_head': r.stderr[:200]})
print(json.dumps(results, ensure_ascii=False, indent=1))