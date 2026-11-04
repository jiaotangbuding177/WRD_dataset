import json, re
from pathlib import Path

# ---- README: generic structural example, no DEV filenames/sheet/rows/columns ----
rp = Path('outputs/candidate/README.md')
readme = rp.read_text(encoding='utf-8')
start = readme.index('## 请求示例')
end = readme.index('## 业务规则')
generic = '''## 请求示例（通用结构说明，占位值需替换为实际工作簿内容）

```json
{
  "schema_version": "data_field_mask_request_v1",
  "input_workbook": "workbook.xlsx",
  "output_workbook": "deliverables/masked.xlsx",
  "report_file": "deliverables/masking_report.json",
  "worksheets": [
    {"name": "<实际工作表名>", "header_row": 1, "data_start_row": 2,
     "data_end_row": <实际末行>, "columns": ["<目标表头A>", "<目标表头B>"]}
  ],
  "masking": {"prefix_chars": 2, "suffix_chars": 2, "replacement": "***"}
}
```

结构要点：`worksheets` 数组每项对应一个工作表，`name` 为精确表名；`header_row` 为
表头所在行；`data_start_row`/`data_end_row` 为数据行闭区间（header_row <
data_start_row <= data_end_row）；`columns` 为该表头行中真实存在的目标表头名，
且各自唯一。`masking` 三参数分别为前保留字符数（0..8）、后保留字符数（0..8）与
替换标记（1..16字符）。以上仅为字段结构说明，实际取值以被处理工作簿为准。

'''
readme = readme[:start] + generic + readme[end:]
rp.write_text(readme, encoding='utf-8')
print('README updated, size:', len(readme))

# ---- workflow_spec: sync with code (CP03/CP04), keep claims accurate ----
sp = Path('outputs/candidate/workflow_spec.json')
spec = json.loads(sp.read_text(encoding='utf-8'))
for n in spec['nodes']:
    if n['id'] == 'parse_request':
        n['method'] += '；同时拒绝schema外多余字段（additionalProperties=false）'
        n['checks'].append('schema外多余字段被拒绝')
    if n['id'] == 'verify_and_save':
        n['method'] += ' ⑥逐格比较全部单元格存储类型data_type，并比较Excel表格定义（表名/范围/样式）保持（R06/R09）'
        n['checks'].append('types_and_tables_preserved')
assert any('types_and_tables_preserved' in n.get('checks', []) for n in spec['nodes'])
sp.write_text(json.dumps(spec, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print('workflow_spec updated')

# ---- sanity: no dev-instance config remains in README ----
for token in ['dev_input', '待脱敏记录', 'data_end_row\": 17', 'dev_outputs']:
    assert token not in readme, token
print('README clean of dev-instance tokens')
