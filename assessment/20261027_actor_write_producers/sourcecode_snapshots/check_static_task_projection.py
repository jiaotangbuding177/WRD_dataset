"""Check that literal provenance recovery never runs unknown original code."""
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SOURCE = Path(__file__).with_name('static_task_dump_projection.py')
spec = importlib.util.spec_from_file_location('projection', SOURCE)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
program = '''python3 <<'EOF'
import json
a=read_unavailable_resource()
p="literal prompt"
cases=[{"id":"c1","prompt":p,"fixtures":[a]}]
dev={"cases":[{k:c[k] for k in ["id","prompt","fixtures"]} for c in cases]}
with open("/not/executed/development_tasks.json","w") as out:
 json.dump(dev,out)
EOF
'''
result = module.project(program)
assert len(result) == 1 and result[0]['cases'][0]['prompt'] == 'literal prompt'
dead = '''python3 <<'EOF'
import json
def dead():
 json.dump({"cases":[{"prompt":"dead"}]},None)
EOF
'''
assert module.project(dead) == []
conditional = '''python3 <<'EOF'
import json
if False:
 json.dump({"prompt":"dead"},None)
EOF
'''
assert module.project(conditional) == []
checks = {'literal_prompt_through_dict_list_comprehension_and_with_dump': 'PASS',
          'unknown_resource_function_is_not_executed': 'PASS',
          'uninvoked_function_is_not_a_dump_witness': 'PASS',
          'conditional_body_is_not_a_dump_witness': 'PASS'}
out = ROOT / 'output/20261027_wrd_main_v10/execution_rescue_01/STATIC_PROJECTOR_QA.json'
out.write_text(json.dumps({'status': 'PASS', 'checks': checks,
    'programs_are_AST_input_strings_not_executed': True,
    'source_sha256': hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
    'checker_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    'no_model_or_training': True}, indent=2) + '\n', encoding='utf-8')
print(json.dumps(checks))
