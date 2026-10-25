# 原始思考、响应与历史轨迹恢复记录

2026-10-25。只读发现、原始记录机械恢复；无模型、训练、Docker或旧执行器运行。本文不含企业正文。

## 已经纠正的入口问题

旧冻结canonical不是全部原始记录的边界。旧历史清单位于`research/data_prep/wrd_training/resources/history_inventory.json`，仅列28个已知根，并明确不保证早期完整。此次另查D盘项目output与E盘skillloop_runs中138个历史根，再补查6个以teacher/SFT/任务预处理命名的早期根。

实际找到原模型`choices[0].message.reasoning_content`，以及原始SSE的`choices[0].delta.reasoning_content`。所以此前在冻结canonical未检出思考正文，不能作为用户原记录没有思考的依据。新恢复的数据使用原文和原顺序，不以新增摘要替换。

## 一、历史原始JSON请求—响应

范围：`20261018_workflow_three_arm`、`20261019_complete_workflow`及`20261019_auto_workflow_pilot`等已定位历史根。只恢复实际存在的`model_requests/<ordinal>/request.json`与`response.raw.json`。

| 原来源角色 | 完整raw请求响应对 | 含原思考的响应 | 思考字符 |
|---|---:|---:|---:|
| 业务执行/验证，实际来源角色待审 | 826 | 99 | 477608 |
| 开发Actor | 23 | 3 | 13213 |
| 历史技能generation | 113 | 2 | 50349 |
| formal明确排除 | 265 | 36 | 108447 |
| technical明确排除 | 6 | 3 | 549 |
| 合计 | 1233 | 143 | 650166 |

143条思考的SHA全部不同；这不等于143个独立技能或当前主策略训练任务。generation中2条思考分别为49942与407字符，不能据此说完整WRD只有2条思考，这只是这批已定位JSON文件的边界。

实际恢复到受控目录：

- `controlled/raw_pairs.all.jsonl.gz`：1233对，原请求messages/tools、原响应reasoning/content/tool_calls/usage及源SHA完整保留。
- `controlled/raw_pairs.nonformal.mechanical.jsonl.gz`：962对，去除formal265与technical6；语义、实际来源许可和质量仍待审，不是最终训练正例。
- `controlled/raw_run_trajectories.jsonl.gz`：146个run，全部有原input_packet、messages_final及result；143个末条raw为stop，3个仍为tool_calls，保留未完成事实。

1087个相邻raw对逐项核验：当前request.messages为下一request.messages完全相同前缀，当前response body真实出现在后续新增消息区间，1087/1087通过。原始reasoning被调用方省略于后续prompt的事实保留；不会把原来未见的思考重新倒灌成“原始历史”。

## 二、早期EWI教师的原始SSE思考

关键原入口：`output/20261015_ewi_teacher_DATA/episodes/<source>/model_calls/decision_*/response.partial.raw`及同目录`response.received.raw`、`request.raw.json`、`receipt.json`和`parsed.json`。同字节partial/received副本去重，不重复算样本。

68个去重原SSE响应流中，67个包含原思考。按SSE协议逐事件连接原字符串增量，保留包括单独单词`off`/`true`在内的实际响应片段，不能把响应片段误当配置枚举删除：

- 原思考**1301758字符**，220466个非空reasoning增量；这些增量不是220466个训练样本。
- 原输出content共230142字符；268466个可解析原JSON帧。
- 63流有`[DONE]`、finish及usage；这63流的重建content与旧`response.json`逐字相同。
- **67个旧response.json都没有保留原流里的reasoning_content，原SSE仍在。** 因此本轮从SSE补回，而不从结果反推思考。
- 机械完整53条（其中52条有思考），保留805621思考字符；5条无DONE，10条finish=length，11条无最终content/toolcall，拒绝原因有重叠。
- 来自10个原会话的67个EWI决策流，另1个M5调用；不能当成68条彼此独立企业来源。

进一步将10个原会话ID逐一回查旧`data/construction_sources.jsonl`及当前1107企业来源：10个全部对应真实原来源；旧教师清单中8个属于evolution、2个属于evaluation。evolution为55流（45机械完整），evaluation为12流（7机械完整），另M5来源依赖未明。因此**用于进一步训练审核的来源隔离机械池为45条、684930原思考字符**，不是53条。历史evaluation及M5未自动进入训练。

新增`controlled/sse_reasoning_pairs.evolution.mechanical.jsonl.gz`和`sse_source_split.labels.jsonl.gz`逐ID绑定原source行号/SHA及原leakage_component；未改写已经冻结的68全量/53机械收据。SSE_SOURCE_SPLIT_EVIDENCE.json与SSE_SOURCE_SPLIT_OVERLAY_REPORT.json分别记录原划分和实际投影。source ID相同不证明独立泛化；旧EWI语义还需对齐现行WRD职责，不能将历史已废弃的生命周期目标当当前正例。

