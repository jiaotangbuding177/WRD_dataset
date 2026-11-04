import openpyxl
wb = openpyxl.load_workbook('inputs/development_cases/dev_06/input.xlsx')
print(openpyxl.__version__)
for name in wb.sheetnames:
    ws = wb[name]
    print(name, type(ws.tables), len(ws.tables))
    for k, v in ws.tables.items():
        print('  item:', repr(k), type(v), repr(v)[:80])
    for tname in ws.tables:
        t = ws.tables[tname]
        print('  get:', tname, type(t), getattr(t, 'ref', None), t.tableStyleInfo)
