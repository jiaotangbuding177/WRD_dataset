# 第11轮：原生53工具协议与离线父调度样本

本审计只读取既有捕获、校验JSON Schema及实际调用两套本地tokenizer。没有启动OpenClaw业务会话、执行下列示例工具、加载模型权重或训练。没有修改主manifest、编译器或双设计。

## 可直接复用的技术来源

原目录为`D:/skillloop/output/20261027_wrd_main_v10/historical_v6_native_repair_01/TOOLS_CAPTURE_53.json`，174763 B，SHA `a47db18b7c6bafcfddfe4bce79ae68787303320225a1edf99457720ee1622345`。其中原捕获请求的文件SHA和`tools`字段已分别核对；另外67个原请求的工具字段逐文件pin读取，与此目录全部相同，只有一个工具目录指纹。

捕获元数据为OpenClaw `2026.9.5`、镜像 `sha256:97a0f55bec1ef293c15ddd5a17cc843050387bd2369dcf2fd388b1afd40810a2`。这是原捕获的技术合同，不是本轮探测当前运行容器或确认Spark服务可用的证据。

- `OPENCLAW_TOOLS53.json`：53项完整工具定义，顺序、名称、描述和参数均保持原捕获；没有导出原请求messages。
- `CHILD_ORCHESTRATION_TOOLS.json`与`tools/*.json`：8项父子调度相关工具的原定义。
- `CAPTURED67_CATALOG_PINS.json`：67个技术目录来源pin，不包含原企业会话正文。
- `ABI_OFFLINE_VALIDATION.json`：8个schema正例与8个拒绝负例，全部是离线校验，不是工具执行。
- `SYNTHETIC_SHORT_STATE_STATIC_PROFILES.json`：真实双tokenizer的长度探针，不计训练样本。
- `PROTOCOL_AND_SOURCE_PINS11.json`：全部来源、技术导出和模型模板的pin。

## 父子调度实际ABI

| 工具 | 捕获schema的硬约束 | 可支持的离线决策例 |
|---|---|---|
| `agents_list` | 无必填字段 | 确有选择配置需求时读取可用配置；没有已见配置时不编造agentId |
| `sessions_spawn` | `task`必填；runtime只能`subagent` | 输入／资源已就绪且预算足够时，发起一次有界、隐藏、隔离的检查任务 |
| `subagents` | action为list/wait/cancel；taskIds最多32；timeoutSeconds最多60 | 原生普通子任务仍pending时等待；不能把pending写成completed |
| `agents_wait` | ids必填、1—1000；timeoutSeconds≥0 | 已明确使用collector时收集结果，不能改等普通完成通知 |
| `sessions_yield` | waitFor若给出只能`message` | 未完子任务确实在等后续消息时，显式让出当前turn |
| `sessions_list` | limit≥1；offset≥0等 | 缺目标身份时先检索可见会话 |
| `sessions_history` | sessionKey必填；includeTools为boolean | 已知真实可见目标后读记录；不是按自造ID读取已发生轨迹 |
| `sessions_send` | message必填；mode为notify/steer/followup/resume | 仅在授权和真实目标均明确的上下文构造后续通信决策；本轮不发送任何消息 |

JSON Schema并未完整表达自然语言约束。例如`subagents.action`在schema中不是required，许多工具也没有`additionalProperties:false`；校验通过不能代替handler接受、有效权限、资源存在或真实返回。离线样本应显式给出必要action，并排除未声明字段及语义冲突。

普通少量内部任务使用隐藏子会话，不因研究、运行长或单独工作树设visible=true；默认省略model覆盖并保持公共配置。`context=fork`有same-agent要求且会继承原上下文，公共构造状态优先isolated。非空attachments在此捕获工具中不支持。不得发明外层dispatch、执行器循环或skills全文注入来绕过原生发现／读取。

`runTimeoutSeconds=0`会禁用超时，不能作为统一预算范例。正时限也只是参数，实际硬预算接线仍待原生验证；离线构造中应只根据当前可见剩余预算选择有界任务，不能把一次调用的时限等同整条pipeline成本。

## 31K静态容纳能力

以下每个profile都分别实际调用14B、8B本地HF tokenizer并核完整IDs相等；每模型16次调用。使用已审的共同因果模板。输入均为本次纯技术构造探针，既不是原生轨迹，也不是新增SFT目标。

| 完整53工具profile | user字符数 | 输入tokens | 含短R＋spawn目标的完整tokens | 31K输入后剩余 |
|---|---:|---:|---:|---:|
| 最简提示 | 45 | 26693 | 26811 | 4307 |
| 短结构化状态 | 225 | 26737 | 26855 | 4263 |
| 较长中文探针 | 2064 | 27944 | 28062 | 3056 |
| 更长中文探针 | 5664 | 30344 | 30462 | 656 |

因此，本轮能构造**完整53目录下的短状态→短R／原生工具调用**组件样本，并逐条要求完整序列不超过实际窗口；不能把31K当作可再加入31K正文的空间。即使最简完整目录输入，在32K也无法再留8192输出，不能据此宣称完整探索和未来工具结果都放得下。

core7长度对照的目录少24960 tokens，但不含`sessions_spawn`等父调度工具。该表中core7的“complete”只是保留同一target字符串的反事实长度探针，**该工具调用未被core7声明，不能作为合法父调度SFT**；真正父调度构造须用完整目录或将来经过原生验证、同版声明的目录。探针名称中的1500／4500是早期名称，实际user字符数以记录的2064／5664为准，不能用名称推算token预算。

以上只支持静态数据编译可行性。完整原生skills发现、工具实际读取、子任务收据、pending与恢复、消费Q、KEEP与总成本仍需真实轨迹和评价；没有因合成文本而新增真实来源组或完整自主示范。

## 构造时的因果边界

1. 把当前可见状态放入输入；后来的反馈只用于后续状态或离线授信，不能提前泄露。
2. 工具A使用本目录的真实名字、参数和严格语义约束；假设taskId/sessionKey应在元数据中标为hypothetical。
3. 新作者R、合成D、实际本地CPU反馈分别标注；不能将CPU测试输出包装成OpenClaw工具成功回执。
4. 资源检查通过只支持相应局部信用；没有独立消费Q和成本时不能生成真实合格KEEP。
5. 同一构造机制的变体、重命名和不同prompt不是独立历史经验；学习曲线与留出应按机制家族／共享资源版本分组。

本次新TRAIN来源准入0、真实父调度执行0、完整自主／合格KEEP新增0。原226及保留来源边界未改，未为扩量读取其答案或评分来构造标签。
