# WRD检查点09：实际过程数据、纠错重基线与独立组件评测

当前入口为09合并根的TRAINING_MANIFEST.json.actual_train_files。**不要单独沿用旧08的569行训练**；本轮发现跨来源私有材料别名，已撤销23行及其派生视图，原08保留审计。[更正说明](ACTIVE_USE_ERRATUM09.md)。

实际主集595目标／216154正监督tokens／3518732序列tokens，418契约＋177过程；516行≤16K、79行在16–32K。新增49个有界过程目标53319正tokens，撤销旧23个14727正tokens，净增26目标／38592正tokens。它们不是595条完整技能沉淀轨迹。

[实际数据与缺口](ACTUAL_DATA_REPORT.md) · [14B主／8B对照训练方案](TRAINING_PLAN.md) · [全量独立核验](FULL_STAGED_DATA_QA.json) · [最终恢复QA](CHECKPOINT_QA.json)

原始思考、完整代码、工具参数、失败、反馈和修订版本在实际加密实体内保全。49新目标为52150动作、261新作者理由、753原公开决策、155原公开解释tokens；新增原教师思考正loss为0。已有原思考正监督54745tokens保留。166个已证坏／未证正文或command范围及相交tokens为零loss，原文未删除。

新增独立评测是9 dev＋17 test的组件输入，含真实任务和材料、独立评分rubric；评测输入数组labels全-100、weights全0，不能加入SFT。core7每题1711–4616tokens；full53每题26671–29576tokens，32K窗口下最长仅余3192tokens，不代表完整rollout可运行。没有运行模型或评分。

## 真实还原与读取

先按05、06、07、08各目录README恢复认证08合并根。再取得09的真实LFS实体（不能只有pointer），沿用本地既有AES密钥；密钥不在Git。

```text
python tooling/merge_delta09.py --base <RESTORED08_ROOT> --cipher controlled/wrd-v10-delta09.tar.gz.aesgcm --receipt ENCRYPTED_DELIVERY_REPORT.json --key <EXISTING_LOCAL_KEY> --delta-out <NEW_DELTA09_DIR> --out <NEW_MERGED09_DIR> --restore-tool tooling/restore_checkpoint.py --restore-tool-sha256 c128038cecd2b7ca7101a000bc05d2e290b8a191760335f0b8030a4907afa719
```

还原后只读主manifest白名单；标准库canonical_arrays09/binary_loader09.py和ARRAY_INDEX09.json覆盖全部595条及1785个真实数组，返回input_ids、attention_mask、labels、loss_weights。旧row.binary_arrays为legacy，不默认跟随。标准token验证／读取工具为tooling/checkpoint_loader.py。

完整原件与本轮审计位于合并根的evidence09/；evaluation输入位于evidence09/eval_input_arrays09，其唯一任务入口为evidence09/holdout/INPUT_ONLY_EVAL_ENTRYPOINT05.json。EVIDENCE_PATH_ALIASES09.json提供本轮原路径到还原路径映射，旧08映射一并保留。候选、旧版本、失败目录、保护材料、rubric和审计不能通配加入训练。

## 能力与交付状态

原226／H12／static继续隔离，新保留40来源不回收进训练；未匹配到长文不等于所有改写／短片段／缺失system祖先已证明干净。局部资源检查只授相应组件信用，不授整包质量或技能收益。

完整原生自主A—D、合格KEEP和完整WRD学生dev/test仍为0。当前数据可用于有边界的组件研究准备；Spark ARM64／GB10梯度、吞吐和长窗服务仍需验机，完整主训练入口为null／NOT_READY。未加载权重、未训练、未新派业务Teacher／Actor。AI整理和CPU验证费用未知非0，当前每合格学生技能总成本未定义。

真实加密还原、完整数组与远端实体验证状态以CHECKPOINT_QA.json及REMOTE_VERIFICATION.json为准；加密receipt本身不证明已上传或模型效果。
