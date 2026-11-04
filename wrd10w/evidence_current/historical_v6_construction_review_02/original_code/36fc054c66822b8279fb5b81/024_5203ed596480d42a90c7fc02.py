import json
s = open('outputs/candidate/scripts/run.py', encoding='utf-8').read()
# find all checks.append blocks
import re
for m in re.finditer(r'checks\.append\(\{[\s\S]*?\}\)', s):
    print(m.group(0)[:400])
    print('---')