# 检查点10：上下文覆盖与原生执行就绪度

日期：2026-10-31。本文只公开数量、方法、来源校验和边界，不包含企业会话正文、原思考全文或凭据。

**结论：当前训练视图的core7长度通过，不等于完整53工具的原生部署已通过。** 新增29条均能在其既定训练目录下装入32K；保持相同消息而改为真实full53目录后，18条完整序列超32K，全部29条输入都无法在32K内预留8192输出。训练数据交付与完整自主执行就绪度必须分别报告。

## 数据及审计范围

活动主集为623个目标，manifest SHA为`9aace2dc6b39d0dde3bafbf9f7f3d6763e485609017dd70a5c40c17a2c30277e`。本审计只测其中本轮新增的29条视图，并另测67份已有兼容API原请求输入；29和67不能相加当新增训练样本。没有修改主manifest、训练目录、mask、历史原件或评测边界，没有权重加载、推理、反向、训练或新增业务会话。

训练core7为`ls/read/write/edit/apply_patch/exec/process`。这些是明确的学生工具目录视图；本项目完整原生环境另有53个工具定义及原生skills发现、读取和会话循环。将7个定义投影为53个定义，只是用于测量静态长度的目录替换，不是原生Agent运行，也不是原完整请求的恢复。

## 测量方法

- 每条新视图的53定义均取自其真实`tool_schema_provenance`，核SHA并逐定义确认原core7是其子集。没有凭名称补造工具schema。
- 使用固定14B／8B资产的两套本地HF tokenizer，每个渲染profile都分别实际调用，两个模型各250次，逐次token IDs相等。没有用一套IDs复制成另一套结果。
- 使用当前声明的Qwen因果模板变体。主input口径为`add_generation_prompt=True, enable_thinking=True`的assistant-header前缀，与含非空R的完整目标保持真实渲染前缀关系；完整序列保留全部当前目标，包括零loss的R或错误上下文。
- 另测`enable_thinking=False`的空think预填输入。本批逐行多4 tokens，覆盖结论不变；它不冒称与非空R目标具有相同前缀。
- 原67份请求保留原53定义和完整过去消息／明确记录的过去R，按同一Qwen模板只重渲染输入，不追加本次响应。不裁过去、不摘短R；多text block完整以换行连接，缺失R显式置空，避免将代码中的think标记误作思考。

## 静态长度实测

16K和32K分别指16384和32768 tokens。下表是两模型各自真实tokenize后的共同结果。

| 对象及口径 | 数量 | 最短／中位／最长tokens | ≤16K | 16K—32K | >32K |
|---|---:|---:|---:|---:|---:|
| 新29：当前core7完整序列 | 29 | 3717／9143／29719 | 23 | 6 | 0 |
| 新29：当前core7仅输入 | 29 | 2331／9102／28229 | 23 | 6 | 0 |
| 新29：full53静态profile，仅输入 | 29 | 27291／34062／53189 | 0 | 11 | 18 |
| 新29：full53静态profile，含完整目标 | 29 | 28677／34103／54679 | 0 | 11 | 18 |
| 原67：原53目录＋完整请求消息，仅输入重渲染 | 67 | 32342／54891／89204 | 0 | 2 | 65 |

新29每行从core7改为full53，完整序列都增加24960 tokens；增加的是工具目录，不是新增经验或新增正监督。该子集结论不能外推为全部623条的full53覆盖率。

## 输出余量与完整过程

| 输入口径 | 32K内可再留8192输出 | 32K内可再留32768输出 |
|---|---:|---:|
| 新29：当前core7 | 28/29 | 0/29 |
| 新29：full53静态profile | 0/29 | 0/29 |
| 原67：full53原请求输入重渲染 | 0/67 | 0/67 |

full53两批输入在16K内也均无法装入。预算计算只适用于input列；完整序列已经包括当前响应，不能把complete值当输入再加输出后混报覆盖率。逐行审计同时保存负值可见的剩余窗口，以及input＋8192／32768的所需窗口。

