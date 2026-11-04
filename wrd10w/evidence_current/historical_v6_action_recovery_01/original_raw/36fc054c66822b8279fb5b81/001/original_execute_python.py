import os, json
for p in ['inputs/validation_feedback.json','inputs/task_contract.json','inputs/development_cases.json','inputs/dev_request.json']:
    print('='*30, p)
    print(open(p, encoding='utf-8').read())