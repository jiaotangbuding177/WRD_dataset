"""Build the bounded research assessment from completed v8 quality audits."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "output/20261026_wrd_quality_v8"


def read(name):
    return json.loads((OUT / name).read_text(encoding="utf-8"))


def main():
    native = read("NATIVE_QUALITY.json")
    chain = read("CHAIN_QUALITY.json")
    raw = read("RAW_RECOVERABILITY.json")
    artifact = read("ARTIFACT_STATIC_QUALITY.json")
    literature = read("LITERATURE_EVIDENCE.json")
    numeric = read("NUMERIC_CONTENT_COUNTEREXAMPLE.json")
    targets = native["global_target_metrics"]
    episodes = native["global_episode_metrics"]
    branches = chain["output_branch_coverage"]
    chains = chain["documented_chain_coverage"]
    raw_native = raw["native"]["totals"]
    provider = raw["provider_responses"]["totals"]
    case_reviews = [json.loads(line) for line in (OUT / "CASE_REVIEWS.jsonl").read_text(encoding="utf-8").split("\n") if line]
    local_reviews = [json.loads(line) for line in (OUT / "LOCAL_SEMANTIC_FINDINGS.jsonl").read_text(encoding="utf-8").split("\n") if line]
    assert len(local_reviews) == 18 and len(case_reviews) >= 20
    assert native["population"]["assistant_positions"] == 32342
    assert artifact["counts"]["python_syntax_pass"] == 57
    pins = [{"path": str(OUT / name), "sha256": hashlib.sha256((OUT / name).read_bytes()).hexdigest(), "bytes": (OUT / name).stat().st_size} for name in ["NATIVE_QUALITY.json", "CHAIN_QUALITY.json", "RAW_RECOVERABILITY.json", "ARTIFACT_STATIC_QUALITY.json", "LOCAL_SEMANTIC_FINDINGS.jsonl", "CASE_REVIEWS.jsonl", "LITERATURE_EVIDENCE.json", "NUMERIC_CONTENT_COUNTEREXAMPLE.json"]]
    summary = {
        "schema_version": "wrd-v8-data-sufficiency-and-quality-assessment",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "requested_goal": "14B primary/8B control: native agent autonomously explores complete conversations, selects reusable work, constructs resources, trials/evaluates, revises, and delivers qualified skills at lower total cost per qualified skill.",
        "raw_scale_justifies_serious_domain_SFT_preparation": True,
        "current_dataset_ready_to_train_full_autonomous_goal": False,
        "ideal_model_outcome_proven_or_guaranteed": False,
        "final_semantically_and_source_admitted_training_count_established": False,
        "old_native_population": native["population"],
        "old_native_raw_target_tokens_including_controls_not_admission": targets["target_body_tokens_including_controls"],
        "old_derived_serialization_nonempty_le16k": targets["nonempty_causal_end_le16k"],
        "old_derived_serialization_nonempty_le32k": targets["nonempty_causal_end_le32k"],
        "lengths_not_original_complete_API_context_coverage": True,
        "documented_outer_chains": chains,
        "retained_task_categories_covered": len(chain["original_catalog"]["categories_retained"]),
        "all_task_categories": len(chain["original_catalog"]["categories_all"]),
        "missing_retained_positive_categories": sorted(set(chain["original_catalog"]["categories_all"]) - set(chain["original_catalog"]["categories_retained"])),
        "bounded_local_window_reviews": len(local_reviews),
        "stratified_chain_reviews": len(case_reviews),
        "population_semantic_pass_rate_or_quality_score_estimated": False,
        "newly_censused_native_session_ids": raw_native["unique_native_session_ids"],
        "newly_censused_provider_response_groups": provider["distinct_provider_id_or_response_content_groups"],
        "native_and_provider_records_not_added_as_independent_workflows": True,
        "model_weights_loaded": False,
        "training_started": False,
        "new_teacher_or_actor_runs": 0,
        "original226_training_and_threshold_isolation_unchanged": True,
        "raw_data_or_existing_masks_changed": False,
        "source_pins": pins,
        "research_recommendation": "Recover original matching inputs and schemas, adjudicate original226 at target/resource visibility boundaries, retain correct process and repair supervision, group independent tasks before splitting, and only then run a separately authorized native closed-loop pilot. Do not generate more teacher data solely to hit an arbitrary row count.",
    }
    (OUT / "ASSESSMENT_SUMMARY.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# WRD数据量、质量与14B目标可达性评估（v8）", "",
        "**结论：原始监督规模已足以支持严肃的领域SFT准备与可行性试验，不能再以93／106条否定整批数据。但当前可直接训练的最终数据集仍未就绪，也没有证据保证一次SFT就获得完整、自主、教师等效且更便宜的WRD模型。** 主要缺口已从‘入口没找到’具体化为输入保真、监督质量、来源隔离、独立任务覆盖和自主协调验证。", "",
        "用户目标保持：14B主模型、8B对照；从完整会话出发自主探索、判断复用价值、构建工作流与资源、试做评估、按反馈修订、封装交付skills。不会将目标缩成分类器、最终SKILL.md模仿或工具格式生成。模型仍需实际原生OpenClaw环境提供发现/读取、工具、反馈和持续会话；权重本身不能执行文件或工具。", "",
        "本轮没有训练、加载权重或启动新的Teacher/Actor/业务复跑；没有改原数据、旧mask、原226边界或当前并行消融。文献结论、实测数据事实、局部语义观察与建议分别列明。", "",
        "## 1. 本轮真正做了什么", "",
        "| 层次 | 实际覆盖 | 不能据此认证的事 |", "|---|---|---|",
        f"| 旧native母本 | 全部1763会话、32342助手位置、30438工具调用；逐原消息hash/行号、工具时序、目标长度与重复代理 | 全部业务语义正确、原系统输入全部完整、全部可训练 |",
        f"| 新入口正文恢复 | 5613个所选载体路径全部读取，native按身份、provider按响应ID/内容分别去重；另精确C会话逐记录解析 | 各格式相加成独立任务；旧已恢复记录冒充新增 |",
        f"| 过程链 | 全121路线/1751逻辑job/1822attempt引用，20个分层原文链案例 | 文件齐全等于学生自主完成整条流程 |",
        f"| 最终资源包 | 全29包/154文件静态检查；57个Python语法、12个JSON及124个具体资源路径 | 实际运行可靠、领域正确性、独立质量Q或降本 |",
        "| 局部语义抽审 | 六个旧阶段各3个不同路线，固定SHA排序抽18个会话的最后写入/可见响应窗口；另有20条定向链审查，可能重叠 | 总体语义合格率或人工专家金标；本轮不报一个伪精确质量分 |", "",
        "可复核原始证据、逐目标质量账和脚本随报告提供。语义抽审是本助手的研究评估，非领域专家盲评；未读完的部分明确不认证。", "",
        "## 2. 数据量究竟够到哪一步", "",
        f"旧入口非空助手目标{targets['nonempty']:,}个，原目标体（含模板控制符）共 **{targets['target_body_tokens_including_controls']:,} tokens**。其中{targets['has_visible_text_with_tool_call']:,}个响应同时包含可见说明与动作，{targets['text_only_response']:,}个纯文本响应，{targets['explicit_write_edit_patch_tool']:,}个显式write/edit/patch动作。存在充分的过程监督材料，不能概括成‘只有单步动作’或‘只有成品’。", "",
        f"但它们不是{targets['nonempty']:,}个独立WRD任务。全库Actor业务来源按现存声明/选例只核到{chain['source_independence']['all_actor_case_sources']}个不同来源；29 retained路线的声明学习来源{chain['source_independence']['retained29_declared_learning_sources']}个，历史业务试做来源{chain['source_independence']['retained29_actor_case_sources']}个（当前活动来源44个），两整库集合有{chain['source_independence']['retained29_declared_learning_and_actor_overlap']}个相交。这是跨整库交叉；同一路线内核到学习/试做重叠的是3条路线，不能把整库交叉都算同路线自测泄漏。声明不是实际全文读取证明，试做也不是独立外部泛化认证。来源、路线、阶段会话、重试、调用、步骤和token必须分别计数。", "",
        f"在补根集合中还恢复{raw_native['unique_native_session_ids']}个不同native身份/{raw_native['assistant_responses']}个响应，均不在旧1763内；其中67已在v4历史恢复，13相对两旧入口新见。另有{provider['distinct_provider_id_or_response_content_groups']}组provider响应，全部匹配实际请求。这些与native有身份重叠，且含正式评测、技术和历史不同执行条件，**不相加冒充新增合格训练样本**。", "",
        "75.27GB描述存储路径，其中大量是输入复制/缓存。当前应按‘去重后的独立来源与完整任务、正确可监督目标tokens、阶段/分支覆盖’判断充分性。现在可以否定‘原始量太少所以不值得训练’，不能据此肯定‘足量达到完整自主目标’。最终语义与原226来源交集后的可训练数量仍待逐目标准入，这轮不捏造一个新最终数字。", "",
        "## 3. 过程链价值与目标覆盖", "",
        "| 已核项目 | 事实 | 对训练的含义 |", "|---|---|---|",
        f"| 过程档案接口组 | {chains['all_routes_A_B_C_outer_interface_groups']}/121路线，29 retained全部29均可关联原筛选、制作、正选题、两臂上下文与评审接口 | 你的完整pipeline材料确实存在，不能再只保留最后结果；仍是档案关联代理，未逐一认证所有时序/版本/语义 |",
        f"| 真实反馈连接 | 114包与原review字段规范JSON投影相同，113包另有后续native实际读取证据；论文引用修复有完整有界生产→投影→读取→局修/回归证据 | 可训练观察反馈后的修订，原v6未证明producer-prefix字段不能解释成没有真实修订链 |",
        f"| 终包与版本 | 29包154文件均能匹配至少一个原native输出；29包原输出树内容版本合76（非独立任务） | 保留成功版本和演化路径，版本/副本不能充独立样本 |",
        f"| 正向终包类别 | {len(chain['original_catalog']['categories_retained'])}/12类，缺ASSIST/KNOW/TECH同口径retained正例 | 不足以声称全部12类均有同等正向训练与验收覆盖；不等于基座绝无迁移可能 |",
        f"| 选题正负分支 | tasks.json {branches['tasks_attempts']}份：{branches['tasks_positive_attempts']}有case、{branches['tasks_zero_case_attempts']}零case；另10份旧development_tasks有20个选例记录 | 零case约七成，可含正确的缺件/不匹配/停止推理；要细分原因、平衡正负，不把它们丢弃或当成功制作 |",
        f"| 评审分支 | {branches['review_attempts']}份原review：retain31/revise180/defer122/reject14 | 大量修订/暂缓是价值所在；不应只取retain。当前catalog终态还混有用户停轮/外层限额 |",
        "| 自主全链控制 | 本轮121路线图没有核证由同一模型策略自主决定A→B→C→修订→D的原生示范；更广历史全局仍未知 | 当前阶段任务是由外层程序派发，发布copy及停轮也由外层/用户控制。需要显式整理协调决策监督，不能用阶段文件齐全证明已学会自主协调 |", "",
        "原链中7条路线最新原review仍为revise，但catalog为1 candidate/6 rejected；用户停止或预算上限不能改写成模型认为资源无价值。原程序运行条目1654是making记录里的自述数量，不等于1654次独立验证已被本轮认证。", "",
        "## 4. 数据质量：工程结构强，输入保真和语义标签仍需修复", "",
        "| 维度 | 全量/局部核查事实 | 处理意见 |", "|---|---|---|",
        f"| 工具因果时序 | 30438调用中30437有结构配对，1个缺结果；{targets['observed_tool_failure']}个目标见显式工具失败 | 结构保全度高。失败测试/探测可以正确，错误后修复应保留；不以exit0或isError单独判业务正误 |",
        f"| 输入capture | 1577份system快照含truncated、2份损坏占位、184份缺失；1579份system-prompt/prompts旁档也未直接补全 | 缺的是捕获保真，不自动代表原上下文永远丢失。只能按相同episode/请求ID补原wire，或有版本证明地重建并标注；不能借别的会话system |",
        "| 新原请求恢复 | 6个补根native身份有本episode完整API记录，包含完整system/52工具；不能泛借给其它版本 | 优先使用真原件。没有逐身份还原前，不称完整模型输入已复原 |",
        f"| 工具适配 | 28442个core7调用，1996个非core调用；{targets['schema_unknown_targets']}目标缺已恢复schema、{targets['arguments_invalid_under_recovered_schema_targets']}目标在现有schema下实参不符 | 补同版原native schema/工具访问约定，逐条判正误及修复。接口缺证与模型错误分开，不直接丢整会话 |",
        f"| 重复与轮询 | {targets['is_process_poll']}次poll，仅占原目标tokens约{100 * targets['poll_target_body_tokens_including_controls'] / targets['target_body_tokens_including_controls']:.2f}%；ID中立精确动作payload有24879型、7463次重复出现 | 不把轮询当数据少的借口。相同动作在不同状态可必要；按独立任务/别名与来源分组控制权重，重复代理不是语义删数依据 |",
        "| 中间JSON | 259 tasks/347 review/10旧development_tasks可解析；282 making中278可解析，4份语法错误 | 保留原错与后续上下文，给错误字段/错误完结语适当mask；不得把write成功当JSON正确 |",
        "| 成品静态 | 154/154 SHA匹配；57/57 Python语法、12/12 JSON通过，124处具体资源路径存在 | 有可复用真实资源，值得蒸馏；语法/链接通过不是运行、领域内容或独立Q认证 |",
        "| 语义反例 | 抽查到done记录明确说尚待测试/外置证据；CSS白字/#00C4A3对比度2.228:1；另有真实错误恢复与有证据的局部修订 | 内容须分步审核，不统一正loss。抽审不推算全库错误率 |", "",
        "CSS反例只认证实际代码里的这个颜色对；普通文字/大文字参考门槛分别为4.5/3。依据：[W3C WCAG 2.2](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html)。它表明流畅说明、工具成功和文件存在可以同时伴随可测内容缺陷，不用于推断其它路线质量。", "",
        "### 原始思考怎样处理", "",
        f"不能再把旧native没有独立R字段概括成没有思考。旧母本有8147个‘可见说明＋动作’响应及结构化reason；新provider集合有{provider['with_original_readable_reasoning']}个响应含可读reasoning字段。6个本episode API审计身份中，56条同responseId原wire有该字段、native独立R却缺失，已经核到字段保真问题。服务的progress也会写reasoning_content，需与真正推理分开，不把一切同名字段都当内部CoT。", "",
        "指定C盘Codex文件为95个task_started的跨轮历史，不是一条修复示范。按真正LF分隔后17016条JSONL均可解析、1893次工具调用全配对；2296个reasoning项是encrypted_content，raw_content为空，只有29份summary可读（7643字符）。加密串不是可训练原始思考；可读summary也不冒称完整CoT。本轮保全源文件，不伪造解密或事后补写教师思考。", "",
        "### 16K／32K与loss mask的判断", "",
        f"旧派生训练表示上，非空目标前缀≤16K为{targets['nonempty_causal_end_le16k']:,}/{targets['nonempty']:,}（{100*targets['nonempty_causal_end_le16k']/targets['nonempty']:.2f}%），≤32K为{targets['nonempty_causal_end_le32k']:,}（{100*targets['nonempty_causal_end_le32k']/targets['nonempty']:.2f}%）。这不是原完整API输入覆盖率：system/schema补回后必须重编。原tokenizer证据为82会话独立双次编码、1681会话因两模型资产逐字节一致而确定性复用，本轮核了资产、数组和32342原目标hash/边界，没有假称全部重新双分词。", "",
        "旧机械派生正loss25141/零loss7201，不是当前质量准入数。当前质量标签不得自动改变旧mask：错误动作/不实结论不正向模仿，仍留上下文；正确观察后的修订及原真实推理可监督；系统、用户、工具反馈不当助手答案。不能用截去早期要求/保护来源的尾窗伪造干净完整链。", "",
        "## 5. 原226与独立性是实际约束，不能靠样本膨胀解决", "",
        f"全121中{chain['original226_boundary']['routes_with_declared_learning226']}路线声明学习来源涉及原226、{chain['original226_boundary']['routes_with_selected_business226']}路线选择的业务来源涉及原226；29 retained对应15与8路线。声明依赖、真实祖先、未决缺证、仅禁止句分别保留。现存episode级资源范围标签为1139 HOLD_PROTECTED、560 HOLD_MISSING_EVIDENCE、64 ADMIT，**只是旧范围证据分布，不是本轮新训练清单**，也不能把后段保护依赖倒灌成所有早期prefix都已暴露。", "",
        f"{chains['all_routes_A_B_C_outer_interface_groups']}个过程接口组并不自动产生可用训练链。其中{chain['original226_boundary']['outer_groups_with_no_declared_learning_or_selected_case226']}组未直接声明/选中226，仍须核正文和资源祖先。全选定阶段attempt都已证明非226闭包的接口组本轮尚未核证；这强于‘存在某条可恢复的干净子链’，不能据零值宣称所有中间数据无价值。下一步要逐目标按当时实际可见输入和资源版本核准，未知不能装成干净，也不能装成已污染。", "",
        "去重/切分必须以实际来源、共享资源及反馈祖先分组。上述整库交叉与同路线重叠各有不同分母，均不能据原试做retain直接宣称独立泛化；窗口随机切分会让同任务不同版本跨train/dev。原226不进训练，也不用于选择超参/门槛；新的开发验证须另按干净来源群留出。", "",
        "## 6. 文献：支持可行性，不支持按行数保证效果", "",
        "| 原始研究 | 数据/单位与结果要点 | 对本项目的限制 |", "|---|---|---|",
    ]
    for study in literature["studies"]:
        lines.append(f"| [{study['title']}]({study['url']}) | {study['reported_data']} {study['reported_result']} | {study['implication']} |")
    lines += ["", "最贴近本次目标的近期反例是Qwen3-14B客服工作流研究：其局部指标提高仍未转化为可靠完整执行。但该研究为单域、采用严格参考工具调用回放，会拒绝部分有效替代路径；本项目不能据它宣布SFT必失败。应吸收的是评估要求：在学生自己的历史与真实工具返回上验收整条流程，分别报告文字、动作、执行、交付质量，不能以gold-history下一步得分代替闭环成功。", "",
        "## 7. 这批数据配怎样的训练方法，才有因果依据", "",
        "这是研究建议，尚未实现为新训练mask/配置，未授权启动训练。", "",
        "1. **以完整任务链组织，以步骤定位监督。** 将原会话→筛选理由→资源版本→双臂试做观察→评审→修订→冻结/暂缓保留为可查询因果图。单步切窗只是训练载体，不能丢掉前因后果或把一个任务反复算新增任务。",
        "2. **角色与目标分开但保留整条pipeline。** 筛选学new/reuse/defer/no_value的证据判断；制作学资源复用、代码/模板与实际复现；Actor记录既可在明确执行角色下监督，也必须是后续评审的观察；评审学证据/质量/成本分开判断；修订学观察后定位与局修。按独立任务和分支平衡，避免大量低层I/O或同一no_skill别名主导权重。",
        "3. **原思考和修订是目标的一部分。** 使用真实可读R、可见说明和结构化reason，标清来源。错误探索留作上下文，已核正确的恢复/修订承受loss；不统一删除失败，也不把错误动作及错误完结语同权当正确答案。这与AgentRefine/SRFT的证据方向一致，具体mask须另行核准。",
        "4. **显式处理协调能力。** 现有程序派发/用户停轮可整理为‘规则或用户来源的协调标签’，不能伪称原教师CoT或学生自主决策。要训练完整自主沉淀，需要让模型学习在当前状态下选阶段、请求缺件、试做/返修/停机和最终交付的接口，并在原生环境闭环验证。保留你已验证pipeline作为约束与脚手架是第一阶段可检验方案，不代表将最终目标降为节点分类器。",
        "5. **先修复现有数据，不先买更多教师生成。** 优先恢复同请求system/schema/R与反馈祖先、矫正角色、审核正确步骤/停止分支、建立来源群切分和可靠mask，再看干净完整正链/修订链的缺口。只有学习曲线与独立开发反馈显示覆盖不足，才按具体类别/失败状态有界补采，不硬凑10万或80万行。", "",
        "因果主张应是：当前可见证据＋真实推理/动作教模型选下一步；反馈与版本演化教模型利用观察纠错；协调监督教它组合阶段；原生闭环及独立Q检验这些局部能力是否真正组成完整沉淀能力。最后一步未做，就不能说前面数据已经保证理想结果。", "",
        "## 8. 怎样判定达到了你的效果与算力目标", "",
        "当前最有依据的预期是改善已覆盖路线上的WRD规则、工具使用、资源制作和反馈修订；对全部12类、未知环境的自主探索、稳定教师等效和总成本降低，仍属待证。只增加epoch或重复窗口不会补齐这些能力。", "",
        "后续经单独授权训练时，14B/8B使用同一干净来源分组、任务、工具、预算与原生OpenClaw流程；比较基座、领域SFT和原教师。开发集先确定规则，原226只保留其原评测边界。先分别看阶段/修复准确性，再实际运行新输入上的完整A→D；错误状态由模型自己的历史产生，不每步重置金标前缀。", "",
        "验收必须同时看：完整交付TSR、独立五维Q、正确不生成/暂缓与成功停止、复现及跨案例复用、每条路线最差分支、重试/人工/教师回退、真实耗时和所有模型/工具用量。原retain或输出文件数不能代替这些指标；本轮不虚构训练后的成功率或Spark吞吐。", "",
        "每个合格技能的总成本 =（本次新增一次性整理/标注、训练、验证总成本＋同一考核周期全部在线推理、工具执行、外部视觉/生成模型、重试、人工和教师回退成本）÷ 该周期独立验收合格技能数。若跨多个周期分摊一次性成本，分摊份额只计一次，再除对应合格数，不二次摊销。历史沉淀已付成本另列，不能在未来替代比较中反复计作新增支出。旧native中1066目标/301会话有外部模型调用线索；字符串提及不是实付调用数，必须取真实计量。14B文本模型继续借视觉/生成模型时，相关算力不能被说成已全部蒸馏掉。", "",
        "训练是否回本要由实际合格率与单位在线成本决定；没有原生学生闭环结果，本轮不给一个保证节约比例。评估学习曲线应比较不同独立来源规模并保留同一干净开发集，而不是用重复次数制造‘数据越大越好’。", "",
        "## 9. 本轮交付与仍未完成的工作", "",
        "- 已完成：全量结构/重复代理/长度与保真审计、新入口正文恢复核查、全路线链覆盖、18窗局部语义＋20链案例、29终包静态检查及原始文献调研。",
        "- 未完成：全量语义/来源准入的新SFT正文与数组、完整system/schema逐身份恢复、协调监督编译、独立开发/闭环模型验证。这些不是本轮已完成的训练数据包，也不能用一个新的候选清单冒充完成。",
        "- 原226继续隔离；本轮原样本/缺陷观察没有反哺训练或改门槛；训练、权重与业务复跑均为0。", "",
        "主要证据：[结构审计](NATIVE_QUALITY.json) · [原入口正文恢复](RAW_RECOVERABILITY.json) · [完整链与来源](CHAIN_QUALITY.json) · [链案例](CASE_REVIEWS.jsonl) · [局部语义案例](LOCAL_SEMANTIC_FINDINGS.jsonl) · [资源静态检查](ARTIFACT_STATIC_QUALITY.json) · [数值反例](NUMERIC_CONTENT_COUNTEREXAMPLE.json) · [文献证据](LITERATURE_EVIDENCE.json) · [结构化结论](ASSESSMENT_SUMMARY.json)。所有原始正文仍在原地址；公开研究报告使用去标识观察与精确引用。", "",
    ]
    (OUT / "QUALITY_ASSESSMENT.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"report": str(OUT / "QUALITY_ASSESSMENT.md"), "report_sha256": hashlib.sha256((OUT / "QUALITY_ASSESSMENT.md").read_bytes()).hexdigest(), "source_pins": len(pins), "training_started": False}))


if __name__ == "__main__":
    main()