纯算术上，新29最坏53189输入需要61381窗口才能再留8192输出、85957才能再留32768；原67最坏89204输入分别需要97396／121972。**这些数字不证明64K／128K可用。** 固定模型revision的实际配置、模板／位置编码、训练与服务实现、峰值内存及精度均未由本次审计验证。

旧26个组件评测full53初始26671—29576的原件和QA保持不变，QA SHA为`6278282c833e9b748d0e197b0bc0c61812a08dc7776a7545d1255035c26d051f`。初始输入放得下，不代表后续探索、工具返回、修订、等待恢复和终态都能装下；完整rollout的动态未来长度仍未知。

67份Qwen重渲染计数也不是原Teacher的tokenizer计数或计费用量，不覆盖任何历史账单，不据此估算训练GPU小时或每个合格技能成本。

## 后续仍需验证的原生与Spark条件

1. **工具及运行协议一致。** 后续需确认学生服务实际暴露的工具定义、参数ABI、system、R处理和训练模板一致，并验证原生skills真实发现及实际读取。core7的JSONL可编译，不能替代full53服务验证。若考虑缩减或按需暴露目录，只能使用经验证的OpenClaw原生机制，按同版设计登记公共配置并保持各组一致；不能临时改某组接口使其装窗，不能自建另一套Agent循环或注入skills全文替代原生读取。
2. **窗口与动态预算。** 需对真实原生请求逐次核完整输入、输出预留、失败重试及父子会话预算，保留所有费用和未知用量。若考虑更长窗口，应先验证固定模型及实现是否支持，再测完整过去与未来增长，不能以本表静态算术宣布完成自主A—D。
3. **ARM64／GB10兼容。** 用户提供的Spark为ARM64、GB10和共享统一内存。本轮CPU tokenizer审计不验证Spark上的镜像、PyTorch／CUDA／attention二进制或可分配内存。后续需分别核arm64软件、固定依赖与模型配置，再按既定授权做真实内存和吞吐检查；不默认依赖未经验证的量化或attention实现。
4. **计算边界。** T0静态核对不加载权重；T1加载／forward是推理计算；T2 backward或一次诊断update已经属于训练计算，即使不保存checkpoint。本轮未执行这三类Spark验证，不借“验机”启动训练。后续原生技术预检／业务采集及训练执行按各自既定范围处理。

完整自主沉淀、真实技能效用、独立Q和合格KEEP仍需实际证据。静态目录展开、组件测试及tokenizer成功均不授予这些结论。

## 证据与交付位置

- [本地完整审计说明](D:/skillloop/output/20261031_wrd_curation10/context53_audit10/README.md)
- [逐行新29 profile](D:/skillloop/output/20261031_wrd_curation10/context53_audit10/NEW29_FULL53_STATIC_PROFILES.json)
- [逐行原67输入profile](D:/skillloop/output/20261031_wrd_curation10/context53_audit10/ORIGINAL67_FULL53_INPUT_PROFILES.json)
- [机器摘要](D:/skillloop/output/20261031_wrd_curation10/context53_audit10/CONTEXT53_CANONICAL_SUMMARY.json)与[静态审计QA](D:/skillloop/output/20261031_wrd_curation10/context53_audit10/CONTEXT53_STATIC_AUDIT_QA.json)
- [可复核脚本](D:/skillloop/research/data_prep/wrd_curation10/identity_context53_audit.py)
- [检查点10预定Git交付目录](https://github.com/jiaotangbuding177/WRD_dataset/tree/codex/wrd-training-data-20261025/dataset/20261031_v10_checkpoint10)：上传、实体还原和远端回读状态以该目录最终README及交付回执为准；本文不提前宣称远端交付成功。

静态QA SHA：`ae461971020cbc80a04ca4173e998a80403155d5838dfd8c95b845d3d4eb4fe4`。脚本SHA：`a7d1c5953d69a411a5d03b36c333fa971474b28dfdd32d30a5368dd486e2fa3b`。逐文件清单在本地`context53_audit10/PUBLIC_OUTPUT_MANIFEST.json`；本报告仅为公开元数据说明，不含训练启动配置。
