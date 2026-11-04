p = 'logs/002.stdout.txt'
s = open(p, encoding='utf-8', errors='replace').read()
i = s.find('=== previous_candidate_plan.json ===')
print(s[i:])
