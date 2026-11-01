# 可直接复用的58训练目标适配器

`objective_adapter58.py`是纯CPU、无依赖的训练数据目标适配器。它不加载模型、不产生logits、不启动trainer，也不执行环境工具。205文件的active58冻结内容保持不变；此helper是后置受审代码。

未来trainer先按`TRAINING_ENTRYPOINT58.json`核验文件hash，使用受审loader读取原始四features，并按`COURSE58.json`某step的microbatch ID顺序准备`loaded_rows`。调用：

```python
prepared = prepare_optimizer_step(step, loaded_rows)
shared_denominator = prepared["denominator"]
for row in prepared["microbatches"]:
    effective_features = row["features"]
    # input_ids/labels/attention_mask仍是原对象；只有loss_weights是新副本。
    # 后续trainer使用这些有效权重及同一个shared_denominator。
```

每个输入item为`{"id": ..., "pool": ..., "features": 四features}`。适配器检查课程ID/顺序/pool、正target数与token hash、原数组mass、精确alpha分数、每步辅助系数mass上限，并只缩放synthetic权重。返回结果带已应用标识；重复传入被拒绝。若剥去标识后把已经缩放的权重冒充原数组，在alpha<1时也会因原mass不匹配被拒绝。

真实训练应按shift后的非ignore target计算逐token CE，用返回的有效权重求整个累积step分子。各microbatch反向时共同除以`shared_denominator`，优化器在本step所有microbatch后更新。**不能再按accumulation数、microbatch均值或权重和归一化；不能在适配器之后再乘一次alpha。**梯度累积框架的隐式平均需要未来trainer明确关闭/覆盖。

`reference_step_loss(prepared, token_losses_by_id)`接收与labels位置对齐的逐token损失向量，按有效权重求和后只除一次共同分母，是可执行的纯CPU参考公式；不计算模型logits、不反向。

`OBJECTIVE_ADAPTER_QA58.json`基于实际两profile全部1260四features，逐241个优化器step与此前独立variable-CE oracle核对，覆盖每profile 92个缩放step、26个无辅助step及尾批1/3。它同时核验输出有效权重的cap、原数组不变和重复缩放拒绝。代理CE只用于合同检查，不是模型loss、质量分或训练成绩。
