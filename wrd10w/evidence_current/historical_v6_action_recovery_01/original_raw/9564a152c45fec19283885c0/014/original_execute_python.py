import openpyxl
from openpyxl.styles.fonts import Font
print('Font has __eq__:', Font.__eq__ is not object.__eq__)
from openpyxl.styles.serialisable import Serialisable
print('Serialisable has __eq__:', '__eq__' in Serialisable.__dict__)
f1 = Font(name='X', sz=10)
f2 = Font(name='X', sz=10)
print('two fresh fonts equal:', f1 == f2, 'ne:', f1 != f2)
wi = openpyxl.load_workbook('inputs/dev_input.xlsx')
wo = openpyxl.load_workbook('outputs/development_delivery/dev_outputs/masked.xlsx')
a = wi['待脱敏记录']['A1'].font; b = wo['待脱敏记录']['A1'].font
print('loaded fonts: == :', a==b, ' != :', a!=b)
import io
from openpyxl.xml.functions import tostring
print('xml equal:', tostring(a.to_tree()) == tostring(b.to_tree()))
# 测试border/alignment同理
sb1, sb2 = wi['待脱敏记录']['A1'].border, wo['待脱敏记录']['A1'].border
print('border xml equal:', tostring(sb1.to_tree()) == tostring(sb2.to_tree()))