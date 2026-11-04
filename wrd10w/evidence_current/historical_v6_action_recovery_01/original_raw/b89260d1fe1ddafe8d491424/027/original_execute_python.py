import json
res = json.load(open('work/raw_run_results.json', encoding='utf-8'))
print(res['dev_06']['stderr'])
print('--- stdout ---')
print(res['dev_06']['stdout'][:500])
