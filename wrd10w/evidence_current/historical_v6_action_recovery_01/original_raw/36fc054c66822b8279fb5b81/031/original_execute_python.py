s = open('outputs/candidate/scripts/run.py', encoding='utf-8').read()
i = s.find('# 4)')
j = s.find('checks.append({\n        "name": "deliverable_hash_recorded"')
print(s[i:j+500])