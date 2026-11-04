# Process lane batch02 closure

本目录是离线数据整理和有界资源 QA 的产物，不能单独视为主训练清单。原 process v1 及其 17 个候选保持原样；根任务负责独立审核、双 tokenizer 编译、保护扫描和最终准入。

## 实际覆盖

- 原待审 **576 / 576 owner，130 episode** 已逐项形成内容裁定：每项保留原消息 index、实际任务、具体动作/公开文字、必要观察和缺陷原因。不是将关键词类别改名为人工审读。
- 完整 **1321 个唯一 owner** 的 v2 账本在 `OWNER1321_DISPOSITION09_v2.jsonl.gz`。新隐私闭包覆盖 42 owner；最终状态计数见 `FINAL_1321_LEDGER_REVIEW.json`。
- v2：172 新 dev/test 隔离，42 新 protected 闭包隔离，526 原 read/list 上下文，407 内容审读后上下文，139 具体缺陷 HOLD，17 新完整 view，17 原完整候选，1 原参数错误，共 1321。
- 这不意味着 555 原 read/list 或每一份长程序的全部业务语义都经过完整验证。对于 HOLD，已定位的具体缺陷足以排除整项正向监督；上下文和完整原文继续保留。

## 交给根任务的最终编译输入

1. `SCOPED_CANDIDATES_FINAL14_v2.jsonl.gz`：9 个原样动作、1 个真实官网搜索恢复、4 份完整正文资源。
2. `SCOPED_ADDITIONAL_CANDIDATES03_v3.jsonl.gz`：真实图像颜色探针、Jane/285/1% 翻译、完整地址翻译。

每项都有完整 `messages/tools/metadata`、原任务、实际先前反馈、资源依赖、独立 packet。原 target 和工具参数值保真。新增功能委托为整理者标注，明确区别于原生历史输入；原公开说明也不冒充内部思考。

四份正文保留全文，仅对错误条数、越界存在性断言、未证价格/安全判断及错误来源编号设置精确 loss0 区间。66e 对 `exec.command` 内无输出的重复循环、无用导入及错误注释给精确 loss0；原命令仍完整保留。区间使用原字段 Unicode `start/end/text_sha256`，整字段 SHA 和 target tool-call ID 同时保留。边界相交 token 的最终排除由根编译器执行。

`CANDIDATE19_EXPLICIT_RESOLUTION.json` 给出最初 19 个 scoped 提议的逐项收口：17 份完整 view 交根最终准入；1 份招聘海报 renderer 命中 protected 来源，整组件隔离；1 份八镜头提示词漏掉真实修订要求且靶数前后不一致，具体 HOLD。没有悬空的“候选名代替正文”。

## 可复核证明

- `FINAL17_SOURCE_AND_MASK_VALIDATION.json`：17 个 view 的工具参数与原 native message 完全相等、原 packet SHA 相等、所有字符区间准确且不交叠、前因 index 严格早于 target；这不是语义或 token 准入结论。
- `CANDIDATE_FINAL14_v2_TRANSFORM.json`：根/peer 指出的两个精确补充 mask，以及 af98 由原消息0恢复的 helper CLI 环境说明。环境声明只支持可尝试调用，不预判服务成功。
- `resource_qa03/EXECUTION.json` 和 `resource_qa03/workspace/qa_outputs/RESULTS.json`：固定镜像 `sha256:97a0f55bec1ef293c15ddd5a17cc843050387bd2369dcf2fd388b1afd40810a2`、CPU、network none，无模型/凭据。66e 完整原命令与实际原图回放，14 行测量数据与原反馈一致；PIL 区域 resize 的结果是代表色，不是逐像素算术平均。两份翻译分别149/73字节，按原参数落盘 readback 相等。没有据此授整个业务交付或完整 skill 成功金标。
- `CONTRAST_NUMERICAL_DEFECT.json`：对历史白字/青绿背景可读性断言的具体离线算术复核。

本 lane 新增内部 R 监督 **0**，完整自主沉淀/合格 KEEP 金标 **0**。本轮 Teacher/Actor 调用及训练均 **0**；整理和有限 CPU 资源 QA 成本为 `UNKNOWN_NOT_ZERO`。本目录提供可追溯、可裁剪的局部监督，不保证单凭这些数据学会完整自主沉淀。
