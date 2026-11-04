import json

# ---------- rev1: run.py Q18 evidence fix ----------
p = 'outputs/candidate/scripts/run.py'
s = open(p, encoding='utf-8').read()

def rep(old, new):
    global s
    assert old in s, 'NOT FOUND: ' + old[:80]
    assert s.count(old) == 1, 'AMBIGUOUS: ' + old[:80]
    s = s.replace(old, new)

# move output_sha computation before the checks (needed as verifiable anchor)
rep('''        print(f"ERROR: 交付文件无法重新打开核验: {exc}", file=sys.stderr)
        return 3
''', '''        print(f"ERROR: 交付文件无法重新打开核验: {exc}", file=sys.stderr)
        return 3

    output_sha = sha256_file(out_path)
''')
rep('''    output_sha = sha256_file(out_path)
    checks.append({
        "name": "deliverable_hash_recorded",''', '''    checks.append({
        "name": "deliverable_hash_recorded",''')

# check 2: non_target_values_preserved
rep('''        "evidence": f"全簿 {len(wb_in.sheetnames)} 个工作表逐格比对 {compared} 个单元格，非目标值保持一致；不一致 {len(mismatch_nontarget)} 处",''', '''        "evidence": f"重开输入 {in_path}（sha256 {input_sha_before}）与输出 {out_path}（sha256 {output_sha}），全簿 {len(wb_in.sheetnames)} 个工作表逐格比对 {compared} 个单元格的值；非目标不一致 {len(mismatch_nontarget)} 处",''')

# check 3: styles_and_layout_preserved
rep('''        "evidence": f"比对 {style_compared} 个单元格的字体/填充/边框/对齐/数字格式，及表顺序、表状态、合并区域、冻结窗格、行列宽高；不一致 {len(style_mismatch)} 处",''', '''        "evidence": f"重开输出 {out_path}（sha256 {output_sha}）与输入逐格比对 {style_compared} 个单元格的字体/填充/边框/对齐/数字格式，及表顺序、表状态、合并区域、冻结窗格、行列宽高；样式不一致 {len(style_mismatch)} 处，布局一致={layout_ok}",''')

# check 6: counting_identity -> computed status + verifiable anchor; move all_pass after it
rep('''    all_pass = all(c["status"] == "PASS" for c in checks)
    checks.append({
        "name": "counting_identity",
        "status": "PASS",
        "evidence": f"changed {totals['changed_cells']} + unchanged_text {totals['unchanged_text_cells']} + blank {totals['blank_cells']} + non_text {totals['non_text_cells']} + formula {totals['formula_cells']} = selected {totals['selected_cells']}",
    })''', '''    identity = (totals["changed_cells"] + totals["unchanged_text_cells"]
                + totals["blank_cells"] + totals["non_text_cells"]
                + totals["formula_cells"] == totals["selected_cells"])
    checks.append({
        "name": "counting_identity",
        "status": "PASS" if identity else "FAIL",
        "evidence": f"报告 {report_path} 的totals：changed {totals['changed_cells']} + unchanged_text {totals['unchanged_text_cells']} + blank {totals['blank_cells']} + non_text {totals['non_text_cells']} + formula {totals['formula_cells']} = selected {totals['selected_cells']}；恒等式成立={identity}，可由报告totals逐字段复算",
    })
    all_pass = all(c["status"] == "PASS" for c in checks)''')

open(p, 'w', encoding='utf-8', newline='').write(s)
print('run.py revised, len', len(s))

# ---------- rev2: learning_evidence.json LE01/LE02 ----------
lp = 'outputs/learning_evidence.json'
le = json.load(open(lp, encoding='utf-8'))

exact_quote = '- 🔒 `2026-07-31_脱敏对照表_内部使用.xlsx`（客户001→原名称、销售A→原姓名、1287条变更明细，**这份含原始信息，自己留档用，千万别外传**）'
conv = json.load(open('inputs/conversation.json', encoding='utf-8'))
src = [m['content'] for m in conv['messages'] if (m.get('id') or m.get('message_id')) == 'conv_b5e6f3d3bab9:23a61c50'][0]
assert exact_quote in src, 'quote not contiguous'
le['requirements_and_corrections'][4]['quote'] = exact_quote
le['requirements_and_corrections'][4]['quote_note'] = '原文连续子串，未做任何省略或拼接；该引文仅用于说明历史交付物形态，不代表历史执行已获工具核实'

le['instance_values']['note'] = ('以下为历史会话中assistant给出的示例值：其实体与取值的真实性未核实（既未证实为真实企业数据，'
                                 '也未证实为合成数据），不构成本次任务的默认参数或答案。synthetic身份仅适用于本轮绑定的'
                                 'synthetic恢复工作簿（material_identity.json input_identity），不扩大到历史会话中的原值。')
json.dump(le, open(lp, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
print('learning_evidence.json revised')

# quick sanity: all quotes contiguous
for i, r in enumerate(le['requirements_and_corrections']):
    mid = r['message_id'].split(':')[-1]
    content = next(m['content'] for m in conv['messages'] if (m.get('id') or m.get('message_id')).endswith(mid))
    ok = r['quote'] in content
    print(i, r['message_id'], 'contiguous:', ok)
assert all(r['quote'] in next(m['content'] for m in conv['messages'] if (m.get('id') or m.get('message_id')).endswith(r['message_id'].split(':')[-1])) for r in le['requirements_and_corrections'])
print('ALL QUOTES VERIFIED')