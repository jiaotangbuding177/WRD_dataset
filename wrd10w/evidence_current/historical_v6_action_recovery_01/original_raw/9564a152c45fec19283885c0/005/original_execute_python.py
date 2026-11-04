import json
print(json.dumps(json.load(open('inputs/material_identity.json', encoding='utf-8')), ensure_ascii=False, indent=1))
print('='*30)
print(json.dumps(json.load(open('inputs/dev_request.json', encoding='utf-8')), ensure_ascii=False, indent=1))