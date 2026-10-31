# WRD11：原过程与可验真构造课程

实际1250个唯一可用目标＝原主集623＋本轮构造辅助627；默认过程课程832＝原205过程＋新627。原623及其原思考、操作、失败和修订保全，原226／H12／static／reserved继续隔离。本轮未加载模型、运行forward/backward或训练。

[实际数据与来源](ACTUAL_DATA_REPORT11.md) · [14B主／8B对照训练方案](TRAINING_STRATEGY11.md) · [统计](DATA_STATISTICS11.json) · [真实还原验收](CHECKPOINT_QA11.json)

新627含576个给定政策状态、51个资源支持case。256个原条件对＋64个阻断对、576个不变扰动QA；10种资源40次真实CPU运行／140项检查。原60资源case中9个重复通用费用目标只保留审计。新R19656全部是新作者依据，不冒充原始CoT；工具意图没有实际派发。32个构造KEEP只是假设前提下的政策答案，真实合格KEEP仍0。

## 还原与读取

新构造包可公开读取，无需AES密钥。它包含实际SFT、两个profile的真实数组、源码、原始新case、被否定的中间稿、反例、独立挑战和验收记录；不是候选清单。

先取得`data/wrd-curriculum11.tar.gz`真实LFS正文，SHA和PM SHA见ARCHIVE_RECEIPT11.json，再用校验过的工具恢复到新目录：

```text
python tooling/restore_package11.py --archive data/wrd-curriculum11.tar.gz --archive-sha256 <ARCHIVE_SHA_FROM_RECEIPT> --manifest-sha256 <PAYLOAD_MANIFEST_SHA_FROM_RECEIPT> --out <NEW_ROOT>
```

原过程pool仍依赖认证05—10合并根，按旧检查点说明恢复，沿用既有本地AES密钥；密钥不在Git。新包不会重复公开企业会话正文。

恢复后的选择清单位于`work/CURRICULUM_SELECTION11.json`。两个profile互斥，同627个目标，不能叠加训练或双算数据：

- `work/curriculum01/`：完整53目录参照。
- `work/budget_curriculum01/`：225条full53＋402条显式无工具决策题。

使用已核SHA的stdlib loader：

```python
import sys
sys.path.insert(0, "<DATASET11_CHECKOUT>/tooling")
from curriculum_loader11 import iter_features

features = iter_features(
    "<NEW_ROOT>/work/budget_curriculum01",
    "<AUTHENTICATED_CHECKPOINT10_ROOT>",
    pools=("real_process", "synthetic"),
    use_binary=True,
)
```

loader在`tooling/curriculum_loader11.py`及各profile内，输出input_ids、attention_mask、labels、loss_weights。只研究新构造pool时可显式`pools=("synthetic",)`，不用base。418契约须显式另选`contract_optional`；严禁glob所有JSONL、错误版本、负例数组、独立挑战或audit进训练。源码内的solve只是离线造题器，不能当业务Agent替代执行循环。

## 计算、质量与范围

full新627为16929495序列tokens，budget为6353061，正监督57362和目标正文保持；62.47%是辅助数据静态序列量减少，不是GPU小时或模型质量的实测变化。budget默认832池为8890987序列tokens／535短297长。0.05构造权重在832唯一池约占有效监督6.667%，不等于梯度或算力份额；全局上限不保证逐批上限。

实际训练需按样本长度动态处理；若把短题一律填充到32K，上述静态序列节省不能直接转成算力收益。

预算视图的目录选择用于离线课程构造，不能推理时偷看正确动作。真实原生评测仍须固定同一OpenClaw环境／工具／skills发现读取／会话循环。当前Spark ARM／GB10梯度与长窗尚未验机，不把静态放得下当完整rollout可运行。

最终曝光在`work/exposure11_final/`：pilot544曝136更新；full832唯一、显式重复4原view后836曝209更新。两profile逐批ID顺序一致；真实曝光匹配控制209曝53更新不冒称计算匹配。它们只是研究卡，不是训练启动器。

真实完整原生自主示范、合格KEEP和完整WRD学生评测仍0。当前可用于组件研究准备，不能保证已能训练出完整自主沉淀模型；K=0时每合格技能总成本未定义。24个手工挑战只有部分兼容，22个修正后probe属于开发回归，均不是学生成绩。

数据和还原QA以CHECKPOINT_QA11.json为准；Git认证缺失时本地提交不代表远端上传。当前远端状态以LOCAL_DELIVERY_STATUS11.json或之后实际网络回执为准。
