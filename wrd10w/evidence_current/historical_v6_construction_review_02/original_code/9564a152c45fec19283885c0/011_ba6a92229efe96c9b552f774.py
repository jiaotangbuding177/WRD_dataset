import subprocess, sys, json
cmd = [sys.executable, 'outputs/candidate/scripts/run.py', '--request', 'inputs/dev_request.json', '--output-root', 'outputs/development_delivery']
r = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', cwd='.')
print('exit:', r.returncode)
print('--- stdout ---')
print(r.stdout)
print('--- stderr ---')
print(r.stderr)