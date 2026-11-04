import inspect
from openpyxl.styles.fonts import Font
print(inspect.getsource(Font.__eq__) if '__eq__' in Font.__dict__ else 'not overridden in Font')
import openpyxl.styles.styles as ss
from openpyxl.styles.serialisable import Serialisable
print(inspect.getsource(Serialisable.__eq__))
wi = openpyxl.load_workbook('inputs/dev_input.xlsx')
a = wi['待脱敏记录']['A1'].font
print(type(a), a.__class__.__module__)
print('is proxy?', type(a).__name__)