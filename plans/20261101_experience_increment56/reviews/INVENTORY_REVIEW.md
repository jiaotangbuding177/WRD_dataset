# 增量计划56：现有来源与真实修订链入口的只读审阅

本轮只制定计划。已读研究三文件、55双稿及最新Git交付记忆；没有模型、训练、原生业务采集、全库编译或数据准入操作。本报告没有复制企业会话正文。

## 当前基准与独立经验的统计单位

当前完整训练池为1,250唯一目标，原主623＝418契约＋205过程，另627明确作者辅助。205过程覆盖56来源ID／44全局连接组；原主合计288来源ID／267跨银行连接组。新增独立企业经验应首先相对**全部当前TRAIN来源及共享资源组**判断，而不只相对44过程组。

一个来源若此前仅出现在418契约中，新增其真实执行可记“过程经验新增”，不能再记“首次未见企业来源”。同一任务的多窗口、多个修订和反复epochs增加监督覆盖，不增加独立来源数。原226、H12/static、reserved40及新dev整组保持隔离。

## 第一优先：有真实附件的未用来源，重新对当前入口做anti-join

原始候选入口：

- `D:/skillloop/output/20261027_wrd_main_v10/clean_inputs/source_scope.metadata.jsonl.gz`：原始身份／TRAIN与保留边界元数据。
- `D:/skillloop/output/20261027_wrd_main_v10/clean_inputs/source_pool.with_body.jsonl.gz`：企业原会话与真实材料载体。选题时先用scope和材料元数据，确定来源后再按需读正文。
- `D:/skillloop/research/plans/20261030_wrd_gap_completion/reviews/clean_source_inventory.json`：已有未用来源及真实附件索引，提供`remaining391_source_metadata`和`authentic20_metadata`，后者字段包含source、group、material引用、SHA和既有类别。

该库存绑定的是**旧552快照**：当时694个TRAIN来源中，391来源／382组与旧训练组不交；其中20来源／18组带53份材料引用、51个独立SHA。它们是优先复核候选，**不能当作当前623＋627下的新可训数量**，更不能直接沿用旧387／378口径。建议计划的第0步对当前623源、所有保留与新识别别名重做元数据anti-join，再以附件实际存在／SHA、机制差异和真实原日志丰富度排序。

选题依据一：该索引已经有实际材料身份与SHA，能优先找到可复现的原任务，减少无附件或相同source被重复造样的成本。

## 第二优先：已恢复身份、存在动作和版本反馈的原生日志

最新10版入口：

- `D:/skillloop/output/20261031_wrd_curation10/identity/OWNER7357_IDENTITY_FINAL.metadata.jsonl.gz`。
- 同目录`FINAL_IDENTITY_QA.json`、`IDENTITY_GRAPH_COMPLETENESS_ERRATUM.json`。
- 同目录`SHARED_RESOURCE_ANCESTRY_WORKLOAD.metadata.json`：按共同资源/producer归并的恢复工作量，避免7357次重复搜索同一资源。
- 同目录`RECOVERED_NATIVE_REVIEW_INDEX.json`与`ORIGINAL_ROOT_DISCOVERY.metadata.json`：已补恢复原native与owner的定点索引。

最新互斥状态仍为：4866身份已恢复但资源祖先待核、1657非TRAIN或缺scope、52确证保护方法、607两轮定点查找未定位、159旧图没有资源边、16公共技术；合7357。159不是祖先已清白的证明。上述均为审查工作量，不能直接报为训练新增。

选题依据二：优先从身份和真实事件可闭合、尚未覆盖的来源组中找“原尝试→真实失败→原修订→同版本再试”关系。资源祖先闭合与语义正确分别判断；不把最终success当整个prefix正loss。52保护方法项不列作可恢复TRAIN，607缺件项不继续无限搜索。

## 第三优先：将已核实的局部修订证据作为抽取模板，扩到独立新任务

可复用的实际证据结构入口：

- `D:/skillloop/output/20261031_wrd_curation10/resource_review10/meeting_gen01/RESOURCE_SEMANTIC_REVIEW.json`及`SOURCE_ARTIFACT_QA.json`：旧formatter实际10过／4反例失败，修订版14过；旧代码错误跨度与资源版本可核。该批属于已有来源和显式新状态，不计新的独立经验。
- `D:/skillloop/output/20261031_wrd_curation10/reasoning_semantic10/CPU_RESOURCE_CHECKS.json`：原21与修订21＋12本地检查的有限证据。
- 同目录`COMPONENT_CREDIT_AND_OWNER_LEDGER.json`：原依据、owner和限定动作授信；该文件明确这些来源已见，不增加独立任务量。
- `D:/skillloop/research/plans/20261031_wrd_curation10/ACTUAL_DATA_REPORT.md`：最终10版准入与边界，优先于早期局部报告中的PENDING_ROOT状态。

选题依据三：这些记录证明应保存什么因果接口——原输入／当前依据、动作、资源SHA、真实错误反馈、局部修订、同版本复试及独立消费／最终取舍。新的来源应按此结构恢复；对旧会议样例再造多窗口不能替代独立新任务。CPU资源检查只授实际测试覆盖，不自动授业务Q、复用收益或KEEP。

## 对下一轮计划的直接建议

1. 先做来源元数据重基和任务级队列，分别列首次新来源、已见来源的新执行、旧来源的进一步修订；不先承诺可新增多少训练tokens。
2. 低成本离线恢复优先：一旦原件齐全，产出真实版本链与可训状态；失败、HOLD、STOP和负反馈原件一并保留。只补标当前可见依据，不编造原思考、工具结果或最终取舍。
3. 有界原生补采按完整任务一次委托给固定OpenClaw，外层只投递、预算、记录和事后评分；不得拆成外层安排的各步来伪装自主长轨迹。新来源和每个消费case先冻结角色及split。
4. 当前学生尚未训练，现有队列由历史大模型真实错误和过程覆盖驱动；V1训练后再使用**TRAIN/专门采集split的学生错误**挑下一批。固定dev/test错误只用于报告，不把其原题、答案或修复链移入TRAIN。
5. 回报按独立来源组、完整版本修订链、可训监督tokens及成本分别计量；真实同版本无技能／有技能消费与质量比较支持最后KEEP/REVISE/STOP。修订正文是否正确挂钩其实际反馈，整条链失败不抹掉可核实的正确局部动作。

本轮新增可训目标0、独立任务采集0、模型/训练0；报告仅提供可据以规划的真实元数据入口与统计单位。
