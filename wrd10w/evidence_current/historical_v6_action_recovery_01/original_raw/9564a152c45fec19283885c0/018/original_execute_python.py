import inspect
from openpyxl.styles.serialisable import Serialisable
src = inspect.getsource(Serialisable.__eq__)
print(src)
from openpyxl.styles.fonts import Font
import openpyxl
wi = openpyxl.load_workbook('inputs/dev_input.xlsx')
wo = openpyxl.load_workbook('outputs/development_delivery/dev_outputs/masked.xlsx')
a = wi['待脱敏记录']['A1'].font
b = wo['待脱敏记录']['A1'].font
print('type a:', type(a), 'module:', type(a).__module__)
# 手动模拟 __eq__ 的关键步骤
import openpyxl.styles.colors as colors
print('color eq:', a.color == b.color)
print('class eq:', a.__class__ == b.__class__)
for k, v in a.__dict__.items():
    w = b.__dict__[k]
    if type(v) != type(w):
        print('TYPE DIFF', k, type(v), type(w))
    elif v != w:
        print('VAL DIFF', k)