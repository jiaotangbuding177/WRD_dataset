# WRD 14B / 8B 训练前数据审核包

2026-10-25。已完成离线整理与 CPU 编译，**未启动训练、加载模型权重或使用 GPU**。

本包与 [14B 主模型 / 8B 对照方案](../../plans/20261025_14b_spark/README.md) 配套。新增公开范围已按本轮用户授权包含处理后的企业语义内容。原归档及历史失败保留，不改原文伪造正例。

| 核对层 | 实际数量 |
| --- | ---: |
| 原主动作候选 | 6,774 |
| 恢复真实末条收尾 | 347（343 核心格式，4 非核心隔离） |
| 核心格式总审核母表 | 7,117 |
| 可公开正文动作 / 收尾 | 3938 / 178 |
| 结构存在明确问题 | 113（错误类别可重叠） |
| AI 审阅唯一目标 | 425（动作300＋收尾125），另60条动作二审 |
| 人工语义 gold / 独立 dev-test 连通组 | 0 / 0 |
| 全7117候选双模型完整编译通过 | 7100 |
| 全7117候选 ≤16K / ≤32K（累计） | 1998 / 4874 |
| 公开候选双模型完整编译通过 | 4109 |
| 公开候选 ≤16K | 1604 / 4116 |
| 公开候选 ≤32K（累计） | 3236 / 4116 |
| 编译前语义银标 ≤16K / ≤32K（累计） | 32 / 93（分母 134） |

最终可进入后续小规模验证的技术银标数量，以 [FINAL_ADMISSION.json](FINAL_ADMISSION.json) 和 [admission.jsonl.gz](admission.jsonl.gz) 为准。源候选中的 `training_eligible` 是编译前标志，不能据此跳过协议、mask 和长度门。两模型已共用同一份 ID 和数组；后续训练还须固定同样顺序与曝光量，当前未训练。

全7117候选另在本地做了相同CPU编译，汇总和无正文长度/失败统计已附；被隔离正文与其token数组留在本地。公开报告仅使用公开的两个输入文件，可按exact SHA复跑。全候选统计的受控部分不能只凭公开正文复现，二者分母分别记录，不混写覆盖率。

**训练数据入口是 [sft/README.md](sft/README.md)。** `sft/common16k.jsonl.gz` 与 `sft/common32k_long_only.jsonl.gz` 互斥，后者只含 (16K,32K]，不重复短样本。完整历史前缀、历史助手、用户和工具结果的 label 均为 `-100`；只监督当前 completion，含正常终止标记。监督 spans 可精确还原 labels。两套官方 tokenizer 分别执行并逐行比较 token 和 mask，不作截断。

本轮300条动作一审有215条局部通过，未达到原方案建议95%门槛；未审记录未整体转银标。AI 审阅不等于人工 gold，也不批准整个技能的业务质量。已恢复可验证的路线决策与真实终态候选，难以核实者保留 needs_context。路线直写36条含546个子决策，最终63/65产物含1292个侧证决策；337条exec目标保留为原命令，不盲目转换为正确决策。详见 [LABEL_COMPLETENESS.json](LABEL_COMPLETENESS.json)。现有来源图只有1个连通分量，不能把相邻前缀随机拆成独立验证集。本包不代表已经具备全量训练与效果比较的准入条件。

93条最终银标目前含83条工具动作和10条收尾；直接路线写入仅1个父样本、16个reuse子决定，new/defer/no_value尚无准入直接正例。累计32K一遍实际处理1,620,754 tokens，仅18,205 tokens参与loss（约1.12%）；masked历史仍有计算成本。详见 [sft统计](reports/sft_statistics.json)。应先补关键路线分支与收尾审阅，不能用候选规模或重复样本凑满训练量。

该300条是分层、有意覆盖特定子集的局部AI抽审，215/300不能外推为总体正确率，也不能替代人工校准。支持材料本地文字提取成功为4750条，本次可公开正文为 4078 / 4750；其余按hold清单受控保留。

## 文件用途

- `data/`：可公开的完整动作/收尾候选，包含拒绝和未审状态，供继续整理；不要直接全量喂给 SFT。
- `sft/`：通过公开、局部银标、结构、协议、双模型 mask 与长度门的最终子集。
- `compiled/`：全部公开候选中编译通过的数组、长度、ID 清单及失败原因；包括不应训练的候选和超长记录。
- `audit/`、`admission.jsonl.gz`：全7117母表的最小准入/隔离清单和逐条 AI 理由；子 decision 不额外扩成独立样本。
- `support/`：可公开的完整记录子集，包括原生历史（含失败）、源会话、附件文字、retained 技能内容、路线侧证和支持清单，全部 evidence_only。支持提取4750条是本地记录总数，不是独立SFT样本或全部公开正文数。
- `support/archive_opaque_inventory.jsonl.gz`：原归档654948别名/58288对象的完整哈希与范围索引，隐去个人文件名/宿主路径；不表示全部原对象字节已经公开。
- `reports/`、[AUDIT_METHOD.md](AUDIT_METHOD.md)：实际恢复、静态检查、抽审、清理、覆盖和局限。未公开正文有明确原因清单，原件仍在本地受控保留。
- `tokenizer_assets/`：两模型锁定 revision 的官方分词器和原许可文件，不含权重。`scripts/` 是离线数据工具，不是 Agent 循环或训练执行器。

## CPU 复核

在本目录执行（输出目录须尚不存在）。审计依赖见 `requirements-audit.txt`，其中不安装 torch。观察到的 Windows CPU 包版本不是 Spark ARM64 训练锁；继续使用 NVIDIA 训练环境原有 torch，未来训练环境兼容性仍需另验。

```sh
python scripts/wrd_training_preflight/token_compile.py --input data/candidates.actions.jsonl.gz --input data/candidates.labels.jsonl.gz --assets tokenizer_assets --plan plan_snapshot/TRAINING_CONFIG.json --output replay_token_masks --workers 2
python scripts/wrd_training_preflight/finalize.py --public . --compiled replay_token_masks --output replay_admission
```

复跑公开数据可核验 token/mask、覆盖和技术准入。重新从原始会话/CAS恢复标签或提取附件，还需要原受控 bundle；公开清理版本不能替代被隔离的原文。`labels.py` 可用 `--legacy-toolkit scripts/wrd_training` 指向附带只读 helper。

算力结果目前仅有离线整理 wall time；未测 Spark 训练速度、峰值内存、耗电或每个合格技能总成本。质量及 CPQS 仍按既定方案在独立新来源上评价，不能用本轮候选量、通过率或 tokenizer 速度代替。
