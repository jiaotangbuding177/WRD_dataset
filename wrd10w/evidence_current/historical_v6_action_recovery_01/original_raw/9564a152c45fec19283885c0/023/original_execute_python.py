import openpyxl, json
inp = openpyxl.load_workbook('inputs/dev_input.xlsx')
out = openpyxl.load_workbook('outputs/development_delivery/dev_outputs/masked.xlsx')
req = json.load(open('inputs/dev_request.json', encoding='utf-8'))
ws_in, ws_out = inp['待脱敏记录'], out['待脱敏记录']
# 独立复核：按请求的表头/区间自行推导预期掩码，与输出比对（不复用run.py代码）
headers = {}
for c in ws_in[1]:
    if isinstance(c.value, str): headers[c.value] = c.column
m = req['masking']
bad = 0; checked = 0
for col_name in req['worksheets'][0]['columns']:
    col = headers[col_name]
    for r in range(2, 18):
        v = ws_in.cell(row=r, column=col).value
        exp = v if v is None or (isinstance(v,str) and len(v) <= m['prefix_chars']+m['suffix_chars']) else v[:m['prefix_chars']] + m['replacement'] + (v[-m['suffix_chars']] and v[-m['suffix_chars']:] or '')
        got = ws_out.cell(row=r, column=col).value
        checked += 1
        if got != exp:
            bad += 1; print('MISMATCH', col_name, r, repr(got), 'exp', repr(exp))
# 抽样展示（脱敏后值，非原值）
print('样例 A3:', ws_out['A3'].value, '| B2(短名):', repr(ws_out['B2'].value), '| B4:', ws_out['B4'].value)
# 非目标复核：G列与材料身份sheet
for r in range(2,18):
    assert ws_out.cell(row=r, column=7).value == ws_in.cell(row=r, column=7).value, f'G{r} changed'
for row in inp['材料身份'].iter_rows():
    for c in row:
        assert out['材料身份'][c.coordinate].value == c.value, c.coordinate
print('独立复核:', 'PASS' if bad==0 else f'FAIL({bad})', '| 目标单元格数', checked, '| G列与材料身份sheet未改动')