# 新完整课程训练计划独立复核建议

2026-11-01；审核者 `/root/git_plan_consolidation`。只读审核研究源文件和已验收数据，没有修改双设计稿或Git交付仓库，没有训练、加载权重或派发业务任务。

## 明确主训练对象

当前可将1,250个目标纳入同一个模型的完整A—D逐步策略SFT，训练单位为当前可见状态→经授信的理由／工具动作／决策。全流程的模型执行由固定原生OpenClaw提供环境反馈并继续调用，外层不接管步骤。主模型Qwen3-14B、对照Qwen3-8B；完整原生专家单episode为0不妨碍这种逐步联合训练。当前尚无学生完整闭环成绩。

418契约目标和205过程、627新辅助都已经实际加载验收。技术pool名`contract_optional`是原接口名称，新主课程可以明确将其选为必修阶段，不能只写“默认832”就称已实际把1250安排进同一模型。627新辅助为576给定政策状态和51个CPU资源目标，与原记录分账；205含明确声明的功能投影，不全是原生轨迹。

## 可直接沿用当前数值的完整主课程

| 阶段 | 唯一目标 | 序列曝光 | 累积最大值 | 更新 | 预算profile序列tokens | full53序列tokens | 曝光正tokens |
|---|---:|---:|---:|---:|---:|---:|---:|
| 契约418，一轮 | 418 | 418 | 16 | 27 | 1,316,051 | 1,316,051 | 70,892 |
| 原205＋新627全过程日程 | 832 | 836 | 4 | 209 | 8,928,476 | 19,504,910 | 215,681 |
| 同一adapter接续合计 | 1,250 | 1,254 | 分阶段 | 236 | 10,244,527 | 20,820,961 | 286,573 |

契约阶段末flush尾部2条；过程full日程沿用`exposure11_final`的固定836序列和209累积批，显式重复4个原过程目标，不增加唯一数据量。总曝光正tokens比unique目标284,595多1,978，正是上述4次重复；不能再默称每个目标恰一遍。契约加权量40,186.8，过程full加权量43,510.85，合83,697.65。

不含4次重复的unique数据池统计：预算profile共10,207,038序列tokens、941短309长；full53共20,783,472序列tokens、539短711长。两profile为相同ID与正目标，互斥选择，不能翻倍计数。预算profile中的225条仍完整53目录，其余402显式无工具决策题；这不是运行时gold工具过滤算法。

建议新计划选择一个明确的两阶段接续口径：同一个LoRA adapter与AdamW状态连续，契约阶段结束保存模型和optimizer/RNG/checkpoint，过程阶段接续；全课程仅最初3个optimizer更新warmup，之后使用事前声明的LR schedule。当前54只确定lr5e-5与前三更新warmup，scheduler尚需新计划明确，不能偷偷沿用旧18版cosine/warmup_ratio。可采用constant-after-3-warmup以减少歧义；若采用cosine则写明236步总程及控制臂各自总程，并说明学习率轨迹差异。

## 模型及损失保持项

- 14B revision `40c069824f4251a91eefaf281ebe4c544efd3e18`；8B revision `b968826d9c46dd6066d109eabc6255188de91218`。
- 冻结BF16基座；LoRA r32、alpha64、dropout0.05；q/k/v/o/gate/up/down七投影；embedding和head冻结，不截断LoRA所需反向路径。
- AdamW lr5e-5，betas(0.9,0.999)、eps1e-8、decay0.01、clip1；microbatch1、gradient checkpointing、use_cache=false；两模型顺序训练。
- 正监督严格沿已验收的input_ids/labels/loss_weights，不重新模板化，不通过`enable_thinking=false`覆盖已准入R。原R、再情境R、新作者R分别标记；原205的非原生投影和原新作者权重0.25继续保留，不可一律提为1；新627为0.05。
- 每optimizer累积批以sum(weight×shifted_CE)/全部有效shifted目标位置数计算；不能按权重和归一化，也不能先micro均值再等权。prompt、历史助手、工具返回和错误／未知范围labels=-100、weight0。
- 新辅助过程阶段全局有效mass约6.59%，并非逐批保证；既有日程91/209批>20%、最高81.29%。不把低loss权重当算力减免或梯度影响保证。
- 两模型相同目标ID、顺序、pool、曝光和mask。主候选在通过32K技术验证后按每条原长完整训练，动态长度、packing=false、不静默截断长代码或用户纠正。16K只用于分桶/技术验证，不能只用941短样本却声称1250全量。

