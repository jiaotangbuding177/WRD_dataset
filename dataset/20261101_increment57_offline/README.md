# 57认证离线增量

本目录单AES LFS实体包含57 active数据入口、最终已mask新银行、真实binary、完整来源/原R/工具/版本/反馈审计及冻结设计。旧05—11仍为依赖；原生在途任务不在该离线实体中。

[完整取得和CPU复验](../../plans/20261101_increment57/RESTORE_AND_VALIDATE.md) · [实际训练量与因果解释](../../plans/20261101_increment57/ACTUAL_DATA_REPORT.md) · [完整计划](../../plans/20261101_increment57/PLAN.md)

请使用`tooling/restore_increment57.py`严格入口，不直接调用impl文件；已有本地密钥不在Git。实体104626003B，SHA `01b8b5ec9e1ca7ce0b131a7da556e19d0115ca645f51b212c864d585dd1cde1b`。真实恢复3100文件/3101成员/311516086源字节，逐SHA与恢复后两profile四features均通过。

恢复根中的`work57/active_dataset57/final1227/TRAINING_ENTRYPOINT57.json`为当前入口：1227唯一目标、272517正tokens，默认v2课程233候选更新。旧实体保留审计，训练只走active selector；不加载学生权重或启动训练。

Git及LFS远端交付状态以本轮最终回执为准，不以本地文件存在代替上传成功。
