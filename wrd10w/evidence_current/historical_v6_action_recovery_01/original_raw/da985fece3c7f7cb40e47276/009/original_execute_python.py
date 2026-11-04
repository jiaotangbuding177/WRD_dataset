import json, os
for cid in ['dev_01','dev_02','dev_03']:
    p = f'inputs/development_cases/{cid}/request.json'
    print(cid, json.load(open(p, encoding='utf-8')))
import openpyxl
for cid in ['dev_03']:
    for f in [f'inputs/development_cases/{cid}/input.xlsx', f'outputs/report_repair_tests/{cid}/masked.xlsx']:
        if os.path.isfile(f):
            print(cid, f, openpyxl.load_workbook(f).sheetnames)
print(os.listdir('outputs/report_repair_tests/dev_01'))
print(os.listdir('outputs/report_repair_tests/dev_03'))