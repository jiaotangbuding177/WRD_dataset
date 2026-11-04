# 全库 owner 实账与原记录保全（2026-10-30）

本目录是实际执行的数据处理结果。`BASELINE01_FROZEN_FILES.json` 封存旧账，`*OVERLAY02*` 追加后续确证；不静默改旧标签。本目录没有启动训练、Teacher、Actor 或旧执行器，没有自行增加正 loss。主训练集的新增准入由 root 另行审查、编译和记录。

## 实际处理人口与粒度

| 入口 | 实际粒度 | 本次连接量 |
|---|---|---:|
| 旧 v9 精确 scope 表 | 1,763 native episode 的 assistant owner | 32,342 |
| v9 恢复后的扩展原件 | 1,843 native episode 的 assistant owner | 34,239 |
| 后续明确定位的遗漏 carrier | 9 个 route batch＋19 个本轮原生会话 | 377 owner |
| 合计注册 native 人口 | 1,871 episode／34,616 assistant owner | 全量连接实际正文 |
| provider 原记录 | 独立 responseID 组，不能加成新任务 | 1,536 |
| 主训练集快照 | 原件范围、新状态和新标注分账 | 552 view／150,674 正 tokens |

episode、模型响应和原企业会话是不同粒度。175 个物理目录、75GB 物理副本不能当作175个独立数据集；本账没有声称已穷尽所有未注册磁盘记录。

`CORPUS_OWNER_COVERAGE.native.jsonl.gz` 的主键为 SHA256(`episode_id:message_index`) 前24位。它保存原消息SHA、事件行、来源范围、旧 eligibility／protocol／405 审查、当前和已撤回的 R/A view。原全文位于 `audit_inputs/native1843.contexts.original.jsonl.gz` 和 `EXTRA_NATIVE_CONTEXTS.original.jsonl.gz`，不把新作者状态标成原 native。

`PROVIDER_OWNER_COVERAGE.jsonl.gz` 与 `audit_inputs/provider1536.pairs.original.jsonl.gz` 分别保存 provider 身份和全部实际请求／原响应正文。相同 responseID 仅为候选边；完整 prefix 和工具／可见输出另核。

## 真正恢复的原字节

`NATIVE1871_ORIGINAL_CARRIER_ARCHIVE_INDEX.json` 对应1,871份完整原 native carrier，446,295,798字节，包含原头部和非 message 事件；压档为 `audit_inputs/native1871.carriers.original.tar.gz`。每个成员名为 `objects/<SHA>`，已逐成员读回核SHA。

`PROVIDER1536_ORIGINAL_CARRIER_ARCHIVE_INDEX.json` 对应2,990个不同的实际 API request/response carrier，共60,722,415字节。原路径2,209个仍在；另781个旧E路径已缺失，但已从v4保全的完整原JSON按原写法恢复字节，恢复后SHA逐份完全等于先前记录的原pin。`EXACT_JSON_CARRIER_RESTORATION.json` 给出每份原SHA、原完整JSON出处、序列化配方和恢复原件。它们不是近似重建或新采样。全部2,990个carrier均在压档中读回校验；1,536组解析正文也单独保全。

原 carrier 仍可能本来就没有捕获完整 system、工具 schema 或 provider 内部思考；文件存在与SHA正确不会补出这些未记录字段。每条未知状态保留。

## scope 和质量处置

旧6,692个“未语义审”owner已逐ID连接：5,954保护祖先、205当前static/shared边界、187血缘未决、287已有只读字节审计、40协议辅助待复杂语义审、19来源闭合待语义。不能直接用6,692减552；它们的粒度、条件和组件不同。

基础账34,616个owner中：20,979保护祖先、2,337当前来源/static隔离、6,272血缘未决、56当前source身份缺失、2,246扩展prefix尚未审、1,229来源闭合待语义、1,092协议辅助、405局部只读审计。表中的“来源闭合”沿用逐target旧证据并套当前来源边界，不代替遗漏私有read检查、程序正确性、技能消费表现或质量Q。

后续另核56个带原R的provider/native候选：6份实际初始prompt、冻结release receipt及XLSX逐SHA确证均属现行冻结评测static输入。保护内容在native初始user index0已经实际收到，故 `NATIVE73_STATIC_SCOPE_OVERLAY02.jsonl.gz` 将同6episode的全部73个assistant owner追加隔离，原unknown扩展人口从2,246变为2,173。原226来源ID映射仍未知，不编造conv映射，不依据evaluation角色排除。其中54个完整工具／输出相等；两个同ID可见输出不等另保留归属HOLD。证据位于相邻 `reasoning/supplement56/`。

