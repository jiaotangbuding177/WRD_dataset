import json, os

readme = '''# Excel指定字段文本脱敏技能（data_field_mask_request_v1）

## 用法

    python {skill_dir}/scripts/run.py --request <request.json> [--output-root <dir>]

- `--request`：请求JSON路径（schema见 `data_field_mask_request_v1`，必填字段：
  schema_version / input_workbook / output_workbook / report_file / worksheets / masking）。
- `--output-root`：可选隔离输出根。提供时，`output_workbook` 与 `report_file` 的
  **相对路径**改映射到该目录下；不提供时以 request.json 所在目录为基准。
  `input_workbook` 的相对路径永远以 request.json 所在目录为基准；绝对路径保持绝对。
  inputs 目录任何情况下只读。

## 请求示例

```json
{
  "schema_version": "data_field_mask_request_v1",
  "input_workbook": "dev_input.xlsx",
  "output_workbook": "dev_outputs/masked.xlsx",
  "report_file": "dev_outputs/masking_report.json",
  "worksheets": [
    {"name": "待脱敏记录", "header_row": 1, "data_start_row": 2, "data_end_row": 17,
     "columns": ["客户名称", "联系人姓名", "联系电话", "证件号码", "电子邮箱", "联系地址"]}
  ],
  "masking": {"prefix_chars": 2, "suffix_chars": 2, "replacement": "***"}
}
```

## 业务规则（契约R01-R12摘要）

1. 输入文件保留不覆盖；输出不得覆盖输入（R01/R11）。
2. 表头按完整值精确匹配且在该表头行唯一，不trim、不模糊猜测、不按列号硬编码（R02）。
3. 只处理指定sheet、行区间、目标表头列的矩形交集；不自动扫描其他范围（R03）。
4. 普通非空字符串按Unicode码点计数：长度>前保留+后保留时输出前缀+replacement+后缀；
   suffix_chars=0时尾部为空；不trim、不归一化、不删括号（R04）。
5. 长度<=前后保留之和的字符串、真空单元格、空字符串原样保留（R05）。
6. 数值/布尔/公式/日期等非文本目标原样保留并分别计数；不把数值转文本（R06）。
7. 相同字符串同参数得到相同结果；不添加撞名后缀，无实体识别或外部查询（R07）。
8. 非目标值、公式、类型、行列位置、表名与表顺序全部保持；不增删行列或工作表（R08）。
9. 字体/填充/边框/对齐/数字格式、行高列宽、隐藏状态、合并区域、冻结窗格保持（R09）。
10. 报告只含参数、计数、哈希、真实检查与未覆盖项；不含任何原值或原值映射（R10）。
11. 缺文件/缺sheet/缺表头/重复表头/行区间无效/输出覆盖输入 → exit 2 显式报错（R11）。

## 依赖

仅使用本地已安装的 openpyxl；不联网、不调用外部模型或服务。
'''
with open('outputs/candidate/README.md','w',encoding='utf-8',newline='\n') as f:
    f.write(readme)

