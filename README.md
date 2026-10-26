# 当前交付：资源闭包与真实过程SFT数据v6

[实际训练数据](reasoning/20261026_lineage_v6/README.md) · [新计划与明确因果链](plans/20261026_lineage_training/README.md)

主过程106原响应、182659监督tokens（30原思考）；43个原生业务Actor辅助窗另列。原生WRD核心/完整A—D自主链仍为0，不能声称完整理想模型训练数据已足量。原226继续隔离，未训练。下方v4/v5为历史交付口径，当前按v6manifest。

---

**v5历史快照（由上方v6替代）：用户确认原226继续隔离。** [历史v5来源审计与补充](reasoning/20261026_strict226/README.md)；直接来源候选本地275窗、公开85窗，资源传递隔离仍待核，最终训练清单准入0。旧数组/旧数量留作历史证据；当时公开候选正loss全部禁用，不启动训练。

# WRD 原始思考、完整过程数据与训练计划

**v4：找回原SSE思考并实际编译，未启动训练。**

[调研与新计划](plans/20261025_reasoning_distillation/README.md) · [真实数据与完整加密原件](reasoning/20261025/README.md) · [当前就绪与限制](plans/20261025_reasoning_distillation/READINESS.json)

完整母本/原思考/响应/工具过程/来源与失败证据已加密交付，钥匙留本机；公开投影提供实际数组和loss span。v4当时原226训练范围待确认，现已按v6保留隔离，严格层不能冒充足量覆盖完整自主目标，候选正loss禁用；旧93不是主训练集。

---

# WRD 全流程蒸馏数据与训练计划

**最新：已扩至全阶段候选；完整主训练集正在审核，尚未训练。旧93条仅作诊断。**

[详细训练算法、数据量与验收计划](plans/20261025_fullchain_distillation/README.md) · [新增1051会话／17513候选](fullchain/20261025/README.md) · [当前入口状态](TRAINING_ENTRYPOINT.json)

新计划覆盖A归纳筛选、B工作流资源、C双臂试做与反馈修订、D封装冻结。完整母表19728个沉淀角色非空位置及11683个Actor非空位置仍需全量准入和共同mask编译；下列旧统计仅对旧make/screen子集有效。

---

## 历史子集交付记录

# WRD 全链路训练数据包

**最新：14B／8B 训练前审核与数据包已整理，未启动训练。**

[数据、审核报告与复核方法](preflight/20261025/README.md) · [最终准入](preflight/20261025/FINAL_ADMISSION.json) · [训练就绪状态](preflight/20261025/READINESS.json) · [文件哈希清单](preflight/20261025/MANIFEST.json)

[标签更正](preflight/20261025/ANNOTATION_ERRATA.json)：一条受控轮询记录的schema拒绝依据改为待复核；旧审阅保留，93条准入及token/mask不变。

| 统计对象 | 总数 | 完整≤16K | 完整≤32K（累计） |
| --- | ---: | ---: | ---: |
| 全部核心格式候选 | 7,117 | 1,998（28.07%） | 4,874（68.48%） |
| 可公开正文候选 | 4,116 | 1,604（38.97%） | 3,236（78.62%） |
| 编译前语义／结构银标 | 134 | 32（23.88%） | 93（69.40%） |

全候选7,100条、公开候选4,109条通过双模型token/mask逐行一致性核查；全候选17条官方模板前缀异常已隔离。当前最终技术银标仅93条：32短样本＋61长样本，两个文件互斥。原6,774条入口是历史候选，不能整包直接训练。人工gold与独立dev/test组仍为0；新建/延后/无价值路线分支还没有准入直接正例，当前不适合按原计划进行完整SFT。

当前入口见 [sft/README](preflight/20261025/sft/README.md)。本轮按用户授权提供处理后的企业候选、标签、数组、源会话/附件文字、完整归档哈希及拒收/受控清单；私盐、映射、疑似个人敏感正文与受控数组留本地。新增包约461MB，旧归档不改、不重传。

仅获取本轮新增资料：

```bash
GIT_LFS_SKIP_SMUDGE=1 git clone --branch codex/wrd-training-data-20261025 https://github.com/jiaotangbuding177/WRD_dataset
cd WRD_dataset
git lfs pull --include="preflight/20261025/**" --exclude=""
```

[14B主模型／8B对照详细训练计划](plans/20261025_14b_spark/README.md) 保留制定时快照；当前数据状态以本次审核为准。训练性能、技能质量和每合格技能总成本尚未实测。

<details>
<summary>历史交付说明（保留原条件与旧候选入口，不作为当前训练准入）</summary>

**最新训练计划：14B主模型、8B对照（2026-10-25）**

