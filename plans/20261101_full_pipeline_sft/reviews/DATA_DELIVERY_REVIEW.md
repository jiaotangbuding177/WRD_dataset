# 完整训练数据Git交付依赖核验

本轮为只读CPU文件及Git对象核验；未读取密钥、未解密或执行包内源码，未加载模型、启动训练或新业务。

## 当前训练数据必须交付的完整链

按05基础包→06→07→08→09→10显式合并取得认证main10根，再恢复11公开辅助包。仅11不足以重建当前1,250目标。

| 包 | 实体字节 | 用途 |
|---|---:|---|
| 05 | 189,578,320 | 基础正文、训练分片、原思考／工具／反馈／资源和审计 |
| 06 | 2,828,093 | 精确增量及显式合并工具 |
| 07 | 30,210,262 | 精确增量、规范数组及证据 |
| 08 | 341,011,987 | 恢复原件、训练增量和来源审计 |
| 09 | 190,393,113 | 保护别名更正、来源与监督修订 |
| 10 | 224,555,640 | 当前623主目标及完整规范数组／原件增量 |
| 11 | 329,185,069 | 627辅助目标、两互斥profile、真实数组、构造原件及反例 |
| **合计** | **1,307,762,484** | 当前训练内容的最小完整包依赖链 |

七包均重新校验了实际本地文件全部SHA256／size、HEAD中的真实LFS pointer OID／size，以及本地LFS对象全部SHA256。07—11的所有PUBLIC_MANIFEST引用亦逐个核验通过。结果见`DATA_DELIVERY_REVIEW.json`，不是只检查pointer存在。

本次尚待上传的10＋11实体合计553,740,709字节；05—09保留既有交付文件及远端历史回执，不能将10＋11本地提交冒充已远端上传。

## 原始与中间记录的保全

仓库已有`dist/wrd-training-bundle-v1.tar.gz.part0001`至`part0012`及`package_manifest.json`。本轮重新校验了全部12个真实实体及其Git LFS pointer：合3,018,378,417字节；manifest声明原始包58,754个文件，本轮没有重新解包计数。该历史包与fullchain／reasoning／census／assessment等历史材料持续保留，不作为当前loss白名单通配载入。

05—10中的原始思考、工具、错误、修订和中间状态，与11中的新作者case／反例／失败稿／QA来源分别保全。完整保全与正向监督准入仍分别处理。不能把已核的这些材料外推成所有磁盘原件已被全局穷尽收集。

## 可重建的实际训练入口

1. 每包使用对应README、加密receipt和固定SHA的恢复／merge工具；05—10沿用现有本地AES密钥，不把密钥或凭据提交Git。
2. 当前main10主manifest SHA：`9aace2dc6b39d0dde3bafbf9f7f3d6763e485609017dd70a5c40c17a2c30277e`。
3. 11解包后选`work/budget_curriculum01`或`work/curriculum01`之一。两profile为同627目标，不能叠加扩量。
4. `curriculum_loader11.iter_features(profile_root, authenticated10_root, pools=("real_process", "synthetic", "contract_optional"), use_binary=True)`可取得全部1,250目标；默认两个pool只取得832过程目标。输出input_ids／attention_mask／labels／loss_weights。
5. 只按当前显式manifest和课程曝光记录训练；历史保护集、audit、独立挑战、失败稿及旧不再准入数据不得由glob进入训练。

本日已有全1,250真实联合加载验收：284,595正监督tokens、10,207,038序列tokens、941短／309长；回执`output/20261101_wrd_training_value/ALL1250_JOINT_TRAINABILITY_QA.json`。本轮交付审计没有重复把它计为新训练实验。

## 新计划与Git接续建议

当前冻结README和根`TRAINING_ENTRYPOINT.json`仍保留旧组件就绪度及完整自主NOT_READY措辞；新完整计划必须在根入口标明本轮“覆盖A—D逐步联合SFT已具备数据”的范围，并分别保留“训练尚未启动、Spark未验机、实际自主表现待验证”的事实。建议追加新版本计划并更新根入口，保留冻结10／11载荷及历史回执原字节，避免无必要重封包。

新计划需明确契约418与默认过程832的排程，不能一处称全1,250主训练、另一处仅调两个pool却未安排契约。模型效果与来源多样性不从文件GB或多profile重复数推算。

本轮报告不提供远端上传证明；必须由主Agent解决认证、推送实际LFS实体与branch后，再做远端普通blob／实体回读核验。
