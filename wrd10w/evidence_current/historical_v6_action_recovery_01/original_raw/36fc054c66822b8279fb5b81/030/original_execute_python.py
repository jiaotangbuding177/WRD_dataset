s = open('outputs/candidate/scripts/run.py', encoding='utf-8').read()
i = s.find('wb.save(out_path)')
j = s.find('checks.append({\n        "name": "non_target_values_preserved"')
print(s[i:j+700])