import json, shutil
from pathlib import Path
hist = Path('outputs/validation_history/rev1_types_tables_check_buggy')
hist.mkdir(parents=True)
shutil.copyfile('outputs/candidate/scripts/run.py', hist / 'scripts_run.py')
shutil.copyfile('outputs/candidate/README.md', hist / 'README.md')
shutil.copyfile('outputs/candidate/workflow_spec.json', hist / 'workflow_spec.json')
(hist / 'failures.json').write_text(json.dumps({
    'snapshot_scope': 'CP03/Q18/CP04/CP01修订后、types_and_tables_preserved检查修正前',
    'failures': [
        {'case': 'dev_01..dev_05,original_recovery首轮', 'error': "ValueError: 客户台账 is not a valid coordinate or range — ws_out[title][cell.coordinate]误用（应为ws_out[cell.coordinate]）", 'exit_code': 1},
        {'case': 'dev_06', 'error': "AttributeError: 'str' object has no attribute 'ref' — openpyxl 3.1.5中ws.tables.items()的值为引用字符串，需用ws.tables[tname]取Table对象", 'exit_code': 1}
    ],
    'resolution': '两处均已修正；dev_06证明新增表格检查在真实含Excel表格的输入上有实际作用'
}, ensure_ascii=False, indent=2), encoding='utf-8')
print('rev1 snapshot saved')
