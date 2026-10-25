# WRD原始思考、行动与闭环决策数据合同

2026-10-25；主体为阶段1独立设计审查，随后按用户授权进入阶段2离线实施，实际数据与核验结果见第10节。未训练、未启动原生会话或修改旧导出器；原独立B/C恢复工作保持。

## 1. 当前确定的问题及修复方向

用户确认完整沉淀中的模型思考与响应均有保存。旧冻结导出未检出显式推理，只能说明其检查范围/字段的结果，不能代表原始日志不存在。v4必须首先定位原始请求、响应/流式块、工具调用与观察，再建立保真母本；新增证据摘要是辅助视图，不能默认代替原始教师思考。

旧实现的具体限制来自本地源码，而不是推测：

- `research/data_prep/wrd_training/training.py::_clean_content`删除thinking/reasoning/redacted_thinking块及think标签段，`_messages`只复制若干字段；即使原始响应另有reasoning_content、analysis或provider扩展，也未被该规范化路径完整保留。旧冻结统计`reasoning_blocks_removed=0`，不证明这些清洗动作实际删过该批正文。
- 旧`PairCompiler.one`固定`enable_thinking=False`，只允许一条当前assistant completion；先分别渲染prompt/full，再要求两种渲染精确前缀稳定。它不适合作为完整原始推理、多助手目标轨迹的唯一编译接口。
- 旧编译器主统计的`eligible=publication_approved AND training_eligible`将公开许可混入训练准入。v4两者彻底分列：本地受控训练数据可以不公开，公开数据也未必适合监督。
- 系统提示只从`evidence/prompts.json.system`及`system-prompt.txt`两处恢复，其他真实request/事件入口需继续查。不能拿当前默认system补过去并冒充原始请求。
- 旧core7工具固定列表不能作为全链路删数据条件；必须恢复每个会话当时实际schema。非核心工具或依赖缺失单列，不通过删历史调用达到“兼容”。

### 17条历史前缀异常的实际结构检查

本轮只读既有`work_compiled_controlled_all/compile_failures.jsonl`对应17条旧候选，未输出企业正文：16条的prefix最后一个角色是assistant，当前目标不含`</think>`；另外1条的prefix最后是tool，而目标正文含孤立`</think>`、不含`<think>`。固定官方模板会依据`loop.last`及`reasoning_content`改变assistant的think包装，也会解析content内的`</think>`。前16条存在连续assistant导致历史末条包装变化的条件；后一条存在正文分隔符被模板重解释的条件。它们不能一概视为无训练价值或直接删除。

修复需对每条完整渲染结果定位其真实段落，比较角色、工具和正文round-trip；不能把最长公共前缀长度当loss边界、删think标签求通过，或给过去插一条虚构user消息。若对连续assistant作合并，必须另存为声明的派生视图并保留原消息映射；正文中的分隔符和真实推理字段分开。任何专用序列化必须记录其与官方模板的差异并验证两模型/推理端一致，不能宣称是未改官方模板的原始记录。

## 2. 母本是原始因果事件，不是最后回答

每个事件保存以下最小字段；正文可为受控存储，公开投影及发布决定独立：

```text
source_id / root_conversation_id / episode_id / request_id / response_id
event_id / native_sequence / raw_file_sha256 / raw_json_pointer_or_line
timestamp_original / timestamp_reliability / role / channel / author
event_type = request | reasoning | assistant_text | tool_call | tool_result | controller_transition | final
payload_original / payload_sha256 / stream_choice_index / stream_delta_index
call_id / tool_name / original_tool_schema_ref / parent_event_ids
model_and_runtime_condition / finish_reason / truncation_or_parse_issues
```

顺序优先采用实际请求/响应ID和原生序列，时间戳仅辅助；机器时钟相邻不能代替因果关联。原始thinking载荷、可见解释文字、工具参数、程序输出、引用的旧对话分别归类。`thinking=off`、reasoning token计数、签名/不透明redacted块不算可训练推理正文；它们仍可作为元数据保留。

流式数据按同一request/choice/tool_index和原序列重建delta，重传去重必须有原事件ID或明确序号；不能按相同文本去重，因为重复字符串可能是实际输出。中断流保留截断状态，不用后来的最终文件补成当时模型已经生成的内容。

原始事件及原文SHA不可变。清洗/脱敏、格式适配、跨阶段摘要均是新投影，记录父SHA、变换规则和字段级映射，不能在主母本上静默覆盖。

## 3. 可靠的推理—动作—观察链

