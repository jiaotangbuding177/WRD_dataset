# 57完整数据取得与CPU复验

本流程只下载、认证恢复和读取数组，不加载模型、不执行训练。完整依赖为既有05—11七实体及新增57单个AES LFS实体。57是active selector、准入新银行和原件/血缘审计增量，不重复打包旧05—11。

## 下载实体

```sh
git clone --branch codex/wrd-training-data-20261025 https://github.com/jiaotangbuding177/WRD_dataset.git
cd WRD_dataset
git lfs install --local
git lfs pull --include="dataset/20261029_v10_checkpoint05/**,dataset/20261029_v10_checkpoint06/**,dataset/20261030_v10_checkpoint07/**,dataset/20261030_v10_checkpoint08/**,dataset/20261031_v10_checkpoint09/**,dataset/20261031_v10_checkpoint10/**,dataset/20261031_v10_curriculum11/**,dataset/20261101_increment57_offline/**"
```

若旧05—11已完整取得，只拉57：

```sh
git lfs pull --include="dataset/20261101_increment57_offline/controlled/wrd-increment57-offline.tar.gz.aesgcm"
```

核`DATA_DEPENDENCIES57.json`中的实体size/SHA，不能把LFS指针文本当已下载数据。57实体104626003字节，SHA `01b8b5ec9e1ca7ce0b131a7da556e19d0115ca645f51b212c864d585dd1cde1b`，单实体、不分片。全部八实体总计1412388487字节；旧七实体曾有独立远端证明，本次不会声称重新下载旧包。

## 恢复05—11与57

先按[既有05—11恢复说明](../20261101_full_pipeline_sft/RESTORE_AND_VALIDATE.md)顺序取得`/data/wrd10`和`/data/wrd11`。10主根manifest SHA应为`9aace2dc6b39d0dde3bafbf9f7f3d6763e485609017dd70a5c40c17a2c30277e`；11 payload manifest SHA为`e17ad42a98967641d0fd24779012791a5052a8d7919f398309f6081af5b371a6`的完整值以`DATA_DEPENDENCIES57.json`及旧包receipt为准。

57使用用户已有本地32字节`wrd-reasoning-v4.key`。请在自己的设备间安全转移已有文件；密钥未打进Git，不需要发送给助手。使用新的输出目录：

```sh
python3 dataset/20261101_increment57_offline/tooling/restore_increment57.py   --cipher dataset/20261101_increment57_offline/controlled/wrd-increment57-offline.tar.gz.aesgcm   --cipher-sha256 01b8b5ec9e1ca7ce0b131a7da556e19d0115ca645f51b212c864d585dd1cde1b   --manifest-sha256 e117f39c2c902c363b2b9311f60d6973ed866bf9f6bbca68048e81b3d7747801   --key-file /secure/wrd-reasoning-v4.key   --out /data/wrd57
```

严格入口显式拒绝`python -O/-OO`，先核固定restore/AES实现源码SHA，再调用认证API；不接受未经审查的AES替换文件。恢复全3100文件/3101成员、311516086源字节并逐SHA验证；不执行归档内业务Python。所需CPU依赖是Python3.11与既有cryptography兼容栈；读取训练数组无需torch或模型权重。

## 实际读取四features

57恢复后训练根为`/data/wrd57/work57/active_dataset57/final1227`。本公开plan目录是相同manifest/课程的去标识快照，不含训练数组，不能直接当已恢复根。

```sh
python3 plans/20261101_increment57/tooling/verify_active57.py   --root /data/wrd57/work57/active_dataset57/final1227   --base-root /data/wrd10   --package11-root /data/wrd11   --out /data/wrd57_saved_read_review.json
```

预期两个profile各1227唯一目标/272517正tokens；budget序列9793602、932短/295长；full序列20370036、530短/697长。四features长度、shift、mask、权重、逐目标正token负载应一致。profile互斥，禁止叠加；禁止glob审计原文、旧白名单、raw或未mask版本补回loss。

实际模型输入由active loader返回：

```python
import sys
sys.path.insert(0, '/data/wrd57/work57/active_dataset57/final1227/tooling')
from active_loader57 import iter_features
for features in iter_features('/data/wrd57/work57/active_dataset57/final1227',
                              '/data/wrd10', '/data/wrd11', profile='budget_projection'):
    # features: input_ids, attention_mask, labels, loss_weights
    pass
```

## 采用v2课程

默认读取恢复根的`TRAINING_ENTRYPOINT57.json`，它固定`COURSE57_v2.json`、`CONFIG57_v2.json`及QA SHA。401契约26步＋826过程207步＝233次候选更新，1227目标各一次，尾批真实flush，无补尾重复；v1文件保留。公开根`TRAINING_ENTRYPOINT.json`负责导航，复制到plan的快照不能替代先恢复实体。

旧55包含44个已隔离ID，不再直接作为默认课程。归档和公开最新57设计的两个时点分别由`DESIGN_BINDING57.json`说明；原生补采状态见`NATIVE_STATUS57.md`，后续delta不混入本离线计量。

`RESTORE_RECEIPT57.json`记录实际认证还原，`FRESH_RESTORED_ACTIVE_FEATURES57.json`记录从新还原根重读全部1227×2 features；这些是CPU数据证据。Git远端实体另按`REMOTE_VERIFY.md`在提交推送后独立新下载验证；本地build/commit不当作远端完成。
