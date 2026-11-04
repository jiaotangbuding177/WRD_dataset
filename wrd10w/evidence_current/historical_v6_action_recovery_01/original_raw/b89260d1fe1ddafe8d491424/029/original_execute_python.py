from pathlib import Path
import ast
p = Path('outputs/candidate/scripts/run.py')
src = p.read_text(encoding='utf-8')
bad = '''        table_defs_in[title] = {
            tname: (t.ref, t.tableStyleInfo.name if t.tableStyleInfo else None)
            for tname, t in ws_in.tables.items()
        }
        table_defs_out[title] = {
            tname: (t.ref, t.tableStyleInfo.name if t.tableStyleInfo else None)
            for tname, t in ws_out.tables.items()
        }
'''
good = '''        table_defs_in[title] = {
            tname: (ws_in.tables[tname].ref,
                    ws_in.tables[tname].tableStyleInfo.name
                    if ws_in.tables[tname].tableStyleInfo else None)
            for tname in ws_in.tables
        }
        table_defs_out[title] = {
            tname: (ws_out.tables[tname].ref,
                    ws_out.tables[tname].tableStyleInfo.name
                    if ws_out.tables[tname].tableStyleInfo else None)
            for tname in ws_out.tables
        }
'''
assert src.count(bad) == 1
src = src.replace(bad, good)
p.write_text(src, encoding='utf-8')
ast.parse(src)
print('fixed, SYNTAX OK')
