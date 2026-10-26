# WRD原始过程数据地址与旧整理范围核查（v7）

本轮回答的是：生成29个skills时留下了哪些原始过程记录、地址在哪里、此前为什么只报93／106条。**已经证实此前整理的入口、角色分类和导出范围没有对齐完整pipeline；不能据此认定大部分原数据没有训练价值。**

本轮覆盖29制作主目录，并补入此前遗漏的版本迭代、前序WRD探索、原生病例/控制和交接载体。补根的语义相关性分别待核，不全部冒充29制作的独立新会话。没有启动训练或新业务模型调用，也没有将未审核记录冒充可训练数据集。原226继续隔离训练；其地址/元数据可在普查单列。

## 1. 实际核到的规模

| 计数对象 | 实际数量 | 含义 |
|---|---:|---|
| 原始企业输入会话 | 1,107 | 被WRD分析的业务来源，不是制作Agent步数 |
| 路线 | 121 | retained29 / candidate60 / rejected19 / needs_revision13 |
| 制作pipeline逻辑任务 | 1,751 | 包括筛选、准备、制作、业务试做、评审；有复用/重试 |
| attempt目录引用 | 1,822 | 当前pipeline1688＋导入历史134，不能当1822独立业务来源 |
| 旧已解析入口的原生会话上下文 | 1,763 | 64,559条消息；逐一SHA/行号核对，不是新发现全部目录的会话总量 |
| 助手响应位置 | 32,342 | 32,014个非空；不是已经审核准入的SFT条数 |
| 实际工具调用块 | 30,438 | 一个响应可以有多个工具块 |
| 最终留存技能 | 29 | 154个最终包文件，逐文件与原清单SHA一致 |
| 九通道原服务记录 | 9个事件文件 / 76,480,390字节 | 去重native_request_id共31,249；为用量/传输元数据，不能代替响应正文 |
| 首份冻结物理账 | 740,167个 / 72,628,618,635字节 | 34个不重叠根实扫；首50地址另含父根覆盖/后续支线 |
| 新补迭代/病例/控制载体根 | 119根 / 51,701文件路径 / 2,561,362,264字节 | 包含D-v10—v35、E-v11—v34与前序历史载体，旧子根重叠已剪除 |
| 独立记忆/原引用反查末批5根 | 2,288文件路径 / 79,705,856字节 | concurrency9及D/E原基础设施审计/修复，均实际存在 |
| 额外Codex辅助修复目录 | 66文件路径 / 1,162,823字节 | 与主GLM制作历史条件分列；另有一个外部原会话文件只stat |
| 截至本轮已定位地址与物理账合计 | 175根地址 / 794,222文件路径 / 75,270,849,578字节 | 后续8根受限metadata不相加，不等于全盘绝对完整或独立训练语料 |

当前合计约75.27GB，采用十进制GB和路径逻辑文件大小，不是实际分配磁盘空间或内容去重训练文本。首份72.63GB基础账中，路径规则识别的输入复制/工作区缓存约63.78GB，新增账另列。基础账按卷号/文件ID去掉3个别名后为740,164身份/72,628,618,530字节；尚未做跨集文件身份或全量内容SHA去重。

## 2. 主要原始入口与原文件结构

- 原1107会话母本：[D:/skillloop/benchmark/enterprise_input_closed_v11_20261012/有效轨迹.jsonl](</D:/skillloop/benchmark/enterprise_input_closed_v11_20261012/有效轨迹.jsonl>)（55,556,390字节，SHA与原inventory声明一致）。
- 原会话到资源绑定：[D:/skillloop/output/20261021_workflow_skill_library/source_bindings.json](</D:/skillloop/output/20261021_workflow_skill_library/source_bindings.json>)；拆分正文在同目录 `sources/<conv_id>/conversation.json`。
- D盘主控制记录、反馈、输入副本、历史版本和镜像：[D:/skillloop/output/workflow_library](</D:/skillloop/output/workflow_library>)（389,780文件路径，40,497,632,317字节）。重点入口是 `records/`、`runs/`、`prepare_runs/`、`history/`、`confirmed_snapshots/`、`selection_repair/`、`selected_followup_20261024/final/`。
- E盘真实执行attempt与工作区：[E:/skillloop_runs/workflow_library](</E:/skillloop_runs/workflow_library>)（309,821文件路径，27,706,756,303字节）。包括 `screen__*`、`prepare__*`、`make__*`、`actor__*`、`review__*` 及 `episodes/<id>/attempt_*`。
- 最终29技能原始文件清单：[D:/skillloop/output/workflow_library/selected_followup_20261024/final/29技能文件清单.json](</D:/skillloop/output/workflow_library/selected_followup_20261024/final/29技能文件清单.json>)；资源包之外仍保留制作和评审记录。

每个原attempt一般同时包含：`request.json`（当时实际输入/资源地址）、`openclaw_transport/session_events.jsonl`（原生助手消息、工具调用和工具返回）、`native_events.jsonl`（调用与用量事件）、`result.json`／`native_result.json`（执行结果），以及 `workspace/inputs`、`workspace/outputs`、修订中的脚本/模板/资料。具体存在性逐条记录，缺失时不补造。`native_events`与`session_events`不能混为同一种正文记录。

下面给出每阶段一个实际原会话地址；所有1822个attempt见完整索引。

| 旧阶段标签 | 原生会话正文地址 |
|---|---|
| 路线筛选 | [E:/skillloop_runs/workflow_library/screen__coverage-mapped_other-bf00f70b0c/attempt_1/openclaw_transport/session_events.jsonl](</E:/skillloop_runs/workflow_library/screen__coverage-mapped_other-bf00f70b0c/attempt_1/openclaw_transport/session_events.jsonl>) |
| 需求/试做准备 | [E:/skillloop_runs/workflow_library/prepare__homework-mastery-analysis__full-search/attempt_3/openclaw_transport/session_events.jsonl](</E:/skillloop_runs/workflow_library/prepare__homework-mastery-analysis__full-search/attempt_3/openclaw_transport/session_events.jsonl>) |
| 技能/资源制作与修订 | [E:/skillloop_runs/workflow_library/make__slide-explainer-video/attempt_1/openclaw_transport/session_events.jsonl](</E:/skillloop_runs/workflow_library/make__slide-explainer-video/attempt_1/openclaw_transport/session_events.jsonl>) |
| 无技能/有技能业务试做 | [E:/skillloop_runs/workflow_library/episodes/f6d67b1a9f82da83/attempt_1/openclaw_transport/session_events.jsonl](</E:/skillloop_runs/workflow_library/episodes/f6d67b1a9f82da83/attempt_1/openclaw_transport/session_events.jsonl>) |
| 评审/反馈 | [E:/skillloop_runs/workflow_library/episodes/7323cbbfe68eb894/attempt_1/openclaw_transport/session_events.jsonl](</E:/skillloop_runs/workflow_library/episodes/7323cbbfe68eb894/attempt_1/openclaw_transport/session_events.jsonl>) |

## 3. 九并发原服务地址

来自原始服务清单 [D:/skillloop/output/workflow_library/services/current.json](</D:/skillloop/output/workflow_library/services/current.json>)（记录时点2026-10-24 22:19:11 +08:00）；九个文件均存在，读取前后SHA相同。

