# C_review局部R与新真实状态的独立复核

复核者为独立AI助手，属于未人工校准的silver，非human gold。本次未调用模型、未训练、未改原生环境、builder或shared compiler。`root_main_admission=false`继续保留。

首版22个原R范围的原文切片与SHA、各自原request SHA及列明证据在当时prefix内可见，全部机械通过；11份非空R的完整无交叠mask分区通过。语义复核要求撤下两处过宽的“限定词均保留”正loss，保留其中独立成立的前半句。具体范围均为原R字符位置，0起、右开：

| 原范围ID | 首版范围 | 可保留范围 | 必须mask0范围 | 原因 |
|---|---|---|---|---|
| C_R_0009_02 | [2416,2635) | [2416,2499) | [2499,2635) | 允许精简、五标题非硬要求成立；但随后“all qualifiers…those are preserved”过宽 |
| C_R_0009_08 | [5782,5889) | [5782,5818) | [5818,5889) | 五个理由均覆盖成立；“Qualifiers…both preserve”过宽 |

E_A把学生“难以持续承担”写成“无法承担”，把贵州工作转向过程写成“工作已从…转向”，且结尾“最合适的人选”超出源材料。这些使限定词全部保留的概括不可靠；不能靠范围外metadata把原句改成较窄的真命题。两处共撤207字符。另20个原R局部范围在原prefix及有限字面/协议范围内可成立；没有据原STOP或完成状态整段批准。

`semantic_revision_02/ORIGINAL_R_LOCAL_REVIEW.json`已逐字核对两处收窄，正范围仍22段、合计2981字符。02保留段SHA为`7511467d8410629f137af07ff4f936f1183b7ebf7b174bb6da1506ea8038d3c6`；08保留段SHA为`e16cb835d018027c1fba828093bed4759ccc461d6dbdb59df4975665cd847ac3`。首版原件和首次编译应保留为历史，不与修订版叠加曝光。

新作者状态可用于监督当前有界STOP。两条L用户消息及一条E用户消息的原content逐字符保留；四份实际交付与四C真实deliverable逐字符完全相等，未删正文或尾换行。输入同时给出原AI盲Q的未人工校准身份、原盲Q先写成功再读身份/费用的实际顺序，并明确两例无法测定统计噪声幅度。v2四个label的完整原AI质量对象（含primary_deduction_note）均原样保留；新增独立语义纠正说明不修改原Q数值，不把原AI错误条目升级为gold。

状态明确是终评结束后的新状态，允许显式加入当时新可知的终评usage。NoSkill合计377870tokens/7calls，Skill合计2021350/30，分别约5.34933倍Token、4.28571倍调用；7367237是评审前subtotal，当前评审1293310，终评后8660547已知tokens、110个真实请求身份、1次usage未知，账目范围清楚。现金、AI整理费用和能耗未知，零合格分母的单位合格技能成本未定义。

输出是新作者简洁理由及普通assistant结构决策，未伪造原D实际tool call、成功封存或全局最优。STOP限于该版本与两例开发消费；局部程序修复和保真成稿的信用与整体不保留并存。两例的Token和调用增加提供当前停止的合理依据，不外推全部写作、全部WRD或其他输入规模。

首版机械审计见`MECHANICAL_AUDIT.json`：37个源/产物receipt的size/SHA、6对原件副本、全部prefix证据、完整源内容、四交付、成本算术及4条编译记录的数组哈希/长度/正loss范围均通过。4seq为76133输入tokens、1496监督tokens（原R425，真实write781，新状态290）；每条≤32K，weight0.25，root准入false。原R另1条因真实动作schema缺path而hold、3条因完整past>32K而hold；没有通过删past转正。所有4条编译记录均记录独立第二tokenizer调用相等；本独审核其回执和数组哈希，未执行第三轮tokenizer。

祖先分组保留同一parent group。L局部写动作的实际source_ids为3源子集，不虚增未读取的E源；其parent union及整个银行为4源，未跨split。首版功能输入的AI质量对象曾省略两条重复primary_deduction_note，v2已补齐，遗漏不影响原分值。复核中曾误把四交付概括为有末尾换行差异，随后查明四份均exact equality并立即更正；该错误不属于数据缺陷。

本报告的语义建议是采用v2收窄后的范围和新状态；最终主准入仍由root独审。v1与v2只可择一，不叠加；本报告不把首版的1496监督数冒称v2最终编译数。

v2最终数组复核见`V2_FINAL_AUDIT.json`，结果`PASS_SCOPED_PENDING_ROOT`：4seq/76289输入/1458监督（原R387＋新R132、A781、D158）。16个dense向量的dtype、长度、SHA、未移位labels、非owner的-100/mask0/weight0，均逐项从实际supervision spans独立重建相等。原R的v1→v2 input_ids/messages/tools完全相同，只撤下38个正loss tokens、无新增位置；撤下207字符范围已明确mask0且与v2正R无交集。4对独立双tokenizer QA回执绑定同版编译报告，本次未再次tokenize。
