import json, hashlib, sys
from copy import copy
from pathlib import Path
import openpyxl

cases = json.load(open('inputs/development_cases.json', encoding='utf-8'))
cases.append({'id': 'original_recovery', 'request': 'inputs/dev_request.json', 'valid_input': True})

def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def mask(v, pre, suf, rep):
    if len(v) <= pre + suf:
        return v
    return v[:pre] + rep + (v[-suf:] if suf > 0 else '')

summary = {}
for case in cases:
    cid = case['id']
    if not case['valid_input']:
        continue
    req = json.loads(Path(case['request']).read_text(encoding='utf-8'))
    base = Path(case['request']).resolve().parent
    in_path = Path(req['input_workbook']); in_path = in_path if in_path.is_absolute() else base / in_path
    out_root = Path('outputs/repair_tests') / cid
    owb = Path(req['output_workbook']); owb = owb if owb.is_absolute() else out_root / owb
    rpt = Path(req['report_file']); rpt = rpt if rpt.is_absolute() else out_root / rpt
    m = req['masking']
    pre, suf, rep = m['prefix_chars'], m['suffix_chars'], m['replacement']
    errors = []

    # report structure
    report = json.loads(rpt.read_text(encoding='utf-8'))
    for k in ('schema_version','input_sha256','output_sha256','masking','sheets','totals','checks','uncovered'):
        if k not in report: errors.append(f'report缺字段 {k}')
    if report.get('schema_version') != 'data_field_mask_report_v1': errors.append('schema_version错')
    if report.get('input_sha256') != sha(in_path): errors.append('input_sha256不符')
    if report.get('output_sha256') != sha(owb): errors.append('output_sha256不符')
    if report.get('masking') != m: errors.append('masking与请求不一致')
    if not isinstance(report.get('uncovered'), list): errors.append('uncovered非数组')
    for c in report.get('checks', []):
        if not (c.get('name') and c.get('status') in ('PASS','FAIL','UNKNOWN') and isinstance(c.get('evidence'), str) and c['evidence']):
            errors.append(f"check证据缺失: {c.get('name')}")
        if c.get('status') != 'PASS': errors.append(f"check非PASS: {c.get('name')}")

    # input unchanged
    wb_in = openpyxl.load_workbook(in_path)
    wb_out = openpyxl.load_workbook(owb)

    target_coords = set()
    for spec in req['worksheets']:
        ws_in = wb_in[spec['name']]
        headers = {}
        for cell in ws_in[spec['header_row']]:
            if isinstance(cell.value, str):
                headers.setdefault(cell.value, []).append(cell.column)
        colmap = {cn: headers[cn][0] for cn in spec['columns']}
        for row in range(spec['data_start_row'], spec['data_end_row'] + 1):
            for cn in spec['columns']:
                cell = ws_in.cell(row=row, column=colmap[cn])
                target_coords.add((spec['name'], cell.coordinate))
                got = wb_out[spec['name']][cell.coordinate].value
                gt = cell.data_type
                if gt == 'f' or cell.value is None or (isinstance(cell.value, str) and cell.value == '') or not isinstance(cell.value, str):
                    if got != cell.value: errors.append(f"{spec['name']}!{cell.coordinate} 应保留: {cell.value!r}->{got!r}")
                else:
                    want = mask(cell.value, pre, suf, rep)
                    if got != want: errors.append(f"{spec['name']}!{cell.coordinate} 掩码不符: {got!r}!={want!r}")

    # non-target values + types + styles; tables; layout
    for title in wb_in.sheetnames:
        wi, wo = wb_in[title], wb_out[title]
        if wi.merged_cells.ranges != wo.merged_cells.ranges or wi.freeze_panes != wo.freeze_panes or wi.sheet_state != wo.sheet_state:
            errors.append(f'{title} 布局/状态改变')
        ti = {n: (wi.tables[n].ref, wi.tables[n].tableStyleInfo.name if wi.tables[n].tableStyleInfo else None) for n in wi.tables}
        to = {n: (wo.tables[n].ref, wo.tables[n].tableStyleInfo.name if wo.tables[n].tableStyleInfo else None) for n in wo.tables}
        if ti != to: errors.append(f'{title} 表格定义改变')
        for row in wi.iter_rows():
            for cell in row:
                oc = wo[cell.coordinate]
                if (title, cell.coordinate) not in target_coords and cell.value != oc.value:
                    errors.append(f'{title}!{cell.coordinate} 非目标值改变')
                if cell.data_type != oc.data_type:
                    errors.append(f'{title}!{cell.coordinate} data_type改变')
                if (copy(cell.font), copy(cell.fill), copy(cell.border), copy(cell.alignment), cell.number_format) != \
                   (copy(oc.font), copy(oc.fill), copy(oc.border), copy(oc.alignment), oc.number_format):
                    errors.append(f'{title}!{cell.coordinate} 样式改变')
    if wb_in.sheetnames != wb_out.sheetnames:
        errors.append('工作表顺序改变')

    # totals identity
    t = report['totals']
    if t['changed_cells'] + t['unchanged_text_cells'] + t['blank_cells'] + t['non_text_cells'] + t['formula_cells'] != t['selected_cells']:
        errors.append('totals恒等式不成立')
    n_selected_expected = sum((s['data_end_row'] - s['data_start_row'] + 1) * len(s['columns']) for s in req['worksheets'])
    if t['selected_cells'] != n_selected_expected:
        errors.append(f"selected_cells {t['selected_cells']} != 预期 {n_selected_expected}")

    summary[cid] = {'errors': errors, 'totals': t, 'report_checks': len(report['checks'])}
    print(cid, 'PASS' if not errors else f'FAIL {errors[:3]}')

Path('work/independent_verification.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
