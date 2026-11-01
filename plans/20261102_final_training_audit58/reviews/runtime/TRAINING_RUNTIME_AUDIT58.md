# 58最终训练与原生接口审计

当前可训练主集的主要优势是已有底座能力上的WRD流程适配：来源契约与B资源制作有真实目标和原文/版本证据，当前原生链同时提供原思考、实际调用和两次反馈修复。保留BF16 LoRA r32、lr5e-5、单pass241上限；本审计没有依据把静态数据量换算为某个最终TSR百分比。

## 1. 实修：把新完整链的可验证原生协议也纳监督

冻结57全1260实际token级审计找到293个工具调用格式实例：旧真实118、辅助122、57增量53。253个工具名已有正监督；旧真实110、辅助122、早先21增量21。新bfc32个调用的名字、参数键、工具壳、thinking控制与结束符原先均为0loss。401契约的2406个F只覆盖thinking/结束控制，不能当新工具链的直接协议训练。

新58只对31个schema合法且有原native ACK的调用加F650/.25。原R2916/A19376/D19和原全部输入/响应保持；API5的错误edit调用缺edits且多input，原始native确实validation error，旧bank仅R150、错误A0，新版完整mask保持。末33含未获整技能效用授信的最终说明，也不补格式结束符。这是覆盖增强，未把错误参数或未证KEEP变为正例。

精确政策只选当前assistant内的thinking开闭、真实tool_call壳/名称、顶层已声明参数键与分隔符、实际assistant结束；不选随机call ID、角色header、参数值、嵌套值或字符串payload内部符号。每新增token必须全部offset落在批准字符区域，边界混合继续0loss。独立第二脚本排除全部原R、可见正文和所有参数值范围，并重新读99个实际binary的四features；两模型分别tokenize全部33，IDs/offsets实际相等。补正不增加独立经验，也不改已冻结57。

对应产物：`bfc_protocol_bank58/BANK_ENTRYPOINT58.json`、`INDEPENDENT_PROTOCOL_BANK_QA58.json`、`PROTOCOL_COVERAGE58.json`、`ALL32_NATIVE_CALL_SCHEMA_AND_ACK58.json`。

## 2. 原生I/O合同

`compile_collected57.py:324-375`和实际rendered目标证明，新33使用Qwen的`<think>`和标准`<tool_call>{name,arguments}</tool_call>`表达，没有额外canonical动作协议。`compile_native.py:75-95`改的是历史R保留及空白，接口不需要替代Agent循环。

需要明确锁定的是服务设置：

- 只固定已经审计的chat template及合法Qwen reasoning/tool-call response parser；原native incoming messages与完整tools逐字段传入，不按gold/目标过滤，不逐步构造past-state，不注入摘要，也不把外部轨迹补作历史R。
- 推理`add_generation_prompt=true`时使用`enable_thinking=true`。训练记录的`add_generation_prompt=false`使当时的`enable_thinking=false`不删除原R；但推理误沿false会预填空`<think></think>`，跳过要学习的R生成。CPU前缀回放已单独验证，不是模型推理。
- 正确解析`reasoning_content`与`tool_calls`，在`im_end`结束响应，不在`</think>`提前截断。原生OpenClaw负责工具执行及会话续跑。
- 新33离线工具族目录18个，实际原native每请求53个；离线past-state还含重新情境化的过去原R。推理保持原生可见历史，不能为消除差异而在服务重写每步输入。该分布迁移由原生未见dev闭环来测。

`SPARK_DEPLOYMENT_CONTRACT57.md`中ARM Spark训练/模型HTTP服务、固定amd64宿主工具循环的分工正确。32K共同训练与128K候选服务分层也正确；扩窗必须明确YaRN，不能只抬max_model_len。该服务与GB10内存/吞吐本轮未实跑。

## 3. 优化器与课程

现有置信权重、loss numerator/非ignore count denominator定义明确，累积批应先确定整步分母，再对每个microbatch的weighted CE分子按同一分母反传；不能让普通Trainer再除一次accumulation，也不能改成按权重和归一化。该项应作为未来trainer的CPU数学fixture，读取有效mask后实现，不能用JSON配置存在冒充已做更新。

r32/alpha64覆盖七投影适合对照；由精确小config计算，14B的LoRA理论参数为128450560，8B为87293952。因此相同r与训练曝光属于相同训练合同，并不等于两者训练参数量或设备时间相同。实际成本独立计量，不预报GB10速度。

3步warmup和lr5e-5没有在静态审计中出现确定错误，保持主设置，避免未测就凭经验改多个变量。质量选择增加base0、26、80、134、188、241检查点；241仍是单pass上限。先在独立dev对比较同一任务闭环成功、必需验收、Q和成本，再冻结一个checkpoint给test。

逐批辅助有效mass cap20%的新58课程可约束量化定义内的辅助占比；仍不等于Adam梯度或参数更新的20%保证。把实际step scale写课程并报告，保持主数据权重原件不回写。

## 4. 质量与公平比较

增加同一原生环境中的未SFT 14B和未SFT 8B，分别报告adapter相对自身底座的增量；直接14B-adapter vs 8B-adapter同时含底座规模能力。保留contract-only26与全过程检查点，用来源级dev测流程迁移；旧1227匹配241/同混排回放控制与等设备小时控制解决的是不同归因问题。

按现有真实监督密度，最有依据的首轮质量预期是结构化来源理解、资源代码/模板构建和局部反馈修复增强。C评估与D取舍有明确政策课程及少量真例，新原生整链验证能测是否串成闭环；来源隔离的完整任务质量与成本使用实际模型结果估计。当前没有学生未见任务结果，不能从一条教师链或静态mask给统计成功率。建议报告模块方向/预期强度与评价终点，结果出后按独立来源给区间，而非把窗口数当独立样本。

本轮所有计算仅tokenizer、JSON/schema、mask、binary与模板回放；无模型权重、forward/backward、新provider或业务执行。科研开发skills保持禁用。
