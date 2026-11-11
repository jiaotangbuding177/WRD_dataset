# WRD58 全量建库交接与 H 批复核

核对日期为 2026-11-12。全量材料可恢复。当前发布的执行入口可运行原生分阶段对照，全量 1,107 条的批筛、归并及入库接线待完成。H 回包来自四个冻结案例的自主试验。其结果和下文的阶段对照分开报告。

## H 批结果

H 归档 SHA256 为 `704277d41b19d5895498e71f7ff1c2ac60b0a1774b06fa30f6a025117f2cc3e7`。2,176 个归档文件与解包目录一一对应，2,175 条清单哈希全部通过。四个案例的两臂初始 Git 树和任务提示逐对相同。两次额外启动尝试在模型调用前失败，单列。

| 指标 | 14B-0 | 14B-241 |
| --- | ---: | ---: |
| 应制作案例中通过功能验收 | 0/3 | 0/3 |
| 交付目录有技能首页 | 1 | 1 |
| 实际 HTTP 请求数 | 96 | 299 |
| 实测输入加输出 token | 3,255,999 | 15,996,963 |
| 会话时长合计 | 11,163 秒 | 25,598 秒 |

14B-241 确实写入文件、执行工具并多次编辑。唯一进入交付目录的候选仍有 CSV 与回执错误，最后一次修改后缺成功复验。基座的候选完成了一个 PDF 转换步骤，整条任务的输入范围及验收依据仍缺。应停止案例中，基座落盘的 STOP 方向符合预期，理由证据不足。241 声称通过验证，但没有执行相应试跑。

395 条实际请求的原始响应均完整，`finish_reason=length` 为零。241 前三项达 96 请求上限，第四项以非法工具参数结束。另有两次原生首事件超时，与完整上游回包并列记账。H 批未包含同条件 GLM 臂，零合格技能时单位合格技能成本记为不可计算。H 支持“241 能实际操作和制作候选”，目前的实物不足以证明生产交付或与 GLM 同效。

## Git 材料及可执行范围

- [DELIVERY.json](DELIVERY.json) 和 [恢复脚本](tooling/restore_corpus58.py) 对应 54 个分卷，共 900,092,964 字节。已在本地复算恢复语料的 9,982 个列入清单的文件哈希，全部通过。索引有 1,107 个不同的来源 ID。归档中声明缺失的历史附件仍按原状态登记。
- [THIN_PIPELINE.md](THIN_PIPELINE.md) 对应 `run_thin58.py` 的 `verify`、`prepare`、`run`、`pair`。当前冻结的 `auto01` 至 `auto04` 能走 `route → make → check`。已重新准备 `auto03` 三臂，14B-0、14B-241、GLM 使用同一初始 Git 树 `8508a686e88ea631b5b17c810d64e27f9319878d` 和 10 个输入文件。三个工作区均通过 CPU 校验。模型调用与容器执行为零。
- Spark 用本机 v2 权重。Git 的 `training-v2-run` 有权重 SHA 清单及探针回执，公开树未找到 `out58_14b_v2/checkpoint-{0,241}` 的权重实体。[Spark 启动脚本](execution/spark/serve_wrd58.sh) 按 v2 SHA 核对两套适配器，`main` 的 v1 权重属于历史。工具主机使用固定 `linux/amd64` 镜像 `sha256:97a0f55bec1ef293c15ddd5a17cc843050387bd2369dcf2fd388b1afd40810a2` 和 OpenClaw 2026.9.5，本地审计主机已复核镜像 ID 和架构。其他工具主机使用已加载镜像或另行交接的 TAR，参见 [环境恢复](../../OPENCLAW_RESTORE.md)。Spark 端口 18758 经同事的私有链路接入 x86 工具主机，原生中继端口 18759 独占。

## 可立即派发的一个阶段对照

