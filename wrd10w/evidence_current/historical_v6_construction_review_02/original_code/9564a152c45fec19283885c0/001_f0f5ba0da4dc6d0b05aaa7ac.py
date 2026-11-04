import json, os
for f in ['inputs/conversation.json','inputs/material_identity.json','inputs/task_contract.json','inputs/dev_request.json']:
    p = os.path.join('.', f)
    print('='*20, f, 'exists:', os.path.exists(p), 'size:', os.path.getsize(p) if os.path.exists(p) else '-')
print(os.listdir('.'))
print(os.listdir('inputs'))