## 对照结构

完整主课程应将契约418明确放入每个比较臂，避免“有契约warmup vs 无warmup”混淆辅助收益。

| 每个模型的候选 | 契约更新 | 过程更新 | 总更新 | 用途 |
|---|---:|---:|---:|---|
| Contract＋原205一轮 | 27 | 52 | 79 | 真实过程对照 |
| Contract＋原205匹配4重复 | 27 | 53 | 80 | 真实曝光匹配对照 |
| Contract＋pilot544 | 27 | 136 | 163 | 低成本辅助规模试验 |
| Contract＋full832 | 27 | 209 | 236 | 完整主课程 |

核心为14B/8B × 原过程/加辅助；同模型契约checkpoint可共用分叉，实际费用只计一次再按声明规则分摊。pilot与full是嵌套构造曝光对照，不是独立经验数量曲线。真实曝光匹配80更新控制不是GPU小时匹配；要归因辅助收益，还需按实测同GPU小时或近似相同序列算力的原过程重复控制，重复仍不得当新数据。full53配对可作为接口迁移和计算对照，不要与budget目标相加。

低来源数学习曲线不能预先看所有418契约后仍称来源holdout未见；必须按全局资源血缘处理契约和过程的共同split。原226、H12/static/reserved40与新增dev whole-group持续隔离，不能参与训练、选checkpoint或调阈值。

## Spark具体落地与评测

设备按用户报告的ARM64/GB10/约121GiB统一内存，不能按另一份独立显存或FP4宣传值估BF16训练时间。旧计划的`nvcr.io/nvidia/pytorch:25.11-py3`仅兼容候选，需冻结实际linux/arm64 digest及依赖；保持NVIDIA torch，不装通用wheel覆盖。T0配置/arm64检查、T1权重forward、T2 backward/update分别记账；当前任务只上传计划和数据，三者不执行。SDPA实际backend与16K/32K峰值、host MemAvailable、swap、RSS、allocated/reserved及吞吐须在获准后实测，两模型逐一运行。

完整任务验收使用固定原生OpenClaw发现/读取skills、工具协议和自然结束规则。制作侧主比较T／14B-SFT／8B-SFT；业务消费侧固定同一Actor，只改变技能资源；加两未微调基座用于判断SFT收益。共同输入、附件、工具及预算事前冻结。既有组件dev/test只报组件，不能改名完整流程评测；完整父输入与消费槽须按实际来源边界形成完整任务清单，现八父输入只有五连接组且缺三消费槽，计划与实际材料分开登记。

质量指标：完整沉淀成功率、契约纠正保留、原生工具选择/参数合法性、资源复现与修订成功率、版本/证据一致的retain/stop、独立消费TSR与五维Q。判定回看同版本资源的真实试跑，不能按工具exit0把整段作正loss。Q阈值需在训练外dev事前校准，构造练习的80不是现行业务阈值。开发probe22与24个部分兼容规则挑战只作数据QA，不是学生泛化成绩。

总成本同时列：已发生数据恢复/AI标注/采集、训练与验机、制作/工具、全部失败/修订、评价、Teacher回退、人工；现金、设备时、能耗、经过时间分报。每合格技能总成本以去重最终合格技能K作分母，K_Q质量、K_R减负、K_G交集分别报告，K=0不编单价；公共成本计一次，纯学生与教师兜底分账。训练沉没成本与后续每skill增量都保留，可按不同部署规模N列(C_data+C_train+C_eval)/N+C_infer以及实测通过率校正的单位成本，不能仅按成功末次推理计费。

## 文档同步清单

新完整训练计划将418由可选明确为主课程阶段、规定阶段接续/scheduler/完整236更新，应同步A_B_MODULES和PIPELINE同版并保存原54快照。旧18/52/54、原manifest和11归档保持历史字节，新的总计划明确覆盖哪些旧建议。旧18配置中的lr1e-4、统一acc16、thinking关闭、数据单来源组、尚无mask等均已过时，不能直接复制为新计划执行值。

## 可复用评测实物的精确范围

### 现成组件输入：26个

只用09的05最终版，不通配历史tasks或被撤回组：

