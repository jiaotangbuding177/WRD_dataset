# native57实体与严格恢复命令

本页为认证归档构建后的独立交付元数据，不修改已冻结57个研究计划成员、训练数据或241步配置。

实体：`dataset/20261101_increment57_native/controlled/wrd-increment57-native.tar.gz.aesgcm`，**81,166,541B**，SHA256 `b4fbf59c470b412d4350e03a553e65b51dcf37f23dae83b487b849a19ffdbdd3`。认证payload manifest SHA256为`836fa3f686ec861fc1803852b21efdaaf95ad5c466f94a8c2d3281b6c0e45ee2`，该完整manifest是AES内首个成员；公开精确pins由严格wrapper与dataset descriptor固定，Git不公开含受控成员路径的完整manifest。

先取得旧05—11及离线57依赖和受控本地32字节密钥，再运行（示例密钥路径需替换为既有本地文件，密钥不上传）：

```sh
git lfs fetch --include="dataset/20261101_increment57_native/controlled/wrd-increment57-native.tar.gz.aesgcm" origin codex/wrd-training-data-20261025
git lfs checkout dataset/20261101_increment57_native/controlled/wrd-increment57-native.tar.gz.aesgcm
python3 plans/20261101_increment57_native/tooling/restore_increment57_native.py \
  --cipher dataset/20261101_increment57_native/controlled/wrd-increment57-native.tar.gz.aesgcm \
  --key-file /secure/existing-wrd-delivery.key \
  --out /data/wrd57_native
```

使用普通Python；`-O`和`-OO`已实际验证被拒绝。严格wrapper固定新entity大小/SHA、manifest SHA及两份restore/AES源码SHA，不接受替换AES接口。它只认证/恢复原件，归档内业务Python不执行，密钥不复制。

实际已从两个不同fresh目录完成4035文件／4036 tar成员／290536413源字节逐SHA还原。第二次由上述公开wrapper完成，见`../../deliveries/20261101_increment57_native/STRICT_WRAPPER_VERIFICATION57.json`。另从第一次真实恢复根完整读取1260两profile四features、labels/mask/weights，见`../../dataset/20261101_increment57_native/FRESH_RESTORED_ACTIVE_FEATURES_NATIVE57.json`，SHA256 `388c620b060857b8e161b6817b1c1724aa78d389d48163867a8f50cb1491049f`；本wrapper检查不重复HF或模型计算。

训练数据实际根为`/data/wrd57_native/work57/active_dataset57/native_bfc_checkpoint01`，遵循本目录`RESTORE_AND_VALIDATE.md` CPU读取步骤。旧05—11和离线57仍为显式依赖，旧1227/233步仅为历史对照。默认1260／294828正tokens／241候选更新；两profile互斥使用，不双计训练量。阶段分池与下一增量重点见`RELEASE_STATUS57.json`。本轮未训练。
