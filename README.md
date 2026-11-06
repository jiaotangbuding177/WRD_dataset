# WRD58 v2 同事接手包

从本入口完成固定模型、原生工具和一个开发来源的同尺寸基座对照。8B、14B 的离线筛查已经完成，均保留 checkpoint-0 和 checkpoint-26。[训练终态](https://github.com/jiaotangbuding177/WRD_dataset/commit/978fb3b25fcc7d40b35246266d2fc8d02ddd1f36) · [离线筛查](https://github.com/jiaotangbuding177/WRD_dataset/commit/4af0c4f1190a595d5b243026aaa68e7026ab0f17)

| 位置 | 同事负责的工作 |
|---|---|
| Spark ARM64 | 用已有训练缓存和四份 adapter 启动 vLLM。按 8B、14B 串行切换。各自验收工具 SSE、用量和长上下文。 |
| 可连接 Spark 的 x86_64 主机 | 恢复同一 OpenClaw 镜像。用原生 Agent 执行工具、制作技能并试用。运行脚本负责投递、预算和证据。 |
| 私下交接 | 从持有者接收冻结镜像 TAR 和开发材料 ZIP。文件名、SHA、来源和验证状态见 [TRANSFER_MANIFEST.json](TRANSFER_MANIFEST.json)。 |

1. 先读 [OPENCLAW_RESTORE.md](OPENCLAW_RESTORE.md)，恢复镜像，核对 `linux/amd64`、镜像 ID、CLI 版本，并建立同事主机与 Spark 的私有连通。
2. 按 [VALIDATION.md](VALIDATION.md) 验收两组服务和四条原生技术会话，接着执行一组四臂制作及两道消费题。逐步门槛和回传文件集中在同一文档。
3. 复制 [RETURN_TEMPLATE.json](RETURN_TEMPLATE.json) 填写实测回执。原始请求、轨迹、业务产物和用量日志经受控路径回传。

`spark/` 有服务、协议探针和手动文件 worker。`local/` 有便携原生入口和冻结的运行适配文件。`eval/` 有此前的权重及短探针验收入口，供交接核验。原训练日志和权重仍用 Spark 上验收过的 v2 文件。只有 Spark ARM64 而缺少可连接的 x86_64 工具主机时，可先完成 Spark 接口验机。完整的原生开发对照需要该工具主机。
