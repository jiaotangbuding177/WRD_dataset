import json, os, shutil, hashlib

# 1. copies first
os.makedirs('outputs', exist_ok=True)
shutil.copytree('inputs/previous_candidate', 'outputs/candidate', dirs_exist_ok=True)
shutil.copy('inputs/previous_learning_evidence.json', 'outputs/previous_learning_evidence.json')
shutil.copy('inputs/previous_candidate_plan.json', 'outputs/previous_candidate_plan.json')
print('copied: outputs/candidate, evidence, plan')

fb = json.load(open('inputs/closure_feedback.json', encoding='utf-8'))
print()
print('=== closure_feedback tail (after dev_06) ===')
s = json.dumps(fb, ensure_ascii=False, indent=1)
print(s[5500:])

print()
print('=== previous_learning_evidence.json ===')
print(open('inputs/previous_learning_evidence.json', encoding='utf-8').read()[:3500])

print()
print('=== previous_candidate_plan.json ===')
print(open('inputs/previous_candidate_plan.json', encoding='utf-8').read()[:3500])

print()
print('=== dev_request.json ===')
print(open('inputs/dev_request.json', encoding='utf-8').read()[:2000])

print()
print('=== development_cases.json ===')
print(open('inputs/development_cases.json', encoding='utf-8').read()[:2500])

print()
print('=== task_contract.json ===')
print(open('inputs/task_contract.json', encoding='utf-8').read()[:3000])
