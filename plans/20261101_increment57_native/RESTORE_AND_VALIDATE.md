# native57数据取得与CPU复验

本页是冻结的研究计划恢复协议：恢复数据和读取四features，不加载模型或训练。新增cipher/manifest精确pins与真实还原回执在研究计划冻结后单独生成，由`dataset/20261101_increment57_native`认证元数据及严格wrapper固定；它们不是本页的自引用成员。远端完成以`deliveries/20261101_increment57_native/REMOTE_VERIFICATION.json`为准。

1. 沿`../20261101_increment57/RESTORE_AND_VALIDATE.md`取得旧05—11和离线57认证依赖，分别保留ROOT10、ROOT11、ROOT57_OFFLINE。旧88caa35/1227及旧实体保留作来源追溯与对照。
2. 新目录`dataset/20261101_increment57_native`使用单LFS实体`controlled/wrd-increment57-native.tar.gz.aesgcm`。核验最终认证manifest/receipt中的size/SHA，不能把LFS pointer文本当实体。密钥沿用受控本地文件，不入Git。
3. 实体冻结后新增的`tooling/restore_increment57_native.py`严格入口拒绝-O/-OO、固定restore57及AES源码SHA，并拒未经审查的AES替换。它固定新cipher与manifest SHA，参数为`--cipher`、`--key-file`、`--out`；具体命令以wrapper的`--help`与dataset真实恢复回执为准。恢复到新ROOT57_NATIVE，逐成员SHA核对，不执行归档内业务Python。
4. 实际恢复active根为`work57/active_dataset57/native_bfc_checkpoint01`；归档同版双稿在`designs/current57/`，历史在`designs/history57/`。本公开manifest/课程快照不能替代数组实体。

恢复后CPU检查（不加载模型）：

```sh
python3 plans/20261101_increment57_native/tooling/verify_active57.py \
  --root /data/wrd57_native/work57/active_dataset57/native_bfc_checkpoint01 \
  --base-root /data/wrd10 \
  --package11-root /data/wrd11 \
  --out /data/wrd57_native_readcheck.json
```

每profile实际1260目标/294828正tokens；budget10631405序列、934短326长；full21207839序列、532短728长，0超32K。两profile互斥、同目标与正负载；新增33均为同一past-only状态，原完整长API另零loss保全。完整原R39679字符保全，不将字符计为tokens。

以恢复active根的`TRAINING_ENTRYPOINT57.json`为实际入口，固定`COURSE57_NATIVE.json`、`CONFIG57_NATIVE.json`和QA：241候选更新，每ID一次，215过程批均有真实锚点。旧1227/233为历史对照，旧55含44隔离ID不可直接沿用。原226及所有保留组继续隔离。

计划冻结后依次完成：显式allowlist/凭据扫描→真实AES还原逐SHA→fresh restore后1260两profile四features实际读取→公开严格wrapper与交付pins→真实Git推送→新bare逐普通blob冷核、官方LFS batch只下载新native OID完整实体。旧实体引用先前证明，本次不重下或重复计算旧1.4GB。无任何训练启动。
