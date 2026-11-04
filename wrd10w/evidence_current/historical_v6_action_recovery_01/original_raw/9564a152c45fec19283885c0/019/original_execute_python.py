import openpyxl
print('version:', openpyxl.__version__)
from openpyxl.descriptors.serialisable import Serialisable
import inspect
print(inspect.getsource(Serialisable.__eq__))
from openpyxl.styles.fonts import Font
wi = openpyxl.load_workbook('inputs/dev_input.xlsx')
wo = openpyxl.load_workbook('outputs/development_delivery/dev_outputs/masked.xlsx')
a = wi['待脱敏记录']['A1'].font; b = wo['待脱敏记录']['A1'].font
print('color eq:', a.color == b.color, '| class eq:', a.__class__ == b.__class__)
for k, v in a.__dict__.items():
    w = b.__dict__[k]
    if type(v) != type(w): print('TYPE DIFF', k, type(v), type(w))
    elif v != w: print('VAL DIFF', k, repr(v)[:80], repr(w)[:80])