| 通道 | 原事件文件 | 字节 |
|---:|---|---:|
| 0 | [E:/skillloop_runs/20261021_v10_reuse_iterations/native_events.jsonl](</E:/skillloop_runs/20261021_v10_reuse_iterations/native_events.jsonl>) | 10,420,742 |
| 1 | [E:/skillloop_runs/20261021_workflow_library_parallel4/lane_1/native_events.jsonl](</E:/skillloop_runs/20261021_workflow_library_parallel4/lane_1/native_events.jsonl>) | 9,937,068 |
| 2 | [E:/skillloop_runs/20261021_workflow_library_parallel4/lane_2/native_events.jsonl](</E:/skillloop_runs/20261021_workflow_library_parallel4/lane_2/native_events.jsonl>) | 9,796,240 |
| 3 | [E:/skillloop_runs/20261021_workflow_library_parallel4/lane_3/native_events.jsonl](</E:/skillloop_runs/20261021_workflow_library_parallel4/lane_3/native_events.jsonl>) | 11,291,470 |
| 4 | [E:/skillloop_runs/20261021_workflow_library_parallel4_recovery1/lane_4/native_events.jsonl](</E:/skillloop_runs/20261021_workflow_library_parallel4_recovery1/lane_4/native_events.jsonl>) | 9,127,786 |
| 5 | [E:/skillloop_runs/20261021_workflow_library_parallel4_recovery1/lane_5/native_events.jsonl](</E:/skillloop_runs/20261021_workflow_library_parallel4_recovery1/lane_5/native_events.jsonl>) | 6,680,446 |
| 6 | [E:/skillloop_runs/20261021_workflow_library_parallel4_recovery1/lane_6/native_events.jsonl](</E:/skillloop_runs/20261021_workflow_library_parallel4_recovery1/lane_6/native_events.jsonl>) | 6,877,529 |
| 7 | [E:/skillloop_runs/20261021_workflow_library_parallel4_recovery1/lane_7/native_events.jsonl](</E:/skillloop_runs/20261021_workflow_library_parallel4_recovery1/lane_7/native_events.jsonl>) | 9,483,918 |
| 8 | [E:/skillloop_runs/workflow_library/channel8/native_events.jsonl](</E:/skillloop_runs/workflow_library/channel8/native_events.jsonl>) | 2,865,191 |

九通道共享的原入口在 `E:/skillloop_runs/20261021_T0012_native_two_arm/observed_service/src/index.js`。旧28根清单及首轮50地址均漏D盘 `20261021_v10_reuse_iterations`；本轮独审后补账33文件/1,172,454字节，并进一步发现D/E版本迭代及前序载体。清单漏根不自动等于相关所有会话没归档，须按文件/请求血缘核对。九通道ID与catalog响应身份/范围不同，不能相减推算丢失量。

## 4. 旧已解析入口中，各阶段确实有大量过程记录

| 旧目录阶段标签 | 逻辑任务 | attempt引用 | 已恢复会话 | 助手响应位置 | 非空响应 |
|---|---:|---:|---:|---:|---:|
| 路线筛选 | 64 | 139 | 135 | 996 | 955 |
| 需求/试做准备 | 260 | 349 | 329 | 3,190 | 3,098 |
| 技能/资源制作与修订 | 283 | 367 | 357 | 9,016 | 8,932 |
| 无技能/有技能业务试做 | 778 | 535 | 526 | 11,732 | 11,683 |
| 评审/反馈 | 366 | 394 | 378 | 6,803 | 6,743 |
| 旧格式待重分类 | — | 38 | 38 | 605 | 603 |

此表只复核旧已解析入口，**不是新发现全部目录的阶段总量或重标后的阶段金标**。实际原request证实导入历史有角色误分：`jd-resume-screening` 因名称含screen被误作WRD筛选，`contract-review-revision` 的业务对照执行因名称含review被误作WRD评审。134条导入记录需按实际职责重分类。job、attempt和正文计数不能相互替代。

## 5. 29个最终技能的原制作地址图

每个入口列出原业务source、逻辑job、attempt、原请求/会话/用量地址、结果/反馈、输出资源树版本和最终包文件SHA。直接job关联、screen输出关联、仅名称推测的legacy关联分别保留，不把弱关联升级为确定因果。未留存/失败/被替代任务仍在全局索引。

| 最终技能 | 直接job | 直接attempt | 含筛选/历史线索的关联attempt | 输出树内容版本 | 逐技能地址入口 |
|---|---:|---:|---:|---:|---|
| AI工具落地应用建议路线 (`ai-adoption-advisory`) | 20 | 18 | 21 | 3 | [JSON](skills29/ai-adoption-advisory.json) |
| AI新闻检索摘要路线 (`ai-news-digest`) | 21 | 19 | 32 | 4 | [JSON](skills29/ai-news-digest.json) |
| 公司/行业调研结构化报告路线 (`company-research-report`) | 6 | 8 | 37 | 1 | [JSON](skills29/company-research-report.json) |
| 课程回顾视频脚本迭代路线 (`course-recap-video-script`) | 10 | 11 | 14 | 2 | [JSON](skills29/course-recap-video-script.json) |
| 交易结构法律风险敞口分析路线 (`deal-structure-legal-risk-analysis`) | 19 | 15 | 16 | 3 | [JSON](skills29/deal-structure-legal-risk-analysis.json) |
| 通用文档审查查错路线 (`document-error-review`) | 45 | 34 | 44 | 7 | [JSON](skills29/document-error-review.json) |
| 文档分析并成审查/分析报告 (`document-review-report`) | 19 | 16 | 26 | 3 | [JSON](skills29/document-review-report.json) |
| 来信阅读与回复起草路线 (`email-reply-drafting`) | 9 | 10 | 13 | 1 | [JSON](skills29/email-reply-drafting.json) |
| 大赛与政府申报机会检索筛选路线 (`funding-opportunity-search`) | 13 | 11 | 12 | 2 | [JSON](skills29/funding-opportunity-search.json) |
| 代码提交贡献年报路线 (`git-contribution-report`) | 11 | 12 | 15 | 2 | [JSON](skills29/git-contribution-report.json) |
| 基金申报形式审查可勾选清单 (`grant-formal-review-checklist`) | 24 | 24 | 27 | 5 | [JSON](skills29/grant-formal-review-checklist.json) |
| 主题/机构介绍文稿起草路线 (`intro-document-drafting`) | 11 | 9 | 19 | 2 | [JSON](skills29/intro-document-drafting.json) |
| 岗位JD起草润色导出 (`jd-drafting`) | 21 | 19 | 25 | 3 | [JSON](skills29/jd-drafting.json) |
| 岗位JD-简历批量筛选评审路线 (`jd-resume-screening`) | 30 | 24 | 53 | 4 | [JSON](skills29/jd-resume-screening.json) |
| 记忆与文档个人画像整理路线 (`memory-profile-compilation`) | 9 | 8 | 13 | 2 | [JSON](skills29/memory-profile-compilation.json) |
| 组织架构设计与岗位配套路线 (`org-chart-design`) | 26 | 22 | 25 | 4 | [JSON](skills29/org-chart-design.json) |
| 组织架构部门职能与岗位说明书成套编制 (`org-role-description-drafting`) | 7 | 9 | 11 | 1 | [JSON](skills29/org-role-description-drafting.json) |
| 境外架构多方案法律风险分析路线 (`overseas-structure-legal-analysis`) | 25 | 22 | 29 | 3 | [JSON](skills29/overseas-structure-legal-analysis.json) |
| 专利年费合规核查与操作指引路线 (`patent-annuity-compliance`) | 24 | 23 | 27 | 5 | [JSON](skills29/patent-annuity-compliance.json) |
| 概念验证报告生成 (`poc-report-route`) | 7 | 7 | 13 | 1 | [JSON](skills29/poc-report-route.json) |
| 主题与材料PPT成稿生成 (`ppt-deck-generation`) | 9 | 10 | 18 | 1 | [JSON](skills29/ppt-deck-generation.json) |
| 现有PPT稿件内容修订路线 (`ppt-deck-revision`) | 11 | 15 | 26 | 2 | [JSON](skills29/ppt-deck-revision.json) |
| 知识库项目材料亮点汇总路线 (`project-material-integration`) | 17 | 15 | 23 | 1 | [JSON](skills29/project-material-integration.json) |
| 招聘流程设计工具包 (`recruitment-process-design`) | 19 | 15 | 21 | 3 | [JSON](skills29/recruitment-process-design.json) |
| 审稿意见回复信成文路线 (`review-response-letter`) | 7 | 7 | 11 | 1 | [JSON](skills29/review-response-letter.json) |
| 股东名册资料汇编成表 (`shareholder-register-compile`) | 16 | 19 | 22 | 2 | [JSON](skills29/shareholder-register-compile.json) |
| 主题案例检索整理讲解清单路线 (`teaching-case-list`) | 7 | 9 | 12 | 1 | [JSON](skills29/teaching-case-list.json) |
| 教学演示交互HTML页面生成路线 (`teaching-html-demo`) | 18 | 14 | 28 | 3 | [JSON](skills29/teaching-html-demo.json) |
| 主题HTML演示动画生成路线 (`web-html-prototype`) | 21 | 20 | 29 | 4 | [JSON](skills29/web-html-prototype.json) |

