import shutil, json
# 保留失败证据：测试脚本快照 + 失败日志
shutil.copy('outputs/validation_history/edge_case_tests.py', 'outputs/validation_history/snapshots/edge_case_tests_v1_expectation_fail.py')
note = {
  "run": "edge_case_tests_run1",
  "exit_code": 1,
  "failed_checks": ["edge_transposed_masked", "edge_transposed_nontarget"],
  "diagnosis": "两处失败均为测试脚本预期错误，非候选程序错误：(1) C2期望值未计入首尾空格，契约R04明确不trim，程序输出' 北***司 '正确；(2) C3位于data_end_row=3区间内的目标列，应被掩码，程序输出'上海***某厂'正确。候选程序未做任何修改。",
  "snapshot": "outputs/validation_history/snapshots/edge_case_tests_v1_expectation_fail.py",
  "logs": ["outputs/validation_history/edge_case_tests_run1.log", "outputs/validation_history/testdata/run_edge_transposed.log"]
}
json.dump(note, open('outputs/validation_history/snapshots/edge_case_tests_v1_failure_note.json','w',encoding='utf-8'), ensure_ascii=False, indent=2)

src = open('outputs/validation_history/edge_case_tests.py', encoding='utf-8').read()
old1 = '''check("edge_transposed_masked",
      wo2["C2"].value == " 北京***公司 " and wo2["A2"].value == "TE***-1",
      f"C2={wo2['C2'].value!r} A2={wo2['A2'].value!r}")'''
new1 = '''# R04：不trim，首尾空格计入前后保留（前2字符=' 北'，后2字符='司 '）
check("edge_transposed_masked",
      wo2["C2"].value == " 北***司 " and wo2["A2"].value == "TE***-1",
      f"C2={wo2['C2'].value!r} A2={wo2['A2'].value!r}")'''
old2 = '''check("edge_transposed_nontarget",
      wo2["B2"].value == 100 and wo2["D2"].value == "张测试" and wo2["C3"].value == "上海某某厂",
      f"B2={wo2['B2'].value!r} D2={wo2['D2'].value!r} C3={wo2['C3'].value!r}")'''
new2 = '''# C3位于行区间2..3内的目标列，应被掩码；非目标列B2/D2保持
check("edge_transposed_nontarget",
      wo2["B2"].value == 100 and wo2["D2"].value == "张测试" and wo2["C3"].value == "上海***某厂",
      f"B2={wo2['B2'].value!r} D2={wo2['D2'].value!r} C3={wo2['C3'].value!r}")'''
assert old1 in src and old2 in src
src = src.replace(old1, new1).replace(old2, new2)
open('outputs/validation_history/edge_case_tests.py','w',encoding='utf-8',newline='\n').write(src)

import subprocess, sys
r = subprocess.run([sys.executable, 'outputs/validation_history/edge_case_tests.py'], capture_output=True, text=True, encoding='utf-8', cwd='.')
print('exit:', r.returncode)
print(r.stdout)
open('outputs/validation_history/edge_case_tests_run2_after_fix.log','w',encoding='utf-8').write(r.stdout + '\n--- stderr ---\n' + r.stderr)