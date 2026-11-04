import json
res = json.load(open('work/raw_run_results.json', encoding='utf-8'))
print(res['dev_01']['stderr'])