各技能共享筛选/资源/试做，行数不能相加当独立来源。资源树版本按内容签名区分副本，不将复制的同一skill当新训练案例；输出树存在也不自动证明质量合格。

## 6. 此前为什么会只剩93／106：已经证实的整理问题

1. **先把主训练范围缩成make/screen。** 旧主流为6774动作＋343终态标签=7117行；执行/评审另有14380行（Actor8089＋review6291），但只导出canonical引用和目标位置，**没有完整prompt/completion正文**。原正文仍在会话记录内。Actor作为辅助及≤10%混合是旧研究建议，不能据此丢弃试做观察、复现、评估反馈和修订上下文。
2. **把‘未审核’变成了很小的已交付数量。** 7117行中只审核425行，还有6692行未审；250行语义pass后再经公开表门得到134行，其中32行≤16K、61行16–32K、41行>32K，因此公开≤32K最终报93。未审核不等于负质量，公开门槛不等于训练价值。
3. **prepare有整阶段误拦截。** 329会话/3190助手位置被旧benchmark字符串规则拦下，触发文本包含‘不读正式250测试集’这类禁止句。这个误因成立，但修正它仍须逐项保留真实原226资源依赖隔离，不能反向宣称所有prepare都可训练。
4. **按名称子串识别角色不可靠。** 已查到业务筛简历、审合同、devprep和blindjudge混入WRD stage标签的问题；职责必须由实际request与工具上下文决定。
5. **后续106仍是窄分支。** 它是历史请求响应经过资源闭包与质量审核的子集，不是从所有原制作过程算出的可用上限。此前用它解释整个pipeline的数据充分性，范围不成立。
6. **目录发现范围过窄。** 旧清单和首轮普查偏重 `workflow*library` 名称，漏掉D/E的v10—v35迭代及前序WRD生成/原生病例/交接/控制载体。本轮新增完整文件账；是否旧CAS已有、是否同内容/同会话仍需逐项匹配，不由漏根反推全部正文遗漏。

旧make/screen的7117行曾有7100行机械编译成功、4874行≤32K；公开投影也有4109行机械编译成功。这些数据证明‘只导出93’不是‘只能解析93’，但机械编译成功本身仍不代表语义/血缘合格。

## 7. 思考、缺失和后续支线不能一刀切

原始响应、可见分析说明、工具参数、反馈与修订在地址账中保留。1763段选定native事件无非空独立reasoning字段，不能推广成全盘无思考记录：历史raw request/response已有143个不同reasoning内容，SSE另67响应含原reasoning，且旧response.json曾遗漏SSE字段。两支线粒度/范围不同，不相加当独立WRD任务。其历史恢复报告与首72.63GB基础账分开；本次补根也可能覆盖其中原目录，不能重复相加。

历史request/response恢复证据：[D:/skillloop/output/20261025_wrd_reasoning_recovery_v4/RAW_RECOVERY_REPORT.json](</D:/skillloop/output/20261025_wrd_reasoning_recovery_v4/RAW_RECOVERY_REPORT.json>)；原地址逐条位于对应 `controlled/raw_pairs.all.jsonl.gz`。
历史SSE证据与原地址：[D:/skillloop/output/20261025_wrd_reasoning_recovery_v4/SSE_REASONING_RECOVERY_REPORT.json](</D:/skillloop/output/20261025_wrd_reasoning_recovery_v4/SSE_REASONING_RECOVERY_REPORT.json>)；例如 [D:/skillloop/output/20261015_ewi_teacher_DATA/episodes/conv_1702b763a7ee/model_calls/decision_001/response.partial.raw](</D:/skillloop/output/20261015_ewi_teacher_DATA/episodes/conv_1702b763a7ee/model_calls/decision_001/response.partial.raw>)。
旧入口之外的97段历史native（含正式评测/技术/角色未知，未等同训练准入）：[D:/skillloop/output/20261025_wrd_reasoning_recovery_v4/HISTORICAL_NATIVE_RECOVERY_REPORT.json](</D:/skillloop/output/20261025_wrd_reasoning_recovery_v4/HISTORICAL_NATIVE_RECOVERY_REPORT.json>)。

1822个attempt中59个没有旧解析器预期位置的自身session_events；其中24个仍有request，27个仍有result。32个内嵌上游事件副本已存在于canonical，不能拿来冒充59个缺失自身响应的新恢复。目录存在1804/1822，存在性与正文可解析性分别列账。

50个根地址中34个已实扫、8个子根由父根覆盖，另8个后续正式评测/修订根另做受限metadata stat：3466文件/42,998,543字节，不含它们的workspace/input缓存。对限定820个原制作控制/反馈文件未观察到这8根basename引用，但不据此断言全语义无因果。后续8/4包修订支线保留地址，不把评测隔离误当成不许统计。

| 后续评测/修订支线原地址 | 本轮metadata文件数 | metadata字节 |
|---|---:|---:|
| [E:/skillloop_runs/w16light_1024](</E:/skillloop_runs/w16light_1024>) | 1,444 | 16,855,395 |
| [E:/skillloop_runs/wrd6if_1024](</E:/skillloop_runs/wrd6if_1024>) | 1,015 | 9,141,804 |
| [D:/skillloop/output/20261024_eval33_two_arm](</D:/skillloop/output/20261024_eval33_two_arm>) | 91 | 804,912 |
| [D:/skillloop/output/20261024_eval6_two_arm](</D:/skillloop/output/20261024_eval6_two_arm>) | 47 | 413,224 |
| [D:/skillloop/output/20261024_modified20_as_ts](</D:/skillloop/output/20261024_modified20_as_ts>) | 341 | 10,623,086 |
| [D:/skillloop/output/20261024_wrd16_light_two_arm](</D:/skillloop/output/20261024_wrd16_light_two_arm>) | 67 | 539,574 |
| [D:/skillloop/output/20261024_wrd250_library_run](</D:/skillloop/output/20261024_wrd250_library_run>) | 416 | 4,216,668 |
| [D:/skillloop/output/20261024_wrd6_interface_retry](</D:/skillloop/output/20261024_wrd6_interface_retry>) | 45 | 403,880 |

独立记忆和原引用反查另外补入D盘concurrency9及D/E的pipeline_infra_audit、pipeline_infra_repair_v3五根（2288文件/79,705,856字节）。concurrency9的154次原引用实际都指向同一个 `channel8/native_profile.json`，不是154个新会话；其jobs_before快照/配置保留在账。

候选legal-document-drafting还接受过额外Codex修复：[D:/skillloop/output/20261023_codex_assisted_resource_repair](</D:/skillloop/output/20261023_codex_assisted_resource_repair>)。明确分列历史条件，不冒充GLM/OpenClaw同条件制作。其精确原会话地址为 [C:/Users/22142/.codex/sessions/2026/10/23/rollout-2026-10-23T01-11-23-01a16469-7614-7e01-ba76-1ad2d9707177_01a16498-9504-7342-80c4-b714199ce710.jsonl](</C:/Users/22142/.codex/sessions/2026/10/23/rollout-2026-10-23T01-11-23-01a16469-7614-7e01-ba76-1ad2d9707177_01a16498-9504-7342-80c4-b714199ce710.jsonl>)（75,555,936字节）。本轮仅确认该文件stat，未读取/哈希/解析正文，未枚举父目录；它不计为第176个目录，也未混入上述目录总字节。原思考/动作字段内容仍待后续按授权完整解析。


