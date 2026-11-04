import json
c = open('inputs/task_contract.json', encoding='utf-8').read()
print(c[5700:])
print('===development_cases.json===')
print(open('inputs/development_cases.json', encoding='utf-8').read())
print('===dev_request.json===')
print(open('inputs/dev_request.json', encoding='utf-8').read())
for cid in ['dev_01','dev_03','invalid_missing_header','invalid_missing_sheet']:
    print('===', cid, '===')
    print(open(f'inputs/development_cases/{cid}/request.json', encoding='utf-8').read())