一个决策状态`h_t`仅包含该响应之前已发送给模型的system/user/assistant历史、实际工具schema、当时可读或确已读取的资源与已返回观察。随后记录：

`h_t → 原始reasoning_t / visible_text_t → tool_call_t或final_t → 实际observation_(t+1) → 后续reasoning/action`

推理文本自身不是正确性证明，但原模型实际输出的推理值得保留和审核。目标可以同时监督reasoning、决策、工具名称/参数及必要结束标记。工具观察是下一状态的输入，不是上一响应的输出目标。

必须检查：

1. 每条响应能定位原请求；同一目标不得混入其他choice或重试的思考。
2. 每条工具结果对应前面真实call_id，名称/参数/schema版本可追溯；并行调用按实际归属保留，不人为串成新的单线因果链。
3. 工具返回被原生截断时，历史输入保留模型实际看见的版本。完整资源可作为独立外部文件供后续read，不能替换当时截断观察而假装模型已看全文。
4. review发生后的判断与修订结果可以作后验质量标签，不能回填为screen或make早期已知事实。
5. 修订样本以真实旧版本和真实反馈为输入，后续已验证的诊断/修复为目标；不用最终版本替换旧版本。
6. 原始推理若存在自相矛盾/幻觉/无依据内容，保留母本但标审核状态；不因最终成功就把每个思考token都自动标正例。

## 4. 全自主控制与外层编排必须分清

本轮只读源码确认：`pipeline.py`约625—687行中，缺任务时外层enqueue prepare；对no_skill/workflow两臂enqueue actor；获得新证据后enqueue review；`build(job)`按kind构造阶段prompt。`research/workflow/native.py::run_native`只启动一个原生consumer，其调用者负责lane和阶段调度。因此多阶段日志齐全并不意味着原模型已经自主选择所有阶段转换。

每个`controller_transition`必须有三分来源：

| 来源 | 含义 | 可如何用于训练 |
|---|---|---|
| `observed_model` | 原模型实际决定并发出下一阶段/子任务动作 | 原样恢复与审核后监督，保留实际动作空间 |
| `actual_orchestrator_policy_trace` | 原外层代码按已知状态派发下一阶段 | 可作为明确来源的控制策略示范；不标为教师原始CoT，不偷带新状态 |
| `assistant_derived_demonstration` | 当前助手依据原证据补的合理转换/交接记录 | 派生任务，记录标注者/证据/审核；不假称原生已发生，不计新独立任务 |

单次输入自主沉淀的目标需要学生实际有可调用的动作：读取来源与技能库、生成/修改资源、选择需求、启动真实受控双臂试做、读取结果/费用、修订/停止与封包。原CONTENT_AUDIT记录make调用过`sessions_spawn=2`及`sessions_yield=1`，review有sessions_search/list/history；这证明部分子会话工具曾实际出现，不能据名称就证明其权限、调用参数和返回允许完成完整双臂业务试做。

下一步应只读恢复这类调用的真实schema/结果及运行条件，并核对原生exec可访问的实际命令、文件、网络和授权边界。若没有可用的试做/子任务启动接口，该项是**部署动作空间兼容缺口**，不能用一个`next_phase=C`训练标签代替实现。后续如需补接口，应保持OpenClaw原生工具和会话循环，显式声明公共资源/命令变更；不能在科研外层写替代Agent循环或逐步代替模型执行决策。

完整自主轨迹、阶段内原生轨迹、外层控制策略示范三者分别计量。训练后须用单次业务输入、无人工阶段指挥的原生运行验证自主闭环；分项预测准确率不能替代。

## 5. 可训练记录与监督所有权

```json
{
  "schema_version": "wrd-causal-trajectory-v4-proposal",
  "id": "stable_id",
  "parent_episode_id": "source_episode",
  "root_source_group_ids": [],
  "view": "native_stage|observed_autonomous|orchestrator_control|derived_transition|repair",
  "transition_origin": "observed_model|actual_orchestrator_policy_trace|assistant_derived_demonstration|null",
  "observation_cutoff_event": "event_before_target",
  "event_refs": [],
  "owned_target_event_ids": [],
  "reasoning_origin": "original_response|original_visible_explanation|derived_evidence_summary|none",
  "causal_checks": {"request_link": "unknown", "tool_pairing": "unknown", "future_evidence_leak": "unknown"},
  "outcome_evidence_refs": [],
  "mechanical_status": "pending",
  "semantic_status": "unreviewed",
  "training_tier": "not_admitted",
  "publication_approved": false,
  "human_gold": false,
  "tokenizer_and_template_sha256": {},
  "input_ids": [],
  "supervision_spans": [],
  "reasoning_spans": [],
  "action_spans": [],
  "label_ignore_index": -100
}
```

