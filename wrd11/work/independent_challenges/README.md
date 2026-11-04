# WRD11独立手工挑战题：仅QA，不作训练

24道新构造题，六个机制各4题：父调度、版本因果、匹配消费对照、Q／费用可观测性、支配／回本、成本分摊与去重。作者没有读取`controller_cases11.py`或root oracle实现。题目为有限规则下的自述假设，不是原生日志、教师轨迹、真实企业材料或生产门槛校准。

仅将`policy_registry[policy_id]`与`visible_state`提交给待测组件。`expected_decision`、`critical_reason`、`required_semantics`、`counterfactual`和`invariance`全部是QA审计答案，不能渲染进当前输入或加进SFT。不存在训练labels、loss数组、tokenizer、权重或模型执行。新理由是本次作者给出的可审计说明，不是恢复的原私有CoT。

## 真正检验的边界

| 题号 | 机制与边界 |
|---|---|
| P01—P04 | 客户端timeout而现有child仍运行；DONE缺产物回执；预算恰好0；预算恰好等于一次派发成本。 |
| V05—V08 | V0成绩不转授V1；制作声明和产物身份冲突；局部修复后缺同版本消费复试；同版本证据可推进但不能自动KEEP。 |
| M09—M12 | 两ID同内容不是两独立输入；同case输入不同；环境不同；数组反序仍应按case键匹配。 |
| Q13—Q16 | 每维Q恰好等于80允许；缺一维不能填0；已知零费用不是未知；exit0和高Q不补交付缺陷。 |
| E17—E20 | 净收益恰好0和+6；质量更低且更贵的支配；零成本相同但质量提升的显式Pareto规则。 |
| A21—A24 | K=0单位成本未定义；重复终版不增加K；共享训练只计一次；缺训练费不是0。 |

金额均为抽象`abstract_credit`，不存在汇率、实际账单或费用估测。计算可用`Decimal(str(value))`以免边界由浮点误差改变。题内的版本／digest是显式构造身份，未声称磁盘有这些真实文件或其字节SHA已被验证。

M09的`case_records`是统一输入定义的结构：每个record的`original_input_digest`同时绑定该record内NS和skill两份receipt。M10—M12则每份receipt分别提供输入身份，必须逐个比对。不能将M09的record级绑定约定泛化成“所有缺输入字段的真实receipt都默认匹配”。

## 独立对照的方式

先核政策是否相同，再核动作语义与数值。不能只因root输出枚举名不同就判错，也不能只因输出包含“HOLD”就判对。`required_semantics`指出最少需要核对的事实，例如复用哪个child、是否重复派发、有效配对数、K、净收益以及未知字段是否被补成0。

每题提供一个反事实和一个不变扰动。JSON pointer均以`visible_state`为根；施加反事实后另行运行并检查相应审计答案。P02、Q16的两字段变更分别是同一“回执送达／缺陷修复”事实的联合更新，不是两次独立干预；不能只改真假标志而保留互相矛盾的诊断。E19只改变Q解除支配，费用仍更高，因此原因会变但STOP不应翻成KEEP。A22／A23改变的是正确数值，不一定改变报告状态，不能要求所有反事实都翻动作。

不变扰动属于另一次QA输入；应当保持动作语义或指定数值。重命名引用需全体一致，不能只改定义不改指向后再声称是不变扰动。

## 不兼容时必须明确报告

- E20采用显式Pareto目标，E17—E19采用固定复用数下的严格净收益目标。若root oracle只有现金净收益目标，E20应报告`NOT_COMPARABLE_POLICY`，不能改答案迎合实现，也不能把它算已通过。
- A21—A24是成本报告问题，预期含数值／UNKNOWN／UNDEFINED，不是父Actor的KEEP／HOLD／STOP终态。若root oracle不返回这些量，应报告`NOT_SUPPORTED_ACCOUNTING_OUTPUT`，不能把REPORT强映成Actor动作。
- 若某实现不表示现有child、版本digest、逐case环境或共享物理cost_event_id，则对应题只能报告`NOT_SUPPORTED_STATE`。独立挑战的目的包括暴露状态表示缺口，而不是把全部题投影到一个实现容易通过的schema。
- 构造KEEP只表示本题规则给定事实下的政策答案，真实原生自主示范、业务消费者Q和合格KEEP数均不增加。

本目录只提交挑战定义和审计答案。本作者未执行root oracle，也未作任何Agent循环、工具派发、网络访问、tokenize或训练；实际通过率须由后续独立运行回执给出，不能由JSON可解析反推。
