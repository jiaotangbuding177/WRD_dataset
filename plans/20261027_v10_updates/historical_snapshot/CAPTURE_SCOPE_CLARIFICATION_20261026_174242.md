# 捕获边界与计量口径澄清

本目录已完整保存本次OpenClaw模型客户端发向既有OpenAI兼容bridge的HTTP原字节：system、messages、53项工具目录、工具反馈，以及bridge返回的JSON/SSE、可读reasoning_content和委托工具调用。纯透传relay没有改请求/响应体。原生主/子会话已持久化的event_json另由结束后只读导出保全。遇到硬故障前未持久化的尾部，仍只能标未知。

bridge之后还有原生SDK/CLI backend。现存 `openai-handler.js` 的 `hasTools/_needsTools` 路径选择带内置工具的全量backend，源码注释提及约22.7k与3.2k的backend前缀差异，并说明委托工具注册依赖全量backend。这是代码支持的接入条件；当前没有取得每次底层provider最终完整system/prompt/tools的原字节，不能把该未知部分写成已恢复。不同tokenizer计数的差值也不能当作精确前缀大小。

完整兼容API请求与底层provider最终请求应分别命名。现有原字段可继续作为明确蒸馏接口的证据：A实际捕获的 `choices[].delta.reasoning_content` 共34473字符、49697 UTF-8字节，原R没有因本澄清被删除、替换或编造。R是否可监督仍按独立片段审核，不能由write成功自动批准整段R。

A有9个兼容HTTP交换、7个具有唯一native meter身份的底层模型调用。0002/0003是既有pending工具流的只读续接，耗时0秒/16毫秒，期间没有新的native_start。`_continuePending`将对应tool result交回同一ACP client/state并继续消费iterator；`_suspendForToolCall`每遇一个delegate工具会结束一个新的兼容SSE。因而9个API response不能计成9次独立付费推理。7次完整usage为输入537698、输出33234、合计570932 tokens，货币未知。逐项映射见 `quality/A_NATIVE_API_PROVIDER_MAPPING.json`。

student core7是声明的工具目录投影视图。其原件来源、被删目录项与保留的可见历史必须记录，`is_original_native_request_identical=false`；不能声称与53工具原API或SDK最终provider输入完全相同。teacher兼容API原件、底层计量身份、学生转写三者分别保留。

实际11项源码/字节pins保存在 [CAPTURE_SCOPE_CLARIFICATION.json](./CAPTURE_SCOPE_CLARIFICATION.json)：未改的native adapter与audit relay，既有bridge的openai-handler/stream-driver/sink-factory/acp-client/prompt-builder/agent-guide/gateway-discovery，以及新录制runtime的container_runner/openclaw_config。该文件不复制企业正文、密钥或认证头。

本澄清只修正证据范围，不产生新的模型或效果结果。唯一B准入waiter已在校验PID/birth/cmd、无dispatch/子进程、独占lane锁且0个B API回执后停止；bridge、0—9和原driver没有停止。B授权保留，待主管双稿5.0.38同步、刷新prepare后再恢复同一job等待；原7 GiB/<8容器门未改。
