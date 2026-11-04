src = open('outputs/candidate/scripts/run.py', encoding='utf-8').read()
old = '''def style_sig(cell):
    return (cell.font, cell.fill, cell.border, cell.alignment, cell.number_format)'''
new = '''def style_sig(cell):
    # cell.font 等返回 StyleProxy 包装对象，其 __eq__ 未委托给真实样式对象；
    # 用 copy() 解包得到真实样式对象后再比较，避免同值样式被误判不等。
    return (copy(cell.font), copy(cell.fill), copy(cell.border),
            copy(cell.alignment), cell.number_format)'''
assert old in src
src = src.replace(old, new)
src = src.replace('import argparse\nimport hashlib\nimport json\nimport sys',
                  'import argparse\nimport hashlib\nimport json\nimport sys\nfrom copy import copy')
open('outputs/candidate/scripts/run.py','w',encoding='utf-8',newline='\n').write(src)
print('patched ok')
import subprocess, sys
cmd = [sys.executable, 'outputs/candidate/scripts/run.py', '--request', 'inputs/dev_request.json', '--output-root', 'outputs/development_delivery']
r = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', cwd='.')
print('exit:', r.returncode)
print(r.stdout[-2500:])
print('stderr:', r.stderr)
open('outputs/validation_history/dev_run2_after_fix_stdout.log','w',encoding='utf-8').write(r.stdout)