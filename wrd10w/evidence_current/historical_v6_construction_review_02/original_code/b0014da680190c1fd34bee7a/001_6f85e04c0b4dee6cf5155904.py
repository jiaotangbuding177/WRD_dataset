import json, os, shutil

print('=== workspace tree ===')
for root, dirs, files in os.walk('.'):
    if '.git' in root: continue
    depth = root.count(os.sep)
    if depth > 3: 
        dirs[:] = []
        continue
    print(root, '->', files[:20])

print()
print('=== closure_feedback.json ===')
print(open('inputs/closure_feedback.json', encoding='utf-8').read())

print()
print('=== task_contract.json ===')
try:
    print(open('inputs/task_contract.json', encoding='utf-8').read()[:4000])
except Exception as e:
    print('ERR', e)

print()
print('=== dev_request.json ===')
try:
    print(open('inputs/dev_request.json', encoding='utf-8').read()[:3000])
except Exception as e:
    print('ERR', e)
