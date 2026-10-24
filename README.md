# WRD 小模型训练快速入口

这里提供已经整理并通过一致性检查的 **6,774 条 SFT 动作候选**，方便先取得训练入口文件。它们与完整数据包中的 core7 数据完全相同，**新增独立样本数为 0**。

- 数据：`training/native_actions_core7.train.jsonl.gz`，200,343,331 字节。
- SHA256：`bf940e8a84be187b6da3288b3d13fff59ee61c10cd2849ddf126bec3ba95e885`。
- 6,200 条来自技能制作，574 条来自路线筛选；统一提供七种原生编码工具定义。
- 这些是待语义审核的候选，语义 gold 批准为 0；尚未按目标 tokenizer 编译损失范围，也未启动权重训练。

安装 Git LFS 后可只下载此分支：

```sh
git clone --single-branch --branch codex/wrd-training-quickstart-20261025 https://github.com/jiaotangbuding177/WRD_dataset.git
cd WRD_dataset
git lfs pull
```

`QUICK_TRAINING_MANIFEST.json` 记录入口文件身份；`TRAINING_VALIDATION.json` 与 `UNIFORM_TOOLS_VALIDATION.json` 记录已经完成的历史前缀、工具协议和一致性检查。`PLAN.md`、`DATA_CARD.md` 和 `IMPLEMENTATION.json` 说明整理范围与使用限制；`tools/` 保存离线整理和校验程序。

训练时只把历史 `prompt`、当前 `completion` 和 `tools` 送入相应训练适配器；语义审核、分组与来源等外部元数据不是历史输入。只对当前 completion 计算损失，工具结果与历史上下文不作为监督目标。需先按实际目标 tokenizer 检查长度和工具模板，不静默截断程序或上下文。

完整证据包现已上传并核验完成：12 个 LFS 分片，共 3,018,378,417 字节。完整原始证据、历史修订、费用、隔离数据和全部校验位于同一私有仓库的 [`codex/wrd-training-data-20261025`](https://github.com/jiaotangbuding177/WRD_dataset/tree/codex/wrd-training-data-20261025) 分支；请查看[完整包说明](https://github.com/jiaotangbuding177/WRD_dataset/blob/codex/wrd-training-data-20261025/README.md)和[分片清单](https://github.com/jiaotangbuding177/WRD_dataset/blob/codex/wrd-training-data-20261025/package_manifest.json)。快速入口与完整包使用相同的 core7 候选数据。

本仓库包含企业领域材料，应保持私有。