## 8. 新补根的记录载体与全部已定位地址

本轮补扫119根，增量51,701文件路径/2,561,362,264字节，扫描错误0。补根父目录中的旧observed_service子根已剪除，D-v10已在补根内，不能另加一次。以下只是文件名载体数，包含复制/缓存，尚未全量解析或内容去重，不能叫新增独立会话/响应。

| 新补根中的记录载体文件名 | 文件数（非新独立样本） |
|---|---:|
| `*.raw` | 2,295 |
| `*.sse*` | 73 |
| `SKILL.md` | 297 |
| `native_events.jsonl` | 9 |
| `other_request_response_named_files` | 4,057 |
| `request.json` | 2,021 |
| `response.json` | 242 |
| `result.json` | 725 |
| `session_events.jsonl` | 74 |

截至本轮共定位175个地址；这是一份有明确发现规则/统计限制的地址登记，不声称穷尽全盘所有历史记录。原制作主根、版本/病例/控制支线、少量研究衍生材料与正式评测支线的职责分别保留在JSON。`实扫`/`补根实扫`按明确依赖/凭据/重解析排除完成元数据遍历；`父根覆盖`不重复计数；`后续支线`受限metadata另列。

| 原地址 | 状态 | 路径文件数（各自账口径） | 路径字节 |
|---|---|---:|---:|
| [E:/skillloop_runs/20261021_v10_reuse_iterations](</E:/skillloop_runs/20261021_v10_reuse_iterations>) | 基础实扫 | 82 | 13816868 |
| [E:/skillloop_runs/20261021_workflow_library_parallel4](</E:/skillloop_runs/20261021_workflow_library_parallel4>) | 基础实扫 | 128 | 314124344 |
| [E:/skillloop_runs/20261021_workflow_library_parallel4_recovery1](</E:/skillloop_runs/20261021_workflow_library_parallel4_recovery1>) | 基础实扫 | 1153 | 717526499 |
| [E:/skillloop_runs/20261021_workflow_library_v2](</E:/skillloop_runs/20261021_workflow_library_v2>) | 基础实扫 | 175 | 11204210 |
| [E:/skillloop_runs/20261021_workflow_skill_library](</E:/skillloop_runs/20261021_workflow_skill_library>) | 基础实扫 | 36 | 869112 |
| [E:/skillloop_runs/w10](</E:/skillloop_runs/w10>) | 基础实扫 | 12058 | 1196214662 |
| [E:/skillloop_runs/w16light_1024](</E:/skillloop_runs/w16light_1024>) | 后续支线（metadata另列） | — | — |
| [E:/skillloop_runs/w4](</E:/skillloop_runs/w4>) | 基础实扫 | 1417 | 668691269 |
| [E:/skillloop_runs/w4_controls](</E:/skillloop_runs/w4_controls>) | 基础实扫 | 2704 | 33277202 |
| [E:/skillloop_runs/w5](</E:/skillloop_runs/w5>) | 基础实扫 | 487 | 509200 |
| [E:/skillloop_runs/w5_controls](</E:/skillloop_runs/w5_controls>) | 基础实扫 | 749 | 487191 |
| [E:/skillloop_runs/w6](</E:/skillloop_runs/w6>) | 基础实扫 | 213 | 2011821 |
| [E:/skillloop_runs/w6_controls](</E:/skillloop_runs/w6_controls>) | 基础实扫 | 1721 | 11509135 |
| [E:/skillloop_runs/w9](</E:/skillloop_runs/w9>) | 基础实扫 | 1475 | 260498253 |
| [E:/skillloop_runs/workflow_library](</E:/skillloop_runs/workflow_library>) | 基础实扫 | 309821 | 27706756303 |
| [E:/skillloop_runs/wrd6if_1024](</E:/skillloop_runs/wrd6if_1024>) | 后续支线（metadata另列） | — | — |
| [D:/skillloop/output/20261021_workflow_library_parallel4](</D:/skillloop/output/20261021_workflow_library_parallel4>) | 基础实扫 | 93 | 1987089 |
| [D:/skillloop/output/20261021_workflow_library_parallel4_recovery1](</D:/skillloop/output/20261021_workflow_library_parallel4_recovery1>) | 基础实扫 | 325 | 7364482 |
| [D:/skillloop/output/20261021_workflow_library_v10](</D:/skillloop/output/20261021_workflow_library_v10>) | 基础实扫 | 9921 | 175285659 |
| [D:/skillloop/output/20261021_workflow_library_v2](</D:/skillloop/output/20261021_workflow_library_v2>) | 基础实扫 | 338 | 3764538 |
| [D:/skillloop/output/20261021_workflow_library_v4](</D:/skillloop/output/20261021_workflow_library_v4>) | 基础实扫 | 1619 | 16257305 |
| [D:/skillloop/output/20261021_workflow_library_v7](</D:/skillloop/output/20261021_workflow_library_v7>) | 基础实扫 | 378 | 3566679 |
| [D:/skillloop/output/20261021_workflow_library_v8](</D:/skillloop/output/20261021_workflow_library_v8>) | 基础实扫 | 459 | 4949113 |
| [D:/skillloop/output/20261021_workflow_library_v9](</D:/skillloop/output/20261021_workflow_library_v9>) | 基础实扫 | 2472 | 736607350 |
| [D:/skillloop/output/20261021_workflow_skill_library](</D:/skillloop/output/20261021_workflow_skill_library>) | 基础实扫 | 1127 | 69846153 |
| [D:/skillloop/output/20261024_eval33_two_arm](</D:/skillloop/output/20261024_eval33_two_arm>) | 后续支线（metadata另列） | — | — |
| [D:/skillloop/output/20261024_eval6_two_arm](</D:/skillloop/output/20261024_eval6_two_arm>) | 后续支线（metadata另列） | — | — |
| [D:/skillloop/output/20261024_modified20_as_ts](</D:/skillloop/output/20261024_modified20_as_ts>) | 后续支线（metadata另列） | — | — |
| [D:/skillloop/output/20261024_wrd12_library](</D:/skillloop/output/20261024_wrd12_library>) | 基础实扫 | 392 | 2441970 |
| [D:/skillloop/output/20261024_wrd16_light_two_arm](</D:/skillloop/output/20261024_wrd16_light_two_arm>) | 后续支线（metadata另列） | — | — |
| [D:/skillloop/output/20261024_wrd250_library_run](</D:/skillloop/output/20261024_wrd250_library_run>) | 后续支线（metadata另列） | — | — |
| [D:/skillloop/output/20261024_wrd6_interface_retry](</D:/skillloop/output/20261024_wrd6_interface_retry>) | 后续支线（metadata另列） | — | — |
| [D:/skillloop/output/workflow_library](</D:/skillloop/output/workflow_library>) | 基础实扫 | 389780 | 40497632317 |
| [E:/skillloop_runs/20261021_T0012_native_two_arm/observed_service](</E:/skillloop_runs/20261021_T0012_native_two_arm/observed_service>) | 基础实扫 | 1027 | 154283846 |
| [E:/skillloop_runs/20261021_workflow_library_parallel4/lane_1](</E:/skillloop_runs/20261021_workflow_library_parallel4/lane_1>) | 父根覆盖 | — | — |
| [E:/skillloop_runs/20261021_workflow_library_parallel4/lane_2](</E:/skillloop_runs/20261021_workflow_library_parallel4/lane_2>) | 父根覆盖 | — | — |
| [E:/skillloop_runs/20261021_workflow_library_parallel4/lane_3](</E:/skillloop_runs/20261021_workflow_library_parallel4/lane_3>) | 父根覆盖 | — | — |
| [E:/skillloop_runs/20261021_workflow_library_parallel4_recovery1/lane_4](</E:/skillloop_runs/20261021_workflow_library_parallel4_recovery1/lane_4>) | 父根覆盖 | — | — |
| [E:/skillloop_runs/20261021_workflow_library_parallel4_recovery1/lane_5](</E:/skillloop_runs/20261021_workflow_library_parallel4_recovery1/lane_5>) | 父根覆盖 | — | — |
| [E:/skillloop_runs/20261021_workflow_library_parallel4_recovery1/lane_6](</E:/skillloop_runs/20261021_workflow_library_parallel4_recovery1/lane_6>) | 父根覆盖 | — | — |
| [E:/skillloop_runs/20261021_workflow_library_parallel4_recovery1/lane_7](</E:/skillloop_runs/20261021_workflow_library_parallel4_recovery1/lane_7>) | 父根覆盖 | — | — |
| [E:/skillloop_runs/workflow_library/channel8](</E:/skillloop_runs/workflow_library/channel8>) | 父根覆盖 | — | — |
| [D:/skillloop/output/20261024_evidence_inputs_closeout/original_request_restore](</D:/skillloop/output/20261024_evidence_inputs_closeout/original_request_restore>) | 基础实扫 | 3 | 16886622 |
| [D:/skillloop/output/20261024_speed_audit/rule_decisions/44d48bf94838db40](</D:/skillloop/output/20261024_speed_audit/rule_decisions/44d48bf94838db40>) | 基础实扫 | 2 | 13962 |
| [D:/skillloop/output/20261024_speed_audit/rule_decisions/50e206fec0d86a65](</D:/skillloop/output/20261024_speed_audit/rule_decisions/50e206fec0d86a65>) | 基础实扫 | 2 | 93220 |
| [D:/skillloop/output/20261024_speed_audit/rule_decisions/95f867d47a057547](</D:/skillloop/output/20261024_speed_audit/rule_decisions/95f867d47a057547>) | 基础实扫 | 2 | 16321 |
| [D:/skillloop/output/20261024_speed_audit/rule_decisions/9946032b6e154a38](</D:/skillloop/output/20261024_speed_audit/rule_decisions/9946032b6e154a38>) | 基础实扫 | 2 | 13263 |
| [D:/skillloop/output/20261024_speed_audit/rule_decisions/a1268959874f42b6](</D:/skillloop/output/20261024_speed_audit/rule_decisions/a1268959874f42b6>) | 基础实扫 | 2 | 35696 |
| [D:/skillloop/output/20261024_speed_audit/rule_decisions/ae4e8801a37082d5](</D:/skillloop/output/20261024_speed_audit/rule_decisions/ae4e8801a37082d5>) | 基础实扫 | 2 | 54668 |
| [D:/skillloop/output/20261024_speed_audit/rule_decisions/d3c591932d2eb780](</D:/skillloop/output/20261024_speed_audit/rule_decisions/d3c591932d2eb780>) | 基础实扫 | 2 | 22313 |
| [E:/skillloop_runs/20261019_auto_workflow_pilot](</E:/skillloop_runs/20261019_auto_workflow_pilot>) | 补根实扫 | 7719 | 183863838 |
| [E:/skillloop_runs/20261019_native_case_three_arm](</E:/skillloop_runs/20261019_native_case_three_arm>) | 补根实扫 | 88 | 1753385 |
| [E:/skillloop_runs/20261019_native_neutral_case_v2](</E:/skillloop_runs/20261019_native_neutral_case_v2>) | 补根实扫 | 1273 | 158772037 |
| [E:/skillloop_runs/20261019_native_openclaw_unification](</E:/skillloop_runs/20261019_native_openclaw_unification>) | 补根实扫 | 203 | 1621621 |
| [E:/skillloop_runs/20261019_native_workflow_stage_probe](</E:/skillloop_runs/20261019_native_workflow_stage_probe>) | 补根实扫 | 68 | 855934 |
| [E:/skillloop_runs/20261020_v9_HR_T0012_commonworkflow](</E:/skillloop_runs/20261020_v9_HR_T0012_commonworkflow>) | 补根实扫 | 1126 | 157799507 |
| [E:/skillloop_runs/20261020_wrd_pipeline_v3_upgrade](</E:/skillloop_runs/20261020_wrd_pipeline_v3_upgrade>) | 补根实扫 | 1326 | 165151261 |
| [E:/skillloop_runs/20261020_wrd_v5_real_generation](</E:/skillloop_runs/20261020_wrd_v5_real_generation>) | 补根实扫 | 1110 | 156037448 |
| [E:/skillloop_runs/20261020_wrd_v6_progressive_generation](</E:/skillloop_runs/20261020_wrd_v6_progressive_generation>) | 补根实扫 | 1114 | 156991209 |
| [E:/skillloop_runs/20261020_wrd_v6_real250_T0047](</E:/skillloop_runs/20261020_wrd_v6_real250_T0047>) | 补根实扫 | 1139 | 159419960 |
| [E:/skillloop_runs/20261020_wrd_v7_performance_generation](</E:/skillloop_runs/20261020_wrd_v7_performance_generation>) | 补根实扫 | 1112 | 172680973 |
| [E:/skillloop_runs/20261020_wrd_v8_real250_case](</E:/skillloop_runs/20261020_wrd_v8_real250_case>) | 补根实扫 | 1294 | 191819389 |
| [E:/skillloop_runs/20261021_T0012_native_two_arm](</E:/skillloop_runs/20261021_T0012_native_two_arm>) | 补根实扫 | 161 | 4842405 |
| [E:/skillloop_runs/20261021_v11_reuse_repair](</E:/skillloop_runs/20261021_v11_reuse_repair>) | 补根实扫 | 242 | 7139097 |
| [E:/skillloop_runs/20261021_v12_batch_shared_results](</E:/skillloop_runs/20261021_v12_batch_shared_results>) | 补根实扫 | 156 | 3849028 |
| [E:/skillloop_runs/20261021_v13_evidence_states](</E:/skillloop_runs/20261021_v13_evidence_states>) | 补根实扫 | 79 | 2416722 |
| [E:/skillloop_runs/20261021_v14_evidence_handoff_repair](</E:/skillloop_runs/20261021_v14_evidence_handoff_repair>) | 补根实扫 | 193 | 5667526 |
| [E:/skillloop_runs/20261021_v15_direct_handoff](</E:/skillloop_runs/20261021_v15_direct_handoff>) | 补根实扫 | 92 | 3037636 |
| [E:/skillloop_runs/20261021_v16_readable_handoff_repair](</E:/skillloop_runs/20261021_v16_readable_handoff_repair>) | 补根实扫 | 186 | 3934214 |
| [E:/skillloop_runs/20261021_v17_compact_conditional_repair](</E:/skillloop_runs/20261021_v17_compact_conditional_repair>) | 补根实扫 | 187 | 4288973 |
| [E:/skillloop_runs/20261021_v18_batch_source_example](</E:/skillloop_runs/20261021_v18_batch_source_example>) | 补根实扫 | 169 | 4099345 |
| [E:/skillloop_runs/20261021_v19_direct_evidence_handoff](</E:/skillloop_runs/20261021_v19_direct_evidence_handoff>) | 补根实扫 | 173 | 3919309 |
| [E:/skillloop_runs/20261021_v20_requirements_resource](</E:/skillloop_runs/20261021_v20_requirements_resource>) | 补根实扫 | 88 | 2266655 |
| [E:/skillloop_runs/20261021_v21_immediate_handoff](</E:/skillloop_runs/20261021_v21_immediate_handoff>) | 补根实扫 | 172 | 3311378 |
| [E:/skillloop_runs/20261021_v22_atomic_evidence](</E:/skillloop_runs/20261021_v22_atomic_evidence>) | 补根实扫 | 105 | 2705314 |
| [E:/skillloop_runs/20261021_v23_scoped_evidence_repair](</E:/skillloop_runs/20261021_v23_scoped_evidence_repair>) | 补根实扫 | 179 | 4091298 |
| [E:/skillloop_runs/20261021_v24_relations_pending](</E:/skillloop_runs/20261021_v24_relations_pending>) | 补根实扫 | 171 | 4035192 |
| [E:/skillloop_runs/20261021_v25_direct_report_blocks](</E:/skillloop_runs/20261021_v25_direct_report_blocks>) | 补根实扫 | 161 | 4103484 |
| [E:/skillloop_runs/20261021_v26_reference_reuse](</E:/skillloop_runs/20261021_v26_reference_reuse>) | 补根实扫 | 171 | 5214953 |
| [E:/skillloop_runs/20261021_v27_reference_contract_repair](</E:/skillloop_runs/20261021_v27_reference_contract_repair>) | 补根实扫 | 178 | 3606475 |
| [E:/skillloop_runs/20261021_v28_question_records](</E:/skillloop_runs/20261021_v28_question_records>) | 补根实扫 | 165 | 3950334 |
| [E:/skillloop_runs/20261021_v29_direct_judgement_handoff](</E:/skillloop_runs/20261021_v29_direct_judgement_handoff>) | 补根实扫 | 164 | 4061184 |
| [E:/skillloop_runs/20261021_v30_bounded_support](</E:/skillloop_runs/20261021_v30_bounded_support>) | 补根实扫 | 164 | 4426944 |
| [E:/skillloop_runs/20261021_v31_renderer_rows](</E:/skillloop_runs/20261021_v31_renderer_rows>) | 补根实扫 | 99 | 2732896 |
| [E:/skillloop_runs/20261021_v32_complete_reproduction](</E:/skillloop_runs/20261021_v32_complete_reproduction>) | 补根实扫 | 136 | 4260985 |
| [E:/skillloop_runs/20261021_v33_global_output_ids](</E:/skillloop_runs/20261021_v33_global_output_ids>) | 补根实扫 | 212 | 6162284 |
| [E:/skillloop_runs/20261021_v34_single_evidence_matrix](</E:/skillloop_runs/20261021_v34_single_evidence_matrix>) | 补根实扫 | 167 | 4892610 |
| [E:/skillloop_runs/p7_vw3durti](</E:/skillloop_runs/p7_vw3durti>) | 补根实扫 | 10 | 24543 |
| [E:/skillloop_runs/v7_controls_1dv25010](</E:/skillloop_runs/v7_controls_1dv25010>) | 补根实扫 | 32 | 131857 |
| [E:/skillloop_runs/v7_controls_l1ahse2w](</E:/skillloop_runs/v7_controls_l1ahse2w>) | 补根实扫 | 32 | 134449 |
| [E:/skillloop_runs/v7_controls_nqnncca3](</E:/skillloop_runs/v7_controls_nqnncca3>) | 补根实扫 | 32 | 132384 |
| [E:/skillloop_runs/v7_controls_t6ja6ryj](</E:/skillloop_runs/v7_controls_t6ja6ryj>) | 补根实扫 | 32 | 132601 |
| [E:/skillloop_runs/validation_noskill_coordinator_1792382449061790600](</E:/skillloop_runs/validation_noskill_coordinator_1792382449061790600>) | 补根实扫 | 770 | 228324 |
| [D:/skillloop/output/20261019_auto_workflow_pilot](</D:/skillloop/output/20261019_auto_workflow_pilot>) | 补根实扫 | 190 | 6408370 |
| [D:/skillloop/output/20261019_complete_workflow](</D:/skillloop/output/20261019_complete_workflow>) | 补根实扫 | 17254 | 637087559 |
| [D:/skillloop/output/20261019_four_arm_T0145](</D:/skillloop/output/20261019_four_arm_T0145>) | 补根实扫 | 525 | 13297160 |
| [D:/skillloop/output/20261019_native_case_three_arm](</D:/skillloop/output/20261019_native_case_three_arm>) | 补根实扫 | 9 | 62350 |
| [D:/skillloop/output/20261019_native_neutral_case_v2](</D:/skillloop/output/20261019_native_neutral_case_v2>) | 补根实扫 | 43 | 1902786 |
| [D:/skillloop/output/20261019_native_openclaw_unification](</D:/skillloop/output/20261019_native_openclaw_unification>) | 补根实扫 | 7 | 25612 |
| [D:/skillloop/output/20261019_native_workflow_stage_probe](</D:/skillloop/output/20261019_native_workflow_stage_probe>) | 补根实扫 | 6 | 228417 |
| [D:/skillloop/output/20261019_wrd_pipeline](</D:/skillloop/output/20261019_wrd_pipeline>) | 补根实扫 | 26 | 3394626 |
| [D:/skillloop/output/20261020_one_request_wrd](</D:/skillloop/output/20261020_one_request_wrd>) | 补根实扫 | 1506 | 67669769 |
| [D:/skillloop/output/20261020_pipeline_v2_generation](</D:/skillloop/output/20261020_pipeline_v2_generation>) | 补根实扫 | 1279 | 10416872 |
| [D:/skillloop/output/20261020_T0145_leanonepass](</D:/skillloop/output/20261020_T0145_leanonepass>) | 补根实扫 | 176 | 3178968 |
| [D:/skillloop/output/20261020_T0145_leanread](</D:/skillloop/output/20261020_T0145_leanread>) | 补根实扫 | 197 | 3034455 |
| [D:/skillloop/output/20261020_T0145_nogate](</D:/skillloop/output/20261020_T0145_nogate>) | 补根实扫 | 135 | 2885822 |
| [D:/skillloop/output/20261020_T0145_onestep](</D:/skillloop/output/20261020_T0145_onestep>) | 补根实扫 | 143 | 2923205 |
| [D:/skillloop/output/20261020_T0145_paramskill](</D:/skillloop/output/20261020_T0145_paramskill>) | 补根实扫 | 272 | 5647638 |
| [D:/skillloop/output/20261020_T0145_v2skill](</D:/skillloop/output/20261020_T0145_v2skill>) | 补根实扫 | 476 | 13414188 |
| [D:/skillloop/output/20261020_v9_HR_T0012_commonworkflow](</D:/skillloop/output/20261020_v9_HR_T0012_commonworkflow>) | 补根实扫 | 77 | 1196015 |
| [D:/skillloop/output/20261020_v9_workflow_matcher](</D:/skillloop/output/20261020_v9_workflow_matcher>) | 补根实扫 | 10 | 42328 |
| [D:/skillloop/output/20261020_wrd_pipeline_v3_native_controls](</D:/skillloop/output/20261020_wrd_pipeline_v3_native_controls>) | 补根实扫 | 6 | 11191 |
| [D:/skillloop/output/20261020_wrd_pipeline_v3_pipeline_controls](</D:/skillloop/output/20261020_wrd_pipeline_v3_pipeline_controls>) | 补根实扫 | 6 | 13934 |
| [D:/skillloop/output/20261020_wrd_pipeline_v3_upgrade](</D:/skillloop/output/20261020_wrd_pipeline_v3_upgrade>) | 补根实扫 | 189 | 4567904 |
| [D:/skillloop/output/20261020_wrd_pipeline_v5_pipeline_controls](</D:/skillloop/output/20261020_wrd_pipeline_v5_pipeline_controls>) | 补根实扫 | 0 | 0 |
| [D:/skillloop/output/20261020_wrd_pipeline_v6_pipeline_controls](</D:/skillloop/output/20261020_wrd_pipeline_v6_pipeline_controls>) | 补根实扫 | 0 | 0 |
| [D:/skillloop/output/20261020_wrd_T0112](</D:/skillloop/output/20261020_wrd_T0112>) | 补根实扫 | 895 | 30261235 |
| [D:/skillloop/output/20261020_wrd_T0112_formal](</D:/skillloop/output/20261020_wrd_T0112_formal>) | 补根实扫 | 399 | 42799195 |
| [D:/skillloop/output/20261020_wrd_T0112_pattern](</D:/skillloop/output/20261020_wrd_T0112_pattern>) | 补根实扫 | 219 | 1906024 |
| [D:/skillloop/output/20261020_wrd_T0112_skill](</D:/skillloop/output/20261020_wrd_T0112_skill>) | 补根实扫 | 229 | 4272790 |
| [D:/skillloop/output/20261020_wrd_T0112_skill_judge32k](</D:/skillloop/output/20261020_wrd_T0112_skill_judge32k>) | 补根实扫 | 202 | 4633773 |
| [D:/skillloop/output/20261020_wrd_T0112_skill_notrace](</D:/skillloop/output/20261020_wrd_T0112_skill_notrace>) | 补根实扫 | 21 | 266501 |
| [D:/skillloop/output/20261020_wrd_T0112_skill_notrace2](</D:/skillloop/output/20261020_wrd_T0112_skill_notrace2>) | 补根实扫 | 21 | 266359 |
| [D:/skillloop/output/20261020_wrd_T0112_skill_notrace3](</D:/skillloop/output/20261020_wrd_T0112_skill_notrace3>) | 补根实扫 | 25 | 269984 |
| [D:/skillloop/output/20261020_wrd_T0120](</D:/skillloop/output/20261020_wrd_T0120>) | 补根实扫 | 411 | 4776180 |
| [D:/skillloop/output/20261020_wrd_T0120_r2](</D:/skillloop/output/20261020_wrd_T0120_r2>) | 补根实扫 | 262 | 2717033 |
| [D:/skillloop/output/20261020_wrd_v4_regeneration_two_arm](</D:/skillloop/output/20261020_wrd_v4_regeneration_two_arm>) | 补根实扫 | 1 | 4664 |
| [D:/skillloop/output/20261020_wrd_v5_read_budget_audit](</D:/skillloop/output/20261020_wrd_v5_read_budget_audit>) | 补根实扫 | 7 | 17730 |
| [D:/skillloop/output/20261020_wrd_v5_real_generation](</D:/skillloop/output/20261020_wrd_v5_real_generation>) | 补根实扫 | 36 | 845810 |
| [D:/skillloop/output/20261020_wrd_v6_progressive_generation](</D:/skillloop/output/20261020_wrd_v6_progressive_generation>) | 补根实扫 | 63 | 1516368 |
| [D:/skillloop/output/20261020_wrd_v6_real250_T0047](</D:/skillloop/output/20261020_wrd_v6_real250_T0047>) | 补根实扫 | 72 | 7974193 |
| [D:/skillloop/output/20261020_wrd_v7_performance_generation](</D:/skillloop/output/20261020_wrd_v7_performance_generation>) | 补根实扫 | 88 | 1093202 |
| [D:/skillloop/output/20261020_wrd_v8_lightweight_boundary](</D:/skillloop/output/20261020_wrd_v8_lightweight_boundary>) | 补根实扫 | 2 | 8964 |
| [D:/skillloop/output/20261020_wrd_v8_real250_case](</D:/skillloop/output/20261020_wrd_v8_real250_case>) | 补根实扫 | 108 | 2435645 |
| [D:/skillloop/output/20261020_wrd_workflow_first_upgrade](</D:/skillloop/output/20261020_wrd_workflow_first_upgrade>) | 补根实扫 | 10 | 435244 |
| [D:/skillloop/output/20261021_T0012_followup_diagnosis](</D:/skillloop/output/20261021_T0012_followup_diagnosis>) | 补根实扫 | 1 | 6930 |
| [D:/skillloop/output/20261021_T0012_native_two_arm](</D:/skillloop/output/20261021_T0012_native_two_arm>) | 补根实扫 | 49 | 1850900 |
| [D:/skillloop/output/20261021_T0012_trace_alignment](</D:/skillloop/output/20261021_T0012_trace_alignment>) | 补根实扫 | 10 | 216201 |
| [D:/skillloop/output/20261021_v10_reuse_iterations](</D:/skillloop/output/20261021_v10_reuse_iterations>) | 补根实扫 | 33 | 1172454 |
| [D:/skillloop/output/20261021_v11_reuse_repair](</D:/skillloop/output/20261021_v11_reuse_repair>) | 补根实扫 | 87 | 1857900 |
| [D:/skillloop/output/20261021_v12_batch_shared_results](</D:/skillloop/output/20261021_v12_batch_shared_results>) | 补根实扫 | 85 | 1697616 |
| [D:/skillloop/output/20261021_v13_evidence_states](</D:/skillloop/output/20261021_v13_evidence_states>) | 补根实扫 | 55 | 1360249 |
| [D:/skillloop/output/20261021_v14_evidence_handoff_repair](</D:/skillloop/output/20261021_v14_evidence_handoff_repair>) | 补根实扫 | 98 | 1858680 |
| [D:/skillloop/output/20261021_v15_direct_handoff](</D:/skillloop/output/20261021_v15_direct_handoff>) | 补根实扫 | 102 | 1670922 |
| [D:/skillloop/output/20261021_v16_readable_handoff_repair](</D:/skillloop/output/20261021_v16_readable_handoff_repair>) | 补根实扫 | 139 | 2217986 |
| [D:/skillloop/output/20261021_v17_compact_conditional_repair](</D:/skillloop/output/20261021_v17_compact_conditional_repair>) | 补根实扫 | 142 | 2249099 |
| [D:/skillloop/output/20261021_v18_batch_source_example](</D:/skillloop/output/20261021_v18_batch_source_example>) | 补根实扫 | 144 | 2236736 |
| [D:/skillloop/output/20261021_v19_direct_evidence_handoff](</D:/skillloop/output/20261021_v19_direct_evidence_handoff>) | 补根实扫 | 142 | 2204467 |
| [D:/skillloop/output/20261021_v20_requirements_resource](</D:/skillloop/output/20261021_v20_requirements_resource>) | 补根实扫 | 128 | 1904713 |
| [D:/skillloop/output/20261021_v21_immediate_handoff](</D:/skillloop/output/20261021_v21_immediate_handoff>) | 补根实扫 | 162 | 2242950 |
| [D:/skillloop/output/20261021_v22_atomic_evidence](</D:/skillloop/output/20261021_v22_atomic_evidence>) | 补根实扫 | 142 | 2150505 |
| [D:/skillloop/output/20261021_v23_scoped_evidence_repair](</D:/skillloop/output/20261021_v23_scoped_evidence_repair>) | 补根实扫 | 173 | 2519017 |
| [D:/skillloop/output/20261021_v24_relations_pending](</D:/skillloop/output/20261021_v24_relations_pending>) | 补根实扫 | 260 | 3319124 |
| [D:/skillloop/output/20261021_v25_direct_report_blocks](</D:/skillloop/output/20261021_v25_direct_report_blocks>) | 补根实扫 | 96 | 1735097 |
| [D:/skillloop/output/20261021_v26_reference_reuse](</D:/skillloop/output/20261021_v26_reference_reuse>) | 补根实扫 | 110 | 1696223 |
| [D:/skillloop/output/20261021_v27_reference_contract_repair](</D:/skillloop/output/20261021_v27_reference_contract_repair>) | 补根实扫 | 111 | 1876589 |
| [D:/skillloop/output/20261021_v28_question_records](</D:/skillloop/output/20261021_v28_question_records>) | 补根实扫 | 112 | 1874971 |
| [D:/skillloop/output/20261021_v29_direct_judgement_handoff](</D:/skillloop/output/20261021_v29_direct_judgement_handoff>) | 补根实扫 | 111 | 1870907 |
| [D:/skillloop/output/20261021_v30_bounded_support](</D:/skillloop/output/20261021_v30_bounded_support>) | 补根实扫 | 123 | 1967491 |
| [D:/skillloop/output/20261021_v31_renderer_rows](</D:/skillloop/output/20261021_v31_renderer_rows>) | 补根实扫 | 237 | 5311992 |
| [D:/skillloop/output/20261021_v32_complete_reproduction](</D:/skillloop/output/20261021_v32_complete_reproduction>) | 补根实扫 | 191 | 5023282 |
| [D:/skillloop/output/20261021_v33_global_output_ids](</D:/skillloop/output/20261021_v33_global_output_ids>) | 补根实扫 | 250 | 6077655 |
| [D:/skillloop/output/20261021_v34_single_evidence_matrix](</D:/skillloop/output/20261021_v34_single_evidence_matrix>) | 补根实扫 | 264 | 6159156 |
| [D:/skillloop/output/20261021_v35_direct_render_handoff](</D:/skillloop/output/20261021_v35_direct_render_handoff>) | 补根实扫 | 54 | 514411 |
| [D:/skillloop/output/20261021_wrd_training_review](</D:/skillloop/output/20261021_wrd_training_review>) | 补根实扫 | 5 | 37617 |
| [D:/skillloop/output/outer152_5o2ubl83](</D:/skillloop/output/outer152_5o2ubl83>) | 补根实扫 | 5 | 387 |
| [D:/skillloop/output/outer152_publy8ff](</D:/skillloop/output/outer152_publy8ff>) | 补根实扫 | 6 | 452 |
| [D:/skillloop/output/outer152_zgip44sl](</D:/skillloop/output/outer152_zgip44sl>) | 补根实扫 | 6 | 452 |
| [D:/skillloop/output/wrd153_d4sntfis](</D:/skillloop/output/wrd153_d4sntfis>) | 补根实扫 | 15 | 2109 |
| [D:/skillloop/output/20261024_concurrency9](</D:/skillloop/output/20261024_concurrency9>) | 末批补根实扫 | 28 | 50877444 |
| [D:/skillloop/output/20261021_pipeline_infra_audit](</D:/skillloop/output/20261021_pipeline_infra_audit>) | 末批补根实扫 | 327 | 10727661 |
| [E:/skillloop_runs/20261021_pipeline_infra_audit](</E:/skillloop_runs/20261021_pipeline_infra_audit>) | 末批补根实扫 | 1882 | 8996253 |
| [D:/skillloop/output/20261021_pipeline_infra_repair_v3](</D:/skillloop/output/20261021_pipeline_infra_repair_v3>) | 末批补根实扫 | 24 | 1074220 |
| [E:/skillloop_runs/20261021_pipeline_infra_repair_v3](</E:/skillloop_runs/20261021_pipeline_infra_repair_v3>) | 末批补根实扫 | 27 | 8030278 |
| [D:/skillloop/output/20261023_codex_assisted_resource_repair](</D:/skillloop/output/20261023_codex_assisted_resource_repair>) | 历史辅助修复实扫 | 66 | 1162823 |

