import json
tc = json.load(open('inputs/task_contract.json', encoding='utf-8'))
s = json.dumps(tc, ensure_ascii=False, indent=1)
print(len(s))
open('work_tc.txt','w',encoding='utf-8').write(s)
print(s[:4000])