一个原始目标事件在同一视图曝光周期仅有一个owner窗口；重叠历史均masked。派生摘要与原生目标可以共存，但共享parent预算，额外曝光明确计账。不得把同一写入消息、最终资源文件、多个归档别名和JSON子字段重复算成独立示范。

所有system/user/tool观察、资源输入、非归属assistant历史、错误/未准入目标及padding均为-100。只对当前窗口owned且准入的assistant原始思考/文字/调用跨度计算loss。loss mask不把工具返回当助手生成，不把未知部分用最终文件补齐。

## 6. 失败、unknown和质量分层

机械准入与语义准入分开，至少采用以下数据层：

- **P：已核过程正例**。请求/目标/观察关联完整、原始来源可追、关键工具协议一致；语义有支持，包括正确路线、必要探测、实际可用资源、正确修复或正确拒绝/暂缓。程序exit0只证明执行结果，不单独证明业务正确。
- **S：结构完整的教师silver**。因果和格式通过、没有已知致命内容问题，但语义只经分层校准/抽审；可作为明确权重和来源的训练层，不能冒充gold。全量审核范围与抽审置信区间公开，不再只训练极少抽审通过项而遗漏其余全部价值。
- **H：历史/失败上下文**。真实错误和未决动作可作为后续诊断/修复的masked历史；其中有依据的探测、诊断和修复可单独准入，不按整场失败删除。
- **U：待恢复/不兼容**。请求/系统/schema/结果缺失、截断角色不明、原始推理归属不明，保留和定位；不自动转正，不删除原文。

最终retain不自动把整条轨迹升级为P；reject/defer也不自动成为坏数据。正确否决、发现边界和停止不必要修改正是WRD的重要监督。少数分支优先检查，但样本数量仍以真实父来源/事件为分母。

## 7. 可实施的离线共同编译流程

本节只建议实现路线。使用现有官方缓存资产`output/20261025_wrd_training_preflight/tokenizer_assets/{primary_14b,control_8b}`，核固定revision和文件SHA，无需模型权重或GPU。

1. **冻结母本与索引**：对原始请求、原始流/响应、事件、schema和资源做SHA/大小记录。流重建与事件归属先独立校验；未解决的字段不让分词器“猜”。
2. **一次生成规范化事件序列**：保留原始reasoning字段/段落、消息边界、call/result ID与当时schema，建立source byte/JSON pointer→规范化segment映射。原始数据与新训练序列化分开保存。
3. **先设计训练窗，后渲染**：以完整阶段、明确修订片段及已核自主/控制转换为单元；按因果闭包纳入所需历史，每个owned目标唯一分配。不要为每个助手目标重新tokenize整个历史前缀造成近似O(n²)重复。
4. **一次渲染每个窗**：官方模板对“最后assistant”“最后user”和thinking有条件行为，不能把每个消息模板片段独立相加后声称等于官方全序列。选择经验证的模板span instrumentation：在Jinja生成片段时只跟踪输出字符区间，或使用声明的带generation标记等价模板，并断言其字节输出与冻结官方模板相同。不得把定位哨兵字符串留在训练正文中。
5. **span映射而非前缀猜测**：将reasoning、文字、tool call和结束标记显式归属于目标事件；用一次tokenize产生offsets，将完全落入owned跨度的token标为目标。若token跨输入/目标边界则调整有证据的模板边界或隔离，不能把输入半个token也监督为输出。特殊token零offset需按原模板token位置与角色标记显式判定。
6. **保真验证**：渲染正文逐段与来源字段/声明变换对应；decode owned token区间后与模板目标区间一致。确认原始reasoning未被历史模板分支省略；若省略，修复为已声明、推理端一致的序列化，不能仍标“原始推理已入loss”。工具调用/结果配对、目标角色、EOS及嵌入角色标记分别检查。
7. **两模型独立证明、后续复用计算**：首先逐字节核两份资产和chat template；对每种消息结构/模式做独立双tokenizer全流程校验。资产完全相同且序列化合同相同时，可复用同一已编译input_ids/mask，记录资产等价证明和确定性抽查，不为“验证两模型”重复编码所有巨大前缀。若有任何模板/资产差异，恢复逐记录双编译比较。
8. **去重曝光与预算账**：保存target_event→window/parent/view归属，记录唯一目标tokens、实际曝光tokens、mask前的处理总tokens；阶段、类别、推理/动作分量权重显式，采样权重和loss倍率不重复叠加。
9. **发布投影独立派生**：受控主集与公开版本各有清单；隐私变换影响了程序/工具参数/推理证据时重做机械与语义核验，不能直接复用旧通过状态。新公开字节只从已审投影来。

