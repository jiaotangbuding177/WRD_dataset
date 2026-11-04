from pathlib import Path
import ast
p = Path('outputs/candidate/scripts/run.py')
src = p.read_text(encoding='utf-8')
bad = '\u5b9a\u4e49\u4e00\u81f4={tables_same}\u201d,'
good = '\u5b9a\u4e49\u4e00\u81f4={tables_same}",'
assert src.count(bad) == 1
src = src.replace(bad, good)
p.write_text(src, encoding='utf-8')
ast.parse(src)
print('SYNTAX OK, size:', len(src))
