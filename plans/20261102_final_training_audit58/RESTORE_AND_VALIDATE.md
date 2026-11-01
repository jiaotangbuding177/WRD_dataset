# 恢复58训练数据并复验

本次是小增量：新协议mask/99数组、active58及课程、目标适配器和审计。旧05—11、离线57、native57继续作为认证依赖；本次不重包旧rawSSE。active58内保留21条旧增量bank的相同SHA小副本，使新的active目录可直接加载，不增加目标、来源或曝光。

当前研究计划/数据合同先冻结。实际新cipher、manifest和已完成的还原/远端上传状态见后置`dataset/20261102_v58_protocol_mask/`及`deliveries/20261102_final_training_audit58/`，不将尚未生成的回执写回冻结训练数据。

1. 在Git分支`codex/wrd-training-data-20261025`取得新数据实体。新文件使用Git LFS；先下载`dataset/20261102_v58_protocol_mask/controlled/wrd-v58-protocol-mask.tar.gz.aesgcm`。旧实体与完整依赖说明保留于[既有入口](../../README.md)、[离线57说明](../20261101_increment57/RESTORE_AND_VALIDATE.md)和[native57说明](../20261101_increment57_native/RESTORE_AND_VALIDATE.md)。
2. 沿旧说明恢复base10与package11，后文分别用`BASE10_ROOT`和`PACKAGE11_ROOT`表示它们的路径。新58的原始思考、provider/native轨迹和实际试跑血缘继续可在native57等原依赖中复核。
3. 使用原本地32字节解密key；key不在Git中。按后置strict wrapper执行到**新目录**：

```text
python plans/20261102_final_training_audit58/tooling/restore_v58.py --cipher dataset/20261102_v58_protocol_mask/controlled/wrd-v58-protocol-mask.tar.gz.aesgcm --key-file LOCAL_KEY_FILE --out NEW_RESTORE58_ROOT
```

wrapper逐SHA钉死cipher/manifest与两个受审恢复实现，拒绝`python -O/-OO`。仍复用已验证57认证envelope，因此容器内的清单和回执名保留`PAYLOAD_MANIFEST57.json`、`RESTORE_RECEIPT57.json`；其中delivery_kind明确58，训练数据和入口是58。不能把命名兼容误读为回退旧课程。

4. 从Git的受审CPU工具复验实际四features、所有步骤alpha和可执行objective；不执行还原包中的Python源码：

```text
python plans/20261102_final_training_audit58/tooling/verify_restore58.py --restored-root NEW_RESTORE58_ROOT --base-root BASE10_ROOT --package11-root PACKAGE11_ROOT --out NEW_FEATURE_QA58.json
```

该检查须实际得到两profile各1260目标、295478正tokens；原数组mass85003.30，课程effective mass84227.1375、辅助2091.9375；215过程步均有真实锚点、每步静态辅助系数mass≤20%，92步缩放。它还在实际还原features上运行受审`objective_adapter58.py`逐241步变量CE算术对账，检查一次缩放、统一分母和原features不变。这里的CE为CPU合同探针，不是模型loss或训练。

5. 实际训练入口为`NEW_RESTORE58_ROOT/active58/TRAINING_ENTRYPOINT58.json`。canonical58与兼容57两个manifest/pin是相同字节，只为使用原受审loader；应按ENTRY58读取`COURSE58.json`和`CONFIG58.json`。两profile互斥，不能拼成2520个样本。

bin中的辅助loss_weights仍是原0.05，不能只读bin而忽略COURSE58。未来trainer按步骤顺序调用[目标适配器](tooling/README_OBJECTIVE_ADAPTER58.md)，以effective weights乘shift后CE，整个累积步骤只除一次共同非ignore target数；不再除accumulation或权重和。

训练配置为14B主/8B对照、最多241更新，checkpoint0/26/80/134/188/241；0是未SFT基线。候选选择和原生模型/工具接线按[总计划](PLAN.md)执行。本次交付不启动训练、模型服务或新业务会话。