- `output/20261031_wrd_curation09/holdout/INPUT_ONLY_EVAL_ENTRYPOINT05.json`，SHA256 `16adeb0bdf999731870ca1b6b77c839a3c53b70712c3fe3506e6618dd8e99a56`。
- `dev.tasks05.jsonl`，SHA256 `059c7c825e73274834fa3ddd20d47bf0321a783e349c27bd669c6cd4f79640a0`，9个组件交付任务。
- `test.tasks05.jsonl`，SHA256 `7109d990e42a6492ac50ec021f5132dee3b0da052966c5f04a6051e25f0f9acf`，17个任务，其中15个交付、2个明确澄清任务。澄清准确率单报，不加入交付TSR分母。
- 原36保留组含10 HOLD，只用26个准入输入；相关28个保留source仍不得反哺训练。原226和static保护边界持续。
- 104个14B/8B×core7/full53模板实例和416个实际input-only数组已独立验收，全部labels=-100、weight0。`output/20261031_wrd_curation09/eval_input_arrays09_independent/EVAL_INPUT_ARRAYS_INDEPENDENT_QA.json`为回执。core7是组件条件，不是实际原生执行权限。原生业务组一律完整53环境；已有full53初始输入27291—29576，只说明初始输入，不证明动态历史和回复余量。

当前这些数据可以直接用于编排组件评价：冻结输入与rubric后，训练执行另获授权、模型服务及原生API预检通过即可按清单产生模型输出。此处的“可以编排”不声称目前已加载模型或原生启动配置已通过。

### 现成完整父输入：8个输入包、5个连接组

入口`output/20261031_wrd_curation10/parent_inputs/PARENT_INPUT_INDEX.json`，SHA256 `c0777bd10857a89a62e60bc2f6c846fb63308c26e6cc982902b216fc4df8c130`；配套`CONSUMER_INDEX.json`、`SOURCES_AND_MATERIALS.json`及每父`READINESS.json`。

实际8父＝train2／dev2／test4，9个不重复consumer输入与rubric、13个父→consumer绑定，41引用已逐字节核；原材料含两个真实PDF。dev01游戏父仅有一个consumer、缺第二个；dev02确认清单父缺两个consumer，三缺口均在dev。test01—04已有各两个consumer，但四父和互为消费者的四来源连成同一component，统计按一组聚类，不能称四独立组。train02两CV consumer来源ID不同但JD实质同文；两case可检查操作稳定性，不能当独立来源覆盖。

父输入中的总体委托是已标记新作者需求，原会话字节保持；消费者只投完整原user及合法前提，原助手答案、历史失败反馈和evaluator-only rubric不挂载给父/Actor。`sources/`、候选元数据与完整隔离audit不默认挂载，防跨任务答案泄漏。原生execution-ready0说明尚需运行时预检，不能转成“训练数据不能覆盖完整A—D”的结论。

### 评价执行顺序与预算建议（计划，不执行）

先完成不接业务数据的模型API／原生工具协议预检，然后只用9个组件dev挑选checkpoint和参数；test17在选择冻结后一次检验。完整父任务dev必须先补齐上述3个真实消费槽、冻结Q合格标准、资源版本SHA和工具宿主权限，再验证同一模型从总体委托自主执行到终态；其余步骤由原生循环自主安排。完整父test四起点作为同组稳健性检验，不以其样本数主张广泛跨任务显著性。若追加独立父来源，先全组冻结为holdout，再制作输入，不从训练来源随机切片。

以下为可在新配置中事前冻结的**初次输出预算**，采用四模型臂B14／S14-full／B8／S8-full；组件真实过程消融S14-real／S8-real和同期Teacher为另列扩展，不能隐含免费加入。Q每task一个独立会话，对匿名随机排序的四臂输出分别评分，不能混成一个总分；保留至少20%人工双审，dev至少2题、test至少4题。

| 组件阶段 | 模型输出会话 | 独立Q会话 | 合计native初次会话 | 按每输出8请求、每Q4请求记账的初始总配额 |
|---|---:|---:|---:|---:|
| dev9×四臂 | 36 | 9 | 45 | 324 |
| test17×四臂 | 68 | 17 | 85 | 612 |

公开预检若采用父1＋子1，另2native／8requests并列入dev总账，dev初始计划为47native／332requests。请求数是未来显式预算选项，须沿统一原生会话预算实现，不能由外层改工具返回或代模型提前收尾。超时、网络失败、重试、修订、Teacher兜底均另记并扣总额，不能用初始槽位冒充全部成本；如不追加额度，预算到线后停止新增派发，已经运行会话按统一终态协议收口。

