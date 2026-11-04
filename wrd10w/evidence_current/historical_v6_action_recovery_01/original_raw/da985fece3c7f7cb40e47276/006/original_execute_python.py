import hashlib, os, json
p = 'outputs/candidate/scripts/run.py'
text = open(p, encoding='utf-8', newline='').read()
lines = text.split('\r\n')

new5 = [
'        "evidence": {',
'            "summary": f"重开输入 {in_path}（sha256 {input_sha_before}）与输出 {out_path}（sha256 {output_sha}）逐格比对 {type_compared} 个单元格的存储类型（data_type），类型不一致 {len(type_mismatch)} 处；逐表比对Excel表格定义（表名/范围/样式）共 {table_count} 个，定义一致={tables_same}",',
'            "input_workbook": str(in_path),',
'            "output_workbook": str(out_path),',
'            "input_sha256": input_sha_before,',
'            "output_sha256": output_sha,',
'            "cells_compared": type_compared,',
'            "type_mismatch_cells": len(type_mismatch),',
'            "table_definition_count": table_count,',
'            "table_definitions_identical": tables_same,',
'        },',
]
new6 = [
'        "evidence": {',
'            "summary": f"报告totals恒等式：changed {totals[\'changed_cells\']} + unchanged_text {totals[\'unchanged_text_cells\']} + blank {totals[\'blank_cells\']} + non_text {totals[\'non_text_cells\']} + formula {totals[\'formula_cells\']} = selected {totals[\'selected_cells\']}；恒等式成立={identity}，可由报告totals逐字段复算",',
'            "totals": dict(totals),',
'            "sum_of_components": totals["changed_cells"] + totals["unchanged_text_cells"] + totals["blank_cells"] + totals["non_text_cells"] + totals["formula_cells"],',
'            "selected_cells": totals["selected_cells"],',
'            "identity_holds": identity,',
'        },',
]

i5 = [i for i,l in enumerate(lines) if '"evidence": f"重开输入与输出逐格比对' in l]
i6 = [i for i,l in enumerate(lines) if '"evidence": f"报告 {report_path} 的totals' in l]
print('found:', i5, i6)
assert len(i5)==1 and len(i6)==1
lines[i5[0]:i5[0]+1] = new5
# i6 shifts by len(new5)-1
i6off = i6[0] + len(new5) - 1
lines[i6off:i6off+1] = new6
open(p, 'w', encoding='utf-8', newline='').write('\r\n'.join(lines))

h=hashlib.sha256(open(p,'rb').read()).hexdigest()
json.dump({'modified_file': p, 'sha256_after': h, 'bytes': os.path.getsize(p),
           'changed': ['checks[5].evidence -> structured dict with paths/sha/counts', 'checks[6].evidence -> structured dict with totals/identity']},
          open('outputs/validation_history/changes.json','w',encoding='utf-8'), ensure_ascii=False, indent=2)
print('patched sha256:', h)
import py_compile; py_compile.compile(p, doraise=True); print('syntax OK')