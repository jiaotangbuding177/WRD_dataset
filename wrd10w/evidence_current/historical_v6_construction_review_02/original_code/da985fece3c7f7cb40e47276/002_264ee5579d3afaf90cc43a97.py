import json
for p in ['inputs/development_cases.json','inputs/dev_request.json']:
    print('='*20, p)
    print(open(p, encoding='utf-8').read())