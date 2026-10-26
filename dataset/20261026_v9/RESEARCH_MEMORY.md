# WRD全量过程整理、结果归因与实际SFT辅助包v9

日期2026-10-26。用户要求实际大规模处理训练数据，恢复缺口；制作/修订正监督须对应技能后续试跑表现，并构建完整协调标注，与14B/8B训练计划对应。

## 用户已确认要求

原226继续隔离，不反哺训练/门槛；不启动训练。新增消融H保持隔离，不读取新消融结果反哺。本轮授权离线恢复、数据标注/转写、数组/mask、计划及Git；不是新Teacher/Actor/业务实验授权。保持同一固定原生OpenClaw循环，不实现替代Agent执行器；开发skills禁用。

## 完成的实数据工作与证据

本轮入口`research/data_prep/wrd_dataset_v9/`，产物`output/20261026_wrd_dataset_v9/`。

- `recovery/episodes.contexts.jsonl.gz`实际保全1843原native身份（旧1763＋补80）、34239助手响应与工具反馈。旧32342助手content/source_event_lines位置逐项与canonical一致。原件SHA、1609请求变体及同ID字段QA通过。原system完整6；截断/缺失没有借别场原件冒充，固定schema重建及学生接口明确区分。56同responseId原wire可读字段保全；1536 API请求/响应、257可读reasoning字段另存，历史执行条件不混称native。精确C盘历史原件保全，encrypted_content不伪造解密。
- `outcomes/`实际全121路线/1751job/1822attempt关联，326版本attempt/308内容树；271版本/真实试跑/评审边，229满足同完整版本实际消费及case通过的历史银标。145精确文件write和87证据审阅write候选均已连结果，不以done/retain/exit0给全步正loss；成本、交付、证据质量分开。
- 最初“0匹配版本”是v7索引漏review candidate目录，已按原file_index逐文件核真正候选，独立检查3 retained＋论文共25文件三方SHA相同。这个机械假0已纠正并保留历史，不拿它否定原记录。
- 700条资源恢复/原图连接包含真正反馈投影、先前生成/临时文件、固定框架及原provider消费。最终独立overlay将439原未知target核为明确保护，3149个clean prefix及来源完全不变，无held转ADMIT。最终原旧32342目标：20097保护、9096未闭合、1363仅协议clean、1786已见业务源clean。补80身份的1897响应未有同级来源闭包，保全不转正。
- 在更严格来源及结果标准下，145试跑支持文件write为144保护/1未知；87语义证据review为85保护/2未知。剩余具体未知不是“量少”推断：backfill写入及其早期route/previous技能创建链缺原producer；保留精确路径/hash和已核copy，不凭晚期全库上下文假判原初保护。相关README、OUTCOME_FINAL_REVIEW、LEGACY_ROUTE_ANCESTRY_QA及重算overlay均有逐目标引用。
- 原阶段状态实际整理3771条协调messages、234路线trace视图；精确write/cwd相对路径与祖先复核后主准入0。原状态/失败/修订全部保全，不用后来干净source列表洗掉上游已读保护预览/卡片的影响。
- 独立新增协调：867干净完整原会话/17696原消息、162纯规则边界、12完整假设控制教学trace/82决策；12类入口覆盖。明确程序标注/假设状态、非原教师CoT、非实际工具返回/试跑、非真实自主任务。33长入口保留原文但不截断入32K。完整规则trace的版本继承语义另外复核，旧版本保留，更正用新文件。
- 867会话及112附件别名已实际按原stages native路径合同实化；93唯一附件417951031字节在原Git dist的12分片逐对象核过，非缺材料而省略。新raw来源4833对象中，1857与附件等对象合计838170157字节在既有包实际核验；82.27MB raw原件增量另封实字节，避免重复传输。缺件/合成/未核附件不伪造。

## 真实训练文件和训练计划

实际`sft/`提供messages、input_ids、逐assistant owned spans、权重、原件来源；`dataset_loader.py`可重建labels=-100/weights及正确causal shift，未运行模型forward或训练。14B/8B两套真实tokenizer均逐最终序列重编码，原prefix/R、hash、边界、mask与来源分组由独立QA核；长目标不静默截断。父源码快照及分阶段编译/输入SHA保留，非只交索引。

