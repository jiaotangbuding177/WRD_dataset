# scheduled 首批真实过程整理结果

2026-10-29，固定范围 ep_04149c237fc7afb2bd67 的 56 个候选位置均已逐目标处理；新增可训练目标 0，新增正监督 tokens 0。它们不是因日志体积、32K 窗口或程序太长被筛掉，而是本轮闭合了实际保护祖先。

`ANCESTRY_PROOF.json` 给出完整证据链：较早的 route_batch_007 原生会话实际读取 20 来源的 compact_proposals（文件 CRLF 与实际返回 LF 的差异已精确核对），实际可见来源含 3 个当前 protected/shared/static 来源；它实际 write 生成的 scheduled 原 card，经仅复制两条既有来源引用的机械规范化，进入后来的制作输入。制作第 3 条消息 read task.json 后，第 4 条工具返回已经实际提供与原 card 完全相同的 value_plan。固定候选从消息 5 开始，全部位于这次实际保护暴露之后。四个最终业务来源标成 TRAIN 不能消除生产者曾看到的其他来源。

该 route_batch_007 原 session_events.jsonl 为 63463 字节、12 条消息、6 条助手响应；按路径及 SHA 检查均不在此前 v9 episodes.metadata。已恢复并保全这个真实遗漏入口，但不将它算成新增干净训练会话。

`TARGETS.with_body.audit.jsonl.gz` 不是候选地址表：包含每个目标完整实际过去、原目标全文、原事件位置及下一条真实工具反馈。未来反馈单独放 audit 字段，不进入过去输入；56 条全部 `positive_loss=0`、`training_admitted=false`。`ACTUAL_CALL_OBSERVATION_VERSION_EDGES.json` 保存 15 次原 write 及实际 call/ack/内容 SHA 的对应关系。完整原会话、两个程序、SKILL、fixtures、原导出 system/tools/事件、独立复现报告均有实际同 SHA 的携带副本。

独立复现的 HOLD 原因也已具体恢复：公开用法指向未实际提供的 `{INPUT}/task_spec.json`，所以该正常用例的实际 argv 和退出码均为空；另外 update/boundary/invalid 三个实际执行用例通过。该报告没有 list_artifacts 的独立 case，不能把 maker 自报的七例通过升级为整包独立合格。静态审读另发现 base 字段全保留的文字承诺比实现范围更广等问题，只标审读问题，没有伪造新的测试结果，也没有执行被保护程序。

原 native、两份 aggregate response 和原导出 evidence 没有发现显式原 thinking/reasoning 文本块；原计量仍保全，reasoning_tokens 数值不冒充原思考正文。这是已检查载体的结果，不声称任何其他 provider 记录不存在。所有原动作、文字、反馈和失败仍在，不生成伪原 CoT。

这些文件属于受保护的审计材料，不能送入训练、开发选阈值或新 Teacher 提示。`PRESERVED_OBJECTS.json` 给出明确原件及实际对象，`RESULT.json` 给出本批结果；检查点 06 的 530 个训练目标和主 manifest 没有修改。未启动 Teacher、Actor、历史程序或训练。AI/CPU 整理成本未计量，记为 UNKNOWN_NOT_ZERO。
