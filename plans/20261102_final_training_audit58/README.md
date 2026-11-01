# WRD最终训练审计58

本版提供1260目标/295478正监督tokens、241更新上限的明确课程，主14B、对照8B。主集由401来源契约、232真实过程、627显式辅助组成，原226及保留来源继续隔离。

- [完整训练计划](PLAN.md)
- [训练结果能力预估与机制依据](QUALITY_FORECAST58.md)
- [实际训练入口](TRAINING_ENTRYPOINT58.json)、[配置](CONFIG58.json)、[逐batch课程](COURSE58.json)
- [完整数据恢复及CPU复验](RESTORE_AND_VALIDATE.md)
- [可执行目标适配器](tooling/README_OBJECTIVE_ADAPTER58.md)
- [独立原始论文核查](research/PRIMARY_RESEARCH_AND_QUALITY_FORECAST58.md)
- [受保护之外开发诊断](DEVELOPMENT_DIAGNOSTICS58.json)：用于排错和dev选模，不当独立test结果。

`reviews/baseline57/`是本轮修改之前的57数据审计，数值294828正tokens等保留历史范围；新58只补31个合法ACK调用的650个协议F tokens，原语义/input IDs不变。`reviews/runtime/`和新58四features/课程回执记录修正结果。辅助比例须区分原bin、课程静态mass和按步归一化系数，不把这些量当梯度或模型质量。

模型质量预估是对改善方向的研究判断。原生完整质量和每个合格skill总成本由训练后的保留来源闭环校准，本轮无模型加载、推理或训练。研究文件先冻结，实物/还原/远端证明作为独立后置交付metadata保存，避免AES自引用。

`designs/latest/`是原项目双稿的逐字绑定副本，历史段落保留了原科研工作树的相对链接；这些历史链接不作为当前Git训练入口。当前使用本页、PLAN和恢复说明的导航，原项目历史可由对应旧认证材料追溯。