最终数量以`FINAL_DATA_STATISTICS.json`和`TRAINING_MANIFEST.json`为准：1968序列，train1660/dev160/test148，train2090助手目标。960 native序列只有1368 read/ls操作辅助（44651监督tokens），不授予技能正确性；其余是明确新增协调监督。当前新原生主监督的原R正loss0，但所有原R载体保全；旧v6 106响应/30原R/121511 R tokens保持历史不同条件引用，未被删除或自动混成新主集。

封包前v2初冻结历史口径（被下方10目标更正替代）：1968序列/2456批准assistant目标/10188742输入tokens/490535监督tokens；train1660序列/2100目标/8528931输入/404141监督。旧QA SHA50ae35…对应此旧mask。v2控制trace因果review SHA3d46b3da85bfd1962ba8c2e295c349673674acbb609fc5b6dda1084da6978513仍有效。旧v1修订后version回v0问题已在独立v2恢复状态继承和新版本验证失效规则，旧原件/更正仍保存；68同版连续转移、2次新版失效、5freeze交付转移独审通过。不等于总体语义金标或闭环收益。

最末质量更正：查到10个只读辅助正owner实际q.observed_tool_failure=True。即使只教格式，也不默认模仿未经认可的报错探测；撤销它们全部353监督tokens（F60+A293），动作/错误返回/后续修复均仍在原上下文，未宣称它们都是领域错误。最终1968序列/2446批准目标/10188742输入/490182监督；train1660/2090目标/8528931输入/403788监督，dev/test不变；native960/1368/44651，coord1008/1078/445531。TARGET_QUALITY_ERRATA SHA07a3102e63deefa2a8707d6127fdf49d469e48455ca1d64d32f89264b971713e；原token/messages/rendered/source/split/协调字节不变。旧数据/封包/QA保存publication_history，未推送旧包。数据QA新增每个read-only正owner原观察不得工具失败的门；父编译receipt旧byte-identical字段是历史，当前新增postcompile mask erratum明确其例外。

`CLEAN_RECOLLECTION_PLAN.json`给出每类一个train-only原输入起点、剩余匹配池、原生路径与最多120阶段的有界补缺草案，不保证12技能/最终足量；不得将同类别误作同工作流。它只是待另行授权的原生制作/试跑建议，未执行，当前静态dev/test、原226和新H不投制作。

本轮**完整WRD制作、修订、语义评审主监督0**，不能拿辅助规模交差为理想目标足量。全量处理/数组技术QA完成与主训练准入分开；不建议仅用辅助数据付GPU做正式WRD SFT。当前恢复不能在保持原226评测边界时把受其影响的成功教师记录改名转正。

训练方案沿用锁定Qwen3-14B主/8B对照、Spark候选BF16 LoRA r32/alpha64、micro1/accum16、lr1e-4、checkpointing、互斥16K/32K。来源群先切分，metadata/未来试跑不能作为模型输入。结果支持单文件只可授予已证明内容，不自动覆盖同轮其它动作/思考；错误未知留上下文。只读/入口辅助0.1，规则/假设trace0.05，不因单bank权重归一化抵消。推理模板为声明变体，原生接线和Spark内核/吞吐尚未实测。

真正缺的是干净来源下实际原生制作→试跑→反馈→修订闭环主证据。后续若获授权，应只补具体缺口，再以学生自己历史/真实工具验证完整TSR、独立五维Q、正确停止/复用、全模型工具重试与人工回退费用/合格技能。当前控制静态dev/test不冒充完整闭环评测；没有训练后的效果/降本保证。

## 更正、边界与交付

- 完整规则源码哈希0aa973…是LF文本，原CRLF字节为0fe620…，无代码被别的工作更改的证据；完整LF源码已冻结，口径overlay保留。此前疑为并行修改的推断撤回。
- QA一次错误地比较旧宿主路径版入口而非native_paths版，已改按实际输入pin逐项核。旧报告保留，新QA与实际文件/SHA及输入集合绑定，不能用旧PASS认证新数组。
- 本轮0训练/权重/GPU forward、0新Teacher/Actor/业务试跑；未改生产pipeline或原生执行环境、预算和在途消融。双稿5.0.35/ALG-20261026-08仅离线数据接口，消融仍按原冻结5.0.33。前版快照在history/5.0.34/wrd_dataset_v9_20261026/。
- Git目录`dataset/20261026_v9/`交付实际SFT与完整恢复证据认证加密实包、公开计划/清单/QA/loader。密钥沿用本地既有v4，不进Git；个人原文/可能含凭据的历史不公开散落。旧数组/归档不改；既有93附件字节按已核dist引用。远端提交/逐对象回读在完成后追加，未上传前不冒称已交。