实际原运行结局也已全量核验：45条逐个action_id及proposal回查原decision_transcript，17 OBSERVED、14 APPLIED、2 FINISHED、12 REJECTED。其中3条arguments不是object，真实执行器拒绝。12条拒绝动作不能直接监督为正确行动，应保留为错误历史并利用真实后续修复。33条只是与原运行结果相容的动作候选，APPLIED不等于业务正确。`SSE_ACTION_OUTCOME_AUDIT.json`及受控`sse_action_outcome.labels.jsonl.gz`逐条给原状态、错误、源SHA与JSON pointer。

另预先固定六个不同来源、覆盖READ/FINISH/INSPECT/TRY/UPDATE的语义样本，完整阅读原思考、原系统目标、用户要求及当前状态/输出/实际结局。`SSE_SEMANTIC_SAMPLE_REVIEW.json`记录：4条有可转移的过程信号但需要现行工具协议投影；1条明确拒绝动作只作失败修复材料；1条需厘清用户调整场景与真实测量值的事实边界。六例均在做工作流/资源/试做/停止推理，并非个人或组织采纳流程。发现长篇反复规划、未来执行与已观察事实混淆风险、READY只指结构试用准备、synthetic材料身份等重要限制。审阅不覆盖所有嵌入业务历史/领域正确性，不能外推45条全为语义正例；AI审阅不是人工gold，本任务不自动准入训练。

受控输出：`sse_reasoning_pairs.all.jsonl.gz`、`sse_reasoning_pairs.mechanical.jsonl.gz`及`sse_event_order.index.jsonl.gz`。每个重建span对应原文件行号、增量SHA和字符位置；这是机械重建原模型响应，非AI补写。原请求、parsed/receipt结果及源SHA同时保留，后验结果不注入早期request。原历史EWI/自建条件显式标明，不能冒充现行原生OpenClaw执行。

## 三、仍需明确的边界

138根初扫覆盖7141个匹配文件的元数据，实际解析6222个去重文件/205301个JSON对象；formal/control根只做元数据盘点。匹配范围为request/response/events/trace/trajectory/transcript/capture/model_calls/journal/proposal/llm名称下的JSON/JSONL/NDJSON/RAW/LOG/TXT；初扫83条解析失败保留计数。它不是对任意命名、压缩、数据库或SDK会话存储的穷尽证明。

额外6根查1609文件，显式解析SSE、JSON、JSONL、NDJSON，跳过已编译token、发布副本和技术验证目录，避免把派生品当新原记录。旧construction_sources与完整企业来源可见对话也是输入证据，但不能将业务会话里的assistant文本统一改标为沉淀教师思考。

初扫还定位247个去重历史原生session_events文件。随后实际按源SHA和真实原生session id与冻结1763会话逐项对照：150已经存在；**97个真正新增原生会话、2288个助手目标**已恢复到`controlled/historical_native_sessions.jsonl.gz`，不清洗任何reasoning/message字段。87个有当时原system及工具schema；新增原生会话中未检出显式reasoning块，但可见说明、工具动作和结果完整保留。

新增97会话分层：make26（957助手目标）、screen2（96）、review4（209）、来源角色待核31（663）、明确正式T任务30（350）、technical4（13）。即新增32个明确沉淀角色候选，1262个助手目标，仍不是已核正确正例。新原生会话加原母表为1860唯一原生会话，不能再加上150个重复或把历史raw自建run混为同一原生会话单位。正式/technical排除训练，unknown保留待审；旧环境证据单列，不把历史价值一律归零。源SHA前后不变，HISTORICAL_NATIVE_RECOVERY_REPORT.json绑定脚本/原始来源/输出哈希。

SDK层另有`.codebuddy/projects`、sessions、traces和logs；ACP中agent_thought_chunk经sink转reasoning_content，并存在仅用于UI进度的reasoning流，后者不能混为推理。该层由独立任务继续按已知WRD session/request标识追溯。本报告不宣称所有原始思考已全部找到。

## 原始证据与验证

计数及SHA见`output/20261025_wrd_reasoning_recovery_v4/`下RAW_SOURCE_DISCOVERY.json、RAW_REASONING_PAIRS_AUDIT.json、RAW_RECOVERY_REPORT.json、EXTRA_TEACHER_SOURCE_DISCOVERY.json和SSE_REASONING_RECOVERY_REPORT.json。脚本均在`research/data_prep/wrd_training_fullchain/`，实际运行退出0、语法检查通过。

所有恢复项区分mechanical_usable与semantic_approved/training_admitted；后两者本任务不自动设真。原始记录未修改，新正文保留受控，原始来源SHA前后核验一致；本报告不是“数据足以保证最终自主能力”的效果结论。