[详细计划](plans/20261025_14b_spark/README.md) · [参数草案](plans/20261025_14b_spark/TRAINING_CONFIG.json) · [质量与每合格技能成本协议](plans/20261025_14b_spark/EVALUATION_PROTOCOL.md)。本次仅新增不含企业内容的公开计划，未启动训练或新评测。下文保留原数据包交付说明，其中初始7B—9B范围与私有交付表述属于当时条件。


直接训练入口另放在 `training/native_actions_core7.train.jsonl.gz`（约200MB），与完整包的推荐core7数据逐字节一致。`QUICK_TRAINING_MANIFEST.json` 绑定SHA和样本数，`TRAINING_VALIDATION.json`、`UNIFORM_TOOLS_VALIDATION.json` 可直接在仓库审阅。完整证据包保留在 `dist/`。

仅下载训练入口时，可跳过完整证据分片。PowerShell：

```powershell
$env:GIT_LFS_SKIP_SMUDGE='1'
git clone --branch codex/wrd-training-data-20261025 https://github.com/jiaotangbuding177/WRD_dataset
$env:GIT_LFS_SKIP_SMUDGE=$null
cd WRD_dataset
git lfs pull --include="training/native_actions_core7.train.jsonl.gz" --exclude="dist/*"
```

Linux：

```bash
GIT_LFS_SKIP_SMUDGE=1 git clone --branch codex/wrd-training-data-20261025 https://github.com/jiaotangbuding177/WRD_dataset
cd WRD_dataset
git lfs pull --include="training/native_actions_core7.train.jsonl.gz" --exclude="dist/*"
```

需要复现输入、资源版本或完整过程时，再拉取 `dist/*` 并按下文解包。训练文件的额外远端回执见 `QUICK_UPLOAD_RECEIPT.json`；它与完整包中的同源动作不重复计数。

面向 7B—9B 技能构建模型。完整企业语义材料，仅限用户指定私有仓库使用。数据由已有记录离线整理；没有重新生成技能、调用教师或启动训练。

首先阅读 `DATA_CARD.md`、`PLAN.md` 和 `summary.json`。本包的目标是学习路线发现、技能与资源制作以及反馈修订；业务 Actor 记录单独保留。

7B—9B 后续训练优先读取 `datasets/native_actions_core7.train.jsonl.gz`：6774条已校验动作采用统一的固定镜像7核心工具定义，避免按每条目标工具裁剪可选集合。它与 `native_actions.train.jsonl.gz` 是同一批样本的两种表示，不重复计数或拼接。实际loss mask和token长度需在选定模型后编译。

- `archive/`：内容寻址归档。`file_index.jsonl` 把原来源、全部尝试、初始输入、资源版本、产物和费用映射到 `objects/`，同字节内容只存一份；`source_sha256` 与 `sha256` 区分原件和经过凭据清理的打包字节。
- `catalog/`：作业、路线、episode、来源附件和原状态表，保留失败、引用、未知及历史条件。
- `canonical/`：原生会话过程；隐藏思考不作为监督答案。
- `datasets/`：真实历史前缀与下一动作候选、最终答复候选及辅助记录，具体名称和数量见 `summary.json`。候选证据等级与适用范围按每行字段读取，不能把所有文件混成同一正例集。
- `training_audit/`：过滤理由、动作定位与待语义审核记录；`TRAINING_VALIDATION.json` 是全量历史前缀、目标和文件匹配的一致性核验结果。
- `quarantine/late_skill_versions/`：后续12类部署库、8份轻修和4份接口修正版，作为版本证据保留；这些版本可能接触正式评测反馈，已从主要训练与独立测试隔离。
- `splits/`：连通组与正式评测隔离说明。现有全链路存在跨来源、跨路线传播，严格分组后不能据随机动作切分声称独立验证。
- `skills/retained29/`：最终保留技能的原样副本，与原 154 文件清单核对；不是把全部历史制作都批准为训练 gold。

分片包的恢复和完整性检查：

```text
git lfs install
git clone --branch codex/wrd-training-data-20261025 https://github.com/jiaotangbuding177/WRD_dataset
cd WRD_dataset
git lfs pull
python tools/delivery.py unpack --release . --output ./unpacked
python tools/delivery.py validate --bundle ./unpacked
```

将某条原生会话的工作区恢复到新目录：

```text
python tools/materialize.py --bundle ./unpacked --prefix episodes/ep_ID/workspace --output ./workspace
```

用 `catalog/episodes.jsonl` 查询真实 `episode_id`。恢复只读取包内对象，不依赖原来的 D/E 盘；原目录字符串作为历史证据保留。运行历史脚本不属于解包步骤。

后续先选择具体学生和 tokenizer，对拟用候选做语义复核、实际长度与训练模板编译，再开展有界 SFT。完整保留上下文；不能静默截断程序、工具结果或依赖前文。教师历史不是当前小模型的在线 GRPO 样本，跨修订不同前缀也不是现成 DPO 配对。

</details>
