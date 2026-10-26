# WRD v6：实际过程训练数据与资源血缘

**有实际正loss数据；完整原生自主沉淀训练集仍未充分。未启动训练。**

[真实训练manifest](TRAINING_MANIFEST.json) · [详细训练计划](../../plans/20261026_lineage_training/README.md) · [数据到模型能力的因果链](../../plans/20261026_lineage_training/CAUSAL_TRAINING_RATIONALE.md) · [阶段覆盖与缺口](COVERAGE_AND_GAPS.json)

| 可训练角色 | 本地受控窗口/响应 | owned助手目标 | 正监督tokens | ≤16K | ≤32K累计 |
|---|---:|---:|---:|---:|---:|
| 历史原思考/制作修订主过程 | 106 | 106 | 182659 | 44 | 106 |
| 原生业务Actor辅助 | 43 | 178 | 128269 | 31 | 43 |
| 原生WRD核心沉淀 | 0 | 0 | 0 | 0 | 0 |

历史主集含30条原始思考，121511纯R监督tokens；覆盖真实UPDATE12、INSPECT5、READ1、TRY10、FINISH2。其余76个原历史响应包括合法代码、读取、测试、反馈后修复。5次历史run是同一企业源的版本链，和SSE的8个原企业源之一重合，106不是106个独立任务。Actor另有32个原企业源，不能用它们补WRD制作能力；默认不混入主训练，最多10%辅助loss。

公开替代投影为72个历史主响应/80147监督tokens（9原R，49445纯Rtokens）和34个Actor窗口/105789监督tokens。选择公开或受控投影，不能相加训练。[完整数据报告](ADMITTED_DATA_REPORT.json)给出每档SHA、处理tokens、完整阶段/前缀与父来源数。

## 91场追溯结论

54场有实际保护来源/确定派生资源依赖，36场仍缺具体祖先身份或运行输入证据，1场只是源闭包成立的旧业务screen且未通过协议质量；因此91场没有新增合格WRD核心正例。每项终态、消息/资源证据见[NATIVE91_AUDIT_TERMINALS](NATIVE91_AUDIT_TERMINALS.json)。缺证没有被称已核清，候选producer没有被union成确定污染。所有原消息、工具动作、失败、反馈和修订证据完整保全在受控包。

## 一条实际反馈修订因果链

旧版程序输出 → 原验证反馈 → 下一run的同SHA真实投递 → 原教师响应0753780c…的两行局修 → 实际工具exit0及新程序SHA43ab… → 后续同版本12/12开发验证。原request/response、时间、文件和验证器指纹逐项见[CAUSAL_REPAIR_EXAMPLE](CAUSAL_REPAIR_EXAMPLE.json)。10个已知失败或未证正确的raw目标保持零loss，最后成功没有追认早期坏代码。原失败仍留在修复的输入历史里。

这能为领域资源设计和反馈条件修复提供直接监督；原生A筛选、B制作、C取题/双臂效能、D合格冻结以及单次输入自主阶段控制的干净示范仍缺。历史TRY/FINISH协议不等于现行OpenClaw原生调用，写skill或READY不等合格冻结。不能仅凭这些数据承诺得到完整理想模型。

## 文件与核验

`data/`是实际公开正例数组；`controlled/wrd-lineage-process-v6.tar.gz.aesgcm`含受控正例、原始上下文/思考、资源CAS、91全部记录、父版本/反馈及历史中间审核，包内逐成员manifest不等于全部训练准入。私钥沿用本机v4文件，未上传；[解密与mask说明](../../plans/20261026_lineage_training/DATA_LOADING.md)。旧约739MB原件包保持，本轮只新增证据与数据增量。

[独立数据QA](INDEPENDENT_FINAL_DATA_QA.json)逐行重建255行的两投影、双分词器编码解码和逐token角色mask，原30条R另从原SSE逐UTF8比对。[精确保护内容检查](EXACT_PROTECTED_CONTENT_CHECK.json)对最终149个受控正例与原226/正式250长请求和附件hash核验无重叠；这不替代资源血缘，也不宣称语义近重复完全隔离。[加密交付QA](INDEPENDENT_ENCRYPTED_DELIVERY_QA.json)核包内每成员SHA、认证和无私钥材料。

14B主、8B对照的[配置](../../plans/20261026_lineage_training/TRAINING_PLAN.json)保留BF16 LoRA与分段/父任务预算，当前106主窗口一遍仅约7次acc16更新，不能把重放当新数据。原226继续禁训/调参；原生OpenClaw环境、业务Actor和工具循环不改。[质量与每个合格技能全成本](../../plans/20261026_lineage_training/COST_AND_ACCEPTANCE.md)尚需未来新源训练/闭环实测，本轮没有模型权重、GPU或新增业务调用。
