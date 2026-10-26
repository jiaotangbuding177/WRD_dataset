# 正例入口、原始过程、资源与loss mask

本轮不训练。实际准入以`reasoning/20261026_lineage_v6/TRAINING_MANIFEST.json`为入口，不回退到v4/v5候选或旧93条。`resource_closed_quality_covered_process_data_ready=true`表示数据可用于过程SFT；`complete_autonomous_training_or_deployment_ready=false`表示尚不能据此启动完整自主目标的训练或部署结论。

## 可用数据与投影

manifest按`controlled`受控原件与`public`去标识投影分开，再按`native_core`、`reasoning`、`actor_aux`列出实际路径、SHA、大小及数量。公开文件在同目录`data/public.admitted.*32k.jsonl.gz`。受控数据在加密包内的`sequences/controlled/admitted.*32k.jsonl.gz`，其原字段和真实原思考保留。

选一种投影训练，不能合并同源公开/受控记录扩大数量。Actor是业务消费过程辅助，默认关闭，开启时loss预算最多10%。历史reasoning文件保留历史工具和system，属于领域/过程蒸馏资料，不等于已证明现行OpenClaw动作ABI兼容。空银行文件不补造样本，实际是否为空看manifest。

每条准入记录保留`input_ids`、`supervision_spans`、`targets`、`training_manifest_admitted=true`及来源闭包决定。span为`[begin,end,component,base_weight]`，end不含；R为显式原思考，E为带工具调用响应的普通正文，A为实际工具调用/参数，D为不带工具调用响应的正文，F为格式。这些是序列载体，不等于全量语义gold。原reason字段可能在A中的JSON/代码，不能只统计R后把其他解释丢掉。

只有获manifest准入的文件和记录才能建立正标签：

```python
assert row['training_manifest_admitted'] is True
labels = [-100] * len(row['input_ids'])
for begin, end, component, base_weight in row['supervision_spans']:
    labels[begin:end] = row['input_ids'][begin:end]
```

system、用户、环境观察、非归属历史、pad、已知错误和截断目标没有正loss。同一原target在一个投影内只归属一个训练视图；原失败仍留在后续修复的历史输入中。真实loss还需实现计划中的片段均值、父任务预算与阶段/角色预算，上面不是完整训练器，默认SFTTrainer token平均不会自动实现这些约束。本轮没有训练启动器。

## 原始上下文、资源和因果链

加密包保留91会话全部原消息、1715条实际动作—观察边、原artifact与字段到原响应的映射、反馈/修订时间边、未决资源证据，以及历史原思考的完整原request/response、父run/input packet/结果与345个原依赖文件。新增独立复核还保全真实版本反馈等原件。全部逐成员SHA和大小见包内`MANIFEST.json`；不要将档案目录直接通配加载为训练数据。

`admitted.contexts.jsonl.gz`、`admitted.target_owners.jsonl.gz`、`admitted.*resource_closure.index.jsonl.gz`及相应CAS用于从训练token追溯原记录和实际资源字节。阶段会话与跨阶段接口分别保留；外层派发不伪装成模型自主切阶段，完整文件不能倒灌进历史仅见截断的工具返回。原Skill文件写出、历史FINISH READY和最终12/12开发验证不等于当前五维Q合格冻结。

## 解密与独立使用

增量包为`controlled/wrd-lineage-process-v6.tar.gz.aesgcm`，沿用v4的本机32字节私钥，并使用不同的新nonce。密钥没有上传Git。用户本机已有位置：

`D:/skillloop/output/20261025_wrd_reasoning_recovery_v4/local_delivery_key/wrd-reasoning-v4.key`

将钥匙通过私有方式放入Spark，沿用仓库`reasoning/20261025/tooling/encrypted_delivery.py`的认证解密接口：

```text
python encrypted_delivery.py --decrypt wrd-lineage-process-v6.tar.gz.aesgcm --key-file /secure/wrd-reasoning-v4.key --output-tar /secure/wrd-lineage-process-v6.tar.gz
```

认证成功后核对`ENCRYPTED_DELIVERY_REPORT.json`的plaintext SHA，再按包内manifest检查所有成员。脚本拒绝覆盖输出；不要把密钥放进模型输入或Git。旧v4约739MB及v5增量保持，可用于更多历史追溯，本轮新数据和证据独立成增量，不重传旧大包。

原恢复/审核源码保留当时Windows路径，是证据重建脚本；离线训练数组不需要在Spark运行旧执行器。源路径用CAS索引重绑定，不能声称在Spark能原样重放历史自建Agent。分词器资产沿用`preflight/20261025/tokenizer_assets/`，因果模板沿用本轮manifest的SHA及`reasoning/20261025/protocol/CAUSAL_TEMPLATE.json`。这是显式Qwen3因果变体；未来推理API须同版并验证thinking模式，本轮未接线。

ARM64依赖与NVIDIA训练栈将来单独锁定，不用x86镜像覆盖Spark现有栈。数据整理的CPU分词/掩码检查不代表14B/8B的16K/32K GPU前后向或完整自主运行已经通过。
