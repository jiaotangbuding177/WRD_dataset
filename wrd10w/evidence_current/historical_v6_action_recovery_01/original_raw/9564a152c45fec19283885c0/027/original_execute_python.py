import json, hashlib, os

def sha(p):
    return hashlib.sha256(open(p,'rb').read()).hexdigest()

manifest = {
  "manifest_id": "candidate_manifest_excel_field_mask_v1",
  "contract": "data_field_mask_request_v1",
  "frozen_candidate_files": [
    {
      "path": "scripts/run.py",
      "purpose": "主入口程序：请求校验(R11)、路径解析(附议a1)、表头精确定位(R02)、矩形交集脱敏(R03-R07)、保存后回读核验(R08/R09)、生成不含原值的报告(R10)、显式报错",
      "sha256": sha('outputs/candidate/scripts/run.py'),
      "evidence": {
        "dev_run": "python outputs/candidate/scripts/run.py --request inputs/dev_request.json --output-root outputs/development_delivery → exit 0，全部checks PASS",
        "dev_summary_log": "outputs/validation_history/dev_run2_after_fix_stdout.log",
        "revision_history": "第1次运行styles_and_layout_preserved真实FAIL（StyleProxy未委托__eq__），快照见snapshots/run_v1_style_fail.py；仅修复style_sig的样式解包方式后重测通过"
      }
    },
    {
      "path": "workflow_spec.json",
      "purpose": "workflow规范：skill_id/name/description/scope/non_applicable/entry_command/normal_path/nodes/resources/completion，节点含方法/工具/输入输出/检查/失败返回",
      "sha256": sha('outputs/candidate/workflow_spec.json')
    },
    {
      "path": "README.md",
      "purpose": "用法、路径解析规则、业务规则R01-R12摘要与请求示例",
      "sha256": sha('outputs/candidate/README.md')
    }
  ],
  "excluded_from_resources": [
    "outputs/learning_evidence.json（历史会话学习证据，非消费资源）",
    "outputs/validation_history/（开发验证代码、测试工作簿、失败快照与运行日志）",
    "outputs/development_delivery/（开发答案产物）",
    "inputs/conversation.json及inputs/dev_input.xlsx（原始会话与开发附件）",
    "原值映射/对照表（契约R10禁止，未生成）"
  ],
  "execution_evidence": {
    "dev_delivery": {
      "command": "python outputs/candidate/scripts/run.py --request inputs/dev_request.json --output-root outputs/development_delivery",
      "exit_code": 0,
      "output_workbook": "outputs/development_delivery/dev_outputs/masked.xlsx",
      "report_file": "outputs/development_delivery/dev_outputs/masking_report.json",
      "input_sha256": "b6a4e5d4f3ef2d83ad739eb2731668835c453d6acb8588addab6bfbcd16e7f8b",
      "totals": {"selected_cells": 96, "changed_cells": 84, "unchanged_text_cells": 12, "blank_cells": 0, "non_text_cells": 0, "formula_cells": 0},
      "independent_recheck": "独立重开输入/输出按请求自行推导预期掩码比对96个目标单元格全部一致；G列(应收金额)与'材料身份'sheet逐格未改动；报告文本扫描0处原值泄露"
    },
    "boundary_tests": {
      "script": "outputs/validation_history/edge_case_tests.py",
      "result": "31项检查全部PASS（exit 0）",
      "logs": ["outputs/validation_history/edge_case_tests_run1.log", "outputs/validation_history/edge_case_tests_run2_after_fix.log", "outputs/validation_history/testdata/run_*.log"],
      "coverage": ["短文本(≤前后保留之和)原样保留", "真空单元格与空字符串", "公式单元格保留及data_type=f", "数值/布尔非文本分类", "列换位(同表头不同物理列位)", "不trim(首尾空格计入码点)", "suffix_chars=0及自定义replacement", "不同字符串同掩码不加后缀(R07)", "括号内容不删(R04)", "样式/合并/冻结/列宽保持(R09)", "默认输出路径相对request目录", "错误输入: 重复表头/缺表头/缺sheet/输出覆盖输入/区间倒置/错误schema_version全部exit 2"],
      "test_revision_note": "第1轮2项FAIL均为测试预期错误(未计入R04不trim、误判C3不在区间)，测试脚本已修订并留快照，候选程序未因此改动"
    }
  },
  "unresolved_issues": [
    "未在原生Excel应用程序中做视觉渲染验证（样式结论来自openpyxl属性级比对）",
    "图表、图片、数据透视表等富对象保真未验证，超出本次契约范围",
    "公式仅按xlsx定义保留，未做重算结果验证（契约R06明确不对公式结果打码）",
    "历史会话无获认证原生工具执行记录，学习证据仅基于语义痕迹"
  ]
}
json.dump(manifest, open('outputs/candidate_manifest.json','w',encoding='utf-8'), ensure_ascii=False, indent=2)
print('manifest written')
print(sorted(os.listdir('outputs')))
print(sorted(os.listdir('outputs/validation_history')))