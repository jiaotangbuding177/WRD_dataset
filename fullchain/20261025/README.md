# 全阶段候选恢复与全流程蒸馏计划

此前93条只属于旧技术诊断子集，完整主训练数据尚在审核建设。

[详细训练计划](../../plans/20261025_fullchain_distillation/README.md) · [数据计数](DATA_LEDGER.json)

本次提供既有已清理1051会话的完整原生记录、17513助手候选及真实末条定位；包含企业语义正文，来源与原公开清理投影一致。所有新增候选均未由本次导出判为训练正例。完整受控范围1763会话、32342助手位置；19728为沉淀角色非空候选，不是合格独立任务数。

候选用session_ref及session_line_1based定位本目录candidates中的完整会话，prompt_messages_range_exclusive是历史前缀范围，completion_native是该位置真实输出。目标/整场成败/公开状态各自保留，不能整包直接送入SFT。

CONTROLLED_RECOVERY_INVENTORY只公开受控文件SHA/大小/相对位置，不含新增受控正文。派生标签15104行、151修订配对的正文仍在本地处理，不假称已经全部公开。tooling是离线只读盘点/组装脚本，不是原生业务Agent执行器或训练启动器。
