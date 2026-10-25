# 全链路内容盘点与监督边界

状态：离线数据设计与内容计数；不是启动配置，没有新增教师调用、训练或效果实证。统计来源为冻结bundle及其CAS，正文不写入本报告。

## 实际内容计数

离线脚本content_audit.py已运行退出0；原归档扫描最终52.313秒，无新模型调用。机器可读结果：output/20261025_wrd_fullchain_reaudit/CONTENT_AUDIT.json，含canonical、归档索引及脚本SHA256。

|角色/阶段|会话|助手目标|非空目标候选|有可见文本|文本与工具同消息|纯文本|
|---|---:|---:|---:|---:|---:|---:|
|prepare|329|3190|3098|1275|1017|258|
|screen|135|996|955|287|173|114|
|make|357|9016|8932|3159|2834|325|
|review|378|6803|6743|1324|974|350|
|沉淀角色小计|1199|20005|19728|6045|4998|1047|
|actor试做|526|11732|11683|3491|2998|493|
|legacy历史|38|605|603|187|151|36|
|全部|1763|32342|32014|9723|8147|1576|

全域328空目标不进入SFT。非空只是内容存在，不等于语义准入；可见文本包括执行说明/收尾/解释，不能全称为CoT或有质量的推理。原生助手content含30438个toolCall块、9801个text块；块数不等于独立样本数。Actor有更多非核心工具与非核心工具历史，不宜为了套核心7工具而丢弃全部上下文。

## 数据组织与用户图对应

用户图A“轨迹归纳与复用筛选”主要对应screen及其原始企业会话；图B“工作流与资源构建”对应make的初制/资源复现/局部修订；图C“效能评估与筛选”跨prepare（检索演化需求）、actor（无技能/增强执行）、review（比较交付与开销并提出修订/保留/停止）；图D“技能封装与冻结”主要是make终态资源与review留存决策的联合证据。阶段名不是六种互相隔离的生成任务，必须以来源、路线、技能版本、试做用例及修订轮次连接。

采用四层数据：

1. 原生会话母本：1763完整观察会话、全部消息、原系统提示、原工具定义/结果和产物版本。是证据母本，不宣称全部为成功正例。
2. 沉淀策略示范：screen/make/prepare/review的动作、公开可见解释、任务选择、评审决策及收尾。完整目标位置均可追溯母本，保留先失败再修复；错误动作本身不自动作为正例。
3. 过程标注：从观察日志提炼“当前目标、证据引用、备选路线、选择、待验证项、停止/修订条件”，单独记录annotator、证据span和可见时间。此层是新增监督任务，不能冒充原教师隐藏思维。
4. 试做辅助：actor执行轨迹与成功/失败工具反馈。它们既可辅助学习工具操作，也为图C策略模型提供观察；保留role身份，不能让大量Actor低层操作淹没路线/评审决策。

资源产物2866去重文本对象不是2866独立任务；同一write目标、终态文件、历史版本和归档别名通过SHA/episode链接，不重复计算独立监督量。阶段会话/助手目标/决策事件/来源组/监督token分别报告。

## 推理可见性

旧training.py::_clean_content包含删除thinking/reasoning/redacted_thinking及think标签的逻辑，但旧summary记录reasoning_blocks_removed=0。因此不能仅凭canonical的reasoning_exported=false，声称原始推理曾被删除，也不能宣称母本已包含原始CoT。实际原归档字段计数见CONTENT_AUDIT.json。reasoning/analysis字符串若出现在程序schema、附件、复制的历史或用户文本中，不能算教师决策推理；需要确认模型响应的作者、角色、字段与时间。

本轮实际检查冻结CAS：3817个不同request.json、1807个不同response.json、1763个不同session_events.jsonl（102150个可解析事件；3行异常保留计数）。已检索的原生事件和请求中未检出显式thinking/reasoning/analysis非空字段或think标签段；response中1579个thinking字符串全部为配置枚举off，样本字段路径为runtime.native_meta.requestShaping.thinking，不是推理正文。当前没有证据称可恢复成千条独立的原教师隐藏CoT。这项结论限于上述冻结文件与字段，不推断未扫描外部服务或未保存传输的内容。

