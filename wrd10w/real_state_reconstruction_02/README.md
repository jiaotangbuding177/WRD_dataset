# 功能状态视图02（独立候选，待根Agent复审）

02移除了01输入中的研究旗标、same-input免责声明、作者声明、原callID和Windows捕获路径／SHA对象。它们全部保留为record metadata。学生输入直接给出总目标、权限、预算未知项、当前状态、功能反馈及资源。

01整目录逐项SHA前后完全相同，没有修改。02与01是同3个动作owner的替代视图，**不能同时激活或相加loss**。主ACTIVE、双设计、计划和native C工作区均未变。

| 目标 | 01 tokens | 02 tokens | 监督tokens |
|---|---:|---:|---:|
| 原CLI复现 | 14,431 | 13,317 | 332 |
| 局部修订 | 16,490 | 15,330 | 1,676 |
| 修后复测 | 15,270 | 14,079 | 306 |

02实际共42,726输入tokens／2,314监督tokens（203新AI银标理由＋2,111原逐字节动作），全部≤16K；global `loss_multiplier=0.5`。双tokenizer三条均独立调用相等，无held、无截断。3来源仍归原1联合群／train，1父链、3不同实际动作owner，未增加独立业务来源。

10份动作所需的完整validator／反例／原失败报告文本、原实际观察内容、原理由和工具动作都与01逐字节相同。功能路径及资源版本SHA保留。原反馈文件的`schema`、`origin`、`parent_job_id`、`parent_job_sha256`四项来源元信息移到metadata，其余功能字段完整保留为user的独立检查反馈段；该段不冒充原文件全文。反馈原全文和其余176项来源／独审证据仍在收据闭包。

新增理由仍明确归属`NEW_AI_SILVER_AUTHOR`，成本`UNKNOWN_NOT_ZERO`，这些声明只在metadata。真实截点、原R、实际工具schema、原动作SHA和未来同版本21＋8信用继续保全；未来结果未进入输入。局部验证不等于技能整体质量、业务效果或完整自主链批准。

主要产物：

- `real_state_tasks.jsonl.gz`、`records/`：完整功能状态训练记录。
- `FUNCTIONAL_VIEW_PROJECTION_REVIEW.json`：字段投影及每份文件／观察保留证据。
- `FUNCTIONAL_SOURCE_CLOSED_QA.json`：176项原件、功能文本、来源和动作核查。
- `VIEW_01_IMMUTABILITY_CHECK.json`：01全目录不变证明。
- `COMPILED_BANK_QA.json`：实际数组、mask、权重及双分词器结果。
- `EXPOSURE_OWNERS.json`：同owner视图互斥注册。
- `../compiled/real_state_repair_02/`：实际编译分片与报告。

本作者自审通过，根Agent仍需独立复审后决定主准入。没有模型调用、原工具重放或训练。
