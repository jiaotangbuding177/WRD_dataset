# P0当前595目标来源与动作资源血缘复核

本子任务执行next51计划的离线P0。没有修改09主manifest、训练行、原始记录、根双稿或Git发布目录；没有运行原始业务代码、Teacher／Actor、权重、推理或训练。原226／H12／static保护边界保留。原始企业／保护内容不复制到本报告。

## 已完成的实际核查

- 读取09冻结manifest的26个实际分片并验证分片SHA，逐一覆盖595目标；直接source、已知保护DSU、原23撤回来源闭包、新保留40个source ID重核均无新直接命中。manifest保持 `01380a42195dd888aded4140db7dc7013364f6bc66594502487387259d174f42`。
- 对411个已知保护来源的1927条**原user**消息建立7651个160字符隔离指纹；未以保护assistant、思考、Q或评语作标签。另对实际26组件评价的原输入及真实材料做独立指纹隔离匹配。
- 当前有A正监督的实际数量是**99个view**，不是99个不同原生动作owner：83个view有native链接，涉及81个不同原生owner／35个episode；16个是外部历史动作投影、后来教师资源的新状态投影或新作者修复。不能仅因无native链接断言它们全部是新写代码。
- 对上述81个native owner直接重新解析35份原native CAS，复核target原message SHA；记录target前各read／exec／write调用、事件行、call ID、路径／command SHA、写入body SHA及实际反馈SHA。exec提到路径不自动视为读取；read返回不自动视为全文或成功；target之后反馈可以用作审核证据，但不冒充此前prompt。
- 保护producer的226份完整资源文件逐一读取CAS并校验SHA，仅用于资源隔离指纹。所有99个A目标关联native prefix的user／toolResult／system中，没有命中这些文件的完整归一行文本（长度至少100字符）。这不排除短片段、改写、图像、缺失system或未记录SDK请求祖先。

## 精确文本命中的处理

全595有8个view、110个message×保护user来源配对命中，不是110次新污染。其中7个是旧09已经分类的通用PromptGuard包装、persona或通用API例子；新增出现的动作view `process09-batch02-ac76ab7ead15378debb0e555` 仅命中同一PromptGuard包装，其全部两种anchor SHA严格包含于旧通用契约view已见指纹集合。

机器分类保存在 `EXACT_MATCH_CLASSIFICATION.json`，按**精确指纹包含关系**继承旧分类，不把来源全部内容放白名单，不添加未经证实的公共来源声明。没有命中当前26组件题面／材料指纹。除此之外的587个view无160字符匹配，不能被描述为已经证明所有未知祖先干净。

## 指定0f1603的两轮定点恢复及结论

该view关联旧保护producer的tree版本。第一轮在其原E盘transport及原生export根读取指定request、prompts、metadata、events、system和skill_reads；第二轮在既有1536 provider载体索引逐精确response ID查找，没有全盘扫描或按相似输出／时间强行连接。

本轮新恢复到实际runtime的 `context.compiled`／`prompt.submitted` 快照：首轮有53工具schema，续场有14条历史message；但没有逐provider-step API请求。skills／prompting元数据及续场tools被序列化为字符串，完整调用条件仍不闭合。outer request确实声明了该保护skill的12份资源文件，不等于模型实际收到全文；原生成功全文读取记录仍为0。目标前8个recorded response ID在1536旧provider组中均无精确匹配。

对上述快照及target之前原user／tool/system输入，比对保护包12文件实际字节和完整归一文本，均没有证明文件全文送达。故保持**祖先UNKNOWN；未证污染，也未证完全干净**。不能据tree标签或同episode把整个来源撤回，也不能凭未查到读取就解除原代码祖先风险。

建议下一活动白名单仅暂扣：

`process09-0f1603b601613eac2fecb014`

机器入口 `revocations.json`：撤1目标、9905个A正tokens、18040序列tokens，原R撤0、source级撤回0。仅扣此项且无新增时，条件重基为594／206249正监督／3500692序列tokens，过程176。这是给root重编的明确撤回指令，本子任务未激活新manifest。

## 产物与适用范围

- `CURRENT595_P0_VIEW_DECISIONS.metadata.jsonl.gz`：595目标当前来源和边界判定；没有新增语义授信。
- `POSITIVE_A99_RESOURCE_EVENT_LINEAGE.metadata.jsonl.gz`：99个A目标的native／external／新状态区分及可观察调用、资源与反馈事件。
- `CURRENT595_EXACT_CONTENT_ISOLATION_MATCHES.metadata.jsonl.gz`：仅来源、偏移、anchor SHA；不序列化保护正文。
- `EXACT_MATCH_CLASSIFICATION.json`：8个命中view的逐指纹旧分类继承。
- `PROTECTED_PACKAGE_BYTE_IDENTITY_ISOLATION_ONLY.json`：226份保护资源CAS字节验证，隔离用途。
- `0F1603_BOUNDED_RESOURCE_CLOSURE.json`：两轮定点查找回执与新观察，非原生执行结果。
- `revocations.json`：最小可操作撤回集合。
- `P0_QA.json`：机器统计、输出pins、输入主SHA及限制。

保留其它视图意味着维持其原有**局部credit和已验证输入范围**，不扩大为整条原前缀、完整原生prompt等价或合格KEEP。后续P1新发现的祖先证据仍须重接此595账，不能以本报告作永久全域豁免。
