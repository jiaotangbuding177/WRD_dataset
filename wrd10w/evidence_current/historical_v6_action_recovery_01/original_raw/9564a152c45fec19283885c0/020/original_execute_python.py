import openpyxl
wi = openpyxl.load_workbook('inputs/dev_input.xlsx')
wo = openpyxl.load_workbook('outputs/development_delivery/dev_outputs/masked.xlsx')
a = wi['待脱敏记录']['A1'].font; b = wo['待脱敏记录']['A1'].font
print('dict(self) eq:', dict(a) == dict(b))
print('dict(a):', dict(a))
print('dict(b):', dict(b))
for el in a.__elements__:
    va, vb = getattr(a, el), getattr(b, el)
    if va != vb:
        print('ELEMENT DIFF:', el, repr(va), '->', repr(vb), '| types', type(va), type(vb))