## 9. 可复核产物与结论边界

- [SUMMARY.json](SUMMARY.json)、[ROOTS_ALL.csv](ROOTS_ALL.csv)、[NINE_CHANNELS.csv](NINE_CHANNELS.csv)、[STAGE_COUNTS.csv](STAGE_COUNTS.csv)、[SKILL29_OVERVIEW.csv](SKILL29_OVERVIEW.csv)：汇总与全部已定位地址；ROOTS_ALL_50.csv仅保留首份基础表。
- [PHYSICAL_ROOTS.json](PHYSICAL_ROOTS.json)、[controlled/PHYSICAL_FILES.jsonl.gz](controlled/PHYSICAL_FILES.jsonl.gz)：740167条原路径/文件身份/大小/时间账，不含正文。
- [SKILL29_LINEAGE_MAP.json](SKILL29_LINEAGE_MAP.json)、[indexes/episodes.all.jsonl.gz](indexes/episodes.all.jsonl.gz)、[indexes/jobs.all.jsonl.gz](indexes/jobs.all.jsonl.gz)、[indexes/episode_files.all.jsonl.gz](indexes/episode_files.all.jsonl.gz)：原job→attempt→正文/工具/资源文件地址。
- [indexes/skill_version_trees.all.jsonl.gz](indexes/skill_version_trees.all.jsonl.gz)、[NON_RETAINED_AND_FAILED_PROCESS_INDEX.json](NON_RETAINED_AND_FAILED_PROCESS_INDEX.json)：资源版本和未留存/失败支线。
- [EXPORT_COVERAGE_AUDIT.json](EXPORT_COVERAGE_AUDIT.json)：旧解析器、角色、筛选漏斗和1763原event对象的独立核查证据。
- [EVALUATION_BRANCH_ROOTS.json](EVALUATION_BRANCH_ROOTS.json)、[controlled/EVALUATION_METADATA_FILES.jsonl.gz](controlled/EVALUATION_METADATA_FILES.jsonl.gz)：后续正式评测/修订支线，分账保留。

