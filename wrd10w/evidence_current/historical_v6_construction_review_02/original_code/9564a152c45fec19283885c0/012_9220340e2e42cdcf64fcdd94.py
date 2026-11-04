import os, shutil, json, hashlib
os.makedirs('outputs/validation_history/snapshots', exist_ok=True)
os.makedirs('outputs/validation_history', exist_ok=True)
shutil.copy('outputs/candidate/scripts/run.py', 'outputs/validation_history/snapshots/run_v1_style_fail.py')
shutil.copy('logs/011.stdout.txt', 'outputs/validation_history/dev_run1_fail_stdout.log')
note = {
  "run": 1,
  "command": "python outputs/candidate/scripts/run.py --request inputs/dev_request.json --output-root outputs/development_delivery",
  "exit_code": 3,
  "failed_check": "styles_and_layout_preserved",
  "snapshot": "outputs/validation_history/snapshots/run_v1_style_fail.py",
  "stdout_log": "outputs/validation_history/dev_run1_fail_stdout.log",
  "note": "首次真实运行样式/布局核验失败，保留快照与日志后再定位"
}
json.dump(note, open('outputs/validation_history/snapshots/run_v1_failure_note.json','w',encoding='utf-8'), ensure_ascii=False, indent=2)

# 定位：重开输入与输出，比较各项，找出真实不一致点
import openpyxl
inp = 'inputs/dev_input.xlsx'
out = 'outputs/development_delivery/dev_outputs/masked.xlsx'
wi = openpyxl.load_workbook(inp)
wo = openpyxl.load_workbook(out)
print('sheetnames:', wi.sheetnames, wo.sheetnames)
for t in wi.sheetnames:
    a, b = wi[t], wo[t]
    print(t, 'merged:', str(a.merged_cells.ranges), str(b.merged_cells.ranges), '| freeze:', a.freeze_panes, b.freeze_panes)
    ca = sorted((k, d.width, d.hidden) for k,d in a.column_dimensions.items())
    cb = sorted((k, d.width, d.hidden) for k,d in b.column_dimensions.items())
    if ca != cb: print(' COL DIFF:', ca, cb)
    ra = sorted((k, d.height, d.hidden) for k,d in a.row_dimensions.items())
    rb = sorted((k, d.height, d.hidden) for k,d in b.row_dimensions.items())
    if ra != rb: print(' ROW DIFF:', ra, rb)
    for row in a.iter_rows():
        for c in row:
            d = b[c.coordinate]
            if (c.font, c.fill, c.border, c.alignment, c.number_format) != (d.font, d.fill, d.border, d.alignment, d.number_format):
                print(' STYLE DIFF', t, c.coordinate)
                for attr in ['font','fill','border','alignment','number_format']:
                    if getattr(c, attr) != getattr(d, attr):
                        print('   ', attr, repr(getattr(c,attr)), '->', repr(getattr(d,attr)))
print('state:', [(t, wi[t].sheet_state, wo[t].sheet_state) for t in wi.sheetnames])