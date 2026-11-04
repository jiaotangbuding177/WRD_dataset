import os, json, shutil, hashlib
os.makedirs('outputs/validation_history', exist_ok=True)

def snap(src_dir, name, files, reasons):
    d = os.path.join('outputs/validation_history', name)
    os.makedirs(d, exist_ok=True)
    for f in files:
        dst = os.path.join(d, f.replace('/', '__'))
        shutil.copy(os.path.join(src_dir, f), dst)
    json.dump(reasons, open(os.path.join(d, 'failure_reason.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
    print('snapped', d)

snap('outputs/candidate', 'rev1_runpy_q18_evidence', ['scripts/run.py'], {
  'revision': 'rev1',
  'date': '2026-10-19',
  'file': 'scripts/run.py',
  'failures': [{
    'id': 'Q18',
    'source': 'inputs/validation_feedback.json development_case_diagnostics (all 7 valid cases)',
    'description': '报告checks数组中索引1/2/5（non_target_values_preserved、styles_and_layout_preserved、counting_identity）的evidence被判为不可核验（unverifiable_check_indices=[1,2,5]，critical）。可核验的检查（索引0/3/4）其证据均含交付文件位置或SHA256锚点，不可核验的三条只有中文散文计数，缺少可定位/可复算的锚点，不符合契约报告schema对evidence的要求（证据为真实统计或交付文件位置）。',
    'fix': '为三条检查的evidence补充输入/输出文件实际路径与SHA256、逐格比对规模与不一致计数等真实可复算统计，不改变任何业务逻辑与检查本身。'
  }]
})

snap('outputs', 'rev2_learning_evidence_quotes', ['learning_evidence.json'], {
  'revision': 'rev2',
  'date': '2026-10-19',
  'file': 'learning_evidence.json',
  'failures': [
    {
      'id': 'LE01',
      'source': 'inputs/validation_feedback.json previous_validation.learning_evidence_review.findings[0]',
      'json_pointer': '/requirements_and_corrections/4/quote',
      'description': '引文非原文连续子串：省略了“变更明细”与右括号之间的内部留档/勿外传提醒却无省略标记直接拼接右括号；引用消息 conv_b5e6f3d3bab9:23a61c50 身份真实。',
      'fix': '替换为该真实消息中已验证连续的精确子串（含原提醒部分）。'
    },
    {
      'id': 'LE02',
      'source': 'inputs/validation_feedback.json previous_validation.learning_evidence_review.findings[1]',
      'json_pointer': '/instance_values/note',
      'description': '原note把历史会话示例值声明为“合成”，但证据只支持本轮恢复附件为synthetic，不支持历史实例值为synthetic；历史示例真实性未知。',
      'fix': 'note改写为：历史助手给出的示例、身份未核实（真实/虚构均未知）、不得作为新任务默认值或答案；synthetic身份仅适用于本轮绑定的恢复附件，不扩大到历史会话原值。'
    }
  ]
})
print('done')