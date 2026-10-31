# WRD检查点10：原思考、资源修订与来源核清

当前实际主集为623目标／227233正监督tokens／3853977序列tokens：418契约辅助＋205过程，过程56来源／44全局连接组。539目标≤16K，84在16—32K，全部14B／8B共同可用。它们不是623条完整技能沉淀。

本批实际新增29目标／20984正监督，资源祖先仍UNKNOWN的一条旧目标暂扣9905 A，净增28目标／11079正监督；原思考撤0。当前主manifest SHA `9aace2dc6b39d0dde3bafbf9f7f3d6763e485609017dd70a5c40c17a2c30277e`。旧09及所有原件／失败／修订链保全。

[数据与阶段缺口](ACTUAL_DATA_REPORT.md) · [14B主／8B对照方案](TRAINING_PLAN.md) · [完整工具目录限制](CONTEXT_AND_NATIVE_READINESS10.md) · [全量分阶段验收](FULL_STAGED_DATA_QA.json) · [真实还原验收](CHECKPOINT_QA.json)

新增包含15个真实read／目录动作与兼容API局部原R、6个会议资源与修复、3个校验器修订／可见HOLD、5个实质原兼容R＋A再情境化。原R54946、明确再情境化的原R4326、新作者R2298分账；R-only46条仍保留。未知、错误及交界tokens为零loss，完整原文仍在受控审计中。后来的成功或最终反馈不倒灌早期输入，也不把错误正文洗成正例。

## 恢复与唯一训练白名单

先按05、06、07、08、09各目录README获得认证09合并根。下载本目录真实LFS实体并沿用既有本地AES密钥；密钥不在Git。所有必要正文及审计在加密实体和先前05—09认证包中，公开报告不代替正文。

```text
python tooling/merge_delta10.py --base <RESTORED09_ROOT> --cipher controlled/wrd-v10-delta10.tar.gz.aesgcm --receipt ENCRYPTED_DELIVERY_REPORT.json --key <EXISTING_LOCAL_KEY> --delta-out <NEW_DELTA10_DIR> --out <NEW_MERGED10_DIR> --restore-tool tooling/restore_checkpoint.py --restore-tool-sha256 c128038cecd2b7ca7101a000bc05d2e290b8a191760335f0b8030a4907afa719
```

恢复后只读`TRAINING_MANIFEST.json.actual_train_files`。`canonical_arrays10/ARRAY_INDEX10.json`及`canonical_arrays10/binary_loader10.py`覆盖623条／1869真实数组，返回input_ids、attention_mask、labels、loss_weights。旧row.binary_arrays为legacy，不能通配载入所有JSONL、候选或历史银行。

新原件／中间审计在`evidence10/`，新原路径映射为`EVIDENCE_PATH_ALIASES10.json`，旧映射保留。原记录、原native工具导出与兼容API的局部脱敏差异、被拒ABI、旧坏代码、CPU反例、208040历史UNKNOWN字符、保护来源和未闭祖先均保全，但审计保全不等训练准入。原226／H12／static与保留40来源＋本轮新增dev整组继续隔离。

## 能力、窗口与成本

当前字面阶段A423／B158／C11／D5，另历史workflow R26。完整原生自主A—D、合格KEEP、完整WRD学生dev/test仍0，完整主入口null／NOT_READY。当前支持组件研究准备，不能保证得到用户预期的全自主沉淀模型。

core7训练投影不能替代原生53工具验证：新29展开各自真实53目录后完整序列只有11≤32K、18超窗；原67仅输入2≤32K、65超窗。两批在32K均不能另留8192输出。该静态profile不等原native请求等价或rollout可运行，64K／128K及Spark ARM64／GB10均未验机；本轮没有自行改变原生发现／工具／会话循环。

组件候选日程为过程一轮52更新、契约一轮27、联合79／最多183；本轮没有加载权重、forward、backward、训练或新业务采集。新增AI整理与CPU费用未知非0；合格学生技能K=0，每合格技能总成本未定义。

实际加密还原与远端完整实体核验以`CHECKPOINT_QA.json`及`REMOTE_VERIFICATION.json`最终回执为准，不以pointer、加密receipt或本说明替代验证。
