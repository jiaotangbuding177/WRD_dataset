from pathlib import Path
import ast
p = Path('outputs/candidate/scripts/run.py')
src = p.read_text(encoding='utf-8')
bad = 'if cell.data_type != ws_out[title][cell.coordinate].data_type:'
good = 'if cell.data_type != ws_out[cell.coordinate].data_type:'
assert src.count(bad) == 1
src = src.replace(bad, good)
p.write_text(src, encoding='utf-8')
ast.parse(src)
print('fixed, SYNTAX OK')