spec = {
  "skill_id": "excel_field_mask_v1",
  "name": "Excel指定字段文本脱敏",
  "description": "按请求JSON指定的工作表、表头列与数据行区间，对普通文本做'前缀+replacement+后缀'掩码；短文本/空值/数值/布尔/公式原样保留并分类计数；精确保留其他单元格内容、类型、样式与工作簿布局；交付脱敏xlsx与不含原值的JSON报告。对应公开契约 data_field_mask_request_v1（R01-R12）及其路径附议a1。",
  "scope": [
    "输入为可读xlsx，请求符合data_field_mask_request_v1 schema",
    "目标=指定工作表内 header_row<data_start_row<=data_end_row 与指定表头列的矩形交集",
    "目标单元格为普通非空字符串时按Unicode码点做前后保留掩码",
    "报告口径：selected=changed+unchanged_text+blank+non_text+formula",
    "路径：input_workbook相对request.json目录；--output-root仅映射output_workbook/report_file的相对路径"
  ],
  "non_applicable": [
    "语义级敏感信息识别、实体识别、联系人抽取或真实外部查询（契约R07无此要求）",
    "对公式结果、数值、布尔值做脱敏（R06原样保留）",
    "撞名加编号后缀、删除括号备注、重排客户编号（R04/R07明确排除）",
    "生成含原值的对照表或把原值写入报告（R10禁止）",
    "非xlsx输入（csv/xls等）、图表/图片/透视表富对象保真、ZIP元数据与序列化顺序（未验证，属uncovered）",
    "请求结构非法（缺字段/区间倒置/表头重复/输出覆盖输入）——程序exit 2显式报错，不猜测（R11）"
  ],
  "entry_command": "python {skill_dir}/scripts/run.py --request inputs/request.json",
  "normal_path": ["parse_request", "resolve_paths", "load_and_locate", "apply_masking", "verify_and_save", "write_report", "review_summary"],
  "nodes": [
    {
      "id": "parse_request",
      "title": "读取并校验请求JSON",
      "when": "每次执行开始",
      "method": "程序读取--request指向的JSON，按schema校验必填字段、区间关系（header_row<data_start_row<=data_end_row）、masking参数范围（0..8/长度1..16）、columns内部唯一",
      "tools": ["python", "scripts/run.py"],
      "inputs": ["--request 请求JSON路径"],
      "outputs": ["内存中的合法请求对象"],
      "checks": ["schema_version==data_field_mask_request_v1", "全部必填字段存在且类型合法"],
      "next": [{"condition": "校验通过", "node": "resolve_paths"}],
      "on_failure": [{"condition": "缺字段/类型/区间/参数范围非法", "node": "error_exit"}]
    },
    {
      "id": "resolve_paths",
      "title": "解析路径与输出映射",
      "when": "请求校验通过后",
      "method": "input_workbook相对路径以request.json所在目录为基准解析，绝对路径保持绝对；无--output-root时output_workbook/report_file同基准，有则映射到输出根下；检查输出/报告路径不等于输入路径（R11），输入文件存在且可读",
      "tools": ["python", "pathlib"],
      "inputs": ["request对象", "--output-root 可选"],
      "outputs": ["in_path/out_path/report_path 绝对路径"],
      "checks": ["输出路径不覆盖输入", "输入文件存在", "记录输入SHA256"],
      "next": [{"condition": "路径合法且输入可读", "node": "load_and_locate"}],
      "on_failure": [{"condition": "输入缺失或输出覆盖输入", "node": "error_exit"}]
    },
    {
      "id": "load_and_locate",
      "title": "打开工作簿并定位目标列",
      "when": "路径解析成功后",
      "method": "openpyxl以data_only=False加载（保留公式定义）；逐个worksheet规格：工作表名精确存在；在header_row按完整表头值精确匹配每个columns条目且要求唯一（R02），不trim不模糊不硬编码列号",
      "tools": ["python", "openpyxl"],
      "inputs": ["in_path", "worksheets规格"],
      "outputs": ["每规格{表头名:列号}映射"],
      "checks": ["每个请求的sheet存在", "每个目标表头恰好命中一次"],
      "on_failure": [{"condition": "缺sheet/缺表头/重复表头/不可读xlsx", "node": "error_exit"}],
      "next": [{"condition": "全部定位成功", "node": "apply_masking"}]
    },
    {
      "id": "apply_masking",
      "title": "按规则脱敏并分类计数",
      "when": "目标列定位成功后",
      "method": "遍历行区间与目标列交集：先按xlsx类型分类（formula/blank/text/non_text，R06）；普通非空字符串按Unicode码点做mask_text（长度>prefix+suffix才替换，R04/R05），同参数同结果、不加后缀（R07）；只写目标单元格，其余不动（R03/R08）",
      "tools": ["python", "openpyxl"],
      "inputs": ["工作簿内存对象", "定位映射", "masking参数"],
      "outputs": ["修改后的工作簿内存对象", "每sheet六项计数", "内存中的预期值清单（不写入交付物）"],
      "checks": ["六项计数恒等式 changed+unchanged_text+blank+non_text+formula==selected"],
      "on_failure": [{"condition": "恒等式不成立", "node": "error_exit"}],
      "next": [{"condition": "脱敏完成", "node": "verify_and_save"}]
    },
    {
      "id": "verify_and_save",
      "title": "保存交付簿并回读核验",
      "when": "内存脱敏完成后",
      "method": "写出output_workbook（不覆盖输入）；随后真实重开输出与输入：①目标单元格值=预期掩码/原值 ②非目标单元格逐格值一致（全簿） ③字体/填充/边框/对齐/数字格式及表顺序、合并区域、冻结窗格、行列宽高一致（R08/R09） ④输入SHA256前后一致（R01） ⑤记录输出SHA256",
      "tools": ["python", "openpyxl", "hashlib"],
      "inputs": ["out_path", "in_path", "预期值清单"],
      "outputs": ["脱敏xlsx文件", "checks数组（含PASS/FAIL与真实证据）"],
      "checks": ["target_cells_match_expected", "non_target_values_preserved", "styles_and_layout_preserved", "input_unchanged", "deliverable_hash_recorded"],
      "on_failure": [{"condition": "任何核验FAIL或输出不可重开", "node": "error_exit"}],
      "next": [{"condition": "全部核验PASS", "node": "write_report"}]
    },
    {
      "id": "write_report",
      "title": "生成报告并输出摘要",
      "when": "核验通过后",
      "method": "写出data_field_mask_report_v1报告：schema_version/input_sha256/output_sha256/masking（与请求逐字段相同）/sheets（含counts）/totals（六项合计）/checks/uncovered；不含任何原值或原值映射（R10）；stdout打印JSON摘要与实际交付路径",
      "tools": ["python"],
      "inputs": ["计数、哈希、checks、uncovered"],
      "outputs": ["report_file JSON", "stdout执行/检查摘要"],
      "checks": ["报告可解析且含全部必需字段", "masking与请求一致", "报告内无原值"],
      "next": [{"condition": "报告已写出", "node": "review_summary"}],
      "on_failure": [{"condition": "报告路径不可写", "node": "error_exit"}]
    },
    {
      "id": "review_summary",
      "title": "审阅摘要并决定交付（模型判断）",
      "when": "程序正常返回后",
      "method": "执行模型审阅stdout摘要：status是否OK、各checks是否PASS、uncovered项是否需要补充人工核验；确认实际交付路径可定位；如存在FAIL或无法覆盖的特性，如实报告阻塞或声明不适用，不冒充成功",
      "tools": ["模型审阅"],
      "inputs": ["stdout摘要", "report_file"],
      "outputs": ["向用户的交付说明（含路径与未覆盖项）"],
      "checks": ["交付路径存在", "摘要与报告一致"],
      "next": [],
      "on_failure": [{"condition": "检查FAIL或产物缺失", "node": "error_exit"}]
    },
    {
      "id": "error_exit",
      "title": "显式报错退出",
      "when": "任何契约违反或核验失败",
      "method": "stderr打印ERROR原因，exit 2（请求/输入/路径错误）或exit 3（内部核验失败）；不交付任何声称成功的半成品（R11）",
      "tools": ["python"],
      "inputs": ["错误上下文"],
      "outputs": ["stderr错误信息", "非零退出码"],
      "checks": ["错误原因可定位"],
      "next": [],
      "on_failure": []
    }
  ],
  "resources": [
    {"path": "scripts/run.py", "purpose": "主入口程序：校验请求、解析路径、定位目标列、脱敏、回读核验、生成报告", "use_when": "每次执行本技能的正常路线（entry_command调用）"},
    {"path": "README.md", "purpose": "用法、路径解析规则、业务规则R01-R12摘要与请求示例", "use_when": "准备请求JSON、解释交付内容或排查错误退出码时"}
  ],
  "completion": "实际完成条件：run.py以--request成功执行，exit 0，全部checks为PASS，六项计数恒等式成立，输入SHA未变，脱敏xlsx与报告落在摘要报告的实际交付路径。未覆盖项（如实列于报告uncovered）：原生Excel视觉验证、ZIP元数据、公式重算结果、图表/图片等富对象。执行器无需强制停止；模型审阅摘要后自然结束即可。"
}
with open('outputs/candidate/workflow_spec.json','w',encoding='utf-8') as f:
    json.dump(spec, f, ensure_ascii=False, indent=2)
print(sorted(os.listdir('outputs/candidate')), sorted(os.listdir('outputs/candidate/scripts')))
print('spec valid json object:', isinstance(spec, dict), 'entry:', spec['entry_command'])