# 同627目标的可选预算条件视图

本profile把训练时的部分条件决策例改成显式无工具接口。**它没有产生新目标、改变OpenClaw运行环境或替代完整53目录参照。** 两个profile互斥：同一训练实验只能选择一个视图，不能把它们相加成1254个目标。

原始参照为`sft_candidates04/CANDIDATES.raw.jsonl.gz`，627条，SHA `7ca28cfbeac05315eefd89cad1899d72c91f4567ad1ae1cdc8f4ad239f6b2aee`；完整目录编译参照在`compiled04/`。原件均未修改。新raw在本目录，独立编译在`compiled_budget01/`。

## 明确选择规则

1. 122条包含原生工具意图／write的样本保留完整53目录，条件messages和工具定义不变。
2. 64条新增跨维度预算／保留政策guard负例全部保留完整53目录，避免将“没有可用工具”变成HOLD的捷径。
3. 在剩余D-only样本中，按`(bank,原始family)`分组，为每组选择目标ID字典序最小的一条保留完整目录，共39条anchor。某些family已全由工具动作代表，不再复制anchor。
4. 其余402条D-only样本使用显式条件决策用户请求，system声明无工具接口，`tools=[]`。当前状态JSON保持原样，R／D目标逐字不变；没有出现工具调用却空schema的样本。

因此新视图是225条full53＋402条短决策。全部627个目标ID、assistant消息、工具参数、来源组、0.05监督权重与原视图相同。保留完整目录的225条连input_ids与监督spans也完全一致。`VIEW_MAP.json`保存每个目标的规则、anchor及前后条件SHA。

这使用已知训练目标来构造离线条件任务，**不能在真实推理时用未知的正确答案选择工具目录**。本profile不引入推理路由器，不授权自建执行循环；实际原生任务仍按共同固定环境和真实工具配置评测。

## 实际tokenizer核验与训练工作量

全部627条重新调用14B／8B本地tokenizer并核完整IDs、offset及精确mask。各组件所有正监督token IDs与完整目录参照相同，没有删除或增加目标思考、决策或代码。

| 指标 | 完整53参照 | 可选预算视图 |
|---|---:|---:|
| 同一组目标 | 627 | 627 |
| 正监督tokens | 57362 | 57362 |
| 加权监督量 | 2868.1 | 2868.1 |
| 序列tokens | 16929495 | 6353061 |
| ≤16K | 0 | 402 |
| 16—32K | 627 | 225 |
| 最长序列 | 28277 | 28248 |

辅助数据每pass减少10576434序列tokens，约62.47%。若与现有205条真实过程各曝光一轮，未padding序列工作量由19467421降为8890987，减少约54.33%。这仍高于真实过程单独一轮的2537926，不能忽略新增辅助的计算成本。

这是实际序列工作量对比，**不是GPU小时、能耗、质量或每合格技能成本的实测降幅**。长短混合的padding、kernel、前后向和吞吐须在Spark另验。低loss权重也不会自动减少上下文前后向成本。

## 评价边界与读取

这改变了402条的输入接口与条件分布，目标相同不等于效果无损。后续须在相同真实来源、目标曝光和未见dev任务下对照full53与budget profile，尤其检查完整53原生输入下的条件决策、工具使用、HOLD／KEEP错误及成本。

本profile不能证明完整原生53工具动态rollout可用、长会话装窗、完整自主沉淀或真实KEEP成立。现有完整主训练manifest和623真实／历史目标未改。

`ALL627_DIRECT_DUAL_TOKEN_AND_MASK_QA.json`为本轮实际token／mask核验；`COST_AND_COVERAGE_COMPARISON.json`为工作量；`FULL53_REFERENCE.json`与`VIEW_MAP.json`固定来源和替代关系。编译JSONL含真实input_ids和监督spans；本子任务未生成另一套canonical二进制数组或修改课程loader，后续若正式接入需对应验证。

本轮仅CPU tokenizer／解析，无权重加载、forward、backward、optimizer update或新原生业务调用。此视图只是可选研究配置，不能与完整目录视图同时曝光后仍称目标数未变。
