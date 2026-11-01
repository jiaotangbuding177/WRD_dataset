# 55版完整流程SFT课程：CPU实编与验收

这些文件描述确定的训练曝光和数据读取，不是训练启动器。固定05—10认证还原根与11公开包还原根；不修改原数据，不新增来源。`contract_optional`是旧loader的pool名，在本完整课程中已经显式纳入，不再是未安排的可选项。

- 第一阶段：418个契约目标按ID排序后，以seed `20261101`洗牌；microbatch 1、累积16，最后2条显式flush，共27个计划更新。
- 第二阶段：原11的full过程日程，832唯一目标、836次曝光，累积4，共209个计划更新。4次原过程重复逐ID列出，不增加独立数据量。
- 同一adapter与optimizer状态接续，完整课程为1,250唯一目标、1,254次曝光、236个计划更新。
- 真实曝光控制同样先做418契约，再做原205过程加相同4次重复：623唯一目标、627次曝光、80个计划更新。它匹配真实曝光，不匹配算力。
- 两种profile互斥，目标ID、监督正文和每批顺序相同；不同的是新辅助题的输入接口。不能将两profile相加计数据量，也不能推理时依赖gold选择工具目录。

| 指标 | budget_projection | full_native53 |
|---|---:|---:|
| 1250唯一目标序列tokens | 10,207,038 | 20,783,472 |
| 唯一正监督tokens | 284,595 | 284,595 |
| 唯一目标≤16K／16K—32K | 941／309 | 539／711 |
| 完整1254次曝光序列tokens | 10,244,527 | 20,820,961 |
| 曝光正监督tokens | 286,573 | 286,573 |
| 曝光加权监督量 | 83,697.65 | 83,697.65 |
| 完整课程计划更新 | 236 | 236 |

实际读取两个profile全部2,500个物理view的二进制数组，验证四features、mask、逐token权重、监督span、shift后有效目标分母和跨profile正监督token IDs。原权重逐位置保留，新627的权重仍为0.05；有效监督量与计算量分别报告。

## 文件

- `FULL_COURSE55.json`：两profile的完整课程与真实曝光控制，逐optimizer步列出microbatch目标ID、pool、长度和loss分母。
- `STATS55.json`：唯一量与实际曝光量、各pool、阶段、监督组件及16K／32K分别计量。
- `COURSE_QA55.json`：实际CPU验收、输入SHA、课程／统计／校验器SHA。
- `verify_course55.py`：stdlib可移植重建与验证器，不导入payload代码或任何模型框架。
- `OPTIMIZATION_GUARD55.json`：实际负例，确认`python -O`会在读取数据与输出前被拒绝，防止关闭固定loader的assert检查。

## 在Spark或其他机器验证

从受信Git checkout选择其`dataset/20261031_v10_curriculum11/tooling/curriculum_loader11.py`，校验器内固定其SHA。先按数据依赖说明实际还原05—10和11；旧企业记录包沿用既有本地密钥，密钥不会写进Git。

```text
python tooling/verify_course55.py --base-root <AUTHENTICATED_CHECKPOINT10_ROOT> --package11-root <RESTORED_PACKAGE11_ROOT> --loader <TRUSTED_CHECKOUT_LOADER11_PY> --out <DIRECTORY_CONTAINING_THIS_COURSE>
```

默认仅对照现有课程和统计，并写入确定的QA回执。`--build`可以从固定输入重新生成相同课程和统计；不会执行训练。请使用正常Python模式，不能使用`-O`或`-OO`。

训练时，每个累积批的loss为`sum(weight * shifted_CE) / sum(shifted_label != -100)`；跨microbatch合计分子分母，不能将各microbatch均值再平均。课程文件已逐步给出有效目标分母。该目录没有权重加载、forward、backward、optimizer update或原生业务采集结果。
