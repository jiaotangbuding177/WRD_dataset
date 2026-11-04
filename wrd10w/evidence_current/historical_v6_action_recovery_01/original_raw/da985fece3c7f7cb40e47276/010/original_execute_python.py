import subprocess, json, os, sys, shutil

prog = os.path.abspath('outputs/candidate/scripts/run.py')
run_root = os.path.abspath('outputs/report_repair_tests')

# remove stray shared dir created by the flawed first batch (own intermediate artifact)
stray = os.path.join(run_root, 'outputs')
if os.path.isdir(stray): shutil.rmtree(stray)

cases = [('original_recovery', 'inputs/dev_request.json')]
for c in json.load(open('inputs/development_cases.json', encoding='utf-8')):
    cases.append((c['id'], c['request']))

results = []
for cid, req in cases:
    # original_recovery: relative outputs have no '../' -> root=<id>
    # dev cases: '../outputs/...' -> root=<id>/case_root so resolved paths land in <id>/outputs
    outroot = os.path.join(run_root, cid) if cid == 'original_recovery' else os.path.join(run_root, cid, 'case_root')
    os.makedirs(outroot, exist_ok=True)
    cmd = [sys.executable, prog, '--request', os.path.abspath(req), '--output-root', outroot]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace', cwd='.')
    meta = {'id': cid, 'request': os.path.abspath(req), 'command': cmd, 'exit_code': r.returncode,
            'stdout': r.stdout, 'stderr': r.stderr, 'output_root': outroot}
    with open(os.path.join(run_root, cid, 'run_meta.json'), 'w', encoding='utf-8') as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    results.append({'id': cid, 'exit_code': r.returncode})
print(json.dumps(results, ensure_ascii=False))
for cid in ['dev_01','dev_02','dev_03','dev_04','dev_05','dev_06']:
    print(cid, os.listdir(os.path.join(run_root, cid, 'outputs')))