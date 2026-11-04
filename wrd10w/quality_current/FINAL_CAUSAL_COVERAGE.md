# 实际阶段覆盖与恢复优先级

2026-10-29，实际529目标／146069监督tokens；契约436、过程93，过程仅12来源／9联合component。

| 实际stage | 目标 | 监督tokens |
|---|---:|---:|
| A_source_contract_management | 429 | 73295 |
| A_current_user_delta_checkpoint | 7 | 1463 |
| A_screen | 1 | 2742 |
| B_make | 1 | 2460 |
| B_revision_real_state_reproduce | 1 | 332 |
| B_revision_real_state_repair | 1 | 1676 |
| B_revision_real_state_retest | 1 | 306 |
| C_trial_skill | 2 | 781 |
| C_review | 1 | 387 |
| D_new_post_terminal_state | 1 | 290 |
| historical_workflow_design_diagnosis_and_falsifiable_plan | 26 | 33153 |
| B_historical_local_resource_repair | 3 | 1098 |
| B_make_CV_extract_evidence_process | 21 | 6469 |
| B_make_HTML_animation_resource_process | 27 | 14193 |
| B_new_state_complete_verified_resource_write | 4 | 4511 |
| B_historical_style_verifier_repair | 1 | 174 |
| B_historical_helpers_resource_construction | 1 | 1891 |
| B_test_oracle_diagnosis_and_revision | 1 | 848 |

token component_D是正文类别，不能当作pipeline D封装覆盖。原生自主A—D示范0、正向合格保留0、独立dev/test数组0，整体训练NOT_READY。当前可用于组件学习的假设与反证见TRAINING_PLAN。

扩充顺序：其它干净来源的完整资源→真实失败归因／局修→同版本复试及独立质量→正向合格封装／反向STOP→原生自主调度。原226／H／静态dev-test继续隔离，未知保留，不靠重放或切窗补独立数据。

## 质量验证、成本与可证伪因果链

先冻结来源独立的组件开发题和完整闭环题。当前实际dev／test序列0，不能从train行切随机窗口冒充独立验证；同来源资源、参数变体和反馈祖先不可跨split。原226只作既定评测边界，不用于调参、标签或准入门槛。AI评审需独立原文／产物核查与校准，不把它自己的成功状态或绿测试当真值。

主对照为同Spark服务／适配器／模板／预算／工具权限下base14B↔SFT14B、base8B↔SFT8B。Teacher另列实用参照；Teacher的SDK prefix和部署差异不能全归因SFT。每个模型均从总目标开始，在自己的实际错误历史上完成任务；静态next-action准确率只作诊断。

| 数据与优化机制 | 预期可学习行为 | 必须提供的反证检验／当前缺口 |
|---|---|---|
| 原会话＋纠正→有证当前需求 | 正确选需求、保留边界与个性化要求 | 未见来源的引文／纠正保真；契约数量不代表路线筛选自主示范 |
| 原R设计／探索＋完整代码目标 | 把流程固化为可复用程序及接口 | 新输入实际运行正常／边界／反例；完整程序机制仍少 |
| 原失败＋完整旧版本→诊断与精确edit | 区分坏资源、坏测试、缺输入；修后复测 | 测试预期错误不能靠改业务规则“变绿”；同版本消费仍不足 |
| 同版本试用＋独立质量＋全成本→决定 | 在质量合格且实际减负时保留，否则修订或STOP | 正向合格保留链0；当前不能支持“会正确封装保留”的结论 |
| 连贯原生历史＋阶段衔接监督 | 从总目标自行调度完整pipeline | 单原生自主A—D示范0，学生闭环未测；外层拼阶段不能替代 |

保留推理、反馈和修订的方向有[AgentTuning](https://arxiv.org/abs/2310.12823)、[AgentRefine](https://arxiv.org/abs/2501.01702)、[SWE-smith](https://arxiv.org/abs/2504.21798)及[DeepSeek-R1](https://arxiv.org/abs/2501.12948)的相关证据支持；这些外域研究没有证明本数据已足量，也不能据其条数承诺WRD效果。既定2000非平凡主目标／100万主监督tokens／50干净来源群／12机制族仅为数据扩充里程碑；数量达到仍须有正向封装、自主链和独立泛化证据。

闭环主指标为交付TSR、独立五维Q、资源可复现、修订后同版本消费、正确STOP／保留及总成本。按来源component统计区间，不把93动作当93独立任务。训练loss下降但功能／需求保真不改善时，不追加曝光；连续两轮开发不改善则停止并保留较早合格检查点。错误引用、覆盖输入、编造观察或无依据冻结单列失败，不被平均分掩盖。

每合格技能总成本 =（数据整理与新标注＋训练＋开发选择／验证＋全部沉淀尝试＋工具／外部模型／重试／人工回退）÷ 合格且去重技能数。分别报告已付历史和新增成本，全部失败保留，现金、设备小时、能耗／电价和AI整理缺账均标UNKNOWN_NOT_ZERO。若实测单位合格技能可变成本差Δ>0，才用新增固定成本F/Δ讨论摊销；Δ≤0没有此结论。

已结束采集范围20 outer／21 native，共22156371已知tokens／286请求身份／3usage未知；339兼容HTTP原件及460514原R字符已保全。仅为本有界采集范围，不是全部项目费用，也不是339个正训练目标。CV评审仍含成本比值方向错误、过去日期误作未来及分数加总错误，原件audit-only，未改成合格金标。现合格保留0，每合格技能总成本未定义。没有训练吞吐、峰值或学生效果实测，因此不给训练小时或固定降本倍数。