建议组件dev IO预算12M tokens／12小时、test24M／24小时，包含全部失败和Q；这是新的计划配额，不是预测训练/评测一定可在其中完成，用户本轮没有授权运行。每次dispatch按完整请求＋最大回复预留，未知usage保守记未知，不按0。全53动态上下文的最大长度与输出余量须在实际共同服务配置核实；若服务不能完整接收某请求，记为技术结果，不能暗删历史或只替学生缩工具。原会话1800秒和回复上限32768保持，实际输出受服务上下文余量约束。

完整父dev补齐后按T／S14／S8三个制作臂，各2父＝6父制作；每父两个case，消费使用N／T-skill／S14-skill／S8-skill共16消费会话；每case绑定一个匿名四臂Q，共4Q，合26native初次会话（公开预检复用已完成可验证receipt，不能凭空当完成）。按父32、消费者8、Q4的候选配额是336requests。完整父test四起点同口径是12父制作＋32消费＋8Q＝52native／672requests，但仅一个连接组，不叠加为四独立父经验。上述是明确的新评测提案，不能借旧24native训练采集预算自动执行；修订和再消费另计且需同版SHA。

Q阈值在dev外或评分校准材料上先冻，不用任何test反馈修改训练。当前预给政策练习的80不可直接生效为真实K门槛。真实K_Q/K_R/K_G必须由本版本的独立消费交付、Q和完整成本共同支持；长期独立覆盖增量与第一版SFT的可训练性分别报告。

## 建议新增配置字段（设计55）

1. `design_revision=5.0.55`、`change_id=ALG-20261101-01`；数据合同另列`base_checkpoint=10`、`auxiliary_checkpoint=11`及原manifest/package SHA，不能把旧数据manifest版本改55。
2. `plan_status=COMPLETE_PIPELINE_STEPWISE_SFT_PLAN`、`training_started=false`、`execution_authorized=false`、`is_launch_configuration=false`；不把文档值作为实际训练成绩。
3. `required_pools`、`stages`明确契约418必修及过程832；每阶段ID/order或固定seed与算法、microbatch、accumulation、尾部flush、曝光/unique/tokens/更新；主课程总1250／1254／236，原4重复ID显式列出。
4. `selected_profile=budget_projection`与`alternative_profile=full_native53`互斥；`stage_resume={same_adapter:true,optimizer_state:carry,rng_state:carry}`；全局step、warmup语义、scheduler和phase边界checkpoint策略。
5. `loss_normalizer=valid_shifted_target_count`、`preserve_canonical_span_weights=true`、`synthetic_weight=0.05`、`retemplate_inputs=false`、`packing=false`、`truncation_allowed=false`，明确shift对应logits[:-1]、labels[1:]、weights[1:]。
6. `common_max_sequence_length=32768`与16K/32K分桶、`max_length_includes_target=true`；`on_device_runtime_verified=false`、ARM64 digest/lock、attention backend实测待填。服务推理的动态上下文与训练32K参数分开。
7. `source_isolation`保护原226／H12／static／reserved40／新增dev whole-group；`component_eval`固定05版入口与9/17数量；`parent_eval`固定8/5/13/3现状、数据只读挂载策略、评测预算提案，不能布尔赋值native-ready=true。
8. `experiment_arms`区分完整主训练、真实过程对照、pilot、full53对照和算力匹配控制；共享契约checkpoint的成本只计一次；低来源曲线不得全域契约预曝光。
9. `cost_accounting`分别记录数据/训练/技术预检/全部失败/修订/Q/Teacher/人工；K分母与UNKNOWN处理、纯学生及Teacher兜底分账、价格时间来源、实际设备小时/能耗。

证据路径：`research/plans/20261031_wrd_curation11/{TRAINING_STRATEGY11,ACTUAL_DATA_REPORT11,EXECUTION_AMENDMENT11}.md`；`output/20261031_wrd_curation11/exposure11_final/{SUMMARY,EXPOSURE_SCHEDULES11,FULL_REAL_EXPOSURE_CONTROL11}.json`；`research/data_prep/wrd_curation11/curriculum_loader11.py`；`output/20261101_wrd_training_value/ALL1250_JOINT_TRAINABILITY_QA.json`；`research/plans/20261025_wrd_14b_spark`仅作历史硬件及评测协议来源。评测材料现状另见09 holdout最新05、10 parent_inputs README及BUILD_QA。