选 `auto03`，因为 H 的两臂都留有实物，阶段对照可以直接检验范围约束能否传到制作，以及局部修订能否写入交付包并通过复验。这个案例已在开发中使用，报告为阶段回归。三臂用同一输入、提示、原生工具与预算。完整技能须能从公开入口运行，失败及修复都有原生证据。此次先交付真实对照结果，再判断生产接线是否值得继续扩批。

Spark 若尚未运行，可在本机设置 `WRD_WORKSPACE_ROOT` 和 `WRD_HF_ROOT` 后执行 `bash execution/spark/serve_wrd58.sh 14b yarn128 0,241`，保留实际启动日志。以下由可连接 Spark 的 x86 工具主机执行。已有恢复目录时设置 `CORPUS` 指向该目录，省去再次恢复。`SPARK_LOG` 指已核 v2 两别名的实际启动日志，`GLM_CREDENTIALS` 指仓库外私有 GLM 配置。运行目录选择新目录，与 H 原件分离。

```bash
set -eu
git clone --depth 1 --single-branch --branch codex/wrd58-thin-pipeline \
  https://github.com/jiaotangbuding177/WRD_dataset.git wrd58-thin
cd wrd58-thin/full_evolution/20261109
CORPUS="${CORPUS:-$PWD/corpus}"
if [ ! -f "$CORPUS/INDEX.jsonl" ]; then
  python3 tooling/restore_corpus58.py --delivery DELIVERY.json --out "$CORPUS"
fi
SELECTION=autonomous/selection/selection.json
python3 execution/local/run_thin58.py verify \
  --corpus "$CORPUS" --delivery DELIVERY.json --selection "$SELECTION" --case auto03
python3 execution/local/run_thin58.py pair --case auto03 --size 14b \
  --corpus "$CORPUS" --delivery DELIVERY.json --selection "$SELECTION" \
  --startup-log "${SPARK_LOG:?set SPARK_LOG}" --include-glm \
  --glm-credentials "${GLM_CREDENTIALS:?set GLM_CREDENTIALS}" --runs thin-auto03-20261112
mkdir -p receipts-auto03-20261112
cp -- "$SPARK_LOG" receipts-auto03-20261112/
python3 execution/local/package_thin58.py --runs thin-auto03-20261112 \
  --selection "$SELECTION" --receipts receipts-auto03-20261112 --out wrd58-thin-auto03-return.zip
```

带回 `wrd58-thin-auto03-return.zip` 和同名 `.sha256`，同时保留实际模型启动日志。具体功能审核使用 [独立验收说明](autonomous/selection/EVALUATOR_ONLY.md)。Windows 工具主机的命令参数见 [分阶段手册](THIN_PIPELINE.md)，把例中的 `auto01` 换为 `auto03` 即可。

## 全量建库还缺哪些接线

1. 把全部 1,107 条历史会话的去向写入覆盖账本。批量筛选后按主工作跨批归并，用稳定路线 ID 控制新增、更新、复用和暂缓。以路线为单位制作。使用现有 241 时，将本轮登记为已知有训练来源重合的历史工作量重放。原 226 一旦用于这一轮建库，就从该产出库的独立验收中隔离，另用从未进入建库的业务任务验收。异源新 SFT 是单独方案。
2. 复用原 WRD 的阶段构造和后验审核接线，为各模型建立隔离的新队列、相同起始库和断点账本。保留 OpenClaw 的原生工具及会话循环。旧生产入口写死 GLM 且初始化复用历史状态，Git 上的历史源码快照用于核对阶段语义。通过现有三段诊断只证明单例能交接，扩展入口还须验证批筛和归并后的真实队列。
3. 将实际制作品接入独立的同任务有／无技能试用。把真实资源读用、业务交付、完整计量和同版本复验绑定到技能包。按原 WRD 保留条件判断总 tokens 和调用数双降。只有正式审核通过的整包才能切换生效版本，保留旧版本可回退。

同等效果的判断以新入口真实回包为依据。原 GLM 历史库已完成全量 1,107 来源筛选并保留 29 个技能，历史交付仍可使用。同条件下的新模型对照将分别报告合格包、质量、总用量和单位合格成本。
