# full53静态上下文审计：29新状态与67原API输入分账

本轮只加载本地HF tokenizer，14B／8B各实际调用250次；两者逐次token IDs相等。没有权重、forward、backward、Agent或业务调用。主manifest仍`9aace2dc6b39d0dde3bafbf9f7f3d6763e485609017dd70a5c40c17a2c30277e`，623目标不变；29行已经属于主集，不是本审计新增样本。

## 静态实测

主input口径使用当前Qwen因果模板的assistant-header生成前缀，`add_generation_prompt=True, enable_thinking=True`；它是完整含R目标的精确渲染前缀。保存全部过去消息、原R及完整目标，不裁输入。每行53工具来自其真实`tool_schema_provenance`，core7逐定义核为该catalog子集。展开工具目录是明确的counterfactual profile，不能称原完整native请求。

| 口径 | 数量 | 最短／中位／最长tokens | ≤16K | 16—32K | >32K |
|---|---:|---:|---:|---:|---:|
| 新29当前core7完整序列 | 29 | 3717／9143／29719 | 23 | 6 | 0 |
| 新29当前core7仅输入 | 29 | 2331／9102／28229 | 23 | 6 | 0 |
| 新29改为full53，仅输入 | 29 | 27291／34062／53189 | 0 | 11 | 18 |
| 新29改为full53，含完整目标 | 29 | 28677／34103／54679 | 0 | 11 | 18 |
| 原67兼容API请求，保留全过去＋原53工具，仅输入 | 67 | 32342／54891／89204 | 0 | 2 | 65 |

同一新state从core7改为full53后，完整序列每行都增加**24960 tokens**；新增的是工具目录，不是更多经验或新增监督量。当前29的实际训练目录、mask及core7编译结果不改。

## 输出余量

| 输入口径 | 32K内能留8192输出 | 32K内能留32768输出 |
|---|---:|---:|
| 新29当前core7 | 28/29 | 0/29 |
| 新29full53 profile | 0/29 | 0/29 |
| 原67full53输入重渲染 | 0/67 | 0/67 |

16K内，full53两批输入均无法装下，也没有上述输出余量。逐行JSON同时报告signed剩余量、非负可输出量和input＋8192／32768所需窗口。输出预算字段只对**输入profile**解释；complete序列已经包含目标，不再将它当作输入重复加输出。人读表和`CONTEXT53_CANONICAL_SUMMARY.json`使用这一明确口径。

纯算术上，新29最坏输入53189需要61381窗口才能再留8192输出、85957才能再留32768；原67最坏89204分别需要97396／121972。这不证明64K／128K、Spark内存或长程精度已通过，也没有据此更改训练窗口。

另测`enable_thinking=False`的空think预填输入：本批逐行比header口径多4 tokens，覆盖结论不变。该预填不是含非空R完整target的相同前缀，不能混称原生协议通过。

## 适用范围与原件

- 原67只是把保存的兼容API请求按Qwen14／8因果模板重渲染；其计数不是原Teacher的tokenizer或计费用量，不能覆盖原账单。
- 29新state、67原请求和旧26组件评价分开。旧26的full53初始26671—29576原文件／QA SHA`6278282c833e9b748d0e197b0bc0c61812a08dc7776a7545d1255035c26d051f`保持；初始能放下不代表完整探索rollout能完成。
- 后续工具返回、重试、修订和思考将继续增长上下文，动态长度未知。本审计没有“原生full53 rollout通过”结论。
- P4八父输入包尚不是捕获的原生system／工具／past请求，本轮没有把其文件目录仿真成一次原生输入来报告通过。
- `NEW29_FULL53_STATIC_PROFILES.json`与`ORIGINAL67_FULL53_INPUT_PROFILES.json`逐行保留来源pin、文本投影规则、rendered／两个模型IDs SHA、真实调用一致性及预算。只对多text block作完整换行拼接，缺失reasoning显式置空以防把代码中的think标记挖成思考，未丢任何过去正文。

原始实测回执`CONTEXT53_STATIC_AUDIT_QA.json` SHA`ae461971020cbc80a04ca4173e998a80403155d5838dfd8c95b845d3d4eb4fe4`，耗时33.25秒；脚本`research/data_prep/wrd_curation10/identity_context53_audit.py` SHA`a7d1c5953d69a411a5d03b36c333fa971474b28dfdd32d30a5368dd486e2fa3b`。该耗时是本机CPU审计经过时间，不是Spark训练或推理吞吐。
