import ast
from pathlib import Path
src = Path('outputs/candidate/scripts/run.py').read_text(encoding='utf-8')
try:
    ast.parse(src)
    print('SYNTAX OK')
except SyntaxError as e:
    print('SYNTAX ERROR:', e)
i = src.find('types_and_tables_preserved')
print(src[i-400:i+300])
