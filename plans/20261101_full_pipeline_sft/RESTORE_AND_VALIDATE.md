# 完整数据取得与CPU验证

本页只下载、恢复和验证数据，不加载模型或执行训练。完整数据依赖05—11七包，不能只下载第11版329MB辅助包。

## 取得真实数据实体

```sh
git clone --branch codex/wrd-training-data-20261025 https://github.com/jiaotangbuding177/WRD_dataset.git
cd WRD_dataset
git lfs install --local
git lfs pull --include="dataset/20261029_v10_checkpoint05/**,dataset/20261029_v10_checkpoint06/**,dataset/20261030_v10_checkpoint07/**,dataset/20261030_v10_checkpoint08/**,dataset/20261031_v10_checkpoint09/**,dataset/20261031_v10_checkpoint10/**,dataset/20261031_v10_curriculum11/**"
```

有LFS指针不等于已下载实体。先按本目录`DATA_DEPENDENCIES.json`核七个文件的size/SHA；其中10＋11是本次此前待补上传的553,740,709字节。需要原始历史总包时，另取根`dist/`的12分卷及对应原清单；它们保留追溯，不直接glob为训练数据。

## 恢复认证主根与辅助根

05—10使用用户已有的本地`wrd-reasoning-v4.key`，由用户在自己的机器之间安全转移；Git中没有密钥，也不把密钥作为仓库文件上传。按以下顺序，在各包目录执行其README中的恢复命令，每次输出到新目录：

| 顺序 | 包目录 | 结果 |
|---|---|---|
| 1 | dataset/20261029_v10_checkpoint05 | 认证05根 |
| 2 | dataset/20261029_v10_checkpoint06 | 05＋06合并根 |
| 3 | dataset/20261030_v10_checkpoint07 | 05—07合并根 |
| 4 | dataset/20261030_v10_checkpoint08 | 05—08合并根 |
| 5 | dataset/20261031_v10_checkpoint09 | 05—09合并根，含保护别名更正 |
| 6 | dataset/20261031_v10_checkpoint10 | ROOT10，当前623主白名单 |
| 7 | dataset/20261031_v10_curriculum11 | 独立ROOT11，两种627目标profile |

每个旧包的加密receipt固定明文/密文及manifest SHA，使用该包配套restore/merge脚本；不能拿05旧529目标入口作为当前训练集。恢复CPU环境可沿用既有Python3.11、cryptography50.0.1，以及需要独立重tokenize时的transformers4.57.6/tokenizers0.22.2/Jinja2 3.1.6/jsonschema4.26.0；实际Spark依赖与wheel架构须核实锁定。仅本次课程数组读取不需要torch、transformers或模型权重。

ROOT10最终应有：

- TRAINING_MANIFEST.json：SHA `9aace2dc6b39d0dde3bafbf9f7f3d6763e485609017dd70a5c40c17a2c30277e`。
- PAYLOAD_MANIFEST.json：SHA `88e0f8b6bd19d02cade6dbad89d60ebea15e254ceb5193b58facdc89b8bfd83d`。
- canonical_arrays10/ARRAY_INDEX10.json：SHA `712c96c0e483c6d171f3a245a83364ab217593004796404b4ce60917c4c60c4a`。

ROOT11归档SHA `7b2f8b6d2719340d2d3d2f8090a3d6c5c580960c7c9fb233de8396445aaad0a7`，PAYLOAD_MANIFEST SHA `e17ad42a98967641d0fd24779012791a5052a8d7919f398309f6081af5b371a6`。用11 README的restore_package11命令取得ROOT11；该包无需密钥。其work/budget_curriculum01与work/curriculum01是同627目标的两种训练条件，不叠加。

## 复验完整1,250目标与课程

```sh
python3 plans/20261101_full_pipeline_sft/tooling/verify_course55.py \
  --base-root /data/wrd10 \
  --package11-root /data/wrd11 \
  --loader dataset/20261031_v10_curriculum11/tooling/curriculum_loader11.py \
  --out plans/20261101_full_pipeline_sft
```

正常结果：全部2,500个物理view（两个profile）实读、1,250唯一目标、284,595唯一正监督；完整课程1,254次曝光、286,573曝光正监督、236次**计划**更新。budget曝光序列10,244,527、full曝光序列20,820,961。校验器不调用训练框架；无forward/backward/update。

`--out`中需先有本次Git的FULL_COURSE55.json和STATS55.json；默认对照验证并输出QA。可用`--build`从相同固定输入重建排程，但不得把它作为模型训练启动器。不使用`python -O/-OO`。

原始会话、完整工具记录、失败/反馈/修订、源码和审计由数据包保全；训练只读取明确白名单。原226及全部保留组维持隔离，不能把保全的评测答案或audit加入loss。
