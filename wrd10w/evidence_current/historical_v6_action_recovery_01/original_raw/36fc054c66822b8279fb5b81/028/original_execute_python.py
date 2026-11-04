import os
print('resources exists:', os.path.isdir('resources'))
if os.path.isdir('resources'):
    for r,d,f in os.walk('resources'):
        print(r, d, f)
        break
print(os.access('resources' if os.path.isdir('resources') else '.', os.W_OK))
import json
conv = json.load(open('inputs/conversation.json', encoding='utf-8'))
c = conv['messages'][10]['content']
q = '- 🔒 `2026-07-31_脱敏对照表_内部使用.xlsx`（客户001→原名称、销售A→原姓名、1287条变更明细，**这份含原始信息，自己留档用，千万别外传**）'
print('contiguous:', q in c)
print('plan file head:')
print(open('outputs/candidate_plan.json', encoding='utf-8').read()[:1500])