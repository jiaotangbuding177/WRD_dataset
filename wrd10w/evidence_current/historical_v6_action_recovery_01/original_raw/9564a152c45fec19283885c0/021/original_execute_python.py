from copy import copy
import openpyxl
wi = openpyxl.load_workbook('inputs/dev_input.xlsx')
wo = openpyxl.load_workbook('outputs/development_delivery/dev_outputs/masked.xlsx')
c1 = wi['待脱敏记录']['A1']; c2 = wo['待脱敏记录']['A1']
print(type(c1.font), type(c2.font))
print('copy eq:', copy(c1.font) == copy(c2.font))
print('border copy eq:', copy(c1.border) == copy(c2.border))
print('fill copy eq:', copy(c1.fill) == copy(c2.fill))
print('alignment copy eq:', copy(c1.alignment) == copy(c2.alignment))
# 全簿验证
mismatch = 0; total = 0
for t in wi.sheetnames:
    for row in wi[t].iter_rows():
        for c in row:
            d = wo[t][c.coordinate]; total += 1
            if any(copy(getattr(c,a)) != copy(getattr(d,a)) for a in ['font','fill','border','alignment','number_format']):
                mismatch += 1
print('total', total, 'mismatch', mismatch)