可学习的推理目标首先是原日志中公开可见的任务分析、路线归并理由、复用选择依据、资源设计说明、比较结论和修订建议。必要的新增标注形成证据支撑的简明决策记录。对没有日志支持的内部思考不进行反推补造；最终成功结果只能作事后评价标签，不能倒灌到当时决策输入。

## 建议样本结构

```json
{
  "id": "stable_example_id",
  "pipeline_phase": "A|B|C|D",
  "actor_role": "distiller|trial_actor",
  "episode_id": "frozen_episode_id",
  "target_message_indices": [17],
  "evidence_refs": [{"session_sha256": "...", "message_index": 16}],
  "chain_id": "verified_route_version_case_chain",
  "source_group_ids": ["..."],
  "observation_cutoff": {"episode_id": "...", "message_index_exclusive": 17},
  "target_type": "native_action|decision_record|repair|stage_completion",
  "label_origin": "observed_teacher|derived_evidence_annotation",
  "review_status": "unreviewed|silver|reviewed",
  "temporal_view": "online_before_action|retrospective_after_observation",
  "candidate_publication_status": "independent_from_training_eligibility",
  "train_admitted": false,
  "tokenizer_revision": "...",
  "input_ids": [],
  "supervision_spans": [[1024, 1150]],
  "supervised_token_count": 126
}
```

后验review作为训练目标时，其输入可以含review发生前已可见的完整试做反馈；它不能被拿来训练较早screen决策的无条件预测，除非明确变为“事后诊断”任务。反事实好坏配对必须同输入信息、同任务和工具条件；不同版本前后自然变好并不自动构成DPO同prompt对。

## Loss mask合同

所有system/user/tool观察、历史assistant前缀、检索材料和教师后验评价默认label=-100。只对声明的当前assistant目标或完整阶段轨迹内被准入的assistant跨度监督；监督工具名称/JSON参数及可见决策解释，不监督工具返回。空target不作为训练样本。公开许可与训练质量准入分列，受控可用数据不能因未公开而被排除于本地统计。

保持native tool call/result ID及顺序，目标不能包含未来tool result。failed命令可以保留为后续repair的历史；是否将失败动作本身作为策略正例，需要区分必要探测与可避免失误。不按会话最终失败全删前面有效行为，也不按最终成功全收所有错误行为。

每条用两模型固定官方模板渲染，验证prompt/full字符前缀、token前缀、offset不跨边界、decode逐字一致、完整结束标记、tools schema及调用配对；再比较14B/8B token ID和mask SHA。旧模板有17条前缀异常，不能忽略或在未知边界上猜mask。全阶段样本还没完成新token编译，旧7117覆盖率不能沿用。

阶段轨迹多assistant监督与单步续写是两种视图，统一曝光账防止同一token无意重复计权。完整轨迹模式仍对工具输出及未准入assistant跨度mask；不能将整段会话每个token都算loss。每来源/路线限制曝光，按阶段均衡采样，避免冗长read/process动作支配损失。新增decision_record可较短且提高决策密度；其质量权重和原生行为权重应分开做开发集选择，不能声称未测权重最优。

## 16K/32K与超长轨迹

先编译完整原生前缀+当前目标，以共同可容纳ID交集分16K/32K，完整保留核心决策。32K以上保留母本，不静默截断、不只保留结尾，不跨来源拼接凑长样本。可另外生成明确标记的“阶段交接/证据摘要”派生任务：摘要只能用cutoff之前已观察内容并引用源span；资源正文通过原生read实际读取。派生短视图不是原始完整轨迹，也不增加独立来源数。

不为节约训练长度凭空更换OpenClaw工具返回、skills发现/读取或Agent循环。是否采用训练期阶段摘要/运行期原生上下文管理，应另立对照；资源对象仍需要外部skills库，14B权重不能替代所有附件/程序字节。

## 可检验预期

期望得到一个在同一原生OpenClaw环境内、按阶段职责执行整条A→B→C→D及C→B局部修订循环的14B模型，8B用相同来源与曝光作对照；成功定义是新来源生成技能可复现、可正常/边界使用且单位合格技能全成本下降。该预期是研究假设。阶段预测准确率与SFT loss只能诊断，不能替代完整技能交付、独立质量Q、真实业务减负和全部失败费用。
