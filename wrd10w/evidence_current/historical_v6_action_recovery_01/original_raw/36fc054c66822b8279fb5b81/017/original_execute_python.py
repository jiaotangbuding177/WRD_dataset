s = open('outputs/candidate/scripts/run.py', encoding='utf-8').read()
print('len', len(s))
open('work_runpy.txt','w',encoding='utf-8').write(s)
print(s[:6000])