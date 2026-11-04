import json, os, hashlib
rep = json.load(open('outputs/development_delivery/dev_outputs/masking_report.json', encoding='utf-8'))
print('report keys:', sorted(rep.keys()))
print('schema:', rep['schema_version'], '| totals:', rep['totals'])
print('sheets[0].columns:', rep['sheets'][0]['columns'])
# 报告不含原值检查：扫描报告文本中不应出现的dev输入原值
txt = json.dumps(rep, ensure_ascii=False)
import openpyxl
wi = openpyxl.load_workbook('inputs/dev_input.xlsx')
leak = 0
for row in wi['待脱敏记录'].iter_rows(min_row=2):
    for c in row:
        if isinstance(c.value, str) and len(c.value) > 4 and c.value in txt:
            leak += 1
print('报告中原值泄露检查: 泄露数 =', leak)
print('candidate files:', [os.path.join(dp, f).replace('outputs/candidate/','') for dp,_,fs in os.walk('outputs/candidate') for f in fs])
for f in ['outputs/candidate/scripts/run.py','outputs/candidate/README.md','outputs/candidate/workflow_spec.json']:
    h = hashlib.sha256(open(f,'rb').read()).hexdigest()
    print(f, h[:16], os.path.getsize(f))