官方模板中历史推理是否被保留必须实测；不能仅看到JSON含reasoning_content就计算为“监督思考tokens”。若一个事件的原思考不能在当前默认模板下训练，保留其原始字段与待适配原因，不能清空后继续宣称完整过程蒸馏。

## 8. 长度与数据足量的报告分母

必须分别报告：企业来源数、原生执行会话数、完整自主链/完整阶段链/外层策略示范数、原始响应数、原始推理响应数及tokens、动作/决策/修订目标数、最终语义准入、实际可编译、共同16K/32K覆盖、独立来源组及类别/分支覆盖。

总长为输入加目标tokens。完整原始窗、声明的压缩状态窗、资源检索窗三种覆盖分开报；不能把摘要窗的短长度当原始完整轨迹已经覆盖。超过32K的母本不截掉关键前因；可基于当时可见证据生成审核过的状态摘要，训练学生经原生read检索资源，但必须另记派生视图和运行期上下文管理的兼容假设。

“足量”以可支持目标职责判断，不能只设一个动作条数：是否覆盖12类任务、A/B/C/D及C→B/C→D、所有关键取舍、真实资源构建和失败修复、独立业务来源、足够原始思考/决策监督tokens，以及非模板重复的完整过程。当前旧19728非空主体目标、151修订关系、73条四阶段记录只是已知存量，不能直接等同19728合格任务、151偏好对或73独立自主轨迹。

若已有记录主要是外层编排过的阶段会话，数据可以有价值地训练阶段操作与控制策略，但训练后自主闭环效果仍须独立验证。数据合同通过证明可追溯、可训练和因果可靠；它本身不证明14B必然达到理想表现。最终解释应把“机制为何有学习信号”与“新来源闭环是否实测达标”分开。

## 9. 下一步最小实施清单

原始思考入口定位并抽样确认归属→冻结原响应/流及请求→重建同request事件顺序→恢复原system/schema→按三分来源重建控制转换→P/S/H/U分层及语义校准→完整窗/修订窗/转换窗与target ownership→本地CPU共同模板及mask编译→质量/长度/来源/原思考token账→公开投影与Git逐字节核验。

本文件未修改任何现行Agent入口或业务执行器。此后数据处理只做离线转换与审核；训练、Spark前后向、教师再生成、试做或新增原生任务均未由此启动。

## 10. 阶段2实际实施记录与已知边界

离线实现位于`research/data_prep/wrd_reasoning_v4/`：`compile_native.py`提供可复用CausalCompiler，`compile_raw.py`接原request/current-response及机械重建SSE，`finalize_native.py`按真实stopReason排除截断正例，`finalize_raw.py`按原动作结局屏蔽拒绝，`validate_compiled.py`独立读回校验；新增`compile_historical_native.py`保留新发现历史条件。

使用明确声明的Qwen3因果模板变体，稳定保留各assistant的reasoning字段，避免未来last_user/loop.last改变过去包装，并让正文`</think>`保持正文。原模板、变体和instrumentation SHA、两模型官方资产SHA及实际独立双实例调用数均记录。生成块instrumentation须与无标记变体逐字一致；首轮64因额外换行失败已保留，修复后的64全部通过，随后完成全量。此变体尚未接入未来模型API，推理端采用同一序列化是部署兼容必需项，不能宣称当前原生服务已经接线。

冻结原生1763会话及公开清理投影1051会话均已实际生成完整input_ids和多目标R/A/D/E/F跨度及权重。`FINAL_NATIVE_COMPILATION_REPORT.json`与`native_compiled_{controlled,public}_final/`为终止复核版本：受控25141个机械可用位置，完整阶段≤16K462/≤32K1020，632个显式因果前缀，1433个有监督窗口合计4811808监督tokens；其中沉淀主角色943窗/2224228tokens，Actor490窗/2587580tokens。公开13922机械位置，完整阶段≤16K412/≤32K781，247前缀，825有监督窗/3419986tokens；主角色468窗/1368891，Actor357窗/2051095。这些是机械silver数量，不是gold、独立任务或自主完整链数量。

