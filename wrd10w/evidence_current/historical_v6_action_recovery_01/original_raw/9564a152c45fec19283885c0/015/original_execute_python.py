import openpyxl
from openpyxl.styles.fonts import Font
f1 = Font(name='X', sz=10); f2 = Font(name='X', sz=10)
print('fresh equal:', f1 == f2, 'f1 != f2:', f1 != f2)
wi = openpyxl.load_workbook('inputs/dev_input.xlsx')
wo = openpyxl.load_workbook('outputs/development_delivery/dev_outputs/masked.xlsx')
a = wi['待脱敏记录']['A1'].font; b = wo['待脱敏记录']['A1'].font
print('loaded: ==:', a==b, '!=:', a!=b)
from openpyxl.xml.functions import tostring
print('font xml equal:', tostring(a.to_tree()) == tostring(b.to_tree()))
sb1, sb2 = wi['待脱敏记录']['A1'].border, wo['待脱敏记录']['A1'].border
print('border xml equal:', tostring(sb1.to_tree()) == tostring(sb2.to_tree()))
print('font ==:', a == b)
print(dict(a.__dict__)==dict(b.__dict__))
print(a.__dict__)
print(b.__dict__)