## 原R的精确剩余

`reasoning_residual/PROVIDER257_R_RESIDUAL.with_body.jsonl.gz` 保留257组非空原R及全部原请求。116组可接v4原pair的同ID且完整message相等；56组是上述实际冻结评测输入。当前已有严格逐请求闭包与TRAIN来源证明的新增provider R为0，不能据此推断其余原R永远不可用。

两条maker累计R共50,349字符：当前仅1,467原字符已授范围信用，剩48,882未授。顶层真实source是TRAIN，但最后累计response不在既有v6逐请求闭包内，不能整段拼到某个单步动作。它们的完整原JSON、原prompt与范围位于 `CURRENT_TRAIN_TOP_SOURCE_CUMULATIVE_R.with_original_pairs.jsonl.gz`。

外部历史SSE另有67份原R，和provider1536按原responseID交集为0。当前严格TRAIN闭包26份，正是主集已有26个原owner；没有新增整owner。396,231原字符全部保全，其中127,833原字符已授正范围，268,398未授。`review_slices/HISTORICAL26_EXACT_REMAINDER_CLASSIFICATIONS.with_original_text.jsonl.gz` 逐字符对齐既有全文审查：208,040未知未批准；21,802有效但未选／重复；37,177 ABI/格式重复；239已证错；1,140 unsupported、未执行或同行精确撤正。未知表示“全文读过但未证可授正”，不表示全错或全未读。

26个完整view均可容纳32K，2个可容纳16K；这268K残余不是仅由窗口长度产生。两份额外原R进一步实审包在 `review_slices/ORIGINAL_R_ROOT_REVIEW2.json`，包含原prompt、完整R、原资源闭包及既有精确已批／撤正范围。它们仍是进一步审查输入。

## 实际复杂代码与修订

已恢复653个完整原 `write` 代码正文，653个不同SHA；其中40个有当前业务来源闭包（35 actor、5 legacy business actor）。这不是653个正确程序，也不包括为了凑量把exec片段或多版本算成独立技能。每份可在 `RECOVERABLE_COMPLETE_NATIVE_WRITES.with_code.jsonl.gz` 直接读取并定位原事件。

`first6/` 给出6条真实过程、9个完整原程序及失败／反馈／后续修订，另附真实CAS原输入和最终产物。`extra_exec6/` 给出6个真实命令过程；三条图片分析共用同一来源，不能报成6个独立新机制。全部待root逐内容审核，不以exit0自动授正。

`review_slices/REPAIR4_ACTUAL_ANCESTRY.json` 保全game17/31和video65/83的原动作、真实失败／复试回执、原资源缺口。game17可以从原write7→确定sed15→真实grep/报错16→修订17/回执18恢复3个确切程序版本；其余后续prefix含视觉或临时资源身份缺口。若root采用明确新功能状态、本地实测坏／好材料承接原修订动作，必须保留该条件变化和原动作作者，不能称原prefix等价。

## 552快照的 owner／组件对账

`CURRENT552_COMPILED_SNAPSHOT_INDEX.json` 冻结实际22个原编译文件。`CURRENT552_VIEW_COMPONENT_COVERAGE.jsonl.gz` 保存实际正向target全文、字符范围和token跨度；`WITHDRAWN_VIEW_COMPONENT_COVERAGE.jsonl.gz` 保留478条已撤view记录，撤某view不自动否定原owner全部内容。

基准中58个view能接native消息、33个能接外部历史owner、460个是明确新标注／新功能状态，不要求有原native owner。另1个CV length completion有真实原wire-R但无native消息ID边，由 `CURRENT552_ALIAS_COMPONENT_OVERLAY02.json` 单列。37个native消息R owner＋1个wire-only R owner对应38个原生调用捕获R；不会为凑38而制造native消息。

`DIRECT_QA_AND_OVERLAY02.json` 记录独立原字节读回、34,616个owner正文SHA、653份代码原文相等、552快照正token重计和精确字符范围SHA。R/A归属、原生／历史条件、局部／主控制器能力、未知与真实错误分别保留。任何增量进主训练集仍须有单独质量与双tokenizer／loader准入。
