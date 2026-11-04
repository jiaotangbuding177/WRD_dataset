# WRD09 独立组件评测任务与血缘隔离

当前唯一可编输入入口为 `INPUT_ONLY_EVAL_ENTRYPOINT05.json`，其指向 `dev.tasks05.jsonl` 和 `test.tasks05.jsonl`。**不要 glob 本目录历史文件**。旧01—04正文、rubric与回执只保留审计，不能把旧33/30的数字继续当当前准入数。

实际通过的是 **26个组件评测输入：9 dev、17 test，覆盖28个保留来源、11个实际材料实体**。其中24个业务交付组件任务，2个信息不足澄清任务；后者不计业务交付TSR分母。`evaluation_level=COMPONENT_OR_CONSUMPTION`，没有完整会话自主沉淀A—D或合格KEEP任务。独审状态为 `PASS_INPUT_CONDITIONS_ONLY_AFTER_PROTECTED_INPUT_EXCLUSIONS`，不是运行验收或模型效果证明。

## 已实际整理的内容

- 初始冻结36个source_scope组件、40个来源（目标12 dev＋24 test），其完整需求和完整原会话均逐SHA恢复；未因后续HOLD而回收进训练。
- 19个带材料来源登记的51引用、49实体全部恢复并与原provided export双重SHA一致。49实体实际独立字节47,622,267；引用字节含重复为47,638,908。实体保存在 `objects/`，不是49个合格任务。
- 每题有实际 `input05.json`、原样文件 `inputs/`、逐题 `rubric.evaluator_only05.json`。输入只含选定用户需求与真实材料路径，不给历史助手答案或评分。原完整会话保存在 `complete_source_audit/`，不挂载给组件任务。
- `COMPLETE_SOURCE_REACHABILITY.json` 可达40份完整原会话。另有36份 `FUTURE_WRD_PARENT_ENVELOPES_NOT_READY.json` 协议，使用完整会话与材料提出未来WRD父任务委托，但全部NOT_READY：没有独立消费案例、实际父模型rollout、固定预算和同版本Q/成本。它们不增加完整自主评测数。

26个输入任务包括清单与技术文档、文案忠实改写、招聘JD与面试规划、HTML交互、图片与资料转换、协议条款提取和有界资料分析。任务来源选择、显式新功能状态和rubric为本轮新作者标注；不冒充原Teacher的原生输入、思考、动作或工具反馈。全部适配在catalog单列。评分未校准、未产生任何模型答案或学生质量分。

## 为什么初始36组只剩26组

| 原因 | 组数 | 处理 |
|---|---:|---|
| 私有DOCX/招聘MD的长文已经在现有训练输入出现 | 2 | HOLD，不作独立新评测 |
| 候选PDF虽新，但私有岗位JD已经在训练输入出现 | 3 | HOLD；可研究近域材料泛化，但不能混入严格独立评测 |
| 私有JD/Gitee变更清单与原226或旧static原用户输入同文 | 4 | HOLD；只作隔离核查，未据保护内容改Q门槛 |
| 原论文未恢复且材料含已有博士方案型内容 | 1 | HOLD，不能当独立研究设计gold |

公司介绍PPT的两份材料属于不同企业，未提供关系，故改为澄清任务；个人画像没有长期记忆，仅评价有界整理/澄清。活动决策固定在2026-10-12的新历史情景，作者身份留metadata，不把活动发生后的结果填入输入。

## 比来源ID更深的隔离核查

先从1107原来源组、97个真实私有材料SHA及已知source引用重建DSU，再比实际内容。元数据零交集仍漏掉了跨来源文档片段和私有JD，所以同时保留：

- `PRIVATE_CONTENT_ALIAS_HOLD.json`：两材料别名的实际当前模型输入位置。
- `REQUEST_CURRENT569_OVERLAP.json`：已见私有JD的请求同文证据。
- `PROTECTED_INPUT_INDEPENDENT_QA.json`：四组与原226/旧static的原用户私有长文匹配独审。
- 密集160字符核查：材料每40字符起点与每个现有训练字符起点比较，49实体6264窗口；有效请求另查。没有命中不证明不存在更短、改写、未捕获或仅图像的祖先。

隔离扫描仅用保护来源的原user输入，不读取其思考、助手答案、成绩或评分来制定任务/门槛。协议的物理13—18页包含低文本/图像附件；现有文本提取不是全文内容正确的gold。未来真实全文检查须图读/OCR，已核实的3.5、7.1、7.2仅是最低具体核点。

## 同时发现的既有训练污染更正

`PROTECTED_CURRENT569_REVOCATION_CLOSURE.json` 提供可机器消费的9来源/23视图撤回提案：15个直接私有JD命中，8个按现有source组件及原代码派生关系保守传播；另7个匹配仅属persona、PromptGuard或通用API示例，不自动撤销。

23视图涉及14727监督token（F108、D3758、A10782、新R79、原R0）与238388输入token。e497—4dff是已冻结显式source引用连接，并非同原组或共享附件；两新纠错视图确实继承旧完整writer代码。独审在 `PROTECTED_VS_TRAIN_INDEPENDENT_QA.json`。本lane没有修改主manifest，原08应保留审计，根采用过滤重基线后才可报告active已撤正。

新32候选除了新功能状态，还逐原owner检查了真实native前缀：31 writer、66 process、12 visible与9 batch02，共118 packet/112唯一owner，只查截至原target、排除未来。所有32都已有精确原owner接线。私有命中为未进新32的旧海报来源；新32仅有通用persona匹配。此结果不替代其它未知资源生产者或缺失system记录的证明。

## 后续使用

1. 根按05入口编14B/8B的input-only数组，labels必须全部为-100，不能加入正loss训练manifest。
2. 先在固定原生OpenClaw与Spark上完成工具、OCR/渲染、图像服务等技术预检；本包没有验证真实运行。缺环境则记录HOLD，不伪造交付。
3. 新五维Q为来源忠实、需求覆盖、交付可用、组织表达、证据边界，各0—4；尚未校准。只允许dev校准后冻结新版，盲test结果不能反向调训练或门槛。Q和TSR分开。
4. 独立父调度、同版本技能消费、真实KEEP/STOP/HOLD和每合格技能总成本仍需后续实际原生任务。不能以这26个组件任务的成功率代替完整WRD成功率，也不能以一次业务输出增加合格skill分母。

本轮没有启动模型、业务Teacher/Actor或训练，没有生成工具反馈或假参考答案。AI整理与CPU核验真实发生，用量和费用未知而非0。
