# 405个当前允许 maker 前缀的真实字节普查

已检查全部405个被v9最终来源账准许的make/legacy_skill_make目标，并用v10当前source_scope确认其可见来源均为TRAIN。403个只是协议前缀，2个已见来源的前缀合计涉及5个来源。

本轮没有凭旧`exact_produced_file_write_proofs`为空推断没有代码：405个目标的canonical消息SHA全部匹配，再按其精确source_event_line读取原native CAS中允许的实际目标，405内容全部与旧canonical一致，原native实体也重新核SHA。没有解析后续保护消息，没有复制保护正文。

实际字节是57个空助手位置，以及348个工具调用：112 read、220 exec、16 ls；只有2个可见text块、共67字符。220个exec完整参数共37662字符，全部经过shell分词复核；子命令仅cat/head/echo/find/ls，只有stderr转stdout或/dev/null，没有Python、代码内写文件、替换/补丁、文件输出重定向或find变更动作。没有发现完整程序创建或修改。

这是**这405个早期前缀**的具体结果，不表示后来保护阶段没有程序，不表示1763条会话或29个skills没有可用代码，也不表示未审核数据不适用。当前没有新增质量准入、训练样本或训练执行。

产物：

- `REPORT.json`：完整选择边界、来源文件SHA、405实际定位和静态提取统计。
- `TARGET_SCAN_405.jsonl.gz`：逐目标来源、原event行与SHA、当前可见TRAIN来源及工具参数静态摘要。
- `allowed_targets/`：405个被允许的原目标，后续保护消息没有复制。
- `COMMAND_GRAMMAR_QA.json`：220完整exec参数的语法复核，不将工具调用成功等同语义正确。
- `ACTUAL_EXEC_COMMANDS_220.jsonl.gz`：原参数、SHA、来源和只读命令分解，可独立复核。
- `EXTRACTED_PROPOSED_WRITES.json`：实际为空；不是未跑提取器。
- `scan_allowed_targets.py`、`classify_command_grammar.py`：实际完整处理脚本。均未执行原命令、未加载模型、未调用新Agent。

本目录是05冻结范围之外的后续恢复账，不修改529主目标、原226/H/static隔离、三个已通过银行或任何冻结原件。其它来源和历史代码的恢复应继续按具体输入/资源/反馈祖先与质量证据推进，不能拿这一局部零值终止全库整理。
