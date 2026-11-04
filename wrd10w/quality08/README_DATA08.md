# WRD实际数据检查点08

本次是实际数据、原件与训练数组交付，不是只有候选清单。完整自主训练仍NOT_READY，未训练。

- 默认主集569目标／177562监督／3496949序列tokens；484≤16K＋85在16–32K。
- 契约436＋过程133；新增17个资源／修订组件26888监督，原R新正loss0，5条新作者R单列226。
- 22坏代码区间精确mask0，初版错误测试整条隔离。原程序、原思考、工具、失败和修订均在认证audit实体内保全。
- 原件账1871 native／34616 owner，另1536 provider组；1871原native和2990原API carrier齐全，781旧缺件exactSHA恢复。保护数据不作默认训练。
- [具体训练计划](TRAINING_PLAN.md)、[实际处理报告](RECOVERY_REPORT.md)、[实际数据统计](ACTUAL_DATA_STATISTICS.json)。
- 3份潜在敏感URL原始载体仅保全于加密审计包，禁止明文导出与默认训练；有限例外按源SHA、匹配SHA、层、次数绑定，密钥不入Git，其他凭据检查仍无条件拒绝。

## 还原与读取

先按检查点05、06、07的README恢复真实07合并根。再下载本目录LFS实际实体，不能只取LFS pointer。本地原AES密钥沿用，密钥不在Git，不要求重新生成。

```text
python tooling/merge_delta08.py --base <RESTORED07_ROOT> --cipher controlled/wrd-v10-delta08.tar.gz.aesgcm --receipt ENCRYPTED_DELIVERY_REPORT.json --key <EXISTING_LOCAL_KEY> --delta-out <NEW_DELTA08_DIR> --out <NEW_MERGED08_DIR> --restore-tool tooling/restore_checkpoint.py --restore-tool-sha256 c128038cecd2b7ca7101a000bc05d2e290b8a191760335f0b8030a4907afa719
```

只读取新合并根的TRAINING_MANIFEST.json.actual_train_files。标准loader生成input_ids／attention_mask／labels／loss_weights；或用canonical_arrays08/binary_loader.py及ARRAY_INDEX08.json读取相同569行、1707真实数组。旧行内binary_arrays字段属legacy，不默认跟随。不得通配audit、候选、旧准备或整个还原目录训练。

08合并保留旧冲突版本到history/pre_delta08，旧分片不改。实际根还原及远端字节回读状态以本目录CHECKPOINT_QA.json和REMOTE_VERIFICATION.json为准；生成加密receipt本身不证明上传或模型效果。

## 适用边界

原226／H12／static评测隔离。56新恢复原R共52823字符来自正式评测，保全audit且loss0。新增17是局部资源和修订子能力，含已有全文的重试，不是17独立任务或完整skills。KEEP、自主A—D和独立学生dev/test数组仍0。14B主／8B对照组件候选62／最多130更新，Spark训练未验机，无权重加载或训练。