- [ADDITIONAL_ORIGINAL_ROOTS.json](ADDITIONAL_ORIGINAL_ROOTS.json)、[controlled/ADDITIONAL_ORIGINAL_FILES.jsonl.gz](controlled/ADDITIONAL_ORIGINAL_FILES.jsonl.gz)：补根闭合路径账、发现规则、旧范围更正、重叠剪除及载体文件名统计。
- [FINAL_DISCOVERY_ROOTS.json](FINAL_DISCOVERY_ROOTS.json)、[ASSISTED_REPAIR_SOURCE.json](ASSISTED_REPAIR_SOURCE.json)：并发配置/原设施回接的末批五根，以及Codex辅助修复目录和精确C盘原会话单文件stat，均分账。
- [FINAL_REGISTRY_RECONCILIATION.json](FINAL_REGISTRY_RECONCILIATION.json)、[indexes/additional_discovery.final_queryable_registry.jsonl.gz](indexes/additional_discovery.final_queryable_registry.jsonl.gz)：独立反查217份10/20—24记忆、原29引用和418个顶层地址。其余状态快照、独立评测、早期参考、语义待核及父子覆盖地址全部登记可查，未递归不等于训练拒绝；不是把418地址冒充418原制作根。
- [STAGE_ADDRESS_EXAMPLES.json](STAGE_ADDRESS_EXAMPLES.json)、[NATIVE_EVENT_CARRIER_ROLES.json](NATIVE_EVENT_CARRIER_ROLES.json)、[indexes/historical_model_pair_carriers.all.jsonl.gz](indexes/historical_model_pair_carriers.all.jsonl.gz)：原阶段产物实例、3341载体hash分解（1763会话转录/1577计量桥接/1其他），以及全部已恢复历史raw/SSE原地址。

物理盘点有11个WinError1920，均为临时venv/python或node_modules_*链接，逐项保留，未当作训练不合格。凭据/依赖/重解析目录不跨引用递归，SQLite物理普查仅stat；另一次独立生产目录核对采用只读SQL/query_only，无写入/checkpoint且DB/WAL前后stat不变。未干预当前并行消融。

**目前可以明确归因于此前整理范围和导出处理问题；不能归因于‘大部分原始数据不适训’。** 这个普查建立了后续完整整理必须使用的入口。下一阶段须按实际角色和时间顺序恢复输入→原始响应/思考→工具操作→观测反馈→资源版本→评审修订→终态，并分别核真实原226血缘、去重、因果可见性及监督mask，才能给最终可训练条数/监督tokens。

这轮没有重新承诺数据充分或效果必达，没有将32342响应位置直接叫32342合格训练样本；也没有把地址清单当成已经完成的全链路训练集。
