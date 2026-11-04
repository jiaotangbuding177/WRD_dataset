from pathlib import Path

p = Path('outputs/candidate/scripts/run.py')
src = p.read_text(encoding='utf-8')
orig = src

# --- CP04: additionalProperties=false enforcement (top-level) ---
old = '''    for k in ("schema_version", "input_workbook", "output_workbook",\n              "report_file", "worksheets", "masking"):\n        if k not in req:\n            raise ContractError(f"request.json \u7f3a\u5c11\u5fc5\u9700\u5b57\u6bb5: {k}")\n'''
new = old + '''    allowed_top = {"schema_version", "input_workbook", "output_workbook",\n                   "report_file", "worksheets", "masking"}\n    extra_top = set(req) - allowed_top\n    if extra_top:\n        raise ContractError(f"request.json \u542b\u591a\u4f59\u5b57\u6bb5: {sorted(extra_top)}\uff08\u5951\u7ea6\u4e0d\u5141\u8bb8\u989d\u5916\u5c5e\u6027\uff09")\n'''
assert src.count(old) == 1, 'top-level anchor'
src = src.replace(old, new)

# --- CP04: worksheets item extra fields ---
old = '''        if not isinstance(ws["name"], str) or not ws["name"]:\n            raise ContractError(f"worksheets[{i}].name \u5fc5\u987b\u662f\u975e\u7a7a\u5b57\u7b26\u4e32")\n'''
new = '''        ws_allowed = {"name", "header_row", "data_start_row", "data_end_row", "columns"}\n        ws_extra = set(ws) - ws_allowed\n        if ws_extra:\n            raise ContractError(f"worksheets[{i}] \u542b\u591a\u4f59\u5b57\u6bb5: {sorted(ws_extra)}\uff08\u5951\u7ea6\u4e0d\u5141\u8bb8\u989d\u5916\u5c5e\u6027\uff09")\n        if not isinstance(ws["name"], str) or not ws["name"]:\n            raise ContractError(f"worksheets[{i}].name \u5fc5\u987b\u662f\u975e\u7a7a\u5b57\u7b26\u4e32")\n'''
assert src.count(old) == 1, 'ws anchor'
src = src.replace(old, new)

# --- CP04: masking extra fields ---
old = '''    m = req["masking"]\n    if not isinstance(m, dict):\n        raise ContractError("masking \u5fc5\u987b\u662f\u5bf9\u8c61")\n    for k in ("prefix_chars", "suffix_chars", "replacement"):\n'''
new = '''    m = req["masking"]\n    if not isinstance(m, dict):\n        raise ContractError("masking \u5fc5\u987b\u662f\u5bf9\u8c61")\n    m_allowed = {"prefix_chars", "suffix_chars", "replacement"}\n    m_extra = set(m) - m_allowed\n    if m_extra:\n        raise ContractError(f"masking \u542b\u591a\u4f59\u5b57\u6bb5: {sorted(m_extra)}\uff08\u5951\u7ea6\u4e0d\u5141\u8bb8\u989d\u5916\u5c5e\u6027\uff09")\n    for k in ("prefix_chars", "suffix_chars", "replacement"):\n'''
assert src.count(old) == 1, 'masking anchor'
src = src.replace(old, new)

# --- CP03: new check for cell data_type and Excel table definitions ---
old = '''    identity = (totals["changed_cells"] + totals["unchanged_text_cells"]\n'''
new = '''    # 6) \u5168\u7c3f\u5355\u5143\u683c\u5b58\u50a8\u7c7b\u578b\u4e0eExcel\u8868\u683c\u5b9a\u4e49\u4fdd\u6301\uff08R06/R09\uff09\n    type_compared, type_mismatch = 0, []\n    table_defs_in = {}\n    table_defs_out = {}\n    for title in wb_in.sheetnames:\n        ws_in, ws_out = wb_in[title], wb_out[title]\n        for row in ws_in.iter_rows():\n            for cell in row:\n                type_compared += 1\n                if cell.data_type != ws_out[title][cell.coordinate].data_type:\n                    type_mismatch.append((title, cell.coordinate))\n        table_defs_in[title] = {\n            tname: (t.ref, t.tableStyleInfo.name if t.tableStyleInfo else None)\n            for tname, t in ws_in.tables.items()\n        }\n        table_defs_out[title] = {\n            tname: (t.ref, t.tableStyleInfo.name if t.tableStyleInfo else None)\n            for tname, t in ws_out.tables.items()\n        }\n    tables_same = table_defs_in == table_defs_out\n    table_count = sum(len(v) for v in table_defs_in.values())\n    checks.append({\n        "name": "types_and_tables_preserved",\n        "status": "PASS" if (tables_same and not type_mismatch) else "FAIL",\n        "evidence": f"\u91cd\u5f00\u8f93\u5165\u4e0e\u8f93\u51fa\u9010\u683c\u6bd4\u5bf9 {type_compared} \u4e2a\u5355\u5143\u683c\u7684\u5b58\u50a8\u7c7b\u578b\uff08data_type\uff09\uff0c\u7c7b\u578b\u4e0d\u4e00\u81f4 {len(type_mismatch)} \u5904\uff1b\u9010\u8868\u6bd4\u5bf9Excel\u8868\u683c\u5b9a\u4e49\uff08\u8868\u540d/\u8303\u56f4/\u6837\u5f0f\uff09\u5171 {table_count} \u4e2a\uff0c\u5b9a\u4e49\u4e00\u81f4={tables_same}\u201d,\n    })\n\n    identity = (totals["changed_cells"] + totals["unchanged_text_cells"]\n'''
assert src.count(old) == 1, 'check-insert anchor'
src = src.replace(old, new)

# --- Q18: stdout summary keeps evidence ---
old = '''        "checks": [{"name": c["name"], "status": c["status"]} for c in checks],\n'''
new = '''        "checks": [{"name": c["name"], "status": c["status"], "evidence": c["evidence"]}\n                   for c in checks],\n'''
assert src.count(old) == 1, 'summary anchor'
src = src.replace(old, new)

assert src != orig
p.write_text(src, encoding='utf-8')
print('patched, new size:', len(src))
