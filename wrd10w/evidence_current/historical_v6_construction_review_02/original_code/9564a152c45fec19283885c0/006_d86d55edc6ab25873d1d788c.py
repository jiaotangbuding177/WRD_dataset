import json
print(json.dumps(json.load(open('inputs/task_contract.json', encoding='utf-8')), ensure_ascii=False, indent=1))