9条原生非空`stopReason=length`保持原文，其中8条曾进入初步机械目标，终止复核已将其loss屏蔽。未因此删除后续真实反馈或修复历史。初步数组/报告原样保留，最终只使用带`_final`版本或父级进一步语义curation投影。

原始思考实际恢复后，已编码45个evolution来源SSE教师响应＋113个历史企业制作/修订响应，共158对、47对含原始思考735279字符。SSE历史evaluation7及来源未确认M5另1未进入该bank。原45个SSE动作结局进一步全量检查为17 OBSERVED、14 APPLIED、12 REJECTED、2 FINISHED；12拒绝输出的全部R/A/D/F loss已归零但原数组与思考完整保留。因此`raw_reasoning_evolution_final/RAW_COMPILATION_REPORT.json`最终有146正面候选，其中35含原R；完整≤32K117对/206840监督tokens，含31条原R，R正文128545tokens及31个跨边界混合token。完整思考的存在和原动作实际应用都不等于当前技能质量gold，旧FINISHED/READY不转换为现行retain。

`COMPILED_DATA_VALIDATION.json`独立核验PASS：两scope全部数组SHA、跨度与owner重算；632＋247前缀逐条等于完整父数组前缀；原生完整decode是15＋12个分层样本，不假称全量decode。47份原始思考全部decode并与source原字段及当前assistant段逐字匹配，确认35仍有正面R、12拒绝全loss0；158个raw渲染及mask fingerprint唯一。原生canonical没有原R，E类可见说明独立统计，不以E冒充隐藏CoT。

额外97个历史原生源按角色选择32 make/screen/review进行真实编码，30 formal、4 technical、31 unknown只保留索引。因inline schema本身截断、未找齐同环境执行证据，没有未经证明补core7；32会话/1260非空位置最终仅2个机械文字目标，≤32K仅1窗849监督tokens。`historical_native_compiled/HISTORICAL_COMPILATION_REPORT.json`如实记录缺口，不能拿1260填充动作正例量，也不能说这些未准入中间记录不存在或没有研究价值。

完整原思考、源记录、历史失败、所有长窗及不能准入的目标均保存，未静默丢弃。当前记录支持有来源的过程/推理SFT与真实修订监督；尚未证明单次输入的自主控制、部署接口兼容或实际训练收益。父级新语义curation、来源隔离及发布清理可能进一步减少正面监督量，应使用最终发布manifest而非本文历史数量直接启动训练。本轮0权重、GPU、训练或新增教师/业务模型调用。

### 公开原思考的实际数组范围

后续通过来源、原结局、AI局部审阅及公开清理后的输入为`curated_reasoning/public/sse_core.pairs.jsonl.gz`9对、`historical_generation.pairs.jsonl.gz`72对。`compile_public_pairs.py`已对这81对实际编译，输出`public_reasoning_compiled_final/`；10条含教师原记录经一致去标识后的reasoning，共175136字符。公开变换明确不是原始未脱敏字节，编译时逐字符验证的是公开source字段，不能移用受控源“原字节保真”的说法。

公开核心81/81编译成功，实际输入1312403tokens，监督92516，R正文49523及10个边界混合token。训练分片互斥≤16K44对、16K—32K32对，共76对/88365监督tokens，其中9对含R（R正文49445tokens及9个边界混合token）；另外5对超32K完整归档，其中包含那1条历史生成reasoning。不能把受控35条正面R或全部67条原SSE思考写成全部已经公开可训练。

历史Actor公开辅助另有234对/33条去标识R，独立`public_actor_aux_compiled/`不并入核心。新的当前tool schema检查屏蔽6个参数无效目标，另3个相同render/mask重复不进入训练分片；可选辅助225对=221短＋4长，242777监督tokens，R正文69300及33个边界混合token。其建议≤10%只是未来损失预算建议，不自动扩大核心数据或证明当前原生工具等价。

`PUBLIC_REASONING_DATA_VALIDATION.json`独立读回PASS：核心81、辅助234全部数组/跨度/source record SHA重算；全部10＋33公开reasoning再次decode并与变换后原字段逐字匹配；短/长/超长桶互斥、复制行与所属all_records完全一致。首轮core因原结局字段为字符串而报9条AttributeError的诊断目录保留；修复后的`_final`81/81成功才是发布版本。上述仍是来源有据的teacher silver，不是语义gold或训练效果结果。
