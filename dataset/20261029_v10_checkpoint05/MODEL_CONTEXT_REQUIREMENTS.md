# 14B／8B共同上下文与设备边界

默认529条全部≤32768，449≤16384，80长桶；均为声明过的学生视图，两tokenizer逐行一致。core7不是原生完整53目录，不能改实际工具权限来伪造一致。

完整53工具条件视图与core共享owner，替换不相加；helpers的full53虽31842可容32K训练，但加32768输出需62712服务窗；style与oracle full53需64K训练和128K总服务候选。它们未默认ACTIVE，Spark未验机。

pinned config40960/rope=null。候选64K YaRN factor2、128K factor4必须统一训练与服务并实测。已研究111原请求的full53训练32K/64K/128K覆盖6/89/111，严格预留输出64K只11/111，不扩大分母到339。

Spark ARM64／GB10／统一内存121GiB：未来先验attention/backward、causal shift和head梯度、实际峰值及吞吐，再决定长桶。selected-head须与dense损失／梯度等价；不能删mask0上下文或detach hidden。本轮没有模型权重、前向、反向或训练。
