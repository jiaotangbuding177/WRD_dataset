# WRD58完整241回包实审

原件：`C:/Users/22142/Downloads/wrd58-final241-return.zip`，7543830字节，SHA256 `625d90ebf4000e8096f51fac939a85cb3d0b203e56ac86bfbbbf817c0fac1390`。1263成员、1262清单成员SHA全过，无重复/越界/符号链接。

## 已证事实

两个241实际制作包均为0；各workspace仅有inputs/source.json，没有真实写文件或exec。两臂各6次上游HTTP COMPLETE、无上游链路错误；这不等于原生业务成功。

| 臂 | 实际工具 | input / output / reasoning tokens | IO | 容器秒 |
|---|---|---|---:|---:|
| 8B-241 | 6 read；首响应并行2 read，5次读source、1次读不存在README | 294056 / 3594 / 3409 | 297650 | 552.36 |
| 14B-241 | 2 read + 1 ls | 192863 / 3630 / 3509 | 196493 | 723.48 |

两臂均在一次回复2048输出中用2047 reasoning并触length。8B随后原生终答恢复遭本地429预算拒绝；14B有工具的主循环仅前4请求，后2为原生text-only终答恢复。其请求明确禁工具、没有system/tools：第5虚构制作记录位于reasoning、可见content为空；第6将read的tool_call输出为普通文字。实际用户可见终态是OpenClaw未产出最终摘要的fallback。不能将其归为“正常53工具请求的解析器吞了tool_call”，也不把hidden reasoning虚构说成已展示给用户的成功终答。虚构内容和未交付本身保留为负结果。

## 对用户三点结论的校正

1. 对照是2尺寸×3检查点×2长度，共12条，不是3尺寸。14B24K三臂stop但均答错；其余9条length。128输出窗口未见检查点特异的停止差异，但不能据此证明26普遍正常或241没有退化。
2. 66K三臂共同length限于这128输出窗口；未查明共同条件的具体因果，不直接称已定位到长输入故障。原生制作初始约31K，后续38K—63K；32K训练与当前部署存在长度条件差异。
3. 两个241在此次单来源mini均未生成skill，是实际业务失败。没有同条件基座mini制作，所以训练净效应尚未测到。

## 执行合同与证据

本包仍用旧mini提示，没有落实前次拟议的普通Git仓库源码作者任务/所有权配置。完整native system仍将durable skills导向Workshop并允许普通仓库源码例外。导出没.git不证明未导出状态不存在，但不能声称新profile已实现。串行避免了本次端口冲突，不是独占修复源码的证据。

8B实际启动命令显式补 `VLLM_ALLOW_LONG_MAX_MODEL_LEN=1`，原serve脚本与实际命令差异需固定；14B未用no-autotune仍成功是本轮观察，不删除前轮PTX失败或升级为普遍不会复发。两个241 SHA与原v2清单一致。

关键ZIP路径：

- `local/diagnostic_evidence/final241/compare_{8b,14b}/summary.json`
- `local/diagnostic_evidence/final241/serve_8b_launch_command.txt`
- `local/dev_pilot/producers_mini/wrd58-<size>-241/model_http/*/{request.raw.json,response.raw.sse,receipt.json}`
- 两臂 `openclaw_transport/gateway.stderr.log`、`container_receipt.json` 和实际workspace。

机器审计：`output/20261108_wrd58_final241_return_audit/INDEPENDENT_DATA_AUDIT.json`及`PROTOCOL_REQUEST_ROLES.json`。未把原企业正文/思考全文复制到本研究记录。

## 后续决定

停止容量填充、26筛查与玩具烟测。以一项真实制作四臂配对实验直接测0→241的训练收益、实际质量和单位合格制作成本。完整方案在 [真实制作效果实验](../plans/2026-11-08_wrd58_real_production_effect_experiment.md)。12来源是待准备的冻结目标、48制作是计划规模；原生新profile和累计预算尚未实现，不能声称已经可直接运行。

本轮仅离线审计、方案与记忆；未修改训练数据/loss/课程/权重，未运行模型、Docker、训练或新业务。原226、DEV/TEST隔离保持，独立业务消费延期。
