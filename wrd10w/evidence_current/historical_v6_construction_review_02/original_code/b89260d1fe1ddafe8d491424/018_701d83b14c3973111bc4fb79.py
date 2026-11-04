import json, shutil, hashlib
from pathlib import Path

root = Path('.')
inputs = root / 'inputs'
outputs = root / 'outputs'
shutil.rmtree(outputs, ignore_errors=True)
outputs.mkdir()

# 1) copy candidate
cand_src = inputs / 'previous_candidate'
cand_dst = outputs / 'candidate'
shutil.copytree(cand_src, cand_dst)

# 2) copy learning evidence + plan
shutil.copyfile(inputs / 'previous_learning_evidence.json', outputs / 'learning_evidence.json')
shutil.copyfile(inputs / 'previous_candidate_plan.json', outputs / 'candidate_plan.json')

# 3) baseline snapshot + failure reasons
hist = outputs / 'validation_history' / 'rev0_baseline_previous_candidate'
hist.mkdir(parents=True)
shutil.copytree(cand_src, hist / 'candidate')

fb = json.load(open(inputs / 'validation_feedback.json', encoding='utf-8'))
failures = {
    'snapshot_of': 'inputs/previous_candidate',
    'reason': '上一自动候选在独立验证中未通过；快照用于局部修订前留档',
    'q18_report_evidence_unverifiable': {
        'scope': '全部6个有效开发用例及original_recovery（invalid两例通过）',
        'detail': 'Q18 status=UNKNOWN，unverifiable_check_indices=[5]（counting_identity）；报告文件checks含evidence但stdout摘要剥离evidence，统计证据不可复算',
        'severity': 'critical'
    },
    'content_review_findings': [
        {'id': 'CP01', 'summary': 'README请求示例与本次DEV请求逐字段相同，公共资料携带开发实例配置'},
        {'id': 'CP03', 'summary': '自检未比较cell.data_type与Excel表格定义（R09要求保持）'},
        {'id': 'CP04', 'summary': 'validate_request未拒绝schema外多余字段，与additionalProperties=false声明不符'},
        {'id': 'CP05', 'summary': '上一会话INTERFACE_LIMIT结束，未产出repair_summary.json与candidate_manifest.json'}
    ],
    'not_a_failure': {'CP02': '条件拒绝是契约合规行为，仅需表述准确，不改代码'}
}
(hist / 'failures.json').write_text(json.dumps(failures, ensure_ascii=False, indent=2), encoding='utf-8')

# also snapshot learning evidence & plan as-is
shutil.copyfile(inputs / 'previous_learning_evidence.json', hist / 'previous_learning_evidence.json')
shutil.copyfile(inputs / 'previous_candidate_plan.json', hist / 'previous_candidate_plan.json')

for p in sorted(outputs.rglob('*')):
    if p.is_file():
        print(p, p.stat().st_size)
