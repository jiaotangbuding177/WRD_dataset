# 数据入口、解密与复用

本计划与数据在2026-10-25开始整理，2026-10-26收口交付。没有启动训练。仓库同时提供可公开的去标识数据与AES-256-GCM受控原件包；解密密钥只保存在用户本机，不上传Git或写入报告正文。

## 目录含义

- `reasoning/20261025/data/strict226_core32k.jsonl.gz`：公开直接来源严格层的阶段过程silver，当前仅85窗；不能作为已足量的完整自主训练主集。
- `data/original_reasoning16k.jsonl.gz`、`data/original_reasoning32k_long_only.jsonl.gz`：公开源可证、经过真实结局/语义边界覆盖的原思考/历史制作补充，44短＋32长互斥，9条≤32K含原思考的去标识版本。
- `data/strict226_actor_aux32k.jsonl.gz`、`data/historical_actor_aux*.jsonl.gz`：可选辅助，训练预算合计最多10%，不计为沉淀主体。
- `candidates/`：宽来源候选。它们未获严格来源准入，发布时所有正loss禁用，原候选span另存，不能误当训练分片。
- `sources/`：公开原请求/响应/思考的去标识视图，含privacy_transform；不能冒称未变换原字节。
- `controlled/wrd-controlled-records-v4.tar.gz.aesgcm`：完整受控母本、原思考/响应、源对象、失败记录、来源标签、原生数组与本地数据层。含正式/失败/未决档案，不等于整包训练准入。
- `reports/`、`tooling/`：无正文汇总、实际CPU编译/审核和解密脚本。完整受控来源可通过加密包内manifest及source_objects逐SHA定位。

同一企业来源/episode的公开和受控投影共享信息，不能合并后算两条独立任务。源码和恢复流程保留原工作区路径；训练数组与解密可在Spark单独使用，完整重做历史恢复时需按manifest重绑定原路径。没有声称换台机器可原样重放旧执行器。

## 把真实数组交给训练器

每行包含实际`input_ids`、`supervision_spans`及target owner。span格式为`[begin,end,component,base_weight]`，end不含，component含R/E/A/D及F/跨边界混合桶。标签构造：

这些component首先是可验证的序列化载体：R为显式reasoning字段，E为同次带工具调用响应的普通可见正文，A为实际工具调用/参数，D为无工具调用响应的正文（可含结构化决定、解释或终态回答），F为格式。**D不等于该段每句话都已被语义标成正确决策，E也不等于全部思考。** write参数中的reason仍可归A；真正的业务决定正确性来自原字段、真实结果和独立审阅，不能从一个component字母推断。损失先利用这些载体分组，后续细粒度语义标注必须另带来源。

```python
labels = [-100] * len(row["input_ids"])
for begin, end, component, base_weight in row["supervision_spans"]:
    labels[begin:end] = row["input_ids"][begin:end]
```

system、user、工具观察和非归属/错误历史均没有正loss。实际训练还需按TRAINING_PLAN中的片段均值、父样本/阶段预算计算loss；上述基础权重不是该算法全部实现，默认SFTTrainer全token均值并不自动实现它。当前没有训练启动器。

分词器资产在既有`preflight/20261025/tokenizer_assets/`，本轮不重复下载模型或上传相同资产。必须使用本轮`CAUSAL_TEMPLATE.json`声明的因果变体；其保留原R、不依据未来loop.last改过去包装。模型API推理端也要匹配，尚未实测接线。

R只统计显式原reasoning字段。原生普通可见解释E，以及write/exec参数里的路线/审查JSON之reason等内容，同样保留并参与监督；后者归A/资源载体。不能把“显式R为0”解释成没有可学习的判断依据，也不能把全部普通正文伪称原始CoT。

## 受控原件包

加密包使用随机32字节key、随机12字节nonce、16字节GCM tag及认证头。公开报告只含cipher/plain SHA、文件数和认证核验，不含密钥。密钥保存在原工作区：

`D:/skillloop/output/20261025_wrd_reasoning_recovery_v4/local_delivery_key/wrd-reasoning-v4.key`

把密钥单独放入Spark的私有目录；不要提交到Git或放进模型输入。解密脚本依赖cryptography，本次封装端为50.0.1，Spark侧需使用ARM64可用依赖，在独立工具环境准备而不覆盖NVIDIA训练依赖。命令示意：

```text
python tooling/encrypted_delivery.py --decrypt controlled/wrd-controlled-records-v4.tar.gz.aesgcm --key-file /secure/wrd-reasoning-v4.key --output-tar /secure/wrd-controlled-records-v4.tar.gz
```

脚本拒绝覆盖已有输出，认证成功后才提交最终tar文件；输出SHA应等于ENCRYPTED_DELIVERY_REPORT中的plaintext_sha256。再检查包内`CONTROLLED_INPUT_MANIFEST.json`，按正式/失败/未决标志和实际profile选择数据，而不是将整个档案送入训练。精确原始request/response/SSE文件以SHA去重存放在source_objects，aliases记录原关联。

## 推理与成本验证

思考token、工具调用和可见回答全部计入实际推理成本。单轮输出上限还受总上下文余量约束，32K输入不能再追加32K输出。两学生使用共同上下文/原生压缩策略；应保留原教师完整配置参考，不通过人为削弱教师上下文制造质量优势。受控32K对照与原教师完整配置若不同，必须分别报告。

新来源端到端测试须从一次业务输入启动，模型自行选择工具与阶段；真实资源复现、固定Actor双臂验证、失败修订和最后独立质量评分都保留。原生stage提示下的好成绩不能替代该测试。
