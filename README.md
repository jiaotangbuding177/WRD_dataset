# WRD58 v2 技能生成模型验证交接包

**同事从 [COLLEAGUE_TASK.md](COLLEAGUE_TASK.md) 开始。** 本分支已含实际制作源会话、提示和冻结清单，按文档生成 skills 后，用回传脚本把技能包与完整制作证据一次交回。

本轮小模型承担 WRD 的技能制作 Agent。输入完整历史会话、可用资源和沉淀目标，由模型在原生 OpenClaw 中分析路线、筛选复用价值、构建工作流及资源、执行制作内的试跑、读取反馈并修订，输出技能包和制作证据。OpenClaw 提供原生工具和会话循环，Spark 提供模型推理。

2026-11-07 用户纠正后，本轮只验证技能生成。此前交接额外安排的固定 Actor、两道业务消费题和 10 个消费槽全部延期。制作过程内的资源测试和修订继续保留。

从本入口完成固定模型、原生工具和一个开发来源的同尺寸基座对照。8B、14B 的离线筛查已经完成，均保留 checkpoint-0 和 checkpoint-26。[训练终态](https://github.com/jiaotangbuding177/WRD_dataset/commit/978fb3b25fcc7d40b35246266d2fc8d02ddd1f36) · [离线筛查](https://github.com/jiaotangbuding177/WRD_dataset/commit/4af0c4f1190a595d5b243026aaa68e7026ab0f17)

| 位置 | 同事负责的工作 |
|---|---|
| Spark ARM64 | 用已有训练缓存和四份 adapter 启动 vLLM。按 8B、14B 串行切换。各自验收工具 SSE、用量和长上下文。 |
| 可连接 Spark 的 x86_64 主机 | 恢复同一 OpenClaw 镜像。让小模型通过原生 Agent 操作环境，完成技能制作、资源自测和修订。运行脚本负责投递、预算和证据。 |
| 制作材料 | `materials/` 内已提供全部本轮制作文本输入；固定镜像在已有工具主机复用，缺镜像按恢复文档从持有者导出。清单见 [TRANSFER_MANIFEST.json](TRANSFER_MANIFEST.json)。 |

1. 先读 [OPENCLAW_RESTORE.md](OPENCLAW_RESTORE.md)，恢复镜像，核对 `linux/amd64`、镜像 ID、CLI 版本，并建立同事主机与 Spark 的私有连通。
2. 按 [VALIDATION.md](VALIDATION.md) 完成必要的接口验机，然后执行一组四臂技能制作并检查制作证据。已有且满足同一冻结配置的验机回执直接复用。
3. 复制 [RETURN_TEMPLATE.json](RETURN_TEMPLATE.json) 填写实测回执，回传技能包、真实工具轨迹、资源自测、修订链和完整制作成本。

本轮要回答的是：同一份会话和资源交给训练后的模型，它能否自主沉淀出更可靠的技能包，以及相对同尺寸基座的制作质量和制作成本如何。所有业务消费命令已在执行入口暂停。

`spark/` 有服务、协议探针和手动文件 worker。`local/` 有便携原生入口和冻结的运行适配文件。`eval/` 有此前的权重及短探针验收入口，供交接核验。原训练日志和权重仍用 Spark 上验收过的 v2 文件。只有 Spark ARM64 而缺少可连接的 x86_64 工具主机时，可先完成 Spark 接口验机。完整的原生开发对照需要该工具主机。
