# C独立评审与真实状态STOP数据：第二版，等待root准入

推荐当前数据为 `semantic_revision_02/` 和 `../compiled/c_review_dataset_02/`。实际编译 **4序列、76,289输入tokens、1,458监督tokens**，每条不超过32K。两套本地tokenizer分别直接重编全部4条，独立QA通过；未加载权重、未训练、未新发原生会话。所有记录保留 `root_main_admission=false`。

| 当前银行 | 序列 | 输入tokens | 监督tokens | 局部信用 |
|---|---:|---:|---:|---|
| native_C_review_partial_02 | 1 | 15,277 | 387 | 实际C评审早期原R的获证字符范围 |
| native_C_execution_local_02 | 2 | 53,017 | 781 | 两个实际保真成稿write，只有A工具动作正loss |
| new_real_state_cost_stop_02 | 1 | 7,995 | 290 | 新作者R132＋普通assistant决策D158 |

统一局部银标系数0.25，等效监督364.5tokens；不把它当human gold。原生原R387与新AI摘要R132分别报告。三个银行共享四个干净train来源的一个parent group；L写作动作的实际祖先仍为三源子集，不虚增未读取的E源。一个候选机制、两例开发消费、四源祖先，不是四个独立完整WRD任务。

完整C评审24个兼容HTTP响应及30,514字符原R已保全；兼容响应不等于独立付费调用。通读后只提出22个局部范围，第二次独立语义审核撤回207字符过宽的“限定词均保留”概括，剩2981字符。原材料被E_A改写得更绝对，因而不能用全称保真结论授信。实际可编32K原R只有上述387tokens，其余获证候选保全待处理，未删past迁就长度。

另外1个原R候选因当时真实write缺少path字段，被现compiler按原schema暂缓；3个后期原R完整窗口为53,107／64,009／66,170tokens，全部暂缓。原错误动作和过去输入没有删改。7个full53候选另存，尚未编译或准入；与相应core7 owner互斥。core7是明确工具目录投影，保留完整system及全部past，不冒称同一原生输入。新state采用普通assistant文本，不伪造原工具动作。

两个真实执行write由另一AI逐段比对原source、实际字段、实际交付和成功反馈。E成稿保留五个理由和原资格限定，L成稿全文486字符、保留两角度和原数值限定；只授这两个写入动作的局部信用。其他中间pack、全R、整episode、资源整体收益未获批准；没有用read／ls凑主监督。

新作者状态明确发生在原终评结束之后，完整保留两例原用户content与四个实际交付；输入保留原盲Q四个label的全部对象及长度观察，明确探索性未人工校准身份，新增独审遗漏说明但不改原Q数值。来源、SHA、捕获路径和准入flags在metadata，不塞入功能状态。新理由与普通assistant结构决策是新的AI银标摘要，不能称原D思考、同条件重放、已执行tool call或成功封存。

该新状态给出实际读用和同版本证明、局部测试边界、质量观察、真实费用及未知。NoSkill合计377,870tokens／7次，Skill合计2,021,350／30次，约5.35倍Token、4.29倍调用。保留须有实际减负，当前两例未观察到，因此STOP有有界合理性；不证明全局最优、所有写作或全部WRD均无价值。资源的局部正确信用继续保留。

7367237是评审前subtotal，原当次终评结束后才新增1293310，终态共8660547已知tokens、110个实际request身份、1次usage未知。新状态显式提供终态信息，绝不倒填进原D当时的past。现金、AI整理／代码工作和能耗未知，不按0；零合格分母的每合格技能总成本未定义。

原盲Q成功write的实际反馈为seq39，之后才读臂身份与成本，且未重写Q。独审只证明实际盲序及计分算术，不证明语义评分gold。原D包含当前评审费用的错误措辞、噪声幅度断言、正文边界与空白计数混淆、把诚实语义范围当代码bug等原件及精确mask0范围都保留。

首编 `compiled/c_review_dataset_01` 的1496监督tokens是已被纠正的历史草稿；与当前版不得叠加。原R输入数组逐token完全相同，只撤下38个过宽范围tokens；两写入动作输入不变；新state明确更新原Q对象与已知独审纠正。所有这些文件仍未进入ACTIVE。

主要入口：

- `semantic_revision_02/COMPILED_COVERAGE.json`、`INDEPENDENT_DUAL_TOKENIZER_QA.json`：实际数组、暂缓原因及验证。
- `semantic_revision_02/actual_unshifted_token_labels_masks.npz`、`DENSE_ARRAY_RECEIPT.json`：实际input_ids、未shift labels、loss_mask及loss_weights；非监督位置labels=-100、weights=0。
- `semantic_revision_02/ORIGINAL_R_LOCAL_REVIEW.json`、`EXPLICIT_ZERO_ERROR_RANGES.json`：原R完整分区、精确获证／已知错误范围及SHA。
- `semantic_revision_02/NEW_AUTHORED_REAL_STATE_COST_STOP.input.json`／`.output.json`：可读的新当前状态与新作者答案。
- `semantic_revision_02/SOURCE_AND_ORIGINAL_ARTIFACT_RECEIPTS.json`：train4闭合来源、原件SHA及冻结设计5.0.39／数据准备5.0.40身份。
- `independent_process_review/REVIEW.md`、`review_followup_01/REVIEW.md`：独立内容与语义复核。

根目录、当前设计、计划、记忆、ACTIVE和固定原生环境均未修改。中央记忆、设计同步与最终Git交付由root在独立准入后统一处理。本轮新增实证限于上述离线内容、数组、边界与错误核对，没有新增效果实验结论。
