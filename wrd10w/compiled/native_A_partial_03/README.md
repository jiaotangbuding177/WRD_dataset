# A 原思考局部监督 V3

本银行替代 `native_A_partial_02`，不得叠加旧银行。仍是同一个真实原生响应、同一组3个 train 来源，未新增独立任务；不是完整 A—D 轨迹。

实际 1 序列／1 个正监督目标，完整输入 31,091 tokens，原 `reasoning_content` 正监督 2,742 tokens，比 V2 增加 2,252。全部正监督使用 0.25 multiplier，等效加权 R tokens 为 685.5；原 V2 的 0.5 权重在本替代银行下调，不重复累计。

原 R 33,083 字符保持原样。V2 的 1,477 字符与新增独立 AI 审核的 6,773 字符合并后，根 Agent 明确撤出一个22字符的过宽停止条件；最终16个范围、8,228原字符获局部信用。其余24,855原字符、正文和工具动作保持完整而 loss 为零。获批范围包括来源理解、保留歧义、带条件的候选流程与验证计划；不代表候选已实现、完整链成功、实际节省成立或内部思考忠实性已证。

`SCOPED_TOKEN_QA.json` 对完整数组、权重、owner、source split、审核边界及两个学生 tokenizer 直接重编通过。`R03_RAW_AND_MASK_QA.json` 额外核实9个响应原有证据字段不变、新旧31,091个 input IDs 全相同、所有正 token 与批准字符范围的完整 token 集精确相等、撤出句覆盖的 token 全为零 loss。只新增两项既有提取器捕获层次元数据，不改原始响应内容。

语义标签是 AI silver，未经人类专家认证。Codex 标注计算及金额为 `UNKNOWN_NOT_ZERO`；未新增原生 Teacher 会话，未加载模型权重，未启动训练。银行尚未自行写入主 manifest，由根 Agent 独立审核后选择导入。

可复现源码：

- `research/data_prep/wrd_main_v10/write_partial_reasoning_review_v3.py`
- 未改的 `extract_native_main.py` 与 `compile_main.py`
- `research/data_prep/wrd_main_v10/verify_partial_reasoning_v3.py`

原审查文件：`native_records/A_screen_narrative_01/A_PARTIAL_REASONING_REVIEW_V3.json`。新增范围原始理由保留在 `a_reasoning_review_03/REVIEW.json`；V2 和旧编译结果保留为历史。
