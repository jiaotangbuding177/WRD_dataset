import sys, json
import subprocess
def captured(item, capture_stderr=True, check_exit=True):
    child = "import sys;sys.stdout.write('synthetic stdout');sys.stderr.write('synthetic diagnostic');sys.exit("+str(item['actual_exit'])+")"
    completed = subprocess.run([sys.executable, '-c', child], capture_output=True, text=True, timeout=5)
    stderr = completed.stderr if capture_stderr else None
    exit_ok = completed.returncode == item['expected_exit'] if check_exit else True
    needle_found = stderr is not None and item['needle'] in stderr
    return {'exit_ok':exit_ok,'needle_found':needle_found,'stderr_saved':stderr is not None,'check_pass':exit_ok and needle_found}

def transform(item):
    return captured(item, capture_stderr=False)

if __name__ == "__main__":
    data = json.loads(sys.stdin.read())
    print(json.dumps([transform(x) for x in data], ensure_ascii=False, sort_keys=True))
